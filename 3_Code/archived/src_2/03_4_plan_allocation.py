#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MeducAI - Step03_4 (Plan Allocation / Quota JSON)
-------------------------------------------------
FINAL mode:
- Reads canonical group weights from:
    2_Data/metadata/group_weights.csv   (default)
  or override via --weights_csv
- Writes quota to:
    2_Data/metadata/generated/<RUN_TAG>/target_cards_per_group_<RUN_TAG>__armX.json

Key fixes vs old behavior:
- RUN_TAG folder is output-only (auto mkdir). Inputs are canonical (2_Data/metadata/).
- No requirement to pre-create run_dir/group_weights.csv.

Weights CSV:
- Required: group_id (or record_id) and weight column among:
    weight, group_weight, group_weight_sum, weight_sum, weight_factor
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import pandas as pd


# ==================================================
# Paths
# ==================================================

def now_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def run_dir(base_dir: Path, run_tag: str) -> Path:
    return base_dir / "2_Data" / "metadata" / "generated" / run_tag


def out_quota_json(base_dir: Path, run_tag: str, arm: str) -> Path:
    return run_dir(base_dir, run_tag) / f"target_cards_per_group_{run_tag}__arm{arm}.json"


def default_weights_csv(base_dir: Path) -> Path:
    return base_dir / "2_Data" / "metadata" / "group_weights.csv"


# ==================================================
# Load weights
# ==================================================

WEIGHT_COL_CANDIDATES = [
    "weight",
    "group_weight",
    "group_weight_sum",
    "weight_sum",
    "weight_factor",
]

ID_COL_CANDIDATES = ["group_id", "record_id"]


def load_weights_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"[03_4] group weights CSV not found: {path}\n"
            f"Create it (EDA output) at: 2_Data/metadata/group_weights.csv\n"
            f"Or pass --weights_csv to override."
        )

    df = pd.read_csv(path)
    id_col = None
    for c in ID_COL_CANDIDATES:
        if c in df.columns:
            id_col = c
            break
    if id_col is None:
        raise KeyError(f"[03_4] weights CSV must contain one of {ID_COL_CANDIDATES}. Found={list(df.columns)}")

    w_col = None
    for c in WEIGHT_COL_CANDIDATES:
        if c in df.columns:
            w_col = c
            break
    if w_col is None:
        raise KeyError(f"[03_4] weights CSV must contain a weight column in {WEIGHT_COL_CANDIDATES}. Found={list(df.columns)}")

    out = df[[id_col, w_col]].copy()
    out.columns = ["group_id", "weight"]
    out["group_id"] = out["group_id"].astype(str)
    out["weight"] = pd.to_numeric(out["weight"], errors="coerce").fillna(0.0).astype(float)

    out = out[out["weight"] > 0].copy()
    if len(out) == 0:
        raise ValueError(f"[03_4] All weights are <= 0 after cleaning: {path}")

    # aggregate if duplicates exist
    out = out.groupby("group_id", as_index=False)["weight"].sum()
    return out


# ==================================================
# Allocation (Hamilton + optional caps + rebalance)
# ==================================================

@dataclass(frozen=True)
class Caps:
    min_cards: int
    max_cards: int  # if <=0 => no max


def read_caps_from_env() -> Caps:
    # FINAL-specific caps if present, else fall back to generic
    min_cards = int(os.getenv("MIN_CARDS_PER_GROUP_FINAL", os.getenv("MIN_CARDS_PER_GROUP", "0")))
    max_cards = int(os.getenv("MAX_CARDS_PER_GROUP_FINAL", os.getenv("MAX_CARDS_PER_GROUP", "0")))
    return Caps(min_cards=max(0, min_cards), max_cards=max_cards)


def hamilton_allocate(weights: Dict[str, float], total: int) -> Dict[str, int]:
    """
    Classic Hamilton (largest remainder) without caps.
    """
    keys = list(weights.keys())
    wsum = sum(weights.values())
    if wsum <= 0:
        raise ValueError("Sum of weights must be > 0")

    quotas = {k: (weights[k] / wsum) * total for k in keys}
    floors = {k: int(quotas[k] // 1) for k in keys}
    rem = total - sum(floors.values())
    remainders = sorted(((quotas[k] - floors[k], k) for k in keys), reverse=True)

    out = dict(floors)
    for i in range(rem):
        _, k = remainders[i % len(remainders)]
        out[k] += 1
    return out


def apply_caps_and_rebalance(
    alloc: Dict[str, int],
    weights: Dict[str, float],
    total: int,
    caps: Caps,
) -> Dict[str, int]:
    """
    Enforce min/max caps while preserving total via iterative redistribution.
    Deterministic tie-break: group_id lexical.
    """
    out = {k: int(v) for k, v in alloc.items()}

    # 1) apply min cap
    if caps.min_cards > 0:
        for k in out:
            if out[k] < caps.min_cards:
                out[k] = caps.min_cards

    # 2) apply max cap (if enabled)
    if caps.max_cards and caps.max_cards > 0:
        for k in out:
            if out[k] > caps.max_cards:
                out[k] = caps.max_cards

    # 3) rebalance to match total
    def can_give(k: str) -> bool:
        return out[k] > (caps.min_cards if caps.min_cards > 0 else 0)

    def can_take(k: str) -> bool:
        return (caps.max_cards <= 0) or (out[k] < caps.max_cards)

    cur = sum(out.values())
    if cur == total:
        return out

    # helper ordering: prefer higher weight; tie-break by group_id
    def give_order() -> List[str]:
        return sorted(out.keys(), key=lambda k: (-weights.get(k, 0.0), k))

    def take_order() -> List[str]:
        return sorted(out.keys(), key=lambda k: (-weights.get(k, 0.0), k))

    # If too many, remove from low-priority? We remove from LOW weight first.
    def remove_order() -> List[str]:
        return sorted(out.keys(), key=lambda k: (weights.get(k, 0.0), k))

    # loop with safety
    for _ in range(10_000):
        cur = sum(out.values())
        if cur == total:
            return out

        if cur > total:
            # need to remove (prefer removing from lowest weight, respecting min)
            for k in remove_order():
                if can_give(k):
                    out[k] -= 1
                    break
            else:
                # cannot reduce further
                break
        else:
            # need to add (prefer adding to highest weight, respecting max)
            for k in take_order():
                if can_take(k):
                    out[k] += 1
                    break
            else:
                # cannot increase further
                break

    # final check
    if sum(out.values()) != total:
        raise RuntimeError(
            f"[03_4] Failed to rebalance with caps. sum={sum(out.values())} total={total} caps={caps}"
        )
    return out


def allocate_quota(weights_df: pd.DataFrame, total_cards: int, caps: Caps) -> Dict[str, int]:
    weights = {str(r["group_id"]): float(r["weight"]) for _, r in weights_df.iterrows()}
    base = hamilton_allocate(weights, int(total_cards))
    final = apply_caps_and_rebalance(base, weights, int(total_cards), caps)
    return final


# ==================================================
# CLI
# ==================================================

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser("MeducAI Step03_4 - plan allocation (quota)")

    ap.add_argument("--base_dir", default=".")
    ap.add_argument("--run_tag", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--mode", choices=["FINAL"], default="FINAL")
    ap.add_argument("--total_cards", type=int, required=True)

    ap.add_argument("--weights_csv", default=None, help="Override weights CSV path (optional).")

    return ap


def main() -> None:
    args = build_parser().parse_args()

    base_dir = Path(args.base_dir).resolve()
    run_tag = str(args.run_tag)
    arm = str(args.arm)
    total_cards = int(args.total_cards)

    gdir = run_dir(base_dir, run_tag)
    gdir.mkdir(parents=True, exist_ok=True)

    weights_path = Path(args.weights_csv).expanduser().resolve() if args.weights_csv else default_weights_csv(base_dir)
    weights_df = load_weights_csv(weights_path)

    # HARD GATE: ensure weights universe matches groups universe (prevent silent shortfall later)
    groups_csv = base_dir / "2_Data" / "metadata" / "groups.csv"
    if not groups_csv.exists():
        raise FileNotFoundError(f"[03_4] groups.csv not found: {groups_csv} (required for intersection gate)")
    gdf = pd.read_csv(groups_csv)
    if "group_id" not in gdf.columns:
        raise KeyError(f"[03_4] groups.csv must contain 'group_id'. Found={list(gdf.columns)}")
    groups_set = set(gdf["group_id"].astype(str).tolist())
    weights_set = set(weights_df["group_id"].astype(str).tolist())

    missing_in_groups = sorted(list(weights_set - groups_set))[:50]
    if missing_in_groups:
        raise ValueError(
            "[03_4] group_id mismatch: weights has ids not present in groups.csv. "
            f"First50={missing_in_groups} (fix EDA outputs so universes match)"
        )

    # use intersection only (should be equal after gate; defensive)
    weights_df = weights_df[weights_df["group_id"].astype(str).isin(groups_set)].copy()

    caps = read_caps_from_env()
    quota = allocate_quota(weights_df, total_cards, caps)

    out_path = out_quota_json(base_dir, run_tag, arm)
    payload = {
        "target_cards_per_group": quota,
        "meta": {
            "ts": now_ts(),
            "run_tag": run_tag,
            "arm": arm,
            "total_cards": total_cards,
            "sum_target": int(sum(quota.values())),
            "n_groups": int(len(quota)),
            "weights_csv": str(weights_path),
            "caps": {"min_cards": caps.min_cards, "max_cards": caps.max_cards},
        },
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    top10 = sorted(quota.items(), key=lambda kv: kv[1], reverse=True)[:10]
    print(f"[03_4] Wrote allocation plan -> {out_path}")
    print(f"[03_4] Groups={len(quota)} total_cards={total_cards} sum_target={sum(quota.values())}")
    print(f"[03_4] Top10 target groups: {top10}")


if __name__ == "__main__":
    main()

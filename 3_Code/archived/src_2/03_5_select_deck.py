#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MeducAI - Step03_5 (Select Deck)
--------------------------------
Goal:
- FINAL: quota-aware selection using target_cards_per_group_<RUN_TAG>__armX.json
         Select EXACTLY quota cards per group (or report shortfall).
- S0: simple fixed-total selection (default 12) for smoke/QA.

Invariants:
- RUN_TAG centric paths (no provider folders)
- Deterministic with seed (order / sampling / tie-break)
- Input JSONL expected schema from Step01 includes:
    group_id, record_id, front, back
  (extra keys allowed)

Outputs (under 2_Data/metadata/generated/<RUN_TAG>/):
- selected_<RUN_TAG>__armX.jsonl
- selected_<RUN_TAG>__armX.csv
- select_report_<RUN_TAG>__armX.json
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional


# ==================================================
# Paths (RUN_TAG-centric)
# ==================================================

def run_dir(base_dir: Path, run_tag: str) -> Path:
    return base_dir / "2_Data" / "metadata" / "generated" / run_tag


def default_input_jsonl(base_dir: Path, run_tag: str, provider: str, arm: str) -> Path:
    # Step01 output naming convention
    return run_dir(base_dir, run_tag) / f"output_{provider}_{run_tag}__arm{arm}.jsonl"


def default_quota_json(base_dir: Path, run_tag: str, arm: str) -> Path:
    return run_dir(base_dir, run_tag) / f"target_cards_per_group_{run_tag}__arm{arm}.json"


def out_selected_jsonl(base_dir: Path, run_tag: str, arm: str) -> Path:
    return run_dir(base_dir, run_tag) / f"selected_{run_tag}__arm{arm}.jsonl"


def out_selected_csv(base_dir: Path, run_tag: str, arm: str) -> Path:
    return run_dir(base_dir, run_tag) / f"selected_{run_tag}__arm{arm}.csv"


def out_report_json(base_dir: Path, run_tag: str, arm: str) -> Path:
    return run_dir(base_dir, run_tag) / f"select_report_{run_tag}__arm{arm}.json"


# ==================================================
# IO helpers
# ==================================================

def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Input JSONL not found: {path}")
    items: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                raise ValueError(f"Invalid JSON at line {i} in {path}: {e}") from e
            items.append(obj)
    return items


def write_jsonl(path: Path, items: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for obj in items:
            f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(path: Path, items: List[Dict[str, Any]]) -> None:
    """
    Minimal Anki-like CSV: group_id, record_id, front, back
    Extra keys are ignored (kept in JSONL).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["group_id", "record_id", "front", "back"])
        w.writeheader()
        for obj in items:
            w.writerow({
                "group_id": obj.get("group_id", ""),
                "record_id": obj.get("record_id", ""),
                "front": obj.get("front", ""),
                "back": obj.get("back", ""),
            })


def load_quota(path: Path) -> Dict[str, int]:
    if not path.exists():
        raise FileNotFoundError(f"Quota JSON not found: {path}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    # canonical format: {"target_cards_per_group": {...}}
    if isinstance(obj, dict) and "target_cards_per_group" in obj and isinstance(obj["target_cards_per_group"], dict):
        q = obj["target_cards_per_group"]
    elif isinstance(obj, dict):
        # allow flat dict too (defensive)
        q = obj
    else:
        raise ValueError(f"Invalid quota json format: {path}")

    out: Dict[str, int] = {}
    for k, v in q.items():
        out[str(k)] = int(v)
    return out


# ==================================================
# Deterministic selection
# ==================================================

def group_items(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    g: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for obj in items:
        gid = obj.get("group_id") or obj.get("record_id")
        if gid is None:
            continue
        g[str(gid)].append(obj)
    return g


def deterministic_shuffle(objs: List[Dict[str, Any]], seed: int, group_id: str) -> List[Dict[str, Any]]:
    """
    Tie-break / sampling determinism:
      - Use a per-group RNG seeded by (seed, group_id)
      - Shuffle to select a stable subset when quota < available
    """
    local_seed = (hash((int(seed), str(group_id))) & 0xFFFFFFFF)
    rng = random.Random(local_seed)
    arr = list(objs)

    # stable pre-sort before shuffle (so JSONL input order does not leak into selection)
    # Use a deterministic key if present; otherwise fall back to front/back text.
    def key_fn(o: Dict[str, Any]) -> Tuple[str, str]:
        # if you later add "card_id" or "entity_id", this naturally stabilizes further
        return (str(o.get("front", ""))[:200], str(o.get("back", ""))[:200])

    arr.sort(key=key_fn)
    rng.shuffle(arr)
    return arr


@dataclass
class SelectReport:
    mode: str
    run_tag: str
    arm: str
    seed: int
    input_jsonl: str
    quota_json: Optional[str]
    total_available: int
    total_selected: int
    total_target: int
    shortfall_total: int
    per_group: Dict[str, Dict[str, int]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "run_tag": self.run_tag,
            "arm": self.arm,
            "seed": self.seed,
            "input_jsonl": self.input_jsonl,
            "quota_json": self.quota_json,
            "total_available": self.total_available,
            "total_selected": self.total_selected,
            "total_target": self.total_target,
            "shortfall_total": self.shortfall_total,
            "per_group": self.per_group,
        }


# ==================================================
# Core selection logic
# ==================================================

def select_final(items: List[Dict[str, Any]], quota: Dict[str, int], seed: int) -> Tuple[List[Dict[str, Any]], SelectReport]:
    grouped = group_items(items)

    selected: List[Dict[str, Any]] = []
    per_group_report: Dict[str, Dict[str, int]] = {}

    total_target = int(sum(quota.values()))
    total_selected = 0
    shortfall_total = 0

    # Deterministic group processing order: descending target then seeded tie-break
    gids = list(quota.keys())
    rng = random.Random(int(seed))
    gids.sort(key=lambda gid: (-int(quota.get(gid, 0)), rng.random(), str(gid)))

    for gid in gids:
        target = int(quota.get(gid, 0))
        avail = len(grouped.get(gid, []))
        if target <= 0:
            per_group_report[gid] = {"target": target, "available": avail, "selected": 0, "shortfall": 0}
            continue

        pool = grouped.get(gid, [])
        pool2 = deterministic_shuffle(pool, seed, gid)

        take = min(target, len(pool2))
        chosen = pool2[:take]
        selected.extend(chosen)

        sf = max(0, target - take)
        per_group_report[gid] = {"target": target, "available": avail, "selected": take, "shortfall": sf}

        total_selected += take
        shortfall_total += sf

    rep = SelectReport(
        mode="FINAL",
        run_tag="",
        arm="",
        seed=seed,
        input_jsonl="",
        quota_json=None,
        total_available=len(items),
        total_selected=total_selected,
        total_target=total_target,
        shortfall_total=shortfall_total,
        per_group=per_group_report,
    )
    return selected, rep


def select_s0(items: List[Dict[str, Any]], target_total: int, seed: int) -> Tuple[List[Dict[str, Any]], SelectReport]:
    # Deterministic selection across all items
    rng = random.Random(int(seed))

    def key_fn(o: Dict[str, Any]) -> Tuple[str, str, str]:
        return (
            str(o.get("group_id", "")),
            str(o.get("front", ""))[:200],
            str(o.get("back", ""))[:200],
        )

    arr = list(items)
    arr.sort(key=key_fn)
    rng.shuffle(arr)

    chosen = arr[: max(0, int(target_total))]
    rep = SelectReport(
        mode="S0",
        run_tag="",
        arm="",
        seed=seed,
        input_jsonl="",
        quota_json=None,
        total_available=len(items),
        total_selected=len(chosen),
        total_target=int(target_total),
        shortfall_total=max(0, int(target_total) - len(chosen)),
        per_group={},
    )
    return chosen, rep


# ==================================================
# CLI
# ==================================================

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser("MeducAI Step03_5 - Select deck (quota-aware)")

    ap.add_argument("--mode", choices=["S0", "FINAL"], default="S0")
    ap.add_argument("--base_dir", default=".")
    ap.add_argument("--run_tag", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--seed", type=int, default=42)

    # Input
    ap.add_argument("--input_jsonl", default=None, help="Override input JSONL path (optional).")
    ap.add_argument("--provider", default=None, help="Provider name used to resolve default input JSONL (required if --input_jsonl not set).")

    # FINAL
    ap.add_argument("--quota_json", default=None, help="Override quota JSON path (optional).")

    # S0
    ap.add_argument("--target_total", type=int, default=12, help="S0 only: total cards to select (default 12).")

    return ap


def main() -> None:
    args = build_parser().parse_args()

    base_dir = Path(args.base_dir).resolve()
    run_tag = str(args.run_tag)
    arm = str(args.arm)
    seed = int(args.seed)
    mode = str(args.mode).upper()

    rdir = run_dir(base_dir, run_tag)
    rdir.mkdir(parents=True, exist_ok=True)

    # resolve input
    if args.input_jsonl:
        in_path = Path(args.input_jsonl).expanduser().resolve()
    else:
        if not args.provider:
            raise SystemExit("Either --input_jsonl or --provider is required to locate Step01 output JSONL.")
        in_path = default_input_jsonl(base_dir, run_tag, str(args.provider), arm)

    items = read_jsonl(in_path)

    # select
    if mode == "FINAL":
        qpath = Path(args.quota_json).expanduser().resolve() if args.quota_json else default_quota_json(base_dir, run_tag, arm)
        quota = load_quota(qpath)
        selected, rep = select_final(items, quota, seed)
        rep.mode = "FINAL"
        rep.run_tag = run_tag
        rep.arm = arm
        rep.input_jsonl = str(in_path)
        rep.quota_json = str(qpath)
    else:
        selected, rep = select_s0(items, int(args.target_total), seed)
        rep.mode = "S0"
        rep.run_tag = run_tag
        rep.arm = arm
        rep.input_jsonl = str(in_path)
        rep.quota_json = None

    # outputs
    out_j = out_selected_jsonl(base_dir, run_tag, arm)
    out_c = out_selected_csv(base_dir, run_tag, arm)
    out_r = out_report_json(base_dir, run_tag, arm)

    write_jsonl(out_j, selected)
    write_csv(out_c, selected)
    out_r.write_text(json.dumps(rep.to_dict(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    print(f"[03_5] mode={mode} run_tag={run_tag} arm={arm} seed={seed}")
    print(f"[03_5] input={in_path}")
    if mode == "FINAL":
        print(f"[03_5] quota={rep.quota_json} | target={rep.total_target}")
    else:
        print(f"[03_5] target_total={rep.total_target}")

    print(f"[03_5] selected={rep.total_selected} | shortfall={rep.shortfall_total}")
    print(f"[03_5] out_jsonl={out_j}")
    print(f"[03_5] out_csv ={out_c}")
    print(f"[03_5] report ={out_r}")

    # hard gate for FINAL: fail if shortfall exists (so pipeline cannot silently proceed)
    if mode == "FINAL" and rep.shortfall_total > 0:
        raise SystemExit(f"[03_5:FINAL] SHORTFALL detected: {rep.shortfall_total} cards missing. See report: {out_r}")


if __name__ == "__main__":
    main()

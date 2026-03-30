#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MeducAI - run_arm_full (Runner)

S0:
  01_generate_json (S0) -> 02_postprocess_results -> 03_5_select_deck (S0)

FINAL:
  03_4_plan_allocation (FINAL) -> 01_generate_json (FINAL) -> 02_postprocess_results -> 03_5_select_deck (FINAL, quota-aware)

Includes:
- FINAL preflight (canonical groups/weights existence + non-empty intersection)
- RUN_TAG centric paths
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any


def now_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def run_cmd(cmd: list[str], env: Optional[dict[str, str]] = None) -> None:
    print("\n[RUN]", " ".join(cmd))
    r = subprocess.run(cmd, env=env)
    if r.returncode != 0:
        raise SystemExit(f"Command failed with code {r.returncode}: {' '.join(cmd)}")


def run_dir(base_dir: Path, run_tag: str) -> Path:
    return base_dir / "2_Data" / "metadata" / "generated" / run_tag


def manifest_path(base_dir: Path, run_tag: str, arm: str) -> Path:
    return run_dir(base_dir, run_tag) / f"run_manifest_{run_tag}__arm{arm}.json"


def write_manifest(p: Path, obj: Dict[str, Any]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def read_ids_csv(path: Path, key: str) -> set[str]:
    ids: set[str] = set()
    with path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        if key not in (r.fieldnames or []):
            raise SystemExit(f"[Runner:FINAL] {path} missing column '{key}'. Found={r.fieldnames}")
        for row in r:
            v = (row.get(key) or "").strip()
            if v:
                ids.add(v)
    return ids


def pick_selection_input_jsonl(rdir: Path, provider: str, run_tag: str, arm: str) -> Path:
    # Prefer Step02-derived jsonl if it exists; otherwise fall back to Step01 output.
    pats = [
        f"*post*__arm{arm}.jsonl",
        f"*validated*__arm{arm}.jsonl",
        f"*clean*__arm{arm}.jsonl",
        f"*final*__arm{arm}.jsonl",
        "*post*.jsonl",
        "*validated*.jsonl",
        "*clean*.jsonl",
        "*final*.jsonl",
    ]
    for pat in pats:
        hits = sorted(rdir.glob(pat), key=lambda x: x.stat().st_mtime, reverse=True)
        if hits:
            return hits[0]
    return rdir / f"output_{provider}_{run_tag}__arm{arm}.jsonl"


@dataclass(frozen=True)
class Args:
    base_dir: Path
    run_tag: str
    arm: str
    mode: str
    provider: str
    seed: int
    total_cards: Optional[int]
    daily_study_cards: Optional[int]


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser("MeducAI runner: run one arm end-to-end")

    ap.add_argument("--base_dir", default=".")
    ap.add_argument("--run_tag", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--mode", choices=["S0", "FINAL"], default="S0")

    ap.add_argument("--provider", required=True)
    ap.add_argument("--seed", type=int, default=42)

    ap.add_argument("--total_cards", type=int, default=None, help="FINAL only")
    ap.add_argument("--daily_study_cards", type=int, default=None)

    return ap


def final_preflight(base_dir: Path) -> None:
    gw = base_dir / "2_Data" / "metadata" / "group_weights.csv"
    gcsv = base_dir / "2_Data" / "metadata" / "groups.csv"

    if not gw.exists():
        raise SystemExit(f"[Runner:FINAL] Missing canonical weights: {gw}")
    if not gcsv.exists():
        raise SystemExit(f"[Runner:FINAL] Missing canonical groups: {gcsv}")

    # groups.csv must have group_id
    gids = read_ids_csv(gcsv, "group_id")

    # group_weights: group_id or record_id
    with gw.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        fns = r.fieldnames or []
    wkey = "group_id" if "group_id" in fns else ("record_id" if "record_id" in fns else None)
    if not wkey:
        raise SystemExit(f"[Runner:FINAL] {gw} must contain group_id or record_id. Found={fns}")

    wids = read_ids_csv(gw, wkey)

    inter = gids.intersection(wids)
    if not inter:
        raise SystemExit("[Runner:FINAL] group_id intersection is empty between groups.csv and group_weights.csv")


def main() -> None:
    ns = build_parser().parse_args()

    args = Args(
        base_dir=Path(ns.base_dir).resolve(),
        run_tag=str(ns.run_tag),
        arm=str(ns.arm),
        mode=str(ns.mode).upper(),
        provider=str(ns.provider),
        seed=int(ns.seed),
        total_cards=ns.total_cards,
        daily_study_cards=ns.daily_study_cards,
    )

    os.chdir(args.base_dir)

    py = sys.executable
    env = os.environ.copy()
    env["PYTHONPATH"] = str(args.base_dir / "3_Code" / "src") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

    m = {
        "ts_start": now_ts(),
        "base_dir": str(args.base_dir),
        "run_tag": args.run_tag,
        "arm": args.arm,
        "mode": args.mode,
        "provider": args.provider,
        "seed": args.seed,
        "total_cards": args.total_cards,
        "daily_study_cards": args.daily_study_cards,
        "steps": [],
    }

    if args.mode == "FINAL":
        if args.total_cards is None:
            raise SystemExit("--total_cards is required when --mode FINAL")

        final_preflight(args.base_dir)

        # ensure run dir exists
        rdir = run_dir(args.base_dir, args.run_tag)
        rdir.mkdir(parents=True, exist_ok=True)

        # 03_4
        step = {
            "name": "03_4_plan_allocation",
            "cmd": [py, "3_Code/src/03_4_plan_allocation.py",
                    "--base_dir", ".", "--run_tag", args.run_tag, "--arm", args.arm,
                    "--mode", "FINAL", "--total_cards", str(args.total_cards)],
        }
        m["steps"].append(step)
        run_cmd(step["cmd"], env=env)

        # 01 FINAL
        step = {
            "name": "01_generate_json",
            "cmd": [py, "3_Code/src/01_generate_json.py",
                    "--mode", "FINAL", "--base_dir", ".", "--run_tag", args.run_tag,
                    "--arm", args.arm, "--provider", args.provider, "--seed", str(args.seed)],
        }
        m["steps"].append(step)
        run_cmd(step["cmd"], env=env)

        # 02
        step = {
            "name": "02_postprocess_results",
            "cmd": [py, "3_Code/src/02_postprocess_results.py",
                    "--base_dir", ".", "--run_tag", args.run_tag, "--arm", args.arm, "--provider", args.provider],
        }
        m["steps"].append(step)
        run_cmd(step["cmd"], env=env)

        # 03_5 FINAL (pick best jsonl)
        sel_in = pick_selection_input_jsonl(rdir, args.provider, args.run_tag, args.arm)
        print(f"[Runner] 03_5 input_jsonl -> {sel_in}")

        step = {
            "name": "03_5_select_deck",
            "cmd": [py, "3_Code/src/03_5_select_deck.py",
                    "--mode", "FINAL", "--base_dir", ".", "--run_tag", args.run_tag,
                    "--arm", args.arm, "--seed", str(args.seed), "--provider", args.provider,
                    "--input_jsonl", str(sel_in)],
        }
        m["steps"].append(step)
        run_cmd(step["cmd"], env=env)

    else:
        # S0
        rdir = run_dir(args.base_dir, args.run_tag)
        rdir.mkdir(parents=True, exist_ok=True)

        step = {
            "name": "01_generate_json",
            "cmd": [py, "3_Code/src/01_generate_json.py",
                    "--mode", "S0", "--base_dir", ".", "--run_tag", args.run_tag,
                    "--arm", args.arm, "--provider", args.provider, "--seed", str(args.seed), "--sample", "1"],
        }
        m["steps"].append(step)
        run_cmd(step["cmd"], env=env)

        step = {
            "name": "02_postprocess_results",
            "cmd": [py, "3_Code/src/02_postprocess_results.py",
                    "--base_dir", ".", "--run_tag", args.run_tag, "--arm", args.arm, "--provider", args.provider],
        }
        m["steps"].append(step)
        run_cmd(step["cmd"], env=env)

        sel_in = pick_selection_input_jsonl(rdir, args.provider, args.run_tag, args.arm)
        print(f"[Runner] 03_5 input_jsonl -> {sel_in}")

        step = {
            "name": "03_5_select_deck",
            "cmd": [py, "3_Code/src/03_5_select_deck.py",
                    "--mode", "S0", "--base_dir", ".", "--run_tag", args.run_tag,
                    "--arm", args.arm, "--seed", str(args.seed), "--provider", args.provider,
                    "--input_jsonl", str(sel_in),
                    "--target_total", "12"],
        }
        m["steps"].append(step)
        run_cmd(step["cmd"], env=env)

    m["ts_end"] = now_ts()
    write_manifest(manifest_path(args.base_dir, args.run_tag, args.arm), m)
    print(f"\n[DONE] manifest={manifest_path(args.base_dir, args.run_tag, args.arm)}")


if __name__ == "__main__":
    main()

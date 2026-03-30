#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MeducAI - run_arm_full.py (S0/FINAL runner, minimal CLI)
-------------------------------------------------------
- Enforces mode guardrails (S0 vs FINAL)
- FINAL call order: 03_4_plan_allocation.py -> Step01 -> Step02 -> 03_5 -> ...
- Provider folder removed: outputs are run_tag centric; provider kept only in filenames.
- Provider auto-detection from Step01 output filenames to prevent mismatch.

Minimal CLI (run-to-run only):
  --mode {S0,FINAL}
  --run_tag
  --arm {A,B,...,ALL}  (S0 only meaningful; FINAL requires single arm)
  --total_cards N      (FINAL required)
  --daily_study_cards N (FINAL optional; default from .env)
  --seed

Author: MeducAI
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ----------------------------
# Optional dotenv
# ----------------------------
def load_dotenv_if_exists(base_dir: Path) -> None:
    env_path = base_dir / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(dotenv_path=str(env_path), override=False)
        print(f"✅ Loaded .env from: {env_path}")
    except Exception:
        # Do not hard-fail: environment may already be configured.
        print(f"⚠️ .env found but python-dotenv not available (continuing): {env_path}")


# ----------------------------
# Utilities
# ----------------------------
def now_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def mkdirp(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def eprint(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


def parse_arms(s: str) -> List[str]:
    s = s.strip().upper()
    if s in ("ALL", "A-F", "A,B,C,D,E,F"):
        return ["A", "B", "C", "D", "E", "F"]
    parts = [x.strip().upper() for x in s.split(",") if x.strip()]
    valid = set(list("ABCDEF"))
    bad = [x for x in parts if x not in valid]
    if bad:
        raise ValueError(f"Invalid arms: {bad}. Use comma list of A..F or ALL.")
    return parts


# ----------------------------
# Paths
# ----------------------------
@dataclass
class Paths:
    base_dir: Path
    run_tag: str

    @property
    def gen_dir(self) -> Path:
        return self.base_dir / "2_Data" / "metadata" / "generated" / self.run_tag

    @property
    def log_dir(self) -> Path:
        return self.base_dir / "2_Data" / "logs" / self.run_tag


# ----------------------------
# Subprocess runner
# ----------------------------
def run_cmd(
    cmd: List[str],
    log_path: Path,
    cwd: Optional[Path] = None,
    env: Optional[dict] = None,
) -> None:
    cmd_str = " ".join(shlex.quote(x) for x in cmd)
    header = f"\n[{now_ts()}] [RUN] {cmd_str}\n"

    mkdirp(log_path.parent)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(header)
        f.flush()

        p = subprocess.Popen(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert p.stdout is not None
        for line in p.stdout:
            print(line, end="")
            f.write(line)
        rc = p.wait()
        if rc != 0:
            f.write(f"\n[{now_ts()}] [ERROR] returncode={rc}\n")
            raise SystemExit(rc)


# ----------------------------
# Provider auto-detect (from Step01 outputs)
# ----------------------------
def detect_provider_from_step01(paths: Paths, arm: str) -> str:
    """
    Expected filename (provider only in filename, not folder):
      2_Data/metadata/generated/<RUN_TAG>/output_<provider>_<RUN_TAG>__armX.jsonl
    """
    pattern = f"output_*_{paths.run_tag}__arm{arm}.jsonl"
    matches = sorted(paths.gen_dir.glob(pattern))

    if len(matches) == 0:
        raise FileNotFoundError(
            f"No Step01 output JSONL found for arm {arm}.\n"
            f"Expected: {paths.gen_dir}/{pattern}"
        )
    if len(matches) > 1:
        names = "\n".join(str(m) for m in matches)
        raise RuntimeError(
            f"Multiple Step01 output JSONLs found for arm {arm} (ambiguous provider).\n"
            f"Please clean directory or use fresh run_tag.\nMatches:\n{names}"
        )

    fname = matches[0].name
    prefix = "output_"
    suffix = f"_{paths.run_tag}__arm{arm}.jsonl"
    if not (fname.startswith(prefix) and fname.endswith(suffix)):
        raise RuntimeError(f"Unexpected Step01 output filename: {fname}")

    provider = fname[len(prefix) : -len(suffix)]
    if not provider:
        raise RuntimeError(f"Parsed empty provider from filename: {fname}")
    return provider


# ----------------------------
# Mode guardrails
# ----------------------------
def guardrails(args: argparse.Namespace) -> None:
    mode = args.mode.upper()
    if mode not in ("S0", "FINAL"):
        raise SystemExit("--mode must be S0 or FINAL")

    if mode == "S0":
        if args.total_cards is not None:
            print("[WARN] S0 ignores --total_cards")
        # S0 allows ALL
        return

    # FINAL
    if args.total_cards is None or args.total_cards <= 0:
        raise SystemExit("[FINAL] requires --total_cards > 0")
    if args.arm.strip().upper() in ("ALL", "A-F", "A,B,C,D,E,F") or ("," in args.arm):
        raise SystemExit("[FINAL] --arm must be a single arm (e.g., --arm A).")


# ----------------------------
# FINAL: plan allocation first
# ----------------------------
def run_03_4_plan_allocation(
    *,
    paths: Paths,
    arm: str,
    total_cards: int,
    log_path: Path,
) -> None:
    cmd = [
        sys.executable,
        "3_Code/src/03_4_plan_allocation.py",
        "--base_dir",
        str(paths.base_dir),
        "--run_tag",
        paths.run_tag,
        "--arm",
        arm,
        "--mode",
        "FINAL",
        "--total_cards",
        str(total_cards),
    ]
    run_cmd(cmd, log_path, cwd=paths.base_dir)


# ----------------------------
# Per-arm pipeline
# ----------------------------
def run_one_arm(args: argparse.Namespace, paths: Paths, arm: str) -> Tuple[str, str]:
    """
    S0: Step01 -> Step02 -> 03_5 -> ...
    FINAL: 03_4 -> Step01 -> Step02 -> 03_5 -> ...
    """
    arm = arm.strip().upper()
    mode = args.mode.upper()
    log_path = paths.log_dir / f"arm{arm}.log"

    print(f"\n================ ARM {arm} ({mode}) ================\n")

    # Read provider from env (single source)
    provider_text = os.getenv("PROVIDER_TEXT", "gemini").strip()
    if not provider_text:
        provider_text = "gemini"

    # FINAL: allocation planning first
    if mode == "FINAL":
        run_03_4_plan_allocation(
            paths=paths,
            arm=arm,
            total_cards=int(args.total_cards),
            log_path=log_path,
        )

    # Step01 (Anki generation)
    # Uses your newer Step01 interface:
    step01_cmd = [
        sys.executable,
        "3_Code/src/01_generate_json.py",
        "--mode",
        mode,
        "--base_dir",
        str(paths.base_dir),
        "--run_tag",
        paths.run_tag,
        "--arm",
        arm,
        "--provider",
        provider_text,
        "--seed",
        str(args.seed),
    ]
    run_cmd(step01_cmd, log_path, cwd=paths.base_dir)

    # Detect provider from Step01 outputs (hard safety)
    detected_provider = detect_provider_from_step01(paths, arm)

    # Step02 (postprocess)
    step02_cmd = [
        sys.executable,
        "3_Code/src/02_postprocess_results.py",
        "--provider",
        detected_provider,
        "--run_tag",
        paths.run_tag,
        "--arm",
        arm,
        "--base_dir",
        str(paths.base_dir),
    ]
    run_cmd(step02_cmd, log_path, cwd=paths.base_dir)

    # Step03_5 (select deck)
    # NOTE: In FINAL, selection should eventually become quota-aware.
    # For now, keep old interface; use S0 payload=12, FINAL uses total_cards as a temporary proxy.
    target_total = 12 if mode == "S0" else int(args.total_cards)
    step035_cmd = [
        sys.executable,
        "3_Code/src/03_5_select_deck.py",
        "--provider",
        detected_provider,
        "--run_tag",
        paths.run_tag,
        "--arm",
        arm,
        "--base_dir",
        str(paths.base_dir),
        "--target_total",
        str(target_total),
    ]
    run_cmd(step035_cmd, log_path, cwd=paths.base_dir)

    print(f"\n[DONE] arm={arm} mode={mode} provider={detected_provider}")
    return arm, detected_provider


# ----------------------------
# CLI
# ----------------------------
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="MeducAI runner (minimal CLI). FINAL order: 03_4 -> Step01 -> Step02 -> 03_5"
    )
    ap.add_argument("--base_dir", default=".", help="MeducAI project root directory")
    ap.add_argument("--mode", choices=["S0", "FINAL"], required=True)
    ap.add_argument("--run_tag", required=True)
    ap.add_argument("--arm", required=True, help="S0: A..F or ALL. FINAL: single arm only.")
    ap.add_argument("--total_cards", type=int, default=None, help="FINAL only (required)")
    ap.add_argument("--daily_study_cards", type=int, default=None, help="FINAL only (optional; default in .env)")
    ap.add_argument("--seed", type=int, default=42)
    return ap


def main() -> None:
    args = build_parser().parse_args()
    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        raise FileNotFoundError(f"--base_dir does not exist: {base_dir}")

    # Load .env (non-overriding)
    load_dotenv_if_exists(base_dir)

    # Guardrails
    guardrails(args)

    paths = Paths(base_dir=base_dir, run_tag=args.run_tag)
    mkdirp(paths.log_dir)
    mkdirp(paths.gen_dir)

    arms = parse_arms(args.arm) if args.mode.upper() == "S0" else [args.arm.strip().upper()]

    for a in arms:
        run_one_arm(args, paths, a)

    print(f"\n[ALL DONE] run_tag={paths.run_tag} mode={args.mode} arms={','.join(arms)}")
    print(f"Logs: {paths.log_dir}")
    print(f"Generated: {paths.gen_dir}")


if __name__ == "__main__":
    main()

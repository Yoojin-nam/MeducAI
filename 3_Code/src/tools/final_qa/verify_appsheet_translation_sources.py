#!/usr/bin/env python3
"""
Verify AppSheet export sources:

- Cards.csv front/back must match *baseline* S2 (translated) content
- S5.csv s5_regenerated_front/back for CARD_REGEN must match *regen* S2 (translated) content

This is meant as a lightweight guardrail after generating AppSheet exports.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Allow running as a script from repo root (mirror export_appsheet_tables.py behavior).
_THIS_FILE = Path(__file__).resolve()
_SRC_ROOT = _THIS_FILE.parents[2]  # .../3_Code/src
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

# Import helper functions from the exporter so comparisons match exactly.
from tools.final_qa.export_appsheet_tables import (  # type: ignore
    _build_s2_regenerated_index,
    _derive_card_id,
    _format_front_with_mcq_options,
    _read_jsonl,
    _strip_md_bold,
)


def _discover_s2_paths(run_dir: Path) -> Tuple[Path, Path]:
    """
    Mirror the exporter's discovery rules (baseline prefers __medterm_en, regen prefers __regen__medterm_en).
    Returns: (baseline_s2_path, regen_s2_path)
    """
    run_dir = run_dir.resolve()

    s2_baseline_translated = sorted(run_dir.glob("s2_results__*__medterm_en.jsonl"))
    s2_baseline_translated = [
        p for p in s2_baseline_translated if "__regen" not in p.stem and "__repaired" not in p.stem
    ]
    s2_candidates_all = sorted(run_dir.glob("s2_results__*.jsonl"))
    s2_candidates = [
        p
        for p in s2_candidates_all
        if "__regen" not in p.stem and "__repaired" not in p.stem and "__medterm_en" not in p.stem
    ]
    baseline = (s2_baseline_translated[0] if s2_baseline_translated else (s2_candidates[0] if s2_candidates else None))
    if baseline is None or not baseline.exists():
        raise FileNotFoundError(f"Could not discover baseline S2 JSONL in: {run_dir}")

    s2_regen_translated = sorted(run_dir.glob("s2_results__*__regen__medterm_en.jsonl"))
    s2_regen_original = sorted(run_dir.glob("s2_results__*__regen.jsonl"))
    s2_repaired_candidates = sorted(run_dir.glob("s2_results__*__repaired.jsonl"))
    regen = (
        s2_regen_translated[0]
        if s2_regen_translated
        else (s2_regen_original[0] if s2_regen_original else (s2_repaired_candidates[0] if s2_repaired_candidates else None))
    )
    if regen is None or not regen.exists():
        raise FileNotFoundError(f"Could not discover regen/repaired S2 JSONL in: {run_dir}")

    return baseline, regen


def _build_baseline_card_index(s2_baseline_path: Path) -> Dict[str, Dict[str, str]]:
    """
    Build the expected Cards.csv front/back per card_uid from baseline S2 JSONL,
    matching export_appsheet_tables.py behavior (MCQ option appending + bold stripping).
    """
    out: Dict[str, Dict[str, str]] = {}
    for row in _read_jsonl(s2_baseline_path):
        group_id = row.get("group_id", "") or ""
        entity_id = row.get("entity_id", "") or ""
        if not group_id or not entity_id:
            continue
        anki_cards = row.get("anki_cards") or []
        for idx, c in enumerate(anki_cards):
            card_role = c.get("card_role", "") or ""
            if not card_role:
                continue
            card_type = c.get("card_type", "") or ""
            front = c.get("front", "") or ""
            back = c.get("back", "") or ""
            mcq_options = c.get("options") or []

            front = _format_front_with_mcq_options(card_type=card_type, front=front, options=mcq_options)
            front = _strip_md_bold(front)
            back = _strip_md_bold(back)

            card_id = _derive_card_id(entity_id, card_role, idx)
            card_uid = f"{group_id}::{card_id}"
            out[card_uid] = {"front": front, "back": back}
    return out


def _read_csv_rows(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _sample(items: List[str], n: int, *, seed: int) -> List[str]:
    if n <= 0 or n >= len(items):
        return items
    rng = random.Random(seed)
    return rng.sample(items, n)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_dir", required=True, type=str, help="Run dir containing S2 JSONLs (baseline + regen)")
    parser.add_argument("--out_dir", required=True, type=str, help="Output dir containing Cards.csv and S5.csv")
    parser.add_argument("--baseline_s2", default=None, type=str, help="Optional override baseline S2 JSONL path")
    parser.add_argument("--regen_s2", default=None, type=str, help="Optional override regen S2 JSONL path")
    parser.add_argument("--cards_sample", default=50, type=int, help="How many Cards.csv rows to sample (0=all)")
    parser.add_argument("--regen_sample", default=50, type=int, help="How many CARD_REGEN rows to sample (0=all)")
    parser.add_argument("--seed", default=1337, type=int)
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    cards_csv = out_dir / "Cards.csv"
    s5_csv = out_dir / "S5.csv"
    if not cards_csv.exists():
        raise FileNotFoundError(f"Missing: {cards_csv}")
    if not s5_csv.exists():
        raise FileNotFoundError(f"Missing: {s5_csv}")

    if args.baseline_s2 and args.regen_s2:
        baseline_s2 = Path(args.baseline_s2).resolve()
        regen_s2 = Path(args.regen_s2).resolve()
    else:
        baseline_s2, regen_s2 = _discover_s2_paths(run_dir)

    if not baseline_s2.exists():
        raise FileNotFoundError(f"Missing baseline S2: {baseline_s2}")
    if not regen_s2.exists():
        raise FileNotFoundError(f"Missing regen S2: {regen_s2}")

    print(f"[INFO] baseline_s2: {baseline_s2}")
    print(f"[INFO] regen_s2:    {regen_s2}")
    print(f"[INFO] out_dir:     {out_dir}")

    baseline_by_uid = _build_baseline_card_index(baseline_s2)
    regen_by_uid = _build_s2_regenerated_index(regen_s2)

    cards_rows = _read_csv_rows(cards_csv)
    s5_rows = _read_csv_rows(s5_csv)

    # ---- Verify Cards.csv uses baseline text ----
    cards_uids = [str(r.get("card_uid") or "") for r in cards_rows if (r.get("card_uid") or "").strip()]
    cards_uids = list(dict.fromkeys(cards_uids))  # stable unique
    sample_cards = _sample(cards_uids, int(args.cards_sample), seed=int(args.seed))

    cards_mismatches: List[str] = []
    for uid in sample_cards:
        expected = baseline_by_uid.get(uid)
        if expected is None:
            cards_mismatches.append(f"{uid}: missing in baseline_s2 index")
            continue
        row = next((r for r in cards_rows if str(r.get("card_uid") or "") == uid), None)
        if row is None:
            cards_mismatches.append(f"{uid}: missing in Cards.csv")
            continue
        got_front = str(row.get("front") or "")
        got_back = str(row.get("back") or "")
        if got_front != expected["front"] or got_back != expected["back"]:
            cards_mismatches.append(
                f"{uid}: Cards.csv != baseline_s2 (front_match={got_front==expected['front']}, back_match={got_back==expected['back']})"
            )

    # ---- Verify S5.csv uses regen text for CARD_REGEN ----
    card_regen_rows = [r for r in s5_rows if (str(r.get("s5_decision") or "") == "CARD_REGEN")]
    card_regen_uids = [str(r.get("card_uid") or "") for r in card_regen_rows if (r.get("card_uid") or "").strip()]
    card_regen_uids = list(dict.fromkeys(card_regen_uids))
    sample_regen = _sample(card_regen_uids, int(args.regen_sample), seed=int(args.seed) + 1)

    s5_mismatches: List[str] = []
    for uid in sample_regen:
        expected = regen_by_uid.get(uid)
        if expected is None:
            s5_mismatches.append(f"{uid}: missing in regen_s2 index")
            continue
        row = next((r for r in card_regen_rows if str(r.get("card_uid") or "") == uid), None)
        if row is None:
            s5_mismatches.append(f"{uid}: missing in S5.csv (CARD_REGEN subset)")
            continue
        got_front = str(row.get("s5_regenerated_front") or "")
        got_back = str(row.get("s5_regenerated_back") or "")
        if got_front != expected["front"] or got_back != expected["back"]:
            s5_mismatches.append(
                f"{uid}: S5.csv regenerated != regen_s2 (front_match={got_front==expected['front']}, back_match={got_back==expected['back']})"
            )

    # ---- Report ----
    print("")
    print("[RESULT] Cards.csv vs baseline_s2")
    print(f"- checked: {len(sample_cards)} / {len(cards_uids)} (sample)")
    print(f"- mismatches: {len(cards_mismatches)}")
    if cards_mismatches:
        print("  examples:")
        for x in cards_mismatches[:10]:
            print(f"  - {x}")

    print("")
    print("[RESULT] S5.csv (CARD_REGEN) regenerated fields vs regen_s2")
    print(f"- CARD_REGEN rows: {len(card_regen_uids)}")
    print(f"- checked: {len(sample_regen)} / {len(card_regen_uids)} (sample)")
    print(f"- mismatches: {len(s5_mismatches)}")
    if s5_mismatches:
        print("  examples:")
        for x in s5_mismatches[:10]:
            print(f"  - {x}")

    if cards_mismatches or s5_mismatches:
        raise SystemExit(2)
    print("")
    print("[OK] Verification passed.")


if __name__ == "__main__":
    main()



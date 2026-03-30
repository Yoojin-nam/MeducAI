#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _safe_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def _safe_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    message: str


def _iter_s5_cards(rows: List[Dict[str, Any]]) -> Iterable[Tuple[str, Dict[str, Any]]]:
    for r in rows:
        gid = str(r.get("group_id") or "").strip() or "<missing_group_id>"
        s2 = _safe_dict(r.get("s2_cards_validation"))
        for c in _safe_list(s2.get("cards")):
            if isinstance(c, dict):
                yield (gid, c)


def check_s5_entity_fields(*, s5_path: Path) -> CheckResult:
    rows = _read_jsonl(s5_path)
    if not rows:
        return CheckResult(ok=False, message=f"[FAIL] Missing or empty S5 JSONL: {s5_path}")

    n_cards = 0
    missing_key_counts: Dict[str, int] = {"entity_id": 0, "entity_name": 0, "entity_type": 0, "card_type": 0}
    nullish_counts: Dict[str, int] = {"entity_id": 0, "entity_name": 0}

    for _, c in _iter_s5_cards(rows):
        n_cards += 1
        for k in ("entity_id", "entity_name", "entity_type", "card_type"):
            if k not in c:
                missing_key_counts[k] += 1
        # "present but null/blank" is allowed, but we still report it so you can see coverage.
        for k in ("entity_id", "entity_name"):
            v = c.get(k)
            if v is None:
                nullish_counts[k] += 1
            elif isinstance(v, str) and v.strip() == "":
                nullish_counts[k] += 1

    if n_cards == 0:
        return CheckResult(ok=False, message=f"[FAIL] No cards found in S5 JSONL (s2_cards_validation.cards[]): {s5_path}")

    hard_fail = any(missing_key_counts[k] > 0 for k in ("entity_id", "entity_name"))
    msg = (
        f"S5={s5_path.name}: cards={n_cards} | "
        f"missing_keys(entity_id/entity_name/entity_type/card_type)="
        f"{missing_key_counts['entity_id']}/{missing_key_counts['entity_name']}/"
        f"{missing_key_counts['entity_type']}/{missing_key_counts['card_type']} | "
        f"nullish(entity_id/entity_name)={nullish_counts['entity_id']}/{nullish_counts['entity_name']}"
    )
    if hard_fail:
        return CheckResult(ok=False, message=f"[FAIL] {msg}")
    return CheckResult(ok=True, message=f"[OK] {msg}")


def check_s5r_plan_entities(*, plan_paths: List[Path]) -> CheckResult:
    if not plan_paths:
        return CheckResult(ok=False, message="[FAIL] No s5_repair_plan__*.jsonl files found")

    n_actions = 0
    n_null_entity_id = 0
    n_null_entity_name = 0
    n_both_null = 0

    for p in sorted(plan_paths):
        rows = _read_jsonl(p)
        if not rows:
            continue
        plan = rows[0]
        for a in _safe_list(plan.get("s2_actions")):
            if not isinstance(a, dict):
                continue
            n_actions += 1
            eid = a.get("entity_id")
            enm = a.get("entity_name")
            eid_blank = (eid is None) or (isinstance(eid, str) and eid.strip() == "")
            enm_blank = (enm is None) or (isinstance(enm, str) and enm.strip() == "")
            if eid_blank:
                n_null_entity_id += 1
            if enm_blank:
                n_null_entity_name += 1
            if eid_blank and enm_blank:
                n_both_null += 1

    if n_actions == 0:
        return CheckResult(ok=False, message="[FAIL] No s2_actions found in repair plans")

    # For the goal of entity-wise repair, we want at least one of (id/name) populated.
    ok = (n_both_null == 0)
    msg = f"plans={len(plan_paths)} | s2_actions={n_actions} | both_null={n_both_null} | null_entity_id={n_null_entity_id} | null_entity_name={n_null_entity_name}"
    return CheckResult(ok=ok, message=("[OK] " if ok else "[FAIL] ") + msg)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Check S5 entity metadata + S5R plan entity targeting for a run_tag.")
    p.add_argument("--run_tag", required=True, type=str, help="e.g. FINAL_DISTRIBUTION_S4TEST_REALISTIC_20260101_000544")
    p.add_argument("--arm", default="G", type=str, help="Arm letter, e.g. G")
    p.add_argument("--base_dir", default=None, type=str, help="Repo root; defaults to auto-detect from this script location")
    args = p.parse_args(argv)

    base_dir = Path(args.base_dir).resolve() if args.base_dir else Path(__file__).resolve().parents[2]
    run_dir = base_dir / "2_Data" / "metadata" / "generated" / str(args.run_tag)
    arm = str(args.arm).strip()

    baseline = run_dir / f"s5_validation__arm{arm}.jsonl"
    postrepair = run_dir / f"s5_validation__arm{arm}__postrepair.jsonl"
    plans = list(run_dir.glob(f"s5_repair_plan__arm{arm}__group*.jsonl"))

    print(f"Run dir: {run_dir}")
    print(f"Arm: {arm}")

    r1 = check_s5_entity_fields(s5_path=baseline)
    print(r1.message)

    if postrepair.exists():
        r2 = check_s5_entity_fields(s5_path=postrepair)
        print(r2.message)
    else:
        r2 = CheckResult(ok=True, message=f"[SKIP] Postrepair S5 not found: {postrepair.name}")
        print(r2.message)

    r3 = check_s5r_plan_entities(plan_paths=plans)
    print(r3.message)

    ok = bool(r1.ok and r2.ok and r3.ok)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())



#!/usr/bin/env python3
"""
S6 Export Gate — Promotion decision (baseline vs repaired) per group_id.

Generates `s6_export_manifest__arm{arm}.json`, which downstream exporters can use
to decide, per group_id, whether to export baseline artifacts or repaired artifacts.

Default policy (safety-first, conservative):
  - Promote repaired ONLY if:
      1) At least one rater marked `accept_ai_correction == ACCEPT` for the group
         (derived from Ratings.csv `card_uid = "{group_id}::{card_id}"`)
      2) No rater marked an explicit rejection value for the group
      3) Postrepair S5 validation exists AND is non-blocking (table + all cards)
  - Otherwise: fallback to baseline.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]


def _parse_iso8601(ts: str) -> Optional[datetime]:
    s = (ts or "").strip()
    if not s:
        return None
    try:
        # Handle 'Z' suffix
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _extract_group_id_from_card_uid(card_uid: str) -> Optional[str]:
    s = (card_uid or "").strip()
    if not s:
        return None
    # card_uid is stable: "{group_id}::{card_id}"
    if "::" in s:
        gid = s.split("::", 1)[0].strip()
        return gid or None
    return None


def _normalize_accept_value(v: str) -> str:
    return (v or "").strip().upper()


def _is_accept(v: str) -> bool:
    s = _normalize_accept_value(v)
    return s in ("ACCEPT", "YES", "Y", "TRUE", "1")


def _is_reject(v: str) -> bool:
    """
    Treat these as explicit rejection / non-promotion signals.
    Anything else (including empty) is treated as "no decision".
    """
    s = _normalize_accept_value(v)
    return s in ("REJECT", "DECLINE", "NO", "N", "FALSE", "0")


@dataclass
class AcceptStats:
    n_rows_with_value: int = 0
    n_accept: int = 0
    n_reject: int = 0
    sample_values: Tuple[str, ...] = ()


def _compute_accept_stats_by_group(ratings_rows: Iterable[Dict[str, str]]) -> Dict[str, AcceptStats]:
    out: Dict[str, AcceptStats] = {}
    for row in ratings_rows:
        gid = _extract_group_id_from_card_uid(row.get("card_uid", ""))
        if not gid:
            continue
        v = (row.get("accept_ai_correction") or "").strip()
        if not v:
            continue

        st = out.get(gid) or AcceptStats()
        st.n_rows_with_value += 1
        if _is_accept(v):
            st.n_accept += 1
        elif _is_reject(v):
            st.n_reject += 1

        # keep small sample for audit/debug
        if len(st.sample_values) < 5:
            st.sample_values = tuple(list(st.sample_values) + [v])
        out[gid] = st
    return out


def _load_latest_s5_by_group(s5_jsonl_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Load S5 JSONL and return latest record per group_id by `validation_timestamp`.
    """
    out: Dict[str, Tuple[Optional[datetime], Dict[str, Any]]] = {}
    if not s5_jsonl_path.exists():
        return {}

    with s5_jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            gid = str(rec.get("group_id") or "").strip()
            if not gid:
                continue
            ts = _parse_iso8601(str(rec.get("validation_timestamp") or ""))
            prev = out.get(gid)
            if prev is None:
                out[gid] = (ts, rec)
                continue
            prev_ts, _prev_rec = prev
            # If timestamps parse, choose the latest. If not, keep the first seen.
            if prev_ts is None and ts is not None:
                out[gid] = (ts, rec)
            elif prev_ts is not None and ts is not None and ts > prev_ts:
                out[gid] = (ts, rec)

    return {gid: rec for gid, (_ts, rec) in out.items()}


def _postrepair_is_non_blocking(s5_group_record: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """
    Conservative "non-blocking" check based on S5 output schema.
    Returns (is_ok, audit_details).
    """
    s1 = s5_group_record.get("s1_table_validation") or {}
    s2 = s5_group_record.get("s2_cards_validation") or {}
    cards = s2.get("cards") or []
    summary = s2.get("summary") or {}

    table_blocking = bool(s1.get("blocking_error", False))
    card_blocking_count = int(summary.get("blocking_errors", 0) or 0)

    # Additional safety scan: any card image blocking/safety flag should block promotion.
    image_blocking = 0
    image_safety = 0
    if isinstance(cards, list):
        for c in cards:
            if not isinstance(c, dict):
                continue
            if bool(c.get("blocking_error")):
                # already counted in summary, but keep conservative.
                pass
            civ = c.get("card_image_validation") or {}
            if isinstance(civ, dict):
                if bool(civ.get("blocking_error")):
                    image_blocking += 1
                if bool(civ.get("safety_flag")):
                    image_safety += 1

    ok = (not table_blocking) and (card_blocking_count == 0) and (image_blocking == 0) and (image_safety == 0)
    audit = {
        "table_blocking_error": table_blocking,
        "card_blocking_errors": card_blocking_count,
        "image_blocking_errors": image_blocking,
        "image_safety_flags": image_safety,
    }
    return ok, audit


def _decide_use_repaired(
    *,
    accept_stats: Optional[AcceptStats],
    accept_policy: str,
    min_accept_count: int,
    postrepair_ok: bool,
) -> Tuple[bool, str]:
    if not postrepair_ok:
        return False, "postrepair_blocking_or_missing"

    if accept_stats is None:
        return False, "no_accept_decision_rows"

    if accept_policy == "any_accept_no_reject":
        if accept_stats.n_reject > 0:
            return False, "explicit_reject_present"
        if accept_stats.n_accept >= min_accept_count:
            return True, "accepted_and_postrepair_ok"
        return False, "no_accept"

    if accept_policy == "all_accept":
        if accept_stats.n_rows_with_value <= 0:
            return False, "no_accept_rows"
        if accept_stats.n_reject > 0:
            return False, "explicit_reject_present"
        if accept_stats.n_accept == accept_stats.n_rows_with_value and accept_stats.n_accept >= min_accept_count:
            return True, "all_accept_and_postrepair_ok"
        return False, "not_all_accept"

    raise ValueError(f"Unknown accept_policy: {accept_policy}")


def main() -> None:
    p = argparse.ArgumentParser(description="S6 Export Gate (baseline vs repaired manifest generator)")
    p.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    p.add_argument("--run_tag", type=str, required=True, help="Run tag")
    p.add_argument("--arm", type=str, required=True, help="Arm identifier (A-F) for the repaired candidate arm")
    p.add_argument("--ratings_csv", type=str, required=True, help="Path to AppSheet Ratings.csv export")
    p.add_argument(
        "--s5_postrepair_jsonl",
        type=str,
        default=None,
        help="Path to postrepair S5 JSONL (default: 2_Data/metadata/generated/<run_tag>/s5_validation__arm<arm>__postrepair.jsonl)",
    )
    p.add_argument(
        "--out_path",
        type=str,
        default=None,
        help="Output manifest path (default: 2_Data/metadata/generated/<run_tag>/s6_export_manifest__arm<arm>.json)",
    )
    p.add_argument(
        "--accept_policy",
        type=str,
        default="any_accept_no_reject",
        choices=["any_accept_no_reject", "all_accept"],
        help="How to interpret accept_ai_correction rows per group (default: any_accept_no_reject).",
    )
    p.add_argument(
        "--min_accept_count",
        type=int,
        default=1,
        help="Minimum number of ACCEPT rows required to promote (default: 1).",
    )

    args = p.parse_args()

    base_dir = Path(args.base_dir).resolve()
    run_tag = str(args.run_tag).strip()
    arm = str(args.arm).strip().upper()

    ratings_csv = Path(args.ratings_csv).expanduser().resolve()
    if not ratings_csv.exists():
        raise FileNotFoundError(f"Ratings.csv not found: {ratings_csv}")

    gen_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    s5_postrepair_jsonl = (
        Path(args.s5_postrepair_jsonl).expanduser().resolve()
        if args.s5_postrepair_jsonl
        else (gen_dir / f"s5_validation__arm{arm}__postrepair.jsonl")
    )
    out_path = (
        Path(args.out_path).expanduser().resolve()
        if args.out_path
        else (gen_dir / f"s6_export_manifest__arm{arm}.json")
    )

    print(f"[S6Gate] ratings_csv={ratings_csv}")
    print(f"[S6Gate] s5_postrepair_jsonl={s5_postrepair_jsonl}")
    print(f"[S6Gate] out_path={out_path}")

    ratings_rows = _read_csv_rows(ratings_csv)
    accept_by_group = _compute_accept_stats_by_group(ratings_rows)

    s5_post_by_group = _load_latest_s5_by_group(s5_postrepair_jsonl)

    all_group_ids = sorted(set(accept_by_group.keys()) | set(s5_post_by_group.keys()))
    entries: List[Dict[str, Any]] = []

    n_promote = 0
    for gid in all_group_ids:
        a = accept_by_group.get(gid)
        s5p = s5_post_by_group.get(gid)
        if s5p is None:
            post_ok = False
            post_audit = {"present": False}
        else:
            post_ok, post_audit_core = _postrepair_is_non_blocking(s5p)
            post_audit = {
                "present": True,
                "s5_snapshot_id": s5p.get("s5_snapshot_id", ""),
                "validation_timestamp": s5p.get("validation_timestamp", ""),
                **post_audit_core,
            }

        use_repaired, reason = _decide_use_repaired(
            accept_stats=a,
            accept_policy=args.accept_policy,
            min_accept_count=int(args.min_accept_count),
            postrepair_ok=post_ok,
        )
        if use_repaired:
            n_promote += 1

        entries.append(
            {
                "group_id": gid,
                "use_repaired": bool(use_repaired),
                "decision_reason": reason,
                "accept_stats": (
                    {
                        "n_rows_with_value": a.n_rows_with_value,
                        "n_accept": a.n_accept,
                        "n_reject": a.n_reject,
                        "sample_values": list(a.sample_values),
                    }
                    if a is not None
                    else {"n_rows_with_value": 0, "n_accept": 0, "n_reject": 0, "sample_values": []}
                ),
                "postrepair_audit": post_audit,
            }
        )

    manifest = {
        "schema_version": "S6_EXPORT_MANIFEST_v1.0",
        "created_utc": datetime.utcnow().isoformat() + "Z",
        "run_tag": run_tag,
        "arm": arm,
        "policy": {
            "accept_policy": args.accept_policy,
            "min_accept_count": int(args.min_accept_count),
            "requires_postrepair_non_blocking": True,
        },
        "sources": {
            "ratings_csv": str(ratings_csv),
            "s5_postrepair_jsonl": str(s5_postrepair_jsonl),
        },
        "summary": {
            "n_groups_total": len(all_group_ids),
            "n_groups_promote_repaired": n_promote,
            "n_groups_fallback_baseline": len(all_group_ids) - n_promote,
        },
        "entries": entries,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(
        f"[S6Gate] Done. Promote repaired: {n_promote}/{len(all_group_ids)} groups. Wrote: {out_path}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[S6Gate] FAIL: {e}", file=sys.stderr)
        raise



#!/usr/bin/env python3
"""
S5 S1 재평가 결과를 기존 S2 결과와 병합하는 스크립트.

사용법:
    python3 merge_s5_s1_with_existing_s2.py \
        --s1_new PATH_TO_NEW_S1_PARTIAL \
        --s5_existing PATH_TO_EXISTING_S5_VALIDATION \
        --output PATH_TO_OUTPUT

이 스크립트는:
1. 새로운 S1 partial 파일에서 s1_table_validation (인포그래픽 포함) 로드
2. 기존 S5 validation 파일에서 s2_cards_validation 로드
3. 두 결과를 병합하여 새로운 S5 validation 파일 생성

S2 API 호출 없이 S1 재평가 결과만 반영 가능.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Load JSONL file into list of dicts."""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def save_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    """Save list of dicts to JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def merge_s5_results(
    s1_new_rows: List[Dict[str, Any]],
    s5_existing_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Merge new S1 results with existing S2 results.
    
    - Takes s1_table_validation from s1_new_rows
    - Takes s2_cards_validation from s5_existing_rows
    - Combines into merged result
    """
    # Index existing S5 by group_id
    existing_by_group: Dict[str, Dict[str, Any]] = {}
    for row in s5_existing_rows:
        gid = row.get("group_id", "")
        if gid:
            existing_by_group[gid] = row
    
    # Index new S1 by group_id
    new_s1_by_group: Dict[str, Dict[str, Any]] = {}
    for row in s1_new_rows:
        gid = row.get("group_id", "")
        if gid:
            new_s1_by_group[gid] = row
    
    merged_rows = []
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    for gid, existing in existing_by_group.items():
        new_s1 = new_s1_by_group.get(gid)
        
        if new_s1:
            # Merge: new S1 + existing S2
            merged = {
                "schema_version": existing.get("schema_version", "S5_VALIDATION_v1.0"),
                "run_tag": existing.get("run_tag"),
                "group_id": gid,
                "arm": existing.get("arm"),
                "validation_timestamp": now_iso,
                "s5_is_postrepair": existing.get("s5_is_postrepair", False),
                "s5_mode": "merged_s1_s2",
                "inputs": existing.get("inputs", {}),
                "outputs": existing.get("outputs", {}),
                "s5_prompt_bundle": new_s1.get("s5_prompt_bundle", existing.get("s5_prompt_bundle", {})),
                "s5_model_info": {
                    **existing.get("s5_model_info", {}),
                    "s1_table_model": new_s1.get("s5_model_info", {}).get("s1_table_model"),
                },
                "s1_table_validation": new_s1.get("s1_table_validation", {}),
                "s2_cards_validation": existing.get("s2_cards_validation", {}),
                "s5_snapshot_id": f"merged_{gid[:8]}_{now_iso[:10]}",
                "s5_timing": existing.get("s5_timing", {}),
            }
            merged_rows.append(merged)
        else:
            # No new S1, keep existing as-is
            merged_rows.append(existing)
    
    # Sort by group_id for consistency
    merged_rows.sort(key=lambda x: x.get("group_id", ""))
    
    return merged_rows


def main():
    parser = argparse.ArgumentParser(
        description="Merge new S5 S1 results with existing S2 results"
    )
    parser.add_argument(
        "--s1_new",
        type=Path,
        required=True,
        help="Path to new S1 partial JSONL (from s1_only re-run)",
    )
    parser.add_argument(
        "--s5_existing",
        type=Path,
        required=True,
        help="Path to existing S5 validation JSONL (with S2 results)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to output merged JSONL",
    )
    
    args = parser.parse_args()
    
    print(f"Loading new S1 results from: {args.s1_new}")
    s1_new_rows = load_jsonl(args.s1_new)
    print(f"  Loaded {len(s1_new_rows)} groups")
    
    print(f"Loading existing S5 results from: {args.s5_existing}")
    s5_existing_rows = load_jsonl(args.s5_existing)
    print(f"  Loaded {len(s5_existing_rows)} groups")
    
    print("Merging results...")
    merged_rows = merge_s5_results(s1_new_rows, s5_existing_rows)
    print(f"  Merged {len(merged_rows)} groups")
    
    print(f"Saving merged results to: {args.output}")
    save_jsonl(args.output, merged_rows)
    
    # Summary statistics
    total_groups = len(merged_rows)
    groups_with_new_s1 = sum(1 for r in merged_rows if r.get("s5_mode") == "merged_s1_s2")
    print(f"\n=== Summary ===")
    print(f"Total groups: {total_groups}")
    print(f"Groups with updated S1: {groups_with_new_s1}")
    print(f"Groups unchanged: {total_groups - groups_with_new_s1}")
    print(f"Output saved to: {args.output}")


if __name__ == "__main__":
    main()


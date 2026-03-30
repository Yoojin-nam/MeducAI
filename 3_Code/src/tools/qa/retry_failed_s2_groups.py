#!/usr/bin/env python3
"""
Retry failed S2 groups from a run.

This script:
1. Identifies groups that succeeded in S1 but failed in S2
2. Retries only the failed groups for specified arms

Usage:
    python 3_Code/src/tools/qa/retry_failed_s2_groups.py --run_tag S0_QA_final_time --arms A B
"""

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.path_resolver import resolve_s2_results_path


def load_selected_groups(base_dir: Path, run_tag: str) -> List[Dict[str, str]]:
    """Load selected groups from the run."""
    selected_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / "selected_18_groups.json"
    if not selected_path.exists():
        raise FileNotFoundError(f"Selected groups file not found: {selected_path}")
    
    with open(selected_path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_failed_s2_groups(base_dir: Path, run_tag: str, arm: str) -> Set[str]:
    """
    Find groups that succeeded in S1 but failed in S2.
    
    Returns set of group_ids that:
    - Are in selected groups
    - Have S1 results (in stage1_struct)
    - But don't have S2 results (in s2_results)
    """
    # Load selected groups
    selected_groups = load_selected_groups(base_dir, run_tag)
    selected_group_ids = {g["group_id"] for g in selected_groups}
    
    # Load groups with S1 results
    stage1_struct_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"stage1_struct__arm{arm}.jsonl"
    s1_successful_group_ids = set()
    if stage1_struct_path.exists():
        with open(stage1_struct_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    group_id = record.get("group_id", "").strip()
                    if group_id:
                        s1_successful_group_ids.add(group_id)
                except json.JSONDecodeError:
                    continue
    
    # Load groups with S2 results
    out_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    s2_results_path = resolve_s2_results_path(out_dir, arm)
    s2_successful_group_ids = set()
    if s2_results_path.exists():
        with open(s2_results_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    group_id = record.get("group_id", "").strip()
                    if group_id:
                        s2_successful_group_ids.add(group_id)
                except json.JSONDecodeError:
                    continue
    
    # Failed S2 groups = selected + S1 success - S2 success
    failed_s2_group_ids = (selected_group_ids & s1_successful_group_ids) - s2_successful_group_ids
    
    return failed_s2_group_ids


def get_group_info(base_dir: Path, group_id: str) -> Dict[str, str]:
    """Get group info from groups_canonical.csv."""
    csv_path = base_dir / "2_Data" / "metadata" / "groups_canonical.csv"
    if not csv_path.exists():
        return {}
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("group_id", "").strip() == group_id:
                return {
                    "group_id": row.get("group_id", "").strip(),
                    "group_key": row.get("group_key", "").strip(),
                    "specialty": row.get("specialty", "").strip(),
                    "anatomy": row.get("anatomy", "").strip(),
                    "modality_or_type": row.get("modality_or_type", "").strip(),
                    "category": row.get("category", "").strip(),
                }
    return {}


def load_existing_s2_results(base_dir: Path, run_tag: str, arm: str) -> Dict[str, dict]:
    """Load existing s2_results to preserve them."""
    out_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    s2_results_path = resolve_s2_results_path(out_dir, arm)
    
    existing = {}
    if s2_results_path.exists():
        with open(s2_results_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    group_id = record.get("group_id", "").strip()
                    if group_id:
                        # S2 results are entity-level, so we need to group by group_id
                        if group_id not in existing:
                            existing[group_id] = []
                        existing[group_id].append(record)
                except json.JSONDecodeError:
                    continue
    
    return existing


def merge_s2_results(base_dir: Path, run_tag: str, arm: str, existing: Dict[str, List[dict]]):
    """Merge existing S2 results with new results from retry."""
    out_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    s2_results_path = resolve_s2_results_path(out_dir, arm)
    
    # Load new results
    new_results = {}
    if s2_results_path.exists():
        with open(s2_results_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    group_id = record.get("group_id", "").strip()
                    if group_id:
                        if group_id not in new_results:
                            new_results[group_id] = []
                        new_results[group_id].append(record)
                except json.JSONDecodeError:
                    continue
    
    # Merge: existing + new (new overwrites existing for retried groups)
    merged = {**existing, **new_results}
    
    # Write merged results back (all entities for all groups)
    with open(s2_results_path, "w", encoding="utf-8") as f:
        # Sort by group_id for consistency
        for group_id in sorted(merged.keys()):
            for entity_record in merged[group_id]:
                f.write(json.dumps(entity_record, ensure_ascii=False) + "\n")
    
    return merged


def retry_group(
    base_dir: Path,
    run_tag: str,
    arm: str,
    group_id: str,
    group_key: str,
    existing_results: Dict[str, List[dict]],
) -> tuple[bool, Dict[str, List[dict]]]:
    """Retry a single group's S2, preserving existing results."""
    print(f"\n  Retrying S2: {group_id} ({group_key[:60]}...)")
    
    # Backup existing results (excluding the group we're retrying)
    backup_results = {k: v for k, v in existing_results.items() if k != group_id}
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "01_generate_json.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
        "--mode", "S0",
        "--stage", "2",
        "--only_group_id", group_id,
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=base_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        
        if result.returncode == 0:
            # Merge results: backup + new
            merged = merge_s2_results(base_dir, run_tag, arm, backup_results)
            
            # Verify the group is now in the merged output
            if group_id in merged and len(merged[group_id]) > 0:
                entity_count = len(merged[group_id])
                print(f"    ✅ Success: {group_id} now in s2_results ({entity_count} entities)")
                return True, merged
            else:
                print(f"    ⚠️  Command succeeded but group not found in merged output")
                return False, merged
        else:
            print(f"    ❌ Failed (return code {result.returncode})")
            if result.stderr:
                error_preview = result.stderr[:500]
                print(f"    Error preview: {error_preview}...")
            
            # Restore backup if retry failed
            merged = merge_s2_results(base_dir, run_tag, arm, existing_results)
            return False, merged
            
    except Exception as e:
        print(f"    ❌ Exception: {e}")
        # Restore backup on exception
        merged = merge_s2_results(base_dir, run_tag, arm, existing_results)
        return False, merged


def main():
    parser = argparse.ArgumentParser(
        description="Retry failed S2 groups from a run"
    )
    parser.add_argument(
        "--base_dir",
        type=str,
        default=".",
        help="Base directory (default: current directory)"
    )
    parser.add_argument(
        "--run_tag",
        type=str,
        required=True,
        help="Run tag (e.g., S0_QA_final_time)"
    )
    parser.add_argument(
        "--arms",
        type=str,
        nargs="+",
        default=["A", "B", "C", "D", "E", "F"],
        help="Arms to retry (default: all arms A-F)"
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Show what would be retried without actually running"
    )
    
    args = parser.parse_args()
    base_dir = Path(args.base_dir).resolve()
    
    print("=" * 70)
    print("S2 Failed Groups Retry")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {args.run_tag}")
    print(f"Arms: {', '.join(args.arms)}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'EXECUTE'}")
    print("=" * 70)
    
    all_failed = {}
    total_failed = 0
    
    # Find failed groups for each arm
    for arm in args.arms:
        print(f"\n[Arm {arm}] Checking for failed S2 groups...")
        failed_group_ids = find_failed_s2_groups(base_dir, args.run_tag, arm)
        
        if failed_group_ids:
            print(f"  Found {len(failed_group_ids)} failed S2 groups:")
            all_failed[arm] = []
            for group_id in sorted(failed_group_ids):
                group_info = get_group_info(base_dir, group_id)
                group_key = group_info.get("group_key", "unknown")
                print(f"    - {group_id}: {group_key[:60]}...")
                all_failed[arm].append({
                    "group_id": group_id,
                    "group_key": group_key,
                    "group_info": group_info,
                })
            total_failed += len(failed_group_ids)
        else:
            print(f"  ✅ No failed S2 groups found")
    
    if total_failed == 0:
        print("\n" + "=" * 70)
        print("✅ No failed S2 groups to retry!")
        print("=" * 70)
        return 0
    
    print("\n" + "=" * 70)
    print(f"Summary: {total_failed} failed S2 groups found across {len(all_failed)} arms")
    print("=" * 70)
    
    if args.dry_run:
        print("\n[DRY RUN] Would retry the above groups")
        return 0
    
    # Retry failed groups
    print("\n" + "=" * 70)
    print("Retrying failed S2 groups...")
    print("=" * 70)
    
    success_count = 0
    fail_count = 0
    
    for arm, failed_groups in all_failed.items():
        print(f"\n[Arm {arm}] Retrying {len(failed_groups)} groups...")
        
        # Load existing results to preserve them
        existing_results = load_existing_s2_results(base_dir, args.run_tag, arm)
        existing_group_count = len(existing_results)
        total_entities = sum(len(entities) for entities in existing_results.values())
        print(f"  Preserving {existing_group_count} existing groups ({total_entities} entities)")
        
        current_results = existing_results.copy()
        
        for group in failed_groups:
            success, current_results = retry_group(
                base_dir=base_dir,
                run_tag=args.run_tag,
                arm=arm,
                group_id=group["group_id"],
                group_key=group["group_key"],
                existing_results=current_results,
            )
            if success:
                success_count += 1
            else:
                fail_count += 1
    
    print("\n" + "=" * 70)
    print("Retry Summary")
    print("=" * 70)
    print(f"Total failed S2 groups: {total_failed}")
    print(f"Successfully retried: {success_count}")
    print(f"Still failed: {fail_count}")
    print("=" * 70)
    
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())


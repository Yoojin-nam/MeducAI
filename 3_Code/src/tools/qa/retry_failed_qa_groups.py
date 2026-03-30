#!/usr/bin/env python3
"""
Retry Failed QA Groups

This script automatically identifies groups that failed in QA dataset generation
and retries only those groups.

It checks:
1. S1 results: Which groups are missing from stage1_struct__arm*.jsonl
2. S2 results: Which groups are missing from s2_results__arm*.jsonl

Usage:
    # Retry all failed groups (S1 and S2)
    python 3_Code/Scripts/retry_failed_qa_groups.py \
        --base_dir . \
        --run_tag S0_QA_fixed_v4 \
        --arms A B C D E F

    # Retry only S1 failures
    python 3_Code/Scripts/retry_failed_qa_groups.py \
        --base_dir . \
        --run_tag S0_QA_fixed_v4 \
        --stage 1

    # Retry only S2 failures
    python 3_Code/Scripts/retry_failed_qa_groups.py \
        --base_dir . \
        --run_tag S0_QA_fixed_v4 \
        --stage 2
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.path_resolver import resolve_s2_results_path

ARMS = ["A", "B", "C", "D", "E", "F"]


def load_selected_groups(base_dir: Path, run_tag: str) -> List[Dict[str, str]]:
    """Load the selected 18 groups from QA run."""
    selected_file = base_dir / "2_Data" / "metadata" / "generated" / run_tag / "selected_18_groups.json"
    if not selected_file.exists():
        raise FileNotFoundError(
            f"Selected groups file not found: {selected_file}\n"
            f"Make sure you ran run_s0_qa_6arm.py first."
        )
    
    with open(selected_file, "r", encoding="utf-8") as f:
        return json.load(f)


def is_process_running(process_name: str = "01_generate_json.py") -> bool:
    """Check if 01_generate_json.py is currently running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", process_name],
            capture_output=True,
            text=True
        )
        return result.returncode == 0 and len(result.stdout.strip()) > 0
    except Exception:
        # If pgrep is not available, try ps
        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True
            )
            return process_name in result.stdout
        except Exception:
            return False


def get_file_age_seconds(file_path: Path) -> float:
    """Get file age in seconds (time since last modification)."""
    if not file_path.exists():
        return float('inf')
    return time.time() - file_path.stat().st_mtime


def get_s1_group_ids(base_dir: Path, run_tag: str, arm: str, min_age_seconds: float = 60.0) -> Tuple[Set[str], Set[str]]:
    """
    Get set of group_ids that exist in S1 output.
    
    Returns:
        (found_ids, potentially_running_ids): 
        - found_ids: Groups that are definitely completed
        - potentially_running_ids: Groups that might still be running (recently modified)
    """
    s1_file = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"stage1_struct__arm{arm}.jsonl"
    if not s1_file.exists():
        return set(), set()
    
    file_age = get_file_age_seconds(s1_file)
    is_recently_modified = file_age < min_age_seconds
    
    found_ids = set()
    with open(s1_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                gid = data.get("group_id")
                if gid:
                    found_ids.add(gid)
            except Exception:
                continue
    
    # If file was recently modified and process might be running, mark all as potentially running
    potentially_running = found_ids.copy() if (is_recently_modified and is_process_running()) else set()
    
    return found_ids, potentially_running


def get_s2_group_ids(base_dir: Path, run_tag: str, arm: str, min_age_seconds: float = 60.0) -> Tuple[Set[str], Set[str]]:
    """
    Get set of group_ids that exist in S2 output.
    
    Returns:
        (found_ids, potentially_running_ids): 
        - found_ids: Groups that are definitely completed
        - potentially_running_ids: Groups that might still be running (recently modified)
    """
    out_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    s2_file = resolve_s2_results_path(out_dir, arm)
    if not s2_file.exists():
        return set(), set()
    
    file_age = get_file_age_seconds(s2_file)
    is_recently_modified = file_age < min_age_seconds
    
    found_ids = set()
    with open(s2_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                gid = data.get("group_id")
                if gid:
                    found_ids.add(gid)
            except Exception:
                continue
    
    # If file was recently modified and process might be running, mark all as potentially running
    potentially_running = found_ids.copy() if (is_recently_modified and is_process_running()) else set()
    
    return found_ids, potentially_running


def find_failed_groups(
    base_dir: Path,
    run_tag: str,
    arms: List[str],
    stage: str = "both",
    min_age_seconds: float = 60.0,
) -> Tuple[Dict[str, List[Dict[str, str]]], Dict[str, List[Dict[str, str]]], Dict[str, List[Dict[str, str]]], Dict[str, List[Dict[str, str]]]]:
    """
    Find failed groups for each arm.
    
    Returns:
        (s1_failed, s2_failed, s1_potentially_running, s2_potentially_running): 
        - s1_failed/s2_failed: Definitely failed groups
        - s1_potentially_running/s2_potentially_running: Groups that might still be running
    """
    selected = load_selected_groups(base_dir, run_tag)
    selected_ids = {g["group_id"] for g in selected}
    
    s1_failed = {}
    s2_failed = {}
    s1_potentially_running = {}
    s2_potentially_running = {}
    
    # Check if process is running
    process_running = is_process_running()
    if process_running:
        print("⚠️  WARNING: 01_generate_json.py process is currently running!")
        print("   Groups in recently modified files may still be processing.")
        print("   Use --min_age_seconds to adjust the threshold.\n")
    
    for arm in arms:
        if stage in ("1", "both"):
            s1_found, s1_running = get_s1_group_ids(base_dir, run_tag, arm, min_age_seconds)
            s1_missing_ids = selected_ids - s1_found
            # Exclude potentially running groups from failed list
            s1_definitely_failed_ids = s1_missing_ids - {g["group_id"] for g in selected if g["group_id"] in s1_running}
            s1_failed[arm] = [g for g in selected if g["group_id"] in s1_definitely_failed_ids]
            s1_potentially_running[arm] = [g for g in selected if g["group_id"] in s1_running]
        
        if stage in ("2", "both"):
            s2_found, s2_running = get_s2_group_ids(base_dir, run_tag, arm, min_age_seconds)
            s2_missing_ids = selected_ids - s2_found
            # Exclude potentially running groups from failed list
            s2_definitely_failed_ids = s2_missing_ids - {g["group_id"] for g in selected if g["group_id"] in s2_running}
            s2_failed[arm] = [g for g in selected if g["group_id"] in s2_definitely_failed_ids]
            s2_potentially_running[arm] = [g for g in selected if g["group_id"] in s2_running]
    
    return s1_failed, s2_failed, s1_potentially_running, s2_potentially_running


def retry_s1_for_groups(
    base_dir: Path,
    run_tag: str,
    arm: str,
    failed_groups: List[Dict[str, str]],
) -> bool:
    """Retry S1 for failed groups."""
    if not failed_groups:
        return True
    
    print(f"\n[Arm {arm}] Retrying S1 for {len(failed_groups)} failed groups...")
    
    # Create a temporary file with failed group_keys
    temp_group_keys_file = base_dir / "2_Data" / "metadata" / f"temp_retry_s1_{run_tag}_{arm}.txt"
    temp_group_keys_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(temp_group_keys_file, "w", encoding="utf-8") as f:
        for group in failed_groups:
            f.write(f"{group['group_key']}\n")
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "01_generate_json.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
        "--mode", "S0",
        "--stage", "1",
        "--only_group_keys_file", str(temp_group_keys_file),
        "--sample", str(len(failed_groups)),
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=base_dir,
            check=True
        )
        
        # Clean up temp file
        if temp_group_keys_file.exists():
            temp_group_keys_file.unlink()
        
        print(f"  ✅ S1 retry completed for Arm {arm}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ S1 retry failed for Arm {arm} (exit code: {e.returncode})")
        if temp_group_keys_file.exists():
            temp_group_keys_file.unlink()
        return False
    except Exception as e:
        print(f"  ❌ Error retrying S1 for Arm {arm}: {e}")
        if temp_group_keys_file.exists():
            temp_group_keys_file.unlink()
        return False


def retry_s2_for_groups(
    base_dir: Path,
    run_tag: str,
    arm: str,
    failed_groups: List[Dict[str, str]],
) -> bool:
    """Retry S2 for failed groups."""
    if not failed_groups:
        return True
    
    print(f"\n[Arm {arm}] Retrying S2 for {len(failed_groups)} failed groups...")
    
    # Create a temporary file with failed group_keys
    temp_group_keys_file = base_dir / "2_Data" / "metadata" / f"temp_retry_s2_{run_tag}_{arm}.txt"
    temp_group_keys_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(temp_group_keys_file, "w", encoding="utf-8") as f:
        for group in failed_groups:
            f.write(f"{group['group_key']}\n")
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "01_generate_json.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
        "--mode", "S0",
        "--stage", "2",
        "--only_group_keys_file", str(temp_group_keys_file),
        "--sample", str(len(failed_groups)),
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=base_dir,
            check=True
        )
        
        # Clean up temp file
        if temp_group_keys_file.exists():
            temp_group_keys_file.unlink()
        
        print(f"  ✅ S2 retry completed for Arm {arm}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ S2 retry failed for Arm {arm} (exit code: {e.returncode})")
        if temp_group_keys_file.exists():
            temp_group_keys_file.unlink()
        return False
    except Exception as e:
        print(f"  ❌ Error retrying S2 for Arm {arm}: {e}")
        if temp_group_keys_file.exists():
            temp_group_keys_file.unlink()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Retry failed groups from QA dataset generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument("--run_tag", type=str, required=True, help="Run tag from QA execution")
    parser.add_argument(
        "--arms",
        type=str,
        nargs="+",
        default=ARMS,
        help=f"Arms to check (default: {ARMS})",
    )
    parser.add_argument(
        "--stage",
        type=str,
        choices=["1", "2", "both"],
        default="both",
        help="Stage to retry: '1' (S1 only), '2' (S2 only), 'both' (default)",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Only show failed groups, don't retry",
    )
    parser.add_argument(
        "--min_age_seconds",
        type=float,
        default=60.0,
        help="Minimum file age in seconds to consider as completed (default: 60.0). "
             "Files modified more recently are considered potentially still running.",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        print(f"❌ Base directory does not exist: {base_dir}")
        sys.exit(1)
    
    arms = [arm.upper() for arm in args.arms]
    
    print("=" * 70)
    print("Retry Failed QA Groups")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {args.run_tag}")
    print(f"Arms: {', '.join(arms)}")
    print(f"Stage: {args.stage}")
    if args.dry_run:
        print("⚠️  DRY RUN MODE - No retries will be performed")
    print("=" * 70)
    
    # Find failed groups
    print("\n>>> Analyzing failed groups...")
    print(f"   Minimum file age threshold: {args.min_age_seconds} seconds")
    s1_failed, s2_failed, s1_running, s2_running = find_failed_groups(
        base_dir, args.run_tag, arms, args.stage, args.min_age_seconds
    )
    
    total_s1_failed = sum(len(groups) for groups in s1_failed.values())
    total_s2_failed = sum(len(groups) for groups in s2_failed.values())
    total_s1_running = sum(len(groups) for groups in s1_running.values())
    total_s2_running = sum(len(groups) for groups in s2_running.values())
    
    # Show potentially running groups
    if total_s1_running > 0 or total_s2_running > 0:
        print(f"\n⚠️  Potentially Running Groups (recently modified, may still be processing):")
        if total_s1_running > 0:
            print(f"   S1: {total_s1_running} groups")
            for arm in arms:
                if s1_running.get(arm):
                    print(f"     Arm {arm}: {len(s1_running[arm])} groups")
        if total_s2_running > 0:
            print(f"   S2: {total_s2_running} groups")
            for arm in arms:
                if s2_running.get(arm):
                    print(f"     Arm {arm}: {len(s2_running[arm])} groups")
        print("   These groups are excluded from failed list to avoid false positives.\n")
    
    if total_s1_failed == 0 and total_s2_failed == 0:
        if total_s1_running > 0 or total_s2_running > 0:
            print("\n✅ No definitely failed groups found!")
            print("   Some groups may still be processing (see above).")
            print("   Wait a few minutes and run again, or use --min_age_seconds to adjust threshold.")
        else:
            print("\n✅ All groups completed successfully!")
        return 0
    
    # Show failed groups
    if args.stage in ("1", "both") and total_s1_failed > 0:
        print(f"\n>>> S1 Failed Groups: {total_s1_failed} total")
        for arm in arms:
            if s1_failed.get(arm):
                print(f"\n  Arm {arm}: {len(s1_failed[arm])} failed groups")
                for group in s1_failed[arm]:
                    print(f"    - {group['group_key']} ({group['group_id']})")
    
    if args.stage in ("2", "both") and total_s2_failed > 0:
        print(f"\n>>> S2 Failed Groups: {total_s2_failed} total")
        for arm in arms:
            if s2_failed.get(arm):
                print(f"\n  Arm {arm}: {len(s2_failed[arm])} failed groups")
                for group in s2_failed[arm]:
                    print(f"    - {group['group_key']} ({group['group_id']})")
    
    if args.dry_run:
        print("\n>>> Dry run mode - not retrying")
        return 0
    
    # Retry failed groups
    print("\n" + "=" * 70)
    print("Retrying failed groups...")
    print("=" * 70)
    
    results = {}
    
    # Retry S1
    if args.stage in ("1", "both") and total_s1_failed > 0:
        print("\n>>> Retrying S1...")
        for arm in arms:
            if s1_failed.get(arm):
                success = retry_s1_for_groups(base_dir, args.run_tag, arm, s1_failed[arm])
                results[f"S1_{arm}"] = success
            else:
                results[f"S1_{arm}"] = True
    
    # Retry S2
    if args.stage in ("2", "both") and total_s2_failed > 0:
        print("\n>>> Retrying S2...")
        for arm in arms:
            if s2_failed.get(arm):
                success = retry_s2_for_groups(base_dir, args.run_tag, arm, s2_failed[arm])
                results[f"S2_{arm}"] = success
            else:
                results[f"S2_{arm}"] = True
    
    # Verify results
    print("\n" + "=" * 70)
    print("Verifying retry results...")
    print("=" * 70)
    
    s1_failed_after, s2_failed_after, s1_running_after, s2_running_after = find_failed_groups(
        base_dir, args.run_tag, arms, args.stage, args.min_age_seconds
    )
    total_s1_failed_after = sum(len(groups) for groups in s1_failed_after.values())
    total_s2_failed_after = sum(len(groups) for groups in s2_failed_after.values())
    
    if total_s1_failed_after == 0 and total_s2_failed_after == 0:
        print("\n✅ All groups completed successfully after retry!")
        return 0
    else:
        print(f"\n⚠️  Still {total_s1_failed_after} S1 failures and {total_s2_failed_after} S2 failures:")
        if total_s1_failed_after > 0:
            for arm in arms:
                if s1_failed_after.get(arm):
                    print(f"  S1 Arm {arm}: {len(s1_failed_after[arm])} still failed")
        if total_s2_failed_after > 0:
            for arm in arms:
                if s2_failed_after.get(arm):
                    print(f"  S2 Arm {arm}: {len(s2_failed_after[arm])} still failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())


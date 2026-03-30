#!/usr/bin/env python3
"""
Test S1 for all arms with sample 1 group.

This script:
1. Selects first group from selected_18_groups.json
2. Runs S1 for all 6 arms (A-F) with that single group
3. Reports success/failure for each arm

Usage:
    python 3_Code/Scripts/test_s1_all_arms_sample1.py \
        --base_dir . \
        --run_tag S0_QA_fixed_v3_test
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


ARMS = ["A", "B", "C", "D", "E", "F"]


def load_first_group(base_dir: Path, run_tag: str) -> Optional[Dict[str, str]]:
    """Load first group from selected groups."""
    selected_file = base_dir / "2_Data" / "metadata" / "generated" / run_tag / "selected_18_groups.json"
    
    # Fallback to S0_QA_fixed_v3 if test run_tag doesn't have selected groups
    if not selected_file.exists():
        fallback_file = base_dir / "2_Data" / "metadata" / "generated" / "S0_QA_fixed_v3" / "selected_18_groups.json"
        if fallback_file.exists():
            selected_file = fallback_file
        else:
            return None
    
    with open(selected_file, "r", encoding="utf-8") as f:
        selected = json.load(f)
        return selected[0] if selected else None


def run_s1_for_arm(
    base_dir: Path,
    run_tag: str,
    arm: str,
    group: Dict[str, str],
) -> tuple[bool, str]:
    """Run S1 for a single arm with one group."""
    print(f"\n[Arm {arm}] Running S1 for group: {group['group_key']}...")
    
    # Create a temporary file with group_key
    temp_group_keys_file = base_dir / "2_Data" / "metadata" / f"temp_test_group_{run_tag}_{arm}.txt"
    temp_group_keys_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(temp_group_keys_file, "w", encoding="utf-8") as f:
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
        "--sample", "1",
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=base_dir,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )
        
        # Clean up temp file
        if temp_group_keys_file.exists():
            temp_group_keys_file.unlink()
        
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, f"Exit code {result.returncode}\n{result.stderr}\n{result.stdout}"
    except subprocess.TimeoutExpired:
        if temp_group_keys_file.exists():
            temp_group_keys_file.unlink()
        return False, "Process timed out after 10 minutes"
    except Exception as e:
        if temp_group_keys_file.exists():
            temp_group_keys_file.unlink()
        return False, f"Exception: {type(e).__name__}: {e}"


def verify_s1_output(base_dir: Path, run_tag: str, arm: str) -> tuple[bool, str]:
    """Verify S1 output file exists and contains the group."""
    s1_file = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"stage1_struct__arm{arm}.jsonl"
    
    if not s1_file.exists():
        return False, f"S1 output file not found: {s1_file}"
    
    # Check if file has content
    with open(s1_file, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
        if not lines:
            return False, f"S1 output file is empty: {s1_file}"
        
        # Try to parse first line
        try:
            data = json.loads(lines[0])
            group_key = data.get("group_key", "")
            group_id = data.get("group_id", "")
            return True, f"Found group: {group_key} ({group_id})"
        except Exception as e:
            return False, f"Failed to parse S1 output: {e}"
    
    return True, "S1 output verified"


def main():
    parser = argparse.ArgumentParser(
        description="Test S1 for all arms with sample 1 group",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument(
        "--run_tag",
        type=str,
        default="S0_QA_test_sample1",
        help="Run tag (default: S0_QA_test_sample1)",
    )
    parser.add_argument(
        "--arms",
        type=str,
        nargs="+",
        default=ARMS,
        help=f"Arms to test (default: {ARMS})",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        print(f"❌ Base directory does not exist: {base_dir}")
        sys.exit(1)
    
    arms = [arm.upper() for arm in args.arms]
    
    print("=" * 70)
    print("S1 Test: All Arms with Sample 1 Group")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {args.run_tag}")
    print(f"Arms: {', '.join(arms)}")
    print("=" * 70)
    
    # Load first group
    print("\n>>> Loading test group...")
    group = load_first_group(base_dir, args.run_tag)
    if not group:
        print("❌ Failed to load test group")
        sys.exit(1)
    
    print(f"✅ Test group: {group['group_key']}")
    print(f"   Group ID: {group.get('group_id', 'unknown')}")
    print(f"   Specialty: {group.get('specialty', 'unknown')}")
    
    # Run S1 for each arm
    print("\n" + "=" * 70)
    print("Running S1 for each arm...")
    print("=" * 70)
    
    results = {}
    for idx, arm in enumerate(arms, 1):
        progress = f"[{idx}/{len(arms)}]"
        print(f"\n{progress} Testing Arm {arm}...")
        
        success, output = run_s1_for_arm(base_dir, args.run_tag, arm, group)
        
        if success:
            # Verify output
            verify_success, verify_msg = verify_s1_output(base_dir, args.run_tag, arm)
            if verify_success:
                print(f"✅ Arm {arm}: S1 completed successfully")
                print(f"   {verify_msg}")
                results[arm] = {"success": True, "message": verify_msg}
            else:
                print(f"⚠️  Arm {arm}: S1 completed but verification failed")
                print(f"   {verify_msg}")
                results[arm] = {"success": False, "message": verify_msg}
        else:
            print(f"❌ Arm {arm}: S1 failed")
            print(f"   Error: {output[:300]}")
            results[arm] = {"success": False, "message": output[:300]}
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    passed = [arm for arm, r in results.items() if r["success"]]
    failed = [arm for arm, r in results.items() if not r["success"]]
    
    print(f"\nPassed: {len(passed)}/{len(arms)} ({', '.join(passed) if passed else 'None'})")
    if failed:
        print(f"Failed: {len(failed)}/{len(arms)} ({', '.join(failed)})")
        print("\nFailed arm details:")
        for arm in failed:
            print(f"  - Arm {arm}: {results[arm]['message'][:150]}")
    
    print("\n" + "=" * 70)
    print(f"Output files: 2_Data/metadata/generated/{args.run_tag}/stage1_struct__arm*.jsonl")
    print("=" * 70)
    
    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())


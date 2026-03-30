#!/usr/bin/env python3
"""
Retry S1 processing for groups that are missing from S1 output files.

This script:
1. Checks which groups are missing from each arm's S1 output
2. Re-runs S1 for only the missing groups
3. Verifies all groups are present after retry

Usage:
    python 3_Code/Scripts/retry_missing_s1_groups.py \
        --base_dir . \
        --run_tag S0_QA_fixed_v3
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set


def load_selected_groups(base_dir: Path, run_tag: str) -> List[Dict[str, str]]:
    """Load the selected 18 groups."""
    selected_file = base_dir / "2_Data" / "metadata" / "generated" / run_tag / "selected_18_groups.json"
    if not selected_file.exists():
        raise FileNotFoundError(f"Selected groups file not found: {selected_file}")
    
    with open(selected_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_s1_group_keys(base_dir: Path, run_tag: str, arm: str) -> Set[str]:
    """Get set of group_keys that exist in S1 output."""
    s1_file = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"stage1_struct__arm{arm}.jsonl"
    if not s1_file.exists():
        return set()
    
    found_keys = set()
    with open(s1_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                gkey = data.get("group_key")
                if gkey:
                    found_keys.add(gkey)
            except Exception:
                continue
    
    return found_keys


def find_missing_groups(base_dir: Path, run_tag: str, arms: List[str]) -> Dict[str, List[Dict[str, str]]]:
    """Find missing groups for each arm."""
    selected = load_selected_groups(base_dir, run_tag)
    selected_keys = {g["group_key"] for g in selected}
    
    missing = {}
    for arm in arms:
        found_keys = get_s1_group_keys(base_dir, run_tag, arm)
        missing_keys = selected_keys - found_keys
        missing_groups = [g for g in selected if g["group_key"] in missing_keys]
        missing[arm] = missing_groups
    
    return missing


def retry_s1_for_groups(
    base_dir: Path,
    run_tag: str,
    arm: str,
    missing_groups: List[Dict[str, str]],
) -> bool:
    """Retry S1 for missing groups and merge with existing output."""
    if not missing_groups:
        return True
    
    print(f"\n[Arm {arm}] Retrying S1 for {len(missing_groups)} missing groups...")
    
    # Backup existing files
    out_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    stage1_struct_path = out_dir / f"stage1_struct__arm{arm}.jsonl"
    stage1_raw_path = out_dir / f"stage1_raw__arm{arm}.jsonl"
    
    # Backup existing data
    existing_struct = []
    existing_raw = []
    if stage1_struct_path.exists():
        with open(stage1_struct_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        existing_struct.append(json.loads(line))
                    except:
                        pass
    
    if stage1_raw_path.exists():
        with open(stage1_raw_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        existing_raw.append(json.loads(line))
                    except:
                        pass
    
    existing_group_keys = {g.get("group_key") for g in existing_struct if g.get("group_key")}
    print(f"  Existing groups in file: {len(existing_group_keys)}")
    
    # Create a temporary file with missing group_keys
    temp_dir = base_dir / "2_Data" / "metadata" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_group_keys_file = temp_dir / f"temp_retry_groups_{run_tag}_{arm}.txt"
    
    with open(temp_group_keys_file, "w", encoding="utf-8") as f:
        for group in missing_groups:
            f.write(f"{group['group_key']}\n")
    
    # Use a temporary run_tag to avoid overwriting
    temp_run_tag = f"{run_tag}_retry_{arm}"
    temp_out_dir = base_dir / "2_Data" / "metadata" / "generated" / temp_run_tag
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "01_generate_json.py"),
        "--base_dir", str(base_dir),
        "--run_tag", temp_run_tag,
        "--arm", arm,
        "--mode", "S0",
        "--stage", "1",
        "--only_group_keys_file", str(temp_group_keys_file),
        "--sample", str(len(missing_groups)),
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=base_dir,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Load new data
        temp_struct_path = temp_out_dir / f"stage1_struct__arm{arm}.jsonl"
        temp_raw_path = temp_out_dir / f"stage1_raw__arm{arm}.jsonl"
        
        new_struct = []
        new_raw = []
        
        if temp_struct_path.exists():
            with open(temp_struct_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            new_struct.append(json.loads(line))
                        except:
                            pass
        
        if temp_raw_path.exists():
            with open(temp_raw_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            new_raw.append(json.loads(line))
                        except:
                            pass
        
        # Merge: existing + new (avoid duplicates by group_key)
        merged_struct = {g.get("group_key"): g for g in existing_struct}
        for g in new_struct:
            merged_struct[g.get("group_key")] = g
        
        merged_raw = {g.get("source_info", {}).get("group_key"): g for g in existing_raw}
        for g in new_raw:
            key = g.get("source_info", {}).get("group_key")
            if key:
                merged_raw[key] = g
        
        # Write merged data back
        with open(stage1_struct_path, "w", encoding="utf-8") as f:
            for g in merged_struct.values():
                f.write(json.dumps(g, ensure_ascii=False) + "\n")
        
        with open(stage1_raw_path, "w", encoding="utf-8") as f:
            for g in merged_raw.values():
                f.write(json.dumps(g, ensure_ascii=False) + "\n")
        
        print(f"  Merged: {len(existing_struct)} existing + {len(new_struct)} new = {len(merged_struct)} total")
        
        # Clean up
        if temp_group_keys_file.exists():
            temp_group_keys_file.unlink()
        
        # Clean up temp directory
        import shutil
        if temp_out_dir.exists():
            shutil.rmtree(temp_out_dir)
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to retry S1 for Arm {arm}")
        print(f"Error: {e.stderr}")
        if temp_group_keys_file.exists():
            temp_group_keys_file.unlink()
        return False
    except Exception as e:
        print(f"❌ Error merging files for Arm {arm}: {e}")
        if temp_group_keys_file.exists():
            temp_group_keys_file.unlink()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Retry S1 processing for missing groups",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument("--run_tag", type=str, required=True, help="Run tag")
    parser.add_argument(
        "--arms",
        type=str,
        nargs="+",
        default=["A", "B", "C", "D", "E", "F"],
        help="Arms to check (default: A B C D E F)",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Only show missing groups, don't retry",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        print(f"❌ Base directory does not exist: {base_dir}")
        sys.exit(1)
    
    arms = [arm.upper() for arm in args.arms]
    
    print("=" * 70)
    print("S1 Missing Groups Retry")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {args.run_tag}")
    print(f"Arms: {', '.join(arms)}")
    print("=" * 70)
    
    # Find missing groups
    print("\n>>> Checking for missing groups...")
    missing = find_missing_groups(base_dir, args.run_tag, arms)
    
    total_missing = sum(len(groups) for groups in missing.values())
    if total_missing == 0:
        print("\n✅ All groups are present in S1 output for all arms!")
        return 0
    
    # Show missing groups
    print(f"\n>>> Found {total_missing} missing groups across {len([a for a in arms if missing[a]])} arms:")
    for arm in arms:
        if missing[arm]:
            print(f"\n  Arm {arm}: {len(missing[arm])} missing groups")
            for group in missing[arm]:
                print(f"    - {group['group_key']} ({group['group_id']})")
    
    if args.dry_run:
        print("\n>>> Dry run mode - not retrying")
        return 0
    
    # Retry missing groups
    print("\n" + "=" * 70)
    print("Retrying S1 for missing groups...")
    print("=" * 70)
    
    results = {}
    for arm in arms:
        if missing[arm]:
            success = retry_s1_for_groups(base_dir, args.run_tag, arm, missing[arm])
            results[arm] = success
            if success:
                print(f"✅ Arm {arm}: Retry completed")
            else:
                print(f"❌ Arm {arm}: Retry failed")
        else:
            print(f"✅ Arm {arm}: No missing groups")
            results[arm] = True
    
    # Verify all groups are now present
    print("\n" + "=" * 70)
    print("Verifying all groups are present...")
    print("=" * 70)
    
    missing_after = find_missing_groups(base_dir, args.run_tag, arms)
    total_missing_after = sum(len(groups) for groups in missing_after.values())
    
    if total_missing_after == 0:
        print("\n✅ All groups are now present in S1 output!")
        return 0
    else:
        print(f"\n⚠️  Still missing {total_missing_after} groups:")
        for arm in arms:
            if missing_after[arm]:
                print(f"  Arm {arm}: {len(missing_after[arm])} still missing")
                for group in missing_after[arm]:
                    print(f"    - {group['group_key']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""
4개의 specialty에서 랜덤으로 1개씩 그룹을 선택해서 S4까지 실행하는 스크립트

Usage:
    python 3_Code/Scripts/run_random_4specialties_s4.py [--base_dir .] [--run_tag RANDOM_4SPEC_YYYYMMDD_HHMMSS] [--arm A] [--seed 42]
"""

import argparse
import csv
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def load_groups_canonical(csv_path: Path) -> List[Dict[str, str]]:
    """Load groups from groups_canonical.csv."""
    groups = []
    if not csv_path.exists():
        raise FileNotFoundError(f"groups_canonical.csv not found: {csv_path}")
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            groups.append({
                "group_id": row.get("group_id", "").strip(),
                "group_key": row.get("group_key", "").strip(),
                "specialty": row.get("specialty", "").strip(),
                "anatomy": row.get("anatomy", "").strip(),
                "modality_or_type": row.get("modality_or_type", "").strip(),
                "category": row.get("category", "").strip(),
                "objectives": row.get("objectives", "").strip(),
            })
    
    return groups


def select_4_specialties_random_groups(
    groups: List[Dict[str, str]], 
    seed: int = 42
) -> List[Dict[str, str]]:
    """Select 4 random specialties, then one random group from each."""
    random.seed(seed)
    
    # Group by specialty
    specialty_groups: Dict[str, List[Dict[str, str]]] = {}
    for group in groups:
        specialty = group.get("specialty", "").strip()
        if not specialty:
            continue
        if specialty not in specialty_groups:
            specialty_groups[specialty] = []
        specialty_groups[specialty].append(group)
    
    # Select 4 random specialties
    all_specialties = list(specialty_groups.keys())
    if len(all_specialties) < 4:
        raise ValueError(f"Not enough specialties: found {len(all_specialties)}, need 4")
    
    selected_specialties = random.sample(all_specialties, 4)
    print(f"\n>>> Selected 4 specialties (seed={seed}):")
    for spec in selected_specialties:
        print(f"  - {spec}")
    
    # Select one random group from each selected specialty
    selected = []
    print(f"\n>>> Selected groups:")
    for specialty in selected_specialties:
        group_list = specialty_groups[specialty]
        if not group_list:
            print(f"  ⚠️  Warning: {specialty} has no groups, skipping")
            continue
        selected_group = random.choice(group_list)
        selected.append(selected_group)
        print(f"  [{specialty:20s}] {selected_group['group_id']} - {selected_group['group_key']}")
    
    return selected


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> bool:
    """Run a command and return True if successful."""
    print(f"\n>>> Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            capture_output=False,
            text=True,
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with return code {e.returncode}")
        return False
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False


def run_s1_s2(
    base_dir: Path,
    run_tag: str,
    arm: str,
    selected_groups: List[Dict[str, str]],
    max_retries: int = 3,
) -> bool:
    """Run S1 and S2 for selected groups with retry logic."""
    print("\n" + "="*60)
    print("STEP 1: Running S1 and S2 (JSON generation)")
    print("="*60)
    
    # Create a temporary file with selected group_keys
    temp_dir = base_dir / "2_Data" / "metadata" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_group_keys_file = temp_dir / f"temp_selected_groups_{run_tag}.txt"
    
    with open(temp_group_keys_file, "w", encoding="utf-8") as f:
        for group in selected_groups:
            f.write(f"{group['group_key']}\n")
    
    print(f"Selected {len(selected_groups)} groups:")
    for group in selected_groups:
        print(f"  - {group['group_id']}: {group['group_key']} ({group['specialty']})")
    
    # Run 01_generate_json.py
    # Note: --sample must be set to process all selected groups (default is 1)
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "01_generate_json.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
        "--mode", "FINAL",
        "--stage", "both",
        "--only_group_keys_file", str(temp_group_keys_file),
        "--sample", str(len(selected_groups)),  # Process all selected groups
        "--resume",
    ]
    
    # Retry logic
    for attempt in range(1, max_retries + 1):
        print(f"\n>>> Attempt {attempt}/{max_retries}")
        try:
            success = run_command(cmd, cwd=base_dir)
            if success:
                # Clean up temp file
                if temp_group_keys_file.exists():
                    temp_group_keys_file.unlink()
                return True
            else:
                if attempt < max_retries:
                    print(f"\n⚠️  Attempt {attempt} failed. Retrying... (--resume will skip completed entities)")
                else:
                    print(f"\n❌ All {max_retries} attempts failed")
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user (Ctrl+C)")
            print(f"\n💡 To resume from where you left off, run the same command again:")
            print(f"   python3 3_Code/Scripts/run_random_4specialties_s4.py \\")
            print(f"       --base_dir . \\")
            print(f"       --run_tag {run_tag} \\")
            print(f"       --arm {arm}")
            print(f"\n   The --resume option will skip already completed entities.")
            # Clean up temp file
            if temp_group_keys_file.exists():
                temp_group_keys_file.unlink()
            raise
    
    # Clean up temp file
    if temp_group_keys_file.exists():
        temp_group_keys_file.unlink()
    
    return False


def run_s3(
    base_dir: Path,
    run_tag: str,
    arm: str,
) -> bool:
    """Run S3 (policy resolver)."""
    print("\n" + "="*60)
    print("STEP 2: Running S3 (Policy Resolver)")
    print("="*60)
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "03_s3_policy_resolver.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
        "--s1_arm", arm,
    ]
    
    return run_command(cmd, cwd=base_dir)


def run_s4(
    base_dir: Path,
    run_tag: str,
    arm: str,
    workers: int = 2,
) -> bool:
    """Run S4 (image generator)."""
    print("\n" + "="*60)
    print("STEP 3: Running S4 (Image Generator)")
    print("="*60)
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "04_s4_image_generator.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
        "--workers", str(workers),
    ]
    
    return run_command(cmd, cwd=base_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Select 4 random specialties, then one group from each, and run S1-S4"
    )
    parser.add_argument(
        "--base_dir",
        type=str,
        default=".",
        help="Base directory of the project",
    )
    parser.add_argument(
        "--run_tag",
        type=str,
        default=None,
        help="Run tag (default: RANDOM_4SPEC_YYYYMMDD_HHMMSS)",
    )
    parser.add_argument(
        "--arm",
        type=str,
        default="A",
        help="Arm to use (default: A)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed (default: current timestamp)",
    )
    parser.add_argument(
        "--workers_s4",
        type=int,
        default=2,
        help="Number of workers for S4 (default: 2)",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    
    # Generate run_tag if not provided
    if args.run_tag is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_tag = f"RANDOM_4SPEC_{timestamp}"
    else:
        run_tag = args.run_tag
    
    # Generate seed if not provided
    if args.seed is None:
        seed = int(datetime.now().timestamp())
    else:
        seed = args.seed
    
    print("="*60)
    print("4개 Specialty 랜덤 선택 - S4까지 실행")
    print("="*60)
    print(f"Base Dir: {base_dir}")
    print(f"Run Tag: {run_tag}")
    print(f"Arm: {args.arm}")
    print(f"Seed: {seed}")
    print("="*60)
    
    # Load groups
    groups_csv_path = base_dir / "2_Data" / "metadata" / "groups_canonical.csv"
    print(f"\n>>> Loading groups from: {groups_csv_path}")
    groups = load_groups_canonical(groups_csv_path)
    print(f"   Loaded {len(groups)} groups")
    
    # Select 4 specialties and one group from each
    print(f"\n>>> Selecting 4 random specialties and one group from each (seed={seed})...")
    selected_groups = select_4_specialties_random_groups(groups, seed=seed)
    print(f"\n✅ Selected {len(selected_groups)} groups from 4 specialties")
    
    # Run pipeline
    all_success = True
    
    # Step 1: S1 and S2 (with retry logic)
    try:
        if not run_s1_s2(base_dir, run_tag, args.arm, selected_groups, max_retries=3):
            print("❌ S1/S2 failed after retries")
            print(f"\n💡 You can retry manually with:")
            print(f"   python3 3_Code/Scripts/run_random_4specialties_s4.py \\")
            print(f"       --base_dir . \\")
            print(f"       --run_tag {run_tag} \\")
            print(f"       --arm {args.arm} \\")
            print(f"       --seed {seed}")
            all_success = False
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        print(f"\n💡 To resume from where you left off, run:")
        print(f"   python3 3_Code/Scripts/run_random_4specialties_s4.py \\")
        print(f"       --base_dir . \\")
        print(f"       --run_tag {run_tag} \\")
        print(f"       --arm {args.arm} \\")
        print(f"       --seed {seed}")
        print(f"\n   The --resume option will skip already completed entities.")
        sys.exit(130)  # Standard exit code for SIGINT
    
    # Step 2: S3
    if not run_s3(base_dir, run_tag, args.arm):
        print("❌ S3 failed")
        all_success = False
        sys.exit(1)
    
    # Step 3: S4
    if not run_s4(base_dir, run_tag, args.arm, workers=args.workers_s4):
        print("❌ S4 failed")
        all_success = False
        sys.exit(1)
    
    # Summary
    print("\n" + "="*60)
    if all_success:
        print("✅ SUCCESS: All steps completed")
        print(f"\nRun Tag: {run_tag}")
        print(f"Selected Groups:")
        for group in selected_groups:
            print(f"  - {group['group_id']}: {group['group_key']} ({group['specialty']})")
    else:
        print("⚠️  COMPLETED WITH ERRORS")
        print("   Check the output above for details")
    print("="*60)


if __name__ == "__main__":
    main()


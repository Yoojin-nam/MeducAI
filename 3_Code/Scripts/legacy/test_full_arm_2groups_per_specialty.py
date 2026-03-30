#!/usr/bin/env python3
"""
Test Full Arm Pipeline: 2 Groups per Specialty Sequentially

This script:
1. For each arm (A, B, C, D, E, F), selects 2 groups from 2 different specialties sequentially
2. Runs full pipeline for each test:
   - S1/S2: JSON generation
   - S3: Policy resolver
   - S4: Image generator
   - PDF: PDF generation
3. Total: 12 tests (6 arms × 2 groups)

Usage:
    python 3_Code/Scripts/test_full_arm_2groups_per_specialty.py [--run_tag TAG] [--seed 42] [--skip_s3_s4]
"""

import argparse
import csv
import json
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ARM_LABELS = {
    "A": "Baseline",
    "B": "RAG Only",
    "C": "Thinking",
    "D": "Synergy",
    "E": "High-End",
    "F": "Benchmark"
}

ARMS = ["A", "B", "C", "D", "E", "F"]


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
            })
    
    return groups


def select_2_groups_per_arm_by_specialty(
    groups: List[Dict[str, str]],
    arms: List[str],
    seed: int = 42,
) -> Dict[str, List[Dict[str, str]]]:
    """
    Select 2 groups per arm from specialties sequentially.
    If there are not enough specialties, will wrap around and reuse specialties.
    
    Returns:
        Dict mapping arm -> list of 2 groups (from different specialties when possible)
    """
    # Group by specialty
    specialty_groups: Dict[str, List[Dict[str, str]]] = {}
    for group in groups:
        specialty = group.get("specialty", "").strip()
        if not specialty:
            continue
        if specialty not in specialty_groups:
            specialty_groups[specialty] = []
        specialty_groups[specialty].append(group)
    
    # Get sorted list of specialties
    specialties = sorted(specialty_groups.keys())
    
    if not specialties:
        raise ValueError("No specialties found in groups")
    
    print(f"   Found {len(specialties)} specialties: {', '.join(specialties[:5])}{'...' if len(specialties) > 5 else ''}")
    
    # Set random seed
    random.seed(seed)
    
    # Select 2 groups per arm from specialties sequentially
    # If we run out of specialties, wrap around
    arm_to_groups: Dict[str, List[Dict[str, str]]] = {}
    specialty_index = 0
    
    for arm in arms:
        selected_groups = []
        # Select 2 groups from specialties (try to use different specialties)
        for _ in range(2):
            if specialty_index >= len(specialties):
                # Wrap around if we run out of specialties
                specialty_index = 0
            
            specialty = specialties[specialty_index]
            specialty_group_list = specialty_groups[specialty]
            
            if specialty_group_list:
                # If this specialty has multiple groups, try to avoid selecting the same group
                # Otherwise, just pick randomly
                if len(selected_groups) > 0 and selected_groups[0].get("specialty") == specialty:
                    # Same specialty as previous group, try to pick a different group if possible
                    available = [g for g in specialty_group_list if g["group_id"] != selected_groups[0]["group_id"]]
                    if available:
                        selected_group = random.choice(available)
                    else:
                        selected_group = random.choice(specialty_group_list)
                else:
                    selected_group = random.choice(specialty_group_list)
                selected_groups.append(selected_group)
            
            specialty_index += 1
        
        arm_to_groups[arm] = selected_groups
    
    return arm_to_groups


def run_command(cmd: List[str], cwd: Optional[Path] = None, capture_output: bool = False) -> bool:
    """Run a command and return success status."""
    try:
        if capture_output:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        else:
            subprocess.run(cmd, cwd=cwd, check=True)
            return True
    except subprocess.CalledProcessError as e:
        if not capture_output:
            print(f"  ❌ Command failed with return code {e.returncode}")
        return False
    except Exception as e:
        if not capture_output:
            print(f"  ❌ Error running command: {e}")
        return False


def run_s1_s2(base_dir: Path, run_tag: str, arm: str, group_key: str) -> bool:
    """Run S1 and S2 for a single group."""
    print(f"    [S1/S2] Running for arm {arm}...")
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "01_generate_json.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
        "--mode", "S0",
        "--stage", "both",
        "--only_group_key", group_key,
        "--sample", "1",
    ]
    
    return run_command(cmd, cwd=base_dir)


def run_s3(base_dir: Path, run_tag: str, arm: str) -> bool:
    """Run S3 (policy resolver)."""
    print(f"    [S3] Running for arm {arm}...")
    
    s3_script = base_dir / "3_Code" / "src" / "03_s3_policy_resolver.py"
    if not s3_script.exists():
        print(f"    ⚠️  S3 script not found, skipping")
        return True
    
    cmd = [
        sys.executable,
        str(s3_script),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
    ]
    
    return run_command(cmd, cwd=base_dir)


def run_s4(base_dir: Path, run_tag: str, arm: str) -> bool:
    """Run S4 (image generator)."""
    print(f"    [S4] Running for arm {arm}...")
    
    s4_script = base_dir / "3_Code" / "src" / "04_s4_image_generator.py"
    if not s4_script.exists():
        print(f"    ⚠️  S4 script not found, skipping")
        return True
    
    cmd = [
        sys.executable,
        str(s4_script),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
    ]
    
    return run_command(cmd, cwd=base_dir)


def load_s1_group_id(base_dir: Path, run_tag: str, arm: str) -> Optional[str]:
    """Load actual group_id from S1 results."""
    s1_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"stage1_struct__arm{arm}.jsonl"
    if not s1_path.exists():
        return None
    
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                return record.get("group_id", "").strip()
            except json.JSONDecodeError:
                continue
    
    return None


def generate_pdf(base_dir: Path, run_tag: str, arm: str, group_id: str) -> bool:
    """Generate PDF for a group."""
    print(f"    [PDF] Generating for arm {arm}...")
    
    out_dir = base_dir / "6_Distributions" / "QA_Packets"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "07_build_set_pdf.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
        "--group_id", group_id,
        "--out_dir", str(out_dir),
    ]
    
    return run_command(cmd, cwd=base_dir)


def process_test(
    base_dir: Path,
    run_tag: str,
    arm: str,
    group: Dict[str, str],
    test_num: int,
    total_tests: int,
    skip_s3_s4: bool = False,
) -> Dict[str, bool]:
    """Process one test (one group for one arm) through full pipeline."""
    results = {
        "s1_s2": False,
        "s3": False,
        "s4": False,
        "pdf": False,
    }
    
    group_key = group["group_key"]
    specialty = group["specialty"]
    group_id = group["group_id"]
    
    print(f"\n{'='*70}")
    print(f"TEST {test_num}/{total_tests}: Arm {arm} ({ARM_LABELS.get(arm, arm)})")
    print(f"  Group: {group_id}")
    print(f"  Group Key: {group_key}")
    print(f"  Specialty: {specialty}")
    print(f"{'='*70}")
    
    # S1/S2
    if run_s1_s2(base_dir, run_tag, arm, group_key):
        results["s1_s2"] = True
        print(f"    ✅ S1/S2 completed")
    else:
        print(f"    ❌ S1/S2 failed")
        return results  # Cannot continue without S1/S2
    
    # Get actual group_id from S1 results
    actual_group_id = load_s1_group_id(base_dir, run_tag, arm)
    if not actual_group_id:
        print(f"    ⚠️  Could not find group_id in S1 results")
        return results
    
    # S3
    if skip_s3_s4:
        print(f"    ⏭️  Skipping S3 (--skip_s3_s4)")
        results["s3"] = True
    else:
        if run_s3(base_dir, run_tag, arm):
            results["s3"] = True
            print(f"    ✅ S3 completed")
        else:
            print(f"    ⚠️  S3 failed (continuing anyway)")
    
    # S4
    if skip_s3_s4:
        print(f"    ⏭️  Skipping S4 (--skip_s3_s4)")
        results["s4"] = True
    else:
        if run_s4(base_dir, run_tag, arm):
            results["s4"] = True
            print(f"    ✅ S4 completed")
        else:
            print(f"    ⚠️  S4 failed (continuing anyway)")
    
    # PDF
    if generate_pdf(base_dir, run_tag, arm, actual_group_id):
        results["pdf"] = True
        pdf_path = base_dir / "6_Distributions" / "QA_Packets" / f"SET_{actual_group_id}_arm{arm}_{run_tag}.pdf"
        if pdf_path.exists():
            print(f"    ✅ PDF created: {pdf_path.name}")
        else:
            print(f"    ⚠️  PDF command succeeded but file not found")
    else:
        print(f"    ❌ PDF generation failed")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Test full arm pipeline: 2 groups per specialty sequentially (12 tests total)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument(
        "--run_tag",
        type=str,
        default=None,
        help="Run tag (default: TEST_FULLARM_2GRP_YYYYMMDD_HHMMSS)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument(
        "--skip_s3_s4",
        action="store_true",
        help="Skip S3/S4 (image generation)",
    )
    parser.add_argument(
        "--groups_csv",
        type=str,
        default="2_Data/metadata/groups_canonical.csv",
        help="Path to groups_canonical.csv",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        print(f"❌ Base directory does not exist: {base_dir}")
        sys.exit(1)
    
    # Generate run_tag if not provided
    if args.run_tag:
        run_tag = args.run_tag
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_tag = f"TEST_FULLARM_2GRP_{timestamp}"
    
    print("=" * 70)
    print("Full Arm Pipeline Test: 2 Groups per Specialty Sequentially")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Arms: {', '.join(ARMS)}")
    print(f"Total tests: {len(ARMS) * 2} (6 arms × 2 groups)")
    print(f"Seed: {args.seed}")
    if args.skip_s3_s4:
        print("⚠️  S3/S4 will be skipped")
    print("=" * 70)
    
    # Load groups
    groups_csv_path = base_dir / args.groups_csv
    print(f"\n>>> Loading groups from: {groups_csv_path}")
    groups = load_groups_canonical(groups_csv_path)
    print(f"   Loaded {len(groups)} groups")
    
    # Select groups (2 per arm from different specialties)
    print(f"\n>>> Selecting 2 groups per arm from different specialties (seed={args.seed})...")
    try:
        arm_to_groups = select_2_groups_per_arm_by_specialty(groups, ARMS, seed=args.seed)
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    
    print(f"\n✅ Selected groups:")
    for arm in ARMS:
        groups_list = arm_to_groups[arm]
        print(f"   Arm {arm} ({ARM_LABELS.get(arm, arm)}):")
        for i, group in enumerate(groups_list, 1):
            print(f"     Group {i}: {group['group_id']} - {group['specialty']} ({group['group_key']})")
    
    # Run tests
    all_results: List[Tuple[str, Dict[str, str], Dict[str, bool]]] = []
    test_num = 0
    
    for arm in ARMS:
        groups_list = arm_to_groups[arm]
        for group in groups_list:
            test_num += 1
            results = process_test(
                base_dir,
                run_tag,
                arm,
                group,
                test_num,
                len(ARMS) * 2,
                skip_s3_s4=args.skip_s3_s4,
            )
            all_results.append((arm, group, results))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    success_count = 0
    for arm, group, results in all_results:
        all_passed = all(results.values())
        status = "✅" if all_passed else "⚠️"
        if all_passed:
            success_count += 1
        
        print(f"{status} Arm {arm} - {group['group_id']} ({group['specialty']}):")
        print(f"   S1/S2: {'✅' if results['s1_s2'] else '❌'}")
        print(f"   S3: {'✅' if results['s3'] else '❌'}")
        print(f"   S4: {'✅' if results['s4'] else '❌'}")
        print(f"   PDF: {'✅' if results['pdf'] else '❌'}")
    
    print("=" * 70)
    print(f"Total: {success_count}/{len(all_results)} tests passed completely")
    print(f"Run tag: {run_tag}")
    print(f"PDF output: {base_dir / '6_Distributions' / 'QA_Packets'}")
    print("=" * 70)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Test Failed Groups Only

This script re-runs tests for specific groups that failed in previous test runs.

Usage:
    python 3_Code/Scripts/test_failed_groups.py --run_tag TEST_FIX_VERIFY_v2_20251221_104635
"""

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

ARM_LABELS = {
    "A": "Baseline",
    "B": "RAG Only",
    "C": "Thinking",
    "D": "Synergy",
    "E": "High-End",
    "F": "Benchmark"
}

# Failed groups from the test run
FAILED_GROUPS = [
    # S1/S2 failures (MAX_TOKENS)
    {"arm": "C", "group_id": "grp_7a520348e0", "group_key": "liver__diagnostic_imaging", "specialty": "ir"},
    {"arm": "D", "group_id": "grp_d269a8c5ab", "group_key": "thyroid__imaging_procedural_techniques", "specialty": "neuro_hn_rad"},
    {"arm": "D", "group_id": "grp_00359a35ac", "group_key": "endocrine__imaging_procedural_techniques", "specialty": "nuclear_medicine"},
    {"arm": "E", "group_id": "grp_3126ec9e7d", "group_key": "cranial_nervous_system__diagnostic_imaging__spine_spinalcord_disease", "specialty": "ped_rad"},
    {"arm": "E", "group_id": "grp_928d4ef3ee", "group_key": "physics__xray__computed_rad_cr", "specialty": "phys_qc_medinfo"},
    
    # S4 failures (quota exhaustion - will retry if quota is available)
    {"arm": "A", "group_id": "grp_c09beee26e", "group_key": "pancreas__imaging_procedural_techniques", "specialty": "abdominal_rad"},
    {"arm": "A", "group_id": "grp_cbcba66e24", "group_key": "specific_objectives__diagnostic_imaging__benign_breast_disease", "specialty": "breast_rad"},
    {"arm": "B", "group_id": "grp_afe6e9c0b9", "group_key": "heart__diagnostic_imaging__congenital_heart_disease", "specialty": "cv_rad"},
    {"arm": "B", "group_id": "grp_20e6b79963", "group_key": "gynecology__congenital_anomaly", "specialty": "gu_rad"},
    {"arm": "C", "group_id": "grp_c467f038b8", "group_key": "bone_soft_tissue__diagnostic_imaging__other_disease", "specialty": "msk_rad"},
    {"arm": "F", "group_id": "grp_1cb38da503", "group_key": "diaphragm_chest_wall__radiologic_anatomy", "specialty": "thoracic_rad"},
    {"arm": "F", "group_id": "grp_4b36ed8159", "group_key": "pharynx_esophagus__diagnostic_imaging", "specialty": "abdominal_rad"},
]


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
        description="Test failed groups from previous test run",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument(
        "--run_tag",
        type=str,
        required=True,
        help="Run tag from previous test (e.g., TEST_FIX_VERIFY_v2_20251221_104635)",
    )
    parser.add_argument(
        "--skip_s3_s4",
        action="store_true",
        help="Skip S3/S4 (image generation)",
    )
    parser.add_argument(
        "--only_s1_s2",
        action="store_true",
        help="Only run S1/S2 (for MAX_TOKENS failures)",
    )
    parser.add_argument(
        "--only_s4",
        action="store_true",
        help="Only run S4 (for quota exhaustion failures)",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        print(f"❌ Base directory does not exist: {base_dir}")
        sys.exit(1)
    
    run_tag = args.run_tag
    
    print("=" * 70)
    print("Re-testing Failed Groups")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Total failed groups: {len(FAILED_GROUPS)}")
    if args.skip_s3_s4:
        print("⚠️  S3/S4 will be skipped")
    if args.only_s1_s2:
        print("⚠️  Only S1/S2 will run")
    if args.only_s4:
        print("⚠️  Only S4 will run")
    print("=" * 70)
    
    # Filter groups based on flags
    groups_to_test = FAILED_GROUPS
    if args.only_s1_s2:
        # Only S1/S2 failures (MAX_TOKENS)
        groups_to_test = [g for g in FAILED_GROUPS if g["arm"] in ["C", "D", "E"]]
    elif args.only_s4:
        # Only S4 failures (quota exhaustion)
        groups_to_test = [g for g in FAILED_GROUPS if g["arm"] in ["A", "B", "C", "F"]]
    
    print(f"\n>>> Testing {len(groups_to_test)} groups...")
    
    # Run tests
    all_results: List[tuple] = []
    test_num = 0
    
    for group in groups_to_test:
        test_num += 1
        results = process_test(
            base_dir,
            run_tag,
            group["arm"],
            group,
            test_num,
            len(groups_to_test),
            skip_s3_s4=args.skip_s3_s4 or args.only_s1_s2,
        )
        all_results.append((group["arm"], group, results))
    
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
        if not args.only_s1_s2:
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


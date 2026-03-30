#!/usr/bin/env python3
"""
Test 6-Arm Full Pipeline for a Single Group

This script:
1. Selects one group (randomly or by group_key/group_id)
2. Runs full pipeline for all 6 arms (A, B, C, D, E, F):
   - S1/S2: JSON generation
   - S3: Policy resolver
   - S4: Image generator
   - PDF: PDF generation
   - Anki: Anki deck export
3. Reports results

Usage:
    python 3_Code/Scripts/test_6arm_single_group.py [--group_key KEY] [--group_id ID] [--run_tag TAG] [--seed 42]
"""

import argparse
import csv
import json
import random
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


def select_group(
    groups: List[Dict[str, str]],
    group_key: Optional[str] = None,
    group_id: Optional[str] = None,
    seed: int = 42,
) -> Dict[str, str]:
    """Select a group by key/id or randomly."""
    if group_key:
        for group in groups:
            if group["group_key"] == group_key:
                return group
        raise ValueError(f"Group key not found: {group_key}")
    
    if group_id:
        for group in groups:
            if group["group_id"] == group_id:
                return group
        raise ValueError(f"Group ID not found: {group_id}")
    
    # Random selection
    random.seed(seed)
    return random.choice(groups)


def run_command(cmd: List[str], cwd: Optional[Path] = None, capture_output: bool = False) -> bool:
    """Run a command and return True if successful."""
    if not capture_output:
        print(f"  >>> {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            capture_output=capture_output,
            text=True,
        )
        return result.returncode == 0
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


def generate_anki(base_dir: Path, run_tag: str, arm: str) -> bool:
    """Generate Anki deck."""
    print(f"    [Anki] Generating for arm {arm}...")
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "07_export_anki_deck.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
    ]
    
    return run_command(cmd, cwd=base_dir)


def process_arm(
    base_dir: Path,
    run_tag: str,
    arm: str,
    group_key: str,
    skip_s3_s4: bool = False,
) -> Dict[str, bool]:
    """Process one arm through full pipeline."""
    results = {
        "s1_s2": False,
        "s3": False,
        "s4": False,
        "pdf": False,
        "anki": False,
    }
    
    print(f"\n  [{arm}] {ARM_LABELS.get(arm, arm)}")
    print("  " + "-" * 50)
    
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
    
    # Anki
    if generate_anki(base_dir, run_tag, arm):
        results["anki"] = True
        anki_path = base_dir / "6_Distributions" / "anki" / f"MeducAI_{run_tag}_arm{arm}.apkg"
        if anki_path.exists():
            print(f"    ✅ Anki deck created: {anki_path.name}")
        else:
            print(f"    ⚠️  Anki command succeeded but file not found")
    else:
        print(f"    ❌ Anki generation failed")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Test 6-arm full pipeline for a single group",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument(
        "--run_tag",
        type=str,
        default=None,
        help="Run tag (default: TEST_6ARM_YYYYMMDD_HHMMSS)",
    )
    parser.add_argument(
        "--group_key",
        type=str,
        default=None,
        help="Group key to test (if not specified, random selection)",
    )
    parser.add_argument(
        "--group_id",
        type=str,
        default=None,
        help="Group ID to test (alternative to --group_key)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument(
        "--skip_s3_s4",
        action="store_true",
        help="Skip S3/S4 (image generation)",
    )
    parser.add_argument(
        "--arms",
        type=str,
        nargs="+",
        default=ARMS,
        help=f"Arms to execute (default: {ARMS})",
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
        run_tag = f"TEST_6ARM_{timestamp}"
    
    arms = [arm.upper() for arm in args.arms]
    
    print("=" * 70)
    print("6-Arm Full Pipeline Test (Single Group)")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Arms: {', '.join(arms)}")
    print(f"Seed: {args.seed}")
    if args.skip_s3_s4:
        print("⚠️  S3/S4 will be skipped")
    print("=" * 70)
    
    # Load groups
    groups_csv_path = base_dir / args.groups_csv
    print(f"\n>>> Loading groups from: {groups_csv_path}")
    groups = load_groups_canonical(groups_csv_path)
    print(f"   Loaded {len(groups)} groups")
    
    # Select group
    print(f"\n>>> Selecting group...")
    try:
        selected_group = select_group(
            groups,
            group_key=args.group_key,
            group_id=args.group_id,
            seed=args.seed,
        )
        print(f"   Selected: {selected_group['group_id']}")
        print(f"   Group key: {selected_group['group_key']}")
        print(f"   Specialty: {selected_group['specialty']}")
        print(f"   Anatomy: {selected_group['anatomy']}")
        print(f"   Modality/Type: {selected_group['modality_or_type']}")
        print(f"   Category: {selected_group['category']}")
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    # Process each arm
    print(f"\n>>> Processing {len(arms)} arms...")
    print("=" * 70)
    
    all_results = {}
    for arm in arms:
        results = process_arm(
            base_dir=base_dir,
            run_tag=run_tag,
            arm=arm,
            group_key=selected_group["group_key"],
            skip_s3_s4=args.skip_s3_s4,
        )
        all_results[arm] = results
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Run tag: {run_tag}")
    print(f"Group: {selected_group['group_id']} ({selected_group['group_key']})")
    print(f"Specialty: {selected_group['specialty']}")
    print()
    print("Results by arm:")
    print()
    
    for arm in arms:
        r = all_results[arm]
        status = "✅" if all(r.values()) else "⚠️"
        print(f"  [{arm}] {ARM_LABELS.get(arm, arm)}: {status}")
        print(f"    S1/S2: {'✅' if r['s1_s2'] else '❌'}")
        print(f"    S3:    {'✅' if r['s3'] else '❌'}")
        print(f"    S4:    {'✅' if r['s4'] else '❌'}")
        print(f"    PDF:   {'✅' if r['pdf'] else '❌'}")
        print(f"    Anki:  {'✅' if r['anki'] else '❌'}")
        print()
    
    # Overall status
    all_success = all(
        all(results.values())
        for results in all_results.values()
    )
    
    if all_success:
        print("✅ ALL ARMS COMPLETED SUCCESSFULLY")
    else:
        print("⚠️  SOME ARMS HAD ERRORS (see details above)")
    
    print("=" * 70)
    print(f"\nOutput files:")
    print(f"  Generated data: {base_dir / '2_Data' / 'metadata' / 'generated' / run_tag}")
    print(f"  PDFs: {base_dir / '6_Distributions' / 'QA_Packets'}")
    print(f"  Anki: {base_dir / '6_Distributions' / 'anki'}")
    print("=" * 70)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Generate sample PDF and Anki decks for co-authors.

This script:
1. Reads groups_canonical.csv
2. Randomly selects one group per specialty
3. Runs full pipeline (S1-S4) for selected groups
4. Generates PDF and Anki decks

Usage:
    python 3_Code/Scripts/generate_sample_pdf_anki.py [--base_dir .] [--run_tag SAMPLE_YYYYMMDD_HHMMSS] [--arm A] [--seed 42]
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


def select_random_groups_by_specialty(groups: List[Dict[str, str]], seed: int = 42) -> List[Dict[str, str]]:
    """Select one random group per specialty."""
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
    
    # Select one random group per specialty
    selected = []
    for specialty, group_list in specialty_groups.items():
        if group_list:
            selected_group = random.choice(group_list)
            selected.append(selected_group)
            print(f"  [{specialty}] Selected: {selected_group['group_id']} - {selected_group['group_key']}")
    
    return selected


def select_random_groups(groups: List[Dict[str, str]], num_groups: int = 3, seed: int = 42) -> List[Dict[str, str]]:
    """Select N random groups from all groups."""
    random.seed(seed)
    
    if num_groups >= len(groups):
        print(f"  Requested {num_groups} groups, but only {len(groups)} available. Returning all groups.")
        return groups
    
    selected = random.sample(groups, num_groups)
    print(f"  Selected {len(selected)} random groups:")
    for group in selected:
        specialty = group.get("specialty", "").strip()
        print(f"    [{specialty}] {group['group_id']} - {group['group_key']}")
    
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
) -> bool:
    """Run S1 and S2 for selected groups."""
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
        "--mode", "S0",
        "--stage", "both",
        "--only_group_keys_file", str(temp_group_keys_file),
        "--sample", str(len(selected_groups)),  # Process all selected groups
    ]
    
    success = run_command(cmd, cwd=base_dir)
    
    # Clean up temp file
    if temp_group_keys_file.exists():
        temp_group_keys_file.unlink()
    
    return success


def run_s3(
    base_dir: Path,
    run_tag: str,
    arm: str,
) -> bool:
    """Run S3 (policy resolver)."""
    print("\n" + "="*60)
    print("STEP 2a: Running S3 (Policy Resolver)")
    print("="*60)
    
    s3_script = base_dir / "3_Code" / "src" / "03_s3_policy_resolver.py"
    if not s3_script.exists():
        print(f"⚠️  S3 script not found: {s3_script}")
        print("   Skipping S3 (assuming already run)")
        return True
    
    cmd = [
        sys.executable,
        str(s3_script),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
    ]
    
    return run_command(cmd, cwd=base_dir)


def run_s4(
    base_dir: Path,
    run_tag: str,
    arm: str,
) -> bool:
    """Run S4 (image generation)."""
    print("\n" + "="*60)
    print("STEP 2b: Running S4 (Image Generator)")
    print("="*60)
    
    s4_script = base_dir / "3_Code" / "src" / "04_s4_image_generator.py"
    if not s4_script.exists():
        print(f"⚠️  S4 script not found: {s4_script}")
        print("   Skipping S4 (assuming images already exist)")
        return True
    
    cmd = [
        sys.executable,
        str(s4_script),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
    ]
    
    return run_command(cmd, cwd=base_dir)


def load_s1_group_mapping(s1_path: Path) -> Dict[str, str]:
    """Load group_key -> group_id mapping from S1 results."""
    mapping = {}
    if not s1_path.exists():
        return mapping
    
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                group_id = record.get("group_id", "").strip()
                group_key = record.get("group_key", "").strip()
                if group_id and group_key:
                    mapping[group_key] = group_id
            except json.JSONDecodeError:
                continue
    
    return mapping


def generate_pdfs(
    base_dir: Path,
    run_tag: str,
    arm: str,
    selected_groups: List[Dict[str, str]],
) -> bool:
    """Generate PDFs for selected groups."""
    print("\n" + "="*60)
    print("STEP 3: Generating PDFs")
    print("="*60)
    
    # Load S1 results to get actual group_id mapping
    s1_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"stage1_struct__arm{arm}.jsonl"
    group_key_to_id = load_s1_group_mapping(s1_path)
    
    if not group_key_to_id:
        print(f"⚠️  No S1 results found at {s1_path}")
        print("   Cannot generate PDFs without S1 data")
        return False
    
    print(f"   Loaded {len(group_key_to_id)} group mappings from S1 results")
    
    out_dir = base_dir / "6_Distributions" / "QA_Packets"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    skipped_count = 0
    
    for group in selected_groups:
        group_key = group["group_key"]
        csv_group_id = group["group_id"]  # Original CSV group_id (for display)
        specialty = group["specialty"]
        
        # Get actual group_id from S1 results
        actual_group_id = group_key_to_id.get(group_key)
        
        if not actual_group_id:
            print(f"\n⚠️  Skipping {csv_group_id} ({specialty}): group_key '{group_key}' not found in S1 results")
            skipped_count += 1
            continue
        
        print(f"\n>>> Generating PDF for {csv_group_id} ({specialty})...")
        print(f"    Using S1 group_id: {actual_group_id}")
        
        cmd = [
            sys.executable,
            str(base_dir / "3_Code" / "src" / "07_build_set_pdf.py"),
            "--base_dir", str(base_dir),
            "--run_tag", run_tag,
            "--arm", arm,
            "--group_id", actual_group_id,
            "--out_dir", str(out_dir),
            "--allow_missing_images",  # Allow missing images for flexible card counts
        ]
        
        if run_command(cmd, cwd=base_dir):
            pdf_path = out_dir / f"SET_{actual_group_id}_arm{arm}_{run_tag}.pdf"
            if pdf_path.exists():
                print(f"✅ PDF created: {pdf_path}")
                success_count += 1
            else:
                print(f"⚠️  PDF command succeeded but file not found: {pdf_path}")
        else:
            print(f"❌ Failed to generate PDF for {csv_group_id}")
    
    print(f"\n✅ Generated {success_count}/{len(selected_groups)} PDFs")
    if skipped_count > 0:
        print(f"⚠️  Skipped {skipped_count} groups (not found in S1 results)")
    return success_count > 0


def generate_anki_decks(
    base_dir: Path,
    run_tag: str,
    arm: str,
) -> bool:
    """Generate Anki decks."""
    print("\n" + "="*60)
    print("STEP 4: Generating Anki Decks")
    print("="*60)
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "07_export_anki_deck.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
    ]
    
    success = run_command(cmd, cwd=base_dir)
    
    if success:
        anki_path = base_dir / "6_Distributions" / "anki" / f"MeducAI_{run_tag}_arm{arm}.apkg"
        if anki_path.exists():
            print(f"✅ Anki deck created: {anki_path}")
        else:
            print(f"⚠️  Anki command succeeded but file not found: {anki_path}")
    
    return success


def main():
    parser = argparse.ArgumentParser(
        description="Generate sample PDF and Anki decks for co-authors",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument(
        "--run_tag",
        type=str,
        default=None,
        help="Run tag (default: SAMPLE_YYYYMMDD_HHMMSS)",
    )
    parser.add_argument("--arm", type=str, default="A", help="Arm identifier (default: A)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument(
        "--num_groups",
        type=int,
        default=None,
        help="Number of random groups to select (default: one per specialty)",
    )
    parser.add_argument(
        "--skip_s1_s2",
        action="store_true",
        help="Skip S1/S2 (assume already run)",
    )
    parser.add_argument(
        "--skip_s3_s4",
        action="store_true",
        help="Skip S3/S4 (assume already run)",
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
        run_tag = f"SAMPLE_{timestamp}"
    
    arm = args.arm.upper()
    
    print("="*60)
    print("Sample PDF & Anki Generator for Co-Authors")
    print("="*60)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Arm: {arm}")
    print(f"Seed: {args.seed}")
    print("="*60)
    
    # Load groups
    groups_csv_path = base_dir / args.groups_csv
    print(f"\n>>> Loading groups from: {groups_csv_path}")
    groups = load_groups_canonical(groups_csv_path)
    print(f"   Loaded {len(groups)} groups")
    
    # Select random groups
    if args.num_groups:
        print(f"\n>>> Selecting {args.num_groups} random groups (seed={args.seed})...")
        selected_groups = select_random_groups(groups, num_groups=args.num_groups, seed=args.seed)
        print(f"\n✅ Selected {len(selected_groups)} random groups")
    else:
        print(f"\n>>> Selecting one random group per specialty (seed={args.seed})...")
        selected_groups = select_random_groups_by_specialty(groups, seed=args.seed)
        print(f"\n✅ Selected {len(selected_groups)} groups from {len(set(g['specialty'] for g in selected_groups))} specialties")
    
    # Run pipeline
    all_success = True
    
    # Step 1: S1 and S2
    if not args.skip_s1_s2:
        if not run_s1_s2(base_dir, run_tag, arm, selected_groups):
            print("❌ S1/S2 failed")
            all_success = False
            sys.exit(1)
    else:
        print("\n>>> Skipping S1/S2 (--skip_s1_s2)")
    
    # Step 2: S3 and S4
    if not args.skip_s3_s4:
        if not run_s3(base_dir, run_tag, arm):
            print("⚠️  S3 failed (continuing anyway)")
        if not run_s4(base_dir, run_tag, arm):
            print("⚠️  S4 failed (continuing anyway)")
    else:
        print("\n>>> Skipping S3/S4 (--skip_s3_s4)")
    
    # Step 3: Generate PDFs
    if not generate_pdfs(base_dir, run_tag, arm, selected_groups):
        print("❌ PDF generation had errors")
        all_success = False
    
    # Step 4: Generate Anki decks
    if not generate_anki_decks(base_dir, run_tag, arm):
        print("❌ Anki generation failed")
        all_success = False
    
    # Summary
    print("\n" + "="*60)
    if all_success:
        print("✅ SUCCESS: All steps completed")
        print(f"\nOutput files:")
        print(f"  PDFs: {base_dir / '6_Distributions' / 'QA_Packets'}")
        print(f"  Anki: {base_dir / '6_Distributions' / 'anki' / f'MeducAI_{run_tag}_arm{arm}.apkg'}")
    else:
        print("⚠️  COMPLETED WITH ERRORS")
        print("   Check the output above for details")
    print("="*60)


if __name__ == "__main__":
    main()


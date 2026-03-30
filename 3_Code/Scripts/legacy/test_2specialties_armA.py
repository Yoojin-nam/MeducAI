#!/usr/bin/env python3
"""
Test 2 random specialties with 1 group each for Arm A (PDF and Anki).

This script:
1. Reads groups_canonical.csv
2. Randomly selects 2 specialties
3. Selects 1 random group per selected specialty
4. Runs full pipeline (S1-S4) for selected groups (Arm A only)
5. Generates PDF and Anki decks

Usage:
    python 3_Code/Scripts/test_2specialties_armA.py [--base_dir .] [--run_tag TEST_YYYYMMDD_HHMMSS] [--seed 42]
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
            })
    
    return groups


def select_2_specialties_1_group_each(groups: List[Dict[str, str]], seed: int = 42) -> List[Dict[str, str]]:
    """Select 2 random specialties, then 1 random group per specialty."""
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
    
    # Select 2 random specialties
    available_specialties = [s for s in specialty_groups.keys() if specialty_groups[s]]
    if len(available_specialties) < 2:
        raise ValueError(f"Need at least 2 specialties, but only found {len(available_specialties)}")
    
    selected_specialties = random.sample(available_specialties, 2)
    print(f"\nSelected 2 specialties: {selected_specialties}")
    
    # Select one random group per selected specialty
    selected = []
    for specialty in selected_specialties:
        group_list = specialty_groups[specialty]
        selected_group = random.choice(group_list)
        selected.append(selected_group)
        print(f"  [{specialty}] Selected: {selected_group['group_id']} - {selected_group['group_key']}")
    
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
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "01_generate_json.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
        "--mode", "S0",
        "--stage", "both",
        "--only_group_keys_file", str(temp_group_keys_file),
        "--sample", str(len(selected_groups)),
    ]
    
    success = run_command(cmd, cwd=base_dir)
    
    # Clean up temp file
    if temp_group_keys_file.exists():
        temp_group_keys_file.unlink()
    
    return success


def run_s3(base_dir: Path, run_tag: str, arm: str) -> bool:
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
    ]
    
    return run_command(cmd, cwd=base_dir)


def run_s4(base_dir: Path, run_tag: str, arm: str) -> bool:
    """Run S4 (image generation)."""
    print("\n" + "="*60)
    print("STEP 3: Running S4 (Image Generator)")
    print("="*60)
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "04_s4_image_generator.py"),
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
    print("STEP 4: Generating PDFs")
    print("="*60)
    
    s1_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"stage1_struct__arm{arm}.jsonl"
    group_key_to_id = load_s1_group_mapping(s1_path)
    
    if not group_key_to_id:
        print(f"⚠️  No S1 results found at {s1_path}")
        return False
    
    out_dir = base_dir / "6_Distributions" / "QA_Packets"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    for group in selected_groups:
        group_key = group["group_key"]
        actual_group_id = group_key_to_id.get(group_key)
        
        if not actual_group_id:
            print(f"\n⚠️  Skipping {group['group_id']} ({group['specialty']}): group_key '{group_key}' not found in S1 results")
            continue
        
        print(f"\n>>> Generating PDF for {group['group_id']} ({group['specialty']})...")
        
        cmd = [
            sys.executable,
            str(base_dir / "3_Code" / "src" / "07_build_set_pdf.py"),
            "--base_dir", str(base_dir),
            "--run_tag", run_tag,
            "--arm", arm,
            "--group_id", actual_group_id,
            "--out_dir", str(out_dir),
        ]
        
        if run_command(cmd, cwd=base_dir):
            pdf_path = out_dir / f"SET_{actual_group_id}_arm{arm}_{run_tag}.pdf"
            if pdf_path.exists():
                print(f"✅ PDF created: {pdf_path}")
                success_count += 1
            else:
                print(f"⚠️  PDF command succeeded but file not found: {pdf_path}")
        else:
            print(f"❌ Failed to generate PDF for {group['group_id']}")
    
    print(f"\n✅ Generated {success_count}/{len(selected_groups)} PDFs")
    return success_count > 0


def generate_anki_decks(
    base_dir: Path,
    run_tag: str,
    arm: str,
) -> bool:
    """Generate Anki deck."""
    print("\n" + "="*60)
    print("STEP 5: Generating Anki Deck")
    print("="*60)
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "07_export_anki_deck.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
    ]
    
    if run_command(cmd, cwd=base_dir):
        anki_path = base_dir / "6_Distributions" / "anki" / f"MeducAI_{run_tag}_arm{arm}.apkg"
        if anki_path.exists():
            print(f"✅ Anki deck created: {anki_path}")
            return True
        else:
            print(f"⚠️  Anki command succeeded but file not found: {anki_path}")
            return False
    else:
        print(f"❌ Failed to generate Anki deck")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test 2 random specialties with 1 group each for Arm A (PDF and Anki)"
    )
    parser.add_argument("--base_dir", default=".", help="Base directory (default: .)")
    parser.add_argument(
        "--run_tag",
        default=None,
        help="Run tag (default: TEST_YYYYMMDD_HHMMSS)"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    
    # Generate run_tag if not provided
    if args.run_tag:
        run_tag = args.run_tag
    else:
        run_tag = f"TEST_2SPEC_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print("="*70)
    print("🧪 Test: 2 Random Specialties (1 group each) - Arm A")
    print("="*70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Seed: {args.seed}")
    print("="*70)
    
    # Load groups
    csv_path = base_dir / "2_Data" / "metadata" / "groups_canonical.csv"
    print(f"\nLoading groups from: {csv_path}")
    groups = load_groups_canonical(csv_path)
    print(f"Loaded {len(groups)} groups")
    
    # Select 2 specialties, 1 group each
    selected_groups = select_2_specialties_1_group_each(groups, seed=args.seed)
    
    arm = "A"
    
    # Run pipeline
    results = {
        "s1_s2": False,
        "s3": False,
        "s4": False,
        "pdf": False,
        "anki": False,
    }
    
    # S1/S2
    if run_s1_s2(base_dir, run_tag, arm, selected_groups):
        results["s1_s2"] = True
        print("\n✅ S1/S2 completed")
    else:
        print("\n❌ S1/S2 failed")
        print("Cannot continue without S1/S2")
        return 1
    
    # S3
    if run_s3(base_dir, run_tag, arm):
        results["s3"] = True
        print("\n✅ S3 completed")
    else:
        print("\n⚠️  S3 failed (continuing anyway)")
    
    # S4
    if run_s4(base_dir, run_tag, arm):
        results["s4"] = True
        print("\n✅ S4 completed")
    else:
        print("\n⚠️  S4 failed (continuing anyway)")
    
    # PDFs
    if generate_pdfs(base_dir, run_tag, arm, selected_groups):
        results["pdf"] = True
        print("\n✅ PDF generation completed")
    else:
        print("\n❌ PDF generation failed")
    
    # Anki
    if generate_anki_decks(base_dir, run_tag, arm):
        results["anki"] = True
        print("\n✅ Anki generation completed")
    else:
        print("\n❌ Anki generation failed")
    
    # Summary
    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    print(f"Run tag: {run_tag}")
    print(f"Selected groups: {len(selected_groups)}")
    for group in selected_groups:
        print(f"  - {group['group_id']}: {group['group_key']} ({group['specialty']})")
    print("\nResults:")
    for step, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {step.upper()}")
    print("="*70)
    
    if all(results.values()):
        print("\n🎉 All steps completed successfully!")
        return 0
    else:
        print("\n⚠️  Some steps failed. Check output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


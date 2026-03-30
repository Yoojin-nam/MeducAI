#!/usr/bin/env python3
"""
Generate sample PDF and Anki for S0 QA (18 groups, Arm A only)

This script:
1. Reads groups_canonical.csv
2. Selects 18 groups according to S0 canonical rule:
   - Stage 1: Each specialty minimum 1 group (highest weight)
   - Stage 2: Remaining 7 groups by weight (highest first)
3. Runs full pipeline (S1-S4) for all selected groups (Arm A only)
4. Generates one combined PDF for all groups
5. Generates one Anki deck for all groups

Reference: 0_Protocol/06_QA_and_Study/QA_Operations/S0_18Group_Selection_Rule_Canonical.md

Usage:
    python 3_Code/Scripts/generate_sample_all_specialties.py [--base_dir .] [--run_tag SAMPLE_ALL_YYYYMMDD_HHMMSS] [--seed 42]
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


def load_group_weights(base_dir: Path) -> Dict[str, float]:
    """Load group weights from EDA results."""
    weight_path = base_dir / "2_Data" / "eda" / "EDA_1780_Decision" / "tables" / "groups_weight_expected_cards.csv"
    
    if not weight_path.exists():
        print(f"⚠️  Weight file not found: {weight_path}")
        print("   Falling back to uniform selection (no weight data)")
        return {}
    
    weights = {}
    with open(weight_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            group_key = row.get("_group_key", "").strip()
            weight_sum = row.get("group_weight_sum", "0").strip()
            try:
                weights[group_key] = float(weight_sum)
            except (ValueError, TypeError):
                continue
    
    print(f"   Loaded weights for {len(weights)} groups")
    return weights


def select_18_groups_s0_rule(
    groups: List[Dict[str, str]], 
    base_dir: Path,
    seed: int = 42
) -> List[Dict[str, str]]:
    """
    Select 18 groups according to S0 canonical rule:
    
    Stage 1: Each specialty minimum 1 group (highest weight)
    Stage 2: Select 7 groups by specialty total weight (highest specialty first, one per specialty)
            - Calculate total weight for each specialty (sum of all groups)
            - Sort specialties by total weight (descending)
            - Select one group per specialty (highest weight group from remaining groups)
            - Continue until 7 groups are selected
    
    Reference: 0_Protocol/06_QA_and_Study/QA_Operations/S0_18Group_Selection_Rule_Canonical.md
    """
    random.seed(seed)
    
    # Load weights
    weights = load_group_weights(base_dir)
    has_weights = len(weights) > 0
    
    # Add weight to each group
    groups_with_weight = []
    for group in groups:
        group_key = group.get("group_key", "").strip()
        weight = weights.get(group_key, 0.0) if has_weights else 0.0
        groups_with_weight.append({
            **group,
            "weight": weight,
        })
    
    # Group by specialty
    specialty_groups: Dict[str, List[Dict[str, str]]] = {}
    for group in groups_with_weight:
        specialty = group.get("specialty", "").strip()
        if not specialty:
            continue
        if specialty not in specialty_groups:
            specialty_groups[specialty] = []
        specialty_groups[specialty].append(group)
    
    print(f"\n>>> Selecting 18 groups (S0 canonical rule)")
    print(f"   Found {len(specialty_groups)} specialties")
    
    # Stage 1: Each specialty minimum 1 group (highest weight)
    selected_stage1 = []
    selected_keys_stage1 = set()
    
    for specialty in sorted(specialty_groups.keys()):
        specialty_list = specialty_groups[specialty]
        # Sort by weight (descending), then by group_key for tie-breaking
        specialty_list.sort(key=lambda x: (x.get("weight", 0), x.get("group_key", "")), reverse=True)
        
        if specialty_list:
            best_group = specialty_list[0]
            selected_stage1.append(best_group)
            selected_keys_stage1.add(best_group["group_key"])
            print(f"  Stage 1 [{specialty:20s}]: {best_group['group_id']} - {best_group['group_key']} (weight: {best_group.get('weight', 0):.2f})")
    
    print(f"\n   Stage 1 complete: {len(selected_stage1)} groups selected")
    
    # Stage 2: Select 7 groups by specialty total weight (highest specialty first, one per specialty)
    # Calculate specialty total weights (sum of all groups in each specialty)
    specialty_total_weights = {}
    for specialty, specialty_list in specialty_groups.items():
        total_weight = sum(g.get("weight", 0) for g in specialty_list)
        specialty_total_weights[specialty] = total_weight
    
    # Sort specialties by total weight (descending)
    sorted_specialties = sorted(specialty_total_weights.items(), key=lambda x: (-x[1], x[0]))
    
    # Select one group per specialty (highest weight specialty first)
    # Skip already selected groups from Stage 1
    selected_stage2 = []
    for specialty, _ in sorted_specialties:
        specialty_list = specialty_groups[specialty]
        # Get remaining groups (not selected in Stage 1)
        remaining_in_specialty = [g for g in specialty_list if g["group_key"] not in selected_keys_stage1]
        if remaining_in_specialty:
            # Sort by weight (descending), then by group_key for tie-breaking
            remaining_in_specialty.sort(key=lambda x: (x.get("weight", 0), x.get("group_key", "")), reverse=True)
            best_remaining = remaining_in_specialty[0]
            selected_stage2.append(best_remaining)
            selected_keys_stage1.add(best_remaining["group_key"])
            print(f"  Stage 2 [{specialty:20s}]: {best_remaining['group_id']} - {best_remaining['group_key']} (weight: {best_remaining.get('weight', 0):.2f}, specialty_total: {specialty_total_weights[specialty]:.2f})")
        
        # Stop when we have 7 groups
        if len(selected_stage2) >= 7:
            break
    
    print(f"\n   Stage 2 complete: {len(selected_stage2)} groups selected")
    
    # Combine results
    all_selected = selected_stage1 + selected_stage2
    
    # Remove weight from output (not needed in return)
    for group in all_selected:
        if "weight" in group:
            del group["weight"]
    
    print(f"   Total: {len(all_selected)} groups selected")
    
    return all_selected


def select_random_groups_by_specialty(groups: List[Dict[str, str]], seed: int = 42) -> List[Dict[str, str]]:
    """
    Legacy function: Select one random group per specialty.
    
    DEPRECATED: Use select_18_groups_s0_rule() for S0 QA.
    This function is kept for backward compatibility.
    """
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
    
    print(f"Selected {len(selected_groups)} groups from {len(set(g['specialty'] for g in selected_groups))} specialties:")
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
    image_model: Optional[str] = None,
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
    
    if image_model:
        cmd.extend(["--image_model", image_model])
    
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


def generate_combined_pdf(
    base_dir: Path,
    run_tag: str,
    arm: str,
    selected_groups: List[Dict[str, str]],
) -> bool:
    """Generate one combined PDF for all selected groups."""
    print("\n" + "="*60)
    print("STEP 3: Generating Combined PDF (all specialties)")
    print("="*60)
    
    # Import PDF building module
    pdf_module_path = base_dir / "3_Code" / "src" / "07_build_set_pdf.py"
    if not pdf_module_path.exists():
        print(f"❌ PDF module not found: {pdf_module_path}")
        return False
    
    # Import the module
    import importlib.util
    spec = importlib.util.spec_from_file_location("pdf_builder", pdf_module_path)
    pdf_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pdf_module)
    
    # Load S1 results to get actual group_id mapping
    s1_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"stage1_struct__arm{arm}.jsonl"
    group_key_to_id = load_s1_group_mapping(s1_path)
    
    if not group_key_to_id:
        print(f"⚠️  No S1 results found at {s1_path}")
        print("   Cannot generate PDF without S1 data")
        return False
    
    print(f"   Loaded {len(group_key_to_id)} group mappings from S1 results")
    
    # Get all valid group_ids
    valid_group_ids = []
    for group in selected_groups:
        group_key = group["group_key"]
        actual_group_id = group_key_to_id.get(group_key)
        if actual_group_id:
            valid_group_ids.append((actual_group_id, group))
        else:
            print(f"   ⚠️  Skipping {group['group_id']} ({group['specialty']}): group_key '{group_key}' not found in S1 results")
    
    if not valid_group_ids:
        print("   ❌ No valid groups found for PDF generation")
        return False
    
    print(f"   Generating combined PDF with {len(valid_group_ids)} groups")
    
    # Setup paths
    gen_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    s2_path = gen_dir / f"s2_results__arm{arm}.jsonl"
    s3_policy_path = gen_dir / f"image_policy_manifest__arm{arm}.jsonl"
    s4_manifest_path = gen_dir / f"s4_image_manifest__arm{arm}.jsonl"
    
    # Import reportlab components
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer
    
    # Create output directory
    out_dir = base_dir / "6_Distributions" / "QA_Packets"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Output filename
    pdf_filename = f"SAMPLE_ALL_SPECIALTIES_arm{arm}_{run_tag}.pdf"
    pdf_path = out_dir / pdf_filename
    
    # Create PDF in landscape mode
    page_size = landscape(A4)
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=page_size,
        rightMargin=0.75 * cm,
        leftMargin=0.75 * cm,
        topMargin=0.75 * cm,
        bottomMargin=0.75 * cm,
    )
    
    page_width = page_size[0]
    page_height = page_size[1]
    
    story = []
    styles, custom_styles, korean_font, korean_font_bold = pdf_module.create_pdf_styles()
    
    # Add title page
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=custom_styles["title"],
        fontSize=20,
        spaceAfter=20,
    )
    story.append(Paragraph("Sample PDF - All Specialties", title_style))
    story.append(Paragraph(f"Run Tag: {run_tag}", custom_styles["header_small"]))
    story.append(Paragraph(f"Arm: {arm}", custom_styles["header_small"]))
    story.append(Paragraph(f"Total Groups: {len(valid_group_ids)}", custom_styles["header_small"]))
    story.append(PageBreak())
    
    # Process each group
    for idx, (actual_group_id, group_info) in enumerate(valid_group_ids, 1):
        specialty = group_info["specialty"]
        group_key = group_info["group_key"]
        
        print(f"  [{idx}/{len(valid_group_ids)}] Processing {specialty}...")
        
        # Load data for this group
        s1_record = pdf_module.load_s1_struct(s1_path, actual_group_id)
        if not s1_record:
            print(f"    ⚠️  S1 record not found, skipping")
            continue
        
        s2_records = pdf_module.load_s2_results(s2_path, actual_group_id)
        if not s2_records:
            print(f"    ⚠️  S2 records not found, skipping")
            continue
        
        policy_mapping = pdf_module.load_s3_policy_manifest(s3_policy_path, actual_group_id)
        image_mapping = pdf_module.load_s4_image_manifest(s4_manifest_path, actual_group_id, base_dir, run_tag)
        
        # Master Table (header will be added in build_master_table_section)
        master_table_md = s1_record.get("master_table_markdown_kr", "")
        if master_table_md:
            pdf_module.build_master_table_section(
                story, master_table_md, custom_styles, page_width, page_height,
                korean_font, korean_font_bold, s1_record=s1_record, specialty=specialty
            )
            story.append(PageBreak())
        
        # Infographic
        infographic_path = image_mapping.get(("S1_TABLE_VISUAL", None, None))
        if infographic_path:
            pdf_module.build_infographic_section(story, infographic_path, custom_styles, allow_missing=True, page_width=page_width, page_height=page_height)
        else:
            # Add placeholder if no infographic
            story.append(Paragraph("(Infographic not available)", custom_styles["card_text"]))
        story.append(PageBreak())
        
        # Cards
        pdf_module.build_cards_section(
            story,
            s2_records,
            policy_mapping,
            image_mapping,
            custom_styles,
            page_width,
            page_height,
            allow_missing_images=True,
        )
        
        # Note: build_cards_section already adds PageBreak() after the last card,
        # so we don't need to add any separator between groups
    
    # Build PDF
    try:
        doc.build(story)
        print(f"\n✅ Combined PDF created: {pdf_path.name}")
        return True
    except Exception as e:
        print(f"\n❌ Failed to create combined PDF: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_anki_deck(
    base_dir: Path,
    run_tag: str,
    arm: str,
    num_specialties: int,
) -> bool:
    """Generate one Anki deck for all groups."""
    print("\n" + "="*60)
    print("STEP 4: Generating Anki Deck (all specialties)")
    print("="*60)
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "07_export_anki_deck.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
        "--allow_missing_images",  # Allow missing images for sample generation
    ]
    
    success = run_command(cmd, cwd=base_dir)
    
    if success:
        anki_path = base_dir / "6_Distributions" / "anki" / f"MeducAI_{run_tag}_arm{arm}.apkg"
        if anki_path.exists():
            print(f"✅ Anki deck created: {anki_path.name}")
            print(f"   Contains cards from all {num_specialties} specialties")
        else:
            print(f"⚠️  Anki command succeeded but file not found: {anki_path}")
    
    return success


def main():
    parser = argparse.ArgumentParser(
        description="Generate sample PDF and Anki for all specialties (Arm A only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument(
        "--run_tag",
        type=str,
        default=None,
        help="Run tag (default: SAMPLE_ALL_YYYYMMDD_HHMMSS)",
    )
    parser.add_argument("--arm", type=str, default="A", help="Arm identifier (default: A)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
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
    parser.add_argument(
        "--image_model",
        type=str,
        default=None,
        help="Image generation model. Options: 'nano-banana-pro' (default, high quality), 'nano-banana' (faster, lower quality). "
             "Can also use full model names: 'models/nano-banana-pro-preview' or 'models/gemini-2.5-flash-image'.",
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
        run_tag = f"SAMPLE_ALL_{timestamp}"
    
    arm = args.arm.upper()
    
    print("="*70)
    print("Sample PDF & Anki Generator for All Specialties (Arm A)")
    print("="*70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Arm: {arm}")
    print(f"Seed: {args.seed}")
    print("="*70)
    
    # Load groups
    groups_csv_path = base_dir / args.groups_csv
    print(f"\n>>> Loading groups from: {groups_csv_path}")
    groups = load_groups_canonical(groups_csv_path)
    print(f"   Loaded {len(groups)} groups")
    
    # Select 18 groups according to S0 canonical rule
    print(f"\n>>> Selecting 18 groups (S0 canonical rule, seed={args.seed})...")
    selected_groups = select_18_groups_s0_rule(groups, base_dir=base_dir, seed=args.seed)
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
        if not run_s4(base_dir, run_tag, arm, image_model=args.image_model):
            print("⚠️  S4 failed (continuing anyway)")
    else:
        print("\n>>> Skipping S3/S4 (--skip_s3_s4)")
    
    # Step 3: Generate one combined PDF for all specialties
    if not generate_combined_pdf(base_dir, run_tag, arm, selected_groups):
        print("❌ Combined PDF generation failed")
        all_success = False
    
    # Step 4: Generate one Anki deck for all groups
    if not generate_anki_deck(base_dir, run_tag, arm, len(selected_groups)):
        print("❌ Anki generation failed")
        all_success = False
    
    # Summary
    print("\n" + "="*70)
    if all_success:
        print("✅ SUCCESS: All steps completed")
    else:
        print("⚠️  COMPLETED WITH ERRORS")
        print("   Check the output above for details")
    
    print(f"\nOutput files:")
    print(f"  PDF (combined, all specialties): {base_dir / '6_Distributions' / 'QA_Packets' / f'SAMPLE_ALL_SPECIALTIES_arm{arm}_{run_tag}.pdf'}")
    print(f"  Anki (all specialties): {base_dir / '6_Distributions' / 'anki' / f'MeducAI_{run_tag}_arm{arm}.apkg'}")
    print("="*70)


if __name__ == "__main__":
    main()


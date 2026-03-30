#!/usr/bin/env python3
"""
Test 6-Arm Pipeline with Different Specialties

This script:
1. Selects 6 different groups from 6 different specialties (one per arm A-F)
2. Runs full pipeline for each arm with its selected group:
   - S1/S2: JSON generation
   - S3: Policy resolver
   - S4: Image generator
3. Generates one combined PDF (all 6 arms/groups)
4. Generates one combined Anki deck (all 6 arms)

Usage:
    python 3_Code/Scripts/test_6arm_different_specialties.py [--run_tag TAG] [--seed 42] [--skip_s3_s4]
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


def select_groups_by_specialty(
    groups: List[Dict[str, str]],
    arms: List[str],
    seed: int = 42,
) -> Dict[str, Dict[str, str]]:
    """Select one group per specialty, assigning to arms A-F."""
    # Group by specialty
    specialty_groups: Dict[str, List[Dict[str, str]]] = {}
    for group in groups:
        specialty = group["specialty"]
        if specialty:
            if specialty not in specialty_groups:
                specialty_groups[specialty] = []
            specialty_groups[specialty].append(group)
    
    # Get list of specialties
    specialties = sorted(specialty_groups.keys())
    
    if len(specialties) < len(arms):
        raise ValueError(
            f"Not enough specialties ({len(specialties)}) for {len(arms)} arms. "
            f"Need at least {len(arms)} different specialties."
        )
    
    # Randomly select specialties (one per arm)
    random.seed(seed)
    selected_specialties = random.sample(specialties, len(arms))
    
    # Select one group from each selected specialty
    arm_to_group: Dict[str, Dict[str, str]] = {}
    for arm, specialty in zip(arms, selected_specialties):
        specialty_group_list = specialty_groups[specialty]
        selected_group = random.choice(specialty_group_list)
        arm_to_group[arm] = selected_group
    
    return arm_to_group


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
            if e.stderr:
                print(f"  Error: {e.stderr}")
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


def run_s4(base_dir: Path, run_tag: str, arm: str, image_model: Optional[str] = None) -> bool:
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
    
    if image_model:
        cmd.extend(["--image_model", image_model])
    
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


def process_arm(
    base_dir: Path,
    run_tag: str,
    arm: str,
    group_key: str,
    skip_s3_s4: bool = False,
    image_model: Optional[str] = None,
) -> Dict[str, bool]:
    """Process one arm through full pipeline."""
    results = {
        "s1_s2": False,
        "s3": False,
        "s4": False,
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
        if run_s4(base_dir, run_tag, arm, image_model=image_model):
            results["s4"] = True
            print(f"    ✅ S4 completed")
        else:
            print(f"    ⚠️  S4 failed (continuing anyway)")
    
    return results


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
                group_key = record.get("group_key", "").strip()
                group_id = record.get("group_id", "").strip()
                if group_key and group_id:
                    mapping[group_key] = group_id
            except json.JSONDecodeError:
                continue
    
    return mapping


def generate_combined_pdf(
    base_dir: Path,
    run_tag: str,
    arms: List[str],
    arm_to_group: Dict[str, Dict[str, str]],
) -> bool:
    """Generate one combined PDF for all arms/groups."""
    print("\n" + "="*70)
    print("GENERATING COMBINED PDF (All Arms)")
    print("="*70)
    
    # Import PDF building module
    pdf_module_path = base_dir / "3_Code" / "src" / "07_build_set_pdf.py"
    if not pdf_module_path.exists():
        print(f"❌ PDF module not found: {pdf_module_path}")
        return False
    
    import importlib.util
    spec = importlib.util.spec_from_file_location("pdf_builder", pdf_module_path)
    pdf_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pdf_module)
    
    # Load S1 results for all arms to get group_id mappings
    gen_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    arm_to_group_id: Dict[str, str] = {}
    
    for arm in arms:
        s1_path = gen_dir / f"stage1_struct__arm{arm}.jsonl"
        group_key_to_id = load_s1_group_mapping(s1_path)
        group_key = arm_to_group[arm]["group_key"]
        actual_group_id = group_key_to_id.get(group_key)
        if actual_group_id:
            arm_to_group_id[arm] = actual_group_id
        else:
            print(f"  ⚠️  Arm {arm}: group_key '{group_key}' not found in S1 results")
    
    if not arm_to_group_id:
        print("  ❌ No valid groups found for PDF generation")
        return False
    
    print(f"  Generating combined PDF with {len(arm_to_group_id)} arms/groups")
    
    # Setup paths
    out_dir = base_dir / "6_Distributions" / "QA_Packets"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Import reportlab components
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer
    
    # Output filename
    pdf_filename = f"TEST_6ARM_ALL_{run_tag}.pdf"
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
    story.append(Paragraph("Test PDF - 6 Arms (Different Specialties)", title_style))
    story.append(Paragraph(f"Run Tag: {run_tag}", custom_styles["header_small"]))
    story.append(Paragraph(f"Total Arms: {len(arm_to_group_id)}", custom_styles["header_small"]))
    story.append(PageBreak())
    
    # Process each arm
    for idx, arm in enumerate(arms, 1):
        if arm not in arm_to_group_id:
            continue
        
        group_info = arm_to_group[arm]
        actual_group_id = arm_to_group_id[arm]
        specialty = group_info["specialty"]
        group_key = group_info["group_key"]
        
        print(f"  [{idx}/{len(arm_to_group_id)}] Processing Arm {arm} ({specialty})...")
        
        # Load data for this arm/group
        s1_path = gen_dir / f"stage1_struct__arm{arm}.jsonl"
        s2_path = gen_dir / f"s2_results__arm{arm}.jsonl"
        s3_policy_path = gen_dir / f"image_policy_manifest__arm{arm}.jsonl"
        s4_manifest_path = gen_dir / f"s4_image_manifest__arm{arm}.jsonl"
        
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
        
        # Add arm header
        arm_header_style = ParagraphStyle(
            "ArmHeader",
            parent=custom_styles["title"],
            fontSize=16,
            spaceAfter=10,
        )
        story.append(Paragraph(f"Arm {arm}: {ARM_LABELS.get(arm, arm)}", arm_header_style))
        story.append(Paragraph(f"Specialty: {specialty}", custom_styles["header_small"]))
        story.append(Paragraph(f"Group: {actual_group_id} ({group_key})", custom_styles["header_small"]))
        story.append(Spacer(1, 0.5 * cm))
        
        # Master Table
        master_table_md = s1_record.get("master_table_markdown_kr", "")
        if master_table_md:
            pdf_module.build_master_table_section(
                story, master_table_md, custom_styles, page_width, page_height,
                korean_font, korean_font_bold, s1_record, specialty=specialty
            )
            story.append(PageBreak())
        
        # Infographic
        infographic_path = image_mapping.get(("S1_TABLE_VISUAL", None, None))
        if infographic_path:
            pdf_module.build_infographic_section(
                story, infographic_path, custom_styles, allow_missing=True,
                page_width=page_width, page_height=page_height
            )
        else:
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
        
        # Add separator between arms (except last)
        if idx < len([a for a in arms if a in arm_to_group_id]):
            story.append(PageBreak())
            story.append(Paragraph("─" * 50, custom_styles["header_small"]))
            story.append(PageBreak())
    
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


def generate_combined_anki(
    base_dir: Path,
    run_tag: str,
    arms: List[str],
) -> bool:
    """Generate one combined Anki deck for all arms."""
    print("\n" + "="*70)
    print("GENERATING COMBINED ANKI DECK (All Arms)")
    print("="*70)
    
    # Import Anki export module
    anki_module_path = base_dir / "3_Code" / "src" / "07_export_anki_deck.py"
    if not anki_module_path.exists():
        print(f"❌ Anki module not found: {anki_module_path}")
        return False
    
    import importlib.util
    spec = importlib.util.spec_from_file_location("anki_export", anki_module_path)
    anki_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(anki_module)
    
    # Load S2 results and S4 manifests for all arms
    gen_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    all_s2_records = []
    all_image_mappings = {}
    
    for arm in arms:
        s2_path = gen_dir / f"s2_results__arm{arm}.jsonl"
        s4_manifest_path = gen_dir / f"s4_image_manifest__arm{arm}.jsonl"
        
        if s2_path.exists():
            s2_records = anki_module.load_s2_results(s2_path)
            # Tag records with arm
            for record in s2_records:
                record["_arm"] = arm
            all_s2_records.extend(s2_records)
            print(f"  Loaded {len(s2_records)} S2 records from arm {arm}")
        
        if s4_manifest_path.exists():
            image_mapping = anki_module.load_s4_manifest(s4_manifest_path)
            # Merge into combined mapping (keys are (run_tag, group_id, entity_id, card_role))
            all_image_mappings.update(image_mapping)
            print(f"  Loaded {len(image_mapping)} image mappings from arm {arm}")
    
    if not all_s2_records:
        print("  ❌ No S2 records found")
        return False
    
    print(f"  Total: {len(all_s2_records)} S2 records, {len(all_image_mappings)} image mappings")
    
    # Create combined deck
    import genanki
    deck_id = hash(f"{run_tag}_ALL_ARMS") % (2 ** 31)
    deck_name = f"MeducAI_{run_tag}_ALL_ARMS"
    deck = genanki.Deck(deck_id, deck_name)
    
    # Track statistics
    n_notes = 0
    n_q1 = 0
    n_q2 = 0
    n_q3 = 0
    n_with_images = 0
    media_files_set: set[str] = set()
    
    images_dir = gen_dir / "images"
    
    # Process each S2 record
    for s2_record in all_s2_records:
        run_tag_rec = str(s2_record.get("run_tag") or run_tag).strip()
        group_id = str(s2_record.get("group_id") or "").strip()
        entity_id = str(s2_record.get("entity_id") or "").strip()
        entity_name = str(s2_record.get("entity_name") or "").strip()
        group_path = str(s2_record.get("group_path") or "").strip()
        
        if not (group_id and entity_id):
            continue
        
        cards = s2_record.get("anki_cards") or []
        for card in cards:
            if not isinstance(card, dict):
                continue
            
            card_role = card.get("card_role", "").strip()
            
            note, media_filename, error = anki_module.process_card(
                card=card,
                run_tag=run_tag_rec,
                group_id=group_id,
                entity_id=entity_id,
                image_mapping=all_image_mappings,
                images_dir=images_dir,
                allow_missing_images=True,
                group_path=group_path,
            )
            
            if note:
                deck.add_note(note)
                n_notes += 1
                if card_role == "Q1":
                    n_q1 += 1
                elif card_role == "Q2":
                    n_q2 += 1
                elif card_role == "Q3":
                    n_q3 += 1
                if media_filename:
                    media_files_set.add(media_filename)
                    n_with_images += 1
            elif error:
                if card_role == "Q1":
                    print(f"  Warning: Q1 card failed: {error}")
                elif card_role == "Q3":
                    print(f"  Warning: Q3 card failed: {error}")
    
    # Create output directory
    out_dir = base_dir / "6_Distributions" / "anki"
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"MeducAI_{run_tag}_ALL_ARMS.apkg"
    
    # Generate package
    try:
        package = genanki.Package(deck)
        package.media_files = list(media_files_set)
        package.write_to_file(str(output_path))
        
        print(f"\n✅ Combined Anki deck created: {output_path.name}")
        print(f"   Total notes: {n_notes} (Q1: {n_q1}, Q2: {n_q2}, Q3: {n_q3})")
        print(f"   Notes with images: {n_with_images}")
        return True
    except Exception as e:
        print(f"\n❌ Failed to create combined Anki deck: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test 6-arm pipeline with different specialties (one group per arm)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument(
        "--run_tag",
        type=str,
        default=None,
        help="Run tag (default: TEST_6ARM_SPEC_YYYYMMDD_HHMMSS)",
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
        run_tag = f"TEST_6ARM_SPEC_{timestamp}"
    
    print("=" * 70)
    print("6-Arm Pipeline Test (Different Specialties)")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Arms: {', '.join(ARMS)}")
    print(f"Seed: {args.seed}")
    if args.skip_s3_s4:
        print("⚠️  S3/S4 will be skipped")
    print("=" * 70)
    
    # Load groups
    groups_csv_path = base_dir / args.groups_csv
    print(f"\n>>> Loading groups from: {groups_csv_path}")
    groups = load_groups_canonical(groups_csv_path)
    print(f"   Loaded {len(groups)} groups")
    
    # Select groups (one per specialty, one per arm)
    print(f"\n>>> Selecting groups (one per specialty, one per arm)...")
    try:
        arm_to_group = select_groups_by_specialty(groups, ARMS, seed=args.seed)
        print(f"\n✅ Selected {len(arm_to_group)} groups:")
        for arm in ARMS:
            if arm in arm_to_group:
                group = arm_to_group[arm]
                print(f"   Arm {arm} ({ARM_LABELS.get(arm, arm)}): {group['group_id']} - {group['specialty']}")
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    # Process each arm
    print(f"\n>>> Processing {len(ARMS)} arms...")
    print("=" * 70)
    
    all_results = {}
    for arm in ARMS:
        if arm not in arm_to_group:
            continue
        group_key = arm_to_group[arm]["group_key"]
        results = process_arm(
            base_dir=base_dir,
            run_tag=run_tag,
            arm=arm,
            group_key=group_key,
            skip_s3_s4=args.skip_s3_s4,
            image_model=args.image_model,
        )
        all_results[arm] = results
    
    # Check if all S1/S2 succeeded
    all_s1_s2_success = all(r.get("s1_s2", False) for r in all_results.values())
    if not all_s1_s2_success:
        print("\n❌ Some arms failed at S1/S2. Cannot generate combined outputs.")
        sys.exit(1)
    
    # Generate combined PDF
    pdf_success = generate_combined_pdf(
        base_dir=base_dir,
        run_tag=run_tag,
        arms=ARMS,
        arm_to_group=arm_to_group,
    )
    
    # Generate combined Anki deck
    anki_success = generate_combined_anki(
        base_dir=base_dir,
        run_tag=run_tag,
        arms=ARMS,
    )
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Run tag: {run_tag}")
    print()
    print("Results by arm:")
    print()
    
    for arm in ARMS:
        if arm not in all_results:
            continue
        r = all_results[arm]
        group = arm_to_group[arm]
        status = "✅" if r.get("s1_s2", False) else "❌"
        print(f"  [{arm}] {ARM_LABELS.get(arm, arm)} ({group['specialty']}): {status}")
        print(f"    S1/S2: {'✅' if r.get('s1_s2') else '❌'}")
        print(f"    S3:    {'✅' if r.get('s3') else '❌'}")
        print(f"    S4:    {'✅' if r.get('s4') else '❌'}")
        print()
    
    print("Combined outputs:")
    print(f"  PDF:  {'✅' if pdf_success else '❌'}")
    print(f"  Anki: {'✅' if anki_success else '❌'}")
    print()
    
    # Overall status
    all_success = (
        all_s1_s2_success and
        pdf_success and
        anki_success
    )
    
    if all_success:
        print("✅ ALL STEPS COMPLETED SUCCESSFULLY")
    else:
        print("⚠️  SOME STEPS HAD ERRORS (see details above)")
    
    print("=" * 70)
    print(f"\nOutput files:")
    print(f"  Generated data: {base_dir / '2_Data' / 'metadata' / 'generated' / run_tag}")
    print(f"  PDF: {base_dir / '6_Distributions' / 'QA_Packets' / f'TEST_6ARM_ALL_{run_tag}.pdf'}")
    print(f"  Anki: {base_dir / '6_Distributions' / 'anki' / f'MeducAI_{run_tag}_ALL_ARMS.apkg'}")
    print("=" * 70)


if __name__ == "__main__":
    main()


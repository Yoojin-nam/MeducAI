#!/usr/bin/env python3
"""
Generate PDF from existing run_tag data

This script:
1. Reads S1 results from a specified run_tag
2. Extracts all groups from S1 results
3. Generates a combined PDF for all groups

Usage:
    python 3_Code/Scripts/generate_pdf_from_run_tag.py --run_tag SAMPLE_ALL_20251220_180008 --arm A
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


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


def load_all_groups_from_s1(s1_path: Path) -> List[Dict[str, str]]:
    """Load all groups from S1 results with their metadata."""
    groups = []
    if not s1_path.exists():
        return groups
    
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                group_id = record.get("group_id", "").strip()
                group_key = record.get("group_key", "").strip()
                specialty = record.get("specialty", "").strip()
                
                if group_id and group_key:
                    groups.append({
                        "group_id": group_id,
                        "group_key": group_key,
                        "specialty": specialty,
                    })
            except json.JSONDecodeError:
                continue
    
    return groups


def generate_combined_pdf(
    base_dir: Path,
    run_tag: str,
    arm: str,
    selected_groups: List[Dict[str, str]],
) -> bool:
    """Generate one combined PDF for all selected groups."""
    print("\n" + "="*60)
    print("Generating Combined PDF (all groups)")
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
            print(f"   ⚠️  Skipping {group['group_id']} ({group.get('specialty', 'unknown')}): group_key '{group_key}' not found in S1 results")
    
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
        specialty = group_info.get("specialty", "unknown")
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
        
        # Master Table
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
        
        # Note: build_cards_section already adds PageBreak() after the last card,
        # so we don't need to add any separator between groups
    
    # Build PDF
    try:
        doc.build(story)
        print(f"\n✅ Combined PDF created: {pdf_path.name}")
        print(f"   Location: {pdf_path}")
        return True
    except Exception as e:
        print(f"\n❌ Failed to create combined PDF: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate PDF from existing run_tag data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument("--run_tag", type=str, required=True, help="Run tag (e.g., SAMPLE_ALL_20251220_180008)")
    parser.add_argument("--arm", type=str, default="A", help="Arm identifier (default: A)")
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        print(f"❌ Base directory does not exist: {base_dir}")
        sys.exit(1)
    
    run_tag = args.run_tag.strip()
    arm = args.arm.upper()
    
    print("="*70)
    print("PDF Generator from Run Tag")
    print("="*70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Arm: {arm}")
    print("="*70)
    
    # Load S1 results to get all groups
    s1_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"stage1_struct__arm{arm}.jsonl"
    if not s1_path.exists():
        print(f"❌ S1 results not found: {s1_path}")
        sys.exit(1)
    
    print(f"\n>>> Loading groups from S1 results...")
    selected_groups = load_all_groups_from_s1(s1_path)
    print(f"   Found {len(selected_groups)} groups")
    
    if not selected_groups:
        print("❌ No groups found in S1 results")
        sys.exit(1)
    
    # Generate PDF
    success = generate_combined_pdf(
        base_dir=base_dir,
        run_tag=run_tag,
        arm=arm,
        selected_groups=selected_groups,
    )
    
    if success:
        print("\n✅ PDF generation completed successfully")
    else:
        print("\n❌ PDF generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Generate combined PDF for all groups in a run_tag with S5 validation included.

Usage:
    python3 3_Code/scripts/generate_combined_pdf_with_s5.py \
        --base_dir /path/to/workspace/workspace/MeducAI \
        --run_tag DEV_armG_s5loop_diverse_20251229_065718 \
        --arm G \
        --out_dir 6_Distributions/QA_Packets
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add src directory to path for imports
_THIS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_THIS_DIR / "src"))

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, SimpleDocTemplate

# Import PDF builder module
try:
    import sys
    sys.path.insert(0, str(_THIS_DIR / "src"))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pdf_module",
        _THIS_DIR / "src" / "07_build_set_pdf.py",
    )
    if spec is None or spec.loader is None:
        raise ImportError("Failed to load spec for 07_build_set_pdf.py")
    pdf_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pdf_module)
except Exception as e:
    print(f"Error importing PDF module: {e}", file=sys.stderr)
    sys.exit(1)


def get_generated_dir(base_dir: Path, run_tag: str) -> Path:
    """Get the generated metadata directory."""
    return base_dir / "2_Data" / "metadata" / "generated" / run_tag


def load_all_group_ids(base_dir: Path, run_tag: str, arm: str) -> List[str]:
    """Load all group IDs from S1 output."""
    gen_dir = get_generated_dir(base_dir, run_tag)
    s1_arm = arm  # For now, assume S1 and S2 use same arm
    s1_path = gen_dir / f"stage1_struct__arm{s1_arm}.jsonl"
    
    if not s1_path.exists():
        print(f"Error: S1 file not found: {s1_path}", file=sys.stderr)
        return []
    
    group_ids = []
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                gid = record.get("group_id", "")
                if gid:
                    group_ids.append(gid)
            except json.JSONDecodeError:
                continue
    
    return sorted(group_ids)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate combined PDF for all groups with S5 validation included"
    )
    parser.add_argument("--base_dir", type=str, required=True, help="Project base directory")
    parser.add_argument("--run_tag", type=str, required=True, help="Run tag")
    parser.add_argument("--arm", type=str, required=True, help="Arm identifier (A-F)")
    parser.add_argument(
        "--out_dir",
        type=str,
        default="6_Distributions/QA_Packets",
        help="Output directory for PDF (default: 6_Distributions/QA_Packets)",
    )
    parser.add_argument(
        "--s1_arm",
        type=str,
        default=None,
        help="S1 arm to use (defaults to --arm if not specified)",
    )
    parser.add_argument(
        "--allow_missing_images",
        action="store_true",
        help="Allow missing images (insert placeholder instead of failing)",
    )
    parser.add_argument(
        "--optimize_images",
        action="store_true",
        default=True,
        help="Optimize images for PDF (default: True)",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    arm = args.arm.upper().strip()
    s1_arm_actual = (args.s1_arm or arm).strip().upper() if args.s1_arm else arm
    
    # Load all group IDs
    print(f"Loading group IDs from run_tag: {args.run_tag}")
    group_ids = load_all_group_ids(base_dir, args.run_tag, arm)
    
    if not group_ids:
        print("Error: No groups found in S1 output", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found {len(group_ids)} groups")
    
    # Generate combined PDF filename
    pdf_filename = f"COMBINED_{args.run_tag}_arm{arm}.pdf"
    pdf_path = out_dir / pdf_filename
    
    print(f"\nGenerating combined PDF: {pdf_path.name}")
    print(f"Groups to include: {len(group_ids)}")
    
    # Page setup
    page_width, page_height = landscape(A4)
    
    # Create PDF document
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=landscape(A4),
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    
    # Load fonts + styles (Korean support)
    # `07_build_set_pdf.py` provides a stable helper that registers fonts and returns styles.
    _styles, custom_styles, korean_font, korean_font_bold = pdf_module.create_pdf_styles()
    
    # Build story (list of elements to add to PDF)
    story = []
    
    # Process each group
    for idx, group_id in enumerate(group_ids, 1):
        print(f"\n[{idx}/{len(group_ids)}] Processing group: {group_id}")
        
        try:
            # Build sections for this group using the existing function
            pdf_module.build_single_group_sections(
                story=story,
                base_dir=base_dir,
                run_tag=args.run_tag,
                arm=arm,
                s1_arm=s1_arm_actual,
                group_id=group_id,
                blinded=False,
                surrogate_map=None,
                allow_missing_images=args.allow_missing_images,
                optimize_images=args.optimize_images,
                image_max_dpi=200.0,
                image_jpeg_quality=90,
                infographic_max_dpi=150.0,
                content_score_weight_col0=0.7,
                content_score_weight_col1=0.5,
                s1_only=False,
                include_s5=True,  # Include S5 validation
                page_width=page_width,
                page_height=page_height,
                custom_styles=custom_styles,
                korean_font=korean_font,
                korean_font_bold=korean_font_bold,
            )
            
            # Add page break between groups (except after last group)
            if idx < len(group_ids):
                story.append(PageBreak())
            
            print(f"  ✓ Completed: {group_id}")
            
        except Exception as e:
            print(f"  ✗ Error processing {group_id}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            # Continue with next group
            continue
    
    # Build PDF
    try:
        print(f"\nBuilding PDF: {pdf_path.name}")
        doc.build(story)
        print(f"✅ Combined PDF created: {pdf_path}")
        print(f"   Total groups: {len(group_ids)}")
    except Exception as e:
        print(f"❌ Failed to create PDF: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


"""
MeducAI Step06 (Specialty PDF Builder) — Build deployment PDFs per specialty

P0 Requirements:
- Read specialty order file (from 06_generate_order_file.py)
- For each specialty, build ONE PDF containing all groups in order
- PDF sections per group: Learning Objectives + Master Table + Infographic (S1-only mode)
- No cards/questions (deployment-only, DIAGRAM images)
- Output: 6_Distributions/Specialty_PDFs/{specialty}.pdf

Design Principles:
- Reuse existing PDF builder functions (07_build_set_pdf.py)
- S1-only mode: skip S2-dependent sections (Cards)
- Order file determines sequence (educational order from xlsx)
- DIAGRAM-only: uses DIAGRAM images (not REALISTIC)
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# Import PDF builder functions from 07_build_set_pdf
import sys
_THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_THIS_DIR))

try:
    from tools.path_resolver import resolve_s2_results_path
    from tools.s6_export_manifest import load_export_manifest, should_use_repaired
except ImportError:
    # Fallback resolvers (same as in 07_build_set_pdf.py)
    def resolve_s2_results_path(out_dir: Path, arm: str, s1_arm=None) -> Path:
        if s1_arm:
            new_path = out_dir / f"s2_results__s1arm{s1_arm}__s2arm{arm}.jsonl"
            if new_path.exists():
                return new_path
        return out_dir / f"s2_results__arm{arm}.jsonl"

    def load_export_manifest(manifest_path: Optional[Path]) -> Dict[str, bool]:
        return {}

    def should_use_repaired(
        manifest: Dict[str, bool], *, group_id: str, default: bool = False
    ) -> bool:
        return default

# Import core PDF building functions
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, SimpleDocTemplate, Spacer
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# Import from 07_build_set_pdf using importlib
import importlib.util
_build_pdf_path = _THIS_DIR / "07_build_set_pdf.py"
spec = importlib.util.spec_from_file_location("07_build_set_pdf", _build_pdf_path)
if spec is None or spec.loader is None:
    raise ImportError(f"Failed to load 07_build_set_pdf from {_build_pdf_path}")
_build_pdf_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_build_pdf_module)

# Reuse functions from 07_build_set_pdf
get_generated_dir = _build_pdf_module.get_generated_dir
get_images_dir = _build_pdf_module.get_images_dir
load_s1_struct = _build_pdf_module.load_s1_struct
list_all_group_ids = _build_pdf_module.list_all_group_ids
resolve_group_variant_paths = _build_pdf_module.resolve_group_variant_paths
load_s4_image_manifest = _build_pdf_module.load_s4_image_manifest
build_objectives_section = _build_pdf_module.build_objectives_section
build_master_table_section = _build_pdf_module.build_master_table_section
build_infographic_section = _build_pdf_module.build_infographic_section
create_pdf_styles = _build_pdf_module.create_pdf_styles


def load_order_file(order_path: Path) -> Dict[str, List[Dict[str, str]]]:
    """
    Load specialty order file and return: specialty -> [ordered groups]
    
    Returns dict mapping specialty to list of groups (each with order, group_key, group_id)
    """
    if not order_path.exists():
        raise FileNotFoundError(f"Order file not found: {order_path}")
    
    specialty_groups = {}
    with open(order_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            specialty = row.get("specialty", "").strip()
            order = int(row.get("order", 0))
            group_key = row.get("group_key", "").strip()
            group_id = row.get("group_id", "").strip()
            
            if not specialty or not group_id:
                continue
            
            if specialty not in specialty_groups:
                specialty_groups[specialty] = []
            
            specialty_groups[specialty].append({
                "order": order,
                "group_key": group_key,
                "group_id": group_id,
            })
    
    # Sort by order within each specialty
    for spec in specialty_groups:
        specialty_groups[spec].sort(key=lambda x: x["order"])
    
    return specialty_groups


def build_specialty_pdf(
    *,
    base_dir: Path,
    run_tag: str,
    arm: str,
    s1_arm: Optional[str],
    specialty: str,
    group_ids: List[str],
    out_dir: Path,
    allow_missing_images: bool = True,
    optimize_images: bool = True,
    infographic_max_dpi: float = 150.0,
    image_jpeg_quality: int = 90,
    content_score_weight_col0: float = 0.7,
    content_score_weight_col1: float = 0.5,
    export_manifest: Optional[Dict[str, bool]] = None,
) -> Path:
    """
    Build ONE PDF for a specialty containing all groups in order.
    
    Uses S1-only mode: Learning Objectives + Master Table + Infographic only.
    """
    gen_dir = get_generated_dir(base_dir, run_tag)
    images_dir = get_images_dir(base_dir, run_tag)
    
    # Create PDF in landscape mode
    page_size = landscape(A4)
    page_width = page_size[0]
    page_height = page_size[1]
    
    # Output filename: sanitize specialty name
    specialty_safe = specialty.replace(" ", "_").replace("/", "_").lower()
    pdf_filename = f"{specialty_safe}.pdf"
    pdf_path = out_dir / pdf_filename
    
    out_dir.mkdir(parents=True, exist_ok=True)
    
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=page_size,
        rightMargin=0.75 * cm,
        leftMargin=0.75 * cm,
        topMargin=0.75 * cm,
        bottomMargin=0.75 * cm,
    )
    
    story = []
    styles, custom_styles, korean_font, korean_font_bold = create_pdf_styles()
    
    s1_arm_actual = (s1_arm or arm).strip().upper() if s1_arm else arm
    
    # Process each group in order
    success_count = 0
    error_count = 0
    
    print(f"[Specialty PDF] Building PDF for specialty: {specialty}")
    print(f"[Specialty PDF] Processing {len(group_ids)} groups in order...")
    
    for idx, group_id in enumerate(group_ids):
        try:
            print(f"[Specialty PDF] Processing group {idx + 1}/{len(group_ids)}: {group_id}")
            
            # Resolve paths
            paths = resolve_group_variant_paths(
                gen_dir=gen_dir,
                arm=arm,
                s1_arm_actual=s1_arm_actual,
                group_id=group_id,
                export_manifest=export_manifest,
            )
            s1_path = paths["s1_path"]
            s4_manifest_path = paths["s4_manifest_path"]
            
            # Load S1 record
            s1_record = load_s1_struct(s1_path, group_id)
            if not s1_record:
                print(f"[Specialty PDF] WARNING: S1 record not found for group_id={group_id}, skipping")
                error_count += 1
                continue
            
            # Load image mapping (for infographic)
            image_mapping = load_s4_image_manifest(s4_manifest_path, group_id, base_dir, run_tag)
            
            # Section 0: Learning Objectives
            objective_bullets = s1_record.get("objective_bullets", [])
            if objective_bullets:
                build_objectives_section(
                    story,
                    objective_bullets,
                    custom_styles,
                    page_width,
                    page_height,
                    korean_font,
                    korean_font_bold,
                    s1_record=s1_record,
                    base_dir=base_dir,
                )
                story.append(PageBreak())
            
            # Section 1: Master Table
            master_table_md = s1_record.get("master_table_markdown_kr", "")
            if master_table_md:
                build_master_table_section(
                    story,
                    master_table_md,
                    custom_styles,
                    page_width,
                    page_height,
                    korean_font,
                    korean_font_bold,
                    s1_record=s1_record,
                    specialty=specialty,
                    content_score_weight_col0=content_score_weight_col0,
                    content_score_weight_col1=content_score_weight_col1,
                )
                story.append(PageBreak())
            
            # Section 2: Infographic(s)
            infographic_path = image_mapping.get(("S1_TABLE_VISUAL", None, None))
            if infographic_path:
                # Single infographic
                build_infographic_section(
                    story,
                    infographic_path,
                    custom_styles,
                    allow_missing_images,
                    page_width,
                    page_height,
                    optimize_images,
                    infographic_max_dpi,
                    image_jpeg_quality,
                    s1_record=s1_record,
                    korean_font_bold=korean_font_bold,
                )
                story.append(PageBreak())
            else:
                # Multiple clustered infographics
                cluster_infographics = []
                for key, path in image_mapping.items():
                    spec_kind, cluster_id, _ = key
                    if spec_kind == "S1_TABLE_VISUAL" and cluster_id:
                        cluster_infographics.append((cluster_id, path))
                
                cluster_infographics.sort(key=lambda x: x[0])
                
                if cluster_infographics:
                    for cluster_id, infographic_path in cluster_infographics:
                        build_infographic_section(
                            story,
                            infographic_path,
                            custom_styles,
                            allow_missing_images,
                            page_width,
                            page_height,
                            optimize_images,
                            infographic_max_dpi,
                            image_jpeg_quality,
                            s1_record=s1_record,
                            korean_font_bold=korean_font_bold,
                        )
                        story.append(PageBreak())
            
            success_count += 1
            
            # Add page break between groups (except after last group)
            if idx < len(group_ids) - 1:
                story.append(PageBreak())
        
        except Exception as e:
            print(f"[Specialty PDF] ✗ ERROR for group_id={group_id}: {e}", file=sys.stderr)
            error_count += 1
            if not allow_missing_images:
                import traceback
                traceback.print_exc()
    
    # Build PDF
    if success_count > 0:
        doc.build(story)
        print(f"[Specialty PDF] ✓ Successfully created PDF: {pdf_path.name}")
        print(f"[Specialty PDF] Summary: {success_count} groups succeeded, {error_count} failed")
    else:
        raise RuntimeError(f"No groups were successfully processed for specialty {specialty}")
    
    if error_count > 0:
        print(f"[Specialty PDF] WARNING: {error_count} groups failed, but PDF was created with successful groups.", file=sys.stderr)
    
    return pdf_path


def main():
    parser = argparse.ArgumentParser(
        description="Build deployment PDFs per specialty (S1-only: Learning Objectives + Master Table + Infographic)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  # Generate order file first:
  python 3_Code/src/06_generate_order_file.py --base_dir .

  # Build all specialty PDFs:
  python 3_Code/src/06_build_specialty_pdf.py \\
    --base_dir . \\
    --run_tag FINAL_DISTRIBUTION_S4TEST_REALISTIC_20260101_000544 \\
    --arm G \\
    --order_file 2_Data/metadata/group_order/specialty_group_order.csv \\
    --out_dir 6_Distributions/Specialty_PDFs \\
    --allow_missing_images

  # Build PDF for specific specialty only:
  python 3_Code/src/06_build_specialty_pdf.py \\
    --base_dir . \\
    --run_tag FINAL_DISTRIBUTION_S4TEST_REALISTIC_20260101_000544 \\
    --arm G \\
    --order_file 2_Data/metadata/group_order/specialty_group_order.csv \\
    --out_dir 6_Distributions/Specialty_PDFs \\
    --specialty musculoskeletal_radiology \\
    --allow_missing_images

Output:
  - 6_Distributions/Specialty_PDFs/{specialty}.pdf (one PDF per specialty)
  - Each PDF contains all groups for that specialty in educational order
  - Sections per group: Learning Objectives + Master Table + Infographic (no cards)
        """,
    )
    
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument("--run_tag", type=str, required=True, help="Run tag (e.g., FINAL_DISTRIBUTION_S4TEST_REALISTIC_20260101_000544)")
    parser.add_argument("--arm", type=str, required=True, help="Arm identifier (A-F, G, etc.)")
    parser.add_argument("--s1_arm", type=str, default=None, help="S1 arm to use (defaults to --arm if not specified)")
    parser.add_argument(
        "--order_file",
        type=str,
        default="2_Data/metadata/group_order/specialty_group_order.csv",
        help="Path to specialty order file (from 06_generate_order_file.py)",
    )
    parser.add_argument(
        "--out_dir",
        type=str,
        default="6_Distributions/Specialty_PDFs",
        help="Output directory for specialty PDFs",
    )
    parser.add_argument(
        "--specialty",
        type=str,
        default=None,
        help="Build PDF for specific specialty only (if not specified, builds all specialties)",
    )
    parser.add_argument(
        "--allow_missing_images",
        action="store_true",
        default=True,
        help="Allow missing images (insert placeholder instead of failing, default: True)",
    )
    parser.add_argument(
        "--optimize_images",
        action="store_true",
        default=True,
        help="Optimize images for PDF (default: True)",
    )
    parser.add_argument(
        "--infographic_max_dpi",
        type=float,
        default=150.0,
        help="Maximum DPI for infographic images (default: 150.0)",
    )
    parser.add_argument(
        "--image_jpeg_quality",
        type=int,
        default=90,
        help="JPEG quality 1-100 (default: 90)",
    )
    parser.add_argument(
        "--content_score_weight_col0",
        type=float,
        default=0.7,
        help="Content score weight multiplier for Entity Name column (default: 0.7)",
    )
    parser.add_argument(
        "--content_score_weight_col1",
        type=float,
        default=0.5,
        help="Content score weight multiplier for columns 2-6 (default: 0.5)",
    )
    parser.add_argument(
        "--export_manifest_path",
        type=str,
        default=None,
        help="Optional S6 export manifest JSON (for repaired variant selection)",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    order_path = base_dir / args.order_file if not Path(args.order_file).is_absolute() else Path(args.order_file)
    out_dir = base_dir / args.out_dir if not Path(args.out_dir).is_absolute() else Path(args.out_dir)
    export_manifest = None
    
    if args.export_manifest_path:
        manifest_path_obj = Path(args.export_manifest_path)
        export_manifest_path = (
            manifest_path_obj.resolve()
            if manifest_path_obj.is_absolute()
            else (base_dir / manifest_path_obj).resolve()
        )
        export_manifest = load_export_manifest(export_manifest_path)
        print(f"[Specialty PDF] Loaded export manifest: {export_manifest_path} ({len(export_manifest)} group entries)")
    
    # Load order file
    print(f"[Specialty PDF] Loading order file: {order_path}")
    specialty_groups = load_order_file(order_path)
    print(f"[Specialty PDF] Loaded {len(specialty_groups)} specialties from order file")
    
    # Filter to specific specialty if requested
    if args.specialty:
        if args.specialty not in specialty_groups:
            print(f"[Specialty PDF] ERROR: Specialty '{args.specialty}' not found in order file", file=sys.stderr)
            print(f"[Specialty PDF] Available specialties: {', '.join(sorted(specialty_groups.keys()))}", file=sys.stderr)
            sys.exit(1)
        specialty_groups = {args.specialty: specialty_groups[args.specialty]}
    
    # Build PDF for each specialty
    success_count = 0
    error_count = 0
    
    for specialty, groups in sorted(specialty_groups.items()):
        try:
            group_ids = [g["group_id"] for g in groups]
            print(f"\n[Specialty PDF] Building PDF for specialty: {specialty} ({len(group_ids)} groups)")
            
            pdf_path = build_specialty_pdf(
                base_dir=base_dir,
                run_tag=args.run_tag,
                arm=args.arm.upper(),
                s1_arm=args.s1_arm.upper() if args.s1_arm else None,
                specialty=specialty,
                group_ids=group_ids,
                out_dir=out_dir,
                allow_missing_images=args.allow_missing_images,
                optimize_images=args.optimize_images,
                infographic_max_dpi=args.infographic_max_dpi,
                image_jpeg_quality=args.image_jpeg_quality,
                content_score_weight_col0=args.content_score_weight_col0,
                content_score_weight_col1=args.content_score_weight_col1,
                export_manifest=export_manifest,
            )
            
            print(f"[Specialty PDF] ✓ Created: {pdf_path}")
            success_count += 1
        
        except Exception as e:
            print(f"[Specialty PDF] ✗ ERROR for specialty {specialty}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            error_count += 1
    
    print(f"\n[Specialty PDF] Summary: {success_count} specialties succeeded, {error_count} failed")
    print(f"[Specialty PDF] Output directory: {out_dir}")
    
    if error_count > 0:
        print(f"[Specialty PDF] WARNING: {error_count} specialties failed", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
MeducAI Distribution PDF Builder

Generates distribution-ready PDF packages with three modes:
1. full: Complete integrated PDF (all groups: 학습목표 + 테이블 + 인포그래픽)
2. tables_only: Tables-only PDF for quick reference
3. by_specialty: Per-specialty PDFs (11 separate files)

Usage:
  # Full PDF with all content
  python3 3_Code/src/tools/build_distribution_pdf.py \
    --mode full \
    --run_tag FINAL_DISTRIBUTION \
    --arm G \
    --out_dir 6_Distributions/MeducAI_Final_Share/PDF

  # Tables only PDF
  python3 3_Code/src/tools/build_distribution_pdf.py \
    --mode tables_only \
    --run_tag FINAL_DISTRIBUTION \
    --arm G \
    --out_dir 6_Distributions/MeducAI_Final_Share/PDF

  # By specialty (generates 11 separate PDFs in Specialty/ subfolder)
  python3 3_Code/src/tools/build_distribution_pdf.py \
    --mode by_specialty \
    --run_tag FINAL_DISTRIBUTION \
    --arm G \
    --out_dir 6_Distributions/MeducAI_Final_Share/PDF

  # All modes at once
  python3 3_Code/src/tools/build_distribution_pdf.py \
    --mode all \
    --run_tag FINAL_DISTRIBUTION \
    --arm G \
    --out_dir 6_Distributions/MeducAI_Final_Share/PDF
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import csv
import re
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image as RLImage,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageTemplate,
    Frame,
    BaseDocTemplate,
    Flowable,
    KeepTogether,
)
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO

# =========================
# Constants
# =========================

# Specialty name mapping (Korean names for PDF titles)
SPECIALTY_NAMES = {
    "abdominal_radiology": "복부영상의학",
    "breast_rad": "유방영상의학",
    "cardiovascular_rad": "심혈관영상의학",
    "gu_radiology": "비뇨생식영상의학",
    "interventional_radiology": "인터벤션영상의학",
    "musculoskeletal_radiology": "근골격영상의학",
    "neuro_hn_imaging": "신경/두경부영상의학",
    "nuclear_med": "핵의학",
    "pediatric_radiology": "소아영상의학",
    "physics_qc_informatics": "물리/QC/정보학",
    "thoracic_radiology": "흉부영상의학",
}

# Specialty name mapping (English names for cover page)
SPECIALTY_NAMES_EN = {
    "abdominal_radiology": "Abdominal Radiology",
    "breast_rad": "Breast Radiology",
    "cardiovascular_rad": "Cardiovascular Radiology",
    "gu_radiology": "Genitourinary Radiology",
    "interventional_radiology": "Interventional Radiology",
    "musculoskeletal_radiology": "Musculoskeletal Radiology",
    "neuro_hn_imaging": "Neuro & Head-Neck Imaging",
    "nuclear_med": "Nuclear Medicine",
    "pediatric_radiology": "Pediatric Radiology",
    "physics_qc_informatics": "Physics / QC / Informatics",
    "thoracic_radiology": "Thoracic Radiology",
}

# Design Color Palette
COLOR_DEEP_NAVY = colors.HexColor("#1B3A5F")      # Primary: Header background (left), accents
COLOR_OCEAN_BLUE = colors.HexColor("#4A90D9")     # Secondary: Header background (right), footer text
COLOR_SOFT_GRAY = colors.HexColor("#F5F7FA")      # Light BG: Table header background
COLOR_PALE_GRAY = colors.HexColor("#E2E8F0")      # Border: Dividers, borders
COLOR_CHARCOAL = colors.HexColor("#2D3748")       # Text Dark: Body text
COLOR_WHITE = colors.HexColor("#FFFFFF")           # Text Light: Header text

# Header/Footer dimensions
HEADER_HEIGHT = 1.2 * cm
FOOTER_HEIGHT = 0.8 * cm

# Content margins (tuned for denser layout)
# These margins control how close the main content (tables/objectives/images) sits to page edges
# and to the header/footer boxes.
CONTENT_MARGIN_X = 0.4 * cm
CONTENT_MARGIN_Y_EXTRA = 0.2 * cm

# =========================
# Custom DocTemplate with Header Tracking
# =========================

class HeaderTrackingDocTemplate(BaseDocTemplate):
    """
    Custom DocTemplate that tracks header information via afterFlowable callback.
    
    This solves the timing issue where SimpleDocTemplate callbacks don't have access
    to the latest header info. The afterFlowable method is called immediately after
    each flowable is drawn, allowing perfect synchronization with page content.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize with empty header info."""
        self.current_header_info = {
            'group_path': '',
            'section_type': '',
            'bookmark': '',
            'hide_header': False,
            'hide_footer': False,
        }
        BaseDocTemplate.__init__(self, *args, **kwargs)
    
    def afterFlowable(self, flowable):
        """
        Called immediately after each flowable is drawn.
        
        This is the perfect hook to update header information, as it runs:
        1. After the flowable is placed on the page
        2. Before the page is finalized
        3. In the same rendering context as the page header callback
        """
        if isinstance(flowable, HeaderInfoFlowable):
            self.current_header_info = {
                'group_path': flowable.group_path,
                'section_type': flowable.section_type,
                'bookmark': flowable.bookmark,
                'hide_header': bool(getattr(flowable, "hide_header", False)),
                'hide_footer': bool(getattr(flowable, "hide_footer", False)),
            }


# =========================
# Path Utilities
# =========================

def get_generated_dir(base_dir: Path, run_tag: str) -> Path:
    """Get the generated metadata directory."""
    return base_dir / "2_Data" / "metadata" / "generated" / run_tag


def get_images_dir(base_dir: Path, run_tag: str) -> Path:
    """Get the images directory."""
    return base_dir / "2_Data" / "metadata" / "generated" / run_tag / "images"


def resolve_s2_results_path(out_dir: Path, arm: str, s1_arm: Optional[str] = None) -> Path:
    """Resolve S2 results path with fallback."""
    arm_u = arm.strip().upper()
    if s1_arm:
        s1_arm_u = s1_arm.strip().upper()
        new_path = out_dir / f"s2_results__s1arm{s1_arm_u}__s2arm{arm_u}.jsonl"
        if new_path.exists():
            return new_path
    return out_dir / f"s2_results__arm{arm_u}.jsonl"


def resolve_s1_struct_path(gen_dir: Path, s1_arm_actual: str) -> Path:
    """
    Prefer REGEN S1 struct if present, otherwise fall back to baseline.

    This matters because REGEN may update master_table_markdown_kr (master table content)
    and we want PDFs to reflect the regenerated master tables when available.
    """
    s1_arm_u = str(s1_arm_actual or "").strip().upper()
    s1_path_regen = gen_dir / f"stage1_struct__arm{s1_arm_u}__regen.jsonl"
    s1_path_baseline = gen_dir / f"stage1_struct__arm{s1_arm_u}.jsonl"
    return s1_path_regen if s1_path_regen.exists() else s1_path_baseline


# =========================
# Data Loading
# =========================

def load_all_s1_records(s1_path: Path) -> List[Dict[str, Any]]:
    """Load all S1 structure records."""
    records = []
    if not s1_path.exists():
        return records
    
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                records.append(record)
            except json.JSONDecodeError:
                continue
    return records


def resolve_image_path_with_regen_priority(
    base_filename: str,
    images_dir: Path,
    images_regen_dir: Path,
) -> Optional[Path]:
    """
    Resolve image path with REGEN priority: check images_regen/ first, then fallback to images/.
    
    Args:
        base_filename: Base filename (e.g., "IMG__RUN__grp_xxx__TABLE__cluster_1.jpg")
        images_dir: Path to images/ directory
        images_regen_dir: Path to images_regen/ directory
    
    Returns:
        Path to the image file (REGEN version if exists, otherwise regular version), or None if neither exists
    """
    # Check for REGEN version first (with _regen suffix before .jpg)
    if base_filename.endswith(".jpg"):
        base_name = base_filename[:-4]  # Remove .jpg
        regen_filename = f"{base_name}_regen.jpg"
        regen_path = images_regen_dir / regen_filename
        if regen_path.exists():
            return regen_path
    
    # Fallback to regular images/ directory
    regular_path = images_dir / base_filename
    if regular_path.exists():
        return regular_path
    
    return None


def load_s4_image_manifest_all(manifest_path: Path, gen_dir: Path) -> Dict[str, Dict[Tuple, str]]:
    """
    Load S4 image manifest for all groups.
    Also scans images directory for TABLE (infographic) images by filename pattern.
    
    REGEN image priority: checks images_regen/ first, then falls back to images/.
    
    Returns:
        Dict mapping group_id -> {(spec_kind, cluster_id, None) -> image_path}
    """
    mapping = defaultdict(dict)
    images_dir = gen_dir / "images"
    images_regen_dir = gen_dir / "images_regen"
    
    # First, try to load from manifest
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    group_id = entry.get("group_id")
                    spec_kind = entry.get("spec_kind", "")
                    cluster_id = entry.get("cluster_id")
                    media_filename = entry.get("media_filename", "")
                    
                    if group_id and media_filename:
                        # Resolve image path with REGEN priority
                        image_path = resolve_image_path_with_regen_priority(
                            media_filename, images_dir, images_regen_dir
                        )
                        if image_path:
                            if spec_kind == "S1_TABLE_VISUAL" and cluster_id:
                                key = (spec_kind, cluster_id, None)
                            else:
                                entity_id = entry.get("entity_id")
                                card_role = entry.get("card_role")
                                if entity_id:
                                    entity_id = str(entity_id).replace(":", "_")
                                key = (spec_kind, entity_id, card_role)
                            mapping[group_id][key] = str(image_path.resolve())
                except json.JSONDecodeError:
                    continue
    
    # Also scan images directories for TABLE (infographic) images by filename pattern
    # Pattern 1: IMG__<run_tag>__<group_id>__TABLE__<cluster_id>.jpg (with cluster)
    # Pattern 2: IMG__<run_tag>__<group_id>__TABLE.jpg (without cluster)
    # Check REGEN directory first, then regular images directory
    import re
    # Pattern for cluster images: IMG__<anything>__grp_<hex>__TABLE__cluster_<N>.jpg
    table_pattern_cluster = re.compile(r"IMG__[A-Za-z0-9_]+__(grp_[a-f0-9]+)__TABLE__cluster_(\d+)(?:_regen)?\.jpg")
    # Pattern for non-cluster images: IMG__<anything>__grp_<hex>__TABLE.jpg
    table_pattern_no_cluster = re.compile(r"IMG__[A-Za-z0-9_]+__(grp_[a-f0-9]+)__TABLE(?:_regen)?\.jpg")
    
    # First, scan images_regen/ directory for REGEN versions
    if images_regen_dir.exists():
        # Check cluster pattern with _regen
        for img_file in images_regen_dir.glob("*__TABLE__*_regen.jpg"):
            match = table_pattern_cluster.match(img_file.name)
            if match:
                group_id = match.group(1)
                cluster_id = f"cluster_{match.group(2)}"
                key = ("S1_TABLE_VISUAL", cluster_id, None)
                # REGEN versions take priority, so always set if found
                mapping[group_id][key] = str(img_file.resolve())
        
        # Check non-cluster pattern with _regen
        for img_file in images_regen_dir.glob("*__TABLE_regen.jpg"):
            match = table_pattern_no_cluster.match(img_file.name)
            if match:
                group_id = match.group(1)
                # For non-cluster, use None as cluster_id (or empty string)
                key = ("S1_TABLE_VISUAL", None, None)
                mapping[group_id][key] = str(img_file.resolve())
    
    # Then, scan regular images/ directory (only if REGEN version not found)
    if images_dir.exists():
        # Check cluster pattern (regular, no _regen)
        for img_file in images_dir.glob("*__TABLE__cluster_*.jpg"):
            # Skip if this is a _regen file (shouldn't be in images/, but just in case)
            if "_regen" in img_file.name:
                continue
            match = table_pattern_cluster.match(img_file.name)
            if match:
                group_id = match.group(1)
                cluster_id = f"cluster_{match.group(2)}"
                key = ("S1_TABLE_VISUAL", cluster_id, None)
                # Only add if REGEN version wasn't already found
                if group_id not in mapping or key not in mapping[group_id]:
                    mapping[group_id][key] = str(img_file.resolve())
        
        # Check non-cluster pattern (regular, no _regen)
        for img_file in images_dir.glob("*__TABLE.jpg"):
            if "_regen" in img_file.name or "__TABLE__" in img_file.name:
                # Skip cluster images or regen images
                continue
            match = table_pattern_no_cluster.match(img_file.name)
            if match:
                group_id = match.group(1)
                key = ("S1_TABLE_VISUAL", None, None)
                # Only add if REGEN version wasn't already found
                if group_id not in mapping or key not in mapping[group_id]:
                    mapping[group_id][key] = str(img_file.resolve())
    
    return mapping


def group_records_by_specialty(s1_records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group S1 records by specialty (first part of group_path)."""
    grouped = defaultdict(list)
    for record in s1_records:
        group_path = record.get("group_path", "")
        if group_path:
            specialty = group_path.split(" > ")[0].strip()
            if specialty:
                grouped[specialty].append(record)
    return grouped


def _load_curriculum_group_order(
    base_dir: Path,
) -> Tuple[List[str], Dict[str, Dict[str, int]]]:
    """
    Load curriculum-derived order from:
      `2_Data/metadata/group_order/specialty_group_order.csv`

    This CSV is generated from `2_Data/processed/Radiology_Curriculum_Weight_Factor.xlsx`
    (SSOT for ordering), but avoids adding XLSX parsing dependencies here.

    Returns:
      - specialty_order: list of specialties in the desired order
      - order_by_specialty: specialty -> {group_id -> order_int}
    """
    order_csv = base_dir / "2_Data" / "metadata" / "group_order" / "specialty_group_order.csv"
    if not order_csv.exists():
        return [], {}

    specialty_order: List[str] = []
    seen_specs: set[str] = set()
    order_by_specialty: Dict[str, Dict[str, int]] = defaultdict(dict)

    with order_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            spec = (row.get("specialty") or "").strip()
            gid = (row.get("group_id") or "").strip()
            order_raw = (row.get("order") or "").strip()
            if not (spec and gid and order_raw):
                continue
            try:
                order_i = int(float(order_raw))
            except Exception:
                continue
            if spec not in seen_specs:
                specialty_order.append(spec)
                seen_specs.add(spec)
            # If duplicates exist, keep the earliest order
            if gid not in order_by_specialty[spec]:
                order_by_specialty[spec][gid] = order_i
            else:
                order_by_specialty[spec][gid] = min(order_by_specialty[spec][gid], order_i)

    return specialty_order, dict(order_by_specialty)


def apply_curriculum_order(
    *,
    base_dir: Path,
    grouped_records: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Reorder grouped_records to match curriculum order (specialty + group within specialty).

    - Specialty order: from specialty_group_order.csv
    - Group order: by group_id order within each specialty (fallback: group_path/group_id)
    """
    specialty_order, order_by_specialty = _load_curriculum_group_order(base_dir)
    if not specialty_order:
        # Fallback to stable alphabetical ordering
        return {k: grouped_records[k] for k in sorted(grouped_records.keys())}

    ordered: Dict[str, List[Dict[str, Any]]] = {}
    remaining = set(grouped_records.keys())

    def sort_records(spec: str, recs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        order_map = order_by_specialty.get(spec, {})

        def key_fn(r: Dict[str, Any]) -> Tuple[int, str, str]:
            gid = (r.get("group_id") or "").strip()
            return (order_map.get(gid, 10**9), (r.get("group_path") or ""), gid)

        return sorted(recs, key=key_fn)

    # First, specialties in curriculum order
    for spec in specialty_order:
        if spec in grouped_records:
            ordered[spec] = sort_records(spec, grouped_records[spec])
            remaining.discard(spec)

    # Then, any specialties not present in curriculum file (should be rare)
    for spec in sorted(remaining):
        ordered[spec] = sort_records(spec, grouped_records[spec])

    return ordered


# =========================
# PDF Styles
# =========================

def setup_korean_fonts() -> Tuple[str, str]:
    """
    Setup Korean fonts and return (regular_font, bold_font) names.

    Important: We register a font *family* so ReportLab can correctly map <b> tags
    to the bold variant. This matches the robust approach used in `07_build_set_pdf.py`.
    """
    home_dir = os.path.expanduser("~")

    # Prefer explicit Regular/Bold font files where possible.
    korean_font_candidates: List[Tuple[str, str]] = [
        # Nanum Gothic (preferred): regular + ExtraBold/Bold
        (f"{home_dir}/Library/Fonts/NanumGothic.ttf", f"{home_dir}/Library/Fonts/NanumGothicExtraBold.ttf"),
        ("/Library/Fonts/NanumGothic.ttf", "/Library/Fonts/NanumGothicExtraBold.ttf"),
        (f"{home_dir}/Library/Fonts/NanumGothic.ttf", f"{home_dir}/Library/Fonts/NanumGothicBold.ttf"),
        ("/Library/Fonts/NanumGothic.ttf", "/Library/Fonts/NanumGothicBold.ttf"),
        # Noto Sans KR: regular + bold static fonts
        (f"{home_dir}/Library/Fonts/NotoSansKR-Regular.ttf", f"{home_dir}/Library/Fonts/NotoSansKR-Bold.ttf"),
        ("/Library/Fonts/NotoSansKR-Regular.ttf", "/Library/Fonts/NotoSansKR-Bold.ttf"),
        # Apple SD Gothic Neo: explicit OTFs if present
        ("/System/Library/Fonts/Supplemental/AppleSDGothicNeo-Regular.otf", "/System/Library/Fonts/Supplemental/AppleSDGothicNeo-Bold.otf"),
        # Apple SD Gothic Neo TTC (fallback; bold may not visually differ depending on TTC)
        ("/System/Library/Fonts/AppleSDGothicNeo.ttc", "/System/Library/Fonts/AppleSDGothicNeo.ttc"),
        # AppleGothic fallback
        ("/System/Library/Fonts/Supplemental/AppleGothic.ttf", "/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
        ("/Library/Fonts/AppleGothic.ttf", "/Library/Fonts/AppleGothic.ttf"),
        # Linux fallback (if present)
        ("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"),
    ]

    korean_font_name = "KoreanFont"
    korean_font_bold_name = "KoreanFontBold"

    for normal_path, bold_path in korean_font_candidates:
        if os.path.exists(normal_path):
            try:
                pdfmetrics.registerFont(TTFont(korean_font_name, normal_path))

                bold_registered = False
                if os.path.exists(bold_path) and bold_path != normal_path:
                    try:
                        pdfmetrics.registerFont(TTFont(korean_font_bold_name, bold_path))
                        bold_registered = True
                    except Exception:
                        bold_registered = False

                if not bold_registered:
                    # Fallback: register bold name to the normal file (won't be visually bold, but won't crash)
                    try:
                        pdfmetrics.registerFont(TTFont(korean_font_bold_name, normal_path))
                    except Exception:
                        korean_font_bold_name = korean_font_name

                pdfmetrics.registerFontFamily(
                    korean_font_name,
                    normal=korean_font_name,
                    bold=korean_font_bold_name,
                )

                return korean_font_name, korean_font_bold_name
            except Exception:
                continue

    # Last resort: variable font (bold may not visually differ)
    variable_font_paths = [
        f"{home_dir}/Library/Fonts/NotoSansKR-VariableFont_wght.ttf",
        "/Library/Fonts/NotoSansKR-VariableFont_wght.ttf",
    ]
    for font_path in variable_font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(korean_font_name, font_path))
                pdfmetrics.registerFont(TTFont(korean_font_bold_name, font_path))
                pdfmetrics.registerFontFamily(
                    korean_font_name,
                    normal=korean_font_name,
                    bold=korean_font_bold_name,
                )
                return korean_font_name, korean_font_bold_name
            except Exception:
                continue

    return "Helvetica", "Helvetica-Bold"


def create_pdf_styles(korean_font: str, korean_font_bold: str) -> Dict[str, ParagraphStyle]:
    """Create PDF paragraph styles."""
    custom_styles = {
        "Title": ParagraphStyle(
            name="Title",
            fontName=korean_font_bold,
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "SectionHeader": ParagraphStyle(
            name="SectionHeader",
            fontName=korean_font_bold,
            fontSize=14,
            leading=18,
            alignment=TA_LEFT,
            spaceBefore=12,
            spaceAfter=8,
            textColor=colors.HexColor("#1a5276"),
        ),
        "SubHeader": ParagraphStyle(
            name="SubHeader",
            fontName=korean_font_bold,
            fontSize=11,
            leading=14,
            alignment=TA_LEFT,
            spaceBefore=8,
            spaceAfter=4,
            textColor=colors.HexColor("#2e86ab"),
        ),
        "BodyText": ParagraphStyle(
            name="BodyText",
            fontName=korean_font,
            fontSize=9,
            leading=12,
            alignment=TA_LEFT,
        ),
        "SmallText": ParagraphStyle(
            name="SmallText",
            fontName=korean_font,
            fontSize=7,
            leading=9,
            alignment=TA_LEFT,
        ),
        "TableCell": ParagraphStyle(
            name="TableCell",
            fontName=korean_font,
            fontSize=9,
            leading=11,
            alignment=TA_LEFT,
        ),
        "Objective": ParagraphStyle(
            name="Objective",
            fontName=korean_font,
            # Larger objectives for readability (per user request)
            fontSize=11,
            # Slightly reduced leading to avoid pushing content and blank-looking pages
            leading=24,
            alignment=TA_LEFT,
            leftIndent=15,
            bulletIndent=5,
        ),
        "PageNumber": ParagraphStyle(
            name="PageNumber",
            fontName=korean_font,
            fontSize=8,
            alignment=TA_RIGHT,
        ),
        "TOCEntry": ParagraphStyle(
            name="TOCEntry",
            fontName=korean_font,
            fontSize=10,
            leading=14,
            alignment=TA_LEFT,
            leftIndent=20,
        ),
        "TOCSpecialty": ParagraphStyle(
            name="TOCSpecialty",
            fontName=korean_font_bold,
            fontSize=12,
            leading=16,
            alignment=TA_LEFT,
            spaceBefore=8,
            spaceAfter=4,
            textColor=colors.HexColor("#1a5276"),
        ),
    }
    
    return custom_styles


# =========================
# Markdown Table Parsing
# =========================

def parse_markdown_table(md_table: str) -> Tuple[List[str], List[List[str]]]:
    """
    Parse markdown table into headers and rows (stable, separator-safe).
    Ported in spirit from `07_build_set_pdf.py`.
    """
    if not md_table or not isinstance(md_table, str):
        return [], []

    lines = [line.rstrip() for line in md_table.strip().split("\n") if line.strip()]
    if not lines:
        return [], []

    # Find header line (first line containing '|')
    header_idx = None
    header_line = None
    for i, line in enumerate(lines):
        if "|" in line:
            header_idx = i
            header_line = line
            break
    if header_line is None or header_idx is None:
        return [], []

    def _parse_row(line: str) -> List[str]:
        cells = [c.strip() for c in line.split("|")]
        # Remove leading/trailing empty caused by leading/trailing '|'
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]
        return cells

    headers = [cell.strip() for cell in _parse_row(header_line) if cell.strip()]
    if not headers:
        return [], []

    # Skip separator lines like: | --- | :---: | ---: |
    def _is_separator(line: str) -> bool:
        s = line.strip()
        # quick exit: must contain '-' and '|'
        if "-" not in s or "|" not in s:
            return False
        # Remove pipes/spaces; remaining should be only '-', ':'
        core = s.replace("|", "").replace(" ", "").replace("\t", "")
        return core != "" and set(core) <= {"-", ":"}

    rows: List[List[str]] = []
    for line in lines[header_idx + 1 :]:
        if _is_separator(line):
            continue
        if "|" not in line:
            continue
        cells = _parse_row(line)
        # Only accept rows matching header length; otherwise skip to avoid column drift
        if len(cells) == len(headers):
            rows.append(cells)

    return headers, rows


def parse_inline_math_commands(text: str) -> str:
    """Parse inline LaTeX math commands (copied from 07_build_set_pdf.py)."""
    if not text or not isinstance(text, str):
        return str(text) if text else ""
    
    greek_map = {
        r'\\theta': 'θ', r'\\alpha': 'α', r'\\beta': 'β', r'\\gamma': 'γ',
        r'\\delta': 'δ', r'\\pi': 'π', r'\\sigma': 'σ', r'\\mu': 'μ',
        r'\\lambda': 'λ', r'\\omega': 'ω',
    }
    
    math_functions = ['cos', 'sin', 'tan', 'sec', 'csc', 'cot', 'log', 'ln', 'exp']
    
    text = re.sub(r'\^\\circ', '°', text)
    text = re.sub(r'\^\{\\circ\}', '°', text)
    
    for latex, unicode_char in greek_map.items():
        text = re.sub(latex, unicode_char, text)
    
    text = re.sub(r'\\le\b', '≤', text)
    text = re.sub(r'\\leq\b', '≤', text)
    text = re.sub(r'\\ge\b', '≥', text)
    text = re.sub(r'\\geq\b', '≥', text)
    text = re.sub(r'\\propto\b', '∝', text)
    
    greek_chars = ''.join(greek_map.values())
    for func in math_functions:
        text = re.sub(rf'\\{func}([{greek_chars}])', rf'<i>{func}</i> \1', text)
        text = re.sub(rf'\\{func}(?=\d|\()', f'<i>{func}</i>', text)
        text = re.sub(rf'\\{func}(?=\s|$|;|,|→|\)|°|≤|≥|∝)', f'<i>{func}</i>', text)
    
    text = re.sub(r'  +', ' ', text)
    return text


def parse_math_expressions(text: str) -> str:
    """Parse $...$ math expressions (copied from 07_build_set_pdf.py)."""
    if not text or not isinstance(text, str):
        return str(text) if text else ""
    
    symbol_map = {
        r'\\propto': '∝', r'\\leq': '≤', r'\\geq': '≥', r'\\times': '×', r'\\div': '÷',
        r'\\theta': 'θ', r'\\alpha': 'α', r'\\beta': 'β', r'\\gamma': 'γ', r'\\delta': 'δ',
        r'\\pi': 'π', r'\\sigma': 'σ', r'\\mu': 'μ', r'\\lambda': 'λ', r'\\omega': 'ω',
    }
    
    def process_math_expression(match):
        expr = match.group(1)
        for latex, unicode_char in symbol_map.items():
            expr = re.sub(latex, unicode_char, expr)
        expr = re.sub(r'\^\\circ', '°', expr)
        expr = re.sub(r'\^\{\\circ\}', '°', expr)
        math_functions = ['cos', 'sin', 'tan', 'sec', 'csc', 'cot', 'log', 'ln', 'exp']
        for func in math_functions:
            expr = re.sub(rf'\\{func}\b', func, expr)
        return f'<i>{expr}</i>'
    
    text = re.sub(r'\$([^$\n]+?)\$', process_math_expression, text)
    return text


def parse_markdown_formatting(text: str) -> str:
    """Parse markdown formatting to HTML tags (copied from 07_build_set_pdf.py)."""
    if not text or not isinstance(text, str):
        return str(text) if text else ""
    
    text = parse_inline_math_commands(text)
    text = parse_math_expressions(text)
    
    def process_markdown_in_segments(text_str: str) -> str:
        result = []
        i = 0
        
        while i < len(text_str):
            # Treat as HTML tag only when it actually looks like a tag.
            # This avoids swallowing comparison operators like "<1cm" which are common in tables.
            if (
                text_str[i] == '<'
                and i + 1 < len(text_str)
                and (text_str[i + 1].isalpha() or text_str[i + 1] in ['/', '!'])
            ):
                in_tag = True
                result.append(text_str[i])
                i += 1
                while i < len(text_str) and text_str[i] != '>':
                    result.append(text_str[i])
                    i += 1
                if i < len(text_str):
                    result.append(text_str[i])
                    i += 1
            else:
                segment_start = i
                while i < len(text_str):
                    if (
                        text_str[i] == '<'
                        and i + 1 < len(text_str)
                        and (text_str[i + 1].isalpha() or text_str[i + 1] in ['/', '!'])
                    ):
                        break
                    i += 1
                segment = text_str[segment_start:i]
                if segment:
                    segment = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', segment)
                    segment = re.sub(r'___(.+?)___', r'<b><i>\1</i></b>', segment)
                    segment = re.sub(r'(?<!\*)\*\*(?!\*)(.+?)(?<!\*)\*\*(?!\*)', r'<b>\1</b>', segment)
                    segment = re.sub(r'(?<!_)__(?!_)(.+?)(?<!_)__(?!_)', r'<b>\1</b>', segment)
                    segment = re.sub(r'(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', segment)
                    segment = re.sub(r'(?<!_)_(?!_)([^_]+?)(?<!_)_(?!_)', r'<i>\1</i>', segment)
                    result.append(segment)
        
        return ''.join(result)
    
    text = process_markdown_in_segments(text)
    return text


def sanitize_html_final(text: str) -> str:
    """
    Final HTML sanitization for reportlab (NO markdown parsing here).
    
    Assumes text has already been through parse_markdown_formatting().
    Only handles:
    - HTML tag balancing
    - <br/> normalization
    - Escaped HTML entities cleanup
    """
    if not text or not isinstance(text, str):
        return str(text) if text else ""
    
    # Remove <para> tags
    for _ in range(3):
        text = re.sub(r'</?para[^>]*>', '', text, flags=re.IGNORECASE)
    
    # Fix escaped HTML tags that should be actual tags
    text = re.sub(r'&lt;br\s*/?\s*&gt;', '<br/>', text, flags=re.IGNORECASE)
    text = re.sub(r'&lt;(/?)i&gt;', r'<\1i>', text, flags=re.IGNORECASE)
    text = re.sub(r'&lt;(/?)b&gt;', r'<\1b>', text, flags=re.IGNORECASE)
    
    # Balance tags
    def balance_tags(text_str, tag_name):
        open_pattern = rf'<{tag_name}>'
        close_pattern = rf'</{tag_name}>'
        open_count = len(re.findall(open_pattern, text_str, re.IGNORECASE))
        close_count = len(re.findall(close_pattern, text_str, re.IGNORECASE))
        if close_count > open_count:
            excess = close_count - open_count
            for _ in range(excess):
                text_str = re.sub(close_pattern, '', text_str, count=1, flags=re.IGNORECASE)
        return text_str
    
    text = balance_tags(text, 'i')
    text = balance_tags(text, 'b')
    
    # Convert <br> to <br/>
    text = re.sub(r'<br\s*/?>', '<br/>', text, flags=re.IGNORECASE)
    
    return text


def bold_important_terms(text: str) -> str:
    """
    Add bold formatting to important terms in table cells.
    
    Patterns to bold:
    - Medical abbreviations (CT, MRI, X-ray, etc.)
    - Capitalized medical terms (e.g., "Codman triangle")
    - Numbers with units or comparisons (e.g., "2cm", "< 2cm", "> 50%")
    """
    if not text or not isinstance(text, str):
        return str(text) if text else ""
    
    # Avoid processing already bolded text
    if '<b>' in text or '</b>' in text:
        return text
    
    # Track positions that are already bolded to avoid double bolding
    bolded_positions = set()
    
    def is_position_bolded(pos):
        for start, end in bolded_positions:
            if start <= pos < end:
                return True
        return False
    
    # Pattern 1: Numbers with units or comparisons (e.g., "2cm", "< 2cm", "> 50%")
    def bold_number_with_unit(match):
        start, end = match.span()
        if is_position_bolded(start):
            return match.group(0)
        bolded_positions.add((start, end))
        token = match.group(1)
        # Escape comparator symbols so ReportLab doesn't treat them as tag delimiters.
        # Keep any leading whitespace.
        token = re.sub(r'(^\s*)<', r'\1&lt;', token, count=1)
        token = re.sub(r'(^\s*)>', r'\1&gt;', token, count=1)
        return f'<b>{token}</b>'

    # One-pass matcher:
    # - comparator is only allowed when preceded by start/whitespace (avoids matching the '>' in '<br/>')
    # - otherwise matches plain numbers with units anywhere
    text = re.sub(
        r'((?:(?<!\S)[<>≤≥=]\s*)?\d+\.?\d*\s*(?:cm|mm|%))',
        bold_number_with_unit,
        text,
    )
    
    # Pattern 2: Medical abbreviations (case-insensitive)
    medical_abbrevs = [
        r'\b(CT|MRI|XR|X-ray|CXR|NM|US|PET|SPECT)\b',
        r'\b(T1|T2|T1WI|T2WI|FS|STIR|DWI|ADC)\b',
    ]
    
    for pattern in medical_abbrevs:
        def bold_abbrev(match):
            start, end = match.span()
            if is_position_bolded(start):
                return match.group(0)
            bolded_positions.add((start, end))
            return f'<b>{match.group(1)}</b>'
        
        text = re.sub(pattern, bold_abbrev, text, flags=re.IGNORECASE)

    # Pattern 3: Terms in parentheses - intentionally NOT bolded
    # (This behavior matches the current 07_build_set_pdf.py implementation note.)

    # Pattern 4: Capitalized medical terms (conservative: multi-word only)
    common_words = {'The', 'This', 'That', 'With', 'From', 'And', 'Or', 'But', 'For', 'To'}

    def bold_capitalized_term(match):
        term = match.group(1)
        if term in common_words:
            return term
        start, end = match.span()
        if is_position_bolded(start):
            return term
        bolded_positions.add((start, end))
        return f'<b>{term}</b>'

    # Only bold multi-word capitalized terms (e.g., "Giant Cell Tumor")
    text = re.sub(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', bold_capitalized_term, text)
    
    # Clean up: remove duplicate bold tags and fix spacing
    text = re.sub(r'</b>\s*<b>', ' ', text)
    text = re.sub(r'<b><b>', '<b>', text)
    text = re.sub(r'</b></b>', '</b>', text)
    
    return text


def add_line_breaks_at_delimiters(text: str) -> str:
    """
    Add line breaks at semicolons and ensure proper spacing after commas.
    (Ported from 07_build_set_pdf.py)
    
    Preserves HTML tags.
    """
    if not text:
        return text
    
    result = []
    i = 0
    in_tag = False
    
    while i < len(text):
        char = text[i]
        
        if char == '<':
            in_tag = True
            result.append(char)
            i += 1
        elif char == '>':
            in_tag = False
            result.append(char)
            i += 1
        elif in_tag:
            result.append(char)
            i += 1
        elif char == ';':
            # Semicolon: always add line break after it
            result.append(';')
            i += 1
            if i < len(text):
                if text[i] == ' ':
                    result.append('<br/>')
                    i += 1
                elif text[i] != '\n' and text[i] != '<':
                    result.append('<br/>')
            else:
                result.append('<br/>')
        elif char == ',':
            # Comma outside HTML tag
            result.append(',')
            i += 1
            if i < len(text) and text[i] == ' ':
                result.append(' ')
                i += 1
            elif i < len(text) and text[i] != '\n':
                result.append(' ')
        else:
            result.append(char)
            i += 1
    
    return ''.join(result)


# =========================
# Korean Objectives Loading
# =========================

def load_korean_objectives_from_canonical(base_dir: Path, group_key: str) -> List[str]:
    """Load Korean objectives from groups_canonical.csv based on group_key."""
    canonical_path = base_dir / "2_Data" / "metadata" / "groups_canonical.csv"
    if not canonical_path.exists():
        return []
    
    try:
        with open(canonical_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("group_key", "").strip() == group_key:
                    objective_list_kr = row.get("objective_list_kr", "").strip()
                    if objective_list_kr:
                        try:
                            objectives = json.loads(objective_list_kr)
                            if isinstance(objectives, list):
                                return [obj for obj in objectives if obj and obj.strip()]
                        except (json.JSONDecodeError, TypeError):
                            pass
                    break
    except Exception:
        pass
    
    return []


def build_group_key_from_path(group_path: str) -> str:
    """
    Build group_key from group_path *excluding specialty*.

    groups_canonical.csv uses keys like:
      anatomy__modality_or_type__category
    while group_path is typically:
      specialty > anatomy > modality_or_type > category
    """
    if not group_path:
        return ""
    raw_parts = [p.strip() for p in str(group_path).split(" > ") if p and p.strip()]
    if not raw_parts:
        return ""
    # Drop specialty (first token)
    parts = raw_parts[1:] if len(raw_parts) >= 2 else []
    norm = [p.lower().replace(" ", "_") for p in parts if p and p.lower() != "nan"]
    return "__".join(norm)


def resolve_group_key_for_objectives(s1_record: Dict[str, Any]) -> str:
    """
    Determine the canonical `group_key` for objectives lookup.

    Priority:
    1) S1 record's `group_key` if present (most reliable)
    2) Derive from `group_path` excluding specialty
    """
    if not s1_record:
        return ""
    direct = str(s1_record.get("group_key", "") or "").strip()
    if direct and direct.lower() not in ("nan", "none", "null"):
        return direct
    return build_group_key_from_path(str(s1_record.get("group_path", "") or ""))


# =========================
# PDF Page Header/Footer (Simplified - No Hyperlinks)
# =========================

class HeaderInfoFlowable(Flowable):
    """
    A zero-size flowable that updates header info and creates bookmark anchors.
    
    Works with HeaderTrackingDocTemplate's afterFlowable callback for proper
    synchronization between header display and page content.
    """
    def __init__(
        self,
        group_path: str,
        section_type: str,
        bookmark: str = "",
        *,
        hide_header: bool = False,
        hide_footer: bool = False,
    ):
        Flowable.__init__(self)
        self.group_path = group_path
        self.section_type = section_type
        self.bookmark = bookmark
        self.hide_header = bool(hide_header)
        self.hide_footer = bool(hide_footer)
        self.width = 0
        self.height = 0
    
    def draw(self):
        """Create bookmark anchor for hyperlinks and TOC."""
        # Register bookmark anchor if specified
        if self.bookmark:
            self.canv.bookmarkPage(self.bookmark)
        
        # Note: The actual header info update happens in HeaderTrackingDocTemplate.afterFlowable()
        # This ensures the info is available when the page header is rendered


def set_page_header(story: List, group_path: str, section_type: str, bookmark: str = "") -> None:
    """Add header info flowable to update the header for the current page."""
    story.append(HeaderInfoFlowable(group_path, section_type, bookmark))


def draw_modern_header(canvas_obj, doc, korean_font: str = "Helvetica"):
    """
    Draw gradient header with group path and section type.
    
    Reads header info from doc.current_header_info (set by HeaderTrackingDocTemplate).
    Each path segment is rendered as a clickable hyperlink.
    """
    # Get header info from DocTemplate (set by afterFlowable callback)
    header_info = getattr(doc, 'current_header_info', {})
    group_path = header_info.get('group_path', '')
    section_type = header_info.get('section_type', '')
    hide_header = bool(header_info.get("hide_header", False))
    hide_footer = bool(header_info.get("hide_footer", False))

    if hide_header:
        return
    
    page_width, page_height = doc.pagesize
    header_y = page_height - HEADER_HEIGHT
    
    # Draw gradient background (left: Deep Navy -> right: Ocean Blue)
    num_steps = 40
    step_width = page_width / num_steps
    
    for i in range(num_steps):
        ratio = i / (num_steps - 1)
        r = 0x1B + (0x4A - 0x1B) * ratio
        g = 0x3A + (0x90 - 0x3A) * ratio
        b = 0x5F + (0xD9 - 0x5F) * ratio
        
        color = colors.Color(r/255, g/255, b/255, alpha=0.95)
        canvas_obj.setFillColor(color)
        canvas_obj.rect(i * step_width, header_y, step_width + 1, HEADER_HEIGHT, fill=1, stroke=0)
    
    # Draw vertical accent bar (left side)
    canvas_obj.setStrokeColor(colors.Color(1, 1, 1, alpha=0.5))
    canvas_obj.setLineWidth(2)
    bar_x = 8
    bar_y_start = header_y + 4
    bar_y_end = header_y + HEADER_HEIGHT - 4
    canvas_obj.line(bar_x, bar_y_start, bar_x, bar_y_end)
    
    # Build display text: PATH | SECTION_TYPE
    display_text = ""
    if group_path:
        parts = group_path.split(" > ")
        formatted_parts = ["CONTENTS"]
        for part in parts:
            if part and part.lower() != 'nan' and part.strip():
                formatted_parts.append(part.upper().replace("_", " "))
        
        display_text = " › ".join(formatted_parts)
        
        # Add section type after path with | separator
        if section_type:
            display_text = f"{display_text}  |  {section_type}"
    elif section_type:
        display_text = section_type
    
    # Draw path + section type (left side)
    if display_text:
        canvas_obj.setFillColor(COLOR_WHITE)

        text_x = 20
        text_y = header_y + (HEADER_HEIGHT / 2) - 3

        # Reserve width for right-side logo + padding.
        reserved_right = 130
        max_path_width = max(50, page_width - reserved_right - text_x)

        # Adaptive font sizing to avoid clipping.
        font_size = 10
        while font_size >= 7 and canvas_obj.stringWidth(display_text, korean_font, font_size) > max_path_width:
            font_size -= 1

        # If still too long at min font, truncate path segments (keep section type).
        max_iter = 50
        iter_count = 0
        while canvas_obj.stringWidth(display_text, korean_font, font_size) > max_path_width and iter_count < max_iter:
            iter_count += 1
            if "  |  " in display_text:
                path_part, section_part = display_text.split("  |  ", 1)
                path_parts = path_part.split(" › ")
                if len(path_parts) > 2:
                    path_parts = path_parts[:-1]
                    path_part = " › ".join(path_parts) + " › ..."
                    display_text = f"{path_part}  |  {section_part}"
                else:
                    display_text = f"...  |  {section_part}"
                    break
            else:
                # No section delimiter: hard-truncate
                if len(display_text) > 8:
                    display_text = display_text[: max(0, len(display_text) - 4)] + "..."
                else:
                    break

        canvas_obj.setFont(korean_font, font_size)
        canvas_obj.drawString(text_x, text_y, display_text)
    
    # Draw MeducAI logo (right side)
    canvas_obj.setFillColor(COLOR_WHITE)
    canvas_obj.setFont(korean_font, 10)
    text_x = page_width - 20
    text_y = header_y + (HEADER_HEIGHT / 2) - 3
    canvas_obj.drawRightString(text_x, text_y, "MeducAI")
    
    # Draw bottom border line
    canvas_obj.setStrokeColor(COLOR_PALE_GRAY)
    canvas_obj.setLineWidth(1)
    canvas_obj.line(0, header_y, page_width, header_y)


def draw_modern_footer(canvas_obj, doc, page_num: int, korean_font: str = "Helvetica"):
    """Draw modern footer with page numbers."""
    header_info = getattr(doc, 'current_header_info', {})
    if bool(header_info.get("hide_footer", False)):
        return

    page_width = doc.pagesize[0]
    footer_y = FOOTER_HEIGHT
    
    # Draw top border line
    canvas_obj.setStrokeColor(COLOR_PALE_GRAY)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(0, footer_y + 0.3 * cm, page_width, footer_y + 0.3 * cm)
    
    # Draw page number with decorative lines: ── 1 ──
    page_text = f"──  {page_num}  ──"
    text_x = page_width / 2
    text_y = 0.4 * cm
    
    canvas_obj.setFillColor(COLOR_OCEAN_BLUE)
    canvas_obj.setFont(korean_font, 9)
    canvas_obj.drawCentredString(text_x, text_y, page_text)


def create_main_page_template(
    page_size: tuple,
    korean_font: str = "Helvetica",
    margins: Optional[Dict[str, float]] = None,
) -> PageTemplate:
    """
    Create main PageTemplate for HeaderTrackingDocTemplate.
    
    This template includes:
    - Custom Frame with proper margins
    - onPage callback that draws header and footer
    - Header reads from doc.current_header_info (updated via afterFlowable)
    
    Args:
        page_size: Page size tuple (width, height) in points
        korean_font: Font name for header text
        margins: Dict with 'left', 'right', 'top', 'bottom' margins in cm
    
    Returns:
        PageTemplate configured for modern header/footer rendering
    """
    if margins is None:
        margins = {
            'left': CONTENT_MARGIN_X,
            'right': CONTENT_MARGIN_X,
            'top': HEADER_HEIGHT + CONTENT_MARGIN_Y_EXTRA,
            'bottom': FOOTER_HEIGHT + CONTENT_MARGIN_Y_EXTRA,
        }
    
    page_width, page_height = page_size
    
    # Calculate frame dimensions
    frame_width = page_width - margins['left'] - margins['right']
    frame_height = page_height - margins['top'] - margins['bottom']
    
    def draw_header_footer(canvas_obj, doc):
        """Draw header and footer on each page."""
        canvas_obj.saveState()
        
        # Draw header (reads from doc.current_header_info)
        draw_modern_header(canvas_obj, doc, korean_font)
        
        # Draw footer with page number
        page_num = canvas_obj.getPageNumber()
        draw_modern_footer(canvas_obj, doc, page_num, korean_font)
        
        canvas_obj.restoreState()
    
    # Create frame for content area
    frame = Frame(
        margins['left'],
        margins['bottom'],
        frame_width,
        frame_height,
        id='normal',
        showBoundary=0,  # Set to 1 for debugging
    )
    
    # Use onPageEnd so header/footer are rendered *after* flowables on the page.
    # This makes header section_type match the page content (afterFlowable timing),
    # and prevents full-page cover artwork from covering the header.
    return PageTemplate(
        id='main',
        frames=[frame],
        onPageEnd=draw_header_footer,
        pagesize=page_size,
    )


# =========================
# Table Building
# =========================

def build_master_table(
    md_table: str,
    styles: Dict[str, ParagraphStyle],
    page_width: float,
    korean_font: str,
    korean_font_bold: Optional[str] = None,
) -> Optional[Table]:
    """
    Build a styled master table from markdown with improved styling.
    
    Styling policy (based on 07_build_set_pdf.py):
    - Font sizes: 9pt for header and cells (as requested)
    - Entity name column: bold, line breaks after '&' and before '('
    - Other cells: line breaks after semicolons, auto-bold for medical terms
    - Dynamic column widths based on content
    """
    headers, rows = parse_markdown_table(md_table)
    if not headers or not rows:
        return None
    
    if korean_font_bold is None:
        korean_font_bold = korean_font
    
    # Calculate available width based on the same margins used by the main Frame
    available_width = page_width - (2 * CONTENT_MARGIN_X)
    
    # Font sizes (9pt for readability per user request)
    header_font_size = 9
    cell_font_size = 9
    entity_name_font_size = 9
    
    # Find "Entity name" column index (usually first column)
    entity_name_col_idx = 0
    for idx, header in enumerate(headers):
        header_lower = str(header).strip().lower()
        if "entity" in header_lower and "name" in header_lower:
            entity_name_col_idx = idx
            break
    
    # Create styles for table cells (9pt with leading 11 for readability)
    cell_style = ParagraphStyle(
        name="TableCellImproved",
        fontName=korean_font,
        fontSize=cell_font_size,
        leading=11,  # 9pt * 1.2 = 10.8 → 11
        alignment=TA_LEFT,
        splitLongWords=True,
        allowWidows=0,
        allowOrphans=0,
    )
    
    entity_style = ParagraphStyle(
        name="TableCellEntity",
        fontName=korean_font_bold,  # Entity column in bold
        fontSize=entity_name_font_size,
        leading=11,  # 9pt * 1.2 = 10.8 → 11
        alignment=TA_LEFT,
        splitLongWords=True,
        allowWidows=0,
        allowOrphans=0,
    )
    
    header_style = ParagraphStyle(
        name="TableHeaderImproved",
        fontName=korean_font_bold,  # Headers in bold
        fontSize=header_font_size,
        leading=11,  # 9pt * 1.2 = 10.8 → 11
        alignment=TA_CENTER,
        textColor=COLOR_CHARCOAL,  # Dark text on light background
    )
    
    # Convert to Paragraphs for proper text wrapping
    # Following 07_build_set_pdf.py formatting rules exactly
    table_data = []
    # Header row
    header_row = []
    for h in headers:
        text = parse_markdown_formatting(str(h).strip())
        text = sanitize_html_final(text)
        if not ('<b>' in text or '</b>' in text):
            text = f"<b>{text}</b>"
        header_row.append(Paragraph(text, header_style))
    table_data.append(header_row)

    # Data rows
    for row in rows:
        processed_row = []
        for cell_idx, cell in enumerate(row):
            text = str(cell).strip()

            if cell_idx == entity_name_col_idx:
                # Entity name column - ALWAYS bold, break after '&' and before '('
                # Process markdown FIRST (before adding <br/> tags)
                text = parse_markdown_formatting(text)
                
                # Add line breaks: after "& " and before "("
                text = re.sub(r'&\s+', '&<br/>', text)
                text = re.sub(r'\s+\(', '<br/>(', text)
                
                # Final sanitization (no markdown parsing)
                text = sanitize_html_final(text)
                
                # Ensure bold (entity name is always bold)
                if not ('<b>' in text or '</b>' in text):
                    text = f"<b>{text}</b>"
                style = entity_style
            elif cell_idx == 1:
                # Second column - also allow line breaks before "("
                # Process markdown FIRST
                text = parse_markdown_formatting(text)
                
                # Add line break before "("
                text = re.sub(r'\s+\(', '<br/>(', text)
                
                # Apply line breaks at semicolons and commas
                text = add_line_breaks_at_delimiters(text)
                
                # Apply automatic bolding to important terms (after markdown, before final sanitization)
                text = bold_important_terms(text)
                
                # Final sanitization (no markdown parsing)
                text = sanitize_html_final(text)
                style = cell_style
            else:
                # Other columns - process markdown first, then format
                text = parse_markdown_formatting(text)
                
                # Apply line breaks at semicolons and commas
                text = add_line_breaks_at_delimiters(text)
                
                # Apply automatic bolding to important terms (after markdown, before final sanitization)
                text = bold_important_terms(text)
                
                # Final sanitization (no markdown parsing)
                text = sanitize_html_final(text)
                style = cell_style
            
            processed_row.append(Paragraph(text, style))
        table_data.append(processed_row)
    
    if not table_data:
        return None
    
    # Calculate column widths
    num_cols = len(headers) if headers else (len(table_data[0]) if table_data else 1)
    
    # Dynamic column width calculation based on content
    # Column weights: [Entity Name, Definition, Findings, Path, DDx, Key Points]
    if num_cols >= 6:
        weights = [1.2, 1.5, 2.0, 1.5, 1.0, 1.2]
        total_weight = sum(weights[:num_cols])
        col_widths = [(w / total_weight) * available_width for w in weights[:num_cols]]
    else:
        col_widths = [available_width / num_cols] * num_cols
    
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    # Style the table with improved design
    table_style = TableStyle([
        # Header row - light gray background with dark text
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_SOFT_GRAY),  # #F5F7FA
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_CHARCOAL),    # #2D3748
        ('FONTNAME', (0, 0), (-1, 0), korean_font_bold),
        ('FONTSIZE', (0, 0), (-1, 0), header_font_size),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        
        # Data rows
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), COLOR_CHARCOAL),
        ('FONTSIZE', (0, 1), (-1, -1), cell_font_size),
        
        # Entity column (first column) bold - handled via ParagraphStyle
        ('FONTNAME', (entity_name_col_idx, 1), (entity_name_col_idx, -1), korean_font_bold),
        
        # Grid - using Pale Gray (#E2E8F0)
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_PALE_GRAY),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_PALE_GRAY),
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
        
        # Padding (slightly increased to reduce cramped feel with Korean fonts)
        ('TOPPADDING', (0, 0), (-1, 0), 5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ])
    
    table.setStyle(table_style)
    return table


# =========================
# Cover Page
# =========================

# Path to cover base image
COVER_IMAGE_PATH = Path(__file__).parent / "assets" / "cover_base.jpg"

# Cover page dimensions (A4 landscape @ 100 DPI)
COVER_WIDTH = 1191  # pixels at 100 DPI
COVER_HEIGHT = 842  # pixels at 100 DPI


def render_cover_page(
    canvas_obj: canvas.Canvas,
    specialty_name: str,
    page_width: float,
    page_height: float,
    korean_font: str = "Helvetica",
) -> None:
    """
    Render cover page with base image, MeducAI title, and specialty name overlay.
    
    The image is center-cropped (no resize) to preserve original quality.
    MeducAI title and specialty name are rendered via PDF text.
    
    Args:
        canvas_obj: ReportLab canvas to draw on
        specialty_name: Specialty name to overlay (English, e.g., "Neuro HN Imaging")
        page_width: Page width in points
        page_height: Page height in points
        korean_font: Font name for text rendering
    """
    from PIL import Image as PILImage
    
    if not COVER_IMAGE_PATH.exists():
        # Fallback: Draw a gradient background if cover image doesn't exist
        _render_cover_fallback(canvas_obj, specialty_name, page_width, page_height, korean_font)
        return
    
    try:
        # Load image and center-crop to page size (no resize to preserve quality)
        with PILImage.open(COVER_IMAGE_PATH) as img:
            # Convert to RGB if necessary
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            img_width, img_height = img.size
            
            # Calculate target crop size based on page aspect ratio
            page_aspect = page_width / page_height
            img_aspect = img_width / img_height
            
            if img_aspect > page_aspect:
                # Image is wider - crop width
                crop_height = img_height
                crop_width = int(crop_height * page_aspect)
            else:
                # Image is taller - crop height
                crop_width = img_width
                crop_height = int(crop_width / page_aspect)
            
            # Center crop coordinates
            left = (img_width - crop_width) // 2
            top = (img_height - crop_height) // 2
            right = left + crop_width
            bottom = top + crop_height
            
            # Crop image (no resize - preserves original quality)
            img_cropped = img.crop((left, top, right, bottom))
            
            # Save to buffer with high quality
            img_buffer = BytesIO()
            img_cropped.save(img_buffer, format="JPEG", quality=95, optimize=True)
            img_buffer.seek(0)
            
            # Draw image on canvas (full page)
            from reportlab.lib.utils import ImageReader
            img_reader = ImageReader(img_buffer)
            canvas_obj.drawImage(
                img_reader,
                0, 0,
                width=page_width,
                height=page_height,
                preserveAspectRatio=True,
                anchor='c',
            )
        
        # Draw MeducAI title at top center
        _draw_meducai_title(canvas_obj, page_width, page_height, korean_font)
        
        # Draw specialty name overlay in the bottom third
        _draw_specialty_overlay(canvas_obj, specialty_name, page_width, page_height, korean_font)
        
    except Exception as e:
        print(f"  Warning: Failed to render cover image: {e}")
        _render_cover_fallback(canvas_obj, specialty_name, page_width, page_height, korean_font)


def _draw_meducai_title(
    canvas_obj: canvas.Canvas,
    page_width: float,
    page_height: float,
    font: str,
) -> None:
    """
    Draw MeducAI title at the top center of the cover page.
    
    Uses semi-transparent background for readability over any image.
    """
    # Title position: upper area of the page
    title_y = page_height * 0.78
    
    # Draw semi-transparent background behind title
    canvas_obj.saveState()
    canvas_obj.setFillColor(colors.Color(0.1, 0.2, 0.35, alpha=0.5))
    title_bg_height = 80
    canvas_obj.rect(
        0, title_y - 20,
        page_width, title_bg_height,
        fill=1, stroke=0
    )
    canvas_obj.restoreState()
    
    # Draw "MeducAI" title
    canvas_obj.setFillColor(COLOR_WHITE)
    canvas_obj.setFont(font, 52)
    canvas_obj.drawCentredString(page_width / 2, title_y, "MeducAI")


def _render_cover_fallback(
    canvas_obj: canvas.Canvas,
    specialty_name: str,
    page_width: float,
    page_height: float,
    font: str,
) -> None:
    """Render fallback cover page with gradient background if image is not available."""
    # Draw gradient background (Deep Navy -> Ocean Blue)
    num_steps = 100
    step_height = page_height / num_steps
    
    for i in range(num_steps):
        # Interpolate from top (lighter) to bottom (darker)
        ratio = i / (num_steps - 1)
        # Top: Ocean Blue, Bottom: Deep Navy
        r = 0x4A + (0x1B - 0x4A) * ratio
        g = 0x90 + (0x3A - 0x90) * ratio
        b = 0xD9 + (0x5F - 0xD9) * ratio
        
        color = colors.Color(r/255, g/255, b/255)
        canvas_obj.setFillColor(color)
        y = page_height - (i + 1) * step_height
        canvas_obj.rect(0, y, page_width, step_height + 1, fill=1, stroke=0)
    
    # Draw MeducAI title
    _draw_meducai_title(canvas_obj, page_width, page_height, font)
    
    # Draw specialty name overlay
    _draw_specialty_overlay(canvas_obj, specialty_name, page_width, page_height, font)


def _draw_specialty_overlay(
    canvas_obj: canvas.Canvas,
    specialty_name: str,
    page_width: float,
    page_height: float,
    font: str,
) -> None:
    """
    Draw specialty name overlay in the bottom third of the cover page.
    
    The overlay consists of:
    - A semi-transparent dark background bar
    - The specialty name in large white text, centered (English)
    """
    if not specialty_name:
        return
    
    # Overlay position: bottom 1/3 of page
    overlay_height = page_height / 5  # Compact height for clean look
    overlay_y = page_height / 8 - overlay_height / 2  # Lower position
    
    # Draw semi-transparent dark background
    canvas_obj.saveState()
    canvas_obj.setFillColor(colors.Color(0.1, 0.15, 0.25, alpha=0.65))
    canvas_obj.rect(
        0, overlay_y,
        page_width, overlay_height,
        fill=1, stroke=0
    )
    canvas_obj.restoreState()
    
    # Draw decorative lines above and below the overlay area
    line_y_top = overlay_y + overlay_height
    line_y_bottom = overlay_y
    
    canvas_obj.setStrokeColor(colors.Color(1, 1, 1, alpha=0.3))
    canvas_obj.setLineWidth(1)
    canvas_obj.line(page_width * 0.15, line_y_top, page_width * 0.85, line_y_top)
    canvas_obj.line(page_width * 0.15, line_y_bottom, page_width * 0.85, line_y_bottom)
    
    # Draw specialty name text (English)
    canvas_obj.setFillColor(COLOR_WHITE)
    
    # Use larger font for specialty name
    font_size = 32
    canvas_obj.setFont(font, font_size)
    
    # Center text vertically and horizontally
    text_y = overlay_y + (overlay_height / 2) - (font_size / 3)
    canvas_obj.drawCentredString(page_width / 2, text_y, specialty_name)


class CoverPageFlowable:
    """
    A custom flowable that renders a full-page cover image with specialty overlay.
    
    This flowable uses KeepInFrame to ensure it fits, and draws directly on the canvas.
    """
    
    def __init__(
        self,
        specialty_name: str,
        page_width: float,
        page_height: float,
        font: str = "Helvetica",
    ):
        from reportlab.platypus import Flowable
        # We need to inherit from Flowable, but do it dynamically
        self.specialty_name = specialty_name
        self.page_width = page_width
        self.page_height = page_height
        self.font = font


def create_cover_flowable(
    specialty_name: str,
    page_width: float,
    page_height: float,
    font: str = "Helvetica",
):
    """
    Create a cover page flowable that renders the cover image with specialty overlay.
    
    This returns a Flowable subclass instance that can be added to a story.
    """
    from reportlab.platypus import Flowable
    
    class _CoverPageFlowable(Flowable):
        """Custom flowable that renders the full cover page."""
        
        def __init__(self, spec_name: str, pw: float, ph: float, text_font: str):
            Flowable.__init__(self)
            self.specialty_name = spec_name
            self._page_width = pw
            self._page_height = ph
            self.font = text_font
            # Set width/height to 0 so it doesn't consume frame space
            # We'll draw on absolute canvas coordinates
            self.width = 0
            self.height = 0
        
        def draw(self):
            """Draw the cover page on the canvas at absolute coordinates."""
            canvas_obj = self.canv
            
            # Save state and reset to absolute positioning
            canvas_obj.saveState()
            
            # Get frame offset to calculate absolute position
            # The flowable's (0,0) is at the current frame position
            # We need to draw at page (0,0), so translate negatively
            frame = getattr(self, '_frame', None)
            if frame:
                # Translate to page origin
                canvas_obj.translate(-frame._x, -frame._y)
            
            # Render the cover page at page origin
            render_cover_page(
                canvas_obj,
                self.specialty_name,
                self._page_width,
                self._page_height,
                self.font,
            )
            
            canvas_obj.restoreState()
        
        def wrap(self, availWidth, availHeight):
            # Return 0,0 - this flowable doesn't consume normal space
            # It draws on the full page canvas instead
            return (0, 0)
    
    return _CoverPageFlowable(specialty_name, page_width, page_height, font)


def add_cover_page_to_story(
    story: List,
    specialty_name: str,
    page_width: float,
    page_height: float,
    font: str = "Helvetica",
) -> None:
    """
    Add a cover page flowable and page break to the story.
    
    The cover page is rendered as a zero-height flowable that draws
    on the full canvas, followed by a page break.
    
    Args:
        story: List of flowables to append to
        specialty_name: Specialty name for overlay (English)
        page_width: Page width in points
        page_height: Page height in points
        font: Font name for text rendering
    """
    # Cover pages don't need header/footer (and cover artwork could obscure them).
    # Set flags for this page via a zero-size flowable.
    story.append(HeaderInfoFlowable("", "", "", hide_header=True, hide_footer=True))

    # Create and add the cover flowable
    cover = create_cover_flowable(
        specialty_name=specialty_name,
        page_width=page_width,
        page_height=page_height,
        font=font,
    )
    story.append(cover)
    story.append(PageBreak())


# =========================
# Image Handling
# =========================

def add_image_to_story(
    story: List,
    image_path: str,
    page_width: float,
    page_height: float,
    max_height_ratio: float = 0.7,
    optimize: bool = True,
    max_dpi: float = 150.0,
    jpeg_quality: int = 85,
    center_vertically: bool = False,
) -> bool:
    """Add an image to the story, scaled to fit the page with optional optimization."""
    if not image_path or not Path(image_path).exists():
        return False
    
    try:
        from PIL import Image as PILImage
        
        with PILImage.open(image_path) as img:
            img_width, img_height = img.size
        
        # Calculate available space (match the main Frame geometry)
        # Content area excludes header/footer bands and the small extra padding margin.
        available_width = page_width - (2 * CONTENT_MARGIN_X)
        content_height = page_height - (HEADER_HEIGHT + FOOTER_HEIGHT) - (2 * CONTENT_MARGIN_Y_EXTRA)
        available_height = content_height * max_height_ratio
        
        # Scale to fit
        width_ratio = available_width / img_width
        height_ratio = available_height / img_height
        scale = min(width_ratio, height_ratio)
        
        final_width = img_width * scale
        final_height = img_height * scale

        # Optional vertical centering within the available content height.
        # Useful for infographics so they don't sit at the top of the frame.
        if center_vertically:
            top_space = max(0.0, (available_height - final_height) / 2.0)
            if top_space > 0:
                story.append(Spacer(1, top_space))
        
        # Optimize image if needed
        if optimize:
            # Calculate target resolution based on display size and max DPI
            target_width = int(final_width * max_dpi / 72)  # 72 points per inch
            target_height = int(final_height * max_dpi / 72)
            
            with PILImage.open(image_path) as img:
                # Only resize if image is larger than target
                if img_width > target_width or img_height > target_height:
                    # Calculate resize ratio maintaining aspect ratio
                    resize_ratio = min(target_width / img_width, target_height / img_height)
                    new_size = (int(img_width * resize_ratio), int(img_height * resize_ratio))
                    
                    # Resize and compress
                    # Use LANCZOS (PIL 10+) or fallback for high-quality resize
                    try:
                        resample = PILImage.Resampling.LANCZOS  # PIL 10+
                    except (AttributeError, NameError):
                        try:
                            resample = getattr(PILImage, 'LANCZOS', None)  # PIL 9.x
                            if resample is None:
                                resample = getattr(PILImage, 'ANTIALIAS', 1)  # PIL 8.x
                        except (AttributeError, NameError):
                            resample = 1  # Fallback to LANCZOS value
                    img_resized = img.resize(new_size, resample)
                    
                    # Convert to RGB if necessary (for JPEG)
                    if img_resized.mode in ("RGBA", "P"):
                        img_resized = img_resized.convert("RGB")
                    
                    # Save to BytesIO
                    img_buffer = BytesIO()
                    img_resized.save(img_buffer, format="JPEG", quality=jpeg_quality, optimize=True)
                    img_buffer.seek(0)
                    
                    rl_image = RLImage(img_buffer, width=final_width, height=final_height)
                    story.append(rl_image)
                    return True
        
        # Use original image if not optimizing or image is small enough
        rl_image = RLImage(image_path, width=final_width, height=final_height)
        story.append(rl_image)
        return True
    except Exception as e:
        print(f"  Warning: Failed to add image {image_path}: {e}")
        return False


# =========================
# PDF Building Functions
# =========================

def build_group_section(
    story: List,
    s1_record: Dict[str, Any],
    image_mapping: Dict[Tuple, str],
    styles: Dict[str, ParagraphStyle],
    page_width: float,
    page_height: float,
    korean_font: str,
    korean_font_bold: Optional[str] = None,
    include_tables: bool = True,
    include_infographics: bool = True,
    include_objectives: bool = True,
    base_dir: Optional[Path] = None,
    add_section_breaks: bool = True,
    infographic_max_dpi: float = 120.0,
    infographic_jpeg_quality: int = 80,
) -> None:
    """Build PDF section for a single group with section page breaks.
    
    Header shows: CONTENTS › SPECIALTY › ... | SECTION_TYPE   MeducAI
    Section type (OBJECTIVE GOAL, MASTER TABLE, INFOGRAPHIC) appears in header, not in content.
    """
    if korean_font_bold is None:
        korean_font_bold = korean_font
    
    group_id = s1_record.get("group_id", "")
    group_path = s1_record.get("group_path", "")
    added_any = False

    # Peek at content availability up front to avoid inserting blank pages
    md_table_peek = (s1_record.get("master_table_markdown_kr", "") or "").strip() if include_tables else ""
    cluster_images_peek: List[Tuple[str, str]] = []
    if include_infographics and image_mapping:
        for key, path in image_mapping.items():
            spec_kind, cluster_id, _ = key
            if spec_kind == "S1_TABLE_VISUAL" and cluster_id:
                cluster_images_peek.append((cluster_id, path))
        cluster_images_peek.sort(key=lambda x: x[0])
    
    # Generate bookmark for this group (used for hyperlinks)
    # Format: CONTENTS_SPECIALTY_ANATOMY_MODALITY_CATEGORY
    bookmark_base = "CONTENTS"
    if group_path:
        parts = group_path.split(" > ")
        for part in parts:
            if part and part.lower() != 'nan' and part.strip():
                bookmark_base += "_" + part.upper().replace(" ", "_")
    
    # Learning Objectives (use Korean objectives from canonical if available)
    if include_objectives:
        objectives = []
        
        # Try to load Korean objectives from groups_canonical.csv
        if base_dir is not None:
            group_key = resolve_group_key_for_objectives(s1_record)
            objectives = load_korean_objectives_from_canonical(base_dir, group_key)
        
        # Fallback to S1 objective_bullets if no Korean objectives found
        if not objectives:
            objectives = s1_record.get("objective_bullets", [])
        
        if objectives:
            # With larger objective leading (e.g., 30), objectives can span multiple pages.
            # Using KeepTogether here can easily create blank pages (it pushes the whole block).
            # So we render objectives as normal flowables and let ReportLab split naturally.

            # Set header info for OBJECTIVE GOAL section (appears in header box)
            bookmark_obj = f"{bookmark_base}_OBJECTIVE"
            story.append(HeaderInfoFlowable(group_path, "OBJECTIVE GOAL", bookmark_obj))

            for obj in objectives:
                obj_text = f"• {obj}"
                obj_text = parse_markdown_formatting(obj_text)
                obj_text = sanitize_html_final(obj_text)
                story.append(Paragraph(obj_text, styles["Objective"]))

            story.append(Spacer(1, 8))
            added_any = True
        
        # Page break after objectives section ONLY if there is a next section with content.
        if add_section_breaks and (bool(md_table_peek) or bool(cluster_images_peek)):
            story.append(PageBreak())
    
    # Master Table
    if include_tables:
        md_table = s1_record.get("master_table_markdown_kr", "")
        if md_table:
            # Set header info for MASTER TABLE section (appears in header box)
            bookmark_table = f"{bookmark_base}_TABLE"
            set_page_header(story, group_path, "MASTER TABLE", bookmark_table)
            
            # Content only - section title is in the header
            table = build_master_table(
                md_table, styles, page_width, korean_font, korean_font_bold
            )
            if table:
                # Do NOT shrink the table (user requested removal; shrink can distort layout).
                story.append(table)
                added_any = True
            story.append(Spacer(1, 12))
        
        # Page break after table section
        if add_section_breaks and bool(cluster_images_peek):
            story.append(PageBreak())
    
    # Infographics
    if include_infographics:
        # Find cluster infographics for this group
        cluster_images = cluster_images_peek
        
        if cluster_images:
            # Set header info for INFOGRAPHIC section (appears in header box)
            bookmark_info = f"{bookmark_base}_INFOGRAPHIC"
            set_page_header(story, group_path, "INFOGRAPHIC", bookmark_info)
            
            # Content only - section title is in the header
            for i, (cluster_id, img_path) in enumerate(cluster_images):
                if add_image_to_story(
                    story, img_path, page_width, page_height, 
                    # Infographics: fit as large as possible in the content frame (keep aspect ratio)
                    max_height_ratio=0.98,
                    # Tablet/laptop-friendly compression
                    optimize=True,
                    max_dpi=infographic_max_dpi,
                    jpeg_quality=infographic_jpeg_quality,
                    center_vertically=True,
                ):
                    story.append(Spacer(1, 4))
                    added_any = True
                
                # Page break between infographics (except after the last one)
                if add_section_breaks and i < len(cluster_images) - 1:
                    story.append(PageBreak())
    
    # Final page break for next group
    # Avoid emitting fully blank pages for groups with no renderable content.
    if added_any:
        story.append(PageBreak())
    else:
        # If we didn't render any section, don't force a blank page.
        pass


def calculate_specialty_pages(
    grouped_records: Dict[str, List[Dict[str, Any]]],
    include_objectives: bool = True,
    include_tables: bool = True,
    include_infographics: bool = True,
) -> Dict[str, int]:
    """
    Calculate approximate starting page numbers for each specialty.
    
    Estimation logic:
    - Cover page: 1 page
    - TOC: 1 page
    - Each specialty: 1 cover page + content pages
    - Each group: 1 page (objectives) + 1 page (table) + ~2 pages (infographics)
    
    Returns:
        Dict mapping specialty -> starting page number (1-indexed)
    """
    specialty_pages = {}
    current_page = 1
    
    # Cover + TOC
    current_page += 2
    
    # IMPORTANT: iteration order should match curriculum ordering (caller pre-orders grouped_records).
    for specialty in grouped_records.keys():
        records = grouped_records[specialty]
        
        # Specialty cover page
        specialty_pages[specialty] = current_page
        current_page += 1
        
        # Content pages (estimate)
        for record in records:
            # Objectives: 1 page (usually fits, but KeepTogether ensures it)
            if include_objectives:
                current_page += 1
            
            # Table: 1 page
            if include_tables:
                current_page += 1
            
            # Infographics: estimate 2 pages per group (can vary)
            if include_infographics:
                current_page += 2
    
    return specialty_pages


def build_toc_simple(
    story: List,
    grouped_records: Dict[str, List[Dict[str, Any]]],
    styles: Dict[str, ParagraphStyle],
    specialty_page_map: Optional[Dict[str, int]] = None,
) -> None:
    """Build table of contents with page numbers and hyperlinks if available.
    
    Format:
        CONTENTS
        
        Abdominal Radiology ................... 5
        Cardiac Radiology ..................... 42
        ...
    
    Args:
        specialty_page_map: Dict mapping specialty -> starting page number
    """
    # TOC page: hide header/footer (not needed, and avoids stale header info).
    story.append(HeaderInfoFlowable("", "", "", hide_header=True, hide_footer=True))

    # Title
    story.append(Paragraph("CONTENTS", styles["Title"]))
    story.append(Spacer(1, 30))
    
    # Create TOC entry style
    toc_entry_style = ParagraphStyle(
        name="TOCEntryWithPages",
        parent=styles["BodyText"],
        fontSize=12,
        leading=18,
        leftIndent=30,
        rightIndent=30,
        textColor=COLOR_CHARCOAL,
    )
    
    # IMPORTANT: iteration order should match curriculum ordering (caller pre-orders grouped_records).
    for specialty in grouped_records.keys():
        specialty_en = SPECIALTY_NAMES_EN.get(specialty, specialty.replace("_", " ").title())
        
        # Create bookmark for this specialty (e.g., "CONTENTS_ABDOMINAL_RADIOLOGY")
        bookmark_name = f"CONTENTS_{specialty.upper()}"
        
        if specialty_page_map and specialty in specialty_page_map:
            # With page numbers and hyperlinks (using ReportLab's internal link syntax)
            page_num = specialty_page_map[specialty]
            # Create dotted line with page number
            dots = " " + "." * 50 + " "
            toc_text = f'<link destination="{bookmark_name}">{specialty_en}{dots}{page_num}</link>'
            story.append(Paragraph(toc_text, toc_entry_style))
        else:
            # Without page numbers (fallback)
            toc_text = f'<link destination="{bookmark_name}">{specialty_en}</link>'
            story.append(Paragraph(toc_text, toc_entry_style))
        
        story.append(Spacer(1, 6))
    
    story.append(PageBreak())


def build_toc(
    story: List,
    grouped_records: Dict[str, List[Dict[str, Any]]],
    styles: Dict[str, ParagraphStyle],
    specialty_page_map: Optional[Dict[str, int]] = None,
) -> None:
    """Build table of contents (simplified version - English only).
    
    This is a wrapper that calls build_toc_simple for backwards compatibility.
    """
    build_toc_simple(story, grouped_records, styles, specialty_page_map)


def build_full_pdf(
    base_dir: Path,
    run_tag: str,
    arm: str,
    out_path: Path,
    s1_arm: Optional[str] = None,
    infographic_max_dpi: float = 120.0,
    infographic_jpeg_quality: int = 80,
) -> Path:
    """Build complete distribution PDF with all content.
    
    Structure:
    1. Main cover page (Complete Collection)
    2. Table of Contents (English specialty names + estimated page numbers + hyperlinks)
    3. For each specialty:
       - Specialty cover page (with specialty name overlay)
       - Group sections (Objective Goal → Master Table → Infographic)
    
    Page numbers in TOC are estimated based on content (close approximation).
    """
    print(f"Building full PDF: {out_path}")
    
    gen_dir = get_generated_dir(base_dir, run_tag)
    s1_arm_actual = s1_arm or arm
    s1_path = resolve_s1_struct_path(gen_dir, s1_arm_actual)
    print(f"  Using S1 data: {s1_path.name}")
    s4_manifest_path = gen_dir / f"s4_image_manifest__arm{arm.upper()}.jsonl"
    
    # Load data
    s1_records = load_all_s1_records(s1_path)
    if not s1_records:
        raise RuntimeError(f"No S1 records found at {s1_path}")
    
    image_mapping_all = load_s4_image_manifest_all(s4_manifest_path, gen_dir)
    grouped_records = apply_curriculum_order(
        base_dir=base_dir,
        grouped_records=group_records_by_specialty(s1_records),
    )
    
    print(f"  Loaded {len(s1_records)} groups across {len(grouped_records)} specialties")
    
    # Setup PDF
    korean_font, korean_font_bold = setup_korean_fonts()
    styles = create_pdf_styles(korean_font, korean_font_bold)
    
    page_size = landscape(A4)
    page_width, page_height = page_size
    
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Calculate estimated specialty starting pages
    specialty_page_map = calculate_specialty_pages(
        grouped_records,
        include_objectives=True,
        include_tables=True,
        include_infographics=True,
    )
    print(f"  Calculated page estimates for {len(specialty_page_map)} specialties")
    
    # Build PDF with HeaderTrackingDocTemplate
    doc = HeaderTrackingDocTemplate(str(out_path), pagesize=page_size)
    page_template = create_main_page_template(page_size, korean_font)
    doc.addPageTemplates([page_template])
    
    story = []
    
    # 1. Main cover page (Complete Collection)
    add_cover_page_to_story(
        story=story,
        specialty_name="Complete Collection",
        page_width=page_width,
        page_height=page_height,
        font=korean_font,
    )
    
    # 2. Table of Contents (WITH estimated page numbers and hyperlinks)
    build_toc_simple(story, grouped_records, styles, specialty_page_map)
    
    # 3. Content by specialty (with cover page and bookmarks for each specialty)
    for specialty in grouped_records.keys():
        records = grouped_records[specialty]
        specialty_en = SPECIALTY_NAMES_EN.get(specialty, specialty.replace("_", " ").title())
        
        # Add bookmark for this specialty's starting page
        bookmark_specialty = f"CONTENTS_{specialty.upper()}"
        story.append(HeaderInfoFlowable("", "", bookmark_specialty))
        
        # Specialty cover page (insert before each specialty section)
        add_cover_page_to_story(
            story=story,
            specialty_name=specialty_en,
            page_width=page_width,
            page_height=page_height,
            font=korean_font,
        )
        
        # Group content for this specialty
        for record in records:
            group_id = record.get("group_id", "")
            image_mapping = image_mapping_all.get(group_id, {})
            
            build_group_section(
                story=story,
                s1_record=record,
                image_mapping=image_mapping,
                styles=styles,
                page_width=page_width,
                page_height=page_height,
                korean_font=korean_font,
                korean_font_bold=korean_font_bold,
                include_tables=True,
                include_infographics=True,
                include_objectives=True,
                base_dir=base_dir,
                add_section_breaks=True,
                infographic_max_dpi=infographic_max_dpi,
                infographic_jpeg_quality=infographic_jpeg_quality,
            )
    
    # Build PDF
    doc.build(story)
    print(f"  Generated: {out_path} ({out_path.stat().st_size / 1024 / 1024:.1f} MB)")
    
    return out_path


def build_tables_only_pdf(
    base_dir: Path,
    run_tag: str,
    arm: str,
    out_path: Path,
    s1_arm: Optional[str] = None,
) -> Path:
    """Build tables-only PDF for quick reference.
    
    Structure:
    1. Main cover page (Tables Only)
    2. Table of Contents (English specialty names + estimated page numbers + hyperlinks)
    3. For each specialty:
       - Specialty cover page
       - Group sections (Objective Goal → Master Table, no infographics)
    """
    print(f"Building tables-only PDF: {out_path}")
    
    gen_dir = get_generated_dir(base_dir, run_tag)
    s1_arm_actual = s1_arm or arm
    s1_path = resolve_s1_struct_path(gen_dir, s1_arm_actual)
    print(f"  Using S1 data: {s1_path.name}")
    
    # Load data
    s1_records = load_all_s1_records(s1_path)
    if not s1_records:
        raise RuntimeError(f"No S1 records found at {s1_path}")
    
    grouped_records = apply_curriculum_order(
        base_dir=base_dir,
        grouped_records=group_records_by_specialty(s1_records),
    )
    
    print(f"  Loaded {len(s1_records)} groups across {len(grouped_records)} specialties")
    
    # Setup PDF
    korean_font, korean_font_bold = setup_korean_fonts()
    styles = create_pdf_styles(korean_font, korean_font_bold)
    
    page_size = landscape(A4)
    page_width, page_height = page_size
    
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Calculate estimated specialty starting pages
    specialty_page_map = calculate_specialty_pages(
        grouped_records,
        include_objectives=True,
        include_tables=True,
        include_infographics=False,  # Tables only
    )
    print(f"  Calculated page estimates for {len(specialty_page_map)} specialties")
    
    # Build PDF with HeaderTrackingDocTemplate
    doc = HeaderTrackingDocTemplate(str(out_path), pagesize=page_size)
    page_template = create_main_page_template(page_size, korean_font)
    doc.addPageTemplates([page_template])
    
    story = []
    
    # 1. Main cover page (Tables Only)
    add_cover_page_to_story(
        story=story,
        specialty_name="Tables Only",
        page_width=page_width,
        page_height=page_height,
        font=korean_font,
    )
    
    # 2. Table of Contents (WITH estimated page numbers and hyperlinks)
    build_toc_simple(story, grouped_records, styles, specialty_page_map)
    
    # 3. Content by specialty (with cover page and bookmarks)
    for specialty in grouped_records.keys():
        records = grouped_records[specialty]
        specialty_en = SPECIALTY_NAMES_EN.get(specialty, specialty.replace("_", " ").title())
        
        # Add bookmark for this specialty's starting page
        bookmark_specialty = f"CONTENTS_{specialty.upper()}"
        story.append(HeaderInfoFlowable("", "", bookmark_specialty))
        
        # Specialty cover page
        add_cover_page_to_story(
            story=story,
            specialty_name=specialty_en,
            page_width=page_width,
            page_height=page_height,
            font=korean_font,
        )
        
        # Group content (tables only)
        for record in records:
            build_group_section(
                story=story,
                s1_record=record,
                image_mapping={},  # No images
                styles=styles,
                page_width=page_width,
                page_height=page_height,
                korean_font=korean_font,
                korean_font_bold=korean_font_bold,
                include_tables=True,
                include_infographics=False,  # No infographics
                include_objectives=True,
                base_dir=base_dir,
                add_section_breaks=True,
            )
    
    # Build PDF
    doc.build(story)
    print(f"  Generated: {out_path} ({out_path.stat().st_size / 1024 / 1024:.1f} MB)")
    
    return out_path


def build_specialty_pdf(
    base_dir: Path,
    run_tag: str,
    arm: str,
    specialty: str,
    out_path: Path,
    s1_arm: Optional[str] = None,
    infographic_max_dpi: float = 120.0,
    infographic_jpeg_quality: int = 80,
) -> Optional[Path]:
    """Build PDF for a single specialty.
    
    Structure:
    1. Cover page (with specialty name overlay)
    2. Group sections (Objective Goal → Master Table → Infographic)
    
    No TOC for single specialty PDFs - directly to content after cover.
    """
    print(f"Building specialty PDF: {specialty} -> {out_path}")
    
    gen_dir = get_generated_dir(base_dir, run_tag)
    s1_arm_actual = s1_arm or arm
    s1_path = resolve_s1_struct_path(gen_dir, s1_arm_actual)
    s4_manifest_path = gen_dir / f"s4_image_manifest__arm{arm.upper()}.jsonl"
    
    # Load data
    s1_records = load_all_s1_records(s1_path)
    if not s1_records:
        raise RuntimeError(f"No S1 records found at {s1_path}")
    
    image_mapping_all = load_s4_image_manifest_all(s4_manifest_path, gen_dir)
    
    # Filter to this specialty
    specialty_records = [
        r for r in s1_records 
        if r.get("group_path", "").split(" > ")[0].strip() == specialty
    ]
    
    if not specialty_records:
        print(f"  Warning: No records found for specialty {specialty}")
        return None
    
    print(f"  Found {len(specialty_records)} groups for {specialty}")

    # Order groups within specialty by curriculum order
    _, order_by_specialty = _load_curriculum_group_order(base_dir)
    order_map = order_by_specialty.get(specialty, {})
    specialty_records = sorted(
        specialty_records,
        key=lambda r: (
            order_map.get((r.get("group_id") or "").strip(), 10**9),
            (r.get("group_path") or ""),
            (r.get("group_id") or ""),
        ),
    )
    
    # Setup PDF
    korean_font, korean_font_bold = setup_korean_fonts()
    styles = create_pdf_styles(korean_font, korean_font_bold)
    
    page_size = landscape(A4)
    page_width, page_height = page_size
    
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Use HeaderTrackingDocTemplate for proper header tracking
    doc = HeaderTrackingDocTemplate(
        str(out_path),
        pagesize=page_size,
    )
    
    # Add PageTemplate
    page_template = create_main_page_template(page_size, korean_font)
    doc.addPageTemplates([page_template])
    
    story = []
    specialty_en = SPECIALTY_NAMES_EN.get(specialty, specialty.replace("_", " ").title())
    
    # Cover page with image and specialty name overlay (English)
    add_cover_page_to_story(
        story=story,
        specialty_name=specialty_en,
        page_width=page_width,
        page_height=page_height,
        font=korean_font,
    )
    
    # Content (directly after cover - no TOC for single specialty)
    for record in specialty_records:
        group_id = record.get("group_id", "")
        image_mapping = image_mapping_all.get(group_id, {})
        
        build_group_section(
            story=story,
            s1_record=record,
            image_mapping=image_mapping,
            styles=styles,
            page_width=page_width,
            page_height=page_height,
            korean_font=korean_font,
            korean_font_bold=korean_font_bold,
            include_tables=True,
            include_infographics=True,
            include_objectives=True,
            base_dir=base_dir,
            add_section_breaks=True,
            infographic_max_dpi=infographic_max_dpi,
            infographic_jpeg_quality=infographic_jpeg_quality,
        )
    
    # Build PDF
    doc.build(story)
    print(f"  Generated: {out_path} ({out_path.stat().st_size / 1024 / 1024:.1f} MB)")
    
    return out_path


def build_by_specialty_pdfs(
    base_dir: Path,
    run_tag: str,
    arm: str,
    out_dir: Path,
    s1_arm: Optional[str] = None,
    infographic_max_dpi: float = 120.0,
    infographic_jpeg_quality: int = 80,
) -> List[Path]:
    """Build separate PDFs for each specialty."""
    print(f"Building by-specialty PDFs: {out_dir}")
    
    gen_dir = get_generated_dir(base_dir, run_tag)
    s1_arm_actual = s1_arm or arm
    s1_path = resolve_s1_struct_path(gen_dir, s1_arm_actual)
    print(f"  Using S1 data for specialty discovery: {s1_path.name}")
    
    # Load data to get specialties
    s1_records = load_all_s1_records(s1_path)
    if not s1_records:
        raise RuntimeError(f"No S1 records found at {s1_path}")
    
    grouped_records = apply_curriculum_order(
        base_dir=base_dir,
        grouped_records=group_records_by_specialty(s1_records),
    )
    
    print(f"  Found {len(grouped_records)} specialties")
    
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_paths = []
    
    for specialty in grouped_records.keys():
        out_path = out_dir / f"MeducAI_{specialty}.pdf"
        path = build_specialty_pdf(
            base_dir=base_dir,
            run_tag=run_tag,
            arm=arm,
            specialty=specialty,
            out_path=out_path,
            s1_arm=s1_arm,
            infographic_max_dpi=infographic_max_dpi,
            infographic_jpeg_quality=infographic_jpeg_quality,
        )
        if path:
            generated_paths.append(path)
    
    print(f"  Generated {len(generated_paths)} specialty PDFs")
    return generated_paths


# =========================
# CLI
# =========================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build distribution PDFs in various modes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  full         - Complete PDF with all content (objectives, tables, infographics)
  tables_only  - Tables-only PDF for quick reference
  by_specialty - Separate PDFs for each specialty (11 files)
  all          - Generate all of the above

Examples:
  # Full integrated PDF
  python3 3_Code/src/tools/build_distribution_pdf.py \\
    --mode full \\
    --run_tag FINAL_DISTRIBUTION \\
    --arm G \\
    --out_dir 6_Distributions/MeducAI_Final_Share/PDF

  # All modes at once
  python3 3_Code/src/tools/build_distribution_pdf.py \\
    --mode all \\
    --run_tag FINAL_DISTRIBUTION \\
    --arm G \\
    --out_dir 6_Distributions/MeducAI_Final_Share/PDF
        """,
    )
    
    parser.add_argument(
        "--mode",
        type=str,
        required=True,
        choices=["full", "tables_only", "by_specialty", "all"],
        help="PDF generation mode",
    )
    parser.add_argument(
        "--base_dir",
        type=str,
        default=".",
        help="Project base directory",
    )
    parser.add_argument(
        "--run_tag",
        type=str,
        required=True,
        help="Run tag (e.g., FINAL_DISTRIBUTION)",
    )
    parser.add_argument(
        "--arm",
        type=str,
        required=True,
        help="Arm identifier (e.g., G)",
    )
    parser.add_argument(
        "--s1_arm",
        type=str,
        default=None,
        help="S1 arm if different from --arm",
    )
    parser.add_argument(
        "--out_dir",
        type=str,
        default="6_Distributions/MeducAI_Final_Share/PDF",
        help="Output directory for all PDFs (default: 6_Distributions/MeducAI_Final_Share/PDF)",
    )
    parser.add_argument(
        "--infographic_max_dpi",
        type=float,
        default=120.0,
        help="Max DPI for infographic images embedded in PDFs (default: 120.0). Increase for sharper text.",
    )
    parser.add_argument(
        "--infographic_jpeg_quality",
        type=int,
        default=80,
        help="JPEG quality for infographic images (default: 80). Increase for sharper text.",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    
    # out_dir: base directory for all PDFs
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = base_dir / out_dir
    
    generated_files = []
    
    try:
        if args.mode in ["full", "all"]:
            full_path = out_dir / "MeducAI_FINAL_ALL.pdf"
            build_full_pdf(
                base_dir=base_dir,
                run_tag=args.run_tag,
                arm=args.arm,
                out_path=full_path,
                s1_arm=args.s1_arm,
                infographic_max_dpi=args.infographic_max_dpi,
                infographic_jpeg_quality=args.infographic_jpeg_quality,
            )
            generated_files.append(full_path)
        
        if args.mode in ["tables_only", "all"]:
            tables_path = out_dir / "MeducAI_Tables_Only.pdf"
            build_tables_only_pdf(
                base_dir=base_dir,
                run_tag=args.run_tag,
                arm=args.arm,
                out_path=tables_path,
                s1_arm=args.s1_arm,
            )
            generated_files.append(tables_path)
        
        if args.mode in ["by_specialty", "all"]:
            # Specialty PDFs go to Specialty/ subdirectory
            specialty_out_dir = out_dir / "Specialty"
            paths = build_by_specialty_pdfs(
                base_dir=base_dir,
                run_tag=args.run_tag,
                arm=args.arm,
                out_dir=specialty_out_dir,
                s1_arm=args.s1_arm,
                infographic_max_dpi=args.infographic_max_dpi,
                infographic_jpeg_quality=args.infographic_jpeg_quality,
            )
            generated_files.extend(paths)
        
        print(f"\n✅ Generated {len(generated_files)} PDF files")
        for f in generated_files:
            print(f"   {f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


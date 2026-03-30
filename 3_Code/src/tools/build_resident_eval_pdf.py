"""
Build Resident Evaluation PDF Packets
--------------------------------------
전공의 평가용 PDF 생성 스크립트

구성:
- 9명 전공의 (reviewer_master.csv의 resident)
- Assignments.csv에서 각 전공의에게 할당된 카드 목록 추출
- 그룹 단위로 PDF 생성: 학습목표 + 테이블 + 인포그래픽 + S5 평가점수

Usage:
    python3 3_Code/src/tools/build_resident_eval_pdf.py --base_dir . --out_dir 6_Distributions/Final_QA/Resident_Eval_Packets

Output:
    6_Distributions/Final_QA/Resident_Eval_Packets/
        Reviewer_11/
            grp_XXXX.pdf
            grp_YYYY.pdf
            ...
        Reviewer_12/
            ...
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add parent directory to path for imports
_THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_THIS_DIR.parent))

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, inch
from reportlab.platypus import (
    Image as RLImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage
from io import BytesIO

# =========================
# Constants
# =========================

RUN_TAG = "FINAL_DISTRIBUTION"
ARM = "G"


# =========================
# Data Loading
# =========================

def load_reviewer_master(base_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Load reviewer master CSV and return residents only."""
    reviewer_path = base_dir / "1_Secure_Participant_Info" / "reviewer_master.csv"
    residents = {}
    
    with open(reviewer_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("role", "").strip().lower() == "resident":
                email = row.get("reviewer_email", "").strip()
                residents[email] = {
                    "reviewer_id": row.get("reviewer_id", "").strip(),
                    "reviewer_name": row.get("reviewer_name", "").strip(),
                    "institution": row.get("institution", "").strip(),
                }
    
    return residents


def load_assignments(base_dir: Path) -> List[Dict[str, Any]]:
    """Load assignments CSV."""
    assignments_path = base_dir / "2_Data" / "metadata" / "generated" / RUN_TAG / "appsheet_export" / "Assignments.csv"
    assignments = []
    
    with open(assignments_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            assignments.append(row)
    
    return assignments


def load_s1_struct_all(gen_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Load all S1 structures indexed by group_id."""
    s1_path = gen_dir / f"stage1_struct__arm{ARM}.jsonl"
    s1_data = {}
    
    if not s1_path.exists():
        return s1_data
    
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                group_id = record.get("group_id", "")
                if group_id:
                    s1_data[group_id] = record
            except json.JSONDecodeError:
                continue
    
    return s1_data


def load_s5_validation_all(gen_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Load all S5 validation records indexed by group_id."""
    s5_path = gen_dir / f"s5_validation__arm{ARM}.jsonl"
    s5_data = {}
    
    if not s5_path.exists():
        return s5_data
    
    from datetime import datetime
    
    with open(s5_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                group_id = record.get("group_id", "")
                if group_id:
                    # Keep latest by timestamp
                    ts_str = record.get("validation_timestamp", "")
                    if group_id in s5_data:
                        existing_ts_str = s5_data[group_id].get("validation_timestamp", "")
                        try:
                            if ts_str.endswith("Z"):
                                ts_str_parsed = ts_str[:-1] + "+00:00"
                            else:
                                ts_str_parsed = ts_str
                            if existing_ts_str.endswith("Z"):
                                existing_ts_str_parsed = existing_ts_str[:-1] + "+00:00"
                            else:
                                existing_ts_str_parsed = existing_ts_str
                            
                            ts = datetime.fromisoformat(ts_str_parsed)
                            existing_ts = datetime.fromisoformat(existing_ts_str_parsed)
                            if ts > existing_ts:
                                s5_data[group_id] = record
                        except Exception:
                            pass
                    else:
                        s5_data[group_id] = record
            except json.JSONDecodeError:
                continue
    
    return s5_data


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


# =========================
# PDF Utilities (from 07_build_set_pdf.py)
# =========================

def register_korean_font() -> Tuple[str, str]:
    """Register Korean font for PDF generation."""
    home_dir = os.path.expanduser("~")
    
    korean_font_candidates = [
        (f"{home_dir}/Library/Fonts/NanumGothic.ttf", f"{home_dir}/Library/Fonts/NanumGothicExtraBold.ttf"),
        ("/Library/Fonts/NanumGothic.ttf", "/Library/Fonts/NanumGothicExtraBold.ttf"),
        (f"{home_dir}/Library/Fonts/NanumGothic.ttf", f"{home_dir}/Library/Fonts/NanumGothicBold.ttf"),
        ("/Library/Fonts/NanumGothic.ttf", "/Library/Fonts/NanumGothicBold.ttf"),
        (f"{home_dir}/Library/Fonts/NotoSansKR-Regular.ttf", f"{home_dir}/Library/Fonts/NotoSansKR-Bold.ttf"),
        ("/Library/Fonts/NotoSansKR-Regular.ttf", "/Library/Fonts/NotoSansKR-Bold.ttf"),
        ("/System/Library/Fonts/Supplemental/AppleSDGothicNeo-Regular.otf", "/System/Library/Fonts/Supplemental/AppleSDGothicNeo-Bold.otf"),
    ]
    
    korean_font_name = "KoreanFont"
    korean_font_bold_name = "KoreanFont-Bold"
    
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
                        pass
                
                if not bold_registered:
                    try:
                        pdfmetrics.registerFont(TTFont(korean_font_bold_name, normal_path))
                    except Exception:
                        korean_font_bold_name = korean_font_name
                
                pdfmetrics.registerFontFamily(
                    korean_font_name,
                    normal=korean_font_name,
                    bold=korean_font_bold_name
                )
                return korean_font_name, korean_font_bold_name
            except Exception:
                continue
    
    return "Helvetica", "Helvetica-Bold"


def create_pdf_styles() -> Tuple[Any, Dict[str, ParagraphStyle], str, str]:
    """Create consistent PDF styles."""
    styles = getSampleStyleSheet()
    korean_font, korean_font_bold = register_korean_font()
    
    custom_styles = {
        "title": ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=16,
            textColor=colors.black,
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName=korean_font,
        ),
        "section": ParagraphStyle(
            "CustomSection",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.black,
            spaceAfter=8,
            spaceBefore=12,
            fontName=korean_font_bold,
        ),
        "section_label": ParagraphStyle(
            "SectionLabel",
            parent=styles["Normal"],
            fontSize=12,
            textColor=colors.HexColor("#666666"),
            spaceAfter=8,
            fontName=korean_font_bold,
            alignment=TA_LEFT,
        ),
        "card_text": ParagraphStyle(
            "CustomCardText",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.black,
            spaceAfter=6,
            fontName=korean_font,
        ),
        "objective_item": ParagraphStyle(
            "ObjectiveItem",
            parent=styles["Normal"],
            fontSize=9,  # Increased from 8pt for better readability
            textColor=colors.black,
            spaceAfter=10,
            leading=13,  # Slightly increased leading for 9pt
            leftIndent=0.5 * cm,
            bulletIndent=0.2 * cm,
            fontName=korean_font,
        ),
        "validation_text": ParagraphStyle(
            "ValidationText",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.black,
            spaceAfter=6,
            fontName=korean_font,
        ),
        "issue_text": ParagraphStyle(
            "IssueText",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#cc0000"),
            spaceAfter=4,
            leftIndent=0.5 * cm,
            fontName=korean_font,
        ),
    }
    
    return styles, custom_styles, korean_font, korean_font_bold


def parse_markdown_formatting(text: str) -> str:
    """
    Parse markdown formatting (bold, italic, etc.) and convert to HTML tags for reportlab.
    """
    if not text or not isinstance(text, str):
        return str(text) if text else ""
    
    # Bold-italic first (triple asterisks/underscores)
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)
    text = re.sub(r'___(.+?)___', r'<b><i>\1</i></b>', text)
    # Bold (double asterisks/underscores)
    text = re.sub(r'(?<!\*)\*\*(?!\*)(.+?)(?<!\*)\*\*(?!\*)', r'<b>\1</b>', text)
    text = re.sub(r'(?<!_)__(?!_)(.+?)(?<!_)__(?!_)', r'<b>\1</b>', text)
    # Italic (single asterisk/underscore)
    text = re.sub(r'(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!_)_(?!_)([^_]+?)(?<!_)_(?!_)', r'<i>\1</i>', text)
    
    return text


def bold_important_terms(text: str) -> str:
    """
    Add bold formatting to important terms in table cells.
    
    Patterns to bold:
    - Medical abbreviations (CT, MRI, X-ray, etc.)
    - Numbers with units (e.g., "2cm", "< 2cm")
    """
    if not text or not isinstance(text, str):
        return str(text) if text else ""
    
    # Avoid processing already bolded text
    if '<b>' in text or '</b>' in text:
        return text
    
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
        return f'<b>{match.group(1)}</b>'
    
    text = re.sub(r'([<>≤≥=]?\s*\d+\.?\d*\s*(?:cm|mm|%))', bold_number_with_unit, text)
    
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
    
    # Clean up: remove duplicate bold tags
    text = re.sub(r'</b>\s*<b>', ' ', text)
    text = re.sub(r'<b><b>', '<b>', text)
    text = re.sub(r'</b></b>', '</b>', text)
    
    return text


def add_line_breaks_at_delimiters(text: str) -> str:
    """Add line breaks at semicolons and ensure proper spacing after commas."""
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
            result.append(';')
            i += 1
            if i < len(text):
                if text[i] == ' ':
                    result.append('<br/>')
                    i += 1
                elif text[i] != '\n' and text[i] != '<':
                    result.append('<br/>')
        elif char == ',':
            result.append(',')
            i += 1
            if i < len(text) and text[i] not in (' ', '\n'):
                result.append(' ')
        else:
            result.append(char)
            i += 1
    
    return ''.join(result)


def sanitize_html_for_reportlab(text: str) -> str:
    """Sanitize HTML text for reportlab Paragraph."""
    if not text or not isinstance(text, str):
        return str(text) if text else ""
    
    # Parse markdown formatting first
    text = parse_markdown_formatting(text)
    
    # Remove <para> tags
    for _ in range(3):
        text = re.sub(r'</?para[^>]*>', '', text, flags=re.IGNORECASE)
    
    # Fix escaped HTML tags
    text = re.sub(r'&lt;br\s*/?\s*&gt;', '<br/>', text, flags=re.IGNORECASE)
    text = re.sub(r'&lt;(/?)i&gt;', r'<\1i>', text, flags=re.IGNORECASE)
    text = re.sub(r'&lt;(/?)b&gt;', r'<\1b>', text, flags=re.IGNORECASE)
    
    # Balance tags
    def balance_tags(text_str, tag_name):
        open_count = len(re.findall(rf'<{tag_name}>', text_str, re.IGNORECASE))
        close_count = len(re.findall(rf'</{tag_name}>', text_str, re.IGNORECASE))
        if close_count > open_count:
            excess = close_count - open_count
            for _ in range(excess):
                text_str = re.sub(rf'</{tag_name}>', '', text_str, count=1, flags=re.IGNORECASE)
        return text_str
    
    text = balance_tags(text, 'i')
    text = balance_tags(text, 'b')
    
    # Convert <br> to <br/>
    text = re.sub(r'<br\s*/?>', '<br/>', text, flags=re.IGNORECASE)
    
    return text


def parse_group_path(s1_record: Dict[str, Any]) -> str:
    """Parse group path from S1 record."""
    def clean_part(part: str) -> str:
        """Clean a path part, removing nan and formatting."""
        part = part.strip()
        if not part or part.lower() in ("nan", "none", "null", ""):
            return ""
        return part.replace("_rad", "").replace("_", " ")
    
    group_path = s1_record.get("group_path", "")
    if group_path:
        parts = [clean_part(p) for p in group_path.split(">")]
        parts = [p for p in parts if p]  # Remove empty parts
        return " > ".join(parts)
    
    group_key = s1_record.get("group_key", "")
    if group_key:
        parts = [clean_part(p) for p in group_key.split("__")]
        parts = [p for p in parts if p]  # Remove empty parts
        return " > ".join(parts)
    
    return ""


def parse_markdown_table(md_table: str) -> Tuple[List[str], List[List[str]]]:
    """Parse markdown table into headers and rows."""
    lines = [line.strip() for line in md_table.strip().split("\n") if line.strip()]
    if not lines:
        return [], []
    
    header_line = None
    header_idx = 0
    for i, line in enumerate(lines):
        if "|" in line:
            header_line = line
            header_idx = i
            break
    
    if not header_line:
        return [], []
    
    headers = [cell.strip() for cell in header_line.split("|") if cell.strip()]
    
    rows = []
    for line in lines[header_idx + 2:]:
        if "|" in line:
            cells = [cell.strip() for cell in line.split("|") if cell.strip()]
            if len(cells) == len(headers):
                rows.append(cells)
    
    return headers, rows


def optimize_image_for_pdf(pil_img: PILImage.Image, width: float, height: float, 
                           max_dpi: float = 150.0, jpeg_quality: int = 85) -> BytesIO:
    """Optimize image for PDF embedding."""
    # Calculate target size based on DPI
    target_width_px = int(width * max_dpi / 72)
    target_height_px = int(height * max_dpi / 72)
    
    # Resize if larger
    if pil_img.width > target_width_px or pil_img.height > target_height_px:
        pil_img.thumbnail((target_width_px, target_height_px), PILImage.Resampling.LANCZOS)
    
    # Save to buffer
    buffer = BytesIO()
    if pil_img.mode in ("RGBA", "P"):
        pil_img = pil_img.convert("RGB")
    pil_img.save(buffer, format="JPEG", quality=jpeg_quality, optimize=True)
    buffer.seek(0)
    
    return buffer


# =========================
# PDF Section Builders
# =========================

def build_objectives_section(
    story: List,
    s1_record: Dict[str, Any],
    base_dir: Path,
    custom_styles: Dict[str, ParagraphStyle],
    korean_font: str,
) -> None:
    """Build Learning Objectives section."""
    group_key = s1_record.get("group_key", "").strip()
    korean_objectives = load_korean_objectives_from_canonical(base_dir, group_key)
    
    if not korean_objectives:
        objective_bullets = s1_record.get("objective_bullets", [])
        korean_objectives = [obj for obj in objective_bullets if obj and obj.strip()]
    
    if not korean_objectives:
        return
    
    # Section label (English)
    group_path = parse_group_path(s1_record)
    story.append(Paragraph(f"{group_path} | Learning Objectives" if group_path else "Learning Objectives", custom_styles["section_label"]))
    story.append(Spacer(1, 0.3 * cm))
    
    # Objectives list
    for objective in korean_objectives:
        if objective and objective.strip():
            formatted = sanitize_html_for_reportlab(str(objective).strip())
            story.append(Paragraph(f"• {formatted}", custom_styles["objective_item"]))
    
    story.append(Spacer(1, 0.5 * cm))


def build_master_table_section(
    story: List,
    s1_record: Dict[str, Any],
    custom_styles: Dict[str, ParagraphStyle],
    page_width: float,
    page_height: float,
    korean_font: str,
    korean_font_bold: str,
) -> None:
    """Build Master Table section with improved readability."""
    master_table_md = s1_record.get("master_table_markdown_kr", "")
    if not master_table_md:
        return
    
    # Section label
    group_path = parse_group_path(s1_record)
    story.append(Paragraph(f"{group_path} | Master Table" if group_path else "Master Table", custom_styles["section_label"]))
    story.append(Spacer(1, 0.3 * cm))
    
    headers, rows = parse_markdown_table(master_table_md)
    if not headers or not rows:
        story.append(Paragraph("(Table data not available)", custom_styles["card_text"]))
        return
    
    # Calculate available dimensions
    available_width = page_width - (1.5 * cm)
    num_cols = len(headers)
    num_rows = len(rows)
    
    # Font sizes - increased for readability
    header_font_size = 9   # Increased from 8pt for better readability
    cell_font_size = 9     # Increased from 8pt for better readability
    
    # Find "Entity name" column index (usually first column)
    entity_name_col_idx = 0
    for idx, header in enumerate(headers):
        header_lower = str(header).strip().lower()
        if "entity" in header_lower and "name" in header_lower:
            entity_name_col_idx = idx
            break
    
    # Calculate dynamic column widths based on content length
    def get_text_length(text: str) -> int:
        """Get text length after removing HTML tags."""
        clean_text = re.sub(r'<[^>]+>', '', text)
        return len(clean_text)
    
    # Calculate average content length for each column
    col_content_lengths = []
    for col_idx in range(num_cols):
        header_text = str(headers[col_idx]).strip()
        header_length = get_text_length(header_text)
        
        data_lengths = []
        for row in rows:
            if col_idx < len(row):
                cell_text = str(row[col_idx]).strip()
                data_lengths.append(get_text_length(cell_text))
        
        avg_data_length = sum(data_lengths) / len(data_lengths) if data_lengths else 0
        # Score based on content length (longer content needs more space)
        content_score = (header_length * 0.3) + (avg_data_length * 0.7)
        
        # Entity name gets more weight, other columns get less
        if col_idx == entity_name_col_idx:
            content_score = content_score * 0.6  # Give more space to entity name
        else:
            content_score = content_score * 0.5
        
        col_content_lengths.append(content_score)
    
    # Distribute available width based on content scores
    total_score = sum(col_content_lengths)
    if total_score > 0:
        col_widths = [(score / total_score) * available_width for score in col_content_lengths]
    else:
        col_widths = [available_width / num_cols] * num_cols
    
    # Ensure minimum width for each column
    min_col_width = available_width / (num_cols * 1.5)
    for i in range(len(col_widths)):
        if col_widths[i] < min_col_width:
            col_widths[i] = min_col_width
    
    # Normalize to fit available width
    total_width = sum(col_widths)
    if total_width > available_width:
        scale = available_width / total_width
        col_widths = [w * scale for w in col_widths]
    
    # Create styles
    header_style = ParagraphStyle(
        "TableHeader",
        parent=custom_styles["card_text"],
        fontSize=header_font_size,
        fontName=korean_font_bold,
        splitLongWords=True,
    )
    
    cell_style = ParagraphStyle(
        "TableCell",
        parent=custom_styles["card_text"],
        fontSize=cell_font_size,
        fontName=korean_font,
        splitLongWords=True,
    )
    
    entity_name_style = ParagraphStyle(
        "EntityNameCell",
        parent=custom_styles["card_text"],
        fontSize=cell_font_size,
        fontName=korean_font_bold,  # Entity name always bold
        splitLongWords=True,
    )
    
    # Build table data
    table_data = []
    
    # Header row
    header_row = []
    for h in headers:
        sanitized = sanitize_html_for_reportlab(h)
        header_row.append(Paragraph(f"<b>{sanitized}</b>", header_style))
    table_data.append(header_row)
    
    # Data rows
    for row in rows:
        data_row = []
        for col_idx, cell in enumerate(row):
            cell_text = str(cell).strip()
            
            # Entity name column - always bold, allow line breaks at & and (
            if col_idx == entity_name_col_idx:
                cell_text = parse_markdown_formatting(cell_text)
                # Add line break after "&" or before "("
                cell_text = re.sub(r'&\s+', '&<br/>', cell_text)
                cell_text = re.sub(r'\s+\(', '<br/>(', cell_text)
                cell_text = sanitize_html_for_reportlab(cell_text)
                if not ('<b>' in cell_text or '</b>' in cell_text):
                    cell_text = f"<b>{cell_text}</b>"
                data_row.append(Paragraph(cell_text, entity_name_style))
            else:
                # Other columns: apply formatting improvements
                cell_text = parse_markdown_formatting(cell_text)
                
                # Add line breaks at "(" for second column
                if col_idx == 1:
                    cell_text = re.sub(r'\s+\(', '<br/>(', cell_text)
                
                # Add line breaks at semicolons
                cell_text = add_line_breaks_at_delimiters(cell_text)
                
                # Bold important terms
                cell_text = bold_important_terms(cell_text)
                
                # Sanitize HTML
                cell_text = sanitize_html_for_reportlab(cell_text)
                
                data_row.append(Paragraph(cell_text, cell_style))
        
        table_data.append(data_row)
    
    # Create table with improved styling
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        # Header styling
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E8E8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (-1, 0), korean_font_bold),
        ("FONTSIZE", (0, 0), (-1, 0), header_font_size),
        # Cell styling
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
        ("FONTNAME", (0, 1), (-1, -1), korean_font),
        ("FONTSIZE", (0, 1), (-1, -1), cell_font_size),
        ("FONTNAME", (entity_name_col_idx, 1), (entity_name_col_idx, -1), korean_font_bold),
        # Grid and padding - INCREASED for better readability
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),   # Increased from 4 to 6
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),  # Increased from 4 to 6
        ("TOPPADDING", (0, 0), (-1, -1), 5),    # Increased from 3 to 5
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5), # Increased from 3 to 5
        ("TOPPADDING", (0, 0), (-1, 0), 6),     # More padding for header
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),  # More padding for header
        # Alternating row colors for readability
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 0.5 * cm))


def build_infographic_section(
    story: List,
    infographic_path: str,
    custom_styles: Dict[str, ParagraphStyle],
    page_width: float,
    page_height: float,
    s1_record: Optional[Dict[str, Any]] = None,
    cluster_label: Optional[str] = None,
) -> None:
    """Build Infographic section for a single infographic image."""
    image_path_obj = Path(infographic_path)
    if not image_path_obj.exists():
        story.append(Paragraph("(Infographic image missing)", custom_styles["card_text"]))
        return
    
    # Section label (English)
    if s1_record:
        group_path = parse_group_path(s1_record)
        if cluster_label:
            label = f"{group_path} | Infographic ({cluster_label})" if group_path else f"Infographic ({cluster_label})"
        else:
            label = f"{group_path} | Infographic" if group_path else "Infographic"
        story.append(Paragraph(label, custom_styles["section_label"]))
    else:
        if cluster_label:
            story.append(Paragraph(f"Infographic ({cluster_label})", custom_styles["section_label"]))
        else:
            story.append(Paragraph("Infographic", custom_styles["section_label"]))
    story.append(Spacer(1, 0.3 * cm))
    
    try:
        pil_img = PILImage.open(image_path_obj)
        img_width_px, img_height_px = pil_img.size
        aspect_ratio = img_height_px / img_width_px if img_width_px > 0 else 1.0
        
        # Calculate display size (fit to page)
        available_width = page_width - (2 * cm)
        available_height = page_height - (5 * cm)
        
        img_width = available_width
        img_height = img_width * aspect_ratio
        
        if img_height > available_height:
            img_height = available_height
            img_width = img_height / aspect_ratio
        
        # Optimize and add image
        optimized_img = optimize_image_for_pdf(pil_img, img_width, img_height, max_dpi=150.0, jpeg_quality=85)
        img = RLImage(optimized_img, width=img_width, height=img_height)
        story.append(img)
        
    except Exception as e:
        story.append(Paragraph(f"(Error loading infographic: {e})", custom_styles["card_text"]))
    
    story.append(Spacer(1, 0.5 * cm))


def build_s5_validation_section(
    story: List,
    s5_record: Dict[str, Any],
    custom_styles: Dict[str, ParagraphStyle],
    s1_record: Optional[Dict[str, Any]] = None,
) -> None:
    """Build S5 Validation Results section (Table validation only, in English)."""
    if not s5_record:
        return
    
    # Section label
    if s1_record:
        group_path = parse_group_path(s1_record)
        story.append(Paragraph(f"{group_path} | S5 Validation" if group_path else "S5 Validation", custom_styles["section_label"]))
    else:
        story.append(Paragraph("S5 Validation", custom_styles["section_label"]))
    story.append(Spacer(1, 0.3 * cm))
    
    # S1 Table Validation only
    s1_validation = s5_record.get("s1_table_validation", {})
    s1_blocking = s1_validation.get("blocking_error", False)
    s1_ta = s1_validation.get("technical_accuracy", 0.0)
    s1_eq = s1_validation.get("educational_quality", 0)
    s1_issues = s1_validation.get("issues", [])
    
    story.append(Paragraph("<b>Table Validation</b>", custom_styles["validation_text"]))
    
    blocking_color = "red" if s1_blocking else "green"
    blocking_text = "Yes" if s1_blocking else "No"
    story.append(Paragraph(f"  • Blocking Error: <font color='{blocking_color}'>{blocking_text}</font>", custom_styles["validation_text"]))
    
    ta_color = "red" if s1_ta < 0.8 else "green"
    story.append(Paragraph(f"  • Technical Accuracy: <font color='{ta_color}'>{s1_ta:.2f}</font>", custom_styles["validation_text"]))
    
    eq_color = "red" if s1_eq < 4 else "green"
    story.append(Paragraph(f"  • Educational Quality: <font color='{eq_color}'>{s1_eq}/5</font>", custom_styles["validation_text"]))
    
    if s1_issues:
        story.append(Paragraph(f"  • Issues: {len(s1_issues)}", custom_styles["validation_text"]))
        for i, issue in enumerate(s1_issues[:3], 1):
            issue_type = issue.get("type", "unknown")
            issue_desc = issue.get("description", "")[:100]
            if issue_desc:
                story.append(Paragraph(f"    {i}. [{issue_type}] {sanitize_html_for_reportlab(issue_desc)}", custom_styles["issue_text"]))
    
    story.append(Spacer(1, 0.5 * cm))




# =========================
# Main PDF Builder
# =========================

def find_infographic_paths(gen_dir: Path, group_id: str) -> List[Tuple[str, Optional[str]]]:
    """
    Find all infographic image paths for a group.
    
    Returns:
        List of (image_path, cluster_label) tuples.
        cluster_label is None for non-clustered infographics.
    """
    images_dir = gen_dir / "images"
    infographics = []
    
    # Pattern for clustered infographics
    cluster_pattern = f"IMG__{RUN_TAG}__{group_id}__TABLE__cluster_"
    
    # Check for clustered infographics
    for img_file in sorted(images_dir.glob("*.jpg")):
        if cluster_pattern in img_file.name:
            # Extract cluster number from filename
            # e.g., IMG__FINAL_DISTRIBUTION__grp_xxx__TABLE__cluster_1.jpg
            match = re.search(r"cluster_(\d+)\.jpg$", img_file.name)
            if match:
                cluster_num = match.group(1)
                infographics.append((str(img_file), f"Cluster {cluster_num}"))
    
    if infographics:
        return infographics
    
    # Try non-clustered infographic
    pattern = f"IMG__{RUN_TAG}__{group_id}__TABLE__"
    for img_file in images_dir.glob("*.jpg"):
        if pattern in img_file.name and "cluster" not in img_file.name:
            return [(str(img_file), None)]
    
    return []




def build_group_pdf(
    *,
    base_dir: Path,
    gen_dir: Path,
    group_id: str,
    entity_ids: List[str],
    s1_record: Dict[str, Any],
    s5_record: Optional[Dict[str, Any]],
    out_path: Path,
) -> Path:
    """Build PDF for a single group."""
    # Create PDF
    page_size = landscape(A4)
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=page_size,
        rightMargin=0.75 * cm,
        leftMargin=0.75 * cm,
        topMargin=0.75 * cm,
        bottomMargin=0.75 * cm,
    )
    
    page_width = page_size[0]
    page_height = page_size[1]
    
    story = []
    styles, custom_styles, korean_font, korean_font_bold = create_pdf_styles()
    
    # Section 1: Learning Objectives
    build_objectives_section(story, s1_record, base_dir, custom_styles, korean_font)
    story.append(PageBreak())
    
    # Section 2: Master Table
    build_master_table_section(story, s1_record, custom_styles, page_width, page_height, korean_font, korean_font_bold)
    story.append(PageBreak())
    
    # Section 3: Infographic(s) - all clusters
    infographic_paths = find_infographic_paths(gen_dir, group_id)
    for infographic_path, cluster_label in infographic_paths:
        build_infographic_section(story, infographic_path, custom_styles, page_width, page_height, s1_record, cluster_label)
        story.append(PageBreak())
    
    # Section 4: S5 Validation Results
    if s5_record:
        build_s5_validation_section(story, s5_record, custom_styles, s1_record)
    
    # Build PDF
    doc.build(story)
    
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build resident evaluation PDF packets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 3_Code/src/tools/build_resident_eval_pdf.py --base_dir . --out_dir 6_Distributions/Final_QA/Resident_Eval_Packets
        """
    )
    
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument("--out_dir", type=str, default="6_Distributions/Final_QA/Resident_Eval_Packets", help="Output directory")
    parser.add_argument("--resident_name", type=str, default=None, help="Process only specific resident (by name)")
    parser.add_argument("--max_groups", type=int, default=None, help="Maximum groups per resident (for testing)")
    parser.add_argument("--dry_run", action="store_true", help="Show what would be generated without creating PDFs")
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    out_dir = Path(args.out_dir)
    gen_dir = base_dir / "2_Data" / "metadata" / "generated" / RUN_TAG
    
    print("=" * 60)
    print("Build Resident Evaluation PDF Packets")
    print("=" * 60)
    
    # Load data
    print("\n[Step 1] Loading data...")
    residents = load_reviewer_master(base_dir)
    print(f"  Found {len(residents)} residents")
    
    assignments = load_assignments(base_dir)
    print(f"  Found {len(assignments)} assignments")
    
    s1_data = load_s1_struct_all(gen_dir)
    print(f"  Loaded {len(s1_data)} S1 records")
    
    s5_data = load_s5_validation_all(gen_dir)
    print(f"  Loaded {len(s5_data)} S5 records")
    
    # Group assignments by resident and group
    print("\n[Step 2] Grouping assignments...")
    resident_groups: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
    
    for assignment in assignments:
        rater_email = assignment.get("rater_email", "").strip()
        rater_role = assignment.get("rater_role", "").strip().lower()
        
        if rater_role != "resident":
            continue
        
        if rater_email not in residents:
            continue
        
        group_id = assignment.get("group_id", "").strip()
        entity_id = assignment.get("entity_id", "").strip()
        
        if group_id and entity_id:
            resident_groups[rater_email][group_id].append(entity_id)
    
    # Process each resident
    print("\n[Step 3] Building PDFs...")
    total_pdfs = 0
    
    for email, groups in resident_groups.items():
        resident_info = residents.get(email, {})
        resident_name = resident_info.get("reviewer_name", email)
        
        if args.resident_name and resident_name != args.resident_name:
            continue
        
        # Create resident output directory
        resident_out_dir = out_dir / resident_name
        if not args.dry_run:
            resident_out_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n  Processing {resident_name} ({len(groups)} groups)...")
        
        group_count = 0
        for group_id, entity_ids in sorted(groups.items()):
            if args.max_groups and group_count >= args.max_groups:
                break
            
            s1_record = s1_data.get(group_id)
            if not s1_record:
                print(f"    [SKIP] {group_id}: S1 record not found")
                continue
            
            s5_record = s5_data.get(group_id)
            
            out_path = resident_out_dir / f"{group_id}.pdf"
            
            if args.dry_run:
                print(f"    [DRY] {group_id}: {len(entity_ids)} entities")
            else:
                try:
                    build_group_pdf(
                        base_dir=base_dir,
                        gen_dir=gen_dir,
                        group_id=group_id,
                        entity_ids=list(set(entity_ids)),
                        s1_record=s1_record,
                        s5_record=s5_record,
                        out_path=out_path,
                    )
                    print(f"    [OK] {group_id}: {out_path.name}")
                    total_pdfs += 1
                except Exception as e:
                    print(f"    [ERROR] {group_id}: {e}")
            
            group_count += 1
    
    print("\n" + "=" * 60)
    if args.dry_run:
        print("DRY RUN COMPLETE (no PDFs created)")
    else:
        print(f"✓ Generated {total_pdfs} PDFs")
    print("=" * 60)


if __name__ == "__main__":
    main()


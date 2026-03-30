#!/usr/bin/env python3
"""
Build a single PDF containing all S1 master tables from a run.
Only requires S1 data (no S2 needed).
"""
import argparse
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import re
import os


def register_korean_font():
    """Register Korean font for PDF generation."""
    home_dir = os.path.expanduser("~")
    korean_font_candidates = [
        (f"{home_dir}/Library/Fonts/NanumGothic.ttf", f"{home_dir}/Library/Fonts/NanumGothicExtraBold.ttf"),
        ("/Library/Fonts/NanumGothic.ttf", "/Library/Fonts/NanumGothicExtraBold.ttf"),
        (f"{home_dir}/Library/Fonts/NanumGothic.ttf", f"{home_dir}/Library/Fonts/NanumGothicBold.ttf"),
        ("/Library/Fonts/NanumGothic.ttf", "/Library/Fonts/NanumGothicBold.ttf"),
    ]
    
    korean_font_name = "KoreanFont"
    korean_font_bold_name = "KoreanFont-Bold"
    
    for normal_path, bold_path in korean_font_candidates:
        if os.path.exists(normal_path):
            try:
                pdfmetrics.registerFont(TTFont(korean_font_name, normal_path))
                if os.path.exists(bold_path) and bold_path != normal_path:
                    try:
                        pdfmetrics.registerFont(TTFont(korean_font_bold_name, bold_path))
                    except Exception:
                        pdfmetrics.registerFont(TTFont(korean_font_bold_name, normal_path))
                pdfmetrics.registerFontFamily(korean_font_name, normal=korean_font_name, bold=korean_font_bold_name)
                return korean_font_name, korean_font_bold_name
            except Exception:
                continue
    
    return "Helvetica", "Helvetica-Bold"


def parse_markdown_table(md_table: str):
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


def add_line_breaks_at_semicolons(text: str) -> str:
    """Add line breaks at semicolons (primary delimiter per prompt: "; ")."""
    if not text or not isinstance(text, str):
        return str(text) if text else ""
    # Replace "; " with "; <br/>" for ReportLab line breaks
    text = re.sub(r';\s+', '; <br/>', text)
    return text


def bold_important_terms(text: str) -> str:
    """Add bold formatting to important terms in table cells."""
    if not text or not isinstance(text, str):
        return str(text) if text else ""
    
    # Avoid processing already bolded text
    if '<b>' in text or '</b>' in text:
        return text
    
    # Pattern 1: Numbers with units or comparisons (e.g., "2cm", "< 2cm", "> 50%")
    text = re.sub(r'([<>≤≥=]?\s*\d+\.?\d*\s*(?:cm|mm|%))', r'<b>\1</b>', text)
    
    # Pattern 2: Medical abbreviations (case-insensitive)
    medical_abbrevs = [
        r'\b(CT|MRI|XR|X-ray|NM|US|PET|SPECT)\b',
        r'\b(T1|T2|T1WI|T2WI|FS|STIR|DWI|ADC)\b',
    ]
    
    for pattern in medical_abbrevs:
        text = re.sub(pattern, r'<b>\1</b>', text, flags=re.IGNORECASE)
    
    # Pattern 3: Capitalized medical terms (multi-word, skip common words)
    common_words = {'The', 'This', 'That', 'With', 'From', 'And', 'Or', 'But', 'For', 'To'}
    
    def bold_capitalized_term(match):
        term = match.group(1)
        if term in common_words:
            return term
        return f'<b>{term}</b>'
    
    text = re.sub(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', bold_capitalized_term, text)
    
    # Clean up duplicate bold tags
    text = re.sub(r'</b>\s*<b>', ' ', text)
    text = re.sub(r'<b><b>', '<b>', text)
    text = re.sub(r'</b></b>', '</b>', text)
    
    return text


def sanitize_html_for_reportlab(text: str) -> str:
    """Basic HTML sanitization for ReportLab."""
    if not text or not isinstance(text, str):
        return str(text) if text else ""
    # Keep <br/> tags (they're needed for line breaks)
    # Keep <b> and </b> tags (they're needed for bold formatting)
    # Remove other HTML tags except <br/>, <b>, </b>
    text = re.sub(r'<(?!/?b>|br/?>)[^>]+>', '', text, flags=re.IGNORECASE)
    # Normalize <br> to <br/>
    text = re.sub(r'<br\s*/?>', '<br/>', text, flags=re.IGNORECASE)
    
    # Balance bold tags (remove orphaned closing tags)
    b_open = len(re.findall(r'<b\b[^>]*>', text, re.IGNORECASE))
    b_close = len(re.findall(r'</b\b[^>]*>', text, re.IGNORECASE))
    if b_close > b_open:
        excess = b_close - b_open
        for _ in range(excess):
            text = re.sub(r'</b>', '', text, count=1, flags=re.IGNORECASE)
    
    return text.strip()


def build_table_section(story, s1_record, korean_font, korean_font_bold, page_width, page_height):
    """Build a master table section for one group."""
    group_id = s1_record.get("group_id", "")
    group_path = s1_record.get("group_path", "")
    visual_type = s1_record.get("visual_type_category", "")
    master_table_md = s1_record.get("master_table_markdown_kr", "")
    
    if not master_table_md:
        return
    
    # Group header
    header_style = ParagraphStyle(
        "GroupHeader",
        fontSize=14,
        textColor=colors.HexColor("#333333"),
        spaceAfter=8,
        fontName=korean_font_bold,
        alignment=TA_LEFT,
    )
    
    header_text = f"Group: {group_id}"
    if group_path:
        header_text += f" | {group_path}"
    if visual_type:
        header_text += f" | {visual_type}"
    
    story.append(Paragraph(header_text, header_style))
    story.append(Spacer(1, 0.2 * cm))
    
    # Parse table
    headers, rows = parse_markdown_table(master_table_md)
    if not headers or not rows:
        story.append(Paragraph("(Table data not available)", ParagraphStyle("Normal", fontName=korean_font)))
        story.append(PageBreak())
        return
    
    # Calculate column widths
    num_cols = len(headers)
    available_width = page_width - (1.5 * cm)
    col_width = available_width / num_cols
    
    # Create table data
    table_data = []
    
    # Header row
    header_style_cell = ParagraphStyle(
        "TableHeader",
        fontSize=8,
        fontName=korean_font_bold,
    )
    header_row = [Paragraph(sanitize_html_for_reportlab(h), header_style_cell) for h in headers]
    table_data.append(header_row)
    
    # Data rows
    cell_style = ParagraphStyle(
        "TableCell",
        fontSize=8,
        fontName=korean_font,
    )
    for row in rows:
        # Process each cell: add line breaks at semicolons, apply bolding, then sanitize
        processed_row = []
        for cell in row:
            cell_text = add_line_breaks_at_semicolons(cell)
            cell_text = bold_important_terms(cell_text)
            cell_text = sanitize_html_for_reportlab(cell_text)
            processed_row.append(Paragraph(cell_text, cell_style))
        table_data.append(processed_row)
    
    # Create table
    table = Table(table_data, colWidths=[col_width] * num_cols, repeatRows=1)
    
    table_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E0E0E0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), korean_font_bold),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
        ("TOPPADDING", (0, 0), (-1, 0), 3),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
        ("FONTNAME", (0, 1), (-1, -1), korean_font),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 1), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 2),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
    ])
    
    table.setStyle(table_style)
    story.append(table)
    story.append(PageBreak())


def main():
    parser = argparse.ArgumentParser(description="Build PDF with all S1 master tables")
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument("--run_tag", type=str, required=True, help="Run tag")
    parser.add_argument("--arm", type=str, required=True, help="Arm identifier")
    parser.add_argument("--out_file", type=str, help="Output PDF file path")
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    s1_path = base_dir / "2_Data" / "metadata" / "generated" / args.run_tag / f"stage1_struct__arm{args.arm}.jsonl"
    
    if not s1_path.exists():
        print(f"Error: S1 file not found: {s1_path}", file=sys.stderr)
        sys.exit(1)
    
    # Load all S1 records
    s1_records = []
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                s1_records.append(record)
            except json.JSONDecodeError:
                continue
    
    if not s1_records:
        print("Error: No S1 records found", file=sys.stderr)
        sys.exit(1)
    
    # Determine output file
    if args.out_file:
        out_path = Path(args.out_file)
    else:
        out_dir = base_dir / "6_Distributions" / "QA_Packets" / args.run_tag
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"ALL_TABLES_arm{args.arm}.pdf"
    
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
    
    korean_font, korean_font_bold = register_korean_font()
    
    story = []
    
    # Title page
    title_style = ParagraphStyle(
        "Title",
        fontSize=18,
        textColor=colors.black,
        spaceAfter=20,
        fontName=korean_font_bold,
        alignment=TA_CENTER,
    )
    story.append(Spacer(1, 5 * cm))
    story.append(Paragraph(f"S1 Master Tables - {args.run_tag}", title_style))
    story.append(Paragraph(f"Arm {args.arm}", ParagraphStyle("Subtitle", fontSize=14, fontName=korean_font, alignment=TA_CENTER)))
    story.append(Paragraph(f"Total Groups: {len(s1_records)}", ParagraphStyle("Subtitle", fontSize=12, fontName=korean_font, alignment=TA_CENTER)))
    story.append(PageBreak())
    
    # Add each group's table
    for s1_record in s1_records:
        build_table_section(story, s1_record, korean_font, korean_font_bold, page_width, page_height)
    
    doc.build(story)
    print(f"[PDF] Successfully created: {out_path}")
    print(f"[PDF] Total groups: {len(s1_records)}")


if __name__ == "__main__":
    main()


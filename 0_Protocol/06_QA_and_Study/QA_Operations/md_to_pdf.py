#!/usr/bin/env python3
"""
Convert Markdown file to PDF using ReportLab.
Based on 07_build_set_pdf.py for consistent styling and Korean font support.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
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
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
except ImportError as e:
    print(f"Error: ReportLab is not installed. Please install it with: pip install reportlab")
    sys.exit(1)


def register_korean_font():
    """Register Korean font for PDF generation (from 07_build_set_pdf.py)."""
    import os
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
    
    # Fallback
    return "Helvetica", "Helvetica-Bold"


def sanitize_html_for_reportlab(text: str) -> str:
    """Sanitize HTML text for reportlab Paragraph."""
    if not text or not isinstance(text, str):
        return str(text) if text else ""
    
    # Remove <para> tags
    text = re.sub(r'</?para[^>]*>', '', text, flags=re.IGNORECASE)
    
    # Convert <br> to <br/>
    text = re.sub(r'<br\s*/?>', '<br/>', text, flags=re.IGNORECASE)
    
    return text


def parse_markdown_formatting(text: str) -> str:
    """Parse markdown formatting and convert to HTML tags for reportlab."""
    if not text or not isinstance(text, str):
        return str(text) if text else ""
    
    # Process bold-italic first (triple asterisks)
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)
    text = re.sub(r'___(.+?)___', r'<b><i>\1</i></b>', text)
    
    # Process bold (double asterisks/underscores)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
    
    # Process italic (single asterisk/underscore, but not part of bold)
    text = re.sub(r'(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!_)_(?!_)([^_]+?)(?<!_)_(?!_)', r'<i>\1</i>', text)
    
    # Process inline code
    text = re.sub(r'`([^`]+)`', r'<font face="Courier"><b>\1</b></font>', text)
    
    return text


def parse_markdown_lines(content: str) -> List[dict]:
    """
    Parse markdown content into structured elements.
    
    Returns list of dicts with 'type' and 'content' fields.
    Types: 'h1', 'h2', 'h3', 'h4', 'p', 'list', 'hr', 'blockquote', 'code'
    """
    lines = content.split('\n')
    elements = []
    i = 0
    
    while i < len(lines):
        line = lines[i].rstrip()
        
        # Empty line
        if not line.strip():
            i += 1
            continue
        
        # Horizontal rule
        if re.match(r'^---+$', line.strip()):
            elements.append({'type': 'hr'})
            i += 1
            continue
        
        # Headings
        if line.startswith('# '):
            text = parse_markdown_formatting(line[2:].strip())
            elements.append({'type': 'h1', 'content': sanitize_html_for_reportlab(text)})
            i += 1
            continue
        elif line.startswith('## '):
            text = parse_markdown_formatting(line[3:].strip())
            elements.append({'type': 'h2', 'content': sanitize_html_for_reportlab(text)})
            i += 1
            continue
        elif line.startswith('### '):
            text = parse_markdown_formatting(line[4:].strip())
            elements.append({'type': 'h3', 'content': sanitize_html_for_reportlab(text)})
            i += 1
            continue
        elif line.startswith('#### '):
            text = parse_markdown_formatting(line[5:].strip())
            elements.append({'type': 'h4', 'content': sanitize_html_for_reportlab(text)})
            i += 1
            continue
        
        # Lists (handle nested lists by tracking indentation level)
        list_match = re.match(r'^([\s]*)([-*+]|\d+[.)])\s+', line)
        if list_match:
            list_items = []
            base_indent = len(list_match.group(1))
            
            while i < len(lines):
                current_line = lines[i].rstrip()
                if not current_line.strip():
                    # Empty line - check if next line continues the list
                    i += 1
                    if i < len(lines):
                        next_line = lines[i].rstrip()
                        next_match = re.match(r'^([\s]*)([-*+]|\d+[.)])\s+', next_line)
                        if next_match and len(next_match.group(1)) >= base_indent:
                            continue
                        else:
                            break
                    else:
                        break
                
                list_match_current = re.match(r'^([\s]*)([-*+]|\d+[.)])\s+(.*)', current_line)
                if list_match_current:
                    indent_level = len(list_match_current.group(1))
                    if indent_level < base_indent:
                        # Outdented - end of this list
                        break
                    
                    list_text = list_match_current.group(3)
                    is_nested = indent_level > base_indent
                    
                    # Parse formatting
                    text = parse_markdown_formatting(list_text.strip())
                    sanitized = sanitize_html_for_reportlab(text)
                    
                    list_items.append({
                        'text': sanitized,
                        'nested': is_nested,
                        'indent': indent_level
                    })
                    i += 1
                else:
                    # Not a list item - end of list
                    break
            
            elements.append({'type': 'list', 'items': list_items})
            continue
        
        # Blockquote
        if line.startswith('> '):
            quote_lines = []
            while i < len(lines) and lines[i].rstrip().startswith('> '):
                quote_line = lines[i].rstrip()[2:].strip()
                text = parse_markdown_formatting(quote_line)
                quote_lines.append(sanitize_html_for_reportlab(text))
                i += 1
            elements.append({'type': 'blockquote', 'items': quote_lines})
            continue
        
        # Code block
        if line.startswith('```'):
            code_lines = []
            i += 1  # Skip opening ```
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1  # Skip closing ```
            elements.append({'type': 'code', 'content': '\n'.join(code_lines)})
            continue
        
        # Regular paragraph (collect multiple lines until empty line or other element)
        para_lines = [line]
        i += 1
        while i < len(lines):
            next_line = lines[i].rstrip()
            if not next_line:
                break
            if (next_line.startswith('#') or 
                next_line.startswith('>') or 
                next_line.startswith('```') or
                re.match(r'^---+$', next_line.strip()) or
                re.match(r'^[\s]*[-*+]\s+', next_line) or
                re.match(r'^\d+[.)]\s+', next_line)):
                break
            para_lines.append(next_line)
            i += 1
        
        para_text = ' '.join(para_lines)
        text = parse_markdown_formatting(para_text.strip())
        if text:
            elements.append({'type': 'p', 'content': sanitize_html_for_reportlab(text)})
    
    return elements


def create_pdf_styles(korean_font: str, korean_font_bold: str):
    """Create PDF styles."""
    styles = getSampleStyleSheet()
    
    custom_styles = {
        "title": ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=colors.black,
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName=korean_font_bold,
        ),
        "h1": ParagraphStyle(
            "CustomH1",
            parent=styles["Heading1"],
            fontSize=16,
            textColor=colors.black,
            spaceAfter=10,
            spaceBefore=12,
            fontName=korean_font_bold,
        ),
        "h2": ParagraphStyle(
            "CustomH2",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.black,
            spaceAfter=8,
            spaceBefore=10,
            fontName=korean_font_bold,
        ),
        "h3": ParagraphStyle(
            "CustomH3",
            parent=styles["Heading3"],
            fontSize=12,
            textColor=colors.black,
            spaceAfter=6,
            spaceBefore=8,
            fontName=korean_font_bold,
        ),
        "h4": ParagraphStyle(
            "CustomH4",
            parent=styles["Heading4"],
            fontSize=11,
            textColor=colors.black,
            spaceAfter=4,
            spaceBefore=6,
            fontName=korean_font_bold,
        ),
        "body": ParagraphStyle(
            "CustomBody",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.black,
            spaceAfter=6,
            leftIndent=0,
            fontName=korean_font,
            alignment=TA_JUSTIFY,
        ),
        "list": ParagraphStyle(
            "CustomList",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.black,
            spaceAfter=4,
            leftIndent=0.5 * cm,
            bulletIndent=0.2 * cm,
            fontName=korean_font,
        ),
        "list_nested": ParagraphStyle(
            "CustomListNested",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.black,
            spaceAfter=3,
            leftIndent=1.0 * cm,
            bulletIndent=0.2 * cm,
            fontName=korean_font,
        ),
        "blockquote": ParagraphStyle(
            "CustomBlockquote",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#555555"),
            spaceAfter=6,
            leftIndent=1 * cm,
            rightIndent=1 * cm,
            fontName=korean_font,
            fontStyle='italic',
        ),
        "code": ParagraphStyle(
            "CustomCode",
            parent=styles["Code"],
            fontSize=9,
            textColor=colors.black,
            spaceAfter=6,
            leftIndent=0.5 * cm,
            fontName="Courier",
            backColor=colors.HexColor("#F5F5F5"),
        ),
    }
    
    return styles, custom_styles


def build_pdf_from_markdown(md_file: Path, pdf_file: Path):
    """Build PDF from markdown file."""
    # Read markdown content
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Register Korean font
    korean_font, korean_font_bold = register_korean_font()
    
    # Create styles
    styles, custom_styles = create_pdf_styles(korean_font, korean_font_bold)
    
    # Create PDF document
    doc = SimpleDocTemplate(
        str(pdf_file),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    
    # Parse markdown
    elements = parse_markdown_lines(content)
    
    # Build story
    story = []
    
    for elem in elements:
        if elem['type'] == 'h1':
            story.append(Paragraph(elem['content'], custom_styles['h1']))
        elif elem['type'] == 'h2':
            story.append(Paragraph(elem['content'], custom_styles['h2']))
        elif elem['type'] == 'h3':
            story.append(Paragraph(elem['content'], custom_styles['h3']))
        elif elem['type'] == 'h4':
            story.append(Paragraph(elem['content'], custom_styles['h4']))
        elif elem['type'] == 'p':
            story.append(Paragraph(elem['content'], custom_styles['body']))
        elif elem['type'] == 'list':
            for item in elem['items']:
                if isinstance(item, dict):
                    # Nested list item
                    style = custom_styles['list_nested'] if item.get('nested', False) else custom_styles['list']
                    story.append(Paragraph(f"• {item['text']}", style))
                else:
                    # Simple list item (backward compatibility)
                    story.append(Paragraph(f"• {item}", custom_styles['list']))
            story.append(Spacer(1, 0.2 * cm))
        elif elem['type'] == 'blockquote':
            for item in elem['items']:
                story.append(Paragraph(item, custom_styles['blockquote']))
            story.append(Spacer(1, 0.2 * cm))
        elif elem['type'] == 'code':
            # Code blocks need special handling
            code_text = elem['content'].replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(f'<font face="Courier">{code_text}</font>', custom_styles['code']))
        elif elem['type'] == 'hr':
            story.append(Spacer(1, 0.5 * cm))
            # Simple line using table
            hr_table = Table([['']], colWidths=[doc.width], rowHeights=[0.5])
            hr_table.setStyle(TableStyle([
                ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(hr_table)
            story.append(Spacer(1, 0.5 * cm))
    
    # Build PDF
    doc.build(story)
    print(f"✓ PDF created: {pdf_file}")


def main():
    parser = argparse.ArgumentParser(description="Convert Markdown file to PDF")
    parser.add_argument("input", type=str, help="Input markdown file")
    parser.add_argument("-o", "--output", type=str, default=None, help="Output PDF file (default: input file with .pdf extension)")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
    
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix('.pdf')
    
    try:
        build_pdf_from_markdown(input_path, output_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


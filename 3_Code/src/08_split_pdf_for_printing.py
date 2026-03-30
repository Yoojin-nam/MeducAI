"""
MeducAI Step08 (PDF Splitter) — Split combined PDF into 4 volumes for printing

P0 Requirements:
- Split one combined PDF into 4 volumes
- Each volume maximum 500 pages
- Each volume has a cover page with volume number (1-4) and specialty list
- Specialty must not be split in the middle (keep complete specialty together)
- Balance distribution across volumes
- Maintain original order within each specialty
- Each volume shows page count
- Save to printing folder with README

Design Principles:
- Read combined PDF and analyze specialty distribution
- Balance page distribution across 4 volumes
- Generate cover pages with volume info
- Use PyPDF2/pypdf for PDF manipulation
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import json
import re
import zipfile
import shutil

try:
    from pypdf import PdfReader, PdfWriter
    PYPDF_AVAILABLE = True
except ImportError:
    try:
        from PyPDF2 import PdfReader, PdfWriter
        PYPDF_AVAILABLE = True
    except ImportError:
        PYPDF_AVAILABLE = False

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as reportlab_canvas
from io import BytesIO
from reportlab.pdfgen import canvas as reportlab_canvas
from io import BytesIO
from PIL import Image as PILImage


def register_korean_font():
    """Register Korean font for cover page."""
    import os
    home_dir = os.path.expanduser("~")
    
    korean_font_candidates = [
        f"{home_dir}/Library/Fonts/NanumGothic.ttf",
        "/Library/Fonts/NanumGothic.ttf",
        f"{home_dir}/Library/Fonts/NotoSansKR-Regular.ttf",
        "/Library/Fonts/NotoSansKR-Regular.ttf",
        "/System/Library/Fonts/Supplemental/AppleSDGothicNeo-Regular.otf",
    ]
    
    korean_font_name = "KoreanFont"
    korean_font_bold_name = "KoreanFont-Bold"
    
    for font_path in korean_font_candidates:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(korean_font_name, font_path))
                pdfmetrics.registerFont(TTFont(korean_font_bold_name, font_path))
                pdfmetrics.registerFontFamily(
                    korean_font_name,
                    normal=korean_font_name,
                    bold=korean_font_bold_name
                )
                return korean_font_name, korean_font_bold_name
            except Exception:
                continue
    
    return "Helvetica", "Helvetica-Bold"


def load_group_mapping_from_pdf_metadata(
    base_dir: Path,
    run_tag: str,
    arm: str,
    s1_arm: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Load group_id -> specialty mapping from S1 structure.
    
    Returns:
        Dict mapping group_id -> {specialty, anatomy, modality_or_type, category, group_path}
    """
    from pathlib import Path
    import json
    
    gen_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    s1_arm_actual = (s1_arm or arm).strip().upper() if s1_arm else arm
    s1_path = gen_dir / f"stage1_struct__arm{s1_arm_actual}.jsonl"
    
    if not s1_path.exists():
        return {}
    
    mapping = {}
    
    def clean_text(text: str) -> str:
        if not text:
            return ""
        text = str(text).strip()
        if text.lower() in ("nan", "none", "null", ""):
            return ""
        text = text.replace("_rad", "").replace("_RAD", "")
        text = text.replace("_", " ")
        return text.strip()
    
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                group_id = record.get("group_id", "").strip()
                if not group_id:
                    continue
                
                group_path = record.get("group_path", "")
                specialty = ""
                anatomy = ""
                modality_or_type = ""
                category = None
                
                if group_path:
                    parts = [p.strip() for p in group_path.split(">")]
                    specialty = clean_text(parts[0]) if len(parts) > 0 else ""
                    anatomy = clean_text(parts[1]) if len(parts) > 1 else ""
                    modality_or_type = clean_text(parts[2]) if len(parts) > 2 else ""
                    category_raw = parts[3] if len(parts) > 3 else None
                    category = clean_text(category_raw) if category_raw else None
                    if not category or category.lower() in ("nan", "none", "null"):
                        category = None
                else:
                    group_key = record.get("group_key", "")
                    if group_key:
                        parts = group_key.split("__")
                        specialty = clean_text(parts[0]) if len(parts) > 0 else ""
                        anatomy = clean_text(parts[1]) if len(parts) > 1 else ""
                
                mapping[group_id] = {
                    "specialty": specialty,
                    "anatomy": anatomy,
                    "modality_or_type": modality_or_type,
                    "category": category,
                    "group_path": group_path,
                }
            except json.JSONDecodeError:
                continue
    
    return mapping


def detect_specialty_boundaries_in_pdf(
    pdf_path: Path,
    group_mapping: Dict[str, Dict[str, Any]],
) -> List[Tuple[int, int, str]]:
    """
    Detect specialty boundaries in PDF by analyzing text content.
    Looks for "specialty > anatomy > ... | " pattern in headers.
    
    Returns:
        List of (start_page, end_page, specialty) tuples for each specialty section
    """
    if not PYPDF_AVAILABLE:
        raise RuntimeError("PyPDF2 or pypdf is required for PDF splitting")
    
    reader = PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    
    # Build specialty patterns from group mapping
    specialty_patterns = {}
    specialty_list = set()
    for group_id, info in group_mapping.items():
        specialty = info.get("specialty", "")
        if specialty:
            specialty_list.add(specialty)
            # Create multiple patterns for matching
            specialty_clean = specialty.lower().strip()
            specialty_patterns[specialty_clean] = specialty
            # Also add variations (remove spaces, etc.)
            specialty_patterns[specialty_clean.replace(" ", "")] = specialty
            specialty_patterns[specialty_clean.replace(" ", "_")] = specialty
    
    # If no patterns, create fallback patterns based on common specialty names
    if not specialty_patterns:
        common_specialties = [
            "abdominal radiology", "breast rad", "cardiovascular rad",
            "gu radiology", "interventional radiology", "musculoskeletal radiology",
            "neuro hn imaging", "nuclear med", "pediatric radiology",
            "physics qc informatics", "thoracic radiology",
        ]
        for spec in common_specialties:
            specialty_patterns[spec.lower()] = spec
            specialty_patterns[spec.lower().replace(" ", "")] = spec
    
    # Track specialty sections
    specialty_sections = []
    current_specialty = None
    specialty_start = 0
    
    # Sample pages to detect specialty changes
    # Check first 3 pages of each potential section, and every 10th page
    pages_to_check = set()
    for i in range(0, total_pages, 10):
        pages_to_check.add(i)
        if i + 1 < total_pages:
            pages_to_check.add(i + 1)
        if i + 2 < total_pages:
            pages_to_check.add(i + 2)
    
    # Also check first and last page of each section
    for i in range(total_pages):
        pages_to_check.add(i)
    
    pages_to_check = sorted(pages_to_check)
    
    for page_idx in pages_to_check:
        if page_idx >= total_pages:
            continue
        
        try:
            page = reader.pages[page_idx]
            text = page.extract_text()
            
            if not text:
                continue
            
            text_lower = text.lower()
            found_specialty = None
            
            # Look for "specialty > " pattern in header (usually in first 500 chars)
            header_text = text[:1000].lower() if len(text) > 1000 else text_lower
            
            # Check for "specialty > anatomy > ... | " pattern
            # This is the pattern used in PDF headers
            for pattern, specialty_name in specialty_patterns.items():
                # Look for pattern in header area
                if pattern in header_text:
                    # Verify it's in a header context (before "|")
                    if "|" in header_text:
                        parts = header_text.split("|")
                        if pattern in parts[0]:  # Before the "|"
                            found_specialty = specialty_name
                            break
                    else:
                        # No "|" separator, check if pattern appears early in page
                        pattern_pos = header_text.find(pattern)
                        if pattern_pos < 500:  # In first 500 chars
                            found_specialty = specialty_name
                            break
            
            # If we found a different specialty, mark boundary
            if found_specialty and found_specialty != current_specialty:
                # New specialty detected
                if current_specialty is not None:
                    # Save previous specialty section
                    specialty_sections.append((specialty_start, page_idx - 1, current_specialty))
                
                current_specialty = found_specialty
                specialty_start = page_idx
        except Exception:
            # Skip pages that can't be read
            continue
    
    # Add last specialty section
    if current_specialty is not None:
        specialty_sections.append((specialty_start, total_pages - 1, current_specialty))
    
    # Merge adjacent sections with same specialty
    merged_sections = []
    for start, end, specialty in specialty_sections:
        if merged_sections and merged_sections[-1][2] == specialty:
            # Merge with previous
            prev_start, prev_end, _ = merged_sections[-1]
            merged_sections[-1] = (prev_start, end, specialty)
        else:
            merged_sections.append((start, end, specialty))
    
    # If detection failed, create uniform split based on specialty_list
    if not merged_sections:
        # Fallback: split evenly or use specialty_list
        if specialty_list:
            pages_per_specialty = total_pages // max(len(specialty_list), 1)
            sorted_specialties = sorted(specialty_list)
            for i, specialty in enumerate(sorted_specialties):
                start = i * pages_per_specialty
                end = min((i + 1) * pages_per_specialty - 1, total_pages - 1)
                if i == len(sorted_specialties) - 1:
                    end = total_pages - 1
                merged_sections.append((start, end, specialty))
        else:
            # Last resort: treat entire PDF as one section
            merged_sections = [(0, total_pages - 1, "All Content")]
    
    # Ensure no gaps or overlaps
    result = []
    for i, (start, end, specialty) in enumerate(merged_sections):
        # Ensure continuity
        if i > 0:
            prev_end = result[-1][1]
            if start > prev_end + 1:
                # Gap detected, adjust start
                start = prev_end + 1
        result.append((start, end, specialty))
    
    # Ensure last section covers all pages
    if result:
        last_start, last_end, last_specialty = result[-1]
        if last_end < total_pages - 1:
            result[-1] = (last_start, total_pages - 1, last_specialty)
    
    return result


def parse_group_ids_from_pdf_content(
    pdf_path: Path,
) -> List[str]:
    """
    Try to extract group IDs from PDF content (if present in headers).
    This is a fallback method if group_mapping is not available.
    """
    if not PYPDF_AVAILABLE:
        return []
    
    reader = PdfReader(str(pdf_path))
    group_ids = []
    
    # Look for patterns like "SET_G0123_armA" or "G0123" in first few pages
    for page_idx in range(min(10, len(reader.pages))):
        try:
            page = reader.pages[page_idx]
            text = page.extract_text()
            # Look for group ID pattern (G followed by digits)
            matches = re.findall(r'\bG\d+\b', text)
            for match in matches:
                if match not in group_ids:
                    group_ids.append(match)
        except Exception:
            continue
    
    return group_ids


def balance_distribution(
    specialty_ranges: List[Tuple[int, int, str]],
    max_pages_per_volume: int = 500,
    num_volumes: int = 4,
) -> List[Tuple[int, int, List[str], int]]:
    """
    Balance specialty ranges across volumes.
    Ensures specialties are not split and pages are balanced.
    
    Args:
        specialty_ranges: List of (start_page, end_page, specialty) tuples
        max_pages_per_volume: Maximum pages per volume
        num_volumes: Number of volumes to create
    
    Returns:
        List of (start_page, end_page, specialty_list, page_count) for each volume
    """
    if not specialty_ranges:
        return []
    
    # Calculate total pages
    total_pages = max(end for _, end, _ in specialty_ranges) + 1
    target_pages_per_volume = total_pages / num_volumes
    
    # Strategy: Greedy bin packing with balance awareness
    # Keep specialties together, balance page counts
    
    volumes = []
    remaining_ranges = specialty_ranges.copy()
    
    for vol_idx in range(num_volumes):
        if not remaining_ranges:
            break
        
        vol_start = None
        vol_end = None
        vol_specialties = []
        vol_pages = 0
        
        # Calculate target for this volume
        # Try to balance, but don't exceed max_pages_per_volume
        remaining_volumes = num_volumes - vol_idx
        if remaining_volumes > 0:
            target_pages = min(
                max_pages_per_volume,
                total_pages - sum(v[3] for v in volumes)
            )
        else:
            target_pages = total_pages - sum(v[3] for v in volumes)
        
        # Add specialties until we reach target or exceed max
        ranges_to_add = []
        
        for start, end, specialty in remaining_ranges:
            section_pages = end - start + 1
            
            # If this single section exceeds max, we must add it anyway (can't split)
            if section_pages > max_pages_per_volume:
                if vol_pages == 0:
                    # This is the first section, add it
                    ranges_to_add.append((start, end, specialty))
                    vol_start = start
                    vol_end = end
                    vol_specialties.append(specialty)
                    vol_pages = section_pages
                    break
                else:
                    # Can't add to current volume, will go to next
                    break
            
            # Check if adding this section would exceed max
            if vol_pages + section_pages > max_pages_per_volume:
                # Stop adding to this volume
                break
            
            # Check if we're close enough to target (allow some flexibility)
            # If we're already over 80% of target and adding would exceed it significantly, stop
            if vol_pages >= target_pages * 0.8 and vol_pages + section_pages > target_pages * 1.2:
                # Check if remaining volumes can handle the rest
                remaining_pages = sum(e - s + 1 for s, e, _ in remaining_ranges if (s, e, _) not in ranges_to_add)
                remaining_vols = remaining_volumes - 1
                if remaining_vols > 0 and remaining_pages / remaining_vols <= max_pages_per_volume:
                    # Safe to stop here
                    break
            
            # Add this section
            ranges_to_add.append((start, end, specialty))
            if vol_start is None:
                vol_start = start
            vol_end = end
            vol_specialties.append(specialty)
            vol_pages += section_pages
        
        # Remove added ranges from remaining
        for r in ranges_to_add:
            if r in remaining_ranges:
                remaining_ranges.remove(r)
        
        # Create volume
        if vol_start is not None:
            volumes.append((
                vol_start,
                vol_end,
                list(set(vol_specialties)),
                vol_pages
            ))
    
    # If we have remaining ranges, add them to the last volume
    if remaining_ranges:
        last_vol = volumes[-1] if volumes else None
        for start, end, specialty in remaining_ranges:
            if last_vol:
                # Extend last volume
                volumes[-1] = (
                    min(last_vol[0], start),
                    max(last_vol[1], end),
                    list(set(last_vol[2] + [specialty])),
                    max(last_vol[1], end) - min(last_vol[0], start) + 1
                )
                last_vol = volumes[-1]
            else:
                # Create new volume
                volumes.append((
                    start,
                    end,
                    [specialty],
                    end - start + 1
                ))
    
    # Ensure we have exactly num_volumes (merge or split if needed)
    if len(volumes) > num_volumes:
        # Merge last volumes
        while len(volumes) > num_volumes:
            last1 = volumes.pop()
            last2 = volumes.pop()
            merged = (
                min(last1[0], last2[0]),
                max(last1[1], last2[1]),
                list(set(last1[2] + last2[2])),
                max(last1[1], last2[1]) - min(last1[0], last2[0]) + 1
            )
            volumes.append(merged)
    
    # Ensure last volume covers all remaining pages
    if volumes:
        last_vol = volumes[-1]
        total_covered = last_vol[1] + 1
        if total_covered < total_pages:
            # Extend last volume
            volumes[-1] = (
                last_vol[0],
                total_pages - 1,
                last_vol[2],
                total_pages - last_vol[0]
            )
    
    return volumes


def create_cover_page(
    volume_num: int,
    specialty_list: List[str],
    page_count: int,
    output_path: Path,
    korean_font: str,
    korean_font_bold: str,
) -> Path:
    """
    Create a cover page PDF matching the main cover style from build_distribution_pdf.py.
    
    Style:
    - Uses cover_base.jpg image (same as main cover)
    - MeducAI - Volume ** title at top center (white, 52pt)
    - Specialty list overlay at bottom (larger font, line breaks, same style as specialty covers)
    """
    page_size = landscape(A4)
    page_width = page_size[0]
    page_height = page_size[1]
    
    # Color palette matching build_distribution_pdf.py
    COLOR_WHITE = colors.HexColor("#FFFFFF")
    
    # Find cover image path (relative to this script or tools/assets)
    this_dir = Path(__file__).resolve().parent  # 3_Code/src/
    # Try 3_Code/src/tools/assets/cover_base.jpg first (same level as src/)
    cover_image_path = this_dir / "tools" / "assets" / "cover_base.jpg"
    if not cover_image_path.exists():
        # Try alternative: 3_Code/src/../tools/assets/ (if tools is at src level)
        cover_image_path = this_dir.parent / "tools" / "assets" / "cover_base.jpg"
    if not cover_image_path.exists():
        # Last try: find from base_dir
        # Look for 3_Code directory by going up from this script
        cur = this_dir
        for _ in range(5):
            test_path = cur / "tools" / "assets" / "cover_base.jpg"
            if test_path.exists():
                cover_image_path = test_path
                break
            if cur.parent == cur:
                break
            cur = cur.parent
    
    # Create PDF with canvas for custom drawing
    buffer = BytesIO()
    c = reportlab_canvas.Canvas(buffer, pagesize=page_size)
    
    # Draw cover image (matching main cover style)
    if cover_image_path.exists():
        try:
            from PIL import Image as PILImage
            from reportlab.lib.utils import ImageReader
            
            # Load image and center-crop to page size (no resize to preserve quality)
            with PILImage.open(cover_image_path) as img:
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
                img_reader = ImageReader(img_buffer)
                c.drawImage(
                    img_reader,
                    0, 0,
                    width=page_width,
                    height=page_height,
                    preserveAspectRatio=True,
                    anchor='c',
                )
        except Exception as e:
            print(f"  Warning: Failed to load cover image: {e}")
            # Fallback to gradient background
            _draw_gradient_background(c, page_width, page_height)
    else:
        # Fallback to gradient background if image not found
        print(f"  Warning: Cover image not found at {cover_image_path}, using gradient background")
        _draw_gradient_background(c, page_width, page_height)
    
    # Draw MeducAI - Volume ** title at top
    # EXACT same positioning as _draw_meducai_title in build_distribution_pdf.py
    title_y = page_height * 0.78  # EXACT same as specialty cover
    title_bg_height = 80  # EXACT same as specialty cover
    
    # Draw semi-transparent background behind title (EXACT same as specialty cover)
    c.saveState()
    c.setFillColor(colors.Color(0.1, 0.2, 0.35, alpha=0.5))
    c.rect(
        0, title_y - 20,
        page_width, title_bg_height,
        fill=1, stroke=0
    )
    c.restoreState()
    
    # Draw "MeducAI - Volume **" title with auto-sized font
    title_text = f"MeducAI - Volume {volume_num}"
    
    # Calculate font size to fit within the box
    # Use much smaller font to ensure text doesn't get cut off
    max_font_size = 28  # Smaller than specialty cover's 52pt to fit longer text
    min_font_size = 14
    title_font_size = max_font_size
    
    # Test font size to fit width (be conservative)
    for test_size in range(max_font_size, min_font_size - 1, -1):
        c.setFont(korean_font_bold, test_size)
        text_width = c.stringWidth(title_text, korean_font_bold, test_size)
        # Use 80% of page width as safe margin
        if text_width <= page_width * 0.8:
            title_font_size = test_size
            break
    
    # Draw title text (EXACT same vertical position as specialty cover)
    c.setFillColor(COLOR_WHITE)
    c.setFont(korean_font_bold, title_font_size)
    c.drawCentredString(page_width / 2, title_y, title_text)
    
    # Draw specialty list overlay at bottom
    # EXACT same positioning as _draw_specialty_overlay in build_distribution_pdf.py
    if specialty_list:
        # Convert specialties to uppercase and sort
        specialty_text_list = sorted([s.upper() for s in specialty_list if s and s.strip()])
        
        # Overlay position: EXACT same as specialty cover
        overlay_height = page_height / 5  # Compact height for clean look
        overlay_y = page_height / 8 - overlay_height / 2  # Lower position
        
        # Draw semi-transparent dark background (EXACT same as specialty cover)
        c.saveState()
        c.setFillColor(colors.Color(0.1, 0.15, 0.25, alpha=0.65))
        c.rect(
            0, overlay_y,
            page_width, overlay_height,
            fill=1, stroke=0
        )
        c.restoreState()
        
        # Draw decorative lines above and below the overlay area (EXACT same as specialty cover)
        line_y_top = overlay_y + overlay_height
        line_y_bottom = overlay_y
        
        c.setStrokeColor(colors.Color(1, 1, 1, alpha=0.3))
        c.setLineWidth(1)
        c.line(page_width * 0.15, line_y_top, page_width * 0.85, line_y_top)
        c.line(page_width * 0.15, line_y_bottom, page_width * 0.85, line_y_bottom)
        
        # Draw specialty text (white)
        c.setFillColor(COLOR_WHITE)
        
        # Calculate font size based on number of specialties and available height
        # Multiple specialties need smaller font to fit
        num_specialties = len(specialty_text_list)
        
        # Calculate line height that fits within the box
        max_font_size = 28  # Smaller starting size
        min_font_size = 12
        
        # Find optimal font size that fits both width and height constraints
        font_size = max_font_size
        for test_size in range(max_font_size, min_font_size - 1, -1):
            c.setFont(korean_font, test_size)
            
            # Check if all specialties fit within width
            all_fit = True
            for specialty in specialty_text_list:
                text_width = c.stringWidth(specialty, korean_font, test_size)
                if text_width > page_width * 0.8:  # 80% width for safety
                    all_fit = False
                    break
            
            # Check if all specialties fit within height
            line_height = test_size * 1.3  # Conservative line spacing
            total_height = num_specialties * line_height
            
            if all_fit and total_height <= overlay_height * 0.8:  # 80% height for safety
                font_size = test_size
                break
        
        # Calculate line height based on final font size
        line_height = font_size * 1.3
        
        # Draw each specialty on a separate line, centered vertically
        total_text_height = num_specialties * line_height
        start_y = overlay_y + (overlay_height / 2) + (total_text_height / 2) - (line_height / 2)
        
        c.setFont(korean_font, font_size)
        for i, specialty_line in enumerate(specialty_text_list):
            text_y = start_y - (i * line_height)
            c.drawCentredString(page_width / 2, text_y, specialty_line)
    
    # Save canvas
    c.save()
    buffer.seek(0)
    
    # Write to file
    with open(output_path, 'wb') as f:
        f.write(buffer.getvalue())
    
    return output_path


def _draw_gradient_background(
    canvas_obj: reportlab_canvas.Canvas,
    page_width: float,
    page_height: float,
) -> None:
    """Draw gradient background as fallback if cover image is not available."""
    # Draw gradient background (Deep Navy -> Ocean Blue)
    num_steps = 100
    step_height = page_height / num_steps
    
    for i in range(num_steps):
        # Interpolate from top (lighter Ocean Blue) to bottom (darker Deep Navy)
        ratio = i / (num_steps - 1)
        # Top: Ocean Blue, Bottom: Deep Navy
        r = 0x4A + (0x1B - 0x4A) * ratio
        g = 0x90 + (0x3A - 0x90) * ratio
        b = 0xD9 + (0x5F - 0xD9) * ratio
        
        color = colors.Color(r/255, g/255, b/255)
        canvas_obj.setFillColor(color)
        y = page_height - (i + 1) * step_height
        canvas_obj.rect(0, y, page_width, step_height + 1, fill=1, stroke=0)


def split_pdf_for_printing(
    pdf_path: Path,
    output_dir: Path,
    volumes: List[Tuple[int, int, List[str], int]],
) -> List[Path]:
    """
    Split PDF into volumes for printing.
    
    Args:
        pdf_path: Path to input PDF
        output_dir: Output directory
        volumes: List of (start_page, end_page, specialty_list, page_count) for each volume
    
    Returns:
        List of output PDF paths
    """
    if not PYPDF_AVAILABLE:
        raise RuntimeError("PyPDF2 or pypdf is required. Install with: pip install pypdf")
    
    if not pdf_path.exists():
        raise RuntimeError(f"PDF file not found: {pdf_path}")
    
    print(f"[PDF Splitter] Creating {len(volumes)} volumes:")
    for i, (start, end, specialties, page_count) in enumerate(volumes):
        print(f"  Volume {i+1}: pages {start+1}-{end+1} ({page_count} pages), specialties: {', '.join(specialties)}")
    
    # Register Korean font
    korean_font, korean_font_bold = register_korean_font()
    
    # Read input PDF
    reader = PdfReader(str(pdf_path))
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_paths = []
    
    # Create each volume
    for vol_idx, (start_page, end_page, specialties, page_count) in enumerate(volumes):
        vol_num = vol_idx + 1
        
        # Create cover page
        cover_path = output_dir / f"Cover_Volume_{vol_num}.pdf"
        create_cover_page(vol_num, specialties, page_count, cover_path, korean_font, korean_font_bold)
        
        # Create volume PDF with cover + content
        writer = PdfWriter()
        
        # Add cover page
        cover_reader = PdfReader(str(cover_path))
        writer.add_page(cover_reader.pages[0])
        
        # Add content pages
        for page_idx in range(start_page, end_page + 1):
            if page_idx < len(reader.pages):
                writer.add_page(reader.pages[page_idx])
        
        # Save volume
        output_path = output_dir / f"MeducAI_Volume_{vol_num}.pdf"
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        
        output_paths.append(output_path)
        print(f"[PDF Splitter] Created: {output_path.name} ({len(writer.pages)} pages including cover)")
    
    return output_paths


def create_readme(
    output_dir: Path,
    volumes: List[Tuple[int, int, List[str], int]],
    pdf_path: Path,
) -> Tuple[Path, Path]:
    """Create README files (both .md and .txt) explaining the printing setup."""
    readme_md_path = output_dir / "README.md"
    readme_txt_path = output_dir / "README.txt"
    
    # Calculate order page counts (round up odd numbers to even)
    order_info = []
    total_order_pages = 0
    for vol_idx, (start_page, end_page, specialties, page_count) in enumerate(volumes):
        vol_num = vol_idx + 1
        # For ordering: use actual page count, round up odd to even
        order_page_count = page_count + 1  # Include cover
        if order_page_count % 2 == 1:
            order_page_count += 1  # Round up odd to even
        order_info.append((vol_num, page_count + 1, order_page_count, specialties))
        total_order_pages += order_page_count
    
    content = f"""# MeducAI 인쇄용 PDF 분권 안내

이 폴더에는 인쇄 주문을 위한 PDF 파일들이 분권되어 있습니다.

## 파일 구성

"""
    
    for vol_num, actual_pages, order_pages, specialties in order_info:
        content += f"""### 제 {vol_num}권
- 파일명: `MeducAI_Volume_{vol_num}.pdf`
- 실제 페이지 수: {actual_pages}페이지 (표지 포함)
- 내용 페이지: {actual_pages - 1}페이지
- **주문 시 입력할 페이지 수: {order_pages}페이지 ({order_pages}장)** (홀수일 경우 짝수로 올림)
- 포함 전문의:
"""
        for specialty in sorted(specialties):
            if specialty and specialty.strip():
                content += f"  - {specialty}\n"
        content += "\n"
    
    content += f"""## 인쇄 주문 방법

### 주문 사이트
다음 사이트에서 인쇄 주문이 가능합니다:
- https://smartstore.naver.com/printing79/products/2789751045

### 주문 시 입력 방법

#### 1. 출력사양 선택
- **흑백** 또는 **컬러** 중 선택
- 컬러 선택 시 이미지량에 따라 금액이 상승될 수 있습니다.

#### 2. 용지사이즈
- **A4** 선택

#### 3. 표지관련선택
- 필요에 따라 선택 (기본 구성: 앞뒤PP(PVC), 앞표지(250g 용지), 뒷표지(250g 용지))

#### 4. 제본 선택 (스프링 제본)
- **④ 제본사양**에서 **스프링 제본** 선택
- **짧은 쪽으로 제본 요청** (기본은 긴 쪽 제본이므로 별도 요청 필요)
- **총 제본권수: 4권 (스프링 4개)** 입력
- 각 권당 최대 500페이지까지 가능 (양면 기준)

#### 5. 총 페이지 수 입력
**여러 권을 한 번에 주문하는 경우:**
- **총 페이지 수: {total_order_pages}페이지 ({total_order_pages}장)** (4권 합계)
- 각 권의 주문 페이지 수를 합산:
"""
    
    for vol_num, actual_pages, order_pages, specialties in order_info:
        content += f"  - 제 {vol_num}권: {order_pages}페이지 ({order_pages}장)\n"
    
    content += f"  - **합계: {total_order_pages}페이지 ({total_order_pages}장)**\n\n"
    
    content += """**주의사항:**
- 페이지 수는 양면/단면 관계없이 **PDF의 페이지 수(1면)가 기준**입니다.
- **페이지 = 장** (1페이지 = 1장)
- 홀수 페이지일 경우 **짝수로 올려서 입력**해야 합니다.
- 장수(절반)로 선택하지 마시고 **반드시 페이지로 선택**해주세요.
- 예: 457페이지(457장) → 458페이지(458장)로 입력, 483페이지(483장) → 484페이지(484장)로 입력

### 각 권별 주문 페이지 수 요약

"""
    
    for vol_num, actual_pages, order_pages, specialties in order_info:
        content += f"- 제 {vol_num}권: **{order_pages}페이지 ({order_pages}장)** (실제 {actual_pages}페이지, 홀수일 경우 짝수로 올림)\n"
    
    content += f"\n**4권 합계 주문 시 총 페이지 수: {total_order_pages}페이지 ({total_order_pages}장)**\n"
    content += f"**스프링 제본: 4개 (권당 1개씩 총 4개)**\n\n"
    
    content += f"""## 메일 작성 안내

주문 시 다음 내용을 메일에 포함하여 보내주세요:

---

**메일 제목:** MeducAI 인쇄 주문 요청 (4권 분권)

**메일 본문:**

안녕하세요.

MeducAI 학습 자료 인쇄 주문을 요청드립니다.

**주문 내용:**
- 파일: MeducAI_Volume_1.pdf ~ MeducAI_Volume_4.pdf (총 4권)
- 출력사양: [흑백/컬러 선택]
- 용지사이즈: A4
- 제본: 스프링 제본 **4개** (권당 1개씩 총 4개)
- **제본 방향: 짧은 쪽으로 제본** 요청드립니다. (기본은 긴 쪽 제본이므로 별도 요청)

**각 권별 페이지 수:**
"""
    
    for vol_num, actual_pages, order_pages, specialties in order_info:
        specialty_list = ", ".join(sorted([s for s in specialties if s and s.strip()]))
        content += f"- 제 {vol_num}권: {order_pages}페이지 ({order_pages}장) (포함 전문의: {specialty_list})\n"
    
    content += f"- **총 페이지 수: {total_order_pages}페이지 ({total_order_pages}장)** (4권 합계)\n"
    content += f"- **스프링 제본: 4개** (권당 1개씩 총 4개)\n\n"
    
    content += """**요청사항:**
1. 스프링 제본 시 **짧은 쪽으로 제본** 부탁드립니다.
2. 양면 인쇄로 진행 부탁드립니다.
3. 파일은 첨부하거나 별도로 전달하겠습니다.

감사합니다.

---

## 추가 주문 안내

### 병합출력 (기본 설정)
- 기본적으로 병합출력이 적용됩니다.
- 세부내용은 사이트의 안내를 확인해주세요.

### 파일 용량
- 파일 용량이 큰 경우 용량을 축소해서 보내주시기 바랍니다.
- 용량이 너무 크면 출력 속도가 느려 취소될 수 있습니다.

### 제본 구성 (스프링 제본 기본 구성)
- 앞뒤 PP(PVC)
- 앞표지(250g 용지)
- 내지(속지) - 본문
- 뒷표지(250g 용지)

### 제본 방식
- 양면 인쇄 시: 최대 500페이지까지 1권 가능
- 180페이지 전후: 코일링(화이트, 투명)
- 그 이하: 와이어(화이트)

"""
    # Calculate original page count
    original_page_count = max(end for _, end, _, _ in volumes) + 1
    import datetime
    split_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    content += f"""## 원본 파일 정보
- 원본 파일: `{pdf_path.name}`
- 실제 총 페이지 수: {original_page_count}페이지 (표지 제외)
- 분권 일시: {split_time}

## 주의사항
- 각 권의 표지 페이지가 포함되어 있습니다.
- 전문의별로 내용이 중간에 잘리지 않도록 구성되었습니다.
- 주문 시 페이지 수는 홀수일 경우 짝수로 올려서 입력해야 합니다.
- 페이지 수는 양면/단면 관계없이 PDF의 페이지 수(1면)를 기준으로 합니다.
"""
    
    # Write Markdown version
    with open(readme_md_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[PDF Splitter] Created README: {readme_md_path}")
    
    # Convert markdown to plain text (remove markdown formatting)
    txt_content = content
    # Remove markdown headers (# -> )
    import re
    txt_content = re.sub(r'^#+\s+(.+)$', r'\1', txt_content, flags=re.MULTILINE)
    # Remove bold markers (**text** -> text)
    txt_content = re.sub(r'\*\*([^*]+)\*\*', r'\1', txt_content)
    # Remove code markers (`text` -> text)
    txt_content = re.sub(r'`([^`]+)`', r'\1', txt_content)
    # Remove markdown list markers (keep indent)
    # Keep - as list marker but remove extra formatting
    
    # Write plain text version
    with open(readme_txt_path, 'w', encoding='utf-8') as f:
        f.write(txt_content)
    
    print(f"[PDF Splitter] Created README: {readme_txt_path}")
    return readme_md_path, readme_txt_path


def create_zip_file(
    output_dir: Path,
    pdf_paths: List[Path],
) -> Path:
    """Create ZIP file containing all PDF volumes."""
    zip_path = output_dir / "MeducAI_Volumes_All.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for pdf_path in pdf_paths:
            if pdf_path.exists():
                # Add PDF to zip with just filename (not full path)
                zipf.write(pdf_path, pdf_path.name)
                print(f"[PDF Splitter] Added to ZIP: {pdf_path.name}")
    
    print(f"[PDF Splitter] Created ZIP file: {zip_path.name} ({zip_path.stat().st_size / 1024 / 1024:.2f} MB)")
    return zip_path


def main():
    parser = argparse.ArgumentParser(
        description="Split combined PDF into 4 volumes for printing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (requires PDF analysis):
  python 3_Code/src/08_split_pdf_for_printing.py \\
    --pdf_path 6_Distributions/MeducAI_Final_Share/PDF/MeducAI_FINAL_ALL.pdf \\
    --output_dir 6_Distributions/MeducAI_Final_Share/PDF/print_ready

  # With metadata for better specialty detection:
  python 3_Code/src/08_split_pdf_for_printing.py \\
    --pdf_path 6_Distributions/MeducAI_Final_Share/PDF/MeducAI_FINAL_ALL.pdf \\
    --output_dir 6_Distributions/MeducAI_Final_Share/PDF/print_ready \\
    --base_dir . \\
    --run_tag FINAL_RUN_V1_20250101_120000 \\
    --arm A

Output:
  - 6_Distributions/MeducAI_Final_Share/PDF/print_ready/
    - MeducAI_Volume_1.pdf
    - MeducAI_Volume_2.pdf
    - MeducAI_Volume_3.pdf
    - MeducAI_Volume_4.pdf
    - MeducAI_Volumes_All.zip (ZIP file containing all PDFs)
    - README.md
        """,
    )
    
    parser.add_argument("--pdf_path", type=str, required=True, help="Path to combined PDF file")
    parser.add_argument("--output_dir", type=str, required=True, help="Output directory for split PDFs")
    parser.add_argument("--base_dir", type=str, default=None, help="Project base directory (for metadata)")
    parser.add_argument("--run_tag", type=str, default=None, help="Run tag (for metadata)")
    parser.add_argument("--arm", type=str, default=None, help="Arm identifier (for metadata)")
    parser.add_argument("--s1_arm", type=str, default=None, help="S1 arm (for metadata)")
    parser.add_argument("--max_pages_per_volume", type=int, default=500, help="Maximum pages per volume (default: 500)")
    parser.add_argument("--num_volumes", type=int, default=4, help="Number of volumes (default: 4)")
    
    args = parser.parse_args()
    
    if not PYPDF_AVAILABLE:
        print("ERROR: PyPDF2 or pypdf is required for PDF splitting.", file=sys.stderr)
        print("Install with: pip install pypdf", file=sys.stderr)
        sys.exit(1)
    
    pdf_path = Path(args.pdf_path).resolve()
    output_dir = Path(args.output_dir).resolve()
    base_dir = Path(args.base_dir).resolve() if args.base_dir else None
    
    if not pdf_path.exists():
        print(f"ERROR: PDF file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"[PDF Splitter] Starting PDF split operation")
    print(f"  Input: {pdf_path}")
    print(f"  Output: {output_dir}")
    print(f"  Max pages per volume: {args.max_pages_per_volume}")
    print(f"  Number of volumes: {args.num_volumes}")
    
    try:
        # Detect specialty boundaries
        group_mapping = {}
        if base_dir and args.run_tag and args.arm:
            try:
                group_mapping = load_group_mapping_from_pdf_metadata(base_dir, args.run_tag, args.arm, args.s1_arm)
                print(f"[PDF Splitter] Loaded {len(group_mapping)} group mappings")
            except Exception as e:
                print(f"[PDF Splitter] Warning: Could not load group mapping: {e}")
        
        specialty_ranges = detect_specialty_boundaries_in_pdf(pdf_path, group_mapping)
        
        if not specialty_ranges:
            # Fallback: uniform split
            reader = PdfReader(str(pdf_path))
            total_pages = len(reader.pages)
            pages_per_volume = total_pages // args.num_volumes
            specialty_ranges = []
            for i in range(args.num_volumes):
                start = i * pages_per_volume
                end = min((i + 1) * pages_per_volume - 1, total_pages - 1)
                if i == args.num_volumes - 1:
                    end = total_pages - 1
                specialty_ranges.append((start, end, f"Volume {i+1}"))
        
        # Balance distribution
        volumes = balance_distribution(specialty_ranges, args.max_pages_per_volume, args.num_volumes)
        
        # Create volumes
        output_paths = split_pdf_for_printing(
            pdf_path,
            output_dir,
            volumes,
        )
        
        # Create README
        readme_md, readme_txt = create_readme(output_dir, volumes, pdf_path)
        
        # Create ZIP file with all PDFs
        zip_path = create_zip_file(output_dir, output_paths)
        
        # Clean up temporary cover files (they're already merged into volumes)
        for vol_num in range(1, args.num_volumes + 1):
            cover_path = output_dir / f"Cover_Volume_{vol_num}.pdf"
            if cover_path.exists():
                cover_path.unlink()
        
        print(f"\n[PDF Splitter] ✓ Successfully created {len(output_paths)} volumes")
        print(f"[PDF Splitter] ✓ Created ZIP file: {zip_path.name}")
        print(f"[PDF Splitter] Output directory: {output_dir}")
        
    except Exception as e:
        print(f"[PDF Splitter] ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


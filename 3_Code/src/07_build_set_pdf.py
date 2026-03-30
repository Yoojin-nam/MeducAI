"""
MeducAI Step06 (PDF Builder) — Set-level PDF Packet Builder for S0 QA

P0 Requirements:
- Build ONE PDF per Set (= group × arm artifact bundle)
- PDF section order: (1) Master Table -> (2) Infographic image -> (3) Cards (12 cards)
- Cards: place images based on image_placement (FRONT/BACK/NONE) from S3 policy manifest
- Support blinded mode: strip provenance cues, use surrogate set_id

Design Principles:
- Read-only consumption of frozen schemas (S1, S2, S3, S4)
- Deterministic file naming and layout
- Identical layout across arms (fonts, spacing, page structure)
- No LLM calls, no network calls
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

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
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from PIL import Image as PILImage
import os

# Import path resolver for S2 results (backward compatibility)
try:
    import sys
    _THIS_DIR = Path(__file__).resolve().parent
    sys.path.insert(0, str(_THIS_DIR))
    from tools.path_resolver import resolve_s2_results_path
    from tools.s6_export_manifest import load_export_manifest, should_use_repaired
except ImportError:
    # Fallback: define simple resolver if path_resolver not available
    def resolve_s2_results_path(out_dir: Path, arm: str, s1_arm=None) -> Path:
        # Try new format first
        if s1_arm:
            new_path = out_dir / f"s2_results__s1arm{s1_arm}__s2arm{arm}.jsonl"
            if new_path.exists():
                return new_path
        # Fallback to legacy
        return out_dir / f"s2_results__arm{arm}.jsonl"

    def load_export_manifest(manifest_path: Optional[Path]) -> Dict[str, bool]:  # type: ignore[no-redef]
        return {}

    def should_use_repaired(  # type: ignore[no-redef]
        manifest: Dict[str, bool], *, group_id: str, default: bool = False
    ) -> bool:
        return default


def _resolve_repaired_variant_path(baseline_path: Path) -> Path:
    """
    Convert `something.jsonl` -> `something__repaired.jsonl` (does not check existence).
    """
    suffix = baseline_path.suffix
    stem = baseline_path.name[: -len(suffix)] if suffix else baseline_path.name
    return baseline_path.with_name(f"{stem}__repaired{suffix}")


def resolve_group_variant_paths(
    *,
    gen_dir: Path,
    arm: str,
    s1_arm_actual: str,
    group_id: str,
    export_manifest: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    """
    Resolve baseline/repaired input paths for a given group.

    - Baseline is always the default.
    - If the manifest selects repaired for this group, we try repaired variants first
      (when they exist), otherwise fallback to baseline per-file.
    """
    arm_u = arm.strip().upper()
    s1_arm_u = s1_arm_actual.strip().upper()

    s1_baseline = gen_dir / f"stage1_struct__arm{s1_arm_u}.jsonl"
    s2_baseline = resolve_s2_results_path(gen_dir, arm_u, s1_arm=s1_arm_u)
    s3_policy_baseline = gen_dir / f"image_policy_manifest__arm{arm_u}.jsonl"
    s4_manifest_baseline = gen_dir / f"s4_image_manifest__arm{arm_u}.jsonl"
    s5_baseline = gen_dir / f"s5_validation__arm{arm_u}.jsonl"
    s5_postrepair = gen_dir / f"s5_validation__arm{arm_u}__postrepair.jsonl"

    use_repaired = should_use_repaired(export_manifest or {}, group_id=group_id, default=False)

    # S2 repaired path: prefer explicit repaired naming, fallback to baseline resolver + suffix conversion.
    s2_repaired_candidates = [
        gen_dir / f"s2_results__s1arm{s1_arm_u}__s2arm{arm_u}__repaired.jsonl",
        gen_dir / f"s2_results__arm{arm_u}__repaired.jsonl",
        _resolve_repaired_variant_path(s2_baseline),
    ]
    s2_repaired = next((p for p in s2_repaired_candidates if p.exists()), s2_baseline)

    # Optional repaired variants for other artifacts
    s1_repaired = _resolve_repaired_variant_path(s1_baseline)
    if not s1_repaired.exists():
        s1_repaired = s1_baseline

    s3_policy_repaired = _resolve_repaired_variant_path(s3_policy_baseline)
    if not s3_policy_repaired.exists():
        s3_policy_repaired = s3_policy_baseline

    s4_manifest_repaired = _resolve_repaired_variant_path(s4_manifest_baseline)
    if not s4_manifest_repaired.exists():
        s4_manifest_repaired = s4_manifest_baseline

    # For S5 display in PDF: if group is repaired, prefer postrepair S5 (if present).
    s5_chosen = s5_postrepair if (use_repaired and s5_postrepair.exists()) else s5_baseline

    return {
        "use_repaired": bool(use_repaired),
        "s1_path": (s1_repaired if use_repaired else s1_baseline),
        "s2_path": (s2_repaired if use_repaired else s2_baseline),
        "s3_policy_path": (s3_policy_repaired if use_repaired else s3_policy_baseline),
        "s4_manifest_path": (s4_manifest_repaired if use_repaired else s4_manifest_baseline),
        "s5_path": s5_chosen,
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


# =========================
# Data Loading
# =========================

def load_s1_struct(s1_path: Path, group_id: str) -> Optional[Dict[str, Any]]:
    """Load S1 structure for a specific group."""
    if not s1_path.exists():
        return None
    
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if record.get("group_id") == group_id:
                    return record
            except json.JSONDecodeError:
                continue
    return None


def list_all_group_ids(s1_path: Path) -> List[str]:
    """List all group_ids in S1 structure file."""
    group_ids = []
    if not s1_path.exists():
        return group_ids
    
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                group_id = record.get("group_id")
                if group_id:
                    group_ids.append(group_id)
            except json.JSONDecodeError:
                continue
    return group_ids


def load_s2_results(s2_path: Path, group_id: str) -> List[Dict[str, Any]]:
    """Load S2 results for a specific group."""
    records = []
    if not s2_path.exists():
        return records
    
    with open(s2_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if record.get("group_id") == group_id:
                    records.append(record)
            except json.JSONDecodeError:
                continue
    return records


def load_s3_policy_manifest(manifest_path: Path, group_id: str) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """
    Load S3 policy manifest for a specific group.
    
    Returns:
        Dict mapping (entity_id, card_role) -> policy entry
    """
    mapping = {}
    if not manifest_path.exists():
        return mapping
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("group_id") == group_id:
                    entity_id = entry.get("entity_id", "")
                    card_role = entry.get("card_role", "")
                    if entity_id and card_role:
                        mapping[(entity_id, card_role)] = entry
            except json.JSONDecodeError:
                continue
    return mapping


def load_s5_validation(s5_path: Path, group_id: str) -> Optional[Dict[str, Any]]:
    """
    Load S5 validation result for a specific group (latest by validation_timestamp).
    
    Returns:
        S5 validation record dict or None if not found
    """
    if not s5_path.exists():
        return None
    
    from datetime import datetime
    
    best_record = None
    best_timestamp = None
    
    with open(s5_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if record.get("group_id") == group_id:
                    ts_str = record.get("validation_timestamp", "")
                    # Parse ISO timestamp for comparison
                    if ts_str:
                        try:
                            # Handle 'Z' suffix
                            if ts_str.endswith("Z"):
                                ts_str = ts_str[:-1] + "+00:00"
                            ts = datetime.fromisoformat(ts_str)
                            if best_timestamp is None or ts > best_timestamp:
                                best_timestamp = ts
                                best_record = record
                        except Exception:
                            # If parsing fails, use first matching record
                            if best_record is None:
                                best_record = record
                    elif best_record is None:
                        best_record = record
            except json.JSONDecodeError:
                continue
    
    return best_record


def load_s4_image_manifest(manifest_path: Path, group_id: str, base_dir: Path, run_tag: str) -> Dict[Tuple[str, Optional[str], Optional[str]], str]:
    """
    Load S4 image manifest for a specific group.
    
    Returns:
        Dict mapping (spec_kind, entity_id, card_role) -> image_path
        For clustered table visuals: (spec_kind, cluster_id, None) -> image_path
    
    Note: entity_id in image filenames uses underscore (DERIVED_xxx) but S2 records
    use colon (DERIVED:xxx). We normalize both formats to handle the mismatch.
    """
    mapping = {}
    if not manifest_path.exists():
        return mapping
    
    # Try multiple possible image directory locations
    images_dir = manifest_path.parent / "images"
    if not images_dir.exists():
        images_dir = get_images_dir(base_dir, run_tag)
    
    def normalize_entity_id(entity_id: Optional[str]) -> Optional[str]:
        """Normalize entity_id: convert colon to underscore for filename compatibility."""
        if entity_id is None:
            return None
        # Convert DERIVED:xxx to DERIVED_xxx to match filename format
        return str(entity_id).replace(":", "_")
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("group_id") == group_id:
                    spec_kind = entry.get("spec_kind", "")
                    entity_id = entry.get("entity_id")
                    card_role = entry.get("card_role")
                    cluster_id = entry.get("cluster_id")  # May be present for clustered table visuals
                    media_filename = entry.get("media_filename", "")
                    
                    if media_filename:
                        image_path = images_dir / media_filename
                        if image_path.exists():
                            # Convert to absolute path for reportlab
                            abs_path = image_path.resolve()
                            # For clustered table visuals, use cluster_id as key
                            if spec_kind == "S1_TABLE_VISUAL" and cluster_id:
                                key = (spec_kind, cluster_id, None)
                            else:
                                # Normalize entity_id for matching (handle both colon and underscore formats)
                                normalized_entity_id = normalize_entity_id(entity_id)
                                key = (spec_kind, normalized_entity_id, card_role)
                            mapping[key] = str(abs_path)
                        else:
                            # Try alternative location: absolute path from manifest
                            alt_path = entry.get("image_path")
                            if alt_path:
                                alt_path_obj = Path(alt_path)
                                if alt_path_obj.exists():
                                    abs_path = alt_path_obj.resolve()
                                    normalized_entity_id = normalize_entity_id(entity_id)
                                    key = (spec_kind, normalized_entity_id, card_role)
                                    mapping[key] = str(abs_path)
            except json.JSONDecodeError:
                continue
    return mapping


def load_surrogate_map(csv_path: Path) -> Dict[Tuple[str, str], str]:
    """
    Load surrogate mapping CSV.
    
    Expected format:
        group_id,arm,surrogate_set_id
    """
    mapping = {}
    if not csv_path.exists():
        return mapping
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            group_id = row.get("group_id", "").strip()
            arm = row.get("arm", "").strip().upper()
            surrogate = row.get("surrogate_set_id", "").strip()
            if group_id and arm and surrogate:
                mapping[(group_id, arm)] = surrogate
    return mapping


# =========================
# Markdown Parsing
# =========================

def parse_inline_math_commands(text: str) -> str:
    """
    Parse inline LaTeX math commands in general text (not just $...$ blocks).
    
    Handles:
    - \cos, \sin, \tan, etc. → cos, sin, tan (in italic)
    - \le, \leq → ≤
    - \ge, \geq → ≥
    - \propto → ∝
    - \theta, \alpha, etc. → θ, α, etc.
    - ^\circ → °
    - \cosθ → cos θ (add space before Greek letters)
    """
    if not text or not isinstance(text, str):
        return str(text) if text else ""
    
    # Greek letters mapping
    greek_map = {
        r'\\theta': 'θ',
        r'\\alpha': 'α',
        r'\\beta': 'β',
        r'\\gamma': 'γ',
        r'\\delta': 'δ',
        r'\\pi': 'π',
        r'\\sigma': 'σ',
        r'\\mu': 'μ',
        r'\\lambda': 'λ',
        r'\\omega': 'ω',
    }
    
    # Math functions (will be converted to italic)
    math_functions = ['cos', 'sin', 'tan', 'sec', 'csc', 'cot', 'log', 'ln', 'exp']
    
    # Step 1: Handle ^\circ → ° (do this first, before other processing)
    text = re.sub(r'\^\\circ', '°', text)
    text = re.sub(r'\^\{\\circ\}', '°', text)
    
    # Step 2: Handle Greek letters (do this before math functions so \cosθ works)
    for latex, unicode_char in greek_map.items():
        text = re.sub(latex, unicode_char, text)
    
    # Step 3: Handle comparison operators
    text = re.sub(r'\\le\b', '≤', text)
    text = re.sub(r'\\leq\b', '≤', text)
    text = re.sub(r'\\ge\b', '≥', text)
    text = re.sub(r'\\geq\b', '≥', text)
    
    # Step 4: Handle \propto → ∝
    text = re.sub(r'\\propto\b', '∝', text)
    
    # Step 5: Handle math functions: \cos, \sin, etc.
    # Get all Greek letter Unicode characters for pattern matching
    greek_chars = ''.join(greek_map.values())
    
    for func in math_functions:
        # Pattern 1: \cosθ (no space, directly followed by Greek letter) → <i>cos</i> θ
        text = re.sub(
            rf'\\{func}([{greek_chars}])',
            rf'<i>{func}</i> \1',
            text
        )
        
        # Pattern 2: \cos90 or \cos(90) (followed by number or parenthesis) → <i>cos</i>90 or <i>cos</i>(90)
        text = re.sub(
            rf'\\{func}(?=\d|\()',
            f'<i>{func}</i>',
            text
        )
        
        # Pattern 3: \cos with space, punctuation, or at end → <i>cos</i>
        text = re.sub(
            rf'\\{func}(?=\s|$|;|,|→|\)|°|≤|≥|∝)',
            f'<i>{func}</i>',
            text
        )
    
    # Step 6: Wrap math variables in italic (single letters like fd, v, etc. in math context)
    # Pattern: standalone variables in math expressions
    # Example: "fd ∝ v" → "<i>fd</i> ∝ <i>v</i>"
    # But be careful not to wrap words that are part of normal text
    
    # Match single/double letter variables followed by math symbols or operators
    # Pattern: word boundary, 1-3 lowercase letters, space, then math symbol
    math_var_pattern = r'\b([a-z]{1,3})\s+([∝≤≥=→])'
    def wrap_math_var(match):
        var = match.group(1)
        op = match.group(2)
        return f'<i>{var}</i> {op}'
    text = re.sub(math_var_pattern, wrap_math_var, text)
    
    # Also wrap variables after math operators
    # Pattern: math symbol, space, 1-3 lowercase letters, then space or end
    math_var_pattern2 = r'([∝≤≥=→])\s+([a-z]{1,3})(?=\s|$|;|,|°|θ|α|β|γ|δ|π|σ|μ|λ|ω)'
    def wrap_math_var2(match):
        op = match.group(1)
        var = match.group(2)
        return f'{op} <i>{var}</i>'
    text = re.sub(math_var_pattern2, wrap_math_var2, text)
    
    # Step 7: Wrap complete math expressions in italic
    # Pattern: expressions like "cos 90° = 0" or "fd ∝ v cos θ"
    # These should be wrapped as a whole if they contain math symbols
    
    # Pattern 1: function number° = number (e.g., "cos 90° = 0")
    # Match: <i>cos</i> or <i>sin</i> etc., followed by number, °, =, number
    # Need to extract the function name and wrap the whole expression
    def wrap_math_expr1(match):
        func_tag = match.group(1)  # <i>cos</i>
        num1 = match.group(2)  # 90°
        num2 = match.group(3)  # 0
        # Extract function name from tag
        func_match = re.search(r'<i>(\w+)</i>', func_tag)
        if func_match is None:
            return match.group(0)  # Return original if pattern doesn't match
        func_name = func_match.group(1)
        return f'<i>{func_name} {num1} = {num2}</i>'
    text = re.sub(
        r'(<i>(?:cos|sin|tan|sec|csc|cot|log|ln|exp)</i>)\s+(\d+°)\s*=\s*(\d+)',
        wrap_math_expr1,
        text
    )
    
    # Pattern 2: variable ∝ variable function variable (e.g., "fd ∝ v cos θ")
    # Match: <i>var</i> ∝ <i>var</i> <i>function</i> variable
    def wrap_math_expr2(match):
        var1_tag = match.group(1)  # <i>fd</i>
        var2_tag = match.group(2)  # <i>v</i>
        func_tag = match.group(3)  # <i>cos</i>
        greek = match.group(4)  # θ
        # Extract variable and function names
        var1_match = re.search(r'<i>(\w+)</i>', var1_tag)
        var2_match = re.search(r'<i>(\w+)</i>', var2_tag)
        func_match = re.search(r'<i>(\w+)</i>', func_tag)
        if var1_match is None or var2_match is None or func_match is None:
            return match.group(0)  # Return original if pattern doesn't match
        var1 = var1_match.group(1)
        var2 = var2_match.group(1)
        func_name = func_match.group(1)
        return f'<i>{var1} ∝ {var2} {func_name} {greek}</i>'
    text = re.sub(
        r'(<i>[a-z]{1,3}</i>)\s+∝\s+(<i>[a-z]{1,3}</i>)\s+(<i>(?:cos|sin|tan)</i>)\s+([θαβγδπσμλω])',
        wrap_math_expr2,
        text
    )
    
    # Step 8: Clean up duplicate spaces
    text = re.sub(r'  +', ' ', text)
    
    return text


def parse_math_expressions(text: str) -> str:
    """
    Parse math expressions in $...$ format for ReportLab.
    
    Converts:
    - $variable$ → <i>variable</i> (italic for math variables)
    - $expression$ → <i>expression</i> with special symbols converted
    
    Special symbol conversions:
    - \propto → ∝ (proportional to)
    - \leq → ≤
    - \geq → ≥
    - \times → ×
    - \div → ÷
    - \cos → cos (keep as text)
    - \sin → sin (keep as text)
    - \theta → θ
    - \alpha → α
    - \beta → β
    - \gamma → γ
    - \delta → δ
    - \pi → π
    - \sigma → σ
    - \mu → μ
    - \lambda → λ
    - \omega → ω
    """
    if not text or not isinstance(text, str):
        return str(text) if text else ""
    
    # Symbol mapping
    symbol_map = {
        r'\\propto': '∝',
        r'\\leq': '≤',
        r'\\geq': '≥',
        r'\\times': '×',
        r'\\div': '÷',
        r'\\theta': 'θ',
        r'\\alpha': 'α',
        r'\\beta': 'β',
        r'\\gamma': 'γ',
        r'\\delta': 'δ',
        r'\\pi': 'π',
        r'\\sigma': 'σ',
        r'\\mu': 'μ',
        r'\\lambda': 'λ',
        r'\\omega': 'ω',
    }
    
    def process_math_expression(match):
        """Process a single math expression."""
        expr = match.group(1)  # Content between $...$
        
        # Replace LaTeX symbols with Unicode equivalents
        for latex, unicode_char in symbol_map.items():
            expr = re.sub(latex, unicode_char, expr)
        
        # Handle ^\circ
        expr = re.sub(r'\^\\circ', '°', expr)
        expr = re.sub(r'\^\{\\circ\}', '°', expr)
        
        # Handle math functions
        math_functions = ['cos', 'sin', 'tan', 'sec', 'csc', 'cot', 'log', 'ln', 'exp']
        for func in math_functions:
            expr = re.sub(rf'\\{func}\b', func, expr)
        
        # Wrap in italic tags for math formatting
        return f'<i>{expr}</i>'
    
    # Match $...$ expressions (non-greedy to handle multiple expressions)
    # Pattern: $...$ but not $$...$$ (which would be block math)
    text = re.sub(r'\$([^$\n]+?)\$', process_math_expression, text)
    
    return text


def parse_markdown_formatting(text: str) -> str:
    """
    Parse markdown formatting (bold, italic, etc.) and convert to HTML tags for reportlab.
    
    Supported markdown:
    - **bold** or __bold__ -> <b>bold</b>
    - *italic* or _italic_ -> <i>italic</i>
    - ***bold-italic*** or ___bold-italic___ -> <b><i>bold-italic</i></b>
    - $expression$ -> <i>expression</i> (math expression in italic)
    
    Note: This function processes markdown before HTML sanitization.
    Always processes markdown even if HTML tags are present (to handle mixed content).
    """
    if not text or not isinstance(text, str):
        return str(text) if text else ""
    
    # Process inline math commands first (handles \cos, \le, ^\circ, etc. in general text)
    text = parse_inline_math_commands(text)
    
    # Process math expressions in $...$ format
    text = parse_math_expressions(text)
    
    # Strategy: Process markdown by splitting text into segments (outside/inside HTML tags)
    # This avoids lookbehind issues and ensures we don't process markdown inside HTML tags
    
    def process_markdown_in_segments(text_str: str) -> str:
        """Process markdown only in segments outside HTML tags."""
        result = []
        i = 0
        in_tag = False
        
        while i < len(text_str):
            if text_str[i] == '<' and i + 1 < len(text_str) and text_str[i + 1] not in ['*', '_']:
                # Start of HTML tag (but not markdown)
                in_tag = True
                result.append(text_str[i])
                i += 1
                # Copy entire tag
                while i < len(text_str) and text_str[i] != '>':
                    result.append(text_str[i])
                    i += 1
                if i < len(text_str):
                    result.append(text_str[i])  # '>'
                    i += 1
                in_tag = False
            else:
                # Regular character - collect segment
                segment_start = i
                while i < len(text_str):
                    if text_str[i] == '<' and i + 1 < len(text_str) and text_str[i + 1] not in ['*', '_']:
                        break
                    i += 1
                segment = text_str[segment_start:i]
                if segment:
                    # Process markdown in this segment
                    # Process bold-italic first (triple asterisks/underscores)
                    segment = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', segment)
                    segment = re.sub(r'___(.+?)___', r'<b><i>\1</i></b>', segment)
                    # Process bold (double asterisks/underscores)
                    segment = re.sub(r'(?<!\*)\*\*(?!\*)(.+?)(?<!\*)\*\*(?!\*)', r'<b>\1</b>', segment)
                    segment = re.sub(r'(?<!_)__(?!_)(.+?)(?<!_)__(?!_)', r'<b>\1</b>', segment)
                    # Process italic (single asterisk/underscore, but not part of bold)
                    segment = re.sub(r'(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', segment)
                    segment = re.sub(r'(?<!_)_(?!_)([^_]+?)(?<!_)_(?!_)', r'<i>\1</i>', segment)
                    result.append(segment)
        
        return ''.join(result)
    
    text = process_markdown_in_segments(text)
    
    return text


# =========================
# HTML Sanitization for ReportLab
# =========================

def sanitize_html_for_reportlab(text: str) -> str:
    """
    Sanitize HTML text for reportlab Paragraph.
    
    ReportLab requirements:
    - <br> must be <br/> (self-closing)
    - <para> tags should be removed (Paragraph already creates para)
    - Other HTML tags are generally OK but we clean up common issues
    - Fix malformed tags with unescaped < and > characters inside tag content
    - Fix escaped HTML entities that should be actual tags (e.g., &lt;i&gt; → <i>)
    
    Note: Markdown formatting should be parsed first using parse_markdown_formatting()
    """
    if not text or not isinstance(text, str):
        return str(text) if text else ""
    
    # First, parse markdown formatting to HTML (always process, even if HTML tags exist)
    # This ensures **text** is converted to <b>text</b> even in mixed content
    # NOTE: This must be called BEFORE other processing to convert markdown to HTML
    # If markdown is not converted here, it will appear as literal **text** in the PDF
    text = parse_markdown_formatting(text)
    
    # Remove <para> tags (reportlab Paragraph already creates para)
    # Do this multiple times to catch nested or malformed para tags
    for _ in range(3):
        text = re.sub(r'</?para[^>]*>', '', text, flags=re.IGNORECASE)
    
    # Fix escaped HTML tags that should be actual tags
    # Common pattern: <b>CTDI&lt;<br/>i&gt;<br/>w</b> should become <b>CTDI<i>w</b>
    # Strategy: Find patterns like &lt;tag&gt; or &lt;/tag&gt; and convert to <tag> or </tag>
    # But be careful: only fix if it's clearly meant to be a tag, not escaped text
    
    # First, fix obvious cases: &lt;br/&gt; → <br/>
    text = re.sub(r'&lt;br\s*/?\s*&gt;', '<br/>', text, flags=re.IGNORECASE)
    
    # Fix &lt;i&gt; → <i> and &lt;/i&gt; → </i>
    # Pattern: &lt;i&gt; or &lt;/i&gt; that appears to be a tag
    text = re.sub(r'&lt;(/?)i&gt;', r'<\1i>', text, flags=re.IGNORECASE)
    
    # Fix other common escaped tags: &lt;b&gt;, &lt;/b&gt;, etc.
    text = re.sub(r'&lt;(/?)b&gt;', r'<\1b>', text, flags=re.IGNORECASE)
    
    # Fix complex patterns like: &lt;<br/>i&gt; → <i>
    # This handles cases where <br/> appears between &lt; and i&gt;
    text = re.sub(r'&lt;\s*<br/>\s*([a-zA-Z]+)\s*&gt;', r'<\1>', text, flags=re.IGNORECASE)
    text = re.sub(r'&lt;\s*<br/>\s*/([a-zA-Z]+)\s*&gt;', r'</\1>', text, flags=re.IGNORECASE)
    
    # Fix specific problematic patterns found in errors:
    # Pattern: <b>CTDI&lt;<br/>i&gt;<br/>w</b> → <b>CTDI<i>w</b>
    # This pattern has escaped <i> tag split across <br/> tags
    def fix_split_escaped_tags(match):
        prefix = match.group(1)  # Text before &lt;
        tag_name = match.group(2)  # Tag name (e.g., 'i')
        suffix = match.group(3)  # Text after &gt;
        # Remove any <br/> tags between the escaped tag parts
        suffix = re.sub(r'<br/>\s*', '', suffix)
        return f'{prefix}<{tag_name}>{suffix}'
    
    # Match: text&lt;<br/>tag&gt;<br/>text
    text = re.sub(r'([^<]*?)&lt;\s*<br/>\s*([a-zA-Z]+)\s*&gt;\s*<br/>\s*([^<]*?)', fix_split_escaped_tags, text, flags=re.IGNORECASE)
    
    # Also fix: text&lt;tag&gt;text where tag is split by <br/>
    text = re.sub(r'&lt;\s*([a-zA-Z]+)\s*&gt;\s*<br/>\s*', r'<\1>', text, flags=re.IGNORECASE)
    
    # Fix orphaned closing tags: if we have </i> but no opening <i>, remove it
    # This is a last resort - try to balance tags
    # Strategy: Track opening and closing tags, remove excess closing tags
    def balance_tags(text_str, tag_name):
        """Balance opening and closing tags by removing excess closing tags."""
        open_pattern = rf'<{tag_name}>'
        close_pattern = rf'</{tag_name}>'
        open_count = len(re.findall(open_pattern, text_str, re.IGNORECASE))
        close_count = len(re.findall(close_pattern, text_str, re.IGNORECASE))
        if close_count > open_count:
            # Remove excess closing tags (keep only as many as opening tags)
            excess = close_count - open_count
            for _ in range(excess):
                text_str = re.sub(close_pattern, '', text_str, count=1, flags=re.IGNORECASE)
        return text_str
    
    # Balance common tags that cause issues
    text = balance_tags(text, 'i')
    text = balance_tags(text, 'b')
    text = balance_tags(text, 'para')
    
    # Fix malformed HTML tags: escape < and > that appear inside tag content
    # This handles cases like <b><L2</b> or <b>>2mm</b>
    # Strategy: Find all tag pairs and escape < and > in their content that aren't valid HTML tags
    
    def fix_tag_content(text_str):
        """Escape < and > in tag content that aren't part of valid HTML structure."""
        # Process tag pairs: <tag>content</tag>
        def escape_in_tag_content(match):
            tag_name = match.group(1)
            content = match.group(2)
            
            # Escape < and > in content
            # Strategy: Replace < and > that are not part of valid HTML tags or entities
            # A valid tag starts with < followed by a letter, /, or !
            # We'll escape any < that's not followed by a valid tag start pattern
            # and any > that's not part of a valid tag or entity
            
            # Escape < that's not part of a valid HTML tag or entity
            # Valid patterns: <tag, </tag, <!, &lt;
            content = re.sub(r'<(?![a-zA-Z/!]|&[a-zA-Z#])', '&lt;', content)
            # Escape > that's not part of a valid HTML tag or entity
            # Valid patterns: > (closing tag), &gt;
            content = re.sub(r'(?<!&[a-zA-Z#])>', '&gt;', content)
            
            return f'<{tag_name}>{content}</{tag_name}>'
        
        # Match tag pairs: <tag>content</tag>
        # Pattern matches opening tag, any content (including nested tags), and closing tag
        # We iterate to handle nested cases
        pattern = r'<([a-zA-Z]+)>((?:[^<]|<(?!/?\1>))*?)</\1>'
        max_iter = 5
        for _ in range(max_iter):
            new_text = re.sub(pattern, escape_in_tag_content, text_str, flags=re.IGNORECASE | re.DOTALL)
            if new_text == text_str:
                break
            text_str = new_text
        
        # Additional pass: handle edge cases like <b><L2</b>
        # Problem: <L2 is not a valid HTML tag (missing closing >)
        # Solution: In tag content, escape < that doesn't have a matching > before </tag>
        def escape_incomplete_tags(match):
            tag_name = match.group(1)
            content = match.group(2) if match.lastindex >= 2 else ""
            
            # Process content character by character
            result = []
            i = 0
            while i < len(content):
                if content[i] == '<':
                    # Check if this < is part of a complete tag
                    # Look ahead to find the next > or </tag_name
                    remaining = content[i:]
                    next_gt = remaining.find('>', 1)  # Skip the < itself
                    next_tag_close = remaining.find(f'</{tag_name}')
                    
                    # If there's a > before </tag_name, it might be a complete tag
                    # But we need to check if it's a valid tag pattern
                    if next_gt != -1 and (next_tag_close == -1 or next_gt < next_tag_close):
                        # Check if it looks like a valid tag: <tag>, </tag>, or <!
                        tag_candidate = remaining[1:next_gt]  # Content between < and >
                        if re.match(r'^[a-zA-Z/!]', tag_candidate):
                            # It's a complete valid tag, keep it
                            result.append(content[i])
                            i += 1
                            continue
                    # No > found, or > comes after </tag_name, so this < is not a complete tag
                    # Escape it
                    result.append('&lt;')
                    i += 1
                else:
                    result.append(content[i])
                    i += 1
            
            new_content = ''.join(result)
            return f'<{tag_name}>{new_content}</{tag_name}>'
        
        # Apply the fix to all tag pairs
        pattern = r'<([a-zA-Z]+)>((?:[^<]|<(?!/?\1>))*?)</\1>'
        text_str = re.sub(pattern, escape_incomplete_tags, text_str, flags=re.IGNORECASE | re.DOTALL)
        
        # Also handle <tag>>something (standalone > after opening tag)
        text_str = re.sub(r'(<[a-zA-Z]+>)>(?![a-zA-Z/!]|&[a-zA-Z#])', r'\1&gt;', text_str)
        
        return text_str
    
    text = fix_tag_content(text)
    
    # Final cleanup: Remove any remaining <para> tags (should have been removed earlier, but be safe)
    # Do this aggressively - remove all para tags
    # Also handle cases where para tags wrap the entire content
    for _ in range(5):
        text = re.sub(r'</?para[^>]*>', '', text, flags=re.IGNORECASE)
        # Also handle malformed para tags
        text = re.sub(r'<para\b[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</para\b[^>]*>', '', text, flags=re.IGNORECASE)
    
    # Special case: If text starts with <para> and ends with </para>, remove them
    text = re.sub(r'^<para[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</para[^>]*>$', '', text, flags=re.IGNORECASE)
    
    # Final tag balancing: Remove orphaned closing tags that have no matching opening tag
    # This is a safety measure for malformed HTML
    # Only remove orphaned </i> and </b> tags, as these are most common issues
    i_open = len(re.findall(r'<i\b[^>]*>', text, re.IGNORECASE))
    i_close = len(re.findall(r'</i\b[^>]*>', text, re.IGNORECASE))
    if i_close > i_open:
        # Remove excess </i> tags (remove from the end first, as they're likely orphaned)
        excess = i_close - i_open
        # Find all </i> positions and remove the last ones
        matches = list(re.finditer(r'</i>', text, re.IGNORECASE))
        if matches and len(matches) >= excess:
            # Remove from the end
            for match in reversed(matches[:excess]):
                text = text[:match.start()] + text[match.end():]
        else:
            # Fallback: just remove all excess closing tags using regex
            for _ in range(excess):
                text = re.sub(r'</i>', '', text, count=1, flags=re.IGNORECASE)
    
    b_open = len(re.findall(r'<b\b[^>]*>', text, re.IGNORECASE))
    b_close = len(re.findall(r'</b\b[^>]*>', text, re.IGNORECASE))
    if b_close > b_open:
        excess = b_close - b_open
        matches = list(re.finditer(r'</b>', text, re.IGNORECASE))
        if matches and len(matches) >= excess:
            for match in reversed(matches[:excess]):
                text = text[:match.start()] + text[match.end():]
        else:
            # Fallback
            for _ in range(excess):
                text = re.sub(r'</b>', '', text, count=1, flags=re.IGNORECASE)
    
    # Convert <br> to <br/> (self-closing tag required by reportlab)
    # Also handle escaped versions
    text = re.sub(r'&lt;br\s*/?\s*&gt;', '<br/>', text, flags=re.IGNORECASE)
    text = re.sub(r'<br\s*/?>', '<br/>', text, flags=re.IGNORECASE)
    
    # Convert <br /> to <br/> (normalize spacing)
    text = re.sub(r'<br\s+/>', '<br/>', text, flags=re.IGNORECASE)
    
    # Final check: ensure <br/> is properly formatted (no spaces, self-closing)
    text = re.sub(r'<br\s*/?\s*>', '<br/>', text, flags=re.IGNORECASE)
    
    return text


def bold_important_terms(text: str) -> str:
    """
    Add bold formatting to important terms in table cells.
    
    Patterns to bold:
    - Medical abbreviations (CT, MRI, X-ray, etc.)
    - Terms in parentheses
    - Capitalized medical terms (e.g., "Nidus", "Codman triangle")
    - Numbers with units (e.g., "2cm", "< 2cm")
    """
    if not text or not isinstance(text, str):
        return str(text) if text else ""
    
    # Avoid processing already bolded text
    if '<b>' in text or '</b>' in text:
        return text
    
    # Track positions that are already bolded to avoid double bolding
    bolded_positions = set()
    
    # Helper function to check if position is already bolded
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
    
    # Pattern 3: Terms in parentheses - REMOVED per user request
    # User requested to not add bold formatting to parentheses content
    # (This was previously adding bold to content like "(17.5 keV)" -> "(<b>17.5 keV</b>)")
    
    # Pattern 4: Capitalized medical terms (more conservative approach)
    # Only bold multi-word capitalized terms (likely medical terms)
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
    
    # Only bold multi-word capitalized terms (e.g., "Codman triangle", "Giant Cell Tumor")
    text = re.sub(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', bold_capitalized_term, text)
    
    # Clean up: remove duplicate bold tags and fix spacing
    text = re.sub(r'</b>\s*<b>', ' ', text)
    text = re.sub(r'<b><b>', '<b>', text)
    text = re.sub(r'</b></b>', '</b>', text)
    
    return text


# =========================
# Markdown Table Parsing
# =========================

def parse_markdown_table(md_table: str) -> Tuple[List[str], List[List[str]]]:
    """
    Parse markdown table into headers and rows.
    
    Returns:
        (headers, rows) where headers is a list of column names and rows is a list of row data
    """
    lines = [line.strip() for line in md_table.strip().split("\n") if line.strip()]
    if not lines:
        return [], []
    
    # Find header row (first line with |)
    header_line = None
    header_idx = 0
    for i, line in enumerate(lines):
        if "|" in line:
            header_line = line
            header_idx = i
            break
    
    if not header_line:
        return [], []
    
    # Parse header
    headers = [cell.strip() for cell in header_line.split("|") if cell.strip()]
    
    # Skip separator row (---)
    rows = []
    for line in lines[header_idx + 2:]:
        if "|" in line:
            cells = [cell.strip() for cell in line.split("|") if cell.strip()]
            if len(cells) == len(headers):
                rows.append(cells)
    
    return headers, rows


# =========================
# PDF Generation
# =========================

def register_korean_font():
    """Register Korean font for PDF generation."""
    # Expand user home directory
    home_dir = os.path.expanduser("~")
    
    # Try to find separate Regular and Bold font files
    # For Variable Fonts, we need to find a separate bold variant or use a fallback
    korean_font_candidates = [
        # 나눔고딕 (Nanum Gothic) - preferred, use ExtraBold for better visibility
        (f"{home_dir}/Library/Fonts/NanumGothic.ttf", f"{home_dir}/Library/Fonts/NanumGothicExtraBold.ttf"),
        ("/Library/Fonts/NanumGothic.ttf", "/Library/Fonts/NanumGothicExtraBold.ttf"),
        # Fallback to regular Bold if ExtraBold not available
        (f"{home_dir}/Library/Fonts/NanumGothic.ttf", f"{home_dir}/Library/Fonts/NanumGothicBold.ttf"),
        ("/Library/Fonts/NanumGothic.ttf", "/Library/Fonts/NanumGothicBold.ttf"),
        # Noto Sans KR - try to find both Regular and Bold static fonts
        (f"{home_dir}/Library/Fonts/NotoSansKR-Regular.ttf", f"{home_dir}/Library/Fonts/NotoSansKR-Bold.ttf"),
        ("/Library/Fonts/NotoSansKR-Regular.ttf", "/Library/Fonts/NotoSansKR-Bold.ttf"),
        # Apple SD Gothic Neo - has separate bold variant
        ("/System/Library/Fonts/Supplemental/AppleSDGothicNeo-Regular.otf", "/System/Library/Fonts/Supplemental/AppleSDGothicNeo-Bold.otf"),
        ("/System/Library/Fonts/AppleSDGothicNeo.ttc", "/System/Library/Fonts/AppleSDGothicNeo.ttc"),  # TTC contains multiple weights
        # AppleGothic fallback
        ("/System/Library/Fonts/Supplemental/AppleGothic.ttf", "/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
        ("/Library/Fonts/AppleGothic.ttf", "/Library/Fonts/AppleGothic.ttf"),
    ]
    
    korean_font_name = "KoreanFont"
    korean_font_bold_name = "KoreanFont-Bold"
    
    # Try to find and register Korean font with separate bold variant
    for normal_path, bold_path in korean_font_candidates:
        if os.path.exists(normal_path):
            try:
                # Register normal font
                pdfmetrics.registerFont(TTFont(korean_font_name, normal_path))
                
                # Try to register bold variant (prefer separate file if available)
                bold_registered = False
                if os.path.exists(bold_path) and bold_path != normal_path:
                    try:
                        pdfmetrics.registerFont(TTFont(korean_font_bold_name, bold_path))
                        bold_registered = True
                    except Exception:
                        pass
                
                # If separate bold not found or failed, use same file
                # Note: This won't give true bold, but at least won't crash
                if not bold_registered:
                    try:
                        pdfmetrics.registerFont(TTFont(korean_font_bold_name, normal_path))
                    except Exception:
                        korean_font_bold_name = korean_font_name
                
                # Register font family so ReportLab can map <b> tags correctly
                pdfmetrics.registerFontFamily(
                    korean_font_name,
                    normal=korean_font_name,
                    bold=korean_font_bold_name
                )
                return korean_font_name, korean_font_bold_name
            except Exception:
                continue
    
    # Last resort: Try Variable Font but with warning that bold may not work
    variable_font_paths = [
        f"{home_dir}/Library/Fonts/NotoSansKR-VariableFont_wght.ttf",
        "/Library/Fonts/NotoSansKR-VariableFont_wght.ttf",
    ]
    
    for font_path in variable_font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(korean_font_name, font_path))
                # For Variable Font, we still register it twice but bold won't be visually different
                pdfmetrics.registerFont(TTFont(korean_font_bold_name, font_path))
                pdfmetrics.registerFontFamily(
                    korean_font_name,
                    normal=korean_font_name,
                    bold=korean_font_bold_name
                )
                # Note: Bold text won't be visually different with Variable Font using same file
                return korean_font_name, korean_font_bold_name
            except Exception:
                continue
    
    # Fallback: use Helvetica (may not display Korean correctly)
    return "Helvetica", "Helvetica-Bold"


def create_pdf_styles():
    """Create consistent PDF styles."""
    styles = getSampleStyleSheet()
    
    # Register Korean font
    korean_font, korean_font_bold = register_korean_font()
    
    # Custom styles
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
        "card_header": ParagraphStyle(
            "CustomCardHeader",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#333333"),
            spaceAfter=4,
            fontName=korean_font_bold,
        ),
        "card_label": ParagraphStyle(
            "CustomCardLabel",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#666666"),
            spaceAfter=2,
            fontName=korean_font_bold,
        ),
        "card_text": ParagraphStyle(
            "CustomCardText",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.black,
            spaceAfter=6,
            leftIndent=0,
            fontName=korean_font,
            splitLongWords=False,  # Prevent word breaking in the middle
        ),
        "footer": ParagraphStyle(
            "CustomFooter",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#999999"),
            alignment=TA_CENTER,
            fontName=korean_font,
        ),
        "header_small": ParagraphStyle(
            "CustomHeaderSmall",
            parent=styles["Normal"],
            fontSize=12,
            textColor=colors.HexColor("#666666"),
            spaceAfter=2,
            fontName=korean_font,
        ),
    }
    
    return styles, custom_styles, korean_font, korean_font_bold


def parse_group_path_from_s1(s1_record: Dict[str, Any]) -> Tuple[str, str, str, Optional[str]]:
    """
    Parse S1 record to extract specialty, anatomy, modality_or_type, category.
    
    Uses group_path (format: "specialty > anatomy > modality > category") 
    or group_key (format: "subspecialty__region__category") as fallback.
    
    Returns:
        (specialty, anatomy, modality_or_type, category)
        - specialty: with "_rad" suffix removed and '_' replaced with spaces
        - anatomy: with '_' replaced with spaces
        - modality_or_type: with '_' replaced with spaces
        - category: with '_' replaced with spaces, or None if not present
    """
    def clean_text(text: str) -> str:
        """Remove '_rad' suffix and replace '_' with spaces."""
        if not text:
            return ""
        # Convert to string and handle "nan" (pandas/CSV empty value representation)
        text = str(text).strip()
        if text.lower() in ("nan", "none", "null", ""):
            return ""
        # Remove '_rad' suffix if present
        text = text.replace("_rad", "").replace("_RAD", "")
        # Replace '_' with spaces
        text = text.replace("_", " ")
        return text.strip()
    
    # Try group_path first (preferred, more readable format)
    group_path = s1_record.get("group_path", "")
    if group_path:
        # Format: "specialty > anatomy > modality > category"
        parts = [p.strip() for p in group_path.split(">")]
        if len(parts) >= 2:
            specialty = clean_text(parts[0]) if len(parts) > 0 else ""
            anatomy = clean_text(parts[1]) if len(parts) > 1 else ""
            modality_or_type = clean_text(parts[2]) if len(parts) > 2 else ""
            category_raw = parts[3] if len(parts) > 3 else None
            category = clean_text(category_raw) if category_raw else None
            # Return None if category is empty or "nan" after cleaning
            if not category or category.lower() in ("nan", "none", "null"):
                category = None
            return specialty, anatomy, modality_or_type, category
    
    # Fallback to group_key if group_path is not available
    group_key = s1_record.get("group_key", "")
    if group_key:
        # Format: "subspecialty__region__category"
        parts = group_key.split("__")
        specialty = clean_text(parts[0]) if len(parts) > 0 else ""
        anatomy = clean_text(parts[1]) if len(parts) > 1 else ""
        modality_or_type = ""  # Not available in group_key format
        category_raw = parts[2] if len(parts) > 2 else None
        category = clean_text(category_raw) if category_raw else None
        # Return None if category is empty or "nan" after cleaning
        if not category or category.lower() in ("nan", "none", "null"):
            category = None
        return specialty, anatomy, modality_or_type, category
    
    return "", "", "", None


def load_korean_objectives_from_canonical(
    base_dir: Path,
    group_key: str,
) -> List[str]:
    """
    Load Korean objectives from groups_canonical.csv based on group_key.
    
    Returns:
        List of Korean objective texts, or empty list if not found.
    """
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
                                # Filter out empty strings
                                return [obj for obj in objectives if obj and obj.strip()]
                        except (json.JSONDecodeError, TypeError):
                            pass
                    break
    except Exception as e:
        # Silently fail if reading fails
        pass
    
    return []


def build_objectives_section(
    story: List,
    objective_bullets: List[str],
    custom_styles: Dict[str, ParagraphStyle],
    page_width: float,
    page_height: float,
    korean_font: str,
    korean_font_bold: str,
    s1_record: Optional[Dict[str, Any]] = None,
    base_dir: Optional[Path] = None,
) -> None:
    """Build Learning Objectives section - displayed before Master Table."""
    # Try to load Korean objectives from groups_canonical.csv
    korean_objectives = []
    if s1_record and base_dir:
        group_key = s1_record.get("group_key", "").strip()
        if group_key:
            korean_objectives = load_korean_objectives_from_canonical(base_dir, group_key)
    
    # Use Korean objectives if available, otherwise fall back to objective_bullets
    objectives_to_display = korean_objectives if korean_objectives else objective_bullets
    
    if not objectives_to_display:
        return
    
    # Add section label at top left (like Master Table)
    specialty, anatomy, modality_or_type, category = parse_group_path_from_s1(s1_record) if s1_record else ("", "", "", None)
    
    # Build header text (similar to Master Table header)
    header_parts = []
    if specialty:
        header_parts.append(specialty)
    if anatomy:
        header_parts.append(anatomy)
    if modality_or_type:
        header_parts.append(modality_or_type)
    if category:
        header_parts.append(category)
    
    header_text = " > ".join(header_parts) if header_parts else ""
    
    # Section label at top left
    section_label_style = ParagraphStyle(
        "SectionLabel",
        parent=custom_styles["header_small"],
        fontSize=12,
        textColor=colors.HexColor("#666666"),
        spaceAfter=8,
        fontName=korean_font_bold,
        alignment=TA_LEFT,
    )
    if header_text:
        story.append(Paragraph(f"{header_text} | 학습 목표", section_label_style))
    else:
        story.append(Paragraph("학습 목표", section_label_style))
    
    story.append(Spacer(1, 0.3 * cm))
    
    # Objectives list
    objective_style = ParagraphStyle(
        "ObjectiveItem",
        parent=custom_styles["card_text"],
        fontSize=8,
        textColor=colors.black,
        spaceAfter=10,  # 중간값: 원래 8, 현재 12 → 중간 10
        leading=12,  # 중간값: 원래 기본값(약 9.6), 현재 14 → 중간 12
        leftIndent=0.5 * cm,
        bulletIndent=0.2 * cm,
        fontName=korean_font,
    )
    
    for objective in objectives_to_display:
        if objective and objective.strip():
            # Parse markdown formatting in objective text
            formatted_objective = parse_markdown_formatting(str(objective).strip())
            # Sanitize HTML for ReportLab
            formatted_objective = sanitize_html_for_reportlab(formatted_objective)
            story.append(Paragraph(f"• {formatted_objective}", objective_style))
    
    story.append(Spacer(1, 0.5 * cm))


def build_master_table_section(
    story: List,
    master_table_md: str,
    custom_styles: Dict[str, ParagraphStyle],
    page_width: float,
    page_height: float,
    korean_font: str,
    korean_font_bold: str,
    s1_record: Optional[Dict[str, Any]] = None,
    specialty: Optional[str] = None,
    content_score_weight_col0: float = 0.5,
    content_score_weight_col1: float = 0.55,
) -> None:
    """Build Master Table section - fits in one page."""
    # Add header info at top left (same format as Learning Objectives)
    specialty_parsed, anatomy, modality_or_type, category = parse_group_path_from_s1(s1_record) if s1_record else ("", "", "", None)
    
    # Build header text (same format as Learning Objectives: " > " separator)
    header_parts = []
    if specialty:
        # Combined PDF mode: use provided specialty
        specialty_clean = specialty.replace("_rad", "").replace("_RAD", "").replace("_", " ").strip()
        if specialty_clean:
            header_parts.append(specialty_clean)
    elif specialty_parsed:
        header_parts.append(specialty_parsed)
    if anatomy:
        header_parts.append(anatomy)
    if modality_or_type:
        header_parts.append(modality_or_type)
    if category:
        header_parts.append(category)
    
    header_text = " > ".join(header_parts) if header_parts else ""
    
    # Section label at top left (same style as Learning Objectives)
    section_label_style = ParagraphStyle(
        "SectionLabel",
        parent=custom_styles["header_small"],
        fontSize=12,
        textColor=colors.HexColor("#666666"),
        spaceAfter=8,
        fontName=korean_font_bold,
        alignment=TA_LEFT,
    )
    if header_text:
        story.append(Paragraph(f"{header_text} | Master Table", section_label_style))
    else:
        story.append(Paragraph("Master Table", section_label_style))
    
    story.append(Spacer(1, 0.3 * cm))
    
    headers, rows = parse_markdown_table(master_table_md)
    if not headers or not rows:
        story.append(Paragraph("(Table data not available)", custom_styles["card_text"]))
        return
    
    # Calculate available dimensions (reduced margins for digital viewing)
    available_width = page_width - (1.5 * cm)
    available_height = page_height - (1.5 * cm) - (1 * cm)  # margins + header space
    
    # Calculate font sizes to fit in one page
    num_rows = len(rows) + 1  # +1 for header
    num_cols = len(headers)
    
    # Font sizes: table header 8pt, all cells 8pt
    header_font_size = 8
    cell_font_size = 8
    entity_name_font_size = 8  # Same as other columns
    row_height = (available_height / num_rows) - 2  # -2 for padding
    
    # Find "Entity name" column index (usually first column, but check header name)
    entity_name_col_idx = 0
    for idx, header in enumerate(headers):
        header_lower = str(header).strip().lower()
        if "entity" in header_lower and "name" in header_lower:
            entity_name_col_idx = idx
            break
    
    # Calculate dynamic column widths based on content length
    def get_text_length(text: str) -> int:
        """Get text length after removing HTML tags."""
        # Remove HTML tags for length calculation
        clean_text = re.sub(r'<[^>]+>', '', text)
        return len(clean_text)
    
    def measure_text_width(text: str, font_name: str, font_size: float) -> float:
        """Measure actual rendered width of text using font metrics."""
        # Remove HTML tags for measurement
        clean_text = re.sub(r'<[^>]+>', '', text)
        if not clean_text:
            return 0.0
        try:
            width = stringWidth(clean_text, font_name, font_size)
            # Add conservative safety margin (20%) for font rendering variations
            # This is especially important for mixed Korean/English text
            return width * 1.2
        except Exception:
            # Fallback: estimate based on character count with generous margin
            return len(clean_text) * (font_size * 0.7)  # More generous estimate
    
    def find_longest_word_in_column(col_idx: int) -> str:
        """Find the longest word in a column (considering all cells)."""
        longest_word = ""
        all_texts = []
        
        # Add header text
        header_text = str(headers[col_idx]).strip()
        all_texts.append(header_text)
        
        # Add all cell texts
        for row in rows:
            if col_idx < len(row):
                cell_text = str(row[col_idx]).strip()
                all_texts.append(cell_text)
        
        # Find longest word (split by whitespace, hyphen, parentheses)
        for text in all_texts:
            # Remove HTML tags
            clean_text = re.sub(r'<[^>]+>', '', text)
            # Split by whitespace, hyphen, parentheses boundaries
            # Use regex to split while preserving delimiters for word boundaries
            words = re.split(r'[\s\-()]+', clean_text)
            for word in words:
                if word and len(word) > len(longest_word):
                    longest_word = word
        
        return longest_word
    
    # Calculate minimum width for each column based on content
    # This ensures no text overflows column boundaries
    def calculate_column_min_width(col_idx: int, font_size: float, is_bold: bool = False) -> float:
        """Calculate minimum width needed for a column based on its content."""
        font_name = korean_font_bold if is_bold else korean_font
        max_width = 0.0
        longest_word_width = 0.0
        
        # Check if this is the entity name column (needs extra care to prevent overflow)
        is_entity_name_col = (col_idx == entity_name_col_idx)
        
        # Check header (use header font size for header measurement)
        header_text = str(headers[col_idx]).strip()
        if header_text:
            # Remove HTML tags for measurement
            clean_header = re.sub(r'<[^>]+>', '', header_text)
            if clean_header:
                header_width = measure_text_width(clean_header, korean_font_bold, header_font_size)
                max_width = max(max_width, header_width)
        
        # Check all data cells - measure each cell text carefully
        # Also track the longest single word (like "Syndrome") separately
        # For columns with comma-separated content, measure segments separately to allow line breaks
        for row in rows:
            if col_idx < len(row):
                cell_text = str(row[col_idx]).strip()
                if cell_text:
                    # Remove HTML tags for measurement
                    clean_text = re.sub(r'<[^>]+>', '', cell_text)
                    if clean_text:
                        # For entity name column: measure segments separated by & or ( (line breaks allowed)
                        # For other columns: measure segments if comma-separated
                        if is_entity_name_col:
                            # Entity name: can break after & and before ( so measure segments separately
                            # Split by & (after) and ( (before) to get segments that will be on separate lines
                            # Pattern: split after "& " or before "("
                            segments = re.split(r'&[\s]+|[\s]*\(', clean_text)
                            for segment in segments:
                                if segment:
                                    segment_width = measure_text_width(segment.strip(), font_name, font_size)
                                    max_width = max(max_width, segment_width)
                            
                            # Also measure full cell text (in case it fits on one line)
                            cell_width = measure_text_width(clean_text, font_name, font_size)
                            max_width = max(max_width, cell_width)
                            
                            # Track longest word for entity name (critical for overflow prevention)
                            words = re.split(r'[\s\-()&]+', clean_text)
                            for word in words:
                                if word:
                                    word_width = measure_text_width(word, font_name, font_size)
                                    longest_word_width = max(longest_word_width, word_width)
                        elif col_idx == 1:
                            # Second column (질환/개념): can break at commas and before "("
                            # Split by comma and "(" to get segments that will be on separate lines
                            segments = re.split(r',\s*|[\s]*\(', clean_text)
                            for segment in segments:
                                if segment:
                                    segment_width = measure_text_width(segment.strip(), font_name, font_size)
                                    max_width = max(max_width, segment_width)
                            
                            # Also measure full cell text (in case it fits on one line)
                            cell_width = measure_text_width(clean_text, font_name, font_size)
                            max_width = max(max_width, cell_width)
                            
                            # Track longest word for second column
                            words = re.split(r'[\s\-()&]+', clean_text)
                            for word in words:
                                if word and len(word) > 3:
                                    word_width = measure_text_width(word, font_name, font_size)
                                    longest_word_width = max(longest_word_width, word_width)
                        else:
                            # Other columns: can break at commas
                            segments = re.split(r',\s*', clean_text)
                            for segment in segments:
                                if segment:
                                    segment_width = measure_text_width(segment, font_name, font_size)
                                    max_width = max(max_width, segment_width)
                            
                            # Also measure full cell text (in case it fits on one line)
                            cell_width = measure_text_width(clean_text, font_name, font_size)
                            max_width = max(max_width, cell_width)
                            
                            # Track longest word for other columns too
                            words = re.split(r'[\s\-()]+', clean_text)
                            for word in words:
                                if word and len(word) > 3:
                                    word_width = measure_text_width(word, font_name, font_size)
                                    longest_word_width = max(longest_word_width, word_width)
        
        # Use the maximum of: full cell width OR longest word width
        # Add safety margin (reduced for first 2 columns since they tend to be shorter)
        if is_entity_name_col:
            # Entity name: smaller margin since line breaks are allowed at & and (
            final_width = max(max_width, longest_word_width * 1.2)  # 20% margin instead of 30%
            padding = (3 * 2)  # 3pt padding each side
            margin = 0.5 * cm  # Reduced margin for entity name (0.5cm instead of 1.0cm)
        elif col_idx == 1:
            # Second column (질환/개념): further reduce margin since it can break at "("
            final_width = max(max_width, longest_word_width * 1.2)  # 20% margin (same as entity name)
            padding = (3 * 2)  # 3pt padding each side
            margin = 0.5 * cm  # Further reduced margin for second column (0.5cm, same as entity name)
        else:
            # Other columns: standard margin
            final_width = max(max_width, longest_word_width * 1.3)  # 30% margin
            padding = (3 * 2)  # 3pt padding each side
            margin = 1.0 * cm  # Standard margin for all columns (1.0cm)
        return final_width + padding + margin
    
    # Calculate minimum widths for all columns
    # Important: Measure each column with its actual font settings
    col_min_widths = []
    for col_idx in range(num_cols):
        is_entity_name = (col_idx == entity_name_col_idx)
        # Use cell font size (7pt) for all columns, but bold for entity name
        min_width = calculate_column_min_width(col_idx, cell_font_size, is_bold=is_entity_name)
        col_min_widths.append(min_width)
    
    # Priority 1: Entity name column minimum width (if needed, can be prioritized)
    entity_name_min_width = col_min_widths[entity_name_col_idx] if entity_name_col_idx < len(col_min_widths) else 0.0
    
    # Calculate column widths with priority for short columns
    # Strategy: Short columns get minimum width, long columns get remaining space
    total_min_width = sum(col_min_widths)
    
    if total_min_width > available_width:
        # If total minimum width exceeds available space, scale proportionally
        scale_factor = available_width / total_min_width
        col_widths = [min_width * scale_factor for min_width in col_min_widths]
    else:
        # Start with minimum widths for all columns
        col_widths = col_min_widths.copy()
        
        # Calculate remaining space after allocating minimum widths
        remaining_width = available_width - total_min_width
        
        if remaining_width > 0:
            # Calculate average content length for each column to determine additional space allocation
            col_content_scores = []
            for col_idx in range(num_cols):
                # Calculate average content length
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
                
                # Apply weight multipliers: Entity name gets normal weight, columns 2-6 get same weight
                if col_idx == 0:
                    # Entity name: apply weight multiplier (default 0.7 to give it more space)
                    content_score = content_score * content_score_weight_col0
                elif col_idx >= 1:
                    # Columns 2-6: apply same weight multiplier (default 0.5, same for all)
                    content_score = content_score * content_score_weight_col1
                
                col_content_scores.append(content_score)
            
            # Calculate how much extra space each column needs beyond minimum
            # Short columns (low content score) get less extra space, long columns get more
            total_score = sum(col_content_scores)
            if total_score > 0:
                # Allocate remaining space proportionally based on content score
                # But give priority to columns that need more space (higher score)
                for col_idx in range(num_cols):
                    if col_content_scores[col_idx] > 0:
                        # Allocate extra space proportional to content score
                        extra_width = remaining_width * (col_content_scores[col_idx] / total_score)
                        col_widths[col_idx] += extra_width
            else:
                # Fallback: equal distribution of remaining space
                extra_per_column = remaining_width / num_cols
                col_widths = [w + extra_per_column for w in col_widths]
        
        # Final check: Ensure all columns meet their minimum width with additional safety margin
        # This is critical to prevent text overflow like "Syndrome"
        # Priority: Entity name column first, then second column, then others
        # Sort columns by priority: entity name first, second column second, then others
        priority_order = []
        for col_idx in range(num_cols):
            if col_idx == entity_name_col_idx:
                priority_order.insert(0, col_idx)  # Entity name first
            elif col_idx == 1:
                priority_order.insert(1, col_idx)  # Second column second
            else:
                priority_order.append(col_idx)
        
        # Process columns in priority order
        for col_idx in priority_order:
            min_width = col_min_widths[col_idx] if col_idx < len(col_min_widths) else 0.0
            if col_widths[col_idx] < min_width:
                # Force minimum width - this is non-negotiable to prevent overflow
                # Entity name column gets absolute priority
                is_entity_name = (col_idx == entity_name_col_idx)
                width_deficit = min_width - col_widths[col_idx]
                if width_deficit > 0:
                    # Find other columns that can be reduced
                    other_cols = [idx for idx in range(num_cols) if idx != col_idx]
                    other_cols_total_width = sum(col_widths[idx] for idx in other_cols)
                    
                    if other_cols_total_width > 0:
                        # Calculate how much we can reduce from other columns
                        # Ensure we don't reduce below their minimum widths
                        reducible_width = 0.0
                        for idx in other_cols:
                            other_min = col_min_widths[idx] if idx < len(col_min_widths) else 0.0
                            if col_widths[idx] > other_min:
                                reducible_width += (col_widths[idx] - other_min)
                        
                        if reducible_width >= width_deficit:
                            # We can reduce other columns
                            reduction_factor = (other_cols_total_width - width_deficit) / other_cols_total_width
                            # For first 2 columns, be less aggressive (allow less reduction from others)
                            # Since they can break more easily, they need less space
                            if is_entity_name:
                                reduction_factor = max(0.2, reduction_factor)  # Allow up to 80% reduction
                            elif col_idx == 1:
                                reduction_factor = max(0.15, reduction_factor)  # Allow up to 85% reduction for second column
                            else:
                                reduction_factor = max(0.1, reduction_factor)  # Don't reduce too much
                            
                            for idx in other_cols:
                                other_min = col_min_widths[idx] if idx < len(col_min_widths) else 0.0
                                new_width = max(other_min, col_widths[idx] * reduction_factor)
                                col_widths[idx] = new_width
                            
                            # Set this column to minimum width
                            col_widths[col_idx] = min_width
                        else:
                            # Can't reduce enough, but still set to minimum (may cause slight overflow in other columns)
                            # For entity name, this is critical - force it even if others overflow slightly
                            col_widths[col_idx] = min_width
                    else:
                        # No other columns to reduce, set to minimum anyway
                        col_widths[col_idx] = min_width
    
    # Create a special style for entity name column that allows line breaks at & and (
    # Use same font size (8pt) as other columns
    entity_name_style = ParagraphStyle(
        "EntityNameStyle",
        parent=custom_styles["card_text"],
        fontSize=entity_name_font_size,  # 8pt, same as other columns
        fontName=korean_font_bold,
        splitLongWords=True,  # Allow breaking at whitespace, &, and ( (we add <br/> tags)
        allowWidows=0,
        allowOrphans=0,
    )
    
    # Create style for other columns (8pt)
    # Allow word breaking for very long words if necessary to prevent overflow
    cell_style = ParagraphStyle(
        "CellStyle",
        parent=custom_styles["card_text"],
        fontSize=cell_font_size,  # 8pt
        fontName=korean_font,
        splitLongWords=True,  # Allow breaking very long words if they don't fit (like "Syndrome")
        # ReportLab will prefer breaking at whitespace/hyphen first, but will break long words if needed
        allowWidows=0,
        allowOrphans=0,
    )
    
    # Create table data with Paragraph objects for proper Korean rendering
    table_data = []
    # Header row: all headers are bold by default, use 8pt font
    header_style = ParagraphStyle(
        "TableHeaderStyle",
        parent=custom_styles["card_header"],
        fontSize=header_font_size,  # 8pt
        fontName=korean_font_bold,
    )
    header_row = []
    for h in headers:
        header_text = str(h).strip()
        # Parse markdown formatting and ensure bold (header is always bold)
        header_text = sanitize_html_for_reportlab(header_text)
        # If not already bold, wrap in bold tags
        if not ('<b>' in header_text or '</b>' in header_text):
            header_text = f"<b>{header_text}</b>"
        header_row.append(Paragraph(header_text, header_style))
    table_data.append(header_row)
    
    # Data rows
    for row in rows:
        data_row = []
        for col_idx, cell in enumerate(row):
            cell_text = str(cell).strip()
            
            # Entity name column - always bold, allow line breaks at & and (
            if col_idx == entity_name_col_idx:
                # First, parse markdown formatting (convert **text** to <b>text</b>)
                # Do this BEFORE adding <br/> tags to avoid conflicts
                cell_text = parse_markdown_formatting(cell_text)
                
                # Then add line break after "&" or before "(" if present
                # Pattern 1: "&" followed by space (e.g., "질환명 & 영어명") -> "질환명 &<br/> 영어명"
                cell_text = re.sub(r'&\s+', '&<br/>', cell_text)
                # Pattern 2: space before "(" (e.g., "한글명 (영어명)") -> "한글명 <br/>(영어명)"
                cell_text = re.sub(r'\s+\(', '<br/>(', cell_text)
                
                # Sanitize HTML (handles <br/> normalization, etc.)
                cell_text = sanitize_html_for_reportlab(cell_text)
                
                # Ensure bold (row title is always bold)
                # If markdown was already converted to <b> tags, don't wrap again
                if not ('<b>' in cell_text or '</b>' in cell_text):
                    cell_text = f"<b>{cell_text}</b>"
                # Use special style that prevents word breaking
                data_row.append(Paragraph(cell_text, entity_name_style))
            elif col_idx == 1:
                # Second column (질환/개념) - also allow line breaks before "("
                # IMPORTANT: Process markdown FIRST before other processing
                cell_text = parse_markdown_formatting(cell_text)
                
                # Pattern: space before "(" (e.g., "진단 접근 원칙 (Diagnosis Approach)") -> "진단 접근 원칙 <br/>(Diagnosis Approach)"
                cell_text = re.sub(r'\s+\(', '<br/>(', cell_text)
                
                # Apply line break processing for semicolons and commas
                def add_line_breaks_at_delimiters(text):
                    """Add line breaks at semicolons and ensure proper spacing after commas.
                    Preserves HTML tags."""
                    if not text:
                        return text
                    
                    result = []
                    i = 0
                    in_tag = False
                    
                    while i < len(text):
                        char = text[i]
                        
                        if char == '<':
                            # Start of HTML tag
                            in_tag = True
                            result.append(char)
                            i += 1
                        elif char == '>':
                            # End of HTML tag
                            in_tag = False
                            result.append(char)
                            i += 1
                        elif in_tag:
                            # Inside HTML tag, copy as-is
                            result.append(char)
                            i += 1
                        elif char == ';':
                            # Semicolon: always add line break after it (improved: even without space)
                            result.append(';')
                            i += 1
                            if i < len(text):
                                if text[i] == ' ':
                                    # Space after semicolon: replace with line break
                                    result.append('<br/>')
                                    i += 1
                                elif text[i] != '\n' and text[i] != '<':
                                    # No space but not newline or HTML tag start: add line break anyway
                                    result.append('<br/>')
                                # If newline or HTML tag, don't add <br/> (already handled)
                            else:
                                # Semicolon at end: add line break
                                result.append('<br/>')
                        elif char == ',':
                            # Comma outside HTML tag
                            result.append(',')
                            i += 1
                            # Always ensure space after comma (even if already present, normalize it)
                            # This makes comma+space a clear line break opportunity
                            if i >= len(text):
                                # Comma at end, no space needed
                                pass
                            elif text[i] == ' ':
                                # Space already exists, keep it (ReportLab will break here if needed)
                                result.append(' ')
                                i += 1
                            elif text[i] == '\n':
                                # Newline already exists, keep it
                                result.append('\n')
                                i += 1
                            else:
                                # No space after comma, add one
                                result.append(' ')
                        else:
                            # Regular character
                            result.append(char)
                            i += 1
                    
                    return ''.join(result)
                
                # Apply line break processing (after markdown is converted to HTML)
                cell_text = add_line_breaks_at_delimiters(cell_text)
                
                # Apply automatic bolding to important terms (medical abbreviations, numbers with units, etc.)
                # This is called AFTER markdown processing, so it works with HTML tags
                cell_text = bold_important_terms(cell_text)
                
                # Sanitize HTML (handles <br/> normalization, etc.)
                cell_text = sanitize_html_for_reportlab(cell_text)
                
                # Use cell style with 8pt font
                data_row.append(Paragraph(cell_text, cell_style))
            else:
                # Other columns: process markdown first, then apply formatting
                # IMPORTANT: Process markdown FIRST before other processing
                cell_text = parse_markdown_formatting(cell_text)
                
                # Add line breaks at semicolons (after markdown is converted to HTML)
                def add_line_breaks_at_delimiters(text):
                    """Add line breaks at semicolons (primary: "; " per prompt spec) and ensure proper spacing after commas.
                    Preserves HTML tags."""
                    if not text:
                        return text
                    
                    result = []
                    i = 0
                    in_tag = False
                    
                    while i < len(text):
                        char = text[i]
                        
                        if char == '<':
                            # Start of HTML tag
                            in_tag = True
                            result.append(char)
                            i += 1
                        elif char == '>':
                            # End of HTML tag
                            in_tag = False
                            result.append(char)
                            i += 1
                        elif in_tag:
                            # Inside HTML tag, copy as-is
                            result.append(char)
                            i += 1
                        elif char == ';':
                            # Semicolon: always add line break after it (improved: even without space)
                            result.append(';')
                            i += 1
                            if i < len(text):
                                if text[i] == ' ':
                                    # Space after semicolon: replace with line break
                                    result.append('<br/>')
                                    i += 1
                                elif text[i] != '\n' and text[i] != '<':
                                    # No space but not newline or HTML tag start: add line break anyway
                                    result.append('<br/>')
                                # If newline or HTML tag, don't add <br/> (already handled)
                            else:
                                # Semicolon at end: add line break
                                result.append('<br/>')
                        elif char == ',':
                            # Comma outside HTML tag
                            result.append(',')
                            i += 1
                            # Always ensure space after comma (even if already present, normalize it)
                            # This makes comma+space a clear line break opportunity
                            if i >= len(text):
                                # Comma at end, no space needed
                                pass
                            elif text[i] == ' ':
                                # Space already exists, keep it (ReportLab will break here if needed)
                                result.append(' ')
                                i += 1
                            elif text[i] == '\n':
                                # Newline already exists, keep it
                                result.append('\n')
                                i += 1
                            else:
                                # No space after comma, add one
                                result.append(' ')
                        else:
                            # Regular character
                            result.append(char)
                            i += 1
                    
                    return ''.join(result)
                
                # Apply line break processing (after markdown is converted to HTML)
                # Primary: semicolons with space ("; ") cause line breaks per prompt spec
                # Secondary: commas with space are also break points (ReportLab breaks at whitespace)
                cell_text = add_line_breaks_at_delimiters(cell_text)
                
                # Apply automatic bolding to important terms (medical abbreviations, numbers with units, etc.)
                # This is called AFTER markdown processing, so it works with HTML tags
                cell_text = bold_important_terms(cell_text)
                
                # Sanitize HTML (handles <br/> normalization, etc.)
                cell_text = sanitize_html_for_reportlab(cell_text)
                
                # Use cell style with 8pt font
                # splitLongWords=True allows breaking long words if needed
                # Semicolon+space ("; ") is the primary break point per prompt spec
                data_row.append(Paragraph(cell_text, cell_style))
        table_data.append(data_row)
    
    # Create table with dynamic column widths
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    # Build table style list with conditional font size rules
    table_style_list = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E0E0E0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), korean_font_bold),
        ("FONTSIZE", (0, 0), (-1, 0), header_font_size),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
        ("TOPPADDING", (0, 0), (-1, 0), 3),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
        ("FONTNAME", (0, 1), (-1, -1), korean_font),
        # All cells use 8pt font size (via ParagraphStyle, but set here for consistency)
        ("FONTSIZE", (0, 1), (-1, -1), cell_font_size),  # All data cells: 8pt
        ("FONTNAME", (entity_name_col_idx, 1), (entity_name_col_idx, -1), korean_font_bold),  # Entity name uses bold
    ]
    
    # Add remaining style rules
    table_style_list.extend([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 1), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 2),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
    ])
    
    table.setStyle(TableStyle(table_style_list))
    
    story.append(table)


def optimize_image_for_pdf(
    pil_img: PILImage.Image,
    target_width_pt: float,
    target_height_pt: float,
    max_dpi: float = 200.0,
    jpeg_quality: int = 90,
) -> BytesIO:
    """
    Optimize image for PDF: resize to target dimensions and compress.
    
    Args:
        pil_img: PIL Image object
        target_width_pt: Target width in points (1/72 inch)
        target_height_pt: Target height in points
        max_dpi: Maximum DPI for the image (default 200, good for medical images)
        jpeg_quality: JPEG quality 1-100 (default 90, high quality for medical detail)
    
    Returns:
        BytesIO object containing optimized JPEG image
    
    Note:
        - Medical images require higher quality to preserve diagnostic details
        - 200 DPI is suitable for both digital viewing and potential printing
        - JPEG quality 90 provides excellent quality with reasonable file size
        - Original images: Card images (1024x1280), Table visuals (4K)
    """
    # Convert points to pixels (1 point = 1/72 inch)
    target_width_px = int(target_width_pt * max_dpi / 72.0)
    target_height_px = int(target_height_pt * max_dpi / 72.0)
    
    # Resize image if larger than target (downscale only, never upscale)
    if pil_img.size[0] > target_width_px or pil_img.size[1] > target_height_px:
        # Maintain aspect ratio
        img_aspect = pil_img.size[1] / pil_img.size[0]
        target_aspect = target_height_px / target_width_px
        
        if img_aspect > target_aspect:
            # Image is taller, fit to height
            new_height = target_height_px
            new_width = int(new_height / img_aspect)
        else:
            # Image is wider, fit to width
            new_width = target_width_px
            new_height = int(new_width * img_aspect)
        
        pil_img = pil_img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
    
    # Convert to RGB if necessary (JPEG doesn't support transparency)
    if pil_img.mode in ('RGBA', 'LA', 'P'):
        rgb_img = PILImage.new('RGB', pil_img.size, (255, 255, 255))
        if pil_img.mode == 'P':
            pil_img = pil_img.convert('RGBA')
        rgb_img.paste(pil_img, mask=pil_img.split()[-1] if pil_img.mode in ('RGBA', 'LA') else None)
        pil_img = rgb_img
    elif pil_img.mode != 'RGB':
        pil_img = pil_img.convert('RGB')
    
    # Save to BytesIO as JPEG
    output = BytesIO()
    pil_img.save(output, format='JPEG', quality=jpeg_quality, optimize=True)
    output.seek(0)
    return output


def build_infographic_section(
    story: List,
    image_path: Optional[str],
    custom_styles: Dict[str, ParagraphStyle],
    allow_missing: bool = False,
    page_width: Optional[float] = None,
    page_height: Optional[float] = None,
    optimize_images: bool = True,
    image_max_dpi: float = 150.0,  # 150 DPI for infographics (4K source, digital viewing)
    image_jpeg_quality: int = 90,
    s1_record: Optional[Dict[str, Any]] = None,
    korean_font_bold: Optional[str] = None,
) -> None:
    """Build Infographic section - full page, with header."""
    
    # Add header info at top left (same format as Learning Objectives)
    if s1_record and korean_font_bold:
        specialty, anatomy, modality_or_type, category = parse_group_path_from_s1(s1_record)
        
        # Build header text (same format as Learning Objectives: " > " separator)
        header_parts = []
        if specialty:
            header_parts.append(specialty)
        if anatomy:
            header_parts.append(anatomy)
        if modality_or_type:
            header_parts.append(modality_or_type)
        if category:
            header_parts.append(category)
        
        header_text = " > ".join(header_parts) if header_parts else ""
        
        # Section label at top left (same style as Learning Objectives)
        section_label_style = ParagraphStyle(
            "SectionLabel",
            parent=custom_styles["header_small"],
            fontSize=12,
            textColor=colors.HexColor("#666666"),
            spaceAfter=8,
            fontName=korean_font_bold,
            alignment=TA_LEFT,
        )
        if header_text:
            story.append(Paragraph(f"{header_text} | Infographic", section_label_style))
        else:
            story.append(Paragraph("Infographic", section_label_style))
        
        story.append(Spacer(1, 0.3 * cm))
    
    if image_path:
        image_path_obj = Path(image_path)
        if image_path_obj.exists():
            try:
                # Load image to get actual dimensions
                pil_img = PILImage.open(image_path)
                img_width_px, img_height_px = pil_img.size
                aspect_ratio = img_height_px / img_width_px if img_width_px > 0 else 9/16
                
                # Use full page size minus margins for landscape mode (reduced margins for digital viewing)
                if page_width is not None and page_height is not None:
                    max_width = page_width - (1.5 * cm)  # margins
                    max_height = page_height - (1.5 * cm)  # margins
                    # Fit image to page while maintaining aspect ratio
                    if max_width * aspect_ratio <= max_height:
                        img_width = max_width
                        img_height = img_width * aspect_ratio
                    else:
                        img_height = max_height
                        img_width = img_height / aspect_ratio
                else:
                    img_width = 16 * cm
                    img_height = img_width * aspect_ratio
                
                # Optimize image for PDF if enabled
                if optimize_images:
                    optimized_img = optimize_image_for_pdf(pil_img, img_width, img_height, max_dpi=image_max_dpi, jpeg_quality=image_jpeg_quality)
                    img = RLImage(optimized_img, width=img_width, height=img_height)
                else:
                    # Use absolute path for reportlab (no optimization)
                    abs_path = str(image_path_obj.resolve())
                    img = RLImage(abs_path, width=img_width, height=img_height)
                story.append(img)
            except Exception as e:
                if allow_missing:
                    story.append(Paragraph("(IMAGE MISSING)", custom_styles["card_text"]))
                else:
                    raise RuntimeError(f"Failed to load infographic image: {e}")
        else:
            if allow_missing:
                story.append(Paragraph("(IMAGE MISSING)", custom_styles["card_text"]))
            else:
                raise RuntimeError(f"Infographic image file not found: {image_path}")
    else:
        if allow_missing:
            story.append(Paragraph("(IMAGE MISSING)", custom_styles["card_text"]))
        else:
            raise RuntimeError(f"Infographic image not found: {image_path}")
    
    story.append(Spacer(1, 0.5 * cm))


def build_cards_section(
    story: List,
    s2_records: List[Dict[str, Any]],
    policy_mapping: Dict[Tuple[str, str], Dict[str, Any]],
    image_mapping: Dict[Tuple[str, Optional[str], Optional[str]], str],
    custom_styles: Dict[str, ParagraphStyle],
    page_width: float,
    page_height: float,
    allow_missing_images: bool = False,
    optimize_images: bool = True,
    image_max_dpi: float = 200.0,
    image_jpeg_quality: int = 90,
    s5_card_validations: Optional[Dict[str, Dict[str, Any]]] = None,
) -> None:
    """Build Cards section (12 cards expected) - 2 column layout: text left, image right."""
    
    # Collect all cards in stable order: entity order from S1, then card_role Q1->Q2
    # Note: Preserve original card index for card_id matching with S5 validation
    all_cards = []
    for s2_record in s2_records:
        entity_id = s2_record.get("entity_id", "")
        entity_name = s2_record.get("entity_name", "")
        anki_cards = s2_record.get("anki_cards", [])
        
        # Sort cards by card_role (Q1, Q2) but preserve original index
        sorted_cards_with_idx = sorted(
            enumerate(anki_cards),
            key=lambda x: x[1].get("card_role", "")
        )
        
        for card_idx, card in sorted_cards_with_idx:
            card_role = card.get("card_role", "")
            # Generate card_id in same format as S5 validator: {entity_id}__{card_role}__{card_idx}
            card_id = card.get("card_id")
            if not card_id:
                card_id = f"{entity_id}__{card_role}__{card_idx}"
            all_cards.append({
                "entity_id": entity_id,
                "entity_name": entity_name,
                "card_role": card_role,
                "card": card,
                "card_id": card_id,  # Store card_id for S5 matching
            })
    
    # Validate card count (warn if unexpected, but allow flexible counts)
    if len(all_cards) == 0:
        raise RuntimeError("No cards found in S2 results")
    elif len(all_cards) != 12:
        # S0 typically expects 12 cards (6 entities × 2 cards), but allow flexible counts
        print(f"[PDF Builder] Warning: Expected 12 cards (S0 standard), found {len(all_cards)} cards. Continuing anyway.")
        if not allow_missing_images and len(all_cards) < 4:
            # Only fail if very few cards (likely data issue)
            raise RuntimeError(f"Too few cards found: {len(all_cards)} (expected at least 4)")
    
    # Calculate column widths for 2-column layout (reduced margins for digital viewing)
    available_width = page_width - (1.5 * cm)  # margins
    text_col_width = available_width * 0.5  # Left column for text
    image_col_width = available_width * 0.5  # Right column for image
    
    # Render each card in 2-column layout
    for card_info in all_cards:
        entity_id = card_info["entity_id"]
        entity_name = card_info["entity_name"]
        card_role = card_info["card_role"]
        card = card_info["card"]
        
        # Get policy
        policy = policy_mapping.get((entity_id, card_role), {})
        image_placement = policy.get("image_placement", "NONE")
        card_type = policy.get("card_type", "BASIC")
        image_required = policy.get("image_required", False)
        
        # Prepare left column content (text)
        left_content = []
        header_text = f"Entity: {entity_name} | Role: {card_role} | Type: {card_type}"
        left_content.append(Paragraph(header_text, custom_styles["card_header"]))
        left_content.append(Spacer(1, 0.2 * cm))
        
        # Question (front text)
        front_text = card.get("front", "").strip()
        if front_text:
            left_content.append(Paragraph("Q:", custom_styles["card_label"]))
            # Sanitize HTML before passing to Paragraph
            front_text_sanitized = sanitize_html_for_reportlab(front_text)
            try:
                left_content.append(Paragraph(front_text_sanitized, custom_styles["card_text"]))
            except (ValueError, Exception) as e:
                # If HTML parsing fails, try more aggressive sanitization
                plain_text = re.sub(r'<[^>]+>', '', front_text_sanitized)
                plain_text = plain_text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                try:
                    left_content.append(Paragraph(plain_text, custom_styles["card_text"]))
                except:
                    left_content.append(Paragraph("(Question formatting error)", custom_styles["card_text"]))
            left_content.append(Spacer(1, 0.2 * cm))
        
        # Options (for MCQ cards)
        card_type = card.get("card_type", "").strip().upper()
        if card_type in ("MCQ", "MCQ_VIGNETTE"):
            options = card.get("options", [])
            if isinstance(options, list) and len(options) > 0:
                left_content.append(Paragraph("Options:", custom_styles["card_label"]))
                option_labels = ["A", "B", "C", "D", "E"]
                for i, option in enumerate(options[:5]):
                    label = option_labels[i] if i < len(option_labels) else str(i + 1)
                    # Sanitize HTML before passing to Paragraph
                    option_sanitized = sanitize_html_for_reportlab(option)
                    option_text = f"{label}. {option_sanitized}"
                    try:
                        left_content.append(Paragraph(option_text, custom_styles["card_text"]))
                    except (ValueError, Exception) as e:
                        # If HTML parsing fails, use plain text
                        plain_text = re.sub(r'<[^>]+>', '', option_sanitized)
                        plain_text = plain_text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                        try:
                            left_content.append(Paragraph(f"{label}. {plain_text}", custom_styles["card_text"]))
                        except:
                            left_content.append(Paragraph(f"{label}. (Option formatting error)", custom_styles["card_text"]))
                left_content.append(Spacer(1, 0.3 * cm))
        
        # Answer/explanation (back text)
        back_text = card.get("back", "").strip()
        if back_text:
            left_content.append(Paragraph("A:", custom_styles["card_label"]))
            
            # Parse back text to handle bullets and sections with proper line breaks
            lines = back_text.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Sanitize HTML before processing
                line_sanitized = sanitize_html_for_reportlab(line)
                
                # Check if it's a bullet point (starts with *, -, •, or numbered)
                if line.startswith("* ") or line.startswith("- ") or line.startswith("• "):
                    # Bullet point - remove marker and add as indented paragraph
                    bullet_text = line_sanitized[2:].strip() if len(line_sanitized) > 2 else line_sanitized.strip()
                    if bullet_text:
                        # Use leftIndent for bullet indentation
                        bullet_style = ParagraphStyle(
                            "BulletStyle",
                            parent=custom_styles["card_text"],
                            leftIndent=0.5 * cm,
                            bulletIndent=0.2 * cm,
                        )
                        try:
                            left_content.append(Paragraph(f"• {bullet_text}", bullet_style))
                        except (ValueError, Exception) as e:
                            # Fallback for bullet text
                            plain_text = re.sub(r'<[^>]+>', '', bullet_text)
                            plain_text = plain_text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                            try:
                                left_content.append(Paragraph(f"• {plain_text}", bullet_style))
                            except:
                                left_content.append(Paragraph("• (Text formatting error)", bullet_style))
                elif re.match(r'^\d+[\.\)]\s', line_sanitized):
                    # Numbered list item
                    try:
                        left_content.append(Paragraph(line_sanitized, custom_styles["card_text"]))
                    except (ValueError, Exception) as e:
                        plain_text = re.sub(r'<[^>]+>', '', line_sanitized)
                        plain_text = plain_text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                        left_content.append(Paragraph(plain_text, custom_styles["card_text"]))
                elif line_sanitized.endswith(":") and any(keyword in line_sanitized for keyword in ["근거", "함정", "감별", "오답", "포인트", "암기", "팁", "Answer", "정답"]):
                    # Section header (e.g., "근거:", "함정/감별:", "Answer:")
                    try:
                        left_content.append(Paragraph(line_sanitized, custom_styles["card_label"]))
                    except (ValueError, Exception) as e:
                        plain_text = re.sub(r'<[^>]+>', '', line_sanitized)
                        plain_text = plain_text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                        left_content.append(Paragraph(plain_text, custom_styles["card_label"]))
                else:
                    # Regular text
                    # Try to create paragraph, with fallback if HTML parsing fails
                    try:
                        left_content.append(Paragraph(line_sanitized, custom_styles["card_text"]))
                    except (ValueError, Exception) as e:
                        # If HTML parsing fails, try more aggressive sanitization
                        # Remove all HTML tags and use plain text
                        plain_text = re.sub(r'<[^>]+>', '', line_sanitized)
                        # Also remove HTML entities
                        plain_text = plain_text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                        try:
                            left_content.append(Paragraph(plain_text, custom_styles["card_text"]))
                        except:
                            # Last resort: use minimal text
                            left_content.append(Paragraph("(Text formatting error)", custom_styles["card_text"]))
        
        # Prepare right column content (image)
        right_content = []
        # Normalize entity_id: convert colon to underscore to match image filename format
        # (S2 records use DERIVED:xxx but image filenames use DERIVED_xxx)
        normalized_entity_id = str(entity_id).replace(":", "_") if entity_id else None
        
        # Q1 and Q2 each have their own image (no reuse).
        # Try S2_CARD_IMAGE first, then S2_CARD_CONCEPT (both are card images)
        lookup_key = ("S2_CARD_IMAGE", normalized_entity_id, card_role)
        if lookup_key not in image_mapping:
            lookup_key = ("S2_CARD_CONCEPT", normalized_entity_id, card_role)
        image_path = image_mapping.get(lookup_key)
        
        if image_path and (image_placement in ("FRONT", "BACK")):
            image_path_obj = Path(image_path)
            if image_path_obj.exists():
                try:
                    # Load image to get dimensions
                    pil_img = PILImage.open(image_path)
                    img_width_px, img_height_px = pil_img.size
                    aspect_ratio = img_height_px / img_width_px if img_width_px > 0 else 4/5
                    
                    # Fit image to right column width
                    img_width = image_col_width - (0.5 * cm)  # small margin
                    img_height = img_width * aspect_ratio
                    
                    # Optimize image for PDF if enabled
                    if optimize_images:
                        optimized_img = optimize_image_for_pdf(pil_img, img_width, img_height, max_dpi=image_max_dpi, jpeg_quality=image_jpeg_quality)
                        img = RLImage(optimized_img, width=img_width, height=img_height)
                    else:
                        # Use absolute path for reportlab (no optimization)
                        abs_path = str(image_path_obj.resolve())
                        img = RLImage(abs_path, width=img_width, height=img_height)
                    right_content.append(img)
                except Exception as e:
                    if image_required and not allow_missing_images:
                        raise RuntimeError(f"Failed to load image for {entity_id}/{card_role}: {e}")
                    elif allow_missing_images:
                        right_content.append(Paragraph("(IMAGE MISSING)", custom_styles["card_text"]))
            else:
                if image_required and not allow_missing_images:
                    raise RuntimeError(f"Image file not found: {image_path}")
                elif allow_missing_images:
                    right_content.append(Paragraph("(IMAGE MISSING)", custom_styles["card_text"]))
        elif image_required and not allow_missing_images:
            raise RuntimeError(f"Image required but missing in mapping for {entity_id}/{card_role} (key: {lookup_key})")
        elif allow_missing_images and image_placement != "NONE":
            right_content.append(Paragraph("(IMAGE MISSING)", custom_styles["card_text"]))
        
        # Create 2-column table
        card_table_data = [
            [left_content, right_content]
        ]
        
        card_table = Table(
            card_table_data,
            colWidths=[text_col_width, image_col_width],
        )
        card_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 0.5 * cm),
                ("LEFTPADDING", (1, 0), (1, -1), 0.5 * cm),
                ("RIGHTPADDING", (1, 0), (1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0.3 * cm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0.3 * cm),
            ])
        )
        
        story.append(card_table)
        story.append(Spacer(1, 0.3 * cm))
        
        # Add S5 validation for this specific card (if available)
        if s5_card_validations:
            # Use stored card_id (generated in same format as S5 validator)
            card_id = card_info.get("card_id", "")
            card_validation = s5_card_validations.get(card_id) if card_id else None
            if card_validation:
                # Compact card validation display
                # Use font from custom_styles (korean_font may not be available in this scope)
                font_name = custom_styles["card_text"].fontName
                validation_style = ParagraphStyle(
                    "CardValidation",
                    parent=custom_styles["card_text"],
                    fontSize=8,
                    textColor=colors.HexColor("#666666"),
                    spaceAfter=4,
                    fontName=font_name,
                    leftIndent=0.5 * cm,
                )
                
                blocking = card_validation.get("blocking_error", False)
                ta = card_validation.get("technical_accuracy", 0.0)
                eq = card_validation.get("educational_quality", 0)
                issues = card_validation.get("issues", [])
                
                status_color = "red" if blocking else ("orange" if ta < 0.8 else "black")
                status_text = "BLOCKING" if blocking else "OK" if ta >= 0.8 and eq >= 4 else "NEEDS_REVIEW"
                
                validation_text = f"<font color='{status_color}'>[S5] {status_text}</font> | TA: {ta:.2f} | EQ: {eq}/5"
                if issues:
                    validation_text += f" | Issues: {len(issues)}"
                
                story.append(Paragraph(validation_text, validation_style))
                
                # Show first issue if blocking or if there are issues
                if blocking or (issues and len(issues) > 0):
                    issue = issues[0]
                    issue_type = issue.get("type", "unknown")
                    issue_desc = issue.get("description", "")
                    if issue_desc:
                        issue_desc_truncated = issue_desc[:100] if len(issue_desc) > 100 else issue_desc
                        issue_desc_truncated = sanitize_html_for_reportlab(issue_desc_truncated)
                        if len(issue_desc) > 100:
                            story.append(Paragraph(f"  → [{issue_type}] {issue_desc_truncated}...", validation_style))
                        else:
                            story.append(Paragraph(f"  → [{issue_type}] {issue_desc_truncated}", validation_style))
        
        story.append(PageBreak())


def build_s5_s1_validation_section(
    story: List,
    s5_record: Dict[str, Any],
    custom_styles: Dict[str, ParagraphStyle],
    korean_font: str,
    korean_font_bold: str,
    s1_record: Optional[Dict[str, Any]] = None,
) -> None:
    """Build S5 S1 Table Validation section (compact, for inline placement after Master Table)."""
    s1_validation = s5_record.get("s1_table_validation", {})
    
    s1_blocking = s1_validation.get("blocking_error", False)
    s1_ta = s1_validation.get("technical_accuracy", 0.0)
    s1_eq = s1_validation.get("educational_quality", 0)
    s1_issues = s1_validation.get("issues", [])
    
    summary_style = ParagraphStyle(
        "SummaryText",
        parent=custom_styles["card_text"],
        fontSize=9,
        textColor=colors.black,
        spaceAfter=6,
        fontName=korean_font,
    )
    
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("<b>S5 Table Validation</b>", summary_style))
    story.append(Paragraph(f"  Blocking Error: <font color='{'red' if s1_blocking else 'black'}'>{'Yes' if s1_blocking else 'No'}</font>", summary_style))
    story.append(Paragraph(f"  Technical Accuracy: {s1_ta:.2f}", summary_style))
    story.append(Paragraph(f"  Educational Quality: {s1_eq}/5", summary_style))
    story.append(Paragraph(f"  Issues Found: {len(s1_issues)}", summary_style))
    
    if s1_issues:
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph("<b>  Top Issues:</b>", summary_style))
        for i, issue in enumerate(s1_issues[:3], 1):  # Show top 3 issues
            issue_type = issue.get("type", "unknown")
            issue_desc_full = issue.get("description", "")
            # Truncate to 200 chars (was 150, but display up to 200)
            issue_desc_truncated = issue_desc_full[:200] if len(issue_desc_full) > 200 else issue_desc_full
            if issue_desc_truncated:
                issue_desc_truncated = sanitize_html_for_reportlab(issue_desc_truncated)
                # Only add "..." if text was actually truncated
                if len(issue_desc_full) > 200:
                    story.append(Paragraph(f"    {i}. [{issue_type}] {issue_desc_truncated}...", summary_style))
                else:
                    story.append(Paragraph(f"    {i}. [{issue_type}] {issue_desc_truncated}", summary_style))
    
    story.append(Spacer(1, 0.5 * cm))


def build_s5_s2_validation_section(
    story: List,
    s5_record: Dict[str, Any],
    custom_styles: Dict[str, ParagraphStyle],
    korean_font: str,
    korean_font_bold: str,
    s1_record: Optional[Dict[str, Any]] = None,
) -> None:
    """Build S5 S2 Cards Validation section (compact, for inline placement after Cards section)."""
    s2_validation = s5_record.get("s2_cards_validation", {})
    s2_summary = s2_validation.get("summary", {})
    
    s2_total = s2_summary.get("total_cards", 0)
    s2_blocking = s2_summary.get("blocking_errors", 0)
    s2_mean_ta = s2_summary.get("mean_technical_accuracy", 0.0)
    s2_mean_eq = s2_summary.get("mean_educational_quality", 0.0)
    
    summary_style = ParagraphStyle(
        "SummaryText",
        parent=custom_styles["card_text"],
        fontSize=9,
        textColor=colors.black,
        spaceAfter=6,
        fontName=korean_font,
    )
    
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("<b>S5 Cards Validation</b>", summary_style))
    story.append(Paragraph(f"  Total Cards: {s2_total}", summary_style))
    story.append(Paragraph(f"  Blocking Cards: <font color='{'red' if s2_blocking > 0 else 'black'}'>{s2_blocking}</font>", summary_style))
    story.append(Paragraph(f"  Mean Technical Accuracy: {s2_mean_ta:.2f}", summary_style))
    story.append(Paragraph(f"  Mean Educational Quality: {s2_mean_eq:.1f}/5", summary_style))
    
    # Collect top card issues
    s2_cards = s2_validation.get("cards", [])
    all_card_issues = []
    for card in s2_cards:
        card_issues = card.get("issues", [])
        for issue in card_issues:
            issue_desc_full = issue.get("description", "")
            all_card_issues.append({
                "card_id": card.get("card_id", "unknown"),
                "card_role": card.get("card_role", ""),
                "type": issue.get("type", "unknown"),
                "description": issue_desc_full,  # Store full description, truncate on display
            })
    
    if all_card_issues:
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph("<b>  Top Card Issues:</b>", summary_style))
        for i, issue in enumerate(all_card_issues[:3], 1):  # Show top 3 issues
            card_role = issue.get("card_role", "")
            issue_type = issue.get("type", "unknown")
            issue_desc_full = issue.get("description", "")
            # Truncate to 200 chars for display
            issue_desc_truncated = issue_desc_full[:200] if len(issue_desc_full) > 200 else issue_desc_full
            if issue_desc_truncated:
                issue_desc_truncated = sanitize_html_for_reportlab(issue_desc_truncated)
                # Only add "..." if text was actually truncated
                if len(issue_desc_full) > 200:
                    story.append(Paragraph(f"    {i}. [{card_role}] [{issue_type}] {issue_desc_truncated}...", summary_style))
                else:
                    story.append(Paragraph(f"    {i}. [{card_role}] [{issue_type}] {issue_desc_truncated}", summary_style))
    
    story.append(Spacer(1, 0.5 * cm))


def build_s5_validation_section(
    story: List,
    s5_record: Dict[str, Any],
    custom_styles: Dict[str, ParagraphStyle],
    page_width: float,
    page_height: float,
    korean_font: str,
    korean_font_bold: str,
    s1_record: Optional[Dict[str, Any]] = None,
) -> None:
    """Build S5 Validation Results section (full, for standalone placement)."""
    # Section label
    specialty, anatomy, modality_or_type, category = parse_group_path_from_s1(s1_record) if s1_record else ("", "", "", None)
    header_parts = []
    if specialty:
        header_parts.append(specialty)
    if anatomy:
        header_parts.append(anatomy)
    if modality_or_type:
        header_parts.append(modality_or_type)
    if category:
        header_parts.append(category)
    header_text = " > ".join(header_parts) if header_parts else ""
    
    section_label_style = ParagraphStyle(
        "SectionLabel",
        parent=custom_styles["header_small"],
        fontSize=12,
        textColor=colors.HexColor("#666666"),
        spaceAfter=8,
        fontName=korean_font_bold,
        alignment=TA_LEFT
    )
    if header_text:
        story.append(Paragraph(f"{header_text} | S5 Validation Results", section_label_style))
    else:
        story.append(Paragraph("S5 Validation Results", section_label_style))
    story.append(Spacer(1, 0.3 * cm))
    
    # Build S1 section
    build_s5_s1_validation_section(
        story, s5_record, custom_styles, korean_font, korean_font_bold, s1_record
    )
    
    # Build S2 section
    build_s5_s2_validation_section(
        story, s5_record, custom_styles, korean_font, korean_font_bold, s1_record
    )


def build_single_group_sections(
    *,
    story: List,
    base_dir: Path,
    run_tag: str,
    arm: str,
    s1_arm: Optional[str] = None,
    group_id: str,
    blinded: bool = False,
    surrogate_map: Optional[Dict[Tuple[str, str], str]] = None,
    allow_missing_images: bool = False,
    optimize_images: bool = True,
    image_max_dpi: float = 200.0,
    image_jpeg_quality: int = 90,
    infographic_max_dpi: float = 150.0,
    content_score_weight_col0: float = 0.7,
    content_score_weight_col1: float = 0.5,
    s1_only: bool = False,
    include_s5: bool = False,
    export_manifest: Optional[Dict[str, bool]] = None,
    page_width: float,
    page_height: float,
    custom_styles: Dict[str, ParagraphStyle],
    korean_font: str,
    korean_font_bold: str,
) -> None:
    """
    Build sections for a single group and append to story.
    
    This is used when combining multiple groups into one PDF.
    """
    gen_dir = get_generated_dir(base_dir, run_tag)
    images_dir = get_images_dir(base_dir, run_tag)
    
    # Load data
    s1_arm_actual = (s1_arm or arm).strip().upper() if s1_arm else arm
    paths = resolve_group_variant_paths(
        gen_dir=gen_dir,
        arm=arm,
        s1_arm_actual=s1_arm_actual,
        group_id=group_id,
        export_manifest=export_manifest,
    )
    s1_path = paths["s1_path"]
    s2_path = paths["s2_path"]
    s3_policy_path = paths["s3_policy_path"]
    s4_manifest_path = paths["s4_manifest_path"]
    
    s1_record = load_s1_struct(s1_path, group_id)
    if not s1_record:
        raise RuntimeError(f"S1 record not found for group_id={group_id}")
    
    # S2 results are optional if s1_only mode is enabled
    s2_records = []
    policy_mapping = {}
    image_mapping = {}
    
    if not s1_only:
        s2_records = load_s2_results(s2_path, group_id)
        if s2_records:  # Only load if S2 records exist
            policy_mapping = load_s3_policy_manifest(s3_policy_path, group_id)
            image_mapping = load_s4_image_manifest(s4_manifest_path, group_id, base_dir, run_tag)
    else:
        # In S1-only mode, still try to load image mapping for infographic (S1_TABLE_VISUAL)
        image_mapping = load_s4_image_manifest(s4_manifest_path, group_id, base_dir, run_tag)
    
    # Section 0: Learning Objectives (before Master Table)
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
    
    # Section 1: Master Table (no title, header info at top left)
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
            s1_record,
            content_score_weight_col0=content_score_weight_col0,
            content_score_weight_col1=content_score_weight_col1,
        )
        
        # Add S5 S1 Table Validation inline (if available)
        if include_s5:
            s5_path = paths["s5_path"]
            s5_record = load_s5_validation(s5_path, group_id)
            if s5_record:
                build_s5_s1_validation_section(
                    story,
                    s5_record,
                    custom_styles,
                    korean_font,
                    korean_font_bold,
                    s1_record=s1_record,
                )
        
        story.append(PageBreak())
    
    # Section 2: Infographic(s) (with header, full page per image)
    # Support both single infographic and multiple clustered infographics
    infographic_path = image_mapping.get(("S1_TABLE_VISUAL", None, None))
    if infographic_path:
        # Single infographic (no clustering)
        build_infographic_section(story, infographic_path, custom_styles, allow_missing_images, page_width, page_height, optimize_images, infographic_max_dpi, image_jpeg_quality, s1_record=s1_record, korean_font_bold=korean_font_bold)
        story.append(PageBreak())
    else:
        # Multiple clustered infographics: find all cluster images
        cluster_infographics = []
        for key, path in image_mapping.items():
            spec_kind, cluster_id, _ = key
            if spec_kind == "S1_TABLE_VISUAL" and cluster_id:
                cluster_infographics.append((cluster_id, path))
        
        # Sort by cluster_id for consistent ordering
        cluster_infographics.sort(key=lambda x: x[0])
        
        if cluster_infographics:
            for cluster_id, infographic_path in cluster_infographics:
                build_infographic_section(story, infographic_path, custom_styles, allow_missing_images, page_width, page_height, optimize_images, infographic_max_dpi, image_jpeg_quality, s1_record=s1_record, korean_font_bold=korean_font_bold)
                story.append(PageBreak())
    
    # Load S5 card validations for individual card display (if include_s5 is enabled)
    s5_card_validations = None
    if include_s5:
        s5_path = paths["s5_path"]
        s5_record = load_s5_validation(s5_path, group_id)
        if s5_record:
            s2_validation = s5_record.get("s2_cards_validation", {})
            s2_cards = s2_validation.get("cards", [])
            # Create mapping: card_id -> validation result
            s5_card_validations = {}
            for card_val in s2_cards:
                card_id = card_val.get("card_id", "")
                if card_id:
                    s5_card_validations[card_id] = card_val
    
    # Section 3: Cards (2-column layout: text left, image right)
    # Skip Cards section if S1-only mode (requires S2 results)
    if not s1_only and s2_records:
        build_cards_section(
            story,
            s2_records,
            policy_mapping,
            image_mapping,
            custom_styles,
            page_width,
            page_height,
            allow_missing_images,
            optimize_images,
            image_max_dpi,
            image_jpeg_quality,
            s5_card_validations=s5_card_validations,
        )
        
        # Add S5 S2 Cards Validation summary inline (if available)
        if include_s5 and s5_record:
            build_s5_s2_validation_section(
                story,
                s5_record,
                custom_styles,
                korean_font,
                korean_font_bold,
                s1_record=s1_record,
            )


def build_set_pdf(
    *,
    base_dir: Path,
    run_tag: str,
    arm: str,
    s1_arm: Optional[str] = None,
    group_id: str,
    out_dir: Path,
    blinded: bool = False,
    surrogate_map: Optional[Dict[Tuple[str, str], str]] = None,
    allow_missing_images: bool = False,
    optimize_images: bool = True,
    image_max_dpi: float = 200.0,  # Default for card images
    image_jpeg_quality: int = 90,
    infographic_max_dpi: float = 150.0,  # 150 DPI for infographics (2K source, digital viewing)
    content_score_weight_col0: float = 0.7,  # Content score weight for Entity Name column (default: 0.7, gives more space)
    content_score_weight_col1: float = 0.5,  # Content score weight for columns 2-6 (default: 0.5, same for all)
    s1_only: bool = False,  # If True, skip S2-dependent sections (Cards) and only generate S1 sections
    include_s5: bool = False,  # If True, include S5 validation results section
    export_manifest: Optional[Dict[str, bool]] = None,
) -> Path:
    """
    Build PDF for a single set (group × arm).
    
    Returns:
        Path to generated PDF file
    """
    gen_dir = get_generated_dir(base_dir, run_tag)
    images_dir = get_images_dir(base_dir, run_tag)
    
    # Load data
    # S1 arm: use s1_arm parameter if specified, otherwise use S2 arm
    s1_arm_actual = (s1_arm or arm).strip().upper() if s1_arm else arm
    s1_path = gen_dir / f"stage1_struct__arm{s1_arm_actual}.jsonl"
    # Use path resolver for backward compatibility (supports both new and legacy formats)
    # Pass s1_arm to resolver so it can find the correct S2 results file
    s2_path = resolve_s2_results_path(gen_dir, arm, s1_arm=s1_arm_actual)
    s3_policy_path = gen_dir / f"image_policy_manifest__arm{arm}.jsonl"
    s4_manifest_path = gen_dir / f"s4_image_manifest__arm{arm}.jsonl"
    
    s1_record = load_s1_struct(s1_path, group_id)
    if not s1_record:
        raise RuntimeError(f"S1 record not found for group_id={group_id}")
    
    # S2 results are optional if s1_only mode is enabled
    s2_records = []
    policy_mapping = {}
    image_mapping = {}
    
    if not s1_only:
        s2_records = load_s2_results(s2_path, group_id)
        if not s2_records:
            raise RuntimeError(f"S2 records not found for group_id={group_id}. Use --s1_only to skip S2-dependent sections.")
        
        policy_mapping = load_s3_policy_manifest(s3_policy_path, group_id)
        image_mapping = load_s4_image_manifest(s4_manifest_path, group_id, base_dir, run_tag)
    else:
        # In S1-only mode, still try to load image mapping for infographic (S1_TABLE_VISUAL)
        # This allows infographic to be displayed even without S2/S3/S4
        image_mapping = load_s4_image_manifest(s4_manifest_path, group_id, base_dir, run_tag)
    
    # Determine output filename (include run_tag to avoid overwriting)
    if blinded:
        if surrogate_map:
            surrogate = surrogate_map.get((group_id, arm.upper()))
            if not surrogate:
                raise RuntimeError(f"Surrogate not found for group_id={group_id}, arm={arm}")
            pdf_filename = f"SET_{surrogate}_{run_tag}.pdf"
        else:
            # Fallback: use hash-based surrogate
            import hashlib
            hash_val = hashlib.md5(f"{group_id}_{arm}".encode()).hexdigest()[:8]
            pdf_filename = f"SET_{hash_val}_{run_tag}.pdf"
    else:
        pdf_filename = f"SET_{group_id}_arm{arm}_{run_tag}.pdf"
    
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / pdf_filename
    
    # Create PDF in landscape mode (reduced margins for digital viewing)
    page_size = landscape(A4)
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=page_size,
        rightMargin=0.75 * cm,
        leftMargin=0.75 * cm,
        topMargin=0.75 * cm,
        bottomMargin=0.75 * cm,
        # Enable compression to reduce file size
        # Note: ReportLab doesn't have built-in compression flag, but we optimize images instead
    )
    
    # Calculate page dimensions for table sizing
    page_width = page_size[0]  # landscape A4 width
    page_height = page_size[1]  # landscape A4 height
    
    story = []
    styles, custom_styles, korean_font, korean_font_bold = create_pdf_styles()
    
    # Build sections for this single group
    build_single_group_sections(
        story=story,
        base_dir=base_dir,
        run_tag=run_tag,
        arm=arm,
        s1_arm=s1_arm,
        group_id=group_id,
        blinded=blinded,
        surrogate_map=surrogate_map,
        allow_missing_images=allow_missing_images,
        optimize_images=optimize_images,
        image_max_dpi=image_max_dpi,
        image_jpeg_quality=image_jpeg_quality,
        infographic_max_dpi=infographic_max_dpi,
        content_score_weight_col0=content_score_weight_col0,
        content_score_weight_col1=content_score_weight_col1,
        s1_only=s1_only,
        include_s5=include_s5,
        export_manifest=export_manifest,
        page_width=page_width,
        page_height=page_height,
        custom_styles=custom_styles,
        korean_font=korean_font,
        korean_font_bold=korean_font_bold,
    )
    
    # No footer (evaluators should not see group/arm information)
    doc.build(story)
    
    return pdf_path


# =========================
# CLI
# =========================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build set-level PDF packets for S0 QA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Non-blinded mode (internal debug):
  python 3_Code/src/07_build_set_pdf.py \\
    --base_dir . \\
    --run_tag TEST_S2_V7_20251220_105343 \\
    --arm A \\
    --group_id G0123 \\
    --out_dir 6_Distributions/QA_Packets

  # Blinded mode:
  python 3_Code/src/07_build_set_pdf.py \\
    --base_dir . \\
    --run_tag TEST_S2_V7_20251220_105343 \\
    --arm A \\
    --group_id G0123 \\
    --out_dir 6_Distributions/QA_Packets \\
    --blinded \\
    --set_surrogate_csv 0_Protocol/06_QA_and_Study/QA_Operations/surrogate_map.csv

  # S1-only mode (skip Cards section, only Learning Objectives + Master Table + Infographic):
  python 3_Code/src/07_build_set_pdf.py \\
    --base_dir . \\
    --run_tag S1_CATEGORY_TEST_armE_20251225_111227 \\
    --arm E \\
    --group_id grp_f073599bec \\
    --out_dir 6_Distributions/QA_Packets \\
    --s1_only \\
    --allow_missing_images

  # Process all groups in a run_tag (omit --group_id):
  python 3_Code/src/07_build_set_pdf.py \\
    --base_dir . \\
    --run_tag S1_CATEGORY_TEST_armE_20251225_111227 \\
    --arm E \\
    --out_dir 6_Distributions/QA_Packets \\
    --s1_only \\
    --allow_missing_images

Expected output:
  - Non-blinded: 6_Distributions/QA_Packets/SET_G0123_armA.pdf
  - Blinded: 6_Distributions/QA_Packets/SET_<surrogate>.pdf
  - S1-only: 6_Distributions/QA_Packets/SET_<group_id>_armE.pdf (without Cards section)

Basic checks:
  - Page count > 0
  - Contains "Master Table" section
  - Contains "Infographic" section (if available)
  - Contains "Cards" section (only if not --s1_only mode)
  - Exactly 12 cards (only if not --s1_only mode)
        """,
    )
    
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument("--run_tag", type=str, required=True, help="Run tag (e.g., TEST_S2_V7_20251220_105343)")
    parser.add_argument("--arm", type=str, required=True, help="Arm identifier (A-F) - S2 execution arm")
    parser.add_argument("--s1_arm", type=str, default=None, help="S1 arm to use for reading S1 output (defaults to --arm if not specified)")
    parser.add_argument("--group_id", type=str, default=None, help="Group ID (e.g., G0123). If not specified, processes all groups in the run_tag.")
    parser.add_argument("--out_dir", type=str, default="6_Distributions/QA_Packets", help="Output directory")
    parser.add_argument("--blinded", action="store_true", help="Enable blinded mode (strip provenance cues)")
    parser.add_argument(
        "--set_surrogate_csv",
        type=str,
        default="0_Protocol/06_QA_and_Study/QA_Operations/surrogate_map.csv",
        help="Path to surrogate mapping CSV (for blinded mode)",
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
        help="Optimize images for PDF (resize and compress, default: True)",
    )
    parser.add_argument(
        "--no_optimize_images",
        dest="optimize_images",
        action="store_false",
        help="Disable image optimization (may result in larger PDF files)",
    )
    parser.add_argument(
        "--image_max_dpi",
        type=float,
        default=200.0,
        help="Maximum DPI for card images (default: 200.0, good for medical images and potential printing)",
    )
    parser.add_argument(
        "--infographic_max_dpi",
        type=float,
        default=150.0,
        help="Maximum DPI for infographic images (default: 150.0, sufficient for 4K source and digital viewing)",
    )
    parser.add_argument(
        "--image_jpeg_quality",
        type=int,
        default=90,
        help="JPEG quality 1-100 (default: 90, high quality for medical detail preservation)",
    )
    parser.add_argument(
        "--content_score_weight_col0",
        type=float,
        default=0.7,
        help="Content score weight multiplier for Entity Name column (default: 0.7, gives more space)",
    )
    parser.add_argument(
        "--content_score_weight_col1",
        type=float,
        default=0.5,
        help="Content score weight multiplier for columns 2-6 (default: 0.5, same for all columns)",
    )
    parser.add_argument(
        "--s1_only",
        action="store_true",
        help="S1-only mode: Skip S2-dependent sections (Cards) and only generate Learning Objectives, Master Table, and Infographic sections. Useful when only S1 data is available.",
    )
    parser.add_argument(
        "--include_s5",
        action="store_true",
        help="Include S5 validation results section in PDF (shows validation summary for the group)",
    )
    parser.add_argument(
        "--export_manifest_path",
        type=str,
        default=None,
        help="Optional S6 export manifest JSON. If provided, per-group inputs will be selected as baseline vs __repaired variants.",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    surrogate_map = None
    export_manifest = None

    if args.export_manifest_path:
        manifest_path_obj = Path(args.export_manifest_path)
        export_manifest_path = (
            manifest_path_obj.resolve()
            if manifest_path_obj.is_absolute()
            else (base_dir / manifest_path_obj).resolve()
        )
        export_manifest = load_export_manifest(export_manifest_path)
        print(
            f"[PDF Builder] Loaded export manifest: {export_manifest_path} ({len(export_manifest)} group entries)"
        )
    
    if args.blinded:
        surrogate_csv_path = base_dir / args.set_surrogate_csv
        surrogate_map = load_surrogate_map(surrogate_csv_path)
        if not surrogate_map:
            print(f"Warning: Surrogate map not found at {surrogate_csv_path}, using hash-based surrogate")
    
    # If group_id is not specified, process all groups in the run_tag and combine into one PDF
    if args.group_id is None:
        gen_dir = get_generated_dir(base_dir, args.run_tag)
        s1_arm_actual = (args.s1_arm or args.arm).strip().upper() if args.s1_arm else args.arm
        s1_path = gen_dir / f"stage1_struct__arm{s1_arm_actual}.jsonl"
        
        if not s1_path.exists():
            print(f"[PDF Builder] ERROR: S1 file not found: {s1_path}", file=sys.stderr)
            print(f"[PDF Builder] Please specify --group_id or ensure the run_tag has S1 data.", file=sys.stderr)
            sys.exit(1)
        
        group_ids = list_all_group_ids(s1_path)
        if not group_ids:
            print(f"[PDF Builder] ERROR: No groups found in {s1_path}", file=sys.stderr)
            sys.exit(1)
        
        print(f"[PDF Builder] Found {len(group_ids)} groups in run_tag {args.run_tag}")
        print(f"[PDF Builder] Combining all groups into one PDF: {', '.join(group_ids)}")
        
        # Determine output filename for combined PDF
        if args.blinded:
            # For blinded mode, use a generic name
            pdf_filename = f"ALL_GROUPS_arm{args.arm.upper()}_{args.run_tag}.pdf"
        else:
            pdf_filename = f"ALL_GROUPS_arm{args.arm.upper()}_{args.run_tag}.pdf"
        
        out_dir.mkdir(parents=True, exist_ok=True)
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
        
        # Calculate page dimensions
        page_width = page_size[0]
        page_height = page_size[1]
        
        story = []
        styles, custom_styles, korean_font, korean_font_bold = create_pdf_styles()
        
        # Process each group and add to story
        success_count = 0
        error_count = 0
        
        for idx, group_id in enumerate(group_ids):
            try:
                print(f"[PDF Builder] Processing group {idx + 1}/{len(group_ids)}: {group_id}")
                build_single_group_sections(
                    story=story,
                    base_dir=base_dir,
                    run_tag=args.run_tag,
                    arm=args.arm.upper(),
                    s1_arm=args.s1_arm.upper() if args.s1_arm else None,
                    group_id=group_id,
                    blinded=args.blinded,
                    surrogate_map=surrogate_map,
                    allow_missing_images=args.allow_missing_images,
                    optimize_images=args.optimize_images,
                    image_max_dpi=args.image_max_dpi,
                    image_jpeg_quality=args.image_jpeg_quality,
                    infographic_max_dpi=args.infographic_max_dpi,
                    content_score_weight_col0=args.content_score_weight_col0,
                    content_score_weight_col1=args.content_score_weight_col1,
                    s1_only=args.s1_only,
                    include_s5=args.include_s5,
                    export_manifest=export_manifest,
                    page_width=page_width,
                    page_height=page_height,
                    custom_styles=custom_styles,
                    korean_font=korean_font,
                    korean_font_bold=korean_font_bold,
                )
                # Add page break between groups (except after last group)
                if idx < len(group_ids) - 1:
                    story.append(PageBreak())
                success_count += 1
            except Exception as e:
                print(f"[PDF Builder] ✗ ERROR for group_id={group_id}: {e}", file=sys.stderr)
                error_count += 1
                if not args.allow_missing_images:
                    import traceback
                    traceback.print_exc()
        
        # Build the combined PDF
        if success_count > 0:
            doc.build(story)
            print(f"\n[PDF Builder] ✓ Successfully created combined PDF: {pdf_path.name}")
            print(f"[PDF Builder] Summary: {success_count} groups succeeded, {error_count} failed")
        else:
            print(f"\n[PDF Builder] ERROR: No groups were successfully processed", file=sys.stderr)
            sys.exit(1)
        
        print(f"[PDF Builder] Output directory: {out_dir}")
        print(f"[PDF Builder] Blinded mode: {args.blinded}")
        
        if error_count > 0:
            print(f"[PDF Builder] Warning: {error_count} groups failed, but PDF was created with successful groups.", file=sys.stderr)
    else:
        # Single group mode
        try:
            pdf_path = build_set_pdf(
                base_dir=base_dir,
                run_tag=args.run_tag,
                arm=args.arm.upper(),
                s1_arm=args.s1_arm.upper() if args.s1_arm else None,
                group_id=args.group_id,
                out_dir=out_dir,
                blinded=args.blinded,
                surrogate_map=surrogate_map,
                allow_missing_images=args.allow_missing_images,
                optimize_images=args.optimize_images,
                image_max_dpi=args.image_max_dpi,
                image_jpeg_quality=args.image_jpeg_quality,
                infographic_max_dpi=args.infographic_max_dpi,
                content_score_weight_col0=args.content_score_weight_col0,
                content_score_weight_col1=args.content_score_weight_col1,
                s1_only=args.s1_only,
                include_s5=args.include_s5,
                export_manifest=export_manifest,
            )
            
            print(f"[PDF Builder] Successfully created: {pdf_path}")
            print(f"[PDF Builder] Output directory: {out_dir}")
            print(f"[PDF Builder] Blinded mode: {args.blinded}")
            
        except Exception as e:
            print(f"[PDF Builder] ERROR: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()


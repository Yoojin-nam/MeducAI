"""
MeducAI Step06 (Export) — Anki Deck Exporter

P0 Requirements:
- Exporter uses S2 + (image filename rule or S4 manifest) to create deck
- Q1: image on Back only, Q2: image on Back only (2-card policy, back-only infographics)
- Missing policy: Q1 missing = FAIL, Q2 missing = FAIL (both required)

Design Principles:
- Role-based image placement (hardcoded, not configurable)
- Fail-fast on Q1/Q2 image missing
- Both Q1 and Q2 have independent back-only educational infographics
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# =========================
# Specialty Constants
# =========================

# All supported specialty IDs (11 specialties from tagging_rules_v1.1.json)
SPECIALTY_IDS = [
    "abdominal_rad",
    "breast_rad",
    "cv_rad",
    "gu_rad",
    "ir",
    "msk_rad",
    "neuro_hn_rad",
    "nuclear_medicine",
    "ped_rad",
    "phys_qc_medinfo",
    "thoracic_rad",
]

# Human-readable names for display/deck naming
SPECIALTY_NAMES = {
    "abdominal_rad": "Abdominal",
    "breast_rad": "Breast",
    "cv_rad": "Cardiovascular",
    "gu_rad": "Genitourinary",
    "ir": "IR",
    "msk_rad": "MSK",
    "neuro_hn_rad": "NeuroHN",
    "nuclear_medicine": "NuclearMedicine",
    "ped_rad": "Pediatric",
    "phys_qc_medinfo": "PhysicsQC",
    "thoracic_rad": "Thoracic",
}

# Specialties excluded from 2nd exam (subjective only): Physics, Nuclear Medicine
# Data group_path uses nuclear_med, physics_qc_informatics; also match canonical IDs
SECOND_EXAM_EXCLUDED_SPECIALTIES = [
    "nuclear_medicine", "nuclear_med",
    "phys_qc_medinfo", "physics_qc_informatics",
]

try:
    import genanki
except ImportError:
    print("Error: genanki package is required. Install with: pip install genanki", file=sys.stderr)
    sys.exit(1)

# Import path resolver for S2 results (backward compatibility)
try:
    import sys as _sys
    _THIS_DIR = Path(__file__).resolve().parent
    _sys.path.insert(0, str(_THIS_DIR))
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


def extract_specialty_from_group_path(group_path: str) -> Optional[str]:
    """
    Extract specialty ID from group_path.
    
    Args:
        group_path: Group path string in format "specialty > anatomy > modality > category"
    
    Returns:
        Specialty ID (e.g., "abdominal_rad") or None if not found
    """
    if not group_path:
        return None
    
    parts = [p.strip() for p in str(group_path).split(">")]
    if len(parts) >= 1 and parts[0]:
        # Normalize specialty: replace spaces with underscores, lowercase
        specialty = parts[0].strip().replace(" ", "_").lower()
        return specialty
    return None


def filter_records_by_specialty(
    records: List[Dict[str, Any]],
    specialty: str,
) -> List[Dict[str, Any]]:
    """
    Filter S2 records by specialty.
    
    Args:
        records: List of S2 records
        specialty: Specialty ID to filter by (case-insensitive)
    
    Returns:
        Filtered list of records matching the specialty
    """
    specialty_lower = specialty.lower().strip()
    filtered = []
    
    for record in records:
        group_path = str(record.get("group_path") or "").strip()
        record_specialty = extract_specialty_from_group_path(group_path)
        
        if record_specialty and record_specialty.lower() == specialty_lower:
            filtered.append(record)
    
    return filtered


def filter_records_exclude_specialties(
    records: List[Dict[str, Any]],
    exclude_specialty_ids: List[str],
) -> List[Dict[str, Any]]:
    """
    Filter out S2 records whose specialty is in the exclude list.
    
    Args:
        records: List of S2 records
        exclude_specialty_ids: Specialty IDs to exclude (case-insensitive)
    
    Returns:
        Filtered list of records not in the excluded specialties
    """
    exclude_set = {s.lower().strip() for s in exclude_specialty_ids if s}
    if not exclude_set:
        return records
    
    filtered = []
    for record in records:
        group_path = str(record.get("group_path") or "").strip()
        record_specialty = extract_specialty_from_group_path(group_path)
        if record_specialty and record_specialty.lower() in exclude_set:
            continue
        filtered.append(record)
    return filtered


def _resolve_repaired_variant_path(baseline_path: Path) -> Path:
    """
    Convert `something.jsonl` -> `something__repaired.jsonl` (does not check existence).
    """
    suffix = baseline_path.suffix
    stem = baseline_path.name[: -len(suffix)] if suffix else baseline_path.name
    return baseline_path.with_name(f"{stem}__repaired{suffix}")


def _prefer_translated_s2_path(candidate: Path) -> Path:
    """
    If a translated S2 file exists (__medterm_en.jsonl), use it so that
    the medical-term translation workflow is reflected in the export.
    """
    if not candidate or not candidate.suffix:
        return candidate
    stem = candidate.stem  # e.g. s2_results__s1armG__s2armG
    translated = candidate.with_name(f"{stem}__medterm_en{candidate.suffix}")
    if translated.exists():
        return translated
    return candidate


def _resolve_s2_paths(
    *,
    out_dir: Path,
    arm: str,
    s1_arm_actual: str,
) -> Tuple[Path, Optional[Path]]:
    """
    Returns (baseline_path, repaired_path_if_exists).
    Prefers translated files (__medterm_en.jsonl) when present.
    """
    arm_u = arm.strip().upper()
    s1_u = s1_arm_actual.strip().upper()
    baseline = resolve_s2_results_path(out_dir, arm_u, s1_arm=s1_u)
    baseline = _prefer_translated_s2_path(baseline)
    repaired_candidates = [
        out_dir / f"s2_results__s1arm{s1_u}__s2arm{arm_u}__repaired.jsonl",
        out_dir / f"s2_results__arm{arm_u}__repaired.jsonl",
        _resolve_repaired_variant_path(baseline),
    ]
    repaired = next((p for p in repaired_candidates if p.exists()), None)
    if repaired:
        repaired = _prefer_translated_s2_path(repaired)
    return baseline, repaired


def _group_s2_records_by_group_id(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for r in records:
        gid = str(r.get("group_id") or "").strip()
        if not gid:
            continue
        out.setdefault(gid, []).append(r)
    return out


# =========================
# Image Mapping
# =========================

def load_s4_manifest(manifest_path: Path) -> Dict[Tuple[str, str, str, str], str]:
    """
    Load S4 image manifest and create mapping.
    
    Returns:
        Dict mapping (run_tag, group_id, entity_id, card_role) -> media_filename
    
    Note: entity_id is normalized (colon to underscore) to match filename format.
    The manifest stores entity_id with colon (DERIVED:xxx) but filenames use underscore (DERIVED_xxx).
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
                run_tag = str(entry.get("run_tag") or "").strip()
                group_id = str(entry.get("group_id") or "").strip()
                entity_id_raw = str(entry.get("entity_id") or "").strip()
                card_role = str(entry.get("card_role") or "").strip().upper()
                media_filename = str(entry.get("media_filename") or "").strip()
                
                # Normalize entity_id: convert colon to underscore to match filename format
                # (S4 manifest stores DERIVED:xxx but filenames use DERIVED_xxx)
                entity_id = entity_id_raw.replace(":", "_") if entity_id_raw else ""
                
                if run_tag and group_id and entity_id and card_role and media_filename:
                    key = (run_tag, group_id, entity_id, card_role)
                    mapping[key] = media_filename
            except json.JSONDecodeError:
                continue
    
    return mapping


def find_image_by_filename(
    *,
    images_dir: Path,
    filename: str,
) -> Optional[Path]:
    """Find image file by filename in images directory."""
    if not images_dir.exists() or not images_dir.is_dir():
        return None
    
    if not filename:
        return None
    
    # Direct match
    image_path = images_dir / filename
    if image_path.exists() and image_path.is_file():
        return image_path
    
    # Try case-insensitive search (only files, skip directories)
    for img_file in images_dir.iterdir():
        if img_file.is_file() and img_file.name.lower() == filename.lower():
            return img_file
    
    return None


def make_image_html(image_path: Path) -> str:
    """Generate HTML for image embedding."""
    return f'<div class="meducai-imgwrap"><img src="{image_path.name}" class="meducai-img" /></div>'


# =========================
# Anki Models
# =========================

BASE_CSS = """
.card { font-family: Arial; font-size: 18px; text-align: left; color: black; background-color: white; }
div { margin: 0; padding: 0; }
img { display: block; margin: 0 auto; }
.meducai-imgwrap { margin: 0; padding: 0; text-align: center; }
.meducai-img { max-width: 100%; max-height: 45vh; width: auto; height: auto; object-fit: contain; }
"""


def make_basic_model(model_id: int) -> genanki.Model:
    """Basic note type (for Q1 with image on front)."""
    return genanki.Model(
        model_id,
        "MeducAI Basic",
        fields=[
            {"name": "Front"},
            {"name": "Back"},
        ],
        templates=[{
            "name": "Card 1",
            "qfmt": "{{Front}}",
            "afmt": "{{Front}}<hr id='answer'>{{Back}}",
        }],
        css=BASE_CSS,
    )


def make_mcq_model(model_id: int) -> genanki.Model:
    """MCQ note type (for Q2)."""
    return genanki.Model(
        model_id,
        "MeducAI MCQ",
        fields=[
            {"name": "Question"},
            {"name": "Options"},
            {"name": "Answer"},
            {"name": "Explanation"},
        ],
        templates=[{
            "name": "Card 1",
            "qfmt": "{{Question}}<br><br>{{Options}}",
            "afmt": "{{Question}}<br><br>{{Options}}<hr id='answer'>{{Answer}}<br>{{Explanation}}",
        }],
        css=BASE_CSS,
    )


# =========================
# Card Processing
# =========================

def format_mcq_options(options: List[str], correct_index: int) -> str:
    """Format MCQ options as HTML."""
    option_labels = ["A", "B", "C", "D", "E"]
    html_parts = []
    for i, option in enumerate(options[:5]):
        label = option_labels[i] if i < len(option_labels) else str(i + 1)
        html_parts.append(f"{label}. {option}")
    return "<br>".join(html_parts)


def format_back_text_html(back_text: str, remove_answer_line: bool = False, is_basic: bool = False) -> str:
    """
    Format back text as HTML with proper line breaks and bullet handling.
    
    Similar to 07_build_set_pdf.py's back text processing:
    - Handles bullets (*, -, •)
    - Handles numbered lists
    - Handles section headers (정답, 근거, etc.)
    - Adds line breaks between sections
    - Converts Markdown bold (**text**) to HTML (<b>text</b>)
    
    Args:
        remove_answer_line: If True, removes lines starting with "정답:" or "Answer:"
        is_basic: If True, removes extra line breaks before section headers (for Basic cards)
    """
    if not back_text or not isinstance(back_text, str):
        return str(back_text) if back_text else ""
    
    lines = back_text.split("\n")
    html_parts = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Remove answer line if requested (for MCQ to avoid duplication)
        if remove_answer_line:
            # Check if line starts with "정답:" or "Answer:" (case-insensitive)
            if re.match(r'^(정답|Answer):', line, re.IGNORECASE):
                continue
        
        # Check if it's a bullet point (starts with *, -, •)
        if line.startswith("* ") or line.startswith("- ") or line.startswith("• "):
            # Bullet point - preserve marker and add as HTML
            bullet_text = line[2:].strip() if len(line) > 2 else line
            if bullet_text:
                html_parts.append(f"• {bullet_text}")
        elif re.match(r'^\d+[\.\)]\s', line):
            # Numbered list item
            html_parts.append(line)
        elif line.endswith(":") and any(keyword in line for keyword in ["근거", "함정", "감별", "오답", "포인트", "암기", "팁", "Answer", "정답"]):
            # Section header (e.g., "근거:", "함정/감별:", "Answer:")
            # Skip "정답:" or "Answer:" headers if remove_answer_line is True
            if remove_answer_line and any(keyword in line for keyword in ["Answer", "정답"]):
                continue
            # For Basic cards, don't add extra line break before section header
            # (just use the <br> from join() at the end)
            if html_parts and not is_basic:
                html_parts.append("<br>")
            html_parts.append(f"<b>{line}</b>")
        else:
            # Regular text
            html_parts.append(line)
    
    # Join with <br> tags
    result = "<br>".join(html_parts)
    
    # Remove Markdown bold (do not convert to HTML)
    # **text** → text
    result = re.sub(r'\*\*([^*]+)\*\*', r'\1', result)
    
    return result


def generate_tags(
    *,
    card_type: str,
    group_path: Optional[str] = None,
    tags_specialty_only: bool = False,
) -> List[str]:
    """
    Generate tags for Anki card based on card type and group path.
    
    When tags_specialty_only is False (default):
    - Card type: "Basic" or "MCQ"
    - From group_path: "Specialty:{specialty}", "Anatomy:{anatomy}",
      "Modality:{modality}", "Category:{category}"
    When tags_specialty_only is True:
    - Only "Specialty:{specialty}" from group_path (no card type, anatomy, modality, category).
    
    Args:
        card_type: Card type string (Basic, MCQ, MCQ_Vignette)
        group_path: Group path string in format "specialty > anatomy > modality > category"
        tags_specialty_only: If True, only add Specialty tag.
    
    Returns:
        List of tag strings
    """
    tags = []
    
    if not tags_specialty_only:
        # Card type tag: Basic or MCQ (MCQ_Vignette included in MCQ)
        card_type_upper = str(card_type or "Basic").strip().upper()
        if card_type_upper in ("MCQ", "MCQ_VIGNETTE"):
            tags.append("MCQ")
        else:
            tags.append("Basic")
    
    # Specialty (and optionally anatomy/modality/category)
    if group_path:
        parts = [p.strip() for p in str(group_path).split(">")]
        if len(parts) >= 1 and parts[0]:
            tags.append(f"Specialty:{parts[0].replace(' ', '_')}")
        if not tags_specialty_only:
            if len(parts) >= 2 and parts[1]:
                tags.append(f"Anatomy:{parts[1].replace(' ', '_')}")
            if len(parts) >= 3 and parts[2]:
                tags.append(f"Modality:{parts[2].replace(' ', '_')}")
            if len(parts) >= 4 and parts[3]:
                tags.append(f"Category:{parts[3].replace(' ', '_')}")
    elif not tags_specialty_only:
        print(
            f"Warning: group_path is missing. Tags will only include card type. "
            f"group_path is required for Specialty/Anatomy/Modality/Category tags.",
            file=sys.stderr
        )
    
    return tags


def process_card(
    *,
    card: Dict[str, Any],
    run_tag: str,
    group_id: str,
    entity_id: str,
    image_mapping: Dict[Tuple[str, str, str, str], str],
    images_dir: Path,
    allow_missing_images: bool = False,
    image_only: bool = False,
    image_placement: Optional[str] = None,
    group_path: Optional[str] = None,
    tags_specialty_only: bool = False,
) -> Tuple[Optional[genanki.Note], Optional[str], Optional[str]]:
    """
    Process a single card and create Anki note.
    
    Returns:
        (note, media_filename, error_message)
    """
    card_role = str(card.get("card_role") or "").strip().upper()
    card_type = str(card.get("card_type") or "Basic").strip()
    front = str(card.get("front") or "").strip()
    back = str(card.get("back") or "").strip()
    
    if not (front and back):
        return None, None, "Missing front or back"
    
    # Format back text with proper line breaks and bullet handling
    # For MCQ, remove answer line to avoid duplication (Answer field already contains it)
    is_mcq = card_type.upper() in ("MCQ", "MCQ_VIGNETTE")
    is_basic = card_type.upper() not in ("MCQ", "MCQ_VIGNETTE")
    back_formatted = format_back_text_html(back, remove_answer_line=is_mcq, is_basic=is_basic)
    
    # P0: Role-based image placement
    # Normalize entity_id: convert colon to underscore to match image filename format
    # (S2 records use DERIVED:xxx but image filenames use DERIVED_xxx)
    normalized_entity_id = str(entity_id).replace(":", "_") if entity_id else ""
    
    # Q1 and Q2 each have their own image (no reuse).
    image_key = (run_tag, group_id, normalized_entity_id, card_role)
    
    media_filename = image_mapping.get(image_key)
    image_path = None
    
    if media_filename:
        image_path = find_image_by_filename(images_dir=images_dir, filename=media_filename)
    
    # P0: Missing policy enforcement
    # Use image_placement from S3 policy manifest (authoritative source)
    # If not provided, fall back to default behavior (Q1=BACK, Q2=BACK for 2-card policy)
    placement = str(image_placement or "").strip().upper()
    
    if card_role == "Q1":
        if not image_path:
            if image_only:
                return None, None, "SKIP_MISSING_IMAGE"
            # P0: Q1 image missing = FAIL (unless allow_missing_images)
            if allow_missing_images:
                # Allow missing Q1 images for sample/debug purposes
                print(f"Warning: Q1 image missing (allowed): {media_filename or 'no filename'} (group_id={group_id}, entity_id={entity_id})", file=sys.stderr)
                front_html = front
                back_html = back_formatted
            else:
                return None, None, f"Q1 image missing (required): {media_filename or 'no filename'}"
        else:
            # Q1: Image on back only (2-card policy, back-only infographic)
            front_html = front
            back_html = back_formatted + "<br>" + make_image_html(image_path)
    elif card_role == "Q2":
        if not image_path:
            if image_only:
                return None, None, "SKIP_MISSING_IMAGE"
            if allow_missing_images:
                print(f"Warning: Q2 image missing (allowed): {media_filename or 'no filename'} (group_id={group_id}, entity_id={entity_id})", file=sys.stderr)
                front_html = front
                back_html = back_formatted
            else:
                return None, None, f"Q2 image missing (required): {media_filename or 'no filename'}"
        else:
            # Q2: Image on back only (independent from Q1, back-only infographic)
            front_html = front
            back_html = back_formatted + "<br>" + make_image_html(image_path)
    else:
        return None, None, f"Unknown card_role: {card_role} (expected Q1 or Q2)"
    
    # Generate tags
    tags = generate_tags(
        card_type=card_type,
        group_path=group_path,
        tags_specialty_only=tags_specialty_only,
    )
    
    # Create note based on card type
    if card_type.upper() in ("MCQ", "MCQ_VIGNETTE"):
        # MCQ format
        options = card.get("options", [])
        correct_index = card.get("correct_index", 0)
        
        if not isinstance(options, list) or len(options) != 5:
            return None, None, f"MCQ must have exactly 5 options, got {len(options) if isinstance(options, list) else 0}"
        
        options_html = format_mcq_options(options, correct_index)
        correct_label = ["A", "B", "C", "D", "E"][correct_index] if 0 <= correct_index < 5 else "?"
        answer_text = f"Answer: {correct_label}. {options[correct_index]}"
        
        model_id = hash(f"mcq_{run_tag}") % (2 ** 31)
        model = make_mcq_model(model_id)
        
        note = genanki.Note(
            model=model,
            fields=[front_html, options_html, answer_text, back_html],
            tags=tags,
        )
    else:
        # Basic format
        model_id = hash(f"basic_{run_tag}") % (2 ** 31)
        model = make_basic_model(model_id)
        
        note = genanki.Note(
            model=model,
            fields=[front_html, back_html],
            tags=tags,
        )
    
    return note, media_filename, None


# =========================
# Main Processing
# =========================

def load_s2_results(s2_results_path: Path) -> List[Dict[str, Any]]:
    """Load S2 results JSONL file."""
    records = []
    if not s2_results_path.exists():
        raise FileNotFoundError(f"S2 results not found: {s2_results_path}")
    
    with open(s2_results_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if isinstance(record, dict):
                    records.append(record)
            except json.JSONDecodeError as e:
                print(f"Warning: Skipping invalid JSON at line {line_num}: {e}", file=sys.stderr)
                continue
    
    if not records:
        raise ValueError(f"No valid records found in {s2_results_path}")
    
    return records


def load_image_policy_manifest(manifest_path: Path) -> Dict[Tuple[str, str, str, str], str]:
    """
    Load S3 image policy manifest and create mapping.
    
    Returns:
        Dict mapping (run_tag, group_id, entity_id, card_role) -> image_placement
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
                run_tag = str(entry.get("run_tag") or "").strip()
                group_id = str(entry.get("group_id") or "").strip()
                entity_id = str(entry.get("entity_id") or "").strip()
                card_role = str(entry.get("card_role") or "").strip().upper()
                image_placement = str(entry.get("image_placement") or "").strip()
                
                if run_tag and group_id and entity_id and card_role and image_placement:
                    key = (run_tag, group_id, entity_id, card_role)
                    mapping[key] = image_placement
            except json.JSONDecodeError:
                continue
    
    return mapping


def process_export(
    *,
    base_dir: Path,
    run_tag: str,
    arm: str,
    s1_arm: Optional[str] = None,
    images_dir: Optional[Path] = None,
    output_path: Optional[Path] = None,
    allow_missing_images: bool = False,
    image_only: bool = False,
    export_manifest: Optional[Dict[str, bool]] = None,
    specialty: Optional[str] = None,
    exclude_specialties: Optional[List[str]] = None,
    subjective_only: bool = False,
    second_exam: bool = False,
    tags_specialty_only: bool = False,
) -> None:
    """Main export processing function."""
    # Paths
    out_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    # Use path resolver for backward compatibility (supports both new and legacy formats)
    # S1 arm: use s1_arm parameter if specified, otherwise use S2 arm
    s1_arm_actual = (s1_arm or arm).strip().upper() if s1_arm else arm
    s2_baseline_path, s2_repaired_path = _resolve_s2_paths(
        out_dir=out_dir, arm=arm, s1_arm_actual=s1_arm_actual
    )
    if "__medterm_en" in s2_baseline_path.name:
        print(f"[Export] Using translated S2 (medterm_en) for baseline")
    if s2_repaired_path and "__medterm_en" in s2_repaired_path.name:
        print(f"[Export] Using translated S2 (medterm_en) for repaired")
    s4_manifest_baseline_path = out_dir / f"s4_image_manifest__arm{arm}.jsonl"
    s4_manifest_repaired_path = _resolve_repaired_variant_path(s4_manifest_baseline_path)
    if not s4_manifest_repaired_path.exists():
        s4_manifest_repaired_path = None  # type: ignore[assignment]
    
    if images_dir is None:
        images_dir = out_dir / "images"
    else:
        images_dir = Path(images_dir).resolve()
    
    if output_path is None:
        if second_exam:
            output_path = base_dir / "6_Distributions" / "anki" / f"MeducAI_{run_tag}_arm{arm}_2nd_exam.apkg"
        else:
            output_path = base_dir / "6_Distributions" / "anki" / f"MeducAI_{run_tag}_arm{arm}.apkg"
    else:
        output_path = Path(output_path).resolve()
    
    # Load inputs (baseline + optional repaired, then select per group via manifest)
    selected_records: List[Dict[str, Any]] = []
    group_source: Dict[str, str] = {}  # group_id -> "baseline" | "repaired"

    if export_manifest:
        print(f"[Export] Manifest mode enabled: {len(export_manifest)} group entries")

        print(f"[Export] Loading S2 baseline from: {s2_baseline_path}")
        s2_baseline_records = load_s2_results(s2_baseline_path)
        by_gid_baseline = _group_s2_records_by_group_id(s2_baseline_records)

        by_gid_repaired: Dict[str, List[Dict[str, Any]]] = {}
        if s2_repaired_path is not None:
            print(f"[Export] Loading S2 repaired from: {s2_repaired_path}")
            s2_repaired_records = load_s2_results(s2_repaired_path)
            by_gid_repaired = _group_s2_records_by_group_id(s2_repaired_records)
        else:
            print(f"[Export] No repaired S2 file found; repaired groups will fallback to baseline")

        group_order: List[str] = []
        seen = set()
        for r in s2_baseline_records:
            gid = str(r.get("group_id") or "").strip()
            if gid and gid not in seen:
                seen.add(gid)
                group_order.append(gid)
        # Add groups that exist only in repaired file (should be rare)
        for gid in sorted(set(by_gid_repaired.keys()) - set(group_order)):
            group_order.append(gid)

        for gid in group_order:
            want_repaired = should_use_repaired(export_manifest, group_id=gid, default=False)
            if want_repaired and gid in by_gid_repaired and by_gid_repaired[gid]:
                selected_records.extend(by_gid_repaired[gid])
                group_source[gid] = "repaired"
            else:
                selected_records.extend(by_gid_baseline.get(gid, []))
                group_source[gid] = "baseline"

        print(
            f"[Export] Selected S2 records: {len(selected_records)} "
            f"(groups baseline={sum(1 for v in group_source.values() if v=='baseline')}, "
            f"repaired={sum(1 for v in group_source.values() if v=='repaired')})"
        )
    else:
        print(f"[Export] Loading S2 results from: {s2_baseline_path}")
        selected_records = load_s2_results(s2_baseline_path)
        print(f"[Export] Loaded {len(selected_records)} S2 records")

    # Filter by specialty if specified
    if specialty:
        specialty_normalized = specialty.lower().strip()
        records_before_filter = len(selected_records)
        selected_records = filter_records_by_specialty(selected_records, specialty_normalized)
        print(
            f"[Export] Specialty filter: {specialty_normalized} "
            f"({len(selected_records)} of {records_before_filter} records)"
        )
        if not selected_records:
            raise ValueError(
                f"No records found for specialty '{specialty_normalized}'. "
                f"Valid specialties: {', '.join(SPECIALTY_IDS)}"
            )

    # Filter out excluded specialties (e.g. for 2nd exam: physics, nuclear medicine)
    if exclude_specialties:
        records_before_exclude = len(selected_records)
        selected_records = filter_records_exclude_specialties(selected_records, exclude_specialties)
        print(
            f"[Export] Excluded specialties {exclude_specialties}: "
            f"({len(selected_records)} of {records_before_exclude} records)"
        )
        if not selected_records:
            raise ValueError(
                f"No records left after excluding specialties {exclude_specialties}."
            )

    # Load S4 manifest(s)
    print(f"[Export] Loading S4 baseline manifest from: {s4_manifest_baseline_path}")
    image_mapping_baseline = load_s4_manifest(s4_manifest_baseline_path)
    print(f"[Export] Loaded {len(image_mapping_baseline)} baseline image mappings")

    image_mapping_repaired: Dict[Tuple[str, str, str, str], str] = {}
    if export_manifest and s4_manifest_repaired_path is not None:
        print(f"[Export] Loading S4 repaired manifest from: {s4_manifest_repaired_path}")
        image_mapping_repaired = load_s4_manifest(s4_manifest_repaired_path)
        print(f"[Export] Loaded {len(image_mapping_repaired)} repaired image mappings")

    # Load S3 image policy manifest(s) (authoritative source for image placement)
    policy_manifest_baseline_path = out_dir / f"image_policy_manifest__arm{arm}.jsonl"
    policy_manifest_repaired_path = _resolve_repaired_variant_path(policy_manifest_baseline_path)
    if not policy_manifest_repaired_path.exists():
        policy_manifest_repaired_path = None  # type: ignore[assignment]

    image_placement_baseline = load_image_policy_manifest(policy_manifest_baseline_path)
    if image_placement_baseline:
        print(f"[Export] Loaded baseline image placement policy for {len(image_placement_baseline)} cards")
    else:
        print(f"[Export] Warning: Baseline policy manifest not found, using default placement")

    image_placement_repaired: Dict[Tuple[str, str, str, str], str] = {}
    if export_manifest and policy_manifest_repaired_path is not None:
        image_placement_repaired = load_image_policy_manifest(policy_manifest_repaired_path)
        if image_placement_repaired:
            print(f"[Export] Loaded repaired image placement policy for {len(image_placement_repaired)} cards")
    
    # Create deck
    # Include specialty in deck name/ID if filtered; 2nd exam gets distinct name
    if specialty:
        specialty_display = SPECIALTY_NAMES.get(specialty.lower(), specialty)
        deck_id = hash(f"{run_tag}_{arm}_{specialty}") % (2 ** 31)
        deck_name = f"MeducAI_{run_tag}_{specialty_display}"
    elif second_exam:
        deck_id = hash(f"{run_tag}_{arm}_2nd_exam") % (2 ** 31)
        deck_name = f"MeducAI_{run_tag}_arm{arm}_2nd_exam"
    else:
        deck_id = hash(f"{run_tag}_{arm}") % (2 ** 31)
        deck_name = f"MeducAI_{run_tag}_arm{arm}"
    deck = genanki.Deck(deck_id, deck_name)
    
    # Track statistics
    n_notes = 0
    n_q1 = 0
    n_q2 = 0
    n_with_images = 0
    q1_failures: List[str] = []
    q2_failures: List[str] = []
    n_skipped_missing_images = 0
    n_skipped_q1 = 0
    n_skipped_q2 = 0
    
    # Collect media files (use set to avoid duplicates)
    media_files_set: set[str] = set()
    
    # Process each S2 record
    n_missing_group_path = 0
    for s2_record in selected_records:
        run_tag_rec = str(s2_record.get("run_tag") or run_tag).strip()
        group_id = str(s2_record.get("group_id") or "").strip()
        entity_id = str(s2_record.get("entity_id") or "").strip()
        entity_name = str(s2_record.get("entity_name") or "").strip()
        group_path = str(s2_record.get("group_path") or "").strip()
        
        if not (group_id and entity_id):
            continue
        
        # Warn if group_path is missing (required for proper tagging)
        if not group_path:
            n_missing_group_path += 1
            print(
                f"Warning: group_path is missing for group_id={group_id}, entity_id={entity_id}. "
                f"Tags will only include card type. group_path is required for Specialty/Anatomy/Modality/Category tags.",
                file=sys.stderr
            )
        
        # Choose baseline vs repaired mappings per group (if manifest mode enabled)
        use_repaired_for_group = False
        if export_manifest:
            use_repaired_for_group = (group_source.get(group_id) == "repaired")

        image_mapping = (
            image_mapping_repaired if (use_repaired_for_group and image_mapping_repaired) else image_mapping_baseline
        )
        image_placement_mapping = (
            image_placement_repaired if (use_repaired_for_group and image_placement_repaired) else image_placement_baseline
        )

        cards = s2_record.get("anki_cards") or []
        for card in cards:
            if not isinstance(card, dict):
                continue
            
            card_role = str(card.get("card_role") or "").strip().upper()
            # Subjective-only (2nd exam): export only Q1 (Basic) cards
            if subjective_only and card_role != "Q1":
                continue
            
            # Get image_placement from S3 policy manifest (authoritative source)
            placement_key = (run_tag_rec, group_id, entity_id, card_role)
            image_placement = image_placement_mapping.get(placement_key)
            
            note, media_filename, error = process_card(
                card=card,
                run_tag=run_tag_rec,
                group_id=group_id,
                entity_id=entity_id,
                image_mapping=image_mapping,
                images_dir=images_dir,
                allow_missing_images=allow_missing_images,
                image_only=image_only,
                image_placement=image_placement,
                group_path=group_path,
                tags_specialty_only=tags_specialty_only,
            )
            
            if error:
                if error == "SKIP_MISSING_IMAGE":
                    n_skipped_missing_images += 1
                    if card_role == "Q1":
                        n_skipped_q1 += 1
                    elif card_role == "Q2":
                        n_skipped_q2 += 1
                    continue
                card_role = str(card.get("card_role") or "").strip().upper()
                error_msg = f"Entity: {entity_name}, Card: {card_role}, Error: {error}"
                if card_role == "Q1":
                    q1_failures.append(error_msg)
                elif card_role == "Q2":
                    q2_failures.append(error_msg)
                print(f"Error: {error_msg}", file=sys.stderr)
                continue
            
            if note:
                deck.add_note(note)
                n_notes += 1
                
                card_role = str(card.get("card_role") or "").strip().upper()
                if card_role == "Q1":
                    n_q1 += 1
                elif card_role == "Q2":
                    n_q2 += 1
                
                if media_filename:
                    image_path = find_image_by_filename(images_dir=images_dir, filename=media_filename)
                    if image_path:
                        media_files_set.add(str(image_path))
                        n_with_images += 1
    
    # P0: Fail-fast on Q1/Q2 failures (unless allow_missing_images or subjective_only)
    # When subjective_only we do not export Q2, so Q2 failures are irrelevant
    if q1_failures and not allow_missing_images and not image_only:
        error_msg = "Export FAIL: Q1 image missing (required):\n" + "\n".join(f"  - {f}" for f in q1_failures)
        raise RuntimeError(error_msg)
    elif q1_failures and allow_missing_images:
        print(f"Warning: {len(q1_failures)} Q1 cards missing images (allowed in sample mode)", file=sys.stderr)
    
    if not subjective_only:
        if q2_failures and not allow_missing_images and not image_only:
            error_msg = "Export FAIL: Q2 image missing (required):\n" + "\n".join(f"  - {f}" for f in q2_failures)
            raise RuntimeError(error_msg)
        elif q2_failures and allow_missing_images:
            print(f"Warning: {len(q2_failures)} Q2 cards missing images (allowed in sample mode)", file=sys.stderr)
    
    if n_notes == 0:
        raise RuntimeError("Export FAIL: No notes were created. Check S2 results and card data.")
    
    # Summary warning for missing group_path
    if n_missing_group_path > 0:
        print(
            f"[Export] Warning: {n_missing_group_path} records missing group_path. "
            f"Tags will only include card type. group_path is required for proper tagging (Specialty/Anatomy/Modality/Category).",
            file=sys.stderr
        )
    
    # Package deck
    print(f"[Export] Packaging deck...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pkg = genanki.Package([deck])
    media_files = sorted(media_files_set)  # Convert to sorted list for deterministic output
    if media_files:
        pkg.media_files = media_files
        print(f"[Export] Including {len(media_files)} media files")
    pkg.write_to_file(str(output_path))
    
    print(f"[Export] Deck: {deck_name}")
    print(f"[Export] Notes: {n_notes} (Q1: {n_q1}, Q2: {n_q2})")
    print(f"[Export] With images: {n_with_images}")
    if image_only:
        print(
            f"[Export] Image-only mode: skipped {n_skipped_missing_images} cards missing images "
            f"(Q1: {n_skipped_q1}, Q2: {n_skipped_q2})"
        )
    print(f"[Export] Output: {output_path}")


# =========================
# CLI
# =========================

def main() -> None:
    parser = argparse.ArgumentParser(description="Anki Deck Exporter")
    parser.add_argument("--base_dir", default=".", help="Base directory")
    parser.add_argument("--run_tag", required=True, help="Run tag")
    parser.add_argument("--arm", default="A", help="Arm identifier (S2 execution arm)")
    parser.add_argument("--s1_arm", default=None, help="S1 arm to use for reading S1 output (defaults to --arm if not specified)")
    parser.add_argument(
        "--export_manifest_path",
        default=None,
        help="Optional S6 export manifest JSON. If provided, per-group S2/S3/S4 inputs will be selected as baseline vs __repaired variants.",
    )
    parser.add_argument("--images_dir", default=None, help="Images directory (default: {out_dir}/images)")
    parser.add_argument("--output_path", default=None, help="Output .apkg path")
    parser.add_argument(
        "--allow_missing_images",
        action="store_true",
        help="Allow missing images (for sample/debug purposes, Q1 images will be skipped)",
    )
    parser.add_argument(
        "--image_only",
        action="store_true",
        help="Export only cards whose required images exist (skip cards missing images).",
    )
    parser.add_argument(
        "--specialty",
        default=None,
        help=f"Filter by specialty. Valid values: {', '.join(SPECIALTY_IDS)}",
    )
    parser.add_argument(
        "--all_specialties",
        action="store_true",
        help="Generate 11 separate decks, one for each specialty.",
    )
    parser.add_argument(
        "--second_exam",
        action="store_true",
        help="2nd exam preset: exclude Physics and Nuclear Medicine, export only subjective (Q1) cards. Output: MeducAI_{run_tag}_arm{arm}_2nd_exam.apkg",
    )
    parser.add_argument(
        "--exclude_specialties",
        default=None,
        metavar="ID1,ID2",
        help="Comma-separated specialty IDs to exclude (e.g. nuclear_medicine,phys_qc_medinfo).",
    )
    parser.add_argument(
        "--subjective_only",
        action="store_true",
        help="Export only Q1 (Basic / subjective) cards; skip Q2 (MCQ) cards.",
    )
    parser.add_argument(
        "--tags_specialty_only",
        action="store_true",
        help="Use only Specialty tag per card (no Basic/MCQ, Anatomy, Modality, Category).",
    )
    
    args = parser.parse_args()
    
    # Validate specialty arguments
    if args.specialty and args.all_specialties:
        raise ValueError("Cannot use both --specialty and --all_specialties")
    
    if args.second_exam and (args.specialty or args.all_specialties):
        raise ValueError("--second_exam cannot be used with --specialty or --all_specialties")
    
    if args.specialty and args.specialty.lower() not in SPECIALTY_IDS:
        raise ValueError(
            f"Invalid specialty '{args.specialty}'. "
            f"Valid values: {', '.join(SPECIALTY_IDS)}"
        )
    
    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        raise FileNotFoundError(f"Base directory does not exist: {base_dir}")
    
    run_tag = str(args.run_tag).strip()
    if not run_tag:
        raise ValueError("run_tag cannot be empty")
    
    arm = str(args.arm).strip().upper()
    if not arm:
        raise ValueError("arm cannot be empty")
    
    images_dir = Path(args.images_dir).resolve() if args.images_dir else None
    output_path = Path(args.output_path).resolve() if args.output_path else None
    
    s1_arm = str(args.s1_arm).strip().upper() if args.s1_arm else None
    export_manifest = None
    if args.export_manifest_path:
        manifest_path_obj = Path(str(args.export_manifest_path))
        manifest_path = (
            manifest_path_obj.resolve()
            if manifest_path_obj.is_absolute()
            else (base_dir / manifest_path_obj).resolve()
        )
        export_manifest = load_export_manifest(manifest_path)
        print(f"[Export] Loaded export manifest: {manifest_path} ({len(export_manifest)} group entries)")
    
    print(f"[Export] Processing: run_tag={run_tag}, arm={arm}")
    if s1_arm and s1_arm != arm:
        print(f"[Export] S1 arm={s1_arm} (reading S1 output from arm {s1_arm}, exporting S2 results from arm {arm})")
    
    # Parse exclude_specialties (comma-separated)
    exclude_specialties_list: Optional[List[str]] = None
    if args.exclude_specialties:
        exclude_specialties_list = [s.strip().lower() for s in args.exclude_specialties.split(",") if s.strip()]
        if exclude_specialties_list:
            print(f"[Export] Exclude specialties: {exclude_specialties_list}")
    if args.second_exam:
        exclude_specialties_list = SECOND_EXAM_EXCLUDED_SPECIALTIES
        print(f"[Export] Second exam mode: exclude {exclude_specialties_list}, subjective (Q1) only")
    
    # Second exam: single deck, no specialty loop
    if args.second_exam:
        try:
            process_export(
                base_dir=base_dir,
                run_tag=run_tag,
                arm=arm,
                s1_arm=s1_arm,
                images_dir=images_dir,
                output_path=output_path,
                allow_missing_images=args.allow_missing_images,
                image_only=args.image_only,
                export_manifest=export_manifest,
                specialty=None,
                exclude_specialties=exclude_specialties_list,
                subjective_only=True,
                second_exam=True,
                tags_specialty_only=args.tags_specialty_only,
            )
            print("[Export] Done (2nd exam deck)")
        except Exception as e:
            print(f"[Export] FAIL: {e}")
            raise
        return
    
    # Determine list of specialties to process
    if args.all_specialties:
        specialties_to_process = SPECIALTY_IDS
        print(f"[Export] All-specialties mode: generating {len(specialties_to_process)} decks")
    elif args.specialty:
        specialties_to_process = [args.specialty.lower().strip()]
        print(f"[Export] Single specialty mode: {args.specialty}")
    else:
        specialties_to_process = [None]  # None means no filtering (export all)
    
    try:
        n_success = 0
        n_fail = 0
        results: List[Tuple[Optional[str], bool, str]] = []  # (specialty, success, message)
        
        for specialty in specialties_to_process:
            # Determine output path for this specialty
            if specialty:
                specialty_display = SPECIALTY_NAMES.get(specialty, specialty)
                # When --all_specialties mode, auto-generate output paths
                if args.all_specialties:
                    current_output_path = (
                        base_dir / "6_Distributions" / "anki" 
                        / f"MeducAI_{run_tag}_{specialty_display}.apkg"
                    )
                elif output_path:
                    # User specified output path with --specialty
                    current_output_path = output_path
                else:
                    # Default output path for single specialty
                    current_output_path = (
                        base_dir / "6_Distributions" / "anki"
                        / f"MeducAI_{run_tag}_{specialty_display}.apkg"
                    )
            else:
                # No specialty filter - use provided output_path or default
                current_output_path = output_path
            
            try:
                process_export(
                    base_dir=base_dir,
                    run_tag=run_tag,
                    arm=arm,
                    s1_arm=s1_arm,
                    images_dir=images_dir,
                    output_path=current_output_path,
                    allow_missing_images=args.allow_missing_images,
                    image_only=args.image_only,
                    export_manifest=export_manifest,
                    specialty=specialty,
                    exclude_specialties=exclude_specialties_list,
                    subjective_only=args.subjective_only,
                    second_exam=False,
                    tags_specialty_only=args.tags_specialty_only,
                )
                n_success += 1
                results.append((specialty, True, "OK"))
                if specialty:
                    print(f"[Export] ✓ {specialty_display} deck complete")
            except Exception as e:
                n_fail += 1
                results.append((specialty, False, str(e)))
                if args.all_specialties:
                    # In all_specialties mode, continue with other specialties
                    print(f"[Export] ✗ {specialty or 'ALL'} FAILED: {e}", file=sys.stderr)
                else:
                    # Single deck mode - propagate error
                    raise
        
        # Summary for all_specialties mode
        if args.all_specialties:
            print(f"\n[Export] Summary: {n_success}/{len(specialties_to_process)} decks generated")
            if n_fail > 0:
                print(f"[Export] Failed decks ({n_fail}):", file=sys.stderr)
                for spec, success, msg in results:
                    if not success:
                        print(f"  - {spec}: {msg}", file=sys.stderr)
        
        print("[Export] Done")
    except Exception as e:
        print(f"[Export] FAIL: {e}")
        raise


if __name__ == "__main__":
    main()


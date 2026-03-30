"""
MeducAI Step03 (S3) — Policy Resolver & ImageSpec Compiler

P0 Requirements:
- S3 Policy Resolver: Hardcode policies (Q1→BACK/BASIC/required, Q2→BACK/MCQ/required) - 2-card policy
- S3 ImageSpec Compiler: S2 image_hint + S1 entity visual context → s3_image_spec.jsonl (Q1/Q2 + S1 table visual)
- Q1 and Q2 must meet minimum modality/anatomy/keywords or FAIL
- Output 2 files: image_policy_manifest.jsonl (Q1/Q2) and s3_image_spec.jsonl (Q1/Q2 + S1 table visual)

Design Principles:
- S3 is a compiler, NOT a generator (no LLM calls)
- Deterministic policy resolution based on card_role
- Template-based image spec compilation with card text and answer context
- Supports both card-level images (Q1/Q2) and group-level table visuals
"""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Import prompt bundle loader
try:
    from tools.prompt_bundle import load_prompt_bundle
    from tools.path_resolver import resolve_s2_results_path
    from tools.progress_logger import ProgressLogger
except ImportError:
    # Fallback: try relative import
    import sys
    _THIS_DIR = Path(__file__).resolve().parent
    sys.path.insert(0, str(_THIS_DIR))
    from tools.prompt_bundle import load_prompt_bundle
    try:
        from tools.path_resolver import resolve_s2_results_path
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
    try:
        from tools.progress_logger import ProgressLogger
    except ImportError:
        ProgressLogger = None


# =========================
# Policy Resolver (Hardcoded)
# =========================

def resolve_image_policy(card_role: str, visual_type_category: Optional[str] = None) -> Dict[str, Any]:
    """
    P0: Deterministic policy resolution based on card_role.
    
    2-card policy: Q1 and Q2 both have back-only educational infographics.
    
    Args:
        card_role: Card role (Q1, Q2)
        visual_type_category: Visual type category from S1 (e.g., "QC", "Equipment") - unused for 2-card policy
    
    Returns:
        {
            "image_placement": "BACK",
            "card_type": "BASIC" | "MCQ",
            "image_required": bool
        }
    """
    card_role = str(card_role).strip().upper()
    
    if card_role == "Q1":
        # Q1: Back-only infographic (2-card policy)
        return {
            "image_placement": "BACK",
            "card_type": "BASIC",
            "image_required": True,
        }
    elif card_role == "Q2":
        return {
            "image_placement": "BACK",
            "card_type": "MCQ",
            "image_required": True,  # Required (NEW: Q2 must have image asset)
        }
    else:
        raise ValueError(f"Unknown card_role: {card_role}. Expected Q1 or Q2.")


# =========================
# Sign Suffix for Realistic Images (De-exaggeration)
# =========================

SIGN_SUFFIX = " (depict subtly, not textbook-perfect)"


def add_sign_suffix(key_findings: List[str]) -> List[str]:
    """
    Add suffix to keywords containing 'sign' pattern to reduce over-exaggeration.
    
    This addresses the issue where image generation models tend to create
    textbook-perfect representations of named signs, which appear unrealistic
    to radiologists.
    
    Example:
        "halo sign" → "halo sign (depict subtly, not textbook-perfect)"
        "target sign" → "target sign (depict subtly, not textbook-perfect)"
    
    Args:
        key_findings: List of key finding keywords from image_hint
    
    Returns:
        List of keywords with suffix added to 'sign' patterns
    """
    if not key_findings:
        return key_findings
    
    result = []
    sign_pattern = re.compile(r'\bsign\b', re.IGNORECASE)
    
    for kw in key_findings:
        kw_stripped = str(kw).strip()
        if not kw_stripped:
            continue
        if sign_pattern.search(kw_stripped):
            # Don't add suffix if already present
            if "(depict subtly" not in kw_stripped:
                kw_stripped = kw_stripped + SIGN_SUFFIX
        result.append(kw_stripped)
    
    return result


# =========================
# Answer Extraction (Deterministic)
# =========================

def extract_answer_text(card: Dict[str, Any], card_role: str) -> str:
    """
    Deterministically extract answer text from card.
    
    For Q1 (BASIC): Parse from back line starting with "Answer:"
    For Q2 (MCQ): Parse correct_index and map to option text.
    
    Returns:
        Answer text string (empty if extraction fails)
    """
    card_role = str(card_role).strip().upper()
    back_text = str(card.get("back") or "").strip()
    
    if card_role == "Q1":
        # BASIC: Look for "Answer:" line
        for line in back_text.split("\n"):
            line = line.strip()
            if line.startswith("Answer:"):
                # Extract text after "Answer:"
                answer = line[7:].strip()  # Remove "Answer:" prefix
                # Remove any trailing punctuation that might be part of formatting
                answer = answer.rstrip(".,;:")
                return answer
        # Fallback: first line if no "Answer:" found
        first_line = back_text.split("\n")[0].strip() if back_text else ""
        return first_line
    
    elif card_role == "Q2":
        # MCQ: Use correct_index to get option text
        options = card.get("options", [])
        correct_index = card.get("correct_index", -1)
        
        if isinstance(options, list) and len(options) > 0 and 0 <= correct_index < len(options):
            option_text = str(options[correct_index]).strip()
            # Also get the letter (A-E)
            option_letter = ["A", "B", "C", "D", "E"][correct_index] if correct_index < 5 else "?"
            return f"{option_letter}. {option_text}"
        
        # Fallback: Try to parse from back text "Correct: X"
        for line in back_text.split("\n"):
            line = line.strip()
            if line.startswith("Correct:"):
                correct_part = line[8:].strip()  # Remove "Correct:" prefix
                # Try to find matching option
                if isinstance(options, list) and len(options) > 0:
                    # Extract letter (A-E)
                    match = re.match(r"^([A-E])", correct_part, re.IGNORECASE)
                    if match:
                        letter = match.group(1).upper()
                        idx = ord(letter) - ord("A")
                        if 0 <= idx < len(options):
                            return f"{letter}. {options[idx]}"
                return correct_part
    
    return ""


def extract_entity_row_from_table(
    *,
    master_table_markdown_kr: str,
    entity_name: str,
) -> Optional[Dict[str, str]]:
    """
    Extract entity row data from master table markdown.
    
    Returns:
        Dict with column values keyed by header, or None if not found
    """
    if not master_table_markdown_kr or not entity_name:
        return None
    
    lines = master_table_markdown_kr.strip().split("\n")
    if len(lines) < 2:
        return None
    
    # Parse header
    header_line = lines[0].strip()
    if not header_line.startswith("|") or not header_line.endswith("|"):
        return None
    
    headers = [h.strip() for h in header_line[1:-1].split("|")]
    
    # Skip separator line (---)
    data_start = 1
    if len(lines) > 1 and "---" in lines[1]:
        data_start = 2
    
    # Find matching entity row
    for line in lines[data_start:]:
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        
        cells = [c.strip() for c in line[1:-1].split("|")]
        if len(cells) != len(headers):
            continue
        
        # First column is typically entity name
        if len(cells) > 0 and entity_name in cells[0]:
            row_data = {}
            for i, header in enumerate(headers):
                if i < len(cells):
                    row_data[header] = cells[i]
            return row_data
    
    return None


# =========================
# Prompt Rendering Safety
# =========================

def safe_prompt_format(template: str, **kwargs) -> str:
    """Safely format prompt templates that may contain JSON examples with braces.
    
    Strategy:
    1) Escape ALL braces in the template so JSON examples remain literal.
    2) Un-escape only the placeholders we intend to substitute (keys in kwargs).
    3) Escape braces in kwargs values to prevent them from being interpreted as placeholders.
    4) Apply str.format().
    
    This prevents KeyError caused by JSON like { "id": ... } inside prompt templates,
    and also prevents braces in kwargs values (e.g., {mAs}, {N}) from being interpreted as placeholders.
    """
    if template is None:
        return ""
    t = template.replace("{", "{{").replace("}", "}}")
    for k in kwargs.keys():
        t = t.replace("{{" + k + "}}", "{" + k + "}")
    # Escape braces in kwargs values to prevent them from being interpreted as placeholders
    escaped_kwargs = {}
    for k, v in kwargs.items():
        if isinstance(v, str):
            escaped_kwargs[k] = v.replace("{", "{{").replace("}", "}}")
        else:
            escaped_kwargs[k] = v
    try:
        return t.format(**escaped_kwargs)
    except KeyError as e:
        raise KeyError(
            f"Prompt template contains an unrecognized placeholder: {e}. "
            f"Allowed keys={sorted(kwargs.keys())}"
        ) from e


# =========================
# View/Sequence Default Mapping (Deterministic)
# =========================

def infer_modality_from_anatomy(
    anatomy_region: str,
    entity_name: str = "",
) -> str:
    """
    Infer modality from anatomy region and entity name when modality is "Other" or missing.
    
    Returns:
        Inferred modality string (CT, MRI, XR, US, PET, etc.) or "CT" as default fallback.
    """
    anatomy_lower = anatomy_region.lower() if anatomy_region else ""
    entity_lower = entity_name.lower() if entity_name else ""
    combined = f"{anatomy_lower} {entity_lower}".lower()
    
    # Thyroid/Neck -> US (most common) or CT
    if any(term in combined for term in ["thyroid", "갑상선", "neck", "경부"]):
        return "US"
    
    # Head/Brain -> CT or MRI (prefer CT for initial imaging)
    if any(term in combined for term in ["head", "brain", "뇌", "두부", "skull", "두개골", "intracranial"]):
        return "CT"
    
    # Chest/Lung -> XR or CT (prefer XR for initial)
    if any(term in combined for term in ["chest", "lung", "thorax", "흉부", "폐", "pulmonary", "pleural"]):
        return "XR"
    
    # Heart/Cardiac -> Echo or CT
    if any(term in combined for term in ["heart", "cardiac", "심장", "myocardial", "coronary"]):
        return "Echo"
    
    # Abdomen/Pelvis -> CT or US (prefer CT for diagnostic)
    if any(term in combined for term in ["abdomen", "pelvis", "복부", "골반", "abdominal", "liver", "간", "kidney", "신장"]):
        return "CT"
    
    # Musculoskeletal/Bone -> XR or MRI (prefer XR for initial)
    if any(term in combined for term in ["bone", "musculoskeletal", "골", "관절", "joint", "spine", "척추", "extremity", "사지"]):
        return "XR"
    
    # Breast -> Mammo
    if any(term in combined for term in ["breast", "유방", "mammary"]):
        return "Mammo"
    
    # Vascular -> Angio or CT
    if any(term in combined for term in ["vascular", "vessel", "혈관", "artery", "vein", "동맥", "정맥"]):
        return "Angio"
    
    # Nuclear medicine / PET: disambiguate PET vs non-PET NM
    # NOTE: Many entities (e.g., bone scan \"Photopenia\") are NM, not PET.
    # Avoid substring false-positives by using word boundaries where possible.
    if re.search(r"\bpet\b", combined) or "petct" in combined or "pet/ct" in combined:
        return "PET"
    if (
        re.search(r"\bspect\b", combined)
        or any(
            term in combined
            for term in [
                "nuclear",
                "scinti",
                "scintigraphy",
                "bone scan",
                "bonescan",
                "photopenia",
                "cold lesion",
                "cold spot",
                "hot spot",
                "tc-99",
                "99m",
                "핵의학",
                "방사성",
                "골스캔",
                "골 스캔",
            ]
        )
    ):
        return "NM"
    
    # Default fallback: CT (most versatile)
    return "CT"


def apply_default_view_sequence(
    image_hint_v2: Dict[str, Any],
    modality: str,
    anatomy_region: str,
) -> Tuple[Dict[str, Any], str]:
    """
    Deterministically fill missing view/sequence in image_hint_v2 based on modality and anatomy.
    
    Args:
        image_hint_v2: image_hint_v2 dict (may be modified in-place)
        modality: Modality string (CT, MRI, XR, US, etc.)
        anatomy_region: Anatomy region string
    
    Returns:
        (updated_image_hint_v2, view_or_sequence_source) where source is "hint_v2" or "s3_default_map"
    """
    # Create copy to avoid mutating original
    v2 = dict(image_hint_v2) if isinstance(image_hint_v2, dict) else {}
    
    # Ensure anatomy structure exists
    if "anatomy" not in v2:
        v2["anatomy"] = {}
    anatomy = v2["anatomy"]
    
    # Ensure orientation structure exists
    if "orientation" not in anatomy:
        anatomy["orientation"] = {}
    orientation = anatomy["orientation"]
    
    # Check if view_plane or projection is already set (not NA/unknown/empty)
    view_plane = str(orientation.get("view_plane", "")).strip()
    projection = str(orientation.get("projection", "")).strip()
    
    has_view = view_plane and view_plane.upper() not in ("NA", "UNKNOWN", "")
    has_projection = projection and projection.upper() not in ("NA", "UNKNOWN", "")
    
    if has_view or has_projection:
        # Already has view/sequence, return as-is
        return v2, "hint_v2"
    
    # Deterministic mapping: (modality, anatomy_region) -> default view/sequence
    modality_upper = modality.upper()
    anatomy_lower = anatomy_region.lower() if anatomy_region else ""
    
    # Default view/sequence mapping
    default_view = None
    default_projection = None
    
    # CT defaults
    if "CT" in modality_upper:
        if any(term in anatomy_lower for term in ["head", "brain", "skull", "뇌", "두부"]):
            default_view = "axial"
        elif any(term in anatomy_lower for term in ["heart", "cardiac", "심장", "congenital"]):
            # Didactic heart diagrams often render more consistently in coronal/frontal than axial
            default_view = "coronal"
        elif any(term in anatomy_lower for term in ["spine", "spine", "척추"]):
            default_view = "sagittal"
        elif any(term in anatomy_lower for term in ["chest", "lung", "thorax", "흉부", "폐"]):
            default_view = "axial"
        elif any(term in anatomy_lower for term in ["abdomen", "pelvis", "복부", "골반"]):
            default_view = "axial"
        else:
            default_view = "axial"  # CT default to axial
    
    # MRI defaults
    elif "MRI" in modality_upper:
        if any(term in anatomy_lower for term in ["head", "brain", "skull", "뇌", "두부"]):
            default_view = "axial"
        elif any(term in anatomy_lower for term in ["spine", "spine", "척추"]):
            default_view = "sagittal"
        elif any(term in anatomy_lower for term in ["knee", "shoulder", "joint", "관절"]):
            default_view = "sagittal"
        else:
            default_view = "axial"  # MRI default to axial
    
    # XR/Radiograph defaults
    elif any(term in modality_upper for term in ["XR", "X-RAY", "RADIOGRAPH"]):
        if any(term in anatomy_lower for term in ["chest", "lung", "thorax", "흉부", "폐"]):
            default_projection = "PA"
        elif any(term in anatomy_lower for term in ["spine", "척추"]):
            default_projection = "AP"
        elif any(term in anatomy_lower for term in ["extremity", "limb", "사지"]):
            default_projection = "AP"
        else:
            default_projection = "AP"  # XR default to AP
    
    # US defaults
    elif "US" in modality_upper or "ULTRASOUND" in modality_upper:
        default_view = "axial"  # US typically axial

    # Nuclear medicine (planar scintigraphy) defaults
    elif modality_upper == "NM" or "NUCLEAR" in modality_upper:
        # Planar projection is more appropriate than a view_plane for NM
        default_projection = "AP"
        default_view = "NA"

    # PET defaults
    elif "PET" in modality_upper:
        default_view = "axial"
    
    # Fill in defaults
    if default_view and not has_view:
        orientation["view_plane"] = default_view
        orientation["projection"] = orientation.get("projection", "NA")
    elif default_projection and not has_projection:
        orientation["projection"] = default_projection
        orientation["view_plane"] = orientation.get("view_plane", "NA")
    else:
        # No default found, mark as unknown
        orientation["view_plane"] = "unknown"
        orientation["projection"] = "unknown"
        return v2, "s3_default_map"  # Still return s3_default_map even if unknown
    
    return v2, "s3_default_map"


# =========================
# Modality × Anatomy → windowing_hint (Deterministic; conservative)
# =========================

def infer_windowing_hint(
    *,
    modality: str,
    anatomy_region: str,
    image_hint_v2: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Deterministically infer a conservative CT windowing hint when we have enough signal.

    Returns one of: "brain" | "lung" | "bone" | "soft_tissue" | None

    IMPORTANT:
    - Only returns hints for CT modality (do NOT guess for other modalities).
    - If uncertain, returns None (safe omission).
    """
    mod = (modality or "").strip().upper()
    if "CT" not in mod:
        return None

    v2: Dict[str, Any] = image_hint_v2 if isinstance(image_hint_v2, dict) else {}
    anatomy_raw = v2.get("anatomy")
    anatomy: Dict[str, Any] = anatomy_raw if isinstance(anatomy_raw, dict) else {}

    organ_system = _as_nonempty_str(anatomy.get("organ_system")).lower()
    organ = _as_nonempty_str(anatomy.get("organ")).lower()
    subregion = _as_nonempty_str(anatomy.get("subregion")).lower()

    text = " ".join(
        [
            (anatomy_region or "").lower(),
            organ_system,
            organ,
            subregion,
        ]
    )
    text = " ".join(text.split())
    if not text:
        return None

    # Brain/head
    if re.search(r"\b(brain|intracranial|head|cns|neuro|cranial)\b", text):
        # If explicitly bone/fracture oriented, prefer bone window (skull/base).
        if re.search(r"\b(fracture|skull|calvarium|bone)\b", text):
            return "bone"
        return "brain"

    # Lungs/chest
    if re.search(r"\b(lung|pulmonary|pleura|thorax|chest)\b", text):
        return "lung"

    # Bone/MSK/spine
    if re.search(r"\b(bone|osseous|fracture|spine|vertebra|rib|pelvic\s+ring)\b", text):
        return "bone"

    # Abdomen/pelvis / generic soft tissue
    if re.search(
        r"\b(abdomen|abdominal|pelvis|hepatic|liver|spleen|pancreas|kidney|renal|adrenal|bowel|appendix|aorta|mesenteric)\b",
        text,
    ):
        return "soft_tissue"

    return None


def apply_windowing_hint(
    image_hint_v2: Dict[str, Any],
    *,
    modality: str,
    anatomy_region: str,
) -> Tuple[Dict[str, Any], Optional[str], str]:
    """
    Attach inferred windowing_hint into image_hint_v2.rendering_policy if missing.

    Returns: (updated_image_hint_v2, windowing_hint, source)
      - source: "hint_v2" | "s3_inferred" | "none"
    """
    v2: Dict[str, Any] = dict(image_hint_v2) if isinstance(image_hint_v2, dict) else {}
    rendering_raw = v2.get("rendering_policy")
    rendering: Dict[str, Any] = rendering_raw if isinstance(rendering_raw, dict) else {}
    if not isinstance(rendering_raw, dict):
        v2["rendering_policy"] = rendering

    existing = _as_nonempty_str(rendering.get("windowing_hint")).strip().lower()
    if existing and existing not in ("na", "n/a", "none", "null", "unknown", "unset"):
        return v2, existing, "hint_v2"

    inferred = infer_windowing_hint(modality=modality, anatomy_region=anatomy_region, image_hint_v2=v2)
    if inferred:
        rendering["windowing_hint"] = inferred
        return v2, inferred, "s3_inferred"

    return v2, None, "none"


# =========================
# image_hint_v2 → CONSTRAINT BLOCK (Deterministic)
# =========================

def _as_nonempty_str(x: Any) -> str:
    s = str(x or "").strip()
    return s


def build_constraint_block(
    image_hint_v2: Optional[Dict[str, Any]],
    *,
    view_or_sequence: Optional[str] = None,
    exam_prompt_profile: Optional[str] = None,
    purpose: str = "card_image",  # card_image | table_visual
    block_title: str = "CONSTRAINT_BLOCK",
    source_label: str = "image_hint_v2",
) -> Tuple[str, List[str], bool]:
    """
    Deterministically convert image_hint_v2 into a compact constraint block (plain text).

    Returns:
        (constraint_block, sufficiency_flags, requires_human_review)
    """
    if not isinstance(image_hint_v2, dict) or not image_hint_v2:
        return "", [], False

    flags: List[str] = []

    _anatomy_raw = image_hint_v2.get("anatomy")
    anatomy: Dict[str, Any] = _anatomy_raw if isinstance(_anatomy_raw, dict) else {}

    _rendering_raw = image_hint_v2.get("rendering_policy")
    rendering: Dict[str, Any] = _rendering_raw if isinstance(_rendering_raw, dict) else {}

    _safety_raw = image_hint_v2.get("safety")
    safety: Dict[str, Any] = _safety_raw if isinstance(_safety_raw, dict) else {}

    organ_system = _as_nonempty_str(anatomy.get("organ_system"))
    organ = _as_nonempty_str(anatomy.get("organ"))
    subregion = _as_nonempty_str(anatomy.get("subregion"))
    laterality = _as_nonempty_str(anatomy.get("laterality"))
    if not organ_system:
        flags.append("missing_v2.anatomy.organ_system")
    if not organ:
        flags.append("missing_v2.anatomy.organ")
    if not laterality:
        flags.append("missing_v2.anatomy.laterality")

    # Safety: explicit review flag takes precedence; otherwise infer from missing critical fields
    requires_review = bool(safety.get("requires_human_review", False)) or bool(flags)

    _orientation_raw = anatomy.get("orientation")
    orientation: Dict[str, Any] = _orientation_raw if isinstance(_orientation_raw, dict) else {}
    # Ensure we can safely persist deterministic auto-fixes into the passed-through v2 structure.
    if not isinstance(_orientation_raw, dict):
        anatomy["orientation"] = orientation
    view_plane = _as_nonempty_str(orientation.get("view_plane"))
    projection = _as_nonempty_str(orientation.get("projection"))
    patient_position = _as_nonempty_str(orientation.get("patient_position"))

    def _list_of_str(v: Any, max_n: int) -> List[str]:
        if not isinstance(v, list):
            return []
        out = []
        for item in v:
            s = _as_nonempty_str(item)
            if s:
                out.append(s)
            if len(out) >= max_n:
                break
        return out

    landmarks = _list_of_str(anatomy.get("key_landmarks_to_include"), 8)
    forbidden = _list_of_str(anatomy.get("forbidden_structures"), 10)
    adjacency = _list_of_str(anatomy.get("adjacency_rules"), 12)
    topology = _list_of_str(anatomy.get("topology_constraints"), 8)

    # NOTE: Do not blindly trust S2 rendering_policy for EXAM(REALISTIC) lane.
    # S2 outputs may contain diagram-oriented hints (e.g., flat_diagram + forbid photorealistic/PACS_UI),
    # which directly conflicts with the REALISTIC prompt templates and increases style instability.
    purpose_norm = (purpose or "card_image").strip().lower()
    is_table_visual = purpose_norm in ("table_visual", "table", "infographic", "table_infographic")

    style_target = _as_nonempty_str(rendering.get("style_target")) or "flat_grayscale_diagram"
    default_text_budget = "explanatory_slide" if is_table_visual else "minimal_labels_only"
    text_budget = _as_nonempty_str(rendering.get("text_budget")) or default_text_budget
    forbidden_styles = _list_of_str(rendering.get("forbidden_styles"), 12)
    windowing_hint = _as_nonempty_str(rendering.get("windowing_hint"))

    # NOTE: Safety fallback mode is descriptive only (we do not implement alternate generators here),
    # but it should not contradict the chosen lane/profile.
    fallback_mode = _as_nonempty_str(safety.get("fallback_mode")) or "generic_conservative_diagram"

    def _is_unknown_token(s: str) -> bool:
        sl = (s or "").strip().lower()
        return (not sl) or sl in ("na", "n/a", "none", "null", "unknown", "unset")

    def _normalize_plane(s: str) -> str:
        sl = (s or "").strip().lower()
        if sl in ("axial", "transverse"):
            return "axial"
        if sl in ("coronal", "frontal"):
            return "coronal"
        if sl in ("sagittal",):
            return "sagittal"
        return sl

    def _normalize_projection(s: str) -> str:
        su = (s or "").strip().upper()
        if su in ("A-P", "ANTERIOR-POSTERIOR"):
            return "AP"
        if su in ("P-A", "POSTERIOR-ANTERIOR"):
            return "PA"
        if su in ("LAT", "LATERAL"):
            return "LATERAL"
        if su in ("OBL", "OBLIQUE"):
            return "OBLIQUE"
        return su

    def _infer_plane_from_view_or_sequence(vos: str) -> Optional[str]:
        t = (vos or "").strip().lower()
        if not t:
            return None
        # Keep this conservative: only infer planes when explicit tokens exist.
        if re.search(r"\baxial\b|\btransverse\b", t):
            return "axial"
        if re.search(r"\bcoronal\b|\bfrontal\b", t):
            return "coronal"
        if re.search(r"\bsagittal\b", t):
            return "sagittal"
        return None

    def _infer_projection_from_view_or_sequence(vos: str) -> Optional[str]:
        t = (vos or "").strip().lower()
        if not t:
            return None
        # XR-like tokens
        if re.search(r"\bpa\b", t):
            return "PA"
        if re.search(r"\bap\b", t):
            return "AP"
        if re.search(r"\blateral\b|\blat\b", t):
            return "LATERAL"
        if re.search(r"\boblique\b|\bobl\b", t):
            return "OBLIQUE"
        return None

    def _is_realistic_profile(p: Optional[str]) -> bool:
        pl = str(p or "").strip().lower()
        # Keep this forgiving: callers may pass simplified tokens ("realistic") or template-ish labels.
        if pl in ("v8_realistic", "realistic", "pacs", "v8_realistic_4x5_2k", "s5r2_realistic"):
            return True
        return ("realistic" in pl) or ("pacs" in pl)

    is_realistic = _is_realistic_profile(exam_prompt_profile)
    # -------------------------
    # REALISTIC(EXAM) overrides (single source of truth)
    # -------------------------
    # For REALISTIC lane we enforce: PACS-like grayscale look, ZERO text, ZERO overlays.
    # This prevents contradictions between S2 hint_v2 (often diagram-biased) and the REALISTIC prompt templates.
    if is_realistic:
        style_target = "pacs_realistic_grayscale"
        text_budget = "zero_text"
        # Replace (not merge) forbidden styles to remove common contradictions like "photorealistic" / "PACS_UI".
        forbidden_styles = [
            "diagram",
            "infographic",
            "cartoon",
            "3d_render",
            "glow",
            "edge_outline",
            "posterized",
        ]
        # Keep the safety metadata consistent with the REALISTIC lane.
        fallback_mode = "generic_conservative_realistic"
        # Also persist these overrides back into the v2 structure for auditability, so downstream
        # artifacts (e.g., s3_image_spec.jsonl) do not carry contradictory diagram-oriented policies.
        try:
            if not isinstance(_rendering_raw, dict):
                image_hint_v2["rendering_policy"] = rendering
            rendering["style_target"] = style_target
            rendering["text_budget"] = text_budget
            rendering["forbidden_styles"] = list(forbidden_styles)
        except Exception:
            pass

    text_policy_profile = (
        "realistic_text0_overlay0"
        if is_realistic
        else ("diagram_slide_explanatory" if is_table_visual else "diagram_minimal_labels")
    )
    effective_text_budget = "zero_text" if is_realistic else text_budget

    lines: List[str] = []
    bt = (block_title or "CONSTRAINT_BLOCK").strip()
    sl = (source_label or "image_hint_v2").strip()
    lines.append(f"{bt} ({sl}):")
    parts = [f"organ_system={organ_system or 'NA'}", f"organ={organ or 'NA'}"]
    if subregion:
        parts.append(f"subregion={subregion}")
    parts.append(f"laterality={laterality or 'NA'}")
    lines.append("ANATOMY: " + ", ".join(parts))

    if view_plane or projection or patient_position:
        o_parts = []
        if view_plane:
            o_parts.append(f"view_plane={view_plane}")
        if projection:
            o_parts.append(f"projection={projection}")
        if patient_position:
            o_parts.append(f"patient_position={patient_position}")
        if o_parts:
            lines.append("ORIENTATION: " + ", ".join(o_parts))

    # --- View alignment: view_or_sequence ↔ orientation(view_plane/projection) ---
    # If both are provided, enforce consistency deterministically:
    # - If one side is unknown/NA, auto-fill from the other.
    # - If both are explicit and conflict, escalate to requires_human_review.
    vos_raw = str(view_or_sequence or "").strip()
    vos_norm = vos_raw.lower()
    inferred_plane = _infer_plane_from_view_or_sequence(vos_norm) if vos_raw else None
    inferred_proj = _infer_projection_from_view_or_sequence(vos_norm) if vos_raw else None
    vp_norm = _normalize_plane(view_plane)
    proj_norm = _normalize_projection(projection)

    alignment_actions: List[str] = []
    if inferred_plane and _is_unknown_token(vp_norm):
        orientation["view_plane"] = inferred_plane
        vp_norm = inferred_plane
        view_plane = inferred_plane
        alignment_actions.append(f"set view_plane={inferred_plane} (from view_or_sequence)")
    if inferred_proj and _is_unknown_token(proj_norm):
        orientation["projection"] = inferred_proj
        proj_norm = inferred_proj
        projection = inferred_proj
        alignment_actions.append(f"set projection={inferred_proj} (from view_or_sequence)")

    mismatch_reasons: List[str] = []
    if inferred_plane and (not _is_unknown_token(vp_norm)) and inferred_plane != vp_norm:
        mismatch_reasons.append(f"view_plane mismatch (view_or_sequence={inferred_plane} vs orientation={vp_norm})")
    if inferred_proj and (not _is_unknown_token(proj_norm)) and inferred_proj != proj_norm:
        mismatch_reasons.append(f"projection mismatch (view_or_sequence={inferred_proj} vs orientation={proj_norm})")

    if alignment_actions:
        lines.append("VIEW_ALIGNMENT_AUTOFIX: " + "; ".join(alignment_actions))

    if vos_raw and (view_plane or projection):
        lines.append(
            "VIEW_ALIGNMENT_PRE_CHECK: Before generating, verify that view_or_sequence matches orientation(view_plane/projection). If mismatch exists, DO NOT generate; align specifications first."
        )

    if mismatch_reasons:
        flags.append("view_or_sequence_orientation_mismatch")
        requires_review = True
        lines.append(
            "VIEW_ORIENTATION_MISMATCH_DETECTED: "
            + "; ".join(mismatch_reasons)
            + f". view_or_sequence='{vos_raw}'. Set requires_human_review=true and DO NOT generate until resolved."
        )

    # Safety hints derived from orientation/text policy (helps reduce laterality errors & excessive text)
    # Laterality self-check strengthening (P0: Critical) - PRE-GENERATION CHECK
    if view_plane.strip().lower() == "coronal":
        lines.append(
            "CORONAL_LATERALITY_PRE_CHECK: Before generating, verify: Does IMAGE_HINT specify a laterality requirement? For coronal views: patient's left = viewer's right. If laterality is ambiguous or you are uncertain, DO NOT generate. Request clarification or use a non-laterality-dependent view."
        )
    if view_plane.strip().lower() == "axial":
        lines.append(
            "AXIAL_LATERALITY_PRE_CHECK: Before generating, verify: Does IMAGE_HINT specify a laterality requirement? For axial views: patient's right = viewer's left. If laterality is ambiguous or you are uncertain, DO NOT generate. Request clarification or use a non-laterality-dependent view."
        )
    # Required laterality check when L/R is specified
    if laterality and laterality.upper() in ("L", "R"):
        lines.append(
            f"REQUIRED_LATERALITY_PRE_CHECK: Before generating, verify: Structure must be on patient's {laterality} side. For coronal views: patient's left = viewer's right. For axial views: patient's right = viewer's left. If uncertain, DO NOT generate. Request clarification or use a non-laterality-dependent view."
        )
    
    # Text budget hard constraint + validation (P0: Critical)
    lines.append(f"TEXT_POLICY_PROFILE: {text_policy_profile}")
    eff = effective_text_budget.strip().lower()
    if eff in ("zero_text", "no_text", "none", "text0", "0", "zero"):
        if is_realistic:
            # REALISTIC lane: overlays are NOT allowed (no arrows/circles/boxes/callouts).
            lines.append(
                "TEXT_POLICY_ZERO_TOLERANCE: ABSOLUTELY FORBIDDEN: Any text labels, captions, annotations, measurements, or text elements of any kind."
            )
            lines.append(
                "OVERLAY_POLICY_ZERO_TOLERANCE: ABSOLUTELY FORBIDDEN: Any overlays such as arrows, circles, boxes, callouts, markers, crosshairs, rulers, measurement lines, or UI-like elements. No PACS UI text/menus."
            )
            lines.append(
                "PRE_GENERATION_CHECK_REALISTIC: If the concept cannot be conveyed WITHOUT text AND WITHOUT overlays, DO NOT generate; request clarification or simplify the target finding."
            )
            # Conspicuity control for REALISTIC lane (common failure: overly iconic ‘sign’ depictions).
            lines.append(
                "CONSPICUITY_POLICY_REALISTIC: Keep findings subtle-to-moderate. Avoid perfect textbook signs (e.g., perfectly uniform halo/ring/target patterns). Prefer irregular, partial, heterogeneous appearances; not every lesion must show the sign."
            )
        else:
            # DIAGRAM lane: allow non-text cues like arrows/circles, but still no text beyond the limited label policy.
            lines.append(
                "TEXT_POLICY_ZERO_TOLERANCE: ABSOLUTELY FORBIDDEN: Any text labels, captions, annotations, measurements, or text elements of any kind. Use ONLY arrows/circles and purely visual cues (shade variation, landmark positioning)."
            )
            lines.append(
                "TEXT_PRE_GENERATION_CHECK: Before generating, ask yourself: 'Can I show this finding using only arrows/circles/visual cues?' If the answer is 'no', reconsider the visual approach."
            )
        lines.append(
            "TEXT_POST_GENERATION_CHECK: After generating, count ALL text elements (labels, captions, annotations, measurements). If text_count > 0, regenerate with ZERO text."
        )
        lines.append(
            "TEXT_FORBIDDEN_TOKENS: FORBIDDEN: 'A', 'B', 'Finding 1', 'Finding 2', 'Left', 'Right', 'L', 'R', 'Anterior', 'Posterior', 'Superior', 'Inferior', any anatomical labels, any measurements, any annotations."
        )
    else:
        if is_table_visual:
            # TABLE VISUAL lane: we EXPECT structured explanatory text (slide-style).
            # This avoids the "empty Key takeaways box" failure caused by diagram_minimal_labels defaults.
            lines.append(
                "TEXT_POLICY_SLIDE: You MUST include a short title and structured explanatory text. Allowed: section headers, short sentences, and bullet lists. "
                "Required minimum: (1) Title, (2) 2–4 short callouts OR small text boxes tied to the diagram, (3) 'Key takeaways' section with 3–6 bullets. "
                "Keep each bullet concise (<=12 words). Avoid long paragraphs (max 2 lines per box)."
            )
            lines.append(
                "TEXT_POLICY_NO_EMPTY: Do NOT leave empty bullets, placeholder dots, or blank 'Key takeaways'. If a bullet list is present, every bullet must contain meaningful content (at least 4 words)."
            )
            lines.append(
                "FACTUALITY_GUARD: Use ONLY information grounded in the provided table/hints. Do NOT invent numbers, branch counts, rare variants, or extra syndromic associations. "
                "If uncertain, write a generic safe takeaway (e.g., 'Key: focus on location and adjacency relationships')."
            )
            lines.append(
                "TEXT_FORBIDDEN: Never label laterality (Left/Right/L/R). No measurements unless explicitly provided. No patient data. No brand/watermark."
            )
        else:
            # DIAGRAM lane: default is "no labels"; allow a small, capped label budget when necessary.
            # Goal: permit simple educational diagrams like "Acute vs Chronic thrombus" without allowing dense text.
            lines.append(
                "TEXT_POLICY_LIMITED_LABELS: Default allows a short title + a few short labels if needed (keep text minimal). If absolutely necessary for disambiguation, allow a SMALL number of short labels (<=3 words each). Target <=5 labels (title allowed). Any image with excessive text (>=8 text elements) must be REJECTED and regenerated with fewer/shorter labels."
            )
            lines.append(
                "TEXT_FORBIDDEN: Never label laterality (Left/Right/L/R). No sentences, no paragraphs, no measurements."
            )

    if landmarks:
        lines.append("LANDMARKS_TO_INCLUDE: " + "; ".join(landmarks))
    if forbidden:
        lines.append("FORBIDDEN_STRUCTURES: " + "; ".join(forbidden))
    if adjacency:
        lines.append("ADJACENCY_RULES: " + "; ".join(adjacency))
    if topology:
        lines.append("TOPOLOGY_CONSTRAINTS: " + "; ".join(topology))

    # CT-only hint: keep deterministic, optional, and conservative.
    wh = (windowing_hint or "").strip().lower()
    if wh and wh not in ("na", "n/a", "none", "null", "unknown", "unset"):
        lines.append(f"WINDOWING_HINT: {wh}  # CT-only (brain|lung|bone|soft_tissue). If not applicable, ignore. Do NOT guess.")

    lines.append(
        f"RENDERING_POLICY: style_target={style_target}, text_budget={text_budget}, text_budget_effective={effective_text_budget}"
    )
    if forbidden_styles:
        lines.append("FORBIDDEN_STYLES: " + "; ".join(forbidden_styles))

    lines.append(f"SAFETY: requires_human_review={str(requires_review).lower()}, fallback_mode={fallback_mode}")
    
    # Contradiction check (P1: High) - compliance requirements validation
    compliance_check = safety.get("compliance_check")
    if isinstance(compliance_check, dict):
        required_elements = compliance_check.get("required_elements", [])
        if required_elements:
            lines.append(
                f"COMPLIANCE_REQUIREMENTS: The image MUST show the following elements: {', '.join(required_elements)}. Verify that the image shows what is required, not labeled as 'NOT VISIBLE'."
            )

    return "\n".join(lines).strip(), flags, requires_review


# =========================
# Anatomy_Map Safety Fallback (optional)
# =========================

def _env_bool(name: str, default: bool) -> bool:
    """Read boolean from environment variable."""
    val = os.getenv(name, "").strip().lower()
    if val in ("1", "true", "yes", "on"):
        return True
    if val in ("0", "false", "no", "off"):
        return False
    return default


def _parse_markdown_table(mt: str) -> Tuple[List[str], List[List[str]]]:
    """
    Best-effort markdown table parser (header + rows).
    Returns (headers, rows). On failure returns ([], []).
    """
    if not mt or "|" not in mt:
        return [], []
    lines = [ln.strip() for ln in mt.strip().split("\n") if ln.strip()]
    if len(lines) < 3:
        return [], []

    header_line = lines[0]
    if "|" not in header_line:
        return [], []
    headers = [h.strip() for h in header_line.strip("|").split("|")]

    # separator is usually lines[1]
    data_start = 2 if len(lines) > 1 and "---" in lines[1] else 1
    rows: List[List[str]] = []
    for ln in lines[data_start:]:
        if "|" not in ln:
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        rows.append(cells)
    return headers, rows


def _stable_hash_json(obj: Any) -> str:
    """Stable short hash for audit/debug (no security use)."""
    try:
        s = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except Exception:
        s = str(obj)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _split_exam_point_cell(cell: str) -> List[str]:
    """
    Best-effort deterministic splitter for 시험포인트-like cells.
    We try to split into short token candidates without inventing text.
    """
    s = (cell or "").strip()
    if not s:
        return []
    sl = s.lower()
    if sl in {"-", "na", "n/a", "none", "unknown", "unclear"}:
        return []
    # Normalize common separators
    s = s.replace("\n", " ").replace("\t", " ")
    # Split on punctuation / connectors
    parts = re.split(r"[;|•·∙/]|,|\band\b|\bor\b|\b및\b|\b또는\b", s, flags=re.IGNORECASE)
    out = []
    for p in parts:
        t = " ".join(p.strip().split())
        if not t:
            continue
        # Keep short (avoid full sentences); prefer first 1-6 words then trim later
        out.append(t)
    return out


def extract_exam_point_tokens_by_entity(
    master_table_markdown_kr: str,
    *,
    max_tokens_per_entity: int = 2,
    max_words_per_token: int = 3,
) -> Dict[str, List[str]]:
    """
    Deterministically extract up to N short 시험포인트 tokens per entity from the master table.
    No invention: if ambiguous, return fewer tokens (possibly empty list).
    """
    headers, rows = _parse_markdown_table(master_table_markdown_kr)
    if not headers or not rows:
        return {}
    # Find entity + exam point columns
    entity_idx = 0
    exam_idx = None
    for i, h in enumerate(headers):
        if i == 0:
            entity_idx = i
        if "시험포인트" in (h or ""):
            exam_idx = i
    if exam_idx is None:
        return {}

    result: Dict[str, List[str]] = {}
    for r in rows:
        if entity_idx >= len(r) or exam_idx >= len(r):
            continue
        entity = " ".join(str(r[entity_idx] or "").strip().split())
        if not entity:
            continue
        cell = str(r[exam_idx] or "").strip()
        cands = _split_exam_point_cell(cell)
        tokens: List[str] = []
        for c in cands:
            # Convert to token (max_words_per_token words)
            words = c.split()
            tok = " ".join(words[:max_words_per_token]).strip()
            if not tok:
                continue
            # Drop trivial tokens
            if tok.lower() in {"-", "na", "n/a", "none", "unknown", "unclear"}:
                continue
            if tok not in tokens:
                tokens.append(tok)
            if len(tokens) >= max_tokens_per_entity:
                break
        result[entity] = tokens
    return result


def _extract_allowed_text_en(
    *,
    compact_table_md: str,
    visual_type_category: str,
    master_table_markdown_kr: Optional[str] = None,
    max_phrase_candidates: int = 600,
) -> List[str]:
    """
    Build a conservative allowlist of EN tokens/phrases derived from the compact table.
    This is used as a prompt-side contract (no OCR).
    """
    headers, rows = _parse_markdown_table(compact_table_md)
    allowed: List[str] = []

    # Expect 4-col compact table (Entity_EN, ModalityTokens_EN, CueToken_EN, ExamPointToken_EN)
    col_idx = {h.strip(): i for i, h in enumerate(headers or [])}
    ent_i = col_idx.get("Entity_EN", 0)
    mod_i = col_idx.get("ModalityTokens_EN", 1)
    cue_i = col_idx.get("CueToken_EN", 2)

    def add(s: str) -> None:
        t = " ".join((s or "").strip().split())
        if not t:
            return
        # EN-only + anti-taxonomy hygiene: never allow Korean or taxonomy separators into EN allowlist.
        # NOTE: we strip Korean characters elsewhere too, but keep this hard stop to avoid leakage.
        if _has_korean_chars(t):
            return
        # Hard ban: never allow taxonomy separators into EN allowlist (avoid group paths and guard regressions).
        if ">" in t:
            return
        # Avoid common markdown/table triggers inside tokens.
        t = t.replace("|", "/").replace("```", "").replace("`", "").strip()
        if not t:
            return
        if t not in allowed:
            allowed.append(t)

    def _extract_en_phrases_from_master_table_cells(
        master_md: str,
        *,
        max_words_per_phrase: int = 6,
        max_phrases: int = 600,
    ) -> List[str]:
        """
        Deterministically extract short EN phrase candidates (1–6 words) from original master table cells.
        This expands ALLOWED_TEXT without permitting Korean or taxonomy/breadcrumb leakage.
        """
        if not master_md:
            return []

        headers2, rows2 = _parse_markdown_table(master_md)
        if not headers2 or not rows2:
            return []

        # Split on punctuation/structure delimiters that commonly separate short phrases.
        split_re = re.compile(r"[;\n\r]+|[.,:]+|[()\[\]{}]+|/|\\\|•|·|—|–")

        def clean_cell(x: Any) -> str:
            t = str(x or "")
            # Remove markdown-ish triggers and taxonomy separators.
            t = t.replace("```", "").replace("`", "").replace("|", " ")
            t = t.replace(">", " ")
            t = t.replace("#", " ").replace("*", " ")
            # EN-only bias: drop Hangul, keep any remaining English.
            t = _strip_korean_chars(t)
            t = " ".join(t.split()).strip()
            return t

        def phrase_ok(p: str) -> bool:
            if not p:
                return False
            if _has_korean_chars(p):
                return False
            if ">" in p:
                return False
            # Must contain at least one Latin letter to avoid numeric-only junk.
            if re.search(r"[A-Za-z]", p) is None:
                return False
            # Avoid obvious metadata-ish tokens
            if re.search(r"\bgroup_path\b", p, flags=re.IGNORECASE):
                return False
            # Bound size/words
            words = p.split()
            if not (1 <= len(words) <= max_words_per_phrase):
                return False
            if len(p) > 90:
                return False
            return True

        out: List[str] = []
        seen: set = set()

        for r in rows2:
            for cell in (r or []):
                s = clean_cell(cell)
                if not s:
                    continue
                # Break into fragments, then chunk long fragments into fixed-size word groups.
                for frag in (f.strip() for f in split_re.split(s)):
                    if not frag:
                        continue
                    words = frag.split()
                    if not words:
                        continue
                    # Chunk deterministically into groups of up to max_words_per_phrase.
                    for i in range(0, len(words), max_words_per_phrase):
                        chunk = " ".join(words[i : i + max_words_per_phrase]).strip().strip(" ,.;:/")
                        if not chunk:
                            continue
                        if not phrase_ok(chunk):
                            continue
                        if chunk in seen:
                            continue
                        seen.add(chunk)
                        out.append(chunk)
                        if len(out) >= max_phrases:
                            return out
        return out

    # Expand allowlist with phrase candidates from the ORIGINAL master table (bounded).
    # This is critical for richer explanatory text while still enforcing ALLOWED_TEXT-only output.
    if master_table_markdown_kr:
        try:
            m = int(max_phrase_candidates) if isinstance(max_phrase_candidates, int) else 600
        except Exception:
            m = 600
        m = max(0, min(m, 2000))
        for p in _extract_en_phrases_from_master_table_cells(master_table_markdown_kr, max_phrases=m):
            add(p)

    for r in rows or []:
        if ent_i < len(r):
            add(r[ent_i])
        if mod_i < len(r):
            # split modality tokens (keep raw tokens too)
            raw = str(r[mod_i] or "").strip()
            for p in re.split(r"[/,]", raw):
                add(p)
            add(raw)
        if cue_i < len(r):
            add(r[cue_i])

    # Add a minimal fixed allowlist for structural labels (always include the global ones used by templates).
    for lab in [
        "Explanation:",
        "Key takeaways:",
    ]:
        add(lab)

    # Category-specific labels (QC/Equipment)
    v = (visual_type_category or "").strip().lower()
    if v in ("qc", "equipment"):
        for lab in [
            "Acquire", "Measure", "Compare", "Action",
            "Metric:", "Action:", "Failure mode:", "Component:", "Function:",
            "Limitation:", "Mitigation:", "Key finding:", "Location:", "Pattern:",
        ]:
            add(lab)

    # Modality canonical tokens that are safe to show if present (kept short)
    for mod in ["CT", "MRI", "XR", "X-ray", "US", "PET", "Angio", "DSA", "NM", "Mammo", "Echo", "Fluoro"]:
        if mod not in allowed:
            allowed.append(mod)

    return sorted(allowed)


def _extract_allowed_text_kr_from_exam_points(exam_point_tokens_by_entity: Dict[str, List[str]]) -> List[str]:
    allowed: List[str] = []
    for toks in (exam_point_tokens_by_entity or {}).values():
        for t in toks or []:
            tt = " ".join(str(t).strip().split())
            if not tt:
                continue
            if tt not in allowed:
                allowed.append(tt)
    return sorted(allowed)


def _sanitize_row_snippet_text(s: str, *, keep_korean: bool) -> str:
    """
    Sanitize row-derived snippet text so it is safe to include in prompts (and safe to allow-copy).
    - Removes markdown triggers (pipes, backticks, code fences)
    - Removes taxonomy/breadcrumb separator '>' (replaces with space)
    - Removes common markdown-ish tokens (#, *)
    - Collapses whitespace
    - Optionally strips Hangul
    """
    if not s:
        return ""
    t = str(s)
    # Remove code fences/backticks; replace markdown-table pipes; remove markdown-ish heading markers.
    t = t.replace("```", "").replace("`", "")
    t = t.replace("|", " ")
    t = t.replace("#", " ").replace("*", " ")
    # Taxonomy/breadcrumb separator must never be allowed through.
    t = t.replace(">", " ")
    # Remove known metadata-ish token
    t = re.sub(r"\bgroup_path\b", " ", t, flags=re.IGNORECASE)
    # Collapse whitespace and trim
    t = " ".join(t.split()).strip()
    if not keep_korean:
        t = " ".join(_strip_korean_chars(t).split()).strip()
    # Strip trivial wrapping punctuation
    t = t.strip(" \t\r\n-–—:;,.()[]{}")
    return t


def _extract_kr_phrase_candidates_from_row(
    row_cells: List[str],
    *,
    max_items: int,
    max_words_per_item: int,
) -> List[str]:
    """
    Extract Korean (Hangul-containing) phrase snippets from a SINGLE row's cells.
    Deterministic, copy-only: returns short fragments directly present in the row.
    """
    if not row_cells:
        return []
    # Split on punctuation/structure delimiters; keep Korean chunks intact.
    split_re = re.compile(r"[;\n\r]+|[.,:]+|[()\[\]{}]+|/|\\\|•|·|—|–")
    out: List[str] = []
    seen: set = set()
    for cell in row_cells:
        raw = _sanitize_row_snippet_text(str(cell or ""), keep_korean=True)
        if not raw:
            continue
        # Only consider fragments that contain Hangul.
        if not _has_korean_chars(raw):
            continue
        for frag in (f.strip() for f in split_re.split(raw)):
            if not frag or not _has_korean_chars(frag):
                continue
            # Chunk into fixed-size word groups (eojeol groups), deterministically.
            words = frag.split()
            if not words:
                continue
            mw = max(1, int(max_words_per_item or 6))
            for i in range(0, len(words), mw):
                chunk = " ".join(words[i : i + mw]).strip()
                chunk = _sanitize_row_snippet_text(chunk, keep_korean=True)
                if not chunk:
                    continue
                if not _has_korean_chars(chunk):
                    continue
                # Guard: never allow a raw '>' or taxonomy separator through (should be gone already).
                if ">" in chunk or _detect_taxonomy_path_separator(chunk):
                    continue
                if chunk in seen:
                    continue
                seen.add(chunk)
                out.append(chunk)
                if len(out) >= max_items:
                    return out
    return out


def _extract_en_phrase_candidates_from_row(
    row_cells: List[str],
    *,
    max_items: int,
    max_words_per_item: int,
) -> List[str]:
    """
    Extract short English phrase snippets from a SINGLE row's cells (EN-only bias).
    Used for per-entity grounding blocks (not as the global EN allowlist).
    """
    if not row_cells:
        return []
    split_re = re.compile(r"[;\n\r]+|[.,:]+|[()\[\]{}]+|/|\\\|•|·|—|–")
    out: List[str] = []
    seen: set = set()
    mw = max(1, int(max_words_per_item or 8))
    for cell in row_cells:
        raw = _sanitize_row_snippet_text(str(cell or ""), keep_korean=False)
        if not raw:
            continue
        # EN-only bias: must contain at least one Latin letter.
        if re.search(r"[A-Za-z]", raw) is None:
            continue
        for frag in (f.strip() for f in split_re.split(raw)):
            if not frag:
                continue
            # Chunk deterministically into fixed-size word groups.
            words = frag.split()
            if not words:
                continue
            for i in range(0, len(words), mw):
                chunk = " ".join(words[i : i + mw]).strip().strip(" ,.;:/")
                chunk = _sanitize_row_snippet_text(chunk, keep_korean=False)
                if not chunk:
                    continue
                if _has_korean_chars(chunk):
                    continue
                if ">" in chunk or _detect_taxonomy_path_separator(chunk):
                    continue
                if re.search(r"[A-Za-z]", chunk) is None:
                    continue
                if chunk in seen:
                    continue
                seen.add(chunk)
                out.append(chunk)
                if len(out) >= max_items:
                    return out
    return out


def extract_entity_row_text_by_entity(
    master_table_markdown_kr: str,
    *,
    max_en_items_per_entity: int = 18,
    max_kr_items_per_entity: int = 18,
    max_en_words_per_item: int = 8,
    max_kr_words_per_item: int = 6,
) -> Dict[str, Dict[str, List[str]]]:
    """
    Build per-entity row grounding snippets (EN/KR) directly from the ORIGINAL master table.
    Keys are EN-cleaned entity names (Hangul stripped; empty parens removed) to match prompt-side entity names.
    Returns:
      { entity_name_en_clean: { "en": [...], "kr": [...] } }
    """
    headers, rows = _parse_markdown_table(master_table_markdown_kr)
    if not headers or not rows:
        return {}
    ent_i = 0
    result: Dict[str, Dict[str, List[str]]] = {}
    for r in rows:
        if not r or ent_i >= len(r):
            continue
        ent_raw = " ".join(str(r[ent_i] or "").strip().split())
        if not ent_raw:
            continue
        ent_clean = " ".join(_strip_korean_chars(ent_raw).split()).strip()
        ent_clean = re.sub(r"\(\s*\)", "", ent_clean).strip()
        if not ent_clean:
            continue
        # Use entire row as source for snippets (row-only grounding).
        row_cells = [str(c or "") for c in r]
        en_snips = _extract_en_phrase_candidates_from_row(
            row_cells,
            max_items=max(0, int(max_en_items_per_entity or 0)),
            max_words_per_item=max_en_words_per_item,
        )
        kr_snips = _extract_kr_phrase_candidates_from_row(
            row_cells,
            max_items=max(0, int(max_kr_items_per_entity or 0)),
            max_words_per_item=max_kr_words_per_item,
        )
        result[ent_clean] = {"en": en_snips, "kr": kr_snips}
    return result


def _extract_allowed_text_kr_from_entity_row_text(
    entity_row_text_by_entity: Dict[str, Dict[str, List[str]]],
    *,
    max_items_total: int = 600,
) -> List[str]:
    """
    Aggregate Korean snippet candidates from ENTITY_ROW_TEXT_BY_ENTITY into a global allowlist.
    """
    allowed: List[str] = []
    if not entity_row_text_by_entity:
        return []
    for ent in sorted(entity_row_text_by_entity.keys()):
        kr_list = (entity_row_text_by_entity.get(ent) or {}).get("kr") or []
        for t in kr_list:
            tt = _sanitize_row_snippet_text(str(t or ""), keep_korean=True)
            if not tt:
                continue
            if not _has_korean_chars(tt):
                continue
            if ">" in tt or _detect_taxonomy_path_separator(tt):
                continue
            if tt not in allowed:
                allowed.append(tt)
            if len(allowed) >= max_items_total:
                return allowed
    return sorted(allowed)


def _format_entity_row_text_by_entity_block(
    entity_row_text_by_entity: Dict[str, Dict[str, List[str]]],
    *,
    max_entities: int = 12,
    max_items_per_lang: int = 14,
) -> str:
    """
    Append-only prompt block providing per-entity copy-only snippets (EN/KR) from THAT entity's row.
    This is the sole permitted source for Korean in table visuals.
    """
    if not entity_row_text_by_entity:
        return ""
    lines: List[str] = []
    lines.append("ENTITY_ROW_TEXT_BY_ENTITY (AUTHORITATIVE; COPY-ONLY SNIPPETS):")
    lines.append("- Purpose: You may use these snippets ONLY to build 'Explanation:' lines and ONLY for the matching entity.")
    lines.append("- Korean rule: Korean is allowed ONLY if it appears EXACTLY in the KR snippets for that entity (no translation, no rewriting, no new Korean).")
    lines.append("- Leak rule: Never output any taxonomy/breadcrumb/path strings; if any snippet seems to contain such leakage, OMIT it.")
    # Deterministic, bounded output
    ents = sorted(entity_row_text_by_entity.keys())
    for ent in ents[: max(0, int(max_entities or 0))]:
        d = entity_row_text_by_entity.get(ent) or {}
        en_list = (d.get("en") or [])[: max(0, int(max_items_per_lang or 0))]
        kr_list = (d.get("kr") or [])[: max(0, int(max_items_per_lang or 0))]
        lines.append(f"- {ent}:")
        if en_list:
            lines.append("  - EN:")
            for t in en_list:
                tt = _sanitize_row_snippet_text(str(t or ""), keep_korean=False)
                if tt:
                    lines.append(f"    - {tt}")
        if kr_list:
            lines.append("  - KR:")
            for t in kr_list:
                tt = _sanitize_row_snippet_text(str(t or ""), keep_korean=True)
                if tt:
                    lines.append(f"    - {tt}")
    return "\n".join(lines).strip()


def _format_allowed_text_block(
    *,
    allowed_text_en: List[str],
    allowed_text_kr: List[str],
    exam_point_tokens_by_entity: Dict[str, List[str]],
) -> str:
    """
    Append-only prompt block for S4_CONCEPT.
    The model must use ONLY these tokens/phrases for text (prompt-level contract).
    """
    lines: List[str] = []
    lines.append("ALLOWED_TEXT (AUTHORITATIVE):")
    lines.append("- English: Use ONLY these tokens/phrases for ANY English text on the slide:")
    # NOTE: richer infographic text requires printing a larger allowlist than the previous 200-item cap.
    # Keep configurable to balance safety vs prompt length.
    try:
        max_items = int(os.getenv("S3_ALLOWED_TEXT_EN_MAX_ITEMS", "600").strip())
    except Exception:
        max_items = 600
    max_items = max(50, min(max_items, 2000))
    for t in (allowed_text_en or [])[:max_items]:
        lines.append(f"  - {t}")
    if allowed_text_kr:
        lines.append("- Korean: Allowed ONLY in 'Explanation:' lines, and ONLY by copying EXACT snippets from ENTITY_ROW_TEXT_BY_ENTITY (row-only).")
        lines.append("- Korean: Do NOT translate; do NOT rewrite; do NOT invent new Korean; do NOT use Korean in titles/headers/takeaways.")
        lines.append("- Korean allowlist (row-derived; copy-only):")
        try:
            max_kr_items = int(os.getenv("S3_ALLOWED_TEXT_KR_MAX_ITEMS", "600").strip())
        except Exception:
            max_kr_items = 600
        max_kr_items = max(0, min(max_kr_items, 2000))
        for t in (allowed_text_kr or [])[:max_kr_items]:
            lines.append(f"  - {t}")
    else:
        lines.append("- Korean: FORBIDDEN (no row-derived Korean snippets were provided).")
    # Entity-level exam point tokens (up to 2)
    if exam_point_tokens_by_entity:
        lines.append("EXAM_POINT_TOKENS_BY_ENTITY (up to 2 tokens per entity):")
        for ent in sorted(exam_point_tokens_by_entity.keys()):
            toks = exam_point_tokens_by_entity.get(ent) or []
            if not toks:
                continue
            # IMPORTANT: avoid markdown-like separators (e.g., '|') anywhere in prompts,
            # because some models will treat that as a markdown-table signal and copy it.
            joined = " / ".join(toks[:2])
            # EN-only hygiene: entity names can contain Korean in parentheses (from S1 tables).
            # Strip Hangul so the prompt-hygiene guard can run in fail mode.
            ent_clean = " ".join(_strip_korean_chars(str(ent or "")).split()).strip()
            # Drop empty parentheses left behind after stripping Korean, e.g., "( )".
            ent_clean = re.sub(r"\(\s*\)", "", ent_clean).strip()
            lines.append(f"- {ent_clean}: {joined}")
    return "\n".join(lines).strip()


def _sanitize_no_markdown_text(s: str) -> str:
    """
    Best-effort sanitizer to remove markdown/table-signaling characters from *non-authoritative*
    hint text that may be appended into prompts (e.g., cluster hints).
    We keep meaning while eliminating common markdown triggers.
    """
    if not s:
        return ""
    t = str(s)
    # Remove code fences/backticks; replace table pipes with slashes.
    # Also remove common taxonomy/path separators and markdown-ish heading markers.
    t = t.replace("```", "").replace("`", "")
    t = t.replace("|", "/")
    t = t.replace(">", "/")
    t = t.replace("#", "")
    t = t.replace("*", "")
    # Collapse excessive whitespace
    t = "\n".join([" ".join(ln.strip().split()) for ln in t.splitlines()]).strip()
    return t


def _detect_markdown_table_leak(prompt_text: str) -> List[str]:
    """
    Detect markdown-table-like leakage signatures in a rendered prompt.
    We intentionally do NOT flag ordinary hyphen bullets (templates are bullet-heavy).
    Returns a list of human-readable findings (empty if OK).
    """
    t = str(prompt_text or "")
    if not t:
        return []
    findings: List[str] = []
    lines = t.splitlines()

    # Code fences are a strong markdown signal.
    if "```" in t or "~~~" in t:
        findings.append("contains_code_fence")

    # Common markdown table separator line.
    if re.search(r"\|\s*---", t):
        findings.append("contains_markdown_table_separator('|---')")

    # Any line that *looks* like a markdown table row: starts with '|' and ends with '|'
    # and has multiple pipe separators.
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if s.startswith("|") and s.endswith("|") and s.count("|") >= 3:
            findings.append("contains_markdown_table_row_line")
            break

    return sorted(set(findings))


def _has_korean_chars(s: str) -> bool:
    """Return True if string contains Hangul syllables or Hangul Jamo."""
    if not s:
        return False
    return re.search(r"[가-힣ㄱ-ㅎㅏ-ㅣ]", s) is not None


def _detect_taxonomy_path_separator(s: str) -> bool:
    """
    Detect taxonomy/breadcrumb separators of the form "token > token" with flexible spacing,
    while avoiding false positives like arrows ("->") and numeric comparisons ("> 8", ">= 8").
    """
    if not s:
        return False
    # token>token (or token > token), both sides must look like an identifier-ish token.
    # Exclude "->" and "=>", and exclude ">=".
    # Require identifier-ish tokens on both sides (start with a letter or underscore) to avoid
    # numeric comparisons like "> 8". Still catch underscore-heavy taxonomy paths.
    return (
        # IMPORTANT: do not allow matching across newlines. Cross-line matches are a common
        # false positive when a line ends with a bare '>' (e.g., truncated exam-point tokens)
        # and the next line begins with an identifier-ish token.
        re.search(r"(?<![-=])\b[A-Za-z_][A-Za-z0-9_]*[ \t]*>(?!=)[ \t]*[A-Za-z_][A-Za-z0-9_]*\b", s)
        is not None
    )


def _find_snake_case_tokens(s: str, *, max_hits: int = 5) -> List[str]:
    """
    Heuristic: extract lower_snake_case tokens (potentially path-like) for regression detection.
    Kept optional behind an env flag to avoid false positives on legitimate tokens.
    """
    if not s:
        return []
    hits = re.findall(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b", s)
    if not hits:
        return []
    uniq = sorted(set(hits))
    return uniq[:max_hits]


def _filter_exam_point_tokens_en_only(exam_point_tokens_by_entity: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    For EN-only modes: drop any exam-point tokens that contain Korean characters.
    We do NOT translate; we omit.
    """
    filtered: Dict[str, List[str]] = {}
    for ent, toks in (exam_point_tokens_by_entity or {}).items():
        kept: List[str] = []
        for t in toks or []:
            tt = " ".join(str(t).strip().split())
            if not tt:
                continue
            if _has_korean_chars(tt):
                continue
            # Leak-prevention: do not carry over tokens that include '>' into the prompt/allowlist.
            # These often represent comparisons (e.g., "TSH > 30") and can cause breadcrumb-like
            # leakage or guard false positives when truncated across lines.
            if ">" in tt:
                continue
            if tt not in kept:
                kept.append(tt)
        filtered[ent] = kept
    return filtered


def _strip_korean_chars(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"[가-힣ㄱ-ㅎㅏ-ㅣ]+", "", s)


def markdown_table_to_plain_rows(
    md_table: str,
    *,
    strip_korean: bool = True,
    max_rows: Optional[int] = None,
) -> str:
    """
    Convert a markdown table into a plain, line-based representation that is:
    - non-markdown (no '|' table pipes)
    - safe for prompt injection (best-effort)
    - optionally EN-only biased by stripping Korean characters from headers/cells
    """
    raw = str(md_table or "").strip()
    if not raw:
        return ""

    headers, rows = _parse_markdown_table(raw)
    if not headers or not rows:
        # Fallback: ensure we do not leak markdown-table pipes into the prompt.
        t = raw.replace("|", "/").replace("```", "").replace("`", "")
        return _strip_korean_chars(t) if strip_korean else t

    def sanitize(x: Any) -> str:
        s = str(x or "")
        # Remove prompt-leak triggers (best-effort): pipes/backticks/fences and taxonomy separator.
        # NOTE: We do NOT attempt to preserve markdown semantics; we want plain, model-safe text.
        s = s.replace("|", "/").replace("```", "").replace("`", "")
        s = s.replace(">", "/")
        s = " ".join(s.split())
        if strip_korean:
            s = " ".join(_strip_korean_chars(s).split())
        return s.strip()

    labels: List[str] = []
    for i, h in enumerate(headers):
        hh = sanitize(h)
        labels.append(hh if hh else f"Col{i+1}")

    use_rows = rows[:max_rows] if (isinstance(max_rows, int) and max_rows > 0) else rows

    out: List[str] = []
    out.append("COLUMNS: " + "; ".join(labels))
    for i, r in enumerate(use_rows, start=1):
        parts: List[str] = []
        for j, lab in enumerate(labels):
            cell = sanitize(r[j] if j < len(r) else "")
            if cell:
                parts.append(f"{lab}={cell}")
        out.append(f"ROW {i}: " + ("; ".join(parts) if parts else "(empty)"))
    return "\n".join(out).strip()


def build_concept_image_table(master_table_markdown_kr: str) -> str:
    """
    Deterministically extract a compact 4-column tokenized table from master table.
    
    Output columns:
    - Entity_EN: Entity name (English term only)
    - ModalityTokens_EN: Modality keywords (CT, MRI, XR, US, etc.)
    - CueToken_EN: First short imaging cue phrase (1-2 words)
    - ExamPointToken_EN: First short EN token (1-3 words) from 시험포인트 (EN-only; Korean is omitted)
    
    Args:
        master_table_markdown_kr: Full master table markdown (mixed KR/EN)
    
    Returns:
        Markdown table string with exactly 4 columns
    """
    headers, rows = _parse_markdown_table(master_table_markdown_kr)
    if not headers or not rows:
        # Fallback: return empty table structure
        return "| Entity_EN | ModalityTokens_EN | CueToken_EN | ExamPointToken_EN |\n| --- | --- | --- | --- |\n"
    
    # Find column indices (case-insensitive, flexible matching)
    entity_col_idx = None
    modality_col_idx = None
    cue_col_idx = None
    exampoint_col_idx = None
    
    for i, h in enumerate(headers):
        h_lower = h.lower()
        # Entity name column (usually first or contains "entity")
        if entity_col_idx is None and ("entity" in h_lower or "name" in h_lower or i == 0):
            entity_col_idx = i
        # Modality columns
        if modality_col_idx is None and ("modality" in h_lower or "모달리티" in h):
            modality_col_idx = i
        # Cue columns (핵심 영상 단서, 모달리티별 핵심 영상 소견)
        if cue_col_idx is None and ("핵심" in h or "영상 단서" in h or "영상 소견" in h or "key" in h_lower or "cue" in h_lower):
            cue_col_idx = i
        # 시험포인트 column
        if exampoint_col_idx is None and ("시험포인트" in h or "exam" in h_lower and "point" in h_lower):
            exampoint_col_idx = i
    
    # Helper to extract English modality tokens
    def extract_modality_tokens(text: str) -> str:
        """Extract modality keywords (CT, MRI, XR, US, PET, etc.) from text."""
        if not text:
            return ""
        text_upper = text.upper()
        modalities = []
        modality_keywords = ["CT", "MRI", "XR", "X-RAY", "US", "ULTRASOUND", "PET", "PET-CT", "ANGIO", "DSA", "NM", "NUCLEAR", "MAMMO", "MAMMOGRAPHY"]
        for mod in modality_keywords:
            if mod in text_upper and mod not in modalities:
                modalities.append(mod)
        # Limit to 3 modalities max
        return " / ".join(modalities[:3]) if modalities else ""
    
    # Helper to extract first short cue token (1-2 words)
    def extract_cue_token(text: str) -> str:
        """Extract first short imaging cue phrase (1-2 words) from text."""
        if not text:
            return ""
        # Remove common prefixes/suffixes and split
        text_clean = text.replace("핵심 영상 단서:", "").replace("Key finding:", "").strip()
        # Try to find English phrases first
        words = text_clean.split()
        # Look for common imaging cues (1-2 words)
        if len(words) >= 1:
            # Take first 1-2 meaningful words (skip articles, prepositions)
            skip_words = {"the", "a", "an", "of", "in", "on", "at", "to", "for"}
            meaningful = [w for w in words[:3] if w.lower() not in skip_words]
            if meaningful:
                return " ".join(meaningful[:2])
        return ""
    
    # Helper to extract first short EN token (1-3 words) from 시험포인트 (EN-only; omit Korean)
    def extract_exampoint_token_en(text: str) -> str:
        """Extract first short EN token (1-3 words) from 시험포인트 column. Drop tokens containing Korean."""
        if not text:
            return ""
        # Split deterministically into candidates, then keep the first EN-only candidate.
        cands = _split_exam_point_cell(str(text))
        for c in cands:
            tok = " ".join(str(c).strip().split())
            if not tok:
                continue
            if _has_korean_chars(tok):
                continue
            # Trim to max 3 words
            tok = " ".join(tok.split()[:3]).strip().rstrip(".,;:")
            # Avoid taxonomy/markdown triggers in tokens
            tok = tok.replace("|", "/").replace("```", "").replace("`", "").replace(">", "/").strip()
            if tok:
                return tok
        return ""
    
    # Build compact table rows
    compact_rows = []
    for row in rows:
        if len(row) <= max(filter(None, [entity_col_idx, modality_col_idx, cue_col_idx, exampoint_col_idx] or [0])):
            continue
        
        entity_en = str(row[entity_col_idx] if entity_col_idx is not None and entity_col_idx < len(row) else "").strip()
        # If entity name is mixed KR/EN, try to extract English part (simple heuristic)
        if entity_en and not any(ord(c) >= 0xAC00 and ord(c) <= 0xD7A3 for c in entity_en):
            # Already English or mixed, use as-is
            pass
        else:
            # Try to find English term in parentheses or after Korean
            # Simple: if contains parentheses, might have English inside
            if "(" in entity_en and ")" in entity_en:
                import re
                match = re.search(r'\(([^)]+)\)', entity_en)
                if match:
                    entity_en = match.group(1).strip()
        
        modality_tokens = ""
        if modality_col_idx is not None and modality_col_idx < len(row):
            modality_tokens = extract_modality_tokens(row[modality_col_idx])
        
        cue_token = ""
        if cue_col_idx is not None and cue_col_idx < len(row):
            cue_token = extract_cue_token(row[cue_col_idx])
        
        exampoint_token = ""
        if exampoint_col_idx is not None and exampoint_col_idx < len(row):
            exampoint_token = extract_exampoint_token_en(row[exampoint_col_idx])
        
        compact_rows.append([entity_en, modality_tokens, cue_token, exampoint_token])
    
    # Build markdown table
    header = "| Entity_EN | ModalityTokens_EN | CueToken_EN | ExamPointToken_EN |\n"
    separator = "| --- | --- | --- | --- |\n"
    row_lines = []
    for row in compact_rows:
        # Escape pipes in cell content
        escaped_row = [cell.replace("|", "\\|") for cell in row]
        row_lines.append("| " + " | ".join(escaped_row) + " |\n")
    
    return header + separator + "".join(row_lines)


def anatomy_map_has_sufficient_location_info(master_table_markdown_kr: str) -> bool:
    """
    Heuristic: if location/adjacency info is weak, Anatomy_Map tends to force guesses -> wrong drawings.
    Uses ONLY the table content (no external knowledge).
    """
    headers, rows = _parse_markdown_table(master_table_markdown_kr)
    if not headers or not rows:
        return False

    loc_markers = ("위치", "인접", "location", "adjacent", "landmark", "region")
    loc_idxs = [i for i, h in enumerate(headers) if any(m in (h or "").lower() for m in loc_markers)]
    if not loc_idxs:
        return False

    def _meaningful(s: str) -> bool:
        t = (s or "").strip()
        if not t:
            return False
        tl = t.lower()
        if tl in {"-", "na", "n/a", "none", "unknown", "unclear"}:
            return False
        return True

    N = min(6, len(rows))
    meaningful_rows = 0
    for r in rows[:N]:
        if any(_meaningful(r[j]) for j in loc_idxs if j < len(r)):
            meaningful_rows += 1

    if meaningful_rows < 2:
        return False
    if (meaningful_rows / max(1, N)) < 0.3:
        return False
    return True


# =========================
# ImageSpec Compiler
# =========================

def is_concept_group(visual_type_category: str) -> bool:
    """
    Determine if a group should use CONCEPT image routing instead of EXAM.
    
    QC and Equipment groups are routed to CONCEPT because they require
    diagrams/graphs/equipment schematics rather than clinical PACS images.
    
    Args:
        visual_type_category: Visual type category from S1 structure
        
    Returns:
        True if group should use CONCEPT routing, False otherwise
    """
    v = (visual_type_category or "").strip().lower()
    return v in ("qc", "equipment")


def compile_concept_image_spec(
    *,
    run_tag: str,
    group_id: str,
    entity_id: str,
    entity_name: str,
    card_role: str,
    card: Dict[str, Any],
    image_hint: Dict[str, Any],
    s1_visual_context: Dict[str, Any],
    prompt_bundle: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compile CONCEPT image spec for QC/Equipment groups.
    
    CONCEPT images are educational diagrams/graphs/equipment schematics
    that allow short labels, axis titles, and simple annotations.
    They do NOT require modality/anatomy (clinical imaging prerequisites).
    
    Args:
        run_tag: Run identifier
        group_id: Group identifier
        entity_id: Entity identifier
        entity_name: Entity name
        card_role: Q1 or Q2
        card: Full card dict (for answer extraction and prompt context)
        image_hint: S2 image_hint object (may be minimal or missing)
        s1_visual_context: S1 visual context (contains visual_type_category)
        prompt_bundle: Prompt bundle dict (if None, will load from base_dir)
    
    Returns:
        Image spec dict for S4 consumption (spec_kind="S2_CARD_CONCEPT")
    """
    visual_type = str(s1_visual_context.get("visual_type_category", "General")).strip()
    # Resolve policy with visual_type_category for QC group special handling
    policy = resolve_image_policy(card_role, visual_type_category=visual_type)
    
    # Extract card text for prompt context (deterministic, no LLM)
    front_text = str(card.get("front") or "").strip()
    back_text = str(card.get("back") or "").strip()
    answer_text = extract_answer_text(card, card_role)
    
    # Extract minimal info from image_hint (optional for CONCEPT)
    modality = str(image_hint.get("modality_preferred") or "").strip()
    anatomy_region = str(image_hint.get("anatomy_region") or "").strip()
    key_findings = image_hint.get("key_findings_keywords") or []
    if not isinstance(key_findings, list):
        key_findings = []
    
    # Build short context strings for prompt (1-2 lines max)
    # Extract first line or first 100 chars
    front_short = front_text.split("\n")[0].strip()[:100] if front_text else ""
    answer_text_short = answer_text[:100] if answer_text else ""
    
    # Extract keywords from back text (simple word extraction, no LLM)
    # Look for common patterns or use first few words
    keywords_parts = []
    if back_text:
        # Take first 3-5 meaningful words from back
        words = back_text.split()[:5]
        keywords_parts = [w.strip() for w in words if len(w.strip()) > 2][:3]
    
    # Add key_findings if available
    if key_findings:
        keywords_parts.extend([str(k).strip() for k in key_findings[:3]])
    
    keywords_or_fallback = ", ".join(keywords_parts) if keywords_parts else "generic concept diagram"
    
    # Load prompt templates
    if prompt_bundle is None:
        try:
            prompt_bundle = load_prompt_bundle(".")
        except Exception as e:
            raise RuntimeError(
                f"S3 FAIL: Cannot load prompt bundle for CONCEPT image: {e}"
            ) from e
    
    prompts = prompt_bundle.get("prompts", {})
    
    # Load CONCEPT system prompt
    system_key = "S4_CONCEPT_SYSTEM"
    system_template = prompts.get(system_key, "")
    if not system_template:
        raise ValueError(
            f"S3 FAIL: Missing prompt template: {system_key}. "
            f"Available keys: {sorted(prompts.keys())}"
        )
    
    # Load CONCEPT user prompt based on visual_type_category
    # NOTE: For CARD images (S2_CARD_CONCEPT), we need card text context, not table content.
    # Table-based templates (QC, Equipment, etc.) are for S1_TABLE_VISUAL only.
    # For card images, use card-text-based template.
    
    # Check if this is a card image (not table visual) - card images need card text context
    # Card images should use card-text-based template, not table-based template
    user_template = None
    
    # Try card-specific template first (if exists in future)
    card_template_key = f"S4_CONCEPT_USER__{visual_type}_CARD"
    user_template = prompts.get(card_template_key, "")
    
    # If no card-specific template, use card-text-based fallback (not table-based)
    if not user_template:
        # Card image template: uses card text (front, answer, keywords)
        user_template = (
            "TASK:\n"
            "Generate a SINGLE 16:9 concept diagram for this specific flashcard question.\n\n"
            "CARD CONTEXT (AUTHORITATIVE):\n"
            "- Question: {front_short}\n"
            "- Correct answer: {answer_text_short}\n"
            "- Explanation keywords: {keywords_or_fallback}\n"
            "- Entity: {entity_name}\n\n"
            "DIAGRAM REQUIREMENTS:\n"
            "- Create a diagram that directly supports answering the question above.\n"
            "- The diagram must illustrate the concept needed to answer: \"{front_short}\"\n"
            "- Include visual elements that help understand the answer: {answer_text_short}\n"
            "- Style: Minimal, high-contrast, lecture-slide style.\n"
            "- Allow short labels, axis titles, simple arrows, and 1–3 short annotations.\n"
            "- Avoid long paragraphs. No patient data. No watermark. No brand logos.\n"
            "- Single panel only. No collage.\n\n"
        )
        
        # Add visual-type-specific guidance
        if visual_type.lower() == "qc":
            user_template += (
                "QC-SPECIFIC:\n"
                "- Prefer: plot/curve showing the metric, checklist flow, or parameter diagram.\n"
                "- The diagram should help visualize the QC concept being tested.\n"
            )
        elif visual_type.lower() == "equipment":
            user_template += (
                "EQUIPMENT-SPECIFIC:\n"
                "- Prefer: labeled schematic blocks showing components and signal flow.\n"
                "- The diagram should help understand the equipment principle being tested.\n"
            )
    
    # Format user template with placeholders
    # Try to use template placeholders, but fallback to simple string replacement
    image_hint_v2 = card.get("image_hint_v2") if isinstance(card, dict) else None
    
    # Apply deterministic view/sequence completion if missing (for CONCEPT, modality/anatomy may be optional)
    view_or_sequence_source = "hint_v2"
    if isinstance(image_hint_v2, dict) and image_hint_v2 and modality and anatomy_region:
        image_hint_v2, view_or_sequence_source = apply_default_view_sequence(
            image_hint_v2, modality, anatomy_region
        )
        # Optional: attach conservative CT windowing hint if inferable
        image_hint_v2, _wh, _wh_source = apply_windowing_hint(
            image_hint_v2,
            modality=modality,
            anatomy_region=anatomy_region,
        )
    
    constraint_block, sufficiency_flags, requires_human_review = build_constraint_block(
        image_hint_v2 if isinstance(image_hint_v2, dict) else None,
        exam_prompt_profile="diagram",
    )
    try:
        user_formatted = safe_prompt_format(
            user_template,
            group_id=group_id,
            entity_name=entity_name,
            card_role=card_role,
            front_short=front_short,
            answer_text_short=answer_text_short,
            keywords_or_fallback=keywords_or_fallback,
            visual_type_category=visual_type,
            constraint_block=constraint_block,
        )
    except KeyError:
        # Fallback: simple string replacement for templates without all placeholders
        user_formatted = user_template.replace("{front_short}", front_short)
        user_formatted = user_formatted.replace("{answer_text_short}", answer_text_short)
        user_formatted = user_formatted.replace("{keywords_or_fallback}", keywords_or_fallback)
        user_formatted = user_formatted.replace("{entity_name}", entity_name)
        user_formatted = user_formatted.replace("{card_role}", card_role)
    
    # Combine system + user prompts
    prompt_en = system_template.strip() + "\n\n" + user_formatted.strip()
    
    # Build image spec
    spec = {
        "schema_version": "S3_IMAGE_SPEC_v1.0",
        "run_tag": run_tag,
        "group_id": group_id,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "card_role": card_role,
        "spec_kind": "S2_CARD_CONCEPT",
        "image_placement_final": policy["image_placement"],
        "image_asset_required": policy["image_required"],
        "modality": modality if modality else "",  # Optional for CONCEPT
        "anatomy_region": anatomy_region if anatomy_region else "",  # Optional for CONCEPT
        "key_findings_keywords": key_findings,
        "template_id": f"CONCEPT_v1__{visual_type}__{card_role}",
        "prompt_en": prompt_en,
        "answer_text": answer_text,  # Store extracted answer
        "visual_type_category": visual_type,  # Store for reference
    }

    # Pass-through v2 constraint info for auditability (optional)
    if isinstance(image_hint_v2, dict) and image_hint_v2:
        spec["image_hint_v2"] = image_hint_v2
        spec["constraint_block"] = constraint_block
        spec["sufficiency_flags"] = sufficiency_flags
        spec["requires_human_review"] = bool(requires_human_review)
        spec["view_or_sequence_source"] = view_or_sequence_source
    
    # Add optional fields if present
    view_or_sequence = str(image_hint.get("view_or_sequence") or "").strip()
    if view_or_sequence:
        spec["view_or_sequence"] = view_or_sequence
    
    # Ambiguity handling: if high ambiguity and image required, log reason
    if requires_human_review and policy["image_required"]:
        ambiguity_reasons = []
        if sufficiency_flags:
            ambiguity_reasons.extend(sufficiency_flags)
        if view_or_sequence_source == "s3_default_map" and not view_or_sequence:
            ambiguity_reasons.append("view_or_sequence_filled_from_default_map")
        if ambiguity_reasons:
            print(
                f"[S3] Warning: High ambiguity for {card_role} (Entity: {entity_name}, Group: {group_id}). "
                f"Reasons: {', '.join(ambiguity_reasons)}. "
                f"Image generation will proceed but may require human review."
            )
    
    exam_focus = str(image_hint.get("exam_focus") or "").strip()
    if exam_focus:
        spec["exam_focus"] = exam_focus
    
    return spec


def compile_image_spec(
    *,
    run_tag: str,
    group_id: str,
    entity_id: str,
    entity_name: str,
    card_role: str,
    card: Dict[str, Any],
    image_hint: Dict[str, Any],
    s1_visual_context: Dict[str, Any],
    prompt_bundle: Optional[Dict[str, Any]] = None,
    image_style: Optional[str] = None,  # CLI override: "diagram" or "realistic"
) -> Dict[str, Any]:
    """
    P0: Compile S2 image_hint into standardized image spec using prompt templates.
    
    This function routes to CONCEPT spec compilation for QC/Equipment groups,
    otherwise uses EXAM spec compilation (existing behavior).
    
    Args:
        run_tag: Run identifier
        group_id: Group identifier
        entity_id: Entity identifier
        entity_name: Entity name
        card_role: Q1 or Q2
        card: Full card dict (for answer extraction, but NOT used in prompt)
        image_hint: S2 image_hint object (AUTHORITATIVE for prompt)
        s1_visual_context: S1 visual context (used to determine CONCEPT vs EXAM routing)
        prompt_bundle: Prompt bundle dict (if None, will load from base_dir)
    
    Returns:
        Image spec dict for S4 consumption (spec_kind="S2_CARD_IMAGE" or "S2_CARD_CONCEPT")
    """
    # Check if this group should use CONCEPT routing
    visual_type = str(s1_visual_context.get("visual_type_category", "General")).strip()
    if is_concept_group(visual_type):
        # Route to CONCEPT compilation (relaxed validation, diagram-focused)
        return compile_concept_image_spec(
            run_tag=run_tag,
            group_id=group_id,
            entity_id=entity_id,
            entity_name=entity_name,
            card_role=card_role,
            card=card,
            image_hint=image_hint,
            s1_visual_context=s1_visual_context,
            prompt_bundle=prompt_bundle,
        )
    
    # Default: EXAM routing (existing behavior, strict validation)
    # Get visual_type for policy resolution (QC groups have special Q1 placement)
    visual_type = str(s1_visual_context.get("visual_type_category", "General")).strip()
    policy = resolve_image_policy(card_role, visual_type_category=visual_type)
    
    # Extract modality (required for Q1 and Q2 in EXAM lane)
    modality_raw = str(image_hint.get("modality_preferred") or "Other").strip()
    anatomy_region = str(image_hint.get("anatomy_region") or "").strip()
    key_findings = image_hint.get("key_findings_keywords") or []
    if not isinstance(key_findings, list):
        key_findings = []
    view_or_sequence = str(image_hint.get("view_or_sequence") or "").strip()
    exam_focus = str(image_hint.get("exam_focus") or "").strip()
    
    # Handle "Other" modality: infer from anatomy/entity
    modality = modality_raw
    modality_source = "image_hint"
    if not modality or modality == "Other":
        inferred_modality = infer_modality_from_anatomy(anatomy_region, entity_name)
        modality = inferred_modality
        modality_source = "s3_inferred"
        print(
            f"[S3] Warning: {card_role} modality_preferred was '{modality_raw}' (Entity: {entity_name}). "
            f"Inferred '{inferred_modality}' from anatomy_region='{anatomy_region}'. "
            f"Consider updating S2 to generate valid modality."
        )
    
    # P0: Q1 and Q2 must meet minimum modality/anatomy/keywords or FAIL (EXAM lane only)
    if card_role in ("Q1", "Q2"):
        # After inference, modality should be valid. Double-check and fail if still invalid.
        valid_modalities = {"CT", "MRI", "XR", "US", "PET", "Fluoro", "Mammo", "NM", "Echo", "Angio"}
        if modality not in valid_modalities:
            raise ValueError(
                f"S3 ImageSpec FAIL: {card_role} must have valid modality_preferred. "
                f"Entity: {entity_name}, Got: {modality} (after inference attempt). "
                f"Valid values: {sorted(valid_modalities)}"
            )
        if not anatomy_region:
            raise ValueError(
                f"S3 ImageSpec FAIL: {card_role} must have anatomy_region. "
                f"Entity: {entity_name}"
            )
        if not key_findings:
            raise ValueError(
                f"S3 ImageSpec FAIL: {card_role} must have key_findings_keywords. "
                f"Entity: {entity_name}"
            )
    
    # Extract answer text (for spec storage and prompt)
    answer_text = extract_answer_text(card, card_role)
    
    # Extract card text for prompt context (deterministic, no LLM)
    front_text = str(card.get("front") or "").strip()
    back_text = str(card.get("back") or "").strip()
    
    # Build short context strings for prompt (1-2 lines max)
    # Extract first line or first 100 chars
    front_short = front_text.split("\n")[0].strip()[:100] if front_text else ""
    answer_short = answer_text[:100] if answer_text else ""
    
    # Extract keywords from back text (simple word extraction, no LLM)
    # Take first 3-5 meaningful words from back text
    back_keywords_parts = []
    if back_text:
        # Remove "Answer:" prefix if present, then take first few words
        back_clean = back_text.replace("Answer:", "").strip()
        words = back_clean.split()[:5]
        back_keywords_parts = [w.strip() for w in words if len(w.strip()) > 2][:3]
    
    back_keywords = ", ".join(back_keywords_parts) if back_keywords_parts else "clinical findings"
    
    # Build key findings string (comma-separated, deterministic order)
    key_findings_str = ", ".join([str(k).strip() for k in key_findings if str(k).strip()])

    # Optional: v2 structured constraints from S2 (pass-through + deterministic constraint block)
    image_hint_v2 = card.get("image_hint_v2") if isinstance(card, dict) else None
    
    # Apply deterministic view/sequence completion if missing
    view_or_sequence_source = "hint_v2"
    if isinstance(image_hint_v2, dict) and image_hint_v2:
        image_hint_v2, view_or_sequence_source = apply_default_view_sequence(
            image_hint_v2, modality, anatomy_region
        )
        # Attach conservative CT windowing hint if inferable (no guessing if uncertain)
        image_hint_v2, _wh, _wh_source = apply_windowing_hint(
            image_hint_v2,
            modality=modality,
            anatomy_region=anatomy_region,
        )

    # -------------------------
    # S4_EXAM prompt profile switch (needed BEFORE constraint_block for text policy branching)
    # -------------------------
    # Default profile uses registry mapping (S5R3 is now the default).
    # Optional: select realistic/pacs-like rendering with v8 schema placeholders.
    #
    # Priority (highest to lowest):
    # 1. CLI argument --image-style (if provided)
    # 2. Environment variable S4_EXAM_PROMPT_PROFILE
    # 3. Auto-detect from run_tag (if run_tag contains "REALISTIC", use realistic)
    # 4. Default: "diagram"
    run_tag_upper = str(run_tag).upper()
    auto_detected = "realistic" if "REALISTIC" in run_tag_upper else "diagram"

    if image_style:
        exam_prompt_profile = image_style.strip().lower()
        profile_source = "CLI"
    else:
        env_value = os.getenv("S4_EXAM_PROMPT_PROFILE")
        if env_value:
            exam_prompt_profile = env_value.strip().lower()
            profile_source = "ENV"
        else:
            exam_prompt_profile = auto_detected
            profile_source = "AUTO-DETECT" if auto_detected == "realistic" else "DEFAULT"

    if profile_source in ("CLI", "ENV", "AUTO-DETECT"):
        print(
            f"[S3] Image style: {exam_prompt_profile} (source: {profile_source}, run_tag: {run_tag})",
            file=sys.stderr,
        )

    if exam_prompt_profile in ("v8_realistic", "realistic", "pacs", "v8_realistic_4x5_2k", "s5r2_realistic", "v13_realistic"):
        system_key = "S4_EXAM_SYSTEM__v13_REALISTIC"
        user_key = "S4_EXAM_USER__v13_REALISTIC"
        # Apply sign suffix for REALISTIC lane to reduce over-exaggeration
        key_findings = add_sign_suffix(key_findings)
        key_findings_str = ", ".join([str(k).strip() for k in key_findings if str(k).strip()])
    else:
        system_key = "S4_EXAM_SYSTEM"
        user_key = "S4_EXAM_USER"

    constraint_block, sufficiency_flags, requires_human_review = build_constraint_block(
        image_hint_v2 if isinstance(image_hint_v2, dict) else None,
        view_or_sequence=view_or_sequence if view_or_sequence else None,
        exam_prompt_profile=exam_prompt_profile,
    )

    # Load prompt templates
    if prompt_bundle is None:
        # Fallback: try to load from current directory
        try:
            prompt_bundle = load_prompt_bundle(".")
        except Exception as e:
            raise RuntimeError(
                f"S3 FAIL: Cannot load prompt bundle for card image: {e}"
            ) from e
    
    prompts = prompt_bundle.get("prompts", {})

    # Load system prompt
    system_template = prompts.get(system_key, "")
    if not system_template:
        raise ValueError(
            f"S3 FAIL: Missing prompt template: {system_key}. "
            f"Available keys: {sorted(prompts.keys())}"
        )
    
    # Load user prompt
    user_template = prompts.get(user_key, "")
    if not user_template:
        raise ValueError(
            f"S3 FAIL: Missing prompt template: {user_key}. "
            f"Available keys: {sorted(prompts.keys())}"
        )
    
    # Format user template with placeholders (image_hint + card context)
    user_formatted = safe_prompt_format(
        user_template,
        group_id=group_id,
        entity_name=entity_name,
        card_role=card_role,
        card_front_short=front_short,
        card_answer_short=answer_short,
        card_back_keywords=back_keywords,
        modality_preferred=modality,
        anatomy_region=anatomy_region,
        view_or_sequence=view_or_sequence if view_or_sequence else "",
        key_findings_keywords=key_findings_str,
        exam_focus=exam_focus if exam_focus else "",
        constraint_block=constraint_block,
    )
    
    # Combine system + user prompts
    prompt_en = system_template.strip() + "\n\n" + user_formatted.strip()
    
    # Build image spec
    spec = {
        "schema_version": "S3_IMAGE_SPEC_v1.0",
        "run_tag": run_tag,
        "group_id": group_id,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "card_role": card_role,
        "spec_kind": "S2_CARD_IMAGE",
        "image_placement_final": policy["image_placement"],
        "image_asset_required": policy["image_required"],
        "modality": modality,
        "modality_source": modality_source,  # "image_hint" or "s3_inferred"
        "anatomy_region": anatomy_region,
        "key_findings_keywords": key_findings,
        "template_id": f"RAD_IMAGE_v1__{modality}__{card_role}",
        "prompt_en": prompt_en,
        "answer_text": answer_text,  # Store extracted answer
    }
    spec["exam_prompt_profile"] = exam_prompt_profile
    spec["exam_prompt_keys"] = {"system_key": system_key, "user_key": user_key}

    # Pass-through v2 constraint info for auditability (optional)
    if isinstance(image_hint_v2, dict) and image_hint_v2:
        spec["image_hint_v2"] = image_hint_v2
        spec["constraint_block"] = constraint_block
        spec["sufficiency_flags"] = sufficiency_flags
        spec["requires_human_review"] = bool(requires_human_review)
        spec["view_or_sequence_source"] = view_or_sequence_source
    
    # Add optional fields if present
    if view_or_sequence:
        spec["view_or_sequence"] = view_or_sequence
    
    if exam_focus:
        spec["exam_focus"] = exam_focus
    
    return spec


def extract_cluster_table(
    master_table_markdown: str,
    entity_names: List[str],
) -> str:
    """
    Extract rows from master table matching cluster entities.
    Returns markdown table with header, separator, and matching rows only.
    
    Args:
        master_table_markdown: Full master table markdown
        entity_names: List of entity names to include in cluster table
    
    Returns:
        Markdown table string with header, separator, and matching rows
    """
    lines = master_table_markdown.strip().split("\n")
    if not lines:
        return ""
    
    # Find header row
    header_idx = None
    for i, line in enumerate(lines):
        if "|" in line and "Entity name" in line:
            header_idx = i
            break
    
    if header_idx is None:
        return ""
    
    # Extract header and separator
    result_lines = [lines[header_idx], lines[header_idx + 1]]
    
    # Normalize entity names for matching (strip bold markdown and trailing annotations)
    import re as _re_cluster
    def normalize_entity_name(name: str) -> str:
        s = name.strip()
        # Remove leading bold markers (**)
        s = _re_cluster.sub(r'^\*\*', '', s)
        # Remove trailing bold markers (**)
        s = _re_cluster.sub(r'\*\*', '', s)
        # Remove trailing annotations: semicolon or space followed by parenthetical content
        # e.g., "; (이중조영술)", " (Gantry, Tube, Detector)", " (수신증)"
        s = _re_cluster.sub(r'[;\s]\s*\([^)]*\)\s*$', '', s)
        return s.strip()
    
    normalized_entity_names = {normalize_entity_name(n) for n in entity_names}
    
    # Extract matching rows
    for line in lines[header_idx + 2:]:
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]  # Remove empty first/last
        if cells:
            cell_normalized = normalize_entity_name(cells[0])
            if cell_normalized in normalized_entity_names:
                result_lines.append(line)
    
    return "\n".join(result_lines)


def compile_table_visual_spec(
    *,
    run_tag: str,
    group_id: str,
    s1_struct: Dict[str, Any],
    prompt_bundle: Optional[Dict[str, Any]] = None,
    cluster_id: Optional[str] = None,
    infographic_style: Optional[str] = None,
    infographic_prompt: Optional[str] = None,
    infographic_hint_v2: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compile S1 table visual spec for group-level image generation.
    
    Args:
        run_tag: Run identifier
        group_id: Group identifier
        s1_struct: S1 struct dict with visual_type_category and master_table_markdown_kr
        prompt_bundle: Prompt bundle dict (if None, will load from base_dir)
        cluster_id: Optional cluster identifier (None for single infographic)
        infographic_prompt: Optional cluster-specific infographic prompt (if None, generates from table)
    
    Returns:
        Image spec dict for S4 consumption (spec_kind="S1_TABLE_VISUAL")
    """
    visual_type = str(s1_struct.get("visual_type_category", "General")).strip()
    master_table = str(s1_struct.get("master_table_markdown_kr", "")).strip()
    group_path = str(s1_struct.get("group_path", "")).strip()

    # Optional safety fallback: Anatomy_Map -> General when location/adjacency info is weak
    # Enable via env: S4_ANATOMY_MAP_FALLBACK_GENERAL=1
    visual_type_original = visual_type
    if visual_type == "Anatomy_Map" and _env_bool("S4_ANATOMY_MAP_FALLBACK_GENERAL", False):
        if not anatomy_map_has_sufficient_location_info(master_table):
            visual_type = "General"
    
    if not master_table:
        raise ValueError(
            f"S3 Table Visual FAIL: master_table_markdown_kr is empty for group {group_id}"
        )
    
    # Load prompt templates
    if prompt_bundle is None:
        # Fallback: try to load from current directory
        try:
            prompt_bundle = load_prompt_bundle(".")
        except Exception as e:
            raise RuntimeError(
                f"S3 FAIL: Cannot load prompt bundle for table visual: {e}"
            ) from e
    
    prompts = prompt_bundle.get("prompts", {})
    
    # Load system prompt
    system_key = "S4_CONCEPT_SYSTEM"
    system_template = prompts.get(system_key, "")
    if not system_template:
        raise ValueError(
            f"S3 FAIL: Missing prompt template: {system_key}. "
            f"Available keys: {sorted(prompts.keys())}"
        )
    
    # -------------------------
    # Cluster-style routing (template selection)
    # -------------------------
    # If S1 provides a cluster-level infographic_style that differs from the group visual_type_category,
    # prefer the cluster style for selecting the S4 user template (prevents template mismatch).
    template_visual_type = visual_type
    infographic_style_str = str(infographic_style or "").strip()
    if cluster_id and infographic_style_str and infographic_style_str != visual_type:
        template_visual_type = infographic_style_str

    # Load user prompt based on template_visual_type (fallback to General)
    user_key_base = f"S4_CONCEPT_USER__{template_visual_type}"
    user_template = prompts.get(user_key_base, "")
    
    # Fallback to General if specific template not found
    if not user_template:
        user_key_fallback = "S4_CONCEPT_USER__General"
        user_template = prompts.get(user_key_fallback, "")
        if not user_template:
            raise ValueError(
                f"S3 FAIL: Missing prompt template for visual_type={visual_type} "
                f"and fallback General. Available keys: {sorted(prompts.keys())}"
            )
    
    # Optional: v2 structured constraints (e.g., cluster-level topology/adjacency grounding)
    # -------------------------
    # Structured constraints normalization (table visuals)
    # -------------------------
    # For table visuals, "minimal_labels_only" conflicts with the richer Explanation/Key takeaways
    # requirements in S4 templates. If present, strip/override it so S4's text policy can apply.
    infographic_hint_v2_effective = None
    hint_text_budget_original = None
    hint_text_budget_overridden = False
    if isinstance(infographic_hint_v2, dict) and infographic_hint_v2:
        # Shallow copy is not enough; nested mutation must not affect upstream data.
        import copy as _copy

        infographic_hint_v2_effective = _copy.deepcopy(infographic_hint_v2)
        rp = infographic_hint_v2_effective.get("rendering_policy")
        if isinstance(rp, dict):
            tb = rp.get("text_budget")
            if str(tb or "").strip() == "minimal_labels_only":
                hint_text_budget_original = "minimal_labels_only"
                # Remove the restriction entirely for table visuals; S4 will enforce its own policy.
                rp.pop("text_budget", None)
                hint_text_budget_overridden = True

    constraint_block, sufficiency_flags, requires_human_review = build_constraint_block(
        infographic_hint_v2_effective if isinstance(infographic_hint_v2_effective, dict) else None,
        purpose="table_visual",
        block_title="AUTHORITATIVE_CONSTRAINTS" if cluster_id else "CONSTRAINT_BLOCK",
        source_label="infographic_hint_v2" if cluster_id else "image_hint_v2",
    )
    # Prompt hygiene: the constraint block is part of the prompt text. Apply the same best-effort
    # sanitization we use for non-authoritative hints to prevent Korean/taxonomy/'>' leakage.
    if isinstance(constraint_block, str) and constraint_block.strip():
        cb = _sanitize_no_markdown_text(constraint_block)
        cb = _strip_korean_chars(cb)
        constraint_block = cb.strip()

    # -------------------------
    # Table input policy for S4_CONCEPT
    # -------------------------
    # Prefer a SINGLE, explicit env var:
    #   S4_TABLE_INPUT_MODE = compact | full_qc_equipment | full_all
    #
    # Backward-compatible aliases (legacy):
    #   S4_USE_FULL_TABLE=1      -> full_qc_equipment
    #   S4_USE_FULL_TABLE_ALL=1  -> full_all
    #
    # Default: full_all (use full master table for all table-visual types).
    visual_type_lc = (visual_type or "").strip().lower()
    mode_raw = os.getenv("S4_TABLE_INPUT_MODE", "").strip().lower()
    if not mode_raw:
        # Default to full table unless explicitly overridden.
        # Operators can force compact behavior via S4_TABLE_INPUT_MODE=compact.
        if _env_bool("S4_USE_FULL_TABLE_ALL", False):
            mode_raw = "full_all"
        elif _env_bool("S4_USE_FULL_TABLE", False):
            mode_raw = "full_qc_equipment"
        else:
            mode_raw = "full_all"

    if mode_raw not in ("compact", "full_qc_equipment", "full_all"):
        print(f"[S3] Warning: Unknown S4_TABLE_INPUT_MODE='{mode_raw}'. Falling back to 'full_all'.")
        mode_raw = "full_all"

    table_for_prompt_kind = "compact"
    if mode_raw == "full_all":
        table_for_prompt_kind = "full"
        table_for_prompt = master_table
        compact_table = build_concept_image_table(master_table)  # auditability
    elif mode_raw == "full_qc_equipment" and (visual_type_lc in ("qc", "equipment")):
        table_for_prompt_kind = "full"
        table_for_prompt = master_table
        compact_table = build_concept_image_table(master_table)  # auditability
    else:
        compact_table = build_concept_image_table(master_table)
        table_for_prompt = compact_table

    original_table = master_table  # Store original for auditability

    # -------------------------
    # Prompt construction (NO cluster bypass)
    # -------------------------
    # IMPORTANT:
    # - Always render system + user concept templates so global constraints (e.g., 16:9 / 4K)
    #   and safety rules remain active.
    # - If a cluster-specific prompt exists, it should be appended as AUTHORITATIVE content guidance
    #   (what to draw), but must NOT override SYSTEM-level safety/policy constraints or ALLOWED_TEXT.
    #
    # Format user template with placeholders (default behavior)
    # Use compact table instead of full master_table_markdown_kr unless table policy selects full.
    table_rows_plain = markdown_table_to_plain_rows(table_for_prompt, strip_korean=True)
    user_formatted = safe_prompt_format(
        user_template,
        group_id=group_id,
        visual_type_category=template_visual_type,
        table_rows_plain=table_rows_plain,
    )
    # Combine system + user prompts
    prompt_en = system_template.strip() + "\n\n" + user_formatted.strip()

    # Append constraint block if present (kept short; deterministic)
    if constraint_block:
        prompt_en = prompt_en.strip() + "\n\n" + constraint_block.strip()

    # Append cluster-specific prompt as AUTHORITATIVE content guidance.
    # Safety/system rules and ALLOWED_TEXT remain higher-priority constraints.
    infographic_prompt_original = None
    infographic_prompt_normalized = None
    infographic_prompt_normalization_notes: List[str] = []
    if isinstance(infographic_prompt, str) and infographic_prompt.strip():
        infographic_prompt_original = infographic_prompt.strip()
        # Normalize cluster prompts that contain scan/3D wording into a strict 2D schematic contract.
        if cluster_id:
            def _normalize_cluster_prompt_to_2d_schematic(p: str) -> Tuple[str, List[str]]:
                import re as _re

                notes: List[str] = []
                p0 = (p or "").strip()
                p1 = p0
                p0_lc = p0.lower()
                scan_like = bool(_re.search(r"\bct\b|\bmri\b|t2[- ]weighted", p0_lc))
                three_d_like = bool(_re.search(r"\b3d\b|\b3-d\b|three[- ]dimensional|volume render|reconstruction", p0_lc))

                # Remove explicit CT density / scan background phrases (common failure trigger).
                p2 = _re.sub(r"\boverlaid on\s+ct\s+density\s+background\b\.?", "", p1, flags=_re.IGNORECASE)
                p2 = _re.sub(r"\bct\s+density\s+background\b\.?", "", p2, flags=_re.IGNORECASE)
                if p2 != p1:
                    notes.append("removed_ct_density_background_phrase")

                # Replace CT-scan-as-output wording with 2D schematic language.
                p3 = _re.sub(
                    r"\b(axial|coronal|sagittal)\s+ct\s+scan\s+diagram\b",
                    r"\1 2D schematic diagram",
                    p2,
                    flags=_re.IGNORECASE,
                )
                p3 = _re.sub(r"\bct\s+scan\s+diagram\b", "2D schematic diagram", p3, flags=_re.IGNORECASE)
                p3 = _re.sub(r"\bct\s+scan\b", "2D schematic", p3, flags=_re.IGNORECASE)
                if p3 != p2:
                    notes.append("rewrote_ct_scan_wording_to_2d_schematic")

                # Soften "CT/MRI style" language into "CT-like/MRI-like schematic" (not a scan).
                p3b = p3
                p3b = _re.sub(
                    r"\bct\s+view\s+style\b",
                    "CT-like grayscale schematic style (not an actual scan)",
                    p3b,
                    flags=_re.IGNORECASE,
                )
                p3b = _re.sub(
                    r"\bt2[- ]weighted\s+mri\b",
                    "T2-weighted MRI-like schematic appearance (not an actual scan)",
                    p3b,
                    flags=_re.IGNORECASE,
                )
                if p3b != p3:
                    notes.append("rewrote_scan_style_wording_to_schematic_not_scan")
                p3 = p3b

                # Replace/strip 3D / reconstruction wording (common failure trigger).
                p4 = _re.sub(r"\btransparent\s+3d\s+view\b", "2D schematic view", p3, flags=_re.IGNORECASE)
                p4 = _re.sub(r"\b3d\s+bone\s+reconstruction\b", "2D schematic diagram", p4, flags=_re.IGNORECASE)
                p4 = _re.sub(r"\b3d\s+render(?:ing)?\b", "2D schematic", p4, flags=_re.IGNORECASE)
                p4 = _re.sub(r"\bvolume\s+render(?:ing)?\b", "2D schematic", p4, flags=_re.IGNORECASE)
                # If "reconstruction" remains, soften it (keep content but remove 3D implication).
                p4 = _re.sub(r"\breconstruction\b", "schematic illustration", p4, flags=_re.IGNORECASE)
                if p4 != p3:
                    notes.append("rewrote_3d_reconstruction_wording_to_2d_schematic")

                # If scan-like or 3D-like cues exist, enforce explicit negatives to avoid model drifting.
                if notes or scan_like or three_d_like:
                    suffix = (
                        " Render as a flat 2D schematic diagram (textbook-style)."
                        " Do NOT depict an actual CT/MRI scan background, CT density texture, photorealism,"
                        " 3D reconstruction, or volume rendering."
                    )
                    if suffix.strip() not in p4:
                        p4 = (p4.rstrip().rstrip(".") + "." + suffix).strip()
                    notes.append("appended_explicit_2d_no_scan_no_3d_constraints")

                # Cleanup whitespace/punctuation.
                # Remove accidental duplicated "schematic" from certain replacements.
                p4 = _re.sub(
                    r"\bschematic appearance \(not an actual scan\)\s+schematic\b",
                    "schematic appearance (not an actual scan)",
                    p4,
                    flags=_re.IGNORECASE,
                )
                p5 = " ".join((p4 or "").split())
                p5 = p5.replace("..", ".").strip()
                return p5, notes

            infographic_prompt_normalized, infographic_prompt_normalization_notes = _normalize_cluster_prompt_to_2d_schematic(
                infographic_prompt_original
            )
        else:
            infographic_prompt_normalized = infographic_prompt_original

        # Cluster prompts become part of the prompt text. Apply leak-prevention hygiene:
        # - remove markdown-ish triggers
        # - strip Korean/Hangul
        # - avoid breadcrumb separators '>' (replace with '/')
        infographic_prompt_sanitized = _sanitize_no_markdown_text(infographic_prompt_normalized or "")
        infographic_prompt_sanitized = _strip_korean_chars(infographic_prompt_sanitized)
        infographic_prompt_sanitized = infographic_prompt_sanitized.replace(">", "/")
        infographic_prompt_sanitized = " ".join(infographic_prompt_sanitized.split())
        if not infographic_prompt_sanitized.strip():
            infographic_prompt_sanitized = ""
        cluster_block = (
            "CLUSTER_SPEC (AUTHORITATIVE):\n"
            "This block defines WHAT the cluster infographic must depict.\n"
            "It overrides generic content guidance in the USER prompt above.\n"
            "It does NOT override SYSTEM safety/policy rules, ALLOWED_TEXT, or other constraints.\n\n"
            + infographic_prompt_sanitized
        )
        if infographic_prompt_sanitized:
            prompt_en = prompt_en.strip() + "\n\n" + cluster_block.strip()

    # -------------------------
    # Allowed-text metadata (no OCR; prompt-level contract)
    # -------------------------
    # - Default categories: allow up to 2 exam-point tokens per entity.
    # - QC/Equipment: still allow up to 2 exam-point tokens, but text budget profile differs.
    infographic_profile = "qc_equipment" if visual_type_lc in ("qc", "equipment") else "default"
    text_budget_profile = "qc_equipment_richer" if infographic_profile == "qc_equipment" else "default_exampoint2"

    exam_point_tokens_by_entity = extract_exam_point_tokens_by_entity(
        original_table, max_tokens_per_entity=2, max_words_per_token=3
    )
    # NOTE: Korean filtering disabled to preserve exam-point content for infographics.
    # Previously: exam_point_tokens_by_entity = _filter_exam_point_tokens_en_only(exam_point_tokens_by_entity)
    # Row-derived per-entity grounding snippets (EN/KR). Korean is ONLY allowed via these row snippets.
    try:
        max_en_items_per_entity = int(os.getenv("S3_ENTITY_ROW_TEXT_MAX_ITEMS_PER_ENTITY_EN", "18").strip())
    except Exception:
        max_en_items_per_entity = 18
    try:
        max_kr_items_per_entity = int(os.getenv("S3_ENTITY_ROW_TEXT_MAX_ITEMS_PER_ENTITY_KR", "18").strip())
    except Exception:
        max_kr_items_per_entity = 18
    try:
        max_kr_total = int(os.getenv("S3_ALLOWED_TEXT_KR_MAX_ITEMS", "600").strip())
    except Exception:
        max_kr_total = 600
    entity_row_text_by_entity = extract_entity_row_text_by_entity(
        original_table,
        max_en_items_per_entity=max(0, min(max_en_items_per_entity, 60)),
        max_kr_items_per_entity=max(0, min(max_kr_items_per_entity, 60)),
        max_en_words_per_item=8,
        max_kr_words_per_item=6,
    )
    allowed_text_kr: List[str] = _extract_allowed_text_kr_from_entity_row_text(
        entity_row_text_by_entity,
        max_items_total=max(0, min(max_kr_total, 2000)),
    )
    # Expand ALLOWED_TEXT by extracting short EN phrases from the ORIGINAL master table cells.
    # This enables richer per-panel explanations and slide-level takeaways while keeping strict allowlist safety.
    try:
        max_phrase_candidates = int(os.getenv("S3_ALLOWED_TEXT_PHRASE_MAX", "600").strip())
    except Exception:
        max_phrase_candidates = 600
    allowed_text_en = _extract_allowed_text_en(
        compact_table_md=compact_table,
        visual_type_category=visual_type,
        master_table_markdown_kr=original_table,
        max_phrase_candidates=max_phrase_candidates,
    )
    # Add EN-only exam-point tokens into the EN allowlist so they are permitted output tokens.
    if exam_point_tokens_by_entity:
        merged = list(allowed_text_en or [])
        for toks in (exam_point_tokens_by_entity or {}).values():
            for t in toks or []:
                tt = " ".join(str(t).strip().split())
                if not tt:
                    continue
                if tt not in merged:
                    merged.append(tt)
        allowed_text_en = sorted(merged)
    allowed_text_hash = _stable_hash_json({"en": allowed_text_en, "kr": allowed_text_kr, "exam": exam_point_tokens_by_entity})

    allowed_text_block = _format_allowed_text_block(
        allowed_text_en=allowed_text_en,
        allowed_text_kr=allowed_text_kr,
        exam_point_tokens_by_entity=exam_point_tokens_by_entity,
    )
    if allowed_text_block:
        prompt_en = prompt_en.strip() + "\n\n" + allowed_text_block.strip()

    # Per-entity row text block (authoritative; copy-only). This is how S4 can safely include richer,
    # row-grounded Korean phrases without translation or invention.
    try:
        max_entities_block = int(os.getenv("S3_ENTITY_ROW_TEXT_MAX_ENTITIES", "12").strip())
    except Exception:
        max_entities_block = 12
    try:
        max_items_block = int(os.getenv("S3_ENTITY_ROW_TEXT_MAX_ITEMS_PER_LANG", "14").strip())
    except Exception:
        max_items_block = 14
    entity_row_text_block = _format_entity_row_text_by_entity_block(
        entity_row_text_by_entity,
        max_entities=max(0, min(max_entities_block, 40)),
        max_items_per_lang=max(0, min(max_items_block, 30)),
    )
    if entity_row_text_block:
        prompt_en = prompt_en.strip() + "\n\n" + entity_row_text_block.strip()

    # NOTE: cluster prompt was already appended above as an AUTHORITATIVE content block.

    # Soft smoke-check: these should be present via templates (do not fail-hard; just warn).
    # This guards against accidental template regressions.
    if "16:9" not in prompt_en and "16×9" not in prompt_en and "16 x 9" not in prompt_en:
        print(f"[S3] Warning: TABLE_VISUAL prompt missing explicit 16:9 token (group={group_id}, cluster={cluster_id})")
    if "4K" not in prompt_en and "3840" not in prompt_en and "2160" not in prompt_en:
        print(f"[S3] Warning: TABLE_VISUAL prompt missing explicit 4K/3840x2160 token (group={group_id}, cluster={cluster_id})")

    # Hard-ish guard against markdown table leakage: we should never ship prompts that contain
    # markdown table separators/rows, because models may copy them into the rendered slide text.
    guard_mode = os.getenv("S3_PROMPT_MARKDOWN_GUARD", "warn").strip().lower()
    leak_findings = _detect_markdown_table_leak(prompt_en)
    if leak_findings:
        msg = (
            f"[S3] TABLE_VISUAL markdown-leak guard triggered (mode={guard_mode}) "
            f"(group={group_id}, cluster={cluster_id}): {leak_findings}"
        )
        if guard_mode in ("fail", "error", "raise", "1", "true", "yes"):
            raise ValueError(msg)
        if guard_mode not in ("off", "0", "false", "no", "disable", "disabled"):
            print(msg)

    # Additional hard-ish guard: for table visuals, prevent obvious Korean/taxonomy leakage in the *prompt*.
    # This is about prompt hygiene; output compliance is handled by templates + ALLOWED_TEXT.
    tv_guard_mode = os.getenv("S3_TABLE_VISUAL_PROMPT_GUARD", "warn").strip().lower()
    tv_findings: List[str] = []
    # Korean prompt hygiene:
    # - Previously: table-visual prompts were EN-only and we fail/warn on any Hangul in the prompt.
    # - Now: Korean is allowed ONLY via ENTITY_ROW_TEXT_BY_ENTITY (row-derived copy-only snippets).
    # Operators can re-disable Korean in prompts (hardening) via env:
    #   S3_TABLE_VISUAL_ALLOW_KOREAN_IN_PROMPT=0
    allow_korean_in_prompt = _env_bool("S3_TABLE_VISUAL_ALLOW_KOREAN_IN_PROMPT", True)
    if (not allow_korean_in_prompt) and _has_korean_chars(prompt_en):
        tv_findings.append("contains_korean_chars(disallowed_by_env)")
    # Hard regression check: the rendered prompt should never contain a raw '>' character after sanitization.
    # This catches taxonomy/breadcrumb leakage regardless of spacing and avoids prompt regressions.
    if ">" in prompt_en:
        tv_findings.append("contains_gt_char('>')")
    # Taxonomy paths typically include a breadcrumb separator (token > token), sometimes without spaces.
    if _detect_taxonomy_path_separator(prompt_en):
        tv_findings.append("contains_taxonomy_path_separator('>')")

    # Optional strict regression checks (OFF by default to avoid false positives).
    # Enable via env:
    #   S3_TABLE_VISUAL_PROMPT_GUARD_STRICT=warn|fail
    strict_mode = os.getenv("S3_TABLE_VISUAL_PROMPT_GUARD_STRICT", "off").strip().lower()
    if strict_mode not in ("off", "0", "false", "no", "disable", "disabled"):
        if re.search(r"\bgroup_path\b", prompt_en, flags=re.IGNORECASE):
            tv_findings.append("contains_group_path_token")
        snake_hits = _find_snake_case_tokens(prompt_en, max_hits=5)
        if snake_hits:
            tv_findings.append(f"contains_snake_case_token({','.join(snake_hits[:3])})")
    if tv_findings:
        mode_effective = strict_mode if strict_mode in ("warn", "fail", "error", "raise") else tv_guard_mode
        msg = (
            f"[S3] TABLE_VISUAL prompt-hygiene guard triggered (mode={mode_effective}) "
            f"(group={group_id}, cluster={cluster_id}): {sorted(set(tv_findings))}"
        )
        if mode_effective in ("fail", "error", "raise", "1", "true", "yes"):
            raise ValueError(msg)
        if mode_effective not in ("off", "0", "false", "no", "disable", "disabled"):
            print(msg)
    
    spec = {
        "schema_version": "S3_IMAGE_SPEC_v1.0",
        "run_tag": run_tag,
        "group_id": group_id,
        "entity_id": None,  # Group-level, no entity
        "entity_name": None,
        "card_role": None,  # Group-level, no card
        "spec_kind": "S1_TABLE_VISUAL",
        "image_placement_final": "TABLE",
        "image_asset_required": True,
        "visual_type_category": visual_type,
        "template_id": f"TABLE_VISUAL_v1__{template_visual_type}",
        "template_visual_type_category": template_visual_type,
        "prompt_en": prompt_en,
        "group_path": group_path,
        # Store original table for auditability (compact table used in prompt)
        "master_table_markdown_kr_original": original_table,
        "master_table_markdown_kr_compact": compact_table,
        "table_rows_plain": table_rows_plain,
        # Audit: whether prompt used full or compact table
        "master_table_input_kind": table_for_prompt_kind,
        # Text policy metadata (prompt-level; no OCR)
        "infographic_profile": infographic_profile,
        "text_budget_profile": text_budget_profile,
        "allowed_text_en": allowed_text_en,
        "allowed_text_kr": allowed_text_kr,
        "allowed_text_hash": allowed_text_hash,
        "exam_point_tokens_by_entity": exam_point_tokens_by_entity,
        # Row grounding (authoritative; enables copy-only bilingual explanations)
        "entity_row_text_by_entity": entity_row_text_by_entity,
        # Prompt hygiene audit (helps catch regressions without opening the prompt)
        "prompt_markdown_leak_findings": leak_findings,
        "prompt_text_leak_findings": sorted(set(tv_findings)),
    }

    # Preserve cluster prompt (original) for debug/audit (additionalProperties allowed)
    if infographic_prompt_original is not None:
        spec["infographic_prompt_en_original"] = infographic_prompt_original
    if infographic_prompt_normalized is not None and infographic_prompt_normalized != infographic_prompt_original:
        spec["infographic_prompt_en_normalized"] = infographic_prompt_normalized
        spec["infographic_prompt_normalization_notes"] = infographic_prompt_normalization_notes

    # Audit: hint-level text budget override
    if hint_text_budget_overridden:
        spec["infographic_hint_v2_text_budget_original"] = hint_text_budget_original
        spec["infographic_hint_v2_text_budget_overridden"] = True

    # Pass-through for auditability (optional)
    if isinstance(infographic_hint_v2, dict) and infographic_hint_v2:
        spec["infographic_hint_v2"] = infographic_hint_v2_effective if infographic_hint_v2_effective is not None else infographic_hint_v2
        spec["constraint_block"] = constraint_block
        spec["sufficiency_flags"] = sufficiency_flags
        spec["requires_human_review"] = bool(requires_human_review)

    # Preserve original category for audit/debug (additionalProperties allowed)
    if visual_type_original != visual_type:
        spec["visual_type_category_original"] = visual_type_original
    
    # Add cluster_id if present
    if cluster_id:
        spec["cluster_id"] = cluster_id
    
    return spec


def compile_table_visual_specs_for_group(
    *,
    run_tag: str,
    group_id: str,
    s1_struct: Dict[str, Any],
    prompt_bundle: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Compile S1 table visual specs for group-level image generation.
    Returns list of specs (1 if no clustering, 1-4 if clustering).
    
    Args:
        run_tag: Run identifier
        group_id: Group identifier
        s1_struct: S1 struct dict with visual_type_category, master_table_markdown_kr, and optional clustering fields
        prompt_bundle: Prompt bundle dict (if None, will load from base_dir)
    
    Returns:
        List of image spec dicts for S4 consumption (spec_kind="S1_TABLE_VISUAL")
    """
    entity_clusters = s1_struct.get("entity_clusters", [])
    infographic_clusters = s1_struct.get("infographic_clusters", [])
    
    if not entity_clusters or not infographic_clusters:
        # No clustering: return single spec (existing behavior)
        return [compile_table_visual_spec(
            run_tag=run_tag,
            group_id=group_id,
            s1_struct=s1_struct,
            prompt_bundle=prompt_bundle,
            cluster_id=None,
            infographic_prompt=None,
        )]
    
    # Clustering: return one spec per cluster
    specs = []
    master_table = s1_struct.get("master_table_markdown_kr", "")
    
    for cluster, infographic in zip(entity_clusters, infographic_clusters):
        cluster_id = cluster.get("cluster_id")
        cluster_entity_names = cluster.get("entity_names", [])
        
        # Ensure stable ordering: sort entity names alphabetically within cluster
        cluster_entity_names_sorted = sorted(cluster_entity_names)
        
        # Extract relevant rows from master table for this cluster (in sorted order)
        cluster_table = extract_cluster_table(
            master_table_markdown=master_table,
            entity_names=cluster_entity_names_sorted,
        )
        
        # Log cluster ordering for auditability
        print(f"[S3] Cluster {cluster_id}: {len(cluster_entity_names_sorted)} entities (sorted: {', '.join(cluster_entity_names_sorted[:3])}{'...' if len(cluster_entity_names_sorted) > 3 else ''})")
        
        # Create cluster-specific s1_struct
        cluster_s1_struct = {
            **s1_struct,
            "master_table_markdown_kr": cluster_table,
        }
        
        # Use cluster-specific infographic prompt
        infographic_prompt = infographic.get("infographic_prompt_en")
        infographic_style = infographic.get("infographic_style")
        infographic_hint_v2 = infographic.get("infographic_hint_v2")
        
        spec = compile_table_visual_spec(
            run_tag=run_tag,
            group_id=group_id,
            s1_struct=cluster_s1_struct,
            prompt_bundle=prompt_bundle,
            cluster_id=cluster_id,
            infographic_style=infographic_style,
            infographic_prompt=infographic_prompt,
            infographic_hint_v2=infographic_hint_v2 if isinstance(infographic_hint_v2, dict) else None,
        )
        specs.append(spec)
    
    return specs


# =========================
# Validation / Smoke Checks
# =========================

def validate_image_specs(specs: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """
    Validate image specs for common errors.
    
    Checks:
    - No leftover {placeholders} in prompt_en strings
    - EXAM images have 2K resolution hints in prompts
    - Concept table specs have compact 4-column table format
    
    Args:
        specs: List of image spec dicts
    
    Returns:
        (is_valid, error_messages): True if all checks pass, False otherwise, with list of error messages
    """
    errors = []
    warnings = []
    
    for i, spec in enumerate(specs):
        spec_kind = str(spec.get("spec_kind", "")).strip()
        prompt_en = str(spec.get("prompt_en", "")).strip()
        group_id = str(spec.get("group_id", "")).strip()
        entity_id = spec.get("entity_id")
        
        # Check 1: No leftover placeholders in prompt_en
        # Exclude LaTeX math notation patterns (e.g., $\sqrt{N}$, $\sqrt{mAs}$)
        import re
        placeholder_pattern = r'\{[a-zA-Z_][a-zA-Z0-9_]*\}'
        # Find all potential placeholders
        all_placeholders = re.findall(placeholder_pattern, prompt_en)
        # Filter out LaTeX math notation: patterns like $\sqrt{...}$ or $...{...}...$
        latex_math_pattern = r'\$[^$]*\{[a-zA-Z_][a-zA-Z0-9_]*\}[^$]*\$'
        latex_matches = re.findall(latex_math_pattern, prompt_en)
        # Extract identifiers from LaTeX matches to exclude them
        latex_identifiers = set()
        for latex_match in latex_matches:
            latex_placeholders = re.findall(placeholder_pattern, latex_match)
            latex_identifiers.update(latex_placeholders)
        # Only flag placeholders that are NOT part of LaTeX math notation
        placeholders = [p for p in all_placeholders if p not in latex_identifiers]
        if placeholders:
            errors.append(
                f"Spec {i} ({spec_kind}, group={group_id}, entity={entity_id}): "
                f"Found leftover placeholders in prompt_en: {', '.join(set(placeholders))}"
            )
        
        # Check 2: EXAM images should have 2K resolution hints
        if spec_kind == "S2_CARD_IMAGE":
            has_2k_hint = "2K" in prompt_en or "2048" in prompt_en or "2048×2560" in prompt_en
            if not has_2k_hint:
                warnings.append(
                    f"Spec {i} ({spec_kind}, group={group_id}, entity={entity_id}): "
                    f"EXAM image prompt missing 2K resolution hint (2048×2560)"
                )
        
        # Check 3: Concept table specs compact-table format (when used)
        if spec_kind == "S1_TABLE_VISUAL":
            table_input_kind = str(spec.get("master_table_input_kind", "compact")).strip().lower()
            compact_table = spec.get("master_table_markdown_kr_compact", "")
            allowed_en = spec.get("allowed_text_en")
            allowed_kr = spec.get("allowed_text_kr")
            exam_tok = spec.get("exam_point_tokens_by_entity")
            # Always validate the compact-table artifact (auditability), and additionally
            # enforce 4-column structure when the prompt uses compact input.
            if compact_table:
                # Check if it has exactly 4 columns
                lines = compact_table.strip().split("\n")
                if len(lines) >= 1:
                    header_line = lines[0]
                    columns = [c.strip() for c in header_line.split("|") if c.strip()]
                    if len(columns) != 4:
                        errors.append(
                            f"Spec {i} ({spec_kind}, group={group_id}): "
                            f"Compact table should have 4 columns, found {len(columns)}: {columns}"
                        )
                    # Check column names
                    expected_cols = ["Entity_EN", "ModalityTokens_EN", "CueToken_EN", "ExamPointToken_EN"]
                    if columns != expected_cols:
                        warnings.append(
                            f"Spec {i} ({spec_kind}, group={group_id}): "
                            f"Compact table columns don't match expected: got {columns}, expected {expected_cols}"
                        )
            # If prompt used compact input, ensure it's present (otherwise S4_CONCEPT gets no table)
            if table_input_kind == "compact" and not compact_table:
                errors.append(
                    f"Spec {i} ({spec_kind}, group={group_id}): "
                    f"Expected compact table input (master_table_input_kind=compact) but compact table is empty"
                )

            # Allowed-text contract (prompt-level, no OCR): required for new infographic stability
            if not isinstance(allowed_en, list) or not allowed_en:
                errors.append(
                    f"Spec {i} ({spec_kind}, group={group_id}): missing or empty allowed_text_en (required)"
                )
            if not isinstance(allowed_kr, list):
                errors.append(
                    f"Spec {i} ({spec_kind}, group={group_id}): allowed_text_kr must be a list (required)"
                )
            if not isinstance(exam_tok, dict):
                warnings.append(
                    f"Spec {i} ({spec_kind}, group={group_id}): exam_point_tokens_by_entity missing or not a dict"
                )
    
    is_valid = len(errors) == 0
    all_messages = errors + warnings
    return is_valid, all_messages


# =========================
# Main Processing
# =========================

def load_s2_results(s2_results_path: Path) -> Tuple[List[Dict[str, Any]], int]:
    """
    Load S2 results JSONL file.
    
    Returns:
        (records, skipped_count): List of valid records and count of skipped invalid lines
    """
    records = []
    skipped_count = 0
    
    if not s2_results_path.exists():
        raise FileNotFoundError(f"S2 results not found: {s2_results_path}")
    
    with open(s2_results_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                records.append(record)
            except json.JSONDecodeError as e:
                print(f"[S3] Warning: Skipping invalid JSON line {line_num}: {e}")
                skipped_count += 1
                continue
    
    if skipped_count > 0:
        print(f"[S3] Warning: Skipped {skipped_count} invalid JSON lines out of {line_num} total lines")
    
    return records, skipped_count


def load_s1_struct(s1_struct_path: Path) -> Tuple[Dict[str, Dict[str, Any]], int]:
    """
    Load S1 struct JSONL and index by group_id.
    
    Returns:
        (structs, skipped_count): Dict indexed by group_id and count of skipped invalid lines
    """
    structs = {}
    skipped_count = 0
    
    if not s1_struct_path.exists():
        raise FileNotFoundError(f"S1 struct not found: {s1_struct_path}")
    
    with open(s1_struct_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                struct = json.loads(line)
                group_id = struct.get("group_id")
                if group_id:
                    structs[group_id] = struct
            except json.JSONDecodeError as e:
                print(f"[S3] Warning: Skipping invalid JSON line {line_num}: {e}")
                skipped_count += 1
                continue
    
    if skipped_count > 0:
        print(f"[S3] Warning: Skipped {skipped_count} invalid JSON lines in S1 struct")
    
    return structs, skipped_count


def process_s3(
    *,
    base_dir: Path,
    run_tag: str,
    arm: str,
    s1_arm: Optional[str] = None,
    s1_path: Optional[Path] = None,  # Custom S1 struct path (e.g., for regen S1)
    progress_logger: Optional[Any] = None,
    image_style: Optional[str] = None,  # CLI override: "diagram" or "realistic"
    s2_path: Optional[Path] = None,  # Custom S2 results path (e.g., repaired)
    output_suffix: Optional[str] = None,  # Output file suffix (e.g., "repaired")
) -> None:
    """Main S3 processing function."""
    # Paths
    out_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    # Use path resolver for backward compatibility (supports both new and legacy formats)
    # S1 arm: use s1_arm parameter if specified, otherwise use S2 arm
    s1_arm_actual = (s1_arm or arm).strip().upper() if s1_arm else arm
    
    # S2 path: use custom path if provided, otherwise resolve automatically
    if s2_path is not None:
        s2_results_path = Path(s2_path).resolve()
    else:
        s2_results_path = resolve_s2_results_path(out_dir, arm, s1_arm=s1_arm_actual)
    
    # Use custom S1 path if provided, otherwise use default
    if s1_path is not None:
        s1_struct_path = s1_path
    else:
        s1_struct_path = out_dir / f"stage1_struct__arm{s1_arm_actual}.jsonl"
    
    # Output suffix for repaired variants (e.g., "__repaired")
    variant_suffix = f"__{output_suffix}" if output_suffix else ""
    
    policy_manifest_path = out_dir / f"image_policy_manifest__arm{arm}{variant_suffix}.jsonl"
    
    # image_style이 비-diagram일 때만 suffix 추가 (backward compatibility)
    if image_style and image_style.lower() not in ("diagram", ""):
        style_suffix = f"__{image_style.lower()}"
    else:
        style_suffix = ""
    image_spec_path = out_dir / f"s3_image_spec__arm{arm}{style_suffix}{variant_suffix}.jsonl"

    # Log resolved table input mode for operator clarity (single place to look)
    mode_raw = os.getenv("S4_TABLE_INPUT_MODE", "").strip().lower()
    if not mode_raw:
        # Legacy alias resolution (informational only; actual logic is in compile_table_visual_spec)
        if _env_bool("S4_USE_FULL_TABLE_ALL", False):
            mode_raw = "full_all (legacy:S4_USE_FULL_TABLE_ALL=1)"
        elif _env_bool("S4_USE_FULL_TABLE", False):
            mode_raw = "full_qc_equipment (legacy:S4_USE_FULL_TABLE=1)"
        else:
            mode_raw = "full_all (default)"
    if progress_logger:
        progress_logger.debug(f"[S3] Table input mode: {mode_raw}")
    else:
        print(f"[S3] Table input mode: {mode_raw}")
    
    # Load prompt bundle (for template-based prompt generation)
    try:
        prompt_bundle = load_prompt_bundle(str(base_dir))
    except Exception as e:
        raise RuntimeError(
            f"S3 FAIL: Cannot load prompt bundle from {base_dir}: {e}"
        ) from e
    
    # Load inputs
    # Optional: S1-only mode (table visuals only). Enable via env:
    #   S3_S1_ONLY=1
    # This allows infographic-only pipelines without running S2.
    s3_s1_only = _env_bool("S3_S1_ONLY", False)
    if s3_s1_only and not s2_results_path.exists():
        print(f"[S3] S1-only mode enabled (S3_S1_ONLY=1). Skipping missing S2 results: {s2_results_path}")
        s2_records, s2_skipped = [], 0
    else:
        s2_records, s2_skipped = load_s2_results(s2_results_path)
    s1_structs, s1_skipped = load_s1_struct(s1_struct_path)
    
    if s2_skipped > 0 or s1_skipped > 0:
        if progress_logger:
            progress_logger.debug(f"[S3] Summary: S2 skipped {s2_skipped} lines, S1 skipped {s1_skipped} lines")
        else:
            print(f"[S3] Summary: S2 skipped {s2_skipped} lines, S1 skipped {s1_skipped} lines")
    
    # Collect all specs first for validation, then write
    all_specs = []
    
    # Group S2 records by group_id and entity_id for progress tracking
    groups_dict = {}
    for s2_record in s2_records:
        group_id = str(s2_record.get("group_id") or "").strip()
        entity_id = str(s2_record.get("entity_id") or "").strip()
        if group_id and entity_id:
            if group_id not in groups_dict:
                groups_dict[group_id] = {}
            if entity_id not in groups_dict[group_id]:
                groups_dict[group_id][entity_id] = s2_record
    
    total_groups = len(groups_dict)
    total_entities = sum(len(entities) for entities in groups_dict.values())
    total_cards = sum(
        len(s2_record.get("anki_cards") or [])
        for entities in groups_dict.values()
        for s2_record in entities.values()
    )
    
    # Initialize progress bars
    if progress_logger:
        progress_logger.init_group(total_groups, desc="[S3] Processing groups")
        progress_logger.init_entity(total_entities, desc="  [S3] Processing entities")
        progress_logger.init_card(total_cards, desc="    [S3] Processing cards")
    
    # Open output files
    with open(policy_manifest_path, "w", encoding="utf-8") as f_policy, \
         open(image_spec_path, "w", encoding="utf-8") as f_spec:
        
        group_idx = 0
        entity_idx = 0
        card_idx = 0
        
        for group_id, entities_dict in groups_dict.items():
            group_idx += 1
            if progress_logger:
                progress_logger.update_group(group_idx, total_groups, group_id=group_id)
                progress_logger.reset_entity()
            
            for entity_id, s2_record in entities_dict.items():
                entity_idx += 1
                if progress_logger:
                    progress_logger.update_entity(entity_idx, total_entities, entity_id=entity_id)
                    progress_logger.reset_card()
                run_tag_rec = str(s2_record.get("run_tag") or run_tag).strip()
                entity_name = str(s2_record.get("entity_name") or "").strip()
                
                if not (group_id and entity_id and entity_name):
                    if progress_logger:
                        progress_logger.warning(f"Skipping record with missing keys: {s2_record}")
                    else:
                        print(f"Warning: Skipping record with missing keys: {s2_record}")
                    continue
                
                # Get S1 visual context
                s1_struct = s1_structs.get(group_id, {})
                visual_type = s1_struct.get("visual_type_category", "General")
                master_table = s1_struct.get("master_table_markdown_kr", "")
                
                s1_visual_context = {
                    "visual_type_category": visual_type,
                    "master_table_markdown_kr": master_table,
                }
                
                # Process each card
                cards = s2_record.get("anki_cards") or []
                for card in cards:
                    if not isinstance(card, dict):
                        continue
                    
                    card_role = str(card.get("card_role") or "").strip().upper()
                    if card_role not in ("Q1", "Q2"):
                        if progress_logger:
                            progress_logger.warning(f"Skipping card with invalid role: {card_role}")
                        else:
                            print(f"Warning: Skipping card with invalid role: {card_role}")
                        continue
                    
                    card_idx += 1
                    if progress_logger:
                        progress_logger.update_card(card_idx, total_cards, card_role=card_role)
                
                    # P0: Resolve policy (all cards)
                    # Pass visual_type_category for QC group special handling
                    policy = resolve_image_policy(card_role, visual_type_category=visual_type)
                    
                    # Write policy manifest (Q1/Q2)
                    policy_record = {
                        "schema_version": "S3_POLICY_MANIFEST_v1.0",
                        "run_tag": run_tag_rec,
                        "group_id": group_id,
                        "entity_id": entity_id,
                        "entity_name": entity_name,
                        "card_role": card_role,
                        "image_placement": policy["image_placement"],
                        "card_type": policy["card_type"],
                        "image_required": policy["image_required"],
                    }
                    f_policy.write(json.dumps(policy_record, ensure_ascii=False) + "\n")
                    
                    # P0: Compile image spec (Q1 and Q2 each get their own image spec)
                    image_hint = card.get("image_hint")
                    is_concept = is_concept_group(visual_type)
                    
                    # For CONCEPT groups (QC/Equipment), allow missing or minimal image_hint
                    # For EXAM groups, image_hint is required
                    if not image_hint:
                        if is_concept:
                            # CONCEPT: Create empty image_hint dict (will use card text only)
                            image_hint = {}
                            if progress_logger:
                                progress_logger.debug(
                                    f"[S3] Note: {card_role} missing image_hint for CONCEPT group (QC/Equipment). "
                                    f"Entity: {entity_name}, Group: {group_id}. Using card text only."
                                )
                            else:
                                print(
                                    f"[S3] Note: {card_role} missing image_hint for CONCEPT group (QC/Equipment). "
                                    f"Entity: {entity_name}, Group: {group_id}. Using card text only."
                                )
                        else:
                            # EXAM: image_hint is required
                            if progress_logger:
                                progress_logger.warning(
                                    f"[S3] {card_role} missing image_hint. "
                                    f"Entity: {entity_name}, Group: {group_id}. Skipping card image spec."
                                )
                            else:
                                print(
                                    f"[S3] Warning: {card_role} missing image_hint. "
                                    f"Entity: {entity_name}, Group: {group_id}. Skipping card image spec."
                                )
                            continue
                    
                    try:
                        spec = compile_image_spec(
                            run_tag=run_tag_rec,
                            group_id=group_id,
                            entity_id=entity_id,
                            entity_name=entity_name,
                            card_role=card_role,
                            card=card,  # Pass full card for answer extraction and prompt context
                            image_hint=image_hint,
                            s1_visual_context=s1_visual_context,
                            prompt_bundle=prompt_bundle,
                            image_style=image_style,  # Pass CLI override
                        )
                        all_specs.append(spec)
                        f_spec.write(json.dumps(spec, ensure_ascii=False) + "\n")
                    except ValueError as e:
                        # Log error but continue to allow table visual generation
                        # For CONCEPT groups, this should rarely fail (relaxed validation)
                        if progress_logger:
                            progress_logger.warning(f"[S3] ImageSpec FAIL for {card_role} (Entity: {entity_name}, Group: {group_id}): {e}")
                            progress_logger.debug("[S3] Continuing to process other cards and table visuals...")
                        else:
                            print(f"[S3] Warning: ImageSpec FAIL for {card_role} (Entity: {entity_name}, Group: {group_id}): {e}")
                            print(f"[S3] Continuing to process other cards and table visuals...")
                        # Don't raise - allow table visual generation to proceed
        
        # Process group-level table visual specs (once per unique group)
        # If S2 records exist, use them to determine which groups to process
        # Otherwise, process all groups from S1 structs (for S1-only mode)
        processed_groups = set()
        if s2_records:
            # Normal mode: process groups that have S2 records
            for s2_record in s2_records:
                group_id = str(s2_record.get("group_id") or "").strip()
                if not group_id or group_id in processed_groups:
                    continue
                processed_groups.add(group_id)
        else:
            # S1-only mode: process all groups from S1 structs
            print(f"[S3] No S2 records found. Processing all groups from S1 structs for table visuals.")
            processed_groups = set(s1_structs.keys())
        
        for group_id in processed_groups:
            s1_struct = s1_structs.get(group_id, {})
            
            if not s1_struct:
                print(f"[S3] Warning: No S1 struct found for group {group_id}, skipping table visual")
                continue
            
            try:
                # Generate table visual spec(s) (one per cluster if clustering, else one)
                table_specs = compile_table_visual_specs_for_group(
                    run_tag=run_tag,
                    group_id=group_id,
                    s1_struct=s1_struct,
                    prompt_bundle=prompt_bundle,
                )
                
                for spec in table_specs:
                    all_specs.append(spec)
                    f_spec.write(json.dumps(spec, ensure_ascii=False) + "\n")
            except ValueError as e:
                # Table visual is required, so fail-fast
                raise ValueError(
                    f"S3 Table Visual FAIL for group {group_id}: {e}"
                ) from e
    
    # Validate all specs (smoke checks)
    if all_specs:
        is_valid, validation_messages = validate_image_specs(all_specs)
        if validation_messages:
            for msg in validation_messages:
                if "Found leftover placeholders" in msg or "should have 4 columns" in msg:
                    # Critical errors: fail-fast
                    print(f"[S3] ERROR: {msg}", file=sys.stderr)
                else:
                    # Warnings: log but continue
                    print(f"[S3] WARNING: {msg}")
            if not is_valid:
                raise ValueError(
                    f"S3 Validation FAIL: Found {len([m for m in validation_messages if 'Found leftover' in m or 'should have 4 columns' in m])} critical error(s). "
                    f"See warnings above."
                )
        else:
            print(f"[S3] Validation: All {len(all_specs)} image spec(s) passed smoke checks")
    
    print(f"[S3] Policy manifest: {policy_manifest_path}")
    print(f"[S3] Image spec: {image_spec_path}")


# =========================
# CLI
# =========================

def main() -> None:
    parser = argparse.ArgumentParser(description="S3 Policy Resolver & ImageSpec Compiler")
    parser.add_argument("--base_dir", default=".", help="Base directory")
    parser.add_argument("--run_tag", required=True, help="Run tag")
    parser.add_argument("--arm", default="A", help="Arm identifier (S2 execution arm)")
    parser.add_argument("--s1_arm", default=None, help="S1 arm to use for reading S1 output (defaults to --arm if not specified)")
    parser.add_argument(
        "--image-style",
        choices=["diagram", "realistic"],
        default=None,
        help="Image style: 'diagram' (default, S5R3) or 'realistic' (S5R2). "
             "If not specified, auto-detects from run_tag (REALISTIC) or uses env var S4_EXAM_PROMPT_PROFILE."
    )
    parser.add_argument(
        "--s1_path",
        default=None,
        help="Custom S1 struct path (e.g., for regen S1). If not specified, uses default baseline path."
    )
    parser.add_argument(
        "--s2_path",
        default=None,
        help="Custom S2 results path (e.g., for repaired S2). If not specified, uses default baseline path."
    )
    parser.add_argument(
        "--output_suffix",
        default=None,
        help="Output file suffix (e.g., 'repaired'). Output will be s3_image_spec__armG__repaired.jsonl"
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    run_tag = str(args.run_tag).strip()
    arm = str(args.arm).strip().upper()
    s1_arm = str(args.s1_arm).strip().upper() if args.s1_arm else None
    s1_path = Path(args.s1_path).resolve() if args.s1_path else None
    s2_path = Path(args.s2_path).resolve() if args.s2_path else None
    output_suffix = str(args.output_suffix).strip() if args.output_suffix else None
    
    # Initialize progress logger
    progress_logger = None
    if ProgressLogger is not None:
        try:
            progress_logger = ProgressLogger(
                run_tag=run_tag,
                script_name="s3",
                arm=arm,
                base_dir=base_dir,
            )
        except Exception as e:
            print(f"[WARN] Failed to initialize ProgressLogger: {e}", file=sys.stderr)
            progress_logger = None
    
    if progress_logger:
        progress_logger.info(f"[S3] Processing: run_tag={run_tag}, arm={arm}")
        if s1_arm and s1_arm != arm:
            progress_logger.info(f"[S3] S1 arm={s1_arm} (reading S1 output from arm {s1_arm}, processing S2 results from arm {arm})")
        if s1_path:
            progress_logger.info(f"[S3] Using custom S1 path: {s1_path}")
        if s2_path:
            progress_logger.info(f"[S3] Using custom S2 path: {s2_path}")
        if output_suffix:
            progress_logger.info(f"[S3] Output suffix: __{output_suffix}")
    else:
        print(f"[S3] Processing: run_tag={run_tag}, arm={arm}")
        if s1_arm and s1_arm != arm:
            print(f"[S3] S1 arm={s1_arm} (reading S1 output from arm {s1_arm}, processing S2 results from arm {arm})")
        if s1_path:
            print(f"[S3] Using custom S1 path: {s1_path}")
        if s2_path:
            print(f"[S3] Using custom S2 path: {s2_path}")
        if output_suffix:
            print(f"[S3] Output suffix: __{output_suffix}")
    
    try:
        process_s3(
            base_dir=base_dir,
            run_tag=run_tag,
            arm=arm,
            s1_arm=s1_arm,
            s1_path=s1_path,
            progress_logger=progress_logger,
            image_style=args.image_style,  # Pass CLI argument
            s2_path=s2_path,
            output_suffix=output_suffix,
        )
        if progress_logger:
            progress_logger.info("[S3] Done")
            progress_logger.close()
        else:
            print("[S3] Done")
    except Exception as e:
        if progress_logger:
            progress_logger.error(f"[S3] FAIL: {e}")
            progress_logger.close()
        else:
            print(f"[S3] FAIL: {e}")
        raise


if __name__ == "__main__":
    main()


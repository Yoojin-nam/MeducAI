from __future__ import annotations

from typing import Any, Dict, Optional


def _as_bool(v: Any) -> Optional[bool]:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        # Treat 0/1 (or 0.0/1.0) as booleans when present.
        if v == 0:
            return False
        if v == 1:
            return True
        return None
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("1", "true", "yes", "y"):
            return True
        if s in ("0", "false", "no", "n"):
            return False
    return None


def _as_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def calculate_s5_regeneration_trigger_score(s5_card_record: Dict[str, Any]) -> float:
    """Safety-first trigger score (0-100, lower => more likely to regenerate).

    Hard triggers (returns 30.0):
    - s5_blocking_error
    - s5_technical_accuracy == 0.0
    - s5_card_image_blocking_error
    - s5_card_image_safety_flag

    Else weighted sum:
    - Technical accuracy: 50 points (0.0/0.5/1.0 scaled to 0-50)
    - Educational quality: 30 points (1-5 Likert scaled to 0-30)
    - Image quality: 20 points (1-5 Likert scaled to 0-20; if no image => 20)
    """

    # --- Hard triggers ---
    if _as_bool(s5_card_record.get("s5_blocking_error")) is True:
        return 30.0

    ta_raw = _as_float(s5_card_record.get("s5_technical_accuracy"))
    if ta_raw is not None and ta_raw == 0.0:
        return 30.0

    if _as_bool(s5_card_record.get("s5_card_image_blocking_error")) is True:
        return 30.0

    if _as_bool(s5_card_record.get("s5_card_image_safety_flag")) is True:
        return 30.0

    # --- Weighted score ---
    ta = ta_raw if ta_raw is not None else 1.0
    ta_score = _clamp(ta, 0.0, 1.0) * 50.0

    eq_raw = _as_float(s5_card_record.get("s5_educational_quality"))
    eq = eq_raw if eq_raw is not None else 5.0
    # Keep compatibility with historical "0 means missing" patterns.
    if eq <= 0:
        eq = 5.0
    eq_score = (_clamp(eq, 1.0, 5.0) / 5.0) * 30.0

    imgq_raw = _as_float(s5_card_record.get("s5_card_image_quality"))
    has_image = imgq_raw is not None and imgq_raw != 0
    if has_image and imgq_raw is not None:
        img_score = (_clamp(imgq_raw, 1.0, 5.0) / 5.0) * 20.0
    else:
        img_score = 20.0

    total = ta_score + eq_score + img_score
    return round(_clamp(total, 0.0, 100.0), 2)


def calculate_s5_card_regeneration_trigger_score(s5_card_record: Dict[str, Any]) -> float:
    """Card-only trigger score (0-100, lower => more likely to regenerate).
    
    This score considers ONLY card text quality, not image.
    Use for determining if the card content (question/answer) needs regeneration.

    Hard triggers (returns 30.0):
    - s5_blocking_error (card text has safety issues)
    - s5_technical_accuracy == 0.0

    Else weighted sum:
    - Technical accuracy: 50 points (0.0/0.5/1.0 scaled to 0-50)
    - Educational quality: 50 points (1-5 Likert scaled to 0-50)
    """
    # --- Hard triggers ---
    if _as_bool(s5_card_record.get("s5_blocking_error")) is True:
        return 30.0

    ta_raw = _as_float(s5_card_record.get("s5_technical_accuracy"))
    if ta_raw is not None and ta_raw == 0.0:
        return 30.0

    # --- Weighted score (card-only: TA 50%, EQ 50%) ---
    ta = ta_raw if ta_raw is not None else 1.0
    ta_score = _clamp(ta, 0.0, 1.0) * 50.0

    eq_raw = _as_float(s5_card_record.get("s5_educational_quality"))
    eq = eq_raw if eq_raw is not None else 5.0
    if eq <= 0:
        eq = 5.0
    eq_score = (_clamp(eq, 1.0, 5.0) / 5.0) * 50.0

    total = ta_score + eq_score
    return round(_clamp(total, 0.0, 100.0), 2)


def calculate_s5_image_regeneration_trigger_score(s5_card_record: Dict[str, Any]) -> Optional[float]:
    """Image-only trigger score (0-100, lower => more likely to regenerate image).
    
    This score considers ONLY image quality metrics.
    Use for determining if the image needs regeneration while keeping card content.
    
    Returns None if no image validation data exists.

    Hard triggers (returns 30.0):
    - s5_card_image_blocking_error
    - s5_card_image_safety_flag
    - s5_card_image_anatomical_accuracy == 0.0

    Else weighted sum:
    - Anatomical accuracy: 40 points (0.0/0.5/1.0 scaled to 0-40)
    - Prompt compliance: 30 points (0.0/0.5/1.0 scaled to 0-30)
    - Image quality: 30 points (1-5 Likert scaled to 0-30)
    """
    # Check if image validation data exists
    has_image_data = (
        s5_card_record.get("s5_card_image_blocking_error") is not None or
        s5_card_record.get("s5_card_image_anatomical_accuracy") is not None or
        s5_card_record.get("s5_card_image_quality") is not None
    )
    
    if not has_image_data:
        return None  # No image to evaluate
    
    # --- Hard triggers ---
    if _as_bool(s5_card_record.get("s5_card_image_blocking_error")) is True:
        return 30.0

    if _as_bool(s5_card_record.get("s5_card_image_safety_flag")) is True:
        return 30.0

    aa_raw = _as_float(s5_card_record.get("s5_card_image_anatomical_accuracy"))
    if aa_raw is not None and aa_raw == 0.0:
        return 30.0

    # --- Weighted score (image-only: AA 40%, PC 30%, IQ 30%) ---
    aa = aa_raw if aa_raw is not None else 1.0
    aa_score = _clamp(aa, 0.0, 1.0) * 40.0

    pc_raw = _as_float(s5_card_record.get("s5_card_image_prompt_compliance"))
    pc = pc_raw if pc_raw is not None else 1.0
    pc_score = _clamp(pc, 0.0, 1.0) * 30.0

    iq_raw = _as_float(s5_card_record.get("s5_card_image_quality"))
    iq = iq_raw if iq_raw is not None else 5.0
    if iq <= 0:
        iq = 5.0
    iq_score = (_clamp(iq, 1.0, 5.0) / 5.0) * 30.0

    total = aa_score + pc_score + iq_score
    return round(_clamp(total, 0.0, 100.0), 2)


def calculate_s1_table_regeneration_trigger_score(
    s1_table_validation: Dict[str, Any]
) -> float:
    """S1 Table trigger score (0-100, lower => more likely to regenerate).
    
    This score considers table text quality only (same formula as card_regeneration_trigger_score).
    Use for determining if the table needs regeneration based on validation feedback.
    
    Hard triggers (returns 30.0):
    - blocking_error == True
    - technical_accuracy == 0.0
    
    Else weighted sum:
    - Technical accuracy: 50 points (0.0/0.5/1.0 scaled to 0-50)
    - Educational quality: 50 points (1-5 Likert scaled to 0-50)
    
    This provides consistent evaluation criteria across S1 tables and S2 cards.
    """
    # --- Hard triggers ---
    if _as_bool(s1_table_validation.get("blocking_error")) is True:
        return 30.0
    
    ta_raw = _as_float(s1_table_validation.get("technical_accuracy"))
    if ta_raw is not None and ta_raw == 0.0:
        return 30.0
    
    # --- Weighted score (table-only: TA 50%, EQ 50%) ---
    ta = ta_raw if ta_raw is not None else 1.0
    ta_score = _clamp(ta, 0.0, 1.0) * 50.0
    
    eq_raw = _as_float(s1_table_validation.get("educational_quality"))
    eq = eq_raw if eq_raw is not None else 5.0
    if eq <= 0:
        eq = 5.0
    eq_score = (_clamp(eq, 1.0, 5.0) / 5.0) * 50.0
    
    total = ta_score + eq_score
    return round(_clamp(total, 0.0, 100.0), 2)


def calculate_regeneration_trigger_score(
    s5_result: Dict[str, Any],
    agent_scores: Optional[Dict[str, Any]] = None,
) -> float:
    """Back-compat alias for docs that reference this older function name."""

    _ = agent_scores  # reserved for future multi-agent scoring extensions
    return calculate_s5_regeneration_trigger_score(s5_result)


def should_trigger_regeneration(score: float, threshold: float = 70.0) -> bool:
    return float(score) < float(threshold)



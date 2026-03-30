"""
S5 Decision Determination Utility

This module implements the canonical S5 decision logic as defined in
`0_Protocol/05_Pipeline_and_Execution/S5_Decision_Definition_Canonical.md`.

Decision Types (v2.0):
- PASS: Both card and image pass quality thresholds
- CARD_REGEN: Card content needs regeneration (question + image)
- IMAGE_ONLY_REGEN: Only image needs regeneration (keep card content)

The decision criteria are binding and must be established before S5 execution
to ensure research design integrity.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def _as_bool(value: Any) -> bool:
    """
    Convert value to boolean, handling None and string representations.
    
    Args:
        value: Any value (bool, str, None, etc.)
    
    Returns:
        bool: True if value is truthy, False otherwise
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        # Treat 0/1 (or 0.0/1.0) as booleans
        if value == 0 or value == 0.0:
            return False
        if value == 1 or value == 1.0:
            return True
        return bool(value)
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "t")
    return bool(value)


def _get_score(record: Dict[str, Any], *keys: str) -> Optional[float]:
    """Get the first non-None score from multiple possible field names."""
    for key in keys:
        val = record.get(key)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                continue
    return None


def determine_s5_decision_v2(
    s5_record: Dict[str, Any],
    card_threshold: float = 70.0,
    image_threshold: float = 70.0,
) -> Tuple[str, Optional[float], Optional[float]]:
    """
    S5 판정 결정 로직 v2.0 (PASS / CARD_REGEN / IMAGE_ONLY_REGEN)
    
    This function implements the enhanced decision criteria that separates
    card content and image quality decisions.
    
    Decision Logic:
    - CARD_REGEN: card_regeneration_trigger_score < card_threshold
      → Regenerate entire card (question + image)
    - IMAGE_ONLY_REGEN: card passes but image_regeneration_trigger_score < image_threshold
      → Regenerate only image, keep card content
    - PASS: Both scores >= thresholds (or missing scores default to PASS)
    
    Args:
        s5_record: Dictionary containing S5 validation results with fields:
            - s5_card_regeneration_trigger_score: float | None (0-100 scale)
            - s5_image_regeneration_trigger_score: float | None (0-100 scale)
            - s5_regeneration_trigger_score: float | None (legacy combined score)
            - s5_was_regenerated: bool | None
            - s5_image_was_regenerated: bool | None
        card_threshold: Threshold for card regen decision (default: 70.0)
        image_threshold: Threshold for image-only regen decision (default: 70.0)
    
    Returns:
        Tuple of (decision, card_score, image_score) where:
        - decision: 'PASS' | 'CARD_REGEN' | 'IMAGE_ONLY_REGEN'
        - card_score: The card regeneration trigger score (or None if missing)
        - image_score: The image regeneration trigger score (or None if no image)
    """
    # Get card score (prefer new field name, fall back to legacy)
    card_score = _get_score(
        s5_record,
        "s5_card_regeneration_trigger_score",
        "s5_regeneration_trigger_score",
        "regeneration_trigger_score",
    )
    
    # Get image score (new field only)
    image_score = _get_score(
        s5_record,
        "s5_image_regeneration_trigger_score",
    )
    
    # Check for explicit regeneration flags
    card_was_regenerated = _as_bool(s5_record.get("s5_was_regenerated") or s5_record.get("was_regenerated"))
    image_was_regenerated = _as_bool(s5_record.get("s5_image_was_regenerated"))
    
    # Decision 1: CARD_REGEN (highest priority)
    # If card content is bad, regenerate everything
    if card_was_regenerated:
        return "CARD_REGEN", card_score, image_score
    
    if card_score is not None and card_score < card_threshold:
        return "CARD_REGEN", card_score, image_score
    
    # Decision 2: IMAGE_ONLY_REGEN
    # Card is OK, but image needs regeneration
    if image_was_regenerated:
        return "IMAGE_ONLY_REGEN", card_score, image_score
    
    if image_score is not None and image_score < image_threshold:
        return "IMAGE_ONLY_REGEN", card_score, image_score
    
    # Default: PASS
    # Missing fields default to PASS (conservative for research design)
    return "PASS", card_score, image_score


def determine_s5_decision(s5_record: Dict[str, Any]) -> str:
    """
    S5 판정 결정 로직 (PASS/REGEN 호환성 유지)
    
    This function maintains backward compatibility with the original
    binary decision logic while using the new v2 internally.
    
    Maps v2 decisions to legacy format:
    - PASS → "PASS"
    - CARD_REGEN → "REGEN"
    - IMAGE_ONLY_REGEN → "REGEN" (for legacy compatibility)
    
    Args:
        s5_record: Dictionary containing S5 validation results
    
    Returns:
        'PASS' | 'REGEN' (legacy format)
    """
    decision, _, _ = determine_s5_decision_v2(s5_record)
    
    if decision == "PASS":
        return "PASS"
    else:
        # Both CARD_REGEN and IMAGE_ONLY_REGEN map to legacy "REGEN"
        return "REGEN"


def determine_s5_decision_detailed(s5_record: Dict[str, Any]) -> str:
    """
    S5 판정 결정 로직 - 상세 버전 (v2.0)
    
    Returns the detailed decision type for downstream processing.
    
    Args:
        s5_record: Dictionary containing S5 validation results
    
    Returns:
        'PASS' | 'CARD_REGEN' | 'IMAGE_ONLY_REGEN'
    """
    decision, _, _ = determine_s5_decision_v2(s5_record)
    return decision


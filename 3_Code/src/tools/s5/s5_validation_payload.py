from __future__ import annotations

from typing import Any, Dict, Optional


def build_s2_card_validation_record(
    *,
    card_id: str,
    card: Dict[str, Any],
    entity_id: Optional[str],
    entity_name: Optional[str],
    entity_type: Optional[str],
    card_validation: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build the per-card record stored under:
      S5 JSONL -> s2_cards_validation.cards[]

    This record is treated as SSOT metadata for downstream repair planning (Option C),
    so entity identifiers should always be present (or None when unknown).
    """
    return {
        "card_id": card_id,
        # SSOT metadata for downstream repair planning (Option C)
        "entity_id": (str(entity_id).strip() or None) if entity_id is not None else None,
        "entity_name": (str(entity_name).strip() or None) if entity_name is not None else None,
        "entity_type": (str(entity_type).strip() or None) if entity_type is not None else None,
        "card_type": card.get("card_type"),
        "card_role": card.get("card_role"),
        **(card_validation or {}),
    }



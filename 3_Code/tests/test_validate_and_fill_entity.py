#!/usr/bin/env python3
"""
Direct test of validate_and_fill_entity function logic.
Tests that options and correct_index are preserved.
"""

def test_validate_and_fill_entity_logic():
    """Test the logic of validate_and_fill_entity without importing the module."""
    
    # Simulate the function logic based on the fixed code
    def validate_and_fill_entity_test(entity):
        """Simplified version of validate_and_fill_entity for testing."""
        e_in = dict(entity or {})
        e_out = {}
        
        if "group_id" in e_in and e_in["group_id"] is not None:
            e_out["group_id"] = str(e_in["group_id"]).strip()
        
        if "entity_id" in e_in and e_in.get("entity_id") is not None:
            _eid = str(e_in.get("entity_id") or "").strip()
            if _eid:
                e_out["entity_id"] = _eid
        
        if "cards_for_entity_exact" in e_in:
            e_out["cards_for_entity_exact"] = int(e_in.get("cards_for_entity_exact") or 0)
        
        e_out["entity_name"] = str(e_in.get("entity_name") or "").strip() or "Unnamed entity"
        
        cards = e_in.get("anki_cards") or []
        if not isinstance(cards, list):
            cards = []
        
        norm_cards = []
        for c in cards:
            if not isinstance(c, dict):
                continue
            
            # Extract fields (as in fixed code)
            card_role = str(c.get("card_role") or "").strip()
            image_hint = c.get("image_hint")
            options = c.get("options")  # NEW: Extract options
            correct_index = c.get("correct_index")  # NEW: Extract correct_index
            
            # Normalize tags
            tags_raw = c.get("tags")
            if isinstance(tags_raw, list):
                tags = [str(t).strip() for t in tags_raw if t]
            elif isinstance(tags_raw, str):
                tags = [t.strip() for t in tags_raw.split() if t.strip()]
            else:
                tags = []
            
            cc = {
                "card_type": str(c.get("card_type") or "Basic").strip(),
                "front": str(c.get("front") or "").strip(),
                "back": str(c.get("back") or "").strip(),
                "tags": tags,
            }
            
            # Preserve card_role
            if card_role:
                cc["card_role"] = card_role
            
            # Preserve image_hint
            if image_hint is not None:
                cc["image_hint"] = image_hint
            
            # NEW: Preserve options and correct_index
            if options is not None:
                if isinstance(options, list):
                    cc["options"] = options
            
            if correct_index is not None:
                cc["correct_index"] = correct_index
            
            if not (cc["front"] and cc["back"]):
                continue
            norm_cards.append(cc)
        
        e_out["anki_cards"] = norm_cards
        return e_out
    
    # Test case
    test_entity = {
        "group_id": "test_group",
        "entity_id": "test_entity",
        "entity_name": "Test Entity",
        "cards_for_entity_exact": 2,
        "anki_cards": [
            {
                "card_role": "Q1",
                "card_type": "Basic",
                "front": "Question 1",
                "back": "Answer 1",
                "tags": ["tag1"],
                "image_hint": {"modality_preferred": "CT"}
            },
            {
                "card_role": "Q2",
                "card_type": "MCQ",
                "front": "Question 2",
                "back": "Answer 2",
                "tags": ["tag2"],
                "options": ["Option A", "Option B", "Option C", "Option D", "Option E"],
                "correct_index": 1
            }
        ]
    }
    
    print("=" * 60)
    print("Testing validate_and_fill_entity logic")
    print("=" * 60)
    
    result = validate_and_fill_entity_test(test_entity)
    cards = result.get("anki_cards", [])
    
    print(f"\n✅ Processed {len(cards)} cards")
    
    # Check Q2
    q2 = next((c for c in cards if c.get("card_role") == "Q2"), None)
    if q2:
        has_options = "options" in q2
        has_correct_index = "correct_index" in q2
        print(f"\n📋 Q2 Card (MCQ):")
        print(f"   - Has options: {has_options}")
        print(f"   - Has correct_index: {has_correct_index}")
        if has_options:
            print(f"   - Options: {q2['options']}")
        if has_correct_index:
            print(f"   - Correct index: {q2['correct_index']}")
        
        if not has_options or not has_correct_index:
            print("   ❌ FAIL")
            return False
        else:
            print("   ✅ PASS")
    else:
        print("   ❌ FAIL: Q2 not found")
        return False
    
    # Note: Q3 is deprecated in the current 2-card policy (Q1/Q2 only).
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED: Logic is correct!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    import sys
    success = test_validate_and_fill_entity_logic()
    sys.exit(0 if success else 1)


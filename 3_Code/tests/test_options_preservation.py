#!/usr/bin/env python3
"""
Test script to verify that options and correct_index fields are preserved
after validate_and_fill_entity() function.
"""

import json
import sys
import importlib.util
from pathlib import Path

# Load module dynamically (file name starts with number)
src_path = Path(__file__).parent.parent / "src" / "01_generate_json.py"
spec = importlib.util.spec_from_file_location("generate_json", src_path)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Failed to load module spec for: {src_path}")
generate_json = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate_json)

validate_and_fill_entity = generate_json.validate_and_fill_entity


def test_options_preservation():
    """Test that options and correct_index are preserved."""
    
    # Test case 1: Entity with MCQ cards that have options
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
    print("Testing validate_and_fill_entity() options preservation")
    print("=" * 60)
    
    # Process entity
    result = validate_and_fill_entity(test_entity)
    
    # Check results
    cards = result.get("anki_cards", [])
    
    print(f"\n✅ Processed {len(cards)} cards")
    
    # Check Q2 (MCQ)
    q2 = next((c for c in cards if c.get("card_role") == "Q2"), None)
    if q2:
        has_options = "options" in q2
        has_correct_index = "correct_index" in q2
        print(f"\n📋 Q2 Card (MCQ):")
        print(f"   - Has options: {has_options}")
        print(f"   - Has correct_index: {has_correct_index}")
        if has_options:
            print(f"   - Options count: {len(q2['options'])}")
            print(f"   - Options: {q2['options']}")
        if has_correct_index:
            print(f"   - Correct index: {q2['correct_index']}")
        
        if not has_options or not has_correct_index:
            print("   ❌ FAIL: Q2 missing options or correct_index!")
            return False
        else:
            print("   ✅ PASS: Q2 has options and correct_index")
    else:
        print("   ❌ FAIL: Q2 card not found!")
        return False
    
    # Note: Q3 is deprecated in the current 2-card policy (Q1/Q2 only).
    
    # Check Q1 (should not have options)
    q1 = next((c for c in cards if c.get("card_role") == "Q1"), None)
    if q1:
        has_options = "options" in q1
        print(f"\n📋 Q1 Card (Basic):")
        print(f"   - Has options: {has_options}")
        if has_options:
            print("   ⚠️  WARNING: Q1 (Basic) has options (unexpected but not critical)")
        else:
            print("   ✅ PASS: Q1 correctly has no options")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED: options and correct_index are preserved!")
    print("=" * 60)
    return True


def test_with_real_data(jsonl_path: str):
    """Test with real S2 results data."""
    print("\n" + "=" * 60)
    print(f"Testing with real data: {jsonl_path}")
    print("=" * 60)
    
    path = Path(jsonl_path)
    if not path.exists():
        print(f"❌ File not found: {jsonl_path}")
        return False
    
    # Read first entity from JSONL
    with open(path, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
        if not first_line:
            print("❌ Empty file")
            return False
        
        record = json.loads(first_line)
        cards = record.get("anki_cards", [])
        
        # Find MCQ cards
        mcq_cards = [c for c in cards if c.get("card_type", "").upper() in ("MCQ", "MCQ_VIGNETTE")]
        
        print(f"\nFound {len(cards)} total cards, {len(mcq_cards)} MCQ cards")
        
        if not mcq_cards:
            print("⚠️  No MCQ cards found in this record")
            return True
        
        # Test with first MCQ card
        test_card = mcq_cards[0]
        print(f"\nTesting with card: {test_card.get('card_role')} ({test_card.get('card_type')})")
        
        # Create test entity
        test_entity = {
            "group_id": record.get("group_id", "test"),
            "entity_id": record.get("entity_id", "test"),
            "entity_name": record.get("entity_name", "Test"),
            "anki_cards": [test_card]
        }
        
        # Process
        result = validate_and_fill_entity(test_entity)
        result_cards = result.get("anki_cards", [])
        
        if not result_cards:
            print("❌ FAIL: No cards in result!")
            return False
        
        result_card = result_cards[0]
        has_options = "options" in result_card
        has_correct_index = "correct_index" in result_card
        
        print(f"   - Original has options: {'options' in test_card}")
        print(f"   - Result has options: {has_options}")
        print(f"   - Original has correct_index: {'correct_index' in test_card}")
        print(f"   - Result has correct_index: {has_correct_index}")
        
        if has_options:
            print(f"   - Options: {result_card['options']}")
        if has_correct_index:
            print(f"   - Correct index: {result_card['correct_index']}")
        
        if has_options and has_correct_index:
            print("\n✅ PASS: Real data test passed!")
            return True
        else:
            print("\n❌ FAIL: Options or correct_index not preserved!")
            return False


if __name__ == "__main__":
    # Run unit test
    success = test_options_preservation()
    
    # Test with real data if available
    if len(sys.argv) > 1:
        jsonl_path = sys.argv[1]
        real_success = test_with_real_data(jsonl_path)
        success = success and real_success
    
    sys.exit(0 if success else 1)


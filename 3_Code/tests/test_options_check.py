#!/usr/bin/env python3
"""
Simple test to check if options field exists in existing S2 results.
This helps verify if the fix is needed.
"""

import json
import sys
from pathlib import Path


def check_options_in_jsonl(jsonl_path: str):
    """Check if options field exists in MCQ cards."""
    path = Path(jsonl_path)
    if not path.exists():
        print(f"❌ File not found: {jsonl_path}")
        return False
    
    print("=" * 60)
    print(f"Checking options field in: {jsonl_path}")
    print("=" * 60)
    
    mcq_without_options = 0
    mcq_with_options = 0
    total_mcq = 0
    
    with open(path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            try:
                record = json.loads(line)
                cards = record.get("anki_cards", [])
                entity_name = record.get("entity_name", "Unknown")
                
                for card in cards:
                    card_type = card.get("card_type", "").upper()
                    card_role = card.get("card_role", "")
                    
                    if card_type in ("MCQ", "MCQ_VIGNETTE"):
                        total_mcq += 1
                        has_options = "options" in card
                        has_correct_index = "correct_index" in card
                        
                        if has_options and has_correct_index:
                            mcq_with_options += 1
                        else:
                            mcq_without_options += 1
                            print(f"\n❌ Line {line_num}, Entity: {entity_name}")
                            print(f"   Card: {card_role} ({card_type})")
                            print(f"   Has options: {has_options}")
                            print(f"   Has correct_index: {has_correct_index}")
                            if not has_options:
                                print(f"   ⚠️  Missing options field!")
                            if not has_correct_index:
                                print(f"   ⚠️  Missing correct_index field!")
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON decode error on line {line_num}: {e}")
                continue
    
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Total MCQ cards: {total_mcq}")
    print(f"  MCQ with options: {mcq_with_options}")
    print(f"  MCQ without options: {mcq_without_options}")
    print("=" * 60)
    
    if mcq_without_options > 0:
        print(f"\n❌ FAIL: Found {mcq_without_options} MCQ cards missing options/correct_index")
        print("   This confirms the bug exists in this run tag.")
        return False
    elif total_mcq == 0:
        print("\n⚠️  No MCQ cards found in this file")
        return True
    else:
        print(f"\n✅ PASS: All {total_mcq} MCQ cards have options and correct_index")
        return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default to checking the problematic run tag
        jsonl_path = "2_Data/metadata/generated/FULL_PIPELINE_V8_20251220_163147/s2_results__armA.jsonl"
        print("No file specified, using default:")
        print(f"  {jsonl_path}\n")
    else:
        jsonl_path = sys.argv[1]
    
    success = check_options_in_jsonl(jsonl_path)
    sys.exit(0 if success else 1)


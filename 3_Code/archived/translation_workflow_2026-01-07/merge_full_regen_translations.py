#!/usr/bin/env python3
"""
Merge full S2 Regen translations by combining:
- CARD_REGEN cards: Use regen translations
- IMAGE_REGEN/PASS cards: Use baseline translations

This creates a complete s2_regen__medterm_en.jsonl file with all 3,518 records.
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, Set


def load_card_decision_map(cards_csv: Path) -> Dict[str, str]:
    """
    Load card_uid -> s5_decision mapping.
    
    Returns:
        Dict: card_uid -> decision (CARD_REGEN, IMAGE_REGEN, PASS)
    """
    decision_map = {}
    
    with cards_csv.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            card_uid = row.get('card_uid', '')
            decision = row.get('s5_decision', 'PASS')
            if card_uid:
                decision_map[card_uid] = decision
    
    return decision_map


def build_card_uid(group_id: str, entity_id: str, card_role: str, card_idx: int) -> str:
    """Build card UID matching Cards.csv format."""
    return f"{group_id}::{entity_id}__{card_role}__{card_idx}"


def load_s2_index(s2_path: Path) -> Dict[str, Dict]:
    """
    Load S2 file and build card-level index.
    
    Returns:
        Dict: card_uid -> card_dict
    """
    card_index = {}
    
    with s2_path.open('r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            
            record = json.loads(line)
            group_id = record.get('group_id', '')
            entity_id = record.get('entity_id', '')
            
            for card_idx, card in enumerate(record.get('anki_cards', [])):
                card_role = card.get('card_role', '')
                
                card_uid = build_card_uid(group_id, entity_id, card_role, card_idx)
                card_index[card_uid] = card
    
    return card_index


def merge_regen_translations(
    baseline_translated: Path,
    regen_card_regen_translated: Path,
    original_regen_structure: Path,
    cards_csv: Path,
    output: Path,
    verbose: bool = True,
) -> int:
    """
    Merge translations to create complete regen__medterm_en.jsonl.
    
    Logic:
    - CARD_REGEN cards: Use regen translation
    - IMAGE_REGEN/PASS cards: Use baseline translation
    
    Returns:
        Number of records written
    """
    if verbose:
        print("Loading indexes...")
    
    # Load decision map
    decision_map = load_card_decision_map(cards_csv)
    if verbose:
        print(f"  Loaded {len(decision_map)} card decisions")
    
    # Load baseline translations
    baseline_index = load_s2_index(baseline_translated)
    if verbose:
        print(f"  Loaded {len(baseline_index)} baseline translated cards")
    
    # Load regen CARD_REGEN translations
    regen_index = load_s2_index(regen_card_regen_translated)
    if verbose:
        print(f"  Loaded {len(regen_index)} regen translated cards")
    
    # Process original regen structure
    if verbose:
        print(f"\nMerging translations...")
    
    written_count = 0
    card_regen_used = 0
    baseline_used = 0
    missing_count = 0
    
    with original_regen_structure.open('r', encoding='utf-8') as infile, \
         output.open('w', encoding='utf-8') as outfile:
        
        for line_num, line in enumerate(infile, 1):
            if not line.strip():
                continue
            
            record = json.loads(line)
            group_id = record.get('group_id', '')
            entity_id = record.get('entity_id', '')
            
            # Process each card
            for card_idx, card in enumerate(record.get('anki_cards', [])):
                card_role = card.get('card_role', '')
                card_uid = build_card_uid(group_id, entity_id, card_role, card_idx)
                
                # Get decision
                decision = decision_map.get(card_uid, 'PASS')
                
                # Choose source based on decision
                if decision == 'CARD_REGEN' and card_uid in regen_index:
                    # Use regen translation
                    translated_card = regen_index[card_uid]
                    card['front'] = translated_card.get('front', card.get('front', ''))
                    card['back'] = translated_card.get('back', card.get('back', ''))
                    if 'options' in translated_card:
                        card['options'] = translated_card['options']
                    card_regen_used += 1
                    
                elif card_uid in baseline_index:
                    # Use baseline translation (for IMAGE_REGEN and PASS)
                    translated_card = baseline_index[card_uid]
                    card['front'] = translated_card.get('front', card.get('front', ''))
                    card['back'] = translated_card.get('back', card.get('back', ''))
                    if 'options' in translated_card:
                        card['options'] = translated_card['options']
                    baseline_used += 1
                    
                else:
                    # Missing translation (keep original)
                    missing_count += 1
                    if verbose and missing_count <= 10:
                        print(f"  [WARN] Missing translation for {card_uid}")
            
            # Write merged record
            outfile.write(json.dumps(record, ensure_ascii=False) + '\n')
            written_count += 1
            
            if verbose and written_count % 100 == 0:
                print(f"  Progress: {written_count} records merged...", flush=True)
    
    if verbose:
        print(f"\n✅ Complete: {written_count} records written")
        print(f"   CARD_REGEN texts used: {card_regen_used}")
        print(f"   Baseline texts used: {baseline_used}")
        if missing_count > 0:
            print(f"   ⚠️  Missing translations: {missing_count} (kept original)")
    
    return written_count


def main():
    parser = argparse.ArgumentParser(
        description='Merge full S2 regen translations'
    )
    parser.add_argument(
        '--baseline_translated',
        type=Path,
        required=True,
        help='Translated baseline S2 file'
    )
    parser.add_argument(
        '--regen_card_regen_only',
        type=Path,
        required=True,
        help='Translated CARD_REGEN only S2 file'
    )
    parser.add_argument(
        '--original_regen',
        type=Path,
        required=True,
        help='Original S2 regen file (for structure)'
    )
    parser.add_argument(
        '--cards_csv',
        type=Path,
        required=True,
        help='Cards.csv with s5_decision column'
    )
    parser.add_argument(
        '--output',
        type=Path,
        required=True,
        help='Output complete regen__medterm_en.jsonl'
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    for path in [args.baseline_translated, args.regen_card_regen_only, 
                 args.original_regen, args.cards_csv]:
        if not path.exists():
            print(f"❌ Error: File not found: {path}", file=sys.stderr)
            return 1
    
    print("="*80)
    print("S2 Regen Full Translation Merger")
    print("="*80)
    print(f"\nInputs:")
    print(f"  Baseline translated: {args.baseline_translated}")
    print(f"  Regen CARD_REGEN:    {args.regen_card_regen_only}")
    print(f"  Original structure:  {args.original_regen}")
    print(f"  Decision info:       {args.cards_csv}")
    print(f"\nOutput:")
    print(f"  {args.output}")
    print()
    
    merge_regen_translations(
        baseline_translated=args.baseline_translated,
        regen_card_regen_translated=args.regen_card_regen_only,
        original_regen_structure=args.original_regen,
        cards_csv=args.cards_csv,
        output=args.output,
        verbose=True,
    )
    
    return 0


if __name__ == '__main__':
    sys.exit(main())


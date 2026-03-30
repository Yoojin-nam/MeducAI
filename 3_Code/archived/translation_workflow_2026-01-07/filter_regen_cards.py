#!/usr/bin/env python3
"""
Filter S2 regen file to only include CARD_REGEN cards.

This optimizes translation by only translating cards where text was regenerated.
IMAGE_REGEN and PASS cards use baseline text, so no translation needed.
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Set


def load_card_regen_set(cards_csv: Path) -> Set[str]:
    """
    Load set of card UIDs that have CARD_REGEN decision.
    
    Returns:
        Set of card_uid strings
    """
    card_regen_uids = set()
    
    with cards_csv.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            decision = row.get('s5_decision', '')
            if decision == 'CARD_REGEN':
                card_uid = row.get('card_uid', '')
                if card_uid:
                    card_regen_uids.add(card_uid)
    
    return card_regen_uids


def filter_s2_regen(
    input_s2: Path,
    output_s2: Path,
    card_regen_uids: Set[str],
    verbose: bool = True,
) -> int:
    """
    Filter S2 regen file to only include records with CARD_REGEN cards.
    
    Returns:
        Number of records written
    """
    written_count = 0
    
    with input_s2.open('r', encoding='utf-8') as infile, \
         output_s2.open('w', encoding='utf-8') as outfile:
        
        for line in infile:
            if not line.strip():
                continue
            
            record = json.loads(line)
            group_id = record.get('group_id', '')
            entity_id = record.get('entity_id', '')
            
            # Check if any card in this record has CARD_REGEN
            has_card_regen = False
            for card in record.get('anki_cards', []):
                card_role = card.get('card_role', '')
                card_idx = card.get('card_idx_in_entity', 0)
                
                # Build card_uid (same format as Cards.csv)
                card_uid = f"{group_id}::{entity_id}__{card_role}__{card_idx}"
                
                if card_uid in card_regen_uids:
                    has_card_regen = True
                    break
            
            # Only write if has CARD_REGEN
            if has_card_regen:
                outfile.write(line)
                written_count += 1
    
    return written_count


def main():
    parser = argparse.ArgumentParser(
        description='Filter S2 regen file to only CARD_REGEN cards'
    )
    parser.add_argument(
        '--cards_csv',
        type=Path,
        required=True,
        help='Cards.csv file with s5_decision column'
    )
    parser.add_argument(
        '--input_s2',
        type=Path,
        required=True,
        help='Input S2 regen JSONL file'
    )
    parser.add_argument(
        '--output_s2',
        type=Path,
        required=True,
        help='Output filtered S2 JSONL file'
    )
    
    args = parser.parse_args()
    
    print(f"Loading CARD_REGEN UIDs from: {args.cards_csv}")
    card_regen_uids = load_card_regen_set(args.cards_csv)
    print(f"  Found {len(card_regen_uids)} CARD_REGEN cards")
    
    print(f"\nFiltering: {args.input_s2}")
    print(f"Output: {args.output_s2}")
    
    written = filter_s2_regen(
        input_s2=args.input_s2,
        output_s2=args.output_s2,
        card_regen_uids=card_regen_uids,
        verbose=True,
    )
    
    print(f"\n✅ Complete: {written} records written")
    print(f"   (Only records with CARD_REGEN cards)")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())


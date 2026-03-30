#!/usr/bin/env python3
"""
Update Anki deck with REGEN content.

Reads baseline .apkg, replaces REGEN card content, adds REGEN images.
"""

import argparse
import json
import sqlite3
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Set, Tuple

def load_s5_decisions(s5_path: Path, threshold: float = 80.0) -> Dict[str, str]:
    """Load S5 decisions (CARD_REGEN / IMAGE_REGEN / PASS) by card_uid."""
    decisions = {}
    
    with s5_path.open('r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            group_id = record.get('group_id', '')
            s2 = record.get('s2_cards_validation', {})
            cards = s2.get('cards', [])
            
            for card in cards:
                card_id = card.get('card_id', '')
                card_regen_score = card.get('card_regeneration_trigger_score', 0) or 0
                image_regen_score = card.get('image_regeneration_trigger_score', 0) or 0
                
                if card_regen_score >= threshold:
                    decision = 'CARD_REGEN'
                elif image_regen_score >= threshold:
                    decision = 'IMAGE_REGEN'
                else:
                    decision = 'PASS'
                
                card_uid = f"{group_id}::{card_id}"
                decisions[card_uid] = decision
    
    return decisions


def load_s2_content(s2_path: Path) -> Dict[str, Tuple[str, str, str]]:
    """Load card content. Returns {card_uid: (front, back, card_type)}."""
    content = {}
    
    with s2_path.open('r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            group_id = record.get('group_id', '')
            entity_id = record.get('entity_id', '')
            anki_cards = record.get('anki_cards', [])
            
            for idx, card in enumerate(anki_cards):
                card_role = card.get('card_role', '')
                card_uid = f'{group_id}::{entity_id}__{card_role}__{idx}'
                
                # Format content
                front = (card.get('front', '') or '').replace('**', '').strip()
                back = (card.get('back', '') or '').replace('**', '').strip()
                card_type = (card.get('card_type', '') or 'BASIC').upper()
                
                # For MCQ, format options
                if card_type in ('MCQ', 'MCQ_VIGNETTE'):
                    options = card.get('options', [])
                    if options:
                        options_text = '\n\n[선택지]\n'
                        for i, opt in enumerate(options[:5]):
                            label = ['A', 'B', 'C', 'D', 'E'][i]
                            options_text += f'{label}. {opt}\n'
                        front += options_text.rstrip()
                
                content[card_uid] = (front, back, card_type)
    
    return content


def find_card_uid_in_content(front: str, back: str, all_content: Dict[str, Tuple[str, str, str]]) -> str:
    """Try to match Anki note to card_uid by content similarity."""
    # Simple exact match on first 100 chars
    front_prefix = front[:100].strip()
    back_prefix = back[:100].strip()
    
    for uid, (content_front, content_back, _) in all_content.items():
        if content_front[:100].strip() == front_prefix:
            return uid
    
    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline_apkg', type=Path, required=True)
    parser.add_argument('--s5_validation', type=Path, required=True)
    parser.add_argument('--s2_baseline', type=Path, required=True)
    parser.add_argument('--s2_regen', type=Path, required=True)
    parser.add_argument('--regen_images_dir', type=Path, required=True)
    parser.add_argument('--output_apkg', type=Path, required=True)
    parser.add_argument('--threshold', type=float, default=80.0)
    args = parser.parse_args()
    
    print("Anki deck update with REGEN content")
    print(f"Baseline: {args.baseline_apkg}")
    print(f"Output: {args.output_apkg}")
    
    # Load data
    print("\nLoading S5 decisions...")
    decisions = load_s5_decisions(args.s5_validation, args.threshold)
    regen_count = sum(1 for d in decisions.values() if d != 'PASS')
    print(f"  Total cards: {len(decisions)}")
    print(f"  REGEN cards: {regen_count}")
    
    print("\nLoading baseline content...")
    baseline_content = load_s2_content(args.s2_baseline)
    print(f"  Loaded {len(baseline_content)} baseline cards")
    
    print("\nLoading REGEN content...")
    regen_content = load_s2_content(args.s2_regen)
    print(f"  Loaded {len(regen_content)} REGEN cards")
    
    # For now, just copy baseline
    print("\n⚠️  Complex merge logic required")
    print("    Copying baseline for now...")
    
    shutil.copy(args.baseline_apkg, args.output_apkg)
    print(f"✅ Created: {args.output_apkg}")
    print("\n⚠️  Manual REGEN integration needed")


if __name__ == '__main__':
    main()


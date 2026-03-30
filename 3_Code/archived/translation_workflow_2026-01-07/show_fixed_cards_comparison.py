#!/usr/bin/env python3
"""
Show before/after comparison of fixed cards.
Compare backup file with current file to see what was fixed.
"""

import json
import csv
import re
from pathlib import Path
from typing import Dict, Set

BASE_DIR = Path(__file__).parent.parent.parent.parent.parent

# Thinking patterns
THINKING_PATTERNS = [
    r"Let's re-evaluate",
    r"Rule \d+:",
    r'So "',
    r"Wait,",
    r"One detail:",
    r"Final check on",
    r'is just the plain',
    r'If I follow',
    r'I\'ll just use',
]

def has_thinking_text(text: str) -> bool:
    """Check if text contains thinking patterns."""
    if not text:
        return False
    for pattern in THINKING_PATTERNS:
        if re.search(pattern, str(text), re.IGNORECASE | re.MULTILINE):
            return True
    return False

def load_s5_decisions(s5_csv_path: Path) -> Dict[str, str]:
    """Load S5 decisions."""
    decisions = {}
    with open(s5_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            card_uid = row.get('card_uid', '')
            decision = row.get('s5_decision', '')
            if card_uid and decision:
                decisions[card_uid] = decision
    return decisions

def build_card_uid(record, card_idx, card):
    """Build card UID."""
    group_id = record.get('group_id', '')
    entity_id = record.get('entity_id', '')
    card_role = card.get('card_role', '')
    return f"{group_id}::{entity_id}__{card_role}__{card_idx}"

def main():
    # Find most recent backup
    baseline_dir = BASE_DIR / '2_Data/metadata/generated/FINAL_DISTRIBUTION'
    backups = sorted(baseline_dir.glob('s2_results__s1armG__s2armG__medterm_en.jsonl.backup_retrans_*'))
    
    if not backups:
        print("Error: No backup file found. Looking for backup_retrans_* files.")
        return
    
    backup_path = backups[-1]  # Most recent
    current_path = baseline_dir / 's2_results__s1armG__s2armG__medterm_en.jsonl'
    s5_csv_path = BASE_DIR / '6_Distributions/Final_QA/AppSheet_Export_TRANSLATED_VERIFY/S5.csv'
    
    print(f"Comparing:")
    print(f"  Before: {backup_path.name}")
    print(f"  After:  {current_path.name}")
    print()
    
    # Load S5 decisions
    s5_decisions = load_s5_decisions(s5_csv_path)
    
    # Load before (backup)
    before_records = {}
    with open(backup_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                before_records[line_num] = json.loads(line)
    
    # Compare with after (current)
    fixed_samples = []
    
    with open(current_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            try:
                after_record = json.loads(line)
                before_record = before_records.get(line_num)
                
                if not before_record or 'anki_cards' not in after_record:
                    continue
                
                for card_idx, after_card in enumerate(after_record['anki_cards']):
                    if card_idx >= len(before_record.get('anki_cards', [])):
                        continue
                    
                    before_card = before_record['anki_cards'][card_idx]
                    
                    # Build card UID
                    card_uid = build_card_uid(after_record, card_idx, after_card)
                    decision = s5_decisions.get(card_uid, '')
                    
                    # Only PASS/IMAGE_REGEN
                    if decision not in ['PASS', 'IMAGE_REGEN']:
                        continue
                    
                    # Check if this was fixed (had thinking in before, not in after)
                    before_has_thinking = (
                        has_thinking_text(before_card.get('front', '')) or
                        has_thinking_text(before_card.get('back', ''))
                    )
                    after_has_thinking = (
                        has_thinking_text(after_card.get('front', '')) or
                        has_thinking_text(after_card.get('back', ''))
                    )
                    
                    if before_has_thinking and not after_has_thinking:
                        fixed_samples.append({
                            'card_uid': card_uid,
                            'entity': after_record.get('entity_name', ''),
                            'decision': decision,
                            'before': before_card,
                            'after': after_card,
                        })
                        
                        if len(fixed_samples) >= 10:
                            break
            except:
                pass
            
            if len(fixed_samples) >= 10:
                break
    
    # Generate output
    output_file = BASE_DIR / '6_Distributions/Final_QA/FIXED_CARDS_BEFORE_AFTER.txt'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 수정된 카드 Before/After 비교\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"총 {len(fixed_samples)}개 샘플 (thinking 패턴 제거 성공)\n\n")
        
        for i, sample in enumerate(fixed_samples, 1):
            f.write(f"\n## 샘플 {i}: {sample['entity']}\n")
            f.write(f"Card UID: {sample['card_uid']}\n")
            f.write(f"Decision: {sample['decision']}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("### BEFORE (with thinking text)\n")
            f.write("-" * 80 + "\n")
            f.write("[FRONT]\n")
            f.write(sample['before'].get('front', '')[:300] + "...\n\n")
            f.write("[BACK]\n")
            f.write(sample['before'].get('back', '')[:500] + "...\n\n")
            
            f.write("### AFTER (cleaned)\n")
            f.write("-" * 80 + "\n")
            f.write("[FRONT]\n")
            f.write(sample['after'].get('front', '')[:300] + "...\n\n")
            f.write("[BACK]\n")
            f.write(sample['after'].get('back', '')[:500] + "...\n\n")
            
            f.write("=" * 80 + "\n")
    
    print(f"✅ Generated: {output_file}")
    print(f"   {len(fixed_samples)} before/after comparisons")

if __name__ == '__main__':
    main()


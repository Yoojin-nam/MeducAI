#!/usr/bin/env python3
"""
Show successful translation samples (no thinking patterns).
Display cards with good English(Korean) format.
"""

import json
import csv
import random
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent.parent  # Up to workspace root

def format_card_display(record, card, card_idx):
    """Format card for display."""
    lines = []
    lines.append("=" * 80)
    
    entity_name = record.get('entity_name', '')
    group_path = record.get('group_path', '').replace(' > ', ' › ')
    
    lines.append(f"Entity: {entity_name}")
    lines.append(f"Path: {group_path}")
    lines.append(f"Card: {card.get('card_role', 'Q?')} ({card.get('card_type', 'BASIC')})")
    lines.append("-" * 80)
    lines.append("\n[FRONT]")
    lines.append(card.get('front', ''))
    lines.append("\n[BACK]")
    lines.append(card.get('back', ''))
    
    if 'options' in card and card['options']:
        lines.append("\n[OPTIONS]")
        for i, opt in enumerate(card['options'], 1):
            lines.append(f"{chr(64+i)}. {opt}")
    
    lines.append("=" * 80)
    lines.append("")
    
    return '\n'.join(lines)

# Load S5 decisions
s5_csv = BASE_DIR / '6_Distributions/Final_QA/AppSheet_Export_TRANSLATED_VERIFY/S5.csv'
card_decisions = {}

with open(s5_csv, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        card_uid = row.get('card_uid', '')
        decision = row.get('s5_decision', '')
        if card_uid and decision:
            card_decisions[card_uid] = decision

# Sample successful cards
baseline_path = BASE_DIR / '2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__medterm_en.jsonl'
output_file = BASE_DIR / '6_Distributions/Final_QA/SUCCESSFUL_TRANSLATION_SAMPLES.txt'

print("Sampling successful translations...")

# Collect all clean cards
clean_cards = []

with open(baseline_path, 'r', encoding='utf-8') as f:
    for line_num, line in enumerate(f, 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            if 'anki_cards' in record:
                for card_idx, card in enumerate(record['anki_cards']):
                    # Build card UID
                    group_id = record.get('group_id', '')
                    entity_id = record.get('entity_id', '')
                    card_role = card.get('card_role', '')
                    card_uid = f"{group_id}::{entity_id}__{card_role}__{card_idx}"
                    
                    decision = card_decisions.get(card_uid, '')
                    
                    # Only PASS/IMAGE_REGEN (baseline text used)
                    if decision in ['PASS', 'IMAGE_REGEN']:
                        # Check for thinking patterns
                        text = card.get('front', '') + card.get('back', '')
                        if all(p not in text for p in ['Let\'s', 'Rule ', 'Wait,', 'One detail', 'Final check', 'is just the plain']):
                            clean_cards.append((record, card, card_idx, decision))
        except:
            pass
        
        if len(clean_cards) >= 1000:  # Enough for sampling
            break

print(f"Found {len(clean_cards)} clean cards")

# Sample cards stratified by decision and specialty
random.seed(42)
pass_cards = [c for c in clean_cards if c[3] == 'PASS']
image_regen_cards = [c for c in clean_cards if c[3] == 'IMAGE_REGEN']

sampled_pass = random.sample(pass_cards, min(15, len(pass_cards)))
sampled_image_regen = random.sample(image_regen_cards, min(5, len(image_regen_cards)))

sampled = sampled_pass + sampled_image_regen

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("# 성공적으로 번역된 카드 샘플\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"총 {len(clean_cards)}개의 clean 카드 중 {len(sampled)}개 샘플\n")
    f.write("(thinking 패턴 없이 정상적으로 번역된 카드들)\n\n")
    f.write("## 확인 포인트:\n")
    f.write("1. ✅ 의학 용어가 영어로 번역되었는가?\n")
    f.write("2. ✅ 일반 단어(환자, 검사, 소견)는 한글인가?\n")
    f.write("3. ✅ 한국어 문장 구조가 자연스러운가?\n")
    f.write("4. ✅ 형식(Answer:, 근거:, 불릿)이 유지되었는가?\n\n")
    f.write("=" * 80 + "\n\n")
    
    for i, (record, card, card_idx, decision) in enumerate(sampled, 1):
        f.write(f"\n## 샘플 {i} (Decision: {decision})\n\n")
        f.write(format_card_display(record, card, card_idx))

print(f"✅ Generated: {output_file}")
print(f"   {len(sampled)} successful translation samples")


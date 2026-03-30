#!/usr/bin/env python3
"""
Debug a single translation to see what's happening.
"""

import json
import sys
from pathlib import Path

_parent = Path('/path/to/workspace/workspace/MeducAI/3_Code/src').resolve()
sys.path.insert(0, str(_parent))

from tools.anki.translate_medical_terms_module import MedicalTermTranslator

# Load first record from original
original_file = Path('/path/to/workspace/workspace/MeducAI/2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG.jsonl')

with original_file.open('r', encoding='utf-8') as f:
    first_rec = json.loads(f.readline())

print("=" * 80)
print("단일 레코드 번역 디버깅")
print("=" * 80)
print(f"\nEntity: {first_rec.get('entity_name', '')}")
print(f"Record ID: {first_rec.get('group_id')}::{first_rec.get('entity_id')}")
print()

# Get first card
card = first_rec['anki_cards'][0]
front_orig = card['front']
back_orig = card['back']

print("원본 Front:")
print("-" * 80)
print(front_orig[:300])
print()

# Initialize translator
print("Translator 초기화...")
translator = MedicalTermTranslator(
    model="gemini-2.0-flash-exp",
    temperature=0.0,
    use_rotator=False,
)

print("✅ 준비 완료")
print()

# Translate with verbose
print("번역 중 (verbose mode)...")
print("=" * 80)

translated_front = translator.translate_text(front_orig, use_cache=False, verbose=True)

print("\n\n번역 결과:")
print("=" * 80)
print(translated_front[:300])
print()

# Compare
if translated_front == front_orig:
    print("⚠️  원본과 동일 - 번역이 안 되었습니다!")
    
    # Check why
    import re
    has_korean = any('\uAC00' <= c <= '\uD7A3' for c in front_orig)
    korean_chars = len(re.findall(r'[가-힣]', front_orig))
    
    print(f"\n한글 체크:")
    print(f"  한글 있음: {has_korean}")
    print(f"  한글 문자 수: {korean_chars}")
    
    if not has_korean:
        print("  → 한글이 없어서 번역 skip됨!")
else:
    print("✅ 번역되었습니다!")
    
    # Show difference
    import re
    orig_korean = len(re.findall(r'[가-힣]+', front_orig))
    trans_korean = len(re.findall(r'[가-힣]+', translated_front))
    
    print(f"\n한글 단어: {orig_korean}개 → {trans_korean}개 (감소: {orig_korean - trans_korean})")

print("\n" + "=" * 80)



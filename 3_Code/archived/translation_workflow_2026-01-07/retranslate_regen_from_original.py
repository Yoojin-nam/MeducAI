#!/usr/bin/env python3
"""
Re-translate REGEN file from original.
Same process as regular file but for regen version.
"""

import json
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import re

_THIS_DIR = Path(__file__).resolve().parent
_parent = _THIS_DIR.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from tools.anki.translate_medical_terms_module import MedicalTermTranslator


def find_regen_thinking_records(translated_file: Path, original_file: Path) -> list:
    """Find records in REGEN that were changed from original and have thinking patterns."""
    
    print("Finding REGEN records with thinking patterns...")
    
    # Load both files
    original_recs = {}
    with original_file.open('r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                rid = f"{rec.get('group_id')}::{rec.get('entity_id')}"
                original_recs[rid] = rec
    
    translated_recs = {}
    with translated_file.open('r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                rid = f"{rec.get('group_id')}::{rec.get('entity_id')}"
                translated_recs[rid] = rec
    
    print(f"  Original: {len(original_recs)} records")
    print(f"  Translated: {len(translated_recs)} records")
    
    # Find changed records (regenerated ones)
    changed_rids = []
    for rid in translated_recs:
        if rid not in original_recs:
            continue
        
        orig_cards = original_recs[rid].get('anki_cards', [])
        trans_cards = translated_recs[rid].get('anki_cards', [])
        
        for oc, tc in zip(orig_cards, trans_cards):
            if oc.get('front') != tc.get('front') or oc.get('back') != tc.get('back'):
                changed_rids.append(rid)
                break
    
    print(f"  Changed (regenerated): {len(changed_rids)} records")
    
    # Check for thinking patterns
    thinking_patterns = [
        r'Wait,', r'\*Wait', r'Rule\s+\d+\s+says', r'Then Rule',
        r'Final check on', r'One last', r'is capitalized',
        r'is Korean', r'is English', r'\(No explanations\)',
    ]
    
    thinking_rids = []
    for rid in changed_rids:
        rec = translated_recs[rid]
        has_thinking = False
        
        for card in rec.get('anki_cards', []):
            text = card.get('front', '') + '\n' + card.get('back', '')
            
            for pattern in thinking_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    has_thinking = True
                    break
            
            if has_thinking:
                break
        
        if has_thinking:
            thinking_rids.append(rid)
    
    print(f"  With thinking patterns: {len(thinking_rids)} records")
    
    return thinking_rids


def main():
    base_dir = Path('/path/to/workspace/workspace/MeducAI/2_Data/metadata/generated/FINAL_DISTRIBUTION')
    
    original_file = base_dir / 's2_results__s1armG__s2armG__regen.jsonl'
    translated_file = base_dir / 's2_results__s1armG__s2armG__regen__medterm_en.jsonl'
    
    print("=" * 80)
    print("REGEN 파일 재번역")
    print("=" * 80)
    print(f"원본: {original_file.name}")
    print(f"번역: {translated_file.name}")
    print()
    
    # Find records to retranslate
    thinking_rids = find_regen_thinking_records(translated_file, original_file)
    
    if len(thinking_rids) == 0:
        print("\n✅ 재번역이 필요한 레코드가 없습니다!")
        return 0
    
    print(f"\n재번역 대상: {len(thinking_rids)}개 레코드")
    print()
    
    # Extract from original
    print("Step 1: Extract from original...")
    problem_recs = {}
    with original_file.open('r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            rid = f"{rec.get('group_id')}::{rec.get('entity_id')}"
            if rid in thinking_rids:
                problem_recs[rid] = rec
    
    print(f"✅ Extracted {len(problem_recs)} records")
    
    # Translate
    print("\nStep 2: Translate with JSON Schema...")
    translator = MedicalTermTranslator(
        model="gemini-2.0-flash-exp",
        temperature=0.0,
        use_rotator=True,
    )
    translator._translation_cache = {}
    
    def translate_one(rid, rec):
        try:
            translated = translator.translate_s2_record(rec, verbose=False)
            return (rid, translated, None)
        except Exception as e:
            return (rid, None, str(e))
    
    translated_recs = {}
    
    try:
        from tqdm import tqdm
        use_tqdm = True
    except:
        use_tqdm = False
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(translate_one, rid, rec): rid for rid, rec in problem_recs.items()}
        
        if use_tqdm:
            with tqdm(total=len(problem_recs), desc="Translating", unit="rec") as pbar:
                for future in as_completed(futures):
                    rid, trans, error = future.result()
                    if error:
                        print(f"\n❌ {rid}: {error}")
                        trans = problem_recs[rid]
                    translated_recs[rid] = trans
                    pbar.update(1)
        else:
            for i, future in enumerate(as_completed(futures), 1):
                rid, trans, error = future.result()
                if error:
                    print(f"❌ {rid}: {error}")
                    trans = problem_recs[rid]
                translated_recs[rid] = trans
                if i % 10 == 0:
                    print(f"  Progress: {i}/{len(problem_recs)}")
    
    print(f"\n✅ Translated {len(translated_recs)} records")
    
    # Merge
    print("\nStep 3: Merge into translated file...")
    import shutil
    backup = translated_file.with_suffix('.jsonl.backup_before_regen_retrans')
    shutil.copy2(translated_file, backup)
    print(f"✅ Backup: {backup.name}")
    
    temp_file = translated_file.with_suffix('.jsonl.tmp_regen_merge')
    merged = 0
    
    with translated_file.open('r', encoding='utf-8') as infile, \
         temp_file.open('w', encoding='utf-8') as outfile:
        
        for line in infile:
            if not line.strip():
                continue
            
            rec = json.loads(line)
            rid = f"{rec.get('group_id')}::{rec.get('entity_id')}"
            
            if rid in translated_recs:
                outfile.write(json.dumps(translated_recs[rid], ensure_ascii=False) + '\n')
                merged += 1
            else:
                outfile.write(line)
    
    temp_file.replace(translated_file)
    print(f"✅ Merged {merged} records")
    
    print("\n" + "=" * 80)
    print("✅ REGEN 파일 재번역 완료")
    print("=" * 80)
    print(f"재번역: {len(translated_recs)}개")
    print(f"병합: {merged}개")
    print(f"백업: {backup.name}")
    print("=" * 80)
    
    return 0


if __name__ == '__main__':
    exit(main())



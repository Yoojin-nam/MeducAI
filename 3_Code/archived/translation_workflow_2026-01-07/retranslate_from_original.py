#!/usr/bin/env python3
"""
Re-translate from ORIGINAL (untranslated) source.
Extract problem records from original, translate, then merge.
"""

import json
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

_THIS_DIR = Path(__file__).resolve().parent
_parent = _THIS_DIR.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from tools.anki.translate_medical_terms_module import MedicalTermTranslator


def extract_and_translate(
    original_file: Path,
    problem_record_ids: list,
    max_workers: int = 10,
) -> dict:
    """Extract problem records from original and translate them."""
    
    print(f"\n{'='*80}")
    print(f"Step 1: Extract {len(problem_record_ids)} records from original")
    print(f"{'='*80}")
    
    # Extract records
    problem_records = {}
    with original_file.open('r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            
            record = json.loads(line)
            rid = f"{record.get('group_id')}::{record.get('entity_id')}"
            
            if rid in problem_record_ids:
                problem_records[rid] = record
    
    print(f"✅ Extracted {len(problem_records)} records")
    
    if len(problem_records) != len(problem_record_ids):
        missing = set(problem_record_ids) - set(problem_records.keys())
        print(f"⚠️  Missing {len(missing)} records:")
        for rid in list(missing)[:5]:
            print(f"   - {rid}")
    
    # Translate
    print(f"\n{'='*80}")
    print(f"Step 2: Translate {len(problem_records)} records (parallel)")
    print(f"Workers: {max_workers}")
    print(f"{'='*80}")
    
    translator = MedicalTermTranslator(
        model="gemini-2.0-flash-exp",
        temperature=0.0,
        use_rotator=True,
    )
    translator._translation_cache = {}
    print("✅ Translator ready")
    
    def translate_one(rid: str, record: dict) -> tuple:
        """Translate one record."""
        try:
            translated = record.copy()
            if 'anki_cards' in translated:
                for card in translated['anki_cards']:
                    if 'front' in card:
                        card['front'] = translator.translate_text(
                            card['front'], use_cache=False, verbose=False
                        )
                    if 'back' in card:
                        card['back'] = translator.translate_text(
                            card['back'], use_cache=False, verbose=False
                        )
                    if 'options' in card and isinstance(card['options'], list):
                        card['options'] = [
                            translator.translate_text(opt, use_cache=False, verbose=False)
                            for opt in card['options']
                        ]
            return (rid, translated, None)
        except Exception as e:
            return (rid, None, str(e))
    
    # Execute parallel
    translated_records = {}
    
    try:
        from tqdm import tqdm
        use_tqdm = True
    except ImportError:
        use_tqdm = False
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(translate_one, rid, rec): rid
            for rid, rec in problem_records.items()
        }
        
        if use_tqdm:
            with tqdm(total=len(problem_records), desc="Translating", unit="rec") as pbar:
                for future in as_completed(futures):
                    rid, translated, error = future.result()
                    if error:
                        print(f"\n  ❌ {rid}: {error}")
                        translated = problem_records[rid]  # Use original
                    
                    translated_records[rid] = translated
                    pbar.update(1)
        else:
            for i, future in enumerate(as_completed(futures), 1):
                rid, translated, error = future.result()
                if error:
                    print(f"  ❌ {rid}: {error}")
                    translated = problem_records[rid]
                
                translated_records[rid] = translated
                
                if i % 5 == 0:
                    print(f"  Progress: {i}/{len(problem_records)}", flush=True)
    
    print(f"\n✅ Translated {len(translated_records)} records")
    return translated_records


def merge_translated(
    current_file: Path,
    translated_records: dict,
) -> int:
    """Merge translated records into current file."""
    
    print(f"\n{'='*80}")
    print(f"Step 3: Merge {len(translated_records)} translated records")
    print(f"{'='*80}")
    
    # Backup current
    backup = current_file.with_suffix('.jsonl.backup_before_merge')
    import shutil
    shutil.copy2(current_file, backup)
    print(f"✅ Backup: {backup.name}")
    
    # Merge
    temp_path = current_file.with_suffix('.jsonl.tmp_merge')
    merged_count = 0
    
    with current_file.open('r', encoding='utf-8') as infile, \
         temp_path.open('w', encoding='utf-8') as outfile:
        
        for line in infile:
            if not line.strip():
                continue
            
            record = json.loads(line)
            rid = f"{record.get('group_id')}::{record.get('entity_id')}"
            
            if rid in translated_records:
                # Use newly translated version
                outfile.write(json.dumps(translated_records[rid], ensure_ascii=False) + '\n')
                merged_count += 1
            else:
                # Keep original
                outfile.write(line)
    
    temp_path.replace(current_file)
    print(f"✅ Merged {merged_count} records")
    return merged_count


def main():
    base_dir = Path('/path/to/workspace/workspace/MeducAI/2_Data/metadata/generated/FINAL_DISTRIBUTION')
    
    # Problem record IDs
    problem_rids = [
        'grp_113da0a126::DERIVED:00713d63d157',
        'grp_18ee8088fe::DERIVED:786a53e04bcf',
        'grp_2337c30174::DERIVED:28a4560f55c8',
        'grp_2b9fdae40f::DERIVED:b07b262b8cd7',
        'grp_2e92fd1c33::DERIVED:2b793c129ed9',
        'grp_431482cf96::DERIVED:6bc32ef925bc',
        'grp_43721062bb::DERIVED:bcc646c82826',
        'grp_47059b1c5d::DERIVED:72d31fecaf4b',
        'grp_445892d0a8::DERIVED:efa6681970e4',
        'grp_49ebf93184::DERIVED:35df95c190fa',
        'grp_49ebf93184::DERIVED:c3a612366b2a',
        'grp_59c5b41288::DERIVED:20c979d0a2d6',
        'grp_5d0f9f278b::DERIVED:0465a3ee2eaf',
        'grp_5daf4c4f97::DERIVED:4c9382536c93',
        'grp_5eb744e770::DERIVED:49847bc089dd',
        'grp_670b2ec1aa::DERIVED:a0c964621b82',
        'grp_6f81a54dc6::DERIVED:125729c83b0f',
        'grp_6f81a54dc6::DERIVED:4480bdc9563e',
        'grp_7bec77b329::DERIVED:a40f79772cbc',
        'grp_8518594435::DERIVED:484102330144',
        'grp_83c32c3b78::DERIVED:f9850d8d7a4a',
        'grp_8eeecb0ab9::DERIVED:e0158092e42e',
        'grp_a0ae27e819::DERIVED:733047f486bd',
        'grp_ad44d0b476::DERIVED:8101f431d45b',
        'grp_b707f59277::DERIVED:281dd1fc657d',
        'grp_bbdf36f7b4::DERIVED:c78d6e3038c9',
        'grp_c29823aa9f::DERIVED:84d2ccc547a7',
        'grp_cdc6e3001c::DERIVED:b03bddfc8ad1',
        'grp_d116157c82::DERIVED:454704c38f97',
        'grp_d671480049::DERIVED:b9224821c614',
        'grp_dcf5b4dc09::DERIVED:45d963777636',
        'grp_f1bda06f3c::DERIVED:828a03c1cf15',
        'grp_fa10706bba::DERIVED:0ec0facc83dc',
        'grp_fa71a8dedf::DERIVED:cb3d1c7323cb',
    ]
    
    original_file = base_dir / 's2_results__s1armG__s2armG.jsonl'
    translated_file = base_dir / 's2_results__s1armG__s2armG__medterm_en.jsonl'
    
    print("=" * 80)
    print("재번역: 원본에서 시작")
    print("=" * 80)
    print(f"원본 (번역 전): {original_file.name}")
    print(f"대상 (병합할 곳): {translated_file.name}")
    print(f"재번역 레코드: {len(problem_rids)}개")
    
    # Extract and translate
    translated_recs = extract_and_translate(original_file, problem_rids, max_workers=10)
    
    # Merge
    merged = merge_translated(translated_file, translated_recs)
    
    print("\n" + "=" * 80)
    print("✅ COMPLETE")
    print("=" * 80)
    print(f"추출: {len(translated_recs)}개")
    print(f"번역: {len(translated_recs)}개")
    print(f"병합: {merged}개")
    print("=" * 80)
    
    return 0


if __name__ == '__main__':
    exit(main())

#!/usr/bin/env python3
"""
Re-translate records with improved JSON Schema approach.
"""

import json
import sys
import time
from pathlib import Path
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

_THIS_DIR = Path(__file__).resolve().parent
_parent = _THIS_DIR.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from tools.anki.translate_medical_terms_module import MedicalTermTranslator


def retranslate_file(
    input_path: Path,
    thinking_record_ids: list,
    max_workers: int = 10,
    verbose: bool = True,
) -> int:
    """Re-translate specific records with parallel processing."""
    
    print(f"\n{'='*80}")
    print(f"Re-translating {len(thinking_record_ids)} records with improved prompt")
    print(f"Parallel workers: {max_workers}")
    print(f"{'='*80}")
    
    # Initialize translator
    print("\nInitializing translator with JSON Schema...")
    translator = MedicalTermTranslator(
        model="gemini-2.0-flash-exp",
        temperature=0.0,
        use_rotator=True,
    )
    # CRITICAL: Clear cache to force re-translation
    translator._translation_cache = {}
    print("✅ Translator ready (cache cleared)")
    
    # Backup
    backup_path = input_path.with_suffix('.jsonl.backup_before_json_retrans')
    if not backup_path.exists():
        import shutil
        shutil.copy2(input_path, backup_path)
        print(f"✅ Backup: {backup_path.name}")
    
    # Load all records
    records = []
    record_order = {}  # Track original order
    
    with input_path.open('r', encoding='utf-8') as infile:
        for idx, line in enumerate(infile):
            if not line.strip():
                continue
            
            record = json.loads(line)
            group_id = record.get('group_id', '')
            entity_id = record.get('entity_id', '')
            record_id = f"{group_id}::{entity_id}"
            record_order[record_id] = idx
            records.append((record_id, record))
    
    # Separate records to translate vs keep
    to_translate = [(rid, rec) for rid, rec in records if rid in thinking_record_ids]
    to_keep = [(rid, rec) for rid, rec in records if rid not in thinking_record_ids]
    
    print(f"\nRecords to re-translate: {len(to_translate)}")
    print(f"Records to keep: {len(to_keep)}")
    
    # Parallel translation
    translated_records = {}
    write_lock = Lock()
    
    def translate_one_record(record_id: str, record: dict) -> tuple:
        """Translate a single record."""
        try:
            # Force re-translation without cache
            translated = record.copy()
            if 'anki_cards' in translated:
                for card in translated['anki_cards']:
                    if 'front' in card:
                        card['front'] = translator.translate_text(card['front'], use_cache=False, verbose=False)
                    if 'back' in card:
                        card['back'] = translator.translate_text(card['back'], use_cache=False, verbose=False)
                    if 'options' in card and isinstance(card['options'], list):
                        card['options'] = [
                            translator.translate_text(opt, use_cache=False, verbose=False) 
                            for opt in card['options']
                        ]
            return (record_id, translated, None)
        except Exception as e:
            return (record_id, None, str(e))
    
    # Execute parallel translation
    print(f"\nStarting parallel translation...")
    retranslated_count = 0
    
    try:
        from tqdm import tqdm
        use_tqdm = True
    except ImportError:
        use_tqdm = False
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(translate_one_record, rid, rec): rid
            for rid, rec in to_translate
        }
        
        if use_tqdm and verbose:
            with tqdm(total=len(to_translate), desc="Re-translating", unit="record") as pbar:
                for future in as_completed(futures):
                    record_id, translated, error = future.result()
                    if error:
                        print(f"\n  ❌ Error {record_id}: {error}")
                        # Keep original on error
                        translated = dict(next(rec for rid, rec in to_translate if rid == record_id))
                    
                    with write_lock:
                        translated_records[record_id] = translated
                        retranslated_count += 1
                    
                    pbar.update(1)
        else:
            completed = 0
            for future in as_completed(futures):
                record_id, translated, error = future.result()
                if error:
                    if verbose:
                        print(f"  ❌ Error {record_id}: {error}")
                    translated = dict(next(rec for rid, rec in to_translate if rid == record_id))
                
                with write_lock:
                    translated_records[record_id] = translated
                    retranslated_count += 1
                
                completed += 1
                if verbose and completed % 5 == 0:
                    print(f"  Progress: {completed}/{len(to_translate)}", flush=True)
    
    # Write output in original order
    temp_path = input_path.with_suffix('.jsonl.tmp_json_retrans')
    with temp_path.open('w', encoding='utf-8') as outfile:
        for record_id, record in records:
            if record_id in translated_records:
                outfile.write(json.dumps(translated_records[record_id], ensure_ascii=False) + '\n')
            else:
                outfile.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    # Replace
    temp_path.replace(input_path)
    print(f"\n✅ Re-translated {retranslated_count} records")
    return retranslated_count


def generate_comparison_html(backup_path: Path, current_path: Path, output_html: Path):
    """Generate before/after comparison HTML report."""
    import html as html_module
    
    # Load records
    backup_recs = {}
    with backup_path.open('r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                rid = f"{rec.get('group_id')}::{rec.get('entity_id')}"
                backup_recs[rid] = rec
    
    current_recs = {}
    with current_path.open('r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                rid = f"{rec.get('group_id')}::{rec.get('entity_id')}"
                current_recs[rid] = rec
    
    # Find changes
    changes = []
    for rid in backup_recs:
        if rid not in current_recs:
            continue
        for idx, (bc, cc) in enumerate(zip(
            backup_recs[rid].get('anki_cards', []),
            current_recs[rid].get('anki_cards', [])
        )):
            if bc.get('front') != cc.get('front') or bc.get('back') != cc.get('back'):
                changes.append({
                    'rid': rid,
                    'idx': idx,
                    'type': bc.get('card_type', ''),
                    'bf': bc.get('front', ''),
                    'cf': cc.get('front', ''),
                    'bb': bc.get('back', ''),
                    'cb': cc.get('back', ''),
                })
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>JSON Schema 재번역 비교</title>
<style>
body{{font-family:system-ui;max-width:1400px;margin:0 auto;padding:20px;background:#f5f5f5}}
.header{{background:white;padding:30px;border-radius:10px;margin-bottom:30px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}}
.card{{background:white;margin-bottom:30px;border-radius:10px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}}
.card-header{{background:#1976d2;color:white;padding:15px 20px;font-weight:bold}}
.card-body{{padding:20px}}
.comparison{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px}}
.before,.after{{border:2px solid #ddd;border-radius:5px;padding:15px}}
.before{{background:#fff3e0;border-color:#ff9800}}
.after{{background:#e8f5e9;border-color:#4caf50}}
.label{{font-weight:bold;margin-bottom:10px;padding:5px 10px;border-radius:3px;display:inline-block}}
.before .label{{background:#ff9800;color:white}}
.after .label{{background:#4caf50;color:white}}
.content{{white-space:pre-wrap;font-family:'Courier New',monospace;font-size:13px;line-height:1.6;background:white;padding:10px;border-radius:3px;max-height:400px;overflow-y:auto}}
</style></head><body>
<div class="header"><h1>🔄 JSON Schema 재번역 비교</h1>
<p><strong>개선:</strong> Structured JSON output → thinking 패턴 완전 제거</p>
<p><strong>변경:</strong> {len(changes)}개 카드</p></div>
"""
    
    for i, c in enumerate(changes, 1):
        html += f'<div class="card"><div class="card-header">#{i} | {html_module.escape(c["rid"])} | 카드 {c["idx"]+1} | {c["type"]}</div><div class="card-body">'
        
        if c['bf'] != c['cf']:
            html += f'<div class="comparison"><div class="before"><div class="label">❌ 재번역 전 (FRONT)</div><div class="content">{html_module.escape(c["bf"])}</div></div>'
            html += f'<div class="after"><div class="label">✅ 재번역 후 (FRONT)</div><div class="content">{html_module.escape(c["cf"])}</div></div></div>'
        
        if c['bb'] != c['cb']:
            html += f'<div class="comparison"><div class="before"><div class="label">❌ 재번역 전 (BACK)</div><div class="content">{html_module.escape(c["bb"])}</div></div>'
            html += f'<div class="after"><div class="label">✅ 재번역 후 (BACK)</div><div class="content">{html_module.escape(c["cb"])}</div></div></div>'
        
        html += '</div></div>'
    
    html += '</body></html>'
    output_html.write_text(html, encoding='utf-8')
    
    return len(changes)


def main():
    # Target records with thinking patterns
    thinking_records = [
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
    
    input_path = Path('/path/to/workspace/workspace/MeducAI/2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__medterm_en.jsonl')
    
    print("=" * 80)
    print("JSON Schema 기반 재번역")
    print("=" * 80)
    print(f"파일: {input_path.name}")
    print(f"대상: {len(thinking_records)}개 레코드")
    
    retranslated = retranslate_file(input_path, thinking_records, verbose=True)
    
    # Generate comparison report
    backup_path = input_path.with_suffix('.jsonl.backup_before_json_retrans')
    output_html = input_path.parent / 'json_schema_retranslation_comparison.html'
    
    if backup_path.exists():
        print(f"\n{'='*80}")
        print("Generating comparison report...")
        print(f"{'='*80}")
        
        changed = generate_comparison_html(backup_path, input_path, output_html)
        
        print(f"✅ HTML report: {output_html}")
        print(f"   {changed}개 카드 변경사항 포함")
    
    print("\n" + "=" * 80)
    print("✅ COMPLETE")
    print("=" * 80)
    print(f"재번역 완료: {retranslated}개")
    print(f"비교 리포트: {output_html.name}")
    print("=" * 80)
    
    return 0


if __name__ == '__main__':
    exit(main())


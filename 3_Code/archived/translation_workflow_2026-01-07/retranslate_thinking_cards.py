#!/usr/bin/env python3
"""
Re-translate records with thinking patterns.
Extract problem records, re-translate, and merge back.
"""

import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
import re

_THIS_DIR = Path(__file__).resolve().parent
_parent = _THIS_DIR.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from tools.anki.translate_medical_terms_module import MedicalTermTranslator


def find_thinking_records(jsonl_path: Path) -> List[str]:
    """Find record IDs with thinking patterns."""
    
    thinking_patterns = [
        r'Wait,',
        r'\*Wait',
        r'Rule\s+\d+',
        r'Final check',
        r'One last',
        r'is capitalized',
        r'is Korean',
        r'is English',
        r'\(No explanations\)',
        r'is not part of the output',
        r'Let\'s check',
        r'Let\'s look',
    ]
    
    record_ids = []
    
    with jsonl_path.open('r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            
            record = json.loads(line)
            group_id = record.get('group_id', '')
            entity_id = record.get('entity_id', '')
            record_id = f"{group_id}::{entity_id}"
            
            # Check for thinking patterns
            has_thinking = False
            for card in record.get('anki_cards', []):
                text = card.get('front', '') + '\n' + card.get('back', '')
                
                for pattern in thinking_patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        has_thinking = True
                        break
                
                if has_thinking:
                    break
            
            if has_thinking:
                record_ids.append(record_id)
    
    return record_ids


def retranslate_file(
    input_path: Path,
    output_path: Path,
    translator: MedicalTermTranslator,
    verbose: bool = True,
) -> int:
    """Re-translate entire file, only changing records with thinking patterns."""
    
    print(f"\n{'='*80}")
    print(f"Processing: {input_path.name}")
    print(f"{'='*80}")
    
    # Find thinking records
    print("Finding records with thinking patterns...")
    thinking_record_ids = set(find_thinking_records(input_path))
    
    print(f"✅ Found {len(thinking_record_ids)} records to re-translate")
    
    if len(thinking_record_ids) == 0:
        print("No records need re-translation. Copying original file...")
        import shutil
        shutil.copy2(input_path, output_path)
        return 0
    
    # Process file
    retranslated_count = 0
    total_records = 0
    
    with input_path.open('r', encoding='utf-8') as infile, \
         output_path.open('w', encoding='utf-8') as outfile:
        
        for line_num, line in enumerate(infile, 1):
            if not line.strip():
                continue
            
            total_records += 1
            record = json.loads(line)
            group_id = record.get('group_id', '')
            entity_id = record.get('entity_id', '')
            record_id = f"{group_id}::{entity_id}"
            
            # Check if needs re-translation
            if record_id in thinking_record_ids:
                if verbose:
                    print(f"\n[{retranslated_count + 1}/{len(thinking_record_ids)}] Re-translating: {record_id}")
                
                try:
                    # Re-translate
                    translated = translator.translate_s2_record(record, verbose=False)
                    outfile.write(json.dumps(translated, ensure_ascii=False) + '\n')
                    retranslated_count += 1
                    
                    if verbose:
                        print(f"  ✅ Complete")
                    
                    # Small delay
                    time.sleep(0.3)
                
                except Exception as e:
                    print(f"  ❌ Error: {e}")
                    print(f"  Using original record")
                    outfile.write(line)
            
            else:
                # Keep original
                outfile.write(line)
            
            # Progress
            if not verbose and total_records % 100 == 0:
                print(f"  Processed {total_records} records...", flush=True)
    
    print(f"\n✅ Re-translated {retranslated_count} / {len(thinking_record_ids)} records")
    return retranslated_count


def main():
    base_dir = Path('/path/to/workspace/workspace/MeducAI')
    dist_dir = base_dir / '2_Data/metadata/generated/FINAL_DISTRIBUTION'
    
    files_to_process = [
        ('s2_results__s1armG__s2armG__medterm_en.jsonl', '일반 파일'),
        ('s2_results__s1armG__s2armG__regen__medterm_en.jsonl', 'REGEN 파일'),
    ]
    
    print("=" * 80)
    print("Thinking Pattern Re-Translation")
    print("=" * 80)
    
    # Initialize translator
    print("\nInitializing translator...")
    translator = MedicalTermTranslator(
        model="gemini-2.0-flash-exp",
        temperature=0.0,
        use_rotator=True,
    )
    print("✅ Translator ready")
    
    # Process each file
    total_retranslated = 0
    
    for filename, label in files_to_process:
        input_path = dist_dir / filename
        
        if not input_path.exists():
            print(f"\n⚠️  {label}: File not found")
            continue
        
        # Backup original
        backup_path = input_path.with_suffix('.jsonl.backup_before_retrans')
        if not backup_path.exists():
            import shutil
            print(f"\nCreating backup: {backup_path.name}")
            shutil.copy2(input_path, backup_path)
        
        # Re-translate to temp file
        temp_path = input_path.with_suffix('.jsonl.retranslated_temp')
        
        retranslated = retranslate_file(
            input_path,
            temp_path,
            translator,
            verbose=True,
        )
        
        total_retranslated += retranslated
        
        # Replace original
        if retranslated > 0:
            temp_path.replace(input_path)
            print(f"✅ Updated: {filename}")
        else:
            temp_path.unlink()
            print(f"✅ No changes needed: {filename}")
    
    print("\n" + "=" * 80)
    print("✅ COMPLETE")
    print("=" * 80)
    print(f"Total records re-translated: {total_retranslated}")
    print(f"\nBackups created:")
    for filename, _ in files_to_process:
        backup = dist_dir / f"{filename}.backup_before_retrans"
        if backup.exists():
            print(f"  - {backup.name}")
    print("=" * 80)
    
    return 0


if __name__ == '__main__':
    exit(main())


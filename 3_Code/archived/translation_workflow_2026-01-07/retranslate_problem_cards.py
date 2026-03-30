#!/usr/bin/env python3
"""
Re-translate problem cards that have thinking patterns mixed with content.
These cards cannot be fixed with regex - need full re-translation.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add parent to path for imports
_THIS_DIR = Path(__file__).resolve().parent
_parent = _THIS_DIR.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from tools.anki.translate_medical_terms_module import MedicalTermTranslator


def extract_problem_cards(
    jsonl_path: Path,
    problem_indices: List[int],
    output_path: Path,
) -> int:
    """
    Extract problem cards from JSONL based on HTML report indices.
    
    Args:
        jsonl_path: Path to the JSONL file
        problem_indices: List of card indices from HTML report (1-based)
        output_path: Path to save problem cards
        
    Returns:
        Number of problem cards extracted
    """
    print(f"Extracting problem cards from: {jsonl_path}")
    
    # Load all records
    records = []
    with jsonl_path.open('r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    
    # Find changed cards (same logic as HTML report generation)
    # Need to load backup to match
    backup_path = jsonl_path.parent / f"{jsonl_path.name}.backup_thinking_20260108_162343"
    if not backup_path.exists():
        # Try finding any backup
        backups = list(jsonl_path.parent.glob(f"{jsonl_path.name}.backup_thinking_*"))
        if backups:
            backup_path = sorted(backups)[-1]  # Most recent
    
    backup_records = []
    if backup_path.exists():
        with backup_path.open('r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    backup_records.append(json.loads(line))
    
    # Find changed records
    changed_records = []
    for record, backup_record in zip(records, backup_records):
        if 'anki_cards' not in record or 'anki_cards' not in backup_record:
            continue
        
        for card, backup_card in zip(record['anki_cards'], backup_record['anki_cards']):
            if card.get('front') != backup_card.get('front') or \
               card.get('back') != backup_card.get('back'):
                changed_records.append({
                    'record': backup_record,  # Use backup (has thinking)
                    'group_id': backup_record.get('group_id'),
                    'entity_id': backup_record.get('entity_id'),
                })
                break
    
    # Extract problem cards based on indices
    problem_cards = []
    for idx in problem_indices:
        if 0 < idx <= len(changed_records):
            problem_cards.append(changed_records[idx - 1])
    
    # Save to output
    with output_path.open('w', encoding='utf-8') as f:
        for item in problem_cards:
            f.write(json.dumps(item['record'], ensure_ascii=False) + '\n')
    
    print(f"✅ Extracted {len(problem_cards)} problem cards to: {output_path}")
    return len(problem_cards)


def retranslate_cards(
    problem_cards_path: Path,
    output_path: Path,
    translator: MedicalTermTranslator,
    verbose: bool = True,
) -> int:
    """
    Re-translate problem cards.
    
    Args:
        problem_cards_path: Path to problem cards JSONL
        output_path: Path to save re-translated cards
        translator: Translator instance
        verbose: Whether to print progress
        
    Returns:
        Number of cards re-translated
    """
    print(f"\nRe-translating cards from: {problem_cards_path}")
    
    records = []
    with problem_cards_path.open('r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    
    if verbose:
        print(f"Found {len(records)} records to re-translate")
    
    # Re-translate each record
    translated_records = []
    
    for i, record in enumerate(records, 1):
        if verbose:
            print(f"\n[{i}/{len(records)}] Re-translating {record.get('group_id')}::{record.get('entity_id')}")
        
        try:
            translated = translator.translate_s2_record(record, verbose=False)
            translated_records.append(translated)
            
            if verbose:
                print(f"  ✅ Complete")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            # Save original on error
            translated_records.append(record)
        
        # Small delay to avoid rate limits
        time.sleep(0.5)
    
    # Save re-translated records
    with output_path.open('w', encoding='utf-8') as f:
        for record in translated_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"\n✅ Re-translated {len(translated_records)} records")
    print(f"   Saved to: {output_path}")
    
    return len(translated_records)


def merge_retranslated_cards(
    original_jsonl: Path,
    retranslated_jsonl: Path,
    output_path: Path,
) -> int:
    """
    Merge re-translated cards back into original JSONL.
    
    Args:
        original_jsonl: Original JSONL file
        retranslated_jsonl: Re-translated cards JSONL
        output_path: Path to save merged result
        
    Returns:
        Number of records updated
    """
    print(f"\nMerging re-translated cards...")
    
    # Load re-translated cards
    retranslated = {}
    with retranslated_jsonl.open('r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                record = json.loads(line)
                key = f"{record.get('group_id')}::{record.get('entity_id')}"
                retranslated[key] = record
    
    print(f"Loaded {len(retranslated)} re-translated records")
    
    # Load original and merge
    updated_count = 0
    with original_jsonl.open('r', encoding='utf-8') as infile, \
         output_path.open('w', encoding='utf-8') as outfile:
        
        for line in infile:
            if not line.strip():
                continue
            
            record = json.loads(line)
            key = f"{record.get('group_id')}::{record.get('entity_id')}"
            
            # Use re-translated version if available
            if key in retranslated:
                record = retranslated[key]
                updated_count += 1
            
            outfile.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"✅ Merged {updated_count} re-translated records")
    print(f"   Output: {output_path}")
    
    return updated_count


def main():
    parser = argparse.ArgumentParser(
        description='Re-translate problem cards with thinking patterns'
    )
    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help='Input JSONL file'
    )
    parser.add_argument(
        '--problem-indices',
        type=str,
        required=True,
        help='Comma-separated list of problem card indices (1-based, from HTML report)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Output merged JSONL file (default: input_retranslated.jsonl)'
    )
    parser.add_argument(
        '--temp-dir',
        type=Path,
        help='Temporary directory for intermediate files (default: same as input)'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Parse problem indices
    problem_indices = [int(x.strip()) for x in args.problem_indices.split(',')]
    print(f"Problem card indices: {problem_indices}")
    print(f"Total: {len(problem_indices)} cards")
    
    # Setup paths
    input_path = args.input.resolve()
    temp_dir = args.temp_dir or input_path.parent
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    problem_cards_path = temp_dir / f"{input_path.stem}_problem_cards.jsonl"
    retranslated_path = temp_dir / f"{input_path.stem}_retranslated.jsonl"
    output_path = args.output or input_path.with_name(f"{input_path.stem}_fixed.jsonl")
    
    # Step 1: Extract problem cards
    print("\n" + "="*80)
    print("STEP 1: Extract problem cards")
    print("="*80)
    
    extracted_count = extract_problem_cards(
        input_path,
        problem_indices,
        problem_cards_path,
    )
    
    if extracted_count == 0:
        print("No problem cards found!")
        return 1
    
    # Step 2: Re-translate
    print("\n" + "="*80)
    print("STEP 2: Re-translate problem cards")
    print("="*80)
    
    translator = MedicalTermTranslator(
        model="gemini-2.0-flash-exp",
        temperature=0.0,
        use_rotator=True,
    )
    
    retranslated_count = retranslate_cards(
        problem_cards_path,
        retranslated_path,
        translator,
        verbose=args.verbose,
    )
    
    # Step 3: Merge back
    print("\n" + "="*80)
    print("STEP 3: Merge re-translated cards")
    print("="*80)
    
    merged_count = merge_retranslated_cards(
        input_path,
        retranslated_path,
        output_path,
    )
    
    print("\n" + "="*80)
    print("✅ COMPLETE")
    print("="*80)
    print(f"Extracted: {extracted_count} cards")
    print(f"Re-translated: {retranslated_count} cards")
    print(f"Merged: {merged_count} records")
    print(f"\nOutput file: {output_path}")
    
    return 0


if __name__ == '__main__':
    exit(main())


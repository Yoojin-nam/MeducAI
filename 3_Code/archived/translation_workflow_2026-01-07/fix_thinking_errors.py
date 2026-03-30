#!/usr/bin/env python3
"""
Fix thinking pattern errors in translated JSONL files.

This script:
1. Identifies cards with thinking pattern errors
2. Re-translates them using the fixed translation module
3. Updates JSONL files in-place (with backups)
"""

import argparse
import json
import re
import sys
import shutil
from pathlib import Path
from typing import Any, Dict, List, Set
from datetime import datetime

_THIS_DIR = Path(__file__).resolve().parent
_parent = _THIS_DIR.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from tools.anki.translate_medical_terms_module import MedicalTermTranslator

# Thinking patterns to detect
THINKING_PATTERNS = [
    r"Let's re-evaluate",
    r"Rule \d+:",
    r'So "',
    r"\*Let's",
    r"One detail:",
    r"This is already",
    r"The input has",
    r"Final check on",
    r'^\s*"\s*is just the plain',
    r'^\s*"[^"]*"\s*is just the plain',
]


def has_thinking_text(text: str) -> bool:
    """Check if text contains thinking patterns."""
    if not text:
        return False
    for pattern in THINKING_PATTERNS:
        if re.search(pattern, str(text), re.IGNORECASE | re.MULTILINE):
            return True
    return False


def check_card_for_errors(card: Dict[str, Any]) -> List[str]:
    """Check a single card for thinking pattern errors.
    
    Returns:
        List of field names with errors (e.g., ['front', 'back'])
    """
    error_fields = []
    
    if has_thinking_text(card.get('front', '')):
        error_fields.append('front')
    
    if has_thinking_text(card.get('back', '')):
        error_fields.append('back')
    
    if 'options' in card and isinstance(card['options'], list):
        for opt_idx, opt in enumerate(card['options']):
            if has_thinking_text(opt):
                error_fields.append(f'option_{opt_idx}')
    
    return error_fields


def scan_jsonl_for_errors(jsonl_path: Path) -> Dict[int, List[int]]:
    """Scan JSONL file for records with thinking pattern errors.
    
    Returns:
        Dict mapping line_num -> list of card indices with errors
    """
    error_records = {}
    
    with jsonl_path.open('r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            try:
                record = json.loads(line)
                
                if 'anki_cards' not in record:
                    continue
                
                error_card_indices = []
                for card_idx, card in enumerate(record['anki_cards']):
                    error_fields = check_card_for_errors(card)
                    if error_fields:
                        error_card_indices.append(card_idx)
                
                if error_card_indices:
                    error_records[line_num] = error_card_indices
                    
            except json.JSONDecodeError as e:
                print(f"  [WARN] JSON error at line {line_num}: {e}", file=sys.stderr)
    
    return error_records


def fix_jsonl_file(
    input_path: Path,
    output_path: Path,
    translator: MedicalTermTranslator,
    error_records: Dict[int, List[int]],
    verbose: bool = True,
) -> int:
    """Fix thinking errors in JSONL file.
    
    Args:
        input_path: Input JSONL file
        output_path: Output JSONL file
        translator: Translator instance (with fixed module)
        error_records: Dict mapping line_num -> card indices to fix
        verbose: Print progress
        
    Returns:
        Number of cards fixed
    """
    cards_fixed = 0
    records_fixed = 0
    
    with input_path.open('r', encoding='utf-8') as infile, \
         output_path.open('w', encoding='utf-8') as outfile:
        
        for line_num, line in enumerate(infile, 1):
            if not line.strip():
                continue
            
            try:
                record = json.loads(line)
                
                # Check if this record needs fixing
                if line_num in error_records:
                    error_card_indices = error_records[line_num]
                    
                    if 'anki_cards' in record:
                        for card_idx in error_card_indices:
                            if card_idx < len(record['anki_cards']):
                                card = record['anki_cards'][card_idx]
                                error_fields = check_card_for_errors(card)
                                
                                if verbose:
                                    entity_id = record.get('entity_id', '')
                                    print(f"  Fixing line {line_num}, card {card_idx} ({entity_id}): {', '.join(error_fields)}")
                                
                                # Re-translate the card
                                fixed_card = translator.translate_card(card, verbose=False)
                                record['anki_cards'][card_idx] = fixed_card
                                cards_fixed += 1
                    
                    records_fixed += 1
                
                # Write record (fixed or original)
                outfile.write(json.dumps(record, ensure_ascii=False) + '\n')
                
            except json.JSONDecodeError as e:
                print(f"  [ERROR] JSON error at line {line_num}: {e}", file=sys.stderr)
                # Write original line as-is
                outfile.write(line)
    
    return cards_fixed


def main():
    parser = argparse.ArgumentParser(description='Fix thinking pattern errors in translated JSONL files')
    parser.add_argument('--input', type=Path, required=True, help='Input JSONL file')
    parser.add_argument('--output', type=Path, help='Output JSONL file (default: overwrite input with backup)')
    parser.add_argument('--model', default='gemini-3-flash-preview', help='Gemini model name')
    parser.add_argument('--no-backup', action='store_true', help='Do not create backup file')
    parser.add_argument('--dry-run', action='store_true', help='Only scan for errors, do not fix')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    input_path = args.input.resolve()
    
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Scanning {input_path} for thinking pattern errors...")
    error_records = scan_jsonl_for_errors(input_path)
    
    total_errors = sum(len(indices) for indices in error_records.values())
    
    print(f"Found {total_errors} cards with errors in {len(error_records)} records")
    
    if total_errors == 0:
        print("No errors found. Nothing to fix.")
        return
    
    if args.dry_run:
        print("\n[Dry run] Would fix the following:")
        for line_num in sorted(error_records.keys())[:20]:
            print(f"  Line {line_num}: {len(error_records[line_num])} cards")
        if len(error_records) > 20:
            print(f"  ... and {len(error_records) - 20} more records")
        return
    
    # Determine output path
    if args.output:
        output_path = args.output.resolve()
    else:
        # Overwrite input (with backup)
        output_path = input_path
        if not args.no_backup:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = input_path.with_suffix(f'.jsonl.backup_{timestamp}')
            print(f"Creating backup: {backup_path}")
            shutil.copy2(input_path, backup_path)
    
    # Initialize translator with fixed module
    print(f"Initializing translator (model: {args.model})...")
    translator = MedicalTermTranslator(
        model=args.model,
        temperature=0.0,
        use_rotator=True,
    )
    
    # Fix errors
    print(f"Re-translating {total_errors} cards...")
    
    if output_path == input_path:
        # Write to temp file first, then replace
        temp_path = input_path.with_suffix('.jsonl.tmp')
        cards_fixed = fix_jsonl_file(
            input_path,
            temp_path,
            translator,
            error_records,
            verbose=args.verbose,
        )
        # Replace original
        temp_path.replace(input_path)
    else:
        cards_fixed = fix_jsonl_file(
            input_path,
            output_path,
            translator,
            error_records,
            verbose=args.verbose,
        )
    
    print(f"\n✅ Fixed {cards_fixed} cards")
    print(f"Output: {output_path}")
    
    # Verify fix
    print("\nVerifying fix...")
    remaining_errors = scan_jsonl_for_errors(output_path)
    remaining_count = sum(len(indices) for indices in remaining_errors.values())
    
    if remaining_count == 0:
        print("✅ All thinking patterns removed!")
    else:
        print(f"⚠️  Warning: {remaining_count} errors still remain")
        print("   This may indicate that the translation module needs further adjustment")


if __name__ == '__main__':
    main()


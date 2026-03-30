#!/usr/bin/env python3
"""
Selectively fix thinking pattern errors ONLY in cards that will appear in export.

For regen file: Only fix CARD_REGEN cards (others use baseline text)
"""

import argparse
import json
import csv
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


def load_s5_decisions(s5_csv_path: Path) -> Dict[str, str]:
    """Load card-level decisions from AppSheet S5.csv.
    
    Returns:
        Dict mapping card_uid -> decision
    """
    decisions = {}
    with open(s5_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            card_uid = row.get('card_uid', '')
            decision = row.get('s5_decision', '')
            if card_uid and decision:
                decisions[card_uid] = decision
    return decisions


def build_card_uid(record: Dict[str, Any], card_idx: int, card: Dict[str, Any]) -> str:
    """Build card UID matching S5.csv format."""
    group_id = record.get('group_id', '')
    entity_id = record.get('entity_id', '')
    card_role = card.get('card_role', '')
    return f"{group_id}::{entity_id}__{card_role}__{card_idx}"


def scan_regen_selective(
    regen_path: Path,
    s5_decisions: Dict[str, str],
    filter_decision: str = 'CARD_REGEN'
) -> Dict[int, List[int]]:
    """Scan regen file for errors in specific decision type only.
    
    Returns:
        Dict mapping line_num -> list of card indices to fix
    """
    error_records = {}
    
    with regen_path.open('r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            try:
                record = json.loads(line)
                
                if 'anki_cards' not in record:
                    continue
                
                error_card_indices = []
                for card_idx, card in enumerate(record['anki_cards']):
                    # Build card UID
                    card_uid = build_card_uid(record, card_idx, card)
                    decision = s5_decisions.get(card_uid, '')
                    
                    # Only check if this decision type
                    if decision == filter_decision:
                        # Check for errors
                        has_error = (
                            has_thinking_text(card.get('front', '')) or
                            has_thinking_text(card.get('back', ''))
                        )
                        
                        if 'options' in card and isinstance(card['options'], list):
                            for opt in card['options']:
                                if has_thinking_text(opt):
                                    has_error = True
                                    break
                        
                        if has_error:
                            error_card_indices.append(card_idx)
                
                if error_card_indices:
                    error_records[line_num] = error_card_indices
                    
            except json.JSONDecodeError as e:
                print(f"  [WARN] JSON error at line {line_num}: {e}", file=sys.stderr)
    
    return error_records


def fix_jsonl_selective(
    input_path: Path,
    output_path: Path,
    translator: MedicalTermTranslator,
    error_records: Dict[int, List[int]],
    verbose: bool = True,
) -> int:
    """Fix only specified cards in JSONL file."""
    cards_fixed = 0
    
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
                                
                                if verbose:
                                    entity_id = record.get('entity_id', '')
                                    card_role = card.get('card_role', '')
                                    print(f"  Fixing line {line_num}, card {card_idx} ({entity_id} {card_role})")
                                
                                # Re-translate the card
                                fixed_card = translator.translate_card(card, verbose=False)
                                record['anki_cards'][card_idx] = fixed_card
                                cards_fixed += 1
                
                # Write record (fixed or original)
                outfile.write(json.dumps(record, ensure_ascii=False) + '\n')
                
            except json.JSONDecodeError as e:
                print(f"  [ERROR] JSON error at line {line_num}: {e}", file=sys.stderr)
                # Write original line as-is
                outfile.write(line)
    
    return cards_fixed


def main():
    parser = argparse.ArgumentParser(description='Selectively fix thinking errors in regen file (CARD_REGEN only)')
    parser.add_argument('--regen', type=Path, required=True, help='Regen JSONL file')
    parser.add_argument('--s5-csv', type=Path, required=True, help='S5.csv with card decisions')
    parser.add_argument('--output', type=Path, help='Output file (default: overwrite with backup)')
    parser.add_argument('--model', default='gemini-3-flash-preview', help='Gemini model')
    parser.add_argument('--no-backup', action='store_true', help='Do not create backup')
    parser.add_argument('--dry-run', action='store_true', help='Only scan, do not fix')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    regen_path = args.regen.resolve()
    s5_csv_path = args.s5_csv.resolve()
    
    if not regen_path.exists():
        print(f"Error: Regen file not found: {regen_path}", file=sys.stderr)
        sys.exit(1)
    
    if not s5_csv_path.exists():
        print(f"Error: S5 CSV not found: {s5_csv_path}", file=sys.stderr)
        sys.exit(1)
    
    # Load S5 decisions
    print(f"Loading S5 decisions from {s5_csv_path}...")
    s5_decisions = load_s5_decisions(s5_csv_path)
    card_regen_count = sum(1 for d in s5_decisions.values() if d == 'CARD_REGEN')
    print(f"  Loaded {len(s5_decisions)} decisions ({card_regen_count} CARD_REGEN)")
    
    # Scan for errors in CARD_REGEN cards only
    print(f"\nScanning {regen_path} for CARD_REGEN errors...")
    error_records = scan_regen_selective(regen_path, s5_decisions, 'CARD_REGEN')
    
    total_errors = sum(len(indices) for indices in error_records.values())
    
    print(f"Found {total_errors} CARD_REGEN cards with thinking errors in {len(error_records)} records")
    
    if total_errors == 0:
        print("✅ No CARD_REGEN errors found. Nothing to fix.")
        return
    
    if args.dry_run:
        print("\n[Dry run] Would fix the following CARD_REGEN cards:")
        for line_num in sorted(error_records.keys()):
            print(f"  Line {line_num}: {len(error_records[line_num])} cards")
        return
    
    # Determine output path
    if args.output:
        output_path = args.output.resolve()
    else:
        output_path = regen_path
        if not args.no_backup:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = regen_path.with_suffix(f'.jsonl.backup_{timestamp}')
            print(f"Creating backup: {backup_path}")
            shutil.copy2(regen_path, backup_path)
    
    # Initialize translator
    print(f"\nInitializing translator (model: {args.model})...")
    translator = MedicalTermTranslator(
        model=args.model,
        temperature=0.0,
        use_rotator=True,
    )
    
    # Fix errors
    print(f"Re-translating {total_errors} CARD_REGEN cards...")
    
    if output_path == regen_path:
        # Write to temp file first
        temp_path = regen_path.with_suffix('.jsonl.tmp')
        cards_fixed = fix_jsonl_selective(
            regen_path,
            temp_path,
            translator,
            error_records,
            verbose=args.verbose,
        )
        # Replace original
        temp_path.replace(regen_path)
    else:
        cards_fixed = fix_jsonl_selective(
            regen_path,
            output_path,
            translator,
            error_records,
            verbose=args.verbose,
        )
    
    print(f"\n✅ Fixed {cards_fixed} CARD_REGEN cards")
    print(f"Output: {output_path}")
    
    # Verify
    print("\nVerifying fix...")
    remaining = scan_regen_selective(output_path, s5_decisions, 'CARD_REGEN')
    remaining_count = sum(len(indices) for indices in remaining.values())
    
    if remaining_count == 0:
        print("✅ All CARD_REGEN thinking patterns removed!")
    else:
        print(f"⚠️  Warning: {remaining_count} CARD_REGEN errors still remain")


if __name__ == '__main__':
    main()


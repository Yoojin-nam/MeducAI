#!/usr/bin/env python3
"""
Aggressively remove ALL thinking pattern text from JSONL files.
No re-translation - just pattern-based text cleaning.
"""

import argparse
import json
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Comprehensive thinking patterns - more aggressive
THINKING_REMOVAL_PATTERNS = [
    # Direct patterns
    (r"Let's re-evaluate[^\n]*\n", ''),
    (r"Rule \d+:[^\n]*\n", ''),
    (r'So "[^"]*"[^\n]*\n', ''),
    (r"\*Let's[^\n]*\n", ''),
    (r"One detail:[^\n]*\n", ''),
    (r"This is already[^\n]*\n", ''),
    (r"The input has[^\n]*\n", ''),
    (r"Final check on[^\n]*\n", ''),
    (r'Wait,[^\n]*\n', ''),
    (r'If I follow Rule[^\n]*\n', ''),
    
    # Quoted patterns
    (r'^\s*"\s*is just the plain[^\n]*\n', ''),
    (r'^\s*"[^"]*"\s*is just the plain[^\n]*\n', ''),
    
    # Markdown asterisk patterns
    (r'\*\s*Wait,[^\*]*\*', ''),
    (r'\*\s*Rule \d+:[^\*]*\*', ''),
    (r'\*\s*Final check[^\*]*\*', ''),
    (r'\*\s*One detail:[^\*]*\*', ''),
    (r'\*\s*Let\'s[^\*]*\*', ''),
    
    # Additional aggressive patterns
    (r'I\'ll just use[^\n]*\n', ''),
    (r'I\'ll use[^\n]*\n', ''),
    (r'Keep "[^"]*"[^\n]*\n', ''),
    (r'\(No, that\'s[^\)]*\)[^\n]*\n', ''),
    (r'\(Wait,[^\)]*\)[^\n]*\n', ''),
    
    # Sentence fragments starting with thinking words
    (r'^\s*Wait[^\n]*\n', ''),
    (r'^\s*So\s+[^\n]*\n', ''),
    
    # Multiple asterisks patterns (markdown bold gone wrong)
    (r'\*\s*\*\s*\*+', ''),
    (r'\*{2,}\s*\n', ''),
]


def clean_thinking_text(text: str) -> str:
    """Aggressively remove all thinking pattern text."""
    if not text:
        return text
    
    result = str(text)
    
    # Apply all patterns
    for pattern, replacement in THINKING_REMOVAL_PATTERNS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE | re.MULTILINE)
    
    # Clean up aftermath
    # Remove lines with only whitespace or punctuation
    lines = result.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip empty lines, lines with only *, or lines with only punctuation
        if stripped and not re.match(r'^[\*\s\.\,\:\;]*$', stripped):
            cleaned_lines.append(line)
    
    result = '\n'.join(cleaned_lines)
    
    # Clean up multiple consecutive newlines
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    # Clean up empty asterisks
    result = re.sub(r'\*\s*\*', '', result)
    result = re.sub(r'^\*\s*$', '', result, flags=re.MULTILINE)
    
    return result.strip()


def clean_card(card: Dict[str, Any]) -> Dict[str, Any]:
    """Clean thinking text from a single card."""
    cleaned = card.copy()
    
    if 'front' in cleaned:
        cleaned['front'] = clean_thinking_text(cleaned['front'])
    
    if 'back' in cleaned:
        cleaned['back'] = clean_thinking_text(cleaned['back'])
    
    if 'options' in cleaned and isinstance(cleaned['options'], list):
        cleaned['options'] = [clean_thinking_text(opt) for opt in cleaned['options']]
    
    return cleaned


def clean_jsonl_file(input_path: Path, output_path: Path, verbose: bool = True) -> int:
    """Clean all cards in JSONL file."""
    cards_cleaned = 0
    records_processed = 0
    
    with input_path.open('r', encoding='utf-8') as infile, \
         output_path.open('w', encoding='utf-8') as outfile:
        
        for line_num, line in enumerate(infile, 1):
            if not line.strip():
                continue
            
            try:
                record = json.loads(line)
                
                if 'anki_cards' in record and record['anki_cards']:
                    for card_idx, card in enumerate(record['anki_cards']):
                        cleaned_card = clean_card(card)
                        record['anki_cards'][card_idx] = cleaned_card
                        cards_cleaned += 1
                
                records_processed += 1
                
                # Write cleaned record
                outfile.write(json.dumps(record, ensure_ascii=False) + '\n')
                
                if verbose and records_processed % 500 == 0:
                    print(f"  Processed {records_processed} records...", flush=True)
                
            except json.JSONDecodeError as e:
                print(f"  [ERROR] JSON error at line {line_num}: {e}")
                # Write original line
                outfile.write(line)
    
    return cards_cleaned


def main():
    parser = argparse.ArgumentParser(description='Aggressively clean thinking patterns from JSONL')
    parser.add_argument('--input', type=Path, required=True, help='Input JSONL file')
    parser.add_argument('--output', type=Path, help='Output file (default: overwrite with backup)')
    parser.add_argument('--no-backup', action='store_true', help='Do not create backup')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    input_path = args.input.resolve()
    
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return 1
    
    # Determine output path
    if args.output:
        output_path = args.output.resolve()
    else:
        output_path = input_path
        if not args.no_backup:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = input_path.with_suffix(f'.jsonl.backup_clean_{timestamp}')
            print(f"Creating backup: {backup_path}")
            shutil.copy2(input_path, backup_path)
    
    print(f"Cleaning {input_path}...")
    
    # Write to temp first
    if output_path == input_path:
        temp_path = input_path.with_suffix('.jsonl.tmp_clean')
        cards_cleaned = clean_jsonl_file(input_path, temp_path, verbose=args.verbose)
        temp_path.replace(input_path)
    else:
        cards_cleaned = clean_jsonl_file(input_path, output_path, verbose=args.verbose)
    
    print(f"\n✅ Cleaned {cards_cleaned} cards")
    print(f"Output: {output_path}")
    
    return 0


if __name__ == '__main__':
    exit(main())


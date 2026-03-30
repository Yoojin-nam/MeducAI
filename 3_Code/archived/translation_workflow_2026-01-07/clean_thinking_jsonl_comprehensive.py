#!/usr/bin/env python3
"""
Comprehensive thinking pattern cleaner for Anki JSONL files.
Removes ALL thinking/reasoning patterns from Gemini translation output.
"""

import argparse
import json
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Comprehensive thinking patterns (based on actual findings)
THINKING_REMOVAL_PATTERNS = [
    # Wait patterns (very aggressive - remove everything with Wait,)
    (r'Wait,\s*\"[^\"]*\"[^\n]*', ''),  # No \n? at end - remove inline
    (r'Wait,\s*[^\n]+', ''),  # Anything after Wait,
    (r'\*\s*Wait,\s*\"[^\"]*\"[^\n]*\*', ''),
    (r'\*\s*Wait,\s*[^\*]*\*', ''),
    (r'\*\s*Wait,\s*', ''),
    
    # Rule checking patterns (aggressive)
    (r'Rule\s+\d+\s+says[^\n.]*\.?', ''),  # Remove until period
    (r'Rule\s+\d+:[^\n]*', ''),  # Remove entire line
    (r'If I then apply Rule[^\n.]*\.?', ''),
    (r'am I violating Rule[^\n.]*\.?', ''),
    (r'Then\s+Rule\s+\d+[^\n.]*\.?', ''),
    
    # Capitalization commentary (aggressive)
    (r'\"[^\"]*\"\s*is capitalized[^\n.]*\.?', ''),
    (r'[^\n]*\"\s*is capitalized[^\n.]*\.?', ''),  # Catch mid-sentence
    (r'\"[^\"]*\"\s*is lowercase[^\n.]*\.?', ''),
    (r'After\s*[^,]+,\s*\"[^\"]*\"\s*is capitalized[^\n.]*\.?', ''),
    
    # Language commentary (aggressive)
    (r'\"[^\"]*\"\s*is Korean[^\n.]*\.?', ''),
    (r'\"[^\"]*\"\s*is English[^\n.]*\.?', ''),
    (r'\"[^\"]*\"\s*is just English[^\n.]*\.?', ''),
    (r'[^\n]*\"\s*is Korean[^\n.]*\.?', ''),  # Mid-sentence
    (r'[^\n]*\"\s*is English[^\n.]*\.?', ''),  # Mid-sentence
    
    # Check/verification statements (aggressive)
    (r'Final check on[^\n.]+\.?', ''),
    (r'One last check on[^\n.]+\.?', ''),
    (r'One last look at[^\n.]+\.?', ''),
    (r'One more thing:[^\n.]+\.?', ''),
    (r'One detail:[^\n.]+\.?', ''),
    
    # Reasoning statements (aggressive)
    (r'But\s*\"[^\"]*\"\s*is[^\n.]*\.?', ''),
    (r'Actually,\s*[^\n.]+\.?', ''),
    (r'Let\'s[^\n.]+\.?', ''),
    (r'So\s*\"[^\"]*\"[^\n.]*\.?', ''),
    (r'I will[^\n.]+\.?', ''),
    (r'I\'ll[^\n.]+\.?', ''),
    
    # Meta statements (aggressive)
    (r'\(No explanations\)[^\n]*', ''),
    (r'\(End of prompt\)[^\n]*', ''),
    (r'is not part of the output[^\n.]*\.?', ''),
    (r'Final string:[^\n]+', ''),
    (r'the standard way to write it[^\n.]*\.?', ''),
    (r'It doesn\'t[^\n.]+\.?', ''),
    
    # Markdown asterisk patterns (in middle of text)
    (r'\*\s*Rule\s+\d+[^\*]+\*', ''),
    (r'\*\s*Final check[^\*]+\*', ''),
    (r'\*\s*One detail:[^\*]+\*', ''),
    (r'\*\s*Let\'s[^\*]+\*', ''),
    (r'\*\s*But\s*[^\*]+\*', ''),
    
    # Parenthetical reasoning
    (r'\(Wait,[^\)]*\)', ''),
    (r'\(But[^\)]*\)', ''),
    (r'\(Rule\s+\d+[^\)]*\)', ''),
    
    # Sentence fragments starting with thinking words (at line start)
    (r'^\s*Wait[^\n]*\n', ''),
    (r'^\s*But\s+[^\n]*\n', ''),
    (r'^\s*So\s+[^\n]*\n', ''),
    (r'^\s*Actually[^\n]*\n', ''),
    (r'^\s*Then\s+Rule[^\n]*\n', ''),
    
    # Incomplete sentences (common artifact)
    (r'Yes,\s*it is\.[^\n]*', ''),
    (r'No,\s*[^\n.]+\.', ''),
    (r'Correct\.[^\n]+', ''),
]


def clean_thinking_text(text: str) -> str:
    """Aggressively remove all thinking pattern text."""
    if not text:
        return text
    
    result = str(text)
    
    # Apply all patterns (multiple passes to handle nested patterns)
    for _ in range(2):  # Two passes to catch nested patterns
        for pattern, replacement in THINKING_REMOVAL_PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE | re.MULTILINE)
    
    # Clean up aftermath
    # Remove lines with only whitespace or punctuation
    lines = result.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip empty lines, lines with only *, or lines with only punctuation
        if stripped and not re.match(r'^[\*\s\.\,\:\;\-]*$', stripped):
            cleaned_lines.append(line)
    
    result = '\n'.join(cleaned_lines)
    
    # Clean up multiple consecutive newlines
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    # Clean up empty asterisks
    result = re.sub(r'\*\s*\*', '', result)
    result = re.sub(r'^\*\s*$', '', result, flags=re.MULTILINE)
    
    # Remove standalone asterisks on their own lines
    result = re.sub(r'^\s*\*\s*\n', '', result, flags=re.MULTILINE)
    
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


def clean_jsonl_file(input_path: Path, output_path: Path, verbose: bool = True) -> tuple:
    """Clean all cards in JSONL file."""
    cards_cleaned = 0
    records_processed = 0
    records_with_changes = 0
    
    with input_path.open('r', encoding='utf-8') as infile, \
         output_path.open('w', encoding='utf-8') as outfile:
        
        for line_num, line in enumerate(infile, 1):
            if not line.strip():
                continue
            
            try:
                record = json.loads(line)
                original_record = json.dumps(record, ensure_ascii=False)
                
                if 'anki_cards' in record and record['anki_cards']:
                    for card_idx, card in enumerate(record['anki_cards']):
                        cleaned_card = clean_card(card)
                        record['anki_cards'][card_idx] = cleaned_card
                        cards_cleaned += 1
                
                records_processed += 1
                
                # Check if anything changed
                new_record = json.dumps(record, ensure_ascii=False)
                if original_record != new_record:
                    records_with_changes += 1
                
                # Write cleaned record
                outfile.write(json.dumps(record, ensure_ascii=False) + '\n')
                
                if verbose and records_processed % 500 == 0:
                    print(f"  Processed {records_processed} records...", flush=True)
                
            except json.JSONDecodeError as e:
                print(f"  [ERROR] JSON error at line {line_num}: {e}")
                # Write original line
                outfile.write(line)
    
    return cards_cleaned, records_with_changes


def main():
    parser = argparse.ArgumentParser(
        description='Comprehensively clean thinking patterns from JSONL'
    )
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
            backup_path = input_path.with_suffix(f'.jsonl.backup_thinking_{timestamp}')
            print(f"Creating backup: {backup_path}")
            shutil.copy2(input_path, backup_path)
    
    print(f"Cleaning {input_path}...")
    
    # Write to temp first
    if output_path == input_path:
        temp_path = input_path.with_suffix('.jsonl.tmp_thinking_clean')
        cards_cleaned, records_changed = clean_jsonl_file(
            input_path, temp_path, verbose=args.verbose
        )
        temp_path.replace(input_path)
    else:
        cards_cleaned, records_changed = clean_jsonl_file(
            input_path, output_path, verbose=args.verbose
        )
    
    print(f"\n✅ Cleaned {cards_cleaned} cards")
    print(f"   Records with changes: {records_changed}")
    print(f"Output: {output_path}")
    
    return 0


if __name__ == '__main__':
    exit(main())


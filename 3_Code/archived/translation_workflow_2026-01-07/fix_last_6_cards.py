#!/usr/bin/env python3
"""
Fix the last 6 stubborn cards with thinking patterns.
Manual targeted fix for specific card UIDs.
"""

import csv
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent.parent

# Problematic card UIDs (expanded)
TARGET_CARDS = [
    'grp_43721062bb::DERIVED:bcc646c82826__Q1__0',
    'grp_ad44d0b476::DERIVED:8101f431d45b__Q1__0',
    'grp_cdc6e3001c::DERIVED:b03bddfc8ad1__Q2__1',
    'grp_d671480049::DERIVED:b9224821c614__Q1__0',
    'grp_dcf5b4dc09::DERIVED:45d963777636__Q2__1',
    'grp_fa71a8dedf::DERIVED:cb3d1c7323cb__Q1__0',
    'grp_49ebf93184::DERIVED:c3a612366b2a__Q1__0',
    'grp_6f81a54dc6::DERIVED:125729c83b0f__Q1__0',
]

def aggressive_clean(text):
    """Remove all thinking patterns aggressively."""
    if not text:
        return text
    
    # Remove everything that looks like thinking (super aggressive)
    patterns = [
        # Rule-related
        r'am I violating Rule[^\n]*\n',
        r'Rule \d+[^\n]*\n',
        r'Rule \d+[^\n]*',  # No newline version
        
        # If/But statements
        r'If I translate[^\n]*\n',
        r'If I[^\n]*\n',
        r'But "[^"]*" is[^\n]*\n',
        r'But [^\n]*\n',
        
        # Actually/Okay/Let's
        r'Actually,[^\n]*\n',
        r'Actually,[^\n]*',
        r'Okay, I will[^\n]*\n',
        r'Okay,[^\n]*\n',
        r'Okay,[^\n]*',
        r'Let\'s see if[^\n]*\n',
        r'Let\'s try to find[^\n]*\n',
        r'Let\'s review[^\n]*\n',
        r'Let\'s [^\n]*\n',
        r'Let\'s [^\n]*',
        
        # Yes/No
        r'Yes, it is\.[^\n]*\n',
        r'Yes,[^\n]*\n',
        r'No,[^\n]*\n',
        
        # Wait
        r'Wait,[^\n]*\n',
        r'Wait,[^\n]*',
        r'\*\s*Wait,[^\*]*\*',
        
        # I'll statements
        r'I\'ll just[^\n]*\n',
        r'I\'ll just[^\n]*',
        r'I\'ll [^\n]*\n',
        r'I will [^\n]*\n',
        
        # Asterisk patterns
        r'\*\s*Actually,[^\*]*\*',
        r'\*\s*Let\'s[^\*]*\*',
        r'\*\s*Okay,[^\*]*\*',
        r'\*\s*I\'ll[^\*]*\*',
        
        # Question patterns
        r'am I[^\n]*\?',
        r'Am I[^\n]*\?',
    ]
    
    result = text
    for p in patterns:
        result = re.sub(p, '', result, flags=re.IGNORECASE | re.MULTILINE)
    
    # Clean up
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = re.sub(r'^\s*\*\s*$', '', result, flags=re.MULTILINE)
    result = re.sub(r'\*\s*\*', '', result)
    
    return result.strip()

# Process Cards.csv
cards_csv = BASE_DIR / '6_Distributions/Final_QA/AppSheet_Export_TRANSLATED_FINAL/Cards.csv'
output_csv = BASE_DIR / '6_Distributions/Final_QA/AppSheet_Export_TRANSLATED_FINAL/Cards_TEMP.csv'

fixed_count = 0

with open(cards_csv, 'r', encoding='utf-8') as infile, \
     open(output_csv, 'w', encoding='utf-8', newline='') as outfile:
    
    reader = csv.DictReader(infile)
    writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
    writer.writeheader()
    
    for row in reader:
        card_uid = row.get('card_uid', '')
        
        if card_uid in TARGET_CARDS:
            # Clean thinking patterns
            row['front'] = aggressive_clean(row['front'])
            row['back'] = aggressive_clean(row['back'])
            fixed_count += 1
            print(f"Fixed: {card_uid}")
        
        writer.writerow(row)

print(f"\n✅ Fixed {fixed_count} cards")

# Replace original
output_csv.replace(cards_csv)
print(f"✅ Updated: {cards_csv}")


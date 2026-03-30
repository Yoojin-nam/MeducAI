#!/usr/bin/env python3
"""
Filter Cards.csv to keep only specific card UIDs (maintaining original assignment).
"""

import csv
import sys
from pathlib import Path

def main():
    if len(sys.argv) < 4:
        print("Usage: python filter_cards_by_uid.py <input_cards.csv> <uid_list.txt> <output_cards.csv>")
        sys.exit(1)
    
    input_csv = Path(sys.argv[1])
    uid_list_file = Path(sys.argv[2])
    output_csv = Path(sys.argv[3])
    
    # Load target UIDs
    target_uids = set()
    with open(uid_list_file, 'r', encoding='utf-8') as f:
        for line in f:
            uid = line.strip()
            if uid:
                target_uids.add(uid)
    
    print(f"Target UIDs: {len(target_uids):,}")
    
    # Filter cards
    with open(input_csv, 'r', encoding='utf-8') as infile, \
         open(output_csv, 'w', encoding='utf-8', newline='') as outfile:
        
        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
        writer.writeheader()
        
        kept = 0
        for row in reader:
            card_uid = row.get('card_uid', '')
            if card_uid in target_uids:
                writer.writerow(row)
                kept += 1
    
    print(f"Filtered: {kept:,} cards kept")
    print(f"Output: {output_csv}")
    
    if kept != len(target_uids):
        print(f"\n⚠️  Warning: {len(target_uids) - kept} UIDs not found in input")

if __name__ == '__main__':
    main()


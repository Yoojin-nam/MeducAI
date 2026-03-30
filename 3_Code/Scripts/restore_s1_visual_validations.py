#!/usr/bin/env python3
"""
Restore S1 visual validation data from backup partial file into final validation file.

This script:
1. Loads complete S1 visual validation data from backup partial file
2. Loads current final validation file (with S2 card validations)
3. Merges: Restores S1 visual data while preserving S2 card data
4. Outputs: Updated validation file with complete data

Usage:
    python3 restore_s1_visual_validations.py --backup <backup_file> --current <current_file> --output <output_file>
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import shutil

def load_jsonl(file_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load JSONL file into dict keyed by group_id."""
    data = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_no, line in enumerate(f, 1):
            try:
                record = json.loads(line)
                group_id = record.get('group_id')
                if not group_id:
                    print(f"Warning: Line {line_no} missing group_id, skipping", file=sys.stderr)
                    continue
                data[group_id] = record
            except json.JSONDecodeError as e:
                print(f"Error: Line {line_no} invalid JSON: {e}", file=sys.stderr)
                continue
    return data

def merge_s1_visual_data(current_record: Dict[str, Any], backup_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge S1 visual validation data from backup into current record.
    
    Preserves:
    - All S2 card validation data from current
    - All other fields from current
    
    Restores:
    - table_visual_validation or table_visual_validations from backup
    
    Returns:
        Merged record with complete data
    """
    merged = current_record.copy()
    
    # Get S1 validation from both sources
    current_s1 = current_record.get('s1_table_validation', {})
    backup_s1 = backup_record.get('s1_table_validation', {})
    
    if not backup_s1:
        # No S1 data in backup, keep current
        return merged
    
    # Create merged S1 validation
    merged_s1 = current_s1.copy()
    
    # Restore visual validation data from backup
    if 'table_visual_validation' in backup_s1:
        merged_s1['table_visual_validation'] = backup_s1['table_visual_validation']
    
    if 'table_visual_validations' in backup_s1:
        merged_s1['table_visual_validations'] = backup_s1['table_visual_validations']
    
    # Update merged record
    merged['s1_table_validation'] = merged_s1
    
    return merged

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Restore S1 visual validation data from backup")
    parser.add_argument('--backup', type=str, required=True, help="Backup partial file path")
    parser.add_argument('--current', type=str, required=True, help="Current validation file path")
    parser.add_argument('--output', type=str, required=True, help="Output validation file path")
    parser.add_argument('--backup-current', action='store_true', help="Backup current file before overwriting")
    
    args = parser.parse_args()
    
    backup_path = Path(args.backup)
    current_path = Path(args.current)
    output_path = Path(args.output)
    
    # Verify input files exist
    if not backup_path.exists():
        print(f"Error: Backup file not found: {backup_path}", file=sys.stderr)
        sys.exit(1)
    
    if not current_path.exists():
        print(f"Error: Current file not found: {current_path}", file=sys.stderr)
        sys.exit(1)
    
    # Backup current file if requested
    if args.backup_current and output_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{output_path.stem}__backup_{timestamp}{output_path.suffix}"
        backup_dest = output_path.parent / backup_name
        shutil.copy2(output_path, backup_dest)
        print(f"✅ Backed up current file to: {backup_dest}")
    
    print(f"Loading backup file: {backup_path}")
    backup_data = load_jsonl(backup_path)
    print(f"  Loaded {len(backup_data)} groups from backup")
    
    print(f"Loading current file: {current_path}")
    current_data = load_jsonl(current_path)
    print(f"  Loaded {len(current_data)} groups from current")
    
    # Merge data
    print("\nMerging visual validation data...")
    merged_data: List[Dict[str, Any]] = []
    groups_with_visuals_restored = 0
    total_visuals_restored = 0
    
    for group_id in sorted(current_data.keys()):
        current_record = current_data[group_id]
        backup_record = backup_data.get(group_id)
        
        if backup_record:
            merged_record = merge_s1_visual_data(current_record, backup_record)
            
            # Count restored visuals
            s1_val = merged_record.get('s1_table_validation', {})
            if 'table_visual_validation' in s1_val:
                groups_with_visuals_restored += 1
                total_visuals_restored += 1
            elif 'table_visual_validations' in s1_val:
                groups_with_visuals_restored += 1
                total_visuals_restored += len(s1_val['table_visual_validations'])
        else:
            print(f"  Warning: Group {group_id} not found in backup, keeping current data", file=sys.stderr)
            merged_record = current_record
        
        merged_data.append(merged_record)
    
    # Write output
    print(f"\nWriting merged data to: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for record in merged_data:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"\n✅ Restoration complete!")
    print(f"   Groups processed: {len(merged_data)}")
    print(f"   Groups with visuals restored: {groups_with_visuals_restored}")
    print(f"   Total visual validations restored: {total_visuals_restored}")
    print(f"   Output file: {output_path}")

if __name__ == '__main__':
    main()


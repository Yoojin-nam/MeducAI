"""
Deduplicate S2 entity records in JSONL files.

Strategy:
1. For each (group_id, entity_id) combination, keep only one record
2. If multiple records exist, prefer the one with repair metadata
3. If both/neither have repair metadata, keep the first one
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def load_jsonl(file_path):
    """Load JSONL file."""
    records = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    records.append((line_num, json.loads(line)))
                except json.JSONDecodeError as e:
                    print(f"  ⚠️  Error parsing line {line_num}: {e}")
    return records

def save_jsonl(records, file_path):
    """Save JSONL file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

def has_repair_metadata(record):
    """Check if any card in the record has repair metadata."""
    for card in record.get('anki_cards', []):
        if card.get('_repair_metadata'):
            return True
    return False

def deduplicate_records(records_with_lines):
    """Deduplicate records, preferring those with repair metadata."""
    
    # Group by (group_id, entity_id)
    entity_groups = defaultdict(list)
    
    for line_num, record in records_with_lines:
        key = (record['group_id'], record['entity_id'])
        entity_groups[key].append((line_num, record))
    
    # Statistics
    total_entities = len(entity_groups)
    duplicate_count = sum(1 for k, v in entity_groups.items() if len(v) > 1)
    
    print(f"  Total unique entities: {total_entities}")
    print(f"  Entities with duplicates: {duplicate_count}")
    
    # Keep one record per entity
    deduplicated = []
    removed_lines = []
    
    for key, group in entity_groups.items():
        if len(group) == 1:
            # No duplicates, keep as is
            deduplicated.append(group[0][1])
        else:
            # Multiple records - choose the best one
            group_id, entity_id = key
            
            # Prefer records with repair metadata
            with_repair = [r for r in group if has_repair_metadata(r[1])]
            
            if with_repair:
                # Keep the first one with repair metadata
                chosen = with_repair[0]
                removed = [r for r in group if r != chosen]
            else:
                # Keep the first record
                chosen = group[0]
                removed = group[1:]
            
            deduplicated.append(chosen[1])
            removed_lines.extend([r[0] for r in removed])
            
            print(f"  • {group_id}/{entity_id}: kept line {chosen[0]}, removed lines {[r[0] for r in removed]}")
    
    return deduplicated, removed_lines

def main():
    base_dir = Path("/path/to/workspace/workspace/MeducAI")
    data_dir = base_dir / "2_Data/metadata/generated/FINAL_DISTRIBUTION"
    
    # Files to deduplicate
    files = [
        "s2_results__s1armG__s2armG.jsonl",
        "s2_results__s1armG__s2armG__regen.jsonl"
    ]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for filename in files:
        filepath = data_dir / filename
        
        if not filepath.exists():
            print(f"⚠️  File not found: {filename}")
            continue
        
        print(f"\n{'='*60}")
        print(f"Processing: {filename}")
        print(f"{'='*60}")
        
        # Load records
        print("Loading records...")
        records_with_lines = load_jsonl(filepath)
        print(f"  Loaded {len(records_with_lines)} records")
        
        # Create backup
        backup_dir = data_dir / "archive"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / f"{filename}.before_dedup_{timestamp}"
        
        import shutil
        shutil.copy(filepath, backup_path)
        print(f"  📦 Backup: {backup_path.name}")
        
        # Deduplicate
        print("\nDeduplicating...")
        deduplicated, removed_lines = deduplicate_records(records_with_lines)
        
        print(f"\n  Before: {len(records_with_lines)} records")
        print(f"  After: {len(deduplicated)} records")
        print(f"  Removed: {len(removed_lines)} duplicate(s)")
        
        # Save deduplicated file
        save_jsonl(deduplicated, filepath)
        print(f"  ✅ Saved to: {filename}")
        
        # Save removed lines log
        if removed_lines:
            log_file = base_dir / "logs" / f"removed_duplicates_{filename}.{timestamp}.txt"
            with open(log_file, 'w') as f:
                f.write(f"Removed line numbers from {filename}:\n")
                for line_num in sorted(removed_lines):
                    f.write(f"{line_num}\n")
            print(f"  📝 Removed lines logged to: {log_file.name}")
    
    print(f"\n{'='*60}")
    print("✅ Deduplication complete!")
    print(f"{'='*60}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


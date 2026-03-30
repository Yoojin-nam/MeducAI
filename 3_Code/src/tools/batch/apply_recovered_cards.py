"""
Apply the 6 recovered cards to the S2 regen JSONL file.
"""

import json
from pathlib import Path

def load_jsonl(file_path):
    """Load JSONL file."""
    records = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records

def save_jsonl(records, file_path):
    """Save JSONL file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

def main():
    base_dir = Path("/path/to/workspace/workspace/MeducAI")
    
    # Load error log to get key mappings
    error_log = base_dir / "logs/batch_parse_errors_20260106_101612.json"
    with open(error_log, 'r', encoding='utf-8') as f:
        error_data = json.load(f)
    
    # Create line_num -> key mapping
    line_to_key = {}
    for failed in error_data["failed_lines"]:
        line_num = str(failed["line_num"])
        key = failed["key"]
        line_to_key[line_num] = key
    
    print("Key mappings:")
    for line_num, key in sorted(line_to_key.items()):
        print(f"  Line {line_num}: {key}")
    
    # Load recovered cards
    recovered_file = base_dir / "logs/all_recovered_6_cards.json"
    with open(recovered_file, 'r', encoding='utf-8') as f:
        recovered = json.load(f)
    
    print(f"\nLoaded {len(recovered)} recovered cards")
    
    # Parse keys to extract (group_id, entity_id, card_role)
    card_updates = {}
    for line_num, data in recovered.items():
        key = line_to_key[line_num]
        
        # Parse key: s2r_{group_id}_{entity_id}_{card_role}
        if key.startswith("s2r_"):
            parts = key.replace("s2r_", "").rsplit("_", 1)
            card_role = parts[-1]  # Q2
            remaining = parts[0].rsplit("_", 1)
            entity_id = remaining[-1]
            group_id = remaining[0]
            
            card_updates[(group_id, entity_id, card_role)] = data
            print(f"  {key} -> ({group_id}, {entity_id}, {card_role})")
    
    # Load S2 regen file
    s2_regen_path = base_dir / "2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__regen.jsonl"
    s2_records = load_jsonl(s2_regen_path)
    
    print(f"\nLoaded {len(s2_records)} S2 records from regen file")
    
    # Apply updates
    updated_count = 0
    for record in s2_records:
        group_id = record.get("group_id", "")
        entity_id = record.get("entity_id", "")
        
        # Iterate through anki_cards array
        anki_cards = record.get("anki_cards", [])
        for card in anki_cards:
            card_role = card.get("card_role", "")
            
            key = (group_id, entity_id, card_role)
            
            if key in card_updates:
                improved = card_updates[key]
                
                # Update fields
                card["front"] = improved.get("improved_front", card.get("front", ""))
                card["back"] = improved.get("improved_back", card.get("back", ""))
                
                # Add repair metadata to the card
                if "_repair_metadata" not in card:
                    card["_repair_metadata"] = {}
                
                card["_repair_metadata"]["manually_recovered"] = True
                card["_repair_metadata"]["recovery_source"] = "fix_truncated_json.py"
                
                updated_count += 1
                print(f"  ✅ Updated: {group_id}/{entity_id}/{card_role}")
    
    print(f"\nUpdated {updated_count} cards")
    
    # Save updated file
    save_jsonl(s2_records, s2_regen_path)
    print(f"💾 Saved to: {s2_regen_path}")
    
    # Create backup with timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = base_dir / "2_Data/metadata/generated/FINAL_DISTRIBUTION/archive"
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / f"s2_results__s1armG__s2armG__regen__before_manual_fix_{timestamp}.jsonl"
    
    # Actually, backup the old version from archive
    old_backup = base_dir / "2_Data/metadata/generated/FINAL_DISTRIBUTION/archive/before_improved_parsing_20260106_101118/s2_results__s1armG__s2armG__regen.jsonl"
    if old_backup.exists():
        import shutil
        shutil.copy(old_backup, backup_path)
        print(f"📦 Backup created: {backup_path}")
    
    print("\n✅ All 6 recovered cards have been applied to the S2 regen file!")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())


#!/usr/bin/env python3
"""
Check S1/S2 completion status
"""
import json
from pathlib import Path
from collections import defaultdict

def check_completion(run_tag, arm="G"):
    """Check S1/S2 completion status."""
    base_dir = Path("2_Data/metadata/generated")
    run_dir = base_dir / run_tag
    
    if not run_dir.exists():
        print(f"❌ Run directory not found: {run_dir}")
        return
    
    # Load S1 results
    s1_path = run_dir / f"stage1_struct__arm{arm}.jsonl"
    s2_path = run_dir / f"s2_results__s1arm{arm}__s2arm{arm}.jsonl"
    
    s1_groups = set()
    s2_groups = set()
    s2_entities = defaultdict(set)
    
    # Load S1 groups
    if s1_path.exists():
        with open(s1_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    group_id = record.get("group_id", "")
                    if group_id:
                        s1_groups.add(group_id)
                except Exception:
                    pass
    
    # Load S2 groups and entities
    if s2_path.exists():
        with open(s2_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    group_id = record.get("group_id", "")
                    entity_id = record.get("entity_id", "")
                    entity_name = record.get("entity_name", "")
                    
                    if group_id:
                        s2_groups.add(group_id)
                        if entity_id:
                            s2_entities[group_id].add((entity_id, entity_name))
                except Exception:
                    pass
    
    print("=" * 80)
    print(f"S1/S2 Completion Status for {run_tag} (arm {arm})")
    print("=" * 80)
    print()
    print(f"S1 Groups: {len(s1_groups)}")
    print(f"S2 Groups: {len(s2_groups)}")
    print()
    
    # Missing S2 groups
    missing_s2 = s1_groups - s2_groups
    if missing_s2:
        print(f"❌ Missing S2 Groups ({len(missing_s2)}):")
        for gid in sorted(missing_s2):
            print(f"  - {gid}")
        print()
    
    # Groups with partial S2 (some entities missing)
    partial_s2 = []
    for group_id in s2_groups:
        # Check if all S1 entities have S2 results
        # This is approximate - we'd need to load S1 entity list to be precise
        pass
    
    # Success rate
    if s1_groups:
        success_rate = len(s2_groups) / len(s1_groups) * 100
        print(f"✅ Success Rate: {success_rate:.1f}% ({len(s2_groups)}/{len(s1_groups)})")
    
    # Entity statistics
    total_entities = sum(len(entities) for entities in s2_entities.values())
    print(f"Total S2 Entities: {total_entities}")
    print()
    
    # Check for the failed group
    failed_group = "grp_dc7faeae74"
    if failed_group in s1_groups:
        if failed_group in s2_groups:
            print(f"✅ {failed_group}: Has S2 results ({len(s2_entities.get(failed_group, set()))} entities)")
        else:
            print(f"❌ {failed_group}: Missing S2 results")
    else:
        print(f"⚠️  {failed_group}: Not in S1 results")

if __name__ == "__main__":
    import sys
    run_tag = sys.argv[1] if len(sys.argv) > 1 else "FINAL_DISTRIBUTION"
    check_completion(run_tag)


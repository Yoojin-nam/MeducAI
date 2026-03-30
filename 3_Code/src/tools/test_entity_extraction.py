#!/usr/bin/env python3
"""
Entity Extraction Test Script

Test script to compare S1 entity_list with S2 entity results.
Verifies that all entities from S1 are processed in S2.

Usage:
    python 3_Code/src/tools/test_entity_extraction.py \
        --base_dir . \
        --run_tag FINAL_DISTRIBUTION \
        --arm G \
        [--output <output.md>]
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

# Add workspace root to path for imports
_SCRIPT_DIR = Path(__file__).resolve().parent
_WORKSPACE_ROOT = _SCRIPT_DIR.parent.parent.parent.parent
sys.path.insert(0, str(_WORKSPACE_ROOT / "3_Code" / "archived"))


# =========================
# Data Loading Functions
# =========================

def load_s1_entities(s1_path: Path) -> Tuple[Dict[str, List[Dict[str, str]]], Dict[str, int]]:
    """
    Load entities from S1 results.
    
    Returns:
        Tuple of:
        - entities_by_group: Dict[group_id, List[{entity_id, entity_name}]]
        - entity_counts: Dict[group_id, count]
    """
    if not s1_path.exists():
        raise FileNotFoundError(f"S1 structure file not found: {s1_path}")
    
    entities_by_group = defaultdict(list)  # Use list to handle duplicates
    entity_counts = {}
    seen_entity_ids = defaultdict(set)  # Track unique entity_id per group
    
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                s1_data = json.loads(line)
                group_id = s1_data.get("group_id", "").strip()
                if not group_id:
                    continue
                
                entity_list = s1_data.get("entity_list", [])
                if not isinstance(entity_list, list):
                    entity_list = []
                
                # Extract entity_id and entity_name from each entity
                # Aggregate entities from all occurrences of the same group_id
                for entity in entity_list:
                    if isinstance(entity, dict):
                        entity_id = entity.get("entity_id", "").strip()
                        entity_name = entity.get("entity_name", "").strip()
                        if entity_id and entity_id not in seen_entity_ids[group_id]:
                            seen_entity_ids[group_id].add(entity_id)
                            entities_by_group[group_id].append({
                                "entity_id": entity_id,
                                "entity_name": entity_name,
                            })
                    elif isinstance(entity, str):
                        # Fallback: if entity is just a string, use it as name
                        entity_id = entity.strip()
                        if entity_id and entity_id not in seen_entity_ids[group_id]:
                            seen_entity_ids[group_id].add(entity_id)
                            entities_by_group[group_id].append({
                                "entity_id": entity_id,
                                "entity_name": entity_id,
                            })
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Failed to parse S1 line: {e}", file=sys.stderr)
                continue
    
    # Convert to regular dict and compute counts
    entities_by_group = dict(entities_by_group)
    for group_id in entities_by_group:
        entity_counts[group_id] = len(entities_by_group[group_id])
    
    return entities_by_group, entity_counts


def load_s2_entities(s2_path: Path) -> Tuple[Dict[str, List[Dict[str, str]]], Dict[str, int], Dict[str, int]]:
    """
    Load entities from S2 results.
    
    Returns:
        Tuple of:
        - entities_by_group: Dict[group_id, List[{entity_id, entity_name}]]
        - entity_counts: Dict[group_id, count]
        - card_counts: Dict[group_id, total_cards]
    """
    if not s2_path.exists():
        raise FileNotFoundError(f"S2 results file not found: {s2_path}")
    
    entities_by_group = defaultdict(list)
    entity_counts = defaultdict(int)
    card_counts = defaultdict(int)
    seen_entities = defaultdict(set)  # Track unique entity_id per group
    
    with open(s2_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                s2_record = json.loads(line)
                group_id = s2_record.get("group_id", "").strip()
                entity_id = s2_record.get("entity_id", "").strip()
                entity_name = s2_record.get("entity_name", "").strip()
                
                if not group_id or not entity_id:
                    continue
                
                # Count cards for this entity
                anki_cards = s2_record.get("anki_cards", [])
                card_count = len(anki_cards) if isinstance(anki_cards, list) else 0
                card_counts[group_id] += card_count
                
                # Track unique entities (deduplicate by entity_id)
                if entity_id not in seen_entities[group_id]:
                    seen_entities[group_id].add(entity_id)
                    entities_by_group[group_id].append({
                        "entity_id": entity_id,
                        "entity_name": entity_name,
                    })
                    entity_counts[group_id] += 1
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Failed to parse S2 line: {e}", file=sys.stderr)
                continue
    
    return dict(entities_by_group), dict(entity_counts), dict(card_counts)


# =========================
# Comparison Functions
# =========================

def compare_entity_counts(
    s1_entities: Dict[str, List[Dict[str, str]]],
    s1_counts: Dict[str, int],
    s2_entities: Dict[str, List[Dict[str, str]]],
    s2_counts: Dict[str, int],
) -> Dict[str, Any]:
    """
    Compare S1 and S2 entity counts and identify missing entities.
    
    Returns:
        Comparison results dictionary with:
        - total_s1_entities: int
        - total_s2_entities: int
        - missing_count: int
        - groups_match: Dict[group_id, bool]
        - missing_by_group: Dict[group_id, List[entity_info]]
        - extra_in_s2: Dict[group_id, List[entity_info]]
    """
    all_group_ids = set(list(s1_entities.keys()) + list(s2_entities.keys()))
    
    total_s1 = sum(s1_counts.values())
    total_s2 = sum(s2_counts.values())
    
    groups_match = {}
    missing_by_group = {}
    extra_in_s2 = {}
    
    for group_id in all_group_ids:
        s1_entity_list = s1_entities.get(group_id, [])
        s2_entity_list = s2_entities.get(group_id, [])
        
        s1_count = len(s1_entity_list)
        s2_count = len(s2_entity_list)
        
        # Check if counts match
        groups_match[group_id] = (s1_count == s2_count)
        
        # Find missing entities (in S1 but not in S2)
        s1_entity_ids = {e["entity_id"] for e in s1_entity_list}
        s2_entity_ids = {e["entity_id"] for e in s2_entity_list}
        
        missing_ids = s1_entity_ids - s2_entity_ids
        if missing_ids:
            missing_entities = [
                e for e in s1_entity_list
                if e["entity_id"] in missing_ids
            ]
            missing_by_group[group_id] = missing_entities
        
        # Find extra entities (in S2 but not in S1) - should be empty
        extra_ids = s2_entity_ids - s1_entity_ids
        if extra_ids:
            extra_entities = [
                e for e in s2_entity_list
                if e["entity_id"] in extra_ids
            ]
            extra_in_s2[group_id] = extra_entities
    
    return {
        "total_s1_entities": total_s1,
        "total_s2_entities": total_s2,
        "missing_count": total_s1 - total_s2,
        "groups_match": groups_match,
        "missing_by_group": missing_by_group,
        "extra_in_s2": extra_in_s2,
    }


# =========================
# Report Generation
# =========================

def generate_test_report(
    s1_entities: Dict[str, List[Dict[str, str]]],
    s1_counts: Dict[str, int],
    s2_entities: Dict[str, List[Dict[str, str]]],
    s2_counts: Dict[str, int],
    s2_card_counts: Dict[str, int],
    comparison: Dict[str, Any],
    run_tag: str,
    arm: str,
) -> str:
    """Generate Markdown test report."""
    lines = []
    lines.append("# Entity Extraction Test Report")
    lines.append("")
    lines.append(f"**RUN_TAG**: `{run_tag}`")
    lines.append(f"**ARM**: `{arm}`")
    lines.append(f"**Test Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # Overall summary
    total_s1 = comparison["total_s1_entities"]
    total_s2 = comparison["total_s2_entities"]
    missing = comparison["missing_count"]
    match_rate = (total_s2 / total_s1 * 100) if total_s1 > 0 else 0
    
    lines.append("## Executive Summary")
    lines.append("")
    
    if missing == 0:
        lines.append("✅ **PASS**: All S1 entities are present in S2 results.")
    else:
        lines.append(f"🔴 **FAIL**: {missing} entities ({100 - match_rate:.1f}%) missing from S2.")
    
    lines.append("")
    lines.append("| Metric | S1 | S2 | Difference |")
    lines.append("|--------|----|----|------------|")
    lines.append(f"| Total Entities | {total_s1} | {total_s2} | {missing} |")
    lines.append(f"| Match Rate | - | - | {match_rate:.1f}% |")
    lines.append("")
    
    # Group statistics
    all_groups = set(list(s1_counts.keys()) + list(s2_counts.keys()))
    matching_groups = sum(1 for gid in all_groups if comparison["groups_match"].get(gid, False))
    mismatching_groups = len(all_groups) - matching_groups
    
    lines.append("## Group Statistics")
    lines.append("")
    lines.append(f"- **Total Groups**: {len(all_groups)}")
    lines.append(f"- **Matching Groups**: {matching_groups} ({matching_groups/len(all_groups)*100:.1f}%)")
    lines.append(f"- **Mismatching Groups**: {mismatching_groups} ({mismatching_groups/len(all_groups)*100:.1f}%)")
    lines.append("")
    
    # Mismatching groups (sorted by missing count, descending)
    mismatching = [
        (gid, s1_counts.get(gid, 0), s2_counts.get(gid, 0))
        for gid in all_groups
        if not comparison["groups_match"].get(gid, False)
    ]
    mismatching.sort(key=lambda x: (x[1] - x[2]), reverse=True)
    
    if mismatching:
        lines.append("## Mismatching Groups (Top 30)")
        lines.append("")
        lines.append("| Group ID | S1 Entities | S2 Entities | Difference | Missing Rate |")
        lines.append("|----------|-------------|-------------|------------|--------------|")
        
        for gid, s1_cnt, s2_cnt in mismatching[:30]:
            diff = s1_cnt - s2_cnt
            missing_rate = (diff / s1_cnt * 100) if s1_cnt > 0 else 0
            lines.append(f"| {gid} | {s1_cnt} | {s2_cnt} | {diff:+d} | {missing_rate:.1f}% |")
        
        lines.append("")
        
        if len(mismatching) > 30:
            lines.append(f"*... and {len(mismatching) - 30} more mismatching groups*")
            lines.append("")
    
    # Missing entities by group (top 20 groups with most missing)
    missing_by_group = comparison["missing_by_group"]
    if missing_by_group:
        sorted_missing = sorted(
            missing_by_group.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:20]
        
        lines.append("## Missing Entities by Group (Top 20)")
        lines.append("")
        for gid, missing_list in sorted_missing:
            s1_cnt = s1_counts.get(gid, 0)
            s2_cnt = s2_counts.get(gid, 0)
            lines.append(f"### Group: {gid}")
            lines.append("")
            lines.append(f"- **S1 Entities**: {s1_cnt}")
            lines.append(f"- **S2 Entities**: {s2_cnt}")
            lines.append(f"- **Missing**: {len(missing_list)}")
            lines.append("")
            lines.append("**Missing Entities:**")
            for entity in missing_list[:10]:  # Show first 10
                entity_id = entity.get("entity_id", "N/A")
                entity_name = entity.get("entity_name", "N/A")
                lines.append(f"- `{entity_id}`: {entity_name}")
            if len(missing_list) > 10:
                lines.append(f"- ... and {len(missing_list) - 10} more entities")
            lines.append("")
    
    # Extra entities in S2 (should be empty)
    extra_in_s2 = comparison["extra_in_s2"]
    if extra_in_s2:
        lines.append("## ⚠️ Warning: Extra Entities in S2")
        lines.append("")
        lines.append("The following entities appear in S2 but not in S1 (this should not happen):")
        lines.append("")
        for gid, extra_list in extra_in_s2.items():
            lines.append(f"### Group: {gid}")
            for entity in extra_list:
                entity_id = entity.get("entity_id", "N/A")
                entity_name = entity.get("entity_name", "N/A")
                lines.append(f"- `{entity_id}`: {entity_name}")
            lines.append("")
    
    # Card count statistics
    total_cards = sum(s2_card_counts.values())
    avg_cards_per_entity = (total_cards / total_s2) if total_s2 > 0 else 0
    
    lines.append("## Card Generation Statistics")
    lines.append("")
    lines.append(f"- **Total Cards Generated**: {total_cards}")
    lines.append(f"- **Average Cards per Entity**: {avg_cards_per_entity:.2f}")
    lines.append("")
    
    # Card count distribution
    card_counts_per_entity = defaultdict(int)
    for gid in s2_entities:
        entity_list = s2_entities[gid]
        for entity in entity_list:
            # Count cards for this specific entity (would need to scan S2 file again)
            # For now, just show group-level stats
            pass
    
    lines.append("## Test Result")
    lines.append("")
    if missing == 0 and not extra_in_s2:
        lines.append("✅ **TEST PASSED**: All entities from S1 are present in S2, no extra entities found.")
    elif missing > 0:
        lines.append(f"🔴 **TEST FAILED**: {missing} entities missing from S2.")
    if extra_in_s2:
        lines.append("🔴 **TEST FAILED**: Found entities in S2 that don't exist in S1.")
    lines.append("")
    
    return "\n".join(lines)


# =========================
# Main
# =========================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test entity extraction: compare S1 entity_list with S2 entity results"
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Base directory")
    parser.add_argument("--run_tag", type=str, required=True, help="RUN_TAG to test")
    parser.add_argument("--arm", type=str, default="G", help="Arm identifier (default: G)")
    parser.add_argument(
        "--s1_arm",
        type=str,
        default=None,
        help="S1 arm identifier (default: same as --arm)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: <run_tag>_entity_extraction_test.md)",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    run_tag = args.run_tag.strip()
    arm = args.arm.strip().upper()
    s1_arm = (args.s1_arm or arm).strip().upper() if args.s1_arm else arm
    
    # Paths
    run_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    s1_path = run_dir / f"stage1_struct__arm{s1_arm}.jsonl"
    
    # S2 path resolution (try new format first, then legacy)
    s2_path_new = run_dir / f"s2_results__s1arm{s1_arm}__s2arm{arm}.jsonl"
    s2_path_legacy = run_dir / f"s2_results__arm{arm}.jsonl"
    s2_path = s2_path_new if s2_path_new.exists() else s2_path_legacy
    
    output_path = (
        Path(args.output) if args.output
        else run_dir / f"{run_tag}_entity_extraction_test.md"
    )
    
    print(f"[Test] Loading S1 entities from: {s1_path}")
    s1_entities, s1_counts = load_s1_entities(s1_path)
    print(f"[Test] Loaded {sum(s1_counts.values())} entities from {len(s1_counts)} groups")
    
    print(f"[Test] Loading S2 entities from: {s2_path}")
    s2_entities, s2_counts, s2_card_counts = load_s2_entities(s2_path)
    print(f"[Test] Loaded {sum(s2_counts.values())} entities from {len(s2_counts)} groups")
    
    print(f"[Test] Comparing entity counts...")
    comparison = compare_entity_counts(
        s1_entities,
        s1_counts,
        s2_entities,
        s2_counts,
    )
    
    print(f"[Test] Generating report...")
    report = generate_test_report(
        s1_entities,
        s1_counts,
        s2_entities,
        s2_counts,
        s2_card_counts,
        comparison,
        run_tag,
        arm,
    )
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"[Test] Report saved to: {output_path}")
    
    # Print summary to console
    total_s1 = comparison["total_s1_entities"]
    total_s2 = comparison["total_s2_entities"]
    missing = comparison["missing_count"]
    match_rate = (total_s2 / total_s1 * 100) if total_s1 > 0 else 0
    
    print("")
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"S1 Total Entities: {total_s1}")
    print(f"S2 Total Entities: {total_s2}")
    print(f"Missing: {missing}")
    print(f"Match Rate: {match_rate:.1f}%")
    
    mismatching = sum(1 for match in comparison["groups_match"].values() if not match)
    total_groups = len(comparison["groups_match"])
    print(f"Mismatching Groups: {mismatching}/{total_groups}")
    print("")
    
    if missing == 0 and not comparison["extra_in_s2"]:
        print("✅ TEST PASSED")
        sys.exit(0)
    else:
        print("🔴 TEST FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
S1-S2 Alignment Validation Script

Validates alignment between:
1. groups_canonical.csv and S1 group list
2. S1 entity-list and S2 entity list

Usage:
    python 3_Code/src/tools/validation/validate_s1_s2_alignment.py \
        --base_dir . \
        --run_tag FINAL_DISTRIBUTION \
        --arm G \
        [--output <output.md>]
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Add workspace root to path for imports
_SCRIPT_DIR = Path(__file__).resolve().parent
_WORKSPACE_ROOT = _SCRIPT_DIR.parent.parent.parent.parent
sys.path.insert(0, str(_WORKSPACE_ROOT / "3_Code" / "src"))


# =========================
# Data Loading Functions
# =========================

def load_groups_canonical(csv_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load groups from groups_canonical.csv."""
    if not csv_path.exists():
        raise FileNotFoundError(f"groups_canonical.csv not found: {csv_path}")
    
    groups = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            group_id = row.get("group_id", "").strip()
            if not group_id:
                continue
            groups[group_id] = {
                "group_id": group_id,
                "group_key": row.get("group_key", "").strip(),
                "specialty": row.get("specialty", "").strip(),
                "anatomy": row.get("anatomy", "").strip(),
                "modality_or_type": row.get("modality_or_type", "").strip(),
                "category": row.get("category", "").strip(),
            }
    
    return groups


def load_s1_results(s1_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load S1 results from stage1_struct JSONL file."""
    if not s1_path.exists():
        raise FileNotFoundError(f"S1 structure file not found: {s1_path}")
    
    s1_data = {}
    with open(s1_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                group_data = json.loads(line)
                group_id = group_data.get("group_id", "").strip()
                if not group_id:
                    continue
                
                entity_list = group_data.get("entity_list", [])
                if not isinstance(entity_list, list):
                    entity_list = []
                
                # Extract entity information
                entities = []
                for entity in entity_list:
                    if isinstance(entity, dict):
                        entity_id = entity.get("entity_id", "").strip()
                        entity_name = entity.get("entity_name", "").strip()
                        if entity_id:
                            entities.append({
                                "entity_id": entity_id,
                                "entity_name": entity_name,
                            })
                
                s1_data[group_id] = {
                    "group_id": group_id,
                    "group_path": group_data.get("group_path", "").strip(),
                    "entity_list": entities,
                    "entity_count": len(entities),
                }
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse S1 line {line_num}: {e}", file=sys.stderr)
                continue
    
    return s1_data


def load_s2_results(s2_path: Path) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
    """Load S2 results from s2_results JSONL file.
    
    Returns:
        Dict mapping group_id -> Dict mapping entity_id -> entity info
    """
    if not s2_path.exists():
        raise FileNotFoundError(f"S2 results file not found: {s2_path}")
    
    s2_data = defaultdict(lambda: {})
    with open(s2_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
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
                
                s2_data[group_id][entity_id] = {
                    "entity_id": entity_id,
                    "entity_name": entity_name,
                }
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse S2 line {line_num}: {e}", file=sys.stderr)
                continue
    
    return dict(s2_data)


# =========================
# Validation Functions
# =========================

def normalize_entity_name(name: str) -> str:
    """Normalize entity name for comparison (remove markdown formatting, trim)."""
    if not name:
        return ""
    # Remove markdown formatting (bold, italic, etc.)
    name = name.replace("**", "").replace("*", "").replace("__", "").replace("_", "")
    # Remove extra whitespace
    name = " ".join(name.split())
    return name.strip()


def validate_group_alignment(
    canonical_groups: Dict[str, Dict[str, Any]],
    s1_groups: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """Validate alignment between groups_canonical.csv and S1 groups."""
    canonical_group_ids = set(canonical_groups.keys())
    s1_group_ids = set(s1_groups.keys())
    
    missing_in_s1 = canonical_group_ids - s1_group_ids
    extra_in_s1 = s1_group_ids - canonical_group_ids
    matching_groups = canonical_group_ids & s1_group_ids
    
    return {
        "canonical_count": len(canonical_group_ids),
        "s1_count": len(s1_group_ids),
        "matching_count": len(matching_groups),
        "missing_in_s1": sorted(missing_in_s1),
        "extra_in_s1": sorted(extra_in_s1),
        "matching_groups": sorted(matching_groups),
    }


def validate_entity_alignment(
    s1_data: Dict[str, Dict[str, Any]],
    s2_data: Dict[str, Dict[str, List[Dict[str, str]]]]
) -> Dict[str, Any]:
    """Validate alignment between S1 entity-list and S2 entities."""
    group_results = {}
    all_missing_entities = []
    all_extra_entities = []
    all_name_mismatches = []
    
    # Get all groups from both S1 and S2
    all_group_ids = set(s1_data.keys()) | set(s2_data.keys())
    
    for group_id in sorted(all_group_ids):
        s1_entities = s1_data.get(group_id, {}).get("entity_list", [])
        s2_entities_dict = s2_data.get(group_id, {})
        
        # Build sets for comparison
        s1_entity_ids = {e["entity_id"] for e in s1_entities}
        s2_entity_ids = set(s2_entities_dict.keys())
        
        # Build entity name maps
        s1_entity_map = {e["entity_id"]: e["entity_name"] for e in s1_entities}
        s2_entity_map = {eid: einfo["entity_name"] for eid, einfo in s2_entities_dict.items()}
        
        # Find mismatches
        missing_in_s2 = s1_entity_ids - s2_entity_ids
        extra_in_s2 = s2_entity_ids - s1_entity_ids
        matching_entity_ids = s1_entity_ids & s2_entity_ids
        
        # Check name mismatches for matching entity IDs
        name_mismatches = []
        for entity_id in matching_entity_ids:
            s1_name = normalize_entity_name(s1_entity_map.get(entity_id, ""))
            s2_name = normalize_entity_name(s2_entity_map.get(entity_id, ""))
            if s1_name != s2_name:
                name_mismatches.append({
                    "entity_id": entity_id,
                    "s1_name": s1_entity_map.get(entity_id, ""),
                    "s2_name": s2_entity_map.get(entity_id, ""),
                    "normalized_s1": s1_name,
                    "normalized_s2": s2_name,
                })
        
        group_results[group_id] = {
            "s1_entity_count": len(s1_entity_ids),
            "s2_entity_count": len(s2_entity_ids),
            "matching_count": len(matching_entity_ids),
            "missing_in_s2": [
                {"entity_id": eid, "entity_name": s1_entity_map.get(eid, "")}
                for eid in sorted(missing_in_s2)
            ],
            "extra_in_s2": [
                {"entity_id": eid, "entity_name": s2_entity_map.get(eid, "")}
                for eid in sorted(extra_in_s2)
            ],
            "name_mismatches": name_mismatches,
        }
        
        # Accumulate for summary
        all_missing_entities.extend(group_results[group_id]["missing_in_s2"])
        all_extra_entities.extend(group_results[group_id]["extra_in_s2"])
        all_name_mismatches.extend(name_mismatches)
    
    return {
        "group_results": group_results,
        "summary": {
            "total_groups": len(all_group_ids),
            "total_missing_entities": len(all_missing_entities),
            "total_extra_entities": len(all_extra_entities),
            "total_name_mismatches": len(all_name_mismatches),
            "groups_with_issues": sum(
                1 for gr in group_results.values()
                if gr["missing_in_s2"] or gr["extra_in_s2"] or gr["name_mismatches"]
            ),
        },
    }


# =========================
# Report Generation
# =========================

def generate_report(
    group_alignment: Dict[str, Any],
    entity_alignment: Dict[str, Any],
    output_path: Path,
) -> None:
    """Generate markdown report."""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# S1-S2 Alignment Validation Report\n\n")
        f.write(f"Generated: {Path(output_path).stat().st_mtime}\n\n")
        f.write("---\n\n")
        
        # Group-level validation
        f.write("## 1. Group-Level Validation\n\n")
        f.write(f"**groups_canonical.csv groups:** {group_alignment['canonical_count']}\n")
        f.write(f"**S1 groups:** {group_alignment['s1_count']}\n")
        f.write(f"**Matching groups:** {group_alignment['matching_count']}\n\n")
        
        if group_alignment["missing_in_s1"]:
            f.write(f"### ⚠️ Groups in canonical but missing in S1 ({len(group_alignment['missing_in_s1'])})\n\n")
            for group_id in group_alignment["missing_in_s1"]:
                f.write(f"- `{group_id}`\n")
            f.write("\n")
        
        if group_alignment["extra_in_s1"]:
            f.write(f"### ⚠️ Groups in S1 but not in canonical ({len(group_alignment['extra_in_s1'])})\n\n")
            for group_id in group_alignment["extra_in_s1"]:
                f.write(f"- `{group_id}`\n")
            f.write("\n")
        
        if not group_alignment["missing_in_s1"] and not group_alignment["extra_in_s1"]:
            f.write("### ✅ All groups match\n\n")
        
        # Entity-level validation summary
        f.write("## 2. Entity-Level Validation Summary\n\n")
        summary = entity_alignment["summary"]
        f.write(f"**Total groups checked:** {summary['total_groups']}\n")
        f.write(f"**Groups with issues:** {summary['groups_with_issues']}\n")
        f.write(f"**Total entities missing in S2:** {summary['total_missing_entities']}\n")
        f.write(f"**Total entities extra in S2:** {summary['total_extra_entities']}\n")
        f.write(f"**Total entity name mismatches:** {summary['total_name_mismatches']}\n\n")
        
        # Entity-level validation details
        f.write("## 3. Entity-Level Validation Details\n\n")
        
        # Find groups with issues
        groups_with_issues = [
            (group_id, gr)
            for group_id, gr in entity_alignment["group_results"].items()
            if gr["missing_in_s2"] or gr["extra_in_s2"] or gr["name_mismatches"]
        ]
        
        if not groups_with_issues:
            f.write("### ✅ All entities match between S1 and S2\n\n")
        else:
            f.write(f"### Groups with Entity Issues ({len(groups_with_issues)})\n\n")
            for group_id, gr in sorted(groups_with_issues):
                f.write(f"#### Group: `{group_id}`\n\n")
                f.write(f"- S1 entities: {gr['s1_entity_count']}\n")
                f.write(f"- S2 entities: {gr['s2_entity_count']}\n")
                f.write(f"- Matching entities: {gr['matching_count']}\n\n")
                
                if gr["missing_in_s2"]:
                    f.write(f"**Missing in S2 ({len(gr['missing_in_s2'])}):**\n\n")
                    for entity in gr["missing_in_s2"]:
                        f.write(f"- `{entity['entity_id']}`: {entity['entity_name']}\n")
                    f.write("\n")
                
                if gr["extra_in_s2"]:
                    f.write(f"**Extra in S2 ({len(gr['extra_in_s2'])}):**\n\n")
                    for entity in gr["extra_in_s2"]:
                        f.write(f"- `{entity['entity_id']}`: {entity['entity_name']}\n")
                    f.write("\n")
                
                if gr["name_mismatches"]:
                    f.write(f"**Name Mismatches ({len(gr['name_mismatches'])}):**\n\n")
                    for mm in gr["name_mismatches"]:
                        f.write(f"- `{mm['entity_id']}`:\n")
                        f.write(f"  - S1: `{mm['s1_name']}`\n")
                        f.write(f"  - S2: `{mm['s2_name']}`\n")
                    f.write("\n")
                
                f.write("---\n\n")
        
        # Statistics
        f.write("## 4. Statistics\n\n")
        f.write("### Entity Count Distribution\n\n")
        
        # Count entities per group
        entity_counts = [
            (group_id, gr["s1_entity_count"], gr["s2_entity_count"])
            for group_id, gr in entity_alignment["group_results"].items()
        ]
        
        if entity_counts:
            f.write("| Group ID | S1 Entities | S2 Entities | Match |\n")
            f.write("|----------|-------------|-------------|-------|\n")
            for group_id, s1_count, s2_count in sorted(entity_counts):
                match_status = "✅" if s1_count == s2_count else "❌"
                f.write(f"| `{group_id}` | {s1_count} | {s2_count} | {match_status} |\n")
            f.write("\n")


# =========================
# Main
# =========================

def main():
    parser = argparse.ArgumentParser(
        description="Validate S1-S2 alignment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--base_dir",
        type=str,
        default=".",
        help="Project base directory (default: current directory)",
    )
    parser.add_argument(
        "--run_tag",
        type=str,
        required=True,
        help="Run tag (e.g., FINAL_DISTRIBUTION)",
    )
    parser.add_argument(
        "--arm",
        type=str,
        required=True,
        help="Arm identifier (e.g., G)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output report path (default: <run_tag>_validation_report.md in generated directory)",
    )
    parser.add_argument(
        "--groups_csv",
        type=str,
        default="2_Data/metadata/groups_canonical.csv",
        help="Path to groups_canonical.csv (relative to base_dir)",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        print(f"❌ Base directory does not exist: {base_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Setup paths
    groups_csv_path = base_dir / args.groups_csv
    generated_dir = base_dir / "2_Data" / "metadata" / "generated" / args.run_tag
    s1_path = generated_dir / f"stage1_struct__arm{args.arm}.jsonl"
    s2_path = generated_dir / f"s2_results__s1arm{args.arm}__s2arm{args.arm}.jsonl"
    
    # Determine output path
    if args.output:
        output_path = Path(args.output).resolve()
    else:
        output_path = generated_dir / f"s1_s2_alignment_validation_report__arm{args.arm}.md"
    
    print(f"Loading groups_canonical.csv from: {groups_csv_path}")
    canonical_groups = load_groups_canonical(groups_csv_path)
    print(f"  Loaded {len(canonical_groups)} groups")
    
    print(f"Loading S1 results from: {s1_path}")
    s1_data = load_s1_results(s1_path)
    print(f"  Loaded {len(s1_data)} groups")
    
    print(f"Loading S2 results from: {s2_path}")
    s2_data = load_s2_results(s2_path)
    print(f"  Loaded {len(s2_data)} groups")
    
    print("\nValidating group alignment...")
    group_alignment = validate_group_alignment(canonical_groups, s1_data)
    
    print("Validating entity alignment...")
    entity_alignment = validate_entity_alignment(s1_data, s2_data)
    
    print(f"\nGenerating report: {output_path}")
    generate_report(group_alignment, entity_alignment, output_path)
    
    print("\n✅ Validation complete!")
    print(f"\nSummary:")
    print(f"  Groups: {group_alignment['matching_count']}/{group_alignment['canonical_count']} match")
    print(f"  Entity issues: {entity_alignment['summary']['groups_with_issues']} groups with issues")
    print(f"  Missing entities: {entity_alignment['summary']['total_missing_entities']}")
    print(f"  Extra entities: {entity_alignment['summary']['total_extra_entities']}")
    print(f"  Name mismatches: {entity_alignment['summary']['total_name_mismatches']}")
    print(f"\nReport saved to: {output_path}")


if __name__ == "__main__":
    main()


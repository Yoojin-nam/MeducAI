#!/usr/bin/env python3
"""
FINAL Allocation Analysis Script

Analyze current card generation vs. weight-based 6000 card allocation
to identify reduction requirements at specialty/group/entity levels.

Usage:
    python 3_Code/src/tools/allocation/analyze_final_allocation.py \
        --base_dir . \
        --run_tag <RUN_TAG> \
        --arm <ARM> \
        [--total_cards 6000] \
        [--output <output.md>]
"""

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add workspace root to path for imports
_SCRIPT_DIR = Path(__file__).resolve().parent
_WORKSPACE_ROOT = _SCRIPT_DIR.parent.parent.parent.parent
sys.path.insert(0, str(_WORKSPACE_ROOT / "3_Code" / "archived"))

# Import allocation algorithm from archived code
try:
    from allocation_module import AllocationParams, allocate_cards_by_weight, transform_weight
except ImportError:
    # Fallback: define minimal version if archived module not available
    WeightTransform = str
    AllocationParams = None
    allocate_cards_by_weight = None
    transform_weight = None


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
                "group_weight_sum": float(row.get("group_weight_sum", 0) or 0),
            }
    
    return groups


def load_s1_entity_counts(s1_path: Path) -> Dict[str, int]:
    """Count entities per group from S1 results."""
    if not s1_path.exists():
        raise FileNotFoundError(f"S1 structure file not found: {s1_path}")
    
    entity_counts = {}
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                group_data = json.loads(line)
                group_id = group_data.get("group_id", "").strip()
                if not group_id:
                    continue
                
                entity_list = group_data.get("entity_list", [])
                entity_counts[group_id] = len(entity_list) if isinstance(entity_list, list) else 0
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Failed to parse S1 line: {e}", file=sys.stderr)
                continue
    
    return entity_counts


def load_s2_card_counts(s2_path: Path) -> Tuple[Dict[str, int], Dict[str, List[Dict[str, str]]]]:
    """Count current cards per group from S2 results, and list entities per group."""
    if not s2_path.exists():
        raise FileNotFoundError(f"S2 results file not found: {s2_path}")
    
    card_counts = defaultdict(int)
    entities_per_group = defaultdict(list)
    
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
                
                if not group_id:
                    continue
                
                anki_cards = s2_record.get("anki_cards", [])
                card_count = len(anki_cards) if isinstance(anki_cards, list) else 0
                card_counts[group_id] += card_count
                
                # Track entities (deduplicate by entity_id)
                if entity_id:
                    existing_ids = {e["entity_id"] for e in entities_per_group[group_id]}
                    if entity_id not in existing_ids:
                        entities_per_group[group_id].append({
                            "entity_id": entity_id,
                            "entity_name": entity_name,
                        })
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Failed to parse S2 line: {e}", file=sys.stderr)
                continue
    
    return dict(card_counts), dict(entities_per_group)


# =========================
# Allocation Algorithm (Fallback if archived module not available)
# =========================

def _transform_weight_fallback(w: float, method: str = "LOG1P") -> float:
    """Transform weights (fallback implementation)."""
    if w is None or not math.isfinite(w) or w <= 0:
        return 0.0
    if method == "NONE":
        return float(w)
    if method == "LOG1P":
        return math.log1p(float(w))
    if method == "SQRT":
        return math.sqrt(float(w))
    return float(w)


def _allocate_cards_by_weight_fallback(
    group_weights: Dict[str, float],
    total_cards: int,
    min_cards_per_group: int = 1,
    max_cards_per_group: int = 999999,
    weight_transform: str = "LOG1P",
) -> Dict[str, int]:
    """
    Fallback allocation algorithm if archived module is not available.
    Simplified version of Hamilton method with caps.
    """
    group_ids = sorted(group_weights.keys())
    
    # Transform weights
    tw = {gid: _transform_weight_fallback(group_weights.get(gid, 0.0), weight_transform) for gid in group_ids}
    
    # Start with minimum allocation
    alloc = {gid: min_cards_per_group for gid in group_ids}
    remaining = total_cards - sum(alloc.values())
    
    if remaining <= 0:
        return alloc
    
    # Calculate proportional allocation
    total_weight = sum(tw.values())
    if total_weight > 0:
        ideal = {gid: (remaining * tw[gid] / total_weight) for gid in group_ids}
    else:
        ideal = {gid: (remaining / len(group_ids)) for gid in group_ids}
    
    # Floor allocation
    floor_alloc = {gid: int(math.floor(ideal[gid])) for gid in group_ids}
    for gid in group_ids:
        floor_alloc[gid] = max(0, min(floor_alloc[gid], max_cards_per_group - alloc[gid]))
    
    # Apply floors
    for gid in group_ids:
        alloc[gid] += floor_alloc[gid]
        remaining -= floor_alloc[gid]
    
    # Largest remainder for leftover
    if remaining > 0:
        remainders = [
            (ideal[gid] - math.floor(ideal[gid]), tw[gid], gid)
            for gid in group_ids
            if alloc[gid] < max_cards_per_group
        ]
        remainders.sort(key=lambda x: (-x[0], -x[1], x[2]))
        
        for i in range(min(remaining, len(remainders))):
            _, _, gid = remainders[i]
            if alloc[gid] < max_cards_per_group:
                alloc[gid] += 1
                remaining -= 1
    
    # If still remaining (due to caps), distribute deterministically
    if remaining > 0:
        for gid in group_ids:
            if remaining <= 0:
                break
            if alloc[gid] < max_cards_per_group:
                alloc[gid] += 1
                remaining -= 1
    
    return alloc


# =========================
# Analysis Functions
# =========================

def calculate_weight_allocation(
    groups: Dict[str, Dict[str, Any]],
    total_cards: int = 6000,
    min_cards_per_group: int = 1,
    max_cards_per_group: int = 999999,
) -> Dict[str, int]:
    """Calculate weight-based allocation for target total cards."""
    # Extract weights
    group_weights = {gid: data["group_weight_sum"] for gid, data in groups.items()}
    
    # Use archived module if available, otherwise use fallback
    if allocate_cards_by_weight is not None and AllocationParams is not None:
        params = AllocationParams(
            total_cards=total_cards,
            min_cards_per_group=min_cards_per_group,
            max_cards_per_group=max_cards_per_group,
            weight_transform="LOG1P",
            rounding="HAMILTON",
        )
        return allocate_cards_by_weight(group_weights, params)
    else:
        return _allocate_cards_by_weight_fallback(
            group_weights,
            total_cards,
            min_cards_per_group,
            max_cards_per_group,
            "LOG1P",
        )


def calculate_reductions(
    groups: Dict[str, Dict[str, Any]],
    group_targets: Dict[str, int],
    group_current_cards: Dict[str, int],
    group_entity_counts: Dict[str, int],
    entities_per_group: Dict[str, List[Dict[str, str]]],
) -> Dict[str, Any]:
    """
    Calculate reduction requirements at specialty/group/entity levels.
    
    Returns:
        {
            "specialty_summary": Dict[specialty, {target, current, over, reduction_needed}],
            "group_details": Dict[group_id, {target, current, over, entities_to_reduce, entity_list}],
        }
    """
    # Aggregate by specialty
    specialty_target = defaultdict(int)
    specialty_current = defaultdict(int)
    
    for group_id, target in group_targets.items():
        specialty = groups.get(group_id, {}).get("specialty", "Unknown")
        specialty_target[specialty] += target
        specialty_current[specialty] += group_current_cards.get(group_id, 0)
    
    # Calculate specialty over-generation
    specialty_summary = {}
    for specialty in set(list(specialty_target.keys()) + list(specialty_current.keys())):
        target = specialty_target[specialty]
        current = specialty_current[specialty]
        over = current - target
        specialty_summary[specialty] = {
            "target": target,
            "current": current,
            "over": over,
            "reduction_needed": max(0, over),
        }
    
    # Calculate group-level reductions
    group_details = {}
    for group_id in set(list(group_targets.keys()) + list(group_current_cards.keys())):
        target = group_targets.get(group_id, 0)
        current = group_current_cards.get(group_id, 0)
        over = current - target
        
        # Use actual entity count from S2 results (entities_per_group), not S1
        entity_list = entities_per_group.get(group_id, [])
        entity_count_s2 = len(entity_list)  # Use actual S2 entity count
        entity_count_s1 = group_entity_counts.get(group_id, 0)  # S1 entity count for comparison
        
        # Warn if S1 and S2 entity counts don't match (data issue)
        entity_count_mismatch = entity_count_s1 > 0 and entity_count_s2 != entity_count_s1
        
        # Calculate how many entities should be reduced from 2 cards to 1 card
        # Each entity reduction saves 1 card (removing Q2, keeping Q1)
        entities_to_reduce = max(0, over) if over > 0 else 0
        # But cannot reduce more than available entities (each entity has at least 1 card)
        entities_to_reduce = min(entities_to_reduce, entity_count_s2)
        
        group_details[group_id] = {
            "target": target,
            "current": current,
            "over": over,
            "entity_count": entity_count_s2,  # Use S2 count (actual generated entities)
            "entity_count_s1": entity_count_s1,  # S1 count for reference
            "entity_count_mismatch": entity_count_mismatch,  # Flag if S1 != S2
            "entities_to_reduce": entities_to_reduce,
            "entity_list": entity_list,
            "specialty": groups.get(group_id, {}).get("specialty", "Unknown"),
        }
    
    return {
        "specialty_summary": specialty_summary,
        "group_details": group_details,
    }


# =========================
# Report Generation
# =========================

def generate_report(
    groups: Dict[str, Dict[str, Any]],
    group_targets: Dict[str, int],
    group_current_cards: Dict[str, int],
    group_entity_counts: Dict[str, int],
    reduction_data: Dict[str, Any],
    total_cards: int,
    run_tag: str,
    arm: str,
) -> str:
    """Generate Markdown report."""
    lines = []
    lines.append("# FINAL Allocation Analysis Report")
    lines.append("")
    lines.append(f"**RUN_TAG**: `{run_tag}`")
    lines.append(f"**ARM**: `{arm}`")
    lines.append(f"**Target Total Cards**: {total_cards}")
    lines.append("")
    
    # Overall summary
    total_current = sum(group_current_cards.values())
    total_target = sum(group_targets.values())
    total_over = total_current - total_target
    
    lines.append("## Overall Summary")
    lines.append("")
    lines.append(f"- **Current Cards**: {total_current}")
    lines.append(f"- **Target Cards**: {total_target}")
    lines.append(f"- **Over-generation**: {total_over}")
    lines.append(f"- **Reduction Needed**: {max(0, total_over)}")
    lines.append("")
    
    # Specialty summary
    lines.append("## Specialty Summary")
    lines.append("")
    lines.append("| Specialty | Target | Current | Over | Reduction Needed |")
    lines.append("|-----------|--------|---------|------|------------------|")
    
    specialty_summary = reduction_data["specialty_summary"]
    for specialty in sorted(specialty_summary.keys()):
        data = specialty_summary[specialty]
        lines.append(
            f"| {specialty} | {data['target']} | {data['current']} | {data['over']} | {data['reduction_needed']} |"
        )
    lines.append("")
    
    # Group details (sorted by over-generation, descending)
    lines.append("## Group Details (Over-allocated Groups)")
    lines.append("")
    
    group_details = reduction_data["group_details"]
    over_allocated_groups = [
        (gid, data) for gid, data in group_details.items() if data["over"] > 0
    ]
    over_allocated_groups.sort(key=lambda x: x[1]["over"], reverse=True)
    
    if over_allocated_groups:
        lines.append("| Group ID | Specialty | Target | Current | Over | Entity Count (S2) | S1/S2 Mismatch | Entities to Reduce |")
        lines.append("|----------|-----------|--------|---------|------|------------------|---------------|-------------------|")
        
        for group_id, data in over_allocated_groups:
            mismatch_flag = "⚠️" if data.get("entity_count_mismatch", False) else ""
            s1_count = data.get("entity_count_s1", 0)
            s2_count = data["entity_count"]
            if data.get("entity_count_mismatch", False):
                entity_count_str = f"{s2_count} (S1:{s1_count})"
            else:
                entity_count_str = str(s2_count)
            lines.append(
                f"| {group_id} | {data['specialty']} | {data['target']} | {data['current']} | "
                f"{data['over']} | {entity_count_str} | {mismatch_flag} | {data['entities_to_reduce']} |"
            )
        lines.append("")
        
        # Warning section for mismatches
        mismatched = [gid for gid, data in over_allocated_groups if data.get("entity_count_mismatch", False)]
        if mismatched:
            lines.append("⚠️ **Warning**: The following groups have S1/S2 entity count mismatches (S2 generated more entities than S1 listed):")
            for gid in mismatched[:10]:  # Show first 10
                data = group_details[gid]
                lines.append(f"- `{gid}`: S1={data.get('entity_count_s1', 0)}, S2={data['entity_count']}")
            if len(mismatched) > 10:
                lines.append(f"- ... and {len(mismatched) - 10} more groups")
            lines.append("")
        
        # Entity-level details for over-allocated groups
        lines.append("## Entity Reduction Plan")
        lines.append("")
        lines.append("For each over-allocated group, the following entities should change from 2 cards (Q1+Q2) to 1 card (Q1 only):")
        lines.append("")
        
        for group_id, data in over_allocated_groups[:20]:  # Limit to top 20 for readability
            if data["entities_to_reduce"] > 0:
                lines.append(f"### Group: {group_id} ({data['specialty']})")
                lines.append("")
                lines.append(f"- **Reduction needed**: {data['over']} cards")
                lines.append(f"- **Entities to reduce**: {data['entities_to_reduce']} entities (from {data['entity_count']} total)")
                lines.append("")
                
                # Show entity list (first N entities that should be reduced)
                entity_list = data["entity_list"][:data["entities_to_reduce"]]
                if entity_list:
                    lines.append("**Entities to reduce (keep Q1 only, remove Q2):**")
                    for i, entity in enumerate(entity_list, 1):
                        entity_name = entity.get("entity_name", entity.get("entity_id", "Unknown"))
                        lines.append(f"{i}. `{entity.get('entity_id', 'N/A')}`: {entity_name}")
                lines.append("")
    else:
        lines.append("No over-allocated groups found.")
        lines.append("")
    
    # All groups summary (for reference)
    lines.append("## All Groups Summary")
    lines.append("")
    lines.append("| Group ID | Specialty | Target | Current | Over | Entity Count |")
    lines.append("|----------|-----------|--------|---------|------|--------------|")
    
    all_groups = sorted(group_details.items(), key=lambda x: x[1]["over"], reverse=True)
    for group_id, data in all_groups:
        lines.append(
            f"| {group_id} | {data['specialty']} | {data['target']} | {data['current']} | "
            f"{data['over']} | {data['entity_count']} |"
        )
    lines.append("")
    
    return "\n".join(lines)


# =========================
# Main
# =========================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze FINAL allocation: current vs. weight-based 6000 card allocation"
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Base directory")
    parser.add_argument("--run_tag", type=str, required=True, help="RUN_TAG to analyze")
    parser.add_argument("--arm", type=str, default="A", help="Arm identifier (default: A)")
    parser.add_argument(
        "--total_cards", type=int, default=6000, help="Target total cards (default: 6000)"
    )
    parser.add_argument(
        "--min_cards_per_group",
        type=int,
        default=1,
        help="Minimum cards per group (default: 1)",
    )
    parser.add_argument(
        "--max_cards_per_group",
        type=int,
        default=999999,
        help="Maximum cards per group (default: 999999, no limit)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: <run_tag>_allocation_analysis.md)",
    )
    parser.add_argument(
        "--s1_arm",
        type=str,
        default=None,
        help="S1 arm identifier (default: same as --arm)",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    run_tag = args.run_tag.strip()
    arm = args.arm.strip().upper()
    s1_arm = (args.s1_arm or arm).strip().upper() if args.s1_arm else arm
    
    # Paths
    groups_canonical_path = base_dir / "2_Data" / "metadata" / "groups_canonical.csv"
    run_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    s1_path = run_dir / f"stage1_struct__arm{s1_arm}.jsonl"
    
    # S2 path resolution (try new format first, then legacy)
    s2_path_new = run_dir / f"s2_results__s1arm{s1_arm}__s2arm{arm}.jsonl"
    s2_path_legacy = run_dir / f"s2_results__arm{arm}.jsonl"
    s2_path = s2_path_new if s2_path_new.exists() else s2_path_legacy
    
    output_path = (
        Path(args.output) if args.output
        else run_dir / f"{run_tag}_allocation_analysis.md"
    )
    
    print(f"[Analysis] Loading groups from: {groups_canonical_path}")
    groups = load_groups_canonical(groups_canonical_path)
    print(f"[Analysis] Loaded {len(groups)} groups")
    
    print(f"[Analysis] Loading S1 entity counts from: {s1_path}")
    entity_counts = load_s1_entity_counts(s1_path)
    print(f"[Analysis] Loaded entity counts for {len(entity_counts)} groups")
    
    print(f"[Analysis] Loading S2 card counts from: {s2_path}")
    card_counts, entities_per_group = load_s2_card_counts(s2_path)
    print(f"[Analysis] Loaded card counts for {len(card_counts)} groups")
    
    print(f"[Analysis] Calculating weight-based allocation for {args.total_cards} cards...")
    group_targets = calculate_weight_allocation(
        groups,
        total_cards=args.total_cards,
        min_cards_per_group=args.min_cards_per_group,
        max_cards_per_group=args.max_cards_per_group,
    )
    print(f"[Analysis] Calculated targets for {len(group_targets)} groups")
    
    print(f"[Analysis] Calculating reduction requirements...")
    reduction_data = calculate_reductions(
        groups,
        group_targets,
        card_counts,
        entity_counts,
        entities_per_group,
    )
    
    print(f"[Analysis] Generating report...")
    report = generate_report(
        groups,
        group_targets,
        card_counts,
        entity_counts,
        reduction_data,
        args.total_cards,
        run_tag,
        arm,
    )
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"[Analysis] Report saved to: {output_path}")
    
    # Print summary to console
    total_current = sum(card_counts.values())
    total_target = sum(group_targets.values())
    total_over = total_current - total_target
    
    print("")
    print("=" * 60)
    print("ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Current Cards: {total_current}")
    print(f"Target Cards: {total_target}")
    print(f"Over-generation: {total_over}")
    print(f"Reduction Needed: {max(0, total_over)}")
    print("")
    print(f"Full report: {output_path}")


if __name__ == "__main__":
    main()


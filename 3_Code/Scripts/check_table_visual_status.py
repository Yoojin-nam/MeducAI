#!/usr/bin/env python3
"""
Check table visual (S1 infographic) generation status for allocated groups.
"""

import json
from pathlib import Path
from collections import defaultdict


def sanitize_filename_component(s: str) -> str:
    """Sanitize a string for use in filename."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        s = s.replace(char, '_')
    return s


def check_table_visual_status(base_dir: Path, allocation_file: Path):
    """Check table visual status for all groups in allocation."""
    
    # Load allocation file
    with open(allocation_file, 'r', encoding='utf-8') as f:
        allocation = json.load(f)
    
    run_tag = allocation.get("run_tag", "FINAL_DISTRIBUTION")
    images_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag / "images"
    
    # Get all unique groups from selected cards
    groups = set()
    group_to_specialty = {}
    
    for card in allocation.get("selected_cards", []):
        group_id = card.get("group_id", "")
        if group_id:
            groups.add(group_id)
    
    # Get specialty for each group
    group_allocation = allocation.get("group_allocation", {})
    for group_id, info in group_allocation.items():
        if isinstance(info, dict):
            group_to_specialty[group_id] = info.get("specialty", "unknown")
    
    # Check table visual for each group
    groups_with_table = []
    groups_without_table = []
    specialty_stats = defaultdict(lambda: {"total": 0, "with_table": 0, "without_table": 0})
    
    for group_id in sorted(groups):
        specialty = group_to_specialty.get(group_id, "unknown")
        specialty_stats[specialty]["total"] += 1
        
        # Check for table visual (both JPG and PNG)
        safe_group_id = sanitize_filename_component(group_id)
        table_jpg = images_dir / f"IMG__{run_tag}__{safe_group_id}__TABLE.jpg"
        table_png = images_dir / f"IMG__{run_tag}__{safe_group_id}__TABLE.png"
        
        has_table = table_jpg.exists() or table_png.exists()
        
        if has_table:
            groups_with_table.append(group_id)
            specialty_stats[specialty]["with_table"] += 1
        else:
            groups_without_table.append({
                "group_id": group_id,
                "specialty": specialty,
            })
            specialty_stats[specialty]["without_table"] += 1
    
    # Print results
    print("=" * 70)
    print("S1 Table Visual (Infographic) Generation Status")
    print("=" * 70)
    print(f"\nAllocation file: {allocation_file}")
    print(f"Run tag: {run_tag}")
    print(f"Images directory: {images_dir}\n")
    
    print("=" * 70)
    print("Overall Statistics")
    print("=" * 70)
    total_groups = len(groups)
    print(f"Total groups in allocation: {total_groups:,}")
    print(f"  ✓ With table visual: {len(groups_with_table):,} ({len(groups_with_table)/total_groups*100:.1f}%)")
    print(f"  ✗ Without table visual: {len(groups_without_table):,} ({len(groups_without_table)/total_groups*100:.1f}%)")
    
    # Specialty breakdown
    print("\n" + "=" * 70)
    print("Specialty Breakdown")
    print("=" * 70)
    print(f"{'Specialty':<30} {'Total':>8} {'With Table':>12} {'Without':>10} {'%':>6}")
    print("-" * 70)
    
    for specialty in sorted(specialty_stats.keys()):
        s = specialty_stats[specialty]
        total = s["total"]
        with_table = s["with_table"]
        without_table = s["without_table"]
        pct = (with_table / total * 100) if total > 0 else 0
        print(f"{specialty:<30} {total:>8,} {with_table:>12,} {without_table:>10,} {pct:>5.1f}%")
    
    # Sample of groups without table visual
    if groups_without_table:
        print("\n" + "=" * 70)
        print(f"Groups Without Table Visual: {len(groups_without_table):,}")
        print("=" * 70)
        
        # Group by specialty
        by_specialty = defaultdict(list)
        for group in groups_without_table:
            by_specialty[group["specialty"]].append(group["group_id"])
        
        print("\nBreakdown by Specialty:")
        for specialty in sorted(by_specialty.keys()):
            group_list = by_specialty[specialty]
            print(f"  {specialty}: {len(group_list):,} groups")
        
        # Sample (first 20 groups)
        print("\nSample of groups without table visual (first 20):")
        for i, group in enumerate(groups_without_table[:20], 1):
            print(f"  {i}. {group['group_id']} ({group['specialty']})")
    
    print("\n" + "=" * 70)
    print("Check completed!")
    print("=" * 70)


if __name__ == "__main__":
    import sys
    
    base_dir = Path(__file__).parent.parent.parent
    if len(sys.argv) > 1:
        base_dir = Path(sys.argv[1])
    
    allocation_file = (
        base_dir / "2_Data" / "metadata" / "generated" / "FINAL_DISTRIBUTION" /
        "allocation" / "final_distribution_allocation__6000cards.json"
    )
    
    if not allocation_file.exists():
        print(f"Error: Allocation file not found: {allocation_file}")
        sys.exit(1)
    
    check_table_visual_status(base_dir, allocation_file)


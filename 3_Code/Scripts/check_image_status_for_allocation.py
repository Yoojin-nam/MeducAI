#!/usr/bin/env python3
"""
Check image generation status for allocated cards.

This script reads the allocation JSON file and checks which cards have
corresponding image files generated.
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple


def sanitize_filename_component(s: str) -> str:
    """Sanitize a string for use in filename (replace invalid chars with underscore)."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        s = s.replace(char, '_')
    return s


def get_image_paths(
    base_dir: Path,
    run_tag: str,
    group_id: str,
    entity_id: str,
    card_role: str,
) -> List[Path]:
    """Get the expected image file paths for a card (check both JPG and PNG, and Q1 for Q2)."""
    images_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag / "images"
    
    # Sanitize components
    safe_group_id = sanitize_filename_component(group_id)
    safe_entity_id = sanitize_filename_component(entity_id)
    safe_card_role = sanitize_filename_component(card_role)
    
    # Check both the card's own image and Q1 image (Q2 may use Q1 image)
    paths = []
    
    # Check card's own image (both JPG and PNG)
    for ext in [".jpg", ".png"]:
        filename = f"IMG__{run_tag}__{safe_group_id}__{safe_entity_id}__{safe_card_role}{ext}"
        paths.append(images_dir / filename)
    
    # For Q2, also check Q1 image (Q2 may reuse Q1 image)
    if card_role == "Q2":
        for ext in [".jpg", ".png"]:
            filename = f"IMG__{run_tag}__{safe_group_id}__{safe_entity_id}__Q1{ext}"
            paths.append(images_dir / filename)
    
    return paths


def check_image_status(
    base_dir: Path,
    allocation_file: Path,
) -> Tuple[Dict[str, int], Dict[str, List[Dict]]]:
    """Check image status for all allocated cards."""
    
    # Load allocation file
    with open(allocation_file, 'r', encoding='utf-8') as f:
        allocation = json.load(f)
    
    run_tag = allocation.get("run_tag", "FINAL_DISTRIBUTION")
    selected_cards = allocation.get("selected_cards", [])
    
    # Statistics
    stats = {
        "total": len(selected_cards),
        "with_image": 0,
        "without_image": 0,
        "q1_with_image": 0,
        "q1_without_image": 0,
        "q2_with_image": 0,
        "q2_without_image": 0,
    }
    
    # Specialty breakdown
    specialty_stats = defaultdict(lambda: {
        "total": 0,
        "with_image": 0,
        "without_image": 0,
    })
    
    # Cards without images (for reporting)
    cards_without_image = []
    
    # Get specialty for each group
    group_allocation = allocation.get("group_allocation", {})
    group_to_specialty = {}
    for group_id, info in group_allocation.items():
        if isinstance(info, dict):
            group_to_specialty[group_id] = info.get("specialty", "unknown")
    
    # Check each card
    for card in selected_cards:
        group_id = card.get("group_id", "")
        entity_id = card.get("entity_id", "")
        card_role = card.get("card_role", "")
        
        # Get specialty
        specialty = group_to_specialty.get(group_id, "unknown")
        specialty_stats[specialty]["total"] += 1
        
        # Check image file (try multiple paths: JPG, PNG, and Q1 for Q2)
        image_paths = get_image_paths(base_dir, run_tag, group_id, entity_id, card_role)
        existing_path = next((p for p in image_paths if p.exists()), None)
        has_image = existing_path is not None
        
        if has_image:
            stats["with_image"] += 1
            specialty_stats[specialty]["with_image"] += 1
            
            if card_role == "Q1":
                stats["q1_with_image"] += 1
            elif card_role == "Q2":
                stats["q2_with_image"] += 1
        else:
            stats["without_image"] += 1
            specialty_stats[specialty]["without_image"] += 1
            
            if card_role == "Q1":
                stats["q1_without_image"] += 1
            elif card_role == "Q2":
                stats["q2_without_image"] += 1
            
            # Record card without image
            cards_without_image.append({
                "group_id": group_id,
                "entity_id": entity_id,
                "entity_name": card.get("entity_name", ""),
                "card_role": card_role,
                "card_id": card.get("card_id", ""),
                "specialty": specialty,
                "expected_image_paths": [str(p) for p in image_paths],
            })
    
    return stats, dict(specialty_stats), cards_without_image


def main():
    import sys
    
    # Calculate base_dir: Script is at 3_Code/Scripts/, so go up 2 levels
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
    
    print("=" * 70)
    print("Image Generation Status Check for Allocated Cards")
    print("=" * 70)
    print(f"\nAllocation file: {allocation_file}")
    print(f"Base directory: {base_dir}\n")
    
    stats, specialty_stats, cards_without_image = check_image_status(
        base_dir, allocation_file
    )
    
    # Overall statistics
    print("=" * 70)
    print("Overall Statistics")
    print("=" * 70)
    print(f"Total allocated cards: {stats['total']:,}")
    print(f"  ✓ With image: {stats['with_image']:,} ({stats['with_image']/stats['total']*100:.1f}%)")
    print(f"  ✗ Without image: {stats['without_image']:,} ({stats['without_image']/stats['total']*100:.1f}%)")
    print()
    print("By Card Role:")
    print(f"  Q1 cards:")
    print(f"    ✓ With image: {stats['q1_with_image']:,}")
    print(f"    ✗ Without image: {stats['q1_without_image']:,}")
    print(f"  Q2 cards:")
    print(f"    ✓ With image: {stats['q2_with_image']:,}")
    print(f"    ✗ Without image: {stats['q2_without_image']:,}")
    
    # Specialty breakdown
    print("\n" + "=" * 70)
    print("Specialty Breakdown")
    print("=" * 70)
    print(f"{'Specialty':<30} {'Total':>8} {'With Image':>12} {'Without':>10} {'%':>6}")
    print("-" * 70)
    
    for specialty in sorted(specialty_stats.keys()):
        s = specialty_stats[specialty]
        total = s["total"]
        with_img = s["with_image"]
        without_img = s["without_image"]
        pct = (with_img / total * 100) if total > 0 else 0
        print(f"{specialty:<30} {total:>8,} {with_img:>12,} {without_img:>10,} {pct:>5.1f}%")
    
    # Summary of cards without images
    if cards_without_image:
        print("\n" + "=" * 70)
        print(f"Cards Without Images: {len(cards_without_image):,}")
        print("=" * 70)
        
        # Group by specialty
        by_specialty = defaultdict(list)
        for card in cards_without_image:
            by_specialty[card["specialty"]].append(card)
        
        print("\nBreakdown by Specialty:")
        for specialty in sorted(by_specialty.keys()):
            cards = by_specialty[specialty]
            q1_count = sum(1 for c in cards if c["card_role"] == "Q1")
            q2_count = sum(1 for c in cards if c["card_role"] == "Q2")
            print(f"  {specialty}: {len(cards):,} cards (Q1: {q1_count}, Q2: {q2_count})")
        
        # Sample of cards without images (first 10)
        print("\nSample of cards without images (first 10):")
        for i, card in enumerate(cards_without_image[:10], 1):
            print(f"  {i}. {card['card_id']} ({card['specialty']}, {card['card_role']})")
            print(f"     Entity: {card['entity_name']}")
            print(f"     Expected paths: {', '.join(card['expected_image_paths'][:2])}...")
    
    print("\n" + "=" * 70)
    print("Check completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()


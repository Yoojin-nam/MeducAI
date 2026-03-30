#!/usr/bin/env python3
"""
Backfill regeneration_trigger_score fields to existing S5 validation files.

This script adds the following score fields to each card in s2_cards_validation.cards[]:
- regeneration_trigger_score: Combined card + image score (0-100, lower = regenerate)
- card_regeneration_trigger_score: Card-only score (0-100)
- image_regeneration_trigger_score: Image-only score (0-100), None if no image

Usage:
    python backfill_regeneration_scores.py <s5_validation_file.jsonl> [--dry-run] [--output <output_file.jsonl>]
    
Options:
    --dry-run       Print statistics without modifying files
    --output FILE   Write to a separate file instead of in-place update
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.multi_agent.score_calculator import (
    calculate_s5_regeneration_trigger_score,
    calculate_s5_card_regeneration_trigger_score,
    calculate_s5_image_regeneration_trigger_score,
    calculate_s1_table_regeneration_trigger_score,
)


def map_card_to_score_input(card: Dict[str, Any]) -> Dict[str, Any]:
    """Map S5 card record fields to the s5_-prefixed format expected by score_calculator.
    
    The S5 validation file uses non-prefixed field names:
    - technical_accuracy, educational_quality, blocking_error
    - card_image_validation.{blocking_error, safety_flag, image_quality, anatomical_accuracy, prompt_compliance}
    
    The score calculator expects s5_-prefixed field names.
    """
    img_val = card.get("card_image_validation") or {}
    
    return {
        "s5_blocking_error": card.get("blocking_error"),
        "s5_technical_accuracy": card.get("technical_accuracy"),
        "s5_educational_quality": card.get("educational_quality"),
        "s5_card_image_blocking_error": img_val.get("blocking_error"),
        "s5_card_image_safety_flag": img_val.get("safety_flag"),
        "s5_card_image_quality": img_val.get("image_quality"),
        "s5_card_image_anatomical_accuracy": img_val.get("anatomical_accuracy"),
        "s5_card_image_prompt_compliance": img_val.get("prompt_compliance"),
    }


def backfill_s1_score_for_record(record: Dict[str, Any]) -> bool:
    """Add table_regeneration_trigger_score to S1 table validation.
    
    Returns True if S1 score was added, False otherwise.
    """
    s1_table_validation = record.get("s1_table_validation")
    if not s1_table_validation:
        return False
    
    # Check if score already exists
    if "table_regeneration_trigger_score" in s1_table_validation:
        return False
    
    # Calculate trigger score
    try:
        table_trigger_score = calculate_s1_table_regeneration_trigger_score({
            "blocking_error": s1_table_validation.get("blocking_error"),
            "technical_accuracy": s1_table_validation.get("technical_accuracy"),
            "educational_quality": s1_table_validation.get("educational_quality"),
        })
        s1_table_validation["table_regeneration_trigger_score"] = table_trigger_score
        return True
    except Exception as e:
        print(f"Warning: Failed to calculate S1 trigger score: {e}")
        return False


def backfill_scores_for_record(record: Dict[str, Any]) -> tuple[int, int, int]:
    """Add regeneration trigger scores to all cards in a record.
    
    Returns (cards_processed, cards_with_regen_score, cards_with_image_score)
    """
    cards_processed = 0
    cards_with_regen_score = 0
    cards_with_image_score = 0
    
    s2_cards_validation = record.get("s2_cards_validation")
    if not s2_cards_validation:
        return 0, 0, 0
    
    cards = s2_cards_validation.get("cards", [])
    
    for card in cards:
        cards_processed += 1
        
        # Map to score input format
        score_input = map_card_to_score_input(card)
        
        # Calculate and add scores
        regen_score = calculate_s5_regeneration_trigger_score(score_input)
        card["regeneration_trigger_score"] = regen_score
        cards_with_regen_score += 1
        
        card_score = calculate_s5_card_regeneration_trigger_score(score_input)
        card["card_regeneration_trigger_score"] = card_score
        
        image_score = calculate_s5_image_regeneration_trigger_score(score_input)
        if image_score is not None:
            card["image_regeneration_trigger_score"] = image_score
            cards_with_image_score += 1
    
    return cards_processed, cards_with_regen_score, cards_with_image_score


def process_file(
    input_path: Path,
    output_path: Optional[Path] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Process an S5 validation JSONL file and add regeneration scores.
    
    Returns statistics about the processing.
    """
    stats = {
        "records_total": 0,
        "records_with_cards": 0,
        "records_with_s1": 0,
        "s1_scores_added": 0,
        "cards_total": 0,
        "cards_with_regen_score": 0,
        "cards_with_image_score": 0,
        "s1_score_distribution": {
            "0-29": 0,
            "30-49": 0,
            "50-69": 0,
            "70-89": 0,
            "90-100": 0,
        },
        "s2_score_distribution": {
            "0-29": 0,
            "30-49": 0,
            "50-69": 0,
            "70-89": 0,
            "90-100": 0,
        },
    }
    
    records = []
    
    # Read and process records
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            
            record = json.loads(line)
            stats["records_total"] += 1
            
            # Backfill S1 table score
            if record.get("s1_table_validation"):
                stats["records_with_s1"] += 1
                if backfill_s1_score_for_record(record):
                    stats["s1_scores_added"] += 1
                
                # Track S1 score distribution
                s1_val = record.get("s1_table_validation", {})
                s1_score = s1_val.get("table_regeneration_trigger_score")
                if s1_score is not None:
                    if s1_score < 30:
                        stats["s1_score_distribution"]["0-29"] += 1
                    elif s1_score < 50:
                        stats["s1_score_distribution"]["30-49"] += 1
                    elif s1_score < 70:
                        stats["s1_score_distribution"]["50-69"] += 1
                    elif s1_score < 90:
                        stats["s1_score_distribution"]["70-89"] += 1
                    else:
                        stats["s1_score_distribution"]["90-100"] += 1
            
            # Backfill S2 card scores
            cards_processed, cards_with_regen, cards_with_img = backfill_scores_for_record(record)
            
            if cards_processed > 0:
                stats["records_with_cards"] += 1
            
            stats["cards_total"] += cards_processed
            stats["cards_with_regen_score"] += cards_with_regen
            stats["cards_with_image_score"] += cards_with_img
            
            # Track S2 score distribution
            s2cv = record.get("s2_cards_validation", {})
            for card in s2cv.get("cards", []):
                score = card.get("regeneration_trigger_score")
                if score is not None:
                    if score < 30:
                        stats["s2_score_distribution"]["0-29"] += 1
                    elif score < 50:
                        stats["s2_score_distribution"]["30-49"] += 1
                    elif score < 70:
                        stats["s2_score_distribution"]["50-69"] += 1
                    elif score < 90:
                        stats["s2_score_distribution"]["70-89"] += 1
                    else:
                        stats["s2_score_distribution"]["90-100"] += 1
            
            records.append(record)
    
    # Write output
    if not dry_run:
        out_path = output_path or input_path
        with open(out_path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        stats["output_path"] = str(out_path)
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Backfill regeneration_trigger_score to S5 validation files"
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to S5 validation JSONL file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print statistics without modifying files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write to a separate file instead of in-place update",
    )
    
    args = parser.parse_args()
    
    if not args.input_file.exists():
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)
    
    print(f"Processing: {args.input_file}")
    if args.dry_run:
        print("(DRY RUN - no files will be modified)")
    
    stats = process_file(args.input_file, args.output, args.dry_run)
    
    print("\n=== Statistics ===")
    print(f"Records total: {stats['records_total']}")
    print(f"Records with S1 table validation: {stats['records_with_s1']}")
    print(f"  S1 scores added: {stats['s1_scores_added']}")
    print(f"Records with S2 cards: {stats['records_with_cards']}")
    print(f"  Cards total: {stats['cards_total']}")
    print(f"  Cards with regeneration_trigger_score: {stats['cards_with_regen_score']}")
    print(f"  Cards with image_regeneration_trigger_score: {stats['cards_with_image_score']}")
    
    print("\n=== S1 Table Score Distribution ===")
    s1_total = sum(stats["s1_score_distribution"].values())
    if s1_total > 0:
        for bucket, count in stats["s1_score_distribution"].items():
            pct = (count / s1_total * 100) if s1_total > 0 else 0
            bar = "█" * int(pct / 2)
            print(f"  {bucket:>8}: {count:>5} ({pct:5.1f}%) {bar}")
    else:
        print("  No S1 scores found")
    
    print("\n=== S2 Card Score Distribution ===")
    s2_total = sum(stats["s2_score_distribution"].values())
    if s2_total > 0:
        for bucket, count in stats["s2_score_distribution"].items():
            pct = (count / s2_total * 100) if s2_total > 0 else 0
            bar = "█" * int(pct / 2)
            print(f"  {bucket:>8}: {count:>5} ({pct:5.1f}%) {bar}")
    else:
        print("  No S2 scores found")
    
    if not args.dry_run:
        print(f"\nOutput written to: {stats.get('output_path', 'N/A')}")
    
    print("\n✓ Done")


if __name__ == "__main__":
    main()


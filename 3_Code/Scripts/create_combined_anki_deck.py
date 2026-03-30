#!/usr/bin/env python3
"""
Create Combined Anki Deck from S0_QA_final_time

This script creates a unified Anki deck combining all arms (A-F) from S0_QA_final_time.

Usage:
    python3 3_Code/Scripts/create_combined_anki_deck.py \
        --run_tag S0_QA_final_time \
        --output_path 6_Distributions/anki/MeducAI_S0_QA_final_time_ALL_ARMS.apkg
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import genanki
except ImportError:
    print("Error: genanki package is required. Install with: pip install genanki", file=sys.stderr)
    sys.exit(1)

# Import Anki export module
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import importlib.util
anki_module_path = Path(__file__).parent.parent / "src" / "07_export_anki_deck.py"
spec = importlib.util.spec_from_file_location("anki_export", anki_module_path)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Failed to load module spec for: {anki_module_path}")
anki_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(anki_module)


def create_combined_anki_deck(
    base_dir: Path,
    run_tag: str,
    arms: List[str] = ["A", "B", "C", "D", "E", "F"],
    output_path: Optional[Path] = None,
    allow_missing_images: bool = False,
) -> bool:
    """Create a combined Anki deck from all arms."""
    print("=" * 70)
    print("Creating Combined Anki Deck")
    print("=" * 70)
    print(f"Run tag: {run_tag}")
    print(f"Arms: {', '.join(arms)}")
    print("=" * 70)
    
    # Paths
    gen_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    images_dir = gen_dir / "images"
    
    if output_path is None:
        output_path = base_dir / "6_Distributions" / "anki" / f"MeducAI_{run_tag}_ALL_ARMS.apkg"
    else:
        output_path = Path(output_path).resolve()
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load S3 image policy manifests from all arms (authoritative source for image placement)
    all_image_placement_mappings = {}
    for arm in arms:
        policy_manifest_path = gen_dir / f"image_policy_manifest__arm{arm}.jsonl"
        if policy_manifest_path.exists():
            placement_mapping = anki_module.load_image_policy_manifest(policy_manifest_path)
            all_image_placement_mappings.update(placement_mapping)
            if placement_mapping:
                print(f"  Loaded image placement policy for {len(placement_mapping)} cards from arm {arm}")
    
    # Load S2 results and S4 manifests for all arms
    all_s2_records = []
    all_image_mappings = {}
    
    for arm in arms:
        s2_path = gen_dir / f"s2_results__arm{arm}.jsonl"
        s4_manifest_path = gen_dir / f"s4_image_manifest__arm{arm}.jsonl"
        
        if s2_path.exists():
            s2_records = anki_module.load_s2_results(s2_path)
            # Tag records with arm for tracking
            for record in s2_records:
                record["_arm"] = arm
            all_s2_records.extend(s2_records)
            print(f"  Loaded {len(s2_records)} S2 records from arm {arm}")
        else:
            print(f"  ⚠️  S2 results not found for arm {arm}: {s2_path}")
        
        if s4_manifest_path.exists():
            image_mapping = anki_module.load_s4_manifest(s4_manifest_path)
            # Merge into combined mapping
            all_image_mappings.update(image_mapping)
            print(f"  Loaded {len(image_mapping)} image mappings from arm {arm}")
        else:
            print(f"  ⚠️  S4 manifest not found for arm {arm}: {s4_manifest_path}")
    
    if not all_s2_records:
        print("  ❌ No S2 records found")
        return False
    
    print(f"\n  Total: {len(all_s2_records)} S2 records")
    print(f"  Total: {len(all_image_mappings)} image mappings")
    
    # Create combined deck
    deck_id = hash(f"{run_tag}_ALL_ARMS") % (2 ** 31)
    deck_name = f"MeducAI_{run_tag}_ALL_ARMS"
    deck = genanki.Deck(deck_id, deck_name)
    
    # Track statistics
    n_notes = 0
    n_q1 = 0
    n_q2 = 0
    n_q3 = 0
    n_with_images = 0
    q1_failures: List[str] = []
    q3_failures: List[str] = []
    
    # Collect media files (use set to avoid duplicates)
    media_files_set: set[str] = set()
    
    # Process each S2 record
    for s2_record in all_s2_records:
        run_tag_rec = str(s2_record.get("run_tag") or run_tag).strip()
        group_id = str(s2_record.get("group_id") or "").strip()
        entity_id = str(s2_record.get("entity_id") or "").strip()
        entity_name = str(s2_record.get("entity_name") or "").strip()
        group_path = str(s2_record.get("group_path") or "").strip()
        arm = s2_record.get("_arm", "?")
        
        if not (group_id and entity_id):
            continue
        
        # Get cards from anki_cards field (S2 format)
        cards = s2_record.get("anki_cards") or []
        
        # If anki_cards is empty, try stage2 format
        if not cards:
            stage2 = s2_record.get("stage2", {})
            # Current 2-card policy: Q1/Q2 only (Q3 deprecated). Keep backward compatibility:
            # if legacy artifacts contain Q3, include it opportunistically.
            roles = ["Q1", "Q2"]
            if "Q3" in stage2:
                roles.append("Q3")
            for card_role in roles:
                card_data = stage2.get(card_role)
                if card_data:
                    # Convert stage2 format to anki_cards format
                    cards.append({
                        "card_role": card_role,
                        "card_type": card_data.get("card_type", "Basic"),
                        "front": card_data.get("front", ""),
                        "back": card_data.get("back", ""),
                    })
        
        for card in cards:
            if not isinstance(card, dict):
                continue
            
            card_role = card.get("card_role", "").strip()
            
            # Get image_placement from S3 policy manifest (authoritative source)
            placement_key = (run_tag_rec, group_id, entity_id, card_role)
            image_placement = all_image_placement_mappings.get(placement_key)
            
            note, media_filename, error = anki_module.process_card(
                card=card,
                run_tag=run_tag_rec,
                group_id=group_id,
                entity_id=entity_id,
                image_mapping=all_image_mappings,
                images_dir=images_dir,
                allow_missing_images=allow_missing_images,
                image_placement=image_placement,
                group_path=group_path,
            )
            
            if note:
                deck.add_note(note)
                n_notes += 1
                if card_role == "Q1":
                    n_q1 += 1
                elif card_role == "Q2":
                    n_q2 += 1
                elif card_role == "Q3":
                    n_q3 += 1
                if media_filename:
                    # Find actual image file path
                    image_path = anki_module.find_image_by_filename(
                        images_dir=images_dir,
                        filename=media_filename,
                    )
                    if image_path and image_path.exists():
                        # Use absolute path for genanki
                        media_files_set.add(str(image_path.resolve()))
                        n_with_images += 1
                    else:
                        print(f"  ⚠️  Image file not found: {media_filename} (group_id={group_id}, entity_id={entity_id}, images_dir={images_dir})")
            elif error:
                if card_role == "Q1":
                    q1_failures.append(f"{group_id}/{entity_id} (arm {arm})")
                    if not allow_missing_images:
                        print(f"  ⚠️  Q1 card failed: {error}")
                elif card_role == "Q3":
                    q3_failures.append(f"{group_id}/{entity_id} (arm {arm})")
                    print(f"  ⚠️  Q3 card failed: {error}")
    
    # Write deck
    print(f"\n[Export] Writing deck to: {output_path}")
    try:
        media_files_list = list(media_files_set)
        genanki.Package(deck, media_files=media_files_list).write_to_file(str(output_path))
        print(f"[Export] ✅ Deck created successfully")
    except Exception as e:
        print(f"[Export] ❌ Failed to write deck: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Print statistics
    print(f"\n[Export] Statistics:")
    print(f"[Export] Notes: {n_notes} (Q1: {n_q1}, Q2: {n_q2}, Q3: {n_q3})")
    print(f"[Export] With images: {n_with_images}")
    print(f"[Export] Output: {output_path}")
    
    if q1_failures:
        print(f"[Export] ⚠️  Q1 failures: {len(q1_failures)}")
    if q3_failures:
        print(f"[Export] ⚠️  Q3 failures: {len(q3_failures)}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Create combined Anki deck from all arms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--run_tag",
        type=str,
        default="S0_QA_final_time",
        help="Run tag (default: S0_QA_final_time)",
    )
    parser.add_argument(
        "--base_dir",
        type=str,
        default=".",
        help="Base directory (default: current directory)",
    )
    parser.add_argument(
        "--arms",
        type=str,
        nargs="+",
        default=["A", "B", "C", "D", "E", "F"],
        help="Arms to include (default: A B C D E F)",
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default=None,
        help="Output .apkg path (default: 6_Distributions/anki/MeducAI_{run_tag}_ALL_ARMS.apkg)",
    )
    parser.add_argument(
        "--allow_missing_images",
        action="store_true",
        help="Allow missing images (for debugging)",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        raise FileNotFoundError(f"Base directory does not exist: {base_dir}")
    
    run_tag = str(args.run_tag).strip()
    if not run_tag:
        raise ValueError("run_tag cannot be empty")
    
    arms = [str(a).strip().upper() for a in args.arms]
    
    output_path = Path(args.output_path).resolve() if args.output_path else None
    
    success = create_combined_anki_deck(
        base_dir=base_dir,
        run_tag=run_tag,
        arms=arms,
        output_path=output_path,
        allow_missing_images=args.allow_missing_images,
    )
    
    if success:
        print("\n✅ Combined Anki deck created successfully!")
        sys.exit(0)
    else:
        print("\n❌ Failed to create combined Anki deck")
        sys.exit(1)


if __name__ == "__main__":
    main()


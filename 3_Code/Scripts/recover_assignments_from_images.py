#!/usr/bin/env python3
"""
Recover assignment files from images_realistic manifest.

Strategy:
1. Parse images_realistic/manifest.csv to extract group_id + entity_id + card_role (Q1/Q2)
2. Load old assignments to get full metadata
3. Reconstruct specialist assignments (330 cards with images)
4. Reconstruct resident assignments (remaining cards)
5. Reconstruct allocation based on recovered assignments
"""

import pandas as pd
import json
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple

# Paths
WORKSPACE = Path("/path/to/workspace/workspace/MeducAI")
MANIFEST_PATH = WORKSPACE / "2_Data/metadata/generated/FINAL_DISTRIBUTION/images_realistic/manifest.csv"
# Use NEW assignments which has specialist assignments (Jan 6)
NEW_ASSIGNMENTS = WORKSPACE / "BACKUP_BEFORE_REASSIGNMENT_20260106_151624/assignments_NEW_jan6/Assignments.csv"
OUTPUT_DIR = WORKSPACE / "2_Data/metadata/generated/FINAL_DISTRIBUTION"

# Output files
SPECIALIST_CSV = OUTPUT_DIR / "assignments_specialist.csv"
RESIDENT_CSV = OUTPUT_DIR / "assignments_resident.csv"
ALLOCATION_JSON = OUTPUT_DIR / "allocation" / "final_distribution_allocation__6000cards.json"


def parse_image_filename(filename: str) -> Tuple[str, str, str]:
    """
    Extract group_id, entity_id, and card_role from image filename.
    
    Example: IMG__FINAL_DISTRIBUTION__grp_ad44d0b476__DERIVED_8f72b4dc3d3f__Q2_realistic.jpg
    Returns: ('grp_ad44d0b476', 'DERIVED:8f72b4dc3d3f', 'Q2')
    """
    pattern = r'IMG__FINAL_DISTRIBUTION__(?P<group>grp_[a-f0-9]+)__(?P<entity>DERIVED_[a-f0-9]+)__(?P<role>Q[12])_realistic\.jpg'
    match = re.match(pattern, filename)
    if not match:
        return None, None, None
    
    group_id = match.group('group')
    entity_id = match.group('entity').replace('_', ':')  # DERIVED_xxx -> DERIVED:xxx
    card_role = match.group('role')
    
    return group_id, entity_id, card_role


def load_image_cards() -> Set[Tuple[str, str, str]]:
    """Load all cards that have realistic images."""
    print(f"Loading image manifest from: {MANIFEST_PATH}")
    
    df = pd.read_csv(MANIFEST_PATH)
    print(f"  Total rows in manifest: {len(df)}")
    
    image_cards = set()
    
    for idx, row in df.iterrows():
        filename = row['original_rel_path']
        group_id, entity_id, card_role = parse_image_filename(filename)
        
        if group_id and entity_id and card_role:
            image_cards.add((group_id, entity_id, card_role))
    
    print(f"  Extracted {len(image_cards)} unique cards with images")
    return image_cards


def load_new_assignments() -> pd.DataFrame:
    """Load NEW assignment data (Jan 6) which has specialist assignments."""
    print(f"\nLoading NEW assignments from: {NEW_ASSIGNMENTS}")
    
    df = pd.read_csv(NEW_ASSIGNMENTS)
    print(f"  Total assignments: {len(df)}")
    print(f"  Specialist assignments: {len(df[df['rater_role'] == 'specialist'])}")
    print(f"  Resident assignments: {len(df[df['rater_role'] == 'resident'])}")
    
    return df


def extract_card_key(card_uid: str) -> Tuple[str, str, str]:
    """
    Extract group_id, entity_id, card_role from card_uid.
    
    Example: grp_ad44d0b476::DERIVED:8f72b4dc3d3f__Q2__1
    Returns: ('grp_ad44d0b476', 'DERIVED:8f72b4dc3d3f', 'Q2')
    """
    pattern = r'(?P<group>grp_[a-f0-9]+)::(?P<entity>DERIVED:[a-f0-9]+)__(?P<role>Q[12])__\d+'
    match = re.match(pattern, card_uid)
    if not match:
        return None, None, None
    
    return match.group('group'), match.group('entity'), match.group('role')


def recover_specialist_assignments(
    new_assignments: pd.DataFrame,
    image_cards: Set[Tuple[str, str, str]]
) -> pd.DataFrame:
    """
    Recover ALL specialist assignments (both with and without images).
    
    Strategy:
    - Take all specialist assignments from NEW_jan6
    - Most should have images (286/330), some won't (44/330)
    - This gives us the full 330 specialist assignments
    """
    print("\n=== Recovering Specialist Assignments ===")
    
    specialist_df = new_assignments[new_assignments['rater_role'] == 'specialist'].copy()
    print(f"Total specialist assignments: {len(specialist_df)}")
    
    # Add card key for matching (for validation)
    specialist_df['card_key'] = specialist_df['card_uid'].apply(extract_card_key)
    
    # Check how many have images
    def has_image(card_key):
        if card_key is None or None in card_key:
            return False
        return card_key in image_cards
    
    specialist_df['has_image'] = specialist_df['card_key'].apply(has_image)
    with_images = specialist_df['has_image'].sum()
    without_images = (~specialist_df['has_image']).sum()
    
    print(f"  With images: {with_images}")
    print(f"  Without images: {without_images}")
    
    # Drop temporary columns
    recovered = specialist_df.drop(columns=['card_key', 'has_image'])
    
    print(f"\nBreakdown by specialist:")
    for email, group in recovered.groupby('rater_email'):
        print(f"  {group['rater_name'].iloc[0]:20s} ({email}): {len(group):3d} cards")
    
    return recovered


def recover_resident_assignments(
    new_assignments: pd.DataFrame,
    specialist_cards: Set[str]
) -> pd.DataFrame:
    """
    Recover resident assignments for cards NOT assigned to specialists.
    
    Strategy:
    - Filter NEW resident assignments
    - Exclude cards that are in specialist_cards
    """
    print("\n=== Recovering Resident Assignments ===")
    
    resident_df = new_assignments[new_assignments['rater_role'] == 'resident'].copy()
    print(f"Total NEW resident assignments: {len(resident_df)}")
    
    # Filter out cards assigned to specialists
    resident_df = resident_df[~resident_df['card_uid'].isin(specialist_cards)].copy()
    
    print(f"Recovered resident assignments: {len(resident_df)}")
    print(f"\nBreakdown by resident:")
    for email, group in resident_df.groupby('rater_email'):
        print(f"  {group['rater_name'].iloc[0]:20s} ({email}): {len(group):3d} cards")
    
    return resident_df


def build_allocation(
    specialist_df: pd.DataFrame,
    resident_df: pd.DataFrame
) -> Dict:
    """Build allocation JSON from recovered assignments."""
    print("\n=== Building Allocation ===")
    
    allocation = {
        "specialist": {},
        "resident": {}
    }
    
    # Specialist allocation
    for email, group in specialist_df.groupby('rater_email'):
        name = group['rater_name'].iloc[0]
        card_uids = group['card_uid'].tolist()
        allocation["specialist"][email] = {
            "name": name,
            "card_uids": card_uids,
            "count": len(card_uids)
        }
    
    # Resident allocation
    for email, group in resident_df.groupby('rater_email'):
        name = group['rater_name'].iloc[0]
        card_uids = group['card_uid'].tolist()
        allocation["resident"][email] = {
            "name": name,
            "card_uids": card_uids,
            "count": len(card_uids)
        }
    
    # Summary
    total_specialist = sum(v['count'] for v in allocation['specialist'].values())
    total_resident = sum(v['count'] for v in allocation['resident'].values())
    
    print(f"Specialist allocation: {len(allocation['specialist'])} raters, {total_specialist} cards")
    print(f"Resident allocation: {len(allocation['resident'])} raters, {total_resident} cards")
    print(f"Total cards: {total_specialist + total_resident}")
    
    return allocation


def save_outputs(
    specialist_df: pd.DataFrame,
    resident_df: pd.DataFrame,
    allocation: Dict
):
    """Save recovered assignments and allocation."""
    print("\n=== Saving Outputs ===")
    
    # Ensure output directories exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "allocation").mkdir(parents=True, exist_ok=True)
    
    # Save specialist assignments
    specialist_df.to_csv(SPECIALIST_CSV, index=False)
    print(f"✓ Saved specialist assignments: {SPECIALIST_CSV}")
    print(f"  {len(specialist_df)} rows")
    
    # Save resident assignments
    resident_df.to_csv(RESIDENT_CSV, index=False)
    print(f"✓ Saved resident assignments: {RESIDENT_CSV}")
    print(f"  {len(resident_df)} rows")
    
    # Save allocation
    with open(ALLOCATION_JSON, 'w', encoding='utf-8') as f:
        json.dump(allocation, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved allocation: {ALLOCATION_JSON}")


def validate_recovery(
    specialist_df: pd.DataFrame,
    resident_df: pd.DataFrame,
    image_cards: Set[Tuple[str, str, str]]
):
    """Validate the recovered assignments."""
    print("\n=== Validation ===")
    
    # Check specialist cards all have images
    specialist_keys = set()
    for card_uid in specialist_df['card_uid']:
        key = extract_card_key(card_uid)
        if key and None not in key:
            specialist_keys.add(key)
    
    missing_images = specialist_keys - image_cards
    extra_images = image_cards - specialist_keys
    
    print(f"Specialist cards: {len(specialist_keys)}")
    print(f"Image cards: {len(image_cards)}")
    print(f"Missing images (specialist cards without images): {len(missing_images)}")
    print(f"Extra images (images without specialist assignment): {len(extra_images)}")
    
    if missing_images:
        print("\n⚠️  WARNING: Some specialist cards don't have images!")
        for key in list(missing_images)[:5]:
            print(f"  {key}")
        if len(missing_images) > 5:
            print(f"  ... and {len(missing_images) - 5} more")
    
    if extra_images:
        print("\n⚠️  WARNING: Some images don't have specialist assignments!")
        for key in list(extra_images)[:5]:
            print(f"  {key}")
        if len(extra_images) > 5:
            print(f"  ... and {len(extra_images) - 5} more")
    
    # Check no overlap between specialist and resident
    specialist_uids = set(specialist_df['card_uid'])
    resident_uids = set(resident_df['card_uid'])
    overlap = specialist_uids & resident_uids
    
    print(f"\nOverlap between specialist and resident: {len(overlap)}")
    if overlap:
        print("⚠️  WARNING: Found overlapping assignments!")
        for uid in list(overlap)[:5]:
            print(f"  {uid}")
    
    # Check total cards
    total_cards = len(specialist_uids) + len(resident_uids)
    print(f"\nTotal unique cards assigned: {total_cards}")
    print(f"Expected: ~1000 (330 specialist + 670 resident)")
    
    if total_cards < 900:
        print("⚠️  WARNING: Total cards seem low!")
    elif total_cards > 1100:
        print("⚠️  WARNING: Total cards seem high!")
    else:
        print("✓ Total cards in expected range")


def main():
    print("=" * 80)
    print("ASSIGNMENT RECOVERY FROM IMAGES_REALISTIC")
    print("=" * 80)
    
    # Step 1: Load image cards
    image_cards = load_image_cards()
    
    # Step 2: Load NEW assignments (Jan 6)
    new_assignments = load_new_assignments()
    
    # Step 3: Recover ALL specialist assignments (330 total)
    specialist_df = recover_specialist_assignments(new_assignments, image_cards)
    
    # Step 4: Recover resident assignments (remaining cards)
    specialist_card_uids = set(specialist_df['card_uid'])
    resident_df = recover_resident_assignments(new_assignments, specialist_card_uids)
    
    # Step 5: Build allocation
    allocation = build_allocation(specialist_df, resident_df)
    
    # Step 6: Validate
    validate_recovery(specialist_df, resident_df, image_cards)
    
    # Step 7: Save outputs
    save_outputs(specialist_df, resident_df, allocation)
    
    print("\n" + "=" * 80)
    print("RECOVERY COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Review the validation warnings above")
    print("2. Check the output files:")
    print(f"   - {SPECIALIST_CSV}")
    print(f"   - {RESIDENT_CSV}")
    print(f"   - {ALLOCATION_JSON}")
    print("3. If everything looks good, you can use these files to restore the assignments")


if __name__ == "__main__":
    main()


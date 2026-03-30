#!/usr/bin/env python3
"""
Rebuild assignments from allocation with full traceability.

This script implements Phase 1-2 of the allocation-based final export plan:
1. Load and analyze allocation JSON (6,000 cards)
2. Build S5 decision map
3. Stratified sampling (~1,500 cards)
4. Role assignment (specialist/resident)
5. Generate Assignments.csv
6. Check existing realistic images for reuse
"""

import json
import csv
import random
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set
import hashlib
from datetime import datetime

# Set random seed for reproducibility
random.seed(42)

BASE_DIR = Path("/path/to/workspace/workspace/MeducAI")
FINAL_DIST_DIR = BASE_DIR / "2_Data/metadata/generated/FINAL_DISTRIBUTION"


def load_allocation() -> List[Dict]:
    """Load allocation JSON (6,000 cards)."""
    allocation_path = FINAL_DIST_DIR / "allocation/final_distribution_allocation__6000cards.json"
    print(f"Loading allocation from: {allocation_path}")
    
    with open(allocation_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get cards from 'selected_cards' key
    cards = data.get('selected_cards', [])
    
    # Get group allocation to add specialty info
    group_allocation = data.get('group_allocation', {})
    
    # Enrich cards with specialty from group allocation
    for card in cards:
        group_id = card.get('group_id', '')
        if group_id in group_allocation:
            card['specialty'] = group_allocation[group_id].get('specialty', 'unknown')
        else:
            card['specialty'] = 'unknown'
        
        # Construct card_uid as entity_id + __ + card_role
        entity_id = card.get('entity_id', '')
        card_role = card.get('card_role', '')
        card['card_uid'] = f"{entity_id}__{card_role}"
        
        # Ensure card_id exists
        if 'card_id' not in card or not card['card_id']:
            card['card_id'] = card['card_uid']
    
    print(f"✅ Loaded {len(cards)} cards from allocation")
    
    return cards


def analyze_allocation(cards: List[Dict]) -> Dict:
    """Analyze allocation distribution."""
    print("\n" + "="*80)
    print("ALLOCATION ANALYSIS")
    print("="*80)
    
    # Specialty distribution
    specialties = Counter(c.get('specialty', 'unknown') for c in cards)
    print(f"\n📊 Specialty Distribution ({len(specialties)} specialties):")
    for specialty, count in sorted(specialties.items(), key=lambda x: -x[1]):
        print(f"   {specialty:30s}: {count:4d} cards ({count/len(cards)*100:5.2f}%)")
    
    # Card role distribution
    card_roles = Counter(c.get('card_role', 'unknown') for c in cards)
    print(f"\n📊 Card Role Distribution:")
    for role, count in card_roles.items():
        print(f"   {role:10s}: {count:4d} cards ({count/len(cards)*100:5.2f}%)")
    
    # Group distribution
    groups = set(c.get('group_id', '') for c in cards)
    print(f"\n📊 Groups: {len(groups)} unique groups")
    
    return {
        'total_cards': len(cards),
        'specialties': dict(specialties),
        'card_roles': dict(card_roles),
        'num_groups': len(groups)
    }


def load_s5_validation() -> List[Dict]:
    """Load S5 validation data."""
    s5_path = FINAL_DIST_DIR / "s5_validation__armG.jsonl"
    print(f"\nLoading S5 validation from: {s5_path}")
    
    s5_data = []
    with open(s5_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                s5_data.append(json.loads(line))
    
    print(f"✅ Loaded {len(s5_data)} S5 validation records")
    return s5_data


def build_s5_decision_map(s5_data: List[Dict]) -> Dict[str, Dict]:
    """Build card-level decision map from S5 validation.
    
    Returns:
        {card_uid: {decision, trigger_score, issues, ...}}
    """
    print("\n" + "="*80)
    print("S5 DECISION MAP CONSTRUCTION")
    print("="*80)
    
    decision_map = {}
    
    for group_record in s5_data:
        group_id = group_record.get('group_id', '')
        
        # Get card-level validation from s2_cards_validation
        s2_validation = group_record.get('s2_cards_validation', {})
        cards = s2_validation.get('cards', [])
        
        for card_data in cards:
            entity_id = card_data.get('entity_id', '')
            card_role = card_data.get('card_role', '')
            card_uid = f"{entity_id}__{card_role}"
            
            # Get trigger scores
            trigger_score = card_data.get('regeneration_trigger_score', 0)
            card_trigger = card_data.get('card_regeneration_trigger_score', 0)
            image_trigger = card_data.get('image_regeneration_trigger_score', 0)
            
            # Determine decision based on trigger score (threshold = 80)
            if card_trigger >= 80:
                decision = 'CARD_REGEN'
            elif image_trigger >= 80:
                decision = 'IMAGE_REGEN'
            else:
                decision = 'PASS'
            
            # Get issues
            issues = card_data.get('issues', [])
            image_issues = card_data.get('card_image_validation', {}).get('issues', [])
            all_issues = issues + image_issues
            
            decision_map[card_uid] = {
                'decision': decision,
                'trigger_score': trigger_score,
                'card_trigger_score': card_trigger,
                'image_trigger_score': image_trigger,
                'issues': all_issues,
                'group_id': group_id,
                'entity_id': entity_id,
                'card_role': card_role
            }
    
    # Analyze decision distribution
    if decision_map:
        decisions = Counter(d['decision'] for d in decision_map.values())
        print(f"\n📊 S5 Decision Distribution ({len(decision_map)} cards):")
        for decision, count in sorted(decisions.items(), key=lambda x: -x[1]):
            print(f"   {decision:20s}: {count:4d} cards ({count/len(decision_map)*100:5.2f}%)")
        
        # Trigger score distribution
        trigger_scores = [d['trigger_score'] for d in decision_map.values()]
        print(f"\n📊 Trigger Score Statistics:")
        print(f"   Mean:   {sum(trigger_scores)/len(trigger_scores):.2f}")
        print(f"   Max:    {max(trigger_scores)}")
        print(f"   Min:    {min(trigger_scores)}")
        print(f"   ≥80:    {sum(1 for s in trigger_scores if s >= 80)} cards")
    else:
        print("\n⚠️ Warning: No cards found in S5 decision map")
    
    return decision_map


def stratified_sample(
    cards: List[Dict],
    decision_map: Dict[str, Dict],
    target_size: int = 1500
) -> List[Dict]:
    """Stratified sampling from allocation.
    
    Strategy:
    1. Include ALL CARD_REGEN cards (highest priority)
    2. Sample IMAGE_REGEN cards (50% rate)
    3. Fill remaining with PASS cards (stratified by specialty)
    """
    print("\n" + "="*80)
    print("STRATIFIED SAMPLING")
    print("="*80)
    
    # Annotate cards with S5 decisions
    for card in cards:
        card_uid = card.get('card_uid', '')
        s5_info = decision_map.get(card_uid, {})
        card['s5_decision'] = s5_info.get('decision', 'PASS')
        card['s5_trigger_score'] = s5_info.get('trigger_score', 0)
        card['s5_issues'] = s5_info.get('issues', [])
    
    # Group by decision
    by_decision = defaultdict(list)
    for card in cards:
        decision = card.get('s5_decision', 'PASS')
        by_decision[decision].append(card)
    
    print(f"\n📊 Cards by S5 Decision:")
    for decision, cards_list in sorted(by_decision.items()):
        print(f"   {decision:20s}: {len(cards_list):4d} cards")
    
    # Sampling strategy
    selected = []
    
    # 1. Include ALL CARD_REGEN (highest value)
    card_regen = by_decision.get("CARD_REGEN", [])
    selected.extend(card_regen)
    print(f"\n✅ Selected ALL CARD_REGEN: {len(card_regen)} cards")
    
    # 2. Sample IMAGE_REGEN (50% rate)
    image_regen = by_decision.get("IMAGE_REGEN", [])
    image_regen_sample_size = len(image_regen) // 2
    image_regen_selected = random.sample(image_regen, image_regen_sample_size)
    selected.extend(image_regen_selected)
    print(f"✅ Selected 50% IMAGE_REGEN: {len(image_regen_selected)} / {len(image_regen)} cards")
    
    # 3. Fill remaining with PASS cards (stratified by specialty)
    remaining_target = target_size - len(selected)
    pass_cards = by_decision.get("PASS", [])
    
    # Stratify PASS cards by specialty
    pass_by_specialty = defaultdict(list)
    for card in pass_cards:
        specialty = card.get('specialty', 'unknown')
        pass_by_specialty[specialty].append(card)
    
    # Calculate proportional sample sizes
    total_pass = len(pass_cards)
    pass_selected = []
    
    for specialty, specialty_cards in pass_by_specialty.items():
        proportion = len(specialty_cards) / total_pass
        sample_size = int(remaining_target * proportion)
        
        # Sample from this specialty
        if sample_size > 0 and len(specialty_cards) >= sample_size:
            sampled = random.sample(specialty_cards, sample_size)
            pass_selected.extend(sampled)
    
    # Fill any remaining slots
    if len(pass_selected) < remaining_target:
        remaining_pass = [c for c in pass_cards if c not in pass_selected]
        additional_needed = remaining_target - len(pass_selected)
        if len(remaining_pass) >= additional_needed:
            additional = random.sample(remaining_pass, additional_needed)
            pass_selected.extend(additional)
    
    selected.extend(pass_selected)
    print(f"✅ Selected stratified PASS: {len(pass_selected)} cards")
    
    print(f"\n📊 Total selected: {len(selected)} / {target_size} target cards")
    
    # Analyze selected sample
    selected_specialties = Counter(c.get('specialty', 'unknown') for c in selected)
    print(f"\n📊 Selected Sample by Specialty:")
    for specialty, count in sorted(selected_specialties.items(), key=lambda x: -x[1]):
        print(f"   {specialty:30s}: {count:4d} cards ({count/len(selected)*100:5.2f}%)")
    
    selected_decisions = Counter(c.get('s5_decision', 'PASS') for c in selected)
    print(f"\n📊 Selected Sample by S5 Decision:")
    for decision, count in sorted(selected_decisions.items()):
        print(f"   {decision:20s}: {count:4d} cards ({count/len(selected)*100:5.2f}%)")
    
    return selected


def assign_roles(qa_sample: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """Assign specialist/resident roles to sampled cards.
    
    Specialist cards (target: 330):
    - Diverse specialty coverage (30 per specialty)
    - Mix of REGEN and PASS
    - Complex/challenging cases
    
    Returns:
        (specialist_cards, resident_cards)
    """
    print("\n" + "="*80)
    print("ROLE ASSIGNMENT")
    print("="*80)
    
    # Group by specialty
    by_specialty = defaultdict(list)
    for card in qa_sample:
        specialty = card.get('specialty', 'unknown')
        by_specialty[specialty].append(card)
    
    specialist_cards = []
    target_per_specialty = 30
    
    print(f"\n📊 Selecting {target_per_specialty} specialist cards per specialty:")
    
    for specialty, cards_list in sorted(by_specialty.items()):
        # Sort by trigger score (descending) to get most interesting cards
        cards_list.sort(key=lambda c: c.get('s5_trigger_score', 0), reverse=True)
        
        # Select top N cards from this specialty
        n = min(target_per_specialty, len(cards_list))
        selected = cards_list[:n]
        specialist_cards.extend(selected)
        
        # Count decisions in selected
        decisions = Counter(c.get('s5_decision', 'PASS') for c in selected)
        decision_str = ', '.join(f"{k}:{v}" for k, v in sorted(decisions.items()))
        
        print(f"   {specialty:30s}: {n:3d} cards ({decision_str})")
    
    # Annotate specialist cards
    for card in specialist_cards:
        card['rater_role'] = 'specialist'
    
    # Remaining cards are resident cards
    specialist_uids = set(c['card_uid'] for c in specialist_cards)
    resident_cards = [c for c in qa_sample if c['card_uid'] not in specialist_uids]
    
    for card in resident_cards:
        card['rater_role'] = 'resident'
    
    print(f"\n✅ Assigned roles:")
    print(f"   Specialist: {len(specialist_cards)} cards")
    print(f"   Resident:   {len(resident_cards)} cards")
    print(f"   Total:      {len(specialist_cards) + len(resident_cards)} cards")
    
    return specialist_cards, resident_cards


def load_rater_list() -> List[Dict]:
    """Load rater information.
    
    For now, create mock raters. In production, load from user_sheet.csv
    """
    # Mock raters for testing
    specialist_raters = [
        {'email': f'specialist{i}@example.com', 'name': f'전문의 {i}', 'role': 'specialist'}
        for i in range(1, 6)  # 5 specialists
    ]
    
    resident_raters = [
        {'email': f'resident{i}@example.com', 'name': f'전공의 {i}', 'role': 'resident'}
        for i in range(1, 11)  # 10 residents
    ]
    
    return {
        'specialist': specialist_raters,
        'resident': resident_raters
    }


def generate_assignment_id(rater_email: str, card_uid: str) -> str:
    """Generate unique assignment ID."""
    combined = f"{rater_email}_{card_uid}"
    hash_obj = hashlib.md5(combined.encode())
    return f"asgn_{hash_obj.hexdigest()[:12]}"


def generate_assignments(
    specialist_cards: List[Dict],
    resident_cards: List[Dict],
    raters: Dict[str, List[Dict]]
) -> List[Dict]:
    """Generate Assignments.csv with full metadata.
    
    Assignment structure:
    - Specialist cards: 3-5 raters per card
    - Resident cards: 1-2 raters per card
    """
    print("\n" + "="*80)
    print("ASSIGNMENT GENERATION")
    print("="*80)
    
    assignments = []
    
    specialist_raters = raters['specialist']
    resident_raters = raters['resident']
    
    # Specialist assignments (3 raters per card)
    raters_per_specialist_card = 3
    print(f"\n📝 Generating specialist assignments ({raters_per_specialist_card} raters per card)...")
    
    for card in specialist_cards:
        # Select 3 random specialist raters
        selected_raters = random.sample(specialist_raters, min(raters_per_specialist_card, len(specialist_raters)))
        
        for rater in selected_raters:
            assignment = {
                'assignment_id': generate_assignment_id(rater['email'], card['card_uid']),
                'rater_email': rater['email'],
                'rater_name': rater['name'],
                'rater_role': 'specialist',
                'card_uid': card['card_uid'],
                'card_id': card.get('card_id', ''),
                'group_id': card.get('group_id', ''),
                'entity_id': card.get('entity_id', ''),
                'specialty': card.get('specialty', ''),
                'card_role': card.get('card_role', ''),
                's5_decision': card.get('s5_decision', 'PASS'),
                's5_trigger_score': card.get('s5_trigger_score', 0),
                'is_calibration': 0,
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }
            assignments.append(assignment)
    
    print(f"   ✅ Created {len(assignments)} specialist assignments")
    
    # Resident assignments (2 raters per card)
    raters_per_resident_card = 2
    print(f"\n📝 Generating resident assignments ({raters_per_resident_card} raters per card)...")
    
    resident_assignment_count = 0
    for card in resident_cards:
        # Select 2 random resident raters
        selected_raters = random.sample(resident_raters, min(raters_per_resident_card, len(resident_raters)))
        
        for rater in selected_raters:
            assignment = {
                'assignment_id': generate_assignment_id(rater['email'], card['card_uid']),
                'rater_email': rater['email'],
                'rater_name': rater['name'],
                'rater_role': 'resident',
                'card_uid': card['card_uid'],
                'card_id': card.get('card_id', ''),
                'group_id': card.get('group_id', ''),
                'entity_id': card.get('entity_id', ''),
                'specialty': card.get('specialty', ''),
                'card_role': card.get('card_role', ''),
                's5_decision': card.get('s5_decision', 'PASS'),
                's5_trigger_score': card.get('s5_trigger_score', 0),
                'is_calibration': 0,
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }
            assignments.append(assignment)
            resident_assignment_count += 1
    
    print(f"   ✅ Created {resident_assignment_count} resident assignments")
    
    print(f"\n📊 Total assignments: {len(assignments)}")
    print(f"   - Specialist assignments: {len(specialist_cards) * raters_per_specialist_card}")
    print(f"   - Resident assignments: {len(resident_cards) * raters_per_resident_card}")
    
    return assignments


def save_assignments(assignments: List[Dict], output_path: Path):
    """Save assignments to CSV."""
    print(f"\n💾 Saving assignments to: {output_path}")
    
    fieldnames = [
        'assignment_id', 'rater_email', 'rater_name', 'rater_role',
        'card_uid', 'card_id', 'group_id', 'entity_id', 'specialty',
        'card_role', 's5_decision', 's5_trigger_score',
        'is_calibration', 'status', 'created_at'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(assignments)
    
    print(f"✅ Saved {len(assignments)} assignments")


def check_existing_realistic_images(specialist_cards: List[Dict]) -> Dict[str, Path]:
    """Check which existing realistic images can be reused.
    
    Returns:
        {card_uid: image_path} for reusable images
    """
    print("\n" + "="*80)
    print("EXISTING REALISTIC IMAGES CHECK")
    print("="*80)
    
    realistic_dir = FINAL_DIST_DIR / "images_realistic"
    print(f"\nScanning: {realistic_dir}")
    
    # Find all realistic images
    existing_images = list(realistic_dir.glob("*.png")) + list(realistic_dir.glob("*.jpg"))
    print(f"✅ Found {len(existing_images)} existing realistic images")
    
    # Parse card UIDs from filenames
    # Expected format: card_uid_*.png or similar
    existing_image_map = {}
    
    for img_path in existing_images:
        filename = img_path.stem
        
        # Try to extract card_uid
        # Assuming format: card_<uid>_* or <uid>_*
        parts = filename.split('_')
        
        # Common patterns:
        # 1. card_<uid>_realistic.png
        # 2. <uid>_realistic.png
        # 3. <uid>_<timestamp>.png
        
        if len(parts) >= 2:
            # Try first part as UID
            potential_uid = parts[0]
            if potential_uid.startswith('card'):
                potential_uid = '_'.join(parts[:2])  # card_xxxxx
            
            existing_image_map[potential_uid] = img_path
    
    print(f"✅ Parsed {len(existing_image_map)} unique card UIDs from filenames")
    
    # Check which specialist cards have existing realistic images
    specialist_card_uids = set(c['card_uid'] for c in specialist_cards)
    
    reusable = {}
    missing = []
    
    for card_uid in specialist_card_uids:
        if card_uid in existing_image_map:
            reusable[card_uid] = existing_image_map[card_uid]
        else:
            missing.append(card_uid)
    
    print(f"\n📊 Realistic Image Reusability:")
    print(f"   Reusable:  {len(reusable)} / {len(specialist_cards)} specialist cards ({len(reusable)/len(specialist_cards)*100:.1f}%)")
    print(f"   Missing:   {len(missing)} cards need new realistic images")
    
    return reusable


def save_qa_sample(qa_sample: List[Dict], output_path: Path):
    """Save QA sample to JSON."""
    print(f"\n💾 Saving QA sample to: {output_path}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'total_cards': len(qa_sample),
            'created_at': datetime.now().isoformat(),
            'cards': qa_sample
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved {len(qa_sample)} cards")


def save_specialist_cards(specialist_cards: List[Dict], output_path: Path):
    """Save specialist cards to JSON."""
    print(f"\n💾 Saving specialist cards to: {output_path}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'total_cards': len(specialist_cards),
            'created_at': datetime.now().isoformat(),
            'cards': specialist_cards
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved {len(specialist_cards)} specialist cards")


def save_summary_report(
    allocation_analysis: Dict,
    qa_sample: List[Dict],
    specialist_cards: List[Dict],
    resident_cards: List[Dict],
    assignments: List[Dict],
    reusable_images: Dict[str, Path],
    output_path: Path
):
    """Save comprehensive summary report."""
    print(f"\n💾 Saving summary report to: {output_path}")
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'allocation': allocation_analysis,
        'qa_sample': {
            'total_cards': len(qa_sample),
            'by_decision': dict(Counter(c.get('s5_decision', 'PASS') for c in qa_sample)),
            'by_specialty': dict(Counter(c.get('specialty', 'unknown') for c in qa_sample))
        },
        'role_assignment': {
            'specialist_cards': len(specialist_cards),
            'resident_cards': len(resident_cards),
            'specialist_by_specialty': dict(Counter(c.get('specialty', 'unknown') for c in specialist_cards)),
            'resident_by_specialty': dict(Counter(c.get('specialty', 'unknown') for c in resident_cards))
        },
        'assignments': {
            'total_assignments': len(assignments),
            'specialist_assignments': sum(1 for a in assignments if a['rater_role'] == 'specialist'),
            'resident_assignments': sum(1 for a in assignments if a['rater_role'] == 'resident'),
            'by_rater_role': dict(Counter(a['rater_role'] for a in assignments))
        },
        'realistic_images': {
            'specialist_cards_total': len(specialist_cards),
            'reusable_images': len(reusable_images),
            'missing_images': len(specialist_cards) - len(reusable_images),
            'reusability_rate': len(reusable_images) / len(specialist_cards) * 100 if specialist_cards else 0
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved summary report")


def main():
    """Main execution function."""
    print("="*80)
    print("ALLOCATION-BASED ASSIGNMENT RECONSTRUCTION")
    print("="*80)
    print(f"Started at: {datetime.now().isoformat()}")
    
    # Create output directory
    output_dir = BASE_DIR / "2_Data/metadata/generated/FINAL_DISTRIBUTION/assignment_rebuild"
    output_dir.mkdir(exist_ok=True, parents=True)
    print(f"\n📁 Output directory: {output_dir}")
    
    # Task 1: Load and analyze allocation
    print("\n" + "="*80)
    print("TASK 1: LOAD ALLOCATION")
    print("="*80)
    cards = load_allocation()
    allocation_analysis = analyze_allocation(cards)
    
    # Task 2: Build S5 decision map
    print("\n" + "="*80)
    print("TASK 2: BUILD S5 DECISION MAP")
    print("="*80)
    s5_data = load_s5_validation()
    decision_map = build_s5_decision_map(s5_data)
    
    # Task 3: Stratified sampling
    print("\n" + "="*80)
    print("TASK 3: STRATIFIED SAMPLING")
    print("="*80)
    qa_sample = stratified_sample(cards, decision_map, target_size=1500)
    
    # Save QA sample
    qa_sample_path = output_dir / "qa_sample_1500cards.json"
    save_qa_sample(qa_sample, qa_sample_path)
    
    # Task 4: Assign roles
    print("\n" + "="*80)
    print("TASK 4: ROLE ASSIGNMENT")
    print("="*80)
    specialist_cards, resident_cards = assign_roles(qa_sample)
    
    # Save specialist cards
    specialist_cards_path = output_dir / "specialist_cards.json"
    save_specialist_cards(specialist_cards, specialist_cards_path)
    
    # Task 5: Generate assignments
    print("\n" + "="*80)
    print("TASK 5: GENERATE ASSIGNMENTS")
    print("="*80)
    raters = load_rater_list()
    assignments = generate_assignments(specialist_cards, resident_cards, raters)
    
    # Save assignments
    assignments_path = output_dir / "Assignments.csv"
    save_assignments(assignments, assignments_path)
    
    # Task 6: Check existing realistic images
    print("\n" + "="*80)
    print("TASK 6: CHECK EXISTING REALISTIC IMAGES")
    print("="*80)
    reusable_images = check_existing_realistic_images(specialist_cards)
    
    # Save summary report
    summary_path = output_dir / "assignment_rebuild_summary.json"
    save_summary_report(
        allocation_analysis,
        qa_sample,
        specialist_cards,
        resident_cards,
        assignments,
        reusable_images,
        summary_path
    )
    
    print("\n" + "="*80)
    print("✅ ALL TASKS COMPLETED")
    print("="*80)
    print(f"\nOutput files:")
    print(f"  1. QA Sample:         {qa_sample_path}")
    print(f"  2. Specialist Cards:  {specialist_cards_path}")
    print(f"  3. Assignments CSV:   {assignments_path}")
    print(f"  4. Summary Report:    {summary_path}")
    print(f"\nFinished at: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()


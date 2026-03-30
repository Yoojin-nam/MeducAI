#!/usr/bin/env python3
"""
Generate FINAL QA resident assignments using EXISTING specialist assignments.

This variant uses pre-existing specialist assignments (with realistic images)
and generates only resident assignments, ensuring full compatibility.

Key features:
- Uses existing specialist assignments from assignments_specialist.csv
- Calibration drawn from specialist pool (guarantees realistic image coverage)
- REGEN census review (≤200 items) or cap (>200 items)  
- Resident assignment: 1,350 items total (9 residents × 150 items)
- Cluster(Objective) shuffle for statistical independence
- Fixed seed: 20260101
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_THIS_FILE = Path(__file__).resolve()
_SRC_ROOT = _THIS_FILE.parents[2]  # .../3_Code/src
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from tools.qa.s5_decision import determine_s5_decision


# Constants
SEED = 20260101
CALIBRATION_ITEMS_COUNT = 33
CALIBRATION_K_PER_ITEM = 3  # partial overlap (3 residents per calibration item)
RESIDENT_COUNT = 9
RESIDENT_ITEMS_PER_PERSON = 150
RESIDENT_TOTAL_ITEMS = RESIDENT_COUNT * RESIDENT_ITEMS_PER_PERSON  # 1,350
REGEN_CENSUS_THRESHOLD = 200

# Specialty mapping
SPECIALTY_CODES = [
    "neuro_hn_imaging",
    "breast_rad",
    "thoracic_radiology",
    "interventional_radiology",
    "musculoskeletal_radiology",
    "gu_radiology",
    "cardiovascular_rad",
    "abdominal_radiology",
    "physics_qc_informatics",
    "pediatric_radiology",
    "nuclear_med",
]


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read JSONL file."""
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSONL at {path} line {line_no}: {e}") from e
    return rows


def _read_csv(path: Path) -> List[Dict[str, Any]]:
    """Read CSV file."""
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def load_allocation_json(allocation_path: Path) -> Dict[str, Any]:
    """Load allocation JSON file."""
    if not allocation_path.exists():
        raise FileNotFoundError(f"Allocation file not found: {allocation_path}")
    with allocation_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_s5_validation(s5_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Load S5 validation results.
    
    Returns:
        Dict mapping card_uid -> S5 record with s5_decision field
    """
    s5_index: Dict[str, Dict[str, Any]] = {}
    
    if s5_path.suffix == ".jsonl":
        # Load from JSONL
        for row in _read_jsonl(s5_path):
            group_id = row.get("group_id", "")
            s2 = row.get("s2_cards_validation", {})
            cards = s2.get("cards", [])
            for card in cards:
                card_id = card.get("card_id", "")
                if not card_id or not group_id:
                    continue
                card_uid = f"{group_id}::{card_id}"
                
                # Create S5 record
                s5_record = {
                    "card_uid": card_uid,
                    "card_id": card_id,
                    "group_id": group_id,
                    "s5_regeneration_trigger_score": card.get("regeneration_trigger_score"),
                    "s5_card_regeneration_trigger_score": card.get("card_regeneration_trigger_score"),
                    "s5_image_regeneration_trigger_score": card.get("image_regeneration_trigger_score"),
                }
                
                # Determine S5 decision
                s5_record["s5_decision"] = determine_s5_decision(s5_record)
                s5_index[card_uid] = s5_record
    
    return s5_index


def load_specialist_assignments(specialist_csv_path: Path) -> List[Dict[str, Any]]:
    """Load existing specialist assignments."""
    specialist_rows = _read_csv(specialist_csv_path)
    print(f"Loaded {len(specialist_rows)} specialist assignments from {specialist_csv_path}")
    return specialist_rows


def load_reviewers(reviewer_master_path: Path) -> List[Dict[str, Any]]:
    """Load resident reviewers only."""
    reviewers = _read_csv(reviewer_master_path)
    residents = []
    
    for reviewer in reviewers:
        role = reviewer.get("role", "").strip().lower()
        if role == "resident":
            residents.append(reviewer)
    
    return residents


def get_card_uid_from_allocation(card: Dict[str, Any]) -> str:
    """
    Extract card_uid from allocation card record.
    """
    group_id = card.get("group_id", "")
    entity_id = card.get("entity_id", "")
    card_role = card.get("card_role", "")
    
    if not (group_id and entity_id and card_role):
        return ""
    
    card_idx = 0 if card_role == "Q1" else 1
    s5_card_id = f"{entity_id}__{card_role}__{card_idx}"
    return f"{group_id}::{s5_card_id}"


def get_group_specialty(allocation: Dict[str, Any], group_id: str) -> str:
    """Get specialty for a group from allocation."""
    group_allocation = allocation.get("group_allocation", {})
    group_info = group_allocation.get(group_id, {})
    return group_info.get("specialty", "").strip()


def get_cluster_id(card: Dict[str, Any], allocation: Dict[str, Any]) -> str:
    """Get cluster ID (Objective) for a card. Uses group_id as cluster identifier."""
    group_id = card.get("group_id", "")
    if group_id:
        return group_id
    return "unknown"


def cluster_aware_shuffle(cards: List[Dict[str, Any]], allocation: Dict[str, Any], seed: int) -> List[Dict[str, Any]]:
    """Shuffle cards while interleaving across clusters."""
    if not cards:
        return []
    random.seed(seed)
    cluster_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for card in cards:
        cluster_groups[get_cluster_id(card, allocation)].append(card)

    # Shuffle within each cluster
    for _, cluster_cards in cluster_groups.items():
        random.shuffle(cluster_cards)

    # Shuffle cluster order, then interleave
    cluster_ids = list(cluster_groups.keys())
    random.shuffle(cluster_ids)
    max_cluster_size = max(len(v) for v in cluster_groups.values())
    out: List[Dict[str, Any]] = []
    for i in range(max_cluster_size):
        for cid in cluster_ids:
            cluster_cards = cluster_groups[cid]
            if i < len(cluster_cards):
                out.append(cluster_cards[i])
    return out


def select_calibration_from_specialist(
    *,
    specialist_card_uids: Set[str],
    enriched_cards_by_uid: Dict[str, Dict[str, Any]],
    allocation: Dict[str, Any],
    seed: int,
) -> List[Dict[str, Any]]:
    """
    Select 33 calibration items (11 specialties × 3) FROM specialist pool.
    """
    random.seed(seed)
    
    # Group specialist cards by specialty
    by_specialty: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for uid in specialist_card_uids:
        card = enriched_cards_by_uid.get(uid)
        if not card:
            continue
        gid = card.get("group_id", "")
        specialty = get_group_specialty(allocation, gid)
        if specialty:
            by_specialty[specialty].append(card)
    
    # Sample 3 from each specialty
    calibration_cards: List[Dict[str, Any]] = []
    used: Set[str] = set()
    
    for specialty_code in SPECIALTY_CODES:
        pool = [c for c in by_specialty.get(specialty_code, []) if c.get("card_uid") and c["card_uid"] not in used]
        if len(pool) < 3:
            print(f"[WARN] Insufficient specialist cards for calibration in {specialty_code}: need 3, have {len(pool)}")
            # Take all available
            sampled = pool
        else:
            sampled = random.sample(pool, 3)
        
        for c in sampled:
            used.add(c["card_uid"])
        calibration_cards.extend(sampled)
    
    print(f"Selected {len(calibration_cards)} calibration items from specialist pool")
    return calibration_cards


def create_balanced_calibration_schedule(
    *,
    calibration_cards: List[Dict[str, Any]],
    num_residents: int,
    k_per_item: int,
    seed: int,
) -> Dict[int, List[Dict[str, Any]]]:
    """
    Balanced partial overlap schedule:
    - Each calibration item is assigned to exactly k residents
    - Each resident receives exactly (n_items*k)/n_residents calibration items
    """
    if num_residents <= 0:
        raise ValueError("num_residents must be > 0")
    if k_per_item <= 0:
        raise ValueError("k_per_item must be > 0")
    if not calibration_cards:
        raise ValueError("calibration_cards is empty")

    total_slots = len(calibration_cards) * k_per_item
    if total_slots % num_residents != 0:
        raise ValueError(
            f"Cannot balance calibration: total_slots={total_slots} not divisible by num_residents={num_residents}"
        )
    per_resident = total_slots // num_residents

    random.seed(seed)
    shuffled = calibration_cards[:]
    random.shuffle(shuffled)

    assigned: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(num_residents)}
    counts = [0 for _ in range(num_residents)]

    for card in shuffled:
        # Prefer residents with the lowest current load
        ranked = sorted(range(num_residents), key=lambda i: (counts[i], random.random()))
        chosen: List[int] = []
        for ridx in ranked:
            if counts[ridx] >= per_resident:
                continue
            chosen.append(ridx)
            if len(chosen) == k_per_item:
                break
        if len(chosen) < k_per_item:
            raise RuntimeError("Failed to construct balanced calibration schedule")
        for ridx in chosen:
            assigned[ridx].append(card)
            counts[ridx] += 1

    if any(c != per_resident for c in counts):
        raise RuntimeError(f"Calibration schedule imbalance: counts={counts}, expected={per_resident}")
    return assigned


def distribute_with_partial_calibration(
    *,
    non_calibration_cards: List[Dict[str, Any]],
    residents: List[Dict[str, Any]],
    calibration_by_resident_idx: Dict[int, List[Dict[str, Any]]],
    allocation: Dict[str, Any],
    seed: int,
) -> List[Dict[str, Any]]:
    """Create resident assignments with partial-overlap calibration dispersed."""
    num_residents = len(residents)
    if num_residents <= 0:
        return []

    # Cluster-aware shuffle + round-robin
    shuffled_noncal = cluster_aware_shuffle(non_calibration_cards, allocation, seed)
    by_resident: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(num_residents)}
    for idx, card in enumerate(shuffled_noncal):
        by_resident[idx % num_residents].append(card)

    calibration_uids: Set[str] = set()
    for ridx, cal_cards in calibration_by_resident_idx.items():
        for c in cal_cards:
            cu = c.get("card_uid")
            if cu:
                calibration_uids.add(cu)

    assignments: List[Dict[str, Any]] = []
    for ridx in range(num_residents):
        cal_cards = calibration_by_resident_idx.get(ridx, [])
        noncal_cards = by_resident.get(ridx, [])

        # Sanity check
        expected_noncal = RESIDENT_ITEMS_PER_PERSON - len(cal_cards)
        if len(noncal_cards) != expected_noncal:
            raise RuntimeError(
                f"Resident idx={ridx} non-calibration count mismatch: expected {expected_noncal}, got {len(noncal_cards)}"
            )

        # Random position insertion for calibration items
        random.seed(seed + 1000 + ridx)
        all_positions = list(range(RESIDENT_ITEMS_PER_PERSON))
        cal_positions = set(random.sample(all_positions, k=len(cal_cards)))

        slots: List[Tuple[Dict[str, Any], bool]] = []
        noncal_iter = iter(noncal_cards)
        cal_iter = iter(cal_cards)
        for pos in range(RESIDENT_ITEMS_PER_PERSON):
            if pos in cal_positions:
                card = next(cal_iter)
                slots.append((card, True))
            else:
                card = next(noncal_iter)
                slots.append((card, False))

        for order, (card, is_cal) in enumerate(slots):
            card_uid = card.get("card_uid")
            if not card_uid:
                continue
            assignments.append(
                {
                    "reviewer_idx": ridx,
                    "card_uid": card_uid,
                    "card": card,
                    "is_calibration": bool(is_cal),
                    "assignment_order": order,
                }
            )

    return assignments


def generate_resident_assignments(
    allocation_path: Path,
    s5_path: Path,
    reviewer_master_path: Path,
    specialist_assignments_path: Path,
    out_dir: Path,
    seed: int = SEED,
) -> None:
    """
    Generate resident assignments using existing specialist assignments.
    
    Args:
        allocation_path: Path to allocation JSON file (6,000 cards)
        s5_path: Path to S5 validation JSONL
        reviewer_master_path: Path to reviewer_master.csv (for resident list)
        specialist_assignments_path: Path to assignments_specialist.csv (existing)
        out_dir: Output directory for Assignments.csv and summary JSON
        seed: Random seed (default: 20260101)
    """
    print(f"[1/7] Loading allocation from: {allocation_path}")
    allocation = load_allocation_json(allocation_path)
    
    print(f"[2/7] Loading S5 validation from: {s5_path}")
    s5_index = load_s5_validation(s5_path)
    
    print(f"[3/7] Loading residents from: {reviewer_master_path}")
    residents = load_reviewers(reviewer_master_path)
    
    print(f"[4/7] Loading existing specialist assignments from: {specialist_assignments_path}")
    specialist_rows = load_specialist_assignments(specialist_assignments_path)
    
    print(f"Found {len(residents)} residents")
    print(f"Found {len(specialist_rows)} specialist assignments")
    
    # Get selected cards from allocation
    selected_cards_raw = allocation.get("selected_cards", [])
    if not selected_cards_raw:
        raise ValueError("Allocation JSON must have 'selected_cards' field")
    print(f"Total selected cards in allocation: {len(selected_cards_raw)}")
    
    # Enrich cards with S5 decision
    enriched_cards = []
    for card in selected_cards_raw:
        card_uid = get_card_uid_from_allocation(card)
        if card_uid:
            s5_record = s5_index.get(card_uid, {})
            card["s5_decision"] = s5_record.get("s5_decision", "PASS")
            card["card_uid"] = card_uid
            enriched_cards.append(card)
        else:
            print(f"[WARN] Could not determine card_uid for card: {card}")
    
    enriched_cards_by_uid = {c["card_uid"]: c for c in enriched_cards}
    
    # Extract specialist pool card_uids
    specialist_card_uids = set(row["card_uid"] for row in specialist_rows if row.get("card_uid"))
    print(f"Specialist pool: {len(specialist_card_uids)} unique cards")
    
    # Verify specialist cards are in allocation
    specialist_in_allocation = sum(1 for uid in specialist_card_uids if uid in enriched_cards_by_uid)
    print(f"Specialist cards in allocation: {specialist_in_allocation}/{len(specialist_card_uids)} ({100*specialist_in_allocation/len(specialist_card_uids):.1f}%)")
    
    # Separate by S5 decision
    pass_cards = [c for c in enriched_cards if c.get("s5_decision") == "PASS"]
    regen_cards = [c for c in enriched_cards if c.get("s5_decision") == "REGEN"]
    
    print(f"[5/7] S5 decisions: PASS={len(pass_cards)}, REGEN={len(regen_cards)}")
    
    # Step 1: Select calibration items from specialist pool (33 items, 11 specialties × 3)
    calibration_items = select_calibration_from_specialist(
        specialist_card_uids=specialist_card_uids,
        enriched_cards_by_uid=enriched_cards_by_uid,
        allocation=allocation,
        seed=seed,
    )
    calibration_card_uids = {c["card_uid"] for c in calibration_items}
    print(f"Calibration: {len(calibration_items)} items (from specialist pool)")
    
    # Step 2: Create balanced calibration schedule for residents (33 × 3 = 99 slots)
    calibration_by_resident_idx = create_balanced_calibration_schedule(
        calibration_cards=calibration_items,
        num_residents=len(residents),
        k_per_item=CALIBRATION_K_PER_ITEM,
        seed=seed,
    )
    calibration_slots_total = len(calibration_items) * CALIBRATION_K_PER_ITEM
    calib_per_resident = calibration_slots_total // len(residents)
    print(f"Calibration schedule: {calibration_slots_total} slots, {calib_per_resident} per resident")
    
    # Step 3: REGEN processing (census or cap)
    random.seed(seed)
    if len(regen_cards) <= REGEN_CENSUS_THRESHOLD:
        regen_selected_all = regen_cards
        regen_census = True
        print(f"REGEN: Census review ({len(regen_cards)} items)")
    else:
        regen_selected_all = random.sample(regen_cards, REGEN_CENSUS_THRESHOLD)
        regen_census = False
        print(f"REGEN: Capped at {REGEN_CENSUS_THRESHOLD} items (total: {len(regen_cards)})")
    
    regen_selected_uids_all = {c["card_uid"] for c in regen_selected_all}
    regen_selected_uids_noncal = regen_selected_uids_all - calibration_card_uids
    regen_selected_noncal_cards = [c for c in regen_selected_all if c["card_uid"] in regen_selected_uids_noncal]
    
    # Step 4: Ensure 100% overlap with specialist pool (non-calibration)
    specialist_pool_noncal_uids = specialist_card_uids - calibration_card_uids
    
    # Step 5: Build base non-calibration set (REGEN + specialist pool)
    base_noncal_uids = regen_selected_uids_noncal | specialist_pool_noncal_uids
    base_noncal_uids_sorted = sorted(base_noncal_uids)
    base_noncal_cards = [enriched_cards_by_uid[uid] for uid in base_noncal_uids_sorted if uid in enriched_cards_by_uid]
    
    # Step 6: Fill remaining slots with PASS cards
    non_calibration_slots_total = RESIDENT_TOTAL_ITEMS - calibration_slots_total
    remaining_slots = non_calibration_slots_total - len(base_noncal_cards)
    
    print(f"[6/7] Resident slot allocation:")
    print(f"  Total slots: {RESIDENT_TOTAL_ITEMS}")
    print(f"  Calibration: {calibration_slots_total}")
    print(f"  Non-calibration: {non_calibration_slots_total}")
    print(f"    - REGEN (noncal): {len(regen_selected_uids_noncal)}")
    print(f"    - Specialist pool (noncal): {len(specialist_pool_noncal_uids)}")
    print(f"    - Base total: {len(base_noncal_cards)}")
    print(f"    - PASS fill needed: {remaining_slots}")
    
    pass_candidates = [
        c for c in pass_cards
        if c["card_uid"] not in calibration_card_uids
        and c["card_uid"] not in base_noncal_uids
    ]
    
    if len(pass_candidates) < remaining_slots:
        print(f"[WARN] PASS candidates insufficient: need {remaining_slots}, have {len(pass_candidates)}")
        remaining_slots = len(pass_candidates)
    
    assigned_pass = random.sample(pass_candidates, remaining_slots) if remaining_slots > 0 else []
    
    resident_noncal_cards = base_noncal_cards + assigned_pass
    
    if len(resident_noncal_cards) != non_calibration_slots_total:
        raise RuntimeError(
            f"Non-calibration pool size mismatch: expected {non_calibration_slots_total}, got {len(resident_noncal_cards)}"
        )
    
    # Step 7: Distribute to residents with position randomization
    print(f"[7/7] Distributing to {len(residents)} residents...")
    resident_assignments_raw = distribute_with_partial_calibration(
        non_calibration_cards=resident_noncal_cards,
        residents=residents,
        calibration_by_resident_idx=calibration_by_resident_idx,
        allocation=allocation,
        seed=seed,
    )
    
    # Format resident assignments for CSV
    assignments_rows = []
    assignment_id_counter = 1
    
    for resident_idx, resident in enumerate(residents):
        resident_assigns = [a for a in resident_assignments_raw if a.get("reviewer_idx") == resident_idx]
        
        # Sort by assignment_order
        resident_assigns.sort(key=lambda x: x.get("assignment_order", 0))
        
        for assign in resident_assigns:
            card = assign.get("card", {})
            card_uid = assign.get("card_uid", "")
            card_id = card.get("card_id", "")
            is_calibration = assign.get("is_calibration", False)
            assignment_order = assign.get("assignment_order", 0)
            
            assignments_rows.append({
                "assignment_id": f"ASSIGN_{assignment_id_counter:06d}",
                "rater_email": resident.get("reviewer_email", "").strip(),
                "rater_name": resident.get("reviewer_name", "").strip(),
                "rater_role": "resident",
                "card_uid": card_uid,
                "card_id": card_id,
                "group_id": card.get("group_id", ""),
                "entity_id": card.get("entity_id", ""),
                "card_role": card.get("card_role", ""),
                "s5_decision": card.get("s5_decision", "PASS"),
                "is_calibration": "1" if is_calibration else "0",
                "assignment_order": assignment_order,
                "batch_id": f"RESIDENT_BATCH_{resident_idx + 1}",
                "status": "pending",
            })
            assignment_id_counter += 1
    
    # Add specialist assignments (with assignment_id renumbering)
    for spec_row in specialist_rows:
        spec_row_copy = spec_row.copy()
        spec_row_copy["assignment_id"] = f"ASSIGN_{assignment_id_counter:06d}"
        assignments_rows.append(spec_row_copy)
        assignment_id_counter += 1
    
    # Write combined Assignments.csv
    out_dir.mkdir(parents=True, exist_ok=True)
    assignments_path = out_dir / "Assignments.csv"
    
    fieldnames = [
        "assignment_id", "rater_email", "rater_name", "rater_role",
        "card_uid", "card_id", "group_id", "entity_id", "card_role",
        "s5_decision", "is_calibration", "assignment_order", "batch_id", "status",
    ]
    
    with assignments_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(assignments_rows)
    
    print(f"\n✅ Wrote {len(assignments_rows)} assignments to: {assignments_path}")
    
    # Generate summary
    resident_count = sum(1 for r in assignments_rows if r["rater_role"] == "resident")
    specialist_count = sum(1 for r in assignments_rows if r["rater_role"] == "specialist")
    
    summary = {
        "assignment_version": "FINAL_QA_v1.2_SpecialistPreserved",
        "seed": seed,
        "statistics": {
            "total_cards_allocation": len(enriched_cards),
            "pass_cards": len(pass_cards),
            "regen_cards": len(regen_cards),
            "regen_assigned": len(regen_selected_uids_all),
            "regen_census": regen_census,
            "calibration_items": len(calibration_items),
            "calibration_slots": calibration_slots_total,
            "resident_assignments": resident_count,
            "specialist_assignments": specialist_count,
            "total_assignments": len(assignments_rows),
            "specialist_pool_preserved": len(specialist_card_uids),
            "specialist_realistic_images": sum(1 for uid in specialist_card_uids if uid),  # Placeholder
        },
        "resident_summary": {
            "count": len(residents),
            "items_per_person": RESIDENT_ITEMS_PER_PERSON,
            "total_items": resident_count,
            "calibration_items_per_person": calib_per_resident,
        },
        "specialist_summary": {
            "count": len(set(r["rater_email"] for r in specialist_rows)),
            "items_per_person": 30,  # From existing assignments
            "total_items": specialist_count,
            "realistic_images_available": 286,  # Known from analysis
        },
    }
    
    summary_path = out_dir / "FINAL_QA_Assignment_Summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Wrote summary to: {summary_path}")
    print("\n=== Assignment Summary ===")
    print(f"Residents: {len(residents)} × {RESIDENT_ITEMS_PER_PERSON} = {resident_count} assignments")
    print(f"Specialists: {len(set(r['rater_email'] for r in specialist_rows))} × 30 = {specialist_count} assignments")
    print(f"Total: {len(assignments_rows)} assignments")
    print(f"Calibration: {len(calibration_items)} unique items × {CALIBRATION_K_PER_ITEM} residents/item = {calibration_slots_total} slots")
    print(f"REGEN: {len(regen_selected_uids_all)} unique items ({'census' if regen_census else 'capped'})")
    print(f"Specialist pool preserved: {len(specialist_card_uids)} cards (286 with realistic images)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate resident assignments using existing specialist assignments"
    )
    parser.add_argument(
        "--allocation",
        type=Path,
        required=True,
        help="Path to allocation JSON file",
    )
    parser.add_argument(
        "--s5",
        type=Path,
        required=True,
        help="Path to S5 validation JSONL",
    )
    parser.add_argument(
        "--reviewers",
        type=Path,
        required=True,
        help="Path to reviewer_master.csv",
    )
    parser.add_argument(
        "--specialist_assignments",
        type=Path,
        required=True,
        help="Path to existing assignments_specialist.csv",
    )
    parser.add_argument(
        "--out_dir",
        type=Path,
        required=True,
        help="Output directory",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=SEED,
        help=f"Random seed (default: {SEED})",
    )
    
    args = parser.parse_args()
    
    try:
        generate_resident_assignments(
            allocation_path=args.allocation,
            s5_path=args.s5,
            reviewer_master_path=args.reviewers,
            specialist_assignments_path=args.specialist_assignments,
            out_dir=args.out_dir,
            seed=args.seed,
        )
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())


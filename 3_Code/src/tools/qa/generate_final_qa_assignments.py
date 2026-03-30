#!/usr/bin/env python3
"""
Generate FINAL QA assignments for residents and specialists.

This script implements the FINAL QA assignment strategy as defined in:
- FINAL_QA_Assignment_Handover.md
- S5_Decision_Definition_Canonical.md

Key features:
- REGEN census review (≤200 items) or cap (>200 items)
- Calibration: 33 unique items (11 specialties × 3) assigned to 3 residents/item (partial overlap)
- Resident assignment: 1,350 items total (9 residents × 150 items)
- Specialist assignment: 330 items total (11 specialists × 30 items, by specialty)
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
SPECIALIST_COUNT = 11
SPECIALIST_ITEMS_PER_PERSON = 30
SPECIALIST_TOTAL_ITEMS = SPECIALIST_COUNT * SPECIALIST_ITEMS_PER_PERSON  # 330
REGEN_CENSUS_THRESHOLD = 200

# Specialty mapping: Korean subspecialty name -> English specialty code
SPECIALTY_MAPPING = {
    "신경두경부영상": "neuro_hn_imaging",
    "유방영상": "breast_rad",
    "흉부영상": "thoracic_radiology",
    "인터벤션": "interventional_radiology",
    "근골격영상": "musculoskeletal_radiology",
    "비뇨생식기영상": "gu_radiology",
    "심장영상": "cardiovascular_rad",
    "복부영상": "abdominal_radiology",
    "물리": "physics_qc_informatics",
    "소아영상": "pediatric_radiology",
    "핵의학": "nuclear_med",
}


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
                    "s5_regeneration_trigger_score": card.get("s5_regeneration_trigger_score") or card.get("regeneration_trigger_score"),
                    "s5_was_regenerated": card.get("s5_was_regenerated") or card.get("was_regenerated"),
                }
                
                # Determine S5 decision
                s5_record["s5_decision"] = determine_s5_decision(s5_record)
                s5_index[card_uid] = s5_record
    elif s5_path.suffix == ".csv":
        # Load from CSV
        for row in _read_csv(s5_path):
            card_uid = row.get("card_uid", "").strip()
            if not card_uid:
                continue
            
            s5_record = {
                "card_uid": card_uid,
                "card_id": row.get("card_id", "").strip(),
                "group_id": row.get("group_id", "").strip(),
                "s5_regeneration_trigger_score": row.get("s5_regeneration_trigger_score") or row.get("regeneration_trigger_score"),
                "s5_was_regenerated": row.get("s5_was_regenerated") or row.get("was_regenerated"),
            }
            
            # Use existing s5_decision if present, otherwise determine
            s5_decision = row.get("s5_decision", "").strip()
            if s5_decision in ("PASS", "REGEN"):
                s5_record["s5_decision"] = s5_decision
            else:
                s5_record["s5_decision"] = determine_s5_decision(s5_record)
            
            s5_index[card_uid] = s5_record
    
    return s5_index


def load_reviewers(reviewer_master_path: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Load reviewer master CSV.
    
    Returns:
        (residents, specialists) - Lists of reviewer records
    """
    reviewers = _read_csv(reviewer_master_path)
    residents = []
    specialists = []
    
    for reviewer in reviewers:
        role = reviewer.get("role", "").strip().lower()
        if role == "resident":
            residents.append(reviewer)
        elif role == "attending":
            # Map Korean subspecialty to English code
            subspecialty_kr = reviewer.get("subspecialty", "").strip()
            specialty_code = SPECIALTY_MAPPING.get(subspecialty_kr, "")
            reviewer["specialty_code"] = specialty_code
            specialists.append(reviewer)
    
    return residents, specialists


def get_card_uid_from_allocation(card: Dict[str, Any]) -> str:
    """
    Extract card_uid from allocation card record.
    
    Allocation card_id format: "{group_id}__{entity_id}__C{01|02}"
    S5 card_id format: "{entity_id}__{card_role}__{card_idx}"
    card_uid format: "{group_id}::{entity_id}__{card_role}__{card_idx}"
    """
    group_id = card.get("group_id", "")
    card_id = card.get("card_id", "")
    entity_id = card.get("entity_id", "")
    card_role = card.get("card_role", "")
    
    # Parse card_id if it's in allocation format "group_id__entity_id__C01"
    if card_id and "__" in card_id:
        parts = card_id.split("__")
        if len(parts) >= 3:
            # Check if first part is group_id
            if parts[0] == group_id:
                # Format: "group_id__entity_id__C01"
                entity_id = parts[1] if not entity_id else entity_id
                card_suffix = parts[2]  # "C01" or "C02"
                # Convert C01/C02 to Q1/Q2 and card_idx
                if card_suffix.startswith("C"):
                    card_num = card_suffix[1:]
                    try:
                        card_num_int = int(card_num)
                        card_role = "Q1" if card_num_int == 1 else "Q2"
                        card_idx = 0 if card_num_int == 1 else 1
                    except ValueError:
                        # Fallback: use card_role from card dict
                        card_idx = 0 if card_role == "Q1" else 1
                else:
                    card_idx = 0 if card_role == "Q1" else 1
            else:
                # Format might already be "entity_id__Q1__0" or similar
                # Try to parse as S5 format
                if len(parts) >= 3:
                    entity_id = parts[0] if not entity_id else entity_id
                    card_role = parts[1] if not card_role else card_role
                    try:
                        card_idx = int(parts[2])
                    except ValueError:
                        card_idx = 0 if card_role == "Q1" else 1
                else:
                    # Not enough parts, use defaults
                    card_idx = 0 if card_role == "Q1" else 1
    
    # If we still don't have entity_id or card_role, try to construct from available data
    if not entity_id or not card_role:
        if not entity_id:
            entity_id = card.get("entity_id", "")
        if not card_role:
            card_role = card.get("card_role", "")
        if not card_role:
            # Default to Q1 if unknown
            card_role = "Q1"
        card_idx = 0 if card_role == "Q1" else 1
    
    # Construct S5-format card_id: "entity_id__card_role__card_idx"
    if entity_id and card_role:
        s5_card_id = f"{entity_id}__{card_role}__{card_idx}"
        if group_id:
            return f"{group_id}::{s5_card_id}"
    
    return ""


def get_group_specialty(allocation: Dict[str, Any], group_id: str) -> str:
    """Get specialty for a group from allocation."""
    group_allocation = allocation.get("group_allocation", {})
    group_info = group_allocation.get(group_id, {})
    return group_info.get("specialty", "").strip()


def get_cluster_id(card: Dict[str, Any], allocation: Dict[str, Any]) -> str:
    """
    Get cluster ID (Objective) for a card.
    
    Uses group_id as cluster identifier (can be enhanced with objective_bullets if available).
    """
    group_id = card.get("group_id", "")
    if group_id:
        # Use group_id as cluster (can be enhanced with objective_bullets from S1)
        return group_id
    return "unknown"


def cluster_aware_shuffle(cards: List[Dict[str, Any]], allocation: Dict[str, Any], seed: int) -> List[Dict[str, Any]]:
    """
    Shuffle cards while interleaving across clusters (Objective/group_id) to reduce local correlation.
    Deterministic for a given seed and input.
    """
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


def select_specialist_pool(
    *,
    cards: List[Dict[str, Any]],
    specialists: List[Dict[str, Any]],
    allocation: Dict[str, Any],
    seed: int,
) -> List[Dict[str, Any]]:
    """
    Select 330 specialist assignments (11 specialists × 30), specialty-matched.

    Note: This is intentionally computed BEFORE calibration selection because calibration
    items must be drawn from the specialist 330 pool (to guarantee Realistic inclusion).
    """
    random.seed(seed)
    cards_by_specialty: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for c in cards:
        gid = c.get("group_id", "")
        spec = get_group_specialty(allocation, gid)
        if spec:
            cards_by_specialty[spec].append(c)

    specialist_assignments: List[Dict[str, Any]] = []
    used_uids: Set[str] = set()
    for specialist in specialists:
        specialty_code = specialist.get("specialty_code", "").strip()
        if not specialty_code:
            continue

        candidates = [c for c in cards_by_specialty.get(specialty_code, []) if c.get("card_uid") and c["card_uid"] not in used_uids]
        regen = [c for c in candidates if c.get("s5_decision") == "REGEN"]
        pas = [c for c in candidates if c.get("s5_decision") != "REGEN"]

        selected: List[Dict[str, Any]] = []
        need = SPECIALIST_ITEMS_PER_PERSON
        if regen:
            selected.extend(random.sample(regen, min(len(regen), need)))
        remain = need - len(selected)
        if remain > 0 and pas:
            selected.extend(random.sample(pas, min(len(pas), remain)))

        if len(selected) < need:
            raise ValueError(
                f"Insufficient cards for specialist specialty={specialty_code}: "
                f"need {need}, have {len(selected)} (candidates={len(candidates)})"
            )

        for assignment_order, card in enumerate(selected):
            card_uid = card.get("card_uid", "")
            if not card_uid:
                continue
            used_uids.add(card_uid)
            specialist_assignments.append(
                {
                    "specialist": specialist,
                    "card_uid": card_uid,
                    "card": card,
                    "assignment_order": assignment_order,
                }
            )

    return specialist_assignments


def select_calibration_items_from_specialist_pool(
    *,
    specialist_assignments: List[Dict[str, Any]],
    seed: int,
) -> List[Dict[str, Any]]:
    """
    Select 33 unique calibration items (11 specialties × 3) FROM the specialist 330 pool.
    """
    random.seed(seed)
    by_specialty: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for a in specialist_assignments:
        specialist = a.get("specialist") or {}
        specialty_code = (specialist.get("specialty_code") or "").strip()
        card = a.get("card") or {}
        card_uid = card.get("card_uid") or a.get("card_uid") or ""
        if not specialty_code or not card_uid:
            continue
        # Ensure card has card_uid embedded for downstream logic
        if not card.get("card_uid"):
            card["card_uid"] = card_uid
        by_specialty[specialty_code].append(card)

    calibration_cards: List[Dict[str, Any]] = []
    used: Set[str] = set()
    specialty_codes = list(SPECIALTY_MAPPING.values())
    for specialty_code in specialty_codes:
        pool = [c for c in by_specialty.get(specialty_code, []) if c.get("card_uid") and c["card_uid"] not in used]
        if len(pool) < 3:
            raise ValueError(
                f"Insufficient specialist-pool cards to sample calibration for specialty={specialty_code}: "
                f"need 3, have {len(pool)}"
            )
        sampled = random.sample(pool, 3)
        for c in sampled:
            used.add(c["card_uid"])
        calibration_cards.extend(sampled)

    if len(calibration_cards) != CALIBRATION_ITEMS_COUNT:
        raise AssertionError(f"Calibration selection mismatch: expected {CALIBRATION_ITEMS_COUNT}, got {len(calibration_cards)}")
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

    Returns:
      reviewer_idx -> list of calibration card dicts
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
        # Prefer residents with the lowest current load, break ties randomly.
        ranked = sorted(range(num_residents), key=lambda i: (counts[i], random.random()))
        chosen: List[int] = []
        for ridx in ranked:
            if counts[ridx] >= per_resident:
                continue
            chosen.append(ridx)
            if len(chosen) == k_per_item:
                break
        if len(chosen) < k_per_item:
            raise RuntimeError("Failed to construct balanced calibration schedule (insufficient capacity)")
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
    """
    Create resident assignments with partial-overlap calibration dispersed across the 150 positions.
    """
    num_residents = len(residents)
    if num_residents <= 0:
        return []

    # Cluster-aware shuffle + round-robin to ensure exact balance.
    shuffled_noncal = cluster_aware_shuffle(non_calibration_cards, allocation, seed)
    by_resident: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(num_residents)}
    for idx, card in enumerate(shuffled_noncal):
        by_resident[idx % num_residents].append(card)

    calibration_uids: Set[str] = set()
    for ridx, cal_cards in calibration_by_resident_idx.items():
        for c in cal_cards:
            cu = c.get("card_uid") or get_card_uid_from_allocation(c)
            if cu:
                calibration_uids.add(cu)

    assignments: List[Dict[str, Any]] = []
    for ridx in range(num_residents):
        cal_cards = calibration_by_resident_idx.get(ridx, [])
        noncal_cards = by_resident.get(ridx, [])

        # Sanity: ensure we can fill exactly 150 slots.
        expected_noncal = RESIDENT_ITEMS_PER_PERSON - len(cal_cards)
        if len(noncal_cards) != expected_noncal:
            raise RuntimeError(
                f"Resident idx={ridx} non-calibration count mismatch: expected {expected_noncal}, got {len(noncal_cards)}"
            )

        # Choose random positions to place calibration items (avoid bunching at the front).
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
            card_uid = card.get("card_uid") or get_card_uid_from_allocation(card)
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

    # Guard against accidental leakage of calibration items into non-calibration pool for the same resident.
    # (We already exclude calibration cards from non-calibration selection upstream.)
    return assignments


def generate_assignments(
    allocation_path: Path,
    s5_path: Path,
    reviewer_master_path: Path,
    out_dir: Path,
    seed: int = SEED,
) -> None:
    """
    Generate FINAL QA assignments.
    
    Args:
        allocation_path: Path to allocation JSON file
        s5_path: Path to S5 validation JSONL or CSV
        reviewer_master_path: Path to reviewer_master.csv
        out_dir: Output directory for Assignments.csv and summary JSON
        seed: Random seed (default: 20260101)
    """
    print(f"Loading allocation from: {allocation_path}")
    allocation = load_allocation_json(allocation_path)
    
    print(f"Loading S5 validation from: {s5_path}")
    s5_index = load_s5_validation(s5_path)
    
    print(f"Loading reviewers from: {reviewer_master_path}")
    residents, specialists = load_reviewers(reviewer_master_path)
    
    print(f"Found {len(residents)} residents, {len(specialists)} specialists")
    
    # Get selected cards from allocation
    selected_cards = allocation.get("selected_cards", [])
    print(f"Total selected cards: {len(selected_cards)}")
    
    # Enrich cards with S5 decision
    enriched_cards = []
    for card in selected_cards:
        card_uid = get_card_uid_from_allocation(card)
        if card_uid:
            s5_record = s5_index.get(card_uid, {})
            card["s5_decision"] = s5_record.get("s5_decision", "PASS")
            card["card_uid"] = card_uid
            enriched_cards.append(card)
        else:
            print(f"Warning: Could not determine card_uid for card: {card}")
    
    # Separate by S5 decision
    pass_cards = [c for c in enriched_cards if c.get("s5_decision") == "PASS"]
    regen_cards = [c for c in enriched_cards if c.get("s5_decision") == "REGEN"]
    
    print(f"PASS cards: {len(pass_cards)}, REGEN cards: {len(regen_cards)}")
    num_residents = len(residents)
    num_specialists = len(specialists)
    resident_total_slots = num_residents * RESIDENT_ITEMS_PER_PERSON
    specialist_total_slots = num_specialists * SPECIALIST_ITEMS_PER_PERSON
    if num_residents != RESIDENT_COUNT:
        print(f"[WARN] Expected {RESIDENT_COUNT} residents, found {num_residents} (using actual count)")
    if num_specialists != SPECIALIST_COUNT:
        print(f"[WARN] Expected {SPECIALIST_COUNT} specialists, found {num_specialists} (using actual count)")

    # Step 1: Build specialist 330 pool FIRST (specialty-matched).
    specialist_assignments_raw = select_specialist_pool(
        cards=enriched_cards,
        specialists=specialists,
        allocation=allocation,
        seed=seed,
    )
    specialist_pool_uids = {a["card_uid"] for a in specialist_assignments_raw if a.get("card_uid")}
    specialist_pool_cards_by_uid = {a["card_uid"]: a["card"] for a in specialist_assignments_raw if a.get("card_uid")}
    print(f"Specialist pool: {len(specialist_assignments_raw)} assignments, {len(specialist_pool_uids)} unique cards")

    # Step 2: Select calibration items from specialist pool (11 specialties × 3 = 33).
    calibration_items = select_calibration_items_from_specialist_pool(
        specialist_assignments=specialist_assignments_raw,
        seed=seed,
    )
    calibration_card_uids = {c.get("card_uid") or get_card_uid_from_allocation(c) for c in calibration_items}
    calibration_card_uids = {u for u in calibration_card_uids if u}
    print(f"Calibration items: {len(calibration_items)} unique items (from specialist pool)")

    # Step 3: Build balanced partial-overlap calibration schedule for residents.
    calibration_by_resident_idx = create_balanced_calibration_schedule(
        calibration_cards=calibration_items,
        num_residents=num_residents,
        k_per_item=CALIBRATION_K_PER_ITEM,
        seed=seed,
    )
    calibration_slots_total = len(calibration_items) * CALIBRATION_K_PER_ITEM  # 99
    calib_per_resident = calibration_slots_total // num_residents
    if any(len(v) != calib_per_resident for v in calibration_by_resident_idx.values()):
        raise RuntimeError("Calibration schedule per-resident count mismatch")
    print(f"Calibration slots: {calibration_slots_total} (k={CALIBRATION_K_PER_ITEM}), per resident: {calib_per_resident}")

    # Step 4: REGEN processing (census or cap) on ALL regen cards, but do not double-assign
    # items that are already in calibration set.
    random.seed(seed)
    if len(regen_cards) <= REGEN_CENSUS_THRESHOLD:
        regen_selected_all = regen_cards
        regen_selected_count_all = len(regen_cards)
        regen_census = True
        print(f"REGEN census: {regen_selected_count_all} unique items (full review)")
    else:
        regen_selected_all = random.sample(regen_cards, REGEN_CENSUS_THRESHOLD)
        regen_selected_count_all = REGEN_CENSUS_THRESHOLD
        regen_census = False
        print(f"REGEN cap: {regen_selected_count_all} unique items (sampled from {len(regen_cards)})")

    regen_selected_uids_all = {c.get("card_uid") for c in regen_selected_all if c.get("card_uid")}
    regen_selected_uids_noncal = regen_selected_uids_all - calibration_card_uids
    regen_selected_noncal_cards = [c for c in regen_selected_all if c.get("card_uid") in regen_selected_uids_noncal]

    # Step 5: Ensure 100% overlap: all specialist pool cards must appear in resident assignments at least once.
    specialist_pool_noncal_uids = specialist_pool_uids - calibration_card_uids

    # Step 6: Compute remaining resident slots and fill with PASS (excluding duplicates and calibration).
    non_calibration_slots_total = resident_total_slots - calibration_slots_total  # 1,251
    base_noncal_uids = set(regen_selected_uids_noncal) | set(specialist_pool_noncal_uids)
    # Build index for stable lookups + reproducibility
    enriched_by_uid = {c.get("card_uid"): c for c in enriched_cards if c.get("card_uid")}
    base_noncal_uids_sorted = sorted(uid for uid in base_noncal_uids if uid in enriched_by_uid)
    missing_base = sorted(uid for uid in base_noncal_uids if uid not in enriched_by_uid)
    if missing_base:
        raise RuntimeError(f"Missing card records for {len(missing_base)} base non-calibration uids. e.g. {missing_base[:3]}")
    base_noncal_cards = [enriched_by_uid[uid] for uid in base_noncal_uids_sorted]

    remaining_slots = non_calibration_slots_total - len(base_noncal_uids)
    if remaining_slots < 0:
        raise RuntimeError(
            f"Base non-calibration set exceeds available slots: base={len(base_noncal_uids)}, "
            f"slots={non_calibration_slots_total}"
        )

    pass_candidates = [
        c for c in pass_cards
        if c.get("card_uid")
        and c["card_uid"] not in calibration_card_uids
        and c["card_uid"] not in base_noncal_uids
    ]
    if len(pass_candidates) < remaining_slots:
        print(f"[WARN] PASS candidates insufficient: need {remaining_slots}, have {len(pass_candidates)} (will use all)")
        remaining_slots = len(pass_candidates)
    assigned_pass = random.sample(pass_candidates, remaining_slots) if remaining_slots > 0 else []

    resident_noncal_cards = base_noncal_cards + assigned_pass
    if len(resident_noncal_cards) != non_calibration_slots_total:
        raise RuntimeError(
            f"Resident non-calibration pool size mismatch: expected {non_calibration_slots_total}, got {len(resident_noncal_cards)}"
        )

    print(
        "Resident allocation (slots): "
        f"Calibration={calibration_slots_total}, "
        f"Non-calibration={non_calibration_slots_total} "
        f"(REGEN_unique_reviewed={len(regen_selected_uids_all)}, "
        f"REGEN_noncal_slots={len(regen_selected_uids_noncal)}, "
        f"Specialist_pool_noncal_unique={len(specialist_pool_noncal_uids)}, "
        f"PASS_fill={len(assigned_pass)})"
    )

    # Step 7: Distribute resident assignments with partial-overlap calibration + position randomization.
    resident_assignments_raw = distribute_with_partial_calibration(
        non_calibration_cards=resident_noncal_cards,
        residents=residents,
        calibration_by_resident_idx=calibration_by_resident_idx,
        allocation=allocation,
        seed=seed,
    )
    
    # Step 8: Format assignments for CSV output
    out_dir.mkdir(parents=True, exist_ok=True)
    assignments_path = out_dir / "Assignments.csv"
    
    assignments_rows = []
    assignment_id_counter = 1
    
    # Resident assignments
    for resident_idx, resident in enumerate(residents):
        resident_assigns = [a for a in resident_assignments_raw if a.get("reviewer_idx") == resident_idx]
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
    
    # Specialist assignments
    for assign in specialist_assignments_raw:
        specialist = assign.get("specialist", {})
        card = assign.get("card", {})
        card_uid = assign.get("card_uid", "")
        card_id = card.get("card_id", "")
        assignment_order = assign.get("assignment_order", 0)
        
        assignments_rows.append({
            "assignment_id": f"ASSIGN_{assignment_id_counter:06d}",
            "rater_email": specialist.get("reviewer_email", "").strip(),
            "rater_name": specialist.get("reviewer_name", "").strip(),
            "rater_role": "specialist",
            "card_uid": card_uid,
            "card_id": card_id,
            "group_id": card.get("group_id", ""),
            "entity_id": card.get("entity_id", ""),
            "card_role": card.get("card_role", ""),
            "s5_decision": card.get("s5_decision", "PASS"),
            "is_calibration": "1" if card_uid in calibration_card_uids else "0",
            "assignment_order": assignment_order,
            "batch_id": f"SPECIALIST_{specialist.get('specialty_code', 'UNKNOWN')}",
            "status": "pending",
        })
        assignment_id_counter += 1
    
    # Write Assignments.csv
    fieldnames = [
        "assignment_id", "rater_email", "rater_name", "rater_role",
        "card_uid", "card_id", "group_id", "entity_id", "card_role",
        "s5_decision", "is_calibration", "assignment_order", "batch_id", "status",
    ]
    
    with assignments_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(assignments_rows)
    
    print(f"Wrote {len(assignments_rows)} assignments to: {assignments_path}")
    
    # Generate summary JSON
    summary = {
        "assignment_version": "FINAL_QA_v1.0",
        "seed": seed,
        "generation_timestamp": str(Path(__file__).stat().st_mtime),
        "statistics": {
            "total_cards": len(enriched_cards),
            "pass_cards": len(pass_cards),
            "regen_cards": len(regen_cards),
            # Unique REGEN items selected for review (census or cap). Some may be in calibration set.
            "regen_assigned": len(regen_selected_uids_all),
            "regen_noncal_slots": len(regen_selected_uids_noncal),
            "regen_census": regen_census,
            "calibration_items": len(calibration_items),
            "calibration_slots": calibration_slots_total,
            "resident_assignments": len([a for a in assignments_rows if a["rater_role"] == "resident"]),
            "specialist_assignments": len([a for a in assignments_rows if a["rater_role"] == "specialist"]),
            "total_assignments": len(assignments_rows),
        },
        "resident_summary": {
            "count": num_residents,
            "items_per_person": RESIDENT_ITEMS_PER_PERSON,
            "total_items": resident_total_slots,
            "calibration_items_per_person": calib_per_resident,
        },
        "specialist_summary": {
            "count": num_specialists,
            "items_per_person": SPECIALIST_ITEMS_PER_PERSON,
            "total_items": specialist_total_slots,
        },
    }
    
    summary_path = out_dir / "FINAL_QA_Assignment_Summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"Wrote summary to: {summary_path}")
    print("\n=== Assignment Summary ===")
    print(f"Residents: {len(residents)} × {RESIDENT_ITEMS_PER_PERSON} = {summary['statistics']['resident_assignments']} assignments")
    print(f"Specialists: {len(specialists)} × {SPECIALIST_ITEMS_PER_PERSON} = {summary['statistics']['specialist_assignments']} assignments")
    print(f"Total: {summary['statistics']['total_assignments']} assignments")
    print(f"Calibration: {len(calibration_items)} unique items × {CALIBRATION_K_PER_ITEM} residents/item = {calibration_slots_total} slots")
    print(f"REGEN: {len(regen_selected_uids_all)} unique items ({'census' if regen_census else 'capped'})")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate FINAL QA assignments for residents and specialists"
    )
    parser.add_argument(
        "--allocation",
        type=Path,
        required=True,
        help="Path to allocation JSON file (final_distribution_allocation__6000cards.json)",
    )
    parser.add_argument(
        "--s5",
        type=Path,
        required=True,
        help="Path to S5 validation file (JSONL or CSV)",
    )
    parser.add_argument(
        "--reviewers",
        type=Path,
        required=True,
        help="Path to reviewer_master.csv",
    )
    parser.add_argument(
        "--out_dir",
        type=Path,
        required=True,
        help="Output directory for Assignments.csv and summary JSON",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=SEED,
        help=f"Random seed (default: {SEED})",
    )
    
    args = parser.parse_args()
    
    try:
        generate_assignments(
            allocation_path=args.allocation,
            s5_path=args.s5,
            reviewer_master_path=args.reviewers,
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


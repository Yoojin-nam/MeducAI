"""
FINAL Distribution Allocation Module
------------------------------------
단순한 규칙 기반 allocation 구현:

1. 핵의학: entity 개수만큼만 출제
   - 절반 entity는 Q1만, 절반 entity는 Q2만
2. 나머지: 시험 출제 비중에 맞춰 할당
3. Entity가 적은 specialty는 최대한 Q2까지 모두 선택
"""

from __future__ import annotations

import json
import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime


# =========================
# Constants
# =========================

TARGET_TOTAL_CARDS = 6000
ALLOCATION_VERSION = "FINAL-Distribution-v2.1"  # v2.1: Exclude entities with missing images
RUN_TAG = "FINAL_DISTRIBUTION"
ARM = "G"

# Entities to exclude (missing images that cannot be generated)
# Format: (group_id, entity_id)
EXCLUDED_ENTITIES = [
    ("grp_39228fc2c9", "DERIVED:d0d3b4eec338"),  # Balloon Angioplasty - Q2 image missing
    ("grp_f828f41eac", "DERIVED:fcfeb43c3b76"),  # Invasive Lobular Carcinoma - Q1 image missing
]

# 실제 시험 출제 비율
QUESTION_PLAN = {
    'thoracic_radiology': 24,
    'cardiovascular_rad': 11,
    'interventional_radiology': 14,
    'abdominal_radiology': 31,
    'gu_radiology': 17,
    'neuro_hn_imaging': 25,
    'musculoskeletal_radiology': 21,
    'pediatric_radiology': 17,
    'breast_rad': 14,
    'nuclear_med': 4,
    'physics_qc_informatics': 22,
}


# =========================
# Data Models
# =========================

@dataclass
class SelectedCard:
    """Represents a selected card for allocation."""
    group_id: str
    entity_id: str
    entity_name: str
    card_role: str  # "Q1" or "Q2"
    selection_reason: str


# =========================
# Data Loading
# =========================

def load_data(base_dir: Path) -> Tuple[Dict, Dict]:
    """Load groups canonical and S1 data."""
    groups_canonical = {}
    with open(base_dir / "2_Data" / "metadata" / "groups_canonical.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            groups_canonical[row['group_id']] = {
                'specialty': row['specialty'],
                'group_weight_sum': float(row['group_weight_sum']),
            }
    
    s1_data = {}
    with open(base_dir / "2_Data" / "metadata" / "generated" / "FINAL_DISTRIBUTION" / "stage1_struct__armG.jsonl", 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                record = json.loads(line)
                s1_data[record['group_id']] = {
                    'entity_list': record.get('entity_list', []),
                }
    
    return groups_canonical, s1_data


# =========================
# Hamilton Method
# =========================

def hamilton_allocate(weights: Dict[str, float], total: int) -> Dict[str, int]:
    """Hamilton (largest remainder) method for allocation."""
    keys = list(weights.keys())
    wsum = sum(weights.values())
    if wsum <= 0:
        raise ValueError("Sum of weights must be > 0")
    
    quotas = {k: (weights[k] / wsum) * total for k in keys}
    floors = {k: int(quotas[k] // 1) for k in keys}
    rem = total - sum(floors.values())
    remainders = sorted(((quotas[k] - floors[k], k) for k in keys), reverse=True)
    
    out = dict(floors)
    for i in range(rem):
        _, k = remainders[i]
        out[k] += 1
    
    return out


# =========================
# Card Selection
# =========================

def _is_excluded(group_id: str, entity_id: str) -> bool:
    """Check if entity should be excluded from allocation."""
    return (group_id, entity_id) in EXCLUDED_ENTITIES


def select_cards_simple(
    groups_canonical: Dict,
    s1_data: Dict,
    target_total: int,
    must_include_card_uids: List[str] = None
) -> List[SelectedCard]:
    """
    단순한 규칙 기반 카드 선택:
    0. must_include_card_uids에 있는 카드는 무조건 포함 (specialist pool 보장)
    1. 핵의학: entity 개수만큼만 (절반 Q1만, 절반 Q2만)
    2. 나머지: 시험 비중에 맞춰 할당
    3. Entity 적은 specialty는 Q2까지 모두 선택
    
    Note: EXCLUDED_ENTITIES에 있는 entity는 제외됨
    """
    selected_cards = []
    excluded_count = 0
    must_include_set = set(must_include_card_uids or [])
    
    # 0. must_include 카드 먼저 추가 (specialist pool 보장)
    must_include_added = []
    if must_include_set:
        print(f"  Guaranteeing {len(must_include_set)} must-include cards (specialist pool)...")
        for group_id in groups_canonical.keys():
            entities = s1_data.get(group_id, {}).get('entity_list', [])
            for entity in entities:
                entity_id = entity.get('entity_id', '')
                if _is_excluded(group_id, entity_id):
                    continue
                
                # Check Q1
                card_idx = 0
                card_uid = f"{group_id}::{entity_id}__Q1__{card_idx}"
                if card_uid in must_include_set:
                    selected_cards.append(SelectedCard(
                        group_id=group_id,
                        entity_id=entity_id,
                        entity_name=entity.get('entity_name', ''),
                        card_role='Q1',
                        selection_reason='specialist_pool_guarantee'
                    ))
                    must_include_added.append(card_uid)
                
                # Check Q2
                card_idx = 1
                card_uid = f"{group_id}::{entity_id}__Q2__{card_idx}"
                if card_uid in must_include_set:
                    selected_cards.append(SelectedCard(
                        group_id=group_id,
                        entity_id=entity_id,
                        entity_name=entity.get('entity_name', ''),
                        card_role='Q2',
                        selection_reason='specialist_pool_guarantee'
                    ))
                    must_include_added.append(card_uid)
        
        print(f"  Added {len(must_include_added)} must-include cards")
        if len(must_include_added) != len(must_include_set):
            missing = must_include_set - set(must_include_added)
            print(f"  [WARN] Could not find {len(missing)} must-include cards in S1 data")
            for uid in list(missing)[:5]:
                print(f"    - {uid}")
    
    # Track already selected (group_id, entity_id, card_role) to avoid duplicates
    already_selected = {(sc.group_id, sc.entity_id, sc.card_role) for sc in selected_cards}
    
    # 1. 핵의학 처리: entity 개수만큼만 (이미 선택된 것 제외)
    nuclear_med_entities = []
    for group_id, group_data in groups_canonical.items():
        if group_data['specialty'] == 'nuclear_med':
            entities = s1_data.get(group_id, {}).get('entity_list', [])
            for entity in entities:
                entity_id = entity.get('entity_id', '')
                if _is_excluded(group_id, entity_id):
                    excluded_count += 1
                    continue
                nuclear_med_entities.append((group_id, entity))
    
    # 핵의학: 절반은 Q1만, 절반은 Q2만 (이미 선택된 것 제외)
    nuclear_count = len(nuclear_med_entities)
    half = nuclear_count // 2
    
    for i, (group_id, entity) in enumerate(nuclear_med_entities):
        entity_id = entity.get('entity_id', '')
        if i < half:
            # Q1
            if (group_id, entity_id, 'Q1') not in already_selected:
                selected_cards.append(SelectedCard(
                    group_id=group_id,
                    entity_id=entity_id,
                    entity_name=entity.get('entity_name', ''),
                    card_role='Q1',
                    selection_reason='nuclear_med_q1_only'
                ))
        else:
            # Q2
            if (group_id, entity_id, 'Q2') not in already_selected:
                selected_cards.append(SelectedCard(
                    group_id=group_id,
                    entity_id=entity_id,
                    entity_name=entity.get('entity_name', ''),
                    card_role='Q2',
                    selection_reason='nuclear_med_q2_only'
                ))
    
    remaining_target = target_total - nuclear_count
    
    # Update already_selected after nuclear_med
    already_selected = {(sc.group_id, sc.entity_id, sc.card_role) for sc in selected_cards}
    
    # 2. 나머지 specialty에 시험 비중에 맞춰 할당 (이미 선택된 카드 고려)
    remaining_target = target_total - len(selected_cards)
    
    weights_without_nuclear = {
        spec: float(count) for spec, count in QUESTION_PLAN.items()
        if spec != 'nuclear_med'
    }
    specialty_allocation = hamilton_allocate(weights_without_nuclear, remaining_target)
    
    # 3. Entity 수 계산 (Entity 적은 specialty 판단용)
    specialty_entity_counts = defaultdict(int)
    for group_id, group_data in groups_canonical.items():
        specialty = group_data['specialty']
        if specialty != 'nuclear_med':
            entity_count = len(s1_data.get(group_id, {}).get('entity_list', []))
            specialty_entity_counts[specialty] += entity_count
    
    # Entity 적은 specialty: 평균보다 적으면 Q2까지 모두 선택
    avg_entities = sum(specialty_entity_counts.values()) / len(specialty_entity_counts) if specialty_entity_counts else 0
    
    # 4. 각 specialty별로 카드 선택 (이미 선택된 것 제외)
    for specialty, target in specialty_allocation.items():
        # 모든 entity 수집 (excluded 제외)
        all_entities = []
        for group_id, group_data in groups_canonical.items():
            if group_data['specialty'] == specialty:
                entities = s1_data.get(group_id, {}).get('entity_list', [])
                for entity in entities:
                    entity_id = entity.get('entity_id', '')
                    if _is_excluded(group_id, entity_id):
                        excluded_count += 1
                        continue
                    all_entities.append((group_id, entity))
        
        entity_count = specialty_entity_counts[specialty]
        fill_all_q2 = entity_count < avg_entities
        
        # 최소 보장: 모든 entity에 Q1 (이미 선택된 것 제외)
        for group_id, entity in all_entities:
            entity_id = entity.get('entity_id', '')
            if (group_id, entity_id, 'Q1') not in already_selected:
                selected_cards.append(SelectedCard(
                    group_id=group_id,
                    entity_id=entity_id,
                    entity_name=entity.get('entity_name', ''),
                    card_role='Q1',
                    selection_reason='entity_minimum_guarantee'
                ))
        
        # Update already_selected
        already_selected = {(sc.group_id, sc.entity_id, sc.card_role) for sc in selected_cards}
        
        # Q2 선택 (이미 선택된 것 제외)
        remaining = target - sum(1 for sc in selected_cards if groups_canonical.get(sc.group_id, {}).get('specialty') == specialty)
        if fill_all_q2:
            # Entity 적은 specialty: Q2까지 모두 선택
            for group_id, entity in all_entities:
                if remaining <= 0:
                    break
                entity_id = entity.get('entity_id', '')
                if (group_id, entity_id, 'Q2') not in already_selected:
                    selected_cards.append(SelectedCard(
                        group_id=group_id,
                        entity_id=entity_id,
                        entity_name=entity.get('entity_name', ''),
                        card_role='Q2',
                        selection_reason='fill_all_q2'
                    ))
                    remaining -= 1
        else:
            # 일반 specialty: 할당량에 맞춰 Q2 선택
            for group_id, entity in all_entities:
                if remaining <= 0:
                    break
                entity_id = entity.get('entity_id', '')
                if (group_id, entity_id, 'Q2') not in already_selected:
                    selected_cards.append(SelectedCard(
                        group_id=group_id,
                        entity_id=entity_id,
                        entity_name=entity.get('entity_name', ''),
                        card_role='Q2',
                        selection_reason='weight_based'
                    ))
                    remaining -= 1
    
    # 5. 정확히 6000개 맞추기
    current_total = len(selected_cards)
    difference = target_total - current_total
    
    if difference > 0:
        # 부족: Q2 추가 (Q1은 있지만 Q2가 없는 entity)
        print(f"  Adding {difference} cards to reach {target_total}...")
        q1_set = {(sc.group_id, sc.entity_id) for sc in selected_cards if sc.card_role == 'Q1'}
        q2_set = {(sc.group_id, sc.entity_id) for sc in selected_cards if sc.card_role == 'Q2'}
        
        for group_id, group_data in groups_canonical.items():
            if difference <= 0:
                break
            if group_data['specialty'] == 'nuclear_med':
                continue
            
            entities = s1_data.get(group_id, {}).get('entity_list', [])
            for entity in entities:
                if difference <= 0:
                    break
                entity_id = entity.get('entity_id', '')
                # Skip excluded entities
                if _is_excluded(group_id, entity_id):
                    continue
                if (group_id, entity_id) in q1_set and (group_id, entity_id) not in q2_set:
                    selected_cards.append(SelectedCard(
                        group_id=group_id,
                        entity_id=entity_id,
                        entity_name=entity.get('entity_name', ''),
                        card_role='Q2',
                        selection_reason='target_adjustment'
                    ))
                    difference -= 1
    
    elif difference < 0:
        # 초과: Q2 제거 (pediatric 우선)
        print(f"  Removing {abs(difference)} cards to reach {target_total}...")
        q2_cards = [sc for sc in selected_cards if sc.card_role == 'Q2' and 
                   groups_canonical.get(sc.group_id, {}).get('specialty') != 'nuclear_med']
        
        # pediatric 우선 제거
        pediatric_q2 = [sc for sc in q2_cards 
                       if groups_canonical.get(sc.group_id, {}).get('specialty') == 'pediatric_radiology']
        other_q2 = [sc for sc in q2_cards 
                   if groups_canonical.get(sc.group_id, {}).get('specialty') != 'pediatric_radiology']
        
        to_remove = abs(difference)
        for sc in pediatric_q2 + other_q2:
            if to_remove <= 0:
                break
            selected_cards.remove(sc)
            to_remove -= 1
    
    return selected_cards


# =========================
# Allocation File Generation
# =========================

def create_allocation_file(
    base_dir: Path,
    selected_cards: List[SelectedCard],
    groups_canonical: Dict
) -> Path:
    """Create allocation JSON file."""
    allocation_dir = base_dir / "2_Data" / "metadata" / "generated" / "FINAL_DISTRIBUTION" / "allocation"
    allocation_dir.mkdir(parents=True, exist_ok=True)
    
    # Calculate statistics
    specialty_counts = defaultdict(int)
    group_counts = defaultdict(int)
    for card in selected_cards:
        specialty = groups_canonical.get(card.group_id, {}).get('specialty', 'unknown')
        specialty_counts[specialty] += 1
        group_counts[card.group_id] += 1
    
    # Build selected_cards list
    selected_cards_list = []
    for card in selected_cards:
        selected_cards_list.append({
            "group_id": card.group_id,
            "entity_id": card.entity_id,
            "entity_name": card.entity_name,
            "card_role": card.card_role,
            "card_id": f"{card.group_id}__{card.entity_id}__C{'01' if card.card_role == 'Q1' else '02'}",
            "selection_reason": card.selection_reason
        })
    
    # Build allocation document
    allocation_doc = {
        "allocation_version": ALLOCATION_VERSION,
        "run_tag": RUN_TAG,
        "arm": ARM,
        "target_total_cards": TARGET_TOTAL_CARDS,
        "created_ts": datetime.now().isoformat(),
        "specialty_allocation": {
            spec: {"target": count, "actual": count}
            for spec, count in specialty_counts.items()
        },
        "group_allocation": {
            group_id: {
                "target": count,
                "specialty": groups_canonical.get(group_id, {}).get('specialty', 'unknown')
            }
            for group_id, count in group_counts.items()
        },
        "selected_cards": selected_cards_list,
        "allocation_summary": {
            "total_selected": len(selected_cards),
            "q1_count": sum(1 for sc in selected_cards if sc.card_role == 'Q1'),
            "q2_count": sum(1 for sc in selected_cards if sc.card_role == 'Q2'),
            "specialty_distribution": {
                spec: {"actual": count}
                for spec, count in specialty_counts.items()
            }
        }
    }
    
    output_file = allocation_dir / f"final_distribution_allocation__{TARGET_TOTAL_CARDS}cards.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(allocation_doc, f, indent=2, ensure_ascii=False)
    
    return output_file


# =========================
# Validation Report
# =========================

def generate_validation_report(
    base_dir: Path,
    selected_cards: List[SelectedCard],
    groups_canonical: Dict,
    allocation_file_path: Path
) -> Path:
    """Generate validation report."""
    report_dir = base_dir / "2_Data" / "metadata" / "generated" / "FINAL_DISTRIBUTION"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    specialty_counts = defaultdict(int)
    specialty_q1 = defaultdict(int)
    specialty_q2 = defaultdict(int)
    
    for card in selected_cards:
        specialty = groups_canonical.get(card.group_id, {}).get('specialty', 'unknown')
        specialty_counts[specialty] += 1
        if card.card_role == 'Q1':
            specialty_q1[specialty] += 1
        elif card.card_role == 'Q2':
            specialty_q2[specialty] += 1
    
    total_exam = sum(QUESTION_PLAN.values())
    
    report_lines = []
    report_lines.append("# FINAL Distribution Allocation Report")
    report_lines.append("")
    report_lines.append(f"**Generated:** {datetime.now().isoformat()}")
    report_lines.append(f"**Allocation File:** `{allocation_file_path.name}`")
    report_lines.append("")
    report_lines.append("## Validation Summary")
    report_lines.append("")
    report_lines.append(f"- **Target Cards:** {TARGET_TOTAL_CARDS}")
    report_lines.append(f"- **Actual Selected:** {len(selected_cards)}")
    report_lines.append(f"- **Target Match:** {'✓ PASS' if len(selected_cards) == TARGET_TOTAL_CARDS else '✗ FAIL'}")
    report_lines.append("")
    report_lines.append(f"- **Q1 Cards:** {sum(specialty_q1.values())}")
    report_lines.append(f"- **Q2 Cards:** {sum(specialty_q2.values())}")
    report_lines.append("")
    report_lines.append("## Specialty Allocation Statistics")
    report_lines.append("")
    report_lines.append("| Specialty | 시험비중 | 할당량 | 실제비중 | Q1 | Q2 |")
    report_lines.append("|-----------|----------|--------|----------|----|----|")
    
    for specialty in sorted(QUESTION_PLAN.keys()):
        exam_weight = QUESTION_PLAN[specialty]
        exam_pct = (exam_weight / total_exam * 100) if total_exam > 0 else 0
        allocated = specialty_counts.get(specialty, 0)
        allocated_pct = (allocated / len(selected_cards) * 100) if selected_cards else 0
        q1 = specialty_q1.get(specialty, 0)
        q2 = specialty_q2.get(specialty, 0)
        report_lines.append(
            f"| {specialty} | {exam_weight} ({exam_pct:.1f}%) | {allocated} ({allocated_pct:.1f}%) | {allocated_pct:.1f}% | {q1} | {q2} |"
        )
    
    report_lines.append("")
    
    report_file = report_dir / f"final_distribution_allocation_report__{TARGET_TOTAL_CARDS}cards.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    return report_file


# =========================
# Main Execution
# =========================

def main(base_dir: Path, must_include_csv: Path = None) -> None:
    """Main execution function."""
    print("=" * 60)
    print("FINAL Distribution Allocation - Simple Rules")
    print("=" * 60)
    
    print("\n[Step 1] Loading data...")
    groups_canonical, s1_data = load_data(base_dir)
    print(f"  Loaded {len(groups_canonical)} groups")
    print(f"  Loaded {len(s1_data)} groups from S1")
    
    # Load must-include cards (specialist pool)
    must_include_uids = []
    if must_include_csv and must_include_csv.exists():
        print(f"\n[Step 1b] Loading must-include cards from: {must_include_csv}")
        with must_include_csv.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                card_uid = row.get("card_uid", "").strip()
                if card_uid:
                    must_include_uids.append(card_uid)
        print(f"  Loaded {len(must_include_uids)} must-include card_uids (specialist pool)")
    
    print(f"\n[Step 2] Selecting cards with simple rules...")
    print("  Rules:")
    print("    0. Must-include cards (specialist pool): guaranteed inclusion")
    print("    1. nuclear_med: entity count only (half Q1, half Q2)")
    print("    2. Others: allocate by exam weight")
    print("    3. Low entity specialties: fill all Q2")
    if EXCLUDED_ENTITIES:
        print(f"  Excluding {len(EXCLUDED_ENTITIES)} entities with missing images:")
        for grp, ent in EXCLUDED_ENTITIES:
            print(f"    - {grp} / {ent}")
    
    selected_cards = select_cards_simple(groups_canonical, s1_data, TARGET_TOTAL_CARDS, must_include_uids)
    
    print(f"\n  Selected {len(selected_cards)} cards")
    q1_count = sum(1 for sc in selected_cards if sc.card_role == 'Q1')
    q2_count = sum(1 for sc in selected_cards if sc.card_role == 'Q2')
    print(f"    Q1: {q1_count}, Q2: {q2_count}")
    
    print("\n[Step 3] Creating allocation file...")
    allocation_file = create_allocation_file(base_dir, selected_cards, groups_canonical)
    print(f"  ✓ Created: {allocation_file}")
    
    print("\n[Step 4] Generating validation report...")
    report_file = generate_validation_report(base_dir, selected_cards, groups_canonical, allocation_file)
    print(f"  ✓ Created: {report_file}")
    
    print("\n[✓] All steps completed!")


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate FINAL Distribution 6000-card allocation")
    parser.add_argument("--base_dir", type=Path, default=None, help="Base directory")
    parser.add_argument("--must_include", type=Path, default=None, help="CSV file with must-include card_uids (specialist pool)")
    args = parser.parse_args()
    
    base_dir = args.base_dir or Path(__file__).parent.parent.parent.parent.parent
    must_include_csv = args.must_include
    
    main(base_dir, must_include_csv)

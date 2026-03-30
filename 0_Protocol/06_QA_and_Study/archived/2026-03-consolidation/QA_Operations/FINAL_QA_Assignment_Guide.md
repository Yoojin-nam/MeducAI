# FINAL QA 할당 알고리즘 가이드

**Status:** Canonical  
**Version:** 1.2  
**Last Updated:** 2026-01-04  
**Purpose:** FINAL QA 할당 알고리즘의 상세 설명 및 구현 가이드 (Specialty-Stratified Calibration 포함)

---

## 0. 개요

이 문서는 FINAL QA 단계에서 평가자(전공의 및 전문의)에게 문항을 할당하는 알고리즘을 상세히 설명합니다.

### 0.1 할당 목표

- **전공의 (Residents)**: 9명, 인당 150건, 총 1,350건
- **전문의 (Attending Physicians)**: 11명, 인당 30건, 총 330건
- **총 할당량**: 1,680건

### 0.2 핵심 설계 원칙

1. **Calibration Set (Partial Overlap)**: 30개 문항을 3명씩 평가하여 ICC 정밀도 확보 (각 전공의 10개)
2. **REGEN 전수 조사**: REGEN ≤ 200개일 때 전수 조사, > 200개일 때 200개로 제한
3. **PASS 집중 할당**: 나머지 할당량을 PASS 그룹에 집중하여 안전성 상한을 낮춤
4. **전문의 서브샘플링**: 전공의 할당분에서 100% 오버랩으로 서브샘플링
5. **분과별 할당**: 전문의는 자신의 분과에 맞는 문항 우선 할당
6. **통계적 독립성**: Cluster(Objective) 고려한 Shuffle로 통계적 독립성 확보
7. **위치 랜덤화**: Calibration 문항을 150개 내에서 랜덤 위치에 분산 (학습효과/피로효과 방지)

---

## 1. 입력 데이터

### 1.1 필수 입력 파일

1. **Allocation JSON**
   - 경로: `2_Data/metadata/generated/FINAL_DISTRIBUTION/allocation/final_distribution_allocation__6000cards.json`
   - 내용: 선택된 6,000개 카드 목록 및 메타데이터

2. **S5 판정 결과**
   - 경로: `s5_validation__armG.jsonl` 또는 `S5.csv`
   - 필수 필드:
     - `card_uid` 또는 `card_id`
     - `s5_regeneration_trigger_score` (0-100)
     - `s5_was_regenerated` (bool)
   - 파생 필드: `s5_decision` (PASS/REGEN)

3. **평가자 마스터**
   - 경로: `1_Secure_Participant_Info/reviewer_master.csv`
   - 필수 필드:
     - `reviewer_email`: 평가자 이메일
     - `role`: `resident` 또는 `attending`
     - `subspecialty`: 전문의의 경우 분과 (전공의는 빈 값)

### 1.2 S5 판정 기준

S5 판정은 `S5_Decision_Definition_Canonical.md`에 정의된 기준을 따릅니다:

- **REGEN**: 
  - `regeneration_trigger_score < 70.0` OR
  - `s5_was_regenerated == True`
- **PASS**: 그 외 모든 경우

**중요**: FLAG는 제외되며, FLAG 상태는 자동으로 REGEN으로 처리됩니다.

---

## 2. 전공의 할당 알고리즘 (총 1,350건)

### 2.1 전체 프로세스 개요

```
1. S5 판정 결과 로드 및 분류 (PASS/REGEN)
2. REGEN 처리 (전수 조사 또는 200개 Cap)
3. Calibration Set 선정 (5개 고유 문항)
4. PASS 문항 샘플링 (나머지 할당량)
5. 균등 분배 + Cluster Shuffle
```

### 2.2 Step 1: S5 판정 결과 분류

```python
# 모든 카드에 대해 S5 판정 적용
all_cards = load_cards_from_allocation(allocation_json)
s5_results = load_s5_validation_results(s5_file)

# 카드별 S5 판정 결정
for card in all_cards:
    card_uid = card['card_uid']
    s5_record = find_s5_record(s5_results, card_uid)
    card['s5_decision'] = determine_s5_decision(s5_record)

# PASS/REGEN 분류
pass_cards = [c for c in all_cards if c['s5_decision'] == 'PASS']
regen_cards = [c for c in all_cards if c['s5_decision'] == 'REGEN']
```

### 2.3 Step 2: REGEN 처리

REGEN 문항 수에 따라 전수 조사 또는 Cap 적용:

```python
total_regen_count = len(regen_cards)

if total_regen_count <= 200:
    # Case A: 전수 조사 (Census)
    assigned_regen = regen_cards.copy()  # 모든 REGEN 문항 할당
    regen_assigned_count = total_regen_count
    regen_census = True
else:
    # Case B: 200개로 제한 (Cap)
    assigned_regen = random_sample(
        regen_cards, 
        n=200, 
        seed=20260101
    )
    regen_assigned_count = 200
    regen_census = False
```

**통계적 근거**: 
- REGEN이 적을 때(≤200개): 전수 조사로 "100% 검증"이라는 강력한 결론 제공
- REGEN이 많을 때(>200개): 200개로 제한하여 실용성 확보

### 2.4 Step 3: Calibration Set 선정 (Partial Overlap, Specialty-Stratified)

**목적**: Inter-rater Consistency 측정을 위한 통계적으로 robust한 ICC 추정

**설계 변경 근거** (통계 자문 반영):
- 기존 5개×9명 설계: ICC 95% CI 폭 ≈ 0.59 (n=5가 bottleneck)
- 신규 33개×3명 설계: ICC 95% CI 폭 ≈ 0.30 (n 증가로 정밀도 개선)
- 문헌 권장: n≥30, k≥3 (Koo & Li, 2016)
- **분과별 균등 배정**: 11개 분과 × 3문제 = 33문제

```python
# 전문의 330 pool에서 분과별 3문제씩 추출 (11분과 × 3 = 33문제)
# 전문의 330에서 선택해야 Realistic 이미지 포함 보장

calibration_cards = []
for specialty in SPECIALTIES:  # 11개 분과
    specialty_cards = [c for c in specialist_330_pool if c['specialty'] == specialty]
    sampled = random_sample(specialty_cards, n=3, seed=20260101)
    calibration_cards.extend(sampled)

# Calibration에 사용된 카드는 개인 할당 풀에서 제외
remaining_pass_cards = [
    c for c in pass_cards 
    if c['card_uid'] not in {cal['card_uid'] for cal in calibration_cards}
]

# Calibration 슬롯 수: 33개 × 3명 = 99 슬롯
calibration_slots = 33 * 3  # 99
items_per_resident = 11  # 각 전공의가 받는 calibration 문항 수
```

**분과별 배정**:

| 분과 | Calibration 문항 |
|------|-----------------|
| neuro_hn_imaging | 3개 |
| breast_rad | 3개 |
| thoracic_radiology | 3개 |
| interventional_radiology | 3개 |
| musculoskeletal_radiology | 3개 |
| gu_radiology | 3개 |
| cardiovascular_rad | 3개 |
| abdominal_radiology | 3개 |
| physics_qc_informatics | 3개 |
| pediatric_radiology | 3개 |
| nuclear_med | 3개 |
| **총계** | **33개** |

**Balanced Assignment 알고리즘**:
```python
def create_balanced_calibration_schedule(
    calibration_cards: List[Dict],
    residents: List[str],
    k_per_item: int = 3,
    seed: int = 20260101
) -> Dict[str, List[str]]:
    """
    30개 문항을 9명 전공의에게 균형 배정
    - 각 문항: 정확히 3명이 평가
    - 각 전공의: 정확히 10개 문항 평가
    """
    import random
    random.seed(seed)
    
    n_items = len(calibration_cards)  # 30
    n_residents = len(residents)  # 9
    items_per_resident = (n_items * k_per_item) // n_residents  # 10
    
    # 각 전공의의 calibration 문항 리스트 초기화
    assignments = {r: [] for r in residents}
    
    # 각 문항에 대해 3명 배정
    for card in calibration_cards:
        # 아직 10개 미만인 전공의 중에서 3명 선택
        available = [r for r in residents if len(assignments[r]) < items_per_resident]
        selected = random.sample(available, k_per_item)
        for r in selected:
            assignments[r].append(card['card_uid'])
    
    return assignments
```

**설계 원칙**:
- **Partial Overlap**: 각 문항을 3명만 평가 (Full Overlap 아님)
- **균형 배정**: 모든 전공의가 정확히 10개씩 calibration 문항 평가
- **PASS 풀에서 선택**: Calibration은 PASS 문항에서만 선택 (REGEN 제외)
- **층화추출 권장**: Specialty, PASS/REGEN 비율 반영
- **분석 제외**: Calibration 문항은 primary 통계 분석에서 제외 (ICC 계산용)

### 2.5 Step 4: PASS 문항 샘플링

나머지 할당량을 PASS 문항으로 채웁니다:

```python
# 총 할당량 계산
total_allocation = 1350  # 9명 × 150건
calibration_slots = 99   # 33개 × 3명 (Specialty-Stratified)
regen_slots = regen_assigned_count

# PASS 할당량 계산
pass_needed = total_allocation - calibration_slots - regen_slots

# PASS 문항 샘플링
assigned_pass = random_sample(
    remaining_pass_cards,
    n=pass_needed,
    seed=20260101
)
```

**예시 계산**:
- 총 할당량: 1,350건
- Calibration: 99건 (33개 × 3명)
- REGEN: 100건 (예시)
- PASS: 1,350 - 99 - 100 = **1,151건**

**Unique 문항 수 계산**:
```python
# Calibration unique: 33개
# REGEN unique: 100개 (예시)
# PASS unique: 1,151개
# Total unique: 33 + 100 + 1,151 = 1,284개

# 감소량 계산: calibration_items × (k - 1)
unique_reduction = 33 × (3 - 1) = 66
total_unique = 1350 - 66 = 1,284
```

### 2.6 Step 5: 균등 분배 + Cluster Shuffle + 위치 랜덤화

모든 문항을 9명 전공의에게 균등 분배하고, Cluster(Objective)를 고려한 Shuffle을 적용합니다:

```python
# 모든 할당 문항 통합
all_assigned_cards = assigned_regen + assigned_pass

# Calibration은 별도 처리 (Partial Overlap - 각 전공의에게 10개씩)
calibration_schedule = create_balanced_calibration_schedule(
    calibration_cards,
    residents,
    k_per_item=3,
    seed=20260101
)  # {reviewer_email: [card_uid, ...]}

# Cluster(Objective) 정보 로드
# Cluster 고려한 Shuffle
shuffled_cards = cluster_aware_shuffle(
    all_assigned_cards,
    cluster_key='objective_id',
    seed=20260101
)

# 9명 전공의에게 균등 분배
residents = get_residents()  # 9명
assignments = distribute_with_partial_overlap(
    shuffled_cards,
    reviewers=residents,
    calibration_schedule=calibration_schedule
)
```

**분배 방식**:

1. **Calibration 문항 (Partial Overlap)**: 
   - 30개 문항, 각 문항을 3명에게 배정
   - 각 전공의에게 **10개** calibration 문항 할당 (균형 배정)
   - **위치 랜덤화**: 150개 내에서 랜덤 위치에 분산 (학습효과/피로효과 방지)

2. **REGEN + PASS 문항**:
   - Round Robin 방식으로 균등 분배
   - 각 전공의에게 140개 (150 - 10 calibration)

3. **Cluster Shuffle**:
   - Objective(질환 그룹)별로 Shuffle하여 통계적 독립성 확보
   - 같은 Cluster의 문항이 한 평가자에게 집중되지 않도록 분산

**구현 예시**:

```python
def distribute_with_partial_overlap(
    cards: List[Dict],
    reviewers: List[Dict],
    calibration_schedule: Dict[str, List[str]]
) -> List[Dict]:
    """
    Partial Overlap 방식으로 분배
    - Calibration: 각 전공의에게 배정된 10개 문항
    - Non-calibration: Round Robin으로 나머지 분배
    - 위치 랜덤화: Calibration을 150개 내에서 랜덤 위치에 분산
    """
    import random
    random.seed(20260101)
    
    assignments_by_reviewer = {r['reviewer_email']: [] for r in reviewers}
    
    # 1. Calibration 문항 배정 (각 전공의에게 10개)
    for reviewer in reviewers:
        email = reviewer['reviewer_email']
        cal_uids = calibration_schedule.get(email, [])
        for uid in cal_uids:
            assignments_by_reviewer[email].append({
                'card_uid': uid,
                'is_calibration': True
            })
    
    # 2. Non-calibration 문항: Round Robin 분배
    calibration_uids = set()
    for uids in calibration_schedule.values():
        calibration_uids.update(uids)
    
    non_calibration_cards = [
        c for c in cards 
        if c['card_uid'] not in calibration_uids
    ]
    
    reviewer_idx = 0
    for card in non_calibration_cards:
        reviewer = reviewers[reviewer_idx % len(reviewers)]
        assignments_by_reviewer[reviewer['reviewer_email']].append({
            'card_uid': card['card_uid'],
            'is_calibration': False,
            's5_decision': card['s5_decision']
        })
        reviewer_idx += 1
    
    # 3. 위치 랜덤화: 각 전공의의 150개 문항 내에서 셔플
    final_assignments = []
    for reviewer in reviewers:
        email = reviewer['reviewer_email']
        items = assignments_by_reviewer[email]
        random.shuffle(items)  # 위치 랜덤화
        
        for order, item in enumerate(items, 1):
            final_assignments.append({
                'reviewer_email': email,
                'card_uid': item['card_uid'],
                'assignment_order': order,
                'is_calibration': item['is_calibration'],
                's5_decision': item.get('s5_decision', 'PASS')
            })
    
    return final_assignments
```

---

## 3. 전문의 할당 알고리즘 (총 330건)

### 3.1 전체 프로세스 개요

```
1. 전공의 할당분 로드
2. 분과별 필터링
3. REGEN 우선 포함
4. PASS에서 나머지 채우기
5. 인당 30건 할당
```

### 3.2 핵심 설계 원칙

1. **100% 오버랩**: 전공의 할당분에서만 서브샘플링 (전공의가 평가하지 않은 문항은 전문의도 평가하지 않음)
2. **분과별 할당**: 각 전문의의 분과(specialty)에 맞는 문항 우선 할당
3. **REGEN 우선**: 전공의에게 할당된 REGEN 문항 중 해당 분과 문항 우선 포함
4. **인당 30건**: 각 전문의에게 정확히 30건 할당

### 3.3 Step 1: 전공의 할당분 로드

```python
# 전공의 할당 결과 로드
resident_assignments = load_resident_assignments()  # 1,350건

# 할당된 카드 UID 집합
resident_assigned_card_uids = {
    a['card_uid'] for a in resident_assignments
}

# 전공의 할당 카드 정보 (중복 제거)
resident_assigned_cards = {
    a['card_uid']: {
        'card_uid': a['card_uid'],
        'card_id': a['card_id'],
        's5_decision': a['s5_decision'],
        'specialty': get_card_specialty(a['card_uid']),  # 카드의 분과 정보
        # ... 기타 메타데이터
    }
    for a in resident_assignments
}
```

### 3.4 Step 2: 분과별 필터링 및 할당

각 전문의의 분과에 맞는 문항을 필터링합니다:

```python
# 전문의 목록 로드
specialists = get_specialists()  # 11명

# 분과 매핑 (reviewer_master.csv 기반)
specialty_mapping = {
    'neuro_hn_imaging': ['rev_010'],  # 신경두경부영상
    'breast_rad': ['rev_011'],        # 유방영상
    'thoracic_radiology': ['rev_012'], # 흉부영상
    'interventional_radiology': ['rev_013'], # 인터벤션
    'musculoskeletal_radiology': ['rev_014'], # 근골격영상
    'gu_radiology': ['rev_015'],      # 비뇨생식기영상
    'cardiovascular_rad': ['rev_016'], # 심장영상
    'abdominal_radiology': ['rev_017'], # 복부영상
    'physics_qc_informatics': ['rev_018'], # 물리
    'pediatric_radiology': ['rev_019'], # 소아영상
    'nuclear_med': ['rev_020'],       # 핵의학
}

# 각 전문의별 할당
specialist_assignments = []

for specialist in specialists:
    specialty = specialist['subspecialty']
    target_count = 30  # 인당 30건
    
    # 1. 전공의 할당분에서 해당 분과 문항 필터링
    specialty_cards = [
        card for card in resident_assigned_cards.values()
        if card['specialty'] == specialty
    ]
    
    # 2. REGEN 우선 포함
    regen_cards = [c for c in specialty_cards if c['s5_decision'] == 'REGEN']
    pass_cards = [c for c in specialty_cards if c['s5_decision'] == 'PASS']
    
    # REGEN 문항 수가 30개 이하인 경우
    if len(regen_cards) <= target_count:
        assigned_regen = regen_cards.copy()
        regen_count = len(assigned_regen)
        pass_needed = target_count - regen_count
        
        # PASS에서 나머지 채우기
        assigned_pass = random_sample(
            pass_cards,
            n=pass_needed,
            seed=20260101
        )
    else:
        # REGEN이 30개 초과인 경우: REGEN만 30개 선택
        assigned_regen = random_sample(
            regen_cards,
            n=target_count,
            seed=20260101
        )
        assigned_pass = []
    
    # 3. 할당 생성
    assigned_cards = assigned_regen + assigned_pass
    for card in assigned_cards:
        specialist_assignments.append({
            'reviewer_email': specialist['reviewer_email'],
            'card_uid': card['card_uid'],
            'card_id': card['card_id'],
            's5_decision': card['s5_decision'],
            'is_calibration': False  # 전문의는 Calibration 없음
        })
```

### 3.5 분과별 할당 현황

각 전문의는 자신의 분과에 맞는 30건을 할당받습니다:

| 분과 | 전문의 수 | 인당 할당량 | 총 할당량 |
|------|----------|------------|----------|
| 신경두경부영상 (neuro_hn_imaging) | 1 | 30 | 30 |
| 유방영상 (breast_rad) | 1 | 30 | 30 |
| 흉부영상 (thoracic_radiology) | 1 | 30 | 30 |
| 인터벤션 (interventional_radiology) | 1 | 30 | 30 |
| 근골격영상 (musculoskeletal_radiology) | 1 | 30 | 30 |
| 비뇨생식기영상 (gu_radiology) | 1 | 30 | 30 |
| 심장영상 (cardiovascular_rad) | 1 | 30 | 30 |
| 복부영상 (abdominal_radiology) | 1 | 30 | 30 |
| 물리 (physics_qc_informatics) | 1 | 30 | 30 |
| 소아영상 (pediatric_radiology) | 1 | 30 | 30 |
| 핵의학 (nuclear_med) | 1 | 30 | 30 |
| **총계** | **11** | **30** | **330** |

---

## 4. Cluster Shuffle 알고리즘

### 4.1 목적

통계적 독립성을 확보하기 위해 Cluster(Objective)를 고려한 Shuffle을 수행합니다.

### 4.2 구현

```python
def cluster_aware_shuffle(cards, cluster_key='objective_id', seed=20260101):
    """
    Cluster를 고려한 Shuffle
    
    같은 Cluster의 문항이 한 평가자에게 집중되지 않도록 분산
    """
    import random
    random.seed(seed)
    
    # Cluster별로 그룹화
    cluster_groups = {}
    for card in cards:
        cluster_id = card.get(cluster_key, 'unknown')
        if cluster_id not in cluster_groups:
            cluster_groups[cluster_id] = []
        cluster_groups[cluster_id].append(card)
    
    # 각 Cluster 내에서 Shuffle
    for cluster_id, cluster_cards in cluster_groups.items():
        random.shuffle(cluster_cards)
    
    # Cluster 순서도 Shuffle
    cluster_ids = list(cluster_groups.keys())
    random.shuffle(cluster_ids)
    
    # Interleaved 방식으로 재배열
    # (같은 Cluster의 문항이 연속되지 않도록)
    shuffled = []
    max_cluster_size = max(len(cards) for cards in cluster_groups.values())
    
    for i in range(max_cluster_size):
        for cluster_id in cluster_ids:
            cluster_cards = cluster_groups[cluster_id]
            if i < len(cluster_cards):
                shuffled.append(cluster_cards[i])
    
    return shuffled
```

**효과**:
- 같은 질환 그룹(Objective)의 문항이 한 평가자에게 집중되지 않음
- 통계적 독립성 확보
- 평가자 피로도 감소

---

## 5. 출력 파일

### 5.1 Assignments.csv

할당 결과를 CSV 형식으로 저장합니다:

```csv
assignment_id,reviewer_email,card_uid,card_id,assignment_order,batch_id,status,s5_decision,is_calibration
asg_001,reviewer_01@example.com,card_uid_001,grp_xxx__entity_yyy__C01,1,batch_001,pending,PASS,True
asg_002,reviewer_01@example.com,card_uid_002,grp_xxx__entity_yyy__C02,2,batch_001,pending,REGEN,False
...
```

**필드 설명**:
- `assignment_id`: 할당 고유 ID
- `reviewer_email`: 평가자 이메일
- `card_uid`: 카드 고유 ID
- `card_id`: 카드 ID (형식: `{group_id}__{entity_id}__C{01|02}`)
- `assignment_order`: 평가 순서
- `batch_id`: 배치 ID (선택적)
- `status`: 할당 상태 (`pending`, `in_progress`, `completed`)
- `s5_decision`: S5 판정 (`PASS` 또는 `REGEN`)
- `is_calibration`: Calibration 문항 여부 (`True` 또는 `False`)

### 5.2 FINAL_QA_Assignment_Summary.json

할당 통계 및 검증 정보를 JSON 형식으로 저장합니다:

```json
{
  "assignment_version": "FINAL_QA_v1.0",
  "created_ts": "2026-01-01T...",
  "seed": 20260101,
  "summary": {
    "total_assignments": 1680,
    "resident_assignments": 1350,
    "specialist_assignments": 330
  },
  "resident_summary": {
    "total_residents": 9,
    "assignments_per_resident": 150,
    "calibration_slots": 45,
    "regen_slots": 150,
    "pass_slots": 1155,
    "regen_census": true
  },
  "specialist_summary": {
    "total_specialists": 11,
    "assignments_per_specialist": 30,
    "specialty_distribution": {
      "neuro_hn_imaging": 30,
      "breast_rad": 30,
      ...
    }
  },
  "validation": {
    "all_residents_same_calibration": true,
    "regen_census_or_cap": "census",
    "total_assignments_match": true
  }
}
```

---

## 6. 검증 체크리스트

할당 완료 후 다음을 확인합니다:

### 6.1 전공의 할당 검증

- [ ] 총 할당량: 1,350건 (9명 × 150건)
- [ ] **Calibration (Specialty-Stratified)**: 33개 고유 문항 (11분과 × 3문제), 각 문항을 3명에게 배정 (99 슬롯)
- [ ] 각 전공의가 정확히 **11개** Calibration 문항 평가
- [ ] **전문의 330에서 선택**: Realistic 이미지 포함 보장
- [ ] Calibration 문항이 150개 내에서 **랜덤 위치**에 분산
- [ ] REGEN: 전수 조사 (≤200개) 또는 200개 Cap (>200개)
- [ ] PASS: 나머지 할당량 채우기 (1,350 - 99 - REGEN 슬롯)
- [ ] 인당 할당량: 150건 (Calibration 11 + REGEN + PASS ~139)

### 6.2 전문의 할당 검증

- [ ] 총 할당량: 330건 (11명 × 30건)
- [ ] 각 분과별로 30문제씩 배정 (핵의학 포함)
- [ ] 전공의 할당분에서 서브샘플링 (100% 오버랩)
- [ ] REGEN 우선 포함 (해당 분과의 REGEN 문항)
- [ ] PASS에서 나머지 채우기 (해당 분과의 PASS 문항)
- [ ] 인당 할당량: 30건

### 6.3 통계적 검증

- [ ] Cluster Shuffle 적용 확인
- [ ] 통계적 독립성 확보 (같은 Cluster 문항 분산)
- [ ] 시드 고정: `SEED=20260101`
- [ ] 재현 가능성 확인

---

## 7. 구현 참고사항

### 7.1 시드 고정

모든 무작위 샘플링은 고정 시드를 사용합니다:

```python
SEED = 20260101  # 프로토콜에 명시된 고정 시드
```

이를 통해 할당 결과의 재현 가능성을 보장합니다.

### 7.2 성능 고려사항

- 대용량 데이터 처리 시 메모리 효율적 구현 필요
- Cluster Shuffle은 메모리 사용량이 클 수 있으므로 스트리밍 방식 고려

### 7.3 에러 처리

- S5 판정 결과가 없는 카드: 기본값 PASS로 처리
- 분과 정보가 없는 카드: 전문의 할당에서 제외
- 할당량 부족 시: 경고 로그 출력 및 부분 할당

---

## 8. 관련 문서

- `0_Protocol/06_QA_and_Study/QA_Operations/FINAL_QA_Assignment_Handover.md`: 구현 인계장
- `0_Protocol/05_Pipeline_and_Execution/S5_Decision_Definition_Canonical.md`: S5 판정 기준
- `0_Protocol/06_QA_and_Study/FINAL_QA_Research_Design_Spec.md`: 연구 설계 사양서
- `2_Data/metadata/generated/FINAL_DISTRIBUTION/qa_handover_allocation_6000cards.md`: Allocation 인계장

---

## 9. 버전 이력

- **v1.2** (2026-01-04): Calibration 분과별 균등 배정
  - Calibration 문항 수 변경: 30개 → **33개** (11분과 × 3문제)
  - 각 전공의 11개 calibration 문항 배정 (99 slots)
  - **전문의 330에서 선택**: Realistic 이미지 포함 보장
  - 모든 분과가 calibration에 균등 대표

- **v1.1** (2026-01-04): Calibration Partial Overlap 설계 도입
  - Calibration 설계 변경: 5개×9명 → **30개×3명** (Partial Overlap)
  - ICC 정밀도 개선: 95% CI 폭 0.59 → 0.30
  - 각 전공의 10개 calibration 문항 배정 (균형 배정)
  - 위치 랜덤화 도입 (학습효과/피로효과 방지)
  - `distribute_with_partial_overlap()` 함수 추가
  - `create_balanced_calibration_schedule()` 함수 추가

- **v1.0** (2026-01-01): 초기 버전
  - 전공의 할당 알고리즘 상세 설명
  - 전문의 할당 알고리즘 상세 설명
  - Calibration Set 설계 설명
  - REGEN 전수 조사 vs Cap 로직 설명
  - Cluster Shuffle 알고리즘 설명

---

**Document Status**: Canonical  
**Version**: 1.2  
**Last Updated**: 2026-01-04  
**Owner**: MeducAI Research Team


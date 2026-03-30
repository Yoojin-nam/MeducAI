# FINAL 배포 규모 예상

**Status:** Draft  
**Version:** 1.0  
**Date:** 2025-12-29  
**Purpose:** FINAL 배포 시 예상되는 Entity 수 및 카드 수 계산

---

## 1. 배경

FINAL 배포에서는:
- **groups_canonical.csv에 있는 모든 그룹 사용** (321개 그룹)
- **S1에서 생성된 모든 Entity 사용**
- **Entity당 2장 카드 생성** (Q1, Q2만, FINAL 모드)

이 경우 총 카드 수가 목표인 6,000장을 초과할 가능성이 있습니다.

---

## 2. 실제 데이터 분석

### 2.1 분석 대상

최근 실행 태그들의 S1 결과를 분석:
- `TEST_PROGRESS_20251229_145011`
- `TEST_PROGRESS_20251229_143111`
- `S0_QA_final_time`

### 2.2 분석 결과

| 항목 | 값 |
|------|-----|
| **분석한 그룹 수** | 22개 |
| **총 Entity 수** | 232개 |
| **그룹당 평균 Entity 수** | **10.55개** |
| **Entity 수 분포** | 최소: 8개, 최대: 14개, 중앙값: 10개 |

---

## 3. FINAL 배포 규모 예상

### 3.1 기본 가정

- **전체 그룹 수**: 321개 (groups_canonical.csv)
- **그룹당 평균 Entity 수**: 10.55개 (실제 데이터 기반)
- **Entity당 카드 수**: 2장 (Q1, Q2만, FINAL 모드)

### 3.2 예상 계산

| 항목 | 계산 | 결과 |
|------|------|------|
| **예상 총 Entity 수** | 321 × 10.55 | **약 3,385개** |
| **예상 총 카드 수** | 3,385 × 2 | **약 6,770장** |
| **목표 카드 수** | - | **6,000장** |
| **차이** | 6,770 - 6,000 | **+770장 (12.8% 초과)** |

### 3.3 시나리오별 예상

#### 시나리오 1: 평균 Entity 수 유지 (10.55개)
- 총 Entity: 3,385개
- 총 카드: 6,770장
- **초과: 770장 (12.8%)**

#### 시나리오 2: 최소 Entity 수 (8개)
- 총 Entity: 321 × 8 = 2,568개
- 총 카드: 2,568 × 2 = 5,136장
- **부족: 864장 (14.4%)**

#### 시나리오 3: 최대 Entity 수 (14개)
- 총 Entity: 321 × 14 = 4,494개
- 총 카드: 4,494 × 2 = 8,988장
- **초과: 2,988장 (49.8%)**

#### 시나리오 4: 중앙값 Entity 수 (10개)
- 총 Entity: 321 × 10 = 3,210개
- 총 카드: 3,210 × 2 = 6,420장
- **초과: 420장 (7.0%)**

---

## 4. 문제점 및 대응 방안

### 4.1 문제점

**Entity당 2장 카드를 모든 Entity에 대해 생성하면, 목표 6,000장을 초과할 가능성이 높습니다.**

- 평균 시나리오: **6,770장** (12.8% 초과)
- 중앙값 시나리오: **6,420장** (7.0% 초과)
- 최대 시나리오: **8,988장** (49.8% 초과)

### 4.2 대응 방안

#### 옵션 1: Entity 선택 (Selection)

**방법**: S1에서 생성된 모든 Entity 중에서 일부만 선택하여 카드 생성

**장점**:
- 정확히 6,000장 달성 가능
- 중요도 기반 선택 가능

**단점**:
- Entity 선택 기준 필요
- 일부 Entity는 카드가 없을 수 있음

**구현**:
- S3 단계에서 Entity 선택 로직 추가
- Group weight 또는 Entity 중요도 기반 선택
- 각 그룹에서 선택할 Entity 수 계산:
  ```
  selected_entities_per_group = floor(6000 / total_entities * entities_in_group)
  ```

#### 옵션 2: 그룹별 카드 수 할당 후 Entity 선택

**방법**: 그룹별로 카드 수를 먼저 할당하고, 각 그룹 내에서 Entity 선택

**장점**:
- 그룹별 균형 유지 가능
- 기존 allocation 로직 활용 가능

**단점**:
- 그룹별 Entity 수가 다르므로 복잡도 증가

**구현**:
- 기존 `group_target_cards` 계산 유지
- 각 그룹 내에서 Entity 선택:
  ```
  entities_to_select = floor(group_target_cards / 2)
  ```

#### 옵션 3: 목표 카드 수 증가

**방법**: TOTAL_CARDS를 6,000에서 7,000 또는 7,500으로 증가

**장점**:
- 모든 Entity에 대해 카드 생성 가능
- 구현 간단

**단점**:
- 목표 카드 수 변경 필요
- QA 부담 증가

#### 옵션 4: Entity당 카드 수 조정 (비권장)

**방법**: 일부 Entity는 1장만 생성

**단점**:
- 일관성 저하
- Q1/Q2 구조 위반

---

## 5. 권장 방안

### 5.1 단기 방안: Entity 선택 (옵션 1 또는 2)

**권장**: **옵션 2 (그룹별 카드 수 할당 후 Entity 선택)**

**이유**:
1. 기존 allocation 로직과 일관성 유지
2. 그룹별 균형 유지 가능
3. Group weight 기반 할당 가능

**구현 예시**:
```python
# 1. 그룹별 카드 수 할당 (기존 로직)
group_target_cards = allocate_by_weight(groups, total_cards=6000)

# 2. 각 그룹 내에서 Entity 선택
for group in groups:
    entities = s1_output[group]['entity_list']
    cards_per_entity = 2
    entities_to_select = floor(group_target_cards[group] / cards_per_entity)
    
    # 중요도 기반 선택 (또는 순서 기반)
    selected_entities = select_entities(entities, count=entities_to_select)
    
    # 선택된 Entity에 대해서만 S2 실행
    for entity in selected_entities:
        generate_cards(entity, count=2)  # Q1, Q2
```

### 5.2 장기 방안: 목표 카드 수 재검토

실제 생성 가능한 카드 수를 고려하여 TOTAL_CARDS 목표를 재검토:
- **7,000장**: 평균 시나리오 대비 여유 있음
- **6,500장**: 중앙값 시나리오 대비 적절

---

## 6. Entity 선택 기준 (옵션 2 구현 시)

### 6.1 선택 방법

1. **순서 기반**: S1에서 생성된 순서대로 선택 (간단)
2. **중요도 기반**: Entity 이름, 설명 등 기반 중요도 계산 (복잡)
3. **균등 분배**: 그룹 내 Entity 수에 비례하여 선택

### 6.2 권장 방법

**순서 기반 선택** (간단하고 일관성 있음)

- S1에서 생성된 Entity 순서대로 선택
- 각 그룹에서 `entities_to_select` 개수만큼 선택
- 나머지 Entity는 카드 생성하지 않음

---

## 7. 예상 시나리오별 Entity 선택 수

### 7.1 평균 시나리오 (10.55 Entity/그룹)

- 총 Entity: 3,385개
- 목표 카드: 6,000장
- 필요한 Entity: 3,000개 (6,000 / 2)
- **선택 비율**: 88.6% (3,000 / 3,385)
- **제외 Entity**: 385개 (11.4%)

### 7.2 중앙값 시나리오 (10 Entity/그룹)

- 총 Entity: 3,210개
- 목표 카드: 6,000장
- 필요한 Entity: 3,000개
- **선택 비율**: 93.5% (3,000 / 3,210)
- **제외 Entity**: 210개 (6.5%)

---

## 8. 참고 문서

- **Card Count Policy**: `0_Protocol/03_CardCount_and_Allocation/S0_vs_FINAL_CardCount_Policy.md`
- **Allocation Policy**: `0_Protocol/03_CardCount_and_Allocation/FINAL_Allocation/Entity_Quota_Distribution_Policy.md`
- **S2 Policy**: `0_Protocol/04_Step_Contracts/Step02_S2/S2_Cardset_Image_Placement_Policy_Canonical.md`

---

## 9. 요약

### 9.1 예상 규모

- **전체 그룹**: 321개
- **예상 총 Entity**: 약 3,385개 (평균 10.55개/그룹)
- **예상 총 카드 (Entity당 2장)**: 약 6,770장
- **목표 카드**: 6,000장
- **초과**: 약 770장 (12.8%)

### 9.2 권장 대응

**Entity 선택 기반 카드 생성**:
- 그룹별 카드 수 할당 후, 각 그룹 내에서 Entity 선택
- 선택 비율: 약 88-94% (시나리오에 따라)
- 제외 Entity: 약 210-385개

### 9.3 다음 단계

1. **Entity 선택 로직 설계**: S3 단계에서 Entity 선택 기준 정의
2. **Allocation 로직 수정**: 그룹별 카드 수 할당 후 Entity 선택
3. **테스트**: 소규모 그룹으로 테스트 후 전체 적용

---

**작성자**: MeducAI Research Team  
**검토 필요**: Entity 선택 기준 및 allocation 로직 구현 방안


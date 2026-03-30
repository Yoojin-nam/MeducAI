# S0/S1/S2 Card Allocation 정책 충돌 분석

**생성일:** 2025-12-19  
**수정 완료일:** 2025-12-19  
**상태:** ✅ **모든 충돌 해결 완료** (Historical Reference)  
**Last Updated:** 2025-12-20  
**목적:** 코드 구현과 Governance 문서 간의 allocation 정책 충돌 지점 정리 및 해결

**⚠️ IMPORTANT:** This document is a **Historical Reference**. All conflicts described in this document have been **resolved** (2025-12-19). The current canonical documents are up-to-date and consistent. This document is retained for historical context.

---

## 📋 요약

코드에서 실제로 구현된 allocation 로직과 Governance 문서의 설명이 **여러 지점에서 불일치**합니다.  
이 문서는 각 충돌 지점을 명확히 정리하여, 사용자가 어떤 것이 올바른지 결정할 수 있도록 합니다.

---

## 🔴 주요 충돌 지점

### 충돌 1: S0 Entity 선택 정책

#### 📄 문서 (S0_vs_FINAL_CardCount_Policy.md)
```
**위치:** `0_Protocol/03_CardCount_and_Allocation/S0_vs_FINAL_CardCount_Policy.md`
**섹션:** 2.3 Entity Handling in S0 (Hard Rule)

"단일 대표 엔티티(single representative entity)를 선택한다.
전체 고정 set payload (q = 12)를 해당 엔티티에 적용한다."
```

#### 💻 코드 (s0_allocation.py)
```python
**위치:** `3_Code/src/tools/allocation/s0_allocation.py`
**버전:** v2.1 (현재 Canonical)

규칙:
- If E >= 4: 첫 4개 엔티티 × 각 3장 = 12장
- If E < 4: 모든 엔티티에 균등 분배하여 합계 12장
```

#### ✅ 문서 (S0_Allocation_Artifact_Spec.md)
```
**위치:** `0_Protocol/03_CardCount_and_Allocation/S0_Allocation/S0_Allocation_Artifact_Spec.md`
**버전:** v2.1

"Deterministic 3×4 Entity Allocation:
- If E >= 4: 첫 4개 엔티티 × 각 3장
- If E < 4: 모든 엔티티에 균등 분배"
```

**충돌 상태:** ⚠️ **S0_vs_FINAL_CardCount_Policy.md가 구버전 정책을 설명**

---

### 충돌 2: 코드 주석과 실제 구현 버전

#### 💻 코드 주석 (01_generate_json.py)
```python
**위치:** `3_Code/src/01_generate_json.py` (라인 18-20)

"""
S0 Allocation v2.0:
- In S0 mode, entity spread allocation is created/validated...
"""
```

#### 💻 실제 구현 (s0_allocation.py)
```python
**위치:** `3_Code/src/tools/allocation/s0_allocation.py`

"""
v2.1 policy (current canonical):
- Fixed 12 cards per set
- Deterministic prefix allocation (3×4):
    - If E >= 4: use first 4 entities × 3 cards each = 12
    - If E < 4 : use all entities, deterministic even split to sum 12
"""
```

**충돌 상태:** ⚠️ **코드 주석이 v2.0이라고 하지만 실제로는 v2.1 사용**

---

### 충돌 3: S2 카드 수 정책과 S0 Allocation의 관계

#### 📄 문서 (S2_CARDSET_POLICY_V1.md)
```
**위치:** `0_Protocol/04_Step_Contracts/Step02_S2/S2_CARDSET_POLICY_V1.md`

"각 Entity마다 정확히 3문항을 생성한다."
```

#### 💻 코드 (S0 allocation)
```python
**위치:** `3_Code/src/tools/allocation/s0_allocation.py`

S0 v2.1:
- If E >= 4: 각 엔티티에 3장씩 할당 (S2_CARDSET_POLICY와 일치)
- If E < 4: 균등 분배 (3장이 아닐 수 있음)
```

**충돌 상태:** ⚠️ **E < 4일 때 S2_CARDSET_POLICY의 "정확히 3문항" 규칙과 충돌 가능**

---

### 충돌 4: FINAL 모드에서의 Allocation

#### 📄 문서 (Allocation_Step_Card_Quota_Policy_v1.0.md)
```
**위치:** `0_Protocol/03_CardCount_and_Allocation/FINAL_Allocation/Allocation_Step_Card_Quota_Policy_v1.0.md`

"Allocation produces group-level quotas for FINAL generation.
Input: groups.csv + TOTAL_CARDS
Output: group_target_cards per group"
```

#### 💻 코드 (01_generate_json.py)
```python
**위치:** `3_Code/src/01_generate_json.py` (라인 1553-1556)

else:  # FINAL mode
    for ent in entity_list:
        s2_targets.append(_S2Target(
            entity_id=eid,
            entity_name=ent,
            cards_for_entity_exact=int(cards_per_entity_default)
        ))
```

**충돌 상태:** ⚠️ **FINAL 모드에서 `cards_per_entity_default`를 사용하는데, 이는 group-level quota와 어떻게 연결되는지 불명확**

---

## 📊 상세 비교표

### S0 Allocation 정책 비교

| 항목 | S0_vs_FINAL 문서 | S0_Allocation_Artifact_Spec | 실제 코드 (v2.1) |
|------|-----------------|----------------------------|-----------------|
| **Entity 선택** | 단일 대표 엔티티 | 최대 4개 엔티티 (E>=4) | 최대 4개 엔티티 (E>=4) |
| **카드 수 분배** | 12장을 1개 엔티티에 | 4개 × 3장 (E>=4) 또는 균등 분배 (E<4) | 4개 × 3장 (E>=4) 또는 균등 분배 (E<4) |
| **버전** | 명시 없음 | v2.1 | v2.1 |
| **상태** | ❌ 구버전 | ✅ 최신 | ✅ 최신 |

---

### S2 카드 생성 정책 비교

| 항목 | S2_CARDSET_POLICY_V1 | S0 Allocation v2.1 | 충돌 여부 |
|------|---------------------|---------------------|----------|
| **Entity당 카드 수** | 정확히 3문항 | E>=4: 3장, E<4: 균등 분배 | ⚠️ E<4일 때 충돌 |
| **카드 타입** | Q1: BASIC, Q2/Q3: MCQ | 명시 없음 (S2 책임) | ✅ 일치 |
| **이미지 배치** | Q1: FRONT, Q2: BACK, Q3: NONE | 명시 없음 (S2 책임) | ✅ 일치 |

---

### FINAL Allocation 정책 비교

| 항목 | Allocation_Step_Card_Quota_Policy | 실제 코드 | 충돌 여부 |
|------|----------------------------------|----------|----------|
| **Control Unit** | Group-level | Entity-level (`cards_per_entity_default`) | ⚠️ 불명확 |
| **Quota 계산** | Allocation step에서 계산 | 코드에서 직접 계산하는 로직 없음 | ⚠️ 누락 |
| **Artifact** | FINAL allocation artifact | 명시 없음 | ⚠️ 불명확 |

---

## 🎯 수정 권장사항

### 우선순위 1 (Critical): S0_vs_FINAL_CardCount_Policy.md 수정

**현재 문제:**
- "단일 대표 엔티티" 설명이 구버전 (v1.0) 정책을 반영
- 실제 코드는 v2.1 (3×4 규칙) 사용

**수정 방안:**
```markdown
### 2.3 Entity Handling in S0 (Hard Rule)

* **Deterministic 3×4 Entity Allocation (v2.1):**
  * If E >= 4: 첫 4개 엔티티 × 각 3장 = 12장
  * If E < 4: 모든 엔티티에 균등 분배하여 합계 12장
* Allocation artifact는 S2 실행을 위한 기록 산출물
```

---

### 우선순위 2 (High): 코드 주석 수정

**현재 문제:**
- `01_generate_json.py` 주석이 "S0 Allocation v2.0"이라고 명시
- 실제로는 v2.1 사용

**수정 방안:**
```python
"""
S0 Allocation v2.1:
- In S0 mode, deterministic prefix allocation (3×4) is created/validated
- Multi-entity S2 targets with exact-N per entity
"""
```

---

### 우선순위 3 (Medium): S2_CARDSET_POLICY와 S0 Allocation 정합성

**현재 문제:**
- S2_CARDSET_POLICY는 "정확히 3문항"을 요구
- S0 Allocation v2.1은 E<4일 때 3장이 아닐 수 있음

**수정 방안 (선택지):**

**옵션 A:** S0 Allocation v2.1을 수정하여 항상 3장씩 할당
```python
# E < 4일 때도 가능한 한 3장씩 할당하도록 수정
# 예: E=3이면 각 4장, E=2면 각 6장 (합계 12장 유지)
```

**옵션 B:** S2_CARDSET_POLICY에 예외 규칙 추가
```markdown
"각 Entity마다 정확히 3문항을 생성한다.
단, S0 모드에서 E < 4인 경우 allocation artifact에 명시된 
cards_for_entity_exact 값을 따른다."
```

---

### 우선순위 4 (Medium): FINAL Allocation 구현 명확화

**현재 문제:**
- FINAL 모드에서 `cards_per_entity_default` 사용
- Group-level quota와의 연결 관계 불명확

**수정 방안:**
1. FINAL allocation artifact 생성 로직 확인/구현
2. Group-level quota → Entity-level allocation 변환 로직 문서화
3. 코드에서 FINAL allocation artifact를 읽어서 사용하도록 수정

---

## ✅ 해결 완료 사항

**사용자 결정사항 (2025-12-19):**

1. **S0 Entity 선택 정책:** ✅ 3×4 규칙 (v2.1) 유지
2. **S2 카드 수 정책:** ✅ E<4일 때는 12장을 위해 3장 위반 가능 (드문 케이스), 그 외에는 3문항 유지
3. **FINAL Allocation:** ✅ `cards_per_entity_default` 폐기, Entity당 3장으로 고정
4. **코드 주석:** ✅ v2.1로 업데이트 완료

---

## 📝 수정 완료 내역

### 1. S0_vs_FINAL_CardCount_Policy.md ✅
- 2.3 섹션: v2.1 정책 반영 (3×4 규칙)
- 3.2-3.3 섹션: FINAL Entity당 3장 정책 추가
- 5번 테이블: Entity count 및 Allocation logic 업데이트
- 7.2 섹션: CARDS_PER_ENTITY deprecated 명시

### 2. 코드 주석 (01_generate_json.py) ✅
- S0 Allocation v2.1로 업데이트
- FINAL mode Entity당 3장 고정 명시

### 3. S2_CARDSET_POLICY_V1.md ✅
- E<4 예외 규칙 추가 (S0 모드, 드문 케이스)

### 4. FINAL 모드 코드 (01_generate_json.py) ✅
- `cards_per_entity_default` 제거
- Entity당 3장 고정 (`FINAL_CARDS_PER_ENTITY = 3`)

### 5. FINAL Allocation 문서 ✅
- Entity_Quota_Distribution_Policy_v1.0.md: Entity당 3장 정책 반영
- Allocation_Step_Card_Quota_Policy_v1.0.md: Group-level target 계산 방식 업데이트

---

## ✅ 최종 상태

모든 충돌이 해결되었으며, 코드와 문서가 일관된 정책을 반영합니다:
- **S0:** 3×4 규칙 (v2.1) - E>=4: 4개×3장, E<4: 균등 분배
- **FINAL:** Entity당 3장 고정
- **S2:** Entity당 3문항 (E<4 예외 허용)

---

**참고 문서:**
- `0_Protocol/03_CardCount_and_Allocation/S0_Allocation/S0_Allocation_Artifact_Spec.md` (v2.1, 최신)
- `0_Protocol/03_CardCount_and_Allocation/S0_vs_FINAL_CardCount_Policy.md` (구버전 정책 반영)
- `3_Code/src/tools/allocation/s0_allocation.py` (실제 구현)


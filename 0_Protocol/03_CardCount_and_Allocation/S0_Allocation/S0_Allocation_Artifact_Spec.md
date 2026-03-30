# S0 Allocation Artifact Specification (v2.1)

**Status:** Canonical
**Applies to:** Step **S0 (QA / Model Comparison only)**
**Effective Date:** 2025-12-19
**Supersedes:** S0 Allocation Artifact Specification (v2.0)
**Change Policy:** S0 종료 전까지 수정 불가 *(v2.1로 동결)*

---

## 0. One-Line Definition (Non-Negotiable)

> **In Step S0, allocation does NOT compute, distribute, or optimize card counts beyond a fixed 12-card payload.**
> **It records a deterministic selection of up to 4 entities and assigns exactly 3 cards per entity (when possible), as an artifact for exact execution by S2.**

---

## 1. Purpose

본 문서는 MeducAI **S0(QA) 단계**에서 다음을 보장하기 위해 존재한다.

1. **Arm 간 공정한 비교**

   * 카드 수 변동성 제거(항상 12장)
   * 엔티티 선택/분배는 **결정론적(deterministic)** 규칙으로만 수행
2. **책임 경계 강제**

   * Allocation은 “결정(decision)”이 아니라 **기록(recording)** 산출물 생성
   * 카드 타입/문항 설계/이미지 결정은 S2/S3 영역
3. **재현성 및 감사 가능성**

   * S2 입력을 artifact로 고정해 **정확히 재실행** 가능
4. **FINAL allocation과의 개념적 단절**

   * S0 allocation은 FINAL allocation과 **정책적 연속성 없음**

---

## 2. Scope & Explicit Non-Scope

### 2.1 Scope (Applies)

* Step **S0** only
* Set = **group × arm**
* QA / model selection 목적

### 2.2 Explicitly Out of Scope (Forbidden)

다음은 **S0 Allocation에서 절대 수행되지 않는다.**

* 가중치/importance 기반 최적화
* coverage/diversity를 위한 탐색적 선택
* FINAL allocation을 암시하는 로직

---

## 3. Core Invariants (Hard Rules)

### 3.1 Fixed Set-Level Payload

* **Set target cards:** `set_target_cards = 12` (상수)
* 모든 S0 set은 **항상 정확히 12장**

### 3.2 Deterministic 3×4 Entity Allocation

목표: S0에서 **entity당 3장**이라는 QA 단위(문항 3종) 고정.

**규칙(결정론)**

1. S1이 반환한 `entities_from_s1`를 **순서 그대로** 사용한다.
2. 엔티티 수 `E = len(entities_from_s1)`일 때:

* **If `E >= 4` (표준 경로 / HARD):**

  * 사용 엔티티 = `entities_from_s1[0:4]`
  * 각 엔티티에 `cards_for_entity_exact = 3`
  * 합계 12장(4×3)

* **If `E < 4` (fallback / deterministic):**

  * 사용 엔티티 = `entities_from_s1[0:E]` (전부 사용)
  * 12장을 `E`개에 **결정론적 균등 분배**

    * `base = 12 // E`, `rem = 12 % E`
    * 앞에서부터 `rem`개 엔티티에 `base+1`, 나머지에 `base`
  * 목적: S0가 “항상 12장”을 보장하며 런 중단을 피함
  * 단, `E < 4`는 QA 설계상 이상 케이스이므로 **Warning 로그**를 권장

> **중요:** Allocation은 카드 타입/앞뒤/이미지 필요 여부를 결정하지 않는다.
> Allocation은 오직 “엔티티별 카드 수(정확히 몇 장)”만 기록한다.

### 3.3 No Decision Authority (Policy Firewall)

* Allocation은 **기록(recording)** 단계이지 **추론/최적화(decision)** 단계가 아니다.

---

## 4. Allocation Artifact (Required Output)

### 4.1 Artifact Timing

* **S1 이후**
* **S2 이전**
* Artifact 없이는 **S2 실행 불가**

### 4.2 Canonical Path

```text
2_Data/metadata/generated/{RUN_TAG}/allocation/
└── allocation_s0__group_{GROUP_ID}__arm_{ARM}.json
```

* group × arm **1:1 대응**
* in-memory allocation **금지**

---

## 5. Artifact Schema (Authoritative)

### 5.1 Required Top-Level Fields (Example)

```json
{
  "allocation_version": "S0-Allocation-v2.1",
  "mode": "S0",
  "run_tag": "S0_XXXX",
  "group_id": "G0001",
  "arm": "A",

  "set_target_cards": 12,

  "entity_selection_policy": {
    "type": "deterministic_prefix",
    "rule": "3x4: if E>=4 use first_4_entities_each_3_cards else deterministic_even_split_over_all_entities"
  },

  "entities_from_s1": ["Entity A", "Entity B", "Entity C", "Entity D", "Entity E"],
  "selected_entities": ["Entity A", "Entity B", "Entity C", "Entity D"],

  "entity_allocations": [
    { "entity_name": "Entity A", "cards_for_entity_exact": 3 },
    { "entity_name": "Entity B", "cards_for_entity_exact": 3 },
    { "entity_name": "Entity C", "cards_for_entity_exact": 3 },
    { "entity_name": "Entity D", "cards_for_entity_exact": 3 }
  ],

  "allocation_checksum": {
    "sum_cards": 12,
    "entity_count_used": 4
  }
}
```

---

## 6. Validation Rules (Fail-Fast)

Artifact 생성 또는 검증 시 아래 중 하나라도 위반하면 **즉시 FAIL**.

### 6.1 Structural

* `mode == "S0"`
* `allocation_version == "S0-Allocation-v2.1"`
* `set_target_cards == 12`
* `entities_from_s1`는 비어 있으면 안 됨
* `selected_entities.length == min(4, len(entities_from_s1))`
* `entity_allocations.length == selected_entities.length`

### 6.2 Arithmetic

```text
Σ(cards_for_entity_exact) == set_target_cards == 12
```

### 6.3 Referential

* `selected_entities ⊆ entities_from_s1`
* `entity_allocations[].entity_name ∈ selected_entities`

### 6.4 3×4 Rule Enforcement

* If `len(entities_from_s1) >= 4` then:

  * `entity_allocations.length == 4`
  * 모든 `cards_for_entity_exact == 3`

---

## 7. Contract with S2 (Binding)

* **S2는 allocation artifact만을 입력으로 사용**
* S2는 카드 수를 계산·보정·추론할 수 없음
* 위반 시 HARD FAIL:

```text
len(generated_cards_for_entity) != cards_for_entity_exact
→ HARD FAIL
```

---

## 8. Explicit Prohibitions (Zero-Tolerance)

다음 키/개념이 S0 allocation artifact 또는 설명에 등장하면 **정책 위반**이다.

* `importance_score`
* `weight`, `ratio`, `quota`
* `distribution`, `optimization` (단, “deterministic even split” 같은 산술적 분배 규칙 설명은 예외)
* FINAL allocation 관련 용어

---

## 9. Relationship to FINAL Allocation (Firewall)

| Dimension | S0 Allocation | FINAL Allocation |
| --------- | ------------- | ---------------- |
| 목적        | QA / 비교       | 배포               |
| 카드 수      | 고정(12)        | 계산됨              |
| Entity    | ≤4(결정론)       | 다수               |
| 정책        | 최소 규칙(3×4)    | 복잡 정책            |
| Artifact  | 필수            | 필수               |
| 연속성       | ❌ 없음          | —                |

---

## 10. Canonical Summary (Handoff Sentence)

> **S0 Allocation is a recording step, not a decision step.**
> **It fixes a 12-card payload and deterministically assigns 3 cards each to the first 4 entities (fallback to even split if fewer).**
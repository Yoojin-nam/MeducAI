# 🔍 MeducAI Canonical 편입 중 검증 템플릿

> **목적**
> Canonical 문서 편입(merge) 과정에서 발생할 수 있는 *구조적·의미적 충돌*을 사전에 차단하기 위한 **최소 교차 검증 템플릿**이다.
>
> **사용 규칙**
> - Canonical 문서 **1개 편입당 본 템플릿 1장 사용**
> - CP-1 ~ CP-5가 모두 통과되기 전에는 다음 Canonical로 이동 금지

---

## Meta
- **Canonical 문서:** Canonical_Merge_Verification_Template.md
- **편입 대상 문서:**
  - S0_vs_FINAL_CardCount_Policy.md
  - FINAL_Card_Count_Policy.md
  - Allocation_Step_Card_Quota_Policy_v1.0.md
  - Entity_Quota_Distribution_Policy_v1.0.md
  - S0_Allocation_Artifact_Spec.md
  - Entity_Definition_S2_Canonical.md
  - Entity_Definition_S3_Canonical.md
  - ARM_CONFIGS_Provider_Model_Resolution.md
- **편입 작업자:** [Study Coordinator]
- **편입 일시:** 2025-12-17
- **관련 단계:** ☑ S0 ☑ FINAL

---


## CP-0. Pipeline Fail-Fast & Abort Governance 검사 (Execution Safety)

### 검사 목적

파이프라인 전반에서 **FAIL 발생 시 중단 범위, 아티팩트 보존, QA/IRB 활용 가능성**이
단일 Canonical 정책에 의해 **일관되고 예측 가능하게 통제되는지**를 검증한다.

본 CP는 **모든 단계(S0–FINAL)의 상위 실행 거버넌스**로서,
개별 단계 정의(CP-1~CP-5)에 **선행**한다.

---

### 검사 대상 (Authoritative)

* **Pipeline Fail-Fast & Abort Policy (Canonical)**
  `05_Pipeline_and_Execution/Pipeline_FailFast_and_Abort_Policy.md`

* **관련 단계 Canonical 정의**

  * `S0_Allocation_Artifact_Spec.md`
  * `Entity_Definition_S2_Canonical.md`
  * `Entity_Definition_S3_Canonical.md`
  * `Entity_Definition_S4_Canonical.md`
  * `ARM_CONFIGS_Provider_Model_Resolution.md`

> ⚠️ 개별 Step 문서의 Fail 규칙은 **본 CP-0 정책을 위반할 수 없으며**,
> 충돌 시 **CP-0이 상위 해석 기준**이다.

---

### 확인 질문 1

**FAIL 발생 시 중단 범위(Abort Scope)가 단계별로 명확히 정의되어 있는가?**

**판정:** ☐ Yes / ☐ No

**검증 기준**

* FAIL 시 중단 단위가 아래 중 하나로 **명시적 고정**되어야 한다.

  ```
  RUN / ARM / GROUP / SET (group × arm)
  ```

* 단계별로 다음이 충족되는가:

| Stage            | Abort Scope            |
| ---------------- | ---------------------- |
| Preflight        | RUN                    |
| S0 Allocation    | SET                    |
| S1               | ARM                    |
| S2               | GROUP                  |
| S3               | GROUP(FINAL) / SET(S0) |
| S4               | GROUP                  |
| FINAL Allocation | RUN                    |

---

### 확인 질문 2

**FAIL 이후에도 아티팩트 보존 원칙이 일관되게 적용되는가?**

**판정:** ☐ Yes / ☐ No

**검증 기준**

* FAIL 이전 생성된 산출물은 **삭제되지 않고 보존**된다.

* 보존 목적은 다음으로 한정된다:

  * 재현성
  * 감사(IRB / MI-CLEAR-LLM)
  * 실패 원인 분석

* FAIL 산출물은 **배포·학습·품질 비교에 사용되지 않음**이 명시되어 있는가?

---

### 확인 질문 3

**FAIL run 산출물의 QA / IRB 활용 가능 범위가 명확히 제한되어 있는가?**

**판정:** ☐ Yes / ☐ No

**검증 기준**

* 다음 구분이 문서에 명시되어야 한다.

| 구분                 | 허용 여부           |
| ------------------ | --------------- |
| 구조 안정성 통계          | 허용              |
| FAIL 비율 / 규칙 위반 분석 | 허용              |
| arm 간 품질 비교        | 조건부(S0 AC 충족 시) |
| 학습 콘텐츠 품질 평가       | ❌ 금지            |
| FINAL 배포 사용        | ❌ 금지            |

---

### 확인 질문 4

**FAIL 이후 자동 재시도·우회·부분 성공 허용이 명시적으로 금지되어 있는가?**

**판정:** ☐ Yes / ☐ No

**검증 기준**

다음 행위가 **Hard Prohibition**으로 선언되어 있는가:

* FAIL 이후 자동 재시도
* FAIL set/group 결과를 정상 결과로 취급
* FAIL 원인 미기록 상태에서 다음 단계 진행
* FAIL run 결과를 FINAL 또는 learner-facing 산출물로 사용

---

### 통과 기준 충족 여부

* [ ] FAIL 중단 범위가 단계별로 단일하게 정의되어 있다
* [ ] FAIL 이후 아티팩트 보존 원칙이 일관된다
* [ ] QA/IRB 활용 범위가 명확히 제한되어 있다
* [ ] FAIL 우회·자동복구·부분성공이 전면 금지되어 있다

---

### CP-0 최종 판정 (템플릿 기입용)

* [ ] CP-0 통과
* [ ] CP-0 보완 필요

**결론:** ☐ **PASS** / ☐ **FAIL**

---

### CP-0 Canonical One-Line Anchor

> **Fail-Fast is enforced at the defined execution scope; artifacts are preserved for audit, but only fully PASSed pipelines may proceed to analysis or deployment.**


---


## CP-1. 카드 수 결정 권한 충돌 검사 (최우선)

### 검사 대상

* `S0_vs_FINAL_CardCount_Policy.md`
* `FINAL_Card_Count_Policy.md`
* `Allocation_Step_Card_Quota_Policy_v1.0.md`
* `Entity_Quota_Distribution_Policy_v1.0.md`
* Allocation / Execution / Step 관련 Canonical 문서 전반

---

### 확인 질문 1

**S0에서 카드 수를 “결정(decide)”하는 주체가 등장하는가?**

**판정: ❌ 없음 (적절)**

* `S0_vs_FINAL_CardCount_Policy.md`의 One-Line Binding에서 카드 수 결정 권한을 명확히 분리함:

  > *“S0 fixes card count per set (group × arm) with a constant payload.”*
  > *“FINAL fixes card count per group via allocation quotas.”*
  > *“S2 never decides counts; it executes exactly N.”*

* S0 문맥에서 카드 수는 **고정 payload(q = 12)** 로만 등장하며,
  어떠한 계산·추론·결정 주체도 정의되지 않음

* 카드 수 “결정”은 **FINAL Allocation(Code)** 의 단일 책임으로 한정됨

→ S0에서 카드 수 결정 주체가 등장할 여지 **문서상 제거됨**

---

### 확인 질문 2

**“allocate / distribute / weight / quota / score” 등 결정·분배 동사가 S0 맥락에 남아 있는가?**

**판정: ❌ 없음 (적절)**

* `Allocation_Step_Card_Quota_Policy_v1.0.md`에서:

  > *“This policy does NOT apply to Step S0.”*

  를 **Explicit Exclusion**으로 명시
* `Entity_Quota_Distribution_Policy_v1.0.md`에서:

  > *“This policy is never invoked in Step S0.”*
  > *“There is no entity-level quota distribution in S0.”*

  를 **Hard Rule**로 고정
* S0 관련 문서 어디에도
  `quota / distribution / weight / optimization` 개념이 **S0 책임으로 등장하지 않음**

→ FINAL 개념의 S0 유입 가능성 **구조적으로 차단**

---

## 통과 기준 충족 여부

### 1) 카드 수 결정 권한의 단일성

**충족 (PASS)**

* 카드 수 결정 권한은 **FINAL Allocation(Code)** 으로만 귀속
* S0, S1, S2, S3, S4 중 어느 단계도 카드 수를 “결정”하지 않음
* LLM 단계는 모두 **집행(execution) 또는 검증(enforcement)** 역할로 한정됨

---

### 2) S0 카드 수 고정성 (Set-level Payload)

**충족 (PASS)**

* S0는 **set-level fixed payload**만 사용
* Canonical 값: `q = 12 (exact)`
* dynamic quota, entity-level distribution, weighting 개념 **전면 금지**

---

### 3) S0 ↔ FINAL 의미적 방화벽

**충족 (PASS)**

* S0 vs FINAL 카드 수 정책을 **단일 앵커 문서**로 고정
* FINAL allocation 문서들에서 S0 적용을 **명시적으로 배제**
* 두 단계 간 개념적 연속성(축소판/사전단계) **부정**

---

## 조치 기록

* 수정/추가한 문구:

  ```text
  - “S0 fixes card count per set with a constant payload.”
  - “FINAL fixes card count per group via allocation quotas.”
  - “This policy does NOT apply to Step S0.”
  - “There is no entity-level quota distribution in S0.”
  ```
* 적용 문서:

  * `S0_vs_FINAL_CardCount_Policy.md`
  * `FINAL_Card_Count_Policy.md`
  * `Allocation_Step_Card_Quota_Policy_v1.0.md`
  * `Entity_Quota_Distribution_Policy_v1.0.md`

---

## CP-1 최종 판정 (템플릿 기입용)

* [x] S0에서 카드 수를 “결정”하는 주체가 존재하지 않는다
* [x] 카드 수 결정 권한은 FINAL Allocation으로 단일화되어 있다
* [x] S0 관련 문서에 dynamic quota / distribution 논리가 없다

**결론:** ☑ **CP-1 통과**

---

## CP-2. S0 Allocation 의미 오염 검사

### 검사 대상

* `S0_Allocation_Artifact_Spec.md`
* `S0_Fixed_Payload_Entity_Selection_Rule.md`
* `S0_vs_FINAL_CardCount_Policy.md`
* `Allocation_Step_Card_Quota_Policy_v1.0.md`
* `Entity_Quota_Distribution_Policy_v1.0.md`

---

### 확인 질문 1

**S0 allocation이 FINAL allocation처럼 카드 수를 계산·분배하는 것으로 오해될 여지가 있는가?**

**판정: ❌ 없음 (적절)**

* `S0_Allocation_Artifact_Spec.md`에서 S0 allocation을

  > *“recording step, not a decision step”*
  > *“does NOT compute, distribute, or optimize card counts”*

  로 **최상위 정의(one-line invariant)** 로 명시함
* `S0_vs_FINAL_CardCount_Policy.md`에서

  > *“There is no entity-level quota distribution in S0”*

  를 Hard Rule로 고정함
* FINAL allocation 문서들에서 **S0 적용을 명시적으로 배제**

→ S0 allocation을 FINAL allocation으로 오해할 경로가 **문서상 제거됨**

---

### 확인 질문 2

**“quota”, “ratio”, “importance” 등 FINAL 개념이 S0 allocation 문맥에 섞여 있는가?**

**판정: ❌ 없음 (적절)**

* `Allocation_Step_Card_Quota_Policy_v1.0.md`에

  > *“This policy does NOT apply to Step S0”*

  라는 **Explicit Exclusion** 문구 추가
* `Entity_Quota_Distribution_Policy_v1.0.md`에

  > *“In Step S0, there is no entity-level quota distribution”*

  를 Hard Rule로 명시
* S0 관련 Canonical 문서 어디에도
  `quota / ratio / importance / distribution / optimization` 개념이 **등장하지 않음**

→ FINAL 개념의 S0 유입 가능성 **차단 완료**

---

## 통과 기준 충족 여부

### 1) S0 allocation 정의의 단일성

**충족 (PASS)**

* S0 allocation = **대표 entity 선택 + artifact 생성**
* allocation은 **결정(decision)** 이 아니라 **기록(recording)** 단계임을 명시
* S0 allocation은 FINAL allocation의 축소판이 아님을 명확히 선언

---

### 2) 카드 수 고정성 (`q = 12`)

**충족 (PASS)**

* S0 set-level 카드 수는 `q = 12 (exact)`로 하드 고정
* entity-level 분배/계산/가중 로직은 **정책적으로 금지**

---

### 3) FINAL allocation과의 의미적 단절

**충족 (PASS)**

* FINAL allocation 문서에서 S0를 **명시적으로 제외**
* S0 vs FINAL 카드 수 정책을 **단일 앵커 문서**로 고정
* 두 단계 간 **개념적 방화벽(Firewall)** 완성

---

## 조치 기록

* 수정/추가한 문구:

  ```text
  - “S0 allocation does NOT compute, distribute, or optimize card counts.”
  - “S0 allocation is a recording step, not a decision step.”
  - “In Step S0, there is no entity-level quota distribution.”
  - “This policy does NOT apply to Step S0.”
  ```
* 적용 문서:

  * `S0_Allocation_Artifact_Spec.md`
  * `S0_vs_FINAL_CardCount_Policy.md`
  * `Allocation_Step_Card_Quota_Policy_v1.0.md`
  * `Entity_Quota_Distribution_Policy_v1.0.md`

---

## CP-2 최종 판정 (템플릿 기입용)

* [x] S0 allocation 정의가 단일하고 명확하다
* [x] 카드 수는 `q = 12 (exact)`로 하드 고정되어 있다
* [x] S0 allocation은 FINAL allocation을 정의하거나 암시하지 않는다

**결론:** ☑ **CP-2 통과**


---


## CP-3. S2 역할 침범 검사 (Execution Engine 보존)

### 검사 대상

* `Entity_Definition_S2_Canonical.md`
* S1/S2 관련 legacy 문서 편입분

---

### 확인 질문 1

**S2가 카드 수, 중요도, 비율, 점수 등을 판단·결정하는 것으로 읽힐 여지가 있는가?**

**판정: ❌ 없음 (적절)**

* `Entity_Definition_S2_Canonical.md`의 One-Line Definition에서 S2를

  > *“policy-agnostic execution stage”*
  > *“generates exactly N … and nothing more”*

  로 정의하여, **판단·결정 권한을 구조적으로 부여하지 않음**
* 동일 문서에서

  > *“S2 does not decide what to generate”*
  > *“S2 does not decide how many to generate”*

  를 **비협상(non-negotiable) 규칙**으로 명시
* 카드 수(`cards_for_entity_exact`)는 **외부에서 계산·주어지는 값**이며,
  S2는 이를 **집행(execution)** 만 수행하도록 고정됨

→ 카드 수·중요도·비율·점수 판단 주체로 S2가 오해될 가능성 **문서상 제거됨**

---

### 확인 질문 2

**“optimize”, “select”, “adjust” 등 정책·판단 동사가 S2 책임으로 남아 있는가?**

**판정: ❌ 없음 (적절)**

* `What S2 Is NOT` 섹션에서 다음 행위를 **명시적으로 금지**:

  * 카드 중요도 결정
  * quota 해석·부여
  * 카드 수 계산·추론·조정
  * entity 병합·분리·재해석
* “allocation / judgment / optimization / visual reasoning”을
  **형식적 선언이 아닌 금지 항목 리스트**로 차단

→ 정책·판단 동사의 S2 잔존 가능성 **구조적으로 차단**

---

## 통과 기준 충족 여부

### 1) S2 집행 역할의 단일성

**충족 (PASS)**

* S2 = **Execution only**
* 입력은 `(Entity, cards_for_entity_exact = N)`으로 고정
* S2는 입력 값에 대해 **추론·보정·해석 권한 없음**

---

### 2) 카드 수 집행의 정확성

**충족 (PASS)**

* `len(anki_cards) == cards_for_entity_exact`를 **binding invariant**로 명시
* “up to N”, “target N”, “approximately N” 표현 **전면 배제**
* 위반 시 **Hard Fail** 규칙 명시

---

### 3) 역할 위반 시 Fail-Fast 규칙

**충족 (PASS)**

* 카드 수 불일치
* forbidden key 존재
* entity 변경
* 비텍스트 출력

→ 모두 **즉시 실패(Fail-Fast)** 로 규정됨

---

## 조치 기록

* 수정/추가한 문구:

  ```text
  - “Step02 (S2) is a policy-agnostic execution stage … and nothing more.”
  - “S2 does not decide what to generate.”
  - “S2 does not decide how many to generate.”
  - “len(anki_cards) == cards_for_entity_exact (Hard Fail if violated).”
  ```
* 적용 문서:

  * `Entity_Definition_S2_Canonical.md`

---

## CP-3 최종 판정 (템플릿 기입용)

* [x] S2는 execution-only 역할로 단일하게 정의되어 있다
* [x] 카드 수·중요도·비율·정책 판단 권한이 전면 제거되어 있다
* [x] 역할 위반 시 hard-fail 규칙이 명시되어 있다

**결론:** ☑ **CP-3 통과**

---
## CP-4. 경계 침범 검사 (S3 ↔ S4)

### 검사 목적

S3와 S4 간 역할 경계가 **Canonical 계약 및 단계 정의에 따라 엄격히 준수되는지**를 검증한다.

본 CP는 다음 두 가지를 동시에 확인한다.

1) **S3 → S4 Input Contract 위반 여부**
   - S3가 state-only gate 원칙을 위반하여
     의미·추론·렌더링 정보를 생성·전달하지 않는지

2) **S4 자체 역할 침범 여부**
   - S4가 render-only stage 원칙을 위반하여
     의료적 의미, 정책, 선택, 판단을 수행하지 않는지

---

### 검사 대상 (Authoritative, Single Source)

* **S3 → S4 Canonical Contract (Single Source of Truth)**  
  `04_Step_Contracts/S3_to_S4_Input_Contract_Canonical.md`

* **관련 단계 Canonical 정의**
  * `Entity_Definition_S3_Canonical.md`
  * `Entity_Definition_S4_Canonical.md`

> ⚠️ archive 경로에 존재하는 이전 버전 문서는  
> 본 CP-4 판단에서 **참고·인용·근거로 사용할 수 없다**.  
> 경계 판단은 반드시 **Canonical 위치의 문서만**을 기준으로 한다.

---

### 확인 질문 A. S3 → S4 계약 위반 여부 (State-only Gate)

1. S3 Output이 Canonical 계약에 정의된 필드만 포함하는가?

   * decision (PASS / FAIL)
   * selected_card_ids (manifest)
   * selection_trace
   * qa_log

2. S3 Output에 **금지된 필드**가 포함되어 있지 않은가?

   * modality, plane, sequence_or_phase, lesion_class 등 의료 의미 필드
   * image_prompt, image_style, rendering_params 등 S4 전용 렌더링 지시자
   * 카드 텍스트 재작성, 신규 카드 생성, 설명 추가

3. S3가 카드 선택 결과 외의
   **의미·해석·요약·교육적 판단**을 산출하지 않았는가?

---

### 확인 질문 B. S4 역할 침범 여부 (Render-only Stage)

4. S4가 새로운 의료적 의미를 생성하거나 추론하지 않는가?

   * 진단, 감별, 소견 해석
   * modality / plane / sequence 추론
   * imaging feature 추가 또는 재해석

5. S4가 정책·선택·결정 권한을 가지지 않는가?

   * 카드 선택 또는 제외 ❌
   * 카드 수 / quota 판단 ❌
   * row_image_necessity(IMG_REQ / OPT / NONE) 재분류 ❌

6. S4가 upstream(S1/S3) 책임 영역을 침범하지 않는가?

   * S3 manifest(selected_card_ids)를 변경·보완하지 않음
   * S1에서 정의된 visual_type_category를
     **분기 키로만 사용**하고 의미 재해석하지 않음

7. S4 Output에 upstream으로 되돌아가는
   제어·피드백·QA 신호가 존재하지 않는가?

---

### 통과 기준 (Pass Criteria)

다음 조건을 **모두 만족**해야 CP-4를 통과한다.

* S3 Output이
  **“PASS/FAIL + manifest + trace + qa_log”** 구조만을 갖는다.
* S3 → S4 데이터 흐름이
  **선정 결과의 무변형 pass-through 계약**을 충족한다.
* S4는 render-only stage로서
  시각화·프레젠테이션 외 행위를 수행하지 않는다.
* 역할 위반 시 즉시 hard-fail 되도록
  코드 또는 QA 정책이 연결되어 있다.

---

### 실패 처리 (Hard Fail)

다음 중 하나라도 발견되면 CP-4는 **즉시 FAIL**로 판정한다.

* S3 Output에 forbidden field 존재
* S4가 S3 Output에 없는 의료적 의미를 생성·추론
* S4가 카드 선택, 정책, quota, 이미지 필요성 판단 수행
* Canonical 계약이 아닌 archive 문서를 근거로 경계 판단 수행

---

### 조치 기록 (필수)

* 위반 유형:
* 발견 위치 (파일 / 로그 / run_tag):
* 수정 조치:
* 재검증 일시:

---

## CP-5. Arm 비교 무효화 요소 검사 (RAG / Thinking)

### 검사 대상

* `ARM_CONFIGS_Provider_Model_Resolution.md` 
* `protocol_addendum_s_0_rag_thinking_option_b.md` 
* `S0 Thinking Policy — Gemini 2.5 Flash.md` 

---

### 확인 질문 1

**RAG/Thinking이 라벨만 있고 실질 실행 검증이 없는 상태에서도 실험을 허용하는가?**

**판정: ❌ 허용하지 않음 (적절)**

* Addendum에 명시적으로

  > *“Until the Acceptance Criteria are satisfied, S0 full runs are prohibited.”*
  > 라는 **하드 금지 규칙**이 존재함 
* Thinking 문서에서도 **API 파라미터 미반영 시 Fail**을 명시 

→ “라벨만 있는 실험”은 문서상 **명백히 불가**

---

### 확인 질문 2

**metadata 필드 누락 시에도 run을 허용하는 문구가 있는가?**

**판정: ❌ 없음 (적절)**

* RAG/Thinking Addendum에서 **metadata 최소 필드 세트**를 *Binding*으로 명시 
* Thinking 문서에서 **non-null 기록 실패 시 S0 Fail**을 명확히 규정 

→ metadata 누락 상태의 run은 **정책 위반**

---

## 통과 기준 충족 여부

### 1) AC 정의의 명확성

**충족 (PASS)**

* RAG: `rag_enabled`, `rag_sources_count`, `rag_queries_count` 명시 
* Thinking: `thinking_enabled`, `thinking_budget`, `thinking_mode` 명시 
* latency / tokens 기록 요구 존재 

---

### 2) AC 미충족 → S0 full run 금지

**충족 (PASS)**

* Addendum §1, §7에서 **명시적 금지** 

---

### 3) arm 간 비교는 AC 충족 후에만 허용

**충족 (PASS)**

* “Observable Arm Differences”를 AC 일부로 요구 
* arm 비교는 metadata 기반 검증 후에만 가능하도록 구조화됨

---

## 🔒 권장 조치: ARM_CONFIGS에 Hard Gate 문구 “흡수”

현재 Hard Gate는 **Addendum에만 존재**하므로,
**ARM_CONFIGS (상위 Canonical)** 에 아래 문구를 **그대로 추가**하는 것이 가장 정석입니다.

### 📌 삽입 위치 (권장)

`ARM_CONFIGS_Provider_Model_Resolution.md`
→ **Section 10. Change Control** 바로 위 또는 별도 섹션 신설

---

### ✅ Hard Gate 문구 (정본, 그대로 복붙)

## RAG / Thinking Acceptance Gate (S0 – Hard Rule)

For S0 QA experiments, RAG and Thinking are **experimental factors** and
**must be actually executed and measurably logged**.

**If the Acceptance Criteria are not satisfied, S0 full runs are prohibited.**

Minimum Acceptance Criteria include:
- `rag_enabled`, `thinking_enabled` recorded in metadata
- Non-null counts for retrieval (`rag_sources_count > 0` when enabled)
- Explicit thinking control applied at API level and reflected in metadata
- Latency (and tokens where available) recorded

**Arm-to-arm comparison is permitted only after all Acceptance Criteria pass.**

This rule is binding and non-negotiable.

---

## CP-5 최종 판정 (템플릿 기입용)

* [x] AC 정의가 명확하다
* [x] AC 미충족 → S0 full run 금지
* [x] arm 간 비교는 AC 충족 후에만 허용

**결론:** ☑ **CP-5 통과**

---

## 최종 판정

- [V] CP-1 통과
- [V] CP-2 통과
- [V] CP-3 통과
- [V] CP-4 통과
- [V] CP-5 통과

### 결론
- [V] **편입 승인 (다음 Canonical로 이동 가능)**
- [ ] 편입 보류 (위 CP 해결 후 재검증 필요)

---

## 편입 후 메모 (선택)
- 용어 통일 필요 사항:
- 향후 정리 대상 중복 문장:
- 링크만 남겨도 되는 문서:
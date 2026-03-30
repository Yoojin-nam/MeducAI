# MeducAI Pipeline — Canonical Governance & Index

**Status:** Canonical · Frozen
**Applies to:** MeducAI Pipeline (S0 → FINAL)
**Purpose:** 본 문서는 MeducAI 파이프라인에 존재하는 모든 Canonical 문서의 **권위 계층, 충돌 해결 규칙, 참조 우선순위**를 단일 지점에서 선언한다.

> 이 문서는 **새로운 정책을 정의하지 않는다.**  
> 이미 확정된 Canonical들을 **어떻게 읽고, 어떻게 충돌을 해석하며, 무엇을 최종 기준으로 삼을지**를 고정한다.

---

## 0. Non-Negotiable Rule (One-Line)

> **Any pipeline interpretation, execution, QA, IRB explanation, or code review must follow the Canonical hierarchy defined in this document.**

---

## 1. Canonical Hierarchy (Authoritative Order)

모든 문서는 아래 **Level 순서대로 권위를 가진다**.  
하위 Level 문서는 상위 Level 문서를 **절대 재정의할 수 없다**.

---

### 🔴 Level 0 — Pipeline Constitution (최상위 헌법)

**역할**  
- 파이프라인의 존재 목적과 철학
- Single Source of Truth(SSOT)
- LLM vs Code 책임 분리

**Canonical Documents**
- `Pipeline_Canonical_Specification.md`
- `Pipeline_Execution_Plan.md`

---

### 🟠 Level 1 — Execution Governance (실행·중단·정상성 규정)

**역할**  
- “언제 멈추는가”
- “무엇이 정상 run인가”
- FAIL 이후 산출물의 법적·연구적 지위

**Canonical Documents**
- `Pipeline_FailFast_and_Abort_Policy.md`
- `Runtime_Artifact_Manifest_Spec.md`

> ⚠️ 실행 중 FAIL/WARN 판단은 **항상 Level 1 문서가 최종 기준**이다.

---

### 🟡 Level 2 — Step & Allocation Contracts (역할·경계 계약)

**역할**  
- 각 Step(S0–S4, FINAL)의 권한과 금지
- 카드 수, 선택, 렌더링 책임 경계

**Canonical Documents**
- `S0_Allocation_Artifact_Spec.md`
- `Allocation_Step_Card_Quota_Policy.md` (FINAL only)
- `S0_vs_FINAL_CardCount_Policy.md`
- `ARM_CONFIGS_Provider_Model_Resolution.md`
- `Entity_Definition_S2_Canonical.md`
- `Entity_Definition_S3_Canonical.md`
- `Entity_Definition_S4_Canonical.md`
- `S3_to_S4_Input_Contract_Canonical.md`

---

### 🟢 Level 3 — Stabilization Logs & Addenda (근거·설명 자료)

**역할**  
- 과거 결정의 맥락 기록
- 구현 세부 및 실험 옵션 설명

**Documents (Non-Authoritative)**
- `Step01_Stabilization_Log_2025-12-16.md`
- `protocol_addendum_s_0_rag_thinking_option_b.md`
- `S0 Thinking Policy — Gemini 2.5 Flash.md`

> Level 3 문서는 **Canonical 해석 권한이 없다**.  
> 단, 상위 Canonical의 근거(reference)로만 사용된다.

---

## 2. Conflict Resolution Rules (Binding)

문서 간 해석 충돌이 발생할 경우, 아래 규칙을 **순서대로 적용**한다.

1. **Level이 높은 문서가 항상 우선**한다.
2. 동일 Level 내 충돌 시:
   - 더 **최근에 Canonical로 편입·동결된 문서**가 우선한다.
3. Level 3 문서는 **어떠한 경우에도** Level 0–2를 재정의할 수 없다.
4. 실행 중 판단(FAIL/WARN/ABORT)은 항상 **Level 1** 기준으로 판정한다.

---

## 3. IRB / QA / Methods Reference Map

아래는 외부 설명(IRB, 논문 Methods, QA 문서) 시 **반드시 따라야 할 참조 규칙**이다.

| 질문 | 참조 Canonical |
|---|---|
| 무엇이 정상 run인가 | `Runtime_Artifact_Manifest_Spec.md` |
| FAIL 시 어디까지 중단되는가 | `Pipeline_FailFast_and_Abort_Policy.md` |
| 카드 수는 누가 결정하는가 | `S0_vs_FINAL_CardCount_Policy.md` |
| S2가 무엇을 하는 단계인가 | `Entity_Definition_S2_Canonical.md` |
| S3가 왜 의미 추론을 안 하는가 | `Entity_Definition_S3_Canonical.md` |
| 이미지 생성 책임은 어디인가 | `Entity_Definition_S4_Canonical.md` |
| arm 비교의 정당성 | `ARM_CONFIGS_Provider_Model_Resolution.md` |

---

## 4. Canonical Merge & Change Control

### 4.1 Change-Sensitive Levels

- **Level 0–1 변경**
  - CP-0 (Governance) 필수
  - 전체 Pipeline 재검토 대상

- **Level 2 변경**
  - 해당 Step 관련 CP 재검증 필수

- **Level 3 변경**
  - Canonical 영향 없음 (기록 갱신만)

---

## 5. Mandatory Usage Rule

다음 행위는 **프로토콜 위반**으로 간주한다.

- Canonical Level을 무시한 코드 수정
- Level 3 문서를 근거로 실행 정책을 변경
- FAIL 상태 산출물을 정상 run으로 설명
- 본 Index 문서를 거치지 않은 Canonical 해석

---

## 6. Canonical Closing Statement

> **This document is the single authoritative index for MeducAI Pipeline Canonicals.**  
> **Any execution, interpretation, or explanation that ignores this hierarchy is invalid.**

---

**This document is Canonical and Frozen.**

---

## 📎 Appendix A. Execution Safety Canonical Index

> **Purpose**
> 본 Appendix는 MeducAI 파이프라인에서 *실행 중 인간 개입(human-applied changes)* 으로 인해 발생할 수 있는
> 구조적 붕괴, 재현성 손상, fail-fast 위반 위험을 방지하기 위한 **Execution Safety 계층의 Canonical 문서 목록**을 정의한다.
>
> 본 Appendix에 등재된 문서는 **운영 중 반드시 준수되어야 하는 실행 안전 규칙**이며,
> 코드 수정·패치·실험 재개 시 참조 우선순위를 가진다.

---

### A.1 Execution Safety Canonical Documents

아래 문서들은 **Execution Safety 계층의 Canonical 문서**로 지정된다.

| Document                                                                    | Status    | Scope     | Purpose                                                           |
| --------------------------------------------------------------------------- | --------- | --------- | ----------------------------------------------------------------- |
| `0_Protocol/01_Execution_Safety/Prompt_Rendering_Safety_Rule.md`            | Canonical | All Steps | Prompt 생성·렌더링 과정에서의 구조적 오류 및 fallback 오염 방지                       |
| `0_Protocol/01_Execution_Safety/File_Replacement_Patch_Delivery_Rule.md`    | Canonical | All Steps | 코드 수정 시 diff 기반 부분 적용을 금지하고, 파일 교체형 패치만 허용함으로써 인간 적용 오류를 구조적으로 차단 |

---

### A.2 Normative Requirement

본 Appendix에 등재된 문서는 다음과 같은 **규범적 효력(normative authority)** 을 가진다.

1. Execution Safety Canonical 문서는
   **Step(S0–FINAL), ARM, Provider, Mode(DEV_SMOKE / S0 / FINAL)** 와 무관하게 항상 적용된다.
2. 본 문서들과 충돌하는 실행 방식, 운영 관행, 비공식 가이드는 **무효**로 간주한다.
3. Execution Safety Canonical을 위반한 상태에서 생성된 결과물은
   **재현성(reproducibility) 및 실험 유효성 측면에서 무효(run invalid)** 로 판단할 수 있다.

---

### A.3 Relationship to Other Canonical Layers

* 본 Appendix는 `00_Governance` 계층에 속하되,
  **Execution 단계에서의 인간 개입 위험 관리**를 명시적으로 분리하여 다룬다.
* Card Count, Allocation, Step Contract, ARM 비교 정책보다
  **상위의 안전 계층(safety envelope)** 으로 해석한다.
* Execution Safety Canonical은
  *실험 설계의 자유*보다 *실험 붕괴 방지*를 우선한다.

---

### A.4 Amendment Policy

* 본 Appendix에 새로운 Execution Safety Canonical을 추가할 경우:

  * 신규 문서는 반드시 **01_Execution_Safety/** 하위에 위치해야 한다.
  * `Canonical_Merge_Log`에 편입 사실을 기록해야 한다.
* 기존 항목 수정 시:

  * Canonical Versioning Policy에 따라
    **archive → new canonical** 절차를 따른다.

---

## 📎 Appendix B. Objective Governance & Source Traceability

> **Purpose**  
> 본 Appendix는 MeducAI 파이프라인에서 사용되는 모든 **Objective(학습 목표)**가  
> 어떤 공식 원천 문서에 근거하여 정의·변환·사용되는지를 규정하는  
> **Objective 거버넌스 및 출처 추적(Source Traceability)** Canonical을 명시한다.
>
> Objective는 MeducAI 파이프라인에서 **가장 상위 의미 단위**이며,  
> 그 출처와 변형 규칙은 실행, QA, IRB 설명, 논문 Methods에서 **항상 추적 가능**해야 한다.

---

### B.1 Objective Source Traceability Canonical

아래 문서는 MeducAI에서 **Objective의 존재 정당성, 출처, 변형 규칙**을 정의하는
**Governance Canonical**이다.

| Document | Status | Scope | Purpose |
|--------|--------|-------|--------|
| `0_Protocol/00_Governance/Objective_Source_Traceability_Spec.md` | Canonical | All Objectives | Objective의 1차 원천(Source), 파생 과정, LLM 개입, 난이도(B/A/S) 처리 규칙을 정의 |

---

### B.2 Normative Authority

본 Appendix에 등재된 문서는 다음과 같은 **구속력(normative authority)**을 가진다.

1. 모든 Objective는  
   **Primary Source(공식 문서)** 없이 생성·수정·사용될 수 없다.
2. Objective에 대한 해석·번역·정제는  
   반드시 `Objective_Source_Traceability_Spec.md`에 정의된 규칙을 따른다.
3. 본 Canonical을 위반한 Objective를 포함한 결과물은  
   **QA, 연구 분석, IRB 설명에서 무효**로 간주될 수 있다.

---

### B.3 Relationship to Other Canonical Levels

- 본 Appendix는 **Level 0–1 문서를 재정의하지 않는다**.
- Objective 관련 해석 충돌 시:
  1. `Objective_Source_Traceability_Spec.md`
  2. `Evaluation_Unit_and_Scope_Definition.md`
  3. `Groups_Canonical_Freeze.md`
  순으로 참조한다.
- Objective 단위에서는 **출제 비율(weight)** 개념을 적용하지 않으며,  
  출제 비율은 Group 단계에서만 적용된다.

---

### B.4 Mandatory Usage Rule

다음 행위는 **프로토콜 위반**으로 간주한다.

- Source가 명시되지 않은 Objective 사용
- Curriculum과 무관한 Objective 생성
- B/A/S 난이도를 출제 난이도로 해석
- Objective 수준에서 출제 비중 또는 중요도 조정

---

> **Canonical Note**  
> Objective는 “문제 생성의 재료”가 아니라  
> **MeducAI 파이프라인 전체를 지탱하는 의미적 헌법 단위**이다.

---

## 📎 Appendix C. Prompt Governance SSOT (Cognitive Alignment)

**Canonical SSOT (Prompt governance):**
- `0_Protocol/00_Governance/supporting/Prompt_governance/Prompt_Engineering_and_Cognitive_Alignment.md`

**Reference (paper summary):**
- `0_Protocol/00_Governance/supporting/Prompt_governance/Yaacoub_2025_Lightweight_Prompt_Engineering_Review.md`

  
---

# QA Evaluation Rubric – MeducAI (v2.0, Canonical)

**Aligned with:** MeducAI QA Framework v2.0
**Date:** 2025-12-15
**Status:** Archived (applies prospectively to S0 & S1)
**Superseded by:** `0_Protocol/06_QA_and_Study/QA_Operations/QA_Evaluation_Rubric.md`
**Do not use this file for new decisions or execution.**

---

## 0. Purpose & Scope

본 Rubric은 **MeducAI Pipeline-1 QA(Step S0, S1)**에서
AI 생성 학습 콘텐츠를 **일관되고 재현 가능하게 평가**하기 위한
**공식 평가 기준(Evaluation Rubric)**이다.

본 문서는 다음 목적을 가진다.

* 평가자 간 변이를 최소화
* S0(모델 선택)와 S1(배포 승인)의 **의사결정 규칙을 수치화**
* IRB·논문(Paper-1)에서 **평가 기준의 사전 고정(pre-specified)** 근거 제공

---

## 1. Evaluation Units (Framework-aligned)

### 1.1 Step S0 (Expert QA)

* **Unit:** **Set**

  * = group × arm 결과물 묶음
  * 포함:

    * Master Table (or summary table)
    * Evaluation Anki payload (**12 cards, fixed**)
    * Infographic (if generated)

### 1.2 Step S1 (Release Gate)

* **Unit:** **Card**

  * 개별 Anki 문항 (Front / Back / Meta)

---

## 2. Core Evaluation Dimensions (Canonical)

**Reference:** For detailed metric definitions, see `05_Pipeline_and_Execution/QA_Metric_Definitions.md`.

### 2.1 Technical Accuracy (Safety-Critical)

**Definition**
의학적 사실성, 가이드라인 적합성, 임상적 안전성 평가.

> 본 항목은 **S0/S1 공통 Hard Gate**이며, 다른 모든 지표보다 우선한다.

#### Scale (Fixed)

|   Score | Definition                    |
| ------: | ----------------------------- |
| **1.0** | 명백한 오류 없음                     |
| **0.5** | 경미한 부정확성, 애매한 표현, 수정 필요       |
| **0.0** | 명백한 사실 오류, 임상적으로 위험, 시험 오도 가능 |

#### Canonical Rule

* **Score = 0.0 → Blocking Error**
* Blocking Error는:

  * S0: 해당 **arm 탈락 조건**
  * S1: **배포 FAIL 판정에 직접 반영**

> Accuracy = 0.0 ⇔ Blocking Error
> (QA Framework v2.0과 정의 동일)

---

### 2.2 Clinical / Exam Relevance (Secondary)

**Definition**
해당 콘텐츠가 영상의학과 전문의 시험 및 수련 목표에 얼마나 부합하는가.

#### Scale (Likert 1–5)

| Score | Interpretation |
| ----: | -------------- |
|     1 | 시험과 거의 무관      |
|     2 | 낮은 관련성         |
|     3 | 보통 수준          |
|     4 | 높은 시험 적합성      |
|     5 | 핵심 고빈도 시험 주제   |

**Notes**

* S0에서 **descriptive / secondary outcome**
* S1에서는 **gate rule에 직접 사용하지 않음**

---

### 2.3 Clarity & Readability (Secondary)

**Definition**
학습자 관점에서의 명확성, 구조적 이해 용이성, 오해 가능성.

#### Scale (Likert 1–5)

| Score | Interpretation |
| ----: | -------------- |
|     1 | 혼란·오해 가능성 높음   |
|     2 | 구조 불량          |
|     3 | 이해 가능하나 개선 필요  |
|     4 | 명확하고 잘 정리됨     |
|     5 | 매우 명확, 학습 친화적  |

---

## 3. Overall Card Quality (Primary Endpoint for S0 Non-Inferiority)

### 3.1 Overall Card Quality (Required for S0)

* Set 내 카드들의 **전반적 품질**에 대한 종합 평가
* 단위: **Likert 1–5 scale**

| Score | Interpretation |
| ----: | -------------- |
|     1 | 매우 나쁨        |
|     2 | 나쁨           |
|     3 | 보통           |
|     4 | 좋음           |
|     5 | 매우 좋음        |

**Evaluation guidance:**
* 세부 항목(정확성/가독성/교육목표 부합성)을 **종합 판단**으로 반영
* 카드 문항만 포함 (테이블/인포그래픽 제외)

> 본 지표는 S0 non-inferiority 분석의 primary endpoint로 사용됩니다.

---

## 4. Role-specific Evaluation Guidance

### 4.1 Attending Physician

* **Safety authority**
* Accuracy = 0.0 (blocking) 판정에 최종 권한
* 임상적·시험적 적합성의 기준점(anchor)

### 4.2 Resident

* **Usability / clarity evaluator**
* 학습자 관점의 명확성 및 가독성 평가
* Overall card quality 평가의 주 담당

---

## 5. Decision Logic Mapping (Framework-aligned)

### 5.1 Step S0 (Model Selection)

* **Hard Gate**

  * Card-level blocking error rate ≤ 1%
* **Primary Non-Inferiority Endpoint**

  * Overall Card Quality (Likert 1–5)
  * Reference: Arm E (High-End, gemini-3-pro-preview)
  * Margin: Δ = 0.5 (on 1–5 scale)
* Accuracy / Overall Quality 외 점수는 **보조적 판단 근거**

---

### 5.2 Step S1 (Release Gate)

* **Only decisive metric**

  * Card-level blocking error (Accuracy = 0.0)
* Likert 점수는:

  * IRR 계산
  * Descriptive reporting 용도

---

## 6. Inter-Rater Reliability (IRR)

본 Rubric 점수는 다음 IRR 지표 산출에 사용된다.

| Dimension                    | Metric           |
| ---------------------------- | ---------------- |
| Technical Accuracy (0/0.5/1) | **Fleiss’ κ**    |
| Likert (Relevance, Clarity)  | **Weighted κ**   |
| (Optional) Multi-rater       | Krippendorff’s α |

IRR는 **S1 anchor subsample (m = 300)**에서 산출한다.

---

## 7. Prohibited Inferences (Bias Control)

평가자는 다음을 **추론하거나 고려해서는 안 된다**.

* 모델 종류, 회사, 비용
* arm 배치
* prompt 설계
* generation 전략

평가는 **콘텐츠 자체 품질**에 한정한다.

---

## 8. Versioning & Freeze Policy

* 본 문서는 **Evaluation Rubric v2.0 (Canonical)**이다.
* S0/S1 실행 중 수정 불가.
* 변경 시:

  * v2.1로 상향
  * 변경 사유 및 적용 시점 명시
  * **prospective only**

---

## Official Statement

> This evaluation rubric operationalizes expert judgment into reproducible, framework-aligned quality metrics for MeducAI Pipeline-1 QA (S0/S1), with safety-first decision rules and non-inferiority-aware efficiency optimization.

---

## Appendix B. Blocking Error Subtypes and Editing Reason Tags

For descriptive and exploratory analyses, blocking errors may be annotated with non-mutually exclusive subtypes, without affecting gate rules.

### B.1 Blocking Error Subtypes (Optional Annotation)

- Factual error (guideline mismatch or incorrect medical fact)
- Ambiguity leading to incorrect exam inference
- Outdated recommendation or terminology
- Clinically dangerous simplification or omission

Subtype annotation is used solely for post-hoc characterization and does not alter the binary blocking decision.

### B.2 Editing Reason Tags (Optional)

When editing is performed, reviewers may optionally record one or more of the following reasons:
- Factual correction
- Wording or phrasing clarification
- Structural reorganization
- Difficulty calibration
- Other (free text)

These tags are descriptive and are not used in any gate or optimization decision.

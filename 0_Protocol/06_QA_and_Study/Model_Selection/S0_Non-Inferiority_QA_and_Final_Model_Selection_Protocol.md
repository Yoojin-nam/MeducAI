# MeducAI

## S0 Non-Inferiority QA & Final Model Selection Protocol

### **SUPERSEDED — DO NOT USE**

**Status:** **SUPERSEDED**
**Version:** **v1.1**
**Superseded by:**
- `0_Protocol/06_QA_and_Study/QA_Framework.md` (Section 2.7)
- `0_Protocol/06_QA_and_Study/QA_Operations/S0_Noninferiority_Criteria_Canonical.md` (Canonical implementation)
- `0_Protocol/06_QA_and_Study/Study_Design/Statistical_Analysis_Plan.md` (Section 8.1.1)
**Date:** 2025-12-17
**Superseded Date:** 2025-12-20

**⚠️ IMPORTANT:** This document is **outdated** and does not reflect the current implementation. The actual S0 non-inferiority framework uses:
- **Endpoint:** Mean Accuracy Score (0/0.5/1), not Overall Card Quality (Likert 1–5)
- **Margin:** Δ = 0.05 (mean score scale), not Δ = 0.5 (Likert scale)
- **Two-layer framework:** Safety gate + NI gate
- **Baseline:** Arm A (default), not Arm E

**Please refer to the superseding documents listed above.**

> 본 문서는 S0 단계에서 수행되는 **비열등성 평가(Statistical Evaluation)** 와
> 그 결과를 이용한 **최종 모델 선택(Decision Layer)** 까지를 포함하는
> 단일 Canonical Protocol이다.
> 본 문서에 명시되지 않은 사후 해석·선택 규칙은 허용되지 않는다.

---

## 1. Purpose

본 프로토콜의 목적은 MeducAI 파이프라인에서 생성된 학습 카드 콘텐츠에 대해,

1. **Test arm**이 **Reference arm** 대비
   교육적으로 의미 있는 품질 저하가 **허용 한계(Δ)를 초과하지 않는지**를
   **non-inferiority 프레임**으로 검증하고,
2. **비열등하다고 판정된 arm들 중에서**
   **시간·비용 효율이 가장 우수한 arm을 최종 배포 모델로 선택**하기 위한
   **사전 정의된 평가·의사결정 규칙**을 제공하는 것이다.

본 단계(S0)는 **early-phase non-inferiority screening + operational optimization** 단계로 정의한다.

---

## 2. Study Design Overview

### 2.1 Unit Definitions

* **Group:** 임상·교육적으로 일관된 커리큘럼 단위
* **Arm:** LLM 설정 조건(provider / model / prompt / RAG / thinking 등)
* **Set:** Group × Arm
* **Card:** 학습자에게 제시되는 최소 학습 문항 단위

### 2.2 Experiment Scale (Fixed)

* **Groups:** 18
* **Arms:** 6
* **Sets:** 108
* **Evaluators:** 전공의 9명 + 전문의 9명
* **Evaluation:** set당 2인 교차평가

---

## 3. Non-Inferiority Framework (Statistical Evaluation Layer)

### 3.1 Reference Arm

* **Reference Arm: Arm E (High-End, gemini-3-pro-preview)**
* **Rationale:** 같은 vendor (Google) 내 고성능 기준으로, candidate arms (A–D)와 vendor 일관성 확보
* **Note:** Arm F (GPT-5.2)는 external benchmark/anchor로서 유지되지만, primary non-inferiority 비교의 reference는 Arm E입니다.

### 3.2 Primary Endpoint

* **Overall Card Quality (1–5 Likert)**

  * 카드 문항만 포함
  * 테이블/인포그래픽은 포함하지 않음

### 3.3 Non-Inferiority Margin

* **Δ = 0.5 (on 1–5 Likert scale)**

> 평균 반 점 이내의 품질 저하는
> 교육적으로 허용 가능한 최소 손실(minimal clinically/educationally important difference)로 정의한다.

### 3.4 Hypotheses

* **H₀:** μ_candidate − μ_reference ≤ −0.5
* **H₁:** μ_candidate − μ_reference > −0.5

### 3.5 Decision Rule

* **one-sided 95% CI 하한 > −0.5 → Non-inferior**

---

## 4. Unit of Analysis & Validity

* **Statistical unit:** Group (n = 18)
* 반복측정(paired) 구조
* 카드 수·세트 수·평가자 수는 **정밀도 보조 요소**로만 작용

n=18은 **non-inferiority early-phase pilot으로서 실무적 하한선**으로 정의한다.

---

## 5. Card Sampling Rule (MI-CLEAR-LLM aligned)

* **엔티티당 2문항**
* **6 엔티티 × 2문항 = 12 cards / set**

### Justification

* 단일 문항의 우연성 완화
* 엔티티 단위 품질 추적 가능
* blocking error 탐지 확률 증가

이는 **MI-CLEAR-LLM의 재현성·추적가능성·위험통제 원칙을 강화하기 위한 최소 반복(minimum replication)** 규칙이다.

---

## 6. QA Scope Definition (Risk-Based)

### 6.1 Included in Primary Analysis

* **Card content only**

### 6.2 Excluded from Primary Analysis

* Master Table
* Diagram
* Table Infographic

위 산출물은 **upstream 보조 콘텐츠**로 간주하며,
통계적 non-inferiority 분석에는 포함하지 않는다.

---

## 7. Table & Diagram & Infographic Safety Gate (Secondary QA)

### 7.1 Purpose

* 테이블/다이어그램/인포그래픽에서 발생 가능한 **치명 오류 탐지**
* MI-CLEAR-LLM 위험 기반 QA 근거 확보

### 7.2 Gate Items (Integrated)

> **⚠️ 중요**: 테이블, 다이어그램, 인포그래픽은 **동일한 기준**으로 평가합니다.

1. **Critical Error (Yes/No)**

   * 임상 판단·학습을 심각히 왜곡할 수 있는 사실 오류
2. **Scope / Alignment Failure (Yes/No)**

   * Group Path / objectives와의 명백한 불일치

* **PASS:** 둘 다 No
* **FAIL:** 하나라도 Yes

> Gate FAIL은 **수정 플래그**로만 기록되며
> 카드 점수 및 NI 결과에는 영향을 주지 않는다.

---

## 8. QA Form Structure (One-Screen)

### Card Evaluation (Primary)

* Blocking error (Y/N + 1줄 근거)
* Overall card quality (1–5)
* Edit time bucket (0–1 / 1–3 / 3–5 / >5분)
* 조건부 근거 코멘트(최악 1–2장)

### Table/Diagram/Infographic Gate (Secondary)

* Critical error (Y/N)
* Scope failure (Y/N)

---

## 9. Workload Assumption

* **10분 / set (운영 가정)**

  * 카드 평가: 약 8분
  * 테이블/다이어그램/인포그래픽 게이트: 1–2분
* 실제 소요 시간은 self-reported bucket으로 기록

---

## 10. Statistical Analysis Plan (S0)

### 10.1 Primary Analysis (Canonical)

```text
overall_card_quality ~ arm + (1 | group) + (1 | rater_pair)
```

* Mixed-effects model
* arm effect에 대해 one-sided 95% CI 산출

### 10.2 Secondary (Descriptive)

* Blocking error rate
* Table/Diagram/Infographic gate failure rate

---

## 11. Final Model Selection Rule

### (Decision Layer — Post Non-Inferiority)

### 11.1 Eligibility

다음 조건을 **모두 만족한 arm만** 최종 선택 후보가 된다.

1. **Non-inferiority 통과**
2. **Safety gate에서 중대한 우려 없음**

---

### 11.2 Decision Criteria (Pre-Specified)

비열등 arm들 간 비교 기준:

1. **Cost Efficiency**

   * 평균 API 비용
   * arm당 총 비용 대비 산출물 수
2. **Latency**

   * 평균 생성 시간

모든 지표는 **run_tag 기반 로그**로 산출한다.

---

### 11.3 Selection Rule

* **Primary rule:**

  * 비열등 arm 중
  * **비용 최소화 우선** (Cost → Latency)

* **Tie-breaker (순차 적용):**

  1. 더 낮은 blocking error 발생
  2. 운영 안정성(실패율, 재시도율)
  3. 더 높은 평균 Overall Card Quality 점수

* **Fallback policy:**

  * 비열등 arm이 없는 경우, Reference Arm (E) 또는 Arm F로 전체 생성 진행 가능

---

### 11.4 Reporting

* 최종 선택은 **통계적 우월성 주장으로 해석하지 않는다**
* **운영·배포 최적화 결정**임을 명시한다

---

## 12. MI-CLEAR-LLM Alignment Summary

| 원칙        | 구현                       |
| --------- | ------------------------ |
| 명확한 단위 정의 | Group / Arm / Set / Card |
| 재현성       | 고정 샘플링 규칙, run_tag       |
| 추적가능성     | entity 반복, gate 로그       |
| 위험 기반 QA  | 카드 중심 + 보조 게이트           |

---

## 13. Status Declaration

본 문서는 **MeducAI S0 단계의 유일한 Canonical Protocol**이며
**Canonical v1.1 (FROZEN)** 으로 동결된다.

* 모든 QA 배포, 분석, 모델 선택은 본 문서를 따른다.
* 변경이 필요할 경우 **v2.0 Major Update**로만 허용한다.
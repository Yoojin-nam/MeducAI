# Study Design – MeducAI (v5.0)

**Date:** 2026-01-04  
**Status:** Canonical (Prospective; pre-specified)  
**Supersedes:** Study_Design_MeducAI_v4.1  
**Aligned with:** QA Framework v2.0, SAP v2.1, Survey Overview v2.1, EDA Decision Interpretation, FINAL_QA_Research_Design_Spec v1.0

---

## 1. Overall Study Architecture

MeducAI is designed as a **three-paper research portfolio**, with each paper addressing a distinct research question while sharing a common data infrastructure.

### 1.1 Three-Paper Structure

| Paper | Title | Research Question | Data Source |
|-------|-------|-------------------|-------------|
| **Paper 1** | S5 Multi-agent 검토 재작성 시스템의 신뢰도 | S5 multi-agent QA 시스템이 인간 전문가 수준의 품질 검증을 수행할 수 있는가? | FINAL QA (1,350 Resident + 330 Specialist) |
| **Paper 2** | MLLM 생성 이미지의 신뢰도 | MLLM이 생성한 의료 교육 이미지가 임상적으로 정확하고 교육적으로 유용한가? | Visual Modality Sub-study + Table Infographic Evaluation |
| **Paper 3** | 교육효과 전향적 관찰연구 | MeducAI 생성 교육자료가 전문의 시험 준비에 효과적인가? | Baseline + FINAL 설문 (IRB 승인) |

### 1.2 Pipeline Structure

연구는 두 개의 파이프라인으로 구성됩니다:

- **Pipeline-1 (Paper 1 & 2)**: Expert QA & System Validation  
  목적: S5 multi-agent 시스템 및 MLLM 이미지 생성의 신뢰성 검증

- **Pipeline-2 (Paper 3)**: Prospective Observational UX Study  
  목적: 실제 사용 환경에서 교육 효과 평가

파이프라인 간 분석은 **독립적**으로 수행됩니다.

---

## 2. Conceptual Rationale

### 2.1 Group-first Educational Modeling

Based on EDA of 1,767 radiology learning objectives collapsed into **312 semantically coherent groups**, MeducAI adopts a **Group-first deployment strategy**.

Key justifications:
- Objective-level deployment is impractical and noisy.
- Curriculum weight is highly concentrated (top 20% of groups ≈ 50% of total weight).
- Group-level handling enables scalable QA, representative sampling, and reproducible allocation.

All downstream processes—QA sampling, card budgeting, table/infographic generation—operate at the **Group** level.

---

## 3. Paper 1: S5 Multi-agent 검토 재작성 시스템의 신뢰도

### 3.1 Design Overview

Paper 1은 S5 multi-agent 시스템의 신뢰도를 검증합니다.

**핵심 질문**: "S5 multi-agent 시스템이 인간 전문가 수준의 품질 검증을 수행할 수 있는가?"

**연구 설계**:
- **연구 유형**: 진단 정확도 연구 (Diagnostic Accuracy Study)
- **표본**: 1,350 Resident + 330 Specialist 평가
- **Reference Standard**: 인간 전문가 (전공의 + 전문의)
- **Index Test**: S5 Multi-agent 시스템

### 3.2 Historical Context: S0 Model Selection

Paper 1 이전에 수행된 S0 단계에서 배포 모델이 선정되었습니다:

1. **Step S0:** 6-arm factorial expert QA for deployment model selection
2. **Step S1:** One-shot acceptance sampling for full-scale release approval

This pipeline prioritizes **patient safety analogues**, operational efficiency, and reproducibility.

---

### 3.2 Step S0 – Expert QA (Model Selection)

#### 3.2.1 Design

- **Design type:** Factorial, non-inferiority-oriented expert evaluation
- **Arms:** 6 fixed arms varying by model scale, reasoning, and retrieval configuration
- **Unit of analysis:** Set (= group × arm artifact bundle)

Each Set includes:
- One master table (or summary table)
- A fixed **12-card Anki payload**
- Infographic (if applicable)

The 12-card payload is fixed to standardize workload and reduce variance across arms.

---

#### 3.2.2 Sampling Strategy

- **Sampling frame:** All 312 groups
- **Sample size:** 18 groups (canonical)
- **Sampling method:** Weight-stratified sampling based on EDA-derived group weights

Hard coverage constraints ensure representation across:
- Subspecialties
- Imaging modalities
- High- and low-weight (tail) groups

---

#### 3.2.3 Evaluation & Roles

- **Per set:** 2-person paired cross-evaluation
  - 1 board-certified attending radiologist (safety authority)
  - 1 senior radiology resident (usability and clarity evaluator)

Primary endpoints:
1. **Technical accuracy (blocking error rate)** – safety hard gate

Secondary endpoints:
- **Overall Card Quality (Likert 1–5)** – used for non-inferiority analysis
- Clarity, relevance, cost, and latency

---

#### 3.2.4 Decision Logic

- Arms exceeding a **1% blocking error rate** are immediately excluded.
- Among safety-passing arms, candidate arms (A–D) are compared to the reference arm (E, High-End) using a **one-sided non-inferiority framework** on Overall Card Quality (Δ = 0.5 on 1–5 Likert scale).
- Low-cost arms are eligible for selection only if non-inferiority is demonstrated.

The selected arm is **conditionally frozen** as the deployment model.

---

### 3.3 FINAL QA Design (Paper 1 Primary Data)

After S0 freeze, the selected deployment model is used to generate the full content set (~6,000 cards).

#### 3.3.1 Evaluator Composition

| 역할 | 인원 | 할당량 | 역할 |
|------|------|--------|------|
| Resident (전공의) | 9명 | 150개/인 (총 1,350개) | 주요 감사 및 안전성 검증 |
| Specialist (전문의) | 11명 | 30개/인 (총 330개) | Reference standard, 전문 분야별 검토 |

#### 3.3.2 S5 Decision Classification

- **PASS**: `regeneration_trigger_score >= 70.0` AND `s5_was_regenerated == False`
- **REGEN**: `regeneration_trigger_score < 70.0` OR `s5_was_regenerated == True`

#### 3.3.3 Sampling Strategy ("Selection and Focus")

- **REGEN 그룹**: Census (≤200) 또는 Cap (=200)
- **PASS 그룹**: 나머지 슬롯 집중 (~1,100-1,300) → FN < 0.3% 검증
- **Calibration**: 5개 공통 문항 × 9명 Resident = 45 슬롯 → Inter-rater reliability

#### 3.3.4 Primary Outcomes

| 분석 | 메트릭 | 타겟 |
|------|--------|------|
| Safety Validation (PASS) | False Negative Rate | < 0.3% (95% CI) |
| Completeness (REGEN) | Accept-as-is Rate | Census review |
| Tool Effect | Pre-S5 → Post-S5 변화율 | Δ 분석 |

**Major Error Definition**:
```
major_error = TRUE if:
  - blocking_error = Yes OR
  - technical_accuracy = 0.0 OR
  - image_blocking_error = Yes
```

---

## 4. Paper 2: MLLM 생성 이미지의 신뢰도

### 4.1 Design Overview

Paper 2는 MLLM이 생성한 의료 교육 이미지의 임상적 정확성을 검증합니다.

**핵심 질문**: "MLLM이 생성한 의료 교육 이미지가 임상적으로 정확하고 교육적으로 유용한가?"

### 4.2 Visual Modality Sub-study

#### 4.2.1 Comparison Design

| 평가자 | Illustration (S5-refined) | Realistic (MLLM Raw) | 총 평가량 |
|--------|---------------------------|----------------------|-----------|
| Resident | 1,350개 | 330개 | 1,680개 |
| Specialist | 330개 | 330개 | 660개 |

**Paired Design**: 동일 330개 문항에 대해 Illustration vs Realistic를 동일 평가자가 평가

#### 4.2.2 Analysis Plan

- **Paired Comparison**: Wilcoxon signed-rank test
- **Inter-rater Reliability**: ICC (Resident vs Specialist)
- **Expertise × Modality Interaction**: 2×2 mixed-effects model

### 4.3 Table Infographic Evaluation

**See**: `Paper2_Image_Reliability/Paper2_Table_Infographic_Evaluation_Design.md`

| 항목 | 값 |
|------|-----|
| 전체 인포그래픽 | 833개 |
| 평가 샘플 | 250개 (30%) |
| 평가자 수 | 5명 |
| 1인당 평가량 | 80개 |
| 통계적 보장 | Error rate margin ±2.7% |

---

## 5. Paper 3: 교육효과 전향적 관찰연구

### 5.1 Design Overview

Paper 3는 MeducAI 생성 교육자료의 실제 교육 효과를 검증합니다.

**핵심 질문**: "MeducAI FINAL 산출물이 전문의 시험 대비에 실질적으로 도움이 되는가?"

| 항목 | 내용 |
|------|------|
| 연구 유형 | 전향적 관찰연구 (Prospective Observational User Study) |
| 대상 | 영상의학과 4년차 전공의 (전문의 시험 응시자) |
| 상태 | IRB 진행 중, 1/7 배포 예정 |

### 5.2 Study Timeline

```
1/7 배포          ~6주 사용           2월 시험         시험 후
┌────┐           ┌───────────┐       ┌────────┐      ┌────────┐
│동의서│ ────────▶│ MeducAI  │──────▶│ 전문의 │─────▶│ FINAL  │
│+    │           │ 자율 사용│       │ 시험   │      │ 설문   │
│Base-│           │          │       │        │      │        │
│line │           │          │       │        │      │        │
└────┘           └───────────┘       └────────┘      └────────┘
```

### 5.3 Survey Design

**Baseline Survey** (배포 시점):
- 동의서, 기본정보, 학습 컨텍스트
- LLM/AI 경험, 인지 부하, 자기효능감
- 생활·정서 요인

**FINAL Survey** (시험 후):
- 사용량, 교육 품질, 기술적 정확성
- 효율성, 신뢰도, 전반적 만족도, NPS

### 5.4 Outcomes

#### 5.4.1 Co-Primary Outcomes

| Outcome | 측정 | Rationale |
|---------|------|-----------|
| Extraneous Cognitive Load | Leppink et al. scale (1–7) | 교수 설계 품질 측정 |
| Learning Efficiency | 0–100% time reduction | 교육 효율성 |
| Perceived Exam Readiness | Change score (Baseline → FINAL) | 시험 준비 자신감 |
| Knowledge Retention | 1–7 Likert | 장기 학습 효과 |

#### 5.4.2 Key Secondary Outcomes

- Intrinsic and germane cognitive load (Leppink et al. scale)
- Academic self-efficacy (MSLQ-derived)
- Learning satisfaction (validated online learning satisfaction scale)
- Technology acceptance (TAM)
- Trust in AI-generated educational content
- Perceived exam score improvement (self-reported)
- Study time efficiency (objective, from usage logs)

#### 5.4.3 Covariates

- Stress, sleep quality, mood stability, physical activity
- Training level and institutional characteristics
- Baseline exam readiness, prior LLM experience

---

## 6. Statistical Considerations

- All hypotheses, endpoints, and analyses are pre-specified in **SAP v2.1**.
- Paper 1/2 (Pipeline-1) 및 Paper 3 (Pipeline-2) 분석은 독립적으로 수행됩니다.
- No multiplicity correction is applied; secondary analyses are exploratory.

---

## 7. Bias Control and Reproducibility

- **Full rater blinding** in Paper 1 & 2 QA
- **2-Pass Workflow**: Pre-S5 (immutable, primary) + Post-S5 (tool effect)
- **MI-CLEAR-LLM compliance** for all generation and QA steps
- Version-controlled prompts, configuration logs, and freeze declarations

---

## 8. Ethical and Governance Considerations

- Paper 1 & 2: Expert evaluators, no human subject outcomes
- Paper 3: IRB 승인 하에 informed consent로 진행
- QA evaluators are explicitly excluded from Paper 3 participation

---

## 9. Publication Roadmap

```
1월         2월         3월         4월         5월         6월
├───────────┼───────────┼───────────┼───────────┼───────────┤
            
┌─────────────────────────────────────────────┐
│ Paper 1: QA 완료 → 분석 → 작성 → 투고      │ → 투고 (3-4월)
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Paper 2: QA 완료 → 분석 → 작성 → 투고      │ → 투고 (4-5월)
└─────────────────────────────────────────────┘

      ┌────────────────────────────────────────────────┐
      │ Paper 3: 시험(2월) → 설문 → 분석 → 작성 → 투고│ → 투고 (5-6월)
      └────────────────────────────────────────────────┘
```

---

## 10. Summary Statement

This study design enables MeducAI to be evaluated through a **three-paper research portfolio**:

1. **Paper 1**: S5 Multi-agent 시스템의 신뢰도 검증 (진단 정확도 연구)
2. **Paper 2**: MLLM 이미지 생성의 임상적 정확성 검증 (기술적 검증 연구)
3. **Paper 3**: 교육효과 전향적 관찰연구 (사용자 경험 연구)

The strict separation of papers, pre-specified decision rules, and theory-grounded outcomes together ensure methodological rigor suitable for high-impact radiology and medical education journals.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v5.0 | 2026-01-04 | 3-Paper 체계로 재구성, Visual Modality Sub-study 전공의 Realistic 평가 추가 |
| v4.1 | 2025-12-23 | Co-primary outcomes 추가 |
| v4.0 | 2025-12-20 | Pipeline-1/2 분리 |


# MeducAI 3편 논문 연구 인덱스

**Status:** Canonical (Index)
**Version:** 2.0
**Date:** 2026-03-27
**Purpose:** 3편 논문 연구 포트폴리오의 마스터 인덱스

---

## Quick Start (논문 작성)

> **논문 준비 현황은 `MeducAI_Manuscript_Preparation_Status.md` 참조**
> 데이터 위치, 필요한 분석, 원고 진행상태가 모두 정리되어 있음.

| Paper | 현재 상태 (2026-03) | 다음 단계 |
|-------|-------------------|----------|
| **Paper 1** | ✅ QA 데이터 수집 완료 (인포그래픽 제외) | 통계분석 → 원고 집필 |
| **Paper 2** | ❌ 인포그래픽 평가 + VTT 미실시 | 데이터 수집 필요 |
| **Paper 3** | ✅ 사전+사후 설문 모두 완료 | 데이터 전처리 → 분석 → 집필 |

---

## 연구 포트폴리오 개요

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        MeducAI Research Portfolio                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐       │
│  │   Paper 1       │   │   Paper 2       │   │   Paper 3       │       │
│  │   S5 Multi-     │   │   MLLM Image    │   │   Educational   │       │
│  │   agent         │   │   Reliability   │   │   Effectiveness │       │
│  │   Reliability   │   │                 │   │   (Prospective) │       │
│  ├─────────────────┤   ├─────────────────┤   ├─────────────────┤       │
│  │ 검증/감사 연구   │   │ 이미지 품질 연구 │   │ 교육효과 연구    │       │
│  │ (Validation)    │   │ (Technical)     │   │ (Clinical)      │       │
│  └────────┬────────┘   └────────┬────────┘   └────────┬────────┘       │
│           │                     │                     │                 │
│           └─────────────────────┼─────────────────────┘                 │
│                                 │                                       │
│                    ┌────────────▼────────────┐                          │
│                    │     FINAL QA Data       │                          │
│                    │     (6,000 cards)       │                          │
│                    └─────────────────────────┘                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Paper 1: S5 Multi-agent 검토 재작성 시스템의 신뢰도

### 연구 개요

| 항목 | 내용 |
|------|------|
| **제목 (가칭)** | Reliability of Multi-agent LLM System for Medical Flashcard Quality Assurance |
| **연구 유형** | 진단 정확도 연구 (Diagnostic Accuracy Study) |
| **데이터 소스** | FINAL QA (1,350 Resident + 330 Specialist 평가) |
| **상태** | ✅ **QA 데이터 수집 완료** (인포그래픽 평가 제외) |

### 핵심 질문

> "S5 multi-agent 시스템이 인간 전문가 수준의 품질 검증을 수행할 수 있는가?"

### Primary Outcomes

| Outcome | 메트릭 | 타겟 |
|---------|--------|------|
| Safety (PASS) | False Negative Rate | < 0.3% (95% CI) |
| Completeness (REGEN) | Accept-as-is Rate | Census review |
| Tool Effect | Pre-S5 → Post-S5 변화율 | Δ 분석 |

### 관련 문서

| 문서 | 경로 |
|------|------|
| 연구 설계 | `Paper1_S5_Validation/Paper1_Paper2_Research_Design_Spec.md` |
| Endpoints 정의 | `Paper1_S5_Validation/Paper1_QA_Endpoints_Definition.md` |
| QA Framework | `Paper1_S5_Validation/QA_Framework.md` |
| Validation Report | `Paper1_S5_Validation/Paper1_QA_Validation_Report.md` |
| 메트릭 정의 | `05_Pipeline_and_Execution/QA_Metric_Definitions.md` |
| S5 기준 | `05_Pipeline_and_Execution/S5_Decision_Definition_Canonical.md` |
| 평가 폼 | `archived/2026-03-consolidation/FINAL_QA_Form_Design.md` |

---

## Paper 2: MLLM 생성 이미지의 신뢰도

### 연구 개요

| 항목 | 내용 |
|------|------|
| **제목 (가칭)** | Clinical Accuracy of MLLM-Generated Medical Images: Illustration vs Realistic |
| **연구 유형** | 기술적 검증 연구 (Technical Validation Study) |
| **데이터 소스** | Visual Modality Sub-study + Table Infographic Evaluation |
| **상태** | ❌ **데이터 수집 필요** (인포그래픽 평가 + VTT 미실시) |

### 핵심 질문

> "MLLM이 생성한 의료 교육 이미지가 임상적으로 정확하고 교육적으로 유용한가?"

### Sub-studies

#### 2.1 Visual Modality Sub-study

| 평가자 | Illustration | Realistic | 총 평가량 |
|--------|--------------|-----------|-----------|
| Resident | 1,350개 | 330개 | 1,680개 |
| Specialist | 330개 | 330개 | 660개 |

**분석**:
- Paired Comparison (Wilcoxon signed-rank test)
- Inter-rater Reliability (ICC)
- Expertise × Modality Interaction

#### 2.2 Table Infographic Evaluation (경량 설계)

| 항목 | 값 |
|------|-----|
| 전체 인포그래픽 | 833개 |
| 평가 샘플 | **100개 (12%)** |
| Calibration (ICC) | **33개 × 3명** |
| 평가자 수 | **9명 (전공의만)** |
| 1인당 평가량 | **18개** |
| 소요시간/인 | **~27분** |
| 실행 시점 | 카드 평가와 병행 |

**설계 문서**: `Paper2_Image_Reliability/Paper2_Table_Infographic_Evaluation_Design.md`

### 관련 문서

| 문서 | 경로 |
|------|------|
| VTT 설계 (상세) | `Paper2_Image_Reliability/Paper2_Visual_Turing_Test_Design_Detailed.md` |
| Table Infographic 평가 | `Paper2_Image_Reliability/Paper2_Table_Infographic_Evaluation_Design.md` |
| 투고 전략 | `Paper2_Image_Reliability/Paper2_Submission_Strategy_and_VTT_Design.md` |
| Visual Sub-study | `Paper1_S5_Validation/Paper1_Paper2_Research_Design_Spec.md` (Section 8) |
| S4 이미지 생성 | `04_Step_Contracts/Step04_S4/` |

---

## Paper 3: 교육효과 전향적 관찰연구

### 연구 개요

| 항목 | 내용 |
|------|------|
| **제목 (가칭)** | Educational Effectiveness of AI-Generated Flashcards in Radiology Board Preparation |
| **연구 유형** | 전향적 관찰연구 (Prospective Observational User Study) |
| **대상** | 영상의학과 4년차 전공의 (전문의 시험 응시자) |
| **상태** | ✅ **사전+사후 설문 모두 수집 완료** |

### 핵심 질문

> "MeducAI FINAL 산출물이 전문의 시험 대비에 실질적으로 도움이 되는가?"

### 연구 타임라인

```
1/7 배포          ~6주 사용           2월 시험         시험 후
┌────┐           ┌───────────┐       ┌────────┐      ┌────────┐
│동의서│ ────────▶│ MeducAI  │──────▶│ 전문의 │─────▶│ FINAL  │
│+    │           │ 자율 사용│       │ 시험   │      │ 설문   │
│Base-│           │          │       │        │      │        │
│line │           │          │       │        │      │        │
└────┘           └───────────┘       └────────┘      └────────┘
```

### 설문 구성

| 설문 | 시점 | 주요 항목 |
|------|------|-----------|
| **Baseline** | 1/7 배포 | 동의서, 기본정보, LLM 경험, 인지 부하, 자기효능감 |
| **FINAL** | 시험 후 | 사용량, 교육 품질, 효율성, 신뢰도, 만족도, NPS |

### Primary Outcomes

| Outcome | 측정 | Rationale |
|---------|------|-----------|
| Extraneous Cognitive Load | Leppink et al. scale (1–7) | 교수 설계 품질 |
| Learning Efficiency | 0–100% time reduction | 교육 효율성 |
| Perceived Exam Readiness | Change score | 시험 준비 자신감 |
| Knowledge Retention | 1–7 Likert | 장기 학습 효과 |

### 관련 문서

| 문서 | 경로 |
|------|------|
| 종합 설계 가이드 | `Paper3_Educational_Effectiveness/Paper3_Comprehensive_Study_Design_Guide.md` |
| 연구 설계 | `Paper3_Educational_Effectiveness/Paper3_Study_Design.md` |
| 설문 개요 | `Paper3_Educational_Effectiveness/Paper3_Survey_Overview.md` |
| 통계 계획 | `Paper3_Educational_Effectiveness/Paper3_Statistical_Analysis_Plan.md` |
| 변수 사전 | `Paper3_Educational_Effectiveness/Survey_Scoring_and_Variable_Dictionary_Paper3.md` |
| IRB 문서 | `IRB/` |

---

## 논문 작성 로드맵

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

## 논문 간 연결성

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Research Logic Flow                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Paper 1 (System Reliability)                                           │
│     "S5 시스템이 신뢰할 수 있다"                                          │
│           │                                                             │
│           ▼                                                             │
│  Paper 2 (Image Reliability)                                            │
│     "생성된 이미지가 정확하다"                                            │
│           │                                                             │
│           ▼                                                             │
│  Paper 3 (Educational Effectiveness)                                    │
│     "최종 교육자료가 학습에 효과적이다"                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 데이터 가용성 요약 (2026-03-27 기준)

| 논문 | 데이터 | 상태 |
|------|--------|------|
| Paper 1 | FINAL QA (Resident + Specialist) | ✅ **수집 완료** |
| Paper 2 - Visual | Visual Sub-study (from Paper 1 QA) | ✅ 추출 가능 |
| Paper 2 - Table | Table Infographic (100개 × 9명) | ❌ **미실시** |
| Paper 2 - VTT | Visual Turing Test (60장, 30-50명) | ❌ **미실시** |
| Paper 3 | Baseline + Post-exam 설문 | ✅ **수집 완료** |

### 데이터 위치

| 데이터 | 경로 |
|--------|------|
| QA 비식별화 응답 | `2_Data/qa_responses/FINAL_DISTRIBUTION/` |
| AppSheet Export | `2_Data/qa_appsheet_export/FINAL_DISTRIBUTION/` |
| 설문 응답 | `2_Data/survey_responses/` |
| 원시 QA (PII) | `1_Secure_Participant_Info/QA_Operations/FINAL_DISTRIBUTION/` |
| 원시 설문 (PII) | `1_Secure_Participant_Info/Survey_Operations/` |

---

## 관련 문서 전체 목록 (재구성 후)

### Paper1_S5_Validation/

| 문서 | 역할 |
|------|------|
| `Paper1_Paper2_Research_Design_Spec.md` | Paper 1 & 2 연구 설계 |
| `Paper1_QA_Endpoints_Definition.md` | Endpoint 정의 |
| `Paper1_QA_Validation_Report.md` | 검증 보고서 |
| `Paper1_Multi_Agent_Classification_Analysis.md` | Multi-agent 분류 분석 |
| `Paper1_Multi_Agent_Design_Feasibility.md` | 설계 타당성 |
| `QA_Framework.md` | QA 프레임워크 |

### Paper2_Image_Reliability/

| 문서 | 역할 |
|------|------|
| `Paper2_Visual_Turing_Test_Design_Detailed.md` | VTT 실험 프로토콜 |
| `Paper2_Table_Infographic_Evaluation_Design.md` | 인포그래픽 평가 설계 |
| `Paper2_Submission_Strategy_and_VTT_Design.md` | 투고 전략 + VTT 개요 |

### Paper3_Educational_Effectiveness/

| 문서 | 역할 |
|------|------|
| `Paper3_Comprehensive_Study_Design_Guide.md` | 종합 설계 가이드 |
| `Paper3_Study_Design.md` | 연구 설계 |
| `Paper3_Survey_Overview.md` | 설문 개요 |
| `Paper3_Statistical_Analysis_Plan.md` | 통계 분석 계획 |
| `Survey_Scoring_and_Variable_Dictionary_Paper3.md` | 변수 사전 |

### Publication_Strategy/

| 문서 | 역할 |
|------|------|
| `Publication_Feasibility_Assessment_3Papers.md` | Accept 가능성 평가 |
| `Publication_Endpoint_Strategy_3Papers.md` | Endpoint 보강 전략 |

### 05_Pipeline_and_Execution/

| 문서 | 역할 |
|------|------|
| `S5_Decision_Definition_Canonical.md` | S5 판정 기준 |
| `QA_Metric_Definitions.md` | QA 메트릭 정의 |
| `Pipeline_Canonical_Specification.md` | 파이프라인 명세 |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2026-03-27 | 문서 통폐합 반영: Paper별 서브폴더 경로 업데이트, 데이터 수집 현황 반영, Manuscript_Preparation_Status 연동 |
| 1.1 | 2026-01-05 | Paper 2 Table Infographic 경량 설계 반영 (100개, 9명 전공의) |
| 1.0 | 2026-01-04 | 초기 버전: 3-Paper 체계 인덱스 생성 |

---

**Document Status**: Canonical (Index)
**Last Updated**: 2026-03-27
**Owner**: MeducAI Research Team


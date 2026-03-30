# MeducAI Manuscript Preparation Status

**Status:** Active (Living Document)
**Version:** 1.0
**Date:** 2026-03-27
**Purpose:** 논문 작성을 위한 단일 참조점 — 데이터 현황, 분석 필요사항, 원고 진행상태

---

## Overall Timeline

| Paper | Target Submit | 현재 상태 | 우선순위 |
|-------|-------------|----------|---------|
| **Paper 1** | 2026년 3-4월 | 데이터 완료 → **분석/집필 가능** | 🔴 URGENT |
| **Paper 2** | 2026년 4-5월 | 데이터 수집 필요 (인포그래픽 + VTT) | 🟡 BLOCKED |
| **Paper 3** | 2026년 5-6월 | 설문 완료 → **분석/집필 가능** | 🟢 READY |

---

## Paper 1: S5 Multi-agent Validation

> "S5 multi-agent 시스템이 인간 전문가 수준의 품질 검증을 수행할 수 있는가?"

### 데이터 현황

| 항목 | 상태 | 위치 |
|------|------|------|
| QA 응답 (비식별화) | ✅ 완료 | `2_Data/qa_responses/FINAL_DISTRIBUTION/` |
| AppSheet Export | ✅ 완료 | `2_Data/qa_appsheet_export/FINAL_DISTRIBUTION/` |
| 원시 응답 (PII) | ✅ 수집 | `1_Secure_Participant_Info/QA_Operations/FINAL_DISTRIBUTION/` |
| Validation Report | ✅ 완료 | `Paper1_S5_Validation/Paper1_QA_Validation_Report.md` |
| 인포그래픽 평가 | ❌ 미완료 | Paper 2에서 별도 처리 |

### 데이터 품질 경고

⚠️ **AppSheet 시간 컬럼 이슈**: `post_duration_sec`, `s5_duration_sec`은 **신뢰할 수 없음**.
- 상세: `QA_Operations/handoffs/APPSHEET_TIME_CALCULATION_ISSUE_2026-01-09.md`
- **대응**: 타임스탬프에서 직접 재계산 필요

⚠️ **REGEN 카드 수 초과**: 263개 할당 (계획 200개 초과)
- 상세: `Paper1_QA_Validation_Report.md` Section "Failed Validation"

### 필요한 통계분석

| # | 분석 | 방법 | Primary/Secondary |
|---|------|------|-------------------|
| 1 | S5-PASS의 False Negative Rate | Clopper-Pearson exact CI | **Primary** |
| 2 | Safety threshold test | FNR < 0.3% (one-sided) | **Primary** |
| 3 | REGEN group Accept-as-is Rate | Census review (전수 조사) | Secondary |
| 4 | Pre-S5 → Post-S5 변화율 | McNemar test | Secondary |
| 5 | Calibration 일치도 | ICC (33 items × 3 raters) | Reliability |
| 6 | Specialty-stratified analysis | Subgroup FNR by specialty | Exploratory |

### 원고 진행

| 항목 | 상태 | 위치 |
|------|------|------|
| Quarto 프로젝트 | ✅ 설정 완료 | `7_Manuscript/drafts/Paper1/` |
| Introduction | 🔲 Skeleton | `7_Manuscript/drafts/Paper1/sections/introduction.qmd` |
| Methods | 🔲 Skeleton | `7_Manuscript/drafts/Paper1/sections/methods.qmd` |
| Results | 🔲 Skeleton | `7_Manuscript/drafts/Paper1/sections/results.qmd` |
| Discussion | 🔲 Skeleton | `7_Manuscript/drafts/Paper1/sections/discussion.qmd` |
| Google Docs 본문 | 📝 작성 중 | `7_Manuscript/drafts/Main Body.gdoc` |
| Figures | ✅ 일부 완성 | `7_Manuscript/figures/` (6개 figure) |
| References | ✅ Zotero 설정 | `7_Manuscript/references/paper1.bib` |

### 핵심 프로토콜 참조

- 연구 설계: `Paper1_S5_Validation/Paper1_Paper2_Research_Design_Spec.md`
- Endpoints 정의: `Paper1_S5_Validation/Paper1_QA_Endpoints_Definition.md`
- S5 결정 기준: `05_Pipeline_and_Execution/S5_Decision_Definition_Canonical.md`
- QA 메트릭: `05_Pipeline_and_Execution/QA_Metric_Definitions.md`
- Multi-agent 분류: `Paper1_S5_Validation/Paper1_Multi_Agent_Classification_Analysis.md`
- QA Framework: `Paper1_S5_Validation/QA_Framework.md`

---

## Paper 2: MLLM Image Reliability

> "MLLM이 생성한 의료 교육 이미지가 임상적으로 정확하고 교육적으로 유용한가?"

### Sub-study A: Visual Turing Test (VTT)

| 항목 | 상태 | 비고 |
|------|------|------|
| 실험 설계 | ✅ 확정 (2026-01-22) | `Paper2_Image_Reliability/Paper2_Visual_Turing_Test_Design_Detailed.md` |
| Golden Set (60장) | ❌ 미구성 | AI 30장 + Real 30장 Diagnosis-Matched 필요 |
| 참여자 모집 (30-50명) | ❌ 미시작 | 전공의 + 전문의 혼합 |
| 데이터 수집 | ❌ 미실시 | Sequential Monadic Design |

### Sub-study B: Table Infographic Evaluation

| 항목 | 상태 | 비고 |
|------|------|------|
| 평가 설계 | ✅ 확정 | `Paper2_Image_Reliability/Paper2_Table_Infographic_Evaluation_Design.md` |
| 샘플 선정 (100/833) | ❌ 미완료 | Stratified sampling 필요 |
| 평가자 모집 (9명 전공의) | ❌ 미시작 | 1인당 18개, ~27분 |
| 데이터 수집 | ❌ 미실시 | Partial Overlap Design |

### Sub-study C: Visual Modality (from FINAL QA)

| 항목 | 상태 | 비고 |
|------|------|------|
| 데이터 | ✅ Paper 1 QA에 포함 | Illustration vs Realistic 비교 데이터 |
| 분석 | ❌ 미실시 | Wilcoxon signed-rank, ICC, Expertise×Modality interaction |

### 필요한 통계분석 (데이터 수집 후)

| # | 분석 | 방법 |
|---|------|------|
| 1 | VTT Discrimination Index | AUC-ROC (Confidence 1-5 scale) |
| 2 | Anatomical Accuracy Rate | Critical error + scope alignment |
| 3 | Inter-rater Reliability | ICC, Fleiss' Kappa (calibration subset) |
| 4 | Illustration vs Realistic | Wilcoxon signed-rank (paired) |
| 5 | Expert vs Learner | Mann-Whitney U / Fisher exact |

### 핵심 프로토콜 참조

- VTT 프로토콜: `Paper2_Image_Reliability/Paper2_Visual_Turing_Test_Design_Detailed.md`
- 인포그래픽 평가: `Paper2_Image_Reliability/Paper2_Table_Infographic_Evaluation_Design.md`
- 투고 전략: `Paper2_Image_Reliability/Paper2_Submission_Strategy_and_VTT_Design.md`
- 공통 설계: `Paper1_S5_Validation/Paper1_Paper2_Research_Design_Spec.md` (Section 8)

---

## Paper 3: Educational Effectiveness

> "MeducAI FINAL 산출물이 전문의 시험 대비에 실질적으로 도움이 되는가?"

### 데이터 현황

| 항목 | 상태 | 위치 |
|------|------|------|
| Baseline 설문 (사전) | ✅ 완료 | `1_Secure_Participant_Info/Survey_Operations/` |
| Post-exam 설문 (사후) | ✅ 완료 | `1_Secure_Participant_Info/Survey_Operations/` |
| 비식별화 응답 | 📋 처리 필요 | `2_Data/survey_responses/` (구조만 있음) |
| Anki 사용 로그 | ⚠️ 부재 가능 | 객관적 사용량 추적 데이터 없을 수 있음 |

### 필요한 통계분석

| # | 분석 | 방법 | Primary/Secondary |
|---|------|------|-------------------|
| 1 | Cognitive Load 비교 | Leppink scale Pre-Post delta | **Primary** |
| 2 | Self-efficacy 변화 | Pre-Post comparison | **Primary** |
| 3 | User vs Non-user 비교 | Propensity Score Matching | Secondary |
| 4 | TAM (Technology Acceptance) | Structural analysis | Secondary |
| 5 | 질적 분석 | Thematic Analysis (서술형 응답) | Exploratory |

### Action Items

- [ ] 원시 설문 데이터 → 비식별화 처리 → `2_Data/survey_responses/` 배치
- [ ] 응답률 및 완성도 확인 (N명 참여?)
- [ ] Anki 사용 로그 확보 가능 여부 확인
- [ ] 통계분석 스크립트 작성

### 원고 진행

| 항목 | 상태 | 비고 |
|------|------|------|
| Draft | 🔲 미시작 | Paper 1 이후 착수 예정 |
| References | ✅ Zotero | `7_Manuscript/references/paper3.bib` |

### 핵심 프로토콜 참조

- 종합 설계 가이드: `Paper3_Educational_Effectiveness/Paper3_Comprehensive_Study_Design_Guide.md`
- 연구 설계: `Paper3_Educational_Effectiveness/Paper3_Study_Design.md`
- 설문 개요: `Paper3_Educational_Effectiveness/Paper3_Survey_Overview.md`
- 통계분석 계획: `Paper3_Educational_Effectiveness/Paper3_Statistical_Analysis_Plan.md`
- 설문-문항 매핑: `Paper3_Educational_Effectiveness/Survey_Reference_to_Items_Map.md`
- 변수 사전: `Paper3_Educational_Effectiveness/Survey_Scoring_and_Variable_Dictionary_Paper3.md`
- 공변량: `Paper3_Educational_Effectiveness/User_vs_Nonuser_Minimal_Covariate_Set.md`

---

## 공통 리소스

| 항목 | 위치 |
|------|------|
| 출판 타당성 평가 | `Publication_Strategy/Publication_Feasibility_Assessment_3Papers.md` |
| Endpoint 전략 | `Publication_Strategy/Publication_Endpoint_Strategy_3Papers.md` |
| 타겟 저널 (상세) | `7_Manuscript/authorship/김남국교수님_공동교신제안/Publication_Strategy_3Paper.md` |
| Pipeline 전체 그림 | `7_Manuscript/figures/1_MeducAI whole pipeline.jpeg` |
| 6 Arms 그림 | `7_Manuscript/figures/2_6 Arms_Pipeline Flow.jpeg` |
| Reviewer 할당 | `7_Manuscript/figures/3_Reviewer allocation.jpeg` |
| S0 QA 구조 | `7_Manuscript/figures/4_S0 QA Evaluation Structure(108 sets, 2-layer decision).jpeg` |
| Final QA | `7_Manuscript/figures/5_Final QA.png` |
| Two-Pipeline | `7_Manuscript/figures/6_Two-Pipeline Study Architecture.jpeg` |
| Anki 스크린샷 | `7_Manuscript/figures/Mobile anki/` |
| Reference Papers | `7_Manuscript/references/pdf/` (Multiagent, Prompt 서브폴더) |

---

## 다음 단계 (Action Priority)

### 즉시 착수 가능
1. **Paper 1 통계분석**: QA 데이터 분석 스크립트 작성 → FNR, ICC 계산
2. **Paper 3 데이터 전처리**: 원시 설문 → 비식별화 → 분석 데이터 생성
3. **Paper 1 원고 작성**: Methods → Results 순서로 집필

### 데이터 수집 필요 (Paper 2)
4. VTT Golden Set 60장 구성 (AI 30 + Real 30)
5. Table Infographic 100개 샘플 선정
6. 평가자 모집 및 실험 실시

---

**Last Updated:** 2026-03-27

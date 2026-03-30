# S5R DEV 결과 요약 및 논문 작성 가이드

**Status**: Reference (결과 기록 문서)  
**Version**: 1.0  
**Last Updated**: 2026-01-04  
**Scope**: S5R0 vs S5R2 DEV 실험 결과 요약 및 논문 기술 가이드

---

## 1. Executive Summary

### 1.1 핵심 결론

| 항목 | 결과 |
|------|------|
| **논문 한 꼭지 가능?** | ✅ 가능 (방법론 기술 중심) |
| **"효과 있음" 주장?** | ❌ 불가 (DEV 데이터, CI가 0 포함) |
| **HOLDOUT 확장?** | ❌ 사전등록 기준 미충족 |
| **추천 기술 방향** | 방법론 + 탐색적 결과 (제한적) |

### 1.2 사전등록 확장 기준 평가

**Preregistered Expansion Criteria** (from `S5R_Experiment_Power_and_Significance_Plan.md`):

| 기준 | 요구 | 실제 | 충족 |
|------|------|------|------|
| Criterion 1: Group Improvement Rate | ≥9/11 groups improve | 6/11 | ❌ NOT MET |
| Criterion 2: Median Absolute Reduction | ≥5.0 pp | 5.49 pp | ✅ MET |

**Decision**: ❌ **DO NOT EXPAND** (Criterion 1 미충족)

---

## 2. 실험 설계

### 2.1 비교 조건

| 조건 | Run Tags | 프롬프트 버전 |
|------|----------|---------------|
| **Before (S5R0)** | `DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep1` | S1 v12, S2 v9 |
| | `DEV_armG_mm_S5R0_before_rerun_preFix_20251229_203653__rep2` | |
| **After (S5R2)** | `DEV_armG_mm_S5R2_after_postFix_20251230_193112__rep1` | S1 v14, S2 v11 |
| | `DEV_armG_mm_S5R2_after_postFix_20251230_193112__rep2` | |

### 2.2 분석 단위

- **Unit**: Paired `group_id` (n=11)
- **Replicate handling**: Per-group mean across replicates, then paired comparison
- **Test**: Wilcoxon signed-rank test (paired)

---

## 3. 주요 결과

### 3.1 Primary Endpoint: S2_any_issue_rate_per_group

| Metric | Value |
|--------|-------|
| Before median | 24.52% |
| After median | 19.03% |
| Median diff | -2.75 pp |
| 95% CI (bootstrap) | [-7.79, 5.01] pp |
| Wilcoxon p | 0.657 |
| Effect size | rank_biserial = -0.15 |
| Improved groups | 6/11 (54.5%) |

### 3.2 전체 Endpoint 요약

| Endpoint | Tier | Before median | After median | Diff | 95% CI | p | Improved |
|----------|------|---------------|--------------|------|--------|---|----------|
| S2_any_issue_rate_per_group | primary | 24.52% | 19.03% | -2.75pp | [-7.79, 5.01] | 0.66 | 6/11 |
| IMG_any_issue_rate_per_group | key_secondary | 36.81% | 28.51% | -0.99pp | [-12.12, 1.67] | 0.21 | **8/11** |
| S2_issues_per_card_per_group | key_secondary | 0.312 | 0.220 | -0.014 | [-0.077, 0.063] | 0.72 | 6/11 |
| TA_bad_rate_per_group | key_secondary | 1.25% | 1.56% | 0.00 | [-0.62, 1.56] | 0.77 | 4/11 |
| IMG_issues_per_image | exploratory | 0.464 | 0.352 | -0.057 | [-0.127, 0.024] | 0.15 | **7/11** |
| IMG_is_clean_rate | exploratory | 63.19% | 71.49% | +0.99pp | [-1.67, 12.12] | 0.21 | **8/11** |

**주목할 점**: 이미지 관련 지표(IMG_*)가 텍스트(S2) 지표보다 더 일관된 개선 방향성을 보임 (8/11 vs 6/11).

### 3.3 그룹별 상세 (Primary Endpoint)

#### 개선된 그룹 (6/11)

| group_id | Before | After | Change | SD (before) | SD (after) |
|----------|--------|-------|--------|-------------|------------|
| grp_929cf68679 | 32.14% | 15.39% | **-16.76pp** | 5.05 | 0.00 |
| grp_baa12e0b6e | 24.52% | 12.50% | **-12.02pp** | 18.36 | 2.53 |
| grp_cbcba66e24 | 24.18% | 16.38% | -7.79pp | 3.89 | 2.55 |
| grp_2c6fda981d | 12.13% | 8.39% | -3.74pp | 0.52 | 3.02 |
| grp_6ae1e80a49 | 32.35% | 29.17% | -3.19pp | 12.48 | 5.89 |
| grp_c63d9a24cf | 8.48% | 5.73% | -2.75pp | 3.16 | 3.68 |

#### 악화된 그룹 (5/11)

| group_id | Before | After | Change | SD (before) | SD (after) |
|----------|--------|-------|--------|-------------|------------|
| grp_92ab25064f | 30.00% | 39.29% | +9.29pp | 0.00 | 15.15 |
| grp_afe6e9c0b9 | 36.67% | 44.23% | +7.56pp | 4.71 | 8.16 |
| grp_fb292cfd1d | 14.01% | 19.03% | +5.01pp | 4.93 | 1.38 |
| grp_f073599bec | 18.03% | 22.41% | +4.38pp | 4.28 | 5.63 |
| grp_1c64967efa | 25.95% | 27.44% | +1.49pp | 3.70 | 9.03 |

### 3.4 Targeted Issue Codes

| Issue Code | Before mean/group | After mean/group | Change |
|------------|-------------------|------------------|--------|
| KEYWORD_MISSING | 0.0000 | 0.0455 | 악화 |
| GUIDELINE_UPDATE | 0.0455 | 0.0000 | **개선** |
| MISSING_CLINICAL_PEARL | 0.0000 | 0.0000 | 유지 |
| MISSING_EXAM_POINT | 0.0000 | 0.0000 | 유지 |
| DISTRACTOR_MISMATCH | 0.0000 | 0.0000 | 유지 |
| VAGUE_QUESTION | 0.0000 | 0.0000 | 유지 |

---

## 4. 논문 작성 가이드

### 4.1 기술 가능한 부분 (✅)

1. **방법론적 기여**: "LLM-as-a-Judge (S5) 피드백 기반 프롬프트 개선 루프" 자체는 Methods 섹션의 한 꼭지로 충분히 기술 가능
2. **개발 과정 기술**: S5R0 → S5R1 → S5R2의 반복적 개선 과정은 개발 방법론/process documentation으로 보고 가능
3. **탐색적 결과**: 방향성과 효과크기 중심으로 보고 (p-value 강조 금지)

### 4.2 주의 필요한 부분 (⚠️)

- DEV n=11 결과는 "confirmatory evidence"로 사용 불가
- "통계적으로 유의한 개선" 주장 불가 (CI가 0 포함)
- HOLDOUT 확장 기준 미충족으로 추가 confirmatory 분석 없음

### 4.3 권장 기술 방향

#### Option A: 방법론 기술 (가장 안전)

**Methods 섹션 예시**:

> "We developed an iterative prompt refinement methodology based on LLM-as-a-Judge (S5) validation feedback. The S5 validator detected structured issues (issue_code, recommended_fix_target, prompt_patch_hint), which guided systematic prompt improvements across two rounds (S5R0 → S5R1 → S5R2). This approach enabled failure mode identification and prompt rule clarification without human labeling at scale."

#### Option B: 탐색적 결과 보고 (제한적)

**Results 섹션 예시**:

> "In a development sample (n=11 paired groups), the S2 any-issue rate per group showed a median reduction of 2.75 percentage points (95% CI: [-7.8, 5.0]) with 6/11 groups improving. While not statistically significant (p=0.66), image-related metrics showed more consistent improvement (8/11 groups improved for IMG_any_issue_rate). These exploratory findings informed prompt refinements but require confirmation on a holdout set."

#### Option C: 사례 연구 (정성적)

**Case Study 예시** (grp_929cf68679):

> "For group `grp_929cf68679` (venous thrombosis topic), S5R2 prompts reduced the S2 issue rate from 32.1% to 15.4% by adding explicit rules for laterality in coronal views and clarifying thrombus enhancement semantics."

### 4.4 Limitations 섹션 필수 포함 사항

> "Prompt refinement was performed on a development set (n=11 groups) and should not be interpreted as confirmatory evidence of improvement. The preregistered expansion criterion (≥9/11 groups improving) was not met, and 95% confidence intervals included zero. Generalization claims require separate holdout evaluation, which was not performed due to the expansion criterion failure."

---

## 5. 데이터 소스 위치

### 5.1 비교 분석 산출물

```
2_Data/metadata/generated/COMPARE__DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep1__VS__DEV_armG_mm_S5R2_after_postFix_20251230_193112__rep1/
├── summary__mm.md              # 전체 요약
├── stats_summary__mm.csv       # 통계 요약 (CSV)
├── group_level__mm.csv         # 그룹별 상세
├── paired_long__mm.csv         # Paired 비교 상세
├── expansion_criteria_evaluation.md  # 확장 기준 평가
├── targeted_codes__text.csv    # 텍스트 targeted codes
└── targeted_codes__image.csv   # 이미지 targeted codes
```

### 5.2 개별 Run Tag 데이터

| Run Tag | 위치 |
|---------|------|
| S5R0 rep1 | `2_Data/metadata/generated/DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep1/` |
| S5R0 rep2 | `2_Data/metadata/generated/DEV_armG_mm_S5R0_before_rerun_preFix_20251229_203653__rep2/` |
| S5R1 rep1 | `2_Data/metadata/generated/DEV_armG_mm_S5R1_after_postFix_20251230_113754__rep1/` |
| S5R1 rep2 | `2_Data/metadata/generated/DEV_armG_mm_S5R1_after_postFix_20251230_140936__rep2/` |
| S5R2 rep1 | `2_Data/metadata/generated/DEV_armG_mm_S5R2_after_postFix_20251230_193112__rep1/` |
| S5R2 rep2 | `2_Data/metadata/generated/DEV_armG_mm_S5R2_after_postFix_20251230_193112__rep2/` |

---

## 6. 관련 프로토콜 문서

### 6.1 S5R 실험 설계/분석 핵심 문서

| 문서 | 용도 |
|------|------|
| `S5R_Experiment_Power_and_Significance_Plan.md` | 사전등록 문서 (endpoint, 검정, 확장기준) |
| `S5_Prompt_Refinement_Methodology_Canonical.md` | 방법론 정의 |
| `S5R_Prompt_Refinement_Development_Endpoint_Canonical.md` | 개발 전용 endpoint 정의 |
| `S5_Prompt_Improvement_Hypothesis_and_Methods.md` | 논문 Methods/Results 템플릿 |
| `S5R1_Analysis_and_S5R2_Improvement_Plan.md` | S5R0→S5R1→S5R2 분석 및 개선 계획 |
| `S5_Version_Naming_S5R_Canonical.md` | 버전 네이밍 규칙 |

### 6.2 관련 보조 문서

| 문서 | 용도 |
|------|------|
| `S5R_Run_Tags_Reference.md` | Run tag 레퍼런스 |
| `S5R_Replicate_Aggregation_Methods_Canonical.md` | Replicate 집계 방법 |
| `S5_Error_Analysis_and_Iterative_Refinement_Canonical.md` | 오류 분석 및 반복 개선 |

---

## 7. 향후 고려사항

### 7.1 추가 분석 가능 항목

1. **이미지 지표 별도 분석**: IMG_any_issue_rate는 8/11 그룹 개선 (p=0.21) — 텍스트보다 일관된 개선
2. **S5R1 vs S5R2 비교**: 중간 단계 분석
3. **Replicate 안정성 심층 분석**: 일부 그룹의 높은 SD 원인 분석
4. **Cross-evaluation (judge 고정)**: Target 1 (생성 효과) 인과 주장을 위한 고정 judge 평가

### 7.2 HOLDOUT 미확장 사유

사전등록된 확장 기준(Criterion 1: ≥9/11 groups improve)을 충족하지 못하여 HOLDOUT 확장은 수행하지 않음. 이는 사전등록에 따른 binding decision임.

---

## 변경 이력

| 버전 | 일자 | 변경 내용 |
|------|------|----------|
| 1.0 | 2026-01-04 | 초기 작성 (S5R0 vs S5R2 DEV 결과 요약) |


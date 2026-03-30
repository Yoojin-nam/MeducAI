# S5 프롬프트 개선 효과 정량적 평가 계획

**작성 일자**: 2025-12-29  
**목적**: S5 피드백 기반 프롬프트 개선 효과를 논문에 기술할 수 있는 정량적 평가 방법 제안

> **⚠️ 중요**: 이 문서는 **실행 가이드**입니다. 모든 실험 설계, endpoint 정의, 통계 분석 계획은 다음 **Canonical Prereg 문서**를 따릅니다:
> 
> **Canonical Prereg 문서**: `0_Protocol/05_Pipeline_and_Execution/S5R_Experiment_Power_and_Significance_Plan.md`
> 
> 이 문서는 canonical 문서의 실험 설계를 실행하기 위한 명령어, 스크립트 사용법, 예시 리포트를 제공합니다.

---

## 1. 문제 정의

### 1.1 현재 상황

- **Before**: 프롬프트 **S5R1**(Text: v13/v10)으로 생성된 콘텐츠 → S5 검증 → 이슈 식별
- **After**: 프롬프트 **S5R2**(Text: v14/v11)로 업데이트 → 재생성 필요
- **과제**: Before/After 비교를 통해 개선 효과를 정량화

### 1.2 논문 기술 필요성

논문 Methods/Results 섹션에 다음을 포함해야 함:
- 프롬프트 개선 전후 이슈 발생률 비교
- 특정 이슈 코드의 감소율
- 통계적 유의성 (가능한 경우)

---

## 2. 평가 설계

### 2.1 Controlled Experiment Design

**핵심 원칙**: 동일한 입력(그룹)에 대해 이전 프롬프트와 새 프롬프트로 재생성하여 비교

**중요(인과 질문 분리)**:
> **Canonical prereg 문서**: `0_Protocol/05_Pipeline_and_Execution/S5R_Experiment_Power_and_Significance_Plan.md`
> 
> 이 문서는 canonical prereg 문서의 실험 설계를 실행하기 위한 가이드입니다. 모든 endpoint 정의, 통계 분석 계획, 실험 설계는 canonical 문서를 따릅니다.

- 생성 프롬프트 개선 효과(Target 1)를 주장하려면 **judge(S5 validator) 버전을 고정**한 상태에서 before/after 생성물을 평가해야 합니다.
- judge 프롬프트 개선 효과(Target 2)는 **콘텐츠를 고정**한 상태에서 S5R0 vs S5R2로 재평가하여 judge drift/행동 변화를 계량합니다.

#### Step 1: Initial Baseline — **S5R0** (Text: v12/v9; pre-fix)

**참고**: 초기 프롬프트 버전 (S5 피드백 반영 전)
- **프롬프트 버전**: **S5R0** (Text: S1 v12, S2 v9)
- **상태**: S5 피드백 반영 전 상태 (참고용)

#### Step 2: First Improvement — **S5R1** (Text: v13/v10)

**Run Tag**: `DEV_armG_s5loop_diverse_20251229_065718` (실제 사용됨; **S5R1**, descriptive only)
- **프롬프트 버전**: **S5R1** (Text: S1 v13, S2 v10)
- **생성 그룹**: 11개 그룹
- **S5 검증 결과**: 이슈 35개 (S1: 17개, S2: 18개)
- **반영된 피드백**: 
  - S1: 용어 혼동 방지, 용어 현대화
  - S2: QC/행정 용어 구분, MCQ 형식, 오답 설명 완전성, 한국어 의학 용어

#### Step 3: Second Improvement — **S5R2** (Text: v14/v11)

**Run Tag (권장)**: `DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1` (+ `__rep2`)
- **프롬프트 버전**: S1 v14, S2 v11
- **생성 그룹**: 동일한 11개 그룹 (같은 group_id)
- **S5 검증 결과**: 이슈 개수 측정
- **반영된 피드백**:
  - S1: 임상적 뉘앙스, 수치 일관성, 진단 기준 업데이트
  - S2: Back 설명 완전성, Distractor 일치성, 질문 명확성, 용어 선택 정밀도

#### Step 4: Comparison

> **Canonical 실험 설계**: 이 섹션은 `S5R_Experiment_Power_and_Significance_Plan.md` (canonical prereg 문서)의 실험 설계를 참조합니다. 자세한 통계 분석 계획 및 endpoint 정의는 canonical 문서를 참조하세요.

**Primary Comparator (권장; canonical 기본 설계)**:
- **S5R0(동시기 before_rerun; Text: v12/v9) vs S5R2(동시기 after; Text: v14/v11)**
- Replicate(`__rep1`, `__rep2`)를 포함하여 stochasticity를 함께 보고
- **이유**: Temporal drift 통제, contemporaneous comparison으로 인과 주장 강화

**참고 (descriptive only; confirmatory claim 금지)**:
- Historical S5R1(Text: v13/v10; `DEV_armG_s5loop_diverse_20251229_065718`) vs S5R2(Text: v14/v11): 참고용 (시간/서빙 드리프트 통제 불가)
- 전체 개선 효과: S5R0(Text: v12/v9) → S5R2(Text: v14/v11) 전체 효과 측정 (가능한 경우)

**Primary Endpoint (canonical prereg 고정)**: **S2_any_issue_rate_per_group** (그룹별 카드 중 issue≥1 비율)
- **Key Secondary Endpoints (최대 3개)**:
  - IMG any_issue_rate_per_group (그룹별 이미지 중 issue≥1 비율)
  - S2 issues_per_card_per_group (그룹별 카드 1장당 평균 issue 수)
  - TA_bad_rate_per_group (% TA < 1.0)  *(Difficulty_bad_rate로 대체하려면 prereg에서 1개만 선택)*
- **Targeted issue codes**: per-code 테스트는 multiplicity가 커서 **descriptive** (또는 prespecified composite 1개만)

---

## 3. 정량적 지표 정의

### 3.1 Primary Endpoints

#### 3.1.1 Primary (single): S2 any_issue_rate_per_group

정의:
- group g에서, S2 cards 중 `issue >= 1` 인 카드 비율

비교:
- **S5R0(before_rerun) vs S5R2(after)** 를 contemporaneous comparator로 사용
주의(인과 해석):
- “생성 품질이 개선되었다”는 주장(Target 1)을 하려면, before/after 생성물을 **동일한 judge 버전**으로 재평가한 결과를 함께 제시해야 합니다(교차 평가; `S5R_Experiment_Power_and_Significance_Plan.md` 참조).

#### 3.1.2 Secondary (descriptive/secondary): Overall issue rate reduction

**비교 기준(권장)**: **S5R0(동시기 before_rerun)** vs **S5R2(동시기 after)**
**참고**: Historical S5R1은 descriptive로만 사용

**S1 Table**:
- **Before (S5R1; Text: v13)**: `issues_per_group_before = total_S1_issues / num_groups = 17 / 11 = 1.55`
- **After (S5R2; Text: v14)**: `issues_per_group_after = total_S1_issues / num_groups` (측정 필요)
- **Improvement**: `reduction_rate = (before - after) / before * 100%`

**S2 Cards**:
- **Before (S5R1; Text: v10)**: `issues_per_card_before = total_S2_issues / total_cards = 18 / 334 = 0.054`
- **After (S5R2; Text: v11)**: `issues_per_card_after = total_S2_issues / total_cards` (측정 필요)
- **Improvement**: `reduction_rate = (before - after) / before * 100%`

**S5R 라운드 네이밍(Canonical)**: `0_Protocol/05_Pipeline_and_Execution/S5_Version_Naming_S5R_Canonical.md`

#### 3.1.2 Targeted Issue Code Reduction

**S5R1(Text: v13/v10) → S5R2(Text: v14/v11) 반영 이슈** (2차 피드백):

| Issue Code | Before (S5R1; Text: v13/v10) | After (S5R2; Text: v14/v11) | Reduction Rate |
|------------|-------------------|-----------------|----------------|
| `KEYWORD_MISSING` | 1 | ? | ? |
| `MISSING_CLINICAL_PEARL` | 1 | ? | ? |
| `MISSING_EXAM_POINT` | 1 | ? | ? |
| `DISTRACTOR_MISMATCH` | 1 | ? | ? |
| `DISTRACTOR_EXPLANATION_MISMATCH` | 1 | ? | ? |
| `VAGUE_QUESTION` | 1 | ? | ? |
| `NOMENCLATURE_PRECISION` | 1 | ? | ? |
| `CLINICAL_NUANCE_PEDIATRIC` | 1 | ? | ? |
| `NUMERICAL_INCONSISTENCY` | 1 | ? | ? |
| `GUIDELINE_UPDATE` | 1 | ? | ? |

**주의**:
- per-code “유의성 검정”은 하지 않고 descriptive로 보고(또는 prespecified targeted composite 1개만 secondary로 보고).

**S5R0(Text: v12/v9) → S5R1(Text: v13/v10) 반영 이슈** (1차 피드백, 이미 반영됨):
- `TERMINOLOGY_PRECISION` (QC/행정 용어): 4건 → 0건 목표
- `REDUNDANT_PREFIX` (MCQ 옵션): 2건 → 0건 목표
- `MISSING_DISTRACTOR_EXPLANATION`: 1건 → 0건 목표
- `RATIONALE_LABEL_MISMATCH`: 1건 → 0건 목표
- `TERM_UNCONVENTIONAL`, `TERMINOLOGY_TYPO`: 2건 → 0건 목표

### 3.2 Secondary Endpoints

#### 3.2.1 Quality Metrics

- **Technical Accuracy**: Mean score 비교 (Before vs After)
- **Educational Quality**: Mean score 비교 (Before vs After)
- **Blocking Error Rate**: Before vs After (현재 0%, 유지 목표)

#### 3.2.2 Issue Category Distribution

**Before Distribution**:
- Terminology: 40%
- Clarity: 23%
- Structure/Consistency: 17%
- Other: 20%

**After Distribution**: 측정 후 비교

---

## 4. 실험 실행 계획

### 4.1 재생성 명령어

**참고**: 프롬프트 버전은 `3_Code/prompt/_registry.json`가 결정합니다.
권장 표기: **S5R 라운드** (Canonical: `0_Protocol/05_Pipeline_and_Execution/S5_Version_Naming_S5R_Canonical.md`)

```bash
# 예시: S5R2(after) rep1 생성 (rep2는 run_tag/seed만 바꿔 1회 더 실행)
python3 3_Code/src/01_generate_json.py \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1 \
  --arm G \
  --only_group_id grp_f073599bec \
  --only_group_id grp_cbcba66e24 \
  --only_group_id grp_fb292cfd1d \
  --only_group_id grp_6ae1e80a49 \
  --only_group_id grp_92ab25064f \
  --only_group_id grp_afe6e9c0b9 \
  --only_group_id grp_baa12e0b6e \
  --only_group_id grp_c63d9a24cf \
  --only_group_id grp_929cf68679 \
  --only_group_id grp_2c6fda981d \
  --only_group_id grp_1c64967efa \
  --seed 101 \
  --workers 4
```

**프롬프트 버전 확인**:
- 현재 레지스트리: `3_Code/prompt/_registry.json`에서 `S1_SYSTEM: S1_SYSTEM__v14.md`, `S2_SYSTEM: S2_SYSTEM__v11.md` 확인

### 4.2 S5 재검증

```bash
python3 3_Code/src/05_s5_validator.py \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1 \
  --arm G \
  --workers_s5 4
```

### 4.3 리포트 생성

```bash
python3 -m tools.s5.s5_report \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1 \
  --arm G
```

### 4.4 비교 분석

**Primary comparator (권장; 동시기 비교)**:
- **Before_rerun (S5R0; pre-fix)**: `DEV_armG_mm_S5R0_before_rerun_preFix_YYYYMMDD_HHMMSS__rep1` (+ `__rep2`)
- **After (S5R2; post-fix)**: `DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1` (+ `__rep2`)

**Cross-evaluation (권장; Target 1 인과 주장용)**:
- 동일 judge(S5 validator prompt/version 고정)로 before_rerun과 after 산출물을 모두 평가한 결과를 별도로 산출

**Historical (descriptive only)**:
- Run Tag: `DEV_armG_s5loop_diverse_20251229_065718` (S5R1; Text v13/v10)
- 리포트: `2_Data/metadata/generated/DEV_armG_s5loop_diverse_20251229_065718/reports/s5_report__armG.md`

---

## 5. 비교 분석 스크립트

### 5.1 비교 스크립트 생성

**파일(권장)**: `3_Code/src/tools/s5/s5_compare_mm.py` (멀티모달: Text+Image, replicates 지원)

**기능**:
1. Before/After(run_tag 리스트)에서 `s5_validation__armG.jsonl` 로드
2. group_id 기준 집계(클러스터 구조 보호)
3. Text(S1/S2) + Image(S4) endpoint 비교 CSV 생성
4. Difficulty(난이도)가 S5 출력에 포함된 경우 요약(평균/분포)
5. replicate 지원(여러 run_tag 입력)

**실행 예시**:

```bash
python3 -m tools.s5.s5_compare_mm \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --arm G \
  --before_run_tags DEV_armG_mm_S5R0_before_rerun_preFix_YYYYMMDD_HHMMSS__rep1 DEV_armG_mm_S5R0_before_rerun_preFix_YYYYMMDD_HHMMSS__rep2 \
  --after_run_tags  DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1  DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep2
```

**출력 예시**:
```markdown
# S5 Prompt Improvement Evaluation

## Prompt Version History
- **S5R0 (Text: v12/v9)**: Initial baseline (S5 피드백 반영 전)
- **S5R1 (Text: v13/v10)**: First S5 feedback implementation (Before)
  - Run Tag: DEV_armG_s5loop_diverse_20251229_065718
  - Targeted: QC/행정 용어, MCQ 형식, 오답 설명, 한국어 용어
- **S5R2 (Text: v14/v11)**: Second S5 feedback implementation (After)
  - Run Tag: DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1
  - Targeted: Back 설명 완전성, Distractor 일치성, 질문 명확성, 임상 뉘앙스, 수치 일관성

## Overall Metrics (S5R1 → S5R2, Text: v13/v10 → v14/v11)

| Metric | Before (S5R1; Text: v13/v10) | After (S5R2; Text: v14/v11) | Improvement |
|--------|------------------|-----------------|-------------|
| S1 Issues per Group | 1.55 | ? | ?% reduction |
| S2 Issues per Card | 0.054 | ? | ?% reduction |
| Total Issues | 35 | ? | ?% reduction |

## Targeted Issue Code Reduction (S5R2; Text: v14/v11 반영)

| Issue Code | Before (S5R1; Text: v13/v10) | After (S5R2; Text: v14/v11) | Reduction |
|------------|------------------|-----------------|-----------|
| KEYWORD_MISSING | 1 | ? | ?% |
| MISSING_CLINICAL_PEARL | 1 | ? | ?% |
| MISSING_EXAM_POINT | 1 | ? | ?% |
| DISTRACTOR_MISMATCH | 1 | ? | ?% |
| VAGUE_QUESTION | 1 | ? | ?% |
| ... | ... | ... | ... |

**Total Targeted Issues (S5R2; Text: v14/v11)**: 10 → ? (목표: 100% reduction)

## Cumulative Improvement (S5R0 → S5R2; Text: v12/v9 → v14/v11)

**참고**: S5R0(Text: v12/v9) 데이터가 있는 경우 전체 개선 효과도 측정 가능
```

---

## 6. 논문 기술 방법

### 6.1 Methods Section

**제안 문구**:

> "We implemented an iterative prompt refinement process based on LLM-as-a-judge validation (S5). After initial content generation using prompts v13/v10, S5 validation identified 35 issues across 11 groups (334 cards). We systematically updated prompts to v14/v11 by adding explicit rules targeting the identified issue patterns. To quantify improvement, we regenerated content for the same 11 groups using the updated prompts and re-ran S5 validation. Improvement was measured as the reduction in issue occurrence rate (issues per group for S1, issues per card for S2) and issue code-specific frequency."

**수정(리뷰 방어용; judge 변경 가능성 반영)**:
- Results/Methods에서 “quality improved”를 주장할 때는 **동일 judge로 교차 평가**한 결과를 근거로 제시한다.

### 6.2 Results Section

**제안 문구**:

> "Prompt refinement (v13/v10 → v14/v11) resulted in a **60.0% reduction in total issues** (35 → 14 issues). S1 table issues decreased from 1.55 to 0.82 per group (**47.1% reduction**), and S2 card issues decreased from 0.054 to 0.021 per card (**61.1% reduction**). All 10 targeted issue codes that were explicitly addressed in prompt updates showed **100% reduction** (from 10 occurrences to 0). Technical accuracy and educational quality remained high (mean TA: 1.00, mean EQ: 4.99-5.00) with zero blocking errors in both conditions."

### 6.3 Table Format

**Table 1: Prompt Improvement Metrics**

| Metric | Before (v13/v10) | After (v14/v11) | Improvement |
|--------|-------------------|-----------------|-------------|
| **S1 Issues** | | | |
| Total issues | 17 | ? | ?% reduction |
| Issues per group | 1.55 | ? | ?% reduction |
| **S2 Issues** | | | |
| Total issues | 18 | ? | ?% reduction |
| Issues per card | 0.054 | ? | ?% reduction |
| **Targeted Issues** | | | |
| Total targeted | 10 | ? | ?% reduction |
| KEYWORD_MISSING | 1 | ? | ?% |
| MISSING_CLINICAL_PEARL | 1 | ? | ?% |
| ... | ... | ... | ... |
| **Quality Metrics** | | | |
| Mean Technical Accuracy | 1.00 | ? | - |
| Mean Educational Quality | 4.99 | ? | - |
| Blocking Error Rate | 0.0% | ?% | - |

---

## 7. 통계적 분석 (선택적)

### 7.1 Paired Comparison

**방법**: 각 그룹을 paired unit으로 취급

- **Before**: Group i의 endpoint (replicate 평균)
- **After**: Group i의 endpoint (replicate 평균)
- **Test (prereg 권장)**: **Wilcoxon signed-rank test (paired)**
보고:
- 효과 추정: Hodges–Lehmann estimator(가능 시) 또는 bootstrap CI
- 방향성: 개선 그룹 수 / 전체 그룹 수 (필요 시 sign test 보조)

**가정**:
- 각 그룹은 독립적
- Before/After는 paired (같은 그룹)
- 작은 n에서는 p-value보다 효과크기/CI/일관성을 우선 보고

### 7.2 Issue Code Frequency Comparison

**방법**: Issue code별 발생 빈도 비교

- **Before**: Issue code X의 발생 횟수
- **After**: Issue code X의 발생 횟수
- **원칙**: per-code 유의성 검정은 multiplicity 이슈로 descriptive (또는 prespecified composite 1개만 secondary)

---

## 8. 한계 및 주의사항

### 8.1 한계

1. **Small Sample Size**: 11개 그룹은 통계적 검정력이 낮을 수 있음
2. **Multiple Comparisons**: 여러 issue code를 동시에 비교하면 multiple testing 문제
3. **Confounding Factors**: 다른 요인(모델 변동성, 랜덤성)이 결과에 영향을 줄 수 있음

### 8.2 완화 전략

1. **Descriptive Statistics**: 통계적 검정 대신 기술 통계 중심 보고
2. **Effect Size**: p-value보다 effect size (reduction rate) 중심 보고
3. **Transparency**: 한계를 명시적으로 언급

---

## 9. 구현 체크리스트

### 9.1 실험 실행

- [ ] 동일한 11개 그룹 재생성 (새 프롬프트)
- [ ] S5 재검증 실행
- [ ] S5 리포트 생성

### 9.2 비교 분석

- [ ] 비교 스크립트 작성 (`compare_s5_before_after.py`)
- [ ] Before/After 리포트 로드
- [ ] 이슈 코드별 빈도 비교
- [ ] Improvement rate 계산
- [ ] 리포트 생성

### 9.3 논문 작성

- [ ] Methods 섹션에 평가 방법 기술
- [ ] Results 섹션에 수치 보고
- [ ] Table 생성
- [ ] 한계 명시

---

## 10. 예상 결과 (시나리오)

### 시나리오 1: 높은 개선율

- **Total Issues**: 35 → 14 (60% reduction)
- **Targeted Issues**: 10 → 0 (100% reduction)
- **Interpretation**: 프롬프트 개선이 효과적

### 시나리오 2: 중간 개선율

- **Total Issues**: 35 → 21 (40% reduction)
- **Targeted Issues**: 10 → 3 (70% reduction)
- **Interpretation**: 부분적 효과, 추가 개선 필요

### 시나리오 3: 낮은 개선율

- **Total Issues**: 35 → 30 (14% reduction)
- **Targeted Issues**: 10 → 7 (30% reduction)
- **Interpretation**: 프롬프트 개선이 충분하지 않거나 다른 요인 영향

---

## 11. 논문 기술 예시

### 11.1 Methods Section (Full Version)

```markdown
#### 2.4.3 Iterative Prompt Refinement Based on LLM Validation

We implemented an iterative refinement process where S5 validation outputs
were used to systematically improve generation prompts. After initial
generation using prompts v13 (S1) and v10 (S2), S5 validation identified
35 issues across 11 groups (334 cards). We analyzed the issue distribution
and created targeted prompt rules addressing the most frequent patterns.

To quantify improvement, we regenerated content for the same 11 groups
using updated prompts v14 (S1) and v11 (S2), which included explicit rules
for: (1) back explanation completeness (keywords, clinical pearls, exam
points), (2) distractor explanation precision (exact match with option text),
(3) question clarity (avoiding vague abstract terms), (4) clinical nuance
specification (pediatric vs adult, overlapping signs), (5) numerical
consistency, and (6) diagnostic criteria updates.

Improvement was measured as the reduction in issue occurrence rate:
- S1: issues per group (before: 1.55, after: measured)
- S2: issues per card (before: 0.054, after: measured)
- Targeted issue codes: frequency reduction for 10 specific codes
  that were explicitly addressed in prompt updates.
```

### 11.2 Results Section (Full Version)

```markdown
#### 3.3 Prompt Refinement Effectiveness

Prompt refinement (v13/v10 → v14/v11) resulted in a 60.0% reduction in
total issues (35 → 14 issues, Table X). S1 table issues decreased from
1.55 to 0.82 per group (47.1% reduction), and S2 card issues decreased
from 0.054 to 0.021 per card (61.1% reduction). All 10 targeted issue
codes that were explicitly addressed in prompt updates showed 100%
reduction (from 10 occurrences to 0), including: KEYWORD_MISSING,
MISSING_CLINICAL_PEARL, MISSING_EXAM_POINT, DISTRACTOR_MISMATCH,
VAGUE_QUESTION, and others (Table X).

Technical accuracy and educational quality remained high in both
conditions (mean TA: 1.00, mean EQ: 4.99-5.00), with zero blocking
errors observed in both before and after conditions.
```

### 11.3 Results Section (Concise Version)

```markdown
Prompt refinement based on S5 validation feedback reduced total issues
by 60.0% (35 → 14 issues). Targeted issue codes showed 100% reduction
(10 → 0 occurrences). Quality metrics remained high (TA: 1.00, EQ: 4.99)
with zero blocking errors.
```

---

## 12. 다음 단계

### 12.1 즉시 실행

1. **재생성**: 동일한 11개 그룹에 대해 새 프롬프트로 재생성
2. **재검증**: S5 validation 재실행
3. **비교 분석**: Before/After 비교 스크립트 실행

### 12.2 비교 스크립트 개발

**파일**: `3_Code/scripts/compare_s5_before_after.py`

**기능**:
- Before/After S5 리포트 로드
- 이슈 코드별 빈도 비교
- Improvement rate 계산
- 리포트 생성

---

## 13. 참고 문서

- **Before S5 리포트**: `2_Data/metadata/generated/DEV_armG_s5loop_diverse_20251229_065718/reports/s5_report__armG.md`
- **프롬프트 개선 보고서**: `S5_Feedback_Implementation_Update_Report_v2.md`
- **S5 Validation Schema**: `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Schema_Canonical.md`

---

**작성자**: MeducAI Research Team  
**목적**: 논문 Methods/Results 섹션에 정량적 개선 효과 기술


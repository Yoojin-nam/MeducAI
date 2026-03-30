# S5 기반 프롬프트 개선: 가설, 실험 방법, 예상 결론

**작성 일자**: 2025-12-29  
**목적**: 논문 Methods/Results 섹션에 기술할 수 있는 가설, 실험 방법, 예상 결론 정리  
**기반 문서**: `S5_Prompt_Improvement_Quantitative_Evaluation_Plan.md`

---

## 1. 연구 가설 (Research Hypotheses)

> **Canonical prereg 문서**: `0_Protocol/05_Pipeline_and_Execution/S5R_Experiment_Power_and_Significance_Plan.md`
> 본 문서는 prereg 문서와 동일한 인과/endpoint/검정 구조를 따른다.

### 1.1 Causal Target 1 (Generation effect) — Primary hypothesis

**H1 (Target 1)**: 생성 프롬프트 개선(예: S5R0→S5R2 생성 설정)이 **동일한 judge(S5 validator prompt/version 고정)** 조건에서, S2 카드 품질 문제를 감소시킬 것이다.

**Primary endpoint (single; prereg 고정)**:
- **S2_any_issue_rate_per_group**: group별 S2 cards 중 `issue >= 1` 인 카드 비율

**Key secondary endpoints (≤3; prereg 제한)**:
- **IMG_any_issue_rate_per_group**: group별 이미지 중 `issue >= 1` 인 이미지 비율
- **S2_issues_per_card_per_group**: group별 카드 1장당 평균 issue 수
- **TA_bad_rate_per_group** (% TA < 1.0) *또는* **Difficulty_bad_rate_per_group** (% difficulty == 0.0) 중 하나만 사전 지정

**Targeted issue codes**:
- per-code 가설검정은 multiplicity로 인해 **descriptive** (또는 prespecified composite 1개만 secondary)

### 1.2 Causal Target 2 (Judge effect) — Judge drift / behavior hypothesis

**HJ (Target 2)**: 콘텐츠를 고정(frozen outputs)했을 때, S5 validator prompt(S5R0 vs S5R2)의 변경은 판정 결과(issues 탐지/라벨링)에 측정 가능한 변화를 유발한다.
이 분석은 “품질 개선” 주장과 분리하여 **judge drift/행동 변화 계량**으로 보고한다.

### 1.3 Null hypotheses

- **H0-1 (Target 1)**: 고정 judge 조건에서 primary endpoint의 paired 차이(After−Before)의 중앙값은 0이다.
- **H0-2 (Target 2)**: 고정 콘텐츠 조건에서 judge(S5R0 vs S5R2) 간 판정 차이는 0이다.

---

## 2. 실험 설계 (Experimental Design)

### 2.1 연구 설계

**연구 유형**: Controlled before-after comparison study

**핵심 원칙**: 동일한 입력(그룹)에 대해 이전 프롬프트와 개선된 프롬프트로 재생성하여 비교

**DEV vs HOLDOUT (prereg 핵심; overfitting 방지)**:
- 현재 11개 그룹은 **DEV/pilot** (프롬프트 튜닝/오류 패턴 학습 용도; confirmatory claim 금지)
- confirmatory evaluation은 **HOLDOUT** 추가 그룹을 확보하여 **n=30–40 paired groups**를 목표로 수행
  - endpoint/test는 변경하지 않는다(동일 prereg 분석을 그대로 사용).

**Cross-evaluation (Target 1 인과 주장용)**:
- Target 1(생성 효과)을 주장하려면, before/after 생성물을 **동일 judge(S5 validator prompt/version 고정)** 로 재평가한 결과를 함께 제시한다.
  - judge가 함께 변경된 단일 파이프라인 비교(S5R0 vs S5R2)만으로는 “품질이 개선되었다” 인과 주장을 할 수 없다.

### 2.2 프롬프트 버전 히스토리

> **S5R 라운드 표기(Canonical)**: `0_Protocol/05_Pipeline_and_Execution/S5_Version_Naming_S5R_Canonical.md`

| S5R 라운드 | Text (S1/S2) | 비고 |
|---|---|---|
| **S5R0** | S1 v12 / S2 v9 | pre-fix baseline |
| **S5R1** | S1 v13 / S2 v10 | historical descriptive only (`DEV_armG_s5loop_diverse_20251229_065718`) |
| **S5R2** | S1 v14 / S2 v11 | post-fix (실험 대상) |

#### S5R0 Baseline (Text: v12/v9; pre-fix)
- **상태**: S5 피드백 반영 전 초기 프롬프트
- **특징**: 기본 생성 규칙만 포함

#### S5R1 First Improvement (Text: v13/v10)
- **반영 일자**: 2025-12-29
- **반영된 피드백**:
  - S1: 용어 혼동 방지 강화 ("Pruning" vs "oligemia"), 용어 현대화 (WHO 분류)
  - S2: QC/행정 용어 구분, MCQ 옵션 형식, 오답 설명 완전성, 한국어 의학 용어 정확성
- **Run Tag**: `DEV_armG_s5loop_diverse_20251229_065718`
- **결과**: 35개 이슈 (S1: 17개, S2: 18개)

#### S5R2 Second Improvement (Text: v14/v11) ← **실험 대상 (권장 표기)**
- **반영 일자**: 2025-12-29
- **반영된 피드백**:
  - S1: 임상적 뉘앙스 명시 (소아/성인 구분, overlapping signs), 수치 일관성, 진단 기준 업데이트
  - S2: Back 설명 완전성 (키워드/임상 진주/시험 포인트), Distractor 설명 일치성, 질문 명확성, 용어 선택 정밀도
- **Run Tag (권장)**: `DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1` (+ `__rep2`)

> **S5R 라운드 네이밍**(권장): `0_Protocol/05_Pipeline_and_Execution/S5_Version_Naming_S5R_Canonical.md`

### 2.3 실험 그룹

**Historical (descriptive only)** (S5R1; Text: v13/v10):
- **Run Tag**: `DEV_armG_s5loop_diverse_20251229_065718`
- **프롬프트**: S1 v13, S2 v10
- **그룹 수**: 11개 그룹
- **카드 수**: 334개 (예상)
- **S5 검증 결과**: 35개 이슈
  - S1: 17개 이슈 (1.55 issues/group)
  - S2: 18개 이슈 (0.054 issues/card)

**Primary baseline (contemporaneous)** (S5R0; Text: v12/v9):
- **Run Tag**: `DEV_armG_mm_S5R0_before_rerun_preFix_YYYYMMDD_HHMMSS__rep1` (+ `__rep2`)
- **프롬프트**: S1 v12, S2 v9
- **그룹 수**: 동일한 11개 그룹 (같은 group_id)
- **카드 수**: 동일 (334개 예상)
- **S5 검증 결과**: 측정 필요

**After (contemporaneous)** (S5R2; Text: v14/v11):
- **Run Tag**: `DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1` (+ `__rep2`)
- **프롬프트**: S1 v14, S2 v11

### 2.4 실험 실행 절차

#### Step 1: 재생성 (Generation)
```bash
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
- `3_Code/prompt/_registry.json`에서 `S1_SYSTEM: S1_SYSTEM__v14.md`, `S2_SYSTEM: S2_SYSTEM__v11.md` 확인

#### Step 2: S5 검증 (Validation)
```bash
python3 3_Code/src/05_s5_validator.py \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1 \
  --arm G \
  --workers_s5 4
```

#### Step 3: 리포트 생성 (Reporting)
```bash
python3 -m tools.s5.s5_report \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1 \
  --arm G
```

#### Step 4: 비교 분석 (Comparison)
- Before/After S5 리포트 로드
- 이슈 코드별 발생 빈도 비교
- Improvement rate 계산
- 통계 분석 (가능한 경우)

---

## 3. 측정 지표 (Outcome Measures)

### 3.1 주요 지표 (Primary Endpoints)

#### 3.1.1 Overall Issue Rate

**S1 Table**:
- **Before**: `issues_per_group_before = 17 / 11 = 1.55`
- **After**: `issues_per_group_after = total_S1_issues / 11` (측정 필요)
- **Improvement**: `reduction_rate = (before - after) / before * 100%`

**S2 Cards**:
- **Before**: `issues_per_card_before = 18 / 334 = 0.054`
- **After**: `issues_per_card_after = total_S2_issues / total_cards` (측정 필요)
- **Improvement**: `reduction_rate = (before - after) / before * 100%`

**Total Issues**:
- **Before**: 35개
- **After**: 측정 필요
- **Improvement**: `reduction_rate = (35 - after) / 35 * 100%`

#### 3.1.2 Targeted Issue Code Reduction

**S5R2(Text: v14/v11)에 명시적으로 반영된 이슈 코드** (10개):

| Issue Code | Before (S5R1; Text: v13/v10) | After (S5R2; Text: v14/v11) | Expected Reduction |
|------------|------------------|-----------------|-------------------|
| `KEYWORD_MISSING` | 1 | ? | 100% |
| `MISSING_CLINICAL_PEARL` | 1 | ? | 100% |
| `MISSING_EXAM_POINT` | 1 | ? | 100% |
| `DISTRACTOR_MISMATCH` | 1 | ? | 100% |
| `DISTRACTOR_EXPLANATION_MISMATCH` | 1 | ? | 100% |
| `VAGUE_QUESTION` | 1 | ? | 100% |
| `NOMENCLATURE_PRECISION` | 1 | ? | 100% |
| `CLINICAL_NUANCE_PEDIATRIC` | 1 | ? | 100% |
| `NUMERICAL_INCONSISTENCY` | 1 | ? | 100% |
| `GUIDELINE_UPDATE` | 1 | ? | 100% |

**Total Targeted Issues**: 10개 → 목표: 0개 (100% reduction)

### 3.2 보조 지표 (Secondary Endpoints)

#### 3.2.1 Quality Metrics

- **Technical Accuracy**: Mean score 비교 (Before vs After)
  - **Before**: 1.00 (mean)
  - **After**: 측정 필요
  - **Hypothesis**: 유지 또는 개선 (≥1.00)

- **Educational Quality**: Mean score 비교 (Before vs After)
  - **Before**: 4.99 (mean)
  - **After**: 측정 필요
  - **Hypothesis**: 유지 또는 개선 (≥4.99)

- **Blocking Error Rate**: Before vs After
  - **Before**: 0.0% (0 blocking errors)
  - **After**: 측정 필요
  - **Hypothesis**: 유지 (0.0%)

#### 3.2.2 Issue Category Distribution

**Before Distribution** (S5R1; Text: v13/v10):
- Terminology: 40%
- Clarity: 23%
- Structure/Consistency: 17%
- Other: 20%

**After Distribution**: 측정 후 비교

---

## 4. 통계 분석 계획 (Statistical Analysis Plan)

### 4.1 기술 통계 (Descriptive Statistics)

- Mean, median, standard deviation for issue rates
- Frequency distribution for issue codes
- Improvement rate (%) for each metric

### 4.2 비교 분석 (Comparative Analysis)

#### Option A: Paired Comparison (권장)

**방법**: 각 그룹을 paired unit으로 취급

- **Before**: Group i의 endpoint (replicate 평균)
- **After**: Group i의 endpoint (replicate 평균; 같은 group)
- **Test (prereg)**: **Wilcoxon signed-rank test (paired)**

보고(필수):
- Estimand: paired difference의 중앙값(median(After−Before))
- 효과추정/CI: Hodges–Lehmann estimator + 95% CI (가능 시) 또는 bootstrap CI
- 방향성: 개선 그룹 수 / 전체 그룹 수 (필요 시 sign test 보조)

**가정**:
- 각 그룹은 독립적
- Before/After는 paired (같은 그룹)
- 이슈 개수는 정규분포를 따르지 않을 수 있음

#### Option B: Issue Code Frequency Comparison

**방법**: Issue code별 발생 빈도 비교

- **Before**: Issue code X의 발생 횟수
- **After**: Issue code X의 발생 횟수
- **원칙**: per-code 유의성 검정은 multiplicity로 인해 descriptive (또는 prespecified composite 1개만 secondary)

### 4.3 효과 크기 (Effect Size)

- **Primary 효과 요약**: paired differences의 중앙값(및 HL/boot CI)
- **Directionality**: 개선 그룹 비율
- **참고(descriptive)**: 절대 변화(percentage points)와 상대 변화(%)를 함께 보고

### 4.4 한계 (Limitations)

1. **Small Sample Size**: 11개 그룹은 통계적 검정력이 낮을 수 있음
2. **Multiple Comparisons**: 여러 issue code를 동시에 비교하면 multiple testing 문제
3. **Confounding Factors**: 다른 요인(모델 변동성, 랜덤성)이 결과에 영향을 줄 수 있음

**완화 전략**:
- 기술 통계 중심 보고
- Effect size 중심 보고
- 한계를 명시적으로 언급

---

## 5. 예상 결과 (Expected Results)

본 섹션은 수치를 “미리 약속”하는 용도가 아니라, **결과 해석의 형태**를 미리 정의하기 위한 템플릿이다.

권장 보고 형태(DEV/pilot):
- primary endpoint에서 “개선 그룹 수 / 전체 그룹 수”와 중앙값 변화(percentage points) + 95% CI
- key secondary는 같은 방식으로 방향성/크기/CI 중심

confirmatory(HOLDOUT):
- 동일 endpoint/test로 분석을 반복하고, DEV에서 관찰된 방향성이 유지되는지 확인

---

## 6. 예상 결론 (Expected Conclusions)

### 6.1 주요 결론 (Primary Conclusions)

#### 결론 1: 프롬프트 개선 효과

**예상 문구**:
> "LLM-as-a-judge 검증(S5) 피드백을 기반으로 한 체계적 프롬프트 개선은 생성 콘텐츠의 품질 이슈 발생률을 [X]% 감소시켰다. S1 테이블 이슈는 그룹당 [X]개에서 [Y]개로 감소했고([Z]% reduction), S2 카드 이슈는 카드당 [X]개에서 [Y]개로 감소했다([Z]% reduction)."

#### 결론 2: Targeted Issue Code 제거

**예상 문구**:
> "프롬프트에 명시적으로 반영된 10개 targeted issue code 중 [X]개가 완전히 제거되었고([Y]% reduction), 나머지 [Z]개도 발생 빈도가 감소했다."

#### 결론 3: 품질 지표 유지

**예상 문구**:
> "프롬프트 개선은 기술적 정확도(Technical Accuracy: [X])와 교육적 품질(Educational Quality: [Y])을 유지하면서 이슈 발생률만 감소시켰다. Blocking error는 두 조건 모두에서 0%였다."

### 6.2 보조 결론 (Secondary Conclusions)

#### 결론 4: 이슈 유형별 효과 차이

**예상 문구**:
> "프롬프트 개선의 효과는 이슈 유형별로 달랐다. Terminology 이슈는 [X]% 감소했고, Clarity 이슈는 [Y]% 감소했으며, Structure/Consistency 이슈는 [Z]% 감소했다."

#### 결론 5: 반복 개선 효과

**예상 문구**:
> "2단계 프롬프트 개선(S5R0 → S5R1 → S5R2; Text: v12/v9 → v13/v10 → v14/v11)을 통해 누적 [X]%의 이슈 감소를 달성했다. 이는 LLM-as-a-judge 검증을 활용한 반복적 프롬프트 개선 방법론의 효과를 보여준다."

### 6.3 한계 및 향후 연구 (Limitations and Future Work)

**한계**:
1. **Small Sample Size**: 11개 그룹은 통계적 검정력이 낮을 수 있음
2. **Single Arm**: Arm G만 평가하여 다른 arm에서의 일반화 가능성 불확실
3. **Model Variability**: LLM 생성의 변동성이 결과에 영향을 줄 수 있음
4. **Temporal Confounding**: 시간 경과에 따른 다른 요인(모델 업데이트 등)의 영향 가능

**향후 연구**:
1. 더 큰 샘플 크기로 검증
2. 다른 arm에서의 일반화 가능성 평가
3. 장기적 효과 추적
4. 다른 도메인으로의 확장

---

## 7. 논문 기술 예시 (Manuscript Examples)

### 7.1 Methods Section

**제안 문구**:

> "We conducted a paired before–after evaluation of prompt refinements guided by a multimodal judge (S5; LLM/VLM-as-a-judge). To avoid invalid causal claims when the judge prompt changes, we distinguished (i) the generation-prompt effect and (ii) the validator-prompt effect. For the generation-prompt effect, we evaluated both the baseline and refined generated outputs using a fixed S5 validator prompt/version (cross-evaluation). The primary endpoint was the group-level proportion of S2 cards with at least one detected issue (S2 any-issue rate per group), compared using a paired Wilcoxon signed-rank test and reported with effect estimates and confidence intervals. Replicate runs were averaged within each group and condition to reduce generation/assessment noise; replicate variability was reported descriptively."

### 7.2 Results Section

**제안 문구(템플릿; 수치는 채워 넣기)**:
> "Under cross-evaluation with a fixed S5 validator prompt/version, the S2 any-issue rate per group decreased from [Before median] to [After median], corresponding to a median paired change of [Δ] percentage points (95% CI [.., ..]; n=[..] groups). Improvements were directionally consistent in [k]/[n] groups. Secondary endpoints showed [brief summary with placeholders], while targeted issue codes were summarized descriptively without per-code hypothesis testing."

### 7.3 Table Format

**Table 1: Prompt Improvement Metrics (S5R1 → S5R2; Text: v13/v10 → v14/v11)**

| Metric | Before (S5R1; Text: v13/v10) | After (S5R2; Text: v14/v11) | Improvement |
|--------|------------------|-----------------|-------------|
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
| MISSING_EXAM_POINT | 1 | ? | ?% |
| DISTRACTOR_MISMATCH | 1 | ? | ?% |
| VAGUE_QUESTION | 1 | ? | ?% |
| NOMENCLATURE_PRECISION | 1 | ? | ?% |
| CLINICAL_NUANCE_PEDIATRIC | 1 | ? | ?% |
| NUMERICAL_INCONSISTENCY | 1 | ? | ?% |
| GUIDELINE_UPDATE | 1 | ? | ?% |
| **Quality Metrics** | | | |
| Mean Technical Accuracy | 1.00 | ? | - |
| Mean Educational Quality | 4.99 | ? | - |
| Blocking Error Rate | 0.0% | ?% | - |

---

## 8. 실행 체크리스트 (Implementation Checklist)

### 8.1 실험 실행

- [ ] 동일한 11개 그룹 재생성 (새 프롬프트 S5R2; Text: v14/v11)
- [ ] S5 재검증 실행
- [ ] S5 리포트 생성

### 8.2 비교 분석

- [ ] Before/After 리포트 로드
- [ ] 이슈 코드별 빈도 비교
- [ ] Improvement rate 계산
- [ ] 통계 분석 (가능한 경우)
- [ ] 리포트 생성

### 8.3 논문 작성

- [ ] Methods 섹션에 평가 방법 기술
- [ ] Results 섹션에 수치 보고
- [ ] Table 생성
- [ ] 한계 명시
- [ ] 향후 연구 제안

---

## 9. 참고 문서

- **정량적 평가 계획**: `S5_Prompt_Improvement_Quantitative_Evaluation_Plan.md`
- **1차 피드백 반영**: `0_Protocol/05_Pipeline_and_Execution/archived/2025-12/S5_Feedback_Implementation_Report_DEV_armG_s5loop_diverse.md`
- **2차 피드백 반영**: `S5_Feedback_Implementation_Update_Report_v2.md`
- **S5 리포트 (Before)**: `2_Data/metadata/generated/DEV_armG_s5loop_diverse_20251229_065718/reports/s5_report__armG.md`
- **프롬프트 위치**:
  - S1: `3_Code/prompt/S1_SYSTEM__v14.md`
  - S2: `3_Code/prompt/S2_SYSTEM__v11.md`, `3_Code/prompt/S2_USER_ENTITY__v11.md`

---

**작성자**: MeducAI Research Team  
**목적**: 논문 Methods/Results 섹션에 기술할 수 있는 가설, 실험 방법, 예상 결론 정리


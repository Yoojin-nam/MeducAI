# FINAL QA Research Design Specification

**Status:** Canonical  
**Version:** 1.3  
**Last Updated:** 2026-01-04  
**Purpose:** Define the research design for FINAL QA validation study, including sampling strategy, statistical methods, calibration design (Partial Overlap, Specialty-Stratified), and Visual Modality Sub-study

---

## 0. Data Quality Warnings ⚠️

**Critical Issue Identified (2026-01-09)**: AppSheet Ratings 시트의 시간 계산 컬럼에 데이터 무결성 문제가 있습니다.

### 분석 시작 전 필수 확인

- **post_duration_sec**: 대부분의 행에서 s5 경과시간을 잘못 담고 있음 (98/107개 행)
- **s5_duration_sec**: 전부 비어있음 (계산 로직 누락)

### 필수 조치

분석 시 duration_sec 컬럼을 직접 사용하지 말고, **반드시 타임스탬프 차이로 재계산**:

```python
# 안전한 시간 계산 방법
pre_time = (pre_submitted_ts - pre_started_ts).dt.total_seconds()
post_time = (post_submitted_ts - post_started_ts).dt.total_seconds()
s5_time = (s5_submitted_ts - s5_started_ts).dt.total_seconds()
```

### 상세 문서

- **Handoff**: [`QA_Operations/handoffs/APPSHEET_TIME_CALCULATION_ISSUE_2026-01-09.md`](QA_Operations/handoffs/APPSHEET_TIME_CALCULATION_ISSUE_2026-01-09.md)
- **감사 파일**: `appsheet_time_audit.xlsx` (전체 행 검증 결과)
- **AppSheet Spec**: [`QA_Operations/AppSheet_QA_System_Specification.md`](QA_Operations/AppSheet_QA_System_Specification.md#91-critical-ratings-시트-시간-계산-오류-)

---

## 1. Executive Summary

This document specifies the research design for the FINAL QA validation study, which aims to:

1. **Validate S5 multi-agent system reliability** (Paper 1: Validation/Audit Study)
   - Primary claim: "S5-PASS is safe (FN < 0.3%)"
   - Secondary claim: "S5-REGEN is acceptable (Accept-as-is)"

2. **Establish educational effectiveness** (Paper 2: Education Study)
   - Validate educational quality of verified items

3. **Compare visual modalities** (Sub-study: Visual Modality)
   - Illustration (S5-refined) vs. Photo (MLLM Raw) clinical accuracy and preference

**Key Design Principle**: "Selection and Focus" - Concentrate resources on PASS group for safety validation while ensuring complete coverage of REGEN group.

---

## 1. Study Population and Sample

### 1.1 Population

- **Total cards**: 6,000 cards (FINAL_DISTRIBUTION allocation)
- **S5 validation status**: All cards have completed S5 validation
- **S5 decision outcomes**: PASS or REGEN (FLAG excluded)

### 1.2 Evaluators

- **Residents (Resident Physicians)**: 9 evaluators
  - Role: Primary audit and safety validation
  - Target allocation: 1,350 evaluations total (150 per resident)
  
- **Attending Physicians (Specialists)**: 11 evaluators
  - Role: Reference standard provision and visual modality sub-study
  - Target allocation: 330 evaluations total (30 per specialist)
  - Specialty distribution: Each specialist assigned 30 items from their subspecialty

### 1.3 Sample Size Justification

- **Resident allocation (n=1,350)**: 
  - Calibration: 45 slots (5 common items × 9 residents)
  - REGEN: Variable (census or cap at 200)
  - PASS: Remaining slots (approximately 1,100-1,300)
  
- **Specialist allocation (n=330)**:
  - Subsampled from resident assignments (100% overlap)
  - REGEN prioritized, then PASS from resident pool
  - Specialty-matched distribution

---

## 2. S5 Decision Classification

### 2.1 Decision Categories

S5 validation results are classified into **exactly two categories**:

- **PASS**: Card passes S5 validation and is eligible for deployment
- **REGEN**: Card requires regeneration or has been regenerated

**Note**: FLAG status is **excluded** from this classification. FLAG automatically triggers REGEN, so it is handled within the REGEN category.

### 2.2 Decision Criteria (Pre-defined)

The decision criteria are **canonical and binding**, defined **before** S5 execution to ensure research design integrity:

- **REGEN** if:
  - `regeneration_trigger_score < 70.0` OR
  - `s5_was_regenerated == True`
  
- **PASS** if:
  - `regeneration_trigger_score >= 70.0` AND
  - `s5_was_regenerated == False`

See `S5_Decision_Definition_Canonical.md` for complete specification.

### 2.3 FLAG Group Disposal

**Decision**: FLAG group is **completely excluded** from the research design.

**Rationale**:
- FLAG status automatically triggers REGEN in S5 logic
- Separate FLAG group is unnecessary and would complicate analysis
- All FLAG cards are handled as REGEN in the assignment logic

**Implementation**: FLAG cards are converted to REGEN in the decision function.

---

## 3. Sampling Strategy

### 3.1 Core Principle: "Selection and Focus"

Based on statistical consultation, the study adopts a **"selection and focus"** strategy:

1. **FLAG disposal**: Complete exclusion (0 cases)
2. **REGEN census review**: Exhaustive sampling when feasible
3. **PASS concentration**: Allocate remaining resources to PASS group for safety validation

### 3.2 REGEN Group: Census Review Strategy

#### 3.2.1 Decision Rule

- **If REGEN ≤ 200 cards**: **Census review (exhaustive sampling)**
  - All REGEN cards are assigned for evaluation
  - Provides 100% coverage of AI-modified items
  
- **If REGEN > 200 cards**: **Cap at 200 cards**
  - Random sampling of 200 REGEN cards (seed: 20260101)
  - Ensures manageable evaluation workload

#### 3.2.2 Rationale

- **Completeness claim**: "All AI-modified items (REGEN) were exhaustively reviewed"
- **Statistical power**: Census review provides maximum information for REGEN group
- **Practical constraint**: Cap prevents excessive workload when REGEN count is high

#### 3.2.3 Assignment Logic

```python
if total_regen_count <= 200:
    assigned_regen = all_regen_cards  # Census
    regen_census = True
else:
    assigned_regen = random_sample(regen_cards, n=200, seed=20260101)  # Cap
    regen_census = False
```

### 3.3 PASS Group: Concentration Strategy

#### 3.3.1 Allocation Principle

**All remaining allocation slots are concentrated in the PASS group** to maximize safety validation power.

#### 3.3.2 Calculation

```python
total_resident_slots = 1350
calibration_slots = 45  # Fixed
regen_slots = min(total_regen_count, 200)  # Variable
pass_slots = total_resident_slots - calibration_slots - regen_slots
```

#### 3.3.3 Rationale

- **Safety validation**: PASS group represents "safe" cards for deployment
- **Upper bound estimation**: Larger PASS sample → tighter confidence interval for error rate
- **Statistical efficiency**: Concentrating resources maximizes precision of safety claim

### 3.4 Calibration Design (Partial Overlap)

#### 3.4.1 Purpose

Establish **inter-rater consistency** and **evaluation standard alignment** among all 9 resident evaluators using a statistically robust partial overlap design.

#### 3.4.2 Design Rationale

기존 Full Overlap 설계(5개×9명)의 한계:
- n=5는 ICC 추정의 정밀도가 낮음 (95% CI 폭 ≈ 0.59)
- 5개 문항이 전체를 대표하는지 불확실

**Partial Overlap 설계 채택** (통계 자문 반영):
- n(문항 수)을 늘리는 것이 ICC 정밀도에 더 효과적
- k=3도 문헌에서 충분히 수용되는 평가자 수 (Koo & Li, 2016)
- 95% CI 폭 ≈ 0.30으로 개선

#### 3.4.3 Design Specification

| 항목 | 값 |
|------|-----|
| **Unique 문항 수** | **33개** (11개 분과 × 3문제) |
| 문항당 평가자 (k) | 3명 |
| 총 Calibration slots | 33 × 3 = **99 slots** |
| 전공의 1인당 Calibration 문항 | 99 ÷ 9 = **11개** |

#### 3.4.3.1 분과별 균등 배정 (Stratified by Specialty)

Calibration 문항은 **전문의 330개 pool에서 선택**하여 Realistic 이미지 포함을 보장:

| 분과 | Calibration 문항 |
|------|-----------------|
| neuro_hn_imaging (신경두경부영상) | 3개 |
| breast_rad (유방영상) | 3개 |
| thoracic_radiology (흉부영상) | 3개 |
| interventional_radiology (인터벤션) | 3개 |
| musculoskeletal_radiology (근골격영상) | 3개 |
| gu_radiology (비뇨생식기영상) | 3개 |
| cardiovascular_rad (심장영상) | 3개 |
| abdominal_radiology (복부영상) | 3개 |
| physics_qc_informatics (물리) | 3개 |
| pediatric_radiology (소아영상) | 3개 |
| nuclear_med (핵의학) | 3개 |
| **총계** | **33개** |

**장점**:
- 모든 분과가 calibration에 균등 대표
- 전문의 330에 포함 → Realistic 이미지 보장
- 분과별 ICC 하위분석 가능

#### 3.4.4 Balanced Assignment

각 문항을 **무작위 3명**에게 배정하되, **모든 전공의가 총 10개씩** 중복문항을 받도록 균형:

```python
# Balanced Incomplete Block Design
# 30개 문항, 각 문항을 3명에게 배정
# 9명 전공의가 각각 10개씩 중복 문항 평가

def create_calibration_schedule(items: List[str], residents: List[str], seed: int = 20260101):
    """
    30개 문항을 3명씩 균형 배정
    - 각 문항: 정확히 3명이 평가
    - 각 전공의: 정확히 10개 문항 평가
    """
    import random
    random.seed(seed)
    
    n_items = 30
    n_residents = 9
    k_per_item = 3
    items_per_resident = (n_items * k_per_item) // n_residents  # 10
    
    # ... balanced assignment logic ...
```

#### 3.4.5 Selection Criteria

- Selected from PASS pool (before PASS allocation)
- **층화추출 (Stratified Sampling)** 권장:
  - PASS/REGEN 비율 반영
  - Specialty 분포 반영
- Random sampling with fixed seed (20260101)
- Items used for calibration are excluded from individual PASS allocation pool

#### 3.4.6 Position Randomization

학습효과/피로효과 방지를 위해:
- Calibration 10개를 맨 앞에 몰지 않음
- 150개 평가 문항 내에서 **랜덤 위치**에 분산 배치
- 평가자별로 위치 랜덤화

#### 3.4.7 Statistical Analysis

- **Inter-rater reliability**: ICC (n=30, k=3) - 문헌 권장 충족
  - 예상 95% CI 폭: ~0.30 (ICC=0.7 가정)
- **Standard alignment**: Assess agreement on blocking errors and error categories
- **Quality control**: Identify evaluators with systematic deviations for retraining

#### 3.4.8 Unique 문항 수 계산

```python
# 기존 (Full Overlap)
unique_reduction_old = 5 × (9 - 1) = 40

# 신규 (Partial Overlap, 분과별 균등)
unique_reduction_new = 33 × (3 - 1) = 66

# 추가 감소: 26개 (66 - 40)
# 전체 unique 문항: 1,350 - 66 = 1,284개
```

---

## 4. Assignment Algorithm

### 4.1 Resident Assignment (Total: 1,350 evaluations)

#### Step 1: Calibration Set Selection (Partial Overlap, Specialty-Stratified)
- Select **33 unique items** from **전문의 330 pool** (분과별 3문제 × 11분과)
- Assign each item to **exactly 3 residents** (balanced assignment)
- Each resident receives **exactly 11 calibration items**
- Total slots: 33 × 3 = **99 slots**
- Remove calibration items from individual PASS allocation pool
- **Realistic 이미지 포함 보장**: 전문의 330에서 선택하므로 자동 포함

```python
# Calibration 배정 예시 (분과별 균등)
n_specialties = 11
items_per_specialty = 3
calibration_items = n_specialties * items_per_specialty  # 33
calibration_slots = calibration_items * 3  # 99
items_per_resident = calibration_slots // 9  # 11
```

#### Step 2: REGEN Processing
- Apply census (≤200) or cap (>200) logic
- Assign each REGEN item to 1 resident (1:1 assignment)
- Total REGEN slots = number of assigned REGEN items

#### Step 3: PASS Allocation
- Calculate remaining slots: `1350 - 99 - regen_slots`
- Randomly sample from remaining PASS pool
- Ensure cluster (Objective) balance via shuffle

```python
# 예시 계산
total_slots = 1350
calibration_slots = 99  # 33 × 3
regen_slots = 100  # 예시
pass_slots = 1350 - 99 - 100 = 1151
```

#### Step 4: Distribution
- Calibration: 각 전공의에게 배정된 10개 문항 분배
- REGEN + PASS: Round-robin 또는 chunk 방식으로 균등 분배
- **위치 랜덤화**: Calibration 10개를 150개 내에서 랜덤 위치에 분산
- Apply cluster-aware shuffle for statistical independence

### 4.2 Specialist Assignment (Total: 330 evaluations)

#### Strategy: Subsampling from Resident Assignments

- **100% overlap**: All specialist assignments are subsampled from resident assignments
- **Purpose**: Enable direct comparison and reference standard validation

#### Step 1: REGEN Prioritization
- Include all REGEN items assigned to residents (up to 200)
- Prioritize specialty-matched REGEN items

#### Step 2: PASS Subsampling
- Sample remaining slots from resident-assigned PASS items
- Specialty-matched: Each specialist receives items from their subspecialty
- Total: 30 items per specialist (11 specialists × 30 = 330)

#### Step 3: Specialty Distribution

Each specialist is assigned 30 items from their subspecialty:

- **neuro_hn_imaging** (신경두경부영상): 30 items
- **breast_rad** (유방영상): 30 items
- **thoracic_radiology** (흉부영상): 30 items
- **interventional_radiology** (인터벤션): 30 items
- **musculoskeletal_radiology** (근골격영상): 30 items
- **gu_radiology** (비뇨생식기영상): 30 items
- **cardiovascular_rad** (심장영상): 30 items
- **abdominal_radiology** (복부영상): 30 items
- **physics_qc_informatics** (물리): 30 items
- **pediatric_radiology** (소아영상): 30 items
- **nuclear_med** (핵의학): 30 items

---

## 5. Statistical Methods

### 5.1 Safety Validation (PASS Group)

#### 5.1.1 Primary Hypothesis

**H₀**: False negative rate (FN) ≥ 0.3%  
**H₁**: False negative rate (FN) < 0.3%

#### 5.1.2 Statistical Method

**Clopper-Pearson exact confidence interval** for binomial proportion.

#### 5.1.3 Sample Size and Power

- **Expected PASS sample**: ~1,100-1,300 evaluations
- **If n=1,300, errors=0**: 
  - 95% CI upper bound: **0.23%**
  - 99% CI upper bound: **0.35%**
- **If n=1,100, errors=0**:
  - 95% CI upper bound: **0.27%**
  - 99% CI upper bound: **0.41%**

#### 5.1.4 Interpretation

- **Safety claim**: "Upper bound of false negative rate is 0.23%-0.27% with 95% confidence"
- **Clinical significance**: FN < 0.3% threshold is met with high confidence

### 5.2 Completeness Validation (REGEN Group)

#### 5.2.1 Primary Hypothesis

**H₀**: REGEN items are not acceptable as-is  
**H₁**: REGEN items are acceptable as-is (Accept-as-is rate > threshold)

#### 5.2.2 Statistical Method

- **Census review**: 100% coverage when REGEN ≤ 200
- **Cap sampling**: Random sample of 200 when REGEN > 200
- **Accept-as-is rate**: Proportion of REGEN items rated as acceptable without further modification

#### 5.2.3 Interpretation

- **Completeness claim**: "All AI-modified items (REGEN) were exhaustively reviewed (census review)"
- **Acceptability**: Report accept-as-is rate with confidence interval

### 5.3 Reliability Validation (Calibration)

#### 5.3.1 Primary Metric

**Inter-rater reliability** measured by:
- **Intraclass Correlation Coefficient (ICC)** for continuous/ordinal ratings
- **Fleiss' Kappa** for categorical ratings (blocking error, error category)

#### 5.3.2 Interpretation

- **Reliability claim**: "5 common items evaluated by all 9 residents to establish inter-rater consistency"
- **Standard alignment**: ICC > 0.7 indicates good agreement

### 5.4 Cluster (Objective) Balance

#### 5.4.1 Purpose

Ensure **statistical independence** by balancing cluster (Objective) distribution across evaluators.

#### 5.4.2 Method

- Shuffle assignments with cluster (Objective) awareness
- Prevent clustering of items from same Objective to same evaluator
- Maintain representativeness of specialty distribution

---

## 6. Manuscript Methods Section (Draft Text)

### 6.1 Safety Validation (PASS Group)

> "To validate the safety of S5-PASS cards, we conducted a comprehensive audit of 1,300 randomly selected PASS cards evaluated by 9 resident physicians. Each card was evaluated for blocking errors (factual errors, clinical errors, hallucinations) using a standardized evaluation protocol. Using Clopper-Pearson exact confidence intervals, we estimated the upper bound of the false negative rate to be **0.23%-0.27% with 95% confidence**, well below our pre-specified safety threshold of 0.3%."

### 6.2 Completeness Validation (REGEN Group)

> "All AI-modified cards (S5-REGEN) underwent **census review (exhaustive sampling)** to ensure complete coverage of items requiring regeneration. When REGEN count exceeded 200 cards, we applied a cap of 200 randomly sampled items (seed: 20260101) to maintain evaluation feasibility. This exhaustive sampling strategy ensures that all AI-identified quality issues were reviewed by expert evaluators."

### 6.3 Reliability Validation (Calibration)

> "To establish inter-rater consistency and evaluation standard alignment, all 9 resident evaluators independently evaluated **5 common items (calibration set)** selected from the PASS pool. These calibration items were excluded from primary statistical analysis but served to align evaluation criteria across evaluators. Inter-rater reliability was assessed using intraclass correlation coefficient (ICC), with ICC > 0.7 indicating good agreement."

### 6.4 Assignment Strategy

> "Assignment followed a 'selection and focus' strategy: (1) FLAG group was excluded (handled within REGEN), (2) REGEN group received census review (≤200) or cap (>200), and (3) all remaining allocation slots were concentrated in the PASS group to maximize safety validation power. Specialist assignments (n=330, 30 per specialist) were subsampled from resident assignments with 100% overlap, enabling direct comparison and reference standard validation."

---

## 7. Quality Control and Validation

### 7.1 Pre-Assignment Validation

- [ ] All cards have S5 decision assigned (PASS or REGEN)
- [ ] No cards have FLAG status (converted to REGEN)
- [ ] REGEN count verified (≤200 for census, or exactly 200 for cap)
- [ ] PASS count + REGEN count + Calibration count = total cards

### 7.2 Assignment Validation

- [ ] Total resident assignments = 1,350
- [ ] Calibration assignments = 45 (5 items × 9 residents)
- [ ] REGEN assignments = expected count (census or cap)
- [ ] PASS assignments = remaining slots
- [ ] All residents receive same 5 calibration items
- [ ] Cluster (Objective) balance verified

### 7.3 Specialist Assignment Validation

- [ ] Total specialist assignments = 330 (11 × 30)
- [ ] Each specialist receives 30 items from their subspecialty
- [ ] 100% overlap with resident assignments verified
- [ ] REGEN items prioritized in specialist assignments

### 7.4 Statistical Validation

- [ ] PASS sample size sufficient for 0.3% threshold (n ≥ 1,000)
- [ ] Clopper-Pearson CI calculated correctly
- [ ] Calibration ICC calculated
- [ ] Cluster balance verified

---

## 8. Visual Modality Sub-study (Paper 2)

### 8.1 Purpose

Visual Modality Sub-study는 **Illustration (S5-refined) vs Realistic (MLLM Raw)** 이미지의 임상적 정확성과 선호도를 비교합니다.

### 8.2 Design Change: Resident Realistic Evaluation

**기존 설계 문제점**:
- Realistic 이미지는 전문의 1인 평가만 있음
- Inter-rater reliability 계산 불가
- 통계적 파워 약함

**변경된 설계**:

| 평가자 | Illustration | Realistic | 총 평가량 |
|--------|--------------|-----------|-----------|
| Resident | 1,350개 | 330개 (NEW) | 1,680개 |
| Specialist | 330개 | 330개 | 660개 (변동 없음) |

### 8.3 Paired Comparison Design

```
┌─────────────────────────────────────────────────────────────────┐
│                 Same Item (n=330, Paired Design)                 │
├───────────────────────────┬─────────────────────────────────────┤
│    Illustration           │         Realistic                   │
│    (S5-refined)           │         (MLLM Raw)                  │
├───────────────────────────┼─────────────────────────────────────┤
│  Resident: ✅             │  Resident: ✅                       │
│  Specialist: ✅           │  Specialist: ✅                     │
├───────────────────────────┴─────────────────────────────────────┤
│  분석:                                                           │
│  • Paired comparison (Wilcoxon/paired t-test)                   │
│  • Inter-rater reliability (ICC) per modality                   │
│  • Expertise × Modality interaction (2×2 mixed-effects)         │
└─────────────────────────────────────────────────────────────────┘
```

### 8.4 Resident Realistic Evaluation Workflow

#### 8.4.1 Evaluation Sequence

1. **Step 1**: Illustration 평가 (전체 1,350개, 기존)
2. **Step 2**: Realistic 평가 (전문의 할당 330개, 추가)
   - 전공의: 전문의 할당과 동일한 330개 문항의 Realistic 이미지
   - 전문의: 동일 330개 문항의 Realistic 이미지
   - **Calibration 중복 유지**: Illustration과 같은 3명이 Realistic도 평가

#### 8.4.2 Calibration in Realistic Evaluation

Calibration 30개가 전문의 330개에 포함된 경우:
- **Illustration**: 3명 Resident + 1명 Specialist = 4명
- **Realistic**: 3명 Resident + 1명 Specialist = 4명 (같은 평가자)
- **Paired comparison**: 같은 평가자가 두 modality 평가하여 within-subject 비교 가능

```
Calibration 30개:
- 평가자 수: 4명 (3 Resident + 1 Specialist)
- 평가 modality: 2 (Illustration + Realistic)
- 총 evaluations/item: 8
```

#### 8.4.3 Workload Analysis

| 항목 | 값 |
|------|-----|
| Realistic 평가 문항 | 330개 |
| - Calibration (중복) | 30개 × 3명 = 90 slots |
| - Non-calibration | 300개 × 1명 = 300 slots |
| **총 Realistic slots** | **390** |
| 카드당 평가 시간 (Realistic) | ~2분 (이미 문항 익숙) |
| 전공의 1인당 추가 평가 | 390 ÷ 9 = **~43개** |
| 1인당 추가 시간 | ~1.5시간/인 |

#### 8.4.4 Total Workload per Resident

| 평가 유형 | 문항 수 |
|----------|--------|
| Illustration (기존) | 150개 |
| Realistic (추가) | ~43개 |
| **총계** | **~193개** |

### 8.5 Realistic Image Evaluation Items

| 항목 | 필드명 | 타입 |
|------|--------|------|
| Modality Accuracy | `realistic_modality_accuracy` | 0.0/0.5/1.0 |
| Anatomical Accuracy | `realistic_anatomical_accuracy` | 0.0/0.5/1.0 |
| Educational Preference | `image_preference` | Illustration / Realistic / No Preference |
| Clinical Realism | `realistic_clinical_realism` | 1-5 Likert |

### 8.6 Analysis Plan

#### 8.6.1 Inter-rater Reliability (Realistic)

```
ICC(Realistic) = ICC(Resident, Specialist) for n=330 items
Target: ICC > 0.7 (good agreement)
```

#### 8.6.2 Visual Modality Comparison (Paired)

```
Within-subject comparison:
- Same item, Same rater
- Illustration score vs Realistic score
- Paired t-test or Wilcoxon signed-rank test
```

#### 8.6.3 Expertise × Modality Interaction

```
2×2 Design:
- Modality: Illustration vs Realistic
- Evaluator: Resident vs Specialist
- Analysis: Mixed-effects model with interaction term
```

### 8.7 Advantages

| 항목 | 기존 | 변경 후 |
|------|------|---------|
| Realistic 평가자 수 | 1인 (전문의) | 2인 (전공의+전문의) |
| Inter-rater reliability | ❌ 계산 불가 | ✅ ICC 계산 가능 |
| Visual modality 비교 파워 | 약함 | 강화 |
| 전문성 차이 분석 | ❌ | ✅ (Resident vs Specialist) |
| 추가 워크로드 | - | ~1.2시간/인 (수용 가능) |

---

## 9. Research Design Integrity

### 9.1 Pre-Registration

All design elements are **pre-defined** before S5 execution:

- ✅ S5 decision criteria (PASS/REGEN) defined in `S5_Decision_Definition_Canonical.md`
- ✅ Sampling strategy (census vs. cap) defined
- ✅ Assignment algorithm defined
- ✅ Statistical methods defined
- ✅ Sample size targets defined

### 9.2 Change Control

**No post-hoc modifications** are permitted after S5 results are available. Any changes require:

1. Version bump (e.g., 1.0 → 1.1)
2. Documented rationale
3. Impact assessment
4. IRB protocol amendment (if applicable)

### 9.3 Reproducibility

- **Fixed seed**: 20260101 for all random sampling
- **Deterministic assignment**: Same inputs → same outputs
- **Version control**: All code and specifications versioned

---

## 10. Related Documents

- `0_Protocol/05_Pipeline_and_Execution/S5_Decision_Definition_Canonical.md`: S5 decision criteria
- `0_Protocol/06_QA_and_Study/QA_Operations/FINAL_QA_Assignment_Handover.md`: Implementation handover
- `0_Protocol/06_QA_and_Study/QA_Operations/FINAL_QA_Assignment_Guide.md`: Assignment algorithm guide
- `0_Protocol/06_QA_and_Study/Table_Infographic_Evaluation_Plan.md`: Table Infographic 평가 계획
- `2_Data/metadata/generated/FINAL_DISTRIBUTION/qa_handover_allocation_6000cards.md`: Allocation details

---

## 11. Version History

- **v1.3** (2026-01-04): Calibration 분과별 균등 배정
  - Calibration 문항 수 변경: 30개 → **33개** (11분과 × 3문제)
  - 각 전공의 11개 calibration 문항 배정 (99 slots)
  - **전문의 330에서 선택**: Realistic 이미지 포함 보장
  - 모든 분과가 calibration에 균등 대표

- **v1.2** (2026-01-04): Calibration Partial Overlap 설계 도입
  - Calibration 설계 변경: 5개×9명 → **30개×3명** (Partial Overlap)
  - ICC 정밀도 개선: 95% CI 폭 0.59 → 0.30
  - 각 전공의 10개 calibration 문항 배정 (균형 배정)
  - Realistic 평가에서 calibration 중복 유지 (시나리오 A)
  - 전공의 총 workload: ~193개/인 (Illustration 150 + Realistic ~43)
  - 위치 랜덤화 도입 (학습효과/피로효과 방지)

- **v1.1** (2026-01-04): Visual Modality Sub-study 확장
  - Resident Realistic 이미지 평가 추가 (330개)
  - 2-rater 설계로 ICC 계산 가능
  - Expertise × Modality interaction 분석 추가
  - Table Infographic Evaluation Plan 참조 추가

- **v1.0** (2026-01-01): Initial canonical specification
  - FLAG disposal decision
  - REGEN census review strategy
  - PASS concentration strategy
  - Calibration design (5 items × 9 residents)
  - Statistical methods (Clopper-Pearson)
  - Manuscript methods section draft

---

**Document Status**: Canonical  
**Version**: 1.3  
**Last Updated**: 2026-01-04  
**Owner**: MeducAI Research Team  
**Review Required**: Before any modification to research design


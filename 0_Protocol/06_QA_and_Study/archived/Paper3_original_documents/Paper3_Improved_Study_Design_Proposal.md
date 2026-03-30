# Paper 3 개선된 연구 설계 제안

**Status:** Proposal (Study Design Improvement)  
**Version:** 1.0  
**Date:** 2026-01-15  
**Purpose:** 모의고사 기반 objective measure를 포함한 개선된 연구 설계 제안

---

## 제안하신 설계 분석

### 제안 설계 요약
- **시점**: 11월 시험 전 (1~4년차 대상)
- **Baseline**: 모의고사 50문제
- **Intervention**: 한달간 Anki 판독량 로그 제출
- **Outcome**: 점수 변화 (Before-After)

### 강점 ✅

1. **Objective Measure 추가**
   - 모의고사 점수는 객관적 측정
   - Self-reported bias 감소
   - Reviewer가 선호하는 outcome

2. **Before-After 비교**
   - Within-subject design
   - Baseline 조정 가능 (ANCOVA)
   - 통계적 파워 향상

3. **Anki 로그 활용**
   - 실제 사용량 측정
   - Dose-response 분석 가능
   - Objective validation

### 개선 필요 사항 ⚠️

1. **Control Group 부재**
   - Confounding 통제 어려움
   - 인과성 추론 제한

2. **1~4년차 혼재**
   - Training level 차이
   - Baseline knowledge 차이 큼

3. **한달 기간**
   - 학습 효과 측정에 충분한가?
   - Retention 측정 어려움

---

## 개선된 연구 설계 옵션

### 옵션 1: Waitlist Control Design (권장 ⭐⭐⭐⭐⭐)

#### 설계 개요

```
┌─────────────────────────────────────────────────────────────┐
│                    Waitlist Control Design                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Baseline (T0)          Intervention (T1)    Follow-up (T2)│
│  ┌──────────┐            ┌──────────┐         ┌──────────┐ │
│  │모의고사  │            │          │         │          │ │
│  │50문제    │            │          │         │          │ │
│  │+ 설문    │            │          │         │          │ │
│  └────┬─────┘            └────┬─────┘         └────┬─────┘ │
│       │                       │                     │       │
│  ┌────▼───────────────────────▼─────────────────────▼────┐ │
│  │  Intervention Group (n=XX)                             │ │
│  │  • MeducAI Anki 사용 (1개월)                          │ │
│  │  • 주간 로그 제출                                     │ │
│  │  • T1: 모의고사 50문제 (1개월 후)                     │ │
│  │  │                                                    │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Control Group (Waitlist, n=XX)                     │ │
│  │  • 기존 학습 방법 유지                               │ │
│  │  • T1: 모의고사 50문제 (1개월 후, 동일 시점)         │ │
│  │  • T2: MeducAI 제공 (1개월 후, delayed access)       │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### 타임라인

| 시점 | Intervention Group | Control Group |
|------|-------------------|---------------|
| **T0 (Baseline)** | 모의고사 50문제 + 설문 | 모의고사 50문제 + 설문 |
| **T1 (1개월 후)** | 모의고사 50문제 + 설문 + Anki 로그 | 모의고사 50문제 + 설문 |
| **T2 (2개월 후)** | 설문 (Retention) | MeducAI 제공 + 설문 |

#### 주요 특징

1. **Randomization**
   - 1:1 randomization (stratified by PGY, baseline score)
   - Allocation concealment

2. **Primary Outcome**
   - **모의고사 점수 변화 (T0 → T1)**
     - Intervention: T1 - T0
     - Control: T1 - T0
     - **ANCOVA**: Baseline score 조정

3. **Secondary Outcomes**
   - Anki 로그 기반 사용량 (cards reviewed, time spent)
   - Dose-response (usage vs score improvement)
   - Retention (T2에서 재측정)

4. **통계 분석**
   ```r
   # Primary analysis
   model <- lm(
     score_T1 ~ group + score_T0 + pgy + baseline_covariates,
     data = study_data
   )
   
   # Effect size
   effect_size <- (mean_intervention - mean_control) / pooled_sd
   ```

#### 장점 ✅

1. **인과성 추론 강화**
   - Control group으로 confounding 통제
   - Randomization으로 selection bias 제거

2. **윤리적 고려**
   - Control group도 나중에 MeducAI 제공 (Waitlist)
   - 참여자 거부감 감소

3. **통계적 파워**
   - Between-group comparison
   - Within-subject change도 활용 가능

4. **Reviewer 선호**
   - RCT에 가까운 설계
   - Accept 확률 향상 (60-75% → 80-90%)

#### 단점 ⚠️

1. **Contamination Risk**
   - Control group이 다른 AI 도구 사용 가능
   - 완전한 blinding 어려움

2. **Sample Size 증가**
   - Control group 필요
   - 최소 n=50 per group (총 100명)

---

### 옵션 2: Stepped-Wedge Cluster Randomized Trial

#### 설계 개요

```
┌─────────────────────────────────────────────────────────────┐
│         Stepped-Wedge Cluster Randomized Trial               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Cluster 1 (Hospital A):  Control → Intervention           │
│  Cluster 2 (Hospital B):  Control → Intervention           │
│  Cluster 3 (Hospital C):  Control → Intervention           │
│                                                              │
│  Time:  T0      T1      T2      T3                          │
│         │       │       │       │                           │
│  ┌──────▼───────▼───────▼───────▼──────┐                   │
│  │  모든 Cluster: Baseline 모의고사     │                   │
│  │  Cluster 1: Intervention 시작       │                   │
│  │  Cluster 2: Intervention 시작       │                   │
│  │  Cluster 3: Intervention 시작       │                   │
│  └─────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

#### 장점 ✅

1. **윤리적 우수성**
   - 모든 참여자가 결국 intervention 받음
   - Cluster 단위로 점진적 도입

2. **실용성**
   - 실제 배포 상황과 유사
   - Hospital-level implementation

#### 단점 ⚠️

1. **복잡성**
   - 분석이 복잡 (mixed-effects model)
   - Cluster 수 필요 (최소 6-8개)

2. **Time Effect**
   - 시점에 따른 효과 혼재 가능

---

### 옵션 3: Historical Control + Propensity Matching

#### 설계 개요

```
┌─────────────────────────────────────────────────────────────┐
│         Historical Control Design                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Intervention Group (2026):                                  │
│  • T0: 모의고사 50문제                                       │
│  • 1개월 MeducAI 사용                                        │
│  • T1: 모의고사 50문제                                       │
│                                                              │
│  Historical Control (2025):                                  │
│  • T0: 모의고사 50문제 (동일 문제)                          │
│  • 1개월 기존 학습 방법                                      │
│  • T1: 모의고사 50문제                                       │
│                                                              │
│  Analysis: Propensity Score Matching                        │
└─────────────────────────────────────────────────────────────┘
```

#### 장점 ✅

1. **실용성**
   - Control group 모집 불필요
   - 기존 데이터 활용

2. **윤리적 고려**
   - 모든 참여자가 intervention 받음

#### 단점 ⚠️

1. **Temporal Confounding**
   - 연도별 차이 (curriculum, difficulty)
   - 완전한 통제 어려움

2. **Reviewer 선호도 낮음**
   - Historical control은 약함
   - Accept 확률 낮음 (50-60%)

---

## 최종 권장 설계: Waitlist Control Design

### 상세 설계

#### 1. 참여자 모집

**대상:**
- 영상의학과 1~4년차 전공의
- 전문의 시험 준비 중인 4년차 우선
- 1~3년차는 보조 분석용

**모집 규모:**
- **Primary analysis**: 4년차만 (n=60-80)
- **Secondary analysis**: 전체 (n=100-120)

**Stratification:**
- PGY (1, 2, 3, 4)
- Baseline 모의고사 점수 (tertiles)
- Hospital (if multi-center)

#### 2. Randomization

**방법:**
- Block randomization (block size = 4)
- Stratified by PGY, baseline score
- Allocation concealment (sealed envelopes)

**할당:**
- Intervention: Control = 1:1

#### 3. Intervention

**Intervention Group:**
- MeducAI Anki deck 제공
- 1개월 자유 사용
- 주간 로그 제출 (Anki sync data)

**Control Group:**
- 기존 학습 방법 유지
- 1개월 후 MeducAI 제공 (Waitlist)

#### 4. 모의고사 설계

**문제 구성:**
- 50문제 (전문의 시험 형식)
- 난이도 균형 (Easy:Medium:Hard = 1:2:1)
- 분과별 균등 배정

**시점:**
- **T0 (Baseline)**: Randomization 전
- **T1 (1개월 후)**: Intervention 종료 시점
- **T2 (2개월 후, 선택)**: Retention 측정

**문제 풀이:**
- 온라인 플랫폼 (Google Form, Qualtrics 등)
- 시간 제한: 90분 (전문의 시험과 유사)
- 자동 채점

#### 5. Anki 로그 수집

**수집 데이터:**
```json
{
  "user_id": "anonymous_id",
  "date": "2026-10-15",
  "cards_reviewed": 150,
  "new_cards": 20,
  "review_cards": 130,
  "study_time_minutes": 45,
  "retention_rate": 0.85,
  "cards_mastered": 12
}
```

**수집 방법:**
- Anki sync API 활용
- 또는 주간 리포트 (self-reported + validation)

#### 6. Primary Outcome

**Primary Endpoint:**
- **모의고사 점수 변화 (T0 → T1)**
  - Continuous: 0-50점 (또는 0-100점)
  - Change score: T1 - T0

**Analysis:**
```r
# Primary analysis (ANCOVA)
primary_model <- lm(
  score_T1 ~ group + score_T0 + pgy + baseline_covariates,
  data = study_data
)

# Effect size
cohen_d <- (mean_intervention - mean_control) / pooled_sd

# Minimum clinically important difference (MCID)
# 전문의 시험: 5점 차이 (10% improvement) = 교육적으로 의미있음
```

#### 7. Secondary Outcomes

1. **Dose-Response Analysis**
   ```r
   # Intervention group only
   dose_response <- lm(
     score_change ~ log(cards_reviewed) + log(study_time) + 
                    baseline_score + pgy,
     data = intervention_group
   )
   ```

2. **Subgroup Analysis**
   - By PGY (1-2년차 vs 3-4년차)
   - By baseline score (low/mid/high)
   - By usage intensity (low/medium/high)

3. **Retention (T2)**
   - 2개월 후 재측정 (선택)
   - Long-term learning effect

#### 8. Sample Size Calculation

**Power Analysis:**
```r
# Assumptions
alpha = 0.05
power = 0.80
effect_size = 0.5 (Cohen's d, medium effect)
baseline_correlation = 0.6 (T0-T1 correlation)

# ANCOVA sample size
n_per_group <- pwr.t.test(
  d = 0.5,
  power = 0.80,
  sig.level = 0.05,
  type = "two.sample"
)$n

# With 20% dropout
n_total <- n_per_group * 2 * 1.2
# Result: ~64 per group, total ~128
```

**권장 Sample Size:**
- **Minimum**: n=50 per group (총 100명)
- **Recommended**: n=60-70 per group (총 120-140명)
- **Ideal**: n=80 per group (총 160명)

#### 9. 통계 분석 계획

**Primary Analysis:**
- **ANCOVA**: Baseline score 조정
- **Effect size**: Cohen's d with 95% CI
- **MCID**: 5점 차이 (10% improvement)

**Secondary Analyses:**
- Dose-response (restricted cubic splines)
- Subgroup analysis (interaction terms)
- Per-protocol (usage ≥ threshold)

**Sensitivity Analyses:**
- Complete-case vs. imputed
- Different MCID thresholds
- Non-parametric alternatives

---

## 개선된 설계의 Accept 가능성

### Before (현재 설계)
- **Accept 가능성**: 60-75%
- **주요 리스크**: Observational design, Confounding

### After (Waitlist Control Design)
- **Accept 가능성**: **80-90%** ⬆️
- **주요 강점**: 
  - RCT에 가까운 설계
  - Objective measure (모의고사 점수)
  - Control group으로 confounding 통제

### 예상 Revision 지적사항

**Minor Revision 가능성 높음:**
1. "Sample size justification" → Power analysis 추가
2. "Contamination control" → Monitoring plan 추가
3. "MCID 정의" → 5점 차이 (10%) 정당화

**Major Revision 가능성 낮음:**
- Waitlist control은 표준적 방법
- Reviewer가 선호하는 설계

---

## 구현 체크리스트

### 연구 설계
- [ ] IRB 수정 (Waitlist control 추가)
- [ ] Randomization procedure 정의
- [ ] 모의고사 문제 50개 준비 (T0, T1 동일 또는 parallel forms)
- [ ] Anki 로그 수집 시스템 구축

### 데이터 수집
- [ ] 참여자 모집 (n=120-140 목표)
- [ ] Baseline 모의고사 (T0)
- [ ] Randomization 수행
- [ ] Intervention 시작
- [ ] 주간 Anki 로그 수집
- [ ] Follow-up 모의고사 (T1)
- [ ] Retention 측정 (T2, 선택)

### 분석 준비
- [ ] Power analysis 완료
- [ ] Statistical analysis plan (SAP) 업데이트
- [ ] Primary endpoint 명확히 정의
- [ ] MCID 정의 및 정당화

---

## 대안: 단순화된 설계 (실용적 제약 시)

### 옵션 4: Single-Arm Before-After (현재 제안)

**설계:**
- Baseline 모의고사 (T0)
- 1개월 MeducAI 사용
- Follow-up 모의고사 (T1)
- **Control group 없음**

**보완 방안:**
1. **Historical Control Matching**
   - 2025년 동일 모의고사 데이터 활용
   - Propensity score matching

2. **Within-Subject Design 강조**
   - Baseline 조정 (ANCOVA)
   - Dose-response analysis

3. **보수적 해석**
   - "Association" 강조
   - "Causation" 회피

**Accept 가능성:**
- **65-75%** (Waitlist보다 낮지만 실용적)

---

## 최종 권장사항

### 1순위: Waitlist Control Design ⭐⭐⭐⭐⭐

**이유:**
- Accept 확률 최고 (80-90%)
- 인과성 추론 강화
- Reviewer 선호
- 윤리적 고려 (모두 받음)

**구현 가능성:**
- Sample size: n=120-140 (실현 가능)
- Randomization: 표준적 방법
- 모의고사: 준비 필요하지만 가능

### 2순위: Single-Arm + Historical Control ⭐⭐⭐

**이유:**
- 실용적 제약 시 대안
- Control group 모집 불필요
- Accept 확률 중간 (65-75%)

---

**Document Status**: Proposal (Study Design Improvement)  
**Last Updated**: 2026-01-15  
**Owner**: MeducAI Research Team


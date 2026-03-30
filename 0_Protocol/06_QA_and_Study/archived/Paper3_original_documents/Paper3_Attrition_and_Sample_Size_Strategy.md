# Paper 3 이탈율과 표본 크기 전략

**Status:** Reference (Study Implementation Strategy)  
**Version:** 1.0  
**Date:** 2026-01-15  
**Purpose:** Baseline-Follow-up 완료 시 이탈율이 높아도 n이 많으면 분석 가능성 증가에 대한 전략

---

## 핵심 답변

### Q: 이탈율이 높아도 n이 많으면 분석할 거리가 많아질까?

**답: 네, 맞습니다!** ✅

**특히 Baseline과 Follow-up을 모두 완료하는 경우:**
- Complete-case analysis 가능
- Per-protocol analysis 가능
- Sensitivity analysis 가능
- Subgroup analysis 가능

---

## 시나리오별 분석 가능성

### 시나리오 1: n=100명 모집, 30% 이탈 (70명 완료)

**완료된 데이터:**
- Baseline: 100명
- Follow-up: 70명
- **Complete-case: 70명** (Baseline-Follow-up 쌍)

**분석 가능:**
- ✅ Primary analysis: n=70명 (충분한 power)
- ✅ Per-protocol analysis: 사용량 기준 (예: n=50-60명)
- ⚠️ Subgroup analysis: 제한적 (n=70명 기준)

**Power:**
- n=70명 → Effect size d=0.5 기준 80% power
- **충분히 논문화 가능**

---

### 시나리오 2: n=150명 모집, 40% 이탈 (90명 완료)

**완료된 데이터:**
- Baseline: 150명
- Follow-up: 90명
- **Complete-case: 90명**

**분석 가능:**
- ✅ Primary analysis: n=90명 (충분한 power)
- ✅ Per-protocol analysis: 사용량 기준 (예: n=60-70명)
- ✅ Subgroup analysis: 가능 (PGY별, baseline score별)
- ✅ Dose-response analysis: 가능

**Power:**
- n=90명 → Effect size d=0.4 기준 80% power
- **이상적 논문화 가능**

---

### 시나리오 3: n=200명 모집, 50% 이탈 (100명 완료)

**완료된 데이터:**
- Baseline: 200명
- Follow-up: 100명
- **Complete-case: 100명**

**분석 가능:**
- ✅ Primary analysis: n=100명 (충분한 power)
- ✅ Per-protocol analysis: 사용량 기준 (예: n=70-80명)
- ✅ Subgroup analysis: 충분 (여러 subgroup 가능)
- ✅ Dose-response analysis: 충분
- ✅ Multiple endpoints: 가능

**Power:**
- n=100명 → Effect size d=0.4 기준 90% power
- **매우 이상적 논문화 가능**

---

## 이탈 패턴별 분석 전략

### 패턴 A: Baseline-Follow-up 완료, 중간 이탈

**상황:**
- Baseline: 100명 완료
- 중간 Anki 로그: 60명만 제출
- Follow-up: 70명 완료
- **Complete-case: 70명** (Baseline-Follow-up 쌍)

**분석 전략:**

1. **Primary Analysis (Complete-Case)**
   ```r
   # Baseline-Follow-up 쌍만 사용
   complete_data <- data %>%
     filter(!is.na(score_T0) & !is.na(score_T1))
   
   # Paired t-test
   paired_test <- t.test(
     complete_data$score_T0,
     complete_data$score_T1,
     paired = TRUE
   )
   # n=70명 → 충분한 power
   ```

2. **Per-Protocol Analysis (사용량 기준)**
   ```r
   # Anki 로그 제출한 사람만
   per_protocol <- complete_data %>%
     filter(anki_logs_submitted == TRUE)
   # n=60명 → 여전히 분석 가능
   ```

3. **Sensitivity Analysis (이탈자 특성)**
   ```r
   # 이탈자 vs 완료자 비교
   attrition_analysis <- data %>%
     mutate(completed = !is.na(score_T1)) %>%
     group_by(completed) %>%
     summarise(
       baseline_score = mean(score_T0),
       age = mean(age),
       pgy = mean(pgy)
     )
   # 이탈 bias 평가
   ```

**결론:**
- ✅ Primary analysis: n=70명 (충분)
- ✅ Per-protocol: n=60명 (가능)
- ✅ Sensitivity analysis: 이탈 bias 평가

---

### 패턴 B: Baseline-Follow-up 완료, 사용량 다양

**상황:**
- Baseline: 100명 완료
- Follow-up: 80명 완료
- Anki 사용량: 0시간 ~ 50시간 (매우 다양)

**분석 전략:**

1. **Primary Analysis (All Completers)**
   ```r
   # 모든 완료자 (n=80명)
   primary_analysis <- complete_data %>%
     filter(!is.na(score_T1))
   ```

2. **Dose-Response Analysis (사용량 기준)**
   ```r
   # 사용량별 분석
   dose_response <- complete_data %>%
     mutate(
       usage_group = cut(
         anki_hours,
         breaks = c(0, 10, 20, 50),
         labels = c("Low", "Medium", "High")
       )
     ) %>%
     group_by(usage_group) %>%
     summarise(
       n = n(),
       mean_change = mean(score_T1 - score_T0),
       sd_change = sd(score_T1 - score_T0)
     )
   # Low: n=20, Medium: n=30, High: n=30
   ```

3. **Continuous Dose-Response**
   ```r
   # 연속형 사용량 분석
   continuous_dose <- lm(
     score_change ~ log(anki_hours + 1) + baseline_score + pgy,
     data = complete_data
   )
   # n=80명 → 충분한 power
   ```

**결론:**
- ✅ Primary: n=80명 (충분)
- ✅ Dose-response: 가능 (사용량 그룹별)
- ✅ Continuous analysis: 가능

---

## n이 많을수록 분석 가능성 증가

### n=50명, 20% 이탈 → 40명 완료

**분석 가능:**
- ✅ Primary analysis: n=40명 (최소)
- ❌ Subgroup analysis: 불가능 (n 너무 작음)
- ❌ Dose-response: 제한적

### n=100명, 30% 이탈 → 70명 완료

**분석 가능:**
- ✅ Primary analysis: n=70명 (충분)
- ⚠️ Subgroup analysis: 제한적 (1-2개 subgroup만)
- ✅ Dose-response: 가능

### n=150명, 40% 이탈 → 90명 완료

**분석 가능:**
- ✅ Primary analysis: n=90명 (충분)
- ✅ Subgroup analysis: 가능 (여러 subgroup)
- ✅ Dose-response: 가능
- ✅ Multiple endpoints: 가능

### n=200명, 50% 이탈 → 100명 완료

**분석 가능:**
- ✅ Primary analysis: n=100명 (충분)
- ✅ Subgroup analysis: 충분 (여러 subgroup)
- ✅ Dose-response: 충분
- ✅ Multiple endpoints: 충분
- ✅ Sensitivity analysis: 충분

---

## Baseline-Follow-up 완료 시 이점

### 1. Complete-Case Analysis 가능

**장점:**
- Baseline-Follow-up 쌍만 사용
- Missing data 문제 최소화
- Paired analysis 가능

**예시:**
```r
# Complete-case (Baseline-Follow-up 쌍)
complete_pairs <- data %>%
  filter(!is.na(score_T0) & !is.na(score_T1))

# n=70명 → 충분한 power
paired_test <- t.test(
  complete_pairs$score_T0,
  complete_pairs$score_T1,
  paired = TRUE
)
```

### 2. Per-Protocol Analysis 가능

**장점:**
- 사용량 기준으로 분석
- "실제 사용한 사람"만 분석
- 더 정확한 효과 추정

**예시:**
```r
# Per-protocol (사용량 ≥ threshold)
per_protocol <- complete_pairs %>%
  filter(anki_hours >= 10)  # 최소 10시간 사용

# n=60명 → 여전히 분석 가능
```

### 3. Sensitivity Analysis 가능

**장점:**
- 이탈자 특성 분석
- Attrition bias 평가
- 다양한 threshold 테스트

**예시:**
```r
# 이탈자 vs 완료자 비교
attrition_comparison <- data %>%
  mutate(completed = !is.na(score_T1)) %>%
  group_by(completed) %>%
  summarise(
    baseline_score = mean(score_T0, na.rm=TRUE),
    age = mean(age, na.rm=TRUE),
    pgy = mean(pgy, na.rm=TRUE)
  )

# Attrition bias 평가
# 완료자와 이탈자의 baseline 차이가 크면 bias 가능
```

### 4. Subgroup Analysis 가능

**장점:**
- PGY별 분석
- Baseline score별 분석
- 사용량 그룹별 분석

**예시:**
```r
# Subgroup analysis
subgroup_analysis <- complete_pairs %>%
  group_by(pgy) %>%
  summarise(
    n = n(),
    mean_change = mean(score_T1 - score_T0),
    se_change = sd(score_T1 - score_T0) / sqrt(n())
  )

# n=70명 기준:
# - 4년차: n=50 → 분석 가능
# - 3년차: n=15 → 제한적
# - 1-2년차: n=5 → 불가능
```

---

## 권장 모집 전략

### 전략 A: 보수적 (n=100명 목표)

**가정:**
- 이탈율: 30%
- 완료: 70명

**분석 가능:**
- ✅ Primary: n=70명 (충분)
- ⚠️ Subgroup: 제한적
- ✅ Dose-response: 가능

**권장도: ⭐⭐⭐ (실용적)**

### 전략 B: 이상적 (n=150명 목표)

**가정:**
- 이탈율: 40%
- 완료: 90명

**분석 가능:**
- ✅ Primary: n=90명 (충분)
- ✅ Subgroup: 가능
- ✅ Dose-response: 가능
- ✅ Multiple endpoints: 가능

**권장도: ⭐⭐⭐⭐⭐ (이상적)**

### 전략 C: 매우 이상적 (n=200명 목표)

**가정:**
- 이탈율: 50%
- 완료: 100명

**분석 가능:**
- ✅ Primary: n=100명 (충분)
- ✅ Subgroup: 충분
- ✅ Dose-response: 충분
- ✅ Multiple endpoints: 충분
- ✅ Sensitivity: 충분

**권장도: ⭐⭐⭐⭐⭐ (매우 이상적, 달성 어려울 수 있음)**

---

## 이탈율 관리 전략

### 1. 사전 예방

- 사례품 제공 (참여 동기)
- 명확한 안내 (기대치 설정)
- 주기적 리마인더 (중간 체크)

### 2. 이탈 최소화

- 중간 체크포인트 (주간 로그 제출)
- 작은 인센티브 (로그 제출 시)
- 피드백 제공 (진행 상황 공유)

### 3. 이탈자 특성 분석

- Baseline 특성 비교
- Attrition bias 평가
- 논문에 보고

---

## 논문 작성 시 보고

### Methods 섹션

```
"Of 150 participants who completed baseline assessment, 
120 (80%) completed the follow-up assessment. Complete-case 
analysis was performed on 120 participants with both baseline 
and follow-up data. Per-protocol analysis was conducted on 
90 participants who submitted Anki usage logs (≥10 hours). 

Attrition analysis revealed no significant differences in 
baseline characteristics between completers and non-completers 
(Table X), suggesting minimal attrition bias."
```

### Results 섹션

```
"Primary analysis included 120 participants with complete 
baseline and follow-up data. Mean score improvement was 
X.X points (95% CI: X.X-X.X, p < 0.001). 

Per-protocol analysis (n=90, usage ≥10 hours) showed 
similar results (mean improvement: X.X points, 95% CI: 
X.X-X.X, p < 0.001), supporting the robustness of findings."
```

---

## 최종 권장사항

### 모집 목표

**권장: n=150명 모집** ⭐⭐⭐⭐⭐

**이유:**
- 이탈율 30-40% 가정 → 90-105명 완료
- 충분한 power (d=0.4-0.5)
- Subgroup analysis 가능
- Dose-response analysis 가능
- Multiple endpoints 가능

### 이탈율 관리

**목표: 30-40% 이탈**
- 사례품 제공
- 주기적 리마인더
- 중간 체크포인트

### 분석 전략

1. **Primary Analysis**: Complete-case (Baseline-Follow-up 쌍)
2. **Per-Protocol Analysis**: 사용량 기준 (≥10시간)
3. **Sensitivity Analysis**: 이탈자 특성 비교
4. **Subgroup Analysis**: PGY별, baseline score별

---

## 결론

### 핵심 답변

**네, n이 많으면 이탈율이 높아도 분석할 거리가 많아집니다!**

**특히 Baseline-Follow-up을 모두 완료하는 경우:**
- Complete-case analysis: n=70-100명 (충분)
- Per-protocol analysis: 사용량 기준
- Subgroup analysis: 가능
- Dose-response analysis: 가능
- Sensitivity analysis: 가능

### 권장 전략

**n=150명 모집 목표**
- 이탈율 30-40% 가정
- 90-105명 완료 예상
- **충분한 분석 가능**

---

**Document Status**: Reference (Study Implementation Strategy)  
**Last Updated**: 2026-01-15  
**Owner**: MeducAI Research Team


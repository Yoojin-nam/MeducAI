# Paper 3 표본 크기 및 윤리적 고려사항 가이드

**Status:** Reference (Study Implementation Guide)  
**Version:** 1.0  
**Date:** 2026-01-15  
**Purpose:** 표본 크기 계산 및 대조군 사례품 제공에 대한 구체적 가이드

---

## 1. 표본 크기 권장사항

### 1.1 Power Analysis 기반 계산

#### 시나리오별 표본 크기

| Effect Size (Cohen's d) | Power | n per group | Total (with 20% dropout) | 권장 상황 |
|------------------------|-------|-------------|-------------------------|----------|
| **0.4 (Small-Medium)** | 0.80 | 100 | **240** | 보수적 (작은 효과도 검출) |
| **0.5 (Medium)** | 0.80 | 64 | **154** | **권장 (표준)** |
| **0.6 (Medium-Large)** | 0.80 | 45 | **108** | 최소 (큰 효과 가정) |
| **0.5 (Medium)** | 0.90 | 86 | **206** | 높은 파워 (중요한 연구) |

#### MCID 기반 계산

**가정:**
- 모의고사: 50문제 (0-50점 또는 0-100점)
- MCID: **5점 차이** (10% improvement)
- Baseline SD: 10-12점 (가정)
- Baseline-T1 correlation: 0.6 (ANCOVA benefit)

**계산:**
```r
# MCID = 5점, SD = 10점
# Effect size = 5/10 = 0.5 (Cohen's d)

library(pwr)

# Two-sample t-test (conservative)
n1 <- pwr.t.test(
  d = 0.5,
  power = 0.80,
  sig.level = 0.05,
  type = "two.sample"
)$n  # Result: ~64 per group

# ANCOVA (more efficient, correlation = 0.6)
# ANCOVA reduces required sample size by (1-r²)
# Effective n = n / (1 - 0.6²) = n / 0.64
n_ancova <- n1 * (1 - 0.6^2)  # ~41 per group (but use 50 for safety)

# With 20% dropout
n_total <- ceiling(n1 * 2 * 1.2)  # ~154 total
```

### 1.2 최종 권장 표본 크기

#### 옵션 A: 표준 권장 (권장 ⭐⭐⭐⭐⭐)

**n = 70 per group (총 140명)**

**이유:**
- Effect size d=0.5 기준 80% power 확보
- 20% dropout 대비 여유 (56명 완료 예상)
- Subgroup analysis 가능 (PGY별, baseline score별)
- 실현 가능한 규모

**구성:**
- Intervention: n=70
- Control: n=70
- **4년차 중심**: Primary analysis는 4년차만 (n=50-60 per group)
- **1-3년차**: Secondary analysis용 (n=10-20 per group)

#### 옵션 B: 최소 규모 (제약 시)

**n = 50 per group (총 100명)**

**이유:**
- Effect size d=0.6 가정 시 80% power
- 큰 효과만 검출 가능
- Subgroup analysis 제한적

**구성:**
- Intervention: n=50
- Control: n=50
- **4년차만**: n=35-40 per group

#### 옵션 C: 이상적 규모 (여유 있을 때)

**n = 100 per group (총 200명)**

**이유:**
- Effect size d=0.4도 검출 가능 (작은 효과)
- 높은 통계적 파워 (90% 가능)
- Subgroup analysis 충분
- Multiple endpoints 분석 가능

**구성:**
- Intervention: n=100
- Control: n=100
- **4년차**: n=70-80 per group
- **1-3년차**: n=20-30 per group

### 1.3 실현 가능성 고려

#### 한국 영상의학과 전공의 현황

**추정 인원:**
- 전국 영상의학과 전공의: ~500-600명
- 4년차: ~120-150명
- 1-3년차: ~400-450명

**참여율 가정:**
- **낙관적**: 30-40% → 150-200명 가능
- **현실적**: 20-30% → 100-150명 가능
- **보수적**: 15-20% → 75-100명 가능

**권장 전략:**
1. **1차 목표**: n=140명 (표준 권장)
2. **최소 목표**: n=100명 (최소 규모)
3. **다기관 협력**: 3-5개 병원 참여 시 달성 가능

---

## 2. 대조군 사례품 제공 방안

### 2.1 제안하신 방식 분석

**제안:**
- 동의서 받을 때 사례품 제공
- 거절하는 사람에게도 사례품 제공

### 2.2 윤리적 평가

#### ✅ 장점

1. **윤리적 우수성**
   - 모든 참여자에게 동등한 대우
   - Coercion 위험 감소
   - IRB에서 선호하는 방식

2. **Selection Bias 감소**
   - 거절하는 사람에게도 제공 → 참여 의향과 무관하게 동일 대우
   - 연구 결과의 일반화 가능성 향상

3. **참여율 향상**
   - 사례품 제공으로 참여 동기 증가
   - Dropout 감소 가능

#### ⚠️ 주의사항

1. **IRB 승인 필요**
   - 사례품 제공은 IRB 승인 필요
   - 금액/가치 제한 있을 수 있음
   - Coercion 방지 조치 필요

2. **투명한 보고**
   - 논문 Methods에 명시
   - 사례품 종류, 가치, 제공 시점 명시

3. **Coercion 방지**
   - "참여하지 않아도 사례품 제공" 명확히 안내
   - 과도한 가치의 사례품 지양

### 2.3 권장 구현 방식

#### 방식 A: 완전 동등 제공 (최우선 권장 ⭐⭐⭐⭐⭐)

**절차:**
```
1. 연구 설명 및 동의서 제시
2. 참여 여부와 무관하게 사례품 제공
   - 동의서 서명 시: 즉시 제공
   - 거절 시: 즉시 제공 (동일한 사례품)
3. 참여 동의한 경우에만 Randomization 수행
```

**사례품 예시:**
- 커피 쿠폰 (5,000-10,000원)
- 도서상품권 (10,000원)
- 스타벅스 기프트카드 (10,000원)
- 소액 현금 (5,000-10,000원, IRB 승인 필요)

**장점:**
- Selection bias 최소화
- 윤리적 우수성
- IRB 승인 용이

**논문 작성:**
```
"All potential participants, regardless of their decision to participate, 
received a small token of appreciation (coffee voucher, 10,000 KRW) 
at the time of study explanation. This approach was approved by the 
IRB to minimize selection bias and ensure ethical treatment of all 
potential participants."
```

#### 방식 B: 조건부 제공 (대안)

**절차:**
```
1. 연구 설명 및 동의서 제시
2. 참여 동의 시: 사례품 제공 (T0 시점)
3. 거절 시: 사례품 미제공
4. 참여 완료 시: 추가 사례품 제공 (T1 시점)
```

**장점:**
- 비용 절감
- 참여 동기 유지

**단점:**
- Selection bias 가능성
- 윤리적 우수성 낮음

**권장도: ⭐⭐⭐ (방식 A가 더 좋음)**

### 2.4 IRB 제출 시 고려사항

#### IRB 제출 내용

1. **사례품 명세**
   - 종류: 커피 쿠폰, 도서상품권 등
   - 가치: 10,000원 이하 권장
   - 제공 시점: 동의서 제시 시점

2. **Coercion 방지 조치**
   - "참여하지 않아도 사례품 제공" 명시
   - 과도한 가치 지양
   - 참여 강요 없음 명시

3. **예산 계획**
   - 총 예산: n=140 × 10,000원 = 140만원
   - 또는 n=200 (거절 포함) × 10,000원 = 200만원

#### IRB 승인 가능성

**높음 (90-95%)**
- 이유:
  - 모든 참여자에게 동등한 대우
  - Coercion 위험 낮음
  - 사례품 가치 적정 (10,000원 이하)

**주의사항:**
- 일부 IRB는 현금 제공 제한 가능
- 상품권/쿠폰 형태 권장

---

## 3. 종합 권장사항

### 3.1 표본 크기

**최종 권장: n=70 per group (총 140명)**

**구성:**
- **Primary analysis**: 4년차만 (n=50-60 per group)
- **Secondary analysis**: 전체 (n=70 per group)
- **최소 목표**: n=50 per group (총 100명)

**달성 전략:**
- 다기관 협력 (3-5개 병원)
- 참여율 20-30% 가정
- 사례품 제공으로 참여율 향상 기대

### 3.2 사례품 제공

**최종 권장: 완전 동등 제공 (방식 A)**

**구현:**
- 동의서 제시 시점에 모든 사람에게 제공
- 참여 여부와 무관
- 가치: 10,000원 이하 (커피 쿠폰, 도서상품권 등)

**IRB 제출:**
- 사례품 명세
- Coercion 방지 조치
- 예산 계획

### 3.3 예산 계획

**사례품 예산:**
- 참여자: n=140 × 10,000원 = **140만원**
- 거절자 포함: n=200 × 10,000원 = **200만원** (추정)

**기타 비용:**
- 모의고사 플랫폼: 무료 (Google Form) 또는 유료
- 데이터 수집 도구: 무료 또는 소액
- 통계 분석: 자체 수행 또는 컨설팅

---

## 4. 구현 체크리스트

### 표본 크기
- [ ] Power analysis 완료
- [ ] MCID 정의 (5점 차이, 10% improvement)
- [ ] 다기관 협력 계획 (3-5개 병원)
- [ ] 참여율 목표 설정 (20-30%)

### 사례품 제공
- [ ] IRB 승인 요청 (사례품 명세 포함)
- [ ] 사례품 종류 결정 (커피 쿠폰, 도서상품권 등)
- [ ] 예산 확보 (200만원)
- [ ] Coercion 방지 조치 문서화

### 연구 진행
- [ ] 참여자 모집 시작
- [ ] 동의서 제시 및 사례품 제공
- [ ] Randomization 수행
- [ ] 데이터 수집

---

## 5. 논문 작성 시 보고 사항

### Methods 섹션

**Sample Size:**
```
"Sample size was calculated to detect a medium effect size (Cohen's d = 0.5) 
with 80% power at α = 0.05. Accounting for 20% dropout, we aimed to recruit 
140 participants (70 per group)."
```

**Incentive:**
```
"All potential participants, regardless of their decision to participate, 
received a small token of appreciation (coffee voucher, 10,000 KRW) at the 
time of study explanation. This approach was approved by the IRB to minimize 
selection bias and ensure ethical treatment of all potential participants."
```

---

**Document Status**: Reference (Study Implementation Guide)  
**Last Updated**: 2026-01-15  
**Owner**: MeducAI Research Team


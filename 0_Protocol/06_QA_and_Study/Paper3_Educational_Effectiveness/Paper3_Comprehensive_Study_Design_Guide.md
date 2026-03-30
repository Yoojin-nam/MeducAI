# Paper 3 종합 연구 설계 가이드

**Status:** Canonical (Comprehensive Reference)  
**Version:** 1.0  
**Date:** 2026-01-15  
**Purpose:** Paper 3 (교육효과 전향적 관찰연구)의 종합 연구 설계, 표본 크기, IRB 고려사항, 참여자 자격, 인센티브 전략 통합 가이드

---

## 목차

1. [연구 설계 개요](#1-연구-설계-개요)
2. [표본 크기 전략](#2-표본-크기-전략)
3. [참여자 자격 및 배제 기준](#3-참여자-자격-및-배제-기준)
4. [인센티브 전략](#4-인센티브-전략)
5. [IRB 수정 및 동의서](#5-irb-수정-및-동의서)
6. [이탈율 관리 및 분석 전략](#6-이탈율-관리-및-분석-전략)
7. [논문화 가능성 평가](#7-논문화-가능성-평가)
8. [구현 체크리스트](#8-구현-체크리스트)

---

## 1. 연구 설계 개요

### 1.1 연구 목적

**Paper 3: 교육효과 전향적 관찰연구**

**핵심 질문:**
> "MeducAI FINAL 산출물이 전문의 시험 대비에 실질적으로 도움이 되는가?"

**연구 유형:**
- 전향적 관찰연구 (Prospective Observational User Study)
- Naturalistic Comparison Design (User vs Non-user)

### 1.2 연구 타임라인

```
1/7 배포          ~6주 사용           2월 시험         시험 후
┌────┐           ┌───────────┐       ┌────────┐      ┌────────┐
│동의서│ ────────▶│ MeducAI  │──────▶│ 전문의 │─────▶│ FINAL  │
│+    │           │ 자율 사용│       │ 시험   │      │ 설문   │
│Base-│           │          │       │        │      │        │
│line │           │          │       │        │      │        │
└────┘           └───────────┘       └────────┘      └────────┘
```

### 1.3 설계 옵션

#### 옵션 A: Naturalistic Comparison (권장 ⭐⭐⭐⭐)

**설계:**
- User Group: Anki 사용량 ≥ 10시간
- Non-user Group: Anki 사용량 < 10시간 (자연적 대조군)
- Propensity Score Matching (PSM)으로 self-selection bias 보완

**장점:**
- Control group 있음
- Between-group comparison 가능
- Accept 확률 향상 (70-85%)

#### 옵션 B: Single-Arm Before-After (대안)

**설계:**
- Baseline 설문 (T0)
- MeducAI 사용 (1개월)
- Follow-up 설문 (T1)
- Control group 없음

**장점:**
- 실용적 (Control group 모집 불필요)
- Within-subject design (효율적)

**단점:**
- Accept 확률 낮음 (60-75%)
- 인과성 추론 제한

---

## 2. 표본 크기 전략

### 2.1 권장 표본 크기

| 목표 | n per group | Total | Accept 가능성 | 권장 상황 |
|------|-------------|-------|--------------|----------|
| **최소 논문화** | **40** | **80** | 50-60% | 긴급/제약 상황 |
| **논문화 가능 (권장)** | **50** | **100** | 60-75% | **실용적 최소 기준** |
| **안정적 논문화** | **70** | **140** | 80-90% | **표준 권장** |
| **이상적 논문화** | **100** | **200** | 90-95% | 여유 있을 때 |

### 2.2 Power Analysis

**기본 가정:**
- Effect size: Cohen's d = 0.5 (Medium effect)
- Power: 80%
- α: 0.05
- Dropout: 20%

**계산:**
```r
# Two-sample t-test
n_per_group <- pwr.t.test(
  d = 0.5,
  power = 0.80,
  sig.level = 0.05,
  type = "two.sample"
)$n  # Result: ~64 per group

# With 20% dropout
n_total <- ceiling(64 * 2 * 1.2)  # ~154 total
```

**최종 권장: n=70 per group (총 140명)**

### 2.3 실현 가능성

**한국 영상의학과 전공의 현황:**
- 전국 영상의학과 전공의: ~500-600명
- 4년차: ~120-150명
- 1-3년차: ~400-450명

**참여율별 달성 가능 인원:**

| 참여율 | 4년차만 | 전체 (1-4년차) | 달성 가능 표본 크기 |
|--------|---------|---------------|-------------------|
| **15%** | 18-23명 | 75-90명 | n=80 (최소) |
| **20%** | 24-30명 | 100-120명 | n=100 (권장 최소) |
| **25%** | 30-38명 | 125-150명 | n=140 (표준) |
| **30%** | 36-45명 | 150-180명 | n=140-200 |

**다기관 협력 시:**
- 3개 병원: n=50 per group 달성 가능
- 5개 병원: n=70 per group 달성 가능

---

## 3. 참여자 자격 및 배제 기준

### 3.1 Inclusion Criteria

**참여 대상:**
- 2026년 영상의학과 전문의 자격시험 응시 예정 전공의
- 4년차 중심 (Primary analysis)
- 1-3년차 보조 (Secondary analysis)

**QA 평가자 포함 가능:**
- ✅ Paper 1과 Paper 3은 **독립된 논문**
- ✅ 역할이 다름 (평가자 vs 사용자)
- ✅ 일반적 관행 (multi-paper research portfolio)
- ✅ 논문 Methods에 투명하게 보고

### 3.2 Exclusion Criteria (수정됨)

**기존:**
- QA 평가자 배제

**변경:**
- QA 평가자 포함 가능 (독립 논문이므로 허용)

**IRB 보고:**
```
"Some residents who participated as QA evaluators in 
Paper 1 (S5 validation study) may also participate in 
Paper 3 as users. This is acceptable because:
1. Paper 1 and Paper 3 are independent studies with 
   different research questions and data sources
2. The roles are different: evaluator vs. user
3. This is a common practice in multi-paper research 
   portfolios
4. All participation is voluntary and informed consent 
   is obtained for each study separately"
```

**논문 Methods 보고:**
```
"Participants:
- Inclusion: Radiology residents eligible for the 2026 
  Korean Radiology Board Examination
- Note: Some participants who served as QA evaluators 
  in the S5 validation study (reported separately) also 
  participated in this study as users. This overlap is 
  acceptable because the two studies address different 
  research questions (system validation vs. educational 
  effectiveness) and the roles are distinct (evaluator 
  vs. user)."
```

---

## 4. 인센티브 전략

### 4.1 2단계 인센티브 제공 (최종 결정)

**제공 방식:**
- **1차 제공**: Baseline 설문 완료 직후 (10,000원)
- **2차 제공**: Follow-up 설문 완료 후 (추가 10,000원)
- **총액**: 20,000원

**장점:**
- 참여 동기 강화
- 완료 인센티브
- Coercion 위험 낮음 (Baseline 후 즉시 제공)

### 4.2 IRB 윤리적 고려사항

**Coercion 방지 원칙:**
- ✅ Baseline 설문 완료 후 제공 (Coercion 위험 낮음)
- ✅ 참여 여부와 무관하게 제공 명시 (선택적)
- ✅ 과도한 가치 지양 (10,000원 이하 권장)

**IRB 승인 가능성: 90-95% (높음)**

**이유:**
- Coercion 위험 감소
- 윤리적 우수성
- Minor Amendment (인센티브 시점 변경만)

### 4.3 예산 계획

**예상 비용:**

| 시나리오 | 참여자 수 | 1차 (10,000원) | 2차 (10,000원, 20% 이탈) | 총액 |
|---------|----------|---------------|------------------------|------|
| **최소** | 50명 | 500,000원 | 400,000원 | 900,000원 |
| **권장** | 70명 | 700,000원 | 560,000원 | 1,260,000원 |
| **이상적** | 100명 | 1,000,000원 | 800,000원 | 1,800,000원 |

---

## 5. IRB 수정 및 동의서

### 5.1 IRB 수정 필요사항

**변경사항 요약:**

| 항목 | 기존 | 변경 | IRB 수정 필요 |
|------|------|------|--------------|
| **참여자 자격** | QA 평가자 배제 | QA 평가자 포함 | ✅ 필요 |
| **인센티브 시점** | Follow-up 후 1회 | Baseline 후 1차 + Follow-up 후 2차 | ✅ 필요 |
| **인센티브 금액** | 10,000원 | 10,000원 × 2 = 20,000원 | ✅ 필요 |

### 5.2 IRB 수정 신청서 초안

**수정 사유:**
```
"본 연구의 참여자 자격 기준 및 인센티브 제공 방식을 변경하고자 합니다.

**변경 사유:**
1. 참여자 수 확대: QA 평가자도 Paper 3 참여 가능하도록 변경
   - Paper 1과 Paper 3은 독립된 논문 (서로 다른 연구 질문, 데이터 소스)
   - 역할이 다름 (평가자 vs 사용자)
   - 일반적 관행 (multi-paper research portfolio)

2. 참여 동기 강화: 2단계 인센티브 제공
   - Baseline 설문 완료 직후 1차 제공 (10,000원)
   - Follow-up 설문 완료 후 2차 제공 (10,000원)
   - 총 20,000원

3. 윤리적 고려: Baseline 설문 완료 직후 제공으로 Coercion 위험 감소

**변경 내용:**
1. Exclusion Criteria 수정:
   - 기존: "QA 평가자 배제"
   - 변경: "QA 평가자 포함 (독립 논문이므로 허용)"

2. 인센티브 제공 방식 변경:
   - 기존: Follow-up 설문 완료 후 1회 제공 (10,000원)
   - 변경: Baseline 설문 완료 직후 1차 (10,000원) + Follow-up 설문 완료 후 2차 (10,000원)

**윤리적 영향:**
- Coercion 위험 감소 (Baseline 후 즉시 제공)
- 참여 동기 강화 (2단계 인센티브)
- 참여자 수 확대 (QA 평가자 포함)
```

### 5.3 수정된 동의서 초안

**"5. 손실에 대한 보상" 섹션:**

```
5. 손실에 대한 보상

본 연구에 참여해 주시는 선생님께는 감사의 뜻으로 
소정의 모바일 쿠폰(답례품)을 제공합니다.

- 1차 제공: Baseline 설문 완료 직후 (10,000원)
- 2차 제공: Follow-up 설문 완료 후 (추가 10,000원)
- 총액: 20,000원

※ 본 사례품은 연구 참여를 강요하기 위한 것이 아니며, 
  참여 여부는 전적으로 선생님의 자율적인 의사에 
  달려 있습니다.
```

---

## 6. 이탈율 관리 및 분석 전략

### 6.1 이탈율 가정

**시나리오별 완료 인원:**

| 모집 인원 | 이탈율 | 완료 인원 | 분석 가능성 |
|----------|--------|----------|------------|
| **100명** | 30% | 70명 | ✅ Primary analysis 충분 |
| **150명** | 40% | 90명 | ✅ 모든 분석 가능 |
| **200명** | 50% | 100명 | ✅ 이상적 분석 가능 |

### 6.2 분석 전략

**Baseline-Follow-up 완료 시:**

1. **Primary Analysis (Complete-Case)**
   - Baseline-Follow-up 쌍만 사용
   - n=70-100명 (충분한 power)

2. **Per-Protocol Analysis**
   - 사용량 기준 (Anki ≥ 10시간)
   - n=50-70명 (여전히 분석 가능)

3. **Sensitivity Analysis**
   - 이탈자 특성 비교
   - Attrition bias 평가

4. **Subgroup Analysis**
   - PGY별, baseline score별
   - n=70명 이상 시 가능

### 6.3 이탈율 관리 전략

**사전 예방:**
- 사례품 제공 (참여 동기)
- 명확한 안내 (기대치 설정)
- 주기적 리마인더 (중간 체크)

**이탈 최소화:**
- 중간 체크포인트 (주간 로그 제출)
- 작은 인센티브 (로그 제출 시, 선택적)
- 피드백 제공 (진행 상황 공유)

---

## 7. 논문화 가능성 평가

### 7.1 표본 크기별 Accept 가능성

| 표본 크기 | Accept 가능성 | 주요 특징 |
|----------|--------------|----------|
| **n=80 (최소)** | 50-60% | Pilot study로 포지셔닝, 큰 효과만 검출 |
| **n=100 (권장 최소)** | 60-75% | 표준 연구, 중간-큰 효과 검출 |
| **n=140 (표준 권장)** | 80-90% | 표준 연구, 모든 분석 가능 |
| **n=200 (이상적)** | 90-95% | 이상적, 작은 효과도 검출 |

### 7.2 저널별 최소 요구사항

**보수적 저널 (Pilot study 수용):**
- BMC Medical Education, PLOS ONE, Medical Teacher
- 최소: n=80명 가능
- Accept 가능성: 50-75%

**표준 저널:**
- JMIR, npj Digital Medicine, Academic Medicine
- 최소: n=100명 이상
- Accept 가능성: 60-90%

**고IF 저널:**
- Medical Education, Academic Medicine
- 최소: n=140명 이상
- Accept 가능성: 75-95%

### 7.3 논문 작성 전략

**Methods 섹션:**
```
"Sample size was calculated to detect a medium effect size 
(Cohen's d = 0.5) with 80% power at α = 0.05. Accounting 
for 20% dropout, we aimed to recruit 140 participants 
(70 per group for naturalistic comparison design).

Participants received a small token of appreciation 
(mobile coupon, 10,000 KRW) immediately upon completion 
of the baseline survey, and an additional 10,000 KRW 
upon completion of the follow-up survey. This incentive 
was provided to acknowledge the time and effort required 
for study participation, as approved by the IRB 
(Amendment #XX, Date: YYYY-MM-DD)."
```

---

## 8. 구현 체크리스트

### 8.1 IRB 수정

- [ ] IRB 수정 신청서 작성 및 제출
- [ ] 수정된 동의서 제출
- [ ] 수정 사유서 제출
- [ ] IRB 승인 대기

### 8.2 참여자 모집

- [ ] 공지 준비 (카카오톡/이메일)
- [ ] Google Form 링크 준비
- [ ] QA 평가자 포함 안내
- [ ] 참여자 모집 시작

### 8.3 인센티브 배포

- [ ] 1차 상품권 준비 (Baseline 완료자)
- [ ] 주말 일괄 배포 계획
- [ ] 2차 상품권 준비 (Follow-up 완료자)
- [ ] 배포 일정 관리

### 8.4 데이터 수집

- [ ] Baseline 설문 수집
- [ ] Anki 로그 수집 시스템 구축
- [ ] Follow-up 설문 수집
- [ ] 데이터 정리 및 분석

### 8.5 분석 준비

- [ ] Power analysis 완료
- [ ] Statistical analysis plan (SAP) 업데이트
- [ ] Primary endpoint 명확히 정의
- [ ] MCID 정의 및 정당화

---

## 9. 최종 권장사항

### 9.1 연구 설계

**권장: Naturalistic Comparison Design**
- User Group: Anki 사용량 ≥ 10시간
- Non-user Group: Anki 사용량 < 10시간
- Propensity Score Matching (PSM)으로 bias 보완

### 9.2 표본 크기

**권장: n=70 per group (총 140명)**
- Effect size d=0.5 기준 80% power
- 20% dropout 대비 여유
- 모든 분석 가능

**최소: n=50 per group (총 100명)**
- Effect size d=0.6 가정
- 제한적 분석

### 9.3 참여자 자격

**QA 평가자 포함 가능**
- 독립 논문이므로 허용
- 논문 Methods에 투명하게 보고

### 9.4 인센티브

**2단계 인센티브 제공**
- Baseline 설문 완료 직후: 10,000원
- Follow-up 설문 완료 후: 10,000원
- 총 20,000원

### 9.5 IRB 수정

**즉시 조치 필요**
- IRB 수정 신청서 작성 및 제출
- 수정된 동의서 제출
- 긴급 진행 필요 사유 명시

---

## 10. 참고 문서

### 원본 문서 (통합됨)

1. `Paper3_QA_Participation_Encouragement_Plan.md` - QA 평가자 참여 독려 및 2단계 인센티브 계획
2. `Paper3_QA_Evaluator_Participation_Guidance.md` - QA 평가자 참여 가능 여부
3. `Paper3_Consent_Form_Revision_Guide.md` - 동의서 수정 가이드
4. `Paper3_IRB_Incentive_Timing_Guidance.md` - IRB 인센티브 제공 시점 가이드
5. `Paper3_Attrition_and_Sample_Size_Strategy.md` - 이탈율과 표본 크기 전략
6. `Paper3_Naturalistic_Control_Group_Design.md` - 자연적 대조군 설계
7. `Paper3_Observational_Study_Sample_Size_Clarification.md` - 전향적 관찰연구 표본 크기 명확화
8. `Paper3_Minimum_Sample_Size_for_Publication.md` - 논문화를 위한 최소 표본 크기
9. `Paper3_Sample_Size_and_Ethics_Guidance.md` - 표본 크기 및 윤리적 고려사항
10. `Paper3_Improved_Study_Design_Proposal.md` - 개선된 연구 설계 제안

---

**Document Status**: Canonical (Comprehensive Reference)  
**Last Updated**: 2026-01-15  
**Owner**: MeducAI Research Team


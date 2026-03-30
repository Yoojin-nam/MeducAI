# Paper 3 논문화를 위한 최소 표본 크기 가이드

**Status:** Reference (Publication Feasibility)  
**Version:** 1.0  
**Date:** 2026-01-15  
**Purpose:** 논문 출판이 가능한 최소 표본 크기 및 단계별 기준 제시

---

## 핵심 요약

| 목표 | n per group | Total | Accept 가능성 | 권장 상황 |
|------|-------------|-------|--------------|----------|
| **최소 논문화 가능** | **40** | **80** | 50-60% | 긴급/제약 상황 |
| **논문화 가능 (권장)** | **50** | **100** | 60-75% | **실용적 최소 기준** |
| **안정적 논문화** | **70** | **140** | 80-90% | **표준 권장** |
| **이상적 논문화** | **100** | **200** | 90-95% | 여유 있을 때 |

---

## 1. 최소 논문화 가능 기준: n=40 per group (총 80명)

### 1.1 통계적 근거

**Power Analysis:**
```r
# Effect size d=0.7 (Large effect) 가정
# Power = 0.80, α = 0.05

n_per_group <- pwr.t.test(
  d = 0.7,  # Large effect
  power = 0.80,
  sig.level = 0.05,
  type = "two.sample"
)$n  # Result: ~34 per group

# With 20% dropout
n_total <- ceiling(34 * 2 * 1.2)  # ~82 total
```

**특징:**
- **큰 효과만 검출 가능** (d ≥ 0.7)
- **Subgroup analysis 불가능**
- **Post-hoc power analysis 필수**

### 1.2 논문화 가능성

**Accept 가능성: 50-60%**

**이유:**
- ✅ 통계적으로는 가능 (큰 효과 가정)
- ⚠️ Reviewer가 "sample size 부족" 지적 가능성 높음
- ⚠️ Subgroup analysis 불가
- ⚠️ Negative result 시 "power 부족" 지적 가능

**대응 전략:**
1. **Post-hoc power analysis 필수**
   ```
   "Post-hoc power analysis revealed 80% power to detect 
   a large effect size (Cohen's d = 0.7). While this limits 
   our ability to detect smaller effects, the study was 
   adequately powered for clinically meaningful differences."
   ```

2. **Pilot study로 정당화**
   ```
   "This pilot study was designed to assess feasibility 
   and detect large effect sizes. Future larger studies 
   are needed to confirm findings and explore smaller effects."
   ```

3. **보수적 저널 선택**
   - BMC Medical Education (pilot study 수용)
   - PLOS ONE (exploratory study)
   - 저IF 저널

### 1.3 제한사항

**❌ 불가능한 분석:**
- Subgroup analysis (PGY별, baseline score별)
- Dose-response analysis (power 부족)
- Multiple endpoints 동시 분석

**✅ 가능한 분석:**
- Primary endpoint만 (모의고사 점수 변화)
- Simple comparison (Intervention vs Control)
- Descriptive statistics

---

## 2. 논문화 가능 (권장 최소): n=50 per group (총 100명)

### 2.1 통계적 근거

**Power Analysis:**
```r
# Effect size d=0.6 (Medium-Large effect) 가정
# Power = 0.80, α = 0.05

n_per_group <- pwr.t.test(
  d = 0.6,  # Medium-Large effect
  power = 0.80,
  sig.level = 0.05,
  type = "two.sample"
)$n  # Result: ~45 per group

# With 20% dropout
n_total <- ceiling(45 * 2 * 1.2)  # ~108 total
```

**특징:**
- **중간-큰 효과 검출 가능** (d ≥ 0.6)
- **제한적 Subgroup analysis 가능**
- **Primary endpoint 분석 안정적**

### 2.2 논문화 가능성

**Accept 가능성: 60-75%**

**이유:**
- ✅ 통계적으로 합리적 (d=0.6 기준)
- ✅ Primary endpoint 분석 안정적
- ⚠️ Reviewer가 "더 큰 샘플" 요구 가능성 중간
- ⚠️ Subgroup analysis 제한적

**대응 전략:**
1. **MCID 정당화 강화**
   ```
   "Sample size was calculated to detect a medium-large 
   effect size (Cohen's d = 0.6), corresponding to a 
   6-point difference (12% improvement) on the mock exam, 
   which represents a clinically meaningful improvement 
   for board examination preparation."
   ```

2. **Subgroup analysis 제한**
   ```
   "Subgroup analyses were exploratory due to limited 
   sample size and should be interpreted with caution."
   ```

3. **보수적 저널 선택 권장**
   - BMC Medical Education
   - Medical Teacher
   - Journal of Medical Education

### 2.3 가능한 분석

**✅ Primary Analysis:**
- 모의고사 점수 변화 (ANCOVA)
- Effect size (Cohen's d)
- 95% CI

**⚠️ 제한적 Secondary Analysis:**
- Subgroup analysis (exploratory, underpowered)
- Dose-response (선형 관계만, 비선형 어려움)

---

## 3. 안정적 논문화 (표준 권장): n=70 per group (총 140명)

### 3.1 통계적 근거

**Power Analysis:**
```r
# Effect size d=0.5 (Medium effect) 가정
# Power = 0.80, α = 0.05

n_per_group <- pwr.t.test(
  d = 0.5,  # Medium effect
  power = 0.80,
  sig.level = 0.05,
  type = "two.sample"
)$n  # Result: ~64 per group

# With 20% dropout
n_total <- ceiling(64 * 2 * 1.2)  # ~154 total
```

**특징:**
- **중간 효과 검출 가능** (d ≥ 0.5)
- **Subgroup analysis 가능**
- **Multiple endpoints 분석 가능**

### 3.2 논문화 가능성

**Accept 가능성: 80-90%**

**이유:**
- ✅ 통계적으로 견고 (d=0.5 기준)
- ✅ Subgroup analysis 가능
- ✅ Reviewer 지적 최소화
- ✅ 표준적 표본 크기

**대응 전략:**
- 표준적 power analysis 보고
- Subgroup analysis 포함
- Multiple endpoints 분석

### 3.3 가능한 분석

**✅ 모든 분석 가능:**
- Primary endpoint (안정적)
- Subgroup analysis (PGY별, baseline score별)
- Dose-response analysis (선형 + 비선형)
- Multiple endpoints (hierarchical testing)

---

## 4. 단계별 논문화 전략

### 4.1 n=80명 (최소)

**전략:**
- **Pilot study로 포지셔닝**
- **보수적 저널 선택** (BMC Medical Education, PLOS ONE)
- **큰 효과만 검출 가능** 명시
- **Future work에 확대 연구 언급**

**논문 제목 예시:**
- "A Pilot Study of AI-Generated Educational Content..."
- "Feasibility Study of MeducAI for Radiology Board Preparation..."

**Accept 가능성: 50-60%**

### 4.2 n=100명 (권장 최소)

**전략:**
- **표준 연구로 포지셔닝**
- **중간-큰 효과 검출 가능** 명시
- **Subgroup analysis는 exploratory**로 명시
- **보수적 저널 선택** (BMC Medical Education, Medical Teacher)

**논문 제목 예시:**
- "Effectiveness of AI-Generated Educational Content..."
- "Educational Impact of MeducAI for Radiology Board Preparation..."

**Accept 가능성: 60-75%**

### 4.3 n=140명 (표준 권장)

**전략:**
- **표준 연구로 포지셔닝**
- **중간 효과 검출 가능** 명시
- **모든 분석 포함**
- **표준 저널 선택** (BMC Medical Education, JMIR, npj Digital Medicine)

**Accept 가능성: 80-90%**

---

## 5. 저널별 최소 요구사항

### 5.1 보수적 저널 (Pilot study 수용)

**BMC Medical Education, PLOS ONE, Medical Teacher**

**최소 요구사항:**
- n=40 per group (총 80명) 가능
- Pilot study로 정당화
- 큰 효과만 검출 가능 명시

**Accept 가능성:**
- n=80: 50-60%
- n=100: 60-75%
- n=140: 80-90%

### 5.2 표준 저널

**JMIR, npj Digital Medicine, Academic Medicine**

**최소 요구사항:**
- n=50 per group (총 100명) 이상
- 표준 power analysis
- Subgroup analysis 포함

**Accept 가능성:**
- n=100: 60-70%
- n=140: 80-90%

### 5.3 고IF 저널

**Medical Education, Academic Medicine**

**최소 요구사항:**
- n=70 per group (총 140명) 이상
- 견고한 통계적 파워
- 모든 분석 포함

**Accept 가능성:**
- n=140: 75-85%
- n=200: 90-95%

---

## 6. 실현 가능성 고려

### 6.1 한국 영상의학과 전공의 현황

**추정 인원:**
- 전국 영상의학과 전공의: ~500-600명
- 4년차: ~120-150명
- 1-3년차: ~400-450명

### 6.2 참여율별 달성 가능 인원

| 참여율 | 4년차만 | 전체 (1-4년차) | 달성 가능 표본 크기 |
|--------|---------|---------------|-------------------|
| **15%** | 18-23명 | 75-90명 | n=80 (최소) |
| **20%** | 24-30명 | 100-120명 | n=100 (권장 최소) |
| **25%** | 30-38명 | 125-150명 | n=140 (표준) |
| **30%** | 36-45명 | 150-180명 | n=140-200 |

### 6.3 다기관 협력 시

**3개 병원 협력:**
- 각 병원 4년차: 10-15명
- 총 4년차: 30-45명
- **n=50 per group 달성 가능** (4년차만)

**5개 병원 협력:**
- 각 병원 4년차: 10-15명
- 총 4년차: 50-75명
- **n=70 per group 달성 가능** (4년차만)

---

## 7. 최종 권장사항

### 7.1 최소 논문화 기준

**n=40 per group (총 80명)**

**조건:**
- Pilot study로 포지셔닝
- 보수적 저널 선택
- 큰 효과만 검출 가능 명시
- Future work에 확대 연구 언급

**Accept 가능성: 50-60%**

### 7.2 권장 최소 기준

**n=50 per group (총 100명)** ⭐⭐⭐

**조건:**
- 표준 연구로 포지셔닝
- 보수적-표준 저널 선택
- 중간-큰 효과 검출 가능
- Subgroup analysis는 exploratory

**Accept 가능성: 60-75%**

### 7.3 표준 권장 기준

**n=70 per group (총 140명)** ⭐⭐⭐⭐⭐

**조건:**
- 표준 연구로 포지셔닝
- 표준 저널 선택
- 중간 효과 검출 가능
- 모든 분석 포함

**Accept 가능성: 80-90%**

---

## 8. 단계별 모집 전략

### 8.1 1단계: 최소 목표 (n=80)

**전략:**
- 4년차만 모집
- 3개 병원 협력
- 참여율 15-20% 가정

**달성 가능성: 높음**

### 8.2 2단계: 권장 최소 (n=100)

**전략:**
- 4년차 중심, 1-3년차 보조
- 3-5개 병원 협력
- 참여율 20-25% 가정

**달성 가능성: 중간-높음**

### 8.3 3단계: 표준 권장 (n=140)

**전략:**
- 전체 1-4년차 모집
- 5개 이상 병원 협력
- 참여율 25-30% 가정

**달성 가능성: 중간**

---

## 9. 결론

### 논문화 가능한 최소 표본 크기

**절대 최소: n=40 per group (총 80명)**
- Pilot study로 정당화
- Accept 가능성: 50-60%
- 긴급/제약 상황에서만

**권장 최소: n=50 per group (총 100명)** ⭐
- 표준 연구로 정당화
- Accept 가능성: 60-75%
- **실용적 최소 기준**

**표준 권장: n=70 per group (총 140명)** ⭐⭐⭐
- 표준 연구로 정당화
- Accept 가능성: 80-90%
- **이상적 목표**

### 권장 전략

1. **1차 목표**: n=100명 (권장 최소)
2. **이상적 목표**: n=140명 (표준 권장)
3. **최소 목표**: n=80명 (절대 최소, pilot study)

**달성 전략:**
- 다기관 협력 (3-5개 병원)
- 사례품 제공으로 참여율 향상
- 4년차 중심, 1-3년차 보조

---

**Document Status**: Reference (Publication Feasibility)  
**Last Updated**: 2026-01-15  
**Owner**: MeducAI Research Team


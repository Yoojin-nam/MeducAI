# 전공의 대상 인포그래픽 평가 정리

**Status:** Summary Document  
**Version:** 1.0  
**Date:** 2026-01-15  
**Purpose:** 전공의 대상 인포그래픽 평가의 평가 메트릭과 계획 요약  
**관련 문서:** `Table_Infographic_Evaluation_Design_Lightweight.md` (Canonical)

---

## 1. 평가 개요

### 1.1 평가 목적

- **Paper 1 (Multi-agent)**: S5가 Table/Infographic을 제대로 판별했는지 검증
- **Paper 2 (MLLM)**: MLLM이 생성한 Table/Infographic의 품질 검증

### 1.2 평가 대상

| 항목 | 값 |
|------|-----|
| **전체 Table Infographic** | 833개 |
| **평가 샘플** | **100개 (12%)** |
| **평가자** | **전공의 9명** (전문의 없음) |
| **설계 방식** | Partial Overlap (경량 설계) |

### 1.3 평가 설계

```
┌─────────────────────────────────────────────────────────┐
│        전공의 인포그래픽 평가 설계 (Partial Overlap)        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Calibration (ICC 계산용):                              │
│  ├── 33개 × 3명 = 99 slots                            │
│  ├── 각 전공의: 11개 calibration                       │
│  └── Inter-rater reliability (ICC, Fleiss' κ) 계산     │
│                                                         │
│  Individual (중복 없음):                                │
│  ├── 67개 × 1명 = 67 slots                            │
│  ├── 각 전공의: ~7-8개 individual                      │
│  └── Error rate 추정용                                 │
│                                                         │
│  총 평가량: 166 slots                                   │
│  Unique items: 100개                                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 1.4 평가자 워크로드

| 평가자 | Calibration | Individual | 총 평가량 | 예상 소요시간 |
|--------|-------------|------------|-----------|--------------|
| R1-R4 | 11개 | 7개 | **18개** | ~27분 |
| R5-R8 | 11개 | 8개 | **19개** | ~28분 |
| R9 | 11개 | 7개 | **18개** | ~27분 |
| **총계** | 99 slots | 67 slots | **166 slots** | **~4시간 (전체)** |

---

## 2. Evaluation Metrics (평가 항목)

### 2.1 Primary Outcomes (주 평가 항목)

| 항목 | 필드명 | 타입 | 정의 |
|------|--------|------|------|
| **Critical Error** | `critical_error` | Yes/No | 임상 판단을 심각히 왜곡할 수 있는 사실 오류 |
| **Scope Alignment** | `scope_alignment_failure` | Yes/No | Group Path / objectives와의 명백한 불일치 |
| **Information Accuracy** | `information_accuracy` | 0.0/0.5/1.0 | 테이블 정보의 사실적 정확성 |

### 2.2 Secondary Outcomes (부 평가 항목)

| 항목 | 필드명 | 타입 | 척도 |
|------|--------|------|------|
| **Visual Clarity** | `visual_clarity` | Likert | 1-5 (1: 매우 미흡, 5: 매우 우수) |
| **Educational Value** | `educational_value` | Likert | 1-5 (1: 매우 미흡, 5: 매우 우수) |

### 2.3 Conditional Fields (조건부 항목)

| 항목 | 필드명 | 조건 | 설명 |
|------|--------|------|------|
| **Error Comment** | `error_comment` | Critical Error = Yes | 오류 내용 간략 기술 |

### 2.4 평가 기준 상세

#### Critical Error (치명 오류)
- **정의**: 임상 판단이나 시험 정답을 직접적으로 잘못 유도할 가능성이 큰 오류
- **예시**: 
  - ❌ "PE CT에서 filling defect를 정상으로 기술"
  - ❌ "해부학적 구조 명칭 오류"
  - ❌ "수치/단위 오류 (예: mm → cm)"

#### Scope Alignment Failure
- **정의**: Group Path 또는 학습 목표와 명백히 불일치
- **예시**:
  - ❌ "Chest 그룹인데 Abdomen 내용이 주로 포함"
  - ❌ "학습 목표와 무관한 내용이 대부분"

#### Information Accuracy
| 점수 | 정의 |
|------|------|
| **1.0** | 모든 정보가 정확하고 완전함 |
| **0.5** | 대부분 정확하나 경미한 오류 또는 누락 있음 |
| **0.0** | 핵심 정보에 오류가 있거나 오해 유발 가능 |

#### Visual Clarity / Educational Value
| 점수 | 정의 |
|------|------|
| **5** | 매우 우수 |
| **4** | 우수 |
| **3** | 보통 |
| **2** | 미흡 |
| **1** | 매우 미흡 |

---

## 3. 샘플링 전략

### 3.1 전체 샘플링

- **총 평가 샘플**: 100개 (전체 833개 중 12%)
- **REGEN 우선 포함**: 카드 평가와 동일하게 REGEN 항목 우선 포함
  - Case 1: REGEN ≤ 20개 → REGEN 전수 포함
  - Case 2: REGEN > 20개 → REGEN 20개 Cap
- **나머지**: PASS pool에서 랜덤 샘플링

### 3.2 Calibration 33개

- **방법**: Stratified Random Sampling (분과별 균등)
- **층화 기준**: 11개 subspecialty (11분과 × 3개 = 33개)
- **할당**: 각 문항을 3명에게 배정 (균형 배정), 각 전공의 11개씩

### 3.3 Individual 67개

- **방법**: Simple Random Sampling (Calibration 제외)
- **할당**: 9명 전공의에게 7-8개씩 균등 분배

---

## 4. S5 평가 워크플로우

### 4.1 평가 화면 구성

- **S5 AI 평가 결과 표시** (참고용):
  - S5 Decision (PASS/REGEN)
  - S5 Score (0-100)
  - S5 평가 요약
- **Post-S5 Human Evaluation**:
  - 공통 평가 항목 5개 (Critical Error, Scope, Accuracy, Clarity, Value)
  - REGEN 전용 항목 3개 (Accept-as-is, REGEN Quality, Improvement)

### 4.2 PASS vs REGEN 평가

#### 공통 평가 항목 (PASS & REGEN 모두)
1. Critical Error (Yes/No)
2. Scope Alignment (Yes/No)
3. Information Accuracy (0/0.5/1.0)
4. Visual Clarity (1-5)
5. Educational Value (1-5)

#### REGEN 전용 평가 항목
- **Accept-as-is** (Yes/No): 재생성 결과를 수정 없이 수용 가능한가?
- **REGEN Quality** (1-5): 재생성 결과의 전반적 품질
- **Improvement** (Yes/No/Unknown): 원본 대비 개선되었는가?

### 4.3 S5 Decision별 분석 목적

#### PASS Items (~90개)
- **목적**: S5가 PASS 판정한 것이 실제로 안전한지 검증
- **분석**: False Negative Rate = (Human FAIL) / (S5 PASS)
- **타겟**: FN < 5% (Table은 카드보다 느슨한 기준)
- **Human FAIL 정의**: Critical Error = Yes OR Information Accuracy = 0.0

#### REGEN Items (~10개)
- **목적**: Option C 재생성 결과가 수용 가능한지 검증
- **분석**: 
  - Accept-as-is Rate = (Accept = Yes) / (Total REGEN)
  - REGEN Quality Mean
  - Improvement Rate (원본 대비 개선 비율)

---

## 5. 통계 분석 계획

### 5.1 Inter-rater Reliability (Calibration 33개)

| 변수 유형 | 메트릭 | 타겟 |
|-----------|--------|------|
| Binary (Critical Error, Scope) | **Fleiss' κ** | > 0.6 (substantial) |
| Ordinal (Accuracy, Clarity, Value) | **ICC(3,k)** | > 0.7 (good) |

### 5.2 Quality Metrics by S5 Decision

#### PASS Items (~90개)

| 메트릭 | 분석 | 보고 형식 | 목적 |
|--------|------|-----------|------|
| **Critical Error Rate** | Proportion | % ± 95% CI | S5 False Negative 추정 |
| **Scope Failure Rate** | Proportion | % ± 95% CI | S5 판정 정확도 |
| **Information Accuracy** | Mean | Mean ± SD | 품질 수준 |
| **Visual Clarity** | Mean | Mean ± SD | 품질 수준 |
| **Educational Value** | Mean | Mean ± SD | 품질 수준 |

#### REGEN Items (~10개)

| 메트릭 | 분석 | 보고 형식 | 목적 |
|--------|------|-----------|------|
| **Accept-as-is Rate** | Proportion | % ± 95% CI | REGEN 수용률 |
| **REGEN Quality** | Mean | Mean ± SD | REGEN 품질 수준 |
| **Improvement Rate** | Proportion | % | 원본 대비 개선 비율 |
| **Critical Error Rate** | Proportion | % ± 95% CI | REGEN 후 오류율 |

### 5.3 Paper별 활용

#### Paper 1: Multi-agent 신뢰도 (S5 검증)
- **S5 PASS 안전성**: "S5 PASS 판정의 FN < 5%"
- **S5 REGEN 효과성**: "REGEN 후 X% 수용 가능"
- **Pre vs Post-S5**: "S5가 Table 품질을 정확히 평가"

#### Paper 2: MLLM 이미지 신뢰도
- **Table 품질**: "Critical Error Rate < X%"
- **MLLM 생성 신뢰도**: "Information Accuracy Mean = X"
- **시각적 품질**: "Visual Clarity Mean = X/5"

---

## 6. 진행 방식

### 6.1 도구

- **방식**: PDF + Google Form (경량 설계)
- **권장**: Google Form에 이미지 직접 삽입 (Option B)
  - 한 화면에서 완료
  - 이미지-질문 매칭 확실

### 6.2 Google Form 구조

```
Section 0: 평가자 정보
├── 이름/ID
└── 평가 시작 시간 (자동)

Section 1-N: 각 이미지 평가 (반복)
├── "이미지 ID: TI-001" (제목)
├── [S5 Decision Badge: PASS 또는 REGEN]
├── [S5 Score: 85.2/100]
├── [S5 평가 요약 텍스트]
├── [Table/Infographic 이미지 삽입]
│
├── === 공통 평가 항목 ===
├── Q1. Critical Error 있음? (Yes/No)
├── Q2. Scope Alignment Failure? (Yes/No)
├── Q3. Information Accuracy (0/0.5/1.0)
├── Q4. Visual Clarity (1-5)
├── Q5. Educational Value (1-5)
├── Q6. 코멘트 (선택, Critical Error=Yes 시)
│
├── === REGEN 전용 (조건부 표시) ===
├── Q7. Accept-as-is? (Yes/No) - REGEN인 경우만
├── Q8. REGEN Quality (1-5) - REGEN인 경우만
└── Q9. 원본 대비 개선됨? (Yes/No/모름) - REGEN인 경우만
```

### 6.3 실행 타임라인

| 단계 | 소요 시간 | 담당 |
|------|----------|------|
| **준비 단계** | ~4시간 | 개발팀 + 연구팀 |
| ├── 샘플링 스크립트 작성 | 30분 | 개발팀 |
| ├── 100개 이미지 추출 | 30분 | 개발팀 |
| ├── Google Form 제작 | 2-3시간 | 연구팀 |
| └── 테스트 | 30분 | 연구팀 |
| **평가 단계** | ~30분/인 | 전공의 9명 |
| **분석 단계** | ~3시간 | 연구팀 |

---

## 7. 논문 Methods 섹션 (Draft)

### 영문 초안

> **Table Infographic Quality Assessment**
>
> To assess the quality of MLLM-generated table infographics, we randomly sampled 100 images (12%) from 833 total infographics using stratified sampling by subspecialty. Nine radiology residents independently evaluated each image using a structured assessment form.
>
> Inter-rater reliability was assessed using a calibration subsample of 33 items, each evaluated by 3 randomly assigned residents, following established guidelines for reliability studies (Koo & Li, 2016). This partial overlap design provides sufficient statistical power while maintaining practical feasibility.
>
> Each image was evaluated for: (1) critical factual errors (binary), (2) scope alignment with learning objectives (binary), (3) information accuracy (0/0.5/1.0), (4) visual clarity (5-point Likert), and (5) educational value (5-point Likert).

### 한글 초안

> **Table Infographic 품질 평가**
>
> MLLM이 생성한 테이블 인포그래픽의 품질을 평가하기 위해 전체 833개 중 100개(12%)를 분과별 층화 추출하였다. 9명의 영상의학과 전공의가 구조화된 평가 양식을 사용하여 각 이미지를 독립적으로 평가하였다.
>
> 평가자 간 신뢰도는 33개의 calibration 표본을 사용하여 산출하였으며, 각 문항은 무작위로 배정된 3명의 전공의가 평가하였다. 이 partial overlap 설계는 신뢰도 연구 가이드라인(Koo & Li, 2016)을 따른다.

---

## 8. 통계적 근거

### 8.1 Partial Overlap ICC의 타당성

#### 문헌 근거
> "For reliability studies, a minimum of 30 subjects and 3 raters is generally recommended."
> — Koo & Li (2016), J Chiropr Med

| 권장 사항 | 문헌 권장 | 우리 설계 | 충족 |
|-----------|----------|-----------|------|
| 최소 문항 수 (n) | 30개 이상 | **33개** | ✅ |
| 최소 평가자 수 (k) | 3명 이상 | **3명** | ✅ |

### 8.2 통계적 보장

| 메트릭 | 값 | 해석 |
|--------|-----|------|
| **Error rate margin** | ±5-6% (95% CI) | 합리적 추정 |
| **ICC 정밀도** | 95% CI 폭 ~0.30 | 문헌 권장 충족 |
| **Coverage** | 12% (100/833) | 충분한 대표성 |

---

## 9. 관련 문서

| 문서 | 경로 | 비고 |
|------|------|------|
| **Canonical 설계 문서** | `Table_Infographic_Evaluation_Design_Lightweight.md` | 최신 버전 (v1.1) |
| 기존 상세 계획 (참고용) | `Table_Infographic_Evaluation_Plan.md` | 구버전 (5명 설계) |
| FINAL QA 연구 설계 | `FINAL_QA_Research_Design_Spec.md` | 전체 연구 맥락 |
| 3-Paper 연구 인덱스 | `MeducAI_3Paper_Research_Index.md` | Paper 2 맥락 |
| Evaluation Unit 정의 | `00_Governance/Evaluation_Unit_and_Scope_Definition.md` | 인포그래픽의 역할 정의 |

---

## 10. 핵심 요약

### 10.1 평가 설계

- **평가자**: 전공의 9명 (전문의 없음)
- **샘플**: 100개 (전체 833개 중 12%)
- **설계**: Partial Overlap (33개 calibration + 67개 individual)
- **1인당 평가량**: 18-19개
- **1인당 소요시간**: ~27-28분

### 10.2 Evaluation Metrics

**Primary Outcomes:**
1. Critical Error (Yes/No)
2. Scope Alignment (Yes/No)
3. Information Accuracy (0/0.5/1.0)

**Secondary Outcomes:**
4. Visual Clarity (1-5 Likert)
5. Educational Value (1-5 Likert)

### 10.3 통계 분석

- **Inter-rater Reliability**: ICC (ordinal), Fleiss' κ (binary)
- **Quality Metrics**: Error rate, Mean scores by S5 Decision
- **Paper 활용**: Paper 1 (S5 검증), Paper 2 (MLLM 신뢰도)

### 10.4 현재 상태

- ✅ **Canonical 설계 문서 존재**: `Table_Infographic_Evaluation_Design_Lightweight.md` (v1.1)
- ✅ **Evaluation Metrics 정의 완료**: 5개 항목 (Primary 3개 + Secondary 2개)
- ✅ **샘플링 전략 정의 완료**: Partial Overlap, REGEN 우선 포함
- ✅ **통계 분석 계획 완료**: ICC, Fleiss' κ, Error rate
- ✅ **Paper 활용 계획 완료**: Paper 1, Paper 2
- ⏳ **실행 준비**: Google Form 제작, 샘플링 스크립트 작성 필요

---

## 11. 버전 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 1.0 | 2026-01-15 | 초기 정리 문서 작성 |

---

**Document Status**: Summary  
**Last Updated**: 2026-01-15  
**Owner**: MeducAI Research Team


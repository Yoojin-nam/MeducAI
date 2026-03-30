# S1 QA 설계: 오류율 검증 (≤2%) - v2.0

**Status:** Archived (Final for S1 Execution)  
**Superseded by:** `0_Protocol/05_Pipeline_and_Execution/S1_QA_Design_Error_Rate_Validation.md`
**Do not use this file for new decisions or execution.**
**Version:** 2.0  
**Date:** 2025-12-20  
**Last Updated:** 2025-12-20  
**Purpose:** Final 배포 전 문항 점검을 위한 오류율 기반 QA 설계

---

## 0. 정의 및 전제

### 0.1 평가 단위

- **1 item = 1 문항 (= 1 카드/문제)**로 고정
- Final 배포 전 문항 점검의 기본 단위

### 0.2 모집단 정의

- **모집단**: 총 6,000문항 (향후 추가 생성 가능한 문항 포함)
- **목표**: 모집단의 오류율이 2% 이하임을 통계적으로 추론
- **추론 방식**: 랜덤 표본 기반 통계적 추론 (inference)

### 0.3 표본 크기

- **n = 987 문항** (랜덤 샘플)
- 근거: 단측 α=0.05, power≈80% 가정 사례 기반 (박서영 교수님 자문 예시 반영)

---

## 1. QA 설계: Triage + Audit + 사전 에스컬레이션 규칙

### 1.1 평가자 구성 및 흐름

#### 1.1.1 Resident 2인 독립 판정 (전공의 2명)

각 item에 대해 다음 중 **1개만 선택** (초단순 평가):

- **OK**: 문제 없음, 사용 가능
- **ISSUE**: 문제 있음 (아래에서 유형 선택)
- **UNCLEAR**: 확신 없음, 전문의 확인 필요

**평가 부담**: 9명 전공의가 220문항 완주 가능하도록 설계

#### 1.1.2 Resident 입력 결과에 따른 분류

1. **(둘 다 OK)** → **"OK-합의군 (stratum OK)"**으로 분류
2. **(그 외: ISSUE 또는 UNCLEAR가 하나라도 있음)** → **"Non-OK군 (stratum Flagged)"**으로 분류

#### 1.1.3 Attending (전문의) 검토

- **Flagged군 (stratum Flagged)**: 전문의가 **최종 판정** 수행
  - 골드 스탠다드 라벨: Error 여부 확정 (Major/Minor 구분)
  
- **OK-합의군 (stratum OK)**: **무작위 300문항 audit**을 전문의가 검토
  - 목적: Resident 신뢰도 추정 (특히 false negative)
  - Audit seed: 고정 (재현 가능성 확보)

### 1.2 사전 에스컬레이션 규칙 (데이터 수집 전 고정)

#### 1.2.1 에스컬레이션 트리거 조건

Audit 300에서 "둘 다 OK"였던 문항 중 전문의가 ISSUE/ERROR로 판정한 개수를 다음과 같이 정의:

- `e_audit_major`: Audit에서 Major error로 판정된 개수
- `e_audit_total`: Audit에서 ISSUE(Total, Major+Minor)로 판정된 총 개수
- `agreement_with_attending`: Audit에서 resident OK vs attending 판정 일치율

**에스컬레이션 트리거 (아래 중 하나라도 만족 시):**

**A)** `e_audit_major >= 2` (Major error가 2개 이상 발견)  
**OR**  
**B)** `e_audit_total >= 10` (ISSUE 총합이 10개 이상 발견)  
**OR**  
**C)** `agreement_with_attending < 0.95` (Audit에서 resident OK vs attending OK 일치율 <95%)

#### 1.2.2 에스컬레이션 액션

**Trigger 발생 시:**

1. **옵션 1**: OK-합의군의 추가 audit을 300 더 수행 (총 600)
2. **옵션 2**: 남은 OK-합의군 전수에 대해 전문의 단독 검토로 전환 (가장 보수적)

**Trigger 미발생 시:**

- 남은 OK-합의군은 resident OK를 최종 OK로 인정
- 단, 통계 분석에서 audit 기반 보수 상계(upper bound) 사용

**※ 중요**: 위 임계값은 연구팀이 수용 가능한 리스크에 맞춰 조정 가능하나, **"데이터 수집 전에 고정"**이 핵심.

---

## 2. 통계 분석: 오류율(%) 단측 검정/상한 CI

### 2.1 모집단/표본 정의

- 본 S1은 6,000문항(및 향후 생성될 문항)을 **모집단**으로 보고, 그 중 **랜덤 표본 n=987**을 추출해 평가한다.
- 따라서 결과는 **"향후 생성될 문항 포함 모집단의 오류율이 2% 이하인지"**에 대한 추론(inference)을 목표로 한다.

### 2.2 Primary/Secondary Endpoint 정의

- **Primary**: **Major error rate** (학습에 위험한 명백 오류)
- **Secondary**: **Any-issue rate** (minor ambiguity 포함)
- 판단 기준: 초단순 UX의 ISSUE 유형에서 Major/Minor로 분기

### 2.3 검정/성공 기준 (고정)

#### 가설 (단측)

- H0: p ≥ 0.02
- H1: p < 0.02

#### 유의수준 및 방법

- 유의수준: α = 0.05 (단측)
- 통계 방법: Exact binomial test 또는 Clopper-Pearson 단측 상한 CI

#### 성공 기준

**Major error rate의 단측 95% 상한(upper CI)이 2% 이하**

#### 대략적인 허용 오류 수 가이드 (참고용)

**※ 주의**: 아래는 단순 binomial test 기준입니다. 실제 Triage + Audit 구조에서는 Flagged군과 OK-합의군의 분포에 따라 보수적 상한이 달라질 수 있습니다.

단순 계산 기준 (n=987, 단측 95% 상한):
- **0~5개 오류**: 상한 CI < 2%, **PASS 가능성이 높음**
- **6~10개 오류**: 상한 CI ≈ 2% 근처, **경계선** (실제 분포에 따라 PASS/FAIL 가능)
- **10개 이상 오류**: 상한 CI > 2%, **FAIL 가능성이 높음**

**예상 기대값**: n=987 × 2% = 약 19.7개 오류가 기대되지만, 통계적 검정에서는 **관찰된 오류가 적을수록 상한 CI가 낮아져** 통과 가능성이 높아집니다.

**실제 평가 시**: 층화 기반 보수적 상한 계산 방식을 사용하므로, 정확한 허용 오류 수는 데이터 수집 후 분석 단계에서 결정됩니다.

### 2.4 Triage + Audit 설계에 맞춘 "보수적 상한" 추정 (필수)

Attending이 전수 검토하지 않으므로, 아래처럼 **층화(stratum) 기반 상한**을 계산해 과소추정을 방지한다.

#### Flagged군 (전문의 전수 검토)

- `e_flagged_major`: Flagged군에서 Major error로 판정된 개수
- `e_flagged_total`: Flagged군에서 ISSUE(Total)로 판정된 개수
- `N_flagged`: Flagged군 총 문항 수

#### OK-합의군 (Audit 샘플링)

- `N_ok_audit`: Audit 대상 문항 수 (300)
- `e_audit_major`: Audit에서 Major error로 판정된 개수
- `e_audit_total`: Audit에서 ISSUE(Total)로 판정된 개수

- OK-합의군의 "오류율"에 대한 **단측 95% 상한** `ub_ok_major`, `ub_ok_total`를 exact binomial로 계산
- 남은 OK-합의군(미검토)의 오류는 최악의 경우 `ub_ok`를 적용한다고 가정 (보수적)

#### 전체 오류율의 보수적 상한

**Major error rate 상한:**
```
UB_total_major = (e_flagged_major + ub_ok_major * (N_ok_total)) / N_total
```

**Any-issue rate 상한:**
```
UB_total_any = (e_flagged_total + ub_ok_total * (N_ok_total)) / N_total
```

여기서:
- `N_ok_total`: OK-합의군 총 문항 수 (audit 300 포함)
- `N_total`: 전체 평가 문항 수 (987)

**※ 구현 참고**: Audit 300도 OK-합의군의 일부이므로, `N_ok_total`에 audit 포함/미포함을 일관되게 처리해야 함.

---

## 3. 평가 UX: 초단순 문항 평가 (220문항/인 완주 가능)

### 3.1 Resident 입력 (전수, 1클릭 중심)

#### 필수 입력

- `R?_decision`: **OK / ISSUE / UNCLEAR** (1개만 선택)

#### ISSUE/UNCLEAR일 때만 추가 입력

- `R?_issue_type`: 
  - **Major**: 명백한 사실 오류/오해 위험 (정답 자체가 틀림, 핵심 개념 왜곡)
  - **Minor**: 핵심은 맞으나 조건/표현이 부정확, 애매함
  - **Scope**: 시험 범위/난이도 부적절
  - **Structure**: 질문-답변 구조가 혼란, front/back 역할 불명확
  - **Image_dependency**: 이미지 없이 이해 불가
  - **Other**: 기타
  
  (복수 선택 가능 또는 1개+Other)

- `R?_comment`: 선택, 한 줄 코멘트

### 3.2 교육품질 점수 (선택, 샘플링)

- Educational quality 1~5는 **전수에서 제거**
- 옵션: 각 batch(110문항)에서 랜덤 10%만 1~5 부여 (분석은 보조)

---

## 4. 배포 단위: 987문항을 110문항 배치로 나누기

### 4.1 배치 구성

- **P01~P09 배치** (각 109~110문항)로 분할
- Sheets 성능/완주율 확보를 위해 배치 단위로 제공

### 4.2 배정 방식

- "각 문항은 resident 2명에게 중복 배정"은 유지
- 권장 배정: **ring 방식**으로 batch가 정확히 2명에게 배정되도록 구성

예시:
- P01: R1, R2
- P02: R2, R3
- P03: R3, R4
- ...
- P09: R9, R1

---

## 5. 평가 프로세스 요약

### 5.1 1차 평가 (Resident 2인)

1. Resident 2인이 각 문항에 대해 독립적으로 **OK/ISSUE/UNCLEAR** 판정
2. 결과 분류:
   - 둘 다 OK → OK-합의군
   - 그 외 → Flagged군

### 5.2 2차 평가 (Attending)

1. **Flagged군**: 전문의가 전수 검토하여 최종 판정 (Major/Minor 구분)
2. **OK-합의군**: 무작위 300문항을 전문의가 audit

### 5.3 에스컬레이션 검토

1. Audit 300 결과를 바탕으로 에스컬레이션 트리거 충족 여부 확인
2. Trigger 발생 시 추가 audit 또는 전수 검토 수행

### 5.4 통계 분석

1. 층화 기반 보수적 상한 계산
2. Primary endpoint: Major error rate의 단측 95% 상한이 2% 이하인지 확인

---

## 6. 관련 문서

- `QA_Rater_OnePage_Checklist.md`: 초단순 평가 UX 체크리스트
- `QA_Framework_v2.0.md`: 전체 QA 프레임워크 (S1 섹션 참조)
- `Evaluation_Unit_and_Scope_Definition.md`: 평가 단위 정의
- `QA_Metric_Definitions.md`: QA 지표 정의

---

**작성일**: 2025-12-20  
**작성자**: MeducAI 연구팀  
**목적**: S1 QA 실행을 위한 최종 설계 문서

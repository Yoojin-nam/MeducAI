# FINAL QA 테이블/인포그래픽 평가 샘플링 전략

**Status:** Draft  
**Version:** 1.0  
**Date:** 2025-12-29  
**Purpose:** FINAL 배포용 테이블/인포그래픽 평가를 위한 통계적 샘플링 전략 제안

---

## 1. 배경

### 1.1 평가 목적

테이블/인포그래픽 평가는 **Safety Gate** 목적으로 수행됩니다:

- **Critical Error 탐지**: 임상 판단·학습을 심각히 왜곡할 수 있는 사실 오류
- **Scope/Alignment Failure 탐지**: Group Path / objectives와의 명백한 불일치
- **위험 기반 QA**: MI-CLEAR-LLM 원칙에 따른 risk-based quality assurance

### 1.2 평가 특성

- **이진 결과 (Binary Outcome)**: PASS / FAIL (Critical Error 또는 Scope Failure 여부)
- **통계적 분석 대상 아님**: Primary endpoint가 아닌 safety gate
- **낮은 오류율 가정**: Critical Error rate는 일반적으로 낮음 (예: 1-5%)

---

## 2. 전체 규모 추정

### 2.1 FINAL 배포 규모

- **TOTAL_CARDS = 6,000** (Canonical)
- **Entity당 카드 수**: 2장 (Q1, Q2)
- **총 Entity 수**: 약 3,000 entities (6,000 / 2)

### 2.2 테이블/인포그래픽 개수

**중요**: 테이블과 인포그래픽은 **그룹당 1개씩** 생성됩니다:
- **그룹당 1개 테이블** (S1 Master Table)
- **그룹당 1개 인포그래픽** (S4 Table Visual)

따라서:
- **전체 그룹 수 = 전체 테이블 수 = 전체 인포그래픽 수**

### 2.3 그룹 수 추정

- **그룹당 Entity 수**: 가변적 (S1 출력에 따라 결정)
- **전체 그룹 수**: 정확한 수는 `groups_canonical.csv`에 따라 결정됨
- **추정**: 그룹당 평균 3-5 entities 가정 시, 약 **600-1,000 그룹**

**참고**: 정확한 그룹 수는 실제 `groups_canonical.csv` 파일을 확인해야 합니다.

---

## 3. 통계적 샘플링 전략

### 3.1 목적

Critical Error rate를 **95% 신뢰구간**으로 추정하여, 전체 배포물의 안전성을 보장합니다.

### 3.2 가정

- **예상 Critical Error rate (p)**: 2-5% (낮은 오류율 가정)
- **신뢰수준**: 95% (Z = 1.96)
- **허용 오차 (Margin of Error, E)**: 1-2%

### 3.3 샘플 크기 계산

**이진 결과 (Binary Outcome)에 대한 샘플 크기 공식**:

```
n = (Z² × p × (1-p)) / E²
```

여기서:
- `n`: 필요한 샘플 크기
- `Z`: 신뢰수준에 따른 Z-score (95% → 1.96)
- `p`: 예상 비율 (Critical Error rate)
- `E`: 허용 오차 (Margin of Error)

### 3.4 시나리오별 계산 결과

**참고**: 테이블/인포그래픽 개수 = 그룹 수이므로, "그룹 수"와 "테이블/인포그래픽 수"는 동일합니다.

| 예상 오류율 (p) | 허용 오차 (E) | 필요한 샘플 크기 (n) | 전체 그룹/테이블/인포그래픽 대비 비율 (600개 기준) | 전체 그룹/테이블/인포그래픽 대비 비율 (1000개 기준) |
|----------------|--------------|---------------------|-------------------------------------|-------------------------------------|
| 2% | 1% | **753** | 125.5% (전체 평가 필요) | 75.3% |
| 2% | 2% | **188** | 31.3% | 18.8% |
| 5% | 1% | **1,825** | 304.2% (불가능) | 182.5% (불가능) |
| 5% | 2% | **457** | 76.2% | 45.7% |
| 5% | 3% | **203** | 33.8% | 20.3% |

### 3.5 권장 샘플 크기

**권장 전략 (Conservative Approach)**:

- **목표**: Critical Error rate를 95% CI로 추정, margin of error = 2%
- **예상 오류율**: 2-5%
- **필요한 샘플 크기**: **200-250 그룹 (또는 테이블/인포그래픽)**

**이유**:
- 600 그룹/테이블/인포그래픽 기준: 약 33-42% 샘플링
- 1000 그룹/테이블/인포그래픽 기준: 약 20-25% 샘플링
- 실용적이고 통계적으로 충분한 샘플 크기

---

## 4. 샘플링 방법

### 4.1 Simple Random Sampling (SRS)

**방법**: 전체 그룹 중 무작위로 n개 선택

**장점**:
- 구현 간단
- 통계적 추론이 명확함

**단점**:
- 그룹 간 변이성 고려 안 함
- 특정 그룹 타입이 과소/과대 표집될 수 있음

### 4.2 Stratified Sampling (권장)

**방법**: 그룹을 특성에 따라 층화(strata) 후 각 층에서 비례 샘플링

**층화 기준 (예시)**:
- **Group Path** (예: Chest, Neuro, Abdomen)
- **Group Weight** (중요도)
- **Entity 수** (그룹당 entity 개수)

**장점**:
- 그룹 간 변이성 고려
- 더 정확한 추정 가능
- 대표성 향상

**단점**:
- 구현 복잡도 증가
- 층화 기준 사전 정의 필요

### 4.3 권장 방법

**Stratified Sampling by Group Path** (권장)

- Group Path별로 층화 (예: Chest, Neuro, Abdomen, MSK 등)
- 각 층에서 비례 샘플링
- 각 층에서 최소 10-20개 그룹 샘플링 (통계적 안정성)

---

## 5. 평가 항목 및 시간

### 5.1 평가 항목 (S0와 동일)

| 항목 | 타입 | 설명 |
|------|------|------|
| **Critical Error** | Yes/No | 임상 판단·학습을 심각히 왜곡할 수 있는 사실 오류 |
| **Scope/Alignment Failure** | Yes/No | Group Path / objectives와의 명백한 불일치 |

**Gate Result**:
- **PASS**: 둘 다 No
- **FAIL**: 하나라도 Yes

### 5.2 예상 시간

- **그룹당 평가 시간**: 90초-2분 (S0 기준, 테이블+인포그래픽 함께 평가)
- **200 그룹 (200 테이블 + 200 인포그래픽) 평가**: 약 3-7시간
- **250 그룹 (250 테이블 + 250 인포그래픽) 평가**: 약 4-8시간

**참고**: 
- 평가자는 1명 또는 2명 (교차 평가)
- 각 그룹에 대해 테이블과 인포그래픽을 함께 평가 (그룹당 1회 평가)

---

## 6. 통계적 분석 계획

### 6.1 Primary Analysis

**Critical Error Rate 추정**:

```
Critical Error Rate = (Critical Error 발생 그룹 수) / (전체 평가 그룹 수)
```

**참고**: 각 그룹에 대해 테이블과 인포그래픽을 함께 평가하므로, 그룹 단위로 Critical Error 여부를 판단합니다.

**95% 신뢰구간 (Clopper-Pearson)**:

```
CI = p ± Z × √(p(1-p)/n)
```

### 6.2 Secondary Analysis

- **Scope Failure Rate**: Scope/Alignment Failure 발생률
- **Gate Failure Rate**: 전체 Gate FAIL 비율
- **Stratum별 분석**: Group Path별 Critical Error rate 비교

### 6.3 Decision Rule

- **Critical Error Rate < 5%**: 배포 승인 (안전)
- **Critical Error Rate ≥ 5%**: 전체 재평가 또는 수정 후 재평가 고려

---

## 7. 실행 계획

### 7.1 샘플링 실행

1. **전체 그룹 수 확인**: `groups_canonical.csv` 파일 확인 (그룹 수 = 테이블 수 = 인포그래픽 수)
2. **층화 기준 결정**: Group Path 또는 다른 기준
3. **샘플 크기 결정**: 목표 200-250 그룹 (각 그룹당 테이블 1개 + 인포그래픽 1개)
4. **무작위 샘플링**: 각 층에서 비례 샘플링

### 7.2 평가 실행

1. **평가자 할당**: 1-2명 평가자
2. **평가 진행**: 그룹당 90초-2분
3. **데이터 수집**: Critical Error, Scope Failure 기록
4. **통계 분석**: Critical Error rate 및 95% CI 계산

### 7.3 결과 해석

- **Critical Error Rate < 5%**: 배포 승인
- **Critical Error Rate ≥ 5%**: 추가 조치 필요 (전체 재평가 또는 수정)

---

## 8. 참고 문서

- **S0 QA Form**: `0_Protocol/06_QA_and_Study/QA_Operations/S0_QA_Form_One-Screen_Layout.md`
- **S0 Non-Inferiority Protocol**: `0_Protocol/06_QA_and_Study/Model_Selection/S0_Non-Inferiority_QA_and_Final_Model_Selection_Protocol.md`
- **FINAL QA Evaluation Items**: `0_Protocol/05_Pipeline_and_Execution/FINAL_QA_Evaluation_Items_and_Time_Estimate.md`

---

## 9. 요약

### 9.1 권장 샘플 크기

- **목표**: **200-250 그룹** (전체 그룹/테이블/인포그래픽의 약 20-40%)
- **근거**: Critical Error rate 2-5% 가정, margin of error 2%, 95% 신뢰수준
- **참고**: 그룹 수 = 테이블 수 = 인포그래픽 수 (그룹당 1개씩)

### 9.2 샘플링 방법

- **권장**: **Stratified Sampling by Group Path**
- **대안**: Simple Random Sampling (구현 간단)

### 9.3 예상 시간

- **200 그룹**: 약 3-7시간
- **250 그룹**: 약 4-8시간

### 9.4 Decision Rule

- **Critical Error Rate < 5%**: 배포 승인
- **Critical Error Rate ≥ 5%**: 추가 조치 필요

---

**작성자**: MeducAI Research Team  
**검토 필요**: 실제 그룹 수 확인 후 샘플 크기 조정


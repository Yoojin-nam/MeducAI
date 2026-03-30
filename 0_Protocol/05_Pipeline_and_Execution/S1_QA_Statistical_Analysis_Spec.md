# S1 QA 통계 분석 코드 스펙

**Status:** Canonical (Analysis Specification)  
**Version:** 1.0  
**Date:** 2025-12-20  
**Purpose:** S1 QA 평가 결과의 통계 분석 코드 구현 스펙

---

## 0. 개요

본 문서는 S1 QA 평가(오류율 검증 ≤2%, n=987) 결과를 분석하는 통계 분석 코드의 입력, 출력, 알고리즘을 정의합니다.

**목표**: 모집단의 Major error rate ≤ 2% 여부를 통계적으로 추론

---

## 1. 입력 데이터

### 1.1 필수 입력 파일

#### 1.1.1 Resident 판정 CSV

**파일명**: `S1_QA_Resident_Judgments_YYYYMMDD.csv`

**필수 컬럼**:
- `Item_ID`: 문항 고유 ID
- `Batch_ID`: 배치 ID (P01~P09)
- `R1_decision`: R1의 판정 (OK / ISSUE / UNCLEAR)
- `R1_issue_type`: R1의 문제 유형 (Major / Minor / Scope / Structure / Image_dependency / Other, 복수 선택 가능)
- `R2_decision`: R2의 판정 (OK / ISSUE / UNCLEAR)
- `R2_issue_type`: R2의 문제 유형 (Major / Minor / Scope / Structure / Image_dependency / Other, 복수 선택 가능)

**옵션 컬럼**:
- `R1_comment`: R1의 코멘트
- `R2_comment`: R2의 코멘트

#### 1.1.2 Attending 판정 CSV

**파일명**: `S1_QA_Attending_Judgments_YYYYMMDD.csv`

**필수 컬럼**:
- `Item_ID`: 문항 고유 ID
- `A_decision`: Attending 최종 판정 (OK / ISSUE)
- `A_issue_type_major`: Major error 여부 (TRUE / FALSE)
- `A_issue_type_minor`: Minor issue 여부 (TRUE / FALSE)

**옵션 컬럼**:
- `A_comment`: Attending 코멘트

**참고**: Flagged군과 Audit 대상만 포함 (전수 검토 또는 Audit 300)

#### 1.1.3 Audit 샘플 리스트

**파일명**: `S1_QA_Audit_Sample_YYYYMMDD.csv`

**필수 컬럼**:
- `Item_ID`: Audit 대상 문항 고유 ID
- `Audit_seed`: Audit 샘플링에 사용된 seed (고정 값, 예: 20251220)

**또는**:
- 별도 파일 없이 코드 내에서 고정 seed로 재생성 가능

---

## 2. 출력 결과

### 2.1 Audit 결과 요약

#### 2.1.1 Audit 통계

- `e_audit_major`: Audit에서 Major error로 판정된 개수
- `e_audit_total`: Audit에서 ISSUE(Total, Major+Minor)로 판정된 총 개수
- `n_audit`: Audit 대상 문항 수 (300)
- `p_audit_major`: Audit에서 Major error 비율 (`e_audit_major / n_audit`)
- `p_audit_total`: Audit에서 ISSUE 비율 (`e_audit_total / n_audit`)

#### 2.1.2 Agreement 통계

- `n_audit_ok_agreement`: Audit에서 Resident 둘 다 OK였고 Attending도 OK로 판정한 개수
- `n_audit_ok_total`: Audit에서 Resident 둘 다 OK였던 총 개수
- `agreement_with_attending`: 일치율 (`n_audit_ok_agreement / n_audit_ok_total`)

### 2.2 에스컬레이션 트리거 충족 여부

#### 2.2.1 트리거 조건 확인

- **Trigger A**: `e_audit_major >= 2` → `trigger_a` (Boolean)
- **Trigger B**: `e_audit_total >= 10` → `trigger_b` (Boolean)
- **Trigger C**: `agreement_with_attending < 0.95` → `trigger_c` (Boolean)
- **Overall Trigger**: `escalation_triggered` (Boolean) = `trigger_a OR trigger_b OR trigger_c`

#### 2.2.2 에스컬레이션 권장 사항

- `escalation_action`: "추가_audit_300" 또는 "전수_검토" (옵션 1 또는 2)

### 2.3 층화 기반 보수적 상한

#### 2.3.1 Flagged군 통계

- `N_flagged`: Flagged군 총 문항 수
- `e_flagged_major`: Flagged군에서 Major error로 판정된 개수
- `e_flagged_total`: Flagged군에서 ISSUE(Total)로 판정된 개수
- `p_flagged_major`: Flagged군 Major error 비율 (`e_flagged_major / N_flagged`)
- `p_flagged_total`: Flagged군 ISSUE 비율 (`e_flagged_total / N_flagged`)

#### 2.3.2 OK-합의군 통계

- `N_ok_total`: OK-합의군 총 문항 수 (audit 300 포함)
- `N_ok_audit`: Audit 대상 문항 수 (300)
- `e_ok_audit_major`: Audit에서 Major error로 판정된 개수
- `e_ok_audit_total`: Audit에서 ISSUE(Total)로 판정된 개수
- `ub_ok_major`: OK-합의군 Major error rate의 단측 95% 상한 (exact binomial)
- `ub_ok_total`: OK-합의군 ISSUE rate의 단측 95% 상한 (exact binomial)

#### 2.3.3 전체 보수적 상한

- `N_total`: 전체 평가 문항 수 (987)
- `UB_total_major`: 전체 Major error rate의 보수적 상한
- `UB_total_total`: 전체 ISSUE rate의 보수적 상한

**계산식**:
```
UB_total_major = (e_flagged_major + ub_ok_major * N_ok_total) / N_total
UB_total_total = (e_flagged_total + ub_ok_total * N_ok_total) / N_total
```

### 2.4 Exact Binomial One-Sided Upper CI

#### 2.4.1 Major Error Rate 검정

- `upper_ci_major_95`: Major error rate의 단측 95% 상한 (Clopper-Pearson 또는 exact binomial)
- `test_result_major`: PASS / FAIL (`upper_ci_major_95 <= 0.02`이면 PASS)

#### 2.4.2 Any-Issue Rate 검정 (Secondary)

- `upper_ci_total_95`: ISSUE rate의 단측 95% 상한
- `test_result_total`: PASS / FAIL (보조 정보)

---

## 3. 알고리즘 스펙

### 3.1 데이터 전처리

#### 3.1.1 층화 분류

1. Resident 판정 CSV를 읽어서 각 문항의 `Stratum` 계산:
   - `R1_decision == "OK" AND R2_decision == "OK"` → "OK-합의군"
   - 그 외 → "Flagged군"

2. Flagged군과 OK-합의군으로 데이터 분할

#### 3.1.2 Audit 샘플 확인

1. OK-합의군에서 Audit 대상 문항 식별 (고정 seed로 재생성 또는 별도 파일에서 읽기)
2. Audit 대상 문항과 Attending 판정 매칭

### 3.2 Audit 결과 요약

#### 3.2.1 Audit 통계 계산

```python
# Audit 대상 문항 필터링
audit_items = ok_stratum[ok_stratum['Item_ID'].isin(audit_sample_ids)]

# Attending 판정과 매칭
audit_with_attending = audit_items.merge(attending_df, on='Item_ID', how='left')

# Major error 개수
e_audit_major = (audit_with_attending['A_issue_type_major'] == True).sum()

# Total issue 개수
e_audit_total = (audit_with_attending['A_decision'] == 'ISSUE').sum()

n_audit = len(audit_with_attending)
p_audit_major = e_audit_major / n_audit
p_audit_total = e_audit_total / n_audit
```

#### 3.2.2 Agreement 계산

```python
# Resident 둘 다 OK였던 문항
audit_ok_resident = audit_items[
    (audit_items['R1_decision'] == 'OK') & 
    (audit_items['R2_decision'] == 'OK')
]

# Attending 판정과 매칭
audit_ok_with_attending = audit_ok_resident.merge(attending_df, on='Item_ID', how='left')

# Agreement 계산
n_audit_ok_total = len(audit_ok_with_attending)
n_audit_ok_agreement = (audit_ok_with_attending['A_decision'] == 'OK').sum()
agreement_with_attending = n_audit_ok_agreement / n_audit_ok_total if n_audit_ok_total > 0 else None
```

### 3.3 에스컬레이션 트리거 확인

```python
trigger_a = e_audit_major >= 2
trigger_b = e_audit_total >= 10
trigger_c = agreement_with_attending < 0.95 if agreement_with_attending is not None else False

escalation_triggered = trigger_a or trigger_b or trigger_c
```

### 3.4 보수적 상한 계산

#### 3.4.1 Flagged군 통계

```python
# Flagged군에서 Attending 판정 매칭
flagged_with_attending = flagged_stratum.merge(attending_df, on='Item_ID', how='left')

N_flagged = len(flagged_with_attending)
e_flagged_major = (flagged_with_attending['A_issue_type_major'] == True).sum()
e_flagged_total = (flagged_with_attending['A_decision'] == 'ISSUE').sum()
```

#### 3.4.2 OK-합의군 상한 (Exact Binomial)

**Python 예시 (scipy.stats 사용)**:

```python
from scipy.stats import beta

def exact_binomial_upper_ci(n, k, alpha=0.05):
    """
    Exact binomial의 단측 상한 CI 계산 (Clopper-Pearson)
    
    Parameters:
    n: 시행 횟수
    k: 성공 횟수
    alpha: 유의수준 (기본값 0.05, 단측)
    
    Returns:
    upper_bound: 단측 (1-alpha) 상한
    """
    if k == 0:
        # k=0인 경우 특별 처리
        upper_bound = 1 - (alpha ** (1/n))
    elif k == n:
        # k=n인 경우
        upper_bound = 1.0
    else:
        # Clopper-Pearson: beta 분포 사용
        upper_bound = beta.ppf(1 - alpha, k + 1, n - k)
    
    return upper_bound

# OK-합의군 Audit에서 Major error 상한
ub_ok_major = exact_binomial_upper_ci(N_ok_audit, e_ok_audit_major, alpha=0.05)

# OK-합의군 Audit에서 Total issue 상한
ub_ok_total = exact_binomial_upper_ci(N_ok_audit, e_ok_audit_total, alpha=0.05)
```

**R 예시**:

```r
# Exact binomial upper CI
ub_ok_major <- qbeta(0.95, e_ok_audit_major + 1, N_ok_audit - e_ok_audit_major)
ub_ok_total <- qbeta(0.95, e_ok_audit_total + 1, N_ok_audit - e_ok_audit_total)
```

#### 3.4.3 전체 보수적 상한

```python
# 전체 상한 계산
UB_total_major = (e_flagged_major + ub_ok_major * N_ok_total) / N_total
UB_total_total = (e_flagged_total + ub_ok_total * N_ok_total) / N_total
```

### 3.5 최종 검정 결과

```python
# Major error rate 검정
test_result_major = "PASS" if UB_total_major <= 0.02 else "FAIL"

# Any-issue rate 검정 (Secondary)
test_result_total = "PASS" if UB_total_total <= 0.02 else "FAIL"  # 보조 정보, 임계값은 조정 가능
```

---

## 4. 출력 형식

### 4.1 요약 리포트 (텍스트/표)

```
=== S1 QA 통계 분석 결과 ===

[1] Audit 결과 요약
  - Audit 대상 문항 수: 300
  - Major error 개수: {e_audit_major}
  - Total issue 개수: {e_audit_total}
  - Agreement with attending: {agreement_with_attending:.3f}

[2] 에스컬레이션 트리거
  - Trigger A (Major >= 2): {trigger_a}
  - Trigger B (Total >= 10): {trigger_b}
  - Trigger C (Agreement < 0.95): {trigger_c}
  - 에스컬레이션 필요: {escalation_triggered}

[3] 층화 기반 보수적 상한
  - Flagged군:
    * 문항 수: {N_flagged}
    * Major error: {e_flagged_major} ({p_flagged_major:.3f})
  - OK-합의군:
    * 문항 수: {N_ok_total}
    * Audit 결과: {e_ok_audit_major} Major, {e_ok_audit_total} Total
    * Major error 상한 (95%): {ub_ok_major:.4f}
  - 전체:
    * Major error rate 상한 (95%): {UB_total_major:.4f} ({UB_total_major*100:.2f}%)

[4] 최종 검정 결과
  - Major error rate ≤ 2% 검정: {test_result_major}
  - 상한 CI (95%): {UB_total_major*100:.2f}%
```

### 4.2 상세 결과 CSV

**파일명**: `S1_QA_Analysis_Results_YYYYMMDD.csv`

**컬럼**:
- `metric_name`: 지표명
- `value`: 값
- `unit`: 단위 (count, proportion, upper_ci 등)
- `category`: 카테고리 (audit, escalation, stratum, final 등)

### 4.3 (선택) 시각화

- Audit 결과 분포 (Major/Minor/OK)
- 층화 분류 결과 (OK-합의군 vs Flagged군)
- 보수적 상한과 임계값 (2%) 비교

---

## 5. 구현 예시 (Python)

### 5.1 전체 함수 구조

```python
import pandas as pd
import numpy as np
from scipy.stats import beta

def exact_binomial_upper_ci(n, k, alpha=0.05):
    """Exact binomial의 단측 상한 CI 계산"""
    if k == 0:
        return 1 - (alpha ** (1/n))
    elif k == n:
        return 1.0
    else:
        return beta.ppf(1 - alpha, k + 1, n - k)

def s1_qa_statistical_analysis(
    resident_csv_path,
    attending_csv_path,
    audit_sample_csv_path=None,
    audit_seed=20251220,
    n_total=987,
    target_error_rate=0.02,
    alpha=0.05
):
    """
    S1 QA 통계 분석 메인 함수
    
    Returns:
    dict: 분석 결과 딕셔너리
    """
    # 1. 데이터 로드
    resident_df = pd.read_csv(resident_csv_path)
    attending_df = pd.read_csv(attending_csv_path)
    
    # 2. 층화 분류
    resident_df['Stratum'] = resident_df.apply(
        lambda row: 'OK-합의군' if (row['R1_decision'] == 'OK' and row['R2_decision'] == 'OK') 
        else 'Flagged군',
        axis=1
    )
    
    flagged_stratum = resident_df[resident_df['Stratum'] == 'Flagged군']
    ok_stratum = resident_df[resident_df['Stratum'] == 'OK-합의군']
    
    # 3. Audit 샘플 처리
    if audit_sample_csv_path:
        audit_sample_df = pd.read_csv(audit_sample_csv_path)
        audit_sample_ids = audit_sample_df['Item_ID'].tolist()
    else:
        # 고정 seed로 재생성
        np.random.seed(audit_seed)
        n_audit = 300
        audit_sample_ids = ok_stratum.sample(n=n_audit, random_state=audit_seed)['Item_ID'].tolist()
    
    # 4. Audit 결과 요약
    audit_items = ok_stratum[ok_stratum['Item_ID'].isin(audit_sample_ids)]
    audit_with_attending = audit_items.merge(attending_df, on='Item_ID', how='left')
    
    e_audit_major = (audit_with_attending['A_issue_type_major'] == True).sum()
    e_audit_total = (audit_with_attending['A_decision'] == 'ISSUE').sum()
    n_audit = len(audit_with_attending)
    
    # 5. Agreement 계산
    audit_ok_resident = audit_items[
        (audit_items['R1_decision'] == 'OK') & 
        (audit_items['R2_decision'] == 'OK')
    ]
    audit_ok_with_attending = audit_ok_resident.merge(attending_df, on='Item_ID', how='left')
    n_audit_ok_total = len(audit_ok_with_attending)
    n_audit_ok_agreement = (audit_ok_with_attending['A_decision'] == 'OK').sum()
    agreement_with_attending = n_audit_ok_agreement / n_audit_ok_total if n_audit_ok_total > 0 else None
    
    # 6. 에스컬레이션 트리거
    trigger_a = e_audit_major >= 2
    trigger_b = e_audit_total >= 10
    trigger_c = agreement_with_attending < 0.95 if agreement_with_attending is not None else False
    escalation_triggered = trigger_a or trigger_b or trigger_c
    
    # 7. Flagged군 통계
    flagged_with_attending = flagged_stratum.merge(attending_df, on='Item_ID', how='left')
    N_flagged = len(flagged_with_attending)
    e_flagged_major = (flagged_with_attending['A_issue_type_major'] == True).sum()
    e_flagged_total = (flagged_with_attending['A_decision'] == 'ISSUE').sum()
    
    # 8. OK-합의군 상한
    N_ok_total = len(ok_stratum)
    e_ok_audit_major = e_audit_major
    e_ok_audit_total = e_audit_total
    ub_ok_major = exact_binomial_upper_ci(n_audit, e_ok_audit_major, alpha=alpha)
    ub_ok_total = exact_binomial_upper_ci(n_audit, e_ok_audit_total, alpha=alpha)
    
    # 9. 전체 보수적 상한
    UB_total_major = (e_flagged_major + ub_ok_major * N_ok_total) / n_total
    UB_total_total = (e_flagged_total + ub_ok_total * N_ok_total) / n_total
    
    # 10. 최종 검정
    test_result_major = "PASS" if UB_total_major <= target_error_rate else "FAIL"
    
    # 결과 반환
    return {
        'audit': {
            'n_audit': n_audit,
            'e_audit_major': e_audit_major,
            'e_audit_total': e_audit_total,
            'p_audit_major': e_audit_major / n_audit,
            'p_audit_total': e_audit_total / n_audit,
            'agreement_with_attending': agreement_with_attending
        },
        'escalation': {
            'trigger_a': trigger_a,
            'trigger_b': trigger_b,
            'trigger_c': trigger_c,
            'escalation_triggered': escalation_triggered
        },
        'stratum': {
            'flagged': {
                'N_flagged': N_flagged,
                'e_flagged_major': e_flagged_major,
                'e_flagged_total': e_flagged_total
            },
            'ok': {
                'N_ok_total': N_ok_total,
                'ub_ok_major': ub_ok_major,
                'ub_ok_total': ub_ok_total
            }
        },
        'final': {
            'N_total': n_total,
            'UB_total_major': UB_total_major,
            'UB_total_total': UB_total_total,
            'test_result_major': test_result_major,
            'target_error_rate': target_error_rate
        }
    }
```

---

## 6. 테스트 시나리오

### 6.1 시나리오 A: PASS

- Audit에서 Major error 0개
- Flagged군에서 Major error 5개
- 예상: UB_total_major < 2%

### 6.2 시나리오 B: FAIL

- Audit에서 Major error 3개
- Flagged군에서 Major error 15개
- 예상: UB_total_major > 2%

### 6.3 시나리오 C: 에스컬레이션 트리거

- Audit에서 Major error 2개 이상 또는 Total issue 10개 이상
- 예상: escalation_triggered = True

---

## 7. 관련 문서

- `S1_QA_Design_Error_Rate_Validation.md`: S1 QA 설계 문서
- `S1_QA_Google_Sheets_Template_Spec.md`: Google Sheets 템플릿 스펙

---

**작성일**: 2025-12-20  
**작성자**: MeducAI 연구팀  
**목적**: S1 QA 통계 분석 코드 구현 가이드


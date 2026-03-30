# S1 QA Google Sheets 템플릿 스펙

**Status:** Canonical (Template Specification)  
**Version:** 1.0  
**Date:** 2025-12-20  
**Purpose:** S1 QA 평가를 위한 Google Sheets 템플릿 컬럼 스펙 및 데이터검증 규칙

---

## 0. 개요

본 문서는 S1 QA 평가(오류율 검증 ≤2%, n=987)를 위한 Google Sheets 템플릿의 컬럼 구조, 데이터검증 규칙, 수식을 정의합니다.

**평가 단위**: 1 item = 1 문항 (= 1 카드/문제)

**배치 구성**: P01~P09 배치 (각 109~110문항)로 분할

---

## 1. 기본 구조

### 1.1 시트 구성

각 배치(P01~P09)마다 별도 시트를 생성하거나, 단일 시트에 배치별로 구분하여 구성합니다.

### 1.2 행 구조

- **헤더 행**: Row 1 (고정)
- **데이터 행**: Row 2부터 시작 (각 행 = 1 문항)

---

## 2. 컬럼 스펙 (최소 세트)

### 2.1 기본 정보 (자동 입력 또는 읽기 전용)

| 컬럼명 | 데이터 타입 | 설명 | 예시 |
|--------|------------|------|------|
| `Item_No` | Integer | 문항 번호 (1부터 시작) | 1, 2, 3, ... |
| `Item_ID` | String | 문항 고유 ID | `P01_001`, `P01_002`, ... |
| `Batch_ID` | String | 배치 ID | P01, P02, ..., P09 |
| `Image_Name` | String | 이미지 파일명 또는 URL/FileID | `img_001.png` 또는 Google Drive File ID |
| `Image_thumb` | String | 이미지 썸네일 URL (옵션) | `https://...` (선택) |

### 2.2 Resident 1 판정

| 컬럼명 | 데이터 타입 | 설명 | 데이터검증 |
|--------|------------|------|------------|
| `R1_decision` | String (Dropdown) | R1의 1차 판정 | OK / ISSUE / UNCLEAR |
| `R1_issue_type` | String (Dropdown, 복수 선택 가능) | R1의 문제 유형 (ISSUE/UNCLEAR일 때만) | Major / Minor / Scope / Structure / Image_dependency / Other |
| `R1_comment` | String | R1의 코멘트 (선택, 한 줄) | 텍스트 (최대 500자) |

### 2.3 Resident 2 판정

| 컬럼명 | 데이터 타입 | 설명 | 데이터검증 |
|--------|------------|------|------------|
| `R2_decision` | String (Dropdown) | R2의 1차 판정 | OK / ISSUE / UNCLEAR |
| `R2_issue_type` | String (Dropdown, 복수 선택 가능) | R2의 문제 유형 (ISSUE/UNCLEAR일 때만) | Major / Minor / Scope / Structure / Image_dependency / Other |
| `R2_comment` | String | R2의 코멘트 (선택, 한 줄) | 텍스트 (최대 500자) |

### 2.4 자동 계산 필드

| 컬럼명 | 데이터 타입 | 설명 | 수식 |
|--------|------------|------|------|
| `Disagree_flag` | Boolean | R1과 R2의 판정 불일치 여부 | `=IF(OR(R1_decision<>R2_decision, R1_decision="UNCLEAR", R2_decision="UNCLEAR", R1_decision="ISSUE", R2_decision="ISSUE"), TRUE, FALSE)` |
| `Stratum` | String (자동 계산) | 분류 결과 (OK-합의군 / Flagged군) | `=IF(AND(R1_decision="OK", R2_decision="OK"), "OK-합의군", "Flagged군")` |
| `Has_issue` | Boolean (자동 계산) | ISSUE 또는 UNCLEAR 존재 여부 | `=OR(R1_decision="ISSUE", R1_decision="UNCLEAR", R2_decision="ISSUE", R2_decision="UNCLEAR")` |

### 2.5 Attending 판정 (Flagged군 또는 Audit 대상)

| 컬럼명 | 데이터 타입 | 설명 | 데이터검증 |
|--------|------------|------|------------|
| `A_decision` | String (Dropdown) | Attending 최종 판정 (Flagged군 또는 Audit) | OK / ISSUE |
| `A_issue_type_major` | Boolean | Attending 판정: Major error 여부 | TRUE / FALSE |
| `A_issue_type_minor` | Boolean | Attending 판정: Minor issue 여부 | TRUE / FALSE |
| `A_comment` | String | Attending 코멘트 (선택) | 텍스트 (최대 500자) |
| `Audit_flag` | Boolean | Audit 대상 여부 (OK-합의군에서 무작위 300) | TRUE / FALSE (수동 또는 자동 배정) |

### 2.6 (선택) Educational Quality (샘플링)

| 컬럼명 | 데이터 타입 | 설명 | 데이터검증 |
|--------|------------|------|------------|
| `Edu_Quality_Sample` | Boolean | 품질 점수 샘플링 대상 여부 | TRUE / FALSE (각 배치에서 랜덤 10%) |
| `Edu_Quality_Score` | Integer (조건부) | 교육 품질 점수 (1-5, 샘플링 대상일 때만) | 1 / 2 / 3 / 4 / 5 (Edu_Quality_Sample=TRUE일 때만 입력) |

---

## 3. 데이터검증 규칙

### 3.1 드롭다운 값 정의

#### R1_decision / R2_decision

```
OK
ISSUE
UNCLEAR
```

#### R1_issue_type / R2_issue_type

```
Major
Minor
Scope
Structure
Image_dependency
Other
```

**참고**: Google Sheets의 데이터검증에서 "목록"을 사용하며, 복수 선택이 필요한 경우 셀에 쉼표로 구분된 값 입력 (예: "Major, Minor") 또는 별도 체크박스 컬럼 구성

#### A_decision

```
OK
ISSUE
```

### 3.2 조건부 입력 규칙

1. **R1_issue_type / R2_issue_type**: 해당 행의 `R1_decision` 또는 `R2_decision`이 "ISSUE" 또는 "UNCLEAR"일 때만 입력 가능
   - 데이터검증 수식: `=OR(R1_decision="ISSUE", R1_decision="UNCLEAR")` (R1_issue_type의 경우)
   - 또는 별도 안내 메시지로 처리

2. **Edu_Quality_Score**: `Edu_Quality_Sample=TRUE`일 때만 입력 가능
   - 데이터검증 수식: `=IF(Edu_Quality_Sample=TRUE, TRUE, FALSE)`

3. **A_decision**: `Stratum="Flagged군"` 또는 `Audit_flag=TRUE`일 때만 입력 가능

---

## 4. Google Sheets 데이터검증 설정 예시

### 4.1 드롭다운 설정

**셀 범위**: `C2:C1000` (R1_decision 컬럼)

**데이터검증 규칙**:
- 기준: 목록
- 값: `OK,ISSUE,UNCLEAR` (쉼표로 구분)
- 잘못된 데이터 입력 시: 경고 표시
- 빈 셀 허용: 아니오

### 4.2 조건부 입력 설정

**셀 범위**: `D2:D1000` (R1_issue_type 컬럼)

**데이터검증 규칙**:
- 기준: 사용자 지정 수식
- 수식: `=OR(C2="ISSUE", C2="UNCLEAR")` (C2는 해당 행의 R1_decision)
- 설명: "ISSUE 또는 UNCLEAR일 때만 입력하세요"
- 잘못된 데이터 입력 시: 경고 표시

---

## 5. 수식 예시

### 5.1 Disagree_flag (불일치 여부)

```
=IF(OR(C2<>H2, C2="UNCLEAR", H2="UNCLEAR", C2="ISSUE", H2="ISSUE"), TRUE, FALSE)
```

여기서:
- C2: R1_decision
- H2: R2_decision

### 5.2 Stratum (층화 분류)

```
=IF(AND(C2="OK", H2="OK"), "OK-합의군", "Flagged군")
```

### 5.3 Has_issue (문제 존재 여부)

```
=OR(C2="ISSUE", C2="UNCLEAR", H2="ISSUE", H2="UNCLEAR")
```

---

## 6. 배치별 시트 구성 (권장)

### 6.1 시트 구조

- **시트명**: `P01`, `P02`, ..., `P09`
- 각 시트는 동일한 컬럼 구조 사용
- Item_No는 각 시트 내에서 1부터 시작

### 6.2 통합 요약 시트 (선택)

- **시트명**: `Summary` 또는 `Overview`
- 모든 배치의 통계 요약 (자동 계산)
- 층화 분류 결과 집계
- Audit 배정 상태 확인

---

## 7. Audit 배정 (OK-합의군 300문항)

### 7.1 Audit 배정 방법

1. 모든 배치에서 OK-합의군(Stratum="OK-합의군") 문항 추출
2. 고정 seed를 사용한 무작위 샘플링으로 300문항 선택
3. 선택된 문항의 `Audit_flag`를 TRUE로 설정

### 7.2 구현 예시 (Python 스크립트 또는 Google Sheets 수식)

**Python 예시**:
```python
import pandas as pd
import numpy as np

# 고정 seed
np.random.seed(20251220)

# 모든 배치 데이터 로드
df = pd.read_csv("s1_qa_all_batches.csv")

# OK-합의군 필터링
ok_stratum = df[df['Stratum'] == 'OK-합의군'].copy()

# 300문항 무작위 선택
audit_sample = ok_stratum.sample(n=300, random_state=20251220)

# Audit_flag 업데이트
df.loc[df['Item_ID'].isin(audit_sample['Item_ID']), 'Audit_flag'] = True

# 저장
df.to_csv("s1_qa_all_batches_with_audit.csv", index=False)
```

---

## 8. 데이터 내보내기 (CSV)

### 8.1 내보내기 형식

- 형식: CSV (UTF-8, 쉼표 구분)
- 파일명: `S1_QA_Batch_P01_YYYYMMDD.csv` (배치별) 또는 `S1_QA_All_Batches_YYYYMMDD.csv` (통합)

### 8.2 필수 컬럼 (최소 세트)

다음 컬럼은 분석에 필수:
- Item_No, Item_ID, Batch_ID
- R1_decision, R1_issue_type, R1_comment
- R2_decision, R2_issue_type, R2_comment
- Disagree_flag, Stratum
- A_decision, A_issue_type_major, A_issue_type_minor (Flagged군 또는 Audit 대상)
- Audit_flag

---

## 9. 템플릿 체크리스트

### 9.1 초기 설정

- [ ] 모든 배치 시트 생성 (P01~P09)
- [ ] 헤더 행 (Row 1)에 컬럼명 입력
- [ ] 데이터검증 규칙 적용 (드롭다운)
- [ ] 자동 계산 수식 입력 (Disagree_flag, Stratum, Has_issue)
- [ ] 조건부 입력 규칙 설정

### 9.2 데이터 입력 전

- [ ] Item_No, Item_ID, Batch_ID, Image_Name 자동 또는 수동 입력
- [ ] 템플릿 테스트 (샘플 데이터로 검증)

### 9.3 평가 진행 중

- [ ] Resident 2인이 독립적으로 입력
- [ ] 불일치 확인 (Disagree_flag 활용)
- [ ] Flagged군 식별 (Stratum 활용)

### 9.4 평가 완료 후

- [ ] Audit 300 배정 (고정 seed 사용)
- [ ] Attending 판정 입력 (Flagged군 + Audit 대상)
- [ ] 데이터 내보내기 (CSV)

---

## 10. 관련 문서

- `S1_QA_Design_Error_Rate_Validation.md`: S1 QA 설계 문서
- `QA_Rater_OnePage_Checklist.md`: 초단순 평가 UX 체크리스트
- `S1_QA_Statistical_Analysis_Spec.md`: 통계 분석 코드 스펙

---

**작성일**: 2025-12-20  
**작성자**: MeducAI 연구팀  
**목적**: S1 QA Google Sheets 템플릿 구현 가이드


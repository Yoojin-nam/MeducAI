# Google Form 설계 명세서 (S0 QA)

**Date:** 2025-12-20  
**Status:** Design Specification  
**Purpose:** Google Form 기반 S0 QA 운영 설계

---

## 1. 평가 단위 명확화

### 1.1 Q01~Q12의 의미

- **Q01~Q12 = 각각 하나의 Set** (12장 카드 묶음)
- **1인당 총 12 Set 평가** (Q01~Q12)
- 각 Q는 하나의 Set을 의미하며, Set 전체를 종합적으로 평가

### 1.2 블라인딩 원칙

- **각 평가자 폴더 내에서 Q01~Q12의 의미는 서로 다를 수 있음**
- 예: Reviewer A의 Q01 = Set #45, Reviewer B의 Q01 = Set #12
- 블라인딩 및 배정 독립성에는 문제 없음

---

## 2. Google Form 구조

### 2.1 기본 설정

- **Google 계정 로그인 필수**
- **Limit to 1 response: ON** (중복 응답 방지)
- **자동 저장 → 중간 저장 후 이어서 응답 가능**

### 2.2 Form 구조

- **Section 1: 평가자 정보**
  - 평가자 구분: 전문의 / 전공의
  - 평가자 이메일
  - (선택) 평가자 ID (자동 생성 또는 입력)

- **Section 2 ~ 13: Q01 ~ Q12** (각 Set 1개당 1섹션)
  - 각 섹션은 하나의 Set을 평가
  - Q번호는 섹션 자체로 암묵적으로 결정

### 2.3 핵심 문항 (각 Q 섹션)

#### 평가자 정보 (Section 1)
- 평가자 구분: 전문의 / 전공의
- 평가자 이메일

#### 각 Q 섹션 (Section 2~13, Q01~Q12)
- **Overall Card Quality:** 1–5 (Likert) ⚠️ **필수 - Primary Endpoint**
- **Accuracy:** 1.0 / 0.5 / 0.0
- **Clinical relevance:** 1–5 (Likert)
- **Clarity / readability:** 1–5 (Likert)
- **Major error 여부:** 있음 / 없음 (Blocking Error)
- **Editing time (분):** 숫자 입력 (분 단위)
- **(선택) 자유 의견:** 텍스트 입력

> **중요:** 파일명이나 arm 정보를 입력하는 문항은 **존재하지 않음**  
> Q번호는 **섹션 자체**로 암묵적으로 결정됨

---

## 3. PDF 배포 방법

### 3.1 문제 상황

- 각 평가자마다 배정된 PDF가 다름
- 블라인딩을 위해 평가자별로 다른 Set이 Q01~Q12로 매핑됨
- 모든 평가자에게 동일한 PDF를 공유할 수 없음

### 3.2 배포 방법 옵션

#### 옵션 A: 이메일 배포 (권장)

**장점:**
- ✅ 간단하고 즉시 실행 가능
- ✅ 평가자별 개별 PDF 첨부 가능
- ✅ Google Form 링크와 함께 전송 가능
- ✅ 접근 제어 용이 (이메일 주소 기반)

**단점:**
- ⚠️ 이메일 첨부 용량 제한 (Gmail: 25MB)
- ⚠️ PDF 파일 관리 복잡 (12개 PDF × 평가자 수)
- ⚠️ 재배포 시 수동 작업 필요

**구현 방법:**
1. 각 평가자별로 12개 PDF 파일 준비 (Q01~Q12)
2. 이메일로 PDF 파일 + Google Form 링크 전송
3. 이메일 본문에 평가 가이드 포함

#### 옵션 B: Google Drive 공유 폴더

**장점:**
- ✅ 파일 용량 제한 없음
- ✅ 중앙 집중식 관리
- ✅ 버전 관리 용이
- ✅ 접근 권한 세밀하게 제어 가능

**단점:**
- ⚠️ 평가자별 개별 폴더 생성 필요 (12개 PDF × 평가자 수)
- ⚠️ 폴더 구조 관리 복잡
- ⚠️ 평가자가 올바른 폴더에 접근하는지 확인 필요

**구현 방법:**
1. 각 평가자별로 Google Drive 폴더 생성
2. 해당 평가자의 12개 PDF (Q01~Q12) 업로드
3. 폴더 공유 링크를 평가자 이메일로 전송
4. Google Form 링크도 함께 전송

**폴더 구조 예시:**
```
Google Drive/
├── Reviewer_A/
│   ├── Q01_Set45.pdf
│   ├── Q02_Set12.pdf
│   ├── ...
│   └── Q12_Set89.pdf
├── Reviewer_B/
│   ├── Q01_Set12.pdf
│   ├── Q02_Set45.pdf
│   ├── ...
│   └── Q12_Set67.pdf
└── ...
```

#### 옵션 C: Google Form에 PDF 링크 포함

**장점:**
- ✅ 평가자가 Form과 PDF를 동시에 볼 수 있음
- ✅ 섹션별로 해당 PDF 링크 제공 가능
- ✅ 중앙 집중식 관리

**단점:**
- ⚠️ Google Form에서 링크 클릭 시 새 탭 열림 (동시 보기 어려움)
- ⚠️ 평가자별로 다른 링크를 제공해야 함 (조건부 로직 필요)
- ⚠️ Google Form의 조건부 로직이 복잡할 수 있음

**구현 방법:**
1. Google Drive에 평가자별 폴더 생성 (옵션 B와 동일)
2. Google Form 각 Q 섹션에 해당 PDF 링크 포함
3. 평가자 이메일 기반으로 조건부 링크 제공 (복잡)

**권장하지 않음:** Google Form의 조건부 로직이 복잡하고, 평가자별로 다른 Form을 만들어야 할 수 있음

#### 옵션 D: 하이브리드 (이메일 + Drive)

**장점:**
- ✅ 이메일로 간단한 안내 + Drive 링크 제공
- ✅ 파일 용량 문제 해결
- ✅ 중앙 집중식 관리

**구현 방법:**
1. Google Drive에 평가자별 폴더 생성
2. 이메일로 Drive 폴더 링크 + Google Form 링크 전송
3. 이메일 본문에 평가 가이드 포함

---

### 3.3 권장 배포 방법

**권장: 옵션 D (하이브리드: 이메일 + Drive)**

**이유:**
1. ✅ 파일 용량 제한 없음 (Drive 활용)
2. ✅ 중앙 집중식 관리 (Drive)
3. ✅ 간단한 안내 (이메일)
4. ✅ 접근 권한 제어 용이 (Drive 공유 설정)

**구현 절차:**

1. **Google Drive 준비**
   ```
   Google Drive/
   ├── S0_QA_Reviewers/
   │   ├── Reviewer_A_Email@example.com/
   │   │   ├── Q01.pdf
   │   │   ├── Q02.pdf
   │   │   ├── ...
   │   │   └── Q12.pdf
   │   ├── Reviewer_B_Email@example.com/
   │   │   └── ...
   │   └── ...
   ```

2. **이메일 템플릿**
   ```
   제목: MeducAI S0 QA 평가 요청
   
   안녕하세요 [평가자 이름]님,
   
   MeducAI S0 QA 평가에 참여해 주셔서 감사합니다.
   
   평가 자료:
   - Google Drive 폴더: [개인 폴더 링크]
   - Google Form: [Form 링크]
   
   평가 가이드:
   1. Google Drive 폴더에서 Q01~Q12 PDF 파일을 확인하세요.
   2. Google Form에서 각 Q 섹션을 순차적으로 평가하세요.
   3. 중간 저장 후 이어서 응답 가능합니다.
   
   문의사항이 있으시면 연락 주세요.
   ```

3. **자동화 스크립트 (선택)**
   - Python 스크립트로 평가자별 폴더 생성 및 PDF 복사
   - 이메일 자동 발송 (Gmail API 또는 SendGrid)

---

## 4. assignment_map.csv 구조

### 4.1 필수 컬럼

| 컬럼명 | 데이터 타입 | 설명 | 예시 |
|--------|-----------|------|------|
| `reviewer_id` | string | 평가자 식별자 (pseudonymized) | `rev_001` |
| `reviewer_email` | string | 평가자 이메일 (선택적, 배포용) | `reviewer@example.com` |
| `local_qid` | string | 평가자별 로컬 Q 번호 | `Q01`, `Q02`, ..., `Q12` |
| `set_id` | string | 실제 Set 식별자 (통계분석용) | `set_045` |
| `group_id` | string | Group ID (통계분석용) | `group_12` |
| `arm_id` | string | Arm ID (통계분석용) | `A`, `B`, `C`, `D`, `E`, `F` |
| `role` | string | 평가자 역할 (선택적) | `resident`, `attending` |

### 4.2 CSV 예시

```csv
reviewer_id,reviewer_email,local_qid,set_id,group_id,arm_id,role
rev_001,reviewer_a@example.com,Q01,set_045,group_12,A,resident
rev_001,reviewer_a@example.com,Q02,set_012,group_05,B,resident
rev_001,reviewer_a@example.com,Q03,set_089,group_18,C,resident
...
rev_001,reviewer_a@example.com,Q12,set_067,group_03,F,resident
rev_002,reviewer_b@example.com,Q01,set_012,group_05,B,attending
rev_002,reviewer_b@example.com,Q02,set_045,group_12,A,attending
...
```

### 4.3 데이터 결합 예시

**Google Form 응답 CSV:**
```csv
reviewer_email,section,accuracy,clinical_relevance,clarity,major_error,editing_time
reviewer_a@example.com,Q01,1.0,4,5,없음,2.5
reviewer_a@example.com,Q02,0.5,3,4,있음,5.0
...
```

**결합 후 데이터:**
```csv
reviewer_id,local_qid,set_id,group_id,arm_id,role,accuracy,clinical_relevance,clarity,major_error,editing_time
rev_001,Q01,set_045,group_12,A,resident,1.0,4,5,없음,2.5
rev_001,Q02,set_012,group_05,B,resident,0.5,3,4,있음,5.0
...
```

### 4.4 데이터 무결성 검증

**검증 항목:**
1. ✅ 모든 `reviewer_id` + `local_qid` 조합이 고유한가?
2. ✅ 각 평가자당 정확히 12개의 `local_qid` (Q01~Q12)가 있는가?
3. ✅ `set_id`, `group_id`, `arm_id`가 모두 채워져 있는가?
4. ✅ Google Form 응답과 `assignment_map.csv`의 조인이 성공하는가?
5. ✅ 누락된 응답이 없는가?

**검증 스크립트 예시:**
```python
import pandas as pd

# assignment_map.csv 로드
assignment = pd.read_csv('assignment_map.csv')

# 검증 1: reviewer_id + local_qid 고유성
assert assignment.groupby(['reviewer_id', 'local_qid']).size().max() == 1

# 검증 2: 각 평가자당 12개 Q
assert all(assignment.groupby('reviewer_id')['local_qid'].count() == 12)

# 검증 3: 필수 컬럼 누락 확인
assert assignment[['set_id', 'group_id', 'arm_id']].notna().all().all()

# 검증 4: Google Form 응답과 조인
form_responses = pd.read_csv('google_form_responses.csv')
merged = form_responses.merge(
    assignment,
    left_on=['reviewer_email', 'section'],
    right_on=['reviewer_email', 'local_qid'],
    how='left'
)
assert merged['set_id'].notna().all()  # 모든 응답이 매핑되었는지 확인
```

---

## 5. 통계 분석 개요

### 5.1 데이터 결합

- **Google Form 응답 CSV** + **assignment_map.csv**
- **Join key:** `reviewer_id` + `local_qid` (Q01~Q12)

### 5.2 통계 분석 개요

- **코호트별(전문의 / 전공의) arm 비교**
- **주요 지표:**
  - 평균 Accuracy (비열등성 Δ 기준)
  - Major error 비율 (안전성)
- **Group을 block으로 한 paired 비교 또는 mixed model 적용 가능**

**분석 모델 예시:**
```r
# Mixed-effects model
outcome ~ arm + role + arm:role + (1|group) + (1|reviewer_id)
```

---

## 6. 본 설계의 장점 요약

- ✔ **완전 블라인드 유지**
- ✔ **arm 균형 확보** → 통계적 안정성
- ✔ **웹 개발 없이 즉시 실행 가능** (Google Form 활용)
- ✔ **평가자 피로도 관리** (1인당 12 set, 중간 저장 가능)
- ✔ **S0 QA 목적(안전성 + 비열등성)에 최적화**

---

## 7. Scope Note

- 본 설계는 **S0 QA에 최적화된 운영 방식**이다.
- S1/S2 단계에서는 Firebase 기반 로그인·자동 배정으로 확장 가능하나,
  본 단계에서는 불필요한 복잡성을 배제한다.

---

## 8. 구현 체크리스트

### 8.1 사전 준비

- [ ] 평가자 목록 및 이메일 수집
- [ ] 평가자별 Set 배정 (assignment algorithm)
- [ ] `assignment_map.csv` 생성 및 검증
- [ ] 평가자별 PDF 파일 준비 (Q01~Q12)

### 8.2 Google Drive 설정

- [ ] Google Drive 폴더 구조 생성
- [ ] 평가자별 개인 폴더 생성
- [ ] PDF 파일 업로드
- [ ] 폴더 공유 권한 설정 (평가자별 개별 공유)

### 8.3 Google Form 생성

- [ ] Section 1: 평가자 정보 섹션 생성
- [ ] Section 2~13: Q01~Q12 평가 섹션 생성
- [ ] 각 섹션에 평가 문항 추가
  - Accuracy (1.0/0.5/0.0)
  - Clinical relevance (1-5)
  - Clarity/readability (1-5)
  - Major error (있음/없음)
  - Editing time (분)
  - 자유 의견 (선택)
- [ ] Google 계정 로그인 필수 설정
- [ ] Limit to 1 response 설정
- [ ] 자동 저장 활성화

### 8.4 배포

- [ ] 이메일 템플릿 작성
- [ ] 평가자별 이메일 발송
  - Google Drive 폴더 링크
  - Google Form 링크
  - 평가 가이드
- [ ] 배포 확인 (평가자 응답 확인)

### 8.5 데이터 수집 및 분석

- [ ] Google Form 응답 CSV 다운로드
- [ ] `assignment_map.csv`와 조인
- [ ] 데이터 무결성 검증
- [ ] 통계 분석 수행

---

## 참고 문서

- QA Framework v2.0
- QA Assignment Plan v2.0
- QA Blinding Procedure v2.0
- New_Google_Form_Design_Comparison.md


# 새로운 Google Form 설계 vs 기존 QA Framework 비교 분석

**Date:** 2025-12-20  
**Status:** Comparison Analysis  
**Purpose:** 새로운 Google Form 설계 아이디어가 기존 QA Framework v2.0과 얼마나 다른지 분석

---

## Executive Summary

**결론: 새로운 설계는 기존 QA Framework의 핵심 원칙과 대부분 일치하지만, 운영 방식과 데이터 구조에서 중요한 차이가 있습니다.**

### 주요 차이점 요약

| 항목 | 기존 QA Framework v2.0 | 새로운 Google Form 설계 | 차이 정도 |
|------|------------------------|------------------------|-----------|
| **평가 단위** | Set 단위 (group × arm) | Q01~Q12 (각 PDF 1개당 1섹션) | ⚠️ **중요 차이** |
| **폼 구조** | 한 화면 레이아웃 (PDF + Form) | 섹션형 Google Form (13섹션) | ⚠️ **중요 차이** |
| **블라인딩 방식** | Surrogate ID (set_id) | Q번호로 암묵적 결정 (섹션 자체) | ✅ **일치** |
| **데이터 결합** | reviewer_id + set_id | reviewer_id + local_qid (Q01~Q12) | ⚠️ **중요 차이** |
| **평가 항목** | Accuracy, Quality, Time 등 | Accuracy, Relevance, Clarity, Error, Time | ✅ **대부분 일치** |
| **배정 구조** | 1 Resident + 1 Attending per set | 동일 (1인당 12 set) | ✅ **일치** |
| **통계 분석** | Set 단위 paired 비교 | 코호트별 arm 비교 (group을 block) | ⚠️ **부분 차이** |

---

## 1. 평가 단위 (Unit of Analysis)

### 기존 QA Framework v2.0

- **평가 단위:** **Set** (= group × arm artifact bundle)
- **Set 구성:**
  - Master Table (또는 요약표)
  - Anki 카드 12장 (6 엔티티 × 2문항)
  - Infographic (있는 경우)
- **평가 방식:** Set 전체를 종합하여 평가
  - "Set 전체의 종합적 품질" (QA_Framework v2.0, Section 2.4)
  - 개별 카드 점수의 평균이 아님

### 새로운 Google Form 설계

- **평가 단위:** **Q01~Q12** (각각 하나의 Set을 의미)
  - **Q01 = Set 1** (12장 카드 묶음)
  - **Q02 = Set 2** (12장 카드 묶음)
  - ...
  - **Q12 = Set 12** (12장 카드 묶음)
- **구조:**
  - Section 1: 평가자 정보
  - Section 2~13: Q01~Q12 (각 Set당 1섹션)
- **평가 방식:** 각 Q 섹션별로 Set 전체를 종합 평가
  - Q번호는 섹션 자체로 암묵적으로 결정
  - 파일명이나 arm 정보 입력 없음
  - **1인당 총 12 Set 평가** (Q01~Q12)

### 차이점 분석

✅ **일치:**
- 기존: **Set 단위 종합 평가** (12장 카드를 하나의 단위로 평가)
- 새로운: **Q01~Q12 각각이 Set 단위** (각 Q는 하나의 Set을 의미)
- **평가 단위는 동일함**: Set 단위 종합 평가

**영향:**
- 통계 분석 단위는 동일: n = 108 sets (18 groups × 6 arms)
- 각 평가자당 12 Set 평가 (Q01~Q12)
- **블라인딩:** 각 평가자마다 배정된 PDF가 다름 (Q01~Q12의 실제 의미가 평가자마다 다를 수 있음)

---

## 2. 폼 구조 및 사용자 경험

### 기존 QA Framework v2.0

- **폼 구조:** 한 화면 레이아웃
  - 좌측: PDF (테이블, 인포그래픽, 안키 카드 12장)
  - 우측: 평가 설문 (S0_QA_Form_One-Screen_Layout.md)
- **제출 방식:** Set당 1회 제출
- **중간 저장:** 명시되지 않음 (Firebase 기반 웹 폼 가정)

### 새로운 Google Form 설계

- **폼 구조:** 섹션형 Google Form
  - Section 1: 평가자 정보
  - Section 2~13: Q01~Q12 (각 PDF 1개당 1섹션)
- **제출 방식:** 이어서 응답 가능 (자동 저장)
- **중간 저장:** Google Form 자동 저장 기능 활용

### 차이점 분석

⚠️ **중요 차이:**
- 기존: **한 화면 레이아웃** (PDF와 Form을 동시에 보면서 평가)
- 새로운: **섹션형 Form** (각 Q를 순차적으로 평가)

**장점 (새로운 설계):**
- ✅ 중간 저장 및 이어서 응답 가능 (평가자 피로도 관리)
- ✅ 웹 개발 없이 즉시 실행 가능 (Google Form 활용)
- ✅ 모바일 접근성 향상

**단점 (새로운 설계):**
- ⚠️ PDF와 Form을 동시에 보기 어려움 (섹션 간 이동 필요)
- ⚠️ Set 전체를 종합적으로 평가하기 어려울 수 있음
- ⚠️ "Set 전체의 종합적 품질" 평가 원칙과 충돌 가능

**권장 사항:**
- Google Form에서도 **PDF 링크를 각 섹션에 포함**하여 동시에 볼 수 있도록 설계 필요
- 또는 **Section 2~13을 하나의 긴 섹션**으로 구성하여 Set 전체를 한 번에 평가

---

## 3. 블라인딩 방식

### 기존 QA Framework v2.0

- **블라인딩 방식:** Surrogate ID 사용
  - `surrogate_set_id` (예: "X3", "Q7")
  - 실제 arm 정보 완전 차단
  - QA Blinding Procedure v2.0 준수

### 새로운 Google Form 설계

- **블라인딩 방식:** Q번호로 암묵적 결정
  - Q01~Q12는 섹션 자체로 결정
  - 파일명이나 arm 정보 입력 없음
  - **각 평가자 폴더 내에서 Q01~Q12의 의미는 서로 다를 수 있음**

### 차이점 분석

✅ **일치:**
- 두 설계 모두 **완전 블라인딩 유지**
- 평가자는 arm 정보를 알 수 없음
- 블라인딩 독립성에는 문제 없음

**새로운 설계의 장점:**
- ✅ Q번호만으로 암묵적 결정 (추가 ID 관리 불필요)
- ✅ 평가자가 ID를 입력할 필요 없음 (오류 방지)

**주의사항:**
- ⚠️ "각 평가자 폴더 내에서 Q01~Q12의 의미는 서로 다를 수 있음"이라는 점이 중요
- 이는 **assignment_map.csv**에서 각 평가자별로 다른 set이 Q01~Q12로 매핑됨을 의미
- 블라인딩 무결성 확보를 위해 이 매핑이 올바르게 관리되어야 함

---

## 4. 데이터 구조 및 결합

### 기존 QA Framework v2.0

- **데이터 구조:**
  - `reviewer_id` + `set_id` (surrogate)
  - Set 단위 평가 데이터
- **결합 키:**
  - `reviewer_id` + `set_id`
- **통계 분석:**
  - Set 단위 분석 (n = 108 sets)
  - Group을 random effect로 포함: `(1 | group)`

### 새로운 Google Form 설계

- **데이터 구조:**
  - Google Form 응답 CSV
  - `reviewer_id` + `local_qid` (Q01~Q12)
- **결합 키:**
  - `reviewer_id` + `local_qid` (Q01~Q12)
  - `assignment_map.csv`와 조인
- **통계 분석:**
  - 코호트별(전문의/전공의) arm 비교
  - Group을 block으로 한 paired 비교 또는 mixed model

### 차이점 분석

⚠️ **중요 차이:**
- 기존: **Set 단위 직접 매핑** (`reviewer_id` + `set_id`)
- 새로운: **Q번호를 통한 간접 매핑** (`reviewer_id` + `local_qid` → `assignment_map.csv` 조인)

**새로운 설계의 요구사항:**
- `assignment_map.csv`에 다음 컬럼이 필요:
  - `reviewer_id` (평가자 식별자)
  - `local_qid` (Q01~Q12, 평가자별 로컬 Q 번호)
  - **통계분석에 필요한 인식 ID** (set_id, group_id, arm_id 등)
  - `role` (resident/attending, 선택적)

**데이터 무결성:**
- ⚠️ 조인 과정에서 데이터 손실 가능성
- ⚠️ Q번호와 실제 set 매핑이 올바른지 검증 필요
- ⚠️ 각 평가자마다 Q01~Q12의 실제 의미가 다르므로 매핑 정확성 중요

---

## 5. 평가 항목 비교

### 기존 QA Framework v2.0

**Primary Endpoint:**
- Overall Card Quality (Likert 1–5) - **문서 간 불일치 있음** (QA_Plan_Review_Report.md 참고)
- 또는 Editing Time (minutes per set) - **일부 문서에서**

**Secondary Outcomes:**
- Accuracy (0/0.5/1.0) - **새 설계에는 없음**
- Blocking Error (Yes/No)
- Clarity & Readability (Likert 1–5)
- Clinical/Exam Relevance (Likert 1–5)
- Editing Time (minutes per set)

### 새로운 Google Form 설계

**평가 항목 (각 Q 섹션):**
- Accuracy: 1.0 / 0.5 / 0.0 ✅
- Clinical relevance: 1–5 ✅
- Clarity / readability: 1–5 ✅
- Major error 여부: 있음 / 없음 ✅ (Blocking Error와 동일)
- Editing time (분) ✅
- (선택) 자유 의견 ✅

### 차이점 분석

✅ **대부분 일치:**
- 평가 항목이 거의 동일함
- Accuracy, Quality, Clarity, Relevance, Error, Time 모두 포함

**차이점:**
- ⚠️ 기존: **Overall Card Quality** (Set 전체 종합 평가) - Primary Endpoint
- 새로운: **Overall Card Quality가 명시적으로 없음** (Accuracy, Relevance, Clarity만 있음)

**영향:**
- Q01~Q12는 각각 Set을 의미하므로, **Set 단위 평가는 동일함**
- 다만, **Overall Card Quality 지표가 빠져있음**
- Non-inferiority 분석의 Primary Endpoint가 누락될 수 있음

**권장 사항:**
- Google Form에 **"Overall Card Quality (1-5 Likert)" 문항 추가** 필요
- 또는 Accuracy, Relevance, Clarity를 종합하여 Overall Quality를 추정 (권장하지 않음)

---

## 6. 배정 구조 및 통계 분석

### 기존 QA Framework v2.0

- **배정 구조:**
  - 1 Resident + 1 Attending per set
  - 총 108 sets
  - 1인당 약 12–15 sets
- **통계 분석:**
  - Set 단위 paired 비교 (Resident–Attending)
  - Mixed-effects model: `outcome ~ arm + role + arm×role + (1|group) + (1|rater)`
  - Group을 random effect로 포함

### 새로운 Google Form 설계

- **배정 구조:**
  - 동일 (1인당 12 set = Q01~Q12)
- **통계 분석:**
  - 코호트별(전문의/전공의) arm 비교
  - Group을 block으로 한 paired 비교 또는 mixed model

### 차이점 분석

✅ **일치:**
- 배정 구조는 동일 (1인당 12 set)

⚠️ **부분 차이:**
- 기존: **Set 단위 분석** (n = 108 sets)
- 새로운: **코호트별 arm 비교** (group을 block)

**통계 분석 호환성:**
- 두 설계 모두 **mixed-effects model** 적용 가능
- Group을 block으로 하는 것은 기존 설계와 일치
- 다만, **평가 단위가 Set인지 Q인지**에 따라 분석 구조가 달라질 수 있음

---

## 7. 운영 방식 비교

### 기존 QA Framework v2.0

- **운영 방식:**
  - Firebase 기반 웹 폼 (QA_Website_Development_Tasks.md 참고)
  - 또는 PDF + 별도 Form
- **개발 필요:**
  - 웹 개발 필요 (Firebase QA 폴더 참고)
  - 로그인 시스템, 자동 배정 등

### 새로운 Google Form 설계

- **운영 방식:**
  - Google Form (웹 개발 없이 즉시 실행 가능)
  - 자동 저장 → 중간 저장 후 이어서 응답 가능
- **개발 필요:**
  - 웹 개발 불필요
  - Google Form 설정만으로 실행 가능

### 차이점 분석

✅ **새로운 설계의 장점:**
- ✅ 웹 개발 없이 즉시 실행 가능
- ✅ 중간 저장 및 이어서 응답 가능 (평가자 피로도 관리)
- ✅ Google 계정 로그인으로 접근 제어 가능
- ✅ Limit to 1 response로 중복 응답 방지

⚠️ **주의사항:**
- Google Form의 제한사항 고려 필요
  - PDF 첨부 방식 (링크 vs 직접 첨부)
  - 섹션 간 이동 시 컨텍스트 유지
  - 데이터 내보내기 및 분석 용이성

---

## 8. 핵심 질문 및 권장 사항

### 핵심 질문

1. **Q01~Q12의 정확한 의미는?**
   - Set 내의 12장 카드를 각각 의미하는가?
   - 아니면 12개의 서로 다른 Set을 의미하는가?
   - "각 PDF 1개당 1섹션"이라는 표현이 모호함

2. **평가 단위는 Set인가 Q인가?**
   - 기존 QA Framework는 **Set 단위 종합 평가**를 강조
   - 새로운 설계는 **Q별 개별 평가**로 보임
   - 통계 분석 단위와 일치시켜야 함

3. **Overall Card Quality는 어떻게 측정?**
   - 기존: Set 전체 종합 평가 (Primary Endpoint)
   - 새로운: 각 Q별 개별 평가 후 집계?
   - Set 단위 종합 점수 입력 섹션 추가 필요?

### 권장 사항

#### ✅ 호환 가능한 부분 (즉시 적용 가능)

1. **블라인딩 방식**
   - Q번호로 암묵적 결정 방식은 기존 설계와 호환
   - `assignment_map.csv` 관리만 올바르게 하면 됨

2. **평가 항목**
   - 평가 항목은 거의 동일하므로 호환 가능
   - 다만 Set 단위 종합 평가 섹션 추가 권장

3. **배정 구조**
   - 1인당 12 set 배정은 동일
   - 통계 분석 구조도 호환 가능

#### ⚠️ 수정 필요 부분

1. **평가 단위 명확화**
   - Q01~Q12가 Set 내의 12장 카드를 의미하는지 명확히 정의
   - Set 단위 종합 평가 원칙 유지 방법 제시

2. **폼 구조 개선**
   - Google Form에서도 Set 전체를 한 번에 볼 수 있도록 설계
   - PDF 링크를 각 섹션에 포함하거나, Set 전체 평가 섹션 추가

3. **데이터 구조 보완**
   - `assignment_map.csv` 구조 명확히 정의
   - 데이터 무결성 검증 절차 추가

4. **Overall Card Quality 측정**
   - Set 단위 종합 점수 입력 섹션 추가
   - 또는 Q01~Q12 평가 후 자동 집계 로직 정의

---

## 9. 결론

### 차이 정도 요약

**전체적으로: 새로운 설계는 기존 QA Framework의 핵심 원칙과 대부분 일치하지만, 운영 방식과 데이터 구조에서 중요한 차이가 있습니다.**

1. **블라인딩 및 배정 독립성:** ✅ **문제 없음**
   - 두 설계 모두 완전 블라인딩 유지
   - 배정 구조도 동일

2. **평가 단위:** ✅ **일치**
   - 기존: Set 단위 종합 평가
   - 새로운: Q01~Q12 각각이 Set을 의미 (평가 단위 동일)

3. **폼 구조:** ⚠️ **중요 차이**
   - 기존: 한 화면 레이아웃
   - 새로운: 섹션형 Google Form
   - 다만, Google Form에서도 Set 전체 평가 가능하도록 개선 가능

4. **운영 방식:** ✅ **새로운 설계의 장점**
   - 웹 개발 없이 즉시 실행 가능
   - 중간 저장 및 이어서 응답 가능

### 최종 권장 사항

**새로운 Google Form 설계는 기존 QA Framework와 호환 가능하지만, 다음 사항을 보완하면 더욱 완벽합니다:**

1. ✅ **Overall Card Quality 지표 추가**
   - Google Form에 "Overall Card Quality (1-5 Likert)" 문항 추가 필요
   - Non-inferiority 분석의 Primary Endpoint

2. ✅ **PDF 배포 방법 결정**
   - 이메일 + Google Drive 하이브리드 방식 권장
   - 평가자별 개별 PDF 폴더 생성 및 공유

3. ✅ **PDF 접근성 개선**
   - 각 섹션에 PDF 링크 포함
   - 또는 Set 전체를 한 번에 볼 수 있는 섹션 구성

4. ✅ **데이터 구조 명확화**
   - `assignment_map.csv` 구조 명확히 정의
   - 데이터 무결성 검증 절차 추가

**결론: 새로운 설계는 기존 QA Framework와 대부분 호환되며, 운영상의 장점이 많습니다. 다만, Overall Card Quality 지표 추가와 PDF 배포 방법 결정이 필요합니다.**

---

## 참고 문서

- QA Framework v2.0
- QA Assignment Plan v2.0
- QA Blinding Procedure v2.0
- S0 QA Form One-Screen Layout
- S0 QA Survey Questions v2.0
- QA Plan Review Report


# AppSheet Form에서 Display Name 표시하기

**문제:** AppSheet Form에서 설문 문항 제목(Display Name)이 안 나오고 Description만 보입니다.

---

## 원인

AppSheet Form에서는 기본적으로 **컬럼명(Column Name)**이 표시됩니다. Display Name을 표시하려면 Form 설정에서 명시적으로 설정해야 합니다.

---

## 해결 방법

### 방법 1: Form View에서 Label 설정 변경 (권장)

**AppSheet 메뉴 경로:** `UX` → `Views` → `[Form View 이름]` → 각 필드 설정

1. `UX` → `Views` 클릭
2. Form View 선택 (예: `Ratings_Form`)
3. 각 필드(컬럼)를 클릭
4. **`Label`** 섹션에서:
   - **`Label type`**: `Display name` 선택
   - 또는 **`Label`** 필드에 직접 Display Name 입력
5. `Save` 클릭

**참고:**
- `Label type`을 `Display name`으로 설정하면 컬럼의 Display Name이 자동으로 사용됩니다
- `Label` 필드에 직접 입력하면 해당 텍스트가 표시됩니다

---

### 방법 2: 컬럼의 Display Name 확인 및 설정

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `[컬럼명]`

1. `Data` → `Tables` → `Ratings` 클릭
2. 각 평가 항목 컬럼 클릭 (예: `blocking_error_pre`)
3. **`Display name`** 필드 확인:
   - 비어있으면 한국어 또는 영어 이름 입력
   - 예: `차단 오류 (Blocking Error)`
4. `Save` 클릭

**Display Name 예시:**
- `blocking_error_pre` → `차단 오류 (Blocking Error)`
- `technical_accuracy_pre` → `기술적 정확도 (Technical Accuracy)`
- `educational_quality_pre` → `교육적 품질 (Educational Quality)`
- `evidence_comment_pre` → `증거/코멘트 (Evidence/Comment)`

---

### 방법 3: Form View 전체 설정 확인

**AppSheet 메뉴 경로:** `UX` → `Views` → `[Form View 이름]` → `Options`

1. `UX` → `Views` → Form View 클릭
2. `Options` 탭 클릭
3. **`Show labels`** 옵션이 활성화되어 있는지 확인
4. 활성화되어 있지 않으면 체크박스 활성화
5. `Save` 클릭

---

## Form View에서 Label vs Description

### Label (제목)
- **위치**: 필드 위에 큰 글씨로 표시
- **설정**: Form View의 각 필드에서 `Label` 설정
- **권장**: Display Name 사용

### Description (설명)
- **위치**: Label 아래 작은 글씨 또는 정보 아이콘(ℹ️)으로 표시
- **설정**: 컬럼의 `Description` 필드
- **용도**: 추가 설명이나 가이드라인

---

## 단계별 설정 가이드

### Step 1: 컬럼 Display Name 설정

각 평가 항목 컬럼에 Display Name을 설정합니다:

**예시:**
```
blocking_error_pre → "차단 오류 (Blocking Error)"
technical_accuracy_pre → "기술적 정확도 (Technical Accuracy)"
educational_quality_pre → "교육적 품질 (Educational Quality)"
evidence_comment_pre → "증거/코멘트 (Evidence/Comment)"
```

### Step 2: Form View Label 설정

Form View의 각 필드에서 Label을 Display Name으로 설정:

1. Form View 열기
2. 각 필드 클릭
3. `Label type` = `Display name` 선택
4. 또는 `Label` 필드에 직접 텍스트 입력

### Step 3: Description 설정 (선택사항)

Description은 Label 아래에 작은 글씨로 표시되거나 정보 아이콘으로 표시됩니다:

1. 컬럼 설정에서 `Description` 필드에 설명 입력
2. Form View에서 `Show description` 옵션 활성화 (있는 경우)

---

## 확인 방법

1. **앱 미리보기**에서 Form View 열기
2. 각 필드 위에 **큰 글씨로 제목(Label)**이 표시되는지 확인
3. 제목 아래 또는 옆에 **작은 글씨로 설명(Description)**이 표시되는지 확인

**예상 결과:**
```
┌─────────────────────────────────────┐
│ 차단 오류 (Blocking Error)          │  ← Label (큰 글씨)
│ 학습자나 임상 판단을 잘못 유도할 수  │  ← Description (작은 글씨)
│ 있는 사실 오류가 있습니까?          │
│                                     │
│ [ ] Yes  [ ] No                     │
└─────────────────────────────────────┘
```

---

## 문제 해결 체크리스트

- [ ] 컬럼의 `Display name`이 설정되어 있는가?
- [ ] Form View의 각 필드에서 `Label type`이 `Display name`으로 설정되어 있는가?
- [ ] Form View의 `Show labels` 옵션이 활성화되어 있는가?
- [ ] 앱 미리보기에서 Label이 표시되는지 확인했는가?

---

## 추가 팁

### Label을 다르게 표시하고 싶은 경우

Form View에서 `Label` 필드에 직접 텍스트를 입력하면, 컬럼의 Display Name과 다르게 표시할 수 있습니다:

**예시:**
- 컬럼 Display Name: `blocking_error_pre`
- Form Label: `이 카드에 차단 오류가 있습니까?`

이렇게 하면 Form에서만 다른 제목을 사용할 수 있습니다.

---

## 참고 문서

- **컬럼 설명 가이드**: `AppSheet_Column_Descriptions.md`
  - Section 3: 평가 항목별 Display Name 및 Description 제안
  - Section 5: AppSheet 설정 방법

---

**문서 버전:** 1.0  
**최종 업데이트:** 2025-01-01


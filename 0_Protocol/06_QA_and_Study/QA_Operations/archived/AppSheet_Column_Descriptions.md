# AppSheet 컬럼 설명 및 Display Name 가이드

**작성일:** 2025-01-01  
**목적:** AppSheet 앱에서 사용되는 컬럼들의 용도 설명 및 사용자 친화적 Display Name 제안

---

## 1. Ratings 테이블 컬럼 용도 설명

### 1.1 Change Log 관련 컬럼

#### `change_reason_code` (Enum)
**용도:** Post 평가에서 Pre 평가와 다른 점수를 준 경우, 변경 이유를 분류하는 코드

**Enum 옵션 (7개):**
- `S5_BLOCKING_FLAG`: S5 결과에서 blocking error를 발견하여 변경
- `S5_BLOCKING_FALSE_POS`: S5 결과에서 blocking error가 false positive였음을 확인하여 변경
- `S5_QUALITY_INSIGHT`: S5 결과가 품질 평가에 도움을 주어 변경
- `S5_EVIDENCE_HELPED`: S5 결과의 증거가 도움을 주어 변경
- `S5_NO_EFFECT`: S5 결과를 봤지만 변경 없음 (변경 로그는 필요 없지만, 시스템상 기록)
- `RATER_REVISION`: 평가자 본인의 재검토로 인한 변경 (S5와 무관)
- `OTHER`: 기타 사유

**사용 시점:**
- Post 평가 제출 시 `is_changed = TRUE`인 경우 필수 입력
- "Submit Post-S5 Rating" 액션의 `Run_If`에서 강제됨

**AppSheet 설정:**
- **`Editable_If`**: 
  ```
  [is_changed]
  ```
  **설명:** 변경이 있을 때만 편집 가능

- **`Required_If`**: 
  ```
  [is_changed]
  ```
  **설명:** 변경이 있을 때 필수 입력

**Display Name 제안:**
- 한국어: `변경 이유 코드`
- 영어: `Change Reason Code`

**Description 제안:**
```
Post 평가에서 Pre 평가와 다른 점수를 준 경우, 변경 이유를 선택하세요.
S5 결과를 확인한 후 평가를 변경한 이유를 분류합니다.
변경이 있을 때만 입력 가능하며 필수입니다.
```

---

#### `change_note` (LongText)
**용도:** `change_reason_code`가 "OTHER"일 때만 입력하는 변경 사유 상세 설명

**사용 시점:**
- `change_reason_code = "OTHER"`인 경우에만 입력
- 다른 코드를 선택한 경우에는 입력 불필요

**AppSheet 설정:**
- **`Editable_If`**: 
  ```
  AND(
    [is_changed],
    [change_reason_code] = "OTHER"
  )
  ```
  **설명:** 변경이 있고, change_reason_code가 "OTHER"일 때만 편집 가능

- **`Required_If`**: 
  ```
  AND(
    [is_changed],
    [change_reason_code] = "OTHER"
  )
  ```
  **설명:** change_reason_code가 "OTHER"일 때 필수 입력

**Display Name 제안:**
- 한국어: `변경 사유 상세 (기타)`
- 영어: `Change Note (Other Details)`

**Description 제안:**
```
변경 이유 코드가 "기타(OTHER)"인 경우에만 입력하세요.
변경 사유를 자세히 설명해주세요.
```

---

#### `changed_fields` (Text, Virtual Column)
**용도:** Pre와 Post 평가 간에 실제로 변경된 필드 목록을 자동으로 기록 (시스템 자동 생성)

**기록되는 필드:**
- `blocking_error_pre` ↔ `blocking_error_post`
- `technical_accuracy_pre` ↔ `technical_accuracy_post`
- `educational_quality_pre` ↔ `educational_quality_post`
- `evidence_comment_pre` ↔ `evidence_comment_post`
- `image_blocking_error_pre` ↔ `image_blocking_error_post`
- `image_anatomical_accuracy_pre` ↔ `image_anatomical_accuracy_post`
- `image_quality_pre` ↔ `image_quality_post`
- `image_text_consistency_pre` ↔ `image_text_consistency_post`

**AppSheet 설정:**
- **Type**: `Virtual` (읽기 전용)
- **Virtual column expression**:
  ```
  IF(
    [post_is_complete],
    TRIM(
      CONCATENATE(
        IF([blocking_error_pre] <> [blocking_error_post], "blocking_error, ", ""),
        IF([technical_accuracy_pre] <> [technical_accuracy_post], "technical_accuracy, ", ""),
        IF([educational_quality_pre] <> [educational_quality_post], "educational_quality, ", ""),
        IF([evidence_comment_pre] <> [evidence_comment_post], "evidence_comment, ", ""),
        IF([image_blocking_error_pre] <> [image_blocking_error_post], "image_blocking_error, ", ""),
        IF([image_anatomical_accuracy_pre] <> [image_anatomical_accuracy_post], "image_anatomical_accuracy, ", ""),
        IF([image_quality_pre] <> [image_quality_post], "image_quality, ", ""),
        IF([image_text_consistency_pre] <> [image_text_consistency_post], "image_text_consistency", "")
      )
    ),
    ""
  )
  ```
  **설명:**
  - `post_is_complete` 가드로 Post가 완결된 뒤에만 변경 판단을 수행합니다
  - 각 필드가 변경되었는지 체크하고, 변경된 필드 이름을 콤마로 구분하여 나열합니다
  - `TRIM()`으로 마지막 콤마와 공백을 제거합니다
  - 변경이 없으면 빈 문자열("")을 반환합니다

**AppSheet 설정 단계:**
1. `Data` → `Tables` → `Ratings` → `+ Add column`
2. 컬럼명: `changed_fields`
3. `Type`: `Virtual` 선택
4. `Virtual column expression`에 위의 formula 입력
5. `Editable`: 체크 해제 (읽기 전용)
6. `Save` 클릭

**사용 시점:**
- 시스템이 자동으로 계산 (Virtual Column)
- 분석 시 어떤 필드가 변경되었는지 추적용

**Display Name 제안:**
- 한국어: `변경된 필드 목록` (읽기 전용)
- 영어: `Changed Fields` (Read-only)

**Description 제안:**
```
Pre와 Post 평가 간에 변경된 필드 목록입니다.
시스템이 자동으로 계산하며, 분석 시 참고용으로 사용됩니다.
예: "blocking_error, technical_accuracy"
```

---

### 1.2 Flag 관련 컬럼

#### `flag_followup` (Yes/No)
**용도:** 평가자가 해당 케이스를 나중에 다시 검토하거나 관리자에게 확인이 필요한 경우 표시하는 플래그

**사용 시나리오:**
- 평가 중 불확실한 부분이 있어 나중에 다시 확인하고 싶을 때
- 데이터 품질 이슈나 시스템 오류가 의심될 때
- 추가 검토가 필요한 케이스로 표시하고 싶을 때

**Editable_If:**
```
[rater_email] = USEREMAIL()
```

**Display Name 제안:**
- 한국어: `후속 조치 필요`
- 영어: `Flag for Follow-up`

**Description 제안:**
```
이 케이스를 나중에 다시 검토하거나 관리자에게 확인이 필요한 경우 체크하세요.
체크하면 "MyFlagged" 목록에서 확인할 수 있습니다.
```

---

#### `flag_note` (LongText)
**용도:** `flag_followup = TRUE`인 경우, 왜 플래그를 설정했는지 이유를 기록

**Editable_If:**
```
AND(
  [rater_email] = USEREMAIL(),
  [flag_followup] = TRUE
)
```

**Display Name 제안:**
- 한국어: `플래그 메모`
- 영어: `Flag Note`

**Description 제안:**
```
후속 조치가 필요한 이유를 자세히 설명하세요.
이 메모는 관리자가 문제를 파악하는 데 도움이 됩니다.
```

---

### 1.3 Admin Undo 관련 컬럼

#### `admin_undo_pre_submitted_ts` (Date/Time)
**용도:** 관리자가 실수로 제출된 Pre 평가를 되돌린 시각을 기록 (감사 추적용)

**사용 시나리오:**
- 평가자가 실수로 "Submit Pre-S5 Rating" 버튼을 눌러 Pre 필드가 잠긴 경우
- 관리자가 "Admin: Undo Pre Submission" 액션을 실행하면 이 컬럼에 현재 시각이 기록됨
- `pre_submitted_ts`는 `BLANK()`로 되돌려짐

**중요:**
- `pre_started_ts`는 유지됨 (시간 측정 데이터 보존)
- 관리자 전용 기능

**Display Name 제안:**
- 한국어: `Pre 제출 취소 시각` (관리자 전용)
- 영어: `Pre Submission Undo Timestamp` (Admin only)

**Description 제안:**
```
관리자가 Pre 평가 제출을 취소한 시각입니다.
데이터 무결성 감사 추적용으로 사용됩니다.
```

---

#### `admin_undo_post_submitted_ts` (Date/Time)
**용도:** 관리자가 실수로 제출된 Post 평가를 되돌린 시각을 기록 (감사 추적용)

**사용 시나리오:**
- 평가자가 실수로 "Submit Post-S5 Rating" 버튼을 눌러 Post 필드가 잠긴 경우
- 관리자가 "Admin: Undo Post Submission" 액션을 실행하면 이 컬럼에 현재 시각이 기록됨
- `post_submitted_ts`는 `BLANK()`로 되돌려짐

**중요:**
- `post_started_ts`는 유지됨 (시간 측정 데이터 보존)
- 관리자 전용 기능

**Display Name 제안:**
- 한국어: `Post 제출 취소 시각` (관리자 전용)
- 영어: `Post Submission Undo Timestamp` (Admin only)

**Description 제안:**
```
관리자가 Post 평가 제출을 취소한 시각입니다.
데이터 무결성 감사 추적용으로 사용됩니다.
```

---

#### `undo_reason` (LongText)
**용도:** 관리자가 Pre/Post 제출을 취소한 이유를 기록

**사용 시나리오:**
- "Admin: Undo Pre/Post Submission" 액션 실행 시 관리자가 취소 이유를 입력
- 데이터 무결성 감사 추적용

**Display Name 제안:**
- 한국어: `제출 취소 사유` (관리자 전용)
- 영어: `Undo Reason` (Admin only)

**Description 제안:**
```
제출 취소 사유를 기록하세요.
데이터 무결성 감사 추적용으로 사용됩니다.
```

---

## 2. Assignments 테이블 Display Name 및 Description 제안

### 2.1 `assignment_id`
**Display Name:**
- 한국어: `배정 ID`
- 영어: `Assignment ID`

**Description:**
```
이 배정의 고유 식별자입니다.
시스템이 자동으로 생성하며, 중복을 방지하는 데 사용됩니다.
```

---

### 2.2 `rater_email`
**Display Name:**
- 한국어: `평가자 이메일`
- 영어: `Rater Email`

**Description:**
```
이 케이스를 평가할 평가자의 이메일 주소입니다.
평가자가 로그인하면 자동으로 자신의 이메일과 매칭됩니다.
```

---

### 2.3 `card_uid`
**Display Name:**
- 한국어: `카드 고유 ID`
- 영어: `Card UID`

**Description:**
```
평가할 카드의 고유 식별자입니다.
Cards 테이블의 card_uid와 연결됩니다.
```

---

### 2.4 `assignment_order`
**Display Name:**
- 한국어: `평가 순서`
- 영어: `Assignment Order`

**Description:**
```
이 평가자가 이 케이스를 평가할 순서 번호입니다.
1부터 시작하며, 평가자는 이 순서대로 평가를 진행합니다.
```

---

### 2.5 `batch_id`
**Display Name:**
- 한국어: `배치 ID`
- 영어: `Batch ID`

**Description:**
```
이 배정이 속한 배치의 식별자입니다.
여러 배치를 구분하거나 배치별로 분석할 때 사용됩니다.
```

---

## 3. 평가 항목별 AppSheet Description (간결 버전)

**⚠️ 중요:** 아래 Description은 AppSheet 앱에서 표시될 간결한 버전입니다.  
**자세한 평가 가이드는 Section 4 "평가 항목 상세 안내문"을 참고하세요.**

### 3.1 Pre/Post 평가 항목

> **⚠️ 중요**: Pre 평가와 Post 평가는 **동일한 기준**을 사용합니다. 평가 시점에 따라 기준이 달라지지 않습니다.

#### 3.1.1 `blocking_error_pre/post` (Yes/No)

**Display Name:**
- 한국어: `차단 오류 (Blocking Error)`
- 영어: `Blocking Error`

**AppSheet Description (간결 버전):**
```
학습자나 임상 판단을 잘못 유도할 수 있는 사실 오류가 있습니까?
Yes인 경우 evidence_comment에 구체적인 이유를 반드시 작성하세요.
```

**상세 안내:** Section 4.1 참고

---

#### 3.1.2 `technical_accuracy_pre/post` (Enum: 0, 0.5, 1)

**Display Name:**
- 한국어: `기술적 정확도 (Technical Accuracy)`
- 영어: `Technical Accuracy`

**AppSheet Description (간결 버전):**
```
1.0=완전 정확(수정 불필요), 0.5=부분 정확(보완 필요), 0.0=부정확(수정 필수)
핵심 개념과 설명의 사실적 정확성과 임상적 타당성을 평가하세요.
```

**상세 안내:** Section 4.2 참고

---

#### 3.1.3 `educational_quality_pre/post` (Enum: 1-5)

**Display Name:**
- 한국어: `교육적 품질 (Educational Quality)`
- 영어: `Educational Quality`

**AppSheet Description (간결 버전):**
```
방사선학 레지던트 훈련/보드 시험에 대한 교육적 가치를 평가하세요.
5=핵심 시험 개념을 직접 다루는 매우 가치 있는 내용, 4=가치 있는 내용, 3=보통, 2=가치 낮음, 1=학습에 도움이 되지 않을 가능성 높음
정확성, 가독성, 교육 목표 달성도, 시험 적합성을 종합적으로 평가하세요.
```

**상세 안내:** Section 4.3 참고

---

#### 3.1.4 `evidence_comment_pre/post` (LongText)

**Display Name:**
- 한국어: `증거/코멘트 (Evidence/Comment)`
- 영어: `Evidence/Comment`

**AppSheet Description (간결 버전):**
```
blocking_error=Yes 또는 educational_quality≤2인 경우 필수입니다.
최악의 문제가 있는 카드 1-2장에 대한 근거를 1줄 이내로 간결하게 작성하세요.
```

**상세 안내:** Section 4.4 참고

---

## 3.2 이미지 평가 항목 (S5 비교용)

**⚠️ 중요:** 아래 항목들은 S5(LLM)가 평가한 이미지 품질과 비교하기 위한 사람 평가 항목입니다.  
**평가 시점:** Post 평가 단계에서 S5 결과를 확인한 후, 이미지를 직접 보고 평가하세요.  
**평가 기준:** Pre 평가와 Post 평가에서 **동일한 기준**을 사용합니다.

#### 3.2.1 `image_blocking_error_pre/post` (Yes/No)

**Display Name:**
- 한국어: `이미지 차단 오류 (Image Blocking Error)`
- 영어: `Image Blocking Error`

**AppSheet Description (간결 버전):**
```
이미지에 학습자나 임상 판단을 잘못 유도할 수 있는 심각한 오류가 있습니까?
모달리티 불일치, 좌우 구분 오류, 심각한 해부학적 오류 등을 체크하세요.
```

**상세 안내:** Section 4.6 참고

---

#### 3.2.2 `image_anatomical_accuracy_pre/post` (Enum: 0, 0.5, 1)

**Display Name:**
- 한국어: `이미지 해부학적 정확도`
- 영어: `Image Anatomical Accuracy`

**AppSheet Description (간결 버전):**
```
이미지의 해부학적 구조가 의학적으로 정확합니까?
1.0=완전 정확, 0.5=부분 정확(보완 필요), 0.0=부정확(수정 필수)
```

**상세 안내:** Section 4.7 참고

---

#### 3.2.3 `image_quality_pre/post` (Enum: 1-5)

**Display Name:**
- 한국어: `이미지 품질`
- 영어: `Image Quality`

**AppSheet Description (간결 버전):**
```
이미지의 해상도, 가독성, 대비, 아티팩트를 종합 평가하세요.
5=매우 좋음, 4=좋음, 3=보통, 2=나쁨, 1=매우 나쁨
```

**상세 안내:** Section 4.8 참고

---

#### 3.2.4 `image_text_consistency_pre/post` (Enum: 0, 0.5, 1)

**Display Name:**
- 한국어: `이미지-텍스트 일관성`
- 영어: `Image-Text Consistency`

**AppSheet Description (간결 버전):**
```
이미지가 카드의 front/back 텍스트와 일치하고 진단/소견을 뒷받침합니까?
1.0=완전 일치, 0.5=대체로 일치(일부 불일치), 0.0=불일치(수정 필요)
```

**상세 안내:** Section 4.9 참고

---

## 4. 평가 항목 상세 안내문 (평가자용)

**이 섹션은 평가자 안내 문서로 별도 제공하거나, 앱 내 도움말로 연결할 수 있습니다.**

### 4.1 `blocking_error_pre/post` 상세 가이드

#### 정의
**차단 오류(Blocking Error)**란 학습자나 임상 판단을 직접적으로 잘못 유도할 가능성이 큰 사실 오류입니다.

#### 평가 기준

**Yes (차단 오류 있음):**
- 사실 오류가 있어 학습자나 임상 판단을 잘못 유도할 가능성이 큰 경우
- 시험 정답을 직접적으로 잘못 유도할 수 있는 오류
- 해부학적 위치, 병리 소견, 진단 기준 등 핵심 사실이 잘못된 경우

**No (차단 오류 없음):**
- 사실 오류가 없는 경우
- 오류가 있어도 학습 목표 달성에 큰 영향을 주지 않는 경우
- 표현이 다소 모호하거나 개선 여지가 있으나 사실 오류는 아닌 경우

#### 예시

**차단 오류가 있는 경우:**
- "MRI DWI 고신호를 T2 shine-through로 오해 → 진단 오류 위험"
- "PE CT 소견에서 filling defect를 정상으로 기술"
- "좌심실을 우심실로 표시" (해부학적 위치 오류)
- "급성 심근경색의 ST 상승을 정상으로 기술"

**차단 오류가 아닌 경우:**
- 표현이 다소 모호하나 사실은 정확한 경우
- 설명이 불완전하나 잘못된 정보는 아닌 경우
- 개선 여지가 있으나 학습 목표 달성에는 문제 없는 경우

#### 주의사항
- Yes를 선택한 경우, 반드시 `evidence_comment`에 구체적인 이유를 설명해야 합니다.
- 차단 오류는 "심각한 문제"와는 다릅니다. 사실 오류에 집중하세요.

---

### 4.2 `technical_accuracy_pre/post` 상세 가이드

#### 정의
**기술적 정확도(Technical Accuracy)**는 핵심 개념과 설명의 사실적 정확성과 임상적 타당성을 평가합니다.

#### 점수별 평가 기준

**1.0 (완전 정확)**
- 핵심 개념과 설명이 완전히 정확함
- 전문의 자격시험 수준의 학습에 적합
- 수정 없이 사용 가능
- 임상적으로 타당하고 사실적으로 정확함

**0.5 (부분 정확)**
- 핵심 개념은 정확하지만, 설명에 다음 중 하나 이상이 있음:
  - 작은 누락 (minor omissions)
  - 부정확한 표현 (imprecise phrasing)
  - 누락된 뉘앙스 (missing nuance)
- 전반적으로 정확하지만 일부 보완이 필요함
- 교육 자료로 사용 가능하나 개선 권장

**0.0 (부정확)**
- 핵심 개념이 잘못되었거나 오해의 소지가 있음
- 학습자에게 오해를 일으킬 가능성이 높음
- 수정이 반드시 필요함
- 사실 오류가 있어 교육 자료로 부적합

#### 평가 시 고려사항
- **핵심 개념**: 카드가 다루는 주요 의학적 개념이 정확한가?
- **설명의 정확성**: 설명이 사실에 부합하는가?
- **임상적 타당성**: 임상 현장에서 적용 가능한가?
- **오해의 소지**: 학습자가 잘못 이해할 가능성이 있는가?

#### 예시

**1.0 예시:**
- "급성 심근경색의 ST 상승 소견을 정확히 설명"
- "DWI 고신호의 임상적 의미를 정확히 기술"
- "해부학적 구조를 정확히 표시하고 설명"

**0.5 예시:**
- "핵심 개념은 정확하나, 예외 상황에 대한 설명이 누락됨"
- "대부분 정확하나, 일부 용어가 부정확하게 사용됨"
- "전반적으로 정확하나, 뉘앙스가 부족함"

**0.0 예시:**
- "DWI 고신호를 T2 shine-through로 잘못 설명"
- "해부학적 위치가 잘못 표시됨"
- "진단 기준이 잘못 기술됨"

---

### 4.3 `educational_quality_pre/post` 상세 가이드

#### 정의
**교육적 품질(Educational Quality)**은 방사선학 레지던트 훈련 및 보드 시험에 대한 교육적 가치를 평가합니다. 정확성, 가독성, 교육 목표 달성도, 시험 적합성을 종합적으로 고려합니다.

#### 점수별 평가 기준

**5 (매우 가치 있는 내용)**
- 핵심 시험 개념을 직접적으로 다루는 매우 가치 있는 내용
- 보드 시험에 직접적으로 도움이 되는 내용
- 정확성, 가독성, 교육 목표 달성 모두 우수
- 전문의 교육 자료로 즉시 사용 가능
- 모범 사례 수준

**4 (가치 있는 내용)**
- 보드 시험에 유용한 내용
- 대체로 우수하나, 일부 개선 여지 있음
- 교육 자료로 사용 가능
- 소폭 개선 시 완벽
- 전반적으로 만족스러움

**3 (보통)**
- 기본 요건은 충족하나, 개선이 필요함
- 교육 자료로 사용 가능하나 개선 권장
- 중간 수준
- 일부 문제점이 있으나 사용 가능

**2 (가치 낮음)**
- 여러 문제점이 있어 개선이 필요함
- 교육 자료로 사용하기에는 부족
- 상당한 수정 필요
- 사용 가능하나 권장하지 않음

**1 (학습에 도움이 되지 않을 가능성 높음)**
- 심각한 문제가 있어 사용 불가
- 전면적 수정 또는 재작성 필요
- 교육 자료로 부적합
- 즉시 수정이 반드시 필요함

#### 평가 시 고려사항

**정확성 (Accuracy)**
- 사실적 정확성
- 임상적 타당성
- 오류의 유무

**가독성 (Readability)**
- 문장의 명확성
- 구조의 논리성
- 이해하기 쉬운 정도

**교육 목표 달성도 (Educational Goal Achievement)**
- 학습 목표를 달성하는가?
- 교육적 가치가 있는가?
- 학습자에게 도움이 되는가?

**시험 적합성 (Exam Fitness)**
- 보드 시험에 직접적으로 도움이 되는가?
- 핵심 시험 개념을 다루는가?
- 시험 스타일에 적합한가?

#### 종합 평가 팁
- 네 가지 요소(정확성, 가독성, 교육 목표, 시험 적합성)를 모두 고려하되, 정확성이 가장 중요합니다.
- 시험 적합성은 방사선학 레지던트 훈련/보드 시험에 대한 가치를 평가하는 핵심 요소입니다.
- 정확성에 심각한 문제가 있으면 2 이하로 평가하세요.
- 전반적으로 우수하나 작은 개선 여지가 있으면 4로 평가하세요.

---

### 4.4 `evidence_comment_pre/post` 상세 가이드

#### 작성 조건

**필수 작성:**
- `blocking_error = Yes`인 경우
- `educational_quality ≤ 2`인 경우

**선택 작성:**
- 그 외의 경우 (특이사항이 있는 경우에만)

#### 작성 가이드

**원칙:**
- 최악의 문제가 있는 카드 1-2장에 대한 근거만 작성
- 각 카드당 1줄 이내로 간결하게 작성
- 구체적인 문제점을 명시

**작성 형식:**
- "Q1: [문제점] → [영향]"
- "Q2: [문제점]"
- "[카드 식별자]: [문제점]"

#### 예시

**좋은 예시:**
- "Q1: DWI 고신호를 T2 shine-through로 오해 → 진단 오류 위험"
- "Q2: 해부학적 위치 오류 (좌심실을 우심실로 표시)"
- "전반적으로 설명이 모호하여 학습 목표 달성 어려움"

**나쁜 예시:**
- "문제가 많음" (너무 모호함)
- "Q1, Q2, Q3 모두 문제가 있음" (구체적이지 않음)
- "좀 더 개선이 필요함" (구체적인 문제점이 없음)

#### 주의사항
- 모든 문제를 나열할 필요는 없습니다. 가장 중요한 문제만 기록하세요.
- 문제점을 구체적으로 명시하되, 간결하게 작성하세요.
- 평가 근거가 명확해야 나중에 검토할 때 도움이 됩니다.

---

### 4.5 평가 시 전반적 주의사항

> **⚠️ 중요**: Pre 평가와 Post 평가는 **동일한 기준**을 사용합니다. 평가 시점에 따라 평가 기준이 달라지지 않습니다.

#### Pre 평가 (S5 결과 확인 전)

**중요 원칙:**
- Pre 평가는 S5 결과를 보기 전에 순수하게 카드 내용만 보고 평가합니다
- Pre 평가는 제출 후 변경할 수 없습니다 (immutable)
- Pre 평가 결과가 모든 분석의 기준이 됩니다
- **평가 기준은 Post 평가와 동일합니다** (시점만 다를 뿐 기준은 같음)

**평가 원칙:**
1. **객관적으로 평가**: 개인적 선호도보다는 사실적 정확성과 교육적 가치에 집중
2. **일관성 유지**: 유사한 문제는 유사하게 평가
3. **시간 효율**: 빠르게 판단하되, 정확성은 유지

#### Post 평가 (S5 결과 확인 후)

**중요 원칙:**
- S5 결과를 확인한 후, 필요시 Pre 평가를 수정할 수 있습니다
- 변경한 경우 반드시 `change_reason_code`와 `change_note`를 작성해야 합니다
- Post 평가는 도구 효과 측정용이며, arm 비교 분석에는 사용되지 않습니다
- **평가 기준은 Pre 평가와 동일합니다** (S5 결과를 참고할 수 있을 뿐 기준은 같음)

**변경 시 고려사항:**
1. S5 결과가 도움이 되었는지 판단
2. S5 결과를 바탕으로 평가를 변경할 충분한 이유가 있는지 확인
3. 변경 이유를 명확히 기록

#### 일반적인 평가 팁

**일관성 유지:**
- 유사한 문제는 유사하게 평가하세요
- 평가 기준을 일관되게 적용하세요

**객관성 유지:**
- 개인적 선호도보다는 사실적 정확성에 집중하세요
- 교육적 가치를 우선 고려하세요

**효율성:**
- 빠르게 판단하되, 정확성은 유지하세요
- 불필요한 코멘트는 작성하지 마세요

---

### 4.6 `image_blocking_error_pre/post` 상세 가이드

#### 정의
**이미지 차단 오류(Image Blocking Error)**는 이미지에 학습자나 임상 판단을 직접적으로 잘못 유도할 가능성이 큰 심각한 오류가 있는지를 평가합니다.

#### 평가 기준

**Yes (차단 오류 있음):**
- **모달리티 불일치**: 카드 텍스트에서 언급한 모달리티(CT, MRI, US 등)와 이미지의 실제 모달리티가 다름
  - 예: 카드에서 "CT 영상"이라고 했으나 이미지는 "US 영상"
- **좌우 구분 오류**: Axial convention이 잘못되어 좌우가 반대로 표시됨
  - 예: viewer-left = patient-left로 잘못 표시 (올바른 convention: viewer-left = patient-right)
- **심각한 해부학적 오류**: 해부학적 구조가 명백히 잘못되어 진단 오류 위험이 있음
  - 예: 좌심실을 우심실로 표시, 해부학적 위치가 완전히 잘못됨
- **안전성 문제**: 부적절한 내용이나 환자 식별 정보 포함

**No (차단 오류 없음):**
- 이미지에 심각한 오류가 없음
- 모달리티가 일치함
- 좌우 구분이 정확함
- 해부학적 구조가 정확하거나, 오류가 있어도 학습 목표 달성에 큰 영향을 주지 않음

#### S5와의 비교
- S5는 `card_image_validation.blocking_error`로 이미지 blocking error를 평가합니다
- S5가 체크하는 주요 항목:
  - 모달리티 불일치 (`modality_mismatch`)
  - 좌우 구분 오류 (`laterality_error`)
  - 심각한 해부학적 오류 (`anatomical_accuracy=0.0`)

#### 예시

**Yes (차단 오류) 예시:**
- "카드에서 'CT 영상'이라고 했으나 이미지는 'US 영상'임"
- "Axial convention이 잘못되어 좌우가 반대로 표시됨"
- "좌심실을 우심실로 잘못 표시하여 진단 오류 위험"

**No (차단 오류 없음) 예시:**
- "모달리티가 일치하고 해부학적 구조가 정확함"
- "일부 랜드마크가 누락되었으나 심각한 오류는 아님"
- "해상도가 다소 낮으나 해석에는 문제 없음"

#### 주의사항
- 이미지 blocking error는 **카드 텍스트의 blocking error와는 별개**입니다
- 이미지만 보고 판단하되, 카드 텍스트와의 일관성도 고려하세요
- Yes를 선택한 경우, `evidence_comment_post`에 구체적인 이유를 기록하는 것을 권장합니다

---

### 4.7 `image_anatomical_accuracy_pre/post` 상세 가이드

#### 정의
**이미지 해부학적 정확도(Image Anatomical Accuracy)**는 이미지에 표시된 해부학적 구조가 의학적으로 정확한지를 평가합니다.

#### 점수별 평가 기준

**1.0 (완전 정확)**
- 해부학적 구조가 의학적으로 완전히 정확함
- 필수 랜드마크가 모두 표시되어 있음
- 좌우 구분(Laterality)이 명확하고 정확함
- 해부학적 관계가 정확하게 표현됨

**0.5 (부분 정확)**
- 핵심 해부학적 구조는 정확하나, 일부 랜드마크가 누락되거나 불명확함
- 해부학적 관계는 대체로 정확하나 일부 표현이 모호함
- 좌우 구분은 있으나 다소 불명확함
- 전반적으로 정확하나 일부 보완 필요

**0.0 (부정확)**
- 해부학적 구조가 잘못 표시됨
- 필수 랜드마크가 누락되어 해석이 어려움
- 좌우 구분이 잘못되었거나 혼란스러움
- 해부학적 관계가 잘못 표현되어 오해의 소지가 있음
- 수정이 반드시 필요함

#### 평가 시 고려사항
- **필수 랜드마크**: 이미지에 표시되어야 할 핵심 해부학적 구조가 모두 있는가?
- **좌우 구분**: Axial convention (viewer-left = patient-right)이 정확한가?
- **해부학적 관계**: 구조 간의 관계가 정확하게 표현되었는가?
- **의학적 정확성**: 전문의가 보기에 해부학적으로 타당한가?

#### 예시

**1.0 예시:**
- "심장의 4개 방이 정확히 표시되고, 대혈관 관계가 명확함"
- "뇌 구조가 정확하고, 좌우 구분이 명확함"
- "해부학적 랜드마크가 모두 정확하게 표시됨"

**0.5 예시:**
- "핵심 구조는 정확하나, 일부 세부 랜드마크가 누락됨"
- "해부학적 관계는 대체로 정확하나, 일부 표현이 모호함"
- "좌우 구분은 있으나 다소 불명확함"

**0.0 예시:**
- "좌심실을 우심실로 잘못 표시함"
- "필수 해부학적 랜드마크가 누락되어 해석 불가능"
- "Axial convention이 잘못되어 좌우가 반대로 표시됨"

---

### 4.8 `image_quality_pre/post` 상세 가이드

#### 정의
**이미지 품질(Image Quality)**은 이미지의 해상도, 가독성, 대비, 아티팩트 등을 종합적으로 평가합니다.

#### 점수별 평가 기준

**5 (매우 좋음)**
- 해상도가 충분하여 모든 구조를 명확히 식별 가능
- 대비가 적절하여 구조 구분이 명확함
- 아티팩트가 없거나 미미함
- 가독성이 매우 우수함
- 교육 자료로 즉시 사용 가능

**4 (좋음)**
- 해상도가 충분하여 대부분의 구조를 식별 가능
- 대비가 적절하나 일부 구조가 다소 불명확함
- 아티팩트가 있으나 해석에 큰 영향 없음
- 전반적으로 우수하나 소폭 개선 여지

**3 (보통)**
- 해상도가 기본 요건은 충족하나 일부 구조 식별이 어려움
- 대비가 다소 부족하여 구조 구분이 모호함
- 아티팩트가 있어 일부 해석에 영향
- 교육 자료로 사용 가능하나 개선 권장

**2 (나쁨)**
- 해상도가 부족하여 핵심 구조 식별이 어려움
- 대비가 부족하여 구조 구분이 어려움
- 아티팩트가 많아 해석에 상당한 영향
- 교육 자료로 사용하기에는 부족
- 상당한 개선 필요

**1 (매우 나쁨)**
- 해상도가 매우 부족하여 구조 식별이 거의 불가능
- 대비가 매우 부족하여 구조 구분이 불가능
- 심각한 아티팩트로 해석이 어려움
- 교육 자료로 부적합
- 전면적 수정 또는 재생성 필요

#### 평가 시 고려사항

**해상도 (Resolution)**
- 이미지 해상도가 충분한가?
- 구조를 명확히 식별할 수 있는가?

**가독성 (Readability)**
- 해부학적 구조를 명확히 구분할 수 있는가?
- 텍스트/라벨이 읽기 쉬운가? (있는 경우)

**아티팩트 (Artifacts)**
- 이미지에 아티팩트가 있는가?
- 아티팩트가 해석에 영향을 주는가?

**대비 (Contrast)**
- 구조 간 대비가 적절한가?
- 모든 구조를 구분할 수 있는가?

#### 종합 평가 팁
- 해상도와 가독성이 가장 중요합니다.
- 아티팩트가 심각하면 2 이하로 평가하세요.
- 전반적으로 우수하나 작은 개선 여지가 있으면 4로 평가하세요.

---

### 4.9 `image_text_consistency_pre/post` 상세 가이드

#### 정의
**이미지-텍스트 일관성(Image-Text Consistency)**은 이미지가 카드의 front/back 텍스트와 일치하고, 진단/소견을 뒷받침하는지를 평가합니다.

#### 점수별 평가 기준

**1.0 (완전 일치)**
- 이미지가 카드 텍스트와 완전히 일치함
- 이미지가 진단/소견을 명확히 뒷받침함
- 텍스트에서 언급한 소견이 이미지에서 명확히 확인됨
- 이미지와 텍스트가 서로 보완적으로 작용함

**0.5 (대체로 일치)**
- 이미지가 카드 텍스트와 대체로 일치하나, 일부 불일치가 있음
- 이미지가 진단/소견을 대체로 뒷받침하나, 일부 모호함
- 텍스트에서 언급한 소견이 이미지에서 대부분 확인되나 일부 누락
- 전반적으로 일치하나 일부 보완 필요

**0.0 (불일치)**
- 이미지가 카드 텍스트와 명백히 불일치함
- 이미지가 진단/소견을 뒷받침하지 않음
- 텍스트에서 언급한 소견이 이미지에서 확인되지 않음
- 이미지와 텍스트가 서로 모순됨
- 수정이 반드시 필요함

#### 평가 시 고려사항
- **텍스트 일치**: 카드의 front/back 텍스트에서 언급한 내용이 이미지에 나타나는가?
- **진단 뒷받침**: 이미지가 카드에서 설명하는 진단/소견을 뒷받침하는가?
- **소견 확인**: 텍스트에서 언급한 핵심 소견이 이미지에서 확인되는가?
- **모순 여부**: 이미지와 텍스트가 서로 모순되는가?

#### 예시

**1.0 예시:**
- "카드에서 'DWI 고신호'를 언급했고, 이미지에서도 DWI 고신호가 명확히 보임"
- "카드에서 '좌심실 비대'를 설명했고, 이미지에서 좌심실 비대가 명확히 확인됨"
- "이미지와 텍스트가 완벽하게 일치하고 서로 보완적임"

**0.5 예시:**
- "카드에서 언급한 소견이 이미지에 대체로 나타나나, 일부 세부 사항이 누락됨"
- "이미지가 진단을 대체로 뒷받침하나, 일부 표현이 모호함"
- "텍스트와 이미지가 대체로 일치하나, 일부 불일치가 있음"

**0.0 예시:**
- "카드에서 'CT 영상'을 언급했으나, 이미지는 'US 영상'임 (모달리티 불일치)"
- "카드에서 '좌심실 비대'를 설명했으나, 이미지에서는 우심실 비대가 보임"
- "이미지와 텍스트가 명백히 모순됨"

#### 주의사항
- 이미지가 텍스트를 단순히 반복하는 것이 아니라, 텍스트를 시각적으로 뒷받침해야 합니다.
- 텍스트에서 언급하지 않은 소견이 이미지에 나타나는 것은 문제가 아닙니다 (추가 정보는 허용).
- 하지만 텍스트에서 언급한 핵심 소견이 이미지에 없으면 문제입니다.

---

## 5. AppSheet 설정 방법

### 4.1 Display Name 설정

**AppSheet 메뉴 경로:** `Data` → `Tables` → `[테이블명]` → `[컬럼명]`

1. 컬럼 클릭
2. `Display name` 필드에 한국어 또는 영어 이름 입력
3. `Save` 클릭

### 4.2 Description 설정

**AppSheet 메뉴 경로:** `Data` → `Tables` → `[테이블명]` → `[컬럼명]`

1. 컬럼 클릭
2. `Description` 필드에 설명 입력
3. `Save` 클릭

**참고:**
- Description은 Detail View에서 컬럼 이름 옆에 작은 정보 아이콘(ℹ️)으로 표시됩니다
- 사용자가 정보 아이콘을 클릭하면 Description이 툴팁으로 표시됩니다
- 평가 항목의 경우, 위의 "Description (평가자용)" 내용을 그대로 사용하시면 됩니다

---

## 6. 추가 권장 사항

### 6.1 컬럼 그룹화 (Detail View)

**Ratings Detail View에서 컬럼을 논리적으로 그룹화:**

1. **기본 정보**
   - `rating_id`, `card_uid`, `rater_email`, `assignment_order`

2. **Pre 평가**
   - `pre_started_ts`, `pre_submitted_ts`, `pre_duration_sec`
   - `blocking_error_pre`, `technical_accuracy_pre`, `educational_quality_pre`, `evidence_comment_pre`

3. **Post 평가**
   - `post_started_ts`, `post_submitted_ts`, `post_duration_sec`
   - `blocking_error_post`, `technical_accuracy_post`, `educational_quality_post`, `evidence_comment_post`

4. **변경 로그**
   - `change_reason_code`, `change_note`, `changed_fields`

5. **플래그**
   - `flag_followup`, `flag_note`

6. **관리자 전용** (Show_If: `ISADMIN()`)
   - `admin_undo_pre_submitted_ts`, `admin_undo_post_submitted_ts`, `undo_reason`

### 6.2 필수 필드 표시

**Required 필드가 아닌 경우에도, 사용자에게 필수임을 알리기:**
- Description에 "(필수)" 또는 "(Required)" 표시
- 또는 Virtual Column `pre_is_complete`, `post_is_complete`를 활용하여 시각적 피드백 제공

### 6.3 조건부 필드 안내

**조건부 필수 필드의 경우 Description에 명확히 표시:**
- 예: `evidence_comment_pre`의 Description에 "blocking_error가 Yes이거나 educational_quality가 2 이하인 경우 필수입니다" 명시

### 6.4 이미지 평가 항목 사용 가이드

**평가 시점:**
- 이미지 평가 항목은 **Post 평가 단계**에서 평가합니다
- S5 결과를 확인한 후, 이미지를 직접 보고 평가하세요
- Pre 평가에서는 이미지를 보지 않으므로 이미지 평가 항목은 평가하지 않습니다

**S5와의 비교:**
- S5가 평가한 이미지 품질 결과와 사람 평가를 비교하여 S5의 정확도를 검증합니다
- S5 결과는 `S5` 테이블의 `card_image_validation` 섹션에서 확인할 수 있습니다
- 비교 항목:
  - `blocking_error`: S5의 `blocking_error` vs 사람의 `image_blocking_error_post` (1번 - 가장 중요)
  - `anatomical_accuracy`: S5의 `anatomical_accuracy` vs 사람의 `image_anatomical_accuracy_post`
  - `image_quality`: S5의 `image_quality` vs 사람의 `image_quality_post`
  - `text_image_consistency`: S5의 `text_image_consistency` vs 사람의 `image_text_consistency_post`

**평가 원칙:**
- S5 결과에 영향을 받지 않고, 이미지를 직접 보고 객관적으로 평가하세요
- S5와 다른 평가를 했다면, `change_note`에 이유를 기록하세요

---

## 7. S5 Final Assessment 관련 컬럼 (멀티에이전트 시스템 Self-Improvement 검증)

### 7.1 S5 단계 시간 측정

#### `s5_started_ts` (Date/Time)
**용도:** S5 Final Assessment 단계 시작 시점 기록

**사용 시점:**
- "Start S5 Final Assessment" 액션 실행 시 자동으로 `NOW()` 기록
- S5 단계가 시작되었음을 표시

**AppSheet 설정:**
- **Initial Value**: `NOW()` (액션에서 설정)
- **Editable**: 체크 해제 (읽기 전용)

**Display Name 제안:**
- 한국어: `S5 단계 시작 시점`
- 영어: `S5 Started Timestamp`

**Description 제안:**
```
S5 Final Assessment 단계가 시작된 시점입니다.
"Start S5 Final Assessment" 버튼을 누르면 자동으로 기록됩니다.
```

---

#### `s5_submitted_ts` (Date/Time)
**용도:** S5 Final Assessment 단계 제출 시점 기록

**사용 시점:**
- "Submit S5 Final Assessment" 액션 실행 시 자동으로 `NOW()` 기록
- S5 단계가 완료되었음을 표시

**AppSheet 설정:**
- **Initial Value**: (액션에서 설정)
- **Editable**: 체크 해제 (읽기 전용)

**Display Name 제안:**
- 한국어: `S5 단계 제출 시점`
- 영어: `S5 Submitted Timestamp`

**Description 제안:**
```
S5 Final Assessment 단계가 제출된 시점입니다.
"Submit S5 Final Assessment" 버튼을 누르면 자동으로 기록됩니다.
```

---

#### `s5_duration_sec` (Number, Virtual Column)
**용도:** S5 Final Assessment 단계 소요 시간 자동 계산 (초 단위)

**계산 수식:**
```
TOTAL_SECONDS([s5_submitted_ts] - [s5_started_ts])
```

**AppSheet 설정:**
- **Type**: `Virtual`
- **Virtual column expression**: 위의 수식
- **Editable**: 체크 해제 (읽기 전용)

**Display Name 제안:**
- 한국어: `S5 단계 소요 시간 (초)`
- 영어: `S5 Duration (seconds)`

**Description 제안:**
```
S5 Final Assessment 단계에 소요된 시간입니다.
시작 시점부터 제출 시점까지의 시간이 초 단위로 자동 계산됩니다.
```

---

### 7.2 AI 자가 평가 신뢰도

#### `ai_self_reliability` (Number, 1-5)
**용도:** 멀티에이전트가 스스로 도출한 평가 결과의 타당성 평가

**평가 척도:**
- 1 = 전혀 신뢰할 수 없음
- 2 = 신뢰하기 어려움
- 3 = 보통
- 4 = 신뢰할 수 있음
- 5 = 매우 신뢰할 수 있음

**사용 시점:**
- S5 Final Assessment 단계에서 필수 입력
- 멀티에이전트의 자가 평가 점수를 보고 신뢰도 평가

**AppSheet 설정:**
- **Type**: `Number`
- **Editable_If**: `AND(NOT(ISBLANK([s5_started_ts])), ISBLANK([s5_submitted_ts]))`
- **Required_If**: `AND(NOT(ISBLANK([s5_started_ts])), ISBLANK([s5_submitted_ts]))`

**Display Name 제안:**
- 한국어: `AI 자가 평가 신뢰도`
- 영어: `AI Self-Assessment Reliability`

**Description 제안 (간결 버전 - 2줄):**
```
멀티에이전트가 스스로 도출한 평가 결과가 타당하다고 생각하십니까?
1-5 척도로 평가해주세요 (1=전혀 신뢰할 수 없음, 5=매우 신뢰할 수 있음).
```

---

#### `ai_self_reliability_comment` (LongText)
**용도:** AI 자가 평가 신뢰도 평가 근거 (선택)

**사용 시점:**
- 신뢰도 평가 시 추가 설명이 필요한 경우 입력
- 선택 사항

**AppSheet 설정:**
- **Type**: `LongText`
- **Editable_If**: `AND(NOT(ISBLANK([s5_started_ts])), ISBLANK([s5_submitted_ts]))`
- **Required_If**: `FALSE` (선택 사항)

**Display Name 제안:**
- 한국어: `AI 자가 평가 신뢰도 근거`
- 영어: `AI Self-Assessment Reliability Comment`

**Description 제안:**
```
AI 자가 평가 신뢰도를 평가한 근거를 설명해주세요 (선택 사항).
```

---

### 7.3 AI 수정안 수용 결정

#### `accept_ai_correction` (Enum)
**용도:** AI의 수정 제안을 최종 판독에 반영할지 결정

**Enum 옵션:**
- `ACCEPT` - AI 수정안 수용
- `REJECT` - 초기안 유지
- `PARTIAL` - 부분 수용 (향후 확장)

**사용 시점:**
- 재생성 콘텐츠가 있을 때만 표시 및 필수 입력
- AI의 수정 제안을 검토한 후 최종 결정

**AppSheet 설정:**
- **Type**: `Enum`
- **Enum Options**: `ACCEPT`, `REJECT`, `PARTIAL`
- **Show_If**: `AND(NOT(ISBLANK([s5_started_ts])), NOT(ISBLANK([card_uid].[S5_one].[s5_regenerated_front])))`
- **Editable_If**: `AND(NOT(ISBLANK([s5_started_ts])), ISBLANK([s5_submitted_ts]), NOT(ISBLANK([card_uid].[S5_one].[s5_regenerated_front])))`
- **Required_If**: `AND(NOT(ISBLANK([s5_started_ts])), ISBLANK([s5_submitted_ts]), NOT(ISBLANK([card_uid].[S5_one].[s5_regenerated_front])))`

**Display Name 제안:**
- 한국어: `AI 수정안 수용 여부`
- 영어: `Accept AI Correction`

**Description 제안 (간결 버전 - 2줄):**
```
AI의 수정 사항을 최종 결과로 채택하시겠습니까?
ACCEPT: 수정안 채택, REJECT: 초기안 유지
```

---

#### `ai_correction_quality` (Number, 1-5)
**용도:** AI 수정안의 품질 평가 (1-5 Likert)

**평가 척도:**
- 1 = 매우 나쁨
- 2 = 나쁨
- 3 = 보통
- 4 = 좋음
- 5 = 매우 좋음

**사용 시점:**
- 재생성 콘텐츠가 있을 때만 표시
- AI 수정안을 검토한 후 품질 평가

**AppSheet 설정:**
- **Type**: `Number`
- **Show_If**: `AND(NOT(ISBLANK([s5_started_ts])), NOT(ISBLANK([card_uid].[S5_one].[s5_regenerated_front])))`
- **Editable_If**: `AND(NOT(ISBLANK([s5_started_ts])), ISBLANK([s5_submitted_ts]), NOT(ISBLANK([card_uid].[S5_one].[s5_regenerated_front])))`

**Display Name 제안:**
- 한국어: `AI 수정안 품질 평가`
- 영어: `AI Correction Quality`

**Description 제안 (간결 버전 - 2줄):**
```
AI의 수정안 품질을 1-5 척도로 평가해주세요.
초기안과 비교하여 수정안의 품질이 얼마나 개선되었는지 평가합니다.
```

---

#### `ai_correction_comment` (LongText)
**용도:** AI 수정안 수용/거부 근거

**사용 시점:**
- 재생성 콘텐츠가 있을 때만 표시
- 수용 또는 거부 결정의 근거를 설명

**AppSheet 설정:**
- **Type**: `LongText`
- **Show_If**: `AND(NOT(ISBLANK([s5_started_ts])), NOT(ISBLANK([card_uid].[S5_one].[s5_regenerated_front])))`
- **Editable_If**: `AND(NOT(ISBLANK([s5_started_ts])), ISBLANK([s5_submitted_ts]), NOT(ISBLANK([card_uid].[S5_one].[s5_regenerated_front])))`
- **Required_If**: `FALSE` (선택 사항)

**Display Name 제안:**
- 한국어: `AI 수정안 수용/거부 근거`
- 영어: `AI Correction Acceptance/Rejection Rationale`

**Description 제안:**
```
AI 수정안을 수용하거나 거부한 근거를 설명해주세요 (선택 사항).
초기안과 수정안을 비교한 결과를 간단히 기록하세요.
```

---

## 8. 참고 문서

- **기본 설정 가이드**: `AppSheet_QA_Setup_Guide.md`
- **프로덕션 강화 가이드**: `AppSheet_QA_Production_Hardening.md`
- **시스템 사양서**: `AppSheet_QA_System_Specification.md`
- **S5 Final Assessment 설계**: `AppSheet_S5_Final_Assessment_Design.md`

---

**문서 버전**: 1.1  
**최종 업데이트**: 2025-01-01


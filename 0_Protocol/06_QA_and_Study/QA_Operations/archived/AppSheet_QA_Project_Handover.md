# AppSheet 의료 데이터 평가 앱 개발 현황 보고서

**작성일:** 2025-01-01  
**프로젝트 상태:** 개발 중 (UI 최적화 단계)  
**인계 대상:** AI 엔지니어 / 개발자

---

## 1. 프로젝트 개요

### 1.1 목적
영상의학과 전문의가 의료 케이스를 **Blind Test 방식**으로 평가(Annotation)하고 시간을 측정하는 앱입니다.

### 1.2 핵심 기능

1. **배정(Assignment)**: 평가자별로 할당된 케이스만 노출
2. **블라인드(Blind)**: 'Start' 버튼을 누르기 전까지는 문제(지문/이미지) 숨김
3. **타이머(Timer)**: Start 버튼 클릭 시점부터 시간 측정 시작
4. **단계별 평가**: 
   - **Pre-Reading**: 지문만 보고 평가 (S5 결과 미공개)
   - **Reveal**: 정답(S5 결과) 공개
   - **Post-Reading**: 최종 평가 (S5 결과 확인 후 재평가)

### 1.3 기술 스택
- **플랫폼**: Google AppSheet (No-code)
- **데이터 저장소**: Google Sheets
- **이미지 저장소**: Google Drive
- **데이터 소스**: Python 스크립트로 생성된 CSV 파일

---

## 2. 데이터베이스 구조 (Tables)

### 2.1 Cards (Master Table)
**역할**: 모든 문제 데이터 (지문, 이미지, 정답 포함). 읽기 전용.

**주요 컬럼:**
- `card_uid` (Key): 고유 식별자
- `card_id`: 카드 ID
- `front`: 문제 지문
- `back`: 정답 (평가자에게는 숨김)
- `image_filename`: 이미지 파일명
- `group_id`: 그룹 ID

**Virtual Columns:**
- `my_order_number`: Assignments 테이블에서 현재 사용자의 순서 번호를 가져옴

### 2.2 Assignments (Link Table)
**역할**: `rater_email`과 `card_uid`를 매핑. 평가자별 할당된 케이스 관리.

**주요 컬럼:**
- `assignment_id` (Key): 고유 식별자
- `rater_email`: 평가자 이메일
- `card_uid`: Cards 테이블 참조
- `assignment_order`: 순서 번호 (1, 2, 3, ...)
- `batch_id`: 배치 ID

### 2.3 Ratings (Transaction Table)
**역할**: 평가 결과 저장소. 평가를 시작해야 행(Row)이 생성됨.

**주요 컬럼:**
- `rating_id` (Key): `CONCATENATE([card_uid], "::", USEREMAIL())`
- `card_uid`: Cards 테이블 참조
- `rater_email`: 평가자 이메일 (자동 설정: `USEREMAIL()`)
- `assignment_order`: Assignments에서 가져온 순서 번호

**Pre-Reading 관련:**
- `pre_started_ts` (Date/Time): 평가 시작 시각
- `pre_submitted_ts` (Date/Time): 평가 제출 시각
- `pre_duration_sec` (Number): 평가 소요 시간 (초)
- `blocking_error_pre` (Yes/No): 차단 오류 여부
- `technical_accuracy_pre` (Enum: 0, 0.5, 1): 기술적 정확도
- `educational_quality_pre` (Enum: 1-5): 교육적 품질
- `evidence_comment_pre` (LongText): 증거 코멘트

**Post-Reading 관련:**
- `post_started_ts` (Date/Time): Post 평가 시작 시각 (S5 공개 시점과 동일)
- `post_submitted_ts` (Date/Time): Post 평가 제출 시각
- `post_duration_sec` (Number): Post 평가 소요 시간 (초)
- `blocking_error_post` (Yes/No)
- `technical_accuracy_post` (Enum: 0, 0.5, 1)
- `educational_quality_post` (Enum: 1-5)
- `evidence_comment_post` (LongText)

**Change Log:**
- `change_reason_code` (Enum): 변경 이유 코드
- `change_note` (LongText): 변경 사유

**Virtual Columns:**
- `view_question_front`: `[card_uid].[front]` - `Show_If: ISNOTBLANK([pre_started_ts])`
- `view_question_image`: `[card_uid].[image_filename]` - `Show_If: ISNOTBLANK([pre_started_ts])`
- `pre_is_complete` (Yes/No): Pre 평가 완결성 체크
- `post_is_complete` (Yes/No): Post 평가 완결성 체크
- `is_changed` (Yes/No): Pre/Post 값 변경 여부
- `qa_state` (Text): 평가 상태 (TODO, PRE, REVEAL_READY, REVEAL, POST, DONE)
- `v_btn_start_holder`: 버튼 위치 잡기용 빈 컬럼 (현재 디버깅 중)

---

## 3. 현재 구현된 핵심 로직 (Logic Flow)

### 3.1 화면 구성 및 이동 경로

#### A. 목록 화면 (Ratings_List)
- **Source**: `MyAssignedCards` (Slice of Cards)
- **Filter**: `IN([card_uid], SELECT(Assignments[card_uid], [rater_email] = USEREMAIL()))`
- **UI 설정**:
  - 이미지 숨김: Image Layout = None
  - 컬럼: `my_order_number`를 "Case 1", "Case 2" 형태로 표시
  - 문제 내용 숨김 (블라인드 유지)

#### B. 상세 진입 (Cards_Detail)
- **UI**: 문제 내용 숨김(Blind)
- **액션**: "Start Rating" 버튼만 노출
- **기능**: `LINKTOFORM`을 통해 `Ratings_Form`을 호출하며 `card_uid` 전달
- **중요**: 이 단계에서는 시간을 찍지 않음 (단순 이동)

#### C. 데이터 생성 (Ratings_Form)
- **설정**: 
  - Auto Save: ON
  - Finish View: `Ratings_Detail`
- **역할**: 사용자 입력 없이 즉시 Ratings 행을 생성하고 Detail View로 자동 넘김
- **초기값**:
  - `rating_id`: `CONCATENATE([card_uid], "::", USEREMAIL())`
  - `rater_email`: `USEREMAIL()`
  - `card_uid`: Form 파라미터에서 전달받은 값
  - `assignment_order`: Assignments에서 조회

#### D. 실제 평가 화면 (Ratings_Detail)

**초기 상태:**
- `pre_started_ts`가 비어있으므로 문제 내용(`view_question_*`) 안 보임
- "Start Pre-S5 Rating" 버튼만 표시

**평가 시작:**
1. "Start Pre-S5 Rating" 버튼 클릭
2. `pre_started_ts = NOW()` 타임스탬프 기록
3. `Show_If` 조건에 의해 문제와 입력창(Quick Edit)이 나타남

**Pre 평가 제출:**
1. "Submit Pre-S5 Rating" 버튼 클릭
2. `pre_submitted_ts = NOW()` 기록
3. `pre_duration_sec` 자동 계산: `([pre_submitted_ts] - [pre_started_ts]) * 24 * 60 * 60`
4. Pre 필드 잠금 (`Editable_If = ISBLANK([pre_submitted_ts])`)

**S5 공개:**
1. "Reveal S5 Results" 버튼 클릭
2. `post_started_ts = NOW()` 기록 (S5 공개 시점과 Post 시작 시점 동일)
3. S5 Reference 섹션 표시 (`Show_If = NOT(ISBLANK([post_started_ts]))`)
4. Post 입력 필드 활성화 (`Editable_If = AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]))`)

**Post 평가 제출:**
1. "Submit Post-S5 Rating" 버튼 클릭
2. `post_submitted_ts = NOW()` 기록
3. `post_duration_sec` 자동 계산
4. Post 필드 잠금
5. 평가 완료 (`qa_state = "DONE"`)

### 3.2 주요 보안 설정 (Security & Visibility)

#### Slice (MyAssignedCards)
```
IN([card_uid], SELECT(Assignments[card_uid], [rater_email] = USEREMAIL()))
```

#### Virtual Columns (Cards 테이블)
- `my_order_number`: Assignments 테이블에서 내 순서 번호를 가져옴

#### Virtual Columns (Ratings 테이블)
- `view_question_front`: `ISNOTBLANK([pre_started_ts])`일 때만 보여주는 지문 컬럼
- `view_question_image`: `ISNOTBLANK([pre_started_ts])`일 때만 보여주는 이미지 컬럼
- `v_btn_start_holder`: 버튼 위치 잡기용 빈 컬럼 (현재 디버깅 중)

### 3.3 액션 (Actions)

#### "Start Pre-S5 Rating"
- **Type**: Update row
- **Update**: `pre_started_ts = NOW()`
- **Show_If**: `ISBLANK([pre_started_ts])`
- **Run_If**: `ISBLANK([pre_started_ts])`

#### "Submit Pre-S5 Rating"
- **Type**: Update row
- **Update**: `pre_submitted_ts = NOW()`
- **On Success**: `pre_duration_sec = ([pre_submitted_ts] - [pre_started_ts]) * 24 * 60 * 60`
- **Show_If**: `AND(NOT(ISBLANK([pre_started_ts])), ISBLANK([pre_submitted_ts]))`
- **Run_If**: `AND(NOT(ISBLANK([pre_started_ts])), ISBLANK([pre_submitted_ts]), [pre_is_complete])`

#### "Reveal S5 Results"
- **Type**: Update row
- **Update**: `post_started_ts = NOW()` (핵심: S5 공개와 Post 시작을 동시에 기록)
- **Show_If**: `AND(NOT(ISBLANK([pre_submitted_ts])), ISBLANK([post_started_ts]))`
- **Run_If**: `AND(NOT(ISBLANK([pre_submitted_ts])), ISBLANK([post_started_ts]))`

#### "Submit Post-S5 Rating"
- **Type**: Update row
- **Update**: `post_submitted_ts = NOW()`
- **On Success**: `post_duration_sec = ([post_submitted_ts] - [post_started_ts]) * 24 * 60 * 60`
- **Show_If**: `AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]))`
- **Run_If**: `AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]), [post_is_complete], OR(NOT([is_changed]), AND(ISNOTBLANK([change_reason_code]), ISNOTBLANK([change_note]))))`

---

## 4. 최근 해결된 이슈 (Solved)

### ✅ 이슈 1: 목록 블라인드
**문제**: 리스트에서 썸네일 이미지가 보이는 문제  
**해결**: Image Layout = None 및 컬럼 수동 배치로 해결

### ✅ 이슈 2: 순서 표시
**문제**: 평가자별 순서를 표시해야 함  
**해결**: CSV의 `assignment_order`를 활용해 리스트에 "Case 1" 형식으로 표시 성공

### ✅ 이슈 3: 타이머 로직 수정
**문제**: 폼을 열자마자 시간이 찍혀 블라인드가 뚫리는 문제  
**해결**: **"진입(Form) -> 대기(Detail) -> 시작 버튼(Action)"**의 3단계로 분리하여 해결
- Form 진입 시: Ratings 행만 생성, 시간 기록 안 함
- Detail View: `pre_started_ts`가 비어있으므로 문제 숨김
- Start 버튼 클릭: `pre_started_ts` 기록 후 문제 표시

### ✅ 이슈 4: s5_revealed_ts 통합
**문제**: `s5_revealed_ts`와 `post_started_ts` 두 개의 컬럼으로 인한 복잡성  
**해결**: `s5_revealed_ts` 제거, `post_started_ts`로 통합
- `post_started_ts`가 있으면 S5가 공개된 것으로 간주
- "Reveal S5 Results" 액션이 `post_started_ts`를 업데이트

---

## 5. 현재 진행 중인 작업 & 이슈 (Pending Issues)

### 🔴 이슈: Start 버튼 위치 문제

**문제**: `Ratings_Detail` 화면에서 "Start Pre-S5 Rating" 액션 버튼을 화면 최상단에 배치하려는데 어려움이 있음.

**시도한 방법:**
1. Inline 모드로 빈 컬럼(`v_btn_start_holder`)에 부착 시도
2. 컬럼을 Slice에 추가
3. 공백 값(" ") 부여

**원인 파악:**
- 해당 컬럼이 Slice에 포함되지 않았거나
- 값이 공란("")이라 화면에서 숨겨지는 AppSheet 특성 때문으로 추정

**다음 단계 (제안):**
1. `v_btn_start_holder` 컬럼에 공백 값(" ") 부여 및 Slice에 컬럼 추가 확인
2. 안 될 경우 Display Overlay 방식(우측 하단 둥둥 떠 있는 버튼)으로 UI 변경 고려
3. 또는 Detail View의 컬럼 순서를 재배치하여 버튼이 자연스럽게 상단에 오도록 조정

---

## 6. 요청 사항 (Next Step for Agent)

### 6.1 즉시 해결 필요
1. **Start 버튼 위치 확정**
   - `Ratings_Detail` 뷰에서 시작 버튼을 최상단에 노출시키거나
   - Overlay 버튼으로 변경하여 UI를 확정지어 주세요

### 6.2 검증 필요
1. **Submit 프로세스 검증**
   - Pre 평가 제출 후 필드 잠금 확인
   - `pre_duration_sec` 자동 계산 확인

2. **Post-Rating 프로세스 검증**
   - Reveal S5 Results 후 S5 섹션 표시 확인
   - Post 필드 활성화 확인
   - Post 평가 제출 후 필드 잠금 확인
   - `post_duration_sec` 자동 계산 확인
   - Change log 필수 입력 확인 (변경 시)

3. **전체 워크플로우 검증**
   - Pre → Reveal → Post 순서대로 진행되는지 확인
   - 중간에 나갔다가 다시 들어와도 이어서 진행 가능한지 확인
   - 시간 측정이 정확한지 확인

---

## 7. 참고 문서

### 7.1 설정 가이드
- **기본 설정**: `AppSheet_QA_Setup_Guide.md`
- **프로덕션 강화**: `AppSheet_QA_Production_Hardening.md`
- **구현 체크리스트**: `AppSheet_QA_Implementation_Checklist.md`

### 7.2 데이터 구조
- **CSV Export 스크립트**: `3_Code/src/tools/final_qa/export_appsheet_tables.py`
- **데이터 위치**: `2_Data/qa_appsheet_export/[RUN_TAG]/`

### 7.3 주요 설정 파일
- **Google Sheets**: `MeducAI_QA_AppSheet/qa_appsheet_db`
- **이미지 폴더**: `MeducAI_QA_AppSheet/images/`

---

## 8. 기술적 세부사항

### 8.1 Virtual Column 공식

#### `pre_is_complete`
```
AND(
  ISNOTBLANK([blocking_error_pre]),
  ISNOTBLANK([technical_accuracy_pre]),
  ISNOTBLANK([educational_quality_pre]),
  OR(
    [blocking_error_pre] = FALSE,
    NUMBER([educational_quality_pre]) > 2,
    ISNOTBLANK([evidence_comment_pre])
  )
)
```

#### `post_is_complete`
```
AND(
  ISNOTBLANK([blocking_error_post]),
  ISNOTBLANK([technical_accuracy_post]),
  ISNOTBLANK([educational_quality_post]),
  OR(
    [blocking_error_post] = FALSE,
    NUMBER([educational_quality_post]) > 2,
    ISNOTBLANK([evidence_comment_post])
  )
)
```

#### `is_changed`
```
AND(
  [post_is_complete],
  OR(
    [blocking_error_post] <> [blocking_error_pre],
    [technical_accuracy_post] <> [technical_accuracy_pre],
    [educational_quality_post] <> [educational_quality_pre],
    [evidence_comment_post] <> [evidence_comment_pre]
  )
)
```

#### `qa_state`
```
IF(
  NOT(ISBLANK([post_submitted_ts])),
  "DONE",
  IF(
    NOT(ISBLANK([post_started_ts])),
    "POST",
    IF(
      NOT(ISBLANK([post_started_ts])),
      "REVEAL",
      IF(
        NOT(ISBLANK([pre_submitted_ts])),
        "REVEAL_READY",
        IF(
          NOT(ISBLANK([pre_started_ts])),
          "PRE",
          "TODO"
        )
      )
    )
  )
)
```

### 8.2 Editable_If 조건

#### Pre 필드
```
ISBLANK([pre_submitted_ts])
```

#### Post 필드
```
AND(
  NOT(ISBLANK([post_started_ts])),
  ISBLANK([post_submitted_ts])
)
```

#### Change Log 필드
```
AND(
  NOT(ISBLANK([post_started_ts])),
  ISBLANK([post_submitted_ts])
)
```

---

## 9. 알려진 제약사항

### 9.1 AppSheet 제약
- Virtual Column은 Slice에 포함되어야 화면에 표시됨
- 빈 값("")인 컬럼은 자동으로 숨겨질 수 있음
- 액션 버튼의 위치 제어가 제한적임

### 9.2 데이터 제약
- CSV Export 시 `s5_revealed_ts` 컬럼은 생성하지 않음 (사용하지 않음)
- `post_started_ts`가 S5 공개 여부를 나타냄

---

## 10. 연락처 및 추가 정보

**프로젝트 위치**: `/path/to/workspace/workspace/MeducAI`  
**문서 위치**: `0_Protocol/06_QA_and_Study/QA_Operations/`

**추가 질문이 있으시면:**
1. 위 참고 문서들을 먼저 확인
2. AppSheet 앱 설정에서 각 테이블/뷰/액션 확인
3. Google Sheets에서 실제 데이터 구조 확인

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-01-01


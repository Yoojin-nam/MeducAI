# [인계장] 영상의학 AI 판독 데이터 수집 시스템 (AppSheet 기반)

**작성일:** 2025-01-01  
**프로젝트 상태:** Production-ready  
**인계 대상:** AI 엔지니어 / 개발자 / 유지보수 담당자  
**문서 버전:** 1.0

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [데이터베이스 구조 (ERD)](#2-데이터베이스-구조-erd)
3. [핵심 비즈니스 로직](#3-핵심-비즈니스-로직)
4. [AppSheet 설정 상세](#4-appsheet-설정-상세)
5. [워크플로우 및 상태 관리](#5-워크플로우-및-상태-관리)
6. [보안 및 권한 설정](#6-보안-및-권한-설정)
7. [성능 최적화](#7-성능-최적화)
8. [운영 가이드](#8-운영-가이드)
9. [문제 해결 가이드](#9-문제-해결-가이드)
10. [향후 개선 사항](#10-향후-개선-사항)

---

## 1. 시스템 개요

### 1.1 목적

영상의학과 전문의가 의료 케이스를 **Blind Test 방식**으로 평가(Annotation)하고 시간을 측정하는 웹 기반 앱입니다.

### 1.2 핵심 기능

1. **배정(Assignment)**: 평가자별로 할당된 케이스만 노출
2. **블라인드(Blind)**: 'Start Pre-S5 Rating' 버튼을 누르기 전까지는 문제(지문/이미지) 숨김
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
  - 위치: `3_Code/src/tools/final_qa/export_appsheet_tables.py`
  - 출력: `2_Data/qa_appsheet_export/[RUN_TAG]/`

### 1.4 데이터 흐름

```
Python Exporter → CSV Files → Google Sheets → AppSheet App
                                    ↓
                            Google Drive (Images)
```

---

## 2. 데이터베이스 구조 (ERD)

### 2.1 테이블 관계도

```
Groups (1) ──< (N) Cards (1) ──< (N) Assignments
                              └──< (N) Ratings
                              └──< (1) S5
```

### 2.2 테이블 상세

#### 2.2.1 Cards (Master Table)
**역할**: 모든 문제 데이터 (지문, 이미지, 정답 포함). 읽기 전용.

| 컬럼명 | 타입 | Key | 설명 |
|--------|------|-----|------|
| `card_uid` | Text | ✅ Primary | 고유 식별자 (예: `grp_xxx::DERIVED:yyy__Q1__0`) |
| `card_id` | Text | | 카드 ID |
| `front` | LongText | | 문제 지문 |
| `back` | LongText | | 정답 (평가자에게는 숨김) |
| `image_filename` | Image | | 이미지 파일명 (Google Drive 경로) |
| `group_id` | Reference → Groups | | 그룹 ID |
| `card_type` | Enum | | 카드 타입 (BASIC, MCQ 등) |

**Virtual Columns:**
- `my_order_number`: Assignments 테이블에서 현재 사용자의 순서 번호를 가져옴

#### 2.2.2 Groups (Reference Table)
**역할**: 그룹 정보 관리

| 컬럼명 | 타입 | Key | 설명 |
|--------|------|-----|------|
| `group_id` | Text | ✅ Primary | 그룹 고유 식별자 |
| `entity_name` | Text | | 그룹명 |
| `master_table_pdf_file` | File | | 마스터 테이블 PDF 파일 |

#### 2.2.3 Assignments (Link Table)
**역할**: `rater_email`과 `card_uid`를 매핑. 평가자별 할당된 케이스 관리.

| 컬럼명 | 타입 | Key | 설명 |
|--------|------|-----|------|
| `assignment_id` | Text | ✅ Primary | 고유 식별자 |
| `rater_email` | Email | | 평가자 이메일 |
| `card_uid` | Reference → Cards | | Cards 테이블 참조 |
| `assignment_order` | Number | | 순서 번호 (1, 2, 3, ...) |
| `batch_id` | Text | | 배치 ID |

#### 2.2.4 S5 (Reference Table)
**역할**: S5(LLM 생성 결과) 데이터

| 컬럼명 | 타입 | Key | 설명 |
|--------|------|-----|------|
| `card_uid` | Reference → Cards | ✅ Primary | Cards 테이블 참조 |
| `s5_front` | LongText | | S5가 생성한 front 텍스트 |
| `s5_back` | LongText | | S5가 생성한 back 텍스트 |

#### 2.2.5 Ratings (Transaction Table)
**역할**: 평가 결과 저장소. **Ratings-first 모델**에서는 Assignments 기반으로 사전 생성됨.

| 컬럼명 | 타입 | Key | 설명 |
|--------|------|-----|------|
| `rating_id` | Text | ✅ Primary | `CONCATENATE([card_uid], "::", USEREMAIL())` |
| `card_uid` | Reference → Cards | | Cards 테이블 참조 |
| `rater_email` | Email | | 평가자 이메일 (자동: `USEREMAIL()`) |
| `assignment_id` | Reference → Assignments | | Assignments 테이블 참조 |
| `assignment_order` | Number | | Assignments에서 가져온 순서 번호 |
| `batch_id` | Text | | 배치 ID |

**Pre-Reading 관련:**
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `pre_started_ts` | Date/Time | 평가 시작 시각 |
| `pre_submitted_ts` | Date/Time | 평가 제출 시각 |
| `pre_duration_sec` | Number | 평가 소요 시간 (초) |
| `blocking_error_pre` | Yes/No | 차단 오류 여부 |
| `technical_accuracy_pre` | Enum (0, 0.5, 1) | 기술적 정확도 |
| `educational_quality_pre` | Enum (1-5) | 교육적 품질 |
| `evidence_comment_pre` | LongText | 증거 코멘트 |

**Post-Reading 관련:**
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `post_started_ts` | Date/Time | Post 평가 시작 시각 (S5 공개 시점과 동일) |
| `post_submitted_ts` | Date/Time | Post 평가 제출 시각 |
| `post_duration_sec` | Number | Post 평가 소요 시간 (초) |
| `blocking_error_post` | Yes/No | 차단 오류 여부 |
| `technical_accuracy_post` | Enum (0, 0.5, 1) | 기술적 정확도 |
| `educational_quality_post` | Enum (1-5) | 교육적 품질 |
| `evidence_comment_post` | LongText | 증거 코멘트 |

**Change Log:**
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `change_reason_code` | Enum | 변경 이유 코드 (7개 옵션) |
| `change_note` | LongText | 변경 사유 |
| `changed_fields` | Text | 변경된 필드 목록 |

**Flags (Optional):**
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `flag_followup` | Yes/No | 후속 조치 필요 플래그 |
| `flag_note` | LongText | 플래그 메모 |

**Virtual Columns:**
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `view_question_front` | Virtual | `[card_uid].[front]` - `Show_If: ISNOTBLANK([pre_started_ts])` |
| `view_question_image` | Virtual | `[card_uid].[image_filename]` - `Show_If: ISNOTBLANK([pre_started_ts])` |
| `pre_is_complete` | Virtual (Yes/No) | Pre 평가 완결성 체크 |
| `post_is_complete` | Virtual (Yes/No) | Post 평가 완결성 체크 |
| `is_changed` | Virtual (Yes/No) | Pre/Post 값 변경 여부 |
| `qa_state` | Virtual (Text) | 평가 상태 (TODO, PRE, REVEAL_READY, REVEAL, POST, DONE) |

### 2.3 키(Key) 설정

각 테이블의 Primary Key:
- `Cards`: `card_uid`
- `Groups`: `group_id`
- `S5`: `card_uid`
- `Ratings`: `rating_id` = `CONCATENATE([card_uid], "::", USEREMAIL())`
- `Assignments`: `assignment_id`

### 2.4 참조(Reference) 설정

| 테이블 | 컬럼 | 참조 테이블 | 참조 컬럼 |
|--------|------|-------------|-----------|
| `Cards` | `group_id` | `Groups` | `group_id` |
| `S5` | `card_uid` | `Cards` | `card_uid` |
| `Ratings` | `card_uid` | `Cards` | `card_uid` |
| `Ratings` | `assignment_id` | `Assignments` | `assignment_id` |
| `Assignments` | `card_uid` | `Cards` | `card_uid` |

---

## 3. 핵심 비즈니스 로직

### 3.1 순차적 워크플로우 (5단계)

```
1. Start Pre-S5 Rating
   ↓ (pre_started_ts 기록, 문제 표시)
2. Submit Pre-S5 Rating
   ↓ (pre_submitted_ts 기록, Pre 필드 잠금)
3. Reveal S5 Results
   ↓ (post_started_ts 기록, S5 결과 표시)
4. Submit Post-S5 Rating
   ↓ (post_submitted_ts 기록, Post 필드 잠금)
5. DONE (평가 완료)
```

### 3.2 시간 측정 로직

#### Pre 평가 시간
- **시작 시점**: `pre_started_ts = NOW()` (Start Pre-S5 Rating 액션)
- **종료 시점**: `pre_submitted_ts = NOW()` (Submit Pre-S5 Rating 액션)
- **계산 수식**: `pre_duration_sec = ([pre_submitted_ts] - [pre_started_ts]) * 24 * 60 * 60`
- **저장 방식**: Number 타입 (초 단위)

#### Post 평가 시간
- **시작 시점**: `post_started_ts = NOW()` (Reveal S5 Results 액션)
- **종료 시점**: `post_submitted_ts = NOW()` (Submit Post-S5 Rating 액션)
- **계산 수식**: `post_duration_sec = ([post_submitted_ts] - [post_started_ts]) * 24 * 60 * 60`
- **저장 방식**: Number 타입 (초 단위)

### 3.3 블라인드 뷰 (Blind View) 로직

**목적**: 평가자가 Start 버튼을 누르기 전까지 문항을 볼 수 없도록 하여 시간 측정 오염을 방지합니다.

**구현 방법:**
1. Virtual Columns 사용:
   - `view_question_front`: `[card_uid].[front]`
   - `view_question_image`: `[card_uid].[image_filename]`
2. `Show_If` 조건:
   - `ISNOTBLANK([pre_started_ts])` - Start 버튼을 눌러야만 표시
3. Starting View 설정:
   - `Settings` → `UX` → `Options` → `General` → `Starting View = Ratings`
4. List View 최적화:
   - 문항 내용(`front`, `back`), 이미지(`image_filename`), Virtual Columns 제거
   - 상태 정보만 표시 (`rating_id`, `qa_state`, timestamps)

### 3.4 완결성 검증 로직

#### Pre 평가 완결성 (`pre_is_complete`)

```appsheet
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

**의미:**
- 필수 필드 3개(blocking_error, technical_accuracy, educational_quality) 모두 채워야 함
- 조건부 필수: blocking_error=TRUE이거나 educational_quality ≤ 2인 경우 evidence_comment도 필요

#### Post 평가 완결성 (`post_is_complete`)

```appsheet
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

#### 변경 감지 (`is_changed`)

```appsheet
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

**중요**: `post_is_complete` 가드로 Post가 완결된 뒤에만 변경 판단을 수행합니다.

### 3.5 상태 관리 (`qa_state`)

```appsheet
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

**상태 설명:**
- `TODO`: 평가 시작 전
- `PRE`: Pre 평가 진행 중
- `REVEAL_READY`: Pre 제출 완료, S5 공개 대기
- `REVEAL`: S5 공개됨, Post 시작 전
- `POST`: Post 평가 진행 중
- `DONE`: Post 제출 완료, 평가 완료

---

## 4. AppSheet 설정 상세

### 4.1 액션(Actions) 설정

#### 4.1.1 "Start Pre-S5 Rating"

| 설정 항목 | 값 |
|-----------|-----|
| **Type** | Update row |
| **Table** | Ratings |
| **Row** | Current row |
| **Update column** | `pre_started_ts` |
| **Update value** | `NOW()` |
| **Show_If** | `ISBLANK([pre_started_ts])` |
| **Run_If** | `ISBLANK([pre_started_ts])` |

**효과:**
- `view_question_front`와 `view_question_image` Virtual Columns가 화면에 나타남
- Pre 입력 필드가 편집 가능해짐

#### 4.1.2 "Submit Pre-S5 Rating"

| 설정 항목 | 값 |
|-----------|-----|
| **Type** | Update row |
| **Table** | Ratings |
| **Row** | Current row |
| **Update column** | `pre_submitted_ts` |
| **Update value** | `NOW()` |
| **Show_If** | `AND(NOT(ISBLANK([pre_started_ts])), ISBLANK([pre_submitted_ts]))` |
| **Run_If** | `AND(NOT(ISBLANK([pre_started_ts])), ISBLANK([pre_submitted_ts]), [pre_is_complete])` |
| **On success** | Update row → `pre_duration_sec` = `([pre_submitted_ts] - [pre_started_ts]) * 24 * 60 * 60` |

**효과:**
- Pre 필드가 잠김 (`Editable_If = ISBLANK([pre_submitted_ts])`)
- "Reveal S5 Results" 버튼이 나타남

#### 4.1.3 "Reveal S5 Results"

| 설정 항목 | 값 |
|-----------|-----|
| **Type** | Update row |
| **Table** | Ratings |
| **Row** | Current row |
| **Update column** | `post_started_ts` (핵심!) |
| **Update value** | `NOW()` |
| **Show_If** | `AND(NOT(ISBLANK([pre_submitted_ts])), ISBLANK([post_started_ts]))` |
| **Run_If** | `AND(NOT(ISBLANK([pre_submitted_ts])), ISBLANK([post_started_ts]))` |

**⚠️ 중요:**
- 이 버튼은 `post_started_ts`를 업데이트합니다
- `post_started_ts`가 있으면 S5가 공개된 것으로 간주합니다
- 별도의 "Start Post-S5 Rating" 액션은 필요하지 않습니다

**효과:**
- S5 Reference 섹션이 화면에 나타남
- Post 입력 필드가 편집 가능해짐

#### 4.1.4 "Submit Post-S5 Rating"

| 설정 항목 | 값 |
|-----------|-----|
| **Type** | Update row |
| **Table** | Ratings |
| **Row** | Current row |
| **Update column** | `post_submitted_ts` |
| **Update value** | `NOW()` |
| **Show_If** | `AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]))` |
| **Run_If** | `AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]), [post_is_complete], OR(NOT([is_changed]), AND(ISNOTBLANK([change_reason_code]), ISNOTBLANK([change_note]))))` |
| **On success** | Update row → `post_duration_sec` = `([post_submitted_ts] - [post_started_ts]) * 24 * 60 * 60` |

**효과:**
- Post 필드가 잠김
- 평가 완료 (`qa_state` = "DONE")

### 4.2 Editable_If 조건

#### Pre 필드
```appsheet
ISBLANK([pre_submitted_ts])
```

#### Post 필드
```appsheet
AND(
  NOT(ISBLANK([post_started_ts])),
  ISBLANK([post_submitted_ts])
)
```

#### Change Log 필드
```appsheet
AND(
  NOT(ISBLANK([post_started_ts])),
  ISBLANK([post_submitted_ts])
)
```

**⚠️ 중요:**
- Post 필드의 `Required` 필드는 **비워두거나 `No`로 설정**합니다
- `Required_If`를 사용하지 않습니다 (Reveal S5 액션과 충돌 방지)
- 대신 "Submit Post-S5 Rating" 액션의 `Run_If`에서 Post 완결성을 강제합니다

### 4.3 View 설정

#### 4.3.1 Starting View
- **경로**: `Settings` → `UX` → `Options` → `General`
- **설정**: `Starting View = Ratings`
- **이유**: Cards 테이블을 Starting View로 설정하면 평가자가 문항을 미리 볼 수 있습니다

#### 4.3.2 Ratings List View
**Allowed columns:**
- `rating_id` (or custom "Case ID")
- `qa_state` (status icon)
- `pre_started_ts`, `pre_submitted_ts`
- `post_started_ts`, `post_submitted_ts`
- `flag_followup` (if exists)

**⚠️ 절대 포함하지 말 것:**
- `front`, `back` (문항 내용)
- `view_question_front`, `view_question_image` (Virtual Columns)
- `image_filename` (이미지)
- Cards 테이블 Reference

#### 4.3.3 Ratings Detail View (컬럼 순서)

1. **"Start Pre-S5 Rating" (Action Button)**
   - `Show_If`: `ISBLANK([pre_started_ts])`

2. **`view_question_front` (Virtual Column)**
   - `Show_If`: `ISNOTBLANK([pre_started_ts])`

3. **`view_question_image` (Virtual Column)**
   - `Show_If`: `ISNOTBLANK([pre_started_ts])`

4. **[Pre Input Fields]**
   - `blocking_error_pre`, `technical_accuracy_pre`, `educational_quality_pre`, `evidence_comment_pre`
   - `Editable_If`: `ISBLANK([pre_submitted_ts])`

5. **"Submit Pre-S5 Rating" (Action Button)**
   - `Show_If`: `AND(NOT(ISBLANK([pre_started_ts])), ISBLANK([pre_submitted_ts]))`

6. **"Reveal S5 Results" (Action Button)**
   - `Show_If`: `AND(NOT(ISBLANK([pre_submitted_ts])), ISBLANK([post_started_ts]))`

7. **[S5 Reference Section]**
   - Reference type: `Cards` → `S5` (via `card_uid`)
   - `Show_If`: `NOT(ISBLANK([post_started_ts]))`

8. **[Post Input Fields]**
   - `blocking_error_post`, `technical_accuracy_post`, `educational_quality_post`, `evidence_comment_post`
   - `Editable_If`: `AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]))`

9. **"Submit Post-S5 Rating" (Action Button)**
   - `Show_If`: `AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]))`

**⚠️ Critical:**
- Cards 테이블의 자동 생성 Reference(Related Cards)는 Detail View에서 제거해야 합니다
- 안 그러면 Start 버튼을 누르기 전에도 답(S5 결과)을 볼 수 있습니다

### 4.4 Slice (Queue Views)

#### 4.4.1 MyQueue_Todo
- **Filter**: `AND([rater_email] = USEREMAIL(), [qa_state] = "TODO")`
- **Sort**: `assignment_order` (ascending)

#### 4.4.2 MyQueue_Reveal
- **Filter**: `AND([rater_email] = USEREMAIL(), [qa_state] = "REVEAL_READY")`
- **Sort**: `assignment_order` (ascending)

#### 4.4.3 MyQueue_Post
- **Filter**: `AND([rater_email] = USEREMAIL(), OR([qa_state] = "REVEAL", [qa_state] = "POST"))`
- **Sort**: `assignment_order` (ascending)

#### 4.4.4 MyQueue_Done
- **Filter**: `AND([rater_email] = USEREMAIL(), [qa_state] = "DONE")`
- **Sort**: `assignment_order` (ascending)

#### 4.4.5 MyFlagged (Optional)
- **Filter**: `AND([rater_email] = USEREMAIL(), [flag_followup] = TRUE)`
- **Sort**: `assignment_order` (ascending)

---

## 5. 워크플로우 및 상태 관리

### 5.1 전체 워크플로우

```
[목록 화면] Ratings_List (MyQueue_Todo)
    ↓
[상세 화면] Ratings_Detail
    ↓
1. "Start Pre-S5 Rating" 클릭
   → pre_started_ts 기록
   → 문제 표시 (view_question_*)
    ↓
2. Pre 평가 입력
   → blocking_error_pre, technical_accuracy_pre, educational_quality_pre, evidence_comment_pre
    ↓
3. "Submit Pre-S5 Rating" 클릭
   → pre_submitted_ts 기록
   → pre_duration_sec 계산
   → Pre 필드 잠금
    ↓
4. "Reveal S5 Results" 클릭
   → post_started_ts 기록
   → S5 Reference 섹션 표시
   → Post 필드 활성화
    ↓
5. Post 평가 입력
   → blocking_error_post, technical_accuracy_post, educational_quality_post, evidence_comment_post
   → (변경 시) change_reason_code, change_note
    ↓
6. "Submit Post-S5 Rating" 클릭
   → post_submitted_ts 기록
   → post_duration_sec 계산
   → Post 필드 잠금
   → 평가 완료 (qa_state = "DONE")
```

### 5.2 Pause/Resume 시나리오

#### 시나리오 1: Pre 시작 후 중단 → 재개
- **상태**: `pre_started_ts` 설정됨, `pre_submitted_ts` 비어있음
- **동작**: Pre 필드 편집 가능, 이어서 진행 가능
- **위험**: 없음 (정상 동작)

#### 시나리오 2: Pre 제출 후 중단 → 재개 → Reveal
- **상태**: `pre_submitted_ts` 설정됨, Pre 필드 잠김
- **동작**: "Reveal S5 Results" 버튼 표시, Reveal 가능
- **위험**: 없음 (정상 동작)

#### 시나리오 3: Reveal 후 Post 중단 → 재개
- **상태**: `post_started_ts` 설정됨 (S5 공개됨)
- **동작**: Post 필드 편집 가능, 이어서 진행 가능
- **위험**: 없음 (정상 동작)

### 5.3 데이터 무결성 보장

#### 중복 방지
- `rating_id = CONCATENATE([card_uid], "::", USEREMAIL())`로 고유성 보장
- AppSheet Key 제약으로 자동 중복 방지

#### 완결성 강제
- Pre/Post 제출 시 `Run_If`에서 `pre_is_complete`/`post_is_complete` 체크
- 미완성 제출 방지

#### 변경 로그 필수
- Post 제출 시 `is_changed = TRUE`이면 `change_reason_code`와 `change_note` 필수
- `Run_If` 조건으로 강제

---

## 6. 보안 및 권한 설정

### 6.1 접근 제어

#### 앱 접근 설정
- **경로**: `Settings` → `Security` → `Access`
- **설정**: "Only users in whitelist"
- **사용자 추가**: 평가자 이메일 목록 추가

### 6.2 Security Filter (Table-level)

#### Ratings 테이블
```appsheet
[rater_email] = USEREMAIL()
```

#### Assignments 테이블
```appsheet
[rater_email] = USEREMAIL()
```

**효과**: 평가자는 자신의 데이터만 볼 수 있습니다.

### 6.3 Editable_If 조건

모든 Ratings 필드는 `Editable_If`로 평가자 본인의 데이터만 편집 가능하도록 설정:
- Pre 필드: `ISBLANK([pre_submitted_ts])` (추가로 `rater_email` 체크 불필요 - Security Filter로 이미 제한됨)
- Post 필드: `AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]))`

---

## 7. 성능 최적화

### 7.1 List View 최적화

**원칙**: List View는 가볍게, Detail View에서만 전체 내용 표시

**제거 항목:**
- 대용량 텍스트 필드 (`front`, `back`, `evidence_comment_*`, `change_note`)
- 이미지 (`image_filename`)
- Virtual Columns (`view_question_*`)

**유지 항목:**
- 메타데이터만 (`rating_id`, `qa_state`, timestamps, `flag_followup`)

### 7.2 이미지 처리

**설정:**
- List View: 이미지 표시 안 함
- Detail View: 이미지 표시 (필요 시에만 로드)

**Google Drive 경로:**
- `Data` → `Tables` → `Cards` → `image_filename` → `Type = Image`
- `Image source`: `Google Drive`
- `Image folder`: `images` (Google Drive 폴더 선택)

### 7.3 Sync 설정

**권장 설정:**
- `Settings` → `Sync`
- `Sync mode`: `Automatic`
- `Sync frequency`: `Real-time` (가능한 경우) 또는 `Every 5 minutes`
- `Offline mode`: 활성화 (모바일 사용자용)

### 7.4 Virtual Column 최적화

**원칙:**
- List View에서 Virtual Column 사용 최소화
- Detail View에서만 사용
- 복잡한 SELECT 표현식 피하기

---

## 8. 운영 가이드

### 8.1 초기 설정 절차

#### 1단계: Google Drive 준비
1. Drive 폴더 생성 (예: `MeducAI_QA_AppSheet/`)
2. Google Sheet 생성 (예: `qa_appsheet_db`)
3. `images/` 하위 폴더 생성

#### 2단계: CSV Export
```bash
cd 3_Code/src/tools/final_qa
python export_appsheet_tables.py [RUN_TAG]
```

**출력 파일:**
- `Cards.csv`
- `Groups.csv`
- `S5.csv`
- `Ratings.csv` (템플릿 또는 사전 생성된 행)
- `Assignments.csv`

#### 3단계: Google Sheets Import
1. 각 CSV를 해당 탭에 Import
2. **⚠️ 중요**: Ratings는 "Update existing + Add new" 모드 사용 (절대 "Replace sheet" 사용 금지)

#### 4단계: 이미지 업로드
1. Drive의 `images/` 폴더에 모든 이미지 파일 업로드
2. 파일명이 `Cards.csv`의 `image_filename`과 일치하는지 확인

#### 5단계: AppSheet 설정
1. AppSheet 앱 생성
2. Google Sheets를 데이터 소스로 연결
3. 키(Key) 설정 (Section 2.3 참조)
4. 참조(Reference) 설정 (Section 2.4 참조)
5. Virtual Columns 추가 (Section 3.3, 3.4 참조)
6. 액션(Actions) 추가 (Section 4.1 참조)
7. View 설정 (Section 4.3 참조)
8. Slice 생성 (Section 4.4 참조)
9. Security Filter 설정 (Section 6.2 참조)

### 8.2 데이터 업데이트 절차

#### 새 배정 추가
1. `Assignments.csv` 업데이트
2. Google Sheets의 `Assignments` 탭에 Import
3. Ratings-first 모델 사용 시: `Ratings.csv` 재생성 및 Import

#### 이미지 추가/변경
1. Drive의 `images/` 폴더에 파일 업로드/교체
2. `Cards.csv`의 `image_filename` 업데이트
3. Google Sheets의 `Cards` 탭에 Import

### 8.3 백업 및 복구

#### 정기 백업
- Google Sheets: `파일` → `버전 기록` → `버전 만들기`
- AppSheet: `Settings` → `Backup` → `Download app backup`

#### 복구 절차
1. Google Sheets 버전 복구 또는 백업 파일 Import
2. AppSheet: `Settings` → `Restore` → `Upload backup`

### 8.4 모니터링

#### 데이터 품질 체크
- 미완성 평가: `qa_state != "DONE"`
- 중복 평가: `rating_id` 중복 확인
- 시간 측정 이상: `pre_duration_sec` 또는 `post_duration_sec` 음수/0/비정상적으로 큰 값

#### 사용자 활동 모니터링
- Google Sheets에서 `pre_started_ts`, `pre_submitted_ts`, `post_started_ts`, `post_submitted_ts` 확인
- 중도 포기자: `pre_started_ts`는 있지만 `pre_submitted_ts`가 없는 경우

---

## 9. Known Issues & Data Quality Warnings

### 9.1 Critical: Ratings 시트 시간 계산 오류 ⚠️

**Status**: Open (2026-01-09)  
**Severity**: High (Data Integrity)

**Issue**: Ratings 시트의 `post_duration_sec`와 `s5_duration_sec` 컬럼에 계산 로직 오류가 있습니다.

**Impact**:
- `post_duration_sec`: 98/107개 행에서 s5 경과시간을 잘못 담고 있음 (오류율 91.6%)
- `s5_duration_sec`: 전부 비어있음 (계산/저장 로직 누락)

**분석 시 필수 조치**:
```python
# ❌ 절대 사용 금지
df['post_time'] = df['post_duration_sec']

# ✅ 반드시 타임스탬프로 재계산
df['post_time'] = (df['post_submitted_ts'] - df['post_started_ts']).dt.total_seconds()
df['s5_time'] = (df['s5_submitted_ts'] - df['s5_started_ts']).dt.total_seconds()
```

**상세 문서**: [`handoffs/APPSHEET_TIME_CALCULATION_ISSUE_2026-01-09.md`](handoffs/APPSHEET_TIME_CALCULATION_ISSUE_2026-01-09.md)

**수정 계획**:
1. AppSheet 로직 수정 (post_duration_sec 보호, s5_duration_sec 구현)
2. 기존 데이터 복구 (98개 행 재계산)
3. 검증 스크립트 실행

---

## 10. 문제 해결 가이드

### 9.1 이미지가 보이지 않는 경우

**증상**: Detail View에서 이미지가 표시되지 않음

**해결 방법:**
1. `Data` → `Tables` → `Cards` → `image_filename` → `Type = Image` 확인
2. `Image source = Google Drive` 확인
3. `Image folder` 경로가 Drive의 `images/` 폴더를 가리키는지 확인
4. Drive의 `images/` 폴더 권한 확인:
   - "Anyone with the link can view" 또는
   - 앱 사용자에게 공유됨
5. `Cards.csv`의 `image_filename` 값이 실제 파일명과 일치하는지 확인

### 9.2 버튼이 보이지 않는 경우

**증상**: "Start Pre-S5 Rating" 또는 "Reveal S5 Results" 버튼이 표시되지 않음

**해결 방법:**
1. 액션의 `Show_If` 조건 확인
2. 관련 타임스탬프 컬럼 값 확인 (`pre_started_ts`, `pre_submitted_ts`, `post_started_ts`)
3. Virtual Column (`qa_state`) 값 확인
4. View 설정에서 액션 버튼이 추가되어 있는지 확인

### 9.3 제출이 안 되는 경우

**증상**: "Submit Pre-S5 Rating" 또는 "Submit Post-S5 Rating" 버튼 클릭 시 아무 반응 없음

**해결 방법:**
1. 액션의 `Run_If` 조건 확인
2. 완결성 Virtual Column (`pre_is_complete`, `post_is_complete`) 값 확인
3. 필수 필드가 모두 채워졌는지 확인
4. 변경 로그 필수 조건 확인 (`is_changed = TRUE`일 때 `change_reason_code`, `change_note` 필수)

### 9.4 필드가 편집되지 않는 경우

**증상**: Pre 또는 Post 필드를 편집할 수 없음

**해결 방법:**
1. 컬럼의 `Editable_If` 조건 확인
2. 관련 타임스탬프 컬럼 값 확인
3. Security Filter로 인한 접근 제한 확인

### 9.5 시간 측정이 안 되는 경우

**증상**: `pre_duration_sec` 또는 `post_duration_sec`가 계산되지 않음

**해결 방법:**
1. "Submit Pre-S5 Rating" 또는 "Submit Post-S5 Rating" 액션의 `On success` 액션 확인
2. 계산 수식 확인: `([*_submitted_ts] - [*_started_ts]) * 24 * 60 * 60`
3. `pre_started_ts`와 `pre_submitted_ts` (또는 Post 버전) 값이 모두 채워져 있는지 확인

### 9.6 데드락 문제 (Reveal 후 막힘)

**증상**: "Reveal S5 Results" 버튼 클릭 후 화면이 막히거나 다음 단계로 진행 불가

**원인**: Post 필드에 `Required_If`가 설정되어 있어 Reveal 시점에 행이 "유효하지 않은 상태"가 됨

**해결 방법:**
1. Post 필드의 `Required` 및 `Required_If` 제거
2. "Submit Post-S5 Rating" 액션의 `Run_If`에서 Post 완결성 강제
3. "다음으로 이동" 버튼의 `Show_If`를 `NOT(ISBLANK([post_submitted_ts]))`로 설정

---

## 10. 향후 개선 사항

### 10.1 이미지 경로 자동화

**현재 상태**: 수동으로 Google Drive 경로 설정 필요

**개선 방안:**
- CSV Export 시 이미지 파일명에 전체 Drive URL 포함
- 또는 Google Apps Script로 자동 경로 설정

### 10.2 Admin Undo 기능

**목적**: 실수로 제출한 평가를 관리자가 되돌릴 수 있도록

**구현 방안:**
- `admin_undo_pre_submitted_ts`, `admin_undo_post_submitted_ts` 컬럼 추가
- Admin 전용 "Undo Pre/Post Submission" 액션 추가
- `Show_If`에 `ISADMIN()` 조건 추가

### 10.3 배치 관리 기능

**목적**: 여러 배치를 한 앱에서 관리

**구현 방안:**
- `batch_id` 기반 필터링
- 배치별 진행률 대시보드

### 10.4 모바일 최적화

**현재 상태**: 기본적으로 모바일 지원

**개선 방안:**
- 터치 친화적 UI 조정
- 오프라인 모드 테스트 및 최적화

### 10.5 자동화 스크립트

**목적**: 반복 작업 자동화

**구현 방안:**
- Google Apps Script로 CSV Import 자동화
- 정기 백업 자동화
- 데이터 품질 체크 자동화

---

## 부록

### A. 주요 문서 위치

- **기본 설정 가이드**: `0_Protocol/06_QA_and_Study/QA_Operations/AppSheet_QA_Setup_Guide.md`
- **프로덕션 강화 가이드**: `0_Protocol/06_QA_and_Study/QA_Operations/AppSheet_QA_Production_Hardening.md`
- **구현 체크리스트**: `0_Protocol/06_QA_and_Study/QA_Operations/AppSheet_QA_Implementation_Checklist.md`
- **프로젝트 인계 문서**: `0_Protocol/06_QA_and_Study/QA_Operations/AppSheet_QA_Project_Handover.md`
- **이미지 경로 설정 가이드**: `0_Protocol/06_QA_and_Study/QA_Operations/AppSheet_Image_Path_Fix_Prompt.md`

### B. 코드 위치

- **CSV Export 스크립트**: `3_Code/src/tools/final_qa/export_appsheet_tables.py`
- **데이터 출력**: `2_Data/qa_appsheet_export/[RUN_TAG]/`

### C. 주요 설정 파일

- **Google Sheets**: `MeducAI_QA_AppSheet/qa_appsheet_db`
- **이미지 폴더**: `MeducAI_QA_AppSheet/images/`

### D. 연락처 및 추가 정보

**프로젝트 위치**: `/path/to/workspace/workspace/MeducAI`  
**문서 위치**: `0_Protocol/06_QA_and_Study/QA_Operations/`

**추가 질문이 있으시면:**
1. 위 참고 문서들을 먼저 확인
2. AppSheet 앱 설정에서 각 테이블/뷰/액션 확인
3. Google Sheets에서 실제 데이터 구조 확인

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-01-01  
**작성자**: AI Assistant (based on project documentation)


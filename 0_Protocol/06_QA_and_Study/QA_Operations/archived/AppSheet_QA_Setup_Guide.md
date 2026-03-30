# AppSheet QA Website Setup Guide (Google Sheets + Drive)

**For production use with 200+ items and multiple sessions, see:**  
**[AppSheet QA Production Hardening Guide](./AppSheet_QA_Production_Hardening.md)**

**Goal:** Run the FINAL QA workflow as a **web app** with **images** and **per-rater logging**, without custom web development.

This guide assumes:
- Internal-only access (team), Google login available
- Data exported as CSVs by `3_Code/src/tools/final_qa/export_appsheet_tables.py`

## 1) Create storage in Google Drive

- Create a Drive folder, e.g. `MeducAI_QA_AppSheet/`
- Inside it:
  - Create a Google Sheet, e.g. `qa_appsheet_db`
  - Create a subfolder `images/`

## 2) Import CSVs into Google Sheets

Create tabs with these exact names:
- `Cards`
- `Groups`
- `S5`
- `Ratings`
- `Assignments`

Then import:
- `Cards.csv` → `Cards` tab
- `Groups.csv` → `Groups` tab
- `S5.csv` → `S5` tab
- `Ratings.csv` → `Ratings` tab (header only)
- `Assignments.csv` → `Assignments` tab (header only)

**⚠️ 중요: Ratings 테이블 컬럼 추가**
- AppSheet에서 컬럼을 추가하면 **자동으로 Google Sheets에 반영**됩니다.
- 따라서 Google Sheets를 수동으로 수정할 필요는 없습니다.
- 하지만 CSV export 시 이 컬럼들이 포함되도록 exporter를 업데이트해야 할 수 있습니다.
- 추가되는 컬럼:
  - Pre 시간 측정: `pre_started_ts`, `pre_submitted_ts`, `pre_duration_sec` (Virtual)
  - Post 시간 측정: `post_started_ts`, `post_submitted_ts`, `post_duration_sec` (Virtual)

## 3) Upload images to Drive — Step-by-step

1. Drive 폴더에서 `images/` 폴더 열기 (또는 생성)
2. 로컬에서 생성된 `images/` 폴더의 모든 `.jpg` 파일을 드래그 앤 드롭으로 업로드
3. 업로드 완료 확인 (330개 파일)

### 3.1 AppSheet에서 이미지 컬럼 설정

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Cards` → `image_filename` → `Type = Image`

1. `Data` → `Tables` → `Cards` 클릭
2. `image_filename` 컬럼 클릭
3. `Type` 드롭다운에서 `Image` 선택
4. `Image source`: `Google Drive` 선택
5. `Image folder`: `images` (또는 Drive에서 `images/` 폴더 선택)
6. `Save` 클릭

### 3.2 이미지 표시 확인 (빠른 테스트)

**AppSheet 메뉴 경로:** `UX` → `Views` → `Cards_Detail` (또는 새로 만들기)

1. `UX` → `Views` → `Cards_Detail` 클릭
2. `+ Add section` → `Column` 선택
3. `Column`: `image_filename` 선택
4. 앱 미리보기에서 `Cards` 한 행을 열어서 **이미지가 보이는지 확인**

**이미지가 안 보이면:**
- `Data` → `Tables` → `Cards` → `image_filename` → `Image folder` 경로가 Drive의 `images/` 폴더를 가리키는지 확인
- Drive에서 `images/` 폴더 권한이 "Anyone with the link can view" 또는 앱 사용자에게 공유되어 있는지 확인

### 4.1 Keys (critical) — Step-by-step

**AppSheet 메뉴 경로:** `Data` → `Tables` → `[테이블명]` → `Key column`

각 테이블마다:
1. 왼쪽 사이드바에서 `Data` 클릭
2. `Tables` 섹션에서 테이블 선택 (예: `Cards`)
3. `Key column` 드롭다운에서 키 컬럼 선택:
   - `Cards` → `card_uid` 선택
   - `Groups` → `group_id` 선택
   - `S5` → `card_uid` 선택
   - `Ratings` → `rating_id` 선택
   - `Assignments` → `assignment_id` 선택

**중요:** 각 테이블마다 반복해서 설정해야 함.

### 4.2 Refs (연결) — Step-by-step

**AppSheet 메뉴 경로:** `Data` → `Tables` → `[테이블명]` → `[컬럼명]` → `Type` = `Reference`

각 Ref마다:
1. `Data` → `Tables` → `Cards` 클릭
2. `group_id` 컬럼 클릭
3. `Type` 드롭다운에서 `Reference` 선택
4. `Reference table`에서 `Groups` 선택
5. `Reference column`에서 `group_id` 선택
6. `Save` 클릭

나머지 Ref도 동일하게:
- `S5` 테이블 → `card_uid` 컬럼 → Type = `Reference` → Reference table = `Cards`, Reference column = `card_uid`
- `Ratings` 테이블 → `card_uid` 컬럼 → Type = `Reference` → Reference table = `Cards`, Reference column = `card_uid`
- `Assignments` 테이블 → `card_uid` 컬럼 → Type = `Reference` → Reference table = `Cards`, Reference column = `card_uid`

## 4.3 Master table PDF (recommended for “table view” without parsing)

We now provide a per-group PDF that renders the markdown master table nicely.

- Ensure you also upload the folder `group_table_pdfs/` next to the Sheet (same Drive folder).
- In `Groups`, set `master_table_pdf_file` column type to **File**
  - Values look like: `group_table_pdfs/MT__...__grp_xxx.pdf`
  - AppSheet will open the PDF in a viewer when tapped.

## 5) Ratings table: per-rater identity & row key — Step-by-step

**목적:** 평가자가 로그인하면 자동으로 이메일이 기록되고, `rating_id`가 자동 생성되어 중복 방지.

### 5.1 `rater_email` 설정

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `rater_email` 컬럼

1. `Data` → `Tables` → `Ratings` 클릭
2. `rater_email` 컬럼 클릭
3. `Type` 드롭다운에서 `Email` 선택
4. `Initial value` 필드에 `USEREMAIL()` 입력
5. `Editable` 체크박스 **해제** (비활성화)
6. `Save` 클릭

### 5.2 `rating_id` 설정

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `rating_id` 컬럼

1. `Data` → `Tables` → `Ratings` 클릭
2. `rating_id` 컬럼 클릭
3. `Type` 드롭다운에서 `Text` 선택
4. `Initial value` 필드에 아래 식 입력:
   ```
   CONCATENATE([card_uid],"::",USEREMAIL())
   ```
5. `Editable` 체크박스 **해제** (비활성화)
6. `Save` 클릭

**결과:** 새 행 생성 시 `rating_id`가 자동으로 `grp_xxx::DERIVED:yyy__Q1__0::user@example.com` 형태로 생성됨.

## 6) Implement FINAL QA flow (Pre → Reveal → Post) — Step-by-step

This follows `0_Protocol/06_QA_and_Study/FINAL_QA_Form_Design.md`.

### 6.1 Pre-S5 submission lock — Step-by-step

**목적:** Pre 입력 후 제출하면 Pre 필드를 잠가서 불변성 보장.

#### 6.1.1 Pre 평가 타임스탬프 컬럼 추가

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `+ Add column`

**6.1.1.1 `pre_started_ts` 컬럼 추가 (평가 시작 시각)**

1. `Data` → `Tables` → `Ratings` 클릭
2. `+ Add column` 클릭
3. 컬럼명: `pre_started_ts`
4. `Type`: `Date/Time` 선택
5. `Save` 클릭

**6.1.1.2 `pre_submitted_ts` 컬럼 추가 (평가 제출 시각)**

1. `Data` → `Tables` → `Ratings` 클릭
2. `+ Add column` 클릭
3. 컬럼명: `pre_submitted_ts`
4. `Type`: `Date/Time` 선택
5. `Save` 클릭

**6.1.1.3 `pre_duration_sec` 컬럼 추가 (편집 시간 저장용)**

**방법 1: AppSheet에서 직접 추가 (권장)**

1. `Data` → `Tables` → `Ratings` 클릭
2. `+ Add column` 버튼 클릭 (테이블 상단 또는 컬럼 목록 오른쪽에 있음)
3. 컬럼명: `pre_duration_sec` 입력
4. `Type` 드롭다운에서 `Number` 선택 (Virtual이 아님!)
5. `Editable` 체크박스 **해제** (비활성화 - 액션에서만 업데이트)
6. `Save` 클릭

**방법 2: Google Sheets에서 직접 추가 (대안)**

AppSheet에서 `+ Add column` 버튼을 찾을 수 없다면:

1. Google Sheets에서 `Ratings` 탭 열기
2. 헤더 행에 새 컬럼 추가: `pre_duration_sec`
3. AppSheet로 돌아가서 `Data` → `Tables` → `Ratings` 클릭
4. 새로 추가된 `pre_duration_sec` 컬럼이 자동으로 인식됨
5. 컬럼 클릭 → `Type`을 `Number`로 설정
6. `Editable` 체크박스 **해제**
7. `Save` 클릭

**설명:** 
- 이 컬럼은 "Submit Pre-S5 Rating" 액션에서 자동으로 계산되어 저장됩니다.
- 논문 작성 시 CSV에서 이 값을 직접 사용할 수 있습니다.

#### 6.1.1.1 ⚠️ 자동 저장 및 작업 연속성

**AppSheet의 자동 저장 동작:**
- AppSheet는 Detail view에서 필드를 편집하면 **자동으로 저장**됩니다 (Google Sheets에 즉시 반영).
- 별도의 "Save" 버튼을 누르지 않아도 필드 편집 시 자동 저장됩니다.
- 이로 인해 `pre_submitted_ts`가 저장 시점에 채워지는 문제가 발생할 수 있습니다 (6.1.5 참조).

**작업 연속성:**
- ✅ **작업을 중단하고 나중에 이어서 할 수 있습니다.**
- Detail view를 닫았다가 다시 열면, 이전에 입력한 내용이 그대로 유지됩니다.
- Pre 평가를 완료하지 않아도 나중에 다시 열어서 계속 진행할 수 있습니다.
- 단, "Submit Pre-S5 Rating" 액션을 실행하기 전까지는 `pre_submitted_ts`가 비어있으므로 Pre 필드를 계속 편집할 수 있습니다.

**주의사항:**
- Pre 필드 편집 중에 Detail view를 닫으면 자동 저장되지만, `pre_submitted_ts`는 채워지지 않습니다.
- "Submit Pre-S5 Rating" 버튼을 클릭해야만 `pre_submitted_ts`가 채워지고 Pre 필드가 잠깁니다.
- Post 평가도 마찬가지로 자동 저장되며, 언제든지 이어서 진행할 수 있습니다.

**✅ 평가 도중 닫아도 문제 없음:**
- 한 문제(카드) 평가 도중에 Detail view를 닫아도 **문제가 없습니다**.
- 자동 저장은 되지만, `pre_submitted_ts`는 "Submit Pre-S5 Rating" 버튼을 클릭하기 전까지는 **비어있습니다**.
- 따라서 나중에 다시 열었을 때도 Pre 필드를 계속 편집할 수 있습니다 (`Editable_If = ISBLANK([pre_submitted_ts])` 조건 때문에).
- **"Submit Pre-S5 Rating" 버튼을 클릭하기 전까지는 언제든지 이어서 평가할 수 있습니다.**

#### 6.1.2 Pre 필드들을 "제출 전에만 편집 가능"으로 설정

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `[Pre 컬럼명]` → `Editable`

각 Pre 필드마다 (`blocking_error_pre`, `technical_accuracy_pre`, `educational_quality_pre`, `evidence_comment_pre`):
1. `Data` → `Tables` → `Ratings` 클릭
2. Pre 컬럼 클릭 (예: `blocking_error_pre`)
3. `Editable` 섹션에서 `Editable_If` 선택
4. `Editable_If` 필드에 아래 식 입력:
   ```
   ISBLANK([pre_submitted_ts])
   ```
5. `Save` 클릭

**의미:** `pre_submitted_ts`가 비어있을 때만 편집 가능.

#### 6.1.3 Pre 필드 타입 설정 (Ratings.csv 템플릿에 이미 있지만 확인)

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `[컬럼명]` → `Type`

각 Pre 필드마다:

**`blocking_error_pre`:**
1. `Data` → `Tables` → `Ratings` → `blocking_error_pre` 클릭
2. `Type` 드롭다운에서 `Yes/No` 선택
3. `Save`

**`technical_accuracy_pre`:**
1. `Data` → `Tables` → `Ratings` → `technical_accuracy_pre` 클릭
2. `Type` 드롭다운에서 `Enum` 선택
3. **`Options` 필드가 나타남** → 아래 값들을 **각각 한 줄씩** 입력:
   ```
   0
   0.5
   1
   ```
   (또는 콤마로 구분: `0, 0.5, 1`)
4. `Save`

**`educational_quality_pre`:**
1. `Data` → `Tables` → `Ratings` → `educational_quality_pre` 클릭
2. `Type` 드롭다운에서 `Enum` 선택
3. **`Options` 필드에** 아래 값들을 **각각 한 줄씩** 입력:
   ```
   1
   2
   3
   4
   5
   ```
   (또는 콤마로 구분: `1, 2, 3, 4, 5`)
4. `Save`

**`evidence_comment_pre`:**
1. `Data` → `Tables` → `Ratings` → `evidence_comment_pre` 클릭
2. `Type` 드롭다운에서 `LongText` 선택
3. `Save`

**참고:** Enum 타입을 선택하면 `Options` 입력 필드가 자동으로 나타납니다. 각 옵션은 줄바꿈 또는 콤마로 구분합니다.

#### 6.1.4 Blind View Virtual Columns 추가 (데이터 오염 방지)

**⚠️ 중요:** 평가자가 Start 버튼을 누르기 전까지 문항을 볼 수 없도록 하여 시간 측정 오염을 방지합니다.

**6.1.4.1 `view_question_front` Virtual Column 추가**

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `+ Add column` → `Type = Virtual`

1. `Data` → `Tables` → `Ratings` → `+ Add column`
2. 컬럼명: `view_question_front`
3. `Type`: `Virtual` 선택
4. `Virtual column expression`에 아래 식 입력:
   ```
   [card_uid].[front]
   ```
   **설명:** Cards 테이블의 `front` 필드를 참조합니다.
5. `Show_If` (컬럼이 보이는 조건):
   ```
   ISNOTBLANK([pre_started_ts])
   ```
   **설명:** "Start Pre-S5 Rating" 버튼을 눌러야만 문항이 보입니다.
6. `Save` 클릭

**6.1.4.2 `view_question_image` Virtual Column 추가**

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `+ Add column` → `Type = Virtual`

1. `Data` → `Tables` → `Ratings` → `+ Add column`
2. 컬럼명: `view_question_image`
3. `Type`: `Virtual` 선택
4. `Virtual column expression`에 아래 식 입력:
   ```
   [card_uid].[image_filename]
   ```
   **설명:** Cards 테이블의 `image_filename` 필드를 참조합니다.
5. `Show_If` (컬럼이 보이는 조건):
   ```
   ISNOTBLANK([pre_started_ts])
   ```
   **설명:** "Start Pre-S5 Rating" 버튼을 눌러야만 이미지가 보입니다.
6. `Save` 클릭

**⚠️ 중요:**
- 이 Virtual Columns는 **Detail View에서만 사용**합니다.
- List View에서는 절대 표시하지 않습니다 (데이터 오염 방지).
- Cards 테이블의 자동 생성 Reference(Related Cards)는 Detail View에서 제거해야 합니다 (6.1.7 참조).

#### 6.1.5 Pre 평가 완결성 체크용 Virtual Column 추가

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `+ Add column` → `Type = Virtual`

1. `Data` → `Tables` → `Ratings` → `+ Add column`
2. 컬럼명: `pre_is_complete`
3. `Type`: `Virtual` 선택
4. `Virtual column expression`에 아래 식 입력:
   ```
   AND(
     ISNOTBLANK([blocking_error_pre]),
     ISNOTBLANK([technical_accuracy_pre]),
     ISNOTBLANK([educational_quality_pre]),
     OR(
       [blocking_error_pre]=FALSE,
       NUMBER([educational_quality_pre]) > 2,
       ISNOTBLANK([evidence_comment_pre])
     )
   )
   ```
   **설명:**
   - Pre 평가의 필수 필드 3개(blocking_error, technical_accuracy, overall_quality)가 모두 채워져야 합니다.
   - 조건부 필수: blocking_error=TRUE이거나 overall_quality ≤ 2인 경우 evidence_comment도 필요합니다.
   - Enum 필드는 문자열로 저장될 수 있으므로 `NUMBER()`로 변환하여 비교합니다.
5. `Save` 클릭

#### 6.1.5 `evidence_comment_pre` 조건부 필수 설정 (선택사항)

**참고:** `pre_is_complete` Virtual Column에서 이미 완결성을 체크하므로, 컬럼 레벨의 `Required_If`는 선택사항입니다. 
하지만 UX상 사용자에게 즉시 피드백을 주고 싶다면 아래 설정을 추가할 수 있습니다.

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `evidence_comment_pre` → `Required_If`

1. `Data` → `Tables` → `Ratings` → `evidence_comment_pre` 클릭
2. `Required_If` 필드에 아래 식 입력:
   ```
   OR([blocking_error_pre]=TRUE, NUMBER([educational_quality_pre]) <= 2)
   ```
3. `Save` 클릭

#### 6.1.6 "Start Pre-S5 Rating" 액션 추가 (평가 시작)

**AppSheet 메뉴 경로:** `UX` → `Actions` → `+ Add action`

1. `UX` → `Actions` 클릭
2. `+ Add action` 클릭
3. `Action name`: `Start Pre-S5 Rating`
4. `Table`: `Ratings` 선택
5. `Action type`: `Update row` 선택
6. `Row`: `Current row` 선택
7. `Update column`: `pre_started_ts` 선택
8. `Update value`: `NOW()` 입력
9. `Show_If` (액션 버튼이 보이는 조건): 아래 식 입력
   ```
   ISBLANK([pre_started_ts])
   ```
   **설명:** 평가를 시작하기 전에만 버튼이 보입니다.
10. `Run_If` (액션이 실행되는 조건): 동일하게 설정
   ```
   ISBLANK([pre_started_ts])
   ```
11. `Save` 클릭

#### 6.1.7 "Submit Pre-S5 Rating" 액션 추가 (평가 제출)

**AppSheet 메뉴 경로:** `UX` → `Actions` → `+ Add action`

**중요:** AppSheet의 "Update row" 액션은 한 번에 하나의 컬럼만 업데이트할 수 있으므로, 두 개의 액션을 순차적으로 실행해야 합니다.

**6.1.6.1 "Submit Pre-S5 Rating (Step 1)" 액션 추가**

1. `UX` → `Actions` 클릭
2. `+ Add action` 클릭
3. `Action name`: `Submit Pre-S5 Rating (Step 1)`
4. `Table`: `Ratings` 선택
5. `Action type`: `Update row` 선택
6. `Row`: `Current row` 선택
7. `Update column`: `pre_submitted_ts` 선택
8. `Update value`: `NOW()` 입력
9. `Show_If` (액션 버튼이 보이는 조건): 아래 식 입력
   ```
   AND(NOT(ISBLANK([pre_started_ts])), ISBLANK([pre_submitted_ts]))
   ```
   **설명:** 평가를 시작했고(`pre_started_ts`가 채워져 있음) 아직 제출하지 않았을 때만 버튼이 보입니다.
10. `Run_If` (액션이 실행되는 조건 - **필수**: 여기서 Pre 완결성을 강제):
   ```
   AND(
     NOT(ISBLANK([pre_started_ts])),
     ISBLANK([pre_submitted_ts]),
     [pre_is_complete]
   )
   ```
   **설명:** 
   - 평가를 시작했고 아직 제출하지 않았으며
   - Pre 평가가 완결된 경우에만 제출 가능합니다.
   - 이렇게 하면 미완성 상태에서 실수로 제출하여 잠겨버리는 문제를 방지할 수 있습니다.
11. `On success` → `+ Add action` → `Update row` 선택
12. `Update column`: `pre_duration_sec` 선택
13. `Update value`: 아래 식 입력
   ```
   ([pre_submitted_ts] - [pre_started_ts]) * 24 * 60 * 60
   ```
   **설명:** 
   - `pre_submitted_ts`가 방금 업데이트되었으므로, 두 시각의 차이를 초(seconds) 단위로 계산합니다.
   - 날짜/시간 차이는 일(day) 단위로 반환되므로 `* 24 * 60 * 60`을 곱합니다.
14. `Save` 클릭

**⚠️ 편집 시간 자동 계산 및 저장:**
- "Start Pre-S5 Rating" 버튼을 클릭하면 `pre_started_ts`가 기록됩니다.
- "Submit Pre-S5 Rating (Step 1)" 버튼을 클릭하면:
  - `pre_submitted_ts`가 `NOW()`로 기록됩니다.
  - `On success` 액션으로 `pre_duration_sec`가 자동으로 계산되어 저장됩니다.
- 이렇게 하면 편집 시간이 Google Sheets에 저장되어 CSV export 시 포함됩니다.

**Effect (효과):**
- `view_question_front`와 `view_question_image` Virtual Columns가 화면에 나타남 (블라인드 해제)
- Pre 입력 필드가 편집 가능해짐 (`Editable_If = ISBLANK([pre_submitted_ts])`)

#### 6.1.8 Ratings Detail View 설정 (Blind View 구현)

**⚠️ 매우 중요:** Detail View의 컬럼 순서와 Show_If 설정이 데이터 오염 방지의 핵심입니다.

**AppSheet 메뉴 경로:** `UX` → `Views` → `Ratings_Detail` (또는 새로 만들기)

**6.1.8.1 컬럼 순서 설정**

Detail View에서 컬럼을 다음 순서로 배치합니다:

1. **"Start Pre-S5 Rating" (Action Button)**
   - `Show_If`: `ISBLANK([pre_started_ts])`
   - 가장 위에 배치

2. **`view_question_front` (Virtual Column)**
   - `Show_If`: `ISNOTBLANK([pre_started_ts])`
   - Start 버튼을 누르기 전까지 숨김

3. **`view_question_image` (Virtual Column)**
   - `Show_If`: `ISNOTBLANK([pre_started_ts])`
   - Start 버튼을 누르기 전까지 숨김

4. **[Pre Input Fields]**
   - `blocking_error_pre`, `technical_accuracy_pre`, `educational_quality_pre`, `evidence_comment_pre`
   - `Editable_If`: `ISBLANK([pre_submitted_ts])`
   - Start 버튼을 누르기 전까지 편집 불가 (이미 `Editable_If`로 제어됨)

5. **"Submit Pre-S5 Rating" (Action Button)**
   - `Show_If`: `AND(NOT(ISBLANK([pre_started_ts])), ISBLANK([pre_submitted_ts]))`

6. **"Reveal S5 Results" (Action Button)**
   - `Show_If`: `AND(NOT(ISBLANK([pre_submitted_ts])), ISBLANK([post_started_ts]))`

7. **[S5 Reference Section]**
   - Reference type: `Cards` → `S5` (via `card_uid`)
   - `Show_If`: `NOT(ISBLANK([post_started_ts]))`
   - Reveal 버튼을 누르기 전까지 숨김

8. **[Post Input Fields]**
   - `blocking_error_post`, `technical_accuracy_post`, `educational_quality_post`, `evidence_comment_post`
   - `Editable_If`: `AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]))`
   - Reveal 버튼을 누르면 `post_started_ts`가 설정되어 편집 가능해짐

9. **[Change Log Fields]** ⚠️ **중요: Show_If 설정 필요**
   - `change_reason_code`
     - `Show_If`: `[is_changed]` ⚠️ **Detail View에서 설정 필요**
     - `Editable_If`: `[is_changed]` (컬럼 레벨에서 설정)
     - `Required_If`: `[is_changed]` (컬럼 레벨에서 설정)
   - `change_note`
     - `Show_If`: `AND([is_changed], [change_reason_code] = "OTHER")` ⚠️ **Detail View에서 설정 필요**
     - `Editable_If`: `AND([is_changed], [change_reason_code] = "OTHER")` (컬럼 레벨에서 설정)
     - `Required_If`: `AND([is_changed], [change_reason_code] = "OTHER")` (컬럼 레벨에서 설정)

10. **"Submit Post-S5 Rating" (Action Button)**
   - `Show_If`: `AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]))`

**6.1.8.2 Cards 테이블 자동 생성 Reference 제거**

**⚠️ Critical:** AppSheet가 자동으로 생성하는 "Related Cards" Reference를 Detail View에서 제거해야 합니다.

**Why:** 이 Reference가 있으면 Start 버튼을 누르기 전에도 답(S5 결과)을 볼 수 있습니다.

**Procedure:**
1. `UX` → `Views` → `Ratings_Detail` 클릭
2. "Related Cards" 또는 "Cards" Reference 섹션 찾기
3. 해당 섹션 삭제 또는 `Show_If`를 `FALSE`로 설정
4. 대신 `view_question_front`와 `view_question_image` Virtual Columns만 사용

**6.1.8.3 Detail View 설정 단계**

1. `UX` → `Views` → `Ratings_Detail` 클릭 (또는 새로 만들기)
2. 위의 순서대로 컬럼/액션 추가
3. 각 컬럼의 `Show_If` 조건 설정
4. Cards 테이블의 자동 생성 Reference 제거 확인
5. `Save`

### 6.2 Starting View 및 List View 설정 (데이터 오염 방지)

**⚠️ Critical:** 카드를 미리 봐서(Peeking) 난이도 체감 시간이 오염되는 것을 방지합니다.

#### 6.2.1 Starting View 설정

**AppSheet 메뉴 경로:** `Settings` → `UX` → `Options` → `General`

1. `Settings` → `UX` → `Options` → `General` 클릭
2. `Starting View`: `Ratings` 선택 (Cards가 아님!)
3. `Save`

**Reason:** 
- Cards 테이블을 Starting View로 설정하면 평가자가 문항을 미리 볼 수 있습니다
- Ratings를 Starting View로 설정하여 평가 시작 전까지 완전히 블라인드 상태를 유지합니다

#### 6.2.2 Ratings List View 최적화

**AppSheet 메뉴 경로:** `UX` → `Views` → `Ratings_List` (또는 새로 만들기)

**목적:** 목록에서 문항 내용을 추측할 수 없게 하여, Start 버튼을 누르기 전까지 완전히 블라인드 상태를 유지합니다.

**Allowed columns in list view:**
- `rating_id` (or custom "Case ID")
- `qa_state` (status icon)
- `pre_started_ts`, `pre_submitted_ts`
- `post_started_ts`, `post_submitted_ts`
- `flag_followup` (if exists)

**⚠️ 절대 포함하지 말 것:**
- `front`, `back` (문항 내용 — 데이터 오염 방지)
- `view_question_front`, `view_question_image` (Virtual Columns — Start 전에는 보이면 안 됨)
- `image_filename` (이미지 — Start 전에는 보이면 안 됨)
- Cards 테이블 Reference

**설정 단계:**
1. `UX` → `Views` → `Ratings_List` 클릭 (또는 새로 만들기)
2. `Type`: `Deck` or `Table` 선택
3. 위의 "Allowed columns"만 추가
4. "Forbidden" 컬럼들은 모두 제거
5. `Save`

### 6.3 Reveal S5 — Step-by-step

**목적:** Pre 제출 후에만 S5 결과를 볼 수 있게 함.

**⚠️ 중요:** `s5_revealed_ts` 컬럼은 사용하지 않습니다. 대신 `post_started_ts`가 S5 공개 여부를 나타냅니다. `post_started_ts`가 있으면 S5가 공개된 것으로 간주합니다.

#### 6.3.1 "Reveal S5 Results" 액션 추가

**AppSheet 메뉴 경로:** `UX` → `Actions` → `+ Add action`

**⚠️ 핵심:** 이 버튼은 이름은 "Reveal S5 Results"이지만, 실제로는 Post 평가 시작 시간(`post_started_ts`)을 기록합니다. `post_started_ts`가 있으면 S5가 공개된 것으로 간주합니다.

1. `UX` → `Actions` → `+ Add action`
2. `Action name`: `Reveal S5 Results`
3. `Table`: `Ratings` 선택
4. `Action type`: `Update row`
5. `Row`: `Current row`
6. `Update column`: `post_started_ts` (여기가 핵심!)
7. `Update value`: `NOW()`
8. `Show_If` (버튼이 보이는 조건):
   ```
   AND(NOT(ISBLANK([pre_submitted_ts])), ISBLANK([post_started_ts]))
   ```
9. **중요:** `Run_If` (액션이 실행되는 조건)도 동일하게 설정:
   ```
   AND(NOT(ISBLANK([pre_submitted_ts])), ISBLANK([post_started_ts]))
   ```
   - `Run_If`가 없으면 버튼이 보이지만 클릭해도 실행되지 않을 수 있습니다.
10. `Save`

**⚠️ 중요: 데드락 방지**
- **Post 필드에 `Required_If`를 설정하면 안 됩니다!**
- Reveal S5 액션이 `post_started_ts`를 채우는 순간, Post 필드가 즉시 Required로 전환되면서 행이 "유효하지 않은 상태"가 되어 액션이 실패하거나 저장/이동이 막힐 수 있습니다.
- 대신 "Submit Post-S5 Rating" 액션의 `Run_If`에서 Post 완결성을 체크하는 방식을 사용합니다 (6.4.7 참조).
- 이렇게 하면 Reveal 시점에는 행이 invalid가 되지 않아서 막힘 현상이 사라지고, Post를 제출하지 않으면 다음으로 못 가게 되어 "Post 필수"도 달성됩니다.

**✅ 편집 시간 자동 계산:**
- **"Start Pre-S5 Rating" 액션을 추가하여 편집 시간을 자동으로 추적할 수 있습니다.**
- 평가 시작 시각(`pre_started_ts`)과 제출 시각(`pre_submitted_ts`)의 차이를 Virtual Column(`pre_duration_sec`)으로 자동 계산합니다.
- 이렇게 하면 사용자가 수동으로 입력할 필요 없이 편집 시간이 자동으로 기록됩니다.
- 자세한 설정 방법은 6.1.1.3과 6.1.5, 6.1.6을 참조하세요.

**🔧 문제 해결:**
- **버튼이 보이지 않는 경우:** `pre_submitted_ts`가 제대로 채워졌는지 확인하세요. "Submit Pre-S5 Rating" 액션이 정상적으로 실행되었는지 확인하세요 (6.1.7 참조).
- **버튼이 보이지만 클릭이 안 되는 경우:** `Run_If` 조건을 추가하세요 (위 9번 단계 참조).
- **액션 실행 후에도 `post_started_ts`가 채워지지 않는 경우:** 액션의 `Update column`이 `post_started_ts`로 설정되어 있고, `Update value`가 `NOW()`로 정확히 설정되었는지 확인하세요.

#### 6.3.2 S5 패널 표시 (Detail view에서)

**AppSheet 메뉴 경로:** `UX` → `Views` → `Ratings_Detail` → `+ Add section`

1. `UX` → `Views` → `Ratings_Detail` (또는 새로 만들기)
2. `+ Add section` 클릭
3. `Section type`: `Reference` 선택
4. `Reference table`: `S5` 선택
5. `Reference path`: `Ratings` → `Cards` (via `card_uid`) → `S5` (via `card_uid`)
6. `Show_If` (섹션이 보이는 조건):
   ```
   NOT(ISBLANK([post_started_ts]))
   ```
   **설명:** `post_started_ts`가 있으면 S5가 공개된 것으로 간주합니다.
7. `Save`

**⚠️ 중요:** Detail View의 컬럼 순서를 업데이트합니다:
- "Reveal S5 Results" 버튼 다음에 S5 Reference 섹션 배치
- "Start Post-S5 Rating" 버튼은 S5 Reference 섹션 다음에 배치 (하지만 이제 Reveal과 Start가 동일한 액션이므로 하나만 표시)

**Effect (효과):**
- S5 참조 섹션(Cards → S5)이 화면에 나타남 (`Show_If = NOT(ISBLANK([post_started_ts]))`)
- Post 입력 필드가 편집 가능해짐 (`Editable_If` 조건 때문에)

### 6.4 Post-S5 — Step-by-step

**목적:** S5 reveal 이후에만 Post 입력 가능, Post 제출 시 완결성 강제, 변경 시 change log 필수.

#### 6.4.1 Post 평가 타임스탬프 컬럼 추가

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `+ Add column`

**6.3.1.1 `post_started_ts` 컬럼 추가 (Post 평가 시작 시각)**

1. `Data` → `Tables` → `Ratings` → `+ Add column`
2. 컬럼명: `post_started_ts`
3. `Type`: `Date/Time` 선택
4. `Save` 클릭

**6.3.1.2 `post_submitted_ts` 컬럼 추가 (Post 평가 제출 시각)**

1. `Data` → `Tables` → `Ratings` → `+ Add column`
2. 컬럼명: `post_submitted_ts`
3. `Type`: `Date/Time` 선택
4. `Save` 클릭

**6.3.1.3 `post_duration_sec` 컬럼 추가 (Post 편집 시간 저장용)**

**방법 1: AppSheet에서 직접 추가 (권장)**

1. `Data` → `Tables` → `Ratings` 클릭
2. `+ Add column` 버튼 클릭 (테이블 상단 또는 컬럼 목록 오른쪽에 있음)
3. 컬럼명: `post_duration_sec` 입력
4. `Type` 드롭다운에서 `Number` 선택 (Virtual이 아님!)
5. `Editable` 체크박스 **해제** (비활성화 - 액션에서만 업데이트)
6. `Save` 클릭

**방법 2: Google Sheets에서 직접 추가 (대안)**

AppSheet에서 `+ Add column` 버튼을 찾을 수 없다면:

1. Google Sheets에서 `Ratings` 탭 열기
2. 헤더 행에 새 컬럼 추가: `post_duration_sec`
3. AppSheet로 돌아가서 `Data` → `Tables` → `Ratings` 클릭
4. 새로 추가된 `post_duration_sec` 컬럼이 자동으로 인식됨
5. 컬럼 클릭 → `Type`을 `Number`로 설정
6. `Editable` 체크박스 **해제**
7. `Save` 클릭

**설명:** 
- 이 컬럼은 "Submit Post-S5 Rating" 액션에서 자동으로 계산되어 저장됩니다.
- 논문 작성 시 CSV에서 이 값을 직접 사용할 수 있습니다.

#### 6.4.2 Post 필드 타입 설정

- `blocking_error_post`: Type = `Yes/No`
- `technical_accuracy_post`: Type = `Enum`, Options = `0`, `0.5`, `1`
- `educational_quality_post`: Type = `Enum`, Options = `1`, `2`, `3`, `4`, `5`
- `evidence_comment_post`: Type = `LongText`
- `change_reason_code`: Type = `Enum`, Options = 아래 7개:
  - `S5_BLOCKING_FLAG`
  - `S5_BLOCKING_FALSE_POS`
  - `S5_QUALITY_INSIGHT`
  - `S5_EVIDENCE_HELPED`
  - `S5_NO_EFFECT`
  - `RATER_REVISION`
  - `OTHER`
- `change_note`: Type = `LongText`

#### 6.4.3 Post 필드들을 "S5 reveal 이후에만 편집 가능, 제출 후 잠금"으로 설정

**⚠️ 중요:** Post 필드의 `Required` 필드는 **비워두거나 `No`로 설정**합니다. `Required_If`를 사용하지 않습니다.
- 이유: Reveal S5 액션과 충돌하여 데드락이 발생할 수 있습니다 (6.3.1 참조).
- 대신 "Submit Post-S5 Rating" 액션의 `Run_If`에서 Post 완결성을 강제합니다 (6.4.7 참조).

각 Post 필드마다 (`blocking_error_post`, `technical_accuracy_post`, `educational_quality_post`, `evidence_comment_post`):
1. `Data` → `Tables` → `Ratings` → `[Post 컬럼명]` 클릭
2. `Editable` → `Editable_If` 선택
3. `Editable_If` 필드에:
   ```
   AND(
     NOT(ISBLANK([post_started_ts])),
     ISBLANK([post_submitted_ts])
   )
   ```
   **설명:**
   - `post_started_ts`가 있으면 S5가 공개된 것으로 간주하므로, 이후에만 입력 가능
   - Post 제출(`post_submitted_ts`) 이후에는 잠금
4. `Required` 필드는 **비워두거나 `No`로 설정**
5. `Save`

#### 6.4.4 Post 완결성 체크용 Virtual Column 추가

**6.3.4.1 `post_is_complete` Virtual Column 추가**

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `+ Add column` → `Type = Virtual`

1. `Data` → `Tables` → `Ratings` → `+ Add column`
2. 컬럼명: `post_is_complete`
3. `Type`: `Virtual` 선택
4. `Virtual column expression`에 아래 식 입력:
   ```
   AND(
     ISNOTBLANK([blocking_error_post]),
     ISNOTBLANK([technical_accuracy_post]),
     ISNOTBLANK([educational_quality_post]),
     OR(
       [blocking_error_post]=FALSE,
       NUMBER([educational_quality_post]) > 2,
       ISNOTBLANK([evidence_comment_post])
     )
   )
   ```
   **설명:**
   - Post 평가의 필수 필드 3개(blocking_error, technical_accuracy, overall_quality)가 모두 채워져야 합니다.
   - 조건부 필수: blocking_error=TRUE이거나 overall_quality ≤ 2인 경우 evidence_comment도 필요합니다.
   - Enum 필드는 문자열로 저장될 수 있으므로 `NUMBER()`로 변환하여 비교합니다.
   - Yes/No, Enum은 "입력 전"이면 BLANK가 될 수 있으니 `ISNOTBLANK()`가 안전합니다.
5. `Save` 클릭

**6.3.4.2 `is_changed` Virtual Column 추가 (변경 감지)**

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `+ Add column` → `Type = Virtual`

1. `Data` → `Tables` → `Ratings` → `+ Add column`
2. 컬럼명: `is_changed`
3. `Type`: `Virtual` 선택
4. `Virtual column expression`에 아래 식 입력:
   ```
   AND(
     [post_is_complete],
     OR(
       [blocking_error_post] <> [blocking_error_pre],
       [technical_accuracy_post] <> [technical_accuracy_pre],
       [educational_quality_post] <> [educational_quality_pre],
       [evidence_comment_post] <> [evidence_comment_pre],
       [image_blocking_error_post] <> [image_blocking_error_pre],
       [image_anatomical_accuracy_post] <> [image_anatomical_accuracy_pre],
       [image_quality_post] <> [image_quality_pre],
       [image_text_consistency_post] <> [image_text_consistency_pre]
     )
   )
   ```
   **설명:**
   - **중요:** `post_is_complete`로 가드하여 Post가 완결된 뒤에만 변경 판단을 수행합니다.
   - 기존처럼 Post가 비어있는 상태에서 비교가 일어나면 "BLANK ≠ 값"으로 인해 변경으로 오판될 수 있습니다.
   - 카드 레벨 평가 항목(blocking_error, technical_accuracy, overall_quality, evidence_comment)과 이미지 평가 항목(image_blocking_error, image_anatomical_accuracy, image_quality, image_text_consistency) 모두 포함합니다.
5. `Save` 클릭

**6.3.4.3 `changed_fields` Virtual Column 추가 (변경된 필드 목록)**

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `+ Add column` → `Type = Virtual`

1. `Data` → `Tables` → `Ratings` → `+ Add column`
2. 컬럼명: `changed_fields`
3. `Type`: `Virtual` 선택
4. `Virtual column expression`에 아래 식 입력:
   ```
   IF(
     [post_is_complete],
     TRIM(
       CONCATENATE(
         IF([blocking_error_pre] <> [blocking_error_post], "blocking_error, ", ""),
         IF([technical_accuracy_pre] <> [technical_accuracy_post], "technical_accuracy, ", ""),
         IF([educational_quality_pre] <> [educational_quality_post], "educational_quality, ", ""),
         IF([evidence_comment_pre] <> [evidence_comment_post], "evidence_comment", "")
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
   - 예시 결과: "blocking_error, technical_accuracy" 또는 "overall_quality"
5. `Editable`: 체크 해제 (읽기 전용)
6. `Save` 클릭

#### 6.4.5 Change log 필드 설정

**`change_reason_code` 설정:**
1. `Data` → `Tables` → `Ratings` → `change_reason_code` 클릭
2. `Editable_If`: 변경이 있을 때만 편집 가능
   ```
   [is_changed]
   ```
   **설명:** 변경이 있을 때만 편집 가능
3. `Required_If`: 변경이 있을 때 필수
   ```
   [is_changed]
   ```
   **설명:** 변경이 있을 때 필수 입력
4. `Save`

**`change_note` 설정:**
1. `Data` → `Tables` → `Ratings` → `change_note` 클릭
2. `Editable_If`: change_reason_code가 "OTHER"일 때만 편집 가능
   ```
   AND(
     [is_changed],
     [change_reason_code] = "OTHER"
   )
   ```
   **설명:** 변경이 있고, change_reason_code가 "OTHER"일 때만 편집 가능
3. `Required_If`: change_reason_code가 "OTHER"일 때 필수
   ```
   AND(
     [is_changed],
     [change_reason_code] = "OTHER"
   )
   ```
   **설명:** change_reason_code가 "OTHER"일 때 필수 입력
4. `Save`

#### 6.4.6 "Start Post-S5 Rating" 액션 (선택사항)

**⚠️ 참고:** "Reveal S5 Results" 액션이 이미 `post_started_ts`를 업데이트하므로, 별도의 "Start Post-S5 Rating" 액션은 필요하지 않습니다. 

하지만 UX상 명확성을 위해 별도 버튼을 원한다면:

**AppSheet 메뉴 경로:** `UX` → `Actions` → `+ Add action`

1. `UX` → `Actions` → `+ Add action`
2. `Action name`: `Start Post-S5 Rating`
3. `Table`: `Ratings` 선택
4. `Action type`: `Update row`
5. `Row`: `Current row`
6. `Update column`: `post_started_ts`
7. `Update value`: `NOW()`
8. `Show_If` (액션 버튼이 보이는 조건):
   ```
   AND(
     NOT(ISBLANK([pre_submitted_ts])),
     ISBLANK([post_started_ts])
   )
   ```
   **설명:** Pre 제출 후에만 시작 가능하고, 아직 시작하지 않았을 때만 버튼이 보입니다.
9. `Run_If` (액션이 실행되는 조건): 동일하게 설정
   ```
   AND(
     NOT(ISBLANK([pre_submitted_ts])),
     ISBLANK([post_started_ts])
   )
   ```
10. `Save` 클릭

**⚠️ 중요:** Post 필드의 `Editable_If`는 다음으로 설정:
```
AND(
  NOT(ISBLANK([post_started_ts])),
  ISBLANK([post_submitted_ts])
)
```

#### 6.4.7 "Submit Post-S5 Rating" 액션 추가 (Post 강제의 핵심)

**AppSheet 메뉴 경로:** `UX` → `Actions` → `+ Add action`

**중요:** AppSheet의 "Update row" 액션은 한 번에 하나의 컬럼만 업데이트할 수 있으므로, `On success` 액션을 사용하여 duration을 계산합니다.

1. `UX` → `Actions` → `+ Add action`
2. `Action name`: `Submit Post-S5 Rating`
3. `Table`: `Ratings` 선택
4. `Action type`: `Update row`
5. `Row`: `Current row`
6. `Update column`: `post_submitted_ts`
7. `Update value`: `NOW()`
8. `Show_If` (액션 버튼이 보이는 조건):
   ```
   AND(
     NOT(ISBLANK([post_started_ts])),
     ISBLANK([post_submitted_ts])
   )
   ```
   **설명:** `post_started_ts`가 있으면 S5가 공개된 것으로 간주하므로, Post 평가를 시작했으며 아직 제출하지 않았을 때만 버튼이 보입니다.
9. `Run_If` (액션이 실행되는 조건 - **필수**: 여기서 "Post 필수"를 강제):
   ```
   AND(
     NOT(ISBLANK([post_started_ts])),
     ISBLANK([post_submitted_ts]),
     [post_is_complete],
     OR(
       NOT([is_changed]),
       AND(
         ISNOTBLANK([change_reason_code]),
         OR(
           [change_reason_code] <> "OTHER",
           ISNOTBLANK([change_note])
         )
       )
     )
   )
   ```
   **설명:**
   - 변경이 없으면 제출 가능
   - 변경이 있으면 change_reason_code 필수
   - change_reason_code가 "OTHER"인 경우에만 change_note 필수
   **설명:**
   - S5를 본 뒤에만 제출 가능
   - Post 평가를 시작했어야 함
   - Post 3개(Blocking/Accuracy/Quality) + (조건부 코멘트)까지 모두 채워야 제출 가능
   - 변경이 있으면 change_reason/note도 반드시 필요
10. `On success` → `+ Add action` → `Update row` 선택
11. `Update column`: `post_duration_sec` 선택
12. `Update value`: 아래 식 입력
    ```
    ([post_submitted_ts] - [post_started_ts]) * 24 * 60 * 60
    ```
    **설명:** 
    - `post_submitted_ts`가 방금 업데이트되었으므로, 두 시각의 차이를 초(seconds) 단위로 계산합니다.
    - 날짜/시간 차이는 일(day) 단위로 반환되므로 `* 24 * 60 * 60`을 곱합니다.
13. `Save`

**⚠️ Post 편집 시간 자동 계산 및 저장:**
- "Start Post-S5 Rating" 버튼을 클릭하면 `post_started_ts`가 기록됩니다.
- "Submit Post-S5 Rating" 버튼을 클릭하면:
  - `post_submitted_ts`가 `NOW()`로 기록됩니다.
  - `On success` 액션으로 `post_duration_sec`가 자동으로 계산되어 저장됩니다.
- 이렇게 하면 Post 편집 시간이 Google Sheets에 저장되어 CSV export 시 포함됩니다.

**📝 Google Sheets 컬럼 자동 추가:**
- AppSheet에서 컬럼을 추가하면 **자동으로 Google Sheets에 반영**됩니다.
- 따라서 Google Sheets를 수동으로 수정할 필요는 없습니다.
- `post_started_ts`, `post_submitted_ts`, `post_duration_sec` 컬럼은 Google Sheets에 자동으로 추가됩니다.
- CSV export 시 이 컬럼들이 포함되도록 exporter를 업데이트해야 합니다 (2번 섹션 참조).

**✅ 이 방식의 장점:**
- Reveal 시점에는 행이 invalid가 되지 않아서 막힘 현상이 사라집니다.
- Post를 제출하지 않으면 다음으로 못 가게 되어 "Post 필수"도 달성됩니다.
- 중간에 나가도 다시 들어와 이어서 가능합니다 (리셋 불필요).

**Effect (효과):**
- Post 필드가 잠김 (`Editable_If` 조건 때문에)
- 평가 완료 (`qa_state` = "DONE")

#### 6.4.8 "다음으로 이동" 버튼 조건 설정

**목적:** Post 제출 전에는 다음 카드로 이동할 수 없도록 합니다.

현재 "다음 카드"로 넘어가는 방식이 무엇이든(Assignments 기반이든 Ratings 리스트든), 이동 액션의 `Show_If`를 아래로 설정합니다:

```
NOT(ISBLANK([post_submitted_ts]))
```

**설명:**
- Post 제출(`post_submitted_ts`) 후에만 다음으로 이동 가능합니다.
- 이렇게 하면 Post 제출 전에는 구조적으로 다음으로 못 가게 됩니다 (원하는 강제 조건 충족).

## 7) Access control (internal-only)

- Set app access to “Only users in whitelist”.
- Optionally add a `Raters` table (email list) and use a Security Filter.

Recommended Security Filter (table-level, strong):
- `Ratings`: `[rater_email] = USEREMAIL()`
- `Assignments`: `[rater_email] = USEREMAIL()`

## 8) Assignments (optional but recommended)

- If you want raters to only see assigned cards:
  - Populate `Assignments` with (`assignment_id`, `rater_email`, `card_uid`, `card_id`, `batch_id`)
  - Create a slice `MyAssignedCards` where `IN([card_uid], SELECT(Assignments[card_uid], [rater_email]=USEREMAIL()))`

## 9) MCQ 옵션을 Front에 표시하기

**목적:** QA 평가 시 MCQ 카드의 front에서 질문과 선택지가 함께 보이도록.

### 9.1 자동 처리됨 (CSV 생성 시 포함)

**중요:** Exporter가 자동으로 MCQ 타입 카드의 `front`에 선택지를 포함시킵니다.

- **MCQ 타입:** `front` = 질문 + `\n\n[선택지]\nA. 옵션1\nB. 옵션2\n...`
- **BASIC 타입:** `front` = 질문 그대로

**AppSheet에서 추가 설정 불필요:**
- `Cards[front]` 컬럼을 그대로 사용하면 됩니다
- Virtual Column이나 별도 설정이 필요 없습니다

### 9.2 Detail view에서 확인

1. `UX` → `Views` → `Cards_Detail` 클릭
2. `front` 컬럼 추가
3. 앱 미리보기에서 MCQ 카드를 열어서 선택지가 함께 표시되는지 확인

**예상 결과:**
- MCQ 카드: 질문 + 선택지 (A, B, C, D, E)가 함께 표시
- BASIC 카드: 질문만 표시

## 10) S5 수정값 표시 (추후 업데이트 가능)

**목적:** S5가 카드의 front/back을 수정했을 때, 평가자가 원본과 수정본을 비교할 수 있게.

### 10.1 S5 테이블에 수정본 컬럼 추가 (추후 확장 가능)

현재 S5.csv에는 수정본이 없지만, **추후 S5가 수정한 값이 있으면** 아래 컬럼을 추가할 수 있습니다:

- `s5_front_modified` (Text): S5가 수정한 front 텍스트
- `s5_back_modified` (Text): S5가 수정한 back 텍스트
- `s5_modified_timestamp` (Date/Time): 수정 시각

### 10.2 Detail view에서 수정본 표시

**AppSheet 메뉴 경로:** `UX` → `Views` → `Ratings_Detail` → `+ Add section`

1. `UX` → `Views` → `Ratings_Detail` 클릭
2. `+ Add section` → `Reference` 선택
3. `Reference table`: `S5` 선택
4. `Reference path`: `Ratings` → `Cards` (via `card_uid`) → `S5` (via `card_uid`)
5. S5 섹션 내에서:
   - `s5_front_modified` 컬럼 추가 (Show_If: `NOT(ISBLANK([s5_front_modified]))`)
   - `s5_back_modified` 컬럼 추가 (Show_If: `NOT(ISBLANK([s5_back_modified]))`)

### 10.3 원본 vs 수정본 비교 표시

**Virtual Column `has_s5_modifications` 추가:**

1. `Data` → `Tables` → `S5` → `+ Add column`
2. 컬럼명: `has_s5_modifications`
3. `Type`: `Virtual`
4. `Virtual column expression`:
   ```
   OR(
     NOT(ISBLANK([s5_front_modified])),
     NOT(ISBLANK([s5_back_modified]))
   )
   ```

**Detail view에서:**
- 원본: `Cards[front]`, `Cards[back]`
- 수정본: `S5[s5_front_modified]`, `S5[s5_back_modified]` (Show_If: `[has_s5_modifications]`)

### 10.4 추후 업데이트 방법

1. S5가 수정본을 생성하면, exporter 스크립트가 자동으로 `s5_front_modified`, `s5_back_modified` 컬럼을 채움
2. Google Sheets의 `S5` 탭에 새 CSV import (덮어쓰기)
3. AppSheet에서 새 컬럼이 자동으로 인식됨 (Type은 Text로 설정 필요)

**참고:** 현재 샘플 데이터에는 수정본이 없으므로, 이 기능은 전체 데이터에서 S5 수정본이 생성된 후 활성화됩니다.

## 11) 빠른 점검 체크리스트 (데드락 문제 진단)

**현재 증상에 즉시 대응하기 위한 체크리스트:**

### 11.1 Post 컬럼들에 Required_If가 걸려 있나요?

- ✅ **걸려 있다면:** Reveal 액션과 충돌할 가능성이 큽니다.
- ✅ **해결:** Post 컬럼들의 `Required_If`를 삭제하고, 대신 "Submit Post-S5 Rating" 액션의 `Run_If`에서 Post 완결성을 강제하세요 (6.3.6 참조).

### 11.2 Required인데 Editable_If가 false거나 Show_If로 숨겨져 있나요?

- ✅ **이 조합은:** 사용자가 채울 수 없는 Required라서 거의 확실히 막힙니다.
- ✅ **해결:** "컬럼 Required"가 아니라 "Submit Post 액션 Run_If"로 강제하는 방식이 가장 안전합니다.

### 11.3 Reveal S5 이후 "Post 미완료라 다음으로 못 넘어감" 현상이 발생하나요?

- ✅ **원인:** Reveal S5 액션이 `post_started_ts`를 채우는 순간, Post 필드가 즉시 Required로 전환되면서 행이 "유효하지 않은 상태"가 됩니다.
- ✅ **해결:**
  1. Post 필드의 `Required_If`를 모두 제거하세요.
  2. `post_submitted_ts` 컬럼을 추가하세요 (6.4.1).
  3. `post_is_complete` Virtual Column을 추가하세요 (6.4.4).
  4. "Submit Post-S5 Rating" 액션을 추가하고 `Run_If`에서 Post 완결성을 강제하세요 (6.4.7).
  5. "다음으로 이동" 버튼의 `Show_If`를 `NOT(ISBLANK([post_submitted_ts]))`로 설정하세요 (6.4.8).

### 11.4 Pre 평가도 동일 패턴 적용

- ✅ **권장:** Pre 평가도 동일한 패턴을 적용하세요.
  1. `pre_is_complete` Virtual Column 추가 (6.1.4).
  2. "Submit Pre-S5 Rating" 액션의 `Run_If`에 `[pre_is_complete]` 조건 추가 (6.1.6).
  3. 이렇게 하면 "잘못 눌러서 잠겨버림" 자체가 예방됩니다.

### 11.5 리셋 버튼이 필요한가?

- ✅ **일반 평가자용 리셋 버튼:** 보통 불필요 (권장하지 않음)
  - 연구 로그의 불변성을 생각하면, 평가자가 임의로 `post_started_ts`나 `pre_submitted_ts`를 되돌리는 리셋은 데이터 무결성을 해칠 가능성이 큽니다.
- ✅ **대신 필요한 것:** "제출 방지(프리체크)"
  - Pre/Post 모두 `*_is_complete` Virtual Column과 Submit 액션의 `Run_If`로 미완성 제출을 방지하세요.
- ✅ **정말 리셋이 필요하다면:** "관리자 전용 Undo"로 제한
  - Admin만 보이는 Undo 액션(예: undo_reason 기록 포함) 정도는 현실적인 타협입니다.
  - `Show_If`에 관리자 조건(예: Raters 테이블 role lookup)로 제한하세요.

## 12) Blind View 및 순차적 워크플로우 요약

### 12.1 Blind View Virtual Columns

**목적:** 평가자가 Start 버튼을 누르기 전까지 문항을 볼 수 없도록 하여 시간 측정 오염을 방지합니다.

**Virtual Columns:**
- `view_question_front`: `[card_uid].[front]`, `Show_If: ISNOTBLANK([pre_started_ts])`
- `view_question_image`: `[card_uid].[image_filename]`, `Show_If: ISNOTBLANK([pre_started_ts])`

**사용 위치:**
- ✅ Detail View에서만 사용
- ❌ List View에서는 절대 표시하지 않음

### 12.2 순차적 워크플로우 (5단계)

1. **Start Pre-S5 Rating** → 문항 표시 (`view_question_*` Virtual Columns 표시)
2. **Submit Pre-S5 Rating** → Pre 잠금 (`pre_submitted_ts` 기록)
3. **Reveal S5 Results** → S5 결과 표시 및 Post 시작 (`post_started_ts` 기록)
   - **참고:** `post_started_ts`가 있으면 S5가 공개된 것으로 간주합니다.
4. **Submit Post-S5 Rating** → 최종 제출 (`post_submitted_ts` 기록)

### 12.3 View 설정 요약

**Starting View:**
- `Settings` → `UX` → `Options` → `General` → `Starting View = Ratings`

**List View:**
- 문항 내용/이미지 제거, 상태만 표시
- Allowed: `rating_id`, `qa_state`, timestamps
- Forbidden: `front`, `back`, `view_question_*`, `image_filename`, Cards Reference

**Detail View:**
- 컬럼 순서: Start 버튼 → `view_question_*` → Pre 필드 → Submit Pre → Reveal → S5 Reference → Start Post → Post 필드 → Submit Post
- Cards 테이블 자동 생성 Reference 제거

### 12.4 체크리스트

- [ ] `view_question_front` Virtual Column 추가 (6.1.4.1)
- [ ] `view_question_image` Virtual Column 추가 (6.1.4.2)
- [ ] Starting View를 `Ratings`로 설정 (6.2.1)
- [ ] List View에서 문항 내용 제거 (6.2.2)
- [ ] Detail View 컬럼 순서 설정 (6.1.8)
- [ ] Cards 테이블 자동 생성 Reference 제거 (6.1.8.2)
- [ ] 모든 액션의 `Show_If`와 `Run_If` 조건 확인

## 13) Recommended AppSheet views/actions (so it feels like a "QA website")

### 13.1 Views

- `Cards_Browse` (table/deck): browse/search cards
- `Cards_Detail` (detail): show `front`, `back`, `image_filename`, plus a linked Ratings panel
- `MyRatings` (table): raters see only their own rows (also enforced by Security Filter)

### 13.2 "Start rating" action (one-click)

On `Cards`, add an action that opens the Ratings form prefilled for this card:

```
LINKTOFORM(
  "Ratings_Form",
  "card_uid", [card_uid],
  "card_id", [card_id]
)
```

Then, in `Ratings_Form`, make these columns non-editable (or hidden):
- `card_uid`, `card_id`, `rater_email`, `rating_id`

### 13.3 Prevent duplicate rows per rater per card

Because `rating_id = CONCATENATE([card_uid],"::",USEREMAIL())` is the key, AppSheet will reject duplicates automatically.
If you want a smoother UX, add a “Go to my rating” action:

```
LINKTOROW(
  CONCATENATE([card_uid],"::",USEREMAIL()),
  "MyRatings_Detail"
)
```

---

## 14) 전체 데이터(FINAL)로 교체하기

**중요:** 지금 샘플 데이터(11개 그룹)로 만든 AppSheet 설정은 **전체 데이터로 교체해도 그대로 사용 가능**합니다.

### 14.1 왜 재사용 가능한가?

- **스키마가 고정되어 있음**: `Cards/Groups/S5/Ratings/Assignments` 컬럼 구조가 동일
- **키/Ref 설정이 데이터와 무관**: `card_uid`, `group_id` 등 키 구조가 동일
- **액션/조건부 로직이 데이터 독립적**: Pre → Reveal → Post 흐름은 데이터와 무관하게 동작

### 14.2 전체 데이터로 교체하는 방법 (약 10분)

#### 14.2.1 Google Sheets에서 CSV import (덮어쓰기)

1. **Cards 탭:**
   - `파일` → `가져오기` → `Cards.csv` 선택
   - `가져오기 위치`: `현재 시트 바꾸기` 선택
   - `데이터 가져오기` 클릭

2. **Groups 탭:**
   - 동일하게 `Groups.csv` import (덮어쓰기)

3. **S5 탭:**
   - 동일하게 `S5.csv` import (덮어쓰기)

4. **Ratings 탭:**
   - 템플릿이므로 그대로 유지 가능 (또는 빈 상태로 두기)

5. **Assignments 탭:**
   - 새 배정 데이터로 채우기 (평가자별 배정이 달라질 수 있음)

#### 14.2.2 Drive에 새 이미지 업로드

1. Drive에서 `images/` 폴더 열기
2. 기존 이미지 파일 모두 삭제 (또는 새 폴더 생성)
3. 새로 생성된 `images/` 폴더의 모든 이미지 파일 업로드

#### 14.2.3 AppSheet 설정 확인

- **변경 불필요:** 키/Ref, 액션, 조건부 로직 등은 그대로 유지
- **확인만:** 데이터가 제대로 import 되었는지 앱 미리보기에서 확인

### 14.3 주의사항

- **Assignments 테이블**: 평가자 배정이 달라질 수 있으니 새로 채워야 함
- **Ratings 테이블**: 빈 템플릿이므로 그대로 사용 가능 (평가 시작 전)
- **이미지 파일명**: 새 데이터의 `image_filename` 값이 실제 파일명과 일치하는지 확인

---

## Notes

- This setup avoids custom backend work while still supporting:
  - web-based QA
  - images
  - per-rater data capture
  - audit-friendly logs
- **재사용 가능**: 샘플 데이터로 만든 설정은 전체 데이터로 교체해도 그대로 사용 가능


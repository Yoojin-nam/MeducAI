# AppSheet FINAL QA Workflow — Production Hardening Guide

**Status:** Production-ready enhancement  
**Applies to:** FINAL QA workflow with ~200 items, multiple 30-minute sessions  
**Last updated:** 2025-01-01

---

## Overview

This guide extends the base AppSheet QA Setup Guide for production use with real raters evaluating ~200 items across multiple sessions. It addresses pause/resume scenarios, performance optimization, data integrity, and UX improvements for scale.

### Two Implementation Options

**Option A: Minimal-change (Current + Enhancements)**
- Keep existing ad-hoc row creation model
- Add status views and navigation
- Suitable for: <50 items, single-session workflows

**Option B: Ratings-first Queue Model (Recommended for 200+ items)**
- Pre-create all Ratings rows from Assignments
- Explicit queue ordering and state management
- Suitable for: 200+ items, multi-session workflows, production use

**This guide focuses on Option B (Recommended).**

---

## 1. Risk & Bug Scenarios

### 1.1 Pause/Resume Edge Cases

#### Scenario 1: Pre Started but Not Submitted — User Exits and Resumes

**Current behavior:**
- `pre_started_ts` is set, `pre_submitted_ts` is blank
- Pre fields remain editable (`Editable_If = ISBLANK([pre_submitted_ts])`)
- User can resume and continue

**Risk:** None — working as intended

**Prevention:** None needed

---

#### Scenario 2: Pre Submitted — User Exits — Resumes — Then Reveals

**Current behavior:**
- `pre_submitted_ts` is set, Pre fields locked
- "Reveal S5 Results" button visible
- User can reveal and proceed

**Risk:** None — working as intended

**Prevention:** None needed

---

#### Scenario 3: Reveal Pressed — User Exits Mid-Post — Resumes

**Current behavior:**
- `post_started_ts` is set (S5 revealed)
- Post fields editable (`Editable_If = AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]))`)
- User can resume Post evaluation

**Risk:** None — working as intended

**Prevention:** None needed

---

#### Scenario 4: User Fills Post Without Pressing "Reveal S5 Results"

**Current behavior:**
- `post_started_ts` remains blank
- Post fields are not editable (`Editable_If = AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]))`)
- User must press "Reveal S5 Results" to enable Post fields

**Risk:** None — Post fields are locked until Reveal is pressed

**Prevention:** None needed — this is the intended behavior

**Note:** "Reveal S5 Results" action sets `post_started_ts`, which enables Post fields. There is no separate "Start Post" action needed.

---

#### Scenario 5: User Accidentally Presses "Submit Pre/Post"

**Current behavior:**
- Submit actions have `Run_If` with completeness checks
- Incomplete submissions are blocked

**Risk:** Low — completeness checks prevent invalid submissions

**Prevention:**
- Keep completeness checks in `Run_If`
- Add confirmation dialog (AppSheet "Confirm before running" option)
- Consider admin-only undo (see Section 4.4)

---

#### Scenario 6: Network Sync Delays / Offline Edits

**Current behavior:**
- AppSheet auto-saves to Google Sheets
- Offline edits sync when connection restored

**Risk:** 
- Timestamp inconsistencies if device clock is wrong
- Lost edits if sync fails before user closes app

**Prevention:**
- Use `NOW()` (server-side) for timestamps, not client-side time
- AppSheet handles sync automatically
- Add "Last synced" indicator (optional)

---

#### Scenario 7: Duplicate Row Attempts / Missing Row Conditions

**Current behavior:**
- `rating_id` is unique key: `CONCATENATE([card_uid], "::", USEREMAIL())`
- Duplicate creation prevented by key constraint

**Risk:** 
- User might try to create duplicate via LINKTOFORM
- Missing row if assignment not pre-created (in ad-hoc model)

**Prevention:**
- **Ratings-first model (Option B):** Pre-create all rows, eliminate ad-hoc creation
- Add Security Filter to prevent duplicate creation
- Use `rating_id` as key to enforce uniqueness

---

## 2. Mandatory UX/Workflow Improvements for 200 Items

### 2.0 Starting View Configuration (Data Contamination Prevention)

**⚠️ Critical:** 카드를 미리 봐서(Peeking) 난이도 체감 시간이 오염되는 것을 방지합니다.

**AppSheet 메뉴 경로:** `Settings` → `UX` → `Options` → `General`

1. `Settings` → `UX` → `Options` → `General` 클릭
2. `Starting View`: `Ratings` 선택 (Cards가 아님!)
3. `Save`

**Reason:** 
- Cards 테이블을 Starting View로 설정하면 평가자가 문항을 미리 볼 수 있습니다
- Ratings를 Starting View로 설정하여 평가 시작 전까지 완전히 블라인드 상태를 유지합니다

---

## 2.1 Status-Driven Queue Views

### 2.1 Status-Driven Queue Views

**Purpose:** Enable raters to quickly see progress and resume work.

#### 2.1.1 Virtual Column: `qa_state`

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `+ Add column` → `Type = Virtual`

1. `Data` → `Tables` → `Ratings` 클릭
2. `+ Add column` 클릭
3. 컬럼명: `qa_state`
4. `Type`: `Virtual` 선택
5. `Virtual column expression`:
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
6. `Save` 클릭

**States:**
- `TODO`: Not started
- `PRE`: Pre evaluation in progress
- `REVEAL_READY`: Pre submitted, ready to reveal S5
- `REVEAL`: S5 revealed, Post not started
- `POST`: Post evaluation in progress
- `DONE`: Post submitted, complete

---

#### 2.1.2 Queue Views (Slices)

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `+ Add slice`

**MyQueue_Todo:**
1. `Data` → `Tables` → `Ratings` → `+ Add slice`
2. Slice name: `MyQueue_Todo`
3. Filter expression:
   ```
   AND(
     [rater_email] = USEREMAIL(),
     [qa_state] = "TODO"
   )
   ```
4. Sort by: `assignment_order` (ascending)
5. `Save`

**MyQueue_Reveal:**
1. `+ Add slice`
2. Slice name: `MyQueue_Reveal`
3. Filter expression:
   ```
   AND(
     [rater_email] = USEREMAIL(),
     [qa_state] = "REVEAL_READY"
   )
   ```
4. Sort by: `assignment_order` (ascending)
5. `Save`

**MyQueue_Post:**
1. `+ Add slice`
2. Slice name: `MyQueue_Post`
3. Filter expression:
   ```
   AND(
     [rater_email] = USEREMAIL(),
     OR([qa_state] = "REVEAL", [qa_state] = "POST")
   )
   ```
4. Sort by: `assignment_order` (ascending)
5. `Save`

**MyQueue_Done:**
1. `+ Add slice`
2. Slice name: `MyQueue_Done`
3. Filter expression:
   ```
   AND(
     [rater_email] = USEREMAIL(),
     [qa_state] = "DONE"
   )
   ```
4. Sort by: `assignment_order` (ascending)
5. `Save`

---

### 2.3 Ratings Detail View Configuration (Critical for Blind View)

**⚠️ 매우 중요:** Detail View의 컬럼 순서와 Show_If 설정이 데이터 오염 방지의 핵심입니다.

**AppSheet 메뉴 경로:** `UX` → `Views` → `Ratings_Detail` (또는 새로 만들기)

#### 2.3.1 컬럼 순서 (매우 중요)

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
   - **참고:** 이 버튼은 `post_started_ts`를 업데이트합니다. `post_started_ts`가 있으면 S5가 공개된 것으로 간주합니다.

7. **[S5 Reference Section]**
   - Reference type: `Cards` → `S5` (via `card_uid`)
   - `Show_If`: `NOT(ISBLANK([post_started_ts]))`
   - Reveal 버튼을 누르기 전까지 숨김

8. **[Post Input Fields]**
   - `blocking_error_post`, `technical_accuracy_post`, `educational_quality_post`, `evidence_comment_post`
   - `Editable_If`: `AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]))`
   - Reveal 버튼을 누르면 `post_started_ts`가 설정되어 편집 가능해짐

9. **"Submit Post-S5 Rating" (Action Button)**
   - `Show_If`: `AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]))`

#### 2.3.2 Cards 테이블 자동 생성 Reference 제거

**⚠️ Critical:** AppSheet가 자동으로 생성하는 "Related Cards" Reference를 Detail View에서 제거해야 합니다.

**Why:** 이 Reference가 있으면 Start 버튼을 누르기 전에도 답(S5 결과)을 볼 수 있습니다.

**Procedure:**
1. `UX` → `Views` → `Ratings_Detail` 클릭
2. "Related Cards" 또는 "Cards" Reference 섹션 찾기
3. 해당 섹션 삭제 또는 `Show_If`를 `FALSE`로 설정
4. 대신 `view_question_front`와 `view_question_image` Virtual Columns만 사용

#### 2.3.3 Detail View 설정 단계

1. `UX` → `Views` → `Ratings_Detail` 클릭 (또는 새로 만들기)
2. 위의 순서대로 컬럼/액션 추가
3. 각 컬럼의 `Show_If` 조건 설정
4. Cards 테이블의 자동 생성 Reference 제거 확인
5. `Save`

---

### 2.4 "Go to Next Pending" Navigation Action

**AppSheet 메뉴 경로:** `UX` → `Actions` → `+ Add action`

1. `UX` → `Actions` → `+ Add action`
2. `Action name`: `Go to Next Pending`
3. `Table`: `Ratings` 선택
4. `Action type`: `Navigate` 선택
5. `View`: `Ratings_Detail` 선택 (or create dedicated detail view)
6. `Row`: `Any row` 선택
7. `Row expression`: 아래 식 입력
   ```
   SELECT(
     MyQueue_Todo[rating_id],
     [assignment_order] = MIN(SELECT(MyQueue_Todo[assignment_order], [rater_email] = USEREMAIL()))
   )
   ```
   **설명:** 
   - `MyQueue_Todo` slice에서 가장 작은 `assignment_order`를 가진 행을 선택
   - 없으면 `MyQueue_Reveal` 또는 `MyQueue_Post`에서 다음 항목 선택
8. `Show_If`: 
   ```
   OR(
     COUNT(SELECT(MyQueue_Todo[rating_id], [rater_email] = USEREMAIL())) > 0,
     COUNT(SELECT(MyQueue_Reveal[rating_id], [rater_email] = USEREMAIL())) > 0,
     COUNT(SELECT(MyQueue_Post[rating_id], [rater_email] = USEREMAIL())) > 0
   )
   ```
9. `Save`

**Alternative (simpler):** Use a detail view with "Next" button that filters by `qa_state` and `assignment_order`.

---

### 2.5 Flag for Follow-up Feature

**Purpose:** Allow raters to mark items needing review or clarification.

#### 2.3.1 Add Flag Columns

**Google Sheets에서 직접 추가 (권장):**

1. Google Sheets → `Ratings` 탭
2. 헤더 행에 새 컬럼 추가:
   - `flag_followup` (Type: Yes/No)
   - `flag_note` (Type: LongText)

**AppSheet에서 설정:**

**`flag_followup`:**
1. `Data` → `Tables` → `Ratings` → `flag_followup` 클릭
2. `Type`: `Yes/No` 선택
3. `Editable_If`: 
   ```
   [rater_email] = USEREMAIL()
   ```
4. `Save`

**`flag_note`:**
1. `Data` → `Tables` → `Ratings` → `flag_note` 클릭
2. `Type`: `LongText` 선택
3. `Editable_If`: 
   ```
   AND(
     [rater_email] = USEREMAIL(),
     [flag_followup] = TRUE
   )
   ```
4. `Save`

#### 2.3.2 MyFlagged View

1. `Data` → `Tables` → `Ratings` → `+ Add slice`
2. Slice name: `MyFlagged`
3. Filter expression:
   ```
   AND(
     [rater_email] = USEREMAIL(),
     [flag_followup] = TRUE
   )
   ```
4. Sort by: `assignment_order` (ascending)
5. `Save`

---

## 3. Performance Optimization

### 3.1 Image Handling

**Problem:** Loading image thumbnails in list views causes slow performance.

**Solution:**
- **List views:** Do NOT show `image_filename` column
- **Detail view only:** Show images in detail view
- Use `Show_If` to hide image columns in list views

**Configuration:**
1. `UX` → `Views` → `Ratings_List` (or queue views)
2. Remove `image_filename` column from list view
3. Keep images only in `Ratings_Detail` view

---

### 3.2 Avoid Expensive IN(...SELECT...) Patterns

**Problem:** Complex SELECT expressions in filters slow down list views.

**Solution:**
- Use slices with simple filters
- Pre-compute relationships in Ratings table (e.g., `assignment_order`)
- Avoid nested SELECT in `Show_If` for list views

**Example (avoid):**
```
IN([card_uid], SELECT(Assignments[card_uid], [rater_email] = USEREMAIL()))
```

**Example (prefer):**
```
AND(
  [rater_email] = USEREMAIL(),
  [qa_state] = "TODO"
)
```

---

### 3.3 Minimize Heavy Reference Chains

**Problem:** Deep reference chains (e.g., `Ratings → Cards → Groups`) slow down views.

**Solution:**
- Denormalize frequently accessed fields into Ratings
- Use virtual columns sparingly in list views
- Cache lookup values in Ratings table

**Recommended denormalization:**
- `card_uid`, `card_id` already in Ratings (via key)
- Consider adding `group_id`, `entity_name` to Ratings if frequently accessed

---

### 3.4 Sync Behavior Settings

**AppSheet 메뉴 경로:** `Settings` → `Sync`

**Recommendations:**
1. `Sync mode`: `Automatic` (default)
2. `Sync frequency`: `Real-time` (if possible) or `Every 5 minutes`
3. `Offline mode`: Enable for mobile users
4. `Quick edit`: Disable for complex forms (Ratings detail view)

**Configuration:**
1. `Settings` → `Sync`
2. Enable `Offline mode`
3. `UX` → `Views` → `Ratings_Detail` → `Quick edit`: Disable

---

### 3.5 Keep List Views Lean (Data Contamination Prevention)

**Problem:** 
- Large text fields (`front`, `back`) in list views cause slow rendering
- **More critical:** Showing question content in list views allows raters to peek at questions before starting, contaminating time measurements

**Solution:**
- List views: Show only metadata (status, timestamps) — **NO question content**
- Detail view: Show full content only after "Start Pre-S5 Rating" is pressed

**Recommended list view columns:**
- `rating_id` (or custom "Case ID")
- `qa_state` (status icon)
- `pre_started_ts`, `pre_submitted_ts`
- `post_started_ts`, `post_submitted_ts`
- `flag_followup`

**⚠️ 절대 포함하지 말 것:**
- `front`, `back` (문항 내용 — 데이터 오염 방지)
- `view_question_front`, `view_question_image` (Virtual Columns — Start 전에는 보이면 안 됨)
- `evidence_comment_pre`, `evidence_comment_post` (large text)
- `change_note` (large text)
- `image_filename` (이미지 — Start 전에는 보이면 안 됨)
- Cards 테이블의 자동 생성 Reference (Related Cards) — Detail View에서도 제거 필요

**Reason:** 목록에서 문항 내용을 추측할 수 없게 하여, Start 버튼을 누르기 전까지 완전히 블라인드 상태를 유지합니다.

---

## 4. Data Model Hardening

### 4.1 Ratings-First Queue Model (Recommended)

**Rationale:**
- Eliminates ad-hoc row creation issues
- Enables explicit queue ordering
- Supports pause/resume across sessions
- Prevents missing row conditions

#### 4.1.1 Schema Changes

**Ratings table additions (Google Sheets):**

Add these columns to `Ratings` tab header:
- `assignment_order` (Number) — Order within rater's queue
- `flag_followup` (Yes/No) — Flag for follow-up
- `flag_note` (LongText) — Flag note
- `admin_undo_pre_submitted_ts` (Date/Time, optional) — Admin undo timestamp
- `admin_undo_post_submitted_ts` (Date/Time, optional) — Admin undo timestamp
- `undo_reason` (LongText, optional) — Reason for undo

**Existing columns (already in guide):**
- `pre_started_ts`, `pre_submitted_ts`, `pre_duration_sec`
- `post_started_ts`, `post_submitted_ts`, `post_duration_sec`
- **참고:** `s5_revealed_ts` 컬럼은 사용하지 않습니다. `post_started_ts`가 S5 공개 여부를 나타냅니다.

---

#### 4.1.2 Exporter Changes

**File:** `3_Code/src/tools/final_qa/export_appsheet_tables.py`

**Update `export_appsheet_tables()` function:**

Add a new function to generate Ratings.csv with pre-created rows:

```python
def _generate_ratings_template(
    assignments_path: Path,
    cards_path: Path,
    out_path: Path,
) -> None:
    """
    Generate Ratings.csv with pre-created rows for all assignments.
    
    Creates one row per (rater_email, card_uid) from Assignments.
    """
    # Load assignments
    assignments = []
    if assignments_path.exists():
        with assignments_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            assignments = list(reader)
    
    # Load cards to get card_uid mapping
    cards_by_id = {}
    if cards_path.exists():
        with cards_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cards_by_id[row.get("card_id", "")] = row
    
    # Group assignments by rater_email and create Ratings rows
    ratings_rows = []
    rater_card_pairs = set()
    
    for assign in assignments:
        rater_email = assign.get("rater_email", "")
        card_uid = assign.get("card_uid", "")
        card_id = assign.get("card_id", "")
        assignment_id = assign.get("assignment_id", "")
        assignment_order = assign.get("assignment_order", "")
        batch_id = assign.get("batch_id", "")
        
        if not rater_email or not card_uid:
            continue
        
        # Avoid duplicates
        pair_key = (rater_email, card_uid)
        if pair_key in rater_card_pairs:
            continue
        rater_card_pairs.add(pair_key)
        
        rating_id = f"{card_uid}::{rater_email}"
        
        ratings_rows.append({
            "rating_id": rating_id,
            "card_uid": card_uid,
            "card_id": card_id,
            "rater_email": rater_email,
            "assignment_id": assignment_id,
            "assignment_order": int(assignment_order) if assignment_order.isdigit() else 0,
            "batch_id": batch_id,
            # Pre fields (blank initially)
            "blocking_error_pre": "",
            "technical_accuracy_pre": "",
            "educational_quality_pre": "",
            "evidence_comment_pre": "",
            "pre_started_ts": "",
            "pre_submitted_ts": "",
            "pre_duration_sec": "",
            # Post fields (blank initially)
            # Note: s5_revealed_ts is not used. post_started_ts indicates S5 reveal.
            "blocking_error_post": "",
            "technical_accuracy_post": "",
            "educational_quality_post": "",
            "evidence_comment_post": "",
            "post_started_ts": "",
            "post_submitted_ts": "",
            "post_duration_sec": "",
            # Change log
            "change_reason_code": "",
            "change_note": "",
            "changed_fields": "",
            # Flags
            "flag_followup": "0",
            "flag_note": "",
            # Admin undo (optional)
            "admin_undo_pre_submitted_ts": "",
            "admin_undo_post_submitted_ts": "",
            "undo_reason": "",
        })
    
    # Sort by rater_email, then assignment_order
    ratings_rows.sort(key=lambda x: (x["rater_email"], x.get("assignment_order", 0)))
    
    # Write CSV
    fieldnames = [
        "rating_id",
        "card_uid",
        "card_id",
        "rater_email",
        "assignment_id",
        "assignment_order",
        "batch_id",
        "blocking_error_pre",
        "technical_accuracy_pre",
        "educational_quality_pre",
        "evidence_comment_pre",
        "pre_started_ts",
        "pre_submitted_ts",
        "pre_duration_sec",
        "blocking_error_post",
        "technical_accuracy_post",
        "educational_quality_post",
        "evidence_comment_post",
        "post_started_ts",
        "post_submitted_ts",
        "post_duration_sec",
        "change_reason_code",
        "change_note",
        "changed_fields",
        "flag_followup",
        "flag_note",
        "admin_undo_pre_submitted_ts",
        "admin_undo_post_submitted_ts",
        "undo_reason",
    ]
    
    _write_csv(out_path, fieldnames, ratings_rows)
```

**Update `export_appsheet_tables()` to call this function:**

```python
# In export_appsheet_tables() function, replace Ratings.csv template generation:

# Load Assignments if available
assignments_path = out_dir / "Assignments.csv"
cards_path = out_dir / "Cards.csv"

if assignments_path.exists() and cards_path.exists():
    # Generate pre-populated Ratings.csv
    _generate_ratings_template(
        assignments_path=assignments_path,
        cards_path=cards_path,
        out_path=out_dir / "Ratings.csv",
    )
    if verbose:
        ratings_df = pd.read_csv(out_dir / "Ratings.csv")
        print(f"[OK] Wrote: {out_dir / 'Ratings.csv'} ({len(ratings_df)} pre-created rows)")
else:
    # Fallback: template only
    _write_csv(
        out_dir / "Ratings.csv",
        fieldnames,  # Use fieldnames from _generate_ratings_template
        [],
    )
    if verbose:
        print(f"[OK] Wrote: {out_dir / 'Ratings.csv'} (template)")
```

---

#### 4.1.3 Operational Policy: Ratings Import

**⚠️ CRITICAL: Never "Replace Sheet" Import on Ratings**

**Why:** AppSheet may add columns (e.g., virtual columns, computed fields) that are not in CSV. Replacing the sheet would lose these columns.

**Correct procedure:**
1. **Initial setup:** Import Ratings.csv (pre-populated or template)
2. **After AppSheet adds columns:** 
   - **DO NOT** re-import Ratings.csv with "Replace sheet"
   - **DO:** Clear existing rows and append new rows, OR
   - **DO:** Use "Update existing + Add new" import mode
3. **To add new assignments:**
   - Re-run exporter to generate updated Ratings.csv
   - Import with "Update existing + Add new" mode
   - Or manually append new rows in Google Sheets

**AppSheet import settings:**
1. `Data` → `Tables` → `Ratings` → `Import data`
2. Select `Ratings.csv`
3. **Import mode:** `Update existing + Add new` (NOT "Replace sheet")
4. `Key column`: `rating_id`
5. `Import`

---

### 4.2 Assignment Order Stability

**Requirement:** `assignment_order` must be stable across sessions.

**Implementation:**
- Set `assignment_order` in Assignments.csv during initial export
- Use deterministic ordering (e.g., by `card_id`, `batch_id`)
- Do not change `assignment_order` after initial assignment

**Exporter responsibility:**
- Generate stable `assignment_order` values
- Ensure same rater gets same order across re-exports

---

### 4.3 Admin Undo Feature (Optional)

**Purpose:** Allow admins to undo accidental submissions for data integrity recovery.

#### 4.3.1 Add Admin Undo Columns

**Google Sheets:**
- `admin_undo_pre_submitted_ts` (Date/Time)
- `admin_undo_post_submitted_ts` (Date/Time)
- `undo_reason` (LongText)

#### 4.3.2 Admin Undo Actions

**"Undo Pre Submission" (Admin only):**

1. `UX` → `Actions` → `+ Add action`
2. `Action name`: `Admin: Undo Pre Submission`
3. `Table`: `Ratings` 선택
4. `Action type`: `Update row`
5. `Row`: `Current row`
6. `Update column`: `pre_submitted_ts`
7. `Update value`: `BLANK()`
8. `Show_If`: 
   ```
   AND(
     ISADMIN(),  # Or use role-based check: [rater_role] = "admin"
     NOT(ISBLANK([pre_submitted_ts])),
     ISBLANK([admin_undo_pre_submitted_ts])
   )
   ```
9. `On success` → `+ Add action` → `Update row`
10. `Update column`: `admin_undo_pre_submitted_ts`
11. `Update value`: `NOW()`
12. `Save`

**Similar for Post undo.**

**Note:** Undo does not clear `pre_started_ts` or `post_started_ts` to preserve timing data.

---

## 5. Concrete AppSheet Formulas and Configuration

### 5.1 Virtual Column Formulas

#### 5.1.1 `qa_state` (See Section 2.1.1)

Already provided above.

#### 5.1.2 Blind View Virtual Columns (Data Contamination Prevention)

**Purpose:** Prevent raters from seeing question content before starting evaluation (prevents time contamination and bias).

**5.1.2.1 `view_question_front` Virtual Column**

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `+ Add column` → `Type = Virtual`

1. `Data` → `Tables` → `Ratings` → `+ Add column`
2. 컬럼명: `view_question_front`
3. `Type`: `Virtual` 선택
4. `Virtual column expression`:
   ```
   [card_uid].[front]
   ```
   **설명:** Cards 테이블의 `front` 필드를 참조합니다.
5. `Show_If` (컬럼이 보이는 조건):
   ```
   ISNOTBLANK([pre_started_ts])
   ```
   **설명:** "Start Pre-S5 Rating" 버튼을 눌러야만 문항이 보입니다.
6. `Save`

**5.1.2.2 `view_question_image` Virtual Column**

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `+ Add column` → `Type = Virtual`

1. `Data` → `Tables` → `Ratings` → `+ Add column`
2. 컬럼명: `view_question_image`
3. `Type`: `Virtual` 선택
4. `Virtual column expression`:
   ```
   [card_uid].[image_filename]
   ```
   **설명:** Cards 테이블의 `image_filename` 필드를 참조합니다.
5. `Show_If` (컬럼이 보이는 조건):
   ```
   ISNOTBLANK([pre_started_ts])
   ```
   **설명:** "Start Pre-S5 Rating" 버튼을 눌러야만 이미지가 보입니다.
6. `Save`

**⚠️ 중요:**
- 이 Virtual Columns는 **Detail View에서만 사용**합니다.
- List View에서는 절대 표시하지 않습니다 (데이터 오염 방지).
- Cards 테이블의 자동 생성 Reference(Related Cards)는 Detail View에서 제거해야 합니다.

#### 5.1.3 `pre_is_complete` Virtual Column

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `+ Add column` → `Type = Virtual`

1. `Data` → `Tables` → `Ratings` → `+ Add column`
2. 컬럼명: `pre_is_complete`
3. `Type`: `Virtual` 선택
4. `Virtual column expression`:
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
5. `Save`

#### 5.1.4 `post_is_complete` Virtual Column

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `+ Add column` → `Type = Virtual`

1. `Data` → `Tables` → `Ratings` → `+ Add column`
2. 컬럼명: `post_is_complete`
3. `Type`: `Virtual` 선택
4. `Virtual column expression`:
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
5. `Save`

#### 5.1.5 `is_changed` Virtual Column (Guarded by `post_is_complete`)

**AppSheet 메뉴 경로:** `Data` → `Tables` → `Ratings` → `+ Add column` → `Type = Virtual`

1. `Data` → `Tables` → `Ratings` → `+ Add column`
2. 컬럼명: `is_changed`
3. `Type`: `Virtual` 선택
4. `Virtual column expression`:
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
   **설명:** `post_is_complete` 가드로 Post가 완결된 뒤에만 변경 판단을 수행합니다. 카드 레벨 평가 항목과 이미지 평가 항목 모두 포함합니다.
5. `Save`

**Important:** The `post_is_complete` guard prevents false change detection when Post fields are blank.

---

### 5.2 Action Run_If / Show_If Formulas (Sequential Workflow)

**⚠️ 중요:** 반드시 아래 순서대로 실행되도록 `Show_If`와 `Run_If`를 설정합니다.

#### 5.2.1 ① "Start Pre-S5 Rating" (평가 시작)

**AppSheet 메뉴 경로:** `UX` → `Actions` → `+ Add action`

1. `UX` → `Actions` → `+ Add action`
2. `Action name`: `Start Pre-S5 Rating`
3. `Table`: `Ratings` 선택
4. `Action type`: `Update row`
5. `Row`: `Current row`
6. `Update column`: `pre_started_ts`
7. `Update value`: `NOW()`
8. `Show_If` (버튼이 보이는 조건):
   ```
   ISBLANK([pre_started_ts])
   ```
9. `Run_If` (액션이 실행되는 조건):
   ```
   ISBLANK([pre_started_ts])
   ```
10. `Save`

**Effect (효과):**
- `view_question_front`와 `view_question_image` Virtual Columns가 화면에 나타남 (블라인드 해제)
- Pre 입력 필드가 편집 가능해짐 (`Editable_If = ISBLANK([pre_submitted_ts])`)

---

#### 5.2.2 ② "Submit Pre-S5 Rating" (Pre 제출)

**AppSheet 메뉴 경로:** `UX` → `Actions` → `+ Add action`

1. `UX` → `Actions` → `+ Add action`
2. `Action name`: `Submit Pre-S5 Rating`
3. `Table`: `Ratings` 선택
4. `Action type`: `Update row`
5. `Row`: `Current row`
6. `Update column`: `pre_submitted_ts`
7. `Update value`: `NOW()`
8. `Show_If` (버튼이 보이는 조건):
   ```
   AND(
     NOT(ISBLANK([pre_started_ts])),
     ISBLANK([pre_submitted_ts])
   )
   ```
9. `Run_If` (액션이 실행되는 조건 - **필수**: 완결성 체크):
   ```
   AND(
     NOT(ISBLANK([pre_started_ts])),
     ISBLANK([pre_submitted_ts]),
     [pre_is_complete]
   )
   ```
10. `On success` → `+ Add action` → `Update row`
11. `Update column`: `pre_duration_sec`
12. `Update value`: 
    ```
    ([pre_submitted_ts] - [pre_started_ts]) * 24 * 60 * 60
    ```
    **참고:** AppSheet에서 `TOTALSECONDS()` 함수가 지원되지 않으므로, 날짜 차이를 초로 변환하는 수식을 사용합니다.
13. `Save`

**Effect (효과):**
- Pre 필드가 잠김 (`Editable_If = ISBLANK([pre_submitted_ts])` 조건 때문에)
- "Reveal S5 Results" 버튼이 나타남

---

#### 5.2.3 ③ "Reveal S5 Results" (정답 공개)

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
   AND(
     NOT(ISBLANK([pre_submitted_ts])),
     ISBLANK([post_started_ts])
   )
   ```
9. `Run_If` (액션이 실행되는 조건):
   ```
   AND(
     NOT(ISBLANK([pre_submitted_ts])),
     ISBLANK([post_started_ts])
   )
   ```
10. `Save`

**Effect (효과):**
- S5 참조 섹션(Cards → S5)이 화면에 나타남 (`Show_If = NOT(ISBLANK([post_started_ts]))`)
- Post 입력 필드가 편집 가능해짐 (`Editable_If` 조건 때문에)

---

#### 5.2.4 ④ "Start Post-S5 Rating" (선택사항)

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
8. `Show_If` (버튼이 보이는 조건):
   ```
   AND(
     NOT(ISBLANK([pre_submitted_ts])),
     ISBLANK([post_started_ts])
   )
   ```
9. `Run_If` (액션이 실행되는 조건): 동일하게 설정
10. `Save`

**⚠️ 중요:** Post 필드의 `Editable_If`는 다음으로 설정:
```
AND(
  NOT(ISBLANK([post_started_ts])),
  ISBLANK([post_submitted_ts])
)
```

---

#### 5.2.5 ⑤ "Submit Post-S5 Rating" (최종 제출)

**AppSheet 메뉴 경로:** `UX` → `Actions` → `+ Add action`

1. `UX` → `Actions` → `+ Add action`
2. `Action name`: `Submit Post-S5 Rating`
3. `Table`: `Ratings` 선택
4. `Action type`: `Update row`
5. `Row`: `Current row`
6. `Update column`: `post_submitted_ts`
7. `Update value`: `NOW()`
8. `Show_If` (버튼이 보이는 조건):
   ```
   AND(
     NOT(ISBLANK([post_started_ts])),
     ISBLANK([post_submitted_ts])
   )
   ```
9. `Run_If` (액션이 실행되는 조건 - **필수**: 완결성 및 변경 로그 체크):
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
10. `On success` → `+ Add action` → `Update row`
11. `Update column`: `post_duration_sec`
12. `Update value`: 
    ```
    ([post_submitted_ts] - [post_started_ts]) * 24 * 60 * 60
    ```
    **참고:** AppSheet에서 `TOTALSECONDS()` 함수가 지원되지 않으므로, 날짜 차이를 초로 변환하는 수식을 사용합니다.
13. `Save`

**Effect (효과):**
- Post 필드가 잠김 (`Editable_If` 조건 때문에)
- 평가 완료 (`qa_state` = "DONE")

---

### 5.3 Common AppSheet Pitfalls Prevention

#### 5.3.1 Use NUMBER() for Enum Comparisons

**Problem:** Enum values may be stored as strings.

**Solution:**
```
NUMBER([educational_quality_pre]) > 2
```

Not:
```
[educational_quality_pre] > 2  # May fail if string
```

---

#### 5.3.2 Use ISNOTBLANK() for Yes/No and Enum

**Problem:** `ISBLANK()` may not work correctly for Yes/No and Enum fields.

**Solution:**
```
ISNOTBLANK([blocking_error_pre])
```

Not:
```
[blocking_error_pre] <> ""  # May fail
```

---

#### 5.3.3 Prevent "BLANK vs value" False Change Detection

**Problem:** Comparing blank Post fields to Pre values triggers false `is_changed`.

**Solution:** Guard with `post_is_complete`:
```
AND(
  [post_is_complete],  # Guard: only check if Post is complete
  OR(
    [blocking_error_post] <> [blocking_error_pre],
    ...
  )
)
```

---

## 6. Implementation Checklist

### 6.1 Exporter Changes

- [ ] Update `export_appsheet_tables.py`:
  - [ ] Add `_generate_ratings_template()` function
  - [ ] Update `export_appsheet_tables()` to call it when Assignments.csv exists
  - [ ] Add new columns to Ratings.csv: `assignment_order`, `flag_followup`, `flag_note`, admin undo fields
  - [ ] Ensure `pre_duration_sec` and `post_duration_sec` are in CSV

### 6.2 AppSheet Configuration

#### 6.2.1 Virtual Columns

- [ ] Add `qa_state` virtual column
- [ ] Add `pre_is_complete` virtual column
- [ ] Add `post_is_complete` virtual column
- [ ] Update `is_changed` virtual column with `post_is_complete` guard
- [ ] Add `changed_fields` virtual column (변경된 필드 목록 자동 계산)
- [ ] **Add `view_question_front` virtual column** (Blind View)
  - [ ] Expression: `[card_uid].[front]`
  - [ ] `Show_If`: `ISNOTBLANK([pre_started_ts])`
- [ ] **Add `view_question_image` virtual column** (Blind View)
  - [ ] Expression: `[card_uid].[image_filename]`
  - [ ] `Show_If`: `ISNOTBLANK([pre_started_ts])`

#### 6.2.2 Starting View

- [ ] **Configure Starting View:**
  - [ ] `Settings` → `UX` → `Options` → `General` → `Starting View` = `Ratings`
  - [ ] Verify: Cards가 아닌 Ratings가 시작 화면

#### 6.2.3 List Views

- [ ] **Optimize Ratings List View:**
  - [ ] Remove `front`, `back` (question content)
  - [ ] Remove `view_question_front`, `view_question_image` (Virtual Columns)
  - [ ] Remove `image_filename` (images)
  - [ ] Remove Cards 테이블 Reference
  - [ ] Keep only: `rating_id`, `qa_state`, timestamps, `flag_followup`

#### 6.2.4 Detail View

- [ ] **Configure Ratings Detail View:**
  - [ ] Set column order (Section 6.3 참조)
  - [ ] Remove Cards 테이블의 자동 생성 Reference (Related Cards)
  - [ ] Add `view_question_front` with `Show_If` = `ISNOTBLANK([pre_started_ts])`
  - [ ] Add `view_question_image` with `Show_If` = `ISNOTBLANK([pre_started_ts])`
  - [ ] Configure all action buttons with correct `Show_If` conditions
  - [ ] Test: Start 버튼 전에는 문항이 보이지 않음

#### 6.2.5 Slices and Navigation

- [ ] Create queue slices: `MyQueue_Todo`, `MyQueue_Reveal`, `MyQueue_Post`, `MyQueue_Done`
- [ ] Create `MyFlagged` slice
- [ ] Add "Go to Next Pending" navigation action

#### 6.2.6 Actions

- [ ] **Configure all actions with sequential workflow:**
  - [ ] "Start Pre-S5 Rating" (Section 5.2.1)
  - [ ] "Submit Pre-S5 Rating" (Section 5.2.2)
  - [ ] "Reveal S5 Results" (Section 5.2.3)
  - [ ] "Start Post-S5 Rating" (Section 5.2.4)
  - [ ] "Submit Post-S5 Rating" (Section 5.2.5)
- [ ] Update Post field `Editable_If` to require `post_started_ts`
- [ ] Update all action `Run_If` / `Show_If` formulas

#### 6.2.7 Performance and Sync

- [ ] Configure sync behavior (offline mode, quick edit settings)
- [ ] Add admin undo actions (optional)

### 6.3 Google Sheets

- [ ] Add columns to Ratings tab: `assignment_order`, `flag_followup`, `flag_note`, admin undo fields
- [ ] Import Ratings.csv with "Update existing + Add new" mode (NOT "Replace sheet")

### 6.4 Testing

- [ ] Test pause/resume scenarios (all 7 scenarios in Section 1)
- [ ] Test queue navigation
- [ ] Test flag functionality
- [ ] Test performance with 200+ rows
- [ ] Test offline sync
- [ ] Test admin undo (if implemented)

---

## 7. Minimal-Change Option (Option A)

If you prefer to keep the current ad-hoc model:

1. **Skip Section 4.1** (Ratings-first model)
2. **Keep Ratings.csv as template** (header only)
3. **Add Sections 2, 3, 5** (UX improvements, performance, formulas)
4. **Use LINKTOFORM for row creation** (existing method)

**Limitations:**
- No explicit queue ordering
- Potential missing row issues
- Less robust for 200+ items

**Recommendation:** Use Option B (Ratings-first) for production.

---

## 6. UX & Views Configuration Summary

### 6.1 Starting View (진입 화면)

**Settings:** `UX` → `Options` → `General` → `Starting View = Ratings`

**Reason:** 카드를 미리 봐서(Peeking) 난이도 체감 시간이 오염되는 것을 방지합니다.

---

### 6.2 Ratings List View (목록 화면)

**Type:** Deck or Table

**Content:**
- **Primary Header:** `rating_id` or custom "Case ID"
- **Image:** None (절대 이미지를 목록에 노출하지 말 것)
- **Summary:** Status icons only (`qa_state`)

**Reason:** 목록에서 문항 내용을 추측할 수 없게 하여, Start 버튼을 누르기 전까지 완전히 블라인드 상태를 유지합니다.

**Allowed columns in list view:**
- `rating_id` (or custom ID)
- `qa_state` (status icon)
- `pre_started_ts`, `pre_submitted_ts`
- `post_started_ts`, `post_submitted_ts`
- `flag_followup`

**Forbidden in list view:**
- `front`, `back` (question content)
- `view_question_front`, `view_question_image` (Virtual Columns)
- `image_filename` (images)
- Cards 테이블 Reference

---

### 6.3 Ratings Detail View (평가 화면)

**Column Order (매우 중요):**

1. **"Start Pre-S5 Rating" (Action Button)**
   - `Show_If`: `ISBLANK([pre_started_ts])`

2. **`view_question_front` (Virtual Column)**
   - `Show_If`: `ISNOTBLANK([pre_started_ts])`
   - Initially hidden

3. **`view_question_image` (Virtual Column)**
   - `Show_If`: `ISNOTBLANK([pre_started_ts])`
   - Initially hidden

4. **[Pre Input Fields]**
   - Initially hidden (Editable_If로 제어)

5. **"Submit Pre-S5 Rating" (Action Button)**
   - `Show_If`: `AND(NOT(ISBLANK([pre_started_ts])), ISBLANK([pre_submitted_ts]))`

6. **"Reveal S5 Results" (Action Button)**
   - `Show_If`: `AND(NOT(ISBLANK([pre_submitted_ts])), ISBLANK([post_started_ts]))`
   - **참고:** 이 버튼은 `post_started_ts`를 업데이트합니다.

7. **[S5 Reference Section]**
   - `Show_If`: `NOT(ISBLANK([post_started_ts]))`
   - Initially hidden

8. **[Post Input Fields]**
   - `Editable_If`: `AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]))`
   - Initially hidden (Editable_If로 제어)

9. **"Submit Post-S5 Rating" (Action Button)**
   - `Show_If`: `AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]))`

**⚠️ Critical:** Cards 테이블에 대한 자동 생성 Reference(Related Cards)는 뷰에서 제거해야 합니다. 안 그러면 Start 누르기 전에 답을 볼 수 있습니다.

---

## Appendix: Formula Reference

### Complete Virtual Column Expressions

**qa_state:**
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

**pre_is_complete:**
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

**post_is_complete:**
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

**is_changed:**
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

**changed_fields:**
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
- `post_is_complete` 가드로 Post가 완결된 뒤에만 변경 판단을 수행합니다
- 각 필드가 변경되었는지 체크하고, 변경된 필드 이름을 콤마로 구분하여 나열합니다
- `TRIM()`으로 마지막 콤마와 공백을 제거합니다
- 변경이 없으면 빈 문자열("")을 반환합니다

**view_question_front:**
```
[card_uid].[front]
```
- `Show_If`: `ISNOTBLANK([pre_started_ts])`
- **Purpose:** Start 버튼을 누르기 전까지 문항이 보이지 않도록 (데이터 오염 방지)

**view_question_image:**
```
[card_uid].[image_filename]
```
- `Show_If`: `ISNOTBLANK([pre_started_ts])`
- **Purpose:** Start 버튼을 누르기 전까지 이미지가 보이지 않도록 (데이터 오염 방지)

---

## 8. Automation Limitations and Workarounds

### 8.1 What Cannot Be Automated

**AppSheet Configuration (Must be done manually in UI):**
- Virtual column creation and formulas
- Slice (view filter) creation
- Action creation and Run_If/Show_If formulas
- View configuration (which columns to show)
- Column type settings (Number, Date/Time, Yes/No, etc.)
- Editable_If, Required_If settings
- Reference relationships between tables
- Security filters
- Sync settings

**Why:** AppSheet does not provide a public API for app configuration. The app structure (tables, views, actions, formulas) must be configured through the web UI.

---

### 8.2 What Can Be Automated

#### 8.2.1 Data Preparation (Fully Automated)

**✅ CSV Export Script:**
- Generate all CSV files (Cards, Groups, S5, Ratings, Assignments)
- Pre-populate Ratings.csv with rows from Assignments
- Set up correct column headers and data types
- **File:** `3_Code/src/tools/final_qa/export_appsheet_tables.py`

**✅ Google Sheets Data Import:**
- Can be automated via Google Apps Script
- Can be automated via Google Sheets API
- Can be done manually (one-time setup)

#### 8.2.2 Google Sheets Manipulation (Partially Automated)

**✅ Google Apps Script:**
- Add/remove columns in Google Sheets
- Populate data in Google Sheets
- Format columns
- **Limitation:** AppSheet column type settings still need manual configuration

**Example Apps Script:**
```javascript
function setupRatingsSheet() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Ratings');
  
  // Add columns if they don't exist
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const requiredCols = ['assignment_order', 'flag_followup', 'flag_note'];
  
  requiredCols.forEach(col => {
    if (!headers.includes(col)) {
      sheet.appendRow([col]);
    }
  });
}
```

#### 8.2.3 AppSheet App Duplication (Template Approach)

**✅ App Template/Backup:**
- Create a "template" AppSheet app with all configurations
- Duplicate the app for new runs
- Update data sources (Google Sheets) in duplicated app
- **Limitation:** Still requires manual data source reconnection

**Procedure:**
1. Configure one AppSheet app completely (all virtual columns, slices, actions)
2. `Settings` → `Backup` → Download app backup
3. For new runs: `Settings` → `Restore` → Upload backup
4. Manually reconnect to new Google Sheets (data sources)

---

### 8.3 Recommended Workflow

**For Initial Setup (One-time):**
1. ✅ **Automated:** Run exporter to generate CSVs
2. ✅ **Automated (optional):** Use Apps Script to set up Google Sheets columns
3. ❌ **Manual:** Import CSVs into Google Sheets
4. ❌ **Manual:** Configure AppSheet (virtual columns, slices, actions, views)
5. ✅ **Automated (optional):** Create AppSheet app backup for reuse

**For Subsequent Runs:**
1. ✅ **Automated:** Run exporter to generate new CSVs
2. ✅ **Automated (optional):** Use Apps Script to update Google Sheets
3. ❌ **Manual:** Import/update CSVs in Google Sheets (or use "Update existing + Add new" mode)
4. ✅ **Automated (if using template):** Restore AppSheet app from backup
5. ❌ **Manual:** Reconnect data sources to new Google Sheets

---

### 8.4 Alternative: AppSheet API (Limited)

**AppSheet Management API (Enterprise only):**
- Some configuration can be automated via API
- Requires enterprise license
- Limited scope (mostly app management, not detailed configuration)
- **Not recommended** for this use case

**Reference:** https://developers.google.com/appsheet/api

---

### 8.5 Summary

| Task | Automation Level | Method |
|------|-----------------|--------|
| CSV generation | ✅ Fully automated | Python exporter script |
| Google Sheets setup | ⚠️ Partially automated | Apps Script (columns), manual (import) |
| AppSheet configuration | ❌ Manual only | Web UI |
| AppSheet data updates | ✅ Automated | Via Google Sheets (AppSheet auto-syncs) |
| App duplication | ⚠️ Partially automated | Backup/restore (manual data source reconnect) |

**Recommendation:**
- Use exporter script for CSV generation (fully automated)
- Create AppSheet app template/backup after initial configuration
- For new runs: restore template and reconnect data sources
- Document all manual steps in checklist for reproducibility

---

**End of Production Hardening Guide**


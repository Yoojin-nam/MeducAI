# AppSheet QA Production Hardening — Implementation Checklist

**Purpose:** Track implementation of production-grade enhancements for 200+ item FINAL QA workflow.

**Reference:** See [AppSheet QA Production Hardening Guide](./AppSheet_QA_Production_Hardening.md) for detailed instructions.

---

## Phase 1: Exporter Updates

### Code Changes

- [ ] **File:** `3_Code/src/tools/final_qa/export_appsheet_tables.py`
  - [ ] Add `_read_csv_rows()` helper function
  - [ ] Add `_generate_ratings_from_assignments()` function
  - [ ] Update `export_appsheet_tables()` to call ratings generator when Assignments.csv exists
  - [ ] Add new columns to Ratings.csv fieldnames:
    - [ ] `assignment_order`
    - [ ] `flag_followup`
    - [ ] `flag_note`
    - [ ] `admin_undo_pre_submitted_ts`
    - [ ] `admin_undo_post_submitted_ts`
    - [ ] `undo_reason`
  - [ ] Add `assignment_order` to Assignments.csv fieldnames
  - [ ] Test exporter with sample Assignments.csv
  - [ ] Verify Ratings.csv contains pre-created rows

### Testing

- [ ] Run exporter with Assignments.csv present → verify Ratings.csv has rows
- [ ] Run exporter without Assignments.csv → verify Ratings.csv is template only
- [ ] Verify all new columns are in CSV output

---

## Phase 2: Google Sheets Setup

### Ratings Tab

- [ ] Add columns to Ratings tab header:
  - [ ] `assignment_order` (Number)
  - [ ] `flag_followup` (Yes/No)
  - [ ] `flag_note` (LongText)
  - [ ] `admin_undo_pre_submitted_ts` (Date/Time, optional)
  - [ ] `admin_undo_post_submitted_ts` (Date/Time, optional)
  - [ ] `undo_reason` (LongText, optional)

### Import Procedure

- [ ] Export Ratings.csv using updated exporter
- [ ] Import Ratings.csv into Google Sheets
- [ ] **CRITICAL:** Use "Update existing + Add new" mode (NOT "Replace sheet")
- [ ] Verify all columns are present
- [ ] Verify pre-created rows are present (if using Ratings-first model)

---

## Phase 3: AppSheet Virtual Columns

### Core Virtual Columns

- [ ] **`qa_state`** virtual column
  - [ ] Expression matches guide (6 states: TODO, PRE, REVEAL_READY, REVEAL, POST, DONE)
  - [ ] Test with sample data

- [ ] **`pre_is_complete`** virtual column
  - [ ] Expression uses `ISNOTBLANK()` and `NUMBER()` correctly
  - [ ] Test with various Pre field combinations

- [ ] **`post_is_complete`** virtual column
  - [ ] Expression uses `ISNOTBLANK()` and `NUMBER()` correctly
  - [ ] Test with various Post field combinations

- [ ] **`is_changed`** virtual column
  - [ ] Expression includes `post_is_complete` guard
  - [ ] Test to ensure no false positives when Post is blank

---

## Phase 4: AppSheet Slices (Queue Views)

### Queue Slices

- [ ] **`MyQueue_Todo`**
  - [ ] Filter: `AND([rater_email] = USEREMAIL(), [qa_state] = "TODO")`
  - [ ] Sort: `assignment_order` (ascending)
  - [ ] Test: Verify only TODO items for current user

- [ ] **`MyQueue_Reveal`**
  - [ ] Filter: `AND([rater_email] = USEREMAIL(), [qa_state] = "REVEAL_READY")`
  - [ ] Sort: `assignment_order` (ascending)
  - [ ] Test: Verify only REVEAL_READY items

- [ ] **`MyQueue_Post`**
  - [ ] Filter: `AND([rater_email] = USEREMAIL(), OR([qa_state] = "REVEAL", [qa_state] = "POST"))`
  - [ ] Sort: `assignment_order` (ascending)
  - [ ] Test: Verify REVEAL and POST items

- [ ] **`MyQueue_Done`**
  - [ ] Filter: `AND([rater_email] = USEREMAIL(), [qa_state] = "DONE")`
  - [ ] Sort: `assignment_order` (ascending)
  - [ ] Test: Verify only DONE items

- [ ] **`MyFlagged`**
  - [ ] Filter: `AND([rater_email] = USEREMAIL(), [flag_followup] = TRUE)`
  - [ ] Sort: `assignment_order` (ascending)
  - [ ] Test: Verify flagged items

---

## Phase 5: AppSheet Actions — Formulas

### Pre Actions

- [ ] **"Start Pre-S5 Rating"**
  - [ ] `Show_If`: `ISBLANK([pre_started_ts])`
  - [ ] `Run_If`: `ISBLANK([pre_started_ts])`
  - [ ] Updates: `pre_started_ts` = `NOW()`
  - [ ] Test: Button appears only when not started

- [ ] **"Submit Pre-S5 Rating"**
  - [ ] `Show_If`: `AND(NOT(ISBLANK([pre_started_ts])), ISBLANK([pre_submitted_ts]))`
  - [ ] `Run_If`: Includes `[pre_is_complete]` check
  - [ ] Updates: `pre_submitted_ts` = `NOW()`
  - [ ] `On success`: `pre_duration_sec` = `([pre_submitted_ts] - [pre_started_ts]) * 24 * 60 * 60`
  - [ ] Test: Cannot submit incomplete Pre evaluation

### Reveal Action

- [ ] **"Reveal S5 Results"**
  - [ ] `Show_If`: `AND(NOT(ISBLANK([pre_submitted_ts])), ISBLANK([s5_revealed_ts]))`
  - [ ] `Run_If`: Same as `Show_If`
  - [ ] Updates: `s5_revealed_ts` = `NOW()`
  - [ ] Test: Button appears only after Pre submission

### Post Actions

- [ ] **"Start Post-S5 Rating"**
  - [ ] `Show_If`: `AND(NOT(ISBLANK([s5_revealed_ts])), ISBLANK([post_started_ts]))`
  - [ ] `Run_If`: Same as `Show_If`
  - [ ] Updates: `post_started_ts` = `NOW()`
  - [ ] Test: Button appears only after S5 reveal

- [ ] **Post Field `Editable_If` Update**
  - [ ] Update all Post fields: `AND(NOT(ISBLANK([s5_revealed_ts])), ISBLANK([post_submitted_ts]), NOT(ISBLANK([post_started_ts])))`
  - [ ] Test: Post fields require `post_started_ts` to edit

- [ ] **"Submit Post-S5 Rating"**
  - [ ] `Show_If`: `AND(NOT(ISBLANK([s5_revealed_ts])), NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]))`
  - [ ] `Run_If`: Includes `[post_is_complete]` and change log requirements
  - [ ] Updates: `post_submitted_ts` = `NOW()`
  - [ ] `On success`: `post_duration_sec` = `([post_submitted_ts] - [post_started_ts]) * 24 * 60 * 60`
  - [ ] Test: Cannot submit incomplete Post evaluation

### Navigation Actions

- [ ] **"Go to Next Pending"**
  - [ ] Action type: `Navigate`
  - [ ] Row expression: Selects next item from `MyQueue_Todo`, `MyQueue_Reveal`, or `MyQueue_Post`
  - [ ] `Show_If`: Checks if any pending items exist
  - [ ] Test: Navigates to correct next item

---

## Phase 6: AppSheet Views — Performance Optimization

### List Views

- [ ] **Remove heavy columns from list views:**
  - [ ] Remove `front`, `back` (large text)
  - [ ] Remove `evidence_comment_pre`, `evidence_comment_post` (large text)
  - [ ] Remove `change_note` (large text)
  - [ ] Remove `image_filename` (images)

- [ ] **Keep only metadata in list views:**
  - [ ] `rating_id`
  - [ ] `card_id`
  - [ ] `qa_state`
  - [ ] `pre_started_ts`, `pre_submitted_ts`
  - [ ] `post_started_ts`, `post_submitted_ts`
  - [ ] `flag_followup`

### Detail Views

- [ ] **Ratings_Detail view:**
  - [ ] Show full content (front, back, comments)
  - [ ] Show images (if applicable)
  - [ ] Disable "Quick edit" for complex forms
  - [ ] Test: Full content visible, images load correctly

### Sync Settings

- [ ] **Settings → Sync:**
  - [ ] Enable "Offline mode" for mobile users
  - [ ] Set sync frequency (real-time or every 5 minutes)
  - [ ] Test: Offline edits sync when connection restored

---

## Phase 7: Flag Functionality

### Flag Columns

- [ ] **`flag_followup` column:**
  - [ ] Type: `Yes/No`
  - [ ] `Editable_If`: `[rater_email] = USEREMAIL()`
  - [ ] Test: User can flag their own items

- [ ] **`flag_note` column:**
  - [ ] Type: `LongText`
  - [ ] `Editable_If`: `AND([rater_email] = USEREMAIL(), [flag_followup] = TRUE)`
  - [ ] Test: Note editable only when flagged

### Flag Actions (Optional)

- [ ] **"Flag for Follow-up" action:**
  - [ ] Sets `flag_followup` = `TRUE`
  - [ ] `Show_If`: `AND([rater_email] = USEREMAIL(), [flag_followup] = FALSE)`
  - [ ] Test: Button appears only for unflagged items

- [ ] **"Clear Flag" action:**
  - [ ] Sets `flag_followup` = `FALSE`, `flag_note` = `""`
  - [ ] `Show_If`: `AND([rater_email] = USEREMAIL(), [flag_followup] = TRUE)`
  - [ ] Test: Button appears only for flagged items

---

## Phase 8: Admin Undo (Optional)

### Admin Undo Columns

- [ ] Add columns to Google Sheets (if not already present):
  - [ ] `admin_undo_pre_submitted_ts`
  - [ ] `admin_undo_post_submitted_ts`
  - [ ] `undo_reason`

### Admin Undo Actions

- [ ] **"Admin: Undo Pre Submission"**
  - [ ] `Show_If`: Admin-only check + `NOT(ISBLANK([pre_submitted_ts]))`
  - [ ] Updates: `pre_submitted_ts` = `BLANK()`, `admin_undo_pre_submitted_ts` = `NOW()`
  - [ ] Test: Only admins can see/use

- [ ] **"Admin: Undo Post Submission"**
  - [ ] `Show_If`: Admin-only check + `NOT(ISBLANK([post_submitted_ts]))`
  - [ ] Updates: `post_submitted_ts` = `BLANK()`, `admin_undo_post_submitted_ts` = `NOW()`
  - [ ] Test: Only admins can see/use

---

## Phase 9: Testing — Pause/Resume Scenarios

### Scenario Testing

- [ ] **Scenario 1:** Pre started but not submitted → exit → resume
  - [ ] Verify: Can continue Pre evaluation

- [ ] **Scenario 2:** Pre submitted → exit → resume → reveal
  - [ ] Verify: Can reveal S5 and proceed

- [ ] **Scenario 3:** Reveal pressed → exit mid-Post → resume
  - [ ] Verify: Can continue Post evaluation

- [ ] **Scenario 4:** Fill Post without pressing "Start Post"
  - [ ] Verify: Post fields require `post_started_ts` (if Editable_If updated)
  - [ ] Verify: Cannot submit without starting

- [ ] **Scenario 5:** Accidentally press Submit Pre/Post
  - [ ] Verify: Completeness checks prevent invalid submission

- [ ] **Scenario 6:** Network sync delays / offline edits
  - [ ] Verify: Edits sync when connection restored
  - [ ] Verify: Timestamps use server time (`NOW()`)

- [ ] **Scenario 7:** Duplicate row attempts
  - [ ] Verify: Key constraint prevents duplicates
  - [ ] Verify: Pre-created rows eliminate missing row issues (Ratings-first model)

---

## Phase 10: Performance Testing

### Scale Testing

- [ ] **Load test with 200+ Ratings rows:**
  - [ ] Verify: List views load quickly (< 3 seconds)
  - [ ] Verify: Navigation actions respond quickly
  - [ ] Verify: No timeout errors

- [ ] **Test queue views:**
  - [ ] Verify: `MyQueue_Todo` filters correctly
  - [ ] Verify: `MyQueue_Reveal` filters correctly
  - [ ] Verify: `MyQueue_Post` filters correctly
  - [ ] Verify: Sorting by `assignment_order` works

- [ ] **Test virtual columns:**
  - [ ] Verify: `qa_state` calculates correctly
  - [ ] Verify: `pre_is_complete` calculates correctly
  - [ ] Verify: `post_is_complete` calculates correctly
  - [ ] Verify: `is_changed` calculates correctly (no false positives)

---

## Phase 11: Documentation

### Guide Updates

- [ ] Link to Production Hardening Guide from main guide
- [ ] Update main guide with reference to production features
- [ ] Document operational procedures (import mode, etc.)

### User Training

- [ ] Create user guide for raters (queue navigation, flagging)
- [ ] Create admin guide (undo procedures, if implemented)
- [ ] Document known limitations and workarounds

---

## Phase 12: Deployment

### Pre-Deployment

- [ ] Backup existing AppSheet app
- [ ] Backup Google Sheets data
- [ ] Test in staging environment (if available)

### Deployment

- [ ] Deploy exporter changes
- [ ] Re-export all CSVs with new schema
- [ ] Import into Google Sheets (using correct import mode)
- [ ] Configure AppSheet (virtual columns, slices, actions, views)
- [ ] Test with small subset of raters

### Post-Deployment

- [ ] Monitor for errors
- [ ] Collect user feedback
- [ ] Document issues and resolutions
- [ ] Update guide with lessons learned

---

## Notes

- **Critical:** Never use "Replace sheet" import mode for Ratings after AppSheet adds columns
- **Performance:** Keep list views lean; show full content only in detail views
- **Data Integrity:** Use admin-only undo; no rater-facing reset buttons
- **Testing:** Test all pause/resume scenarios before production deployment

---

**Last updated:** 2025-01-01


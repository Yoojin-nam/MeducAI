---

# Firebase QA/Survey Site Implementation Notes

**Time Logging + Evaluation Data Collection (S0/S1)**

**Document status:** Canonical (Implementation guide)
**Applies to:** MeducAI Phase 1 (S0/S1) evaluator site
**Owner:** MeducAI Study Team
**Last updated:** 2025-03

---

## 1. Scope

This document specifies:

1. What input/evaluation data must be collected for S0/S1
2. How to implement event-based time measurement (active vs idle)
3. Firestore collection design (recommended)
4. Minimal client-side logic and server-side aggregation strategy
5. UX patterns that reduce measurement noise without harming usability

---

## 2. Data Units and Screens

### 2.1 S0 (Expert QA)

* **Unit:** `set` = group × arm artifact bundle
* **Typical screen:**

  * left: artifact content (table/infographic/cards)
  * right: rubric + critical flags + optional edit box
  * bottom: submit

### 2.2 S1 (Acceptance sampling)

* **Unit:** `card` (or “micro-item”)
* **Typical screen:**

  * card content
  * 2–5 quick rubric items (binary accept + major/minor + safety)
  * next card auto-load

---

## 3. Firestore Collections (Recommended)

### 3.1 Overview

```
/runs/{run_tag}
/assignments/{assignment_id}
/sessions/{session_id}
/events/{event_id}         (optional, if not embedding in sessions)
/aggregates/{agg_id}       (optional, daily / per-run summaries)
```

> Recommendation: **Store events embedded inside `sessions`** for simplicity.
> Use a separate `events` collection only if events become large/high-frequency.

---

## 4. Core Documents and Fields

## 4.1 `runs/{run_tag}`

Used for configuration and auditability.

**Fields**

* `run_tag`: string
* `phase`: "S0" | "S1"
* `created_at`: serverTimestamp
* `frozen`: bool (set true when data collection ends)
* `idle_threshold_sec`: number (fixed = 30)
* `ui_version`: string
* `rubric_version`: string
* `arm_blinding_enabled`: bool

---

## 4.2 `assignments/{assignment_id}`

Defines “who reviews what” (supports paired and randomized assignment).

**Fields**

* `run_tag`
* `phase`
* `reviewer_id`
* `reviewer_role`: "resident" | "attending"
* `items`: array of objects (S0: set objects, S1: card objects)

  * each item object contains:

    * `set_id` (S0) or `card_id` (S1)
    * `arm_blinded_code` (e.g., "X3", "Q7") — **do not store raw arm on client UI**
    * `order_index` (randomized order)
    * `status`: "todo" | "in_progress" | "done"
* `created_at`: serverTimestamp

---

## 4.3 `sessions/{session_id}` (The main log unit)

One session = one item evaluation instance.

### Required metadata (S0/S1 공용)

* `run_tag`: string
* `phase`: "S0" | "S1"
* `set_id` (S0) OR `card_id` (S1)
* `item_id`: string (alias of set_id/card_id)
* `arm_blinded_code`: string
* `arm` (optional, server-only): string

  * **권장:** 클라이언트에서는 숨기고, 서버에서 매핑(혹은 collection join)
* `reviewer_id`: string (pseudonymized)
* `reviewer_role`: "resident" | "attending"
* `device_type`: "web" | "tablet" | "mobile"
* `ui_version`: string
* `timestamp_start_ms`: int
* `timestamp_end_ms`: int (set on submit)
* `total_duration_sec`: number (computed)
* `active_duration_sec`: number **(primary)**
* `idle_duration_sec`: number
* `idle_segment_count`: int

### Event log (embedded)

* `events`: array of objects (append-only)

  * `type`: "view" | "scroll" | "click" | "edit" | "idle_enter" | "idle_exit" | "save" | "submit"
  * `ts_ms`: int
  * `meta`: object (optional)

### Edit metrics

* `edit_event`: bool
* `edit_char_count`: int
* `edit_block_count`: int

### Evaluation payload (S0/S1 diverges)

* `evaluation`: object

  * See section 5.

---

## 5. Evaluation Input Fields (UI forms)

## 5.1 S0 Rubric (recommended minimal)

**Binary**

* `blocking_error_flag`: bool
* `overall_accept_without_edit`: bool

**Likert (e.g., 1–5 or 1–7)**

* `completeness_score`
* `clarity_score`
* `clinical_alignment_score`
* `actionability_score`
* `safety_appropriateness_score`

**Optional**

* `free_text_comment`: string (limit length)
* `edit_summary`: string (if edits were made)

> Tip: “수정 자체(edit)”는 **리포트/카드 본문을 고치는 기능**이 아니라,
> “수정이 필요하다고 판단한 부분을 요약”하는 형태로도 충분합니다.
> (진짜 editing UI는 비용이 큼)

---

## 5.2 S1 Rubric (fast, micro-task)

**Binary**

* `binary_accept`: bool
* `major_revision_flag`: bool
* `minor_revision_flag`: bool
* `adjudication_needed`: bool (optional)
* `safety_flag`: bool (optional)

**Optional**

* `short_comment`: string

> S1은 속도가 중요하므로 Likert를 최소화하고 binary 중심 권장.

---

## 6. Time Measurement Implementation (Client-Side)

## 6.1 Key idea

* **No manual time entry**
* “view → submit” 사이에서 **Active/Idle**을 상태 머신으로 계산
* Primary = `active_duration_sec`

## 6.2 Minimal interaction events to listen

* `scroll`
* `keydown` / `input`
* `click`
* `mousemove` (선택: 과도하면 노이즈; 권장하지 않음)
* `focus` / `blur` (탭 전환 감지)

**권장 최소 세트:** scroll + keydown/input + click + focus/blur

---

## 6.3 State machine variables (per session)

* `idle_threshold_ms = 30000`
* `state = ACTIVE | IDLE`
* `last_event_ts_ms`
* `active_accum_ms`
* `idle_accum_ms`
* `state_enter_ts_ms`

---

## 6.4 Pseudocode (drop-in logic)

```text
onSessionStart():
  ts0 = now()
  state = ACTIVE
  state_enter = ts0
  last_event = ts0
  logEvent("view", ts0)

onUserInteraction(eventType):
  ts = now()

  // if currently idle, exit idle first
  if state == IDLE:
     idle_accum += (ts - state_enter)
     logEvent("idle_exit", ts)
     state = ACTIVE
     state_enter = ts

  // update last event
  last_event = ts
  logEvent(eventType, ts)

timerTick(every 1s):
  ts = now()
  if state == ACTIVE and (ts - last_event) >= idle_threshold:
      active_accum += (last_event - state_enter)   // active until last action
      logEvent("idle_enter", ts)
      state = IDLE
      state_enter = ts

onSubmit():
  ts = now()

  if state == ACTIVE:
      active_accum += (ts - state_enter)
  else:
      idle_accum += (ts - state_enter)

  logEvent("submit", ts)

  writeSessionDoc({
     timestamp_start_ms: ts0,
     timestamp_end_ms: ts,
     total_duration_sec: (ts - ts0)/1000,
     active_duration_sec: active_accum/1000,
     idle_duration_sec: idle_accum/1000,
     idle_segment_count: countIdleSegments(events),
     ...
  })
```

**주의**

* ACTIVE 구간을 “마지막 interaction까지”로 끊는 방식이 가장 보수적입니다.
* idle_enter 시점은 `ts`로 남기되, active 누적은 `last_event`까지 반영.

---

## 7. UX/Flow to Reduce Noise (without hard blocking)

### 7.1 Soft idle banner (non-blocking)

* idle_enter 발생 시:

  * 배너: “비활성 상태로 기록이 일시 중지되었습니다. 다시 조작하면 재개됩니다.”
* 사용자는 그대로 쉬었다가 돌아와도 됨.

### 7.2 Explicit Resume (선택)

* idle 상태에서 첫 interaction을 resume로 취급하거나,
* “Resume” 버튼을 한 번 눌러야 active 재개되도록 설계 가능

  * 데이터 정합성은 좋아지지만 UX 부담 증가
  * **S0(긴 작업)**에만 적용 추천

### 7.3 Micro-task segmentation

* S0: set 단위 유지, 화면 분리 최소화
* S1: 카드 단위로 “Next” 중심 설계
  → idle이 들어가도 영향이 작아짐.

### 7.4 Guardrails

* “Submit”은 언제나 가능하게 유지(강제 종료 금지)
* “Draft save”는 옵션 (장시간 작업 대비)

---

## 8. Firebase Security & Privacy Notes

* `reviewer_id`는 이메일/실명 대신 **pseudonymized ID** 사용
* arm 정보는 UI에 노출하지 않으며, 가능하면 server-side에서 매핑
* Firestore Rules:

  * reviewer는 자신의 assignment/session만 read/write
  * aggregate는 admin only

---

## 9. Aggregation Strategy (Server-side recommended)

### 9.1 Why aggregate?

* 논문용 지표는 개별 세션이 아니라:

  * run_tag × arm × role 별 분포
  * P95 active time
  * zero-edit approval rate
* 클라이언트에서 계산하면 데이터 불일치 위험 ↑

### 9.2 Recommended approach

* Cloud Functions (onWrite sessions/{session_id})

  * incremental aggregate update
  * 또는 BigQuery export 후 배치 분석

**Aggregate fields examples**

* `count_sessions`
* `sum_active_sec`
* `p95_active_sec` (배치에서 계산 권장)
* `zero_edit_rate`
* `blocking_error_rate`

---

## 10. Minimal Testing Checklist (Today’s build)

1. Idle threshold가 정확히 30s에서 작동하는지
2. idle_enter/exit가 이벤트로 남는지
3. “수정 없음 + submit”도 세션이 저장되는지
4. 탭 이동(blur/focus) 시 idle로 처리되는지
5. 랜덤 배정 순서가 유지되는지
6. arm 정보가 UI에서 노출되지 않는지
7. sessions 문서에 active/idle/total이 모두 기록되는지

---

## 11. Output Guarantees (What the dataset will support)

If implemented as above, the collected dataset can support:

* Human effort (active time) distribution and tail behavior
* Zero-edit approvals as a system stability signal
* Role-based calibration (resident vs attending time and disagreement)
* Arm-level cost–quality–human-effort trade-off curves

---

## Appendix A. Example `sessions/{session_id}` Document

```json
{
  "run_tag": "S0_QA_202503",
  "phase": "S0",
  "set_id": "grp_023__armX3",
  "item_id": "grp_023__armX3",
  "arm_blinded_code": "X3",
  "reviewer_id": "rev_9c21",
  "reviewer_role": "resident",
  "device_type": "web",
  "ui_version": "qa-ui-0.8.1",
  "timestamp_start_ms": 1740900000123,
  "timestamp_end_ms": 1740900123456,
  "total_duration_sec": 123.3,
  "active_duration_sec": 78.4,
  "idle_duration_sec": 44.9,
  "edit_event": false,
  "edit_char_count": 0,
  "idle_segment_count": 2,
  "events": [
    {"type":"view","ts_ms":1740900000123},
    {"type":"scroll","ts_ms":1740900005000},
    {"type":"idle_enter","ts_ms":1740900040000},
    {"type":"idle_exit","ts_ms":1740900060000},
    {"type":"submit","ts_ms":1740900123456}
  ],
  "evaluation": {
    "blocking_error_flag": false,
    "overall_accept_without_edit": true,
    "completeness_score": 5,
    "clarity_score": 5,
    "clinical_alignment_score": 5,
    "actionability_score": 4,
    "safety_appropriateness_score": 5,
    "free_text_comment": ""
  }
}
```

---
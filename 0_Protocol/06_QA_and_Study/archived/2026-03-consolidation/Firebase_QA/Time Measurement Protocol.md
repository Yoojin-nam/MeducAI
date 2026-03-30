\---

# Time Measurement Protocol

**(Human-in-the-loop Interaction Time Logging)**

**Document status:** Canonical
**Applies to:** MeducAI Phase 1 (S0, S1) and subsequent system evaluations
**Last updated:** 2025-03
**Owner:** MeducAI Study Team

---

## 1. Purpose

This document defines the protocol for measuring **human interaction time** during MeducAI evaluation workflows (S0 and S1).
The goal is to obtain a **robust, reproducible, and interpretable estimate of human effort**, accounting for real-world interruptions and multitasking.

This protocol explicitly distinguishes between:

* **Active interaction time** (primary outcome)
* **Idle time** (secondary, descriptive)

---

## 2. Design Principles

1. **No manual time entry**

   * All time measurements are collected automatically via system events.
2. **Event-based logging**

   * Human effort is inferred from interaction events, not wall-clock duration alone.
3. **Active time as primary metric**

   * Idle periods are excluded from primary analyses.
4. **Non-intrusive UX**

   * The system does not restrict breaks or multitasking.
5. **Auditability**

   * Raw event logs are preserved for post-hoc verification.

---

## 3. Definitions

### 3.1 Session

A **session** is defined as a single continuous evaluation of one item.

* **S0:** one *set* (group × arm)
* **S1:** one *card*

Each session has a unique `session_id`.

---

### 3.2 Active Interaction Time (Primary Metric)

**Active interaction time** is defined as the cumulative duration during which the reviewer is actively interacting with the interface.

A session is considered **active** if **any** of the following events occur:

* Keyboard input
* Mouse click
* Scroll event
* Text edit
* Focused interaction with the evaluation UI

---

### 3.3 Idle Time

An **idle period** is defined as a continuous interval during which **no interaction events** occur for a predefined threshold.

* **Idle threshold:** 30 seconds (fixed)
* If no interaction is detected for ≥30 seconds, the session enters *idle state*.
* Idle periods are logged but excluded from primary analyses.

---

## 4. State Model

Each session follows a two-state model:

```
ACTIVE  ──(no interaction ≥30s)──▶  IDLE
IDLE    ──(any interaction)──────▶  ACTIVE
```

* Transitions are logged with timestamps.
* Multiple idle–active cycles may occur within a single session.

---

## 5. Logged Events

### 5.1 Core Interaction Events

| Event type | Description           |
| ---------- | --------------------- |
| view       | Initial content load  |
| scroll     | Content scrolling     |
| edit       | Text modification     |
| click      | UI interaction        |
| submit     | Evaluation submission |
| save       | Explicit save action  |

---

### 5.2 Session Metadata (Automatically Recorded)

| Field            | Description               |
| ---------------- | ------------------------- |
| run_tag          | Experiment identifier     |
| phase            | S0 or S1                  |
| set_id / card_id | Evaluation unit           |
| arm              | System configuration      |
| reviewer_id      | Pseudonymized reviewer ID |
| reviewer_role    | Resident / Attending      |
| timestamp_start  | Session start             |
| timestamp_end    | Session end               |

---

## 6. Time Metrics Stored Per Session

For each session, the following metrics are stored:

* `total_duration_sec`
  (timestamp_end − timestamp_start)
* `active_duration_sec` **(primary)**
* `idle_duration_sec`
* `idle_segment_count`
* `idle_segments[]` (optional, start/end timestamps)

Only **active_duration_sec** is used for primary statistical analyses.

---

## 7. UX Safeguards Against Measurement Noise

### 7.1 Passive Idle Detection

* No hard time limits are enforced.
* When idle is detected, time accumulation pauses automatically.

### 7.2 Non-blocking Resume

* Upon interaction after idle, the session resumes without penalty.
* Optional UI message:
  *“Session paused due to inactivity. Time recording resumed.”*

---

## 8. Data Usage in Analysis

### 8.1 Primary Analysis

* Uses **active interaction time only**
* Reported as:

  * mean, median
  * variance
  * 95th percentile (worst-case workload)

---

### 8.2 Secondary / Sensitivity Analyses

* Comparison between:

  * active time
  * total time
* Used to assess robustness against interruption patterns.

---

## 9. Reporting Statement (For Manuscripts)

The following statement is used verbatim in manuscripts:

> “Human effort was measured using active interaction time, excluding idle periods due to interruptions or multitasking. Idle time was defined as ≥30 seconds without interaction events and was excluded from primary analyses.”

---

## 10. Ethical and Practical Considerations

* No behavioral constraints are imposed on reviewers.
* Breaks and multitasking are permitted and expected.
* Time measurement serves analytical purposes only and is not used for individual performance evaluation.

---

## 11. Scope and Reuse

This protocol applies to:

* MeducAI Phase 1 (S0, S1)
* Future multi-agent system comparisons
* Retrospective and prospective evaluations

The same definitions must be used across phases to ensure comparability.

---

## 12. Change Log

| Version | Date    | Description               |
| ------- | ------- | ------------------------- |
| v1.0    | 2025-03 | Initial canonical version |

---

### ✅ 요약 한 줄

> **Human time은 통제하지 않고, 계측한다.
> Primary metric은 active interaction time이다.**

---

## Appendix C. Decomposition of Editing Time

In addition to total active interaction time, editing activity may be optionally categorized by primary cause to support future system-level comparisons.

### C.1 Editing Cause Categories (Optional)

- Factual correction
- Wording or clarity improvement
- Structural reorganization
- Difficulty calibration
- No edit required

These categories are collected at the session level as categorical metadata and are not used in primary analyses. Their purpose is to support downstream analyses of workload composition.

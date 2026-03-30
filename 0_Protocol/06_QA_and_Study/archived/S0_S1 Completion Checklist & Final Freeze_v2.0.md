# MeducAI – S0/S1 Completion Checklist & Final Freeze (Table-based, v2.0 aligned)

**Date:** 2025-12-19 (Updated)
**Status:** Archived (v2.0 aligned)
**Superseded by:** `0_Protocol/06_QA_and_Study/S0_S1_Completion_Checklist_and_Final_Freeze.md`
**Do not use this file for new decisions or execution.**
**Scope:** Pipeline-1 QA Only — Step S0 (Deployment Freeze) + Step S1 (Full-scale Release Gate)

본 문서는 기존 S0 중심 체크리스트가 **v1.6 정합**임을 명시하고("QA Framework v1.6…정합") S0에만 종속되어 있던 구조를, **v2.0(=S0+S1) 2단계 QA**에 맞게 재정의한 최종 체크리스트이다.

* **S0 PASS → Deployment Model Freeze (조건부 고정)**
* **S1 PASS → Release 승인 + Final Freeze (최종 고정)**

**⚠️ S1 Schema/Structure Complete Freeze (2025-12-19):**

As of 2025-12-19, the S1 output schema (`stage1_struct.jsonl`) and structure are **completely frozen**. The schema version 1.3 is final, and no further structural changes are permitted. The pipeline is ready to proceed to downstream stages (S2, S3, S4).

**Note:** While the schema is frozen, **S1 prompt improvements are allowed and planned** for future iterations. Prompt changes must not alter the output schema structure.

---

## 0. Canonical Preconditions (Already Frozen)

| 구분  | 항목                                     | Evidence              | 상태     |
| --- | -------------------------------------- | --------------------- | ------ |
| 구조  | Group-first ( group_id)     | schema doc / EDA      | Closed |
| 데이터 | CSV single source of truth             | anki_cards/*.csv      | Closed |
| 규정  | MI-CLEAR-LLM (prompt/hash/log)         | prompts+hash+manifest | Closed |
| 목적  | Vendor compare ❌ / Deployment freeze ⭕ | QA Framework v2.0     | Fixed  |

---

## 0-B. Execution Environment Requirements (Freeze prerequisite)

| Check ID | Item                                    | Evidence / Output              | Status |
| -------- | --------------------------------------- | ------------------------------ | ------ |
| ENV-01   | Python interpreter fixed (project venv) | `which python3`                | ☐      |
| ENV-02   | deps snapshot recorded                  | `pip freeze > pip-freeze.txt`  | ☐      |
| ENV-03   | markdown table deps installed           | `pip show tabulate`            | ☐      |
| ENV-04   | requirements lock committed             | `requirements.txt` or lockfile | ☐      |

---

## 1. Step S0 — Paper-1 Expert QA (Deployment Freeze)

### 1-A. S0 Sampling Freeze (18 groups option)

| Check ID   | Item                                                             | Evidence / Output      | Status |
| ---------- | ---------------------------------------------------------------- | ---------------------- | ------ |
| S0-SAMP-01 | S0 group list fixed (n=18)                                       | `group_list_S0_v2.csv` | ☐      |
| S0-SAMP-02 | Selection rule applied (Stage 1: 11 groups, Stage 2: 7 groups)   | selection report md    | ☐      |
| S0-SAMP-03 | All 11 specialties included (minimum 1 group each)              | selection report md    | ☐      |
| S0-SAMP-04 | Random seed recorded                                             | selection report       | ☐      |

### 1-B. S0 Set Generation (18 groups × 6 arms)

| Check ID  | Item                             | Evidence / Output         | Status |
| --------- | -------------------------------- | ------------------------- | ------ |
| S0-SET-01 | 6 arms generated per group       | artifacts/                | ☐      |
| S0-SET-02 | Total sets = 108                 | count log                 | ☐      |
| S0-SET-03 | Per-set payload fixed (12 cards) | payload spec md           | ☐      |
| S0-SET-04 | Card-type mix fixed              | payload spec + deck_stats | ☐      |
| S0-SET-05 | 실패/재시도 로그 누락 없음                  | manifest_generation.jsonl | ☐      |

### 1-C. S0 Model / System Configuration Freeze

| Check ID  | Field   | Value (Fixed)                    | Verified |
| --------- | ------- | -------------------------------- | -------- |
| S0-CFG-01 | RUN_TAG | `S0_QA_YYYY-MM-DD`               | ☐        |
| S0-CFG-02 | Arm A   | Flash / Think OFF / RAG OFF      | ☐        |
| S0-CFG-03 | Arm B   | Flash / Think OFF / RAG ON       | ☐        |
| S0-CFG-04 | Arm C   | Flash / Think ON / RAG OFF       | ☐        |
| S0-CFG-05 | Arm D   | Flash / Think ON / RAG ON        | ☐        |
| S0-CFG-06 | Arm E   | Pro v3 / Think ON / RAG OFF      | ☐        |
| S0-CFG-07 | Arm F   | GPT-5.2-pro / Think ON / RAG OFF | ☐        |

### 1-D. Prompt & Reproducibility Snapshot

| Check ID  | Artifact                                       | Evidence / Output    | Status |
| --------- | ---------------------------------------------- | -------------------- | ------ |
| S0-REP-01 | Prompt files archived                          | prompts/             | ☐      |
| S0-REP-02 | Prompt hash recorded                           | manifest             | ☐      |
| S0-REP-03 | Config snapshot stored                         | `.env.snapshot`      | ☐      |
| S0-REP-04 | Git commit recorded (optional but recommended) | `git rev-parse HEAD` | ☐      |

### 1-E. Cost/Latency/Token/RAG Logging (S0)

| Check ID  | Metric                      | Unit      | Evidence                  | Status |
| --------- | --------------------------- | --------- | ------------------------- | ------ |
| S0-SYS-01 | start_ts / end_ts logged    | timestamp | manifest_generation.jsonl | ☐      |
| S0-SYS-02 | latency_sec computed        | sec       | derived                   | ☐      |
| S0-SYS-03 | input_tokens logged         | tokens    | provider log              | ☐      |
| S0-SYS-04 | output_tokens logged        | tokens    | provider log              | ☐      |
| S0-SYS-05 | rag_queries_count (B/D)     | count     | provider log              | ☐      |
| S0-SYS-06 | rag_sources_count (B/D)     | count     | provider log              | ☐      |
| S0-SYS-07 | cost_estimated_usd computed | USD       | summary table             | ☐      |

### 1-F. Panel Assignment & Evaluation (Paired Cross-evaluation)

| Check ID    | Item                                               | Evidence / Output | Status |
| ----------- | -------------------------------------------------- | ----------------- | ------ |
| S0-PANEL-01 | Pairing enforced: 1 Resident + 1 Attending per set | assignment sheet  | ☐      |
| S0-PANEL-02 | Set-level evaluation completed (10 min/set target) | timer sheet       | ☐      |
| S0-PANEL-03 | Safety labels captured (blocking)                  | score sheet       | ☐      |
| S0-PANEL-04 | Overall card quality captured (Likert 1–5)        | score sheet       | ☐      |
| S0-PANEL-05 | Editing time captured (minutes, self-reported)    | score sheet       | ☐      |
| S0-PANEL-06 | Likert clarity captured (optional)                 | score sheet       | ☐      |

### 1-G. S0 Analysis Artifacts (Paper-1 ready)

| Check ID  | Item                                                    | Evidence / Output          | Status |
| --------- | ------------------------------------------------------- | -------------------------- | ------ |
| S0-ANA-01 | Arm summary table generated                             | `S0_arm_summary.csv/md`    | ☐      |
| S0-ANA-02 | Non-inferiority test executed (Two-layer: Safety + NI, Δ=0.05, Baseline: Arm A default) | `qa_s0_noninferiority_decision.md` | ☐      |
| S0-ANA-03 | Secondary outcomes (EDI/Disagreement/Role×Arm) computed | `S0_secondary_outcomes.md` | ☐      |

### 1-H. S0 Deployment Decision & Conditional Freeze

| Step    | Rule                                  | Result            | Passed |
| ------- | ------------------------------------- | ----------------- | ------ |
| S0-D-01 | Safety hard gate                      | eligible arms     | ☐      |
| S0-D-02 | Two-layer gate: Safety (RD0 ≤ 0.02) + NI (LowerCI(d) > -Δ, Δ=0.05) | non-inferior arms | ☐      |
| S0-D-03 | Cost & Editing Time minimization      | winner arm        | ☐      |
| S0-D-04 | Tie-break: latency → stability        | final arm         | ☐      |

**Selected Deployment Model (S0 Freeze):** `Arm ____`

**S0 Freeze declaration (Conditional):**

> “MeducAI Step S0 has been completed and the deployment configuration is frozen for full-scale generation, pending S1 release gate.”

* Date: ___________
* Signed by (PI): ___________

---

## 2. Step S1 — Full-scale Generation Quality Gate (One-shot Release Gate)

### 2-A. Full-scale Generation Completion

| Check ID  | Item                                            | Evidence / Output | Status |
| --------- | ----------------------------------------------- | ----------------- | ------ |
| S1-GEN-01 | Full card population generated (N=6,000–12,000) | deck export count | ☐      |
| S1-GEN-02 | Coverage across all EDA groups confirmed        | coverage report   | ☐      |
| S1-GEN-03 | Manifest/log completeness (no missing ids)      | manifest audit    | ☐      |

### 2-B. One-shot Acceptance Sampling (Fixed)

| Check ID   | Item                                         | Evidence / Output    | Status |
| ---------- | -------------------------------------------- | -------------------- | ------ |
| S1-SAMP-01 | Sampling frame fixed (all cards)             | `sampling_frame.csv` | ☐      |
| S1-SAMP-02 | PPS + strata constraints enforced            | sampling report      | ☐      |
| S1-SAMP-03 | Sample size fixed: n=838                     | sample file          | ☐      |
| S1-SAMP-04 | One-shot sample generated (no interim looks) | random seed + log    | ☐      |

### 2-C. Reviewer Workflow (2× Resident + Attending authority)

| Check ID  | Item                                              | Evidence / Output | Status |
| --------- | ------------------------------------------------- | ----------------- | ------ |
| S1-REV-01 | Residents 2-person independent review for all 838 | score sheet       | ☐      |
| S1-REV-02 | IRR anchor subsample m=300 selected               | anchor list       | ☐      |
| S1-REV-03 | Anchor: Resident2 + Attending1 completed          | score sheet       | ☐      |
| S1-REV-04 | Adjudication triggers enforced                    | adjudication log  | ☐      |

### 2-D. IRR Reporting

| Check ID  | Metric                      | Evidence / Output | Status |
| --------- | --------------------------- | ----------------- | ------ |
| S1-IRR-01 | Accuracy: Fleiss’ κ (m=300) | IRR report        | ☐      |
| S1-IRR-02 | Likert: weighted κ (m=300)  | IRR report        | ☐      |
| S1-IRR-03 | Override/adjudication rate  | adjudication log  | ☐      |

### 2-E. Acceptance Rule Decision (Fixed)

| Check ID  | Rule                | Result               | Passed |
| --------- | ------------------- | -------------------- | ------ |
| S1-DEC-01 | n=838, c=2          | blocking count = ___ | ☐      |
| S1-DEC-02 | PASS if blocking ≤2 | PASS/FAIL            | ☐      |

**S1 PASS statement:**

> “Observed blocking errors were ≤2 in n=838 sampled cards; therefore the one-sided 99% Clopper–Pearson upper bound supports a population blocking error rate <1%, and release is approved.”

---

## 3. Final Freeze Declaration (Release Approved)

S1까지 모든 항목이 체크된 시점에 최종 선언한다.

> “MeducAI Pipeline-1 QA (S0+S1) has been completed. The deployment configuration is finally frozen and the release is approved.”

* Date: ___________
* Signed by (PI): ___________

---

## 4. Canonical Storage Location (Recommended)

```
0_Protocol/04_QA_Framework/
├─ QA_Framework_v2.0.md
├─ S0_S1_Completion_Checklist_and_Final_Freeze_v2.0.md   ← 본 문서
└─ (optional) templates/
   ├─ S0_score_sheet_template.csv
   ├─ S1_score_sheet_template.csv
   └─ adjudication_log_template.csv
```

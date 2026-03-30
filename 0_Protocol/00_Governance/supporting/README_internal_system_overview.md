“This document is explanatory. Governance authority resides in meduc_ai_pipeline_canonical_governance_index.md.”

# Internal System Overview (Not an Entry Document)

This document describes the internal architecture and operational status of MeducAI.
External readers should start from the top-level README.md.

# MeducAI v5.2 (Canonical Research System)

**Group-first · Reproducible · QA-driven Generative AI Framework**
**for Radiology Board Examination Education**
*(IRB-ready · Deployment-oriented · MI-CLEAR-LLM v2.0 compliant)*

---

## 0. Executive Summary

**MeducAI** is a research-grade, end-to-end generative AI framework designed to support **radiology board examination preparation**.
Unlike ad-hoc LLM wrappers, MeducAI operates under a strict **Two-Stage QA Governance (S0/S1)** to ensure clinical safety and educational efficacy before release.

**Current Status: v5.2 (Operational)**
* **Step S0 (Model Selection):** 6-Arm Non-inferiority Study (Ready)
* **Step S1 (Release Gate):** One-shot Acceptance Sampling (Ready)
* **Architecture:** Group-first, JSONL-Contract based

---

## 1. Canonical Protocols (The "Law")

All operations must strictly adhere to the following frozen protocols located in `0_Protocol/`.

| Component | Protocol Document | Status | Scope |
| :--- | :--- | :--- | :--- |
| **QA Governance** | [`QA_Framework.md`](0_Protocol/06_QA_and_Study/QA_Framework.md) | **Frozen** | S0 & S1 Logic |
| **Model Config** | [`S0_S1_Configuration_Log.md`](0_Protocol/06_QA_and_Study/S0_S1_Configuration_Log.md) | **Frozen** | Models/Params |
| **Blinding** | [`QA_Blinding_Procedure.md`](0_Protocol/06_QA_and_Study/QA_Operations/QA_Blinding_Procedure.md) | **Frozen** | Rater Bias Control |
| **Pipeline** | [`Pipeline_Execution_Plan.md`](0_Protocol/05_Pipeline_and_Execution/Pipeline_Execution_Plan.md) | **Frozen** | JSONL/Code Contract |
| **Checklist** | [`S0_S1_Completion_Checklist_and_Final_Freeze.md`](0_Protocol/06_QA_and_Study/S0_S1_Completion_Checklist_and_Final_Freeze.md) | **Active** | Go/No-Go Criteria |

---

## 2. Research Architecture (Pipeline-1)

MeducAI Pipeline-1 serves solely to **select, freeze, and validate** the deployment model.

### 2.1 Step S0: Model Selection (Expert QA)
* **Objective:** Select a single deployment model among 6 arms (A–F).
* **Design:** 6-arm factorial, paired cross-evaluation (Resident + Attending).
* **Primary Endpoints:**
    1.  **Safety:** Card-level blocking error rate (Hard Gate > 1% fail).
    2.  **Efficiency:** Editing time (Non-inferiority optimization).

### 2.2 Step S1: Full-scale Release Gate
* **Objective:** Statistical validation of the entire generated corpus (≈6,000+ cards).
* **Design:** One-shot acceptance sampling ($n=838$).
* **Decision:** PASS if blocking errors $\le 2$ (guarantees $<1\%$ error rate with 99% confidence).

---

## 3. System Architecture & Invariants

### 3.1 Group-First Invariant
* **Unit of Processing:** `Group` (derived from EDA of ~1,800 objectives).
* **Traceability:** One Group $\rightarrow$ One JSONL Record $\rightarrow$ One Image Folder.

### 3.2 MI-CLEAR-LLM Compliance
* **Transparency:** All prompts are hashed and logged.
* **Reproducibility:** Execution requires `RUN_TAG` and fixed `.env`.
* **Logging:** See `2_Data/metadata/generated/` for run manifests.

### 3.3 Folder Structure (IRB / Data Governance)

```text
MeducAI/
├── 0_Protocol/                  # [READ-ONLY] Canonical Protocols & Governance
├── 1_Secure_Participant_Info/   # [RESTRICTED] PII, Consent Forms (IRB)
├── 2_Data/
│   ├── metadata/generated/      # JSONL Contracts, Run Manifests
│   ├── images/generated/        # Visual Artifacts (Arm-separated)
│   └── eda/                     # Curriculum Analysis
├── 3_Code/                      # Source Code & Pipelines
├── 6_Distributions/             # QA Packages (Blinded/Unblinded)
├── 7_QC_Validation/             # QA Results & Score Sheets
└── 8_Governance/                # Audit Trails & Policy Docs
````

-----

## 4\. Operational Guide

**DO NOT** run scripts blindly. Follow the specific runbooks.

  * **For QA Runs (S0/S1):**
    👉 Refer to `0_Protocol/05_Pipeline_and_Execution/README_run.md` for terminal commands.

  * **For Development:**
    Refer to `Pipeline_Execution_Plan.md` for the JSONL Schema Contract.

-----

## 5\. Current Version Status

> **MeducAI v5.2** is declared as the **Operational Research System** for the 2025 Study.
> All Step S0 configurations are frozen as per `S0_S1_Configuration_Log.md`.

**Lead Research Engineer:** `MeducAI`
**Principal Investigator:** `User (MD)`



---

groups_canonical.csv is the single source of truth for all group-level operations
and must not be regenerated after S0 freeze.

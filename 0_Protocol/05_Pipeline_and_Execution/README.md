# Pipeline & Execution — QA and Evaluation

Status: Canonical (Execution-Level Index)
Version: 1.0
Applies to: QA Phase (S0, S1) and Exploratory User Evaluation
Last Updated: 2025-12-20

---

## 1. Purpose of This Directory

This directory contains **execution-level documents** governing how MeducAI is *run, evaluated, quality-controlled, and reported*.

Unlike documents in `00_Governance/`, which define global principles and authoritative definitions, files in this directory specify:

- How QA is operationally performed
- How evaluation metrics are applied
- How results are standardized and reported
- How methodological risks (bias, variability, irreproducibility) are controlled at runtime

All documents here are **protocol-bound** and directly support IRB review, reproducibility audits, and peer-reviewed publication.

---

## 2. Scope and Applicability

Documents in this directory apply primarily to:

- **Step S0**: QA / model comparison under fixed payload conditions
- **Step S1**: Early validation and limited QA reuse
- **Exploratory user evaluation** derived from QA-approved content

They do *not* define curriculum structure, card-count authority, or model selection logic, which are governed elsewhere.

---

## 3. Document Index and Roles

### 3.1 Core QA Definitions (Canonical)

| Document | Role |
|---------|------|
| `QA_Metric_Definitions.md` | Defines all quantitative QA metrics (accuracy, quality, efficiency) |
| `QA_Methodological_Checkpoints.md` | Defines mandatory governance and safety checks applied before scoring |
| `Inter_Rater_Agreement_Analysis_Plan.md` | Specifies reliability analysis for human evaluators |

---

### 3.2 Evaluation & Analysis Plans (Canonical)

| Document | Role |
|---------|------|
| `Efficiency_Measurement_Exploratory.md` | Defines exploratory efficiency-related outcomes |
| `Subgroup_and_Longitudinal_Analysis_Plan.md` | Specifies subgroup and within-subject analysis strategy |
| `Evaluation_and_QA_Methods_Integrated.md` | Integrated protocol section for IRB and manuscript Methods |

---

### 3.3 QA Execution Tools (Operational Standards)

| Document | Role |
|---------|------|
| `QA_Rater_OnePage_Checklist.md` | One-page checklist for human QA evaluators |
| `QA_Result_Report_Template_S0.md` | Standardized reporting template for S0 QA results |

**Note:** `expert_qa_accuracy_evaluation_form.md` is **DEPRECATED**. Use `06_QA_and_Study/QA_Operations/QA_Evaluation_Rubric.md` instead.

### 3.4 Pipeline Execution & Implementation (Canonical)

| Document | Role |
|---------|------|
| `Pipeline_Canonical_Specification.md` | Pipeline philosophy, entity definitions, step responsibilities (S1-S5) |
| `Pipeline_Execution_Plan.md` | JSONL contract-first execution plan and MI-CLEAR-LLM traceability |
| `Code_to_Protocol_Traceability.md` | Code-to-protocol mapping and implementation status (v1.6, latest) |
| `S1_S2_Independent_Execution_Design.md` | S1/S2 independent execution design (✅ Implemented) |
| `S0_Execution_Plan_Without_S4.md` | S0 execution plan without S4 (specific workflow) |
| `README_run.md` | Operational runbook for pipeline execution |
| `Implementation_Update_Log_2025-12-20.md` | Recent implementation updates and changes |

---

## 4. How These Documents Are Used Together

### 4.1 Pipeline Execution Workflow

A typical S0 pipeline execution proceeds as follows:

1. **S1 (Group-level structuring)** - `Pipeline_Canonical_Specification.md` Section 3
   - Generate master table and entity list
   - Output: `stage1_struct__arm{X}.jsonl`
2. **S1 Gate validation** - `validate_stage1_struct.py`
3. **Allocation** (S0 mode) - `03_CardCount_and_Allocation/`
4. **S2 (Card generation)** - `Pipeline_Canonical_Specification.md` Section 4
   - Generate exactly N cards per entity
   - Output: `s2_results__arm{X}.jsonl`
5. **S3 (Policy resolution & image spec)** - `Pipeline_Canonical_Specification.md` Section 5
   - Resolve image policies and compile image specs
   - Output: `s3_image_spec__arm{X}.jsonl`
6. **S4 (Image generation)** - `Pipeline_Canonical_Specification.md` Section 6
   - Generate images from S3 specs
   - Output: `s4_image_manifest__arm{X}.jsonl` + PNG files
7. **S5 (Export & packaging)** - `Pipeline_Canonical_Specification.md` Section 7
   - PDF builder for S0 QA
   - Anki deck export

**Implementation Status (2025-12-20):** ✅ All steps (S1-S5) implemented and operational

### 4.2 QA Evaluation Workflow

A typical S0 QA workflow proceeds as follows:

1. **Content generation and allocation** (Pipeline execution above)
2. **Checkpoint-based QA gating** (`QA_Methodological_Checkpoints.md`)
3. **Item-level scoring** using predefined metrics (`QA_Metric_Definitions.md`)
4. **Independent multi-rater evaluation** and agreement analysis (`Inter_Rater_Agreement_Analysis_Plan.md`)
5. **Optional exploratory efficiency measurement** (`Efficiency_Measurement_Exploratory.md`)
6. **Aggregation and longitudinal/subgroup analysis** (`Subgroup_and_Longitudinal_Analysis_Plan.md`)
7. **Standardized reporting of results** (`QA_Result_Report_Template_S0.md`)

The integrated methodological rationale is summarized in `Evaluation_and_QA_Methods_Integrated.md`.

---

## 5. Governance and Change Policy

- Documents labeled **Canonical** are authoritative at the execution level
- Changes to Canonical documents require:
  - Version increment
  - Documentation of rationale
  - Consistency with higher-level Governance documents
- Deprecated versions must be archived, not deleted

Operational checklists and templates may evolve more flexibly but must remain consistent with Canonical definitions.

---

## 6. Relationship to Other Directories

- `00_Governance/`: Defines terminology, evaluation units, and global methodological principles
- `03_CardCount_and_Allocation/`: Defines card-count authority and allocation logic
- `04_Step_Contracts/`: Defines step-specific roles and boundary contracts
- `06_QA_and_Study/`: QA framework, non-inferiority analysis, and study design

This directory focuses on **pipeline execution** (S1-S5) and **how evaluation and QA are executed and documented** once content exists.

---

## 7. One-Line Summary

> This directory operationalizes MeducAI’s evaluation philosophy by translating governance principles into executable QA procedures, metrics, and reporting standards.

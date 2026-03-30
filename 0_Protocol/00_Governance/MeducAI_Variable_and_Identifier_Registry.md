# MeducAI Variable and Identifier Registry

**Status:** Canonical  
**Version:** v1.1  
**Frozen:** Yes  
**Supersedes:** None  

**Applies to:** S0–S4, FINAL, codebase, QA logs, IRB documents  
**Last Updated:** 2025-12-26  

---

## 0. Purpose

This document defines the **authoritative semantic meaning, scope, and allowed usage** of all core variables and identifiers used across the MeducAI pipeline.

Its purpose is to:

- Prevent silent semantic drift between code, protocol, and manuscripts
- Eliminate identifier confusion (e.g., `group_id` vs `group_key`)
- Provide a single reference for developers, researchers, and reviewers
- Serve as the binding source for variable interpretation in IRB and Methods sections

This document complements (but does not replace) the **MeducAI Terminology Glossary**, which defines *concepts*.  
This registry defines *fields and variables*.

---

## 1. Global Design Principles

### 1.1 Identity vs Label

- **Identity**: Immutable, canonical, machine-level identifiers  
- **Label**: Human-readable, replaceable, non-authoritative descriptors  

> Identity is used for joining, allocation ownership, and invariants.  
> Labels are used for filtering, reporting, and readability only.

### 1.2 Decision vs Execution

- **Decision variables** are determined only by Allocation or Canonical policy
- **Execution variables** must strictly obey upstream decisions
- LLM stages never decide counts, priority, or policy

---

## 2. Core Identifiers

### 2.1 `group_id`

- **Type:** string (canonical ID)
- **Role:** Canonical identity of a Group
- **Properties:**
  - Immutable
  - Used for all joins, ownership, and allocation
- **Used in:**
  - Allocation artifacts
  - S1/S2 outputs
  - Runtime manifests
- **Prohibitions:**
  - Must never be inferred from `group_key`
  - Must never be user-facing by default


---

### 2.3 `group_key`

- **Type:** string (human-readable label)
- **Role:** Readable identifier for filtering and reporting
- **Properties:**
  - May change over time
  - Not guaranteed to be unique
- **Used in:**
  - CLI filtering (`only_group_key`)
  - QA reports and deck statistics
  - Human-facing summaries
- **Prohibitions:**
  - Must never be used as a join key
  - Must never replace `group_id`

---

## 3. Execution Context Variables

### 3.1 `run_tag`

- **Type:** string
- **Role:** Unique identifier for a single pipeline execution
- **Used in:**
  - Output directory roots
  - QA traceability
  - Reproducibility and audit
- **Rule:**
  - All runtime paths are derived from `run_tag`

---

### 3.2 `mode`

- **Type:** enum `{S0, FINAL}`
- **Semantic Meaning:**
  - `S0`: QA / model comparison with fixed payload
  - `FINAL`: Deployment generation with quota-based allocation
- **Implication:**
  - Changes allocation logic and enforcement rules

---

### 3.3 `arm`

- **Type:** string
- **Role:** Experimental condition identifier
- **Defines:**
  - Provider
  - Model
  - Prompt constraints
- **Notes:**
  - Arms define *experimental conditions*, not content meaning

---

## 4. Allocation & Count Variables

### 4.1 `set_target_cards` (S0 only)

- **Type:** integer
- **Role:** Fixed total number of cards per Set (Group × Arm)
- **Canonical Value:** 12
- **Rule:**
  - `Σ(cards_for_entity_exact) == set_target_cards`

---

### 4.2 `cards_for_entity_exact`

- **Type:** integer
- **Role:** Binding execution instruction for S2
- **Meaning:** Generate exactly N cards
- **Hard Rule:**
  - `len(anki_cards) != N → HARD FAIL`
- **Authority:**
  - Decided only by Allocation
  - S2 must never adjust or reinterpret

---

### 4.3 `allocation_version`, `allocation_path`

- **Role:** Audit and reproducibility metadata
- **Used for:**
  - Experiment traceability
  - IRB and Methods documentation

---

## 5. Entity-Level Variables

### 5.1 `entity_name`

- **Role:** Execution unit name defined in S1
- **Properties:**
  - Immutable once passed to S2
  - No semantic weight or priority
- **Prohibitions:**
  - Must not imply importance or quota

---

### 5.2 `entity_id`

- **Role:** Positional reference within a Group
- **Notes:**
  - Used only for ordering
  - Not semantically meaningful

---

## 6. Content Output Variables

### 6.1 `anki_cards[]`

- **Role:** Final learner-facing content units
- **Defined in:** S2
- **Rules:**
  - Exact cardinality enforcement
  - Schema must match Anki export contract

---

### 6.2 `visual_type_category`

- **Role:** Structural classification for presentation
- **Defined in:** S1
- **Notes:**
  - Must not influence allocation or selection

---

## 7. Image-Related Variables

### 7.1 `row_image_necessity`

- **Enum:** `{IMG_REQ, IMG_OPT, IMG_NONE}`
- **Role:** Declares whether an image is required
- **Authority:**
  - Assigned upstream
  - Enforced in S3
- **Prohibition:**
  - S4 must not reclassify

---

### 7.2 `image_lane`

- **Enum:** `{S4_CONCEPT, S4_EXAM}`
- **Role:** Rendering intent
- **Rules:**
  - Lanes must never mix
  - Resolution/model fixed per lane

---

## 8. Runtime & QA Variables

### 8.1 `runtime_manifest.json`

- **Role:** Declares what artifacts must exist for a valid run
- **Status Values:** `{PASS, FAIL, WARN}`
- **Notes:**
  - Canonical audit artifact

---

### 8.2 `qa_status`, `fail_reason`

- **Role:** Execution and QA traceability
- **Notes:**
  - Fail reasons must be explicit
  - Silent recovery prohibited

---

### 8.3 Execution Temperature Environment Variables (`TEMPERATURE_STAGEX`)

- **Role:** Control decoding stochasticity (lower ⇒ more deterministic) per pipeline step.
- **Type:** float
- **Scope:** Execution-only knob (does not change semantic policy or allocation).
- **Variables:**
  - `TEMPERATURE_STAGE1`: S1 generation (`3_Code/src/01_generate_json.py`)
  - `TEMPERATURE_STAGE2`: S2 generation (`3_Code/src/01_generate_json.py`)
  - `TEMPERATURE_STAGE4`: S4 image generation (`3_Code/src/04_s4_image_generator.py`)
  - `TEMPERATURE_STAGE5`: S5 validation/triage (`3_Code/src/05_s5_validator.py`)
- **Canonical default (current code):** `0.2` for all stages unless overridden.
- **Rule:** Any change to temperature values must be reported in run metadata/logs for reproducibility (MI-CLEAR-LLM stochasticity management).

---

## 9. Prohibited Patterns (Non-Negotiable)

- Using `group_key` as an identity
- Allowing S2 to alter card counts
- Inferring identifiers from labels
- Defaulting missing IDs instead of failing fast

---

## 10. Change Control

- Any semantic change to variables requires:
  1. Update to this registry
  2. Canonical review
  3. Version increment
- Code changes without registry updates are protocol violations

---

## 11. One-Line Summary

> **This document is the single authoritative source for the meaning and allowed use of variables and identifiers in MeducAI.**

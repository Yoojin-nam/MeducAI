물론입니다. 아래는 **`0_Protocol/Step01_Stabilization_Log_2025-12-16.md`**로 **그대로 저장해도 되는 완성본(Canonical 기록 문서)**입니다.
이미 README에 넣을 수 있도록 정제했던 내용을, **Protocol/IRB/재현성 관점에 맞게 더 포멀하게 다듬은 버전**입니다.

---

````markdown
# Step01 Stabilization Log
**Date:** 2025-12-16  
**Scope:** MeducAI Pipeline – Step01 (`01_generate_json.py`)  
**Status:** Frozen (S0-ready)

---

## 1. Purpose of This Document

This document records the **design decisions, implementation changes, and validation outcomes**
associated with stabilizing **Step01 (JSONL generation stage)** of the MeducAI pipeline.

The intent is to:

- Preserve **institutional memory** of critical design choices
- Prevent regression or reintroduction of previously resolved ambiguities
- Serve as a **canonical reference** for downstream pipeline design (Step02+)
- Support **IRB auditability, MI-CLEAR-LLM transparency, and reproducibility**

This log is considered **normative** for Step01 behavior as of the stated date.

---

## 2. Background

During early S0 testing, Step01 was executed as part of an end-to-end pipeline.
However, repeated failures and ambiguities revealed that:

- Step01 correctness could not be reliably assessed in the presence of
  incomplete or unstable downstream steps (Step02+)
- Provider and model resolution logic was **ambiguous**, particularly under
  multi-arm experimental settings
- CLI-driven overrides conflicted with arm-level experimental control

As a result, a focused stabilization phase was initiated with the explicit goal
of **freezing Step01 independently**.

---

## 3. Stabilization Objectives

The following objectives were defined for Step01 stabilization:

1. Step01 must be executable **independently** of downstream steps
2. Multi-arm execution (A–F) must be deterministic and debuggable
3. Output JSONL must strictly conform to the **Canonical Contract v1.1**
4. Provider/model resolution must be **unambiguous and arm-consistent**
5. All hard-fail conditions must be enforced at generation time

Only after satisfying these criteria would Step02+ be redesigned.

---

## 4. Key Design Decisions

### 4.1 Removal of `--provider` from Step01 CLI (Critical)

**Decision**

- `01_generate_json.py` no longer accepts `--provider` as a CLI argument
- Provider is resolved **exclusively** from per-arm configuration (`ARM_CONFIGS`)

**Rationale**

- Provider is an experimental factor and must be intrinsic to the arm
- CLI-level provider overrides caused ambiguity and invalid experimental states
- Arm-level resolution aligns with factorial experimental design principles

**Canonical Rule**

```text
provider := ARM_CONFIGS[arm].provider
````

No other source is permitted.

---

### 4.2 Model Override via CLI (`--model`) (Allowed Exception)

**Decision**

* A CLI argument `--model` is permitted as a **runtime override**
* Applied after arm-level provider resolution

**Rationale**

* Necessary to handle practical constraints such as:

  * Model access restrictions
  * Temporary API availability issues (e.g. Arm F)
* Avoids embedding one-off exceptions in source code
* Preserves reproducibility when logged in metadata

**Constraint**

* `--model` does **not** change provider
* Provider must still be consistent with arm definition

---

### 4.3 Runner Refactoring: Step01-only Execution

**Decision**

* `run_arm_full.py` was rewritten as a **Step01-only runner**
* Calls to Step02/03 were intentionally removed

**Rationale**

* Step02+ are scheduled for redesign and must not block Step01 validation
* Missing or unstable downstream scripts caused false-negative failures
* Clear stage isolation improves diagnosability and confidence

This runner is explicitly temporary and scoped to Step01 stabilization.

---

## 5. Current CLI Contract (Frozen)

### 5.1 Step01 (`01_generate_json.py`)

**기본 실행 (S1 + S2):**
```bash
python3 3_Code/src/01_generate_json.py \
  --mode S0 \
  --base_dir . \
  --run_tag <RUN_TAG> \
  --arm <A–F> \
  --seed 42 \
  --sample 1 \
  [--model <model_name>]
  # --stage both (기본값)
```

**S1만 실행:**
```bash
python3 3_Code/src/01_generate_json.py \
  --mode S0 \
  --base_dir . \
  --run_tag <RUN_TAG> \
  --arm <A–F> \
  --stage 1 \
  --sample 1
```

**S2만 실행 (S1 출력 필요):**
```bash
python3 3_Code/src/01_generate_json.py \
  --mode S0 \
  --base_dir . \
  --run_tag <RUN_TAG> \
  --arm <A–F> \
  --stage 2 \
  --sample 1
```

**Stage 옵션:**
- `--stage 1`: S1만 실행
- `--stage 2`: S2만 실행 (기존 S1 출력 파일 필요)
- `--stage both`: S1+S2 실행 (기본값)

**Explicitly NOT supported:**

* `--provider`

---

### 5.2 Step01 Runner (`run_arm_full.py`)

```bash
python3 3_Code/src/run_arm_full.py \
  --base_dir . \
  --mode S0 \
  --run_tag <RUN_TAG> \
  --arms A,B,C,D,E,F \
  --sample 1
```

* Executes Step01 only
* Multi-arm smoke testing supported
* Downstream steps intentionally excluded

---

## 6. Validation Summary (S0 6-Arm Smoke Test)

### 6.1 Execution Results

| Arm | Status      | Notes                                                       |
| --- | ----------- | ----------------------------------------------------------- |
| A–E | PASS        | JSONL generated successfully                                |
| F   | CONDITIONAL | Failed due to model access; resolved via `--model` override |

---

### 6.2 Schema / Contract Validation

Automated checks confirmed:

* Root keys present:

  * `metadata`
  * `source_info`
  * `curriculum_content`
* Hard-fail enforcement:

  * `table_infographic.prompt_en` is non-empty
  * `IMG_REQ → row_image_prompt_en` is non-empty
* No schema violations detected in inspected fields

**Result:** PASS

---

## 7. Qualitative Output Review

Manual inspection confirmed that:

* `master_table` is clinically accurate and well-structured
* Table infographic prompts are explicit and suitable for professional generation
* Entity-level structures are stable and Anki-compatible
* Image necessity flags are coherent and actionable

Step01 outputs are deemed **fit for educational and research use**.

---

## 8. Freeze Declaration

As of **2025-12-16**, Step01 is declared:

> **STABLE AND FROZEN FOR S0**

Any future changes to Step01 must:

* Be explicitly justified
* Be documented in a new stabilization or revision log
* Avoid breaking the current CLI and JSONL contract

---

## 9. Next Steps (Out of Scope for This Document)

* Redesign and implementation of Step02 based on frozen Step01 JSONL
* Definition of downstream CSV schemas
* Reintroduction of image and Anki pipelines post-Step02 freeze

---

## 10. Document Status

* This document is **canonical**
* Supersedes any informal notes or chat-based decisions prior to 2025-12-16
* Intended for internal development, IRB audit, and reproducibility review

---

```

---

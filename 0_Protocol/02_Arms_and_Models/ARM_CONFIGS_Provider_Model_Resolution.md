# ARM_CONFIGS – Provider / Model Resolution Protocol
**Date:** 2025-12-19 (Updated)  
**Scope:** MeducAI Pipeline – Step01 and beyond  
**Status:** Canonical (Frozen for Step01)

---

## 1. Purpose

This document defines the **authoritative rules** by which
**provider** and **model** are selected and resolved in the MeducAI pipeline.

It exists to:

- Eliminate ambiguity in multi-arm experimental execution
- Ensure reproducibility and auditability (MI-CLEAR-LLM / IRB)
- Prevent accidental override of experimental factors
- Provide a stable contract for downstream steps (Step02+)

This protocol is **normative** for Step01 as of the stated date.

---

## 2. Design Principle (Non-Negotiable)

> **Provider and model selection are experimental factors, not runtime options.**

Therefore:

- Provider is an intrinsic property of an **arm**
- Model selection follows a **strict precedence order**
- CLI arguments must not invalidate arm semantics

---

## 3. Conceptual Hierarchy

```

Experiment
└── Arm (A–F)
├── provider  ← FIXED experimental factor
├── default_model
└── optional runtime model override

````

---

## 4. ARM_CONFIGS Definition (Conceptual)

Each arm is defined with a **fixed provider**, optionally accompanied by a
default model.

```python
ARM_CONFIGS = {
    "A": {
        "label": "Baseline",
        "provider": "gemini",
        "api_style": "chat",
        "model_stage1": "gemini-3-flash-preview",
        "model_stage2": "gemini-3-flash-preview",
        "thinking": False,
        "rag": False,
        "thinking_level": "minimal"  # Gemini 3 uses thinking_level
    },
    "B": {
        "label": "RAG_Only",
        "provider": "gemini",
        "api_style": "chat",
        "model_stage1": "gemini-3-flash-preview",
        "model_stage2": "gemini-3-flash-preview",
        "thinking": False,
        "rag": True,
        "thinking_level": "minimal"
    },
    "C": {
        "label": "Thinking",
        "provider": "gemini",
        "api_style": "chat",
        "model_stage1": "gemini-3-flash-preview",
        "model_stage2": "gemini-3-flash-preview",
        "thinking": True,
        "rag": False,
        "thinking_level": "high"  # Gemini 3: high thinking
    },
    "D": {
        "label": "Synergy",
        "provider": "gemini",
        "api_style": "chat",
        "model_stage1": "gemini-3-flash-preview",
        "model_stage2": "gemini-3-flash-preview",
        "thinking": True,
        "rag": True,
        "thinking_level": "high"
    },
    "E": {
        "label": "High_End",
        "provider": "gemini",
        "api_style": "chat",
        "model_stage1": "gemini-3-pro-preview",
        "model_stage2": "gemini-3-pro-preview",
        "thinking": True,
        "rag": True,
        "thinking_budget": 2048  # Gemini 3 Pro uses thinking_budget
    },
    "F": {
        "label": "Benchmark",
        "provider": "gpt",
        "api_style": "responses",  # OpenAI Responses API
        "model_stage1": "gpt-5.2-2025-12-11",  # non-pro version
        "model_stage2": "gpt-5.2-2025-12-11",
        "thinking": True,
        "rag": True,
        "temp_stage1": 0.0,
        "temp_stage2": 0.0,
        # reasoning.effort="medium" applied via API
    }
}
```

**Notes (Updated 2025-12-19):**
* **Provider is mandatory** for each arm
* **Gemini 3 models** (A-D, E): Use `thinking_level` ("minimal", "low", "medium", "high") instead of `thinking_budget`
* **Gemini 3 Pro** (E): Uses `thinking_budget` (2048) for backward compatibility
* **GPT-5.2** (F): Uses OpenAI Responses API with `reasoning.effort="medium"`
* Default model may be implicit via `MODEL_CONFIG` if not specified in arm config

---

## 5. MODEL_CONFIG Definition (Conceptual)

Providers map to one or more supported models.

```python
MODEL_CONFIG = {
    "gemini": {
        "default_model": "gemini-3-flash-preview"  # Updated 2025-12-19
    },
    "gpt": {
        "default_model": "gpt-5.2-2025-12-11"  # Updated 2025-12-19 (non-pro for Arm F)
    }
}
```

---

## 6. Resolution Algorithm (Canonical)

### 6.1 Provider Resolution (Step01)

**Source of Truth:** `ARM_CONFIGS`

```text
provider := ARM_CONFIGS[arm].provider
```

Rules:

* CLI input is NOT consulted
* Environment variables are NOT consulted
* Any attempt to override provider at runtime is invalid

---

### 6.2 Model Resolution (Step01)

Model selection follows **strict precedence order**:

```
1. CLI --model override (if provided)
2. MODEL_CONFIG[provider].default_model
3. Hard-coded safe fallback (provider-specific)
```

Formally:

```text
if args.model is provided:
    model := args.model
else:
    model := MODEL_CONFIG[provider].default_model
```

Constraints:

* `--model` must be compatible with resolved provider
* `--model` MUST NOT change provider semantics

---

## 7. Explicitly Forbidden Patterns

The following are **explicitly prohibited**:

### 7.1 CLI Provider Override

```bash
--provider gemini   # ❌ forbidden
```

**Reason:**

* Breaks arm-level experimental control
* Creates irreproducible states

---

### 7.2 Provider Inference from Model Name

```python
if model.startswith("gpt"):
    provider = "gpt"   # ❌ forbidden
```

**Reason:**

* Provider must be explicit
* Model naming conventions are not stable contracts

---

### 7.3 Environment Variable Provider Control

```bash
PROVIDER=gemini   # ❌ forbidden
```

**Reason:**

* Hidden global state
* Breaks determinism

---

## 8. Metadata Logging Requirement

The **final resolved values** must be recorded in output metadata.

Required fields (Step01 JSONL):

```json
metadata: {
  "arm": "F",
  "provider": "gpt",
  "model": "gpt-5.2-pro-2025-12-11",
  "model_override": true,
  "resolution_protocol": "ARM_CONFIGS_v1"
}
```

This ensures:

* Reproducibility
* Auditability
* Clear post-hoc analysis

---

## 9. Implications for Downstream Steps (Step02+)

Downstream steps may assume:

* Provider and model are already resolved
* They must NOT attempt to re-resolve provider/model
* They may only **consume metadata**

Step02+ must treat provider/model as **read-only facts**.

---

## 10. Change Control

This protocol is **frozen for Step01**.

Any changes require:

1. Explicit justification
2. New protocol version
3. Corresponding stabilization log

Silent modification is prohibited.

---

## RAG / Thinking Acceptance Gate (S0 – Hard Rule)

For S0 QA experiments, RAG and Thinking are **experimental factors** and
**must be actually executed and measurably logged**.

**If the Acceptance Criteria are not satisfied, S0 full runs are prohibited.**

Minimum Acceptance Criteria include:
- `rag_enabled`, `thinking_enabled` recorded in metadata
- Non-null retrieval evidence when enabled (e.g., `rag_sources_count > 0`)
- Explicit thinking control applied at the API level and reflected in metadata
- Latency (and tokens where available) recorded per stage or in total

**Arm-to-arm comparison is permitted only after all Acceptance Criteria pass.**

This rule is binding and non-negotiable for Step S0.

---

## 11. Summary (One-Sentence Rule)

> **Arms define providers; providers define models; CLI may only override models, never providers.**
# Runtime Artifact Index / Manifest Specification

**Status:** Canonical
**Applies to:** MeducAI Runtime Execution (S0, S1, S2, S3, S4, FINAL)
**Purpose:** 하나의 RUN_TAG 아래에서 **무엇이 생성되어야 정상인지**, 그리고 **누락 시 FAIL/WARN 기준**을 단일 스펙으로 고정한다.

---

## 1. Core Principles (Non-Negotiable)

1. **RUN_TAG 단위 완결성**  
   모든 산출물은 반드시 `2_Data/metadata/generated/{RUN_TAG}/` 하위에 존재해야 하며, 외부 위치 산출물은 비정상 상태로 간주한다.

2. **Manifest-First Interpretation**  
   개별 파일의 존재 여부보다 **Manifest에 기록되었는지**가 1차 판정 기준이다.

3. **Fail-Fast 연동**  
   필수 artifact 누락은 해당 단계의 Abort Scope에 따라 즉시 FAIL 처리한다.

---

## 2. Runtime Artifact Manifest (Top-Level)

### 2.1 Canonical File

```
2_Data/metadata/generated/{RUN_TAG}/
└── runtime_manifest_{RUN_TAG}.json
```

### 2.2 Manifest Purpose

* 해당 RUN_TAG에서 **의도된 실행 단계 목록**
* 단계별 **생성 성공/실패 여부**
* artifact index (경로 + 유형)
* FAIL/WARN 판정의 단일 근거

---

## 3. Manifest Minimum Schema (Binding)

```json
{
  "run_tag": "S0_XXXX",
  "mode": "S0 | FINAL",
  "timestamp": "2025-12-17T00:00:00Z",

  "execution_plan": ["Preflight", "S0_Allocation", "S1", "S2", "S3", "S4"],

  "artifacts": {
    "Preflight": { ... },
    "S0_Allocation": { ... },
    "S1": { ... },
    "S2": { ... },
    "S3": { ... },
    "S4": { ... }
  },

  "final_status": "PASS | FAIL",
  "fail_reason": null
}
```

---

## 4. Required Artifacts by Step

### 4.1 Preflight

**Required**

| Artifact | Pattern | Missing |
|-------|--------|---------|
| Preflight log | `preflight_check.log` | FAIL (RUN) |
| groups.csv hash | embedded in manifest | FAIL (RUN) |

---

### 4.2 S0 Allocation (S0 only)

**Required**

| Artifact | Pattern | Missing |
|--------|--------|---------|
| Allocation artifact | `allocation/allocation_s0__group_*__arm_*.json` | FAIL (SET) |

**Optional**

| Artifact | Missing |
|--------|---------|
| Allocation summary | WARN |

---

### 4.3 Step01 (S1 – JSONL Generation)

**Required**

| Artifact | Pattern | Missing |
|--------|--------|---------|
| Group JSONL | `output_*__arm*.jsonl` | FAIL (ARM) |

**Optional**

| Artifact | Missing |
|--------|---------|
| Validation report | WARN |

---

### 4.4 Step02 (S2 – Execution)

**Required**

| Artifact | Pattern | Missing |
|--------|--------|---------|
| Entity execution result | `s2_entity_*__group*.json` | FAIL (GROUP) |

---

### 4.5 Step03 (S3 – QA / Selection)

**Required**

| Artifact | Pattern | Missing |
|--------|--------|---------|
| QA result | `s3_qa__group*.json` | FAIL (GROUP/SET) |
| Selected manifest | `selected_cards__group*.json` | FAIL (GROUP/SET) |

**Optional**

| Artifact | Missing |
|--------|---------|
| selection_trace | WARN |

---

### 4.6 Step04 (S4 – Rendering)

**Required**

| Artifact | Pattern | Missing |
|--------|--------|---------|
| Image prompt index | `image_prompts__group*.csv` | FAIL (GROUP) |

**Optional**

| Artifact | Missing |
|--------|---------|
| Rendered images | WARN (text-only fallback) |

---

### 4.7 FINAL Allocation (FINAL only)

**Required**

| Artifact | Pattern | Missing |
|--------|--------|---------|
| Group quota file | `target_cards_per_group_*.json` | FAIL (RUN) |

---

## 5. FAIL vs WARN Classification Rules

### 5.1 FAIL (Hard Stop)

* Required artifact missing
* Manifest mismatch with execution_plan
* Artifact schema invalid

### 5.2 WARN (Soft)

* Optional artifact missing
* Non-critical summary/log absent
* Image generation skipped with fallback 가능

WARN는 **final_status를 FAIL로 변경하지 않는다**.

---

## 6. Relationship to Fail-Fast Policy

* 본 문서는 **Pipeline_FailFast_and_Abort_Policy.md**의
  *Artifact 판정 기준*을 구체화한 하위 스펙이다.
* 충돌 시 **Fail-Fast & Abort Policy가 상위 기준**이다.

---

## 7. Canonical One-Line Summary

> **A run is valid only if all required artifacts declared in the runtime manifest exist and are schema-valid; optional artifacts may be missing with warnings, but never silently.**

---

**This document is Canonical and Frozen.**
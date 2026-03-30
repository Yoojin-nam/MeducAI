# MeducAI S1 Gate Checklist (Fail-fast Canonical)

**Status:** Canonical (FINAL FREEZE)  
**Version:** 1.2  
**Frozen:** Yes (Complete Freeze - Schema validation rules are final)  
**Supersedes:** `s_1_gate_checklist_canonical.md` (v1.1, 2025-12-18)  
**Location:** `0_Protocol/01_Execution_Safety/stabilization/`  
**Applies to:** `--stage 1`, `--stage both`  
**Mode:** Fail-fast (Gate failure returns non-zero exit code)  
**Target schema:** `S1_STRUCT_v1.3` (FROZEN)  
**Last Updated:** 2025-12-19 (KST)

**⚠️ IMPORTANT: S1 Schema/Structure Complete Freeze (2025-12-19)**

As of 2025-12-19, the S1 output schema (`S1_STRUCT_v1.3`) and structure are **completely frozen**. This Gate validates against the frozen schema. No further structural changes to the S1 output format are permitted. The pipeline is ready to proceed to downstream stages (S2, S3, S4).

**Note:** While the schema is frozen, **S1 prompt improvements are allowed and planned** for future iterations. Prompt changes must not alter the output schema structure.

---

## 0. Purpose and Scope

S1 (`stage1_struct.jsonl`) is the **single entry point** for Group → Structure: visual type selection, master table rendering, and entity structuring.

If S1 output drifts, downstream stages (S2/S3/S4/QA) collapse or become non-deterministic.  
This Gate enforces **immediate PASS/FAIL** on the S1 output artifacts and blocks downstream execution on FAIL.

**Normative references:**
- `00_Governance/S1_Stage1_Struct_JSON_Schema_Canonical.md` (v1.3)
- (Optional, upstream) `00_Governance/Objective_Bullets_and_LargeGroup_Summarization_Canonical.md`

---

## 1. Required Artifact

After running S1, the following MUST exist:

- `2_Data/metadata/generated/<RUN_TAG>/stage1_struct.jsonl`

---

## 2. Gate Levels

### 2.1 Level 0 — Existence (Fail-fast)

FAIL if:

- `stage1_struct.jsonl` missing
- file is empty (0 bytes) or has 0 non-empty JSON lines

**Exit code recommendation:** 3

---

### 2.2 Level 1 — NDJSON parseability (Fail-fast)

For each non-empty line:

FAIL if:

- the line is not valid JSON
- the parsed JSON is not an object (must be `{...}`)

**Exit code recommendation:** 3

---

### 2.3 Level 2 — Schema conformance (Binding, Fail-fast)

Schema reference: `S1_Stage1_Struct_JSON_Schema_Canonical.md` (v1.3)

For every record (JSON object), FAIL if any of the following are true:

#### A) Required top-level keys missing / wrong type

- `schema_version` missing or not exactly `"S1_STRUCT_v1.3"`
- missing or empty: `group_id`, `group_path`
- `objective_bullets` missing, not an array, or empty
- `visual_type_category` missing or not in canonical enum
- `master_table_markdown_kr` missing or not a string
- `entity_list` missing, not an array, or empty
- `integrity` missing or not an object

#### B) Entity object validity

For each element of `entity_list`, FAIL if:

- entity is not an object
- missing or empty: `entity_id`, `entity_name`
- duplicate `entity_id` within the record

#### C) Integrity object (binding count checks)

FAIL if any mismatch:

- `integrity.entity_count != len(entity_list)`
- `integrity.objective_count != len(objective_bullets)`

> Note: `integrity.table_row_count` is validated in Level 2.4 after master table parsing.

**Exit code recommendation:** 3

---

### 2.4 Level 3 — Master table hard constraints (Binding, Fail-fast)

Parse `master_table_markdown_kr` as markdown table.

FAIL if any hard constraints are violated:

1) Exactly **one** markdown table is present.  
2) Header row is an **exact match** to the project’s canonical header set  
   - (defined by the S1 prompt bundle / validator constants; comparison must be strict).  
3) Fixed column count: every data row has the **same number of cells** as the header.  
4) No empty cells.  
5) No multiline cells (no embedded newline inside any cell).  
6) No raw `|` characters inside cells (must be sanitized/escaped upstream).  
7) `data_rows <= 20` (hard max).

Row count policy (enforced by Gate):

- `data_rows > 20` → **FAIL**  
- `15–20` → **PASS requires warnings** (see Level 2.5)  
- `10–14` → target  
- `<10` → allowed; MAY warn if the group appears broad

**Exit code recommendation:** 3

---

### 2.5 Level 4 — Table↔Entity alignment (Binding, Fail-fast)

After parsing the master table:

FAIL if:

- `len(entity_list) != data_rows`
- entity order does not match the master table row order (row-by-row)
- `entity_name` is not derived from the designated “entity label” column
  - (the designated column name is fixed by the S1 prompt bundle / validator constants)
- `integrity.table_row_count != data_rows`

**Exit code recommendation:** 3

---

### 2.6 Level 5 — Backward compatibility & forbidden fields (Binding)

#### A) Forbidden field (Fail-fast)

FAIL if:

- `visual_type_other` is present anywhere in the record (deprecated; treat as FAIL to prevent schema drift)

**Exit code recommendation:** 3

#### B) Legacy field tolerance (Warn-only)

- `record_id` is NOT part of the official contract and MUST NOT be required by validators or consumers.
- If `record_id` is present:
  - Consumers SHOULD ignore it.
  - Gate SHOULD emit a warning if `record_id != group_id`.

**Exit code recommendation (warn-only):** 0 (PASS with warning)

---

### 2.7 Level 6 — Required warning policy for 15–20 rows (Binding)

If `data_rows` is in **[15, 20]**, the record MUST include a warning string.

Gate behavior:

- If `warnings` is missing / not an array / empty → **FAIL**
- Else PASS, but Gate SHOULD ensure at least one warning string explicitly indicates `row_count=15_20` policy
  - e.g., `"ROWCOUNT_WARN_15_20"` (exact string is up to your validator; must be deterministic)

**Exit code recommendation:** 3 for missing-required-warning, 0 for PASS-with-warning

---

### 2.8 Level 7 — Minimal QA usability (Warn-only, recommended)

These are not schema violations, but are strong predictors of downstream confusion.  
Gate MAY warn (but should not fail) if:

- `entity_name` is a vague meta label (e.g., “Overview”, “Misc”, “General”)
- `entity_name` duplicates after whitespace/case normalization
- `linked_objective_indices` contains out-of-range indices (if present)

**Exit code recommendation:** 0 (PASS with warning)

---

## 3. Pass Criteria

Gate PASS requires **Levels 0–5** to pass for all records.

- Level 6 (15–20 row warning policy) is binding when applicable and MUST be satisfied.
- Levels 7 warnings do not block PASS unless you deliberately switch to a stricter stabilization mode.

---

## 4. Operational Notes (How to run)

Typical run sequence (example):

```bash
cd /path/to/workspace/workspace/MeducAI
export RUN_TAG="S1_GATE_SMOKE_$(date +%Y%m%d_%H%M%S)"

python 3_Code/src/01_generate_json.py --base_dir . --run_tag "$RUN_TAG" --arm A --mode S0 --row_index 25

# Gate / validator
python 3_Code/src/validate_stage1_struct.py --base_dir . --run_tag "$RUN_TAG"
echo $?
```

---

## 5. File Replacement Workflow Notes (Operational)

After download, replace the canonical file in your repo:

```bash
cd /path/to/workspace/workspace/MeducAI
mv /path/to/workspace/Downloads/s_1_gate_checklist_canonical.REPLACEMENT.md 0_Protocol/01_Execution_Safety/stabilization/s_1_gate_checklist_canonical.md
```

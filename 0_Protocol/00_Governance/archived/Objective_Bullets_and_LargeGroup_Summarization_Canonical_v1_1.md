# Objective Bullets Rendering Standard and Large-Group Summarization Rules (Operating Canonical)

**Status:** Archived (Active)  
**Superseded by:** `0_Protocol/00_Governance/Objective_Bullets_and_LargeGroup_Summarization_Canonical.md`
**Do not use this file for new decisions or execution.**
**Version:** 1.1  
**Date:** 2025-12-18 (KST)  
**Frozen:** NO  
**Supersedes:** Version 1.0 (2025-12-18)  

---

## 0. Purpose

This document fixes:

1) The **deterministic rendering standard** that converts `objective_list` (a JSON array string) into `objective_bullets` (a Markdown bullet list) for S1 prompting.

2) The **large-group summarization operating rule** that keeps S1 outputs stable when a group contains many objectives (e.g., 30–40), by constraining the **master table row count** and enforcing **core-only** entity selection.

This version incorporates the **Weekly Integrated Conclusion (Operating SSOT)** decisions, especially the updated row/entity cap and the “prompt+gate responsibility” boundary.

---

## 1. Definitions

- `objective_list`  
  - **Type:** JSON string representing a JSON array of objective strings (as stored in CSV).  
  - **Example (raw CSV cell):**  
    - `["Define spinal dysraphism and describe and diagnose its various forms using imaging (A)."]`

- `objective_bullets`  
  - **Type:** Markdown bullet list (plain text).  
  - **Example:**  
    - `- Define spinal dysraphism and describe and diagnose its various forms using imaging.`

- “Large group”  
  - A group with **objective_count > 14**.

---

## 2. Hard Invariants

### 2.1 Objective rendering invariants (S1 input)
- The transformation MUST be deterministic and stable for identical inputs.
- Ordering MUST be preserved (same order as JSON array).
- Empty or non-parseable `objective_list` MUST be treated as a **preflight failure** (do not call the model).
- Output MUST be a Markdown bullet list:
  - Each objective on one line.
  - Each line MUST start with `- `.
  - Line separator MUST be `\n` (LF).

### 2.2 Normalization policy (recommended default)
To reduce noise and stabilize clustering, apply **end-of-string difficulty marker stripping**:

- Strip only if it matches the pattern at the end of the objective:
  - `(A)` / `(B)` / `(C)` with optional trailing period
- Do NOT strip other parentheses occurring mid-sentence.

Recommended regex (after trimming whitespace):
- `\s*\(([ABC])\)\.?\s*$`

**Traceability rule:** Keep the original `objective_list` unchanged in the source CSV. Only `objective_bullets` is normalized.

### 2.3 Role boundary (important)
- **Preprocessing** (this document) only normalizes input into `objective_bullets`.
- **Summarization / row-count enforcement** is a **prompt + gate** responsibility (S1 prompt must instruct it; S1 Gate must enforce it).  
  Preprocessing MUST NOT “summarize” or delete objectives.

---

## 3. Rendering Specification

### 3.1 Input
- `objective_list` string (JSON array string)

### 3.2 Output (`objective_bullets`)
- A single text block:
  - Line 1: `- <Objective 1 normalized>`
  - Line 2: `- <Objective 2 normalized>`
  - ...
- No numbering, no extra blank lines at the top or bottom.

### 3.3 Example
Input (`objective_list`):
```json
["Define spinal dysraphism and describe and diagnose its various forms using imaging (A).",
 "List key imaging features of split cord malformation (B)."]
```

Output (`objective_bullets`):
```text
- Define spinal dysraphism and describe and diagnose its various forms using imaging.
- List key imaging features of split cord malformation.
```

---

## 4. Large-Group Summarization Rule (Operating)

### 4.1 Trigger
Apply when **objective_count > 14**.

### 4.2 Objective
Even with many objectives, the S1 output MUST remain stable:

- **Hard max:** master table rows/entities **<= 20**  
- **Preferred target:** **10–14** rows/entities  
- **Large groups:** **15–20** is allowed **only if necessary**, and should be treated as **PASS with Warning** (log a warning; do not fail).  
- **> 20 rows/entities:** **FAIL** (gate must reject)

Rationale: a strict 8–14 hard cap can over-compress broad groups and destabilize outputs; the operating SSOT adopts a “preferred 10–14, allow 15–20 with warning, hard max 20” policy.

### 4.3 What “core concepts” means (selection constraints)
A selected row/entity SHOULD satisfy at least one of:
- High-yield exam category/classification node (e.g., “Open vs Closed dysraphism”)
- Canonical lesion/condition that anchors multiple objectives (coverage)
- Frequent pitfall/differential that is repeatedly tested
- Structurally necessary framework item (definition, key imaging approach) when needed for coherence

A selected row/entity MUST NOT be:
- A synonym-only variant of another selected entity
- A trivial detail or rare trivia with no exam relevance
- A mixed-granularity item (e.g., combining a modality, a sign, and a disease name in one entity)

### 4.4 Coverage rule (ensuring objectives are “represented”)
For large groups, the table/entities must cover the objectives via **conceptual aggregation**:

- Step A: Cluster objectives into major subthemes (2–6 subthemes typical).
- Step B: For each subtheme, select 1–3 representative “core” concepts.
- Step C: Ensure no subtheme is entirely missing.
- Step D: If too many candidates remain, collapse:
  - Merge near-synonyms into canonical labels
  - Prefer broader exam categories over micro-subtypes
  - Keep “pitfalls” rows only if they change diagnosis/classification

### 4.5 Deterministic row-count policy (recommended operating mapping)
This is a deterministic target mapping for S1 prompt authoring and for interpretation of “PASS with Warning”:

- If objectives 1–8: allow 5–10 rows (do not pad with fluff).
- If objectives 9–14: target 8–14 rows.
- If objectives 15–40: target 10–14 rows (allow 15–20 with warning).
- If objectives > 40: target 12–14 rows (allow 15–20 with warning).

---

## 5. Table Format Constraints (must be enforced in S1 prompt + S1 Gate)

To prevent table breakage and drifting formats:

- Exactly **one** master table.
- Column headers are **EXACT match** to the project’s canonical set (wording and order).
- Fixed column count (e.g., 6 columns if that is the canonical table).
- Each data row has exactly the same number of cells as headers.
- No cell contains raw `|` characters (replace/escape by a defined rule).
- No multiline cells.
- No empty cells.
- **Data rows <= 20** (hard).

---

## 6. Entity List Interface Notes (tie-in for stability)

This document does not define the full S1 schema, but it constrains behavior that affects large-group summarization stability:

- `entity_list` length MUST match the number of master table data rows (same order).
- `entity_id` is **code-owned deterministic** and MUST NOT be generated by the LLM.
  - Recommended deterministic format: `{group_id}__E{index:02d}` in table row order.
- `entity_name` is a **display label**, not a join key.

---

## 7. Pipeline Integration (recommended)

1) Read `objective_list` from CSV (string).
2) Parse JSON array.
3) Normalize (strip end difficulty markers) for `objective_bullets`.
4) Pass `objective_bullets` into the S1 user template.
5) Gate check before LLM call:
   - bullet list non-empty
   - each line starts with `- `
   - no raw braces/quotes artifacts from CSV escaping

---

## 8. Quick Preflight Checklist (fail-fast)

- [ ] `objective_list` is valid JSON array string
- [ ] Parsed list length equals `objectives` count
- [ ] `objective_bullets` contains one bullet per objective
- [ ] Optional: difficulty marker stripped only at end-of-string
- [ ] No empty bullet lines

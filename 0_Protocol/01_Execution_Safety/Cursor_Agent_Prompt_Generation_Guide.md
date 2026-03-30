# Cursor Agent Prompt Generation Guide (MD Template)

**Status:** Working Draft  
**Last updated:** 2025-12-20  
**Audience:** You (MeducAI maintainer)  
**Scope:** How to write high-signal prompts for **Cursor Agent** to implement complex changes end-to-end (policy + code + tests) with minimal iteration.

---

## 1. Core idea

Cursor Agent performs best when your prompt makes the following **unambiguous**:

1) **What is frozen (must not change)**  
2) **What must change (explicit intent)**  
3) **What files are relevant (use `@` to load context)**  
4) **What “done” means (deliverables + verification plan)**  
5) **What the Agent may/may not execute (command rules)**  
6) **How to recover (checkpoints and rollback)**

Think of the Agent prompt as a **mini contract**: constraints + inputs + outputs + acceptance tests.

---

## 2. Use `@` to give the Agent the right context

### 2.1 Minimum recommended `@` set (for code changes)

- Target implementation files (the ones you expect to change)
- Adjacent helper/registry/path modules that influence behavior
- Canonical policies/contracts/schemas that define invariants
- Validators/gates/smoke runners (if acceptance criteria depends on them)

Example (MeducAI-like):

- `@3_Code/src/03_s3_policy_resolver.py`
- `@3_Code/src/04_s4_image_generator.py`
- `@3_Code/src/generated_paths.py`
- `@0_Protocol/.../S1_Stage1_Struct_JSON_Schema_Canonical.md`
- `@0_Protocol/.../S2_Contract_and_Schema_Canonical.md`
- `@3_Code/src/validate_stage1_struct.py` (optional)

### 2.2 When to add more files

Add extra `@` context when:
- There is a **frozen schema** (Agent must see it to avoid breaking it)
- File naming / output paths must remain deterministic
- You have prior docs/policies that must be updated consistently
- There is a repeated bug that appears in logs (include a log snippet file)

---

## 3. The prompt structure that consistently works

Use this structure (copy/paste and fill placeholders):

### 3.1 Prompt skeleton (best practice)

1. **Objective**
2. **Context files (`@...`)**
3. **Hard constraints (do-not-change)**
4. **Required changes (what must change)**
5. **Artifacts & deterministic naming**
6. **Failure rules (fail-fast / warn-only)**
7. **Command rules (safe commands only)**
8. **Deliverables + smoke test plan**

---

## 4. Copy-paste templates

### 4.1 Minimal template (fast)

```text
Objective: <one sentence: what end-state must be achieved>

Context:
@<file1>
@<file2>
@<policy_or_schema_doc>

Hard constraints:
1) <do not change X>
2) <do not change Y>

Required changes:
A) <change 1>
B) <change 2>

Deliverables:
1) <code changes>
2) <doc updates>
3) <test plan>
```

Use this only when the scope is small and you can inspect quickly.

---

### 4.2 Full template (recommended for multi-file / policy+code tasks)

```text
We need an end-to-end patch.

Context files:
@<primary_code_file>
@<secondary_code_file>
@<paths_or_registry>
@<canonical_schema_or_contract>
@<policy_doc_to_update>

HARD CONSTRAINTS:
1) Do NOT modify <frozen schema/contract>. Do NOT require new fields.
2) Do NOT change deterministic filenames/paths. Preserve run_tag semantics.
3) <no destructive actions>, <no LLM calls> (if applicable).
4) Maintain backwards compatibility with existing generated artifacts.

CHANGES REQUIRED:
A) <policy/behavior change with explicit mapping or examples>
B) <artifact change: new field, new spec_kind, etc.>
C) <prompt/content logic changes if relevant>
D) <model/config default changes>

ARTIFACTS / OUTPUTS:
- <file path> must contain <rows/keys>
- Deterministic naming: <filename spec>

FAILURE RULES:
- Fail-fast: <cases>
- Warn-only: <cases>

WORKFLOW / COMMAND RULES:
- Allowed: <safe commands>
- Forbidden: <rm -rf>, <mass reformat>, <destructive scripts>

DELIVERABLES:
1) Update docs: <doc file> reflects new behavior
2) Update code: <files>
3) Provide smoke test plan and expected indicators
```

---

## 5. MeducAI-style example (policy + code + artifacts)

This example is tailored to tasks like “S3/S4 update” where S1/S2 schemas are frozen:

```text
We need an end-to-end patch to S3 and S4 (code + policy doc), without changing frozen S1/S2 output schemas.

Context files:
@3_Code/src/03_s3_policy_resolver.py
@3_Code/src/04_s4_image_generator.py
@0_Protocol/01_Execution_Safety/stabilization/S3_S4_code_behavior.md
@0_Protocol/.../S1_Stage1_Struct_JSON_Schema_Canonical.md
@0_Protocol/.../S2_Contract_and_Schema_Canonical.md
@3_Code/src/generated_paths.py

HARD CONSTRAINTS:
1) Do NOT modify S1 output schema or file format. Do NOT require new fields from S1.
2) Do NOT modify S2 output schema or contract. Do NOT require new fields from S2.
3) S3 must remain deterministic (NO LLM calls). S4 only calls an image model.
4) Preserve deterministic filenames and reproducible artifacts (run_tag/group_id/entity_id/card_role based).
5) Update BOTH doc and code consistently.

CHANGES REQUIRED:
A) Q2 must also require an image asset (image_required/image_asset_required becomes true).
B) S3 must compile both:
   - S2-derived card image specs (Q1+Q2)
   - S1-derived group-level table/visual spec (1 per group)
C) Improve S3 prompt generation to include front/back + extracted answer_text.
D) S4 default model must be "nano banana pro" (env overridable).

ARTIFACTS:
- image_policy_manifest must reflect Q2 required=true.
- s3_image_spec must include Q1, Q2, and TABLE spec_kind.
- s4_image_manifest must include spec_kind + deterministic filenames.

FAILURE RULES:
- Any required spec generation failure => fail-fast: Q1, Q2, TABLE.

WORKFLOW / COMMAND RULES:
- Allowed: python -m compileall 3_Code/src
- Forbidden: destructive deletes, mass formatting.

DELIVERABLES:
1) Patch the markdown doc to match behavior.
2) Patch code end-to-end (S3 + S4).
3) Provide a smoke-test plan with expected outputs.
```

---

## 6. “Good constraints” checklist (what to explicitly write)

### 6.1 Schema immutability

If a schema/contract is frozen, say BOTH:
- “Do not modify the schema”
- “Do not require new fields”

Otherwise the Agent may keep the schema but accidentally make upstream changes mandatory.

### 6.2 Deterministic naming

If you rely on deterministic filenames/paths, write the exact format, e.g.:

- `IMG__{run_tag}__{group_id}__{entity_id}__{card_role}.png`

If you omit this, the Agent often “improves” naming and breaks downstream.

### 6.3 Fail-fast vs warn-only

Agents can’t guess which failures are acceptable. Specify:

- “Fail-fast if Q1 missing image_hint”  
- “Warn-only if Q2 optional fields missing”

---

## 7. Command execution rules (safety + reproducibility)

Include a short allow/deny list.

### Allowed
- `python -m compileall <path>`
- `python <script> --help`
- `pytest -q` (if repo uses it)
- read-only inspection: `ls`, `cat`, `grep`, `rg`

### Forbidden
- `rm -rf`, `git clean -fd`
- bulk formatting across repo
- migrations that rewrite historical generated data without explicit instruction

---

## 8. Checkpoints and rollback routine (practical)

A stable workflow:

1) Checkpoint A: before any changes  
2) Checkpoint B: after doc + S3 changes pass quick validation  
3) Checkpoint C: after S4 changes + smoke test passes

If something goes wrong:
- revert to checkpoint B to isolate S4 issues, etc.

---

## 9. Smoke tests: specify what “pass” looks like

Always request at least one **objective** check.

Examples:
- Manifest contains `Q2 image_required=true`
- Spec stream contains `spec_kind == "S1_TABLE_VISUAL"` exactly once per group
- Output images exist with deterministic filename patterns
- `compileall` succeeds (no syntax errors)

---

## 10. Common failure modes and how to pre-empt them

### Failure mode 1: Agent changes upstream schema “to make it easier”
**Pre-empt:** write “frozen schema” + “do not require new fields” as HARD constraints.

### Failure mode 2: Agent adds new filenames/dirs that break downstream
**Pre-empt:** explicitly specify deterministic formats + required output locations.

### Failure mode 3: Agent implements behavior but forgets to update docs
**Pre-empt:** put “Update BOTH doc and code” into constraints and deliverables.

### Failure mode 4: Partial implementation without a verification plan
**Pre-empt:** require a smoke test plan and ask for expected indicators.

---

## 11. Practical prompt-writing rules (high leverage)

1) Use **enumerated lists** (A/B/C) for required changes.  
2) Provide **exact mappings** (e.g., Q1/Q2/Q3 policy table).  
3) Separate **policy intent** from **implementation constraints**.  
4) Prefer “must”/“must not” language over vague wording.  
5) Include **acceptance criteria** that can be checked by reading artifacts.

---

## 12. One-page quick-start prompt (copy/paste)

```text
Objective: <end-state>

Context:
@<files>

HARD CONSTRAINTS:
1) <frozen schema / deterministic outputs / no destructive commands>

CHANGES REQUIRED:
A) <mapping>
B) <artifact updates>
C) <doc updates>
D) <tests>

DELIVERABLES:
1) Code patches
2) Doc patch
3) Smoke test plan + expected pass indicators
```

---

### Notes
- This guide is meant to be pasted into your repository as a reusable policy document.
- If you maintain a “Prompt Bundle” registry, you can store the templates here and reference them from your runbook.

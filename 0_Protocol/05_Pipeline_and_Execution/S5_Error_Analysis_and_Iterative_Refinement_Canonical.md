# S5 Error Analysis & Iterative Refinement (Canonical)

**Status**: Canonical (process doc)  
**Scope**: How we use S5 validation outputs to improve schemas/prompts *without contaminating primary endpoints*  
**Key principle**: Improvements are performed **offline** with explicit versioning and dataset separation.

---

### 1) Goal

Use S5 validation artifacts to produce:
- a **repeatable report** (human-readable) of failure modes,
- a **structured change log** of schema/prompt updates,
- and a **paper-ready description** of how prompt/schema improvements were performed.

---

### 2) What counts as “multi-agent” vs “refinement process”

This doc covers an **offline refinement loop**:
- Run pipeline → run S5 → summarize errors → update prompts/schemas → re-run on a development slice → freeze.

This is typically described as:
- **“error analysis–driven prompt refinement”**
- **“iterative prompt development”**
- **“schema hardening based on validation outputs”**

It is distinct from a runtime multi-agent closed loop (see Option C plan).

---

### 3) Inputs and outputs

#### 3.1 Inputs
- `2_Data/metadata/generated/<RUN_TAG>/s5_validation__arm{arm}.jsonl`
- (Optional) `logs/llm_metrics.jsonl` for latency/tokens/cost proxy counters

#### 3.2 Outputs (recommended)
- `2_Data/metadata/generated/<RUN_TAG>/reports/s5_report__arm{arm}.md`
  - Per-group summary
  - Issue taxonomy counts
  - Blocking items list with evidence excerpts (when available)
  - Recommended changes for prompts/schemas

---

### 4) Procedure (repeatable)

#### 4.1 Generate report (automation)
Use the canonical script:
- `3_Code/src/tools/s5/s5_report.py`

Run example:

```bash
python3 -m tools.s5.s5_report \
  --base_dir . \
  --run_tag <RUN_TAG> \
  --arm A
```

**Rule**: when multiple S5 lines exist per `group_id` (re-runs), analyses MUST dedupe by latest `validation_timestamp` unless explicitly debugging.

#### 4.2 Classify failures (taxonomy)
Use S5 `issues[].type` as the primary taxonomy.
Add sub-tags in the report when useful (e.g., “MCQ option missing” as a structural sub-category).

**Update (recommended, backward-compatible)**:
- Prefer stable `issues[].issue_code` (when present) for cross-run comparability.
- When present, use `issues[].recommended_fix_target` + `issues[].prompt_patch_hint` to directly generate a “patch backlog” section in the report.

#### 4.3 Apply improvements (prompt/schema)
Allowed improvement types:
- **Prompt improvements**: add explicit constraints, clarify output schema, add checklists.
- **Schema improvements**: add fields that improve traceability (e.g., `run_tag`, inputs provenance), make optional fields explicit, and add enums for common issue types when stable.
- **Determinism controls**: document fixed temperatures / thinking / RAG toggles by step.

**Anki MCQ convention note**:
- For MCQ cards, options are stored in structured fields (`options[]`, `correct_index`) and may not be duplicated in `front`.
- S5 validators should evaluate MCQ integrity using these structured fields to avoid false “options missing in front” flags.

**Versioning requirement**:
- Any prompt change MUST bump prompt version (e.g., `S5_USER_CARD__v2.md`) and update prompt registry.
- Any schema change MUST bump schema version or be introduced as clearly optional fields with backward compatibility.

#### 4.4 Freeze before evaluation
For a formal study run:
- Prompt/schema versions must be **frozen** before collecting primary endpoints.
- If changes occur after seeing test outputs, they MUST be treated as a new study iteration or clearly labeled as post-hoc.

---

### 5) Estimand protection (how to avoid contaminating endpoints)

If the study’s primary endpoint compares arms:
- Primary endpoint must use **Pre-S5 human ratings** (Option B).

If S5 outputs are used to improve prompts:
- This is **development work** and should occur on:
  - a designated development slice (e.g., S0), or
  - a separate run clearly labeled “prompt iteration”.

Paper reporting should explicitly state:
- what data split was used (development vs test),
- what was changed (prompt/schema versions),
- and when the freeze occurred.

---

### 6) Paper-ready language (recommended)

Suggested phrasing:
- “We performed structured error analysis on verifier outputs (S5) and iteratively refined prompts and output schemas on a development subset. All prompt versions, parameters, and run artifacts were logged to support MI-CLEAR-LLM reproducibility.”

When describing S5:
- “S5 is a post-generation LLM-based validation step that flags issues and provides evidence; it does not enforce hard failures.”

---

### 7) MI-CLEAR-LLM alignment (minimum reporting items)

For each prompt/schema iteration, keep:
- model name/version, access mode (API), run date/time,
- system+user prompts (full text) + hashes,
- decoding params (temperature, max tokens) and flags (thinking/RAG),
- dataset identifier (run_tag) and split role (dev/test),
- artifacts: `s5_validation__*.jsonl`, `llm_metrics.jsonl`, and generated reports.



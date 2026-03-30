# MeducAI S5 Multi-Agent Repair Plan (Option C, Canonical)

**Status**: Draft (Protocol-only; no implementation implied)  
**Scope**: Step05 (S5 Validation) → *One-shot Repair Loop* for S1 tables and S2 cards  
**Core constraint**: **Original artifacts remain immutable**. Repairs are written to **separate outputs**.  

---

### 0) Terminology (internal vs paper-facing)

- **Internal (repo/code/protocol shorthand)**: “multi-agent”, “Option C”
- **Paper-facing (recommended primary wording)**:
  - “**role-specialized agentic repair pipeline (verifier–planner–regenerator)**”
  - “**agent-orchestrated one-shot repair cascade**”
- **Rationale**: “multi-agent system” can imply autonomy/negotiation. Our design is role-specialized and artifact-mediated, with one-shot stopping.
- Canonical positioning: `Multiagent_Terminology_and_Research_Rationale_Canonical.md`

### 1) What this is (and is not)

#### 1.1 What Option C is
- **A closed-loop “critic → generator” workflow** that uses S5 validation outputs as structured feedback to trigger **one additional regeneration pass**:
  - S5 (critic/verifier) produces issues + evidence.
  - S5R (repair planner) converts those issues into deterministic **repair instructions**.
  - S1R/S2R (generator) re-runs generation **once** using S5R instructions.
  - S5’ re-validates repaired artifacts for triage.

This can be described in a paper as:
- **“LLM-based verification with one-step self-refinement (critic–generator loop)”**
- **“Verifier-assisted regeneration (one iteration), with immutable originals”**

#### 1.2 What Option C is not
- **Not auto-correction in-place** (no overwriting `stage1_struct__*.jsonl` / `s2_results__*.jsonl`)
- **Not fail-fast** (pipeline does not abort if S5 flags blocking)
- **Not multi-iteration optimization** (exactly **one** repair iteration)

---

### 2) Why we do it (research framing)

Option C adds a **tool-effect** workflow layer:
- Primary clinical/educational endpoints for arm comparisons remain **Pre-S5 human ratings** (see Option B plan).
- Option C can be reported as:
  - **Secondary/exploratory**: “Does verifier-guided one-step regeneration reduce blocking errors and/or editing time?”
  - **Engineering outcome**: throughput/cost deltas for “baseline” vs “repaired” artifacts.

**Important**: If Option C is used during a study, it must be treated as a **separate intervention condition** (or a separate pipeline run) to avoid contaminating the primary estimand.

---

### 3) System definition (agents + responsibilities)

#### 3.1 Agent roles
- **Agent A — S5 Validator (Critic/Verifier)**  
  Inputs: S1 table artifact, S2 cards artifact (+ RAG enabled)  
  Outputs: structured issues with optional evidence and suggested fixes (no hard fails)

- **Agent B — S5R Repair Planner (Instruction Synthesizer)**  
  Inputs: S5 validation result (S1 + S2 issues), plus original artifact excerpts needed for patching  
  Outputs: a **repair plan** that is executable by a generator (clear instructions, minimal scope)

- **Agent C — Generator (S1R / S2R Regeneration)**  
  Inputs: original prompts + original inputs + S5R plan  
  Outputs: repaired artifacts, written as new files (immutable lineage)

- **Agent D — S5’ Post-Repair Validator**  
  Inputs: repaired artifacts  
  Outputs: S5 validation result for repaired artifacts

#### 3.2 “Multi-agent” claim boundary
This is reasonably described as **multi-agent** if:
- the roles are **explicitly separated** (critic vs generator vs planner), and
- the system operates as a **closed loop** (S5 → S5R → regeneration → S5’).

If the repair step is only manual (human editing) then it is better described as **“post-hoc LLM validation with human-in-the-loop QA”** rather than multi-agent.

**Paper-facing boundary**:
- Prefer “agentic repair pipeline” as the primary term.
- Use “multi-agent” as a secondary/internal label, explicitly defined as role-specialized + artifact-mediated + one-shot + immutable originals.

---

### 4) Workflow (one-shot loop)

#### 4.1 Baseline run (unchanged)
- S1 → S2 → S3 → S4 → **S5** → S6

#### 4.2 Option C loop (new, optional branch)
After **S5** completes (baseline artifacts):
1. **S5R plan generation**
   - Produce repair instructions for:
     - **S1 table** (structure/terminology/accuracy corrections)
     - **S2 cards** (format issues like missing options, factual errors, ambiguity)
     - **S4 images** (positive regen for threshold-failing images) ✅ **구현 완료 (2026-01-05)**
2. **S1R regeneration (once)**
   - Regenerate S1 table for the affected group(s) using original S1 inputs + S5R instructions.
3. **S2R regeneration (once)**
   - Regenerate S2 cards for affected entities/cards using original S2 inputs + S5R instructions.
4. **S4R image regeneration (Positive Regen)** ✅ **구현 완료**
   - Extract `prompt_patch_hint` from S5 validation results
   - Merge with S3 original `prompt_en` (delta injection)
   - Re-run S4 with `--image_type regen` → `images_regen/IMG__*_regen.jpg`
   - Separate manifest: `s4_image_manifest__armX__regen.jsonl`
5. **S5' validation**
   - Validate repaired S1/S2 artifacts using the same S5 models/settings.
6. **Export gating (S6 selection; safe fallback)**
   - Repaired artifacts are treated as a **promotion** candidate, not a replacement.
   - Recommended default gate (safe-by-default):
     - Human gate: `multiagent_repair_acceptance == ACCEPT` (see `Multiagent_Evaluation_Workflow_Design.md`)
     - Safety gate: S5’ shows no blocking errors (or below a pre-specified threshold)
   - If gating fails (e.g., QA hold/reject, or post-repair still blocking), export **baseline** artifacts (no fail-fast; no abort).

**Termination**: exactly **one** repair iteration. No loops beyond that.

---

### 5) Artifact strategy (immutability + lineage)

#### 5.1 Principle: never overwrite
- Baseline artifacts are SSOT for the arm run (as generated in S1/S2).
- Repair artifacts are **additive** and must include traceability fields pointing back to the baseline.

#### 5.2 Suggested file outputs (canonical naming)
Within `2_Data/metadata/generated/{run_tag}/`:

- **Baseline (existing)**
  - `stage1_struct__arm{arm}.jsonl`
  - `s2_results__s1arm{S1arm}__s2arm{arm}.jsonl`
  - `s5_validation__arm{arm}.jsonl`

- **Repair plan (new)**
  - `s5_repair_plan__arm{arm}.jsonl`

- **Repaired generation outputs (new)**
  - `stage1_struct__arm{arm}__repaired.jsonl`
  - `s2_results__s1arm{S1arm}__s2arm{arm}__repaired.jsonl`

- **Post-repair validation (new)**
  - `s5_validation__arm{arm}__postrepair.jsonl`

#### 5.2.1 Image regeneration outputs (image-only; separate from baseline) ✅ **구현 완료 (2026-01-05)**

**Positive Regen 아키텍처 (Option C Image Regeneration):**

Baseline image sets MUST remain immutable:

- **Baseline images (do not modify)**: `images/`, `images_anki/`, `images_realistic/` (if present)
- **Regen images (new output only)**: `images_regen/` (generated with `_regen` filename suffix)
- **Same RUN_TAG**: regen 이미지는 baseline과 동일한 RUN_TAG 사용 (폴더/suffix로 구분)
- **Separate manifest**: `s4_image_manifest__armX__regen.jsonl` (baseline manifest 보존)
- **S3 spec**: `s3_image_spec__armX__regen_positive_v{N}.jsonl` (원본 spec 보존)

**Workflow:**
1. S5 validation → `prompt_patch_hint` 추출 (threshold < 80점)
2. S3 원본 `prompt_en` + `prompt_patch_hint` delta 병합
3. S4 재호출 (`--image_type regen`) → `images_regen/IMG__*_regen.jpg`
4. Manifest 분리 저장 (baseline 덮어쓰기 방지)

**참조 문서**: `S5_Positive_Regen_Procedure.md` (운영 가이드)

This separation is required to avoid contaminating baseline exports and to preserve lineage for QA/audits.

##### Operational snapshot (required before new regen run)

Before generating a new `images_regen/` for an existing `{run_tag}`, snapshot any prior regen output by renaming the folder:

```bash
# Example (POSIX shell)
RUN_TAG="FINAL_DISTRIBUTION"
TS="$(date +%Y%m%d_%H%M%S)"
if [ -d "2_Data/metadata/generated/${RUN_TAG}/images_regen" ]; then
  mv "2_Data/metadata/generated/${RUN_TAG}/images_regen" \
     "2_Data/metadata/generated/${RUN_TAG}/images_regen__backup_${TS}"
fi
```

#### 5.3 Required lineage fields (minimum)
Every repair-related record MUST include:
- `run_tag`, `arm`, `group_id`
- `baseline_snapshot_id` (or hashes of baseline S1/S2 records)
- `s5_snapshot_id` (the specific S5 result used to plan the repair)
- `repair_iteration`: fixed to `1`
- `repaired_snapshot_id` (new hash/version for repaired output)

---

### 6) S5R Repair Plan schema (high-level)

`s5_repair_plan__arm{arm}.jsonl` (one record per `group_id`):
- **Identity**
  - `schema_version`, `run_tag`, `arm`, `group_id`, `created_at`
- **Inputs used**
  - `s5_snapshot_id`
  - `baseline_s1_hash`, `baseline_s2_hash` (or per-entity hashes)
- **S1 repair instructions**
  - `s1_actions[]`: each item includes:
    - `action_type` (rename_entity / fix_row / clarify_term / remove_ambiguous_claim / etc.)
    - `target` (row_index, entity_name, column_name if applicable)
    - `instruction` (1–3 lines; unambiguous)
    - `evidence[]` (optional; copied/linked from S5 rag_evidence when relevant)
- **S2 repair instructions**
  - `s2_actions[]`: each item includes:
    - `target_card_id` (or derived id), `card_role`, `entity_id`, `entity_name`
    - `action_type` (add_missing_options / fix_correct_index / fix_factual / improve_clarity / etc.)
    - `instruction`
    - `evidence[]` (required if the action is based on “blocking/factual” claims)
- **Guardrails**
  - `no_new_content_scope` (boolean; true)
  - `max_iteration` (=1)

---

### 7) MI-CLEAR-LLM compliance requirements for Option C

For each agent call (S5, S5R, S1R, S2R, S5’), log:
- **Model identification**: provider, model name/version (snapshot if available)
- **Prompt disclosure**: prompt IDs + prompt hashes (system + user templates)
- **Parameters**: temperature, max output tokens, thinking/RAG flags
- **Timing/counters**: start/end timestamps, latency, token usage when available
- **RAG logging**: query count, sources count, plus evidence excerpts when claiming blocking/factual errors
- **Failure logging**: retries, parse failures, truncation indicators

**Note**: Because Option C involves iterative refinement, it must explicitly report:
- `repair_iteration=1`, and
- what artifacts were used as inputs to the repair planner and generator.

---

### 8) Evaluation / endpoints (how to write it in the paper)

#### 8.1 Primary endpoint (arm comparison)
- Must use **pre-repair / baseline-only human ratings** only (per Option B, and the multiagent 3-pass workflow).
- Operationally:
  - Pre-Multiagent evaluation MUST be blinded (no S5, no repaired artifacts).
  - Pre-Multiagent submission MUST be immutable/locked before any reveal.
  - Canonical workflow reference: `Multiagent_Evaluation_Workflow_Design.md` (3-pass).
 - FINAL gate assurance boundary:
   - FINAL gate error rate (%) claims must be anchored on the attending audit and attending adjudication workflow, using the binary `major_error` definition in `QA_Metric_Definitions.md` and `FINAL_QA_Form_Design.md`.
   - Multi-agent outputs and post-repair self-checks must not be used to define or revise the FINAL gate primary endpoint labels.

#### 8.2 Secondary endpoints (tool effect)
Recommended:
- Change in blocking rate after repair: \( BER_{postrepair} - BER_{baseline} \)
- Change in quality after repair (if rated): \( Q_{postrepair} - Q_{baseline} \)
- Editing time reduction (human-in-the-loop): time saved when evaluators see repaired artifacts (must be clearly separated from primary estimand)

Mandatory reporting (to avoid cherry-picking):
- **Degradation rate**: fraction of items where human judges the repaired artifact is worse than baseline.
- **Acceptance rate**: fraction of repaired artifacts marked acceptable for downstream use.
- **Technical accuracy alignment**: human collection SHOULD include `technical_accuracy` on the 0.0 / 0.5 / 1.0 scale so S5 vs human agreement is measurable (see `S5_vs_FINAL_QA_Alignment_Analysis.md`).

Verifier reliability (recommended):
- Agreement rates between S5 and human on blocking / technical accuracy / educational quality.
- False positive / false negative characterization where feasible.

Validity threats (and how we measure/mitigate):
- Anchoring risk (same rater sees baseline then repaired): keep primary endpoints baseline-only, and report degradation + acceptance as mandatory outcomes.
- S5 authority bias: require explicit agreement/disagreement fields (`s5_*_agreement`) and treat them as measurable covariates.
- Optional sensitivity: small subset between-rater comparison (baseline-only vs repaired-only) for robustness.

Implementation references (canonical docs):
- 3-pass evaluation workflow: `Multiagent_Evaluation_Workflow_Design.md`
- Timing schema and comparison: `S5_Time_Measurement_and_Comparison_Plan.md`
- Human vs S5 metric alignment (Technical Accuracy): `S5_vs_FINAL_QA_Alignment_Analysis.md`

#### 8.3 Reporting language
Suggested phrasing:
- “We evaluated a verifier-assisted one-step regeneration loop (critic–planner–generator) that preserves immutable baseline artifacts and produces separate repaired outputs for downstream QA.”

---

### 9) Guardrails & non-goals

- **No overwrite** of baseline artifacts.
- **No hard-fail** pipeline abort (triage only).
- **One iteration only** (no open-ended self-improvement loop).
- **No confounding arm comparison**:
  - If repairs are used, they must be either:
    - applied uniformly across arms as a separate condition, or
    - treated as a secondary/tool-effect analysis, not the primary arm comparison.
- **No hiding degradation**:
  - Report both improvement and degradation rates when presenting tool effect outcomes.
- **Evidence discipline**:
  - If S5/S5R asserts “blocking/factual error”, it should include evidence (RAG or cited table context excerpt) in logs/outputs.

---

### 10) Decision points (explicit)

- **DP1**: Are repaired artifacts used for export (S6) in the main study, or only for exploratory QA?
  - Recommended default: baseline is exported unless repaired is explicitly promoted via the export gate (QA accept + postrepair non-blocking).
- **DP2**: Do we run Option C on all groups, or only those with S5 `blocking_error=true` / low quality?
- **DP3**: Do we allow the generator to introduce new entities/claims not present in baseline? (Recommended: **No**)

#### 10.1 Decision points for **image-inclusive** multi-agent extension (optional)

If Option C is extended to include image evaluation/repair signals (S4 artifacts), decide:
- **DP4 (Input coupling)**: Should the critic evaluate **card+image jointly** (recommended for “support/answerability”) and **image-only** separately (recommended for “policy/legibility”)?
- **DP5 (What can be repaired)**: Are we allowed to regenerate **images** (S4) as part of the one-shot repair, or only regenerate **text** (S1/S2) while keeping images fixed?
- **DP6 (Attribution)**: When a blocking issue is flagged, do we attribute it to **S2 text**, **S4 image**, or **interaction** (card requires image to answer)?
- **DP7 (Evidence logging)**: If blocking depends on image content, what evidence is stored for audit (e.g., image filename + short structured description + policy flags), given that raw images may not be embedded in logs?

##### Qualitative note (paper-facing; limitation-level)

In internal pilot iterations, we observed that **negative prompt–style regen instructions** (heavy “do not / avoid / exclude” constraints) can degrade medical image realism and introduce unintended artifacts (over-constrained, “unnatural” composites). For this reason, regen instruction synthesis SHOULD prefer **positive, additive, and specific** requirements (what to include/strengthen) over negative prohibitions.

- This is a **qualitative observation** intended for Discussion/Limitations framing.
- This note does **not** modify any binding decision criteria (see `S5_Decision_Definition_Canonical.md`).

#### 10.2 PR8 — QA300 Paired Image Experiment (DIAGRAM vs REALISTIC) — **Experiment-only**

This is an **execution + reporting convention** for a paired experiment that generates **the same “specialist allocation” card set (~300 cards)** twice:
- **DIAGRAM**: distribution-eligible baseline (this is what S6 export may use)
- **REALISTIC**: **experiment-only** paired variant (must never be exported)

**Non-negotiables**
- **Distribution policy**: FINAL distribution exports (Anki/PDF) must remain **DIAGRAM-only**.
- **Paired design**: DIAGRAM and REALISTIC must be **1:1 matched** by stable identifiers (no “roughly similar” samples).
- **Immutability**: Do not overwrite outputs inside a RUN_TAG. Use separate RUN_TAGs for DIAGRAM vs REALISTIC.

**Pairing key (canonical)**
- **Card identity**: `card_uid = "{group_id}::{card_id}"` (stable across steps and used by QA tooling).
- **Image identity**: deterministic filenames from S4: `IMG__{run_tag}__{group_id}__{entity_id}__{card_role}.jpg`.

**Sample definition (how we get ~300 cards)**
- Use the same group set used for specialist allocation (typically **11 groups**) via:
  - `temp_selected_groups.txt` (one `group_key` per line; comments with `#` allowed)
- The resulting S2 output across these groups is treated as the “QA300” sample for this paired experiment.

**RUN_TAG convention (required)**
- `RUN_TAG_DIAGRAM`: `FINAL_QA300PAIR_DIAGRAM_YYYYMMDD_HHMMSS`
- `RUN_TAG_REALISTIC`: `FINAL_QA300PAIR_REALISTIC_YYYYMMDD_HHMMSS`
  - **Important**: include substring **`REALISTIC`** so S3 auto-detects REALISTIC profile by default.

**Execution convention (required)**
1) **Generate the QA300 sample once** (S1+S2) under `RUN_TAG_DIAGRAM`:

```bash
ONLY_GROUP_KEYS_FILE="temp_selected_groups.txt"
RUN_TAG_DIAGRAM="FINAL_QA300PAIR_DIAGRAM_$(date +%Y%m%d_%H%M%S)"

python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_DIAGRAM" \
  --arm G \
  --mode FINAL \
  --stage both \
  --only_group_keys_file "$ONLY_GROUP_KEYS_FILE"
```

2) **Clone S1/S2 artifacts into the REALISTIC run directory** (to guarantee identical card sets):
   - Copy (at minimum):
     - `2_Data/metadata/generated/$RUN_TAG_DIAGRAM/stage1_struct__armG.jsonl`
     - `2_Data/metadata/generated/$RUN_TAG_DIAGRAM/s2_results__s1armG__s2armG.jsonl`
   - Then create `RUN_TAG_REALISTIC` and place those two files under its directory before running S3.

Minimal copy commands (example):

```bash
RUN_TAG_REALISTIC="FINAL_QA300PAIR_REALISTIC_$(date +%Y%m%d_%H%M%S)"
mkdir -p "2_Data/metadata/generated/$RUN_TAG_REALISTIC"

cp "2_Data/metadata/generated/$RUN_TAG_DIAGRAM/stage1_struct__armG.jsonl" \
   "2_Data/metadata/generated/$RUN_TAG_REALISTIC/stage1_struct__armG.jsonl"

cp "2_Data/metadata/generated/$RUN_TAG_DIAGRAM/s2_results__s1armG__s2armG.jsonl" \
   "2_Data/metadata/generated/$RUN_TAG_REALISTIC/s2_results__s1armG__s2armG.jsonl"
```

Sanity checks (required):

```bash
# 1) identical upstream artifacts (strongest guarantee)
shasum "2_Data/metadata/generated/$RUN_TAG_DIAGRAM/stage1_struct__armG.jsonl" \
       "2_Data/metadata/generated/$RUN_TAG_REALISTIC/stage1_struct__armG.jsonl"

shasum "2_Data/metadata/generated/$RUN_TAG_DIAGRAM/s2_results__s1armG__s2armG.jsonl" \
       "2_Data/metadata/generated/$RUN_TAG_REALISTIC/s2_results__s1armG__s2armG.jsonl"
```

3) Run **S3 → S4 → S5** for **each** run_tag:
- DIAGRAM:

```bash
python3 3_Code/src/03_s3_policy_resolver.py --base_dir . --run_tag "$RUN_TAG_DIAGRAM" --arm G
python3 3_Code/src/04_s4_image_generator.py  --base_dir . --run_tag "$RUN_TAG_DIAGRAM" --arm G
python3 3_Code/src/05_s5_validator.py        --base_dir . --run_tag "$RUN_TAG_DIAGRAM" --arm G
```

- REALISTIC (auto-detects from run_tag; do **not** set global env overrides when running paired experiments):

```bash
RUN_TAG_REALISTIC="FINAL_QA300PAIR_REALISTIC_$(date +%Y%m%d_%H%M%S)"

python3 3_Code/src/03_s3_policy_resolver.py --base_dir . --run_tag "$RUN_TAG_REALISTIC" --arm G
python3 3_Code/src/04_s4_image_generator.py  --base_dir . --run_tag "$RUN_TAG_REALISTIC" --arm G
python3 3_Code/src/05_s5_validator.py        --base_dir . --run_tag "$RUN_TAG_REALISTIC" --arm G
```

**Per-run artifacts to keep (required)**
Within each `2_Data/metadata/generated/{run_tag}/`:
- `s3_image_spec__armG.jsonl` (contains `exam_prompt_profile` + prompt keys)
- `s4_image_manifest__armG.jsonl` and `images/IMG__*.jpg`
- `s5_validation__armG.jsonl`
- Optional human-readable report:
  - `reports/s5_report__armG.md` (generate via `3_Code/src/tools/s5/s5_report.py`)
- Optional image completeness audit artifacts (if generated by the run tooling):
  - `missing_images__armG.json`

**Comparison report convention (required)**
- Use the canonical multimodal comparator to generate a paired DIAGRAM vs REALISTIC report:

```bash
python3 3_Code/src/05_s5_compare_mm.py \
  --base_dir . \
  --arm G \
  --before_run_tags "$RUN_TAG_DIAGRAM" \
  --after_run_tags "$RUN_TAG_REALISTIC"
```

- Output directory (auto-created):
  - `2_Data/metadata/generated/COMPARE__<before_tag0>__VS__<after_tag0>/`
- Canonical report files:
  - `summary__mm.md` (primary; attach this in experiment logs)
  - `paired_long__mm.csv` (card-level long form for audits)
  - `group_level__mm.csv` (group-level aggregates)

**Interpretation boundary (required)**
- This PR8 paired experiment is a **quality/engineering experiment** for image prompt profiles.
- It must be reported as **experiment-only** and must not be mixed into FINAL distribution exports (S6).

---

### 11) Operational checklist (doc worklist)

Minimum set of documents/requirements to implement and evaluate Option C safely:

- **Implementation guidance**: `0_Protocol/05_Pipeline_and_Execution/archived/2025-12/Multiagent_Development_Handoff.md`
- **Evaluation workflow (3-pass)**: `Multiagent_Evaluation_Workflow_Design.md`
  - Must include: `technical_accuracy` (0.0/0.5/1.0), `s5_*_agreement`, `multiagent_repair_acceptance`, `quality_change`
  - Pre-Multiagent pass must be blinded and immutable before reveal
- **Timing schema and comparison**: `S5_Time_Measurement_and_Comparison_Plan.md`
  - Must log start/end/duration for S5, S5R, regeneration, and S5’
- **Metric alignment**: `S5_vs_FINAL_QA_Alignment_Analysis.md`
- **Export gate**:
  - Default: promote repaired only when `multiagent_repair_acceptance == ACCEPT` and S5’ is non-blocking
  - Otherwise: baseline fallback (no abort)



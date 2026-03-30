# S2 Cardset & Image Placement Policy (Canonical, S3 ImageSpec Handoff)

**Status**: Canonical  
**Version**: 1.5  
**Frozen**: No  
**Supersedes**: 1.4  
**Change Log**: 
- v1.4 - Updated Q1 image placement from FRONT to BACK (2-card policy: both Q1 and Q2 use back-only images)
- v1.5 - Clarified that the current pipeline is **2-card only (Q1/Q2)**. **Q3 is removed**; any Q3 output is invalid and must fail validation/resolution.  

---

## 1. Purpose

Define a **deterministic, board-exam–aligned** policy that:

1) Generates **exactly 2 cards per Entity** (Q1, Q2 only; 2-card policy).  
2) Fixes **image placement (BACK)** by card role (**Q1/Q2**) as a question-design constraint.  
3) Adds a **deterministic S3 "ImageSpec compiler"** that converts **S1 visual keywords + S2 image hints** into **standardized image prompts/specs** for S4 **without using an LLM**.  
4) Protects **S0 arm comparability and reproducibility** by preventing "LLM makes policy" drift.

This policy applies to all pipeline runs: card roles are fixed to **Q1/Q2 only** and placement is **back-only**.

---

## 2. Scope

### 2.1 In scope
- Per-Entity **2-card** structure (Q1/Q2) and fixed **BASIC vs MCQ** mapping.
- Placement-aware item-writing rules (how stems/options/explanations must change with FRONT/BACK/NONE).
- Deterministic handling of **image hint → image spec** handoff (S2 → S3 → S4).

### 2.2 Out of scope
- Actual image generation/rendering (S4 runtime and model-specific controls).
- Note-type HTML/templates and export mechanics (Anki export layer).
- Table infographic pipeline (S1 master table → "one table image per group"): **separate policy**.

---

## 3. Definitions

- **Entity**: atomic concept unit selected for S2 generation (identified by `entity_id`).  
- **Card role**: fixed per entity: `Q1`, `Q2`, `Q3`.  
- **Image placement**: where the deck places an image:
  - `FRONT` = image-as-stem
  - `BACK` = image-as-explanation
  - `NONE` = no image in the note (and no image references in text)

### 3.1 Image hint (S2 → S3)
A **minimal, structured** "request" emitted by S2 for image-enabled cards (Q1/Q2), used by S3 to compile the final prompt/spec.

### 3.2 Image spec (S3 → S4)
A **deterministic, standardized** record that S4 can consume directly to generate an asset (or queue one), including modality and keywords, plus a pre-rendered prompt text (template-filled).

---

## 4. Design Principles (Non-negotiable)

1) **Policy is not decided by the LLM.**  
   LLM stages may generate *content*, but **policy outcomes** (counts, placement, requiredness) are **deterministic**.

2) **Arm comparability is protected.**  
   All arms follow the same cardset structure and resolution rules. Variance should affect quality, not policy decisions.

3) **S2 remains text-first.**  
   S2 produces card text. Images are generated later, and placement is enforced via metadata/manifests.

4) **S3 is a compiler, not a generator.**  
   S3 **MUST NOT** call an LLM. S3 only applies rules/templates to produce `image_spec` for S4.

5) **No Cloze for S0/QA distribution.**  
   Cloze is excluded to maximize board-exam face validity and reduce format variance.

---

## 5. Responsibility Boundaries by Stage

### 5.1 S1 (Structure)
- Produces stable identifiers (`group_id`, `entity_id`, `entity_name`) and the master table.
- Provides *visual context* for image compilation:
  - `visual_type_category`
  - per-entity row text such as "영상 소견 키워드", "모달리티별 핵심 소견", "시험포인트" (as available in the canonical table).

### 5.2 S2 (Item generation + image hints)
- Generates **exactly 2 cards per entity** (Q1–Q2), **text only**.
- Emits **image hints** for **both Q1 and Q2** (structured metadata) but does not generate image prompts.
- Must not change placement rules; at most it provides **hints**.

### 5.3 S3 (Resolver + ImageSpec compiler)
- Deterministically resolves placement (`Q1→BACK`, `Q2→BACK`) (2-card policy: both Q1 and Q2 use back-only images).
- Enforces constraints (e.g., `NONE` means no image references anywhere).
- Compiles **S1 visual context + S2 image hints** into a standardized `image_spec` for S4.
- Optionally performs **asset existence checks** before export (operational gate).

### 5.4 S4 (Image generation)
- Generates assets **only** for cards that the resolved policy marks as image-enabled.
- Must not reclassify placement.
- Should consume S3 `image_spec` directly (no interpretation drift).

### 5.5 Export (Anki)
- Applies note-type/templates based on resolved placement metadata.
- Attaches generated image assets to FRONT or BACK per placement.

---

## 6. Core Cardset Structure (Role-Fixed)

For each **Entity**, generate exactly:

- **Q1**: `BASIC` + `IMAGE_ON_BACK` (pattern recognition / diagnosis / sign recall; image reinforces explanation)  
- **Q2**: `MCQ` (5 options) + `IMAGE_ON_BACK` (text-first; image reinforces explanation)  

**참고(업데이트)**: 현재 파이프라인은 **Q1/Q2만 유지**합니다. Q3는 legacy 문서/실험에서만 존재했으며, 신규 실행에서는 사용하지 않습니다.

---

## 7. Deterministic Placement Resolution

Placement is fixed by role (and only Q1/Q2 are valid roles):

- Q1 → `BACK` (2-card policy: back-only educational infographic)
- Q2 → `BACK` (2-card policy: back-only educational infographic)

### 7.1 Asset requiredness (operational minimum)
- **Q1 is image-required** at distribution time.
  - If Q1 asset is missing → **FAIL-FAST before distribution**
- **Q2 is image-required** at distribution time (Q2 generates its own image, independent of Q1).
  - Q2 does NOT reuse Q1 image; it generates a separate image asset.
  - If Q2 asset is missing → **FAIL-FAST before distribution**
 

---

## 8. Image Hint → ImageSpec Handoff (S2 → S3 → S4)

### 8.1 Policy intent
- S2 should not attempt to "design the exact image prompt."
- Instead, S2 emits **minimal, exam-aligned hints** (modality + a few key visual cues).
- S3 compiles these into standardized prompts/specs using deterministic templates.

### 8.2 Required: Image hint object (S2 output, per card)
S2 MUST output `image_hint` **only** when `image_placement_final in {FRONT, BACK}`.
(For `NONE`, `image_hint` MUST be absent or null.)

**Minimum recommended schema (per card):**
```json
{
  "image_hint": {
    "modality_preferred": "XR|CT|MRI|US|Angio|NM|PETCT|Other",
    "anatomy_region": "free text (short)",
    "key_findings_keywords": ["keyword1", "keyword2", "keyword3"],
    "view_or_sequence": "optional (e.g., axial T2, PA view)",
    "exam_focus": "optional (diagnosis|sign|pattern|differential)"
  }
}
```

**Hard rules:**
- Q1: `image_hint` is **required** (Q1 has back-only infographic; S3 must be able to compile a spec).
- Q2: `image_hint` is **required** (Q2 has its own back-only infographic; no reuse from Q1).

### 8.3 Deterministic S3 compilation rules (no LLM)
S3 MUST compile `image_spec` with the following precedence:

1) Start from **S2 image_hint** fields (if present).  
2) Fill missing pieces from **S1 master table row context** for the entity:
   - "영상 소견 키워드" → `key_findings_keywords` augmentation
   - "모달리티별 핵심 소견" → `modality_preferred` and/or `view_or_sequence` inference
   - "시험포인트" → optional `exam_focus` clarification
3) Apply a deterministic **template** based on:
   - card role (`Q1` vs `Q2`)
   - modality (`XR/CT/MRI/US/...`)
   - (optional) `visual_type_category` (used only as a template selector; no semantics inference)

**No free-form reasoning is allowed in S3.** If required fields cannot be resolved deterministically, S3 must **hard fail** for Q1.

### 8.4 ImageSpec schema (S3 output, per card)
S3 outputs one line per (group_id, entity_id, card_role) for **both Q1 and Q2** (each card role gets its own image spec).

```json
{
  "schema_version": "S3_IMAGE_SPEC_v1.0",
  "run_tag": "...",
  "group_id": "...",
  "entity_id": "...",
  "entity_name": "...",
  "card_role": "Q1|Q2",
  "image_placement_final": "FRONT|BACK",
  "image_asset_required": true,
  "modality": "XR|CT|MRI|US|Angio|NM|PETCT|Other",
  "anatomy_region": "...",
  "key_findings_keywords": ["..."],
  "view_or_sequence": "optional",
  "template_id": "RAD_IMAGE_v1__<MODALITY>__<ROLE>",
  "prompt_en": "Rendered prompt string for S4 (deterministic template fill)"
}
```

Recommended mapping:
- `image_asset_required = true` for both Q1 and Q2.

### 8.5 Prompt template policy (S3)
S3 may render `prompt_en` using deterministic templates for Q1 and Q2. Example (normative structure; wording can be tuned):

- **Q1 (BACK; image-as-explanation):**
  - "Create a realistic {modality} radiology image of {anatomy_region} that demonstrates: {key_findings_keywords}. No labels. Board-exam style."

- **Q2 (BACK; image-as-explanation):**
  - Q2는 Q1과 독립적인 이미지를 생성하므로 별도 프롬프트 생성 필요.

S3 MUST NOT add new medical content not present in S1/S2 sources; it may only reorganize/standardize.

---

## 9. Card-Type Resolution (BASIC vs MCQ)

Card types are fixed per role and do not vary by arm:

- Q1: `BASIC`
- Q2: `MCQ` (exactly 5 options A–E)

Fallback (allowed only if BASIC is technically unsupported):
- Q1 may be generated as MCQ **only if**:
  - all options are within the same differential family, and
  - the correct answer is not trivially revealed.
- Fallback must be applied consistently across all arms if enabled.

---

## 10. Item-Writing Rules (Placement-Aware)

### 10.1 Global constraints (all cards)
- Board-relevant, high-yield only.
- Avoid ambiguous stems requiring external context.
- **Q1/Q2 must be solvable from text alone** (images are on BACK, providing educational reinforcement).
- **Do not use deictic image references** ("this image", "shown here", "above figure").

### 10.2 Q1 — BASIC + IMAGE_ON_BACK
**Front (question)**
- Text-only question that can be solved from text description alone.
- One short prompt:
  - "Most likely diagnosis?"
  - "Name the key imaging sign."
  - "What pattern is demonstrated?"
- May include imaging description in words (e.g., "CT shows...") as long as it does not rely on an actual figure being present.
- Must be solvable without an image (text-first approach).

**Back (answer/explanation)**
- `Answer:` single diagnosis/sign
- `Why:` 2–3 bullets (image-visible features)
- `Pitfall:` optional 1 bullet
- Image (if present) reinforces the explanation; text remains sufficient.

**Hard self-check**
- If Q1 front text gives away the answer with excessive hints → FAIL (rewrite to maintain appropriate difficulty).
- Q1 must be solvable from text alone, but image on back provides educational reinforcement.

### 10.3 Q2 — MCQ + IMAGE_ON_BACK
**Front**
- Text-only vignette and/or imaging description in words.
- Must be solvable without an image.
- Exactly 5 options (A–E).
- Modality mention is allowed (e.g., "contrast-enhanced CT shows…") **as long as** it does not rely on an actual figure being present.

**Back**
- Correct option + rationale.
- Image (if present) reinforces the explanation; text remains sufficient.

**Failure mode**
- Any phrasing that collapses without an image ("shown on the image…", "this figure…").

### 10.4 (Deprecated) Q3 — MCQ + NO_IMAGE
Q3 is **deprecated / not generated** in the current pipeline.
This section remains only for legacy reference.

---

## 11. Artifacts (Recommended)

### 11.1 Placement manifest (S3 or pre-export)
`image_policy_manifest.jsonl` (one row per card):
```json
{
  "group_id": "...",
  "entity_id": "...",
  "card_role": "Q1|Q2",
  "image_placement_final": "FRONT|BACK|NONE",
  "card_type": "BASIC|MCQ",
  "image_asset_required": true
}
```

### 11.2 Image hint manifest (S2 output, recommended)
`image_hint_manifest.jsonl` (one row per image-enabled card; Q1/Q2 only):
```json
{
  "group_id": "...",
  "entity_id": "...",
  "card_role": "Q1|Q2",
  "image_hint": { "...": "..." }
}
```

### 11.3 Image spec manifest (S3 output; authoritative for S4)
`s3_image_spec.jsonl` (one row per image-enabled card; current policy: Q1/Q2 both):
```json
{
  "schema_version": "S3_IMAGE_SPEC_v1.0",
  "group_id": "...",
  "entity_id": "...",
  "card_role": "Q1|Q2",
  "prompt_en": "...",
  "modality": "...",
  "key_findings_keywords": ["..."]
}
```

---

## 12. Gate / Validator Checks (Fail-fast)

Minimum enforced checks before export:

1) **2-card completeness**
- Each entity has exactly Q1/Q2 (and only Q1/Q2).

2) **Format correctness**
2) **Format correctness**
- Q2 has exactly 5 options labeled A–E.
- `front`/`back` are non-empty.

3) **Placement compliance**
- If `image_placement_final == NONE`: front/back must not include image-referential phrases.
- If `image_placement_final in {FRONT, BACK}`: card MUST NOT contain deictic image references; image is attached by template, not referenced.

4) **Image hint compliance (new)**
- Q1 must include `image_hint`.
- Q2 must include `image_hint`.

5) **Asset required check (operational, recommended)**
- For Q1, if `image_asset_required == true` and the asset is missing, FAIL-FAST before distribution.

---

## 13. Change Log

### v1.3
- Fixed the per-entity 3-card rule as the single standard (no per-entity image necessity concept).
- Explicitly defined S3 as a **deterministic ImageSpec compiler** (no LLM), consuming **S1 visual context + S2 image hints** and producing standardized prompts/specs for S4.
- Added a minimal `image_hint` object requirement for image-enabled cards (Q1 required; Q2 recommended).
- Added recommended `s3_image_spec.jsonl` artifact and related validator checks.

## 04_Step_Contracts/S3_to_S4_Input_Contract_Canonical.md

```markdown
# S3 → S4 Input Contract (Canonical)

- Status: Canonical · Frozen
- Applies to: Step03 (S3) → Step04 (S4)
- Boundary: S3 → S4
- Last Updated: 2026-03-30
- Compliance: MI-CLEAR-LLM / IRB-ready
- Implementation Status: ✅ **완료** (2025-12-20)
  - `03_s3_policy_resolver.py` → `04_s4_image_generator.py` 인터페이스 구현 완료
  - Join key SSOT: `(run_tag, group_id, entity_id, card_role)`
  - S3 출력: `s3_image_spec__arm{X}.jsonl`
  - S4 입력: `s3_image_spec__arm{X}.jsonl`
  - S4 출력: `s4_image_manifest__arm{X}.jsonl` + 이미지 파일들

## 0. Purpose (Normative)

This document defines the single authoritative contract for handing off
S3 outputs to S4 inputs, to eliminate ambiguity in boundary enforcement,
IRB/QA audits, and code review.

This contract is binding and frozen. Any deviation is a protocol violation.

## 1. Authoritative Boundary Rule (Binding)

- S3 is a state-only compiler (Policy Resolver & ImageSpec Compiler).
  S3 outputs image policy manifest and image specs only (no content generation/modification).
- S4 is a render-only presentation stage.
  S4 consumes S3 image specs to generate images without adding medical meaning.

Therefore:
> The S3 → S4 handoff is a spec-to-render contract.
> S3 compiles image generation specs from upstream content.
> S4 renders images from S3 specs without interpretation.

## 2. S3 Output (Authoritative Inputs to S4)

S4 MUST treat the following as read-only authoritative inputs from S3.

### 2.1 Required: Image Spec File

**File:** `s3_image_spec__arm{X}.jsonl` (또는 suffix 포함 변형)

**S3 Spec Naming Convention (2026-01-05 확정):**
- `s3_image_spec__arm{X}__original_diagram.jsonl`: 원본 spec (절대 수정 금지)
- `s3_image_spec__arm{X}__realistic_v{N}.jsonl`: realistic 변환용 spec (선택사항)
- `s3_image_spec__arm{X}__regen_positive_v{N}.jsonl`: positive regen용 spec (선택사항)
- `s3_image_spec__arm{X}.jsonl`: 하위 호환 (suffix 없음, 기본값)

**Rationale:** Suffix 분리로 원본 보호 + 워크플로우별 spec 버전 관리 가능.

Each line is a JSON object representing one image generation spec:

**For card images (Q1 & Q2; independent back-only infographics):**
```json
{
  "schema_version": "S3_IMAGE_SPEC_v1.0",
  "run_tag": "...",
  "group_id": "...",
  "entity_id": "...",
  "entity_name": "...",
  "card_role": "Q1" | "Q2",
  "spec_kind": "S2_CARD_IMAGE",
  "image_placement_final": "FRONT" | "BACK",
  "image_asset_required": true,
  "modality": "...",
  "anatomy_region": "...",
  "key_findings_keywords": ["..."],
  "template_id": "...",
  "prompt_en": "...",
  "constraint_block": "...",
  "answer_text": "...",
  "view_or_sequence": "...",
  "exam_focus": "..."
}
```

**Notes (binding):**
- `constraint_block` is a deterministic, compact rendering of structured constraints (e.g., from `image_hint_v2`
  and/or cluster-level hints) injected by S3 into the prompt templates for S4.
- S4 MUST treat `prompt_en` (including the embedded constraint block) as authoritative and MUST NOT rewrite it.

**For table visuals (S1):**
```json
{
  "schema_version": "S3_IMAGE_SPEC_v1.0",
  "run_tag": "...",
  "group_id": "...",
  "entity_id": null,
  "entity_name": null,
  "card_role": null,
  "spec_kind": "S1_TABLE_VISUAL",
  "image_placement_final": "TABLE",
  "image_asset_required": true,
  "visual_type_category": "...",
  "template_id": "...",
  "prompt_en": "..."
}
```

### 2.2 Required: Policy Manifest File

**File:** `image_policy_manifest__arm{X}.jsonl`

Each line is a JSON object representing image policy for each card:

```json
{
  "schema_version": "S3_POLICY_MANIFEST_v1.0",
  "run_tag": "...",
  "group_id": "...",
  "entity_id": "...",
  "card_role": "Q1" | "Q2",
  "image_placement": "BACK",
  "card_type": "BASIC" | "MCQ",
  "image_required": true | false
}
```

**Policy Rules (Hardcoded):**
- Q1: `image_placement="BACK"`, `image_required=true` (back-only infographic)
- Q2: `image_placement="BACK"`, `image_required=true` (Q1과 독립적인 이미지 생성; Q1 이미지 재사용 아님)

## 3. S3 Processing Rules (Binding)

S3 MUST follow these rules when compiling image specs:

### 3.1 Image Hint Validation

- **Q1**: `image_hint` 필수, `modality_preferred`, `anatomy_region`, `key_findings_keywords` 필수
- **Q2**: `image_hint` 필수 (Q1과 독립적인 infographic 생성을 위해 사용)

### 3.2 Image Spec Compilation

- S3 extracts `image_hint` from S2 **Q1 and Q2** cards and compiles into `prompt_en` (English) using prompt templates
- S3 uses prompt bundle system:
  - **Card images (Q1/Q2)**: `S4_EXAM_SYSTEM` + `S4_EXAM_USER` templates
  - **Table visuals**: `S4_CONCEPT_SYSTEM` + `S4_CONCEPT_USER__{visual_type_category}` templates (fallback to `S4_CONCEPT_USER__General`)
- S3 combines system and user prompts: `prompt_en = system_template + "\n\n" + user_formatted`
- S3 extracts `answer_text` from cards (for spec storage) but does NOT include it in prompt generation
- S3 compiles S1 table visual specs (one per group) when `master_table_markdown_kr` is available

### 3.3 Deterministic Processing

- S3 is a compiler (no LLM calls)
- All policy decisions are hardcoded
- All prompt generation uses deterministic templates from prompt bundle (`_registry.json`)
- Prompt templates are loaded from `3_Code/prompt/` directory via `load_prompt_bundle()`
- Template placeholders are filled using `safe_prompt_format()` to handle JSON examples in templates

## 4. S3 Prohibitions (Hard Fail)

S3 MUST NOT perform any of the following:

### 4.1 Content Generation/Modification (Forbidden)

- ❌ Generate new cards
- ❌ Edit or rewrite card text (front/back)
- ❌ Modify answers, explanations, or structure
- ❌ Add or remove medical facts

### 4.2 Medical Interpretation (Forbidden — with compiler safety defaults)

- ❌ Derive lesion class or imaging features
- ❌ Summarize or reinterpret medical meaning
- ❌ Make clinical judgments or diagnostic inferences

**Compiler Safety Defaults (Permitted):**
The following deterministic fallbacks are permitted as spec-completeness guarantees, not medical interpretation:
- When `modality_preferred` is missing or "Other", S3 may assign a default modality value to prevent S4 prompt failure
- When `view_or_sequence` is missing in `image_hint_v2`, S3 may fill a safe default
- QC/Equipment entities are deterministically routed to CONCEPT rendering paths based on group metadata

### 4.3 Image Generation (Forbidden)

- ❌ Call LLM for image generation (S3 is compiler-only)
- ❌ Generate actual images
- ❌ Decide image layout or style beyond template selection

**Rationale:**
S3 is a compiler that creates specs. S4 is the renderer that generates images.

## 5. S4 Processing Rules (Binding)

S4 MUST follow these rules when rendering images:

### 5.1 Image Generation

- S4 reads `s3_image_spec__arm{X}.jsonl` and generates images for each spec
- S4 uses Gemini API (`models/nano-banana-pro-preview`) for all image generation
- S4 uses `prompt_en` from S3 spec directly (no modification)
- S4 does not perform web retrieval. Any retrieval/grounding, if used, MUST be offline/internal and injected upstream
  (S3 selects blueprint_id or embeds blueprint text into the spec; S4 remains a renderer).

### 5.2 File Naming

- **Card images**: `IMG__{run_tag}__{group_id}__{entity_id}__Q1{suffix}.jpg` and `IMG__{run_tag}__{group_id}__{entity_id}__Q2{suffix}.jpg`
- **Table visuals**: `IMG__{run_tag}__{group_id}__TABLE{suffix}.jpg`
- Deterministic mapping ensures 1:1 card-to-image traceability per role.
- **Suffix**: `--image_type` CLI 인자에 따라 자동 설정 (기본값: 없음, `realistic`: `_realistic`, `regen`: `_regen`)
- **Folder**: `--image_type` CLI 인자에 따라 자동 설정 (기본값: `images/`, `anki`: `images_anki/`, `realistic`: `images_realistic/`, `regen`: `images_regen/`)
- **하위 호환성**: CLI 인자 없이 실행하면 기존 방식(`images/` 폴더, suffix 없음) 유지

### 5.3 Image Specifications

- **Card images (Q1 & Q2)**: `aspect_ratio="4:5"`, `image_size="2K"` (default, configurable via `S4_CARD_IMAGE_SIZE` env var)
- **Table visuals**: `aspect_ratio="16:9"`, `image_size="4K"`

### 5.4 Fail-Fast Rules

- Q1 image generation failure → FAIL-FAST (required)
- Q2 image generation failure → FAIL-FAST (required)
- Table visual image generation failure → FAIL-FAST

## 6. S4 Output (Authoritative)

### 6.1 Image Files

- 기본값: `{RUN_TAG}/images/IMG__*.jpg` (card images + table visuals, suffix 없음)
- `--image_type anki`: `{RUN_TAG}/images_anki/IMG__*.jpg` (suffix 없음)
- `--image_type realistic`: `{RUN_TAG}/images_realistic/IMG__*_realistic.jpg`
- `--image_type regen`: `{RUN_TAG}/images_regen/IMG__*_regen.jpg` ✅ **구현 완료**
  - **Same RUN_TAG as baseline** (folder + suffix로 구분)
  - S5 validation 결과의 `prompt_patch_hint` 기반 positive regen
  - S3 spec: `s3_image_spec__armX__regen_positive_v{N}.jsonl`

### 6.2 Image Manifest

**File:** `s4_image_manifest__arm{X}.jsonl` (baseline) or `s4_image_manifest__arm{X}__regen.jsonl` (regen)

**Manifest 분리 정책 (2026-01-05 확정):**
- Baseline: `s4_image_manifest__armX.jsonl`
- Regen: `s4_image_manifest__armX__regen.jsonl` (separate file to avoid overwrite)
- Realistic: `s4_image_manifest__armX__realistic.jsonl` (if applicable)

```json
{
  "schema_version": "S4_IMAGE_MANIFEST_v1.0",
  "run_tag": "...",
  "group_id": "...",
  "entity_id": "...",
  "card_role": "Q1" | "Q2" | null,
  "spec_kind": "S2_CARD_IMAGE" | "S1_TABLE_VISUAL",
  "media_filename": "IMG__...",
  "image_path": "/path/to/image",
  "generation_success": true | false,
  "image_required": true | false
}
```

## 7. Acceptance Tests (Fail-Fast)

S3 must hard-fail if:
- Q1 `image_hint` missing or invalid
- Required fields (`modality_preferred`, `anatomy_region`, `key_findings_keywords`) missing in Q1
- Q2 `image_hint` missing or invalid

S4 must hard-fail if:
- S3 image spec file missing
- Q1 image generation failure
- Q2 image generation failure
- Table visual image generation failure

## 8. Change Control

Frozen. Any changes require:
- protocol-level justification
- CP re-validation (CP-4 boundary test mandatory)
- canonical merge record
```

---

## 운영 합의 요약 (프로젝트 규칙으로 “고정”)

1. **Canonical 단일본 위치 확정**
   `04_Step_Contracts/S3_to_S4_Input_Contract_Canonical.md`

2. **archive의 v3는 “이전 Canonical(동결 보관)”으로 유지**
   지금까지 확정한 버전관리 원칙(archived로 이동, 삭제 금지)에 그대로 부합합니다.

3. **경계 판단 기준 단일화**

* S3는 "image policy manifest + image spec"만 산출한다 (컴파일러 역할).
* S4는 "S3 image spec 기반 이미지 생성"만 수행하며, S3에 추가 의미를 요구하지 않는다.
* S3는 LLM을 호출하지 않으며, deterministic 템플릿 기반으로 프롬프트를 생성한다.
* S4는 S3에서 생성된 프롬프트를 그대로 사용하며, 수정하지 않는다. 
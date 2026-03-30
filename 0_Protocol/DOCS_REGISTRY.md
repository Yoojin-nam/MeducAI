# Protocol Docs Registry (Inventory + SSOT Map + Code↔Protocol Mismatch Register)

**Status:** Canonical (Registry)  
**Scope:** Documentation governance only (does not define new pipeline policy)  
**Primary Goal:** Provide a single, auditable place to answer:  
1) “Which document is SSOT for X?” and  
2) “Where are code vs protocol currently inconsistent?”

---

## 1) SSOT Map (What to trust for what)

### 1.1 Highest-level interpretation SSOT (Document hierarchy)

- **Canonical hierarchy & conflict rules (SSOT)**  
  - `0_Protocol/00_Governance/meduc_ai_pipeline_canonical_governance_index.md`
- **Document status / how to read `0_Protocol` (operator guide)**  
  - `0_Protocol/00_Governance/DOCUMENT_STATUS_GUIDE.md`
- **Document versioning / canonicalization rules (SSOT)**  
  - `0_Protocol/00_Governance/MeducAI_Document_Versioning_Policy.md`

### 1.2 “Current week” operational SSOT (time-varying)

- **Weekly integrated operating conclusion (SSOT for “what we do this week”)**  
  - `0_Protocol/01_Execution_Safety/stabilization/Weekly_Integrated_Conclusion_Operating_SSOT.md`

> **Rule:** If a stable Canonical (Level 0–2) conflicts with the weekly operating SSOT, treat it as an escalation item—do not silently “patch reality” in ad-hoc ways.

### 1.3 Implementation SSOT (what the pipeline *actually does*)

- **Runtime behavior SSOT**: `3_Code/src/`  
  - Entrypoint (S1/S2): `3_Code/src/01_generate_json.py`
  - S3 policy/spec compiler: `3_Code/src/03_s3_policy_resolver.py`
  - S4 image generator: `3_Code/src/04_s4_image_generator.py`
  - S5 validator: `3_Code/src/05_s5_validator.py`
  - S6 positive instruction agent: `3_Code/src/06_s6_positive_instruction_agent.py`
  - PDF builder: `3_Code/src/07_build_set_pdf.py`
  - Anki exporter: `3_Code/src/07_export_anki_deck.py`
- **FINAL QA 도구 SSOT**: `3_Code/src/tools/final_qa/` (AppSheet 통합)
- **Batch 이미지 생성 SSOT**: `3_Code/src/tools/batch/batch_image_generator.py`
- **Prompt runtime SSOT**: `3_Code/prompt/_registry.json` + referenced prompt files under `3_Code/prompt/`
- **Path resolution SSOT (backward-compatible path rules)**: `3_Code/src/tools/path_resolver.py`

> **Rule:** When “what the code does” diverges from protocol text, the immediate SSOT for execution is the code, but the **protocol must be updated** (or explicitly marked superseded) to avoid audit ambiguity.

### 1.4 Schema/contract SSOT (interfaces)

- **S1 output schema (frozen)**: `0_Protocol/04_Step_Contracts/Step01_S1/`
- **S2 output schema (canonical)**:  
  - `0_Protocol/04_Step_Contracts/Step02_S2/S2_Contract_and_Schema_Canonical.md`
  - (v2 structured hint schema) `0_Protocol/04_Step_Contracts/Step02_S2/S2_Image_Hint_Schema_v2.json`
- **S2 current status & future upgrade (reference)**:  
  - `0_Protocol/04_Step_Contracts/Step02_S2/S2_Current_Status_and_Future_Upgrade.md` (current production version, publication considerations)
  - `0_Protocol/00_Governance/supporting/Prompt_governance/S2_Language_Policy_Future_Upgrade.md` (future language policy improvements)
- **S3→S4 contract (canonical)**: `0_Protocol/04_Step_Contracts/S3_to_S4_Input_Contract_Canonical.md`

### 1.5 Research/QA SSOT (study-facing)

- **3-Paper Research Index (Master Index)**: `0_Protocol/06_QA_and_Study/MeducAI_3Paper_Research_Index.md`
- **Manuscript Preparation Status**: `0_Protocol/06_QA_and_Study/MeducAI_Manuscript_Preparation_Status.md`
- **QA framework SSOT**: `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/QA_Framework.md`
- **Paper 1+2 Research Design SSOT**: `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/Paper1_Paper2_Research_Design_Spec.md`
- **Paper 1 QA Endpoints SSOT**: `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/Paper1_QA_Endpoints_Definition.md`
- **Paper 2 Table Infographic Evaluation SSOT**: `0_Protocol/06_QA_and_Study/Paper2_Image_Reliability/Paper2_Table_Infographic_Evaluation_Design.md`
- **Paper 2 VTT Design SSOT**: `0_Protocol/06_QA_and_Study/Paper2_Image_Reliability/Paper2_Visual_Turing_Test_Design_Detailed.md`
- **Paper 3 Study Design SSOT**: `0_Protocol/06_QA_and_Study/Paper3_Educational_Effectiveness/Paper3_Study_Design.md`
- **Paper 3 Communications (archived)**: `0_Protocol/06_QA_and_Study/archived/2026-03-consolidation/Communications/`

### 1.6 Objective / variable governance SSOT

- **Objective source traceability SSOT**: `0_Protocol/00_Governance/Objective_Source_Traceability_Spec.md`
- **Terminology SSOT**: `0_Protocol/00_Governance/MeducAI_Terminology_Glossary.md`
- **Variable/identifier registry SSOT**: `0_Protocol/00_Governance/MeducAI_Variable_and_Identifier_Registry.md`

---

## 2) Inventory (Minimal “Start Here” set)

This inventory is intentionally small; it points to *where the rest lives* rather than duplicating content.

### 2.1 Start Here (everyone)

- `0_Protocol/README.md` (reading order)
- `0_Protocol/00_Governance/meduc_ai_pipeline_canonical_governance_index.md` (hierarchy SSOT)
- `0_Protocol/01_Execution_Safety/stabilization/Weekly_Integrated_Conclusion_Operating_SSOT.md` (current ops SSOT)
- `0_Protocol/05_Pipeline_and_Execution/Pipeline_Canonical_Specification.md` (pipeline constitution)

### 2.2 If you are executing runs (operators)

- `0_Protocol/05_Pipeline_and_Execution/Pipeline_Execution_Plan.md`
- `0_Protocol/05_Pipeline_and_Execution/Pipeline_FailFast_and_Abort_Policy.md`
- `0_Protocol/05_Pipeline_and_Execution/Runtime_Artifact_Manifest_Spec.md`
- `0_Protocol/05_Pipeline_and_Execution/Image_Asset_Naming_and_Storage_Convention.md` (Realistic/REGEN/Anki 이미지 경로·파일명 인계 규칙)
- `0_Protocol/01_Execution_Safety/Prompt_Rendering_Safety_Rule.md`
- **Handoff Documentation** (execution history and major changes):
  - `0_Protocol/01_Execution_Safety/handoffs/` (language policy, translation workflow)
  - `0_Protocol/05_Pipeline_and_Execution/handoffs/` (image/S5/PDF/regeneration)
  - `0_Protocol/06_QA_and_Study/QA_Operations/handoffs/` (FINAL distribution, AppSheet)

### 2.3 If you are working on step interfaces (engineers / reviewers)

- `0_Protocol/04_Step_Contracts/`
  - especially `Step02_S2/` and `S3_to_S4_Input_Contract_Canonical.md`
- `0_Protocol/05_Pipeline_and_Execution/Code_to_Protocol_Traceability.md`

### 2.4 If you are reviewing QA / release decisions

- `0_Protocol/06_QA_and_Study/MeducAI_3Paper_Research_Index.md` (3-Paper 연구 인덱스)
- `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/QA_Framework.md`
- `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/Paper1_Paper2_Research_Design_Spec.md`
- `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/Paper1_QA_Endpoints_Definition.md`
- **FINAL QA AppSheet export handoff (2026-01-09)**:
  - `0_Protocol/06_QA_and_Study/QA_Operations/handoffs/APP_SHEET_EXPORT_HANDOFF_2026-01-09.md`
- **⚠️ Critical: AppSheet Time Calculation Issue (2026-01-09)**:
  - `0_Protocol/06_QA_and_Study/QA_Operations/handoffs/APPSHEET_TIME_CALCULATION_ISSUE_2026-01-09.md`
  - 분석 시작 전 필수 확인: duration_sec 컬럼 사용 금지, 타임스탬프 재계산 필수

### 2.5 If you are working on research papers

> **논문 준비 현황 종합**: `0_Protocol/06_QA_and_Study/MeducAI_Manuscript_Preparation_Status.md`

**Paper 1 (S5 Multi-agent 신뢰도)**:
- `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/Paper1_Paper2_Research_Design_Spec.md`
- `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/Paper1_QA_Endpoints_Definition.md`
- `0_Protocol/05_Pipeline_and_Execution/S5_Decision_Definition_Canonical.md`

**Paper 2 (MLLM 이미지 신뢰도)**:
- `0_Protocol/06_QA_and_Study/Paper2_Image_Reliability/Paper2_Visual_Turing_Test_Design_Detailed.md`
- `0_Protocol/06_QA_and_Study/Paper2_Image_Reliability/Paper2_Table_Infographic_Evaluation_Design.md`
- `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/Paper1_Paper2_Research_Design_Spec.md` (Section 8: Visual Modality)

**Paper 3 (교육효과 전향적 연구)**:
- `0_Protocol/06_QA_and_Study/Paper3_Educational_Effectiveness/Paper3_Study_Design.md`
- `0_Protocol/06_QA_and_Study/Paper3_Educational_Effectiveness/Paper3_Survey_Overview.md`
- `0_Protocol/06_QA_and_Study/Paper3_Educational_Effectiveness/Paper3_Statistical_Analysis_Plan.md`
- `0_Protocol/IRB/`

---

## 3) Code ↔ Protocol mismatch register (as of 2026-03-30)

**How to read:** Each item lists the **code truth**, the **protocol/docs that conflict**, and what must be reconciled.

### M-01 — Per-entity card count (2-card vs 3-card)

- **Code truth (SSOT)**  
  - `3_Code/src/01_generate_json.py` enforces **exactly 2 cards per entity** (Q1/Q2) and forces S0 allocation requests to 2.
  - `3_Code/src/03_s3_policy_resolver.py` accepts only Q1/Q2.
- **Status**
  - ✅ **Resolved (2025-12-30)** — Protocol Canonicals now explicitly define **2-card (Q1/Q2 only)** and remove Q3 from the current pipeline.
  - Updated docs: `Pipeline_Canonical_Specification.md`, `S2_Cardset_Image_Placement_Policy_Canonical.md`, `Code_to_Protocol_Traceability.md`.

### M-02 — Image placement (Q1 FRONT vs BACK; Q2 behavior)

- **Code truth (SSOT)**
  - `3_Code/src/03_s3_policy_resolver.py`: Q1=BACK, Q2=BACK (**both back-only**).
  - `3_Code/src/07_export_anki_deck.py`: back-only infographics are assumed for Q1/Q2 (fail-fast if missing).
- **Status**
  - ✅ **Resolved (2025-12-30)** — Protocol Canonicals now match code: **Q1=BACK, Q2=BACK** (back-only infographics).

### M-03 — “Q2 reuses Q1 image” vs “Q2 has its own image”

- **Code truth (SSOT)**
  - `3_Code/src/01_generate_json.py`: Q2 requires its own `image_hint`.
  - `3_Code/src/03_s3_policy_resolver.py`: compiles specs and policy per Q1/Q2; Q2 image_required=True.
- **Status**
  - ✅ **Resolved (2025-12-30)** — Protocol now matches code: **Q2 has its own image** (no reuse), and S3 compiles specs for **both Q1 and Q2**.
  - Updated docs: `S3_to_S4_Input_Contract_Canonical.md`, `S2_Cardset_Image_Placement_Policy_Canonical.md`.

### M-04 — S3 “no inference” prohibition vs actual S3 deterministic inference/fallbacks

- **Code truth (SSOT)**
  - `3_Code/src/03_s3_policy_resolver.py` deterministically:
    - infers modality when `modality_preferred` is missing/Other,
    - fills view/sequence defaults in `image_hint_v2`,
    - routes QC/Equipment to CONCEPT rendering paths,
    - supports table input selection (`S4_TABLE_INPUT_MODE`) and produces allowed-text blocks.
- **Status**
  - ✅ **Resolved (2026-03-30)** — `S3_to_S4_Input_Contract_Canonical.md` Section 4.2 updated to permit these deterministic fallbacks as “compiler safety defaults” (spec-completeness guarantees, not medical interpretation). Medical interpretation prohibitions (lesion class derivation, clinical judgment) remain forbidden.

### M-05 — S4 output file format + image sizes (PNG/1K/2K vs JPG/2K/4K)

- **Code truth (SSOT)**
  - `3_Code/src/04_s4_image_generator.py` produces deterministic filenames with **`.jpg`** extension.
  - Default sizes: **card images 2K**, **table visuals 4K** (configurable via env vars / spec_kind).
- **Status**
  - ✅ **Resolved (2026-03-30)** — Protocol documents updated to match code:
    - `Pipeline_Canonical_Specification.md`: PNG→JPG, card 1K→2K, table 2K→4K, filenames `.png`→`.jpg`
    - `S3_to_S4_Input_Contract_Canonical.md`: card 1K→2K, table 2K→4K (filenames were already `.jpg` in this doc)

### M-06 — Script name drift (`05_*.py` vs `06_*.py` vs `07_*.py`)

- **Code truth (SSOT)**
  - Pipeline 단계별 스크립트 번호 체계 (2026-01-04 확정):
    - `01_`: S1/S2 (JSON 생성)
    - `03_`: S3 (Policy Resolver)
    - `04_`: S4 (Image Generation)
    - `05_`: S5/S5R (Validation, Repair)
    - `06_`: S6 (Export Gate, Specialty PDF, Order File)
    - `07_`: Final Output (Set PDF, Anki Deck)
  - 현재 스크립트: `3_Code/src/07_build_set_pdf.py`, `3_Code/src/07_export_anki_deck.py`
- **Status**
  - ✅ **Resolved (2026-01-04)** — 번호 체계 확정: S6 이후 최종 출력물(PDF, Anki)은 `07_`로 통일.

### M-07 — Traceability doc drift (paths / claims that no longer match code)

- **Code truth (SSOT)**
  - Current implemented entrypoints and output naming include:
    - `s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl` (new format)
    - S4 uses `.jpg` outputs
- **Status**
  - ✅ **Resolved (2025-12-30)** — `Code_to_Protocol_Traceability.md` updated to mirror current code tree and artifact naming. M-05 also resolved (2026-03-30).

---

## 4) Notes / boundaries (what this registry is NOT)

- This registry is **not** the place to re-argue policy or introduce new rules.
- If a mismatch implies a policy change, it must be handled via:
  - (a) updating the relevant Canonical(s) + archival trail, or
  - (b) reverting/changing code to match existing Canonical(s),
  - and recording the change in governance logs per versioning policy.

---

## 5) Document Organization Log

### 2026-01-09: Translation Workflow Completion & Repository Consolidation

**변경 사항**:
1. **Translation Workflow Scripts Archived**:
   - 27개 번역/디버깅 스크립트 아카이브 완료
   - 위치: `3_Code/archived/translation_workflow_2026-01-07/`
   - 의학용어 영어 전용 정책 구현 완료 (Anki, AppSheet)
   - Production scripts 유지: `export_final_anki_integrated.py`, `merge_anki_decks_with_regen.py`, `update_anki_with_regen.py`
2. **Paper 3 Communications Separated**:
   - 이메일, 카카오톡 공지 등 커뮤니케이션 문서 분리
   - 위치: `0_Protocol/06_QA_and_Study/Communications/`
   - 연구 설계 문서와 운영 문서는 메인 폴더에 유지
3. **Handoff Documentation Indexed**:
   - 3개 handoff 폴더에 README.md 추가
   - `0_Protocol/01_Execution_Safety/handoffs/` (언어 정책, 번역 워크플로우)
   - `0_Protocol/05_Pipeline_and_Execution/handoffs/` (이미지/S5/PDF/재생성)
   - `0_Protocol/06_QA_and_Study/QA_Operations/handoffs/` (FINAL 배포, AppSheet)

**업데이트된 문서**:
- `README.md`: Pipeline 개요 S5/S6 추가, v1.3.1 업데이트, 번역 워크플로우 섹션 추가
- `DOCS_REGISTRY.md`: Paper 3 Communications 참조 추가, handoff 위치 추가, S6 추가
- `3_Code/README.md`: 번역 워크플로우 완료 및 아카이브 참조

**신규 문서**:
- `3_Code/archived/translation_workflow_2026-01-07/README.md`: 아카이브된 번역 스크립트 인덱스
- `0_Protocol/06_QA_and_Study/Communications/README.md`: Paper 3 커뮤니케이션 문서 인덱스
- `0_Protocol/01_Execution_Safety/handoffs/README.md`: Execution safety handoffs 인덱스
- `0_Protocol/CONSOLIDATION_SUMMARY_2026-01-09.md`: 통합 정리 요약

**참조 문서**:
- Handoff: `0_Protocol/01_Execution_Safety/handoffs/HANDOFF__MEDTERM_ENGLISH_ONLY__S2_APPSHEET_ANKI__2026-01-07.md`
- Language Policy: `0_Protocol/00_Governance/supporting/Prompt_governance/S2_Language_Policy_Future_Upgrade.md`

### 2026-01-05: S3 Spec 네이밍 규칙 확정 및 Positive Regen (Option C) 구현 완료

**변경 사항**:
1. **S3 Spec 네이밍 규칙 확정**:
   - `s3_image_spec__arm{X}__original_diagram.jsonl`: 원본 spec (절대 수정 금지)
   - `s3_image_spec__arm{X}__realistic_v{N}.jsonl`: realistic 변환용 spec (선택사항)
   - `s3_image_spec__arm{X}__regen_positive_v{N}.jsonl`: positive regen용 spec (선택사항)
2. **Positive Regen (Option C Image Regeneration) 구현 완료**:
   - S5 `prompt_patch_hint` 기반 이미지 재생성
   - Same RUN_TAG 사용 (폴더 `images_regen/` + suffix `_regen`로 구분)
   - Manifest 분리: `s4_image_manifest__armX__regen.jsonl` (baseline 보존)
   - 신규 문서: `S5_Positive_Regen_Procedure.md` (운영 가이드)
3. **Q2 이미지 독립 생성 정책 재확인**:
   - Q1/Q2 각각 독립 이미지 생성 (2-card policy)
   - "Q2는 Q1 이미지 재사용" 문구 제거 (S3_S4_Code_Documentation.md)

**업데이트된 문서**:
- `Image_Asset_Naming_and_Storage_Convention.md`: S3 spec 네이밍 + `images_regen/` 폴더 추가
- `S3_to_S4_Input_Contract_Canonical.md`: S3 spec suffix 규칙 + regen manifest 분리 정책
- `S3_S4_Code_Documentation.md`: Q2 독립 이미지 생성 정책 반영
- `S5_Multiagent_Repair_Plan_OptionC_Canonical.md`: Positive Regen 워크플로우 추가
- `S5_Validation_Schema_Canonical.md`: `prompt_patch_hints` 필드 사용 예시 추가
- `AppSheet_Realistic_Image_Evaluation_Design.md`: `images_regen/` 폴더 구조 반영
- `AppSheet_S5_Final_Assessment_Design.md`: Regen 이미지 경로 설명 추가

**신규 문서**:
- `S5_Positive_Regen_Procedure.md`: Positive Regen 운영 절차 가이드 (구현 완료)

### 2026-01-04: 3-Paper 체계 정비

**변경 사항**:
1. Study_Design.md를 v5.0으로 업데이트 (3-Paper 체계)
2. FINAL_QA_Research_Design_Spec.md에 Visual Modality Sub-study 섹션 추가 (전공의 Realistic 평가)
3. MeducAI_3Paper_Research_Index.md 마스터 인덱스 생성
4. Table_Infographic_Evaluation_Plan.md 생성 (5명 평가자 설계)

**아카이브된 문서**:
- 00_Governance/: 정리 로그, 충돌 분석, legacy 문서들
- 05_Pipeline_and_Execution/: HANDOFF 문서, TODO 문서, 안정화 로그
- 06_QA_and_Study/: 업데이트 요약 문서
- 06_QA_and_Study/QA_Operations/: S0 관련 문서, AppSheet 설정 가이드

**핵심 문서 유지**:
- 모든 Canonical 문서
- FINAL QA 관련 핵심 문서
- 연구 설계 및 통계 분석 문서

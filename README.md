# MeducAI

**A Governed, Reproducible Pipeline for LLM-Generated Radiology Learning Content**

---

## 1. What is MeducAI? (One-paragraph summary)

**MeducAI** is a research pipeline for systematically, reproducibly, and auditably generating radiology learning content (e.g., Anki cards, tables, visual materials) using large language models (LLMs).

The core goal of this project is not *content generation itself*, but rather to achieve **fair model comparison (QA), IRB-friendly documentation, and reproducible execution** while maintaining clear definitions of **what each stage can and cannot decide**.

---

## 2. Pipeline Overview (S0 → FINAL)

MeducAI consists of **clearly separated stages (S0–S6, FINAL)**:

```
S0   : QA / Model Comparison (fixed payload, arm fairness)
S1   : Structure only (LLM, no counts)
S2   : Execution only (LLM, exact N cards)
S3   : Selection & QA gate (state-only)
S4   : Rendering & presentation (image only)
S5   : Validation & Triage (multi-agent review, regeneration decisions)
S6   : Positive Instruction (visual regeneration with feedback)
FINAL: Allocation & deployment (card counts decided here only)
```

Core principles:

* **LLMs do not make "decisions".**
* **Card counts, selections, and policies are determined only in code and Canonical documents.**
* **Each stage has unique responsibilities, and boundary violations result in immediate failure (Fail-Fast).**

---

## 3. Canonical Document System (Why this repo looks this way)

This repository is not simply a code repository, but a **"Constitutional" repository for research decision-making**.

### What Canonical means

* For each concept, **only one final document exists** at any time
* Previous versions are not deleted but **archived and frozen**
* Code, experiments, papers, and IRB explanations **always reference Canonical documents as the source of truth**

### Hierarchy (Summary)

* **Level 0–1**: Pipeline constitution, Fail-Fast / Abort rules
* **Level 2**: Step (S0–S4) roles, boundaries, and card count contracts
* **Level 3**: Implementation details, reference documents (for reference only)

This structure enables **external reviewers (IRB, peer reviewers)** to verify "why this design was chosen" by reading documents alone, without examining code.

---

## 4. What this repository intentionally does NOT do (Important)

This repository **intentionally excludes** the following:

* ❌ Learner personal information or raw data
* ❌ Post-hoc adjusted analysis results
* ❌ LLM chain-of-thought exposure
* ❌ Logic relying on implicit rules or verbal agreements
* ❌ Ad-hoc workarounds to "make things work"

In other words, **"explainable research design" takes priority over "working demos"**.

---

## 5. IRB, QA, and Reproducibility Guarantees

MeducAI was designed from the outset with **IRB, auditing, and reproducibility** as prerequisites.

* **Fail-Fast & Abort Policy**
  Error handling scope (RUN / ARM / GROUP / SET) is fixed in advance
* **Runtime Artifact Manifest**
  Each execution (RUN_TAG) mechanically records "what should be generated for a normal run"
* **Fairness guarantee for Arm comparison**
  RAG / Thinking must be verified with **actual execution + metadata recording**, not just *labels*, before comparison is allowed
* **Unified card count decision authority**
  S0 uses fixed payload; only FINAL decides quotas

This ensures **Methods / Supplement / IRB response text is guaranteed by pre-existing documents, not post-hoc**.

---

## 6. Who this README is for

This README is written for the following audiences:

* **Supervisors / Co-authors**:
  "What has this research fixed, and what is it comparing?"
* **IRB reviewers**:
  "To what extent do LLMs participate, and how is control maintained?"
* **External reviewers**:
  "Is reproducibility and experimental fairness demonstrated through documentation?"

> This single document is designed so that reading it alone
> allows understanding of **the project's philosophy, boundaries, and safety mechanisms**.

---

## 7. One-line takeaway

> **MeducAI is not about letting LLMs generate content freely.
> It is about proving—document by document—that they are used safely, fairly, and reproducibly.**

---

## 8. Update Log

> 💡 Update Log (Latest: v1.3)
실시간 업데이트 내역입니다. 최신 버전의 자료를 확인해 주세요.

- **v1.3.1 (Current)** `2026/01/09`
    - **[정리]** Repository 구조 통합 및 정리 (Translation workflow 완료, Paper 3 communications 분리)
    - 번역 워크플로우 스크립트 아카이브 (`3_Code/archived/translation_workflow_2026-01-07/`)
    - Paper 3 커뮤니케이션 문서 분리 (`0_Protocol/06_QA_and_Study/Communications/`)
    - Handoff 문서 README 추가 (3개 위치)
    - S5/S6 파이프라인 단계 추가
- **v1.3** `2026/01/08`
    - **[추가]** 프린팅용 PDF 파일 추가 (4권 분권, 인쇄 주문 안내 포함)
    - 인쇄 주문 시 사용할 수 있는 분권된 PDF 파일 제공
    - 각 권별 표지, 페이지 수, 포함 전문의 정보 제공
    - 자세한 인쇄 주문 방법은 `6_Distributions/MeducAI_Final_Share/PDF/print_ready/README.md` 참고
- **v1.2** `2025/01/08 01:00`
    - **[개선]** Anki 덱 내 의학용어 표기 방식을 **영어 단독(English Only)**으로 변경 (혼동 방지 및 전문성 강화)
- **v1.1** `2025/01/07 13:00`
    - **[수정]** PDF 페이지 순서 재정렬
    - **[UI]** Anki 덱 카드 내 줄바꿈(Layout) 가독성 개선
- **v1.0** `2025/01/07 12:00`
    - 최초 배포 (Initial Release)

---

## 9. Recent Updates

### 3-Paper Research Portfolio Consolidation (2026-01-04)

**연구 체계 정비:**
- ✅ 3-Paper 연구 포트폴리오 구조 확립
- ✅ Study_Design.md v5.0 업데이트 (3-Paper 체계)
- ✅ MeducAI_3Paper_Research_Index.md 마스터 인덱스 생성
- ✅ Visual Modality Sub-study 확장 (전공의 Realistic 평가 추가)
- ✅ Table Infographic Evaluation Plan 생성 (5명 평가자 설계)

**3-Paper 구조:**

| Paper | 제목 | 데이터 소스 |
|-------|------|-------------|
| Paper 1 | S5 Multi-agent 검토 재작성 시스템의 신뢰도 | FINAL QA (1,350 Resident + 330 Specialist) |
| Paper 2 | MLLM 생성 이미지의 신뢰도 | Visual Modality Sub-study + Table Infographic |
| Paper 3 | 교육효과 전향적 관찰연구 | Baseline + FINAL 설문 (IRB 승인) |

**문서 정리:**
- 91개 운영/임시 문서 아카이브 (HANDOFF, S0_QA, AppSheet 설정 등)
- 핵심 Canonical 문서만 유지
- DOCS_REGISTRY.md에 논문별 문서 가이드 추가

**핵심 문서:**
- `0_Protocol/06_QA_and_Study/MeducAI_3Paper_Research_Index.md` (마스터 인덱스)
- `0_Protocol/06_QA_and_Study/Paper3_Educational_Effectiveness/Paper3_Study_Design.md`
- `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/Paper1_Paper2_Research_Design_Spec.md`
- `0_Protocol/06_QA_and_Study/Paper2_Image_Reliability/Paper2_Table_Infographic_Evaluation_Design.md`

---

### Translation Workflow & Repository Consolidation (2026-01-09)

**Repository consolidation completed:**
- ✅ Translation workflow scripts archived (`3_Code/archived/translation_workflow_2026-01-07/`)
- ✅ Medical term English-only policy implemented and completed
- ✅ Paper 3 communications separated (`0_Protocol/06_QA_and_Study/Communications/`)
- ✅ Handoff documentation indexed (3 locations with READMEs)
- ✅ Pipeline overview updated to include S5/S6 stages
- ✅ Main documentation updated for v1.3.1

**Key organizational changes:**
- 27 translation/debugging scripts moved to archive with comprehensive README
- Paper 3 emails and announcements organized in dedicated Communications folder
- Handoff folders now include scope documentation and cross-references
- Production Anki/AppSheet export scripts remain in active tools

**Language policy:**
- Medical terms now English-only across all Anki decks and AppSheet exports
- Sentence structure and formatting preserved during translation
- Applied consistently to baseline and regenerated cards

**Reference documents:**
- `0_Protocol/CONSOLIDATION_SUMMARY_2026-01-09.md` (consolidation summary)
- `3_Code/archived/translation_workflow_2026-01-07/README.md` (archived scripts)
- `0_Protocol/06_QA_and_Study/Communications/README.md` (communications index)
- `0_Protocol/01_Execution_Safety/handoffs/HANDOFF__MEDTERM_ENGLISH_ONLY__S2_APPSHEET_ANKI__2026-01-07.md`

---

### Legacy Cleanup & Protocol Consolidation (2025-12-22)

**Repository organization completed:**
- ✅ Legacy metadata/code archived (`2_Data/metadata/legacy/`, `3_Code/archived/`)
- ✅ Protocol root documents consolidated into `00_Governance/`
- ✅ Scripts/Configs/Notebooks organized (moved to `legacy/` folders)
- ✅ Tools migration completed (`3_Code/src/tools/`)
- ✅ System files removed (`.DS_Store`, etc.)
- ✅ `9_Future_Work/` added to `.gitignore`

**Key organizational changes:**
- All Protocol summary/analysis documents moved to `0_Protocol/00_Governance/`
- Legacy scripts moved to `3_Code/Scripts/legacy/`
- Utility scripts migrated to `3_Code/src/tools/` and `3_Code/src/tools/qa/`
- Legacy configs moved to `3_Code/configs/legacy/`
- Legacy notebooks moved to `3_Code/notebooks/legacy/`

**Git milestones:**
- Frozen tag: `protocol-freeze-v1.1` (2025-12-22)
- Default branch: `protocol-freeze-main`

**Reference documents:**
- `0_Protocol/00_Governance/archived/LEGACY_AND_CLEANUP_DOCUMENTS_INDEX.md` (archived)
- `0_Protocol/00_Governance/archived/LEGACY_CLEANUP_SUMMARY.md` (archived)
- `0_Protocol/00_Governance/archived/LEGACY_ARCHIVE_SUMMARY.md` (archived)

---

### Upstream Curriculum Preprocess v2 (Robust PDF → SSOT) (2025-12-27)

**What changed:**
- ✅ Robust PDF parsing that recovers wrapped lines / page breaks / deep nesting (notably pediatric sections)
- ✅ Deterministic LLM steps using `gemini-3-flash-preview` (translation/enrichment) with MI‑CLEAR‑LLM run logs
- ✅ Text normalization for PDF artifacts (e.g., split English tokens like `R enal` → `Renal`)
- ✅ Versioned SSOT outputs ready for S1–S4 with no schema changes required

**Key outputs (v2):**
- `2_Data/processed/Radiology_Curriculum_Weight_Factor_v2.xlsx` (SSOT)
- `2_Data/metadata/groups_canonical_v2.csv` (+ `.sha256`, `.meta.json`)
- `2_Data/metadata/translation_map_v2.json` (expanded coverage)
- MI‑CLEAR logs: `2_Data/processed/logs/<run_id>.jsonl` and `<run_id>.system_prompts.txt`

**How to run (v2 upstream pipeline):**
- `3_Code/src/preprocess/run_pipeline_v2.py` (end-to-end)

**Legacy note (S0 interpretation vs future runs):**
- Keep v1 snapshots under `2_Data/metadata/legacy/` and `2_Data/processed/legacy/` for S0 interpretability.
- Promote v2 artifacts to the default names only when you intentionally switch the operational SSOT.

---

### Document Organization & Cleanup (2025-12-20)

**Full document organization completed:**
- ✅ All subfolder documents organized and structured
- ✅ Conflict documents resolved and marked as Historical Reference
- ✅ Superseded documents clearly marked
- ✅ Filename cleanup completed (`Prompt_Rendering_Safety_Rule.md`)
- ✅ Document status classification clarified (Canonical / Reference / Historical Reference)

**Major cleanup work:**
- `00_Governance/`: Document status clarified, relationships organized
- `01_Execution_Safety/`: Filename cleanup, duplicate removal
- `02_Arms_and_Models/`: Superseded documents clarified
- `03_CardCount_and_Allocation/`: Experimental documents clarified
- `04_Step_Contracts/`: Superseded documents marked
- `05_Pipeline_and_Execution/`: README updated, deprecated items marked
- `06_QA_and_Study/`: S0 Non-Inferiority policy unified

**Cleanup summary documents:**
- Cleanup summary documents archived to respective `archived/` folders (2026-01-04)

---

### S3 & S4 Implementation Updates (2025-12-20)

**S3 (Policy Resolver & ImageSpec Compiler):**
- Q2 image policy change: Q2 now also requires images (`image_required = True`)
- S1 table visual spec added: Group-level table/visual image generation support
- Prompt improvements: Enhanced image generation quality by including card text (front/back) and extracted answers
- Answer extraction logic: Q1 uses "Answer:" parsing, Q2/Q3 use `correct_index`-based extraction

**S4 (Image Generator):**
- Image generation model changed: `models/nano-banana-pro-preview` (Gemini 3 Pro Image Preview)
- Spec type branching: Card images (4:5, 1K) vs table visuals (16:9, 2K)
- Fail-fast extended: Q2 and table visuals also treated as required images
- Image extraction logic improved: PNG header validation and debugging enhanced

**Pipeline tools:**
- `run_6arm_s1_s2_full.py`: Added `--arms` option (select specific arms only)
- Report storage location changed: `2_Data/metadata/generated/{run_tag}/` directory
- `check_models.py`: Updated to `google.genai` SDK

**Documentation:**
- `S3_S4_Code_Documentation.md`: Complete code behavior documentation
- `0_Protocol/04_Step_Contracts/Step03_S3/S3_Implementation_Update_Log_2025-12-20.md`
- `0_Protocol/04_Step_Contracts/Step04_S4/S4_Implementation_Update_Log_2025-12-20.md`
- `0_Protocol/05_Pipeline_and_Execution/Implementation_Update_Log_2025-12-20.md`

**Detailed information:**
- Implementation log: `0_Protocol/00_Governance/archived/Implementation_Change_Log_2025-12-20.md` (archived)
- Code documentation: `0_Protocol/04_Step_Contracts/S3_S4_Code_Documentation.md`

---

### Experimental Stabilization of S2 Batch Failures

- `03_CardCount_and_Allocation/Experimental/S0_STABILIZE_MULTI_Allocation_Artifact_Spec.md`
- `01_Execution_Safety/stabilization/S2_Stabilization_Plan_and_Preflight_Checks.md`

---

## 10. Repository Structure

```
MeducAI/
├── 0_Protocol/                  # [READ-ONLY] Canonical Protocols & Governance
│   ├── 00_Governance/           # Governance documents, cleanup summaries
│   ├── 01_Execution_Safety/     # Safety rules and policies
│   ├── 02_Arms_and_Models/      # Arm configurations and model specifications
│   ├── 03_CardCount_and_Allocation/  # Card count policies
│   ├── 04_Step_Contracts/       # Step contracts (S1-S4)
│   ├── 05_Pipeline_and_Execution/    # Pipeline execution plans
│   └── 06_QA_and_Study/         # QA framework and study design
├── 1_Secure_Participant_Info/   # [RESTRICTED] PII, Consent Forms (IRB)
├── 2_Data/                      # Data and metadata
│   ├── metadata/
│   │   ├── generated/           # Runtime artifacts (excluded from git)
│   │   └── legacy/              # Archived legacy metadata
│   └── processed/               # Processed curriculum data (SSOT)
├── 3_Code/                      # Source Code & Pipelines
│   ├── src/                     # Main source code
│   │   └── tools/               # Utility tools and QA scripts
│   ├── Scripts/                 # Execution scripts
│   │   └── legacy/              # Archived scripts
│   ├── configs/                 # Configuration files
│   │   └── legacy/              # Archived configs
│   └── notebooks/               # Jupyter notebooks
│       └── legacy/              # Archived notebooks
└── 6_Distributions/             # QA Packages (Blinded/Unblinded)
    └── MeducAI_Final_Share/
        └── PDF/
            └── print_ready/     # 프린팅용 PDF (4권 분권, 인쇄 주문 안내 포함)
```

---

## 11. Getting Started

### Prerequisites

- Python 3.8+
- GitHub account (for private repository access)
- Access credentials for LLM providers (Gemini, OpenAI, etc.)

### Initial Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Yoojin-nam/MeducAI.git
   cd MeducAI
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. Review Canonical documents:
   - Start here: `0_Protocol/README.md`
   - Start with: `0_Protocol/00_Governance/meduc_ai_pipeline_canonical_governance_index.md`
   - Check operating status: `0_Protocol/01_Execution_Safety/stabilization/Weekly_Integrated_Conclusion_Operating_SSOT.md`

---

## 12. Key Documents

### For Understanding the Pipeline

- `0_Protocol/README.md` - Start-here reading order (minimal set)
- `0_Protocol/00_Governance/meduc_ai_pipeline_canonical_governance_index.md` - Canonical document hierarchy
- `0_Protocol/05_Pipeline_and_Execution/Pipeline_Canonical_Specification.md` - Pipeline philosophy
- `0_Protocol/05_Pipeline_and_Execution/Pipeline_Execution_Plan.md` - Execution plan

### For QA and Study Design

- `0_Protocol/06_QA_and_Study/MeducAI_3Paper_Research_Index.md` - 3-Paper 연구 마스터 인덱스
- `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/QA_Framework.md` - QA framework
- `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/Paper1_Paper2_Research_Design_Spec.md` - Paper 1+2 연구 설계
- `0_Protocol/06_QA_and_Study/Paper3_Educational_Effectiveness/Paper3_Study_Design.md` - Paper 3 연구 설계

### For Printing and Distribution

- `6_Distributions/MeducAI_Final_Share/PDF/print_ready/` - 프린팅용 PDF (4권 분권)
    - 인쇄 주문 시 사용할 수 있는 분권된 PDF 파일
    - 각 권별 표지, 페이지 수, 포함 전문의 정보 제공
    - 상세한 인쇄 주문 방법 및 메일 템플릿 포함
    - 자세한 내용은 `print_ready/README.md` 참고

### For Research Papers

**Paper 1 (S5 Multi-agent 신뢰도):**
- `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/Paper1_Paper2_Research_Design_Spec.md`
- `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/Paper1_QA_Endpoints_Definition.md`
- `0_Protocol/05_Pipeline_and_Execution/S5_Decision_Definition_Canonical.md`

**Paper 2 (MLLM 이미지 신뢰도):**
- `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/Paper1_Paper2_Research_Design_Spec.md` (Section 8: Visual Modality)
- `0_Protocol/06_QA_and_Study/Paper2_Image_Reliability/Paper2_Table_Infographic_Evaluation_Design.md`
- `0_Protocol/06_QA_and_Study/Paper2_Image_Reliability/Paper2_Visual_Turing_Test_Design_Detailed.md`

**Paper 3 (교육효과 전향적 연구):**
- `0_Protocol/06_QA_and_Study/Paper3_Educational_Effectiveness/Paper3_Study_Design.md`
- `0_Protocol/06_QA_and_Study/Paper3_Educational_Effectiveness/Paper3_Survey_Overview.md`
- `0_Protocol/06_QA_and_Study/Paper3_Educational_Effectiveness/Paper3_Statistical_Analysis_Plan.md`

### For Prompt Governance (Cognitive Alignment)

- `0_Protocol/00_Governance/supporting/Prompt_governance/Prompt_Engineering_and_Cognitive_Alignment.md` - Prompt governance SSOT (Methods-ready + change control)
- `3_Code/prompt/_registry.json` - Current active prompt bundle (code truth)

### For IRB and Compliance

- `0_Protocol/IRB/README.md` - IRB documentation index
- `0_Protocol/01_Execution_Safety/Prompt_Rendering_Safety_Rule.md` - Prompt safety rules

---

## 13. Contributing

This is a private research repository. Access is limited to authorized collaborators.

For co-authors and collaborators:
1. Contact the repository owner for access
2. Review the Canonical documents before making changes
3. Follow the Fail-Fast policy and document any modifications
4. Update relevant documentation when making protocol changes

---

## 14. License

This project is part of a research study. All rights reserved.

---

## 15. Contact

For questions about the pipeline, protocol, or access requests, please contact the principal investigator.

---

**Last Updated**: 2026-03-30
**Frozen Tag**: `protocol-freeze-v1.3`
**Default Branch**: `protocol-freeze-main`

아래는 요청하신 대로 **“바로 붙여넣기 가능한 Canonical v1.1 개정안”**입니다.
현재 코드 현실(01/02/03), MI-CLEAR-LLM 요구사항, 그리고 **JSONL Contract-First 전략**이 **충돌 없이 실행 가능**하도록 정리했습니다.

이 문서는 그대로 `0_Protocol/Pipeline_Execution_Plan.md`에 덮어써도 됩니다.

---

````markdown
# MeducAI – Pipeline Execution Plan (JSONL Contract-First)

**Version:** 1.1 (Canonical)  
**Date:** 2025-12-16  
**Status:** Canonical (S0/S1 Freeze Target)  
**Scope:** Pipeline-1 (S0/S1) Content Generation, Visualization, QA, Distribution  
**Supersedes:** v1.0 Draft

**Related Documents:**
- `Pipeline_Canonical_Specification.md` - Pipeline philosophy and entity definitions
- `04_Step_Contracts/` - Step-specific contracts and schemas

---

## 0. Executive Summary

본 문서는 MeducAI Pipeline-1의 **유일한 실행 계약(Execution Contract)**을 정의한다.  
본 파이프라인에서 **Step01이 생성하는 JSONL은 절대 계약(Absolute Contract)**이며,  
Step02–05는 해당 JSONL을 **소비(consumption)**만 한다.

* **Single Source of Truth:** JSONL
* **CSV:** Optional, Read-only, Human-QA View
* **Image / Anki / Distribution 실패는 허용하되, JSONL 계약 실패는 허용하지 않는다.**

---

## 1. Core Principles

### 1.1 JSONL Contract-First

* Step01 출력 JSONL은 파이프라인의 **유일한 진실**이다.
* Downstream 단계는 JSONL 구조 변경을 요구할 수 없다.
* 구조 변경은 **Protocol 개정(vX.X)** 없이는 불가하다.

### 1.2 Group-First Invariant

* 처리 최소 단위는 **Group**
* Table / Entity / Anki Card는 **동일 group_id에 결속**된다.

### 1.3 RUN_TAG-Centric Execution

* 모든 산출물은 `<run_tag>` 기준으로 완전히 분리된다.
* provider / arm 은 **파일명과 metadata에만 존재**하며 폴더 분리는 하지 않는다.

---

## 2. MI-CLEAR-LLM Traceability (Mandatory)

모든 JSONL 레코드는 아래 메타데이터를 **반드시 포함**해야 한다  
(값이 없는 경우 빈 문자열이라도 키는 존재해야 함).

### 2.1 Required Metadata Fields

```json
{
  "run_tag": "S0_RUN_20251216",
  "timestamp": "2025-12-16T12:00:00Z",
  "provider": "gemini",
  "model_name": "gemini-1.5-pro-002",
  "arm": "C",

  "code_git_commit": "abc1234",
  "prompt_bundle_hash": "f0e1d2c3",
  "prompt_file_ids": {
    "table": "prompt/table_v3.md",
    "entity": "prompt/entity_v2.md",
    "anki": "prompt/anki_v4.md"
  },

  "generation_config": {
    "temperature": 0.2,
    "top_p": 0.9,
    "seed": 42
  }
}
````

### 2.2 Run-Level Manifest (Required)

* 위치:

  ```
  2_Data/metadata/generated/<run_tag>/run_manifest_<run_tag>__armX.json
  ```
* 목적:

  * MI-CLEAR-LLM 감사
  * 비용/시간/모델 고정 근거
  * 논문 Methods 재현성 보장

---

## 3. Step01 JSONL Contract (Minimum & Frozen)

### 3.1 File Pattern

```
2_Data/metadata/generated/<run_tag>/output_<provider>_<run_tag>__armX.jsonl
```

* One line = One Group

---

### 3.2 Root Structure

```json
{
  "metadata": {
    "group_id": "G_001",
    "... MI-CLEAR fields ..."
  },

  "source_info": {
    "specialty": "Chest",
    "anatomy": "Lung",
    "modality_or_type": "CT",
    "category": "",
    "group_key": "Chest-Lung-CT",
    "weight": 1.42,
    "split_index": 12
  },

  "curriculum_content": {
    "visual_type": "table",

    "table_infographic": {
      "infographic_style": "anatomical_map",
      "title_en": "TNM Staging of Lung Cancer",
      "key_elements": ["T1", "T2", "Pleura"],
      "prompt_en": "High-quality medical infographic showing..."
    },

    "entities": [ ... ]
  }
}
```

---

## 4. Infographic Strategy (Group Level)

### 4.1 infographic_style (Enum – Frozen)

Allowed values:

```
anatomical_map
flowchart
matrix
staging_map
timeline
checklist
physics_diagram
physics_graph
radiograph_style
ct_mri_style
default
```

### 4.2 Style Selection Rules

* Location / Anatomy → `anatomical_map`
* Diagnostic algorithm / guideline → `flowchart`
* Differential diagnosis → `matrix`
* TNM / grading → `staging_map`
* Physics / dose / curves → `physics_graph` / `physics_diagram`

---

## 5. Entity Contract (Row-Level)

### 5.1 Entity Minimum Contract

```json
{
  "entity_name": "Adenocarcinoma",
  "importance_score": 50,

  "row_image_necessity": "IMG_REQ",

  "visual_context": {
    "modality": "CT",
    "view": "Axial",
    "contrast": "contrast",
    "key_findings": ["spiculation", "peripheral nodule"],
    "finding_description_en": "Peripheral spiculated nodule in upper lobe",
    "row_image_prompt_en": "High-resolution axial CT image showing..."
  },

  "anki_cards": [ ... ]
}
```

### 5.2 Image Necessity Logic

* `IMG_REQ` → 반드시 이미지 생성
* `IMG_OPT` → include_opt 옵션에서만 생성
* `IMG_NONE` → 절대 생성 안 함

---

## 6. Anki Card Contract

### 6.1 Minimum Card Fields

```json
{
  "card_type": "Basic",
  "front": "What is the most common subtype of lung cancer?",
  "back": "Adenocarcinoma",
  "tags": ["ct_basic", "Chest"]
}
```

### 6.2 Validation Rules

* `front` or `back` 공백 → 카드 삭제
* 삭제율 > 10% → Step01 실패 처리

---

## 7. Pipeline Step Responsibilities

### Step 01 – Generation (Creator)

* Input: `groups.csv`, weight tables
* Output: **output_*.jsonl** (or `stage1_struct__arm{X}.jsonl` when using `--stage 1`)
* Responsibility:

  * Medical correctness
  * Reasoning
  * JSONL Contract validation (Hard-Fail)

**Execution Modes (2025-12-19):**
* `--stage 1`: S1만 실행 (Group-level 구조 생성)
* `--stage 2`: S2만 실행 (기존 S1 출력 읽기)
* `--stage both`: S1+S2 통합 실행 (기본값)

---

### Step 02 – Flattening (Viewer, Optional)

* Input: `output_*.jsonl`
* Output: CSV views

  * `anki_cards_*.csv`
  * `image_prompts_*.csv`
  * `table_infographic_prompts_*.csv`
* Failure here **does not stop pipeline**

---

### Step 03 – Visualization (Artist)

* Input: `output_*.jsonl`
* Logic:

  * Group → table_infographic → 1 image
  * Entity → IMG_REQ → clinical images
* Output:

  ```
  2_Data/images/generated/<run_tag>/
  ```

---

### Step 04/05 – Packaging & Distribution (Distributor)

* Input: JSONL + images
* CSV 사용은 optional
* 이미지 실패 시 **text-only deck 생성 가능해야 함**

---

## 8. Validation & Freeze Policy (S0)

### 8.1 Hard-Fail Conditions

* `table_infographic.prompt_en` missing
* `IMG_REQ` but `row_image_prompt_en` missing
* MI-CLEAR metadata missing
* JSON schema violation

### 8.2 S0 Freeze Conditions

* Step01 validator 100% pass
* Step03 table + entity 이미지 최소 1개 이상 생성
* Step04 text-only deck 생성 가능
* Configuration Log 업데이트 완료

---

## 9. Final Statement

> **Step01 JSONL is law.**
> Everything else is a view, an interpretation, or a distribution.
>
> This contract is frozen for S0/S1 unless formally revised.

---

## 10. S1 Schema/Structure Complete Freeze Declaration (2025-12-19)

**Effective Date:** 2025-12-19

### 10.1 Freeze Status

The S1 output schema (`stage1_struct.jsonl`) and structure are **completely frozen** as of this date:

- ✅ **Schema version 1.3 is final** - No further structural changes permitted
- ✅ **All required fields, types, and constraints are locked**
- ✅ **Enum values are fixed** - `visual_type_category` enum is final
- ✅ **Entity structure is fixed** - `entity_list` format is final
- ✅ **Master table format constraints are fixed**

### 10.2 What Remains Mutable

The following are **explicitly allowed** for future improvement:

- ✅ **S1 Prompts** - Prompt text improvements are planned and allowed
- ✅ **Prompt instructions and examples** - Can be refined to improve output quality
- ✅ **Validation error messages** - Can be improved for better debugging

### 10.3 Pipeline Readiness

With S1 schema/structure frozen, the pipeline is **ready to proceed** to downstream stages (S2, S3, S4) with a stable contract.

```

---

### 다음 자연스러운 액션 (권장 순서)

1. 이 문서를 **Canonical로 commit**
2. `01_generate_json.py`에 이 스키마를 그대로 반영한 **validator 고정**
3. 1–2 groups로 **golden JSONL 생성**
4. Step03/04를 golden JSONL로 끝까지 smoke test

지금 상태에서는 **문서 → 코드 → 실험**의 순서가 완전히 정렬되었습니다.  
다음으로는 원하시면 **Step01 validator 코드(Pydantic/순수 Python)**를 이 문서에 정확히 대응시켜 드리겠습니다.

---

## 11. S1/S2 독립 실행 기능 (2025-12-19 추가)

### 11.1 구현 상태

✅ **구현 완료**: `01_generate_json.py`에 `--stage` 옵션 추가

### 11.2 사용법

**S1만 실행:**
```bash
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag TEST_20251219 \
  --arm A \
  --mode S0 \
  --stage 1
```

**S2만 실행 (S1 출력 필요):**
```bash
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag TEST_20251219 \
  --arm A \
  --mode S0 \
  --stage 2
```

**S1+S2 통합 실행 (기본값):**
```bash
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag TEST_20251219 \
  --arm A \
  --mode S0 \
  --stage both  # 또는 생략 (기본값)
```

### 11.3 워크플로우

**권장: S1 → S2 분리 실행**
1. Stage 1: 모든 arm 실행
2. S1 Gate 검증
3. Allocation 생성 (S0 모드)
4. Stage 2: 모든 arm 실행

이 방식의 장점:
- S1 완료 후 검증 가능
- S2 실패 시 S1 재실행 불필요
- 병렬 처리 유연성 향상

자세한 내용은 `05_Pipeline_and_Execution/S1_S2_Independent_Execution_Design.md` 참조.
```
## Appendix F. Generator–QA Layer Separation

The MeducAI pipeline enforces a conceptual separation between:
- Content generation (Step01; JSONL creation), and
- Quality assurance and evaluation layers (S0/S1 and beyond).

Once the JSONL contract is satisfied, alternative QA systems may be applied without modifying or regenerating content.

This design explicitly supports future studies comparing different QA architectures while holding the generator constant.

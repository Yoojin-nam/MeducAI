# Code ↔ Protocol Traceability Map

## Current Tree + Step02 Minimal + Runtime Manifest (v1.3)

**Status:** Canonical
**Version:** v1.6
**Last Updated:** 2025-12-20
**Scope:** Step01 implemented, Allocation implemented (detached), Step02 execution via `--stage` option (implemented), Step03 implemented (policy resolver + table visual), Step04 implemented (image generator with nano-banana-pro), Step05 implemented (validator), Step06 implemented (PDF + Anki packaging)
**Purpose:** Audit · Reproducibility · IRB / MI-CLEAR-LLM compliance

---

## 0. v1.6 변경점 (v1.5 대비)

### 추가 (2025-12-20, 저녁)

1. **샘플 PDF/Anki 생성 스크립트 추가**:
   - `generate_sample_pdf_anki.py`: Specialty별 랜덤 그룹 선택하여 개별 PDF/Anki 생성
   - `generate_sample_all_specialties.py`: 모든 specialty 통합 PDF/Anki 생성
   - `test_6arm_single_group.py`: 단일 그룹에 대한 6-arm 전체 파이프라인 테스트

2. **S3 에러 처리 개선**:
   - 카드 이미지 스펙 생성 실패 시에도 테이블 비주얼 스펙 생성 계속
   - 샘플 PDF 생성 시 일부 그룹의 카드 이미지 실패해도 Infographic 생성 가능

3. **S4 선택적 생성 옵션**:
   - `--only-infographic` 옵션 추가: Infographic만 생성하고 카드 이미지는 스킵

4. **Entity ID 형식 정규화**:
   - PDF와 Anki export에서 `entity_id` 형식 불일치 해결 (DERIVED:xxx vs DERIVED_xxx)
   - `load_s4_image_manifest()`와 `build_cards_section()`에서 정규화 적용
   - 정상 생성된 manifest와 재생성된 manifest 모두 호환

5. **통합 PDF 헤더 개선**:
   - 좌측 상단에 `Specialty - region - category` 형식만 표시 (간소화)
   - 불필요한 "Specialty: ...", "Group: ..." 헤더 제거

6. **S4 Manifest 재생성 스크립트**:
   - `regenerate_s4_manifest.py`: 기존 이미지 파일로부터 manifest 재생성
   - S3 spec의 원본 entity_id 형식 유지

7. **Anki Export 개선**:
   - `--allow_missing_images` 옵션 추가: 샘플/디버그 생성 시 이미지 누락 허용 (운영용 escape hatch; 품질 게이트는 Option C로 일원화)
   - Entity ID 정규화 적용

---

## 0-A. v1.5 변경점 (v1.4 대비)

### 추가 (2025-12-20, 오후)

1. **Step03 (S3) 업데이트**:
   - Q2 이미지 정책 변경: `image_required = True` (필수)
   - S1 테이블 비주얼 스펙 컴파일 추가 (`spec_kind = "S1_TABLE_VISUAL"`)
   - 프롬프트 개선: 카드 텍스트(front/back)와 정답 포함
   - 정답 추출 로직 추가 (`extract_answer_text()`)
   - S1 테이블 행 데이터를 컨텍스트로 활용

2. **Step04 (S4) 업데이트**:
   - 이미지 생성 모델 변경: `models/nano-banana-pro-preview` (Gemini 3 Pro Image Preview)
   - 스펙 종류별 분기 처리: 카드 이미지(4:5, 1K) vs 테이블 비주얼(16:9, 2K)
   - 파일명 규칙 확장: 테이블 비주얼 `IMG__{run_tag}__{group_id}__TABLE.png`
   - Fail-fast 규칙 확장: Q2와 테이블 비주얼도 필수
   - 이미지 추출 로직 개선: PNG 헤더 검증, 디버깅 강화

3. **Step05 (S5) 구현 완료**:
   - `07_build_set_pdf.py`: S0 QA용 PDF 패킷 빌더 구현
     - S1 Master Table → S1 Infographic → S2 Cards (12장) 순서로 PDF 구성
     - Image placement 기반 이미지 배치 (FRONT/BACK/NONE)
     - Blinded mode 지원 (surrogate set_id 사용)
   - `07_export_anki_deck.py`: Anki 덱 익스포터 업데이트
     - S4 image manifest 기반 이미지 매핑
     - Role-based image placement (2-card policy: Q1: Back, Q2: Back)
     - Missing image policy (Q1: FAIL, Q2: FAIL)

4. **파이프라인 실행 도구 개선**:
   - `run_6arm_s1_s2_full.py`: `--arms` 옵션 추가 (특정 arm만 선택 실행)
   - 리포트 저장 위치 변경: `2_Data/metadata/generated/{run_tag}/` 디렉토리
   - `check_models.py`: `google.genai` SDK로 업데이트

5. **문서화**:
   - `S3_S4_Code_Documentation.md` 작성 (프로젝트 루트)
   - S3/S4 구현 업데이트 로그 작성

---

## 0-A. v1.4 변경점 (v1.3 대비)

### 추가 (2025-12-20, 오전)

1. **Step03 (S3) Policy Resolver 구현 완료**: `03_s3_policy_resolver.py` 구현
   - S2 결과를 읽어서 image policy 적용
   - `image_policy_manifest.jsonl` 생성 (모든 카드에 대한 정책)
   - `s3_image_spec.jsonl` 생성 (Q1/Q2에 대한 이미지 스펙)
   - Q1: image_hint 필수 검증
   - Q2: image_hint optional (없으면 스킵) → **v1.5에서 필수로 변경됨**
   - (Legacy) Q3 image_hint 금지 검증 (현재 파이프라인은 Q3를 생성/수용하지 않음)
   - Deterministic join key 사용: `(run_tag, group_id, entity_id, card_role)`

2. **Step04 (S4) Image Generator 구현 완료**: `04_s4_image_generator.py` 구현
   - Gemini 이미지 생성 API 통합 (`gemini-2.5-flash-image`) → **v1.5에서 nano-banana-pro-preview로 변경됨**
   - S3 image spec을 읽어서 이미지 생성
   - Deterministic 파일명: `IMG__{run_tag}__{group_id}__{entity_id}__{card_role}.png`
   - `s4_image_manifest.jsonl` 생성 (카드-이미지 매핑)
   - Q1 이미지 누락 시 FAIL-FAST
   - Q2 이미지 누락 시 경고만 (optional) → **v1.5에서 FAIL-FAST로 변경됨**
   - (Legacy) Q3 이미지 존재 시 FAIL (현재 파이프라인은 Q3를 생성/수용하지 않음)

3. **Anki Exporter 업데이트**: `07_export_anki_deck.py` 업데이트
   - S4 image manifest 기반 이미지 배치
   - Role-based image placement (2-card policy: Q1: Back, Q2: Back)
   - Missing image policy 적용

4. **6-Arm 테스트 스크립트 확장**: `run_6arm_s1_s2_full.py` 업데이트
   - S3, S4 단계 추가
   - 전체 파이프라인 (S1→S2→S3→S4) 테스트 지원
   - 리포트에 S3, S4 상태 포함

5. **S2 안정화 완료**:
   - 정확히 2 cards per entity 강제 (Q1/Q2, 2-card policy)
   - 5-option MCQ 검증 (Q2)
   - Deictic image reference 검증 (Q2 금지)
   - Image hint compliance 검증

6. **코드 품질 개선**:
   - S4 클라이언트 생성 실패 시 명시적 에러 처리
   - .env 파일 로딩 실패 시 경고 메시지 추가
   - Invalid JSON line 스킵 시 통계 보고

### 유지

* Allocation의 카드 수 결정 권한 단독 원칙 유지(CP-1)
* (Deprecated) runtime_manifest 개념은 문서상 존재했으나, 현재 트리에는 구현이 포함되지 않음

## 0-A. v1.3 변경점 (v1.2 대비)

### 추가 (2025-12-19)

1. **Step02 실행 기능 구현 완료**: `01_generate_json.py`에 `--stage` 옵션 추가
   - `--stage 1`: S1만 실행
   - `--stage 2`: S2만 실행 (기존 S1 출력 읽기)
   - `--stage both`: S1+S2 통합 실행 (기본값)
2. **S1/S2 독립 실행 검증 완료**: 6 arm 테스트 성공
3. **S2 스키마 v3.1 반영**: `card_role` 및 `image_hint` 필드 추가 (현재 파이프라인은 2-card policy로 Q1/Q2만 허용)
   - Q1: image_hint 필수
   - Q2: image_hint 권장
   - (Legacy) Q3: image_hint 금지 (현재 파이프라인은 Q3를 생성/수용하지 않음)
4. **Gemini 3 모델 지원**: `thinking_level` 파라미터 사용 (minimal/high)
   - Arm A-D: gemini-3-flash-preview
   - Arm E: gemini-3-pro-preview
   - Arm F: gpt-5.2-2025-12-11 (non-pro, Responses API)

## 0-B. v1.2 변경점 (v1.1 대비)

### 추가

1. **Step02 최소 runner "정의 완료(Implement-Ready)"**: 파일명/입출력/게이트/산출물 경로를 고정
2. (Deprecated) runtime_manifest / generated_paths 설계는 현재 트리에 포함되지 않음 (현행은 S2 results path resolver 중심)

---

## 1. Authoritative Directory Snapshot

### 1.1 Code (Current + v1.4 fixed additions)

```text
3_Code/src/
├── 01_generate_json.py               (v1.3: --stage 옵션 추가, S1/S2 독립 실행 지원)
├── 03_s3_policy_resolver.py          (v1.5: S3 policy resolver + table visual 구현 완료)
├── 04_s4_image_generator.py           (v1.5: S4 image generator with nano-banana-pro 구현 완료)
├── 05_s5_validator.py                (v1.6: validation/triage 구현)
├── 07_build_set_pdf.py               (v1.5: S0 QA PDF builder)
├── 07_export_anki_deck.py            (v1.5: Anki exporter)
└── tools/
    ├── path_resolver.py              (S2 results path resolver: new/legacy formats)
    └── allocation/
        └── s0_allocation.py          (S0 allocation artifact builder/validator)
```

### 1.2 Runtime Artifacts (RUN_TAG root)

```text
2_Data/metadata/generated/{RUN_TAG}/
├── allocation/
│   └── allocation_s0__group_{GROUP_ID}__arm_{ARM}.json
├── stage1_struct__arm{ARM}.jsonl
├── s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl   (preferred, 2025-12-23+)
├── s2_results__arm{ARM}.jsonl                       (legacy, backward compatible)
├── image_policy_manifest__arm{ARM}.jsonl
├── s3_image_spec__arm{ARM}.jsonl
├── s4_image_manifest__arm{ARM}.jsonl
└── images/
    └── IMG__{run_tag}__{group_id}__{entity_id}__{card_role}.png
```

---

## 2. Traceability Map (v1.2)

---

## 2.1 Pipeline Entrypoint · Step01 (Implemented)

| 항목                         | 내용                                                                                                                                  |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **Area**                   | Pipeline Entrypoint · Step01                                                                                                        |
| **Code Path**              | `3_Code/src/01_generate_json.py`                                                                                                    |
| **Primary Canonical Docs** | - `04_Step_Contracts/Step01_S1_Output_Contract_Canonical.md`<br>- `05_Pipeline_and_Execution/Pipeline_FailFast_and_Abort_Policy.md` |
| **Secondary Docs**         | - `05_Pipeline_and_Execution/Runtime_Artifact_Manifest_Spec.md`                                                                     |
| **Implemented Invariants** | Step01은 콘텐츠 생성 단계, quota 결정 금지, JSONL 1-record/line                                                                                 |
| **Hard Gates**             | empty output/parse/schema violation → FAIL                                                                                          |
| **Runtime Artifacts**      | `{RUN_TAG}/stage1_struct__arm{ARM}.jsonl`                                                                                           |
| **Verification Hooks**     | CP-2, CP-3                                                                                                                          |
| **Status**                 | ✅ Implemented                                                                                                                       |

---

## 2.2 Allocation (S0) — CardCount Authority (Implemented, Detached)

| 항목                         | 내용                                                                |
| -------------------------- | ----------------------------------------------------------------- |
| **Area**                   | Allocation (S0)                                                   |
| **Code Path**              | `3_Code/src/tools/allocation/s0_allocation.py`                    |
| **Primary Canonical Docs** | `03_CardCount_and_Allocation/S0_Allocation_Artifact_Spec_v2.0.md` |
| **Implemented Invariants** | 카드 수 결정 권한 단독, set 단위 fixed payload                               |
| **Hard Gates**             | quota sum mismatch / schema invalid → FAIL                        |
| **Runtime Artifacts**      | `{RUN_TAG}/allocation/allocation_s0__group_{G}__arm_{A}.json`     |
| **Verification Hooks**     | CP-1                                                              |
| **Status**                 | ✅ Implemented (01과 분리)                                            |

---

## 2.3 Runtime Path & Artifact Routing (Implemented)

| 항목                         | 내용                                                            |
| -------------------------- | ------------------------------------------------------------- |
| **Area**                   | Runtime Infrastructure                                        |
| **Code Path**              | `3_Code/src/tools/path_resolver.py` (S2 results path only; new/legacy compatibility) |
| **Primary Canonical Docs** | `05_Pipeline_and_Execution/Runtime_Artifact_Manifest_Spec.md` |
| **Implemented Invariants** | S2 results 파일명은 new/legacy 포맷을 모두 지원하며, 읽기 시 우선순위로 해석한다. |
| **Hard Gates**             | S2 결과 파일 미존재 / 경로 해석 실패 → FAIL (해당 consumer 단계에서) |
| **Runtime Artifacts**      | `s2_results__*.jsonl` (resolver 적용 대상)                     |
| **Verification Hooks**     | CP-0                                                          |
| **Status**                 | ✅ Implemented                                                 |

### v1.6 운영 규칙 (S2 Results Path Resolver)

* S2 결과 파일은 **가능하면 new format**(`s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl`)을 사용한다.
* consumer(S3/S5/PDF/Anki)는 **`tools/path_resolver.py`**를 통해 new/legacy를 우선순위로 해석한다.

---

## 2.4 Step02 — Entity-level Execution (v1.3: Implemented via --stage option)

| 항목                         | 내용                                                                                                                    |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **Area**                   | Step02 (Entity Execution)                                                                                             |
| **Code Path**              | `3_Code/src/01_generate_json.py` (with `--stage 2` option)                                                           |
| **Primary Canonical Docs** | `04_Step_Contracts/Step02_S2_Execution_Contract_Canonical.md`                                                         |
| **Secondary Docs**         | `03_CardCount_and_Allocation/S0_Allocation_Artifact_Spec_v2.0.md`                                                     |
| **v1.3 Implementation**    | - `--stage 2` 옵션으로 S2만 실행 가능<br>- 기존 S1 출력 (`{RUN_TAG}/stage1_struct__arm{X}.jsonl`) 읽기<br>- Allocation artifact (`{RUN_TAG}/allocation/*.json`) 읽기 |
| **Canonical Invariants**   | - allocation이 준 N을 **정확히 집행(len==N)**<br>- 콘텐츠 수정/재생성 금지(단, S2가 생성자라면 "재생성"이 아니라 "생성"이므로 문서 정의에 맞추어 S2의 역할을 분명히 해야 함) |
| **Hard Gates**             | - len(cards_out) ≠ allocated_N → FAIL<br>- required fields 누락 → FAIL<br>- S1 출력 파일 없음 → FAIL (S2-only 모드) |
| **Runtime Artifacts**      | `{RUN_TAG}/s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl` (new format, 2025-12-23)<br>`{RUN_TAG}/s2_results__arm{X}.jsonl` (legacy, backward compatible)<br>(schema: `S2_RESULTS_v3.1`)                                                      |
| **Verification Hooks**     | CP-2 (schema), CP-3 (권한/역할 경계)                                                                                        |
| **Status**                 | ✅ Implemented (v1.3: `--stage` 옵션으로 구현 완료, 테스트 검증 완료)                                                              |
| **Schema Version**         | `S2_RESULTS_v3.1` (card_role, image_hint 필드 포함)                                                                  |
| **Note**                   | 별도 스크립트(`02_execute_entities.py`) 분리는 향후 선택사항. 현재는 `--stage` 옵션으로 충분히 작동함.                              |

> **중요(감사 대비 문구)**
> Step02의 “정확히 N 집행”은 **Allocation의 결정권을 침범하지 않기 위한 핵심 통제점**이다.
> 따라서 N이 부족하면 “완화”가 아니라 **하드 실패**가 정석이다.

---

## 2.5 Runtime Manifest (v1.2: Implement-Ready)

> (Deprecated) `runtime_manifest.json`은 과거 문서에서 "implement-ready"로 정의되었으나, **현재 코드 트리에는 구현이 포함되지 않습니다.**

---

## 2.6 Step03 — Policy Resolver (v1.5: Implemented)

| 항목                         | 내용                                                                                                                    |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **Area**                   | Step03 (Policy Resolver & ImageSpec Compiler)                                                                                              |
| **Code Path**              | `3_Code/src/03_s3_policy_resolver.py`                                                                                 |
| **Primary Canonical Docs** | - `04_Step_Contracts/S3_to_S4_Input_Contract_Canonical.md`<br>- `04_Step_Contracts/Step03_S3/Entity_Definition_S3_Canonical.md`<br>- `04_Step_Contracts/S3_S4_Code_Documentation.md` |
| **v1.5 Implementation**    | - S2 결과 (`s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl` 또는 legacy `s2_results__arm{X}.jsonl`) 읽기<br>- S1 구조 (`stage1_struct__arm{X}.jsonl`) 읽기<br>- Image policy 적용 (2-card policy: Q1: BACK, Q2: BACK)<br>- Image spec 컴파일 (Q1/Q2 + S1 테이블 비주얼)<br>- `image_policy_manifest__arm{X}.jsonl` 생성<br>- `s3_image_spec__arm{X}.jsonl` 생성<br>- 프롬프트 개선: 카드 텍스트(front/back)와 정답 포함 |
| **Canonical Invariants**   | - State-only (content 생성/수정 금지)<br>- Q1 image_hint 필수 검증<br>- Q2 image_hint 필수 검증<br>- card_role은 Q1/Q2만 허용<br>- S1 테이블 비주얼 스펙 컴파일 (그룹당 1개) |
| **Hard Gates**             | - Q1 image_hint 누락 → FAIL<br>- Q2 image_hint 누락 → FAIL<br>- Q1/Q2 modality/anatomy/keywords 누락 → FAIL<br>- unknown card_role → FAIL<br>- S2 출력 파일 없음 → FAIL<br>- 테이블 비주얼 스펙 컴파일 실패 → FAIL |
| **Runtime Artifacts**      | `{RUN_TAG}/image_policy_manifest__arm{X}.jsonl`<br>`{RUN_TAG}/s3_image_spec__arm{X}.jsonl` (Q1/Q2 카드 이미지 + S1 테이블 비주얼) |
| **Verification Hooks**     | CP-2 (schema), CP-3 (권한/역할 경계)                                                                                        |
| **Status**                 | ✅ Implemented (v1.5: Q2 필수화, 테이블 비주얼 추가, 프롬프트 개선 완료)                                                                              |

---

## 2.7 Step04 — Image Generator (v1.5: Implemented)

| 항목                         | 내용                                                                                                                     |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Area**                   | Step04 (Image Generator)                                                                                              |
| **Code Path**              | `3_Code/src/04_s4_image_generator.py`                                                                                   |
| **Primary Canonical Docs** | - `04_Step_Contracts/Step04_S4/Entity_Definition_S4_Canonical.md`<br>- `04_Step_Contracts/Step04_S4/S4_Image_Cost_and_Resolution_Policy.md`<br>- `04_Step_Contracts/S3_S4_Code_Documentation.md` |
| **v1.5 Implementation**    | - S3 image spec (`s3_image_spec__arm{X}.jsonl`) 읽기<br>- Gemini 이미지 생성 API 사용 (`models/nano-banana-pro-preview`)<br>- Deterministic 파일명: 카드 이미지 `IMG__{run_tag}__{group_id}__{entity_id}__{card_role}.png`, 테이블 비주얼 `IMG__{run_tag}__{group_id}__TABLE.png`<br>- 스펙 종류별 분기: 카드 이미지(4:5, 1K) vs 테이블 비주얼(16:9, 2K)<br>- `s4_image_manifest__arm{X}.jsonl` 생성 |
| **Canonical Invariants**   | - Render-only (medical interpretation 금지)<br>- Fixed image model (arm-independent, `nano-banana-pro-preview`)<br>- Q1 이미지 누락 → FAIL-FAST<br>- Q2 이미지 누락 → FAIL-FAST<br>- 테이블 비주얼 이미지 누락 → FAIL-FAST |
| **Hard Gates**             | - Q1 이미지 생성 실패 → FAIL-FAST<br>- Q2 이미지 생성 실패 → FAIL-FAST<br>- 테이블 비주얼 이미지 생성 실패 → FAIL-FAST<br>- API 키 누락 → FAIL<br>- 클라이언트 생성 실패 → FAIL |
| **Runtime Artifacts**      | `{RUN_TAG}/images/IMG__*.png` (카드 이미지 + 테이블 비주얼)<br>`{RUN_TAG}/s4_image_manifest__arm{X}.jsonl` |
| **Verification Hooks**     | CP-2 (schema), CP-3 (권한/역할 경계)                                                                                        |
| **Status**                 | ✅ Implemented (v1.5: nano-banana-pro 모델, Q2 필수화, 테이블 비주얼 지원, 스펙 종류별 분기 완료)                                                                     |

---

## 2.8 Step05 — PDF Builder (v1.5: Implemented)

| 항목                         | 내용                                                                                                                     |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Area**                   | Step05 (PDF Builder for S0 QA)                                                                                              |
| **Code Path**              | `3_Code/src/07_build_set_pdf.py`                                                                                   |
| **Primary Canonical Docs** | - `04_Step_Contracts/Step04_S4/Entity_Definition_S4_Canonical.md` (이미지 배치 정책 참조) |
| **v1.5 Implementation**    | - S1 구조 (`stage1_struct__arm{X}.jsonl`) 읽기<br>- S2 결과 (`s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl` 또는 legacy `s2_results__arm{X}.jsonl`) 읽기<br>- S3 policy manifest (`image_policy_manifest__arm{X}.jsonl`) 읽기<br>- S4 image manifest (`s4_image_manifest__arm{X}.jsonl`) 읽기<br>- PDF 구성: (1) Master Table → (2) Infographic image → (3) Cards (12 cards)<br>- Image placement 기반 이미지 배치 (FRONT/BACK/NONE)<br>- Blinded mode 지원 (surrogate set_id 사용) |
| **Canonical Invariants**   | - Read-only consumption of frozen schemas (S1, S2, S3, S4)<br>- Deterministic file naming and layout<br>- Identical layout across arms (fonts, spacing, page structure)<br>- No LLM calls, no network calls |
| **Hard Gates**             | - S1/S2/S3/S4 출력 파일 없음 → FAIL<br>- 필수 이미지 누락 → FAIL<br>- PDF 생성 실패 → FAIL |
| **Runtime Artifacts**      | `6_Distributions/QA_Packets/SET_{group_id}_arm{arm}_{run_tag}.pdf` (S0 QA용, non-blinded)<br>`6_Distributions/QA_Packets/SET_{surrogate}_{run_tag}.pdf` (blinded) |
| **Verification Hooks**     | CP-2 (schema), CP-3 (권한/역할 경계)                                                                                        |
| **Status**                 | ✅ Implemented (v1.5: S0 QA용 PDF 패킷 빌더 구현 완료)                                                                     |

---

## 2.9 Step05 — Anki Export (v1.5: Implemented)

| 항목                         | 내용                                                                                                                     |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Area**                   | Step05 (Anki Deck Export)                                                                                              |
| **Code Path**              | `3_Code/src/07_export_anki_deck.py`                                                                                   |
| **Primary Canonical Docs** | - `04_Step_Contracts/Step04_S4/Entity_Definition_S4_Canonical.md` (이미지 배치 정책 참조) |
| **v1.5 Implementation**    | - S2 결과 (`s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl` 또는 legacy `s2_results__arm{X}.jsonl`) 읽기 (필수: `group_path` 필드 포함)<br>- S3 policy manifest (`image_policy_manifest__arm{X}.jsonl`)에서 image_placement를 읽어 적용 (authoritative)<br>- S4 image manifest (`s4_image_manifest__arm{X}.jsonl`) 읽기<br>- Role-based image placement (2-card policy: Q1: BACK, Q2: BACK)<br>- Missing image policy (Q1: FAIL, Q2: FAIL)<br>- Anki deck 생성 (`.apkg` 파일)<br>- 태그 생성: 카드 타입 (Basic/MCQ) + group_path 기반 메타데이터 태그 (Specialty/Anatomy/Modality/Category) |
| **Canonical Invariants**   | - Role-based image placement (hardcoded via S3 policy manifest; not configurable)<br>- Fail-fast on Q1 image missing<br>- Fail-fast on Q2 image missing<br>- card_role은 Q1/Q2만 허용<br>- **group_path 필수**: S2 결과에 `group_path` 필드가 없으면 경고 발생 (태그 불완전, 하지만 export는 계속) |
| **Hard Gates**             | - Q1 이미지 누락 → FAIL<br>- Q2 이미지 누락 → FAIL<br>- unknown card_role → FAIL<br>- S2/S3/S4 출력 파일 없음 → FAIL |
| **Warnings**               | - S2 결과에 `group_path` 필드 누락 → WARNING (태그는 카드 타입만 포함, export는 계속) |
| **Runtime Artifacts**      | `6_Distributions/anki/MeducAI_{run_tag}_arm{X}.apkg` |
| **Verification Hooks**     | CP-2 (schema), CP-3 (권한/역할 경계)                                                                                        |
| **Status**                 | ✅ Implemented (v1.5: S4 manifest 기반 Anki 덱 생성, Q2 필수화 반영)                                                                     |

---

## 3. Audit-Ready "Explainability" Statements (v1.5)

1. **카드 수 결정권은 Allocation 단독**이며, Step01/Step02는 이를 변경하지 않는다.
2. Step02는 Allocation이 준 quota(N)를 만족하지 못하면 **완화하지 않고 실패**한다.
3. S2 결과 파일(new/legacy)은 consumer 단계에서 `tools/path_resolver.py`를 통해 우선순위로 해석한다.
5. **Step03 (S3)는 state-only compiler**이며, content 생성/수정을 하지 않는다. Q1/Q2 이미지 스펙과 S1 테이블 비주얼 스펙을 컴파일한다.
6. **Step04 (S4)는 render-only presentation stage**이며, medical interpretation을 하지 않는다. S3에서 생성된 프롬프트를 그대로 사용한다.
7. **Join key SSOT**: 모든 단계에서 `(run_tag, group_id, entity_id, card_role)`을 join key로 사용한다.
8. **Image policy는 hardcoded**: 2-card policy로 Q1=BACK/required, Q2=BACK/required (S3에서 적용).
9. **Image model은 arm-independent**: 모든 arm에서 동일한 이미지 모델 사용 (`nano-banana-pro-preview`, S4_Image_Cost_and_Resolution_Policy 준수).
10. **이중 이미지 생성**: 각 entity당 Q1/Q2 카드 이미지 2개, 각 group당 S1 테이블 비주얼 1개가 생성된다.
11. **프롬프트 개선**: S3에서 생성하는 이미지 프롬프트는 카드의 front/back 텍스트와 추출된 정답을 포함하여 이미지 생성 품질을 향상시킨다.

---

## 4. v1.5 구현 완료 요약

* **Step01 (S1)**: ✅ 구현 완료 (v1.3)
* **Step02 (S2)**: ✅ 구현 완료 및 안정화 (v1.3, v1.4)
* **Step03 (S3)**: ✅ 구현 완료 (v1.5: Q2 필수화, 테이블 비주얼 추가, 프롬프트 개선)
* **Step04 (S4)**: ✅ 구현 완료 (v1.5: nano-banana-pro 모델, Q2 필수화, 테이블 비주얼 지원, 스펙 종류별 분기)
* **Step05 (PDF Builder)**: ✅ 구현 완료 (`07_build_set_pdf.py`: S0 QA용 PDF 패킷 생성)
* **Step05 (Anki Export)**: ✅ 구현 완료 (`07_export_anki_deck.py`: S4 manifest 기반 Anki 덱 생성)
* **Allocation**: ✅ 구현 완료 (v2.1: deterministic prefix allocation)
* **Runtime Manifest**: (Deprecated) 현재 트리에는 구현이 포함되지 않음

**전체 파이프라인 (S1→S2→S3→S4→S5→S6) 구현 완료**

---

## 4-A. v1.2에서 "무리 없이" 끝내는 이유 (역사적 참고)

* Step03/Step04는 코드를 억지로 넣지 않고, **문서-기반 고정**만 한다.
* Step02와 manifest는 "최소 단위"로만 고정하여, 실제 구현/테스트를 다음 커밋에서 진행할 수 있다.
* 즉 v1.2는 **설계의 강제력(게이트/산출물/경로)을 먼저 고정**하고, 생성·품질은 단계적으로 올리는 전략이다.
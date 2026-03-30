# S4 이미지 프롬프트 분석 문서

**작성일:** 2025-12-20  
**목적:** S4에서 사용되는 이미지 프롬프트 개선을 위한 S1용/S2용 이미지 생성 정보 정리

---

## 목차

1. [S1용 이미지 (테이블 비주얼)](#s1용-이미지-테이블-비주얼)
2. [S2용 이미지 (카드 이미지)](#s2용-이미지-카드-이미지)
3. [프롬프트 생성 흐름](#프롬프트-생성-흐름)

---

## S1용 이미지 (테이블 비주얼)

### 개요

- **스펙 종류:** `S1_TABLE_VISUAL`
- **용도:** 그룹 레벨 테이블 데이터의 시각적 요약 다이어그램
- **생성 위치:** S3의 `compile_table_visual_spec()` 함수
- **이미지 설정:**
  - Aspect Ratio: `16:9` (넓은 화면 비율)
  - Image Size: `2K` (고해상도)
  - 파일명 형식: `IMG__{run_tag}__{group_id}__TABLE.png`

### 입력 정보 (S1에서 전달)

| 필드명 | 출처 | 설명 | 예시 |
|--------|------|------|------|
| `visual_type_category` | `stage1_struct__arm{arm}.jsonl` | 시각화 유형 카테고리 | `"Pathology_Pattern"`, `"Anatomy_Map"`, `"Pattern_Collection"`, `"Physiology_Process"`, `"Equipment"`, `"QC"`, `"General"` |
| `master_table_markdown_kr` | `stage1_struct__arm{arm}.jsonl` | 마스터 테이블 마크다운 (전체) | 마크다운 형식의 테이블 문자열 |
| `group_id` | `stage1_struct__arm{arm}.jsonl` | 그룹 식별자 | `"G001"` |
| `run_tag` | 파이프라인 파라미터 | 실행 태그 | `"RUN_20251220"` |

### 프롬프트 구조

**생성 함수:** `compile_table_visual_spec()` (03_s3_policy_resolver.py:319-397)

```python
prompt_en = (
    f"Create a clean {style_desc} based on the following medical table data.\n"
    f"Visual type: {visual_type}\n"
    f"Table structure: {len(headers)} columns, {row_count} data rows\n"
    f"Content source: {master_table[:500]}{'...' if len(master_table) > 500 else ''}\n"
    f"Style requirements: Minimal text (prefer English short labels if any). Clean layout. "
    f"Visual summary aligned to {visual_type} category. Do NOT render the markdown table verbatim as text. "
    f"Instead, create a diagrammatic/visual representation."
)
```

### 프롬프트 구성 요소

1. **시각화 스타일 (`style_desc`)**
   - `visual_type_category`에 따라 매핑:
     - `"Pattern_Collection"` → `"pattern collection visual"`
     - `"Anatomy_Map"` → `"anatomy map diagram"`
     - `"Pathology_Pattern"` → `"pathology pattern diagram"`
     - `"Physiology_Process"` → `"physiology process diagram"`
     - `"Equipment"` → `"equipment diagram"`
     - `"QC"` → `"quality control diagram"`
     - `"General"` → `"visual summary diagram"` (기본값)
   
   **Note (v11):** `Comparison`, `Algorithm`, `Classification`, and `Sign_Collection` categories have been removed as they were not used in the study.

2. **테이블 구조 정보**
   - 컬럼 수 (`len(headers)`)
   - 데이터 행 수 (`row_count`)

3. **테이블 내용 미리보기**
   - `master_table`의 처음 500자만 포함 (긴 테이블의 경우 `...` 추가)

4. **스타일 요구사항**
   - 최소한의 텍스트 (영문 짧은 라벨 선호)
   - 깔끔한 레이아웃
   - `visual_type_category`에 맞춘 시각적 요약
   - 마크다운 테이블을 텍스트로 그대로 렌더링하지 않음
   - 다이어그램/시각적 표현으로 생성

### 예시 프롬프트

**입력:**
- `visual_type_category`: `"Pathology_Pattern"`
- `master_table_markdown_kr`: `"| Entity name | 질환/개념 | 영상 소견 키워드 | ...\n| --- | --- | --- |\n| Entity1 | Value1 | Value2 | ..."`
- `headers`: `["Entity name", "질환/개념", "영상 소견 키워드", ...]` (7개)
- `row_count`: 12

**생성된 프롬프트:**
```
Create a clean pathology pattern diagram based on the following medical table data.
Visual type: Pathology_Pattern
Table structure: 6 columns, 12 data rows
Content source: | Entity name | 질환/개념 | 영상 소견 키워드 | ...
Style requirements: Minimal text (prefer English short labels if any). Clean layout. Visual summary aligned to Pathology_Pattern category. Do NOT render the markdown table verbatim as text. Instead, create a diagrammatic/visual representation.
```

### 출력 스펙 구조

```json
{
  "schema_version": "S3_IMAGE_SPEC_v1.0",
  "run_tag": "RUN_20251220",
  "group_id": "G001",
  "entity_id": null,
  "entity_name": null,
  "card_role": null,
  "spec_kind": "S1_TABLE_VISUAL",
  "image_placement_final": "TABLE",
  "image_asset_required": true,
  "visual_type_category": "Pathology_Pattern",
  "template_id": "TABLE_VISUAL_v1__Pathology_Pattern",
  "prompt_en": "..."
}
```

---

## S2용 이미지 (카드 이미지)

### 개요

- **스펙 종류:** `S2_CARD_IMAGE`
- **용도:** Q1/Q2 카드에 사용되는 방사선 이미지
- **생성 위치:** S3의 `compile_image_spec()` 함수
- **이미지 설정:**
  - Aspect Ratio: `4:5` (카드 이미지 비율)
  - Image Size: `1K` (1024x1280)
  - 파일명 형식: `IMG__{run_tag}__{group_id}__{entity_id}__{card_role}.png`

### 입력 정보 (S2에서 전달)

#### 1. S2 카드 정보 (`s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl` 또는 legacy `s2_results__arm{arm}.jsonl`)

| 필드명 | 설명 | 예시 |
|--------|------|------|
| `group_id` | 그룹 식별자 | `"G001"` |
| `entity_id` | 엔티티 식별자 | `"E001"` |
| `entity_name` | 엔티티 이름 | `"뇌경색"` |
| `anki_cards[].card_role` | 카드 역할 | `"Q1"` 또는 `"Q2"` |
| `anki_cards[].front` | 카드 앞면 텍스트 | `"Most likely diagnosis?"` |
| `anki_cards[].back` | 카드 뒷면 텍스트 | `"Answer: 뇌경색\nWhy: ..."` |
| `anki_cards[].options` | 선택지 (Q2/Q3용) | `["Option A", "Option B", ...]` |
| `anki_cards[].correct_index` | 정답 인덱스 (Q2/Q3용) | `0` (A 선택지) |
| `anki_cards[].image_hint` | 이미지 힌트 객체 | 아래 참조 |

#### 2. 이미지 힌트 (`image_hint` 객체)

| 필드명 | 필수 여부 | 설명 | 예시 |
|--------|----------|------|------|
| `modality_preferred` | **필수** | 선호 영상 방식 | `"CT"`, `"MRI"`, `"X-ray"` 등 |
| `anatomy_region` | **필수** | 해부학적 부위 | `"뇌"`, `"폐"`, `"심장"` 등 |
| `key_findings_keywords` | **필수** | 주요 소견 키워드 리스트 | `["저음영", "삼각형 모양"]` |
| `view_or_sequence` | 선택 | 뷰 또는 시퀀스 | `"axial"`, `"coronal"` 등 |
| `exam_focus` | 선택 | 시험 초점 | 추가 컨텍스트 |

#### 3. S1 시각적 컨텍스트 (보조 정보)

| 필드명 | 출처 | 설명 | 예시 |
|--------|------|------|------|
| `visual_type_category` | `stage1_struct__arm{arm}.jsonl` | 시각화 유형 | `"Pathology_Pattern"`, `"Anatomy_Map"`, `"Pattern_Collection"`, `"Physiology_Process"`, `"Equipment"`, `"QC"`, `"General"` |
| `master_table_markdown_kr` | `stage1_struct__arm{arm}.jsonl` | 마스터 테이블 | 엔티티 행 데이터 추출용 |

### 프롬프트 구조

**생성 함수:** `compile_image_spec()` (03_s3_policy_resolver.py:182-316)

#### Q1용 프롬프트 (이미지가 앞면에 위치)

```python
prompt_en = (
    f"Generate a realistic {modality} radiology image{view_part} of {anatomy_region}.\n"
    f"The image should best support this flashcard:\n"
    f"- Question (front): {front_short}\n"
    f"- Correct answer: {answer_text}\n"
    f"- Explanation (back): {back_short}\n"
    f"Imaging features to depict: {key_findings_str or 'key findings'}\n"
    f"Constraints: No text, no labels, no arrows, no watermark. Single frame. Realistic clinical style. Board-exam style."
)
```

#### Q2용 프롬프트 (이미지가 뒷면에 위치)

```python
prompt_en = (
    f"Generate a realistic {modality} radiology image{view_part} of {anatomy_region}.\n"
    f"The image should best support this flashcard:\n"
    f"- Question (front): {front_short}\n"
    f"- Correct answer: {answer_text}\n"
    f"- Explanation (back): {back_short}\n"
    f"Imaging features to depict: {key_findings_str or 'key findings'}\n"
    f"Constraints: No text, no labels, no arrows, no watermark. Single frame. Realistic clinical style. Board-exam style."
)
```

**참고:** 현재 Q1과 Q2 프롬프트는 동일합니다. 향후 개선 시 용도에 맞게 차별화 가능.

### 프롬프트 구성 요소

1. **기본 이미지 정보**
   - `modality`: 영상 방식 (CT, MRI, X-ray 등)
   - `view_or_sequence`: 뷰 또는 시퀀스 (있는 경우만 추가)
   - `anatomy_region`: 해부학적 부위

2. **카드 컨텍스트**
   - `front_short`: 카드 앞면 텍스트 (처음 200자, 초과 시 `...` 추가)
   - `answer_text`: 정답 텍스트
     - Q1: `"Answer:"` 라인에서 추출 또는 뒷면 첫 줄
     - Q2/Q3: `correct_index`로부터 `"A. Option text"` 형식으로 추출
   - `back_short`: 카드 뒷면 텍스트 (처음 300자, 초과 시 `...` 추가)

3. **이미징 소견**
   - `key_findings_str`: `key_findings_keywords`를 쉼표로 연결
   - S1 테이블 행 데이터 컨텍스트 추가 (있는 경우):
     - 엔티티 행에서 엔티티 이름 컬럼 제외한 값들 중 최대 3개
     - 형식: `"keyword1, keyword2 | Context: value1, value2, value3"`

4. **제약 조건**
   - 텍스트 없음
   - 라벨 없음
   - 화살표 없음
   - 워터마크 없음
   - 단일 프레임
   - 현실적인 임상 스타일
   - 보드 시험 스타일

### 예시 프롬프트

#### Q1 예시

**입력:**
- `modality`: `"CT"`
- `anatomy_region`: `"뇌"`
- `view_or_sequence`: `"axial"`
- `key_findings_keywords`: `["저음영", "삼각형 모양"]`
- `front`: `"Most likely diagnosis?"`
- `back`: `"Answer: 뇌경색\nWhy: CT에서 저음영의 삼각형 모양이 특징적입니다."`
- `entity_row`: `{"Entity name": "뇌경색", "Location": "MCA territory", "Shape": "Triangular"}`

**생성된 프롬프트:**
```
Generate a realistic CT radiology image (axial) of 뇌.
The image should best support this flashcard:
- Question (front): Most likely diagnosis?
- Correct answer: 뇌경색
- Explanation (back): Answer: 뇌경색
Why: CT에서 저음영의 삼각형 모양이 특징적입니다.
Imaging features to depict: 저음영, 삼각형 모양 | Context: MCA territory, Triangular, ...
Constraints: No text, no labels, no arrows, no watermark. Single frame. Realistic clinical style. Board-exam style.
```

#### Q2 예시

**입력:**
- `modality`: `"MRI"`
- `anatomy_region`: `"폐"`
- `view_or_sequence`: `""` (없음)
- `key_findings_keywords`: `["고신호강도", "T2-weighted"]`
- `front`: `"What is the most likely finding?"`
- `back`: `"Correct: A. 폐부종\nExplanation: ..."`
- `options`: `["폐부종", "폐렴", "기흉"]`
- `correct_index`: `0`

**생성된 프롬프트:**
```
Generate a realistic MRI radiology image of 폐.
The image should best support this flashcard:
- Question (front): What is the most likely finding?
- Correct answer: A. 폐부종
- Explanation (back): Correct: A. 폐부종
Explanation: ...
Imaging features to depict: 고신호강도, T2-weighted
Constraints: No text, no labels, no arrows, no watermark. Single frame. Realistic clinical style. Board-exam style.
```

### 출력 스펙 구조

```json
{
  "schema_version": "S3_IMAGE_SPEC_v1.0",
  "run_tag": "RUN_20251220",
  "group_id": "G001",
  "entity_id": "E001",
  "entity_name": "뇌경색",
  "card_role": "Q1",
  "spec_kind": "S2_CARD_IMAGE",
  "image_placement_final": "FRONT",
  "image_asset_required": true,
  "modality": "CT",
  "anatomy_region": "뇌",
  "key_findings_keywords": ["저음영", "삼각형 모양"],
  "template_id": "RAD_IMAGE_v1__CT__Q1",
  "prompt_en": "...",
  "answer_text": "뇌경색",
  "view_or_sequence": "axial"
}
```

---

## 프롬프트 생성 흐름

### 전체 파이프라인

```
S1 (Structure Generation)
  ↓
  stage1_struct__arm{arm}.jsonl
  (visual_type_category, master_table_markdown_kr)

S2 (Card Execution)
  ↓
  s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl (new format, 2025-12-23)
  또는 s2_results__arm{arm}.jsonl (legacy, backward compatible)
  (entity별 anki_cards, image_hint)

S3 (Policy Resolver & ImageSpec Compiler)
  ↓ 입력: s2_results + stage1_struct
  ↓ 처리:
    1. resolve_image_policy(card_role) → 정책 결정
    2. compile_image_spec() → S2 카드 이미지 스펙 생성
    3. compile_table_visual_spec() → S1 테이블 비주얼 스펙 생성
  ↓ 출력:
    - image_policy_manifest__arm{arm}.jsonl (모든 카드)
    - s3_image_spec__arm{arm}.jsonl (Q1/Q2 + S1 테이블 비주얼)

S4 (Image Generator)
  ↓ 입력: s3_image_spec__arm{arm}.jsonl
  ↓ 처리:
    1. load_image_specs() → 스펙 로드
    2. generate_image() → Gemini API로 이미지 생성
    3. spec_kind에 따라 aspect_ratio/size 결정
  ↓ 출력:
    - IMG__*.png (이미지 파일)
    - s4_image_manifest__arm{arm}.jsonl (매핑 정보)
```

### S3에서의 프롬프트 생성 로직

#### S2 카드 이미지 (Q1/Q2)

```python
# 1. 이미지 힌트 검증 (필수 필드)
modality = image_hint.get("modality_preferred")  # 필수
anatomy_region = image_hint.get("anatomy_region")  # 필수
key_findings = image_hint.get("key_findings_keywords")  # 필수

# 2. 카드 텍스트 추출
front_short = card.get("front")[:200] + "..."
back_short = card.get("back")[:300] + "..."

# 3. 정답 추출
answer_text = extract_answer_text(card, card_role)

# 4. S1 테이블 행 데이터 추출 (보조 컨텍스트)
entity_row = extract_entity_row_from_table(
    master_table_markdown_kr=s1_visual_context["master_table_markdown_kr"],
    entity_name=entity_name,
)

# 5. 키 소견 문자열 구성
key_findings_str = ", ".join(key_findings)
if entity_row:
    row_values = [v for k, v in entity_row.items() if k != "Entity name" and v.strip()]
    if row_values:
        key_findings_str += " | Context: " + ", ".join(row_values[:3])

# 6. 프롬프트 생성
prompt_en = f"Generate a realistic {modality} radiology image{view_part} of {anatomy_region}.\n..."
```

#### S1 테이블 비주얼

```python
# 1. S1 구조 정보 추출
visual_type = s1_struct.get("visual_type_category", "General")
master_table = s1_struct.get("master_table_markdown_kr", "")

# 2. 시각화 스타일 매핑
style_desc = visual_style_map.get(visual_type, "visual summary diagram")

# 3. 테이블 구조 파싱
headers = [h.strip() for h in header_line[1:-1].split("|") if h.strip()]
row_count = len([l for l in lines[2:] if l.strip().startswith("|")])

# 4. 프롬프트 생성
prompt_en = (
    f"Create a clean {style_desc} based on the following medical table data.\n"
    f"Visual type: {visual_type}\n"
    f"Table structure: {len(headers)} columns, {row_count} data rows\n"
    f"Content source: {master_table[:500]}...\n"
    f"Style requirements: ..."
)
```

---

## 개선 포인트

### 현재 상태

1. **S1 테이블 비주얼**
   - 테이블 내용이 500자로 제한되어 전체 정보 전달이 제한적
   - 시각화 스타일이 카테고리별로 고정되어 있음

2. **S2 카드 이미지**
   - Q1과 Q2 프롬프트가 동일함 (용도 차이 반영 필요)
   - 카드 텍스트가 잘림 (200/300자 제한)
   - S1 테이블 컨텍스트가 최대 3개 값으로 제한됨

### 개선 제안

1. **S1 테이블 비주얼**
   - 테이블 구조 정보를 더 상세히 전달 (컬럼명, 주요 값 등)
   - 시각화 스타일을 더 구체적으로 지정

2. **S2 카드 이미지**
   - Q1 (이미지가 문제): 문제 해결에 필요한 핵심 소견 강조
   - Q2 (이미지가 설명): 정답과 설명을 뒷받침하는 소견 강조
   - 카드 텍스트 길이 제한 완화 또는 요약 개선
   - S1 컨텍스트 활용도 향상

---

## 참고 파일

- **S3 코드:** `3_Code/src/03_s3_policy_resolver.py`
  - `compile_image_spec()`: S2 카드 이미지 스펙 생성 (182-316줄)
  - `compile_table_visual_spec()`: S1 테이블 비주얼 스펙 생성 (319-397줄)
- **S4 코드:** `3_Code/src/04_s4_image_generator.py`
  - `generate_image()`: 이미지 생성 실행 (171-262줄)
- **문서:** `0_Protocol/04_Step_Contracts/S3_S4_Code_Documentation.md`



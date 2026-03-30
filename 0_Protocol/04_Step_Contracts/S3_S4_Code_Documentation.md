# S3 & S4 코드 동작 방식 문서

**작성일:** 2025-12-20  
**목적:** S3 (Policy Resolver & ImageSpec Compiler)와 S4 (Image Generator) 코드의 입출력, 내부 진행방법, 프롬프트 정리

---

## 목차

1. [S3 (Policy Resolver & ImageSpec Compiler)](#s3-policy-resolver--imagespec-compiler)
   - [입력값](#s3-입력값)
   - [출력값](#s3-출력값)
   - [내부 진행방법](#s3-내부-진행방법)
   - [프롬프트](#s3-프롬프트)
2. [S4 (Image Generator)](#s4-image-generator)
   - [입력값](#s4-입력값)
   - [출력값](#s4-출력값)
   - [내부 진행방법](#s4-내부-진행방법)
   - [프롬프트](#s4-프롬프트)
3. [전체 파이프라인 흐름](#전체-파이프라인-흐름)

---

## S3 (Policy Resolver & ImageSpec Compiler)

### 개요

S3는 **정책 해석기(Policy Resolver)**와 **이미지 스펙 컴파일러(ImageSpec Compiler)** 역할을 수행합니다.

- **핵심 원칙:** S3는 컴파일러이며, LLM을 호출하지 않습니다 (deterministic)
- **역할:** S2 결과물에서 이미지 정책을 해석하고, 이미지 생성에 필요한 스펙을 컴파일합니다

### S3 입력값

#### 1. 파일 입력

| 파일 경로 | 설명 | 형식 |
|----------|------|------|
| `{base_dir}/2_Data/metadata/generated/{run_tag}/s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl` | S2 단계에서 생성된 카드 결과물 (new format, 2025-12-23) | JSONL (각 라인 = 1 entity) |
| `{base_dir}/2_Data/metadata/generated/{run_tag}/s2_results__arm{arm}.jsonl` | S2 단계에서 생성된 카드 결과물 (legacy format, backward compatible) | JSONL (각 라인 = 1 entity) |
| `{base_dir}/2_Data/metadata/generated/{run_tag}/stage1_struct__arm{arm}.jsonl` | S1 단계에서 생성된 구조 정보 | JSONL (각 라인 = 1 group) |

#### 2. S2 결과물 구조 (s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl 또는 legacy s2_results__arm{arm}.jsonl)

각 라인은 하나의 entity를 나타냅니다:

```json
{
  "run_tag": "RUN_20251220",
  "group_id": "G001",
  "entity_id": "E001",
  "entity_name": "뇌경색",
  "anki_cards": [
    {
      "card_role": "Q1",
      "front": "...",
      "back": "...",
      "image_hint": {
        "modality_preferred": "CT",
        "anatomy_region": "뇌",
        "key_findings_keywords": ["저음영", "삼각형 모양"],
        "view_or_sequence": "axial",
        "exam_focus": "acute infarction"
      }
    },
    {
      "card_role": "Q2",
      "front": "...",
      "back": "...",
      "image_hint": { ... }
    },
    {
      "card_role": "Q3",
      "front": "...",
      "back": "..."
    }
  ]
}
```

**주요 필드:**
- `anki_cards`: 각 entity당 Q1, Q2, Q3 카드 배열
- `image_hint`: Q1/Q2에만 존재 (Q3는 없음)
  - `modality_preferred`: 영상 방식 (CT, MRI, X-ray 등)
  - `anatomy_region`: 해부학적 부위
  - `key_findings_keywords`: 주요 소견 키워드 배열
  - `view_or_sequence`: 선택적 (axial, coronal 등)
  - `exam_focus`: 선택적

#### 3. S1 구조 정보 (stage1_struct__arm{arm}.jsonl)

각 라인은 하나의 group을 나타냅니다:

```json
{
  "group_id": "G001",
  "visual_type_category": "General",
  "master_table_markdown_kr": "| 항목 | 값 |\n|------|-----|"
}
```

**주요 필드:**
- `visual_type_category`: 시각화 타입 카테고리
- `master_table_markdown_kr`: 마스터 테이블 마크다운 (선택적)

#### 4. CLI 인자

```bash
python 03_s3_policy_resolver.py \
  --base_dir /path/to/base \
  --run_tag RUN_20251220 \
  --arm A
```

- `--base_dir`: 프로젝트 루트 디렉토리 (기본값: ".")
- `--run_tag`: 실행 태그 (필수)
- `--arm`: Arm 식별자 (기본값: "A")

### S3 출력값

#### 1. 파일 출력

| 파일 경로 | 설명 | 형식 |
|----------|------|------|
| `{out_dir}/image_policy_manifest__arm{arm}.jsonl` | 모든 카드(Q1-Q2)의 이미지 정책 매니페스트 | JSONL |
| `{out_dir}/s3_image_spec__arm{arm}.jsonl` | Q1과 Q2 각각 독립적인 이미지 생성 스펙 (Q1/Q2 모두 별도 이미지) | JSONL |

#### 2. Policy Manifest 구조 (image_policy_manifest__arm{arm}.jsonl)

모든 카드(Q1, Q2)에 대해 생성됩니다:

```json
{
  "schema_version": "S3_POLICY_MANIFEST_v1.0",
  "run_tag": "RUN_20251220",
  "group_id": "G001",
  "entity_id": "E001",
  "entity_name": "뇌경색",
  "card_role": "Q1",
  "image_placement": "FRONT",
  "card_type": "BASIC",
  "image_required": true
}
```

**정책 규칙 (2-card policy):**
- **Q1:** `image_placement="BACK"`, `card_type="BASIC"`, `image_required=true` (독립 이미지 생성)
- **Q2:** `image_placement="BACK"`, `card_type="MCQ"`, `image_required=true` (독립 이미지 생성, Q1과 별개)

#### 3. Image Spec 구조 (s3_image_spec__arm{arm}.jsonl)

**Q1과 Q2 각각 독립적인 이미지 스펙이 생성됩니다** (2-card policy). 그룹 레벨 테이블 비주얼도 함께 생성됩니다:

**카드 이미지 스펙 (Q1 & Q2):**

**EXAM 스펙 (일반 그룹):**
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
  "prompt_en": "Generate a realistic CT radiology image (axial) of 뇌.\nThe image should best support this flashcard:\n- Question (front): ...\n- Correct answer: ...\n- Explanation (back): ...\nImaging features to depict: 저음영, 삼각형 모양\nConstraints: No text, no labels, no arrows, no watermark. Single frame. Realistic clinical style. Board-exam style.",
  "answer_text": "뇌경색",
  "view_or_sequence": "axial",
  "exam_focus": "acute infarction"
}
```

**CONCEPT 스펙 (QC/Equipment 그룹):**
```json
{
  "schema_version": "S3_IMAGE_SPEC_v1.0",
  "run_tag": "RUN_20251220",
  "group_id": "G002",
  "entity_id": "E005",
  "entity_name": "CT 선량 측정",
  "card_role": "Q1",
  "spec_kind": "S2_CARD_CONCEPT",
  "image_placement_final": "FRONT",
  "image_asset_required": true,
  "modality": "",
  "anatomy_region": "",
  "key_findings_keywords": [],
  "template_id": "CONCEPT_v1__QC__Q1",
  "prompt_en": "You are a senior medical illustrator...\n\nCreate ONE clean medical physics / QA concept diagram...",
  "answer_text": "CT 선량 측정",
  "visual_type_category": "QC"
}
```

**그룹 레벨 테이블 비주얼 스펙:**
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
  "prompt_en": "Create a clean pathology pattern diagram based on the following medical table data.\nVisual type: Pathology_Pattern\nTable structure: 6 columns, 12 data rows\nContent source: ...\nStyle requirements: Minimal text (prefer English short labels if any). Clean layout. Visual summary aligned to Pathology_Pattern category. Do NOT render the markdown table verbatim as text. Instead, create a diagrammatic/visual representation."
}
```

**주요 필드:**
- `spec_kind`: `"S2_CARD_IMAGE"` (EXAM 카드 이미지), `"S2_CARD_CONCEPT"` (CONCEPT 카드 이미지), 또는 `"S1_TABLE_VISUAL"` (테이블 비주얼)
- `prompt_en`: S4에서 사용할 이미지 생성 프롬프트 (영문, 카드 텍스트와 정답 포함)
- `template_id`: 템플릿 식별자
  - EXAM: `"RAD_IMAGE_v1__{modality}__{card_role}"`
  - CONCEPT: `"CONCEPT_v1__{visual_type_category}__{card_role}"`
  - TABLE: `"TABLE_VISUAL_v1__{visual_type_category}"`
- `image_asset_required`: Q1과 Q2 모두 true (각각 독립 이미지 생성), 테이블 비주얼은 true
- `answer_text`: 추출된 정답 텍스트 (카드 이미지에만 존재)
- `visual_type_category`: CONCEPT 스펙에만 존재 (QC 또는 Equipment)

### S3 내부 진행방법

#### 1. 전체 흐름도

```
1. 입력 파일 로드
   ├─ load_s2_results() → s2_records
   └─ load_s1_struct() → s1_structs (group_id로 인덱싱)

2. 각 S2 레코드 처리
   ├─ group_id로 S1 구조 정보 조회
   └─ 각 카드 처리
       ├─ resolve_image_policy(card_role) → 정책 결정
       ├─ Policy Manifest 작성 (모든 Q1-Q3)
       └─ Image Spec 컴파일 (Q1/Q2만)
           ├─ compile_image_spec()
           └─ 프롬프트 템플릿 적용
```

#### 2. 주요 함수

##### `resolve_image_policy(card_role: str) -> Dict[str, Any]`

**역할:** 카드 역할(Q1/Q2)에 따라 이미지 정책을 결정합니다.

**로직 (2-card policy):**
- Q1 → `{image_placement: "BACK", card_type: "BASIC", image_required: True}`
- Q2 → `{image_placement: "BACK", card_type: "MCQ", image_required: True}`

**특징:** 하드코딩된 규칙 (LLM 호출 없음)

##### `compile_image_spec(...) -> Dict[str, Any]`

**역할:** S2의 `image_hint`를 기반으로 프롬프트 번들에서 템플릿을 로드하여 이미지 스펙을 컴파일합니다.

**검증 (Q1 & Q2):**
- Q1의 `image_hint`에서 `modality_preferred`가 유효한지 확인 (빈 값 또는 "Other"면 FAIL)
- Q1의 `image_hint`에서 `anatomy_region`이 존재하는지 확인 (없으면 FAIL)
- Q1의 `image_hint`에서 `key_findings_keywords`가 존재하는지 확인 (없으면 FAIL)
- Q2의 `image_hint`에서 동일한 필드 검증 수행 (Q2도 독립 이미지 생성)

**프롬프트 생성:**
1. 프롬프트 번들 로드 (`load_prompt_bundle()`)
2. System 템플릿 로드: `S4_EXAM_SYSTEM` 키
3. User 템플릿 로드: `S4_EXAM_USER` 키
4. User 템플릿 포맷팅: `safe_prompt_format()`로 placeholders 채우기
   - Placeholders: `group_id`, `entity_name`, `card_role`, `modality_preferred`, `anatomy_region`, `view_or_sequence`, `key_findings_keywords`, `exam_focus`
5. 결합: `prompt_en = system_template + "\n\n" + user_formatted`

**답안 추출:**
- `extract_answer_text()` 함수로 카드에서 정답 추출
- Q1: "Answer:" 라인에서 추출
- Q2/Q3: `correct_index`로 옵션 텍스트 추출
- **주의**: `answer_text`는 스펙에 저장되지만 프롬프트 생성에는 사용되지 않음

**에러 처리:**
- Q1/Q2 검증 실패 → 즉시 예외 발생 (FAIL-FAST)
- 프롬프트 템플릿 누락 → 즉시 예외 발생 (FAIL-FAST)

#### 3. 처리 순서

```python
for s2_record in s2_records:
    # 1. S1 구조 정보 조회
    s1_struct = s1_structs.get(group_id, {})
    s1_visual_context = {
        "visual_type_category": s1_struct.get("visual_type_category", "General"),
        "master_table_markdown_kr": s1_struct.get("master_table_markdown_kr", ""),
    }
    
    # 2. 각 카드 처리
    for card in cards:
        card_role = card.get("card_role")
        
        # 2-1. 정책 해석 (모든 카드)
        policy = resolve_image_policy(card_role)
        # → Policy Manifest 작성
        
        # 2-2. Image Spec 컴파일 (Q1 & Q2 - 각각 독립 이미지 생성)
        if card_role in ("Q1", "Q2"):
            image_hint = card.get("image_hint")
            if not image_hint:
                # Q1 and Q2 require image_hint
                print(f"[S3] Warning: {card_role} missing image_hint. Entity: {entity_name}, Group: {group_id}. Skipping card image spec.")
                continue
            
            try:
                spec = compile_image_spec(
                    run_tag=run_tag_rec,
                    group_id=group_id,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    card_role=card_role,
                    card=card,  # Pass full card for answer extraction (answer_text는 스펙 저장용, 프롬프트에는 사용 안 함)
                    image_hint=image_hint,  # AUTHORITATIVE: 프롬프트 생성의 유일한 소스
                    s1_visual_context=s1_visual_context,  # 테이블 비주얼용 (카드 이미지에는 사용 안 함)
                    prompt_bundle=prompt_bundle,  # 프롬프트 템플릿 번들
                )
                f_spec.write(json.dumps(spec, ensure_ascii=False) + "\n")
            except ValueError as e:
                # Log error but continue to allow table visual generation
                print(f"[S3] Warning: ImageSpec FAIL for {card_role} (Entity: {entity_name}, Group: {group_id}): {e}")
                print(f"[S3] Continuing to process other cards and table visuals...")
                # Don't raise - allow table visual generation to proceed
```

### S3 프롬프트

S3는 **프롬프트를 생성**하지만, LLM을 호출하지는 않습니다. 생성된 프롬프트는 S4에서 사용됩니다.

#### 프롬프트 번들 시스템

S3는 프롬프트 번들(`_registry.json`)을 통해 템플릿을 로드합니다:
- 프롬프트 파일 위치: `3_Code/prompt/`
- 번들 로더: `tools.prompt_bundle.load_prompt_bundle()`
- 템플릿 포맷팅: `safe_prompt_format()` (JSON 예시의 중괄호 처리)

#### 프롬프트 템플릿 구조

**Q1 & Q2 카드 이미지 프롬프트 (EXAM 그룹):**
- **System prompt**: `S4_EXAM_SYSTEM__v3.md` (역할 정의 및 제약사항)
- **User prompt**: `S4_EXAM_USER__v3.md` (IMAGE_HINT 기반 구체적 지시사항)
- **결합 방식**: `prompt_en = system_template + "\n\n" + user_formatted`
- **Placeholders**: `{group_id}`, `{entity_name}`, `{card_role}`, `{modality_preferred}`, `{anatomy_region}`, `{view_or_sequence}`, `{key_findings_keywords}`, `{exam_focus}`
- **주의**: `answer_text`는 추출되지만 프롬프트 생성에는 사용되지 않음 (스펙 저장용)
- **Q1과 Q2**: 각각 독립적인 프롬프트 생성 (서로 다른 image_hint 사용)

**Q1 카드 이미지 프롬프트 (CONCEPT 그룹, QC/Equipment):**
- **System prompt**: `S4_CONCEPT_SYSTEM__v1.md` (역할 정의 및 제약사항)
- **User prompt**: `S4_CONCEPT_USER__{visual_type_category}__v2.md` (visual_type_category별 템플릿)
  - 예: `S4_CONCEPT_USER__QC__v2.md`, `S4_CONCEPT_USER__Equipment__v2.md`
  - Fallback: `S4_CONCEPT_USER__General__v2.md` (특정 visual_type 템플릿이 없을 경우)
  - 최종 Fallback: 하드코딩된 기본 템플릿 문자열
- **결합 방식**: `prompt_en = system_template + "\n\n" + user_formatted`
- **Placeholders**: `{group_id}`, `{entity_name}`, `{card_role}`, `{front_short}`, `{answer_text_short}`, `{keywords_or_fallback}`, `{visual_type_category}`
- **특징**: 
  - `image_hint`가 없어도 카드 텍스트만으로 프롬프트 생성 가능
  - 라벨/축/간단 텍스트 허용 (임상 영상 전제 없음)
  - 도식/그래프/장비 구성도 생성에 최적화

**S1 테이블 비주얼 프롬프트:**
- **System prompt**: `S4_CONCEPT_SYSTEM__v3.md` (역할 정의 및 제약사항)
- **User prompt**: `S4_CONCEPT_USER__{visual_type_category}__v3.md` (visual_type_category별 템플릿)
  - 예: `S4_CONCEPT_USER__Pathology_Pattern__v3.md`, `S4_CONCEPT_USER__Anatomy_Map__v3.md`
  - Fallback: `S4_CONCEPT_USER__General__v3.md` (특정 visual_type 템플릿이 없을 경우)
  - **Note (v11):** `Comparison`, `Algorithm`, `Classification`, and `Sign_Collection` templates have been removed as they were not used in the study.
- **Placeholders**: `{group_id}`, `{group_path}`, `{visual_type_category}`, `{master_table_markdown_kr}`

**예시 (Q1 또는 Q2):**
- 입력: `modality="CT"`, `anatomy_region="뇌"`, `key_findings=["저음영", "삼각형 모양"]`
- System: "You are a board-certified radiologist generating ONE realistic radiology image..."
- User: "TARGET: Group ID: G001, Entity: 뇌경색, Card Role: Q1 (or Q2)\nIMAGE_HINT: modality_preferred: CT, anatomy_region: 뇌, key_findings_keywords: 저음영, 삼각형 모양..."
- 출력: System + User 결합된 다중 라인 프롬프트

**특징:**
- 프롬프트 번들 시스템으로 템플릿 관리 (버전 관리 및 일관성)
- System/User 분리로 역할과 구체 지시사항 분리
- `safe_prompt_format()`으로 JSON 예시 포함 템플릿 안전 처리
- visual_type_category 기반 동적 템플릿 선택 (테이블 비주얼)
- 고정된 템플릿 사용 (deterministic, LLM 호출 없음)

---

## S4 (Image Generator)

### 개요

S4는 **이미지 생성기(Image Generator)** 역할을 수행합니다.

- **핵심 원칙:** S4는 렌더링 전용 (의학적 해석 없음)
- **역할:** S3에서 생성된 이미지 스펙을 기반으로 실제 이미지를 생성합니다

### S4 입력값

#### 1. 파일 입력

| 파일 경로 | 설명 | 형식 |
|----------|------|------|
| `{base_dir}/2_Data/metadata/generated/{run_tag}/s3_image_spec__arm{arm}.jsonl` | S3에서 생성된 이미지 스펙 | JSONL (각 라인 = 1 이미지 스펙) |

#### 2. Image Spec 구조 (s3_image_spec__arm{arm}.jsonl)

S3의 출력과 동일합니다:

```json
{
  "schema_version": "S3_IMAGE_SPEC_v1.0",
  "run_tag": "RUN_20251220",
  "group_id": "G001",
  "entity_id": "E001",
  "entity_name": "뇌경색",
  "card_role": "Q1",
  "image_placement_final": "FRONT",
  "image_asset_required": true,
  "modality": "CT",
  "anatomy_region": "뇌",
  "key_findings_keywords": ["저음영", "삼각형 모양"],
  "template_id": "RAD_IMAGE_v1__CT__Q1",
  "prompt_en": "Create a realistic CT radiology image of 뇌 that demonstrates: 저음영, 삼각형 모양. No labels. Board-exam style."
}
```

**핵심 필드:**
- `prompt_en`: 이미지 생성에 사용할 프롬프트 (S3에서 System + User 템플릿 결합하여 생성)
- `image_asset_required`: Q1과 Q2 모두 true (각각 독립적으로 필수)
- `card_role`: Q1 또는 Q2
- `spec_kind`: `"S2_CARD_IMAGE"` (EXAM 카드 이미지), `"S2_CARD_CONCEPT"` (CONCEPT 카드 이미지), 또는 `"S1_TABLE_VISUAL"` (테이블 비주얼)
- `answer_text`: 추출된 정답 텍스트 (스펙 저장용, 프롬프트에는 사용 안 함)
- `visual_type_category`: CONCEPT 스펙에만 존재 (QC 또는 Equipment)

#### 3. 환경 변수

| 환경 변수 | 설명 | 기본값 |
|----------|------|--------|
| `GOOGLE_API_KEY` | Gemini API 키 (필수) | 없음 |
| `S4_IMAGE_MODEL` | 이미지 생성 모델 | `"nano banana pro"` (NEW) |

#### 4. CLI 인자

```bash
python 04_s4_image_generator.py \
  --base_dir /path/to/base \
  --run_tag RUN_20251220 \
  --arm A \
  --images_dir /optional/path/to/images \
  --dry_run \
  --only-infographic \
  --image_type anki|realistic|regen \
  --filename_suffix _custom
```

- `--base_dir`: 프로젝트 루트 디렉토리 (기본값: ".")
- `--run_tag`: 실행 태그 (필수)
- `--arm`: Arm 식별자 (기본값: "A")
- `--images_dir`: 이미지 출력 디렉토리 (기본값: `{out_dir}/images` 또는 `--image_type`에 따라 자동 설정)
- `--dry_run`: 실제 이미지 생성 없이 시뮬레이션만 수행
- `--only-infographic`: Infographic(S1_TABLE_VISUAL)만 생성하고 카드 이미지(S2_CARD_IMAGE)는 스킵 (NEW)
- `--image_type`: 이미지 타입 (선택적, 기본값: None - 기존 방식 유지)
  - `anki`: `images_anki/` 폴더 사용, suffix 없음
  - `realistic`: `images_realistic/` 폴더 사용, `_realistic` suffix 추가
  - `regen`: `images_regen/` 폴더 사용, `_regen` suffix 추가 (향후 구현)
  - 지정하지 않으면 기존 방식 (`images/` 폴더, suffix 없음)
- `--filename_suffix`: 파일명 suffix 수동 지정 (선택적, 기본값: `--image_type`에 따라 자동 설정)

### S4 출력값

#### 1. 파일 출력

| 파일 경로 | 설명 | 형식 |
|----------|------|------|
| `{images_dir}/IMG__{run_tag}__{group_id}__{entity_id}__{card_role}{suffix}.jpg` | 생성된 카드 이미지 파일 (EXAM/CONCEPT) | JPG (기본값) |
| `{images_dir}/IMG__{run_tag}__{group_id}__TABLE{suffix}.jpg` | 생성된 테이블 비주얼 파일 | JPG |
| `{out_dir}/s4_image_manifest__arm{arm}.jsonl` | 이미지 매핑 매니페스트 | JSONL |

**폴더 구조:**
- 기본값 (CLI 인자 없음): `{out_dir}/images/`
- `--image_type anki`: `{out_dir}/images_anki/`
- `--image_type realistic`: `{out_dir}/images_realistic/`
- `--image_type regen`: `{out_dir}/images_regen/` (향후 구현)

#### 2. 이미지 파일명 규칙

**Deterministic 매핑:**

카드 이미지:
```
IMG__{run_tag}__{group_id}__{entity_id}__{card_role}{suffix}.jpg
```

테이블 비주얼:
```
IMG__{run_tag}__{group_id}__TABLE{suffix}.jpg
```

**Suffix 규칙:**
- 기본값 (CLI 인자 없음): suffix 없음
- `--image_type realistic`: `_realistic` suffix 추가
- `--image_type regen`: `_regen` suffix 추가 (향후 구현)
- `--filename_suffix`: 수동 지정 가능

**예시:**
```
# 기본 (기존 방식)
images/IMG__RUN_20251220__G001__E001__Q1.jpg

# Realistic 이미지
images_realistic/IMG__RUN_20251220__G001__E001__Q1_realistic.jpg

# Regen 이미지 (향후)
images_regen/IMG__RUN_20251220__G001__E001__Q1_regen.jpg
```

**특징:**
- 파일명에 유효하지 않은 문자(`<>:"/\|?*`)는 언더스코어(`_`)로 치환
- Q1과 Q2는 각각 독립적인 이미지 파일 생성 (각자의 image_hint 기반)
- 테이블 비주얼은 그룹당 1개 생성
- **하위 호환성**: CLI 인자 없이 실행하면 기존 방식(`images/` 폴더, suffix 없음) 유지

#### 3. Image Manifest 구조 (s4_image_manifest__arm{arm}.jsonl)

각 이미지 스펙에 대해 생성됩니다:

```json
{
  "schema_version": "S4_IMAGE_MANIFEST_v1.0",
  "run_tag": "RUN_20251220",
  "group_id": "G001",
  "entity_id": "E001",
  "entity_name": "뇌경색",
  "card_role": "Q1",
  "media_filename": "IMG__RUN_20251220__G001__E001__Q1.png",
  "image_path": "/path/to/images/IMG__RUN_20251220__G001__E001__Q1.png",
  "generation_success": true,
  "image_required": true
}
```

**주요 필드:**
- `spec_kind`: `"S2_CARD_IMAGE"` (EXAM), `"S2_CARD_CONCEPT"` (CONCEPT), 또는 `"S1_TABLE_VISUAL"` (테이블 비주얼)
- `generation_success`: 이미지 생성 성공 여부
- `image_required`: Q1과 Q2는 true, Q3는 false, 테이블 비주얼은 true

### S4 내부 진행방법

#### 1. 전체 흐름도

```
1. 입력 파일 로드
   └─ load_image_specs() → specs

2. Gemini 클라이언트 초기화
   └─ build_gemini_client(api_key)

3. 각 이미지 스펙 처리
   ├─ make_image_filename() → 파일명 생성
   ├─ generate_image() → 이미지 생성
   │   ├─ Gemini API 호출
   │   ├─ 응답에서 이미지 추출
   │   └─ PNG 파일로 저장
   └─ Manifest 작성

4. Q1 실패 검증
   └─ Q1 이미지가 하나라도 실패하면 FAIL-FAST
```

#### 2. 주요 함수

##### `make_image_filename(...) -> str`

**역할:** Deterministic 파일명을 생성합니다.

**로직:**
1. `run_tag`, `group_id`, `entity_id`, `card_role`을 sanitize
2. `IMG__{run_tag}__{group_id}__{entity_id}__{card_role}.png` 형식으로 조합

**Sanitize 규칙:**
- 유효하지 않은 파일명 문자(`<>:"/\|?*`)를 `_`로 치환
- 앞뒤 공백 제거

##### `generate_image(...) -> bool`

**역할:** Gemini API를 사용하여 이미지를 생성합니다.

**로직:**
1. `image_spec`에서 `prompt_en`과 `spec_kind` 추출
2. Gemini 클라이언트 생성 (없으면)
3. CONCEPT 프리앰블 적용 (`spec_kind="S2_CARD_CONCEPT"`인 경우):
   - `S4_CONCEPT_PREAMBLE__v1.txt` 파일 로드 (없으면 기본값 사용)
   - `prompt_en` 앞에 프리앰블 추가: `prompt_en = preamble + prompt_en`
4. 이미지 생성 설정 (`spec_kind`에 따라 분기):
   - 카드 이미지 (`S2_CARD_IMAGE`, `S2_CARD_CONCEPT`): `aspect_ratio="4:5"`, `image_size="1K"` (1024x1280)
   - 테이블 비주얼 (`S1_TABLE_VISUAL`): `aspect_ratio="16:9"`, `image_size="4K"` (3840x2160)
5. `client.models.generate_content()` 호출 (모델: "models/nano-banana-pro-preview")
6. 응답에서 이미지 바이트 추출
7. PNG 파일로 저장

**에러 처리:**
- API 호출 실패 → `False` 반환
- 이미지 추출 실패 → `False` 반환
- 파일 저장 실패 → 예외 발생

##### `extract_image_from_response(resp) -> Optional[bytes]`

**역할:** Gemini API 응답에서 이미지 바이트를 추출합니다.

**로직:**
1. `resp.parts` 확인 → `inline_data`에서 이미지 추출
2. `part.as_image()` 시도 (PIL Image → PNG 바이트)
3. 실패 시 `inline.data` (base64) 디코딩 시도
4. `resp.candidates` 형식도 지원 (fallback)

#### 3. 처리 순서

```python
# 1. 이미지 스펙 로드
specs, skipped_count = load_image_specs(image_spec_path)

# 2. Gemini 클라이언트 초기화
client = build_gemini_client(api_key)

# 3. 각 스펙 처리
q1_failures = []
for spec in specs:
    # 3-1. 파일명 생성 (spec_kind에 따라 분기)
    filename = make_image_filename(
        run_tag=run_tag,
        group_id=group_id,
        entity_id=entity_id,  # None for table visuals
        card_role=card_role,  # None for table visuals
        spec_kind=spec_kind,
    )
    
    # 3-2. 이미지 생성 (spec_kind에 따라 aspect/size 분기)
    success = generate_image(
        image_spec=spec,
        output_path=images_dir / filename,
        client=client,
    )
    
    # 3-3. 필수 이미지 실패 추적 (Q1, Q2, TABLE)
    if not success and image_required:
        required_failures.append({...})
    
    # 3-4. Manifest 작성 (spec_kind 포함)
    manifest_entry = {
        ...,
        "spec_kind": spec_kind,
    }
    f_manifest.write(json.dumps(manifest_entry) + "\n")

# 4. 필수 이미지 실패 검증 (FAIL-FAST: Q1, Q2, TABLE)
if required_failures:
    raise RuntimeError("S4 FAIL-FAST: Required image generation failed")
```

#### 4. 이미지 생성 설정

**고정 설정 (arm-independent):**
- **모델:** `nano banana pro` (환경 변수 `S4_IMAGE_MODEL`로 변경 가능, 기본값 변경됨)
- **카드 이미지:**
  - 비율: `4:5` (세로형)
  - 크기: `1K` (1024x1280 픽셀)
- **테이블 비주얼:**
  - 비율: `16:9` (가로형)
  - 크기: `2K` (더 높은 해상도)

**이유:** S4_Image_Cost_and_Resolution_Policy에 따라 모든 arm에서 동일한 모델 사용, 이미지 종류에 따라 적절한 비율/크기 적용

### S4 프롬프트

S4는 **S3에서 생성된 프롬프트를 그대로 사용**합니다. 추가적인 프롬프트 생성이나 수정은 하지 않습니다.

#### 프롬프트 사용 방식

1. **입력:** S3의 `prompt_en` 필드
2. **전달:** Gemini API의 `contents` 파라미터에 직접 전달
3. **변환 없음:** 프롬프트를 수정하거나 추가하지 않음

**예시:**
```python
# S3에서 생성된 프롬프트
prompt_en = "Create a realistic CT radiology image of 뇌 that demonstrates: 저음영, 삼각형 모양. No labels. Board-exam style."

# S4에서 그대로 사용
response = client.models.generate_content(
    model=IMAGE_MODEL,
    contents=[prompt_en],  # ← 그대로 전달
    config=config,
)
```

**특징:**
- S4는 렌더링 전용이므로 프롬프트 생성/수정 금지
- S3에서 생성된 프롬프트를 신뢰하고 그대로 사용

---

## 전체 파이프라인 흐름

### S1 → S2 → S3 → S4 흐름

```
S1 (Structure Generation)
  ↓
  stage1_struct__arm{arm}.jsonl
  (group_id, visual_type_category, master_table_markdown_kr)

S2 (Card Execution)
  ↓
  s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl (new format, 2025-12-23)
  또는 s2_results__arm{arm}.jsonl (legacy, backward compatible)
  (entity별 anki_cards, image_hint)

S3 (Policy Resolver & ImageSpec Compiler)
  ↓ 입력: s2_results + stage1_struct + 프롬프트 번들
  ↓ 처리: 정책 해석 + 이미지 스펙 컴파일 (프롬프트 템플릿 사용)
  ↓ 출력:
    - image_policy_manifest__arm{arm}.jsonl (모든 카드 Q1-Q2)
    - s3_image_spec__arm{arm}.jsonl (Q1 & Q2 카드 이미지 + S1 테이블 비주얼, 각각 독립)

S4 (Image Generator)
  ↓ 입력: s3_image_spec
  ↓ 처리: Gemini API로 이미지 생성
  ↓ 출력:
    - IMG__*.png (이미지 파일)
    - s4_image_manifest__arm{arm}.jsonl (매핑 정보)
```

### 데이터 흐름 예시

**S2 출력 (s2_results):**
```json
{
  "group_id": "G001",
  "entity_id": "E001",
  "anki_cards": [
    {
      "card_role": "Q1",
      "image_hint": {
        "modality_preferred": "CT",
        "anatomy_region": "뇌",
        "key_findings_keywords": ["저음영"]
      }
    }
  ]
}
```

**S3 출력 (s3_image_spec):**
```json
{
  "schema_version": "S3_IMAGE_SPEC_v1.0",
  "group_id": "G001",
  "entity_id": "E001",
  "card_role": "Q1",
  "spec_kind": "S2_CARD_IMAGE",
  "prompt_en": "You are a board-certified radiologist generating ONE realistic radiology image...\n\nTARGET (READ-ONLY):\n- Group ID: G001\n- Entity: 뇌경색\n- Card Role: Q1\n\nIMAGE_HINT (AUTHORITATIVE; use ONLY this):\n- modality_preferred: CT\n- anatomy_region: 뇌\n- key_findings_keywords: 저음영, 삼각형 모양\n...",
  "answer_text": "뇌경색"
}
```

**S4 출력:**
- 파일: `IMG__RUN_20251220__G001__E001__Q1.png`
- Manifest:
```json
{
  "group_id": "G001",
  "entity_id": "E001",
  "card_role": "Q1",
  "media_filename": "IMG__RUN_20251220__G001__E001__Q1.png",
  "generation_success": true
}
```

---

## 주요 특징 요약

### S3 특징

1. **Deterministic:** LLM 호출 없음, 하드코딩된 규칙 사용
2. **Policy Resolution:** Q1/Q2에 따라 정책 자동 결정 (각각 독립 이미지)
3. **Validation:** Q1과 Q2 모두 필수 필드 검증 (modality, anatomy, keywords)
4. **Fail-Fast:** Q1/Q2/테이블 비주얼 실패 시 즉시 예외 발생
5. **프롬프트 번들 시스템:** System/User 템플릿 분리, visual_type_category 기반 동적 선택
6. **이미지 스펙 생성:** 카드 이미지(Q1 & Q2)와 그룹 레벨 테이블 비주얼 생성 (각각 독립)
7. **프롬프트 생성:** 각 카드의 image_hint를 사용하여 프롬프트 생성 (카드 텍스트나 answer_text는 프롬프트에 포함 안 함)

### S4 특징

1. **Render-Only:** 의학적 해석 없음, 프롬프트 수정 없음
2. **Deterministic Filename:** Q1/Q2 카드와 이미지 간 1:1 매핑 보장, 테이블 비주얼은 그룹당 1개
3. **Fixed Model:** 모든 arm에서 동일한 이미지 모델 사용 (`nano banana pro`)
4. **Fail-Fast:** Q1/Q2 이미지 생성 실패 시 즉시 예외 발생, 테이블 비주얼 이미지 생성 실패 시 즉시 예외 발생
5. **스펙 종류별 분기:** 카드 이미지(Q1 & Q2)와 테이블 비주얼에 따라 다른 aspect ratio와 해상도 적용

---

## 에러 처리

### S3 에러

| 상황 | 처리 방법 |
|------|----------|
| Q1/Q2에 `image_hint` 없음 | `ValueError` 예외 발생 (FAIL) |
| Q1/Q2에 `modality_preferred` 없음/무효 | 경고 출력 후 계속 진행 (테이블 비주얼 생성 계속) |
| Q1/Q2에 `anatomy_region` 없음 | 경고 출력 후 계속 진행 (테이블 비주얼 생성 계속) |
| Q1/Q2에 `key_findings_keywords` 없음 | 경고 출력 후 계속 진행 (테이블 비주얼 생성 계속) |
| 테이블 비주얼 스펙 컴파일 실패 | `ValueError` 예외 발생 (FAIL) |

**참고:** 카드 이미지 스펙 생성 실패 시에도 테이블 비주얼 스펙 생성은 계속됩니다. 이는 샘플 PDF 생성 시 일부 그룹의 카드 이미지가 실패해도 Infographic은 생성되어야 하기 때문입니다.

### S4 에러

| 상황 | 처리 방법 |
|------|----------|
| Q1 이미지 생성 실패 | `RuntimeError` 예외 발생 (FAIL-FAST) |
| Q2 이미지 생성 실패 | `RuntimeError` 예외 발생 (FAIL-FAST) |
| 테이블 비주얼 이미지 생성 실패 | `RuntimeError` 예외 발생 (FAIL-FAST) |
| API 키 없음 | `RuntimeError` 예외 발생 |
| Gemini 클라이언트 생성 실패 | `RuntimeError` 예외 발생 |

---

## 참고사항

1. **S3는 컴파일러:** LLM을 호출하지 않으며, 프롬프트 번들에서 템플릿을 로드하여 프롬프트를 생성합니다. System/User 템플릿을 결합하여 사용합니다.
2. **프롬프트 생성 원칙:** S3는 `image_hint`만 사용하여 프롬프트를 생성합니다. 카드 텍스트(front/back)나 `answer_text`는 프롬프트에 포함되지 않습니다 (스펙 저장용으로만 사용).
3. **S4는 렌더러:** 프롬프트를 수정하지 않으며, S3에서 생성된 프롬프트를 그대로 사용합니다. `models/nano-banana-pro-preview` 모델을 사용합니다.
4. **Deterministic:** 파일명과 정책 해석이 모두 deterministic하므로 재현 가능합니다.
5. **Fail-Fast:** Q1, Q2, 테이블 비주얼 이미지는 모두 필수이므로, 실패 시 즉시 중단합니다. (단, S3에서는 카드 이미지 스펙 생성 실패 시에도 테이블 비주얼 스펙 생성은 계속됩니다)
6. **이미지 생성 (2-card policy):** 각 entity당 Q1 카드 이미지 1개 + Q2 카드 이미지 1개가 생성됩니다 (각각 독립). 각 group당 테이블 비주얼 1개가 생성됩니다.
7. **프롬프트 번들:** `3_Code/prompt/_registry.json`에서 템플릿 매핑을 관리하며, visual_type_category에 따라 동적으로 템플릿을 선택합니다.
8. **선택적 생성:** S4의 `--only-infographic` 옵션으로 Infographic만 빠르게 재생성할 수 있습니다.
9. **Entity ID 형식:** 이미지 파일명은 `DERIVED_xxx` (언더스코어) 형식을 사용하지만, S2 records는 `DERIVED:xxx` (콜론) 형식을 사용합니다. PDF와 Anki export에서 정규화하여 두 형식을 모두 지원합니다.


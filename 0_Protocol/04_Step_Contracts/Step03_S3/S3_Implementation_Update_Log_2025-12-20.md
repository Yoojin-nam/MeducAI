# S3 Implementation Update Log — 2025-12-20

**Status:** Canonical  
**Version:** 1.1  
**Last Updated:** 2025-12-20  
**Purpose:** S3 Policy Resolver & ImageSpec Compiler 구현 업데이트 이력

---

## 개요

이 문서는 2025-12-20에 수행된 S3 (Policy Resolver & ImageSpec Compiler) 구현 업데이트를 기록합니다.

---

## 주요 변경 사항

### 1. Q2 이미지 정책 변경 (Policy Update)

**변경 전:**
- Q2: `image_required = False` (optional)

**변경 후:**
- Q2: `image_required = True` (required, fail-fast)

**영향:**
- Q2도 Q1과 동일하게 이미지 생성이 필수가 됨
- Q2 이미지 생성 실패 시 FAIL-FAST
- Policy manifest에서 Q2의 `image_required` 필드가 `true`로 변경

**관련 코드:**
- `03_s3_policy_resolver.py`: `resolve_image_policy()` 함수

---

### 2. S1 테이블 비주얼 스펙 추가 (New Feature)

**추가 기능:**
- 그룹 레벨 테이블 비주얼 이미지 스펙 컴파일
- `compile_table_visual_spec()` 함수 추가
- `spec_kind = "S1_TABLE_VISUAL"` 지원

**입력:**
- S1 `stage1_struct__arm{arm}.jsonl`에서 `visual_type_category`, `master_table_markdown_kr` 사용

**출력:**
- `s3_image_spec__arm{arm}.jsonl`에 그룹당 1개의 테이블 비주얼 스펙 추가
- 파일명: `IMG__{run_tag}__{group_id}__TABLE.png`

**프롬프트:**
- `visual_type_category`에 따라 스타일 선택 (comparison diagram, algorithm flowchart 등)
- 마크다운 테이블을 그대로 렌더링하지 않고 시각적 요약 생성

**관련 코드:**
- `03_s3_policy_resolver.py`: `compile_table_visual_spec()` 함수
- `process_s3()` 함수에 그룹 레벨 처리 로직 추가

---

### 3. 프롬프트 개선 (Prompt Enhancement)

**변경 전:**
```
Create a realistic {modality} radiology image of {anatomy_region} 
that demonstrates: {key_findings}. No labels. Board-exam style.
```

**변경 후:**
```
Generate a realistic {modality} radiology image ({view_or_sequence}) of {anatomy_region}.
The image should best support this flashcard:
- Question (front): {front_text_short}
- Correct answer: {answer_text}
- Explanation (back): {back_text_short}
Imaging features to depict: {key_findings_keywords + row_context}
Constraints: No text, no labels, no arrows, no watermark. Single frame. Realistic clinical style. Board-exam style.
```

**개선 사항:**
- 카드의 front/back 텍스트 포함
- 추출된 정답 텍스트 포함
- S1 테이블 행 데이터를 컨텍스트로 추가
- 더 구체적인 제약 조건 명시

**정답 추출 로직:**
- Q1 (BASIC): back에서 "Answer:" 줄 파싱
- Q2/Q3 (MCQ): `correct_index`로 옵션 텍스트 추출

**관련 코드:**
- `03_s3_policy_resolver.py`: `extract_answer_text()` 함수
- `compile_image_spec()` 함수의 프롬프트 생성 부분

---

### 4. 이미지 스펙 스키마 확장 (Schema Extension)

**추가 필드:**
- `spec_kind`: `"S2_CARD_IMAGE"` 또는 `"S1_TABLE_VISUAL"`
- `answer_text`: 추출된 정답 텍스트 (카드 이미지에만)

**스펙 종류별 차이:**

| 필드 | S2_CARD_IMAGE | S1_TABLE_VISUAL |
|------|---------------|-----------------|
| `entity_id` | 있음 | `null` |
| `card_role` | Q1 또는 Q2 | `null` |
| `spec_kind` | `"S2_CARD_IMAGE"` | `"S1_TABLE_VISUAL"` |
| `image_placement_final` | FRONT 또는 BACK | TABLE |
| `modality` | 있음 | 없음 |
| `visual_type_category` | 없음 | 있음 |

---

## 코드 변경 사항

### 파일: `3_Code/src/03_s3_policy_resolver.py`

**추가 함수:**
1. `extract_answer_text()`: 카드에서 정답 텍스트 추출
2. `extract_entity_row_from_table()`: S1 테이블에서 entity 행 데이터 추출
3. `compile_table_visual_spec()`: 그룹 레벨 테이블 비주얼 스펙 컴파일

**수정 함수:**
1. `resolve_image_policy()`: Q2의 `image_required`를 `True`로 변경
2. `compile_image_spec()`: 
   - `card` 파라미터 추가 (front/back/answer 추출용)
   - 프롬프트 템플릿 개선
   - `spec_kind` 필드 추가
   - `answer_text` 필드 추가
3. `process_s3()`:
   - Q2도 필수로 처리 (image_hint 없으면 FAIL)
   - 그룹 레벨 테이블 비주얼 스펙 생성 로직 추가

---

## 출력 아티팩트 변경

### `image_policy_manifest__arm{arm}.jsonl`

**변경 사항:**
- Q2의 `image_required` 필드가 `true`로 변경

**예시:**
```json
{
  "schema_version": "S3_POLICY_MANIFEST_v1.0",
  "run_tag": "RUN_20251220",
  "group_id": "G001",
  "entity_id": "E001",
  "entity_name": "뇌경색",
  "card_role": "Q2",
  "image_placement": "BACK",
  "card_type": "MCQ",
  "image_required": true  // 변경됨 (기존: false)
}
```

### `s3_image_spec__arm{arm}.jsonl`

**변경 사항:**
- Q2도 포함 (기존에는 Q1만)
- 그룹 레벨 테이블 비주얼 스펙 추가
- `spec_kind` 필드 추가
- `answer_text` 필드 추가 (카드 이미지에만)
- 프롬프트 형식 개선

**카드 이미지 스펙 예시:**
```json
{
  "schema_version": "S3_IMAGE_SPEC_v1.0",
  "run_tag": "RUN_20251220",
  "group_id": "G001",
  "entity_id": "E001",
  "entity_name": "뇌경색",
  "card_role": "Q1",
  "spec_kind": "S2_CARD_IMAGE",  // 추가됨
  "image_placement_final": "FRONT",
  "image_asset_required": true,
  "modality": "CT",
  "anatomy_region": "뇌",
  "key_findings_keywords": ["저음영", "삼각형 모양"],
  "template_id": "RAD_IMAGE_v1__CT__Q1",
  "prompt_en": "Generate a realistic CT radiology image...",  // 개선됨
  "answer_text": "뇌경색"  // 추가됨
}
```

**테이블 비주얼 스펙 예시:**
```json
{
  "schema_version": "S3_IMAGE_SPEC_v1.0",
  "run_tag": "RUN_20251220",
  "group_id": "G001",
  "entity_id": null,  // 그룹 레벨
  "entity_name": null,
  "card_role": null,
  "spec_kind": "S1_TABLE_VISUAL",  // 새로 추가
  "image_placement_final": "TABLE",
  "image_asset_required": true,
  "visual_type_category": "Pathology_Pattern",
  "template_id": "TABLE_VISUAL_v1__Pathology_Pattern",
  "prompt_en": "Create a clean pathology pattern diagram..."
}
```

---

## 검증 규칙 변경

### Q2 검증 강화

**변경 전:**
- Q2에 `image_hint` 없음 → 경고 후 스킵

**변경 후:**
- Q2에 `image_hint` 없음 → `ValueError` 예외 발생 (FAIL)
- Q2에 `modality_preferred` 없음/무효 → `ValueError` 예외 발생 (FAIL)
- Q2에 `anatomy_region` 없음 → `ValueError` 예외 발생 (FAIL)
- Q2에 `key_findings_keywords` 없음 → `ValueError` 예외 발생 (FAIL)

---

## 하위 호환성

### 기존 S2 출력과의 호환성

- ✅ 기존 S2 출력 스키마 변경 없음 (frozen)
- ✅ 기존 S2 출력의 optional 필드(`image_hint`)를 소비만 함
- ⚠️ Q2에 `image_hint`가 없는 경우 실패 (기존에는 경고만)

### 마이그레이션 가이드

기존 실행 결과를 재사용하려면:
1. S2 출력에 Q2의 `image_hint`가 있는지 확인
2. 없으면 S2를 재실행하여 `image_hint` 생성 필요

---

## 테스트 결과

### 테스트 실행
- Run Tag: `test_armA_sample1_v5`
- Arm: A
- Sample: 1

### 결과
- ✅ S1: 성공
- ✅ S2: 성공
- ✅ S3: 성공 (Policy Manifest: 12 records, Image Spec: 9 records)
- ✅ S4: 성공 (이미지 생성 완료)

---

## 관련 문서

- `Entity_Definition_S3_Canonical.md`: S3 엔티티 정의
- `S3_to_S4_Input_Contract_Canonical.md`: S3→S4 입력 계약
- `S3_S4_Code_Documentation.md`: 코드 동작 방식 문서 (프로젝트 루트)

---

### 5. 카드 이미지 스펙 생성 실패 시 테이블 비주얼 생성 계속 (Error Handling Improvement)

**변경 전:**
- 카드 이미지 스펙 생성 실패 시 즉시 예외 발생 → 테이블 비주얼 스펙 생성 불가

**변경 후:**
- 카드 이미지 스펙 생성 실패 시 경고만 출력하고 계속 진행
- 테이블 비주얼 스펙 생성은 항상 시도 (카드 이미지 실패와 독립적)

**이유:**
- 샘플 PDF 생성 시 일부 그룹의 카드 이미지가 실패해도 Infographic은 생성되어야 함
- 테이블 비주얼은 그룹 레벨이므로 카드 이미지 실패와 무관하게 생성 가능

**관련 코드:**
- `03_s3_policy_resolver.py`: `process_s3()` 함수의 카드 이미지 스펙 생성 부분

**에러 처리:**
```python
try:
    spec = compile_image_spec(...)
    f_spec.write(json.dumps(spec, ensure_ascii=False) + "\n")
except ValueError as e:
    # Log error but continue to allow table visual generation
    print(f"[S3] Warning: ImageSpec FAIL for {card_role}: {e}")
    print(f"[S3] Continuing to process other cards and table visuals...")
    # Don't raise - allow table visual generation to proceed
```

---

## 변경 이력

- **2025-12-20 (오후)**: 추가 업데이트
  - 카드 이미지 스펙 생성 실패 시에도 테이블 비주얼 생성 계속
- **2025-12-20 (오전)**: 초기 구현 업데이트
  - Q2 이미지 정책 변경
  - S1 테이블 비주얼 추가
  - 프롬프트 개선
  - 정답 추출 로직 추가


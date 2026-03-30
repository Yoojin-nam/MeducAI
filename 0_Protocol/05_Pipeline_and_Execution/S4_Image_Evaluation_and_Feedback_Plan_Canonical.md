# S4 이미지 평가 및 피드백 계획 (Canonical)

**Status**: Canonical (implementation plan)  
**Version**: 1.0  
**Last Updated**: 2025-12-28  
**Scope**: S4에서 생성된 인포그래픽(테이블 비주얼)과 카드 이미지를 LLM 기반으로 평가하고, 피드백을 통해 S3/S4 프롬프트를 개선하는 계획

---

## 1. 개요

### 1.1 목표
- S4에서 생성된 이미지(카드 이미지 + 테이블 비주얼)의 품질을 LLM vision으로 평가
- 평가 결과를 S3/S4 프롬프트 개선으로 연결하는 반복 루프 구축
- S5 텍스트 평가와 유사한 구조로 "S5-Image" 또는 "S6" 단계 설계

### 1.2 평가 대상
- **카드 이미지**: `IMG__{run_tag}__{group_id}__{entity_id}__Q1.jpg`, `Q2.jpg`
- **테이블 비주얼**: `IMG__{run_tag}__{group_id}__TABLE.jpg` (또는 `TABLE__cluster_{n}.jpg`)
- **매핑 정보**: `s4_image_manifest__arm{arm}.jsonl`

---

## 2. 입력 스키마

### 2.1 S4 Image Manifest
파일: `2_Data/metadata/generated/<RUN_TAG>/s4_image_manifest__arm{arm}.jsonl`

```json
{
  "schema_version": "S4_IMAGE_MANIFEST_v1.0",
  "run_tag": "...",
  "group_id": "...",
  "entity_id": "...",
  "entity_name": "...",
  "card_role": "Q1" | "Q2" | null,
  "spec_kind": "S2_CARD_IMAGE" | "S1_TABLE_VISUAL",
  "media_filename": "IMG__...",
  "image_path": "/path/to/image.jpg",
  "generation_success": true | false,
  "image_required": true | false,
  "rag_enabled": false,
  "rag_queries_count": 0,
  "rag_sources_count": 0
}
```

### 2.2 S3 Image Spec (참조용)
파일: `2_Data/metadata/generated/<RUN_TAG>/s3_image_spec__arm{arm}.jsonl`

```json
{
  "schema_version": "S3_IMAGE_SPEC_v1.0",
  "group_id": "...",
  "entity_id": "...",
  "card_role": "Q1",
  "spec_kind": "S2_CARD_IMAGE",
  "prompt_en": "You are a board-certified radiologist...",
  "answer_text": "...",
  "image_hint_v2": { ... }
}
```

### 2.3 S2 Card Context (참조용)
`front`, `back`, `options[]`, `correct_index` 등 카드 텍스트 정보

---

## 3. 평가 항목 (평가 스키마 설계)

### 3.1 카드 이미지 평가 항목

#### 3.1.1 해부학 정확도 (Anatomical Accuracy)
- **기준**: 이미지가 의학적으로 정확한 해부학 구조를 보여주는가
- **평가**: `anatomical_accuracy` (0.0 | 0.5 | 1.0)
- **이슈 타입**: `anatomical_error`, `landmark_missing`, `laterality_error`

#### 3.1.2 프롬프트 준수도 (Prompt Compliance)
- **기준**: S3 `prompt_en`의 요구사항을 충족하는가
- **평가**: `prompt_compliance` (0.0 | 0.5 | 1.0)
- **이슈 타입**: `modality_mismatch`, `view_mismatch`, `key_finding_missing`

#### 3.1.3 카드 텍스트 일관성 (Card-Image Consistency)
- **기준**: 이미지가 카드의 `front`/`back` 텍스트와 일치하는가
- **평가**: `text_image_consistency` (0.0 | 0.5 | 1.0)
- **이슈 타입**: `diagnosis_mismatch`, `finding_contradiction`

#### 3.1.4 이미지 품질 (Image Quality)
- **기준**: 해상도, 가독성, 아티팩트
- **평가**: `image_quality` (1-5 Likert)
- **이슈 타입**: `low_resolution`, `artifacts`, `poor_contrast`

#### 3.1.5 안전성 (Safety)
- **기준**: 부적절한 이미지, 환자 식별 가능 정보
- **평가**: `safety_flag` (boolean)
- **이슈 타입**: `inappropriate_content`, `patient_identifier`

### 3.2 테이블 비주얼 평가 항목

#### 3.2.1 정보 전달력 (Information Clarity)
- **기준**: 테이블의 핵심 정보가 시각적으로 명확히 전달되는가
- **평가**: `information_clarity` (1-5 Likert)
- **이슈 타입**: `cluttered_layout`, `unclear_hierarchy`

#### 3.2.2 해부학 정확도
- **기준**: 인포그래픽의 해부학 구조/관계가 정확한가
- **평가**: `anatomical_accuracy` (0.0 | 0.5 | 1.0)
- **이슈 타입**: `anatomical_error`, `relationship_misrepresentation`

#### 3.2.3 프롬프트 준수도
- **기준**: S3 `infographic_prompt_en` 요구사항 충족
- **평가**: `prompt_compliance` (0.0 | 0.5 | 1.0)

---

## 4. 출력 스키마 (S5-Image / S6)

### 4.1 제안 스키마: `s6_image_validation__arm{arm}.jsonl`

```json
{
  "schema_version": "S6_IMAGE_VALIDATION_v1.0",
  "run_tag": "...",
  "group_id": "...",
  "arm": "...",
  "validation_timestamp": "2025-12-28T...Z",
  "inputs": {
    "s4_image_manifest_path": "2_Data/metadata/generated/.../s4_image_manifest__arm{arm}.jsonl",
    "s3_image_spec_path": "2_Data/metadata/generated/.../s3_image_spec__arm{arm}.jsonl",
    "s2_results_path": "2_Data/metadata/generated/.../s2_results__arm{arm}.jsonl"
  },
  "s6_model_info": {
    "image_eval_model": "gemini-3-pro-preview",
    "image_eval_thinking": true,
    "image_eval_rag_enabled": true
  },
  "card_images_validation": {
    "cards": [
      {
        "entity_id": "...",
        "entity_name": "...",
        "card_role": "Q1",
        "image_path": "/path/to/IMG__...__Q1.jpg",
        "blocking_error": false,
        "anatomical_accuracy": 1.0,
        "prompt_compliance": 1.0,
        "text_image_consistency": 1.0,
        "image_quality": 5,
        "safety_flag": false,
        "issues": [
          {
            "severity": "minor",
            "type": "key_finding_missing",
            "description": "...",
            "issue_code": "PROMPT_COMPLIANCE_MISSING_FINDING",
            "recommended_fix_target": "S3_PROMPT",
            "prompt_patch_hint": "Add explicit requirement for 'halo sign' visualization in prompt.",
            "confidence": 0.9
          }
        ],
        "rag_evidence": []
      }
    ],
    "summary": {
      "total_images": 16,
      "blocking_errors": 0,
      "mean_anatomical_accuracy": 0.95,
      "mean_prompt_compliance": 0.90,
      "mean_text_image_consistency": 0.92,
      "mean_image_quality": 4.5
    }
  },
  "table_visuals_validation": {
    "visuals": [
      {
        "group_id": "...",
        "cluster_id": "cluster_1" | null,
        "image_path": "/path/to/IMG__...__TABLE.jpg",
        "blocking_error": false,
        "information_clarity": 5,
        "anatomical_accuracy": 1.0,
        "prompt_compliance": 1.0,
        "issues": [],
        "rag_evidence": []
      }
    ],
    "summary": {
      "total_visuals": 2,
      "blocking_errors": 0,
      "mean_information_clarity": 4.8,
      "mean_anatomical_accuracy": 0.98
    }
  },
  "s6_snapshot_id": "s6_..."
}
```

---

## 5. 구현 계획

### 5.1 Phase 1: 기본 평가 인프라

#### 5.1.1 S6 Validator 스크립트 생성
- 파일: `3_Code/src/06_image_validator.py`
- 기능:
  - S4 manifest 읽기
  - 이미지 파일 경로 추출
  - Gemini vision API로 이미지 평가
  - S3 spec, S2 card context와 함께 프롬프트 구성

#### 5.1.2 S6 프롬프트 작성
- `3_Code/prompt/S6_SYSTEM__v1.md`: 이미지 평가 역할 정의
- `3_Code/prompt/S6_USER_CARD_IMAGE__v1.md`: 카드 이미지 평가 프롬프트
- `3_Code/prompt/S6_USER_TABLE_VISUAL__v1.md`: 테이블 비주얼 평가 프롬프트

#### 5.1.3 S6 리포트 생성
- 파일: `3_Code/src/06_image_report.py`
- S5 리포트와 유사한 구조:
  - Summary (blocking 비율, 평균 점수)
  - Issue taxonomy
  - Patch backlog (S3/S4 프롬프트 개선 제안)

### 5.2 Phase 2: 평가 항목 세분화

#### 5.2.1 해부학 정확도 평가 강화
- `image_hint_v2.anatomy` 필드와 실제 이미지 비교
- Landmark, laterality, orientation 일치도 체크

#### 5.2.2 프롬프트 준수도 평가 강화
- S3 `prompt_en`의 키워드/요구사항 추출
- 이미지에서 해당 요소 존재 여부 확인

### 5.3 Phase 3: 피드백 루프

#### 5.3.1 S3 프롬프트 개선
- `recommended_fix_target=S3_PROMPT`인 이슈 추출
- `prompt_patch_hint`를 바탕으로 S3 프롬프트 수정
- 예: `S3_EXAM_USER__v9.md`에 "halo sign 시각화 필수" 규칙 추가

#### 5.3.2 S4 프롬프트 개선 (필요시)
- S4는 주로 S3 spec을 그대로 사용하지만, 필요시 S4 전용 프롬프트 보강

---

## 6. 프롬프트 개선 워크플로우 (S5와 유사)

```
1. S4 이미지 생성 완료
   ↓
2. S6 이미지 평가 실행
   python3 3_Code/src/06_image_validator.py \
     --base_dir ... \
     --run_tag <RUN_TAG> \
     --arm <ARM>
   ↓
3. S6 리포트 생성
   python3 3_Code/src/06_image_report.py \
     --base_dir ... \
     --run_tag <RUN_TAG> \
     --arm <ARM>
   ↓
4. Patch Backlog에서 S3/S4 프롬프트 개선 항목 선정
   - P0: safety_flag=true, anatomical_accuracy=0.0
   - P1: prompt_compliance < 0.8, text_image_consistency < 0.8
   ↓
5. S3/S4 프롬프트에 구체적 규칙 추가
   - 예: "Halo sign은 반드시 시각화되어야 함"
   - 예: "Laterality는 명확히 표시 (L/R/Midline)"
   ↓
6. 새 dev run_tag로 재생성 (동일 그룹)
   ↓
7. S6 재검증 → 전/후 비교
   ↓
8. 개선 확인되면 freeze
```

---

## 7. 기술적 고려사항

### 7.1 Gemini Vision API 사용
- 이미지 파일을 base64 인코딩 또는 파일 경로로 전달
- Multimodal prompt 구성 (이미지 + 텍스트)
- Vision model: `gemini-3-pro-preview` (또는 `gemini-2.0-flash-exp`)

### 7.2 이미지 파일 읽기
- PIL/Pillow로 이미지 로드 및 검증
- 파일 존재 여부, 형식(JPEG/PNG) 체크
- 이미지 크기/해상도 로깅

### 7.3 컨텍스트 구성
- S3 `prompt_en`: 원본 프롬프트 요구사항
- S2 `front`/`back`: 카드 텍스트 (일관성 체크용)
- `image_hint_v2`: 해부학 제약 (정확도 체크용)

---

## 8. 체크리스트 (구현 시)

### 8.1 Phase 1 (기본 인프라)
- [ ] `06_image_validator.py` 스크립트 생성
- [ ] S4 manifest 읽기 로직
- [ ] 이미지 파일 경로 추출
- [ ] Gemini vision API 호출 (이미지 + 프롬프트)
- [ ] S6 출력 스키마로 JSON 생성
- [ ] `06_image_report.py` 리포트 생성
- [ ] S6 프롬프트 작성 (`S6_SYSTEM__v1.md`, `S6_USER_CARD_IMAGE__v1.md`, `S6_USER_TABLE_VISUAL__v1.md`)

### 8.2 Phase 2 (평가 강화)
- [ ] 해부학 정확도 평가 세분화
- [ ] 프롬프트 준수도 평가 세분화
- [ ] 카드-이미지 일관성 평가 강화

### 8.3 Phase 3 (피드백 루프)
- [ ] Patch Backlog에서 S3 프롬프트 개선 항목 추출
- [ ] S3 프롬프트 버전 업데이트
- [ ] 재생성 → 재검증 → 비교

---

## 9. 참고 파일

- S4 이미지 생성: `3_Code/src/04_s4_image_generator.py`
- S3 이미지 스펙: `3_Code/src/03_s3_policy_resolver.py`
- S4 manifest 스키마: `0_Protocol/04_Step_Contracts/S3_S4_Code_Documentation.md`
- S5 텍스트 평가 방법론: `0_Protocol/05_Pipeline_and_Execution/S5_Prompt_Refinement_Methodology_Canonical.md`

---

## 10. 예상 이슈 및 해결

### 10.1 이미지 파일 누락
- **문제**: `generation_success=false`인 경우 평가 스킵
- **해결**: `image_required=true`인데 파일이 없으면 `blocking_error=true`로 기록

### 10.2 Vision API 비용/지연
- **문제**: 이미지당 API 호출 비용 및 지연
- **해결**: 병렬 처리 (`workers_s6`), 샘플링 옵션 (`--sample N`)

### 10.3 평가 주관성
- **문제**: LLM judge의 평가가 일관성 없을 수 있음
- **해결**: 명확한 rubric, multi-judge consensus (옵션), confidence score 기록

---

## 11. 다음 단계

1. **S6 Validator 구현**: `06_image_validator.py` 작성
2. **S6 프롬프트 작성**: 평가 rubric 명확화
3. **S6 리포트 생성**: S5 리포트와 유사한 구조
4. **피드백 루프 테스트**: dev run_tag에서 1-2 그룹으로 검증
5. **확장**: 전체 그룹으로 확장 후 freeze


# S5 이미지 평가 통합 기능 인계서

**작성일**: 2025-12-29  
**인계 대상**: 실험 계획 에이전트 / S5 실험 담당자  
**관련 문서**: 
- `S5_이미지_평가_통합_계획_5d1606b8.plan.md`
- `S0_QA_Continuous_Improvement_Handoff.md`
- `S5_Validation_Schema_Canonical.md`

---

## 1. 개요

S5 검증 파이프라인에 **이미지 평가 기능**을 통합하여 텍스트와 이미지를 함께 평가할 수 있도록 개선했습니다. 이는 QA 평가단 피드백을 반영한 것으로, 이미지-텍스트 일관성, 모달리티 일치, 해부학적 정확성 등을 자동으로 검증합니다.

> **S5R 라운드 정렬(권장)**: 이미지(S4) 프롬프트 개선도 S1/S2와 동일한 **S5R 라운드**로 관리합니다.
> Canonical: `0_Protocol/05_Pipeline_and_Execution/S5_Version_Naming_S5R_Canonical.md`

### 1.1 주요 변경사항

1. **Multimodal Input 지원**: Gemini Vision API를 활용하여 텍스트와 이미지를 동시에 평가
2. **카드 이미지 평가**: Q1/Q2 카드의 이미지와 텍스트 일관성 검증
3. **테이블 인포그래픽 평가**: S1 테이블과 인포그래픽 일관성 검증
4. **QA 피드백 반영**: 모달리티 일치, 랜드마크 검증, 답-해설 일관성, 중복 정답 검증
5. **OCR 기능**: 이미지 내 텍스트 추출 및 검증

---

## 2. 기술적 구현

### 2.1 Multimodal API 통합

**파일**: `3_Code/src/01_generate_json.py`

- `call_llm()` 함수에 `image_paths: Optional[List[Path]]` 파라미터 추가
- Gemini Vision API를 통한 이미지 전달 지원
- Subprocess watchdog에서도 multimodal input 지원 (base64 인코딩)

**사용 예시**:
```python
parsed_json, err, meta, raw_text = call_llm(
    provider="gemini",
    model_name="gemini-3-flash-preview",
    system_prompt=system_prompt,
    user_prompt=user_prompt,
    image_paths=[image_path],  # 이미지 경로 전달
    # ... 기타 파라미터
)
```

### 2.2 S5 Validator 확장

**파일**: `3_Code/src/05_s5_validator.py`

**주요 함수 변경**:
- `validate_s2_card()`: 카드 이미지 평가 추가
- `validate_s1_table()`: 테이블 인포그래픽 평가 추가
- `load_s4_manifest()`: S4 이미지 매니페스트 로드
- `load_s3_image_specs()`: S3 이미지 스펙 로드
- `resolve_image_path()`: 이미지 파일 경로 해석

**입력 데이터**:
- `s4_image_manifest__arm{arm}.jsonl`: 생성된 이미지 메타데이터
- `s3_image_spec__arm{arm}.jsonl`: 이미지 생성 스펙
- `images/` 디렉토리: 실제 이미지 파일

**실험 run_tag 권장 패턴(S5R 기반)**:
- `DEV_armG_mm_S5R0_before_rerun_preFix_YYYYMMDD_HHMMSS__repN`
- `DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__repN`

> 동일한 run_tag 단위로 S1/S2 생성 → S3 spec → S4 이미지 → S5(VLM) 검증이 연결되며, 이미지 경로는 `IMG__{run_tag}__...`로 추적됩니다.

### 2.3 프롬프트 파일

**새로 추가된 프롬프트**:
- `3_Code/prompt/S5_USER_CARD_IMAGE__v1.md`: 카드 이미지 평가용
- `3_Code/prompt/S5_USER_TABLE_VISUAL__v1.md`: 테이블 인포그래픽 평가용

**프롬프트 레지스트리**: `3_Code/prompt/_registry.json`에 등록됨

---

## 3. 평가 항목 및 메트릭

### 3.1 카드 이미지 평가 (`card_image_validation`)

**평가 항목**:

1. **Anatomical Accuracy** (0.0 | 0.5 | 1.0)
   - 해부학적 구조의 의학적 정확성
   - **랜드마크 검증**: `key_landmarks_to_include` 목록 확인
   - 이슈 타입: `anatomical_error`, `landmark_missing`, `laterality_error`

2. **Prompt Compliance** (0.0 | 0.5 | 1.0)
   - S3 `prompt_en` 요구사항 준수
   - **모달리티 일치 검증** (CRITICAL):
     - 지문에서 모달리티 키워드 추출 (CT, MRI, XR, US 등)
     - `image_hint.modality_preferred`와 비교
     - 실제 이미지의 모달리티 분석
     - 불일치 시 `blocking_error=true`
   - 이슈 타입: `modality_mismatch_text_hint`, `modality_mismatch_image_actual`, `modality_mismatch_text_image`, `view_mismatch`, `key_finding_missing`

3. **Text-Image Consistency** (0.0 | 0.5 | 1.0)
   - 카드 텍스트와 이미지 일관성
   - 이슈 타입: `diagnosis_mismatch`, `finding_contradiction`

4. **Image Quality** (1-5 Likert)
   - 해상도, 가독성, 아티팩트, 대비
   - **OCR/Text Detection**:
     - EXAM 이미지: 텍스트가 없어야 함 (발견 시 `blocking_error`)
     - CONCEPT 이미지: 텍스트 추출 및 검증
   - 이슈 타입: `low_resolution`, `artifacts`, `poor_contrast`, `unexpected_text`, `missing_text`, `unreadable_text`

5. **Safety** (boolean)
   - 부적절한 콘텐츠, 환자 식별 정보
   - 이슈 타입: `inappropriate_content`, `patient_identifier`

**추가 필드**:
- `modality_match`: 모달리티 일치 여부 (boolean)
- `landmarks_present`: 랜드마크 존재 여부 (boolean)
- `extracted_text`: OCR로 추출된 텍스트 (string | null)
- `text_detected`: 텍스트 발견 여부 (boolean)

### 3.2 테이블 인포그래픽 평가 (`table_visual_validation`)

**평가 항목**:

1. **Information Clarity** (1-5 Likert)
   - 정보 전달 명확성, 레이아웃, 계층 구조
   - **OCR 검증**: 모든 텍스트 추출 및 검증
   - 이슈 타입: `cluttered_layout`, `unclear_hierarchy`, `missing_text`, `unreadable_text`, `text_error`

2. **Anatomical Accuracy** (0.0 | 0.5 | 1.0)
   - 해부학적 구조/관계 정확성
   - 이슈 타입: `anatomical_error`, `relationship_misrepresentation`

3. **Prompt Compliance** (0.0 | 0.5 | 1.0)
   - S3 `infographic_prompt_en` 요구사항 준수

4. **Table-Visual Consistency** (0.0 | 0.5 | 1.0)
   - S1 테이블과 인포그래픽 일관성
   - **텍스트 기반 검증**: OCR로 엔티티 이름 추출 및 비교
   - 이슈 타입: `content_mismatch`, `entity_missing`, `entity_name_mismatch`

**추가 필드**:
- `extracted_text`: OCR로 추출된 모든 텍스트
- `entities_found_in_text`: 텍스트에서 추출한 엔티티 이름 배열

### 3.3 카드 텍스트 평가 확장

**MCQ 카드 추가 검증**:

1. **Answer-Explanation Consistency** (boolean)
   - `correct_index`와 `back` 해설 일치 여부
   - 불일치 시 `blocking_error=true`
   - 이슈 타입: `answer_explanation_mismatch`

2. **Multiple Answer Risk** (boolean)
   - 여러 정답 가능성 검증
   - 감별 진단 시나리오 고려
   - 이슈 타입: `multiple_answer_possible`

---

## 4. 출력 스키마

### 4.1 S5 Validation Schema 확장

**카드 검증 결과** (`s2_cards_validation.cards[]`):
```json
{
  "card_id": "...",
  "card_role": "Q1",
  "blocking_error": false,
  "technical_accuracy": 1.0,
  "educational_quality": 5,
  "issues": [...],
  "rag_evidence": [...],
  "card_image_validation": {
    "blocking_error": false,
    "anatomical_accuracy": 1.0,
    "prompt_compliance": 1.0,
    "text_image_consistency": 1.0,
    "image_quality": 5,
    "safety_flag": false,
    "modality_match": true,
    "landmarks_present": true,
    "extracted_text": null,
    "text_detected": false,
    "issues": [...],
    "image_path": "/path/to/image.jpg"
  },
  "answer_explanation_consistency": true,
  "multiple_answer_risk": false
}
```

**테이블 검증 결과** (`s1_table_validation`):
```json
{
  "blocking_error": false,
  "technical_accuracy": 1.0,
  "educational_quality": 4,
  "issues": [...],
  "rag_evidence": [...],
  "table_visual_validation": {
    "blocking_error": false,
    "information_clarity": 5,
    "anatomical_accuracy": 1.0,
    "prompt_compliance": 1.0,
    "table_visual_consistency": 1.0,
    "extracted_text": "Entity1: Description1\n...",
    "entities_found_in_text": ["Entity1", "Entity2", "..."],
    "issues": [...],
    "image_path": "/path/to/infographic.jpg"
  }
}
```

### 4.2 리포트 생성

**파일**: `3_Code/src/tools/s5/s5_report.py`

리포트에 다음 섹션이 추가됨:
- **Card Image Validation Summary**: 카드 이미지 평가 요약
- **Table Visual Validation Summary**: 테이블 인포그래픽 평가 요약
- **Image-related Issues**: 이미지 관련 이슈 taxonomy
- **Patch backlog**: 이미지 관련 프롬프트 개선 제안

---

## 5. 실험 계획 가이드

### 5.1 Baseline 측정

**목적**: 현재 이미지 품질의 정량적 측정

**실행 방법**:
```bash
# 기존 run_tag의 S1~S4 데이터로 S5 검증 실행
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag <EXISTING_RUN_TAG> \
  --arm <ARM> \
  --workers_s5 2
```

**측정 메트릭**:
- `card_image_validation`의 각 항목별 평균 점수
- 이슈 타입별 빈도 및 비율
- `blocking_error` 비율
- 모달리티 불일치 비율
- 랜드마크 누락 비율

**리포트 생성**:
```bash
python3 -m tools.s5.s5_report \
  --base_dir . \
  --run_tag <EXISTING_RUN_TAG> \
  --arm <ARM>
```

### 5.2 문제점 분석

**S5 리포트에서 확인할 항목**:

1. **이미지 평가 요약 섹션**:
   - 평균 `anatomical_accuracy`, `prompt_compliance`, `text_image_consistency`
   - `blocking_error` 비율

2. **이슈 Taxonomy**:
   - 가장 빈번한 이슈 타입 (예: `modality_mismatch`, `landmark_missing`)
   - 심각도별 분포

3. **Patch backlog**:
   - 프롬프트 개선 제안 (`recommended_fix_target`, `prompt_patch_hint`)

**분석 예시**:
- "모달리티 불일치가 80% 발생 → S4 프롬프트에 모달리티 검증 강화 필요"
- "랜드마크 누락이 60% 발생 → S3 `key_landmarks_to_include` 명시 강화 필요"

### 5.3 프롬프트 개선 실험

**가설 수립**:
- 문제 패턴에 맞춘 프롬프트 수정 가설
- 예: "S4_EXAM_SYSTEM에 모달리티 검증 체크리스트 추가 → 모달리티 불일치 감소"

**실험 실행**:
1. 프롬프트 수정 (새 버전 생성)
2. S4 재실행 (새 run_tag 또는 기존 run_tag 덮어쓰기)
3. S5 재검증
4. Before/After 비교

**비교 메트릭**:
- 각 평가 항목의 평균 점수 변화
- 이슈 타입별 빈도 변화
- `blocking_error` 비율 변화
- 통계적 유의성 확인 (필요시)

### 5.4 실험 설계 예시

**실험 1: 모달리티 일치 개선**
- **가설**: S4 프롬프트에 모달리티 검증 체크리스트 추가 시 모달리티 불일치 감소
- **변수**: `S4_EXAM_SYSTEM__v9.md` (모달리티 검증 강화)
- **측정**: `card_image_validation.prompt_compliance`, `modality_mismatch` 이슈 빈도

**실험 2: 랜드마크 포함 개선**
- **가설**: S3 `key_landmarks_to_include` 명시 강화 시 랜드마크 누락 감소
- **변수**: S2 프롬프트에서 `image_hint_v2.anatomy.key_landmarks_to_include` 생성 강화
- **측정**: `card_image_validation.anatomical_accuracy`, `landmark_missing` 이슈 빈도

**실험 3: 텍스트-이미지 일관성 개선**
- **가설**: S2 프롬프트에 이미지-텍스트 일관성 자가 점검 추가 시 일관성 향상
- **변수**: `S2_SYSTEM__v11.md` (이미지-텍스트 일관성 체크리스트)
- **측정**: `card_image_validation.text_image_consistency`, `diagnosis_mismatch` 이슈 빈도

---

## 6. 주의사항

### 6.1 이미지 파일 경로

- S5 검증은 `s4_image_manifest__arm{arm}.jsonl`의 `image_path`를 사용
- 이미지 파일이 실제로 존재해야 평가 가능
- 이미지가 없으면 텍스트만 평가 (하위 호환성 유지)

### 6.2 모델 선택

- **카드 이미지 평가**: `gemini-3-flash-preview` (multimodal 지원)
- **테이블 인포그래픽 평가**: `gemini-3-pro-preview` (더 복잡한 인포그래픽 분석)

환경 변수로 변경 가능:
- `S5_S2_CARD_MODEL`: 카드 검증 모델
- `S5_S1_TABLE_MODEL`: 테이블 검증 모델

### 6.3 토큰 사용량

- 이미지 포함 시 `input_tokens`가 크게 증가 (약 8,000-10,000 tokens)
- 비용 및 지연 시간 고려 필요
- 이미지가 없는 경우 기존과 동일한 토큰 사용량

### 6.4 OCR 기능

- Gemini Vision API의 내장 OCR 기능 활용
- 프롬프트에서 명시적으로 OCR 요청 시 더 안정적
- EXAM 이미지: 텍스트가 없어야 함 (발견 시 에러)
- CONCEPT/인포그래픽: 텍스트 추출 및 검증

---

## 7. 참고 자료

### 7.1 관련 문서
- `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Schema_Canonical.md`: 스키마 정의
- `0_Protocol/06_QA_and_Study/QA_Operations/S0_QA_Continuous_Improvement_Handoff.md`: QA 피드백
- `0_Protocol/05_Pipeline_and_Execution/S5_Prompt_Refinement_Methodology_Canonical.md`: 프롬프트 개선 방법론

### 7.2 코드 파일
- `3_Code/src/05_s5_validator.py`: S5 검증 메인 로직
- `3_Code/src/tools/s5/s5_report.py`: 리포트 생성
- `3_Code/src/01_generate_json.py`: Multimodal API 통합
- `3_Code/prompt/S5_USER_CARD_IMAGE__v1.md`: 카드 이미지 평가 프롬프트
- `3_Code/prompt/S5_USER_TABLE_VISUAL__v1.md`: 테이블 인포그래픽 평가 프롬프트

### 7.3 샘플 데이터
- `2_Data/metadata/generated/TEST_PROGRESS_20251229_145011/`: 테스트 데이터
  - `s4_image_manifest__armA.jsonl`: 이미지 매니페스트
  - `s3_image_spec__armA.jsonl`: 이미지 스펙
  - `images/`: 생성된 이미지 파일
  - `s5_validation__armA.jsonl`: 검증 결과

---

## 8. 다음 단계

1. **Baseline 측정**: 기존 run_tag로 S5 검증 실행 및 리포트 생성
2. **문제점 분석**: S5 리포트에서 이미지 품질 문제 패턴 파악
3. **가설 수립**: 문제 패턴에 맞춘 프롬프트 개선 가설
4. **실험 실행**: 개선된 프롬프트로 S4 재실행 및 S5 재검증
5. **결과 비교**: Before/After 메트릭 비교 및 개선 효과 측정
6. **반복**: 필요시 추가 개선 실험

---

**작성자**: MeducAI Development Team  
**최종 업데이트**: 2025-12-29  
**버전**: 1.0


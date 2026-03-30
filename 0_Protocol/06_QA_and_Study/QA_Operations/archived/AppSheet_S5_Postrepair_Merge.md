# AppSheet S5 Postrepair 병합 가이드

**작성일:** 2025-01-01  
**목적:** S5_postrepair 데이터를 별도 파일이 아닌 S5.csv에 병합하는 방식 문서화

---

## 변경 사항 요약

### 이전 방식 (Deprecated)
- **S5.csv**: Baseline S5 validation 결과만 포함
- **S5_postrepair.csv**: Postrepair S5 validation 결과를 별도 파일로 생성

### 현재 방식 (2025-01-01 이후)
- **S5.csv**: Baseline S5 validation 결과 + S4 regeneration 콘텐츠 (`s5_regenerated_*`) 포함
- **S5_postrepair.csv**: 더 이상 생성되지 않음 (제거됨)
- **Postrepair S5 validation 결과**: AppSheet에 export하지 않음 (내부 분석용으로만 사용)

---

## S5.csv 컬럼 구조

### Baseline S5 컬럼 (기존 유지)
- `s5_blocking_error`
- `s5_technical_accuracy`
- `s5_educational_quality`
- `s5_issues_json`
- `s5_description`
- `s5_evidence_ref`
- `s5_rag_evidence_json`
- `s5_card_image_blocking_error`
- `s5_card_image_anatomical_accuracy`
- `s5_card_image_prompt_compliance`
- `s5_card_image_text_image_consistency`
- `s5_card_image_quality`
- `s5_card_image_safety_flag`
- `s5_card_image_issues_json`
- `s5_regenerated_front` (S4 regeneration: 재생성된 카드 문제 텍스트)
- `s5_regenerated_back` (S4 regeneration: 재생성된 카드 정답 텍스트)
- `s5_regenerated_image_filename` (S4 regeneration: 재생성된 이미지)
- `s5_regeneration_timestamp` (재생성 시점)
- `s5_regeneration_trigger_score` (재생성 트리거 점수)
- `s5_was_regenerated` (재생성 여부: 0 또는 1)

### Postrepair S5 validation 결과 (AppSheet에 export하지 않음)
**중요:** Postrepair S5 validation 결과(`s5_postrepair_*`)는 AppSheet에 export하지 않습니다.

**이유:**
- S4 regeneration workflow는 재생성된 카드 내용(`s5_regenerated_*`)만 사용자에게 보여줍니다
- 사용자는 재생성된 카드를 보고 `accept_ai_correction`으로 수용/거부만 결정합니다
- Postrepair S5 validation 결과는 내부 분석용으로만 사용됩니다 (S6 Export Gate의 `postrepair_ok` 확인 등)

---

## 데이터 구조

### S4 Regeneration이 없는 경우
- `s5_was_regenerated = 0`
- 모든 `s5_regenerated_*` 컬럼은 빈 값

### S4 Regeneration이 있는 경우
- `s5_was_regenerated = 1`
- 재생성된 카드 내용이 `s5_regenerated_*` 컬럼에 기록됨
- 사용자는 재생성된 카드를 보고 `accept_ai_correction`으로 수용/거부 결정

### Postrepair S5 validation 데이터
- Postrepair S5 validation 결과는 JSONL 파일에만 존재하며 AppSheet에는 export되지 않음
- 내부 분석용으로만 사용 (S6 Export Gate 등)

---

## 코드 변경사항

### `export_appsheet_tables.py`

#### 변경 전:
```python
# S5.csv: baseline만 포함
# S5_postrepair.csv: 별도 파일로 생성
```

#### 변경 후:
```python
# S5.csv: baseline + s5_regenerated_* (S4 regeneration 콘텐츠) 포함
# S5_postrepair.csv: 생성하지 않음
# Postrepair S5 validation: AppSheet에 export하지 않음 (내부 분석용)
```

**구체적 변경:**
1. S5.csv 생성 시 `s5_regenerated_*` 컬럼 포함 (S4 regeneration 콘텐츠)
2. S5_postrepair.csv 생성 코드 제거
3. Postrepair S5 validation 결과(`s5_postrepair_*`)는 AppSheet에 export하지 않음
4. Postrepair 데이터는 JSONL 파일에만 존재하며 내부 분석용으로만 사용

---

## AppSheet 설정

### S5 테이블 컬럼 (기존 유지)

S5 테이블에는 다음 컬럼들이 포함됩니다:
- Baseline S5 validation 결과 (`s5_blocking_error`, `s5_technical_accuracy`, 등)
- S4 regeneration 콘텐츠 (`s5_regenerated_front`, `s5_regenerated_back`, 등)

**중요:** Postrepair S5 validation 컬럼(`s5_postrepair_*`)은 AppSheet에 export되지 않으므로 추가할 필요가 없습니다.

### S4 Regeneration Workflow

1. **재생성된 카드 표시 (S5 테이블):**
   - `s5_regenerated_front` (재생성된 문제 텍스트)
   - `s5_regenerated_back` (재생성된 정답 텍스트)
   - `s5_regenerated_image_filename` (재생성된 이미지)
   - S5 테이블을 통해 재생성된 카드 내용 확인

2. **사용자 결정 (Ratings 테이블에 기록):**
   - `accept_ai_correction` (Enum: ACCEPT/REJECT) - **Ratings 테이블**
   - `ai_correction_quality` (Number, 1-5) - **Ratings 테이블**
   - `ai_correction_comment` (LongText) - **Ratings 테이블**
   - 사용자는 S5 테이블의 재생성된 카드를 보고, Ratings 테이블에서 수용/거부 결정

3. **Postrepair S5 validation 결과는 표시하지 않음:**
   - 내부 분석용으로만 사용 (S6 Export Gate 등)

---

## 사용 시나리오

### 시나리오 1: Baseline만 있는 경우 (재생성 없음)
- `s5_was_regenerated = 0`
- 모든 `s5_regenerated_*` 컬럼은 빈 값
- Baseline S5 결과만 사용

### 시나리오 2: S4 Regeneration이 있는 경우
- `s5_was_regenerated = 1`
- **S5 테이블**: 재생성된 카드 내용(`s5_regenerated_*`)이 표시됨
- **Ratings 테이블**: 사용자가 재생성된 카드를 보고 `accept_ai_correction`으로 수용/거부 결정을 기록
- Postrepair S5 validation 결과는 사용자에게 표시되지 않음 (내부 분석용)

### 시나리오 3: S6 Export Gate에서 사용
- Postrepair S5 validation 결과는 JSONL 파일에서 읽어서 `postrepair_ok` 확인
- `use_repaired` 결정에 사용 (baseline vs repaired 선택)

---

## 마이그레이션 가이드

### 기존 S5_postrepair.csv가 있는 경우

**옵션 1: 수동 병합 (일회성)**
1. 기존 S5.csv와 S5_postrepair.csv를 읽기
2. `card_uid`를 기준으로 LEFT JOIN
3. Postrepair 컬럼을 S5.csv에 추가
4. 새로운 S5.csv로 교체

**옵션 2: 재생성 (권장)**
1. `export_appsheet_tables.py`를 최신 버전으로 실행
2. 자동으로 병합된 S5.csv 생성
3. AppSheet에서 S5 테이블 업데이트

### AppSheet 테이블 업데이트

1. **기존 S5_postrepair 테이블이 있는 경우:**
   - S5 테이블에 postrepair 컬럼 추가
   - S5_postrepair 테이블은 더 이상 사용하지 않음 (선택적으로 삭제 가능)

2. **S5 테이블에 postrepair 컬럼 추가:**
   - 위의 "AppSheet 설정" 섹션 참고

---

## 장점

### 1. 단일 테이블 관리
- Baseline과 Postrepair를 한 테이블에서 관리
- AppSheet Reference 관계 단순화

### 2. 비교 분석 용이
- 같은 행에서 Baseline과 Postrepair 직접 비교
- Virtual Column으로 개선도 계산 가능

### 3. 데이터 일관성
- `card_uid` 기준으로 항상 일대일 매핑
- LEFT JOIN으로 누락 방지

---

## Cards 테이블 구조

### Cards.csv에는 재생성 관련 컬럼이 없음

**중요:** Cards 테이블에는 재생성 관련 컬럼(`s5_was_regenerated`, `s2_regenerated_front/back` 등)이 포함되지 않습니다.

**이유:**
- Cards 테이블은 **원본 카드 내용**만 포함합니다 (`front`, `back`, `image_filename` 등)
- 재생성된 카드 내용은 **S5 테이블의 `s5_regenerated_*` 컬럼**으로만 관리됩니다
- 사용자는 S5 테이블을 통해 재생성된 카드를 확인하고, **Ratings 테이블**에서 `accept_ai_correction`으로 수용/거부 결정을 기록합니다

**Cards.csv 컬럼 (재생성 관련 없음):**
- `card_uid`, `card_id`, `run_tag`, `arm`, `group_id`, `group_path`
- `entity_id`, `entity_name`, `card_idx_in_entity`, `card_role`, `card_type`
- `front`, `back` (원본 카드 내용)
- `tags_csv`, `tags_json`, `mcq_options_json`, `mcq_correct_index`
- `image_hint_json`, `image_hint_v2_json`, `image_filename` (원본 이미지)

**재생성 관련 정보 관리:**
- **S5 테이블**: 재생성된 카드 내용 표시
  - `s5_was_regenerated`: 재생성 여부 (0 또는 1)
  - `s5_regenerated_front`: 재생성된 문제 텍스트
  - `s5_regenerated_back`: 재생성된 정답 텍스트
  - `s5_regenerated_image_filename`: 재생성된 이미지
- **Ratings 테이블**: 사용자 결정 기록
  - `accept_ai_correction`: 수용/거부 결정 (ACCEPT/REJECT)
  - `ai_correction_quality`: 품질 평가 (1-5)
  - `ai_correction_comment`: 수용/거부 근거

---

## 참고 문서

- **Exporter 코드**: `3_Code/src/tools/final_qa/export_appsheet_tables.py`
- **S5 Regenerated Columns**: `AppSheet_S5_Regenerated_Columns_Merge.md`
- **S6 Export Gate**: `06_s6_export_gate.py` (postrepair_ok 확인 로직)

---

**문서 버전:** 1.1  
**최종 업데이트:** 2025-01-01


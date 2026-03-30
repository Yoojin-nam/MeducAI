# AppSheet 이미지 평가 항목 추가 요약

**작성일:** 2025-01-01  
**목적:** S5(LLM) 이미지 평가와 사람 평가를 비교하기 위한 항목 추가

---

## 추가된 컬럼 (4개)

### 1. `image_blocking_error_pre/post` (Yes/No)
- **용도:** 이미지에 학습자나 임상 판단을 잘못 유도할 수 있는 심각한 오류가 있는지 평가
- **S5 대응:** `card_image_validation.blocking_error`
- **평가 시점:** Post 평가 단계 (이미지 확인 후)
- **주요 체크 항목:** 모달리티 불일치, 좌우 구분 오류, 심각한 해부학적 오류

### 2. `image_anatomical_accuracy_pre/post` (Enum: 0, 0.5, 1)
- **용도:** 이미지의 해부학적 정확성 평가
- **S5 대응:** `card_image_validation.anatomical_accuracy`
- **평가 시점:** Post 평가 단계 (이미지 확인 후)

### 3. `image_quality_pre/post` (Enum: 1-5)
- **용도:** 이미지 품질 종합 평가 (해상도, 가독성, 대비, 아티팩트)
- **S5 대응:** `card_image_validation.image_quality`
- **평가 시점:** Post 평가 단계 (이미지 확인 후)

### 4. `image_text_consistency_pre/post` (Enum: 0, 0.5, 1)
- **용도:** 이미지와 카드 텍스트의 일관성 평가
- **S5 대응:** `card_image_validation.text_image_consistency`
- **평가 시점:** Post 평가 단계 (이미지 확인 후)

---

## AppSheet 설정 절차

### 1단계: Google Sheets에 컬럼 추가

**Ratings 탭에 다음 컬럼 추가:**
- `image_blocking_error_pre` (Yes/No 또는 Text)
- `image_anatomical_accuracy_pre` (Number 또는 Text)
- `image_quality_pre` (Number 또는 Text)
- `image_text_consistency_pre` (Number 또는 Text)
- `image_blocking_error_post` (Yes/No 또는 Text)
- `image_anatomical_accuracy_post` (Number 또는 Text)
- `image_quality_post` (Number 또는 Text)
- `image_text_consistency_post` (Number 또는 Text)

### 2단계: AppSheet에서 컬럼 타입 설정

#### `image_blocking_error_pre/post`
1. `Data` → `Tables` → `Ratings` → `image_blocking_error_pre` 클릭
2. `Type`: `Yes/No` 선택
3. `Editable_If`: Post는 `AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]))`
4. `Display name`: `이미지 차단 오류`
5. `Description`: Section 3.2.1의 간결 버전 사용
6. `Save`

#### `image_anatomical_accuracy_pre/post`
1. `Data` → `Tables` → `Ratings` → `image_anatomical_accuracy_pre` 클릭
2. `Type`: `Enum` 선택
3. `Options`: `0`, `0.5`, `1` (각각 한 줄씩)
4. `Editable_If`: Post는 `AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]))`
5. `Display name`: `이미지 해부학적 정확도`
6. `Description`: Section 3.2.1의 간결 버전 사용
7. `Save`

#### `image_quality_pre/post`
1. `Data` → `Tables` → `Ratings` → `image_quality_pre` 클릭
2. `Type`: `Enum` 선택
3. `Options`: `1`, `2`, `3`, `4`, `5` (각각 한 줄씩)
4. `Editable_If`: Post는 `AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]))`
5. `Display name`: `이미지 품질`
6. `Description`: Section 3.2.3의 간결 버전 사용
7. `Save`

#### `image_text_consistency_pre/post`
1. `Data` → `Tables` → `Ratings` → `image_text_consistency_pre` 클릭
2. `Type`: `Enum` 선택
3. `Options`: `0`, `0.5`, `1` (각각 한 줄씩)
4. `Editable_If`: Post는 `AND(NOT(ISBLANK([post_started_ts])), ISBLANK([post_submitted_ts]))`
5. `Display name`: `이미지-텍스트 일관성`
6. `Description`: Section 3.2.4의 간결 버전 사용
7. `Save`

### 3단계: Detail View에 컬럼 추가

**Ratings Detail View에서:**
1. Post 평가 섹션에 이미지 평가 항목 추가
2. 컬럼 순서:
   - S5 Reference 섹션 다음
   - Post Input Fields 이전 또는 이후
3. `Show_If` 조건:
   - `NOT(ISBLANK([post_started_ts]))` - S5를 확인한 후에만 표시

---

## 평가 워크플로우

### Pre 평가 단계
- **이미지 평가 항목은 평가하지 않음**
- Pre 평가는 이미지를 보기 전에 수행하므로 이미지 평가 불가

### Post 평가 단계
1. "Reveal S5 Results" 버튼 클릭
2. S5 결과 확인 (이미지 포함)
3. 이미지를 직접 보고 평가:
   - `image_blocking_error_post` (1번 - 가장 중요)
   - `image_anatomical_accuracy_post`
   - `image_quality_post`
   - `image_text_consistency_post`
4. S5 결과와 비교 (선택사항)
5. "Submit Post-S5 Rating" 버튼 클릭

---

## S5와의 비교 방법

### S5 결과 확인
- S5 결과는 `S5` 테이블의 `card_image_validation` 섹션에 저장됨
- AppSheet Detail View에서 S5 Reference 섹션으로 확인 가능

### 비교 항목 매핑

| 사람 평가 항목 | S5 평가 항목 |
|--------------|------------|
| `image_blocking_error_post` | `card_image_validation.blocking_error` |
| `image_anatomical_accuracy_post` | `card_image_validation.anatomical_accuracy` |
| `image_quality_post` | `card_image_validation.image_quality` |
| `image_text_consistency_post` | `card_image_validation.text_image_consistency` |

### 분석 방법
- CSV Export 후 Python으로 비교 분석
- 일치율, 차이 분포, S5 정확도 계산
- S5와 사람 평가 간 상관관계 분석

---

## 참고 문서

- **컬럼 설명 가이드**: `AppSheet_Column_Descriptions.md`
  - Section 3.2: 이미지 평가 항목 (간결 버전)
  - Section 4.6-4.8: 이미지 평가 항목 상세 안내문
- **S5 프롬프트**: `3_Code/prompt/S5_USER_CARD_IMAGE__S5R2__v3.md`
- **S5 검증 코드**: `3_Code/src/05_s5_validator.py`

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-01-01


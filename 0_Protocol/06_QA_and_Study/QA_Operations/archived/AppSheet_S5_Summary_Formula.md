# AppSheet S5 Summary Formula (개선 버전)

**목적:** S5 평가 결과를 각 항목별로 한 줄씩 읽기 쉽게 표시

---

## 개선된 Formula (Issues 정보 포함)

```
IF(
  ISBLANK([card_uid].[S5_one]),
  "",
  CONCATENATE(
    "Blocking Error: ", IF(ISBLANK([card_uid].[S5_one].[s5_blocking_error]), "N/A", IF([card_uid].[S5_one].[s5_blocking_error] = 1, "Yes", "No")), CHAR(10),
    "Technical Accuracy: ", IF(ISBLANK([card_uid].[S5_one].[s5_technical_accuracy]), "N/A", [card_uid].[S5_one].[s5_technical_accuracy]), CHAR(10),
    "Educational Quality: ", IF(ISBLANK([card_uid].[S5_one].[s5_educational_quality]), "N/A", [card_uid].[S5_one].[s5_educational_quality]), CHAR(10),
    "Image Blocking Error: ", IF(ISBLANK([card_uid].[S5_one].[s5_card_image_blocking_error]), "N/A", IF([card_uid].[S5_one].[s5_card_image_blocking_error] = 1, "Yes", "No")), CHAR(10),
    "Image Anatomical Accuracy: ", IF(ISBLANK([card_uid].[S5_one].[s5_card_image_anatomical_accuracy]), "N/A", [card_uid].[S5_one].[s5_card_image_anatomical_accuracy]), CHAR(10),
    "Image Prompt Compliance: ", IF(ISBLANK([card_uid].[S5_one].[s5_card_image_prompt_compliance]), "N/A", [card_uid].[S5_one].[s5_card_image_prompt_compliance]), CHAR(10),
    "Image Text Consistency: ", IF(ISBLANK([card_uid].[S5_one].[s5_card_image_text_image_consistency]), "N/A", [card_uid].[S5_one].[s5_card_image_text_image_consistency]), CHAR(10),
    "Image Quality: ", IF(ISBLANK([card_uid].[S5_one].[s5_card_image_quality]), "N/A", [card_uid].[S5_one].[s5_card_image_quality]), CHAR(10),
    "Image Safety Flag: ", IF(ISBLANK([card_uid].[S5_one].[s5_card_image_safety_flag]), "N/A", IF([card_uid].[S5_one].[s5_card_image_safety_flag] = 1, "Yes", "No")), CHAR(10),
    IF(ISNOTBLANK([card_uid].[S5_one].[s5_description]), CONCATENATE("Issues: ", [card_uid].[S5_one].[s5_description], CHAR(10)), ""),
    IF(ISNOTBLANK([card_uid].[S5_one].[s5_evidence_ref]), CONCATENATE("Evidence Ref: ", [card_uid].[S5_one].[s5_evidence_ref]), "")
  )
)
```

**참고:** `s5_description`과 `s5_evidence_ref`는 `export_appsheet_tables.py`에서 `s5_issues_json`을 파싱하여 자동으로 생성됩니다.

---

## 출력 예시

```
Blocking Error: No
Technical Accuracy: 1.0
Educational Quality: 4
Image Blocking Error: No
Image Anatomical Accuracy: 1.0
Image Prompt Compliance: 1.0
Image Text Consistency: 1.0
Image Quality: 4
Image Safety Flag: No
Issues: Judge returned blocking_error=true but technical_accuracy!=0.0; forcing technical_accuracy=0.0 due to clinical blocking signal.
Evidence Ref: source_123, source_456
```

**참고:** Issues와 Evidence Ref는 `s5_issues_json`에 데이터가 있을 때만 표시됩니다.

---

## Formula 설명

### 1. 기본 구조

```
IF(
  ISBLANK([card_uid].[S5_one]),
  "",
  CONCATENATE(...)
)
```

- S5 데이터가 없으면 빈 문자열 반환
- S5 데이터가 있으면 각 항목을 한 줄씩 표시

### 2. 각 항목 포맷

**Boolean 필드 (Yes/No):**
```
"Blocking Error: ", IF(ISBLANK([card_uid].[S5_one].[s5_blocking_error]), "N/A", IF([card_uid].[S5_one].[s5_blocking_error] = 1, "Yes", "No")), CHAR(10)
```

- 값이 없으면 "N/A"
- 값이 1이면 "Yes"
- 값이 0이면 "No"
- `CHAR(10)`으로 줄바꿈

**Numeric 필드 (점수):**
```
"Technical Accuracy: ", IF(ISBLANK([card_uid].[S5_one].[s5_technical_accuracy]), "N/A", [card_uid].[S5_one].[s5_technical_accuracy]), CHAR(10)
```

- 값이 없으면 "N/A"
- 값이 있으면 그대로 표시
- `CHAR(10)`으로 줄바꿈

### 3. 포함된 필드

**카드 레벨 평가:**
1. `s5_blocking_error` → "Blocking Error"
2. `s5_technical_accuracy` → "Technical Accuracy"
3. `s5_educational_quality` → "Educational Quality"

**이미지 관련 평가:**
4. `s5_card_image_blocking_error` → "Image Blocking Error"
5. `s5_card_image_anatomical_accuracy` → "Image Anatomical Accuracy"
6. `s5_card_image_prompt_compliance` → "Image Prompt Compliance"
7. `s5_card_image_text_image_consistency` → "Image Text Consistency"
8. `s5_card_image_quality` → "Image Quality"
9. `s5_card_image_safety_flag` → "Image Safety Flag"

---

## AppSheet 설정 단계

### Step 1: Virtual Column 생성 또는 수정

1. `Data` → `Tables` → `Ratings` 클릭
2. S5 summary를 표시할 Virtual Column 찾기 (예: `s5_summary` 또는 `view_s5_summary`)
3. 컬럼 클릭 (또는 `+ Add column`으로 새로 생성)
4. `Type`: `Virtual` 선택
5. `Virtual column expression`에 위의 formula 입력
6. `Save` 클릭

### Step 2: Detail View에 추가

1. `UX` → `Views` → `Ratings_Detail` 클릭
2. S5 summary Virtual Column 추가
3. `Show_If`: `NOT(ISBLANK([card_uid].[S5_one]))` (S5 데이터가 있을 때만 표시)
4. `Save` 클릭

---

## 주의사항

### 1. Boolean 값 처리

**AppSheet에서 Boolean은:**
- `1` = TRUE (Yes)
- `0` = FALSE (No)
- `NULL` = 빈 값 (N/A)

**따라서:**
```
IF([field] = 1, "Yes", "No")
```
로 처리합니다.

### 2. 줄바꿈 문자

**AppSheet에서 줄바꿈:**
- `CHAR(10)` 사용 (줄바꿈 문자)
- 또는 `"\n"` 사용 (일부 경우)

**확인 방법:**
- Detail View에서 텍스트가 여러 줄로 표시되는지 확인
- 안 되면 `CHAR(10)` 대신 다른 방법 시도

### 3. 빈 값 처리

**모든 필드에 대해:**
- `ISBLANK()` 체크로 빈 값 처리
- 빈 값이면 "N/A" 표시
- 값이 있으면 그대로 표시

---

## 대안: 더 간단한 버전 (값만 표시)

값만 간단히 표시하고 싶다면:

```
IF(
  ISBLANK([card_uid].[S5_one]),
  "",
  CONCATENATE(
    "Blocking Error: ", IF([card_uid].[S5_one].[s5_blocking_error] = 1, "Yes", "No"), CHAR(10),
    "Technical Accuracy: ", [card_uid].[S5_one].[s5_technical_accuracy], CHAR(10),
    "Educational Quality: ", [card_uid].[S5_one].[s5_educational_quality], CHAR(10),
    "Image Blocking Error: ", IF([card_uid].[S5_one].[s5_card_image_blocking_error] = 1, "Yes", "No"), CHAR(10),
    "Image Anatomical Accuracy: ", [card_uid].[S5_one].[s5_card_image_anatomical_accuracy], CHAR(10),
    "Image Prompt Compliance: ", [card_uid].[S5_one].[s5_card_image_prompt_compliance], CHAR(10),
    "Image Text Consistency: ", [card_uid].[S5_one].[s5_card_image_text_image_consistency], CHAR(10),
    "Image Quality: ", [card_uid].[S5_one].[s5_card_image_quality], CHAR(10),
    "Image Safety Flag: ", IF([card_uid].[S5_one].[s5_card_image_safety_flag] = 1, "Yes", "No")
  )
)
```

**주의:** 이 버전은 빈 값 체크를 하지 않으므로, 값이 없으면 빈 문자열이 표시될 수 있습니다.

---

## 참고 문서

- **S5 테이블 구조**: `export_appsheet_tables.py`
- **S5 필드 정의**: `S5_USER_CARD_IMAGE__S5R2__v3.md`
- **QA 메트릭 정의**: `QA_Metric_Definitions.md`

---

**문서 버전:** 1.0  
**최종 업데이트:** 2025-01-01


# AppSheet `changed_fields` Virtual Column Formula

**작성일:** 2025-01-01  
**목적:** Pre와 Post 평가 간에 변경된 필드 목록을 자동으로 계산하는 Virtual Column 설정

---

## Virtual Column Formula

### Formula

```
  IF(
    [post_is_complete],
    TRIM(
      CONCATENATE(
        IF([blocking_error_pre] <> [blocking_error_post], "blocking_error, ", ""),
        IF([technical_accuracy_pre] <> [technical_accuracy_post], "technical_accuracy, ", ""),
        IF([educational_quality_pre] <> [educational_quality_post], "educational_quality, ", ""),
        IF([evidence_comment_pre] <> [evidence_comment_post], "evidence_comment, ", ""),
        IF([image_blocking_error_pre] <> [image_blocking_error_post], "image_blocking_error, ", ""),
        IF([image_anatomical_accuracy_pre] <> [image_anatomical_accuracy_post], "image_anatomical_accuracy, ", ""),
        IF([image_quality_pre] <> [image_quality_post], "image_quality, ", ""),
        IF([image_text_consistency_pre] <> [image_text_consistency_post], "image_text_consistency", "")
      )
    ),
    ""
  )
```

---

## Formula 설명

### 1. `post_is_complete` 가드

```
IF([post_is_complete], ...)
```

**목적:** Post 평가가 완결된 뒤에만 변경 판단을 수행합니다.

**이유:**
- Post 필드가 비어있는 상태에서 비교하면 "BLANK ≠ 값"으로 인해 변경으로 오판될 수 있습니다
- `post_is_complete`가 TRUE일 때만 Post 필드가 모두 채워진 상태이므로 안전하게 비교할 수 있습니다

### 2. 각 필드 변경 체크

```
IF([blocking_error_pre] <> [blocking_error_post], "blocking_error, ", "")
```

**동작:**
- Pre와 Post 값이 다르면 → 필드 이름 + ", " 추가
- Pre와 Post 값이 같으면 → 빈 문자열("") 추가

### 3. CONCATENATE로 조합

```
CONCATENATE(
  IF(...),  // blocking_error 체크
  IF(...),  // technical_accuracy 체크
  IF(...),  // educational_quality 체크
  IF(...)   // evidence_comment 체크
)
```

**결과 예시:**
- 변경 없음: `""`
- blocking_error만 변경: `"blocking_error, "`
- blocking_error와 technical_accuracy 변경: `"blocking_error, technical_accuracy, "`

### 4. TRIM으로 정리

```
TRIM(CONCATENATE(...))
```

**목적:** 마지막 콤마와 공백을 제거합니다.

**결과 예시:**
- `"blocking_error, "` → `"blocking_error"`
- `"blocking_error, technical_accuracy, "` → `"blocking_error, technical_accuracy"`

---

## AppSheet 설정 단계

### Step 1: Virtual Column 생성

1. `Data` → `Tables` → `Ratings` 클릭
2. `+ Add column` 클릭
3. 컬럼명: `changed_fields`
4. `Type`: `Virtual` 선택
5. `Virtual column expression`에 위의 formula 입력
6. `Editable`: 체크 해제 (읽기 전용)
7. `Save` 클릭

### Step 2: Display Name 설정 (선택사항)

1. `changed_fields` 컬럼 클릭
2. `Display name`: `변경된 필드 목록` 또는 `Changed Fields`
3. `Save` 클릭

---

## 결과 예시

### 시나리오 1: 변경 없음
- Pre: `blocking_error_pre = FALSE`, `technical_accuracy_pre = 1`
- Post: `blocking_error_post = FALSE`, `technical_accuracy_post = 1`
- **결과:** `""` (빈 문자열)

### 시나리오 2: blocking_error만 변경
- Pre: `blocking_error_pre = FALSE`
- Post: `blocking_error_post = TRUE`
- **결과:** `"blocking_error"`

### 시나리오 3: 여러 필드 변경
- Pre: `blocking_error_pre = FALSE`, `technical_accuracy_pre = 1`, `educational_quality_pre = 4`, `image_quality_pre = 4`
- Post: `blocking_error_post = TRUE`, `technical_accuracy_post = 0.5`, `educational_quality_post = 3`, `image_quality_post = 3`
- **결과:** `"blocking_error, technical_accuracy, educational_quality, image_quality"`

### 시나리오 4: 모든 필드 변경
- Pre: 모든 필드 값
- Post: 모든 필드 값이 다름
- **결과:** `"blocking_error, technical_accuracy, educational_quality, evidence_comment, image_blocking_error, image_anatomical_accuracy, image_quality, image_text_consistency"`

---

## 주의사항

### 1. `post_is_complete` 가드 필수

**문제:** `post_is_complete` 가드 없이 비교하면 Post 필드가 비어있을 때 변경으로 오판될 수 있습니다.

**해결:** 항상 `IF([post_is_complete], ...)`로 감싸서 Post가 완결된 뒤에만 비교합니다.

### 2. Yes/No 필드 비교

**AppSheet에서 Yes/No 필드 비교:**
- `[blocking_error_pre] <> [blocking_error_post]` 사용
- `ISBLANK()` 대신 직접 비교 사용

### 3. Enum 필드 비교

**AppSheet에서 Enum 필드 비교:**
- `[technical_accuracy_pre] <> [technical_accuracy_post]` 사용
- 문자열로 저장될 수 있으므로 직접 비교 사용

### 4. Text 필드 비교

**AppSheet에서 Text 필드 비교:**
- `[evidence_comment_pre] <> [evidence_comment_post]` 사용
- 빈 문자열("")과 NULL 모두 체크됨

---

## 테스트 방법

### 테스트 1: 변경 없음
1. Pre 평가 입력
2. Post 평가에서 Pre와 동일한 값 입력
3. `changed_fields` 확인 → 빈 문자열("") 확인

### 테스트 2: 하나의 필드 변경
1. Pre 평가 입력
2. Post 평가에서 `blocking_error`만 변경
3. `changed_fields` 확인 → "blocking_error" 확인

### 테스트 3: 여러 필드 변경
1. Pre 평가 입력
2. Post 평가에서 여러 필드 변경
3. `changed_fields` 확인 → 콤마로 구분된 필드 목록 확인

### 테스트 4: Post 미완료 상태
1. Pre 평가 입력
2. Post 평가를 일부만 입력 (미완료)
3. `changed_fields` 확인 → 빈 문자열("") 확인 (`post_is_complete = FALSE`)

---

## 참고 문서

- **컬럼 설명**: `AppSheet_Column_Descriptions.md` Section 1.1.3
- **설정 가이드**: `AppSheet_QA_Setup_Guide.md` Section 6.3.4.3
- **프로덕션 강화**: `AppSheet_QA_Production_Hardening.md` Appendix

---

**문서 버전:** 1.0  
**최종 업데이트:** 2025-01-01


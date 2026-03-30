# AppSheet Change Log 필드 설정 가이드

**작성일:** 2025-01-01  
**목적:** `change_reason_code`와 `change_note` 필드의 조건부 입력 설정

---

## 변경 사항 요약

1. ✅ **`s5_revealed_ts` 컬럼 제거** (더 이상 사용하지 않음)
2. ✅ **`change_reason_code`**: 변경이 있을 때만 편집 가능하고 필수
3. ✅ **`change_note`**: `change_reason_code`가 "OTHER"일 때만 입력 가능하고 필수

---

## 1. `change_reason_code` 설정

### 1.1 Editable_If (편집 가능 조건)

**조건:** 변경이 있을 때만 편집 가능

```
[is_changed]
```

**설명:**
- 변경이 있을 때만 (`is_changed = TRUE`) 편집 가능

### 1.2 Required_If (필수 입력 조건)

**조건:** 변경이 있을 때 필수

```
[is_changed]
```

**설명:**
- 변경이 있을 때 반드시 입력해야 함

### 1.3 AppSheet 설정 단계

1. `Data` → `Tables` → `Ratings` → `change_reason_code` 클릭
2. `Editable` → `Editable_If` 선택
3. 위의 `Editable_If` 조건 입력
4. `Required` → `Required_If` 선택
5. 위의 `Required_If` 조건 입력
6. `Save` 클릭

---

## 2. `change_note` 설정

### 2.1 Editable_If (편집 가능 조건)

**조건:** `change_reason_code`가 "OTHER"일 때만 편집 가능

```
AND(
  [is_changed],
  [change_reason_code] = "OTHER"
)
```

**설명:**
- 변경이 있고
- `change_reason_code`가 "OTHER"일 때만 편집 가능

### 2.2 Required_If (필수 입력 조건)

**조건:** `change_reason_code`가 "OTHER"일 때 필수

```
AND(
  [is_changed],
  [change_reason_code] = "OTHER"
)
```

**설명:**
- `change_reason_code`가 "OTHER"일 때 반드시 입력해야 함

### 2.3 AppSheet 설정 단계

1. `Data` → `Tables` → `Ratings` → `change_note` 클릭
2. `Editable` → `Editable_If` 선택
3. 위의 `Editable_If` 조건 입력
4. `Required` → `Required_If` 선택
5. 위의 `Required_If` 조건 입력
6. `Save` 클릭

---

## 3. Detail View에서 Show_If 설정 (⚠️ 중요)

**문제:** Virtual Column(`is_changed`)을 사용하는 경우, 컬럼 레벨의 `Editable_If`만으로는 Detail View에서 컬럼이 숨겨지지 않을 수 있습니다.

**해결:** Detail View에서 각 컬럼의 `Show_If` 조건을 추가로 설정해야 합니다.

### 3.1 Detail View에서 `change_reason_code` Show_If 설정

**AppSheet 메뉴 경로:** `UX` → `Views` → `Ratings_Detail` → `change_reason_code` 컬럼

1. `UX` → `Views` → `Ratings_Detail` 클릭
2. `change_reason_code` 컬럼 찾기 (또는 추가)
3. 컬럼 클릭
4. `Show_If` 필드에 아래 조건 입력:
   ```
   [is_changed]
   ```
   **설명:** 변경이 있을 때만 컬럼이 표시됩니다
5. `Save` 클릭

### 3.2 Detail View에서 `change_note` Show_If 설정

**AppSheet 메뉴 경로:** `UX` → `Views` → `Ratings_Detail` → `change_note` 컬럼

1. `UX` → `Views` → `Ratings_Detail` 클릭
2. `change_note` 컬럼 찾기 (또는 추가)
3. 컬럼 클릭
4. `Show_If` 필드에 아래 조건 입력:
   ```
   AND(
     [is_changed],
     [change_reason_code] = "OTHER"
   )
   ```
   **설명:** 변경이 있고, change_reason_code가 "OTHER"일 때만 컬럼이 표시됩니다
5. `Save` 클릭

### 3.3 Virtual Column 계산 타이밍 문제 해결

**문제:** Virtual Column(`is_changed`)이 실시간으로 업데이트되지 않을 수 있습니다.

**해결 방법:**

1. **Detail View 새로고침:**
   - Detail View를 닫았다가 다시 열기
   - 또는 다른 행으로 이동했다가 다시 돌아오기

2. **Post 필드 수정 후 확인:**
   - Post 필드를 수정하면 `is_changed`가 자동으로 재계산됩니다
   - Post 필드를 한 번 수정하면 Virtual Column이 업데이트됩니다

3. **초기값 문제 확인:**
   - Virtual Column은 기본값이 없습니다
   - Post 필드가 비어있으면 `is_changed`는 FALSE입니다
   - Post 필드를 입력한 후에야 `is_changed`가 계산됩니다

---

## 3. "Submit Post-S5 Rating" 액션 Run_If 업데이트

### 3.1 업데이트된 Run_If 조건

```
AND(
  NOT(ISBLANK([post_started_ts])),
  ISBLANK([post_submitted_ts]),
  [post_is_complete],
  OR(
    NOT([is_changed]),
    AND(
      ISNOTBLANK([change_reason_code]),
      OR(
        [change_reason_code] <> "OTHER",
        ISNOTBLANK([change_note])
      )
    )
  )
)
```

### 3.2 조건 설명

**변경이 없으면:**
- `NOT([is_changed])` = TRUE → 제출 가능

**변경이 있으면:**
- `change_reason_code` 필수 (`ISNOTBLANK([change_reason_code])`)
- `change_reason_code`가 "OTHER"가 아니면 → 제출 가능
- `change_reason_code`가 "OTHER"이면 → `change_note`도 필수 (`ISNOTBLANK([change_note])`)

### 3.3 AppSheet 설정 단계

1. `UX` → `Actions` → `Submit Post-S5 Rating` 클릭
2. `Run_If` 필드에 위의 조건 입력
3. `Save` 클릭

---

## 4. 동작 시나리오

### 시나리오 1: 변경 없음
- `is_changed = FALSE`
- `change_reason_code`: 편집 불가 (Editable_If = FALSE)
- `change_note`: 편집 불가 (Editable_If = FALSE)
- **결과:** 제출 가능

### 시나리오 2: 변경 있음, change_reason_code = "S5_BLOCKING_FLAG"
- `is_changed = TRUE`
- `change_reason_code`: 편집 가능, 필수 → "S5_BLOCKING_FLAG" 선택
- `change_note`: 편집 불가 (Editable_If = FALSE, "OTHER"가 아니므로)
- **결과:** `change_reason_code`만 입력하면 제출 가능

### 시나리오 3: 변경 있음, change_reason_code = "OTHER"
- `is_changed = TRUE`
- `change_reason_code`: 편집 가능, 필수 → "OTHER" 선택
- `change_note`: 편집 가능, 필수 → 상세 설명 입력
- **결과:** `change_reason_code`와 `change_note` 모두 입력해야 제출 가능

---

## 5. 체크리스트

### 컬럼 설정
- [ ] `change_reason_code`의 `Editable_If` 설정 완료
- [ ] `change_reason_code`의 `Required_If` 설정 완료
- [ ] `change_note`의 `Editable_If` 설정 완료
- [ ] `change_note`의 `Required_If` 설정 완료

### Detail View 설정 (⚠️ 중요)
- [ ] Detail View에서 `change_reason_code` 컬럼의 `Show_If` 설정 완료
- [ ] Detail View에서 `change_note` 컬럼의 `Show_If` 설정 완료

### 액션 설정
- [ ] "Submit Post-S5 Rating" 액션의 `Run_If` 업데이트 완료

### 테스트
- [ ] 변경 없을 때: `change_reason_code` 편집 불가 확인
- [ ] 변경 있을 때: `change_reason_code` 편집 가능 확인
- [ ] "OTHER" 선택 시: `change_note` 편집 가능 확인
- [ ] "OTHER" 외 선택 시: `change_note` 편집 불가 확인
- [ ] "OTHER" 선택 후 `change_note` 없이 제출 시도: 제출 불가 확인

---

## 6. 참고 문서

- **컬럼 설명**: `AppSheet_Column_Descriptions.md` Section 1.1
- **설정 가이드**: `AppSheet_QA_Setup_Guide.md` Section 6.4.5
- **프로덕션 강화**: `AppSheet_QA_Production_Hardening.md` Section 5.2.5

---

**문서 버전:** 1.0  
**최종 업데이트:** 2025-01-01


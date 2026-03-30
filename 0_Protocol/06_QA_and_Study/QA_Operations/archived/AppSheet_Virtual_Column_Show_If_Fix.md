# AppSheet Virtual Column Show_If 문제 해결 가이드

**문제:** `is_changed` Virtual Column을 사용하여 `change_reason_code`와 `change_note`를 조건부로 표시했는데, Detail View에서 잘 적용되지 않습니다.

---

## 문제 원인

### 1. Detail View에서 Show_If 설정 누락

**문제:** 컬럼 레벨의 `Editable_If`와 `Required_If`만 설정하고, **Detail View에서 컬럼의 `Show_If` 조건을 설정하지 않았을 수 있습니다.**

**해결:** Detail View에서 각 컬럼의 `Show_If` 조건을 추가로 설정해야 합니다.

### 2. Virtual Column 계산 타이밍

**문제:** Virtual Column(`is_changed`)이 실시간으로 업데이트되지 않을 수 있습니다.

**해결:** Post 필드를 수정하면 Virtual Column이 자동으로 재계산됩니다.

---

## 해결 방법

### 방법 1: Detail View에서 Show_If 설정 (필수)

**AppSheet 메뉴 경로:** `UX` → `Views` → `Ratings_Detail` → 각 컬럼

#### Step 1: `change_reason_code` Show_If 설정

1. `UX` → `Views` → `Ratings_Detail` 클릭
2. `change_reason_code` 컬럼 찾기 (또는 추가)
3. 컬럼 클릭
4. **`Show_If`** 필드에 아래 조건 입력:
   ```
   [is_changed]
   ```
5. `Save` 클릭

**결과:** 변경이 있을 때만 `change_reason_code` 컬럼이 Detail View에 표시됩니다.

#### Step 2: `change_note` Show_If 설정

1. `UX` → `Views` → `Ratings_Detail` 클릭
2. `change_note` 컬럼 찾기 (또는 추가)
3. 컬럼 클릭
4. **`Show_If`** 필드에 아래 조건 입력:
   ```
   AND(
     [is_changed],
     [change_reason_code] = "OTHER"
   )
   ```
5. `Save` 클릭

**결과:** 변경이 있고, `change_reason_code`가 "OTHER"일 때만 `change_note` 컬럼이 Detail View에 표시됩니다.

---

### 방법 2: Virtual Column 계산 강제 (필요시)

**문제:** Virtual Column이 실시간으로 업데이트되지 않는 경우

**해결 방법:**

1. **Post 필드 수정 후 확인:**
   - Post 필드(`blocking_error_post`, `technical_accuracy_post` 등)를 한 번 수정
   - Virtual Column이 자동으로 재계산됩니다
   - Detail View를 새로고침하면 `is_changed` 값이 업데이트됩니다

2. **Detail View 새로고침:**
   - Detail View를 닫았다가 다시 열기
   - 또는 다른 행으로 이동했다가 다시 돌아오기

3. **초기 상태 확인:**
   - Post 필드가 비어있으면 `is_changed`는 FALSE입니다
   - Post 필드를 입력한 후에야 `is_changed`가 계산됩니다

---

## 설정 체크리스트

### 컬럼 레벨 설정 (Data → Tables → Ratings)
- [ ] `change_reason_code`의 `Editable_If` = `[is_changed]`
- [ ] `change_reason_code`의 `Required_If` = `[is_changed]`
- [ ] `change_note`의 `Editable_If` = `AND([is_changed], [change_reason_code] = "OTHER")`
- [ ] `change_note`의 `Required_If` = `AND([is_changed], [change_reason_code] = "OTHER")`

### Detail View 설정 (UX → Views → Ratings_Detail) ⚠️ **중요**
- [ ] `change_reason_code` 컬럼의 `Show_If` = `[is_changed]`
- [ ] `change_note` 컬럼의 `Show_If` = `AND([is_changed], [change_reason_code] = "OTHER")`

### Virtual Column 확인
- [ ] `is_changed` Virtual Column이 제대로 계산되는지 확인
- [ ] Post 필드를 수정한 후 `is_changed` 값이 업데이트되는지 확인

---

## 테스트 방법

### 테스트 1: 변경 없을 때
1. Pre 평가 입력
2. Post 평가에서 Pre와 동일한 값 입력
3. Detail View 확인:
   - `change_reason_code` 컬럼이 **보이지 않아야** 함 (`Show_If = [is_changed] = FALSE`)
   - `change_note` 컬럼이 **보이지 않아야** 함

### 테스트 2: 변경 있을 때
1. Pre 평가 입력
2. Post 평가에서 하나 이상의 필드 변경
3. Detail View 확인:
   - `change_reason_code` 컬럼이 **보여야** 함 (`Show_If = [is_changed] = TRUE`)
   - `change_reason_code`가 편집 가능해야 함
4. `change_reason_code` 선택 (예: "S5_BLOCKING_FLAG")
5. Detail View 확인:
   - `change_note` 컬럼이 **보이지 않아야** 함 ("OTHER"가 아니므로)

### 테스트 3: OTHER 선택 시
1. Pre 평가 입력
2. Post 평가에서 하나 이상의 필드 변경
3. `change_reason_code` = "OTHER" 선택
4. Detail View 확인:
   - `change_note` 컬럼이 **보여야** 함
   - `change_note`가 편집 가능해야 함

---

## 문제 해결 단계

### Step 1: Detail View Show_If 확인
1. `UX` → `Views` → `Ratings_Detail` 클릭
2. `change_reason_code` 컬럼 클릭
3. `Show_If` 필드 확인:
   - 비어있으면 → `[is_changed]` 입력
   - 다른 조건이면 → `[is_changed]`로 변경
4. `change_note` 컬럼도 동일하게 확인

### Step 2: Virtual Column 확인
1. `Data` → `Tables` → `Ratings` → `is_changed` 클릭
2. Virtual column expression 확인:
   ```
   AND(
     [post_is_complete],
     OR(
       [blocking_error_post] <> [blocking_error_pre],
       [technical_accuracy_post] <> [technical_accuracy_pre],
       [educational_quality_post] <> [educational_quality_pre],
       [evidence_comment_post] <> [evidence_comment_pre]
     )
   )
   ```

### Step 3: 테스트
1. 앱 미리보기에서 Detail View 열기
2. Post 필드를 수정하여 변경 발생시키기
3. `change_reason_code` 컬럼이 나타나는지 확인

---

## 주의사항

### 1. Show_If vs Editable_If

**차이점:**
- **`Show_If`**: Detail View에서 컬럼이 **보이는지 여부**를 제어
- **`Editable_If`**: 컬럼이 **편집 가능한지 여부**를 제어

**둘 다 설정해야 함:**
- `Show_If` = `[is_changed]` → 변경이 있을 때만 보임
- `Editable_If` = `[is_changed]` → 변경이 있을 때만 편집 가능

### 2. Virtual Column 계산 타이밍

**Virtual Column은:**
- 다른 필드가 변경될 때 자동으로 재계산됩니다
- 하지만 즉시 반영되지 않을 수 있습니다
- Detail View를 새로고침하면 업데이트됩니다

### 3. 초기 상태

**Post 필드가 비어있을 때:**
- `post_is_complete` = FALSE
- `is_changed` = FALSE (가드 때문에)
- `change_reason_code`와 `change_note` 모두 숨김

**Post 필드를 입력한 후:**
- `post_is_complete` = TRUE (조건 만족 시)
- `is_changed` = TRUE/FALSE (실제 변경 여부에 따라)
- `change_reason_code`와 `change_note`가 조건에 따라 표시됨

---

## 참고 문서

- **Change Log 설정**: `AppSheet_Change_Log_Field_Configuration.md`
- **설정 가이드**: `AppSheet_QA_Setup_Guide.md` Section 6.4.5
- **Detail View 설정**: `AppSheet_QA_Setup_Guide.md` Section 6.1.8

---

**문서 버전:** 1.0  
**최종 업데이트:** 2025-01-01


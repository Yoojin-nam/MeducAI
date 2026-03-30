# AppSheet Ratings 테이블 스키마 (업데이트됨)

**작성일:** 2025-01-01  
**업데이트:** 이미지 평가 항목 추가 완료

---

## Ratings 테이블 전체 컬럼 구조

### 기본 정보 (7개)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `rating_id` | Text (Key) | 고유 식별자: `{card_uid}::{rater_email}` |
| `card_uid` | Text (Ref → Cards) | 카드 고유 ID |
| `card_id` | Text | 카드 ID |
| `rater_email` | Email | 평가자 이메일 (자동: `USEREMAIL()`) |
| `assignment_id` | Text (Ref → Assignments) | 배정 ID |
| `assignment_order` | Number | 평가 순서 (1부터 시작) |
| `batch_id` | Text | 배치 ID |

---

### Pre 평가 항목 (7개)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `blocking_error_pre` | Yes/No | 차단 오류 여부 |
| `technical_accuracy_pre` | Enum (0, 0.5, 1) | 기술적 정확도 |
| `educational_quality_pre` | Enum (1-5) | 교육적 품질 |
| `evidence_comment_pre` | LongText | 증거 코멘트 |
| `pre_started_ts` | Date/Time | Pre 평가 시작 시각 |
| `pre_submitted_ts` | Date/Time | Pre 평가 제출 시각 |
| `pre_duration_sec` | Number | Pre 평가 소요 시간 (초) |

---

### 이미지 평가 - Pre (4개) ⭐ **새로 추가**

**참고:** Pre 단계에서는 이미지를 보지 않으므로 빈 값으로 시작합니다. Post 단계에서 평가합니다.

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `image_blocking_error_pre` | Yes/No | 이미지 차단 오류 (Pre) |
| `image_anatomical_accuracy_pre` | Enum (0, 0.5, 1) | 이미지 해부학적 정확도 (Pre) |
| `image_quality_pre` | Enum (1-5) | 이미지 품질 (Pre) |
| `image_text_consistency_pre` | Enum (0, 0.5, 1) | 이미지-텍스트 일관성 (Pre) |

---

---

### Post 평가 항목 (7개)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `blocking_error_post` | Yes/No | 차단 오류 여부 |
| `technical_accuracy_post` | Enum (0, 0.5, 1) | 기술적 정확도 |
| `educational_quality_post` | Enum (1-5) | 교육적 품질 |
| `evidence_comment_post` | LongText | 증거 코멘트 |
| `post_started_ts` | Date/Time | Post 평가 시작 시각 (S5 공개 시점) |
| `post_submitted_ts` | Date/Time | Post 평가 제출 시각 |
| `post_duration_sec` | Number | Post 평가 소요 시간 (초) |

---

### 이미지 평가 - Post (4개) ⭐ **새로 추가**

**평가 시점:** Post 평가 단계에서 S5 결과를 확인한 후, 이미지를 직접 보고 평가합니다.

| 컬럼명 | 타입 | 설명 | S5 대응 |
|--------|------|------|---------|
| `image_blocking_error_post` | Yes/No | 이미지 차단 오류 | `card_image_validation.blocking_error` |
| `image_anatomical_accuracy_post` | Enum (0, 0.5, 1) | 이미지 해부학적 정확도 | `card_image_validation.anatomical_accuracy` |
| `image_quality_post` | Enum (1-5) | 이미지 품질 | `card_image_validation.image_quality` |
| `image_text_consistency_post` | Enum (0, 0.5, 1) | 이미지-텍스트 일관성 | `card_image_validation.text_image_consistency` |

---

### 변경 로그 (3개)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `change_reason_code` | Enum | 변경 이유 코드 (변경 시 필수) |
| `change_note` | LongText | 변경 사유 상세 (변경 시 필수) |
| `changed_fields` | Text | 변경된 필드 목록 (자동 생성) |

---

### 플래그 (2개)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `flag_followup` | Yes/No | 후속 조치 필요 플래그 |
| `flag_note` | LongText | 플래그 메모 |

---

### 관리자 Undo (3개)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `admin_undo_pre_submitted_ts` | Date/Time | Pre 제출 취소 시각 (관리자 전용) |
| `admin_undo_post_submitted_ts` | Date/Time | Post 제출 취소 시각 (관리자 전용) |
| `undo_reason` | LongText | 제출 취소 사유 (관리자 전용) |

---

## 전체 컬럼 개수

- **총 37개 컬럼** (s5_revealed_ts 제거)
- **기본 정보:** 7개
- **Pre 평가:** 7개
- **이미지 평가 - Pre:** 4개 (새로 추가)
- **Post 평가:** 7개
- **이미지 평가 - Post:** 4개 (새로 추가)
- **변경 로그:** 3개
- **플래그:** 2개
- **관리자 Undo:** 3개

---

## CSV Export 순서

`export_appsheet_tables.py`에서 생성되는 `Ratings.csv`의 컬럼 순서:

1. `rating_id`
2. `card_uid`
3. `card_id`
4. `rater_email`
5. `assignment_id`
6. `assignment_order`
7. `batch_id`
8. `blocking_error_pre`
9. `technical_accuracy_pre`
10. `educational_quality_pre`
11. `evidence_comment_pre`
12. `pre_started_ts`
13. `pre_submitted_ts`
14. `pre_duration_sec`
15. **`image_blocking_error_pre`** ⭐
16. **`image_anatomical_accuracy_pre`** ⭐
17. **`image_quality_pre`** ⭐
18. **`image_text_consistency_pre`** ⭐
19. `blocking_error_post`
21. `technical_accuracy_post`
22. `educational_quality_post`
23. `evidence_comment_post`
24. `post_started_ts`
25. `post_submitted_ts`
26. `post_duration_sec`
27. **`image_blocking_error_post`** ⭐
28. **`image_anatomical_accuracy_post`** ⭐
29. **`image_quality_post`** ⭐
30. **`image_text_consistency_post`** ⭐
31. `change_reason_code`
32. `change_note`
33. `changed_fields`
34. `flag_followup`
35. `flag_note`
36. `admin_undo_pre_submitted_ts`
37. `admin_undo_post_submitted_ts`
38. `undo_reason`

**참고:** `s5_revealed_ts` 컬럼은 제거되었습니다. `post_started_ts`가 S5 공개 시점을 나타냅니다.

---

## 업데이트 내용

### 변경 사항
- ✅ `_generate_ratings_from_assignments()` 함수에 이미지 평가 항목 8개 추가
- ✅ `ratings_fieldnames` 리스트에 이미지 평가 항목 8개 추가
- ✅ CSV 생성 시 모든 이미지 평가 항목이 빈 값("")으로 초기화됨
- ✅ `s5_revealed_ts` 컬럼 제거 (더 이상 사용하지 않음, `post_started_ts`로 통합)

### Change Log 필드 설정
- ✅ `change_reason_code`: 변경이 있을 때만 편집 가능하고 필수
- ✅ `change_note`: `change_reason_code`가 "OTHER"일 때만 입력 가능하고 필수

### 참고 사항
- 이미지 평가 항목은 **Post 평가 단계**에서만 평가합니다
- Pre 단계에서는 이미지를 보지 않으므로 Pre 항목은 빈 값으로 유지됩니다
- S5 결과와 비교 분석을 위해 Post 항목을 평가합니다
- `s5_revealed_ts`는 제거되었으며, `post_started_ts`가 S5 공개 시점을 나타냅니다

---

**문서 버전:** 1.1  
**최종 업데이트:** 2025-01-01


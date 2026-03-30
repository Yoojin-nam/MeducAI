# AppSheet S5 재생성 컬럼 통합 가이드

**작성일:** 2025-01-01  
**목적:** 기존 S5 수정본 컬럼과 새로 추가된 재생성 컬럼 통합

---

## 컬럼 중복 분석

### 기존 컬럼 (Legacy)
- `s5_front_modified` (LongText)
- `s5_back_modified` (LongText)
- `s5_modified_timestamp` (Date/Time)

### 새로 추가된 컬럼 (S5 Final Assessment)
- `regenerated_front` (LongText)
- `regenerated_back` (LongText)
- `regenerated_image_filename` (Image)
- `regeneration_timestamp` (Date/Time)
- `regeneration_trigger_score` (Number)

### 중복 확인
**결론:** 명확히 중복됩니다. 같은 개념을 다른 이름으로 표현하고 있습니다.

---

## 통합 방안

### 최종 컬럼 구조 (통합 후)

| 컬럼명 | 타입 | 설명 | 기존 컬럼과의 관계 |
|--------|------|------|-------------------|
| `s5_regenerated_front` | LongText | 재생성된 문제 텍스트 | `s5_front_modified` 통합 |
| `s5_regenerated_back` | LongText | 재생성된 정답 텍스트 | `s5_back_modified` 통합 |
| `s5_regenerated_image_filename` | Image | 재생성된 이미지 파일명 | 새로 추가 |
| `s5_regeneration_timestamp` | Date/Time | 재생성 시점 | `s5_modified_timestamp` 통합 |
| `s5_regeneration_trigger_score` | Number | 재생성을 트리거한 평가 점수 | 새로 추가 |

### 통합 규칙

**`export_appsheet_tables.py`에서 자동 병합:**
```python
"s5_regenerated_front": s5.get("s5_regenerated_front") or s5.get("s5_front_modified", ""),
"s5_regenerated_back": s5.get("s5_regenerated_back") or s5.get("s5_back_modified", ""),
"s5_regeneration_timestamp": s5.get("s5_regeneration_timestamp") or s5.get("s5_modified_timestamp", ""),
```

**우선순위:**
1. 새 컬럼(`s5_regenerated_*`)이 있으면 우선 사용
2. 새 컬럼이 없으면 기존 컬럼(`s5_*_modified`) 사용
3. 둘 다 없으면 빈 문자열("")

---

## 마이그레이션 가이드

### 1. 기존 데이터 호환성

**기존 데이터가 있는 경우:**
- `s5_front_modified` → `s5_regenerated_front`로 자동 매핑
- `s5_back_modified` → `s5_regenerated_back`로 자동 매핑
- `s5_modified_timestamp` → `s5_regeneration_timestamp`로 자동 매핑

**새 데이터 생성 시:**
- `s5_regenerated_*` 컬럼 사용 (권장)
- 기존 컬럼은 하위 호환성을 위해 유지하되, 새 컬럼 우선 사용

### 2. AppSheet 설정

#### Step 1: 기존 컬럼 이름 변경 (선택사항)

기존 컬럼을 그대로 사용하거나, 새 이름으로 변경:

1. `Data` → `Tables` → `S5` 클릭
2. `s5_front_modified` 컬럼 클릭
3. 컬럼명을 `s5_regenerated_front`로 변경 (또는 그대로 유지)
4. `Save` 클릭

**또는 새 컬럼 추가:**
- 기존 컬럼은 그대로 두고 새 컬럼 추가
- `export_appsheet_tables.py`가 자동으로 병합 처리

#### Step 2: 새 컬럼 추가

1. `Data` → `Tables` → `S5` → `+ Add column`
2. 컬럼명: `s5_regenerated_image_filename`
3. `Type`: `Image` 선택
4. `Save` 클릭

3. 컬럼명: `s5_regeneration_trigger_score`
4. `Type`: `Number` 선택
5. `Save` 클릭

---

## 코드 변경사항

### `export_appsheet_tables.py`

#### 변경 전:
```python
"s5_front_modified": s5.get("s5_front_modified", ""),
"s5_back_modified": s5.get("s5_back_modified", ""),
"s5_modified_timestamp": s5.get("s5_modified_timestamp", ""),
```

#### 변경 후:
```python
# S5 재생성 콘텐츠 (멀티에이전트 시스템의 Self-Improvement 결과)
# 기존 s5_front_modified, s5_back_modified, s5_modified_timestamp와 통합
"s5_regenerated_front": s5.get("s5_regenerated_front") or s5.get("s5_front_modified", ""),
"s5_regenerated_back": s5.get("s5_regenerated_back") or s5.get("s5_back_modified", ""),
"s5_regenerated_image_filename": s5.get("s5_regenerated_image_filename", ""),
"s5_regeneration_timestamp": s5.get("s5_regeneration_timestamp") or s5.get("s5_modified_timestamp", ""),
"s5_regeneration_trigger_score": s5.get("s5_regeneration_trigger_score"),
```

---

## Virtual Column 업데이트

### Ratings 테이블의 Virtual Columns

#### `s5_regenerated_front`
```
[card_uid].[S5_one].[s5_regenerated_front]
```

#### `s5_regenerated_back`
```
[card_uid].[S5_one].[s5_regenerated_back]
```

#### `s5_regenerated_image`
```
[card_uid].[S5_one].[s5_regenerated_image_filename]
```

---

## 데이터 예시

### 입력 (S5 JSONL):
```json
{
  "card_uid": "G001::DERIVED:123__Q1__0",
  "s5_regenerated_front": "수정된 문제 텍스트",
  "s5_regenerated_back": "수정된 정답 텍스트",
  "s5_regenerated_image_filename": "IMG__regenerated_123.png",
  "s5_regeneration_timestamp": "2025-01-01T12:00:00Z",
  "s5_regeneration_trigger_score": 65.5
}
```

### 출력 (S5.csv):
```csv
card_uid,s5_regenerated_front,s5_regenerated_back,s5_regenerated_image_filename,s5_regeneration_timestamp,s5_regeneration_trigger_score
G001::DERIVED:123__Q1__0,수정된 문제 텍스트,수정된 정답 텍스트,IMG__regenerated_123.png,2025-01-01T12:00:00Z,65.5
```

---

## 하위 호환성

### 기존 데이터 지원

**시나리오 1: 기존 컬럼만 있는 경우**
```json
{
  "s5_front_modified": "기존 수정 텍스트",
  "s5_back_modified": "기존 수정 정답",
  "s5_modified_timestamp": "2025-01-01T10:00:00Z"
}
```
→ 자동으로 `s5_regenerated_*` 컬럼으로 매핑됨

**시나리오 2: 새 컬럼만 있는 경우**
```json
{
  "s5_regenerated_front": "새 수정 텍스트",
  "s5_regenerated_back": "새 수정 정답",
  "s5_regeneration_timestamp": "2025-01-01T12:00:00Z"
}
```
→ 그대로 사용됨

**시나리오 3: 둘 다 있는 경우**
```json
{
  "s5_front_modified": "기존 텍스트",
  "s5_regenerated_front": "새 텍스트"
}
```
→ `s5_regenerated_front` 우선 사용 (새 컬럼 우선)

---

## 체크리스트

### 코드 업데이트
- [x] `export_appsheet_tables.py`에서 컬럼 통합 로직 추가
- [x] CSV fieldnames 업데이트
- [x] 기존 컬럼과 새 컬럼 병합 처리

### 문서 업데이트
- [x] `AppSheet_S5_Final_Assessment_Design.md` 업데이트
- [x] 통합 가이드 문서 생성

### AppSheet 설정 (향후)
- [ ] S5 테이블에 새 컬럼 추가 (`s5_regenerated_image_filename`, `s5_regeneration_trigger_score`)
- [ ] 기존 컬럼 이름 변경 또는 새 컬럼 추가
- [ ] Virtual Columns 업데이트

---

## 참고 문서

- **S5 Final Assessment 설계**: `AppSheet_S5_Final_Assessment_Design.md`
- **Exporter 코드**: `3_Code/src/tools/final_qa/export_appsheet_tables.py`
- **S5 Summary Formula**: `AppSheet_S5_Summary_Formula.md`

---

**문서 버전:** 1.0  
**최종 업데이트:** 2025-01-01


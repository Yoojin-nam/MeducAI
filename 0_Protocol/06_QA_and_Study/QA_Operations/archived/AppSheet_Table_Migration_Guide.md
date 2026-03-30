# AppSheet 테이블 마이그레이션 가이드

**작성일:** 2025-01-01  
**목적:** 기존 export된 테이블과 새로운 코드가 생성하는 테이블 간 차이점 및 마이그레이션 가이드

---

## 차이점 요약

### S5.csv

#### 제거된 컬럼 (3개)
- `s5_front_modified` → `s5_regenerated_front`로 변경
- `s5_back_modified` → `s5_regenerated_back`로 변경
- `s5_modified_timestamp` → `s5_regeneration_timestamp`로 변경

#### 추가된 컬럼 (8개)
- `s5_description`: S5 issues에서 추출한 description 목록
- `s5_evidence_ref`: S5 issues에서 추출한 evidence reference 목록
- `s5_regenerated_front`: 재생성된 카드 문제 텍스트 (기존 `s5_front_modified` 대체)
- `s5_regenerated_back`: 재생성된 카드 정답 텍스트 (기존 `s5_back_modified` 대체)
- `s5_regenerated_image_filename`: 재생성된 이미지 파일명 (새로 추가)
- `s5_regeneration_timestamp`: 재생성 시점 (기존 `s5_modified_timestamp` 대체)
- `s5_regeneration_trigger_score`: 재생성 트리거 점수 (새로 추가)
- `s5_was_regenerated`: 재생성 여부 플래그 (0 또는 1, 새로 추가)

#### 변경 사항
- **기존 컬럼명 변경**: `s5_*_modified` → `s5_regenerated_*`
- **하위 호환성**: 코드에서 기존 컬럼명도 읽어서 새 컬럼명으로 자동 매핑

---

### Cards.csv

#### 변경 사항
- **변경 없음**: Cards 테이블은 원본 카드 내용만 포함하므로 변경 없음

---

### Ratings.csv

#### 제거된 컬럼 (3개)
- `overall_quality_pre` → `educational_quality_pre`로 변경
- `overall_quality_post` → `educational_quality_post`로 변경
- `s5_revealed_ts` → `post_started_ts`로 변경 (S5 reveal 시점은 `post_started_ts`로 표시)

#### 추가된 컬럼 (10개)
- `educational_quality_pre`: 교육적 품질 평가 (Pre, 기존 `overall_quality_pre` 대체)
- `educational_quality_post`: 교육적 품질 평가 (Post, 기존 `overall_quality_post` 대체)
- `s5_started_ts`: S5 Final Assessment 시작 시점
- `s5_submitted_ts`: S5 Final Assessment 제출 시점
- `s5_duration_sec`: S5 Final Assessment 소요 시간 (초)
- `ai_self_reliability`: AI 자가 평가 신뢰도 (1-5)
- `ai_self_reliability_comment`: AI 자가 평가 신뢰도 근거
- `accept_ai_correction`: AI 수정안 수용 여부 (ACCEPT/REJECT)
- `ai_correction_quality`: AI 수정안 품질 평가 (1-5)
- `ai_correction_comment`: AI 수정안 수용/거부 근거

#### 변경 사항
- **컬럼명 변경**: `overall_quality_*` → `educational_quality_*`
- **S5 관련 컬럼 추가**: S5 Final Assessment 및 AI 수정안 수용 결정 관련 컬럼 추가

---

## 마이그레이션 절차

### 1. S5 테이블 마이그레이션

#### 옵션 1: 재생성 (권장)
```bash
python 3_Code/src/tools/final_qa/export_appsheet_tables.py \
  --run_dir "2_Data/metadata/generated/{RUN_TAG}" \
  --out_dir "2_Data/qa_appsheet_export/{RUN_TAG}" \
  --copy_images true
```

**장점:**
- 자동으로 기존 컬럼명(`s5_*_modified`)을 새 컬럼명(`s5_regenerated_*`)으로 매핑
- 모든 새 컬럼이 자동으로 추가됨
- 데이터 일관성 보장

#### 옵션 2: 수동 마이그레이션 (기존 데이터 유지 필요 시)

**Google Sheets에서:**
1. S5 테이블 열기
2. 컬럼명 변경:
   - `s5_front_modified` → `s5_regenerated_front`
   - `s5_back_modified` → `s5_regenerated_back`
   - `s5_modified_timestamp` → `s5_regeneration_timestamp`
3. 새 컬럼 추가:
   - `s5_description` (Text)
   - `s5_evidence_ref` (Text)
   - `s5_regenerated_image_filename` (Image)
   - `s5_regeneration_trigger_score` (Number)
   - `s5_was_regenerated` (Number)

---

### 2. Ratings 테이블 마이그레이션

#### 옵션 1: 재생성 (권장)
```bash
# Assignments.csv가 있으면 Ratings.csv가 자동으로 생성됨
python 3_Code/src/tools/final_qa/export_appsheet_tables.py \
  --run_dir "2_Data/metadata/generated/{RUN_TAG}" \
  --out_dir "2_Data/qa_appsheet_export/{RUN_TAG}" \
  --copy_images true
```

#### 옵션 2: 수동 마이그레이션

**Google Sheets에서:**
1. Ratings 테이블 열기
2. 컬럼명 변경:
   - `overall_quality_pre` → `educational_quality_pre`
   - `overall_quality_post` → `educational_quality_post`
   - `s5_revealed_ts` → 제거 (또는 `post_started_ts`로 대체)
3. 새 컬럼 추가:
   - `s5_started_ts` (Date/Time)
   - `s5_submitted_ts` (Date/Time)
   - `s5_duration_sec` (Number, Virtual Column)
   - `ai_self_reliability` (Number, 1-5)
   - `ai_self_reliability_comment` (LongText)
   - `accept_ai_correction` (Enum: ACCEPT, REJECT, PARTIAL)
   - `ai_correction_quality` (Number, 1-5)
   - `ai_correction_comment` (LongText)

---

### 3. Cards 테이블 마이그레이션

**변경 없음**: Cards 테이블은 변경 사항이 없으므로 마이그레이션 불필요

---

## 하위 호환성

### 코드 레벨 하위 호환성

`export_appsheet_tables.py`는 기존 컬럼명도 읽어서 새 컬럼명으로 자동 매핑합니다:

```python
"s5_regenerated_front": regen.get("front", "") or s5.get("s5_regenerated_front") or s5.get("s5_front_modified", ""),
"s5_regenerated_back": regen.get("back", "") or s5.get("s5_regenerated_back") or s5.get("s5_back_modified", ""),
"s5_regeneration_timestamp": s5.get("s5_regeneration_timestamp") or s5.get("s5_modified_timestamp", ""),
```

**우선순위:**
1. 새 컬럼명 (`s5_regenerated_*`)
2. 기존 컬럼명 (`s5_*_modified`)
3. 빈 문자열

---

## AppSheet 설정 업데이트

### S5 테이블

1. **컬럼명 변경:**
   - `s5_front_modified` → `s5_regenerated_front`
   - `s5_back_modified` → `s5_regenerated_back`
   - `s5_modified_timestamp` → `s5_regeneration_timestamp`

2. **새 컬럼 추가:**
   - `s5_description` (Text)
   - `s5_evidence_ref` (Text)
   - `s5_regenerated_image_filename` (Image)
   - `s5_regeneration_trigger_score` (Number)
   - `s5_was_regenerated` (Number)

### Ratings 테이블

1. **컬럼명 변경:**
   - `overall_quality_pre` → `educational_quality_pre`
   - `overall_quality_post` → `educational_quality_post`

2. **컬럼 제거:**
   - `s5_revealed_ts` (더 이상 사용하지 않음, `post_started_ts`로 대체)

3. **새 컬럼 추가:**
   - S5 Final Assessment 관련 컬럼 (위의 "추가된 컬럼" 참고)

---

## 데이터 마이그레이션 스크립트 (선택사항)

기존 데이터를 유지하면서 마이그레이션하려면:

```python
import csv
from pathlib import Path

def migrate_s5_csv(old_path: Path, new_path: Path):
    """기존 S5.csv를 새 형식으로 마이그레이션"""
    with old_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # 컬럼명 매핑
    for row in rows:
        if "s5_front_modified" in row and not row.get("s5_regenerated_front"):
            row["s5_regenerated_front"] = row.pop("s5_front_modified", "")
        if "s5_back_modified" in row and not row.get("s5_regenerated_back"):
            row["s5_regenerated_back"] = row.pop("s5_back_modified", "")
        if "s5_modified_timestamp" in row and not row.get("s5_regeneration_timestamp"):
            row["s5_regeneration_timestamp"] = row.pop("s5_modified_timestamp", "")
    
    # 새 컬럼 추가 (빈 값)
    new_cols = ["s5_description", "s5_evidence_ref", "s5_regenerated_image_filename",
                "s5_regeneration_trigger_score", "s5_was_regenerated"]
    for row in rows:
        for col in new_cols:
            if col not in row:
                row[col] = ""
    
    # 새 CSV 작성
    fieldnames = [
        "card_uid", "card_id", "run_tag", "arm", "group_id",
        "s5_blocking_error", "s5_technical_accuracy", "s5_educational_quality",
        "s5_issues_json", "s5_description", "s5_evidence_ref", "s5_rag_evidence_json",
        "s5_card_image_blocking_error", "s5_card_image_anatomical_accuracy",
        "s5_card_image_prompt_compliance", "s5_card_image_text_image_consistency",
        "s5_card_image_quality", "s5_card_image_safety_flag", "s5_card_image_issues_json",
        "s5_regenerated_front", "s5_regenerated_back", "s5_regenerated_image_filename",
        "s5_regeneration_timestamp", "s5_regeneration_trigger_score", "s5_was_regenerated"
    ]
    
    with new_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
```

---

## 체크리스트

### S5 테이블
- [ ] 기존 컬럼명 변경 (`s5_*_modified` → `s5_regenerated_*`)
- [ ] 새 컬럼 추가 (`s5_description`, `s5_evidence_ref`, 등)
- [ ] AppSheet에서 컬럼 타입 설정
- [ ] Virtual Column 업데이트 (있는 경우)

### Ratings 테이블
- [ ] 기존 컬럼명 변경 (`overall_quality_*` → `educational_quality_*`)
- [ ] `s5_revealed_ts` 제거 또는 `post_started_ts`로 대체
- [ ] 새 컬럼 추가 (S5 Final Assessment 관련)
- [ ] AppSheet에서 컬럼 타입 및 Enum 설정
- [ ] Virtual Column 업데이트

### Cards 테이블
- [ ] 변경 없음 (확인만)

---

## 참고 문서

- **S5 Postrepair Merge**: `AppSheet_S5_Postrepair_Merge.md`
- **S5 Regenerated Columns**: `AppSheet_S5_Regenerated_Columns_Merge.md`
- **Column Descriptions**: `AppSheet_Column_Descriptions.md`
- **Exporter Code**: `3_Code/src/tools/final_qa/export_appsheet_tables.py`

---

**문서 버전:** 1.0  
**최종 업데이트:** 2025-01-01


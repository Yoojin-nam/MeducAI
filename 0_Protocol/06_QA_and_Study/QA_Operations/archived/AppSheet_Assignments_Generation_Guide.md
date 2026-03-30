# AppSheet Assignments 테이블 생성 가이드

**목적:** `Assignments.csv`의 각 필드가 Export 시 어떤 값들이 들어가는지 명확히 정의합니다.

## 현재 상황

`export_appsheet_tables.py`는 **Assignments.csv 템플릿만 생성**합니다 (빈 헤더만).  
실제 데이터는 **별도로 생성**해야 합니다.

## Assignments 테이블 필드 정의

### 1. `assignment_id` (Text, Key)

**생성 방법:**
```
assignment_id = f"{rater_email}::{card_uid}::{batch_id}"
```

**예시:**
- `rater1@example.com::group_01::entity_001__Q1__0::batch_001`
- `rater2@example.com::group_02::entity_002__Q2__1::batch_001`

**특징:**
- 고유 식별자 (Primary Key)
- `rater_email`, `card_uid`, `batch_id`를 조합하여 생성
- 중복 방지: 동일한 (rater, card, batch) 조합은 하나만 존재

---

### 2. `rater_email` (Email)

**생성 방법:**
- 명단(예: `reviewer_master.csv`)에서 배정
- 각 평가자에게 고유한 이메일 주소

**예시:**
- `rater1@example.com`
- `rater2@example.com`
- `resident.kim@hospital.ac.kr`

**특징:**
- AppSheet에서 `USEREMAIL()`과 매칭되어 자동 필터링
- Google 로그인 이메일과 일치해야 함

---

### 3. `card_uid` (Text, Ref → Cards)

**생성 방법:**
- `Cards.csv`에서 가져옴
- 형식: `{group_id}::{card_id}`
- `card_id` 형식: `{entity_id}__{card_role}__{card_idx_in_entity}`

**예시:**
- `group_01::entity_001__Q1__0`
- `group_02::entity_002__Q2__1`

**특징:**
- `Cards` 테이블의 Primary Key와 일치해야 함
- `export_appsheet_tables.py`에서 자동 생성됨

---

### 4. `card_id` (Text)

**생성 방법:**
- `Cards.csv`에서 가져옴
- 형식: `{entity_id}__{card_role}__{card_idx_in_entity}`

**예시:**
- `entity_001__Q1__0`
- `entity_002__Q2__1`

**특징:**
- `card_uid`의 일부 (group_id 제외)
- 참고용 (실제 Key는 `card_uid`)

---

### 5. `assignment_order` (Number)

**생성 방법:**
- **한 명당 1부터 시작하여 순차적으로 배정**
- 각 `rater_email`별로 독립적으로 카운트
- 예: rater1은 1, 2, 3, ..., 30 (또는 200)
- 예: rater2도 1, 2, 3, ..., 30 (또는 200)

**예시:**
```
rater1@example.com, card_uid_1, assignment_order=1
rater1@example.com, card_uid_2, assignment_order=2
rater1@example.com, card_uid_3, assignment_order=3
...
rater1@example.com, card_uid_30, assignment_order=30

rater2@example.com, card_uid_10, assignment_order=1
rater2@example.com, card_uid_20, assignment_order=2
...
```

**특징:**
- AppSheet에서 "Case 1", "Case 2" 형식으로 표시
- 정렬 기준으로 사용 (`Sort: assignment_order ASC`)
- **안정성 중요**: 한 번 배정되면 변경하지 않음

---

### 6. `batch_id` (Text)

**생성 방법:**
- 배치 구분자 (예: `batch_001`, `batch_002`, `round_1`, `round_2`)
- 연구 설계에 따라 배정
- 예: 시간대별 배치, 그룹별 배치, 라운드별 배치

**예시:**
- `batch_001` (첫 번째 배치)
- `batch_002` (두 번째 배치)
- `round_1` (첫 번째 라운드)
- `round_2` (두 번째 라운드)

**특징:**
- 동일한 배치 내에서만 비교 분석
- 배치 간 비교는 별도 분석 필요

---

### 7. `status` (Enum: "To do", "In Progress", "Completed")

**생성 방법:**
- **초기값:** `"To do"` (모든 assignment)
- **프로그램 실행 중 업데이트:**
  - 평가 시작 시: `"In Progress"`
  - 평가 완료 시: `"Completed"`

**상태 전이:**
```
To do → In Progress → Completed
```

**특징:**
- AppSheet 액션으로 자동 업데이트
- Python 분석 시 `status == "Completed"`만 필터링

---

## Assignments.csv 생성 스크립트 예시

```python
import csv
from pathlib import Path

def generate_assignments_csv(
    cards_csv_path: Path,
    rater_emails: list[str],
    cards_per_rater: int,
    batch_id: str,
    out_path: Path,
) -> None:
    """
    Assignments.csv 생성
    
    Args:
        cards_csv_path: Cards.csv 경로
        rater_emails: 평가자 이메일 리스트
        cards_per_rater: 평가자당 배정할 카드 수
        batch_id: 배치 ID
        out_path: 출력 경로
    """
    # Cards.csv 읽기
    cards = []
    with cards_csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cards = list(reader)
    
    # Assignments 생성
    assignments = []
    card_idx = 0
    
    for rater_email in rater_emails:
        for order in range(1, cards_per_rater + 1):
            if card_idx >= len(cards):
                break  # 카드가 부족하면 중단
            
            card = cards[card_idx]
            card_uid = card["card_uid"]
            card_id = card["card_id"]
            
            assignment_id = f"{rater_email}::{card_uid}::{batch_id}"
            
            assignments.append({
                "assignment_id": assignment_id,
                "rater_email": rater_email,
                "card_uid": card_uid,
                "card_id": card_id,
                "assignment_order": order,
                "batch_id": batch_id,
                "status": "To do",
            })
            
            card_idx += 1
    
    # CSV 작성
    fieldnames = [
        "assignment_id",
        "rater_email",
        "card_uid",
        "card_id",
        "assignment_order",
        "batch_id",
        "status",
    ]
    
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(assignments)
    
    print(f"[OK] Generated {len(assignments)} assignments to {out_path}")


# 사용 예시
if __name__ == "__main__":
    cards_csv = Path("2_Data/processed/appsheet/run_001/Cards.csv")
    rater_emails = [
        "rater1@example.com",
        "rater2@example.com",
        "rater3@example.com",
    ]
    cards_per_rater = 30  # 또는 200
    batch_id = "batch_001"
    out_path = Path("2_Data/processed/appsheet/run_001/Assignments.csv")
    
    generate_assignments_csv(
        cards_csv_path=cards_csv,
        rater_emails=rater_emails,
        cards_per_rater=cards_per_rater,
        batch_id=batch_id,
        out_path=out_path,
    )
```

---

## Export 워크플로우

### 1단계: Cards.csv 생성
```bash
python 3_Code/src/tools/final_qa/export_appsheet_tables.py \
  --run_dir "2_Data/metadata/generated/run_001" \
  --out_dir "2_Data/processed/appsheet/run_001" \
  --copy_images true
```

**결과:**
- `Cards.csv` 생성됨
- `Assignments.csv` 템플릿만 생성됨 (빈 헤더)

### 2단계: Assignments.csv 생성
```bash
python 3_Code/src/tools/final_qa/generate_assignments.py \
  --cards_csv "2_Data/processed/appsheet/run_001/Cards.csv" \
  --s5_csv "2_Data/processed/appsheet/run_001/S5.csv" \
  --batch_id "batch_001" \
  --seed 42 \
  --out_assignments_csv "2_Data/processed/appsheet/run_001/Assignments.csv" \
  --out_summary_json "2_Data/processed/appsheet/run_001/Assignments_summary.json"
```

**결과:**
- `Assignments.csv`에 실제 데이터 생성됨
- (선택) `Assignments_summary.json`에 배정/다운스케일/분과별 통계가 저장됨

**메모:**
- 샘플 데이터처럼 카드 수가 900/300 요구량보다 적으면 **자동으로 downscale**하여 가능한 범위 내에서 배정합니다.
- 전문의 분과 매칭은 기본적으로 `reviewer_master.csv`의 `subspecialty`(자유 텍스트)를 키워드 기반으로 `groups_canonical.csv`의 `specialty` 키로 매핑합니다.
  - 매핑이 안 되는 분과는(예: 현재 전문의 명단에 해당 분과가 없을 때) 해당 분과 전문의 배정을 스킵하고 summary에 경고로 남깁니다.

### 3단계: Ratings.csv 자동 생성 (선택)
`export_appsheet_tables.py`가 `Assignments.csv`를 읽어서 `Ratings.csv`를 자동 생성합니다:

```python
# export_appsheet_tables.py 내부 로직
if assignments_path.exists() and cards_path.exists():
    _generate_ratings_from_assignments(
        assignments_path=assignments_path,
        cards_path=cards_path,
        out_path=out_dir / "Ratings.csv",
        fieldnames=ratings_fieldnames,
    )
```

**결과:**
- `Ratings.csv`에 모든 assignment에 대한 빈 행이 미리 생성됨
- `rating_id = f"{card_uid}::{rater_email}"` 형식

---

## 주의사항

### 1. `assignment_order` 안정성
- 한 번 배정되면 **변경하지 않음**
- AppSheet에서 정렬 기준으로 사용
- Python 분석 시에도 동일한 순서 유지

### 2. `card_uid` 일관성
- `Cards.csv`의 `card_uid`와 정확히 일치해야 함
- `export_appsheet_tables.py`에서 생성된 형식 사용

### 3. `rater_email` 일치
- Google 로그인 이메일과 정확히 일치해야 함
- 대소문자 구분 (일반적으로 소문자 사용 권장)

### 4. `batch_id` 설계
- 연구 설계에 따라 배치 구분
- 동일한 배치 내에서만 비교 분석

---

## 다음 단계

1. **Assignments 생성 스크립트 사용**
   - `3_Code/src/tools/final_qa/generate_assignments.py`
   - `reviewer_master.csv` 기반으로 전공의/전문의 배정 생성
   - S5 점수가 낮거나 blocking flag가 있는 항목을 high-risk로 우선 배정

2. **Export 워크플로우 통합**
   - `export_appsheet_tables.py`에 Assignments 생성 옵션 추가 (선택)
   - 또는 별도 스크립트로 분리

3. **테스트**
   - 소규모 데이터로 Assignments 생성 테스트
   - AppSheet에서 정상 작동 확인


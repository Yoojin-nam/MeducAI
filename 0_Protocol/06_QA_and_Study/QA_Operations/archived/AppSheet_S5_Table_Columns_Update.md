# AppSheet S5 테이블 컬럼 업데이트

**작성일:** 2025-01-01  
**목적:** S5 테이블에 `s5_description`과 `s5_evidence_ref` 컬럼 추가

---

## 추가된 컬럼

### 1. `s5_description` (Text)

**용도:** `s5_issues_json`에서 추출한 `description` 값들을 콤마로 구분하여 표시

**생성 방법:**
- `export_appsheet_tables.py`에서 `s5_issues_json`을 파싱하여 자동 생성
- 각 issue의 `description` 필드를 추출하여 콤마로 구분

**예시:**
```
"Judge returned blocking_error=true but technical_accuracy!=0.0; forcing technical_accuracy=0.0 due to clinical blocking signal., S5 normalized technical_accuracy: 0.5"
```

**빈 값 처리:**
- `s5_issues_json`이 비어있거나 파싱 에러가 발생하면 빈 문자열("")

---

### 2. `s5_evidence_ref` (Text)

**용도:** `s5_issues_json`에서 추출한 `evidence_ref` 또는 `rag_evidence` 값들을 콤마로 구분하여 표시

**생성 방법:**
- `export_appsheet_tables.py`에서 `s5_issues_json`을 파싱하여 자동 생성
- 각 issue의 `evidence_ref` 또는 `rag_evidence` 필드를 추출
- 리스트인 경우 각 항목의 `source_id` 또는 `source_excerpt` 추출

**예시:**
```
"source_123, source_456, source_789"
```

**빈 값 처리:**
- `s5_issues_json`이 비어있거나 파싱 에러가 발생하면 빈 문자열("")
- `evidence_ref`가 없는 issue는 무시

---

## 구현 세부사항

### `export_appsheet_tables.py` 변경사항

#### 1. `_extract_issues_description` 함수 추가

```python
def _extract_issues_description(issues_json_str: str) -> str:
    """Extract description values from s5_issues_json.
    
    Args:
        issues_json_str: JSON string containing list of issue dictionaries
    
    Returns:
        Comma-separated string of description values, or empty string if empty/error
    """
    if not issues_json_str or issues_json_str.strip() == "":
        return ""
    
    try:
        issues = json.loads(issues_json_str)
        if not isinstance(issues, list):
            return ""
        
        descriptions = []
        for issue in issues:
            if isinstance(issue, dict):
                desc = issue.get("description", "")
                if desc and str(desc).strip():
                    descriptions.append(str(desc).strip())
        
        return ", ".join(descriptions) if descriptions else ""
    except (json.JSONDecodeError, TypeError, ValueError):
        return ""
```

#### 2. `_extract_issues_evidence_ref` 함수 추가

```python
def _extract_issues_evidence_ref(issues_json_str: str) -> str:
    """Extract evidence_ref values from s5_issues_json.
    
    Args:
        issues_json_str: JSON string containing list of issue dictionaries
    
    Returns:
        Comma-separated string of evidence_ref values, or empty string if empty/error
    """
    if not issues_json_str or issues_json_str.strip() == "":
        return ""
    
    try:
        issues = json.loads(issues_json_str)
        if not isinstance(issues, list):
            return ""
        
        evidence_refs = []
        for issue in issues:
            if isinstance(issue, dict):
                # Check both "evidence_ref" and "rag_evidence" fields
                evidence_ref = issue.get("evidence_ref") or issue.get("rag_evidence")
                if evidence_ref:
                    if isinstance(evidence_ref, list):
                        # If it's a list, extract source_id or description from each item
                        for ev in evidence_ref:
                            if isinstance(ev, dict):
                                source_id = ev.get("source_id") or ev.get("source_excerpt", "")
                                if source_id and str(source_id).strip():
                                    evidence_refs.append(str(source_id).strip())
                    elif isinstance(evidence_ref, str) and evidence_ref.strip():
                        evidence_refs.append(evidence_ref.strip())
                    else:
                        # Try to convert to string
                        ev_str = str(evidence_ref).strip()
                        if ev_str:
                            evidence_refs.append(ev_str)
        
        return ", ".join(evidence_refs) if evidence_refs else ""
    except (json.JSONDecodeError, TypeError, ValueError):
        return ""
```

#### 3. S5 테이블 생성 시 컬럼 추가

```python
s5_rows.append(
    {
        "card_uid": card_uid,
        "card_id": s5.get("card_id", ""),
        # ... 기존 컬럼들 ...
        "s5_issues_json": s5.get("s5_issues_json", "[]"),
        "s5_description": _extract_issues_description(s5.get("s5_issues_json", "[]")),
        "s5_evidence_ref": _extract_issues_evidence_ref(s5.get("s5_issues_json", "[]")),
        # ... 나머지 컬럼들 ...
    }
)
```

#### 4. CSV fieldnames에 추가

```python
_write_csv(
    out_dir / "S5.csv",
    [
        "card_uid",
        # ... 기존 필드들 ...
        "s5_issues_json",
        "s5_description",
        "s5_evidence_ref",
        # ... 나머지 필드들 ...
    ],
    s5_rows,
)
```

---

## AppSheet 설정

### 1. S5 테이블 컬럼 추가

1. `Data` → `Tables` → `S5` 클릭
2. `+ Add column` 클릭
3. 컬럼명: `s5_description`
4. `Type`: `Text` 선택
5. `Save` 클릭
6. 동일하게 `s5_evidence_ref` 컬럼 추가

### 2. Display Name 설정

**`s5_description`:**
- **Display Name**: `S5 Issues Description`
- **Description**: `S5 validation에서 발견된 issues의 description 목록`

**`s5_evidence_ref`:**
- **Display Name**: `S5 Evidence References`
- **Description**: `S5 validation issues와 관련된 evidence reference 목록`

---

## S5 Summary Formula 업데이트

S5 Summary Virtual Column에 issues 정보를 포함하도록 업데이트:

```
IF(
  ISBLANK([card_uid].[S5_one]),
  "",
  CONCATENATE(
    # ... 기존 항목들 ...
    IF(ISNOTBLANK([card_uid].[S5_one].[s5_description]), 
       CONCATENATE("Issues: ", [card_uid].[S5_one].[s5_description], CHAR(10)), 
       ""),
    IF(ISNOTBLANK([card_uid].[S5_one].[s5_evidence_ref]), 
       CONCATENATE("Evidence Ref: ", [card_uid].[S5_one].[s5_evidence_ref]), 
       "")
  )
)
```

---

## 데이터 예시

### 입력 (`s5_issues_json`):
```json
[
  {
    "severity": "warning",
    "type": "s5_output_inconsistency",
    "description": "Judge returned blocking_error=true but technical_accuracy!=0.0",
    "issue_code": "S5_INCONSISTENT_OUTPUT",
    "evidence_ref": [
      {"source_id": "source_123", "source_excerpt": "..."},
      {"source_id": "source_456", "source_excerpt": "..."}
    ]
  },
  {
    "severity": "minor",
    "type": "entity_type_mismatch",
    "description": "Entity type mismatch",
    "issue_code": "S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH"
  }
]
```

### 출력:
- **`s5_description`**: `"Judge returned blocking_error=true but technical_accuracy!=0.0, Entity type mismatch"`
- **`s5_evidence_ref`**: `"source_123, source_456"`

---

## 참고 문서

- **Exporter 코드**: `3_Code/src/tools/final_qa/export_appsheet_tables.py`
- **S5 Summary Formula**: `AppSheet_S5_Summary_Formula.md`
- **S5 Issues 중복 분석**: `S5_Issues_JSON_Duplicate_Analysis.md`

---

**문서 버전:** 1.0  
**최종 업데이트:** 2025-01-01


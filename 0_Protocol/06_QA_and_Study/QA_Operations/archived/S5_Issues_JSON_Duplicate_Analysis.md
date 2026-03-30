# S5 Issues JSON 중복 문제 분석

**작성일:** 2025-01-01  
**문제:** `s5_issues_json`에 같은 값이 2개 들어가는 경우 발생

---

## 문제 원인

### 1. 중복 발생 시나리오

**시나리오 1: LLM 응답과 코드 추가의 중복**

1. LLM이 이미 `issues` 배열에 특정 issue를 포함시켜서 반환
   - 예: `"Judge returned blocking_error=true but technical_accuracy!=0.0..."`
2. 코드에서 normalization 과정에서 같은 내용의 issue를 `_append_inconsistency_issue()`로 다시 추가
3. 결과: 같은 issue가 2번 들어감

**시나리오 2: 여러 normalization 단계에서 중복 추가**

```python
# 1354: LLM이 반환한 issues
issues = parsed_json.get("issues", [])

# 1360: technical_accuracy normalization
if ta_warn:
    issues = _append_inconsistency_issue(issues, note=f"S5 normalized technical_accuracy: {ta_warn}")

# 1363-1375: blocking_error와 technical_accuracy 불일치 처리
if blocking_error and technical_accuracy != 0.0:
    if _has_clinical_blocking_signal(issues):
        issues = _append_inconsistency_issue(
            issues,
            note="Judge returned blocking_error=true but technical_accuracy!=0.0; forcing technical_accuracy=0.0 due to clinical blocking signal.",
        )
```

**문제점:**
- LLM이 이미 "blocking_error=true but technical_accuracy!=0.0" issue를 반환했을 수 있음
- 코드에서도 같은 내용의 issue를 추가
- 중복 체크 없이 `base.append()`만 수행

### 2. `_append_inconsistency_issue` 함수의 문제

```python
def _append_inconsistency_issue(issues: Any, *, note: str) -> List[Dict[str, Any]]:
    base: List[Dict[str, Any]] = []
    if isinstance(issues, list):
        base = [x for x in issues if isinstance(x, dict)]
    base.append(
        {
            "severity": "warning",
            "type": "s5_output_inconsistency",
            "description": note,
            "issue_code": "S5_INCONSISTENT_OUTPUT",
            "affected_stage": "S5",
            "confidence": 0.8,
            "recommended_fix_target": "S5_SYSTEM",
            "prompt_patch_hint": "Enforce: blocking_error=true ONLY for clinical safety errors AND implies technical_accuracy=0.0.",
        }
    )
    return base
```

**문제점:**
- 중복 체크를 하지 않음
- `description`이 같아도 그냥 추가함
- `issue_code`가 같아도 그냥 추가함

---

## 해결 방법

### 방법 1: 중복 체크 추가 (권장)

`_append_inconsistency_issue` 함수에 중복 체크 로직 추가:

```python
def _append_inconsistency_issue(issues: Any, *, note: str) -> List[Dict[str, Any]]:
    base: List[Dict[str, Any]] = []
    if isinstance(issues, list):
        base = [x for x in issues if isinstance(x, dict)]
    
    # 중복 체크: 같은 description이 이미 있는지 확인
    note_normalized = note.strip().lower()
    has_duplicate = False
    for existing_issue in base:
        if isinstance(existing_issue, dict):
            existing_desc = existing_issue.get("description", "").strip().lower()
            existing_code = existing_issue.get("issue_code", "")
            # description이 같거나, issue_code가 "S5_INCONSISTENT_OUTPUT"이고 description이 유사하면 중복으로 간주
            if (existing_desc == note_normalized or 
                (existing_code == "S5_INCONSISTENT_OUTPUT" and 
                 note_normalized in existing_desc or existing_desc in note_normalized)):
                has_duplicate = True
                break
    
    if not has_duplicate:
        base.append(
            {
                "severity": "warning",
                "type": "s5_output_inconsistency",
                "description": note,
                "issue_code": "S5_INCONSISTENT_OUTPUT",
                "affected_stage": "S5",
                "confidence": 0.8,
                "recommended_fix_target": "S5_SYSTEM",
                "prompt_patch_hint": "Enforce: blocking_error=true ONLY for clinical safety errors AND implies technical_accuracy=0.0.",
            }
        )
    
    return base
```

### 방법 2: 최종 정리 단계에서 중복 제거

issues를 최종적으로 저장하기 전에 중복 제거:

```python
def _deduplicate_issues(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate issues based on description and issue_code."""
    seen = set()
    deduplicated = []
    
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        
        # Create a unique key from description and issue_code
        desc = issue.get("description", "").strip().lower()
        code = issue.get("issue_code", "")
        key = (code, desc)
        
        if key not in seen:
            seen.add(key)
            deduplicated.append(issue)
    
    return deduplicated

# 최종 저장 전에 호출
issues = _deduplicate_issues(issues)
```

### 방법 3: LLM 응답에서 이미 있는 issue는 건너뛰기

LLM이 반환한 issues를 먼저 확인하고, 이미 있는 내용은 추가하지 않기:

```python
# LLM이 반환한 issues에서 특정 패턴이 있는지 확인
def _has_similar_issue(issues: List[Dict[str, Any]], pattern: str) -> bool:
    """Check if issues list already contains a similar issue."""
    pattern_lower = pattern.strip().lower()
    for issue in issues:
        if isinstance(issue, dict):
            desc = issue.get("description", "").strip().lower()
            if pattern_lower in desc or desc in pattern_lower:
                return True
    return False

# 사용 예시
if blocking_error and technical_accuracy != 0.0:
    if _has_clinical_blocking_signal(issues):
        # 이미 비슷한 issue가 있는지 확인
        if not _has_similar_issue(issues, "blocking_error=true but technical_accuracy!=0.0"):
            issues = _append_inconsistency_issue(
                issues,
                note="Judge returned blocking_error=true but technical_accuracy!=0.0; forcing technical_accuracy=0.0 due to clinical blocking signal.",
            )
```

---

## 권장 해결책

**방법 1 (중복 체크 추가) + 방법 2 (최종 정리)**를 함께 사용:

1. `_append_inconsistency_issue`에 중복 체크 추가
2. 최종 저장 전에 `_deduplicate_issues`로 한 번 더 정리

이렇게 하면:
- 실시간으로 중복을 방지
- 최종적으로 한 번 더 안전장치 역할

---

## 코드 수정 예시

### `_append_inconsistency_issue` 함수 개선

```python
def _append_inconsistency_issue(issues: Any, *, note: str) -> List[Dict[str, Any]]:
    base: List[Dict[str, Any]] = []
    if isinstance(issues, list):
        base = [x for x in issues if isinstance(x, dict)]
    
    # 중복 체크: 같은 description이 이미 있는지 확인
    note_normalized = note.strip().lower()
    has_duplicate = False
    for existing_issue in base:
        if isinstance(existing_issue, dict):
            existing_desc = existing_issue.get("description", "").strip().lower()
            existing_code = existing_issue.get("issue_code", "")
            # description이 정확히 같거나, issue_code가 같고 description이 유사하면 중복
            if existing_desc == note_normalized:
                has_duplicate = True
                break
            # S5_INCONSISTENT_OUTPUT인 경우 description이 포함 관계면 중복으로 간주
            if (existing_code == "S5_INCONSISTENT_OUTPUT" and 
                (note_normalized in existing_desc or existing_desc in note_normalized)):
                has_duplicate = True
                break
    
    if not has_duplicate:
        base.append(
            {
                "severity": "warning",
                "type": "s5_output_inconsistency",
                "description": note,
                "issue_code": "S5_INCONSISTENT_OUTPUT",
                "affected_stage": "S5",
                "confidence": 0.8,
                "recommended_fix_target": "S5_SYSTEM",
                "prompt_patch_hint": "Enforce: blocking_error=true ONLY for clinical safety errors AND implies technical_accuracy=0.0.",
            }
        )
    
    return base
```

### 최종 정리 함수 추가

```python
def _deduplicate_issues(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate issues based on description and issue_code.
    
    Two issues are considered duplicates if:
    1. They have the same issue_code AND description (case-insensitive)
    2. They are both S5_INCONSISTENT_OUTPUT and descriptions are similar (substring match)
    """
    if not isinstance(issues, list):
        return []
    
    seen = set()
    deduplicated = []
    
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        
        desc = issue.get("description", "").strip().lower()
        code = issue.get("issue_code", "")
        
        # Create a unique key
        key = (code, desc)
        
        # For S5_INCONSISTENT_OUTPUT, also check for substring matches
        if code == "S5_INCONSISTENT_OUTPUT":
            is_duplicate = False
            for seen_code, seen_desc in seen:
                if seen_code == code:
                    # Check if descriptions are similar (one contains the other)
                    if desc in seen_desc or seen_desc in desc:
                        is_duplicate = True
                        break
            if is_duplicate:
                continue
        
        if key not in seen:
            seen.add(key)
            deduplicated.append(issue)
    
    return deduplicated
```

### 사용 위치

```python
# 카드 validation 결과 저장 전
result = {
    "blocking_error": blocking_error,
    "technical_accuracy": technical_accuracy,
    "educational_quality": educational_quality,
    "issues": _deduplicate_issues(issues),  # 중복 제거
    "rag_evidence": rag_evidence,
}
```

---

## 테스트 방법

1. **중복 시나리오 재현:**
   - LLM이 이미 issue를 포함한 응답을 반환하도록 설정
   - 코드에서 같은 내용의 issue를 추가
   - 최종 `issues` 배열에 중복이 없는지 확인

2. **다양한 중복 패턴 테스트:**
   - 정확히 같은 description
   - 유사한 description (하나가 다른 하나를 포함)
   - 같은 issue_code지만 다른 description

---

## 참고 문서

- **S5 Validator 코드**: `3_Code/src/05_s5_validator.py`
- **Issues 구조**: S5 validation JSON schema

---

**문서 버전:** 1.0  
**최종 업데이트:** 2025-01-01


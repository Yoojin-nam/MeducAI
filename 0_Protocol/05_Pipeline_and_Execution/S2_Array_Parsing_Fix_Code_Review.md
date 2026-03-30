# S2 배열 파싱 수정 사항 코드 리뷰 및 최적화

**작성일**: 2025-12-26  
**목적**: 프롬프트/파싱 문제 해결 과정에서 발생한 비효율적이거나 우회적인 수정 사항 점검

---

## 발견된 문제점

### 1. ❌ 비효율: `prefer_anki_cards=True` 하드코딩

**문제**:
- `extract_json_object()` 함수가 S1과 S2 모두에서 사용됨
- 모든 파싱 경로에서 `prefer_anki_cards=True`로 하드코딩됨
- S1에서는 `anki_cards` 필드가 없으므로 불필요한 검색 수행

**영향**:
- S1에서 배열 파싱 시 `anki_cards` 필드를 찾기 위해 전체 배열을 순회 (비효율)
- 코드가 S2에만 특화되어 있어 재사용성 저하

**수정**:
- ✅ `extract_json_object()`에 `stage` 파라미터 추가
- ✅ `prefer_anki_cards = (stage == 2)`로 동적 결정
- ✅ S1에서는 `prefer_anki_cards=False`, S2에서는 `prefer_anki_cards=True`
- ✅ 모든 파싱 경로에서 하드코딩 제거

---

## 수정 사항 상세

### Before (비효율적)

```python
def extract_json_object(raw: str) -> Dict[str, Any]:
    # ...
    if isinstance(parsed, list):
        parsed = _extract_valid_object_from_array(parsed, prefer_anki_cards=True)  # ❌ 항상 True
```

**문제점**:
- S1에서도 `anki_cards` 필드를 찾기 위해 배열 전체를 순회
- S1에는 `anki_cards` 필드가 없으므로 불필요한 작업

### After (최적화)

```python
def extract_json_object(raw: str, stage: Optional[int] = None) -> Dict[str, Any]:
    # ...
    prefer_anki_cards = (stage == 2)  # ✅ S2일 때만 True
    
    if isinstance(parsed, list):
        parsed = _extract_valid_object_from_array(parsed, prefer_anki_cards=prefer_anki_cards)
```

**개선점**:
- S1에서는 첫 번째 dict 객체를 바로 반환 (효율적)
- S2에서만 `anki_cards` 필드를 가진 객체를 우선 선택
- 코드 재사용성 향상

---

## 검증된 올바른 수정 사항

### ✅ 1. 배열 파싱 로직 강화
- `_extract_valid_object_from_array()` 함수 추가
- 배열에서 유효한 객체 추출 로직 구현
- **평가**: 올바른 수정, 문제 해결에 직접적 기여

### ✅ 2. 진단 로깅 추가
- `validate_stage2()` 호출 전 JSON 구조 로깅
- `anki_cards` 필드 검증 및 경고
- **평가**: 디버깅에 유용, 성능 영향 미미

### ✅ 3. 프롬프트 개선
- S2 시스템 프롬프트에 단일 JSON 객체 반환 명시
- 배열 반환 금지 및 예시 제공
- **평가**: 근본 원인 해결, 예방적 조치

### ✅ 4. 에러 복구 메커니즘
- `card_count_mismatch` 발생 시 재시도 프롬프트 강화
- **평가**: 사용자 경험 개선, 적절한 수정

---

## Parallel 처리와의 관계

### 확인 사항
- ✅ Parallel 처리와는 무관한 수정 사항
- ✅ 모든 수정이 프롬프트/파싱 문제 해결에 집중
- ✅ Parallel 처리 로직에는 영향 없음

### Parallel 처리 관련 코드
- Entity-level parallelization은 그대로 유지
- IPC 메커니즘 (파일 기반)은 그대로 유지
- Worker pool 설정은 그대로 유지

---

## 최종 평가

### 수정 전 상태
- ❌ `prefer_anki_cards=True` 하드코딩 (비효율)
- ✅ 배열 파싱 로직 강화 (올바름)
- ✅ 진단 로깅 추가 (올바름)
- ✅ 프롬프트 개선 (올바름)
- ✅ 에러 복구 메커니즘 (올바름)

### 수정 후 상태
- ✅ `prefer_anki_cards` 동적 결정 (최적화)
- ✅ 배열 파싱 로직 강화 (유지)
- ✅ 진단 로깅 추가 (유지)
- ✅ 프롬프트 개선 (유지)
- ✅ 에러 복구 메커니즘 (유지)

---

## 성능 영향 분석

### S1에서의 개선
- **Before**: 배열 파싱 시 `anki_cards` 필드 검색 (O(n))
- **After**: 첫 번째 dict 객체 반환 (O(1))
- **개선**: 불필요한 검색 제거

### S2에서의 영향
- **Before**: `prefer_anki_cards=True` 하드코딩
- **After**: `prefer_anki_cards=True` 동적 결정
- **영향**: 동일 (기능적으로 동일, 코드 품질 향상)

---

## 결론

1. ✅ **비효율 수정 완료**: `prefer_anki_cards` 하드코딩 제거
2. ✅ **코드 품질 향상**: Stage별 동적 처리로 재사용성 향상
3. ✅ **기능 유지**: S2에서의 동작은 동일하게 유지
4. ✅ **Parallel 처리와 무관**: 모든 수정이 프롬프트/파싱 문제에 집중

**최종 평가**: 수정 사항들이 올바르게 구현되었으며, 비효율적인 부분은 제거되었습니다.


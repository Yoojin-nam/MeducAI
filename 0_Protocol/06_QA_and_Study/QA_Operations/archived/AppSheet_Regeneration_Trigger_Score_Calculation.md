# Regeneration Trigger Score 계산 방법

**작성일:** 2025-01-01  
**목적:** `s5_regeneration_trigger_score` 값이 어떻게 계산되는지 설명

---

## 1. 현재 상태

### 1.1 구현 상태
- **현재:** 멀티에이전트 시스템이 아직 구축되지 않았으므로, `s5_regeneration_trigger_score`는 **아직 계산되지 않음**
- **향후:** 멀티에이전트 시스템에서 자가 평가 점수를 계산하여 이 값을 채움

### 1.2 데이터 흐름
1. S5 validation 결과에서 `s5_technical_accuracy`, `s5_educational_quality`, `s5_blocking_error` 등의 값이 생성됨
2. 멀티에이전트 시스템이 이 값들을 종합하여 **자가 평가 점수**를 계산
3. 이 점수가 특정 임계값(예: 70점) 미만이면 재생성 트리거
4. 재생성이 발생하면 `s5_regeneration_trigger_score`에 해당 점수 저장

---

## 2. 가능한 계산 방식 (제안)

### 2.1 방식 1: 가중 평균 기반

S5 validation 결과를 종합하여 0-100 점수로 변환:

```python
def calculate_regeneration_trigger_score(s5_result: Dict[str, Any]) -> float:
    """
    S5 validation 결과를 종합하여 재생성 트리거 점수 계산 (0-100)
    
    Args:
        s5_result: S5 validation 결과 딕셔너리
        
    Returns:
        float: 0-100 점수 (낮을수록 재생성 필요)
    """
    # 1. Blocking error가 있으면 즉시 낮은 점수
    if s5_result.get("s5_blocking_error"):
        return 30.0  # 또는 더 낮은 값
    
    # 2. Technical Accuracy (0.0, 0.5, 1.0) → 0-50점
    ta = s5_result.get("s5_technical_accuracy", 1.0)
    ta_score = ta * 50.0  # 0.0 → 0점, 0.5 → 25점, 1.0 → 50점
    
    # 3. Educational Quality (1-5 Likert) → 0-50점
    eq = s5_result.get("s5_educational_quality", 5)
    eq_score = (eq / 5.0) * 50.0  # 1 → 10점, 3 → 30점, 5 → 50점
    
    # 4. 종합 점수
    total_score = ta_score + eq_score  # 최대 100점
    
    return total_score
```

**특징:**
- Blocking error가 있으면 즉시 낮은 점수 (30점)
- Technical Accuracy와 Educational Quality를 동일 가중치로 합산
- 최대 100점, 최소 0점

---

### 2.2 방식 2: 이미지 평가 포함

이미지 관련 평가 항목도 포함:

```python
def calculate_regeneration_trigger_score_with_image(s5_result: Dict[str, Any]) -> float:
    """
    이미지 평가를 포함한 종합 점수 계산
    """
    # 1. Blocking error 체크 (텍스트 + 이미지)
    if s5_result.get("s5_blocking_error") or s5_result.get("s5_card_image_blocking_error"):
        return 30.0
    
    # 2. Technical Accuracy (0-50점)
    ta = s5_result.get("s5_technical_accuracy", 1.0)
    ta_score = ta * 50.0
    
    # 3. Educational Quality (0-30점)
    eq = s5_result.get("s5_educational_quality", 5)
    eq_score = (eq / 5.0) * 30.0
    
    # 4. Image Quality (0-20점) - 이미지가 있는 경우만
    img_quality = s5_result.get("s5_card_image_quality", 5)
    img_score = (img_quality / 5.0) * 20.0 if img_quality else 20.0  # 이미지 없으면 만점
    
    total_score = ta_score + eq_score + img_score
    
    return total_score
```

**특징:**
- 이미지 blocking error도 체크
- 이미지 품질 평가 포함
- 가중치: Technical Accuracy (50%) > Educational Quality (30%) > Image Quality (20%)

---

### 2.3 방식 3: 멀티에이전트 자가 평가 점수

멀티에이전트 시스템이 자체적으로 계산한 점수:

```python
def multi_agent_self_evaluation_score(
    s5_validation_result: Dict[str, Any],
    card_content: Dict[str, Any],
    reference_materials: List[Dict[str, Any]]
) -> float:
    """
    멀티에이전트 시스템이 여러 에이전트의 평가를 종합하여 계산한 점수
    
    Process:
    1. Agent 1: Technical Accuracy 전문가 → 점수1
    2. Agent 2: Educational Quality 전문가 → 점수2
    3. Agent 3: Image Quality 전문가 → 점수3 (이미지가 있는 경우)
    4. Agent 4: Meta-reviewer → 종합 점수
    
    Returns:
        float: 0-100 점수
    """
    # 멀티에이전트 시스템 구현 시 구체화
    # 현재는 S5 validation 결과를 기반으로 추정
    pass
```

**특징:**
- 여러 전문가 에이전트의 평가를 종합
- Meta-reviewer가 최종 점수 결정
- 더 정확하지만 구현 복잡도 높음

---

## 3. 임계값 (Threshold)

### 3.1 기본 임계값
- **기본값:** 70점 미만이면 재생성 트리거
- **설정 위치:** `generate_assignments.py`의 `--s5_trigger_score_lt` 파라미터 (기본값: 70.0)

### 3.2 임계값 조정
- **더 엄격하게:** 80점 미만 → 더 많은 재생성 발생
- **더 관대하게:** 60점 미만 → 재생성 빈도 감소

---

## 4. 구현 위치

### 4.1 현재 코드
- **읽기 위치:** `3_Code/src/tools/final_qa/export_appsheet_tables.py`
  - S5 테이블에서 `s5_regeneration_trigger_score` 값을 읽어서 CSV로 출력

### 4.2 향후 구현 위치
- **계산 위치:** 멀티에이전트 시스템 (아직 미구현)
  - S5 validation 결과를 받아서 점수 계산
  - 재생성 필요 여부 판단
  - 재생성 발생 시 `s5_regeneration_trigger_score`에 점수 저장

---

## 5. 데이터 예시

### 5.1 S5 Validation 결과 예시
```json
{
  "s5_blocking_error": false,
  "s5_technical_accuracy": 1.0,
  "s5_educational_quality": 4,
  "s5_card_image_blocking_error": false,
  "s5_card_image_quality": 4
}
```

### 5.2 계산된 Trigger Score
**방식 1 적용:**
- `ta_score = 1.0 * 50.0 = 50.0`
- `eq_score = (4 / 5.0) * 50.0 = 40.0`
- `total_score = 50.0 + 40.0 = 90.0`
- **결과:** 90점 > 70점 → 재생성 불필요

**낮은 점수 예시:**
```json
{
  "s5_blocking_error": false,
  "s5_technical_accuracy": 0.5,
  "s5_educational_quality": 2
}
```
- `ta_score = 0.5 * 50.0 = 25.0`
- `eq_score = (2 / 5.0) * 50.0 = 20.0`
- `total_score = 25.0 + 20.0 = 45.0`
- **결과:** 45점 < 70점 → 재생성 트리거

---

## 6. 연구 활용

### 6.1 분석 가능한 데이터
- `regeneration_trigger_score` 분포
- 재생성 발생 빈도와 점수의 상관관계
- 재생성 후 품질 개선 여부 (`accept_ai_correction`, `ai_correction_quality`)

### 6.2 논문 작성 시
- "AI Self-Reflection and Regeneration Trigger" 섹션
- 점수 계산 방식의 타당성 검증
- 임계값 최적화 연구

---

## 7. 참고 문서

- **S5 Final Assessment 설계**: `AppSheet_S5_Final_Assessment_Design.md`
- **S5 Validation 스펙**: `docs/s5_s1_validation_specification.md` (참고)
- **멀티에이전트 시스템 설계**: (향후 작성 예정)

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-01-01


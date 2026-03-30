# 멀티에이전트 시스템 구축 인계장

**작성일:** 2025-01-01  
**목적:** 멀티에이전트 시스템을 구축할 개발자를 위한 종합 인계 문서  
**상태:** 설계 완료, 구현 대기  
**관련 문서:**
- `AppSheet_S5_Final_Assessment_Design.md` - S5 Final Assessment 설계
- `AppSheet_Regeneration_Trigger_Score_Calculation.md` - 점수 계산 방법
- `AppSheet_QA_System_Specification.md` - 전체 시스템 스펙
- `MeducAI_Stage_Naming_MultiAgent_MLLM.md` - 논문 제목( Multi-Agent + MLLM ) 정합 단계명(S0–S6) 제안

---

## 1. 시스템 개요

### 1.1 목적

멀티에이전트 시스템은 **AI의 자기 개선(Self-Improvement) 능력을 검증**하기 위한 시스템입니다:

1. **자가 평가**: 여러 전문가 에이전트가 카드 품질을 평가하고 종합 점수 계산
2. **재생성 트리거**: 낮은 점수(예: 70점 미만)일 때 콘텐츠 재생성
3. **인간 검증**: 재생성된 콘텐츠를 인간 평가자가 검토하고 수용/거부 결정

### 1.2 워크플로우

```
S5 Validation 결과
    ↓
멀티에이전트 평가 (자가 평가 점수 계산)
    ↓
점수 < 임계값? → Yes → 콘텐츠 재생성
    ↓                    ↓
    No                  재생성된 콘텐츠 저장
    ↓                    ↓
AppSheet로 전송    AppSheet로 전송
    ↓                    ↓
S5 Final Assessment (인간 검증)
```

### 1.3 핵심 요구사항

- **입력**: S5 validation 결과 (`s5_blocking_error`, `s5_technical_accuracy`, `s5_educational_quality`, 등)
- **출력**: 
  - `s5_regeneration_trigger_score` (0-100 점수)
  - 재생성 필요 여부 (Boolean)
  - 재생성된 콘텐츠 (조건부)
- **통합**: `export_appsheet_tables.py`에서 S5 테이블에 결과 저장

---

## 2. 아키텍처 설계

### 2.1 멀티에이전트 구조

```
┌─────────────────────────────────────────────────────────┐
│              Multi-Agent Self-Evaluation System          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Agent 1:     │  │ Agent 2:     │  │ Agent 3:     │  │
│  │ Technical    │  │ Educational  │  │ Image        │  │
│  │ Accuracy     │  │ Quality      │  │ Quality      │  │
│  │ Expert       │  │ Expert       │  │ Expert       │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                 │           │
│         └─────────────────┼─────────────────┘           │
│                           │                             │
│                  ┌────────▼────────┐                    │
│                  │ Agent 4:        │                    │
│                  │ Meta-Reviewer  │                    │
│                  │ (Score          │                    │
│                  │  Aggregator)    │                    │
│                  └────────┬────────┘                    │
│                           │                             │
│                  ┌────────▼────────┐                    │
│                  │ Final Score     │                    │
│                  │ (0-100)         │                    │
│                  └────────┬────────┘                    │
│                           │                             │
│                  ┌────────▼────────┐                    │
│                  │ Regeneration   │                    │
│                  │ Decision       │                    │
│                  └─────────────────┘                    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 2.2 각 에이전트의 역할

#### Agent 1: Technical Accuracy Expert
- **입력**: 카드 텍스트 (`front`, `back`), S5 validation 결과
- **역할**: 사실 정확성, 임상 타당성 평가
- **출력**: Technical Accuracy 점수 (0.0, 0.5, 1.0) + 근거

#### Agent 2: Educational Quality Expert
- **입력**: 카드 텍스트, 학습 목표, 시험 범위
- **역할**: 교육적 가치, 시험 관련성 평가
- **출력**: Educational Quality 점수 (1-5 Likert) + 근거

#### Agent 3: Image Quality Expert (조건부)
- **입력**: 카드 이미지, 이미지 프롬프트, S5 이미지 평가 결과
- **역할**: 이미지 품질, 해부학적 정확성, 프롬프트 준수도 평가
- **출력**: Image Quality 점수 (1-5 Likert) + 근거
- **조건**: 이미지가 있는 카드만 평가

#### Agent 4: Meta-Reviewer (Score Aggregator)
- **입력**: Agent 1, 2, 3의 평가 결과
- **역할**: 
  - 각 에이전트의 평가를 종합하여 최종 점수 계산
  - 재생성 필요 여부 결정
  - 재생성 시 개선 방향 제시
- **출력**: 
  - `s5_regeneration_trigger_score` (0-100)
  - 재생성 필요 여부 (Boolean)
  - 개선 제안 (선택)

---

## 3. 데이터 모델

### 3.1 입력 데이터 (S5 Validation 결과)

**소스**: `3_Code/src/05_s5_validator.py`의 출력

```python
s5_validation_result = {
    # 카드 레벨 평가
    "s5_blocking_error": bool,  # True/False
    "s5_technical_accuracy": float,  # 0.0, 0.5, 1.0
    "s5_educational_quality": int,  # 1-5
    "s5_issues_json": str,  # JSON string with issues
    
    # 이미지 레벨 평가 (조건부)
    "s5_card_image_blocking_error": bool,  # True/False
    "s5_card_image_anatomical_accuracy": int,  # 1-5
    "s5_card_image_prompt_compliance": int,  # 1-5
    "s5_card_image_text_image_consistency": int,  # 1-5
    "s5_card_image_quality": int,  # 1-5
    "s5_card_image_safety_flag": bool,  # True/False
    
    # 메타데이터
    "card_uid": str,
    "s5_snapshot_id": str,
    # ... 기타 메타데이터
}
```

### 3.2 출력 데이터

**저장 위치**: S5 테이블 (Google Sheets / CSV)

```python
multi_agent_output = {
    # 점수 및 재생성 정보
    "s5_regeneration_trigger_score": float,  # 0-100
    "s5_regeneration_triggered": bool,  # True/False
    
    # 재생성된 콘텐츠 (조건부)
    "s5_regenerated_front": str,  # 재생성된 문제 텍스트 (조건부)
    "s5_regenerated_back": str,  # 재생성된 정답 텍스트 (조건부)
    "s5_regenerated_image_filename": str,  # 재생성된 이미지 파일명 (조건부)
    "s5_regeneration_timestamp": str,  # ISO 8601 format
    
    # 개선 제안 (선택)
    "s5_regeneration_suggestions": str,  # JSON string with improvement suggestions
    
    # 메타데이터
    "card_uid": str,
    "multi_agent_version": str,  # 예: "v1.0"
    "evaluation_timestamp": str,  # ISO 8601 format
}
```

---

## 4. 점수 계산 로직

### 4.1 기본 계산 방식 (권장)

**구현 위치**: `3_Code/src/tools/multi_agent/score_calculator.py` (새로 생성)

```python
def calculate_regeneration_trigger_score(
    s5_result: Dict[str, Any],
    agent_scores: Optional[Dict[str, Any]] = None
) -> float:
    """
    멀티에이전트 평가 결과를 종합하여 재생성 트리거 점수 계산 (0-100)
    
    Args:
        s5_result: S5 validation 결과
        agent_scores: 각 에이전트의 개별 평가 결과 (선택)
        
    Returns:
        float: 0-100 점수 (낮을수록 재생성 필요)
    """
    # 1. Blocking error 체크 (즉시 낮은 점수)
    if s5_result.get("s5_blocking_error") or s5_result.get("s5_card_image_blocking_error"):
        return 30.0  # 재생성 필요
    
    # 2. Technical Accuracy (0-50점)
    ta = s5_result.get("s5_technical_accuracy", 1.0)
    ta_score = ta * 50.0  # 0.0 → 0점, 0.5 → 25점, 1.0 → 50점
    
    # 3. Educational Quality (0-30점)
    eq = s5_result.get("s5_educational_quality", 5)
    eq_score = (eq / 5.0) * 30.0  # 1 → 6점, 3 → 18점, 5 → 30점
    
    # 4. Image Quality (0-20점) - 이미지가 있는 경우만
    has_image = bool(s5_result.get("s5_card_image_quality"))
    if has_image:
        img_quality = s5_result.get("s5_card_image_quality", 5)
        img_score = (img_quality / 5.0) * 20.0  # 1 → 4점, 3 → 12점, 5 → 20점
    else:
        img_score = 20.0  # 이미지 없으면 만점
    
    # 5. 종합 점수
    total_score = ta_score + eq_score + img_score  # 최대 100점
    
    return round(total_score, 2)
```

### 4.2 고급 계산 방식 (향후 확장)

멀티에이전트 시스템이 완전히 구축되면, 각 에이전트의 평가를 종합:

```python
def calculate_multi_agent_score(
    agent1_score: float,  # Technical Accuracy (0-50)
    agent2_score: float,  # Educational Quality (0-30)
    agent3_score: Optional[float],  # Image Quality (0-20, optional)
    meta_reviewer_weight: float = 1.0
) -> float:
    """
    여러 에이전트의 평가를 종합하여 최종 점수 계산
    """
    base_score = agent1_score + agent2_score + (agent3_score or 20.0)
    
    # Meta-reviewer가 점수 조정 (향후 구현)
    adjusted_score = base_score * meta_reviewer_weight
    
    return min(100.0, max(0.0, adjusted_score))
```

---

## 5. 재생성 트리거 로직

### 5.1 기본 임계값

```python
REGENERATION_THRESHOLD = 70.0  # 기본값

def should_trigger_regeneration(score: float, threshold: float = REGENERATION_THRESHOLD) -> bool:
    """
    재생성 트리거 여부 결정
    
    Args:
        score: 계산된 점수 (0-100)
        threshold: 임계값 (기본값: 70.0)
        
    Returns:
        bool: True면 재생성 필요
    """
    return score < threshold
```

### 5.2 재생성 프로세스

재생성이 트리거되면:

1. **프롬프트 수정**: S5 validation 결과와 개선 제안을 바탕으로 프롬프트 수정
2. **콘텐츠 재생성**: S2 (카드 생성) 단계를 다시 실행
3. **결과 저장**: 재생성된 콘텐츠를 S5 테이블에 저장

**구현 위치**: `3_Code/src/tools/multi_agent/regeneration_engine.py` (새로 생성)

---

## 6. 구현 단계

### Phase 1: 기본 점수 계산 (MVP)

**목표**: S5 validation 결과를 기반으로 점수 계산 및 재생성 트리거

**작업 내용:**
1. `3_Code/src/tools/multi_agent/` 디렉토리 생성
2. `score_calculator.py` 구현
   - `calculate_regeneration_trigger_score()` 함수
   - 기본 계산 방식 (Section 4.1)
3. `3_Code/src/tools/final_qa/export_appsheet_tables.py` 수정
   - S5 validation 결과를 받아서 점수 계산
   - `s5_regeneration_trigger_score` 컬럼에 값 저장

**예상 소요 시간**: 1-2일

---

### Phase 2: 멀티에이전트 평가 (Full Implementation)

**목표**: 여러 전문가 에이전트를 활용한 평가

**작업 내용:**
1. `agent_technical_accuracy.py` 구현
   - Technical Accuracy 전문가 에이전트
2. `agent_educational_quality.py` 구현
   - Educational Quality 전문가 에이전트
3. `agent_image_quality.py` 구현
   - Image Quality 전문가 에이전트 (조건부)
4. `agent_meta_reviewer.py` 구현
   - Meta-Reviewer (점수 종합)
5. `multi_agent_orchestrator.py` 구현
   - 에이전트들을 조율하는 메인 오케스트레이터

**예상 소요 시간**: 1-2주

---

### Phase 3: 재생성 엔진 (Advanced)

**목표**: 자동 콘텐츠 재생성

**작업 내용:**
1. `regeneration_engine.py` 구현
   - 프롬프트 수정 로직
   - S2 재실행 통합
   - 재생성된 콘텐츠 저장
2. `improvement_suggester.py` 구현
   - 개선 제안 생성

**예상 소요 시간**: 1주

---

## 7. 통합 포인트

### 7.1 S5 Validator와의 통합

**현재**: `3_Code/src/05_s5_validator.py`가 S5 validation 수행

**통합 방법:**
```python
# 05_s5_validator.py의 출력을 멀티에이전트 시스템으로 전달
s5_result = validate_card(card_data)
multi_agent_score = calculate_regeneration_trigger_score(s5_result)
```

### 7.2 export_appsheet_tables.py와의 통합

**현재**: `3_Code/src/tools/final_qa/export_appsheet_tables.py`가 S5 테이블을 CSV로 출력

**수정 사항:**
```python
# S5 validation 결과를 읽어서 점수 계산
for s5_row in s5_data:
    trigger_score = calculate_regeneration_trigger_score(s5_row)
    s5_row["s5_regeneration_trigger_score"] = trigger_score
    s5_row["s5_regeneration_triggered"] = trigger_score < 70.0
```

### 7.3 AppSheet와의 통합

**데이터 흐름:**
1. 멀티에이전트 시스템이 점수 계산
2. `export_appsheet_tables.py`가 S5.csv에 점수 저장
3. AppSheet가 S5.csv를 읽어서 표시
4. S5 Final Assessment에서 인간 평가자가 점수 확인

---

## 8. LLM 프롬프트 설계

### 8.1 Agent 1: Technical Accuracy Expert

**시스템 프롬프트:**
```
You are a medical education expert specializing in technical accuracy evaluation.
Your role is to assess the factual correctness and clinical validity of Anki cards.
```

**사용자 프롬프트:**
```
Evaluate the technical accuracy of this Anki card:

Front: {front}
Back: {back}

S5 Validation Results:
- Blocking Error: {s5_blocking_error}
- Technical Accuracy: {s5_technical_accuracy}

Provide:
1. Technical Accuracy Score (0.0, 0.5, or 1.0)
2. Reasoning for your score
3. Specific issues found (if any)
```

### 8.2 Agent 2: Educational Quality Expert

**시스템 프롬프트:**
```
You are a medical education expert specializing in educational quality evaluation.
Your role is to assess the pedagogical value and exam relevance of Anki cards.
```

**사용자 프롬프트:**
```
Evaluate the educational quality of this Anki card:

Front: {front}
Back: {back}
Learning Objective: {objective}

S5 Validation Results:
- Educational Quality: {s5_educational_quality}

Provide:
1. Educational Quality Score (1-5 Likert)
2. Reasoning for your score
3. Suggestions for improvement (if score < 4)
```

### 8.3 Agent 3: Image Quality Expert

**시스템 프롬프트:**
```
You are a medical imaging expert specializing in image quality evaluation.
Your role is to assess the anatomical accuracy, prompt compliance, and educational value of medical images.
```

**사용자 프롬프트:**
```
Evaluate the image quality of this Anki card:

Image: {image_path}
Image Prompt: {image_prompt}
Card Text: {front}, {back}

S5 Validation Results:
- Image Blocking Error: {s5_card_image_blocking_error}
- Anatomical Accuracy: {s5_card_image_anatomical_accuracy}
- Image Quality: {s5_card_image_quality}

Provide:
1. Image Quality Score (1-5 Likert)
2. Reasoning for your score
3. Specific issues found (if any)
```

### 8.4 Agent 4: Meta-Reviewer

**시스템 프롬프트:**
```
You are a meta-reviewer that aggregates evaluations from multiple expert agents.
Your role is to calculate a final composite score and determine if content regeneration is needed.
```

**사용자 프롬프트:**
```
Aggregate the following agent evaluations:

Agent 1 (Technical Accuracy): {agent1_score} - {agent1_reasoning}
Agent 2 (Educational Quality): {agent2_score} - {agent2_reasoning}
Agent 3 (Image Quality): {agent3_score} - {agent3_reasoning} (if applicable)

Provide:
1. Final Composite Score (0-100)
2. Regeneration Recommendation (Yes/No, threshold: 70)
3. Improvement Suggestions (if regeneration needed)
```

---

## 9. 테스트 및 검증

### 9.1 단위 테스트

**테스트 파일**: `3_Code/tests/test_multi_agent_score_calculator.py`

```python
def test_calculate_score_high_quality():
    """높은 품질 카드의 점수 계산 테스트"""
    s5_result = {
        "s5_blocking_error": False,
        "s5_technical_accuracy": 1.0,
        "s5_educational_quality": 5,
        "s5_card_image_quality": 5
    }
    score = calculate_regeneration_trigger_score(s5_result)
    assert score >= 90.0  # 높은 점수 기대

def test_calculate_score_blocking_error():
    """Blocking error가 있는 카드의 점수 계산 테스트"""
    s5_result = {
        "s5_blocking_error": True,
        "s5_technical_accuracy": 1.0,
        "s5_educational_quality": 5
    }
    score = calculate_regeneration_trigger_score(s5_result)
    assert score == 30.0  # 낮은 점수 기대

def test_calculate_score_low_quality():
    """낮은 품질 카드의 점수 계산 테스트"""
    s5_result = {
        "s5_blocking_error": False,
        "s5_technical_accuracy": 0.5,
        "s5_educational_quality": 2
    }
    score = calculate_regeneration_trigger_score(s5_result)
    assert score < 70.0  # 재생성 트리거 기대
```

### 9.2 통합 테스트

**테스트 시나리오:**
1. S5 validation 결과 샘플 생성
2. 멀티에이전트 시스템 실행
3. 점수 계산 및 재생성 트리거 확인
4. `export_appsheet_tables.py`로 CSV 출력 확인

### 9.3 검증 방법

**수동 검증:**
- 샘플 카드 10-20개에 대해 점수 계산
- 전문가가 점수를 검토하여 타당성 확인
- 재생성 트리거된 카드의 점수가 실제로 낮은지 확인

---

## 10. 환경 설정

### 10.1 필요한 패키지

```python
# requirements.txt에 추가
# (기존 패키지들은 01_generate_json.py와 동일)
```

### 10.2 환경 변수

```bash
# .env 파일에 추가 (선택)
MULTI_AGENT_TEMPERATURE=0.2
MULTI_AGENT_REGENERATION_THRESHOLD=70.0
MULTI_AGENT_MODEL=gemini-3-pro-preview
```

---

## 11. 파일 구조

```
3_Code/src/tools/multi_agent/
├── __init__.py
├── score_calculator.py          # 점수 계산 로직
├── agent_technical_accuracy.py  # Agent 1
├── agent_educational_quality.py # Agent 2
├── agent_image_quality.py       # Agent 3
├── agent_meta_reviewer.py       # Agent 4
├── multi_agent_orchestrator.py  # 메인 오케스트레이터
├── regeneration_engine.py      # 재생성 엔진 (Phase 3)
└── improvement_suggester.py     # 개선 제안 생성 (Phase 3)

3_Code/tests/
└── test_multi_agent_score_calculator.py
```

---

## 12. 참고 자료

### 12.1 관련 문서
- `AppSheet_S5_Final_Assessment_Design.md` - S5 Final Assessment 설계
- `AppSheet_Regeneration_Trigger_Score_Calculation.md` - 점수 계산 방법
- `AppSheet_QA_System_Specification.md` - 전체 시스템 스펙
- `QA_Metric_Definitions.md` - 평가 지표 정의

### 12.2 관련 코드
- `3_Code/src/05_s5_validator.py` - S5 validation 로직
- `3_Code/src/tools/final_qa/export_appsheet_tables.py` - AppSheet 테이블 출력
- `3_Code/src/01_generate_json.py` - LLM 호출 인프라

---

## 13. FAQ

### Q1: 멀티에이전트 시스템이 없어도 동작하나요?
**A**: Phase 1에서는 S5 validation 결과만으로 점수 계산이 가능합니다. 멀티에이전트 평가는 Phase 2에서 추가됩니다.

### Q2: 재생성은 언제 구현하나요?
**A**: Phase 3에서 구현 예정입니다. Phase 1-2에서는 점수 계산과 트리거 판단만 수행합니다.

### Q3: 점수 계산 방식을 변경하려면?
**A**: `score_calculator.py`의 `calculate_regeneration_trigger_score()` 함수를 수정하면 됩니다.

### Q4: 임계값을 조정하려면?
**A**: `REGENERATION_THRESHOLD` 상수를 변경하거나, `generate_assignments.py`의 `--s5_trigger_score_lt` 파라미터를 사용하세요.

---

## 14. 연락처 및 지원

**문의 사항:**
- 시스템 설계: `AppSheet_S5_Final_Assessment_Design.md` 참고
- 점수 계산: `AppSheet_Regeneration_Trigger_Score_Calculation.md` 참고
- 전체 시스템: `AppSheet_QA_System_Specification.md` 참고

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-01-01  
**작성자**: MeducAI Development Team


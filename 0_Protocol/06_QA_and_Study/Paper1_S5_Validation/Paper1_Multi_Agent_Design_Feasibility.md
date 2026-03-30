# Multi-Agent 설계 가능성 분석 (프로그래머 도움 없이)

**질문**: 프로그래머 도움 없이 옵션 C (피드백 루프) Multi-Agent 시스템을 설계할 수 있는가?

---

## 1. 현재 파이프라인 구조 분석

### 1.1 프롬프트 기반 제어

**현재 구조:**
- S1, S2는 **프롬프트로 완전히 제어**됨
- 프롬프트 파일 위치: `3_Code/prompt/`
- 프롬프트는 템플릿 변수 사용: `{entity_name}`, `{cards_for_entity_exact}` 등
- 사용자가 직접 프롬프트 파일 수정 가능

**프롬프트 레지스트리:**
- `_registry.json`에 프롬프트 파일 매핑
- 새 프롬프트 파일 추가 시 레지스트리 업데이트 필요

---

## 2. 프로그래머 도움 없이 가능한 부분

### 2.1 ✅ 프롬프트 설계 (완전히 가능)

#### A. 검토 LLM용 프롬프트 작성

**새 프롬프트 파일 생성:**
- `S2_REVIEW_SYSTEM__v1.md` (검토 LLM 시스템 프롬프트)
- `S2_REVIEW_USER__v1.md` (검토 LLM 사용자 프롬프트)

**역할:**
- S2 생성 결과를 평가
- 피드백 생성 (JSON 형식)
- 품질 점수 제공

**예시 구조:**
```markdown
# S2_REVIEW_SYSTEM__v1.md

ROLE: Quality Reviewer for Generated Anki Cards

TASK:
Review the generated Anki cards and provide structured feedback.

OUTPUT FORMAT:
{{
  "quality_score": 0.0-1.0,
  "blocking_errors": ["error1", "error2"],
  "suggestions": ["suggestion1", "suggestion2"],
  "revision_needed": true/false
}}
```

#### B. S2 프롬프트에 피드백 반영 로직 추가

**S2_USER_ENTITY 프롬프트 수정:**
- 피드백 섹션 추가
- 재생성 지시 추가

**예시 추가 내용:**
```markdown
# S2_USER_ENTITY__v8.md (수정 버전)

[기존 내용...]

FEEDBACK CONTEXT (OPTIONAL):
{previous_feedback}

REVISION INSTRUCTIONS:
- If previous_feedback is provided, incorporate the feedback into your generation.
- Address blocking_errors first.
- Apply suggestions where appropriate.
- Maintain exact card count: {cards_for_entity_exact}
```

#### C. 피드백 형식 정의

**JSON 스키마 설계:**
- 피드백 구조 정의
- 품질 점수 기준 정의
- 재생성 조건 정의

---

### 2.2 ⚠️ 부분적으로 가능한 부분

#### A. 프롬프트 레지스트리 업데이트

**필요 작업:**
- `_registry.json`에 새 프롬프트 추가
- 형식: `"S2_REVIEW_SYSTEM": "S2_REVIEW_SYSTEM__v1.md"`

**난이도:** 낮음 (JSON 파일 수정)

---

## 3. 프로그래머 도움이 필요한 부분

### 3.1 ❌ 코드 수정 (필수)

#### A. 피드백 루프 로직 구현

**필요한 코드 변경:**
```python
# 01_generate_json.py 수정 필요

# 현재 구조:
for entity in entities:
    cards = generate_cards(entity)  # S2 호출
    save_cards(cards)

# 피드백 루프 구조:
for entity in entities:
    max_iterations = 3
    iteration = 0
    cards = None
    feedback = None
    
    while iteration < max_iterations:
        if iteration == 0:
            cards = generate_cards(entity)  # 초기 생성
        else:
            cards = regenerate_cards(entity, feedback)  # 피드백 반영 재생성
        
        feedback = review_cards(cards)  # 검토 LLM 호출
        
        if not feedback['revision_needed']:
            break  # 만족스러우면 종료
        
        iteration += 1
    
    save_cards(cards)
```

**필요 작업:**
1. 검토 LLM 호출 함수 추가
2. 피드백 파싱 로직
3. 반복 제어 로직
4. S2 프롬프트에 피드백 전달

---

#### B. 프롬프트 로딩 및 전달

**필요한 코드 변경:**
```python
# 프롬프트 번들에 검토 프롬프트 추가
bundle = load_prompt_bundle(...)
P_REVIEW_SYS = bundle["prompts"]["S2_REVIEW_SYSTEM"]
P_REVIEW_USER = bundle["prompts"]["S2_REVIEW_USER"]

# 피드백 생성
feedback_json = call_llm(
    system_prompt=P_REVIEW_SYS,
    user_prompt=format_review_prompt(cards),
    ...
)

# S2 재생성 시 피드백 전달
s2_user = safe_prompt_format(
    P_S2_USER_T,
    entity_name=entity_name,
    previous_feedback=format_feedback(feedback_json),  # 새 변수
    ...
)
```

---

#### C. 반복 제어 및 종료 조건

**필요한 로직:**
- 최대 반복 횟수 설정
- 종료 조건 판단 (품질 점수, blocking error 없음)
- 타임아웃 처리

---

## 4. 실현 가능성 평가

### 4.1 프롬프트만으로 가능한 범위

**✅ 완전히 가능:**
1. 검토 LLM 프롬프트 설계
2. 피드백 형식 정의
3. S2 프롬프트에 피드백 반영 지시 추가
4. 프롬프트 레지스트리 업데이트

**⚠️ 부분적으로 가능:**
- 프롬프트에 반복 조건 명시 가능
- 하지만 실제 루프 실행은 코드 필요

---

### 4.2 코드 수정이 필요한 범위

**❌ 필수:**
1. 피드백 루프 구현 (while/for 루프)
2. 검토 LLM 호출 함수
3. 피드백 파싱 및 전달
4. 반복 제어 로직

**예상 코드 변경량:**
- `01_generate_json.py`: 약 50-100줄 추가/수정
- 프롬프트 로딩 부분: 약 10-20줄 수정

---

## 5. 대안: 프롬프트만으로 부분 구현

### 5.1 옵션: 수동 피드백 루프

**프로그래머 도움 없이 가능한 접근:**

1. **1단계**: S2로 초기 생성
2. **2단계**: 검토 LLM으로 피드백 생성 (별도 실행)
3. **3단계**: S2 프롬프트에 피드백 포함하여 수동 재생성

**장점:**
- 코드 수정 불필요
- 프롬프트만으로 구현 가능

**단점:**
- 자동화되지 않음
- 반복 작업 필요
- Multi-Agent의 "동적 상호작용" 특성 약함

---

### 5.2 옵션: Cursor Agent 활용

**프로그래머 대신 Cursor Agent 사용:**

1. 프롬프트 설계 완료
2. Cursor Agent에게 구현 요청:
   ```
   Context:
   @3_Code/src/01_generate_json.py
   @3_Code/prompt/_registry.json
   @3_Code/prompt/S2_REVIEW_SYSTEM__v1.md
   
   Task:
   Implement feedback loop between S2 generation and review LLM.
   - Add review LLM call after S2 generation
   - Parse feedback JSON
   - Regenerate cards with feedback if revision_needed=true
   - Maximum 3 iterations
   ```

**장점:**
- 프로그래머 직접 코딩 불필요
- 프롬프트 설계 후 자동 구현 가능

**단점:**
- Cursor Agent의 구현 품질 의존
- 검증 및 테스트 필요

---

## 6. 결론 및 권장사항

### 6.1 프로그래머 도움 없이 가능한 범위

**✅ 가능:**
- **프롬프트 설계**: 100% 가능
  - 검토 LLM 프롬프트 작성
  - S2 프롬프트에 피드백 반영 로직 추가
  - 피드백 형식 정의
- **프롬프트 레지스트리 업데이트**: 가능 (JSON 수정)

**❌ 불가능:**
- **코드 수정**: 필수
  - 피드백 루프 구현
  - 검토 LLM 호출
  - 피드백 파싱 및 전달

---

### 6.2 최소 요구사항

**프로그래머 도움 없이 완전한 Multi-Agent 구현:**
- ❌ **불가능** (코드 수정 필수)

**프로그래머 도움 없이 설계 및 부분 구현:**
- ✅ **가능** (프롬프트 설계 + Cursor Agent 활용)

---

### 6.3 권장 접근 방법

#### 방법 1: 프롬프트 설계 + Cursor Agent (권장)

**단계:**
1. ✅ 검토 LLM 프롬프트 설계 (프로그래머 도움 없이)
2. ✅ S2 프롬프트에 피드백 반영 로직 추가 (프로그래머 도움 없이)
3. ✅ 피드백 형식 정의 (프로그래머 도움 없이)
4. ⚠️ Cursor Agent에게 코드 구현 요청
5. ✅ 검증 및 테스트

**예상 시간:**
- 프롬프트 설계: 2-4시간
- Cursor Agent 구현: 1-2시간
- 검증: 1-2시간
- **총: 4-8시간**

---

#### 방법 2: 수동 피드백 루프 (프로토타입)

**단계:**
1. ✅ 검토 LLM 프롬프트 설계
2. ✅ S2 프롬프트에 피드백 반영 로직 추가
3. ✅ 수동으로 피드백 루프 실행
   - S2 생성 → 검토 LLM 실행 → S2 재생성 (수동)

**장점:**
- 코드 수정 전혀 불필요
- 즉시 테스트 가능

**단점:**
- 자동화되지 않음
- Multi-Agent의 "자동 상호작용" 특성 부족

---

## 7. 실용적 권장사항

### 7.1 단계별 접근

**Phase 1: 프롬프트 설계 (프로그래머 도움 없이)**
- 검토 LLM 프롬프트 작성
- S2 프롬프트 수정
- 피드백 형식 정의
- **예상 시간: 2-4시간**

**Phase 2: 프로토타입 테스트 (수동)**
- 수동 피드백 루프로 테스트
- 피드백 품질 검증
- **예상 시간: 1-2시간**

**Phase 3: 자동화 (Cursor Agent 또는 프로그래머)**
- 피드백 루프 코드 구현
- 자동화 테스트
- **예상 시간: 2-4시간**

---

### 7.2 최종 답변

**질문: 프로그래머 도움 없이 옵션 C 설계 가능한가?**

**답변:**
- **프롬프트 설계**: ✅ **완전히 가능**
- **전체 구현**: ⚠️ **Cursor Agent 활용 시 가능**
- **프로그래머 직접 코딩 없이**: ✅ **가능 (Cursor Agent 사용)**

**권장:**
1. 프롬프트 설계 먼저 완료 (프로그래머 도움 없이)
2. Cursor Agent에게 구현 요청
3. 검증 및 테스트

---

**작성일**: 2025-12-20  
**목적**: Multi-Agent 설계 가능성 명확화


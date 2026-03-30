# Yaacoub 2025 연구 기반 프롬프트 개선 실행 계획

**Status:** Archived
**Superseded by:** `0_Protocol/00_Governance/supporting/Prompt_governance/Prompt_Engineering_and_Cognitive_Alignment.md`
**Do not use this file for new decisions or execution.**


**Status:** Implementation Plan  
**Source:** Yaacoub et al. (2025) Lightweight Prompt Engineering for Cognitive Alignment  
**Date:** 2025-12-26  
**Purpose:** 논문 연구 결과를 MeducAI S2 프롬프트에 즉시 적용 가능한 구체적 개선 사항 정의

---

## 1. 핵심 적용 원칙

### 1.1 논문의 핵심 교훈
> **"명시적이고 상세한 프롬프트가 정확한 인지적 정렬(cognitive alignment)을 위한 필수 요소"**

### 1.2 MeducAI 적용 범위
- **주 적용 대상**: S2 (Entity-level) 프롬프트
  - S2가 질문 생성 단계이므로 인지적 정렬이 가장 중요
  - Q1/Q2/Q3 카드 타입별 목표 인지 수준 명시 필요
- **보조 적용 대상**: S1 (Group-level) 프롬프트
  - Master Table의 시험포인트에 인지 수준 고려

---

## 2. S2 프롬프트 개선 사항

### 2.1 현재 상태 분석

#### 현재 S2_SYSTEM__v7.md의 카드 역할 정의:
```
CARD ROLE AND IMAGE HINT RULES:
- Each card MUST have a card_role: Q1, Q2, or Q3.
- Q1 (BASIC, image-on-front): image_hint is REQUIRED.
- Q2 (MCQ, image-on-back): image_hint is OPTIONAL.
- Q3 (MCQ, no-image): image_hint is FORBIDDEN.
```

**문제점:**
- ❌ 각 카드 타입의 **목표 인지 수준**이 명시되지 않음
- ❌ 각 카드 타입에서 **금지되어야 할 인지적 복잡도**가 명시되지 않음
- ❌ 인지 수준 위반 사례가 제공되지 않음

### 2.2 개선 제안: 인지 수준 명시적 정의 추가

#### 제안 1: CARD ROLE 섹션에 인지 수준 명시 추가

**현재 구조를 다음과 같이 확장:**

```markdown
CARD ROLE, COGNITIVE ALIGNMENT, AND IMAGE HINT RULES (HARD):

Each card MUST have a card_role: Q1, Q2, or Q3.

────────────────────────
Q1 (BASIC, image-on-front)
────────────────────────
Cognitive Level Target: KNOWLEDGE (Bloom's Taxonomy Level 1)

Purpose:
- Direct recall of facts, definitions, structures, and basic associations
- Recognition and identification without complex reasoning

Expected Behavior:
- Questions that can be answered by direct recall
- "What is...?", "Define...", "Identify..." type questions
- Simple factual associations: "X is characterized by Y"

Forbidden Cognitive Operations:
- ❌ Application to new contexts (move to Q2)
- ❌ Analysis, comparison, or differentiation (move to Q3)
- ❌ Multi-step reasoning or synthesis
- ❌ Evaluation or judgment

Image Requirement:
- image_hint is REQUIRED
- Image should directly illustrate the fact/definition being tested

Examples of APPROPRIATE Q1:
- "이 영상에서 화살표가 가리키는 구조는?" (direct identification)
- "Osteosarcoma의 정의는?" (factual recall)
- "T1-weighted MRI에서 지방의 신호 강도는?" (factual knowledge)

Examples of INAPPROPRIATE Q1 (too complex):
- "이 영상 소견의 감별 진단은?" (requires Analysis → should be Q3)
- "이 병변에서 예상되는 임상 증상은?" (requires Application → should be Q2)
- "이 소견이 다른 질환과 구별되는 핵심 특징은?" (requires Analysis → should be Q3)

────────────────────────
Q2 (MCQ, image-on-back)
────────────────────────
Cognitive Level Target: APPLICATION (Bloom's Taxonomy Level 3)

Purpose:
- Apply knowledge to specific imaging findings
- Recognize patterns in clinical context
- Connect imaging features to diagnostic concepts

Expected Behavior:
- Questions requiring pattern recognition in imaging context
- "What is the most likely diagnosis?" (applying knowledge to image)
- "Which finding is most consistent with...?" (contextual application)
- Questions that connect image features to clinical concepts

Forbidden Cognitive Operations:
- ❌ Pure recall without context (too simple → should be Q1)
- ❌ Complex multi-factor analysis or differentiation (too complex → should be Q3)
- ❌ Synthesis of multiple unrelated concepts
- ❌ Evaluation requiring expert judgment

Image Requirement:
- image_hint is OPTIONAL (Q2 reuses Q1 image, so hint is for metadata consistency)

Examples of APPROPRIATE Q2:
- "이 영상 소견에서 가장 가능성 높은 진단은?" (pattern recognition + application)
- "이 환자의 임상 정보와 영상 소견을 고려할 때 다음 중 적절한 것은?" (contextual application)
- "이 패턴을 보이는 질환은?" (applying knowledge to pattern)

Examples of INAPPROPRIATE Q2:
- "이 구조의 이름은?" (too simple, Knowledge level → should be Q1)
- "이 5가지 질환을 확률 순으로 나열하면?" (too complex, Analysis level → should be Q3)
- "이 소견의 병인론적 기전은?" (requires Analysis → should be Q3)

────────────────────────
Q3 (MCQ, no-image)
────────────────────────
Cognitive Level Target: ANALYSIS or APPLICATION (Bloom's Taxonomy Level 4 or 3)

Purpose:
- Differentiate between diagnostic options
- Synthesize multiple factors (imaging + clinical + pathological)
- Apply clinical reasoning to complex scenarios

Expected Behavior:
- Questions requiring differentiation or comparison
- "Which finding distinguishes X from Y?" (analysis)
- "Given multiple findings, the most important is?" (synthesis)
- Questions combining imaging, clinical, and pathological information

Forbidden Cognitive Operations:
- ❌ Simple factual recall (too simple → should be Q1)
- ❌ Single-factor pattern recognition (too simple → should be Q2)
- ❌ Questions answerable without clinical reasoning

Image Requirement:
- image_hint is FORBIDDEN (must be null or absent)

Examples of APPROPRIATE Q3:
- "다음 중 이 소견을 가장 잘 설명하는 것은?" (requires differentiation)
- "이 병변의 병인, 영상 소견, 임상 증상을 종합할 때 가장 중요한 특징은?" (synthesis)
- "X와 Y를 감별하는 데 가장 유용한 영상 소견은?" (analysis)
- "다음 증례에서 가장 적절한 다음 검사는?" (clinical reasoning)

Examples of INAPPROPRIATE Q3:
- "이 구조의 정의는?" (too simple, Knowledge level → should be Q1)
- "이 영상에서 보이는 소견은?" (too simple, Application level → should be Q2)
```

#### 제안 2: 인지 수준 자체 점검 요청 추가

**S2_SYSTEM__v7.md에 다음 섹션 추가:**

```markdown
────────────────────────
COGNITIVE LEVEL SELF-VERIFICATION (INTERNAL CHECK)
────────────────────────

Before finalizing each card, perform the following internal verification:

FOR Q1 CARDS:
1. Can this question be answered by direct recall without context?
   - If NO → This is likely Q2 (requires context) or Q3 (requires analysis)
   - Adjust card_role or simplify the question

FOR Q2 CARDS:
1. Does this question require applying knowledge to a specific imaging context?
   - If NO and answerable by pure recall → This is Q1 level, adjust card_role
   - If NO and requires complex differentiation → This is Q3 level, adjust card_role

FOR Q3 CARDS:
1. Does this question require differentiating, analyzing, or synthesizing multiple factors?
   - If NO and answerable by recall → This is Q1 level, adjust card_role
   - If NO and requires only pattern recognition → This is Q2 level, adjust card_role

CRITICAL RULE:
- If a card's cognitive complexity does not match its card_role, you MUST either:
  (a) Adjust the card_role to match the actual cognitive level, OR
  (b) Simplify/complexify the question to match the intended card_role
- Do NOT generate cards where the cognitive level and card_role are misaligned
```

### 2.3 S2_USER 프롬프트 개선

**현재 S2_USER_ENTITY__v7.md의 구조 확인 필요**, 필요 시 다음 내용 추가:

```markdown
COGNITIVE ALIGNMENT REQUIREMENT:

When generating cards, ensure that:
- Q1 cards test KNOWLEDGE level (factual recall)
- Q2 cards test APPLICATION level (pattern recognition in context)
- Q3 cards test ANALYSIS level (differentiation, synthesis)

If a generated card does not align with its target cognitive level, regenerate it.
```

---

## 3. S1 프롬프트 개선 사항 (선택적)

### 3.1 Master Table 시험포인트 컬럼 개선

**현재 상태:**
- S1이 Master Table 생성 시 "시험포인트" 컬럼 포함
- 인지 수준에 대한 명시적 고려 부재

**개선 제안:**

```markdown
시험포인트 컬럼 작성 규칙 (ENHANCED):

각 Entity의 시험 포인트를 작성할 때, 목표 인지 수준을 고려하여 작성:

1. Knowledge-level 포인트:
   - "용어 정의", "해부학적 위치", "기본 개념"
   - 예: "Knowledge: 용어 정의 및 해부학적 위치"

2. Application-level 포인트:
   - "모달리티별 영상 소견 인식", "패턴 매칭", "소견-진단 연결"
   - 예: "Application: CT/MRI에서 특징적 소견 인식"

3. Analysis-level 포인트:
   - "감별 진단 기준", "차별화 포인트", "임상적 판단"
   - 예: "Analysis: 유사 질환과의 감별 진단 포인트"

참고: 시험포인트는 실제 시험에서 묻는 인지 수준을 반영하되, 
명시적으로 "[인지수준]:" 접두사를 붙이지 않아도 됩니다. 
다만 작성 시 인지 수준을 의식적으로 고려하여 작성하세요.
```

**주의:** S1 스키마가 이미 freeze되어 있으므로, 이 개선은 **프롬프트 텍스트 개선**으로만 적용 (스키마 변경 없음)

---

## 4. 구현 단계

### 4.1 Phase 1: S2 프롬프트 개선 (즉시 적용 가능)

**작업 내용:**
1. `S2_SYSTEM__v7.md`에 "CARD ROLE, COGNITIVE ALIGNMENT, AND IMAGE HINT RULES" 섹션 확장
2. Q1/Q2/Q3 각각에 대해:
   - Cognitive Level Target 명시
   - Expected Behavior 설명
   - Forbidden Cognitive Operations 명시
   - Appropriate/Inappropriate 예시 제공
3. "COGNITIVE LEVEL SELF-VERIFICATION" 섹션 추가

**예상 효과:**
- 각 카드 타입의 목표 인지 수준이 명확해져 정렬률 향상
- 인지 수준 위반 카드 생성 감소
- QA 시간 단축 (사전 필터링)

**검증 방법:**
- 개선 전/후 S2 출력 샘플 비교
- QA 리뷰어의 인지 수준 정렬 평가
- 카드 타입별 인지 수준 위반률 측정

### 4.2 Phase 2: 평가 메커니즘 도입 (중기)

**작업 내용:**
1. Bloom's Taxonomy 자동 분류 모델 도입 (DistilBERT 기반 또는 유사)
2. S2 출력 카드에 대해 자동 인지 수준 분류 수행
3. 목표 레벨(Q1→Knowledge, Q2→Application, Q3→Analysis)과의 정렬률 측정
4. QA 프로세스에 인지 수준 정렬 평가 추가

**예상 효과:**
- 프롬프트 개선 효과를 정량적으로 측정
- 인지 수준 위반 카드 자동 검출
- 프롬프트 반복 개선 사이클 구축

### 4.3 Phase 3: 고급 기법 실험 (장기)

**작업 내용:**
1. Few-shot learning: 인지 수준별 예시를 프롬프트에 포함
2. Chain-of-thought prompting: 복잡한 인지 수준 정렬 향상
3. 프롬프트 변형 A/B 테스트 인프라 구축

---

## 5. 예상 리스크 및 대응 방안

### 5.1 리스크 1: 프롬프트 길이 증가로 인한 토큰 비용 증가

**대응:**
- 핵심 섹션만 확장 (CARD ROLE 섹션)
- 예시는 간결하게 유지
- 불필요한 중복 제거

### 5.2 리스크 2: 과도한 제약으로 인한 카드 다양성 감소

**대응:**
- "Forbidden" 규칙은 명시하되, "Must" 규칙은 최소화
- 예시는 가이드라인으로 제공, 강제 사항 아님
- QA 결과 모니터링하여 필요시 조정

### 5.3 리스크 3: LLM 모델별 차이 (Gemini vs GPT 등)

**대응:**
- 논문은 Gemini 2.0 Flash Lite 기준이지만, 원칙은 범용적
- 각 모델별로 프롬프트 효과 검증 필요
- 모델별 최적화는 별도 실험으로 진행

---

## 6. 성공 지표

### 6.1 정량적 지표
- **인지 수준 정렬률**: 자동 분류 모델 기준 목표 레벨과의 일치율
- **QA 통과율**: 인지 수준 관련 QA 실패 감소율
- **인간 평가 점수**: 리뷰어의 인지 수준 정렬 평가 점수

### 6.2 정성적 지표
- QA 리뷰어 피드백: "이 카드는 Q1인데 너무 복잡함" 같은 피드백 감소
- 프롬프트 명확성: 프롬프트만 봐도 각 카드 타입의 목표가 명확한지

---

## 7. 다음 단계

### 7.1 즉시 실행 가능 (Phase 1)
1. ✅ S2_SYSTEM__v7.md 개선안 작성
2. ⏳ 프롬프트 개선안 검토 및 승인
3. ⏳ S2_SYSTEM 프롬프트 파일 업데이트
4. ⏳ 테스트 실행 및 결과 검증

### 7.2 중기 계획 (Phase 2)
1. Bloom's Taxonomy 분류 모델 조사 및 도입 계획 수립
2. 평가 메커니즘 설계
3. QA 프로세스 통합

### 7.3 장기 계획 (Phase 3)
1. Few-shot learning 실험 설계
2. A/B 테스트 인프라 구축
3. 다양한 프롬프트 전략 비교 연구

---

## 8. 참고 자료

- **원본 논문**: Yaacoub_2025_Lightweight_Prompt_Engineering_Review.md
- **현재 프롬프트**: 
  - `3_Code/prompt/S2_SYSTEM__v7.md`
  - `3_Code/prompt/S2_USER_ENTITY__v7.md`
- **프롬프트 개선 가이드**: `0_Protocol/00_Governance/supporting/Prompt_governance/S2_Prompt_Improvement_Guide.md`

# 논문 Method 섹션용: 프롬프트 엔지니어링 및 인지적 정렬 설계

**Status:** Archived  
**Superseded by:** `0_Protocol/00_Governance/supporting/Prompt_governance/Prompt_Engineering_and_Cognitive_Alignment.md`
**Do not use this file for new decisions or execution.**
**Purpose:** 논문 Methods 섹션에 포함할 프롬프트 엔지니어링 전략 및 인지적 정렬 설계 내용  
**Date:** 2025-12-26  
**Based on:** Yaacoub et al. (2025) Lightweight Prompt Engineering for Cognitive Alignment

---

## 1. 프롬프트 엔지니어링 전략 (Prompt Engineering Strategy)

### 1.1 설계 원칙

본 연구에서는 교육용 AI 생성 콘텐츠의 품질을 보장하기 위해 **명시적이고 구조화된 프롬프트 엔지니어링 전략**을 채택하였다. 이는 최근 연구(Yaacoub et al., 2025)에서 제시된 바와 같이, **명시적이고 상세한 프롬프트가 정확한 인지적 정렬(cognitive alignment)을 위한 필수 요소**임을 근거로 한다.

프롬프트 설계 시 다음 원칙을 준수하였다:

1. **명시적 인지 수준 정의**: 각 카드 타입에 대해 목표하는 Bloom's Taxonomy 인지 수준을 명시적으로 정의
2. **구조화된 제약 조건**: 예상되는 행동(Expected Behavior)과 금지 사항(Forbidden Operations)을 명확히 기술
3. **자체 검증 요청**: 생성된 콘텐츠가 의도한 인지 수준과 정렬되는지 자체 검증 요청 포함
4. **구체적 예시 제공**: 적절한 예시(Appropriate Examples)와 부적절한 예시(Inappropriate Examples)를 프롬프트에 포함

### 1.2 프롬프트 구조

각 단계(Step)별로 System Prompt와 User Prompt를 분리하여 구성하였다:

- **System Prompt**: 역할 정의, 제약 조건, 출력 형식, 일반적 규칙
- **User Prompt**: 구체적 입력 데이터, 작업 지시, 예시

이러한 분리는 프롬프트의 재사용성과 유지보수성을 높이며, 역할과 작업을 명확히 구분하는 데 기여한다.

---

## 2. 인지적 정렬을 위한 카드 타입별 설계 (Cognitive Alignment Design)

### 2.1 카드 타입 및 인지 수준 정의

본 연구는 2-card policy를 채택하였으며, 각 카드 타입은 다음과 같이 Bloom's Taxonomy에 기반하여 인지 수준을 명시적으로 정의하였다:

#### 2.1.1 Q1 카드 (진단형 질문)

- **카드 타입**: BASIC (short-answer)
- **목표 인지 수준**: APPLICATION (Bloom's Taxonomy Level 3)
- **설계 목적**: 영상 소견을 진단 개념에 적용하는 능력 평가
- **형식**: 
  - Front: "영상 요약" 섹션(모달리티, 뷰/시퀀스, 핵심 소견 기술) + "가장 가능성이 높은 진단은?" 질문
  - Back: 답변, 근거(2-4개 bullet), 함정/감별(1-2개 bullet)

**인지적 정렬 기준:**
- 영상 소견(imaging findings)을 진단(diagnosis)에 **적용(application)**하는 과정을 요구
- 단순 기억(Knowledge level)이 아닌, 패턴 인식과 맥락적 적용이 필요
- 복잡한 다단계 감별 진단(Analysis level)은 배제

**프롬프트 명시 사항:**
```
Expected Behavior:
- 영상 소견을 기술적으로 설명하고, 기술된 소견을 바탕으로 가장 가능성 높은 진단 요구
- 영상 소견과 진단 사이의 연결을 요구 (패턴 인식)

Forbidden Operations:
- 단순 용어 정의나 사실 회상 (too simple, Knowledge level)
- 복잡한 감별 진단 과정 (too complex, Analysis level)
- 병태생리학적 기전 질문 (conceptual, belongs to Q2)
```

#### 2.1.2 Q2 카드 (개념 이해 기반 MCQ)

- **카드 타입**: MCQ (multiple-choice question, 5 options)
- **목표 인지 수준**: APPLICATION or KNOWLEDGE (Bloom's Taxonomy Level 3 or 1)
- **설계 목적**: 병태생리학적 원리, 치료 원칙, 적응증/금기증, 물리 원리 등 개념적 이해 평가
- **형식**:
  - Front: 개념 질문 (텍스트만으로 해결 가능, 영상 의존 없음)
  - Back: 정답, 근거(2-4개 bullet), 오답 포인트(1-2개 bullet)

**인지적 정렬 기준:**
- 병태생리, 기전, 치료 원칙, 적응증/금기증 등 **개념적 이해**를 테스트
- 일부는 순수 지식(Knowledge)일 수 있으나, 대부분 개념을 특정 상황에 적용(Application)하는 수준
- 텍스트만으로 해결 가능해야 함 (영상 의존성 제거)

**프롬프트 명시 사항:**
```
Expected Behavior:
- 병태생리학적 원리, 치료 원칙, 적응증/금기증, 물리 원리 등을 묻는 MCQ
- 텍스트만으로 해결 가능 (영상 불필요)

Forbidden Operations:
- 영상 소견을 다시 묻는 진단형 질문 (Q1과 중복)
- 복잡한 다단계 추론이나 종합 (too complex, Analysis level)
- 영상에 의존하는 질문
```

### 2.2 인지 수준 자체 검증 (Self-Verification)

각 카드 생성 시, 프롬프트는 LLM에게 다음 자체 검증을 수행하도록 요청한다:

**Q1 카드 검증:**
1. 이 질문이 영상 소견을 진단 지식에 적용하는 것을 요구하는가? (APPLICATION level)
2. Front에 "영상 요약" 섹션이 포함되어 있는가? (모달리티/뷰/핵심 소견)
3. 단순 기억 수준(too simple) 또는 복잡한 감별 진단 수준(too complex)이 아닌가?

**Q2 카드 검증:**
1. 이 질문이 텍스트만으로 해결 가능한가? (영상 의존성 없음)
2. 이 질문이 개념적 이해를 테스트하는가? (진단 패턴 인식 아님)
3. Q1과 중복되지 않는가? (진단 질문 다시 묻지 않음)

인지 수준과 카드 역할이 정렬되지 않은 경우, LLM은 질문을 조정하거나 재생성하도록 지시받는다.

---

## 3. 프롬프트 구조화 방법 (Prompt Structuring Approach)

### 3.1 명시적 제약 조건 (Explicit Constraints)

프롬프트에는 다음과 같은 명시적 제약 조건이 포함된다:

1. **출력 형식 제약**: JSON 스키마 준수, 필수 필드 존재, 데이터 타입 규정
2. **인지 수준 제약**: 각 카드 타입별 목표 인지 수준, 금지된 인지적 연산
3. **범위 제약**: 상위 단계(S1)에서 정의된 개념 범위 내에서만 생성
4. **품질 제약**: 시험 지향, 간결성, 임상적 정확성

### 3.2 예시 기반 학습 (Example-Based Guidance)

프롬프트에 다음을 포함하여 LLM의 이해를 돕는다:

- **적절한 예시 (Appropriate Examples)**: 각 카드 타입에 맞는 올바른 형식의 예시
- **부적절한 예시 (Inappropriate Examples)**: 피해야 할 형식과 그 이유

이는 few-shot learning 접근법의 변형으로, 명시적 지시와 함께 예시를 제공하여 의도한 출력 형식을 명확히 한다.

### 3.3 단계별 역할 분리 (Role Separation by Stage)

각 단계(Step)별로 LLM의 역할을 명확히 정의하여 자율적 판단을 제한한다:

- **S1 (Step 1)**: 개념 구조 정의 (Group-level 구조화)
- **S2 (Step 2)**: 카드 생성 (Entity-level 실행, 결정 권한 없음)
- **S3 (Step 3)**: 카드 선택 및 정책 적용 (코드 기반)
- **S4 (Step 4)**: 이미지 생성 (S2의 image_hint 기반)

이러한 역할 분리는 LLM이 교육적 결정(예: 카드 수, 중요도 가중치)을 내리지 않도록 보장하며, 모든 결정은 사전 정의된 정책과 코드 로직에 의해 이루어진다.

---

## 4. 문헌 근거 및 방법론적 위치 (Methodological Positioning)

### 4.1 프롬프트 엔지니어링 문헌

본 연구의 프롬프트 엔지니어링 전략은 최근 연구 결과를 기반으로 한다. Yaacoub et al. (2025)는 교육용 AI에서 경량 프롬프트 엔지니어링 전략을 평가한 결과, **명시적이고 상세한 프롬프트가 정확한 인지적 정렬을 위한 필수 요소**임을 입증하였다. 이들의 연구는 3가지 프롬프트 전략(detailed baseline, simpler version, persona-based)을 비교한 결과, 상세한 기준선 프롬프트가 목표 Bloom's Taxonomy 레벨과 가장 높은 정렬률을 달성함을 보여주었다.

본 연구는 이러한 발견을 의학 교육 맥락에 적용하여, 각 카드 타입에 대해 명시적인 인지 수준 정의, 예상 행동, 금지 사항을 포함하는 구조화된 프롬프트를 설계하였다.

### 4.2 인지적 정렬 및 Bloom's Taxonomy

Bloom's Taxonomy는 교육 평가에서 널리 사용되는 인지 수준 분류 체계이다(Anderson & Krathwohl, 2001). 본 연구는 카드 타입별로 목표 인지 수준을 명시적으로 정의함으로써, 생성된 교육 콘텐츠가 의도한 학습 목표와 정렬되도록 보장한다.

- **Q1**: APPLICATION level (Level 3) - 영상 소견을 진단에 적용
- **Q2**: APPLICATION or KNOWLEDGE level (Level 3 or 1) - 개념 이해 또는 적용

이러한 명시적 정의는 AI 생성 콘텐츠의 교육적 품질을 보장하는 방법론적 기여로 볼 수 있다.

---

## 5. 논문 Methods 섹션 작성 가이드

### 5.1 포함할 섹션 구조 (제안)

논문 Methods 섹션에 다음 구조로 포함할 수 있다:

```markdown
## 2.3 Prompt Engineering and Cognitive Alignment

### 2.3.1 Prompt Design Principles

To ensure quality and cognitive alignment of AI-generated educational content, 
we adopted an explicit and structured prompt engineering strategy, based on 
recent findings that detailed prompts are essential for accurate cognitive 
alignment (Yaacoub et al., 2025). Our prompt design followed four key principles:
(1) explicit cognitive level definitions, (2) structured constraints, 
(3) self-verification requests, and (4) example-based guidance.

### 2.3.2 Card Type Design and Cognitive Levels

We implemented a 2-card policy, with each card type explicitly aligned to 
Bloom's Taxonomy cognitive levels:

**Q1 Cards (Diagnostic Questions)**:
- Type: BASIC (short-answer)
- Target Cognitive Level: APPLICATION (Bloom's Taxonomy Level 3)
- Purpose: Assess ability to apply imaging findings to diagnostic concepts
- Format: "Imaging Summary" section (modality, view/sequence, key findings) 
  + diagnostic question

**Q2 Cards (Conceptual MCQ)**:
- Type: MCQ (5 options)
- Target Cognitive Level: APPLICATION or KNOWLEDGE (Level 3 or 1)
- Purpose: Assess conceptual understanding (pathophysiology, mechanisms, 
  treatment principles, indications/contraindications)
- Format: Text-based concept question (solvable without images)

Each card type included explicit definitions of expected behaviors and 
forbidden cognitive operations to ensure alignment with target cognitive levels.

### 2.3.3 Self-Verification Mechanism

The prompts included self-verification instructions requiring the LLM to 
check cognitive alignment before finalizing each card:
- For Q1: Verify that the question requires applying imaging findings to 
  diagnostic knowledge (APPLICATION level)
- For Q2: Verify that the question is solvable from text alone and tests 
  conceptual understanding

If cognitive misalignment was detected, the LLM was instructed to regenerate 
the card.
```

### 5.2 통계/정량적 결과 포함 가능성

향후 평가 단계에서 다음 정량적 지표를 포함할 수 있다:

- **인지 수준 정렬률**: 자동 분류 모델(DistilBERT 또는 유사)을 사용하여 생성된 카드의 인지 수준을 분류하고, 목표 레벨과의 정렬률 측정
- **QA 통과율**: 인지 수준 관련 QA 실패 감소율
- **인간 평가 점수**: 전문가 리뷰어의 인지 수준 정렬 평가 점수

이러한 정량적 평가는 프롬프트 엔지니어링 전략의 효과를 입증하는 데 기여할 수 있다.

---

## 6. 참고 문헌 (References for Methods Section)

논문 Methods 섹션에 포함할 참고 문헌:

1. **Yaacoub, A., Da-Rugna, J., & Assaghir, Z. (2025)**. Lightweight Prompt Engineering for Cognitive Alignment in Educational AI: A OneClickQuiz Case Study. *36th Central European Conference on Information and Intelligent Systems (CECIIS 2025)*, Varazdin, Croatia. arXiv:2510.03374v1
   - 프롬프트 엔지니어링 전략의 효과성, 명시적 프롬프트의 중요성

2. **Anderson, L. W., & Krathwohl, D. R. (2001)**. A Taxonomy for Learning, Teaching, and Assessing: A Revision of Bloom's Taxonomy of Educational Objectives. Longman.
   - Bloom's Taxonomy 인지 수준 분류 체계

3. **Bloom, B. S. (1984)**. Taxonomy of Educational Objectives, Handbook 1: Cognitive Domain (2nd edition). Addison-Wesley Longman Ltd.
   - 원본 Bloom's Taxonomy

---

## 7. 논문 Methods 섹션 작성 체크리스트

- [ ] 프롬프트 엔지니어링 전략 설명 (설계 원칙 4가지)
- [ ] 각 카드 타입별 인지 수준 정의 (Q1: APPLICATION, Q2: APPLICATION/KNOWLEDGE)
- [ ] 카드 타입별 형식 및 목적 설명
- [ ] 인지 수준 자체 검증 메커니즘 설명
- [ ] 예시 기반 학습(few-shot) 접근법 언급
- [ ] 단계별 역할 분리 설명 (LLM의 자율적 판단 제한)
- [ ] Yaacoub et al. (2025) 연구 결과 인용 및 방법론적 근거
- [ ] 향후 평가 지표 (인지 수준 정렬률, QA 통과율 등) 언급 (Results 섹션에 포함될 경우)

---

## 8. 추가 고려사항

### 8.1 재현가능성 (Reproducibility)

Methods 섹션에 다음을 포함하여 재현가능성을 보장:

- 프롬프트 파일의 버전 정보
- 사용한 LLM 모델 및 버전
- 프롬프트의 주요 섹션 구조 설명 (상세한 전체 프롬프트는 Supplementary Material에 포함 가능)

### 8.2 윤리적 고려사항

- LLM의 자율적 판단 제한 (역할 분리)
- 교육적 결정 권한의 외부화 (코드 기반 정책)
- 명시적 제약 조건을 통한 편향 및 오류 감소

---

## 9. Methods 섹션 초안 (전체 통합 버전)

다음은 논문 Methods 섹션에 직접 포함할 수 있는 초안이다:

```markdown
### 2.3 Prompt Engineering for Cognitive Alignment

To ensure that AI-generated educational content aligns with intended learning 
objectives, we implemented a structured prompt engineering strategy based on 
recent evidence that explicit, detailed prompts are essential for accurate 
cognitive alignment (Yaacoub et al., 2025). Our approach incorporated four 
key principles: (1) explicit cognitive level definitions aligned to Bloom's 
Taxonomy, (2) structured constraints specifying expected behaviors and 
forbidden operations, (3) self-verification mechanisms requiring the LLM to 
verify cognitive alignment, and (4) example-based guidance providing both 
appropriate and inappropriate examples.

#### 2.3.1 Card Type Design and Cognitive Levels

We implemented a 2-card policy, with each card type explicitly aligned to 
target cognitive levels:

**Q1 Cards (Diagnostic Application)**:
- Format: BASIC (short-answer) with "Imaging Summary" section followed by 
  diagnostic question
- Target Cognitive Level: APPLICATION (Bloom's Taxonomy Level 3)
- Purpose: Assess ability to apply imaging findings (modality, view/sequence, 
  key findings) to diagnostic concepts
- Expected Behavior: Pattern recognition and contextual application of 
  imaging findings to diagnosis
- Forbidden Operations: Pure factual recall (too simple, Knowledge level), 
  complex multi-step differential diagnosis (too complex, Analysis level), 
  pathophysiological mechanism questions (conceptual, belongs to Q2)

**Q2 Cards (Conceptual Understanding)**:
- Format: MCQ with 5 options, text-based (solvable without images)
- Target Cognitive Level: APPLICATION or KNOWLEDGE (Bloom's Taxonomy Level 3 or 1)
- Purpose: Assess conceptual understanding including pathophysiology, 
  mechanisms, treatment principles, indications/contraindications, QC/physics 
  principles
- Expected Behavior: Application of conceptual knowledge to specific contexts, 
  or recall of stable conceptual knowledge
- Forbidden Operations: Diagnostic pattern recognition questions (Q1 territory), 
  complex multi-step analysis (too complex, Analysis level), image-dependent 
  questions

#### 2.3.2 Self-Verification Mechanism

To ensure cognitive alignment, the prompts included explicit self-verification 
instructions. For each card, the LLM was required to verify:
- Q1: Does this question require applying imaging findings to diagnostic 
  knowledge? (APPLICATION level)
- Q2: Is this question solvable from text alone and does it test conceptual 
  understanding? (not diagnostic pattern recognition)

If cognitive misalignment was detected, the LLM was instructed to regenerate 
the card with correct alignment.

#### 2.3.3 Prompt Structure and Constraints

Each stage (Step) employed separate System and User prompts:
- **System Prompt**: Role definition, constraints, output format, general rules
- **User Prompt**: Specific input data, task instructions, examples

Role boundaries were strictly defined to prevent LLMs from making educational 
decisions (e.g., card counts, importance weights), which were instead 
determined by predefined policies and code-level logic. This design aligns 
with calls for safer human-AI collaboration models in high-stakes educational 
applications.
```

---

이 내용은 논문 Methods 섹션에 포함할 수 있으며, 필요에 따라 연구의 특정 맥락에 맞게 조정할 수 있다.

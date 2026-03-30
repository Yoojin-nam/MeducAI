# Lightweight Prompt Engineering for Cognitive Alignment in Educational AI: 논문 정리 및 적용 방안

**Status:** Reference Document  
**Source:** Yaacoub, A., Da-Rugna, J., & Assaghir, Z. (2025). Lightweight Prompt Engineering for Cognitive Alignment in Educational AI: A OneClickQuiz Case Study. *36th Central European Conference on Information and Intelligent Systems (CECIIS 2025)*, Varazdin, Croatia.  
**Paper ID:** arXiv:2510.03374v1  
**Date Added:** 2025-12-26  
**Purpose:** 프롬프트 엔지니어링 전략이 교육용 AI의 인지적 정렬에 미치는 영향에 대한 연구 정리 및 MeducAI 프롬프트 개선에의 적용 방안

---

## 1. 논문 개요

### 1.1 연구 목적
OneClickQuiz (Moodle 플러그인)에서 생성형 AI를 활용한 퀴즈 생성 시, **경량 프롬프트 엔지니어링 전략**이 AI 생성 질문의 **인지적 정렬(cognitive alignment)**에 미치는 영향을 평가하는 연구.

### 1.2 연구 질문
> "경량 프롬프트 엔지니어링 기법(명시적, 간소화, 페르소나 기반)이 OneClickQuiz와 같은 실제 교육 애플리케이션에서 AI 생성 질문의 인지적 정렬과 인지된 품질에 어느 정도 영향을 미치는가?"

### 1.3 연구 맥락
- **이전 연구 기반**: DistilBERT 모델을 이용한 Bloom's Taxonomy 분류 시스템 개발 (Yaacoub et al., 2025)
- **연구 전환점**: 결과 평가(post-generation alignment)에서 **입력 메커니즘(프롬프트 엔지니어링)**으로 초점 이동
- **목표**: "Cognitive Alignment" 단계에서 프롬프트 변형이 출력 품질에 미치는 영향 정량화

---

## 2. 방법론

### 2.1 실험 설계
- **모델**: Gemini 2.0 Flash Lite
- **평가 프레임워크**: Bloom's Taxonomy (Knowledge, Application, Analysis 레벨)
- **평가 방법**: 
  - 자동 분류: DistilBERT 기반 분류 모델
  - 인간 검토: 명확성, 관련성, 주관적 인지적 정렬 평가

### 2.2 프롬프트 전략 비교

#### 2.2.1 Detailed Baseline (명시적, 상세한 프롬프트)
- **특징**: 명시적 지시사항, 상세한 제약 조건, 명확한 구조
- **목적**: 목표 인지 수준에 대한 정확한 정렬 달성

#### 2.2.2 Simpler Version (간소화된 프롬프트)
- **특징**: 간결한 설명, 최소한의 제약
- **목적**: 단순화가 정렬에 미치는 영향 평가

#### 2.2.3 Persona-Based Approach (페르소나 기반 프롬프트)
- **특징**: 특정 역할이나 페르소나를 부여 (예: "경험 많은 교사로서...")
- **목적**: 페르소나 기반 접근법의 효과성 평가

---

## 3. 주요 발견 (Findings)

### 3.1 핵심 발견
> **"명시적이고 상세한 프롬프트가 정확한 인지적 정렬을 위한 필수 요소"**

### 3.2 정량적 결과
- **Detailed Baseline**: 목표 Bloom's Taxonomy 레벨과 가장 높은 정렬률 달성
- **Simpler Version**: 명확하고 관련성 있는 질문 생성 가능하나, **목표 인지 수준과의 정렬 실패 빈번**
- **Persona-Based Approach**: 질문 품질은 양호하나, **의도한 인지 목표에서 벗어나는 경우 빈번**

### 3.3 정성적 결과 (인간 검토)
- 간소화된 프롬프트와 페르소나 기반 프롬프트는:
  - 질문의 명확성과 관련성은 양호
  - 하지만 **목표 인지 수준과의 정렬에서 일관성 부족**
  - 질문이 너무 복잡하거나 의도한 인지 목표에서 벗어나는 경향

### 3.4 교육적 함의
- AI 생성 교육 콘텐츠의 품질은 단순히 "생성 가능한지"가 아니라 **"의도한 학습 목표와 정렬되는지"**가 핵심
- 프롬프트의 명시성과 구조화가 **학습 분석(learning analytics)**의 품질을 결정

---

## 4. 한계점 및 향후 연구 방향

### 4.1 연구 한계
- 특정 LLM (Gemini 2.0 Flash Lite)에 한정
- 특정 도메인 (컴퓨터 과학)에 한정
- Bloom's Taxonomy의 제한된 레벨 (Knowledge, Application, Analysis)
- 소규모 인간 검토 (제한된 수의 검토자, 질문 일부만 검토)

### 4.2 향후 연구 계획 (논문에서 제시)
1. **Few-shot learning**: 프롬프트에 여러 예시 제공
2. **Chain-of-thought prompting**: 복잡한 인지 수준 정렬 향상
3. **대규모 인간 전문가 검토**: 다중 검토자, 다양한 주제 전문가
4. **다양한 LLM 및 도메인 테스트**: 일반화 가능성 평가
5. **OneClickQuiz 통합**: 프롬프트 최적화 기능 직접 통합

---

## 5. MeducAI 프롬프트에의 적용 가능성

### 5.1 현재 MeducAI 프롬프트 특징 분석

#### 5.1.1 S1 (Group-level) 프롬프트
- ✅ **명시적 제약 조건**: HARD RULES, Schema Invariance 등 명확한 구조
- ✅ **상세한 지시사항**: Column 구조, Formatting rules 등 구체적 명세
- ✅ **역할 정의**: "Radiology Board Exam Content Architect" 명시
- ⚠️ **개선 여지**: 인지적 수준(Bloom's Taxonomy)에 대한 명시적 언급 부재

#### 5.1.2 S2 (Entity-level) 프롬프트
- ✅ **명시적 제약**: CARD ROLE, BOARD-EXAM STYLE 등 상세 규칙
- ✅ **구조화된 출력**: JSON Schema 명확히 정의
- ⚠️ **개선 여지**: 각 카드(Q1/Q2/Q3)의 목표 인지 수준에 대한 명시적 지시 부재

### 5.2 적용 가능한 개선 방향

#### 5.2.1 명시적 인지 수준 정렬 강화

**현재 상태:**
- S2 프롬프트에서 Q1/Q2/Q3의 역할 구분은 있으나, 각 역할이 목표하는 **인지적 수준**에 대한 명시 부족

**개선 제안:**
```
Q1 (BASIC, image-on-front):
- 목표 인지 수준: Knowledge (기억/재인)
- 기대 행동: 핵심 용어, 정의, 기본 구조의 명확한 회상
- 금지: 복잡한 분석, 적용, 평가 단계 요구

Q2 (MCQ, image-on-back):
- 목표 인지 수준: Application (적용)
- 기대 행동: 영상 소견과 임상 상황 연결, 패턴 인식, 진단 과정 적용
- 금지: 단순 기억 수준 또는 고차원 분석 수준

Q3 (MCQ, no-image):
- 목표 인지 수준: Analysis (분석) 또는 Application (적용)
- 기대 행동: 차별 진단, 다중 요인 종합, 임상적 판단
- 금지: 단순 기억 수준
```

#### 5.2.2 프롬프트 구조화 수준 강화

**논문의 주요 교훈:**
- "Explicit, detailed prompts are crucial for precise cognitive alignment"
- 간소화된 프롬프트는 질문 품질은 양호하나 목표 정렬 실패

**현재 MeducAI 프롬프트의 강점:**
- 이미 상세한 HARD RULES 구조를 가지고 있음
- 명시적 제약 조건과 포맷 규칙 정의

**추가 강화 가능 영역:**
1. **인지 수준별 예시 제공**: Few-shot learning 접근법
2. **인지 수준 위반 사례 명시**: "Do NOT generate Q1 questions that require Analysis-level reasoning"
3. **인지 수준 자체 점검 요청**: "Verify that each card matches its target cognitive level"

#### 5.2.3 페르소나 기반 접근법의 제한성 인식

**논문 발견:**
- 페르소나 기반 프롬프트는 질문 품질은 좋지만 인지적 정렬에서 일관성 부족

**MeducAI 적용:**
- 현재 "Radiology Board Exam Content Architect" 등 역할 정의는 **명시적 제약과 함께 사용** 중 → 이는 적절한 접근
- 단, 역할 정의만으로는 부족하며 **구체적 행동 규칙**이 필수 → 현재 S1/S2 프롬프트는 이미 이를 충족

---

## 6. 구체적 프롬프트 개선 제안

### 6.1 S2 프롬프트 개선 제안

#### 제안 1: 인지 수준 명시적 정의 추가

```markdown
CARD ROLE AND COGNITIVE ALIGNMENT (HARD):

Q1 (BASIC, image-on-front):
- Cognitive Level Target: KNOWLEDGE (Bloom's Taxonomy Level 1)
- Expected Behavior: Direct recall of facts, definitions, structures
- Forbidden: Questions requiring application, analysis, or evaluation
- Examples of appropriate Q1:
  * "X선에서 이 구조는 무엇인가?" (direct identification)
  * "이 용어의 정의는?" (factual recall)
- Examples of INappropriate Q1:
  * "이 소견의 감별 진단은?" (requires analysis)
  * "이 병변에서 예상되는 임상 증상은?" (requires application)

Q2 (MCQ, image-on-back):
- Cognitive Level Target: APPLICATION (Bloom's Taxonomy Level 3)
- Expected Behavior: Apply knowledge to specific imaging findings, recognize patterns
- Forbidden: Pure recall without context, or complex multi-step analysis
- Examples of appropriate Q2:
  * "이 영상 소견에서 가장 가능성 높은 진단은?" (pattern recognition + application)
  * "이 환자의 임상 정보와 영상 소견을 고려할 때 다음 중 적절한 것은?" (contextual application)
- Examples of INappropriate Q2:
  * "이 병변의 정의는?" (too simple, Knowledge level)
  * "이 5가지 질환을 확률 순으로 나열하면?" (too complex, Analysis level)

Q3 (MCQ, no-image):
- Cognitive Level Target: ANALYSIS or APPLICATION (Bloom's Taxonomy Level 4 or 3)
- Expected Behavior: Differentiate between options, synthesize multiple factors, clinical reasoning
- Forbidden: Simple factual recall
- Examples of appropriate Q3:
  * "다음 중 이 소견을 가장 잘 설명하는 것은?" (requires differentiation)
  * "이 병변의 병인, 영상 소견, 임상 증상을 종합할 때 가장 중요한 특징은?" (synthesis)
```

#### 제안 2: 인지 수준 자체 점검 요청 추가

```markdown
SELF-VERIFICATION (INTERNAL):
Before finalizing each card, verify:
1. Q1 cards: Can this be answered by direct recall without context? If NO → move to Q2/Q3 or simplify.
2. Q2 cards: Does this require applying knowledge to a specific imaging context? If NO → adjust to Q1 (too simple) or Q3 (too complex).
3. Q3 cards: Does this require differentiating, analyzing, or synthesizing multiple factors? If NO → this is likely Q1 or Q2 level.
```

### 6.2 S1 프롬프트 개선 제안

#### 제안: Master Table의 시험포인트 컬럼에 인지 수준 명시

현재 S1은 Master Table 생성 시 "시험포인트" 컬럼을 포함하나, 이 컬럼에 **목표 인지 수준**을 명시적으로 포함하도록 프롬프트 개선:

```markdown
시험포인트 컬럼 작성 규칙:
- 각 Entity의 시험 포인트를 명시할 때, 목표 인지 수준을 함께 표시
- 형식: "[인지 수준]: [포인트 내용]"
- 인지 수준 옵션: Knowledge, Application, Analysis
- 예시:
  * "Knowledge: 용어 정의 및 해부학적 위치"
  * "Application: 모달리티별 영상 소견 인식 및 패턴 매칭"
  * "Analysis: 감별 진단 포인트 및 임상적 판단 기준"
```

---

## 7. 연구 방법론적 교훈

### 7.1 프롬프트 평가 방법론

**논문의 접근법:**
1. 자동 분류 (DistilBERT) + 인간 검토 조합
2. 정량적 정렬률 + 정성적 품질 평가

**MeducAI 적용:**
- 현재 QA 프로세스에서 인간 검토는 수행 중
- **인지 수준 자동 분류** 도입 검토 가능:
  - S2 출력 카드에 대해 Bloom's Taxonomy 레벨 자동 분류
  - 목표 레벨(Q1→Knowledge, Q2→Application, Q3→Analysis)과의 정렬률 측정
  - 프롬프트 개선의 효과를 정량적으로 평가

### 7.2 프롬프트 변형 실험

**논문의 실험 설계:**
- 3가지 프롬프트 전략을 동일한 입력으로 비교
- 동일 모델, 동일 평가 기준

**MeducAI 적용:**
- 프롬프트 개선 시 **A/B 테스트** 방식 도입:
  - 현재 프롬프트 vs 개선된 프롬프트
  - 동일한 Entity 그룹에 대해 두 버전 실행
  - QA 결과 비교 (인지 수준 정렬률, 인간 평가 점수)

---

## 8. 결론 및 다음 단계

### 8.1 핵심 교훈
1. **명시성의 중요성**: 프롬프트의 명시적이고 상세한 구조가 인지적 정렬에 결정적
2. **구조화의 필요성**: 단순한 페르소나 정의만으로는 부족, 구체적 행동 규칙 필수
3. **정량적 평가**: 프롬프트 개선 효과를 정량적으로 측정하는 메커니즘 필요

### 8.2 MeducAI에의 즉시 적용 가능성
- ✅ **높음**: S2 프롬프트에 인지 수준 명시적 정의 추가
- ✅ **높음**: 각 카드 타입(Q1/Q2/Q3)의 목표 인지 수준 명시
- ⚠️ **중간**: 인지 수준 자동 분류 시스템 도입 (추가 개발 필요)
- ⚠️ **중간**: 프롬프트 변형 A/B 테스트 인프라 구축 (실험 설계 필요)

### 8.3 권장 다음 단계
1. **단기 (즉시 적용 가능)**:
   - S2 프롬프트에 인지 수준 명시적 정의 섹션 추가
   - 각 카드 타입별 목표 인지 수준과 금지 사항 명시
   - 인지 수준 자체 점검 요청 추가

2. **중기 (개발 필요)**:
   - Bloom's Taxonomy 분류 모델 도입 (DistilBERT 기반 또는 유사)
   - QA 프로세스에 인지 수준 정렬 평가 추가
   - 프롬프트 개선 효과 정량적 측정

3. **장기 (연구 확장)**:
   - Few-shot learning 접근법 실험
   - Chain-of-thought prompting 적용 검토
   - 다양한 프롬프트 전략 비교 연구

---

## 9. 참고 문헌

**원본 논문:**
Yaacoub, A., Da-Rugna, J., & Assaghir, Z. (2025). Lightweight Prompt Engineering for Cognitive Alignment in Educational AI: A OneClickQuiz Case Study. *36th Central European Conference on Information and Intelligent Systems (CECIIS 2025)*, Varazdin, Croatia. arXiv:2510.03374v1

**관련 선행 연구 (논문에서 인용):**
- Yaacoub, A., Da-Rugna, J., & Assaghir, Z. (2025). Assessing AI-Generated Questions' Alignment with Cognitive Frameworks in Educational Assessment. arXiv:2504.14232
- Yaacoub, A., Assaghir, Z., & Da-Rugna, J. (2025). Cognitive Depth Enhancement in AI-Driven Educational Tools via SOLO Taxonomy. In *Proceedings of the Third International Conference on Advances in Computing Research (ACR'25)*
- Yaacoub, A., Tarnpradab, S., Khumprom, P., Assaghir, Z., Prevost, L., & Da-Rugna, J. (2025). Enhancing AI-Driven Education: Integrating Cognitive Frameworks, Linguistic Feedback Analysis, and Ethical Considerations for Improved Content Generation. arXiv:2505.00339

---

## 10. 부록: 논문 핵심 요약표

| 항목 | 내용 |
|------|------|
| **연구 주제** | 경량 프롬프트 엔지니어링이 교육용 AI의 인지적 정렬에 미치는 영향 |
| **평가 프레임워크** | Bloom's Taxonomy (Knowledge, Application, Analysis) |
| **실험 모델** | Gemini 2.0 Flash Lite |
| **프롬프트 전략** | 1) Detailed Baseline, 2) Simpler Version, 3) Persona-Based |
| **핵심 발견** | 명시적이고 상세한 프롬프트가 정확한 인지적 정렬의 필수 요소 |
| **평가 방법** | DistilBERT 자동 분류 + 인간 검토 |
| **주요 결론** | 간소화/페르소나 기반 프롬프트는 질문 품질은 양호하나 인지적 정렬 실패 빈번 |
| **MeducAI 적용 가능성** | 높음 (S2 프롬프트 인지 수준 명시화, 평가 메커니즘 도입) |


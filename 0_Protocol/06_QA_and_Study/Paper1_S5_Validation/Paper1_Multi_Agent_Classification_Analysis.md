# Multi-Agent 시스템 분류 분석

**질문**: S2 생성 이후 생성된 문제를 검토하는 LLM을 하나 더 추가하면 이번 연구를 "Multi-agent"라고 볼 수 있는가?

---

## 1. 현재 파이프라인 구조

### 1.1 현재 단계별 역할

```
S1 (LLM): Group-level 구조화
  ↓
S2 (LLM): Entity-level 카드 생성
  ↓
S3 (코드): 선택 및 QA gate (LLM 없음)
  ↓
S4 (LLM): 이미지 생성
```

**특징:**
- **순차적 파이프라인** (Sequential Pipeline)
- 각 단계는 독립적으로 실행
- 단방향 데이터 흐름 (S1 → S2 → S3 → S4)
- 에이전트 간 직접적인 상호작용 없음

---

## 2. S2 이후 검토 LLM 추가 시 구조

### 2.1 제안된 구조

```
S1 (LLM): Group-level 구조화
  ↓
S2 (LLM): Entity-level 카드 생성
  ↓
S2.5 (검토 LLM): 생성된 카드 검토/평가
  ↓
S3 (코드): 선택 및 QA gate
  ↓
S4 (LLM): 이미지 생성
```

**가능한 검토 LLM 역할:**
- **옵션 A**: 단순 평가 (Quality scoring, blocking error detection)
- **옵션 B**: 피드백 제공 (Feedback generation, revision suggestions)
- **옵션 C**: 수정/재생성 (Revision, regeneration with feedback)

---

## 3. Multi-Agent 시스템의 정의

### 3.1 학술적 정의 (일반적)

**Multi-Agent System (MAS)**는 다음 특성을 가집니다:

1. **여러 독립적인 에이전트** (Multiple Independent Agents)
   - 각 에이전트는 자율적인 의사결정 능력
   - 각 에이전트는 고유한 목표/책임

2. **에이전트 간 상호작용** (Agent Interaction)
   - 협력 (Cooperation)
   - 경쟁 (Competition)
   - 협상 (Negotiation)
   - 통신 (Communication)

3. **동적 의사결정** (Dynamic Decision-Making)
   - 에이전트가 다른 에이전트의 행동에 반응
   - 피드백 루프 (Feedback Loops)
   - 적응적 행동 (Adaptive Behavior)

4. **분산 처리** (Distributed Processing)
   - 병렬 실행 가능
   - 독립적인 작업 수행

---

## 4. 현재 구조의 Multi-Agent 특성 분석

### 4.1 현재 구조 (S2 이후 검토 LLM 추가 전)

**Multi-Agent 특성:**
- ✅ **여러 LLM 사용**: S1, S2, S4에서 LLM 사용
- ❌ **상호작용 부재**: 순차적 실행, 단방향 흐름
- ❌ **동적 의사결정 부재**: 각 단계는 고정된 입력-출력
- ❌ **피드백 루프 없음**: 이전 단계로의 피드백 없음

**결론**: **Multi-LLM Pipeline**이지만 **Multi-Agent System**은 아님

---

### 4.2 S2 이후 검토 LLM 추가 시 (옵션별)

#### 옵션 A: 단순 평가 (Quality Scoring)

```
S2 → 검토 LLM (평가만) → S3
```

**특성:**
- 검토 LLM은 평가만 수행 (수정 없음)
- 단방향 흐름 유지
- 피드백 루프 없음

**Multi-Agent 여부**: ❌ **아니오**
- 여전히 순차적 파이프라인
- 에이전트 간 상호작용 없음

---

#### 옵션 B: 피드백 제공 (Feedback Generation)

```
S2 → 검토 LLM (피드백 생성) → S3 (피드백 반영 여부 결정)
```

**특성:**
- 검토 LLM이 피드백 생성
- S3가 피드백을 반영할지 결정
- 일부 상호작용 존재

**Multi-Agent 여부**: ⚠️ **부분적**
- 피드백 메커니즘이 있으나
- 직접적인 협력/협상 구조는 아님
- "Multi-Agent"라고 하기에는 약함

---

#### 옵션 C: 수정/재생성 (Revision with Feedback Loop)

```
S2 → 검토 LLM (평가 + 피드백) → S2 (재생성) → 검토 LLM (재평가)
  ↑                                                              ↓
  └─────────────────── 반복 (만족할 때까지) ────────────────────┘
```

**특성:**
- 검토 LLM과 S2 간 피드백 루프
- 동적 의사결정 (재생성 여부 결정)
- 협력적 구조 (검토 ↔ 생성)

**Multi-Agent 여부**: ✅ **예, 가능**
- 에이전트 간 상호작용 존재
- 피드백 루프로 인한 동적 의사결정
- 협력적 구조

---

## 5. 학술적 분류 관점

### 5.1 현재 구조의 적절한 분류

**권장 용어:**
- **"Multi-LLM Pipeline"** 또는 **"Sequential LLM Pipeline"**
- **"Modular LLM System"**
- **"Staged Generation System"**

**피해야 할 용어:**
- "Multi-Agent System" (상호작용 부재)

---

### 5.2 S2 이후 검토 LLM 추가 시 분류

#### 옵션 A (단순 평가)
- **"Multi-LLM Pipeline with Quality Gate"**
- Multi-Agent 아님

#### 옵션 B (피드백 제공)
- **"Multi-LLM Pipeline with Feedback Mechanism"**
- Multi-Agent라고 하기에는 약함

#### 옵션 C (피드백 루프)
- **"Multi-Agent LLM System"** 또는 **"Collaborative LLM System"**
- Multi-Agent로 분류 가능

---

## 6. 논문 작성 시 권장사항

### 6.1 정확한 용어 사용

**현재 구조:**
- "We propose a **sequential multi-LLM pipeline** for educational content generation"
- "The system employs **multiple LLMs in a staged architecture**"

**검토 LLM 추가 시 (옵션 C):**
- "We extend the pipeline to a **multi-agent system** where a review agent provides iterative feedback to the generation agent"
- "The system employs **collaborative LLM agents** with feedback loops"

### 6.2 Multi-Agent라고 주장하려면

**필수 요소:**
1. ✅ **에이전트 간 상호작용**: 피드백 루프, 협력 메커니즘
2. ✅ **동적 의사결정**: 에이전트가 다른 에이전트의 출력에 반응
3. ✅ **자율성**: 각 에이전트가 독립적인 목표/책임
4. ✅ **통신/협상**: 에이전트 간 정보 교환

**현재 구조 (검토 LLM 없음):**
- ❌ 위 요소들이 부족 → Multi-Agent 아님

**검토 LLM 추가 (옵션 C):**
- ✅ 위 요소들이 충족 → Multi-Agent로 분류 가능

---

## 7. 결론 및 권장사항

### 7.1 현재 구조

**Multi-Agent 아님**
- 순차적 파이프라인
- 에이전트 간 상호작용 없음
- "Multi-LLM Pipeline" 또는 "Sequential LLM System"이 적절

### 7.2 S2 이후 검토 LLM 추가 시

**옵션에 따라 다름:**

| 옵션 | Multi-Agent 여부 | 권장 용어 |
|------|-----------------|----------|
| A: 단순 평가 | ❌ 아니오 | Multi-LLM Pipeline with Quality Gate |
| B: 피드백 제공 | ⚠️ 부분적 | Multi-LLM Pipeline with Feedback |
| C: 피드백 루프 | ✅ 예 | Multi-Agent LLM System |

### 7.3 Multi-Agent로 분류하려면

**최소 요구사항:**
- 검토 LLM이 S2에 피드백 제공
- S2가 피드백을 반영하여 재생성 가능
- 반복적 개선 루프 (iterative refinement)
- 에이전트 간 협력 구조

**권장 구조:**
```
S2 (생성 에이전트) ↔ 검토 LLM (검토 에이전트)
  ↑                    ↓
  └── 피드백 루프 ──────┘
```

---

## 8. 참고 문헌 관점

**Multi-Agent System의 전형적 예시:**
- Swarm intelligence (여러 에이전트가 협력하여 문제 해결)
- Game-theoretic agents (경쟁/협상)
- Collaborative filtering agents (상호 추천)
- Iterative refinement systems (반복적 개선)

**현재 MeducAI 구조:**
- 전형적인 Multi-Agent System은 아님
- 하지만 **옵션 C (피드백 루프)** 구조로 확장하면 Multi-Agent로 분류 가능

---

**작성일**: 2025-12-20  
**목적**: Multi-Agent 분류 기준 명확화


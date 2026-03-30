# Multiagent Terminology and Research Rationale (Canonical)

**Status**: Canonical (Positioning + research rationale)  
**Version**: 1.0  
**Supersedes**: None  
**Frozen**: No  
**Last updated**: 2025-12-29  
**Owner**: MeducAI Research Team  
**Scope**: “S5 기반 one-shot 자동 수정 루프(S5R/S1R/S2R)”의 명명(‘multiagent’) 적합성 및 연구적 가치(논문화 가능성) 정리  
**Non-goals**: 구현 상세(코드) 자체를 대체하지 않음. 구현은 개발 인계 문서/워크플로우 문서를 따른다.

---

## 1. 결론 요약 (Executive take)

### 1.1 “Multiagent”라고 불러도 되는가?

- **내부 구현/프로젝트 커뮤니케이션에서는 “multiagent” 명명이 정당화 가능**하다.
  - 역할이 분리된 복수의 컴포넌트(Verifier/Planner/Regenerator)가 **명시적 인터페이스(아티팩트/스키마)**로 연결되어 순차적으로 협업한다.
  - 현재 정의된 흐름: **S5(Verifier) → S5R(Planner) → S1R/S2R(Regenerator) → S5’(Post-Validator)**.
- 다만 **외부(논문/리뷰어) 관점에서 “multi-agent system”은 과도한 기대(자율적 상호작용/협상/동시성)를 유발**할 수 있다.
  - 따라서 논문에서는 아래 표현을 **1차 용어**로 사용하고, “multi-agent”는 보조적으로 쓰는 것을 권장한다.

#### 권장 외부 표현(Primary wording)

- **role-specialized agentic repair pipeline (verifier–planner–regenerator)**
- **agent-orchestrated one-shot repair cascade**

#### 보조 표현(Secondary wording)

- “we refer to this setup as a multi-agent (role-specialized) workflow”

#### 피해야 할 과장

- autonomous multi-agent, negotiation, emergent behavior, MARL 등(본 설계의 one-shot/루프 금지와 불일치)

### 1.2 연구적 가치가 있는가?

- 있다. 핵심은 “LLM이 더 잘 만들었다”가 아니라 아래 2축을 **같은 데이터 흐름에서 동시에 계량화**할 수 있다는 점이다.
  - **Tool-effect**: 수정 파이프라인이 품질/안전성을 얼마나 개선하는가, 그리고 **악화(degradation)**는 얼마나 발생하는가.
  - **Verifier(S5) 정확도/신뢰도**: S5의 판단이 사람과 얼마나 일치하는가(agreement), FP/FN은 어떤가.
- 또한 평가 설계가 **Primary endpoint(수정 전 원본 평가)**를 보호하도록 강제한다.
  - arm 비교/주 분석은 원본만으로 수행하고, 수정 효과는 secondary로 분리해 보고한다.

---

## 2. “Multiagent” 최소 정의(논문용 방어 정의)

본 프로젝트에서 “multiagent”는 아래 조건을 만족하는 **role-specialized agentic workflow**로 정의한다.

1. 서로 다른 역할(role)과 책임(boundary)을 가진 컴포넌트가 2개 이상 존재한다.
   - 예: S5는 validation-only이며 수정/생성을 하지 않는다.
2. 에이전트 간 상호작용은 자연어 채팅이 아니라 **아티팩트(파일/스키마) 기반 메시지 전달**로 구현된다.
   - 예: S5 결과 → S5R repair plan → S1R/S2R 입력.
3. 시스템은 **one-shot(단 1회 수정)**으로 제한되며, 원본 아티팩트는 불변(immutable)이다.

리뷰어가 “이건 multi-agent가 아니라 파이프라인 아닌가?”라고 물으면:

- “agentic pipeline”로 1차 포지셔닝하고,
- “multiagent는 내부 용어이며, 본 연구에서의 정의는 role-specialized artifact-mediated workflow”라고 명시한다.

---

## 3. 연구 질문(Research questions)과 기여(Contributions)

### 3.1 핵심 연구 질문(권장 2축)

1) **Tool-effect(수정 파이프라인의 효과)**  
- 동일 원본에 대해, one-shot repair 후 품질이 개선되는가? **악화(degradation)**는 얼마나 발생하는가?  
- 측정(예):
  - `blocking_error_change`
  - `technical_accuracy_change` (0/0.5/1)
  - `overall_quality_change` (1–5)
  - `repair_acceptance_rate`
  - `degradation_rate` (필수 보고)

2) **Verifier(S5) 판단의 신뢰도/정확도**  
- S5의 blocking/accuracy/quality 판단은 사람과 얼마나 일치하는가? FP/FN은?  
- 측정(예):
  - `s5_*_agreement_rate`
  - `s5_false_positive_rate`
  - `s5_false_negative_rate`

### 3.2 논문화 포인트(리뷰어 설득 포인트)

- “생성 모델 비교(arm comparison)”와 “수정 도구 평가(tool evaluation)”를 **평가 디자인 차원에서 분리**했다.
  - arm 비교(Primary): Pre-Multiagent(원본만) 평가
  - tool-effect(Secondary): Post-Multiagent(수정본) 평가 및 변화량
- 원본 불변/one-shot/Fail-fast 금지/로깅 강제는 재현성과 편향 통제를 위한 **실험 설계 요소**로 주장 가능하다.

---

## 4. 평가 설계 타당성(Threats to validity)과 보완책

### 4.1 위협 1: 동일 평가자가 원본 후 수정본을 평가하는 anchoring

- 장점: within-rater 비교로 분산 감소, “도구가 실제로 도움 되는지” 측정에 유리
- 단점: 수정본 평가가 원본 평가에 영향을 받을 수 있음(anchoring/confirmation bias)

**보완책(비용 대비 효과 순)**
- A. Primary endpoint는 Pre-Multiagent만 사용(원칙을 반복 강조)
- B. tool-effect 보고 시 **degradation rate**와 **acceptance rate**를 반드시 함께 제시
- C. 가능하면 소규모 서브셋에서 between-rater 감도 분석(원본만 vs 수정본만 평가)

### 4.2 위협 2: S5 결과가 ‘정답’처럼 보이는 권위 편향

- Reveal 화면에서 S5 패널이 강하면 사람 평가가 S5에 끌릴 수 있음
- 보완:
  - UI 문구로 “S5는 참고용이며 오류가 있을 수 있음”을 명시
  - Post 단계에서 **동의/비동의(agreement)** 항목을 강제로 수집해 영향력을 측정 변수로 흡수

---

## 5. 구현/운영 관점의 연구 친화적 규칙(요약)

- **라인리지 필수**: S5R plan에 baseline hashes, `s5_snapshot_id`, `repair_iteration=1` 포함
- **악화 숨김 금지**: `quality_change=DEGRADED` 비율을 상시 모니터링하고 논문에도 보고
- **안전 폴백 export**: fail-fast 금지와 양립. repaired 선택은 “승격”, 실패 시 baseline 유지

---

## 6. One-liner(논문용)

“We propose a role-specialized agentic repair pipeline that converts verifier-detected issues into executable repair plans and regenerates educational items in a one-shot manner, while preserving an immutable primary endpoint collected before any repair signal is revealed.”



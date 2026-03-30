# S0 Thinking Policy — Gemini 2.5 Flash

**Status:** **SUPERSEDED** (Historical Reference)  
**Superseded-by:** `ARM_CONFIGS_Provider_Model_Resolution.md`  
**Applies-to:** Step S0 (Gemini implementation)  
**Last Updated:** 2025-12-20

**⚠️ IMPORTANT:** This document is **superseded**. The canonical protocol is `ARM_CONFIGS_Provider_Model_Resolution.md`. This document is retained as a **historical reference** for Gemini 2.5 Flash-specific thinking control details.

**Note:** Current implementation uses **Gemini 3** models with `thinking_level` parameter, not Gemini 2.5 Flash with `thinkingBudget`.

---

## 1. Purpose

본 문서는 MeducAI S0 QA 실험에서
**Gemini 계열 모델의 “Thinking”을 실제 실행 가능한 실험 요인으로 정의하고**,
“thinking 플래그는 있으나 API 레벨에서 미동작하는 상태”가 재발하지 않도록
**모델 선택, 파라미터, 메타데이터 기록 규칙**을 명확히 고정한다.

---

## 2. Design Principles (Non-Negotiable)

1. **Thinking은 ‘라벨’이 아니라 API 파라미터로 실행되어야 한다.**
2. S0에서는 **Thinking ON / OFF가 명확히 구분되는 최소 설계**만 허용한다.
3. S0 결과물(JSONL)만 보고도
   *“이 arm에서 thinking이 실제로 적용되었는지”*를 판별할 수 있어야 한다.
4. S0에서는 **thought summary / thought signature를 수집하지 않는다.**
   (품질·비용·복잡도 최소화 목적)

Normative acceptance and experimental validity rules are defined in
ARM_CONFIGS_Provider_Model_Resolution.md.

---

## 3. Model Selection (S0 Fixed)

### 3.1 Allowed Model

* **`gemini-2.5-flash` ONLY**

### 3.2 Rationale

* Gemini 2.5 Flash는 `thinkingBudget=0`으로 **thinking 완전 비활성화 가능**
* Gemini 2.5 Pro는 thinking 비활성화 불가 → S0 실험 요인 분리에 부적합
* Gemini 3 계열은 `thinkingLevel(low/high)` 체계로, S0 단순 ON/OFF 비교에 부적합

---

## 4. Thinking Definition in S0

S0에서 Thinking은 아래와 같이 **단일 축으로 정의**한다.

| Mode             | thinkingBudget | Meaning                  |
| ---------------- | -------------- | ------------------------ |
| **OFF**          | `0`            | Thinking disabled        |
| **ON (Dynamic)** | `-1`           | Dynamic thinking enabled |

* 다른 값(양수 budget, thinkingLevel 등)은 **S0에서 금지**
* Gemini API 요청에 **반드시 명시적으로 포함**되어야 함

---

## 5. Arm-Level Mapping (Gemini)

S0에서 Gemini arm은 최소 아래 두 가지 상태만 허용한다.

### 5.1 Arm A — Baseline (Thinking OFF)

* model: `gemini-2.5-flash`
* thinkingBudget: `0`
* intent: 최소 latency / 비용 baseline

### 5.2 Arm C — Thinking ON (Dynamic)

* model: `gemini-2.5-flash`
* thinkingBudget: `-1`
* intent: reasoning depth 증가가 품질에 미치는 영향 평가

> ⚠️ arm_config에 `thinking: true/false`가 있더라도
> **API 요청에 thinkingBudget이 반영되지 않으면 이는 “설계 위반”으로 간주한다.**

---

## 6. API Invocation Contract (Mandatory)

Gemini 호출 시 **반드시 아래 구조를 만족해야 한다.**

### 6.1 Required Parameter Injection

* Gemini `generate_content()` 호출에

  * `thinking_config.thinking_budget`를 **항상 명시**

### 6.2 Forbidden in S0

* `includeThoughts = true`
* thought summary 수집
* thoughtSignature 관리
* function calling 기반 reasoning

---

## 7. Metadata Recording (Evidence Requirement)

S0 결과 JSONL의 각 record에는
아래 thinking 관련 메타데이터가 **항상 non-null로 기록**되어야 한다.

### 7.1 Required Fields

```json
metadata: {
  "thinking_enabled": boolean,
  "thinking_budget": integer,
  "thinking_mode": "off" | "dynamic"
}
```

### 7.2 Mapping Rule

* `thinking_budget == 0`

  * thinking_enabled = false
  * thinking_mode = "off"

* `thinking_budget == -1`

  * thinking_enabled = true
  * thinking_mode = "dynamic"

### 7.3 Hard-Fail Rule

다음 중 하나라도 발생하면 **S0 실행은 실패(Fail)로 판정**한다.

* thinking arm에서 `thinking_budget`이 metadata에 기록되지 않음
* thinking arm인데 `thinking_budget`이 API 요청에 반영되지 않음
* thinking OFF arm에서 `thinking_budget != 0`

---

## 8. Expected Observable Effects (S0 Analysis Scope)

S0 분석에서 thinking 효과는 **아래 지표들 중 일부에서만 관측되면 충분**하다.

* latency 분포 변화
* output token 수 분포 변화
* JSON schema violation rate
* QA 점수(정확성/가독성) 평균 차이

> **출력 텍스트가 동일하더라도**,
> metadata와 latency/token 차이가 존재하면
> “thinking 실험은 유효”하다고 판정한다.

---

## 9. Explicit Non-Goals (S0)

S0에서는 아래를 **의도적으로 다루지 않는다.**

* Chain-of-Thought 노출
* Thought summary 분석
* Multi-turn reasoning
* Tool-based agentic reasoning
* Gemini 3 thinkingLevel 비교

이 항목들은 **S1 이후 연구 확장 범위**에 속한다.

---

## 10. Compliance Checklist (S0 Run Validation)

S0 실행 후 아래 체크리스트를 **모두 통과해야 한다.**

* [ ] Gemini arm 요청에 thinkingBudget이 실제 포함되었다
* [ ] metadata.thinking_budget이 null이 아니다
* [ ] OFF arm은 항상 0, ON arm은 항상 -1이다
* [ ] arm 간 thinking 설정이 코드와 결과에서 일관된다

---

## 11. Summary (One-Line Rule)

> **S0에서 Gemini Thinking은
> “gemini-2.5-flash + thinkingBudget {0 vs −1}”로만 정의한다.**
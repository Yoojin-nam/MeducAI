# MI-CLEAR Configuration Log – Step S0 (v2.0 aligned)

**Date of Experiment:** 2025-12-15
**QA Framework Version:** **v2.0**
**Scope:** Step S0 only (Paper-1, Deployment Model Selection)
**Reproducibility Standard:** MI-CLEAR-LLM (Items 1–3)

> 본 문서는 기존 `S0_Configuration_Log.md (v1.7)`을 **QA Framework v2.0**에 맞게 재작성한 **최종 Canonical 설정 로그**이다.
> 본 로그는 **S0 Non-inferiority 논문화(Paper-1)**의 Methods/Appendix에 그대로 인용 가능하도록 구성된다.

---

## 1. Purpose of This Log (Canonical)

* Step S0에서 비교된 **6-arm 설정을 완전 재현 가능**하게 고정
* “왜 이 모델/설정으로 비교했는가”에 대한 **사후 변경 불가 근거** 제공
* Step S1(Full-scale QA)과 **의도적으로 분리**됨

  * 본 로그는 **모델 선택(S0)**만을 위한 문서이며
  * S1에서는 **선정된 단일 Deployment Model만 사용**한다.

---

## 2. Model Versions & Access Definition

> 특정 date-stamped snapshot이 제공되지 않는 모델의 특성상,
> **Access Date + Provider SDK version**을 모델 상태 정의의 기준으로 사용한다.

| Model Identifier       | Provider | Access Date | SDK / API Version | Note                          |
| ---------------------- | -------- | ----------- | ----------------- | ----------------------------- |
| `gemini-2.5-flash`     | Google   | 2025-12-15  | google-genai v0.x | Arms A–D (low-cost backbone)  |
| `gemini-3-pro-preview` | Google   | 2025-12-15  | google-genai v0.x | Arm E (high-end, closed-book) |
| `gpt-5.2`          | OpenAI   | 2025-12-15  | openai v1.x       | Arm F (external benchmark)    |

**Access-date policy (MI-CLEAR):**
동일 Access Date + 동일 SDK + 동일 파라미터 세트가 유지되지 않으면 **동일 모델로 간주하지 않는다**.

---

## 3. Arm Configuration (Frozen for Step S0)

> 모든 arm은 **Set 단위 평가(S0)**에서만 사용되며,
> S1 단계에서는 **본 섹션의 설정을 재사용하지 않는다**.

| Arm | ID        | Base Model           | Thinking | RAG | Key Params                        | Canonical Note                |
| --- | --------- | -------------------- | -------- | --- | --------------------------------- | ----------------------------- |
| A   | Baseline  | gemini-2.5-flash     | OFF      | OFF | temp=0.2                          | Minimum viable baseline       |
| B   | RAG Only  | gemini-2.5-flash     | OFF      | ON  | temp=0.2, tool=search             | Retrieval-only ablation       |
| C   | Thinking  | gemini-2.5-flash     | ON       | OFF | thinking_budget=1024              | Reasoning-only ablation       |
| D   | Synergy   | gemini-2.5-flash     | ON       | ON  | thinking_budget=1024, tool=search | **Cost-efficient challenger** |
| E   | High-End  | gemini-3-pro-preview | ON       | OFF | thinking_budget=2048              | Google intelligence benchmark |
| F   | Benchmark | gpt-5.2-pro          | ON       | OFF | reasoning_effort="medium"         | External industry benchmark   |

---

## 4. Arm-specific Constraints & Rationale

### 4.1 RAG Arms (B, D)

* Retrieval tool: **Google Search**
* JSON mode disabled during generation (tool invocation requirement)
* Post-generation structured parsing applied

**Rationale:**
검색 기반 grounding의 **순수 효과(ablation)**와 thinking과의 상호작용을 분리 평가하기 위함.

---

### 4.2 Thinking Parameters

* gemini-2.5-flash: `thinking_budget = 1024`
* gemini-3-pro-preview: `thinking_budget = 2048`
* gpt-5.2-pro: `reasoning_effort = "medium"`

**Rationale:**

* Flash 계열: cost–performance 균형점
* Pro 계열: 상한 성능 측정 목적
* GPT-5.2: API 충돌 방지를 위해 reasoning_effort만 사용

---

## 5. Disabled / Fixed Parameters (MI-CLEAR Safeguards)

### 5.1 Explicitly Disabled

* temperature tuning beyond fixed default
* top_p, top_k sampling variation
* logprobs output
* system-level prompt mutation during run

### 5.2 Fixed Across All Arms

* Prompt templates (hash-locked)
* Set payload size: **12 cards per set**
* Card-type mix
* Sequential execution (no concurrency)

---

## 6. Compute & Execution Environment

* **Language:** Python ≥ 3.9
* **Execution mode:** Sequential (rate-limit & contamination control)
* **SDKs:**

  * Google: `google-genai`
  * OpenAI: `openai`
* **Logging:**

  * start_ts / end_ts / latency_sec
  * input_tokens / output_tokens
  * rag_queries_count / rag_sources_count
  * cost_estimated_usd (post-hoc)

---

## 7. Relationship to Freeze Policy (v2.0)

* 본 로그는 **Step S0 Freeze**의 일부이다.
* S0 PASS 시:

  * 본 문서에 정의된 arm 중 **단일 Deployment Model**만 선택됨
  * 선택된 arm의 설정은 **조건부 Freeze** 상태로 전환
* Step S1 PASS 시:

  * 본 로그는 **Reference-only archival artifact**가 되며
  * 실제 배포는 **선정된 단일 모델 설정만 사용**한다.

---

## 8. Canonical Storage Location

```
0_Protocol/04_QA_Framework/
├─ QA_Framework.md
├─ S0_S1_Completion_Checklist_and_Final_Freeze_v2.0.md
├─ S0_Configuration_Log_v2.0.md   ← 본 문서
└─ (archive)
   └─ S0_Configuration_Log_v1.7.md
```

---

**Canonical statement**

> This configuration log fully specifies the model versions, parameters, and constraints used in Step S0 of MeducAI QA Framework v2.0, ensuring MI-CLEAR-compliant reproducibility and auditability for the non-inferiority study (Paper-1).

## Appendix E. Replayability for Post-hoc QA System Comparison

All artifacts generated under this configuration are intended to be replayable for post-hoc evaluation by alternative QA systems.

The generation layer (models, prompts, parameters) is considered frozen after S0/S1, while the QA layer may be re-applied without regeneration.

This separation enables controlled comparisons between Human-only QA and automated or multi-agent QA systems using identical underlying content.

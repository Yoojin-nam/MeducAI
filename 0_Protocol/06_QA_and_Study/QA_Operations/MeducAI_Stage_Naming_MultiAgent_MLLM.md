# MeducAI Stage Naming (Multi-Agent + MLLM)

**Target paper title:** *MeducAI: A Governed Multi-Agent MLLM Pipeline for Reproducible Radiology Education Content Generation and Quality Assurance*

This document proposes stage names (S0–S6) that match the title’s framing:
- **Governed**: contract-/policy-grounded, auditable, deterministic where applicable
- **Multi-Agent**: self-evaluation loop and orchestration emphasized post-validation
- **MLLM**: multimodal rendering (S4) and multimodal validation (S5)
- **Reproducible**: deterministic compilation/resolution (S3) is explicitly labeled as such

---

## Recommended stage names (Methods-ready)

| Stage | Recommended name (EN) | Recommended name (KR) |
|---|---|---|
| S0 | **Controlled Payload & Arm-Fairness Orchestrator** | **통제 페이로드·Arm 공정성 오케스트레이터** |
| S1 | **Structure Induction Agent (Schema-Grounded)** | **구조 유도 에이전트(스키마 기반)** |
| S2 | **Card Synthesis Agent (Execution-Bounded)** | **카드 합성 에이전트(실행 경계형)** |
| S3 | **Deterministic Policy & Spec Compiler** | **결정론적 정책·스펙 컴파일러** |
| S4 | **MLLM Visual Rendering Agent** | **MLLM 시각 렌더링 에이전트** |
| S5 | **MLLM Validation & Triage Agent (Evidence-Grounded QA)** | **MLLM 검증·트리아지 에이전트(근거 기반 QA)** |
| S6 | **Multi-Agent Self-Evaluation & Refinement Orchestrator** | **다중 에이전트 자기평가·정제 오케스트레이터** |

### Notes on terminology (for consistency)
- Prefer **Agent** for stages with model calls (e.g., S1/S2/S4/S5), **Compiler/Resolver** for deterministic stages (S3), and **Orchestrator** for control loops / scheduling (S0/S6).
- If you need a single umbrella phrase, use: **“stage”** (neutral) or **“agentic module”** (when emphasizing autonomy).

---

## Concise stage names (short-form set)

| Stage | Concise name (EN) | Concise name (KR) |
|---|---|---|
| S0 | **Fairness Orchestrator** | **공정성 오케스트레이터** |
| S1 | **Structure Agent** | **구조 에이전트** |
| S2 | **Card Agent** | **카드 에이전트** |
| S3 | **Policy Compiler** | **정책 컴파일러** |
| S4 | **Visual Renderer** | **시각 렌더러** |
| S5 | **QA Validator** | **QA 검증기** |
| S6 | **Refinement Orchestrator** | **정제 오케스트레이터** |



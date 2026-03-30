# Reference Arm 선택 권장사항

**Date:** 2025-12-20  
**Updated:** 2025-12-20 (Implementation status noted)  
**Status:** Recommendation for S0 Non-Inferiority Framework

---

## 요약

**Arm E (High-End, gemini-3-pro-preview)**를 Non-Inferiority의 **Reference Arm**으로 채택하는 것을 권장합니다.

**⚠️ Implementation Note (2025-12-20):**
- **Current Implementation:** `s0_noninferiority.py` defaults to **Arm A (Baseline)** as baseline for operational simplicity
- **Recommendation:** Arm E can be configured as reference using `--baseline_arm E` parameter
- **Rationale:** While Arm E is recommended for vendor consistency and logical coherence (see below), Arm A is used as default baseline for practical implementation
- **Canonical Reference:** See `0_Protocol/06_QA_and_Study/QA_Operations/S0_Noninferiority_Criteria_Canonical.md` Section 7.2

---

## Arm E vs Arm F 비교

### Arm E (High-End)
- **Model:** gemini-3-pro-preview (Google)
- **Thinking:** ON (thinking_budget=2048)
- **RAG:** OFF (Closed-book)
- **역할:** Google intelligence benchmark (고성능 기준)
- **Vendor:** Google (내부 벤치마크)

### Arm F (Benchmark)
- **Model:** gpt-5.2-pro (OpenAI)
- **Thinking:** ON (reasoning_effort="medium")
- **RAG:** OFF (Closed-book)
- **역할:** External industry benchmark (외부 벤치마크)
- **Vendor:** OpenAI (외부 벤치마크)

---

## Arm E를 Reference로 선택하는 근거

### 1. **Vendor 일관성 (Internal Benchmark)**

- 연구 목적이 **"벤더 비교가 아니라 단일 Deployment Model 고정"** (QA_Framework v2.0, Section 1)
- Candidate arms (A-D) 모두 **Google Gemini ecosystem** 기반
- 같은 vendor 내 비교로:
  - **API/SDK 일관성** 확보
  - **Prompt/후처리 로직 공유** 가능
  - **Vendor-specific bias 최소화**
  - 논문에서 "왜 이 reference를 선택했는가" 설명 용이

### 2. **실제 배포 가능성 고려**

- Reference arm은 "최고 성능 기준"이지만, 논리적으로는 **실제 선택 가능한 후보**여야 함
- Arm F는 명시적으로 "외부 벤치마크"이며, 실제 배포 시 사용하기 어려울 수 있음
- Model_Selection_Rationale v2.0 Section 4.1: Arm F는 **"비교 대상이 아니라 참조(anchor)"**로 정의
- Arm E는 Google ecosystem 내에서 **실제 배포 가능한 고성능 옵션**

### 3. **연구 설계의 논리적 일관성**

- 6-arm factorial design에서:
  - Arms A-D: Flash 기반 저비용 후보
  - Arm E: Pro 기반 고성능 기준 (같은 vendor)
  - Arm F: 외부 참조점 (다른 vendor)
- Non-inferiority 질문: "저비용 arm이 고비용 arm에 비열등한가?"
- **같은 vendor 내 비교**가 더 직관적이고 해석이 용이

### 4. **Fairness Invariant 준수**

- QA_Framework v2.0 Section 2.2: "Arm E/F는 **RAG OFF**로 고정하여 모델 자체 지능을 비교"
- Closed-book 조건에서 **모델 자체 성능** 비교가 목적
- 같은 조건(RAG OFF)에서 같은 vendor의 고성능 모델(E)과 비교하는 것이 공정

### 5. **논문 작성 및 방어 용이성**

- Reviewer 질문: "왜 이 arm을 reference로 했는가?"
  - **Arm E:** "Google ecosystem 내 최고 성능 모델을 기준으로, 같은 vendor 내에서 비용 효율성 검증"
  - **Arm F:** "외부 벤더와 비교했지만, vendor 차이가 결과에 영향을 미쳤을 수 있음" (방어 어려움)
- 논문 Methods에서 **명확하고 간결한 근거** 제시 가능

### 6. **Secondary Role of Arm F**

- Arm F는 여전히 **external benchmark**로서 중요한 역할:
  - "Google만 비교했지만, 외부 기준(GPT-5.2)도 포함했다"는 **투명성** 제시
  - 논문 Discussion에서 cross-vendor 성능 관찰 가능
  - 하지만 **primary non-inferiority 비교**는 Arm E 기준

---

## Arm F를 Reference로 선택할 경우의 문제점

### 1. **Vendor Heterogeneity**
- API, prompt interpretation, output format이 다름
- Non-inferiority margin 해석 시 vendor effect가 혼입될 수 있음

### 2. **논리적 일관성 부족**
- Candidate arms는 모두 Google인데, reference만 OpenAI
- "왜 다른 vendor를 reference로 했는가"에 대한 설명 필요

### 3. **실제 배포 시나리오와 불일치**
- Reference는 이론적 "최고 기준"이지만, 실제 선택 가능한 arm이 reference가 아닌 것은 논리적으로 어색

---

## 권장 Non-Inferiority Framework

### Reference Arm: **Arm E (High-End, gemini-3-pro-preview)**

### Candidate Arms (비열등성 검증 대상):
- Arm A (Baseline)
- Arm B (RAG Only)
- Arm C (Thinking)
- Arm D (Synergy) ← **주요 관심 후보** (저비용 풀옵션)

### Hypothesis (예시 - Endpoint에 따라 조정):
- H₀: μ_candidate − μ_E ≥ Δ
- H₁: μ_candidate − μ_E < Δ

### Interpretation:
- NI 성립 → 저비용 candidate arm이 고성능 reference (E)에 비열등
- NI 미성립 → 통계적으로 미입증 (inconclusive)

---

## Arm F의 역할 재정의

Arm F는 Non-Inferiority의 reference가 아니라:

1. **External validation anchor**
   - "Google ecosystem만 비교했지만, 외부 기준도 확인했다"
   - 논문 Discussion에서 cross-vendor 관찰 보고

2. **Sensitivity analysis**
   - Reference를 E vs F로 바꿔도 결과가 일관적인지 확인 (exploratory)

3. **Fairness demonstration**
   - 연구가 특정 vendor에 종속되지 않았음을 보여주는 **투명성 도구**

---

## 결론

**Arm E (High-End, gemini-3-pro-preview)**를 Non-Inferiority의 **Primary Reference Arm**으로 채택하고, Arm F는 **External Benchmark/Anchor**로 유지하는 것을 강력히 권장합니다.

이는 연구 설계의 논리적 일관성, 논문 작성 용이성, 그리고 실제 배포 시나리오와의 정합성을 모두 충족합니다.


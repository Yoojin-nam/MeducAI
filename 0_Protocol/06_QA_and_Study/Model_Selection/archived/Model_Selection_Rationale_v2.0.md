# Model Selection Rationale – MeducAI (v2.0, Canonical)

**Project:** MeducAI – Clinical-Grade LLM-Based Radiology Education Study  
**Date:** 2025-12-15  
**Status:** Archived (Pre-specified; non-adaptive)  
**Superseded by:** `0_Protocol/06_QA_and_Study/Model_Selection/Model_Selection_Rationale.md`
**Do not use this file for new decisions or execution.**
**Aligned with:**  
- QA Framework v2.0  
- Sample Experiment & Model Selection Plan v2.0  
- QA Evaluation Rubric v2.0  
- QA Blinding Procedure v2.0  
- MI-CLEAR-LLM (Items 1–3)

---

## Purpose of This Document

본 문서는 MeducAI 프로젝트에서 수행된 **모델 선택(Model Selection)**에 대한  
**공식적·방법론적 근거(rationale)**를 기록한 문서이다.

본 문서의 목적은 다음과 같다.

- 모델 비교 범위와 깊이에 대한 **사전 지정 근거 제공**
- 특정 모델 및 설정의 **포함·배제 이유 명확화**
- 모델 선택이 **임상 교육 연구로서 책임감 있고 재현 가능하게 이루어졌음**을 입증
- 저널 심사, IRB 검토, 감사(audit) 대응 시 **방어 문서**로 활용

본 문서는 **실험 설계 문서(Plan)**가 아니라  
그 설계를 **왜 그렇게 제한·구성했는지 설명하는 해석·정당화 문서**이다.

---

## 1. Guiding Philosophy

MeducAI는 **대규모 언어 모델의 성능을 비교·순위화하는 연구**가 아니라,  
**임상 교육 환경에 안전하게 배포 가능한 AI 기반 교육 시스템을 평가하는 연구**이다.

따라서 모델 선택은 다음 원칙에 의해 지배된다.

1. **임상적 적합성(Clinical appropriateness)**을 기술적 완전성보다 우선
2. **안전성·신뢰성(Safety & reliability)**을 미세한 성능 차이보다 우선
3. **재현성(Reproducibility)**을 탐색적 최적화보다 우선
4. **교육적 타당성(Educational validity)**을 벤더 경쟁보다 우선

이 원칙은 모델 비교의 범위, arm 구성, 평가 지표, 고정(freeze) 정책 전반에 적용되었다.

---

## 2. Why Exhaustive Vendor Comparison Was Not Performed

다수의 LLM 벤더(ChatGPT, Gemini, Claude, DeepSeek 등)를 포괄적으로 비교하는 접근은  
검토되었으나, 본 연구의 1차 목적에는 **부적절**하다고 판단되어 채택되지 않았다.

### 2.1 Methodological Considerations

전면적 벤더 비교는 다음 문제를 야기한다.

- 서로 다른 API, 추론 전략, 출력 포맷으로 인한 **구조적 이질성**
- 벤더별 prompt·후처리 로직 필요 → **혼입(confounding) 증가**
- 연구 초점이 **교육 효과**가 아닌 **엔지니어링 벤치마킹**으로 이동
- 결과 해석의 임상적 의미 감소

이는 학습자 중심·QA 기반 연구의 **내적 타당성**을 약화시킨다.

---

### 2.2 Alignment with Medical Education Literature

의학교육 연구에서 핵심 질문은  
“어떤 알고리즘이 가장 강력한가”가 아니라,

- 실제 배포 환경에서 **안전한가**
- 학습자가 **수용 가능한가**
- 교육적으로 **일관된 품질을 제공하는가**

이다.

따라서 본 연구에서는 **제한적·투명한 비교**가  
과도한 포괄성보다 더 적절하다고 판단하였다.

---

## 3. Rationale for a Gemini-Centered Evaluation

1차 최적화는 **Google Gemini ecosystem 내부**에서 수행되었다.

### 3.1 Technical Stability and Structured Outputs

Gemini 계열 모델은:

- JSON schema 기반 **구조화 출력**을 안정적으로 지원
- 장문 입력·배치 실행에서 **출력 변동성 낮음**
- 대규모 자동 생성 파이프라인에 적합한 **예측 가능성** 제공

이는 Master table, Anki card, infographic을 포함하는  
MeducAI 파이프라인의 **재현성과 감사 가능성**에 필수적이다.

---

### 3.2 Operational and Cost Predictability

동일 ecosystem 내 비교는:

- 비용·지연(latency) 추정의 명확화
- thinking / RAG 옵션의 **통제된 조합 평가**
- 벤더 간 숨은 정책 변화로 인한 변동성 최소화

를 가능하게 한다.

이는 반복 사용을 전제로 한 교육 시스템에서 특히 중요하다.

---

## 4. Use of External Reference Model (GPT-5.2)

OpenAI GPT-5.2-pro는 **외부 참조 기준점(external benchmark)**으로 포함되었다.

### 4.1 Purpose of External Reference

외부 참조 모델의 목적은:

- 전문가 평가자에게 **맥락적 기준점 제공**
- 연구가 특정 ecosystem에 종속되지 않았음을 **투명하게 제시**
- 저널 심사 시 **“왜 다른 모델을 완전히 배제했는가”**에 대한 방어

이다.

이는 **비교 대상**이 아니라 **참조(anchor)**이다.

---

### 4.2 Scope Limitation

외부 참조는 다음으로 엄격히 제한된다.

- 동일 prompt, 동일 payload, 동일 QA 기준
- 제한된 샘플 그룹
- RAG 비활성화(Closed-book) 고정

이를 통해 연구가 **벤더 경쟁으로 확장되는 것을 원천 차단**하였다.

---

## 5. Role of the Sample Experiment (Step S0)

모델 선택은 **학습자 노출 이전**에 수행된  
**전문의 기반 샘플 실험(Step S0)**을 통해 이루어졌다.

### 5.1 Objectives

S0의 목적은 다음을 판별하는 것이다.

- 최소 안전성 기준(Blocking error rate ≤ 1%) 충족 여부
- Reference arm (E) 대비 **품질 수준(Overall Card Quality)**
- 대규모 생성 시의 **운영 가능성**

---

### 5.2 Decision Framework

- **Safety:** Hard gate (Blocking error)
- **Quality:** Overall Card Quality를 non-inferiority endpoint로 사용
- **Statistical logic:** Non-inferiority (Reference: Arm E, Δ = 0.5 on 1–5 Likert scale)

이를 통해 **저비용 arm 채택 가능성**을 통계적으로 방어 가능하게 설계하였다.

---

## 6. Why Thinking / RAG Were Not Treated as Primary Educational Variables

Thinking 및 RAG는 **교육 개입 변수**가 아니라  
**생성 효율·품질을 조정하는 내부 시스템 변수**로 취급되었다.

그 이유는 다음과 같다.

- 학습자 경험에 직접 노출되지 않음
- 주로 생성 효율과 편집 부담에 영향
- 교육 효과 분석에는 **혼입 변수**로 작용 가능

따라서 이들은:

- S0 단계에서만 **통제 변수로 평가**
- Deployment model 선정 후 **고정**
- 학습자 연구 단계(S1 이후)에서는 **비가변 요소**

로 처리되었다.

---

## 7. Separation from Learner Outcomes

모델 선택 과정에서는 다음 정보를 **일절 사용하지 않았다**.

- 학습자 UX
- 인지 부하
- 자기 효능감
- 성취도

이는 모두 **Deployment model 고정 이후**  
전향적 관찰 연구 단계에서만 사용된다.

이로써 **post-hoc tuning 및 결과 기반 최적화 편향**을 방지한다.

---

## 8. Reproducibility, Blinding, and Auditability

모든 모델 선택 결정은:

- 사전 지정(pre-specified)
- QA Framework v2.0에 따라 실행
- Full rater blinding 하에서 평가
- Configuration log 및 completion checklist에 기록

되었다.

이는 다음을 보장한다.

- 선택적 보고 방지
- 외부 감사 가능성
- 향후 재현 연구 가능성

---

## 9. Anticipated Reviewer Questions (Updated)

**Q. 왜 6-arm인가?**  
A. thinking과 RAG의 순수 효과 및 상호작용을 분리 평가하기 위한 최소·충분 구조이다.

**Q. 왜 non-inferiority인가?**  
A. 교육 시스템에서는 “약간 더 나쁘지 않으면서 훨씬 효율적인” 선택이 임상적으로 타당하다.

**Q. 왜 acceptance sampling을 사용했는가?**  
A. 전체 문항에 대한 안전성 보장을 통계적으로 명확히 하기 위함이다.

---

## Summary

MeducAI의 모델 선택은:

- 보수적이고
- 투명하며
- 사전 지정되었고
- 임상 교육 연구에 정합적이다.

이는 AI 모델의 우열을 주장하기 위한 것이 아니라,  
**안전하고 재현 가능한 교육 시스템을 구축하기 위한 엔지니어링 결정**이다.

본 접근은 의학교육 연구의 모범 사례에 부합하며,  
연구 결과의 신뢰성과 해석 가능성을 강화한다.

---

### Canonical RAG Policy (Re-stated)

- `NONE`: no retrieval  
- `QA_ONLY` (default): QA fact-checking 시 제한적 허용  
- `GENERATION`: 특별한 근거 없이는 사용하지 않음

`RAG_MODE=QA_ONLY`는 재현성과 안전성의 균형을 위한 기본 설정이다.

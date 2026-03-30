### QA Methodological Checkpoints

#### (Literature-Informed QA Criteria for LLM-Generated Educational Content)

---

### 1. Assistance Quality Classification (필수)

**근거**
High-quality vs low-quality LLM assistance는 학습자 성과에 질적으로 다른 영향을 미친다 .

**QA 체크포인트**

* [ ] 해당 산출물은 어떤 assistance class에 해당하는가?

  * ☐ Text-dominant, structured, expert-like
  * ☐ Image-dominant, weakly grounded
* [ ] 이 assistance class는 사전에 정의된 ARM_CONFIGS와 일치하는가?
* [ ] QA 보고서에 assistance class가 명시되었는가?

> ⚠️ “그냥 LLM 결과”라는 표현은 QA 실패로 간주

---

### 2. Misleading Risk Assessment (Automation Bias 대응)

**근거**
저품질 LLM 도움은 비전문가에게 misleading influence를 유발할 수 있다 .

**QA 체크포인트**

* [ ] 학습자가 **틀린 확신(false confidence)**을 가질 수 있는 표현이 있는가?
* [ ] 단정적 진술이 불확실한 임상 상황에 사용되었는가?
* [ ] differential diagnosis의 **상대적 가중치**가 과도하게 강조되었는가?

→ 하나라도 Yes면 **QA revision 대상**

---

### 3. Expertise Sensitivity Check (교육 연구 핵심)

**근거**
전문의와 전공의는 LLM에 반응하는 방식이 다르다 .

**QA 체크포인트**

* [ ] 이 콘텐츠는 **target learner level**이 명시되었는가?

  * ☐ Junior resident
  * ☐ Senior resident
  * ☐ Board-level review
* [ ] 초보자에게 과도한 shortcut reasoning을 제공하지 않는가?
* [ ] “왜 틀릴 수 있는가”가 함께 설명되는가?

---

### 4. Repeatability Risk Flag (VLM 변동성 대응)

**근거**
Image-only 또는 weakly structured input은 반복 실행 간 변동성이 크다 .

**QA 체크포인트**

* [ ] 이 콘텐츠는 **text-first artifact**인가?
* [ ] 이미지가 핵심 정보를 대체하지 않는가?
* [ ] 동일 RUN_TAG 재실행 시 의미 변동 가능성이 있는가?

→ 변동 가능성 높으면 `REPEATABILITY_RISK = HIGH` 플래그

---

### 5. Scope Alignment Check (임상 vs 교육 구분)

**근거**
현존 연구들은 iterative clinical reasoning을 완전히 반영하지 못함 .

**QA 체크포인트**

* [ ] 이 콘텐츠는 **교육용 scaffold**임이 명확한가?
* [ ] 실제 임상 의사결정처럼 오해될 수 있는 표현은 없는가?
* [ ] “clinical decision support”로 오인될 소지는 없는가?

---

## 5. 이 QA 문서가 주는 전략적 이점

이 문서를 추가하면:

* ✅ QA가 “주관적 평가”가 아니라 **문헌 기반 판단**이 됨
* ✅ IRB / 리뷰어 질문:

  > “LLM이 학습자를 오도할 위험은 어떻게 관리했나?”
  > 에 **문서 하나로 대응 가능**
* ✅ RAD-25-3397, EURA 논문을 *단순 인용*이 아니라
  **운영 규칙으로 승화**시킴

---

## 6. 요약 (실행 체크리스트)

* [x] Methodological proposal → `00_Governance/`
* [x] QA 반영 규칙 → `05_Pipeline_and_Execution/`
* [ ] QA template에 위 5개 checkpoint 반영
* [ ] S0 QA 결과 보고서에 assistance class / misleading risk 포함
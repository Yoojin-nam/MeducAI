# S0 QA 설문 문항 및 답변 형식 (v2.0)

**Date:** 2025-12-20  
**Status:** Canonical (v2.0 aligned)  
**Aligned with:**
- QA Framework v2.0
- QA Evaluation Rubric v2.0
- S0 QA Form One-Screen Layout

---

## 설문 구조 개요

좌측에 PDF(테이블, 인포그래픽, 안키 카드 12장), 우측에 평가 설문을 배치하는 레이아웃으로 진행합니다.

평가는 **Set 단위**로 수행되며, 각 Set은 다음을 포함합니다:
- Master Table (또는 요약표)
- Anki 카드 12장 (6 엔티티 × 2문항)
- Infographic (있는 경우)

---

## Part A: Set 정보 (자동 입력, 읽기 전용)

다음 정보는 시스템에서 자동으로 표시됩니다:

| 항목 | 설명 |
|------|------|
| Run tag | 실행 태그 (예: S0_QA_2025-12-20) |
| Group ID | 평가 그룹 ID |
| Arm ID | 블라인딩 코드 (예: "X3", "Q7") - 실제 arm 정보는 숨김 |
| 평가자 역할 | Resident / Attending |
| 평가 시작 시간 | 자동 기록 |

---

## Part B: 카드 평가 (Primary Endpoint - NI 분석 대상)

> **평가 대상:** 이 Set에 포함된 **12장의 Anki 카드**  
> **평가 원칙:** 카드 전체를 종합하여 판단하며, 개별 카드별 점수가 아닌 **Set 전체에 대한 종합 평가**입니다.

### B1. Blocking Error (필수)

**질문:** 이 Set의 카드 중 **blocking error**가 있는가?

**답변 형식:**
- ○ **No** (blocking error 없음)
- ○ **Yes** (blocking error 있음)

**Yes 선택 시 추가 입력 (필수):**
- **Blocking Error 설명** (1줄 이내, 텍스트 입력)
  - 예: "MRI DWI 고신호를 T2 shine-through로 오해 → 진단 오류 위험"
  - 예: "폐색전증 CT에서 filling defect를 정상으로 기술"
  - 예: "뇌경색 시간 경과를 잘못 설명하여 치료 시점 판단 오류 가능"

**안내 문구 (툴팁):**
> Blocking Error란: 임상 판단 또는 시험 정답을 직접적으로 잘못 유도할 가능성이 큰 오류입니다. 의학적 사실 오류, 임상적으로 위험한 정보, 시험에서 오답을 유도할 수 있는 명백한 오류를 포함합니다.

---

### B2. Overall Card Quality (필수, Primary Endpoint)

**질문:** 이 Set의 카드 **전반적 품질**은 어떠한가?

**답변 형식:**
- ○ **1점** - 매우 나쁨
- ○ **2점** - 나쁨
- ○ **3점** - 보통
- ○ **4점** - 좋음
- ○ **5점** - 매우 좋음

**평가 가이드:**
> 다음 항목들을 **종합적으로 고려**하여 평가하세요:
> - 정확성 (의학적 사실성)
> - 가독성 (명확성, 구조적 이해 용이성)
> - 교육 목표 부합성 (영상의학과 전문의 시험 및 수련 목표)
> 
> 개별 카드의 점수를 평균내는 것이 아니라, **Set 전체의 종합적 품질**을 평가합니다.

**참고:**
- 본 지표는 **S0 Non-inferiority 분석의 Primary Endpoint**로 사용됩니다.
- Reference Arm (E)와 비교하여 Δ = 0.5 이내의 차이를 허용합니다.

---

### B3. Evidence Comment (조건부, 선택)

**작성 조건:**
- B1 = Yes (blocking error 있음) **또는**
- B2 ≤ 2 (Overall Card Quality가 2점 이하)

**위 조건에 해당하지 않으면:** 본 항목을 건너뜁니다.

**작성 시:**

**질문:** 문제가 있는 카드에 대한 구체적 근거를 제시해주세요.

**답변 형식:** 텍스트 입력 (최악 1–2장에 대한 근거, 각 1줄 이내)

**예시:**
```
카드 #3: 뇌경색 조영 증강 패턴 설명이 부정확함
카드 #7: 폐결절 크기 기준을 잘못 기술
```

**제한사항:**
- 최악 1–2장만 작성 (모든 카드를 검토할 필요 없음)
- 각 근거는 1줄 이내
- 조건에 해당하지 않으면 코멘트 작성하지 않음

---

## Part C: 테이블 및 다이어그램 및 인포그래픽 안전성 게이트

> **평가 대상:** Master Table, Diagram, 및 Infographic  
> **시간 상한:** Set당 약 90초–2분  
> **원칙:** Yes일 때만 1줄 근거 작성. No면 코멘트 작성하지 않음.
> **⚠️ 중요:** 테이블, 다이어그램, 인포그래픽은 **동일한 기준**으로 평가합니다.

### C1. Critical Error (치명 오류)

**질문:** 테이블, 다이어그램, 또는 인포그래픽에 **치명 오류**가 있는가?

**답변 형식:**
- ○ **No** (치명 오류 없음)
- ○ **Yes** (치명 오류 있음)

**Yes 선택 시 추가 입력 (필수):**
- **Critical Error 설명** (1줄 이내, 텍스트 입력)
  - 예: "PE CT 소견에서 filling defect를 정상으로 기술"
  - 예: "뇌경색 시간 경과별 소견 순서가 잘못되어 있음"
  - 예: "조영제 사용 금기 환자 조건을 누락"

**안내 문구:**
> Critical Error란: 테이블/다이어그램/인포그래픽에서 임상 판단이나 학습을 심각히 왜곡할 수 있는 사실 오류를 의미합니다.

---

### C2. Scope / Alignment Failure (스코프 불일치)

**질문:** 테이블, 다이어그램, 또는 인포그래픽이 **Group Path / objectives와 명백히 불일치**하는가?

**답변 형식:**
- ○ **No** (불일치 없음)
- ○ **Yes** (불일치 있음)

**Yes 선택 시 추가 입력 (필수):**
- **Scope Failure 설명** (1줄 이내, 텍스트 입력)
  - 예: "뇌 MRI 그룹에 복부 CT staging 내용 혼입"
  - 예: "흉부 CT 그룹인데 골격계 해부학 내용 포함"
  - 예: "소아 영상 그룹인데 성인 기준만 제시"

**안내 문구:**
> Scope Failure란: 해당 Group의 교육 목표(Group Path/objectives)와 명백히 맞지 않는 내용이 포함된 경우를 의미합니다.

---

### C3. Gate Result (자동 계산, 표시용)

다음은 시스템에서 자동으로 계산되어 표시됩니다:

| 결과 | 조건 |
|------|------|
| **PASS** | C1 = No **그리고** C2 = No |
| **FAIL** | C1 = Yes **또는** C2 = Yes |

**참고:**
- Gate FAIL이어도 카드 점수(B 섹션)는 그대로 유효합니다.
- 테이블/인포그래픽은 수정 플래그만 기록되며, NI 분석에는 영향을 주지 않습니다.

---

## Part D: 보조 평가 항목 (Secondary Outcomes, 선택)

다음 항목들은 **secondary outcome**으로 기록되며, descriptive analysis에 사용됩니다.

### D1. Clarity & Readability (선택)

**질문:** 이 Set의 카드가 학습자 관점에서 얼마나 **명확하고 읽기 쉬운가**?

**답변 형식:**
- ○ **1점** - 혼란·오해 가능성 높음
- ○ **2점** - 구조 불량
- ○ **3점** - 이해 가능하나 개선 필요
- ○ **4점** - 명확하고 잘 정리됨
- ○ **5점** - 매우 명확, 학습 친화적

**평가 가이드:**
> 다음을 고려하세요:
> - 용어 사용의 명확성
> - 문장 구조와 가독성
> - 정보 구조화 수준
> - 학습자가 이해하기 쉬운가?

---

### D2. Clinical / Exam Relevance (선택)

**질문:** 이 Set의 카드가 **영상의학과 전문의 시험 및 수련 목표**에 얼마나 부합하는가?

**답변 형식:**
- ○ **1점** - 시험과 거의 무관
- ○ **2점** - 낮은 관련성
- ○ **3점** - 보통 수준
- ○ **4점** - 높은 시험 적합성
- ○ **5점** - 핵심 고빈도 시험 주제

**평가 가이드:**
> 다음을 고려하세요:
> - 전문의 시험에서 출제 가능성
> - 임상 수련에 필요한 내용인가?
> - 교육 커리큘럼 목표와의 부합성

---

### D3. Editing Time (필수, Secondary Outcome)

**질문:** 이 Set을 **"배포 가능한 수준"**으로 만드는 데 필요한 **편집 시간**은 얼마나 소요되겠습니까?

**답변 형식:** 숫자 입력 (분 단위, 정수 또는 소수점 첫째 자리까지)

- 입력 예: `0`, `1`, `2.5`, `3`, `5`, `10` 등

**평가 가이드:**
> 다음을 고려하세요:
> - 카드 내용의 사실 오류 수정 시간
> - 표현/가독성 개선 시간
> - 구조 재정리 시간
> - **실제 편집을 수행하지 않고 추정**하셔도 됩니다.
> - 편집이 전혀 필요 없다고 판단되면 **0분**을 입력하세요.

**참고:**
- 본 지표는 **secondary outcome**이며, decision criteria에서 비열등 arm들 간 선택 시 사용됩니다.
- Primary endpoint (Overall Card Quality)는 그대로 유지됩니다.
- Self-reported 추정값이므로, 정확도를 최대한 유지하되 완벽한 정확도는 요구하지 않습니다.

---

## Part E: 평가 시간 (선택, 운영 검증용)

**질문:** 본 Set 평가에 실제로 소요된 시간은?

**답변 형식:**
- ○ **5분 미만**
- ○ **5–7분**
- ○ **7–10분**
- ○ **10분 초과**

**참고:**
- 본 항목은 운영 가정 검증용이며, 통계 분석에는 포함되지 않습니다.
- 목표 시간: Set당 약 10분

---

## Part F: 제출

모든 필수 항목을 입력한 후 **제출** 버튼을 클릭합니다.

**필수 항목 체크:**
- ✓ B1. Blocking Error (Yes/No)
- ✓ B2. Overall Card Quality (1–5)
- ✓ D3. Editing Time (분 단위)
- ✓ C1. Critical Error (Yes/No)
- ✓ C2. Scope Failure (Yes/No)

**조건부 필수 항목:**
- B1 = Yes 또는 B2 ≤ 2인 경우: B3. Evidence Comment 필수
- C1 = Yes인 경우: Critical Error 설명 필수
- C2 = Yes인 경우: Scope Failure 설명 필수

---

## 평가 시 주의사항

### ⚠️ 금지 사항

평가자는 다음을 **추론하거나 고려해서는 안 됩니다:**

- ❌ 모델 종류 (Gemini, GPT 등)
- ❌ 벤더/회사 정보
- ❌ 비용 정보
- ❌ Arm 배치 정보
- ❌ Prompt 설계
- ❌ Generation 전략

**평가는 콘텐츠 자체 품질에만 집중해야 합니다.**

---

### ✅ 평가 원칙

1. **블라인딩 준수**
   - Arm ID는 블라인딩 코드만 표시됩니다
   - 실제 모델/설정 정보는 알 수 없습니다

2. **종합 평가**
   - 개별 카드의 세부사항보다는 **Set 전체의 품질**을 평가합니다
   - 최악 1–2장만 상세히 검토하면 충분합니다

3. **효율성**
   - Set당 약 10분을 목표로 합니다
   - 테이블/인포그래픽은 빠르게 검토 (90초–2분)

4. **일관성**
   - 평가 기준표(Rubric)를 참고하여 일관되게 평가합니다
   - 모호한 경우, Attending은 safety 판단을, Resident는 clarity/usability 판단을 우선합니다

---

## 데이터 저장 필드명

설문 응답은 다음과 같은 필드명으로 저장됩니다:

| 필드명 | 데이터 타입 | 설명 |
|--------|------------|------|
| `blocking_error` | boolean | B1. Blocking Error (Yes/No) |
| `blocking_error_comment` | string | B1 Yes 시 설명 (조건부) |
| `overall_card_quality` | integer (1-5) | B2. Overall Card Quality |
| `evidence_comment` | string | B3. Evidence Comment (조건부) |
| `table_info_critical_error` | boolean | C1. Critical Error (Yes/No) |
| `table_info_critical_comment` | string | C1 Yes 시 설명 (조건부) |
| `table_info_scope_failure` | boolean | C2. Scope Failure (Yes/No) |
| `table_info_scope_comment` | string | C2 Yes 시 설명 (조건부) |
| `table_info_gate_result` | string | C3. Gate Result (PASS/FAIL, 자동 계산) |
| `editing_time_min` | float | D3. Editing Time (분 단위, 필수) |
| `clarity_score` | integer (1-5) | D1. Clarity & Readability (선택) |
| `relevance_score` | integer (1-5) | D2. Clinical/Exam Relevance (선택) |
| `actual_time_bucket` | string | E. Actual Time (선택) |

---

## 역할별 평가 가이드

### Attending Physician (전문의)

**주요 역할:**
- **Safety authority** - Blocking error 판정의 최종 권한
- 임상적·시험적 적합성의 기준점(anchor) 역할

**평가 우선순위:**
1. B1. Blocking Error 판정 (Safety-critical)
2. B2. Overall Card Quality (전문가 관점)
3. C1/C2. Table/Infographic Critical Error 판정

---

### Resident (전공의)

**주요 역할:**
- **Usability / clarity evaluator** - 학습자 관점 평가
- Overall card quality 평가의 주 담당

**평가 우선순위:**
1. B2. Overall Card Quality (학습자 관점 종합 평가)
2. D1. Clarity & Readability (가독성 평가)
3. D2. Clinical/Exam Relevance (교육 목표 부합성)

---

## FAQ

**Q1. 모든 카드를 상세히 검토해야 하나요?**  
A: 아닙니다. Set 전체를 빠르게 검토하고, 문제가 있는 경우 최악 1–2장만 상세히 기록하면 됩니다.

**Q2. Blocking Error와 Critical Error의 차이는?**  
A: Blocking Error는 **카드**의 오류, Critical Error는 **테이블/인포그래픽**의 오류입니다. 둘 다 safety-critical이지만 평가 대상이 다릅니다.

**Q3. Overall Card Quality를 어떻게 판단하나요?**  
A: 정확성, 가독성, 교육 목표 부합성을 **종합적으로 고려**하여 Set 전체의 품질을 평가합니다. 개별 카드 점수의 평균이 아닙니다.

**Q4. Secondary outcomes (D1, D2)는 반드시 입력해야 하나요?**  
A: 선택 사항입니다. 하지만 가능하면 입력해주시면 분석에 도움이 됩니다.

**Q5. 평가 시간이 10분을 초과해도 되나요?**  
A: 네, 문제없습니다. 10분은 목표 시간이며, 정확한 평가가 우선입니다.

**Q6. Editing Time을 어떻게 추정하나요?**  
A: 실제 편집을 수행하지 않고 추정하셔도 됩니다. 이 Set을 "배포 가능한 수준"으로 만들기 위해 필요한 시간을 분 단위로 입력하세요. 편집이 필요 없다고 판단되면 0분을 입력하세요.

---

## 참고 문서

- QA Framework v2.0
- QA Evaluation Rubric v2.0
- S0 QA Form One-Screen Layout
- QA Assignment Plan v2.0

---

**Canonical Statement:**

> 본 설문 문항 및 답변 형식은 MeducAI QA Framework v2.0과 QA Evaluation Rubric v2.0에 정합되도록 설계되었으며, S0 Non-inferiority 분석의 primary endpoint (Overall Card Quality)와 safety hard gate (Blocking Error)를 중심으로 구성되었습니다.


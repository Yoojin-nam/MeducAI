# S0 QA Form — One-Screen Layout (Canonical)

## A. Set Metadata (자동/읽기 전용)

* **Run tag**
* **Group ID**
* **Arm ID**
* **Evaluator role**: Resident / Specialist
* **Timestamp (auto)**

---

## B. Card Evaluation (Primary Endpoint — NI 분석 대상)

> **평가 대상:** 이 set에 포함된 카드 **6엔티티 × 2문항 = 12 cards**
> **원칙:** 점수는 카드 전체를 종합해 빠르게 판단.
> **코멘트는 “최악 1–2장”만 근거 작성(그 외 코멘트 금지).**

### B1. Blocking Error (필수, Yes/No)

**질문:** 이 set의 카드 중 **blocking error**가 있는가?

* **Yes / No**

**Yes일 때만 (필수, 1줄):**

* `blocking_error_comment`

  * 예: “MRI DWI 고신호를 T2 shine-through로 오해 → 진단 오류 위험”

> 정의 요약(툴팁):
> *blocking error = 임상 판단/시험 정답을 직접적으로 잘못 유도할 가능성이 큰 오류*

---

### B2. Overall Card Quality (필수, 단일 점수)

**질문:** 이 set의 카드 **전반적 품질**은 어떠한가?

* **1–5 Likert**

  * 1 매우 나쁨 / 2 나쁨 / 3 보통 / 4 좋음 / 5 매우 좋음

> 안내: 세부 항목(정확성/가독성/교육목표)을 **종합 판단**으로 반영

---

### B3. Evidence Comment (조건부)

* **작성 조건:**

  * B1=Yes 이거나, B2 ≤ 2 인 경우만
* **내용:** 최악 카드 **1–2장**에 대한 근거(각 1줄 이내)

---

## C. Table & Diagram & Infographic Safety Gate

*(Secondary — 점수화 ❌, NI 통계 ❌, 위험 기반 게이트 ⭕)*

> **시간 상한:** set당 **90초–2분**
> **원칙:** Yes일 때만 1줄 근거. No면 코멘트 금지.
> **⚠️ 중요:** 테이블, 다이어그램, 인포그래픽은 **동일한 기준**으로 평가합니다.

### C1. Critical Error (치명 오류) — Yes/No

**질문:** 테이블, 다이어그램, 또는 인포그래픽에 **치명 오류**가 있는가?

* **Yes / No**

**Yes일 때만 (필수, 1줄):**

* `table_info_critical_comment`

  * 예: "PE CT 소견에서 filling defect를 정상으로 기술"

---

### C2. Scope / Alignment Failure (스코프 불일치) — Yes/No

**질문:** 테이블, 다이어그램, 또는 인포그래픽이 **Group Path / objectives와 명백히 불일치**하는가?

* **Yes / No**

**Yes일 때만 (필수, 1줄):**

* `table_info_scope_comment`

  * 예: "뇌 MRI 그룹에 복부 CT staging 내용 혼입"

---

### C3. Gate Result (자동 계산)

* **PASS:** C1=No AND C2=No
* **FAIL:** C1=Yes OR C2=Yes
  *(FAIL이어도 카드 점수는 그대로 유효. 테이블/인포는 수정 플래그만 기록)*

---

## D. Time Check (권장, 선택)

* **Actual time spent (self-reported):**

  * `<5분 / 5–7분 / 7–10분 / >10분`

> 운영 가정 검증용(분석에는 미포함)

---

## E. Submission

* **Submit**

---

# 필드명 요약 (데이터/로그용)

* `blocking_error` (Y/N)
* `blocking_error_comment`
* `overall_card_quality` (1–5)
* `evidence_comment`
* `table_info_critical_error` (Y/N)
* `table_info_scope_failure` (Y/N)
* `table_info_gate_result` (PASS/FAIL)
* `table_info_comment`
* `actual_time_bucket`

---

## 운영 포인트(중요)

1. **Primary NI 분석**: B섹션만 사용
2. **MI-CLEAR-LLM 근거**: C섹션은 *위험 기반 게이트*로만 사용
3. **부담 통제**:

   * 테이블/인포는 Yes/No만
   * 코멘트는 조건부
   * 한 화면 스크롤 최소화
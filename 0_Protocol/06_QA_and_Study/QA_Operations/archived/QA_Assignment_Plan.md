---

# QA Assignment Plan – MeducAI (v2.0, Canonical)

**Aligned with:**

* QA Framework v2.0
* QA Evaluation Rubric v2.0
* QA Blinding Procedure v2.0

**Date:** 2025-12-15
**Status:** Canonical (applies prospectively to S0 & S1)

---

## 0. Purpose

본 문서는 **MeducAI Pipeline-1 QA (Step S0, Step S1)**에서
평가자의 **배정(assignment) 원칙, 수, 역할, 통계적 정당성**을 사전에 고정하기 위한
**공식 QA Assignment Plan**이다.

본 계획의 목적은 다음과 같다.

* QA Framework v2.0에서 정의된 **unit of analysis(S0: Set, S1: Card)**에 정합된 배정
* Safety-critical 판단과 usability 평가의 **역할 분리**
* Inter-Rater Reliability(IRR) 산출이 가능한 **최소·충분 배정**
* Reviewer 부담과 편향을 동시에 최소화

---

## 1. QA Panel Composition (v2.0 Aligned)

QA 패널은 **역할 기반(role-based)**으로 구성되며,
S0와 S1에서 **배정 구조가 명확히 다르다**.

### 1.1 Attending Physicians (Board-Certified Radiologists)

**Role:** Safety authority / clinical anchor

* Blocking error(Accuracy = 0.0) 판정의 최종 권한
* 임상적·시험적 적합성 판단의 기준점(anchor)

> S0: Set 단위 cross-evaluation
> S1: Adjudication 및 IRR anchor 평가

---

### 1.2 Radiology Residents (Senior Trainees)

**Role:** Usability / clarity evaluators

* Clarity, readability 평가
* Overall card quality 평가 담당
* S1에서 primary independent reviewers

---

## 2. Assignment Structure by Step

### 2.1 Step S0 – Model Selection QA

#### Unit

* **Set** (= group × arm artifact bundle)

#### Assignment Rule (Fixed)

* **Per set:**
  **2-person paired cross-evaluation**

  * **1 Resident**
  * **1 Attending**

#### Rationale

* Safety 판단을 1차 평가에 내재화
* Overall card quality(Primary endpoint)을 실제 사용자(Resident) 기준으로 평가
* 전문성 차이를 secondary outcome(EDI)으로 정량화 가능

> ❗ v1.0의 “3 reviewers per artifact” 구조는
> S0 목적(비교·최적화)에는 **과잉이며 비효율적**이므로 폐기됨.

---

### 2.2 Step S1 – Release Gate QA

#### Unit

* **Card** (개별 Anki 문항)

#### Assignment Rule (Fixed)

##### ① Primary Review

* 모든 sampled cards (n = 838)
* **Residents 2인 독립 평가**

  * 총 review actions = 2 × 838

##### ② IRR Anchor Subsample

* **m = 300 cards**
* **3-person evaluation**

  * Resident 2 + Attending 1

##### ③ Adjudication

* 다음 조건 중 하나라도 충족 시:

  * Resident 중 누구라도 Accuracy = 0.0
  * Accuracy 점수 불일치
* **Attending이 최종 판정**

---

## 3. Reviewer Allocation & Workload

### 3.1 Step S0 Workload (Canonical)

* Total sets: **108 sets**
* Evaluation target: **~10 min per set**

| Role      | Sets per person (approx.) |
| --------- | ------------------------- |
| Resident  | 12–15 sets                |
| Attending | 12–15 sets                |

> S0는 **깊이 있는 평가 + 짧은 기간 집중 수행**을 전제로 함

---

### 3.2 Step S1 Workload (Canonical)

| Role      | Expected Time       |
| --------- | ------------------- |
| Resident  | ~3–4 hours / person |
| Attending | ~40–60 min / person |

> Time cost 증가를 허용하고,
> **통계적 보장과 안전성**을 최우선으로 함 (QA Framework v2.0 원칙)

---

## 4. Assignment Constraints (Bias Control)

### 4.1 Subspecialty De-correlation

* 가능하면 **본인 주 subspecialty group은 배정 제외**
* 불가피한 경우:

  * QA audit log에 명시

---

### 4.2 Institution De-correlation

* 동일 artifact에:

  * **동일 기관 reviewer 2인 이상 배정 금지**
* 예외 발생 시:

  * 사유 기록 및 sensitivity analysis 고려

---

## 5. Randomization & Mapping Control

* Assignment는 다음 절차로 수행된다.

1. 사전 고정된 assignment algorithm
2. 역할·기관·subspecialty 제약 반영
3. Random seed 기록
4. Reviewer-artifact mapping 파일 생성

* Mapping 파일은:

  * QA 운영자만 접근 가능
  * Reviewers에게 절대 공유되지 않음

---

## 6. Blinding Enforcement

본 assignment는 **QA Blinding Procedure v2.0** 하에서 수행된다.

* Reviewers는:

  * model
  * provider
  * arm
  * generation 설정
    을 알 수 없음
* Assignment ID는 **surrogate ID**만 사용

---

## 7. Statistical Justification (v2.0)

### 7.1 S0

* Paired design (Resident–Attending)
* Secondary analyses:

  * Expertise Discrepancy Index (EDI)
  * Disagreement rate
  * Role × Arm interaction (exploratory)

### 7.2 S1

* 2-rater independent review → sensitivity 확보
* 3-rater anchor → IRR 안정적 추정
* Metrics:

  * Accuracy: **Fleiss’ κ**
  * Likert: **Weighted κ**

---

## 8. Documentation & Audit Trail

For each assignment, the following are logged:

* reviewer_id (coded)
* role (resident / attending)
* institution
* subspecialty
* assigned unit (set_id or card_id)
* timestamps

Logs are stored as part of the **QA audit package**.

---

## 9. Versioning & Freeze Policy

* 본 문서는 **QA Assignment Plan v2.0 (Canonical)**이다.
* S0/S1 실행 중 수정 불가.
* 변경 필요 시:

  * v2.1로 상향
  * 변경 사유 명시
  * QA 시작 이전에만 적용 가능

---

## Official Statement

> This assignment plan defines a role-aware, statistically defensible reviewer allocation strategy for MeducAI Pipeline-1 QA (S0/S1), ensuring safety-critical judgment, efficiency optimization, and unbiased release decisions under full blinding.

---

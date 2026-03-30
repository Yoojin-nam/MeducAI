# MeducAI QA Framework v2.0 (Final)

**Subtitle:** Two-Stage QA for Deployment Freeze and Full-Scale Release: 6-Arm Factorial (S0) + One-shot Acceptance Sampling (S1)
**Date:** 2025-12-15
**Status:** Canonical (Final; to be Frozen after S1 PASS)
**Scope:** Pipeline-1 QA Only (Paper-1: S0 Non-inferiority; S1 Full-scale Quality Gate)

---

## 0. Definitions (Canonical)

### 0.1 Units

* **Objective:** 원시 교육목표 단위
* **Group:** EDA 기반 교육 개념 단위(그룹핑 규칙에 따라 생성된 최소 배포 단위)
* **Set (S0 unit of analysis):** **group × arm** 결과물 묶음(= artifact bundle)

  * 포함: Master Table(또는 요약표), 평가용 Anki payload(고정 12장), 필요 시 이미지/인포그래픽
* **Card (S1 unit of analysis):** 개별 Anki 문항(Front/Back/Meta 포함)

### 0.2 Error Taxonomy

* **Blocking error:** 배포 불가 수준의 의학적 오류 또는 안전성 위반

  * S0/S1 공통으로 **Accuracy = 0**과 동치로 취급
* **Non-blocking issue:** 표현/가독성/부분 누락 등 수정으로 해결 가능한 결함

### 0.3 Roles

* **Attending (전문의):** safety-critical 판단 권위(최종 판단권, 임상적 적합성 기준점)
* **Resident (전공의):** usability/clarity 평가 담당

---

## 1. Executive Summary (Decision-ready)

본 프레임워크는 **벤더 비교**가 아니라, **단일 Deployment Model을 고정(Freeze)**하고 대규모 생성본을 **배포 승인(PASS)**하기 위한 2단계 QA이다.

* **Step S0 (Paper-1):** 6-arm factorial 설계로 **모델 선택 및 Freeze 근거** 확보

  * Safety hard-gate + Quality-based non-inferiority 검증
  * 저비용 arm 선택 시 **Non-inferiority(Δ)로 정당화**
  * 전문성 쌍(Resident–Attending) 배치로 **secondary outcome(전문성 차이/보정) 생성**

* **Step S1 (Release gate):** Freeze된 모델로 생성된 전체 카드(≈6,000–12,000)에 대해

  * **card-level blocking error rate < 1%**를 **one-sided 99%**로 보장하는 **one-shot acceptance sampling**
  * PASS 시 배포 승인 및 최종 Freeze

---

## 2. Step S0 — Paper-1 Expert QA (Non-inferiority-oriented)

### 2.1 Purpose

Step S0는 6-arm 실험을 통해 **단일 Deployment Model**을 선정하고, 이후 전체 생성에서 **설정 변경 금지**가 가능한 근거(Methods/Discussion)를 확보한다.

### 2.2 Arm Configuration (Fixed)

| Arm | ID        | Model             | Thinking | RAG | Role                 |
| --- | --------- | ----------------- | -------- | --- | -------------------- |
| A   | Baseline  | Flash (Low)       | OFF      | OFF | 최소 기준점               |
| B   | RAG Only  | Flash (Low)       | OFF      | ON  | 검색 효과                |
| C   | Thinking  | Flash (Low)       | ON       | OFF | 추론 효과                |
| D   | Synergy   | Flash (Low)       | ON       | ON  | 저비용 풀옵션              |
| E   | High-End  | Pro v3 (High)     | ON       | OFF | 고성능 기준(Closed-book)  |
| F   | Benchmark | GPT-5.2 (Max) | ON       | OFF | 외부 벤치마크(Closed-book) |

**Fairness invariant:** Arm E/F는 **RAG OFF**로 고정하여 모델 자체 지능을 비교한다.

### 2.3 Sampling Strategy (Fixed)

#### 2.3.1 Sampling Unit

* **Group** 단위로 선정하고, 각 group에 대해 6 arms 결과물을 생성하여 **Set**을 구성한다.

#### 2.3.2 Sample Size

* **Paper-1 Canonical:** **18 groups × 6 arms = 108 sets**

#### 2.3.3 18-Group Selection Rule (Canonical)

**Two-stage selection:**

1. **Stage 1: Minimum Coverage Guarantee**
   * 각 specialty에서 weight가 가장 높은 그룹 1개씩 선택
   * 결과: 11개 그룹 (모든 specialty 포함)

2. **Stage 2: Weight-Based Selection**
   * Stage 1에서 선택된 그룹 제외
   * 나머지 그룹을 weight 기준으로 정렬 (높은 순)
   * 상위 7개 선택
   * 결과: 7개 그룹

**Total:** 18 groups (11 + 7 = 18)

**Constraints:**
* 모든 11개 specialty 포함 (자동으로 ≥6 subspecialties 충족)
* Weight 기반 선택으로 교육적 중요도 반영
* Tie-break: seed 고정 난수

**Reference:** `0_Protocol/06_QA_and_Study/QA_Operations/S0_18Group_Selection_Rule_Canonical.md`

### 2.4 Evaluation Payload (Fixed)

* **12 cards per set (고정)**
* Card-type mix 고정 (Basic/MCQ/Cloze)
* 목적: arm 간 workload 표준화 및 결과 분산 감소

### 2.5 Panel Assignment (Paired Cross-evaluation; Fixed)

* **Unit:** Set (= group × arm artifact bundle)
* **Per-set evaluation:** **2-person cross-evaluation**
* **Pairing constraint (fixed):** **1 Resident + 1 Attending** per set

  * 목적: (i) safety-critical judgment를 1차 평가에 내재화
    (ii) 전문성(Resident vs Attending) 차이를 정량화하여 secondary outcome으로 보고

**Role split**

* **Attending (Safety authority within the pair):**

  * Blocking error(accuracy=0) 판정에 준하는 권위 부여
  * 임상적 적합성/수험 부합성 평가의 기준(anchor) 역할
* **Resident (Usability/clarity evaluator):**

  * 학습자 관점 명확성 및 가독성 중심 평가

**Workload assumption (canonical):** set당 10분 평가(기본)

### 2.6 Outcomes & Measurement

#### 2.6.1 Primary endpoints

1. **Safety (Hard Gate):**

* **Card-level blocking error rate ≤ 1%** (S0 내 생성 카드 기준)
* 초과 시 해당 arm **즉시 탈락**

#### 2.6.2 Secondary outcomes

* Mean Accuracy Score (0/0.5/1) — **used for non-inferiority analysis (primary endpoint)**
* Overall Card Quality (Likert 1–5) — **descriptive/exploratory**
* Editing Time (minutes per set) — **self-reported via survey, used for decision criteria**
* Clarity & Readability (Likert 1–5)
* Clinical/Exam Relevance (Likert 1–5)
* Cost per set (USD, logged counters 기반 후계산)
* Latency (sec)

### 2.7 Non-Inferiority Framework (Two-Layer Decision Framework)

**Canonical Reference:** `0_Protocol/06_QA_and_Study/QA_Operations/S0_Noninferiority_Criteria_Canonical.md`

본 프레임워크는 S0의 **고정 12-card payload**에 맞게 설계된 **two-layer decision framework**를 사용합니다:

#### 2.7.1 Layer 1: Safety Endpoint (Gatekeeper)

**Purpose:** Mean score NI pass에도 불구하고 major error (0-score cards)의 허용 불가능한 증가를 방지

* **Metric:** Major error rate (proportion of cards scored 0)
* **Notation:**
  - `p0_T` = proportion of 0-score cards in candidate arm T
  - `p0_A` = proportion of 0-score cards in baseline arm A
  - `RD0` = `p0_T - p0_A` (risk difference, absolute)
* **Safety Pass Criterion:**
  - Compute one-sided upper bound via two-sided 95% CI for `RD0`
  - **Safety PASS if:** `UpperCI(RD0) ≤ +0.02`
  - **Interpretation:** Candidate must not increase 0-score rate by more than **2 percentage points**, with 95% confidence
* **Rationale:** A 2%p increase in 0-score rate on a 12-card set ≈ 0.24 additional major errors per set (operationally acceptable)

#### 2.7.2 Layer 2: Primary NI Endpoint (Non-Inferiority Test)

**Purpose:** Determine if candidate arm is non-inferior to baseline on mean accuracy score

* **Baseline Arm:** **Arm A (Baseline, Flash Low)** — default configuration
  * **Alternative:** Arm E (High-End) can be configured as reference if needed
  * **Note:** Arm E (High-End) is recommended as reference for vendor consistency (see `Reference_Arm_Recommendation.md`), but implementation defaults to Arm A for operational simplicity
* **Endpoint:** **Mean Accuracy Score** (card-level accuracy 0/0.5/1 averaged across all cards in the set)
* **Notation:**
  - `mean_T` = mean accuracy in candidate arm T
  - `mean_A` = mean accuracy in baseline arm A
  - `d` = `mean_T - mean_A` (difference)
* **Non-Inferiority Margin (Δ):**
  - **Default:** Δ = 0.05 (mean score scale)
  - **Configuration options:**
    - Conservative: Δ = 0.03 (stricter, for high-stakes decisions)
    - Default: Δ = 0.05 (recommended, balances rigor and practicality)
    - Cost-driven: Δ = 0.08 (more permissive, for cost optimization scenarios)
  - **Rationale:** On a 12-card set, Δ = 0.05 implies allowing up to **0.6 points degradation** (≈ 1 card dropping from 1.0 to 0.4, or 2 cards from 0.5 to 0.0). This is educationally meaningful and statistically defensible. Larger Δ values (0.5, 1.0) are **invalid** for S0 because they would allow 6–12 points per set degradation.
* **Hypothesis:**
  - H0: `d ≤ -Δ` (candidate is inferior)
  - H1: `d > -Δ` (candidate is non-inferior)
* **Decision Rule:**
  - Compute CI for `d` (difference in mean accuracy)
  - **NI PASS if:** `LowerCI(d) > -Δ`
  - **NI FAIL if:** `LowerCI(d) ≤ -Δ`
* **CI Level:**
  - **Default:** 90% two-sided CI (operational one-sided α = 0.05) for S0 selection
  - **Stricter option:** 95% two-sided CI (one-sided α = 0.025) for high-stakes scenarios

#### 2.7.3 Statistical Method

* **Primary Implementation:** Clustered paired bootstrap
  - **Unit of resampling:** `(rater_id, group_id)` pairs
  - For each bootstrap replicate:
    1. Sample `(rater_id, group_id)` pairs with replacement
    2. For each arm: compute mean accuracy and `p0` within sampled pairs
    3. Compute `d` and `RD0` vs baseline A
  - **CI construction:** Percentile CI
  - **Fixed seed:** Default = 20251220 (configurable)

**Interpretation:**

* NI 성립 → 저비용 arm이 baseline에 비열등
* NI 미성립 → "열등"이 아니라 **통계적 미입증(inconclusive)**

**Note:** Arm F (GPT-5.2)는 external benchmark/anchor로서 유지되지만, primary non-inferiority 비교의 baseline은 Arm A (default) 또는 Arm E (alternative)입니다.

### 2.8 Secondary Outcomes Enabled by Expertise-paired Design (NEW)

본 설계(Resident–Attending pairing)는 아래 secondary outcome을 추가 비용 없이 산출 가능하게 한다.

1. **Expertise Discrepancy Index (EDI)**

* 정의: (Attending score − Resident score)의 평균/분산
* 대상: Accuracy(0/0.5/1), Likert(1–5)
* 해석: 전공의의 과대/과소평가 경향 및 calibration 정량화

2. **Disagreement Rate**

* 정의: pair 불일치 비율

  * Accuracy 불일치율
  * Likert 차이 ≥ 2 비율(운영 가능 시)
* 해석: 모호한 콘텐츠(표현/임상적 적합성)의 분포를 반영

3. **Blocking Flag Concordance (Exploratory)**

* 정의: Resident blocking flag와 Attending 판정의 정합성(민감도/특이도; exploratory)
* 해석: 전공의 기반 1차 필터의 신뢰성 평가

4. **Role × Arm Interaction (Exploratory)**

* 정의: 역할(Resident vs Attending)과 Arm의 상호작용
* 예: 특정 Arm에서 “전공의는 수용, 전문의는 더 엄격”한 패턴 존재 여부

**Recommended analysis note (brief):**

* Mixed-effects model (exploratory): outcome ~ arm + role + arm×role + (1|group) + (1|rater)
* Secondary outcomes are descriptive/exploratory and do not override the primary non-inferiority decision logic.

### 2.9 Instrumentation & Logging (S0)

**Per set required fields (minimum):**

* Identity: group_id, arm_id, provider, model_name
* Reproducibility: prompt_id/step, prompt_hash, config snapshot(think/rag), run_tag, execution_date, git_commit(optional)
* Counters: start_ts, end_ts, latency_sec, input_tokens, output_tokens, rag_queries_count, rag_sources_count, image_calls_count
* Cost: cost_estimated_usd (후계산 가능 시 null 허용)
* QA outcomes: accuracy score, blocking flag, overall_quality_score, editing_time_min (self-reported), clarity_score, relevance_score

### 2.10 Decision Rules (S0 Deployment Freeze)

**Two-Layer Decision Framework:**

1. **Layer 1: Safety Gate (Hard Gate)**
   - **Safety PASS if:** `UpperCI(RD0) ≤ +0.02` (prevents unacceptable major error increases)
   - Safety FAIL → arm **immediately disqualified** regardless of mean score performance

2. **Layer 2: Non-Inferiority Gate**
   - **NI PASS if:** `LowerCI(d) > -Δ` (ensures non-inferiority on mean accuracy)
   - **Final PASS:** Both safety and NI must pass

3. **Selection Priority (among final_pass arms):**
   - **Primary:** **Cost minimization** (lowest API cost)
   - **Secondary:** **Editing Time minimization** (lowest self-reported editing time)
   - **Tie-break:** Latency → Stability (error rate/retry rate)

4. **Fallback Policy:**
   - 비열등 arm이 없으면: **Baseline Arm (A) 또는 Arm E (High-End) 또는 Arm F로 전체 생성 진행**

**S0 Output:** Selected Deployment Model (Arm ____) + Freeze declaration

**Implementation Reference:** `3_Code/src/tools/qa/s0_noninferiority.py`

---

## 3. Step S1 — Full-scale Generation Quality Gate (Error Rate Validation)

**Canonical Reference:** `0_Protocol/05_Pipeline_and_Execution/S1_QA_Design_Error_Rate_Validation.md`

### 3.1 Purpose

배포 모델 확정 후, 전체 생성된 Anki 문항(≈6,000문항, 향후 생성 포함)에 대해 **모집단의 Major error rate ≤ 2%**임을 **통계적으로 추론**하고 배포 승인 여부를 결정한다.

**평가 단위**: **1 item = 1 문항 (= 1 카드/문제)**

### 3.2 Quality Target & Statistical Guarantee

* **Quality target:** 모집단 Major error rate ≤ **2%**
* **Statistical guarantee:** **one-sided 95% confidence** (단측 α = 0.05)
* **Method:** Exact binomial test 또는 Clopper-Pearson 단측 상한 CI

**성공 기준 (고정):**

* Major error rate의 **단측 95% 상한(upper CI)이 2% 이하**

### 3.3 Sampling Strategy

* **모집단**: 6,000문항 (향후 추가 생성될 문항 포함)
* **표본 크기**: **n = 987 문항** (랜덤 샘플)
* **샘플링 방식**: 랜덤 표본 추출 (PPS 또는 단순 무작위)
* **배치 구성**: P01~P09 배치 (각 109~110문항)로 분할

### 3.4 Triage + Audit 설계

#### 3.4.1 Resident 2인 독립 판정 (전공의 2명)

각 item에 대해 **초단순 평가**:
* **OK / ISSUE / UNCLEAR** 중 1개 선택

**분류 규칙:**
* **(둘 다 OK)** → **"OK-합의군 (stratum OK)"**
* **(그 외: ISSUE 또는 UNCLEAR가 하나라도 있음)** → **"Flagged군 (stratum Flagged)"**

#### 3.4.2 Attending (전문의) 검토

* **Flagged군**: 전문의가 **최종 판정** (골드 스탠다드: Major/Minor 구분)
* **OK-합의군**: **무작위 300문항 audit** (고정 seed, 재현 가능)

### 3.5 사전 에스컬레이션 규칙 (데이터 수집 전 고정)

**에스컬레이션 트리거** (아래 중 하나라도 만족 시):

**A)** `e_audit_major >= 2` (Major error가 2개 이상 발견)  
**OR**  
**B)** `e_audit_total >= 10` (ISSUE 총합이 10개 이상 발견)  
**OR**  
**C)** `agreement_with_attending < 0.95` (Audit에서 일치율 <95%)

**에스컬레이션 액션:**
* Trigger 발생: OK-합의군 추가 audit 300 또는 전수 검토로 전환
* Trigger 미발생: 남은 OK-합의군은 resident OK를 최종 OK로 인정 (보수적 상한 적용)

### 3.6 통계 분석: 층화 기반 보수적 상한

**전체 오류율의 보수적 상한:**

* **Flagged군**: 전문의 전수 검토 결과 사용 (`e_flagged_major`, `e_flagged_total`)
* **OK-합의군**: Audit 300 결과에서 단측 95% 상한 `ub_ok_major`, `ub_ok_total` 계산
* **전체 상한**: `UB_total = (e_flagged + ub_ok * N_ok_total) / N_total`

**Primary endpoint**: Major error rate의 단측 95% 상한이 2% 이하

### 3.7 Reviewer Roles & Workload Allocation

* **Residents (n=9): Primary reviewers**
  * 모든 샘플 문항(**n=987**)을 **2인 독립 평가** (OK/ISSUE/UNCLEAR)
  * 총 resident review actions = **2 × 987**
  * 목표: 220문항/인 완주 가능 (배치 단위 제공)

* **Attending physicians: Authority**
  * Flagged군: 전수 검토 (최종 판정)
  * OK-합의군: Audit 300 검토 (신뢰도 추정)

### 3.8 평가 UX: 초단순 문항 평가

**Resident 입력 (전수):**
* `R?_decision`: OK / ISSUE / UNCLEAR (1개만 선택)
* `R?_issue_type`: Major / Minor / Scope / Structure / Image_dependency / Other (ISSUE/UNCLEAR일 때만)
* `R?_comment`: 선택, 한 줄 코멘트

**Educational Quality (선택, 샘플링):**
* 1~5 점수는 전수에서 제거
* 옵션: 각 batch에서 랜덤 10%만 1~5 부여 (보조 분석)

**참고:** `QA_Rater_OnePage_Checklist.md` (Ultra-Light 버전)

### 3.9 Decision & Post-Decision Policy

* **PASS**: Major error rate의 단측 95% 상한이 2% 이하
  * 배포 승인
  * Deployment model 유지(Freeze)
  
* **FAIL**: Major error rate의 단측 95% 상한이 2% 초과
  * 배포 승인 보류
  * Error 유형에 따라 (a) 국소 수정 후 재검토, 또는 (b) 모델/프롬프트 수정 후 재생성 및 재검토

---

## 4. Reporting Package (Publication-ready)

### 4.1 Paper-1 (S0) — Minimum Tables

* Arm별: N sets, blocking error rate, overall_quality(mean±SD), editing_time(mean±SD), clarity(mean±SD), relevance(mean±SD), cost(mean±SD), latency(mean±SD)
* Non-inferiority: one-sided CI vs Δ_quality, NI 성립 여부 (Reference: Arm E)
* Secondary: EDI, disagreement rate, (exploratory) role×arm interaction

### 4.2 S1 Release Gate — Minimum Tables

* 표본 정보: n=987, 모집단 N=6,000
* 층화 결과: Flagged군 vs OK-합의군 분포
* Audit 결과: e_audit_major, e_audit_total, agreement_with_attending
* 에스컬레이션 트리거 충족 여부
* 통계 분석: Major error rate의 단측 95% 상한, PASS/FAIL
* Error 유형 분포: Major/Minor/Scope/Structure/Image_dependency

---

## 5. Freeze & Versioning Policy (Final)

* 본 문서(v2.0)는 **Final canonical**이며, S0/S1 실행 중 수정 금지.
* 변경이 필요하면 **v2.1**로 상향하고 변경 로그를 남긴다.
* Freeze 정의

  * **S0 Freeze:** Deployment model(arm) 및 설정 고정
  * **S1 Freeze:** PASS 이후 배포 승인 및 최종 릴리즈 고정

---

**Official Statement (for record)**

> MeducAI Pipeline-1 QA is executed in two stages: S0 selects and freezes a single deployment configuration under safety gating and non-inferiority-aware efficiency testing; S1 validates full-scale generation safety via one-shot acceptance sampling to approve release.

## Appendix A. Human-only QA as a Canonical Baseline System

For the purpose of downstream comparative studies, the Human-only QA process used in MeducAI Pipeline-1 is explicitly defined as a canonical baseline system.

Human-only QA is operationally defined as a monolithic, non-decomposed evaluation process in which a single human reviewer (or paired human reviewers) performs the following functions in an integrated manner:
1. Detection of blocking and non-blocking errors,
2. Manual editing to reach a deployable quality threshold,
3. Final pass/fail judgment.

Human-only QA explicitly excludes:
- Content regeneration,
- Prompt modification,
- Structural redesign of generated artifacts.

This definition enables subsequent comparative studies to evaluate decomposed or multi-agent QA systems relative to a fixed human baseline, rather than an implicit or variable human practice.

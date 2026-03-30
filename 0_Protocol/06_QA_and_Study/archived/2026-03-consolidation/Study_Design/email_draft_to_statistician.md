# [Statistician] 교수님께 보낼 메일 초안

**제목:** [연구 자문 요청] MeducAI 의료 AI 교육콘텐츠 연구 - 통계 분석 설계 검토

---

[Statistician] 교수님 안녕하세요. [Study Coordinator]입니다.

이번에 의료 AI 교육콘텐츠 연구를 진행 중인데, 통계 분석 설계부터 도움을 부탁드릴 수 있을지 여쭙습니다. 

## 1. 연구 배경 및 목적

### 1.1 MeducAI 프로젝트 개요

**MeducAI**는 대형 언어 모델(LLM)을 활용한 영상의학 교육용 학습 콘텐츠(Anki 카드, 표, 시각 자료)의 체계적·재현 가능·감사 가능한 생성 시스템입니다.

**핵심 철학:**
- 콘텐츠 생성 그 자체보다, **공정한 모델 비교(QA), IRB-친화적 기록, 재현 가능한 실행**을 동시에 달성
- **LLM은 "결정(decision)"을 하지 않는다** - 카드 수, 선택, 정책은 코드와 Canonical 문서에서만 결정
- 각 단계는 고유한 책임만 가지며, 경계 침범은 즉시 실패(Fail-Fast)로 처리

### 1.2 연구 구조: Two-Pipeline 설계

본 연구는 **두 개의 분석적으로 독립적인 파이프라인**으로 구성됩니다:

- **Pipeline-1 (Paper-1): Expert QA & Deployment Model Selection**
  - 목적: 단일 배포 모델을 선정하고 안전성과 효율성을 검증
  - 구성: Step S0 (6-arm factorial QA) + Step S1 (One-shot acceptance sampling)
  
- **Pipeline-2 (Paper-2): Prospective Observational UX Study**
  - 목적: 실제 사용자(전공의)의 교육적 효과 및 사용성 평가
  - 구성: 자연스러운 사용 환경에서의 관찰 연구 (별도 진행)

**분리 원칙:** 두 파이프라인은 분석적으로 독립적이며, Pipeline-1의 결과는 배포 설정을 결정하지만 Pipeline-2의 결과 분석과는 합치지 않습니다.

### 1.3 현재 단계 및 일정

- **현재 단계:** S0 QA 자료 배포 완료, 평가 진행 중
- **목표 일정:** 1월 초 전공의 배포 목표로 촉박한 상황
- **다음 단계:** QA 결과 분석 → 모델 선정 → IRB 제출 → 배포

---

## 2. MeducAI 파이프라인 구조

### 2.1 파이프라인 단계

```
S0   : QA / Model Comparison (fixed payload, arm fairness)
S1   : Structure only (LLM, no counts) - Group-level structuring, Master Table
S2   : Execution only (LLM, exact N cards) - Q1/Q2/Q3 생성
S3   : Selection & QA gate (state-only) - Policy Resolution & Image Spec
S4   : Rendering & presentation (image only) - Image Generation (PNG rendering)
FINAL: Allocation & deployment (card counts decided here only)
```

### 2.2 Group-first Architecture

- **최소 처리 단위:** Group (312개 semantically coherent groups)
- **Group 정의:** EDA 기반 1,767개 학습 목표를 의미론적으로 통합
- **장점:** 확장 가능한 QA, 대표 샘플링, 재현 가능한 할당

---

## 3. Step S0 설계 (현재 진행 중)

### 3.1 실험 설계

**6개 Arm 비교:**
- **Arm A:** Baseline (Gemini 3 Flash Preview, Thinking OFF, RAG OFF)
- **Arm B:** RAG Only (Gemini 3 Flash Preview, Thinking OFF, RAG ON)
- **Arm C:** Thinking (Gemini 3 Flash Preview, Thinking ON, RAG OFF)
- **Arm D:** Synergy (Gemini 3 Flash Preview, Thinking ON, RAG ON)
- **Arm E:** High-End (Gemini 3 Pro Preview, Thinking ON, RAG ON) - **Reference Arm**
- **Arm F:** Benchmark (GPT-5.2, Thinking ON, RAG ON) - 외부 벤치마크

**샘플링 전략:**
- **샘플 크기:** 18 groups × 6 arms = 108 sets
- **18-Group Selection Rule:**
  - Stage 1: 각 specialty에서 weight가 가장 높은 그룹 1개씩 선택 (11개 그룹)
  - Stage 2: 나머지 그룹을 weight 기준으로 정렬하여 상위 7개 선택
  - 결과: 모든 11개 specialty 포함, 교육적 중요도 반영

**평가 단위:**
- **Set:** group × arm artifact bundle
- **Set 구성:** Master Table + Anki 카드 12장 (고정) + Infographic(해당 시)
- **고정 payload:** 각 Set당 정확히 12장의 Anki 카드로 Arm 간 공정한 비교 보장

**평가자 구조:**
- **총 평가자:** 전공의 9명 + 전문의 9명
- **평가 방식:** Set당 2인 교차평가 (1명 전공의 + 1명 전문의)
- **역할 분리:**
  - **Attending (전문의):** Safety-critical 판단 권위, Blocking error 최종 판정, 임상/시험 적합성 기준점
  - **Resident (전공의):** Usability/clarity 평가, 가독성·명확성 등 사용자 관점 평가
- **예상 소요 시간:** Set당 약 5–10분, 총 약 1시간 내외

### 3.2 통계 분석 계획 (현재 설계)

**Primary Non-Inferiority Framework (Single-Layer):**

**참고:** Blocking error (major error)는 별도의 safety gate로 운영되며, 통계 분석의 primary endpoint에는 포함되지 않습니다. Blocking error rate가 1%를 초과하는 arm은 사전에 제외됩니다.

**Primary Endpoint:**
- **Metric:** Set-level Overall Card Quality (1–5 Likert scale)
  - 각 Set에 대해 평가자가 부여한 Overall Card Quality 점수
  - 1 = 매우 나쁨 (Very Poor)
  - 2 = 나쁨 (Poor)
  - 3 = 보통 (Average)
  - 4 = 좋음 (Good)
  - 5 = 매우 좋음 (Very Good)
- **Set-level aggregation:** Multiple raters가 같은 set을 평가한 경우, rater 간 평균을 사용하여 set-level score 산출

**Baseline 및 비교:**
- **Baseline Arm:** Arm E (High-End, Gemini 3 Pro Preview)
- **Comparison:** Candidate arms (A, B, C, D) vs baseline arm (E)
- **Benchmark Arm:** Arm F (GPT-5.2)는 외부 벤치마크로 보고(reporting)만 사용되며, primary NI 결정에는 포함되지 않음

**Non-Inferiority Framework:**
- **Type:** One-sided non-inferiority
- **Margin:** Δ = 0.5 (Likert scale)
  - **Rationale:** 1–5 Likert scale에서 0.5는 한 단계의 절반 (예: 4.0 → 3.5, 또는 3.0 → 2.5)
  - 교육적으로 의미 있는 최소 허용 저하 수준으로, 실무적으로 수용 가능
  - 예: Baseline E가 평균 4.0일 때, candidate가 평균 3.5 이상이면 비열등으로 판정 가능

**Hypotheses:**
- H0: `d_j ≤ -Δ` (candidate j is inferior to baseline E)
- H1: `d_j > -Δ` (candidate j is non-inferior to baseline E)
- where `d_j = mean(Score_j) - mean(Score_E)` (group 단위로 평균 계산)

**Decision Rule:**
- Compute CI for `d_j` using group-cluster bootstrap
- **NI PASS if:** `LowerCI(d_j) > -0.5`
- **NI FAIL if:** `LowerCI(d_j) ≤ -0.5`
- **CI Level:** 95% two-sided CI (one-sided α = 0.025) for LowerCI
  - LowerCI는 bootstrap distribution의 2.5th percentile

**Statistical Method:**
- **Primary:** Group-cluster bootstrap
  - **Unit of resampling:** `group_id` (clusters)
  - For each bootstrap replicate:
    1. Sample `group_id` values with replacement (bootstrap resample of groups)
    2. For each arm: compute mean Overall Card Quality across sampled groups
    3. Compute `d_j = mean_j - mean_E` for each candidate arm j
  - **CI construction:** Percentile CI
    - LowerCI: 2.5th percentile of bootstrap distribution
    - UpperCI: 97.5th percentile of bootstrap distribution
  - **Fixed seed:** Default = 123 (configurable)
  - **Rationale:** 
    - Group-level clustering 구조를 보존
    - 18개 groups를 독립 단위로 취급
    - Distributional assumptions에 robust
    - Fixed seed로 재현 가능성 보장

**Multiple Comparisons Correction:**
- **Method:** Holm correction (default ON, recommended)
- **Comparisons:** 4개 (A vs E, B vs E, C vs E, D vs E)
- **Output:** 
  - `holm_adjusted_p`: Adjusted p-value for each candidate
  - `holm_pass`: Pass/fail after Holm correction

**Safety Gate (별도 운영):**
- **Metric:** Major error rate (proportion of cards scored 0)
- **Notation:** `RD0 = p0_T - p0_A` (risk difference)
- **Safety Pass Criterion:** `UpperCI(RD0) ≤ +0.02` (two-sided 95% CI)
- **목적:** Major error의 허용 불가능한 증가 방지
- **Action:** Safety FAIL → arm 즉시 제외 (NI 검증 전)

### 3.3 데이터 구조

**Set-level 데이터 (S0):**

**Required columns:**
- `run_tag`: 실행 태그
- `arm`: Arm identifier (A-F)
- `group_id`: Group identifier (1-18)
- `set_id`: Set identifier (within group × arm)
- `rater_id`: 평가자 identifier
- `overall_quality_1to5`: Overall Card Quality score (1-5 Likert) - **Primary endpoint**

**Optional columns:**
- `accuracy_set`: Set-level accuracy (0/0.5/1.0) - Secondary endpoint (NI 분석에는 사용 안 함)
- `blocking_error`: Blocking error 존재 여부 (bool) - Safety gate용
- `editing_time_min`: 편집 시간 (minutes, self-reported) - Decision criteria용
- `clarity_score`: Clarity & Readability score (1-5 Likert) - Secondary endpoint
- `relevance_score`: Clinical/Exam Relevance score (1-5 Likert) - Secondary endpoint

**Data preprocessing:**
- Missing data: Rows with missing `overall_quality_1to5` are excluded
- Set-level aggregation: If multiple raters evaluate the same `(group_id, arm, set_id)`, compute mean
- Baseline missing: Groups where baseline E is missing are excluded from comparisons

---

## 4. Step S1 설계 (향후 진행 예정)

**목적:** 선정된 모델로 생성된 전체 콘텐츠(약 6,000개)에 대한 배포 승인

**Design:** One-shot acceptance sampling

**Quality target:** card-level blocking error rate < 1%

**Statistical guarantee:** one-sided 99% confidence

**Method:** Clopper-Pearson upper bound

**Acceptance rule:**
- Sample size: n = 838 cards (PPS + stratified sampling)
- Acceptance criterion: blocking error ≤ 2건 → PASS
- PASS 시, 전체 문항의 blocking error rate이 1% 미만임을 99% 신뢰로 보장

**Sampling strategy:**
- 모집단: EDA 기반 전체 그룹에서 생성된 모든 카드
- 방식: PPS(weight-proportional) + 층화 샘플링
- One-shot sampling: 중간 배치 없이 단일 샘플로 종료

---

## 5. 현재 진행 상황 및 검토 요청 사항

### 5.1 진행 상황

- 연구 설계 및 통계 분석 계획 문서화 완료
- S0 QA 자료 배포 완료, 평가 진행 중
- 1월 초 전공의 배포 목표로 촉박한 상황
- ChatGPT 도움으로 초안 작성했으나, 전문가 검토 필요

### 5.2 검토 요청 사항

1. **Non-inferiority margin (Δ = 0.5 on Likert scale)의 적절성**
   - 1–5 Likert scale에서 0.5 (한 단계의 절반)가 교육적으로 의미 있는 margin인지?
   - 통계적으로 방어 가능한 margin인지?
   - 예: Baseline E가 평균 4.0일 때, candidate가 평균 3.5 이상이면 비열등으로 판정하는 것이 적절한지?
   - Alternative margin 값 (예: 0.3, 0.4, 0.6)에 대한 의견

2. **Single-layer framework의 적절성**
   - Set-level Overall Card Quality (1–5 Likert)만을 primary endpoint로 사용하는 것이 적절한지?
   - Blocking error rate는 별도 safety gate로 운영하되 통계 분석에는 포함하지 않는 접근이 타당한지?
   - 또는 blocking error를 통계 모델에 통합하는 것이 더 나은지?
   - Two-layer framework (Safety gate + NI gate)를 고려해야 하는지?

3. **Sample size (n=18 groups)의 적절성**
   - Non-inferiority early-phase pilot로서 충분한지?
   - Group-cluster bootstrap을 사용할 때 n=18이 통계적 검정력 측면에서 적절한지?
   - Power analysis가 필요한지?
   - 만약 부족하다면, 몇 개의 groups가 필요한지?

4. **Statistical method (group-cluster bootstrap)의 적절성**
   - Group 단위로 resampling하는 것이 적절한지?
   - Group-level clustering 구조를 보존하면서도 rater-level pairing 정보를 활용하는 더 나은 방법이 있는지?
   - Alternative method (mixed-effects model 등) 고려 필요 여부?
   - Bootstrap resample 수 (현재 명시되지 않음)는 몇 개가 적절한지?

5. **Multiple comparisons correction**
   - Holm correction이 적절한지?
   - 4개 비교 (A vs E, B vs E, C vs E, D vs E)에 대한 correction이 필요한지?
   - Alternative correction method (Bonferroni, FDR 등) 고려 필요 여부?

6. **Reference arm 선택 (Arm E)**
   - Arm E (High-End, Gemini 3 Pro Preview)를 reference로 사용하는 것이 적절한지?
   - 연구 목적(비용 효율성 최적화)을 고려할 때, 고성능 모델을 기준으로 저비용 모델의 비열등성을 입증하는 접근이 타당한지?
   - Alternative: Arm A (Baseline, 최저 비용)를 reference로 사용하는 것과 비교

7. **CI Level (95% vs 90%)**
   - 현재 설계: 95% two-sided CI (one-sided α = 0.025)
   - Alternative: 90% two-sided CI (one-sided α = 0.05) - 더 관대한 기준
   - Early-phase pilot로서 어떤 CI level이 적절한지?

8. **Secondary outcomes 활용**
   - Editing time, Clarity, Relevance 등의 secondary outcomes를 어떻게 활용할지?
   - Decision criteria에서 cost minimization과 editing time minimization의 우선순위는 적절한지?

---

## 6. 첨부 자료

본 메일에는 다음 3가지 자료를 첨부드립니다:

1. **연구 개요 및 오늘 미팅 안건 슬라이드 (PPT)**
   - 프로젝트 목표 및 배경
   - MeducAI 파이프라인 구조
   - S0 QA 구조 및 평가 현황
   - 통계 분석 계획 및 의사결정 규칙
   - 오늘 저녁 킥오프 미팅 안건

2. **배포할 자료 샘플**
   - 나노바나나프로(NanoBananaPro)로 생성한 의료 이미지 활용 예시
   - 실제 배포될 교육 콘텐츠(Anki 카드, 표, 시각 자료) 샘플
   - S0 QA 평가에서 사용되는 자료 형태

3. **설문 문항**
   - S0 QA 평가 설문 문항 및 답변 형식
   - 평가 항목 정의 (Blocking error, Overall Card Quality 등)
   - 평가 방법 및 기준

**추가 자료:**
- **연구 내용 및 공저자 정보 (Notion 페이지):** [https://www.notion.so/MeducAI-2c701b7d46208072a71ffd6b2ba70da1](https://www.notion.so/MeducAI-2c701b7d46208072a71ffd6b2ba70da1)
  - 연구 프로젝트 전체 개요
  - 공저자 목록 및 역할
  - 프로젝트 진행 현황
- 필요하시면 상세한 연구 설계 문서, 통계 분석 계획 문서 등 추가 자료도 공유 가능합니다.

---

## 7. 일정 및 협력 방식

### 7.1 일정

- **현재:** S0 QA 평가 진행 중
- **목표:** 1월 초 전공의 배포 목표로 촉박한 상황
- **예상 일정:**
  - QA 평가 완료: 12월 말
  - QA 결과 분석: 12월 말
  - 배포: 1월 첫째 주

### 7.2 협력 방식

교수님의 기대사항을 명확히 이해하고, 서로 다른 부분이 있으면 솔직하게 얘기하고 조율하는 것이 좋을 것 같습니다.

**교수님의 기대사항 (참고):**
- **Authorship과 자문료는 별개**로 생각하심
- **Intellectual contribution**이 있으면 자문료를 받았든 받지 않았든 공저자가 되어야 함
- 기여도가 충분하지 않으면 공저자가 될 필요가 없음
- 공저자로 포함되면 논문의 전체적인 writing이나 revision에 대한 대응까지 같이 책임지심
- 자문료는 상담과 분석에 들어간 시간을 계산해서 시간당으로 청구 (논문 writing이나 revision에 쓴 시간은 자문료를 받지 않음)

**협력 방식 옵션:**

**옵션 1: 피드백 (간단한 검토 및 의견)**
- 자료 검토 후 주요 의견 및 개선 사항 피드백
- Intellectual contribution 정도에 따라 공저자 여부 결정

**옵션 2: 유료 자문 (정식 통계 자문)**
- 상세한 통계 분석 설계 검토
- 분석 계획 수정 및 보완
- 상담 및 분석 시간 기준 시간당 자문료 청구
- 병원 연구비 집행 가능
- Intellectual contribution 정도에 따라 공저자 여부 별도 결정

**옵션 3: 공저자 참여 (논문 출간까지 지속 지원)**
- 통계 분석 설계 및 실행 전 과정 지원
- 논문 Methods/Results 섹션 작성 지원
- 논문 writing 및 revision까지 책임
- 공저자로 참여
- 논문 writing/revision 시간은 자문료 대상에서 제외

**미팅 제안:**
- 필요하시면 온라인 미팅(Google Meet)으로 상세 논의 가능
- 미팅 PPT 자료 준비되어 있음
- 협력 방식, 기여도, authorship, 자문료 등에 대해 솔직하게 논의하고 조율

**오늘 저녁 킥오프 미팅 안내:**
- 죄송하지만, 공저자 참여 의향이 있으시고 오늘 저녁 시간이 되시면 킥오프 미팅에도 참여해주시면 감사하겠습니다.
- 일시(한국시간, KST): **2025-12-23(화) 20:00–21:00**
- 영상 통화 링크(Google Meet): [https://meet.google.com/fkp-eskz-twp](https://meet.google.com/fkp-eskz-twp)
- 미팅에 참석이 어려우시더라도, 메일로 연구 방향에 대해 조언 주시면 큰 도움이 됩니다.

---

## 8. 문의 및 연락처

평가 중 기술적 문제 또는 내용 관련 문의가 있으시면 언제든지 연락 부탁드립니다.

- **이메일:** [email-redacted]
- **전화:** [phone-redacted]

---

부담 없이 편하게 답변 주시면 감사하겠습니다.
추가로 필요한 자료가 있으시면 말씀해 주세요.

감사합니다.

[Study Coordinator] 올림
[Institution] 영상의학과

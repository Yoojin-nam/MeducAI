# MeducAI QA 배포 후 첫 미팅 PPT 구성

**일시:** 2025-12-23 (화) 20:00  
**목적:** S0 QA 진행 현황 공유, 분석·의사결정 규칙 재확인, 다음 단계 실행 합의

---

## 슬라이드 구성 (총 약 25-30장)

---

## Part 1: 오프닝 및 프로젝트 개요 (5-7장)

### 슬라이드 1: 타이틀
- **제목:** MeducAI QA 배포 후 첫 미팅
- **부제:** S0 QA 진행 현황 공유 및 다음 단계 합의
- **일시:** 2025-12-23 (화) 20:00
- **참석자:** [참석자 목록]

### 슬라이드 2: 오늘 미팅에서 결정할 것
- **목표 합의**
  - ✅ QA 이슈 정리
  - ✅ S0 분석 계획 확정
  - ✅ Safety gate & Non-inferiority 적용 방식
  - ✅ 최종 모델 선택 로직 (동률 시 tie-break)
  - ✅ Target journal 선정
  - ✅ 역할 배정

### 슬라이드 3: MeducAI 프로젝트 개요
- **목표:** LLM 기반 영상의학 교육용 학습 콘텐츠의 체계적·재현 가능·감사 가능한 생성
- **핵심 철학:** 공정한 모델 비교(QA), IRB-친화적 기록, 재현 가능한 실행
- **현재 단계:** S0 QA 자료 배포 완료 → 평가 진행 중

### 슬라이드 4: Two-Pipeline Study Architecture
- **이미지 사용:** [Two-Pipeline Study Architecture 이미지]
- **Pipeline-1 (Paper-1):** Expert QA & Deployment Model Selection
  - S0: 6-arm Factorial QA (108 sets)
  - S1: One-shot Acceptance Sampling (n=838 cards)
  - → Deployment Model Freeze
- **Pipeline-2 (Paper-2):** Prospective Observational UX Study
  - 실제 사용자 연구 (별도 진행)
- **분리 원칙:** Analytically Independent

### 슬라이드 5: MeducAI Pipeline Flow
- **이미지 사용:** [MEDUCAI PIPELINE FLOW 이미지]
- **S0:** QA/Model Comparison (fixed payload, arm fairness)
- **S1:** Structure only (Group-level structuring, Master Table)
- **S2:** Execution only (Exact N cards, Q1/Q2/Q3)
- **S3:** Policy Resolution & Image Spec (State-only compiler)
- **S4:** Image Generation (PNG rendering)
- **S5:** Export (PDF/Anki packaging)

### 슬라이드 6: MeducAI Model Architecture & Arms
- **이미지 사용:** [MEDUCAI MODEL ARCHITECTURE & ARMS 이미지]
- **6개 Arm 비교:**
  - **Arm A:** Baseline (Gemini 3 Flash, Thinking OFF, RAG OFF)
  - **Arm B:** RAG Only (Gemini 3 Flash, Thinking OFF, RAG ON)
  - **Arm C:** Thinking (Gemini 3 Flash, Thinking ON, RAG OFF)
  - **Arm D:** Synergy (Gemini 3 Flash, Thinking ON, RAG ON)
  - **Arm E:** High-End (Gemini 3 Pro, Thinking ON, RAG OFF)
  - **Arm F:** Benchmark (GPT-5.2 Pro, Thinking ON, RAG OFF)

---

## Part 2: S0 QA 구조 및 평가 현황 (6-8장)

### 슬라이드 7: S0 QA Evaluation Structure
- **이미지 사용:** [S0 QA EVALUATION STRUCTURE 이미지]
- **Sampling Structure:**
  - 18 Groups × 6 Arms = 108 Sets
  - 각 Set: Master Table + 12 Anki Cards + Infographic (해당 시)
- **Evaluation Structure:**
  - Unit of Analysis: Set-level
  - Primary: Safety Gate (Blocking error rate ≤ 1%)
  - Secondary: Overall Card Quality (Non-inferiority analysis)

### 슬라이드 8: Two-Layer Decision Framework
- **Layer 1: Safety Gate**
  - Check: UpperCI(RD0) ≤ +0.02
  - If FAIL → Arm disqualified
- **Layer 2: Non-Inferiority Gate**
  - Check: LowerCI(d) > -Δ (Δ = 0.05)
  - If PASS → Eligible for selection
- **Final Selection Criteria:**
  - Cost minimization
  - Editing time minimization

### 슬라이드 9: S0 평가자 배정 구조
- **이미지 사용:** [S0 평가자 배정 구조 이미지]
- **108 Sets (Total)**
- **Per Set: 2-person Paired Cross-Evaluation**
  - **Attending Physician:** Safety Authority
    - Blocking error final judgment
    - Clinical/exam appropriateness anchor
  - **Radiology Resident:** Usability/Clarity Evaluator
    - Clarity and readability evaluation
    - Overall card quality assessment
- **Workload:** 12 sets per reviewer, 5-10 min per set, 총 1-2 hours

### 슬라이드 10: S1→S2→S3→S4 Pipeline Schema
- **이미지 사용:** [S1→S2→S3→S4 pipeline schema 이미지]
- **S1:** Structure only (Text LLM) → `stage1_struct.jsonl`
- **S2:** Execution only (Text LLM) → `s2_results.jsonl`
- **S3:** Policy Resolution (Deterministic compiler) → `s3_image_spec.jsonl`
- **S4:** Image Generation (Image MLLM) → `IMG_*.png`

### 슬라이드 11: QA 진행 현황 (실시간 업데이트)
- **배포 현황:**
  - 평가자 배정: [명] (Resident [명] + Attending [명])
  - 평가 완료: [명] / [명] ([%])
  - 예상 완료일: [날짜]
- **이슈 사항:**
  - [기술적 이슈]
  - [평가자 피드백]
  - [기타]

---

## Part 3: S0 분석 계획 및 의사결정 규칙 (5-6장)

### 슬라이드 12: S0 분석 계획 확정
- **Primary Analysis:**
  - Mean Accuracy Score (0/0.5/1) per card
  - Non-inferiority test: LowerCI(d) > -Δ (Δ = 0.05)
  - Baseline: Arm A (default) 또는 Arm E (alternative)
- **Statistical Method:**
  - Clustered paired bootstrap
  - Unit of resampling: (rater_id, group_id) pairs
  - CI construction: Percentile CI (90% two-sided, one-sided α = 0.05)

### 슬라이드 13: Safety Gate 적용 방식
- **Layer 1: Safety Gate (Gatekeeper)**
  - **Metric:** Major error rate (proportion of 0-score cards)
  - **Check:** UpperCI(RD0) ≤ +0.02
  - **Interpretation:** Blocking error rate ≤ 1% 보장
  - **Action:** FAIL → Arm 자동 제외

### 슬라이드 14: Non-Inferiority 적용 방식
- **Layer 2: Non-Inferiority Gate**
  - **Endpoint:** Mean Accuracy Score (0/0.5/1)
  - **Margin:** Δ = 0.05 (mean score scale)
  - **Check:** LowerCI(d) > -Δ
  - **Interpretation:** Test arm이 baseline 대비 교육적으로 의미 있는 품질 저하 없음
  - **Action:** PASS → Eligible for selection

### 슬라이드 15: 최종 모델 선택 로직
- **Eligibility Criteria:**
  1. Non-inferiority 통과
  2. Safety gate 통과
- **Selection Criteria (Pre-specified):**
  1. **Primary:** Cost minimization (API 비용)
  2. **Secondary:** Editing time minimization
- **Tie-breaker (순차 적용):**
  1. 더 낮은 blocking error 발생
  2. 운영 안정성 (실패율, 재시도율)
  3. 더 높은 평균 Overall Card Quality 점수
- **Fallback:** 비열등 arm이 없는 경우, Reference Arm (A 또는 E) 사용

### 슬라이드 16: Post-S0 FINAL Deployment Process
- **이미지 사용:** [Post-S0 FINAL Deployment Quality Assurance Process 이미지]
- **S0 QA 완료** → **Selected Deployment Model**
- **FINAL Generation:** ~6,000 cards 생성
- **Random Sampling (10%):** 838 cards (PPS + stratified sampling)
- **3-Person Evaluation:**
  - Resident Reviewer 1 & 2: Independent evaluation
  - Attending: Adjudication for disagreements & blocking errors
- **Quality Gate:**
  - Blocking error rate < 1%
  - Acceptance rule: ≤2 blocking errors → PASS
- **Deployment Approved** → FINAL Deployment

---

## Part 4: Target Journal 선정 및 제출 전략 (4-5장)

### 슬라이드 17: Target Journal 선정 기준
- **선정 기준:**
  1. **스코프 적합성:** 의료 AI / 영상의학 / 교육
  2. **방법론 기여도:** 재현성·거버넌스 강조
  3. **예상 심사 기간:** 3-6개월
  4. **오픈액세스/비용:** APC 고려
  5. **허용 형식:** Original Article / Technical Note
- **파이프라인 분리 출간 여부:** 논의 필요

### 슬라이드 18: 1순위 저널 Shortlist
- **Radiology: Artificial Intelligence**
  - 스코프: ⭐⭐⭐⭐⭐
  - 방법론: ⭐⭐⭐⭐⭐
  - 심사 기간: 3-4개월
  - APC: [확인 필요]
  - 형식: Original Article
- **European Radiology**
  - 스코프: ⭐⭐⭐⭐
  - 방법론: ⭐⭐⭐⭐
  - 심사 기간: 4-6개월
  - APC: [확인 필요]
  - 형식: Original Article

### 슬라이드 19: 2순위 저널 Shortlist
- **AJR (American Journal of Roentgenology)**
  - 스코프: ⭐⭐⭐⭐
  - 방법론: ⭐⭐⭐
  - 심사 기간: 3-5개월
  - APC: [확인 필요]
  - 형식: Original Article
- **JACR (Journal of the American College of Radiology)**
  - 스코프: ⭐⭐⭐⭐
  - 방법론: ⭐⭐⭐
  - 심사 기간: 4-6개월
  - APC: [확인 필요]
  - 형식: Original Article / Technical Note
- **Academic Radiology**
  - 스코프: ⭐⭐⭐⭐
  - 방법론: ⭐⭐⭐
  - 심사 기간: 4-6개월
  - APC: [확인 필요]
  - 형식: Original Article

### 슬라이드 20: 제출 전략 및 일정
- **목표:** 2월 중으로 3-4월 내 저널 제출
- **일정:**
  - **1월:** Methods & Results 초안 작성
  - **2월:** 논문 완성 및 내부 검토
  - **3-4월:** 저널 제출
- **Pipeline 분리 전략:**
  - **Option 1:** Pipeline-1과 Pipeline-2 분리 출간
  - **Option 2:** 통합 출간 (논의 필요)

---

## Part 5: FINAL 배포 후 설문 조사 (3-4장)

### 슬라이드 21: FINAL 배포 후 설문 조사 개요
- **대상:** 4년차 전공의 (Radiology residents)
- **목적:** Pipeline-2 (Prospective Observational UX Study)
- **주요 지표:**
  - Cognitive load (extraneous / intrinsic / germane)
  - Self-efficacy
  - Satisfaction
  - Technology acceptance

### 슬라이드 22: 참가율/응답률 높이는 방안
- **참가율 향상 전략:**
  1. 사전 안내 및 동의서 작성 (IRB 통과 후)
  2. 인센티브 제공 (연구 참여 인정 등)
  3. 리마인더 체계 구축
  4. 설문 길이 최적화 (10-15분 이내)
- **응답률 향상 전략:**
  1. 단계별 설문 (초기/중기/후기)
  2. 모바일 친화적 설문 형식
  3. 피드백 제공 (개인화된 학습 리포트)

### 슬라이드 23: 설문조사 문항 타당성
- **Cognitive Load:**
  - NASA-TLX 또는 adapted scale
  - Extraneous / Intrinsic / Germane load 구분
- **Self-Efficacy:**
  - Bandura's self-efficacy scale (adapted)
  - 영상의학 학습 맥락에 맞춘 문항
- **Satisfaction:**
  - System Usability Scale (SUS) 또는 custom scale
- **Technology Acceptance:**
  - TAM (Technology Acceptance Model) 기반
  - Perceived usefulness, ease of use

---

## Part 6: 역할 배정 및 다음 단계 (4-5장)

### 슬라이드 24: QA 대체 평가자 확보
- **현재 상황:**
  - 평가자 수: [명]
  - 이슈 발생 평가자: [명]
- **대체 평가자 확보 방안:**
  1. 예비 평가자 풀 활용
  2. 추가 평가자 모집
  3. 배정 재조정 (subspecialty de-correlation 고려)

### 슬라이드 25: 통계 분석 역할 배정
- **S0 분석:**
  - Primary analysis: [담당자]
  - Statistical validation: [담당자]
- **S1 분석:**
  - Acceptance sampling analysis: [담당자]
  - Quality gate evaluation: [담당자]

### 슬라이드 26: 논문 작성 역할 배정
- **Methods Section:**
  - Pipeline 구조: [담당자]
  - QA Framework: [담당자]
  - Statistical analysis: [담당자]
- **Results Section:**
  - S0 결과: [담당자]
  - S1 결과: [담당자]
- **Introduction & Discussion:**
  - [담당자]

### 슬라이드 27: Figure 작성 역할 배정
- **Figure 1:** Pipeline Flow Diagram → [담당자]
- **Figure 2:** Model Architecture & Arms → [담당자]
- **Figure 3:** S0 QA Evaluation Structure → [담당자]
- **Figure 4:** Two-Layer Decision Framework → [담당자]
- **Figure 5:** Results (Primary/Secondary endpoints) → [담당자]
- **Figure 6:** Post-S0 FINAL Process → [담당자]

### 슬라이드 28: 다음 미팅 일정
- **다음 미팅 시기:** [토의 필요]
- **예상 일정:**
  - QA 완료 후 1-2주 내: S0 결과 분석 미팅
  - 모델 선정 후: IRB 제출 준비 미팅
  - 논문 초안 완성 후: 내부 검토 미팅
- **다음 미팅 안건:**
  - S0 분석 결과 공유
  - 모델 선정 확정
  - IRB 제출 준비 상황

---

## Part 7: 마무리 및 Q&A (2-3장)

### 슬라이드 29: 오늘 결정 사항 요약
- ✅ S0 분석 계획 확정
- ✅ Safety gate & Non-inferiority 적용 방식 합의
- ✅ 최종 모델 선택 로직 확정
- ✅ Target journal 1순위/2순위 선정
- ✅ 역할 배정 완료
- ✅ 다음 미팅 일정 확정

### 슬라이드 30: Action Items
- **즉시 실행:**
  1. QA 진행 상황 모니터링
  2. 대체 평가자 확보 (필요 시)
  3. Target journal 상세 조사
- **단기 (1-2주):**
  1. S0 분석 스크립트 준비
  2. 논문 작성 역할 분담 상세화
  3. IRB 제출 준비 시작
- **중기 (1-2개월):**
  1. S0 결과 분석 및 모델 선정
  2. IRB 제출
  3. 논문 초안 작성 시작

### 슬라이드 31: Q&A 및 논의
- **질문 사항:**
  - [참석자 질문]
- **추가 논의:**
  - [기타 논의 사항]

---

## 이미지 사용 가이드

### 각 슬라이드별 이미지 배치 권장사항:
1. **슬라이드 4:** Two-Pipeline Study Architecture (전체 화면)
2. **슬라이드 5:** MEDUCAI PIPELINE FLOW (전체 화면)
3. **슬라이드 6:** MEDUCAI MODEL ARCHITECTURE & ARMS (전체 화면)
4. **슬라이드 7:** S0 QA EVALUATION STRUCTURE (전체 화면)
5. **슬라이드 9:** S0 평가자 배정 구조 (전체 화면)
6. **슬라이드 10:** S1→S2→S3→S4 pipeline schema (전체 화면)
7. **슬라이드 16:** Post-S0 FINAL Deployment Quality Assurance Process (전체 화면)

### 텍스트와 이미지 배치:
- 이미지 중심 슬라이드: 이미지를 크게 배치하고 설명은 하단 또는 오른쪽에 간단히
- 텍스트 중심 슬라이드: 이미지는 보조 자료로 작게 배치하거나 별도 슬라이드로 분리

---

## 발표 시간 배분 (총 80분)

- **Part 1: 오프닝 및 프로젝트 개요** (10분)
- **Part 2: S0 QA 구조 및 평가 현황** (15분)
- **Part 3: S0 분석 계획 및 의사결정 규칙** (15분)
- **Part 4: Target Journal 선정 및 제출 전략** (10분)
- **Part 5: FINAL 배포 후 설문 조사** (10분)
- **Part 6: 역할 배정 및 다음 단계** (10분)
- **Part 7: 마무리 및 Q&A** (10분)

---

**작성일:** 2025-12-20  
**최종 업데이트:** 2025-12-20


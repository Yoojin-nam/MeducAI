# MeducAI 3-Paper Submission Strategy & Turing Test Design
**Date:** 2026-01-22  
**Status:** Strategic Decision Record  
**Context:** Paper 1, 2, 3 저널 타겟 상향 조정 및 실험 설계 고도화

---

## 1. Revised Submission Strategy (High Impact Approach)

기존의 보수적인 전략(Academic Radiology 중심)을 수정하여, 각 논문의 Novelty와 데이터 규모에 걸맞은 **Top-tier 저널**을 타겟팅함.

| Paper | Target Journal (1st) | Target Journal (Safe) | Core Selling Point (The "Hook") |
| :--- | :--- | :--- | :--- |
| **Paper 1**<br>(S5 Agent) | **Radiology: AI**<br>*(or npj Digital Medicine)* | *J Digital Imaging* | **"AI Supervising AI"**<br>- 6,000장 규모 검증 자동화 & 거버넌스<br>- Human-level performance (Non-inferiority)<br>- **New:** 실제 전문의 시험 문제 검증(External Validation) 추가 |
| **Paper 2**<br>(Visual) | **Radiology (RSNA)**<br>*(Reject시 Rad:AI Transfer)* | *Academic Radiology* | **"The Visual Turing Test"**<br>- Privacy-free/Copyright-free Medical Imaging<br>- 전문가와 전공의 집단도 구분 못한(Indistinguishable) 퀄리티<br>- 생성형 AI의 해부학적 정확성 정량화 |
| **Paper 3**<br>(Edu UX) | **Academic Radiology**<br>*(or Medical Teacher)* | *BMC Med Educ* | **"Real-world Implementation & Acceptance"**<br>- (로그 부재 대안) Mixed Methods 접근<br>- 단순 성적보다 **심리적 변화(Cognitive Load, Self-efficacy)** 및 **수용성(TAM)** 강조<br>- 실제 시험 준비(High-stakes) 맥락의 질적 분석 |

---

## 2. Paper 2: Visual Turing Test 설계 (Detailed Protocol)

*Radiology* 투고를 위한 통계적 엄밀성과 실험 설계.

### 2.1 참여자 (Sample Size)
*   **Target**: **30~50명** (전공의 + 전문의 혼합)
*   **구성**:
    *   Group A (Experts): 기존 QA 참여 교수님 (Washout 효과 검증)
    *   Group B (Learners): 신규 전공의/전문의 (Real-world Utility 검증)
*   **Incentive**: **Group Authorship** (e.g., "MeducAI Collaborative Group") 제공으로 대규모 모집 유도.

### 2.2 문항 구성 (The "Golden Set")
*   **총 문항**: **60 sets** (Single Presentation 방식)
    *   **AI Generated**: 30장 (High/Mid/Low Quality 층화)
    *   **Real Patient**: 30장 (AI와 Diagnosis-Matched)
*   **제시 방식**: **Sequential Monadic Design (순차적 단일 제시)**
    *   1:1 비교(Side-by-side) 지양 → 실제 판독 환경과 동일하게 1장씩 제시하여 난이도 유지 및 편향 제거.
    *   모든 평가자에게 **동일한 60문항(Common Set)** 제시 (Inter-rater Reliability 확보).

### 2.3 매트릭스 설계 (Part × Modality)
영상의학의 다양성을 커버하기 위해 Core 4 Parts와 Modality를 균형 있게 배분.

| | Chest | Abdomen | Neuro | MSK | 합계 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **X-ray** | 6 | - | - | 6 | **12 (20%)** |
| **CT** | 6 | 10 | 2 | 2 | **20 (33%)** |
| **MRI** | 3 | 5 | 13 | 7 | **28 (47%)** |
| **Total** | **15** | **15** | **15** | **15** | **60** |

*   **원칙**: AI 이미지와 Real 이미지는 반드시 **동일 진단명(Diagnosis-Matched)**이어야 함. (Confounding factor 제거)

### 2.4 실험 프로토콜 (Step-by-Step)
1.  **Blind Phase**:
    *   이미지 1장 제시
    *   Q1: **"Real or AI?"** (Binary Choice)
    *   Q2: **"Confidence?"** (1-5 Scale) → ROC Curve 분석용
2.  **Unblind Phase** (정답 공개 후):
    *   Q3: **"Educational Suitability?"** (1-5 Scale)
    *   *AI임이 밝혀진 후에도 높은 점수를 받는다면 교육적 가치 입증.*

---

## 3. Paper 1 & 3 보강 전략

### Paper 1 (S5 Validation Agent)
*   **약점**: Self-referential loop (AI가 만든 걸 AI가 검사).
*   **보강 (Killer Move)**: **"External Validation with Board Exam Items"**
    *   실제 전문의 평가고사/시험 기출문제(Ground Truth)를 S5가 평가하게 함.
    *   전문의들이 S5의 지적(Critique)에 얼마나 동의하는지 측정.
    *   → "S5는 실제 시험 수준의 감수 능력을 가졌다"는 논리 확보.

### Paper 3 (Educational Effectiveness)
*   **약점**: 로그 데이터 부재 (객관적 사용량 추적 불가).
*   **보강 (Survival Strategy)**: **"Mixed Methods Study"**
    *   **Quantitative**: Validated Scales (Leppink Cognitive Load, Self-efficacy)의 Pre-Post 변화량(Delta)에 집중.
    *   **Qualitative**: 서술형 응답에 대한 정교한 **Thematic Analysis**.
    *   **Message**: "성적 향상"보다는 **"학습 경험의 질적 변화(Quality of Experience)"**와 **"심리적 부담 완화(Stress Reduction)"**에 초점.

---

## 4. Action Items

1.  [ ] **Paper 2 Golden Set 구성**: 300개 풀에서 위 매트릭스에 맞춰 60쌍(120개 후보 중 60개 선정) 추출.
2.  [ ] **Turing Test 플랫폼 준비**: Google Forms 또는 전용 뷰어 세팅 (Single presentation → Unblind 순서).
3.  [ ] **참여자 모집 공지**: "MeducAI Collaborative Group" 저자 포함 조건으로 전공의/전문의 대규모 모집.
4.  [ ] **Paper 1 추가 실험**: 전문의 시험 기출문제 50개 확보 및 S5 평가 돌리기.

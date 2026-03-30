# Paper 2: MLLM 생성 의료 이미지 Visual Turing Test 상세 설계
**Detailed Experimental Design**

**작성일:** 2026-01-22  
**상태:** 실행 프로토콜 (Canonical)  
**타겟 저널:** Radiology (RSNA) / Radiology: Artificial Intelligence  
**관련 문서:**
- `Paper_Submission_Strategy_and_Turing_Test_Design_2026-01-22.md` (전략 개요)
- `MeducAI_3Paper_Research_Index.md` (연구 포트폴리오)

---

## 1. 연구 질문 및 의의 (Research Question)

### 1.1 핵심 질문
> **"MLLM이 생성한 의료 이미지가 영상의학과 전문의 및 전공의에게 실제 환자 이미지와 구분 불가능(Indistinguishable)한 수준인가?"**

### 1.2 세부 질문
1. **Expertise Effect**: 판독 경험(연차)이 AI 식별 능력에 유의미한 영향을 미치는가? (전문의 vs 고연차 vs 저연차)
2. **Modality Effect**: 영상 모달리티(CT, MRI, X-ray)에 따라 AI 생성 품질의 차이가 있는가?
3. **Educational Value**: AI 이미지임을 인지한 후에도 교육적 가치가 있다고 판단하는가?

### 1.3 연구 의의 (Significance)
- **Visual Turing Test**: 대규모 MLLM 생성 의료 이미지에 대한 최초의 정량적 튜링 테스트
- **Privacy-free**: 환자 개인정보와 저작권 문제없는 무한한 교육 데이터 생성 가능성 입증
- **Educational Utility**: 실제 영상의학 교육 현장에 즉시 투입 가능한 수준임을 증명

---

## 2. 연구 설계 개요 (Study Design)

### 2.1 연구 유형
- **진단 정확도 연구 (Diagnostic Accuracy Study)**
- **전향적, 블라인드, 무작위 배정 설계 (Prospective, Blinded, Randomized)**
- **비교 연구 (Comparative Study)**: 인간 vs AI 이미지 / 연차별 식별 능력 비교

### 2.2 참여자 구성 (Target Population: The "Radiology Family")
타과 의사를 배제하고 영상의학 전문성(Expertise)의 스펙트럼을 분석하기 위해 **3개 그룹**으로 구성.

| 그룹 | 대상 | 목표 인원 | 역할 |
| :--- | :--- | :--- | :--- |
| **Group A (Faculty)** | 영상의학과 전문의 | 10~15명 | Gold Standard (최고 전문가의 눈) |
| **Group B (Senior)** | 전공의 3-4년차 | 10~15명 | Exam-ready (시험 최적화된 눈) |
| **Group C (Junior)** | 전공의 1-2년차 | 10~15명 | Trainees (학습자 대표) |
| **Total** | | **30~45명** | 통계적 검정력(Power > 0.8) 확보 |

### 2.3 인센티브
- **Group Authorship**: 모든 참여자를 논문 내 "MeducAI Collaborative Group" 공저자로 등재하여 대규모 모집 유도.

---

## 3. 이미지 세트 구성: "The Golden Set"

### 3.1 전체 구성
- **총 60문항** (120개 후보 중 엄선된 60개)
  - **AI Generated (30개)**: S5 품질 검증을 거친 이미지 (High/Mid/Low 층화)
  - **Real Patient (30개)**: AI 이미지와 **동일 진단명(Diagnosis-Matched)**을 가진 실제 환자 데이터

### 3.2 매트릭스 설계 (Part × Modality)
영상의학의 핵심 영역을 골고루 커버하여 일반화 가능성 확보.

| | Chest | Abdomen | Neuro | MSK | **합계** |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **X-ray** | 6 | - | - | 6 | **12 (20%)** |
| **CT** | 6 | 10 | 2 | 2 | **20 (33%)** |
| **MRI** | 3 | 5 | 13 | 7 | **28 (47%)** |
| **Total** | **15** | **15** | **15** | **15** | **60** |

*   **원칙**: AI 이미지와 Real 이미지는 반드시 **짝(Pair)**이 맞아야 함 (예: AI 폐렴 - Real 폐렴).

---

## 4. 실험 프로토콜 (Experimental Protocol)

### 4.1 제시 방식: "Randomized Sequential Monadic"

1.  **단일 제시 (Single Presentation)**: 화면에 한 번에 **이미지 1장**만 제시 (1:1 비교 아님).
2.  **완전 무작위 (Fully Randomized)**:
    - 60장(AI 30 + Real 30)의 순서를 섞어서 제시.
    - **Pair 분리**: AI 이미지와 그 짝꿍(Real)이 연달아 나오지 않도록 무작위 배치.
    - **참가자별 무작위 (Random per Participant)**: 플랫폼 기능을 활용하여 **참가자마다 제시 순서를 다르게 설정** (순서 효과 및 학습 효과 완전 제거).

### 4.2 진행 단계 (Two-Phase)

#### Phase 1: Blind Turing Test (식별 평가)
*   **이미지 제시** (순서 랜덤)
*   **Q1**: "이 이미지는 실제 환자(Real)입니까, AI 생성(AI)입니까?" (이지선다)
*   **Q2**: "판단의 확신도는?" (1: 매우 불확실 ~ 5: 매우 확실)
    *   *목적: ROC Curve 분석 및 AUC 산출*

#### Phase 2: Unblind Educational Assessment (가치 평가)
*   **정답 공개**: "이 이미지는 [AI 생성 / 실제 환자] 였습니다."
*   **Q3**: "이 이미지가 교육 자료로 적절합니까?" (1: 부적절 ~ 5: 매우 적절)
    *   *목적: AI임을 알고 난 후(Unblinded)의 수용성 평가*

---

## 5. 통계 분석 계획 (Statistical Analysis)

### 5.1 Primary Endpoint
*   **Overall Accuracy**: Real vs AI 식별 정답률 (%)
    *   **귀무가설 (H0)**: Accuracy = 50% (Random Guessing과 차이 없다 = 구분 불가능하다)
    *   **분석 방법**: One-sample Binomial Test

### 5.2 Secondary Endpoints
1.  **Expertise Effect (연차별 분석)**
    *   전문의 vs 고연차 vs 저연차 그룹 간 정답률 비교 (ANOVA or Chi-square)
    *   *가설: 연차가 높아져도 정답률은 50%에서 유의하게 벗어나지 않는다.*
2.  **Modality Effect**
    *   CT vs MRI vs X-ray 정답률 비교
    *   *목적: AI가 특정 모달리티에 강/약점이 있는지 파악*
3.  **Educational Suitability**
    *   AI 이미지의 교육적 적합성 점수 (Mean ± SD)

---

## 6. 품질 관리 및 리스크 완화

### 6.1 Positive Control (함정 카드)
*   **Low Quality AI**: S5에서 낮은 점수를 받았거나 미세한 오류가 있는 AI 이미지 3-5장 포함.
*   **목적**: 참여자가 졸지 않고 집중하고 있는지 검증 (이걸 못 맞추면 데이터 신뢰도 하락).

### 6.2 Washout Period (기존 참여자 대상)
*   기존 QA에 참여했던 교수님(Group A)은 최소 2주 이상의 휴지기(Washout) 후 참여.
*   자신이 평가했던 이미지를 기억해내는지 확인 (기억 못 할 가능성 높음).

---

## 7. 예상 결과 시나리오

| 시나리오 | 결과 (Accuracy) | 해석 | 논문 임팩트 |
| :--- | :--- | :--- | :--- |
| **Best** | **50% (Random)** | 전문가도 찍어야 할 만큼 완벽함 | **Radiology (RSNA)** |
| **Good** | **55-60%** | 미세하게 구분되지만 교육용으로 훌륭함 | **Radiology: AI** |
| **Bad** | **>70%** | 전문가 눈에는 티가 남 (한계 명시 필요) | **Academic Radiology** |

---

## 8. 실행 타임라인

1.  [ ] **Golden Set 60문항 확정**: 300개 풀에서 추출 및 매트릭스 검증 (D-Day)
2.  [ ] **플랫폼 세팅**: 랜덤 순서 제시 기능 구현 (D+3)
3.  [ ] **참여자 모집**: 공저자 인센티브 공지 및 3개 그룹 모집 (D+7)
4.  [ ] **데이터 수집**: 2주간 진행 (D+21)
5.  [ ] **데이터 분석**: 연차별/모달리티별 통계 분석 (D+25)

---

**문서 상태**: Canonical (실행 프로토콜)  
**최종 업데이트**: 2026-01-22  
**소유**: MeducAI Research Team

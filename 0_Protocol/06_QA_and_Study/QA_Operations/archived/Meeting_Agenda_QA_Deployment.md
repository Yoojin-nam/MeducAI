# MeducAI QA 배포 후 첫 미팅 Agenda

**일시:** [화요일 날짜]  
**참석자:** [참석자 목록]  
**목적:** QA 자료 배포 후 프로젝트 현황 공유 및 향후 일정 논의

---

## 1. 프로젝트 목표 및 배경 (15분)

### 1.1 MeducAI 프로젝트 개요
- **목표:** 대형 언어 모델(LLM)을 활용한 영상의학 교육용 학습 콘텐츠(Anki 카드, 표, 시각 자료)의 체계적·재현 가능·감사 가능한 생성
- **핵심 철학:** 콘텐츠 생성 그 자체보다, **공정한 모델 비교(QA), IRB-친화적 기록, 재현 가능한 실행**을 동시에 달성
- **연구 구조:** Two-Pipeline 설계
  - **Pipeline-1 (Paper-1):** Expert QA 기반 모델 선택 및 배포 승인
  - **Pipeline-2 (Paper-2):** 실제 사용자 연구 (별도 진행)

### 1.2 현재 단계
- **S0 QA 단계 완료:** 6개 Arm(A–F) 비교를 통한 최종 배포 모델 선정
- **QA 자료 배포 완료:** 평가자들에게 개인별 배정 자료 전달
- **다음 단계:** QA 결과 분석 → 모델 선정 → IRB 제출 → 배포

---

## 2. 모델 구조 및 파이프라인 (20분)

### 2.1 MeducAI 파이프라인 구조
```
S0   : QA / Model Comparison (fixed payload, arm fairness)
S1   : Structure only (LLM, no counts)
S2   : Execution only (LLM, exact N cards)
S3   : Selection & QA gate (state-only)
S4   : Rendering & presentation (image only)
FINAL: Allocation & deployment (card counts decided here only)
```

### 2.2 핵심 설계 원칙
- **LLM은 "결정(decision)"을 하지 않는다**
- **카드 수, 선택, 정책은 코드와 Canonical 문서에서만 결정**
- **각 단계는 고유한 책임만 가지며, 경계 침범은 즉시 실패(Fail-Fast)로 처리**

### 2.3 6-Arm 비교 구조
- **Arm A–F:** 다양한 LLM 설정 조합 (RAG, Thinking, 모델 버전 등)
- **S0 단계:** 고정 payload(각 Set당 12 cards)로 Arm 간 공정한 비교
- **평가 단위:** Set-level evaluation (108 sets = 18 groups × 6 arms)

### 2.4 Group-first Architecture
- **최소 처리 단위:** Group (312개 semantically coherent groups)
- **Group 정의:** EDA 기반 1,767개 학습 목표를 의미론적으로 통합
- **장점:** 확장 가능한 QA, 대표 샘플링, 재현 가능한 할당

---

## 3. QA 과정 및 평가 구조 (20분)

### 3.1 S0 QA 설계
- **목적:** 배포 전 최종 품질 검증 및 모델 선정
- **평가 범위:** 총 108 sets (18 groups × 6 arms)
- **Set 구성:** Master Table + Anki 카드 12장 + Infographic(해당 시)

### 3.2 평가자 구조
- **2인 교차평가:** Resident 1명 + Attending 1명 per Set
- **역할 분리:**
  - **Attending:** Safety-critical 판단 권위 (Blocking error 최종 판정), 임상/시험 적합성 기준점
  - **Resident:** Usability/clarity 평가 (가독성·명확성), 실제 사용자 관점의 품질 평가

### 3.3 의사결정 프레임워크 (2-layer)
- **Primary endpoint (Safety Gate):** Blocking error rate ≤ 1%
- **Secondary endpoint:** Overall Card Quality (Non-inferiority 분석)

### 3.4 블라인딩 원칙
- **블라인드 평가:** 통계적 타당성과 객관성 확보
- **평가 집중:** 콘텐츠 품질(정확성, 안전성, 가독성, 교육목표 부합성)에만 집중
- **제외 사항:** 모델/arm 추론, 생성 설정, 비용 및 기술적 세부사항

### 3.5 평가 항목
1. **Blocking Error 여부** (필수): 임상 판단을 잘못 유도할 수 있는 오류
2. **Overall Card Quality** (필수): Set 전체 종합 품질 (1–5점)
3. **Table/Infographic Critical Error** (필수): 치명 오류 여부
4. **Scope Failure** (해당 시): 교육 목표와의 불일치
5. **Editing Time** (필수): 배포 가능 수준으로 만드는 데 필요한 편집 시간
6. **Clarity & Readability** (필수): 학습자 관점의 명확성
7. **Clinical/Exam Relevance** (필수): 시험/수련 목표 부합성

---

## 4. 향후 일정 및 로드맵 (15분)

### 4.1 단기 일정 (1–2개월)
- **QA 평가 기간:** [시작일] ~ [마감일]
- **QA 결과 분석:** 평가 완료 후 1–2주 내
- **모델 선정:** S0 결과 기반 최종 배포 모델 결정
- **IRB 제출:** 모델 선정 후 IRB 승인 신청

### 4.2 중기 일정 (2–4개월)
- **IRB 통과 후 배포:** IRB 승인 후 대규모 콘텐츠 생성 및 배포
- **Pipeline-1 완료:** Expert QA 기반 모델 선택 및 배포 승인 완료
- **논문 작성 시작:** Methods 및 Results 섹션 초안 작성

### 4.3 장기 목표 (3–4개월)
- **저널 제출 목표:** 2월 중으로 3–4월 내 저널 제출
- **Pipeline-2 준비:** 실제 사용자 연구 설계 및 IRB 제출

---

## 5. 논의 사항 및 Q&A (10분)

### 5.1 QA 진행 상황
- 평가자 피드백 및 진행률 확인
- 기술적 이슈 또는 질문 사항

### 5.2 다음 단계 준비
- IRB 제출 준비 사항
- 논문 작성 역할 분담
- 추가 리소스 필요 사항

### 5.3 기타 논의
- 프로젝트 관련 추가 의견 및 제안

---

## 참고 자료

- **프로젝트 README:** `/README.md`
- **QA Framework:** `0_Protocol/06_QA_and_Study/QA_Framework.md`
- **Study Design:** `0_Protocol/06_QA_and_Study/Study_Design/Study_Design.md`
- **QA 평가자 이메일 템플릿:** `0_Protocol/06_QA_and_Study/QA_Operations/QA_Reviewer_Email_Template.md`

---

**작성일:** 2025-12-20  
**최종 업데이트:** 2025-12-20


# MeducAI QA 배포 후 첫 미팅 - PowerPoint 프레젠테이션 프롬프트 (Enhanced)

당신은 의학 연구(영상의학/의료 AI) 프로젝트의 공저자 브리핑용 PowerPoint를 만드는 프레젠테이션 디자이너입니다.
목표는 "공저자들이 5분 안에 프로젝트 QA 흐름, 통계적 의사결정, 일정, 요청 액션"을 이해하게 하는 것입니다.

---

## [출력물 요구사항]

- **16:9 PowerPoint, 총 10장(필수).** (옵션으로 부록 2장까지 추가 가능)
- **언어:** 한국어(필요한 전문용어는 영어 병기 가능)
- **각 슬라이드 본문 텍스트:** 과밀 금지(슬라이드당 5~7줄 내)
- **각 슬라이드에 Speaker Notes 포함:** 3~6문장(슬라이드에 못 넣는 배경/맥락/의사결정 포인트)
- **강조 규칙:** 핵심 메시지는 **굵게(BOLD)** 처리
- **문장부호 선호:** '·, —, 『 』' 같은 기호는 피하고, 쉼표/콜론을 사용
- **링크를 써야 한다면,** URL을 길게 쓰지 말고 "(링크)" 같은 플레이스홀더로 대체

---

## [미팅 컨텍스트]

- **미팅명:** MeducAI QA 배포 후 첫 미팅
- **일시/장소:** 12/23(화) 20:00, Google Meet
- **목적:** S0 QA 진행 현황 공유, 분석·의사결정 규칙 재확인, 다음 단계(모델 선정→IRB→배포/논문화) 실행 합의
- **오늘 논의 아젠다:**
  1) 오프닝, 오늘 미팅에서 "결정할 것" 합의, QA 이슈 정리
     - S0 분석 계획 확정
     - Safety gate(치명 오류)와 Non-inferiority(품질) 적용 방식
     - 최종 모델 선택 로직(동률 시 비용/편집시간 tie-break)
  2) Target journal 선정 및 제출 전략
     - 파이프라인 분리 출간 여부 합의
     - 1순위/2순위 저널 shortlist 확정
     - 선정 기준 합의: 스코프, 방법론 기여, 예상 심사 기간, OA/비용, 허용 형식
  3) FINAL 배포 후 설문 조사: 전공의 참여율/응답률, 설문 문항 타당성
  4) 역할 배정: 대체 평가자 확보, 통계/논문/Figure 분담
  5) 다음 미팅 시기

---

## [제공 이미지(슬라이드에 반드시 활용)]

- **Image 1:** "S1→S2→S3→S4 pipeline schema"
- **Image 2:** "MEDUCAI MODEL ARCHITECTURE & ARMS / MEDUCAI PIPELINE FLOW"
- **Image 3:** "108 Sets / Reviewer allocation (Attending vs Resident)"
- **Image 4:** "S0 QA Evaluation Structure (108 sets, 2-layer decision)"
- **Image 5:** "Post-S0 FINAL Deployment Quality Assurance Process"
- **Image 6:** "MeducAI Two-Pipeline Study Architecture"
※ 당신이 실제로 이미지를 삽입할 수 없다면, 해당 슬라이드에 [Insert Image X] 플레이스홀더를 넣고, 어디에 배치할지(예: 우측 60% 큰 그림, 좌측 텍스트)까지 명시하세요.

---

## [프로젝트 핵심 정보]

### 모델명 및 Arms 구성
- **Arm A (Baseline):** gemini-3-flash-preview, Thinking OFF, RAG OFF
- **Arm B (RAG Only):** gemini-3-flash-preview, Thinking OFF, RAG ON
- **Arm C (Thinking):** gemini-3-flash-preview, Thinking ON, RAG OFF
- **Arm D (Synergy):** gemini-3-flash-preview, Thinking ON, RAG ON
- **Arm E (High-End):** gemini-3-pro-preview, Thinking ON, RAG OFF (Closed-book 기준)
- **Arm F (Benchmark):** gpt-5.2-pro-2025-12-11, Thinking ON, RAG OFF (외부 벤치마크)

### 파이프라인 구조 (S1→S2→S3→S4)
- **S1 (Step 1):** 원시 교육목표(Objective) 입력 및 그룹핑
- **S2 (Step 2):** Execution 단계 - 텍스트 카드 생성 (LLM 호출, RAG/Thinking 적용)
- **S3 (Step 3):** Deterministic policy compiler - state-only 결정론적 정책 컴파일
- **S4 (Step 4):** Render-only - 최종 Anki 덱/표/인포그래픽 렌더링

### S0 분석 계획
- **샘플링:** 18 groups × 6 arms = **108 sets**
- **평가자 배정:** Set당 2인 (전공의 1인 + 전문의 1인)
- **Non-inferiority Test:**
  - **Layer 1 (Safety Gate):** UpperCI(RD0) ≤ 0.02 (치명 오류 증가 방지)
  - **Layer 2 (NI Gate):** LowerCI(d) > -Δ, Δ=0.05 (평균 정확도 비열등성)
  - **통계 방법:** Clustered paired bootstrap (5000 replicates, seed 20251220)
  - **Unit of resampling:** (rater_id, group_id) pairs
- **Tie-break:** 비용 최소화 → 편집시간 최소화 → 지연시간 → 안정성

### FINAL 배포 QA 프로세스
- **전체 생성 규모:** 약 6,000개 Anki 카드
- **샘플링:** 600개 카드 (10% 샘플링, 통계적 유효성 확보)
- **평가자 구성:** 전문의 1인 + 전공의 2인
- **평가 목적:** 안정성 검토 후 배포 승인
- **통계적 보장:** card-level blocking error rate < 1% (one-sided 99% confidence)

### 설문조사 계획
- **Baseline 설문 (배포 전):**
  - 인구학적 특성, 학습 배경
  - LLM 사용 경험, 신뢰도
  - 학습 자기효능감, 인지부하 (baseline 측정)
- **Post-exam 설문 (시험 후):**
  - MeducAI 사용 경험 평가
  - 학습 만족도, 기술 수용성(TAM)
  - 교육적 질, 효율성 종합 평가
  - 재사용 의향, 동료 추천 의향

### 타겟 저널 전략

#### 파이프라인 분리 시
**Paper A: "Expert QA 기반 모델 선택, Non-inferiority, QA 거버넌스"**
- 핵심 독자: radiology AI, implementation, workflow/quality 관점
- **1순위 후보:**
  - **Radiology: Artificial Intelligence (RSNA):** AI의 임상·운영·의료 성과 영향 중심. "교육" 자체만으로는 약할 수 있으나, radiology AI의 안전한 도입을 위한 QA 프레임워크로 각을 세우면 도전 가치 있음
  - **European Journal of Radiology Artificial Intelligence:** radiology에서 AI를 연구·구현·평가하는 흐름에 초점. "모델 비교, QA, 평가 방법론" 축이 잘 맞음

**Paper B: "전공의 80명 UX/수용성/인지부하, 로그 기반 사용-결과 연관"**
- 핵심 독자: 의료교육, 디지털 학습, 교육평가(설문+로그)
- **1순위 후보:**
  - **JMIR Medical Education:** 기술·혁신·e-learning/virtual training 등 의료교육 기술 평가를 정면으로 받는 저널. 현재 연구 디자인(설문+사용 로그)과 매우 정합적
  - **BMC Medical Education:** 보건의료인 교육 전반을 폭넓게 수용. 단일기관, 80명 규모의 관찰 연구도 구조만 탄탄하면 무난하게 타겟이 됨

#### 파이프라인 통합 시
- **Radiology (통합 출간 가능성):**
  - RCT 급 시험 점수 상승 데이터가 필요한데 현재 현실적으로 불가능
  - 추후 전공의 시험 몇 달 전에 동의서 받아서 전공의 1~4년차 100명 이상 모아서 모의고사 점수를 모으고, 이걸로 공부한 뒤 점수 상승을 확인하면 가능할지도

---

## [슬라이드 구성(10장 필수, 슬라이드별 산출 형식 준수)]

각 슬라이드는 아래 형식으로 출력하세요:
- **Slide N Title:**
- **On-slide Body (5~7줄):**
- **Visual/Layout (이미지 배치 지시 포함):**
- **Speaker Notes (3~6문장, 의사결정/근거/다음 액션 중심):**

---

## [슬라이드별 내용 요구]

### Slide 1) Title / Meeting Goal & Decisions
- 오늘 "결정할 것" 3~4개를 명확히, 회의 목적 1줄
- **핵심 결정사항:**
  - S0 분석 계획 확정 (Safety gate + Non-inferiority 기준)
  - 최종 모델 선택 로직 (tie-break 규칙)
  - Target journal shortlist 확정
  - FINAL 배포 QA 및 설문 계획 합의
- 노트에는: 오늘 회의는 보고보다 결정이 목표라는 점, 산출물(SSOT 업데이트)까지 연결한다는 점

### Slide 2) Big Picture: Two-Pipeline Architecture
- Image 6 사용
- **Paper-1 (Expert QA & Deployment Model Selection)** vs **Paper-2 (Prospective UX Study)** 분리
- **Paper-1:** S0 (6-arm factorial, non-inferiority) → 모델 선정 → FINAL 배포 QA (6000개 중 600개 샘플링)
- **Paper-2:** 전공의 80명 대상 사용자 연구 (baseline 설문 → 사용 → post-exam 설문)
- 노트에는: 오늘은 Paper-1 중심이지만 Paper-2(설문/참여율)까지 연결된다는 설명, 파이프라인 통합 시 Radiology 저널 가능성도 언급

### Slide 3) Pipeline Responsibility: S1→S2→S3→S4
- Image 1 사용
- 핵심 메시지: **S2는 execution(텍스트 카드, LLM 호출), S3는 deterministic policy compiler(state-only), S4는 render-only**
- **S2에서 모델 선택:** gemini-3-flash-preview (A-D), gemini-3-pro-preview (E), gpt-5.2-pro-2025-12-11 (F)
- **RAG/Thinking 설정:** S2 단계에서 적용 (Arm별 차이)
- 노트에는: 경계 고정이 공정성/감사 가능성에 왜 중요한지, S2에서의 모델/설정 변경이 실험 무결성에 미치는 영향

### Slide 4) 6 Arms: What Each Arm Tests
- Image 2(arms 표) 사용
- A–F arm의 목적을 1줄씩, "가설(검색 효과/추론 효과/시너지/고성능/벤치마크)"로 요약
- **Arm A (Baseline):** 최소 기준점 (gemini-3-flash-preview, Thinking OFF, RAG OFF)
- **Arm B (RAG Only):** 검색 효과 검증 (RAG ON)
- **Arm C (Thinking):** 추론 효과 검증 (Thinking ON)
- **Arm D (Synergy):** 저비용 풀옵션 (Thinking + RAG)
- **Arm E (High-End):** 고성능 기준 Closed-book (gemini-3-pro-preview)
- **Arm F (Benchmark):** 외부 벤치마크 Closed-book (gpt-5.2-pro-2025-12-11)
- 노트에는: arm 공정성(동일 payload, 동일 평가) 강조, E/F는 RAG OFF로 모델 자체 지능 비교

### Slide 5) S0 Sampling: 108 Sets, What Reviewers See
- Image 4 또는 Image 2의 flow 중 S0 관련 요소 활용
- "18 groups × 6 arms = 108 sets", set 구성(표 + 12 Anki + infographic)
- **18-Group 선택 규칙:** 
  - Stage 1: 각 specialty에서 weight 최고 그룹 1개씩 (11개)
  - Stage 2: 나머지 중 weight 기준 상위 7개
- **Set 구성:** Master Table + 고정 12-card Anki payload + Infographic (해당 시)
- 노트에는: set-level이 왜 운영/통계에 유리한지, 12-card payload 고정이 variance 감소에 미치는 영향

### Slide 6) Reviewer Allocation & Workload
- Image 3 사용
- **Attending:** Safety authority(0점/치명 오류 최종 판단), **Resident:** usability/clarity
- **평가자 배정:** Set당 2인 (전공의 1인 + 전문의 1인)
- 예상 소요시간(셋당 5–10분, 총 1–2시간) 포함
- **워크로드:** 전공의 12–15 sets, 전문의 12–15 sets
- 노트에는: 배정 제약(세부분과/기관 de-correlation)과 대체 평가자 플랜 언급, 전문의의 safety gatekeeper 역할 강조

### Slide 7) Decision Rule: Two-layer Gate + Tie-break
- Image 4 사용(2-layer decision framework)
- **Layer 1 Safety gate:** UpperCI(RD0) ≤ 0.02 (치명 오류 증가 방지)
- **Layer 2 Non-inferiority gate:** LowerCI(d) > -Δ, Δ=0.05 (평균 정확도 비열등성)
- **통계 방법:** Clustered paired bootstrap (5000 replicates, seed 20251220)
- **Tie-break:** 비용 최소화 → 편집시간 최소화 → 지연시간 → 안정성
- 노트에는: "Eligibility vs Selection"을 구분해 설명, 오늘 확정해야 할 규칙을 명시, bootstrap의 clustered paired 구조 설명

### Slide 8) Target Journal: Shortlist & Selection Criteria
- 텍스트 중심(표 1개 권장)
- **파이프라인 분리 시:**
  - **Paper A:** Radiology: Artificial Intelligence (RSNA), European Journal of Radiology Artificial Intelligence
  - **Paper B:** JMIR Medical Education, BMC Medical Education
- **파이프라인 통합 시:** Radiology (RCT 급 시험 점수 상승 데이터 필요, 현재는 현실적으로 불가능)
- 선정 기준 4~6개를 짧게: 스코프, 방법론 기여, 예상 심사 기간, OA/비용, 허용 형식
- 노트에는: 오늘 '1순위/2순위 shortlist 확정'까지만, 다음 액션(가이드라인 확인/투고 형식) 오너 지정, 통합 시 추후 가능성 언급

### Slide 9) FINAL Deployment QA & Survey Plan
- Image 5 사용
- **FINAL QA 프로세스:**
  - 전체 6,000개 카드 중 600개 샘플링 (10%)
  - 전문의 1인 + 전공의 2인 평가
  - 안정성 검토 후 배포 승인
  - 통계적 보장: blocking error rate < 1% (one-sided 99% confidence)
- **설문 계획:**
  - **Baseline 설문 (배포 전):** 인구학적 특성, LLM 경험, 자기효능감, 인지부하
  - **Post-exam 설문 (시험 후):** 사용 경험, 만족도, 기술 수용성, 교육적 질 평가
- 노트에는: S0(모델 선택)과 FINAL(배포 승인)의 목표 차이를 명확히, 참여율을 높이기 위한 운영장치 2~3개 제안, 설문 문항 타당성 검토 필요성

### Slide 10) Roles / Action Items / Next Meeting
- "오늘 결정사항 요약" + 오너/마감(예: D+2, D+3) + 다음 미팅 어젠다 초안
- **Action Items:**
  - S0 분석 계획 확정 문서화 (Owner: ___, D+2)
  - Target journal shortlist 확정 및 가이드라인 확인 (Owner: ___, D+3)
  - FINAL QA 프로세스 상세화 (Owner: ___, D+3)
  - Baseline/Post-exam 설문 문항 최종 검토 (Owner: ___, D+5)
  - 대체 평가자 확보 (Owner: ___, D+7)
- 노트에는: 회의 종료 후 SSOT 업데이트 항목과 책임 분담을 확정한다는 문장, 다음 미팅 시기 제안 (예: 1주 후)

---

## [옵션 부록(가능하면 2장 추가)]

### Appendix A) Stage Contracts 한 장 요약(S2/S3/S4 역할 경계)
- S2: Execution (LLM 호출, RAG/Thinking 적용, 텍스트 카드 생성)
- S3: Deterministic policy compiler (state-only, 결정론적 정책 컴파일)
- S4: Render-only (최종 Anki 덱/표/인포그래픽 렌더링)
- 각 단계의 입력/출력 계약 명시

### Appendix B) Image policy(해상도/비율/공정성) 요약
- 이미지 생성/선택 기준
- 해상도 및 비율 규칙
- 공정성 검증 방법

---

## [주의사항]

- 슬라이드 본문은 반드시 간결하게, 문장 길이 짧게
- Speaker Notes는 "왜 이 결론인지, 무엇을 결정해야 하는지, 다음 액션은 무엇인지"가 드러나게 작성
- 숫자/용어는 일관성 유지: 18 groups, 6 arms, 108 sets, set 구성(표+12 cards+infographic)
- 모델명은 정확히: gemini-3-flash-preview, gemini-3-pro-preview, gpt-5.2-pro-2025-12-11
- 출력은 최소한 슬라이드별 텍스트/노트/레이아웃 지시가 완결된 형태여야 함
- FINAL 배포 QA의 6000개 중 600개 샘플링, 전문의 1인 + 전공의 2인 평가 구조를 명확히 반영
- Baseline 설문과 Post-exam 설문의 목적과 시점을 구분하여 명시



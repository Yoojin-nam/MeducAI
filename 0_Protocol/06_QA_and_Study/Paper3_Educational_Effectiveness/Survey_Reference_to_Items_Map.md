# Survey Reference → Construct → Items Map (for Paper 3 / Pipeline-2)

**Status:** Working doc (manuscript-facing helper)  
**Goal:** 설문 문항이 어떤 **구성개념(construct)**을 측정하고, 어떤 **레퍼런스**(이론/검증 척도)에 근거하는지 1페이지로 연결한다.  

> ⚠️ Note: `7_Manuscript/references/*.bib`는 Zotero Better BibTeX 자동 동기화 파일이므로, **누락된 참고문헌(Eom 2016, Pintrich 1990 등)**은 Zotero에서 먼저 추가 후 동기화하는 것을 권장한다.

---

## 1) Where the items live (SSOT)

- **BASELINE 설문 (동의 직후)**: `3_Code/Scripts/create_google_form_baseline.js` + `0_Protocol/05_Pipeline_and_Execution/google_form_items_baseline_and_final.md`
- **FINAL 설문 (시험 후)**:  
  - 설문 원문: `0_Protocol/05_Pipeline_and_Execution/meduc_ai_final_survey_form.md`  
  - Google Form 생성 스크립트: `3_Code/Scripts/create_google_form_final.js`  
  - 문항 텍스트(수기 제작용): `0_Protocol/05_Pipeline_and_Execution/google_form_items_baseline_and_final.md`

> **스코어/변수 정의(SSOT)**: `0_Protocol/06_QA_and_Study/Study_Design/Survey_Scoring_and_Variable_Dictionary_Paper3.md`

---

## 2) Reference → Construct → Item mapping (high-signal)

### 2.1 Cognitive Load Theory / Multi-dimensional Cognitive Load Scale

- **Reference**
  - Sweller (Cognitive Load Theory): `@sweller1988cognitive` (exists in `7_Manuscript/references/shared.bib`)
  - Leppink et al. (multi-dimensional cognitive load scale): `@leppink2013cognitive` (exists in `7_Manuscript/references/paper3.bib`)
- **Construct(s)**
  - Extraneous cognitive load (co-primary in study design)
- **Items**
  - **BASELINE**: 인지 부하(현재 시점 기준) 문항군 (extraneous/intrinsic/germane 축을 포함하도록 구성됨)
  - **FINAL**: `F1–F3` (Extraneous cognitive load; 1–7)

### 2.2 Academic Self-Efficacy (MSLQ-derived)

- **Reference**
  - Pintrich & De Groot (MSLQ): `@pintrich1990` *(예상 키; Zotero 동기화 후 실제 키 확인 필요)*
  - PDF: `7_Manuscript/references/pdf/Pintrich_1990.pdf`
- **Construct(s)**
  - Academic self-efficacy (baseline covariate + change interpretation에 핵심)
- **Items**
  - **BASELINE**: 자기효능감 문항군 (1–7)

### 2.3 Learning Satisfaction (validated online learning satisfaction scale)

- **Reference**
  - Eom & Ashill (online learning satisfaction): `@eom2016` *(예상 키; Zotero 동기화 후 실제 키 확인 필요)*
  - PDF: `7_Manuscript/references/pdf/Eom_2016.pdf`
- **Construct(s)**
  - Global learning satisfaction (feature-level이 아니라 "학습 지원 도구로서의 만족도")
- **Items**
  - **FINAL**: `G1–G2` (Satisfaction; 1–5)

### 2.4 Technology Acceptance Model (TAM)

- **Reference**
  - Davis (TAM): `@davis1989perceived` (exists in `7_Manuscript/references/shared.bib`)
- **Construct(s)**
  - Perceived usefulness / ease of use / behavioral intention
- **Items**
  - **FINAL**: `G3 (Usefulness)`, `G4 (Ease of use)`, `G5 (Intention)` (1–5)

### 2.5 Trust / Calibration (automation bias / over-reliance)

- **Reference**
  - (개별 검증척도 대신) Survey overview 상 “custom items grounded in prior literature”로 운영
  - 문서 근거: `0_Protocol/06_QA_and_Study/Study_Design/Survey_Overview.md`
- **Construct(s)**
  - Trust, over-reliance(맹목 수용), critical use
- **Items**
  - **FINAL**: `E1–E3` (1–5)

### 2.6 Technical Accuracy (perceived) + Negative Events

- **Reference**
  - (주관 평가이므로) 설문 기반 safety signal로 운영
  - 문서 근거: `0_Protocol/06_QA_and_Study/Study_Design/Survey_Overview.md` + `0_Protocol/05_Pipeline_and_Execution/Baseline_vs_final_survey_mapping.md`
- **Construct(s)**
  - Perceived factual error frequency, harm perception, negative experience narrative
- **Items**
  - **FINAL**: `C1–C4` + (선택) 서술

### 2.7 Efficiency (time-based)

- **Reference**
  - Survey overview의 “time saved” 정의(도메인) + usage log 연동
- **Construct(s)**
  - Actual time, counterfactual time, edit/verification cost → derived time_saved
- **Items**
  - **FINAL**: `D1–D4`

### 2.8 NPS / Overall evaluation / improvement target

- **Reference**
  - (도구 평가에서 흔히 쓰는 운영 지표; paper context에서 “recommendation intent”로 해석)
- **Construct(s)**
  - Recommendation intent, improvement priority
- **Items**
  - **FINAL**: `H1 (0–10)`, `H3 (개선 영역 단일선택)` + 자유 의견

### 2.9 Non-user module (selection bias / implementation barriers)

- **Reference**
  - (검증 척도라기보다) “접근/인지/장벽”을 수집해 **비사용자의 맥락**을 해석하기 위한 운영 모듈
- **Construct(s)**
  - Awareness/exposure, barriers to adoption, future intention (feasibility)
- **Items**
  - **FINAL (A1=아니오인 경우만)**: `N1–N4`

---

## 3) Action items (for Zotero sync completeness)

- `Eom_2016.pdf`, `Pintrich_1990.pdf`는 현재 `7_Manuscript/references/*.bib`에 인용 키가 보이지 않습니다.  
  - **Zotero에 두 항목을 추가** → Better BibTeX 동기화 → `paper3.bib` 또는 `shared.bib`에 들어오는지 확인
  - 동기화 후 생성된 실제 citekey를 확인하여 위 섹션 2.2, 2.3의 예상 키(`@pintrich1990`, `@eom2016`)를 실제 키로 교체 권장
  - 예상 키는 일반적인 BibTeX 키 생성 규칙(첫 저자+연도)을 따름



# 0_Protocol — Start Here (Canonical Reading Order)

**Purpose:** 이 디렉토리는 MeducAI의 “문서로 증명되는” 설계/거버넌스/QA 규칙을 담는다.  
**Goal:** 아래 **필수 문서만 읽어도** 파이프라인 전체(역할, 경계, QA, FINAL 배포 승인 논리)를 이해할 수 있게 한다.

---

## 1) First read (필수 3개)

1. **Canonical 계층/충돌 해석(최상위 인덱스)**  
   - `0_Protocol/00_Governance/meduc_ai_pipeline_canonical_governance_index.md`

2. **현재 주 운영 SSOT(가장 최신 운영 기준)**  
   - `0_Protocol/01_Execution_Safety/stabilization/Weekly_Integrated_Conclusion_Operating_SSOT.md`

3. **파이프라인 헌법(단계 정의/권한 경계)**  
   - `0_Protocol/05_Pipeline_and_Execution/Pipeline_Canonical_Specification.md`

---

## 2) If you are running the pipeline (실행자 필수)

- **실행 계획 / 산출물**: `0_Protocol/05_Pipeline_and_Execution/Pipeline_Execution_Plan.md`
- **Fail-fast / Abort**: `0_Protocol/05_Pipeline_and_Execution/Pipeline_FailFast_and_Abort_Policy.md`
- **Arm/Model 해석 규칙(재현성)**: `0_Protocol/02_Arms_and_Models/ARM_CONFIGS_Provider_Model_Resolution.md`
- **Prompt 렌더링 안전(중요)**: `0_Protocol/01_Execution_Safety/Prompt_Rendering_Safety_Rule.md`
- **QC/Equipment 인포그래픽 스모크 런(시험포인트 1–2토큰, no OCR)**:  
  - `0_Protocol/05_Pipeline_and_Execution/Infographic_Only_QC_Equipment_Smoke_Run_2025-12-28.md`

---

## 3) If you are reviewing QA / release decisions (QA·배포 승인)

- **QA Framework (S0/S1)**: `0_Protocol/06_QA_and_Study/QA_Framework.md`
- **S1 오류율 검증 설계(Release gate)**: `0_Protocol/05_Pipeline_and_Execution/S1_QA_Design_Error_Rate_Validation.md`
- **S0/S1 설정 로그**: `0_Protocol/06_QA_and_Study/S0_S1_Configuration_Log.md`
- **S0/S1 완료 체크리스트**: `0_Protocol/06_QA_and_Study/S0_S1_Completion_Checklist_and_Final_Freeze.md`
- **FINAL QA 설계(배포본 v2 기준 엔드포인트/Adjudication/Flagger/Table 점검)**:  
  - `0_Protocol/06_QA_and_Study/QA_Operations/FINAL_QA_Design_and_Endpoints.md`

---

## 4) Prompt governance (인지적 정렬/Methods 문단/변경통제)

- **Prompt governance SSOT**: `0_Protocol/00_Governance/supporting/Prompt_governance/Prompt_Engineering_and_Cognitive_Alignment.md`
- **현재 실제 사용 프롬프트 버전(코드 기준)**: `3_Code/prompt/_registry.json`

---

## 5) Where the code lives (for traceability)

- Entrypoint: `3_Code/src/01_generate_json.py`
- Prompt bundle loader: `3_Code/src/tools/prompt_bundle.py`
- S3: `3_Code/src/03_s3_policy_resolver.py`
- S4: `3_Code/src/04_s4_image_generator.py`
- S5 PDF builder: `3_Code/src/07_build_set_pdf.py`

## 6) Step contract addenda (operational)
- **S3→S4 infographic text policy addendum (allowed-text, exam-point up to 2; no OCR)**:  
  - `0_Protocol/04_Step_Contracts/Step03_S3/S3_S4_Infographic_Text_Policy_Addendum_2025-12-28.md`



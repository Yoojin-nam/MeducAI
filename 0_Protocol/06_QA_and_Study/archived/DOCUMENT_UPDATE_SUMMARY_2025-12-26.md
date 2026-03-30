# QA 및 Study 문서 업데이트 요약 (2025-12-26)

**업데이트 일자:** 2025-12-26  
**목적:** FINAL 배포 후보(6,000+ 문항) QA의 엔드포인트/Freeze/Adjudication/Flagger 경계를 “비판점 반영” 형태로 단일 문서에 정리

---

## 1. 추가된 문서 (Draft → Canonical 후보)

### 1.1 FINAL QA 설계 및 엔드포인트 정의
- **신규:** `0_Protocol/06_QA_and_Study/QA_Operations/FINAL_QA_Design_and_Endpoints.md`
- **핵심 추가점:**
  - v1(Freeze 평가본) / patch log / v2(최종 배포본) **버전 경계** 명시
  - Primary safety endpoint: **Critical error rate** (CI 상한 기반 Go/No-Go)
  - Primary educational endpoint: **Objective alignment(Yes/No)** (필수)
  - 전문의 300은 **random/high-risk strata 분리 보고**(전체율로 오해 금지)
  - 전공의 불일치 및 flagger 기반 **adjudication SOP** 고정
  - Flagger LLM은 **수정 금지(오직 triage/flagging)** 및 unflagged 무작위 감사 샘플 규칙 “필수” 선언
  - (추가) **S1 master table 점검(테이블 특화 flagger)**: 구조 FAIL-fast + row/col/cell location 기반 이슈 출력, 추천 모델 및 NDJSON/CSV 출력 포맷 제안 포함

---

## 2. 변경하지 않은 문서(의도적)

본 업데이트는 “정리 문서 추가”에 한정하며, 아래 Canonical 문서들은 이번 커밋에서 변경하지 않았다.

- `0_Protocol/06_QA_and_Study/QA_Framework.md`
- `0_Protocol/05_Pipeline_and_Execution/S1_QA_Design_Error_Rate_Validation.md`
- `0_Protocol/06_QA_and_Study/QA_Operations/QA_Blinding_Procedure.md`
- `0_Protocol/06_QA_and_Study/QA_Operations/QA_Evaluation_Rubric.md`

---

**작성일:** 2025-12-26  
**작성자:** MeducAI 문서 업데이트(Protocol)



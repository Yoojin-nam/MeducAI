# 문서 정리 요약 — 2025-12-20

**Status:** Reference (Summary)  
**Last Updated:** 2025-12-20  
**Purpose:** 2025-12-20에 수행된 문서 정리 및 구조화 작업 요약

**Related Documents:**
- `Implementation_Change_Log_2025-12-20.md` - 통합 구현 변경 로그
- `Canonical_Merge_Log_2025-12-17.md` - Canonical merge 기록

---

## 개요

이 문서는 2025-12-20 저녁에 수행된 문서 정리 및 구조화 작업을 기록합니다.

---

## 문서 이동 작업

### 1. Gemini 3 코드 검토 문서 이동

**이동 전:**
- 위치: `3_Code/src/GEMINI_3_CODE_REVIEW.md`
- 문제: 코드 디렉토리에 프로토콜 문서가 위치

**이동 후:**
- 위치: `0_Protocol/02_Arms_and_Models/GEMINI_3_CODE_REVIEW.md`
- 이유: 모델/ARM 관련 문서이므로 `02_Arms_and_Models/` 디렉토리가 적절

**문서 내용:**
- Gemini 3 가이드라인 준수 여부 검토
- Thinking Level, Temperature, max_output_tokens 설정 검토
- 코드 구현 상태 및 권장사항

---

### 2. S4 프롬프트 템플릿 스모크 테스트 계획 이동

**이동 전:**
- 위치: `3_Code/src/S4_Prompt_Template_Smoke_Test_Plan.md`
- 문제: 코드 디렉토리에 테스트 계획 문서가 위치

**이동 후:**
- 위치: `0_Protocol/04_Step_Contracts/Step04_S4/S4_Prompt_Template_Smoke_Test_Plan.md`
- 이유: S4 단계별 계약 문서와 함께 위치하는 것이 적절

**문서 내용:**
- S3 prompt_en 생성 검증 계획
- CONCEPT lane (S1_TABLE_VISUAL) 및 EXAM lane (S2_CARD_IMAGE) 테스트 절차
- 프롬프트 템플릿 검증 체크리스트

---

## 문서 구조 점검 결과

### ✅ 적절히 배치된 문서들

1. **모델/ARM 관련 문서**
   - `0_Protocol/02_Arms_and_Models/GEMINI_3_CODE_REVIEW.md` ✅ (이동 완료)
   - `0_Protocol/02_Arms_and_Models/ARM_CONFIGS_Provider_Model_Resolution.md` ✅
   - `0_Protocol/02_Arms_and_Models/README.md` ✅

2. **Step 계약 문서**
   - `0_Protocol/04_Step_Contracts/Step04_S4/S4_Prompt_Template_Smoke_Test_Plan.md` ✅ (이동 완료)
   - 각 Step별 Implementation Update Log ✅
   - 각 Step별 Entity Definition ✅

3. **QA 및 연구 문서**
   - `0_Protocol/06_QA_and_Study/QA_Framework.md` ✅
   - `0_Protocol/06_QA_and_Study/QA_Operations/` 하위 문서들 ✅

4. **파이프라인 실행 문서**
   - `0_Protocol/05_Pipeline_and_Execution/STAGE_SEPARATION_TEST_REPORT.md` ✅
   - 테스트 리포트는 실행 관련 문서로 적절한 위치

---

## 문서 구조 원칙

### 디렉토리별 역할

1. **`00_Governance/`**: 거버넌스 및 메타 문서
   - 문서 버전 관리 정책
   - 용어집 및 식별자 등록부
   - 구현 변경 로그 (통합)

2. **`01_Execution_Safety/`**: 실행 안전성 규칙
   - 프롬프트 렌더링 안전 규칙
   - 파일 교체 패치 규칙

3. **`02_Arms_and_Models/`**: ARM 및 모델 설정
   - ARM 설정 해석 규칙
   - 모델별 코드 검토 문서
   - 모델별 정책 문서

4. **`03_CardCount_and_Allocation/`**: 카드 수 및 할당
   - S0 할당 규칙
   - FINAL 할당 규칙

5. **`04_Step_Contracts/`**: 단계별 계약
   - 각 Step별 엔티티 정의
   - 각 Step별 구현 업데이트 로그
   - Step별 테스트 계획

6. **`05_Pipeline_and_Execution/`**: 파이프라인 실행
   - 파이프라인 헌법 및 실행 계획
   - 실행 도구 업데이트 로그
   - 테스트 리포트

7. **`06_QA_and_Study/`**: QA 및 연구
   - QA 프레임워크
   - QA 운영 문서
   - 연구 설계 문서

---

## 문서 배치 가이드라인

### 코드 디렉토리 (`3_Code/`)에 있어야 할 문서
- ❌ 프로토콜 문서 (이동 필요)
- ✅ 코드 주석 및 인라인 문서
- ✅ 코드 실행 가이드 (README 등)

### 프로토콜 디렉토리 (`0_Protocol/`)에 있어야 할 문서
- ✅ 모든 Canonical 문서
- ✅ 구현 업데이트 로그
- ✅ 테스트 계획 및 리포트
- ✅ 코드 검토 문서
- ✅ 정책 및 규칙 문서

---

## 향후 권장사항

### 1. 문서 생성 시 위치 확인
- 새 문서 작성 시 적절한 디렉토리 확인
- `DOCUMENT_STATUS_GUIDE.md` 참조

### 2. 정기적인 문서 구조 점검
- 월 1회 문서 구조 점검 권장
- 잘못 배치된 문서 발견 시 즉시 이동

### 3. 문서 이동 시 변경 로그 업데이트
- 문서 이동 시 `Implementation_Change_Log`에 기록
- 관련 문서 간 링크 업데이트

---

## 관련 문서

- `DOCUMENT_STATUS_GUIDE.md`: 문서 참고 가이드
- `Implementation_Change_Log_2025-12-20.md`: 통합 변경 로그
- `meduc_ai_pipeline_canonical_governance_index.md`: 문서 계층 구조 인덱스

---

## 변경 이력

- **2025-12-20 (저녁)**: 문서 정리 및 구조화
  - `GEMINI_3_CODE_REVIEW.md` 이동
  - `S4_Prompt_Template_Smoke_Test_Plan.md` 이동
  - 문서 구조 점검 및 가이드라인 정리


# Pipeline and Execution 문서 정리 요약 (2025-12-20)

**정리 일자:** 2025-12-20  
**목적:** 최근 변경 사항 반영, 중복 문서 정리, 문서 구조 개선

---

## 1. 주요 업데이트 사항

### 1.1 README.md 업데이트

**변경 내용:**
- Last Updated: 2025-12-17 → **2025-12-20**
- **Section 3.4 추가:** Pipeline Execution & Implementation 문서 인덱스
  - Pipeline_Canonical_Specification.md
  - Pipeline_Execution_Plan.md
  - Code_to_Protocol_Traceability.md (v1.6, latest)
  - S1_S2_Independent_Execution_Design.md (✅ Implemented)
  - S0_Execution_Plan_Without_S4.md
  - README_run.md
  - Implementation_Update_Log_2025-12-20.md
- **Section 4.1 추가:** Pipeline Execution Workflow (S1-S5 전체 워크플로우)
- **Section 6 업데이트:** `06_QA_and_Study/` 디렉토리 관계 추가

### 1.2 문서 상태 확인

**Canonical Documents (최신 상태):**
- ✅ **Pipeline_Canonical_Specification.md** - v1.5 반영 완료 (2025-12-20)
  - S3/S4/S5 업데이트 반영
  - Q2 이미지 필수화 (v1.5)
  - S1 테이블 비주얼 추가
  - 이미지 모델: nano-banana-pro-preview
- ✅ **Pipeline_Execution_Plan.md** - v1.1 (Canonical)
  - S1/S2 독립 실행 기능 반영 (Section 11)
  - S1 Schema Freeze 선언 (Section 10)
- ✅ **Code_to_Protocol_Traceability.md** - v1.6 (최신)
  - S1-S5 전체 구현 완료 상태 반영
  - 최근 업데이트 (샘플 PDF/Anki 생성, S4 manifest 재생성 등) 반영
- ✅ **S1_S2_Independent_Execution_Design.md** - v1.1 (✅ Implemented)
  - 구현 완료 상태 명시

**Operational Documents:**
- ✅ **README_run.md** - 최신 실행 가이드 (2025-12-20)
  - S1/S2/S3/S4 단계별 실행 방법 포함
  - 6-Arm Full Pipeline 실행 방법 포함
- ✅ **S0_Execution_Plan_Without_S4.md** - 특정 상황 실행 계획 (유지)
- ✅ **Implementation_Update_Log_2025-12-20.md** - 최근 업데이트 기록

**Deprecated Documents:**
- ⚠️ **expert_qa_accuracy_evaluation_form.md** - DEPRECATED
  - Status: Deprecated
  - Superseded by: `06_QA_and_Study/QA_Operations/QA_Evaluation_Rubric.md`
  - README.md에 명시적으로 표시됨

---

## 2. 문서 구조 개선

### 2.1 README.md 구조 개선

**Before:**
- Pipeline execution 문서가 명시적으로 인덱스되지 않음
- Pipeline workflow가 QA workflow와 혼재

**After:**
- Section 3.4 추가: Pipeline Execution & Implementation 문서 인덱스
- Section 4.1 추가: Pipeline Execution Workflow (S1-S5)
- Section 4.2: QA Evaluation Workflow (기존 내용 유지)
- 명확한 문서 역할 구분

### 2.2 문서 관계 명확화

**Pipeline Execution Documents:**
- `Pipeline_Canonical_Specification.md` - 개념적 명세 (Entity, Step 정의)
- `Pipeline_Execution_Plan.md` - 실행 계약 (JSONL Contract-First)
- `Code_to_Protocol_Traceability.md` - 코드-프로토콜 매핑 및 구현 상태

**Operational Documents:**
- `README_run.md` - 실행 가이드 (운영용)
- `S0_Execution_Plan_Without_S4.md` - 특정 상황 실행 계획
- `S1_S2_Independent_Execution_Design.md` - S1/S2 독립 실행 설계

**Update Logs:**
- `Implementation_Update_Log_2025-12-20.md` - 최근 구현 업데이트 기록

---

## 3. 중복 문서 정리

### 3.1 유지된 문서

**Canonical Documents:**
- `Pipeline_Canonical_Specification.md` - 유지 (최신 상태)
- `Pipeline_Execution_Plan.md` - 유지 (최신 상태)
- `Code_to_Protocol_Traceability.md` - 유지 (v1.6, 최신)

**Operational Documents:**
- `README_run.md` - 유지 (운영 가이드)
- `S0_Execution_Plan_Without_S4.md` - 유지 (특정 상황 계획)
- `S1_S2_Independent_Execution_Design.md` - 유지 (구현 완료 상태)

**Update Logs:**
- `Implementation_Update_Log_2025-12-20.md` - 유지 (최근 업데이트 기록)

### 3.2 Deprecated 문서

**expert_qa_accuracy_evaluation_form.md:**
- Status: **DEPRECATED**
- Superseded by: `06_QA_and_Study/QA_Operations/QA_Evaluation_Rubric.md`
- README.md에 명시적으로 표시됨
- 문서는 보존 (archived, not deleted)

---

## 4. 구현 상태 요약

### 4.1 Pipeline Steps

**Implementation Status (2025-12-20):**
- ✅ **S1 (Group-level structuring)**: 구현 완료 (v1.3, Frozen)
- ✅ **S2 (Card generation)**: 구현 완료 및 안정화
- ✅ **S3 (Policy resolution & image spec)**: 구현 완료 (v1.5)
- ✅ **S4 (Image generation)**: 구현 완료 (v1.5)
- ✅ **S5 (Export & packaging)**: 구현 완료 (PDF Builder + Anki Export)

**전체 파이프라인 (S1→S2→S3→S4→S5) 구현 완료**

### 4.2 주요 기능

**S1/S2 독립 실행:**
- ✅ `--stage 1`: S1만 실행
- ✅ `--stage 2`: S2만 실행 (S1 출력 필요)
- ✅ `--stage both`: S1+S2 통합 실행 (기본값)

**6-Arm Full Pipeline:**
- ✅ `run_6arm_s1_s2_full.py`: 전체 파이프라인 자동 실행
- ✅ `--arms` 옵션: 특정 arm만 선택 실행 가능

**샘플 생성:**
- ✅ `generate_sample_pdf_anki.py`: Specialty별 랜덤 그룹 선택
- ✅ `generate_sample_all_specialties.py`: 모든 specialty 통합
- ✅ `test_6arm_single_group.py`: 단일 그룹 6-arm 테스트

**S4 Manifest 재생성:**
- ✅ `regenerate_s4_manifest.py`: 기존 이미지 파일로부터 manifest 재생성

---

## 5. 문서 정리 결과

### 5.1 정리 완료

✅ **README.md 업데이트 완료**
- 최신 문서 인덱스 추가
- Pipeline Execution Workflow 추가
- 문서 관계 명확화

✅ **문서 상태 확인 완료**
- 모든 Canonical 문서 최신 상태 확인
- Deprecated 문서 명시

✅ **구조 개선 완료**
- Pipeline execution과 QA evaluation 워크플로우 분리
- 문서 역할 명확화

### 5.2 유지된 문서 구조

```
0_Protocol/05_Pipeline_and_Execution/
├── README.md (✅ Updated)
├── Pipeline_Canonical_Specification.md (✅ Latest)
├── Pipeline_Execution_Plan.md (✅ Latest)
├── Code_to_Protocol_Traceability.md (✅ v1.6, Latest)
├── S1_S2_Independent_Execution_Design.md (✅ Implemented)
├── S0_Execution_Plan_Without_S4.md (✅ Maintained)
├── README_run.md (✅ Latest)
├── Implementation_Update_Log_2025-12-20.md (✅ Latest)
└── expert_qa_accuracy_evaluation_form.md (⚠️ Deprecated)
```

---

## 6. 다음 단계

### 6.1 문서 유지

- 모든 Canonical 문서는 최신 상태 유지
- Implementation_Update_Log는 지속적으로 업데이트
- README.md는 문서 구조 변경 시 즉시 업데이트

### 6.2 향후 개선 사항

- Pipeline_Execution_Plan.md와 Pipeline_Canonical_Specification.md의 관계 더 명확히 문서화 (선택사항)
- S0_Execution_Plan_Without_S4.md가 일반적인 실행 계획으로 통합 가능한지 검토 (선택사항)

---

**작성일:** 2025-12-20  
**작성자:** Document Cleanup Task  
**상태:** 완료


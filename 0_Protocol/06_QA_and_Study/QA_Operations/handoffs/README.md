# QA Operations Handoffs

**Purpose**: FINAL QA 및 배포 관련 작업 기록  
**Last Updated**: 2026-01-15

---

## 통합 문서

### [FINAL Distribution Execution History](FINAL_Distribution_Execution_History.md)

**범위**: FINAL_DISTRIBUTION armG 실행 및 QA 배포 작업 기록

**주요 내용**:
- FINAL_DISTRIBUTION Execution Guide
- S5 검증 실행 (Mode Split)
- AppSheet Export
- Assignment 생성 (6000 cards)
- Deployment Checklist

**원본 문서**: 4개
- HANDOFF_2026-01-15_FINAL_DISTRIBUTION_Execution_Guide.md
- HANDOFF_2026-01-15_Current_Work_Status.md
- HANDOFF_2026-01-04_S5_Execution_Ready.md
- HANDOFF_2026-01-04_FINAL_QA_Design_Update.md

---

## Known Issues & Critical Warnings

### ⚠️ [AppSheet Time Calculation Issue](APPSHEET_TIME_CALCULATION_ISSUE_2026-01-09.md)

**Status**: Open (2026-01-09)  
**Severity**: High (Data Integrity)

**Issue**: Ratings 시트의 시간 계산 컬럼에 데이터 무결성 오류

**Impact**:
- `post_duration_sec`: 98/107개 행에서 잘못된 값 (s5 시간으로 덮어씀)
- `s5_duration_sec`: 전부 비어있음 (계산 로직 누락)

**분석 시 필수 조치**:
- ❌ duration_sec 컬럼 사용 금지
- ✅ 타임스탬프 차이로 재계산 필수

**감사 파일**: `appsheet_time_audit.xlsx` (전체 행 검증 결과)

**수정 계획**:
1. AppSheet 로직 수정 (post/s5 duration 분리)
2. 기존 데이터 복구 (타임스탬프 기반 재계산)
3. 검증 스크립트 재실행

---

## 관련 Protocol 문서

### QA Framework
- [`0_Protocol/06_QA_and_Study/QA_Framework.md`](../../QA_Framework.md)
- [`0_Protocol/06_QA_and_Study/QA_Operations/FINAL_QA_Design_and_Endpoints.md`](../FINAL_QA_Design_and_Endpoints.md)

### Assignment Generation
- [`0_Protocol/06_QA_and_Study/QA_Operations/FINAL_QA_Assignment_Guide.md`](../FINAL_QA_Assignment_Guide.md)

### AppSheet
- [`0_Protocol/06_QA_and_Study/QA_Operations/AppSheet_QA_System_Specification.md`](../AppSheet_QA_System_Specification.md)

---

## 다른 Handoff 문서

### Pipeline Execution
**위치**: [`0_Protocol/05_Pipeline_and_Execution/handoffs/`](../../../05_Pipeline_and_Execution/handoffs/)

---

## 원본 문서 위치

**Archive**: [`5_Meeting/archive/handoffs_2026-01/`](../../../../5_Meeting/archive/handoffs_2026-01/)

---

**작성일**: 2026-01-15  
**최종 업데이트**: 2026-01-09 (AppSheet 시간 계산 이슈 추가)  
**작성자**: AI Assistant


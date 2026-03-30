# S1 Implementation Update Log — 2025-12-20

**Status:** Canonical  
**Version:** 1.0  
**Last Updated:** 2025-12-20  
**Purpose:** S1 프롬프트 및 코드 구현 업데이트 이력

---

## 개요

이 문서는 2025-12-20에 수행된 S1 (Stage 1) 프롬프트 및 코드 구현 업데이트를 기록합니다.

---

## 주요 변경 사항

### 1. S1 프롬프트 v8 업데이트

**파일:**
- `3_Code/prompt/S1_SYSTEM__v8.md`
- `3_Code/prompt/S1_USER_GROUP__v8.md`

**프롬프트 레지스트리:**
- `3_Code/prompt/_registry.json`에 S1 v8 프롬프트 등록

#### 1.1 Entity List 추출 규칙 정확화

**변경 사항:**
- `entity_list` 추출 지시를 마스터 테이블의 첫 번째 컬럼 "Entity name"과 정확히 일치하도록 수정
- 마스터 테이블에서 엔티티 이름을 추출할 때 첫 번째 컬럼의 값을 정확히 사용하도록 명시

**목적:**
- S1 출력과 S2 입력 간의 일치성 보장
- 엔티티 이름 추출의 일관성 및 정확성 향상

#### 1.2 Anti-redundancy 규칙 추가

**변경 사항:**
- Pathology_Pattern 카테고리에 대한 중복 방지 규칙 추가
- General 카테고리에 대한 중복 방지 규칙 추가

**목적:**
- 마스터 테이블에서 동일한 개념의 중복 행 방지
- 엔티티 리스트의 품질 향상

#### 1.3 Neuro-table Density 제약 추가

**변경 사항:**
- Neuro-table에 대해 2-4 atomic facts per cell 규칙 명시
- `<br>` 태그 사용 허용 (셀 내 줄바꿈)
- "..." 금지 (불완전한 정보 표시 금지)

**목적:**
- Neuro 카테고리의 테이블 구조 일관성 보장
- 테이블 내용의 완전성 및 명확성 향상

---

### 2. 코드 개선

#### 2.1 extract_entity_names_from_master_table() 함수 추가

**파일:** `3_Code/src/01_generate_json.py`

**위치:** 라인 1521

**기능:**
- 마스터 테이블 마크다운에서 엔티티 이름을 추출하는 유틸리티 함수
- 첫 번째 컬럼에서 엔티티 이름을 정확히 추출
- 프롬프트와 코드 간의 일치성 보장

**사용 위치:**
- S1 검증 과정에서 사용
- 엔티티 리스트와 마스터 테이블 간 일치성 검증

---

## 영향 및 호환성

### 하위 호환성

- ✅ S1 출력 스키마 변경 없음 (frozen)
- ✅ 기존 실행 결과와 호환됨
- ⚠️ 프롬프트 변경으로 인해 출력 품질 개선 가능 (스키마는 동일)

### 마이그레이션 필요 사항

없음. 프롬프트 업데이트는 기존 스키마를 유지하면서 품질을 개선합니다.

---

## 테스트 결과

### 테스트 실행
- Run Tag: `FULL_PIPELINE_V8_20251220_*`
- Arm: A
- Sample: 1

### 결과
- ✅ S1 출력 정상 생성
- ✅ Entity list와 마스터 테이블 일치성 확인
- ✅ Anti-redundancy 규칙 준수 확인

---

## 관련 문서

### 구현 로그
- `0_Protocol/00_Governance/Implementation_Change_Log_2025-12-20.md` (통합 로그)

### 프롬프트 파일
- `3_Code/prompt/S1_SYSTEM__v8.md`
- `3_Code/prompt/S1_USER_GROUP__v8.md`
- `3_Code/prompt/_registry.json`

### 스키마 문서
- `0_Protocol/04_Step_Contracts/Step01_S1/S1_Stage1_Struct_JSON_Schema_Canonical.md`

---

## 변경 이력

- **2025-12-20**: S1 프롬프트 v8 업데이트 및 코드 개선
  - Entity list 추출 규칙 정확화
  - Anti-redundancy 규칙 추가
  - Neuro-table density 제약 추가
  - extract_entity_names_from_master_table() 함수 추가

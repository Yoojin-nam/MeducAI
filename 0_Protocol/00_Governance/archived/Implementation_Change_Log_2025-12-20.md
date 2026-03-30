# Implementation Change Log — 2025-12-20

**Status:** Canonical  
**Last Updated:** 2025-12-20  
**Purpose:** 2025-12-20에 수행된 모든 구현 변경사항 통합 로그

---

## 개요

이 문서는 2025-12-20에 수행된 모든 구현 변경사항을 통합하여 기록합니다.

---

## 주요 작업 항목

### 1. S1 & S2 프롬프트 및 코드 업데이트

#### 1.1 S1 프롬프트 v8 업데이트

**파일:** 
- `3_Code/prompt/S1_SYSTEM__v8.md`
- `3_Code/prompt/S1_USER_GROUP__v8.md`

**변경 사항:**
- `entity_list` 추출 지시를 마스터 테이블의 첫 번째 컬럼 "Entity name"과 정확히 일치하도록 수정
- Anti-redundancy 규칙 추가 (Pathology_Pattern, General 카테고리)
- Neuro-table density 제약 추가 (2-4 atomic facts per cell, `<br>` 사용, "..." 금지)

**프롬프트 레지스트리 업데이트:**
- `3_Code/prompt/_registry.json`에 S1 v8 프롬프트 등록

#### 1.2 S2 프롬프트 v7 개선

**파일:**
- `3_Code/prompt/S2_SYSTEM__v7.md`
- `3_Code/prompt/S2_USER_ENTITY__v7.md`

**변경 사항:**
- Q2, Q3 카드의 `front` 필드에는 문제만 포함, `options` 배열에 선택지 포함하도록 명시
- MCQ 카드에서 front 텍스트와 options 분리 규칙 명확화

#### 1.3 S1/S2 코드 개선

**파일:** `3_Code/src/01_generate_json.py`

**주요 변경 사항:**

1. **`extract_entity_names_from_master_table()` 함수 추가**
   - 마스터 테이블에서 엔티티 이름을 추출하는 유틸리티 함수 추가
   - 첫 번째 컬럼에서 엔티티 이름을 정확히 추출하여 프롬프트와 일치성 보장

2. **`validate_stage2()` 함수 개선**
   - `options` 저장 로직 개선: 검증된 `options`와 `correct_index` 필드가 정확히 저장되도록 수정
   - MCQ 카드에 대한 필수 필드 검증 강화
   - 에러 메시지 개선

3. **`validate_and_fill_entity()` 함수 수정 (중요한 버그 수정)**
   - **근본 원인**: S2 결과에서 `options`와 `correct_index` 필드가 저장되지 않는 문제 해결
   - `options`와 `correct_index` 필드 보존 로직 추가 (라인 412-450)
   - `card_role`과 `image_hint`를 보존하는 것과 동일한 방식으로 처리
   - MCQ 카드 (Q2, Q3)의 선택지 정보가 S2 출력에 정상적으로 포함되도록 수정

**영향:**
- Anki 덱 생성 시 MCQ 카드에 선택지가 정상적으로 표시됨
- 이전 run tag (`FULL_PIPELINE_V8_20251220_*`)는 재실행 필요

---

### 2. PDF 및 Anki 출력 개선

#### 2.1 PDF 생성 개선

**파일:** `3_Code/src/07_build_set_pdf.py`

**변경 사항:**
- HTML 태그 정리 함수 추가 (`<br>` → `<br/>`, `<para>` 제거)
- 마크다운 변환 시 HTML 태그 일관성 보장

#### 2.2 Anki 덱 생성 개선

**파일:** `3_Code/src/07_export_anki_deck.py`

**변경 사항:**
- 에러 처리 개선
- MCQ 카드 검증 강화 (5개 선택지 필수 검증)

---

### 3. 파이프라인 실행 스크립트 개선

#### 3.1 전체 파이프라인 스크립트 개선

**파일:** `3_Code/Scripts/run_full_pipeline_armA_sample_v8.sh`

**변경 사항:**
- RUN_TAG를 인자로 받도록 수정 (없으면 자동 생성)
- 빈 파일 체크 추가: S2 결과 파일이 비어있는지 검증
- 각 단계별 성공/실패 확인 강화

**사용 예시:**
```bash
# RUN_TAG 자동 생성
bash 3_Code/Scripts/run_full_pipeline_armA_sample_v8.sh

# RUN_TAG 지정
bash 3_Code/Scripts/run_full_pipeline_armA_sample_v8.sh FULL_PIPELINE_V8_20251220_180000
```

#### 3.2 PDF/Anki 전용 스크립트 추가

**파일:** `3_Code/Scripts/run_pdf_anki_only.sh` (신규)

**용도:**
- S1/S2/S3/S4가 이미 완료된 경우 PDF와 Anki 덱만 생성
- 전체 파이프라인을 재실행하지 않고 출력물만 재생성

**사용 예시:**
```bash
bash 3_Code/Scripts/run_pdf_anki_only.sh FULL_PIPELINE_V8_20251220_180000
```

---

### 4. S3 & S4 코드 업데이트 및 문서화

#### 1.1 S3 (Policy Resolver & ImageSpec Compiler) 업데이트

**파일:** `3_Code/src/03_s3_policy_resolver.py`

**변경 사항:**
- Q2 이미지 정책 변경: `image_required = True` (필수)
- S1 테이블 비주얼 스펙 컴파일 추가
- 프롬프트 개선 (카드 텍스트, 정답 포함)
- 정답 추출 로직 추가

**상세:** `0_Protocol/04_Step_Contracts/Step03_S3/S3_Implementation_Update_Log_2025-12-20.md` 참조

#### 1.2 S4 (Image Generator) 업데이트

**파일:** `3_Code/src/04_s4_image_generator.py`

**변경 사항:**
- 모델명 변경: `models/nano-banana-pro-preview`
- 스펙 종류별 분기 처리 (카드 이미지 vs 테이블 비주얼)
- 파일명 규칙 확장
- Fail-fast 규칙 확장
- 이미지 추출 로직 개선

**상세:** `0_Protocol/04_Step_Contracts/Step04_S4/S4_Implementation_Update_Log_2025-12-20.md` 참조

#### 1.3 코드 동작 방식 문서 작성

**파일:** `S3_S4_Code_Documentation.md` (프로젝트 루트)

**내용:**
- S3/S4 입출력 값 정리
- 내부 진행방법 설명
- 프롬프트 템플릿 정리
- 전체 파이프라인 흐름도

---

### 5. 파이프라인 실행 도구 개선

#### 5.1 6-Arm 실행 스크립트 개선

**파일:** `3_Code/Scripts/run_6arm_s1_s2_full.py`

**변경 사항:**
- `--arms` 옵션 추가: 특정 arm만 선택 실행 가능
- 리포트 저장 위치 변경: `2_Data/metadata/generated/{run_tag}/`

**상세:** `0_Protocol/05_Pipeline_and_Execution/Implementation_Update_Log_2025-12-20.md` 참조

#### 5.2 모델 확인 도구 업데이트

**파일:** `3_Code/src/tools/check_models.py`

**변경 사항:**
- `google.generativeai` → `google.genai` SDK로 변경
- 이미지/텍스트 모델 구분 표시

---

### 6. 문서화 및 정리

#### 3.1 구현 업데이트 로그 작성

**작성된 문서:**
1. `0_Protocol/04_Step_Contracts/Step01_S1/S1_Implementation_Update_Log_2025-12-20.md`
2. `0_Protocol/04_Step_Contracts/Step02_S2/S2_Implementation_Update_Log_2025-12-20.md`
3. `0_Protocol/04_Step_Contracts/Step03_S3/S3_Implementation_Update_Log_2025-12-20.md`
4. `0_Protocol/04_Step_Contracts/Step04_S4/S4_Implementation_Update_Log_2025-12-20.md`
5. `0_Protocol/05_Pipeline_and_Execution/Implementation_Update_Log_2025-12-20.md`

#### 3.2 추적성 문서 업데이트

**파일:** `0_Protocol/05_Pipeline_and_Execution/Code_to_Protocol_Traceability.md`

**변경 사항:**
- v1.4 → v1.5로 버전 업데이트
- 오늘의 변경사항 반영

#### 3.3 기존 리포트 파일 정리

**작업:**
- 프로젝트 루트에 있던 리포트 18개를 각 run_tag 디렉토리로 이동
- 프로젝트 루트 정리 완료

---

## 변경사항 요약

### 코드 변경

| 파일 | 변경 내용 |
|------|----------|
| `01_generate_json.py` | extract_entity_names_from_master_table() 추가, validate_stage2() 개선, **validate_and_fill_entity() 버그 수정 (options/correct_index 보존)** |
| `07_build_set_pdf.py` | HTML 태그 정리 함수 추가 |
| `07_export_anki_deck.py` | 에러 처리 개선 |
| `03_s3_policy_resolver.py` | Q2 필수화, 테이블 비주얼 추가, 프롬프트 개선 |
| `04_s4_image_generator.py` | 모델 변경, 스펙 분기, 추출 로직 개선 |
| `run_full_pipeline_armA_sample_v8.sh` | RUN_TAG 인자 지원, 빈 파일 체크 추가 |
| `run_pdf_anki_only.sh` | 신규 스크립트 추가 (PDF/Anki만 생성) |
| `run_6arm_s1_s2_full.py` | `--arms` 옵션, 리포트 위치 변경 |
| `check_models.py` | SDK 변경 |

### 프롬프트 변경

| 파일 | 버전 | 변경 내용 |
|------|------|----------|
| `S1_SYSTEM__v8.md` | v8 | entity_list 추출 규칙 정확화, Anti-redundancy 규칙, Neuro-table density 제약 |
| `S1_USER_GROUP__v8.md` | v8 | S1 시스템 프롬프트와 일치하도록 업데이트 |
| `S2_SYSTEM__v7.md` | v7 | Q2/Q3 front와 options 분리 규칙 명확화 |
| `S2_USER_ENTITY__v7.md` | v7 | S2 시스템 프롬프트와 일치하도록 업데이트 |

### 문서 추가

| 파일 | 내용 |
|------|------|
| `S3_S4_Code_Documentation.md` | 코드 동작 방식 전체 정리 |
| `S3_Implementation_Update_Log_2025-12-20.md` | S3 업데이트 상세 로그 |
| `S4_Implementation_Update_Log_2025-12-20.md` | S4 업데이트 상세 로그 |
| `Implementation_Update_Log_2025-12-20.md` | 파이프라인 도구 업데이트 로그 |

### 문서 업데이트

| 파일 | 변경 내용 |
|------|----------|
| `Code_to_Protocol_Traceability.md` | v1.5로 업데이트, 오늘의 변경사항 반영 |

---

## 테스트 결과

### 테스트 실행 1 (S3/S4)
- Run Tag: `test_armA_sample1_v5`
- Arm: A
- Sample: 1

### 결과
- ✅ S1: 성공
- ✅ S2: 성공
- ✅ S3: 성공 (Policy Manifest: 12 records, Image Spec: 9 records)
- ✅ S4: 성공 (모든 이미지 생성 완료)

### 테스트 실행 2 (S2 options 필드 저장 문제 해결)
- Run Tag: `TEST_OPTIONS_FIX_20251220_172357`
- 목적: `validate_and_fill_entity()` 함수 수정 후 options 필드 보존 검증

### 결과
- ✅ 전체 파이프라인 성공적으로 완료
- ✅ 8개 MCQ 카드 모두 `options`와 `correct_index` 필드 정상 저장 확인
- ✅ Anki 덱 생성: 성공 (에러 없음)
- ✅ PDF 생성: 성공

**검증 명령어:**
```bash
python3 3_Code/test_options_check.py 2_Data/metadata/generated/TEST_OPTIONS_FIX_20251220_172357/s2_results__armA.jsonl
```

**결과:**
```
Total MCQ cards: 8
MCQ with options: 8
MCQ without options: 0
✅ PASS: All 8 MCQ cards have options and correct_index
```

---

## 중요 버그 수정

### S2 options 필드 저장 문제 해결

**증상:**
- Raw LLM 출력에는 `options`와 `correct_index`가 정상적으로 생성됨
- 하지만 `s2_results__armA.jsonl` 파일에는 `options` 필드가 없음
- 결과적으로 Anki 덱 생성 시 에러 발생: `MCQ must have exactly 5 options, got 0`

**영향받는 Run Tags:**
- `FULL_PIPELINE_V8_20251220_161953`
- `FULL_PIPELINE_V8_20251220_162628`
- `FULL_PIPELINE_V8_20251220_163147`
- `FULL_PIPELINE_V8_20251220_163907`
- `FULL_PIPELINE_V8_20251220_164637`
- `FULL_PIPELINE_V8_20251220_170722`

**근본 원인:**
- `validate_and_fill_entity()` 함수가 `options`와 `correct_index`를 보존하지 않았음
- `validate_stage2()`에서는 검증하고 저장했지만, 이후 `validate_and_fill_entity()`에서 손실됨

**해결 방법:**
- `validate_and_fill_entity()` 함수 수정하여 `options`와 `correct_index` 필드 보존 로직 추가
- `card_role`과 `image_hint`를 보존하는 것과 동일한 방식으로 처리
- 수정 위치: `3_Code/src/01_generate_json.py` 라인 375-441

**결과:**
- ✅ 문제 해결 완료 (테스트 Run Tag: `TEST_OPTIONS_FIX_20251220_172357`)
- ⚠️ 기존 run tag는 재실행 필요 (이미 저장된 파일은 수정 불가)

---

## 하위 호환성

### 기존 실행 결과와의 호환성

- ✅ 기존 S1/S2 출력 스키마 변경 없음 (frozen)
- ⚠️ Q2에 `image_hint`가 없는 경우 실패 (기존에는 경고만)
- ✅ 기존 이미지 스펙도 정상 처리 (`spec_kind` 기본값 사용)
- ⚠️ **S2 options 필드 누락 문제**: 기존 run tag는 재실행 필요

### 마이그레이션 필요 사항

기존 실행 결과를 재사용하려면:
1. S2 출력에 Q2의 `image_hint`가 있는지 확인
2. S2 출력에 MCQ 카드의 `options`와 `correct_index` 필드가 있는지 확인
3. 없으면 S2를 재실행하여 필드 생성 필요

---

## 관련 문서

### 구현 로그
- `0_Protocol/04_Step_Contracts/Step01_S1/S1_Implementation_Update_Log_2025-12-20.md`
- `0_Protocol/04_Step_Contracts/Step02_S2/S2_Implementation_Update_Log_2025-12-20.md`
- `0_Protocol/04_Step_Contracts/Step03_S3/S3_Implementation_Update_Log_2025-12-20.md`
- `0_Protocol/04_Step_Contracts/Step04_S4/S4_Implementation_Update_Log_2025-12-20.md`
- `0_Protocol/05_Pipeline_and_Execution/Implementation_Update_Log_2025-12-20.md`

### 코드 문서
- `S3_S4_Code_Documentation.md` (프로젝트 루트)

### 추적성 문서
- `0_Protocol/05_Pipeline_and_Execution/Code_to_Protocol_Traceability.md`

### 엔티티 정의
- `0_Protocol/04_Step_Contracts/Step03_S3/Entity_Definition_S3_Canonical.md`
- `0_Protocol/04_Step_Contracts/Step04_S4/Entity_Definition_S4_Canonical.md`

---

## 변경 이력

- **2025-12-20 (오전)**: S3/S4 구현 업데이트 및 문서화
  - S3/S4 코드 업데이트
  - 파이프라인 도구 개선 (6-arm 스크립트, 모델 확인 도구)
  - 구현 업데이트 로그 작성

- **2025-12-20 (오후)**: S1/S2 프롬프트 및 코드 개선, 버그 수정
  - S1 프롬프트 v8 업데이트
  - S2 프롬프트 v7 개선
  - S2 options 필드 저장 문제 해결 (중요한 버그 수정)
  - PDF/Anki 출력 개선
  - 파이프라인 실행 스크립트 개선
  - 통합 변경 로그 업데이트

- **2025-12-20 (저녁)**: 문서 정리 및 구조화
  - `GEMINI_3_CODE_REVIEW.md` 이동: `3_Code/src/` → `0_Protocol/02_Arms_and_Models/`
  - `S4_Prompt_Template_Smoke_Test_Plan.md` 이동: `3_Code/src/` → `0_Protocol/04_Step_Contracts/Step04_S4/`
  - 문서 구조 점검 및 정리


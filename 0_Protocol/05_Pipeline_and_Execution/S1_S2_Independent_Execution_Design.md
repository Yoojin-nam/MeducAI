# S1/S2 독립 실행 시스템 설계 (Canonical)

**Status:** Canonical (Implemented)  
**Version:** 1.1  
**Date:** 2025-12-19  
**Last Updated:** 2025-12-19  
**Purpose:** S1과 S2를 독립적으로 실행 가능한 시스템 구축 가이드

---

## 0. Executive Summary

S1 (Group-level structuring)과 S2 (Entity-level card generation)는 **명확히 분리된 책임**을 가지며, **독립적으로 실행 가능**해야 합니다.

**구현 상태 (2025-12-19):** ✅ **구현 완료**

현재 `01_generate_json.py`에 `--stage` 옵션이 추가되어 S1과 S2를 독립적으로 실행할 수 있습니다:
- `--stage 1`: S1만 실행
- `--stage 2`: S2만 실행 (기존 S1 출력 필요)
- `--stage both`: S1+S2 실행 (기본값)

**향후 계획:** 별도 스크립트(`01_generate_s1.py`, `02_execute_s2.py`) 분리는 선택사항

---

## 1. 설계 원칙

### 1.1 Separation of Concerns

- **S1**: Group → Master Table + Entity List 생성
- **S2**: Entity → Anki Cards 생성 (S1 출력 소비)
- **공통 코드**: LLM 호출, 설정 로드, 유틸리티 (모듈로 분리)

### 1.2 독립 실행 가능성

- S1은 S2 없이 실행 가능
- S2는 S1 출력을 소비하여 실행
- S1 Gate 통과 후에만 S2 실행 (fail-fast)

### 1.3 프로토콜 준수

- `Code_to_Protocol_Traceability.md` (v1.2)에 정의된 구조 준수
- `02_execute_entities.py`는 "implement-ready" 상태로 정의됨

---

## 2. 권장 구조 (모듈화 + CLI 분리)

### 2.1 디렉토리 구조

```
3_Code/src/
├── core/                          # 공통 모듈 (NEW)
│   ├── __init__.py
│   ├── llm_client.py              # LLM 호출 로직
│   ├── config_loader.py            # ARM_CONFIGS, 환경변수 로드
│   ├── prompt_bundle.py            # 프롬프트 번들 로드
│   ├── path_utils.py               # 경로 유틸리티
│   └── validation.py               # 공통 검증 로직
│
├── 01_generate_s1.py              # S1 전용 실행 스크립트 (NEW)
├── 02_execute_s2.py                # S2 전용 실행 스크립트 (NEW)
│
├── 01_generate_json.py            # 기존 통합 스크립트 (DEPRECATED)
│                                   # --stage 옵션으로 호환성 유지 또는 제거
│
├── tools/                          # 기존 유틸리티
│   ├── allocation/
│   └── ...
│
└── validate_stage1_struct.py      # S1 Gate 검증 (기존 유지)
```

### 2.2 실행 스크립트 명세

#### 2.2.1 `01_generate_s1.py` (S1 전용)

**입력:**
- `--base_dir`: 프로젝트 루트
- `--run_tag`: 실행 태그
- `--arm`: Arm 식별자 (A-F)
- `--mode`: S0/FINAL
- `--sample`, `--row_index`, `--only_group_id`: 그룹 필터링 옵션

**출력:**
- `{RUN_TAG}/stage1_struct__arm{ARM}.jsonl`
- `{RUN_TAG}/stage1_raw__arm{ARM}.jsonl`

**책임:**
- Group-level 구조 생성만 담당
- S2 실행은 하지 않음

**예시:**
```bash
python3 3_Code/src/01_generate_s1.py \
  --base_dir . \
  --run_tag S1_TEST_20251219 \
  --arm A \
  --mode S0 \
  --sample 1
```

#### 2.2.2 `02_execute_s2.py` (S2 전용)

**입력:**
- `--base_dir`: 프로젝트 루트
- `--run_tag`: 실행 태그 (S1과 동일)
- `--arm`: Arm 식별자 (S1과 동일)
- `--mode`: S0/FINAL
- `--group_id`: 특정 그룹만 실행 (선택적)

**입력 파일 (소비):**
- `{RUN_TAG}/stage1_struct__arm{S1_ARM}.jsonl` (S1 출력, `--s1_arm`으로 지정)
- `{RUN_TAG}/allocation/allocation_s0__group_{G}__arm_{A}.json` (Allocation)

**출력:**
- `{RUN_TAG}/s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl` (new format, 2025-12-23)
- `{RUN_TAG}/s2_results__arm{ARM}.jsonl` (legacy format, backward compatible)

**책임:**
- S1 출력을 읽어서 Entity-level 카드 생성
- Allocation artifact를 읽어서 정확한 카드 수 집행

**예시:**
```bash
python3 3_Code/src/02_execute_s2.py \
  --base_dir . \
  --run_tag S1_TEST_20251219 \
  --arm A \
  --mode S0
```

### 2.3 공통 모듈 (`core/`)

#### 2.3.1 `core/llm_client.py`

**책임:**
- LLM API 호출 로직
- Retry/backoff 처리
- Provider별 클라이언트 관리
- `call_llm()` 함수 (S1, S2 공통 사용)

#### 2.3.2 `core/config_loader.py`

**책임:**
- `ARM_CONFIGS` 로드
- 환경변수 로드
- Provider/Model 해석
- Temperature, timeout 등 설정 로드

#### 2.3.3 `core/prompt_bundle.py`

**책임:**
- 프롬프트 번들 로드
- 프롬프트 해시 계산
- MI-CLEAR-LLM 준수

#### 2.3.4 `core/path_utils.py`

**책임:**
- RUN_TAG 기반 경로 생성
- Artifact 경로 해석
- `generated_paths.py`와 통합

---

## 3. 실행 워크플로우 (✅ 구현 완료)

### 3.1 S1만 실행 (6 arm 순차 실행)

```bash
# Stage 1: 모든 arm 실행
for arm in A B C D E F; do
  python3 3_Code/src/01_generate_json.py \
    --base_dir . \
    --run_tag TEST_20251219 \
    --arm $arm \
    --mode S0 \
    --stage 1 \
    --sample 1
done

# S1 Gate 검증
python3 3_Code/src/validate_stage1_struct.py \
  --base_dir . \
  --run_tag TEST_20251219

# Allocation 생성 (S0 모드, 각 arm별)
for arm in A B C D E F; do
  python3 3_Code/src/tools/allocation/s0_allocation.py \
    --base_dir . \
    --run_tag TEST_20251219 \
    --arm $arm
done
```

### 3.2 S2만 실행 (S1 출력 소비, 6 arm 순차 실행)

```bash
# S1 출력이 이미 존재하는 경우
for arm in A B C D E F; do
  python3 3_Code/src/01_generate_json.py \
    --base_dir . \
    --run_tag TEST_20251219 \
    --arm $arm \
    --mode S0 \
    --stage 2 \
    --sample 1
done
```

### 3.3 S1 → S2 순차 실행 (권장 워크플로우)

```bash
# 1. Stage 1: 모든 arm 실행
for arm in A B C D E F; do
  python3 3_Code/src/01_generate_json.py \
    --base_dir . \
    --run_tag TEST_20251219 \
    --arm $arm \
    --mode S0 \
    --stage 1 \
    --sample 1
done

# 2. S1 Gate 검증
python3 3_Code/src/validate_stage1_struct.py \
  --base_dir . \
  --run_tag TEST_20251219

# 3. Allocation 생성 (S0 모드)
for arm in A B C D E F; do
  python3 3_Code/src/tools/allocation/s0_allocation.py \
    --base_dir . \
    --run_tag TEST_20251219 \
    --arm $arm
done

# 4. Stage 2: 모든 arm 실행
for arm in A B C D E F; do
  python3 3_Code/src/01_generate_json.py \
    --base_dir . \
    --run_tag TEST_20251219 \
    --arm $arm \
    --mode S0 \
    --stage 2 \
    --sample 1
done
```

### 3.4 통합 실행 (기본값, 호환성 유지)

```bash
# S1 + S2 통합 실행 (기본값)
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag TEST_20251219 \
  --arm A \
  --mode S0 \
  --stage both \
  --sample 1
```

---

## 4. 기존 코드 마이그레이션 전략

### 4.1 단계별 접근

**Phase 1: 공통 모듈 추출**
- `01_generate_json.py`에서 공통 코드를 `core/` 모듈로 추출
- LLM 호출, 설정 로드, 경로 유틸리티 등

**Phase 2: S1 스크립트 분리**
- `01_generate_s1.py` 생성
- `process_single_group()`의 S1 부분만 실행
- S2 호출 제거

**Phase 3: S2 스크립트 생성**
- `02_execute_s2.py` 생성
- S1 출력 파일 읽기
- Allocation artifact 읽기
- Entity별 카드 생성

**Phase 4: 기존 스크립트 처리**
- `01_generate_json.py`는 `--stage` 옵션으로 호환성 유지하거나
- Deprecated로 표시하고 제거

---

## 5. 구현된 방식: 단일 스크립트 + --stage 옵션 (✅ 구현 완료)

### 5.1 구현 상태

**현재 구현 (2025-12-19):** `01_generate_json.py`에 `--stage` 옵션 추가 완료

```bash
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag TEST_20251219 \
  --arm A \
  --mode S0 \
  --stage 1        # S1만 실행
  # --stage 2      # S2만 실행 (S1 출력 필요)
  # --stage both   # S1 + S2 실행 (기본값)
```

### 5.2 동작 방식

**Stage 1 (S1) 실행:**
- Group-level 구조 생성
- `stage1_struct__arm{X}.jsonl` 파일 생성
- `stage1_raw__arm{X}.jsonl` 파일 생성 (선택적)

**Stage 2 (S2) 실행:**
- 기존 `stage1_struct__arm{S1_ARM}.jsonl` 파일을 읽어서 S1 출력 로드 (`--s1_arm`으로 지정)
- Allocation artifact 읽기 (S0 모드)
- Entity-level 카드 생성
- `s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl` 파일 생성 (new format, 2025-12-23)
- Legacy 형식 (`s2_results__arm{X}.jsonl`)은 하위 호환성을 위해 계속 지원

**S2-only 모드 전제조건:**
- S1 출력 파일(`stage1_struct__arm{X}.jsonl`)이 존재해야 함
- 파일이 없으면 에러 발생 (fail-fast)

### 5.3 테스트 결과

**테스트 완료 (2025-12-19):**
- ✅ Stage 1로 6개 arm (A-F) 모두 성공
- ✅ Stage 2로 6개 arm (A-F) 모두 성공
- ✅ 모든 출력 파일 정상 생성 확인

---

## 6. 구현 상태 및 향후 계획

### 6.1 현재 구현 (✅ 완료)

**구현 방식:** 단일 스크립트 + `--stage` 옵션

**완료된 기능:**
- ✅ `--stage 1`: S1만 실행
- ✅ `--stage 2`: S2만 실행 (기존 S1 출력 읽기)
- ✅ `--stage both`: S1+S2 통합 실행 (기본값)
- ✅ S2-only 모드에서 기존 S1 출력 파일 읽기
- ✅ 6 arm 테스트 완료 및 검증

**장점:**
- 기존 코드 변경 최소화
- 빠른 구현 및 검증 완료
- 호환성 유지 (기본값은 `both`)
- 실제 운영에서 사용 가능

### 6.2 향후 개선 계획 (선택사항)

**P1 (선택):** 별도 스크립트 분리
- `01_generate_s1.py`: S1 전용
- `02_execute_s2.py`: S2 전용
- 더 명확한 책임 분리

**P2 (선택):** 공통 모듈 추출
- `core/` 디렉토리 구조
- 코드 재사용성 향상

**현재 상태:** ✅ **운영 가능** - 별도 스크립트 분리는 선택사항

---

## 7. 프로토콜 준수 체크리스트

- [x] ✅ S1 출력 경로: `{RUN_TAG}/stage1_struct__arm{ARM}.jsonl`
- [x] ✅ S2 출력 경로: `{RUN_TAG}/s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl` (new, 2025-12-23)
- [x] ✅ S2 출력 경로 (legacy): `{RUN_TAG}/s2_results__arm{ARM}.jsonl` (backward compatible)
- [x] ✅ Allocation artifact 경로 준수
- [x] ✅ S1 Gate 통과 후에만 S2 실행 (S2-only 모드에서 파일 존재 확인)
- [x] ✅ MI-CLEAR-LLM 메타데이터 기록
- [x] ✅ S1/S2 독립 실행 가능 (테스트 완료)
- [ ] `02_execute_entities.py` 별도 스크립트 분리 (선택사항, 현재는 `--stage` 옵션 사용)

---

## 8. 참고 문서

- `04_Step_Contracts/Step01_S1/S1_Stage1_Struct_JSON_Schema_Canonical.md`
- `04_Step_Contracts/Step02_S2/S2_Contract_and_Schema_Canonical.md`
- `05_Pipeline_and_Execution/Code_to_Protocol_Traceability.md`
- `05_Pipeline_and_Execution/Pipeline_Canonical_Specification.md`


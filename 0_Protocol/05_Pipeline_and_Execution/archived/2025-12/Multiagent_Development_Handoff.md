# 멀티에이전트 시스템 개발 인계 문서

**작성 일자**: 2025-12-29  
**인계 대상**: 멀티에이전트 시스템 개발 담당 Agent  
**목적**: S5R/S1R/S2R 멀티에이전트 수정 시스템 구현을 위한 종합 가이드  
**상태**: 개발 전 단계 (프로토콜 정의 완료, 구현 시작 준비)

---

## 1. Executive Summary

### 1.1 개발 목표

멀티에이전트 시스템은 **S5 validation 결과를 기반으로 한 one-shot 자동 수정 루프**를 구현합니다:

1. **S5 (Critic/Verifier)**: 이미 구현 완료 ✅ - validation만 수행, 수정 안 함
2. **S5R (Repair Planner)**: 새로 구현 필요 - S5 결과를 repair instructions로 변환
3. **S1R/S2R (Generator)**: 새로 구현 필요 - S5R instructions를 사용하여 재생성
4. **S5' (Post-Repair Validator)**: S5 재사용 - 수정본 검증

### 1.2 핵심 제약사항 (Non-Negotiable)

- ✅ **원본 아티팩트는 절대 수정 불가**: 모든 수정본은 별도 파일로 저장 (`*__repaired.jsonl`)
- ✅ **One-shot only**: 정확히 1회의 수정 iteration만 허용 (루프 없음)
- ✅ **Fail-fast 없음**: 수정 실패해도 pipeline 중단 안 함
- ✅ **Primary endpoint 보호**: Human rating의 Pre-Multiagent 평가는 primary endpoint (immutable)
- ✅ **MI-CLEAR-LLM 준수**: 모든 LLM 호출에 대해 완전한 로깅 필수

---

## 2. 현재 시스템 상태

### 2.1 이미 구현된 컴포넌트

#### S5 Validator (Critic/Verifier)
- **파일**: `3_Code/src/05_s5_validator.py`
- **상태**: ✅ 구현 완료
- **역할**: S1 테이블과 S2 카드 검증
- **출력**: `s5_validation__arm{arm}.jsonl`
- **스키마**: `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Schema_Canonical.md`
- **중요**: S5는 **validation만 수행**, generation/modification 절대 안 함
- **평가 구조** (S1 기준):
  - **Step 1: 테이블 평가** (항상 수행)
    - 입력: `master_table_markdown_kr`, `objective_bullets`
    - 출력: `blocking_error`, `technical_accuracy`, `educational_quality`, `issues`, `rag_evidence`
    - 프롬프트: `S5_USER_TABLE__v2.md`
  - **Step 2: 인포그래픽 평가** (선택적)
    - 클러스터 없음: 단일 인포그래픽 평가 → `table_visual_validation` (단일 dict)
    - 클러스터 있음: 최대 4개 인포그래픽 평가 (각 클러스터별 독립 LLM 호출) → `table_visual_validations` (리스트)
    - 출력: `information_clarity`, `anatomical_accuracy`, `prompt_compliance`, `table_visual_consistency`, `issues`
    - 프롬프트: `S5_USER_TABLE_VISUAL__v1.md`
- **참고 문서**: `0_Protocol/04_Step_Contracts/Step05_S5/S5_S1_Validation_Specification.md`

#### S1/S2 Generator (재사용 가능)
- **파일**: `3_Code/src/01_generate_json.py`
- **상태**: ✅ 구현 완료 (S1R/S2R에서 재사용 가능)
- **함수**: `call_llm()`, `extract_json_object()` 등
- **LLM 호출 인프라**: ProviderClients, QuotaLimiter, ApiKeyRotator 등

### 2.2 새로 구현해야 할 컴포넌트

#### S5R Repair Planner
- **입력**: 
  - `s5_validation__arm{arm}.jsonl` (S5 validation 결과)
    - 테이블 평가 결과: `blocking_error`, `technical_accuracy`, `educational_quality`, `issues[]`, `rag_evidence[]`
    - 인포그래픽 평가 결과: `table_visual_validation` (단일) 또는 `table_visual_validations[]` (클러스터별, 최대 4개)
  - 원본 S1/S2 아티팩트 (read-only 참조)
- **출력**: `s5_repair_plan__arm{arm}.jsonl`
- **역할**: S5의 issues를 executable repair instructions로 변환
- **특징**:
  - 테이블 평가 이슈 → S1 repair instructions
  - 인포그래픽 평가 이슈 → S3/S4 repair instructions (향후 확장 가능)
  - 클러스터별 인포그래픽 이슈는 각 클러스터별로 처리

#### S1R Regenerator
- **입력**: 
  - 원본 S1 inputs (group_path, objectives 등)
  - `s5_repair_plan__arm{arm}.jsonl` (S1 repair instructions)
- **출력**: `stage1_struct__arm{arm}__repaired.jsonl`
- **역할**: S1 테이블 재생성 (S1 prompt + S5R instructions)

#### S2R Regenerator
- **입력**: 
  - 원본 S2 inputs
  - `s5_repair_plan__arm{arm}.jsonl` (S2 repair instructions)
  - 수정된 S1 아티팩트 (S1R 출력)
- **출력**: `s2_results__s1arm{S1arm}__s2arm{arm}__repaired.jsonl`
- **역할**: S2 카드 재생성 (S2 prompt + S5R instructions)

#### S5' Post-Repair Validator
- **입력**: S1R/S2R 출력 (수정본)
- **출력**: `s5_validation__arm{arm}__postrepair.jsonl`
- **역할**: 수정본 검증 (S5와 동일한 로직, 다른 파일에 출력)
- **구현**: S5 validator 재사용 가능 (입력/출력 파일만 변경)

---

## 3. 시스템 아키텍처

### 3.1 워크플로우 다이어그램

```
Baseline Pipeline (기존):
S1 → S2 → S3 → S4 → S5 → S6

멀티에이전트 루프 (신규):
S5 (validation)
  ↓
S5R (repair plan generation)
  ↓
S1R (S1 table regeneration) ─┐
  ↓                            │
S2R (S2 cards regeneration)    │ (one-shot)
  ↓                            │
S5' (post-repair validation) ──┘
  ↓
S6 (export - baseline 또는 repaired 선택)
```

### 3.2 에이전트 역할 분리

| 에이전트 | 역할 | 입력 | 출력 | 구현 상태 |
|---------|------|------|------|----------|
| **S5** | Critic/Verifier | S1 table, S2 cards | Validation results + issues | ✅ 완료 |
| **S5R** | Repair Planner | S5 results + original artifacts | Repair plan (instructions) | ❌ 미구현 |
| **S1R** | S1 Regenerator | Original S1 inputs + S5R plan | Repaired S1 table | ❌ 미구현 |
| **S2R** | S2 Regenerator | Original S2 inputs + S5R plan + repaired S1 | Repaired S2 cards | ❌ 미구현 |
| **S5'** | Post-Repair Validator | Repaired S1/S2 | Post-repair validation | ⚠️ S5 재사용 |

**참고**: S5는 내부적으로 2단계 평가를 수행:
- **Table Validator** (Step 1): 테이블 평가 (항상 수행)
- **Infographic Validator** (Step 2): 인포그래픽 평가 (선택적, 클러스터별 최대 4개 독립 LLM 호출)
- 상세 내용: `0_Protocol/04_Step_Contracts/Step05_S5/S5_S1_Validation_Specification.md` 참조

---

## 4. 아티팩트 구조 및 스키마

### 4.1 파일 구조

모든 아티팩트는 `2_Data/metadata/generated/{RUN_TAG}/` 하위에 저장됩니다.

#### Baseline Artifacts (기존, 수정 불가)
```
stage1_struct__arm{arm}.jsonl                    # 원본 S1 테이블
s2_results__s1arm{S1arm}__s2arm{arm}.jsonl      # 원본 S2 카드
s5_validation__arm{arm}.jsonl                    # S5 validation 결과
```

#### Multiagent Artifacts (신규)
```
s5_repair_plan__arm{arm}.jsonl                   # S5R 출력: 수정 계획
stage1_struct__arm{arm}__repaired.jsonl          # S1R 출력: 수정된 S1
s2_results__s1arm{S1arm}__s2arm{arm}__repaired.jsonl  # S2R 출력: 수정된 S2
s5_validation__arm{arm}__postrepair.jsonl        # S5' 출력: 수정본 검증 결과
```

### 4.2 S5R Repair Plan Schema

**파일**: `s5_repair_plan__arm{arm}.jsonl` (one record per `group_id`)

```json
{
  "schema_version": "S5_REPAIR_PLAN_v1.0",
  "run_tag": "RUN_TAG_XXX",
  "arm": "A",
  "group_id": "G0123",
  "created_at": "2025-12-29T10:00:00Z",
  
  "inputs": {
    "s5_snapshot_id": "s5_RUN_TAG_G0123_A_gemini-2.0-pro-exp_v1_abc123",
    "baseline_s1_hash": "sha256_hash_of_original_s1",
    "baseline_s2_hash": "sha256_hash_of_original_s2"
  },
  
  "s1_repair_instructions": [
    {
      "action_type": "fix_row",
      "target": {
        "row_index": 3,
        "entity_name": "Entity Name",
        "column_name": "description"  // optional
      },
      "instruction": "Fix factual error: DWI high signal indicates acute infarction, not T2 shine-through",
      "evidence": [
        {
          "source_id": "rag_doc_001",
          "source_excerpt": "DWI high signal indicates acute infarction...",
          "relevance": "high"
        }
      ]
    }
  ],
  
  "s2_repair_instructions": [
    {
      "target_card_id": "G0123__E01__C02",
      "card_role": "Q1",
      "entity_id": "E01",
      "entity_name": "Entity Name",
      "action_type": "fix_factual",
      "instruction": "Correct the explanation: DWI high signal indicates acute infarction, not T2 shine-through",
      "evidence": [
        {
          "source_id": "rag_doc_001",
          "source_excerpt": "DWI high signal indicates acute infarction...",
          "relevance": "high"
        }
      ]
    },
    {
      "target_card_id": "G0123__E01__C03",
      "card_role": "Q2",
      "entity_id": "E01",
      "entity_name": "Entity Name",
      "action_type": "add_missing_options",
      "instruction": "Add missing MCQ options. Current options count: 3, required: 5",
      "evidence": []
    }
  ],
  
  "guardrails": {
    "no_new_content_scope": true,
    "max_iteration": 1,
    "repair_iteration": 1
  },
  
  "metadata": {
    "s5r_model": "models/gemini-2.0-pro-exp",
    "s5r_thinking_enabled": true,
    "s5r_rag_enabled": true,
    "s5r_prompt_hash": "sha256_hash_of_s5r_prompt"
  }
}
```

### 4.3 Lineage 필수 필드

모든 repair-related 아티팩트에 다음 필드를 포함해야 합니다:

- `run_tag`: 원본 RUN_TAG
- `arm`: 원본 arm
- `group_id`: 원본 group_id
- `baseline_snapshot_id` 또는 `baseline_*_hash`: 원본 아티팩트 추적
- `s5_snapshot_id`: 수정 계획에 사용된 S5 결과
- `repair_iteration`: 항상 `1` (one-shot 제약)
- `repaired_snapshot_id`: 수정본의 고유 식별자

---

## 5. 구현 단계별 가이드

### 5.1 Phase 1: S5R Repair Planner 구현 (우선순위: 최우선)

#### 5.1.1 입력 데이터 로딩
```python
# S5 validation 결과 로딩
s5_validation_path = f"2_Data/metadata/generated/{run_tag}/s5_validation__arm{arm}.jsonl"
s5_results = load_s5_validation(s5_validation_path, group_id)

# 원본 S1/S2 아티팩트 로딩 (read-only)
s1_original = load_s1_artifact(run_tag, arm, group_id)
s2_original = load_s2_artifact(run_tag, arm, group_id)
```

#### 5.1.2 Repair Instruction 생성
- S5의 `issues[]` 배열을 분석
  - **테이블 평가 이슈**: `issues[]` (테이블 레벨)
  - **인포그래픽 평가 이슈**: `table_visual_validation.issues[]` (단일) 또는 `table_visual_validations[].issues[]` (클러스터별)
- 각 issue를 executable instruction으로 변환
- `action_type` 결정:
  - S1: `fix_row`, `rename_entity`, `clarify_term`, `remove_ambiguous_claim`
  - S2: `fix_factual`, `add_missing_options`, `fix_correct_index`, `improve_clarity`
  - S3/S4: (향후 확장 가능) 인포그래픽 관련 repair instructions
- RAG evidence를 instruction에 포함 (blocking error인 경우 필수)
- **클러스터 처리**: 클러스터별 인포그래픽 이슈는 각 클러스터 ID와 함께 instruction에 포함

#### 5.1.3 출력 스키마 준수
- `s5_repair_plan__arm{arm}.jsonl` 생성
- 모든 필수 lineage 필드 포함
- Guardrails 명시 (`max_iteration=1`, `no_new_content_scope=true`)

#### 5.1.4 MI-CLEAR-LLM 로깅
- S5R LLM 호출 정보 로깅:
  - Model identification (provider, model name/version)
  - Prompt disclosure (prompt IDs + hashes)
  - Parameters (temperature, max_output_tokens, thinking/RAG flags)
  - Timing (start/end timestamps, latency)
  - Token usage (input/output tokens)
  - RAG logging (query count, sources count, evidence excerpts)

### 5.2 Phase 2: S1R Regenerator 구현

#### 5.2.1 입력 준비
```python
# 원본 S1 inputs 로딩
original_s1_inputs = load_original_s1_inputs(run_tag, group_id)

# S5R repair plan 로딩
repair_plan = load_s5r_repair_plan(run_tag, arm, group_id)
s1_instructions = repair_plan["s1_repair_instructions"]
```

#### 5.2.2 Prompt 구성
- 원본 S1 prompt 재사용 (`3_Code/prompt/` 디렉토리)
- S5R instructions를 system prompt 또는 user prompt에 추가
- 명확한 지시: "Apply the following repair instructions to the original generation task..."

#### 5.2.3 재생성 실행
- 기존 `01_generate_json.py`의 `call_llm()` 함수 재사용
- 원본 S1과 동일한 model/configuration 사용 (arm consistency 유지)
- 출력: `stage1_struct__arm{arm}__repaired.jsonl`

#### 5.2.4 아티팩트 검증
- Schema validation (S1 schema 준수 확인)
- Lineage 필드 포함 확인
- 원본과의 차이점 로깅 (audit trail)

### 5.3 Phase 3: S2R Regenerator 구현

#### 5.3.1 입력 준비
```python
# 원본 S2 inputs 로딩
original_s2_inputs = load_original_s2_inputs(run_tag, arm, group_id)

# 수정된 S1 아티팩트 로딩 (S1R 출력)
repaired_s1 = load_repaired_s1(run_tag, arm, group_id)

# S5R repair plan 로딩
repair_plan = load_s5r_repair_plan(run_tag, arm, group_id)
s2_instructions = repair_plan["s2_repair_instructions"]
```

#### 5.3.2 Prompt 구성
- 원본 S2 prompt 재사용
- 수정된 S1 아티팩트를 context로 제공
- S5R instructions를 prompt에 통합

#### 5.3.3 재생성 실행
- Entity 단위로 처리 (병렬화 가능)
- 각 card에 대한 repair instruction 적용
- 출력: `s2_results__s1arm{S1arm}__s2arm{arm}__repaired.jsonl`

### 5.4 Phase 4: S5' Post-Repair Validator 구현

#### 5.4.1 S5 Validator 재사용
- 기존 `05_s5_validator.py`의 로직 재사용
- 입력만 수정본으로 변경:
  ```python
  repaired_s1 = load_repaired_s1(run_tag, arm, group_id)
  repaired_s2 = load_repaired_s2(run_tag, arm, group_id)
  ```
- 출력 파일명만 변경: `s5_validation__arm{arm}__postrepair.jsonl`
- **평가 구조 동일**: 
  - Step 1: 테이블 평가 (수정된 S1 테이블)
  - Step 2: 인포그래픽 평가 (수정된 S3/S4 인포그래픽, 클러스터별 처리 동일)
  - 클러스터가 있는 경우 동일하게 최대 4개 인포그래픽 평가 수행

#### 5.4.2 Lineage 연결
- Post-repair validation 결과에 다음 정보 포함:
  - `baseline_s5_snapshot_id`: 원본 S5 validation 결과
  - `repair_plan_snapshot_id`: 사용된 S5R repair plan
  - `repaired_s1_hash`: 수정된 S1 아티팩트 해시
  - `repaired_s2_hash`: 수정된 S2 아티팩트 해시

---

## 6. 필수 가드레일 및 제약사항

### 6.1 원본 아티팩트 불변성 (Critical)

```python
# ❌ 절대 하지 말 것
# modify_in_place(original_artifact)

# ✅ 올바른 방법
repaired_artifact = generate_repaired_version(original_artifact, instructions)
save_to_separate_file(repaired_artifact, f"{original_filename}__repaired.jsonl")
```

### 6.2 One-Shot 제약

```python
# ✅ 올바른 구현
repair_iteration = 1  # 고정값
max_iteration = 1     # 고정값

# ❌ 루프 구현 금지
# while should_continue_repairing():
#     repair_iteration += 1
#     ...  # 절대 안 됨!
```

### 6.3 Fail-Fast 금지

```python
# ✅ 올바른 에러 처리
try:
    repaired = generate_repaired(content, instructions)
except Exception as e:
    log_error(f"Repair failed for {group_id}: {e}")
    # Pipeline 계속 진행 (수정 실패해도 baseline 사용)
    continue_to_s6_with_baseline()
```

### 6.4 MI-CLEAR-LLM 로깅 필수

모든 LLM 호출에 대해 다음 정보를 로깅해야 합니다:

```python
runtime_log = {
    "model_provider": "google",
    "model_name": "models/gemini-2.0-pro-exp",
    "model_version": "v1",
    "temperature": 0.2,
    "max_output_tokens": 8192,
    "thinking_enabled": True,
    "rag_enabled": True,
    "rag_queries_count": 3,
    "rag_sources_count": 5,
    "prompt_id": "s5r_repair_planner_v1",
    "prompt_hash": "sha256_hash_of_prompt",
    "start_timestamp_ms": 1703587200000,
    "end_timestamp_ms": 1703587250000,
    "latency_sec": 5.0,
    "input_tokens": 1500,
    "output_tokens": 800,
    "retry_count": 0,
    "errors": []
}
```

---

## 7. Human Rating Workflow 통합

### 7.1 3-Pass Evaluation Workflow

멀티에이전트 수정 결과를 평가하기 위한 3-pass workflow가 정의되어 있습니다:

- **Pass 1: Pre-Multiagent Evaluation** (Primary Endpoint)
  - 원본 콘텐츠만 평가 (멀티에이전트 수정 결과 숨김)
  - Blocking Error, Technical Accuracy, Overall Quality 평가
  - 평가 제출 후 immutable

- **Pass 2: Multiagent Results Reveal**
  - 멀티에이전트 수정 결과 공개
  - 원본 vs 수정본 비교 표시
  - S5 평가 결과 표시

- **Pass 3: Post-Multiagent Evaluation** (Secondary Endpoint)
  - 수정본 평가
  - S5 평가 동의/비동의 평가
  - 수정본 수용 여부 평가

**상세 설계**: `0_Protocol/05_Pipeline_and_Execution/Multiagent_Evaluation_Workflow_Design.md`

### 7.2 데이터 스키마

Human rating 스키마는 별도로 정의됩니다:
- 파일: `human_rating_with_multiagent__arm{arm}.jsonl`
- 스키마 버전: `HUMAN_RATING_MULTIAGENT_v1.0`
- **참고**: 이는 평가 시스템의 스키마이지, 멀티에이전트 시스템 자체의 스키마는 아닙니다.

---

## 8. 테스트 및 검증 전략

### 8.1 단위 테스트

각 컴포넌트별로 단위 테스트 작성:

```python
def test_s5r_repair_planner():
    """S5R가 S5 results를 올바른 repair instructions로 변환하는지 테스트"""
    s5_result = load_test_s5_result()
    repair_plan = s5r_generate_repair_plan(s5_result)
    
    assert repair_plan["schema_version"] == "S5_REPAIR_PLAN_v1.0"
    assert repair_plan["guardrails"]["max_iteration"] == 1
    assert len(repair_plan["s1_repair_instructions"]) > 0 or len(repair_plan["s2_repair_instructions"]) > 0

def test_s1r_regeneration():
    """S1R이 repair instructions를 올바르게 적용하는지 테스트"""
    original_s1 = load_test_s1()
    repair_plan = load_test_repair_plan()
    repaired_s1 = s1r_regenerate(original_s1, repair_plan)
    
    assert repaired_s1["schema_version"] == original_s1["schema_version"]  # Schema 호환
    assert "baseline_s1_hash" in repaired_s1["metadata"]
    assert repaired_s1["metadata"]["repair_iteration"] == 1
```

### 8.2 통합 테스트

전체 루프 테스트:

```python
def test_multiagent_loop():
    """멀티에이전트 루프가 end-to-end로 동작하는지 테스트"""
    # 1. S5 validation (이미 구현)
    s5_result = run_s5_validation(run_tag, arm, group_id)
    
    # 2. S5R repair plan
    repair_plan = run_s5r_repair_planner(s5_result)
    
    # 3. S1R regeneration
    repaired_s1 = run_s1r_regenerator(repair_plan)
    
    # 4. S2R regeneration
    repaired_s2 = run_s2r_regenerator(repair_plan, repaired_s1)
    
    # 5. S5' post-repair validation
    post_repair_validation = run_s5_post_repair_validator(repaired_s1, repaired_s2)
    
    # 검증
    assert post_repair_validation["schema_version"] == "S5_VALIDATION_v1.0"
    assert post_repair_validation["metadata"]["baseline_s5_snapshot_id"] == s5_result["s5_snapshot_id"]
```

### 8.3 아티팩트 무결성 검증

```python
def verify_artifact_integrity():
    """원본 아티팩트가 수정되지 않았는지 확인"""
    original_s1_hash = calculate_hash(load_original_s1())
    current_s1_hash = calculate_hash(load_s1_artifact())
    
    assert original_s1_hash == current_s1_hash, "Original artifact was modified!"
```

---

## 9. 구현 체크리스트

### 9.1 S5R Repair Planner
- [ ] S5 validation 결과 로딩 함수
- [ ] 원본 S1/S2 아티팩트 로딩 함수 (read-only)
- [ ] Issue to instruction 변환 로직
- [ ] Repair plan 스키마 생성
- [ ] Lineage 필드 생성 (baseline hashes, s5_snapshot_id)
- [ ] MI-CLEAR-LLM 로깅
- [ ] 단위 테스트
- [ ] Schema validation

### 9.2 S1R Regenerator
- [ ] 원본 S1 inputs 로딩
- [ ] S5R repair plan 로딩
- [ ] Prompt 구성 (original + instructions)
- [ ] LLM 호출 (기존 인프라 재사용)
- [ ] Repaired S1 아티팩트 저장
- [ ] Lineage 필드 포함
- [ ] Schema validation
- [ ] 단위 테스트

### 9.3 S2R Regenerator
- [ ] 원본 S2 inputs 로딩
- [ ] Repaired S1 아티팩트 로딩
- [ ] S5R repair plan 로딩
- [ ] Prompt 구성
- [ ] Entity 단위 처리 (병렬화 고려)
- [ ] Repaired S2 아티팩트 저장
- [ ] Lineage 필드 포함
- [ ] Schema validation
- [ ] 단위 테스트

### 9.4 S5' Post-Repair Validator
- [ ] S5 validator 로직 재사용
- [ ] Repaired artifacts 입력으로 변경
- [ ] 출력 파일명 변경 (`*__postrepair.jsonl`)
- [ ] Lineage 필드 추가 (baseline_s5_snapshot_id 등)
- [ ] 단위 테스트

### 9.5 통합 및 E2E 테스트
- [ ] 전체 루프 통합 테스트
- [ ] 아티팩트 무결성 검증 테스트
- [ ] Error handling 테스트 (repair 실패 시에도 pipeline 계속)
- [ ] MI-CLEAR-LLM 로깅 검증

---

## 10. 참고 문서 (필수 읽기)

### 10.1 프로토콜 문서 (Canonical)

1. **멀티에이전트 수정 시스템 설계**
   - `0_Protocol/05_Pipeline_and_Execution/S5_Multiagent_Repair_Plan_OptionC_Canonical.md`
   - **핵심**: 전체 시스템 설계, 가드레일, 스키마 정의

2. **멀티에이전트 평가 워크플로우**
   - `0_Protocol/05_Pipeline_and_Execution/Multiagent_Evaluation_Workflow_Design.md`
   - **핵심**: Human rating 통합, 3-pass workflow 설계

3. **S5 Validation Contract**
   - `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Contract_Canonical.md`
   - **핵심**: S5의 역할과 제약사항 (S5R과 구분)

4. **S5 Validation Schema**
   - `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Schema_Canonical.md`
   - **핵심**: S5R 입력 스키마 정의

5. **S5 S1 평가 명세서**
   - `0_Protocol/04_Step_Contracts/Step05_S5/S5_S1_Validation_Specification.md`
   - **핵심**: S5의 2단계 평가 구조 (테이블 평가 + 인포그래픽 평가), 클러스터 처리 로직, 출력 스키마 상세
   - **필수**: S5R 구현 시 S5 출력 구조를 정확히 이해하기 위해 반드시 참조

### 10.2 코드 참고

1. **S5 Validator 구현**
   - `3_Code/src/05_s5_validator.py`
   - S5R과 S5' 구현 시 참고

2. **S1/S2 Generator**
   - `3_Code/src/01_generate_json.py`
   - `call_llm()`, LLM 호출 인프라 재사용

3. **Pipeline Execution**
   - `0_Protocol/05_Pipeline_and_Execution/README_run.md`
   - 실행 방법 및 RUN_TAG 관리

### 10.3 스키마 정의

1. **S1 Schema**
   - `0_Protocol/04_Step_Contracts/Step01_S1/S1_Stage1_Struct_JSON_Schema_Canonical.md`
   - S1R 출력이 준수해야 할 스키마

2. **S2 Schema**
   - `0_Protocol/04_Step_Contracts/Step02_S2/S2_Contract_and_Schema_Canonical.md`
   - S2R 출력이 준수해야 할 스키마

---

## 11. 의사결정 필요 사항 (DP1-DP3)

멀티에이전트 시스템 구현 전에 다음 사항을 결정해야 합니다:

### DP1: 수정본 사용 범위
- **질문**: 수정본이 메인 스터디의 export (S6)에 사용되는가, 아니면 탐색적 QA용인가?
- **영향**: S6 export 로직 변경 필요 여부

### DP2: 수정 실행 범위
- **질문**: 모든 group에 수정을 실행하는가, 아니면 `blocking_error=true` 또는 낮은 quality인 group만?
- **영향**: S5R 실행 조건 결정

### DP3: 새 콘텐츠 허용 여부
- **질문**: Generator가 원본에 없던 새로운 entity/claim을 추가할 수 있는가?
- **권장**: **No** (scope 변경 방지)
- **영향**: S5R instructions의 `no_new_content_scope` guardrail 강제

---

## 12. 개발 우선순위 권장사항

### Phase 1: S5R Repair Planner (1-2주)
1. S5 validation 결과 파싱
2. Issue 분석 및 instruction 생성 로직
3. Repair plan 스키마 구현
4. 단위 테스트

### Phase 2: S1R Regenerator (1주)
1. 원본 S1 inputs 로딩
2. Prompt 구성 (original + instructions)
3. LLM 호출 및 출력 저장
4. 단위 테스트

### Phase 3: S2R Regenerator (1-2주)
1. 원본 S2 inputs 로딩
2. Repaired S1 연동
3. Entity 단위 처리
4. 단위 테스트

### Phase 4: S5' Post-Repair Validator (3-5일)
1. S5 validator 재사용
2. Lineage 필드 추가
3. 단위 테스트

### Phase 5: 통합 및 E2E 테스트 (1주)
1. 전체 루프 통합
2. 아티팩트 무결성 검증
3. Error handling 테스트
4. MI-CLEAR-LLM 로깅 검증

---

## 13. 문의 및 지원

프로토콜 관련 질문:
- `0_Protocol/` 디렉토리의 Canonical 문서 참조
- 프로토콜 위반 시 즉시 확인 필요 (fail-fast 원칙)

코드 구조 질문:
- 기존 S5 validator (`05_s5_validator.py`) 참조
- 기존 S1/S2 generator (`01_generate_json.py`) 참조

---

## 14. 버전 히스토리

- **v1.0** (2025-12-29): 초기 인계 문서 작성
- **v1.1** (2025-12-30): S5의 2단계 평가 구조 (테이블 평가 + 인포그래픽 평가) 추가, 클러스터 처리 로직 명시, s5_s1_validation_specification.md 참조 추가

---

**작성자**: MeducAI Research Team  
**인계 대상**: 멀티에이전트 시스템 개발 담당 Agent  
**다음 단계**: Phase 1 (S5R Repair Planner) 구현 시작


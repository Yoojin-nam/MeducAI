# S5R 프롬프트 개선: 개발 전용 엔드포인트 (Development-Only Endpoint)

**Status**: Canonical  
**Version**: 1.0  
**Frozen**: No  
**Last Updated**: 2025-12-29  
**Scope**: S5 validation 결과를 기반으로 한 수동 프롬프트 개선 프로세스 (개발 전용, confirmatory 아님)

---

## 1. 목적 및 범위 (Purpose & Scope)

### 1.1 엔드포인트 정의

**Endpoint #2: S5-based Prompt Refinement (Development-Only)**

이 엔드포인트는 **내부 개발/개선 프로세스**로 정의되며, 다음을 명시적으로 제외합니다:
- ❌ Confirmatory effectiveness claims
- ❌ 일반화 가능한 "개선 효과" 주장
- ❌ 통계적 유의성 검정
- ❌ 모델 선택 (Endpoint #1과 분리)
- ❌ 멀티에이전트 수정 비교 (Endpoint #3과 분리)
- ❌ 학습 효과 설문 (Endpoint #4와 분리)

### 1.2 개발 신호 (Development Signal)

프롬프트 개선은 다음을 목적으로 합니다:
- ✅ 실패 모드 식별 (failure mode identification)
- ✅ 프롬프트 규칙 명확화 (prompt rule clarification)
- ✅ 내부 품질 지표 개선 (internal quality metrics)
- ✅ 개발 단계 안정화 (development stabilization)

**중요**: 모든 "개선" 표현은 개발/내부 지표로 제한되며, 외부 평가는 별도의 holdout 평가에서 수행됩니다 (이 엔드포인트의 범위 아님).

---

## 2. 입력/출력 (Inputs/Outputs)

### 2.1 입력 (Primary Truth Source)

**Primary Input**: `s5_validation__arm{arm}.jsonl`
- 위치: `2_Data/metadata/generated/<RUN_TAG>/s5_validation__arm{arm}.jsonl`
- 형식: NDJSON (한 줄 = 한 그룹)
- 스키마: `S5_VALIDATION_v1.0` (또는 v1.1+)
- 필수 필드:
  - `group_id`
  - `s1_table_validation.blocking_error`
  - `s1_table_validation.issues[]` (optional fields: `issue_code`, `recommended_fix_target`, `prompt_patch_hint`)
  - `s2_cards_validation.blocking_error`
  - `s2_cards_validation.issues[]` (optional fields: `issue_code`, `recommended_fix_target`, `prompt_patch_hint`)

**Secondary Input** (참고용): `s5_report__arm{arm}.md`
- 위치: `2_Data/metadata/generated/<RUN_TAG>/reports/s5_report__arm{arm}.md`
- 용도: 인간 가독성 향상, Patch Backlog 섹션 참고
- **주의**: JSONL이 primary truth source이며, MD 리포트는 보조 참고용

### 2.2 출력 (Artifacts)

#### 2.2.1 프롬프트 파일

**Canonical 프롬프트** (새 버전):
- 위치: `3_Code/prompt/{PROMPT_NAME}__S5R{k}__v{XX}.md`
- 예: `S1_SYSTEM__S5R1__v13.md`
- 헤더에 버전 정보 포함:
  ```markdown
  # S1_SYSTEM__S5R1__v13.md
  
  **S5R Round**: S5R1
  **Version**: v13
  **Previous Version**: S5R0__v12
  **Refinement Run Tag**: DEV_armG_mm_S5R0_before_rerun_preFix_20251229_203653__rep2
  **Refinement Date**: 2025-12-29
  **Commit Hash**: abc1234...
  ```

**Archived 프롬프트** (이전 버전):
- 위치: `3_Code/prompt/archive/{PROMPT_NAME}__S5R{k}__v{XX}.md`
- 상태: Frozen (수정 불가)

#### 2.2.2 변경 이력 문서

**Change Log**:
- 위치: `2_Data/metadata/generated/<RUN_TAG>/prompt_refinement/change_log__S5R{k}.md`
- 내용:
  - 변경된 프롬프트 목록
  - 각 변경의 근거 (issue_code, count, examples)
  - Diff 요약

**Patch Backlog** (구조화):
- 위치: `2_Data/metadata/generated/<RUN_TAG>/prompt_refinement/patch_backlog__S5R{k}.json`
- 형식: JSON
- 내용: `issue_code` × `recommended_fix_target` 그룹화

**Diff Report**:
- 위치: `2_Data/metadata/generated/<RUN_TAG>/prompt_refinement/diff_report__{PROMPT_NAME}__S5R{k}.md`
- 형식: Markdown diff

---

## 3. 거버넌스 제약사항 (Governance Constraints)

### 3.1 스키마 불변성 (Schema Invariance) - Non-Negotiable

프롬프트 개선 시 다음은 **절대 변경 불가**:
- ❌ JSON 스키마 구조 변경
- ❌ 필수 키 추가/삭제/이름 변경
- ❌ 데이터 타입 변경
- ❌ 중첩 레벨 변경
- ❌ Enum 값 변경

**허용되는 변경**:
- ✅ 프롬프트 텍스트 개선 (규칙 추가, 명확화)
- ✅ 예시 업데이트
- ✅ 제약사항 강화 (더 명확한 지시사항)

### 3.2 추적 가능성 (Traceability) - Required

모든 프롬프트 개선은 다음 정보를 포함해야 함:
- `run_tag`: 어떤 실행에서 이슈가 발견되었는지
- `commit_hash`: 프롬프트 변경이 커밋된 git commit hash
- `s5_snapshot_id`: S5 validation snapshot ID (재현성)
- `refinement_date`: 개선 일자
- `rationale`: 각 변경의 근거 (issue_code, count, examples)

### 3.3 MI-CLEAR-LLM 로깅 (If LLM Used)

프롬프트 개선 과정에서 LLM을 사용하는 경우 (예: 프롬프트 개선 가이드 활용):
- 모든 LLM 호출 로깅 필수
- `prompt_id`, `prompt_hash` 기록
- `model_name`, `temperature`, `top_p` 등 설정 기록
- 위치: `2_Data/metadata/generated/<RUN_TAG>/prompt_refinement/llm_logs__S5R{k}.jsonl`

---

## 4. 개발 지표 정의 (Development Metrics)

### 4.1 Primary Development Metric

**Blocking Issue Rate per Group** (단일 primary metric)

정의:
- `blocking_issue_rate_per_group = (groups with blocking_error=true) / total_groups`
- 단위: 그룹 레벨 (group-level)
- 해석: 개발 신호로서 blocking error가 있는 그룹의 비율

**측정 방법**:
```python
blocking_groups = sum(1 for record in s5_validation if 
                      record['s1_table_validation']['blocking_error'] or 
                      record['s2_cards_validation']['blocking_error'])
total_groups = len(s5_validation)
blocking_rate = blocking_groups / total_groups
```

### 4.2 Secondary Development Metrics (Optional)

**Blocking Issue Count per Group**:
- `blocking_issue_count_per_group = total_blocking_issues / total_groups`
- 단위: 그룹당 평균 blocking issue 수

**Major Issue Count** (non-blocking but high-severity):
- `major_issue_count_per_group = total_major_issues / total_groups`
- 정의: `severity == "major"` 또는 특정 `issue_code` 집합

**Total Weighted Issue Score** (탐색적):
- 각 이슈에 가중치 부여 (blocking=10, major=5, minor=1)
- `weighted_score_per_group = sum(weighted_issues) / total_groups`

**중요**: Secondary metrics는 descriptive 목적으로만 사용하며, 통계적 검정은 수행하지 않음.

---

## 5. 반복 정책 (Iteration Policy)

### 5.1 최대 반복 횟수

**Default**: 단일 개선 단계 (S5R0 → S5R1)

**Optional**: 최대 2단계 (S5R0 → S5R1 → S5R2)
- 조건: 첫 번째 개선 후에도 blocking issue가 지속되는 경우
- 사전 정의된 중지 조건 필요 (아래 참조)

### 5.2 중지 규칙 (Stopping Rule)

다음 조건 중 하나가 충족되면 추가 개선 중지:

1. **Blocking Issue 제거**: `blocking_issue_rate_per_group == 0`
2. **Marginal Gain 임계값**: 새로운 blocking issue가 나타나거나, 개선 효과가 임계값 미만
3. **최대 반복 도달**: S5R2까지 도달 (더 이상 진행 안 함)

**명시적 금지**:
- ❌ "개선이 보일 때까지 반복" (improve until it looks good)
- ❌ 통계적 유의성 도달까지 반복
- ❌ 사후 분석 기반 추가 개선

### 5.3 반복 기록

각 반복은 다음을 기록:
- `s5r_round`: S5R0, S5R1, S5R2
- `iteration_count`: 현재 반복 횟수 (1 또는 2)
- `stopping_reason`: 중지 이유 (blocking_removed, max_iteration, marginal_gain_threshold)

---

## 6. 데이터 누수 방지 (Data Leakage Disclaimer)

### 6.1 명시적 제한

**Development Set 사용**:
- 프롬프트 개선은 **development set**에서 식별된 실패 모드를 기반으로 수행됩니다.
- Development set은 failure mode identification과 prompt adjustment 목적으로 사용됩니다.

**Generalization Claims 금지**:
- 이 엔드포인트에서 **일반화 가능한 "개선 효과"를 주장하지 않습니다**.
- 모든 일반화 주장은 별도의 **holdout evaluation**에서 수행되며, 이는 이 엔드포인트의 범위가 아닙니다.

### 6.2 논문 기술 권장사항

**Methods 섹션**:
```
"Prompt refinement was performed as an internal development process 
based on S5 validation outputs from the development set (n=11 groups). 
This process identified failure modes and guided prompt rule 
clarifications. All refinements were limited to a maximum of two 
iterations (S5R0 → S5R1 → S5R2) with predefined stopping rules. 
Any claims about generalization require separate evaluation on a 
holdout set, which is not part of this development endpoint."
```

**Limitations 섹션**:
```
"Prompt refinement was performed on a development set and should 
not be interpreted as confirmatory evidence of improvement. 
Generalization claims require separate holdout evaluation."
```

---

## 7. 단계별 절차 (Step-by-Step Procedure)

### 7.1 S5 출력 검토

1. **JSONL 파일 확인**:
   ```bash
   # Primary truth source
   cat 2_Data/metadata/generated/<RUN_TAG>/s5_validation__arm{arm}.jsonl | jq .
   ```

2. **리포트 확인** (보조):
   ```bash
   # Human-readable reference
   cat 2_Data/metadata/generated/<RUN_TAG>/reports/s5_report__arm{arm}.md
   ```

### 7.2 Patch Backlog 생성

**자동 생성** (권장):
```bash
python3 3_Code/src/tools/prompt_refinement/build_patch_backlog.py \
  --base_dir . \
  --run_tag <RUN_TAG> \
  --arm <ARM> \
  --output 2_Data/metadata/generated/<RUN_TAG>/prompt_refinement/patch_backlog__S5R{k}.json
```

**수동 생성** (대안):
- JSONL에서 `issue_code`, `recommended_fix_target`, `prompt_patch_hint` 추출
- `recommended_fix_target`별로 그룹화
- 우선순위 결정 (P0: blocking, P1: high-frequency)

### 7.3 프롬프트 편집 (Cursor 사용)

1. **현재 프롬프트 로드**: `3_Code/prompt/{PROMPT_NAME}__S5R{k}__v{XX}.md`
2. **Patch Backlog 참고**: 어떤 이슈를 해결할지 확인
3. **프롬프트 수정**: Cursor에서 직접 편집
   - 스키마 불변성 확인
   - 규칙 추가/명확화
4. **변경 근거 기록**: 각 변경에 대해 issue_code, count, examples 기록

### 7.4 Diff 생성

**자동 생성**:
```bash
python3 3_Code/src/tools/prompt_refinement/make_prompt_diff_report.py \
  --base_dir . \
  --prompt_name S1_SYSTEM \
  --old_version S5R0__v12 \
  --new_version S5R1__v13 \
  --output 2_Data/metadata/generated/<RUN_TAG>/prompt_refinement/diff_report__S1_SYSTEM__S5R1.md
```

### 7.5 Smoke Validation

**스키마 불변성 검증**:
```bash
python3 3_Code/src/tools/prompt_refinement/smoke_validate_prompt.py \
  --base_dir . \
  --prompt_file 3_Code/prompt/S1_SYSTEM__S5R1__v13.md \
  --schema_file 0_Protocol/04_Step_Contracts/Step01_S1/S1_Stage1_Struct_JSON_Schema_Canonical.md
```

**검증 항목**:
- [ ] 스키마 관련 키워드 변경 없음
- [ ] 필수 섹션 모두 존재
- [ ] 마크다운 형식 유효
- [ ] JSON 스키마 참조 정확

### 7.6 변경 이력 기록

**Change Log 작성**:
- 위치: `2_Data/metadata/generated/<RUN_TAG>/prompt_refinement/change_log__S5R{k}.md`
- 내용:
  - 변경된 프롬프트 목록
  - 각 변경의 근거
  - Primary metric 변화 (blocking_issue_rate_per_group)

### 7.7 프롬프트 버전 생성 및 레지스트리 업데이트

1. **새 프롬프트 파일 생성**: `{PROMPT_NAME}__S5R{k}__v{XX}.md`
2. **이전 버전 아카이브**: `archive/`로 이동
3. **레지스트리 업데이트**: `3_Code/prompt/_registry.json` 수정
4. **Git 커밋**: 모든 변경사항 커밋 (commit hash 기록)

---

## 8. 아티팩트 네이밍 및 저장 (Artifact Naming & Storage)

### 8.1 네이밍 규칙

**Canonical 문서**:
- 파일명에 버전 없음: `S5R_Prompt_Refinement_Development_Endpoint_Canonical.md`
- 버전은 헤더에만: `**Version**: 1.0`

**프롬프트 파일**:
- S5R 정보 포함: `S1_SYSTEM__S5R1__v13.md`
- 이전 버전은 `archive/`로 이동

**변경 이력**:
- `2_Data/metadata/generated/<RUN_TAG>/prompt_refinement/` 하위에 저장
- `change_log__S5R{k}.md`
- `patch_backlog__S5R{k}.json`
- `diff_report__{PROMPT_NAME}__S5R{k}.md`

### 8.2 저장 구조

```
2_Data/metadata/generated/<RUN_TAG>/
  ├── s5_validation__arm{arm}.jsonl          # Primary input
  ├── reports/
  │   └── s5_report__arm{arm}.md           # Secondary input
  └── prompt_refinement/                    # Output artifacts
      ├── patch_backlog__S5R{k}.json
      ├── change_log__S5R{k}.md
      ├── diff_report__S1_SYSTEM__S5R{k}.md
      ├── diff_report__S2_SYSTEM__S5R{k}.md
      └── llm_logs__S5R{k}.jsonl           # If LLM used

3_Code/prompt/
  ├── S1_SYSTEM__S5R1__v13.md              # New canonical
  ├── archive/
  │   └── S1_SYSTEM__S5R0__v12.md          # Frozen previous
  └── _registry.json                        # Updated
```

---

## 9. 체크리스트 (Checklist)

자세한 체크리스트는 다음 문서 참조:
- `0_Protocol/00_Governance/supporting/Prompt_governance/S5R_Manual_Refinement_Checklist.md`

---

## 10. 관련 문서

- `0_Protocol/05_Pipeline_and_Execution/S5_Prompt_Refinement_Methodology_Canonical.md` (기존 방법론)
- `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Schema_Canonical.md` (S5 스키마)
- `0_Protocol/00_Governance/supporting/Prompt_governance/S1_Prompt_Improvement_Guide.md` (S1 개선 가이드)
- `0_Protocol/00_Governance/supporting/Prompt_governance/S2_Prompt_Improvement_Guide.md` (S2 개선 가이드)
- `0_Protocol/05_Pipeline_and_Execution/S5_Version_Naming_S5R_Canonical.md` (버전 네이밍)

---

## 11. 변경 이력

- **v1.0** (2025-12-29): 초기 작성 (개발 전용 엔드포인트로 명확화)


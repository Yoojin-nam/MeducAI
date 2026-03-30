# S5R 프롬프트 개선 실험 실행 명령어 템플릿

**Status**: Execution Guide (Canonical)  
**Last Updated**: 2025-12-29  
**Purpose**: S5R 실험 각 Phase별 실행 명령어 템플릿 제공

---

## 전제 조건

- 현재 작업 디렉토리: **MeducAI 프로젝트 루트**
- Python venv 활성화
- `.env` 파일 존재 (provider keys, base path)
- 프롬프트 레지스트리: `3_Code/prompt/_registry.json`

---

## Phase 1: Baseline 측정 (S5R0)

### 1.1 S1/S2 생성 (S5R0: v12/v9)

**Run Tag 형식**: `DEV_armG_mm_S5R0_before_rerun_preFix_YYYYMMDD_HHMMSS__rep1` 및 `__rep2`

**Run Tag 예시 (현재 시점 기준)**:
- rep1: `DEV_armG_mm_S5R0_before_rerun_preFix_20251230_185052__rep1`
- rep2: `DEV_armG_mm_S5R0_before_rerun_preFix_20251230_185052__rep2`
- 참고: 이전 실험 - `DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep1`

**실행 명령어 (rep1) - FINAL mode (모든 Entity 생성, 필수)**:
```bash
RUN_TAG_REP1="DEV_armG_mm_S5R0_before_rerun_preFix_$(date +%Y%m%d_%H%M%S)__rep1"
echo "Run tag: $RUN_TAG_REP1"

# 11개 그룹 선택 파일 생성 (예시)
# groups_canonical.csv에서 11개 그룹의 group_key를 선택하여 파일 생성
# temp_selected_groups.txt 예시:
#   group_key_1
#   group_key_2
#   ...
#   group_key_11

# FINAL mode로 실행 (모든 Entity에 대해 Entity당 2장 생성)
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G \
  --mode FINAL \
  --stage both \
  --only_group_keys_file temp_selected_groups.txt
```

**중요**: 
- **S0 mode는 사용하지 않음**: S0 mode는 Entity를 최대 4개만 처리 (3×4 규칙)
- **FINAL mode 필수**: 모든 Entity에 대해 카드를 생성해야 함
- `--only_group_keys_file`: 11개 그룹만 선택하기 위해 필요
- **같은 그룹 사용 필수**: 모든 Phase에서 동일한 `temp_selected_groups.txt` 사용 (paired comparison을 위해)
- 이전 S5R0 실험은 11개 그룹이 실행되었음 (확인됨)

**Run Tag 형식 (정확한 규칙)**:
- 형식: `DEV_armG_mm_S5R0_before_rerun_preFix_YYYYMMDD_HHMMSS__rep1` 및 `__rep2`
- 예시 (현재 시점 기준): `DEV_armG_mm_S5R0_before_rerun_preFix_20251230_185052__rep1`
- 참고: 이전 실험 - `DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep1`

**rep2도 동일하게 실행** (독립적인 replicate):
```bash
RUN_TAG_REP2="DEV_armG_mm_S5R0_before_rerun_preFix_$(date +%Y%m%d_%H%M%S)__rep2"
# (동일한 명령어, RUN_TAG_REP2 사용)
```

### 1.2 S3 이미지 스펙 생성

**실행 전략**: rep1 완료 후 rep2 실행 (권장)

**rep1 실행**:
```bash
python3 3_Code/src/03_s3_policy_resolver.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G
```

**rep2 실행** (rep1 완료 후):
```bash
python3 3_Code/src/03_s3_policy_resolver.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP2" \
  --arm G
```

### 1.3 S4 이미지 생성

**rep1 실행**:
```bash
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G
```

**rep2 실행** (rep1 완료 후):
```bash
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP2" \
  --arm G
```

### 1.4 S5 검증 실행

**기본 실행 (Target 1용: 기본 레지스트리 사용)**:
```bash
# rep1
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G

# rep2
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP2" \
  --arm G
```

**Judge 교차평가 (Target 2용: 별도 레지스트리 지정)**:
```bash
# S5R0 생성물을 S5R2 judge로 평가
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag "${RUN_TAG_REP1}__evalS5R2" \
  --arm G \
  --prompt_registry 3_Code/prompt/_registry_S5R2.json

# rep2도 동일
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag "${RUN_TAG_REP2}__evalS5R2" \
  --arm G \
  --prompt_registry 3_Code/prompt/_registry_S5R2.json
```

### 1.5 S5 리포트 생성

**rep1 리포트**:
```bash
python3 3_Code/src/tools/s5/s5_report.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G
```

**rep2 리포트**:
```bash
python3 3_Code/src/tools/s5/s5_report.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP2" \
  --arm G
```

**출력 위치**: `2_Data/metadata/generated/{run_tag}/reports/s5_report__armG.md`

---

## Phase 2: 1차 프롬프트 개선 (S5R1)

### 2.1 S5R0 리포트 분석

- Primary endpoint: `S2_any_issue_rate_per_group`
- Secondary endpoints: `IMG_any_issue_rate_per_group`, `S2_issues_per_card_per_group`
- Targeted issue codes 분석
- Patch backlog 확인

### 2.2 프롬프트 개선 (S5R1)

- S1/S2 프롬프트 수정 (새 파일 생성: `S1_SYSTEM__S5R1__v13.md`, `S2_SYSTEM__S5R1__v10.md`)
- S4 프롬프트도 필요시 수정
- 레지스트리 업데이트

### 2.3 재생성 및 재평가 (S5R1)

**Run Tag 형식**: `DEV_armG_mm_S5R1_after_postFix_YYYYMMDD_HHMMSS__rep1` 및 `__rep2`

**Run Tag 예시 (현재 시점 기준)**:
- rep1: `DEV_armG_mm_S5R1_after_postFix_20251230_185052__rep1`
- rep2: `DEV_armG_mm_S5R1_after_postFix_20251230_185052__rep2`
- 참고: 이전 실험 - `DEV_armG_mm_S5R1_after_postFix_20251230_112411__rep1`

**S1/S2 생성 (11개 그룹만 실행) - FINAL mode (모든 Entity 생성, 필수)**:
```bash
# rep1
RUN_TAG_REP1="DEV_armG_mm_S5R1_after_postFix_$(date +%Y%m%d_%H%M%S)__rep1"
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G \
  --mode FINAL \
  --stage both \
  --only_group_keys_file temp_selected_groups.txt

# rep2
RUN_TAG_REP2="DEV_armG_mm_S5R1_after_postFix_$(date +%Y%m%d_%H%M%S)__rep2"
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP2" \
  --arm G \
  --mode FINAL \
  --stage both \
  --only_group_keys_file temp_selected_groups.txt
```

**중요**: Phase 1과 동일한 11개 그룹을 사용해야 함 (같은 `temp_selected_groups.txt` 파일 사용)

**실행 순서**: Phase 1과 동일
1. S1/S2 생성 (rep1 → rep2) - 위 명령어 사용
2. S3 실행 (rep1 → rep2)
3. S4 실행 (rep1 → rep2)
4. S5 검증 (rep1 → rep2)
5. S5 리포트 (rep1 → rep2)

---

## Phase 3: 2차 프롬프트 개선 (S5R2)

### 3.1 S5R1 리포트 분석

- S5R0 vs S5R1 비교
- 개선 효과 측정
- 추가 개선 포인트 식별

### 3.2 프롬프트 개선 (S5R2)

- S1/S2 프롬프트 수정 (새 파일: `S1_SYSTEM__S5R2__v14.md`, `S2_SYSTEM__S5R2__v11.md`)
- 레지스트리 업데이트

### 3.3 재생성 및 재평가 (S5R2)

**Run Tag 형식**: `DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1` 및 `__rep2`

**Run Tag 예시 (현재 시점 기준)**:
- rep1: `DEV_armG_mm_S5R2_after_postFix_20251230_185052__rep1`
- rep2: `DEV_armG_mm_S5R2_after_postFix_20251230_185052__rep2`

**S1/S2 생성 (11개 그룹만 실행) - FINAL mode (모든 Entity 생성, 필수)**:
```bash
# rep1
RUN_TAG_REP1="DEV_armG_mm_S5R2_after_postFix_$(date +%Y%m%d_%H%M%S)__rep1"
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G \
  --mode FINAL \
  --stage both \
  --only_group_keys_file temp_selected_groups.txt

# rep2
RUN_TAG_REP2="DEV_armG_mm_S5R2_after_postFix_$(date +%Y%m%d_%H%M%S)__rep2"
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP2" \
  --arm G \
  --mode FINAL \
  --stage both \
  --only_group_keys_file temp_selected_groups.txt
```

**Run Tag 형식 (정확한 규칙)**:
- 형식: `DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1` 및 `__rep2`
- 예시 (현재 시점 기준): `DEV_armG_mm_S5R2_after_postFix_20251230_185052__rep1`

**중요**: Phase 1과 동일한 11개 그룹을 사용해야 함 (같은 `temp_selected_groups.txt` 파일 사용)

**실행 순서**: Phase 1과 동일
1. S1/S2 생성 (rep1 → rep2) - 위 명령어 사용
2. S3 실행 (rep1 → rep2)
3. S4 실행 (rep1 → rep2)
4. S5 검증 (rep1 → rep2) - **중요: S5R2 validator 사용**
5. S5 리포트 (rep1 → rep2)

**S5 검증 실행 (Target 1용: S5R2 validator로 평가)**:
```bash
# rep1
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G
  # 기본 레지스트리 사용 (S5R2 validator 포함)

# rep2
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP2" \
  --arm G
```

---

## Phase 4: 최종 비교 분석

### 4.1 비교 분석 실행 (Prereg 방식)

**S5R0 vs S5R2 비교 (replicate aggregation 포함, prereg endpoint/통계 사용)**:

```bash
python3 3_Code/src/05_s5_compare_mm.py \
  --base_dir . \
  --arm G \
  --before_run_tag DEV_armG_mm_S5R0_before_rerun_preFix_YYYYMMDD_HHMMSS__rep1 \
  --before_run_tag DEV_armG_mm_S5R0_before_rerun_preFix_YYYYMMDD_HHMMSS__rep2 \
  --after_run_tag DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1 \
  --after_run_tag DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep2
```

**또는 wrapper 스크립트 사용**:
```bash
python3 3_Code/src/05_s5_compare_mm.py \
  --base_dir . \
  --arm G \
  --before_run_tag <S5R0_REP1> \
  --before_run_tag <S5R0_REP2> \
  --after_run_tag <S5R2_REP1> \
  --after_run_tag <S5R2_REP2>
```

**출력 위치**: `2_Data/metadata/generated/COMPARE__<before_tag0>__VS__<after_tag0>/`

**출력 파일**:
- `summary__mm.md`: 마크다운 리포트 (prereg 통계 포함)
- `group_level__mm.csv`: group-level 집계 데이터 (replicate 안정성 포함)
- `paired_long__mm.csv`: paired long-form 데이터
- `stats_summary__mm.csv`: 통계 요약
- `targeted_codes__text.csv`: 텍스트 issue 코드별 집계
- `targeted_codes__image.csv`: 이미지 issue 코드별 집계

### 4.2 Prereg Endpoint

**Primary**: `S2_any_issue_rate_per_group` (그룹 내 S2 카드 중 `issue_count>=1`인 카드 비율)

**Key Secondary (≤3개)**:
1. `IMG_any_issue_rate_per_group` (이미지 중 `issue_count>=1` 비율)
2. `S2_issues_per_card_per_group` (카드 1장당 평균 issue 개수)
3. `TA_bad_rate_per_group` (technical_accuracy < 1.0인 카드 비율)

### 4.3 통계 분석 (Prereg 방법)

- **Estimand**: `median(diff_i)` (paired difference의 중앙값)
- **Primary test**: Wilcoxon signed-rank test (paired)
- **Effect size & CI**: Bootstrap 95% CI on paired differences
- **Directionality**: 개선 그룹 수 / 전체 그룹 수 (primary endpoint에서 `After < Before`)
- **n**: 11 groups (replicate 수 아님)

### 4.4 Replicate 안정성 보고

- `group_level__mm.csv`에 rep1, rep2 값 및 SD(또는 min-max) 컬럼 포함
- `summary__mm.md`에 안정성 지표 요약 포함

### 4.5 Expansion Criteria 평가 (HOLDOUT 결정)

**Prereg 기준** (from `S5R_Experiment_Power_and_Significance_Plan.md`):
- Expand if BOTH:
  1) Primary endpoint에서 **≥9/11 groups improve** (`After < Before`), AND
  2) Primary endpoint의 **median absolute reduction ≥ 5 percentage points**

**실행 명령어**:
```bash
# 비교 분석 결과 디렉토리 지정
COMPARE_DIR="2_Data/metadata/generated/COMPARE__<before_tag0>__VS__<after_tag0>"

# Expansion criteria 평가
python3 3_Code/src/05_evaluate_expansion_criteria.py \
  --base_dir . \
  --compare_dir "$COMPARE_DIR"
```

**또는 wrapper 스크립트 사용**:
```bash
python3 3_Code/src/tools/s5/s5_evaluate_expansion_criteria.py \
  --base_dir . \
  --compare_dir "$COMPARE_DIR" \
  --primary_endpoint S2_any_issue_rate_per_group
```

**출력 위치**: `{compare_dir}/expansion_criteria_evaluation.md`

**출력 내용**:
- Criterion 1 평가: 개선된 그룹 수 / 전체 그룹 수
- Criterion 2 평가: Median absolute reduction (percentage points)
- HOLDOUT 확장 권장 여부 (✅ EXPAND / ❌ DO NOT EXPAND)

**결과 해석**:
- **EXPAND TO HOLDOUT**: 두 기준 모두 충족 → HOLDOUT 확장 진행 (n=30-40 groups)
- **DO NOT EXPAND**: 기준 미충족 → DEV 결과만 사용 (탐색적 해석)

---

## Target 1/2 분리 전략

### Target 1: Generation prompt improvement effect (Content quality)

**질문**: "생성 프롬프트(S1/S2/S4)를 개선하면 생성물의 품질이 좋아지는가?"

**요건**: 평가자(validator/judge)는 고정(Fixed Judge)

**실행 방법**:
- Before/After 모두 동일한 S5 validator prompt/version 사용
- 모든 S5 실행에서 `--prompt_registry` 옵션 없이 기본 레지스트리 사용하거나, 동일 레지스트리 경로 지정

**예시**:
```bash
# S5R0 생성물 평가 (기본 레지스트리 = S5R0 validator)
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag "$S5R0_RUN_TAG" \
  --arm G

# S5R2 생성물 평가 (기본 레지스트리 = S5R2 validator)
# 하지만 Target 1을 위해서는 S5R0 validator로도 평가 필요
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag "${S5R2_RUN_TAG}__evalS5R0" \
  --arm G \
  --prompt_registry 3_Code/prompt/_registry_S5R0.json
```

### Target 2: S5 validator prompt improvement effect (Judge behavior)

**질문**: "S5 validator prompt(S5R0→S5R2)가 판단 기준/감지 행동에 어떤 변화를 만드는가?"

**요건**: 평가 대상 콘텐츠는 고정(Frozen Content)

**실행 방법**:
- 동일 run_tag의 산출물(S1/S2/S4)에 대해 `--prompt_registry`로 다른 S5 judge 버전 지정
- Run tag에 `__evalS5Rk` suffix 추가하여 별도 저장 (덮어쓰기 방지)

**예시**:
```bash
# S5R0 생성물을 S5R0 judge로 평가 (기본)
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag "$S5R0_RUN_TAG" \
  --arm G

# 동일한 S5R0 생성물을 S5R2 judge로 평가 (Target 2)
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag "${S5R0_RUN_TAG}__evalS5R2" \
  --arm G \
  --prompt_registry 3_Code/prompt/_registry_S5R2.json
```

### 교차평가 설계 (권장)

- **Target 1 주 분석**: S5R0 생성물 vs S5R2 생성물 (동일 judge S5R2로 평가)
- **Target 2 보조 분석**: S5R0 생성물을 S5R0 judge vs S5R2 judge로 평가 (judge 변화량 계량)

---

## 주의사항

### 1. Replicate 실행 순서

**옵션 A (권장)**: rep1 전체 완료 → rep2 전체 완료
- 장점: 각 replicate의 일관성 유지, 디버깅 용이, 데이터 구조 명확
- 단점: 시간이 오래 걸림

**옵션 B**: 단계별로 rep1/rep2 교차 실행
- 장점: 단계별 비교 가능, 중간 결과 확인 용이
- 단점: 복잡도 증가, 데이터 구조 관리 복잡

### 2. Judge Version 고정 (Target 1 인과 주장)

**중요**: Target 1 (Generation effect) 주장을 위해서는:
- Before와 After 생성물을 **동일한 S5 validator version**으로 평가해야 함
- Cross-evaluation 필요: After 생성물을 S5R0으로도 평가하여 Target 1 주장 가능

### 3. Replicate Aggregation

- Replicate는 독립 표본수를 늘리지 않음 (n은 여전히 group 수, n=11)
- 각 조건(Before/After)×group에 대해 replicate별 endpoint 계산 후 **평균(mean)** 사용
- 비교 분석 스크립트가 자동으로 처리함

---

## 참고 문서

- `0_Protocol/05_Pipeline_and_Execution/README_run.md`: **운영 Runbook (Option C / S6 gate 포함)**
- `3_Code/Scripts/smoke_optionc_one_group_e2e.sh`: **Option C 1-group E2E smoke 스크립트**
- `S5R_프롬프트_개선_실험_계획_및_레지스트리_개선_a84380c0.plan.md`: 전체 실험 계획
- `S5R_Experiment_Power_and_Significance_Plan.md`: 실험 설계 및 분석 계획
- `S5R_Execution_Plan_Current_Status.md`: 현재 데이터 상태 및 실행 계획


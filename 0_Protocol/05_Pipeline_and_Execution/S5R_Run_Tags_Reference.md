# S5R 실험 Run Tag 참조 가이드

**Status**: Execution Reference  
**Last Updated**: 2025-12-30  
**Purpose**: S5R 실험 각 Phase별 정확한 Run Tag 형식 및 예시 제공

---

## 중요: 같은 그룹 사용

**계획 문서 확인 결과**: ✅ **같은 11개 그룹을 모든 Phase에서 사용해야 합니다**

**이유**:
1. **Paired comparison**: Phase 4에서 S5R0 vs S5R2 비교는 같은 그룹 간 비교가 필요
2. **계획 문서 명시**: "각 replicate에 대해 동일한 11개 그룹에 대해 독립적으로 실행"
3. **통계 분석**: n=11 groups (paired)로 분석하므로 그룹이 일치해야 함

**사용 파일**: `temp_selected_groups.txt` (모든 Phase에서 동일하게 사용)

---

## Run Tag 형식 (정확한 규칙)

### Phase 1: Baseline 측정 (S5R0)

**형식**: `DEV_armG_mm_S5R0_before_rerun_preFix_YYYYMMDD_HHMMSS__rep1` 및 `__rep2`

**예시 (현재 시점 기준)**:
```bash
# rep1
DEV_armG_mm_S5R0_before_rerun_preFix_20251230_185052__rep1

# rep2
DEV_armG_mm_S5R0_before_rerun_preFix_20251230_185052__rep2
```

**생성 명령어**:
```bash
RUN_TAG_REP1="DEV_armG_mm_S5R0_before_rerun_preFix_$(date +%Y%m%d_%H%M%S)__rep1"
RUN_TAG_REP2="DEV_armG_mm_S5R0_before_rerun_preFix_$(date +%Y%m%d_%H%M%S)__rep2"
```

**참고**: 이전 실험 run tag (참고용)
- `DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep1`
- `DEV_armG_mm_S5R0_before_rerun_preFix_20251229_203653__rep2`

---

### Phase 2: 1차 프롬프트 개선 (S5R1)

**형식**: `DEV_armG_mm_S5R1_after_postFix_YYYYMMDD_HHMMSS__rep1` 및 `__rep2`

**예시 (현재 시점 기준)**:
```bash
# rep1
DEV_armG_mm_S5R1_after_postFix_20251230_185052__rep1

# rep2
DEV_armG_mm_S5R1_after_postFix_20251230_185052__rep2
```

**생성 명령어**:
```bash
RUN_TAG_REP1="DEV_armG_mm_S5R1_after_postFix_$(date +%Y%m%d_%H%M%S)__rep1"
RUN_TAG_REP2="DEV_armG_mm_S5R1_after_postFix_$(date +%Y%m%d_%H%M%S)__rep2"
```

**참고**: 이전 실험 run tag (참고용)
- `DEV_armG_mm_S5R1_after_postFix_20251230_112411__rep1`
- `DEV_armG_mm_S5R1_after_postFix_20251230_140936__rep2`

---

### Phase 3: 2차 프롬프트 개선 (S5R2)

**형식**: `DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1` 및 `__rep2`

**예시 (현재 시점 기준)**:
```bash
# rep1
DEV_armG_mm_S5R2_after_postFix_20251230_185052__rep1

# rep2
DEV_armG_mm_S5R2_after_postFix_20251230_185052__rep2
```

**생성 명령어**:
```bash
RUN_TAG_REP1="DEV_armG_mm_S5R2_after_postFix_$(date +%Y%m%d_%H%M%S)__rep1"
RUN_TAG_REP2="DEV_armG_mm_S5R2_after_postFix_$(date +%Y%m%d_%H%M%S)__rep2"
```

---

## Judge 교차평가 Run Tag (Target 2용)

**형식**: 기존 run tag에 `__evalS5Rk` suffix 추가

**예시**:
```bash
# S5R0 생성물을 S5R2 judge로 평가
DEV_armG_mm_S5R0_before_rerun_preFix_20251230_185052__rep1__evalS5R2
DEV_armG_mm_S5R0_before_rerun_preFix_20251230_185052__rep2__evalS5R2
```

**생성 명령어**:
```bash
BASE_RUN_TAG="DEV_armG_mm_S5R0_before_rerun_preFix_20251230_185052__rep1"
EVAL_RUN_TAG="${BASE_RUN_TAG}__evalS5R2"
```

---

## 실행 명령어 예시 (완전한 형태)

### Phase 1: S5R0 (Baseline)

```bash
# Run tag 생성
RUN_TAG_REP1="DEV_armG_mm_S5R0_before_rerun_preFix_$(date +%Y%m%d_%H%M%S)__rep1"
RUN_TAG_REP2="DEV_armG_mm_S5R0_before_rerun_preFix_$(date +%Y%m%d_%H%M%S)__rep2"

echo "rep1: $RUN_TAG_REP1"
echo "rep2: $RUN_TAG_REP2"

# S1/S2 생성 (rep1)
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G \
  --mode FINAL \
  --stage both \
  --only_group_keys_file temp_selected_groups.txt

# S1/S2 생성 (rep2)
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP2" \
  --arm G \
  --mode FINAL \
  --stage both \
  --only_group_keys_file temp_selected_groups.txt
```

### Phase 3: S5R2 (최종)

```bash
# Run tag 생성
RUN_TAG_REP1="DEV_armG_mm_S5R2_after_postFix_$(date +%Y%m%d_%H%M%S)__rep1"
RUN_TAG_REP2="DEV_armG_mm_S5R2_after_postFix_$(date +%Y%m%d_%H%M%S)__rep2"

echo "rep1: $RUN_TAG_REP1"
echo "rep2: $RUN_TAG_REP2"

# S1/S2 생성 (rep1) - 동일한 temp_selected_groups.txt 사용
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G \
  --mode FINAL \
  --stage both \
  --only_group_keys_file temp_selected_groups.txt

# S1/S2 생성 (rep2) - 동일한 temp_selected_groups.txt 사용
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP2" \
  --arm G \
  --mode FINAL \
  --stage both \
  --only_group_keys_file temp_selected_groups.txt
```

---

## 비교 분석 실행 (Phase 4)

**S5R0 vs S5R2 비교**:
```bash
python3 3_Code/src/05_s5_compare_mm.py \
  --base_dir . \
  --arm G \
  --before_run_tag DEV_armG_mm_S5R0_before_rerun_preFix_20251230_185052__rep1 \
  --before_run_tag DEV_armG_mm_S5R0_before_rerun_preFix_20251230_185052__rep2 \
  --after_run_tag DEV_armG_mm_S5R2_after_postFix_20251230_185052__rep1 \
  --after_run_tag DEV_armG_mm_S5R2_after_postFix_20251230_185052__rep2
```

**참고**: 실제 실행 시에는 위의 run tag를 실제 생성된 run tag로 교체해야 합니다.

---

## 체크리스트

### Phase별 실행 전 확인
- [ ] `temp_selected_groups.txt` 파일이 존재하고 11개 그룹이 포함되어 있는지 확인
- [ ] Run tag 형식이 정확한지 확인 (S5R0/S5R1/S5R2, before_rerun/after_postFix, rep1/rep2)
- [ ] 모든 Phase에서 동일한 `temp_selected_groups.txt` 파일 사용

### 실행 후 확인
- [ ] 각 run_tag 디렉토리에 `stage1_struct__armG.jsonl` 파일이 11줄인지 확인
- [ ] 각 run_tag 디렉토리에 `s2_results__s1armG__s2armG.jsonl` 파일이 생성되었는지 확인
- [ ] Run tag가 계획대로 생성되었는지 확인

---

## 참고 문서

- `S5R_Execution_Commands_Template.md`: 전체 실행 명령어 템플릿
- `S5R_프롬프트_개선_실험_계획_및_레지스트리_개선_a84380c0.plan.md`: 전체 실험 계획


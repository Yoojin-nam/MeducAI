## Status / Version

- **Status**: Execution Plan (Current Status)
- **Version**: 1.0
- **Last Updated**: 2025-12-29
- **Purpose**: 현재 데이터 상태 기반 S5R 실험 실행 계획

---

## 현재 데이터 상태 (2025-12-29)

### Before_rerun (S5R0) 데이터

| Run Tag | S2 완료 | S5 Validation | 비고 |
|---------|---------|---------------|------|
| `DEV_armG_mm_S5R0_before_rerun_preFix_20251229_192216__rep1` | ✅ | ❌ | S5 validation 필요 |
| `DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep1` | ✅ | ✅ | 완료 |
| `DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep2` | ✅ | ❌ | S5 validation 필요 |
| `DEV_armG_mm_S5R0_before_rerun_preFix_20251229_203653__rep2` | ✅ | ✅ | 완료 |

**요약**:
- Before_rerun 데이터: 4개 run_tag (rep1: 2개, rep2: 2개)
- S5 validation 완료: 2개 (rep1: 1개, rep2: 1개)
- S5 validation 필요: 2개

### After (S5R2) 데이터

- **현재 상태**: 아직 생성되지 않음
- **필요 작업**: 프롬프트 개선 후 S1→S2→S5 실행

---

## 실행 계획 (단계별)

### Phase 1: Before_rerun 데이터 완성 (현재 단계)

#### Step 1.1: 누락된 S5 Validation 실행

**목표**: 모든 Before_rerun run_tag에 대해 S5 validation 완료

**실행 명령**:

```bash
# 누락된 run_tag 1: rep1
python3 3_Code/src/05_s5_validator.py \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag DEV_armG_mm_S5R0_before_rerun_preFix_20251229_192216__rep1 \
  --arm G

# 누락된 run_tag 2: rep2
python3 3_Code/src/05_s5_validator.py \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep2 \
  --arm G
```

**확인 방법**:
```bash
# 각 run_tag 디렉토리에 s5_validation__armG.jsonl 파일 생성 확인
ls -lh 2_Data/metadata/generated/DEV_armG_mm_S5R0_before_rerun_preFix_*/s5_validation__armG.jsonl
```

#### Step 1.2: S5 Report 생성 (선택사항, 디버깅용)

**목적**: 각 run_tag별 validation 결과를 사람이 읽을 수 있는 리포트로 생성

**실행 명령**:

```bash
# tools/s5/s5_report.py 사용
python3 3_Code/src/tools/s5/s5_report.py \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag DEV_armG_mm_S5R0_before_rerun_preFix_20251229_192216__rep1 \
  --arm G

python3 3_Code/src/tools/s5/s5_report.py \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep2 \
  --arm G
```

**출력 위치**: `2_Data/metadata/generated/{run_tag}/reports/s5_report__armG.md`

---

### Phase 2: After 데이터 생성 (프롬프트 개선 후)

#### Step 2.1: 프롬프트 개선 확인

**전제 조건**:
- S1/S2/S4 프롬프트가 개선되었는지 확인
- S5R2 validator prompt가 준비되었는지 확인

**확인 사항**:
- `0_Protocol/05_Pipeline_and_Execution/S5R_Prompt_Refinement_Development_Endpoint_Canonical.md` 참조
- 프롬프트 버전: S5R0 → S5R2

#### Step 2.2: After 데이터 생성 (S1→S2)

**Run Tag 형식**: `DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1` (+ `__rep2`)

**실행 명령** (rep1 예시):

```bash
# Run tag 생성
RUN_TAG_REP1="DEV_armG_mm_S5R2_after_postFix_$(date +%Y%m%d_%H%M%S)__rep1"
echo "Run tag: $RUN_TAG_REP1"

# S1 + S2 실행
python3 3_Code/src/01_generate_json.py \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag "$RUN_TAG_REP1" \
  --arm G \
  --mode S0 \
  --stage both \
  --sample 1
```

**rep2도 동일하게 실행** (독립적인 replicate)

#### Step 2.3: After 데이터 S5 Validation

**실행 명령**:

```bash
# rep1
python3 3_Code/src/05_s5_validator.py \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag "$RUN_TAG_REP1" \
  --arm G

# rep2
python3 3_Code/src/05_s5_validator.py \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --run_tag "$RUN_TAG_REP2" \
  --arm G
```

**중요**: After 데이터는 **S5R2 validator**로 평가해야 함 (Target 1 인과 주장을 위해)

---

### Phase 3: 비교 분석

#### Step 3.1: Before vs After 비교

**실행 명령**:

```bash
python3 3_Code/src/tools/s5/s5_compare_mm.py \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --arm G \
  --before_run_tags \
    DEV_armG_mm_S5R0_before_rerun_preFix_20251229_192216__rep1 \
    DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep1 \
    DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep2 \
    DEV_armG_mm_S5R0_before_rerun_preFix_20251229_203653__rep2 \
  --after_run_tags \
    <AFTER_REP1> \
    <AFTER_REP2>
```

**출력 위치**: `2_Data/metadata/generated/COMPARE__<before_tag0>__VS__<after_tag0>/`

**출력 파일**:
- `summary__mm.md`: 마크다운 리포트
- `paired_long__mm.csv`: paired long-form 데이터
- `group_level__mm.csv`: group-level 집계 데이터

---

## 체크리스트

### Before_rerun 완성
- [ ] `DEV_armG_mm_S5R0_before_rerun_preFix_20251229_192216__rep1` S5 validation 실행
- [ ] `DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep2` S5 validation 실행
- [ ] 모든 Before_rerun run_tag에 `s5_validation__armG.jsonl` 존재 확인

### After 데이터 생성
- [ ] 프롬프트 개선 완료 확인 (S5R2)
- [ ] After rep1 생성 (S1→S2)
- [ ] After rep2 생성 (S1→S2)
- [ ] After rep1 S5 validation 실행
- [ ] After rep2 S5 validation 실행

### 비교 분석
- [ ] Before/After 비교 스크립트 실행
- [ ] 결과 리포트 확인
- [ ] Expansion criteria 평가 (≥9/11 groups improve, median reduction ≥ 5pp)

---

## 주의사항

### 1. Judge Version 고정 (Target 1 인과 주장)

**중요**: Target 1 (Generation effect) 주장을 위해서는:
- Before와 After 생성물을 **동일한 S5 validator version**으로 평가해야 함
- 현재 계획: Before는 S5R0, After는 S5R2로 평가 예정
- **Cross-evaluation 필요**: After 생성물을 S5R0으로도 평가하여 Target 1 주장 가능

### 2. Replicate 처리

- Replicate는 독립 표본수를 늘리지 않음 (n은 여전히 group 수)
- 각 조건(Before/After)×group에 대해 replicate별 endpoint 계산 후 **평균(mean)** 사용
- 비교 분석 스크립트가 자동으로 처리함

### 3. Primary Endpoint

- **S2_any_issue_rate_per_group**: 한 group에서 S2 cards 중 `issue >= 1` 인 카드의 비율
- 이 endpoint가 개선되었는지가 주요 평가 기준

---

## 다음 단계 결정 기준

Phase 1 완료 후:
1. Before_rerun 데이터의 S5 validation 결과 확인
2. 주요 issue patterns 파악
3. 프롬프트 개선 방향 결정 (Phase 2로 진행)

Phase 2 완료 후:
1. Expansion criteria 평가:
   - Primary endpoint에서 **≥9/11 groups improve** (`After < Before`)
   - Primary endpoint의 **median absolute reduction ≥ 5 percentage points**
2. 기준 충족 시: HOLDOUT 확장 고려
3. 기준 미충족 시: 추가 프롬프트 개선 또는 실험 설계 재검토

---

## 참고 문서

- `0_Protocol/05_Pipeline_and_Execution/S5R_Experiment_Power_and_Significance_Plan.md`: 실험 설계 및 분석 계획
- `0_Protocol/05_Pipeline_and_Execution/S5_Prompt_Improvement_Quantitative_Evaluation_Plan.md`: 평가 계획 상세
- `0_Protocol/05_Pipeline_and_Execution/S5R_Prompt_Refinement_Development_Endpoint_Canonical.md`: 프롬프트 개선 가이드


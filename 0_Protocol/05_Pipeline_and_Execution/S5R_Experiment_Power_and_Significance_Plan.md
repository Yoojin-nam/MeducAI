## Status / Version

- **Status**: Canonical (prereg-ready)
- **Version**: 1.0
- **Frozen**: No (DEV 단계에서 업데이트 가능; HOLDOUT 시작 시 Yes로 전환)
- **Last Updated**: 2025-12-29

---

## Purpose

이 문서는 S5R 실험을 **논문 심사/리뷰 관점에서 방어 가능한 수준**으로 만들기 위한 **사전 규정(pre-registered-like)** 계획서이다.

핵심 목표:
- **인과 질문을 분리**한다(Generation vs Judge).
- **낮은 multiplicity**(Primary 1개 + Key secondary 2–3개)로 제한한다.
- **paired group_id** 단위에서 분석한다.
- **효과크기 + CI + 일관성(방향성)** 중심으로 보고한다(작은 n에서 p-value는 보조).

관련 문서:
- `0_Protocol/05_Pipeline_and_Execution/S5_Prompt_Improvement_Quantitative_Evaluation_Plan.md`
- `0_Protocol/05_Pipeline_and_Execution/S5_Prompt_Improvement_Hypothesis_and_Methods.md`
- `0_Protocol/05_Pipeline_and_Execution/S5_Version_Naming_S5R_Canonical.md`
- `0_Protocol/04_Step_Contracts/Step05_S5/S5_Validation_Schema_Canonical.md`

---

## Causal Targets (MUST be separated)

이 프로젝트에는 서로 다른 두 인과 질문이 있다. 둘을 섞어서 “품질이 향상되었다”고 주장하면 리뷰에서 반박된다.

### Target 1 — Generation prompt improvement effect (Content quality)

질문: “생성 프롬프트(S1/S2/S4)를 개선하면 생성물의 품질이 좋아지는가?”

인과 주장 요건:
- **평가자(validator/judge)는 고정(Fixed Judge)** 되어야 한다.
  - 즉, before/after 생성물을 **동일한 S5 validator prompt/version** 으로 평가한다.

### Target 2 — S5 validator prompt improvement effect (Judge behavior / detection)

질문: “S5 validator prompt(S5R0→S5R2)가 판단 기준/감지 행동에 어떤 변화를 만드는가?”

인과 주장 요건:
- **평가 대상 콘텐츠는 고정(Frozen Content)** 되어야 한다.
  - 즉, 동일한 텍스트/이미지 산출물에 대해 **S5R0 vs S5R2** 로 평가한다.

---

## Design (publication-grade minimal design)

### Unit of analysis

- 기본 분석 단위는 **paired `group_id`** 이다.
- 카드/이미지는 group 안에 중첩(nested)되므로, **group-level endpoint로 집계**한다.

### DEV vs HOLDOUT split (overfitting 방지; prereg 핵심)

- **DEV (pilot)**: 현재 11개 그룹
  - 목적: failure mode 파악, 프롬프트 수정, 파이프라인 안정화
  - 결과 해석: **탐색적** (confirmatory claim 금지)
- **HOLDOUT (confirmatory)**: 추가 그룹을 확보해 **n=30–40 paired groups** 목표
  - DEV에서 고정한 endpoint/test로 **동일 분석** (분석 계획 변경 금지)

### Cross-evaluation (권장; Target 1 vs Target 2 분리)

권장 최소 설계(실행 가능하면서 인과 분리 가능):
- **Target 1 (Generation effect)**: Before 생성물과 After 생성물을 **동일 judge version(고정 S5R)** 으로 평가
- **Target 2 (Judge drift; sensitivity/secondary)**: 동일 콘텐츠(고정 산출물)를 **S5R0 vs S5R2** 로 평가해 judge 변화량을 계량

---

## Endpoints (STRICT; low multiplicity)

모든 endpoint는 group_id별로 계산하며, 조건 간 비교는 paired로 수행한다.

### Primary endpoint (single; prereg 고정)

- **S2_any_issue_rate_per_group**
  - 정의: 한 group에서 S2 cards 중 `issue >= 1` 인 카드의 비율
  - 해석: “문제 있는 카드가 얼마나 줄었는가”를 가장 직관적으로 반영

### Key secondary endpoints (≤3)

1) **IMG_any_issue_rate_per_group**
   - 정의: 한 group에서 이미지 중 `issue >= 1` 인 이미지의 비율

2) **S2_issues_per_card_per_group**
   - 정의: 한 group에서 카드 1장당 평균 issue 개수

3) 아래 중 하나만 사전 지정 (둘 다 key secondary로 두지 않음)
   - **TA_bad_rate_per_group**: `% (technical_accuracy < 1.0)`
   - **Difficulty_bad_rate_per_group**: `% (difficulty == 0.0)`

### Targeted issue codes

- 원칙: per-code 검정은 multiplicity가 커서 **descriptive** 로 둔다.
- 옵션(하나만 허용): prespecified targeted code set에 대해
  - **targeted_issue_composite_per_group** = targeted code occurrences의 합(또는 rate)
  - 이 composite는 **secondary/descriptive** 로만 보고(새 primary 금지)

---

## Statistical Analysis Plan (Prereg)

### Estimand

각 endpoint의 효과는 아래의 paired difference로 정의한다.
- 각 group에 대해 `diff_i = After_i - Before_i`
- **Estimand(요약 효과)**: `median(diff_i)`

### Primary test

- **Wilcoxon signed-rank test (paired)**
- n이 작을 수 있으므로 p-value는 보조이며, 아래 보고 항목을 필수로 포함한다.

### Effect size and CI

- **Hodges–Lehmann estimator** (paired location shift) + 95% CI
- 구현 여건상 HL CI가 어려우면, paired differences에 대한 **bootstrap 95% CI** 사용

### Directionality / consistency (n이 작은 경우 필수)

- “개선 그룹 수 / 전체 그룹 수”를 명시
  - 개선의 기준: primary endpoint에서 `After < Before`
- 필요 시 **sign test** 결과를 보조로 제시(탐색적 지원)

### Multiplicity handling

- Primary 1개 + Key secondary ≤3개로 제한하여 correction 없이도 해석 가능하도록 설계
- Targeted issue codes는 per-code hypothesis test를 하지 않고 descriptive 또는 composite 하나로 제한

---

## Replicates (REQUIRED handling)

### What replicates do / do not buy

- Replicate는 독립 표본수를 늘리지 않는다(n은 여전히 group 수).
- 대신 생성/평가 변동성(특히 이미지)을 줄이고 **측정 안정성**을 제공한다.

### Aggregation rule (strict)

- 각 조건(Before/After)×group에 대해 replicate별 endpoint를 계산한 후,
  - **replicate 평균(mean)** 을 그 group의 endpoint로 사용한다.
- 안정성 보고:
  - group별 replicate **SD** 또는 **min–max** 를 표에 함께 제시한다.

### Minimum recommendation

- 각 조건당 **2 replicates** (rep1/rep2) 권장
- 비용 제약 시: 1 replicate + 아래 “judge-only noise study” 필수 수행

---

## Judge-only noise study (REQUIRED)

목적: judge의 확률적 변동(LLM/VLM sampling, tool drift)을 분리해 계량한다.

설계:
- 콘텐츠 고정(frozen outputs): 특정 run_tag 산출물을 고정 입력으로 사용
- 동일 judge 조건에서 S5 validator를 **≥5회** 반복 실행

보고(최소):
- `any_issue`의 flip rate (같은 항목이 issue→clean 또는 clean→issue로 바뀌는 비율)
- (가능하면) 간단한 일치도: kappa/ICC 또는 합의율

---

## n=11 (DEV) vs n=30–40 (HOLDOUT) guidance

### DEV (n=11)에서의 해석 원칙

- “유의하다/유의하지 않다” 결론보다 다음을 중심으로 보고한다:
  - 효과 방향(개선 그룹 비율)
  - 효과크기(중앙값 차이)
  - CI 폭(정밀도)
  - 일관성(몇 개 그룹이 동일 방향?)

### HOLDOUT (n=30–40)에서의 목적

- 동일 endpoint/test를 유지한 채, 더 안정적인 CI와 해석 가능한 p-value를 확보한다.

---

## Expansion criteria (Go/No-Go; prereg)

DEV(n=11) 결과로 HOLDOUT 확장 여부를 아래 기준으로 결정한다.

Expand if BOTH:
1) primary endpoint에서 **≥9/11 groups improve** (`After < Before`), AND
2) primary endpoint의 **median absolute reduction ≥ 5 percentage points**

확장 목표:
- HOLDOUT에서 **n=30–40 paired groups**
- 분석 계획(엔드포인트/테스트)은 변경하지 않는다.

---

## Reporting checklist (Methods/Results-ready)

- Comparator는 **contemporaneous** Before_rerun vs After를 기본으로 사용
- Judge version 고정 여부를 명시(Target 1 주장에 필수)
- Primary endpoint 1개를 명시하고, secondary ≤3개로 제한
- 각 endpoint에 대해:
  - Before/After 요약(중앙값/평균 등)
  - paired differences의 중앙값(HL)과 95% CI
  - Wilcoxon p-value(보조)
  - 개선 그룹 비율(방향성)

---

## Implementation artifacts (minimal)

### Run tags (canonical)

- Before_rerun (S5R0): `DEV_armG_mm_S5R0_before_rerun_preFix_YYYYMMDD_HHMMSS__rep1` (+ `__rep2`)
- After (S5R2): `DEV_armG_mm_S5R2_after_postFix_YYYYMMDD_HHMMSS__rep1` (+ `__rep2`)

### Scripts

- Generate: `3_Code/src/01_generate_json.py`
- Validate: `3_Code/src/05_s5_validator.py`
- Report: `3_Code/src/tools/s5/s5_report.py`
- Compare: `3_Code/src/tools/s5/s5_compare_mm.py`

### Minimal command template

```bash
# Validate + report (per run_tag)
python3 3_Code/src/05_s5_validator.py --base_dir /path/to/workspace/workspace/MeducAI --run_tag <RUN_TAG> --arm G
python3 -m tools.s5.s5_report    --base_dir /path/to/workspace/workspace/MeducAI --run_tag <RUN_TAG> --arm G

# Compare (paired; replicates averaged per group)
python3 -m tools.s5.s5_compare_mm \
  --base_dir /path/to/workspace/workspace/MeducAI \
  --arm G \
  --before_run_tags <BEFORE_REP1> <BEFORE_REP2> \
  --after_run_tags  <AFTER_REP1>  <AFTER_REP2>
```

산출물 위치:
- `2_Data/metadata/generated/COMPARE__<before_tag0>__VS__<after_tag0>/`

---

## Risks & mitigations

- **Judge circularity / overfitting**: DEV vs HOLDOUT 분리, HOLDOUT에서 confirmatory claim
- **Temporal drift**: contemporaneous before_rerun vs after
- **Stochasticity**: replicates + judge-only noise study
- **Multiplicity**: primary 1개 + secondary ≤3개, targeted codes descriptive/composite 하나


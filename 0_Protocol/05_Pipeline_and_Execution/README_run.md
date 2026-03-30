# README_RUN.md

**Last Updated:** 2025-12-20

## Purpose
This document is an **operation-oriented runbook** for MeducAI.
It is intended to be copied into a memo or used directly in terminal sessions during QA runs.

Scope:
- RUN_TAG management
- Full arm end-to-end execution (S0 / QA)
- S1/S2/S3/S4 단계별 실행 방법
- Logging & monitoring
- Git snapshot & reproducibility discipline

**Implementation Status:**
- ✅ S1/S2: 구현 완료 (2025-12-19)
- ✅ S3: 구현 완료 (2025-12-20)
- ✅ S4: 구현 완료 (2025-12-20)
- ✅ 6-Arm Full Pipeline: 구현 완료 (2025-12-20)

---

## 0. Assumptions

- Current working directory: **MeducAI project root**
- Python venv activated
- `.env` exists (provider keys, base path)
- Primary execution entrypoint: `3_Code/src/run_arm_full.py`

---

## 0.1 Overnight runs on macOS (Sleep vs Display Sleep)

Important distinction:
- **True macOS Sleep** (잠자기/뚜껑 닫힘): CPU stops → **pipelines cannot continue**.
- **Display sleep only** (화면만 꺼짐): OK.

Recommended (repo-provided) approach:
- **S3→S4 only (existing RUN_TAG)**:

```bash
bash 3_Code/Scripts/run_s3_s4_background.sh --run_tag "$RUN_TAG" --arm G
```

- **Full FINAL pipeline (S1→S5)**:

```bash
bash 3_Code/Scripts/run_final_background.sh
```

Both scripts:
- run inside **tmux** (safe to detach)
- use **`caffeinate`** to prevent system sleep while the job runs
- write logs to `2_Data/metadata/generated/$RUN_TAG/logs/`

---

## 1. RUN_TAG Management

### 1.1 Generate a new RUN_TAG (recommended)

```bash
RUN_TAG="S0_SMOKE_$(date +%Y%m%d_%H%M%S)"
echo $RUN_TAG
```

Use this for:
- Smoke tests
- New QA trials
- Any run that must be clearly separated

---

### 1.2 Fixed RUN_TAG (re-run / debug)

```bash
RUN_TAG="S0_QA_FIXED"
```

Use only when:
- Re-running the *same* experiment
- Debugging a failed arm

---

## 2. Full Arm End-to-End Execution

### 2.1 S1/S2 독립 실행 (권장, 2025-12-19 추가)

**Stage 1만 실행 (6 arm):**
```bash
for arm in A B C D E F; do
  python3 3_Code/src/01_generate_json.py \
    --base_dir . \
    --run_tag "$RUN_TAG" \
    --arm $arm \
    --mode S0 \
    --stage 1 \
    --sample 1
done
```

**Stage 2만 실행 (6 arm, S1 출력 필요):**
```bash
for arm in A B C D E F; do
  python3 3_Code/src/01_generate_json.py \
    --base_dir . \
    --run_tag "$RUN_TAG" \
    --arm $arm \
    --mode S0 \
    --stage 2 \
    --sample 1
done
```

**Stage 옵션:**
- `--stage 1`: S1만 실행
- `--stage 2`: S2만 실행 (기존 S1 출력 필요)
- `--stage both`: S1+S2 통합 실행 (기본값)

---

### 2.2 S3 Policy Resolver 실행 (2025-12-20 추가)

**S3 실행 (6 arm, S2 출력 필요):**
```bash
for arm in A B C D E F; do
  python3 3_Code/src/03_s3_policy_resolver.py \
    --base_dir . \
    --run_tag "$RUN_TAG" \
    --arm $arm
done
```

**출력 파일:**
- `2_Data/metadata/generated/$RUN_TAG/image_policy_manifest__arm{X}.jsonl`
- `2_Data/metadata/generated/$RUN_TAG/s3_image_spec__arm{X}.jsonl`

---

### 2.3 S4 Image Generator 실행 (2025-12-20 추가)

**S4 실행 (6 arm, S3 출력 필요):**
```bash
for arm in A B C D E F; do
  python3 3_Code/src/04_s4_image_generator.py \
    --base_dir . \
    --run_tag "$RUN_TAG" \
    --arm $arm
done
```

**Dry-run 모드 (이미지 생성 없이 테스트):**
```bash
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir . \
  --run_tag "$RUN_TAG" \
  --arm A \
  --dry_run
```

**출력 파일:**
- `2_Data/metadata/generated/$RUN_TAG/images/IMG__*.png`
- `2_Data/metadata/generated/$RUN_TAG/s4_image_manifest__arm{X}.jsonl`

**주의사항:**
- Gemini API 키 필요 (`GOOGLE_API_KEY` 환경 변수)
- Q1 이미지 생성 실패 시 FAIL-FAST
- 이미지 모델: `gemini-2.5-flash-image` (arm-independent)

---

### 2.4 6-Arm Full Pipeline 실행 (2025-12-20 추가)

**전체 파이프라인 (S1→S2→S3→S4) 자동 실행:**
```bash
python3 3_Code/Scripts/run_6arm_s1_s2_full.py \
  --run_tag "$RUN_TAG" \
  --mode S0
```

**출력:**
- 마크다운 리포트 자동 생성: `6ARM_S1_S2_RESULTS_{RUN_TAG}.md`
- 각 단계별 성공/실패 상태 포함

---

### 2.5 S0 Smoke Test (ALL arms, parallel) - Legacy

```bash
python3 3_Code/src/run_arm_full.py \
  --base_dir . \
  --provider gemini \
  --run_tag_base "$RUN_TAG" \
  --arms A,B,C,D,E,F \
  --parallel \
  --max_workers 2 \
  --sample 1 \
  --target_total 12
```

Meaning:
- `sample 1` : minimal Step01 payload
- `target_total 12` : fixed S0 payload
- `parallel` : arm-level parallelism
- `max_workers 2` : API-quota-safe default

---

### 2.6 Single Arm Debug Run

```bash
python3 3_Code/src/run_arm_full.py \
  --base_dir . \
  --provider gemini \
  --run_tag_base "$RUN_TAG" \
  --arms E \
  --sample 1 \
  --target_total 12
```

---

### 2.7 Resume Failed Arm (Step05 continuation)

```bash
python3 3_Code/src/run_arm_full.py \
  --base_dir . \
  --provider gemini \
  --run_tag_base "$RUN_TAG" \
  --arms C \
  --resume
```

---

### 2.8 Option C (S5 → Repair(S2-only) → Postrepair S5 → S6 Gate → Export) — One-group Smoke

Prereqs (must already exist under `2_Data/metadata/generated/$RUN_TAG/`):
- Baseline S1: `stage1_struct__arm{S1_ARM}.jsonl`
- Baseline S2: `s2_results__s1arm{S1_ARM}__s2arm{ARM}.jsonl`
- Baseline S5: `s5_validation__arm{ARM}.jsonl`

If baseline S5 is missing, run the baseline validator first:

```bash
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag "$RUN_TAG" \
  --arm "$ARM"
```

**One-group E2E smoke (recommended)** — runs orchestrator + creates a synthetic `Ratings.csv` (ACCEPT) + gate + PDF + Anki:

```bash
RUN_TAG="YOUR_RUN_TAG"
GROUP_ID="grp_XXXXXXXXXX"
ARM="A"
S1_ARM="A"

bash 3_Code/Scripts/smoke_optionc_one_group_e2e.sh
```

**Manual (step-by-step)**

1) Option C orchestrator (creates `__repaired` S2 + `__postrepair` S5; never overwrites baseline):

```bash
python3 3_Code/src/05c_option_c_orchestrator.py \
  --base_dir . \
  --run_tag "$RUN_TAG" \
  --arm "$ARM" \
  --s1_arm "$S1_ARM" \
  --only_group_id "$GROUP_ID" \
  --threshold 70.0 \
  --entity_filter_mode from_plan
```

2) S6 export gate → `s6_export_manifest__arm{ARM}.json` (promotion decision per group)

Inputs:
- `Ratings.csv` export from AppSheet (must contain `card_uid` and `accept_ai_correction`)
- `s5_validation__arm{ARM}__postrepair.jsonl`

```bash
RATINGS_CSV="PATH/TO/Ratings.csv"
python3 3_Code/src/06_s6_export_gate.py \
  --base_dir . \
  --run_tag "$RUN_TAG" \
  --arm "$ARM" \
  --ratings_csv "$RATINGS_CSV"
```

3) Export with manifest (baseline vs repaired per group)

```bash
MANIFEST="2_Data/metadata/generated/$RUN_TAG/s6_export_manifest__arm${ARM}.json"

# NOTE: PDF/Anki exporters are NOT quality gates. They are deterministic export tools.
# - Final export: keep strict defaults (omit --allow_missing_images). If this fails, fix upstream (typically S4).
# - Preview/debug only: add --allow_missing_images to insert placeholders / skip missing-image cards.

# PDF (single group) — strict (recommended for final distribution)
python3 3_Code/src/07_build_set_pdf.py \
  --base_dir . \
  --run_tag "$RUN_TAG" \
  --arm "$ARM" \
  --s1_arm "$S1_ARM" \
  --group_id "$GROUP_ID" \
  --export_manifest_path "$MANIFEST"

# Anki (run_tag-level; uses manifest per group) — strict (recommended for final distribution)
python3 3_Code/src/07_export_anki_deck.py \
  --base_dir . \
  --run_tag "$RUN_TAG" \
  --arm "$ARM" \
  --s1_arm "$S1_ARM" \
  --export_manifest_path "$MANIFEST"

# Preview/debug variants (NOT for final distribution)
python3 3_Code/src/07_build_set_pdf.py --base_dir . --run_tag "$RUN_TAG" --arm "$ARM" --s1_arm "$S1_ARM" --group_id "$GROUP_ID" --allow_missing_images --export_manifest_path "$MANIFEST"
python3 3_Code/src/07_export_anki_deck.py --base_dir . --run_tag "$RUN_TAG" --arm "$ARM" --s1_arm "$S1_ARM" --allow_missing_images --export_manifest_path "$MANIFEST"
```

## 3. Log Inspection

### 3.1 Log directory

```bash
ls logs/$RUN_TAG
```

### 3.2 Real-time log tail (per arm)

```bash
tail -f logs/$RUN_TAG/${RUN_TAG}__armA.log
```

### 3.3 Find failed arms quickly

```bash
grep -R "FAILED" logs/$RUN_TAG
```

---

## 4. Output Verification

### 4.1 Generated metadata

```bash
ls 2_Data/metadata/generated | grep "$RUN_TAG"
```

### 4.2 Arm-specific Anki CSV

```bash
ls 2_Data/metadata/generated/anki_cards_*${RUN_TAG}*__arm*.csv
```

---

## 5. Process Monitoring

```bash
ps aux | grep run_arm_full
```

---

## 6. Git Snapshot & Reproducibility (MANDATORY)

### 6.1 Check status

```bash
git status
```

### 6.2 Commit

```bash
git add -A
git commit -m "S0 QA run completed ($RUN_TAG)"
```

### 6.3 Tag (strongly recommended)

```bash
git tag S0_QA_$RUN_TAG
git tag
```

Rule:
- **RUN_TAG = experiment unit**
- **Git tag = code version unit**

Never mix them.

---

## 7. Safe Execution Discipline

- ❌ Do NOT modify code while a run is active
- ✅ Let all arms finish (even failed ones)
- ✅ Inspect logs first
- ✅ Commit + tag before any fix
- ✅ Use a *new* RUN_TAG after code changes

---

## 8. Minimal One-Line Cheats

```bash
RUN_TAG="S0_SMOKE_$(date +%Y%m%d_%H%M%S)"
python3 3_Code/src/run_arm_full.py --base_dir . --provider gemini --run_tag_base "$RUN_TAG" --arms A,B,C,D,E,F --parallel --max_workers 2 --sample 1 --target_total 12
git add -A && git commit -m "S0 QA run ($RUN_TAG)" && git tag S0_QA_$RUN_TAG
```

---

## Status

This file is intended to be **operational**, not descriptive.
If execution behavior changes, update this document immediately.


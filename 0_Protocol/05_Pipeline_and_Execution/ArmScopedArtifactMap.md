# Arm-Scoped S1/S2 Artifact Map (RUN_TAG folder)

**Status:** working note (P0-2 tracker)

Each invocation of `3_Code/src/01_generate_json.py` now writes per-arm artifacts directly under `2_Data/metadata/generated/<RUN_TAG>/`. This eliminates the previous overwrite hazard from sharing `stage1_struct.jsonl` across arms.

| Artifact | Purpose | Canonical filename |
| --- | --- | --- |
| Stage1 raw records | Full Step01 record stream (one line per group) | `stage1_raw__armX.jsonl` |
| Stage1 struct | S1 Gate / SSOT input | `stage1_struct__armX.jsonl` |
| Stage2 results | Entity-level cards (`S2_RESULTS_v3.1`) | `s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl` (new)<br>`s2_results__armX.jsonl` (legacy, backward compatible) |
| Image spec (reserved) | Produced by upcoming S3A CLI | `image_spec__armX.jsonl` |

**Example CLI (Arm B, one group sample)**

**S1 + S2 통합 실행 (기본값):**
```bash
python 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag RUN_20251218 \
  --arm B \
  --mode S0 \
  --sample 1
  # --stage both (기본값)
```

**S1만 실행:**
```bash
python 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag RUN_20251218 \
  --arm B \
  --mode S0 \
  --stage 1 \
  --sample 1
```

**S2만 실행 (S1 출력 필요):**
```bash
python 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag RUN_20251218 \
  --arm B \
  --mode S0 \
  --stage 2 \
  --sample 1
```

**S2 실행 (다른 S1 arm 사용):**
```bash
python 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag RUN_20251218 \
  --arm B \
  --s1_arm A \
  --mode S0 \
  --stage 2 \
  --sample 1
# 생성: s2_results__s1armA__s2armB.jsonl
```

**Note (2025-12-23):**
- S2 출력 파일명이 `s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl` 형식으로 변경됨
- S1과 S2가 같은 arm인 경우에도 새 형식 사용 (하위 호환성 유지)
- Legacy 형식 (`s2_results__armX.jsonl`)은 S0 결과와의 호환성을 위해 계속 지원
- `--s1_arm` 옵션으로 S1 출력을 읽을 arm을 명시적으로 지정 가능 (기본값: `--arm`)

The validator and automation scripts (`validate_stage1_struct.py`, `run_s0_smoke_6arm.py`, `run_s1_stress_3x.sh`) now resolve the per-arm filenames above, while still honouring legacy fallback paths if needed.

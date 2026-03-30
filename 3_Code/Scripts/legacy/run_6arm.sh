#!/usr/bin/env bash
set -euo pipefail

# MeducAI project root = current working directory (you said you will run from MeducAI terminal)
ROOT_DIR="$(pwd)"

RUNNER="$ROOT_DIR/3_Code/src/run_s0_smoketest_6arm.py"

RUN_TAG_BASE="${1:-S0_QA}"
SAMPLE="${2:-2}"
EXPORT_ANKI="${3:-0}"   # 1이면 export_anki 포함, 0이면 export 생략

if [[ ! -f "$RUNNER" ]]; then
  echo "[FATAL] Runner not found: $RUNNER"
  echo "Create it at: 3_Code/src/run_s0_smoketest_6arm.py"
  exit 2
fi

if [[ "$EXPORT_ANKI" == "1" ]]; then
  python3 "$RUNNER" --base_dir "$ROOT_DIR" --run_tag_base "$RUN_TAG_BASE" --sample "$SAMPLE" --export_anki
else
  python3 "$RUNNER" --base_dir "$ROOT_DIR" --run_tag_base "$RUN_TAG_BASE" --sample "$SAMPLE"
fi


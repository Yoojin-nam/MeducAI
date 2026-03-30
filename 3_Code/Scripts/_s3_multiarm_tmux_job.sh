#!/bin/bash
# Internal tmux job runner for S3-only across multiple arms.
# Expects env vars:
#   RUN_TAG, ARMS_CSV, BASE_DIR, LOG_DIR, S1_ARM (optional)
#
# Writes per-arm logs:
#   $LOG_DIR/S3_arm<ARM>.log

set -euo pipefail

: "${RUN_TAG:?RUN_TAG is required}"
: "${ARMS_CSV:?ARMS_CSV is required (e.g., A,B,C)}"
: "${BASE_DIR:?BASE_DIR is required}"
: "${LOG_DIR:?LOG_DIR is required}"

S1_ARM="${S1_ARM:-}"

cd "$BASE_DIR"

echo "========================================"
echo "[S3 multi-arm] Started at $(date)"
echo "Run tag: $RUN_TAG"
echo "Arms: $ARMS_CSV"
if [[ -n "$S1_ARM" ]]; then
  echo "S1 arm override: $S1_ARM"
fi
echo "Logs: $LOG_DIR"
echo "========================================"
echo ""

IFS=',' read -r -a ARMS <<< "$ARMS_CSV"
if [[ ${#ARMS[@]} -eq 0 ]]; then
  echo "[S3 multi-arm] No arms provided"
  exit 1
fi

for ARM in "${ARMS[@]}"; do
  ARM="$(echo "$ARM" | tr '[:lower:]' '[:upper:]' | xargs)"
  if [[ -z "$ARM" ]]; then
    continue
  fi

  echo "----------------------------------------"
  echo "[S3 arm=$ARM] Started at $(date)"
  echo "----------------------------------------"

  S1_ARM_ARGS=()
  if [[ -n "$S1_ARM" ]]; then
    S1_ARM_ARGS=(--s1_arm "$S1_ARM")
  fi

  python3 -u 3_Code/src/03_s3_policy_resolver.py \
    --base_dir . \
    --run_tag "$RUN_TAG" \
    --arm "$ARM" \
    "${S1_ARM_ARGS[@]}" 2>&1 | tee "$LOG_DIR/S3_arm${ARM}.log"

  echo "[S3 arm=$ARM] Completed at $(date)"
  echo ""
done

echo "========================================"
echo "[S3 multi-arm] Done at $(date)"
echo "Output dir: 2_Data/metadata/generated/$RUN_TAG"
echo "========================================"

















#!/bin/bash
# Internal tmux job runner for S3 -> S4.
# Expects env vars:
#   RUN_TAG, ARM, BASE_DIR, LOG_DIR, RESUME_S4

set -euo pipefail

: "${RUN_TAG:?RUN_TAG is required}"
: "${ARM:?ARM is required}"
: "${BASE_DIR:?BASE_DIR is required}"
: "${LOG_DIR:?LOG_DIR is required}"

cd "$BASE_DIR"

echo "========================================"
echo "[S3/S4] Started at $(date)"
echo "Run tag: $RUN_TAG"
echo "Arm: $ARM"
echo "Logs: $LOG_DIR"
echo "========================================"
echo ""

if [[ "${SKIP_S3:-0}" == "1" ]]; then
  echo "----------------------------------------"
  echo "[S3] Skipped (SKIP_S3=1)"
  echo "----------------------------------------"
  echo ""
else
  echo "----------------------------------------"
  echo "[S3] Started at $(date)"
  echo "----------------------------------------"
  python3 -u 3_Code/src/03_s3_policy_resolver.py \
    --base_dir . \
    --run_tag "$RUN_TAG" \
    --arm "$ARM" 2>&1 | tee "$LOG_DIR/S3.log"
  echo "[S3] Completed at $(date)"
  echo ""
fi

S4_RESUME_FLAG=()
if [[ "${RESUME_S4:-0}" == "1" ]]; then
  S4_RESUME_FLAG=(--resume)
fi

echo "----------------------------------------"
echo "[S4] Started at $(date) (resume=${RESUME_S4:-0})"
echo "----------------------------------------"
python3 -u 3_Code/src/04_s4_image_generator.py \
  --base_dir . \
  --run_tag "$RUN_TAG" \
  --arm "$ARM" \
  "${S4_RESUME_FLAG[@]}" 2>&1 | tee "$LOG_DIR/S4.log"
echo "[S4] Completed at $(date)"
echo ""

echo "========================================"
echo "[S3/S4] Done at $(date)"
echo "Output dir: 2_Data/metadata/generated/$RUN_TAG"
echo "========================================"



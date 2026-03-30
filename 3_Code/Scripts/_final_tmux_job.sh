#!/bin/bash
# Internal tmux job runner for FINAL pipeline (S1/S2 -> S3 -> S4 -> S5).
# Expects env vars:
#   RUN_TAG, ARM, BASE_DIR, LOG_DIR, PROVIDER

set -euo pipefail

: "${RUN_TAG:?RUN_TAG is required}"
: "${ARM:?ARM is required}"
: "${BASE_DIR:?BASE_DIR is required}"
: "${LOG_DIR:?LOG_DIR is required}"

PROVIDER="${PROVIDER:-gemini}"

cd "$BASE_DIR"

echo "========================================"
echo "[FINAL] Pipeline Started at $(date)"
echo "Run tag: $RUN_TAG"
echo "Arm: $ARM"
echo "Provider: $PROVIDER"
echo "Logs: $LOG_DIR"
echo "========================================"
echo ""

echo "----------------------------------------"
echo "[S1/S2] Started at $(date)"
echo "----------------------------------------"
python3 -u 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG" \
  --arm "$ARM" \
  --mode FINAL \
  --stage both \
  --provider "$PROVIDER" 2>&1 | tee "$LOG_DIR/S1_S2.log"
echo "[S1/S2] Completed at $(date)"
echo ""

echo "----------------------------------------"
echo "[S3] Started at $(date)"
echo "----------------------------------------"
python3 -u 3_Code/src/03_s3_policy_resolver.py \
  --base_dir . \
  --run_tag "$RUN_TAG" \
  --arm "$ARM" 2>&1 | tee "$LOG_DIR/S3.log"
echo "[S3] Completed at $(date)"
echo ""

echo "----------------------------------------"
echo "[S4] Started at $(date)"
echo "----------------------------------------"
python3 -u 3_Code/src/04_s4_image_generator.py \
  --base_dir . \
  --run_tag "$RUN_TAG" \
  --arm "$ARM" 2>&1 | tee "$LOG_DIR/S4.log"
echo "[S4] Completed at $(date)"
echo ""

echo "----------------------------------------"
echo "[S5] Started at $(date)"
echo "----------------------------------------"
python3 -u 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag "$RUN_TAG" \
  --arm "$ARM" 2>&1 | tee "$LOG_DIR/S5.log"
echo "[S5] Completed at $(date)"
echo ""

echo "========================================"
echo "[FINAL] Pipeline completed at $(date)"
echo "Run tag: $RUN_TAG"
echo "Output: 2_Data/metadata/generated/$RUN_TAG"
echo "========================================"



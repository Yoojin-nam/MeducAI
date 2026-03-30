#!/usr/bin/env bash
set -euo pipefail

# -----------------------------
# Config
# -----------------------------
BASE_DIR="."
MODE="S0"
SAMPLE="1"
ARMS=("armA" "armB" "armC" "armD" "armE" "armF")

export S0_FIXED_PAYLOAD_CARDS="${S0_FIXED_PAYLOAD_CARDS:-12}"

RUN_TAG="${RUN_TAG:-S0_6ARM_FIXED12_$(date +%Y%m%d_%H%M%S)}"
OUT_DIR="2_Data/metadata/generated/${RUN_TAG}"

echo "=================================================="
echo "[S0 6-ARM SMOKE] RUN_TAG=${RUN_TAG}"
echo "[Config] S0_FIXED_PAYLOAD_CARDS=${S0_FIXED_PAYLOAD_CARDS} | MODE=${MODE} | SAMPLE=${SAMPLE}"
echo "=================================================="

# -----------------------------
# Helpers
# -----------------------------
fail() {
  echo
  echo "FAIL: $1"
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing command: $1"
}

check_output_file_exists() {
  local arm="$1"
  local out
  out=$(ls -t "${OUT_DIR}"/output_*__"${arm}"*.jsonl 2>/dev/null | head -n 1 || true)
  [[ -n "${out}" ]] || fail "[${arm}] output file not found under ${OUT_DIR}"
  echo "${out}"
}

validate_output() {
  local arm="$1"
  local out="$2"

  echo "---- [${arm}] VALIDATION: ${out}"

  # 1) non-empty
  test -s "${out}" && echo "PASS: non-empty" || fail "[${arm}] empty output"

  # 2) JSON valid (first line)
  head -n 1 "${out}" | jq . >/dev/null && echo "PASS: JSON valid" || fail "[${arm}] invalid JSON"

  # 3) S0: entity 1개
  local n_entities
  n_entities=$(head -n 1 "${out}" | jq '.curriculum_content.entities | length')
  [[ "${n_entities}" == "1" ]] && echo "PASS: single entity" || fail "[${arm}] entity count=${n_entities} (expected 1)"

  # 4) S0: exact 12 cards
  local n_cards
  n_cards=$(head -n 1 "${out}" | jq '.curriculum_content.entities[0].anki_cards | length')
  [[ "${n_cards}" == "${S0_FIXED_PAYLOAD_CARDS}" ]] && echo "PASS: exact ${S0_FIXED_PAYLOAD_CARDS} cards" \
    || fail "[${arm}] card count=${n_cards} (expected ${S0_FIXED_PAYLOAD_CARDS})"

  # 5) Forbidden keys
  if grep -nE 'row_image_|importance_score' "${out}" >/dev/null 2>&1; then
    grep -nE 'row_image_|importance_score' "${out}" | head -n 20
    fail "[${arm}] forbidden keys detected (row_image_* or importance_score)"
  else
    echo "PASS: no forbidden keys"
  fi
}

# -----------------------------
# Pre-flight checks
# -----------------------------
require_cmd python3
require_cmd jq
mkdir -p "${OUT_DIR}"

# -----------------------------
# Run arms
# -----------------------------
declare -a SUMMARY=()

for arm in "${ARMS[@]}"; do
  echo
  echo "=================================================="
  echo "[RUN] ${arm}"
  echo "=================================================="

  python3 3_Code/src/01_generate_json.py \
    --base_dir "${BASE_DIR}" \
    --run_tag "${RUN_TAG}" \
    --mode "${MODE}" \
    --arm "${arm}" \
    --sample "${SAMPLE}"

  out=$(check_output_file_exists "${arm}")
  validate_output "${arm}" "${out}"

  SUMMARY+=("${arm}:PASS")
done

echo
echo "=================================================="
echo "[RESULT] ALL ARMS PASSED"
echo "RUN_TAG=${RUN_TAG}"
echo "Outputs: ${OUT_DIR}"
echo "Summary:"
printf ' - %s\n' "${SUMMARY[@]}"
echo "=================================================="

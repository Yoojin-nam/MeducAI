#!/usr/bin/env bash
set -uo pipefail

# ==============================
# Preflight: S2 N-sweep stability test (minimal)
# - Runs N in {1,3,5,8,12} for the SAME (mode, arm, group, entity)
# - Captures stdout/stderr logs per N
# - Records PASS/FAIL and failure type heuristics into a CSV
# - Does NOT require any code changes
# ==============================

# ---- User-editable knobs (minimal) ----
RUN_TAG_BASE="${RUN_TAG_BASE:-PREFLIGHT_NSweep_$(date +%Y%m%d_%H%M%S)}"
MODE="${MODE:-S0}"                 # or whatever canonical mode you use for the baseline 1×12 test
ARM="${ARM:-A}"                    # arm identifier
GROUP_ID="${GROUP_ID:-0}"          # set to a real group id
ENTITY_KEY="${ENTITY_KEY:-ENTITY_001}"  # set to a deterministic entity key/id/name used by your runner
N_LIST="${N_LIST:-1 3 5 8 12}"

# Output root (keep it inside 2_Data so it is gitignored and consistent with your structure)
OUT_ROOT="${OUT_ROOT:-2_Data/04_QA_Analysis/preflight_s2_nsweep/${RUN_TAG_BASE}}"

mkdir -p "${OUT_ROOT}/logs" "${OUT_ROOT}/outputs"

RESULTS_CSV="${OUT_ROOT}/nsweep_results.csv"
echo "timestamp,run_tag,mode,arm,group_id,entity_key,N,status,fail_hint,log_path,output_path" > "${RESULTS_CSV}"

# ---- Define the one true command to run S2 for ONE entity with EXACT N cards ----
# You MUST edit this S2_CMD line to match your project CLI.
#
# Requirements:
# - Accepts: run_tag, mode, arm, group_id, entity_key, and exact N
# - Produces a parseable output (json/jsonl) or at least a deterministic output file per run_tag
#
# Example placeholder (EDIT ME):
S2_CMD=(
  python 3_Code/src/02_generate_cards.py
  --run_tag "__RUN_TAG__"
  --mode "__MODE__"
  --arm "__ARM__"
  --group_id "__GROUP_ID__"
  --entity_key "__ENTITY_KEY__"
  --cards_for_entity_exact "__N__"
)

# ------------------------------
# Helper: replace placeholders in the S2_CMD array
# ------------------------------
build_cmd() {
  local run_tag="$1"
  local mode="$2"
  local arm="$3"
  local group_id="$4"
  local entity_key="$5"
  local n="$6"

  local cmd=()
  for token in "${S2_CMD[@]}"; do
    token="${token//__RUN_TAG__/${run_tag}}"
    token="${token//__MODE__/${mode}}"
    token="${token//__ARM__/${arm}}"
    token="${token//__GROUP_ID__/${group_id}}"
    token="${token//__ENTITY_KEY__/${entity_key}}"
    token="${token//__N__/${n}}"
    cmd+=("${token}")
  done
  echo "${cmd[@]}"
}

# ------------------------------
# Heuristic fail hint extraction from log
# ------------------------------
fail_hint_from_log() {
  local log="$1"
  if grep -qiE "JSONDecodeError|Expecting value|Unterminated string|parse|parsing|Invalid JSON" "$log"; then
    echo "parse_error"
  elif grep -qiE "len|length|exactly|expected|mismatch|card.*count|count.*card" "$log"; then
    echo "len_mismatch"
  elif grep -qiE "forbidden|not allowed|disallowed|schema|validation" "$log"; then
    echo "schema_or_forbidden"
  elif grep -qiE "timeout|timed out|rate limit|429|quota" "$log"; then
    echo "timeout_or_ratelimit"
  elif grep -qiE "Traceback" "$log"; then
    echo "runtime_exception"
  else
    echo "unknown"
  fi
}

# ------------------------------
# Main loop
# ------------------------------
for N in ${N_LIST}; do
  TS="$(date +%Y-%m-%dT%H:%M:%S%z)"
  RUN_TAG="${RUN_TAG_BASE}_N${N}"
  LOG_PATH="${OUT_ROOT}/logs/${RUN_TAG}.log"
  OUTPUT_PATH="${OUT_ROOT}/outputs/${RUN_TAG}"  # directory or file prefix; depends on your runner

  mkdir -p "${OUTPUT_PATH}"

  echo "============================================================" | tee -a "${LOG_PATH}"
  echo "[${TS}] RUN N=${N} run_tag=${RUN_TAG} mode=${MODE} arm=${ARM} group_id=${GROUP_ID} entity=${ENTITY_KEY}" | tee -a "${LOG_PATH}"
  echo "OUT=${OUTPUT_PATH}" | tee -a "${LOG_PATH}"

  CMD_STR="$(build_cmd "${RUN_TAG}" "${MODE}" "${ARM}" "${GROUP_ID}" "${ENTITY_KEY}" "${N}")"

  # Run: never stop the sweep on failure
  set +e
  eval "${CMD_STR}" >> "${LOG_PATH}" 2>&1
  EXIT_CODE=$?
  set -e

  if [[ ${EXIT_CODE} -eq 0 ]]; then
    STATUS="PASS"
    FAIL_HINT=""
  else
    STATUS="FAIL"
    FAIL_HINT="$(fail_hint_from_log "${LOG_PATH}")"
  fi

  echo "${TS},${RUN_TAG},${MODE},${ARM},${GROUP_ID},${ENTITY_KEY},${N},${STATUS},${FAIL_HINT},${LOG_PATH},${OUTPUT_PATH}" >> "${RESULTS_CSV}"

  echo "[DONE] N=${N} status=${STATUS} exit_code=${EXIT_CODE} hint=${FAIL_HINT}" | tee -a "${LOG_PATH}"
done

echo "============================================================"
echo "N-sweep completed."
echo "Results CSV: ${RESULTS_CSV}"
echo "Logs:        ${OUT_ROOT}/logs/"
echo "Outputs:     ${OUT_ROOT}/outputs/"
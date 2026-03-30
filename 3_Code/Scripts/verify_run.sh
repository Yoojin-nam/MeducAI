#!/usr/bin/env bash
set -euo pipefail

# verify_run.sh
# Usage:
#   ./verify_run.sh RUN_TAG
#   ./verify_run.sh RUN_TAG --arm A
#   ./verify_run.sh RUN_TAG --provider gemini
#   ./verify_run.sh RUN_TAG --mode S0
#
# Notes:
# - Expects outputs under: 2_Data/metadata/generated/${RUN_TAG}/
# - Validates JSONL, required top-level keys, and runtime logging fields.

RUN_TAG="${1:-}"
shift || true

ARM_FILTER=""
PROVIDER_FILTER=""
MODE_FILTER=""
STRICT_OPTION_B=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --arm)
      ARM_FILTER="${2:-}"; shift 2;;
    --provider)
      PROVIDER_FILTER="${2:-}"; shift 2;;
    --mode)
      MODE_FILTER="${2:-}"; shift 2;;
    --strict-option-b)
      STRICT_OPTION_B=1; shift 1;;
    -h|--help)
      sed -n '1,120p' "$0"; exit 0;;
    *)
      echo "Unknown arg: $1" >&2
      exit 2;;
  esac
done

if [[ -z "${RUN_TAG}" ]]; then
  echo "Usage: $0 RUN_TAG [--arm A] [--provider gemini] [--mode S0] [--strict-option-b]" >&2
  exit 2
fi

ROOT="2_Data/metadata/generated/${RUN_TAG}"

if [[ ! -d "${ROOT}" ]]; then
  echo "FAIL: run dir missing: ${ROOT}" >&2
  exit 1
fi

# Try to find output jsonl files (newest first)
mapfile -t OUTS < <(ls -t "${ROOT}"/output_*__arm*.jsonl 2>/dev/null || true)

if [[ ${#OUTS[@]} -eq 0 ]]; then
  # fallback: any jsonl in root
  mapfile -t OUTS < <(ls -t "${ROOT}"/*.jsonl 2>/dev/null || true)
fi

if [[ ${#OUTS[@]} -eq 0 ]]; then
  echo "FAIL: no output jsonl found under ${ROOT}" >&2
  exit 1
fi

echo "[INFO] Found ${#OUTS[@]} output file(s) under ${ROOT}"

JQ_FILTER='
  # Core structure
  (.metadata | type=="object") and
  (.metadata.id | type=="string" and length>0) and
  (.source_info | type=="object") and
  (.source_info.group_path | type=="string" and length>0) and
  (.curriculum_content | type=="object") and
  (.curriculum_content.visual_type | type=="string" and length>0) and
  (.curriculum_content.master_table | type=="string" and length>0) and
  (.curriculum_content.table_infographic.prompt_en | type=="string" and length>0) and

  # Runtime logging (policy)
  (.metadata.runtime | type=="object") and
  (.metadata.runtime.run_tag | type=="string" and length>0) and
  (.metadata.runtime.mode | type=="string" and length>0) and
  (.metadata.runtime.arm | type=="string" and length>0) and
  (.metadata.runtime.provider | type=="string" and length>0) and
  (.metadata.runtime.model_stage1 | type=="string" and length>0) and
  (.metadata.runtime.model_stage2 | type=="string" and length>0) and

  # Thinking/RAG flags must exist as booleans
  (.metadata.runtime.thinking_enabled | type=="boolean") and
  (.metadata.runtime.rag_enabled | type=="boolean") and

  # RAG/Thinking detail fields must exist (allow null where provider does not report)
  (.metadata.runtime.thinking_budget | (type=="string" or type=="number" or .==null)) and
  (.metadata.runtime.rag_mode | (type=="string" or .==null)) and
  (.metadata.runtime.rag_queries_count | (type=="number" or .==null)) and
  (.metadata.runtime.rag_sources_count | (type=="number" or .==null)) and

  # Latency must exist (allow null only if a stage was explicitly skipped; normally should be number)
  (.metadata.runtime.latency_sec_stage1 | (type=="number" or .==null)) and
  (.metadata.runtime.latency_sec_stage2 | (type=="number" or .==null)) and

  # Token counters (best-effort; allow null)
  (.metadata.runtime.input_tokens_stage1 | (type=="number" or .==null)) and
  (.metadata.runtime.output_tokens_stage1 | (type=="number" or .==null)) and
  (.metadata.runtime.input_tokens_stage2 | (type=="number" or .==null)) and
  (.metadata.runtime.output_tokens_stage2 | (type=="number" or .==null))
'

# Optional filters
if [[ -n "${ARM_FILTER}" ]]; then
  JQ_FILTER="(${JQ_FILTER}) and (.metadata.runtime.arm==\"${ARM_FILTER}\")"
fi
if [[ -n "${PROVIDER_FILTER}" ]]; then
  JQ_FILTER="(${JQ_FILTER}) and (.metadata.runtime.provider==\"${PROVIDER_FILTER}\")"
fi
if [[ -n "${MODE_FILTER}" ]]; then
  JQ_FILTER="(${JQ_FILTER}) and (.metadata.runtime.mode==\"${MODE_FILTER}\")"
fi

FAILS=0
PASS=0

for OUT in "${OUTS[@]}"; do
  echo "----"
  echo "[FILE] ${OUT}"
  if [[ ! -s "${OUT}" ]]; then
    echo "FAIL: empty or missing file" >&2
    FAILS=$((FAILS+1))
    continue
  fi

  # Validate JSON syntax for every line
  if ! jq -e . "${OUT}" >/dev/null 2>&1; then
    echo "FAIL: invalid JSONL (jq parse failed)" >&2
    FAILS=$((FAILS+1))
    continue
  fi

  # Enforce required schema per record
  if ! jq -e "${JQ_FILTER}" "${OUT}" >/dev/null; then
    echo "FAIL: required fields missing or invalid (see policy / runtime logging contract)" >&2
    # show a compact diff-like view for the first record to help debugging
    echo "[DEBUG] First record keys:"
    head -n 1 "${OUT}" | jq -r 'keys'
    echo "[DEBUG] runtime object (first record):"
    head -n 1 "${OUT}" | jq -r '.metadata.runtime'
    FAILS=$((FAILS+1))
    continue
  fi

  # Strict Option B checks (RAG/Thinking arm differentiation)
  if [[ "${STRICT_OPTION_B}" -eq 1 ]]; then
    # For B/D: rag_enabled=true and rag_sources_count > 0
    # For C/D: thinking_enabled=true and thinking_budget != null (or >0)
    if ! jq -e '
      .metadata.runtime.arm as $a |
      if ($a=="B" or $a=="D") then
        (.metadata.runtime.rag_enabled==true) and
        ((.metadata.runtime.rag_sources_count|tonumber) > 0)
      elif ($a=="C" or $a=="D") then
        (.metadata.runtime.thinking_enabled==true) and
        (.metadata.runtime.thinking_budget != null)
      else
        true
      end
    ' "${OUT}" >/dev/null; then
      echo "FAIL: strict Option-B acceptance criteria not met for some record(s)" >&2
      echo "[DEBUG] Offending summary (arm, rag_enabled, rag_sources_count, thinking_enabled, thinking_budget):"
      jq -r '[.metadata.runtime.arm,
             .metadata.runtime.rag_enabled,
             .metadata.runtime.rag_sources_count,
             .metadata.runtime.thinking_enabled,
             .metadata.runtime.thinking_budget] | @tsv' "${OUT}" | head -n 20
      FAILS=$((FAILS+1))
      continue
    fi
  fi

  echo "PASS"
  PASS=$((PASS+1))
done

echo "----"
echo "[RESULT] PASS files: ${PASS} / ${#OUTS[@]}"
if [[ "${FAILS}" -gt 0 ]]; then
  echo "[RESULT] FAIL files: ${FAILS} (see above)" >&2
  exit 1
fi

echo "[OK] All checks passed."

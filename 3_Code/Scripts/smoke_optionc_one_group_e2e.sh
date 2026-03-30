#!/usr/bin/env bash
set -euo pipefail

# MeducAI Option C E2E Smoke (1 group)
# -----------------------------------
# Runs:
#   baseline S5 (must already exist) -> Option C orchestrator -> postrepair S5
#   -> (synthetic) Ratings.csv -> S6 export gate manifest -> PDF + Anki export using manifest
#
# Usage:
#   RUN_TAG="..." GROUP_ID="grp_XXXXXXXXXX" ARM="A" S1_ARM="A" bash 3_Code/Scripts/smoke_optionc_one_group_e2e.sh
#
# Notes:
# - This script is meant for operator smoke runs (not CI).
# - It never overwrites baseline artifacts; it creates __repaired and __postrepair outputs.

BASE_DIR="${BASE_DIR:-"$(cd "$(dirname "$0")/../.." && pwd)"}"
RUN_TAG="${RUN_TAG:-""}"
GROUP_ID="${GROUP_ID:-""}"
ARM="${ARM:-"A"}"
S1_ARM="${S1_ARM:-"$ARM"}"
THRESHOLD="${THRESHOLD:-"70.0"}"

OUT_PDF_DIR="${OUT_PDF_DIR:-"$BASE_DIR/6_Distributions/QA_Packets"}"
OUT_ANKI_PATH="${OUT_ANKI_PATH:-"$BASE_DIR/6_Distributions/anki/SMOKE_${RUN_TAG}__arm${ARM}.apkg"}"

if [[ -z "$RUN_TAG" || -z "$GROUP_ID" ]]; then
  echo "ERROR: RUN_TAG and GROUP_ID are required." >&2
  echo "Example:" >&2
  echo "  RUN_TAG=\"...\" GROUP_ID=\"grp_...\" ARM=\"A\" S1_ARM=\"A\" bash 3_Code/Scripts/smoke_optionc_one_group_e2e.sh" >&2
  exit 2
fi

ARM="$(echo "$ARM" | tr '[:lower:]' '[:upper:]')"
S1_ARM="$(echo "$S1_ARM" | tr '[:lower:]' '[:upper:]')"

GEN_DIR="$BASE_DIR/2_Data/metadata/generated/$RUN_TAG"
BASELINE_S5="$GEN_DIR/s5_validation__arm${ARM}.jsonl"
BASELINE_S1="$GEN_DIR/stage1_struct__arm${S1_ARM}.jsonl"
BASELINE_S2="$GEN_DIR/s2_results__s1arm${S1_ARM}__s2arm${ARM}.jsonl"
REPAIRED_S2="$GEN_DIR/s2_results__s1arm${S1_ARM}__s2arm${ARM}__repaired.jsonl"
POSTREPAIR_S5="$GEN_DIR/s5_validation__arm${ARM}__postrepair.jsonl"

if [[ ! -f "$BASELINE_S5" ]]; then
  echo "ERROR: baseline S5 JSONL missing: $BASELINE_S5" >&2
  echo "Hint: run S5 validator first (baseline): python3 \"$BASE_DIR/3_Code/src/05_s5_validator.py\" --base_dir \"$BASE_DIR\" --run_tag \"$RUN_TAG\" --arm \"$ARM\"" >&2
  exit 2
fi
if [[ ! -f "$BASELINE_S1" ]]; then
  echo "ERROR: baseline S1 JSONL missing: $BASELINE_S1" >&2
  exit 2
fi
if [[ ! -f "$BASELINE_S2" ]]; then
  echo "ERROR: baseline S2 JSONL missing: $BASELINE_S2" >&2
  echo "Hint: generate S2 baseline first (stage 2): python3 \"$BASE_DIR/3_Code/src/01_generate_json.py\" --base_dir \"$BASE_DIR\" --run_tag \"$RUN_TAG\" --arm \"$ARM\" --s1_arm \"$S1_ARM\" --stage 2" >&2
  exit 2
fi

sha256_file () {
  python3 - "$1" <<'PY'
import hashlib, sys
from pathlib import Path
p = Path(sys.argv[1])
h = hashlib.sha256()
with p.open("rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
        h.update(chunk)
print(h.hexdigest())
PY
}

echo "[SMOKE] BASE_DIR=$BASE_DIR"
echo "[SMOKE] RUN_TAG=$RUN_TAG ARM=$ARM S1_ARM=$S1_ARM GROUP_ID=$GROUP_ID THRESHOLD=$THRESHOLD"

S1_SHA_BEFORE="$(sha256_file "$BASELINE_S1")"
S2_SHA_BEFORE="$(sha256_file "$BASELINE_S2")"

echo "[SMOKE] Baseline hashes (pre):"
echo "  - S1: $S1_SHA_BEFORE"
echo "  - S2: $S2_SHA_BEFORE"

echo "[SMOKE] 1) Option C orchestrator (one group)..."
python3 "$BASE_DIR/3_Code/src/05c_option_c_orchestrator.py" \
  --base_dir "$BASE_DIR" \
  --run_tag "$RUN_TAG" \
  --arm "$ARM" \
  --s1_arm "$S1_ARM" \
  --only_group_id "$GROUP_ID" \
  --threshold "$THRESHOLD" \
  --entity_filter_mode from_plan

S1_SHA_AFTER="$(sha256_file "$BASELINE_S1")"
S2_SHA_AFTER="$(sha256_file "$BASELINE_S2")"

if [[ "$S1_SHA_BEFORE" != "$S1_SHA_AFTER" ]]; then
  echo "ERROR: baseline S1 changed! (expected immutable)" >&2
  echo "  before=$S1_SHA_BEFORE" >&2
  echo "  after =$S1_SHA_AFTER" >&2
  exit 1
fi
if [[ "$S2_SHA_BEFORE" != "$S2_SHA_AFTER" ]]; then
  echo "ERROR: baseline S2 changed! (expected immutable)" >&2
  echo "  before=$S2_SHA_BEFORE" >&2
  echo "  after =$S2_SHA_AFTER" >&2
  exit 1
fi

echo "[SMOKE] Baseline immutability check: OK"

if [[ ! -f "$REPAIRED_S2" ]]; then
  echo "ERROR: repaired S2 JSONL not found (expected): $REPAIRED_S2" >&2
  exit 1
fi
if [[ ! -f "$POSTREPAIR_S5" ]]; then
  echo "ERROR: postrepair S5 JSONL not found (expected): $POSTREPAIR_S5" >&2
  exit 1
fi

echo "[SMOKE] 2) Create synthetic Ratings.csv (ACCEPT) to exercise S6 gate..."
RATINGS_CSV="$GEN_DIR/Ratings__SMOKE__${GROUP_ID}.csv"
cat > "$RATINGS_CSV" <<EOF
card_uid,accept_ai_correction
${GROUP_ID}::SMOKE_CARD,ACCEPT
EOF
echo "[SMOKE]   wrote: $RATINGS_CSV"

echo "[SMOKE] 3) S6 export gate -> manifest..."
MANIFEST_PATH="$GEN_DIR/s6_export_manifest__arm${ARM}__SMOKE__group${GROUP_ID}.json"
python3 "$BASE_DIR/3_Code/src/06_s6_export_gate.py" \
  --base_dir "$BASE_DIR" \
  --run_tag "$RUN_TAG" \
  --arm "$ARM" \
  --ratings_csv "$RATINGS_CSV" \
  --s5_postrepair_jsonl "$POSTREPAIR_S5" \
  --out_path "$MANIFEST_PATH"

echo "[SMOKE] 4) Export PDF (single group) using manifest..."
python3 "$BASE_DIR/3_Code/src/07_build_set_pdf.py" \
  --base_dir "$BASE_DIR" \
  --run_tag "$RUN_TAG" \
  --arm "$ARM" \
  --s1_arm "$S1_ARM" \
  --group_id "$GROUP_ID" \
  --out_dir "$OUT_PDF_DIR" \
  --allow_missing_images \
  --include_s5 \
  --export_manifest_path "$MANIFEST_PATH"

echo "[SMOKE] 5) Export Anki using manifest (allow missing images)..."
python3 "$BASE_DIR/3_Code/src/07_export_anki_deck.py" \
  --base_dir "$BASE_DIR" \
  --run_tag "$RUN_TAG" \
  --arm "$ARM" \
  --s1_arm "$S1_ARM" \
  --allow_missing_images \
  --export_manifest_path "$MANIFEST_PATH" \
  --output_path "$OUT_ANKI_PATH"

echo "[SMOKE] DONE"



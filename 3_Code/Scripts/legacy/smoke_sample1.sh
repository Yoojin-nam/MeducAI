#!/usr/bin/env bash
set -euo pipefail

# Smoke test for MeducAI (Sample 1): Step01 -> Step02 -> Tag integrity checks
#
# Usage:
#   ./scripts/smoke_sample1.sh
#   PROVIDER=gpt RUN_TAG=sample1_fix ./scripts/smoke_sample1.sh
#   CLEAN=0 ./scripts/smoke_sample1.sh   # keep existing outputs (not recommended)

PROVIDER="${PROVIDER:-gemini}"
RUN_TAG="${RUN_TAG:-sample1}"
CLEAN="${CLEAN:-1}"
BASE_DIR="${BASE_DIR:-.}"

JSONL="2_Data/metadata/generated/${PROVIDER}/output_${PROVIDER}_${RUN_TAG}.jsonl"
CSV="2_Data/metadata/generated/${PROVIDER}/anki_cards_${PROVIDER}_${RUN_TAG}.csv"

echo "=== MeducAI Smoke Test ==="
echo "PROVIDER=${PROVIDER}"
echo "RUN_TAG=${RUN_TAG}"
echo "CLEAN=${CLEAN}"
echo "BASE_DIR=${BASE_DIR}"
echo

if [[ "${CLEAN}" == "1" ]]; then
  echo "=== (0) Cleanup existing outputs (avoid JSONL append confusion) ==="
  rm -f "${JSONL}" "${CSV}" \
    "2_Data/metadata/generated/${PROVIDER}/table_infographic_prompts_${PROVIDER}_${RUN_TAG}.csv" \
    "2_Data/metadata/generated/${PROVIDER}/image_prompts_${PROVIDER}_${RUN_TAG}.csv" \
    "2_Data/metadata/generated/${PROVIDER}/postprocess_summary_${PROVIDER}_${RUN_TAG}.json" || true
  echo
fi

echo "=== (1) Step01: generate JSONL (sample=1) ==="
python 3_Code/src/01_generate_json.py --provider "${PROVIDER}" --sample 1 --run_tag "${RUN_TAG}"
test -f "${JSONL}" || { echo "ERROR: JSONL not found: ${JSONL}"; exit 1; }
echo "JSONL => ${JSONL}"
echo

echo "=== (2) Step01 sanity (use LAST line as truth) ==="
python - <<PY
import json
p="${JSONL}"
with open(p, encoding="utf-8") as f:
    lines=f.readlines()
r=json.loads(lines[-1])
src=(r.get("meta", {}) or {}).get("source", {})
print("group_key        :", repr(src.get("group_key")))
print("meta.source.tags :", repr(src.get("tags")))
ents=(r.get("curriculum_content", {}) or {}).get("entities", []) or []
if ents and ents[0].get("anki_cards"):
    c0=ents[0]["anki_cards"][0]
    print("first card_type  :", c0.get("card_type"))
    print("first card tags  :", c0.get("tags"))
PY
echo

echo "=== (2b) Step01 tag invariant check (LAST line) ==="
python - <<PY
import json
p="${JSONL}"
with open(p, encoding="utf-8") as f:
    r=json.loads(f.readlines()[-1])

src=(r.get("meta", {}) or {}).get("source", {})
tags=(src.get("tags","") or "")
if ";" in tags or "," in tags or "|" in tags:
    raise SystemExit(f"FAIL: meta.source.tags not canonical (contains delimiter): {tags!r}")

bad_hash=0
bad_ct=0
for e in (r.get("curriculum_content", {}) or {}).get("entities", []) or []:
    for c in e.get("anki_cards", []) or []:
        t=c.get("tags", [])
        if any("#" in x for x in t):
            bad_hash += 1
        ct=(c.get("card_type","") or "").strip().lower()
        if ct and (f"ct_{ct}" not in t):
            bad_ct += 1

print("Step01 cards with '#':", bad_hash)
print("Step01 ct mismatch   :", bad_ct)
if bad_hash or bad_ct:
    raise SystemExit("FAIL: Step01 tag invariant broken")
print("OK: Step01 tag invariants satisfied")
PY
echo

echo "=== (3) Step02: postprocess to CSV ==="
python 3_Code/src/02_postprocess_results.py --provider "${PROVIDER}" --run_tag "${RUN_TAG}" --base_dir "${BASE_DIR}"
test -f "${CSV}" || { echo "ERROR: CSV not found: ${CSV}"; exit 1; }
echo "CSV => ${CSV}"
echo

echo "=== (4) Step02 CSV tag integrity check (must be all 0) ==="
python - <<PY
import csv

p="${CSV}"
bad_empty = bad_hash = bad_korean = bad_ct = 0

def has_korean(s):
    return any("\uac00" <= ch <= "\ud7a3" for ch in s)

with open(p, encoding="utf-8") as f:
    r = csv.DictReader(f)
    for row in r:
        tags = (row.get("tags","") or "")
        ct = (row.get("card_type","") or "").strip().lower()
        if not tags.strip():
            bad_empty += 1
        if "#" in tags:
            bad_hash += 1
        if has_korean(tags):
            bad_korean += 1
        if ct and f"ct_{ct}" not in tags:
            bad_ct += 1

print("empty tags      :", bad_empty)
print("contains '#'    :", bad_hash)
print("contains korean :", bad_korean)
print("ct mismatch     :", bad_ct)

if bad_empty or bad_hash or bad_korean or bad_ct:
    raise SystemExit("FAIL: Step02 CSV tag integrity broken")
print("OK: Step02 CSV tag integrity satisfied")
PY
echo
echo "✅ PASS: Step01 -> Step02 smoke test succeeded (P0-3 invariants stable)"

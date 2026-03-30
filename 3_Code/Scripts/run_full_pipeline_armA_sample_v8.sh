#!/bin/bash
# Full Pipeline: S1/S2 → S3 → S4 → PDF → Anki for Arm A (sample 1)
# Updated for v8 prompts and improved PDF/Anki export

set -e  # Exit on error

# Accept RUN_TAG as argument or generate new one
if [ -n "$1" ]; then
    RUN_TAG="$1"
    echo "Using provided RUN_TAG: $RUN_TAG"
else
    RUN_TAG="FULL_PIPELINE_V8_$(date +%Y%m%d_%H%M%S)"
    echo "Generated new RUN_TAG: $RUN_TAG"
fi

echo "=========================================="
echo "🚀 MeducAI Full Pipeline - Arm A (Sample 1)"
echo "RUN_TAG: $RUN_TAG"
echo "=========================================="

BASE_DIR="."

# Step 1: S1/S2 - Generate content
echo ""
echo ">>> [Step 1] S1/S2: Generating content (Arm A, sample 1)..."
python3 3_Code/src/01_generate_json.py \
  --base_dir "$BASE_DIR" \
  --run_tag "$RUN_TAG" \
  --arm A \
  --mode S0 \
  --sample 1

# Check if S1/S2 succeeded
if [ ! -f "2_Data/metadata/generated/$RUN_TAG/s2_results__armA.jsonl" ]; then
  echo "❌ ERROR: S1/S2 failed - s2_results__armA.jsonl not found"
  exit 1
fi

# Check if S2 results file is not empty
if [ ! -s "2_Data/metadata/generated/$RUN_TAG/s2_results__armA.jsonl" ]; then
  echo "❌ ERROR: S1/S2 failed - s2_results__armA.jsonl is empty (no records generated)"
  echo "   This usually means no rows matched the filter criteria or S1/S2 processing failed silently"
  exit 1
fi

echo "✅ S1/S2 completed"

# Step 2: S3 - Policy resolver
echo ""
echo ">>> [Step 2] S3: Resolving image policies..."
python3 3_Code/src/03_s3_policy_resolver.py \
  --base_dir "$BASE_DIR" \
  --run_tag "$RUN_TAG" \
  --arm A

# Check if S3 succeeded
if [ ! -f "2_Data/metadata/generated/$RUN_TAG/image_policy_manifest__armA.jsonl" ]; then
  echo "❌ ERROR: S3 failed - image_policy_manifest__armA.jsonl not found"
  exit 1
fi

# Check if S3 output is not empty
if [ ! -s "2_Data/metadata/generated/$RUN_TAG/s3_image_spec__armA.jsonl" ]; then
  echo "❌ ERROR: S3 failed - s3_image_spec__armA.jsonl is empty (no image specs generated)"
  echo "   This usually means S2 results had no valid image_hint data"
  exit 1
fi

echo "✅ S3 completed"

# Step 3: S4 - Image generation
echo ""
echo ">>> [Step 3] S4: Generating images..."
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir "$BASE_DIR" \
  --run_tag "$RUN_TAG" \
  --arm A

# Check if S4 succeeded
if [ ! -f "2_Data/metadata/generated/$RUN_TAG/s4_image_manifest__armA.jsonl" ]; then
  echo "❌ ERROR: S4 failed - s4_image_manifest__armA.jsonl not found"
  exit 1
fi

# Check if S4 output is not empty
if [ ! -s "2_Data/metadata/generated/$RUN_TAG/s4_image_manifest__armA.jsonl" ]; then
  echo "❌ ERROR: S4 failed - s4_image_manifest__armA.jsonl is empty (no images generated)"
  exit 1
fi

echo "✅ S4 completed"

# Step 4: Get group_id from S1 output
echo ""
echo ">>> [Step 4] Extracting group_id..."
GROUP_ID=$(python3 -c "
import json
import sys
try:
    with open('2_Data/metadata/generated/$RUN_TAG/stage1_struct__armA.jsonl', 'r') as f:
        line = f.readline().strip()
        if line:
            data = json.loads(line)
            print(data.get('group_id', ''))
        else:
            sys.exit(1)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
")

if [ -z "$GROUP_ID" ]; then
  echo "❌ ERROR: Could not extract group_id"
  exit 1
fi

echo "Found group_id: $GROUP_ID"

# Step 5: PDF generation
echo ""
echo ">>> [Step 5] PDF: Building PDF packet..."
python3 3_Code/src/07_build_set_pdf.py \
  --base_dir "$BASE_DIR" \
  --run_tag "$RUN_TAG" \
  --arm A \
  --group_id "$GROUP_ID" \
  --out_dir "6_Distributions/QA_Packets"

# Check if PDF was created
PDF_PATH="6_Distributions/QA_Packets/SET_${GROUP_ID}_armA.pdf"
if [ ! -f "$PDF_PATH" ]; then
  echo "❌ ERROR: PDF not found at $PDF_PATH"
  exit 1
fi
echo "✅ PDF created: $PDF_PATH"

# Step 6: Anki deck generation
echo ""
echo ">>> [Step 6] Anki: Building Anki deck..."
python3 3_Code/src/07_export_anki_deck.py \
  --base_dir "$BASE_DIR" \
  --run_tag "$RUN_TAG" \
  --arm A

# Check if Anki deck was created
ANKI_PATH="6_Distributions/anki/MeducAI_${RUN_TAG}_armA.apkg"
if [ ! -f "$ANKI_PATH" ]; then
  echo "❌ ERROR: Anki deck not found at $ANKI_PATH"
  exit 1
fi
echo "✅ Anki deck created: $ANKI_PATH"

# Summary
echo ""
echo "=========================================="
echo "✅ SUCCESS: Full pipeline completed!"
echo "=========================================="
echo "RUN_TAG: $RUN_TAG"
echo "Group ID: $GROUP_ID"
echo ""
echo "Output files:"
echo "  - S1/S2: 2_Data/metadata/generated/$RUN_TAG/s2_results__armA.jsonl"
echo "  - S3:    2_Data/metadata/generated/$RUN_TAG/image_policy_manifest__armA.jsonl"
echo "  - S4:    2_Data/metadata/generated/$RUN_TAG/s4_image_manifest__armA.jsonl"
echo "  - PDF:   $PDF_PATH"
echo "  - Anki:  $ANKI_PATH"
echo "=========================================="


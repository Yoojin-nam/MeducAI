#!/bin/bash
# Full Pipeline: S1/S2 → S3 → S4 → PDF for Arm A (sample 1)

set -e  # Exit on error

# Generate RUN_TAG
RUN_TAG="SAMPLE_A_$(date +%Y%m%d_%H%M%S)"
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

# Step 2: S3 - Policy resolver
echo ""
echo ">>> [Step 2] S3: Resolving image policies..."
python3 3_Code/src/03_s3_policy_resolver.py \
  --base_dir "$BASE_DIR" \
  --run_tag "$RUN_TAG" \
  --arm A

# Check if S3 succeeded
if [ ! -f "2_Data/metadata/generated/$RUN_TAG/s3_image_spec__armA.jsonl" ]; then
  echo "❌ ERROR: S3 failed - s3_image_spec__armA.jsonl not found"
  exit 1
fi

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

# Step 4: Get group_id from S1 output
echo ""
echo ">>> [Step 4] Extracting group_id..."
GROUP_ID=$(python3 -c "
import json
with open('2_Data/metadata/generated/$RUN_TAG/stage1_struct__armA.jsonl', 'r') as f:
    line = f.readline().strip()
    if line:
        data = json.loads(line)
        print(data.get('group_id', ''))
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
if [ -f "$PDF_PATH" ]; then
  echo ""
  echo "=========================================="
  echo "✅ SUCCESS: Full pipeline completed!"
  echo "=========================================="
  echo "RUN_TAG: $RUN_TAG"
  echo "Group ID: $GROUP_ID"
  echo "PDF: $PDF_PATH"
  echo ""
  echo "Output files:"
  echo "  - S1/S2: 2_Data/metadata/generated/$RUN_TAG/s2_results__armA.jsonl"
  echo "  - S3:    2_Data/metadata/generated/$RUN_TAG/s3_image_spec__armA.jsonl"
  echo "  - S4:    2_Data/metadata/generated/$RUN_TAG/s4_image_manifest__armA.jsonl"
  echo "  - PDF:   $PDF_PATH"
  echo "=========================================="
else
  echo "❌ ERROR: PDF not found at $PDF_PATH"
  exit 1
fi


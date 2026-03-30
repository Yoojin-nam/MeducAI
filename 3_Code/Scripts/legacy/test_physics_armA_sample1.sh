#!/bin/bash
# Test Physics Specialty - Arm A, Sample 1
# Tests CONCEPT routing for QC/Equipment groups

set -e  # Exit on error

# Generate RUN_TAG
RUN_TAG="PHYSICS_TEST_$(date +%Y%m%d_%H%M%S)"
echo "=========================================="
echo "🧪 MeducAI Physics Specialty Test - Arm A (Sample 1)"
echo "RUN_TAG: $RUN_TAG"
echo "Testing CONCEPT routing for QC/Equipment groups"
echo "=========================================="

BASE_DIR="."

# Step 1: Find a physics specialty group
echo ""
echo ">>> [Step 0] Finding physics specialty group..."
PHYSICS_GROUP=$(python3 -c "
import csv
import sys
from pathlib import Path

csv_path = Path('2_Data/metadata/groups_canonical.csv')
if not csv_path.exists():
    print('ERROR: groups_canonical.csv not found', file=sys.stderr)
    sys.exit(1)

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        specialty = row.get('specialty', '').strip().lower()
        group_key = row.get('group_key', '').strip().lower()
        # Check specialty (phys_qc_medinfo contains 'phys') or group_key starting with 'physics'
        if 'phys' in specialty or group_key.startswith('physics'):
            print(row.get('group_key', ''))
            sys.exit(0)

print('ERROR: No physics specialty group found', file=sys.stderr)
sys.exit(1)
")

if [ -z "$PHYSICS_GROUP" ]; then
  echo "❌ ERROR: Could not find physics specialty group"
  exit 1
fi

echo "Found physics group: $PHYSICS_GROUP"

# Step 2: S1/S2 - Generate content
echo ""
echo ">>> [Step 1] S1/S2: Generating content (Arm A, physics group, sample 1)..."
python3 3_Code/src/01_generate_json.py \
  --base_dir "$BASE_DIR" \
  --run_tag "$RUN_TAG" \
  --arm A \
  --mode S0 \
  --only_group_key "$PHYSICS_GROUP" \
  --sample 1

# Check if S1/S2 succeeded
if [ ! -f "2_Data/metadata/generated/$RUN_TAG/s2_results__armA.jsonl" ]; then
  echo "❌ ERROR: S1/S2 failed - s2_results__armA.jsonl not found"
  exit 1
fi

# Check if S2 results file is not empty
if [ ! -s "2_Data/metadata/generated/$RUN_TAG/s2_results__armA.jsonl" ]; then
  echo "❌ ERROR: S1/S2 failed - s2_results__armA.jsonl is empty"
  exit 1
fi

echo "✅ S1/S2 completed"

# Step 3: S3 - Policy resolver (with CONCEPT routing check)
echo ""
echo ">>> [Step 2] S3: Resolving image policies (checking CONCEPT routing)..."
python3 3_Code/src/03_s3_policy_resolver.py \
  --base_dir "$BASE_DIR" \
  --run_tag "$RUN_TAG" \
  --arm A

# Check if S3 succeeded
if [ ! -f "2_Data/metadata/generated/$RUN_TAG/s3_image_spec__armA.jsonl" ]; then
  echo "❌ ERROR: S3 failed - s3_image_spec__armA.jsonl not found"
  exit 1
fi

# Check for CONCEPT specs
echo ""
echo ">>> Checking for CONCEPT specs..."
CONCEPT_COUNT=$(python3 -c "
import json
import sys

spec_path = '2_Data/metadata/generated/$RUN_TAG/s3_image_spec__armA.jsonl'
try:
    with open(spec_path, 'r', encoding='utf-8') as f:
        concept_count = 0
        exam_count = 0
        for line in f:
            line = line.strip()
            if not line:
                continue
            spec = json.loads(line)
            spec_kind = spec.get('spec_kind', '')
            if spec_kind == 'S2_CARD_CONCEPT':
                concept_count += 1
                print(f\"  Found CONCEPT spec: {spec.get('entity_name', 'N/A')} (visual_type: {spec.get('visual_type_category', 'N/A')})\", file=sys.stderr)
            elif spec_kind == 'S2_CARD_IMAGE':
                exam_count += 1
        print(f\"CONCEPT: {concept_count}, EXAM: {exam_count}\")
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
")

echo "$CONCEPT_COUNT"

# Step 4: S4 - Image generation (dry-run first to check preamble)
echo ""
echo ">>> [Step 3] S4: Testing image generation (dry-run)..."
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir "$BASE_DIR" \
  --run_tag "$RUN_TAG" \
  --arm A \
  --dry_run

echo ""
echo ">>> [Step 4] S4: Generating images (actual)..."
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir "$BASE_DIR" \
  --run_tag "$RUN_TAG" \
  --arm A

# Check if S4 succeeded
if [ ! -f "2_Data/metadata/generated/$RUN_TAG/s4_image_manifest__armA.jsonl" ]; then
  echo "❌ ERROR: S4 failed - s4_image_manifest__armA.jsonl not found"
  exit 1
fi

# Summary
echo ""
echo "=========================================="
echo "✅ SUCCESS: Physics specialty test completed!"
echo "=========================================="
echo "RUN_TAG: $RUN_TAG"
echo "Group: $PHYSICS_GROUP"
echo ""
echo "Output files:"
echo "  - S1/S2: 2_Data/metadata/generated/$RUN_TAG/s2_results__armA.jsonl"
echo "  - S3:    2_Data/metadata/generated/$RUN_TAG/s3_image_spec__armA.jsonl"
echo "  - S4:    2_Data/metadata/generated/$RUN_TAG/s4_image_manifest__armA.jsonl"
echo "  - Images: 2_Data/metadata/generated/$RUN_TAG/images/"
echo ""
echo "Check CONCEPT routing:"
echo "  python3 -c \"import json; [print(f\\\"{s.get('spec_kind')}: {s.get('entity_name')} (visual_type: {s.get('visual_type_category', 'N/A')})\\\") for s in [json.loads(l) for l in open('2_Data/metadata/generated/$RUN_TAG/s3_image_spec__armA.jsonl')] if s.get('spec_kind') in ['S2_CARD_CONCEPT', 'S2_CARD_IMAGE']]\""
echo "=========================================="


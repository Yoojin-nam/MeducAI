#!/bin/bash
# Retry failed image generation for a specific run_tag
# Usage: ./retry_failed_images.sh <run_tag> <arm>

set -e

RUN_TAG="${1}"
ARM="${2:-G}"

if [ -z "$RUN_TAG" ]; then
    echo "Usage: $0 <run_tag> [arm]"
    echo "Example: $0 DEV_armG_mm_S5R0_before_rerun_preFix_20251229_195130__rep1 G"
    exit 1
fi

BASE_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="${BASE_DIR}/2_Data/metadata/generated/${RUN_TAG}"
MANIFEST_PATH="${OUT_DIR}/s4_image_manifest__arm${ARM}.jsonl"
IMAGES_DIR="${OUT_DIR}/images"

if [ ! -f "$MANIFEST_PATH" ]; then
    echo "Error: Manifest not found: $MANIFEST_PATH"
    exit 1
fi

echo "=========================================="
echo "Retrying Failed Image Generation"
echo "=========================================="
echo "Run tag: $RUN_TAG"
echo "Arm: $ARM"
echo "Manifest: $MANIFEST_PATH"
echo "Images dir: $IMAGES_DIR"
echo "=========================================="
echo ""

# Delete failed image files (if they exist) so S4 will regenerate them
echo "Checking for failed images to retry..."
python3 -c "
import json
import sys
from pathlib import Path

manifest_path = Path('$MANIFEST_PATH')
images_dir = Path('$IMAGES_DIR')

if not manifest_path.exists():
    print(f'Error: Manifest not found: {manifest_path}')
    sys.exit(1)

failed_count = 0
deleted_count = 0

with open(manifest_path, 'r') as f:
    for line in f:
        if not line.strip():
            continue
        record = json.loads(line)
        if not record.get('generation_success', True):
            filename = record.get('media_filename', '')
            if filename:
                filepath = images_dir / filename
                failed_count += 1
                if filepath.exists():
                    filepath.unlink()
                    deleted_count += 1
                    print(f'Deleted: {filename}')

print(f'')
print(f'Failed images in manifest: {failed_count}')
print(f'Deleted existing files: {deleted_count}')
print(f'Will regenerate: {failed_count}')
"

if [ $? -ne 0 ]; then
    echo "Error: Failed to process manifest"
    exit 1
fi

echo ""
echo "Running S4 to regenerate failed images..."
echo ""

# Run S4 (it will skip existing images and regenerate missing ones)
cd "$BASE_DIR"
python3 "$BASE_DIR/3_Code/src/04_s4_image_generator.py" \
    --base_dir "$BASE_DIR" \
    --run_tag "$RUN_TAG" \
    --arm "$ARM"

echo ""
echo "=========================================="
echo "Done!"
echo "=========================================="


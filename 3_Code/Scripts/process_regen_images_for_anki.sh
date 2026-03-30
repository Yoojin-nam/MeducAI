#!/bin/bash
# Process REGEN images for Anki distribution
# - Resize and optimize for Anki (images_anki/)
# - Move originals to raw/ folder for archival

set -euo pipefail

# Configuration
REGEN_DIR="2_Data/metadata/generated/FINAL_DISTRIBUTION/images_regen"
ANKI_OUTPUT_DIR="2_Data/metadata/generated/FINAL_DISTRIBUTION/images_regen_anki"
RAW_OUTPUT_DIR="2_Data/metadata/generated/FINAL_DISTRIBUTION/images_regen_raw"

# Anki optimization settings (matching existing images_anki)
GRAY_WIDTH=1200
GRAY_QUALITY=85
COLOR_WIDTH=1200
COLOR_QUALITY=90

echo "========================================"
echo "REGEN Images → Anki Processing"
echo "========================================"
echo ""
echo "Input:  ${REGEN_DIR}"
echo "Anki:   ${ANKI_OUTPUT_DIR}"
echo "Raw:    ${RAW_OUTPUT_DIR}"
echo ""
echo "Settings:"
echo "  GRAY:  width=${GRAY_WIDTH}, quality=${GRAY_QUALITY}, grayscale_encode=1"
echo "  COLOR: width=${COLOR_WIDTH}, quality=${COLOR_QUALITY}"
echo ""

# Check if input directory exists
if [ ! -d "${REGEN_DIR}" ]; then
    echo "Error: REGEN directory not found: ${REGEN_DIR}"
    exit 1
fi

# Count images
IMAGE_COUNT=$(find "${REGEN_DIR}" -name "*.jpg" -type f | wc -l | tr -d ' ')
echo "Found ${IMAGE_COUNT} REGEN images to process"
echo ""

# Create output directories
mkdir -p "${ANKI_OUTPUT_DIR}"
mkdir -p "${RAW_OUTPUT_DIR}"

# Step 1: Run optimize_images.py in final mode
echo "Step 1: Optimizing images for Anki..."
echo "----------------------------------------"
python3 3_Code/src/tools/optimize_images.py final \
    --input "${REGEN_DIR}" \
    --out "${ANKI_OUTPUT_DIR}" \
    --threshold 0.15 \
    --gray_width ${GRAY_WIDTH} \
    --gray_quality ${GRAY_QUALITY} \
    --gray_grayscale_encode 1 \
    --color_width ${COLOR_WIDTH} \
    --color_quality ${COLOR_QUALITY} \
    --lossless_opt 0 \
    --overwrite

echo ""
echo "Step 2: Moving original REGEN images to raw/ folder..."
echo "----------------------------------------"

# Move originals to raw folder
MOVED_COUNT=0
for img in "${REGEN_DIR}"/*.jpg; do
    if [ -f "$img" ]; then
        filename=$(basename "$img")
        mv "$img" "${RAW_OUTPUT_DIR}/${filename}"
        MOVED_COUNT=$((MOVED_COUNT + 1))
    fi
done

echo "Moved ${MOVED_COUNT} original images to ${RAW_OUTPUT_DIR}"
echo ""

# Step 3: Verify outputs
echo "Step 3: Verification..."
echo "----------------------------------------"

ANKI_COUNT=$(find "${ANKI_OUTPUT_DIR}" -name "*.jpg" -type f | wc -l | tr -d ' ')
RAW_COUNT=$(find "${RAW_OUTPUT_DIR}" -name "*.jpg" -type f | wc -l | tr -d ' ')

echo "Anki images:     ${ANKI_COUNT}"
echo "Raw images:      ${RAW_COUNT}"
echo "Expected:        ${IMAGE_COUNT}"
echo ""

if [ "${ANKI_COUNT}" -eq "${IMAGE_COUNT}" ] && [ "${RAW_COUNT}" -eq "${IMAGE_COUNT}" ]; then
    echo "✅ SUCCESS: All images processed correctly"
else
    echo "⚠️  WARNING: Image counts don't match expected"
    echo "   Anki: ${ANKI_COUNT}/${IMAGE_COUNT}"
    echo "   Raw:  ${RAW_COUNT}/${IMAGE_COUNT}"
fi

echo ""
echo "========================================"
echo "Processing Complete"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Review manifest.csv in ${ANKI_OUTPUT_DIR}"
echo "2. Verify sample images in ${ANKI_OUTPUT_DIR}"
echo "3. Original high-res images archived in ${RAW_OUTPUT_DIR}"


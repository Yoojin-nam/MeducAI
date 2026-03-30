#!/bin/bash
# Resume S4 image generation from where it failed
# This script runs S4 for arms that have missing images
# The S4 script has been modified to skip existing images, so it will only generate missing ones

set -e

RUN_TAG="S0_QA_final_time"
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "========================================="
echo "Resuming S4 Image Generation"
echo "Run Tag: $RUN_TAG"
echo "Base Dir: $BASE_DIR"
echo "========================================="
echo ""
echo "Note: This script will skip existing images and only generate missing ones."
echo ""

# Arms that have missing images (based on analysis)
ARMS_WITH_MISSING=("D" "E" "F")

for arm in "${ARMS_WITH_MISSING[@]}"; do
    echo ""
    echo "========================================="
    echo "Processing Arm $arm..."
    echo "========================================="
    
    python3 "$BASE_DIR/3_Code/src/04_s4_image_generator.py" \
        --base_dir "$BASE_DIR" \
        --run_tag "$RUN_TAG" \
        --arm "$arm"
    
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ Arm $arm completed successfully"
    else
        echo "❌ Arm $arm failed (exit code: $EXIT_CODE)"
        echo "You may want to retry this arm separately"
        # Continue with other arms even if one fails
    fi
done

echo ""
echo "========================================="
echo "All arms processed"
echo "========================================="
echo ""
echo "To check the results, you can run:"
echo "  python3 $BASE_DIR/3_Code/Scripts/regenerate_s4_manifest.py --base_dir $BASE_DIR --run_tag $RUN_TAG --arm <ARM>"
echo "to regenerate manifests if needed."


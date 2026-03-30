#!/bin/bash
#
# Export FINAL Anki deck with selective REGEN content
# 
# Strategy:
# 1. Export REGEN cards only (from s2_regen + images_regen)
# 2. Export PASS cards only (from s2_baseline + images_anki)
# 3. Manual merge not needed - just provide two decks
#

set -e

BASE_DIR="/path/to/workspace/workspace/MeducAI"
RUN_TAG="FINAL_DISTRIBUTION"
ARM="G"

OUT_DIR="$BASE_DIR/6_Distributions/MeducAI_Final_Share"
mkdir -p "$OUT_DIR"

echo "========================================"
echo "FINAL Anki Export with REGEN"
echo "========================================"

# Export baseline only (all cards, baseline content/images)
echo ""
echo "[1/2] Exporting baseline deck (7,018 cards)..."
python3 "$BASE_DIR/3_Code/src/07_export_anki_deck.py" \
    --base_dir "$BASE_DIR" \
    --run_tag "$RUN_TAG" \
    --arm "$ARM" \
    --s1_arm "$ARM" \
    --allow_missing_images \
    --output_path "$OUT_DIR/MeducAI_FINAL_7018cards_BASELINE.apkg"

echo ""
echo "✅ Baseline deck created"
echo "   - Cards: ~7,018"
echo "   - Images: images_anki (baseline)"
echo "   - Content: Baseline (uncorrected)"

echo ""
echo "========================================"
echo "✅ Export Complete"
echo "========================================"
echo ""
echo "Output files:"
echo "  - $OUT_DIR/MeducAI_FINAL_7018cards_BASELINE.apkg"
echo ""
echo "Note: REGEN content integration requires manual Anki processing"
echo "      or use AppSheet for QA (REGEN content already included)"


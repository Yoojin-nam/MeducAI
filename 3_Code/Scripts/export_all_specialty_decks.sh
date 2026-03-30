#!/bin/bash
#
# Export all 11 specialty-specific Anki decks with REGEN integration
#

set -e

BASE_DIR="/path/to/workspace/workspace/MeducAI"
OUT_DIR="$BASE_DIR/6_Distributions/MeducAI_Final_Share/anki/Specialty_Decks"

mkdir -p "$OUT_DIR"

echo "========================================"
echo "Exporting 11 Specialty Decks with REGEN"
echo "========================================"

declare -A DISPLAY_NAMES
DISPLAY_NAMES["abdominal_radiology"]="Abdominal"
DISPLAY_NAMES["breast_rad"]="Breast"
DISPLAY_NAMES["cardiovascular_rad"]="Cardiovascular"
DISPLAY_NAMES["gu_radiology"]="GU"
DISPLAY_NAMES["interventional_radiology"]="IR"
DISPLAY_NAMES["musculoskeletal_radiology"]="MSK"
DISPLAY_NAMES["neuro_hn_imaging"]="NeuroHN"
DISPLAY_NAMES["nuclear_med"]="NuclearMed"
DISPLAY_NAMES["pediatric_radiology"]="Pediatric"
DISPLAY_NAMES["physics_qc_informatics"]="PhysicsQC"
DISPLAY_NAMES["thoracic_radiology"]="Thoracic"

i=1
for specialty in abdominal_radiology breast_rad cardiovascular_rad gu_radiology interventional_radiology musculoskeletal_radiology neuro_hn_imaging nuclear_med pediatric_radiology physics_qc_informatics thoracic_radiology; do
    display_name="${DISPLAY_NAMES[$specialty]}"
    
    echo ""
    echo "[$i/11] $display_name ($cli_code)..."
    
    python3 "$BASE_DIR/3_Code/src/tools/anki/export_final_anki_integrated.py" \
        --allocation "$BASE_DIR/2_Data/metadata/generated/FINAL_DISTRIBUTION/allocation/final_distribution_allocation__6000cards.json" \
        --s5 "$BASE_DIR/2_Data/metadata/generated/FINAL_DISTRIBUTION/s5_validation__armG.jsonl" \
        --s2_baseline "$BASE_DIR/2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG.jsonl" \
        --s2_regen "$BASE_DIR/2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__regen.jsonl" \
        --images_anki "$BASE_DIR/2_Data/metadata/generated/FINAL_DISTRIBUTION/images_anki" \
        --images_regen "$BASE_DIR/2_Data/metadata/generated/FINAL_DISTRIBUTION/images_regen" \
        --output "$OUT_DIR/MeducAI_FINAL_${display_name}.apkg" \
        --threshold 80.0 \
        --specialty "$specialty" 2>&1 | grep -E "(Processing|Total notes|File size|Complete|Cards in allocation)" || true
    
    i=$((i + 1))
done

echo ""
echo "========================================"
echo "✅ All specialty decks exported"
echo "========================================"
echo ""
echo "Output directory: $OUT_DIR"
ls -lh "$OUT_DIR"/*.apkg


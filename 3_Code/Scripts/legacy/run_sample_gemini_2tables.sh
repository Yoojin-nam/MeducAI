#!/usr/bin/env bash
set -euo pipefail

# =========================
# MeducAI v3.0 sample run
# Gemini / 2 tables only
# =========================

PROVIDER="gemini"
RUN_TAG="sample2_$(date +%Y%m%d_%H%M%S)"

echo "🚀 MeducAI sample run"
echo "  provider : ${PROVIDER}"
echo "  run_tag  : ${RUN_TAG}"
echo "  sample   : 2 objectives (tables)"
echo "----------------------------------"

# Step 01: JSONL 생성 (테이블 2개만)
echo "▶ Step 01: generate JSONL (sample=2)"
python 3_Code/src/01_generate_json.py \
  --provider ${PROVIDER} \
  --sample 2 \
  --run_tag ${RUN_TAG}

# Step 02: JSONL → CSV 정규화
echo "▶ Step 02: postprocess JSONL → CSV"
python 3_Code/src/02_postprocess_results.py \
  --provider ${PROVIDER} \
  --run_tag ${RUN_TAG}

# Step 03-A: Table-level infographic 생성 (record_id당 1장)
echo "▶ Step 03-A: generate table infographics (1 per table)"
python 3_Code/src/03_generate_images.py \
  --provider ${PROVIDER} \
  --run_tag ${RUN_TAG} \
  --input_csv 2_Data/metadata/generated/${PROVIDER}/table_infographic_prompts_${PROVIDER}_${RUN_TAG}.csv \
  --input_kind table \
  --table_one_per_record \
  --aspect_ratio 4:5 \
  --image_size 2K

# (선택) Step 03-B: Entity 이미지까지 보고 싶으면 주석 해제
echo "▶ Step 03-B: generate entity images (IMG_REQ only)"
python 3_Code/src/03_generate_images.py \
   --provider ${PROVIDER} \
   --run_tag ${RUN_TAG}

# Step 04: Anki deck 생성 (specialty/topic subdeck + 이미지 포함)
echo "▶ Step 04: export Anki deck"
python 3_Code/src/04_export_anki.py \
  --provider ${PROVIDER} \
  --run_tag ${RUN_TAG} \
  --split_mode specialty_topic \
  --attach_images

echo "✅ Sample pipeline completed."
echo "📦 Outputs:"
echo " - JSONL   : 2_Data/metadata/generated/${PROVIDER}/output_${PROVIDER}_${RUN_TAG}.jsonl"
echo " - CSVs    : 2_Data/metadata/generated/${PROVIDER}/*_${PROVIDER}_${RUN_TAG}.csv"
echo " - Images  : 2_Data/images/generated/${PROVIDER}/${RUN_TAG}/table/"
echo " - Anki    : 6_Distributions/anki/MeducAI_${PROVIDER}_${RUN_TAG}.apkg"

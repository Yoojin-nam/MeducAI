#!/bin/bash
# S5 재실행: card_image_validation 누락된 29개 그룹
# 생성일: 2026-01-05

set -e

BASE_DIR="/path/to/workspace/workspace/MeducAI"
RUN_TAG="FINAL_DISTRIBUTION"
ARM="G"

# 29개 그룹 목록
GROUPS=(
    "grp_6024906e14"
    "grp_61246822e4"
    "grp_62b879c0f5"
    "grp_6415318e8a"
    "grp_641bed1b4f"
    "grp_651a04fff1"
    "grp_667f21cebc"
    "grp_670b2ec1aa"
    "grp_68db6c4b3a"
    "grp_6a3cd258ee"
    "grp_6a9258636c"
    "grp_6ae1e80a49"
    "grp_6c8f5e306d"
    "grp_6d0f5b77d8"
    "grp_6de2ba1c83"
    "grp_70bff0442c"
    "grp_7149f98c07"
    "grp_71a686597f"
    "grp_7298635e2e"
    "grp_73d656909a"
    "grp_743004ab29"
    "grp_d94a493ab2"
    "grp_db29c16fd1"
    "grp_dc7faeae74"
    "grp_dcf5b4dc09"
    "grp_dd0ad73336"
    "grp_e190b25c83"
    "grp_e344f0c686"
    "grp_e4c2459d59"
)

# 임시 출력 파일
TEMP_OUTPUT="${BASE_DIR}/2_Data/metadata/generated/${RUN_TAG}/s5_validation__arm${ARM}__patch_29groups.jsonl"

echo "=============================================="
echo "S5 재실행: card_image_validation 누락 그룹"
echo "=============================================="
echo "총 ${#GROUPS[@]}개 그룹"
echo "출력: ${TEMP_OUTPUT}"
echo ""

# 기존 임시 파일 삭제
rm -f "${TEMP_OUTPUT}"

cd "${BASE_DIR}/3_Code/src"

for i in "${!GROUPS[@]}"; do
    GROUP="${GROUPS[$i]}"
    echo "[$(($i + 1))/${#GROUPS[@]}] Processing ${GROUP}..."
    
    python3 05_s5_validator.py \
        --base_dir "${BASE_DIR}" \
        --run_tag "${RUN_TAG}" \
        --arm "${ARM}" \
        --group_id "${GROUP}" \
        --output_path "${TEMP_OUTPUT}" \
        --s5_mode s2_only \
        --workers_s5 1
    
    echo "  ✓ Done"
done

echo ""
echo "=============================================="
echo "S5 재실행 완료!"
echo "패치 파일: ${TEMP_OUTPUT}"
echo ""
echo "다음 단계: 패치 파일을 기존 S5 validation 파일에 병합"
echo "=============================================="

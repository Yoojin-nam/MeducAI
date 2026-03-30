#!/bin/bash
# FINAL 모드 - Arm E - 모든 entity - S1만 실행
# 목적: RPD 제한을 피하기 위해 S1만 먼저 실행

set -e  # Exit on error

# RUN_TAG 생성
RUN_TAG="FINAL_ARM_E_S1_$(date +%Y%m%d_%H%M%S)"
echo "=========================================="
echo "🚀 FINAL Mode - Arm E - S1 Only"
echo "RUN_TAG: $RUN_TAG"
echo "=========================================="

# RUN_TAG를 파일에 저장 (나중에 참조용)
echo "$RUN_TAG" > "run_tag_final_arm_e_s1_$(date +%Y%m%d).txt"
echo "RUN_TAG saved to: run_tag_final_arm_e_s1_$(date +%Y%m%d).txt"

BASE_DIR="."

# groups.csv에서 전체 그룹 수 확인
GROUPS_CSV="$BASE_DIR/2_Data/metadata/groups.csv"
if [ ! -f "$GROUPS_CSV" ]; then
  echo "❌ ERROR: groups.csv not found at $GROUPS_CSV"
  exit 1
fi

# 전체 그룹 수 계산 (헤더 제외)
TOTAL_GROUPS=$(tail -n +2 "$GROUPS_CSV" | wc -l | tr -d ' ')
echo "📊 Total groups in groups.csv: $TOTAL_GROUPS"

# S1만 실행 (FINAL 모드, Arm E, 모든 entity)
# --sample을 전체 그룹 수보다 큰 값으로 설정하여 모든 그룹 처리
echo ""
echo ">>> [S1] Generating stage1_struct for Arm E (FINAL mode, all $TOTAL_GROUPS entities)..."
python3 3_Code/src/01_generate_json.py \
  --base_dir "$BASE_DIR" \
  --run_tag "$RUN_TAG" \
  --arm E \
  --mode FINAL \
  --stage 1 \
  --sample $((TOTAL_GROUPS + 100))  # 전체 그룹 수보다 큰 값으로 설정

# S1 Gate 검증 (선택사항)
echo ""
echo ">>> [Validation] Checking S1 output..."
if [ -f "2_Data/metadata/generated/$RUN_TAG/stage1_struct__armE.jsonl" ]; then
  echo "✅ S1 output found: stage1_struct__armE.jsonl"
  # 파일 크기 확인
  FILE_SIZE=$(wc -l < "2_Data/metadata/generated/$RUN_TAG/stage1_struct__armE.jsonl")
  echo "   Records: $FILE_SIZE"
else
  echo "❌ ERROR: S1 output not found"
  exit 1
fi

echo ""
echo "=========================================="
echo "✅ S1 execution completed"
echo "RUN_TAG: $RUN_TAG"
echo ""
echo "📝 To continue with S2 later:"
echo ""
echo "   # 같은 arm (E)으로 S2 실행:"
echo "   RUN_TAG=\"$RUN_TAG\""
echo "   python3 3_Code/src/01_generate_json.py \\"
echo "     --base_dir . \\"
echo "     --run_tag \"\$RUN_TAG\" \\"
echo "     --arm E \\"
echo "     --mode FINAL \\"
echo "     --stage 2"
echo ""
echo "   # 다른 arm (예: A)으로 S2 실행 (S1 출력은 arm E에서 읽음):"
echo "   RUN_TAG=\"$RUN_TAG\""
echo "   python3 3_Code/src/01_generate_json.py \\"
echo "     --base_dir . \\"
echo "     --run_tag \"\$RUN_TAG\" \\"
echo "     --arm A \\"
echo "     --s1_arm E \\"
echo "     --mode FINAL \\"
echo "     --stage 2"
echo "=========================================="

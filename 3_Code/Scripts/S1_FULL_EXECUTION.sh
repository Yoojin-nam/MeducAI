#!/bin/bash
# S1+S2 전체 그룹 실행 스크립트
# 모든 그룹에 대해 S1 (문제 생성) 및 S2 (카드 생성) 실행

# 타임스탬프 생성
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Run Tag 생성 (S5R2 버전 사용 중)
RUN_TAG="PROD_S1S2_all_groups_S5R2_${TIMESTAMP}"

echo "=========================================="
echo "S1+S2 전체 그룹 실행"
echo "=========================================="
echo "Run Tag: $RUN_TAG"
echo "Stage: both (S1 문제 생성 + S2 카드 생성)"
echo "Mode: FINAL (모든 Entity 생성)"
echo "Arm: G (기본)"
echo "=========================================="
echo ""

# S1+S2 함께 실행 (API 효율적)
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG" \
  --arm G \
  --mode FINAL \
  --stage both

echo ""
echo "=========================================="
echo "실행 완료"
echo "Run Tag: $RUN_TAG"
echo "=========================================="

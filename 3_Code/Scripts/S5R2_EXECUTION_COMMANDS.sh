#!/bin/bash
# S5R2 실행 스크립트
# Run tag: DEV_armG_mm_S5R2_after_postFix_20251230_185052__rep1 및 __rep2

set -e  # 에러 발생 시 중단

# Run tag 설정
RUN_TAG_REP1="DEV_armG_mm_S5R2_after_postFix_20251230_185052__rep1"
RUN_TAG_REP2="DEV_armG_mm_S5R2_after_postFix_20251230_185052__rep2"

echo "=========================================="
echo "S5R2 실행 시작"
echo "rep1: $RUN_TAG_REP1"
echo "rep2: $RUN_TAG_REP2"
echo "=========================================="

# ==========================================
# rep1 실행
# ==========================================
echo ""
echo ">>> rep1 실행 시작"

# 1. S1/S2 생성
echo "  [1/5] S1/S2 생성 중..."
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G \
  --mode FINAL \
  --stage both \
  --only_group_keys_file temp_selected_groups.txt

# 2. S3 실행
echo "  [2/5] S3 실행 중..."
python3 3_Code/src/03_s3_policy_resolver.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G

# 3. S4 실행
echo "  [3/5] S4 실행 중..."
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G

# 4. S5 검증
echo "  [4/5] S5 검증 중..."
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G

# 5. S5 리포트
echo "  [5/5] S5 리포트 생성 중..."
python3 3_Code/src/tools/s5/s5_report.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP1" \
  --arm G

echo ">>> rep1 실행 완료"
echo ""

# ==========================================
# rep2 실행
# ==========================================
echo ">>> rep2 실행 시작"

# 1. S1/S2 생성
echo "  [1/5] S1/S2 생성 중..."
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP2" \
  --arm G \
  --mode FINAL \
  --stage both \
  --only_group_keys_file temp_selected_groups.txt

# 2. S3 실행
echo "  [2/5] S3 실행 중..."
python3 3_Code/src/03_s3_policy_resolver.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP2" \
  --arm G

# 3. S4 실행
echo "  [3/5] S4 실행 중..."
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP2" \
  --arm G

# 4. S5 검증
echo "  [4/5] S5 검증 중..."
python3 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP2" \
  --arm G

# 5. S5 리포트
echo "  [5/5] S5 리포트 생성 중..."
python3 3_Code/src/tools/s5/s5_report.py \
  --base_dir . \
  --run_tag "$RUN_TAG_REP2" \
  --arm G

echo ">>> rep2 실행 완료"
echo ""
echo "=========================================="
echo "S5R2 실행 완료"
echo "=========================================="


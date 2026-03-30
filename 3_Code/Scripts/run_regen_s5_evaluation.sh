#!/bin/bash
# S5 Regen Evaluation Script
#
# This script runs S5 evaluation for regenerated items:
# - S1R (S1 table regen): Pro model evaluation
# - S2R (S2 card regen): Flash model evaluation
# - S6-S1 (S6 S1 visual regen): Pro model evaluation with images
# - S6-S2 (S6 S2 card regen): Flash model evaluation with images
#
# Usage:
#   bash 3_Code/Scripts/run_regen_s5_evaluation.sh [RUN_TAG] [ARM]
#
# Example:
#   bash 3_Code/Scripts/run_regen_s5_evaluation.sh FINAL_DISTRIBUTION_REGN G

set -e

# Default values
DEFAULT_RUN_TAG="FINAL_DISTRIBUTION_REGN"
DEFAULT_ARM="G"

# Parse arguments
RUN_TAG="${1:-${DEFAULT_RUN_TAG}}"
ARM="${2:-${DEFAULT_ARM}}"
BASE_DIR="${BASE_DIR:-$(pwd)}"

# Ensure BASE_DIR is absolute
if [[ ! "$BASE_DIR" = /* ]]; then
    BASE_DIR="$(cd "$BASE_DIR" && pwd)"
fi

# Paths
DATA_DIR="${BASE_DIR}/2_Data/metadata/generated/${RUN_TAG}"
ARM_UPPER=$(echo "${ARM}" | tr '[:lower:]' '[:upper:]')

echo "=============================================="
echo "S5 Regen Evaluation"
echo "=============================================="
echo "Run Tag: ${RUN_TAG}"
echo "Arm: ${ARM_UPPER}"
echo "Base Dir: ${BASE_DIR}"
echo "Data Dir: ${DATA_DIR}"
echo ""

# Check if data directory exists
if [[ ! -d "${DATA_DIR}" ]]; then
    echo "❌ Error: Data directory not found: ${DATA_DIR}"
    echo "   Please run prepare_regen_s5_evaluation.py first."
    exit 1
fi

# Change to source directory for Python execution
cd "${BASE_DIR}/3_Code/src"

# ============================================================
# 1. S1R Evaluation (S1 table regen - Pro model)
# ============================================================
echo ""
echo "=============================================="
echo "[1] S1R Evaluation (S1 table regen)"
echo "=============================================="
echo "Model: gemini-3-pro-preview"
echo "Mode: s1_only"
echo ""

S1R_OUTPUT="${DATA_DIR}/s5_validation__arm${ARM_UPPER}__s1r.jsonl"
S1R_S1_PATH="${DATA_DIR}/stage1_struct__arm${ARM_UPPER}.jsonl"

if [[ ! -f "${S1R_S1_PATH}" ]]; then
    echo "⚠️  Warning: S1R input file not found: ${S1R_S1_PATH}"
    echo "   Skipping S1R evaluation."
else
    # Remove existing output
    rm -f "${S1R_OUTPUT}"
    
    export S5_S1_TABLE_MODEL="gemini-3-pro-preview"
    export S5_S1_TABLE_THINKING="false"
    export S5_S1_TABLE_RAG_ENABLED="false"
    
    python3 05_s5_validator.py \
        --base_dir "${BASE_DIR}" \
        --run_tag "${RUN_TAG}" \
        --arm "${ARM_UPPER}" \
        --s1_path "${S1R_S1_PATH}" \
        --s5_mode s1_only \
        --output_path "${S1R_OUTPUT}" \
        --workers_s5 1
    
    echo "✅ S1R evaluation complete: ${S1R_OUTPUT}"
fi

# ============================================================
# 2. S2R Evaluation (S2 card regen - Flash model)
# ============================================================
echo ""
echo "=============================================="
echo "[2] S2R Evaluation (S2 card regen)"
echo "=============================================="
echo "Model: gemini-3-flash-preview"
echo "Mode: s2_only"
echo ""

S2R_OUTPUT="${DATA_DIR}/s5_validation__arm${ARM_UPPER}__s2r.jsonl"
S2R_S2_PATH="${DATA_DIR}/s2_results__s1arm${ARM_UPPER}__s2arm${ARM_UPPER}.jsonl"
S2R_PARTIAL="${DATA_DIR}/s5_s1_partial__arm${ARM_UPPER}.jsonl"

if [[ ! -f "${S2R_S2_PATH}" ]]; then
    echo "⚠️  Warning: S2R input file not found: ${S2R_S2_PATH}"
    echo "   Skipping S2R evaluation."
else
    # Check if partial file exists (required for s2_only mode)
    # For S2R, we can use an empty partial file since we're only evaluating S2 cards
    if [[ ! -f "${S2R_PARTIAL}" ]]; then
        echo "ℹ️  Note: Partial file not found: ${S2R_PARTIAL}"
        echo "   Creating empty partial file (S2R evaluation doesn't require S1 partials)."
        touch "${S2R_PARTIAL}"  # Create empty file (code handles empty files gracefully)
    fi
    
    # Remove existing output
    rm -f "${S2R_OUTPUT}"
    
    export S5_S2_CARD_MODEL="gemini-3-flash-preview"
    export S5_S2_CARD_THINKING="false"
    export S5_S2_CARD_RAG_ENABLED="false"
    
    python3 05_s5_validator.py \
        --base_dir "${BASE_DIR}" \
        --run_tag "${RUN_TAG}" \
        --arm "${ARM_UPPER}" \
        --s2_path "${S2R_S2_PATH}" \
        --s5_mode s2_only \
        --output_path "${S2R_OUTPUT}" \
        --workers_s5 4
    
    echo "✅ S2R evaluation complete: ${S2R_OUTPUT}"
fi

# ============================================================
# 3. S6-S1 Evaluation (S6 S1 visual regen - Pro model with images)
# ============================================================
echo ""
echo "=============================================="
echo "[3] S6-S1 Evaluation (S6 S1 visual regen)"
echo "=============================================="
echo "Model: gemini-3-pro-preview"
echo "Mode: s1_only (with images)"
echo ""

S6S1_OUTPUT="${DATA_DIR}/s5_validation__arm${ARM_UPPER}__s6s1.jsonl"
S6S1_S1_PATH="${DATA_DIR}/stage1_struct__arm${ARM_UPPER}.jsonl"
S6S1_S3_SPEC="${DATA_DIR}/s3_image_spec__arm${ARM_UPPER}__s1_visual.jsonl"
S6S1_S4_MANIFEST="${DATA_DIR}/s4_image_manifest__arm${ARM_UPPER}__s1_visual.jsonl"
S6S1_S3_STANDARD="${DATA_DIR}/s3_image_spec__arm${ARM_UPPER}.jsonl"
S6S1_S4_STANDARD="${DATA_DIR}/s4_image_manifest__arm${ARM_UPPER}.jsonl"

if [[ ! -f "${S6S1_S1_PATH}" ]] || [[ ! -f "${S6S1_S3_SPEC}" ]] || [[ ! -f "${S6S1_S4_MANIFEST}" ]]; then
    echo "⚠️  Warning: S6-S1 input files not found:"
    [[ ! -f "${S6S1_S1_PATH}" ]] && echo "   - ${S6S1_S1_PATH}"
    [[ ! -f "${S6S1_S3_SPEC}" ]] && echo "   - ${S6S1_S3_SPEC}"
    [[ ! -f "${S6S1_S4_MANIFEST}" ]] && echo "   - ${S6S1_S4_MANIFEST}"
    echo "   Skipping S6-S1 evaluation."
else
    # Create temporary symlinks to expected file names
    # (S5 validator expects s3_image_spec__arm{X}.jsonl and s4_image_manifest__arm{X}.jsonl)
    ln -sf "$(basename "${S6S1_S3_SPEC}")" "${S6S1_S3_STANDARD}" 2>/dev/null || cp "${S6S1_S3_SPEC}" "${S6S1_S3_STANDARD}"
    ln -sf "$(basename "${S6S1_S4_MANIFEST}")" "${S6S1_S4_STANDARD}" 2>/dev/null || cp "${S6S1_S4_MANIFEST}" "${S6S1_S4_STANDARD}"
    
    # Remove existing output
    rm -f "${S6S1_OUTPUT}"
    
    export S5_S1_TABLE_MODEL="gemini-3-pro-preview"
    export S5_S1_TABLE_THINKING="false"
    export S5_S1_TABLE_RAG_ENABLED="false"
    
    python3 05_s5_validator.py \
        --base_dir "${BASE_DIR}" \
        --run_tag "${RUN_TAG}" \
        --arm "${ARM_UPPER}" \
        --s1_path "${S6S1_S1_PATH}" \
        --s5_mode s1_only \
        --output_path "${S6S1_OUTPUT}" \
        --workers_s5 1
    
    # Clean up temporary symlinks/files
    [[ -L "${S6S1_S3_STANDARD}" ]] && rm -f "${S6S1_S3_STANDARD}"
    [[ -L "${S6S1_S4_STANDARD}" ]] && rm -f "${S6S1_S4_STANDARD}"
    [[ -f "${S6S1_S3_STANDARD}" && ! -L "${S6S1_S3_STANDARD}" ]] && rm -f "${S6S1_S3_STANDARD}"
    [[ -f "${S6S1_S4_STANDARD}" && ! -L "${S6S1_S4_STANDARD}" ]] && rm -f "${S6S1_S4_STANDARD}"
    
    echo "✅ S6-S1 evaluation complete: ${S6S1_OUTPUT}"
fi

# ============================================================
# 4. S6-S2 Evaluation (S6 S2 card regen - Flash model with images)
# ============================================================
echo ""
echo "=============================================="
echo "[4] S6-S2 Evaluation (S6 S2 card regen)"
echo "=============================================="
echo "Model: gemini-3-flash-preview"
echo "Mode: s2_only (with images)"
echo ""

S6S2_OUTPUT="${DATA_DIR}/s5_validation__arm${ARM_UPPER}__s6s2.jsonl"
S6S2_S2_PATH="${DATA_DIR}/s2_results__s1arm${ARM_UPPER}__s2arm${ARM_UPPER}.jsonl"
S6S2_S3_SPEC="${DATA_DIR}/s3_image_spec__arm${ARM_UPPER}__s2_card.jsonl"
S6S2_S4_MANIFEST="${DATA_DIR}/s4_image_manifest__arm${ARM_UPPER}__s2_card.jsonl"
S6S2_S3_STANDARD="${DATA_DIR}/s3_image_spec__arm${ARM_UPPER}.jsonl"
S6S2_S4_STANDARD="${DATA_DIR}/s4_image_manifest__arm${ARM_UPPER}.jsonl"
S6S2_PARTIAL="${DATA_DIR}/s5_s1_partial__arm${ARM_UPPER}.jsonl"

if [[ ! -f "${S6S2_S2_PATH}" ]] || [[ ! -f "${S6S2_S3_SPEC}" ]] || [[ ! -f "${S6S2_S4_MANIFEST}" ]]; then
    echo "⚠️  Warning: S6-S2 input files not found:"
    [[ ! -f "${S6S2_S2_PATH}" ]] && echo "   - ${S6S2_S2_PATH}"
    [[ ! -f "${S6S2_S3_SPEC}" ]] && echo "   - ${S6S2_S3_SPEC}"
    [[ ! -f "${S6S2_S4_MANIFEST}" ]] && echo "   - ${S6S2_S4_MANIFEST}"
    echo "   Skipping S6-S2 evaluation."
else
    # Check if partial file exists (required for s2_only mode)
    # For S6-S2, we can use an empty partial file since S6-S1 runs separately
    if [[ ! -f "${S6S2_PARTIAL}" ]]; then
        echo "ℹ️  Note: Partial file not found: ${S6S2_PARTIAL}"
        echo "   Creating empty partial file (S6-S2 evaluation will proceed without S1 partials)."
        touch "${S6S2_PARTIAL}"  # Create empty file (code handles empty files gracefully)
    fi
    
    # Create temporary symlinks to expected file names
    ln -sf "$(basename "${S6S2_S3_SPEC}")" "${S6S2_S3_STANDARD}" 2>/dev/null || cp "${S6S2_S3_SPEC}" "${S6S2_S3_STANDARD}"
    ln -sf "$(basename "${S6S2_S4_MANIFEST}")" "${S6S2_S4_STANDARD}" 2>/dev/null || cp "${S6S2_S4_MANIFEST}" "${S6S2_S4_STANDARD}"
    
    # Remove existing output
    rm -f "${S6S2_OUTPUT}"
    
    export S5_S2_CARD_MODEL="gemini-3-flash-preview"
    export S5_S2_CARD_THINKING="false"
    export S5_S2_CARD_RAG_ENABLED="false"
    
    python3 05_s5_validator.py \
        --base_dir "${BASE_DIR}" \
        --run_tag "${RUN_TAG}" \
        --arm "${ARM_UPPER}" \
        --s2_path "${S6S2_S2_PATH}" \
        --s5_mode s2_only \
        --output_path "${S6S2_OUTPUT}" \
        --workers_s5 4
    
    # Clean up temporary symlinks/files
    [[ -L "${S6S2_S3_STANDARD}" ]] && rm -f "${S6S2_S3_STANDARD}"
    [[ -L "${S6S2_S4_STANDARD}" ]] && rm -f "${S6S2_S4_STANDARD}"
    [[ -f "${S6S2_S3_STANDARD}" && ! -L "${S6S2_S3_STANDARD}" ]] && rm -f "${S6S2_S3_STANDARD}"
    [[ -f "${S6S2_S4_STANDARD}" && ! -L "${S6S2_S4_STANDARD}" ]] && rm -f "${S6S2_S4_STANDARD}"
    
    echo "✅ S6-S2 evaluation complete: ${S6S2_OUTPUT}"
fi

# ============================================================
# Summary
# ============================================================
echo ""
echo "=============================================="
echo "S5 Regen Evaluation Complete"
echo "=============================================="
echo ""
echo "Output files:"
[[ -f "${S1R_OUTPUT}" ]] && echo "  ✅ S1R: ${S1R_OUTPUT}"
[[ -f "${S2R_OUTPUT}" ]] && echo "  ✅ S2R: ${S2R_OUTPUT}"
[[ -f "${S6S1_OUTPUT}" ]] && echo "  ✅ S6-S1: ${S6S1_OUTPUT}"
[[ -f "${S6S2_OUTPUT}" ]] && echo "  ✅ S6-S2: ${S6S2_OUTPUT}"
echo ""


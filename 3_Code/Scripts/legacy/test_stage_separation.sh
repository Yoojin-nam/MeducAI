#!/bin/bash
# Test S1/S2 stage separation: Run all 6 arms with stage 1, then stage 2

set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$BASE_DIR"

RUN_TAG="TEST_STAGE_SEP_$(date +%Y%m%d_%H%M%S)"
echo "=========================================="
echo "Testing Stage Separation"
echo "RUN_TAG: $RUN_TAG"
echo "=========================================="
echo

# Stage 1: Run all 6 arms
echo "=== Stage 1: Running all 6 arms ==="
for arm in A B C D E F; do
    echo
    echo "--- Arm $arm (Stage 1) ---"
    python3 3_Code/src/01_generate_json.py \
        --base_dir . \
        --run_tag "$RUN_TAG" \
        --arm "$arm" \
        --mode S0 \
        --stage 1 \
        --sample 1 \
        --seed 42
    
    if [ $? -ne 0 ]; then
        echo "❌ Arm $arm (Stage 1) failed"
        exit 1
    fi
    echo "✅ Arm $arm (Stage 1) completed"
done

echo
echo "=== Stage 1 completed for all arms ==="
echo

# Verify S1 outputs exist
echo "=== Verifying S1 outputs ==="
for arm in A B C D E F; do
    stage1_struct="2_Data/metadata/generated/$RUN_TAG/stage1_struct__arm${arm}.jsonl"
    if [ ! -f "$stage1_struct" ]; then
        echo "❌ Missing S1 output for arm $arm: $stage1_struct"
        exit 1
    fi
    line_count=$(wc -l < "$stage1_struct" | tr -d ' ')
    if [ "$line_count" -eq 0 ]; then
        echo "❌ Empty S1 output for arm $arm"
        exit 1
    fi
    echo "✅ Arm $arm: S1 output exists ($line_count lines)"
done

echo
echo "=== Stage 2: Running all 6 arms ==="
for arm in A B C D E F; do
    echo
    echo "--- Arm $arm (Stage 2) ---"
    python3 3_Code/src/01_generate_json.py \
        --base_dir . \
        --run_tag "$RUN_TAG" \
        --arm "$arm" \
        --mode S0 \
        --stage 2 \
        --sample 1 \
        --seed 42
    
    if [ $? -ne 0 ]; then
        echo "❌ Arm $arm (Stage 2) failed"
        exit 1
    fi
    echo "✅ Arm $arm (Stage 2) completed"
done

echo
echo "=== Stage 2 completed for all arms ==="
echo

# Verify S2 outputs exist
echo "=== Verifying S2 outputs ==="
for arm in A B C D E F; do
    s2_results="2_Data/metadata/generated/$RUN_TAG/s2_results__arm${arm}.jsonl"
    if [ ! -f "$s2_results" ]; then
        echo "❌ Missing S2 output for arm $arm: $s2_results"
        exit 1
    fi
    line_count=$(wc -l < "$s2_results" | tr -d ' ')
    if [ "$line_count" -eq 0 ]; then
        echo "❌ Empty S2 output for arm $arm"
        exit 1
    fi
    echo "✅ Arm $arm: S2 output exists ($line_count lines)"
done

echo
echo "=========================================="
echo "✅ All tests passed!"
echo "RUN_TAG: $RUN_TAG"
echo "=========================================="


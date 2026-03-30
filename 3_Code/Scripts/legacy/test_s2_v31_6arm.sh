#!/bin/bash
# Test S2 v3.1 (card_role, image_hint) with 6 arms, 1 sample each

set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$BASE_DIR"

RUN_TAG="TEST_S2_V31_$(date +%Y%m%d_%H%M%S)"
echo "=========================================="
echo "Testing S2 v3.1 (card_role, image_hint)"
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
        --sample 1
    
    if [ $? -ne 0 ]; then
        echo "❌ Arm $arm (Stage 1) failed"
        exit 1
    fi
    echo "✅ Arm $arm (Stage 1) completed"
done

echo
echo "=== S1 Gate Validation ==="
PASSED_ARMS=()
for arm in A B C D E F; do
    echo "--- Arm $arm (S1 Gate) ---"
    python3 3_Code/src/tools/qa/validate_stage1_struct.py \
        --base_dir . \
        --run_tag "$RUN_TAG" \
        --arm "$arm"
    
    if [ $? -eq 0 ]; then
        echo "✅ Arm $arm (S1 Gate) passed"
        PASSED_ARMS+=("$arm")
    else
        echo "⚠️  Arm $arm (S1 Gate) failed - skipping S2 for this arm"
    fi
done

if [ ${#PASSED_ARMS[@]} -eq 0 ]; then
    echo "❌ No arms passed S1 Gate validation"
    exit 1
fi

echo "✅ S1 Gate passed for arms: ${PASSED_ARMS[*]}"

echo
echo "=== S0 Allocation Generation ==="
for arm in "${PASSED_ARMS[@]}"; do
    echo "--- Arm $arm (Allocation) ---"
    python3 3_Code/src/tools/allocation/s0_allocation.py \
        --base_dir . \
        --run_tag "$RUN_TAG" \
        --arm "$arm"
    
    if [ $? -ne 0 ]; then
        echo "❌ Arm $arm (Allocation) failed"
        exit 1
    fi
    echo "✅ Arm $arm (Allocation) completed"
done

echo
echo "=== Stage 2: Running S2 v3.1 for passed arms ==="
for arm in "${PASSED_ARMS[@]}"; do
    echo
    echo "--- Arm $arm (Stage 2) ---"
    python3 3_Code/src/01_generate_json.py \
        --base_dir . \
        --run_tag "$RUN_TAG" \
        --arm "$arm" \
        --mode S0 \
        --stage 2 \
        --sample 1
    
    if [ $? -ne 0 ]; then
        echo "❌ Arm $arm (Stage 2) failed"
        exit 1
    fi
    echo "✅ Arm $arm (Stage 2) completed"
done

echo
echo "=== Verifying S2 outputs ==="
for arm in "${PASSED_ARMS[@]}"; do
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
    
    # Check for card_role and image_hint in output
    if grep -q '"card_role"' "$s2_results" && grep -q '"image_hint"' "$s2_results"; then
        echo "   ✅ card_role and image_hint found in output"
    else
        echo "   ⚠️  card_role or image_hint missing in output"
    fi
done

echo
echo "=========================================="
echo "✅ All tests completed successfully!"
echo "RUN_TAG: $RUN_TAG"
echo "Results: 2_Data/metadata/generated/$RUN_TAG/"
echo "=========================================="


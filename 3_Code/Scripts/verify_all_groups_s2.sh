#!/bin/bash
# Verification script for all groups S2 execution
# Verifies that card_count_mismatch errors are 0 for all groups

set -e

cd /path/to/workspace/workspace/MeducAI

RUN_TAG="smoke_4groups_20251226_123809"
ARM="G"

echo "=========================================="
echo "S2 All Groups Verification"
echo "=========================================="
echo "RUN_TAG: ${RUN_TAG}"
echo "ARM: ${ARM}"
echo ""

# Check result file
RESULT_FILE="2_Data/metadata/generated/${RUN_TAG}/s2_results__s1arm${ARM}__s2arm${ARM}.jsonl"

if [ ! -f "${RESULT_FILE}" ]; then
    echo "❌ Result file not found: ${RESULT_FILE}"
    echo "Please run S2 execution first."
    exit 1
fi

# Count total entities
TOTAL_ENTITIES=$(wc -l < "${RESULT_FILE}" | tr -d ' ')
echo "Total entities in result file: ${TOTAL_ENTITIES}"

# Count by group
echo ""
echo "Entities by group:"
grep -o '"group_id":"[^"]*"' "${RESULT_FILE}" | sort | uniq -c | sort -rn

# Check for card_count_mismatch in logs
LOG_DIR="2_Data/metadata/generated/${RUN_TAG}/logs"
RETRY_LOG="${LOG_DIR}/llm_schema_retry_log.jsonl"

if [ -f "${RETRY_LOG}" ]; then
    echo ""
    echo "Checking retry log for errors..."
    
    # Count card_count_mismatch errors
    MISMATCH_COUNT=$(grep -c '"error_type":"card_count_mismatch"' "${RETRY_LOG}" || echo "0")
    echo "card_count_mismatch errors in retry log: ${MISMATCH_COUNT}"
    
    if [ "${MISMATCH_COUNT}" -eq 0 ]; then
        echo "✅ No card_count_mismatch errors found in retry log!"
    else
        echo "❌ Found ${MISMATCH_COUNT} card_count_mismatch errors"
        echo ""
        echo "Error details (first 5):"
        grep '"error_type":"card_count_mismatch"' "${RETRY_LOG}" | head -5 | jq -r '.entity_name + ": " + .error_summary' 2>/dev/null || \
        grep '"error_type":"card_count_mismatch"' "${RETRY_LOG}" | head -5
    fi
    
    # Count total errors
    TOTAL_ERRORS=$(grep -c '"success":false' "${RETRY_LOG}" || echo "0")
    echo ""
    echo "Total validation errors: ${TOTAL_ERRORS}"
    
    if [ "${TOTAL_ERRORS}" -gt 0 ]; then
        echo "Error breakdown by type:"
        grep '"success":false' "${RETRY_LOG}" | grep -o '"error_type":"[^"]*"' | sort | uniq -c | sort -rn
    fi
else
    echo ""
    echo "⚠️  Retry log not found: ${RETRY_LOG}"
    echo "This is normal if no validation errors occurred."
fi

# Expected entity count per group (from handoff document)
# grp_2155b4f5c3: 14
# grp_cbcba66e24: 16
# grp_f073599bec: 19
# grp_fb292cfd1d: 19
# Total: 68

EXPECTED_TOTAL=68
echo ""
echo "Expected total entities: ${EXPECTED_TOTAL}"
echo "Actual total entities: ${TOTAL_ENTITIES}"

if [ "${TOTAL_ENTITIES}" -eq "${EXPECTED_TOTAL}" ]; then
    echo "✅ Entity count matches expected value!"
elif [ "${TOTAL_ENTITIES}" -gt 0 ]; then
    echo "⚠️  Entity count differs from expected (${EXPECTED_TOTAL})"
else
    echo "❌ No entities found in result file"
fi

echo ""
echo "=========================================="
echo "Verification Complete"
echo "=========================================="


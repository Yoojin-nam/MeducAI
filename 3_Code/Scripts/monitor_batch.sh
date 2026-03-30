#!/bin/bash
# Monitor S5 batch job until completion

cd /path/to/workspace/workspace/MeducAI

echo "======================================"
echo "S5 Batch Monitor - Started"
echo "======================================"
echo ""

MAX_CHECKS=120  # 2 hours (120 checks * 60 seconds)
CHECK_COUNT=0

while [ $CHECK_COUNT -lt $MAX_CHECKS ]; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Checking batch status (check $((CHECK_COUNT + 1))/$MAX_CHECKS)..."
    
    # Run status check and capture output
    OUTPUT=$(python3 3_Code/src/tools/batch/batch_s5_validator.py --check_status 2>&1)
    
    # Check if succeeded
    if echo "$OUTPUT" | grep -q "JOB_STATE_SUCCEEDED"; then
        echo ""
        echo "======================================"
        echo "SUCCESS! Batch job completed!"
        echo "======================================"
        echo ""
        echo "$OUTPUT"
        echo ""
        echo "Results have been downloaded and merged to s5_validation__armG.jsonl"
        exit 0
    fi
    
    # Check if failed
    if echo "$OUTPUT" | grep -q "JOB_STATE_FAILED"; then
        echo ""
        echo "======================================"
        echo "ERROR! Batch job failed!"
        echo "======================================"
        echo ""
        echo "$OUTPUT"
        exit 1
    fi
    
    # Check if running
    if echo "$OUTPUT" | grep -q "JOB_STATE_RUNNING"; then
        echo "  Status: RUNNING (in progress...)"
    elif echo "$OUTPUT" | grep -q "JOB_STATE_PENDING"; then
        echo "  Status: PENDING (waiting to start...)"
    else
        echo "  Status: Unknown"
    fi
    
    CHECK_COUNT=$((CHECK_COUNT + 1))
    
    # Wait 60 seconds before next check
    if [ $CHECK_COUNT -lt $MAX_CHECKS ]; then
        sleep 60
    fi
done

echo ""
echo "======================================"
echo "Timeout: Batch not completed after 2 hours"
echo "======================================"
echo "Run manual check:"
echo "  python3 3_Code/src/tools/batch/batch_s5_validator.py --check_status"
exit 1


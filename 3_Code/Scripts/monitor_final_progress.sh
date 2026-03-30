#!/bin/bash
# Monitor FINAL mode pipeline progress
#
# Usage:
#   ./monitor_final_progress.sh <RUN_TAG>
#
# If RUN_TAG is not provided, shows progress for the most recent FINAL run

if [ -z "$1" ]; then
    # Find most recent FINAL run
    RUN_TAG=$(ls -t 2_Data/metadata/generated/ | grep "^FINAL_armG_" | head -1)
    if [ -z "$RUN_TAG" ]; then
        echo "No FINAL run found. Please provide RUN_TAG."
        exit 1
    fi
    echo "Using most recent run: $RUN_TAG"
else
    RUN_TAG="$1"
fi

RUN_DIR="2_Data/metadata/generated/$RUN_TAG"

if [ ! -d "$RUN_DIR" ]; then
    echo "Error: Run directory not found: $RUN_DIR"
    exit 1
fi

echo "=========================================="
echo "Pipeline Progress Monitor"
echo "Run Tag: $RUN_TAG"
echo "=========================================="
echo ""

# Check tmux session
if tmux has-session -t meducai_final 2>/dev/null; then
    echo "✓ tmux session 'meducai_final' is running"
else
    echo "⚠ tmux session 'meducai_final' not found (may have completed or not started)"
fi
echo ""

# Check output files
echo "Output Files:"
echo "------------"

# S1/S2
if [ -f "$RUN_DIR/stage1_struct__armG.jsonl" ]; then
    S1_COUNT=$(wc -l < "$RUN_DIR/stage1_struct__armG.jsonl" | tr -d ' ')
    echo "✓ S1: $S1_COUNT groups"
else
    echo "✗ S1: Not started"
fi

if [ -f "$RUN_DIR/s2_results__s1armG__s2armG.jsonl" ]; then
    S2_COUNT=$(wc -l < "$RUN_DIR/s2_results__s1armG__s2armG.jsonl" | tr -d ' ')
    echo "✓ S2: $S2_COUNT entities"
else
    echo "✗ S2: Not started"
fi

# S3
if [ -f "$RUN_DIR/s3_image_spec__armG.jsonl" ]; then
    S3_COUNT=$(wc -l < "$RUN_DIR/s3_image_spec__armG.jsonl" | tr -d ' ')
    echo "✓ S3: $S3_COUNT image specs"
else
    echo "✗ S3: Not started"
fi

# S4
if [ -f "$RUN_DIR/s4_image_manifest__armG.jsonl" ]; then
    S4_COUNT=$(wc -l < "$RUN_DIR/s4_image_manifest__armG.jsonl" | tr -d ' ')
    echo "✓ S4: $S4_COUNT images"
else
    echo "✗ S4: Not started"
fi

# S5
if [ -f "$RUN_DIR/s5_validation__armG.jsonl" ]; then
    S5_COUNT=$(wc -l < "$RUN_DIR/s5_validation__armG.jsonl" | tr -d ' ')
    echo "✓ S5: $S5_COUNT validations"
else
    echo "✗ S5: Not started"
fi

echo ""
echo "=========================================="
echo "Quick Commands:"
echo "  View logs:        tail -f $RUN_DIR/logs/*.log"
echo "  Attach tmux:      tmux attach -t meducai_final"
echo "  Check files:      ls -lh $RUN_DIR/*.jsonl"
echo "=========================================="


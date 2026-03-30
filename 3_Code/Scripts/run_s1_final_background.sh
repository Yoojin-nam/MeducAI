#!/bin/bash
# MeducAI S1 FINAL Mode - Background Execution Script
# 
# Usage:
#   ./run_s1_final_background.sh
#
# This script runs S1 (Stage 1) only in FINAL mode
# in a tmux session with caffeinate to prevent sleep.

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Generate run tag
RUN_TAG="FINAL_S1_armG_$(date +%Y%m%d_%H%M%S)"
echo -e "${GREEN}Run tag: $RUN_TAG${NC}"

# Check if tmux session already exists
if tmux has-session -t meducai_s1 2>/dev/null; then
    echo -e "${YELLOW}Warning: tmux session 'meducai_s1' already exists.${NC}"
    echo "Attach with: tmux attach -t meducai_s1"
    echo "Or kill it with: tmux kill-session -t meducai_s1"
    exit 1
fi

# Create tmux session
tmux new-session -d -s meducai_s1 -c "$(pwd)"

# Create log directory
LOG_DIR="2_Data/metadata/generated/$RUN_TAG/logs"
mkdir -p "$LOG_DIR"

# Run S1 in tmux with caffeinate
echo -e "${GREEN}[S1] Starting...${NC}"
echo "Command: python3 3_Code/src/01_generate_json.py --base_dir . --run_tag $RUN_TAG --arm G --mode FINAL --stage 1 --provider gemini"

tmux send-keys -t meducai_s1 "echo '========================================'" Enter
tmux send-keys -t meducai_s1 "echo '[S1] Started at \$(date)'" Enter
tmux send-keys -t meducai_s1 "echo 'Run tag: $RUN_TAG'" Enter
tmux send-keys -t meducai_s1 "echo '========================================'" Enter
tmux send-keys -t meducai_s1 "caffeinate -s python3 3_Code/src/01_generate_json.py --base_dir . --run_tag $RUN_TAG --arm G --mode FINAL --stage 1 --provider gemini 2>&1 | tee $LOG_DIR/S1.log" Enter
tmux send-keys -t meducai_s1 "echo ''" Enter
tmux send-keys -t meducai_s1 "echo '========================================'" Enter
tmux send-keys -t meducai_s1 "echo '[S1] Completed at \$(date)'" Enter
tmux send-keys -t meducai_s1 "echo 'Output: 2_Data/metadata/generated/$RUN_TAG/stage1_struct__armG.jsonl'" Enter
tmux send-keys -t meducai_s1 "echo '========================================'" Enter

echo ""
echo -e "${GREEN}✓ S1 started in tmux session 'meducai_s1'${NC}"
echo ""
echo "Useful commands:"
echo "  Attach to session:    ${YELLOW}tmux attach -t meducai_s1${NC}"
echo "  Detach from session:  ${YELLOW}Ctrl+B, then D${NC}"
echo "  View logs:            ${YELLOW}tail -f $LOG_DIR/S1.log${NC}"
echo "  Check progress:       ${YELLOW}wc -l 2_Data/metadata/generated/$RUN_TAG/stage1_struct__armG.jsonl${NC}"
echo "  Kill session:         ${YELLOW}tmux kill-session -t meducai_s1${NC}"
echo ""
echo "Note: caffeinate prevents macOS from sleeping while S1 runs."
echo "      The process will continue even if you detach from tmux."


#!/bin/bash
# MeducAI FINAL Mode - Background Execution Script
#
# Usage:
#   bash 3_Code/Scripts/run_final_background.sh
#
# This script runs the full pipeline (S1/S2/S3/S4/S5) in FINAL mode
# in a tmux session with caffeinate to prevent sleep.
#
# Reliability note:
# - macOS true sleep stops CPU; this script prevents sleep instead.
# - caffeinate is kept active for the entire pipeline (no gaps between steps).

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

if ! command -v tmux >/dev/null 2>&1; then
  echo -e "${RED}Error:${NC} tmux is not installed."
  echo "Install (Homebrew): brew install tmux"
  exit 1
fi

if ! command -v caffeinate >/dev/null 2>&1; then
  echo -e "${RED}Error:${NC} caffeinate not found (macOS only)."
  exit 1
fi

# Repo root
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Fixed arm/provider for FINAL script (can be generalized later)
ARM="G"
PROVIDER="gemini"

# Generate run tag
RUN_TAG="FINAL_arm${ARM}_$(date +%Y%m%d_%H%M%S)"
echo -e "${GREEN}Run tag:${NC} $RUN_TAG"

# Check if tmux session already exists
if tmux has-session -t meducai_final 2>/dev/null; then
  echo -e "${YELLOW}Warning:${NC} tmux session 'meducai_final' already exists."
  echo "Attach with: tmux attach -t meducai_final"
  echo "Or kill it with: tmux kill-session -t meducai_final"
  exit 1
fi

# Create log directory
LOG_DIR="$BASE_DIR/2_Data/metadata/generated/$RUN_TAG/logs"
mkdir -p "$LOG_DIR"

JOB_SCRIPT="3_Code/Scripts/_final_tmux_job.sh"
if [[ ! -f "$BASE_DIR/$JOB_SCRIPT" ]]; then
  echo -e "${RED}Error:${NC} Missing job script: $BASE_DIR/$JOB_SCRIPT"
  exit 1
fi

# Create tmux session and run one long caffeinate-wrapped job
tmux new-session -d -s meducai_final -c "$BASE_DIR" \
  "RUN_TAG=\"$RUN_TAG\" ARM=\"$ARM\" BASE_DIR=\"$BASE_DIR\" LOG_DIR=\"$LOG_DIR\" PROVIDER=\"$PROVIDER\" bash -lc 'set +e; caffeinate -s -i -m -u bash \"$JOB_SCRIPT\"; status=$?; echo \"\"; echo \"[tmux-job] Exit code: $status\"; echo $status > \"$LOG_DIR/final_exit_code.txt\"; echo \"[tmux-job] Wrote: $LOG_DIR/final_exit_code.txt\"; exec bash -l'"

echo ""
echo -e "${GREEN}✓ Pipeline started in tmux session 'meducai_final'${NC}"
echo ""
echo "Useful commands:"
echo "  Attach to session:    ${YELLOW}tmux attach -t meducai_final${NC}"
echo "  Detach from session:  ${YELLOW}Ctrl+B, then D${NC}"
echo "  View logs:            ${YELLOW}tail -f $LOG_DIR/*.log${NC}"
echo "  Check progress:       ${YELLOW}ls -lh 2_Data/metadata/generated/$RUN_TAG/*.jsonl${NC}"
echo "  Kill session:         ${YELLOW}tmux kill-session -t meducai_final${NC}"
echo ""
echo "Note: caffeinate prevents macOS from sleeping while the pipeline runs."
echo "      Display can still sleep; true system sleep (or closing lid) will pause computation."


#!/bin/bash
# MeducAI S3/S4 - Background Execution Script (macOS overnight-safe)
#
# Runs S3 -> S4 for an existing RUN_TAG in a tmux session.
# Uses caffeinate to prevent macOS system sleep while the long-running job executes.
#
# Usage:
#   bash 3_Code/Scripts/run_s3_s4_background.sh --run_tag <RUN_TAG> [--arm G] [--resume_s4] [--skip_s3]
#
# Examples:
#   bash 3_Code/Scripts/run_s3_s4_background.sh --run_tag "FINAL_armG_20260101_010203" --arm G
#   bash 3_Code/Scripts/run_s3_s4_background.sh --run_tag "DEV_armG_xxx" --arm G --resume_s4
#
# Notes:
# - macOS "Sleep" stops CPU; you cannot run during true sleep. This script prevents sleep instead.
# - For best reliability, keep the Mac on AC power. Closing the laptop lid may still force sleep.

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

usage() {
  cat <<'EOF'
Usage:
  bash 3_Code/Scripts/run_s3_s4_background.sh --run_tag <RUN_TAG> [--arm G] [--resume_s4] [--skip_s3] [--session <NAME>]

Options:
  --run_tag <RUN_TAG>   Required. Existing run tag under 2_Data/metadata/generated/<RUN_TAG>
  --arm <ARM>           Optional. Default: G
  --resume_s4           Optional. Passes --resume to S4 to retry only failed images from existing manifest
  --skip_s3             Optional. Skip S3 and run S4 only (useful when s3_image_spec already exists)
  --session <NAME>      Optional. tmux session name (auto-generated if omitted)
EOF
}

if ! command -v tmux >/dev/null 2>&1; then
  echo -e "${RED}Error:${NC} tmux is not installed."
  echo "Install (Homebrew): brew install tmux"
  exit 1
fi

if ! command -v caffeinate >/dev/null 2>&1; then
  echo -e "${RED}Error:${NC} caffeinate not found (macOS only)."
  exit 1
fi

RUN_TAG=""
ARM="G"
RESUME_S4="0"
SKIP_S3="0"
SESSION_NAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run_tag)
      RUN_TAG="${2:-}"; shift 2 ;;
    --arm)
      ARM="${2:-}"; shift 2 ;;
    --resume_s4)
      RESUME_S4="1"; shift 1 ;;
    --skip_s3)
      SKIP_S3="1"; shift 1 ;;
    --session)
      SESSION_NAME="${2:-}"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo -e "${RED}Error:${NC} Unknown argument: $1"
      usage
      exit 1 ;;
  esac
done

RUN_TAG="$(echo "$RUN_TAG" | xargs)"
ARM="$(echo "$ARM" | tr '[:lower:]' '[:upper:]' | xargs)"

if [[ -z "$RUN_TAG" ]]; then
  echo -e "${RED}Error:${NC} --run_tag is required."
  usage
  exit 1
fi

# Repo root
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_DIR="$BASE_DIR/2_Data/metadata/generated/$RUN_TAG"

if [[ ! -d "$RUN_DIR" ]]; then
  echo -e "${RED}Error:${NC} Run directory not found: $RUN_DIR"
  echo "Did you type the correct RUN_TAG?"
  exit 1
fi

LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

# Default session name (sanitized)
if [[ -z "$SESSION_NAME" ]]; then
  SAFE_RUN_TAG="$(echo "$RUN_TAG" | tr -cs '[:alnum:]' '_' | sed 's/^_//;s/_$//')"
  SESSION_NAME="meducai_s3s4_${ARM}_${SAFE_RUN_TAG}"
fi

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  echo -e "${YELLOW}Warning:${NC} tmux session '$SESSION_NAME' already exists."
  echo "Attach with: tmux attach -t $SESSION_NAME"
  echo "Or kill it with: tmux kill-session -t $SESSION_NAME"
  exit 1
fi

echo -e "${GREEN}Run tag:${NC} $RUN_TAG"
echo -e "${GREEN}Arm:${NC} $ARM"
echo -e "${GREEN}tmux session:${NC} $SESSION_NAME"
echo -e "${GREEN}Logs:${NC} $LOG_DIR/{S3.log,S4.log}"

# Create tmux session and run (single long-running command under caffeinate; no gaps)
JOB_SCRIPT="3_Code/Scripts/_s3_s4_tmux_job.sh"
if [[ ! -f "$BASE_DIR/$JOB_SCRIPT" ]]; then
  echo -e "${RED}Error:${NC} Missing job script: $BASE_DIR/$JOB_SCRIPT"
  exit 1
fi

tmux new-session -d -s "$SESSION_NAME" -c "$BASE_DIR" \
  "RUN_TAG=\"$RUN_TAG\" ARM=\"$ARM\" BASE_DIR=\"$BASE_DIR\" LOG_DIR=\"$LOG_DIR\" RESUME_S4=\"$RESUME_S4\" SKIP_S3=\"$SKIP_S3\" bash -lc 'set +e; caffeinate -s -i -m -u bash \"$JOB_SCRIPT\"; status=$?; echo \"\"; echo \"[tmux-job] Exit code: $status\"; echo $status > \"$LOG_DIR/s3s4_exit_code.txt\"; echo \"[tmux-job] Wrote: $LOG_DIR/s3s4_exit_code.txt\"; exec bash -l'"

echo ""
echo -e "${GREEN}✓ S3/S4 started in tmux session '$SESSION_NAME'${NC}"
echo ""
echo "Useful commands:"
echo "  Attach to session:    ${YELLOW}tmux attach -t $SESSION_NAME${NC}"
echo "  Detach from session:  ${YELLOW}Ctrl+B, then D${NC}"
echo "  View logs:            ${YELLOW}tail -f $LOG_DIR/S3.log $LOG_DIR/S4.log${NC}"
echo "  Monitor outputs:      ${YELLOW}ls -lh $RUN_DIR/s3_image_spec__arm${ARM}.jsonl $RUN_DIR/s4_image_manifest__arm${ARM}.jsonl${NC}"
echo "  Kill session:         ${YELLOW}tmux kill-session -t $SESSION_NAME${NC}"
echo ""
echo "Note: caffeinate prevents macOS from sleeping while S3/S4 runs."
echo "      Display can still sleep; true system sleep (or closing lid) will pause computation."



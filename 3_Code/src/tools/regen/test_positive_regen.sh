#!/bin/bash
#
# Positive Regen Pipeline - Dry-Run Test Script
#
# This script tests the S6 Positive Instruction Agent and Full Pipeline Orchestrator
# in dry-run mode (no actual LLM calls or image generation).
#
# Usage:
#   bash 3_Code/src/tools/regen/test_positive_regen.sh
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

echo "=========================================="
echo "Positive Regen Pipeline - Dry-Run Tests"
echo "=========================================="
echo ""
echo "Project root: $PROJECT_ROOT"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Test 1: S6 Agent - Single Card Test
echo "=========================================="
echo "Test 1: S6 Agent - Single Card Test"
echo "=========================================="
echo ""
echo "Testing S6 agent on a single card with low image score..."
echo ""

python3 3_Code/src/06_s6_positive_instruction_agent.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --group_id grp_023d60ba08 \
  --entity_id DERIVED:9bdeff847613 \
  --card_role Q1 \
  --dry_run

echo ""
echo "✅ Test 1 passed: S6 agent single card test"
echo ""
sleep 2

# Test 2: Full Pipeline - Single Entity
echo "=========================================="
echo "Test 2: Full Pipeline - Single Entity"
echo "=========================================="
echo ""
echo "Testing full pipeline orchestrator with one entity..."
echo ""

python3 3_Code/src/tools/regen/positive_regen_runner.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --threshold 80.0 \
  --dry_run \
  --only_entity_id DERIVED:9bdeff847613

echo ""
echo "✅ Test 2 passed: Full pipeline single entity"
echo ""
sleep 2

# Test 3: Full Pipeline - Multiple Entities
echo "=========================================="
echo "Test 3: Full Pipeline - Multiple Entities"
echo "=========================================="
echo ""
echo "Testing full pipeline orchestrator with 3 entities..."
echo ""

python3 3_Code/src/tools/regen/positive_regen_runner.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --threshold 80.0 \
  --dry_run \
  --only_entity_id DERIVED:9bdeff847613 \
  --only_entity_id DERIVED:a2fdb799c277 \
  --only_entity_id DERIVED:58b7eded5ec1

echo ""
echo "✅ Test 3 passed: Full pipeline multiple entities"
echo ""
sleep 2

# Test 4: Full Pipeline - All Cards (Summary Only)
echo "=========================================="
echo "Test 4: Full Pipeline - All Cards Summary"
echo "=========================================="
echo ""
echo "Testing full pipeline orchestrator with all cards (showing summary)..."
echo ""

python3 3_Code/src/tools/regen/positive_regen_runner.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --threshold 80.0 \
  --dry_run 2>&1 | tail -20

echo ""
echo "✅ Test 4 passed: Full pipeline all cards"
echo ""

# Summary
echo ""
echo "=========================================="
echo "All Dry-Run Tests Completed Successfully!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  ✅ S6 agent single card test"
echo "  ✅ Full pipeline single entity"
echo "  ✅ Full pipeline multiple entities"
echo "  ✅ Full pipeline all cards"
echo ""
echo "Next steps:"
echo "  1. To run S6 agent on a single card (no dry-run):"
echo "     python3 3_Code/src/06_s6_positive_instruction_agent.py \\"
echo "       --base_dir . \\"
echo "       --run_tag FINAL_DISTRIBUTION \\"
echo "       --arm G \\"
echo "       --group_id <GROUP_ID> \\"
echo "       --entity_id <ENTITY_ID> \\"
echo "       --card_role <Q1|Q2>"
echo ""
echo "  2. To run full pipeline on selected entities (with actual regeneration):"
echo "     python3 3_Code/src/tools/regen/positive_regen_runner.py \\"
echo "       --base_dir . \\"
echo "       --run_tag FINAL_DISTRIBUTION \\"
echo "       --arm G \\"
echo "       --threshold 80.0 \\"
echo "       --workers 4 \\"
echo "       --only_entity_id <ENTITY_1> \\"
echo "       --only_entity_id <ENTITY_2>"
echo ""
echo "  3. To run full pipeline on ALL cards (WARNING: 958 cards, will take hours):"
echo "     python3 3_Code/src/tools/regen/positive_regen_runner.py \\"
echo "       --base_dir . \\"
echo "       --run_tag FINAL_DISTRIBUTION \\"
echo "       --arm G \\"
echo "       --threshold 80.0 \\"
echo "       --workers 8"
echo ""


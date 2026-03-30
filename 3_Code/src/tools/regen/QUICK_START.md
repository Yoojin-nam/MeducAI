# Positive Regen Pipeline - Quick Start Guide

## Overview

The Positive Regen Pipeline regenerates images with low S5 validation scores by:
1. Extracting negative feedback (prompt_patch_hint) from S5 validation
2. Converting it to positive instructions using S6 agent (LLM)
3. Regenerating images using S4 with enhanced prompts

---

## Quick Commands

### 1. Dry-Run Test (No LLM calls, no image generation)
```bash
# Test single card
python3 3_Code/src/06_s6_positive_instruction_agent.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --group_id grp_023d60ba08 \
  --entity_id DERIVED:9bdeff847613 \
  --card_role Q1 \
  --dry_run

# Test full pipeline (all 958 cards)
python3 3_Code/src/tools/regen/positive_regen_runner.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --threshold 80.0 \
  --dry_run

# Run all tests
bash 3_Code/src/tools/regen/test_positive_regen.sh
```

### 2. Single Card Test (Real execution)
```bash
python3 3_Code/src/06_s6_positive_instruction_agent.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --group_id grp_023d60ba08 \
  --entity_id DERIVED:9bdeff847613 \
  --card_role Q1
```

### 3. Small Batch (2-3 cards)
```bash
python3 3_Code/src/tools/regen/positive_regen_runner.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --threshold 80.0 \
  --workers 1 \
  --only_entity_id DERIVED:9bdeff847613 \
  --only_entity_id DERIVED:a2fdb799c277
```

### 4. Full Pipeline (All 958 cards)
```bash
python3 3_Code/src/tools/regen/positive_regen_runner.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --threshold 80.0 \
  --workers 8
```

---

## Command-Line Options

### S6 Agent (`06_s6_positive_instruction_agent.py`)

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--base_dir` | No | `.` | Project base directory |
| `--run_tag` | Yes | - | Run tag (e.g., FINAL_DISTRIBUTION) |
| `--arm` | Yes | - | Arm identifier (e.g., G) |
| `--group_id` | Yes | - | Group ID |
| `--entity_id` | Yes | - | Entity ID |
| `--card_role` | Yes | - | Card role (Q1/Q2) |
| `--dry_run` | No | False | Dry-run mode (skip LLM call) |
| `--model` | No | Auto | Override model (pro/flash) |
| `--temperature` | No | 0.3 | Temperature for LLM |
| `--thinking_level` | No | high | Thinking level (minimal/low/medium/high) |
| `--rag_enabled` | No | False | Enable RAG (not recommended) |

### Positive Regen Orchestrator (`positive_regen_runner.py`)

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--base_dir` | No | `.` | Project base directory |
| `--run_tag` | Yes | - | Run tag (e.g., FINAL_DISTRIBUTION) |
| `--arm` | Yes | - | Arm identifier (e.g., G) |
| `--threshold` | No | 80.0 | Score threshold for regeneration |
| `--workers` | No | 4 | Number of parallel workers for S4 |
| `--dry_run` | No | False | Dry-run mode (skip LLM/S4 calls) |
| `--only_entity_id` | No | - | Filter to specific entity IDs (repeatable) |
| `--temperature` | No | 0.3 | Temperature for S6 LLM calls |
| `--thinking_level` | No | high | Thinking level for S6 LLM calls |
| `--rag_enabled` | No | False | Enable RAG for S6 calls (not recommended) |

---

## File Locations

### Input Files
- **S5 validation:** `2_Data/metadata/generated/FINAL_DISTRIBUTION/s5_validation__armG.jsonl`
- **S3 specs:** `2_Data/metadata/generated/FINAL_DISTRIBUTION/s3_image_spec__armG.jsonl`
- **Original images:** `2_Data/metadata/generated/FINAL_DISTRIBUTION/images/`

### Output Files
- **Enhanced S3 specs:** `2_Data/metadata/generated/FINAL_DISTRIBUTION/s3_image_spec__armG__regen_enhanced.jsonl`
- **Regenerated images:** `2_Data/metadata/generated/FINAL_DISTRIBUTION/images_regen/`
- **Regen manifest:** `2_Data/metadata/generated/FINAL_DISTRIBUTION/s4_image_manifest__armG__regen.jsonl`

---

## Expected Execution Times

| Task | Cards | Workers | Time |
|------|-------|---------|------|
| S6 single card | 1 | 1 | ~5s |
| Small batch | 2-3 | 1 | ~30s |
| Medium batch | 10-20 | 4 | ~5min |
| Full pipeline | 958 | 8 | ~100min |

**Note:** Times are estimates. Actual times depend on:
- LLM API response time
- Image generation complexity
- Network latency
- API rate limits

---

## Troubleshooting

### Error: "S4 image not found"
**Cause:** Image filename doesn't match expected pattern  
**Solution:** Check that entity_id sanitization is working (`:` → `_`)

### Error: "S3 spec not found"
**Cause:** Entity ID doesn't exist in S3 specs  
**Solution:** Verify entity_id is correct and exists in `s3_image_spec__armG.jsonl`

### Error: "No patch hints found"
**Cause:** Card has low score but no prompt_patch_hint in S5 validation  
**Solution:** This is expected behavior. Card will be skipped (not an error).

### Error: "GOOGLE_API_KEY not set"
**Cause:** Environment variable not set  
**Solution:** Set `GOOGLE_API_KEY` in `.env` or export it:
```bash
export GOOGLE_API_KEY="your-api-key-here"
```

### Error: "PermissionError: [Errno 1] Operation not permitted"
**Cause:** Sandbox restrictions or file permissions  
**Solution:** Run with proper permissions or check file ownership

---

## Verification Steps

### After Dry-Run
1. ✅ Check that script completes without errors
2. ✅ Verify success count matches expected count
3. ✅ Review any warning messages

### After Real Execution
1. ✅ Check `s3_image_spec__armG__regen_enhanced.jsonl` exists
2. ✅ Verify file has expected number of entries
3. ✅ Check `images_regen/` directory for images
4. ✅ Verify image count matches expected count
5. ✅ Spot-check a few images for quality
6. ✅ Compare original vs regenerated images
7. ✅ (Optional) Run S5 validation on regenerated images

---

## Tips

### For Testing
- Always start with `--dry_run` to verify setup
- Use `--only_entity_id` to test small batches first
- Check a few cards manually before running full pipeline

### For Production
- Run during off-peak hours (API rate limits)
- Use `--workers 8` or higher for faster execution
- Monitor progress output for errors
- Keep logs for troubleshooting

### For Debugging
- Add `2>&1 | tee regen_log.txt` to save output
- Use `--only_entity_id` to isolate problematic cards
- Check S5 validation for patch hints
- Verify S3 specs have correct entity_ids

---

## Support

### Documentation
- **Full test results:** `3_Code/src/tools/regen/DRY_RUN_TEST_RESULTS.md`
- **Phase 3 completion:** `3_Code/src/tools/regen/PHASE3_DRY_RUN_COMPLETE.md`
- **Implementation plan:** See attached plan file

### Test Script
```bash
bash 3_Code/src/tools/regen/test_positive_regen.sh
```

### Common Issues
See `DRY_RUN_TEST_RESULTS.md` section "Issues Fixed During Testing"

---

## Quick Reference

```bash
# Dry-run test
python3 3_Code/src/tools/regen/positive_regen_runner.py \
  --base_dir . --run_tag FINAL_DISTRIBUTION --arm G \
  --threshold 90.0 --dry_run

# Small batch (2 cards)
python3 3_Code/src/tools/regen/positive_regen_runner.py \
  --base_dir . --run_tag FINAL_DISTRIBUTION --arm G \
  --threshold 90.0 --workers 1 \
  --only_entity_id DERIVED:9bdeff847613 \
  --only_entity_id DERIVED:a2fdb799c277

# Full pipeline (958 cards)
python3 3_Code/src/tools/regen/positive_regen_runner.py \
  --base_dir . --run_tag FINAL_DISTRIBUTION --arm G \
  --threshold 90.0 --workers 8
```

---

**Status:** ✅ Ready for production use  
**Last Updated:** 2026-01-15  
**Dry-Run Tests:** All passed (958/958 cards)


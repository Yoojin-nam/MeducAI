# Positive Regen Tools

This directory contains tools for the **Positive Regeneration Pipeline** (Option C Image Regeneration).

## Overview

The Positive Regen Pipeline improves low-scoring images by:
1. Filtering S5 validation results for images with `image_regeneration_trigger_score < 80`
2. Converting S5 negative feedback (`prompt_patch_hint`) into positive instructions using S6 agent
3. Enhancing S3 specs with positive instructions
4. Regenerating images using S4 with `--image_type regen`

## Files

### `positive_regen_runner.py`

**Purpose:** Main orchestrator for the positive regeneration pipeline.

**Usage:**

```bash
# Dry run (show plan without executing)
python 3_Code/src/tools/regen/positive_regen_runner.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --threshold 80.0 \
  --dry_run

# Full pipeline (generate images)
python 3_Code/src/tools/regen/positive_regen_runner.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --threshold 80.0 \
  --workers 4

# Test with specific entity IDs only
python 3_Code/src/tools/regen/positive_regen_runner.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --threshold 80.0 \
  --only_entity_id DERIVED_xxx \
  --only_entity_id DERIVED_yyy \
  --dry_run
```

**Key Arguments:**

- `--run_tag`: Run tag (e.g., `FINAL_DISTRIBUTION`)
- `--arm`: Arm identifier (e.g., `G`)
- `--threshold`: Image score threshold for regeneration (default: 80.0)
  - Cards with `image_regeneration_trigger_score < threshold` will be regenerated
- `--workers`: Number of parallel workers for S4 (default: 4)
- `--dry_run`: Show plan without calling S6 or S4
- `--only_entity_id`: Filter to specific entity IDs (can specify multiple times)
- `--temperature`: Temperature for S6 LLM calls (default: 0.3)
- `--thinking_level`: Thinking level for S6 (`minimal`, `low`, `medium`, `high`; default: `high`)
- `--rag_enabled`: Enable RAG for S6 calls (default: disabled)

**Pipeline Steps:**

1. **Load S5 validation results** from `s5_validation__arm{arm}.jsonl`
2. **Filter cards** with `image_regeneration_trigger_score < threshold`
3. **For each target card:**
   - Load S3 spec from `s3_image_spec__arm{arm}.jsonl`
   - Load S4 image from `s4_image_manifest__arm{arm}.jsonl`
   - Extract `prompt_patch_hint` from S5 validation
   - Call S6 agent to convert hints into positive instructions
   - Generate enhanced S3 spec with `positive_instructions` field
4. **Write enhanced specs** to `s3_image_spec__arm{arm}__regen_enhanced.jsonl`
5. **Call S4** with `--image_type regen` to generate improved images

**Output:**

- Enhanced S3 specs: `s3_image_spec__arm{arm}__regen_enhanced.jsonl`
- Regenerated images: `images_regen/IMG__{run_tag}__{group_id}__{entity_id}__{card_role}_regen.jpg`
- Regen manifest: `s4_image_manifest__arm{arm}__regen.jsonl`

**Model Selection:**

- `S1_TABLE_VISUAL` specs → Pro model (`gemini-3-pro-preview`)
- `S2_CARD_IMAGE` specs → Flash model (`gemini-3-flash-preview`)

**Dependencies:**

- S6 Positive Instruction Agent (`06_s6_positive_instruction_agent.py`)
- S4 Image Generator (`04_s4_image_generator.py`)
- S5 validation results with `image_regeneration_trigger_score` field

### `fast_s2_regen.py`

**Purpose:** Fast S2 card regeneration tool (legacy, for card content regeneration).

## Related Documentation

- **Protocol:** `0_Protocol/05_Pipeline_and_Execution/S5_Positive_Regen_Procedure.md`
- **S6 Agent Spec:** `0_Protocol/05_Pipeline_and_Execution/S6_Positive_Instruction_Agent_Spec.md`
- **S5 Decision:** `0_Protocol/05_Pipeline_and_Execution/S5_Decision_Definition_Canonical.md`
- **Image Naming:** `0_Protocol/05_Pipeline_and_Execution/Image_Asset_Naming_and_Storage_Convention.md`

## Example Workflow

```bash
# 1. Run S5 validation (if not already done)
python 3_Code/src/05_s5_validator.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G

# 2. Check how many cards need regeneration (dry run)
python 3_Code/src/tools/regen/positive_regen_runner.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --threshold 90.0 \
  --dry_run

# 3. Test with 2-3 cards first
python 3_Code/src/tools/regen/positive_regen_runner.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --threshold 90.0 \
  --only_entity_id DERIVED_xxx \
  --only_entity_id DERIVED_yyy

# 4. Run full regeneration for all low-scoring cards
python 3_Code/src/tools/regen/positive_regen_runner.py \
  --base_dir . \
  --run_tag FINAL_DISTRIBUTION \
  --arm G \
  --threshold 90.0 \
  --workers 4
```

## Notes

- **Same RUN_TAG:** Regenerated images use the same `RUN_TAG` as baseline, differentiated by folder (`images_regen/`) and suffix (`_regen`)
- **Threshold:** Default threshold is 80.0. Lower threshold = fewer regenerations, higher threshold = more regenerations
- **Dry Run:** Always test with `--dry_run` first to see the plan
- **Testing:** Use `--only_entity_id` to test with specific cards before full run
- **Thinking:** S6 agent uses `thinking_level=high` by default for high-quality reasoning
- **RAG:** RAG is disabled by default (regeneration is a generation task, not retrieval)

## Troubleshooting

**"S6 agent not available":**
- Ensure `06_s6_positive_instruction_agent.py` is in `3_Code/src/`
- Check that all dependencies are installed (`google-genai`, `Pillow`)
- Dry-run mode will still work without S6 agent

**"No cards need regeneration":**
- Check S5 validation results have `image_regeneration_trigger_score` field
- Try lowering the threshold (e.g., `--threshold 80.0`)
- Verify S5 validation was run successfully

**"S3 spec not found" or "S4 image not found":**
- Ensure S3 and S4 were run successfully for this arm
- Check that `s3_image_spec__arm{arm}.jsonl` and `s4_image_manifest__arm{arm}.jsonl` exist
- Verify `group_id`, `entity_id`, and `card_role` match between S3/S4/S5

**"No patch hints found":**
- S5 validation may not have generated `prompt_patch_hint` for this card
- Check S5 validation results for `card_image_validation.issues[].prompt_patch_hint`
- Ensure S5 was run with the correct configuration


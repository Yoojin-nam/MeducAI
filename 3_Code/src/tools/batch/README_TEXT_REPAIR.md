# Batch Text Repair (S1R + S2R) Implementation Guide

## Overview

This directory contains the implementation for batch-based text repair of S1 tables and S2 cards using the Gemini Batch API. This approach provides:

- **50% cost reduction** compared to synchronous API calls
- **RPM bypass** - no 15 RPM limit, true parallel processing
- **Automatic retry** with 404/429 error handling and API key rotation
- **Progress tracking** with resumable operations

## File Structure

```
3_Code/src/tools/
├── batch/
│   ├── batch_text_repair.py          # Main batch orchestrator (NEW)
│   ├── batch_image_generator.py      # Reference implementation (S4)
│   └── README_TEXT_REPAIR.md          # This file (NEW)
├── regen/
│   ├── s1r_s2r_agent.py               # Synchronous fallback agent (NEW)
│   └── positive_regen_runner.py       # Reference implementation (S6)
└── prompt/
    ├── S1R_SYSTEM__v1.md               # S1 table repair system prompt (NEW)
    └── S2R_SYSTEM__v1.md               # S2 card repair system prompt (NEW)
```

## Architecture

### Input Phase
1. Load S5 validation results (`s5_validation__armG.jsonl`)
2. Load S1 baseline data (`stage1_struct__armG.jsonl`)
3. Load S2 baseline data (`s2_results__armG.jsonl`)

### Batch Preparation
1. Extract repair targets (TA < 1.0)
2. Build batch requests with S5 feedback
3. Upload to File API
4. Track batch metadata

### Batch Execution
1. Create batch job via Gemini API
2. Poll status every 5min
3. Download results when ready

### Output Phase
1. Parse improved text from batch results
2. Update original JSONL files
3. Add repair metadata to records

## Usage Examples

### 1. Submit Batch for Repair

```bash
# Repair both S1 tables and S2 cards
python3 3_Code/src/tools/batch/batch_text_repair.py \
    --base_dir . \
    --run_tag FINAL_DISTRIBUTION \
    --arm G \
    --mode mixed \
    --submit

# Repair only S2 cards
python3 3_Code/src/tools/batch/batch_text_repair.py \
    --base_dir . \
    --run_tag FINAL_DISTRIBUTION \
    --arm G \
    --mode s2r \
    --submit

# Test with specific entities only
python3 3_Code/src/tools/batch/batch_text_repair.py \
    --base_dir . \
    --run_tag FINAL_DISTRIBUTION \
    --arm G \
    --mode s2r \
    --only_entity_id a80baa3eb411 \
    --only_entity_id f0eea517b0b9 \
    --submit
```

### 2. Check Status

```bash
# Check status of all batch jobs
python3 3_Code/src/tools/batch/batch_text_repair.py --check_status
```

### 3. Download Results and Apply

```bash
# Download results and update JSONL files
python3 3_Code/src/tools/batch/batch_text_repair.py \
    --base_dir . \
    --run_tag FINAL_DISTRIBUTION \
    --arm G \
    --download_and_apply
```

## Batch Tracking Schema

Tracking file location: `2_Data/metadata/generated/{RUN_TAG}/.batch_text_repair_tracking.json`

```json
{
    "schema_version": "TEXT_REPAIR_BATCH_v1.0",
    "run_tag": "FINAL_DISTRIBUTION",
    "arm": "G",
    "batches": {
        "<api_key_hash>": {
            "chunks": [
                {
                    "batch_id": "batches/abc123",
                    "status": "JOB_STATE_SUCCEEDED",
                    "mode": "s1r|s2r|mixed",
                    "file_name": "files/abc123",
                    "prompts_metadata": [
                        {
                            "key": "s1r_grp_1ed9548fc8",
                            "type": "s1_table",
                            "group_id": "grp_1ed9548fc8",
                            "prompt_hash": "abc123..."
                        },
                        {
                            "key": "s2r_grp_0bb51821c7_a80baa3eb411_Q1",
                            "type": "s2_card",
                            "group_id": "grp_0bb51821c7",
                            "entity_id": "a80baa3eb411",
                            "card_role": "Q1",
                            "prompt_hash": "def456..."
                        }
                    ],
                    "created_at": "2026-01-06T10:00:00Z",
                    "completed_at": "2026-01-06T10:15:00Z",
                    "request_count": 59
                }
            ]
        }
    },
    "failed_requests": []
}
```

## Error Handling

### Automatic Retry Logic

| Error | Cause | Response |
|-------|-------|----------|
| **429** | RPM/quota exceeded | API key rotation |
| **404** | File access denied (after key rotation) | Re-upload file with new key |
| **500/503** | Transient server error | Exponential backoff (2s → 4s → 8s → 16s → 32s) |

### API Key Rotation

The system automatically rotates API keys when quota limits are hit:

1. Detects 429 error with quota exhaustion
2. Calls `ApiKeyRotator.rotate_on_quota_exhausted()`
3. Re-uploads file with new key (if 404 occurs)
4. Retries batch submission

## Batch Request Format

### S1 Table Repair Request

```json
{
    "key": "s1r_grp_1ed9548fc8",
    "request": {
        "contents": [{
            "parts": [{"text": "USER_PROMPT"}],
            "role": "user"
        }],
        "config": {
            "system_instruction": {
                "parts": [{"text": "SYSTEM_PROMPT"}]
            },
            "temperature": 0.2,
            "tools": [{"google_search": {}}],
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "object",
                "properties": {
                    "improved_table_markdown": {"type": "string"},
                    "changes_summary": {"type": "string"},
                    "confidence": {"type": "number"}
                }
            }
        }
    }
}
```

### S2 Card Repair Request

```json
{
    "key": "s2r_grp_0bb51821c7_a80baa3eb411_Q1",
    "request": {
        "contents": [{
            "parts": [{"text": "USER_PROMPT"}],
            "role": "user"
        }],
        "config": {
            "system_instruction": {
                "parts": [{"text": "SYSTEM_PROMPT"}]
            },
            "temperature": 0.3,
            "tools": [{"google_search": {}}],
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "object",
                "properties": {
                    "improved_front": {"type": "string"},
                    "improved_back": {"type": "string"},
                    "improved_options": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "changes_summary": {"type": "string"},
                    "confidence": {"type": "number"}
                }
            }
        }
    }
}
```

## Result Parsing and Merging

### Batch Result Format

```jsonl
{"key": "s1r_grp_1ed9548fc8", "response": {"candidates": [{"content": {"parts": [{"text": "{\"improved_table_markdown\": \"...\"}"}]}}]}}
{"key": "s2r_grp_0bb51821c7_a80baa3eb411_Q1", "response": {"candidates": [{"content": {"parts": [{"text": "{\"improved_front\": \"...\"}"}]}}]}}
```

### Merge Logic

1. **Parse batch results** - Extract JSON from response text
2. **Build lookup dicts**:
   - S1: `group_id → improved_table_markdown`
   - S2: `(group_id, entity_id, card_role) → improved_card`
3. **Update S1 JSONL**:
   - Match by `group_id`
   - Replace `master_table_markdown_kr`
   - Add `_repair_metadata`
4. **Update S2 JSONL**:
   - Match by `(group_id, entity_id, card_role)`
   - Replace `front`, `back`, `options`
   - Add `_repair_metadata`

### Repair Metadata

Added to each repaired record:

```json
{
    "_repair_metadata": {
        "repaired_at": "2026-01-06T10:15:00Z",
        "method": "batch_s1r" | "batch_s2r",
        "confidence": 0.95
    }
}
```

## Cost Comparison

| Method | Input Cost | Output Cost | Total Cost (59 requests) |
|--------|------------|-------------|--------------------------|
| **Synchronous API** | $0.52 | $2.08 | **$2.60** |
| **Batch API (50% discount)** | $0.26 | $1.04 | **$1.30** |
| **Savings** | - | - | **$1.30 (50%)** |

### Additional Benefits

- **RPM bypass**: No 15 RPM limit (synchronous) → unlimited parallel processing (batch)
- **Time savings**: 1 hour (sequential @ 15 RPM) → 10-15 minutes (batch)
- **Automatic key rotation**: Handles quota exhaustion transparently

## Synchronous Fallback

For small-scale repairs or debugging, use the synchronous agent:

```bash
# Repair specific entity synchronously
python3 3_Code/src/tools/regen/s1r_s2r_agent.py \
    --base_dir . \
    --run_tag FINAL_DISTRIBUTION \
    --arm G \
    --mode sync \
    --only_entity_id a80baa3eb411
```

**Pros:**
- Immediate results (no 10-15 min wait)
- Easier debugging

**Cons:**
- 15 RPM limit
- 2x cost (no batch discount)
- Sequential processing

## Testing Plan

### Phase 1: Pilot Test (3 requests)

```bash
# Test with 3 entities
python3 3_Code/src/tools/batch/batch_text_repair.py \
    --base_dir . \
    --run_tag FINAL_DISTRIBUTION \
    --arm G \
    --mode s2r \
    --only_entity_id a80baa3eb411 \
    --only_entity_id f0eea517b0b9 \
    --only_entity_id 3ba3f0ddb56d \
    --submit

# Wait 10 minutes
sleep 600

# Check status
python3 3_Code/src/tools/batch/batch_text_repair.py --check_status

# Apply results
python3 3_Code/src/tools/batch/batch_text_repair.py \
    --base_dir . \
    --run_tag FINAL_DISTRIBUTION \
    --arm G \
    --download_and_apply
```

**Validation:**
1. Batch submission succeeds
2. Tracking JSON properly records metadata
3. Results parse correctly
4. JSONL files merge successfully
5. S5 re-validation shows TA improvement

### Phase 2: Full Execution (59 requests)

```bash
# Submit full batch
python3 3_Code/src/tools/batch/batch_text_repair.py \
    --base_dir . \
    --run_tag FINAL_DISTRIBUTION \
    --arm G \
    --mode mixed \
    --submit

# Wait for completion (~10-15 minutes)
# Then apply results
```

**Expected Outcome:**
- **Success rate**: 85%+ (50+/59 requests)
- **TA improvement**: 0.0/0.5 → 0.5+ (85%+)
- **Cost**: $1.30 (vs $2.60 synchronous)

## Troubleshooting

### Issue: Batch stuck in "PENDING" status

**Solution:**
```bash
# Wait longer (batches can take 10-15 minutes)
# If still pending after 30 minutes, check API console
```

### Issue: 404 error after key rotation

**Cause:** File uploaded with one key cannot be accessed by another key

**Solution:** Script automatically re-uploads file with new key

### Issue: All API keys exhausted

**Cause:** All keys hit daily quota limit

**Solution:**
```bash
# Wait for quota reset (typically 24 hours)
# Or add more API keys to .env:
# GOOGLE_API_KEY_1=...
# GOOGLE_API_KEY_2=...
# GOOGLE_API_KEY_3=...
```

### Issue: Parse error in batch results

**Cause:** LLM returned malformed JSON

**Solution:**
```bash
# Check batch result file manually
# Re-run failed requests with --retry_failed (TODO)
```

## Implementation Status

✅ **Completed** (All 5 To-Dos):

1. ✅ Request builder - S5 feedback → batch JSONL
2. ✅ Tracking system - Batch metadata persistence
3. ✅ Error handling - 404/429 retry, key rotation
4. ✅ Result parser - JSON extraction and JSONL merge
5. ✅ CLI interface - `--submit`, `--check_status`, `--download_and_apply`

🚧 **TODO** (Future Enhancements):

- `--retry_failed` - Automatic retry of failed requests
- Dry-run mode - Preview repairs without submitting
- Diff report - Before/after comparison
- Confidence threshold - Only apply high-confidence repairs

## References

- **Plan**: `/path/to/workspace/.cursor/plans/s1r_s2r_batch_implementation_c30bc16a.plan.md`
- **S4 Batch Reference**: `3_Code/src/tools/batch/batch_image_generator.py`
- **S6 Agent Reference**: `3_Code/src/tools/regen/positive_regen_runner.py`
- **API Key Rotator**: `3_Code/src/tools/api_key_rotator.py`

## Contact

For questions or issues, refer to the project README or handoff documents in `5_Meeting/`.


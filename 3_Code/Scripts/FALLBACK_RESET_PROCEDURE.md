## Fallback reset procedure (repair failed)

When the “repair” approach fails (e.g., downloads succeed but saving stays at 0, or parsing/saving repeatedly crashes), use this fallback to **restart cleanly** while still **skipping anything already saved locally**.

This procedure **does not delete images**. It only resets state files so the pipeline can be re-submitted / re-checked without being blocked by broken tracking.

### What gets reset

- `2_Data/metadata/.batch_tracking.json`
- `2_Data/metadata/.batch_failed.json`

Before resetting, the script creates timestamped backups next to the originals:

- `.batch_tracking.json.backup_YYYYmmdd_HHMMSS`
- `.batch_failed.json.backup_YYYYmmdd_HHMMSS`

### Why local-image skip still works after reset

Batch restart will still skip already-generated images because `batch_image_generator.py` checks:

- `2_Data/metadata/generated/<run_tag>/images/` for existing filenames
- and skips generation/download when files already exist

Resetting tracking just removes the “already submitted batch” memory; it does **not** remove local files.

### Step 1) Backup + reset tracking/failed state

From repo root:

```bash
python 3_Code/Scripts/fallback_reset_batch_state.py --base_dir . --yes
```

If you want the script to print a ready-to-run restart command:

```bash
python 3_Code/Scripts/fallback_reset_batch_state.py --base_dir . --yes \
  --spec 2_Data/metadata/generated/<run_tag>/s3_image_spec__armX.jsonl \
  --run_tag <run_tag>
```

### Step 2) Restart submission (resume mode)

```bash
python 3_Code/src/batch_image_generator.py \
  --input 2_Data/metadata/generated/<run_tag>/s3_image_spec__armX.jsonl \
  --base_dir . \
  --run_tag <run_tag> \
  --resume
```

### Step 3) (Optional) After some batches succeed, re-run status check/download

```bash
python 3_Code/src/batch_image_generator.py --base_dir . --check_status
```

### Safety notes

- If you later decide you need to recover old tracking, restore from the `.backup_...` files created in `2_Data/metadata/`.
- Avoid `--no_backup` unless you have already copied the state files elsewhere.



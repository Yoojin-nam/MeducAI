# Prompt Refinement Tools

Tools for S5-based manual prompt refinement (development-only endpoint).

## Tools

### 1. `build_patch_backlog.py`

Extracts issues from S5 validation JSONL and creates a structured patch backlog.

**Usage**:
```bash
python3 3_Code/src/tools/prompt_refinement/build_patch_backlog.py \
    --base_dir . \
    --run_tag <RUN_TAG> \
    --arm <ARM> \
    --output 2_Data/metadata/generated/<RUN_TAG>/prompt_refinement/patch_backlog__S5R{k}.json
```

**Output**: JSON file with issues grouped by `recommended_fix_target` and `issue_code`.

### 2. `make_prompt_diff_report.py`

Generates a markdown diff report comparing old and new prompt versions.

**Usage**:
```bash
python3 3_Code/src/tools/prompt_refinement/make_prompt_diff_report.py \
    --base_dir . \
    --prompt_name S1_SYSTEM \
    --old_version S5R0__v12 \
    --new_version S5R1__v13 \
    --output 2_Data/metadata/generated/<RUN_TAG>/prompt_refinement/diff_report__S1_SYSTEM__S5R1.md
```

**Output**: Markdown diff report.

### 3. `smoke_validate_prompt.py`

Performs static validation on prompt files to ensure schema invariance.

**Usage**:
```bash
python3 3_Code/src/tools/prompt_refinement/smoke_validate_prompt.py \
    --base_dir . \
    --prompt_file 3_Code/prompt/S1_SYSTEM__S5R1__v13.md
```

**Output**: Validation results (pass/fail with errors/warnings).

## Quick Start

1. **Build patch backlog**:
   ```bash
   python3 3_Code/src/tools/prompt_refinement/build_patch_backlog.py \
       --base_dir . \
       --run_tag DEV_armG_mm_S5R0_before_rerun_preFix_20251229_203653__rep2 \
       --arm G
   ```

2. **Review patch backlog** and edit prompts in Cursor.

3. **Generate diff report**:
   ```bash
   python3 3_Code/src/tools/prompt_refinement/make_prompt_diff_report.py \
       --base_dir . \
       --prompt_name S1_SYSTEM \
       --old_version S5R0__v12 \
       --new_version S5R1__v13
   ```

4. **Validate prompt**:
   ```bash
   python3 3_Code/src/tools/prompt_refinement/smoke_validate_prompt.py \
       --base_dir . \
       --prompt_file 3_Code/prompt/S1_SYSTEM__S5R1__v13.md
   ```

## Related Documentation

- `0_Protocol/05_Pipeline_and_Execution/S5R_Prompt_Refinement_Development_Endpoint_Canonical.md`
- `0_Protocol/00_Governance/supporting/Prompt_governance/S5R_Manual_Refinement_Checklist.md`


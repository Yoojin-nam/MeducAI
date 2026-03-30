# Scripts Folder Cleanup Summary

**Date**: 2026-01-07
**Task**: 3_Code/Scripts 폴더 정리 (archive 이동, 중복 통합)

## Changes Made

### 1. Archive Folder Migration

**Action**: Moved `3_Code/Scripts/archive/` → `99_archived/code_scripts/`

**Files Moved**: 30 files (26 scripts + 4 documentation files)

**Rationale**: 
- The archive folder contained old test scripts, analysis scripts, and one-time migration scripts
- These files are no longer actively used but retained for historical reference
- Moving to `99_archived/` consolidates all archived materials in one location
- `99_archived/` is in .gitignore, so these files remain local-only

**Files Included**:
- Analysis scripts (4): `analyze_missing_images_detailed.py`, `analyze_rate_limits.py`, etc.
- Audit scripts (3): `audit_curriculum_parsing_coverage.py`, etc.
- Test scripts (6): `test_s2_array_parsing_fix.sh`, `test_s5_validator.py`, etc.
- Run scripts (5): `run_s1_stress_3x.sh`, `run_s5r1_phase2_regeneration.sh`, etc.
- Pilot/experimental scripts (5): `pilot_ocr_table_visuals_gemini.py`, etc.
- Migration/utility scripts (4): `migrate_v1_to_v2.py`, `ppt_to_markdown.py`, etc.
- Documentation (3): `SCRIPTS_CLEANUP_PLAN.md`, `TOOLS_MIGRATION_PLAN.md`, `README_S5_TESTING.md`

### 2. Duplicate Script Analysis

**Finding**: The plan suggested consolidating "duplicate" scripts, but after detailed analysis, these scripts serve **different purposes** and should **NOT** be consolidated:

#### S1 Execution Scripts (NOT duplicates)
- `run_s1_final_background.sh` (63 lines)
  - Runs **S1 only** in tmux with caffeinate
  - Sophisticated logging and session management
  - Prevents macOS sleep during long runs
  - Use case: Run S1 stage independently

- `S1_FULL_EXECUTION.sh` (33 lines)
  - Runs **S1+S2 together** (both stages)
  - Simpler, direct execution
  - Use case: Run both stages sequentially

**Decision**: Keep both - they serve different execution patterns

#### PDF Generation Scripts (NOT duplicates)
- `generate_combined_pdf_with_s5.py` (215 lines)
  - Generates combined PDF with **S5 validation included**
  - Uses `build_single_group_sections()` directly
  - Optimized for S5 workflow
  - Use case: Generate PDFs with S5 validation results

- `generate_combined_pdf_from_completed_groups.py` (276 lines)
  - Generates PDF from **completed S2 groups**
  - Creates individual PDFs first, then merges with PyPDF2
  - Two-step process for flexibility
  - Use case: Generate PDFs from S2 results

- `generate_pdf_from_run_tag.py` (304 lines)
  - General-purpose PDF generation from run_tag
  - Most flexible, supports various options
  - Use case: General PDF generation utility

**Decision**: Keep all three - they serve different use cases and workflows

### 3. Final Structure

```
3_Code/Scripts/
├── (61 active scripts)
├── legacy/                    # Legacy scripts (22 files, kept for reference)
│   ├── README.md
│   ├── test_*.py
│   ├── run_*.sh
│   └── ...
└── pdf_generation/            # PDF generation utilities
    ├── generate_final_pdf.py
    └── regenerate_full_pdf.py

99_archived/code_scripts/      # Newly archived (30 files)
├── README.md                  # Documentation of archived scripts
├── analyze_*.py
├── audit_*.py
├── test_*.sh
├── run_*.sh
└── ...
```

## Statistics

### Before Cleanup
- Total scripts in `3_Code/Scripts/`: 121 files (62 .py, 47 .sh, etc.)
- Archive folder: 30 files
- Legacy folder: 22 files

### After Cleanup
- Active scripts in `3_Code/Scripts/`: 83 files (.py and .sh)
- Legacy folder (unchanged): 22 files
- Archived to `99_archived/code_scripts/`: 30 files (26 scripts + 4 docs)

**Net Result**: Cleaner Scripts folder with better organization

## Notes

1. **No consolidation needed**: After detailed analysis, the "duplicate" scripts identified in the plan actually serve different purposes and should remain separate.

2. **Archive location**: Files moved to `99_archived/code_scripts/` with comprehensive README documenting their purpose and history.

3. **Legacy folder**: The existing `legacy/` folder remains in place as it contains older scripts that may still be referenced.

4. **Documentation**: Created README in `99_archived/code_scripts/` explaining the archived scripts.

## Related Documentation

- `3_Code/Scripts/legacy/README.md` - Legacy scripts documentation
- `99_archived/code_scripts/README.md` - Archived scripts documentation
- `3_Code/Scripts/CROSS_ARM_S1_S2_USAGE.md` - S1/S2 usage guide
- `3_Code/Scripts/tmux_usage.md` - Tmux usage guide

## Git Changes

```bash
# Files deleted from git (moved to 99_archived which is in .gitignore)
D 3_Code/Scripts/archive/README_S5_TESTING.md
D 3_Code/Scripts/archive/SCRIPTS_CLEANUP_PLAN.md
D 3_Code/Scripts/archive/TOOLS_MIGRATION_PLAN.md
D 3_Code/Scripts/archive/analyze_*.py (4 files)
D 3_Code/Scripts/archive/audit_*.py (3 files)
D 3_Code/Scripts/archive/test_*.sh (6 files)
D 3_Code/Scripts/archive/run_*.sh (5 files)
D 3_Code/Scripts/archive/pilot_*.py (5 files)
D 3_Code/Scripts/archive/migrate_v1_to_v2.py
D 3_Code/Scripts/archive/ppt_to_markdown.py
D 3_Code/Scripts/archive/incremental_batch_test.py
D 3_Code/Scripts/archive/generate_missing_entities_s2_s5.py.20251230_224810
D 3_Code/Scripts/archive/generate_pdf_final_test_separation.sh
```

## Commit Message

```
chore(3_Code): consolidate archived scripts to 99_archived/code_scripts

- Move 3_Code/Scripts/archive/ (30 files) → 99_archived/code_scripts/
- Add comprehensive README documenting archived scripts
- Analysis shows "duplicate" scripts serve different purposes, kept separate
- Scripts folder now cleaner with 83 active scripts + 22 legacy scripts
```


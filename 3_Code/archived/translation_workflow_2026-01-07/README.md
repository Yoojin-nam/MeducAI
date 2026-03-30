# Translation Workflow Scripts Archive

**Archive Date**: 2026-01-07  
**Status**: Completed  
**Purpose**: Medical term English-only translation implementation

## Overview

This archive contains temporary scripts used for the medical term translation workflow that converted Korean medical terms to English in Anki cards and AppSheet exports while preserving sentence structure and formatting.

## Workflow Completion Status

The translation workflow was successfully completed with the following outcomes:
- Medical terms in Anki cards converted to English-only format
- AppSheet exports updated with consistent English medical terminology
- Translation applied to both baseline and regenerated (repaired) cards
- QA validation performed on translated content

## Archive Contents

### Translation Scripts (9 files)
- `translate_medical_terms.py` - Main translation module
- `translate_medical_terms_module.py` - Translation utility functions
- `retranslate_from_original.py` - Retranslate from original source
- `retranslate_problem_cards.py` - Fix problematic translations
- `retranslate_regen_from_original.py` - Retranslate regenerated cards
- `retranslate_thinking_cards.py` - Retranslate thinking process cards
- `retranslate_with_improved_prompt.py` - Retranslate with improved prompts
- `merge_full_regen_translations.py` - Merge baseline and regen translations
- `batch_medterm_translation.py` - Batch processing for translation

### Fix/Debug Scripts (6 files)
- `fix_thinking_errors.py` - Fix thinking format errors
- `fix_thinking_errors_selective.py` - Selective thinking error fixes
- `fix_last_6_cards.py` - Fix specific problematic cards
- `debug_json_schema_response.py` - Debug JSON schema responses
- `debug_single_translation.py` - Debug individual translations
- `aggressive_thinking_cleaner.py` - Clean thinking artifacts

### Filter/Analysis Scripts (5 files)
- `filter_cards_by_uid.py` - Filter cards by UID
- `filter_regen_cards.py` - Filter regenerated cards
- `verify_regen_translations.py` - Verify regen translations
- `generate_translation_qa_report.py` - Generate QA reports
- `analyze_mixed_formats.py` - Analyze mixed format issues

### Test Scripts (3 files)
- `test_json_schema_translation.py` - Test JSON schema translation
- `run_test20_regression.py` - Run regression tests on 20 samples
- `show_fixed_cards_comparison.py` - Show before/after comparison
- `show_successful_translations.py` - Display successful translations
- `skip_problematic_record.py` - Skip problematic records

### Supporting Files (2 files)
- `ORIGINAL_PROMPT_BACKUP.txt` - Backup of original translation prompt
- `mcq_back_gloss_overrides.json` - Manual overrides for MCQ glosses

## Active Production Scripts

The following scripts remain in active use in `3_Code/src/tools/anki/`:
- `export_final_anki_integrated.py` - Production Anki export
- `merge_anki_decks_with_regen.py` - Production deck merging
- `update_anki_with_regen.py` - Production card updates
- `TRANSLATE_MEDICAL_TERMS_GUIDE.md` - Translation guide (documentation)
- `TRANSLATION_WORKFLOW.md` - Workflow documentation

## Related Documentation

- **Handoff**: `0_Protocol/01_Execution_Safety/handoffs/HANDOFF__MEDTERM_ENGLISH_ONLY__S2_APPSHEET_ANKI__2026-01-07.md`
- **Language Policy**: `0_Protocol/00_Governance/supporting/Prompt_governance/S2_Language_Policy_Future_Upgrade.md`
- **Export Guide**: `3_Code/src/tools/docs/ANKI_EXPORT_GUIDE.md`

## Technical Notes

### Translation Approach
- **Principle**: Translate medical terms only, preserve sentence structure
- **Model**: `gemini-3-flash-preview` with JSON schema enforcement
- **Resume Support**: Built-in resume functionality for interrupted batches
- **Coverage**: Applied to all S2 baseline and S2 repaired/regenerated cards

### Quality Control
- Manual QA performed on 50+ sample cards
- Regression testing on TEST_20 subset
- Comparison reports generated for validation
- Override mechanism for edge cases

## Archive Rationale

These scripts were archived because:
1. Translation workflow is now complete
2. Final translated files are in production use
3. Scripts served one-time migration purpose
4. Production export scripts handle ongoing needs
5. Maintaining archive for reproducibility and reference

## Retrieval

If you need to reference or re-run any of these scripts:
1. Scripts are preserved exactly as used in production
2. All dependencies are documented in the main requirements.txt
3. Refer to TRANSLATION_WORKFLOW.md for execution instructions
4. Contact project maintainer for guidance on script usage

---

**Archive Frozen**: 2026-01-07  
**Maintained By**: MeducAI Team  
**Status**: Historical Reference


# Execution Safety Handoffs

**Purpose**: Pipeline execution safety, language policy, and translation workflow handoffs  
**Last Updated**: 2026-01-09  
**Status**: Active

---

## Overview

This folder contains handoff documentation related to execution safety policies, language standards, and major workflow changes that affect pipeline execution integrity and reproducibility.

## Contents

### Translation and Language Policy

#### HANDOFF__MEDTERM_ENGLISH_ONLY__S2_APPSHEET_ANKI__2026-01-07.md

**Status**: Completed  
**Date**: 2026-01-07

**Scope**: Medical term English-only translation implementation across S2 baseline, S2 regenerated, AppSheet exports, and Anki exports

**Key Changes**:
- Medical terms converted from Korean to English-only
- Sentence structure and formatting preserved
- Applied to both baseline and repaired/regenerated S2 cards
- AppSheet and Anki exports updated with consistent language policy

**Impact**:
- All distributed Anki decks use English medical terminology
- AppSheet QA forms display English medical terms
- Improved consistency with international medical education standards
- Reduced ambiguity in medical term usage

**Related Documents**:
- Language Policy: `0_Protocol/00_Governance/supporting/Prompt_governance/S2_Language_Policy_Future_Upgrade.md`
- Translation Guide: `3_Code/src/tools/anki/TRANSLATE_MEDICAL_TERMS_GUIDE.md`
- Translation Workflow: `3_Code/src/tools/anki/TRANSLATION_WORKFLOW.md`
- Archived Scripts: `3_Code/archived/translation_workflow_2026-01-07/`

---

## Related Handoff Folders

### Pipeline Execution Handoffs
**Location**: [`0_Protocol/05_Pipeline_and_Execution/handoffs/`](../../05_Pipeline_and_Execution/handoffs/)

**Content**: S4 image generation, S5 validation, PDF generation, regeneration agents

### QA Operations Handoffs
**Location**: [`0_Protocol/06_QA_and_Study/QA_Operations/handoffs/`](../../06_QA_and_Study/QA_Operations/handoffs/)

**Content**: FINAL distribution execution, AppSheet exports, assignment generation

---

## Handoff Document Principles

### When to Create a Handoff
- Major policy changes that affect execution
- Completed workflow migrations
- Safety-critical implementation changes
- Language or format standardization
- Breaking changes requiring downstream updates

### Handoff Structure
1. **Context**: Why the change was needed
2. **Scope**: What was changed
3. **Implementation**: How it was done
4. **Validation**: How success was verified
5. **Impact**: Downstream effects and required actions
6. **Related Docs**: Links to relevant protocol/code

### Naming Convention
`HANDOFF__[TOPIC]__[AFFECTED_SYSTEMS]__[DATE].md`

Example:
- `HANDOFF__MEDTERM_ENGLISH_ONLY__S2_APPSHEET_ANKI__2026-01-07.md`

---

## Execution Safety Context

This handoff folder is part of the Execution Safety protocol structure:

### Parent Folder: `0_Protocol/01_Execution_Safety/`

**Contains**:
- Fail-Fast policies
- Abort rules
- Safety mechanisms
- Batch processing history
- Stabilization plans
- Prompt rendering safety rules

### Related Safety Documents
- `Batch_Processing_History.md` - Batch API execution records
- `Prompt_Rendering_Safety_Rule.md` - Prompt safety guidelines
- `stabilization/` - S2 stabilization plans and checks

---

## Archive Policy

- Active handoffs remain in this folder until superseded
- Superseded handoffs move to `archived/` subfolder
- Original implementation scripts archived separately (e.g., `3_Code/archived/`)
- Maintain for reproducibility and audit trail

---

## Usage Guidelines

### For Developers
- Read relevant handoffs before modifying affected systems
- Create new handoff when implementing major changes
- Link handoffs in code comments for context
- Update related documentation references

### For Reviewers
- Check handoffs for impact assessment
- Verify downstream changes are documented
- Ensure validation procedures are complete
- Confirm related docs are updated

### For Auditors
- Handoffs provide change history for safety-critical systems
- Cross-reference with git commits and frozen tags
- Verify protocol alignment with implementation

---

**Maintained By**: MeducAI Execution Safety Team  
**Contact**: Refer to main Protocol documentation for contacts


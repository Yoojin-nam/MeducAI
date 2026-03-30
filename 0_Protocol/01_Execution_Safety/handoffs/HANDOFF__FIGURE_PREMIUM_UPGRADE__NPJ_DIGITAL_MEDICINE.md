# HANDOFF: Premium Figure Upgrade (npj Digital Medicine)

**Date**: 2026-03-30
**Target Agents**: Claude Code (Manuscript Writer/Data Analyst)
**Objective**: Ensure all generated figures for Paper 1, Paper 2, and Paper 3 comply strictly with **Nature Portfolio (npj Digital Medicine)** submission standards.

---

## 1. Context & Motivation

We are preparing to submit the MeducAI manuscript(s) to *npj Digital Medicine*. Because Nature Portfolio has extremely strict artwork and visualization requirements, we have completely overhauled the project's figure generation ecosystem. You (the agent) must utilize these new assets whenever you assist the user in drafting the manuscript, analyzing clinical statistics, or updating the S0-S6 architecture diagrams.

## 2. Implemented Assets & Your Guidelines

### A. Data/Statistical Plots (Python)
Whenever you are asked to generate or modify Python plotting scripts (e.g., using `matplotlib` or `seaborn`) to analyze Survey results, MLLM scores, or any numerical data, **you MUST import and enforce the new MeducAI Nature Portfolio theme**:
- **Location**: `3_Code/src/tools/meducai_plot_theme.py`
- **Action Required**: Import `apply_npj_theme` and `NPJ_PALETTE`, and apply it to the `matplotlib` context before plotting. Do not rely on default seaborn styles.
- **Reference Example**: `3_Code/src/tools/qa/example_npj_plot_survey_results.py` shows how to create a 600 DPI, 89mm (single column width) bar chart.

### B. Flowcharts and Study Diagrams (Architecture)
Whenever you advise the user on updating `MeducAI_Research_Overview.pptx` or building CONSORT flow diagrams:
- **Location**: `0_Protocol/06_QA_and_Study/Figure_Premium_Design_Guide.md`
- **Action Required**: Enforce the exact specifications in this guide. Flowcharts must be designed tightly to 89mm or 183mm width, use Arial/Helvetica (5-8pt only), single line widths of 0.5-1.0pt, and export as vector graphics (PDF/EPS). Colorblind-friendly sRGB palettes are mandatory.

### C. MLLM Generated Images (Paper 2 Target)
The MeducAI Image Generator (S4) system prompts have been updated to enforce a premium, minimalist editorial aesthetic (similar to NEJM/Radiology standards) out of the box.
- **Updated Prompt**: `3_Code/prompt/S4_EXAM_SYSTEM__S5R3__v11_DIAGRAM_4x5_2K.md`
- **Action Required**: When reviewing MLLM image outputs for Paper 2, note that the prompts now strictly forbid photorealism, bright primary colors, and cartoonish 3D assets, enforcing instead a flat tone, vector-like textbook diagram look.

## 3. Strict Rules for Claude Code

1. **Do not use default Matplotlib/Seaborn themes** for any manuscript figures. If you create a new Python script to analyze data, always use `apply_npj_theme`.
2. **Never suggest adding titles or large labels above 8pt** for formal PDF outputs.
3. **Always output line art and charts as PDF (600 DPI)** via `plt.savefig(path, format='pdf', dpi=600)`. Do not save as PNG/JPEG unless strictly analyzing pixel data.
4. If you need to evaluate if an existing flowchart is compliant, cross-reference it with `Figure_Premium_Design_Guide.md`.

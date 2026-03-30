---
name: meducai
description: MeducAI project-specific context, data locations, and analysis helpers. Provides pipeline stage context (S1–S6–FINAL), data file mapping, AppSheet warnings, and quick-start commands for Paper 1 (S5 Multi-agent Validation) and Paper 3 (Educational Effectiveness) analyses.
triggers: meducai, paper1, paper 1, paper3, paper 3, s5 validation, qa data, appsheet, pipeline stage, meducai stats, meducai analysis
tools: Read, Write, Edit, Bash, Grep, Glob
model: inherit
---

# MeducAI Project Skill

## Project Overview

**MeducAI**: LLM-based radiology medical education content generation pipeline
- 7-stage pipeline: S1 → S2 → S3 → S4 → S5 → S6 → FINAL
- Outputs: 6,000 Anki flashcards + 833 infographics
- Protocol version: v1.3.1 (frozen)
- 3-paper portfolio (Papers 1, 2, 3)

---

## Pipeline Stage Reference

| Stage | Name | Description | Key Output |
|-------|------|-------------|------------|
| S1 | Topic Generation | LLM generates radiology topics from syllabus | Topic list |
| S2 | Content Draft | LLM drafts Q&A flashcard content | Raw flashcards |
| S3 | Review Filter | First LLM filter for accuracy | Filtered cards |
| S4 | Infographic Generation | MLLM generates infographics from flashcard text | PNG infographics |
| S5 | Multi-agent QA | Multi-agent LLM validates flashcards + infographics | QA reports, REGEN tags |
| S6 | Final Integration | Combines validated content | Anki deck package |
| FINAL | Distribution | Resident deployment + tracking | AppSheet records |

---

## ⚠️ CRITICAL DATA WARNINGS — READ BEFORE ANY ANALYSIS

### Warning 1: AppSheet Time Columns Are Unreliable

**DO NOT USE:** `post_duration_sec`, `s5_duration_sec`

These columns were calculated by AppSheet using a buggy formula. They do not reflect actual time spent.

**ALWAYS RECALCULATE** from raw timestamps:
```python
# Correct approach — recalculate from timestamps
df['actual_duration_sec'] = (
    pd.to_datetime(df['timestamp_end']) -
    pd.to_datetime(df['timestamp_start'])
).dt.total_seconds()
```

Full details: `0_Protocol/06_QA_and_Study/QA_Operations/handoffs/APPSHEET_TIME_CALCULATION_ISSUE_2026-01-09.md`

### Warning 2: REGEN Count Exceeded Protocol Limit

- **Planned cap:** 200 REGEN cards
- **Actual count:** 263 REGEN cards (31.5% over cap)
- **Action:** Document as protocol deviation in Paper 1 Methods; include in Limitations

Full details: `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/Paper1_QA_Validation_Report.md`

---

## Paper 1: S5 Multi-agent Validation

### Research Question

Does multi-agent LLM quality assurance produce reliable and accurate validation of AI-generated radiology education content?

### Data Locations

```
2_Data/
├── qa_responses/FINAL_DISTRIBUTION/          ← Primary QA data (de-identified)
│   ├── qa_responses_final.csv                ← Main data file
│   └── reviewer_master.csv                   ← Reviewer metadata (anonymized)
├── qa_appsheet_export/                        ← Raw AppSheet exports (backup)
│   └── *.csv                                 ← Raw exports (time columns unreliable!)
└── metadata/generated/FINAL_DISTRIBUTION/    ← Pipeline output metadata
```

### Target Journal

**Primary:** Radiology:AI
**Backup:** npj Digital Medicine, Journal of the American Medical Informatics Association (JAMIA)

### Analysis Plan

#### Primary Outcome: Inter-rater Agreement
```python
# ICC for Q-sort evaluation scores
# Use: analyze-stats/references/templates/agreement_analysis.py
# ICC model: two-way mixed, absolute agreement, average measures
```

#### Secondary Outcomes

| Metric | Method | Template |
|--------|--------|----------|
| False Negative Rate (FNR) | Clopper-Pearson exact 95% CI | Custom (see below) |
| Human vs LLM error detection | McNemar test (paired) | Custom |
| REGEN card characteristics | Descriptive + chi-square | table1_demographics.py |
| Time per evaluation | Mann-Whitney U | Custom |

#### FNR Calculation Template

```python
from scipy import stats
import numpy as np

# FNR = False Negatives / (False Negatives + True Positives)
# Clopper-Pearson exact 95% CI
def fnr_with_ci(fn, tp, alpha=0.05):
    """
    fn: number of false negatives
    tp: number of true positives
    Returns: FNR, CI_lower, CI_upper
    """
    n = fn + tp  # total positives
    k = fn       # false negatives
    fnr = k / n
    ci_lower, ci_upper = stats.beta.ppf(
        [alpha/2, 1-alpha/2],
        a=[k, k+1],
        b=[n-k+1, n-k]
    )
    return fnr, ci_lower, ci_upper
```

#### McNemar Test (Human vs LLM error detection)

```python
from statsmodels.stats.contingency_tables import mcnemar

# Contingency table:
# Cell a: both Human and LLM detected error
# Cell b: Human detected, LLM missed (FN for LLM)
# Cell c: LLM detected, Human missed (FN for Human)
# Cell d: both missed
table = [[a, b], [c, d]]
result = mcnemar(table, exact=True)  # exact=True for small N
print(f"McNemar statistic: {result.statistic:.3f}")
print(f"P-value: {result.pvalue:.3f}")
```

### Table Shells (Paper 1)

**Table 1**: Characteristics of evaluated QA cards

| Variable | All Cards | Standard Cards | REGEN Cards | P value |
|----------|-----------|----------------|-------------|---------|
| N | | | | |
| Topic category, n (%) | | | | |
| Pipeline stage, n (%) | | | | |
| ... | | | | |

**Table 2**: Inter-rater agreement (ICC)

| Metric | ICC | 95% CI | Interpretation |
|--------|-----|--------|----------------|
| Overall Q-sort agreement | | | |
| LLM-A vs LLM-B | | | |
| LLM vs Human-expert | | | |

**Table 3**: False Negative Rates

| Evaluator type | N errors | N detected | FNR (%) | 95% CI |
|----------------|----------|------------|---------|--------|
| Human reviewers | | | | |
| Multi-agent LLM | | | | |

---

## Paper 3: Educational Effectiveness

### Research Question

Does MeducAI-generated flashcard content improve radiology knowledge retention among medical students compared to traditional study materials?

### Data Location

```
2_Data/survey_responses/              ← Survey data
├── pre_survey_*.csv                  ← Pre-intervention survey
├── post_survey_*.csv                 ← Post-intervention survey
└── demographic_*.csv                 ← Participant demographics
```

### Analysis Plan

| Analysis | Method | Template |
|----------|--------|----------|
| Pre-post knowledge comparison | Wilcoxon signed-rank (paired) | Custom |
| Likert satisfaction scores | Descriptive + Cronbach's alpha | likert_summary.py |
| Subgroup: intern vs resident | Mann-Whitney U | table1_demographics.py |
| Effect size | Cohen's d or rank-biserial r | Calculate with pingouin |

---

## Quick Commands

### `paper1-stats`

Run Paper 1 primary analysis:
```bash
# 1. Check data integrity first
python -c "
import pandas as pd
df = pd.read_csv('2_Data/qa_responses/FINAL_DISTRIBUTION/qa_responses_final.csv')
print('Shape:', df.shape)
print('Columns:', df.columns.tolist())
print('Missing values:', df.isnull().sum())
# Verify time column issue
if 'post_duration_sec' in df.columns:
    print('WARNING: post_duration_sec present — recalculate from timestamps!')
"

# 2. Run agreement analysis
cp ~/.claude/skills/analyze-stats/references/templates/agreement_analysis.py analysis/scripts/
python analysis/scripts/agreement_analysis.py

# 3. Calculate FNR with CI
# (see FNR template above)
```

### `paper3-stats`

Run Paper 3 survey analysis:
```bash
cp ~/.claude/skills/analyze-stats/references/templates/likert_summary.py analysis/scripts/
python analysis/scripts/likert_summary.py
```

### `check-data`

Verify data integrity before analysis:
```python
import pandas as pd

# Load data
df = pd.read_csv('2_Data/qa_responses/FINAL_DISTRIBUTION/qa_responses_final.csv')

# Check 1: AppSheet time column warning
time_cols = ['post_duration_sec', 's5_duration_sec']
for col in time_cols:
    if col in df.columns:
        print(f"⚠️ WARNING: '{col}' present — DO NOT USE. Recalculate from timestamps.")

# Check 2: REGEN count
if 'card_type' in df.columns:
    regen_count = (df['card_type'] == 'REGEN').sum()
    print(f"REGEN count: {regen_count} (protocol cap: 200)")
    if regen_count > 200:
        print(f"⚠️ PROTOCOL DEVIATION: {regen_count - 200} excess REGEN cards")

# Check 3: Completeness
print(f"\nData completeness:")
for col in df.columns:
    pct_complete = (df[col].notna().sum() / len(df)) * 100
    if pct_complete < 95:
        print(f"  {col}: {pct_complete:.1f}% complete")

print("\nData check complete.")
```

---

## Manuscript File Locations

```
7_Manuscript/
├── drafts/Paper1/                   ← Paper 1 Quarto manuscript
│   ├── main.qmd
│   └── sections/
├── drafts/Main Body.gdoc            ← Google Docs draft (Paper 1 main body)
├── figures/                         ← Publication figures
└── references/
    ├── library.bib                  ← BibTeX
    └── *.pdf                        ← Reference PDFs
```

---

## Key Protocol Documents

| Document | Path | Purpose |
|----------|------|---------|
| Master index | `0_Protocol/06_QA_and_Study/MeducAI_3Paper_Research_Index.md` | Overview of all 3 papers |
| Manuscript status | `0_Protocol/06_QA_and_Study/MeducAI_Manuscript_Preparation_Status.md` | Current writing status |
| Paper 1 design | `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/` | Paper 1 analysis plan |
| AppSheet warning | `0_Protocol/06_QA_and_Study/QA_Operations/handoffs/APPSHEET_TIME_CALCULATION_ISSUE_2026-01-09.md` | Time column bug details |
| QA validation report | `0_Protocol/06_QA_and_Study/Paper1_S5_Validation/Paper1_QA_Validation_Report.md` | REGEN count details |

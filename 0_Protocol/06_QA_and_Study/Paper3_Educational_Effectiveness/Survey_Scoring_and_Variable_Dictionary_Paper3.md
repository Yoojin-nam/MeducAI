# Paper 3 (Pipeline-2) — Survey Scoring & Variable Dictionary (1-page freeze)

**Status:** Canonical helper (analysis-ready; freeze before data analysis)  
**Scope:** Paper 3 user study (Prospective observational; user vs non-user comparison)  

This document defines:
- **exposure definitions** (user/non-user, dose),
- **outcome scoring** (baseline→final change scores \(\Delta\)),
- and a minimal **variable dictionary** for reproducible analysis and manuscript Methods.

---

## 1) Where variables come from (SSOT)

- **Baseline (consent + baseline survey, Google Apps Script)**: `3_Code/Scripts/create_google_form_baseline.js`
  - Cognitive load items: `F11-1` ~ `F13-3` (1–7)
  - Self-efficacy items: `F14-1` ~ `F14-5` (1–7)
  - Behavioral/emotional covariates: `F15-1` ~ `F15-5`
  - LLM covariates: `F7` ~ `F10`
  - Training context: `F2`, `F3`, `F5`, `F6`
- **Final (post-exam survey)**:
  - Survey spec: `0_Protocol/05_Pipeline_and_Execution/meduc_ai_final_survey_form.md`
  - Google Form generator: `3_Code/Scripts/create_google_form_final.js`
  - Manual item text: `0_Protocol/05_Pipeline_and_Execution/google_form_items_baseline_and_final.md`

---

## 2) Exposure definitions (primary comparison)

- **User (binary)**: `A1 == "예"`
- **Non-user (binary)**: `A1 == "아니오 (사용하지 않음)"`

### Dose / intensity (users only)
- **Dose_hours (continuous)**: `A5` (total hours of MeducAI usage; numeric)
- **Components_used (multi-select)**: `A4` (Anki / Table / Slide / Other)

### Non-user implementation context
- **Exposure_to_materials (binary)**: `N1` (received/encountered vs not)
- **Nonuse_reasons (multi-select)**: `N2`
- **Future_intent_if_nonuser (1–5)**: `N3`

---

## 3) Outcomes to compare between users vs non-users (baseline→final change, \(\Delta\))

### 3.1 Extraneous cognitive load (co-primary construct; **subscale subset**)

> **Reference note (Methods-ready):** We operationalize *extraneous cognitive load* using **3 adapted items** aligned to the extraneous subdomain of the multi-dimensional cognitive load scale (Leppink et al., 2013), and report change scores from baseline to post-exam.

**Baseline items (1–7):**
- `F11-1` “학습 자료의 구성이나 표현 방식 때문에 불필요하게 머리가 복잡하다고 느낀다.”
- `F11-2` “필요한 정보를 찾기 위해 자료를 이리저리 찾아보는 데 많은 노력이 든다.”
- `F11-3` “학습 도구의 사용 방식이 직관적이지 않아 학습 흐름이 끊긴다고 느낀다.”

**Final common items (1–7):**
- `Z1`, `Z2`, `Z3` (exam-prep period; **referent is the learner’s overall study materials/tools used during the period**, not MeducAI-only; applies to all respondents)

**Score definition:**
- `ECL_baseline = mean(F11-1, F11-2, F11-3)`
- `ECL_final = mean(Z1, Z2, Z3)`
- `ΔECL = ECL_final - ECL_baseline`

**Interpretation:**
- Higher score = higher extraneous load (worse).  
  \(\Delta ECL < 0\) implies improvement **in overall study-environment extraneous load** (not isolated MeducAI-only burden).

### 3.2 Self-efficacy (matched single item for change scoring)

**Baseline (1–7):**
- `F14-4` “시험에 필요한 핵심 개념을 이해하는 데 자신이 있다.”

**Final common (1–7):**
- `Z9` (same statement)

**Score definition:**
- `SE_baseline = F14-4`
- `SE_final = Z9`
- `ΔSE = SE_final - SE_baseline`

**Interpretation:**
- Higher score = higher self-efficacy (better).  
  \(\Delta SE > 0\) implies improvement.

---

## 4) Key covariates (minimal adjustment set)

Use baseline covariates for adjustment; use final common Z-items for descriptive/sensitivity checks.

### Baseline covariates (recommended minimum)
- **Training context**
  - `F2` rotation
  - `F3` study hours per week (categorical)
  - `F5` learning tools (multi-select)
  - `F6` Anki usage (optional)
- **LLM/AI experience**
  - `F7` prior LLM use (yes/no)
  - `F8` clinical LLM use (optional; conditional)
  - `F9` LLM knowledge (1–5)
  - `F10` LLM trust (1–5)
- **Behavioral/emotional baseline**
  - `F15-1` stress (1–7)
  - `F15-2` sleep duration (categorical)
  - `F15-3` sleep quality (1–7)
  - `F15-4` mood (1–7)
  - `F15-5` exercise frequency (categorical)

### Final common (all respondents; for interpretation / sensitivity)
- `Z4–Z8` (stress/sleep/mood/exercise)

---

## 5) User-only outcomes (not comparable to non-users)

These are valid and important but should be analyzed **within users** or descriptively:
- Educational quality / exam utility: `B1–B4` (1–5)
- Technical accuracy (perceived): `C1–C4` (+ narrative)
- Efficiency: `D1–D4`
- Trust / calibration: `E1–E3`
- Satisfaction / TAM: `G1–G5`
- NPS / recommendation: `H1` (0–10), improvement target `H3`

---

## 6) Coding conventions (analysis-ready)

- Likert items are treated as numeric with bounded ranges (1–5, 1–7).
- Multi-select items are expanded to binary indicators per option (0/1).
- Non-user “received/encountered” (N1) is used for stratified sensitivity analyses:
  - **Received but did not use** vs **Did not receive/unknown**

---

## 7) Analysis template (manuscript-ready; copy/paste)

### 7.1 Primary estimand (observational; association, not RCT causality)

We compared baseline-to-post change scores between participants who used MeducAI (A1=Yes) and those who did not (A1=No).

**Outcomes (change scores):**
- \(\Delta ECL = ECL_{final} - ECL_{baseline}\)
- \(\Delta SE = SE_{final} - SE_{baseline}\)

### 7.2 Primary model (adjusted change-score regression)

For each outcome \(\Delta Y\), we fit:

\[
\Delta Y_i = \beta_0 + \beta_1 \cdot \text{User}_i + \gamma^\top X_i + \varepsilon_i
\]

where:
- \(\text{User}_i\) is a binary indicator (A1=Yes),
- \(X_i\) is the **minimal baseline covariate set** (training context, baseline study intensity/strategy, LLM experience, baseline behavioral/emotional factors; see Section 4),
- \(\beta_1\) is interpreted as the adjusted association between MeducAI use and change in outcome.

### 7.3 Dose–response (users only; exploratory)

Among users, we explored:

\[
\Delta Y_i = \alpha_0 + \alpha_1 \cdot \text{Dose\_hours}_i + \gamma^\top X_i + \varepsilon_i
\]

Optionally, we additionally included component indicators from A4 (Anki/Table/Slide).

### 7.4 Sensitivity analyses (selection/implementation context)

- **Stratified non-user analysis:** Among non-users, we stratified by N1:
  - received/encountered vs did not receive/unknown,
  and compared \(\Delta Y\) descriptively (and/or with the same adjusted model).
- **Propensity weighting (optional):** We estimated a propensity score \(p(User=1|X)\) using baseline covariates and applied inverse probability weights (IPW) to estimate weighted differences in \(\Delta Y\).

### 7.5 Minimal pseudo-code (R-like)

```r
# Inputs: baseline_df, final_df merged by participant_id

# Scores
ECL_baseline <- rowMeans(baseline_df[, c("F11_1","F11_2","F11_3")], na.rm = TRUE)
ECL_final    <- rowMeans(final_df[, c("Z1","Z2","Z3")], na.rm = TRUE)
delta_ECL    <- ECL_final - ECL_baseline

SE_baseline  <- baseline_df$F14_4
SE_final     <- final_df$Z9
delta_SE     <- SE_final - SE_baseline

# User indicator
User <- final_df$A1_yes

# Adjusted model
fit <- lm(delta_ECL ~ User + rotation + study_hours_cat + llm_knowledge + llm_trust + stress + sleep_cat + sleep_quality + mood + exercise, data = df)
summary(fit)
```

> Note: Exact column names depend on the export schema; treat this snippet as a template.



"""
Paper 1: S5 Multi-agent Validation — De-identification & Statistical Analysis
==============================================================================
Reads raw AppSheet export (PII), de-identifies, exports analysis-ready CSVs,
and runs all pre-specified statistical analyses.

Outputs:
  2_Data/qa_responses/FINAL_DISTRIBUTION/
    ├── ratings_deidentified.csv
    ├── cards_analysis.csv
    ├── rater_summary.csv
    └── analysis/
        ├── paper1_results.txt          (console-readable summary)
        ├── table1_card_characteristics.csv
        ├── table2_fnr_results.csv
        ├── table3_pre_post_change.csv
        ├── table4_icc_results.csv
        ├── table5_regen_acceptance.csv
        └── figures/  (placeholder for future figures)

Random seed: 42
Python >=3.10, pandas, scipy, statsmodels, pingouin
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore", category=FutureWarning)
np.random.seed(42)

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT = Path("/Users/eugene/workspace/MeducAI")
SRC_XLSX = PROJECT / "1_Secure_Participant_Info/QA_Operations/FINAL_DISTRIBUTION/appsheet.xlsx"
OUT_DIR = PROJECT / "2_Data/qa_responses/FINAL_DISTRIBUTION"
ANALYSIS_DIR = OUT_DIR / "analysis"
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

# ── 1. Load raw data ────────────────────────────────────────────────────────
print("=" * 70)
print("STEP 1: Loading raw data")
print("=" * 70)

ratings_raw = pd.read_excel(SRC_XLSX, sheet_name="Ratings")
cards = pd.read_excel(SRC_XLSX, sheet_name="Cards")
assignments = pd.read_excel(SRC_XLSX, sheet_name="Assignments")
s5 = pd.read_excel(SRC_XLSX, sheet_name="S5")
user_sheet = pd.read_excel(SRC_XLSX, sheet_name="user_sheet")

print(f"  Ratings:     {len(ratings_raw):,} rows")
print(f"  Cards:       {len(cards):,} rows")
print(f"  Assignments: {len(assignments):,} rows")
print(f"  S5:          {len(s5):,} rows")
print(f"  Raters:      {len(user_sheet):,}")

# ── 2. De-identify ──────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("STEP 2: De-identification")
print("=" * 70)

# Create surrogate rater IDs (deterministic from sorted email)
email_to_role = dict(zip(user_sheet["Email"], user_sheet["Role"]))
emails_sorted = sorted(user_sheet["Email"].tolist())
email_to_surrogate = {
    email: f"R{i+1:02d}" for i, email in enumerate(emails_sorted)
}

# Build rater summary (de-identified)
rater_summary = []
for email, surr_id in email_to_surrogate.items():
    role = email_to_role.get(email, "unknown")
    n_ratings = (ratings_raw["rater_email"] == email).sum()
    n_assigned = (assignments["rater_email"] == email).sum()
    rater_summary.append({
        "rater_id": surr_id,
        "role": role,
        "n_assigned": n_assigned,
        "n_completed": n_ratings,
        "completion_pct": round(n_ratings / n_assigned * 100, 1) if n_assigned > 0 else 0,
    })
rater_summary_df = pd.DataFrame(rater_summary).sort_values("rater_id")

# De-identify ratings
ratings = ratings_raw.copy()
ratings["rater_id"] = ratings["rater_email"].map(email_to_surrogate)
ratings = ratings.drop(columns=["rater_email"])

# Recalculate durations from timestamps (AppSheet duration columns unreliable)
for prefix in ["pre", "post", "realistic_image", "s5"]:
    start_col = f"{prefix}_started_ts"
    end_col = f"{prefix}_submitted_ts"
    dur_col = f"{prefix}_duration_sec_calc"
    if start_col in ratings.columns and end_col in ratings.columns:
        start = pd.to_datetime(ratings[start_col], errors="coerce")
        end = pd.to_datetime(ratings[end_col], errors="coerce")
        ratings[dur_col] = (end - start).dt.total_seconds()

# Drop unreliable AppSheet duration columns
unreliable_cols = ["pre_duration_sec", "post_duration_sec",
                   "realistic_image_duration_sec", "s5_duration_sec"]
ratings = ratings.drop(columns=[c for c in unreliable_cols if c in ratings.columns])

# Merge s5_decision onto ratings
ratings = ratings.merge(
    cards[["card_uid", "s5_decision"]].rename(columns={"s5_decision": "card_s5_decision"}),
    on="card_uid", how="left"
)

# Merge calibration flag from assignments (via card_uid + rater mapping)
# Since assignment_id is NaN in ratings, use card_uid to get calibration status
cal_cards = set(assignments[assignments["is_calibration"] == 1]["card_uid"].unique())
ratings["is_calibration"] = ratings["card_uid"].isin(cal_cards).astype(int)

print(f"  Surrogate IDs assigned: {len(email_to_surrogate)}")
print(f"  Duration columns recalculated from timestamps")
print(f"  Unreliable AppSheet duration columns dropped")

# ── 3. Export de-identified data ────────────────────────────────────────────
print("\n" + "=" * 70)
print("STEP 3: Exporting de-identified datasets")
print("=" * 70)

# Cards analysis (no PII, add S5 scores)
cards_analysis = cards.merge(
    s5[["card_uid", "s5_blocking_error", "s5_technical_accuracy",
        "s5_educational_quality", "s5_was_regenerated",
        "s5_card_image_blocking_error", "s5_card_image_anatomical_accuracy"]],
    on="card_uid", how="left"
)

ratings.to_csv(OUT_DIR / "ratings_deidentified.csv", index=False)
cards_analysis.to_csv(OUT_DIR / "cards_analysis.csv", index=False)
rater_summary_df.to_csv(OUT_DIR / "rater_summary.csv", index=False)

print(f"  ratings_deidentified.csv: {len(ratings):,} rows")
print(f"  cards_analysis.csv:       {len(cards_analysis):,} rows")
print(f"  rater_summary.csv:        {len(rater_summary_df):,} rows")

# ══════════════════════════════════════════════════════════════════════════════
# STATISTICAL ANALYSES
# ══════════════════════════════════════════════════════════════════════════════
results_lines = []


def log(msg=""):
    print(msg)
    results_lines.append(msg)


log("\n" + "=" * 70)
log("PAPER 1 STATISTICAL ANALYSIS RESULTS")
log("=" * 70)
log(f"Analysis date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
log(f"Total ratings: {len(ratings):,}")
log(f"Total cards:   {len(cards):,}")
log(f"Total raters:  {ratings['rater_id'].nunique()}")

# ── A. Descriptive Statistics (Table 1) ─────────────────────────────────────
log("\n" + "-" * 70)
log("A. DESCRIPTIVE STATISTICS")
log("-" * 70)

# Card characteristics by s5_decision
card_desc = []
for decision in ["PASS", "CARD_REGEN", "IMAGE_REGEN"]:
    subset = cards_analysis[cards_analysis["s5_decision"] == decision]
    card_desc.append({
        "s5_decision": decision,
        "n_cards": len(subset),
        "pct": round(len(subset) / len(cards_analysis) * 100, 1),
        "card_type_BASIC_n": (subset["card_type"] == "BASIC").sum(),
        "card_type_MCQ_n": (subset["card_type"] == "MCQ").sum(),
        "card_role_Q1_n": (subset["card_role"] == "Q1").sum(),
        "card_role_Q2_n": (subset["card_role"] == "Q2").sum(),
    })
# Total row
total = cards_analysis
card_desc.append({
    "s5_decision": "Total",
    "n_cards": len(total),
    "pct": 100.0,
    "card_type_BASIC_n": (total["card_type"] == "BASIC").sum(),
    "card_type_MCQ_n": (total["card_type"] == "MCQ").sum(),
    "card_role_Q1_n": (total["card_role"] == "Q1").sum(),
    "card_role_Q2_n": (total["card_role"] == "Q2").sum(),
})
table1 = pd.DataFrame(card_desc)
table1.to_csv(ANALYSIS_DIR / "table1_card_characteristics.csv", index=False)

log("\nTable 1: Card Characteristics by S5 Decision")
log(table1.to_string(index=False))

# Rater summary
log("\nRater Summary:")
log(rater_summary_df.to_string(index=False))

# Rating distributions
log("\nRating Distributions (Pre-correction phase):")
log(f"  blocking_error_pre:      Yes={ratings['blocking_error_pre'].eq('Yes').sum()}, "
    f"No={ratings['blocking_error_pre'].eq('No').sum()}")
log(f"  technical_accuracy_pre:  0={ratings['technical_accuracy_pre'].eq(0).sum()}, "
    f"0.5={ratings['technical_accuracy_pre'].eq(0.5).sum()}, "
    f"1={ratings['technical_accuracy_pre'].eq(1.0).sum()}")
log(f"  educational_quality_pre: " +
    ", ".join(f"{v}={ratings['educational_quality_pre'].eq(v).sum()}" for v in [1, 2, 3, 4, 5]))

# ── B. PRIMARY: False Negative Rate (FNR) ──────────────────────────────────
log("\n" + "-" * 70)
log("B. PRIMARY ENDPOINT: False Negative Rate (FNR)")
log("-" * 70)
log("Definition: S5 marked PASS, but human reviewer flagged blocking_error = Yes")
log("Unit of analysis: per-rating (each human evaluation of an S5-PASS card)")


def clopper_pearson_ci(k, n, alpha=0.05):
    """Exact Clopper-Pearson confidence interval."""
    if n == 0:
        return np.nan, np.nan, np.nan
    p = k / n
    if k == 0:
        ci_low = 0.0
    else:
        ci_low = stats.beta.ppf(alpha / 2, k, n - k + 1)
    if k == n:
        ci_high = 1.0
    else:
        ci_high = stats.beta.ppf(1 - alpha / 2, k + 1, n - k)
    return p, ci_low, ci_high


# FNR for S5-PASS cards
pass_ratings = ratings[ratings["card_s5_decision"] == "PASS"].copy()
n_pass_ratings = len(pass_ratings)
fn_count = pass_ratings["blocking_error_pre"].eq("Yes").sum()
fnr, fnr_ci_low, fnr_ci_high = clopper_pearson_ci(fn_count, n_pass_ratings)

log(f"\nS5-PASS cards evaluated: {pass_ratings['card_uid'].nunique()} unique cards")
log(f"S5-PASS ratings (N):    {n_pass_ratings}")
log(f"False Negatives (blocking_error=Yes among PASS): {fn_count}")
log(f"FNR = {fn_count}/{n_pass_ratings} = {fnr:.4f} ({fnr*100:.2f}%)")
log(f"95% CI (Clopper-Pearson): [{fnr_ci_low:.4f}, {fnr_ci_high:.4f}] "
    f"([{fnr_ci_low*100:.2f}%, {fnr_ci_high*100:.2f}%])")

# Safety threshold test: FNR < 0.3% (one-sided)
threshold = 0.003
# One-sided 95% upper bound
if fn_count == n_pass_ratings:
    fnr_upper_one_sided = 1.0
else:
    fnr_upper_one_sided = stats.beta.ppf(0.95, fn_count + 1, n_pass_ratings - fn_count)

safety_pass = fnr_upper_one_sided <= threshold
log(f"\nSafety Threshold Test:")
log(f"  H0: FNR >= 0.3%  vs  H1: FNR < 0.3%")
log(f"  One-sided 95% upper bound: {fnr_upper_one_sided:.4f} ({fnr_upper_one_sided*100:.2f}%)")
log(f"  Threshold: {threshold*100:.1f}%")
log(f"  Result: {'PASS ✓' if safety_pass else 'FAIL ✗'}")

# Also compute FNR by rater role
fnr_results = []
for role in ["resident", "attending"]:
    role_raters = set(user_sheet[user_sheet["Role"] == role]["Email"])
    role_surrogates = {email_to_surrogate[e] for e in role_raters}
    role_pass = pass_ratings[pass_ratings["rater_id"].isin(role_surrogates)]
    n_r = len(role_pass)
    fn_r = role_pass["blocking_error_pre"].eq("Yes").sum()
    p_r, ci_l, ci_h = clopper_pearson_ci(fn_r, n_r)
    fnr_results.append({
        "group": role,
        "n_ratings": n_r,
        "n_false_negatives": fn_r,
        "fnr_pct": round(p_r * 100, 2) if not np.isnan(p_r) else np.nan,
        "ci_lower_pct": round(ci_l * 100, 2) if not np.isnan(ci_l) else np.nan,
        "ci_upper_pct": round(ci_h * 100, 2) if not np.isnan(ci_h) else np.nan,
    })

# Overall
fnr_results.append({
    "group": "overall",
    "n_ratings": n_pass_ratings,
    "n_false_negatives": fn_count,
    "fnr_pct": round(fnr * 100, 2),
    "ci_lower_pct": round(fnr_ci_low * 100, 2),
    "ci_upper_pct": round(fnr_ci_high * 100, 2),
})
table2 = pd.DataFrame(fnr_results)
table2.to_csv(ANALYSIS_DIR / "table2_fnr_results.csv", index=False)

log("\nFNR by Rater Role:")
log(table2.to_string(index=False))

# ── C. SECONDARY: Pre→Post Change (McNemar) ────────────────────────────────
log("\n" + "-" * 70)
log("C. SECONDARY: Pre → Post Change Analysis (McNemar Test)")
log("-" * 70)
log("Paired comparison of blocking_error before and after seeing S5 corrections")

# Only REGEN cards have meaningful pre→post comparison (S5 made corrections)
regen_ratings = ratings[ratings["card_s5_decision"].isin(["CARD_REGEN", "IMAGE_REGEN"])].copy()
regen_with_post = regen_ratings.dropna(subset=["blocking_error_post"])

log(f"\nREGEN ratings total: {len(regen_ratings)}")
log(f"REGEN ratings with post data: {len(regen_with_post)}")

if len(regen_with_post) > 0:
    # blocking_error: pre vs post
    pre_yes = regen_with_post["blocking_error_pre"].eq("Yes")
    post_yes = regen_with_post["blocking_error_post"].eq("Yes")

    # McNemar 2×2: rows=pre, cols=post
    a = (pre_yes & post_yes).sum()      # Yes→Yes
    b = (pre_yes & ~post_yes).sum()     # Yes→No (improved)
    c = (~pre_yes & post_yes).sum()     # No→Yes (worsened)
    d = (~pre_yes & ~post_yes).sum()    # No→No

    log(f"\nBlocking Error: Pre vs Post (REGEN cards)")
    log(f"  Contingency table:")
    log(f"                    Post=Yes  Post=No")
    log(f"    Pre=Yes            {a:4d}     {b:4d}   (b: improved)")
    log(f"    Pre=No             {c:4d}     {d:4d}   (c: worsened)")

    # McNemar test (exact for small discordant cells)
    from statsmodels.stats.contingency_tables import mcnemar
    table_mcnemar = [[a, b], [c, d]]
    use_exact = (b + c) < 25
    result_mcn = mcnemar(table_mcnemar, exact=use_exact)

    log(f"\n  McNemar test ({'exact' if use_exact else 'chi-squared'}):")
    log(f"    Statistic: {result_mcn.statistic:.3f}")
    log(f"    P-value:   {result_mcn.pvalue:.4f}")
    log(f"    Discordant pairs: b={b} (improved), c={c} (worsened)")
    if b > c:
        log(f"    Direction: Net improvement (b > c)")
    elif c > b:
        log(f"    Direction: Net worsening (c > b)")
    else:
        log(f"    Direction: No net change (b = c)")

    # Also for technical_accuracy
    log(f"\nTechnical Accuracy: Pre vs Post (REGEN cards)")
    ta_pre = regen_with_post["technical_accuracy_pre"]
    ta_post = regen_with_post["technical_accuracy_post"]
    log(f"  Pre  mean: {ta_pre.mean():.3f} (SD {ta_pre.std():.3f})")
    log(f"  Post mean: {ta_post.mean():.3f} (SD {ta_post.std():.3f})")
    diff = ta_post - ta_pre
    log(f"  Diff mean: {diff.mean():.3f} (SD {diff.std():.3f})")

    # Wilcoxon signed-rank (ordinal scale 0/0.5/1)
    nonzero_diff = diff[diff != 0]
    if len(nonzero_diff) > 0:
        wsr_stat, wsr_p = stats.wilcoxon(nonzero_diff)
        log(f"  Wilcoxon signed-rank: W={wsr_stat:.1f}, p={wsr_p:.4f}")
        # Effect size: rank-biserial r
        n_nonzero = len(nonzero_diff)
        r_rb = 1 - (2 * wsr_stat) / (n_nonzero * (n_nonzero + 1) / 2)
        log(f"  Rank-biserial r: {r_rb:.3f}")
    else:
        log(f"  Wilcoxon signed-rank: not applicable (no non-zero differences)")

    # Educational quality pre vs post
    eq_pre = regen_with_post["educational_quality_pre"]
    eq_post = regen_with_post["educational_quality_post"]
    log(f"\nEducational Quality: Pre vs Post (REGEN cards)")
    log(f"  Pre  mean: {eq_pre.mean():.3f} (SD {eq_pre.std():.3f})")
    log(f"  Post mean: {eq_post.mean():.3f} (SD {eq_post.std():.3f})")
    eq_diff = eq_post - eq_pre
    nonzero_eq = eq_diff[eq_diff != 0]
    if len(nonzero_eq) > 0:
        wsr_stat2, wsr_p2 = stats.wilcoxon(nonzero_eq)
        log(f"  Wilcoxon signed-rank: W={wsr_stat2:.1f}, p={wsr_p2:.4f}")
        r_rb2 = 1 - (2 * wsr_stat2) / (len(nonzero_eq) * (len(nonzero_eq) + 1) / 2)
        log(f"  Rank-biserial r: {r_rb2:.3f}")

    table3_data = {
        "metric": ["blocking_error", "technical_accuracy", "educational_quality"],
        "n_paired": [len(regen_with_post)] * 3,
        "pre_blocking_yes": [pre_yes.sum(), None, None],
        "post_blocking_yes": [post_yes.sum(), None, None],
        "pre_mean": [None, ta_pre.mean(), eq_pre.mean()],
        "post_mean": [None, ta_post.mean(), eq_post.mean()],
        "test": ["McNemar", "Wilcoxon", "Wilcoxon"],
        "p_value": [result_mcn.pvalue,
                    wsr_p if len(nonzero_diff) > 0 else None,
                    wsr_p2 if len(nonzero_eq) > 0 else None],
    }
    table3 = pd.DataFrame(table3_data)
    table3.to_csv(ANALYSIS_DIR / "table3_pre_post_change.csv", index=False)

# ── D. ICC for Calibration Items ────────────────────────────────────────────
log("\n" + "-" * 70)
log("D. INTER-RATER RELIABILITY: ICC for Calibration Items")
log("-" * 70)

try:
    import pingouin as pg
    HAS_PINGOUIN = True
except ImportError:
    HAS_PINGOUIN = False
    log("WARNING: pingouin not installed. Attempting manual ICC calculation.")

cal_ratings = ratings[ratings["is_calibration"] == 1].copy()
log(f"\nCalibration ratings: {len(cal_ratings)}")
log(f"Unique calibration cards: {cal_ratings['card_uid'].nunique()}")
log(f"Raters per calibration card:")
raters_per_card = cal_ratings.groupby("card_uid")["rater_id"].nunique()
log(f"  Mean: {raters_per_card.mean():.1f}, Min: {raters_per_card.min()}, Max: {raters_per_card.max()}")

# Only resident calibration items (designed for 3 residents each)
resident_surrogates = {email_to_surrogate[e] for e in user_sheet[user_sheet["Role"] == "resident"]["Email"]}
cal_resident = cal_ratings[cal_ratings["rater_id"].isin(resident_surrogates)]
log(f"\nResident calibration ratings: {len(cal_resident)}")
log(f"Unique cards with resident calibration: {cal_resident['card_uid'].nunique()}")

icc_results = []

# Use ALL calibration ratings (residents + attendings) for ICC
# Pingouin requires balanced data: pivot to wide, keep complete cases
cal_all = cal_ratings.copy()
log(f"\nUsing all calibration ratings (residents + attendings): {len(cal_all)}")

for metric, col in [("technical_accuracy_pre", "technical_accuracy_pre"),
                     ("educational_quality_pre", "educational_quality_pre"),
                     ("technical_accuracy_post", "technical_accuracy_post"),
                     ("educational_quality_post", "educational_quality_post")]:
    cal_data = cal_all[["card_uid", "rater_id", col]].dropna()

    if len(cal_data) < 6:
        log(f"\n  {metric}: insufficient data ({len(cal_data)} ratings)")
        continue

    # Deduplicate (keep first rating per card-rater pair)
    cal_data = cal_data.drop_duplicates(subset=["card_uid", "rater_id"], keep="first")

    # For unbalanced design: find the most common rater count and filter
    rater_counts = cal_data.groupby("card_uid")["rater_id"].nunique()
    target_k = rater_counts.mode().iloc[0]
    balanced_cards = rater_counts[rater_counts == target_k].index
    cal_balanced = cal_data[cal_data["card_uid"].isin(balanced_cards)]

    log(f"\n  {metric}:")
    log(f"    Total calibration ratings: {len(cal_data)}")
    log(f"    Balanced subset (k={target_k} raters/item): {len(balanced_cards)} items, {len(cal_balanced)} ratings")

    if len(balanced_cards) < 3 or len(cal_balanced) < 6:
        log(f"    Skipped: too few balanced items")
        continue

    # Pingouin requires fully crossed design (same raters for all items).
    # Our calibration has different rater subsets per item.
    # Solution: pivot to wide format, use pingouin with nan_policy or
    # compute Fleiss' kappa / Krippendorff's alpha for partial overlap.
    # Alternative: find largest fully-crossed subset.
    pivot = cal_balanced.pivot(index="card_uid", columns="rater_id", values=col)

    # Find fully-crossed subset: raters who rated ALL balanced items
    rater_coverage = pivot.notna().sum(axis=0)
    full_raters = rater_coverage[rater_coverage == len(pivot)].index.tolist()

    if len(full_raters) >= 2:
        # Fully crossed subset exists
        crossed_data = pivot[full_raters].reset_index().melt(
            id_vars="card_uid", var_name="rater_id", value_name=col
        ).dropna()
        try:
            icc_df = pg.intraclass_corr(
                data=crossed_data,
                targets="card_uid",
                raters="rater_id",
                ratings=col,
            )
            for icc_type in ["ICC2k", "ICC3k"]:
                icc_row = icc_df[icc_df["Type"] == icc_type]
                if len(icc_row) > 0:
                    icc_val = icc_row["ICC"].values[0]
                    ci95 = icc_row["CI95%"].values[0]
                    pval = icc_row["pval"].values[0]
                    icc_results.append({
                        "metric": metric,
                        "ICC_type": icc_type,
                        "ICC": round(icc_val, 3),
                        "CI_lower": round(ci95[0], 3),
                        "CI_upper": round(ci95[1], 3),
                        "p_value": round(pval, 4) if pval >= 0.001 else pval,
                        "n_items": len(pivot),
                        "n_raters": len(full_raters),
                        "n_ratings": len(crossed_data),
                    })
                    log(f"    {icc_type} = {icc_val:.3f} [{ci95[0]:.3f}, {ci95[1]:.3f}], p={pval:.4f}")
                    log(f"      (fully-crossed: {len(full_raters)} raters × {len(pivot)} items)")
        except Exception as e:
            log(f"    ICC (crossed) failed: {e}")
    else:
        log(f"    No fully-crossed rater subset found (max coverage: {rater_coverage.max()}/{len(pivot)})")

        # Fallback: pairwise agreement using all available pairs
        from itertools import combinations
        pair_agreements = []
        for r1, r2 in combinations(pivot.columns, 2):
            mask = pivot[[r1, r2]].notna().all(axis=1)
            if mask.sum() >= 3:
                corr = pivot.loc[mask, r1].corr(pivot.loc[mask, r2])
                pair_agreements.append({"rater1": r1, "rater2": r2,
                                        "n_shared": mask.sum(), "pearson_r": corr})
        if pair_agreements:
            pa_df = pd.DataFrame(pair_agreements)
            mean_r = pa_df["pearson_r"].mean()
            log(f"    Pairwise Pearson r (mean): {mean_r:.3f} (n_pairs={len(pa_df)})")
            icc_results.append({
                "metric": metric,
                "ICC_type": "pairwise_r_mean",
                "ICC": round(mean_r, 3),
                "CI_lower": None, "CI_upper": None,
                "p_value": None,
                "n_items": len(pivot),
                "n_raters": len(pivot.columns),
                "n_ratings": len(cal_balanced),
            })

if icc_results:
    table4 = pd.DataFrame(icc_results)
    table4.to_csv(ANALYSIS_DIR / "table4_icc_results.csv", index=False)
    log("\nICC Results Table:")
    log(table4.to_string(index=False))

# ── E. REGEN Acceptance Analysis ────────────────────────────────────────────
log("\n" + "-" * 70)
log("E. REGEN CARD ACCEPTANCE ANALYSIS")
log("-" * 70)

regen_all = ratings[ratings["card_s5_decision"].isin(["CARD_REGEN", "IMAGE_REGEN"])].copy()
log(f"\nTotal REGEN ratings: {len(regen_all)}")
log(f"  CARD_REGEN: {(regen_all['card_s5_decision']=='CARD_REGEN').sum()}")
log(f"  IMAGE_REGEN: {(regen_all['card_s5_decision']=='IMAGE_REGEN').sum()}")

# accept_ai_correction
ai_corr = regen_all["accept_ai_correction"].dropna()
log(f"\naccept_ai_correction (n={len(ai_corr)}):")
log(ai_corr.value_counts().sort_index().to_string())
if len(ai_corr) > 0:
    accept_rate = ai_corr.isin(["Yes", "yes", True, 1, "1"]).sum()
    # Check actual values first
    log(f"\nUnique values: {ai_corr.unique()}")

# ai_correction_quality
ai_qual = regen_all["ai_correction_quality"].dropna()
log(f"\nai_correction_quality (n={len(ai_qual)}):")
log(ai_qual.value_counts().sort_index().to_string())
if len(ai_qual) > 0:
    log(f"  Mean: {ai_qual.mean():.2f}, SD: {ai_qual.std():.2f}, Median: {ai_qual.median():.1f}")

# Acceptance by s5_decision type
table5_data = []
for decision in ["CARD_REGEN", "IMAGE_REGEN"]:
    sub = regen_all[regen_all["card_s5_decision"] == decision]
    ai_sub = sub["accept_ai_correction"].dropna()
    qual_sub = sub["ai_correction_quality"].dropna()
    table5_data.append({
        "s5_decision": decision,
        "n_ratings": len(sub),
        "n_accept_responded": len(ai_sub),
        "accept_distribution": ai_sub.value_counts().to_dict() if len(ai_sub) > 0 else {},
        "n_quality_responded": len(qual_sub),
        "quality_mean": round(qual_sub.mean(), 2) if len(qual_sub) > 0 else None,
        "quality_sd": round(qual_sub.std(), 2) if len(qual_sub) > 0 else None,
        "quality_median": qual_sub.median() if len(qual_sub) > 0 else None,
    })
table5 = pd.DataFrame(table5_data)
table5.to_csv(ANALYSIS_DIR / "table5_regen_acceptance.csv", index=False)
log("\nREGEN Acceptance by Decision Type:")
log(table5.to_string(index=False))

# ── F. Supplementary: Duration Analysis ─────────────────────────────────────
log("\n" + "-" * 70)
log("F. SUPPLEMENTARY: Evaluation Duration (recalculated from timestamps)")
log("-" * 70)

for phase, col in [("Pre-correction", "pre_duration_sec_calc"),
                    ("Post-correction", "post_duration_sec_calc"),
                    ("S5 review", "s5_duration_sec_calc")]:
    if col in ratings.columns:
        valid = ratings[col].dropna()
        valid_pos = valid[valid > 0]
        if len(valid_pos) > 0:
            log(f"\n{phase} duration (seconds, n={len(valid_pos)}):")
            log(f"  Mean: {valid_pos.mean():.1f}, SD: {valid_pos.std():.1f}")
            log(f"  Median: {valid_pos.median():.1f} [IQR: {valid_pos.quantile(0.25):.1f}–{valid_pos.quantile(0.75):.1f}]")
            log(f"  Min: {valid_pos.min():.1f}, Max: {valid_pos.max():.1f}")

# ── G. Specialty-stratified FNR (Exploratory) ───────────────────────────────
log("\n" + "-" * 70)
log("G. EXPLORATORY: FNR by Specialty Group (top-level)")
log("-" * 70)

# Extract top-level specialty from group_path
pass_with_group = pass_ratings.merge(
    cards[["card_uid", "group_path"]], on="card_uid", how="left"
)
pass_with_group["specialty"] = pass_with_group["group_path"].str.split(" > ").str[0]

for spec in sorted(pass_with_group["specialty"].dropna().unique()):
    spec_data = pass_with_group[pass_with_group["specialty"] == spec]
    n_spec = len(spec_data)
    fn_spec = spec_data["blocking_error_pre"].eq("Yes").sum()
    if n_spec > 0:
        p_s, ci_l, ci_h = clopper_pearson_ci(fn_spec, n_spec)
        log(f"  {spec}: FNR={fn_spec}/{n_spec} ({p_s*100:.1f}%) "
            f"[{ci_l*100:.1f}%, {ci_h*100:.1f}%]")

# ── Save results ────────────────────────────────────────────────────────────
with open(ANALYSIS_DIR / "paper1_results.txt", "w") as f:
    f.write("\n".join(results_lines))

log("\n" + "=" * 70)
log("ANALYSIS COMPLETE")
log(f"Results saved to: {ANALYSIS_DIR}/")
log("=" * 70)

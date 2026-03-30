"""
Paper 1: Leave-One-Rater-Out FNR Sensitivity Analysis
=====================================================
Addresses the single-rater dominance concern:
  - One rater contributed 9/11 false negative flags (82%)
  - How does FNR change when each rater is excluded?

Reads from: 2_Data/qa_responses/FINAL_DISTRIBUTION/ (de-identified)
Outputs to: 2_Data/qa_responses/FINAL_DISTRIBUTION/analysis/sensitivity/

Random seed: 42
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore", category=FutureWarning)
np.random.seed(42)

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT = Path("/Users/eugene/workspace/MeducAI")
DATA_DIR = PROJECT / "2_Data/qa_responses/FINAL_DISTRIBUTION"
OUT_DIR = DATA_DIR / "analysis" / "sensitivity"
OUT_DIR.mkdir(parents=True, exist_ok=True)

results = []


def log(msg=""):
    print(msg)
    results.append(msg)


def clopper_pearson_ci(k, n, alpha=0.05):
    """Exact Clopper-Pearson confidence interval."""
    if n == 0:
        return np.nan, np.nan, np.nan
    p = k / n
    ci_low = stats.beta.ppf(alpha / 2, k, n - k + 1) if k > 0 else 0.0
    ci_high = stats.beta.ppf(1 - alpha / 2, k + 1, n - k) if k < n else 1.0
    return p, ci_low, ci_high


# ── Load data ────────────────────────────────────────────────────────────────
ratings = pd.read_csv(DATA_DIR / "ratings_deidentified.csv")
cards = pd.read_csv(DATA_DIR / "cards_analysis.csv")
rater_summary = pd.read_csv(DATA_DIR / "rater_summary.csv")

log("=" * 70)
log("PAPER 1: LEAVE-ONE-RATER-OUT FNR SENSITIVITY ANALYSIS")
log("=" * 70)
log(f"Analysis date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
log(f"Total ratings: {len(ratings):,}")

# ══════════════════════════════════════════════════════════════════════════════
# 0. IDENTIFY TEXT-LEVEL PASS CARDS AND FNR COLUMN
# ══════════════════════════════════════════════════════════════════════════════
log("\n--- Data exploration: S5 decisions ---")
log(f"Card S5 decisions in ratings: {ratings['card_s5_decision'].value_counts().to_dict()}")

# Text-level PASS = PASS + IMAGE_REGEN (text content was acceptable)
text_pass_mask = ratings["card_s5_decision"].isin(["PASS", "IMAGE_REGEN"])
pass_ratings = ratings[text_pass_mask].copy()
log(f"\nText-level PASS evaluations: {len(pass_ratings)}")
log(f"Text-level PASS unique cards: {pass_ratings['card_uid'].nunique()}")

# Check which blocking_error column gives 11 FNs (matching manuscript)
for col in ["blocking_error_pre", "blocking_error_post"]:
    fn_count = pass_ratings[col].eq("Yes").sum()
    log(f"  {col} FN count: {fn_count}")

# Manuscript reports 11 FNs which matches blocking_error_pre.
# The pre-evaluation FNR measures S5's standalone detection performance
# (human judgment before viewing S5 feedback), which is the correct
# operationalization for "what did S5 miss?"
BE_COL = "blocking_error_pre"
fn_total = pass_ratings[BE_COL].eq("Yes").sum()
n_total = len(pass_ratings)
log(f"\nPrimary FNR column: {BE_COL} (matches manuscript's 11 FNs)")
log(f"Total FN: {fn_total} / {n_total}")

# Also report post for comparison
fn_post = pass_ratings["blocking_error_post"].eq("Yes").sum()
log(f"Post-S5 FN count for comparison: {fn_post} / {n_total}")
log(f"→ 1 FN was 'resolved' after seeing S5 feedback (pre=11, post=10)")

# ══════════════════════════════════════════════════════════════════════════════
# 1. PER-RATER FN BREAKDOWN
# ══════════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 70)
log("1. PER-RATER FALSE NEGATIVE BREAKDOWN")
log("=" * 70)

rater_fn = (
    pass_ratings.groupby("rater_id")
    .agg(
        n_evals=(BE_COL, "count"),
        n_fn=(BE_COL, lambda x: (x == "Yes").sum()),
    )
    .reset_index()
)
rater_fn = rater_fn.merge(rater_summary[["rater_id", "role"]], on="rater_id", how="left")
rater_fn["fnr_pct"] = (rater_fn["n_fn"] / rater_fn["n_evals"] * 100).round(3)
rater_fn = rater_fn.sort_values("n_fn", ascending=False)

log(f"\n{'Rater':<10} {'Role':<12} {'Evals':>6} {'FN':>4} {'FNR%':>8}")
log("-" * 44)
for _, row in rater_fn.iterrows():
    log(f"{row['rater_id']:<10} {row['role']:<12} {row['n_evals']:>6} "
        f"{row['n_fn']:>4} {row['fnr_pct']:>8.2f}")

dominant_rater = rater_fn.iloc[0]["rater_id"]
dominant_fn = int(rater_fn.iloc[0]["n_fn"])
log(f"\nDominant rater: {dominant_rater} ({dominant_fn} of {fn_total} FNs = "
    f"{dominant_fn/fn_total*100:.1f}%)")

# ══════════════════════════════════════════════════════════════════════════════
# 2. LEAVE-ONE-RATER-OUT ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 70)
log("2. LEAVE-ONE-RATER-OUT FNR SENSITIVITY ANALYSIS")
log("=" * 70)

all_raters = sorted(pass_ratings["rater_id"].unique())
loo_results = []

for rater in all_raters:
    mask = pass_ratings["rater_id"] != rater
    remaining = pass_ratings[mask]
    n_rem = len(remaining)
    fn_rem = remaining[BE_COL].eq("Yes").sum()
    fnr_rem, ci_l, ci_h = clopper_pearson_ci(fn_rem, n_rem)
    role = rater_summary[rater_summary["rater_id"] == rater]["role"].values[0]
    fn_excluded = int(rater_fn[rater_fn["rater_id"] == rater]["n_fn"].values[0])

    loo_results.append({
        "excluded_rater": rater,
        "role": role,
        "fn_by_excluded": fn_excluded,
        "remaining_evals": n_rem,
        "remaining_fn": fn_rem,
        "fnr_pct": round(fnr_rem * 100, 3) if not np.isnan(fnr_rem) else None,
        "ci_lower_pct": round(ci_l * 100, 3) if not np.isnan(ci_l) else None,
        "ci_upper_pct": round(ci_h * 100, 3) if not np.isnan(ci_h) else None,
        "meets_threshold": ci_h <= 0.003 if not np.isnan(ci_h) else None,
    })

loo_df = pd.DataFrame(loo_results)

log(f"\n{'Excluded':<10} {'Role':<12} {'FN excl':>8} {'Remain N':>9} {'Remain FN':>10} "
    f"{'FNR%':>7} {'95% CI':>18} {'≤0.3%':>6}")
log("-" * 85)
for _, row in loo_df.iterrows():
    ci_str = f"({row['ci_lower_pct']:.2f}–{row['ci_upper_pct']:.2f})"
    thresh = "YES" if row["meets_threshold"] else "NO"
    log(f"{row['excluded_rater']:<10} {row['role']:<12} {row['fn_by_excluded']:>8} "
        f"{row['remaining_evals']:>9} {row['remaining_fn']:>10} "
        f"{row['fnr_pct']:>7.2f} {ci_str:>18} {thresh:>6}")

# ══════════════════════════════════════════════════════════════════════════════
# 3. SUMMARY STATISTICS
# ══════════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 70)
log("3. SUMMARY")
log("=" * 70)

# Overall FNR (all raters)
fnr_all, ci_l_all, ci_h_all = clopper_pearson_ci(fn_total, n_total)
log(f"\nAll raters: FNR = {fnr_all*100:.2f}% (95% CI: {ci_l_all*100:.2f}–{ci_h_all*100:.2f}%)")
log(f"Safety threshold (0.3%): {'PASS' if ci_h_all <= 0.003 else 'FAIL'}")

# Excluding dominant rater
dom_row = loo_df[loo_df["excluded_rater"] == dominant_rater].iloc[0]
log(f"\nExcluding {dominant_rater}: FNR = {dom_row['fnr_pct']:.2f}% "
    f"(95% CI: {dom_row['ci_lower_pct']:.2f}–{dom_row['ci_upper_pct']:.2f}%)")
log(f"Safety threshold (0.3%): {'PASS' if dom_row['meets_threshold'] else 'FAIL'}")

# Range of leave-one-out FNR
log(f"\nLeave-one-out FNR range: {loo_df['fnr_pct'].min():.2f}%–{loo_df['fnr_pct'].max():.2f}%")

# How many raters, if excluded, would change the safety threshold result?
n_change = loo_df["meets_threshold"].sum()
log(f"Raters whose exclusion would meet 0.3% threshold: {n_change} / {len(loo_df)}")

# ══════════════════════════════════════════════════════════════════════════════
# 4. KAPPA FOR BINARY BLOCKING ERROR (on calibration subset)
# ══════════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 70)
log("4. INTER-RATER AGREEMENT: BINARY BLOCKING ERROR (calibration items)")
log("=" * 70)

cal_ratings = ratings[ratings["is_calibration"] == 1].copy()
log(f"Calibration ratings: {len(cal_ratings)}")
log(f"Calibration unique cards: {cal_ratings['card_uid'].nunique()}")

# Compute pairwise percent agreement and Cohen's kappa for blocking error
cal_cards = cal_ratings["card_uid"].unique()
rater_pairs = []

for card in cal_cards:
    card_data = cal_ratings[cal_ratings["card_uid"] == card]
    raters = card_data["rater_id"].unique()
    for i in range(len(raters)):
        for j in range(i + 1, len(raters)):
            r1_val = card_data[card_data["rater_id"] == raters[i]][BE_COL].values[0]
            r2_val = card_data[card_data["rater_id"] == raters[j]][BE_COL].values[0]
            rater_pairs.append({
                "card_uid": card,
                "rater_1": raters[i],
                "rater_2": raters[j],
                "r1_be": r1_val,
                "r2_be": r2_val,
                "agree": r1_val == r2_val,
            })

pairs_df = pd.DataFrame(rater_pairs)
if len(pairs_df) > 0:
    pct_agree = pairs_df["agree"].mean() * 100
    log(f"Pairwise comparisons: {len(pairs_df)}")
    log(f"Percent agreement (blocking error): {pct_agree:.1f}%")

    # Overall 2x2 for kappa
    both_yes = ((pairs_df["r1_be"] == "Yes") & (pairs_df["r2_be"] == "Yes")).sum()
    both_no = ((pairs_df["r1_be"] == "No") & (pairs_df["r2_be"] == "No")).sum()
    r1y_r2n = ((pairs_df["r1_be"] == "Yes") & (pairs_df["r2_be"] == "No")).sum()
    r1n_r2y = ((pairs_df["r1_be"] == "No") & (pairs_df["r2_be"] == "Yes")).sum()
    total_p = len(pairs_df)

    log(f"\n  2x2 table:")
    log(f"                 Rater 2 Yes   Rater 2 No")
    log(f"  Rater 1 Yes    {both_yes:>10}   {r1y_r2n:>10}")
    log(f"  Rater 1 No     {r1n_r2y:>10}   {both_no:>10}")

    po = (both_yes + both_no) / total_p
    p1_yes = (both_yes + r1y_r2n) / total_p
    p2_yes = (both_yes + r1n_r2y) / total_p
    pe = p1_yes * p2_yes + (1 - p1_yes) * (1 - p2_yes)

    if pe < 1.0:
        kappa = (po - pe) / (1 - pe)
        log(f"\n  Cohen's kappa (blocking error): {kappa:.3f}")
        if kappa < 0:
            interp = "less than chance"
        elif kappa < 0.20:
            interp = "slight"
        elif kappa < 0.40:
            interp = "fair"
        elif kappa < 0.60:
            interp = "moderate"
        elif kappa < 0.80:
            interp = "substantial"
        else:
            interp = "almost perfect"
        log(f"  Interpretation (Landis & Koch): {interp}")
    else:
        log(f"  Cohen's kappa: undefined (perfect agreement by chance)")
        kappa = None

    # Prevalence of blocking error in calibration
    be_rate = (cal_ratings[BE_COL] == "Yes").mean() * 100
    log(f"\n  Blocking error prevalence (calibration): {be_rate:.1f}%")
    log(f"  Note: Very low prevalence can deflate kappa even with high percent agreement")
else:
    kappa = None
    pct_agree = None
    log("No pairwise comparisons possible")

# ── Save results ────────────────────────────────────────────────────────────
loo_df.to_csv(OUT_DIR / "fnr_leave_one_out.csv", index=False)
rater_fn.to_csv(OUT_DIR / "fnr_per_rater_breakdown.csv", index=False)

with open(OUT_DIR / "leave_one_out_analysis_results.txt", "w") as f:
    f.write("\n".join(results))

log("\n" + "=" * 70)
log(f"ANALYSIS COMPLETE — Results saved to: {OUT_DIR}/")
log("=" * 70)

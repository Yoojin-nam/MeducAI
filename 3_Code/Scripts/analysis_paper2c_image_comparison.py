# Analysis: Paper 2C — Illustration vs Realistic image comparison
# Date: 2026-03-28
# Random seed: 42
# Python: 3.14.3
# Key packages: pandas==2.3.3, scipy==1.17.1, numpy==2.4.3
"""
Paper 2C analysis: Paired comparisons of illustration (pre/post S5) and
realistic image metrics across all 1,833 card evaluations.

Analyses:
  1. Descriptive statistics for all image metrics
  2. Illustration PRE vs POST (paired)
  3. Illustration PRE vs Realistic (paired)
  4. Illustration POST vs Realistic (paired)
  5. Resident vs Attending comparison (post metrics)
  6. Summary of realistic image data availability

CI method for rank-biserial r: large-sample normal approximation
  SE(r) = sqrt((1 - r^2) / (n - 1)) where n = number of non-zero differences
  This is appropriate given the sample sizes (n >> 30).
"""

import numpy as np
import pandas as pd
from scipy import stats
from pathlib import Path
import warnings
import math

warnings.filterwarnings("ignore", category=FutureWarning)

# ── Reproducibility ──────────────────────────────────────────────────────────
np.random.seed(42)

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_PATH = Path(
    "/Users/eugene/workspace/meducai/2_Data/qa_responses/FINAL_DISTRIBUTION/"
    "ratings_deidentified.csv"
)
OUT_DIR = Path(
    "/Users/eugene/workspace/meducai/2_Data/qa_responses/FINAL_DISTRIBUTION/analysis"
)
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Rater groups ──────────────────────────────────────────────────────────────
RESIDENTS = {"R01", "R02", "R03", "R04", "R09", "R10", "R11", "R14", "R19"}
ATTENDINGS = {"R05", "R06", "R07", "R08", "R12", "R13", "R15", "R16", "R17", "R18", "R20"}

# ── Column sets ───────────────────────────────────────────────────────────────
METRICS = ["blocking_error", "anatomical_accuracy", "quality", "text_consistency"]

PRE_COLS = {m: f"image_{m}_pre" for m in METRICS}
POST_COLS = {m: f"image_{m}_post" for m in METRICS}
REAL_COLS = {m: f"realistic_image_{m}" for m in METRICS}

# ── Load data ─────────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH)
print(f"Loaded {len(df)} rows from ratings_deidentified.csv")
print(f"Columns used (PRE):  {list(PRE_COLS.values())}")
print(f"Columns used (POST): {list(POST_COLS.values())}")
print(f"Columns used (REAL): {list(REAL_COLS.values())}")

# Convert blocking_error Yes/No -> 1/0
for col in [PRE_COLS["blocking_error"], POST_COLS["blocking_error"],
            REAL_COLS["blocking_error"]]:
    if col in df.columns:
        df[col] = df[col].map({"Yes": 1, "No": 0})

# Add rater group
df["rater_group"] = df["rater_id"].apply(
    lambda x: "Resident" if x in RESIDENTS
    else ("Attending" if x in ATTENDINGS else "Unknown")
)

# ═══════════════════════════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════════════════════════


def descriptive_stats(series, name):
    """Compute descriptive statistics for a single series."""
    s = series.dropna()
    n = len(s)
    if n == 0:
        return {"metric": name, "N": 0, "mean": np.nan, "SD": np.nan,
                "median": np.nan, "Q1": np.nan, "Q3": np.nan, "IQR": np.nan}
    q1, med, q3 = np.percentile(s, [25, 50, 75])
    return {
        "metric": name, "N": n, "mean": round(s.mean(), 4),
        "SD": round(s.std(ddof=1), 4), "median": round(med, 4),
        "Q1": round(q1, 4), "Q3": round(q3, 4), "IQR": round(q3 - q1, 4),
    }


def rank_biserial_r_wilcoxon(x, y):
    """Rank-biserial r for Wilcoxon signed-rank with analytic 95% CI.

    r = 1 - 2T / (n*(n+1)/2)
    SE(r) approximated via large-sample formula.
    """
    diff = x - y
    nonzero = diff != 0
    n = nonzero.sum()
    if n == 0:
        return 0.0, (0.0, 0.0), 1.0

    res = stats.wilcoxon(x, y, alternative="two-sided")
    T = res.statistic
    p_val = res.pvalue

    r = 1.0 - (2.0 * T) / (n * (n + 1) / 2.0)

    # Large-sample SE for rank-biserial r (Kerby 2014 approximation)
    # SE = sqrt( (1 - r^2) * 2 * (2*n^2 + 3*n - 1) / (6 * n * (n+1) * (2*n+1)) )
    # Simplified conservative: SE ~ sqrt((1 - r^2) / (n - 1)) when n > 30
    if n > 2:
        se_r = math.sqrt(max((1.0 - r ** 2), 0.0) / (n - 1))
    else:
        se_r = np.nan
    ci_lo = r - 1.96 * se_r if not np.isnan(se_r) else np.nan
    ci_hi = r + 1.96 * se_r if not np.isnan(se_r) else np.nan
    # Clamp to [-1, 1]
    ci_lo = max(ci_lo, -1.0) if not np.isnan(ci_lo) else np.nan
    ci_hi = min(ci_hi, 1.0) if not np.isnan(ci_hi) else np.nan

    return r, (ci_lo, ci_hi), p_val


def rank_biserial_r_mannwhitney(x, y):
    """Rank-biserial r for Mann-Whitney U with analytic 95% CI.

    r = 1 - 2U / (n1 * n2)
    """
    n1, n2 = len(x), len(y)
    u_stat, p_val = stats.mannwhitneyu(x, y, alternative="two-sided")
    r = 1.0 - (2.0 * u_stat) / (n1 * n2)

    # SE from Wendt (1972): SE = sqrt( (n1+n2+1) / (3*n1*n2) )
    se_r = math.sqrt((n1 + n2 + 1) / (3.0 * n1 * n2))
    ci_lo = max(r - 1.96 * se_r, -1.0)
    ci_hi = min(r + 1.96 * se_r, 1.0)

    return r, (ci_lo, ci_hi), p_val, u_stat


def mcnemar_effect_size(a, b):
    """Compute McNemar test and odds ratio (b/c) with 95% CI.

    a, b are paired binary series.
    Returns: p_val, odds_r, ci_lo, ci_hi, n_disc, n_total, n10, n01
    """
    mask = a.notna() & b.notna()
    a_v, b_v = a[mask].astype(int), b[mask].astype(int)
    n10 = int(((a_v == 1) & (b_v == 0)).sum())
    n01 = int(((a_v == 0) & (b_v == 1)).sum())
    n_total = len(a_v)
    n_disc = n10 + n01

    if n_disc == 0:
        return np.nan, np.nan, np.nan, np.nan, 0, n_total, n10, n01
    if n_disc < 25:
        p_val = stats.binomtest(n10, n_disc, 0.5).pvalue
    else:
        chi2 = (abs(n10 - n01) - 1) ** 2 / (n10 + n01)
        p_val = stats.chi2.sf(chi2, 1)

    if n01 == 0:
        odds_r = np.inf
        ci_lo, ci_hi = np.nan, np.nan
    elif n10 == 0:
        odds_r = 0.0
        ci_lo, ci_hi = np.nan, np.nan
    else:
        odds_r = n10 / n01
        log_or = np.log(odds_r)
        se_log_or = math.sqrt(1.0 / n10 + 1.0 / n01)
        ci_lo = np.exp(log_or - 1.96 * se_log_or)
        ci_hi = np.exp(log_or + 1.96 * se_log_or)

    return p_val, odds_r, ci_lo, ci_hi, n_disc, n_total, n10, n01


def paired_comparison(df_pair, col_a, col_b, label_a, label_b, metrics_list):
    """Run paired comparison for all metrics between two column sets."""
    results = []
    for m in metrics_list:
        ca, cb = col_a[m], col_b[m]
        mask = df_pair[ca].notna() & df_pair[cb].notna()
        sub = df_pair[mask]
        n_pairs = len(sub)

        if m == "blocking_error":
            p_val, odds_r, ci_lo, ci_hi, n_disc, n_total, n10, n01 = \
                mcnemar_effect_size(sub[ca], sub[cb])
            results.append({
                "metric": m,
                "comparison": f"{label_a} vs {label_b}",
                "test": "McNemar",
                "N_pairs": n_pairs,
                "n_discordant": n_disc,
                f"{label_a}_yes": int(sub[ca].sum()),
                f"{label_b}_yes": int(sub[cb].sum()),
                "p_value": p_val,
                "effect_size_type": "Odds Ratio (b/c)",
                "effect_size": odds_r,
                "CI_95_lo": ci_lo,
                "CI_95_hi": ci_hi,
            })
        else:
            a_vals = sub[ca].astype(float)
            b_vals = sub[cb].astype(float)
            r_es, (ci_lo, ci_hi), p_val = rank_biserial_r_wilcoxon(a_vals, b_vals)
            results.append({
                "metric": m,
                "comparison": f"{label_a} vs {label_b}",
                "test": "Wilcoxon signed-rank",
                "N_pairs": n_pairs,
                f"{label_a}_median": round(a_vals.median(), 4),
                f"{label_b}_median": round(b_vals.median(), 4),
                "p_value": p_val,
                "effect_size_type": "rank-biserial r",
                "effect_size": round(r_es, 4),
                "CI_95_lo": round(ci_lo, 4) if not np.isnan(ci_lo) else np.nan,
                "CI_95_hi": round(ci_hi, 4) if not np.isnan(ci_hi) else np.nan,
            })
    return pd.DataFrame(results)


def apply_holm_correction(result_df):
    """Apply Holm correction to p_value column, adding corrected column."""
    pvals = result_df["p_value"].values.astype(float).copy()
    valid = ~np.isnan(pvals)
    corrected = np.full_like(pvals, np.nan)
    if valid.sum() > 0:
        n_valid = int(valid.sum())
        idx_valid = np.where(valid)[0]
        sorted_idx = idx_valid[np.argsort(pvals[idx_valid])]
        for rank_i, orig_i in enumerate(sorted_idx):
            corrected[orig_i] = min(pvals[orig_i] * (n_valid - rank_i), 1.0)
        # Enforce monotonicity
        running_max = 0.0
        for orig_i in sorted_idx:
            corrected[orig_i] = max(corrected[orig_i], running_max)
            running_max = corrected[orig_i]
    result_df["p_value_holm"] = corrected
    return result_df


def format_p(p):
    """Format p-value for display."""
    if pd.isna(p):
        return "NA"
    if p < 0.001:
        return "p<0.001"
    return f"p={p:.4f}"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. DESCRIPTIVE STATISTICS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("1. DESCRIPTIVE STATISTICS")
print("=" * 80)

desc_rows = []
for m in METRICS:
    desc_rows.append(descriptive_stats(df[PRE_COLS[m]], f"Illustration PRE -- {m}"))
    desc_rows.append(descriptive_stats(df[POST_COLS[m]], f"Illustration POST -- {m}"))
    desc_rows.append(descriptive_stats(df[REAL_COLS[m]], f"Realistic -- {m}"))

desc_df = pd.DataFrame(desc_rows)
desc_df.to_csv(OUT_DIR / "paper2c_descriptives.csv", index=False)
print(desc_df.to_string(index=False))

# ═══════════════════════════════════════════════════════════════════════════════
# 2. ILLUSTRATION PRE vs POST (paired)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("2. ILLUSTRATION PRE vs POST (paired)")
print("=" * 80)

pre_post_df = paired_comparison(df, PRE_COLS, POST_COLS, "PRE", "POST", METRICS)
pre_post_df = apply_holm_correction(pre_post_df)
pre_post_df.to_csv(OUT_DIR / "paper2c_pre_vs_post.csv", index=False)
for _, row in pre_post_df.iterrows():
    print(f"\n  {row['metric']} ({row['test']}):")
    print(f"    N pairs = {row['N_pairs']}")
    print(f"    {format_p(row['p_value'])}  (Holm-corrected: {format_p(row['p_value_holm'])})")
    es = row['effect_size']
    ci_lo = row.get('CI_95_lo', np.nan)
    ci_hi = row.get('CI_95_hi', np.nan)
    if pd.notna(es):
        ci_str = (f"  95% CI [{ci_lo:.4f}, {ci_hi:.4f}]"
                  if pd.notna(ci_lo) else "  95% CI [NA, NA]")
        print(f"    Effect size ({row['effect_size_type']}): {es:.4f}{ci_str}")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. ILLUSTRATION PRE vs REALISTIC (paired, subset with realistic data)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("3. ILLUSTRATION PRE vs REALISTIC (paired)")
print("=" * 80)

has_real = df[REAL_COLS["quality"]].notna()
df_real = df[has_real].copy()
print(f"  Cards with realistic image data: {len(df_real)}")

pre_real_df = paired_comparison(
    df_real, PRE_COLS, REAL_COLS, "IllustPRE", "Realistic", METRICS
)
pre_real_df = apply_holm_correction(pre_real_df)
pre_real_df.to_csv(OUT_DIR / "paper2c_illust_pre_vs_realistic.csv", index=False)
for _, row in pre_real_df.iterrows():
    print(f"\n  {row['metric']} ({row['test']}):")
    print(f"    N pairs = {row['N_pairs']}")
    print(f"    {format_p(row['p_value'])}  (Holm-corrected: {format_p(row['p_value_holm'])})")
    es = row['effect_size']
    ci_lo = row.get('CI_95_lo', np.nan)
    ci_hi = row.get('CI_95_hi', np.nan)
    if pd.notna(es):
        ci_str = (f"  95% CI [{ci_lo:.4f}, {ci_hi:.4f}]"
                  if pd.notna(ci_lo) else "  95% CI [NA, NA]")
        print(f"    Effect size ({row['effect_size_type']}): {es:.4f}{ci_str}")

# ═══════════════════════════════════════════════════════════════════════════════
# 4. ILLUSTRATION POST vs REALISTIC (paired)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("4. ILLUSTRATION POST vs REALISTIC (paired)")
print("=" * 80)

post_real_df = paired_comparison(
    df_real, POST_COLS, REAL_COLS, "IllustPOST", "Realistic", METRICS
)
post_real_df = apply_holm_correction(post_real_df)
post_real_df.to_csv(OUT_DIR / "paper2c_illust_post_vs_realistic.csv", index=False)
for _, row in post_real_df.iterrows():
    print(f"\n  {row['metric']} ({row['test']}):")
    print(f"    N pairs = {row['N_pairs']}")
    print(f"    {format_p(row['p_value'])}  (Holm-corrected: {format_p(row['p_value_holm'])})")
    es = row['effect_size']
    ci_lo = row.get('CI_95_lo', np.nan)
    ci_hi = row.get('CI_95_hi', np.nan)
    if pd.notna(es):
        ci_str = (f"  95% CI [{ci_lo:.4f}, {ci_hi:.4f}]"
                  if pd.notna(ci_lo) else "  95% CI [NA, NA]")
        print(f"    Effect size ({row['effect_size_type']}): {es:.4f}{ci_str}")

# ═══════════════════════════════════════════════════════════════════════════════
# 5. RESIDENT vs ATTENDING (POST metrics, unpaired)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("5. RESIDENT vs ATTENDING -- POST image metrics")
print("=" * 80)

res_df = df[df["rater_group"] == "Resident"]
att_df = df[df["rater_group"] == "Attending"]
print(f"  Residents: {len(res_df)} ratings from {res_df['rater_id'].nunique()} raters")
print(f"  Attendings: {len(att_df)} ratings from {att_df['rater_id'].nunique()} raters")

ra_results = []
for m in METRICS:
    col = POST_COLS[m]
    r_vals = res_df[col].dropna()
    a_vals = att_df[col].dropna()
    n_r, n_a = len(r_vals), len(a_vals)

    if m == "blocking_error":
        r_yes = int(r_vals.sum())
        r_no = n_r - r_yes
        a_yes = int(a_vals.sum())
        a_no = n_a - a_yes
        table = np.array([[r_yes, r_no], [a_yes, a_no]])
        res = stats.fisher_exact(table, alternative="two-sided")
        odds_r = res.statistic
        p_val = res.pvalue
        if r_yes > 0 and r_no > 0 and a_yes > 0 and a_no > 0:
            log_or = np.log(odds_r)
            se = math.sqrt(1 / r_yes + 1 / r_no + 1 / a_yes + 1 / a_no)
            ci_lo = np.exp(log_or - 1.96 * se)
            ci_hi = np.exp(log_or + 1.96 * se)
        else:
            ci_lo, ci_hi = np.nan, np.nan
        ra_results.append({
            "metric": m, "test": "Fisher exact",
            "N_resident": n_r, "N_attending": n_a,
            "Resident_yes_pct": round(100 * r_yes / n_r, 2) if n_r else np.nan,
            "Attending_yes_pct": round(100 * a_yes / n_a, 2) if n_a else np.nan,
            "p_value": p_val,
            "effect_size_type": "Odds Ratio",
            "effect_size": round(odds_r, 4),
            "CI_95_lo": round(ci_lo, 4) if not np.isnan(ci_lo) else np.nan,
            "CI_95_hi": round(ci_hi, 4) if not np.isnan(ci_hi) else np.nan,
        })
    else:
        r_es, (ci_lo, ci_hi), p_val, u_stat = rank_biserial_r_mannwhitney(
            r_vals.values, a_vals.values
        )
        ra_results.append({
            "metric": m, "test": "Mann-Whitney U",
            "N_resident": n_r, "N_attending": n_a,
            "Resident_median": round(r_vals.median(), 4),
            "Attending_median": round(a_vals.median(), 4),
            "p_value": p_val,
            "effect_size_type": "rank-biserial r",
            "effect_size": round(r_es, 4),
            "CI_95_lo": round(ci_lo, 4),
            "CI_95_hi": round(ci_hi, 4),
        })

ra_df = pd.DataFrame(ra_results)
ra_df = apply_holm_correction(ra_df)
ra_df.to_csv(OUT_DIR / "paper2c_resident_vs_attending.csv", index=False)
for _, row in ra_df.iterrows():
    print(f"\n  {row['metric']} ({row['test']}):")
    print(f"    N: Resident={row['N_resident']}, Attending={row['N_attending']}")
    print(f"    {format_p(row['p_value'])}  (Holm-corrected: {format_p(row['p_value_holm'])})")
    es = row['effect_size']
    ci_lo = row.get('CI_95_lo', np.nan)
    ci_hi = row.get('CI_95_hi', np.nan)
    if pd.notna(es):
        ci_str = (f"  95% CI [{ci_lo:.4f}, {ci_hi:.4f}]"
                  if pd.notna(ci_lo) else "  95% CI [NA, NA]")
        print(f"    Effect size ({row['effect_size_type']}): {es:.4f}{ci_str}")

# ═══════════════════════════════════════════════════════════════════════════════
# 6. SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("6. SUMMARY")
print("=" * 80)

n_total = len(df)
n_real = int(has_real.sum())
n_raters = df["rater_id"].nunique()

# Missing data report
print("\n--- Missing data report ---")
for label, cols in [("Illustration PRE", PRE_COLS),
                    ("Illustration POST", POST_COLS),
                    ("Realistic", REAL_COLS)]:
    for m, col in cols.items():
        n_miss = int(df[col].isna().sum())
        pct = 100 * n_miss / n_total
        print(f"  {label} {m}: {n_miss} ({pct:.1f}%)")

summary_lines = [
    "Paper 2C Image Comparison Analysis Summary",
    "Date: 2026-03-28",
    "Random seed: 42",
    "",
    f"Total card evaluations: {n_total}",
    f"Total raters: {n_raters}",
    f"  Residents: {len(RESIDENTS)} ({len(res_df)} ratings)",
    f"  Attendings: {len(ATTENDINGS)} ({len(att_df)} ratings)",
    f"Cards with realistic image data: {n_real}",
    "",
    "Missing data handling: listwise deletion (pairs with both values required)",
    "Multiple comparison correction: Holm method within each analysis block",
    "Effect sizes: rank-biserial r (Wilcoxon/Mann-Whitney), Odds Ratio (McNemar/Fisher)",
    "CI method: large-sample normal approximation for rank-biserial r; "
    "Wald CI for log(OR)",
    "",
]


def _fmt_result_block(title, result_df):
    """Format a result block for the summary text."""
    lines = ["=" * 60, title, "=" * 60]
    for _, row in result_df.iterrows():
        es = row["effect_size"]
        ci_lo = row.get("CI_95_lo", np.nan)
        ci_hi = row.get("CI_95_hi", np.nan)
        es_str = f"{es:.4f}" if pd.notna(es) and not np.isinf(es) else str(es)
        ci_str = (f"[{ci_lo:.4f}, {ci_hi:.4f}]"
                  if pd.notna(ci_lo) and pd.notna(ci_hi) else "[NA, NA]")
        lines.append(
            f"  {row['metric']}: {format_p(row['p_value'])} "
            f"(Holm: {format_p(row['p_value_holm'])}), "
            f"ES={es_str} {ci_str}"
        )
    return lines


summary_lines += _fmt_result_block("ILLUSTRATION PRE vs POST", pre_post_df)
summary_lines.append("")
summary_lines += _fmt_result_block("ILLUSTRATION PRE vs REALISTIC", pre_real_df)
summary_lines.append("")
summary_lines += _fmt_result_block("ILLUSTRATION POST vs REALISTIC", post_real_df)
summary_lines.append("")
summary_lines += _fmt_result_block("RESIDENT vs ATTENDING (POST)", ra_df)

summary_text = "\n".join(summary_lines)
(OUT_DIR / "paper2c_summary.txt").write_text(summary_text)
print(f"\n{summary_text}")

print("\n" + "=" * 80)
print("OUTPUT FILES:")
print("=" * 80)
for f in sorted(OUT_DIR.glob("paper2c_*")):
    print(f"  {f}")
print("\nDone.")

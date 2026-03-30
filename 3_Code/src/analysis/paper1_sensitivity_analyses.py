"""
Paper 1: Sensitivity Analyses — Addressing Reviewer Concerns
=============================================================
1. Card-level FNR (unit-of-analysis sensitivity)
2. Subspecialty-stratified attending vs resident analysis
3. Data consistency audit (958 vs 980, CI checks)

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

# ── Load de-identified data ──────────────────────────────────────────────────
ratings = pd.read_csv(DATA_DIR / "ratings_deidentified.csv")
cards = pd.read_csv(DATA_DIR / "cards_analysis.csv")
rater_summary = pd.read_csv(DATA_DIR / "rater_summary.csv")

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


log("=" * 70)
log("PAPER 1 SENSITIVITY ANALYSES")
log("=" * 70)
log(f"Analysis date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
log(f"Total ratings: {len(ratings):,}")
log(f"Total cards:   {len(cards):,}")

# ══════════════════════════════════════════════════════════════════════════════
# 1. CARD-LEVEL FNR (Unit-of-Analysis Sensitivity)
# ══════════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 70)
log("1. CARD-LEVEL FNR SENSITIVITY ANALYSIS")
log("=" * 70)
log("Current manuscript: rater-card pair level (N=1,100 evaluations)")
log("Sensitivity: card level — a card is FN if ANY rater flagged blocking_error=Yes")

pass_ratings = ratings[ratings["card_s5_decision"] == "PASS"].copy()
n_pass_cards = pass_ratings["card_uid"].nunique()

# Card-level: aggregate per card — FN if any rater said blocking_error = Yes
card_level = pass_ratings.groupby("card_uid").agg(
    n_raters=("rater_id", "nunique"),
    any_blocking_error=("blocking_error_pre", lambda x: (x == "Yes").any()),
    all_blocking_error=("blocking_error_pre", lambda x: (x == "Yes").all()),
    n_blocking_yes=("blocking_error_pre", lambda x: (x == "Yes").sum()),
).reset_index()

# Card-level FNR: any rater flagged
fn_any = card_level["any_blocking_error"].sum()
fnr_any, ci_l_any, ci_h_any = clopper_pearson_ci(fn_any, n_pass_cards)

# Card-level FNR: all raters flagged (stricter)
fn_all = card_level["all_blocking_error"].sum()
fnr_all, ci_l_all, ci_h_all = clopper_pearson_ci(fn_all, n_pass_cards)

# Card-level FNR: majority flagged (≥50% of raters)
card_level["majority_flagged"] = card_level["n_blocking_yes"] > (card_level["n_raters"] / 2)
fn_majority = card_level["majority_flagged"].sum()
fnr_maj, ci_l_maj, ci_h_maj = clopper_pearson_ci(fn_majority, n_pass_cards)

log(f"\nS5-PASS unique cards: {n_pass_cards}")
log(f"Raters per PASS card: mean={card_level['n_raters'].mean():.1f}, "
    f"min={card_level['n_raters'].min()}, max={card_level['n_raters'].max()}")

log(f"\n--- Rating-level (current manuscript) ---")
n_pass_ratings = len(pass_ratings)
fn_rating = pass_ratings["blocking_error_pre"].eq("Yes").sum()
fnr_r, ci_l_r, ci_h_r = clopper_pearson_ci(fn_rating, n_pass_ratings)
log(f"  N = {n_pass_ratings} evaluations")
log(f"  FN = {fn_rating}")
log(f"  FNR = {fnr_r*100:.2f}% (95% CI: {ci_l_r*100:.2f}–{ci_h_r*100:.2f}%)")

log(f"\n--- Card-level: ANY rater flagged (liberal) ---")
log(f"  N = {n_pass_cards} cards")
log(f"  FN = {fn_any}")
log(f"  FNR = {fnr_any*100:.2f}% (95% CI: {ci_l_any*100:.2f}–{ci_h_any*100:.2f}%)")

log(f"\n--- Card-level: MAJORITY of raters flagged ---")
log(f"  N = {n_pass_cards} cards")
log(f"  FN = {fn_majority}")
log(f"  FNR = {fnr_maj*100:.2f}% (95% CI: {ci_l_maj*100:.2f}–{ci_h_maj*100:.2f}%)")

log(f"\n--- Card-level: ALL raters flagged (strict) ---")
log(f"  N = {n_pass_cards} cards")
log(f"  FN = {fn_all}")
log(f"  FNR = {fnr_all*100:.2f}% (95% CI: {ci_l_all*100:.2f}–{ci_h_all*100:.2f}%)")

# Safety threshold test for each
threshold = 0.003
for label, fn, n in [("Rating-level", fn_rating, n_pass_ratings),
                      ("Card-level (any)", fn_any, n_pass_cards),
                      ("Card-level (majority)", fn_majority, n_pass_cards),
                      ("Card-level (all)", fn_all, n_pass_cards)]:
    if fn == n:
        upper = 1.0
    else:
        upper = stats.beta.ppf(0.95, fn + 1, n - fn)
    passes = upper <= threshold
    log(f"\n  Safety test ({label}): upper 95% = {upper*100:.2f}%, "
        f"threshold = {threshold*100:.1f}% → {'PASS' if passes else 'FAIL'}")

# Detail on FN cards
fn_cards = card_level[card_level["any_blocking_error"]].copy()
if len(fn_cards) > 0:
    fn_cards_merged = fn_cards.merge(cards[["card_uid", "group_path", "card_type", "card_role"]],
                                      on="card_uid", how="left")
    log(f"\n--- FN Card Details ---")
    for _, row in fn_cards_merged.iterrows():
        log(f"  {row['card_uid'][:30]}... | raters={row['n_raters']}, "
            f"flagged={row['n_blocking_yes']}/{row['n_raters']} | {row.get('group_path', 'N/A')}")

# Save
fnr_comparison = pd.DataFrame([
    {"level": "rating", "N": n_pass_ratings, "FN": fn_rating,
     "FNR_pct": round(fnr_r * 100, 3), "CI_lower": round(ci_l_r * 100, 3),
     "CI_upper": round(ci_h_r * 100, 3)},
    {"level": "card_any", "N": n_pass_cards, "FN": fn_any,
     "FNR_pct": round(fnr_any * 100, 3), "CI_lower": round(ci_l_any * 100, 3),
     "CI_upper": round(ci_h_any * 100, 3)},
    {"level": "card_majority", "N": n_pass_cards, "FN": fn_majority,
     "FNR_pct": round(fnr_maj * 100, 3), "CI_lower": round(ci_l_maj * 100, 3),
     "CI_upper": round(ci_h_maj * 100, 3)},
    {"level": "card_all", "N": n_pass_cards, "FN": fn_all,
     "FNR_pct": round(fnr_all * 100, 3), "CI_lower": round(ci_l_all * 100, 3),
     "CI_upper": round(ci_h_all * 100, 3)},
])
fnr_comparison.to_csv(OUT_DIR / "fnr_unit_of_analysis.csv", index=False)

# ══════════════════════════════════════════════════════════════════════════════
# 2. SUBSPECIALTY-STRATIFIED ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
log("\n\n" + "=" * 70)
log("2. SUBSPECIALTY-STRATIFIED ATTENDING vs RESIDENT ANALYSIS")
log("=" * 70)
log("Concern: Attendings evaluated subspecialty-matched cards; residents evaluated across all specialties.")
log("This analysis checks whether higher attending error detection reflects domain expertise vs general vigilance.")

# Identify attending vs resident raters
attending_ids = set(rater_summary[rater_summary["role"] == "attending"]["rater_id"])
resident_ids = set(rater_summary[rater_summary["role"] == "resident"]["rater_id"])

# Merge specialty info
ratings_with_spec = ratings.merge(
    cards[["card_uid", "group_path"]], on="card_uid", how="left"
)
ratings_with_spec["specialty"] = ratings_with_spec["group_path"].str.split(" > ").str[0]
ratings_with_spec["rater_role"] = ratings_with_spec["rater_id"].apply(
    lambda x: "attending" if x in attending_ids else "resident"
)

# Extract attending subspecialty from batch_id
ratings_with_spec["batch_specialty"] = ratings_with_spec["batch_id"].apply(
    lambda x: x.replace("SPECIALIST_", "") if isinstance(x, str) and x.startswith("SPECIALIST_") else None
)

# Check: are attending cards matched to their specialty?
att_ratings = ratings_with_spec[ratings_with_spec["rater_role"] == "attending"]
log(f"\nAttending ratings: {len(att_ratings)}")
log(f"Attending batch specialties: {att_ratings['batch_specialty'].dropna().unique()}")
log(f"Card specialties in attending ratings: {att_ratings['specialty'].unique()}")

# Check match rate
att_with_batch = att_ratings.dropna(subset=["batch_specialty"])
if len(att_with_batch) > 0:
    match = (att_with_batch["batch_specialty"] == att_with_batch["specialty"]).mean()
    log(f"Specialty match rate (attending batch vs card specialty): {match*100:.1f}%")

# Overall blocking error rate by role
log(f"\n--- Overall Blocking Error Rate by Role ---")
for role, ids in [("resident", resident_ids), ("attending", attending_ids)]:
    role_data = ratings_with_spec[ratings_with_spec["rater_id"].isin(ids)]
    n_r = len(role_data)
    be_r = role_data["blocking_error_pre"].eq("Yes").sum()
    rate, ci_l, ci_h = clopper_pearson_ci(be_r, n_r)
    log(f"  {role}: {be_r}/{n_r} = {rate*100:.2f}% (95% CI: {ci_l*100:.2f}–{ci_h*100:.2f}%)")

# Stratified analysis: for each specialty, compare resident vs attending error detection
log(f"\n--- Specialty-Stratified Blocking Error Detection ---")
strat_results = []
specialties = sorted(ratings_with_spec["specialty"].dropna().unique())

for spec in specialties:
    spec_data = ratings_with_spec[ratings_with_spec["specialty"] == spec]

    res_data = spec_data[spec_data["rater_role"] == "resident"]
    att_data = spec_data[spec_data["rater_role"] == "attending"]

    n_res = len(res_data)
    n_att = len(att_data)
    be_res = res_data["blocking_error_pre"].eq("Yes").sum() if n_res > 0 else 0
    be_att = att_data["blocking_error_pre"].eq("Yes").sum() if n_att > 0 else 0

    rate_res = be_res / n_res if n_res > 0 else None
    rate_att = be_att / n_att if n_att > 0 else None

    strat_results.append({
        "specialty": spec,
        "resident_n": n_res,
        "resident_blocking_n": be_res,
        "resident_rate_pct": round(rate_res * 100, 2) if rate_res is not None else None,
        "attending_n": n_att,
        "attending_blocking_n": be_att,
        "attending_rate_pct": round(rate_att * 100, 2) if rate_att is not None else None,
    })

    res_str = f"{be_res}/{n_res} ({rate_res*100:.1f}%)" if n_res > 0 else "N/A"
    att_str = f"{be_att}/{n_att} ({rate_att*100:.1f}%)" if n_att > 0 else "N/A"
    log(f"  {spec:30s} | Resident: {res_str:20s} | Attending: {att_str}")

strat_df = pd.DataFrame(strat_results)
strat_df.to_csv(OUT_DIR / "subspecialty_stratified.csv", index=False)

# Fisher's exact test: overall attending vs resident blocking error
att_all = ratings_with_spec[ratings_with_spec["rater_role"] == "attending"]
res_all = ratings_with_spec[ratings_with_spec["rater_role"] == "resident"]
table_2x2 = [
    [att_all["blocking_error_pre"].eq("Yes").sum(),
     att_all["blocking_error_pre"].eq("No").sum()],
    [res_all["blocking_error_pre"].eq("Yes").sum(),
     res_all["blocking_error_pre"].eq("No").sum()],
]
or_val, fisher_p = stats.fisher_exact(table_2x2)
log(f"\n--- Fisher's Exact Test: Attending vs Resident (overall) ---")
log(f"  Attending: {table_2x2[0][0]} Yes / {table_2x2[0][1]} No")
log(f"  Resident:  {table_2x2[1][0]} Yes / {table_2x2[1][1]} No")
log(f"  OR = {or_val:.3f}, p = {fisher_p:.4f}")

# OR with 95% CI (log method)
a, b = table_2x2[0]
c, d = table_2x2[1]
log_or = np.log(or_val) if or_val > 0 else np.nan
se_log_or = np.sqrt(1/max(a,1) + 1/max(b,1) + 1/max(c,1) + 1/max(d,1))
or_ci_low = np.exp(log_or - 1.96 * se_log_or)
or_ci_high = np.exp(log_or + 1.96 * se_log_or)
log(f"  OR 95% CI: ({or_ci_low:.3f}–{or_ci_high:.3f})")

# Mantel-Haenszel stratified OR (adjusting for specialty)
log(f"\n--- Mantel-Haenszel Stratified Analysis (adjusting for specialty) ---")
mh_num = 0
mh_den = 0
mh_var = 0
n_valid_strata = 0

for spec in specialties:
    spec_data = ratings_with_spec[ratings_with_spec["specialty"] == spec]
    res_d = spec_data[spec_data["rater_role"] == "resident"]
    att_d = spec_data[spec_data["rater_role"] == "attending"]

    if len(res_d) == 0 or len(att_d) == 0:
        continue

    a_s = att_d["blocking_error_pre"].eq("Yes").sum()
    b_s = att_d["blocking_error_pre"].eq("No").sum()
    c_s = res_d["blocking_error_pre"].eq("Yes").sum()
    d_s = res_d["blocking_error_pre"].eq("No").sum()
    n_s = a_s + b_s + c_s + d_s

    if n_s == 0:
        continue

    n_valid_strata += 1
    mh_num += (a_s * d_s) / n_s
    mh_den += (b_s * c_s) / n_s

if mh_den > 0:
    mh_or = mh_num / mh_den
    log(f"  Valid strata: {n_valid_strata}")
    log(f"  Mantel-Haenszel OR = {mh_or:.3f}")
    log(f"  (Crude OR = {or_val:.3f})")
    log(f"  Interpretation: {'Confounding present' if abs(mh_or - or_val) / or_val > 0.1 else 'Minimal confounding'} "
        f"(MH vs crude difference: {abs(mh_or - or_val)/or_val*100:.1f}%)")
else:
    log(f"  Mantel-Haenszel OR: cannot compute (empty strata)")

# ══════════════════════════════════════════════════════════════════════════════
# 3. DATA CONSISTENCY AUDIT
# ══════════════════════════════════════════════════════════════════════════════
log("\n\n" + "=" * 70)
log("3. DATA CONSISTENCY AUDIT")
log("=" * 70)

# 3a. PASS card count
log(f"\n--- 3a. PASS Card Count ---")
pass_cards = cards[cards["s5_decision"] == "PASS"]
log(f"  Cards with s5_decision=PASS: {len(pass_cards)}")
log(f"  Unique PASS cards in ratings: {pass_ratings['card_uid'].nunique()}")
log(f"  → Manuscript should report: {len(pass_cards)} PASS cards")

# 3b. Total cards by decision
log(f"\n--- 3b. Card Decision Distribution ---")
decision_counts = cards["s5_decision"].value_counts()
for dec, cnt in decision_counts.items():
    log(f"  {dec}: {cnt}")
log(f"  Total: {len(cards)}")

# 3c. Ratings per card distribution
log(f"\n--- 3c. Ratings per Card ---")
ratings_per_card = ratings.groupby("card_uid")["rater_id"].nunique()
log(f"  Mean: {ratings_per_card.mean():.2f}")
log(f"  Distribution:")
for n_raters, count in ratings_per_card.value_counts().sort_index().items():
    log(f"    {n_raters} raters: {count} cards")

# 3d. Total ratings by role
log(f"\n--- 3d. Total Ratings by Role ---")
for role in ["resident", "attending"]:
    role_ids = set(rater_summary[rater_summary["role"] == role]["rater_id"])
    n = ratings[ratings["rater_id"].isin(role_ids)].shape[0]
    log(f"  {role}: {n} ratings")
log(f"  Total: {len(ratings)}")

# 3e. Calibration vs non-calibration
log(f"\n--- 3e. Calibration Items ---")
cal = ratings[ratings["is_calibration"] == 1]
non_cal = ratings[ratings["is_calibration"] == 0]
log(f"  Calibration ratings: {len(cal)}")
log(f"  Non-calibration ratings: {len(non_cal)}")
log(f"  Calibration unique cards: {cal['card_uid'].nunique()}")

# 3f. Critical error (blocking_error) counts
log(f"\n--- 3f. Blocking Error Distribution ---")
# All ratings
be_all = ratings["blocking_error_pre"].value_counts()
log(f"  All ratings (pre): {be_all.to_dict()}")
# PASS cards only
be_pass = pass_ratings["blocking_error_pre"].value_counts()
log(f"  PASS cards only (pre): {be_pass.to_dict()}")
# REGEN cards only
regen_ratings = ratings[ratings["card_s5_decision"].isin(["CARD_REGEN", "IMAGE_REGEN"])]
be_regen = regen_ratings["blocking_error_pre"].value_counts()
log(f"  REGEN cards only (pre): {be_regen.to_dict()}")

# 3g. Critical error rate (S5-PASS cards with blocking_error = Yes by BOTH raters)
log(f"\n--- 3g. Critical Error Rate (confirmed by multiple raters) ---")
# Cards where ALL raters agreed on blocking error
confirmed_fn = card_level[card_level["all_blocking_error"]]["card_uid"].tolist()
log(f"  Cards with ALL raters flagging blocking_error: {len(confirmed_fn)}")
if len(confirmed_fn) > 0:
    cr, ci_l, ci_h = clopper_pearson_ci(len(confirmed_fn), n_pass_cards)
    log(f"  Critical error rate: {cr*100:.2f}% (95% CI: {ci_l*100:.2f}–{ci_h*100:.2f}%)")

# ── Save results ────────────────────────────────────────────────────────────
with open(OUT_DIR / "sensitivity_analysis_results.txt", "w") as f:
    f.write("\n".join(results))

log("\n" + "=" * 70)
log(f"ANALYSIS COMPLETE — Results saved to: {OUT_DIR}/")
log("=" * 70)

"""Paper 3: Pilot Educational Effectiveness Analysis (N=26)
De-identifies data and runs primary outcome analyses.
"""
import numpy as np
import pandas as pd
from scipy import stats
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)

# --- Paths ---
BASE = Path('/Users/eugene/workspace/meducai')
BASELINE = BASE / '1_Secure_Participant_Info/raw_identifiable/[연구 참여 동의서] 전문의 시험 대비 MeducAI 사용자 평가 연구(응답).xlsx'
FINAL = BASE / '1_Secure_Participant_Info/raw_identifiable/[FINAL 설문] MeducAI 사용자 경험 및 학습 효과 평가 (시험 후)(응답).xlsx'
OUT = BASE / '2_Data/survey_responses/analysis'
OUT.mkdir(parents=True, exist_ok=True)
DEID_OUT = BASE / '2_Data/survey_responses'

# --- Load ---
bl = pd.read_excel(BASELINE)
fi = pd.read_excel(FINAL)

print(f"Baseline: {len(bl)} rows, Final: {len(fi)} rows")

# --- Column mapping (by position/prefix) ---
# Baseline columns by prefix
bl_cols = {
    'email': '이메일 주소',
    'hospital': [c for c in bl.columns if 'S0-2' in c][0],
    'age': [c for c in bl.columns if 'S0-3' in c][0],
    'gender': [c for c in bl.columns if 'S0-4' in c][0],
    'training': [c for c in bl.columns if 'S0-5' in c][0],
    'F11_1': [c for c in bl.columns if 'F11-1' in c][0],
    'F11_2': [c for c in bl.columns if 'F11-2' in c][0],
    'F11_3': [c for c in bl.columns if 'F11-3' in c][0],
    'F14_4': [c for c in bl.columns if 'F14-4' in c][0],
    'F7': [c for c in bl.columns if c.startswith('F7.')][0] if any(c.startswith('F7.') for c in bl.columns) else [c for c in bl.columns if 'F7' in c][0],
    'stress_bl': [c for c in bl.columns if 'F15-1' in c][0],
    'sleep_hrs_bl': [c for c in bl.columns if 'F15-2' in c][0],
    'sleep_qual_bl': [c for c in bl.columns if 'F15-3' in c][0],
    'mood_bl': [c for c in bl.columns if 'F15-4' in c][0],
    'exercise_bl': [c for c in bl.columns if 'F15-5' in c][0],
}

# Final columns by prefix
fi_cols = {
    'email': '이메일 주소',
    'A1': [c for c in fi.columns if 'A1.' in c][0],
    'A2': [c for c in fi.columns if 'A2.' in c][0],
    'A3': [c for c in fi.columns if 'A3.' in c][0],
    'A4': [c for c in fi.columns if 'A4.' in c][0],
    'A5': [c for c in fi.columns if 'A5.' in c][0],
    'B1': [c for c in fi.columns if 'B1.' in c][0],
    'B2': [c for c in fi.columns if 'B2.' in c][0],
    'B3': [c for c in fi.columns if 'B3.' in c][0],
    'B4': [c for c in fi.columns if 'B4.' in c][0],
    'C1': [c for c in fi.columns if 'C1.' in c][0],
    'C2': [c for c in fi.columns if 'C2.' in c][0],
    'C3': [c for c in fi.columns if 'C3.' in c][0],
    'C4': [c for c in fi.columns if 'C4.' in c][0],
    'D1': [c for c in fi.columns if 'D1.' in c][0],
    'D2': [c for c in fi.columns if 'D2.' in c][0],
    'D3': [c for c in fi.columns if 'D3.' in c][0],
    'D4': [c for c in fi.columns if 'D4.' in c][0],
    'E1': [c for c in fi.columns if 'E1.' in c][0],
    'E2': [c for c in fi.columns if 'E2.' in c][0],
    'E3': [c for c in fi.columns if 'E3.' in c][0],
    'G1': [c for c in fi.columns if 'G1.' in c][0],
    'G2': [c for c in fi.columns if 'G2.' in c][0],
    'G3': [c for c in fi.columns if 'G3.' in c][0],
    'G4': [c for c in fi.columns if 'G4.' in c][0],
    'G5': [c for c in fi.columns if 'G5.' in c][0],
    'H1': [c for c in fi.columns if 'H1.' in c][0],
    'Z1': [c for c in fi.columns if 'Z1.' in c][0],
    'Z2': [c for c in fi.columns if 'Z2.' in c][0],
    'Z3': [c for c in fi.columns if 'Z3.' in c][0],
    'Z9': [c for c in fi.columns if 'Z9.' in c][0],
}

# --- Merge by email ---
bl_sub = bl[[bl_cols[k] for k in ['email', 'hospital', 'age', 'gender', 'training',
             'F11_1', 'F11_2', 'F11_3', 'F14_4', 'F7',
             'stress_bl', 'sleep_hrs_bl', 'sleep_qual_bl', 'mood_bl', 'exercise_bl']]].copy()
bl_sub.columns = ['email', 'hospital', 'age', 'gender', 'training',
                  'F11_1', 'F11_2', 'F11_3', 'F14_4', 'F7',
                  'stress_bl', 'sleep_hrs_bl', 'sleep_qual_bl', 'mood_bl', 'exercise_bl']

fi_sub = fi[[fi_cols[k] for k in fi_cols]].copy()
fi_sub.columns = list(fi_cols.keys())

merged = bl_sub.merge(fi_sub, on='email', how='inner')
print(f"Matched: {len(merged)} participants")

# --- De-identify ---
merged = merged.sort_values('email').reset_index(drop=True)
merged['pid'] = [f'P{i+1:02d}' for i in range(len(merged))]

# Determine user status
merged['is_user'] = merged['A1'].apply(lambda x: 1 if '예' in str(x) else 0)

# Save de-identified (drop email, hospital, name, phone)
deid_cols = [c for c in merged.columns if c not in ['email', 'hospital']]
deid = merged[deid_cols].copy()
deid.to_csv(DEID_OUT / 'paper3_deidentified.csv', index=False)
print(f"De-identified data saved: {len(deid)} rows, {len(deid.columns)} columns")

# --- Parse numeric values ---
def to_numeric(series):
    return pd.to_numeric(series, errors='coerce')

for col in ['F11_1', 'F11_2', 'F11_3', 'F14_4', 'Z1', 'Z2', 'Z3', 'Z9', 'A5',
            'B1', 'B2', 'B3', 'B4', 'C1', 'C2', 'C3', 'C4',
            'D1', 'D2', 'D3', 'D4', 'E1', 'E2', 'E3',
            'G1', 'G2', 'G3', 'G4', 'G5', 'H1']:
    if col in merged.columns:
        merged[col] = to_numeric(merged[col])

# --- Compute outcomes ---
merged['ECL_baseline'] = merged[['F11_1', 'F11_2', 'F11_3']].mean(axis=1)
merged['ECL_final'] = merged[['Z1', 'Z2', 'Z3']].mean(axis=1)
merged['delta_ECL'] = merged['ECL_final'] - merged['ECL_baseline']

merged['SE_baseline'] = to_numeric(merged['F14_4'])
merged['SE_final'] = to_numeric(merged['Z9'])
merged['delta_SE'] = merged['SE_final'] - merged['SE_baseline']

users = merged[merged['is_user'] == 1]
nonusers = merged[merged['is_user'] == 0]
print(f"Users: {len(users)}, Non-users: {len(nonusers)}")

# === Analysis 1: Sample Characteristics ===
char_rows = []
char_rows.append({'variable': 'N', 'overall': len(merged), 'users': len(users), 'nonusers': len(nonusers)})
char_rows.append({'variable': 'age_mean', 'overall': merged['age'].mean(), 'users': users['age'].mean(), 'nonusers': nonusers['age'].mean()})
char_rows.append({'variable': 'age_sd', 'overall': merged['age'].std(), 'users': users['age'].std(), 'nonusers': nonusers['age'].std()})

for gender_val in merged['gender'].dropna().unique():
    n_all = (merged['gender'] == gender_val).sum()
    n_u = (users['gender'] == gender_val).sum()
    n_nu = (nonusers['gender'] == gender_val).sum()
    char_rows.append({'variable': f'gender_{gender_val}', 'overall': n_all, 'users': n_u, 'nonusers': n_nu})

char_rows.append({'variable': 'baseline_N', 'overall': len(bl), 'users': '', 'nonusers': ''})
char_rows.append({'variable': 'final_N', 'overall': len(fi), 'users': '', 'nonusers': ''})
char_rows.append({'variable': 'response_rate', 'overall': f'{len(fi)/len(bl)*100:.1f}%', 'users': '', 'nonusers': ''})
char_rows.append({'variable': 'dropout_N', 'overall': len(bl) - len(merged), 'users': '', 'nonusers': ''})

char_df = pd.DataFrame(char_rows)
char_df.to_csv(OUT / 'paper3_sample_characteristics.csv', index=False)
print("\n=== Sample Characteristics ===")
print(char_df.to_string())

# === Analysis 2: Primary Outcomes ===
def rank_biserial_ci(x, y, n_boot=10000):
    """Rank-biserial r with bootstrap 95% CI."""
    stat, p = stats.mannwhitneyu(x, y, alternative='two-sided')
    n1, n2 = len(x), len(y)
    r = 1 - (2 * stat) / (n1 * n2)

    # Bootstrap CI
    combined = np.concatenate([x.values, y.values])
    labels = np.concatenate([np.ones(n1), np.zeros(n2)])
    boot_rs = []
    for _ in range(n_boot):
        idx = np.random.choice(len(combined), len(combined), replace=True)
        bx = combined[idx[labels[idx] == 1]] if sum(labels[idx] == 1) > 0 else x.values
        by = combined[idx[labels[idx] == 0]] if sum(labels[idx] == 0) > 0 else y.values
        if len(bx) > 0 and len(by) > 0:
            bU, _ = stats.mannwhitneyu(bx, by, alternative='two-sided')
            boot_rs.append(1 - (2 * bU) / (len(bx) * len(by)))
    ci_lower = np.percentile(boot_rs, 2.5) if boot_rs else np.nan
    ci_upper = np.percentile(boot_rs, 97.5) if boot_rs else np.nan
    return r, ci_lower, ci_upper, stat, p

outcome_rows = []
for outcome_name, delta_col in [('ECL_change', 'delta_ECL'), ('SE_change', 'delta_SE')]:
    u = users[delta_col].dropna()
    nu = nonusers[delta_col].dropna()

    if len(u) > 0 and len(nu) > 0:
        r, ci_l, ci_u, U, p = rank_biserial_ci(u, nu)
        outcome_rows.append({
            'outcome': outcome_name,
            'users_n': len(u), 'users_median': u.median(), 'users_q25': u.quantile(0.25), 'users_q75': u.quantile(0.75),
            'users_mean': u.mean(), 'users_sd': u.std(),
            'nonusers_n': len(nu), 'nonusers_median': nu.median(), 'nonusers_q25': nu.quantile(0.25), 'nonusers_q75': nu.quantile(0.75),
            'nonusers_mean': nu.mean(), 'nonusers_sd': nu.std(),
            'mann_whitney_U': U, 'p_value': p,
            'rank_biserial_r': r, 'r_ci_lower': ci_l, 'r_ci_upper': ci_u
        })

outcome_df = pd.DataFrame(outcome_rows)
outcome_df.to_csv(OUT / 'paper3_primary_outcomes.csv', index=False)
print("\n=== Primary Outcomes ===")
print(outcome_df.to_string())

# === Analysis 3: User-only Descriptives ===
user_desc_rows = []
user_metrics = {
    'B1_exam_help': 'B1', 'B2_core_concepts': 'B2', 'B3_no_irrelevant': 'B3', 'B4_structure': 'B4',
    'C1_factual_errors': 'C1', 'C2_plausible_errors': 'C2', 'C3_error_impact': 'C3', 'C4_error_count': 'C4',
    'D1_actual_time_min': 'D1', 'D2_estimated_trad_min': 'D2', 'D3_verification_min': 'D3', 'D4_time_saved': 'D4',
    'E1_trust': 'E1', 'E2_uncritical_use': 'E2', 'E3_critical_review': 'E3',
    'G1_satisfaction': 'G1', 'G2_useful_experience': 'G2', 'G3_TAM_usefulness': 'G3',
    'G4_TAM_ease': 'G4', 'G5_TAM_intention': 'G5',
    'H1_NPS': 'H1',
}

for label, col in user_metrics.items():
    if col in users.columns:
        s = to_numeric(users[col]).dropna()
        user_desc_rows.append({
            'metric': label, 'n': len(s),
            'mean': s.mean(), 'sd': s.std(), 'median': s.median(),
            'q25': s.quantile(0.25), 'q75': s.quantile(0.75),
            'min': s.min(), 'max': s.max()
        })

# NPS classification
if 'H1' in users.columns:
    nps_scores = to_numeric(users['H1']).dropna()
    promoters = (nps_scores >= 9).sum()
    passives = ((nps_scores >= 7) & (nps_scores <= 8)).sum()
    detractors = (nps_scores <= 6).sum()
    nps = (promoters - detractors) / len(nps_scores) * 100 if len(nps_scores) > 0 else np.nan
    user_desc_rows.append({'metric': 'NPS_score', 'n': len(nps_scores), 'mean': nps, 'sd': np.nan,
                           'median': np.nan, 'q25': promoters, 'q75': detractors, 'min': passives, 'max': np.nan})

user_desc_df = pd.DataFrame(user_desc_rows)
user_desc_df.to_csv(OUT / 'paper3_user_descriptives.csv', index=False)
print("\n=== User-only Descriptives ===")
print(user_desc_df.to_string())

# === Analysis 4: Dose-Response ===
dose_rows = []
if 'A5' in users.columns:
    hours = to_numeric(users['A5']).dropna()
    for outcome_name, delta_col in [('ECL_change', 'delta_ECL'), ('SE_change', 'delta_SE')]:
        valid = users[['A5', delta_col]].dropna()
        if len(valid) >= 5:
            rho, p = stats.spearmanr(to_numeric(valid['A5']), valid[delta_col])
            dose_rows.append({
                'outcome': outcome_name, 'n': len(valid),
                'spearman_rho': rho, 'p_value': p,
                'hours_median': to_numeric(valid['A5']).median(),
                'hours_range': f"{to_numeric(valid['A5']).min()}-{to_numeric(valid['A5']).max()}"
            })

dose_df = pd.DataFrame(dose_rows)
dose_df.to_csv(OUT / 'paper3_dose_response.csv', index=False)
print("\n=== Dose-Response ===")
print(dose_df.to_string())

# === Analysis 5: Post-hoc Power ===
from scipy.stats import norm

def min_detectable_effect_mwu(n1, n2, alpha=0.05, power=0.80):
    """Approximate minimum detectable effect size (Cohen's d) for Mann-Whitney U."""
    z_alpha = norm.ppf(1 - alpha / 2)
    z_beta = norm.ppf(power)
    n_harmonic = 2 * n1 * n2 / (n1 + n2)
    d = (z_alpha + z_beta) / np.sqrt(n_harmonic / 4)
    return d

n1, n2 = len(users), len(nonusers)
d_detectable = min_detectable_effect_mwu(n1, n2)

power_rows = [{
    'n_users': n1, 'n_nonusers': n2,
    'alpha': 0.05, 'target_power': 0.80,
    'min_detectable_cohens_d': round(d_detectable, 2),
    'interpretation': 'very large' if d_detectable > 0.8 else 'large' if d_detectable > 0.5 else 'medium'
}]
power_df = pd.DataFrame(power_rows)
power_df.to_csv(OUT / 'paper3_power_analysis.csv', index=False)
print("\n=== Power Analysis ===")
print(power_df.to_string())

# === Summary ===
summary = f"""Paper 3: Pilot Educational Effectiveness — Summary
===================================================
Baseline enrolled: {len(bl)}
Final completed: {len(fi)}
Matched (analyzed): {len(merged)}
Response rate: {len(fi)/len(bl)*100:.1f}%
Users: {len(users)}, Non-users: {len(nonusers)}

Primary Outcomes (User vs Non-user):
"""
for _, row in outcome_df.iterrows():
    summary += f"""
  {row['outcome']}:
    Users: median={row['users_median']:.2f} (IQR: {row['users_q25']:.2f}-{row['users_q75']:.2f}), n={int(row['users_n'])}
    Non-users: median={row['nonusers_median']:.2f} (IQR: {row['nonusers_q25']:.2f}-{row['nonusers_q75']:.2f}), n={int(row['nonusers_n'])}
    Mann-Whitney U={row['mann_whitney_U']:.1f}, p={row['p_value']:.4f}
    Rank-biserial r={row['rank_biserial_r']:.3f} (95% CI: {row['r_ci_lower']:.3f}-{row['r_ci_upper']:.3f})
"""

summary += f"""
Post-hoc Power:
  With n1={n1}, n2={n2}: minimum detectable Cohen's d = {d_detectable:.2f} ({power_rows[0]['interpretation']})
  Study is substantially underpowered for medium effects (d=0.5)

Note: This is an underpowered pilot study. Results should be interpreted as
directional/exploratory only, not as definitive evidence.
"""

(OUT / 'paper3_summary.txt').write_text(summary)
print(summary)
print("Files saved to:", OUT)

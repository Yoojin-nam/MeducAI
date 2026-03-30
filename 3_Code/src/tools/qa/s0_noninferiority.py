#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
s0_noninferiority.py

Purpose
- Implements S0 non-inferiority analysis with two-layer decision framework:
 1. Safety endpoint: prevents unacceptable increases in major errors (0-score cards)
 2. Primary NI endpoint: mean accuracy score non-inferiority test
- Uses clustered paired bootstrap to handle repeated measures (rater × group pairs)
- Produces deterministic outputs (CSV, MD, JSON) for arm selection

Assumptions
- Input: Long format CSV with one row per card
- Required columns: run_tag, arm, group_id, rater_id, card_id, accuracy_score
- Optional columns: entity_id, editing_time_sec

Exit codes
- 0: Success
- 1: Fail-fast error (missing baseline, insufficient data, etc.)

Usage
  python 3_Code/src/tools/qa/s0_noninferiority.py \
    --input_csv <path> \
    --baseline_arm A \
    --delta 0.05 \
    --ci 0.90 \
    --bootstrap_n 5000 \
    --seed 20251220 \
    --out_dir <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class AnalysisConfig:
    """Configuration for S0 non-inferiority analysis."""
    input_csv: Path
    baseline_arm: str
    delta: float
    ci_level: float
    bootstrap_n: int
    seed: int
    out_dir: Path
    min_pairs: int = 20
    major_error_margin: float = 0.02
    edit_time_margin_pct: float = 0.10
    edit_time_margin_abs: float = 2.0


@dataclass
class ArmResults:
    """Results for a single arm."""
    arm: str
    n_pairs: int
    n_cards: int
    mean_accuracy: float
    p0: float
    mean_edit_time: Optional[float] = None
    
    # Differences vs baseline
    diff_vs_baseline: Optional[float] = None
    diff_ci_low: Optional[float] = None
    diff_ci_high: Optional[float] = None
    
    rd0_vs_baseline: Optional[float] = None
    rd0_ci_low: Optional[float] = None
    rd0_ci_high: Optional[float] = None
    
    diff_edit_time: Optional[float] = None
    
    # Pass/fail flags
    ni_pass: Optional[bool] = None
    safety_pass: Optional[bool] = None
    edit_time_pass: Optional[bool] = None
    final_pass: Optional[bool] = None


def load_and_validate_data(input_csv: Path, baseline_arm: str, min_pairs: int) -> pd.DataFrame:
    """
    Load input CSV and validate required columns and data quality.
    
    Raises SystemExit if validation fails.
    """
    try:
        df = pd.read_csv(input_csv)
    except Exception as e:
        print(f"ERROR: Failed to read input CSV: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Required columns
    required = ['run_tag', 'arm', 'group_id', 'rater_id', 'card_id', 'accuracy_score']
    missing = [col for col in required if col not in df.columns]
    if missing:
        print(f"ERROR: Missing required columns: {missing}", file=sys.stderr)
        print(f"Available columns: {list(df.columns)}", file=sys.stderr)
        sys.exit(1)
    
    # Check baseline arm exists
    if baseline_arm not in df['arm'].unique():
        print(f"ERROR: Baseline arm '{baseline_arm}' not found in data", file=sys.stderr)
        print(f"Available arms: {sorted(df['arm'].unique())}", file=sys.stderr)
        sys.exit(1)
    
    # Validate accuracy_score values
    invalid_scores = df[~df['accuracy_score'].isin([0.0, 0.5, 1.0])]
    if len(invalid_scores) > 0:
        print(f"WARNING: Found {len(invalid_scores)} rows with invalid accuracy_score values", file=sys.stderr)
        print(f"Invalid values: {invalid_scores['accuracy_score'].unique()}", file=sys.stderr)
        df = df[df['accuracy_score'].isin([0.0, 0.5, 1.0])]
    
    # Check minimum pairs requirement
    pairs_with_baseline = df[df['arm'] == baseline_arm].groupby(['rater_id', 'group_id']).size()
    n_pairs_baseline = len(pairs_with_baseline)
    
    if n_pairs_baseline < min_pairs:
        print(f"ERROR: Baseline arm has only {n_pairs_baseline} unique (rater_id, group_id) pairs, minimum required: {min_pairs}", file=sys.stderr)
        sys.exit(1)
    
    # Warn about missing data
    arms = df['arm'].unique()
    for arm in arms:
        arm_df = df[df['arm'] == arm]
        arm_pairs = arm_df.groupby(['rater_id', 'group_id']).size()
        n_pairs_arm = len(arm_pairs)
        if n_pairs_arm < min_pairs:
            print(f"WARNING: Arm {arm} has only {n_pairs_arm} unique pairs (minimum recommended: {min_pairs})", file=sys.stderr)
    
    return df


def compute_arm_statistics(df: pd.DataFrame, arm: str) -> Tuple[float, float, Optional[float]]:
    """
    Compute mean accuracy, p0 (proportion of 0-score cards), and mean editing time for an arm.
    
    Returns:
        (mean_accuracy, p0, mean_edit_time)
    """
    arm_df = df[df['arm'] == arm].copy()
    
    mean_accuracy = arm_df['accuracy_score'].mean()
    p0 = (arm_df['accuracy_score'] == 0.0).mean()
    
    mean_edit_time = None
    if 'editing_time_sec' in arm_df.columns:
        edit_times = arm_df['editing_time_sec'].dropna()
        if len(edit_times) > 0:
            mean_edit_time = edit_times.mean() / 60.0  # Convert to minutes
    
    return mean_accuracy, p0, mean_edit_time


def clustered_bootstrap(
    df: pd.DataFrame,
    baseline_arm: str,
    candidate_arm: str,
    bootstrap_n: int,
    seed: int,
    ci_level: float
) -> Tuple[Dict[str, np.ndarray], Dict[str, Tuple[float, float]]]:
    """
    Perform clustered paired bootstrap resampling.
    
    Resamples (rater_id, group_id) pairs with replacement, then computes statistics
    for each arm within sampled pairs.
    
    Returns:
        (bootstrap_stats, ci_dict)
        - bootstrap_stats: dict with keys 'd', 'rd0', 'edit_time_diff' (arrays of bootstrap replicates)
        - ci_dict: dict with CI bounds for each statistic
    """
    np.random.seed(seed)
    
    # Get unique pairs that have data for both arms
    baseline_pairs = set(df[df['arm'] == baseline_arm][['rater_id', 'group_id']].apply(tuple, axis=1))
    candidate_pairs = set(df[df['arm'] == candidate_arm][['rater_id', 'group_id']].apply(tuple, axis=1))
    common_pairs = list(baseline_pairs & candidate_pairs)
    
    if len(common_pairs) == 0:
        raise ValueError(f"No common (rater_id, group_id) pairs between baseline {baseline_arm} and candidate {candidate_arm}")
    
    # Convert to list of tuples for indexing
    common_pairs = [tuple(p) for p in common_pairs]
    
    bootstrap_d = []
    bootstrap_rd0 = []
    bootstrap_edit_time_diff = []
    
    for _ in range(bootstrap_n):
        # Resample pairs with replacement
        sampled_pairs = np.random.choice(len(common_pairs), size=len(common_pairs), replace=True)
        
        # For each sampled pair, get data for both arms
        baseline_scores = []
        candidate_scores = []
        baseline_zeros = []
        candidate_zeros = []
        baseline_edit_times = []
        candidate_edit_times = []
        
        for pair_idx in sampled_pairs:
            rater_id, group_id = common_pairs[pair_idx]
            
            # Baseline arm data
            baseline_data = df[(df['arm'] == baseline_arm) & 
                              (df['rater_id'] == rater_id) & 
                              (df['group_id'] == group_id)]
            if len(baseline_data) > 0:
                baseline_scores.extend(baseline_data['accuracy_score'].tolist())
                baseline_zeros.extend((baseline_data['accuracy_score'] == 0.0).tolist())
                if 'editing_time_sec' in baseline_data.columns:
                    baseline_edit_times.extend(baseline_data['editing_time_sec'].dropna().tolist())
            
            # Candidate arm data
            candidate_data = df[(df['arm'] == candidate_arm) & 
                               (df['rater_id'] == rater_id) & 
                               (df['group_id'] == group_id)]
            if len(candidate_data) > 0:
                candidate_scores.extend(candidate_data['accuracy_score'].tolist())
                candidate_zeros.extend((candidate_data['accuracy_score'] == 0.0).tolist())
                if 'editing_time_sec' in candidate_data.columns:
                    candidate_edit_times.extend(candidate_data['editing_time_sec'].dropna().tolist())
        
        # Compute statistics for this bootstrap replicate
        if len(baseline_scores) > 0 and len(candidate_scores) > 0:
            mean_baseline = np.mean(baseline_scores)
            mean_candidate = np.mean(candidate_scores)
            d = mean_candidate - mean_baseline
            bootstrap_d.append(d)
            
            p0_baseline = np.mean(baseline_zeros)
            p0_candidate = np.mean(candidate_zeros)
            rd0 = p0_candidate - p0_baseline
            bootstrap_rd0.append(rd0)
            
            if len(baseline_edit_times) > 0 and len(candidate_edit_times) > 0:
                mean_edit_baseline = np.mean(baseline_edit_times) / 60.0  # Convert to minutes
                mean_edit_candidate = np.mean(candidate_edit_times) / 60.0
                edit_time_diff = mean_edit_candidate - mean_edit_baseline
                bootstrap_edit_time_diff.append(edit_time_diff)
    
    bootstrap_d = np.array(bootstrap_d)
    bootstrap_rd0 = np.array(bootstrap_rd0)
    bootstrap_edit_time_diff = np.array(bootstrap_edit_time_diff) if bootstrap_edit_time_diff else None
    
    # Compute CIs
    alpha = 1.0 - ci_level
    lower_percentile = (alpha / 2) * 100
    upper_percentile = (1 - alpha / 2) * 100
    
    ci_d = (np.percentile(bootstrap_d, lower_percentile), np.percentile(bootstrap_d, upper_percentile))
    ci_rd0 = (np.percentile(bootstrap_rd0, lower_percentile), np.percentile(bootstrap_rd0, upper_percentile))
    
    ci_edit_time = None
    if bootstrap_edit_time_diff is not None and len(bootstrap_edit_time_diff) > 0:
        ci_edit_time = (np.percentile(bootstrap_edit_time_diff, lower_percentile), 
                       np.percentile(bootstrap_edit_time_diff, upper_percentile))
    
    bootstrap_stats = {
        'd': bootstrap_d,
        'rd0': bootstrap_rd0,
        'edit_time_diff': bootstrap_edit_time_diff
    }
    
    ci_dict = {
        'd': ci_d,
        'rd0': ci_rd0,
        'edit_time_diff': ci_edit_time
    }
    
    return bootstrap_stats, ci_dict


def analyze_arm(
    df: pd.DataFrame,
    arm: str,
    baseline_arm: str,
    config: AnalysisConfig
) -> ArmResults:
    """Analyze a single candidate arm against baseline."""
    
    # Compute basic statistics
    mean_accuracy, p0, mean_edit_time = compute_arm_statistics(df, arm)
    
    # Count pairs and cards
    arm_df = df[df['arm'] == arm]
    n_pairs = len(arm_df.groupby(['rater_id', 'group_id']).size())
    n_cards = len(arm_df)
    
    # If this is the baseline arm, return early
    if arm == baseline_arm:
        return ArmResults(
            arm=arm,
            n_pairs=n_pairs,
            n_cards=n_cards,
            mean_accuracy=mean_accuracy,
            p0=p0,
            mean_edit_time=mean_edit_time,
            diff_vs_baseline=0.0,
            diff_ci_low=0.0,
            diff_ci_high=0.0,
            rd0_vs_baseline=0.0,
            rd0_ci_low=0.0,
            rd0_ci_high=0.0,
            ni_pass=True,
            safety_pass=True,
            edit_time_pass=True,
            final_pass=True
        )
    
    # Bootstrap analysis
    try:
        bootstrap_stats, ci_dict = clustered_bootstrap(
            df, baseline_arm, arm, config.bootstrap_n, config.seed, config.ci_level
        )
    except ValueError as e:
        print(f"WARNING: Cannot analyze arm {arm} vs baseline: {e}", file=sys.stderr)
        return ArmResults(
            arm=arm,
            n_pairs=n_pairs,
            n_cards=n_cards,
            mean_accuracy=mean_accuracy,
            p0=p0,
            mean_edit_time=mean_edit_time
        )
    
    # Extract differences and CIs
    baseline_mean, baseline_p0, baseline_edit_time = compute_arm_statistics(df, baseline_arm)
    
    diff_vs_baseline = mean_accuracy - baseline_mean
    diff_ci_low, diff_ci_high = ci_dict['d']
    
    rd0_vs_baseline = p0 - baseline_p0
    rd0_ci_low, rd0_ci_high = ci_dict['rd0']
    
    diff_edit_time = None
    edit_time_pass = None
    if mean_edit_time is not None and baseline_edit_time is not None:
        diff_edit_time = mean_edit_time - baseline_edit_time
        # Soft gate: not worse by more than +10% or +2 minutes
        margin = max(baseline_edit_time * config.edit_time_margin_pct, config.edit_time_margin_abs)
        edit_time_pass = diff_edit_time <= margin
    
    # Safety pass: UpperCI(RD0) <= major_error_margin
    safety_pass = rd0_ci_high <= config.major_error_margin
    
    # NI pass: LowerCI(d) > -delta
    ni_pass = diff_ci_low > -config.delta
    
    # Final pass: both safety and NI must pass
    final_pass = safety_pass and ni_pass
    
    return ArmResults(
        arm=arm,
        n_pairs=n_pairs,
        n_cards=n_cards,
        mean_accuracy=mean_accuracy,
        p0=p0,
        mean_edit_time=mean_edit_time,
        diff_vs_baseline=diff_vs_baseline,
        diff_ci_low=diff_ci_low,
        diff_ci_high=diff_ci_high,
        rd0_vs_baseline=rd0_vs_baseline,
        rd0_ci_low=rd0_ci_low,
        rd0_ci_high=rd0_ci_high,
        diff_edit_time=diff_edit_time,
        ni_pass=ni_pass,
        safety_pass=safety_pass,
        edit_time_pass=edit_time_pass,
        final_pass=final_pass
    )


def write_summary_csv(results: List[ArmResults], baseline_arm: str, config: AnalysisConfig, output_path: Path):
    """Write summary CSV with all results."""
    rows = []
    for r in results:
        row = {
            'arm': r.arm,
            'baseline_arm': baseline_arm,
            'n_pairs': r.n_pairs,
            'n_cards': r.n_cards,
            'mean_accuracy': r.mean_accuracy,
            'diff_vs_baseline': r.diff_vs_baseline if r.diff_vs_baseline is not None else '',
            'diff_ci_low': r.diff_ci_low if r.diff_ci_low is not None else '',
            'diff_ci_high': r.diff_ci_high if r.diff_ci_high is not None else '',
            'delta': config.delta,
            'ci_level': config.ci_level,
            'ni_pass': r.ni_pass if r.ni_pass is not None else '',
            'p0': r.p0,
            'rd0_vs_baseline': r.rd0_vs_baseline if r.rd0_vs_baseline is not None else '',
            'rd0_ci_low': r.rd0_ci_low if r.rd0_ci_low is not None else '',
            'rd0_ci_high': r.rd0_ci_high if r.rd0_ci_high is not None else '',
            'major_error_margin': config.major_error_margin,
            'safety_pass': r.safety_pass if r.safety_pass is not None else '',
            'final_pass': r.final_pass if r.final_pass is not None else '',
            'mean_edit_time': r.mean_edit_time if r.mean_edit_time is not None else '',
            'diff_edit_time': r.diff_edit_time if r.diff_edit_time is not None else '',
            'edit_time_pass': r.edit_time_pass if r.edit_time_pass is not None else ''
        }
        rows.append(row)
    
    df_out = pd.DataFrame(rows)
    df_out.to_csv(output_path, index=False)


def write_decision_md(results: List[ArmResults], baseline_arm: str, config: AnalysisConfig, output_path: Path):
    """Write decision markdown summary."""
    with open(output_path, 'w') as f:
        f.write("# S0 Non-Inferiority Analysis Results\n\n")
        f.write(f"**Baseline Arm:** {baseline_arm}\n")
        f.write(f"**Delta (Δ):** {config.delta}\n")
        f.write(f"**CI Level:** {config.ci_level * 100}%\n")
        f.write(f"**Bootstrap N:** {config.bootstrap_n}\n")
        f.write(f"**Seed:** {config.seed}\n")
        f.write(f"**Major Error Margin:** {config.major_error_margin}\n\n")
        f.write("## Results by Arm\n\n")
        
        for r in results:
            if r.arm == baseline_arm:
                continue
            
            f.write(f"### Arm {r.arm}\n")
            f.write(f"- **Mean Accuracy:** {r.mean_accuracy:.3f}\n")
            f.write(f"- **P0 (Major Error Rate):** {r.p0:.3f}\n")
            
            if r.safety_pass is not None:
                safety_status = "PASS" if r.safety_pass else "FAIL"
                f.write(f"- **Safety:** {safety_status}")
                if r.rd0_ci_high is not None:
                    f.write(f" (RD0 UpperCI = {r.rd0_ci_high:.4f} {'≤' if r.safety_pass else '>'} {config.major_error_margin})")
                f.write("\n")
            
            if r.ni_pass is not None:
                ni_status = "PASS" if r.ni_pass else "FAIL"
                f.write(f"- **NI:** {ni_status}")
                if r.diff_ci_low is not None:
                    f.write(f" (LowerCI = {r.diff_ci_low:.4f} {'>' if r.ni_pass else '≤'} -{config.delta})")
                f.write("\n")
            
            if r.final_pass is not None:
                final_status = "PASS" if r.final_pass else "FAIL"
                f.write(f"- **Final:** {final_status}\n")
            
            if r.mean_edit_time is not None and r.diff_edit_time is not None:
                f.write(f"- **Mean Edit Time:** {r.mean_edit_time:.2f} min (diff: {r.diff_edit_time:+.2f} min)")
                if r.edit_time_pass is not None:
                    f.write(f" {'PASS' if r.edit_time_pass else 'FAIL'}")
                f.write("\n")
            
            f.write("\n")
        
        f.write("## Recommendation\n\n")
        passing_arms = [r for r in results if r.final_pass is True and r.final_pass]
        if passing_arms:
            f.write("Among final_pass arms, choose lowest cost.\n")
        else:
            f.write("No arms passed both safety and NI gates. Consider using baseline arm or investigating failures.\n")


def compute_file_hash(filepath: Path) -> str:
    """Compute SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"


def write_bootstrap_meta(config: AnalysisConfig, output_path: Path):
    """Write bootstrap metadata JSON."""
    meta = {
        'seed': config.seed,
        'bootstrap_n': config.bootstrap_n,
        'ci_level': config.ci_level,
        'delta': config.delta,
        'major_error_margin': config.major_error_margin,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'input_file': str(config.input_csv),
        'input_file_hash': compute_file_hash(config.input_csv),
        'baseline_arm': config.baseline_arm
    }
    
    with open(output_path, 'w') as f:
        json.dump(meta, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='S0 Non-Inferiority Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python 3_Code/src/tools/qa/s0_noninferiority.py \\
    --input_csv data/qa_long.csv \\
    --baseline_arm A \\
    --delta 0.05 \\
    --ci 0.90 \\
    --bootstrap_n 5000 \\
    --seed 20251220 \\
    --out_dir output/qa/
        """
    )
    
    parser.add_argument('--input_csv', type=Path, required=True,
                       help='Input CSV (long format: one row per card)')
    parser.add_argument('--baseline_arm', type=str, required=True,
                       help='Baseline arm identifier (e.g., A)')
    parser.add_argument('--delta', type=float, default=0.05,
                       help='Non-inferiority margin (default: 0.05)')
    parser.add_argument('--ci', type=float, default=0.90,
                       help='CI level (default: 0.90)')
    parser.add_argument('--bootstrap_n', type=int, default=5000,
                       help='Number of bootstrap replicates (default: 5000)')
    parser.add_argument('--seed', type=int, default=20251220,
                       help='Random seed (default: 20251220)')
    parser.add_argument('--out_dir', type=Path, required=True,
                       help='Output directory')
    parser.add_argument('--min_pairs', type=int, default=20,
                       help='Minimum pairs required (default: 20)')
    parser.add_argument('--major_error_margin', type=float, default=0.02,
                       help='Major error margin for safety gate (default: 0.02)')
    
    args = parser.parse_args()
    
    # Create output directory
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    # Build config
    config = AnalysisConfig(
        input_csv=args.input_csv,
        baseline_arm=args.baseline_arm,
        delta=args.delta,
        ci_level=args.ci,
        bootstrap_n=args.bootstrap_n,
        seed=args.seed,
        out_dir=args.out_dir,
        min_pairs=args.min_pairs,
        major_error_margin=args.major_error_margin
    )
    
    # Load and validate data
    df = load_and_validate_data(config.input_csv, config.baseline_arm, config.min_pairs)
    
    # Analyze all arms
    arms = sorted(df['arm'].unique())
    results = []
    for arm in arms:
        result = analyze_arm(df, arm, config.baseline_arm, config)
        results.append(result)
    
    # Write outputs
    summary_path = config.out_dir / 'qa_s0_noninferiority_summary.csv'
    decision_path = config.out_dir / 'qa_s0_noninferiority_decision.md'
    meta_path = config.out_dir / 'qa_s0_noninferiority_bootstrap_meta.json'
    
    write_summary_csv(results, config.baseline_arm, config, summary_path)
    write_decision_md(results, config.baseline_arm, config, decision_path)
    write_bootstrap_meta(config, meta_path)
    
    print(f"Analysis complete. Outputs written to {config.out_dir}")
    print(f"  - Summary CSV: {summary_path}")
    print(f"  - Decision MD: {decision_path}")
    print(f"  - Bootstrap meta: {meta_path}")


if __name__ == '__main__':
    main()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
s0_noninferiority_setlevel.py

Purpose
- Implements S0 non-inferiority analysis using Set-level Overall Card Quality (1-5 Likert)
- Primary endpoint: Set-level Overall Card Quality
- Baseline: Arm E (High-End)
- Candidates: A, B, C, D (primary decision targets)
- Benchmark: F (ChatGPT, secondary, excluded from primary decision)
- Uses group-cluster bootstrap to handle repeated measures
- Applies Holm correction for multiple comparisons (default ON)

Assumptions
- Input: Set-long format CSV with one row per set per rater
- Required columns: run_tag, arm, group_id, set_id, rater_id, overall_quality_1to5
- Set-level aggregation: If multiple raters per set, use mean across raters

Exit codes
- 0: Success
- 1: Fail-fast error (missing baseline, insufficient data, etc.)

Usage
  python 3_Code/src/tools/qa/s0_noninferiority_setlevel.py \
    --input_csv <path> \
    --endpoint_col overall_quality_1to5 \
    --baseline_arm E \
    --candidate_arms A,B,C,D \
    --benchmark_arms F \
    --delta 0.5 \
    --n_boot 10000 \
    --seed 123 \
    --holm true \
    --out_json <path> \
    --out_csv <path> \
    --verbose
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class AnalysisConfig:
    """Configuration for S0 set-level non-inferiority analysis."""
    input_csv: Path
    endpoint_col: str = "overall_quality_1to5"
    baseline_arm: str = "E"
    candidate_arms: List[str] = field(default_factory=lambda: ["A", "B", "C", "D"])
    benchmark_arms: List[str] = field(default_factory=lambda: ["F"])
    delta: float = 0.5
    n_boot: int = 10000
    seed: int = 123
    holm: bool = True
    out_json: Optional[Path] = None
    out_csv: Optional[Path] = None
    verbose: bool = False


@dataclass
class ArmResult:
    """Results for a single arm."""
    arm: str
    role: str  # "baseline" | "candidate" | "benchmark"
    mean_score: float
    mean_diff_vs_baseline: Optional[float] = None
    lower_ci: Optional[float] = None
    upper_ci: Optional[float] = None
    ni_pass: Optional[bool] = None  # None for baseline/benchmark, bool for candidates
    n_groups_used: int = 0
    groups_dropped_missing_baseline: List[str] = field(default_factory=list)
    holm_adjusted_p: Optional[float] = None  # None for baseline/benchmark
    holm_pass: Optional[bool] = None  # None for baseline/benchmark
    note: str = ""


def load_and_validate_data(
    input_csv: Path,
    endpoint_col: str,
    baseline_arm: str,
    verbose: bool = False
) -> pd.DataFrame:
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
    required = ['run_tag', 'arm', 'group_id', 'set_id', 'rater_id', endpoint_col]
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
    
    # Remove rows with missing endpoint
    n_before = len(df)
    df = df[df[endpoint_col].notna()].copy()
    n_after = len(df)
    if n_before > n_after:
        if verbose:
            print(f"WARNING: Removed {n_before - n_after} rows with missing {endpoint_col}", file=sys.stderr)
    
    # Validate endpoint values (should be 1-5)
    invalid = df[~df[endpoint_col].isin([1, 2, 3, 4, 5])]
    if len(invalid) > 0:
        print(f"WARNING: Found {len(invalid)} rows with invalid {endpoint_col} values", file=sys.stderr)
        print(f"Invalid values: {sorted(invalid[endpoint_col].unique())}", file=sys.stderr)
        df = df[df[endpoint_col].isin([1, 2, 3, 4, 5])]
    
    if len(df) == 0:
        print(f"ERROR: No valid data after filtering", file=sys.stderr)
        sys.exit(1)
    
    return df


def aggregate_set_level_scores(
    df: pd.DataFrame,
    endpoint_col: str
) -> pd.DataFrame:
    """
    Aggregate set-level scores: if multiple raters per set, use mean.
    
    Returns:
        DataFrame with one row per (run_tag, arm, group_id, set_id)
    """
    # Group by set and compute mean across raters
    agg_cols = ['run_tag', 'arm', 'group_id', 'set_id']
    set_df = df.groupby(agg_cols, as_index=False).agg({
        endpoint_col: 'mean',
        'rater_id': lambda x: ','.join(sorted(set(x)))  # Keep track of raters
    }).rename(columns={endpoint_col: 'set_score'})
    
    return set_df


def group_cluster_bootstrap(
    set_df: pd.DataFrame,
    baseline_arm: str,
    candidate_arm: str,
    n_boot: int,
    seed: int
) -> Tuple[np.ndarray, List[str]]:
    """
    Perform group-cluster bootstrap resampling.
    
    Resamples group_id values with replacement, then computes mean difference
    for each bootstrap replicate.
    
    Returns:
        (bootstrap_diffs, groups_dropped)
        - bootstrap_diffs: array of bootstrap replicates of mean difference
        - groups_dropped: list of groups that were dropped (missing baseline or candidate)
    """
    np.random.seed(seed)
    
    # Get groups that have both baseline and candidate
    baseline_groups = set(set_df[set_df['arm'] == baseline_arm]['group_id'].unique())
    candidate_groups = set(set_df[set_df['arm'] == candidate_arm]['group_id'].unique())
    common_groups = sorted(list(baseline_groups & candidate_groups))
    
    if len(common_groups) == 0:
        raise ValueError(
            f"No common groups between baseline {baseline_arm} and candidate {candidate_arm}"
        )
    
    groups_dropped = sorted(list(
        (baseline_groups | candidate_groups) - set(common_groups)
    ))
    
    # Compute group-level means for baseline and candidate
    baseline_group_means = {}
    candidate_group_means = {}
    
    for group_id in common_groups:
        baseline_sets = set_df[
            (set_df['arm'] == baseline_arm) & 
            (set_df['group_id'] == group_id)
        ]
        if len(baseline_sets) > 0:
            baseline_group_means[group_id] = baseline_sets['set_score'].mean()
        
        candidate_sets = set_df[
            (set_df['arm'] == candidate_arm) & 
            (set_df['group_id'] == group_id)
        ]
        if len(candidate_sets) > 0:
            candidate_group_means[group_id] = candidate_sets['set_score'].mean()
    
    # Bootstrap resampling
    bootstrap_diffs = []
    
    for _ in range(n_boot):
        # Resample groups with replacement
        sampled_groups = np.random.choice(common_groups, size=len(common_groups), replace=True)
        
        # Compute mean difference for this bootstrap replicate
        baseline_scores = [baseline_group_means[g] for g in sampled_groups if g in baseline_group_means]
        candidate_scores = [candidate_group_means[g] for g in sampled_groups if g in candidate_group_means]
        
        if len(baseline_scores) > 0 and len(candidate_scores) > 0:
            mean_baseline = np.mean(baseline_scores)
            mean_candidate = np.mean(candidate_scores)
            diff = mean_candidate - mean_baseline
            bootstrap_diffs.append(diff)
    
    return np.array(bootstrap_diffs), groups_dropped


def holm_correction(
    p_values: Dict[str, float],
    alpha: float = 0.025
) -> Dict[str, Tuple[float, bool]]:
    """
    Apply Holm step-down procedure for multiple comparisons correction.
    
    Args:
        p_values: dict mapping arm -> p_value (one-sided, for LowerCI)
        alpha: significance level (default 0.025 for one-sided)
    
    Returns:
        dict mapping arm -> (adjusted_p, holm_pass)
    """
    if len(p_values) == 0:
        return {}
    
    # Sort by p-value (ascending)
    sorted_arms = sorted(p_values.items(), key=lambda x: x[1])
    
    n = len(sorted_arms)
    adjusted = {}
    
    for i, (arm, p) in enumerate(sorted_arms):
        # Holm adjustment: alpha / (n - i)
        adjusted_alpha = alpha / (n - i)
        adjusted_p = min(p * (n - i), 1.0)  # Holm-adjusted p-value
        holm_pass = adjusted_p <= adjusted_alpha
        
        adjusted[arm] = (adjusted_p, holm_pass)
    
    return adjusted


def compute_p_value_from_bootstrap(
    bootstrap_diffs: np.ndarray,
    delta: float
) -> float:
    """
    Compute one-sided p-value from bootstrap distribution.
    
    H0: mean_diff <= -delta
    H1: mean_diff > -delta
    
    p-value = proportion of bootstrap replicates where diff <= -delta
    """
    if len(bootstrap_diffs) == 0:
        return 1.0
    
    p_value = np.mean(bootstrap_diffs <= -delta)
    return p_value


def analyze_arm(
    set_df: pd.DataFrame,
    arm: str,
    baseline_arm: str,
    config: AnalysisConfig
) -> Tuple[ArmResult, Optional[np.ndarray]]:
    """
    Analyze a single arm against baseline.
    
    Returns:
        (ArmResult, bootstrap_diffs)
        - bootstrap_diffs is None for baseline, otherwise array of bootstrap replicates
    """
    # Compute overall mean score for this arm
    arm_sets = set_df[set_df['arm'] == arm]
    if len(arm_sets) == 0:
        return ArmResult(
            arm=arm,
            role="unknown",
            mean_score=0.0,
            n_groups_used=0,
            note="No data available"
        ), None
    
    mean_score = arm_sets['set_score'].mean()
    
    # Determine role
    if arm == baseline_arm:
        role = "baseline"
        return ArmResult(
            arm=arm,
            role=role,
            mean_score=mean_score,
            mean_diff_vs_baseline=0.0,
            lower_ci=0.0,
            upper_ci=0.0,
            ni_pass=None,
            n_groups_used=len(arm_sets['group_id'].unique()),
            note="baseline arm"
        ), None
    elif arm in config.benchmark_arms:
        role = "benchmark"
    elif arm in config.candidate_arms:
        role = "candidate"
    else:
        role = "other"
    
    # Bootstrap analysis
    try:
        bootstrap_diffs, groups_dropped = group_cluster_bootstrap(
            set_df, baseline_arm, arm, config.n_boot, config.seed
        )
    except ValueError as e:
        if config.verbose:
            print(f"WARNING: Cannot analyze arm {arm} vs baseline: {e}", file=sys.stderr)
        return ArmResult(
            arm=arm,
            role=role,
            mean_score=mean_score,
            n_groups_used=0,
            groups_dropped_missing_baseline=groups_dropped,
            note=f"Analysis failed: {e}"
        ), None
    
    if len(bootstrap_diffs) == 0:
        return ArmResult(
            arm=arm,
            role=role,
            mean_score=mean_score,
            n_groups_used=0,
            groups_dropped_missing_baseline=groups_dropped,
            note="No valid bootstrap replicates"
        ), None
    
    # Compute mean difference and CI
    mean_diff = np.mean(bootstrap_diffs)
    lower_ci = np.percentile(bootstrap_diffs, 2.5)
    upper_ci = np.percentile(bootstrap_diffs, 97.5)
    
    # NI pass/fail (only for candidates)
    ni_pass = None
    if role == "candidate":
        ni_pass = lower_ci > -config.delta
    
    # Count groups used
    baseline_groups = set(set_df[set_df['arm'] == baseline_arm]['group_id'].unique())
    arm_groups = set(set_df[set_df['arm'] == arm]['group_id'].unique())
    n_groups_used = len(baseline_groups & arm_groups)
    
    # Note
    note = ""
    if role == "benchmark":
        note = "benchmark only, excluded from primary decision"
    
    return ArmResult(
        arm=arm,
        role=role,
        mean_score=mean_score,
        mean_diff_vs_baseline=mean_diff,
        lower_ci=lower_ci,
        upper_ci=upper_ci,
        ni_pass=ni_pass,
        n_groups_used=n_groups_used,
        groups_dropped_missing_baseline=groups_dropped,
        note=note
    ), bootstrap_diffs


def apply_holm_correction(
    results: List[ArmResult],
    bootstrap_dict: Dict[str, np.ndarray],
    config: AnalysisConfig
) -> List[ArmResult]:
    """
    Apply Holm correction to candidate arms only.
    
    Args:
        results: List of ArmResult objects
        bootstrap_dict: dict mapping arm -> bootstrap_diffs array
        config: AnalysisConfig
    
    Modifies results in place to add holm_adjusted_p and holm_pass.
    """
    # Get candidate results
    candidate_results = [r for r in results if r.role == "candidate"]
    
    if len(candidate_results) == 0 or not config.holm:
        return results
    
    # Compute p-values for candidates from bootstrap distributions
    p_values = {}
    for r in candidate_results:
        if r.arm in bootstrap_dict and bootstrap_dict[r.arm] is not None:
            bootstrap_diffs = bootstrap_dict[r.arm]
            p_value = compute_p_value_from_bootstrap(bootstrap_diffs, config.delta)
            p_values[r.arm] = p_value
    
    # Apply Holm correction
    holm_adjusted = holm_correction(p_values, alpha=0.025)
    
    # Update results
    for r in candidate_results:
        if r.arm in holm_adjusted:
            r.holm_adjusted_p, r.holm_pass = holm_adjusted[r.arm]
    
    return results


def write_summary_csv(results: List[ArmResult], config: AnalysisConfig, output_path: Path):
    """Write summary CSV with all results."""
    rows = []
    for r in results:
        row = {
            'arm': r.arm,
            'role': r.role,
            'mean_score': r.mean_score,
            'mean_diff_vs_baseline': r.mean_diff_vs_baseline if r.mean_diff_vs_baseline is not None else '',
            'lower_ci': r.lower_ci if r.lower_ci is not None else '',
            'upper_ci': r.upper_ci if r.upper_ci is not None else '',
            'ni_pass': r.ni_pass if r.ni_pass is not None else '',
            'n_groups_used': r.n_groups_used,
            'groups_dropped_missing_baseline': ','.join(r.groups_dropped_missing_baseline) if r.groups_dropped_missing_baseline else '',
            'holm_adjusted_p': r.holm_adjusted_p if r.holm_adjusted_p is not None else '',
            'holm_pass': r.holm_pass if r.holm_pass is not None else '',
            'note': r.note
        }
        rows.append(row)
    
    df_out = pd.DataFrame(rows)
    df_out.to_csv(output_path, index=False)


def write_results_json(
    results: List[ArmResult],
    config: AnalysisConfig,
    output_path: Path
):
    """Write structured JSON results."""
    results_dict = {
        'config': {
            'input_csv': str(config.input_csv),
            'endpoint_col': config.endpoint_col,
            'baseline_arm': config.baseline_arm,
            'candidate_arms': config.candidate_arms,
            'benchmark_arms': config.benchmark_arms,
            'delta': config.delta,
            'n_boot': config.n_boot,
            'seed': config.seed,
            'holm': config.holm
        },
        'results': [
            {
                'arm': r.arm,
                'role': r.role,
                'mean_score': r.mean_score,
                'mean_diff_vs_baseline': r.mean_diff_vs_baseline,
                'lower_ci': r.lower_ci,
                'upper_ci': r.upper_ci,
                'ni_pass': r.ni_pass,
                'n_groups_used': r.n_groups_used,
                'groups_dropped_missing_baseline': r.groups_dropped_missing_baseline,
                'holm_adjusted_p': r.holm_adjusted_p,
                'holm_pass': r.holm_pass,
                'note': r.note
            }
            for r in results
        ],
        'metadata': {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'input_file_hash': compute_file_hash(config.input_csv)
        }
    }
    
    with open(output_path, 'w') as f:
        json.dump(results_dict, f, indent=2)


def compute_file_hash(filepath: Path) -> str:
    """Compute SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"


def main():
    parser = argparse.ArgumentParser(
        description='S0 Set-Level Non-Inferiority Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python 3_Code/src/tools/qa/s0_noninferiority_setlevel.py \\
    --input_csv data/set_long.csv \\
    --endpoint_col overall_quality_1to5 \\
    --baseline_arm E \\
    --candidate_arms A,B,C,D \\
    --benchmark_arms F \\
    --delta 0.5 \\
    --n_boot 10000 \\
    --seed 123 \\
    --holm true \\
    --out_json output/results.json \\
    --out_csv output/summary.csv \\
    --verbose
        """
    )
    
    parser.add_argument('--input_csv', type=Path, required=True,
                       help='Input CSV (set-long format: one row per set per rater)')
    parser.add_argument('--endpoint_col', type=str, default='overall_quality_1to5',
                       help='Endpoint column name (default: overall_quality_1to5)')
    parser.add_argument('--baseline_arm', type=str, default='E',
                       help='Baseline arm identifier (default: E)')
    parser.add_argument('--candidate_arms', type=str, default='A,B,C,D',
                       help='Comma-separated candidate arms (default: A,B,C,D)')
    parser.add_argument('--benchmark_arms', type=str, default='F',
                       help='Comma-separated benchmark arms (default: F)')
    parser.add_argument('--delta', type=float, default=0.5,
                       help='Non-inferiority margin (default: 0.5)')
    parser.add_argument('--n_boot', type=int, default=10000,
                       help='Number of bootstrap replicates (default: 10000)')
    parser.add_argument('--seed', type=int, default=123,
                       help='Random seed (default: 123)')
    parser.add_argument('--holm', type=str, default='true',
                       help='Apply Holm correction (default: true)')
    parser.add_argument('--out_json', type=Path, required=True,
                       help='Output JSON path')
    parser.add_argument('--out_csv', type=Path, required=True,
                       help='Output CSV path')
    parser.add_argument('--verbose', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Parse boolean
    holm = args.holm.lower() in ('true', '1', 'yes', 'on')
    
    # Parse candidate and benchmark arms
    candidate_arms = [a.strip() for a in args.candidate_arms.split(',')]
    benchmark_arms = [a.strip() for a in args.benchmark_arms.split(',')]
    
    # Build config
    config = AnalysisConfig(
        input_csv=args.input_csv,
        endpoint_col=args.endpoint_col,
        baseline_arm=args.baseline_arm,
        candidate_arms=candidate_arms,
        benchmark_arms=benchmark_arms,
        delta=args.delta,
        n_boot=args.n_boot,
        seed=args.seed,
        holm=holm,
        out_json=args.out_json,
        out_csv=args.out_csv,
        verbose=args.verbose
    )
    
    # Load and validate data
    df = load_and_validate_data(config.input_csv, config.endpoint_col, config.baseline_arm, config.verbose)
    
    # Aggregate to set level
    set_df = aggregate_set_level_scores(df, config.endpoint_col)
    
    if config.verbose:
        print(f"Loaded {len(df)} rows, aggregated to {len(set_df)} sets", file=sys.stderr)
    
    # Analyze all arms
    all_arms = sorted(set_df['arm'].unique())
    results = []
    bootstrap_dict = {}  # Store bootstrap_diffs for Holm correction
    
    for arm in all_arms:
        result, bootstrap_diffs = analyze_arm(set_df, arm, config.baseline_arm, config)
        results.append(result)
        if bootstrap_diffs is not None:
            bootstrap_dict[arm] = bootstrap_diffs
    
    # Apply Holm correction
    results = apply_holm_correction(results, bootstrap_dict, config)
    
    # Write outputs
    config.out_csv.parent.mkdir(parents=True, exist_ok=True)
    config.out_json.parent.mkdir(parents=True, exist_ok=True)
    
    write_summary_csv(results, config, config.out_csv)
    write_results_json(results, config, config.out_json)
    
    print(f"Analysis complete. Outputs written:")
    print(f"  - Summary CSV: {config.out_csv}")
    print(f"  - Results JSON: {config.out_json}")


if __name__ == '__main__':
    main()


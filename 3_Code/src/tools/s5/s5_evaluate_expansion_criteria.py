#!/usr/bin/env python3
"""
MeducAI S5R Expansion Criteria Evaluator

Evaluates preregistered expansion criteria for HOLDOUT decision based on S5R0 vs S5R2 comparison results.

Expansion criteria (from S5R_Experiment_Power_and_Significance_Plan.md):
- Expand if BOTH:
  1) Primary endpoint에서 ≥9/11 groups improve (After < Before), AND
  2) Primary endpoint의 median absolute reduction ≥ 5 percentage points

Usage:
    python3 3_Code/src/tools/s5/s5_evaluate_expansion_criteria.py \
      --base_dir . \
      --compare_dir 2_Data/metadata/generated/COMPARE__<before>__VS__<after> \
      --out_dir <output_directory>
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ExpansionCriteriaResult:
    """Result of expansion criteria evaluation."""
    criterion_1_met: bool  # ≥9/11 groups improve
    criterion_1_value: int  # Number of improved groups
    criterion_1_total: int  # Total number of groups
    criterion_2_met: bool  # median absolute reduction ≥ 5 percentage points
    criterion_2_value: float  # Median absolute reduction (percentage points)
    expand_recommended: bool  # Both criteria met
    primary_endpoint: str  # Endpoint name used for evaluation


def read_csv_dict(path: Path) -> List[Dict[str, Any]]:
    """Read CSV file and return list of dictionaries."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def evaluate_expansion_criteria(
    stats_summary_path: Path,
    group_level_path: Path,
    primary_endpoint_name: str = "S2_any_issue_rate_per_group",
) -> ExpansionCriteriaResult:
    """
    Evaluate expansion criteria based on comparison results.
    
    Args:
        stats_summary_path: Path to stats_summary__mm.csv
        group_level_path: Path to group_level__mm.csv
        primary_endpoint_name: Name of primary endpoint (default: S2_any_issue_rate_per_group)
    
    Returns:
        ExpansionCriteriaResult with evaluation results
    """
    # Read stats summary to get primary endpoint median difference
    stats_rows = read_csv_dict(stats_summary_path)
    primary_stats = None
    for row in stats_rows:
        if row.get("endpoint", "").strip() == primary_endpoint_name:
            primary_stats = row
            break
    
    if primary_stats is None:
        raise ValueError(f"Primary endpoint '{primary_endpoint_name}' not found in stats summary")
    
    # Read group-level data to count improved groups
    group_rows = read_csv_dict(group_level_path)
    
    # Extract primary endpoint columns (before/after)
    # Column names in group_level CSV are: {endpoint_name}_before and {endpoint_name}_after
    # For S2_any_issue_rate_per_group, the column is: s2_any_issue_rate_per_group_before
    endpoint_lower = primary_endpoint_name.lower()
    before_col = f"{endpoint_lower}_before"
    after_col = f"{endpoint_lower}_after"
    
    # If not found, try with explicit mapping for known endpoints
    if before_col not in group_rows[0]:
        # Map known endpoint names to CSV column names
        endpoint_col_map = {
            "s2_any_issue_rate_per_group": "s2_any_issue_rate_per_group",
            "img_any_issue_rate_per_group": "img_any_issue_rate_per_group",
            "s2_issues_per_card_per_group": "s2_issues_per_card",
            "ta_bad_rate_per_group": "ta_bad_rate_per_group",
        }
        base_col = endpoint_col_map.get(endpoint_lower, endpoint_lower)
        before_col = f"{base_col}_before"
        after_col = f"{base_col}_after"
    
    if before_col not in group_rows[0] or after_col not in group_rows[0]:
        available_cols = ", ".join(group_rows[0].keys())
        raise ValueError(
            f"Columns '{before_col}' or '{after_col}' not found in group_level CSV. "
            f"Available columns: {available_cols}"
        )
    
    # Count improved groups (After < Before for "lower is better" endpoint)
    improved_count = 0
    total_groups = len(group_rows)
    
    for row in group_rows:
        try:
            before_val = float(row[before_col])
            after_val = float(row[after_col])
            # For "lower is better" endpoints, improvement means After < Before
            if after_val < before_val:
                improved_count += 1
        except (ValueError, KeyError):
            continue
    
    # Criterion 1: ≥9/11 groups improve
    criterion_1_met = improved_count >= 9
    
    # Criterion 2: median absolute reduction ≥ 5 percentage points
    try:
        before_median = float(primary_stats.get("before_median", 0))
        after_median = float(primary_stats.get("after_median", 0))
        # Calculate absolute reduction (percentage points)
        # Note: values in stats_summary are in rate (0-1), so we convert to percentage points
        # "Reduction" means improvement, so for "lower is better": reduction = before - after
        # We take absolute value to get the magnitude of change
        before_median_pp = before_median * 100.0
        after_median_pp = after_median * 100.0
        median_absolute_reduction_pp = abs(before_median_pp - after_median_pp)
        criterion_2_met = median_absolute_reduction_pp >= 5.0
    except (ValueError, KeyError) as e:
        raise ValueError(f"Could not extract median values from stats summary: {e}")
    
    expand_recommended = criterion_1_met and criterion_2_met
    
    return ExpansionCriteriaResult(
        criterion_1_met=criterion_1_met,
        criterion_1_value=improved_count,
        criterion_1_total=total_groups,
        criterion_2_met=criterion_2_met,
        criterion_2_value=median_absolute_reduction_pp,
        expand_recommended=expand_recommended,
        primary_endpoint=primary_endpoint_name,
    )


def generate_report(
    result: ExpansionCriteriaResult,
    stats_summary_path: Path,
    output_path: Path,
) -> None:
    """Generate markdown report for expansion criteria evaluation."""
    md_lines: List[str] = []
    
    md_lines.append("# S5R Expansion Criteria Evaluation\n\n")
    md_lines.append("## Preregistered Expansion Criteria\n\n")
    md_lines.append("From `S5R_Experiment_Power_and_Significance_Plan.md`:\n\n")
    md_lines.append("**Expand if BOTH:**\n")
    md_lines.append("1. Primary endpoint에서 **≥9/11 groups improve** (`After < Before`), AND\n")
    md_lines.append("2. Primary endpoint의 **median absolute reduction ≥ 5 percentage points**\n\n")
    
    md_lines.append("---\n\n")
    md_lines.append("## Evaluation Results\n\n")
    md_lines.append(f"**Primary Endpoint**: `{result.primary_endpoint}`\n\n")
    
    md_lines.append("### Criterion 1: Group Improvement Rate\n\n")
    md_lines.append(f"- **Improved groups**: {result.criterion_1_value} / {result.criterion_1_total}\n")
    md_lines.append(f"- **Required**: ≥9 / 11\n")
    md_lines.append(f"- **Status**: {'✅ **MET**' if result.criterion_1_met else '❌ **NOT MET**'}\n\n")
    
    md_lines.append("### Criterion 2: Median Absolute Reduction\n\n")
    md_lines.append(f"- **Median absolute reduction**: {result.criterion_2_value:.2f} percentage points\n")
    md_lines.append(f"- **Required**: ≥5.0 percentage points\n")
    md_lines.append(f"- **Status**: {'✅ **MET**' if result.criterion_2_met else '❌ **NOT MET**'}\n\n")
    
    md_lines.append("---\n\n")
    md_lines.append("## HOLDOUT Expansion Decision\n\n")
    
    if result.expand_recommended:
        md_lines.append("### ✅ **EXPAND TO HOLDOUT**\n\n")
        md_lines.append("**Both criteria are met.** Proceed with HOLDOUT expansion:\n")
        md_lines.append("- Target: **n=30–40 paired groups**\n")
        md_lines.append("- Analysis plan (endpoint/test) remains unchanged\n")
    else:
        md_lines.append("### ❌ **DO NOT EXPAND**\n\n")
        md_lines.append("**One or both criteria are not met.**\n\n")
        if not result.criterion_1_met:
            md_lines.append(f"- Criterion 1 failed: Only {result.criterion_1_value}/{result.criterion_1_total} groups improved (required: ≥9/11)\n")
        if not result.criterion_2_met:
            md_lines.append(f"- Criterion 2 failed: Median absolute reduction is {result.criterion_2_value:.2f} pp (required: ≥5.0 pp)\n")
    
    md_lines.append("\n---\n\n")
    md_lines.append("## Notes\n\n")
    md_lines.append("- This evaluation is based on DEV (n=11) results\n")
    md_lines.append("- Expansion decision is preregistered and binding\n")
    md_lines.append("- If expanded, HOLDOUT analysis must use the same endpoint/test as DEV\n")
    
    output_path.write_text("".join(md_lines), encoding="utf-8")
    print(f"✓ Expansion criteria report written: {output_path}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Evaluate S5R expansion criteria for HOLDOUT decision"
    )
    ap.add_argument(
        "--base_dir",
        required=True,
        type=str,
        help="Base directory of the project",
    )
    ap.add_argument(
        "--compare_dir",
        required=True,
        type=str,
        help="Directory containing comparison results (stats_summary__mm.csv, group_level__mm.csv)",
    )
    ap.add_argument(
        "--out_dir",
        default=None,
        type=str,
        help="Output directory (default: same as compare_dir)",
    )
    ap.add_argument(
        "--primary_endpoint",
        default="S2_any_issue_rate_per_group",
        type=str,
        help="Primary endpoint name (default: S2_any_issue_rate_per_group)",
    )
    args = ap.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    compare_dir = Path(args.compare_dir).resolve()
    
    if not compare_dir.is_absolute():
        compare_dir = base_dir / compare_dir
    
    if not compare_dir.exists():
        raise SystemExit(f"Comparison directory not found: {compare_dir}")
    
    stats_summary_path = compare_dir / "stats_summary__mm.csv"
    group_level_path = compare_dir / "group_level__mm.csv"
    
    if not stats_summary_path.exists():
        raise SystemExit(f"Stats summary not found: {stats_summary_path}")
    if not group_level_path.exists():
        raise SystemExit(f"Group level CSV not found: {group_level_path}")
    
    # Evaluate criteria
    try:
        result = evaluate_expansion_criteria(
            stats_summary_path=stats_summary_path,
            group_level_path=group_level_path,
            primary_endpoint_name=args.primary_endpoint,
        )
    except Exception as e:
        raise SystemExit(f"Error evaluating expansion criteria: {e}")
    
    # Determine output directory
    if args.out_dir:
        out_dir = Path(args.out_dir).resolve()
        if not out_dir.is_absolute():
            out_dir = base_dir / out_dir
    else:
        out_dir = compare_dir
    
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate report
    report_path = out_dir / "expansion_criteria_evaluation.md"
    generate_report(result, stats_summary_path, report_path)
    
    # Print summary to console
    print("\n" + "=" * 60)
    print("EXPANSION CRITERIA EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Primary Endpoint: {result.primary_endpoint}")
    print(f"\nCriterion 1 (≥9/11 groups improve):")
    print(f"  Improved: {result.criterion_1_value}/{result.criterion_1_total} groups")
    print(f"  Status: {'✅ MET' if result.criterion_1_met else '❌ NOT MET'}")
    print(f"\nCriterion 2 (median absolute reduction ≥5 pp):")
    print(f"  Reduction: {result.criterion_2_value:.2f} percentage points")
    print(f"  Status: {'✅ MET' if result.criterion_2_met else '❌ NOT MET'}")
    print(f"\n{'=' * 60}")
    if result.expand_recommended:
        print("✅ RECOMMENDATION: EXPAND TO HOLDOUT")
    else:
        print("❌ RECOMMENDATION: DO NOT EXPAND")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_set_long_from_google_form.py

Purpose
- Converts Google Form export (wide format) to set_long format for NI analysis
- Maps Q01-Q12 columns to local_qid and joins with assignment_map.csv
- Maps reviewer_email to rater_id using reviewer_master.csv
- Extracts Overall Card Quality (1-5) and optional fields

Input
- Google Form CSV (wide format with columns like [Q01] Overall Card Quality, etc.)
- assignment_map.csv (reviewer_id, local_qid, set_id, group_id, arm_id, role)
- reviewer_master.csv (reviewer_id, reviewer_email, role, etc.)

Output
- set_long.csv with columns: run_tag, arm, group_id, set_id, rater_id, overall_quality_1to5, ...

Usage
  python 3_Code/src/tools/qa/build_set_long_from_google_form.py \
    --google_form_csv <path> \
    --assignment_map_csv <path> \
    --reviewer_master_csv <path> \
    --run_tag <tag> \
    --out_csv <path> \
    --verbose
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


def extract_local_qid_from_column(col_name: str) -> Optional[str]:
    """
    Extract local_qid (Q01-Q12) from column name.
    
    Handles various formats:
    - [Q01] Overall Card Quality
    - Q01 Overall Card Quality
    - Q01_Overall_Card_Quality
    """
    # Pattern: Q followed by 01-12
    pattern = r'Q(0[1-9]|1[0-2])'
    match = re.search(pattern, col_name.upper())
    if match:
        return f"Q{match.group(1).zfill(2)}"
    return None


def find_quality_column(df: pd.DataFrame, local_qid: str) -> Optional[str]:
    """
    Find the Overall Card Quality column for a given local_qid.
    
    Looks for columns containing the local_qid and "quality" or "overall".
    """
    qid_pattern = local_qid.upper()
    quality_keywords = ['quality', 'overall', '품질']
    
    for col in df.columns:
        col_upper = col.upper()
        if qid_pattern in col_upper:
            for keyword in quality_keywords:
                if keyword.upper() in col_upper:
                    return col
    
    # Fallback: try exact match with brackets
    bracket_col = f"[{local_qid}] Overall Card Quality"
    if bracket_col in df.columns:
        return bracket_col
    
    return None


def find_optional_columns(df: pd.DataFrame, local_qid: str) -> Dict[str, Optional[str]]:
    """
    Find optional columns for a given local_qid.
    
    Returns dict mapping field_name -> column_name
    """
    optional = {}
    qid_pattern = local_qid.upper()
    
    # Map of field names to keywords
    field_keywords = {
        'blocking_error': ['blocking', 'block'],
        'critical_error_table': ['critical', 'table', '테이블'],
        'critical_error_infographic': ['critical', 'infographic', '인포그래픽'],
        'scope_failure': ['scope', 'alignment', '스코프'],
        'editing_time_min': ['time', 'editing', '시간', '분'],
        'accuracy_set': ['accuracy', '정확도']
    }
    
    for field_name, keywords in field_keywords.items():
        for col in df.columns:
            col_upper = col.upper()
            if qid_pattern in col_upper:
                if any(kw.upper() in col_upper for kw in keywords):
                    optional[field_name] = col
                    break
    
    return optional


def load_assignment_map(csv_path: Path) -> pd.DataFrame:
    """Load assignment_map.csv."""
    try:
        df = pd.read_csv(csv_path)
        required_cols = ['reviewer_id', 'local_qid', 'set_id', 'group_id', 'arm_id']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns in assignment_map: {missing}")
        return df
    except Exception as e:
        print(f"ERROR: Failed to load assignment_map: {e}", file=sys.stderr)
        sys.exit(1)


def load_reviewer_master(csv_path: Path) -> pd.DataFrame:
    """Load reviewer_master.csv."""
    try:
        df = pd.read_csv(csv_path)
        required_cols = ['reviewer_id', 'reviewer_email']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns in reviewer_master: {missing}")
        return df
    except Exception as e:
        print(f"ERROR: Failed to load reviewer_master: {e}", file=sys.stderr)
        sys.exit(1)


def process_google_form(
    google_form_csv: Path,
    assignment_map: pd.DataFrame,
    reviewer_master: pd.DataFrame,
    run_tag: str,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Process Google Form export and convert to set_long format.
    
    Returns:
        DataFrame in set_long format
    """
    # Load Google Form data
    try:
        df_form = pd.read_csv(google_form_csv)
    except Exception as e:
        print(f"ERROR: Failed to load Google Form CSV: {e}", file=sys.stderr)
        sys.exit(1)
    
    if verbose:
        print(f"Loaded Google Form with {len(df_form)} rows and {len(df_form.columns)} columns", file=sys.stderr)
    
    # Find email column (for reviewer mapping)
    email_col = None
    for col in df_form.columns:
        col_lower = col.lower()
        if 'email' in col_lower or '이메일' in col_lower:
            email_col = col
            break
    
    if email_col is None:
        print("ERROR: Could not find email column in Google Form", file=sys.stderr)
        print(f"Available columns: {list(df_form.columns)}", file=sys.stderr)
        sys.exit(1)
    
    # Extract all local_qids from columns
    qid_to_quality_col = {}
    qid_to_optional_cols = {}
    
    for col in df_form.columns:
        local_qid = extract_local_qid_from_column(col)
        if local_qid:
            quality_col = find_quality_column(df_form, local_qid)
            if quality_col:
                qid_to_quality_col[local_qid] = quality_col
            optional_cols = find_optional_columns(df_form, local_qid)
            if optional_cols:
                qid_to_optional_cols[local_qid] = optional_cols
    
    if verbose:
        print(f"Found quality columns for {len(qid_to_quality_col)} local_qids", file=sys.stderr)
        print(f"  QIDs: {sorted(qid_to_quality_col.keys())}", file=sys.stderr)
    
    # Process each row (each reviewer response)
    rows = []
    
    for idx, row in df_form.iterrows():
        reviewer_email = str(row[email_col]).strip().lower()
        
        # Map email to reviewer_id
        reviewer_match = reviewer_master[
            reviewer_master['reviewer_email'].str.lower().str.strip() == reviewer_email
        ]
        
        if len(reviewer_match) == 0:
            if verbose:
                print(f"WARNING: No reviewer_id found for email: {reviewer_email}", file=sys.stderr)
            continue
        
        reviewer_id = reviewer_match.iloc[0]['reviewer_id']
        
        # Process each local_qid (Q01-Q12)
        for local_qid in sorted(qid_to_quality_col.keys()):
            # Get assignment for this reviewer_id and local_qid
            assignment = assignment_map[
                (assignment_map['reviewer_id'] == reviewer_id) &
                (assignment_map['local_qid'] == local_qid)
            ]
            
            if len(assignment) == 0:
                if verbose:
                    print(f"WARNING: No assignment found for reviewer_id={reviewer_id}, local_qid={local_qid}", file=sys.stderr)
                continue
            
            if len(assignment) > 1:
                if verbose:
                    print(f"WARNING: Multiple assignments for reviewer_id={reviewer_id}, local_qid={local_qid}, using first", file=sys.stderr)
            
            assign = assignment.iloc[0]
            
            # Get quality score
            quality_col = qid_to_quality_col[local_qid]
            quality_value = row[quality_col]
            
            # Skip if missing
            if pd.isna(quality_value):
                continue
            
            # Convert to int if possible
            try:
                quality_int = int(float(quality_value))
                if quality_int not in [1, 2, 3, 4, 5]:
                    if verbose:
                        print(f"WARNING: Invalid quality value {quality_int} for {reviewer_id}/{local_qid}, skipping", file=sys.stderr)
                    continue
            except (ValueError, TypeError):
                if verbose:
                    print(f"WARNING: Could not convert quality value '{quality_value}' to int for {reviewer_id}/{local_qid}, skipping", file=sys.stderr)
                continue
            
            # Build output row
            out_row = {
                'run_tag': run_tag,
                'arm': assign['arm_id'],
                'group_id': assign['group_id'],
                'set_id': assign['set_id'],
                'rater_id': reviewer_id,
                'overall_quality_1to5': quality_int
            }
            
            # Add optional fields if available
            if local_qid in qid_to_optional_cols:
                for field_name, col_name in qid_to_optional_cols[local_qid].items():
                    if col_name and col_name in df_form.columns:
                        value = row[col_name]
                        # Convert boolean fields
                        if field_name in ['blocking_error', 'critical_error_table', 
                                        'critical_error_infographic', 'scope_failure']:
                            if pd.notna(value):
                                # Try to convert Yes/No, True/False, etc.
                                value_str = str(value).lower().strip()
                                out_row[field_name] = value_str in ('yes', 'true', '1', 'y', '예')
                            else:
                                out_row[field_name] = False
                        else:
                            out_row[field_name] = value
            
            rows.append(out_row)
    
    if len(rows) == 0:
        print("ERROR: No valid rows generated", file=sys.stderr)
        sys.exit(1)
    
    df_out = pd.DataFrame(rows)
    
    if verbose:
        print(f"Generated {len(df_out)} rows in set_long format", file=sys.stderr)
        print(f"  Arms: {sorted(df_out['arm'].unique())}", file=sys.stderr)
        print(f"  Groups: {sorted(df_out['group_id'].unique())}", file=sys.stderr)
        print(f"  Raters: {sorted(df_out['rater_id'].unique())}", file=sys.stderr)
    
    return df_out


def main():
    parser = argparse.ArgumentParser(
        description='Convert Google Form export to set_long format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python 3_Code/src/tools/qa/build_set_long_from_google_form.py \\
    --google_form_csv data/google_form_responses.csv \\
    --assignment_map_csv 1_Secure_Participant_Info/QA_Operations/assignment_map.csv \\
    --reviewer_master_csv 1_Secure_Participant_Info/reviewer_master.csv \\
    --run_tag S0_QA_2025-12-20 \\
    --out_csv data/set_long.csv \\
    --verbose
        """
    )
    
    parser.add_argument('--google_form_csv', type=Path, required=True,
                       help='Google Form export CSV (wide format)')
    parser.add_argument('--assignment_map_csv', type=Path, required=True,
                       help='Assignment map CSV (reviewer_id, local_qid, set_id, group_id, arm_id)')
    parser.add_argument('--reviewer_master_csv', type=Path, required=True,
                       help='Reviewer master CSV (reviewer_id, reviewer_email)')
    parser.add_argument('--run_tag', type=str, required=True,
                       help='Run tag identifier')
    parser.add_argument('--out_csv', type=Path, required=True,
                       help='Output CSV path (set_long format)')
    parser.add_argument('--verbose', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Load mapping files
    assignment_map = load_assignment_map(args.assignment_map_csv)
    reviewer_master = load_reviewer_master(args.reviewer_master_csv)
    
    # Process Google Form
    df_out = process_google_form(
        args.google_form_csv,
        assignment_map,
        reviewer_master,
        args.run_tag,
        args.verbose
    )
    
    # Write output
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(args.out_csv, index=False)
    
    print(f"Conversion complete. Output written to: {args.out_csv}")
    print(f"  Total rows: {len(df_out)}")
    print(f"  Columns: {list(df_out.columns)}")


if __name__ == '__main__':
    main()


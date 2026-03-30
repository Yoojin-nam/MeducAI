#!/usr/bin/env python3
"""
Analyze QA Survey Results from Google Forms CSV

This script merges Google Forms survey response CSV with assignment_map.csv
to enable analysis of QA evaluation results.

Usage:
    python 3_Code/src/tools/qa/analyze_qa_survey_results.py \
        --survey_csv path/to/google_forms_responses.csv \
        --assignment_map 0_Protocol/06_QA_and_Study/QA_Operations/assignment_map.csv \
        --reviewer_master 1_Secure_Participant_Info/reviewer_master.csv \
        --output_dir 2_Data/processed/qa_analysis \
        [--reviewer_id_column EMAIL] \
        [--local_qid_column QID]
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def load_reviewer_master(csv_path: Path) -> Dict[str, Dict[str, str]]:
    """Load reviewer_master.csv and return reviewer_id -> info mapping."""
    reviewers = {}
    if not csv_path.exists():
        raise FileNotFoundError(f"reviewer_master.csv not found: {csv_path}")
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            reviewer_id = row.get("reviewer_id", "").strip()
            if reviewer_id:
                reviewers[reviewer_id] = {
                    "name": row.get("reviewer_name", "").strip(),
                    "email": row.get("reviewer_email", "").strip().lower(),
                    "role": row.get("role", "").strip(),
                    "institution": row.get("institution", "").strip(),
                    "subspecialty": row.get("subspecialty", "").strip(),
                }
    
    return reviewers


def load_assignment_map(csv_path: Path) -> Dict[Tuple[str, str], Dict[str, str]]:
    """
    Load assignment_map.csv and return (reviewer_id, local_qid) -> assignment mapping.
    
    Returns:
        Dictionary mapping (reviewer_id, local_qid) to assignment details
    """
    assignments = {}
    if not csv_path.exists():
        raise FileNotFoundError(f"assignment_map.csv not found: {csv_path}")
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            reviewer_id = row.get("reviewer_id", "").strip()
            local_qid = row.get("local_qid", "").strip()
            if reviewer_id and local_qid:
                key = (reviewer_id, local_qid)
                assignments[key] = {
                    "reviewer_id": reviewer_id,
                    "local_qid": local_qid,
                    "set_id": row.get("set_id", "").strip(),
                    "group_id": row.get("group_id", "").strip(),
                    "arm_id": row.get("arm_id", "").strip(),
                    "role": row.get("role", "").strip(),
                }
    
    return assignments


def identify_reviewer_from_survey_row(
    row: Dict[str, str],
    reviewer_master: Dict[str, Dict[str, str]],
    reviewer_id_column: Optional[str] = None,
    email_column: Optional[str] = None,
    name_column: Optional[str] = None,
) -> Optional[str]:
    """
    Identify reviewer_id from survey row.
    
    Tries multiple methods:
    1. Direct reviewer_id column
    2. Email matching
    3. Name matching
    """
    # Method 1: Direct reviewer_id column
    if reviewer_id_column and reviewer_id_column in row:
        reviewer_id = row[reviewer_id_column].strip()
        if reviewer_id in reviewer_master:
            return reviewer_id
    
    # Method 2: Email matching
    if email_column and email_column in row:
        email = row[email_column].strip().lower()
        for rev_id, info in reviewer_master.items():
            if info["email"] == email:
                return rev_id
    
    # Method 3: Name matching
    if name_column and name_column in row:
        name = row[name_column].strip()
        for rev_id, info in reviewer_master.items():
            if info["name"] == name:
                return rev_id
    
    # Try common column names
    for col_name in ["reviewer_id", "Reviewer ID", "REVIEWER_ID", "reviewer", "Reviewer"]:
        if col_name in row:
            reviewer_id = row[col_name].strip()
            if reviewer_id in reviewer_master:
                return reviewer_id
    
    for col_name in ["email", "Email", "EMAIL", "이메일", "이메일 주소"]:
        if col_name in row:
            email = row[col_name].strip().lower()
            for rev_id, info in reviewer_master.items():
                if info["email"] == email:
                    return rev_id
    
    for col_name in ["name", "Name", "NAME", "이름", "성명"]:
        if col_name in row:
            name = row[col_name].strip()
            for rev_id, info in reviewer_master.items():
                if info["name"] == name:
                    return rev_id
    
    return None


def extract_qid_from_column_name(column_name: str) -> Optional[str]:
    """
    Extract Q01-Q12 from Google Form column name.
    
    Google Form columns typically look like:
    - "[Q01] B1. Blocking Error"
    - "[Q02] B2. Overall Card Quality"
    - "Q01 B1 Blocking Error"
    - etc.
    """
    # Pattern 1: [Q01], [Q02], etc.
    match = re.search(r'\[Q(\d{2})\]', column_name, re.IGNORECASE)
    if match:
        qnum = int(match.group(1))
        if 1 <= qnum <= 12:
            return f"Q{qnum:02d}"
    
    # Pattern 2: Q01, Q02, etc. (without brackets)
    match = re.search(r'\bQ(\d{2})\b', column_name, re.IGNORECASE)
    if match:
        qnum = int(match.group(1))
        if 1 <= qnum <= 12:
            return f"Q{qnum:02d}"
    
    # Pattern 3: Q1, Q2, etc. (single digit)
    match = re.search(r'\bQ(\d)\b', column_name, re.IGNORECASE)
    if match:
        qnum = int(match.group(1))
        if 1 <= qnum <= 12:
            return f"Q{qnum:02d}"
    
    return None


def identify_local_qid_from_survey_row(
    row: Dict[str, str],
    local_qid_column: Optional[str] = None,
) -> Optional[str]:
    """
    Identify local_qid (Q01-Q12) from survey row.
    
    Note: This function is used when each row represents one Q.
    For Google Form wide format, use extract_qid_from_column_name instead.
    """
    # Method 1: Direct local_qid column
    if local_qid_column and local_qid_column in row:
        qid = row[local_qid_column].strip()
        if qid.startswith("Q") and len(qid) >= 3:
            return qid
    
    # Method 2: Try common column names
    for col_name in ["local_qid", "Local QID", "LOCAL_QID", "QID", "qid", "질문번호", "Q 번호", "section", "Section"]:
        if col_name in row:
            qid = row[col_name].strip()
            if qid.startswith("Q") and len(qid) >= 3:
                return qid
    
    # Method 3: Look for Q01-Q12 pattern in any column value
    for col_name, value in row.items():
        if isinstance(value, str) and value.strip().startswith("Q") and len(value.strip()) >= 3:
            qid = value.strip()
            if qid[1:3].isdigit():
                return qid
    
    return None


def convert_wide_to_long_format(
    row: Dict[str, str],
    reviewer_id: str,
) -> List[Dict[str, str]]:
    """
    Convert Google Form wide format (one row per reviewer) to long format (one row per Q).
    
    Google Form typically has columns like:
    - Email (auto-collected)
    - "[Q01] B1. Blocking Error"
    - "[Q01] B2. Overall Card Quality"
    - "[Q02] B1. Blocking Error"
    - etc.
    
    Returns list of rows, one per Q01-Q12.
    """
    long_rows = []
    
    # Group columns by QID
    qid_columns = {}  # {qid: {column_name: value}}
    
    for col_name, value in row.items():
        qid = extract_qid_from_column_name(col_name)
        if qid:
            if qid not in qid_columns:
                qid_columns[qid] = {}
            qid_columns[qid][col_name] = value
    
    # Create one row per QID
    for qid in sorted(qid_columns.keys()):  # Q01, Q02, ..., Q12
        q_row = {
            "reviewer_id": reviewer_id,
            "local_qid": qid,
            **{k: v for k, v in qid_columns[qid].items()}
        }
        long_rows.append(q_row)
    
    return long_rows


def merge_survey_with_assignments(
    survey_csv_path: Path,
    assignment_map: Dict[Tuple[str, str], Dict[str, str]],
    reviewer_master: Dict[str, Dict[str, str]],
    reviewer_id_column: Optional[str] = None,
    local_qid_column: Optional[str] = None,
    wide_format: bool = True,
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Merge survey responses with assignment map.
    
    Returns:
        List of merged records with both survey data and assignment metadata
    """
    merged_records = []
    unmatched_rows = []
    
    if not survey_csv_path.exists():
        raise FileNotFoundError(f"Survey CSV not found: {survey_csv_path}")
    
    with open(survey_csv_path, "r", encoding="utf-8") as f:
        # Try to detect encoding and delimiter
        sample = f.read(1024)
        f.seek(0)
        
        # Try common delimiters
        delimiter = ","
        if "\t" in sample:
            delimiter = "\t"
        elif ";" in sample and sample.count(";") > sample.count(","):
            delimiter = ";"
        
        reader = csv.DictReader(f, delimiter=delimiter)
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            # Identify reviewer
            reviewer_id = identify_reviewer_from_survey_row(
                row, reviewer_master, reviewer_id_column
            )
            
            if not reviewer_id:
                unmatched_rows.append({
                    "row": row_num,
                    "reason": "reviewer_id not found",
                    "data": dict(row)
                })
                continue
            
            # Handle wide format (Google Form default: one row per reviewer, all Qs in columns)
            if wide_format:
                # Convert wide to long format
                long_rows = convert_wide_to_long_format(row, reviewer_id)
                
                if not long_rows:
                    unmatched_rows.append({
                        "row": row_num,
                        "reason": "no Q01-Q12 columns found in wide format",
                        "reviewer_id": reviewer_id,
                        "data": dict(row)
                    })
                    continue
                
                # Process each Q
                for q_row in long_rows:
                    local_qid = q_row.get("local_qid")
                    if not local_qid:
                        continue
                    
                    # Look up assignment
                    key = (reviewer_id, local_qid)
                    if key not in assignment_map:
                        unmatched_rows.append({
                            "row": row_num,
                            "reason": f"assignment not found for {local_qid}",
                            "reviewer_id": reviewer_id,
                            "local_qid": local_qid,
                            "data": dict(q_row)
                        })
                        continue
                    
                    # Merge survey data with assignment metadata
                    assignment = assignment_map[key]
                    reviewer_info = reviewer_master.get(reviewer_id, {})
                    
                    merged_record = {
                        # Assignment metadata
                        "reviewer_id": reviewer_id,
                        "reviewer_name": reviewer_info.get("name", ""),
                        "reviewer_email": reviewer_info.get("email", ""),
                        "reviewer_role": reviewer_info.get("role", ""),
                        "reviewer_institution": reviewer_info.get("institution", ""),
                        "reviewer_subspecialty": reviewer_info.get("subspecialty", ""),
                        "local_qid": local_qid,
                        "set_id": assignment.get("set_id", ""),
                        "group_id": assignment.get("group_id", ""),
                        "arm_id": assignment.get("arm_id", ""),
                        "role": assignment.get("role", ""),
                        # Survey response data (Q-specific columns)
                        **{f"survey_{k}": v for k, v in q_row.items() if k not in ["reviewer_id", "local_qid"]}
                    }
                    
                    merged_records.append(merged_record)
            
            else:
                # Long format: one row per Q
                local_qid = identify_local_qid_from_survey_row(row, local_qid_column)
                
                if not local_qid:
                    unmatched_rows.append({
                        "row": row_num,
                        "reason": "local_qid not found",
                        "reviewer_id": reviewer_id,
                        "data": dict(row)
                    })
                    continue
                
                # Look up assignment
                key = (reviewer_id, local_qid)
                if key not in assignment_map:
                    unmatched_rows.append({
                        "row": row_num,
                        "reason": "assignment not found in assignment_map",
                        "reviewer_id": reviewer_id,
                        "local_qid": local_qid,
                        "data": dict(row)
                    })
                    continue
                
                # Merge survey data with assignment metadata
                assignment = assignment_map[key]
                reviewer_info = reviewer_master.get(reviewer_id, {})
                
                merged_record = {
                    # Assignment metadata
                    "reviewer_id": reviewer_id,
                    "reviewer_name": reviewer_info.get("name", ""),
                    "reviewer_email": reviewer_info.get("email", ""),
                    "reviewer_role": reviewer_info.get("role", ""),
                    "reviewer_institution": reviewer_info.get("institution", ""),
                    "reviewer_subspecialty": reviewer_info.get("subspecialty", ""),
                    "local_qid": local_qid,
                    "set_id": assignment.get("set_id", ""),
                    "group_id": assignment.get("group_id", ""),
                    "arm_id": assignment.get("arm_id", ""),
                    "role": assignment.get("role", ""),
                    # Survey response data (all original columns)
                    **{f"survey_{k}": v for k, v in row.items()}
                }
                
                merged_records.append(merged_record)
    
    if unmatched_rows:
        print(f"\n⚠️  {len(unmatched_rows)} rows could not be matched:")
        for item in unmatched_rows[:10]:
            print(f"  Row {item['row']}: {item['reason']}")
            if 'reviewer_id' in item:
                print(f"    reviewer_id: {item.get('reviewer_id', 'N/A')}")
            if 'local_qid' in item:
                print(f"    local_qid: {item.get('local_qid', 'N/A')}")
        if len(unmatched_rows) > 10:
            print(f"    ... and {len(unmatched_rows) - 10} more")
    
    return merged_records, unmatched_rows


def save_merged_results(
    merged_records: List[Dict[str, str]],
    output_dir: Path,
    base_filename: str = "qa_survey_merged",
) -> None:
    """Save merged results to CSV and JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save as CSV
    csv_path = output_dir / f"{base_filename}.csv"
    if merged_records:
        fieldnames = list(merged_records[0].keys())
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(merged_records)
        print(f"✅ Saved merged results: {csv_path} ({len(merged_records)} records)")
    else:
        print(f"⚠️  No merged records to save")
    
    # Save as JSON for easier programmatic access
    json_path = output_dir / f"{base_filename}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(merged_records, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved merged results (JSON): {json_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Merge Google Forms survey results with assignment map for QA analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--survey_csv",
        type=str,
        required=True,
        help="Path to Google Forms survey response CSV",
    )
    parser.add_argument(
        "--assignment_map",
        type=str,
        default="0_Protocol/06_QA_and_Study/QA_Operations/assignment_map.csv",
        help="Path to assignment_map.csv",
    )
    parser.add_argument(
        "--reviewer_master",
        type=str,
        default="1_Secure_Participant_Info/reviewer_master.csv",
        help="Path to reviewer_master.csv",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="2_Data/processed/qa_analysis",
        help="Output directory for merged results",
    )
    parser.add_argument(
        "--base_dir",
        type=str,
        default=".",
        help="Project base directory",
    )
    parser.add_argument(
        "--reviewer_id_column",
        type=str,
        help="Column name for reviewer identifier (auto-detect if not specified)",
    )
    parser.add_argument(
        "--local_qid_column",
        type=str,
        help="Column name for local_qid (Q01-Q12) (auto-detect if not specified)",
    )
    parser.add_argument(
        "--email_column",
        type=str,
        help="Column name for email (for reviewer matching)",
    )
    parser.add_argument(
        "--name_column",
        type=str,
        help="Column name for name (for reviewer matching)",
    )
    parser.add_argument(
        "--wide_format",
        action="store_true",
        default=True,
        help="Input CSV is in wide format (one row per reviewer, all Qs in columns). Default: True for Google Forms",
    )
    parser.add_argument(
        "--long_format",
        action="store_false",
        dest="wide_format",
        help="Input CSV is in long format (one row per Q). Overrides --wide_format",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    survey_csv_path = base_dir / args.survey_csv
    assignment_map_path = base_dir / args.assignment_map
    reviewer_master_path = base_dir / args.reviewer_master
    output_dir = base_dir / args.output_dir
    
    print("=" * 70)
    print("QA Survey Results Analysis")
    print("=" * 70)
    print(f"Survey CSV: {survey_csv_path}")
    print(f"Assignment map: {assignment_map_path}")
    print(f"Reviewer master: {reviewer_master_path}")
    print(f"Output directory: {output_dir}")
    print("=" * 70)
    
    # Load data
    print("\n>>> Loading data...")
    reviewer_master = load_reviewer_master(reviewer_master_path)
    print(f"  Loaded {len(reviewer_master)} reviewers")
    
    assignment_map = load_assignment_map(assignment_map_path)
    print(f"  Loaded {len(assignment_map)} assignments")
    
    # Merge survey with assignments
    print("\n>>> Merging survey responses with assignments...")
    if args.wide_format:
        print("  Using wide format mode (Google Forms default)")
    else:
        print("  Using long format mode")
    
    merged_records, unmatched_rows = merge_survey_with_assignments(
        survey_csv_path,
        assignment_map,
        reviewer_master,
        args.reviewer_id_column,
        args.local_qid_column,
        args.wide_format,
    )
    
    print(f"  Matched: {len(merged_records)} records")
    print(f"  Unmatched: {len(unmatched_rows)} records")
    
    # Save results
    print("\n>>> Saving merged results...")
    save_merged_results(merged_records, output_dir)
    
    if unmatched_rows:
        # Save unmatched rows for debugging
        unmatched_path = output_dir / "qa_survey_unmatched.json"
        with open(unmatched_path, "w", encoding="utf-8") as f:
            json.dump(unmatched_rows, f, ensure_ascii=False, indent=2)
        print(f"⚠️  Unmatched rows saved: {unmatched_path}")
    
    print("\n" + "=" * 70)
    print("✅ Analysis Complete")
    print("=" * 70)
    print(f"\nNext steps:")
    print(f"1. Review merged results: {output_dir}/qa_survey_merged.csv")
    print(f"2. Use merged data for statistical analysis")
    print(f"3. Check unmatched rows if matching rate is low")
    print("=" * 70)


if __name__ == "__main__":
    main()


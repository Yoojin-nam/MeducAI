#!/usr/bin/env python3
"""
Verify PDF Distribution

This script verifies that PDFs are correctly distributed:
1. All assignments in assignment_map.csv have corresponding PDFs
2. Each reviewer folder has exactly 12 PDFs (Q01-Q12)
3. PDFs are correctly mapped from SET_XXX to reviewer folders
4. All SET_XXX PDFs exist in S0_final_time folder
"""

import csv
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def load_reviewer_master(csv_path: Path) -> Dict[str, str]:
    """Load reviewer_master.csv and return reviewer_id -> reviewer_name mapping."""
    reviewers = {}
    if not csv_path.exists():
        raise FileNotFoundError(f"reviewer_master.csv not found: {csv_path}")
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            reviewer_id = row.get("reviewer_id", "").strip()
            reviewer_name = row.get("reviewer_name", "").strip()
            if reviewer_id and reviewer_name:
                reviewers[reviewer_id] = reviewer_name
    
    return reviewers


def load_assignment_map(csv_path: Path) -> List[Dict[str, str]]:
    """Load assignment_map.csv."""
    assignments = []
    if not csv_path.exists():
        raise FileNotFoundError(f"assignment_map.csv not found: {csv_path}")
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            assignments.append({
                "reviewer_id": row.get("reviewer_id", "").strip(),
                "local_qid": row.get("local_qid", "").strip(),
                "set_id": row.get("set_id", "").strip(),
                "group_id": row.get("group_id", "").strip(),
                "arm_id": row.get("arm_id", "").strip(),
            })
    
    return assignments


def load_surrogate_map(csv_path: Path) -> Dict[Tuple[str, str], str]:
    """
    Load surrogate_map.csv and return (group_id, arm) -> surrogate_set_id mapping.
    
    Example: (group_10, F) -> SET_001
    """
    mapping = {}
    if not csv_path.exists():
        return mapping
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            group_id = row.get("group_id", "").strip()
            arm = row.get("arm", "").strip().upper()
            surrogate = row.get("surrogate_set_id", "").strip()
            if group_id and arm and surrogate:
                mapping[(group_id, arm)] = surrogate
    
    return mapping


def extract_set_id_from_assignment(set_id: str, group_id: str, arm_id: str, surrogate_map: Dict[Tuple[str, str], str]) -> str:
    """
    Extract SET_XXX from assignment.
    
    set_id format: "set_group_02_C" -> extract group_02 and arm C, then look up in surrogate_map
    """
    # Try to extract from set_id
    import re
    match = re.search(r"group_(\d+)", set_id)
    if match:
        group_num = match.group(1)
        placeholder_group_id = f"group_{int(group_num):02d}"
        key = (placeholder_group_id, arm_id.upper())
        surrogate = surrogate_map.get(key)
        if surrogate:
            return surrogate
    
    # Fallback: use group_id and arm_id directly
    key = (group_id, arm_id.upper())
    return surrogate_map.get(key, "")


def verify_pdf_distribution(
    base_dir: Path,
    assignment_map_path: Path,
    reviewer_master_path: Path,
    surrogate_map_path: Path,
    s0_final_time_dir: Path,
    by_reviewer_name_dir: Path,
) -> Tuple[bool, List[str]]:
    """
    Verify PDF distribution.
    
    Returns: (is_valid, list_of_errors)
    """
    errors = []
    
    print("=" * 70)
    print("PDF Distribution Verification")
    print("=" * 70)
    
    # Load data
    print("\n>>> Loading data...")
    reviewers = load_reviewer_master(reviewer_master_path)
    assignments = load_assignment_map(assignment_map_path)
    surrogate_map = load_surrogate_map(surrogate_map_path)
    
    print(f"  Loaded {len(reviewers)} reviewers")
    print(f"  Loaded {len(assignments)} assignments")
    print(f"  Loaded {len(surrogate_map)} surrogate mappings")
    
    # Check S0_final_time directory
    print("\n>>> Checking S0_final_time directory...")
    if not s0_final_time_dir.exists():
        errors.append(f"S0_final_time directory not found: {s0_final_time_dir}")
        return False, errors
    
    s0_pdfs = {f.name for f in s0_final_time_dir.glob("*.pdf")}
    print(f"  Found {len(s0_pdfs)} PDFs in S0_final_time")
    
    # Check for all SET_XXX PDFs (SET_001 to SET_108)
    expected_sets = {f"SET_SET_{i:03d}_S0_QA_final_time.pdf" for i in range(1, 109)}
    missing_sets = expected_sets - s0_pdfs
    if missing_sets:
        errors.append(f"Missing SET PDFs in S0_final_time: {sorted(missing_sets)}")
        print(f"  ⚠️  Missing {len(missing_sets)} SET PDFs")
    else:
        print(f"  ✅ All 108 SET PDFs found")
    
    # Check by_reviewer_name directory
    print("\n>>> Checking by_reviewer_name directory...")
    if not by_reviewer_name_dir.exists():
        errors.append(f"by_reviewer_name directory not found: {by_reviewer_name_dir}")
        return False, errors
    
    # Verify each assignment
    print("\n>>> Verifying assignments...")
    assignment_errors = []
    reviewer_pdf_counts = {}
    
    for assignment in assignments:
        reviewer_id = assignment["reviewer_id"]
        local_qid = assignment["local_qid"]
        set_id = assignment["set_id"]
        group_id = assignment["group_id"]
        arm_id = assignment["arm_id"]
        
        # Get SET_XXX from surrogate_map
        surrogate_set_id = extract_set_id_from_assignment(set_id, group_id, arm_id, surrogate_map)
        
        if not surrogate_set_id:
            assignment_errors.append(
                f"  {reviewer_id} {local_qid}: Could not find surrogate_set_id for {group_id} arm{arm_id}"
            )
            continue
        
        # Check if SET PDF exists
        expected_pdf_name = f"SET_{surrogate_set_id}_S0_QA_final_time.pdf"
        if expected_pdf_name not in s0_pdfs:
            assignment_errors.append(
                f"  {reviewer_id} {local_qid}: SET PDF not found: {expected_pdf_name}"
            )
            continue
        
        # Check if PDF exists in reviewer folder
        reviewer_name = reviewers.get(reviewer_id, reviewer_id)
        reviewer_folder = by_reviewer_name_dir / reviewer_name
        expected_reviewer_pdf = reviewer_folder / f"{local_qid}.pdf"
        
        if not expected_reviewer_pdf.exists():
            assignment_errors.append(
                f"  {reviewer_id} {local_qid}: PDF not found in reviewer folder: {expected_reviewer_pdf}"
            )
            continue
        
        # Count PDFs per reviewer
        if reviewer_id not in reviewer_pdf_counts:
            reviewer_pdf_counts[reviewer_id] = 0
        reviewer_pdf_counts[reviewer_id] += 1
    
    if assignment_errors:
        errors.extend(assignment_errors)
        print(f"  ⚠️  Found {len(assignment_errors)} assignment errors")
    else:
        print(f"  ✅ All assignments verified")
    
    # Check reviewer folders
    print("\n>>> Checking reviewer folders...")
    reviewer_folder_errors = []
    
    for reviewer_id, reviewer_name in reviewers.items():
        reviewer_folder = by_reviewer_name_dir / reviewer_name
        
        if not reviewer_folder.exists():
            reviewer_folder_errors.append(
                f"  {reviewer_name} ({reviewer_id}): Folder not found"
            )
            continue
        
        # Check for exactly 12 PDFs (Q01-Q12)
        pdfs = list(reviewer_folder.glob("Q*.pdf"))
        pdf_names = {p.name for p in pdfs}
        expected_pdfs = {f"Q{i:02d}.pdf" for i in range(1, 13)}
        
        missing_pdfs = expected_pdfs - pdf_names
        extra_pdfs = pdf_names - expected_pdfs
        
        if missing_pdfs:
            reviewer_folder_errors.append(
                f"  {reviewer_name} ({reviewer_id}): Missing PDFs: {sorted(missing_pdfs)}"
            )
        
        if extra_pdfs:
            reviewer_folder_errors.append(
                f"  {reviewer_name} ({reviewer_id}): Extra PDFs: {sorted(extra_pdfs)}"
            )
        
        # Check count
        expected_count = reviewer_pdf_counts.get(reviewer_id, 0)
        if len(pdfs) != expected_count:
            reviewer_folder_errors.append(
                f"  {reviewer_name} ({reviewer_id}): Expected {expected_count} PDFs, found {len(pdfs)}"
            )
    
    if reviewer_folder_errors:
        errors.extend(reviewer_folder_errors)
        print(f"  ⚠️  Found {len(reviewer_folder_errors)} reviewer folder errors")
    else:
        print(f"  ✅ All reviewer folders verified")
    
    # Summary
    print("\n" + "=" * 70)
    if errors:
        print(f"❌ Verification FAILED: {len(errors)} errors found")
        print("=" * 70)
        return False, errors
    else:
        print("✅ Verification PASSED: All checks passed")
        print("=" * 70)
        return True, []


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Verify PDF distribution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument(
        "--assignment_map",
        type=str,
        default="1_Secure_Participant_Info/QA_Operations/assignment_map.csv",
        help="Path to assignment_map.csv",
    )
    parser.add_argument(
        "--reviewer_master",
        type=str,
        default="1_Secure_Participant_Info/reviewer_master.csv",
        help="Path to reviewer_master.csv",
    )
    parser.add_argument(
        "--surrogate_map",
        type=str,
        default="1_Secure_Participant_Info/QA_Operations/surrogate_map.csv",
        help="Path to surrogate_map.csv",
    )
    parser.add_argument(
        "--s0_final_time_dir",
        type=str,
        default="6_Distributions/QA_Packets/S0_final_time",
        help="Directory containing SET_XXX PDFs",
    )
    parser.add_argument(
        "--by_reviewer_name_dir",
        type=str,
        default="6_Distributions/QA_Packets/by_reviewer_name",
        help="Directory containing reviewer folders",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    assignment_map_path = base_dir / args.assignment_map
    reviewer_master_path = base_dir / args.reviewer_master
    surrogate_map_path = base_dir / args.surrogate_map
    s0_final_time_dir = base_dir / args.s0_final_time_dir
    by_reviewer_name_dir = base_dir / args.by_reviewer_name_dir
    
    is_valid, errors = verify_pdf_distribution(
        base_dir,
        assignment_map_path,
        reviewer_master_path,
        surrogate_map_path,
        s0_final_time_dir,
        by_reviewer_name_dir,
    )
    
    if errors:
        print("\n>>> Detailed Errors:")
        for error in errors[:50]:  # Show first 50 errors
            print(error)
        if len(errors) > 50:
            print(f"\n... and {len(errors) - 50} more errors")
    
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()


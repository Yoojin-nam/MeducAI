#!/usr/bin/env python3
"""
Detailed PDF Distribution Verification

This script provides detailed verification including:
1. Mapping verification: assignment_map -> surrogate_map -> PDF files
2. Sample verification of actual PDF assignments
3. Statistics on distribution
"""

import csv
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

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
    """Extract SET_XXX from assignment."""
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


def verify_detailed(
    base_dir: Path,
    assignment_map_path: Path,
    reviewer_master_path: Path,
    surrogate_map_path: Path,
    s0_final_time_dir: Path,
    by_reviewer_name_dir: Path,
) -> None:
    """Detailed verification with statistics."""
    
    print("=" * 70)
    print("Detailed PDF Distribution Verification")
    print("=" * 70)
    
    # Load data
    print("\n>>> Loading data...")
    reviewers = load_reviewer_master(reviewer_master_path)
    assignments = load_assignment_map(assignment_map_path)
    surrogate_map = load_surrogate_map(surrogate_map_path)
    
    print(f"  Loaded {len(reviewers)} reviewers")
    print(f"  Loaded {len(assignments)} assignments")
    print(f"  Loaded {len(surrogate_map)} surrogate mappings")
    
    # Statistics
    print("\n>>> Statistics:")
    
    # Count assignments per reviewer
    assignments_per_reviewer = defaultdict(int)
    for assignment in assignments:
        reviewer_id = assignment["reviewer_id"]
        assignments_per_reviewer[reviewer_id] += 1
    
    print(f"  Assignments per reviewer: {dict(assignments_per_reviewer)}")
    
    # Count assignments per arm
    assignments_per_arm = defaultdict(int)
    for assignment in assignments:
        arm_id = assignment["arm_id"]
        assignments_per_arm[arm_id] += 1
    
    print(f"  Assignments per arm: {dict(sorted(assignments_per_arm.items()))}")
    
    # Verify mapping chain
    print("\n>>> Verifying mapping chain (assignment -> surrogate -> PDF)...")
    
    mapping_errors = []
    successful_mappings = []
    
    for assignment in assignments:
        reviewer_id = assignment["reviewer_id"]
        local_qid = assignment["local_qid"]
        set_id = assignment["set_id"]
        group_id = assignment["group_id"]
        arm_id = assignment["arm_id"]
        
        # Get SET_XXX from surrogate_map
        surrogate_set_id = extract_set_id_from_assignment(set_id, group_id, arm_id, surrogate_map)
        
        if not surrogate_set_id:
            mapping_errors.append({
                "reviewer_id": reviewer_id,
                "local_qid": local_qid,
                "group_id": group_id,
                "arm_id": arm_id,
                "error": "Could not find surrogate_set_id"
            })
            continue
        
        # Check if SET PDF exists
        expected_pdf_name = f"SET_{surrogate_set_id}_S0_QA_final_time.pdf"
        s0_pdf_path = s0_final_time_dir / expected_pdf_name
        
        if not s0_pdf_path.exists():
            mapping_errors.append({
                "reviewer_id": reviewer_id,
                "local_qid": local_qid,
                "surrogate_set_id": surrogate_set_id,
                "error": f"SET PDF not found: {expected_pdf_name}"
            })
            continue
        
        # Check if PDF exists in reviewer folder
        reviewer_name = reviewers.get(reviewer_id, reviewer_id)
        reviewer_folder = by_reviewer_name_dir / reviewer_name
        expected_reviewer_pdf = reviewer_folder / f"{local_qid}.pdf"
        
        if not expected_reviewer_pdf.exists():
            mapping_errors.append({
                "reviewer_id": reviewer_id,
                "local_qid": local_qid,
                "surrogate_set_id": surrogate_set_id,
                "error": f"PDF not found in reviewer folder: {expected_reviewer_pdf}"
            })
            continue
        
        successful_mappings.append({
            "reviewer_id": reviewer_id,
            "reviewer_name": reviewer_name,
            "local_qid": local_qid,
            "group_id": group_id,
            "arm_id": arm_id,
            "surrogate_set_id": surrogate_set_id,
        })
    
    print(f"  ✅ Successful mappings: {len(successful_mappings)}")
    if mapping_errors:
        print(f"  ⚠️  Mapping errors: {len(mapping_errors)}")
        for error in mapping_errors[:10]:
            print(f"    {error}")
        if len(mapping_errors) > 10:
            print(f"    ... and {len(mapping_errors) - 10} more errors")
    else:
        print(f"  ✅ All mappings successful")
    
    # Sample verification - show first few assignments for each reviewer
    print("\n>>> Sample assignments (first 3 per reviewer):")
    
    reviewer_assignments = defaultdict(list)
    for mapping in successful_mappings:
        reviewer_assignments[mapping["reviewer_id"]].append(mapping)
    
    for reviewer_id in sorted(reviewer_assignments.keys()):
        reviewer_name = reviewers.get(reviewer_id, reviewer_id)
        reviewer_assigns = sorted(reviewer_assignments[reviewer_id], key=lambda x: x["local_qid"])
        
        print(f"\n  {reviewer_name} ({reviewer_id}):")
        for assign in reviewer_assigns[:3]:
            print(f"    {assign['local_qid']}: {assign['group_id']} arm{assign['arm_id']} -> {assign['surrogate_set_id']}")
        if len(reviewer_assigns) > 3:
            print(f"    ... and {len(reviewer_assigns) - 3} more")
    
    # Check SET distribution
    print("\n>>> SET distribution (how many times each SET is assigned):")
    
    set_usage = defaultdict(int)
    for mapping in successful_mappings:
        set_usage[mapping["surrogate_set_id"]] += 1
    
    # Show SETs that are used more than once (shouldn't happen in proper assignment)
    duplicate_sets = {set_id: count for set_id, count in set_usage.items() if count > 1}
    if duplicate_sets:
        print(f"  ⚠️  SETs assigned multiple times: {dict(sorted(duplicate_sets.items()))}")
    else:
        print(f"  ✅ Each SET is assigned exactly once")
    
    # Check reviewer folder contents
    print("\n>>> Reviewer folder verification:")
    
    for reviewer_id, reviewer_name in sorted(reviewers.items()):
        reviewer_folder = by_reviewer_name_dir / reviewer_name
        
        if not reviewer_folder.exists():
            print(f"  ⚠️  {reviewer_name} ({reviewer_id}): Folder not found")
            continue
        
        pdfs = sorted(reviewer_folder.glob("Q*.pdf"))
        pdf_names = sorted([p.name for p in pdfs])
        expected_pdfs = [f"Q{i:02d}.pdf" for i in range(1, 13)]
        
        if pdf_names == expected_pdfs:
            print(f"  ✅ {reviewer_name}: {len(pdfs)} PDFs (Q01-Q12)")
        else:
            print(f"  ⚠️  {reviewer_name}: Expected Q01-Q12, found {pdf_names}")
    
    # Final summary
    print("\n" + "=" * 70)
    print("Summary:")
    print(f"  Total reviewers: {len(reviewers)}")
    print(f"  Total assignments: {len(assignments)}")
    print(f"  Successful mappings: {len(successful_mappings)}")
    print(f"  Mapping errors: {len(mapping_errors)}")
    print(f"  Unique SETs used: {len(set_usage)}")
    print("=" * 70)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Detailed PDF distribution verification",
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
    
    verify_detailed(
        base_dir,
        assignment_map_path,
        reviewer_master_path,
        surrogate_map_path,
        s0_final_time_dir,
        by_reviewer_name_dir,
    )


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Organize QA PDFs by Reviewer Name

This script organizes already-generated PDFs into folders named by reviewer names.
It reads assignment_map.csv and reviewer_master.csv to:
1. Map placeholder group_ids (group_01, group_02, etc.) to actual group_keys
2. Find corresponding PDF files in S0_final folder
3. Create folders named by reviewer names and copy PDFs with Q01-Q12 naming

Usage:
    python 3_Code/src/tools/qa/organize_pdfs_by_reviewer_name.py \
        --base_dir . \
        --pdf_source_dir 6_Distributions/QA_Packets/S0_final \
        [--dry_run]
"""

import argparse
import csv
import json
import re
import shutil
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
                    "email": row.get("reviewer_email", "").strip(),
                    "role": row.get("role", "").strip(),
                    "institution": row.get("institution", "").strip(),
                    "subspecialty": row.get("subspecialty", "").strip(),
                }
    
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
                "role": row.get("role", "").strip(),
            })
    
    return assignments


def load_groups_canonical(csv_path: Path) -> Dict[str, str]:
    """Load groups_canonical.csv and return group_id -> group_key mapping."""
    mapping = {}
    if not csv_path.exists():
        print(f"⚠️  groups_canonical.csv not found: {csv_path}")
        return mapping
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            group_id = row.get("group_id", "").strip()
            group_key = row.get("group_key", "").strip()
            if group_id and group_key:
                mapping[group_id] = group_key
    
    return mapping


def load_selected_groups(json_path: Path) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Load selected_18_groups.json and create placeholder -> group_key and placeholder -> group_id mappings.
    
    Returns: 
        (placeholder_to_key, placeholder_to_id) 
        where placeholder is "group_01", "group_02", etc.
    """
    if not json_path.exists():
        print(f"⚠️  selected_18_groups.json not found: {json_path}")
        return {}, {}
    
    with open(json_path, "r", encoding="utf-8") as f:
        selected_groups = json.load(f)
    
    # Create placeholder -> group_key and placeholder -> group_id mappings
    placeholder_to_key = {}
    placeholder_to_id = {}
    for i, group in enumerate(selected_groups, 1):
        placeholder = f"group_{i:02d}"
        group_key = group.get("group_key", "")
        group_id = group.get("group_id", "")
        if group_key:
            placeholder_to_key[placeholder] = group_key
        if group_id:
            placeholder_to_id[placeholder] = group_id
    
    return placeholder_to_key, placeholder_to_id


def load_s1_group_mapping(s1_path: Path) -> Dict[str, str]:
    """Load group_key -> group_id mapping from S1 results."""
    mapping = {}
    if not s1_path.exists():
        return mapping
    
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                group_id = record.get("group_id", "").strip()
                group_key = record.get("group_key", "").strip()
                if group_id and group_key:
                    mapping[group_key] = group_id
            except json.JSONDecodeError:
                continue
    
    return mapping


def build_placeholder_to_group_key_mapping(
    base_dir: Path,
    run_tag: Optional[str],
    arms: List[str],
    groups_canonical: Dict[str, str],
) -> Dict[str, str]:
    """
    Build placeholder -> group_key mapping from S1 outputs or groups_canonical.
    
    This replicates the logic from distribute_qa_packets.py
    """
    placeholder_to_key = {}
    
    # Method 1: Try to load from S1 outputs
    if run_tag:
        all_group_mappings = {}
        for arm in arms:
            s1_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"stage1_struct__arm{arm}.jsonl"
            if s1_path.exists():
                mapping = load_s1_group_mapping(s1_path)
                all_group_mappings.update(mapping)
        
        if all_group_mappings:
            # Load selected_18_groups.json to map placeholder to group_key
            selected_groups_file = base_dir / "2_Data" / "metadata" / "generated" / run_tag / "selected_18_groups.json"
            if selected_groups_file.exists():
                with open(selected_groups_file, "r", encoding="utf-8") as f:
                    selected_groups = json.load(f)
                
                # Create placeholder -> group_key mapping
                for i, group in enumerate(selected_groups, 1):
                    placeholder = f"group_{i:02d}"
                    group_key = group.get("group_key", "")
                    if group_key:
                        placeholder_to_key[placeholder] = group_key
                
                print(f"  Built {len(placeholder_to_key)} mappings from S1 outputs")
                return placeholder_to_key
    
    # Method 2: Fallback - try to infer from groups_canonical
    # This is less reliable but may work if group_id format matches
    # Note: This assumes group_01, group_02, etc. correspond to sorted groups
    # This is a best-effort fallback
    print("  ⚠️  Using fallback method - may not be accurate")
    return placeholder_to_key


def load_surrogate_map_group_id(csv_path: Path) -> Dict[Tuple[str, str], str]:
    """
    Load surrogate_map_group_id.csv and return (group_id, arm) -> surrogate_set_id mapping.
    
    Returns:
        Dict with key (group_id, arm) and value surrogate_set_id
    """
    mapping = {}
    if not csv_path.exists():
        return mapping
    
    import csv
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            group_id = row.get("group_id", "").strip()
            arm = row.get("arm", "").strip().upper()
            surrogate = row.get("surrogate_set_id", "").strip()
            if group_id and arm and surrogate:
                mapping[(group_id, arm)] = surrogate
    
    return mapping


def find_pdf_by_group_id_and_arm(
    pdf_dir: Path,
    group_id: str,
    arm: str,
    surrogate_map: Optional[Dict[Tuple[str, str], str]] = None,
) -> Optional[Path]:
    """
    Find PDF file matching group_id and arm.
    
    Supports two filename patterns:
    1. Non-blinded: SET_grp_{group_id}_arm{arm}_*.pdf
    2. Blinded: SET_{surrogate_set_id}_*.pdf (using surrogate_map)
    
    where group_id is like "1ef3e276b7" (from "grp_1ef3e276b7")
    """
    # Extract the hash part from group_id (e.g., "grp_1ef3e276b7" -> "1ef3e276b7")
    group_hash = group_id
    if group_id.startswith("grp_"):
        group_hash = group_id[4:]  # Remove "grp_" prefix
    elif group_id.startswith("group_"):
        # This is a placeholder, we need the actual group_id
        return None
    
    # Method 1: Try non-blinded format first
    pattern = f"SET_grp_{group_hash}_arm{arm.upper()}_*.pdf"
    matches = list(pdf_dir.glob(pattern))
    if matches:
        return matches[0]
    
    # Method 2: Try case-insensitive search for non-blinded format
    for pdf_file in pdf_dir.glob("*.pdf"):
        name_lower = pdf_file.name.lower()
        if name_lower.startswith(f"set_grp_{group_hash.lower()}_arm{arm.upper().lower()}_"):
            return pdf_file
    
    # Method 3: Try blinded format using surrogate_map
    if surrogate_map:
        key = (group_id, arm.upper())
        surrogate = surrogate_map.get(key)
        if surrogate:
            # Look for SET_{surrogate}_*.pdf pattern
            pattern = f"SET_{surrogate}_*.pdf"
            matches = list(pdf_dir.glob(pattern))
            if matches:
                return matches[0]
            
            # Try case-insensitive search
            for pdf_file in pdf_dir.glob("*.pdf"):
                name_lower = pdf_file.name.lower()
                if name_lower.startswith(f"set_{surrogate.lower()}_"):
                    return pdf_file
    
    return None


def organize_pdfs_by_reviewer_name(
    base_dir: Path,
    pdf_source_dir: Path,
    assignment_map_path: Path,
    reviewer_master_path: Path,
    groups_canonical_path: Path,
    selected_groups_path: Optional[Path] = None,
    run_tag: Optional[str] = None,
    dry_run: bool = False,
) -> None:
    """
    Organize PDFs by reviewer name.
    
    Creates folders like:
        by_reviewer_name/
            Reviewer_11/
                Q01.pdf
                Q02.pdf
                ...
    """
    print("=" * 70)
    print("Organizing PDFs by Reviewer Name")
    print("=" * 70)
    print(f"PDF source directory: {pdf_source_dir}")
    print(f"Assignment map: {assignment_map_path}")
    print(f"Reviewer master: {reviewer_master_path}")
    if dry_run:
        print("⚠️  DRY RUN MODE")
    print("=" * 70)
    
    # Load data
    print("\n>>> Loading data...")
    reviewers = load_reviewer_master(reviewer_master_path)
    assignments = load_assignment_map(assignment_map_path)
    groups_canonical = load_groups_canonical(groups_canonical_path)
    
    # Load placeholder -> group_key and placeholder -> group_id mappings
    placeholder_to_key = {}
    placeholder_to_id = {}
    if selected_groups_path and selected_groups_path.exists():
        placeholder_to_key, placeholder_to_id = load_selected_groups(selected_groups_path)
        print(f"  Loaded {len(placeholder_to_key)} placeholder->group_key mappings")
        print(f"  Loaded {len(placeholder_to_id)} placeholder->group_id mappings")
    else:
        # Try to build from S1 outputs or other sources
        arms = ["A", "B", "C", "D", "E", "F"]
        placeholder_to_key = build_placeholder_to_group_key_mapping(
            base_dir, run_tag, arms, groups_canonical
        )
        if not placeholder_to_key:
            print("  ⚠️  Could not build placeholder mapping. Trying alternative methods...")
    
    # Load surrogate map for blinded PDF support
    surrogate_map = {}
    surrogate_map_path = base_dir / "0_Protocol" / "06_QA_and_Study" / "QA_Operations" / "surrogate_map_group_id.csv"
    if surrogate_map_path.exists():
        surrogate_map = load_surrogate_map_group_id(surrogate_map_path)
        print(f"  Loaded {len(surrogate_map)} surrogate mappings for blinded PDF support")
    else:
        # Try original surrogate_map.csv location
        original_surrogate_map_path = base_dir / "0_Protocol" / "06_QA_and_Study" / "QA_Operations" / "surrogate_map.csv"
        if original_surrogate_map_path.exists():
            print(f"  ⚠️  surrogate_map_group_id.csv not found, using surrogate_map.csv (may need conversion)")
    
    # Create output directory
    output_dir = base_dir / "6_Distributions" / "QA_Packets" / "by_reviewer_name"
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Organize by reviewer
    reviewer_pdfs = {}
    missing_pdfs = []
    missing_mappings = []
    
    print("\n>>> Processing assignments...")
    for assignment in assignments:
        reviewer_id = assignment["reviewer_id"]
        local_qid = assignment["local_qid"]
        placeholder_group_id = assignment["group_id"]  # e.g., "group_02"
        arm = assignment["arm_id"]
        
        # Map placeholder to actual group_id
        actual_group_id = None
        
        # Method 1: Use selected_18_groups.json mapping (preferred - has group_id directly)
        if placeholder_group_id in placeholder_to_id:
            actual_group_id = placeholder_to_id[placeholder_group_id]
        
        # Method 2: Extract from set_id if available
        # set_id format: "set_group_02_C" -> extract "group_02"
        set_id = assignment.get("set_id", "")
        if not actual_group_id and set_id:
            # Try to extract group number from set_id
            match = re.search(r"group_(\d+)", set_id)
            if match:
                group_num = match.group(1)
                placeholder_from_set = f"group_{int(group_num):02d}"
                if placeholder_from_set in placeholder_to_id:
                    actual_group_id = placeholder_to_id[placeholder_from_set]
        
        # Method 3: If placeholder_group_id is already a real group_id (like "grp_xxx")
        if not actual_group_id and placeholder_group_id.startswith("grp_"):
            actual_group_id = placeholder_group_id
        
        # Method 4: Try to get group_id from groups_canonical using group_key
        if not actual_group_id:
            group_key = None
            if placeholder_group_id in placeholder_to_key:
                group_key = placeholder_to_key[placeholder_group_id]
            
            if group_key:
                # Find group_id from groups_canonical by group_key
                for gid, gkey in groups_canonical.items():
                    if gkey == group_key:
                        actual_group_id = gid
                        break
        
        if not actual_group_id:
            missing_mappings.append((reviewer_id, local_qid, placeholder_group_id, arm))
            continue
        
        # Find PDF using group_id (with surrogate map support for blinded PDFs)
        pdf_path = find_pdf_by_group_id_and_arm(pdf_source_dir, actual_group_id, arm, surrogate_map)
        
        if not pdf_path:
            missing_pdfs.append((reviewer_id, local_qid, actual_group_id, arm))
            continue
        
        # Add to reviewer's list
        if reviewer_id not in reviewer_pdfs:
            reviewer_pdfs[reviewer_id] = []
        
        reviewer_pdfs[reviewer_id].append((local_qid, pdf_path))
    
    # Sort by local_qid
    for reviewer_id in reviewer_pdfs:
        reviewer_pdfs[reviewer_id].sort(key=lambda x: x[0])
    
    # Create folders and copy PDFs
    print("\n>>> Organizing PDFs...")
    for reviewer_id, pdfs in reviewer_pdfs.items():
        reviewer_info = reviewers.get(reviewer_id, {})
        reviewer_name = reviewer_info.get("name", reviewer_id)
        
        # Create folder (sanitize name for filesystem)
        # Remove or replace characters that might cause issues
        safe_name = reviewer_name.replace("/", "_").replace("\\", "_")
        reviewer_folder = output_dir / safe_name
        
        if not dry_run:
            reviewer_folder.mkdir(parents=True, exist_ok=True)
        
        print(f"\n  {reviewer_name} ({reviewer_id}): {len(pdfs)} PDFs")
        for local_qid, pdf_path in pdfs:
            dest_path = reviewer_folder / f"{local_qid}.pdf"
            if not dry_run:
                shutil.copy2(pdf_path, dest_path)
            print(f"    {local_qid}: {pdf_path.name} -> {dest_path.name}")
    
    # Report missing items
    if missing_mappings:
        print(f"\n⚠️  {len(missing_mappings)} assignments with missing group_key mappings:")
        for reviewer_id, local_qid, placeholder_group_id, arm in missing_mappings[:10]:
            print(f"    {reviewer_id} {local_qid}: {placeholder_group_id} arm{arm}")
        if len(missing_mappings) > 10:
            print(f"    ... and {len(missing_mappings) - 10} more")
    
    if missing_pdfs:
        print(f"\n⚠️  {len(missing_pdfs)} assignments with missing PDF files:")
        for reviewer_id, local_qid, group_key, arm in missing_pdfs[:10]:
            print(f"    {reviewer_id} {local_qid}: {group_key} arm{arm}")
        if len(missing_pdfs) > 10:
            print(f"    ... and {len(missing_pdfs) - 10} more")
    
    print("\n" + "=" * 70)
    print("✅ Organization Complete")
    print("=" * 70)
    print(f"Reviewers organized: {len(reviewer_pdfs)}")
    print(f"Total PDFs organized: {sum(len(pdfs) for pdfs in reviewer_pdfs.values())}")
    print(f"Output directory: {output_dir}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Organize QA PDFs by reviewer name",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument(
        "--pdf_source_dir",
        type=str,
        default="6_Distributions/QA_Packets/S0_final",
        help="Directory containing source PDF files",
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
        "--groups_canonical",
        type=str,
        default="2_Data/metadata/groups_canonical.csv",
        help="Path to groups_canonical.csv",
    )
    parser.add_argument(
        "--selected_groups",
        type=str,
        help="Path to selected_18_groups.json (optional, will try to infer if not provided)",
    )
    parser.add_argument(
        "--run_tag",
        type=str,
        help="Run tag to find S1 outputs (optional, will try to infer if not provided)",
    )
    parser.add_argument("--dry_run", action="store_true", help="Dry run (no actual operations)")
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    pdf_source_dir = base_dir / args.pdf_source_dir
    assignment_map_path = base_dir / args.assignment_map
    reviewer_master_path = base_dir / args.reviewer_master
    groups_canonical_path = base_dir / args.groups_canonical
    
    selected_groups_path = None
    if args.selected_groups:
        selected_groups_path = base_dir / args.selected_groups
    else:
        # Try run_tag-specific location first (most accurate)
        if args.run_tag:
            run_tag_path = base_dir / "2_Data" / "metadata" / "generated" / args.run_tag / "selected_18_groups.json"
            if run_tag_path.exists():
                selected_groups_path = run_tag_path
                print(f"  Found selected_18_groups.json in run_tag directory: {run_tag_path}")
        
        # Fallback to common locations if run_tag path not found
        if not selected_groups_path:
            common_paths = [
                base_dir / "2_Data" / "metadata" / "generated" / "S0_QA_20251220" / "selected_18_groups.json",
                base_dir / "2_Data" / "metadata" / "generated" / "selected_18_groups.json",
            ]
            for path in common_paths:
                if path.exists():
                    selected_groups_path = path
                    print(f"  Found selected_18_groups.json in common location: {path}")
                    break
    
    if not pdf_source_dir.exists():
        print(f"❌ PDF source directory not found: {pdf_source_dir}")
        sys.exit(1)
    
    organize_pdfs_by_reviewer_name(
        base_dir,
        pdf_source_dir,
        assignment_map_path,
        reviewer_master_path,
        groups_canonical_path,
        selected_groups_path,
        args.run_tag,
        args.dry_run,
    )


if __name__ == "__main__":
    main()


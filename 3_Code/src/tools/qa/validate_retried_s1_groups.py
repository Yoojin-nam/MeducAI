#!/usr/bin/env python3
"""
Validate S1 retried groups to check if structure is intact.

This script:
1. Identifies groups that were retried (by comparing with original selected groups)
2. Validates only the retried groups using S1 Gate validation
3. Reports any structural issues

Usage:
    python 3_Code/src/tools/qa/validate_retried_s1_groups.py --run_tag S0_QA_final_time --arms A B
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.s1_table_spec import S1_EXPECTED_COLS, S1_HEADERS_BY_CATEGORY, sanitize_cell_text


def load_selected_groups(base_dir: Path, run_tag: str) -> List[Dict[str, str]]:
    """Load selected groups from the run."""
    selected_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / "selected_18_groups.json"
    if not selected_path.exists():
        raise FileNotFoundError(f"Selected groups file not found: {selected_path}")
    
    with open(selected_path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_retried_groups(base_dir: Path, run_tag: str, arm: str) -> Set[str]:
    """
    Find groups that were likely retried by checking modification times.
    
    This is a heuristic: groups that exist in stage1_struct but have recent
    modification times compared to the original run might be retried.
    
    For now, we'll validate all groups in stage1_struct and report issues.
    """
    stage1_struct_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"stage1_struct__arm{arm}.jsonl"
    
    group_ids = set()
    if stage1_struct_path.exists():
        with open(stage1_struct_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    group_id = record.get("group_id", "").strip()
                    if group_id:
                        group_ids.add(group_id)
                except json.JSONDecodeError:
                    continue
    
    return group_ids


def validate_s1_gate(base_dir: Path, run_tag: str, arm: str) -> tuple[bool, str]:
    """Run S1 Gate validation for an arm."""
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "tools" / "qa" / "validate_stage1_struct.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=base_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, f"Exception running validation: {e}"


def validate_specific_groups(
    base_dir: Path,
    run_tag: str,
    arm: str,
    group_ids: Set[str],
) -> Dict[str, tuple[bool, str]]:
    """
    Validate specific groups by reading stage1_struct and checking each group.
    
    Returns dict mapping group_id -> (is_valid, error_message)
    """
    stage1_struct_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"stage1_struct__arm{arm}.jsonl"
    
    if not stage1_struct_path.exists():
        return {gid: (False, "stage1_struct file not found") for gid in group_ids}
    
    results = {}
    
    # Read all records
    all_records = []
    with open(stage1_struct_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                all_records.append(record)
            except json.JSONDecodeError as e:
                # This is a structural error
                for gid in group_ids:
                    if gid not in results:
                        results[gid] = (False, f"JSON parse error in file: {e}")
                continue
    
    # Validate each target group
    for group_id in group_ids:
        # Find record for this group
        record = None
        for rec in all_records:
            if rec.get("group_id", "").strip() == group_id:
                record = rec
                break
        
        if not record:
            results[group_id] = (False, "Group not found in stage1_struct")
            continue
        
        # Basic schema validation
        errors = []
        
        # Check schema_version
        schema_version = record.get("schema_version", "").strip()
        if schema_version != "S1_STRUCT_v1.3":
            errors.append(f"Invalid schema_version: {schema_version} (expected S1_STRUCT_v1.3)")
        
        # Check required fields
        if not record.get("group_id", "").strip():
            errors.append("Missing or empty group_id")
        
        if not record.get("group_path", "").strip():
            errors.append("Missing or empty group_path")
        
        if not isinstance(record.get("objective_bullets"), list) or len(record.get("objective_bullets", [])) == 0:
            errors.append("Missing, invalid, or empty objective_bullets")
        
        visual_type = record.get("visual_type_category", "").strip()
        # Removed unused categories: Comparison, Algorithm, Classification, Sign_Collection (v11)
        allowed_types = {
            "Anatomy_Map", "Pathology_Pattern", "Pattern_Collection", "Physiology_Process",
            "Equipment", "QC", "General"
        }
        if visual_type not in allowed_types:
            errors.append(f"Invalid visual_type_category: {visual_type}")
        
        mt = record.get("master_table_markdown_kr")
        if not isinstance(mt, str):
            errors.append("Missing or invalid master_table_markdown_kr")
        else:
            lines = [ln.strip() for ln in str(mt).splitlines() if ln.strip()]
            header = []
            if len(lines) >= 2 and "|" in lines[0]:
                header = [c.strip() for c in lines[0].split("|") if c.strip()]
            if header and len(header) != S1_EXPECTED_COLS:
                errors.append(f"Table header column count {len(header)} != {S1_EXPECTED_COLS}")
            if visual_type in S1_HEADERS_BY_CATEGORY and header and header != S1_HEADERS_BY_CATEGORY[visual_type]:
                errors.append(f"Table header mismatch for {visual_type}")
            for idx, line in enumerate(lines[2:], start=1):
                if "|" not in line:
                    continue
                cells = [sanitize_cell_text(c.strip()) for c in line.split("|") if c.strip()]
                if len(cells) != S1_EXPECTED_COLS:
                    errors.append(f"Row {idx} column count {len(cells)} != {S1_EXPECTED_COLS}")
            if "<br" in mt.lower():
                errors.append("master_table_markdown_kr contains <br>, which is forbidden")
        
        entity_list = record.get("entity_list", [])
        if not isinstance(entity_list, list) or len(entity_list) == 0:
            errors.append("Missing, invalid, or empty entity_list")
        else:
            # Check entity structure
            entity_ids = set()
            for i, entity in enumerate(entity_list):
                if not isinstance(entity, dict):
                    errors.append(f"Entity {i} is not an object")
                    continue
                
                entity_id = entity.get("entity_id", "").strip()
                entity_name = entity.get("entity_name", "").strip()
                
                if not entity_id:
                    errors.append(f"Entity {i} missing entity_id")
                if not entity_name:
                    errors.append(f"Entity {i} missing entity_name")
                if entity_id in entity_ids:
                    errors.append(f"Duplicate entity_id: {entity_id}")
                entity_ids.add(entity_id)
        
        # Check integrity
        integrity = record.get("integrity", {})
        if not isinstance(integrity, dict):
            errors.append("Missing or invalid integrity object")
        else:
            entity_count = integrity.get("entity_count")
            if entity_count != len(entity_list):
                errors.append(f"integrity.entity_count ({entity_count}) != len(entity_list) ({len(entity_list)})")
            
            objective_count = integrity.get("objective_count")
            if objective_count != len(record.get("objective_bullets", [])):
                errors.append(f"integrity.objective_count mismatch")
        
        if errors:
            results[group_id] = (False, "; ".join(errors))
        else:
            results[group_id] = (True, "OK")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Validate S1 retried groups structure"
    )
    parser.add_argument(
        "--base_dir",
        type=str,
        default=".",
        help="Base directory (default: current directory)"
    )
    parser.add_argument(
        "--run_tag",
        type=str,
        required=True,
        help="Run tag (e.g., S0_QA_final_time)"
    )
    parser.add_argument(
        "--arms",
        type=str,
        nargs="+",
        default=["A", "B", "C", "D", "E", "F"],
        help="Arms to validate (default: all arms A-F)"
    )
    parser.add_argument(
        "--group_ids",
        type=str,
        nargs="+",
        default=None,
        help="Specific group IDs to validate (if not provided, validates all groups in stage1_struct)"
    )
    
    args = parser.parse_args()
    base_dir = Path(args.base_dir).resolve()
    
    print("=" * 70)
    print("S1 Retried Groups Validation")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {args.run_tag}")
    print(f"Arms: {', '.join(args.arms)}")
    print("=" * 70)
    
    all_valid = True
    
    for arm in args.arms:
        print(f"\n[Arm {arm}] Validating...")
        
        # Determine which groups to validate
        if args.group_ids:
            target_group_ids = set(args.group_ids)
        else:
            # Validate all groups in stage1_struct
            target_group_ids = find_retried_groups(base_dir, args.run_tag, arm)
        
        if not target_group_ids:
            print(f"  ⚠️  No groups found to validate")
            continue
        
        print(f"  Validating {len(target_group_ids)} groups...")
        
        # Run full S1 Gate validation first
        print(f"  Running S1 Gate validation...")
        gate_valid, gate_output = validate_s1_gate(base_dir, args.run_tag, arm)
        
        if gate_valid:
            print(f"  ✅ S1 Gate validation: PASS")
        else:
            print(f"  ❌ S1 Gate validation: FAIL")
            print(f"  Error details:")
            for line in gate_output.split("\n")[:20]:  # Show first 20 lines
                if line.strip():
                    print(f"    {line}")
            all_valid = False
        
        # Validate specific groups in detail
        print(f"  Validating individual groups...")
        group_results = validate_specific_groups(base_dir, args.run_tag, arm, target_group_ids)
        
        valid_count = 0
        invalid_count = 0
        
        for group_id, (is_valid, message) in sorted(group_results.items()):
            if is_valid:
                print(f"    ✅ {group_id}: {message}")
                valid_count += 1
            else:
                print(f"    ❌ {group_id}: {message}")
                invalid_count += 1
                all_valid = False
        
        print(f"  Summary: {valid_count} valid, {invalid_count} invalid")
    
    print("\n" + "=" * 70)
    if all_valid:
        print("✅ All validations PASSED")
    else:
        print("❌ Some validations FAILED")
    print("=" * 70)
    
    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())


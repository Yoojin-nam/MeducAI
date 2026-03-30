#!/usr/bin/env python3
"""
S1R (Table Regeneration) Input Generator

Extracts groups from S5 validation where table_regeneration_trigger_score < threshold,
loads original S1 table (entity list, column structure), converts S5 issues to positive
instructions, and generates S1R input specs.

Output: s1_regen_input__arm{ARM}.jsonl
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_s5_validation(path: Path) -> List[Dict[str, Any]]:
    """Load S5 validation records from JSONL."""
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_s1_structs(path: Path) -> Dict[str, Dict[str, Any]]:
    """Load S1 struct records indexed by group_id."""
    structs = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                rec = json.loads(line)
                gid = rec.get("group_id")
                if gid:
                    structs[gid] = rec
    return structs


def extract_entity_names_from_list(entity_list: List[Any]) -> List[str]:
    """Extract entity names from entity_list field."""
    names = []
    for item in entity_list:
        if isinstance(item, dict):
            name = item.get("entity_name") or item.get("name") or ""
            if name:
                names.append(str(name).strip())
        elif isinstance(item, str):
            names.append(item.strip())
    return names


def extract_column_names_from_table(master_table_md: str) -> List[str]:
    """
    Extract column names from master table markdown.
    Returns list of column names from the header row.
    """
    if not master_table_md:
        return []
    
    lines = master_table_md.strip().split('\n')
    if len(lines) < 2:
        return []
    
    # First line should be header row
    header_line = lines[0].strip()
    if not header_line.startswith('|'):
        return []
    
    # Parse column names
    columns = [col.strip() for col in header_line.strip('|').split('|')]
    return [col for col in columns if col]  # Filter empty strings


def convert_issues_to_positive_instruction(issues: List[Dict[str, Any]]) -> str:
    """
    Convert S5 issues to positive instruction for S1R.
    
    Returns a formatted positive instruction that tells the model what to improve.
    """
    if not issues:
        return ""
    
    instructions = []
    instructions.append("## Quality Improvement Instructions")
    instructions.append("")
    instructions.append("Based on validation feedback, please improve the table content by addressing the following:")
    instructions.append("")
    
    # Group issues by type
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for issue in issues:
        issue_type = issue.get("type", "general")
        if issue_type not in by_type:
            by_type[issue_type] = []
        by_type[issue_type].append(issue)
    
    # Format by type
    for issue_type, type_issues in by_type.items():
        instructions.append(f"### {issue_type.replace('_', ' ').title()}")
        instructions.append("")
        
        for i, issue in enumerate(type_issues, 1):
            entity_name = issue.get("entity_name", "")
            description = issue.get("description", "")
            suggested_fix = issue.get("suggested_fix", "")
            severity = issue.get("severity", "minor")
            
            instructions.append(f"{i}. **{entity_name}** ({severity})")
            if description:
                instructions.append(f"   - Issue: {description}")
            if suggested_fix:
                instructions.append(f"   - Fix: {suggested_fix}")
            instructions.append("")
    
    instructions.append("**IMPORTANT**: Preserve the exact entity list and column structure. Only improve the cell content.")
    instructions.append("")
    
    return "\n".join(instructions)


def generate_s1r_input_specs(
    s5_validation_path: Path,
    stage1_struct_path: Path,
    threshold: float,
    output_path: Path,
) -> int:
    """
    Generate S1R input specs from S5 validation results.
    
    Returns: number of specs generated
    """
    print(f"Loading S5 validation from: {s5_validation_path}")
    s5_records = load_s5_validation(s5_validation_path)
    print(f"Loaded {len(s5_records)} S5 validation records")
    
    print(f"Loading S1 structs from: {stage1_struct_path}")
    s1_structs = load_s1_structs(stage1_struct_path)
    print(f"Loaded {len(s1_structs)} S1 struct records")
    
    specs = []
    skipped_no_s1 = 0
    skipped_no_issues = 0
    
    for s5_rec in s5_records:
        group_id = s5_rec.get("group_id")
        if not group_id:
            continue
        
        # Check table_regeneration_trigger_score
        s1_validation = s5_rec.get("s1_table_validation", {})
        score = s1_validation.get("table_regeneration_trigger_score")
        
        if score is None or score >= threshold:
            continue
        
        # Get S1 struct
        s1_struct = s1_structs.get(group_id)
        if not s1_struct:
            print(f"  Warning: No S1 struct found for group_id={group_id}, skipping")
            skipped_no_s1 += 1
            continue
        
        # Extract entity list and column structure
        entity_list_raw = s1_struct.get("entity_list", [])
        entity_names = extract_entity_names_from_list(entity_list_raw)
        
        master_table_md = s1_struct.get("master_table_markdown_kr", "")
        column_names = extract_column_names_from_table(master_table_md)
        
        # Get issues
        issues = s1_validation.get("issues", [])
        if not issues:
            print(f"  Warning: No issues found for group_id={group_id} (score={score}), skipping")
            skipped_no_issues += 1
            continue
        
        # Convert issues to positive instruction
        positive_instruction = convert_issues_to_positive_instruction(issues)
        
        # Build spec
        spec = {
            "group_id": group_id,
            "group_key": s1_struct.get("group_key", ""),
            "table_regeneration_trigger_score": score,
            "original_entity_count": len(entity_names),
            "original_entity_list": entity_names,
            "original_column_names": column_names,
            "s5_issues": issues,
            "positive_instruction": positive_instruction,
            "preserve_structure": True,
            "regen_mode": "table_content_only",
        }
        
        specs.append(spec)
        print(f"  ✓ {group_id}: score={score}, entities={len(entity_names)}, columns={len(column_names)}, issues={len(issues)}")
    
    # Write specs
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for spec in specs:
            f.write(json.dumps(spec, ensure_ascii=False) + '\n')
    
    print(f"\n✅ Generated {len(specs)} S1R input specs")
    print(f"   Output: {output_path}")
    if skipped_no_s1 > 0:
        print(f"   Skipped {skipped_no_s1} groups (no S1 struct)")
    if skipped_no_issues > 0:
        print(f"   Skipped {skipped_no_issues} groups (no issues despite low score)")
    
    return len(specs)


def main():
    parser = argparse.ArgumentParser(
        description="Generate S1R (table regeneration) input specs from S5 validation results"
    )
    parser.add_argument("--base_dir", default=".", help="Base directory (default: .)")
    parser.add_argument("--run_tag", required=True, help="Run tag (e.g., FINAL_DISTRIBUTION)")
    parser.add_argument("--arm", required=True, help="Arm (e.g., G)")
    parser.add_argument("--threshold", type=float, default=80.0, 
                       help="Score threshold for regeneration (default: 80.0)")
    parser.add_argument("--output_name", default=None,
                       help="Output filename (default: s1_regen_input__arm{ARM}.jsonl)")
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    metadata_dir = base_dir / "2_Data" / "metadata" / "generated" / args.run_tag
    
    # Input paths
    s5_validation_path = metadata_dir / f"s5_validation__arm{args.arm}.jsonl"
    stage1_struct_path = metadata_dir / f"stage1_struct__arm{args.arm}.jsonl"
    
    # Check inputs
    if not s5_validation_path.exists():
        print(f"❌ Error: S5 validation file not found: {s5_validation_path}", file=sys.stderr)
        sys.exit(1)
    
    if not stage1_struct_path.exists():
        print(f"❌ Error: S1 struct file not found: {stage1_struct_path}", file=sys.stderr)
        sys.exit(1)
    
    # Output path
    if args.output_name:
        output_path = metadata_dir / args.output_name
    else:
        output_path = metadata_dir / f"s1_regen_input__arm{args.arm}.jsonl"
    
    # Generate
    count = generate_s1r_input_specs(
        s5_validation_path=s5_validation_path,
        stage1_struct_path=stage1_struct_path,
        threshold=args.threshold,
        output_path=output_path,
    )
    
    if count == 0:
        print("\n⚠️  Warning: No specs generated. Check threshold or S5 validation results.", file=sys.stderr)
        sys.exit(1)
    
    print("\n✅ S1R input generation complete")


if __name__ == "__main__":
    main()

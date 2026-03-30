#!/usr/bin/env python3
"""
Build Patch Backlog from S5 Validation JSONL

Extracts issues from s5_validation__arm{arm}.jsonl and creates a structured
patch backlog grouped by issue_code and recommended_fix_target.

Usage:
    python3 build_patch_backlog.py \
        --base_dir . \
        --run_tag <RUN_TAG> \
        --arm <ARM> \
        --output <OUTPUT_PATH>
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any


def load_s5_validation(base_dir: Path, run_tag: str, arm: str) -> List[Dict[str, Any]]:
    """Load S5 validation JSONL file."""
    validation_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"s5_validation__arm{arm}.jsonl"
    
    if not validation_path.exists():
        print(f"Error: S5 validation file not found: {validation_path}", file=sys.stderr)
        sys.exit(1)
    
    records = []
    with open(validation_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse JSON line: {e}", file=sys.stderr)
    
    return records


def extract_issues(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract issues grouped by recommended_fix_target.
    
    Returns:
        Dict mapping recommended_fix_target to list of issues
    """
    issues_by_target = defaultdict(list)
    
    for record in records:
        group_id = record.get("group_id", "unknown")
        
        # S1 table issues
        s1_validation = record.get("s1_table_validation", {})
        s1_blocking = s1_validation.get("blocking_error", False)
        s1_issues = s1_validation.get("issues", [])
        
        for issue in s1_issues:
            issue_code = issue.get("issue_code", "UNKNOWN")
            fix_target = issue.get("recommended_fix_target", "S1_SYSTEM")
            patch_hint = issue.get("prompt_patch_hint", "")
            
            issues_by_target[fix_target].append({
                "issue_code": issue_code,
                "severity": issue.get("severity", "unknown"),
                "type": issue.get("type", "unknown"),
                "description": issue.get("description", ""),
                "group_id": group_id,
                "prompt_patch_hint": patch_hint,
                "affected_stage": "S1",
                "blocking": s1_blocking,
            })
        
        # S2 cards issues
        s2_validation = record.get("s2_cards_validation", {})
        s2_blocking = s2_validation.get("blocking_error", False)
        s2_issues = s2_validation.get("issues", [])
        
        for issue in s2_issues:
            issue_code = issue.get("issue_code", "UNKNOWN")
            fix_target = issue.get("recommended_fix_target", "S2_SYSTEM")
            patch_hint = issue.get("prompt_patch_hint", "")
            
            issues_by_target[fix_target].append({
                "issue_code": issue_code,
                "severity": issue.get("severity", "unknown"),
                "type": issue.get("type", "unknown"),
                "description": issue.get("description", ""),
                "group_id": group_id,
                "prompt_patch_hint": patch_hint,
                "affected_stage": "S2",
                "blocking": s2_blocking,
            })
    
    return dict(issues_by_target)


def aggregate_by_issue_code(issues: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Aggregate issues by issue_code."""
    aggregated: Dict[str, Dict[str, Any]] = {}
    
    for issue in issues:
        issue_code = issue.get("issue_code", "UNKNOWN")
        
        if issue_code not in aggregated:
            aggregated[issue_code] = {
                "count": 0,
                "examples": [],
                "prompt_patch_hints": [],
                "blocking_count": 0,
                "severity_distribution": defaultdict(int),
            }
        
        agg = aggregated[issue_code]
        
        agg["count"] += 1
        if issue.get("blocking"):
            agg["blocking_count"] += 1
        agg["severity_distribution"][issue.get("severity", "unknown")] += 1
        
        # Collect examples (max 3)
        if len(agg["examples"]) < 3:
            example = {
                "group_id": issue.get("group_id"),
                "description": issue.get("description", "")[:200],
            }
            agg["examples"].append(example)
        
        # Collect unique patch hints
        patch_hint = issue.get("prompt_patch_hint", "").strip()
        if patch_hint and patch_hint not in agg["prompt_patch_hints"]:
            agg["prompt_patch_hints"].append(patch_hint)
    
    # Convert defaultdict to dict
    result: Dict[str, Dict[str, Any]] = {}
    for k, v in aggregated.items():
        result[k] = {
            "count": v["count"],
            "examples": v["examples"],
            "prompt_patch_hints": v["prompt_patch_hints"],
            "blocking_count": v["blocking_count"],
            "severity_distribution": dict(v["severity_distribution"]),
        }
    return result


def build_patch_backlog(base_dir: Path, run_tag: str, arm: str) -> Dict[str, Any]:
    """Build structured patch backlog."""
    records = load_s5_validation(base_dir, run_tag, arm)
    
    # Extract issues by target
    issues_by_target = extract_issues(records)
    
    # Aggregate by issue_code for each target
    backlog = {
        "run_tag": run_tag,
        "arm": arm,
        "total_groups": len(records),
        "issues_by_target": {},
        "priority_ranking": {
            "P0": [],  # blocking issues
            "P1": [],  # high-frequency non-blocking
        },
    }
    
    for target, issues in issues_by_target.items():
        aggregated = aggregate_by_issue_code(issues)
        
        backlog["issues_by_target"][target] = []
        for issue_code, agg_data in sorted(aggregated.items(), key=lambda x: x[1]["count"], reverse=True):
            entry = {
                "issue_code": issue_code,
                "count": agg_data["count"],
                "blocking_count": agg_data["blocking_count"],
                "severity_distribution": dict(agg_data["severity_distribution"]),
                "examples": agg_data["examples"],
                "prompt_patch_hints": agg_data["prompt_patch_hints"][:3],  # Top 3
            }
            backlog["issues_by_target"][target].append(entry)
            
            # Priority ranking
            if agg_data["blocking_count"] > 0:
                backlog["priority_ranking"]["P0"].append({
                    "target": target,
                    "issue_code": issue_code,
                    "count": agg_data["count"],
                })
            elif agg_data["count"] >= 3:  # High frequency threshold
                backlog["priority_ranking"]["P1"].append({
                    "target": target,
                    "issue_code": issue_code,
                    "count": agg_data["count"],
                })
    
    return backlog


def main():
    parser = argparse.ArgumentParser(description="Build patch backlog from S5 validation")
    parser.add_argument("--base_dir", type=str, required=True, help="Base directory")
    parser.add_argument("--run_tag", type=str, required=True, help="Run tag")
    parser.add_argument("--arm", type=str, required=True, help="Arm identifier")
    parser.add_argument("--output", type=str, help="Output JSON path (default: auto-generated)")
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    run_tag = args.run_tag
    arm = args.arm
    
    # Build backlog
    backlog = build_patch_backlog(base_dir, run_tag, arm)
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / "prompt_refinement" / f"patch_backlog__{run_tag}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(backlog, f, ensure_ascii=False, indent=2)
    
    print(f"Patch backlog written to: {output_path}")
    print(f"Total targets: {len(backlog['issues_by_target'])}")
    print(f"P0 (blocking): {len(backlog['priority_ranking']['P0'])}")
    print(f"P1 (high-frequency): {len(backlog['priority_ranking']['P1'])}")


if __name__ == "__main__":
    main()


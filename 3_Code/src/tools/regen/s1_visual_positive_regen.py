#!/usr/bin/env python3
"""
S6 Input Generator for S1 Table Visual Regeneration

Purpose:
- Extract S1 table visuals from S5 validation with low scores (< threshold)
- Convert S5 visual issues into positive instructions for S6
- Generate enhanced S3 specs for visual regeneration

Based on positive_regen_runner.py but focused on S1_TABLE_VISUAL instead of S2 cards.

Usage:
    python3 s1_visual_positive_regen.py \
        --base_dir . \
        --run_tag FINAL_DISTRIBUTION \
        --arm G \
        --threshold 80.0 \
        --output s3_image_spec__armG__s1_visual_regen.jsonl
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# =========================
# Score Calculation
# =========================

def calculate_table_visual_score(visual_validation: Dict[str, Any]) -> float:
    """
    Calculate visual quality score (0-100, higher = better quality).
    
    This is used to determine if a visual needs regeneration.
    Score < 80 triggers regeneration.
    
    Scoring:
    - blocking_error: If True, return 30.0 (hard fail)
    - anatomical_accuracy: 40 points (0.0/0.5/1.0 scaled to 0-40)
    - prompt_compliance: 30 points (0.0/0.5/1.0 scaled to 0-30)
    - information_clarity: 20 points (1-5 Likert scaled to 0-20)
    - table_visual_consistency: 10 points (0.0/0.5/1.0 scaled to 0-10)
    
    Args:
        visual_validation: Visual validation record from S5
        
    Returns:
        Score from 0-100 (higher = better)
    """
    # Hard fail on blocking error
    if visual_validation.get("blocking_error") is True:
        return 30.0
    
    # Anatomical accuracy (40 points)
    aa_raw = visual_validation.get("anatomical_accuracy")
    if aa_raw is None:
        aa_score = 40.0  # Default to perfect if missing
    else:
        aa = float(aa_raw)
        if aa == 0.0:
            return 30.0  # Hard fail
        aa_score = max(0.0, min(1.0, aa)) * 40.0
    
    # Prompt compliance (30 points)
    pc_raw = visual_validation.get("prompt_compliance")
    if pc_raw is None:
        pc_score = 30.0  # Default to perfect if missing
    else:
        pc = float(pc_raw)
        pc_score = max(0.0, min(1.0, pc)) * 30.0
    
    # Information clarity (20 points, 1-5 Likert)
    ic_raw = visual_validation.get("information_clarity")
    if ic_raw is None or ic_raw <= 0:
        ic = 5.0  # Default to perfect if missing
    else:
        ic = float(ic_raw)
    ic_score = (max(1.0, min(5.0, ic)) / 5.0) * 20.0
    
    # Table visual consistency (10 points)
    tvc_raw = visual_validation.get("table_visual_consistency")
    if tvc_raw is None:
        tvc_score = 10.0  # Default to perfect if missing
    else:
        tvc = float(tvc_raw)
        tvc_score = max(0.0, min(1.0, tvc)) * 10.0
    
    total = aa_score + pc_score + ic_score + tvc_score
    return round(max(0.0, min(100.0, total)), 2)


# =========================
# Data Loading Utilities
# =========================

def load_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """Load a JSONL file and return list of records."""
    records = []
    if not file_path.exists():
        return records
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                records.append(record)
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse JSON line in {file_path}: {e}", file=sys.stderr)
                continue
    
    return records


def write_jsonl(file_path: Path, records: List[Dict[str, Any]]) -> None:
    """Write records to a JSONL file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        for record in records:
            json_line = json.dumps(record, ensure_ascii=False)
            f.write(json_line + "\n")


# =========================
# Regen Target Extraction
# =========================

def extract_visual_regen_targets(
    s5_results: List[Dict[str, Any]],
    threshold: float = 80.0,
) -> List[Dict[str, Any]]:
    """
    Extract S1 table visuals that need regeneration based on calculated score.
    
    Args:
        s5_results: List of S5 validation records (one per group)
        threshold: Score threshold (default: 80.0, regen if < threshold)
        
    Returns:
        List of regen target dicts with:
            - group_id
            - cluster_id
            - score (calculated visual score)
            - issues (list of issue dicts from visual validation)
            - visual_validation (full validation record)
    """
    regen_targets = []
    
    for group_result in s5_results:
        group_id = str(group_result.get("group_id", "")).strip()
        if not group_id:
            continue
        
        # Extract table visual validations from s1_table_validation
        s1_table_validation = group_result.get("s1_table_validation", {})
        visual_validations = s1_table_validation.get("table_visual_validations", [])
        
        for visual in visual_validations:
            cluster_id = str(visual.get("cluster_id", "")).strip()
            
            if not cluster_id:
                continue
            
            # Calculate visual score
            visual_score = calculate_table_visual_score(visual)
            
            if visual_score >= threshold:
                # Score is above threshold, no regeneration needed
                continue
            
            # Extract issues
            issues = visual.get("issues", [])
            
            # If no issues but score is low, create a generic issue
            if not issues:
                print(f"[Warning] Visual {group_id}/{cluster_id} has low score ({visual_score:.1f}) but no issues. Adding generic issue.")
                issues = [{
                    "severity": "moderate",
                    "type": "quality_improvement",
                    "description": "Visual quality below threshold and requires regeneration.",
                    "recommended_fix_target": "S3_PROMPT",
                    "prompt_patch_hint": "Improve overall visual quality, clarity, and consistency with table content.",
                }]
            
            regen_targets.append({
                "group_id": group_id,
                "cluster_id": cluster_id,
                "score": visual_score,
                "issues": issues,
                "visual_validation": visual,
            })
    
    return regen_targets


# =========================
# S3 Spec Matching
# =========================

def find_s3_spec_for_visual(
    s3_specs: List[Dict[str, Any]],
    group_id: str,
    cluster_id: str,
) -> Optional[Dict[str, Any]]:
    """Find matching S3 spec for a given visual."""
    for spec in s3_specs:
        if (
            str(spec.get("group_id", "")).strip() == group_id
            and str(spec.get("cluster_id", "")).strip() == cluster_id
            and spec.get("spec_kind") == "S1_TABLE_VISUAL"
        ):
            return spec
    return None


# =========================
# Issue to Positive Instruction Conversion
# =========================

def convert_issues_to_positive_instructions(issues: List[Dict[str, Any]]) -> List[str]:
    """
    Convert S5 visual issues into positive instructions for S6.
    
    This is a simplified conversion that extracts prompt_patch_hint from issues.
    For more sophisticated conversion, S6 agent should be called.
    
    Args:
        issues: List of issue dicts from visual validation
        
    Returns:
        List of positive instruction strings
    """
    positive_instructions = []
    
    for issue in issues:
        # Extract prompt_patch_hint if available
        hint = str(issue.get("prompt_patch_hint", "")).strip()
        
        # If no hint, construct from description
        if not hint:
            description = str(issue.get("description", "")).strip()
            suggested_fix = str(issue.get("suggested_fix", "")).strip()
            
            if description:
                # Convert negative description to positive instruction
                # This is a simple heuristic; S6 agent would do this better
                hint = f"Ensure: {description}"
                if suggested_fix:
                    hint += f" ({suggested_fix})"
        
        if hint:
            positive_instructions.append(hint)
    
    return positive_instructions


# =========================
# Enhanced Spec Generation
# =========================

def generate_enhanced_specs(
    regen_targets: List[Dict[str, Any]],
    s3_specs: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    Generate enhanced S3 specs for visual regeneration.
    
    Args:
        regen_targets: List of visual regen targets
        s3_specs: List of original S3 specs
        
    Returns:
        Tuple of (enhanced_specs, success_count, error_count)
    """
    enhanced_specs = []
    success_count = 0
    error_count = 0
    
    for i, target in enumerate(regen_targets, 1):
        group_id = target["group_id"]
        cluster_id = target["cluster_id"]
        
        print(f"\n  [{i}/{len(regen_targets)}] {group_id}/{cluster_id} (score: {target['score']:.1f})")
        
        # Find S3 spec
        s3_spec = find_s3_spec_for_visual(s3_specs, group_id, cluster_id)
        
        if not s3_spec:
            print(f"    ❌ Error: S3 spec not found. Skipping.")
            error_count += 1
            continue
        
        print(f"    Found S3 spec (spec_kind: {s3_spec.get('spec_kind', '')})")
        
        # Convert issues to positive instructions
        positive_instructions = convert_issues_to_positive_instructions(target["issues"])
        
        if not positive_instructions:
            print(f"    ⚠️  Warning: No positive instructions generated from issues")
            # Continue anyway with original spec
            positive_instructions = ["Improve overall visual quality and consistency with table content."]
        
        print(f"    Generated {len(positive_instructions)} positive instruction(s):")
        for j, inst in enumerate(positive_instructions, 1):
            print(f"      {j}. {inst[:80]}{'...' if len(inst) > 80 else ''}")
        
        # Create enhanced spec
        enhanced_spec = s3_spec.copy()
        
        # Add positive instructions
        enhanced_spec["positive_instructions"] = positive_instructions
        
        # Add metadata
        enhanced_spec["_regen_metadata"] = {
            "regen_type": "S1_TABLE_VISUAL",
            "original_score": target["score"],
            "regen_reason": "low_visual_score",
            "s5_issues_count": len(target["issues"]),
        }
        
        # Combine positive instructions with original prompt
        original_prompt = enhanced_spec.get("prompt_en", "")
        instructions_text = "\n".join([f"- {inst}" for inst in positive_instructions])
        enhanced_prompt = f"{original_prompt}\n\nIMPROVEMENTS REQUIRED:\n{instructions_text}"
        
        enhanced_spec["prompt_en_enhanced"] = enhanced_prompt
        enhanced_spec["prompt_en"] = enhanced_prompt  # Overwrite for S4 compatibility
        
        enhanced_specs.append(enhanced_spec)
        success_count += 1
    
    return enhanced_specs, success_count, error_count


# =========================
# Main Pipeline
# =========================

def run_s1_visual_positive_regen(
    base_dir: Path,
    run_tag: str,
    arm: str,
    threshold: float = 80.0,
    output_filename: Optional[str] = None,
) -> int:
    """
    S6 input generator for S1 table visual regeneration.
    
    Args:
        base_dir: Project base directory
        run_tag: Run tag (e.g., FINAL_DISTRIBUTION)
        arm: Arm identifier (e.g., G)
        threshold: Visual score threshold for regeneration (default: 80.0)
        output_filename: Output filename (default: s3_image_spec__arm{arm}__s1_visual_regen.jsonl)
        
    Returns:
        Exit code (0 = success, non-zero = error)
    """
    print("="*80)
    print("S6 Input Generator - S1 Table Visual Regeneration")
    print("="*80)
    print(f"RUN_TAG: {run_tag}")
    print(f"ARM: {arm}")
    print(f"Threshold: {threshold}")
    print()
    
    # Resolve paths
    base_dir = base_dir.resolve()
    data_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    
    s5_path = data_dir / f"s5_validation__arm{arm}.jsonl"
    s3_spec_path = data_dir / f"s3_image_spec__arm{arm}.jsonl"
    
    if output_filename is None:
        output_filename = f"s3_image_spec__arm{arm}__s1_visual_regen.jsonl"
    
    output_path = data_dir / output_filename
    
    # 1. Load S5 validation results
    print("[Step 1] Loading S5 validation results...")
    if not s5_path.exists():
        print(f"Error: S5 validation file not found: {s5_path}", file=sys.stderr)
        return 1
    
    s5_results = load_jsonl(s5_path)
    print(f"  Loaded {len(s5_results)} group(s) from S5 validation")
    
    # 2. Extract regen targets
    print(f"\n[Step 2] Filtering visuals with score < {threshold}...")
    regen_targets = extract_visual_regen_targets(s5_results, threshold=threshold)
    
    if not regen_targets:
        print("\n✓ No visuals need regeneration. Done.")
        return 0
    
    print(f"  Found {len(regen_targets)} visual(s) needing regeneration")
    
    # Show targets
    print("\n  Regeneration targets:")
    for i, target in enumerate(regen_targets, 1):
        print(f"    {i}. {target['group_id']}/{target['cluster_id']} (score: {target['score']:.1f})")
        for j, issue in enumerate(target['issues'], 1):
            desc = issue.get("description", "")[:60]
            severity = issue.get("severity", "unknown")
            print(f"       Issue {j} [{severity}]: {desc}{'...' if len(issue.get('description', '')) > 60 else ''}")
    
    # 3. Load S3 specs
    print(f"\n[Step 3] Loading S3 specs...")
    if not s3_spec_path.exists():
        print(f"Error: S3 spec file not found: {s3_spec_path}", file=sys.stderr)
        return 1
    
    s3_specs = load_jsonl(s3_spec_path)
    print(f"  Loaded {len(s3_specs)} S3 spec(s)")
    
    # 4. Generate enhanced specs
    print(f"\n[Step 4] Generating enhanced S3 specs...")
    enhanced_specs, success_count, error_count = generate_enhanced_specs(
        regen_targets, s3_specs
    )
    
    # Summary
    print("\n" + "="*80)
    print(f"[Step 4] Processing complete:")
    print(f"  Success: {success_count}/{len(regen_targets)}")
    print(f"  Errors: {error_count}/{len(regen_targets)}")
    
    if error_count > 0:
        print(f"\n⚠️  Warning: {error_count} visual(s) failed. Check errors above.")
    
    if not enhanced_specs:
        print("\n❌ Error: No enhanced specs generated. Cannot proceed.")
        return 1
    
    # 5. Write enhanced specs
    print(f"\n[Step 5] Writing enhanced S3 specs...")
    write_jsonl(output_path, enhanced_specs)
    print(f"  Written {len(enhanced_specs)} spec(s) to: {output_path}")
    
    print("\n" + "="*80)
    print("✓ S6 input generation complete!")
    print(f"  Output: {output_path}")
    print(f"  Next step: Run S4 image generator with --spec_path {output_path}")
    print("="*80)
    
    return 0


# =========================
# CLI Entry Point
# =========================

def main():
    """CLI entry point for S6 input generator."""
    parser = argparse.ArgumentParser(
        description="S6 Input Generator - Generate enhanced specs for S1 table visual regeneration"
    )
    parser.add_argument("--base_dir", type=Path, default=Path("."),
                        help="Base directory (default: current directory)")
    parser.add_argument("--run_tag", type=str, required=True,
                        help="Run tag (e.g., FINAL_DISTRIBUTION)")
    parser.add_argument("--arm", type=str, required=True,
                        help="Arm (e.g., G)")
    parser.add_argument("--threshold", type=float, default=80.0,
                        help="Visual score threshold for regeneration (default: 80.0)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output filename (default: s3_image_spec__arm{arm}__s1_visual_regen.jsonl)")
    
    args = parser.parse_args()
    
    exit_code = run_s1_visual_positive_regen(
        base_dir=args.base_dir,
        run_tag=args.run_tag,
        arm=args.arm,
        threshold=args.threshold,
        output_filename=args.output,
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()


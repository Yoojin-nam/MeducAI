#!/usr/bin/env python3
"""
Generate PDFs for all groups and arms WITHOUT blinding

This script:
1. Reads groups from selected_18_groups.json or S1 results
2. Generates PDFs for all groups across all arms (A-F)
3. Does NOT use --blinded flag
4. Outputs to specified directory

Usage:
    python 3_Code/Scripts/generate_pdfs_no_blind.py \
        --run_tag S0_QA_final_time \
        --out_dir 6_Distributions/QA_Packets/S0_final_time_no_blind
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set

def load_groups_from_json(json_path: Path) -> List[Dict[str, str]]:
    """Load groups from selected_18_groups.json."""
    if not json_path.exists():
        return []
    
    with open(json_path, "r", encoding="utf-8") as f:
        groups = json.load(f)
    return groups

def load_groups_from_s1(s1_path: Path) -> List[Dict[str, str]]:
    """Load all groups from S1 results."""
    groups = []
    if not s1_path.exists():
        return groups
    
    seen_group_ids: Set[str] = set()
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                group_id = record.get("group_id", "").strip()
                if group_id and group_id not in seen_group_ids:
                    seen_group_ids.add(group_id)
                    groups.append({
                        "group_id": group_id,
                        "group_key": record.get("group_key", ""),
                        "specialty": record.get("specialty", ""),
                    })
            except json.JSONDecodeError:
                continue
    
    return groups

def generate_pdf_for_group_arm(
    base_dir: Path,
    run_tag: str,
    arm: str,
    group_id: str,
    out_dir: Path,
) -> bool:
    """Generate PDF for a single group-arm combination WITHOUT blinding."""
    pdf_script = base_dir / "3_Code" / "src" / "07_build_set_pdf.py"
    
    if not pdf_script.exists():
        print(f"    ❌ PDF script not found: {pdf_script}")
        return False
    
    cmd = [
        sys.executable,
        str(pdf_script),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
        "--group_id", group_id,
        "--out_dir", str(out_dir),
        "--allow_missing_images",  # Allow missing images to avoid failures
        # Note: NOT using --blinded flag
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=base_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        
        if result.returncode == 0:
            # Check if PDF was created (non-blinded format)
            pdf_filename_with_tag = f"SET_{group_id}_arm{arm}_{run_tag}.pdf"
            pdf_filename_without_tag = f"SET_{group_id}_arm{arm}.pdf"
            
            pdf_path = out_dir / pdf_filename_with_tag
            if not pdf_path.exists():
                pdf_path = out_dir / pdf_filename_without_tag
            
            if pdf_path.exists():
                print(f"    ✅ PDF created: {pdf_path.name}")
                return True
            else:
                print(f"    ⚠️  Command succeeded but PDF not found")
                print(f"       Expected: {pdf_filename_with_tag} or {pdf_filename_without_tag}")
                if result.stdout:
                    stdout_lines = result.stdout.strip().split('\n')
                    for line in stdout_lines[-5:]:
                        if line.strip():
                            print(f"       [stdout] {line}")
                return False
        else:
            print(f"    ❌ PDF generation failed (exit code {result.returncode})")
            if result.stderr:
                stderr_lines = result.stderr.strip().split('\n')
                for line in stderr_lines[-5:]:
                    if line.strip():
                        print(f"       [stderr] {line}")
            return False
    except Exception as e:
        print(f"    ❌ Exception during PDF generation: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Generate PDFs for all groups and arms WITHOUT blinding",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument("--run_tag", type=str, required=True, help="Run tag (e.g., S0_QA_final_time)")
    parser.add_argument(
        "--out_dir",
        type=str,
        default="6_Distributions/QA_Packets/S0_final_time_no_blind",
        help="Output directory for PDFs",
    )
    parser.add_argument(
        "--arms",
        type=str,
        nargs="+",
        default=["A", "B", "C", "D", "E", "F"],
        help="Arms to process (default: A B C D E F)",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        print(f"❌ Base directory does not exist: {base_dir}")
        sys.exit(1)
    
    run_tag = args.run_tag.strip()
    out_dir = base_dir / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    
    arms = [arm.upper() for arm in args.arms]
    
    print("="*70)
    print("PDF Generator (NO BLINDING)")
    print("="*70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Arms: {', '.join(arms)}")
    print(f"Output directory: {out_dir}")
    print(f"Blinded mode: FALSE (no blinding)")
    print("="*70)
    
    # Try to load groups from selected_18_groups.json first
    groups_json_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / "selected_18_groups.json"
    groups = load_groups_from_json(groups_json_path)
    
    if not groups:
        # Fallback: load from S1 results (first arm)
        print(f"\n>>> Groups JSON not found, loading from S1 results...")
        s1_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"stage1_struct__arm{arms[0]}.jsonl"
        groups = load_groups_from_s1(s1_path)
    
    if not groups:
        print(f"❌ No groups found")
        sys.exit(1)
    
    print(f"\n>>> Found {len(groups)} groups")
    for group in groups:
        print(f"   - {group['group_id']}: {group.get('specialty', 'unknown')}")
    
    # Generate PDFs for each group-arm combination
    print(f"\n>>> Generating PDFs for {len(groups)} groups × {len(arms)} arms = {len(groups) * len(arms)} PDFs...")
    print()
    
    total_count = 0
    success_count = 0
    failed_combinations = []
    
    for arm in arms:
        print(f"\n--- Processing Arm {arm} ---")
        
        # Verify S1 results exist for this arm
        s1_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"stage1_struct__arm{arm}.jsonl"
        if not s1_path.exists():
            print(f"⚠️  S1 results not found for arm {arm}, skipping all groups for this arm")
            continue
        
        for idx, group in enumerate(groups, 1):
            group_id = group["group_id"]
            specialty = group.get("specialty", "unknown")
            
            total_count += 1
            print(f"[{total_count}/{len(groups) * len(arms)}] Arm {arm} - {group_id} ({specialty})...")
            
            success = generate_pdf_for_group_arm(
                base_dir=base_dir,
                run_tag=run_tag,
                arm=arm,
                group_id=group_id,
                out_dir=out_dir,
            )
            
            if success:
                success_count += 1
            else:
                failed_combinations.append(f"{group_id}_arm{arm}")
    
    # Summary
    print("\n" + "="*70)
    print("Summary")
    print("="*70)
    print(f"Total PDFs attempted: {total_count}")
    print(f"Successfully generated: {success_count}")
    print(f"Failed: {len(failed_combinations)}")
    
    if failed_combinations:
        print(f"\nFailed combinations:")
        for combo in failed_combinations[:20]:  # Show first 20
            print(f"  - {combo}")
        if len(failed_combinations) > 20:
            print(f"  ... and {len(failed_combinations) - 20} more")
    
    print(f"\nOutput directory: {out_dir}")
    print("="*70)
    
    if success_count == 0:
        print("\n❌ No PDFs were generated successfully")
        sys.exit(1)
    elif len(failed_combinations) > 0:
        print(f"\n⚠️  Generated {success_count} PDFs, but {len(failed_combinations)} failed")
        sys.exit(1)
    else:
        print(f"\n✅ Successfully generated {success_count} PDFs")
        sys.exit(0)

if __name__ == "__main__":
    main()


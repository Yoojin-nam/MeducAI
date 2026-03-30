#!/usr/bin/env python3
"""
Generate QA deployment PDFs for all groups (allowing missing images)

This script:
1. Reads S1 results from a specified run_tag
2. Extracts all groups from S1 results
3. Generates individual PDF for each group using --allow_missing_images flag
4. Useful when image generation has failed or is incomplete

Usage:
    python 3_Code/src/tools/qa/generate_qa_pdfs_allow_missing_images.py \
        --run_tag <RUN_TAG> \
        --arm <A-F> \
        [--base_dir .] \
        [--out_dir 6_Distributions/QA_Packets]
"""

import argparse
import glob
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def load_all_groups_from_s1(s1_path: Path) -> List[Dict[str, str]]:
    """Load all groups from S1 results with their metadata."""
    groups = []
    if not s1_path.exists():
        return groups
    
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                group_id = record.get("group_id", "").strip()
                group_key = record.get("group_key", "").strip()
                specialty = record.get("specialty", "").strip()
                
                if group_id:
                    groups.append({
                        "group_id": group_id,
                        "group_key": group_key,
                        "specialty": specialty,
                    })
            except json.JSONDecodeError:
                continue
    
    return groups


def generate_pdf_for_group(
    base_dir: Path,
    run_tag: str,
    arm: str,
    group_id: str,
    out_dir: Path,
    blinded: bool = True,
    surrogate_csv_path: Optional[str] = None,
) -> bool:
    """Generate PDF for a single group using 07_build_set_pdf.py with --allow_missing_images."""
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
        "--allow_missing_images",  # Allow missing images
    ]
    
    # Add blinded mode flags for QA compliance (QA Blinding Procedure v2.0)
    if blinded:
        cmd.append("--blinded")
        if surrogate_csv_path:
            cmd.extend(["--set_surrogate_csv", surrogate_csv_path])
        else:
            # Default surrogate map location
            default_surrogate = base_dir / "0_Protocol" / "06_QA_and_Study" / "QA_Operations" / "surrogate_map.csv"
            if default_surrogate.exists():
                cmd.extend(["--set_surrogate_csv", str(default_surrogate)])
            else:
                print(f"    ⚠️  Warning: Surrogate map not found at {default_surrogate}, using hash-based surrogate")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=base_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        
        if result.returncode == 0:
            # Check if PDF was created
            # Note: 07_build_set_pdf.py filename format depends on blinded mode:
            # - Non-blinded: SET_{group_id}_arm{arm}_{run_tag}.pdf
            # - Blinded: SET_{surrogate}_{run_tag}.pdf
            # We need to check both formats
            if blinded:
                # In blinded mode, filename uses surrogate ID
                # We can't predict the exact filename without loading the surrogate map
                # So we'll check for any PDF file that starts with SET_ and ends with the run_tag
                pdf_pattern = f"SET_*_{run_tag}.pdf"
                matching_pdfs = list(out_dir.glob(pdf_pattern))
                if matching_pdfs:
                    # Use the most recently created one (should be the one we just created)
                    pdf_path = max(matching_pdfs, key=lambda p: p.stat().st_mtime)
                    print(f"    ✅ PDF created: {pdf_path.name}")
                    return True
                else:
                    pdf_filename_with_tag = f"SET_*_{run_tag}.pdf"
                    pdf_filename_without_tag = f"SET_*.pdf"
            else:
                pdf_filename_with_tag = f"SET_{group_id}_arm{arm}_{run_tag}.pdf"
                pdf_filename_without_tag = f"SET_{group_id}_arm{arm}.pdf"
            
            # Try both filename formats (with and without run_tag)
            if not blinded:
                pdf_path = out_dir / pdf_filename_with_tag
                if not pdf_path.exists():
                    pdf_path = out_dir / pdf_filename_without_tag
                
                if pdf_path.exists():
                    print(f"    ✅ PDF created: {pdf_path.name}")
                    return True
                else:
                    print(f"    ⚠️  Command succeeded but PDF not found")
                    print(f"       Expected: {pdf_filename_with_tag} or {pdf_filename_without_tag}")
                # Print stdout/stderr to help debug
                if result.stdout:
                    stdout_lines = result.stdout.strip().split('\n')
                    for line in stdout_lines[-10:]:  # Last 10 lines
                        if line.strip():
                            print(f"       [stdout] {line}")
                if result.stderr:
                    stderr_lines = result.stderr.strip().split('\n')
                    for line in stderr_lines[-10:]:  # Last 10 lines
                        if line.strip():
                            print(f"       [stderr] {line}")
                return False
        else:
            print(f"    ❌ PDF generation failed (exit code {result.returncode})")
            if result.stdout:
                stdout_lines = result.stdout.strip().split('\n')
                for line in stdout_lines[-10:]:  # Last 10 lines
                    if line.strip():
                        print(f"       [stdout] {line}")
            if result.stderr:
                stderr_lines = result.stderr.strip().split('\n')
                for line in stderr_lines[-10:]:  # Last 10 lines
                    if line.strip():
                        print(f"       [stderr] {line}")
            return False
    except Exception as e:
        print(f"    ❌ Exception during PDF generation: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate QA deployment PDFs for all groups (allowing missing images)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument("--run_tag", type=str, required=True, help="Run tag (e.g., TEST_S2_V7_20251220_105343)")
    parser.add_argument("--arm", type=str, default="A", help="Arm identifier (default: A)")
    parser.add_argument(
        "--out_dir",
        type=str,
        default="6_Distributions/QA_Packets",
        help="Output directory for PDFs (default: 6_Distributions/QA_Packets)",
    )
    parser.add_argument(
        "--blinded",
        action="store_true",
        default=True,
        help="Enable blinded mode for QA compliance (default: True, required for QA deployment)",
    )
    parser.add_argument(
        "--set_surrogate_csv",
        type=str,
        default=None,
        help="Path to surrogate mapping CSV (default: 0_Protocol/06_QA_and_Study/QA_Operations/surrogate_map.csv)",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        print(f"❌ Base directory does not exist: {base_dir}")
        sys.exit(1)
    
    run_tag = args.run_tag.strip()
    arm = args.arm.upper()
    out_dir = base_dir / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*70)
    print("QA PDF Generator (Allow Missing Images)")
    print("="*70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Arm: {arm}")
    print(f"Output directory: {out_dir}")
    print(f"Blinded mode: {args.blinded}")
    if args.blinded:
        surrogate_path = args.set_surrogate_csv or str(base_dir / "0_Protocol" / "06_QA_and_Study" / "QA_Operations" / "surrogate_map.csv")
        print(f"Surrogate map: {surrogate_path}")
    print("="*70)
    
    # Load S1 results to get all groups
    s1_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"stage1_struct__arm{arm}.jsonl"
    if not s1_path.exists():
        print(f"❌ S1 results not found: {s1_path}")
        sys.exit(1)
    
    print(f"\n>>> Loading groups from S1 results...")
    groups = load_all_groups_from_s1(s1_path)
    print(f"   Found {len(groups)} groups")
    
    if not groups:
        print("❌ No groups found in S1 results")
        sys.exit(1)
    
    # Generate PDF for each group
    print(f"\n>>> Generating PDFs for {len(groups)} groups...")
    print(f"   Note: Using --allow_missing_images flag (missing images will show as placeholders)")
    print()
    
    success_count = 0
    failed_groups = []
    
    for idx, group in enumerate(groups, 1):
        group_id = group["group_id"]
        specialty = group.get("specialty", "unknown")
        
        print(f"[{idx}/{len(groups)}] Processing {group_id} ({specialty})...")
        
        # Determine surrogate CSV path
        surrogate_csv = args.set_surrogate_csv
        if not surrogate_csv and args.blinded:
            default_surrogate = base_dir / "0_Protocol" / "06_QA_and_Study" / "QA_Operations" / "surrogate_map.csv"
            if default_surrogate.exists():
                surrogate_csv = str(default_surrogate)
        
        success = generate_pdf_for_group(
            base_dir=base_dir,
            run_tag=run_tag,
            arm=arm,
            group_id=group_id,
            out_dir=out_dir,
            blinded=args.blinded,
            surrogate_csv_path=surrogate_csv,
        )
        
        if success:
            success_count += 1
        else:
            failed_groups.append(group_id)
    
    # Summary
    print("\n" + "="*70)
    print("Summary")
    print("="*70)
    print(f"Total groups: {len(groups)}")
    print(f"Successfully generated: {success_count}")
    print(f"Failed: {len(failed_groups)}")
    
    if failed_groups:
        print(f"\nFailed groups:")
        for group_id in failed_groups:
            print(f"  - {group_id}")
    
    print(f"\nOutput directory: {out_dir}")
    print("="*70)
    
    if success_count == 0:
        print("\n❌ No PDFs were generated successfully")
        sys.exit(1)
    elif len(failed_groups) > 0:
        print(f"\n⚠️  Generated {success_count} PDFs, but {len(failed_groups)} failed")
        sys.exit(1)
    else:
        print(f"\n✅ Successfully generated {success_count} PDFs")
        sys.exit(0)


if __name__ == "__main__":
    main()


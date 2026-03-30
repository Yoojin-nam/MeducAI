#!/usr/bin/env python3
"""
Retry PDF generation for failed groups from a test run.
Usage: python3 retry_failed_pdfs.py --run_tag TEST_FIX_VERIFY_v2_20251221_094623
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def load_s1_group_id(base_dir: Path, run_tag: str, arm: str) -> Optional[str]:
    """Load actual group_id from S1 results."""
    s1_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"stage1_struct__arm{arm}.jsonl"
    if not s1_path.exists():
        return None
    
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                return record.get("group_id", "").strip()
            except json.JSONDecodeError:
                continue
    
    return None


def generate_pdf(base_dir: Path, run_tag: str, arm: str, group_id: str) -> bool:
    """Generate PDF for a group."""
    print(f"    [PDF] Generating for arm {arm}, group_id {group_id}...")
    
    out_dir = base_dir / "6_Distributions" / "QA_Packets"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    import subprocess
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "07_build_set_pdf.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
        "--group_id", group_id,
        "--out_dir", str(out_dir),
    ]
    
    try:
        result = subprocess.run(cmd, cwd=base_dir, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            pdf_path = out_dir / f"SET_{group_id}_arm{arm}_{run_tag}.pdf"
            if pdf_path.exists():
                print(f"    ✅ PDF created: {pdf_path}")
                return True
            else:
                print(f"    ⚠️  PDF command succeeded but file not found: {pdf_path}")
                return False
        else:
            print(f"    ❌ PDF generation failed:")
            print(f"    stdout: {result.stdout}")
            print(f"    stderr: {result.stderr}")
            return False
    except Exception as e:
        print(f"    ❌ Exception during PDF generation: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Retry PDF generation for failed groups")
    parser.add_argument("--run_tag", type=str, required=True, help="Run tag from test")
    parser.add_argument("--base_dir", type=str, default=".", help="Base directory")
    
    args = parser.parse_args()
    base_dir = Path(args.base_dir).resolve()
    run_tag = args.run_tag
    
    print("=" * 70)
    print(f"Retrying PDF generation for failed groups")
    print(f"Run tag: {run_tag}")
    print("=" * 70)
    
    # Failed groups from the test output
    # Based on the test results, these are the groups that failed PDF generation:
    failed_groups = [
        # TEST 9/12: Arm E - grp_3126ec9e7d (HTML parsing error)
        {"arm": "E", "group_id_hint": "grp_3126ec9e7d"},
        # TEST 11/12: Arm F - grp_1cb38da503 (Image missing)
        {"arm": "F", "group_id_hint": "grp_1cb38da503"},
        # TEST 12/12: Arm F - grp_4b36ed8159 (Image missing)
        {"arm": "F", "group_id_hint": "grp_4b36ed8159"},
    ]
    
    # Try to find group_id for each failed group
    success_count = 0
    for group_info in failed_groups:
        arm = group_info["arm"]
        group_id_hint = group_info["group_id_hint"]
        
        print(f"\n{'=' * 70}")
        print(f"Processing: Arm {arm}, hint: {group_id_hint}")
        print(f"{'=' * 70}")
        
        # Try to load group_id from S1 results
        group_id = load_s1_group_id(base_dir, run_tag, arm)
        
        if not group_id:
            print(f"    ⚠️  Could not find group_id for arm {arm}")
            print(f"    Trying to use hint: {group_id_hint}")
            # Try to extract from hint (remove 'grp_' prefix if present)
            if group_id_hint.startswith("grp_"):
                group_id = group_id_hint[4:]  # Remove 'grp_' prefix
            else:
                group_id = group_id_hint
            print(f"    Using group_id: {group_id}")
        else:
            print(f"    Found group_id: {group_id}")
        
        # Generate PDF
        if generate_pdf(base_dir, run_tag, arm, group_id):
            success_count += 1
        else:
            print(f"    ❌ Failed to generate PDF for arm {arm}, group_id {group_id}")
    
    print(f"\n{'=' * 70}")
    print(f"Summary: {success_count}/{len(failed_groups)} PDFs generated successfully")
    print(f"{'=' * 70}")
    
    return 0 if success_count == len(failed_groups) else 1


if __name__ == "__main__":
    sys.exit(main())


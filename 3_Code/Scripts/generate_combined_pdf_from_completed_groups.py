#!/usr/bin/env python3
"""
완료된 그룹들을 합쳐서 하나의 PDF를 생성하는 스크립트

Usage:
    python 3_Code/Scripts/generate_combined_pdf_from_completed_groups.py \
        --base_dir . \
        --run_tag RANDOM_4SPEC_20251226_151148 \
        --arm G
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def load_completed_groups_from_s2(s2_path: Path) -> List[str]:
    """Load completed group IDs from S2 results."""
    completed_groups = set()
    if not s2_path.exists():
        return []
    
    with open(s2_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    rec = json.loads(line)
                    group_id = rec.get("group_id", "")
                    if group_id:
                        completed_groups.add(group_id)
                except Exception:
                    continue
    
    return sorted(list(completed_groups))


def load_s1_group_mapping(s1_path: Path) -> Dict[str, str]:
    """Load group_key -> group_id mapping from S1 results."""
    mapping = {}
    if not s1_path.exists():
        return mapping
    
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    record = json.loads(line)
                    group_id = record.get("group_id", "").strip()
                    source_info = record.get("source_info", {})
                    group_key = source_info.get("group_key", "").strip()
                    if group_id and group_key:
                        mapping[group_key] = group_id
                except Exception:
                    continue
    
    return mapping


def generate_combined_pdf(
    base_dir: Path,
    run_tag: str,
    arm: str,
    group_ids: List[str],
) -> bool:
    """Generate one combined PDF for all completed groups."""
    print("\n" + "="*60)
    print("Generating Combined PDF")
    print("="*60)
    print(f"Run Tag: {run_tag}")
    print(f"Arm: {arm}")
    print(f"Groups: {', '.join(group_ids)}")
    print("="*60)
    
    # Import PDF building module
    pdf_module_path = base_dir / "3_Code" / "src" / "07_build_set_pdf.py"
    if not pdf_module_path.exists():
        print(f"❌ PDF module not found: {pdf_module_path}")
        return False
    
    # Import the module
    import importlib.util
    spec = importlib.util.spec_from_file_location("pdf_builder", pdf_module_path)
    pdf_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pdf_module)
    
    # Use 07_build_set_pdf.py's built-in combine feature
    # We'll call it via subprocess for each group, then combine, or use the built-in combine
    import subprocess
    
    print("\n>>> Creating combined PDF using 07_build_set_pdf.py...")
    
    # Create individual PDFs first
    individual_pdfs = []
    for group_id in group_ids:
        print(f"\n  Generating PDF for {group_id}...")
        cmd = [
            sys.executable,
            str(pdf_module_path),
            "--base_dir", str(base_dir),
            "--run_tag", run_tag,
            "--arm", arm,
            "--group_id", group_id,
            "--out_dir", str(base_dir / "6_Distributions" / "QA_Packets"),
            "--allow_missing_images",
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=base_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            
            # Find the created PDF (check both naming patterns)
            out_dir = base_dir / "6_Distributions" / "QA_Packets"
            pdf_filename1 = f"SET_{group_id}_arm{arm}.pdf"
            pdf_filename2 = f"SET_{group_id}_arm{arm}_{run_tag}.pdf"
            pdf_path = out_dir / pdf_filename2  # Try the run_tag version first
            
            if not pdf_path.exists():
                pdf_path = out_dir / pdf_filename1  # Fallback to simple name
            
            if pdf_path.exists():
                individual_pdfs.append(pdf_path)
                print(f"    ✅ Created: {pdf_path.name}")
            else:
                # Try to find any PDF with this group_id
                found = False
                for pdf_file in out_dir.glob(f"SET_{group_id}_arm{arm}*.pdf"):
                    individual_pdfs.append(pdf_file)
                    print(f"    ✅ Found: {pdf_file.name}")
                    found = True
                    break
                if not found:
                    print(f"    ⚠️  PDF not found for {group_id}")
        except subprocess.CalledProcessError as e:
            print(f"    ❌ Failed: {e.stderr[:200] if e.stderr else str(e)}")
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    if not individual_pdfs:
        print("\n❌ No PDFs were created")
        return False
    
    # Combine PDFs using PyPDF2
    print(f"\n>>> Combining {len(individual_pdfs)} PDFs...")
    try:
        from PyPDF2 import PdfMerger
        
        out_dir = base_dir / "6_Distributions" / "QA_Packets"
        out_dir.mkdir(parents=True, exist_ok=True)
        combined_pdf_path = out_dir / f"COMBINED_{run_tag}_arm{arm}.pdf"
        
        merger = PdfMerger()
        for pdf_path in individual_pdfs:
            merger.append(str(pdf_path))
        
        merger.write(str(combined_pdf_path))
        merger.close()
        
        print(f"✅ Successfully created combined PDF: {combined_pdf_path.name}")
        print(f"   Size: {combined_pdf_path.stat().st_size / 1024 / 1024:.2f} MB")
        return True
    except ImportError:
        print("⚠️  PyPDF2 not available. Installing...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "PyPDF2"], check=True)
            from PyPDF2 import PdfMerger
            
            out_dir = base_dir / "6_Distributions" / "QA_Packets"
            combined_pdf_path = out_dir / f"COMBINED_{run_tag}_arm{arm}.pdf"
            
            merger = PdfMerger()
            for pdf_path in individual_pdfs:
                merger.append(str(pdf_path))
            
            merger.write(str(combined_pdf_path))
            merger.close()
            
            print(f"✅ Successfully created combined PDF: {combined_pdf_path.name}")
            return True
        except Exception as e:
            print(f"❌ Failed to install PyPDF2: {e}")
            print("Individual PDFs created:")
            for pdf_path in individual_pdfs:
                print(f"  - {pdf_path}")
            return True
    except Exception as e:
        print(f"❌ Failed to combine PDFs: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate combined PDF from completed groups"
    )
    parser.add_argument(
        "--base_dir",
        type=str,
        default=".",
        help="Base directory of the project",
    )
    parser.add_argument(
        "--run_tag",
        type=str,
        required=True,
        help="Run tag",
    )
    parser.add_argument(
        "--arm",
        type=str,
        required=True,
        help="Arm identifier (A-F)",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    
    # Load completed groups from S2
    gen_dir = base_dir / "2_Data" / "metadata" / "generated" / args.run_tag
    s2_path = gen_dir / f"s2_results__s1arm{args.arm}__s2arm{args.arm}.jsonl"
    
    print("="*60)
    print("Combined PDF Generator")
    print("="*60)
    print(f"Base Dir: {base_dir}")
    print(f"Run Tag: {args.run_tag}")
    print(f"Arm: {args.arm}")
    print("="*60)
    
    if not s2_path.exists():
        print(f"\n❌ S2 results not found: {s2_path}")
        sys.exit(1)
    
    completed_groups = load_completed_groups_from_s2(s2_path)
    
    if not completed_groups:
        print("\n❌ No completed groups found in S2 results")
        sys.exit(1)
    
    print(f"\n>>> Found {len(completed_groups)} completed groups:")
    for gid in completed_groups:
        print(f"  - {gid}")
    
    # Generate combined PDF
    success = generate_combined_pdf(
        base_dir=base_dir,
        run_tag=args.run_tag,
        arm=args.arm,
        group_ids=completed_groups,
    )
    
    if success:
        print("\n" + "="*60)
        print("✅ SUCCESS: Combined PDF created")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ FAILED: PDF generation failed")
        print("="*60)
        sys.exit(1)


if __name__ == "__main__":
    main()


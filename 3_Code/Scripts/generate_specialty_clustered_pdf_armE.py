#!/usr/bin/env python3
"""
Specialty별로 1개씩 그룹을 선택하여 E arm으로 전체 파이프라인 실행 (Clustering 포함)

This script:
1. Reads groups_canonical.csv
2. Selects one group per specialty
3. Runs full pipeline (S1→S2→S3→S4→PDF) with arm E
4. Supports clustering for multi-infographic generation

Usage:
    python 3_Code/Scripts/generate_specialty_clustered_pdf_armE.py [--base_dir .] [--run_tag SPECIALTY_CLUSTER_YYYYMMDD_HHMMSS] [--seed 42]
"""

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).parent.parent.parent


def load_groups_canonical(csv_path: Path) -> List[Dict[str, str]]:
    """Load groups from groups_canonical.csv."""
    groups = []
    if not csv_path.exists():
        raise FileNotFoundError(f"groups_canonical.csv not found: {csv_path}")
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            groups.append({
                "group_id": row.get("group_id", "").strip(),
                "group_key": row.get("group_key", "").strip(),
                "specialty": row.get("specialty", "").strip(),
                "anatomy": row.get("anatomy", "").strip(),
                "modality_or_type": row.get("modality_or_type", "").strip(),
                "category": row.get("category", "").strip(),
                "objectives": row.get("objectives", "").strip(),
            })
    
    return groups


def select_one_group_per_specialty(groups: List[Dict[str, str]], seed: int = 42) -> List[Dict[str, str]]:
    """Select one random group per specialty."""
    import random
    random.seed(seed)
    
    # Group by specialty
    specialty_groups: Dict[str, List[Dict[str, str]]] = {}
    for group in groups:
        specialty = group.get("specialty", "").strip()
        if not specialty:
            continue
        if specialty not in specialty_groups:
            specialty_groups[specialty] = []
        specialty_groups[specialty].append(group)
    
    # Select one random group per specialty
    selected = []
    for specialty, group_list in sorted(specialty_groups.items()):
        if group_list:
            selected_group = random.choice(group_list)
            selected.append(selected_group)
            print(f"  [{specialty:20s}] Selected: {selected_group['group_id']} - {selected_group['group_key']}")
    
    return selected


def run_command(cmd: List[str], cwd: Optional[Path] = None, description: str = "") -> bool:
    """Run a command and return True if successful."""
    if description:
        print(f"\n>>> {description}")
    print(f"[CMD] {' '.join(cmd)}")
    
    result = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=False)
    if result.returncode != 0:
        print(f"❌ Command failed with exit code {result.returncode}")
        return False
    return True


def run_s1(base_dir: Path, run_tag: str, arm: str, group_ids: List[str]) -> bool:
    """Run S1 generation for selected groups."""
    group_id_args = []
    for gid in group_ids:
        group_id_args.extend(["--only_group_id", gid])
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "01_generate_json.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
        "--stage", "1",
        "--mode", "FINAL",
    ] + group_id_args
    
    return run_command(cmd, cwd=base_dir, description=f"S1: Generating tables for {len(group_ids)} groups (arm {arm})")


def run_s2(base_dir: Path, run_tag: str, arm: str, s1_arm: str, group_ids: List[str]) -> bool:
    """Run S2 generation (uses S1 output from s1_arm)."""
    group_id_args = []
    for gid in group_ids:
        group_id_args.extend(["--only_group_id", gid])
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "01_generate_json.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
        "--stage", "2",
        "--mode", "FINAL",
        "--s1_arm", s1_arm,  # Use S1 output from s1_arm
    ] + group_id_args
    
    return run_command(cmd, cwd=base_dir, description=f"S2: Generating cards (arm {arm}, using S1 from arm {s1_arm})")


def run_s3(base_dir: Path, run_tag: str, arm: str, s1_arm: str) -> bool:
    """Run S3 policy resolver."""
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "03_s3_policy_resolver.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
        "--s1_arm", s1_arm,  # Use S1 output from s1_arm
    ]
    
    return run_command(cmd, cwd=base_dir, description=f"S3: Resolving image policies (arm {arm})")


def run_s4(base_dir: Path, run_tag: str, arm: str) -> bool:
    """Run S4 image generator."""
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "04_s4_image_generator.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
    ]
    
    return run_command(cmd, cwd=base_dir, description=f"S4: Generating images (arm {arm})")


def check_s1_infographics(base_dir: Path, run_tag: str, arm: str, selected_groups: List[Dict[str, str]]) -> bool:
    """Check if infographic clusters are generated in S1 output."""
    print(f"\n>>> Checking S1 infographic generation for {len(selected_groups)} groups")
    
    s1_struct_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"stage1_struct__arm{arm}.jsonl"
    
    if not s1_struct_path.exists():
        print(f"❌ S1 output file not found: {s1_struct_path}")
        return False
    
    # Load S1 results
    s1_results = {}
    with open(s1_struct_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                group_id = record.get("group_id", "").strip()
                if group_id:
                    s1_results[group_id] = record
            except json.JSONDecodeError:
                continue
    
    # Check each selected group
    print("\n" + "="*80)
    print("S1 Infographic Generation Check")
    print("="*80)
    
    all_ok = True
    for idx, group in enumerate(selected_groups, 1):
        group_id = group["group_id"]
        group_key = group.get("group_key", "unknown")
        specialty = group.get("specialty", "unknown")
        
        if group_id not in s1_results:
            print(f"\n[{idx}/{len(selected_groups)}] ❌ {specialty} ({group_id})")
            print(f"   S1 output not found")
            all_ok = False
            continue
        
        record = s1_results[group_id]
        entity_clusters = record.get("entity_clusters", [])
        infographic_clusters = record.get("infographic_clusters", [])
        
        has_clusters = bool(entity_clusters and infographic_clusters)
        cluster_count = len(infographic_clusters) if infographic_clusters else 0
        
        status = "✅" if has_clusters else "⚠️"
        print(f"\n[{idx}/{len(selected_groups)}] {status} {specialty} ({group_id})")
        print(f"   Group key: {group_key}")
        print(f"   Entity clusters: {len(entity_clusters) if entity_clusters else 0}")
        print(f"   Infographic clusters: {cluster_count}")
        
        if has_clusters:
            print(f"   ✅ Infographic clustering successful")
            # Show cluster details
            for i, inf_cluster in enumerate(infographic_clusters[:3], 1):  # Show first 3
                cluster_id = inf_cluster.get("cluster_id", f"cluster_{i}")
                prompt = inf_cluster.get("infographic_prompt", "")
                prompt_preview = prompt[:60] + "..." if len(prompt) > 60 else prompt
                print(f"      - {cluster_id}: {prompt_preview}")
            if len(infographic_clusters) > 3:
                print(f"      ... and {len(infographic_clusters) - 3} more clusters")
        else:
            print(f"   ⚠️  No infographic clusters found")
            all_ok = False
    
    print("\n" + "="*80)
    if all_ok:
        print("✅ All groups have infographic clusters")
    else:
        print("⚠️  Some groups are missing infographic clusters")
    print("="*80)
    
    return all_ok


def generate_pdfs(base_dir: Path, run_tag: str, arm: str, selected_groups: List[Dict[str, str]]) -> bool:
    """Generate PDFs for each selected group."""
    print(f"\n>>> Generating PDFs for {len(selected_groups)} groups")
    
    out_dir = base_dir / "6_Distributions" / "QA_Packets" / run_tag
    out_dir.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    for idx, group in enumerate(selected_groups, 1):
        group_id = group["group_id"]
        specialty = group.get("specialty", "unknown")
        
        print(f"\n  [{idx}/{len(selected_groups)}] Generating PDF for {specialty} (group_id: {group_id})...")
        
        cmd = [
            sys.executable,
            str(base_dir / "3_Code" / "src" / "07_build_set_pdf.py"),
            "--base_dir", str(base_dir),
            "--run_tag", run_tag,
            "--arm", arm,
            "--group_id", group_id,
            "--out_dir", str(out_dir),
            "--allow_missing_images",
        ]
        
        if run_command(cmd, cwd=base_dir, description=f"PDF: {specialty}"):
            success_count += 1
            print(f"    ✅ PDF generated: {out_dir / f'SET_{group_id}_arm{arm}.pdf'}")
        else:
            print(f"    ❌ PDF generation failed for {specialty}")
    
    print(f"\n>>> PDF generation complete: {success_count}/{len(selected_groups)} successful")
    return success_count == len(selected_groups)


def main():
    parser = argparse.ArgumentParser(
        description="Generate specialty-based clustered PDFs with arm E",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument(
        "--run_tag",
        type=str,
        default=None,
        help="Run tag (default: SPECIALTY_CLUSTER_YYYYMMDD_HHMMSS)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for group selection (default: 42)")
    parser.add_argument(
        "--groups_csv",
        type=str,
        default="2_Data/metadata/groups_canonical.csv",
        help="Path to groups_canonical.csv",
    )
    parser.add_argument(
        "--skip_s1",
        action="store_true",
        help="Skip S1 (assume already run)",
    )
    parser.add_argument(
        "--skip_s2",
        action="store_true",
        help="Skip S2 (assume already run)",
    )
    parser.add_argument(
        "--skip_s3",
        action="store_true",
        help="Skip S3 (assume already run)",
    )
    parser.add_argument(
        "--skip_s4",
        action="store_true",
        help="Skip S4 (assume already run)",
    )
    parser.add_argument(
        "--s1_only",
        action="store_true",
        help="Check infographic generation from existing S1 results (skips S1 execution, S2, S3, S4, PDF)",
    )
    
    args = parser.parse_args()
    
    # If s1_only is set, automatically skip S1 (use existing results)
    if args.s1_only:
        args.skip_s1 = True
    
    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        print(f"❌ Base directory does not exist: {base_dir}")
        sys.exit(1)
    
    # Generate run_tag if not provided
    if args.run_tag:
        run_tag = args.run_tag
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_tag = f"SPECIALTY_CLUSTER_{timestamp}"
    
    arm = "E"  # Fixed to arm E
    s1_arm = "E"  # S1 arm (same as S2 arm in this case)
    
    print("="*80)
    print("Specialty-based Clustered PDF Generator (Arm E)")
    print("="*80)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Arm: {arm}")
    print(f"Seed: {args.seed}")
    print("="*80)
    
    # Load groups
    groups_csv_path = base_dir / args.groups_csv
    print(f"\n>>> Loading groups from: {groups_csv_path}")
    groups = load_groups_canonical(groups_csv_path)
    print(f"   Loaded {len(groups)} groups")
    
    # Select one group per specialty
    print(f"\n>>> Selecting one group per specialty (seed={args.seed})...")
    selected_groups = select_one_group_per_specialty(groups, seed=args.seed)
    print(f"\n✅ Selected {len(selected_groups)} groups from {len(set(g['specialty'] for g in selected_groups))} specialties")
    
    # Extract group IDs
    group_ids = [g["group_id"] for g in selected_groups]
    
    # Run pipeline
    all_success = True
    
    # Step 1: S1
    if not args.skip_s1:
        if not run_s1(base_dir, run_tag, arm, group_ids):
            print("❌ S1 failed")
            all_success = False
            sys.exit(1)
    else:
        print("\n>>> Skipping S1 (--skip_s1)")
    
    # If s1_only mode, check infographics and exit
    if args.s1_only:
        print("\n>>> S1-only mode: Checking infographic generation...")
        if args.skip_s1:
            print("   (Using existing S1 results)")
        if check_s1_infographics(base_dir, run_tag, arm, selected_groups):
            print("\n✅ S1 infographic check completed successfully")
        else:
            print("\n⚠️  S1 infographic check found issues")
            all_success = False
    else:
        # Step 2: S2
        if not args.skip_s2:
            if not run_s2(base_dir, run_tag, arm, s1_arm, group_ids):
                print("❌ S2 failed")
                all_success = False
                sys.exit(1)
        else:
            print("\n>>> Skipping S2 (--skip_s2)")
        
        # Step 3: S3
        if not args.skip_s3:
            if not run_s3(base_dir, run_tag, arm, s1_arm):
                print("❌ S3 failed")
                all_success = False
                sys.exit(1)
        else:
            print("\n>>> Skipping S3 (--skip_s3)")
        
        # Step 4: S4
        if not args.skip_s4:
            if not run_s4(base_dir, run_tag, arm):
                print("❌ S4 failed")
                all_success = False
                sys.exit(1)
        else:
            print("\n>>> Skipping S4 (--skip_s4)")
        
        # Step 5: Generate PDFs
        if not generate_pdfs(base_dir, run_tag, arm, selected_groups):
            print("❌ PDF generation had errors")
            all_success = False
    
    # Summary
    print("\n" + "="*80)
    if all_success:
        print("✅ SUCCESS: All steps completed")
        print(f"\nOutput files:")
        print(f"  PDFs: {base_dir / '6_Distributions' / 'QA_Packets' / run_tag}")
        print(f"  Metadata: {base_dir / '2_Data' / 'metadata' / 'generated' / run_tag}")
    else:
        print("⚠️  COMPLETED WITH ERRORS")
        print("   Check the output above for details")
    print("="*80)


if __name__ == "__main__":
    main()


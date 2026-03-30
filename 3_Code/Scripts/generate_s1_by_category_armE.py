#!/usr/bin/env python3
"""
카테고리별로 1개씩 그룹을 선택해서 arm E로 S1만 생성하고 PDF까지 생성하는 스크립트
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# 카테고리별로 선택할 그룹 ID (테이블 파일에서 추출)
CATEGORY_GROUPS = {
    "Pattern_Collection": "grp_0f2d714339",
    "Physiology_Process": "grp_de13f1c5d0",
    "QC": "grp_9b18e6ae4f",
    "Anatomy_Map": "grp_c1a8dcbd3b",
    "Equipment": "grp_2155b4f5c3",
    "General": "grp_5773989fd3",
    "Pathology_Pattern": "grp_f073599bec",
}

BASE_DIR = Path(__file__).parent.parent.parent
ARM = "E"
STAGE = "1"  # S1만 생성

# Run tag 생성 (타임스탬프 포함)
run_tag = f"S1_CATEGORY_TEST_arm{ARM}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

print(f"[INFO] Base directory: {BASE_DIR}")
print(f"[INFO] Run tag: {run_tag}")
print(f"[INFO] Arm: {ARM}")
print(f"[INFO] Stage: {STAGE} (S1 only)")
print(f"[INFO] Groups to process: {len(CATEGORY_GROUPS)}")

# S1 생성
print("\n" + "="*80)
print("Step 1: Generating S1 for all category groups")
print("="*80)

group_ids = list(CATEGORY_GROUPS.values())
group_id_args = []
for gid in group_ids:
    group_id_args.extend(["--only_group_id", gid])

cmd_s1 = [
    sys.executable,
    str(BASE_DIR / "3_Code" / "src" / "01_generate_json.py"),
    "--base_dir", str(BASE_DIR),
    "--run_tag", run_tag,
    "--arm", ARM,
    "--stage", STAGE,
    "--mode", "FINAL",
] + group_id_args

print(f"\n[CMD] {' '.join(cmd_s1)}\n")

result_s1 = subprocess.run(cmd_s1, cwd=str(BASE_DIR), capture_output=False)
if result_s1.returncode != 0:
    print(f"\n[ERROR] S1 generation failed with exit code {result_s1.returncode}")
    sys.exit(1)

print("\n[SUCCESS] S1 generation completed!")

# PDF 생성 (각 그룹별로)
print("\n" + "="*80)
print("Step 2: Generating PDFs for each group")
print("="*80)

for category, group_id in CATEGORY_GROUPS.items():
    print(f"\n[PDF] Generating PDF for {category} (group_id: {group_id})...")
    
    cmd_pdf = [
        sys.executable,
        str(BASE_DIR / "3_Code" / "src" / "07_build_set_pdf.py"),
        "--base_dir", str(BASE_DIR),
        "--run_tag", run_tag,
        "--arm", ARM,
        "--group_id", group_id,
        "--out_dir", str(BASE_DIR / "6_Distributions" / "QA_Packets" / run_tag),
        "--s1_only",  # S1-only mode: skip Cards section
        "--allow_missing_images",
    ]
    
    result_pdf = subprocess.run(cmd_pdf, cwd=str(BASE_DIR), capture_output=False)
    if result_pdf.returncode != 0:
        print(f"[WARNING] PDF generation failed for {category} (group_id: {group_id})")
        print(f"[CMD] {' '.join(cmd_pdf)}")
    else:
        print(f"[SUCCESS] PDF generated for {category}")

print("\n" + "="*80)
print("All processes completed!")
print(f"Run tag: {run_tag}")
print(f"Output directory: {BASE_DIR / '2_Data' / 'metadata' / 'generated' / run_tag}")
print(f"PDF directory: {BASE_DIR / '6_Distributions' / 'QA_Packets' / run_tag}")
print("="*80)


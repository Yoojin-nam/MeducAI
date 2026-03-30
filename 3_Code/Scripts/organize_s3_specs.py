#!/usr/bin/env python3
"""
S3 Spec 정리 및 버전 관리 스크립트

Purpose:
- 현재 S3 spec을 원본으로 보존
- suffix 기반 버전 관리 체계 적용
- 백업 파일 정리

Usage:
    python organize_s3_specs.py --run_tag FINAL_DISTRIBUTION --arm G

Author: MeducAI Team
Created: 2026-01-05
"""

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple


def analyze_s3_spec(spec_path: Path) -> Dict[str, Any]:
    """S3 spec 파일 분석"""
    if not spec_path.exists():
        return {"error": f"File not found: {spec_path}"}
    
    counts = {
        "S1_TABLE_VISUAL": 0,
        "S2_CARD_IMAGE": 0,
        "S2_CARD_CONCEPT": 0,
        "other": 0,
        "total": 0,
    }
    
    exam_profiles = {"diagram": 0, "realistic": 0, "other": 0}
    
    with open(spec_path, "r", encoding="utf-8") as f:
        for line in f:
            counts["total"] += 1
            try:
                d = json.loads(line)
                spec_kind = d.get("spec_kind", "")
                if spec_kind in counts:
                    counts[spec_kind] += 1
                else:
                    counts["other"] += 1
                
                profile = d.get("exam_prompt_profile", "").lower()
                if "realistic" in profile:
                    exam_profiles["realistic"] += 1
                elif "diagram" in profile:
                    exam_profiles["diagram"] += 1
                else:
                    exam_profiles["other"] += 1
            except json.JSONDecodeError:
                continue
    
    return {
        "path": str(spec_path),
        "counts": counts,
        "exam_profiles": exam_profiles,
    }


def count_images(images_dir: Path) -> Dict[str, Any]:
    """이미지 폴더 분석"""
    if not images_dir.exists():
        return {"error": f"Directory not found: {images_dir}"}
    
    counts = {"TABLE": 0, "Q1": 0, "Q2": 0, "other": 0, "total": 0}
    
    for img_file in images_dir.iterdir():
        if not img_file.suffix.lower() in (".jpg", ".jpeg", ".png"):
            continue
        counts["total"] += 1
        name = img_file.name
        if "__TABLE" in name:
            counts["TABLE"] += 1
        elif "__Q1." in name:
            counts["Q1"] += 1
        elif "__Q2." in name:
            counts["Q2"] += 1
        else:
            counts["other"] += 1
    
    return counts


def organize_s3_specs(
    base_dir: Path,
    run_tag: str,
    arm: str,
    dry_run: bool = True,
) -> List[str]:
    """S3 spec 파일들을 정리"""
    actions = []
    
    # 파일 경로들
    current_spec = base_dir / f"s3_image_spec__arm{arm}.jsonl"
    original_spec = base_dir / f"s3_image_spec__arm{arm}__original_diagram.jsonl"
    realistic_spec = base_dir / f"s3_image_spec__arm{arm}__realistic.jsonl"
    realistic_v1_spec = base_dir / f"s3_image_spec__arm{arm}__realistic_v1.jsonl"
    
    # 1. 현재 spec → 원본으로 복사 (이미 없으면)
    if current_spec.exists() and not original_spec.exists():
        actions.append(f"COPY: {current_spec.name} → {original_spec.name}")
        if not dry_run:
            shutil.copy2(current_spec, original_spec)
    elif original_spec.exists():
        actions.append(f"SKIP: {original_spec.name} already exists")
    
    # 2. realistic spec → v1으로 이름 변경 (없으면)
    if realistic_spec.exists() and not realistic_v1_spec.exists():
        actions.append(f"RENAME: {realistic_spec.name} → {realistic_v1_spec.name}")
        if not dry_run:
            shutil.move(realistic_spec, realistic_v1_spec)
    
    # 3. 백업 폴더 정리
    backup_dir = base_dir / "archive" / "backups"
    if backup_dir.exists():
        old_backups = list(backup_dir.glob("s3_image_spec*.backup_*"))
        for backup in old_backups:
            # 이전 버전 라벨링
            if "before_s3_rerun" in backup.name:
                new_name = backup.name.replace(".backup_before_s3_rerun_", "__old_s2_version_")
                new_name = new_name.replace(".jsonl", "") + ".jsonl"
                actions.append(f"RELABEL: {backup.name} → {new_name}")
                if not dry_run:
                    shutil.move(backup, backup_dir / new_name)
    
    return actions


def generate_report(base_dir: Path, run_tag: str, arm: str) -> str:
    """분석 리포트 생성"""
    lines = []
    lines.append("=" * 70)
    lines.append(f"S3 SPEC ANALYSIS REPORT - {run_tag} arm{arm}")
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append("=" * 70)
    lines.append("")
    
    # S3 spec 분석
    lines.append("## S3 Spec Files Analysis")
    lines.append("")
    
    spec_files = [
        base_dir / f"s3_image_spec__arm{arm}.jsonl",
        base_dir / f"s3_image_spec__arm{arm}__original_diagram.jsonl",
        base_dir / f"s3_image_spec__arm{arm}__realistic.jsonl",
        base_dir / f"s3_image_spec__arm{arm}__realistic_v1.jsonl",
    ]
    
    for spec_path in spec_files:
        if spec_path.exists():
            analysis = analyze_s3_spec(spec_path)
            lines.append(f"### {spec_path.name}")
            lines.append(f"  Total: {analysis['counts']['total']}")
            lines.append(f"  S1_TABLE_VISUAL: {analysis['counts']['S1_TABLE_VISUAL']}")
            lines.append(f"  S2_CARD_IMAGE: {analysis['counts']['S2_CARD_IMAGE']}")
            lines.append(f"  S2_CARD_CONCEPT: {analysis['counts']['S2_CARD_CONCEPT']}")
            lines.append(f"  exam_prompt_profile: {analysis['exam_profiles']}")
            lines.append("")
    
    # 이미지 폴더 분석
    lines.append("## Generated Images Analysis")
    lines.append("")
    
    images_dir = base_dir / "images"
    if images_dir.exists():
        img_counts = count_images(images_dir)
        lines.append(f"### {images_dir.name}/")
        lines.append(f"  Total: {img_counts['total']}")
        lines.append(f"  TABLE: {img_counts['TABLE']}")
        lines.append(f"  Q1: {img_counts['Q1']}")
        lines.append(f"  Q2: {img_counts['Q2']}")
        lines.append("")
    
    # 일치 여부 확인
    lines.append("## Consistency Check")
    lines.append("")
    
    current_spec = base_dir / f"s3_image_spec__arm{arm}.jsonl"
    if current_spec.exists() and images_dir.exists():
        spec_analysis = analyze_s3_spec(current_spec)
        img_counts = count_images(images_dir)
        
        s3_total = spec_analysis["counts"]["total"]
        img_total = img_counts["total"]
        
        if abs(s3_total - img_total) <= 1:
            lines.append(f"✅ S3 spec ({s3_total}) ≈ Images ({img_total}) - MATCH")
        else:
            lines.append(f"❌ S3 spec ({s3_total}) ≠ Images ({img_total}) - MISMATCH")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Organize S3 spec files")
    parser.add_argument("--run_tag", required=True, help="Run tag (e.g., FINAL_DISTRIBUTION)")
    parser.add_argument("--arm", required=True, help="Arm identifier (e.g., G)")
    parser.add_argument("--base_dir", default=None, help="Base directory (auto-detected if not provided)")
    parser.add_argument("--dry_run", action="store_true", help="Show actions without executing")
    parser.add_argument("--report", action="store_true", help="Generate analysis report only")
    
    args = parser.parse_args()
    
    # Base directory 자동 탐지
    if args.base_dir:
        base_dir = Path(args.base_dir)
    else:
        # Try common locations
        candidates = [
            Path(f"2_Data/metadata/generated/{args.run_tag}"),
            Path(f"../2_Data/metadata/generated/{args.run_tag}"),
            Path(f"../../2_Data/metadata/generated/{args.run_tag}"),
        ]
        base_dir = None
        for c in candidates:
            if c.exists():
                base_dir = c
                break
        
        if base_dir is None:
            print(f"ERROR: Cannot find base directory for run_tag={args.run_tag}")
            print("Please provide --base_dir explicitly")
            return 1
    
    print(f"Base directory: {base_dir}")
    print("")
    
    if args.report:
        report = generate_report(base_dir, args.run_tag, args.arm)
        print(report)
        
        # Save report
        report_path = base_dir / f"s3_spec_analysis_report__{args.arm}.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\nReport saved to: {report_path}")
        return 0
    
    # Organize
    print(f"{'DRY RUN - ' if args.dry_run else ''}Organizing S3 specs...")
    print("")
    
    actions = organize_s3_specs(base_dir, args.run_tag, args.arm, dry_run=args.dry_run)
    
    for action in actions:
        print(f"  {action}")
    
    if args.dry_run:
        print("")
        print("This was a dry run. Run without --dry_run to execute.")
    else:
        print("")
        print("Done!")
    
    return 0


if __name__ == "__main__":
    exit(main())


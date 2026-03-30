#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S3에서 요구하는 이미지 중 image 폴더 내에 생성되지 않은 이미지 개수 확인

Usage:
    python check_missing_images.py --run_tag <RUN_TAG> [--arm <ARM>]
    python check_missing_images.py --run_tag <RUN_TAG> --all_arms
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional


def sanitize_filename_component(s: str) -> str:
    """파일명에서 유효하지 않은 문자를 언더스코어로 치환"""
    invalid = '<>:"/\\|?*'
    for c in invalid:
        s = s.replace(c, '_')
    return s.strip()


def make_image_filename(
    *,
    run_tag: str,
    group_id: str,
    entity_id: Optional[str] = None,
    card_role: Optional[str] = None,
    spec_kind: Optional[str] = None,
    cluster_id: Optional[str] = None,
) -> str:
    """
    S4와 동일한 파일명 생성 로직
    """
    run_tag_safe = sanitize_filename_component(str(run_tag))
    group_id_safe = sanitize_filename_component(str(group_id))
    
    spec_kind = str(spec_kind or "").strip()
    if spec_kind == "S1_TABLE_VISUAL":
        if cluster_id:
            cluster_id_safe = sanitize_filename_component(str(cluster_id))
            return f"IMG__{run_tag_safe}__{group_id_safe}__TABLE__{cluster_id_safe}"
        else:
            return f"IMG__{run_tag_safe}__{group_id_safe}__TABLE"
    else:
        entity_id_safe = sanitize_filename_component(str(entity_id or ""))
        card_role_safe = sanitize_filename_component(str(card_role or "").upper())
        return f"IMG__{run_tag_safe}__{group_id_safe}__{entity_id_safe}__{card_role_safe}"


def load_s3_image_specs(s3_spec_path: Path) -> List[Dict]:
    """S3 이미지 스펙 파일 로드"""
    if not s3_spec_path.exists():
        return []
    
    specs = []
    with open(s3_spec_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                spec = json.loads(line)
                # image_asset_required가 True인 것만 확인
                if spec.get("image_asset_required", False):
                    specs.append(spec)
            except json.JSONDecodeError:
                continue
    
    return specs


def get_required_image_filenames(specs: List[Dict], run_tag: str) -> Set[str]:
    """S3 스펙에서 필요한 이미지 파일명 목록 생성 (확장자 제외)"""
    required = set()
    
    for spec in specs:
        run_tag_spec = str(spec.get("run_tag", run_tag)).strip()
        group_id = str(spec.get("group_id", "")).strip()
        spec_kind = str(spec.get("spec_kind", "")).strip()
        
        if spec_kind == "S1_TABLE_VISUAL":
            cluster_id = spec.get("cluster_id")
            filename_base = make_image_filename(
                run_tag=run_tag_spec,
                group_id=group_id,
                spec_kind=spec_kind,
                cluster_id=cluster_id,
            )
            required.add(filename_base)
        else:
            entity_id = spec.get("entity_id")
            card_role = spec.get("card_role")
            if entity_id and card_role:
                filename_base = make_image_filename(
                    run_tag=run_tag_spec,
                    group_id=group_id,
                    entity_id=entity_id,
                    card_role=card_role,
                    spec_kind=spec_kind,
                )
                required.add(filename_base)
    
    return required


def get_existing_image_files(images_dir: Path) -> Set[str]:
    """이미지 폴더에서 실제 존재하는 이미지 파일명 목록 (확장자 제외)"""
    existing = set()
    
    if not images_dir.exists():
        return existing
    
    # .jpg, .png, .jpeg 등 모든 이미지 확장자 확인
    image_extensions = [".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"]
    
    for ext in image_extensions:
        for img_file in images_dir.glob(f"*{ext}"):
            # 확장자 제거한 파일명
            filename_base = img_file.stem
            existing.add(filename_base)
    
    return existing


def check_missing_images(
    base_dir: Path,
    run_tag: str,
    arm: Optional[str] = None,
) -> Tuple[int, int, List[str], Dict[str, any]]:
    """
    누락된 이미지 확인
    
    Returns:
        (required_count, missing_count, missing_list, details)
    """
    out_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    
    # 모든 arm 확인 또는 특정 arm만 확인
    arms_to_check = []
    if arm:
        arms_to_check = [arm]
    else:
        # 모든 arm의 s3_image_spec 파일 찾기
        for spec_file in out_dir.glob("s3_image_spec__arm*.jsonl"):
            arm_from_file = spec_file.stem.replace("s3_image_spec__arm", "").replace(".jsonl", "")
            if arm_from_file:
                arms_to_check.append(arm_from_file)
    
    if not arms_to_check:
        print(f"⚠️  No S3 image spec files found in {out_dir}")
        return 0, 0, [], {}
    
    all_required = set()
    all_existing = set()
    missing_by_arm = {}
    details_by_arm = {}
    
    for arm_check in arms_to_check:
        s3_spec_path = out_dir / f"s3_image_spec__arm{arm_check}.jsonl"
        
        # images 폴더 확인 (baseline과 repaired 둘 다 확인)
        images_dir_baseline = out_dir / "images"
        images_dir_repaired = out_dir / "images__repaired"
        
        # S3 스펙 로드
        specs = load_s3_image_specs(s3_spec_path)
        required = get_required_image_filenames(specs, run_tag)
        
        # 실제 이미지 파일 확인 (baseline과 repaired 둘 다)
        existing_baseline = get_existing_image_files(images_dir_baseline)
        existing_repaired = get_existing_image_files(images_dir_repaired)
        existing = existing_baseline | existing_repaired
        
        missing = required - existing
        all_required |= required
        all_existing |= existing
        
        missing_by_arm[arm_check] = {
            "required": len(required),
            "existing": len(existing),
            "missing": len(missing),
            "missing_list": sorted(list(missing)),
        }
        
        details_by_arm[arm_check] = {
            "s3_spec_path": str(s3_spec_path),
            "images_dir_baseline": str(images_dir_baseline),
            "images_dir_repaired": str(images_dir_repaired),
            "specs_count": len(specs),
            "required_images": sorted(list(required)),
            "existing_images": sorted(list(existing)),
        }
    
    all_missing = all_required - all_existing
    
    return len(all_required), len(all_missing), sorted(list(all_missing)), {
        "by_arm": missing_by_arm,
        "details": details_by_arm,
    }


def main():
    parser = argparse.ArgumentParser(
        description="S3에서 요구하는 이미지 중 image 폴더 내에 생성되지 않은 이미지 개수 확인"
    )
    parser.add_argument(
        "--base_dir",
        type=str,
        default=".",
        help="프로젝트 루트 디렉토리 (기본값: 현재 디렉토리)",
    )
    parser.add_argument(
        "--run_tag",
        type=str,
        required=True,
        help="RUN_TAG (필수)",
    )
    parser.add_argument(
        "--arm",
        type=str,
        default=None,
        help="특정 arm만 확인 (기본값: 모든 arm 확인)",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    run_tag = args.run_tag.strip()
    arm = args.arm.strip() if args.arm else None
    
    print(f"🔍 Checking missing images for run_tag: {run_tag}")
    if arm:
        print(f"   Arm: {arm}")
    else:
        print(f"   Arm: All arms")
    print()
    
    required_count, missing_count, missing_list, details = check_missing_images(
        base_dir=base_dir,
        run_tag=run_tag,
        arm=arm,
    )
    
    print("=" * 80)
    print(f"📊 Summary")
    print("=" * 80)
    print(f"Required images: {required_count}")
    print(f"Missing images:  {missing_count}")
    print(f"Generated images: {required_count - missing_count}")
    print()
    
    if details.get("by_arm"):
        print("=" * 80)
        print(f"📋 By Arm")
        print("=" * 80)
        for arm_name, stats in sorted(details["by_arm"].items()):
            print(f"\nArm {arm_name}:")
            print(f"  Required: {stats['required']}")
            print(f"  Existing: {stats['existing']}")
            print(f"  Missing:  {stats['missing']}")
            if stats['missing'] > 0:
                print(f"  Missing files:")
                for missing_file in stats['missing_list'][:10]:  # 처음 10개만 표시
                    print(f"    - {missing_file}.jpg (or .png)")
                if len(stats['missing_list']) > 10:
                    print(f"    ... and {len(stats['missing_list']) - 10} more")
    
    if missing_count > 0:
        print()
        print("=" * 80)
        print(f"❌ Missing Images ({missing_count} total)")
        print("=" * 80)
        for missing_file in missing_list[:20]:  # 처음 20개만 표시
            print(f"  - {missing_file}.jpg (or .png)")
        if len(missing_list) > 20:
            print(f"  ... and {len(missing_list) - 20} more")
    else:
        print()
        print("✅ All required images are generated!")
    
    print()


if __name__ == "__main__":
    main()


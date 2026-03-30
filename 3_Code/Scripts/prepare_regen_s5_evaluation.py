#!/usr/bin/env python3
"""
Prepare Regen S5 Evaluation Setup

This script copies necessary files from FINAL_DISTRIBUTION to a new RUN_TAG
for S5 evaluation of regenerated items:
- S1R (S1 table regen): Pro model evaluation
- S2R (S2 card regen): Flash model evaluation
- S6-S1 (S6 S1 visual regen): Pro model evaluation with images
- S6-S2 (S6 S2 card regen): Flash model evaluation with images
"""

import argparse
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set


def copy_file(src: Path, dst: Path, description: str) -> bool:
    """Copy a file and report status."""
    try:
        if not src.exists():
            print(f"  ⚠️  {description}: Source file not found: {src}")
            return False
        
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  ✅ {description}: {src.name} → {dst.name}")
        return True
    except Exception as e:
        print(f"  ❌ {description}: Failed to copy {src.name}: {e}")
        return False


def filter_jsonl_by_spec_kind(
    input_path: Path,
    output_path: Path,
    allowed_spec_kinds: Set[str],
    description: str
) -> int:
    """
    Filter JSONL file by spec_kind field.
    
    Returns:
        Number of records written
    """
    if not input_path.exists():
        print(f"  ⚠️  {description}: Source file not found: {input_path}")
        return 0
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    count = 0
    try:
        with open(input_path, "r", encoding="utf-8") as f_in:
            with open(output_path, "w", encoding="utf-8") as f_out:
                for line in f_in:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        record = json.loads(line)
                        spec_kind = record.get("spec_kind", "")
                        
                        if spec_kind in allowed_spec_kinds:
                            f_out.write(line + "\n")
                            count += 1
                    except json.JSONDecodeError as e:
                        print(f"  ⚠️  {description}: Skipping invalid JSON line: {e}")
                        continue
        
        print(f"  ✅ {description}: Filtered {count} records from {input_path.name} → {output_path.name}")
        return count
    except Exception as e:
        print(f"  ❌ {description}: Failed to filter {input_path.name}: {e}")
        return 0


def copy_images_with_rename(
    src_dir: Path,
    dst_dir: Path,
    pattern: str,
    suffix_to_remove: str,
    description: str
) -> int:
    """
    Copy images matching pattern and remove suffix from filename.
    
    Args:
        src_dir: Source directory (e.g., images_regen/)
        dst_dir: Destination directory (e.g., images/)
        pattern: Glob pattern to match (e.g., "IMG__*__TABLE__*_regen.jpg")
        suffix_to_remove: Suffix to remove from filename (e.g., "_regen")
        description: Description for logging
    
    Returns:
        Number of images copied
    """
    if not src_dir.exists():
        print(f"  ⚠️  {description}: Source directory not found: {src_dir}")
        return 0
    
    dst_dir.mkdir(parents=True, exist_ok=True)
    
    count = 0
    try:
        for src_file in src_dir.glob(pattern):
            # Remove suffix from filename
            new_name = src_file.name.replace(suffix_to_remove, "")
            dst_file = dst_dir / new_name
            
            shutil.copy2(src_file, dst_file)
            count += 1
        
        if count > 0:
            print(f"  ✅ {description}: Copied {count} images from {src_dir.name}/ to {dst_dir.name}/")
        else:
            print(f"  ⚠️  {description}: No images found matching pattern: {pattern}")
        
        return count
    except Exception as e:
        print(f"  ❌ {description}: Failed to copy images: {e}")
        return 0


def update_image_paths_in_manifest(
    manifest_path: Path,
    old_suffix: str,
    new_suffix: str,
    source_dir: Path,
    target_dir: Path
) -> int:
    """
    Update image paths in S4 manifest file.
    
    Updates:
    - image_path: changes directory (from source to target) and removes suffix
    - media_filename: removes suffix
    
    Args:
        manifest_path: Path to manifest file to update
        old_suffix: Suffix to remove (e.g., "_regen")
        new_suffix: New suffix (usually "")
        source_dir: Source directory (for absolute path replacement)
        target_dir: Target directory (for absolute path replacement)
    
    Returns:
        Number of records updated
    """
    if not manifest_path.exists():
        return 0
    
    updated_count = 0
    temp_path = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    
    try:
        with open(manifest_path, "r", encoding="utf-8") as f_in:
            with open(temp_path, "w", encoding="utf-8") as f_out:
                for line in f_in:
                    line = line.strip()
                    if not line:
                        f_out.write("\n")
                        continue
                    
                    try:
                        record = json.loads(line)
                        record_updated = False
                        
                        # Update media_filename
                        if "media_filename" in record:
                            old_filename = record["media_filename"]
                            if old_suffix in old_filename:
                                record["media_filename"] = old_filename.replace(old_suffix, new_suffix)
                                record_updated = True
                        
                        # Update image_path
                        if "image_path" in record:
                            old_path_str = record["image_path"]
                            new_path_str = old_path_str
                            
                            # Handle absolute paths: replace source_dir with target_dir
                            if str(source_dir) in old_path_str:
                                new_path_str = new_path_str.replace(str(source_dir), str(target_dir))
                                record_updated = True
                            
                            # Update directory name in path (for relative paths or partial matches)
                            if "images_regen" in new_path_str:
                                new_path_str = new_path_str.replace("images_regen", "images")
                                record_updated = True
                            
                            # Remove suffix from filename
                            if old_suffix in new_path_str:
                                new_path_str = new_path_str.replace(old_suffix, new_suffix)
                                record_updated = True
                            
                            if record_updated:
                                record["image_path"] = new_path_str
                        
                        if record_updated:
                            updated_count += 1
                        
                        f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    except json.JSONDecodeError:
                        # Keep invalid lines as-is
                        f_out.write(line + "\n")
                        continue
        
        # Replace original with updated file
        temp_path.replace(manifest_path)
        if updated_count > 0:
            print(f"  ✅ Updated {updated_count} image paths in {manifest_path.name}")
        
        return updated_count
    except Exception as e:
        print(f"  ⚠️  Failed to update image paths in {manifest_path.name}: {e}")
        if temp_path.exists():
            temp_path.unlink()
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Prepare regen S5 evaluation by copying files from FINAL_DISTRIBUTION to new RUN_TAG"
    )
    parser.add_argument(
        "--source_run_tag",
        type=str,
        default="FINAL_DISTRIBUTION",
        help="Source RUN_TAG (default: FINAL_DISTRIBUTION)"
    )
    parser.add_argument(
        "--target_run_tag",
        type=str,
        default="FINAL_DISTRIBUTION_REGN",
        help="Target RUN_TAG (default: FINAL_DISTRIBUTION_REGN)"
    )
    parser.add_argument(
        "--arm",
        type=str,
        default="G",
        help="Arm identifier (default: G)"
    )
    parser.add_argument(
        "--base_dir",
        type=str,
        default=".",
        help="Base directory of MeducAI project (default: current directory)"
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    source_dir = base_dir / "2_Data" / "metadata" / "generated" / args.source_run_tag
    target_dir = base_dir / "2_Data" / "metadata" / "generated" / args.target_run_tag
    
    arm = args.arm.upper()
    
    print("=" * 80)
    print(f"Preparing Regen S5 Evaluation Setup")
    print("=" * 80)
    print(f"Source: {source_dir}")
    print(f"Target: {target_dir}")
    print(f"Arm: {arm}")
    print()
    
    if not source_dir.exists():
        print(f"❌ Error: Source directory not found: {source_dir}")
        return 1
    
    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    total_operations = 0
    
    # ============================================================
    # 1. Copy S1R files
    # ============================================================
    print("\n[1] Copying S1R files (S1 table regen)...")
    print("-" * 80)
    
    s1r_src = source_dir / f"stage1_struct__arm{arm}__regen.jsonl"
    s1r_dst = target_dir / f"stage1_struct__arm{arm}.jsonl"
    total_operations += 1
    if copy_file(s1r_src, s1r_dst, "S1R stage1_struct"):
        success_count += 1
    
    # ============================================================
    # 2. Copy S2R files
    # ============================================================
    print("\n[2] Copying S2R files (S2 card regen)...")
    print("-" * 80)
    
    s2r_src = source_dir / f"s2_results__s1arm{arm}__s2arm{arm}__regen.jsonl"
    s2r_dst = target_dir / f"s2_results__s1arm{arm}__s2arm{arm}.jsonl"
    total_operations += 1
    if copy_file(s2r_src, s2r_dst, "S2R s2_results"):
        success_count += 1
    
    # ============================================================
    # 3. Copy S6-S1 files (S1 visual regen)
    # ============================================================
    print("\n[3] Copying S6-S1 files (S1 visual regen)...")
    print("-" * 80)
    
    # S3 spec: filter S1_TABLE_VISUAL only
    s3_s1_src = source_dir / f"s3_image_spec__arm{arm}__s1_visual_regen.jsonl"
    s3_s1_dst = target_dir / f"s3_image_spec__arm{arm}__s1_visual.jsonl"
    total_operations += 1
    s3_s1_count = filter_jsonl_by_spec_kind(
        s3_s1_src,
        s3_s1_dst,
        {"S1_TABLE_VISUAL"},
        "S6-S1 S3 spec (S1_TABLE_VISUAL)"
    )
    if s3_s1_count > 0:
        success_count += 1
    
    # S4 manifest: filter S1_TABLE_VISUAL only
    s4_src = source_dir / f"s4_image_manifest__arm{arm}__regen.jsonl"
    s4_s1_dst = target_dir / f"s4_image_manifest__arm{arm}__s1_visual.jsonl"
    total_operations += 1
    s4_s1_count = filter_jsonl_by_spec_kind(
        s4_src,
        s4_s1_dst,
        {"S1_TABLE_VISUAL"},
        "S6-S1 S4 manifest (S1_TABLE_VISUAL)"
    )
    if s4_s1_count > 0:
        success_count += 1
    
    # Images: copy TABLE images from images_regen/ to images/
    src_images_dir = source_dir / "images_regen"
    dst_images_dir = target_dir / "images"
    total_operations += 1
    img_s1_count = copy_images_with_rename(
        src_images_dir,
        dst_images_dir,
        f"IMG__*__TABLE__*_regen.jpg",
        "_regen",
        "S6-S1 images (TABLE)"
    )
    if img_s1_count > 0:
        success_count += 1
    
    # Update image paths in S4 manifest
    if s4_s1_dst.exists():
        update_image_paths_in_manifest(
            s4_s1_dst,
            "_regen",
            "",
            source_dir,
            target_dir
        )
    
    # ============================================================
    # 4. Copy S6-S2 files (S2 card regen)
    # ============================================================
    print("\n[4] Copying S6-S2 files (S2 card regen)...")
    print("-" * 80)
    
    # S3 spec: filter S2_CARD_IMAGE and S2_CARD_CONCEPT
    s3_s2_src = source_dir / f"s3_image_spec__arm{arm}__regen.jsonl"
    s3_s2_dst = target_dir / f"s3_image_spec__arm{arm}__s2_card.jsonl"
    total_operations += 1
    s3_s2_count = filter_jsonl_by_spec_kind(
        s3_s2_src,
        s3_s2_dst,
        {"S2_CARD_IMAGE", "S2_CARD_CONCEPT"},
        "S6-S2 S3 spec (S2_CARD_IMAGE/CONCEPT)"
    )
    if s3_s2_count > 0:
        success_count += 1
    
    # S4 manifest: filter S2_CARD_IMAGE and S2_CARD_CONCEPT
    s4_s2_dst = target_dir / f"s4_image_manifest__arm{arm}__s2_card.jsonl"
    total_operations += 1
    s4_s2_count = filter_jsonl_by_spec_kind(
        s4_src,
        s4_s2_dst,
        {"S2_CARD_IMAGE", "S2_CARD_CONCEPT"},
        "S6-S2 S4 manifest (S2_CARD_IMAGE/CONCEPT)"
    )
    if s4_s2_count > 0:
        success_count += 1
    
    # Images: copy Q1 and Q2 images from images_regen/ to images/
    total_operations += 1
    img_s2_q1_count = copy_images_with_rename(
        src_images_dir,
        dst_images_dir,
        f"IMG__*__*__Q1_regen.jpg",
        "_regen",
        "S6-S2 images (Q1)"
    )
    if img_s2_q1_count > 0:
        success_count += 1
    
    total_operations += 1
    img_s2_q2_count = copy_images_with_rename(
        src_images_dir,
        dst_images_dir,
        f"IMG__*__*__Q2_regen.jpg",
        "_regen",
        "S6-S2 images (Q2)"
    )
    if img_s2_q2_count > 0:
        success_count += 1
    
    # Update image paths in S4 manifest
    if s4_s2_dst.exists():
        update_image_paths_in_manifest(
            s4_s2_dst,
            "_regen",
            "",
            source_dir,
            target_dir
        )
    
    # ============================================================
    # Summary
    # ============================================================
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"✅ Successful operations: {success_count} / {total_operations}")
    print(f"📁 Target directory: {target_dir}")
    print()
    print("Files created:")
    print(f"  - stage1_struct__arm{arm}.jsonl (S1R)")
    print(f"  - s2_results__s1arm{arm}__s2arm{arm}.jsonl (S2R)")
    print(f"  - s3_image_spec__arm{arm}__s1_visual.jsonl (S6-S1)")
    print(f"  - s4_image_manifest__arm{arm}__s1_visual.jsonl (S6-S1)")
    print(f"  - s3_image_spec__arm{arm}__s2_card.jsonl (S6-S2)")
    print(f"  - s4_image_manifest__arm{arm}__s2_card.jsonl (S6-S2)")
    print(f"  - images/ (copied regen images)")
    print()
    
    if success_count == total_operations:
        print("✅ All operations completed successfully!")
        return 0
    else:
        print(f"⚠️  Some operations failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    exit(main())


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Archive에서 복구 가능한 이미지 찾기 및 복구

S2 재생성 후, archive에 있는 이미지 중에서 새로 생성된 entity와 매칭되는 이미지를 찾아 복구합니다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# =========================
# Entity Normalization
# =========================

def normalize_entity_key(s: str) -> str:
    """Normalize entity names for matching (strip + remove asterisks)."""
    return re.sub(r"\*+", "", str(s or "")).strip()


# =========================
# Load S2 Results
# =========================

def load_s2_entities(s2_results_path: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Load entities from S2 results file, grouped by group_id.
    
    Args:
        s2_results_path: Path to S2 results JSONL file
    
    Returns:
        Dictionary mapping group_id to list of entity records
    """
    entities_by_group: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    if not s2_results_path.exists():
        return entities_by_group
    
    with open(s2_results_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                record = json.loads(line)
                group_id = record.get("group_id")
                entity_id = record.get("entity_id")
                entity_name = record.get("entity_name")
                
                if not group_id or not entity_id or not entity_name:
                    continue
                
                entities_by_group[group_id].append(record)
            except json.JSONDecodeError:
                continue
    
    return dict(entities_by_group)


# =========================
# Load Archived Images
# =========================

def load_archived_images(archive_dir: Path) -> List[Path]:
    """Load all image files from archive directory.
    
    Args:
        archive_dir: Path to archive directory containing unused images
    
    Returns:
        List of image file paths
    """
    if not archive_dir.exists():
        return []
    
    images = []
    for ext in ["jpg", "jpeg", "png"]:
        images.extend(list(archive_dir.glob(f"*.{ext}")))
    
    return images


def parse_image_filename(filename: str) -> Optional[Dict[str, str]]:
    """Parse image filename to extract metadata.
    
    Pattern: IMG__{run_tag}__{group_id}__{entity_id}__{card_role}.{ext}
    
    Args:
        filename: Image filename
    
    Returns:
        Dictionary with keys: run_tag, group_id, entity_id, card_role, ext
        or None if parsing fails
    """
    # Remove extension
    name_without_ext = filename.rsplit(".", 1)[0]
    ext = filename.rsplit(".", 1)[1] if "." in filename else ""
    
    # Split by double underscore
    parts = name_without_ext.split("__")
    if len(parts) < 5:
        return None
    
    # Pattern: IMG__{run_tag}__{group_id}__{entity_id}__{card_role}
    if parts[0] != "IMG":
        return None
    
    return {
        "run_tag": parts[1],
        "group_id": parts[2],
        "entity_id": parts[3],
        "card_role": parts[4],
        "ext": ext,
        "filename": filename
    }


# =========================
# Match Images to Entities
# =========================

def match_archived_images_to_entities(
    archived_images: List[Path],
    s2_entities_by_group: Dict[str, List[Dict[str, Any]]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Match archived images to current S2 entities.
    
    Args:
        archived_images: List of archived image file paths
        s2_entities_by_group: Dictionary mapping group_id to list of entity records
    
    Returns:
        Tuple of (recoverable_images, unmatched_images)
        - recoverable_images: List of dicts with image path and matching entity info
        - unmatched_images: List of dicts with image path and parsed metadata
    """
    recoverable_images = []
    unmatched_images = []
    
    # Create lookup map: (group_id, entity_id) -> entity record
    entity_lookup: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for group_id, entities in s2_entities_by_group.items():
        for entity in entities:
            entity_id = entity.get("entity_id", "")
            if entity_id:
                # Normalize entity_id: convert colon to underscore for matching
                entity_id_normalized = str(entity_id).replace(":", "_")
                key = (group_id, entity_id_normalized)
                entity_lookup[key] = entity
    
    # Also create lookup by normalized entity_name (fallback)
    entity_lookup_by_name: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for group_id, entities in s2_entities_by_group.items():
        for entity in entities:
            entity_name = entity.get("entity_name", "")
            entity_id = entity.get("entity_id", "")
            if entity_name and entity_id:
                normalized_name = normalize_entity_key(entity_name)
                key = (group_id, normalized_name)
                # Prefer exact entity_id match, but store name match as fallback
                if key not in entity_lookup_by_name:
                    entity_lookup_by_name[key] = entity
    
    # Match images
    for img_path in archived_images:
        parsed = parse_image_filename(img_path.name)
        if not parsed:
            unmatched_images.append({
                "image_path": str(img_path),
                "filename": img_path.name,
                "reason": "filename_parse_failed"
            })
            continue
        
        group_id = parsed["group_id"]
        entity_id_from_filename = parsed["entity_id"]  # Already normalized (underscore)
        card_role = parsed["card_role"]
        
        # Try exact match: (group_id, entity_id)
        key = (group_id, entity_id_from_filename)
        if key in entity_lookup:
            entity = entity_lookup[key]
            recoverable_images.append({
                "image_path": str(img_path),
                "filename": img_path.name,
                "group_id": group_id,
                "entity_id": entity.get("entity_id", ""),
                "entity_name": entity.get("entity_name", ""),
                "card_role": card_role,
                "match_type": "entity_id"
            })
            continue
        
        # Try group match and check if entity_name matches (fallback)
        # This is less reliable but might catch some cases
        entities_in_group = s2_entities_by_group.get(group_id, [])
        matched = False
        for entity in entities_in_group:
            entity_name = entity.get("entity_name", "")
            if entity_name:
                normalized_name = normalize_entity_key(entity_name)
                # Try to derive entity_id from entity_name and compare
                # This is approximate matching
                entity_id_actual = entity.get("entity_id", "")
                if entity_id_actual:
                    entity_id_normalized_actual = str(entity_id_actual).replace(":", "_")
                    # If the normalized IDs are similar, it might be a match
                    # But this is risky, so we'll be conservative
                    if entity_id_normalized_actual == entity_id_from_filename:
                        recoverable_images.append({
                            "image_path": str(img_path),
                            "filename": img_path.name,
                            "group_id": group_id,
                            "entity_id": entity_id_actual,
                            "entity_name": entity_name,
                            "card_role": card_role,
                            "match_type": "entity_id_normalized"
                        })
                        matched = True
                        break
        
        if not matched:
            unmatched_images.append({
                "image_path": str(img_path),
                "filename": img_path.name,
                "group_id": group_id,
                "entity_id_from_filename": entity_id_from_filename,
                "card_role": card_role,
                "reason": "no_matching_entity"
            })
    
    return recoverable_images, unmatched_images


# =========================
# Recover Images
# =========================

def recover_images(
    recoverable_images: List[Dict[str, Any]],
    images_dir: Path,
    archive_dir: Path,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Recover images from archive to images directory.
    
    Args:
        recoverable_images: List of recoverable image info dicts
        images_dir: Target images directory
        archive_dir: Source archive directory
        dry_run: If True, don't actually move files
    
    Returns:
        Dictionary with recovery statistics
    """
    import shutil
    
    images_dir.mkdir(parents=True, exist_ok=True)
    
    recovered_count = 0
    failed_count = 0
    recovered_files = []
    
    for img_info in recoverable_images:
        src_path = Path(img_info["image_path"])
        dest_path = images_dir / img_info["filename"]
        
        if not src_path.exists():
            failed_count += 1
            continue
        
        if dest_path.exists():
            # Image already exists in target directory
            recovered_files.append({
                "filename": img_info["filename"],
                "status": "already_exists",
                "source": str(src_path.relative_to(archive_dir.parent.parent.parent.parent)),
                "destination": str(dest_path.relative_to(images_dir.parent.parent.parent.parent))
            })
            continue
        
        if dry_run:
            recovered_files.append({
                "filename": img_info["filename"],
                "status": "would_recover",
                "source": str(src_path.relative_to(archive_dir.parent.parent.parent.parent)),
                "destination": str(dest_path.relative_to(images_dir.parent.parent.parent.parent))
            })
            recovered_count += 1
        else:
            try:
                shutil.move(str(src_path), str(dest_path))
                recovered_files.append({
                    "filename": img_info["filename"],
                    "status": "recovered",
                    "source": str(src_path.relative_to(archive_dir.parent.parent.parent.parent)),
                    "destination": str(dest_path.relative_to(images_dir.parent.parent.parent.parent)),
                    "size_bytes": dest_path.stat().st_size
                })
                recovered_count += 1
            except Exception as e:
                failed_count += 1
                recovered_files.append({
                    "filename": img_info["filename"],
                    "status": "failed",
                    "error": str(e)
                })
    
    return {
        "recovered_count": recovered_count,
        "failed_count": failed_count,
        "already_exists_count": sum(1 for f in recovered_files if f.get("status") == "already_exists"),
        "recovered_files": recovered_files
    }


# =========================
# Report Generation
# =========================

def generate_recovery_report(
    recovery_result: Dict[str, Any],
    recoverable_images: List[Dict[str, Any]],
    unmatched_images: List[Dict[str, Any]],
    output_path: Path,
    run_tag: str,
    arm: str
) -> None:
    """Generate recovery report.
    
    Args:
        recovery_result: Result dictionary from recover_images()
        recoverable_images: List of recoverable image info
        unmatched_images: List of unmatched image info
        output_path: Path to output markdown report file
        arm: Arm identifier
    """
    lines = []
    lines.append(f"# Archive 이미지 복구 리포트")
    lines.append("")
    lines.append(f"**생성일**: {recovery_result.get('generated_at', 'N/A')}")
    lines.append(f"**RUN_TAG**: `{run_tag}`")
    lines.append(f"**ARM**: `{arm}`")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Summary statistics
    lines.append("## 1. 요약 통계")
    lines.append("")
    lines.append(f"- **Archive 이미지 총 수**: {len(recoverable_images) + len(unmatched_images)}")
    lines.append(f"- **복구 가능한 이미지**: {len(recoverable_images)}")
    lines.append(f"- **매칭되지 않은 이미지**: {len(unmatched_images)}")
    lines.append(f"- **실제 복구된 이미지**: {recovery_result['recovered_count']}")
    lines.append(f"- **이미 존재하는 이미지**: {recovery_result['already_exists_count']}")
    lines.append(f"- **복구 실패**: {recovery_result['failed_count']}")
    lines.append("")
    
    # Recoverable images by match type
    if recoverable_images:
        lines.append("## 2. 복구 가능한 이미지 상세")
        lines.append("")
        match_type_counts = defaultdict(int)
        for img in recoverable_images:
            match_type = img.get("match_type", "unknown")
            match_type_counts[match_type] += 1
        
        lines.append("### 매칭 타입별 통계")
        lines.append("")
        for match_type, count in sorted(match_type_counts.items()):
            lines.append(f"- **{match_type}**: {count}개")
        lines.append("")
        
        # Group by entity
        by_entity = defaultdict(list)
        for img in recoverable_images:
            entity_id = img.get("entity_id", "")
            entity_name = img.get("entity_name", "")
            key = f"{entity_id} ({entity_name})"
            by_entity[key].append(img)
        
        lines.append(f"### Entity별 복구 가능한 이미지 (총 {len(by_entity)}개 entity)")
        lines.append("")
        lines.append("| Entity ID | Entity Name | 이미지 수 | Card Role |")
        lines.append("|-----------|------------|----------|-----------|")
        for entity_key, imgs in sorted(by_entity.items()):
            entity_id = imgs[0].get("entity_id", "")
            entity_name = imgs[0].get("entity_name", "")
            card_roles = sorted(set(img.get("card_role", "") for img in imgs))
            lines.append(f"| `{entity_id[:20]}...` | {entity_name[:30]}... | {len(imgs)} | {', '.join(card_roles)} |")
        lines.append("")
    
    # Unmatched images summary
    if unmatched_images:
        lines.append("## 3. 매칭되지 않은 이미지 요약")
        lines.append("")
        lines.append(f"총 {len(unmatched_images)}개의 이미지가 현재 S2 entity와 매칭되지 않습니다.")
        lines.append("")
        
        # Group by reason
        by_reason = defaultdict(list)
        for img in unmatched_images:
            reason = img.get("reason", "unknown")
            by_reason[reason].append(img)
        
        lines.append("### 이유별 분류")
        lines.append("")
        for reason, imgs in sorted(by_reason.items()):
            lines.append(f"- **{reason}**: {len(imgs)}개")
        lines.append("")
    
    # Recovery results
    lines.append("## 4. 복구 결과")
    lines.append("")
    if recovery_result['recovered_count'] > 0:
        lines.append(f"✅ {recovery_result['recovered_count']}개의 이미지가 archive에서 복구되었습니다.")
    if recovery_result['already_exists_count'] > 0:
        lines.append(f"ℹ️  {recovery_result['already_exists_count']}개의 이미지는 이미 images 디렉토리에 존재합니다.")
    if recovery_result['failed_count'] > 0:
        lines.append(f"❌ {recovery_result['failed_count']}개의 이미지 복구에 실패했습니다.")
    lines.append("")
    
    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# =========================
# Main Entry Point
# =========================

def main():
    """Main entry point for image recovery from archive."""
    parser = argparse.ArgumentParser(
        description="Recover images from archive that match current S2 entities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python recover_images_from_archive.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G

  # Dry run to preview
  python recover_images_from_archive.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G --dry_run
        """
    )
    parser.add_argument(
        "--base_dir",
        type=str,
        required=True,
        help="Project root directory"
    )
    parser.add_argument(
        "--run_tag",
        type=str,
        required=True,
        help="Run tag (e.g., FINAL_DISTRIBUTION)"
    )
    parser.add_argument(
        "--arm",
        type=str,
        required=True,
        help="Arm identifier (e.g., G)"
    )
    parser.add_argument(
        "--s2_results_path",
        type=str,
        help="Path to S2 results file (optional, auto-detected if not provided)"
    )
    parser.add_argument(
        "--archive_dir",
        type=str,
        help="Path to archive directory (optional, auto-detected if not provided)"
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Don't actually move files, just simulate"
    )
    
    args = parser.parse_args()
    
    # Validate and resolve base directory
    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        print(f"Error: Base directory does not exist: {base_dir}", file=sys.stderr)
        return 1
    
    run_tag = args.run_tag.strip()
    arm = args.arm.strip().upper()
    
    # Determine paths
    gen_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    
    # Resolve S2 results path
    if args.s2_results_path:
        s2_results_path = Path(args.s2_results_path)
        if not s2_results_path.is_absolute():
            s2_results_path = base_dir / s2_results_path
        s2_results_path = s2_results_path.resolve()
    else:
        # Try to use path_resolver if available, otherwise fall back to default
        try:
            sys.path.insert(0, str(base_dir / "3_Code" / "src"))
            from tools.path_resolver import resolve_s2_results_path
            s2_results_path = resolve_s2_results_path(gen_dir, arm, s1_arm=arm)
        except ImportError:
            # Fallback: use default path pattern
            s2_results_path = gen_dir / f"s2_results__s1arm{arm}__s2arm{arm}.jsonl"
    
    # Resolve archive directory
    if args.archive_dir:
        archive_dir = Path(args.archive_dir)
        if not archive_dir.is_absolute():
            archive_dir = base_dir / archive_dir
        archive_dir = archive_dir.resolve()
    else:
        archive_dir = gen_dir / "archive" / "unused_images"
    
    # Resolve images directory
    images_dir = gen_dir / "images"
    
    # Validate paths
    if not s2_results_path.exists():
        print(f"Error: S2 results file not found: {s2_results_path}", file=sys.stderr)
        return 1
    
    if not archive_dir.exists():
        print(f"Error: Archive directory not found: {archive_dir}", file=sys.stderr)
        print(f"  No archived images to recover.", file=sys.stderr)
        return 1
    
    # Print configuration
    print("=" * 70)
    print("Archive Image Recovery")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Arm: {arm}")
    print(f"S2 results: {s2_results_path}")
    print(f"Archive directory: {archive_dir}")
    print(f"Images directory: {images_dir}")
    print(f"Dry run: {args.dry_run}")
    print("=" * 70)
    print()
    
    # Load S2 entities
    print("Loading S2 entities...")
    s2_entities_by_group = load_s2_entities(s2_results_path)
    total_entities = sum(len(entities) for entities in s2_entities_by_group.values())
    print(f"  Loaded {total_entities} entities from {len(s2_entities_by_group)} groups")
    
    # Load archived images
    print("Loading archived images...")
    archived_images = load_archived_images(archive_dir)
    print(f"  Found {len(archived_images)} archived images")
    
    # Match images to entities
    print("Matching images to entities...")
    recoverable_images, unmatched_images = match_archived_images_to_entities(
        archived_images, s2_entities_by_group
    )
    print(f"  Recoverable: {len(recoverable_images)}")
    print(f"  Unmatched: {len(unmatched_images)}")
    
    # Recover images
    print("Recovering images...")
    from datetime import datetime
    recovery_result = recover_images(
        recoverable_images, images_dir, archive_dir, dry_run=args.dry_run
    )
    recovery_result["generated_at"] = datetime.now().isoformat()
    
    # Generate report
    report_path = gen_dir / f"archive_image_recovery_report__arm{arm}.md"
    generate_recovery_report(
        recovery_result, recoverable_images, unmatched_images,
        report_path, run_tag, arm
    )
    
    # Save detailed results
    results_path = gen_dir / f"archive_image_recovery_results__arm{arm}.jsonl"
    with open(results_path, "w", encoding="utf-8") as f:
        for img in recoverable_images:
            f.write(json.dumps(img, ensure_ascii=False) + "\n")
    
    # Print summary
    print("\n" + "=" * 70)
    if args.dry_run:
        print("Dry Run Complete!")
    else:
        print("Recovery Complete!")
    print("=" * 70)
    print(f"✅ Recoverable images: {len(recoverable_images)}")
    print(f"📦 Recovered: {recovery_result['recovered_count']}")
    print(f"ℹ️  Already exists: {recovery_result['already_exists_count']}")
    print(f"❌ Failed: {recovery_result['failed_count']}")
    print(f"⚠️  Unmatched: {len(unmatched_images)}")
    print()
    print("Output files:")
    print(f"  📄 Report: {report_path}")
    print(f"  📋 Results: {results_path}")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


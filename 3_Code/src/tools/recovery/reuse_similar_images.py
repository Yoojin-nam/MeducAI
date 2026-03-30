#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
이미지 재사용 스크립트

유사한 entity의 이미지를 찾아 재사용하고, Archive에서 복구 가능한 이미지를 복구합니다.
유사도 매칭 결과를 기반으로 이미지 파일명을 변경하고 재사용합니다.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# =========================
# Image Filename Parsing
# =========================

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


def normalize_entity_id_for_filename(entity_id: str) -> str:
    """Normalize entity_id for use in filename (replace colons with underscores).
    
    Args:
        entity_id: Entity ID (may contain colons)
    
    Returns:
        Normalized entity ID for filename
    """
    return str(entity_id).replace(":", "_")


def build_image_filename(
    run_tag: str,
    group_id: str,
    entity_id: str,
    card_role: str,
    ext: str = "png"
) -> str:
    """Build image filename from components.
    
    Args:
        run_tag: Run tag
        group_id: Group ID
        entity_id: Entity ID (will be normalized)
        card_role: Card role (Q1, Q2, etc.)
        ext: File extension
    
    Returns:
        Image filename
    """
    normalized_entity_id = normalize_entity_id_for_filename(entity_id)
    return f"IMG__{run_tag}__{group_id}__{normalized_entity_id}__{card_role}.{ext}"


# =========================
# Load Similarity Matches
# =========================

def load_similarity_matches(matches_path: Path) -> List[Dict[str, Any]]:
    """Load similarity matches from JSONL file.
    
    Args:
        matches_path: Path to similarity matches JSONL file
    
    Returns:
        List of match records
    """
    matches = []
    
    if not matches_path.exists():
        return matches
    
    with open(matches_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                record = json.loads(line)
                matches.append(record)
            except json.JSONDecodeError:
                continue
    
    return matches


# =========================
# Find Images for Entities
# =========================

def find_images_for_entity(
    images_dir: Path,
    run_tag: str,
    entity_id: str,
    card_roles: List[str] = ["Q1", "Q2"]
) -> List[Path]:
    """Find all images for a given entity_id.
    
    Args:
        images_dir: Images directory
        entity_id: Entity ID to search for
        card_roles: List of card roles to search (default: Q1, Q2)
    
    Returns:
        List of image file paths
    """
    if not images_dir.exists():
        return []
    
    normalized_entity_id = normalize_entity_id_for_filename(entity_id)
    found_images = []
    
    # Search for images matching the entity_id pattern
    # Pattern: IMG__{run_tag}__*__{entity_id}__{card_role}.{ext}
    for ext in ["png", "jpg", "jpeg"]:
        for card_role in card_roles:
            # Try exact match first
            pattern = f"IMG__{run_tag}__*__{normalized_entity_id}__{card_role}.{ext}"
            found_images.extend(images_dir.glob(pattern))
            
            # Also try with case variations
            pattern_upper = f"IMG__{run_tag}__*__{normalized_entity_id}__{card_role.upper()}.{ext}"
            if pattern_upper != pattern:
                found_images.extend(images_dir.glob(pattern_upper))
            pattern_lower = f"IMG__{run_tag}__*__{normalized_entity_id}__{card_role.lower()}.{ext}"
            if pattern_lower != pattern:
                found_images.extend(images_dir.glob(pattern_lower))
    
    # Also search in archive if it exists
    archive_dir = images_dir.parent / "archive" / "unused_images"
    if archive_dir.exists():
        for ext in ["png", "jpg", "jpeg"]:
            for card_role in card_roles:
                pattern = f"IMG__{run_tag}__*__{normalized_entity_id}__{card_role}.{ext}"
                found_images.extend(archive_dir.glob(pattern))
    
    return list(set(found_images))  # Remove duplicates


def find_archived_images_for_entity(
    archive_dir: Path,
    run_tag: str,
    entity_id: str,
    card_roles: List[str] = ["Q1", "Q2"]
) -> List[Path]:
    """Find archived images for a given entity_id.
    
    Args:
        archive_dir: Archive directory
        entity_id: Entity ID to search for
        card_roles: List of card roles to search (default: Q1, Q2)
    
    Returns:
        List of archived image file paths
    """
    if not archive_dir.exists():
        return []
    
    normalized_entity_id = normalize_entity_id_for_filename(entity_id)
    found_images = []
    
    for ext in ["png", "jpg", "jpeg"]:
        for card_role in card_roles:
            pattern = f"IMG__{run_tag}__*__{normalized_entity_id}__{card_role}.{ext}"
            found_images.extend(archive_dir.glob(pattern))
    
    return list(set(found_images))  # Remove duplicates


# =========================
# Image Reuse Processing
# =========================

def process_image_reuse(
    matches: List[Dict[str, Any]],
    images_dir: Path,
    archive_dir: Path,
    run_tag: str,
    similarity_threshold: float = 0.95,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Process image reuse for similar entities.
    
    Args:
        matches: List of similarity match records
        images_dir: Target images directory
        archive_dir: Archive directory containing unused images
        run_tag: Run tag
        similarity_threshold: Minimum similarity for auto-reuse (default: 0.95)
        dry_run: If True, don't actually move/rename files
    
    Returns:
        Dictionary with processing statistics and results
    """
    images_dir.mkdir(parents=True, exist_ok=True)
    
    reuse_mappings = []
    reused_images = []
    recovered_images = []
    failed_operations = []
    
    # Filter matches by similarity threshold
    auto_reuse_matches = [m for m in matches if m.get("similarity", 0.0) >= similarity_threshold]
    
    print(f"Processing {len(auto_reuse_matches)} matches with similarity >= {similarity_threshold}")
    
    for match in auto_reuse_matches:
        backup_entity_id = match.get("backup_entity_id", "")
        s1_entity_id = match.get("s1_entity_id", "")
        similarity = match.get("similarity", 0.0)
        backup_entity_name = match.get("backup_entity_name", "")
        s1_entity_name = match.get("s1_entity_name", "")
        
        if not backup_entity_id or not s1_entity_id:
            continue
        
        # Find images for backup entity
        backup_images = find_images_for_entity(images_dir, run_tag, backup_entity_id)
        archived_images = find_archived_images_for_entity(archive_dir, run_tag, backup_entity_id)
        
        # Process images in images_dir
        for img_path in backup_images:
            parsed = parse_image_filename(img_path.name)
            if not parsed:
                continue
            
            group_id = parsed["group_id"]
            card_role = parsed["card_role"]
            ext = parsed["ext"]
            
            # Build new filename with s1_entity_id
            new_filename = build_image_filename(run_tag, group_id, s1_entity_id, card_role, ext)
            new_path = images_dir / new_filename
            
            # Skip if source and destination are the same
            if img_path == new_path:
                continue
            
            reuse_mapping = {
                "backup_entity_id": backup_entity_id,
                "backup_entity_name": backup_entity_name,
                "s1_entity_id": s1_entity_id,
                "s1_entity_name": s1_entity_name,
                "group_id": group_id,
                "card_role": card_role,
                "similarity": similarity,
                "old_filename": img_path.name,
                "new_filename": new_filename,
                "old_path": str(img_path),
                "new_path": str(new_path),
                "source": "images_dir"
            }
            
            if new_path.exists():
                reuse_mapping["status"] = "target_exists"
                reuse_mapping["action"] = "skipped"
            elif dry_run:
                reuse_mapping["status"] = "would_rename"
                reuse_mapping["action"] = "dry_run"
                reused_images.append(reuse_mapping)
            else:
                try:
                    shutil.move(str(img_path), str(new_path))
                    reuse_mapping["status"] = "renamed"
                    reuse_mapping["action"] = "moved"
                    reuse_mapping["size_bytes"] = new_path.stat().st_size
                    reused_images.append(reuse_mapping)
                except Exception as e:
                    reuse_mapping["status"] = "failed"
                    reuse_mapping["action"] = "error"
                    reuse_mapping["error"] = str(e)
                    failed_operations.append(reuse_mapping)
            
            reuse_mappings.append(reuse_mapping)
        
        # Process archived images
        for img_path in archived_images:
            parsed = parse_image_filename(img_path.name)
            if not parsed:
                continue
            
            group_id = parsed["group_id"]
            card_role = parsed["card_role"]
            ext = parsed["ext"]
            
            # Build new filename with s1_entity_id
            new_filename = build_image_filename(run_tag, group_id, s1_entity_id, card_role, ext)
            new_path = images_dir / new_filename
            
            reuse_mapping = {
                "backup_entity_id": backup_entity_id,
                "backup_entity_name": backup_entity_name,
                "s1_entity_id": s1_entity_id,
                "s1_entity_name": s1_entity_name,
                "group_id": group_id,
                "card_role": card_role,
                "similarity": similarity,
                "old_filename": img_path.name,
                "new_filename": new_filename,
                "old_path": str(img_path),
                "new_path": str(new_path),
                "source": "archive"
            }
            
            if new_path.exists():
                reuse_mapping["status"] = "target_exists"
                reuse_mapping["action"] = "skipped"
            elif dry_run:
                reuse_mapping["status"] = "would_recover"
                reuse_mapping["action"] = "dry_run"
                recovered_images.append(reuse_mapping)
            else:
                try:
                    shutil.move(str(img_path), str(new_path))
                    reuse_mapping["status"] = "recovered"
                    reuse_mapping["action"] = "moved"
                    reuse_mapping["size_bytes"] = new_path.stat().st_size
                    recovered_images.append(reuse_mapping)
                except Exception as e:
                    reuse_mapping["status"] = "failed"
                    reuse_mapping["action"] = "error"
                    reuse_mapping["error"] = str(e)
                    failed_operations.append(reuse_mapping)
            
            reuse_mappings.append(reuse_mapping)
    
    # Calculate statistics
    stats = {
        "total_matches_processed": len(auto_reuse_matches),
        "total_mappings": len(reuse_mappings),
        "reused_from_images": len([m for m in reuse_mappings if m.get("source") == "images_dir" and m.get("status") in ["renamed", "would_rename"]]),
        "recovered_from_archive": len([m for m in reuse_mappings if m.get("source") == "archive" and m.get("status") in ["recovered", "would_recover"]]),
        "target_exists": len([m for m in reuse_mappings if m.get("status") == "target_exists"]),
        "failed": len(failed_operations),
        "similarity_threshold": similarity_threshold
    }
    
    return {
        "stats": stats,
        "mappings": reuse_mappings,
        "reused_images": reused_images,
        "recovered_images": recovered_images,
        "failed_operations": failed_operations,
        "generated_at": datetime.now().isoformat()
    }


# =========================
# Report Generation
# =========================

def generate_reuse_report(
    result: Dict[str, Any],
    output_path: Path,
    run_tag: str,
    arm: str
) -> None:
    """Generate image reuse report.
    
    Args:
        result: Result dictionary from process_image_reuse()
        output_path: Path to output markdown report file
        run_tag: Run tag
        arm: Arm identifier
    """
    lines = []
    lines.append("# 이미지 재사용 리포트")
    lines.append("")
    lines.append(f"**생성일**: {result.get('generated_at', 'N/A')}")
    lines.append(f"**RUN_TAG**: `{run_tag}`")
    lines.append(f"**ARM**: `{arm}`")
    lines.append(f"**유사도 임계값**: {result['stats']['similarity_threshold']}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Summary statistics
    stats = result["stats"]
    lines.append("## 1. 요약 통계")
    lines.append("")
    lines.append(f"- **처리된 매칭 수**: {stats['total_matches_processed']}")
    lines.append(f"- **총 이미지 매핑 수**: {stats['total_mappings']}")
    lines.append(f"- **images 디렉토리에서 재사용**: {stats['reused_from_images']}")
    lines.append(f"- **archive에서 복구**: {stats['recovered_from_archive']}")
    lines.append(f"- **대상 이미지 이미 존재**: {stats['target_exists']}")
    lines.append(f"- **실패**: {stats['failed']}")
    lines.append("")
    
    # Group by entity
    by_entity = defaultdict(list)
    for mapping in result["mappings"]:
        key = f"{mapping.get('s1_entity_id', '')} ({mapping.get('s1_entity_name', '')})"
        by_entity[key].append(mapping)
    
    if by_entity:
        lines.append("## 2. Entity별 재사용 상세")
        lines.append("")
        lines.append(f"총 {len(by_entity)}개 entity의 이미지가 재사용되었습니다.")
        lines.append("")
        lines.append("| Entity ID | Entity Name | 재사용 이미지 수 | Card Role |")
        lines.append("|-----------|------------|-----------------|-----------|")
        for entity_key, mappings in sorted(by_entity.items()):
            entity_id = mappings[0].get("s1_entity_id", "")
            entity_name = mappings[0].get("s1_entity_name", "")
            card_roles = sorted(set(m.get("card_role", "") for m in mappings))
            reused_count = len([m for m in mappings if m.get("status") in ["renamed", "recovered", "would_rename", "would_recover"]])
            lines.append(f"| `{entity_id[:30]}...` | {entity_name[:40]}... | {reused_count} | {', '.join(card_roles)} |")
        lines.append("")
    
    # Failed operations
    if result["failed_operations"]:
        lines.append("## 3. 실패한 작업")
        lines.append("")
        lines.append(f"총 {len(result['failed_operations'])}개의 작업이 실패했습니다.")
        lines.append("")
        for failed in result["failed_operations"][:20]:  # Limit to first 20
            lines.append(f"- **{failed.get('old_filename', '')}**: {failed.get('error', 'Unknown error')}")
        if len(result["failed_operations"]) > 20:
            lines.append(f"\n... and {len(result['failed_operations']) - 20} more failures")
        lines.append("")
    
    # Next steps
    lines.append("## 4. 다음 단계")
    lines.append("")
    lines.append("### 재사용된 이미지")
    lines.append("")
    lines.append(f"- images 디렉토리에서 재사용: {stats['reused_from_images']}개")
    lines.append(f"- archive에서 복구: {stats['recovered_from_archive']}개")
    lines.append("")
    lines.append("### 매핑 파일")
    lines.append("")
    lines.append("상세 매핑 정보는 `s2_image_reuse_mapping__arm{arm}.jsonl` 파일에 저장되었습니다.")
    lines.append("")
    
    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# =========================
# Main Entry Point
# =========================

def main():
    """Main entry point for image reuse."""
    parser = argparse.ArgumentParser(
        description="Reuse images for similar entities based on similarity matching",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python reuse_similar_images.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G

  # Dry run to preview
  python reuse_similar_images.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G --dry_run

  # Custom similarity threshold
  python reuse_similar_images.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G \\
    --similarity_threshold 0.97
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
        "--similarity_threshold",
        type=float,
        default=0.95,
        help="Minimum similarity score for auto-reuse (default: 0.95)"
    )
    parser.add_argument(
        "--similarity_matches_path",
        type=str,
        help="Path to similarity matches file (optional, auto-detected if not provided)"
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Don't actually move/rename files, just simulate"
    )
    
    args = parser.parse_args()
    
    # Validate and resolve base directory
    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        print(f"Error: Base directory does not exist: {base_dir}", file=sys.stderr)
        return 1
    
    run_tag = args.run_tag.strip()
    arm = args.arm.strip().upper()
    similarity_threshold = args.similarity_threshold
    
    if similarity_threshold < 0.0 or similarity_threshold > 1.0:
        print("Error: --similarity_threshold must be between 0.0 and 1.0", file=sys.stderr)
        return 1
    
    # Determine paths
    gen_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    images_dir = gen_dir / "images"
    archive_dir = gen_dir / "archive" / "unused_images"
    
    # Resolve similarity matches path
    if args.similarity_matches_path:
        similarity_matches_path = Path(args.similarity_matches_path)
        if not similarity_matches_path.is_absolute():
            similarity_matches_path = base_dir / similarity_matches_path
        similarity_matches_path = similarity_matches_path.resolve()
    else:
        similarity_matches_path = gen_dir / f"s2_similarity_matches__arm{arm}.jsonl"
    
    if not similarity_matches_path.exists():
        print(f"Error: Similarity matches file not found: {similarity_matches_path}", file=sys.stderr)
        print(f"  Please run match_similar_entities.py first.", file=sys.stderr)
        return 1
    
    # Output paths
    output_mapping_path = gen_dir / f"s2_image_reuse_mapping__arm{arm}.jsonl"
    output_report_path = gen_dir / f"s2_image_reuse_report__arm{arm}.md"
    
    # Print configuration
    print("=" * 70)
    print("Image Reuse for Similar Entities")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Arm: {arm}")
    print(f"Similarity matches: {similarity_matches_path}")
    print(f"Images directory: {images_dir}")
    print(f"Archive directory: {archive_dir}")
    print(f"Similarity threshold: {similarity_threshold}")
    print(f"Dry run: {args.dry_run}")
    print(f"Output mapping: {output_mapping_path}")
    print(f"Output report: {output_report_path}")
    print("=" * 70)
    print()
    
    # Load similarity matches
    print("Loading similarity matches...")
    matches = load_similarity_matches(similarity_matches_path)
    print(f"  Loaded {len(matches)} matches")
    
    if not matches:
        print("Error: No similarity matches found.", file=sys.stderr)
        return 1
    
    # Process image reuse
    print("Processing image reuse...")
    try:
        result = process_image_reuse(
            matches=matches,
            images_dir=images_dir,
            archive_dir=archive_dir,
            run_tag=run_tag,
            similarity_threshold=similarity_threshold,
            dry_run=args.dry_run
        )
    except Exception as e:
        print(f"Error during processing: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    
    # Save mapping file
    output_mapping_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_mapping_path, "w", encoding="utf-8") as f:
        for mapping in result["mappings"]:
            f.write(json.dumps(mapping, ensure_ascii=False) + "\n")
    
    # Generate report
    generate_reuse_report(result, output_report_path, run_tag, arm)
    
    # Print summary
    print("\n" + "=" * 70)
    if args.dry_run:
        print("Dry Run Complete!")
    else:
        print("Image Reuse Complete!")
    print("=" * 70)
    stats = result["stats"]
    print(f"✅ Processed matches: {stats['total_matches_processed']}")
    print(f"✅ Total mappings: {stats['total_mappings']}")
    print(f"📦 Reused from images: {stats['reused_from_images']}")
    print(f"📦 Recovered from archive: {stats['recovered_from_archive']}")
    print(f"ℹ️  Target exists: {stats['target_exists']}")
    if stats['failed'] > 0:
        print(f"❌ Failed: {stats['failed']}")
    print()
    print("Output files:")
    print(f"  📄 Mapping: {output_mapping_path}")
    print(f"  📊 Report: {output_report_path}")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S2 백업 기반 복원 스크립트

백업된 S2 데이터를 entity_id 기반으로 복원하여 S2 결과 파일 재구성.
새 entity_list와 비교하여 누락된 entity 식별.
재사용된 entity에 해당하는 기존 S4 이미지 파일 매핑 기록.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# =========================
# Entity Normalization
# =========================

def normalize_entity_key(s: str) -> str:
    """Normalize entity names for matching (strip + remove asterisks).
    
    This function matches the behavior of _normalize_entity_key in 01_generate_json.py.
    """
    return re.sub(r"\*+", "", str(s or "")).strip()


# =========================
# Phase 2: Backup File Detection
# =========================

def find_backup_file(s2_results_path: Path) -> Optional[Path]:
    """Find the most recent backup file for s2_results_path.
    
    Searches for files matching pattern: s2_results__*.jsonl.backup_*
    Returns the most recent backup based on timestamp in filename.
    
    Args:
        s2_results_path: Path to the S2 results file (e.g., s2_results__s1armG__s2armG.jsonl)
    
    Returns:
        Path to the most recent backup file, or None if no backup found
    """
    backup_dir = s2_results_path.parent
    
    # Get base name - handle both .jsonl and potential extensions
    if s2_results_path.suffix == '.jsonl':
        base_name = s2_results_path.stem  # e.g., "s2_results__s1armG__s2armG"
    else:
        # If no .jsonl extension, use the full name
        base_name = s2_results_path.name
    
    # Pattern: s2_results__*.jsonl.backup_YYYYMMDD_HHMMSS
    # Also try: s2_results__*.backup_* (in case extension is already in base_name)
    backup_patterns = [
        f"{base_name}.backup_*",
        f"{base_name}.jsonl.backup_*",
    ]
    
    backup_files = []
    for pattern in backup_patterns:
        backup_files.extend(backup_dir.glob(pattern))
    
    if not backup_files:
        return None
    
    # Sort by modification time (most recent first)
    backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    return backup_files[0]


# =========================
# Phase 3: Backup Entity Loading
# =========================

def load_backup_entities(backup_file: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Load entities from backup file, grouped by group_id.
    
    Each entity record in the backup file contains:
    - schema_version
    - group_id
    - entity_id
    - entity_name
    - cards_for_entity_exact
    - anki_cards
    - integrity
    - (other fields)
    
    Args:
        backup_file: Path to the backup JSONL file
    
    Returns:
        Dictionary mapping group_id to list of entity records
    """
    entities_by_group: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    if not backup_file.exists():
        return entities_by_group
    
    with open(backup_file, "r", encoding="utf-8") as f:
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
                
                # Store the full record
                entities_by_group[group_id].append(record)
            except json.JSONDecodeError:
                # Skip malformed lines
                continue
    
    return dict(entities_by_group)


# =========================
# Phase 4: S1 Entity List Loading
# =========================

def load_s1_entity_list(s1_struct_path: Path, group_id: str) -> List[Dict[str, str]]:
    """Load entity_list from S1 structure for a specific group.
    
    The S1 structure file is a JSONL file where each line is a group record.
    Each record contains an entity_list array with objects like:
    {
        "entity_id": "...",
        "entity_name": "..."
    }
    
    This function matches the behavior of _normalize_entity_list in 01_generate_json.py,
    returning the canonical format: [{"entity_id": "...", "entity_name": "..."}]
    
    Args:
        s1_struct_path: Path to stage1_struct__arm*.jsonl file
        group_id: The group_id to find
    
    Returns:
        List of entity objects with entity_id and entity_name keys
    """
    if not s1_struct_path.exists():
        return []
    
    with open(s1_struct_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                record = json.loads(line)
                if record.get("group_id") == group_id:
                    entity_list_raw = record.get("entity_list", [])
                    return _normalize_entity_list(entity_list_raw)
            except json.JSONDecodeError:
                continue
    
    return []


def _normalize_entity_list(raw: Any) -> List[Dict[str, str]]:
    """Normalize Stage1 entity_list into a list of objects.
    
    Canonical object shape (minimum):
      {"entity_id": <str>, "entity_name": <str>}
    
    This function matches the behavior of _normalize_entity_list in 01_generate_json.py.
    
    Backward compatibility:
      - If raw entries are strings, we deterministically derive entity_id using the
        stabilization rule (DERIVED:sha1(normalized_name)[:12]).
      - If raw entries are dicts, we accept keys:
          entity_id / id, entity_name / name
        and derive missing entity_id when needed.
    
    We de-duplicate by entity_id while preserving order.
    """
    import hashlib
    
    if not isinstance(raw, list):
        return []
    
    out: List[Dict[str, str]] = []
    seen_ids: set[str] = set()
    
    def _derive(name: str) -> str:
        norm = re.sub(r"\s+", " ", str(name).strip().lower())
        h = hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]
        return f"DERIVED:{h}"
    
    for item in raw:
        if isinstance(item, dict):
            name = str(item.get("entity_name") or item.get("name") or "").strip()
            eid = str(item.get("entity_id") or item.get("id") or "").strip()
            
            if not name:
                continue
            
            if not eid:
                eid = _derive(name)
            
            if eid not in seen_ids:
                seen_ids.add(eid)
                out.append({"entity_id": eid, "entity_name": name})
        elif isinstance(item, str):
            name = str(item).strip()
            if name:
                eid = _derive(name)
                if eid not in seen_ids:
                    seen_ids.add(eid)
                    out.append({"entity_id": eid, "entity_name": name})
    
    return out


# =========================
# Phase 5: Entity Comparison
# =========================

def compare_entities(
    backup_entities: List[Dict[str, Any]],
    new_entity_list: List[Dict[str, str]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """Compare entities between backup and new entity_list.
    
    Matches entities based on:
    - entity_id (exact match)
    - normalized_entity_name (fallback if entity_id differs)
    
    Args:
        backup_entities: List of entity records from backup (full S2 records)
        new_entity_list: List of new entity objects from S1 structure
            Format: [{"entity_id": "...", "entity_name": "..."}]
    
    Returns:
        Tuple of (reusable_entities, missing_entities)
        - reusable_entities: List of backup entity records that match new entity_list
        - missing_entities: List of new entity objects not found in backup
            Format: [{"entity_id": "...", "entity_name": "..."}]
    """
    reusable_entities = []
    missing_entities = []
    
    # Create lookup maps from backup entities
    backup_by_id: Dict[str, Dict[str, Any]] = {}
    backup_by_name: Dict[str, Dict[str, Any]] = {}
    
    for backup_ent in backup_entities:
        entity_id = backup_ent.get("entity_id", "")
        entity_name = backup_ent.get("entity_name", "")
        
        if entity_id:
            backup_by_id[entity_id] = backup_ent
        
        # Also index by normalized name for fallback matching
        if entity_name:
            normalized_name = normalize_entity_key(entity_name)
            if normalized_name:
                # If multiple entities have the same normalized name, keep the first one
                if normalized_name not in backup_by_name:
                    backup_by_name[normalized_name] = backup_ent
    
    # Check each new entity
    matched_backup_ids = set()
    
    for new_ent in new_entity_list:
        entity_id = new_ent.get("entity_id", "")
        entity_name = new_ent.get("entity_name", "")
        normalized_name = normalize_entity_key(entity_name) if entity_name else ""
        
        matched = False
        
        # First try: match by entity_id (exact match)
        if entity_id and entity_id in backup_by_id:
            backup_ent = backup_by_id[entity_id]
            reusable_entities.append(backup_ent)
            matched_backup_ids.add(entity_id)
            matched = True
        # Second try: match by normalized entity_name (fallback)
        elif normalized_name and normalized_name in backup_by_name:
            backup_ent = backup_by_name[normalized_name]
            backup_id = backup_ent.get("entity_id", "")
            # Only use if not already matched by ID
            if backup_id not in matched_backup_ids:
                reusable_entities.append(backup_ent)
                matched_backup_ids.add(backup_id)
                matched = True
        
        if not matched:
            missing_entities.append(new_ent)
    
    return reusable_entities, missing_entities


# =========================
# Phase 6: Image File Mapping
# =========================

def find_images_for_entity(
    images_dir: Path,
    run_tag: str,
    group_id: str,
    entity_id: str
) -> List[str]:
    """Find image files for a given entity_id.
    
    Image file pattern: IMG__{run_tag}__{group_id}__{entity_id_normalized}__{card_role}.jpg
    or IMG__{run_tag}__{group_id}__{entity_id_normalized}__{card_role}.png
    
    Note: entity_id in S2 uses colon (DERIVED:xxx) but image filenames use underscore (DERIVED_xxx).
    We convert colon to underscore for matching.
    
    Args:
        images_dir: Path to images directory
        run_tag: Run tag (e.g., "FINAL_DISTRIBUTION")
        group_id: Group ID
        entity_id: Entity ID (may contain colon, e.g., "DERIVED:xxx")
    
    Returns:
        List of image filenames (relative to images_dir or just filenames)
    """
    if not images_dir.exists():
        return []
    
    # Normalize entity_id: convert colon to underscore for filename matching
    entity_id_normalized = str(entity_id).replace(":", "_")
    
    # Pattern: IMG__{run_tag}__{group_id}__{entity_id_normalized}__*.{jpg,png}
    pattern_base = f"IMG__{run_tag}__{group_id}__{entity_id_normalized}__*"
    
    image_files = []
    for ext in ["jpg", "jpeg", "png"]:
        pattern = f"{pattern_base}.{ext}"
        found_files = list(images_dir.glob(pattern))
        image_files.extend([f.name for f in found_files])
    
    # Sort for deterministic output
    image_files.sort()
    
    return image_files


def generate_image_mapping(
    restored_entities: List[Dict[str, Any]],
    images_dir: Path,
    run_tag: str
) -> List[Dict[str, Any]]:
    """Generate image file mapping for restored entities.
    
    Args:
        restored_entities: List of restored entity records (full S2 records)
        images_dir: Path to images directory
        run_tag: Run tag
    
    Returns:
        List of mapping records with format:
        {
            "group_id": "...",
            "entity_id": "...",
            "entity_name": "...",
            "image_files": ["IMG__...__Q1.jpg", "IMG__...__Q2.jpg"],
            "has_images": true
        }
    """
    mapping = []
    
    for entity in restored_entities:
        group_id = entity.get("group_id", "")
        entity_id = entity.get("entity_id", "")
        entity_name = entity.get("entity_name", "")
        
        if not group_id or not entity_id:
            continue
        
        image_files = find_images_for_entity(images_dir, run_tag, group_id, entity_id)
        
        mapping.append({
            "group_id": group_id,
            "entity_id": entity_id,
            "entity_name": entity_name,
            "image_files": image_files,
            "has_images": len(image_files) > 0
        })
    
    return mapping


# =========================
# Phase 7: S2 Results Restoration
# =========================

def restore_s2_results(
    backup_file: Path,
    s1_struct_path: Path,
    s2_results_path: Path,
    run_tag: str,
    arm: str,
    base_dir: Path,
    dry_run: bool = False,
    force: bool = False
) -> Dict[str, Any]:
    """Main restoration function.
    
    Restores S2 results file from backup by:
    1. Loading backup entities grouped by group_id
    2. For each group, loading new entity_list from S1 structure
    3. Comparing entities to identify reusable vs missing
    4. Writing restored S2 results file (only reusable entities)
    5. Generating image mapping and missing entities list
    
    Args:
        backup_file: Path to backup JSONL file
        s1_struct_path: Path to stage1_struct__arm*.jsonl file
        s2_results_path: Path to output S2 results file
        run_tag: Run tag
        arm: Arm identifier
        base_dir: Project root directory
        dry_run: If True, don't actually write files
        force: If True, overwrite existing s2_results_path
    
    Returns:
        Dictionary with restoration statistics and results
    """
    # Load backup entities
    backup_entities_by_group = load_backup_entities(backup_file)
    
    # Get all group_ids from backup
    group_ids = list(backup_entities_by_group.keys())
    
    # Get all group_ids from S1 structure (to find new groups)
    all_group_ids = set(group_ids)
    if s1_struct_path.exists():
        with open(s1_struct_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    gid = record.get("group_id")
                    if gid:
                        all_group_ids.add(gid)
                except json.JSONDecodeError:
                    continue
    
    # Process each group
    all_restored_entities = []
    all_missing_entities = []
    group_stats = []
    
    for group_id in sorted(all_group_ids):
        # Load new entity_list from S1
        new_entity_list = load_s1_entity_list(s1_struct_path, group_id)
        
        # Get backup entities for this group
        backup_entities = backup_entities_by_group.get(group_id, [])
        
        if not new_entity_list:
            # Group not found in S1 structure, skip
            continue
        
        # Compare entities
        reusable_entities, missing_entities = compare_entities(
            backup_entities, new_entity_list
        )
        
        # Add to collections
        all_restored_entities.extend(reusable_entities)
        all_missing_entities.extend(missing_entities)
        
        # Record stats
        group_stats.append({
            "group_id": group_id,
            "new_entity_count": len(new_entity_list),
            "reusable_count": len(reusable_entities),
            "missing_count": len(missing_entities)
        })
    
    # Generate image mapping
    images_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag / "images"
    image_mapping = generate_image_mapping(all_restored_entities, images_dir, run_tag)
    
    # Calculate statistics
    total_reusable = len(all_restored_entities)
    total_missing = len(all_missing_entities)
    entities_with_images = sum(1 for m in image_mapping if m["has_images"])
    
    result = {
        "success": True,
        "total_groups_processed": len(group_stats),
        "total_reusable_entities": total_reusable,
        "total_missing_entities": total_missing,
        "entities_with_images": entities_with_images,
        "group_stats": group_stats,
        "image_mapping": image_mapping,
        "missing_entities": all_missing_entities
    }
    
    if dry_run:
        result["dry_run"] = True
        return result
    
    # Backup existing file if it exists
    if s2_results_path.exists() and not force:
        raise FileExistsError(
            f"S2 results file already exists: {s2_results_path}\n"
            "Use --force to overwrite or remove the file manually."
        )
    
    if s2_results_path.exists() and force:
        # Create backup of existing file
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = s2_results_path.with_name(f"{s2_results_path.name}.backup_{timestamp}")
        import shutil
        shutil.copy2(s2_results_path, backup_path)
        result["existing_file_backed_up"] = str(backup_path)
    
    # Write restored S2 results file
    s2_results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(s2_results_path, "w", encoding="utf-8") as f:
        for entity in all_restored_entities:
            f.write(json.dumps(entity, ensure_ascii=False) + "\n")
    
    result["s2_results_path"] = str(s2_results_path)
    
    return result


# =========================
# Phase 8: Report Generation
# =========================

def generate_report(
    restoration_result: Dict[str, Any],
    output_path: Path,
    run_tag: str,
    arm: str
) -> None:
    """Generate restoration report.
    
    Args:
        restoration_result: Result dictionary from restore_s2_results()
        output_path: Path to output markdown report file
        arm: Arm identifier
    """
    lines = []
    lines.append(f"# S2 복원 리포트")
    lines.append("")
    lines.append(f"**생성일**: {restoration_result.get('generated_at', 'N/A')}")
    lines.append(f"**RUN_TAG**: `{run_tag}`")
    lines.append(f"**ARM**: `{arm}`")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Summary statistics
    lines.append("## 1. 요약 통계")
    lines.append("")
    lines.append(f"- **처리된 그룹 수**: {restoration_result['total_groups_processed']}")
    lines.append(f"- **재사용된 Entity 수**: {restoration_result['total_reusable_entities']}")
    lines.append(f"- **누락된 Entity 수**: {restoration_result['total_missing_entities']}")
    lines.append(f"- **이미지 파일이 있는 Entity 수**: {restoration_result['entities_with_images']}")
    lines.append("")
    
    # API 호출 절약 예상량
    lines.append("### API 호출 절약 예상량")
    lines.append("")
    lines.append(f"재사용된 {restoration_result['total_reusable_entities']}개 entity에 대해 S2 LLM 호출을 건너뛸 수 있습니다.")
    lines.append("")
    
    # Group statistics
    lines.append("## 2. 그룹별 통계")
    lines.append("")
    lines.append("| 그룹 ID | 새 Entity 수 | 재사용 수 | 누락 수 |")
    lines.append("|---------|-------------|----------|---------|")
    for stat in restoration_result['group_stats']:
        lines.append(
            f"| {stat['group_id']} | {stat['new_entity_count']} | "
            f"{stat['reusable_count']} | {stat['missing_count']} |"
        )
    lines.append("")
    
    # Image mapping statistics
    lines.append("## 3. 이미지 파일 매핑 통계")
    lines.append("")
    total_images = sum(len(m["image_files"]) for m in restoration_result['image_mapping'])
    lines.append(f"- **총 이미지 파일 수**: {total_images}")
    lines.append(f"- **이미지가 있는 Entity 수**: {restoration_result['entities_with_images']}")
    lines.append("")
    
    # Missing entities summary
    lines.append("## 4. 누락된 Entity 요약")
    lines.append("")
    if restoration_result['total_missing_entities'] > 0:
        lines.append(f"총 {restoration_result['total_missing_entities']}개의 entity가 백업에 없어 새로 생성해야 합니다.")
        lines.append("")
        lines.append(f"누락된 entity 목록은 `s2_missing_entities__arm{arm}.jsonl` 파일에 저장되었습니다.")
    else:
        lines.append("모든 entity가 백업에서 찾아져 재사용 가능합니다.")
    lines.append("")
    
    # Next steps guide
    lines.append("## 5. 다음 단계 가이드")
    lines.append("")
    lines.append("### 누락된 Entity 생성")
    lines.append("")
    lines.append("누락된 entity를 생성하려면 `01_generate_json.py`를 실행하세요:")
    lines.append("")
    lines.append("```bash")
    lines.append("# 방법 1: 누락된 entity만 생성 (권장)")
    lines.append(f"python3 3_Code/src/01_generate_json.py \\")
    lines.append(f"  --run_tag {run_tag} \\")
    lines.append(f"  --arm {arm} \\")
    lines.append(f"  --only_entity_ids $(cat s2_missing_entities__arm{arm}.jsonl | jq -r '.entity_id')")
    lines.append("")
    lines.append("# 방법 2: 전체 재생성 (시간이 오래 걸림)")
    lines.append(f"python3 3_Code/src/01_generate_json.py \\")
    lines.append(f"  --run_tag {run_tag} \\")
    lines.append(f"  --arm {arm}")
    lines.append("```")
    lines.append("")
    
    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# =========================
# Main Entry Point
# =========================

def main():
    """Main entry point for S2 backup restoration."""
    parser = argparse.ArgumentParser(
        description="Restore S2 results from backup based on entity_id matching",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with auto-detection
  python restore_s2_from_backup.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G

  # With explicit paths
  python restore_s2_from_backup.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G \\
    --s2_results_path 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG.jsonl \\
    --backup_path 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG.jsonl.backup_20250101_120000

  # Dry run to preview changes
  python restore_s2_from_backup.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G --dry_run

  # Force overwrite existing file
  python restore_s2_from_backup.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G --force
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
        "--backup_path",
        type=str,
        help="Path to backup file (optional, auto-detected if not provided)"
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Don't actually write files, just simulate"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing S2 results file if it exists (creates backup first)"
    )
    
    args = parser.parse_args()
    
    # Validate and resolve base directory
    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        print(f"Error: Base directory does not exist: {base_dir}", file=sys.stderr)
        return 1
    
    if not base_dir.is_dir():
        print(f"Error: Base directory is not a directory: {base_dir}", file=sys.stderr)
        return 1
    
    run_tag = args.run_tag.strip()
    arm = args.arm.strip().upper()
    
    if not run_tag:
        print("Error: --run_tag cannot be empty", file=sys.stderr)
        return 1
    
    if not arm:
        print("Error: --arm cannot be empty", file=sys.stderr)
        return 1
    
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
    
    # Resolve backup file path
    if args.backup_path:
        backup_file = Path(args.backup_path)
        if not backup_file.is_absolute():
            backup_file = base_dir / backup_file
        backup_file = backup_file.resolve()
        
        if not backup_file.exists():
            print(f"Error: Specified backup file does not exist: {backup_file}", file=sys.stderr)
            return 1
    else:
        # Auto-detect backup file
        backup_file = find_backup_file(s2_results_path)
        if not backup_file or not backup_file.exists():
            print(f"Error: Backup file not found", file=sys.stderr)
            print(f"  Searched for backup of: {s2_results_path}", file=sys.stderr)
            print(f"  Expected pattern: {s2_results_path.name}.backup_*", file=sys.stderr)
            return 1
    
    # Find S1 structure file
    s1_struct_path = gen_dir / f"stage1_struct__arm{arm}.jsonl"
    if not s1_struct_path.exists():
        print(f"Error: S1 structure file not found: {s1_struct_path}", file=sys.stderr)
        print(f"  This file is required to determine the new entity_list", file=sys.stderr)
        return 1
    
    # Check if output file exists and handle accordingly
    if s2_results_path.exists() and not args.force and not args.dry_run:
        print(f"Error: S2 results file already exists: {s2_results_path}", file=sys.stderr)
        print(f"  Use --force to overwrite (will create a backup first)", file=sys.stderr)
        print(f"  Or use --dry_run to preview changes without writing files", file=sys.stderr)
        return 1
    
    # Print configuration
    print("=" * 70)
    print("S2 Backup Restoration")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Arm: {arm}")
    print(f"Backup file: {backup_file}")
    print(f"S1 structure: {s1_struct_path}")
    print(f"Output: {s2_results_path}")
    print(f"Dry run: {args.dry_run}")
    print(f"Force: {args.force}")
    if s2_results_path.exists() and args.force:
        print(f"⚠️  Existing file will be backed up before overwriting")
    print("=" * 70)
    print()
    
    # Perform restoration
    from datetime import datetime
    try:
        restoration_result = restore_s2_results(
            backup_file=backup_file,
            s1_struct_path=s1_struct_path,
            s2_results_path=s2_results_path,
            run_tag=run_tag,
            arm=arm,
            base_dir=base_dir,
            dry_run=args.dry_run,
            force=args.force
        )
    except FileExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error during restoration: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    
    restoration_result["generated_at"] = datetime.now().isoformat()
    
    if not args.dry_run:
        # Save missing entities list
        missing_entities_path = gen_dir / f"s2_missing_entities__arm{arm}.jsonl"
        missing_entities_path.parent.mkdir(parents=True, exist_ok=True)
        with open(missing_entities_path, "w", encoding="utf-8") as f:
            for entity in restoration_result["missing_entities"]:
                f.write(json.dumps(entity, ensure_ascii=False) + "\n")
        
        # Save image mapping
        image_mapping_path = gen_dir / f"s2_restored_entities_images__arm{arm}.jsonl"
        with open(image_mapping_path, "w", encoding="utf-8") as f:
            for mapping in restoration_result["image_mapping"]:
                f.write(json.dumps(mapping, ensure_ascii=False) + "\n")
        
        # Generate report
        report_path = gen_dir / f"s2_restoration_report__arm{arm}.md"
        generate_report(restoration_result, report_path, run_tag, arm)
        
        print("\n" + "=" * 70)
        print("Restoration Complete!")
        print("=" * 70)
        print(f"✅ Restored entities: {restoration_result['total_reusable_entities']}")
        print(f"⚠️  Missing entities: {restoration_result['total_missing_entities']}")
        print(f"📊 Entities with images: {restoration_result['entities_with_images']}")
        print()
        print("Output files:")
        print(f"  📄 Report: {report_path}")
        print(f"  📋 Missing entities list: {missing_entities_path}")
        print(f"  🖼️  Image mapping: {image_mapping_path}")
        print(f"  💾 Restored S2 results: {s2_results_path}")
        if "existing_file_backed_up" in restoration_result:
            print(f"  🔄 Original file backed up to: {restoration_result['existing_file_backed_up']}")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("Dry Run Complete!")
        print("=" * 70)
        print(f"Would restore entities: {restoration_result['total_reusable_entities']}")
        print(f"Would need to generate: {restoration_result['total_missing_entities']}")
        print(f"Entities with images: {restoration_result['entities_with_images']}")
        print()
        print("No files were modified. Run without --dry_run to apply changes.")
        print("=" * 70)
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S2 결과 업데이트 스크립트

유사도 매칭 결과를 기반으로 S2 결과 파일을 업데이트합니다.
재사용할 entity를 복원된 S2 파일에 추가하고, Entity ID를 업데이트합니다.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# =========================
# File Loading Functions
# =========================

def load_s2_results(s2_results_path: Path) -> Dict[tuple[str, str], Dict[str, Any]]:
    """Load existing S2 results, indexed by (group_id, entity_id).
    
    Args:
        s2_results_path: Path to S2 results JSONL file
    
    Returns:
        Dictionary mapping (group_id, entity_id) tuple to entity record
    """
    entities: Dict[tuple[str, str], Dict[str, Any]] = {}
    
    if not s2_results_path.exists():
        return entities
    
    with open(s2_results_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                record = json.loads(line)
                group_id = record.get("group_id", "")
                entity_id = record.get("entity_id", "")
                
                if group_id and entity_id:
                    entities[(group_id, entity_id)] = record
            except json.JSONDecodeError:
                continue
    
    return entities


def load_backup_entities(backup_file: Path) -> Dict[str, Dict[str, Any]]:
    """Load entities from backup file, indexed by entity_id.
    
    Args:
        backup_file: Path to backup JSONL file
    
    Returns:
        Dictionary mapping entity_id to entity record
    """
    entities: Dict[str, Dict[str, Any]] = {}
    
    if not backup_file.exists():
        return entities
    
    with open(backup_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                record = json.loads(line)
                entity_id = record.get("entity_id", "")
                
                if entity_id:
                    entities[entity_id] = record
            except json.JSONDecodeError:
                continue
    
    return entities


def load_similarity_matches(matches_path: Path) -> List[Dict[str, Any]]:
    """Load similarity match results.
    
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


def load_normalized_matches(normalized_path: Path) -> Dict[str, Dict[str, str]]:
    """Load normalized match results.
    
    Args:
        normalized_path: Path to normalized matches JSONL file (optional)
    
    Returns:
        Dictionary mapping backup_entity_id to {s1_entity_id, s1_entity_name}
    """
    normalized: Dict[str, Dict[str, str]] = {}
    
    if not normalized_path.exists():
        return normalized
    
    with open(normalized_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                record = json.loads(line)
                backup_id = record.get("backup_entity_id", "")
                s1_id = record.get("s1_entity_id", "")
                s1_name = record.get("s1_entity_name", "")
                
                if backup_id and s1_id:
                    normalized[backup_id] = {
                        "s1_entity_id": s1_id,
                        "s1_entity_name": s1_name
                    }
            except json.JSONDecodeError:
                continue
    
    return normalized


# =========================
# S2 Results Update
# =========================

def update_s2_with_similar_entities(
    s2_results_path: Path,
    similarity_matches_path: Path,
    backup_file: Path,
    normalized_matches_path: Optional[Path],
    similarity_threshold: float = 0.95,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Update S2 results file with similar entities from matches.
    
    Args:
        s2_results_path: Path to S2 results file (will be updated)
        similarity_matches_path: Path to similarity matches JSONL file
        backup_file: Path to backup S2 JSONL file (source of entity records)
        normalized_matches_path: Optional path to normalized matches JSONL file
        similarity_threshold: Minimum similarity score to include (default: 0.95)
        dry_run: If True, don't actually write files
    
    Returns:
        Dictionary with update statistics
    """
    # Load existing S2 results
    print("Loading existing S2 results...")
    existing_entities = load_s2_results(s2_results_path)
    existing_keys: Set[tuple[str, str]] = set(existing_entities.keys())
    
    # Load backup entities
    print("Loading backup entities...")
    backup_entities = load_backup_entities(backup_file)
    
    # Load similarity matches
    print("Loading similarity matches...")
    similarity_matches = load_similarity_matches(similarity_matches_path)
    
    # Load normalized matches (optional)
    normalized_matches: Dict[str, Dict[str, str]] = {}
    if normalized_matches_path:
        print("Loading normalized matches...")
        normalized_matches = load_normalized_matches(normalized_matches_path)
    
    # Process matches
    added_entities = []
    skipped_entities = []
    missing_backup_entities = []
    
    # Track which S1 entity_ids we've already matched (to avoid duplicates)
    matched_s1_entity_ids: Set[tuple[str, str]] = set()
    
    for match in similarity_matches:
        similarity = match.get("similarity", 0.0)
        
        # Skip if below threshold
        if similarity < similarity_threshold:
            continue
        
        backup_entity_id = match.get("backup_entity_id", "")
        s1_entity_id = match.get("s1_entity_id", "")
        s1_entity_name = match.get("s1_entity_name", "")
        
        if not backup_entity_id or not s1_entity_id:
            continue
        
        # Check if already in existing results
        # We need group_id from backup entity to check
        backup_entity = backup_entities.get(backup_entity_id)
        if not backup_entity:
            missing_backup_entities.append(backup_entity_id)
            continue
        
        group_id = backup_entity.get("group_id", "")
        if not group_id:
            continue
        
        # Check if S1 entity already exists in results
        if (group_id, s1_entity_id) in existing_keys:
            skipped_entities.append({
                "backup_entity_id": backup_entity_id,
                "s1_entity_id": s1_entity_id,
                "reason": "already_exists"
            })
            continue
        
        # Check if normalized match exists (takes precedence)
        if backup_entity_id in normalized_matches:
            norm_match = normalized_matches[backup_entity_id]
            s1_entity_id = norm_match["s1_entity_id"]
            s1_entity_name = norm_match["s1_entity_name"]
        
        # Re-check if S1 entity already exists (after normalized match update)
        if (group_id, s1_entity_id) in existing_keys:
            skipped_entities.append({
                "backup_entity_id": backup_entity_id,
                "s1_entity_id": s1_entity_id,
                "reason": "already_exists"
            })
            continue
        
        # Check if we've already matched this S1 entity_id in this run
        if (group_id, s1_entity_id) in matched_s1_entity_ids:
            skipped_entities.append({
                "backup_entity_id": backup_entity_id,
                "s1_entity_id": s1_entity_id,
                "reason": "duplicate_match"
            })
            continue
        
        # Create updated entity record
        updated_entity = backup_entity.copy()
        
        # Update entity_id and entity_name to match S1
        updated_entity["entity_id"] = s1_entity_id
        updated_entity["entity_name"] = s1_entity_name
        
        # Ensure group_id and group_path are preserved (should already be there)
        if "group_id" not in updated_entity:
            updated_entity["group_id"] = group_id
        
        # Add to results
        existing_entities[(group_id, s1_entity_id)] = updated_entity
        matched_s1_entity_ids.add((group_id, s1_entity_id))
        added_entities.append({
            "backup_entity_id": backup_entity_id,
            "backup_entity_name": backup_entity.get("entity_name", ""),
            "s1_entity_id": s1_entity_id,
            "s1_entity_name": s1_entity_name,
            "similarity": similarity,
            "group_id": group_id
        })
    
    # Calculate statistics
    result = {
        "success": True,
        "total_existing_entities": len(existing_entities),
        "total_matches_processed": len([m for m in similarity_matches if m.get("similarity", 0.0) >= similarity_threshold]),
        "entities_added": len(added_entities),
        "entities_skipped": len(skipped_entities),
        "missing_backup_entities": len(missing_backup_entities),
        "similarity_threshold": similarity_threshold,
        "added_entities": added_entities,
        "skipped_entities": skipped_entities,
        "missing_backup_entities": missing_backup_entities
    }
    
    if dry_run:
        result["dry_run"] = True
        return result
    
    # Create backup of existing file
    if s2_results_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = s2_results_path.with_name(f"{s2_results_path.name}.backup_{timestamp}")
        shutil.copy2(s2_results_path, backup_path)
        result["backup_created"] = str(backup_path)
    
    # Write updated S2 results file
    s2_results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(s2_results_path, "w", encoding="utf-8") as f:
        # Write all entities (existing + added)
        for (group_id, entity_id), entity_record in sorted(existing_entities.items()):
            f.write(json.dumps(entity_record, ensure_ascii=False) + "\n")
    
    result["s2_results_path"] = str(s2_results_path)
    result["total_entities_after_update"] = len(existing_entities)
    
    return result


# =========================
# Report Generation
# =========================

def generate_report(
    update_result: Dict[str, Any],
    output_path: Path,
    run_tag: str,
    arm: str
) -> None:
    """Generate update report.
    
    Args:
        update_result: Result dictionary from update_s2_with_similar_entities()
        output_path: Path to output markdown report file
        run_tag: Run tag
        arm: Arm identifier
    """
    lines = []
    lines.append("# S2 결과 업데이트 리포트")
    lines.append("")
    lines.append(f"**생성일**: {datetime.now().isoformat()}")
    lines.append(f"**RUN_TAG**: `{run_tag}`")
    lines.append(f"**ARM**: `{arm}`")
    lines.append(f"**유사도 임계값**: {update_result['similarity_threshold']}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Summary statistics
    lines.append("## 1. 요약 통계")
    lines.append("")
    lines.append(f"- **기존 Entity 수**: {update_result['total_existing_entities']}")
    lines.append(f"- **처리된 매칭 수** (유사도 ≥ {update_result['similarity_threshold']}): {update_result['total_matches_processed']}")
    lines.append(f"- **추가된 Entity 수**: {update_result['entities_added']}")
    lines.append(f"- **건너뛴 Entity 수**: {update_result['entities_skipped']}")
    lines.append(f"- **백업에 없는 Entity 수**: {len(update_result['missing_backup_entities'])}")
    lines.append(f"- **업데이트 후 총 Entity 수**: {update_result.get('total_entities_after_update', update_result['total_existing_entities'] + update_result['entities_added'])}")
    lines.append("")
    
    # Added entities summary
    if update_result['entities_added'] > 0:
        lines.append("## 2. 추가된 Entity 요약")
        lines.append("")
        lines.append(f"총 {update_result['entities_added']}개의 entity가 S2 결과 파일에 추가되었습니다.")
        lines.append("")
        
        # Group by similarity ranges
        similarity_ranges = {
            "0.95-1.00": [e for e in update_result['added_entities'] if 0.95 <= e.get("similarity", 0.0) <= 1.0],
            "0.90-0.95": [e for e in update_result['added_entities'] if 0.90 <= e.get("similarity", 0.0) < 0.95],
        }
        
        lines.append("### 유사도 분포")
        lines.append("")
        lines.append("| 유사도 범위 | 추가된 수 |")
        lines.append("|------------|----------|")
        for range_name, entities in similarity_ranges.items():
            lines.append(f"| {range_name} | {len(entities)} |")
        lines.append("")
    
    # Skipped entities
    if update_result['entities_skipped'] > 0:
        lines.append("## 3. 건너뛴 Entity")
        lines.append("")
        lines.append(f"총 {update_result['entities_skipped']}개의 entity가 건너뛰어졌습니다.")
        lines.append("")
        
        # Group by reason
        skip_reasons = defaultdict(int)
        for skipped in update_result['skipped_entities']:
            reason = skipped.get("reason", "unknown")
            skip_reasons[reason] += 1
        
        lines.append("### 건너뛴 이유")
        lines.append("")
        lines.append("| 이유 | 수 |")
        lines.append("|------|----|")
        for reason, count in sorted(skip_reasons.items(), key=lambda x: -x[1]):
            lines.append(f"| {reason} | {count} |")
        lines.append("")
    
    # Missing backup entities
    if len(update_result['missing_backup_entities']) > 0:
        lines.append("## 4. 백업에 없는 Entity")
        lines.append("")
        lines.append(f"경고: {len(update_result['missing_backup_entities'])}개의 entity가 백업 파일에서 찾을 수 없었습니다.")
        lines.append("이들은 추가되지 않았습니다.")
        lines.append("")
    
    # Next steps
    lines.append("## 5. 다음 단계")
    lines.append("")
    if update_result['entities_added'] > 0:
        lines.append(f"✅ {update_result['entities_added']}개의 entity가 S2 결과 파일에 추가되었습니다.")
        lines.append("")
        lines.append("다음 단계:")
        lines.append("1. 업데이트된 S2 결과 파일 검증")
        lines.append("2. 이미지 파일 매핑 확인 (필요시 `reuse_similar_images.py` 실행)")
        lines.append("3. 누락된 entity 생성 (필요시)")
    else:
        lines.append("추가된 entity가 없습니다.")
    lines.append("")
    
    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# =========================
# Main Entry Point
# =========================

def main():
    """Main entry point for S2 results update."""
    parser = argparse.ArgumentParser(
        description="Update S2 results file with similar entities from similarity matches",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python update_s2_with_similar_entities.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G

  # With custom similarity threshold
  python update_s2_with_similar_entities.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G \\
    --similarity_threshold 0.90

  # With normalized matches
  python update_s2_with_similar_entities.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G \\
    --normalized_matches_path s2_normalized_matches__armG.jsonl

  # Dry run to preview changes
  python update_s2_with_similar_entities.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G --dry_run
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
        help="Minimum similarity score to include (default: 0.95)"
    )
    parser.add_argument(
        "--similarity_matches_path",
        type=str,
        help="Path to similarity matches file (optional, auto-detected if not provided)"
    )
    parser.add_argument(
        "--normalized_matches_path",
        type=str,
        help="Path to normalized matches file (optional)"
    )
    parser.add_argument(
        "--backup_path",
        type=str,
        help="Path to backup file (optional, auto-detected if not provided)"
    )
    parser.add_argument(
        "--s2_results_path",
        type=str,
        help="Path to S2 results file (optional, auto-detected if not provided)"
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Don't actually write files, just simulate"
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
        return 1
    
    # Resolve normalized matches path (optional)
    normalized_matches_path: Optional[Path] = None
    if args.normalized_matches_path:
        normalized_matches_path = Path(args.normalized_matches_path)
        if not normalized_matches_path.is_absolute():
            normalized_matches_path = base_dir / normalized_matches_path
        normalized_matches_path = normalized_matches_path.resolve()
    else:
        # Auto-detect normalized matches file
        potential_normalized = gen_dir / f"s2_normalized_matches__arm{arm}.jsonl"
        if potential_normalized.exists():
            normalized_matches_path = potential_normalized
    
    # Resolve backup file path
    if args.backup_path:
        backup_file = Path(args.backup_path)
        if not backup_file.is_absolute():
            backup_file = base_dir / backup_file
        backup_file = backup_file.resolve()
    else:
        # Auto-detect backup file (find most recent)
        backup_patterns = [
            f"s2_results__s1arm{arm}__s2arm{arm}.jsonl.backup_*",
            f"s2_results__s1arm{arm}__s2arm{arm}.backup_*",
        ]
        backup_files = []
        for pattern in backup_patterns:
            backup_files.extend(gen_dir.glob(pattern))
        
        if not backup_files:
            print(f"Error: Backup file not found in {gen_dir}", file=sys.stderr)
            print(f"  Searched for patterns: {backup_patterns}", file=sys.stderr)
            return 1
        
        # Sort by modification time (most recent first)
        backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        backup_file = backup_files[0]
    
    if not backup_file.exists():
        print(f"Error: Backup file does not exist: {backup_file}", file=sys.stderr)
        return 1
    
    # Print configuration
    print("=" * 70)
    print("S2 Results Update with Similar Entities")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Arm: {arm}")
    print(f"S2 results: {s2_results_path}")
    print(f"Similarity matches: {similarity_matches_path}")
    if normalized_matches_path:
        print(f"Normalized matches: {normalized_matches_path}")
    print(f"Backup file: {backup_file}")
    print(f"Similarity threshold: {similarity_threshold}")
    print(f"Dry run: {args.dry_run}")
    print("=" * 70)
    print()
    
    # Perform update
    try:
        update_result = update_s2_with_similar_entities(
            s2_results_path=s2_results_path,
            similarity_matches_path=similarity_matches_path,
            backup_file=backup_file,
            normalized_matches_path=normalized_matches_path,
            similarity_threshold=similarity_threshold,
            dry_run=args.dry_run
        )
    except Exception as e:
        print(f"Error during update: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    
    # Generate report
    if not args.dry_run:
        report_path = gen_dir / f"s2_update_report__arm{arm}.md"
        generate_report(update_result, report_path, run_tag, arm)
    
    print("\n" + "=" * 70)
    if args.dry_run:
        print("Dry Run Complete!")
        print("=" * 70)
        print(f"Would add entities: {update_result['entities_added']}")
        print(f"Would skip entities: {update_result['entities_skipped']}")
        print(f"Missing backup entities: {update_result['missing_backup_entities']}")
        print()
        print("No files were modified. Run without --dry_run to apply changes.")
    else:
        print("Update Complete!")
        print("=" * 70)
        print(f"✅ Entities added: {update_result['entities_added']}")
        print(f"⚠️  Entities skipped: {update_result['entities_skipped']}")
        print(f"❌ Missing backup entities: {update_result['missing_backup_entities']}")
        print(f"📊 Total entities after update: {update_result.get('total_entities_after_update', 'N/A')}")
        print()
        print("Output files:")
        print(f"  💾 Updated S2 results: {s2_results_path}")
        if "backup_created" in update_result:
            print(f"  🔄 Original file backed up to: {update_result['backup_created']}")
        report_path = gen_dir / f"s2_update_report__arm{arm}.md"
        print(f"  📊 Report: {report_path}")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


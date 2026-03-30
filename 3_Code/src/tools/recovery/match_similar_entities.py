#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
유사도 기반 Entity 매칭 스크립트

백업 S2 entity와 S1 entity를 그룹별로 비교하여 유사도 기반 매칭 수행.
difflib.SequenceMatcher를 사용하여 문자열 유사도 계산.
이미 복원된 entity는 제외하고, 유사도가 임계값 이상인 매칭 결과 저장.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# =========================
# Entity Normalization (from restore_s2_from_backup.py)
# =========================

def normalize_entity_key(s: str) -> str:
    """Normalize entity names for matching (strip + remove asterisks).
    
    This function matches the behavior of _normalize_entity_key in 01_generate_json.py.
    """
    return re.sub(r"\*+", "", str(s or "")).strip()


# =========================
# File Loading Functions
# =========================

def load_backup_entities(backup_file: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Load entities from backup file, grouped by group_id.
    
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
                
                entities_by_group[group_id].append(record)
            except json.JSONDecodeError:
                continue
    
    return dict(entities_by_group)


def load_s1_entity_list(s1_struct_path: Path, group_id: str) -> List[Dict[str, str]]:
    """Load entity_list from S1 structure for a specific group.
    
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
    
    Canonical object shape: {"entity_id": <str>, "entity_name": <str>}
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


def load_restored_entities(s2_results_path: Path) -> Dict[str, set[str]]:
    """Load already restored entities, grouped by group_id.
    
    Args:
        s2_results_path: Path to restored S2 results file
    
    Returns:
        Dictionary mapping group_id to set of entity_ids
    """
    restored_by_group: Dict[str, set[str]] = defaultdict(set)
    
    if not s2_results_path.exists():
        return dict(restored_by_group)
    
    with open(s2_results_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                record = json.loads(line)
                group_id = record.get("group_id")
                entity_id = record.get("entity_id")
                
                if group_id and entity_id:
                    restored_by_group[group_id].add(entity_id)
            except json.JSONDecodeError:
                continue
    
    return dict(restored_by_group)


# =========================
# Similarity Matching
# =========================

def calculate_similarity(name1: str, name2: str) -> float:
    """Calculate similarity between two entity names using SequenceMatcher.
    
    Args:
        name1: First entity name
        name2: Second entity name
    
    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Normalize both names for comparison
    norm1 = normalize_entity_key(name1)
    norm2 = normalize_entity_key(name2)
    
    if not norm1 or not norm2:
        return 0.0
    
    # Use SequenceMatcher for similarity calculation
    matcher = difflib.SequenceMatcher(None, norm1, norm2)
    return matcher.ratio()


def find_similar_entities(
    backup_entities: List[Dict[str, Any]],
    s1_entities: List[Dict[str, str]],
    restored_entity_ids: set[str],
    similarity_threshold: float = 0.90
) -> List[Dict[str, Any]]:
    """Find similar entities between backup and S1 entity list.
    
    Args:
        backup_entities: List of backup entity records
        s1_entities: List of S1 entity objects
        restored_entity_ids: Set of already restored entity_ids (to exclude)
        similarity_threshold: Minimum similarity score to consider a match
    
    Returns:
        List of match records with format:
        {
            "backup_entity_id": "...",
            "backup_entity_name": "...",
            "s1_entity_id": "...",
            "s1_entity_name": "...",
            "similarity": 0.95,
            "difference_type": "abbreviation",
            "can_reuse": true
        }
    """
    matches = []
    
    # Create a set of S1 entity IDs for quick lookup
    s1_entity_ids = {e["entity_id"] for e in s1_entities}
    
    for backup_ent in backup_entities:
        backup_id = backup_ent.get("entity_id", "")
        backup_name = backup_ent.get("entity_name", "")
        
        # Skip if already restored
        if backup_id in restored_entity_ids:
            continue
        
        # Find best match in S1 entities
        best_match = None
        best_similarity = 0.0
        
        for s1_ent in s1_entities:
            s1_id = s1_ent.get("entity_id", "")
            s1_name = s1_ent.get("entity_name", "")
            
            # Skip if S1 entity is already restored (exact match)
            if s1_id in restored_entity_ids:
                continue
            
            similarity = calculate_similarity(backup_name, s1_name)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = {
                    "s1_entity_id": s1_id,
                    "s1_entity_name": s1_name,
                    "similarity": similarity
                }
        
        # If best match meets threshold, record it
        if best_match and best_similarity >= similarity_threshold:
            # Classify the type of difference
            diff_type = classify_difference(backup_name, best_match["s1_entity_name"])
            
            match_record = {
                "backup_entity_id": backup_id,
                "backup_entity_name": backup_name,
                "s1_entity_id": best_match["s1_entity_id"],
                "s1_entity_name": best_match["s1_entity_name"],
                "similarity": round(best_similarity, 4),
                "difference_type": diff_type,
                "can_reuse": best_similarity >= 0.95  # Auto-reuse if >= 0.95
            }
            matches.append(match_record)
    
    return matches


def classify_difference(name1: str, name2: str) -> str:
    """Classify the type of difference between two entity names.
    
    Args:
        name1: First entity name
        name2: Second entity name
    
    Returns:
        Difference type: "abbreviation", "singular_plural", "punctuation", "type_version", "other"
    """
    norm1 = normalize_entity_key(name1).lower()
    norm2 = normalize_entity_key(name2).lower()
    
    # Check for abbreviation differences (e.g., SACD vs SCD)
    # Look for acronyms in parentheses
    abbrev_pattern = r'\(([A-Z]+)\)'
    abbrev1 = set(re.findall(abbrev_pattern, name1))
    abbrev2 = set(re.findall(abbrev_pattern, name2))
    if abbrev1 != abbrev2 and (abbrev1 or abbrev2):
        return "abbreviation"
    
    # Check for singular/plural differences
    # Common patterns: Device/Devices, Gland/Glands, Effect/Effects
    singular_plural_patterns = [
        (r'\bdevice\b', r'\bdevices\b'),
        (r'\bgland\b', r'\bglands\b'),
        (r'\beffect\b', r'\beffects\b'),
        (r'\bnode\b', r'\bnodes\b'),
        (r'\bligament\b', r'\bligaments\b'),
        (r'\bcell\b', r'\bcells\b'),
        (r'\bmalformation\b', r'\bmalformations\b'),
    ]
    for pattern1, pattern2 in singular_plural_patterns:
        if (re.search(pattern1, norm1) and re.search(pattern2, norm2)) or \
           (re.search(pattern2, norm1) and re.search(pattern1, norm2)):
            return "singular_plural"
    
    # Check for punctuation differences (colon, parentheses, hyphen/slash)
    punct_chars = [':', '(', ')', '-', '/']
    has_punct1 = any(c in name1 for c in punct_chars)
    has_punct2 = any(c in name2 for c in punct_chars)
    if has_punct1 != has_punct2:
        return "punctuation"
    
    # Check for type/version differences (Type I vs Type II, IVa vs IV)
    type_pattern = r'type\s+([ivxlcdm]+[a-z]?|\d+)'
    type1 = re.findall(type_pattern, norm1, re.IGNORECASE)
    type2 = re.findall(type_pattern, norm2, re.IGNORECASE)
    if type1 != type2 and (type1 or type2):
        return "type_version"
    
    return "other"


# =========================
# Main Processing
# =========================

def match_similar_entities(
    backup_file: Path,
    s1_struct_path: Path,
    s2_results_path: Path,
    output_matches_path: Path,
    similarity_threshold: float = 0.90
) -> Dict[str, Any]:
    """Main function to match similar entities.
    
    Args:
        backup_file: Path to backup S2 JSONL file
        s1_struct_path: Path to S1 structure JSONL file
        s2_results_path: Path to restored S2 results file (to exclude already matched)
        output_matches_path: Path to output matches JSONL file
        similarity_threshold: Minimum similarity score
    
    Returns:
        Dictionary with matching statistics
    """
    # Load data
    print("Loading backup entities...")
    backup_entities_by_group = load_backup_entities(backup_file)
    
    print("Loading restored entities...")
    restored_entities_by_group = load_restored_entities(s2_results_path)
    
    # Process each group
    all_matches = []
    group_stats = []
    
    for group_id in sorted(backup_entities_by_group.keys()):
        backup_entities = backup_entities_by_group[group_id]
        restored_entity_ids = restored_entities_by_group.get(group_id, set())
        
        # Load S1 entities for this group
        s1_entities = load_s1_entity_list(s1_struct_path, group_id)
        
        if not s1_entities:
            continue
        
        # Find similar entities
        matches = find_similar_entities(
            backup_entities,
            s1_entities,
            restored_entity_ids,
            similarity_threshold
        )
        
        all_matches.extend(matches)
        
        # Record stats
        group_stats.append({
            "group_id": group_id,
            "backup_entity_count": len(backup_entities),
            "s1_entity_count": len(s1_entities),
            "restored_count": len(restored_entity_ids),
            "similar_matches": len(matches),
            "auto_reuse_count": sum(1 for m in matches if m.get("can_reuse", False))
        })
    
    # Calculate statistics
    total_matches = len(all_matches)
    auto_reuse_count = sum(1 for m in all_matches if m.get("can_reuse", False))
    manual_review_count = total_matches - auto_reuse_count
    
    # Group by similarity ranges
    similarity_ranges = {
        "0.95-1.00": sum(1 for m in all_matches if 0.95 <= m["similarity"] <= 1.0),
        "0.90-0.95": sum(1 for m in all_matches if 0.90 <= m["similarity"] < 0.95),
    }
    
    # Group by difference type
    diff_type_counts = defaultdict(int)
    for m in all_matches:
        diff_type_counts[m["difference_type"]] += 1
    
    result = {
        "success": True,
        "total_matches": total_matches,
        "auto_reuse_count": auto_reuse_count,
        "manual_review_count": manual_review_count,
        "similarity_threshold": similarity_threshold,
        "similarity_ranges": similarity_ranges,
        "difference_type_counts": dict(diff_type_counts),
        "group_stats": group_stats
    }
    
    # Write matches to file
    output_matches_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_matches_path, "w", encoding="utf-8") as f:
        for match in all_matches:
            f.write(json.dumps(match, ensure_ascii=False) + "\n")
    
    return result


# =========================
# Report Generation
# =========================

def generate_report(
    match_result: Dict[str, Any],
    output_path: Path,
    run_tag: str,
    arm: str
) -> None:
    """Generate similarity matching report.
    
    Args:
        match_result: Result dictionary from match_similar_entities()
        output_path: Path to output markdown report file
        run_tag: Run tag
        arm: Arm identifier
    """
    lines = []
    lines.append("# 유사도 기반 Entity 매칭 리포트")
    lines.append("")
    lines.append(f"**생성일**: {datetime.now().isoformat()}")
    lines.append(f"**RUN_TAG**: `{run_tag}`")
    lines.append(f"**ARM**: `{arm}`")
    lines.append(f"**유사도 임계값**: {match_result['similarity_threshold']}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Summary statistics
    lines.append("## 1. 요약 통계")
    lines.append("")
    lines.append(f"- **총 매칭 수**: {match_result['total_matches']}")
    lines.append(f"- **자동 재사용 가능** (유사도 ≥ 0.95): {match_result['auto_reuse_count']}")
    lines.append(f"- **수동 검토 필요** (유사도 0.90-0.95): {match_result['manual_review_count']}")
    lines.append("")
    
    # Similarity ranges
    lines.append("### 유사도 분포")
    lines.append("")
    lines.append("| 유사도 범위 | 매칭 수 |")
    lines.append("|------------|--------|")
    for range_name, count in match_result['similarity_ranges'].items():
        lines.append(f"| {range_name} | {count} |")
    lines.append("")
    
    # Difference types
    lines.append("### 차이 유형 분포")
    lines.append("")
    lines.append("| 차이 유형 | 매칭 수 |")
    lines.append("|----------|--------|")
    for diff_type, count in sorted(match_result['difference_type_counts'].items(), key=lambda x: -x[1]):
        lines.append(f"| {diff_type} | {count} |")
    lines.append("")
    
    # Group statistics
    lines.append("## 2. 그룹별 통계")
    lines.append("")
    lines.append("| 그룹 ID | 백업 Entity | S1 Entity | 복원됨 | 유사 매칭 | 자동 재사용 |")
    lines.append("|---------|------------|-----------|--------|----------|------------|")
    for stat in match_result['group_stats']:
        lines.append(
            f"| {stat['group_id']} | {stat['backup_entity_count']} | "
            f"{stat['s1_entity_count']} | {stat['restored_count']} | "
            f"{stat['similar_matches']} | {stat['auto_reuse_count']} |"
        )
    lines.append("")
    
    # Next steps
    lines.append("## 3. 다음 단계")
    lines.append("")
    lines.append("### 자동 재사용 가능한 Entity")
    lines.append("")
    lines.append(f"유사도 0.95 이상인 {match_result['auto_reuse_count']}개 entity는 자동으로 재사용할 수 있습니다.")
    lines.append("")
    lines.append("### 수동 검토 필요")
    lines.append("")
    lines.append(f"유사도 0.90-0.95인 {match_result['manual_review_count']}개 entity는 수동 검토 후 재사용 여부를 결정해야 합니다.")
    lines.append("")
    lines.append("### 매칭 결과 파일")
    lines.append("")
    lines.append("상세 매칭 결과는 `s2_similarity_matches__arm{arm}.jsonl` 파일에 저장되었습니다.")
    lines.append("")
    
    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# =========================
# Main Entry Point
# =========================

def main():
    """Main entry point for similarity-based entity matching."""
    parser = argparse.ArgumentParser(
        description="Match similar entities between backup S2 and S1 using similarity scoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python match_similar_entities.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G

  # With custom similarity threshold
  python match_similar_entities.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G \\
    --similarity_threshold 0.95
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
        default=0.90,
        help="Minimum similarity score to consider a match (default: 0.90)"
    )
    parser.add_argument(
        "--backup_path",
        type=str,
        help="Path to backup file (optional, auto-detected if not provided)"
    )
    parser.add_argument(
        "--s2_results_path",
        type=str,
        help="Path to restored S2 results file (optional, auto-detected if not provided)"
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
    
    # Resolve backup file path
    if args.backup_path:
        backup_file = Path(args.backup_path)
        if not backup_file.is_absolute():
            backup_file = base_dir / backup_file
        backup_file = backup_file.resolve()
    else:
        # Auto-detect backup file (find most recent)
        s2_results_path_default = gen_dir / f"s2_results__s1arm{arm}__s2arm{arm}.jsonl"
        backup_patterns = [
            f"s2_results__s1arm{arm}__s2arm{arm}.jsonl.backup_*",
            f"s2_results__s1arm{arm}__s2arm{arm}.backup_*",
        ]
        backup_files = []
        for pattern in backup_patterns:
            backup_files.extend(gen_dir.glob(pattern))
        
        if not backup_files:
            print(f"Error: Backup file not found in {gen_dir}", file=sys.stderr)
            return 1
        
        # Sort by modification time (most recent first)
        backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        backup_file = backup_files[0]
    
    if not backup_file.exists():
        print(f"Error: Backup file does not exist: {backup_file}", file=sys.stderr)
        return 1
    
    # Resolve S2 results path
    if args.s2_results_path:
        s2_results_path = Path(args.s2_results_path)
        if not s2_results_path.is_absolute():
            s2_results_path = base_dir / s2_results_path
        s2_results_path = s2_results_path.resolve()
    else:
        s2_results_path = gen_dir / f"s2_results__s1arm{arm}__s2arm{arm}.jsonl"
    
    # Find S1 structure file
    s1_struct_path = gen_dir / f"stage1_struct__arm{arm}.jsonl"
    if not s1_struct_path.exists():
        print(f"Error: S1 structure file not found: {s1_struct_path}", file=sys.stderr)
        return 1
    
    # Output paths
    output_matches_path = gen_dir / f"s2_similarity_matches__arm{arm}.jsonl"
    output_report_path = gen_dir / f"s2_similarity_matches_report__arm{arm}.md"
    
    # Print configuration
    print("=" * 70)
    print("Similarity-Based Entity Matching")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Arm: {arm}")
    print(f"Backup file: {backup_file}")
    print(f"S1 structure: {s1_struct_path}")
    print(f"Restored S2: {s2_results_path}")
    print(f"Similarity threshold: {similarity_threshold}")
    print(f"Output matches: {output_matches_path}")
    print(f"Output report: {output_report_path}")
    print("=" * 70)
    print()
    
    # Perform matching
    try:
        match_result = match_similar_entities(
            backup_file=backup_file,
            s1_struct_path=s1_struct_path,
            s2_results_path=s2_results_path,
            output_matches_path=output_matches_path,
            similarity_threshold=similarity_threshold
        )
    except Exception as e:
        print(f"Error during matching: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    
    # Generate report
    generate_report(match_result, output_report_path, run_tag, arm)
    
    print("\n" + "=" * 70)
    print("Matching Complete!")
    print("=" * 70)
    print(f"✅ Total matches: {match_result['total_matches']}")
    print(f"✅ Auto-reuse (≥0.95): {match_result['auto_reuse_count']}")
    print(f"⚠️  Manual review (0.90-0.95): {match_result['manual_review_count']}")
    print()
    print("Output files:")
    print(f"  📄 Matches: {output_matches_path}")
    print(f"  📊 Report: {output_report_path}")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


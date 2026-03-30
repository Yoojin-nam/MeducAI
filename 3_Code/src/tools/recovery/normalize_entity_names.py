#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Entity 이름 정규화 스크립트

Entity 이름을 정규화하여 추가 매칭 가능성을 찾습니다.
약어 통일, 단수/복수 통일, 구두점 통일 등의 규칙을 적용하고,
정규화된 이름으로 entity_id를 재계산하여 재매칭을 수행합니다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# =========================
# Normalization Rules
# =========================

# Abbreviation mappings (backup -> normalized)
ABBREVIATION_MAP = {
    "SACD": "SCD",
    "pNET": "PanNET",
    "PCC": "PCN",  # Note: This might need manual review
    "FEG": "Gfe",  # Note: This might need manual review
}

# Singular/plural rules
# For anatomical structures: prefer plural
# For concepts: prefer singular
ANATOMICAL_PLURAL = {
    "gland": "glands",
    "node": "nodes",
    "ligament": "ligaments",
    "cell": "cells",
}

CONCEPT_SINGULAR = {
    "devices": "device",
    "effects": "effect",
    "malformations": "malformation",
}


def normalize_abbreviation(name: str) -> str:
    """Normalize abbreviations in entity names.
    
    Args:
        name: Entity name
    
    Returns:
        Normalized name with abbreviations unified
    """
    result = name
    for old_abbrev, new_abbrev in ABBREVIATION_MAP.items():
        # Replace in parentheses: (SACD) -> (SCD)
        result = re.sub(
            rf'\({re.escape(old_abbrev)}\)',
            f'({new_abbrev})',
            result,
            flags=re.IGNORECASE
        )
        # Replace standalone: SACD -> SCD (when not in parentheses)
        result = re.sub(
            rf'\b{re.escape(old_abbrev)}\b',
            new_abbrev,
            result,
            flags=re.IGNORECASE
        )
    return result


def normalize_singular_plural(name: str) -> str:
    """Normalize singular/plural forms.
    
    Rules:
    - Anatomical structures: prefer plural (glands, nodes, ligaments, cells)
    - Concepts: prefer singular (device, effect, malformation)
    
    Args:
        name: Entity name
    
    Returns:
        Normalized name with singular/plural unified
    """
    result = name
    
    # Apply anatomical plural rules
    for singular, plural in ANATOMICAL_PLURAL.items():
        # Replace singular with plural for anatomical structures
        # Pattern: "Parathyroid Gland" -> "Parathyroid Glands"
        result = re.sub(
            rf'\b{re.escape(singular.capitalize())}\b',
            plural.capitalize(),
            result
        )
        result = re.sub(
            rf'\b{re.escape(singular)}\b',
            plural,
            result,
            flags=re.IGNORECASE
        )
    
    # Apply concept singular rules
    for plural, singular in CONCEPT_SINGULAR.items():
        # Replace plural with singular for concepts
        # Pattern: "Devices" -> "Device" (when not anatomical)
        result = re.sub(
            rf'\b{re.escape(plural.capitalize())}\b',
            singular.capitalize(),
            result
        )
        result = re.sub(
            rf'\b{re.escape(plural)}\b',
            singular,
            result,
            flags=re.IGNORECASE
        )
    
    return result


def normalize_punctuation(name: str) -> str:
    """Normalize punctuation in entity names.
    
    Rules:
    - Remove colons after category names: "Cardiac MRI: Black Blood" -> "Cardiac MRI Black Blood"
    - Normalize parentheses: "(Views)" -> "Views" (when at end)
    - Normalize hyphens/slashes: "Agyria/Pachygyria" -> "Agyria-Pachygyria"
    
    Args:
        name: Entity name
    
    Returns:
        Normalized name with punctuation unified
    """
    result = name
    
    # Remove colons after category names (but keep in abbreviations like "Type I:")
    # Pattern: "Cardiac MRI: Black Blood" -> "Cardiac MRI Black Blood"
    result = re.sub(r'([A-Z][a-z]+ [A-Z]+):\s+', r'\1 ', result)
    
    # Normalize parentheses at end: "(Views)" -> "Views"
    result = re.sub(r'\s*\(([^)]+)\)$', r' \1', result)
    result = re.sub(r'^\s*\(([^)]+)\)\s*$', r'\1', result)
    
    # Normalize slashes to hyphens in parenthetical: "(A/B)" -> "(A-B)"
    result = re.sub(r'\(([^)]+)/([^)]+)\)', r'(\1-\2)', result)
    
    # Normalize standalone slashes (when not in URL or special context)
    # Pattern: "Agyria/Pachygyria" -> "Agyria-Pachygyria"
    result = re.sub(r'([A-Za-z]+)/([A-Za-z]+)', r'\1-\2', result)
    
    return result


def normalize_entity_name(name: str) -> str:
    """Apply all normalization rules to an entity name.
    
    Args:
        name: Original entity name
    
    Returns:
        Fully normalized entity name
    """
    result = name
    
    # Apply normalization rules in order
    result = normalize_abbreviation(result)
    result = normalize_singular_plural(result)
    result = normalize_punctuation(result)
    
    # Final cleanup: normalize whitespace
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result


def derive_entity_id(name: str) -> str:
    """Derive entity_id from normalized entity name.
    
    This matches the behavior of _derive in restore_s2_from_backup.py.
    
    Args:
        name: Entity name (will be normalized)
    
    Returns:
        Entity ID in format: DERIVED:sha1(normalized_name)[:12]
    """
    # Normalize for hashing (same as in restore_s2_from_backup.py)
    norm = re.sub(r"\s+", " ", str(name).strip().lower())
    h = hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]
    return f"DERIVED:{h}"


# =========================
# File Loading Functions
# =========================

def load_backup_entities(backup_file: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Load entities from backup file, grouped by group_id."""
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
    """Load entity_list from S1 structure for a specific group."""
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
    """Normalize Stage1 entity_list into a list of objects."""
    if not isinstance(raw, list):
        return []
    
    out: List[Dict[str, str]] = []
    seen_ids: set[str] = set()
    
    for item in raw:
        if isinstance(item, dict):
            name = str(item.get("entity_name") or item.get("name") or "").strip()
            eid = str(item.get("entity_id") or item.get("id") or "").strip()
            
            if not name:
                continue
            
            if not eid:
                eid = derive_entity_id(name)
            
            if eid not in seen_ids:
                seen_ids.add(eid)
                out.append({"entity_id": eid, "entity_name": name})
        elif isinstance(item, str):
            name = str(item).strip()
            if name:
                eid = derive_entity_id(name)
                if eid not in seen_ids:
                    seen_ids.add(eid)
                    out.append({"entity_id": eid, "entity_name": name})
    
    return out


def load_restored_entities(s2_results_path: Path) -> Dict[str, set[str]]:
    """Load already restored entities, grouped by group_id."""
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
# Normalization and Rematching
# =========================

def normalize_and_rematch(
    backup_entities: List[Dict[str, Any]],
    s1_entities: List[Dict[str, str]],
    restored_entity_ids: set[str]
) -> List[Dict[str, Any]]:
    """Normalize entity names and find additional matches.
    
    Args:
        backup_entities: List of backup entity records
        s1_entities: List of S1 entity objects
        restored_entity_ids: Set of already restored entity_ids (to exclude)
    
    Returns:
        List of normalized match records with format:
        {
            "backup_entity_id": "...",
            "backup_entity_name": "...",
            "backup_normalized_name": "...",
            "backup_normalized_id": "...",
            "s1_entity_id": "...",
            "s1_entity_name": "...",
            "s1_normalized_name": "...",
            "s1_normalized_id": "...",
            "match_type": "normalized_id_match" or "normalized_name_match"
        }
    """
    matches = []
    
    # Create normalized lookup maps for S1 entities
    s1_by_normalized_id: Dict[str, Dict[str, str]] = {}
    s1_by_normalized_name: Dict[str, Dict[str, str]] = {}
    
    for s1_ent in s1_entities:
        s1_id = s1_ent.get("entity_id", "")
        s1_name = s1_ent.get("entity_name", "")
        
        # Skip if already restored
        if s1_id in restored_entity_ids:
            continue
        
        # Normalize S1 entity name
        s1_normalized_name = normalize_entity_name(s1_name)
        s1_normalized_id = derive_entity_id(s1_normalized_name)
        
        # Index by normalized ID
        if s1_normalized_id not in s1_by_normalized_id:
            s1_by_normalized_id[s1_normalized_id] = {
                "entity_id": s1_id,
                "entity_name": s1_name,
                "normalized_name": s1_normalized_name,
                "normalized_id": s1_normalized_id
            }
        
        # Index by normalized name (for fallback matching)
        if s1_normalized_name.lower() not in s1_by_normalized_name:
            s1_by_normalized_name[s1_normalized_name.lower()] = {
                "entity_id": s1_id,
                "entity_name": s1_name,
                "normalized_name": s1_normalized_name,
                "normalized_id": s1_normalized_id
            }
    
    # Process backup entities
    for backup_ent in backup_entities:
        backup_id = backup_ent.get("entity_id", "")
        backup_name = backup_ent.get("entity_name", "")
        
        # Skip if already restored
        if backup_id in restored_entity_ids:
            continue
        
        # Normalize backup entity name
        backup_normalized_name = normalize_entity_name(backup_name)
        backup_normalized_id = derive_entity_id(backup_normalized_name)
        
        # Try to match by normalized ID first
        if backup_normalized_id in s1_by_normalized_id:
            s1_info = s1_by_normalized_id[backup_normalized_id]
            matches.append({
                "backup_entity_id": backup_id,
                "backup_entity_name": backup_name,
                "backup_normalized_name": backup_normalized_name,
                "backup_normalized_id": backup_normalized_id,
                "s1_entity_id": s1_info["entity_id"],
                "s1_entity_name": s1_info["entity_name"],
                "s1_normalized_name": s1_info["normalized_name"],
                "s1_normalized_id": s1_info["normalized_id"],
                "match_type": "normalized_id_match"
            })
        # Fallback: match by normalized name (case-insensitive)
        elif backup_normalized_name.lower() in s1_by_normalized_name:
            s1_info = s1_by_normalized_name[backup_normalized_name.lower()]
            matches.append({
                "backup_entity_id": backup_id,
                "backup_entity_name": backup_name,
                "backup_normalized_name": backup_normalized_name,
                "backup_normalized_id": backup_normalized_id,
                "s1_entity_id": s1_info["entity_id"],
                "s1_entity_name": s1_info["entity_name"],
                "s1_normalized_name": s1_info["normalized_name"],
                "s1_normalized_id": s1_info["normalized_id"],
                "match_type": "normalized_name_match"
            })
    
    return matches


# =========================
# Main Processing
# =========================

def normalize_entity_names(
    backup_file: Path,
    s1_struct_path: Path,
    s2_results_path: Path,
    output_matches_path: Path
) -> Dict[str, Any]:
    """Main function to normalize entity names and find additional matches.
    
    Args:
        backup_file: Path to backup S2 JSONL file
        s1_struct_path: Path to S1 structure JSONL file
        s2_results_path: Path to restored S2 results file (to exclude already matched)
        output_matches_path: Path to output normalized matches JSONL file
    
    Returns:
        Dictionary with normalization statistics
    """
    # Load data
    print("Loading backup entities...")
    backup_entities_by_group = load_backup_entities(backup_file)
    
    print("Loading restored entities...")
    restored_entities_by_group = load_restored_entities(s2_results_path)
    
    # Process each group
    all_matches = []
    group_stats = []
    normalization_changes = []
    
    for group_id in sorted(backup_entities_by_group.keys()):
        backup_entities = backup_entities_by_group[group_id]
        restored_entity_ids = restored_entities_by_group.get(group_id, set())
        
        # Load S1 entities for this group
        s1_entities = load_s1_entity_list(s1_struct_path, group_id)
        
        if not s1_entities:
            continue
        
        # Normalize and rematch
        matches = normalize_and_rematch(
            backup_entities,
            s1_entities,
            restored_entity_ids
        )
        
        all_matches.extend(matches)
        
        # Track normalization changes
        for match in matches:
            if match["backup_entity_name"] != match["backup_normalized_name"]:
                normalization_changes.append({
                    "group_id": group_id,
                    "original": match["backup_entity_name"],
                    "normalized": match["backup_normalized_name"],
                    "entity_id_original": match["backup_entity_id"],
                    "entity_id_normalized": match["backup_normalized_id"]
                })
        
        # Record stats
        group_stats.append({
            "group_id": group_id,
            "backup_entity_count": len(backup_entities),
            "s1_entity_count": len(s1_entities),
            "restored_count": len(restored_entity_ids),
            "normalized_matches": len(matches),
            "id_matches": sum(1 for m in matches if m["match_type"] == "normalized_id_match"),
            "name_matches": sum(1 for m in matches if m["match_type"] == "normalized_name_match")
        })
    
    # Calculate statistics
    total_matches = len(all_matches)
    id_matches = sum(1 for m in all_matches if m["match_type"] == "normalized_id_match")
    name_matches = sum(1 for m in all_matches if m["match_type"] == "normalized_name_match")
    entities_with_name_changes = len(normalization_changes)
    
    result = {
        "success": True,
        "total_matches": total_matches,
        "id_matches": id_matches,
        "name_matches": name_matches,
        "entities_with_name_changes": entities_with_name_changes,
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
    norm_result: Dict[str, Any],
    output_path: Path,
    run_tag: str,
    arm: str
) -> None:
    """Generate normalization report.
    
    Args:
        norm_result: Result dictionary from normalize_entity_names()
        output_path: Path to output markdown report file
        run_tag: Run tag
        arm: Arm identifier
    """
    lines = []
    lines.append("# Entity 이름 정규화 리포트")
    lines.append("")
    lines.append(f"**생성일**: {datetime.now().isoformat()}")
    lines.append(f"**RUN_TAG**: `{run_tag}`")
    lines.append(f"**ARM**: `{arm}`")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Summary statistics
    lines.append("## 1. 요약 통계")
    lines.append("")
    lines.append(f"- **총 정규화 매칭 수**: {norm_result['total_matches']}")
    lines.append(f"- **정규화 ID 매칭**: {norm_result['id_matches']}")
    lines.append(f"- **정규화 이름 매칭**: {norm_result['name_matches']}")
    lines.append(f"- **이름이 변경된 Entity 수**: {norm_result['entities_with_name_changes']}")
    lines.append("")
    
    # Group statistics
    lines.append("## 2. 그룹별 통계")
    lines.append("")
    lines.append("| 그룹 ID | 백업 Entity | S1 Entity | 복원됨 | 정규화 매칭 | ID 매칭 | 이름 매칭 |")
    lines.append("|---------|------------|-----------|--------|------------|--------|----------|")
    for stat in norm_result['group_stats']:
        lines.append(
            f"| {stat['group_id']} | {stat['backup_entity_count']} | "
            f"{stat['s1_entity_count']} | {stat['restored_count']} | "
            f"{stat['normalized_matches']} | {stat['id_matches']} | {stat['name_matches']} |"
        )
    lines.append("")
    
    # Normalization rules
    lines.append("## 3. 적용된 정규화 규칙")
    lines.append("")
    lines.append("### 약어 통일")
    lines.append("")
    for old, new in ABBREVIATION_MAP.items():
        lines.append(f"- `{old}` → `{new}`")
    lines.append("")
    
    lines.append("### 단수/복수 통일")
    lines.append("")
    lines.append("**해부학적 구조 (복수 선호)**:")
    for singular, plural in ANATOMICAL_PLURAL.items():
        lines.append(f"- `{singular}` → `{plural}`")
    lines.append("")
    lines.append("**개념 (단수 선호)**:")
    for plural, singular in CONCEPT_SINGULAR.items():
        lines.append(f"- `{plural}` → `{singular}`")
    lines.append("")
    
    lines.append("### 구두점 통일")
    lines.append("")
    lines.append("- 콜론 제거: `Cardiac MRI: Black Blood` → `Cardiac MRI Black Blood`")
    lines.append("- 괄호 정규화: `(Views)` → `Views`")
    lines.append("- 슬래시를 하이픈으로: `Agyria/Pachygyria` → `Agyria-Pachygyria`")
    lines.append("")
    
    # Warning about entity_id changes
    lines.append("## 4. 주의사항")
    lines.append("")
    lines.append("⚠️ **중요**: 정규화 후 `entity_id`가 변경될 수 있습니다.")
    lines.append("")
    lines.append("정규화된 이름으로 `entity_id`를 재계산하므로:")
    lines.append("- 기존 이미지 파일명과의 매칭에 영향이 있을 수 있습니다")
    lines.append("- 정규화 규칙은 의학적 정확성을 고려하여 신중하게 결정해야 합니다")
    lines.append("- 변경 사항은 반드시 검토 후 적용해야 합니다")
    lines.append("")
    
    # Next steps
    lines.append("## 5. 다음 단계")
    lines.append("")
    lines.append("### 정규화 매칭 결과 사용")
    lines.append("")
    lines.append(f"정규화를 통해 추가로 {norm_result['total_matches']}개 entity를 매칭할 수 있습니다.")
    lines.append("")
    lines.append("### 매칭 결과 파일")
    lines.append("")
    lines.append("상세 매칭 결과는 `s2_normalized_matches__arm{arm}.jsonl` 파일에 저장되었습니다.")
    lines.append("")
    
    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# =========================
# Main Entry Point
# =========================

def main():
    """Main entry point for entity name normalization."""
    parser = argparse.ArgumentParser(
        description="Normalize entity names and find additional matches",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python normalize_entity_names.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G

  # With explicit paths
  python normalize_entity_names.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G \\
    --backup_path 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG.jsonl.backup_20260102_113357
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
    output_matches_path = gen_dir / f"s2_normalized_matches__arm{arm}.jsonl"
    output_report_path = gen_dir / f"s2_normalization_report__arm{arm}.md"
    
    # Print configuration
    print("=" * 70)
    print("Entity Name Normalization")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Arm: {arm}")
    print(f"Backup file: {backup_file}")
    print(f"S1 structure: {s1_struct_path}")
    print(f"Restored S2: {s2_results_path}")
    print(f"Output matches: {output_matches_path}")
    print(f"Output report: {output_report_path}")
    print("=" * 70)
    print()
    print("⚠️  WARNING: Normalization will change entity_id values!")
    print("   This may affect image file matching.")
    print("   Review the results carefully before applying.")
    print()
    
    # Perform normalization
    try:
        norm_result = normalize_entity_names(
            backup_file=backup_file,
            s1_struct_path=s1_struct_path,
            s2_results_path=s2_results_path,
            output_matches_path=output_matches_path
        )
    except Exception as e:
        print(f"Error during normalization: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    
    # Generate report
    generate_report(norm_result, output_report_path, run_tag, arm)
    
    print("\n" + "=" * 70)
    print("Normalization Complete!")
    print("=" * 70)
    print(f"✅ Total normalized matches: {norm_result['total_matches']}")
    print(f"✅ ID matches: {norm_result['id_matches']}")
    print(f"✅ Name matches: {norm_result['name_matches']}")
    print(f"📝 Entities with name changes: {norm_result['entities_with_name_changes']}")
    print()
    print("Output files:")
    print(f"  📄 Matches: {output_matches_path}")
    print(f"  📊 Report: {output_report_path}")
    print()
    print("⚠️  Remember to review the results before applying!")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
유사도 기반 매칭 결과 검토 및 필터링 스크립트

잘못된 매칭을 수동으로 제거하고 의학적 정확성을 확인합니다.
특히 Type/Version 차이, Billroth I vs II 같은 중요한 차이를 감지합니다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# =========================
# Problematic Match Detection
# =========================

def is_potentially_problematic(match: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Detect potentially problematic matches that need manual review.
    
    Args:
        match: Match record with backup_entity_name, s1_entity_name, difference_type, similarity
    
    Returns:
        Tuple of (is_problematic, reason)
    """
    backup_name = match.get("backup_entity_name", "")
    s1_name = match.get("s1_entity_name", "")
    diff_type = match.get("difference_type", "")
    similarity = match.get("similarity", 0.0)
    
    # Normalize for comparison
    backup_norm = backup_name.lower().strip()
    s1_norm = s1_name.lower().strip()
    
    # 1. Type/Version differences - always review (e.g., Billroth I vs II, Type I vs Type II)
    if diff_type == "type_version":
        return (True, "Type/Version difference - may represent different concepts (e.g., Billroth I vs II)")
    
    # 2. Roman numeral differences (Type I, Type II, Type IVa, etc.)
    roman_numeral_pattern = r'\b(type\s+)?([ivxlcdm]+[a-z]?)\b'
    backup_roman = set(re.findall(roman_numeral_pattern, backup_norm, re.IGNORECASE))
    s1_roman = set(re.findall(roman_numeral_pattern, s1_norm, re.IGNORECASE))
    if backup_roman != s1_roman and (backup_roman or s1_roman):
        # Check if the roman numerals differ
        backup_nums = {r[1].lower() for r in backup_roman}
        s1_nums = {r[1].lower() for r in s1_roman}
        if backup_nums != s1_nums:
            return (True, f"Roman numeral difference: {backup_nums} vs {s1_nums}")
    
    # 3. Arabic number differences (Type 1, Type 2, etc.)
    arabic_pattern = r'\b(type\s+)?(\d+[a-z]?)\b'
    backup_arabic = set(re.findall(arabic_pattern, backup_norm, re.IGNORECASE))
    s1_arabic = set(re.findall(arabic_pattern, s1_norm, re.IGNORECASE))
    if backup_arabic != s1_arabic and (backup_arabic or s1_arabic):
        backup_nums = {r[1].lower() for r in backup_arabic}
        s1_nums = {r[1].lower() for r in s1_arabic}
        if backup_nums != s1_nums:
            return (True, f"Number difference: {backup_nums} vs {s1_nums}")
    
    # 4. Specific problematic patterns
    problematic_patterns = [
        (r'\bbillroth\s+i\b', r'\bbillroth\s+ii\b', "Billroth I vs II - different surgical procedures"),
        (r'\bbillroth\s+ii\b', r'\bbillroth\s+i\b', "Billroth II vs I - different surgical procedures"),
        (r'\bstage\s+i\b', r'\bstage\s+ii\b', "Stage I vs II - may represent different disease stages"),
        (r'\bstage\s+ii\b', r'\bstage\s+i\b', "Stage II vs I - may represent different disease stages"),
        (r'\bgrade\s+i\b', r'\bgrade\s+ii\b', "Grade I vs II - may represent different severity"),
        (r'\bgrade\s+ii\b', r'\bgrade\s+i\b', "Grade II vs I - may represent different severity"),
    ]
    
    for pattern1, pattern2, reason in problematic_patterns:
        if (re.search(pattern1, backup_norm) and re.search(pattern2, s1_norm)) or \
           (re.search(pattern2, backup_norm) and re.search(pattern1, s1_norm)):
            return (True, reason)
    
    # 5. Low similarity threshold (0.90-0.95) - needs review
    if 0.90 <= similarity < 0.95:
        return (True, f"Low similarity ({similarity:.3f}) - requires manual review")
    
    # 6. "other" difference type with low similarity
    if diff_type == "other" and similarity < 0.97:
        return (True, f"Other difference type with similarity {similarity:.3f}")
    
    return (False, "")


def classify_match_priority(match: Dict[str, Any]) -> str:
    """
    Classify match into priority categories for review.
    
    Returns:
        "reject" - likely incorrect (e.g., Type I vs Type II)
        "review_required" - needs manual review
        "auto_approve" - likely safe to approve
    """
    is_problematic, reason = is_potentially_problematic(match)
    
    if is_problematic:
        # Check if it's a clear reject case (type/version differences)
        if "Billroth" in reason or "Type" in reason and "different concepts" in reason:
            return "reject"
        elif "Roman numeral" in reason or "Number difference" in reason:
            return "reject"
        elif "Stage" in reason or "Grade" in reason:
            return "reject"
        else:
            return "review_required"
    
    similarity = match.get("similarity", 0.0)
    if similarity >= 0.95:
        return "auto_approve"
    else:
        return "review_required"


# =========================
# File I/O
# =========================

def load_matches(matches_file: Path) -> List[Dict[str, Any]]:
    """Load similarity matches from JSONL file."""
    matches = []
    
    if not matches_file.exists():
        print(f"Warning: Matches file not found: {matches_file}", file=sys.stderr)
        return matches
    
    with open(matches_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                match = json.loads(line)
                matches.append(match)
            except json.JSONDecodeError:
                continue
    
    return matches


def save_filtered_matches(matches: List[Dict[str, Any]], output_file: Path) -> None:
    """Save filtered matches to JSONL file."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        for match in matches:
            f.write(json.dumps(match, ensure_ascii=False) + "\n")


# =========================
# Review Report Generation
# =========================

def generate_review_report(
    matches: List[Dict[str, Any]],
    output_path: Path,
    run_tag: str,
    arm: str
) -> Dict[str, Any]:
    """
    Generate a detailed review report with problematic matches highlighted.
    
    Returns:
        Dictionary with statistics
    """
    # Classify all matches
    classified_matches = defaultdict(list)
    for match in matches:
        priority = classify_match_priority(match)
        classified_matches[priority].append(match)
    
    # Count problematic matches
    problematic_details = []
    for match in matches:
        is_problematic, reason = is_potentially_problematic(match)
        if is_problematic:
            problematic_details.append({
                "match": match,
                "reason": reason
            })
    
    # Generate report
    lines = []
    lines.append("# 유사도 매칭 결과 검토 리포트")
    lines.append("")
    lines.append(f"**생성일**: {datetime.now().isoformat()}")
    lines.append(f"**RUN_TAG**: `{run_tag}`")
    lines.append(f"**ARM**: `{arm}`")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Summary statistics
    lines.append("## 1. 검토 요약")
    lines.append("")
    lines.append(f"- **총 매칭 수**: {len(matches)}")
    lines.append(f"- **자동 승인 가능** (문제 없음, 유사도 ≥ 0.95): {len(classified_matches['auto_approve'])}")
    lines.append(f"- **검토 필요** (주의 필요): {len(classified_matches['review_required'])}")
    lines.append(f"- **거부 권장** (Type/Version 차이 등): {len(classified_matches['reject'])}")
    lines.append("")
    
    # Priority breakdown
    lines.append("### 우선순위별 분류")
    lines.append("")
    lines.append("| 우선순위 | 매칭 수 | 설명 |")
    lines.append("|---------|--------|------|")
    lines.append(f"| 자동 승인 | {len(classified_matches['auto_approve'])} | 문제없음, 바로 재사용 가능 |")
    lines.append(f"| 검토 필요 | {len(classified_matches['review_required'])} | 수동 검토 후 결정 |")
    lines.append(f"| 거부 권장 | {len(classified_matches['reject'])} | Type/Version 차이 등, 재사용 비권장 |")
    lines.append("")
    
    # Problematic matches details
    lines.append("## 2. 주의 필요 매칭 (Problematic Matches)")
    lines.append("")
    lines.append(f"총 {len(problematic_details)}개 매칭이 주의가 필요합니다.")
    lines.append("")
    
    # Group by reason
    by_reason = defaultdict(list)
    for item in problematic_details:
        by_reason[item["reason"]].append(item["match"])
    
    lines.append("### 사유별 분류")
    lines.append("")
    for reason, matches_list in sorted(by_reason.items(), key=lambda x: -len(x[1])):
        lines.append(f"#### {reason} ({len(matches_list)}개)")
        lines.append("")
        lines.append("| 백업 Entity | S1 Entity | 유사도 | 차이 유형 |")
        lines.append("|------------|----------|--------|----------|")
        for match in matches_list[:20]:  # Show first 20
            backup_name = match.get("backup_entity_name", "")
            s1_name = match.get("s1_entity_name", "")
            similarity = match.get("similarity", 0.0)
            diff_type = match.get("difference_type", "")
            lines.append(f"| `{backup_name}` | `{s1_name}` | {similarity:.3f} | {diff_type} |")
        if len(matches_list) > 20:
            lines.append(f"| ... (총 {len(matches_list)}개 중 20개만 표시) | ... | ... | ... |")
        lines.append("")
    
    # Reject recommendations
    lines.append("## 3. 거부 권장 매칭 (Reject Recommended)")
    lines.append("")
    reject_matches = classified_matches["reject"]
    lines.append(f"총 {len(reject_matches)}개 매칭이 거부를 권장합니다.")
    lines.append("")
    lines.append("| 백업 Entity | S1 Entity | 유사도 | 차이 유형 | 사유 |")
    lines.append("|------------|----------|--------|----------|------|")
    for match in reject_matches[:50]:  # Show first 50
        backup_name = match.get("backup_entity_name", "")
        s1_name = match.get("s1_entity_name", "")
        similarity = match.get("similarity", 0.0)
        diff_type = match.get("difference_type", "")
        is_problematic, reason = is_potentially_problematic(match)
        reason_short = reason[:50] if reason else ""
        lines.append(f"| `{backup_name}` | `{s1_name}` | {similarity:.3f} | {diff_type} | {reason_short} |")
    if len(reject_matches) > 50:
        lines.append(f"| ... (총 {len(reject_matches)}개 중 50개만 표시) | ... | ... | ... | ... |")
    lines.append("")
    
    # Next steps
    lines.append("## 4. 다음 단계")
    lines.append("")
    lines.append("### 4.1 자동 승인 매칭")
    lines.append("")
    lines.append(f"{len(classified_matches['auto_approve'])}개 매칭은 자동으로 승인되어 재사용할 수 있습니다.")
    lines.append("")
    lines.append("### 4.2 검토 필요 매칭")
    lines.append("")
    lines.append(f"{len(classified_matches['review_required'])}개 매칭은 수동 검토가 필요합니다.")
    lines.append("의학적 정확성을 확인한 후 재사용 여부를 결정하세요.")
    lines.append("")
    lines.append("### 4.3 거부 권장 매칭")
    lines.append("")
    lines.append(f"{len(classified_matches['reject'])}개 매칭은 거부를 권장합니다.")
    lines.append("Type/Version 차이, Billroth I vs II 같은 경우는 다른 개념이므로 재사용하지 않는 것이 좋습니다.")
    lines.append("")
    lines.append("### 4.4 필터링 방법")
    lines.append("")
    lines.append("다음 명령어로 거부 권장 매칭을 제외하고 필터링할 수 있습니다:")
    lines.append("")
    lines.append("```bash")
    lines.append(f"python3 review_similarity_matches.py --base_dir . --run_tag {run_tag} --arm {arm} \\")
    lines.append("  --filter_reject")
    lines.append("```")
    lines.append("")
    
    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    return {
        "total_matches": len(matches),
        "auto_approve": len(classified_matches["auto_approve"]),
        "review_required": len(classified_matches["review_required"]),
        "reject": len(classified_matches["reject"]),
        "problematic_count": len(problematic_details)
    }


# =========================
# Filtering Functions
# =========================

def filter_matches(
    matches: List[Dict[str, Any]],
    filter_reject: bool = False,
    min_similarity: float = 0.0,
    exclude_difference_types: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Filter matches based on criteria.
    
    Args:
        matches: List of match records
        filter_reject: If True, exclude matches classified as "reject"
        min_similarity: Minimum similarity score to include
        exclude_difference_types: List of difference types to exclude
    
    Returns:
        Filtered list of matches
    """
    filtered = []
    exclude_types = set(exclude_difference_types or [])
    
    for match in matches:
        # Filter by similarity
        similarity = match.get("similarity", 0.0)
        if similarity < min_similarity:
            continue
        
        # Filter by difference type
        diff_type = match.get("difference_type", "")
        if diff_type in exclude_types:
            continue
        
        # Filter reject if requested
        if filter_reject:
            priority = classify_match_priority(match)
            if priority == "reject":
                continue
        
        filtered.append(match)
    
    return filtered


# =========================
# Main Entry Point
# =========================

def main():
    """Main entry point for similarity match review."""
    parser = argparse.ArgumentParser(
        description="Review and filter similarity-based entity matches",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate review report
  python review_similarity_matches.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G

  # Filter out reject-recommended matches
  python review_similarity_matches.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G \\
    --filter_reject --output_approved

  # Filter with custom similarity threshold
  python review_similarity_matches.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G \\
    --min_similarity 0.95 --output_approved
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
        "--filter_reject",
        action="store_true",
        help="Filter out reject-recommended matches"
    )
    parser.add_argument(
        "--min_similarity",
        type=float,
        default=0.0,
        help="Minimum similarity score to include (default: 0.0, no filter)"
    )
    parser.add_argument(
        "--exclude_diff_types",
        type=str,
        nargs="+",
        help="Difference types to exclude (e.g., type_version abbreviation)"
    )
    parser.add_argument(
        "--output_approved",
        action="store_true",
        help="Output approved/filtered matches to a new file"
    )
    parser.add_argument(
        "--matches_file",
        type=str,
        help="Path to matches file (optional, auto-detected if not provided)"
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
    
    # Resolve matches file path
    if args.matches_file:
        matches_file = Path(args.matches_file)
        if not matches_file.is_absolute():
            matches_file = base_dir / matches_file
        matches_file = matches_file.resolve()
    else:
        matches_file = gen_dir / f"s2_similarity_matches__arm{arm}.jsonl"
    
    if not matches_file.exists():
        print(f"Error: Matches file not found: {matches_file}", file=sys.stderr)
        print(f"Please run match_similar_entities.py first to generate matches.", file=sys.stderr)
        return 1
    
    # Output paths
    review_report_path = gen_dir / f"s2_similarity_matches_review__arm{arm}.md"
    approved_matches_path = gen_dir / f"s2_similarity_matches_approved__arm{arm}.jsonl"
    
    # Print configuration
    print("=" * 70)
    print("Similarity Match Review and Filtering")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Arm: {arm}")
    print(f"Matches file: {matches_file}")
    print(f"Filter reject: {args.filter_reject}")
    print(f"Min similarity: {args.min_similarity}")
    print(f"Output approved: {args.output_approved}")
    print(f"Review report: {review_report_path}")
    if args.output_approved:
        print(f"Approved matches: {approved_matches_path}")
    print("=" * 70)
    print()
    
    # Load matches
    print("Loading matches...")
    matches = load_matches(matches_file)
    print(f"Loaded {len(matches)} matches")
    print()
    
    if not matches:
        print("No matches found to review.", file=sys.stderr)
        return 1
    
    # Generate review report
    print("Generating review report...")
    stats = generate_review_report(matches, review_report_path, run_tag, arm)
    print(f"✅ Review report generated: {review_report_path}")
    print()
    
    # Print statistics
    print("Review Statistics:")
    print(f"  Total matches: {stats['total_matches']}")
    print(f"  Auto-approve: {stats['auto_approve']}")
    print(f"  Review required: {stats['review_required']}")
    print(f"  Reject recommended: {stats['reject']}")
    print(f"  Problematic: {stats['problematic_count']}")
    print()
    
    # Filter matches if requested
    if args.output_approved or args.filter_reject or args.min_similarity > 0.0 or args.exclude_diff_types:
        print("Filtering matches...")
        filtered = filter_matches(
            matches,
            filter_reject=args.filter_reject,
            min_similarity=args.min_similarity,
            exclude_difference_types=args.exclude_diff_types
        )
        print(f"Filtered: {len(matches)} → {len(filtered)} matches ({len(matches) - len(filtered)} removed)")
        print()
        
        if args.output_approved:
            save_filtered_matches(filtered, approved_matches_path)
            print(f"✅ Approved matches saved: {approved_matches_path}")
            print()
    
    print("=" * 70)
    print("Review Complete!")
    print("=" * 70)
    print(f"📊 Review report: {review_report_path}")
    if args.output_approved:
        print(f"✅ Approved matches: {approved_matches_path}")
    print()
    print("Next steps:")
    print("1. Review the report to identify problematic matches")
    print("2. Use --filter_reject to exclude reject-recommended matches")
    print("3. Use --output_approved to generate filtered matches file")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


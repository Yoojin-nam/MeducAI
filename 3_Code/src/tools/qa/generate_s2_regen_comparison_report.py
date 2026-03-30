#!/usr/bin/env python3
"""
Generate a comparison report showing:
- Original S2 card content
- S5 validation feedback
- Regenerated S2 card content

For entities where S2 regeneration was executed.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read JSONL file and return list of records."""
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_card_index(s2_results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Build index of cards: card_uid -> card content.
    card_uid = "{group_id}::{entity_id}__{card_role}__{card_idx}"
    """
    index = {}
    for entity in s2_results:
        group_id = entity.get("group_id", "")
        entity_id = entity.get("entity_id", "")
        entity_name = entity.get("entity_name", "")
        
        for idx, card in enumerate(entity.get("anki_cards", [])):
            card_role = card.get("card_role", "")
            card_id = f"{entity_id}__{card_role}__{idx}"
            card_uid = f"{group_id}::{card_id}"
            
            index[card_uid] = {
                "group_id": group_id,
                "entity_id": entity_id,
                "entity_name": entity_name,
                "card_role": card_role,
                "card_idx": idx,
                "card_type": card.get("card_type", ""),
                "front": card.get("front", ""),
                "back": card.get("back", ""),
                "options": card.get("options", []),
                "correct_index": card.get("correct_index"),
            }
    return index


def build_s5_feedback_index(s5_validation: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Build index of S5 feedback: card_uid -> S5 feedback.
    """
    index = {}
    for group in s5_validation:
        group_id = group.get("group_id", "")
        s2_validation = group.get("s2_cards_validation", {})
        
        for card in s2_validation.get("cards", []):
            card_id = card.get("card_id", "")
            card_uid = f"{group_id}::{card_id}"
            
            # Extract issues
            card_issues = card.get("issues", [])
            image_issues = card.get("card_image_validation", {}).get("issues", [])
            
            # Extract scores
            card_regen_score = card.get("card_regeneration_trigger_score")
            image_regen_score = card.get("image_regeneration_trigger_score")
            
            index[card_uid] = {
                "card_issues": card_issues,
                "image_issues": image_issues,
                "card_regen_score": card_regen_score,
                "image_regen_score": image_regen_score,
                "blocking_error": card.get("blocking_error", False),
                "technical_accuracy": card.get("technical_accuracy"),
                "educational_quality": card.get("educational_quality"),
            }
    return index


def format_card_content(card: Dict[str, Any]) -> str:
    """Format card content for display."""
    lines = []
    
    # Card type and role
    card_type = card.get("card_type", "")
    lines.append(f"**Type**: {card_type}")
    
    # Front
    front = card.get("front", "").strip()
    lines.append(f"\n**Front (Question)**:")
    lines.append(f"{front}")
    
    # Options for MCQ
    if card_type == "MCQ" and card.get("options"):
        lines.append(f"\n**Options**:")
        labels = ["A", "B", "C", "D", "E", "F", "G", "H"]
        for i, opt in enumerate(card.get("options", [])):
            label = labels[i] if i < len(labels) else str(i + 1)
            marker = " ✓" if i == card.get("correct_index") else ""
            lines.append(f"{label}. {opt}{marker}")
    
    # Back
    back = card.get("back", "").strip()
    lines.append(f"\n**Back (Answer)**:")
    lines.append(f"{back}")
    
    return "\n".join(lines)


def format_s5_feedback(feedback: Dict[str, Any]) -> str:
    """Format S5 feedback for display."""
    lines = []
    
    # Scores
    card_score = feedback.get("card_regen_score")
    image_score = feedback.get("image_regen_score")
    
    lines.append(f"**Card Regeneration Score**: {card_score if card_score is not None else 'N/A'}")
    lines.append(f"**Image Regeneration Score**: {image_score if image_score is not None else 'N/A'}")
    
    # Quality scores
    tech_accuracy = feedback.get("technical_accuracy")
    edu_quality = feedback.get("educational_quality")
    
    if tech_accuracy is not None:
        lines.append(f"**Technical Accuracy**: {tech_accuracy}/5")
    if edu_quality is not None:
        lines.append(f"**Educational Quality**: {edu_quality}/5")
    
    # Card issues
    card_issues = feedback.get("card_issues", [])
    if card_issues:
        lines.append(f"\n**Card Issues**:")
        for i, issue in enumerate(card_issues, 1):
            severity = issue.get("severity", "")
            desc = issue.get("description", "")
            lines.append(f"{i}. [{severity}] {desc}")
            
            # Evidence
            evidence = issue.get("evidence_ref") or issue.get("rag_evidence")
            if evidence:
                if isinstance(evidence, list):
                    for ev in evidence:
                        if isinstance(ev, dict):
                            source = ev.get("source_id") or ev.get("source_excerpt", "")
                            if source:
                                lines.append(f"   - Evidence: {source}")
                elif isinstance(evidence, str):
                    lines.append(f"   - Evidence: {evidence}")
    
    # Image issues
    image_issues = feedback.get("image_issues", [])
    if image_issues:
        lines.append(f"\n**Image Issues**:")
        for i, issue in enumerate(image_issues, 1):
            severity = issue.get("severity", "")
            desc = issue.get("description", "")
            lines.append(f"{i}. [{severity}] {desc}")
            
            # Hints
            hints = issue.get("hints", [])
            if hints:
                for hint in hints:
                    lines.append(f"   - Hint: {hint}")
    
    return "\n".join(lines)


def generate_comparison_report(
    run_dir: Path,
    out_path: Path,
) -> None:
    """Generate S2 regeneration comparison report."""
    
    # File paths
    s2_original_path = run_dir / "s2_results__s1armG__s2armG.jsonl"
    if not s2_original_path.exists():
        # Try legacy format
        s2_original_path = run_dir / "s2_results__armG.jsonl"
    
    s2_repaired_path = run_dir / "s2_results__s1armG__s2armG__repaired.jsonl"
    if not s2_repaired_path.exists():
        s2_repaired_path = run_dir / "s2_results__armG__repaired.jsonl"
    
    s5_validation_path = run_dir / "s5_validation__armG.jsonl"
    
    # Check files exist
    if not s2_original_path.exists():
        raise FileNotFoundError(f"Original S2 results not found: {s2_original_path}")
    if not s2_repaired_path.exists():
        raise FileNotFoundError(f"Repaired S2 results not found: {s2_repaired_path}")
    if not s5_validation_path.exists():
        raise FileNotFoundError(f"S5 validation not found: {s5_validation_path}")
    
    # Load data
    print("Loading data...")
    s2_original = read_jsonl(s2_original_path)
    s2_repaired = read_jsonl(s2_repaired_path)
    s5_validation = read_jsonl(s5_validation_path)
    
    # Build indexes
    print("Building indexes...")
    original_cards = build_card_index(s2_original)
    repaired_cards = build_card_index(s2_repaired)
    s5_feedback = build_s5_feedback_index(s5_validation)
    
    # Find cards that were regenerated
    regenerated_card_uids = set(repaired_cards.keys())
    
    print(f"Found {len(regenerated_card_uids)} regenerated cards")
    
    # Filter to only cards with low scores (actually regenerated)
    cards_to_report = []
    for card_uid in regenerated_card_uids:
        feedback = s5_feedback.get(card_uid, {})
        card_score = feedback.get("card_regen_score")
        
        # Only include cards where regeneration was actually triggered (score < 90)
        if card_score is not None and card_score < 90.0:
            cards_to_report.append(card_uid)
    
    print(f"Found {len(cards_to_report)} cards with card_regen_score < 90")
    
    # Sort by group_id, entity_id, card_role
    cards_to_report.sort(key=lambda uid: (
        repaired_cards[uid]["group_id"],
        repaired_cards[uid]["entity_id"],
        repaired_cards[uid]["card_role"],
    ))
    
    # Generate report
    print(f"Generating report to {out_path}...")
    
    with out_path.open("w", encoding="utf-8") as f:
        # Header
        f.write("# S2 Card Regeneration Comparison Report\n\n")
        f.write(f"**Generated**: {Path(__file__).name}\n\n")
        f.write(f"**Source Data**:\n")
        f.write(f"- Original S2: `{s2_original_path.name}`\n")
        f.write(f"- Repaired S2: `{s2_repaired_path.name}`\n")
        f.write(f"- S5 Validation: `{s5_validation_path.name}`\n\n")
        f.write(f"**Summary**:\n")
        f.write(f"- Total regenerated cards: {len(regenerated_card_uids)}\n")
        f.write(f"- Cards with card_regen_score < 90: {len(cards_to_report)}\n\n")
        f.write("---\n\n")
        
        # Table of contents
        f.write("## Table of Contents\n\n")
        for i, card_uid in enumerate(cards_to_report, 1):
            card = repaired_cards[card_uid]
            f.write(f"{i}. [{card['entity_name']} - {card['card_role']}](#{i}-{card['entity_id'].replace(':', '').lower()}-{card['card_role'].lower()})\n")
        f.write("\n---\n\n")
        
        # Individual card comparisons
        for i, card_uid in enumerate(cards_to_report, 1):
            original_card = original_cards.get(card_uid, {})
            repaired_card = repaired_cards[card_uid]
            feedback = s5_feedback.get(card_uid, {})
            
            # Card header
            f.write(f"## {i}. {repaired_card['entity_name']} - {repaired_card['card_role']}\n\n")
            f.write(f"**Card UID**: `{card_uid}`\n\n")
            f.write(f"**Group ID**: `{repaired_card['group_id']}`\n\n")
            f.write(f"**Entity ID**: `{repaired_card['entity_id']}`\n\n")
            
            # S5 Feedback
            f.write("### 📋 S5 Feedback\n\n")
            f.write(format_s5_feedback(feedback))
            f.write("\n\n")
            
            # Comparison table
            f.write("### 🔄 Comparison\n\n")
            f.write("<table>\n")
            f.write("<tr>\n")
            f.write("<th width=\"50%\">❌ Original Content</th>\n")
            f.write("<th width=\"50%\">✅ Regenerated Content</th>\n")
            f.write("</tr>\n")
            f.write("<tr>\n")
            f.write("<td valign=\"top\">\n\n")
            
            if original_card:
                # Convert markdown to HTML-safe format
                original_content = format_card_content(original_card)
                # Replace newlines with <br> for HTML table
                original_content_html = original_content.replace("\n", "<br>")
                f.write(original_content_html)
            else:
                f.write("<em>Original content not found</em>")
            
            f.write("\n\n</td>\n")
            f.write("<td valign=\"top\">\n\n")
            
            # Regenerated content
            repaired_content = format_card_content(repaired_card)
            repaired_content_html = repaired_content.replace("\n", "<br>")
            f.write(repaired_content_html)
            
            f.write("\n\n</td>\n")
            f.write("</tr>\n")
            f.write("</table>\n\n")
            
            # Divider
            f.write("---\n\n")
    
    print(f"✅ Report generated: {out_path}")
    print(f"   Total cards in report: {len(cards_to_report)}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate S2 regeneration comparison report"
    )
    parser.add_argument(
        "--run_dir",
        type=str,
        required=True,
        help="Path to run directory (e.g., 2_Data/metadata/generated/FINAL_DISTRIBUTION)",
    )
    parser.add_argument(
        "--out_path",
        type=str,
        required=True,
        help="Output path for MD report",
    )
    
    args = parser.parse_args()
    
    run_dir = Path(args.run_dir).resolve()
    out_path = Path(args.out_path).resolve()
    
    generate_comparison_report(run_dir, out_path)


if __name__ == "__main__":
    main()


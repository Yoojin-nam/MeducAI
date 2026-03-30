#!/usr/bin/env python3
"""Convert S2 results JSONL to markdown for viewing."""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.path_resolver import resolve_s2_results_path


def format_card_markdown(card: Dict[str, Any], card_index: int) -> str:
    """Format a single card as markdown."""
    card_role = card.get("card_role", "?")
    card_type = card.get("card_type", "?")
    front = card.get("front", "")
    back = card.get("back", "")
    
    md_lines = [
        f"### 카드 {card_index + 1}: {card_role} ({card_type})",
        "",
        "#### Front (앞면)",
        "",
        "```",
        front,
        "```",
        "",
        "#### Back (뒷면)",
        "",
        "```",
        back,
        "```",
        ""
    ]
    
    # MCQ options if present
    if card_type.upper() in ("MCQ", "MCQ_VIGNETTE"):
        options = card.get("options", [])
        correct_index = card.get("correct_index")
        
        if options:
            md_lines.append("#### 선택지 (Options)")
            md_lines.append("")
            for i, opt in enumerate(options):
                marker = "✅" if i == correct_index else "  "
                md_lines.append(f"{marker} {i+1}. {opt}")
            md_lines.append("")
            if correct_index is not None:
                md_lines.append(f"**정답 인덱스**: `{correct_index}` (선택지 {correct_index + 1})")
                md_lines.append("")
    
    # Image hint if present
    image_hint = card.get("image_hint")
    if image_hint:
        md_lines.append("#### Image Hint")
        md_lines.append("")
        md_lines.append("```json")
        md_lines.append(json.dumps(image_hint, ensure_ascii=False, indent=2))
        md_lines.append("```")
        md_lines.append("")
    
    # Tags
    tags = card.get("tags", [])
    if tags:
        md_lines.append(f"**Tags**: `{', '.join(tags)}`")
        md_lines.append("")
    
    return "\n".join(md_lines)


def convert_s2_to_markdown(
    s2_jsonl_path: Path,
    output_md_path: Path,
    max_entities: int = None
) -> None:
    """Convert S2 results JSONL to markdown."""
    
    if not s2_jsonl_path.exists():
        raise FileNotFoundError(f"S2 results file not found: {s2_jsonl_path}")
    
    md_lines = [
        "# S2 결과 리포트",
        "",
        f"**파일**: `{s2_jsonl_path.name}`",
        "",
        "---",
        ""
    ]
    
    entity_count = 0
    total_cards = 0
    
    with open(s2_jsonl_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Warning: Skipping invalid JSON at line {line_num}: {e}")
                continue
            
            if max_entities and entity_count >= max_entities:
                break
            
            group_id = record.get("group_id", "?")
            entity_id = record.get("entity_id", "?")
            entity_name = record.get("entity_name", "?")
            cards = record.get("anki_cards", [])
            
            md_lines.extend([
                f"## 엔티티: {entity_name}",
                "",
                f"- **Group ID**: `{group_id}`",
                f"- **Entity ID**: `{entity_id}`",
                f"- **카드 수**: {len(cards)}",
                "",
                "---",
                ""
            ])
            
            for i, card in enumerate(cards):
                md_lines.append(format_card_markdown(card, i))
                md_lines.append("---")
                md_lines.append("")
            
            entity_count += 1
            total_cards += len(cards)
    
    md_lines.extend([
        "",
        "## 요약",
        "",
        f"- **엔티티 수**: {entity_count}",
        f"- **총 카드 수**: {total_cards}",
        ""
    ])
    
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.write_text("\n".join(md_lines), encoding='utf-8')
    
    print(f"✅ 마크다운 리포트 생성 완료: {output_md_path}")
    print(f"   - 엔티티: {entity_count}개")
    print(f"   - 카드: {total_cards}개")


def main():
    parser = argparse.ArgumentParser(description="Convert S2 results JSONL to markdown")
    parser.add_argument("--base_dir", type=str, default=".", help="Base directory")
    parser.add_argument("--run_tag", type=str, required=True, help="RUN_TAG")
    parser.add_argument("--arm", type=str, default="A", help="Arm (default: A)")
    parser.add_argument("--output", type=str, help="Output markdown file path (default: auto-generated)")
    parser.add_argument("--max_entities", type=int, help="Maximum number of entities to include")
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    run_tag = args.run_tag
    arm = args.arm.upper()
    
    out_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    s2_jsonl_path = resolve_s2_results_path(out_dir, arm)
    
    if args.output:
        output_md_path = Path(args.output)
    else:
        output_md_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"s2_results__arm{arm}.md"
    
    convert_s2_to_markdown(s2_jsonl_path, output_md_path, max_entities=args.max_entities)


if __name__ == "__main__":
    main()



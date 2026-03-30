#!/usr/bin/env python3
"""
Export FINAL Anki deck with integrated REGEN content.

Card-level decision logic:
- CARD_REGEN: regenerated content + regenerated image
- IMAGE_REGEN: baseline content + regenerated image
- PASS: baseline content + baseline image
"""

import argparse
import json
import sys
import re
import html
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import genanki
except ImportError:
    print("Error: genanki package is required. Install with: pip install genanki", file=sys.stderr)
    sys.exit(1)


# S5 Decision threshold
REGEN_THRESHOLD = 80.0

# CSS for Anki cards
BASE_CSS = """
.card { font-family: Arial; font-size: 18px; text-align: left; color: black; background-color: white; }
div { margin: 0; padding: 0; }
img { display: block; margin: 0 auto; }
.meducai-imgwrap { margin: 0; padding: 0; text-align: center; }
.meducai-img { max-width: 100%; max-height: 45vh; width: auto; height: auto; object-fit: contain; }
"""

def format_back_html(text: str, *, remove_answer_line: bool) -> str:
    """
    Improve Anki back/explanation readability:
    - Insert line break BEFORE "근거:" (even if the source has no newlines)
    - Insert line break BEFORE '*' bullets
    - Render as HTML using <br>
    """
    if not text:
        return ""
    t = str(text)
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    # remove markdown bold markers (keep content)
    t = t.replace("**", "")
    t = t.strip()

    # If the model/template doesn't preserve raw newlines, force structure here.
    # Inject newline before answer headers / section header "근거:" when it's mid-line.
    t = re.sub(r"([^\n])\s*((?:정답|Answer)\s*[:：])", r"\1\n\2", t, flags=re.IGNORECASE)
    t = re.sub(r"([^\n])\s*(근거\s*[:：])", r"\1\n\2", t)
    # Inject newline before '*' bullets when they're mid-line.
    t = re.sub(r"([^\n])\s*(\*\s+)", r"\1\n\2", t)

    lines = [ln.strip() for ln in t.split("\n") if ln.strip()]
    out: List[str] = []

    def _style_inline(raw: str) -> str:
        """
        Escape user text, then add a few safe <b> highlights:
        - A./B./C./D./E. (and A)/B) variants)
        - Answer (word)
        - 오답포인트
        """
        s = html.escape(str(raw))
        s = re.sub(r"(?i)\bAnswer\b", r"<b>Answer</b>", s)
        s = s.replace("오답포인트", "<b>오답포인트</b>")
        s = re.sub(r"(?<![A-Za-z0-9])([A-E])([\\.)])", r"<b>\1\2</b>", s)
        return s

    def _is_answer_header(line: str) -> bool:
        return re.match(r"^(정답|Answer)\s*[:：]", line, re.IGNORECASE) is not None

    for ln in lines:
        # Remove answer line only when requested (MCQ) to prevent duplication with Answer field.
        # For BASIC, keep "정답:" lines (these are often the entire answer).
        if remove_answer_line and _is_answer_header(ln):
            continue

        # "근거: ..." (header, optionally with inline content)
        m = re.match(r"^(근거)\s*[:：]\s*(.*)$", ln)
        if m:
            # NOTE: keep exactly ONE line break before this header (via join()).
            out.append("<b>근거:</b>")
            rest = (m.group(2) or "").strip()
            if rest:
                out.append(_style_inline(rest))
            continue

        # Bullet lines
        if ln.startswith("* "):
            out.append(_style_inline(ln))  # keep '*' as requested
            continue

        out.append(_style_inline(ln))

    # Join with <br>. Keep any explicit "<br>" tokens (above) to create extra spacing.
    return "<br>".join(out)


def make_basic_model(model_id: int) -> genanki.Model:
    """Basic note type."""
    return genanki.Model(
        model_id,
        "MeducAI Basic",
        fields=[{"name": "Front"}, {"name": "Back"}],
        templates=[{
            "name": "Card 1",
            "qfmt": "{{Front}}",
            "afmt": "{{Front}}<hr id='answer'>{{Back}}",
        }],
        css=BASE_CSS,
    )


def make_mcq_model(model_id: int) -> genanki.Model:
    """MCQ note type."""
    return genanki.Model(
        model_id,
        "MeducAI MCQ",
        fields=[
            {"name": "Question"},
            {"name": "Options"},
            {"name": "Answer"},
            {"name": "Explanation"},
        ],
        templates=[{
            "name": "Card 1",
            "qfmt": "{{Question}}<br><br>{{Options}}",
            "afmt": "{{Question}}<br><br>{{Options}}<hr id='answer'>{{Answer}}<br>{{Explanation}}",
        }],
        css=BASE_CSS,
    )


def load_s5_decisions(s5_path: Path, threshold: float) -> Dict[str, str]:
    """Load S5 decisions by card_uid from S5 JSONL (legacy, score-based)."""
    decisions = {}
    
    with s5_path.open('r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            group_id = record.get('group_id', '')
            s2 = record.get('s2_cards_validation', {})
            cards = s2.get('cards', [])
            
            for card in cards:
                card_id = card.get('card_id', '')
                card_regen_score = card.get('card_regeneration_trigger_score', 0) or 0
                image_regen_score = card.get('image_regeneration_trigger_score', 0) or 0
                
                # Lower score = needs regeneration (score < threshold means poor quality)
                if card_regen_score < threshold:
                    decision = 'CARD_REGEN'
                elif image_regen_score < threshold:
                    decision = 'IMAGE_REGEN'
                else:
                    decision = 'PASS'
                
                card_uid = f"{group_id}::{card_id}"
                decisions[card_uid] = decision
    
    return decisions


def load_decisions_from_diff(card_regen_keys_path: Path, s5_path: Optional[Path] = None, threshold: float = 80.0) -> Dict[str, str]:
    """Load CARD_REGEN from diff file + IMAGE_REGEN from S5 scores."""
    decisions = {}
    
    # 1. Load CARD_REGEN from diff file
    with card_regen_keys_path.open('r', encoding='utf-8') as f:
        card_regen_keys = set(json.load(f))
    
    for key in card_regen_keys:
        decisions[key] = 'CARD_REGEN'
    
    print(f"  Loaded {len(card_regen_keys)} CARD_REGEN keys from diff")
    
    # 2. Load IMAGE_REGEN from S5 scores (if s5_path provided)
    if s5_path and s5_path.exists():
        image_regen_count = 0
        with s5_path.open('r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                group_id = record.get('group_id', '')
                s2 = record.get('s2_cards_validation', {})
                cards = s2.get('cards', [])
                
                for card in cards:
                    card_id = card.get('card_id', '')
                    card_uid = f"{group_id}::{card_id}"
                    
                    # Skip if already CARD_REGEN
                    if card_uid in decisions:
                        continue
                    
                    image_regen_score = card.get('image_regeneration_trigger_score', 0) or 0
                    
                    # IMAGE_REGEN if score < threshold
                    if image_regen_score < threshold:
                        decisions[card_uid] = 'IMAGE_REGEN'
                        image_regen_count += 1
        
        print(f"  Loaded {image_regen_count} IMAGE_REGEN keys from S5 scores")
    
    return decisions


def load_s5_decisions_from_csv(cards_csv_path: Path) -> Dict[str, str]:
    """Load S5 decisions from Cards.csv (assignment-time decisions)."""
    import csv
    decisions = {}
    
    with cards_csv_path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            card_uid = row.get('card_uid', '')
            decision = row.get('s5_decision', 'PASS')
            if card_uid and decision:
                decisions[card_uid] = decision
    
    return decisions


def load_s2_content(s2_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load card content from S2 results."""
    content = {}
    
    with s2_path.open('r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            group_id = record.get('group_id', '')
            entity_id = record.get('entity_id', '')
            group_path = record.get('group_path', '')
            anki_cards = record.get('anki_cards', [])
            
            for idx, card in enumerate(anki_cards):
                card_role = card.get('card_role', '')
                card_uid = f'{group_id}::{entity_id}__{card_role}__{idx}'
                
                # Store complete card data
                content[card_uid] = {
                    'card_type': (card.get('card_type', '') or 'BASIC').upper(),
                    'front': (card.get('front', '') or '').replace('**', '').strip(),
                    'back': (card.get('back', '') or '').replace('**', '').strip(),
                    'options': card.get('options', []),
                    'correct_index': card.get('correct_index', 0),
                    'group_path': group_path,
                    'group_id': group_id,
                    'entity_id': entity_id,
                    'card_role': card_role,
                }
    
    return content


def find_image(images_dir: Path, group_id: str, entity_id: str, card_role: str, suffix: str = "") -> Optional[Path]:
    """Find image file."""
    # Normalize entity_id: DERIVED:xxx → DERIVED_xxx
    entity_id_normalized = entity_id.replace(':', '_')
    
    # Build filename
    filename = f"IMG__FINAL_DISTRIBUTION__{group_id}__{entity_id_normalized}__{card_role}{suffix}.jpg"
    image_path = images_dir / filename
    
    if image_path.exists():
        return image_path
    
    return None


def make_image_html(image_path: Path) -> str:
    """Generate HTML for image."""
    return f'<div class="meducai-imgwrap"><img src="{image_path.name}" class="meducai-img" /></div>'


def format_mcq_options(options: List[str], correct_index: int) -> str:
    """Format MCQ options as HTML."""
    option_labels = ["A", "B", "C", "D", "E"]
    html_parts = []
    for i, option in enumerate(options[:5]):
        label = option_labels[i] if i < len(option_labels) else str(i + 1)
        html_parts.append(f"<b>{label}.</b> {html.escape(str(option))}")
    return "<br>".join(html_parts)


def create_note(
    card_data: Dict[str, Any],
    image_path: Optional[Path],
    model_basic: genanki.Model,
    model_mcq: genanki.Model,
) -> Optional[genanki.Note]:
    """Create Anki note from card data."""
    card_type = card_data['card_type']
    def _style_inline_front(raw: str) -> str:
        s = html.escape(str(raw))
        s = re.sub(r"(?i)\bAnswer\b", r"<b>Answer</b>", s)
        s = s.replace("오답포인트", "<b>오답포인트</b>")
        s = re.sub(r"(?<![A-Za-z0-9])([A-E])([\\.)])", r"<b>\1\2</b>", s)
        return s

    front = _style_inline_front(card_data['front'])
    back = card_data['back']
    group_path = card_data.get('group_path', '')
    
    # Add image to back
    is_mcq = card_type in ('MCQ', 'MCQ_VIGNETTE')
    back_with_image = format_back_html(back, remove_answer_line=is_mcq)
    if image_path:
        back_with_image = back_with_image + "<br>" + make_image_html(image_path)
    
    # Generate tags
    tags = []
    if card_type in ('MCQ', 'MCQ_VIGNETTE'):
        tags.append("MCQ")
    else:
        tags.append("Basic")
    
    if group_path:
        parts = [p.strip() for p in group_path.split(">")]
        if len(parts) >= 1 and parts[0]:
            tags.append(f"Specialty:{parts[0].replace(' ', '_')}")
    
    # Create note
    if card_type in ('MCQ', 'MCQ_VIGNETTE'):
        options = card_data.get('options', [])
        correct_index = card_data.get('correct_index', 0)
        
        if not isinstance(options, list) or len(options) != 5:
            print(f"[WARN] MCQ must have 5 options: {card_data.get('card_uid', 'unknown')}")
            return None
        
        options_html = format_mcq_options(options, correct_index)
        correct_label = ["A", "B", "C", "D", "E"][correct_index] if 0 <= correct_index < 5 else "?"
        answer_opt = html.escape(str(options[correct_index])) if 0 <= correct_index < len(options) else ""
        answer_text = f"<b>Answer</b>: <b>{correct_label}.</b> {answer_opt}"
        
        note = genanki.Note(
            model=model_mcq,
            fields=[front, options_html, answer_text, back_with_image],
            tags=tags,
        )
    else:
        note = genanki.Note(
            model=model_basic,
            fields=[front, back_with_image],
            tags=tags,
        )
    
    return note


def export_integrated_deck(
    allocation_path: Path,
    s5_path: Path,
    s2_baseline_path: Path,
    s2_regen_path: Path,
    images_anki_dir: Path,
    images_regen_dir: Path,
    output_path: Path,
    threshold: float = REGEN_THRESHOLD,
    specialty_filter: Optional[str] = None,
    cards_csv_path: Optional[Path] = None,
    card_regen_keys_path: Optional[Path] = None,
) -> None:
    """Export integrated Anki deck with card-level REGEN selection."""
    
    print("="*60)
    print("FINAL Anki Export - Integrated REGEN")
    print("="*60)
    
    # Load allocation
    print(f"\n[1/7] Loading allocation: {allocation_path}")
    with allocation_path.open('r', encoding='utf-8') as f:
        allocation = json.load(f)
    
    selected_cards_all = allocation.get('selected_cards', [])
    
    # Filter by specialty if specified
    if specialty_filter:
        group_allocation = allocation.get('group_allocation', {})
        selected_cards = [
            c for c in selected_cards_all
            if group_allocation.get(c['group_id'], {}).get('specialty', '') == specialty_filter
        ]
        print(f"  Cards in allocation: {len(selected_cards_all)} total, {len(selected_cards)} in {specialty_filter}")
    else:
        selected_cards = selected_cards_all
        print(f"  Cards in allocation: {len(selected_cards)}")
    
    # Load S5 decisions - priority: card_regen_keys > Cards.csv > S5 JSONL
    if card_regen_keys_path and card_regen_keys_path.exists():
        print(f"\n[2/7] Loading decisions from diff file + S5 IMAGE_REGEN: {card_regen_keys_path}")
        s5_decisions = load_decisions_from_diff(card_regen_keys_path, s5_path, threshold)
    elif cards_csv_path and cards_csv_path.exists():
        print(f"\n[2/7] Loading S5 decisions from Cards.csv: {cards_csv_path}")
        s5_decisions = load_s5_decisions_from_csv(cards_csv_path)
        print(f"  Total decisions from CSV: {len(s5_decisions)}")
    else:
        print(f"\n[2/7] Loading S5 decisions from JSONL: {s5_path}")
        s5_decisions = load_s5_decisions(s5_path, threshold)
        print(f"  Total decisions: {len(s5_decisions)}")
    
    decision_counts = {}
    for d in s5_decisions.values():
        decision_counts[d] = decision_counts.get(d, 0) + 1
    
    for decision, count in sorted(decision_counts.items()):
        print(f"    {decision}: {count}")
    
    # Load content
    print(f"\n[3/7] Loading baseline content: {s2_baseline_path}")
    baseline_content = load_s2_content(s2_baseline_path)
    print(f"  Loaded {len(baseline_content)} baseline cards")
    
    print(f"\n[4/7] Loading REGEN content: {s2_regen_path}")
    regen_content = load_s2_content(s2_regen_path)
    print(f"  Loaded {len(regen_content)} REGEN cards")
    
    # Create deck
    print(f"\n[5/7] Creating Anki deck...")
    if specialty_filter:
        deck_id = hash(f"MeducAI_FINAL_{specialty_filter}") % (2 ** 31)
        deck_name = f"MeducAI_FINAL_{specialty_filter}"
    else:
        deck_id = 2026010701
        deck_name = "MeducAI_FINAL_Integrated"
    deck = genanki.Deck(deck_id, deck_name)
    
    model_basic = make_basic_model(2026010702)
    model_mcq = make_mcq_model(2026010703)
    
    # Track statistics
    stats = {
        'total': 0,
        'pass': 0,
        'card_regen': 0,
        'image_regen': 0,
        'with_image': 0,
        'missing_content': 0,
        'missing_image': 0,
    }
    
    media_files = set()
    
    # Process each card
    print(f"\n[6/7] Processing {len(selected_cards)} cards...")
    
    for card in selected_cards:
        group_id = card.get('group_id', '')
        entity_id = card.get('entity_id', '')
        card_role = card.get('card_role', '')
        
        # Build card_uid
        card_idx = 0 if card_role == 'Q1' else 1
        card_uid = f"{group_id}::{entity_id}__{card_role}__{card_idx}"
        
        # Get S5 decision from Cards.csv (assignment-time decision)
        decision = s5_decisions.get(card_uid, 'PASS')
        
        # Select content and image based on decision
        if decision == 'CARD_REGEN':
            # Use regen content + regen image
            card_data = regen_content.get(card_uid)
            if not card_data:
                # Fallback to baseline if regen content missing
                card_data = baseline_content.get(card_uid)
                if not card_data:
                    stats['missing_content'] += 1
                    continue
            image_dir = images_regen_dir
            suffix = "_regen"
            stats['card_regen'] += 1
        elif decision == 'IMAGE_REGEN':
            # Use baseline content + regen image
            card_data = baseline_content.get(card_uid)
            if not card_data:
                stats['missing_content'] += 1
                continue
            image_dir = images_regen_dir
            suffix = "_regen"
            stats['image_regen'] += 1
        else:  # PASS
            # Use baseline content + baseline image
            card_data = baseline_content.get(card_uid)
            if not card_data:
                stats['missing_content'] += 1
                continue
            image_dir = images_anki_dir
            suffix = ""
            stats['pass'] += 1
        
        # Find image
        image_path = find_image(image_dir, group_id, entity_id, card_role, suffix)
        
        if not image_path:
            # Try fallback to baseline
            if suffix:  # Was looking for regen
                image_path = find_image(images_anki_dir, group_id, entity_id, card_role, "")
        
        if image_path:
            media_files.add(str(image_path))
            stats['with_image'] += 1
        else:
            stats['missing_image'] += 1
        
        # Create note
        note = create_note(card_data, image_path, model_basic, model_mcq)
        if note:
            deck.add_note(note)
            stats['total'] += 1
    
    # Package deck
    print(f"\n[7/7] Packaging deck...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    pkg = genanki.Package([deck])
    if media_files:
        pkg.media_files = sorted(media_files)
        print(f"  Including {len(media_files)} media files")
    
    pkg.write_to_file(str(output_path))
    
    # Summary
    print(f"\n{'='*60}")
    print("✅ Export Complete")
    print(f"{'='*60}")
    print(f"Output: {output_path}")
    print(f"Deck: {deck.name}")
    print(f"\nStatistics:")
    print(f"  Total notes: {stats['total']}")
    print(f"  - PASS: {stats['pass']}")
    print(f"  - CARD_REGEN: {stats['card_regen']} (content + image corrected)")
    print(f"  - IMAGE_REGEN: {stats['image_regen']} (image only corrected)")
    print(f"\n  With images: {stats['with_image']}")
    print(f"  Missing images: {stats['missing_image']}")
    print(f"  Missing content: {stats['missing_content']}")
    print(f"\nFile size: {output_path.stat().st_size / (1024**3):.2f} GB")


def main():
    parser = argparse.ArgumentParser(description='Export integrated FINAL Anki deck')
    parser.add_argument('--allocation', type=Path, required=True, help='Allocation JSON (6000 cards)')
    parser.add_argument('--s5', type=Path, required=True, help='S5 validation JSONL')
    parser.add_argument('--s2_baseline', type=Path, required=True, help='S2 baseline JSONL')
    parser.add_argument('--s2_regen', type=Path, required=True, help='S2 regen JSONL')
    parser.add_argument('--images_anki', type=Path, required=True, help='Baseline images directory')
    parser.add_argument('--images_regen', type=Path, required=True, help='REGEN images directory')
    parser.add_argument('--output', type=Path, required=True, help='Output .apkg file')
    parser.add_argument('--threshold', type=float, default=REGEN_THRESHOLD, help='REGEN threshold')
    parser.add_argument('--specialty', type=str, default=None, help='Filter by specialty (e.g., abdominal_radiology)')
    parser.add_argument('--cards_csv', type=Path, default=None, help='Cards.csv with s5_decision column (preferred over S5 JSONL)')
    parser.add_argument('--card_regen_keys', type=Path, default=None, help='JSON file with actual CARD_REGEN keys from baseline vs regen diff')
    
    args = parser.parse_args()
    
    try:
        export_integrated_deck(
            allocation_path=args.allocation,
            s5_path=args.s5,
            s2_baseline_path=args.s2_baseline,
            s2_regen_path=args.s2_regen,
            images_anki_dir=args.images_anki,
            images_regen_dir=args.images_regen,
            output_path=args.output,
            threshold=args.threshold,
            specialty_filter=args.specialty,
            cards_csv_path=args.cards_csv,
            card_regen_keys_path=args.card_regen_keys,
        )
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())


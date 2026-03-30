#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate HTML QA report comparing original and translated S2 JSONL files.

Usage:
    python generate_translation_qa_report.py \
        --original 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__regen__CARD_REGEN_ONLY.jsonl \
        --translated 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__regen__CARD_REGEN_ONLY__medterm_en.jsonl \
        --output 2_Data/metadata/generated/FINAL_DISTRIBUTION/regen_translation_qa_report.html \
        --max_samples 50
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional


def load_jsonl_index(path: Path) -> Dict[str, Dict[str, Any]]:
    """Load JSONL file and index by group_id::entity_id."""
    index = {}
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                group_id = record.get('group_id', '')
                entity_id = record.get('entity_id', '')
                key = f"{group_id}::{entity_id}"
                index[key] = record
            except json.JSONDecodeError as e:
                print(f"  [WARN] JSON decode error: {e}", file=sys.stderr)
    return index


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    if not text:
        return ""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))


def highlight_korean(text: str) -> str:
    """Highlight Korean characters with a span."""
    if not text:
        return ""
    result = []
    current_korean = False
    current_text = []
    
    for char in text:
        is_korean = '\uAC00' <= char <= '\uD7A3'
        if is_korean != current_korean:
            if current_text:
                if current_korean:
                    result.append(f'<span style="background: #fff3cd; padding: 2px 4px; border-radius: 2px;">{"".join(current_text)}</span>')
                else:
                    result.append("".join(current_text))
            current_text = [char]
            current_korean = is_korean
        else:
            current_text.append(char)
    
    if current_text:
        if current_korean:
            result.append(f'<span style="background: #fff3cd; padding: 2px 4px; border-radius: 2px;">{"".join(current_text)}</span>')
        else:
            result.append("".join(current_text))
    
    return "".join(result)


def count_korean_chars(text: str) -> int:
    """Count Korean characters in text."""
    if not text:
        return 0
    return sum(1 for char in text if '\uAC00' <= char <= '\uD7A3')


def format_card_content(card: Dict[str, Any], field: str) -> str:
    """Extract and format card content."""
    content = card.get(field, '')
    if isinstance(content, list):
        content = '\n'.join(str(item) for item in content)
    return str(content) if content else ''


def generate_html_report(
    original_index: Dict[str, Dict[str, Any]],
    translated_index: Dict[str, Dict[str, Any]],
    output_path: Path,
    max_samples: Optional[int] = None,
    title: str = "번역 QA 리포트",
) -> None:
    """Generate HTML QA report."""
    
    # Find matching records
    matching_keys = sorted(set(original_index.keys()) & set(translated_index.keys()))
    
    if not matching_keys:
        print("❌ No matching records found!", file=sys.stderr)
        return
    
    # Sample records if needed
    if max_samples and len(matching_keys) > max_samples:
        matching_keys = random.sample(matching_keys, max_samples)
        print(f"📊 Sampling {max_samples} records from {len(set(original_index.keys()) & set(translated_index.keys()))} total")
    else:
        print(f"📊 Processing {len(matching_keys)} records")
    
    # Collect all cards for comparison
    records_data = []
    total_cards = 0
    cards_with_korean_remaining = 0
    
    for key in matching_keys:
        orig_record = original_index[key]
        trans_record = translated_index.get(key)
        
        if not trans_record:
            continue
        
        group_id = orig_record.get('group_id', '')
        entity_id = orig_record.get('entity_id', '')
        entity_name = orig_record.get('entity_name', '')
        
        orig_cards = orig_record.get('anki_cards', [])
        trans_cards = trans_record.get('anki_cards', [])
        
        # Match cards by index (if same order) or by card_role and card_idx_in_entity
        card_pairs = []
        
        # First try: match by index if same length and order matches
        if len(orig_cards) == len(trans_cards):
            for idx in range(len(orig_cards)):
                orig_card = orig_cards[idx]
                trans_card = trans_cards[idx]
                card_pairs.append((orig_card, trans_card))
        else:
            # Fallback: match by card_role and card_idx_in_entity
            for orig_card in orig_cards:
                card_role = orig_card.get('card_role', '')
                card_idx = orig_card.get('card_idx_in_entity')
                
                # Find matching translated card
                trans_card = None
                for tc in trans_cards:
                    tc_role = tc.get('card_role', '')
                    tc_idx = tc.get('card_idx_in_entity')
                    
                    # Match by role and index if available, otherwise just by role
                    if card_role == tc_role:
                        if card_idx is not None and tc_idx is not None:
                            if card_idx == tc_idx:
                                trans_card = tc
                                break
                        elif card_idx is None and tc_idx is None:
                            trans_card = tc
                            break
                
                if trans_card:
                    card_pairs.append((orig_card, trans_card))
        
        # Count cards and check for remaining Korean
        for orig_card, trans_card in card_pairs:
            total_cards += 1
            
            # Check if Korean remains in translated version
            front_trans = format_card_content(trans_card, 'front')
            back_trans = format_card_content(trans_card, 'back')
            has_korean = (count_korean_chars(front_trans) > 0 or 
                         count_korean_chars(back_trans) > 0)
            if has_korean:
                cards_with_korean_remaining += 1
        
        if card_pairs:
            records_data.append({
                'key': key,
                'group_id': group_id,
                'entity_id': entity_id,
                'entity_name': entity_name,
                'cards': card_pairs,
            })
    
    # Generate HTML
    html_parts = []
    html_parts.append("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>""")
    html_parts.append(escape_html(title))
    html_parts.append("""</title>
    <style>
        body { 
            font-family: 'Noto Sans KR', 'Malgun Gothic', Arial, sans-serif; 
            margin: 20px; 
            background: #f5f5f5; 
            line-height: 1.6;
        }
        h1 { 
            color: #2c3e50; 
            text-align: center; 
            margin-bottom: 10px;
        }
        .stats { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px; 
            border-radius: 8px; 
            margin: 20px 0; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .stats h2 {
            margin-top: 0;
        }
        .stat-item {
            margin: 10px 0;
            font-size: 16px;
        }
        .stat-value {
            font-weight: bold;
            font-size: 18px;
            color: #ffd700;
        }
        .record { 
            background: white; 
            margin: 20px 0; 
            padding: 0;
            border-radius: 8px; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header { 
            background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
            color: white; 
            padding: 15px 20px; 
            margin: 0;
        }
        .header h2 {
            margin: 0;
            font-size: 18px;
        }
        .header .meta {
            font-size: 13px;
            opacity: 0.9;
            margin-top: 5px;
        }
        .comparison { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 20px; 
            margin: 20px;
        }
        @media (max-width: 1200px) {
            .comparison {
                grid-template-columns: 1fr;
            }
        }
        .original, .translated { 
            padding: 15px; 
            border-radius: 5px; 
        }
        .original { 
            background: #fff3cd; 
            border-left: 4px solid #ffc107; 
        }
        .translated { 
            background: #d4edda; 
            border-left: 4px solid #28a745; 
        }
        .label { 
            font-weight: bold; 
            color: #2c3e50; 
            margin-bottom: 10px; 
            font-size: 14px; 
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .content { 
            white-space: pre-wrap; 
            line-height: 1.8; 
            font-size: 14px; 
            word-wrap: break-word;
        }
        .card-container {
            margin: 15px 0;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 5px;
            border-left: 3px solid #6c757d;
        }
        .card-role {
            font-weight: bold;
            color: #495057;
            margin-bottom: 10px;
            font-size: 13px;
        }
        .korean-remaining {
            background: #f8d7da;
            border-left: 4px solid #dc3545;
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
        }
        .korean-remaining-label {
            font-weight: bold;
            color: #721c24;
            margin-bottom: 5px;
        }
    </style>
</head>
<body>
    <h1>🎯 """)
    html_parts.append(escape_html(title))
    html_parts.append("""</h1>
    <div class="stats">
        <h2>📊 번역 통계</h2>
        <div class="stat-item">
            비교된 레코드 수: <span class="stat-value">""")
    html_parts.append(str(len(records_data)))
    html_parts.append("""</span>
        </div>
        <div class="stat-item">
            비교된 카드 수: <span class="stat-value">""")
    html_parts.append(str(total_cards))
    html_parts.append("""</span>
        </div>
        <div class="stat-item">
            번역 후 한국어 남아있는 카드: <span class="stat-value">""")
    html_parts.append(str(cards_with_korean_remaining))
    html_parts.append("""</span> (""")
    html_parts.append(f"{cards_with_korean_remaining * 100.0 / total_cards:.1f}%" if total_cards > 0 else "0%")
    html_parts.append(""")
        </div>
        <div class="stat-item">
            완전히 번역된 카드: <span class="stat-value">""")
    html_parts.append(str(total_cards - cards_with_korean_remaining))
    html_parts.append("""</span> (""")
    html_parts.append(f"{(total_cards - cards_with_korean_remaining) * 100.0 / total_cards:.1f}%" if total_cards > 0 else "0%")
    html_parts.append(""")
        </div>
    </div>
""")
    
    # Add records
    for rec_idx, record_data in enumerate(records_data, 1):
        html_parts.append("""    <div class="record">
        <div class="header">
            <h2>🎯 Record #""")
        html_parts.append(str(rec_idx))
        html_parts.append(": ")
        html_parts.append(escape_html(record_data['entity_name']))
        html_parts.append("""</h2>
            <div class="meta">""")
        html_parts.append(escape_html(f"{record_data['group_id']}::{record_data['entity_id']}"))
        html_parts.append("""</div>
        </div>
""")
        
        for card_idx, (orig_card, trans_card) in enumerate(record_data['cards'], 1):
            card_role = orig_card.get('card_role', 'UNKNOWN')
            card_type = orig_card.get('card_type', '')
            
            html_parts.append("""        <div class="card-container">
            <div class="card-role">카드 #""")
            html_parts.append(str(card_idx))
            html_parts.append(": ")
            html_parts.append(escape_html(card_role))
            if card_type:
                html_parts.append(" (")
                html_parts.append(escape_html(card_type))
                html_parts.append(")")
            html_parts.append("""</div>
""")
            
            # Front
            orig_front = format_card_content(orig_card, 'front')
            trans_front = format_card_content(trans_card, 'front')
            front_has_korean = count_korean_chars(trans_front) > 0
            
            html_parts.append("""            <div class="comparison">
                <div class="original">
                    <div class="label">📝 원본 (FRONT)</div>""")
            if front_has_korean:
                html_parts.append("""                    <div class="korean-remaining">
                        <div class="korean-remaining-label">⚠️ 번역 후 한국어 남아있음</div>
                    </div>""")
            html_parts.append("""                    <div class="content">""")
            html_parts.append(escape_html(orig_front))
            html_parts.append("""</div>
                </div>
                <div class="translated">
                    <div class="label">🎯 번역본 (FRONT)</div>""")
            if front_has_korean:
                html_parts.append("""                    <div class="korean-remaining">
                        <div class="korean-remaining-label">⚠️ 한국어 남아있음</div>
                    </div>""")
            html_parts.append("""                    <div class="content">""")
            html_parts.append(highlight_korean(trans_front))
            html_parts.append("""</div>
                </div>
            </div>
""")
            
            # Options (if present) - placed between Front and Back
            if 'options' in orig_card or 'options' in trans_card:
                orig_options_list = orig_card.get('options', [])
                trans_options_list = trans_card.get('options', [])
                
                # Format options as list or string
                if isinstance(orig_options_list, list):
                    orig_options = '\n'.join(str(opt) for opt in orig_options_list)
                else:
                    orig_options = format_card_content(orig_card, 'options')
                
                if isinstance(trans_options_list, list):
                    trans_options = '\n'.join(str(opt) for opt in trans_options_list)
                else:
                    trans_options = format_card_content(trans_card, 'options')
                
                options_has_korean = count_korean_chars(trans_options) > 0
                
                html_parts.append("""            <div class="comparison">
                <div class="original">
                    <div class="label">📝 원본 (OPTIONS)</div>""")
                if options_has_korean:
                    html_parts.append("""                    <div class="korean-remaining">
                        <div class="korean-remaining-label">⚠️ 번역 후 한국어 남아있음</div>
                    </div>""")
                html_parts.append("""                    <div class="content">""")
                html_parts.append(escape_html(orig_options))
                html_parts.append("""</div>
                </div>
                <div class="translated">
                    <div class="label">🎯 번역본 (OPTIONS)</div>""")
                if options_has_korean:
                    html_parts.append("""                    <div class="korean-remaining">
                        <div class="korean-remaining-label">⚠️ 한국어 남아있음</div>
                    </div>""")
                html_parts.append("""                    <div class="content">""")
                html_parts.append(highlight_korean(trans_options))
                html_parts.append("""</div>
                </div>
            </div>
""")
            
            # Back
            orig_back = format_card_content(orig_card, 'back')
            trans_back = format_card_content(trans_card, 'back')
            back_has_korean = count_korean_chars(trans_back) > 0
            
            html_parts.append("""            <div class="comparison">
                <div class="original">
                    <div class="label">📝 원본 (BACK)</div>""")
            if back_has_korean:
                html_parts.append("""                    <div class="korean-remaining">
                        <div class="korean-remaining-label">⚠️ 번역 후 한국어 남아있음</div>
                    </div>""")
            html_parts.append("""                    <div class="content">""")
            html_parts.append(escape_html(orig_back))
            html_parts.append("""</div>
                </div>
                <div class="translated">
                    <div class="label">🎯 번역본 (BACK)</div>""")
            if back_has_korean:
                html_parts.append("""                    <div class="korean-remaining">
                        <div class="korean-remaining-label">⚠️ 한국어 남아있음</div>
                    </div>""")
            html_parts.append("""                    <div class="content">""")
            html_parts.append(highlight_korean(trans_back))
            html_parts.append("""</div>
                </div>
            </div>
""")
            
            html_parts.append("""        </div>
""")
        
        html_parts.append("""    </div>
""")
    
    html_parts.append("""</body>
</html>""")
    
    # Write HTML file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8') as f:
        f.write("".join(html_parts))
    
    print(f"✅ HTML 리포트 생성 완료: {output_path}")
    print(f"   레코드: {len(records_data)}개, 카드: {total_cards}개")


def main():
    parser = argparse.ArgumentParser(
        description='Generate HTML QA report comparing original and translated S2 JSONL files'
    )
    parser.add_argument(
        '--original',
        type=Path,
        required=True,
        help='Original S2 JSONL file path'
    )
    parser.add_argument(
        '--translated',
        type=Path,
        required=True,
        help='Translated S2 JSONL file path'
    )
    parser.add_argument(
        '--output',
        type=Path,
        required=True,
        help='Output HTML report path'
    )
    parser.add_argument(
        '--max_samples',
        type=int,
        default=None,
        help='Maximum number of records to sample (default: all)'
    )
    parser.add_argument(
        '--title',
        type=str,
        default='번역 QA 리포트',
        help='Report title (default: 번역 QA 리포트)'
    )
    
    args = parser.parse_args()
    
    if not args.original.exists():
        print(f"❌ Error: Original file not found: {args.original}", file=sys.stderr)
        return 1
    
    if not args.translated.exists():
        print(f"❌ Error: Translated file not found: {args.translated}", file=sys.stderr)
        return 1
    
    print(f"Loading original: {args.original}")
    original_index = load_jsonl_index(args.original)
    print(f"  Loaded {len(original_index)} records")
    
    print(f"Loading translated: {args.translated}")
    translated_index = load_jsonl_index(args.translated)
    print(f"  Loaded {len(translated_index)} records")
    
    generate_html_report(
        original_index=original_index,
        translated_index=translated_index,
        output_path=args.output,
        max_samples=args.max_samples,
        title=args.title,
    )
    
    return 0


if __name__ == '__main__':
    sys.exit(main())


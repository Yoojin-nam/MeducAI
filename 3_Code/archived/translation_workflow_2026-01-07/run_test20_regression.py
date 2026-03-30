#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST20 regression check: comparison HTML + basic quality metrics.

This script is intentionally lightweight (stdlib-only) so it can be run anywhere.

Common usage patterns:

1) 3-way comparison (recommended): original vs baseline vs candidate
   - original: untranslated S2 JSONL (Korean / mixed)
   - baseline: known-good translated output (e.g., TEST20_v2)
   - candidate: newly generated translated output to validate

2) 2-way comparison: original vs candidate
   - useful when you only care about the new output quality

3) 2-way comparison: baseline vs candidate
   - useful when original isn't available (metrics that require original will be skipped)
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _contains_korean(text: str) -> bool:
    return any("\uAC00" <= ch <= "\uD7A3" for ch in (text or ""))


def _escape(text: str) -> str:
    return html.escape(text or "", quote=False)


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _norm_token(text: str) -> str:
    t = _collapse_ws(text)
    t = t.strip(" \t\r\n-–—·•*:,;.")
    return t.casefold()


def load_jsonl_index(path: Path) -> Dict[str, Dict[str, Any]]:
    """Load JSONL file and index by group_id::entity_id."""
    index: Dict[str, Dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"JSON decode error in {path} at line {line_no}: {e}") from e

            key = f"{rec.get('group_id', '')}::{rec.get('entity_id', '')}"
            index[key] = rec
    return index


def _card_key(card: Dict[str, Any], fallback_idx: int) -> Tuple[str, int, str]:
    """
    Key used for aligning cards across files.

    We prioritize (card_role, card_idx_in_entity) when available.
    """
    role = str(card.get("card_role") or "")
    idx_in = card.get("card_idx_in_entity")
    try:
        idx_in_int = int(idx_in) if idx_in is not None else fallback_idx
    except Exception:
        idx_in_int = fallback_idx
    ctype = str(card.get("card_type") or "")
    return (role, idx_in_int, ctype)


def align_cards(cards_by_label: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Optional[Dict[str, Any]]]]:
    """
    Align cards across labels by a stable per-card key.
    Returns a list of rows, each row mapping label -> card (or None).
    """
    # Build per-label maps
    label_maps: Dict[str, Dict[Tuple[str, int, str], Dict[str, Any]]] = {}
    all_keys: set[Tuple[str, int, str]] = set()
    for label, cards in cards_by_label.items():
        m: Dict[Tuple[str, int, str], Dict[str, Any]] = {}
        for idx, c in enumerate(cards or []):
            k = _card_key(c, idx)
            # If duplicate key, fall back to index-based disambiguation
            if k in m:
                k = (k[0], k[1], f"{k[2]}#{idx}")
            m[k] = c
            all_keys.add(k)
        label_maps[label] = m

    # Sort keys: role, idx, type-ish
    def sort_key(k: Tuple[str, int, str]) -> Tuple[str, int, str]:
        return (k[0], k[1], k[2])

    rows: List[Dict[str, Optional[Dict[str, Any]]]] = []
    for k in sorted(all_keys, key=sort_key):
        row: Dict[str, Optional[Dict[str, Any]]] = {}
        for label in cards_by_label.keys():
            row[label] = label_maps.get(label, {}).get(k)
        rows.append(row)
    return rows


def _field_values(card: Optional[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Returns a dict of logical fields -> list of strings.
    - front/back are single-item lists
    - options becomes one item per option (so metrics can count per-option)
    """
    if not card:
        return {"front": [""], "back": [""], "options": []}
    front = str(card.get("front") or "")
    back = str(card.get("back") or "")
    options_raw = card.get("options")
    options: List[str] = []
    if isinstance(options_raw, list):
        options = [str(x) for x in options_raw]
    elif options_raw is not None:
        options = [str(options_raw)]
    return {"front": [front], "back": [back], "options": options}


def _join_options(options: List[str]) -> str:
    if not options:
        return ""
    return "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(options))


_RE_MIXED_KO_EN = re.compile(r"[가-힣]+\s*\(\s*[A-Za-z][^)]*\)")
_RE_MIXED_EN_KO = re.compile(r"[A-Za-z][A-Za-z0-9 .:/_-]{0,80}\(\s*[가-힣][^)]*\)")
_RE_PAREN = re.compile(r"([^\(\)]{1,80}?)\s*\(\s*([^\(\)]{1,80}?)\s*\)")
_RE_THINKING = re.compile(
    r"(?is)"
    r"(<\s*think\s*>|</\s*think\s*>|\bchain\s*of\s*thought\b|\breasoning\b|\banalysis\b|"
    r"\blet's\s*think\b|\bthoughts?\b|\bthinking\b)"
)


@dataclass
class MetricCounts:
    total_fields_with_korean: int = 0
    unchanged_fields_with_korean: int = 0
    duplicate_parentheses: int = 0
    mixed_format_markers: int = 0
    thinking_markers: int = 0

    def to_dict(self) -> Dict[str, Any]:
        pct = (
            (100.0 * self.unchanged_fields_with_korean / self.total_fields_with_korean)
            if self.total_fields_with_korean
            else None
        )
        return {
            "total_fields_with_korean": self.total_fields_with_korean,
            "unchanged_fields_with_korean": self.unchanged_fields_with_korean,
            "pct_unchanged_when_korean_present": pct,
            "duplicate_parentheses": self.duplicate_parentheses,
            "mixed_format_markers": self.mixed_format_markers,
            "thinking_markers": self.thinking_markers,
        }


def _count_duplicate_parentheses(text: str) -> int:
    """
    Count patterns like `X (X)` in a tolerant way (case/whitespace insensitive).
    """
    if not text:
        return 0
    n = 0
    for a, b in _RE_PAREN.findall(text):
        na = _norm_token(a)
        nb = _norm_token(b)
        if not nb:
            continue

        # Exact duplicate: "X (X)"
        if na == nb:
            n += 1
            continue

        # Common in this dataset: "Answer: X (X)" (prefixes before the duplicated phrase)
        # Count it as a duplicate if the left side ends with the parenthetical content.
        if na.endswith(nb) or na.endswith(" " + nb):
            n += 1
    return n


def _count_mixed_format(text: str) -> int:
    if not text:
        return 0
    return len(_RE_MIXED_KO_EN.findall(text)) + len(_RE_MIXED_EN_KO.findall(text))


def _count_thinking(text: str) -> int:
    if not text:
        return 0
    return len(_RE_THINKING.findall(text))


def compute_metrics(
    *,
    original_index: Optional[Dict[str, Dict[str, Any]]],
    candidate_index: Dict[str, Dict[str, Any]],
) -> MetricCounts:
    """
    Compute metrics on the candidate output. If original is provided, also compute
    the 'unchanged despite Korean present' metric by comparing original->candidate.
    """
    counts = MetricCounts()
    keys = sorted(candidate_index.keys())
    for key in keys:
        cand_rec = candidate_index.get(key)
        orig_rec = original_index.get(key) if original_index else None

        cand_cards = (cand_rec or {}).get("anki_cards") or []
        orig_cards = (orig_rec or {}).get("anki_cards") or []

        aligned = align_cards({"orig": orig_cards, "cand": cand_cards})
        for row in aligned:
            orig_card = row.get("orig")
            cand_card = row.get("cand")

            cand_fields = _field_values(cand_card)
            orig_fields = _field_values(orig_card) if original_index else None

            # candidate-only quality metrics
            for s in cand_fields["front"] + cand_fields["back"] + cand_fields["options"]:
                counts.duplicate_parentheses += _count_duplicate_parentheses(s)
                counts.mixed_format_markers += _count_mixed_format(s)
                counts.thinking_markers += _count_thinking(s)

            # unchanged despite Korean present (only meaningful with original)
            if original_index and orig_fields is not None:
                for field_name in ("front", "back"):
                    o = orig_fields[field_name][0]
                    c = cand_fields[field_name][0]
                    if _contains_korean(o):
                        counts.total_fields_with_korean += 1
                        if o == c:
                            counts.unchanged_fields_with_korean += 1

                # options: compare per-index
                o_opts = orig_fields["options"]
                c_opts = cand_fields["options"]
                for i, o in enumerate(o_opts):
                    if _contains_korean(o):
                        counts.total_fields_with_korean += 1
                        if i < len(c_opts) and o == c_opts[i]:
                            counts.unchanged_fields_with_korean += 1
    return counts


def _diff_counts(
    left_index: Dict[str, Dict[str, Any]],
    right_index: Dict[str, Dict[str, Any]],
) -> Dict[str, int]:
    """
    Count how many fields differ between two translated outputs.
    (Pure regression signal; doesn't require original.)
    """
    changed_fields = 0
    total_fields = 0

    keys = sorted(set(left_index.keys()) & set(right_index.keys()))
    for key in keys:
        l_cards = (left_index[key].get("anki_cards") or [])
        r_cards = (right_index[key].get("anki_cards") or [])
        aligned = align_cards({"l": l_cards, "r": r_cards})
        for row in aligned:
            l = row.get("l")
            r = row.get("r")
            l_fields = _field_values(l)
            r_fields = _field_values(r)

            for field_name in ("front", "back"):
                total_fields += 1
                if l_fields[field_name][0] != r_fields[field_name][0]:
                    changed_fields += 1

            l_opts = l_fields["options"]
            r_opts = r_fields["options"]
            for i in range(max(len(l_opts), len(r_opts))):
                total_fields += 1
                lv = l_opts[i] if i < len(l_opts) else ""
                rv = r_opts[i] if i < len(r_opts) else ""
                if lv != rv:
                    changed_fields += 1

    return {"total_fields_compared": total_fields, "changed_fields": changed_fields}


def generate_comparison_html(
    *,
    original_index: Optional[Dict[str, Dict[str, Any]]],
    baseline_index: Optional[Dict[str, Dict[str, Any]]],
    candidate_index: Dict[str, Dict[str, Any]],
    output_html: Path,
    title: str,
    label_original: str,
    label_baseline: str,
    label_candidate: str,
) -> None:
    # Determine which columns exist
    cols: List[Tuple[str, str]] = []
    if original_index is not None:
        cols.append(("original", label_original))
    if baseline_index is not None:
        cols.append(("baseline", label_baseline))
    cols.append(("candidate", label_candidate))

    # CSS class mapping for consistent color-coding
    class_for = {"original": "original", "baseline": "good", "candidate": "test"}

    keys = sorted(candidate_index.keys())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Basic summary stats
    total_records = len(keys)
    total_cards = 0
    for k in keys:
        total_cards += len((candidate_index[k].get("anki_cards") or []))

    grid_cols_css = " ".join(["1fr"] * len(cols))

    parts: List[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="ko"><head><meta charset="UTF-8">')
    parts.append(f"<title>{_escape(title)}</title>")
    parts.append(
        "<style>"
        "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
        "max-width:1700px;margin:0 auto;padding:20px;background:#f5f5f5}"
        ".header{background:white;padding:30px;border-radius:10px;margin-bottom:30px;"
        "box-shadow:0 2px 4px rgba(0,0,0,0.1)}"
        "h1{margin:0 0 10px 0;color:#333}"
        "h3{margin:15px 0 10px 0;color:#555}"
        ".summary{background:#fff3e0;padding:15px;border-radius:5px;margin-top:20px}"
        ".card{background:white;margin-bottom:30px;border-radius:10px;"
        "box-shadow:0 2px 4px rgba(0,0,0,0.1)}"
        ".card-header{background:#00897b;color:white;padding:15px 20px;font-weight:bold}"
        ".card-body{padding:20px}"
        f".grid{{display:grid;grid-template-columns:{grid_cols_css};gap:15px;margin-bottom:20px}}"
        ".column{border:2px solid #ddd;border-radius:5px;padding:12px}"
        ".original{background:#f3e5f5;border-color:#9c27b0}"
        ".good{background:#e3f2fd;border-color:#2196f3}"
        ".test{background:#e8f5e9;border-color:#4caf50}"
        ".label{font-weight:bold;margin-bottom:8px;padding:4px 8px;border-radius:3px;"
        "display:inline-block;font-size:13px}"
        ".original .label{background:#9c27b0;color:white}"
        ".good .label{background:#2196f3;color:white}"
        ".test .label{background:#4caf50;color:white}"
        ".content{white-space:pre-wrap;font-family:'Courier New',monospace;font-size:12px;"
        "line-height:1.5;background:white;padding:10px;border-radius:3px;max-height:320px;"
        "overflow-y:auto}"
        "</style></head><body>"
    )

    parts.append('<div class="header">')
    parts.append(f"<h1>{_escape(title)}</h1>")
    parts.append(f"<p><strong>generated:</strong> {_escape(now)}</p>")
    parts.append('<div class="summary">')
    parts.append("<strong>📋 비교 대상:</strong><br>")
    for key, label in cols:
        parts.append(f"• { _escape(label) }<br>")
    parts.append("<br>")
    parts.append(f"<strong>records:</strong> {total_records} &nbsp; | &nbsp; <strong>cards:</strong> {total_cards}")
    parts.append("</div></div>")

    card_counter = 0
    for rec_no, rid in enumerate(keys, 1):
        cand_rec = candidate_index[rid]
        entity_name = str(cand_rec.get("entity_name") or "")

        cards_by_label: Dict[str, List[Dict[str, Any]]] = {"candidate": cand_rec.get("anki_cards") or []}
        if baseline_index is not None:
            cards_by_label["baseline"] = (baseline_index.get(rid, {}) or {}).get("anki_cards") or []
        if original_index is not None:
            cards_by_label["original"] = (original_index.get(rid, {}) or {}).get("anki_cards") or []

        aligned_rows = align_cards(cards_by_label)
        for row in aligned_rows:
            card_counter += 1
            cand_card = row.get("candidate") or {}
            card_type = str(cand_card.get("card_type") or "")
            card_role = str(cand_card.get("card_role") or "")
            header = f"#{card_counter} | {rid} | {entity_name} | {card_role} | {card_type}"

            parts.append('<div class="card">')
            parts.append(f'<div class="card-header">{_escape(header)}</div>')
            parts.append('<div class="card-body">')

            # FRONT
            parts.append("<h3>FRONT</h3>")
            parts.append('<div class="grid">')
            for col_key, col_label in cols:
                card = row.get(col_key)
                fv = _field_values(card)
                text = fv["front"][0]
                klass = class_for[col_key]
                parts.append(f'<div class="column {klass}"><div class="label">{_escape(col_label)}</div>')
                parts.append(f'<div class="content">{_escape(text)}</div></div>')
            parts.append("</div>")

            # BACK
            parts.append("<h3>BACK</h3>")
            parts.append('<div class="grid">')
            for col_key, col_label in cols:
                card = row.get(col_key)
                fv = _field_values(card)
                text = fv["back"][0]
                klass = class_for[col_key]
                parts.append(f'<div class="column {klass}"><div class="label">{_escape(col_label)}</div>')
                parts.append(f'<div class="content">{_escape(text)}</div></div>')
            parts.append("</div>")

            # OPTIONS (if any in any column)
            any_opts = False
            for col_key, _ in cols:
                if _field_values(row.get(col_key)).get("options"):
                    any_opts = True
                    break
            if any_opts:
                parts.append("<h3>OPTIONS</h3>")
                parts.append('<div class="grid">')
                for col_key, col_label in cols:
                    card = row.get(col_key)
                    fv = _field_values(card)
                    text = _join_options(fv["options"])
                    klass = class_for[col_key]
                    parts.append(f'<div class="column {klass}"><div class="label">{_escape(col_label)}</div>')
                    parts.append(f'<div class="content">{_escape(text)}</div></div>')
                parts.append("</div>")

            parts.append("</div></div>")  # card-body, card

    parts.append("</body></html>")
    output_html.write_text("\n".join(parts), encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Generate TEST20 regression HTML + metrics.")
    p.add_argument("--candidate", type=Path, required=True, help="Candidate translated JSONL (new output)")
    p.add_argument("--baseline", type=Path, default=None, help="Baseline translated JSONL (known-good)")
    p.add_argument("--original", type=Path, default=None, help="Original untranslated JSONL (optional but recommended)")
    p.add_argument("--output_html", type=Path, default=None, help="Output HTML path (default: sibling of candidate)")
    p.add_argument("--output_metrics", type=Path, default=None, help="Output metrics JSON path (default: sibling of candidate)")
    p.add_argument("--title", type=str, default="🧪 TEST20 regression comparison", help="HTML title")
    p.add_argument("--label_original", type=str, default="📝 Original", help="Column label for original")
    p.add_argument("--label_baseline", type=str, default="✅ Baseline", help="Column label for baseline")
    p.add_argument("--label_candidate", type=str, default="🆕 Candidate", help="Column label for candidate")
    args = p.parse_args()

    candidate_path: Path = args.candidate
    baseline_path: Optional[Path] = args.baseline
    original_path: Optional[Path] = args.original

    if not candidate_path.exists():
        print(f"❌ candidate not found: {candidate_path}", file=sys.stderr)
        return 2
    if baseline_path is not None and not baseline_path.exists():
        print(f"❌ baseline not found: {baseline_path}", file=sys.stderr)
        return 2
    if original_path is not None and not original_path.exists():
        print(f"❌ original not found: {original_path}", file=sys.stderr)
        return 2

    out_html = args.output_html or candidate_path.parent / "TEST20_regression_comparison.html"
    out_metrics = args.output_metrics or candidate_path.parent / "TEST20_regression_metrics.json"

    candidate_index = load_jsonl_index(candidate_path)
    baseline_index = load_jsonl_index(baseline_path) if baseline_path else None
    original_index = load_jsonl_index(original_path) if original_path else None

    # Metrics
    cand_metrics = compute_metrics(original_index=original_index, candidate_index=candidate_index)
    baseline_metrics = (
        compute_metrics(original_index=original_index, candidate_index=baseline_index)
        if (baseline_index is not None)
        else None
    )
    baseline_vs_candidate = _diff_counts(baseline_index, candidate_index) if baseline_index is not None else None

    metrics_payload: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "paths": {
            "original": str(original_path) if original_path else None,
            "baseline": str(baseline_path) if baseline_path else None,
            "candidate": str(candidate_path),
            "output_html": str(out_html),
            "output_metrics": str(out_metrics),
        },
        "candidate": cand_metrics.to_dict(),
        "baseline": baseline_metrics.to_dict() if baseline_metrics else None,
        "baseline_vs_candidate": baseline_vs_candidate,
    }

    # HTML
    generate_comparison_html(
        original_index=original_index,
        baseline_index=baseline_index,
        candidate_index=candidate_index,
        output_html=out_html,
        title=args.title,
        label_original=args.label_original,
        label_baseline=args.label_baseline,
        label_candidate=args.label_candidate,
    )

    out_metrics.write_text(json.dumps(metrics_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Console summary (kept short)
    print(f"✅ HTML: {out_html}")
    print(f"✅ Metrics: {out_metrics}")
    print(f"candidate: {cand_metrics.to_dict()}")
    if baseline_metrics:
        print(f"baseline: {baseline_metrics.to_dict()}")
    if baseline_vs_candidate:
        print(f"baseline_vs_candidate: {baseline_vs_candidate}")
    if original_index is None:
        print("ℹ️ Note: original not provided -> 'unchanged when Korean present' will be null.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())



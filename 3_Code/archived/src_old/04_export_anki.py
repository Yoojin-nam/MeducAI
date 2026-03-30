#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
04_export_anki.py (MeducAI v3.x)
--------------------------------
- Export Anki .apkg with:
  * per-card-type models (Basic / MCQ / ImageDx / Cloze)
  * subdeck splitting
  * optional entity image attachment
  * robust markdown (**bold**, *italic*) rendering
  * LaTeX -> plain-text math normalization (Option 1)
  * optional LaTeX pattern report mining
  * mobile-friendly image sizing:
      - default 45vh
      - ImageDx override 55vh
  * deck description with recommended Anki settings
  * deterministic note GUID
"""

from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import genanki


# ============================================================
# Regex / Constants
# ============================================================
CLOZE_RE = re.compile(r"\{\{c\d+::", re.IGNORECASE)

# MCQ options like: A) text / (A) text / A. text / A: text / A- text
MCQ_OPT_RE = re.compile(r"^\s*\(?([A-Ea-e])\)?\s*[\)\.\:\-]\s+(.*)\s*$")
MCQ_ANSWER_RE = re.compile(r"(?:^|\b)(?:answer|정답)\s*[:\-]?\s*([A-Ea-e])\b", re.IGNORECASE)

# Markdown
_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")

# LaTeX mining
_LATEX_CMD_RE = re.compile(r"\\[A-Za-z]+")
_INLINE_MATH_RE = re.compile(r"\$(.+?)\$", re.DOTALL)

ALLOWED_INLINE_TAGS = {"b", "strong", "i", "em", "u", "br", "hr"}


# ============================================================
# IO Helpers
# ============================================================
def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    df = pd.read_csv(
        path,
        keep_default_na=False,
        na_filter=False,
    )
    df.columns = df.columns.str.strip()
    return df


def safe_str(x: Any) -> str:
    if x is None:
        return ""
    try:
        # pandas NaN 방어
        if isinstance(x, float) and pd.isna(x):
            return ""
    except Exception:
        pass

    s = str(x).strip()
    if s.lower() in {"nan", "null", "none"}:
        return ""
    return s



def split_tags(tag_string: str) -> List[str]:
    s = safe_str(tag_string)
    if not s:
        return []
    return [t for t in re.split(r"\s+", s) if t]


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


# ============================================================
# Image Index
# ============================================================
@dataclass
class ImageIndexEntry:
    ts: int
    output_path: str
    entity_name: str
    record_id: str


def build_entity_image_index(manifest_path: Path) -> Dict[Tuple[str, str], ImageIndexEntry]:
    """
    Map (record_id, entity_name_lower) -> latest successful image entry.
    """
    idx: Dict[Tuple[str, str], ImageIndexEntry] = {}
    rows = read_jsonl(manifest_path)

    for r in rows:
        if safe_str(r.get("status")).lower() != "ok":
            continue
        # optional filter: input_kind must be "entity" if present
        if safe_str(r.get("input_kind")) and safe_str(r.get("input_kind")) != "entity":
            continue

        record_id = safe_str(r.get("record_id"))
        entity_name = safe_str(r.get("entity_name"))
        output_path = safe_str(r.get("output_path"))
        ts = int(r.get("ts") or 0)

        if not record_id or not entity_name or not output_path:
            continue

        key = (record_id, entity_name.lower())
        cur = idx.get(key)
        if (cur is None) or (ts >= cur.ts):
            idx[key] = ImageIndexEntry(ts=ts, output_path=output_path, entity_name=entity_name, record_id=record_id)

    return idx


def attach_image_html(
    record_id: str,
    entity_name: str,
    image_index: Dict[Tuple[str, str], ImageIndexEntry],
    media_files: List[str],
) -> str:
    """
    Return HTML that references media by basename.
    Uses CSS classes (meducai-imgwrap / meducai-img) for sizing control.
    """
    key = (safe_str(record_id), safe_str(entity_name).lower())
    ent = image_index.get(key)
    if not ent:
        return ""

    p = Path(ent.output_path)
    if not p.exists():
        return ""

    if str(p) not in media_files:
        media_files.append(str(p))

    media_name = p.name
    return (
        '<div class="meducai-imgwrap">'
        f'<img src="{html.escape(media_name)}" class="meducai-img">'
        "</div>"
    )


# ============================================================
# Stable IDs / GUID
# ============================================================
def stable_id_from_text(text: str) -> int:
    import hashlib
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def make_note_guid(record_id: str, entity_name: str, card_type: str, front: str) -> str:
    key = f"{safe_str(record_id)}|{safe_str(entity_name)}|{safe_str(card_type)}|{safe_str(front)}"
    return str(stable_id_from_text(key))


# ============================================================
# LaTeX -> Plain text (Option 1)
# ============================================================
_SUB_DIGITS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
_SUP_DIGITS = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")


def normalize_md_symbols(s: str) -> str:
    # normalize odd asterisks
    s = s.replace("＊", "*").replace("∗", "*").replace("⋆", "*")
    # escaped literal star
    s = s.replace("\\*", "*")
    # remove zero-width chars
    s = s.replace("\u200b", "").replace("\ufeff", "")
    return s


def _latex_frac_to_slash(s: str) -> str:
    # \frac{a}{b} -> (a/b)  (repeat to handle some nesting)
    frac_re = re.compile(r"\\frac\{([^{}]+)\}\{([^{}]+)\}")
    prev = None
    cur = s
    while prev != cur:
        prev = cur
        cur = frac_re.sub(r"(\1/\2)", cur)
    return cur


def _latex_sub_sup(s: str) -> str:
    # Subscript
    s = re.sub(r"_\{([0-9]+)\}", lambda m: m.group(1).translate(_SUB_DIGITS), s)
    s = re.sub(r"_([0-9]+)", lambda m: m.group(1).translate(_SUB_DIGITS), s)

    # Superscript
    s = re.sub(r"\^\{([0-9+\-=\(\)n]+)\}", lambda m: m.group(1).translate(_SUP_DIGITS), s)
    s = re.sub(r"\^([0-9])", lambda m: m.group(1).translate(_SUP_DIGITS), s)
    return s


def _latex_symbols(s: str) -> str:
    replacements = [
        # arrows
        (r"\\rightarrow", "→"),
        (r"\\leftarrow", "←"),
        (r"\\to\b", "→"),

        # relations
        (r"\\geq\b", "≥"),
        (r"\\leq\b", "≤"),
        (r"\\neq\b", "≠"),
        (r"\\approx\b", "≈"),
        (r"\\propto\b", "∝"),

        # operators
        (r"\\times\b", "×"),
        (r"\\cdot\b", "·"),
        (r"\\pm\b", "±"),
        (r"\\div\b", "÷"),

        # misc
        (r"\\infty\b", "∞"),
        (r"\\degree\b", "°"),

        # greek (pragmatic)
        (r"\\mu\b", "μ"),
        (r"\\alpha\b", "α"),
        (r"\\beta\b", "β"),
        (r"\\gamma\b", "γ"),
        (r"\\Delta\b", "Δ"),
        (r"\\delta\b", "δ"),
        (r"\\lambda\b", "λ"),
        (r"\\pi\b", "π"),
        (r"\\sigma\b", "σ"),
        (r"\\omega\b", "ω"),
    ]

    out = s
    for pat, rep in replacements:
        out = re.sub(pat, rep, out)
    return out


def latex_to_plain_math(expr: str) -> str:
    s = safe_str(expr)

    # remove spacing commands
    s = re.sub(r"\\,", "", s)
    s = re.sub(r"\\;", "", s)
    s = re.sub(r"\\!", "", s)
    s = re.sub(r"\\\s+", " ", s)

    s = _latex_frac_to_slash(s)
    s = _latex_symbols(s)
    s = _latex_sub_sup(s)

    # remove \left \right
    s = re.sub(r"\\left\b", "", s)
    s = re.sub(r"\\right\b", "", s)

    s = re.sub(r"\s{2,}", " ", s).strip()
    return s


def normalize_latex_tokens(text: str) -> str:
    """
    Option 1: convert $...$ to plain-text math.
    Also normalize stray latex tokens outside $...$.
    """
    s = safe_str(text)

    # inline math: $...$ -> plain
    def _repl(m: re.Match) -> str:
        return latex_to_plain_math(m.group(1))

    s = _INLINE_MATH_RE.sub(_repl, s)
    s = _latex_symbols(s)
    return s


# ============================================================
# Markdown -> HTML (safe)
# ============================================================
def md_to_html_basic(text: str) -> str:
    s = safe_str(text)
    s = normalize_latex_tokens(s)
    s = normalize_md_symbols(s)
    s = _MD_BOLD_RE.sub(r"<b>\1</b>", s)
    s = _MD_ITALIC_RE.sub(r"<i>\1</i>", s)
    return s


def sanitize_allow_basic_html(text: str) -> str:
    """
    Convert markdown to basic HTML, then escape everything except a tiny whitelist of bare tags.
    (Images are not allowed in text fields; images are injected only via attach_image_html().)
    """
    s = md_to_html_basic(text)

    # protect bare tags
    for tag in ALLOWED_INLINE_TAGS:
        s = re.sub(fr"<{tag}>", f"__TAG_OPEN_{tag}__", s, flags=re.IGNORECASE)
        s = re.sub(fr"</{tag}>", f"__TAG_CLOSE_{tag}__", s, flags=re.IGNORECASE)

    escaped = html.escape(s)

    for tag in ALLOWED_INLINE_TAGS:
        escaped = escaped.replace(f"__TAG_OPEN_{tag}__", f"<{tag}>")
        escaped = escaped.replace(f"__TAG_CLOSE_{tag}__", f"</{tag}>")

    return escaped.replace("\n", "<br>")


def anki_html(text: str, wrap_div: bool = True) -> str:
    body = sanitize_allow_basic_html(text)
    return f"<div>{body}</div>" if wrap_div else body


# ============================================================
# Card Rendering (MCQ / Basic)
# ============================================================
def extract_answer_letter(text: str) -> str:
    s = safe_str(text)
    m = MCQ_ANSWER_RE.search(s)
    if not m:
        return ""
    return m.group(1).upper()


def parse_mcq(front_text: str) -> Tuple[str, List[Tuple[str, str]]]:
    lines = [ln.rstrip() for ln in safe_str(front_text).splitlines() if ln.strip()]
    opts: List[Tuple[str, str]] = []
    stem_lines: List[str] = []

    found_opts = False
    for ln in lines:
        m = MCQ_OPT_RE.match(ln)
        if m:
            found_opts = True
            opts.append((m.group(1).upper(), m.group(2).strip()))
        else:
            if not found_opts:
                stem_lines.append(ln)
            else:
                if opts:
                    prev_l, prev_t = opts[-1]
                    opts[-1] = (prev_l, (prev_t + " " + ln).strip())
                else:
                    stem_lines.append(ln)

    stem_raw = "\n".join(stem_lines).strip()
    stem_html = anki_html(stem_raw, wrap_div=True) if stem_raw else "<div></div>"
    return stem_html, opts


def render_mcq_front(front_text: str) -> str:
    stem_html, opts = parse_mcq(front_text)
    if not opts:
        return anki_html(front_text, wrap_div=True)

    opt_rows = []
    for letter, txt in opts:
        opt_rows.append(
            f"""
            <label style="display:block; margin:6px 0; line-height:1.35;">
              <input type="radio" disabled style="margin-right:8px;">
              <b>{html.escape(letter)}.</b> {sanitize_allow_basic_html(txt)}
            </label>
            """.strip()
        )
    options_html = "<div style='margin-top:10px;'>" + "\n".join(opt_rows) + "</div>"
    return stem_html + options_html


def render_mcq_back(back_text: str) -> str:
    b = safe_str(back_text)
    ans = extract_answer_letter(b)
    body = anki_html(b, wrap_div=True)
    if ans:
        return f"<div><b>Answer:</b> {html.escape(ans)}</div><hr>" + body
    return body


def render_basic_html(text: str) -> str:
    return anki_html(text, wrap_div=True)


# ============================================================
# CSS (mobile-friendly)
# ============================================================
BASE_CSS = """
.card { font-family: Arial; font-size: 18px; text-align: left; color: black; background-color: white; }

/* Reduce unexpected whitespace */
div { margin: 0; padding: 0; }
img { display: block; margin: 0 auto; }

.meducai-imgwrap { margin: 0; padding: 0; text-align: center; }

/* Default image: mobile friendly */
.meducai-img {
  max-width: 100%;
  max-height: 45vh;
  width: auto;
  height: auto;
  object-fit: contain;
}
"""

CLOZE_CSS_EXTRA = """
.cloze {
  font-weight: 700;
  color: #1e5eff;
}
"""

IMAGEDX_CSS_OVERRIDE = """
/* ImageDx: allow larger image for diagnosis */
.meducai-img {
  max-height: 55vh;
}
"""


# ============================================================
# Anki Models
# ============================================================
def make_basic_model(model_id: int) -> genanki.Model:
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
    return genanki.Model(
        model_id,
        "MeducAI MCQ",
        fields=[{"name": "StemOptions"}, {"name": "Explanation"}],
        templates=[{
            "name": "MCQ",
            "qfmt": "{{StemOptions}}",
            "afmt": "{{StemOptions}}<hr id='answer'>{{Explanation}}",
        }],
        css=BASE_CSS + "\nlabel { cursor: default; }\n",
    )


def make_image_dx_model(model_id: int) -> genanki.Model:
    return genanki.Model(
        model_id,
        "MeducAI Image Diagnosis",
        fields=[{"name": "ImageAndQuestion"}, {"name": "Answer"}],
        templates=[{
            "name": "ImageDx",
            "qfmt": "{{ImageAndQuestion}}",
            "afmt": "{{ImageAndQuestion}}<hr id='answer'>{{Answer}}",
        }],
        css=BASE_CSS + IMAGEDX_CSS_OVERRIDE,
    )


def make_cloze_model(model_id: int) -> genanki.Model:
    return genanki.Model(
        model_id,
        "MeducAI Cloze",
        fields=[{"name": "Text"}, {"name": "Extra"}],
        templates=[{
            "name": "Cloze",
            "qfmt": "{{cloze:Text}}",
            "afmt": "{{cloze:Text}}<hr id='answer'>{{Extra}}",
        }],
        css=BASE_CSS + CLOZE_CSS_EXTRA,
        model_type=genanki.Model.CLOZE,
    )


# ============================================================
# Subdeck Naming
# ============================================================
def sanitize_deck_component(s: str, fallback: str) -> str:
    s = safe_str(s)
    if not s:
        return fallback
    return s.replace("::", " - ")


def decide_deck_name(root_deck: str, specialty: str, anatomy: str, topic: str, split_mode: str) -> str:
    root = sanitize_deck_component(root_deck, "MeducAI")
    if split_mode == "none":
        return root

    sp = sanitize_deck_component(specialty, "UnknownSpecialty")
    if split_mode == "specialty":
        return f"{root}::{sp}"

    an = sanitize_deck_component(anatomy, "UnknownAnatomy")
    if split_mode == "specialty_anatomy":
        return f"{root}::{sp}::{an}"

    tp = sanitize_deck_component(topic, "UnknownTopic")
    return f"{root}::{sp}::{an}::{tp}"


# ============================================================
# Deck Description
# ============================================================
def build_deck_description() -> str:
    return """
<b>📌 MeducAI 권장 Anki 설정</b><br><br>

<b>Daily Limits</b><br>
- New cards/day: <b>9999</b><br>
- Maximum reviews/day: <b>9999</b><br><br>

<b>New Cards</b><br>
- Learning steps: <b>15m</b><br>
- Insertion order: <b>Random</b><br><br>

<b>Lapses</b><br>
- Leech action: <b>Tag only</b><br><br>

<b>Advanced</b><br>
- Maximum interval: <b>25 days</b><br><br>

👉 위 설정은 전문의 시험 대비를 기준으로 최적화되어 있습니다.
""".strip()


# ============================================================
# LaTeX Pattern Report (mining)
# ============================================================
def mine_latex_patterns_from_text(text: str) -> Dict[str, Any]:
    s = safe_str(text)
    cmds = _LATEX_CMD_RE.findall(s)
    blocks = [m.group(1) for m in _INLINE_MATH_RE.finditer(s)]
    return {
        "latex_commands": cmds,
        "inline_math_blocks": blocks,
        "has_dollar": ("$" in s),
    }


def build_latex_report(
    df: pd.DataFrame,
    top_k_cmds: int = 30,
    top_k_blocks: int = 30,
    sample_per_item: int = 3,
) -> Dict[str, Any]:
    from collections import Counter, defaultdict

    cmd_counter = Counter()
    block_counter = Counter()
    cmd_samples = defaultdict(list)
    block_samples = defaultdict(list)

    texts_scanned = 0
    texts_with_dollar = 0
    texts_with_cmd = 0

    for _, r in df.iterrows():
        front = safe_str(r.get("front", ""))
        back = safe_str(r.get("back", ""))
        record_id = safe_str(r.get("record_id", ""))
        entity_name = safe_str(r.get("entity_name", ""))
        card_type = safe_str(r.get("card_type", ""))

        for field_name, text in (("front", front), ("back", back)):
            if not text:
                continue
            texts_scanned += 1
            mined = mine_latex_patterns_from_text(text)

            if mined["has_dollar"]:
                texts_with_dollar += 1
            if mined["latex_commands"]:
                texts_with_cmd += 1

            for c in mined["latex_commands"]:
                cmd_counter[c] += 1
                if len(cmd_samples[c]) < sample_per_item:
                    cmd_samples[c].append({
                        "record_id": record_id,
                        "entity_name": entity_name,
                        "card_type": card_type,
                        "field": field_name,
                        "snippet": text[:240],
                    })

            for b in mined["inline_math_blocks"]:
                key = b.strip()
                if not key:
                    continue
                block_counter[key] += 1
                if len(block_samples[key]) < sample_per_item:
                    block_samples[key].append({
                        "record_id": record_id,
                        "entity_name": entity_name,
                        "card_type": card_type,
                        "field": field_name,
                        "snippet": text[:240],
                    })

    top_cmds = cmd_counter.most_common(top_k_cmds)
    top_blocks = block_counter.most_common(top_k_blocks)

    return {
        "stats": {
            "texts_scanned": texts_scanned,
            "texts_with_dollar": texts_with_dollar,
            "texts_with_latex_command": texts_with_cmd,
            "unique_commands": len(cmd_counter),
            "unique_inline_math_blocks": len(block_counter),
        },
        "command_counts": [{"cmd": k, "count": v} for k, v in top_cmds],
        "block_counts": [{"block": k, "count": v} for k, v in top_blocks],
        "cmd_samples": {k: cmd_samples[k] for k, _ in top_cmds},
        "block_samples": {k: block_samples[k] for k, _ in top_blocks},
    }


def write_latex_report(report: Dict[str, Any], out_path: Path) -> None:
    ensure_dir(out_path.parent)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


# ============================================================
# Main
# ============================================================
def main() -> None:
    parser = argparse.ArgumentParser(description="MeducAI Step 04 - Export Anki .apkg")

    parser.add_argument("--provider", required=True)
    parser.add_argument("--run_tag", required=True)
    parser.add_argument("--base_dir", default=".")
    parser.add_argument("--input_csv", default="", help="Optional override CSV path.")
    parser.add_argument("--root_deck", default="", help="Root deck name (default=MeducAI_<provider>_<run_tag>)")
    parser.add_argument("--out_dir", default="", help="Default=6_Distributions/anki")

    parser.add_argument(
        "--split_mode",
        default="specialty_anatomy_topic",
        choices=["none", "specialty", "specialty_anatomy", "specialty_anatomy_topic"],
        help="Split decks into subdecks by specialty/anatomy/topic.",
    )

    parser.add_argument("--attach_images", action="store_true", help="Attach entity images if available.")
    parser.add_argument(
        "--attach_default_to",
        default="back",
        choices=["back", "front"],
        help="For non-Image_Diagnosis cards: where to attach images when available.",
    )
    parser.add_argument("--limit", type=int, default=0, help="0=all; else cap number of cards (debug)")

    # LaTeX report options
    parser.add_argument("--report_latex", action="store_true", help="Scan CSV and write LaTeX pattern report (json).")
    parser.add_argument("--report_latex_topk", type=int, default=30, help="Top-K LaTeX commands/blocks to report.")
    parser.add_argument("--report_latex_samples", type=int, default=3, help="Samples per LaTeX item in report.")

    args = parser.parse_args()
    base_dir = Path(args.base_dir).resolve()

    # Input CSV
    if args.input_csv.strip():
        in_csv = Path(args.input_csv).expanduser()
        if not in_csv.is_absolute():
            in_csv = (base_dir / in_csv).resolve()
    else:
        in_csv = base_dir / "2_Data" / "metadata" / "generated" / args.provider / f"anki_cards_{args.provider}_{args.run_tag}.csv"

    df = load_csv(in_csv)

    # Normalize required columns
    expected = ["record_id", "entity_name", "card_type", "front", "back", "tags", "specialty", "anatomy", "topic"]
    for col in expected:
        if col not in df.columns:
            df[col] = ""

    if args.limit and args.limit > 0:
        df = df.head(args.limit)

    # Output directory
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir.strip() else (base_dir / "6_Distributions" / "anki")
    ensure_dir(out_dir)

    # Optional: LaTeX pattern mining report
    if args.report_latex:
        report_path = out_dir / f"latex_report_{args.provider}_{args.run_tag}.json"
        report = build_latex_report(
            df=df,
            top_k_cmds=args.report_latex_topk,
            top_k_blocks=args.report_latex_topk,
            sample_per_item=args.report_latex_samples,
        )
        write_latex_report(report, report_path)
        print(f"🧾 LaTeX report written: {report_path}")

    # Images
    media_files: List[str] = []
    image_index: Dict[Tuple[str, str], ImageIndexEntry] = {}
    entity_manifest = (
        base_dir
        / "2_Data"
        / "images"
        / "generated"
        / args.provider
        / args.run_tag
        / "entity"
        / f"manifest_{args.provider}_{args.run_tag}_entity.jsonl"
    )
    if args.attach_images:
        image_index = build_entity_image_index(entity_manifest)

    root_deck = args.root_deck.strip() or f"MeducAI_{args.provider}_{args.run_tag}"
    deck_description = build_deck_description()

    # Models
    model_basic = make_basic_model(stable_id_from_text(root_deck + "_basic"))
    model_mcq = make_mcq_model(stable_id_from_text(root_deck + "_mcq"))
    model_imgdx = make_image_dx_model(stable_id_from_text(root_deck + "_imgdx"))
    model_cloze = make_cloze_model(stable_id_from_text(root_deck + "_cloze"))

    # Deck map
    decks: Dict[str, genanki.Deck] = {}

    def get_deck(deck_name: str) -> genanki.Deck:
        if deck_name in decks:
            return decks[deck_name]
        deck_id = stable_id_from_text(deck_name)
        d = genanki.Deck(deck_id, deck_name)
        d.description = deck_description
        decks[deck_name] = d
        return d

    # Counters
    n_notes = 0
    n_mcq = 0
    n_imgdx = 0
    n_cloze = 0
    n_basic = 0
    n_with_images = 0

    for _, r in df.iterrows():
        record_id = safe_str(r.get("record_id"))
        entity_name = safe_str(r.get("entity_name"))
        card_type = safe_str(r.get("card_type"))
        front = safe_str(r.get("front"))
        back = safe_str(r.get("back"))
        tags = split_tags(safe_str(r.get("tags")))

        specialty = safe_str(r.get("specialty"))
        anatomy = safe_str(r.get("anatomy"))
        topic = safe_str(r.get("topic"))

        if not front or not back:
            continue

        deck_name = decide_deck_name(root_deck, specialty, anatomy, topic, args.split_mode)
        deck = get_deck(deck_name)

        # optional image
        img_html = ""
        if args.attach_images and record_id and entity_name:
            img_html = attach_image_html(record_id, entity_name, image_index, media_files)
            if img_html:
                n_with_images += 1

        ct = card_type or "Basic"
        guid = make_note_guid(record_id, entity_name, ct, front)

        # Cloze
        if ct.lower().startswith("cloze") or CLOZE_RE.search(front):
            if CLOZE_RE.search(front):
                # Cloze markup must survive; also apply markdown/latex normalization safely.
                # wrap_div=False reduces risk of cloze filter edge cases.
                text_field = anki_html(front, wrap_div=False)
                extra_field = render_basic_html(back)
                if img_html:
                    extra_field += img_html

                note = genanki.Note(model=model_cloze, fields=[text_field, extra_field], tags=tags, guid=guid)
                deck.add_note(note)
                n_cloze += 1
                n_notes += 1
                continue

        # MCQ
        if ct == "MCQ_Vignette":
            stem_opts = render_mcq_front(front)
            explanation = render_mcq_back(back)

            if img_html:
                if args.attach_default_to == "front":
                    stem_opts += img_html
                else:
                    explanation += img_html

            note = genanki.Note(model=model_mcq, fields=[stem_opts, explanation], tags=tags, guid=guid)
            deck.add_note(note)
            n_mcq += 1
            n_notes += 1
            continue

        # Image Diagnosis (image front fixed)
        if ct == "Image_Diagnosis":
            q_html = render_basic_html(front)
            front_field = (img_html + q_html) if img_html else q_html
            back_field = render_basic_html(back)

            note = genanki.Note(model=model_imgdx, fields=[front_field, back_field], tags=tags, guid=guid)
            deck.add_note(note)
            n_imgdx += 1
            n_notes += 1
            continue

        # Basic fallback
        f_field = render_basic_html(front)
        b_field = render_basic_html(back)
        if img_html:
            if args.attach_default_to == "front":
                f_field += img_html
            else:
                b_field += img_html

        note = genanki.Note(model=model_basic, fields=[f_field, b_field], tags=tags, guid=guid)
        deck.add_note(note)
        n_basic += 1
        n_notes += 1

    # Write package
    out_path = out_dir / f"MeducAI_{args.provider}_{args.run_tag}.apkg"
    pkg = genanki.Package(list(decks.values()))
    if args.attach_images and media_files:
        pkg.media_files = media_files

    pkg.write_to_file(str(out_path))

    print("✅ Step 04 export completed.")
    print(f"  Input CSV:   {in_csv}")
    print(f"  Root deck:   {root_deck}")
    print(f"  Split mode:  {args.split_mode}")
    print(f"  Deck count:  {len(decks)}")
    print(f"  Notes total: {n_notes}")
    print(f"    MCQ:       {n_mcq}")
    print(f"    ImageDx:   {n_imgdx}")
    print(f"    Cloze:     {n_cloze}")
    print(f"    Basic:     {n_basic}")
    print(f"  With images: {n_with_images} (attach_images={args.attach_images})")
    print(f"  Output:      {out_path}")
    if args.attach_images:
        print(f"  Entity manifest: {entity_manifest} (exists={entity_manifest.exists()})")


if __name__ == "__main__":
    main()

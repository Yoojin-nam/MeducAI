#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
04_export_anki.py (MeducAI v3.x)
--------------------------------
Features:
1) card_type별 템플릿(Anki Model) 분리
   - MCQ_Vignette: 선택지 서식 고정(HTML 라디오 스타일)
   - Image_Diagnosis: 이미지 front 고정(가능하면 entity image를 front에 붙임)
   - Cloze_Finding: Cloze 모델(실제 cloze 마크업이 있을 때만)
   - Physics_Concept: Basic(필요시 향후 확장)

2) Specialty/Topic 별 하위 덱 자동 분리
   - RootDeck::Specialty::Topic

Inputs:
- 2_Data/metadata/generated/<provider>/anki_cards_<provider>_<run_tag>.csv

Optional images:
- 2_Data/images/generated/<provider>/<run_tag>/entity/manifest_<provider>_<run_tag>_entity.jsonl
- 2_Data/images/generated/<provider>/<run_tag>/entity/*.png

Output:
- 6_Distributions/anki/MeducAI_<provider>_<run_tag>.apkg
"""

from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import genanki


# -------------------------
# Constants / Regex
# -------------------------
CLOZE_RE = re.compile(r"\{\{c\d+::", re.IGNORECASE)
MCQ_OPT_RE = re.compile(r"^\s*([A-Ea-e])[\)\.\:]\s+(.*)\s*$")  # e.g., "A) text" / "B. text"
MCQ_ANSWER_RE = re.compile(r"(?:^|\b)(?:answer|정답)\s*[:\-]?\s*([A-Ea-e])\b", re.IGNORECASE)


# -------------------------
# IO Helpers
# -------------------------
def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    return df


def safe_str(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()


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


# -------------------------
# Image Index
# -------------------------
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
    If image exists: add to media_files and return <img> HTML snippet.
    """
    key = (safe_str(record_id), safe_str(entity_name).lower())
    ent = image_index.get(key)
    if not ent:
        return ""

    p = Path(ent.output_path)
    if not p.exists():
        return ""

    # Add absolute filepath to media list (genanki will pack it)
    if str(p) not in media_files:
        media_files.append(str(p))

    media_name = p.name
    return f'<div style="margin:10px 0;"><img src="{html.escape(media_name)}" style="max-width:100%; height:auto;"></div>'


# -------------------------
# Stable IDs
# -------------------------
def stable_id_from_text(text: str) -> int:
    import hashlib
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


# -------------------------
# Card Rendering
# -------------------------
def parse_mcq(front_text: str) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Try to split MCQ stem and options.
    Returns: (stem_html, options_list[(letter, text)])
    Strategy:
      - treat lines matching A) / B. / C: as options
      - everything before first option is stem
    """
    lines = [ln.rstrip() for ln in safe_str(front_text).splitlines() if ln.strip()]
    opts: List[Tuple[str, str]] = []
    stem_lines: List[str] = []

    found_opts = False
    for ln in lines:
        m = MCQ_OPT_RE.match(ln)
        if m:
            found_opts = True
            letter = m.group(1).upper()
            txt = m.group(2).strip()
            opts.append((letter, txt))
        else:
            if not found_opts:
                stem_lines.append(ln)
            else:
                # continuation line for last option
                if opts:
                    prev_l, prev_t = opts[-1]
                    opts[-1] = (prev_l, (prev_t + " " + ln).strip())
                else:
                    stem_lines.append(ln)

    stem_html = "<div>" + "<br>".join(html.escape(x) for x in stem_lines) + "</div>" if stem_lines else "<div></div>"
    return stem_html, opts


def render_mcq_front(front_text: str) -> str:
    stem_html, opts = parse_mcq(front_text)

    # If we can't parse options, keep original but still wrap for consistency
    if not opts:
        return f"<div>{html.escape(safe_str(front_text)).replace(chr(10), '<br>')}</div>"

    # Render options in fixed style (radio-like)
    opt_rows = []
    for letter, txt in opts:
        opt_rows.append(
            f"""
            <label style="display:block; margin:6px 0; line-height:1.35;">
              <input type="radio" disabled style="margin-right:8px;">
              <b>{html.escape(letter)}.</b> {html.escape(txt)}
            </label>
            """.strip()
        )
    options_html = "<div style='margin-top:10px;'>" + "\n".join(opt_rows) + "</div>"
    return stem_html + options_html


def extract_answer_letter(back_text: str) -> Optional[str]:
    m = MCQ_ANSWER_RE.search(safe_str(back_text))
    if not m:
        return None
    return m.group(1).upper()


def render_mcq_back(back_text: str) -> str:
    """
    Encourage consistent answer layout:
    - If answer letter is detectable, prepend "Answer: X"
    - Then the rest of explanation (original back)
    """
    b = safe_str(back_text)
    ans = extract_answer_letter(b)
    if ans:
        prefix = f"<div><b>Answer:</b> {html.escape(ans)}</div><hr>"
        return prefix + f"<div>{html.escape(b).replace(chr(10), '<br>')}</div>"
    return f"<div>{html.escape(b).replace(chr(10), '<br>')}</div>"


def render_basic_html(text: str) -> str:
    return f"<div>{html.escape(safe_str(text)).replace(chr(10), '<br>')}</div>"


# -------------------------
# Anki Models (Templates)
# -------------------------
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
        css="""
.card { font-family: Arial; font-size: 18px; text-align: left; color: black; background-color: white; }
img { display: block; margin-left: auto; margin-right: auto; }
""",
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
        css="""
.card { font-family: Arial; font-size: 18px; text-align: left; color: black; background-color: white; }
label { cursor: default; }
img { display: block; margin-left: auto; margin-right: auto; }
""",
    )


def make_image_dx_model(model_id: int) -> genanki.Model:
    """
    Image_Diagnosis: front에 이미지가 항상 먼저 오도록 설계.
    (필드에 이미지를 넣는 방식으로 강제)
    """
    return genanki.Model(
        model_id,
        "MeducAI Image Diagnosis",
        fields=[{"name": "ImageAndQuestion"}, {"name": "Answer"}],
        templates=[{
            "name": "ImageDx",
            "qfmt": "{{ImageAndQuestion}}",
            "afmt": "{{ImageAndQuestion}}<hr id='answer'>{{Answer}}",
        }],
        css="""
.card { font-family: Arial; font-size: 18px; text-align: left; color: black; background-color: white; }
img { display: block; margin-left: auto; margin-right: auto; }
""",
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
        css="""
.card { font-family: Arial; font-size: 18px; text-align: left; color: black; background-color: white; }
img { display: block; margin-left: auto; margin-right: auto; }
""",
        model_type=genanki.Model.CLOZE,
    )


# -------------------------
# Deck naming / splitting
# -------------------------
def sanitize_deck_component(s: str, fallback: str = "Unknown") -> str:
    s = safe_str(s)
    if not s:
        return fallback
    # Anki deck separator is "::", so remove it from components
    s = s.replace("::", " - ")
    return s


def decide_deck_name(
    root_deck: str,
    specialty: str,
    topic: str,
    split_mode: str,
) -> str:
    """
    split_mode:
      - none: root only
      - specialty: Root::Specialty
      - specialty_topic: Root::Specialty::Topic
    """
    root = sanitize_deck_component(root_deck, "MeducAI")
    if split_mode == "none":
        return root

    sp = sanitize_deck_component(specialty, "UnknownSpecialty")
    if split_mode == "specialty":
        return f"{root}::{sp}"

    tp = sanitize_deck_component(topic, "UnknownTopic")
    return f"{root}::{sp}::{tp}"


# -------------------------
# Main
# -------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="MeducAI Step 04 - Export Anki .apkg (card_type templates + subdecks)")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--run_tag", required=True)
    parser.add_argument("--base_dir", default=".")

    parser.add_argument("--root_deck", default="", help="Root deck name (default=MeducAI_<provider>_<run_tag>)")
    parser.add_argument("--out_dir", default="", help="Default=6_Distributions/anki")

    parser.add_argument(
        "--split_mode",
        default="specialty_topic",
        choices=["none", "specialty", "specialty_topic"],
        help="Split decks into subdecks by specialty/topic.",
    )

    parser.add_argument("--attach_images", action="store_true", help="Attach entity images if available.")
    parser.add_argument(
        "--attach_default_to",
        default="back",
        choices=["back", "front"],
        help="For non-Image_Diagnosis cards: where to attach images when available.",
    )
    parser.add_argument("--limit", type=int, default=0, help="0=all; else cap number of cards (debug)")
    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()

    in_csv = base_dir / "2_Data" / "metadata" / "generated" / args.provider / f"anki_cards_{args.provider}_{args.run_tag}.csv"
    df = load_csv(in_csv)

    # Normalize columns we will use
    expected = [
        "record_id", "entity_name", "card_type", "front", "back", "tags",
        # for split
        "specialty", "topic",
    ]
    for col in expected:
        if col not in df.columns:
            df[col] = ""

    if args.limit and args.limit > 0:
        df = df.head(args.limit)

    # Image index
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

    # Root deck name
    root_deck = args.root_deck.strip() or f"MeducAI_{args.provider}_{args.run_tag}"

    # Models
    model_basic = make_basic_model(stable_id_from_text(root_deck + "_basic"))
    model_mcq = make_mcq_model(stable_id_from_text(root_deck + "_mcq"))
    model_imgdx = make_image_dx_model(stable_id_from_text(root_deck + "_imgdx"))
    model_cloze = make_cloze_model(stable_id_from_text(root_deck + "_cloze"))

    # Decks map: deck_name -> genanki.Deck
    decks: Dict[str, genanki.Deck] = {}

    def get_deck(deck_name: str) -> genanki.Deck:
        if deck_name in decks:
            return decks[deck_name]
        deck_id = stable_id_from_text(deck_name)
        d = genanki.Deck(deck_id, deck_name)
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
        topic = safe_str(r.get("topic"))

        if not front or not back:
            continue

        deck_name = decide_deck_name(root_deck, specialty, topic, args.split_mode)
        deck = get_deck(deck_name)

        # Prepare image (if possible)
        img_html = ""
        if args.attach_images and record_id and entity_name:
            img_html = attach_image_html(record_id, entity_name, image_index, media_files)
            if img_html:
                n_with_images += 1

        ct = card_type or "Basic"

        # 1) Cloze_Finding
        if ct.lower().startswith("cloze") or CLOZE_RE.search(front):
            # Only cloze if markup exists; otherwise fallback basic
            if CLOZE_RE.search(front):
                text_field = front
                extra_field = back
                # by default, keep image on Extra (back side) unless you explicitly cloze with image
                if img_html:
                    extra_field = extra_field + img_html

                note = genanki.Note(
                    model=model_cloze,
                    fields=[text_field, extra_field],
                    tags=tags,
                )
                deck.add_note(note)
                n_cloze += 1
                n_notes += 1
                continue

        # 2) MCQ_Vignette
        if ct == "MCQ_Vignette":
            stem_opts = render_mcq_front(front)
            explanation = render_mcq_back(back)

            # MCQ는 기본적으로 이미지를 "back"에 붙이는 것이 안전(문항에서 bias 줄이기)
            if img_html:
                if args.attach_default_to == "front":
                    stem_opts = stem_opts + img_html
                else:
                    explanation = explanation + img_html

            note = genanki.Note(
                model=model_mcq,
                fields=[stem_opts, explanation],
                tags=tags,
            )
            deck.add_note(note)
            n_mcq += 1
            n_notes += 1
            continue

        # 3) Image_Diagnosis (이미지 front 고정)
        if ct == "Image_Diagnosis":
            # 이미지가 있으면 front에 반드시 먼저
            if img_html:
                q_html = render_basic_html(front)
                front_field = img_html + q_html
            else:
                # 이미지 없으면 질문만 (그래도 model 유지)
                front_field = render_basic_html(front)

            back_field = render_basic_html(back)

            note = genanki.Note(
                model=model_imgdx,
                fields=[front_field, back_field],
                tags=tags,
            )
            deck.add_note(note)
            n_imgdx += 1
            n_notes += 1
            continue

        # 4) Physics_Concept 등: Basic
        f_field = render_basic_html(front)
        b_field = render_basic_html(back)

        if img_html:
            if args.attach_default_to == "front":
                f_field = f_field + img_html
            else:
                b_field = b_field + img_html

        note = genanki.Note(
            model=model_basic,
            fields=[f_field, b_field],
            tags=tags,
        )
        deck.add_note(note)
        n_basic += 1
        n_notes += 1

    # Package
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir.strip() else (base_dir / "6_Distributions" / "anki")
    ensure_dir(out_dir)
    out_path = out_dir / f"MeducAI_{args.provider}_{args.run_tag}.apkg"

    # genanki.Package can take a list of decks (subdecks included)
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

#!/usr/bin/env python3
"""
Generate KakaoTalk announcement sample PDF in *distribution style*.

What this produces (ONE file):
- Cover: identical to distribution cover (uses `3_Code/src/tools/assets/cover_base.jpg`)
  with only "SAMPLE" overlay (no aggressive red watermark)
- For 3 selected groups: Objective Goal → Master Table → Infographic
  rendered using the same code as distribution PDFs (`3_Code/src/tools/build_distribution_pdf.py`)
- Append Anki card samples: BASIC 6 + MCQ 6 (front | back | image), landscape A4

Default source:
- run_tag=FINAL_DISTRIBUTION, arm=G (same as `6_Distributions/MeducAI_Final_Share/PDF`)
"""

import argparse
import csv
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image as RLImage,
    KeepTogether,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from PIL import Image as PILImage

def _load_distribution_pdf_module(base_dir: Path):
    """Import `3_Code/src/tools/build_distribution_pdf.py` via importlib."""
    import importlib.util

    mod_path = (base_dir / "3_Code" / "src" / "tools" / "build_distribution_pdf.py").resolve()
    if not mod_path.exists():
        raise FileNotFoundError(f"build_distribution_pdf.py not found: {mod_path}")
    spec = importlib.util.spec_from_file_location("build_distribution_pdf", mod_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to import build_distribution_pdf from: {mod_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_groups(groups_csv: Path) -> List[Dict[str, Any]]:
    """Load groups from CSV."""
    groups = []
    with open(groups_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            groups.append(row)
    return groups


def load_cards(cards_csv: Path) -> List[Dict[str, Any]]:
    """Load cards from CSV."""
    cards = []
    with open(cards_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cards.append(row)
    return cards


def load_s5(s5_csv: Path) -> List[Dict[str, Any]]:
    """Load S5 evaluation rows from CSV (card-level)."""
    rows: List[Dict[str, Any]] = []
    with open(s5_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def _fnum(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        s = str(x).strip()
        if s == "":
            return default
        return float(s)
    except Exception:
        return default


def compute_group_s5_stats(
    s5_rows: List[Dict[str, Any]],
    *,
    run_tag: str,
    arm: str,
) -> Dict[str, Dict[str, Any]]:
    """Aggregate S5 metrics per group_id for the specified run_tag/arm."""
    arm_u = arm.strip().upper()
    rt = run_tag.strip()
    by_gid: Dict[str, List[Dict[str, Any]]] = {}
    for r in s5_rows:
        if (r.get("run_tag") or "").strip() != rt:
            continue
        if (r.get("arm") or "").strip().upper() != arm_u:
            continue
        gid = (r.get("group_id") or "").strip()
        if not gid:
            continue
        by_gid.setdefault(gid, []).append(r)

    out: Dict[str, Dict[str, Any]] = {}
    for gid, rows in by_gid.items():
        n = len(rows)
        if n == 0:
            continue
        decisions = [(r.get("s5_decision") or "").strip().upper() for r in rows]
        pass_rate = sum(d == "PASS" for d in decisions) / n
        avg_tech = sum(_fnum(r.get("s5_technical_accuracy")) for r in rows) / n
        avg_edu = sum(_fnum(r.get("s5_educational_quality")) for r in rows) / n
        avg_img = sum(_fnum(r.get("s5_card_image_quality")) for r in rows) / n
        any_blocking = any(int(_fnum(r.get("s5_blocking_error"))) != 0 for r in rows)
        any_img_blocking = any(int(_fnum(r.get("s5_card_image_blocking_error"))) != 0 for r in rows)
        regen_rate = sum(int(_fnum(r.get("s5_was_regenerated"))) == 1 for r in rows) / n
        out[gid] = {
            "n_cards": n,
            "pass_rate": pass_rate,
            "avg_tech": avg_tech,
            "avg_edu": avg_edu,
            "avg_img": avg_img,
            "any_blocking": any_blocking,
            "any_img_blocking": any_img_blocking,
            "regen_rate": regen_rate,
        }
    return out


def select_sample_groups(groups: List[Dict[str, Any]], num_groups: int = 3, seed: int = 42) -> List[Dict[str, Any]]:
    """Select diverse sample groups with good entity counts."""
    # Filter groups with good entity count
    good_groups = [g for g in groups if int(g.get("entity_count", 0)) >= 8]
    
    random.seed(seed)
    selected = random.sample(good_groups, min(num_groups, len(good_groups)))
    
    return selected


def select_sample_groups_by_s5(
    *,
    groups: List[Dict[str, Any]],
    group_s5: Dict[str, Dict[str, Any]],
    num_groups: int,
    seed: int,
    allowed_group_ids: set,
    diagnostic_imaging_only: bool,
    s5_policy: str,
) -> List[Dict[str, Any]]:
    """
    Select groups by S5 quality.

    - s5_policy="perfect": PASS 100% + avg(tech)=1.0 + avg(edu)=5.0 + avg(img)=5.0 (and no blocking errors)
    - s5_policy="high": PASS >= 0.95 + avg(edu) >= 4.8 + avg(tech) >= 0.95 + avg(img) >= 4.8 (and no blocking errors)
    """
    random.seed(seed)
    eps = 1e-6
    pool: List[Tuple[float, Dict[str, Any]]] = []
    for g in groups:
        gid = (g.get("group_id") or "").strip()
        if not gid:
            continue
        if gid not in allowed_group_ids:
            continue
        if int(g.get("entity_count", 0)) < 8:
            continue
        if diagnostic_imaging_only and "diagnostic_imaging" not in (g.get("group_path") or ""):
            continue
        s = group_s5.get(gid)
        if not s:
            continue
        if s.get("any_blocking") or s.get("any_img_blocking"):
            continue

        pass_rate = float(s.get("pass_rate") or 0.0)
        avg_edu = float(s.get("avg_edu") or 0.0)
        avg_tech = float(s.get("avg_tech") or 0.0)
        avg_img = float(s.get("avg_img") or 0.0)
        if s5_policy == "perfect":
            if not (pass_rate >= 1.0 - eps and avg_edu >= 5.0 - eps and avg_tech >= 1.0 - eps and avg_img >= 5.0 - eps):
                continue
        elif s5_policy == "high":
            if not (pass_rate >= 0.95 and avg_edu >= 4.8 and avg_tech >= 0.95 and avg_img >= 4.8):
                continue
        else:
            # fall back to random if policy is unknown
            continue

        # Primary score (quality) + tiny random jitter for stable tie-break
        score = (pass_rate * 1000.0) + (avg_edu * 10.0) + (avg_tech * 5.0) + (avg_img * 1.0) + random.random() * 1e-6
        pool.append((score, g))

    pool.sort(key=lambda x: x[0], reverse=True)

    # Prefer diversity by top-level specialty prefix (before first ' > ')
    picked: List[Dict[str, Any]] = []
    used_prefix: set = set()
    for _, g in pool:
        prefix = ((g.get("group_path") or "").split(">")[0]).strip()
        if prefix and prefix in used_prefix:
            continue
        picked.append(g)
        if prefix:
            used_prefix.add(prefix)
        if len(picked) >= num_groups:
            break

    # If not enough, fill from remaining irrespective of prefix
    if len(picked) < num_groups:
        for _, g in pool:
            if g in picked:
                continue
            picked.append(g)
            if len(picked) >= num_groups:
                break

    return picked


def select_sample_cards(
    cards: List[Dict[str, Any]],
    num_basic: int = 6,
    num_mcq: int = 6,
    seed: int = 42,
) -> Dict[str, List[Dict[str, Any]]]:
    """Select sample cards (basic and MCQ)."""
    basic_cards = [c for c in cards if c.get("card_type") == "BASIC"]
    mcq_cards = [c for c in cards if c.get("card_type") == "MCQ"]
    
    random.seed(seed)
    
    selected_basic = random.sample(basic_cards, min(num_basic, len(basic_cards)))
    selected_mcq = random.sample(mcq_cards, min(num_mcq, len(mcq_cards)))
    
    return {
        "basic": selected_basic,
        "mcq": selected_mcq,
    }


def select_sample_cards_by_s5(
    *,
    cards: List[Dict[str, Any]],
    s5_by_card_uid: Dict[str, Dict[str, Any]],
    base_dir: Path,
    run_tag: str,
    arm: str,
    num_basic: int,
    num_mcq: int,
    seed: int,
    diagnostic_imaging_only: bool,
    s5_policy: str,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Select BASIC/MCQ cards by S5 quality.

    - s5_policy="perfect": PASS + blocking=0 + (tech=1.0, edu=5, img=5)
    - s5_policy="high": PASS + blocking=0 + (tech>=0.95, edu>=4.8, img>=4.8)
    """
    random.seed(seed)
    eps = 1e-6
    rt = run_tag.strip()
    arm_u = arm.strip().upper()
    img_root = (base_dir / "6_Distributions" / "Final_QA" / "AppSheet_Export").resolve()

    def ok_card(c: Dict[str, Any]) -> Tuple[bool, float]:
        uid = (c.get("card_uid") or "").strip()
        if not uid:
            return False, 0.0
        s5 = s5_by_card_uid.get(uid)
        if not s5:
            return False, 0.0
        if (c.get("run_tag") or "").strip() != rt:
            return False, 0.0
        if (c.get("arm") or "").strip().upper() != arm_u:
            return False, 0.0
        if diagnostic_imaging_only and "diagnostic_imaging" not in (c.get("group_path") or ""):
            return False, 0.0

        # require image exists for the sample PDF
        rel = (c.get("image_filename") or "").strip()
        if not rel:
            return False, 0.0
        if not (img_root / rel).exists():
            return False, 0.0

        if (s5.get("s5_decision") or "").strip().upper() != "PASS":
            return False, 0.0
        if int(_fnum(s5.get("s5_blocking_error"))) != 0:
            return False, 0.0
        if int(_fnum(s5.get("s5_card_image_blocking_error"))) != 0:
            return False, 0.0

        tech = _fnum(s5.get("s5_technical_accuracy"))
        edu = _fnum(s5.get("s5_educational_quality"))
        img = _fnum(s5.get("s5_card_image_quality"))
        if s5_policy == "perfect":
            if not (tech >= 1.0 - eps and edu >= 5.0 - eps and img >= 5.0 - eps):
                return False, 0.0
        elif s5_policy == "high":
            if not (tech >= 0.95 and edu >= 4.8 and img >= 4.8):
                return False, 0.0
        else:
            return False, 0.0

        # Higher is better; tiny random jitter for tie-break
        score = (edu * 10.0) + (tech * 5.0) + (img * 1.0) + random.random() * 1e-6
        return True, score

    def pick(card_type: str, k: int) -> List[Dict[str, Any]]:
        if k <= 0:
            return []
        pool: List[Tuple[float, Dict[str, Any]]] = []
        for c in cards:
            if (c.get("card_type") or "").strip().upper() != card_type:
                continue
            ok, sc = ok_card(c)
            if not ok:
                continue
            pool.append((sc, c))
        pool.sort(key=lambda x: x[0], reverse=True)

        out: List[Dict[str, Any]] = []
        used_prefix: set = set()
        for _, c in pool:
            prefix = ((c.get("group_path") or "").split(">")[0]).strip()
            if prefix and prefix in used_prefix:
                continue
            out.append(c)
            if prefix:
                used_prefix.add(prefix)
            if len(out) >= k:
                break
        if len(out) < k:
            for _, c in pool:
                if c in out:
                    continue
                out.append(c)
                if len(out) >= k:
                    break
        return out

    return {"basic": pick("BASIC", num_basic), "mcq": pick("MCQ", num_mcq)}

def select_specific_cards(
    cards: List[Dict[str, Any]],
    *,
    basic_indices_1based: List[int],
    mcq_indices_1based: List[int],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Select specific card numbers (1-based) from the CSV order.
    Example: basic_indices_1based=[2,4] selects the 2nd and 4th BASIC cards in Cards.csv order.
    """
    basic_cards = [c for c in cards if (c.get("card_type") or "").strip().upper() == "BASIC"]
    mcq_cards = [c for c in cards if (c.get("card_type") or "").strip().upper() == "MCQ"]

    def pick(pool: List[Dict[str, Any]], idxs_1based: List[int], label: str) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for n in idxs_1based:
            if n <= 0:
                raise ValueError(f"{label} index must be 1-based positive int; got {n}")
            i = n - 1
            if i >= len(pool):
                raise ValueError(f"{label} index {n} out of range (pool size={len(pool)})")
            out.append(pool[i])
        return out

    return {
        "basic": pick(basic_cards, basic_indices_1based, "BASIC"),
        "mcq": pick(mcq_cards, mcq_indices_1based, "MCQ"),
    }


def _append_anki_section(
    *,
    story: List[Any],
    cards: Dict[str, List[Dict[str, Any]]],
    base_dir: Path,
    korean_font: str,
    korean_font_bold: str,
    dist: Any,
) -> None:
    """Append Anki section with the same header/footer system as distribution PDFs."""
    styles = getSampleStyleSheet()

    # Header label for this section
    story.append(dist.HeaderInfoFlowable("SAMPLE", "ANKI CARDS", "SAMPLE_ANKI"))

    title_style = ParagraphStyle(
        "AnkiTitle",
        parent=styles["Heading2"],
        fontName=korean_font_bold,
        fontSize=14,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=0.35 * cm,
    )
    story.append(Paragraph("Anki Cards (Sample)", title_style))

    section_style = ParagraphStyle(
        "AnkiSection",
        parent=styles["Normal"],
        fontName=korean_font_bold,
        fontSize=11,
        textColor=colors.HexColor("#1B3A5F"),
        spaceBefore=0.2 * cm,
        spaceAfter=0.2 * cm,
    )

    body_style = ParagraphStyle(
        "AnkiBody",
        parent=styles["Normal"],
        fontName=korean_font,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#2D3748"),
    )

    header_cell_style = ParagraphStyle(
        "AnkiHeaderCell",
        parent=body_style,
        fontName=korean_font_bold,
        fontSize=9,
        textColor=colors.white,
    )

    def card_table(card: Dict[str, Any], idx: int) -> Table:
        front = (card.get("front") or "").strip()
        back = (card.get("back") or "").strip()
        # Keep cards compact to avoid page-splitting within a card
        max_front = 400
        max_back = 400
        if (card.get("card_type") or "").strip().upper() == "MCQ":
            # MCQ tends to be longer (options); cap a bit more aggressively
            max_front = 350
            max_back = 350
        if len(front) > max_front:
            front = front[:max_front] + "…"
        if len(back) > max_back:
            back = back[:max_back] + "…"

        front_p = Paragraph(front.replace("\n", "<br/>"), body_style)
        back_p = Paragraph(back.replace("\n", "<br/>"), body_style)

        img_flow: Any
        rel = (card.get("image_filename") or "").strip()
        img_path = (base_dir / "6_Distributions" / "Final_QA" / "AppSheet_Export" / rel).resolve()
        if rel and img_path.exists():
            try:
                with PILImage.open(img_path) as im:
                    w, h = im.size
                aspect = (w / h) if h else 1.0
                max_w = 6.5 * cm
                max_h = 4.5 * cm
                if aspect > (max_w / max_h):
                    iw = max_w
                    ih = max_w / aspect
                else:
                    ih = max_h
                    iw = max_h * aspect
                img_flow = RLImage(str(img_path), width=iw, height=ih)
            except Exception:
                img_flow = Paragraph("이미지 로드 실패", ParagraphStyle("ImgErr", parent=body_style, textColor=colors.HexColor("#A00")))
        else:
            img_flow = Paragraph("이미지 없음", ParagraphStyle("ImgNA", parent=body_style, textColor=colors.HexColor("#999999")))

        headers = [
            Paragraph(f"<b>카드 {idx} | 앞면</b>", header_cell_style),
            Paragraph("<b>뒷면</b>", header_cell_style),
            Paragraph("<b>이미지</b>", header_cell_style),
        ]
        row = [front_p, back_p, img_flow]

        t = Table(
            [headers, row],
            colWidths=[8.2 * cm, 8.2 * cm, 7.0 * cm],
            hAlign="LEFT",
            # Prevent header row (title) and content row from splitting across pages
            splitByRow=0,
        )
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4A90D9")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return t

    basic = cards.get("basic", []) or []
    mcq = cards.get("mcq", []) or []

    # BASIC (optional)
    if basic:
        story.append(Paragraph(f"주관식 (BASIC) {len(basic)}문제", section_style))
        for i, c in enumerate(basic, 1):
            # Keep each card together (avoid header/content splitting)
            story.append(KeepTogether([card_table(c, i), Spacer(1, 0.35 * cm)]))
            if i % 2 == 0 and i < len(basic):
                story.append(PageBreak())

        # Separate sections only if MCQ exists
        if mcq:
            story.append(PageBreak())

    # MCQ (optional)
    if mcq:
        story.append(Paragraph(f"객관식 (MCQ) {len(mcq)}문제", section_style))
        for i, c in enumerate(mcq, 1):
            # Keep MCQ title/content on the same page
            story.append(KeepTogether([card_table(c, i), Spacer(1, 0.35 * cm)]))
            if i % 2 == 0 and i < len(mcq):
                story.append(PageBreak())


def generate_sample_pdf(
    *,
    base_dir: Path,
    selected_groups: List[Dict[str, Any]],
    sample_cards: Dict[str, List[Dict[str, Any]]],
    out_path: Path,
    run_tag: str,
    arm: str,
) -> None:
    """Generate ONE combined PDF in distribution style (+ appended Anki section)."""
    dist = _load_distribution_pdf_module(base_dir)

    # Same font registration logic as distribution builder (Nanum preferred)
    korean_font, korean_font_bold = dist.setup_korean_fonts()
    styles = dist.create_pdf_styles(korean_font, korean_font_bold)

    page_size = landscape(A4)
    page_width, page_height = page_size

    # Build doc in the same way as distribution PDFs (header/footer + cover flowable)
    doc = dist.HeaderTrackingDocTemplate(str(out_path), pagesize=page_size)
    doc.addPageTemplates([dist.create_main_page_template(page_size, korean_font=korean_font)])

    gen_dir = dist.get_generated_dir(base_dir, run_tag)
    s1_path = gen_dir / f"stage1_struct__arm{arm.upper()}.jsonl"
    s4_manifest_path = gen_dir / f"s4_image_manifest__arm{arm.upper()}.jsonl"
    if not s1_path.exists():
        raise FileNotFoundError(f"S1 file not found: {s1_path}")
    if not s4_manifest_path.exists():
        raise FileNotFoundError(f"S4 manifest file not found: {s4_manifest_path}")

    s1_records = dist.load_all_s1_records(s1_path)
    s1_by_id = {r.get("group_id", ""): r for r in s1_records if r.get("group_id")}
    image_mapping_all = dist.load_s4_image_manifest_all(s4_manifest_path, gen_dir)

    story: List[Any] = []

    # Cover: use distribution cover_base.jpg, overlay text only "SAMPLE"
    dist.add_cover_page_to_story(
        story,
        specialty_name="SAMPLE",
        page_width=page_width,
        page_height=page_height,
        font=korean_font,
    )

    # Group sections (distribution rendering: objectives → table → infographic)
    for g in selected_groups:
        gid = (g.get("group_id") or "").strip()
        s1 = s1_by_id.get(gid)
        if not s1:
            print(f"⚠️  Missing S1 record for group_id={gid}; skipping", file=sys.stderr)
            continue
        img_map = image_mapping_all.get(gid, {})
        dist.build_group_section(
            story=story,
            s1_record=s1,
            image_mapping=img_map,
            styles=styles,
            page_width=page_width,
            page_height=page_height,
            korean_font=korean_font,
            korean_font_bold=korean_font_bold,
            include_tables=True,
            include_infographics=True,
            include_objectives=True,
            base_dir=base_dir,
            add_section_breaks=True,
        )

    # Append Anki pages (no red SAMPLE watermark; keep distribution header/footer)
    _append_anki_section(
        story=story,
        cards=sample_cards,
        base_dir=base_dir,
        korean_font=korean_font,
        korean_font_bold=korean_font_bold,
        dist=dist,
    )

    doc.build(story)


def main():
    parser = argparse.ArgumentParser(description="Generate sample materials for KakaoTalk announcement")
    parser.add_argument("--base_dir", type=str, default=".", help="Base directory")
    parser.add_argument("--output_dir", type=str, default="6_Distributions/KakaoTalk_Samples", help="Output directory")
    parser.add_argument("--num_groups", type=int, default=3, help="Number of sample groups")
    parser.add_argument("--num_basic", type=int, default=6, help="Number of basic cards")
    parser.add_argument("--num_mcq", type=int, default=6, help="Number of MCQ cards")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--run_tag", type=str, default="FINAL_DISTRIBUTION", help="Run tag for distribution assets")
    parser.add_argument("--arm", type=str, default="G", help="Arm for distribution assets")
    parser.add_argument(
        "--s5_policy",
        type=str,
        default="perfect",
        choices=["perfect", "high", "random"],
        help="How to pick samples using S5 quality. perfect/high use S5.csv; random ignores S5.",
    )
    parser.add_argument(
        "--diagnostic_imaging_only",
        action="store_true",
        default=True,
        help="Restrict samples to groups/cards whose group_path includes 'diagnostic_imaging'.",
    )
    parser.add_argument(
        "--no_diagnostic_imaging_only",
        action="store_false",
        dest="diagnostic_imaging_only",
        help="Disable diagnostic_imaging-only restriction.",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    output_dir = base_dir / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*60)
    print("MeducAI KakaoTalk Sample Generator")
    print("="*60)
    print(f"Base directory: {base_dir}")
    print(f"Output directory: {output_dir}")
    print("="*60)
    
    # Load data
    groups_csv = base_dir / "6_Distributions" / "Final_QA" / "AppSheet_Export" / "Groups.csv"
    cards_csv = base_dir / "6_Distributions" / "Final_QA" / "AppSheet_Export" / "Cards.csv"
    s5_csv = base_dir / "6_Distributions" / "Final_QA" / "AppSheet_Export" / "S5.csv"
    
    print(f"\n>>> Loading groups from: {groups_csv}")
    groups = load_groups(groups_csv)
    print(f"   Loaded {len(groups)} groups")
    
    print(f"\n>>> Loading cards from: {cards_csv}")
    cards = load_cards(cards_csv)
    print(f"   Loaded {len(cards)} cards")

    print(f"\n>>> Loading S5 from: {s5_csv}")
    s5_rows = load_s5(s5_csv)
    print(f"   Loaded {len(s5_rows)} S5 rows")

    # Load distribution metadata to filter only renderable groups
    dist = _load_distribution_pdf_module(base_dir)
    gen_dir = dist.get_generated_dir(base_dir, args.run_tag)
    s1_path = gen_dir / f"stage1_struct__arm{args.arm.upper()}.jsonl"
    if not s1_path.exists():
        raise FileNotFoundError(f"S1 file not found: {s1_path}")
    s1_records = dist.load_all_s1_records(s1_path)
    allowed_group_ids = {r.get('group_id', '') for r in s1_records if r.get('group_id')}
    group_s5 = compute_group_s5_stats(s5_rows, run_tag=args.run_tag, arm=args.arm)
    s5_by_uid = { (r.get('card_uid') or '').strip(): r for r in s5_rows if (r.get('card_uid') or '').strip() }
    
    # Select sample groups
    print(f"\n>>> Selecting {args.num_groups} sample groups...")
    if args.s5_policy in ("perfect", "high"):
        selected_groups = select_sample_groups_by_s5(
            groups=groups,
            group_s5=group_s5,
            num_groups=args.num_groups,
            seed=args.seed,
            allowed_group_ids=allowed_group_ids,
            diagnostic_imaging_only=args.diagnostic_imaging_only,
            s5_policy=args.s5_policy,
        )
        if len(selected_groups) < args.num_groups:
            print(
                f"⚠️  Not enough groups matched s5_policy={args.s5_policy}. "
                f"Falling back to random selection for remaining slots.",
                file=sys.stderr,
            )
            fallback = select_sample_groups(groups, num_groups=args.num_groups, seed=args.seed)
            # fill without duplicates
            have = {g.get("group_id") for g in selected_groups}
            for g in fallback:
                if g.get("group_id") in have:
                    continue
                selected_groups.append(g)
                if len(selected_groups) >= args.num_groups:
                    break
    else:
        selected_groups = select_sample_groups(groups, num_groups=args.num_groups, seed=args.seed)
    
    for i, group in enumerate(selected_groups, 1):
        gid = (group.get("group_id") or "").strip()
        s = group_s5.get(gid) or {}
        s5_msg = ""
        if s:
            s5_msg = (
                f" | S5 pass={s.get('pass_rate', 0):.2f}"
                f" edu={s.get('avg_edu', 0):.2f}"
                f" tech={s.get('avg_tech', 0):.2f}"
                f" img={s.get('avg_img', 0):.2f}"
            )
        print(f"   {i}. {gid}: {group.get('group_path')} (entities: {group.get('entity_count')}){s5_msg}")
    
    # Select Anki cards
    if args.s5_policy in ("perfect", "high"):
        print(
            f"\n>>> Selecting Anki cards by S5 ({args.s5_policy}): "
            f"BASIC {args.num_basic}, MCQ {args.num_mcq}..."
        )
        sample_cards = select_sample_cards_by_s5(
            cards=cards,
            s5_by_card_uid=s5_by_uid,
            base_dir=base_dir,
            run_tag=args.run_tag,
            arm=args.arm,
            num_basic=args.num_basic,
            num_mcq=args.num_mcq,
            seed=args.seed,
            diagnostic_imaging_only=args.diagnostic_imaging_only,
            s5_policy=args.s5_policy,
        )
        if len(sample_cards.get("basic", [])) < args.num_basic or len(sample_cards.get("mcq", [])) < args.num_mcq:
            print(
                f"⚠️  Not enough cards matched s5_policy={args.s5_policy}. "
                f"Falling back to random selection for remaining cards.",
                file=sys.stderr,
            )
            fb = select_sample_cards(cards, num_basic=args.num_basic, num_mcq=args.num_mcq, seed=args.seed)
            # fill without duplicates
            have_b = {c.get("card_uid") for c in sample_cards.get("basic", [])}
            have_m = {c.get("card_uid") for c in sample_cards.get("mcq", [])}
            for c in fb.get("basic", []):
                if c.get("card_uid") in have_b:
                    continue
                sample_cards["basic"].append(c)
                if len(sample_cards["basic"]) >= args.num_basic:
                    break
            for c in fb.get("mcq", []):
                if c.get("card_uid") in have_m:
                    continue
                sample_cards["mcq"].append(c)
                if len(sample_cards["mcq"]) >= args.num_mcq:
                    break
    else:
        print(f"\n>>> Selecting Anki cards randomly: BASIC {args.num_basic}, MCQ {args.num_mcq}...")
        sample_cards = select_sample_cards(cards, num_basic=args.num_basic, num_mcq=args.num_mcq, seed=args.seed)
    print(f"   Selected {len(sample_cards['basic'])} basic cards")
    print(f"   Selected {len(sample_cards['mcq'])} MCQ cards")

    # Print chosen card details (helpful for documentation / reproducibility)
    def _print_cards(label: str, picked: List[Dict[str, Any]]) -> None:
        print(f"\n>>> {label} selected cards:")
        for i, c in enumerate(picked, 1):
            uid = (c.get("card_uid") or "").strip()
            s5 = s5_by_uid.get(uid, {})
            tech = _fnum(s5.get("s5_technical_accuracy"))
            edu = _fnum(s5.get("s5_educational_quality"))
            img = _fnum(s5.get("s5_card_image_quality"))
            dec = (s5.get("s5_decision") or "").strip().upper()
            front_1 = ((c.get("front") or "").strip().splitlines() or [""])[0]
            if len(front_1) > 80:
                front_1 = front_1[:80] + "…"
            print(
                f"   {i}. {c.get('entity_name')} | {c.get('group_path')} | {uid} "
                f"| S5(dec={dec}, edu={edu:.2f}, tech={tech:.2f}, img={img:.2f}) | {front_1}"
            )

    _print_cards("BASIC", sample_cards.get("basic", []))
    _print_cards("MCQ", sample_cards.get("mcq", []))
    
    print(f"\n>>> Generating distribution-style combined sample PDF...")
    combined_output_path = output_dir / "MeducAI_카톡공지_샘플자료.pdf"
    generate_sample_pdf(
        base_dir=base_dir,
        selected_groups=selected_groups,
        sample_cards=sample_cards,
        out_path=combined_output_path,
        run_tag=args.run_tag,
        arm=args.arm,
    )
    
    print("\n" + "="*60)
    print("✅ Sample generation complete!")
    print(f"   Output file: {combined_output_path.name}")
    print(f"   Output directory: {output_dir}")
    print("="*60)


if __name__ == "__main__":
    main()


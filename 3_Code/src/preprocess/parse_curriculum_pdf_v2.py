#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
V2 curriculum PDF parser (wrap-safe).

Goal:
- Extract objectives from `2_Data/raw/Radiology_Curriculum_v1.pdf` without losing items
  due to PDF line-wrapping (the known failure mode in v1 parsing).

Output schema (matches current raw table):
- Specialty
- Anatomy
- Modality/Type
- Category
- Objective
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


try:
    import pdfplumber  # type: ignore
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "Missing dependency: pdfplumber. Install it (e.g. `pip install pdfplumber`)."
    ) from e


_PATTERN_PART = re.compile(r"^([\d]+\.|[\ue424-\ue450])\s*(.*)")
_PATTERN_REGION = re.compile(r"^([가-하])\.\s*(.*)")
_PATTERN_SUB1 = re.compile(r"^(\d+)\)\s*(.*)")
_PATTERN_SUB2_KOR = re.compile(r"^([가-하])\)\s*(.*)")
_PATTERN_ITEM_ENG = re.compile(r"^([a-zA-Z])\)\s*(.*)")
_PATTERN_BULLET = re.compile(r"^[-•·]\s*(.*)")

# Difficulty marker at the end of an objective, allowing optional trailing punctuation.
_DIFFICULTY_SUFFIX_RE = re.compile(r"\s*[\(\[]\s*([ABCabcSs])\s*[\)\]]\s*[\.\:;,\-]?\s*$")

# Header/footer noise patterns
_PATTERN_HEADER_NOISE = re.compile(r".*구체적인 교육목표.*")
_PATTERN_DOTTED_LINE = re.compile(r"·{3,}")


def _join_wrapped(prev: str, nxt: str) -> str:
    prev = prev.rstrip()
    nxt = nxt.lstrip()
    if not prev:
        return nxt
    if not nxt:
        return prev
    # Join hyphenated words without a space.
    if prev.endswith("-"):
        return prev[:-1] + nxt
    return prev + " " + nxt


def _looks_like_new_structure(line: str) -> bool:
    return bool(
        _PATTERN_PART.match(line)
        or _PATTERN_REGION.match(line)
        or _PATTERN_SUB1.match(line)
        or _PATTERN_SUB2_KOR.match(line)
        or _PATTERN_ITEM_ENG.match(line)
        or _PATTERN_BULLET.match(line)
    )


def _is_noise(line: str, start_parsing: bool) -> bool:
    if not line:
        return True
    if "PAGE" in line or "Korean Society" in line or "대한영상의학회" in line:
        return True
    if _PATTERN_DOTTED_LINE.search(line):
        return True
    if line.isdigit():
        return True
    if start_parsing and _PATTERN_HEADER_NOISE.search(line):
        return True
    return False


@dataclasses.dataclass
class _State:
    part: Optional[str] = None
    region: Optional[str] = None
    sub1: Optional[str] = None
    sub2: Optional[str] = None
    item_header: Optional[str] = None


@dataclasses.dataclass
class _Buffer:
    active: bool = False
    text: str = ""
    # If True: we keep appending until difficulty marker appears.
    requires_difficulty_suffix: bool = True
    # Classification hint to allow re-interpretation if no difficulty suffix appears.
    # - "objective": buffer should become an objective row once closed.
    # - "maybe_category": a `가)` line that might be a category label OR a wrapped objective.
    # - "maybe_item_header": an `a)` line that might be a header for bullets OR a wrapped objective.
    kind: str = "objective"
    # Snapshot of state when buffer started (for stable assignment even if state updates mid-buffer).
    state: _State = dataclasses.field(default_factory=_State)
    start_page: int = 0
    start_line: str = ""


def _buffer_is_complete(buf: _Buffer) -> bool:
    if not buf.active:
        return False
    if not buf.requires_difficulty_suffix:
        return True
    return bool(_DIFFICULTY_SUFFIX_RE.search(buf.text.strip()))


def parse_pdf_to_rows(pdf_path: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Returns:
      - rows: list of row dicts for the output table
      - suspicious: list of suspicious buffered objectives that never closed
    """
    rows: List[Dict[str, Any]] = []
    suspicious: List[Dict[str, Any]] = []

    state = _State()
    buf = _Buffer()
    start_parsing = False

    def flush_buffer(reason: str) -> None:
        nonlocal buf, rows, suspicious
        if not buf.active:
            return
        txt = buf.text.strip()
        if not txt:
            buf = _Buffer()
            return
        # If we never saw a difficulty suffix and this buffer could be a category/header,
        # reinterpret it instead of recording as suspicious (this is the main wrap-loss fix).
        if buf.requires_difficulty_suffix and not _DIFFICULTY_SUFFIX_RE.search(txt):
            if buf.kind == "maybe_category":
                state.sub2 = txt
                state.item_header = None
                buf = _Buffer()
                return
            if buf.kind == "maybe_item_header":
                state.item_header = txt
                buf = _Buffer()
                return

        if buf.requires_difficulty_suffix and not _DIFFICULTY_SUFFIX_RE.search(txt):
            suspicious.append(
                {
                    "reason": reason,
                    "start_page": buf.start_page,
                    "start_line": buf.start_line,
                    "specialty": buf.state.part,
                    "anatomy": buf.state.region,
                    "modality_or_type": buf.state.sub1,
                    "category": buf.state.sub2,
                    "objective_buffer": txt,
                }
            )
            buf = _Buffer()
            return

        rows.append(
            {
                "Specialty": (buf.state.part or "").strip(),
                "Anatomy": (buf.state.region or "").strip(),
                "Modality/Type": (buf.state.sub1 or "").strip(),
                "Category": (buf.state.sub2 or ""),
                "Objective": txt,
            }
        )
        buf = _Buffer()

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_index, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            lines = [ln.strip() for ln in text.split("\n")]

            for raw_line in lines:
                line = raw_line.strip()
                if _is_noise(line, start_parsing):
                    continue

                if not start_parsing:
                    # Start marker: "구체적인 교육목표" + roman numeral IV (or similar)
                    if "구체적인 교육목표" in line and ("IV" in line or "Ⅳ" in line or "4" in line):
                        start_parsing = True
                    continue

                # If we have an active buffer and see a new structural marker, flush buffer first.
                if buf.active and _looks_like_new_structure(line):
                    flush_buffer(reason="new_structure_encountered")

                # 1) Part
                m = _PATTERN_PART.match(line)
                if m:
                    state.part = m.group(2).strip()
                    state.region = None
                    state.sub1 = None
                    state.sub2 = None
                    state.item_header = None
                    continue

                # 2) Region
                m = _PATTERN_REGION.match(line)
                if m:
                    state.region = m.group(2).strip()
                    state.sub1 = None
                    state.sub2 = None
                    state.item_header = None
                    continue

                # 3) Subcategory 1
                m = _PATTERN_SUB1.match(line)
                if m:
                    state.sub1 = m.group(2).strip()
                    state.sub2 = None
                    state.item_header = None
                    continue

                # 4) Subcategory 2 (Korean, e.g. 가) 라) ...)
                m = _PATTERN_SUB2_KOR.match(line)
                if m:
                    content = m.group(2).strip()
                    # v2 improvement:
                    # `가)` lines can be either category labels OR wrapped objectives where (A/B/S) appears later.
                    buf = _Buffer(
                        active=True,
                        text=content,
                        requires_difficulty_suffix=True,
                        kind="objective" if _DIFFICULTY_SUFFIX_RE.search(content) else "maybe_category",
                        state=dataclasses.replace(state),
                        start_page=page_index + 1,
                        start_line=line,
                    )
                    if _DIFFICULTY_SUFFIX_RE.search(content):
                        # Objective that directly sits under sub2 marker without a category label.
                        buf.state.sub2 = state.sub2
                        flush_buffer(reason="sub2_direct_objective")
                    continue

                # 5) English item header (a) b) ...)
                m = _PATTERN_ITEM_ENG.match(line)
                if m:
                    content = m.group(2).strip()
                    # v2 improvement:
                    # `a)` lines are often wrapped objectives where (A/B/S) appears later.
                    buf = _Buffer(
                        active=True,
                        text=content,
                        requires_difficulty_suffix=True,
                        kind="objective" if _DIFFICULTY_SUFFIX_RE.search(content) else "maybe_item_header",
                        state=dataclasses.replace(state),
                        start_page=page_index + 1,
                        start_line=line,
                    )
                    if _DIFFICULTY_SUFFIX_RE.search(content):
                        flush_buffer(reason="eng_direct_objective")
                    continue

                # 6) Bullet points
                m = _PATTERN_BULLET.match(line)
                if m:
                    item = m.group(1).strip()
                    # If we had a pending `a)` header buffered, reinterpret it now.
                    if (
                        buf.active
                        and buf.kind == "maybe_item_header"
                        and buf.requires_difficulty_suffix
                        and not _DIFFICULTY_SUFFIX_RE.search(buf.text.strip())
                    ):
                        state.item_header = buf.text.strip()
                        buf = _Buffer()
                    final_object = item
                    if state.item_header:
                        final_object = f"{state.item_header} - {item}"
                    # Bullets often don't carry (A/B/S); store as-is.
                    buf = _Buffer(
                        active=True,
                        text=final_object,
                        requires_difficulty_suffix=False,
                        kind="objective",
                        state=dataclasses.replace(state),
                        start_page=page_index + 1,
                        start_line=line,
                    )
                    flush_buffer(reason="bullet")
                    continue

                # 7) Continuation text
                if buf.active:
                    buf.text = _join_wrapped(buf.text, line)
                    if _buffer_is_complete(buf):
                        flush_buffer(reason="difficulty_suffix_closed")
                    continue

                # 8) Loose short text that may be category label
                if (not _DIFFICULTY_SUFFIX_RE.search(line)) and len(line) < 40 and not line.endswith("."):
                    if re.search(r"\d+$", line):  # avoid page-number residue
                        continue
                    state.sub2 = line
                    state.item_header = None
                    continue

                # Otherwise: ignore unknown line (but could be future extension)

    # end of pdf
    if buf.active:
        flush_buffer(reason="eof")

    return rows, suspicious


def rows_to_df(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    # Enforce stable column order
    df = df.reindex(columns=["Specialty", "Anatomy", "Modality/Type", "Category", "Objective"])
    # Normalize NaNs to empty strings for consistency with legacy outputs
    for c in ["Specialty", "Anatomy", "Modality/Type", "Category", "Objective"]:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str)
    return df


def write_audit_md(df: pd.DataFrame, suspicious: List[Dict[str, Any]], out_md: Path) -> None:
    counts = {
        "rows_total": int(len(df)),
        "unique_objectives": int(df["Objective"].nunique(dropna=True)),
        "suspicious_unclosed_objectives": int(len(suspicious)),
    }

    lines: List[str] = []
    lines.append("# Curriculum Parse Audit (v2)")
    lines.append("")
    lines.append(f"- Generated at: `{dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')}`")
    lines.append(f"- Rows: **{counts['rows_total']}**")
    lines.append(f"- Unique objectives: **{counts['unique_objectives']}**")
    lines.append(f"- Suspicious (unclosed buffered objectives): **{counts['suspicious_unclosed_objectives']}**")
    lines.append("")

    def _counts_table(cols: List[str], head: int = 50) -> List[str]:
        sub = df.copy()
        for c in cols:
            sub[c] = sub[c].fillna("").astype(str).str.strip()
        grp = (
            sub.groupby(cols, dropna=False)
            .size()
            .reset_index()
            .rename(columns={0: "rows"})
            .sort_values("rows", ascending=False)
        )
        out: List[str] = []
        out.append("| " + " | ".join(cols + ["rows"]) + " |")
        out.append("|" + "|".join(["---"] * (len(cols) + 1)) + "|")
        for _, r in grp.head(head).iterrows():
            out.append("| " + " | ".join([str(r[c]) or "" for c in cols] + [str(int(r["rows"]))]) + " |")
        if len(grp) > head:
            out.append(f"\n... and {len(grp) - head} more")
        return out

    lines.append("## Distribution (top groups)")
    lines.append("")
    lines.append("### By Specialty")
    lines.append("")
    lines.extend(_counts_table(["Specialty"], head=30))
    lines.append("")
    lines.append("### By Specialty × Anatomy")
    lines.append("")
    lines.extend(_counts_table(["Specialty", "Anatomy"], head=60))
    lines.append("")
    lines.append("### By Specialty × Anatomy × Modality/Type")
    lines.append("")
    lines.extend(_counts_table(["Specialty", "Anatomy", "Modality/Type"], head=80))
    lines.append("")
    lines.append("### By Specialty × Anatomy × Modality/Type × Category")
    lines.append("")
    lines.extend(_counts_table(["Specialty", "Anatomy", "Modality/Type", "Category"], head=120))
    lines.append("")

    if suspicious:
        lines.append("## Suspicious buffered objectives (needs review)")
        lines.append("")
        for s in suspicious[:200]:
            loc = f"p{s.get('start_page')} :: {s.get('start_line')}"
            lines.append(f"- {loc}")
            lines.append(f"  - specialty: `{s.get('specialty','')}`")
            lines.append(f"  - anatomy: `{s.get('anatomy','')}`")
            lines.append(f"  - modality_or_type: `{s.get('modality_or_type','')}`")
            lines.append(f"  - category: `{s.get('category','')}`")
            lines.append(f"  - buffer: {s.get('objective_buffer','')}")
        if len(suspicious) > 200:
            lines.append(f"- ... and {len(suspicious) - 200} more")
        lines.append("")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Parse curriculum PDF into raw XLSX (v2, wrap-safe).")
    ap.add_argument("--pdf", required=True, help="Input curriculum PDF")
    ap.add_argument("--out_xlsx", required=True, help="Output XLSX path")
    ap.add_argument("--out_audit_md", required=False, default=None, help="Optional audit markdown output path")
    ap.add_argument("--out_suspicious_json", required=False, default=None, help="Optional suspicious buffer JSON output path")
    args = ap.parse_args()

    pdf_path = Path(args.pdf).resolve()
    out_xlsx = Path(args.out_xlsx).resolve()

    rows, suspicious = parse_pdf_to_rows(pdf_path)
    df = rows_to_df(rows)

    out_xlsx.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(out_xlsx, index=False, engine="openpyxl")

    if args.out_audit_md:
        write_audit_md(df, suspicious, Path(args.out_audit_md).resolve())

    if args.out_suspicious_json:
        out_p = Path(args.out_suspicious_json).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(suspicious, ensure_ascii=False, indent=2), encoding="utf-8")

    print("OK")
    print(f"- pdf: {pdf_path}")
    print(f"- out_xlsx: {out_xlsx}")
    print(f"- rows: {len(df)}")
    print(f"- suspicious: {len(suspicious)}")


if __name__ == "__main__":
    main()



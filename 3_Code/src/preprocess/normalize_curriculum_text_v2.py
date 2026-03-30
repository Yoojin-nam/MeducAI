#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Normalize curriculum text without LLM calls (v2).

Primary goal:
- Fix common PDF extraction artifacts such as split English tokens:
  - "R enal" -> "Renal"
  - "A cute" -> "Acute"
  - "S pin-echo" -> "Spin-echo"
  - "C T" -> "CT", "M R" -> "MR"

This is intended to run BEFORE translation to improve Objective_EN quality.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable, List

import pandas as pd


_SOFT_HYPHEN = "\u00ad"

# Merge patterns
_RE_SPLIT_ALPHA = re.compile(r"\b([A-Za-z])\s+([a-z])")  # R enal -> Renal
_RE_SPLIT_UPPER_SEQ = re.compile(r"\b((?:[A-Z]\s+){1,3}[A-Z])\b")  # C T -> CT, M R -> MR
_RE_WS = re.compile(r"\s+")


def normalize_text(s: str) -> str:
    t = str(s or "")
    if not t:
        return ""
    t = t.replace(_SOFT_HYPHEN, "")
    # Normalize whitespace early
    t = t.replace("\r", " ").replace("\n", " ")
    t = _RE_WS.sub(" ", t).strip()

    # Merge split English tokens (iterate a few times until stable)
    for _ in range(5):
        new = _RE_SPLIT_ALPHA.sub(r"\1\2", t)
        if new == t:
            break
        t = new

    # Merge split all-caps sequences like "C T", "M R", "U S"
    def _merge_upper(m: re.Match) -> str:
        return m.group(1).replace(" ", "")

    t = _RE_SPLIT_UPPER_SEQ.sub(_merge_upper, t)
    t = _RE_WS.sub(" ", t).strip()
    return t


def normalize_df(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c not in out.columns:
            continue
        out[c] = out[c].fillna("").astype(str).map(normalize_text)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Normalize curriculum text columns (v2) without LLM.")
    ap.add_argument("--in_xlsx", required=True)
    ap.add_argument("--out_xlsx", required=True)
    ap.add_argument(
        "--cols",
        default="Objective",
        help="Comma-separated columns to normalize (default: Objective).",
    )
    args = ap.parse_args()

    in_path = Path(args.in_xlsx).resolve()
    out_path = Path(args.out_xlsx).resolve()
    cols: List[str] = [c.strip() for c in str(args.cols).split(",") if c.strip()]

    df = pd.read_excel(in_path).reset_index(drop=True)
    df2 = normalize_df(df, cols)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df2.to_excel(out_path, index=False, engine="openpyxl")
    print(f"OK: normalized {len(cols)} cols -> {out_path} rows={len(df2)}")


if __name__ == "__main__":
    main()



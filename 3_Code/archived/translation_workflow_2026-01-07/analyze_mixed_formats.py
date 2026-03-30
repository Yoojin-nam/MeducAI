#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze mixed-format leftovers in translated Anki fields.

Focus metrics:
- KR(EN): 한글(English)
- EN(KR): English(한글)

Usage:
  python3 3_Code/src/tools/anki/analyze_mixed_formats.py --input path/to/file.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


PAT_KR_EN = re.compile(r"([가-힣][가-힣\s\-/]+?)\s*\(([A-Za-z][A-Za-z0-9\s\-./]+)\)")
PAT_EN_KR = re.compile(r"([A-Za-z][A-Za-z0-9\s\-./]+)\s*\(([가-힣][가-힣\s\-/]+?)\)")


def _normalize_ws(s: str) -> str:
    return " ".join(s.split())


def analyze(path: Path) -> dict:
    kr_en = Counter()
    en_kr = Counter()
    total_records = 0
    total_cards = 0

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            total_records += 1
            r = json.loads(line)
            for card in r.get("anki_cards", []):
                total_cards += 1
                for field in ("front", "back"):
                    t = card.get(field, "") or ""
                    for k, e in PAT_KR_EN.findall(t):
                        kr_en[f"{_normalize_ws(k)}({_normalize_ws(e)})"] += 1
                    for e, k in PAT_EN_KR.findall(t):
                        en_kr[f"{_normalize_ws(e)}({_normalize_ws(k)})"] += 1

    return {
        "path": str(path),
        "records": total_records,
        "cards": total_cards,
        "kr_en_total": sum(kr_en.values()),
        "en_kr_total": sum(en_kr.values()),
        "kr_en_top20": kr_en.most_common(20),
        "en_kr_top20": en_kr.most_common(20),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    args = ap.parse_args()

    res = analyze(args.input)
    print(f"File: {res['path']}")
    print(f"Records: {res['records']}, Cards: {res['cards']}")
    print(f"KR(EN) total: {res['kr_en_total']}")
    print(f"EN(KR) total: {res['en_kr_total']}")
    print("\nTop KR(EN):")
    for term, cnt in res["kr_en_top20"]:
        print(f"  {term}: {cnt}")
    print("\nTop EN(KR):")
    for term, cnt in res["en_kr_top20"]:
        print(f"  {term}: {cnt}")


if __name__ == "__main__":
    main()



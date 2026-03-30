#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Objective bullets formatter (MeducAI S1)

Deterministically converts:
- objective_list: JSON array string (from CSV cell)
to:
- objective_bullets: Markdown bullet list (for S1 prompt)

Design goals:
- deterministic
- stable across environments
- safe normalization (strip only trailing difficulty markers)
"""

from __future__ import annotations

import argparse
import json
import re
from typing import List


_DIFFICULTY_TAIL_RE = re.compile(r"\s*\(([ABC])\)\.?\s*$")


def normalize_objective(text: str, *, strip_difficulty: bool = True) -> str:
    s = (text or "").strip()
    if strip_difficulty:
        s = _DIFFICULTY_TAIL_RE.sub("", s).strip()
    # Defensive: collapse internal whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def objective_list_to_bullets(objective_list_json: str, *, strip_difficulty: bool = True) -> str:
    """Convert JSON array string -> markdown bullets."""
    if objective_list_json is None:
        raise ValueError("objective_list_json is None")

    try:
        arr = json.loads(objective_list_json)
    except Exception as e:
        raise ValueError(f"objective_list is not valid JSON: {e}") from e

    if not isinstance(arr, list) or not arr:
        raise ValueError("objective_list must be a non-empty JSON array")

    bullets: List[str] = []
    for item in arr:
        if not isinstance(item, str):
            raise ValueError("objective_list must be an array of strings")
        norm = normalize_objective(item, strip_difficulty=strip_difficulty)
        if not norm:
            raise ValueError("objective_list contains an empty objective after normalization")
        bullets.append(f"- {norm}")

    return "\n".join(bullets)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--objective_list", required=True, help="JSON array string from CSV cell")
    ap.add_argument("--keep_difficulty", action="store_true", help="Do not strip trailing (A)/(B)/(C)")
    args = ap.parse_args()

    strip = not args.keep_difficulty
    print(objective_list_to_bullets(args.objective_list, strip_difficulty=strip))


if __name__ == "__main__":
    main()

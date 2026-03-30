#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix translation_map_v2.json by translating missing Korean terms.

This script:
1. Loads missing terms from missing_translation_terms.json
2. Translates them using Gemini
3. Updates translation_map_v2.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from gemini_utils import GeminiClient, GeminiConfig  # noqa: E402

SYSTEM_PROMPT_TRANSLATION = """
You are an expert medical translator specializing in Radiology.

Your task:
You will receive a JSON array of Korean medical curriculum terms (strings).

Return a SINGLE valid JSON ARRAY where each element is an object with EXACTLY:
- "kr": original Korean term (string)
- "label": a human-readable English phrase (string)
- "tag": a short, machine-friendly identifier (string)

Requirements for "label":
- Professional radiology English.
- Use normal spaces, not underscores.
- Use sentence or title case.
- Keep the phrase concise but clinically accurate.

Requirements for "tag":
- Use only: lowercase letters, numbers, and underscores.
- Prefer short tags.
- Use common abbreviations where obvious.
- Remove articles and conjunctions.

Ambiguity handling:
- If a term is ambiguous or you are not confident, set:
  - "label": "REVIEW_NEEDED"
  - "tag": "review_needed"

Output format:
- Return a SINGLE valid JSON array.
- Do NOT wrap the JSON in markdown code blocks.
""".strip()


def _batch_terms(items: List[str], batch_size: int) -> List[List[str]]:
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def main() -> None:
    ap = argparse.ArgumentParser(description="Fix translation_map_v2.json with missing terms.")
    ap.add_argument("--missing_json", default="2_Data/metadata/missing_translation_terms.json")
    ap.add_argument("--translation_map", default="2_Data/metadata/translation_map_v2.json")
    ap.add_argument("--model", default="gemini-3-flash-preview")
    ap.add_argument("--batch_size", type=int, default=40)
    args = ap.parse_args()

    # Load missing terms
    missing_path = Path(args.missing_json)
    if not missing_path.exists():
        raise FileNotFoundError(f"Missing terms file not found: {missing_path}")
    
    with open(missing_path, "r", encoding="utf-8") as f:
        missing_data = json.load(f)
    
    all_missing = missing_data.get("all_missing", [])
    print(f"[fix_translation_map] Found {len(all_missing)} missing terms", flush=True)

    # Load existing translation map
    map_path = Path(args.translation_map)
    if map_path.exists():
        with open(map_path, "r", encoding="utf-8") as f:
            translation_map = json.load(f)
    else:
        translation_map = {}
    
    print(f"[fix_translation_map] Existing map has {len(translation_map)} entries", flush=True)

    # Initialize Gemini client
    client = GeminiClient(GeminiConfig(model=args.model, temperature=0.0, top_p=1.0, top_k=1))

    # Translate missing terms in batches
    term_batches = _batch_terms(all_missing, batch_size=args.batch_size)
    total_batches = len(term_batches)
    
    for bi, terms in enumerate(term_batches, start=1):
        print(f"[fix_translation_map] batch {bi}/{total_batches} (terms {len(terms)})", flush=True)
        
        try:
            arr, meta = client.generate_json_with_meta(
                json.dumps(terms, ensure_ascii=False), SYSTEM_PROMPT_TRANSLATION
            )
            
            # Handle both list and dict responses
            if isinstance(arr, dict):
                # Single object: {"i": 123, "en_b64": "..."} or {"kr": "...", "label": "...", "tag": "..."}
                if "kr" in arr and "label" in arr and "tag" in arr:
                    arr = [arr]
                else:
                    # Try to convert dict to list
                    arr = [v for v in arr.values() if isinstance(v, dict) and "kr" in v]
            
            if not isinstance(arr, list):
                print(f"  WARNING: Unexpected response type {type(arr)}, skipping batch", flush=True)
                continue
            
            # Add to translation map
            added = 0
            for it in arr:
                if not isinstance(it, dict):
                    continue
                kr = str(it.get("kr") or "").strip()
                if not kr:
                    continue
                translation_map[kr] = {
                    "label": it.get("label"),
                    "tag": it.get("tag")
                }
                added += 1
            
            print(f"  Added {added}/{len(terms)} terms to map", flush=True)
            
        except Exception as e:
            print(f"  ERROR in batch {bi}: {e}", flush=True)
            continue

    # Save updated translation map
    map_path.parent.mkdir(parents=True, exist_ok=True)
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(translation_map, f, indent=2, ensure_ascii=False)
    
    print(f"\nOK: Updated {map_path} with {len(translation_map)} total entries", flush=True)


if __name__ == "__main__":
    main()


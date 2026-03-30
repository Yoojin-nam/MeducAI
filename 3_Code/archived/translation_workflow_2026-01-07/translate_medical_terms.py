#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Translate Korean medical terms to English in Anki cards.

This script:
1. Loads Anki cards from S2 JSONL files
2. Identifies Korean medical terms in front/back/options fields
3. Translates only medical terms to English (preserves sentence structure)
4. Outputs translated JSONL files

Usage:
    python translate_medical_terms.py \
        --input 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG.jsonl \
        --output 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__translated.jsonl \
        --model gemini-3-flash-preview
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
_THIS_DIR = Path(__file__).resolve().parent
# Path: .../MeducAI/3_Code/src/tools/anki -> need 4 parents to get to MeducAI/
_PROJECT_ROOT = _THIS_DIR.parent.parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"

print(f"[DEBUG] Project root: {_PROJECT_ROOT}")
print(f"[DEBUG] .env file path: {_ENV_FILE}")
print(f"[DEBUG] .env exists: {_ENV_FILE.exists()}")

if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE, override=False)
    print(f"[DEBUG] .env loaded successfully")
    
    # Check if API key is available
    import os
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("RAB_LLM_API_KEY")
    if key:
        print(f"[DEBUG] API Key found: {key[:20]}...")
    else:
        print("[DEBUG] WARNING: No API key found in environment")
else:
    print("[DEBUG] WARNING: .env file not found")

if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from translate_medical_terms_module import (  # noqa: E402
    MedicalTermTranslator,
    translate_s2_jsonl_file,
)


def main():
    parser = argparse.ArgumentParser(
        description='Translate Korean medical terms to English in Anki cards'
    )
    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help='Input S2 JSONL file path'
    )
    parser.add_argument(
        '--output',
        type=Path,
        required=True,
        help='Output JSONL file path'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='gemini-3-flash-preview',
        help='Gemini model name (default: gemini-3-flash-preview)'
    )
    parser.add_argument(
        '--batch_size',
        type=int,
        default=10,
        help='Print progress every N records (default: 10)'
    )
    parser.add_argument(
        '--max_records',
        type=int,
        default=None,
        help='Maximum number of records to process (for testing)'
    )
    parser.add_argument(
        '--max_workers',
        type=int,
        default=10,
        help='Number of parallel workers (default: 10)'
    )
    parser.add_argument(
        '--no_resume',
        action='store_true',
        help='Disable resume mode and re-translate even if output already exists'
    )
    
    args = parser.parse_args()
    
    if not args.input.exists():
        print(f"❌ Error: Input file not found: {args.input}", file=sys.stderr)
        return 1
    
    # Initialize translator
    try:
        translator = MedicalTermTranslator(
            model=args.model,
            use_rotator=True,  # Explicitly enable API key rotation
            base_dir=_PROJECT_ROOT,
        )
    except Exception as e:
        print(f"❌ Error: Failed to initialize translator: {e}", file=sys.stderr)
        return 1
    
    # Process file
    try:
        translate_s2_jsonl_file(
            input_path=args.input,
            output_path=args.output,
            translator=translator,
            batch_size=args.batch_size,
            max_records=args.max_records,
            max_workers=args.max_workers,
            verbose=True,
            resume=(not args.no_resume),
        )
        return 0
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())


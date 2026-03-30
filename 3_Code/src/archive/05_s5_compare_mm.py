#!/usr/bin/env python3
"""
MeducAI S5 Compare (Multimodal) - Thin Wrapper

This is a thin wrapper around tools/s5/s5_compare_mm.py for consistency
with other 05_*.py scripts in the src/ directory.

Usage:
    python3 3_Code/src/05_s5_compare_mm.py \
      --base_dir . \
      --arm G \
      --before_run_tag RUN_TAG_REP1 \
      --before_run_tag RUN_TAG_REP2 \
      --after_run_tag RUN_TAG_REP1 \
      --after_run_tag RUN_TAG_REP2

    # Alternative: using plural aliases (also supported)
    python3 3_Code/src/05_s5_compare_mm.py \
      --base_dir . \
      --arm G \
      --before_run_tags RUN_TAG_REP1 RUN_TAG_REP2 \
      --after_run_tags RUN_TAG_REP1 RUN_TAG_REP2

See tools/s5/s5_compare_mm.py for full documentation.
"""

import sys
from pathlib import Path

# Add src directory to path so we can import from tools
_THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_THIS_DIR))

# Import and run the main function
if __name__ == "__main__":
    try:
        from tools.s5.s5_compare_mm import main
        main()
    except ImportError as e:
        print(f"Error: Could not import s5_compare_mm: {e}", file=sys.stderr)
        print(f"Expected module at: {_THIS_DIR / 'tools' / 's5' / 's5_compare_mm.py'}", file=sys.stderr)
        sys.exit(1)


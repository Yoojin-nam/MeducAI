#!/usr/bin/env python3
"""
MeducAI S5R Expansion Criteria Evaluator - Thin Wrapper

This is a thin wrapper around tools/s5/s5_evaluate_expansion_criteria.py for consistency
with other 05_*.py scripts in the src/ directory.

Usage:
    python3 3_Code/src/05_evaluate_expansion_criteria.py \
      --base_dir . \
      --compare_dir 2_Data/metadata/generated/COMPARE__<before>__VS__<after>

See tools/s5/s5_evaluate_expansion_criteria.py for full documentation.
"""

import sys
from pathlib import Path

# Add src directory to path so we can import from tools
_THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_THIS_DIR))

# Import and run the main function
if __name__ == "__main__":
    try:
        from tools.s5.s5_evaluate_expansion_criteria import main
        main()
    except ImportError as e:
        print(f"Error: Could not import s5_evaluate_expansion_criteria: {e}", file=sys.stderr)
        print(f"Expected module at: {_THIS_DIR / 'tools' / 's5' / 's5_evaluate_expansion_criteria.py'}", file=sys.stderr)
        sys.exit(1)


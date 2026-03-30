#!/usr/bin/env python3
"""
Show current API key information.

Usage:
    python3 3_Code/Scripts/show_current_api_key.py
    # or as one-liner:
    python3 -c "import sys; sys.path.insert(0, '3_Code/src'); from tools.api_key_rotator import ApiKeyRotator; from pathlib import Path; r = ApiKeyRotator(base_dir=Path('.')); idx = r._current_index; print(f'현재 키: {r.key_prefix}_{r.key_numbers[idx]} (인덱스 {idx})')"
"""

import sys
from pathlib import Path

# Add src to path
base_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(base_dir / "3_Code" / "src"))

try:
    from tools.api_key_rotator import ApiKeyRotator
    
    rotator = ApiKeyRotator(base_dir=base_dir, key_prefix="GOOGLE_API_KEY")
    current_idx = rotator._current_index
    current_key_number = rotator.key_numbers[current_idx]
    
    print(f"현재 키: GOOGLE_API_KEY_{current_key_number} (인덱스 {current_idx})")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


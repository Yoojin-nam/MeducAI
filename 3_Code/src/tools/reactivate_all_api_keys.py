#!/usr/bin/env python3
"""
Reactivate all API keys in .api_key_status.json

This script resets all keys to active status, useful when:
- All keys were marked inactive but you want to retry
- Keys need to be manually reactivated
- Testing key rotation behavior

Usage:
    python3 3_Code/Scripts/reactivate_all_api_keys.py
"""

import json
from pathlib import Path
from datetime import datetime


def reactivate_all_keys(base_dir: Path = None):
    """Reactivate all API keys in the status file."""
    if base_dir is None:
        base_dir = Path.cwd()
        # Try to find repo root
        for parent in base_dir.parents:
            if (parent / "3_Code" / "src").exists():
                base_dir = parent
                break
    
    status_file = base_dir / "2_Data" / "metadata" / ".api_key_status.json"
    
    if not status_file.exists():
        print(f"Status file not found: {status_file}")
        print("Nothing to reactivate.")
        return
    
    # Load current state
    with open(status_file, 'r', encoding='utf-8') as f:
        state = json.load(f)
    
    # Count current status
    keys_state = state.get('keys', {})
    inactive_before = sum(1 for k, v in keys_state.items() if not v.get('is_active', True))
    
    if inactive_before == 0:
        print("All keys are already active. Nothing to do.")
        return
    
    # Reactivate all keys
    today = datetime.now().date().isoformat()
    reactivated_count = 0
    
    for key_id, key_state in keys_state.items():
        if not key_state.get('is_active', True):
            key_state['is_active'] = True
            key_state['failure_count'] = 0
            key_state['consecutive_failures'] = 0
            key_state['last_reset_date'] = today
            reactivated_count += 1
    
    # Update last_updated timestamp
    state['last_updated'] = datetime.now().isoformat()
    
    # Save state
    status_file.parent.mkdir(parents=True, exist_ok=True)
    with open(status_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    
    # Get current key info using ApiKeyRotator for accurate key number
    try:
        import sys
        sys.path.insert(0, str(base_dir / "3_Code" / "src"))
        from tools.api_key_rotator import ApiKeyRotator
        rotator = ApiKeyRotator(base_dir=base_dir, key_prefix="GOOGLE_API_KEY")
        current_idx = state.get('current_key_index', 0)
        current_key_number = rotator.key_numbers[current_idx] if current_idx < len(rotator.key_numbers) else current_idx + 1
        current_key_id = f"GOOGLE_API_KEY_{current_key_number}"
    except Exception:
        # Fallback if ApiKeyRotator not available
        current_idx = state.get('current_key_index', 0)
        current_key_id = f"GOOGLE_API_KEY_{current_idx + 1}"
    
    print("=" * 60)
    print("API Key Reactivation")
    print("=" * 60)
    print(f"Status file: {status_file}")
    print(f"Current key: {current_key_id} (인덱스 {current_idx})")
    print(f"Reactivated keys: {reactivated_count}")
    print(f"All keys are now active.")
    print("=" * 60)


if __name__ == "__main__":
    reactivate_all_keys()


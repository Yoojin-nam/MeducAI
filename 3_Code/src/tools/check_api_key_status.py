#!/usr/bin/env python3
"""
Check API key rotation status
"""
import json
from pathlib import Path

def check_api_key_status(base_dir="."):
    """Check API key rotation status."""
    base_path = Path(base_dir)
    state_file = base_path / "2_Data" / "metadata" / ".api_key_status.json"
    
    if not state_file.exists():
        print("❌ API key status file not found. No rotation has occurred yet.")
        return
    
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
        
        print("=" * 80)
        print("API Key Rotation Status")
        print("=" * 80)
        print()
        
        current_idx = state.get("current_key_index", 0)
        keys = state.get("keys", {})
        
        print(f"Current Key Index: {current_idx + 1} (1-based)")
        print()
        print("Key Status:")
        print("-" * 80)
        
        for key_id, key_state in sorted(keys.items()):
            is_active = key_state.get("is_active", True)
            daily_requests = key_state.get("daily_requests", 0)
            failure_count = key_state.get("failure_count", 0)
            last_failure = key_state.get("last_failure_time")
            is_current = (key_id == f"GOOGLE_API_KEY_{current_idx + 1}")
            
            status = "✅ ACTIVE" if is_active else "❌ EXHAUSTED"
            current_marker = " (CURRENT)" if is_current else ""
            
            print(f"{key_id}: {status}{current_marker}")
            print(f"  Daily Requests: {daily_requests}")
            print(f"  Failure Count: {failure_count}")
            if last_failure:
                print(f"  Last Failure: {last_failure}")
            print()
        
        # Check if all keys are exhausted
        active_keys = [k for k, v in keys.items() if v.get("is_active", True)]
        if not active_keys:
            print("⚠️  WARNING: All API keys are exhausted!")
            print("   You need to:")
            print("   1. Wait for quota reset (typically 24 hours)")
            print("   2. Add more API keys to .env (GOOGLE_API_KEY_1, GOOGLE_API_KEY_2, ...)")
            print("   3. Or use --resume-failed to retry later")
        else:
            print(f"✅ {len(active_keys)} key(s) still active")
        
    except Exception as e:
        print(f"❌ Error reading status file: {e}")

if __name__ == "__main__":
    check_api_key_status()


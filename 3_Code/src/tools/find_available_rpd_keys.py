#!/usr/bin/env python3
"""
Find API keys with available RPD quota
"""
import json
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

def find_available_rpd_keys(base_dir="."):
    """Find API keys with available RPD quota."""
    base_path = Path(base_dir)
    
    # Load .env
    env_path = base_path / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    
    # Count available keys
    key_count = 0
    for i in range(1, 100):
        key_name = f"GOOGLE_API_KEY_{i}"
        key_value = os.getenv(key_name, "").strip()
        if key_value:
            key_count = i
        else:
            break
    
    print("=" * 80)
    print("API Key RPD Status Check")
    print("=" * 80)
    print()
    print(f"Total Keys Available: {key_count}")
    print()
    
    # Check key status
    state_file = base_path / "2_Data" / "metadata" / ".api_key_status.json"
    if not state_file.exists():
        print("ℹ️  No key status file found. All keys should be available.")
        print(f"   You can use any key from 1 to {key_count}")
        return
    
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
        
        current_idx = state.get("current_key_index", 0)
        keys = state.get("keys", {})
        
        print(f"Current Key Index: {current_idx + 1} (1-based)")
        print()
        print("Key RPD Status:")
        print("-" * 80)
        
        available_keys = []
        exhausted_keys = []
        
        for i in range(1, key_count + 1):
            key_id = f"GOOGLE_API_KEY_{i}"
            key_state = keys.get(key_id, {})
            daily_requests = key_state.get("daily_requests", 0)
            is_active = key_state.get("is_active", True)
            last_reset = key_state.get("last_reset_date", datetime.now().date().isoformat())
            is_current = (i == current_idx + 1)
            
            # Check if RPD is exhausted (assuming limit is 250)
            # Note: Actual limit may vary, but 250 is common for Gemini
            rpd_limit = 250  # Common limit for Gemini API
            rpd_remaining = max(0, rpd_limit - daily_requests)
            
            status = "✅ AVAILABLE" if (is_active and rpd_remaining > 0) else "❌ EXHAUSTED"
            current_marker = " (CURRENT)" if is_current else ""
            
            print(f"{key_id}: {status}{current_marker}")
            print(f"  Daily Requests: {daily_requests}/{rpd_limit} (Remaining: {rpd_remaining})")
            print(f"  Active: {is_active}")
            print(f"  Last Reset: {last_reset}")
            print()
            
            if is_active and rpd_remaining > 0:
                available_keys.append(i)
            else:
                exhausted_keys.append(i)
        
        print("=" * 80)
        print("Summary")
        print("=" * 80)
        print()
        
        if available_keys:
            print(f"✅ Available Keys (RPD remaining): {available_keys}")
            print(f"   Recommended START_INDEX: {available_keys[0]}")
        else:
            print("❌ All keys are exhausted!")
            print("   Options:")
            print("   1. Wait for RPD reset (typically at midnight UTC)")
            print("   2. Check if RPD limit is actually 250 (may be different)")
            print("   3. Add more API keys to .env")
        
        if exhausted_keys:
            print(f"❌ Exhausted Keys: {exhausted_keys}")
        
        print()
        print("To use an available key, set in .env:")
        if available_keys:
            print(f"   API_KEY_ROTATOR_START_INDEX={available_keys[0]}")
        else:
            print("   (No available keys - wait for reset or add more keys)")
        
    except Exception as e:
        print(f"❌ Error reading status file: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    find_available_rpd_keys()


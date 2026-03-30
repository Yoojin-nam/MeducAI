#!/usr/bin/env python3
"""
Check if START_INDEX=4 is causing the issue
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

def check_start_index_issue(base_dir="."):
    """Check if START_INDEX is pointing to an exhausted key."""
    base_path = Path(base_dir)
    
    # Load .env
    env_path = base_path / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    
    start_index = os.getenv("API_KEY_ROTATOR_START_INDEX", "").strip()
    if not start_index:
        start_index = os.getenv("GOOGLE_API_KEY_START_INDEX", "").strip()
    
    if not start_index:
        print("✅ No START_INDEX set - using default rotation")
        return
    
    try:
        start_1based = int(start_index)
    except ValueError:
        print(f"❌ Invalid START_INDEX: {start_index}")
        return
    
    # Count available keys
    key_count = 0
    for i in range(1, 100):  # Check up to 100 keys
        key_name = f"GOOGLE_API_KEY_{i}"
        key_value = os.getenv(key_name, "").strip()
        if key_value:
            key_count = i
        else:
            break
    
    print("=" * 80)
    print("API Key START_INDEX Analysis")
    print("=" * 80)
    print()
    print(f"START_INDEX (1-based): {start_1based}")
    print(f"Total Keys Available: {key_count}")
    print()
    
    if start_1based > key_count:
        print(f"❌ ERROR: START_INDEX={start_1based} exceeds available keys ({key_count})")
        print(f"   Fix: Set START_INDEX to 1-{key_count} or remove it")
        return
    
    # Check key status
    state_file = base_path / "2_Data" / "metadata" / ".api_key_status.json"
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            
            key_id = f"GOOGLE_API_KEY_{start_1based}"
            key_state = state.get("keys", {}).get(key_id, {})
            is_active = key_state.get("is_active", True)
            failure_count = key_state.get("failure_count", 0)
            daily_requests = key_state.get("daily_requests", 0)
            
            print(f"Key Status for {key_id}:")
            print(f"  Active: {is_active}")
            print(f"  Daily Requests: {daily_requests}")
            print(f"  Failure Count: {failure_count}")
            print()
            
            if not is_active:
                print(f"❌ WARNING: START_INDEX={start_1based} points to an EXHAUSTED key!")
                print(f"   This key has been marked inactive due to quota exhaustion.")
                print(f"   Solution:")
                print(f"   1. Remove START_INDEX from .env to use automatic rotation")
                print(f"   2. Or set START_INDEX to a different active key (1-{key_count})")
                print()
                
                # Find active keys
                active_keys = []
                for i in range(1, key_count + 1):
                    kid = f"GOOGLE_API_KEY_{i}"
                    kstate = state.get("keys", {}).get(kid, {})
                    if kstate.get("is_active", True):
                        active_keys.append(i)
                
                if active_keys:
                    print(f"   Available active keys: {active_keys}")
                else:
                    print(f"   ⚠️  All keys are exhausted! Wait for quota reset or add more keys.")
            else:
                print(f"✅ Key {start_1based} is active")
                
        except Exception as e:
            print(f"⚠️  Could not read key status: {e}")
    else:
        print("ℹ️  No key status file found (first run)")
        print(f"   START_INDEX={start_1based} will be used on first run")

if __name__ == "__main__":
    check_start_index_issue()


#!/usr/bin/env python3
"""
Check for duplicate API keys in .env file

This script reads the .env file and checks for duplicate GOOGLE_API_KEY_N values.
For security, it outputs hash values of keys instead of the actual keys.

Usage:
    python3 3_Code/Scripts/check_api_keys_duplicate.py
    # or from project root:
    python3 3_Code/Scripts/check_api_keys_duplicate.py
"""
import hashlib
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

from dotenv import load_dotenv


def get_key_hash(key_value: str) -> str:
    """Generate a short hash of the API key for visual verification."""
    # Use SHA256 and take first 8 characters for readability
    return hashlib.sha256(key_value.encode("utf-8")).hexdigest()[:8]


def load_api_keys_from_env(base_dir: Path) -> Dict[int, str]:
    """
    Load all GOOGLE_API_KEY_N keys from .env file.
    
    Returns:
        Dictionary mapping key index (1-based) to key value
    """
    env_path = base_dir / ".env"
    if not env_path.exists():
        return {}
    
    # Load .env file
    load_dotenv(dotenv_path=env_path, override=True)
    
    # Find all numbered keys using regex pattern (same as ApiKeyRotator)
    key_prefix = "GOOGLE_API_KEY"
    pattern = re.compile(rf"^{re.escape(key_prefix)}_(\d+)$")
    found_keys: Dict[int, str] = {}
    
    # Scan all environment variables
    for env_key, env_value in os.environ.items():
        match = pattern.match(env_key)
        if match:
            key_num = int(match.group(1))
            key_value = env_value.strip()
            if key_value:  # Only add non-empty keys
                found_keys[key_num] = key_value
    
    return found_keys


def find_duplicates(keys: Dict[int, str]) -> Dict[str, List[int]]:
    """
    Find duplicate key values.
    
    Returns:
        Dictionary mapping key value to list of key indices (1-based) that use it
    """
    value_to_indices: Dict[str, List[int]] = {}
    
    for key_num, key_value in keys.items():
        if key_value not in value_to_indices:
            value_to_indices[key_value] = []
        value_to_indices[key_value].append(key_num)
    
    # Filter to only duplicates (values that appear more than once)
    duplicates = {k: v for k, v in value_to_indices.items() if len(v) > 1}
    
    return duplicates


def main():
    """Main function to check for duplicate API keys."""
    # Default to current working directory (scripts are run from project root)
    # Also try to find .env by going up from script location as fallback
    base_dir = Path.cwd()
    
    # If .env doesn't exist in current directory, try script location
    if not (base_dir / ".env").exists():
        script_dir = Path(__file__).parent
        # Try: 3_Code/Scripts -> 3_Code -> project root
        potential_base = script_dir.parent.parent
        if (potential_base / ".env").exists():
            base_dir = potential_base
    
    # Load API keys
    keys = load_api_keys_from_env(base_dir)
    
    if not keys:
        print("=" * 80)
        print("API Key Duplicate Check")
        print("=" * 80)
        print()
        print("ℹ️  No GOOGLE_API_KEY_N keys found in .env file")
        print(f"   Checked: {base_dir / '.env'}")
        print()
        print("Expected format: GOOGLE_API_KEY_1, GOOGLE_API_KEY_2, ...")
        return
    
    # Find duplicates
    duplicates = find_duplicates(keys)
    
    # Print results
    print("=" * 80)
    print("API Key Duplicate Check")
    print("=" * 80)
    print()
    print(f"Total keys found: {len(keys)}")
    print(f"Unique key values: {len(keys) - sum(len(v) - 1 for v in duplicates.values())}")
    print()
    
    # Print all keys with their hashes
    print("All Keys (Hash Values):")
    print("-" * 80)
    for key_num in sorted(keys.keys()):
        key_value = keys[key_num]
        key_hash = get_key_hash(key_value)
        duplicate_marker = " ⚠️  (DUPLICATE)" if key_value in duplicates else ""
        print(f"  GOOGLE_API_KEY_{key_num}: {key_hash}{duplicate_marker}")
    print()
    
    # Print duplicate warnings
    if duplicates:
        print("=" * 80)
        print("⚠️  DUPLICATE KEYS DETECTED!")
        print("=" * 80)
        print()
        print("The following keys have duplicate values:")
        print()
        
        for key_value, indices in sorted(duplicates.items(), key=lambda x: min(x[1])):
            key_hash = get_key_hash(key_value)
            print(f"  Hash: {key_hash}")
            print(f"  Used by: {', '.join(f'GOOGLE_API_KEY_{i}' for i in sorted(indices))}")
            print(f"  Count: {len(indices)} occurrences")
            print()
        
        print("Recommendation:")
        print("  - Remove duplicate keys from .env file")
        print("  - Each GOOGLE_API_KEY_N should have a unique value")
        print("  - Duplicate keys reduce the effectiveness of key rotation")
    else:
        print("=" * 80)
        print("✅ No duplicate keys found")
        print("=" * 80)
        print()
        print("All API keys are unique. Key rotation will work correctly.")


if __name__ == "__main__":
    main()


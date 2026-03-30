#!/usr/bin/env python3
"""
Check current API key status for S4 image generation.

Usage:
    python3 3_Code/Scripts/check_api_key_status.py
"""

import sys
from pathlib import Path

# Add src to path
base_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(base_dir / "3_Code" / "src"))

try:
    from tools.api_key_rotator import ApiKeyRotator
    
    # Initialize rotator
    rotator = ApiKeyRotator(base_dir=base_dir, key_prefix="GOOGLE_API_KEY")
    
    # Get current key
    current_key = rotator.get_current_key()
    current_index = rotator._current_index
    current_key_number = rotator.key_numbers[current_index]
    
    print("=" * 60)
    print("현재 사용 중인 API KEY")
    print("=" * 60)
    print(f"키 인덱스: {current_index} (0-based)")
    print(f"키 ID: GOOGLE_API_KEY_{current_key_number} (실제 번호)")
    print(f"키 값: {current_key[:30]}...{current_key[-10:]}")
    print()
    
    # Get full status
    print("=" * 60)
    print("전체 키 상태")
    print("=" * 60)
    status = rotator.get_key_status()
    print(f"총 키 개수: {status['total_keys']}")
    print(f"현재 키: {status['current_key_id']} (실제 번호)")
    print()
    
    print("각 키별 상태:")
    print("-" * 60)
    # Sort by actual key number (not string sort)
    import re
    def extract_key_number(key_id):
        match = re.search(r'(\d+)$', key_id)
        return int(match.group(1)) if match else 0
    
    for key_id in sorted(status['keys'].keys(), key=extract_key_number):
        key_info = status['keys'][key_id]
        is_current = key_info.get('is_current', False)
        marker = "👉 [현재]" if is_current else "   "
        active_status = "✅ Active" if key_info.get('is_active', True) else "❌ Inactive"
        daily = key_info.get('daily_requests', 0)
        total = key_info.get('total_requests', 0)
        failures = key_info.get('failure_count', 0)
        
        print(f"{marker} {key_id:25} {active_status:12} Daily: {daily:6} Total: {total:6} Failures: {failures:4}")
    
    print("=" * 60)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


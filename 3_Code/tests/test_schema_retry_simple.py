#!/usr/bin/env python3
"""
Simple test for Schema Retry functionality - checks code integration.
"""

from pathlib import Path

def test_code_integration():
    """Test that schema retry code is properly integrated."""
    print("=" * 60)
    print("Schema Retry Integration Test")
    print("=" * 60)
    
    code_file = Path(__file__).parent.parent / "src" / "01_generate_json.py"
    
    if not code_file.exists():
        print(f"❌ File not found: {code_file}")
        return False
    
    with open(code_file, "r", encoding="utf-8") as f:
        code = f.read()
    
    checks = [
        ("MAX_SCHEMA_ATTEMPTS constant", "MAX_SCHEMA_ATTEMPTS = 3"),
        ("SCHEMA_RETRY_FEEDBACK_TEMPLATE", "SCHEMA_RETRY_FEEDBACK_TEMPLATE"),
        ("call_llm_with_schema_retry function", "def call_llm_with_schema_retry"),
        ("_classify_schema_error function", "def _classify_schema_error"),
        ("S1 integration", "call_llm_with_schema_retry" in code and "validate_fn=validate_stage1" in code),
        ("S2 integration", "call_llm_with_schema_retry" in code and "validate_fn=validate_stage2" in code),
        ("Retry log path", "llm_schema_retry_log.jsonl"),
        ("Raw response saving", "raw_llm_dir"),
        ("Error feedback template", "Your previous output failed schema validation"),
    ]
    
    passed = 0
    total = len(checks)
    
    for name, check in checks:
        if isinstance(check, bool):
            result = check
        else:
            result = check in code
        
        status = "✅" if result else "❌"
        print(f"{status} {name}")
        if result:
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} checks passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 All integration checks passed!")
        print("\nTo test with actual execution:")
        print("  python3 3_Code/src/01_generate_json.py \\")
        print("    --base_dir . \\")
        print("    --run_tag TEST_SCHEMA_RETRY \\")
        print("    --arm A \\")
        print("    --stage 1 \\")
        print("    --sample 1")
        print("\nCheck logs at: 2_Data/metadata/generated/TEST_SCHEMA_RETRY/logs/llm_schema_retry_log.jsonl")
        print("Check raw responses at: 2_Data/metadata/generated/TEST_SCHEMA_RETRY/raw_llm/")
        return True
    else:
        print(f"\n⚠️  {total - passed} check(s) failed")
        return False


if __name__ == "__main__":
    import sys
    success = test_code_integration()
    sys.exit(0 if success else 1)


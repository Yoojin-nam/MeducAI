#!/usr/bin/env python3
"""
Test script for Schema Retry functionality.

This script tests the schema retry logic by:
1. Verifying the function exists and can be imported
2. Checking that retry logic is properly integrated in S1/S2
3. Validating log/artifact paths are correctly set up
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_imports():
    """Test that required functions can be imported."""
    print("Testing imports...")
    try:
        # Import using importlib to handle numeric prefix
        import importlib.util
        code_path = Path(__file__).parent.parent / "src" / "01_generate_json.py"
        if not code_path.exists():
            print(f"❌ File not found: {code_path}")
            return False
        
        spec = importlib.util.spec_from_file_location("generate_json_module", str(code_path))
        if spec is None or spec.loader is None:
            print(f"❌ Failed to create spec from file")
            return False
        
        generate_json = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generate_json)
        
        # Check required attributes exist
        required_attrs = [
            "call_llm_with_schema_retry",
            "MAX_SCHEMA_ATTEMPTS",
            "SCHEMA_RETRY_FEEDBACK_TEMPLATE",
            "validate_stage1",
            "validate_stage2",
        ]
        
        missing = [attr for attr in required_attrs if not hasattr(generate_json, attr)]
        if missing:
            print(f"❌ Missing attributes: {missing}")
            return False
        
        print(f"✅ All imports successful")
        print(f"   - MAX_SCHEMA_ATTEMPTS = {generate_json.MAX_SCHEMA_ATTEMPTS}")
        print(f"   - SCHEMA_RETRY_FEEDBACK_TEMPLATE length = {len(generate_json.SCHEMA_RETRY_FEEDBACK_TEMPLATE)} chars")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_function_signature():
    """Test that call_llm_with_schema_retry has correct signature."""
    print("\nTesting function signature...")
    try:
        import inspect
        import importlib.util
        code_path = Path(__file__).parent.parent / "src" / "01_generate_json.py"
        spec = importlib.util.spec_from_file_location("generate_json_module", str(code_path))
        if spec is None or spec.loader is None:
            return False
        generate_json = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generate_json)
        call_llm_with_schema_retry = generate_json.call_llm_with_schema_retry
        
        sig = inspect.signature(call_llm_with_schema_retry)
        params = list(sig.parameters.keys())
        
        required_params = [
            "validate_fn",
            "run_tag",
            "arm",
            "group_id",
            "out_dir",
        ]
        
        missing = [p for p in required_params if p not in params]
        if missing:
            print(f"❌ Missing required parameters: {missing}")
            return False
        
        print(f"✅ Function signature OK")
        print(f"   - Total parameters: {len(params)}")
        print(f"   - Required parameters present: {required_params}")
        return True
    except Exception as e:
        print(f"❌ Signature check failed: {e}")
        return False


def test_error_classification():
    """Test error classification logic."""
    print("\nTesting error classification...")
    try:
        import importlib.util
        code_path = Path(__file__).parent.parent / "src" / "01_generate_json.py"
        spec = importlib.util.spec_from_file_location("generate_json_module", str(code_path))
        if spec is None or spec.loader is None:
            return False
        generate_json = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generate_json)
        _classify_schema_error = generate_json._classify_schema_error
        
        test_cases = [
            (ValueError("JSON parse error"), "json_parse"),
            (ValueError("Missing key: visual_type_category"), "schema_missing_key"),
            (ValueError("Type mismatch: expected str, got int"), "type_mismatch"),
            (ValueError("Expected exactly 3 cards per entity"), "card_count_mismatch"),
            (ValueError("Stage1 visual_type_category is empty"), "s1_required_field"),
            (ValueError("Q1 requires image_hint"), "s2_required_field"),
            (ValueError("Deictic image reference found"), "s2_deictic_reference"),
            (ValueError("MCQ must have exactly 5 options"), "s2_mcq_format"),
        ]
        
        all_passed = True
        for error, expected_type in test_cases:
            error_type, summary = _classify_schema_error(error)
            if error_type == expected_type:
                print(f"   ✅ {expected_type}: '{summary[:50]}...'")
            else:
                print(f"   ❌ Expected {expected_type}, got {error_type}")
                all_passed = False
        
        if all_passed:
            print("✅ Error classification OK")
        return all_passed
    except Exception as e:
        print(f"❌ Error classification test failed: {e}")
        return False


def test_integration_points():
    """Test that S1/S2 integration points exist."""
    print("\nTesting integration points...")
    try:
        import ast
        import inspect
        
        code_file = Path(__file__).parent.parent / "src" / "01_generate_json.py"
        with open(code_file, "r", encoding="utf-8") as f:
            code = f.read()
        
        # Check S1 integration
        if "call_llm_with_schema_retry" in code and "validate_fn=validate_stage1" in code:
            print("   ✅ S1 integration found")
            s1_ok = True
        else:
            print("   ❌ S1 integration not found")
            s1_ok = False
        
        # Check S2 integration
        if "call_llm_with_schema_retry" in code and "validate_fn=validate_stage2" in code:
            print("   ✅ S2 integration found")
            s2_ok = True
        else:
            print("   ❌ S2 integration not found")
            s2_ok = False
        
        return s1_ok and s2_ok
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Schema Retry Test Suite")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Function Signature", test_function_signature),
        ("Error Classification", test_error_classification),
        ("Integration Points", test_integration_points),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())


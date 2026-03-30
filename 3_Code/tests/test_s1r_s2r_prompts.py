"""
Test script for S1R/S2R prompts

This script validates that:
1. Prompt files exist and are readable
2. Prompt templates have correct placeholders
3. Prompts can be formatted correctly
"""

import sys
from pathlib import Path


def load_prompt(base_dir: Path, prompt_name: str) -> str:
    """Load prompt from 3_Code/prompt/ directory."""
    prompt_path = base_dir / "3_Code" / "prompt" / prompt_name
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def test_prompt_files_exist(base_dir: Path) -> bool:
    """Test that all required prompt files exist."""
    print("\n[Test 1] Checking prompt files exist...")
    
    required_prompts = [
        "S1R_SYSTEM__v1.md",
        "S1R_USER__v1.md",
        "S2R_SYSTEM__v1.md",
        "S2R_USER__v1.md",
    ]
    
    all_exist = True
    for prompt_name in required_prompts:
        prompt_path = base_dir / "3_Code" / "prompt" / prompt_name
        if prompt_path.exists():
            size = prompt_path.stat().st_size
            print(f"  ✓ {prompt_name} exists ({size} bytes)")
        else:
            print(f"  ❌ {prompt_name} NOT FOUND")
            all_exist = False
    
    return all_exist


def test_prompt_content(base_dir: Path) -> bool:
    """Test that prompts have expected content and placeholders."""
    print("\n[Test 2] Checking prompt content and placeholders...")
    
    tests_passed = True
    
    # Test S1R_SYSTEM
    try:
        s1r_system = load_prompt(base_dir, "S1R_SYSTEM__v1.md")
        if "Master Table" in s1r_system and "S5 validation" in s1r_system:
            print("  ✓ S1R_SYSTEM__v1.md has expected content")
        else:
            print("  ❌ S1R_SYSTEM__v1.md missing expected keywords")
            tests_passed = False
    except Exception as e:
        print(f"  ❌ Failed to load S1R_SYSTEM__v1.md: {e}")
        tests_passed = False
    
    # Test S1R_USER
    try:
        s1r_user = load_prompt(base_dir, "S1R_USER__v1.md")
        required_placeholders = ["{master_table_markdown_kr}", "{s5_issues_formatted}"]
        missing = [p for p in required_placeholders if p not in s1r_user]
        if not missing:
            print("  ✓ S1R_USER__v1.md has all required placeholders")
        else:
            print(f"  ❌ S1R_USER__v1.md missing placeholders: {missing}")
            tests_passed = False
    except Exception as e:
        print(f"  ❌ Failed to load S1R_USER__v1.md: {e}")
        tests_passed = False
    
    # Test S2R_SYSTEM
    try:
        s2r_system = load_prompt(base_dir, "S2R_SYSTEM__v1.md")
        if "Anki flashcard" in s2r_system and "S5 validation" in s2r_system:
            print("  ✓ S2R_SYSTEM__v1.md has expected content")
        else:
            print("  ❌ S2R_SYSTEM__v1.md missing expected keywords")
            tests_passed = False
    except Exception as e:
        print(f"  ❌ Failed to load S2R_SYSTEM__v1.md: {e}")
        tests_passed = False
    
    # Test S2R_USER
    try:
        s2r_user = load_prompt(base_dir, "S2R_USER__v1.md")
        required_placeholders = ["{front_text}", "{back_text}", "{options_list}", "{s5_issues_formatted}"]
        missing = [p for p in required_placeholders if p not in s2r_user]
        if not missing:
            print("  ✓ S2R_USER__v1.md has all required placeholders")
        else:
            print(f"  ❌ S2R_USER__v1.md missing placeholders: {missing}")
            tests_passed = False
    except Exception as e:
        print(f"  ❌ Failed to load S2R_USER__v1.md: {e}")
        tests_passed = False
    
    return tests_passed


def test_prompt_formatting(base_dir: Path) -> bool:
    """Test that prompts can be formatted with sample data."""
    print("\n[Test 3] Testing prompt formatting with sample data...")
    
    tests_passed = True
    
    # Test S1R_USER formatting
    try:
        s1r_user_template = load_prompt(base_dir, "S1R_USER__v1.md")
        
        sample_table = "|Entity name|질환 정의|영상 소견|병리|감별|시험포인트|\n|---|---|---|---|---|---|\n|Test Entity|Test definition|Test findings|Test pathology|Test DDx|Test exam point|"
        sample_issues = "Issue 1:\n  - Severity: major\n  - Type: factual\n  - Description: Test issue description\n  - Suggested Fix: Test fix"
        
        formatted = s1r_user_template.format(
            master_table_markdown_kr=sample_table,
            s5_issues_formatted=sample_issues,
        )
        
        if sample_table in formatted and sample_issues in formatted:
            print("  ✓ S1R_USER__v1.md formatting works")
        else:
            print("  ❌ S1R_USER__v1.md formatting failed")
            tests_passed = False
    except Exception as e:
        print(f"  ❌ S1R_USER__v1.md formatting error: {e}")
        tests_passed = False
    
    # Test S2R_USER formatting
    try:
        s2r_user_template = load_prompt(base_dir, "S2R_USER__v1.md")
        
        sample_front = "Test question text"
        sample_back = "Test answer text"
        sample_options = "A. Option A\nB. Option B\nC. Option C\nD. Option D\nE. Option E"
        sample_issues = "Issue 1:\n  - Severity: major\n  - Type: factual\n  - Description: Test issue description"
        
        formatted = s2r_user_template.format(
            front_text=sample_front,
            back_text=sample_back,
            options_list=sample_options,
            s5_issues_formatted=sample_issues,
        )
        
        if sample_front in formatted and sample_back in formatted and sample_options in formatted:
            print("  ✓ S2R_USER__v1.md formatting works")
        else:
            print("  ❌ S2R_USER__v1.md formatting failed")
            tests_passed = False
    except Exception as e:
        print(f"  ❌ S2R_USER__v1.md formatting error: {e}")
        tests_passed = False
    
    return tests_passed


def test_prompt_structure(base_dir: Path) -> bool:
    """Test that prompts have proper markdown structure."""
    print("\n[Test 4] Checking prompt markdown structure...")
    
    tests_passed = True
    
    for prompt_name in ["S1R_SYSTEM__v1.md", "S1R_USER__v1.md", "S2R_SYSTEM__v1.md", "S2R_USER__v1.md"]:
        try:
            content = load_prompt(base_dir, prompt_name)
            
            # Check for basic markdown elements
            has_headers = "#" in content
            has_sections = "##" in content or "###" in content
            has_code_blocks = "```" in content
            
            if has_headers and has_sections:
                print(f"  ✓ {prompt_name} has proper markdown structure")
            else:
                print(f"  ⚠️  {prompt_name} may be missing markdown structure elements")
                # Not a hard failure, just a warning
        except Exception as e:
            print(f"  ❌ Failed to check {prompt_name}: {e}")
            tests_passed = False
    
    return tests_passed


def test_prompt_response_schemas(base_dir: Path) -> bool:
    """Test that prompts specify correct JSON response schemas."""
    print("\n[Test 5] Checking response schema specifications...")
    
    tests_passed = True
    
    # Test S1R prompts mention expected output fields
    try:
        s1r_system = load_prompt(base_dir, "S1R_SYSTEM__v1.md")
        s1r_user = load_prompt(base_dir, "S1R_USER__v1.md")
        
        expected_fields = ["improved_table_markdown", "changes_summary", "confidence"]
        missing = [f for f in expected_fields if f not in s1r_system and f not in s1r_user]
        
        if not missing:
            print("  ✓ S1R prompts specify all expected output fields")
        else:
            print(f"  ⚠️  S1R prompts may be missing output field mentions: {missing}")
            # Not a hard failure
    except Exception as e:
        print(f"  ❌ Failed to check S1R response schema: {e}")
        tests_passed = False
    
    # Test S2R prompts mention expected output fields
    try:
        s2r_system = load_prompt(base_dir, "S2R_SYSTEM__v1.md")
        s2r_user = load_prompt(base_dir, "S2R_USER__v1.md")
        
        expected_fields = ["improved_front", "improved_back", "improved_options", "changes_summary", "confidence"]
        missing = [f for f in expected_fields if f not in s2r_system and f not in s2r_user]
        
        if not missing:
            print("  ✓ S2R prompts specify all expected output fields")
        else:
            print(f"  ⚠️  S2R prompts may be missing output field mentions: {missing}")
            # Not a hard failure
    except Exception as e:
        print(f"  ❌ Failed to check S2R response schema: {e}")
        tests_passed = False
    
    return tests_passed


def main():
    """Run all tests."""
    print("="*80)
    print("S1R/S2R Prompt Validation Tests")
    print("="*80)
    
    # Determine base directory (assume running from 3_Code/tests/)
    base_dir = Path(__file__).resolve().parent.parent.parent
    print(f"\nBase directory: {base_dir}")
    
    # Run tests
    results = []
    results.append(("Prompt files exist", test_prompt_files_exist(base_dir)))
    results.append(("Prompt content valid", test_prompt_content(base_dir)))
    results.append(("Prompt formatting works", test_prompt_formatting(base_dir)))
    results.append(("Prompt structure valid", test_prompt_structure(base_dir)))
    results.append(("Response schemas specified", test_prompt_response_schemas(base_dir)))
    
    # Summary
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("✓ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

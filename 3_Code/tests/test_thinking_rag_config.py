#!/usr/bin/env python3
"""
Test script to verify that thinking and RAG configurations are properly applied
for each arm in the 6-arm setup.
"""

import re
from pathlib import Path

def test_arm_configs():
    """Verify ARM_CONFIGS have correct thinking and rag flags."""
    print("=" * 60)
    print("Testing ARM_CONFIGS for thinking and RAG settings")
    print("=" * 60)
    
    src_file = Path(__file__).parent.parent / "src" / "01_generate_json.py"
    content = src_file.read_text()
    
    expected = {
        "A": {"thinking": False, "rag": False, "desc": "Baseline"},
        "B": {"thinking": False, "rag": True, "desc": "RAG Only"},
        "C": {"thinking": True, "rag": False, "desc": "Thinking"},
        "D": {"thinking": True, "rag": True, "desc": "Synergy"},
        "E": {"thinking": True, "rag": True, "desc": "High-End"},
        "F": {"thinking": True, "rag": True, "desc": "Benchmark"},
    }
    
    all_pass = True
    
    for arm in ["A", "B", "C", "D", "E", "F"]:
        # Find arm config block by searching for the arm key
        arm_key_pos = content.find(f'"{arm}":')
        if arm_key_pos == -1:
            print(f"\n❌ Arm {arm}: Config block not found")
            all_pass = False
            continue
        
        # Extract a reasonable chunk around the arm config (up to next arm or closing brace)
        arm_section = content[arm_key_pos:arm_key_pos + 800]
        # Stop at next arm definition or closing brace
        next_arm_pos = min(
            [pos for pos in [arm_section.find(f'"{a}":') for a in ["A", "B", "C", "D", "E", "F"] if a != arm] if pos > 0] + [len(arm_section)],
            default=len(arm_section)
        )
        arm_section = arm_section[:next_arm_pos]
        
        # Check thinking flag
        thinking_match = re.search(r'"thinking":\s*(True|False)', arm_section)
        thinking = thinking_match.group(1) == "True" if thinking_match else None
        
        # Check rag flag
        rag_match = re.search(r'"rag":\s*(True|False)', arm_section)
        rag = rag_match.group(1) == "True" if rag_match else None
        
        if thinking is None or rag is None:
            print(f"\n❌ Arm {arm}: Could not parse thinking or rag flags")
            all_pass = False
            continue
        
        exp = expected[arm]
        thinking_ok = thinking == exp["thinking"]
        rag_ok = rag == exp["rag"]
        
        status = "✅" if (thinking_ok and rag_ok) else "❌"
        
        print(f"\n{status} Arm {arm} ({exp['desc']}):")
        print(f"   thinking: {thinking} (expected: {exp['thinking']}) {'✓' if thinking_ok else '✗'}")
        print(f"   rag:      {rag} (expected: {exp['rag']}) {'✓' if rag_ok else '✗'}")
        
        if not (thinking_ok and rag_ok):
            all_pass = False
    
    print("\n" + "=" * 60)
    if all_pass:
        print("✅ All ARM_CONFIGS are correctly configured!")
    else:
        print("❌ Some ARM_CONFIGS have incorrect settings!")
    print("=" * 60)
    
    return all_pass


def test_call_llm_signature():
    """Verify call_llm function accepts rag_enabled parameter."""
    print("\n" + "=" * 60)
    print("Testing call_llm function signature")
    print("=" * 60)
    
    src_file = Path(__file__).parent.parent / "src" / "01_generate_json.py"
    content = src_file.read_text()
    
    # Find call_llm function definition
    func_match = re.search(r'def call_llm\([^)]+\)', content, re.DOTALL)
    
    if not func_match:
        print("❌ Could not find call_llm function definition")
        return False
    
    func_sig = func_match.group(0)
    
    has_rag_enabled = "rag_enabled" in func_sig
    has_thinking_enabled = "thinking_enabled" in func_sig
    has_thinking_budget = "thinking_budget" in func_sig
    
    print(f"Function signature found: {func_sig[:100]}...")
    print(f"  thinking_enabled: {'✅' if has_thinking_enabled else '❌'}")
    print(f"  thinking_budget:   {'✅' if has_thinking_budget else '❌'}")
    print(f"  rag_enabled:       {'✅' if has_rag_enabled else '❌'}")
    
    result = has_rag_enabled and has_thinking_enabled and has_thinking_budget
    
    print("\n" + "=" * 60)
    if result:
        print("✅ call_llm function signature is correct!")
    else:
        print("❌ call_llm function signature is missing required parameters!")
    print("=" * 60)
    
    return result


def test_gemini_config_application():
    """Verify that Gemini generation config applies thinking and RAG."""
    print("\n" + "=" * 60)
    print("Testing Gemini config application logic")
    print("=" * 60)
    
    src_file = Path(__file__).parent.parent / "src" / "01_generate_json.py"
    content = src_file.read_text()
    
    checks = {
        "thinking_config applied": "thinking_config = genai_types.ThinkingConfig" in content,
        "GoogleSearch tool applied": "genai_types.Tool(google_search=genai_types.GoogleSearch())" in content,
        "response_mime_type conditional": "if not rag_enabled:" in content and "response_mime_type" in content,
        "rag_enabled parameter": "rag_enabled: bool" in content,
        "RAG metadata logging": "rag_queries_count" in content and "rag_sources_count" in content,
        "thinking condition check": "if thinking_enabled and thinking_budget > 0:" in content,
    }
    
    all_pass = True
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
        if not result:
            all_pass = False
    
    print("\n" + "=" * 60)
    if all_pass:
        print("✅ All Gemini config application checks passed!")
    else:
        print("❌ Some checks failed!")
    print("=" * 60)
    
    return all_pass


def test_call_llm_invocations():
    """Verify that call_llm is called with rag_enabled in both stages."""
    print("\n" + "=" * 60)
    print("Testing call_llm invocations")
    print("=" * 60)
    
    src_file = Path(__file__).parent.parent / "src" / "01_generate_json.py"
    content = src_file.read_text()
    
    # Check Stage1 call - look for the pattern more flexibly
    stage1_section = content[content.find("s1_json, err1, rt_s1"):content.find("s1_json, err1, rt_s1") + 500]
    stage1_has_rag = "rag_enabled=rag_enabled" in stage1_section
    
    # Check Stage2 call - look for the pattern more flexibly
    stage2_section = content[content.find("s2_json, err2, rt_s2"):content.find("s2_json, err2, rt_s2") + 500]
    stage2_has_rag = "rag_enabled=rag_enabled" in stage2_section
    
    print(f"Stage1 call_llm with rag_enabled: {'✅' if stage1_has_rag else '❌'}")
    if not stage1_has_rag:
        print(f"  Stage1 section preview: {stage1_section[:200]}")
    print(f"Stage2 call_llm with rag_enabled: {'✅' if stage2_has_rag else '❌'}")
    if not stage2_has_rag:
        print(f"  Stage2 section preview: {stage2_section[:200]}")
    
    result = stage1_has_rag and stage2_has_rag
    
    print("\n" + "=" * 60)
    if result:
        print("✅ Both Stage1 and Stage2 call_llm with rag_enabled!")
    else:
        print("❌ Some call_llm invocations are missing rag_enabled!")
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    print("\n🧪 Testing Thinking and RAG Configuration\n")
    
    test1 = test_arm_configs()
    test2 = test_call_llm_signature()
    test3 = test_gemini_config_application()
    test4 = test_call_llm_invocations()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"ARM_CONFIGS test:        {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"call_llm signature test:  {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"Gemini config test:       {'✅ PASS' if test3 else '❌ FAIL'}")
    print(f"call_llm invocations:     {'✅ PASS' if test4 else '❌ FAIL'}")
    print("=" * 60)
    
    if test1 and test2 and test3 and test4:
        print("\n✅ All tests passed! Thinking and RAG should be properly applied.")
        print("\n💡 Next step: Run a smoke test with --sample 1 to verify actual API calls.")
        exit(0)
    else:
        print("\n❌ Some tests failed. Please review the code.")
        exit(1)

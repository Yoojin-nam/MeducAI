#!/usr/bin/env python3
"""
Test JSON Schema translation to debug the issue.
"""

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_parent = _THIS_DIR.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from tools.anki.translate_medical_terms_module import MedicalTermTranslator

# Test text with Korean
test_text = """Answer: Midgut Volvulus (중장 염전)

근거:
* US에서 superior mesenteric vein (SMV)이 superior mesenteric artery (SMA) 주위를 whirlpool sign 양상으로 회전
* UGIS에서 distal duodenum이 corkscrew appearance로 좁아짐"""

print("=" * 80)
print("JSON Schema Translation Test")
print("=" * 80)
print("\nInput text:")
print("-" * 80)
print(test_text)
print()

# Initialize translator
print("Initializing translator...")
translator = MedicalTermTranslator(
    model="gemini-2.0-flash-exp",
    temperature=0.0,
    use_rotator=False,  # Use single key for testing
)

print("✅ Translator initialized")
print()

# Translate with debug
print("Translating...")
print("-" * 80)

try:
    result = translator.translate_text(test_text, use_cache=False, verbose=True)
    
    print()
    print("=" * 80)
    print("Result:")
    print("=" * 80)
    print(result)
    print()
    
    # Check for thinking patterns
    thinking_markers = ['Wait,', 'Rule', 'Let\'s', 'is capitalized', 'Actually']
    has_thinking = any(marker in result for marker in thinking_markers)
    
    if has_thinking:
        print("⚠️  WARNING: Result still contains thinking patterns!")
        for marker in thinking_markers:
            if marker in result:
                print(f"   - Found: {marker}")
    else:
        print("✅ SUCCESS: No thinking patterns detected")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("=" * 80)


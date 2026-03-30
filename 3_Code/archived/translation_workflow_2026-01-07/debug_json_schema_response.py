#!/usr/bin/env python3
"""
Debug JSON Schema translation response.
"""

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_parent = _THIS_DIR.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from preprocess.gemini_utils import GeminiClient, GeminiConfig

# Test text - problematic pattern
test_text = """초음파 횡단면에서 상장간막정맥(SMV)이 상장간막동맥(SMA) 주위를 감싸고 도는 양상이 관찰되며, 상부위장관조영술(UGIS)에서 십이지장 원위부가 나선형으로 좁아지는 소견을 보이는 신생아의 가장 가능성이 높은 진단은?"""

print("=" * 80)
print("JSON Schema 응답 디버깅")
print("=" * 80)
print(f"\n입력 텍스트:")
print(test_text)
print()

# Import actual prompt + schema config helper from module
from tools.anki.translate_medical_terms_module import (
    SYSTEM_PROMPT,
    TRANSLATION_SCHEMA,
    _make_structured_generate_config,
)

print("Using updated SYSTEM_PROMPT from module")
print(f"Prompt length: {len(SYSTEM_PROMPT)} characters")
print()

# Initialize client
print("Initializing Gemini client...")

import os
api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('RAB_LLM_API_KEY') or os.getenv('GEMINI_API_KEY')

client = GeminiClient(
    GeminiConfig(
        model="gemini-2.0-flash-exp",
        temperature=0.0,
        top_p=1.0,
        top_k=1,
        max_output_tokens=4096,
    ),
    api_key=api_key,
)

print("✅ Client ready")
print()

# Call with JSON Schema
print("Calling API with JSON Schema...")
print("-" * 80)

cfg = _make_structured_generate_config(
    types=client._types,
    model=client.cfg.model,
    system_instruction=SYSTEM_PROMPT,
    temperature=0.0,
    schema=TRANSLATION_SCHEMA,
)

resp = client._client.models.generate_content(
    model=client.cfg.model,
    contents=test_text,
    config=cfg,
)

# Raw response
raw_result = getattr(resp, "text", "").strip()

print(f"Raw API Response:")
print("=" * 80)
print(raw_result)
print()

# Parse JSON
import json
try:
    parsed = json.loads(raw_result)
    print(f"Parsed JSON:")
    print("=" * 80)
    print(json.dumps(parsed, ensure_ascii=False, indent=2))
    print()
    
    translated_text = parsed.get("translated_text", "")
    print(f"Extracted 'translated_text':")
    print("=" * 80)
    print(translated_text)
    print()
    
    if translated_text:
        print("✅ JSON parsing successful")
        if "Liver" in translated_text:
            print("✅ Translation successful")
        else:
            print("⚠️  Translation may not have worked (no 'Liver')")
    else:
        print("⚠️  'translated_text' field is empty")

except json.JSONDecodeError as e:
    print(f"❌ JSON parsing failed: {e}")
    print("   Raw response is not valid JSON")

print("\n" + "=" * 80)


#!/usr/bin/env python3
"""
Skip specific problematic record from JSONL file.
"""

import json
import sys
from pathlib import Path

input_file = Path('2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__regen__CARD_REGEN_ONLY.jsonl')
output_file = Path('2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__regen__CARD_REGEN_ONLY__skip192.jsonl')

skip_index = 192

with input_file.open('r') as inf, output_file.open('w') as outf:
    for i, line in enumerate(inf, 1):
        if i == skip_index:
            rec = json.loads(line)
            print(f"❌ Skipping record {i}: {rec.get('entity_name', 'Unknown')}")
            continue
        outf.write(line)

print(f"\n✅ Created: {output_file}")
print(f"   Skipped record {skip_index}")


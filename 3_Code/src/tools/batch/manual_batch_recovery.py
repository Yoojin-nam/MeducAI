"""
Manual recovery script for failed batch parsing lines.
This script extracts and manually fixes the 6 failed S2 cards.
"""

import json
import sys
from pathlib import Path

def extract_and_fix_failed_lines():
    """Extract failed lines from raw batch results and manually fix JSON issues."""
    
    # File paths
    base_dir = Path("/path/to/workspace/workspace/MeducAI")
    raw_file = base_dir / "logs/batch_raw_results_xplbwboytocdwletk7feg2gd7u49peg0chm1_20260106_101612.jsonl"
    error_log = base_dir / "logs/batch_parse_errors_20260106_101612.json"
    output_file = base_dir / "logs/recovered_s2_cards.json"
    
    # Load error log to get failed line numbers
    with open(error_log, "r", encoding="utf-8") as f:
        error_data = json.load(f)
    
    failed_lines = error_data["failed_lines"]
    line_nums = {f["line_num"]: f["key"] for f in failed_lines}
    
    print(f"Attempting to recover {len(line_nums)} failed lines...")
    
    # Read raw batch results
    with open(raw_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    recovered = {}
    
    for line_num, key in line_nums.items():
        print(f"\nProcessing line {line_num}: {key}")
        line = lines[line_num - 1]  # 0-indexed
        
        try:
            # Parse outer JSON
            result = json.loads(line)
            response = result.get("response", {})
            candidates = response.get("candidates", [])
            
            if not candidates:
                print(f"  ❌ No candidates found")
                continue
            
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            
            if not parts:
                print(f"  ❌ No parts found")
                continue
            
            text = parts[0].get("text", "")
            
            if not text:
                print(f"  ❌ No text found")
                continue
            
            # Save raw text for manual inspection
            raw_text_file = base_dir / f"logs/failed_line_{line_num}_raw.txt"
            with open(raw_text_file, "w", encoding="utf-8") as f:
                f.write(text)
            
            print(f"  📝 Raw text saved to: {raw_text_file}")
            print(f"  📏 Text length: {len(text)} characters")
            
            # Try to parse as JSON (will likely fail)
            try:
                improved = json.loads(text)
                print(f"  ✅ JSON parsed successfully!")
                recovered[key] = improved
            except json.JSONDecodeError as e:
                print(f"  ⚠️  JSON parse error: {e}")
                print(f"  Error position: line {e.lineno}, column {e.colno}")
                
                # Try to find and show the problematic area
                lines_in_text = text.split('\n')
                if e.lineno <= len(lines_in_text):
                    error_line = lines_in_text[e.lineno - 1]
                    start = max(0, e.colno - 100)
                    end = min(len(error_line), e.colno + 100)
                    context = error_line[start:end]
                    print(f"  Context: ...{context}...")
        
        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue
    
    # Save recovered cards
    if recovered:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(recovered, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Recovered {len(recovered)} cards saved to: {output_file}")
    else:
        print(f"\n⚠️  No cards were successfully recovered automatically")
    
    print(f"\n📋 Summary:")
    print(f"  Total failed: {len(line_nums)}")
    print(f"  Recovered: {len(recovered)}")
    print(f"  Still need manual fix: {len(line_nums) - len(recovered)}")
    
    return recovered

if __name__ == "__main__":
    recovered = extract_and_fix_failed_lines()
    sys.exit(0 if recovered else 1)


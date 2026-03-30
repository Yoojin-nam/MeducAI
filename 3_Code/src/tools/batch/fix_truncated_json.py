"""
Fix truncated JSON in failed batch lines by:
1. Stripping trailing whitespace
2. Adding missing closing braces/brackets
3. Validating the result
"""

import json
import sys
from pathlib import Path

def fix_truncated_json(text):
    """Fix a truncated JSON string by adding missing closing delimiters."""
    
    # Remove trailing whitespace
    text = text.rstrip()
    
    # Count delimiters
    open_brace = text.count('{')
    close_brace = text.count('}')
    open_bracket = text.count('[')
    close_bracket = text.count(']')
    
    # Add missing closing delimiters
    missing_brackets = open_bracket - close_bracket
    missing_braces = open_brace - close_brace
    
    # Add in reverse order (brackets first, then braces)
    for _ in range(missing_brackets):
        text += '\n  ]'
    for _ in range(missing_braces):
        text += '\n}'
    
    return text

def main():
    base_dir = Path("/path/to/workspace/workspace/MeducAI")
    logs_dir = base_dir / "logs"
    
    # Find all failed line raw files
    failed_files = list(logs_dir.glob("failed_line_*_raw.txt"))
    
    if not failed_files:
        print("No failed line files found")
        return 1
    
    print(f"Found {len(failed_files)} failed line files")
    
    recovered = {}
    
    for file_path in sorted(failed_files):
        line_num = file_path.stem.replace("failed_line_", "").replace("_raw", "")
        print(f"\nProcessing {file_path.name}...")
        
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        print(f"  Original length: {len(text)} chars")
        
        # Fix the JSON
        fixed_text = fix_truncated_json(text)
        
        print(f"  Fixed length: {len(fixed_text)} chars")
        
        # Try to parse
        try:
            data = json.loads(fixed_text)
            print(f"  ✅ Successfully parsed!")
            
            # Validate required fields
            required_fields = ["improved_front", "improved_back"]
            missing = [f for f in required_fields if f not in data]
            
            if missing:
                print(f"  ⚠️  Missing fields: {missing}")
            else:
                print(f"  ✅ All required fields present")
                
                # Save fixed version
                fixed_file = logs_dir / f"fixed_line_{line_num}.json"
                with open(fixed_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                print(f"  💾 Saved to: {fixed_file.name}")
                recovered[line_num] = data
        
        except json.JSONDecodeError as e:
            print(f"  ❌ Parse error: {e}")
            print(f"  Error at line {e.lineno}, column {e.colno}")
    
    # Save all recovered data
    if recovered:
        output_file = logs_dir / "all_recovered_cards.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(recovered, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Successfully recovered {len(recovered)}/{ len(failed_files)} cards")
        print(f"💾 All recovered cards saved to: {output_file}")
        return 0
    else:
        print(f"\n❌ Failed to recover any cards")
        return 1

if __name__ == "__main__":
    sys.exit(main())


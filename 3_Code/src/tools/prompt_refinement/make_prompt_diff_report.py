#!/usr/bin/env python3
"""
Generate Prompt Diff Report

Creates a markdown diff report comparing old and new prompt versions.

Usage:
    python3 make_prompt_diff_report.py \
        --base_dir . \
        --prompt_name S1_SYSTEM \
        --old_version S5R0__v12 \
        --new_version S5R1__v13 \
        --output <OUTPUT_PATH>
"""

import argparse
import difflib
import sys
from pathlib import Path
from datetime import datetime


def load_prompt(base_dir: Path, prompt_name: str, version: str) -> str:
    """Load prompt file content."""
    # Try canonical location first
    prompt_path = base_dir / "3_Code" / "prompt" / f"{prompt_name}__{version}.md"
    
    if not prompt_path.exists():
        # Try archive
        prompt_path = base_dir / "3_Code" / "prompt" / "archive" / f"{prompt_name}__{version}.md"
    
    if not prompt_path.exists():
        print(f"Error: Prompt file not found: {prompt_name}__{version}.md", file=sys.stderr)
        sys.exit(1)
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def generate_diff_report(old_content: str, new_content: str, prompt_name: str, old_version: str, new_version: str) -> str:
    """Generate markdown diff report."""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"{prompt_name}__{old_version}.md",
        tofile=f"{prompt_name}__{new_version}.md",
        lineterm="",
    )
    
    diff_text = "".join(diff)
    
    report = f"""# Prompt Diff Report

**Prompt**: {prompt_name}
**Old Version**: {old_version}
**New Version**: {new_version}
**Generated**: {datetime.now().isoformat()}

---

## Diff

```diff
{diff_text}
```

---

## Summary

- **Total lines changed**: {len([l for l in diff_text.splitlines() if l.startswith(('+', '-')) and not l.startswith(('+++', '---'))])}
- **Files**: {prompt_name}__{old_version}.md → {prompt_name}__{new_version}.md

---

## Notes

Review this diff carefully to ensure:
- Schema invariance is maintained
- Only intended changes are present
- No accidental deletions of required sections
"""
    
    return report


def main():
    parser = argparse.ArgumentParser(description="Generate prompt diff report")
    parser.add_argument("--base_dir", type=str, required=True, help="Base directory")
    parser.add_argument("--prompt_name", type=str, required=True, help="Prompt name (e.g., S1_SYSTEM)")
    parser.add_argument("--old_version", type=str, required=True, help="Old version (e.g., S5R0__v12)")
    parser.add_argument("--new_version", type=str, required=True, help="New version (e.g., S5R1__v13)")
    parser.add_argument("--output", type=str, help="Output markdown path (default: auto-generated)")
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    
    # Load prompts
    old_content = load_prompt(base_dir, args.prompt_name, args.old_version)
    new_content = load_prompt(base_dir, args.prompt_name, args.new_version)
    
    # Generate diff report
    report = generate_diff_report(
        old_content,
        new_content,
        args.prompt_name,
        args.old_version,
        args.new_version,
    )
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        # Try to infer run_tag from current directory or use default
        output_path = base_dir / "2_Data" / "metadata" / "generated" / "prompt_refinement" / f"diff_report__{args.prompt_name}__{args.new_version}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"Diff report written to: {output_path}")


if __name__ == "__main__":
    main()


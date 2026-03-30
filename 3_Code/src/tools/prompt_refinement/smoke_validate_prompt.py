#!/usr/bin/env python3
"""
Smoke Validate Prompt

Performs static validation on prompt files to ensure schema invariance.

Usage:
    python3 smoke_validate_prompt.py \
        --base_dir . \
        --prompt_file 3_Code/prompt/S1_SYSTEM__S5R1__v13.md
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Dict, Any


# Schema-related keywords that must not change
S1_SCHEMA_KEYWORDS = [
    "schema_version",
    "S1_STRUCT_v1.3",
    "master_table_markdown_kr",
    "entity_list",
    "visual_type_category",
    "group_id",
    "objective_bullets",
    "integrity",
]

S2_SCHEMA_KEYWORDS = [
    "entity_name",
    "anki_cards",
    "card_role",
    "card_type",
    "front",
    "back",
    "options",
    "correct_index",
    "image_hint",
]

REQUIRED_SECTIONS_S1 = [
    "OUTPUT SCHEMA",
    "master_table_markdown_kr",
    "entity_list",
    "visual_type_category",
]

REQUIRED_SECTIONS_S2 = [
    "OUTPUT SCHEMA",
    "anki_cards",
    "card_role",
    "card_type",
]


def load_prompt(prompt_path: Path) -> str:
    """Load prompt file."""
    if not prompt_path.exists():
        print(f"Error: Prompt file not found: {prompt_path}", file=sys.stderr)
        sys.exit(1)
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def check_schema_keywords(content: str, prompt_type: str) -> List[str]:
    """Check if schema keywords are present."""
    errors = []
    
    if prompt_type == "S1":
        keywords = S1_SCHEMA_KEYWORDS
    elif prompt_type == "S2":
        keywords = S2_SCHEMA_KEYWORDS
    else:
        return ["Unknown prompt type"]
    
    for keyword in keywords:
        if keyword not in content:
            errors.append(f"Missing schema keyword: {keyword}")
    
    return errors


def check_required_sections(content: str, prompt_type: str) -> List[str]:
    """Check if required sections are present."""
    errors = []
    
    if prompt_type == "S1":
        sections = REQUIRED_SECTIONS_S1
    elif prompt_type == "S2":
        sections = REQUIRED_SECTIONS_S2
    else:
        return ["Unknown prompt type"]
    
    for section in sections:
        if section not in content:
            errors.append(f"Missing required section: {section}")
    
    return errors


def check_markdown_format(content: str) -> List[str]:
    """Basic markdown format validation."""
    errors = []
    
    # Check for balanced markdown headers
    header_count = len(re.findall(r'^#+\s', content, re.MULTILINE))
    if header_count == 0:
        errors.append("No markdown headers found")
    
    # Check for unclosed code blocks (basic)
    code_block_count = content.count("```")
    if code_block_count % 2 != 0:
        errors.append("Unbalanced code blocks (```)")
    
    return errors


def detect_prompt_type(prompt_name: str) -> str:
    """Detect prompt type from name."""
    if "S1" in prompt_name:
        return "S1"
    elif "S2" in prompt_name:
        return "S2"
    else:
        return "UNKNOWN"


def validate_prompt(prompt_path: Path) -> Dict[str, Any]:
    """Perform smoke validation on prompt."""
    content = load_prompt(prompt_path)
    prompt_name = prompt_path.stem
    prompt_type = detect_prompt_type(prompt_name)
    
    errors = []
    warnings = []
    
    # Check schema keywords
    keyword_errors = check_schema_keywords(content, prompt_type)
    errors.extend(keyword_errors)
    
    # Check required sections
    section_errors = check_required_sections(content, prompt_type)
    errors.extend(section_errors)
    
    # Check markdown format
    format_errors = check_markdown_format(content)
    warnings.extend(format_errors)  # Format issues are warnings, not errors
    
    return {
        "prompt_file": str(prompt_path),
        "prompt_type": prompt_type,
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser(description="Smoke validate prompt file")
    parser.add_argument("--base_dir", type=str, help="Base directory (optional)")
    parser.add_argument("--prompt_file", type=str, required=True, help="Prompt file path")
    
    args = parser.parse_args()
    
    # Resolve prompt path
    if args.base_dir:
        prompt_path = Path(args.base_dir).resolve() / args.prompt_file
    else:
        prompt_path = Path(args.prompt_file).resolve()
    
    # Validate
    result = validate_prompt(prompt_path)
    
    # Print results
    print(f"Prompt: {result['prompt_file']}")
    print(f"Type: {result['prompt_type']}")
    print(f"Valid: {result['is_valid']}")
    
    if result['errors']:
        print("\nErrors:")
        for error in result['errors']:
            print(f"  - {error}")
    
    if result['warnings']:
        print("\nWarnings:")
        for warning in result['warnings']:
            print(f"  - {warning}")
    
    if not result['is_valid']:
        sys.exit(1)
    
    print("\n✓ Smoke validation passed")


if __name__ == "__main__":
    main()


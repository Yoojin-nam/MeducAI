"""
MeducAI - S1R/S2R Text Repair Agent (Synchronous Fallback)

This script provides synchronous (non-batch) text repair for S1 tables and S2 cards.
Use this for:
- Small-scale repairs (< 10 items)
- Emergency fixes requiring immediate results
- Debugging batch prompts

For large-scale repairs (50+ items), use batch_text_repair.py instead.

Usage:
    # Repair specific entity
    python s1r_s2r_agent.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G --mode sync --only_entity_id <entity_id>
    
    # Repair all low-TA items
    python s1r_s2r_agent.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G --mode sync
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Error: google.genai not available. Install: pip install google-genai")

from dotenv import load_dotenv


# =========================
# Configuration
# =========================

S1R_MODEL = "gemini-3-pro-preview"
S2R_MODEL = "gemini-3-flash-preview"
S1R_TEMPERATURE = 0.2
S2R_TEMPERATURE = 0.3
S1R_TIMEOUT = 120
S2R_TIMEOUT = 60


# =========================
# Helper Functions
# =========================

def load_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """Load a JSONL file and return list of records."""
    records = []
    if not file_path.exists():
        return records
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                records.append(record)
            except json.JSONDecodeError:
                continue
    
    return records


def write_jsonl(file_path: Path, records: List[Dict[str, Any]]) -> None:
    """Write records to a JSONL file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        for record in records:
            json_line = json.dumps(record, ensure_ascii=False)
            f.write(json_line + "\n")


# =========================
# Repair Functions
# =========================

def repair_s1_table_sync(
    client: Any,
    group_id: str,
    master_table_markdown_kr: str,
    issues: List[Dict[str, Any]],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Repair S1 table synchronously.
    
    Returns:
        (improved_table_markdown, error_message)
    """
    # Build issues text
    issues_text = ""
    for i, issue in enumerate(issues, 1):
        severity = issue.get("severity", "unknown")
        issue_type = issue.get("type", "unknown")
        description = issue.get("description", "")
        suggested_fix = issue.get("suggested_fix", "")
        issue_code = issue.get("issue_code", "")
        
        issues_text += f"\n[Issue {i}]\n"
        issues_text += f"- Severity: {severity}\n"
        issues_text += f"- Type: {issue_type}\n"
        issues_text += f"- Code: {issue_code}\n"
        issues_text += f"- Description: {description}\n"
        if suggested_fix:
            issues_text += f"- Suggested Fix: {suggested_fix}\n"
    
    # System prompt
    system_prompt = """You are an expert medical education content repair agent specializing in radiology reference tables.

TASK: Fix factual errors in a Master Table based on S5 validation feedback.

CONSTRAINTS:
1. PRESERVE table structure (columns, entity order)
2. ONLY fix the specific issues mentioned in S5 feedback
3. Do NOT add/remove entities
4. Use evidence-based corrections (cite guidelines if possible)
5. Maintain Korean language and formatting conventions

OUTPUT FORMAT: JSON with improved_table_markdown"""
    
    # User prompt
    user_prompt = f"""ORIGINAL TABLE:
{master_table_markdown_kr}

S5 VALIDATION ISSUES:
{issues_text}

REPAIR INSTRUCTIONS:
- Fix only the issues mentioned above
- Maintain table structure and formatting
- Use precise medical terminology
- Ensure all changes are evidence-based

Generate improved table with corrections applied."""
    
    try:
        response = client.models.generate_content(
            model=S1R_MODEL,
            contents=[{"role": "user", "parts": [{"text": user_prompt}]}],
            config={
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "temperature": S1R_TEMPERATURE,
                "response_mime_type": "application/json",
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "improved_table_markdown": {"type": "string"},
                        "changes_summary": {"type": "string"},
                        "confidence": {"type": "number"}
                    },
                    "required": ["improved_table_markdown"]
                }
            }
        )
        
        # Parse response
        text = response.text
        result = json.loads(text)
        improved_table = result.get("improved_table_markdown", "")
        
        if not improved_table:
            return None, "Empty improved table"
        
        return improved_table, None
        
    except Exception as e:
        return None, str(e)


def repair_s2_card_sync(
    client: Any,
    group_id: str,
    entity_id: str,
    card_role: str,
    front_text: str,
    back_text: str,
    options: Optional[List[str]],
    issues: List[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Repair S2 card synchronously.
    
    Returns:
        (improved_card_dict, error_message)
    """
    # Build issues text
    issues_text = ""
    for i, issue in enumerate(issues, 1):
        severity = issue.get("severity", "unknown")
        issue_type = issue.get("type", "unknown")
        description = issue.get("description", "")
        suggested_fix = issue.get("suggested_fix", "")
        issue_code = issue.get("issue_code", "")
        
        issues_text += f"\n[Issue {i}]\n"
        issues_text += f"- Severity: {severity}\n"
        issues_text += f"- Type: {issue_type}\n"
        issues_text += f"- Code: {issue_code}\n"
        issues_text += f"- Description: {description}\n"
        if suggested_fix:
            issues_text += f"- Suggested Fix: {suggested_fix}\n"
    
    # System prompt
    system_prompt = """You are an expert medical education content repair agent specializing in radiology flashcards.

TASK: Fix factual/anatomical errors in Anki card text based on S5 validation feedback.

CONSTRAINTS:
1. PRESERVE card structure (MCQ format, option count)
2. ONLY fix the specific issues mentioned
3. Maintain educational value and board-exam relevance
4. Use precise medical terminology

OUTPUT FORMAT: JSON with improved_front, improved_back, improved_options"""
    
    # User prompt
    options_text = ""
    if options:
        options_text = "\nOptions:\n" + "\n".join(f"  {i+1}. {opt}" for i, opt in enumerate(options))
    
    user_prompt = f"""ORIGINAL CARD:
Front: {front_text}
Back: {back_text}{options_text}

S5 VALIDATION ISSUES:
{issues_text}

REPAIR INSTRUCTIONS:
- Fix only the issues mentioned above
- Maintain card structure and format
- Use precise medical terminology
- Ensure educational clarity

Generate improved card text with corrections applied."""
    
    # Response schema
    response_schema = {
        "type": "object",
        "properties": {
            "improved_front": {"type": "string"},
            "improved_back": {"type": "string"},
            "changes_summary": {"type": "string"},
            "confidence": {"type": "number"}
        },
        "required": ["improved_front", "improved_back"]
    }
    
    if options:
        response_schema["properties"]["improved_options"] = {
            "type": "array",
            "items": {"type": "string"}
        }
    
    try:
        response = client.models.generate_content(
            model=S2R_MODEL,
            contents=[{"role": "user", "parts": [{"text": user_prompt}]}],
            config={
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "temperature": S2R_TEMPERATURE,
                "response_mime_type": "application/json",
                "response_schema": response_schema
            }
        )
        
        # Parse response
        text = response.text
        result = json.loads(text)
        
        improved_front = result.get("improved_front", "")
        improved_back = result.get("improved_back", "")
        
        if not improved_front or not improved_back:
            return None, "Empty improved card text"
        
        improved_card = {
            "improved_front": improved_front,
            "improved_back": improved_back,
        }
        
        if options and "improved_options" in result:
            improved_card["improved_options"] = result["improved_options"]
        
        improved_card["confidence"] = result.get("confidence", 0.0)
        
        return improved_card, None
        
    except Exception as e:
        return None, str(e)


# =========================
# Main
# =========================

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="S1R/S2R Text Repair Agent (Synchronous Fallback)"
    )
    parser.add_argument("--base_dir", type=Path, default=Path("."),
                        help="Base directory")
    parser.add_argument("--run_tag", type=str, required=True,
                        help="Run tag")
    parser.add_argument("--arm", type=str, required=True,
                        help="Arm")
    parser.add_argument("--mode", type=str, default="sync",
                        help="Mode (sync)")
    parser.add_argument("--only_entity_id", type=str, action="append", dest="only_entity_ids",
                        help="Only process this entity ID")
    
    args = parser.parse_args()
    
    print("="*80)
    print("S1R/S2R Text Repair Agent (Synchronous)")
    print("="*80)
    print(f"RUN_TAG: {args.run_tag}")
    print(f"ARM: {args.arm}")
    if args.only_entity_ids:
        print(f"Filter: Only entity IDs: {', '.join(args.only_entity_ids)}")
    print()
    
    # Load .env
    env_path = args.base_dir / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
    
    # Initialize client
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        print("Error: No API key found", file=sys.stderr)
        return 1
    
    if not GEMINI_AVAILABLE:
        print("Error: google.genai not available", file=sys.stderr)
        return 1
    
    client = genai.Client(api_key=api_key)
    
    print("✓ Synchronous repair agent ready")
    print("  Note: For large-scale repairs (50+ items), use batch_text_repair.py instead")
    print()
    
    # TODO: Implement synchronous repair logic
    # For now, just show that the agent is ready
    
    print("="*80)
    print("✓ Agent initialized successfully")
    print("="*80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

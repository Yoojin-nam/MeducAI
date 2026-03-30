"""
MeducAI - Batch Text Repair (S1R + S2R via Gemini Batch API)

이 스크립트는 S5 validation 결과를 기반으로 S1 테이블 및 S2 카드의 텍스트를 수정합니다.
Google Gemini Batch API를 사용하여 비용 절감(50%) 및 RPM 제한 우회를 달성합니다.

Usage:
    # Submit batch for repair
    python batch_text_repair.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G --mode mixed --submit
    
    # Check status
    python batch_text_repair.py --check_status
    
    # Download results and apply
    python batch_text_repair.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G --download_and_apply
    
    # Retry failed requests
    python batch_text_repair.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G --retry_failed

Requirements:
    - google-genai>=1.56.0
    - GOOGLE_API_KEY environment variables
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Error: google.genai not available. Install: pip install google-genai")

from dotenv import load_dotenv

# API Key Rotator
ApiKeyRotator = None
ROTATOR_AVAILABLE = False
try:
    _THIS_DIR = Path(__file__).resolve().parent
    _SRC_DIR = _THIS_DIR.parent.parent  # 3_Code/src/
    sys.path.insert(0, str(_SRC_DIR))
    from tools.api_key_rotator import ApiKeyRotator  # type: ignore
    ROTATOR_AVAILABLE = True
except Exception as e:
    print(f"Warning: Could not import ApiKeyRotator: {e}")

# =========================
# Configuration
# =========================

# Tier 1 Batch Limit: 2,000,000 tokens
TIER1_BATCH_TOKEN_LIMIT = 2_000_000

# Default models
S1R_MODEL = "gemini-3-pro-preview"  # For table repair
S2R_MODEL = "gemini-3-flash-preview"  # For card repair

# Temperature settings
S1R_TEMPERATURE = 0.2
S2R_TEMPERATURE = 0.3

# Max output tokens (increased to model limits to avoid truncation)
# Reference: Gemini_3.md - gemini-3-pro-preview: 64k, flash: 64k
S1R_MAX_OUTPUT_TOKENS = 64000  # Pro model max
S2R_MAX_OUTPUT_TOKENS = 64000  # Flash model max (same as Pro)

# Batch tracking file
def get_batch_tracking_file_path(base_dir: Path, run_tag: str) -> Path:
    """배치 추적 파일 경로를 반환합니다."""
    return base_dir / "2_Data" / "metadata" / "generated" / run_tag / ".batch_text_repair_tracking.json"

# Global rotator instance
_global_rotator: Optional[Any] = None


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
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse JSON line: {e}", file=sys.stderr)
                continue
    
    return records


def write_jsonl(file_path: Path, records: List[Dict[str, Any]]) -> None:
    """Write records to a JSONL file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        for record in records:
            json_line = json.dumps(record, ensure_ascii=False)
            f.write(json_line + "\n")


def compute_hash(text: str) -> str:
    """Compute SHA-256 hash of text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


# =========================
# S5 Validation Processing
# =========================

def extract_s1_repair_targets(
    s5_results: List[Dict[str, Any]],
    table_score_threshold: float = 80.0,
    accuracy_threshold: float = 1.0,  # Fallback threshold for backward compatibility
) -> List[Dict[str, Any]]:
    """
    Extract S1 tables that need repair based on S5 validation results.
    
    Uses table_regeneration_trigger_score < threshold as the primary criterion (if available).
    Falls back to technical_accuracy < 1.0 for backward compatibility with older S5 files.
    
    Args:
        s5_results: List of S5 validation records (one per group)
        table_score_threshold: Trigger score threshold (default: 80.0)
        accuracy_threshold: TA threshold for fallback mode (default: 1.0)
        
    Returns:
        List of repair target dicts with:
            - group_id
            - table_regeneration_trigger_score (if available)
            - technical_accuracy
            - issues (list of issue dicts)
    """
    repair_targets = []
    
    for group_result in s5_results:
        group_id = str(group_result.get("group_id", "")).strip()
        if not group_id:
            continue
        
        # Extract S1 table validation
        s1_val = group_result.get("s1_table_validation", {})
        
        # Check if trigger score is available (new S5 validation format)
        trigger_score = s1_val.get("table_regeneration_trigger_score")
        
        if trigger_score is not None:
            # Use trigger score (preferred method)
            if trigger_score >= table_score_threshold:
                # No repair needed (score is high enough)
                continue
        else:
            # Fallback: Use TA < 1.0 (backward compatibility)
            ta = s1_val.get("technical_accuracy")
            if ta is None or ta >= accuracy_threshold:
                # No repair needed
                continue
        
        issues = s1_val.get("issues", [])
        if not issues:
            ta = s1_val.get("technical_accuracy")
            score_info = f"trigger_score={trigger_score}" if trigger_score is not None else f"TA={ta}"
            print(f"[S1R] Warning: Group {group_id} has {score_info} but no issues. Skipping.")
            continue
        
        repair_targets.append({
            "group_id": group_id,
            "table_regeneration_trigger_score": trigger_score,
            "technical_accuracy": s1_val.get("technical_accuracy"),
            "issues": issues,
        })
    
    return repair_targets


def extract_s2_repair_targets(
    s5_results: List[Dict[str, Any]],
    card_score_threshold: float = 80.0,
) -> List[Dict[str, Any]]:
    """
    Extract S2 cards that need repair based on S5 validation results.
    
    Uses card_regeneration_trigger_score < threshold as the criterion.
    This score considers card text quality only (TA 50% + EQ 50%).
    
    Args:
        s5_results: List of S5 validation records (one per group)
        card_score_threshold: Only repair if card_regeneration_trigger_score < threshold (default: 80.0)
        
    Returns:
        List of repair target dicts with:
            - group_id
            - entity_id
            - card_role
            - card_regeneration_trigger_score
            - technical_accuracy (for reference)
            - issues (list of issue dicts)
    """
    repair_targets = []
    
    for group_result in s5_results:
        group_id = str(group_result.get("group_id", "")).strip()
        if not group_id:
            continue
        
        # Extract cards from s2_cards_validation
        s2_cards_validation = group_result.get("s2_cards_validation", {})
        cards = s2_cards_validation.get("cards", [])
        
        for card in cards:
            entity_id = str(card.get("entity_id", "")).strip()
            card_role = str(card.get("card_role", "")).strip()
            
            if not entity_id or not card_role:
                continue
            
            # Check card_regeneration_trigger_score (0-100 scale)
            card_score = card.get("card_regeneration_trigger_score")
            if card_score is None or card_score >= card_score_threshold:
                # No repair needed (score is high enough)
                continue
            
            issues = card.get("issues", [])
            if not issues:
                print(f"[S2R] Warning: Card {group_id}/{entity_id}/{card_role} has card_score={card_score} but no issues. Skipping.")
                continue
            
            repair_targets.append({
                "group_id": group_id,
                "entity_id": entity_id,
                "card_role": card_role,
                "card_regeneration_trigger_score": card_score,
                "technical_accuracy": card.get("technical_accuracy"),  # For reference
                "issues": issues,
            })
    
    return repair_targets


# =========================
# Batch Request Builder
# =========================

def build_s1r_batch_request(
    group_id: str,
    master_table_markdown_kr: str,
    issues: List[Dict[str, Any]],
) -> Tuple[str, Dict[str, Any]]:
    """
    Build a Gemini Batch API request for S1 table repair.
    
    Args:
        group_id: Group ID
        master_table_markdown_kr: Original table markdown
        issues: List of S5 validation issues
        
    Returns:
        (request_key, request_dict)
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
    
    # Request key
    request_key = f"s1r_{group_id}"
    
    # Build request - Follow official Batch API format
    # Reference: Batch API docs - system_instruction, tools, generation_config go directly in request
    request_dict = {
        "key": request_key,
        "request": {
            "contents": [{
                "parts": [{"text": user_prompt}],
                "role": "user"
            }],
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "tools": [{"google_search": {}}],
            "generation_config": {
                "temperature": S1R_TEMPERATURE,
                "max_output_tokens": S1R_MAX_OUTPUT_TOKENS,
                "response_mime_type": "application/json",
                "response_schema": {
                    "type": "OBJECT",
                    "properties": {
                        "improved_table_markdown": {"type": "STRING"},
                        "changes_summary": {"type": "STRING"},
                        "confidence": {"type": "NUMBER"}
                    },
                    "required": ["improved_table_markdown"]
                }
            }
        }
    }
    
    return request_key, request_dict


def build_s2r_batch_request(
    group_id: str,
    entity_id: str,
    card_role: str,
    front_text: str,
    back_text: str,
    options: Optional[List[str]],
    issues: List[Dict[str, Any]],
) -> Tuple[str, Dict[str, Any]]:
    """
    Build a Gemini Batch API request for S2 card repair.
    
    Args:
        group_id: Group ID
        entity_id: Entity ID
        card_role: Card role
        front_text: Original front text
        back_text: Original back text
        options: MCQ options (if applicable)
        issues: List of S5 validation issues
        
    Returns:
        (request_key, request_dict)
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
    
    # Request key
    request_key = f"s2r_{group_id}_{entity_id}_{card_role}"
    
    # Response schema (use uppercase types for Gemini Batch API)
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "improved_front": {"type": "STRING"},
            "improved_back": {"type": "STRING"},
            "changes_summary": {"type": "STRING"},
            "confidence": {"type": "NUMBER"}
        },
        "required": ["improved_front", "improved_back"]
    }
    
    # Add options if MCQ
    if options:
        response_schema["properties"]["improved_options"] = {
            "type": "ARRAY",
            "items": {"type": "STRING"}
        }
    
    # Build request - Follow official Batch API format
    # Reference: Batch API docs - system_instruction, tools, generation_config go directly in request
    request_dict = {
        "key": request_key,
        "request": {
            "contents": [{
                "parts": [{"text": user_prompt}],
                "role": "user"
            }],
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "tools": [{"google_search": {}}],
            "generation_config": {
                "temperature": S2R_TEMPERATURE,
                "max_output_tokens": S2R_MAX_OUTPUT_TOKENS,
                "response_mime_type": "application/json",
                "response_schema": response_schema
            }
        }
    }
    
    return request_key, request_dict


def prepare_batch_requests(
    base_dir: Path,
    run_tag: str,
    arm: str,
    mode: str = "mixed",  # "s1r", "s2r", "mixed"
    only_entity_ids: Optional[List[str]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Prepare batch requests based on S5 validation results.
    
    Args:
        base_dir: Project base directory
        run_tag: Run tag (e.g., FINAL_DISTRIBUTION)
        arm: Arm identifier (e.g., G)
        mode: Repair mode ("s1r", "s2r", "mixed")
        only_entity_ids: Filter to specific entity IDs (for testing)
        
    Returns:
        (batch_requests, prompts_metadata)
    """
    data_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    
    s5_path = data_dir / f"s5_validation__arm{arm}.jsonl"
    s1_path = data_dir / f"stage1_struct__arm{arm}.jsonl"
    s2_path = data_dir / f"s2_results__s1arm{arm}__s2arm{arm}.jsonl"
    
    # Load data
    print("[Step 1] Loading S5 validation results...")
    if not s5_path.exists():
        print(f"Error: S5 validation file not found: {s5_path}", file=sys.stderr)
        return [], []
    
    s5_results = load_jsonl(s5_path)
    print(f"  Loaded {len(s5_results)} group(s) from S5 validation")
    
    print("\n[Step 2] Loading S1/S2 baseline data...")
    s1_rows = load_jsonl(s1_path) if s1_path.exists() else []
    s2_rows = load_jsonl(s2_path) if s2_path.exists() else []
    print(f"  Loaded {len(s1_rows)} S1 row(s), {len(s2_rows)} S2 row(s)")
    
    # Build lookup dicts
    s1_dict = {row["group_id"]: row for row in s1_rows if "group_id" in row}
    
    s2_dict: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for row in s2_rows:
        group_id = row.get("group_id", "")
        entity_id = row.get("entity_id", "")
        for card in row.get("anki_cards", []):
            card_role = card.get("card_role", "")
            key = (group_id, entity_id, card_role)
            s2_dict[key] = card
    
    # Extract repair targets
    print("\n[Step 3] Extracting repair targets...")
    s1_targets = []
    s2_targets = []
    
    if mode in ["s1r", "mixed"]:
        s1_targets = extract_s1_repair_targets(s5_results, table_score_threshold=80.0, accuracy_threshold=1.0)
        # Check if any targets have trigger scores (new format) or using fallback (TA)
        targets_with_score = sum(1 for t in s1_targets if t.get("table_regeneration_trigger_score") is not None)
        if targets_with_score > 0:
            print(f"  Found {len(s1_targets)} S1 table(s) needing repair (trigger_score < 80)")
        else:
            print(f"  Found {len(s1_targets)} S1 table(s) needing repair (TA < 1.0, fallback mode)")
    
    if mode in ["s2r", "mixed"]:
        s2_targets = extract_s2_repair_targets(s5_results, card_score_threshold=80.0)
        
        # Filter by entity_ids if specified
        # Note: S5 uses "DERIVED:xxx" format, but user may provide "xxx" or "DERIVED:xxx"
        if only_entity_ids:
            # Normalize user input: add "DERIVED:" prefix if not present
            normalized_ids = set()
            for eid in only_entity_ids:
                if eid.startswith("DERIVED:"):
                    normalized_ids.add(eid)
                else:
                    normalized_ids.add(f"DERIVED:{eid}")
            
            s2_targets = [t for t in s2_targets if t["entity_id"] in normalized_ids]
            print(f"  Filtered to {len(s2_targets)} S2 card(s) (only_entity_ids filter)")
            if len(s2_targets) == 0 and only_entity_ids:
                print(f"  ⚠️  Warning: No cards found for specified entity IDs")
                print(f"     Provided: {', '.join(only_entity_ids)}")
                print(f"     Note: S5 uses 'DERIVED:' prefix (e.g., 'DERIVED:a80baa3eb411')")
        else:
            print(f"  Found {len(s2_targets)} S2 card(s) needing repair (card_regeneration_trigger_score < 80)")
    
    if not s1_targets and not s2_targets:
        print("\n✓ No repairs needed. Done.")
        return [], []
    
    # Build batch requests
    print("\n[Step 4] Building batch requests...")
    batch_requests = []
    prompts_metadata = []
    
    # S1R requests
    for target in s1_targets:
        group_id = target["group_id"]
        s1_row = s1_dict.get(group_id)
        
        if not s1_row:
            print(f"  Warning: S1 row not found for group {group_id}. Skipping.")
            continue
        
        master_table = s1_row.get("master_table_markdown_kr", "")
        if not master_table:
            print(f"  Warning: Master table empty for group {group_id}. Skipping.")
            continue
        
        request_key, request_dict = build_s1r_batch_request(
            group_id=group_id,
            master_table_markdown_kr=master_table,
            issues=target["issues"],
        )
        
        batch_requests.append(request_dict)
        prompts_metadata.append({
            "key": request_key,
            "type": "s1_table",
            "group_id": group_id,
            "prompt_hash": compute_hash(json.dumps(request_dict)),
        })
    
    # S2R requests
    for target in s2_targets:
        group_id = target["group_id"]
        entity_id = target["entity_id"]
        card_role = target["card_role"]
        
        key = (group_id, entity_id, card_role)
        card = s2_dict.get(key)
        
        if not card:
            print(f"  Warning: S2 card not found for {group_id}/{entity_id}/{card_role}. Skipping.")
            continue
        
        front_text = card.get("front", "")
        back_text = card.get("back", "")
        options = card.get("options")  # May be None
        
        if not front_text or not back_text:
            print(f"  Warning: Card text empty for {group_id}/{entity_id}/{card_role}. Skipping.")
            continue
        
        request_key, request_dict = build_s2r_batch_request(
            group_id=group_id,
            entity_id=entity_id,
            card_role=card_role,
            front_text=front_text,
            back_text=back_text,
            options=options,
            issues=target["issues"],
        )
        
        batch_requests.append(request_dict)
        prompts_metadata.append({
            "key": request_key,
            "type": "s2_card",
            "group_id": group_id,
            "entity_id": entity_id,
            "card_role": card_role,
            "prompt_hash": compute_hash(json.dumps(request_dict)),
        })
    
    print(f"  Built {len(batch_requests)} batch request(s)")
    print(f"    S1R: {len(s1_targets)}, S2R: {len(batch_requests) - len(s1_targets)}")
    
    return batch_requests, prompts_metadata


# =========================
# Batch Tracking
# =========================

def load_batch_tracking_file(tracking_path: Path) -> Dict[str, Any]:
    """
    Load batch tracking file.
    """
    if not tracking_path.exists():
        return {
            "schema_version": "TEXT_REPAIR_BATCH_v1.0",
            "batches": {},
            "failed_requests": [],
            "last_updated": datetime.now().isoformat(),
        }
    
    try:
        with open(tracking_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "schema_version" not in data:
                data["schema_version"] = "TEXT_REPAIR_BATCH_v1.0"
            if "batches" not in data:
                data["batches"] = {}
            if "failed_requests" not in data:
                data["failed_requests"] = []
            return data
    except Exception as e:
        print(f"⚠️  Warning: Error loading tracking file: {e}, creating new one")
        return {
            "schema_version": "TEXT_REPAIR_BATCH_v1.0",
            "batches": {},
            "failed_requests": [],
            "last_updated": datetime.now().isoformat(),
        }


def save_batch_tracking_file(tracking_path: Path, data: Dict[str, Any]) -> bool:
    """Save batch tracking file."""
    try:
        tracking_path.parent.mkdir(parents=True, exist_ok=True)
        data["last_updated"] = datetime.now().isoformat()
        with open(tracking_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error saving tracking file: {e}")
        return False


# =========================
# Batch Submission
# =========================

def submit_batch_with_retry(
    client: Any,
    batch_requests: List[Dict[str, Any]],
    prompts_metadata: List[Dict[str, Any]],
    rotator: Any,
    max_retries: int = 3,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Submit batch with automatic retry on 404/429 errors.
    
    Returns:
        (batch_id, file_name, error_message)
    """
    uploaded_file_name = None
    temp_file_path = None
    
    for attempt in range(max_retries):
        try:
            # Upload file
            print(f"    Uploading requests file (attempt {attempt + 1}/{max_retries})...")
            
            # Create temporary JSONL file
            # Reference: Batch API docs, lines 929-942 (write to file first)
            if temp_file_path is None:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    suffix=".jsonl",
                    delete=False,
                ) as f:
                    for req in batch_requests:
                        f.write(json.dumps(req, ensure_ascii=False) + "\n")
                    temp_file_path = f.name
            
            # Upload file - Use official API format
            # Reference: Batch API docs, lines 938-942
            uploaded_file = client.files.upload(
                file=temp_file_path,  # Pass file path, not bytes
                config={
                    "display_name": f"text_repair_requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl",
                    "mime_type": "jsonl",
                }
            )
            uploaded_file_name = uploaded_file.name
            print(f"    ✓ File uploaded: {uploaded_file_name}")
            
            # Create batch job - Use uploaded_file.name as src
            # Reference: Batch API docs, lines 252-260
            print(f"    Creating batch job...")
            batch = client.batches.create(
                model=S1R_MODEL,  # Model is specified per-request in config
                src=uploaded_file_name,  # Use file name, not URI
                config={
                    "display_name": f"text_repair_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                }
            )
            
            batch_id = batch.name
            print(f"    ✓ Batch created: {batch_id}")
            
            # Record success
            if rotator:
                rotator.record_success()
            
            # Clean up temp file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass
            
            return batch_id, uploaded_file_name, None
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for 404 (file not found after key rotation)
            if "404" in error_str:
                print(f"    ❌ Error 404: File not found. Re-uploading...")
                uploaded_file_name = None  # Force re-upload
                continue
            
            # Check for 429 (quota exhausted)
            elif "429" in error_str or "quota" in error_str:
                print(f"    ❌ Error 429: Quota exhausted. Rotating API key...")
                if rotator:
                    try:
                        new_key, new_index = rotator.rotate_on_quota_exhausted(str(e))
                        print(f"    ✓ Rotated to key index {new_index}")
                        
                        # Rebuild client with new key
                        client = genai.Client(api_key=new_key)
                        
                        # Force re-upload with new key
                        uploaded_file_name = None
                        continue
                    except RuntimeError as re:
                        # All keys exhausted
                        error_msg = f"All API keys exhausted: {re}"
                        print(f"    ❌ {error_msg}")
                        return None, None, error_msg
                else:
                    error_msg = f"Quota exhausted but no rotator available: {e}"
                    print(f"    ❌ {error_msg}")
                    return None, None, error_msg
            
            # Other errors
            else:
                error_msg = f"Unexpected error: {e}"
                print(f"    ❌ {error_msg}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"    Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    return None, None, error_msg
    
    # Clean up temp file on failure
    if temp_file_path and os.path.exists(temp_file_path):
        try:
            os.unlink(temp_file_path)
        except Exception:
            pass
    
    return None, None, "Max retries exceeded"


def submit_batch_job(
    base_dir: Path,
    run_tag: str,
    arm: str,
    mode: str = "mixed",
    only_entity_ids: Optional[List[str]] = None,
) -> int:
    """
    Submit batch job for text repair.
    
    Args:
        base_dir: Project base directory
        run_tag: Run tag (e.g., FINAL_DISTRIBUTION)
        arm: Arm identifier (e.g., G)
        mode: Repair mode ("s1r", "s2r", "mixed")
        only_entity_ids: Filter to specific entity IDs (for testing)
        
    Returns:
        Exit code (0 = success)
    """
    print("="*80)
    print("Batch Text Repair - Submit")
    print("="*80)
    print(f"RUN_TAG: {run_tag}")
    print(f"ARM: {arm}")
    print(f"Mode: {mode}")
    if only_entity_ids:
        print(f"Filter: Only entity IDs: {', '.join(only_entity_ids)}")
    print()
    
    # Load .env
    env_path = base_dir / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
    
    # Initialize rotator
    global _global_rotator
    if ROTATOR_AVAILABLE and ApiKeyRotator:
        _global_rotator = ApiKeyRotator(base_dir=base_dir)
        api_key = _global_rotator.get_current_key()
    else:
        api_key = os.getenv("GOOGLE_API_KEY", "").strip()
        if not api_key:
            print("Error: No API key found", file=sys.stderr)
            return 1
    
    # Initialize client
    if not GEMINI_AVAILABLE:
        print("Error: google.genai not available", file=sys.stderr)
        return 1
    
    client = genai.Client(api_key=api_key)
    
    # Prepare batch requests
    batch_requests, prompts_metadata = prepare_batch_requests(
        base_dir=base_dir,
        run_tag=run_tag,
        arm=arm,
        mode=mode,
        only_entity_ids=only_entity_ids,
    )
    
    if not batch_requests:
        print("\n✓ No repairs needed. Done.")
        return 0
    
    # Submit batch
    print("\n[Step 5] Submitting batch job...")
    batch_id, file_name, error = submit_batch_with_retry(
        client=client,
        batch_requests=batch_requests,
        prompts_metadata=prompts_metadata,
        rotator=_global_rotator,
    )
    
    if error:
        print(f"\n❌ Error: Failed to submit batch: {error}")
        return 1
    
    # Save tracking data
    print("\n[Step 6] Saving tracking data...")
    tracking_path = get_batch_tracking_file_path(base_dir, run_tag)
    tracking_data = load_batch_tracking_file(tracking_path)
    
    # Get API key hash
    api_key_hash = compute_hash(api_key)
    
    # Add batch to tracking
    if api_key_hash not in tracking_data["batches"]:
        tracking_data["batches"][api_key_hash] = {"chunks": []}
    
    tracking_data["batches"][api_key_hash]["chunks"].append({
        "batch_id": batch_id,
        "status": "JOB_STATE_PENDING",
        "mode": mode,
        "file_name": file_name,  # Store file name, not URI
        "prompts_metadata": prompts_metadata,
        "created_at": datetime.now().isoformat(),
        "request_count": len(batch_requests),
    })
    
    tracking_data["run_tag"] = run_tag
    tracking_data["arm"] = arm
    
    save_batch_tracking_file(tracking_path, tracking_data)
    print(f"  ✓ Tracking data saved to: {tracking_path.name}")
    
    print("\n" + "="*80)
    print("✓ Batch submitted successfully")
    print(f"  Batch ID: {batch_id}")
    print(f"  Requests: {len(batch_requests)}")
    print(f"  Expected completion: ~10-15 minutes")
    print("="*80)
    
    return 0


# =========================
# Status Check
# =========================

def check_batch_status(base_dir: Path) -> int:
    """
    Check status of all batch jobs.
    Uses correct API key for each batch based on tracking data.
    
    Returns:
        Exit code (0 = success)
    """
    print("="*80)
    print("Batch Text Repair - Status Check")
    print("="*80)
    
    # Find all tracking files
    metadata_dir = base_dir / "2_Data" / "metadata" / "generated"
    tracking_files = list(metadata_dir.glob("*/.batch_text_repair_tracking.json"))
    
    if not tracking_files:
        print("\nNo batch tracking files found.")
        return 0
    
    print(f"\nFound {len(tracking_files)} tracking file(s)\n")
    
    # Load .env
    env_path = base_dir / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
    
    # Initialize rotator to get all available keys
    global _global_rotator
    if ROTATOR_AVAILABLE and ApiKeyRotator:
        _global_rotator = ApiKeyRotator(base_dir=base_dir)
    
    # Build API key lookup: hash -> actual key
    api_key_lookup = {}
    if _global_rotator:
        for i, key in enumerate(_global_rotator.keys):
            key_hash = compute_hash(key)
            api_key_lookup[key_hash] = key
    else:
        # Single key fallback
        single_key = os.getenv("GOOGLE_API_KEY", "").strip()
        if single_key:
            key_hash = compute_hash(single_key)
            api_key_lookup[key_hash] = single_key
    
    if not api_key_lookup:
        print("Error: No API keys found", file=sys.stderr)
        return 1
    
    # Check each tracking file
    for tracking_path in tracking_files:
        run_tag = tracking_path.parent.name
        print(f"Run Tag: {run_tag}")
        print("-" * 60)
        
        tracking_data = load_batch_tracking_file(tracking_path)
        
        if not tracking_data.get("batches"):
            print("  No batches found\n")
            continue
        
        # Check each batch with its original API key
        for api_key_hash, api_batch in tracking_data["batches"].items():
            chunks = api_batch.get("chunks", [])
            
            # Get the API key for this batch
            api_key = api_key_lookup.get(api_key_hash)
            if not api_key:
                print(f"  ⚠️  Warning: API key not found for hash {api_key_hash[:8]}... (may be rotated out)")
                # Try with current key as fallback
                api_key = list(api_key_lookup.values())[0] if api_key_lookup else None
                if not api_key:
                    continue
            
            # Create client with correct key
            client = genai.Client(api_key=api_key)
            
            for i, chunk in enumerate(chunks):
                batch_id = chunk.get("batch_id", "")
                status = chunk.get("status", "UNKNOWN")
                mode = chunk.get("mode", "")
                request_count = chunk.get("request_count", 0)
                created_at = chunk.get("created_at", "")
                
                print(f"  Batch {i+1}: {batch_id}")
                print(f"    Mode: {mode}")
                print(f"    Status: {status}")
                print(f"    Requests: {request_count}")
                print(f"    Created: {created_at}")
                print(f"    API Key: ...{api_key_hash[:8]}")
                
                # Query current status with correct key
                try:
                    batch = client.batches.get(name=batch_id)
                    # Handle both enum and string status - use type: ignore for dynamic API
                    current_status = "UNKNOWN"
                    if hasattr(batch, 'state'):
                        state = batch.state  # type: ignore[attr-defined]
                        if hasattr(state, 'name'):
                            current_status = state.name  # type: ignore[attr-defined]
                        else:
                            current_status = str(state)
                    
                    if current_status != status:
                        print(f"    Updated Status: {current_status}")
                        chunk["status"] = current_status
                        
                        if current_status == "JOB_STATE_SUCCEEDED":
                            chunk["completed_at"] = datetime.now().isoformat()
                            print(f"    ✓ Batch completed!")
                        elif current_status == "JOB_STATE_FAILED":
                            print(f"    ❌ Batch failed")
                    
                except Exception as e:
                    error_str = str(e)
                    if "404" in error_str:
                        print(f"    ⚠️  404 Error: Batch not found with this key (may need different key)")
                    else:
                        print(f"    ❌ Error querying status: {e}")
                
                print()
        
        # Save updated tracking data
        save_batch_tracking_file(tracking_path, tracking_data)
    
    print("="*80)
    return 0


# =========================
# Result Download and Apply
# =========================

def download_and_apply_results(
    base_dir: Path,
    run_tag: str,
    arm: str,
) -> int:
    """
    Download batch results and apply to original JSONL files.
    Uses correct API key for each batch based on tracking data.
    
    Args:
        base_dir: Project base directory
        run_tag: Run tag (e.g., FINAL_DISTRIBUTION)
        arm: Arm identifier (e.g., G)
        
    Returns:
        Exit code (0 = success)
    """
    print("="*80)
    print("Batch Text Repair - Download and Apply")
    print("="*80)
    print(f"RUN_TAG: {run_tag}")
    print(f"ARM: {arm}\n")
    
    # Load .env
    env_path = base_dir / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
    
    # Initialize rotator to get all available keys
    global _global_rotator
    if ROTATOR_AVAILABLE and ApiKeyRotator:
        _global_rotator = ApiKeyRotator(base_dir=base_dir)
    
    # Build API key lookup: hash -> actual key
    api_key_lookup = {}
    if _global_rotator:
        for i, key in enumerate(_global_rotator.keys):
            key_hash = compute_hash(key)
            api_key_lookup[key_hash] = key
    else:
        # Single key fallback
        single_key = os.getenv("GOOGLE_API_KEY", "").strip()
        if single_key:
            key_hash = compute_hash(single_key)
            api_key_lookup[key_hash] = single_key
    
    if not api_key_lookup:
        print("Error: No API keys found", file=sys.stderr)
        return 1
    
    # Load tracking file
    tracking_path = get_batch_tracking_file_path(base_dir, run_tag)
    tracking_data = load_batch_tracking_file(tracking_path)
    
    if not tracking_data.get("batches"):
        print("No batches found in tracking file.")
        return 0
    
    # Find succeeded batches with their API keys
    succeeded_batches = []
    for api_key_hash, api_batch in tracking_data["batches"].items():
        for chunk in api_batch.get("chunks", []):
            if chunk.get("status") == "JOB_STATE_SUCCEEDED":
                succeeded_batches.append({
                    "chunk": chunk,
                    "api_key_hash": api_key_hash,
                })
    
    if not succeeded_batches:
        print("No succeeded batches found.")
        return 0
    
    print(f"Found {len(succeeded_batches)} succeeded batch(es)\n")
    
    # Download and parse results
    print("[Step 1] Downloading batch results...")
    s1_improvements: Dict[str, str] = {}
    s2_improvements: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    
    for i, batch_info in enumerate(succeeded_batches, 1):
        chunk = batch_info["chunk"]
        api_key_hash = batch_info["api_key_hash"]
        batch_id = chunk.get("batch_id", "")
        
        print(f"  [{i}/{len(succeeded_batches)}] Batch: {batch_id}")
        print(f"    API Key: ...{api_key_hash[:8]}")
        
        # Get the correct API key for this batch
        api_key = api_key_lookup.get(api_key_hash)
        if not api_key:
            print(f"    ⚠️  Warning: API key not found for hash {api_key_hash[:8]}...")
            print(f"    Skipping this batch")
            continue
        
        # Create client with correct key
        client = genai.Client(api_key=api_key)
        
        try:
            # Get batch with correct key
            batch = client.batches.get(name=batch_id)
            
            # Download results using official API method
            # Reference: Batch API docs, lines 722-732
            if not hasattr(batch, 'dest') or not batch.dest:
                print(f"    ⚠️  Warning: No destination info (batch may not be complete)")
                continue
            
            # Check for file-based output
            if not hasattr(batch.dest, 'file_name') or not batch.dest.file_name:
                print(f"    ⚠️  Warning: No output file (batch may not be complete)")
                continue
            
            result_file_name = batch.dest.file_name
            print(f"    Downloading results from: {result_file_name}")
            
            # Download file content using official method
            # Reference: Batch API docs, line 730
            file_content_bytes = client.files.download(file=result_file_name)
            
            # Decode to string
            if isinstance(file_content_bytes, bytes):
                result_content = file_content_bytes.decode("utf-8")
            else:
                result_content = str(file_content_bytes)
            
            # Save raw results for debugging
            log_dir = base_dir / "logs"
            log_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            raw_file = log_dir / f"batch_raw_results_{chunk['batch_id'].split('/')[-1]}_{timestamp}.jsonl"
            with open(raw_file, "w", encoding="utf-8") as f:
                f.write(result_content)
            print(f"    💾 Raw results saved to: {raw_file}")
            
            # Parse results
            failed_lines = []
            line_num = 0
            for line in result_content.splitlines():
                line_num += 1
                if not line.strip():
                    continue
                
                try:
                    result = json.loads(line)
                    key = result.get("key", "")
                    response = result.get("response", {})
                    
                    # Extract JSON from response
                    candidates = response.get("candidates", [])
                    if not candidates:
                        continue
                    
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if not parts:
                        continue
                    
                    text = parts[0].get("text", "")
                    if not text:
                        continue
                    
                    # Parse JSON response with enhanced error handling
                    try:
                        improved = json.loads(text)
                    except json.JSONDecodeError as json_err:
                        # Try to extract JSON from markdown code blocks
                        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
                        if json_match:
                            try:
                                improved = json.loads(json_match.group(1))
                            except:
                                failed_lines.append({
                                    "line_num": line_num,
                                    "key": key,
                                    "error": f"Inner JSON parse failed: {json_err}",
                                    "text_preview": text[:200] if text else ""
                                })
                                continue
                        else:
                            failed_lines.append({
                                "line_num": line_num,
                                "key": key,
                                "error": f"Inner JSON parse failed: {json_err}",
                                "text_preview": text[:200] if text else ""
                            })
                            continue
                    
                    # Store by type
                    if key.startswith("s1r_"):
                        group_id = key.replace("s1r_", "")
                        s1_improvements[group_id] = improved.get("improved_table_markdown", "")
                    elif key.startswith("s2r_"):
                        # Parse key: s2r_{group_id}_{entity_id}_{card_role}
                        parts = key.replace("s2r_", "").rsplit("_", 1)
                        card_role = parts[-1]
                        remaining = parts[0].rsplit("_", 1)
                        entity_id = remaining[-1]
                        group_id = remaining[0]
                        
                        s2_improvements[(group_id, entity_id, card_role)] = improved
                
                except json.JSONDecodeError as e:
                    # Outer JSON parse failed
                    failed_lines.append({
                        "line_num": line_num,
                        "key": "unknown",
                        "error": f"Outer JSON parse failed: {e}",
                        "text_preview": line[:200] if line else ""
                    })
                    print(f"    ⚠️  Warning: Error parsing result line {line_num}: {e}")
                    continue
                except Exception as e:
                    failed_lines.append({
                        "line_num": line_num,
                        "key": key if 'key' in locals() else "unknown",
                        "error": str(e),
                        "text_preview": line[:200] if line else ""
                    })
                    print(f"    ⚠️  Warning: Error processing line {line_num}: {e}")
                    continue
            
            print(f"    ✓ Downloaded {len(s1_improvements)} S1, {len(s2_improvements)} S2 result(s)")
            
            # Log failed lines if any
            if failed_lines:
                log_dir = base_dir / "logs"
                log_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file = log_dir / f"batch_parse_errors_{timestamp}.json"
                
                # Group failures by type
                s1_failures = [f for f in failed_lines if f.get("key", "").startswith("s1r_")]
                s2_failures = [f for f in failed_lines if f.get("key", "").startswith("s2r_")]
                unknown_failures = [f for f in failed_lines if not f.get("key", "").startswith(("s1r_", "s2r_"))]
                
                with open(log_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "batch_id": chunk["batch_id"],
                        "timestamp": timestamp,
                        "total_failed": len(failed_lines),
                        "s1_failed": len(s1_failures),
                        "s2_failed": len(s2_failures),
                        "unknown_failed": len(unknown_failures),
                        "failed_lines": failed_lines
                    }, f, indent=2, ensure_ascii=False)
                
                print(f"    ⚠️  {len(failed_lines)} line(s) failed to parse (S1: {len(s1_failures)}, S2: {len(s2_failures)})")
                print(f"    📝 Failed lines logged to: {log_file}")
                
                # Show first few failed keys for user awareness
                if failed_lines[:3]:
                    print(f"    Failed keys (first 3):")
                    for f in failed_lines[:3]:
                        key = f.get("key", "unknown")
                        error = f.get("error", "")[:50]
                        print(f"      - {key}: {error}...")
            
        except Exception as e:
            print(f"    ❌ Error downloading results: {e}")
            continue
    
    print(f"\n  Total: {len(s1_improvements)} S1 improvements, {len(s2_improvements)} S2 improvements\n")
    
    if not s1_improvements and not s2_improvements:
        print("No improvements to apply.")
        return 0
    
    # Apply improvements
    data_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    
    # Apply S1 improvements
    if s1_improvements:
        print("[Step 2] Applying S1 improvements...")
        s1_baseline_path = data_dir / f"stage1_struct__arm{arm}.jsonl"
        s1_regen_path = data_dir / f"stage1_struct__arm{arm}__regen.jsonl"
        
        # Load baseline (read-only)
        s1_rows = load_jsonl(s1_baseline_path)
        
        s1_updated = 0
        for row in s1_rows:
            group_id = row.get("group_id", "")
            if group_id in s1_improvements:
                row["master_table_markdown_kr"] = s1_improvements[group_id]
                row["_repair_metadata"] = {
                    "repaired_at": datetime.now().isoformat(),
                    "method": "batch_s1r"
                }
                s1_updated += 1
        
        # Write to __regen file (preserves baseline)
        write_jsonl(s1_regen_path, s1_rows)
        print(f"  ✓ Updated {s1_updated} S1 table(s)")
        print(f"  ✓ Written to: {s1_regen_path.name}")
    
    # Apply S2 improvements
    if s2_improvements:
        print("\n[Step 3] Applying S2 improvements...")
        s2_baseline_path = data_dir / f"s2_results__s1arm{arm}__s2arm{arm}.jsonl"
        s2_regen_path = data_dir / f"s2_results__s1arm{arm}__s2arm{arm}__regen.jsonl"
        
        # Load baseline (read-only)
        s2_rows = load_jsonl(s2_baseline_path)
        
        s2_updated = 0
        for row in s2_rows:
            group_id = row.get("group_id", "")
            entity_id = row.get("entity_id", "")
            
            for card in row.get("anki_cards", []):
                card_role = card.get("card_role", "")
                key = (group_id, entity_id, card_role)
                
                if key in s2_improvements:
                    improved = s2_improvements[key]
                    card["front"] = improved.get("improved_front", card["front"])
                    card["back"] = improved.get("improved_back", card["back"])
                    if "improved_options" in improved:
                        card["options"] = improved["improved_options"]
                    card["_repair_metadata"] = {
                        "repaired_at": datetime.now().isoformat(),
                        "method": "batch_s2r",
                        "confidence": improved.get("confidence")
                    }
                    s2_updated += 1
        
        # Write to __regen file (preserves baseline)
        write_jsonl(s2_regen_path, s2_rows)
        print(f"  ✓ Updated {s2_updated} S2 card(s)")
        print(f"  ✓ Written to: {s2_regen_path.name}")
    
    print("\n" + "="*80)
    print("✓ Results applied successfully")
    print("="*80)
    
    return 0


# =========================
# Retry Failed Requests
# =========================

def identify_failed_requests(
    base_dir: Path,
    run_tag: str,
    arm: str,
) -> Tuple[List[str], List[Tuple[str, str, str]]]:
    """
    Identify failed requests by comparing submitted vs applied.
    
    Returns:
        (failed_s1_group_ids, failed_s2_keys)
        where failed_s2_keys = [(group_id, entity_id, card_role), ...]
    """
    # Load tracking to get all submitted keys
    tracking_path = get_batch_tracking_file_path(base_dir, run_tag)
    tracking_data = load_batch_tracking_file(tracking_path)
    
    submitted_s1 = set()
    submitted_s2_keys = set()  # (group_id, entity_id, card_role)
    
    for api_key_hash, api_batch in tracking_data.get("batches", {}).items():
        for chunk in api_batch.get("chunks", []):
            for meta in chunk.get("prompts_metadata", []):
                key = meta.get("key", "")
                if key.startswith("s1r_"):
                    group_id = key.replace("s1r_", "")
                    submitted_s1.add(group_id)
                elif key.startswith("s2r_"):
                    # Parse: s2r_{group_id}_{entity_id}_{card_role}
                    parts = key.replace("s2r_", "").rsplit("_", 1)
                    card_role = parts[-1]
                    remaining = parts[0].rsplit("_", 1)
                    entity_id = remaining[-1]
                    group_id = remaining[0]
                    submitted_s2_keys.add((group_id, entity_id, card_role))
    
    # Load applied repairs
    data_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    s1_path = data_dir / f"stage1_struct__arm{arm}.jsonl"
    s2_path = data_dir / f"s2_results__s1arm{arm}__s2arm{arm}.jsonl"
    
    applied_s1 = set()
    for line in open(s1_path):
        data = json.loads(line)
        if "_repair_metadata" in data:
            applied_s1.add(data["group_id"])
    
    applied_s2_keys = set()
    for line in open(s2_path):
        data = json.loads(line)
        group_id = data.get("group_id", "")
        entity_id = data.get("entity_id", "")
        for card in data.get("anki_cards", []):
            if "_repair_metadata" in card:
                card_role = card.get("card_role", "")
                applied_s2_keys.add((group_id, entity_id, card_role))
    
    # Find failed ones
    failed_s1 = list(submitted_s1 - applied_s1)
    failed_s2 = list(submitted_s2_keys - applied_s2_keys)
    
    return failed_s1, failed_s2


def retry_failed_requests(
    base_dir: Path,
    run_tag: str,
    arm: str,
) -> int:
    """
    Retry failed requests from previous batch.
    
    Returns:
        Exit code (0 = success)
    """
    print("="*80)
    print("Batch Text Repair - Retry Failed")
    print("="*80)
    print(f"RUN_TAG: {run_tag}")
    print(f"ARM: {arm}\n")
    
    # Identify failed requests
    print("[Step 1] Identifying failed requests...")
    failed_s1, failed_s2 = identify_failed_requests(base_dir, run_tag, arm)
    
    print(f"  Found {len(failed_s1)} failed S1 table(s)")
    print(f"  Found {len(failed_s2)} failed S2 card(s)")
    
    if not failed_s1 and not failed_s2:
        print("\n✓ No failed requests to retry. All done!")
        return 0
    
    print(f"\n  Total to retry: {len(failed_s1) + len(failed_s2)}")
    
    # Show what will be retried
    if failed_s1:
        print(f"\n  Failed S1 groups:")
        for gid in failed_s1:
            print(f"    - {gid}")
    
    if failed_s2:
        print(f"\n  Failed S2 cards:")
        for group_id, entity_id, card_role in failed_s2[:10]:
            print(f"    - {group_id}/{entity_id}/{card_role}")
        if len(failed_s2) > 10:
            print(f"    ... and {len(failed_s2) - 10} more")
    
    # Load S5, S1, S2 data
    print("\n[Step 2] Loading baseline data...")
    data_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    
    s5_path = data_dir / f"s5_validation__arm{arm}.jsonl"
    s1_path = data_dir / f"stage1_struct__arm{arm}.jsonl"
    s2_path = data_dir / f"s2_results__s1arm{arm}__s2arm{arm}.jsonl"
    
    s5_results = load_jsonl(s5_path)
    s1_rows = load_jsonl(s1_path)
    s2_rows = load_jsonl(s2_path)
    
    # Build lookups
    s1_dict = {row["group_id"]: row for row in s1_rows if "group_id" in row}
    s5_dict = {}
    for s5_row in s5_results:
        gid = s5_row.get("group_id", "")
        s5_dict[gid] = s5_row
    
    s2_dict = {}
    for row in s2_rows:
        group_id = row.get("group_id", "")
        entity_id = row.get("entity_id", "")
        for card in row.get("anki_cards", []):
            card_role = card.get("card_role", "")
            key = (group_id, entity_id, card_role)
            s2_dict[key] = card
    
    # Build retry requests
    print("\n[Step 3] Building retry requests...")
    batch_requests = []
    prompts_metadata = []
    
    # S1 retry
    for group_id in failed_s1:
        s1_row = s1_dict.get(group_id)
        s5_row = s5_dict.get(group_id)
        
        if not s1_row or not s5_row:
            print(f"  Warning: Data not found for S1 group {group_id}")
            continue
        
        master_table = s1_row.get('master_table_markdown_kr', '')
        issues = s5_row.get('s1_table_validation', {}).get('issues', [])
        
        if not master_table or not issues:
            print(f"  Warning: Missing data for S1 group {group_id}")
            continue
        
        request_key, request_dict = build_s1r_batch_request(
            group_id=group_id,
            master_table_markdown_kr=master_table,
            issues=issues,
        )
        
        batch_requests.append(request_dict)
        prompts_metadata.append({
            'key': request_key,
            'type': 's1_table',
            'group_id': group_id,
            'prompt_hash': compute_hash(json.dumps(request_dict)),
        })
    
    # S2 retry
    for group_id, entity_id, card_role in failed_s2:
        key = (group_id, entity_id, card_role)
        card = s2_dict.get(key)
        s5_row = s5_dict.get(group_id)
        
        if not card or not s5_row:
            print(f"  Warning: Data not found for S2 {group_id}/{entity_id}/{card_role}")
            continue
        
        # Find S5 issues for this card
        issues = []
        for s5_card in s5_row.get('s2_cards_validation', {}).get('cards', []):
            if (s5_card.get('entity_id') == entity_id and 
                s5_card.get('card_role') == card_role):
                issues = s5_card.get('issues', [])
                break
        
        if not issues:
            print(f"  Warning: No issues for S2 {group_id}/{entity_id}/{card_role}")
            continue
        
        front_text = card.get('front', '')
        back_text = card.get('back', '')
        options = card.get('options')
        
        request_key, request_dict = build_s2r_batch_request(
            group_id=group_id,
            entity_id=entity_id,
            card_role=card_role,
            front_text=front_text,
            back_text=back_text,
            options=options,
            issues=issues,
        )
        
        batch_requests.append(request_dict)
        prompts_metadata.append({
            'key': request_key,
            'type': 's2_card',
            'group_id': group_id,
            'entity_id': entity_id,
            'card_role': card_role,
            'prompt_hash': compute_hash(json.dumps(request_dict)),
        })
    
    print(f"  Built {len(batch_requests)} retry request(s)")
    
    if not batch_requests:
        print("\n✓ No valid retry requests to submit.")
        return 0
    
    # Submit batch
    print("\n[Step 4] Submitting retry batch...")
    
    # Load .env
    env_path = base_dir / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
    
    # Initialize rotator
    global _global_rotator
    if ROTATOR_AVAILABLE and ApiKeyRotator:
        _global_rotator = ApiKeyRotator(base_dir=base_dir)
        api_key = _global_rotator.get_current_key()
    else:
        api_key = os.getenv("GOOGLE_API_KEY", "").strip()
        if not api_key:
            print("Error: No API key found", file=sys.stderr)
            return 1
    
    if not GEMINI_AVAILABLE:
        print("Error: google.genai not available", file=sys.stderr)
        return 1
    
    client = genai.Client(api_key=api_key)
    
    batch_id, file_name, error = submit_batch_with_retry(
        client=client,
        batch_requests=batch_requests,
        prompts_metadata=prompts_metadata,
        rotator=_global_rotator,
    )
    
    if error:
        print(f"\n❌ Error: Failed to submit retry batch: {error}")
        return 1
    
    # Save tracking data
    print("\n[Step 5] Saving tracking data...")
    tracking_path = get_batch_tracking_file_path(base_dir, run_tag)
    tracking_data = load_batch_tracking_file(tracking_path)
    
    api_key_hash = compute_hash(api_key)
    
    if api_key_hash not in tracking_data["batches"]:
        tracking_data["batches"][api_key_hash] = {"chunks": []}
    
    tracking_data["batches"][api_key_hash]["chunks"].append({
        "batch_id": batch_id,
        "status": "JOB_STATE_PENDING",
        "mode": "retry",
        "file_name": file_name,
        "prompts_metadata": prompts_metadata,
        "created_at": datetime.now().isoformat(),
        "request_count": len(batch_requests),
        "is_retry": True,
    })
    
    save_batch_tracking_file(tracking_path, tracking_data)
    print(f"  ✓ Tracking data saved")
    
    print("\n" + "="*80)
    print("✓ Retry batch submitted successfully")
    print(f"  Batch ID: {batch_id}")
    print(f"  Requests: {len(batch_requests)}")
    print(f"  Expected completion: ~5-10 minutes")
    print("="*80)
    
    return 0


# =========================
# CLI Entry Point
# =========================

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Batch Text Repair - S1R + S2R via Gemini Batch API"
    )
    parser.add_argument("--base_dir", type=Path, default=Path("."),
                        help="Base directory (default: current directory)")
    parser.add_argument("--run_tag", type=str,
                        help="Run tag (e.g., FINAL_DISTRIBUTION)")
    parser.add_argument("--arm", type=str,
                        help="Arm (e.g., G)")
    parser.add_argument("--mode", type=str, default="mixed",
                        choices=["s1r", "s2r", "mixed"],
                        help="Repair mode (default: mixed)")
    parser.add_argument("--only_entity_id", type=str, action="append", dest="only_entity_ids",
                        help="Only process this entity ID (can specify multiple times)")
    
    # Actions
    parser.add_argument("--submit", action="store_true",
                        help="Submit batch job")
    parser.add_argument("--check_status", action="store_true",
                        help="Check status of all batch jobs")
    parser.add_argument("--download_and_apply", action="store_true",
                        help="Download results and apply to JSONL files")
    parser.add_argument("--retry_failed", action="store_true",
                        help="Retry failed requests (requires --run_tag and --arm)")
    
    args = parser.parse_args()
    
    # Validate args
    if args.submit or args.download_and_apply:
        if not args.run_tag or not args.arm:
            print("Error: --run_tag and --arm are required for --submit and --download_and_apply", file=sys.stderr)
            return 1
    
    # Execute action
    if args.submit:
        exit_code = submit_batch_job(
            base_dir=args.base_dir,
            run_tag=args.run_tag,
            arm=args.arm,
            mode=args.mode,
            only_entity_ids=args.only_entity_ids,
        )
    elif args.check_status:
        exit_code = check_batch_status(base_dir=args.base_dir)
    elif args.download_and_apply:
        exit_code = download_and_apply_results(
            base_dir=args.base_dir,
            run_tag=args.run_tag,
            arm=args.arm,
        )
    elif args.retry_failed:
        exit_code = retry_failed_requests(
            base_dir=args.base_dir,
            run_tag=args.run_tag,
            arm=args.arm,
        )
    else:
        parser.print_help()
        exit_code = 0
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

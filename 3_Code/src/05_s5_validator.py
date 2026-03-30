"""
MeducAI Step05 (S5) — LLM-based Validation & Triage

P0 Requirements:
- S5 validates S1 tables and S2 cards for content quality
- Provides evidence and suggestions to human raters (2-pass workflow)
- Never generates, modifies, or auto-corrects upstream content
- No fail-fast stopping (pipeline continues regardless of validation results)

Design Principles:
- S5 is a triage/flagging system (read-only validation)
- Arm-independent model configuration (fixed across arms)
- RAG evidence required when blocking errors flagged
- Reproducible validation results (s5_snapshot_id)

S1 Validation Architecture (per specification):
- Step 1: Table evaluation (always performed)
  - Input: master_table_markdown_kr, objective_bullets
  - Output: blocking_error, technical_accuracy, educational_quality, issues, rag_evidence
  - Prompt: S5_USER_TABLE__v2.md
- Step 2: Infographic evaluation (optional, if infographic exists)
  - Single infographic: 1 LLM call
  - Clustered infographics: up to 4 LLM calls (one per cluster, max 4 clusters)
  - Input: table + infographic image + S3 prompt
  - Output: table_visual_validation (single) or table_visual_validations (list)
  - Prompt: S5_USER_TABLE_VISUAL__v1.md

Model Configuration (S1 validation):
- Model: gemini-3-pro-preview (Pro model, fixed)
- Temperature: 0.2 (configurable via TEMPERATURE_STAGE5 env var)
- Thinking: enabled=true, level="high"
- RAG: enabled=true (required when blocking_error=true)
- Timeout: 300 seconds per LLM call

See docs/s5_s1_validation_specification.md for complete specification.
"""

import argparse
import hashlib
import json
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from tools.s5.s5_validation_payload import build_s2_card_validation_record

try:
    from tools.multi_agent.score_calculator import (
        calculate_s5_regeneration_trigger_score,
        calculate_s5_card_regeneration_trigger_score,
        calculate_s5_image_regeneration_trigger_score,
        calculate_s1_table_regeneration_trigger_score,
    )
except ImportError:
    # Fallback: define stub functions if score_calculator not available
    def calculate_s5_regeneration_trigger_score(s5_card_record: Dict[str, Any]) -> float:
        return 100.0  # Default: no regeneration needed
    def calculate_s5_card_regeneration_trigger_score(s5_card_record: Dict[str, Any]) -> float:
        return 100.0
    def calculate_s5_image_regeneration_trigger_score(s5_card_record: Dict[str, Any]) -> Optional[float]:
        return None
    def calculate_s1_table_regeneration_trigger_score(s1_table_validation: Dict[str, Any]) -> float:
        return 100.0  # Default: no regeneration needed

try:
    from dotenv import load_dotenv
    # Load environment variables (best-effort, may fail in sandbox)
    try:
        load_dotenv()
    except Exception:
        pass  # Continue without .env if not accessible
except ImportError:
    pass  # dotenv not available

try:
    from tools.progress_logger import ProgressLogger
except ImportError:
    ProgressLogger = None

# =========================
# S5 Config
# =========================

def _env_float(name: str, default: float) -> float:
    """Read float from environment variable (best-effort)."""
    try:
        return float(str(os.getenv(name, str(default))).strip())
    except Exception:
        return default

# Temperature for validation (low => more deterministic, better reproducibility)
# Can be overridden via TEMPERATURE_STAGE5 env var
S5_TEMPERATURE = _env_float("TEMPERATURE_STAGE5", 0.2)

# Import LLM caller from S1/S2 (reuse existing infrastructure)
try:
    import sys as _sys
    _THIS_DIR = Path(__file__).resolve().parent
    _sys.path.insert(0, str(_THIS_DIR))
    
    # Import tools
    try:
        from tools.api_key_rotator import ApiKeyRotator
        from tools.quota_limiter import QuotaLimiter, quota_from_env
    except ImportError:
        ApiKeyRotator = None
        QuotaLimiter = None
        quota_from_env = None
    
    # Import from 01_generate_json.py
    # Use importlib with proper module registration
    import importlib.util
    _generate_json_path = _THIS_DIR / "01_generate_json.py"
    if _generate_json_path.exists():
        try:
            # Create a proper module name
            module_name = "meducai_generate_json"
            spec = importlib.util.spec_from_file_location(module_name, _generate_json_path)
            if spec is not None and spec.loader is not None:
                # Register module in sys.modules before loading
                generate_json_module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = generate_json_module
                spec.loader.exec_module(generate_json_module)
                
                # Extract required functions/classes
                call_llm = getattr(generate_json_module, "call_llm", None)
                ProviderClients = getattr(generate_json_module, "ProviderClients", None)
                # Extract extract_json_object for manual JSON parsing if needed
                try:
                    extract_json_object = getattr(generate_json_module, "extract_json_object", None)
                except Exception:
                    extract_json_object = None
                # Extract detect_entity_type_for_s2 for entity type detection
                try:
                    detect_entity_type_for_s2 = getattr(generate_json_module, "detect_entity_type_for_s2", None)
                except Exception:
                    detect_entity_type_for_s2 = None
                
                # Initialize _global_rotator for subprocess workers (if ApiKeyRotator is available)
                # Note: This ensures API key rotation works even when S5 is run independently
                # (not via 01_generate_json.py main function which already initializes the rotator)
                if ApiKeyRotator is not None:
                    try:
                        # Get _global_rotator from the module and initialize it if not already set
                        _global_rotator = getattr(generate_json_module, "_global_rotator", None)
                        if _global_rotator is None:
                            # Initialize rotator (same pattern as 01_generate_json.py main function)
                            try:
                                # Try to find project root by looking for .env file or 3_Code directory
                                base_dir_for_rotator = Path.cwd()
                                # Walk up to find project root (contains .env or 3_Code directory)
                                for parent in base_dir_for_rotator.parents:
                                    if (parent / ".env").exists() or (parent / "3_Code").exists():
                                        base_dir_for_rotator = parent
                                        break
                                rotator = ApiKeyRotator(base_dir=base_dir_for_rotator, key_prefix="GOOGLE_API_KEY")
                                # Set the global rotator in the module
                                setattr(generate_json_module, "_global_rotator", rotator)
                                # API rotator initialization logging suppressed for cleaner terminal output
                                # (This happens in subprocess workers, so it's logged to file via progress_logger if available)
                            except Exception as rotator_err:
                                print(f"[S5] Warning: Failed to initialize API key rotator: {rotator_err}. "
                                      f"Subprocess workers will use GOOGLE_API_KEY environment variable.", 
                                      file=sys.stderr, flush=True)
                    except Exception as e:
                        print(f"[S5] Warning: Could not access _global_rotator: {e}", file=sys.stderr, flush=True)
                
                # Check if required functions/classes are available
                if call_llm and ProviderClients:
                    LLM_INFRASTRUCTURE_AVAILABLE = True
                else:
                    LLM_INFRASTRUCTURE_AVAILABLE = False
                    missing = []
                    if not call_llm:
                        missing.append("call_llm")
                    if not ProviderClients:
                        missing.append("ProviderClients")
                    print(f"Warning: Required functions/classes not found in 01_generate_json.py: {missing}. S5 validation will be disabled.", file=sys.stderr)
            else:
                LLM_INFRASTRUCTURE_AVAILABLE = False
                print("Warning: Failed to load 01_generate_json.py spec. S5 validation will be disabled.", file=sys.stderr)
        except Exception as e:
            LLM_INFRASTRUCTURE_AVAILABLE = False
            print(f"Warning: Failed to import 01_generate_json.py: {e}. S5 validation will be disabled.", file=sys.stderr)
    else:
        LLM_INFRASTRUCTURE_AVAILABLE = False
        print("Warning: 01_generate_json.py not found. S5 validation will be disabled.", file=sys.stderr)
except Exception as e:
    LLM_INFRASTRUCTURE_AVAILABLE = False
    print(f"Warning: LLM infrastructure not available: {e}. S5 validation will be disabled.", file=sys.stderr)

# Import prompt bundle loader
try:
    from tools.prompt_bundle import load_prompt_bundle
except ImportError:
    load_prompt_bundle = None

# Import path resolver for S2 results
try:
    from tools.path_resolver import resolve_s2_results_path
except ImportError:
    def resolve_s2_results_path(out_dir: Path, arm: str, s1_arm=None) -> Path:
        if s1_arm:
            new_path = out_dir / f"s2_results__s1arm{s1_arm}__s2arm{arm}.jsonl"
            if new_path.exists():
                return new_path
        return out_dir / f"s2_results__arm{arm}.jsonl"


# =========================
# S5 Model Configuration (Arm-Independent)
# =========================

# S1 Table Validation: Pro model, thinking=on, RAG=on
# Default: gemini-3-pro-preview (same as Arm E/F for S1)
S5_S1_TABLE_MODEL = os.getenv("S5_S1_TABLE_MODEL", "gemini-3-pro-preview")
S5_S1_TABLE_THINKING = True
S5_S1_TABLE_RAG_ENABLED = True

# S2 Card Validation: Flash model, thinking=on, RAG=on
# Default: gemini-3-flash-preview (same as Arm A-D for S2)
S5_S2_CARD_MODEL = os.getenv("S5_S2_CARD_MODEL", "gemini-3-flash-preview")
S5_S2_CARD_THINKING = True
S5_S2_CARD_RAG_ENABLED = True


# =========================
# S5 Logging Functions
# =========================

def log_s5_error(
    out_dir: Path,
    run_tag: str,
    arm: str,
    group_id: Optional[str],
    card_id: Optional[str],
    validation_type: str,  # "s1_table" | "s2_card"
    error_type: str,
    error_class: Optional[str],
    error_message: str,
    raw_response_preview: Optional[str] = None,
    traceback_str: Optional[str] = None,
    recovered: bool = False,
) -> None:
    """
    Log S5 validation errors to logs/s5_error_log.jsonl.
    Thread-safe logging for parallel validation processing.
    """
    log_dir = out_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "s5_error_log.jsonl"
    
    try:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "run_tag": run_tag,
            "arm": arm,
            "group_id": group_id,
            "card_id": card_id,
            "validation_type": validation_type,
            "error_type": error_type,
            "error_class": error_class,
            "error_message": error_message[:1000] if len(error_message) > 1000 else error_message,
            "recovered": recovered,
        }
        
        if raw_response_preview:
            log_entry["raw_response_preview"] = raw_response_preview[:1000] if len(raw_response_preview) > 1000 else raw_response_preview
        if traceback_str:
            log_entry["traceback"] = traceback_str[:2000] if len(traceback_str) > 2000 else traceback_str
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[WARN] Failed to log S5 error: {e}", file=sys.stderr, flush=True)


def log_s5_processing(
    out_dir: Path,
    run_tag: str,
    arm: str,
    group_id: Optional[str],
    card_id: Optional[str],
    action: str,  # "start" | "complete" | "skipped"
    validation_type: str,  # "s1_table" | "s2_card" | "group"
    duration_ms: Optional[float] = None,
    model_used: Optional[str] = None,
    s5_snapshot_id: Optional[str] = None,
    validation_attempt: Optional[int] = None,
    s2_cards_count: Optional[int] = None,
    s2_cards_missing: Optional[bool] = None,
) -> None:
    """
    Log S5 processing events (start/complete/skipped) to logs/s5_processing_log.jsonl.
    Thread-safe logging for parallel validation processing.
    """
    log_dir = out_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "s5_processing_log.jsonl"
    
    try:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "run_tag": run_tag,
            "arm": arm,
            "group_id": group_id,
            "card_id": card_id,
            "action": action,
            "validation_type": validation_type,
        }
        
        if duration_ms is not None:
            log_entry["duration_ms"] = duration_ms
        if model_used is not None:
            log_entry["model_used"] = model_used
        if s5_snapshot_id is not None:
            log_entry["s5_snapshot_id"] = s5_snapshot_id
        if validation_attempt is not None:
            log_entry["validation_attempt"] = validation_attempt
        if s2_cards_count is not None:
            log_entry["s2_cards_count"] = s2_cards_count
        if s2_cards_missing is not None:
            log_entry["s2_cards_missing"] = s2_cards_missing
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[WARN] Failed to log S5 processing: {e}", file=sys.stderr, flush=True)


# =========================
# Input Loading
# =========================

def load_s1_structure(s1_path: Path) -> List[Dict[str, Any]]:
    """Load S1 structure from JSONL file (returns list of groups)."""
    if not s1_path.exists():
        raise FileNotFoundError(f"S1 structure file not found: {s1_path}")
    
    groups = []
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    group_data = json.loads(line)
                    if isinstance(group_data, dict):
                        groups.append(group_data)
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse JSON line in S1 file: {e}", file=sys.stderr)
                    continue
    
    if not groups:
        raise ValueError(f"No valid JSON found in S1 structure file: {s1_path}")
    
    return groups


def load_s2_results(s2_path: Path) -> List[Dict[str, Any]]:
    """Load S2 results from JSONL file."""
    if not s2_path.exists():
        raise FileNotFoundError(f"S2 results file not found: {s2_path}")
    
    results = []
    with open(s2_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
    
    return results


def _infer_repaired_variant_path(baseline_path: Path) -> Path:
    """
    Infer the repaired-variant path for a baseline artifact.

    Example:
      s4_image_manifest__armA.jsonl -> s4_image_manifest__armA__repaired.jsonl
    """
    return baseline_path.with_name(f"{baseline_path.stem}__repaired{baseline_path.suffix}")


def _entry_points_to_existing_file(entry: Dict[str, Any], *, base_dir: Path, run_dir: Optional[Path]) -> bool:
    """
    Best-effort check whether a manifest entry points to an existing image file.

    Notes:
    - Absolute paths are checked directly.
    - Relative paths are checked relative to `run_dir` (preferred) then `base_dir`.
    - If no path exists, return False (so we don't mask a working baseline mapping).
    """
    try:
        image_path_str = str(entry.get("image_path") or "").strip()
        if not image_path_str:
            return False
        p = Path(image_path_str)
        if p.is_absolute():
            return p.exists()
        # Prefer resolving relative paths against the run_dir (metadata/generated/<run_tag>/)
        if run_dir is not None and (run_dir / p).exists():
            return True
        if (base_dir / p).exists():
            return True
        return False
    except Exception:
        return False


def load_s4_manifest(s4_manifest_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Load S4 image manifest from JSONL file.
    
    Returns:
        Dictionary mapping:
        - For S1_TABLE_VISUAL: (group_id, "TABLE", cluster_id) or (group_id, "TABLE", None) to manifest entry
        - For S2_CARD_IMAGE/CONCEPT: (group_id, entity_id, card_role) to manifest entry
    """
    if not s4_manifest_path.exists():
        return {}
    
    manifest = {}
    with open(s4_manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                group_id = entry.get("group_id", "")
                entity_id = entry.get("entity_id")
                card_role = entry.get("card_role")
                spec_kind = entry.get("spec_kind", "")
                cluster_id = entry.get("cluster_id")  # May be present for clustered table visuals
                
                if spec_kind == "S1_TABLE_VISUAL":
                    # Table visual: key by (group_id, "TABLE", cluster_id)
                    # cluster_id may be None for non-clustered infographics
                    key = (group_id, "TABLE", cluster_id)
                elif spec_kind in ("S2_CARD_IMAGE", "S2_CARD_CONCEPT"):
                    # Card image: key by (group_id, entity_id, card_role)
                    if entity_id and card_role:
                        key = (group_id, entity_id, card_role)
                    else:
                        continue
                else:
                    continue
                
                manifest[key] = entry
            except json.JSONDecodeError:
                continue
    
    return manifest


def load_s4_manifest_merged(
    *,
    base_dir: Path,
    s4_manifest_baseline_path: Path,
    s4_manifest_repaired_path: Optional[Path],
) -> Dict[str, Dict[str, Any]]:
    """
    Load S4 baseline manifest and (optionally) merge in repaired entries.

    Merge behavior:
    - Start with baseline entries.
    - Overlay repaired entries *only when* the repaired entry points to an existing file.
      (This avoids masking a good baseline path with a missing/corrupt repaired artifact.)

    Returns:
        A single manifest dict keyed the same way as `load_s4_manifest()`.
    """
    merged: Dict[str, Dict[str, Any]] = {}
    merged.update(load_s4_manifest(s4_manifest_baseline_path))

    if s4_manifest_repaired_path is None or (not s4_manifest_repaired_path.exists()):
        return merged

    repaired = load_s4_manifest(s4_manifest_repaired_path)
    run_dir = s4_manifest_baseline_path.parent if s4_manifest_baseline_path else None
    for k, entry in repaired.items():
        if _entry_points_to_existing_file(entry, base_dir=base_dir, run_dir=run_dir):
            merged[k] = entry
    return merged


def load_s3_image_specs(s3_image_spec_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Load S3 image specs from JSONL file.
    
    Returns:
        Dictionary mapping:
        - For S1_TABLE_VISUAL: (group_id, "TABLE", cluster_id) or (group_id, "TABLE", None) to spec entry
        - For S2_CARD_IMAGE/CONCEPT: (group_id, entity_id, card_role) to spec entry
    """
    if not s3_image_spec_path.exists():
        return {}
    
    specs = {}
    with open(s3_image_spec_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                group_id = entry.get("group_id", "")
                entity_id = entry.get("entity_id")
                card_role = entry.get("card_role")
                spec_kind = entry.get("spec_kind", "")
                cluster_id = entry.get("cluster_id")  # May be present for clustered table visuals
                
                if spec_kind == "S1_TABLE_VISUAL":
                    # Table visual: key by (group_id, "TABLE", cluster_id)
                    # cluster_id may be None for non-clustered infographics
                    key = (group_id, "TABLE", cluster_id)
                elif spec_kind in ("S2_CARD_IMAGE", "S2_CARD_CONCEPT") and entity_id and card_role:
                    key = (group_id, entity_id, card_role)
                else:
                    continue
                
                specs[key] = entry
            except json.JSONDecodeError:
                continue
    
    return specs


def resolve_image_path(
    base_dir: Path,
    run_tag: str,
    group_id: str,
    entity_id: Optional[str] = None,
    card_role: Optional[str] = None,
    spec_kind: Optional[str] = None,
    s4_manifest: Optional[Dict[str, Dict[str, Any]]] = None,
    cluster_id: Optional[str] = None,
) -> Optional[Path]:
    """
    Resolve image file path from S4 manifest or construct from filename pattern.
    
    Args:
        base_dir: Base directory of MeducAI project
        run_tag: Run tag identifier
        group_id: Group ID
        entity_id: Entity ID (for card images)
        card_role: Card role (Q1, Q2) (for card images)
        spec_kind: Spec kind ("S2_CARD_IMAGE", "S1_TABLE_VISUAL")
        s4_manifest: Optional pre-loaded S4 manifest dictionary
        cluster_id: Optional cluster ID (for clustered table visuals)
        
    Returns:
        Path to image file, or None if not found
    """
    # Try manifest first if provided
    if s4_manifest:
        if spec_kind == "S1_TABLE_VISUAL":
            # For table visuals, key includes cluster_id (may be None)
            key = (group_id, "TABLE", cluster_id)
        elif spec_kind in ("S2_CARD_IMAGE", "S2_CARD_CONCEPT") and entity_id and card_role:
            key = (group_id, entity_id, card_role)
        else:
            key = None
        
        if key and key in s4_manifest:
            entry = s4_manifest[key]
            image_path_str = entry.get("image_path")
            if image_path_str:
                image_path = Path(image_path_str)
                # Check if absolute path exists (ignore generation_success flag - file existence is authoritative)
                if image_path.is_absolute() and image_path.exists():
                    return image_path
                # Try relative to base_dir
                rel_path = base_dir / image_path_str
                if rel_path.exists():
                    return rel_path
                # Also try extracting just the filename and looking in base_dir/images
                # (handles cases where image_path is absolute but file was moved)
                if image_path.is_absolute():
                    filename = image_path.name
                    alt_dirs = [
                        base_dir / "2_Data" / "metadata" / "generated" / run_tag / "images",
                        base_dir / "2_Data" / "metadata" / "generated" / run_tag / "images__repaired",
                        base_dir / "images",
                        base_dir / "images__repaired",
                    ]
                    for d in alt_dirs:
                        alt_path = d / filename
                        if alt_path.exists():
                            return alt_path
    
    # Fallback: construct filename from pattern
    # Try multiple possible image directory locations
    # Prefer images_anki (resized for users) for token efficiency and realistic evaluation
    possible_image_dirs = [
        # Anki-ready images (resized, preferred for S5 validation)
        base_dir / "2_Data" / "metadata" / "generated" / run_tag / "images_anki",
        # Canonical run output (full resolution)
        base_dir / "2_Data" / "metadata" / "generated" / run_tag / "images",
        base_dir / "2_Data" / "metadata" / "generated" / run_tag / "images__repaired",
        # Legacy/alternative locations
        base_dir / "images",
        base_dir / "images__repaired",
        base_dir / "2_Data" / "images" / "generated" / run_tag,  # Legacy path structure
        base_dir.parent / "images" / run_tag,  # Alternative structure
    ]
    
    if spec_kind == "S1_TABLE_VISUAL":
        # Table visual: IMG__{run_tag}__{group_id}__TABLE.jpg (non-clustered)
        # or IMG__{run_tag}__{group_id}__TABLE__{cluster_id}.jpg (clustered)
        if cluster_id:
            filename = f"IMG__{run_tag}__{group_id}__TABLE__{cluster_id}.jpg"
        else:
            filename = f"IMG__{run_tag}__{group_id}__TABLE.jpg"
        # Try each possible image directory and each extension
        for images_dir in possible_image_dirs:
            for ext in [".jpg", ".png", ".jpeg"]:
                image_path = images_dir / filename.replace(".jpg", ext)
                if image_path.exists():
                    return image_path
    elif spec_kind in ("S2_CARD_IMAGE", "S2_CARD_CONCEPT") and entity_id and card_role:
        # Card image: IMG__{run_tag}__{group_id}__{entity_id}__{card_role}.jpg
        # Note: entity_id may contain ":" (e.g., "DERIVED:abc123") which is converted to "_" in filenames
        entity_id_safe = entity_id.replace(":", "_")
        filename = f"IMG__{run_tag}__{group_id}__{entity_id_safe}__{card_role}.jpg"
        # Try each possible image directory and each extension
        for images_dir in possible_image_dirs:
            for ext in [".jpg", ".png", ".jpeg"]:
                image_path = images_dir / filename.replace(".jpg", ext)
                if image_path.exists():
                    return image_path
    
    return None


# =========================
# S5 Snapshot ID Generation
# =========================

def generate_s5_snapshot_id(
    run_tag: str,
    group_id: str,
    arm: str,
    s5_model_version: str,
    validation_result: Dict[str, Any],
) -> str:
    """
    Generate S5 snapshot ID for reproducibility.
    
    Format: s5_{run_tag}_{group_id}_{arm}_{s5_model_version}_{hash}
    Hash: SHA256 of (validation result JSON + model config)
    """
    # Create hash input: validation result + model config
    hash_input = {
        "validation_result": validation_result,
        "model_config": {
            "s1_table_model": S5_S1_TABLE_MODEL,
            "s1_table_thinking": S5_S1_TABLE_THINKING,
            "s1_table_rag_enabled": S5_S1_TABLE_RAG_ENABLED,
            "s2_card_model": S5_S2_CARD_MODEL,
            "s2_card_thinking": S5_S2_CARD_THINKING,
            "s2_card_rag_enabled": S5_S2_CARD_RAG_ENABLED,
        },
    }
    
    # Generate hash (first 12 hex characters)
    hash_str = json.dumps(hash_input, sort_keys=True, ensure_ascii=False)
    hash_bytes = hashlib.sha256(hash_str.encode("utf-8")).digest()
    hash_hex = hash_bytes.hex()[:12]
    
    return f"s5_{run_tag}_{group_id}_{arm}_{s5_model_version}_{hash_hex}"


# =========================
# S5 Validation Logic
# =========================

def _normalize_ta(value: Any) -> Tuple[float, Optional[str]]:
    """
    Normalize technical_accuracy to one of {0.0, 0.5, 1.0}.
    Returns (normalized_value, warning_message_if_any).
    """
    try:
        v = float(value)
    except Exception:
        return 1.0, f"technical_accuracy not parseable: {value!r}"
    if v in (0.0, 0.5, 1.0):
        return v, None
    # Best-effort snapping (keep deterministic)
    if v <= 0.25:
        return 0.0, f"technical_accuracy out of set {v}; snapped to 0.0"
    if v <= 0.75:
        return 0.5, f"technical_accuracy out of set {v}; snapped to 0.5"
    return 1.0, f"technical_accuracy out of set {v}; snapped to 1.0"


def _normalize_difficulty(value: Any) -> Tuple[Optional[float], Optional[str]]:
    """
    Normalize difficulty to one of {0.0, 0.5, 1.0}.

    Notes:
    - S5 schema allows difficulty to be optional.
    - If value is missing/None/empty, returns (None, None).
    - If value is present but invalid, returns (None, warning).
    """
    if value is None:
        return None, None
    if isinstance(value, str) and not value.strip():
        return None, None
    try:
        v = float(value)
    except Exception:
        return None, f"difficulty not parseable: {value!r}"
    if v in (0.0, 0.5, 1.0):
        return v, None
    return None, f"difficulty out of set {v}; dropped (allowed: 0.0/0.5/1.0)"


def _has_clinical_blocking_signal(issues: Any) -> bool:
    """
    Heuristic: determine whether issues contain a clinical-safety blocking signal.
    Used to disambiguate judge inconsistencies.
    """
    if not isinstance(issues, list):
        return False
    clinical_types = {
        "factual_error",
        "medical_false",
        "clinical_risk",
        "guideline_violation",
        "guideline",
        "accuracy",
        "contraindication",
        "dosage_error",
        "unsafe_recommendation",
    }
    for it in issues:
        if not isinstance(it, dict):
            continue
        sev = str(it.get("severity", "") or "").strip().lower()
        t = str(it.get("type", "") or "").strip()
        code = str(it.get("issue_code", "") or "").strip()
        if code.startswith("FATAL_"):
            return True
        if sev == "blocking" and (t in clinical_types):
            return True
    return False


def _append_inconsistency_issue(issues: Any, *, note: str) -> List[Dict[str, Any]]:
    """Append an inconsistency issue, checking for duplicates first.
    
    Args:
        issues: Existing issues list (may be any type)
        note: Description of the inconsistency
    
    Returns:
        Updated issues list with new issue appended (if not duplicate)
    """
    base: List[Dict[str, Any]] = []
    if isinstance(issues, list):
        base = [x for x in issues if isinstance(x, dict)]
    
    # 중복 체크: 같은 description이 이미 있는지 확인
    note_normalized = note.strip().lower()
    has_duplicate = False
    for existing_issue in base:
        if isinstance(existing_issue, dict):
            existing_desc = existing_issue.get("description", "").strip().lower()
            existing_code = existing_issue.get("issue_code", "")
            # description이 정확히 같으면 중복
            if existing_desc == note_normalized:
                has_duplicate = True
                break
            # S5_INCONSISTENT_OUTPUT인 경우 description이 포함 관계면 중복으로 간주
            if (existing_code == "S5_INCONSISTENT_OUTPUT" and 
                (note_normalized in existing_desc or existing_desc in note_normalized)):
                has_duplicate = True
                break
    
    if not has_duplicate:
        base.append(
            {
                "severity": "warning",
                "type": "s5_output_inconsistency",
                "description": note,
                "issue_code": "S5_INCONSISTENT_OUTPUT",
                "affected_stage": "S5",
                "confidence": 0.8,
                "recommended_fix_target": "S5_SYSTEM",
                "prompt_patch_hint": "Enforce: blocking_error=true ONLY for clinical safety errors AND implies technical_accuracy=0.0.",
            }
        )
    
    return base


def _deduplicate_issues(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate issues based on description and issue_code.
    
    Two issues are considered duplicates if:
    1. They have the same issue_code AND description (case-insensitive)
    2. They are both S5_INCONSISTENT_OUTPUT and descriptions are similar (substring match)
    
    Args:
        issues: List of issue dictionaries
    
    Returns:
        Deduplicated list of issues
    """
    if not isinstance(issues, list):
        return []
    
    seen = set()
    deduplicated = []
    
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        
        desc = issue.get("description", "").strip().lower()
        code = issue.get("issue_code", "")
        
        # Create a unique key
        key = (code, desc)
        
        # For S5_INCONSISTENT_OUTPUT, also check for substring matches
        if code == "S5_INCONSISTENT_OUTPUT":
            is_duplicate = False
            for seen_code, seen_desc in seen:
                if seen_code == code:
                    # Check if descriptions are similar (one contains the other)
                    if desc in seen_desc or seen_desc in desc:
                        is_duplicate = True
                        break
            if is_duplicate:
                continue
        
        if key not in seen:
            seen.add(key)
            deduplicated.append(issue)
    
    return deduplicated

def extract_rag_evidence_from_response(
    parsed_json: Optional[Dict[str, Any]],
    meta: Dict[str, Any],
    raw_response: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Extract RAG evidence from LLM response.
    
    Priority:
    1. Check if LLM included rag_evidence in parsed JSON (preferred)
    2. Try to extract from API response metadata if available
    3. Return empty list if not available
    
    For Gemini API, RAG evidence can be:
    - In parsed JSON (if LLM followed prompt instructions)
    - In grounding_metadata.grounding_chunks (from API response)
    """
    rag_evidence = []
    
    # First, check if LLM included rag_evidence in parsed JSON
    if parsed_json and isinstance(parsed_json, dict):
        evidence_from_json = parsed_json.get("rag_evidence", [])
        if evidence_from_json and isinstance(evidence_from_json, list):
            # Validate and use evidence from LLM response
            for ev in evidence_from_json:
                if isinstance(ev, dict) and "source_id" in ev:
                    rag_evidence.append({
                        "source_id": str(ev.get("source_id", "")),
                        "source_excerpt": str(ev.get("source_excerpt", ""))[:500],  # Max 500 chars
                        "relevance": str(ev.get("relevance", "high")),
                    })
            if rag_evidence:
                return rag_evidence
    
    # If no evidence in JSON, try to extract from API metadata
    # Note: This requires access to the actual API response object,
    # which may not be available in call_llm return value
    # For now, if we have rag_sources_count, create placeholder entries
    try:
        if "rag_sources_count" in meta and meta["rag_sources_count"] > 0:
            # Create placeholder entries with note that actual excerpts need to be extracted
            # In production, this should be improved to extract actual chunks from API response
            for i in range(min(meta["rag_sources_count"], 3)):  # Limit to 3 sources
                rag_evidence.append({
                    "source_id": f"rag_doc_{i+1:03d}",
                    "source_excerpt": f"RAG source {i+1} (excerpt extraction from API response needed)",
                    "relevance": "high",
                })
    except Exception:
        pass  # Best-effort extraction
    
    return rag_evidence


def _validate_single_infographic(
    s1_table: Dict[str, Any],
    clients: Any,
    group_id: str,
    base_dir: Path,
    run_tag: str,
    arm: str,
    infographic_path: Optional[Path],
    s3_infographic_spec: Optional[Dict[str, Any]],
    cluster_id: Optional[str],
    prompt_bundle: Dict[str, Any],
    cluster_table_markdown: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Validate a single infographic (either non-clustered or one cluster).
    
    This is Step 2 of S5 S1 validation (infographic evaluation).
    Performs independent LLM call for each infographic.
    
    Args:
        s1_table: S1 table structure dict
        clients: ProviderClients instance
        group_id: Group identifier
        base_dir: Base directory of MeducAI project
        run_tag: Run tag identifier
        arm: Arm identifier
        infographic_path: Path to infographic image file
        s3_infographic_spec: S3 image spec dict (contains prompt_en)
        cluster_id: Optional cluster ID (None for single infographic)
        prompt_bundle: Prompt bundle dict (must contain S5_SYSTEM and S5_USER_TABLE_VISUAL)
        cluster_table_markdown: Optional cluster-specific table subset (if None, uses full master table)
    
    Returns:
        Tuple of (table_visual_validation dict, error_message if any)
        
        table_visual_validation dict structure:
        - cluster_id: Optional[str] (only for clusters)
        - blocking_error: bool
        - information_clarity: int (1-5 Likert)
        - anatomical_accuracy: float (0.0 | 0.5 | 1.0)
        - prompt_compliance: float (0.0 | 0.5 | 1.0)
        - table_visual_consistency: float (0.0 | 0.5 | 1.0)
        - extracted_text: Optional[str] (OCR-extracted text from image)
        - entities_found_in_text: Optional[List[str]] (entity names found via OCR)
        - issues: List[Dict]
        - image_path: str
    
    Model configuration (per specification):
    - Model: gemini-3-pro-preview
    - Temperature: 0.2
    - Thinking: enabled=true, level="high"
    - RAG: enabled=true
    - Timeout: 300 seconds
    """
    if not infographic_path or not infographic_path.exists():
        return None, None
    
    system_prompt = prompt_bundle["prompts"].get("S5_SYSTEM", "")
    user_prompt_template = prompt_bundle["prompts"].get("S5_USER_TABLE_VISUAL", "")
    if not user_prompt_template:
        # Fallback to regular table prompt if infographic prompt not available
        return None, "S5_USER_TABLE_VISUAL prompt not available"
    
    # Use cluster-specific table if provided, otherwise use full master table
    master_table_markdown = cluster_table_markdown if cluster_table_markdown else s1_table.get("master_table_markdown_kr", "")
    
    # Get S3 infographic spec data
    s3_infographic_prompt_en = ""
    if s3_infographic_spec:
        s3_infographic_prompt_en = s3_infographic_spec.get("prompt_en", "")
    
    # Format user prompt
    def safe_prompt_format(template: str, **kwargs) -> str:
        if template is None:
            return ""
        t = template.replace("{", "{{").replace("}", "}}")
        for k in kwargs.keys():
            t = t.replace("{{" + k + "}}", "{" + k + "}")
        try:
            return t.format(**kwargs)
        except KeyError as e:
            raise KeyError(
                f"Prompt template contains an unrecognized placeholder: {e}. "
                f"Allowed keys={sorted(kwargs.keys())}"
            ) from e
    
    prompt_kwargs = {
        "group_id": group_id,
        "group_path": s1_table.get("group_path", ""),
        "objective_bullets": "\n".join(s1_table.get("objective_bullets", [])),
        "master_table_markdown_kr": master_table_markdown,
        "s3_infographic_prompt_en": s3_infographic_prompt_en,
        "infographic_path": str(infographic_path),
    }
    
    user_prompt = safe_prompt_format(user_prompt_template, **prompt_kwargs)
    
    # Call LLM for infographic evaluation only
    try:
        if call_llm is None:
            return None, "call_llm function not available"
        
        log_ctx = f"S5_S1_table_{group_id}"
        if cluster_id:
            log_ctx = f"S5_S1_table_{group_id}_cluster_{cluster_id}"
        
        parsed_json, err, meta, raw_text = _call_llm_tracked(
            provider="gemini",
            clients=clients,
            model_name=S5_S1_TABLE_MODEL,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=S5_TEMPERATURE,
            timeout_s=300,
            stage=5,
            api_style="chat",
            thinking_enabled=S5_S1_TABLE_THINKING,
            thinking_level="high" if S5_S1_TABLE_THINKING else None,
            rag_enabled=S5_S1_TABLE_RAG_ENABLED,
            log_ctx=log_ctx,
            quota_limiter=None,  # RPD tracking disabled - rely on API errors and auto key rotation
            image_paths=[infographic_path] if infographic_path.exists() else None,
        )
        
        if err or not parsed_json:
            error_msg = str(err) if err else "No JSON returned from LLM"
            if raw_text and extract_json_object:
                try:
                    parsed_json = extract_json_object(raw_text, stage=5)
                except Exception:
                    return None, error_msg
            else:
                return None, error_msg
        
        if not isinstance(parsed_json, dict):
            return None, f"Expected dict, got {type(parsed_json).__name__}"
        
        # Extract infographic validation results
        visual_validation_raw = parsed_json.get("table_visual_validation")
        if visual_validation_raw and isinstance(visual_validation_raw, dict):
            table_visual_validation = {
                "cluster_id": cluster_id,  # Include cluster_id for identification (optional, only for clusters)
                "blocking_error": bool(visual_validation_raw.get("blocking_error", False)),
                "information_clarity": int(visual_validation_raw.get("information_clarity", 5)),
                "anatomical_accuracy": float(visual_validation_raw.get("anatomical_accuracy", 1.0)),
                "prompt_compliance": float(visual_validation_raw.get("prompt_compliance", 1.0)),
                "table_visual_consistency": float(visual_validation_raw.get("table_visual_consistency", 1.0)),
                "issues": visual_validation_raw.get("issues", []),
                "image_path": str(infographic_path),
            }
            
            # Extract OCR-related fields if present (per specification)
            extracted_text = visual_validation_raw.get("extracted_text")
            if extracted_text is not None:
                table_visual_validation["extracted_text"] = str(extracted_text)
            
            entities_found_in_text = visual_validation_raw.get("entities_found_in_text")
            if entities_found_in_text is not None and isinstance(entities_found_in_text, list):
                table_visual_validation["entities_found_in_text"] = [str(e) for e in entities_found_in_text if e]
            
            return table_visual_validation, None
        
        return None, "No table_visual_validation in LLM response"
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error: Infographic validation exception for group {group_id}" + 
              (f" cluster {cluster_id}" if cluster_id else "") + f": {e}", file=sys.stderr)
        log_s5_error(
            out_dir=base_dir,
            run_tag=run_tag,
            arm=arm,
            group_id=group_id,
            card_id=None,
            validation_type="s1_table",
            error_type="ValidationError",
            error_class=type(e).__name__,
            error_message=str(e),
            traceback_str=error_traceback,
            recovered=False,
        )
        return None, str(e)


def validate_s1_table(
    s1_table: Dict[str, Any],
    clients: Any,  # ProviderClients type
    group_id: str,
    base_dir: Path,
    run_tag: str = "unknown",
    arm: str = "unknown",
    s4_manifest: Optional[Dict[str, Dict[str, Any]]] = None,
    s3_image_specs: Optional[Dict[str, Dict[str, Any]]] = None,
    prompt_bundle: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Validate S1 table using Pro model with thinking and RAG.
    
    Evaluation follows a 2-step process per specification:
    1. Step 1: Table evaluation (always performed)
       - Input: master_table_markdown_kr, objective_bullets
       - Output: blocking_error, technical_accuracy, educational_quality, issues, rag_evidence
       - Prompt: S5_USER_TABLE__v2.md
    
    2. Step 2: Infographic evaluation (optional, if infographic exists)
       - Single infographic: 1 LLM call
       - Clustered infographics: up to 4 LLM calls (one per cluster)
       - Input: table + infographic image + S3 prompt
       - Output: table_visual_validation (single) or table_visual_validations (list)
       - Prompt: S5_USER_TABLE_VISUAL__v1.md
    
    Model configuration:
    - Model: gemini-3-pro-preview (fixed, arm-independent)
    - Temperature: 0.2 (configurable via TEMPERATURE_STAGE5 env var)
    - Thinking: enabled=true, level="high"
    - RAG: enabled=true (required when blocking_error=true)
    - Timeout: 300 seconds per LLM call
    
    Args:
        s1_table: S1 table structure dict (must contain master_table_markdown_kr, objective_bullets, etc.)
        clients: ProviderClients instance for LLM calls
        group_id: Group identifier
        base_dir: Base directory of MeducAI project
        run_tag: Run tag identifier
        arm: Arm identifier (A, B, C, D, E, F)
        s4_manifest: Optional S4 image manifest dict (keys: (group_id, "TABLE", cluster_id) or (group_id, entity_id, card_role))
        s3_image_specs: Optional S3 image specs dict (keys: same as s4_manifest)
        prompt_bundle: Optional prompt bundle dict (if None, will load from base_dir)
    
    Returns:
        Dict with validation results:
        - blocking_error: bool (clinical safety-critical only)
        - technical_accuracy: 0.0 | 0.5 | 1.0
        - educational_quality: 1 | 2 | 3 | 4 | 5
        - issues: List[Dict] (with issue_code, recommended_fix_target, prompt_patch_hint, etc.)
        - rag_evidence: List[Dict] (required if blocking_error=true, each with source_id, source_excerpt, relevance)
        - table_visual_validation: Dict (single infographic, backward compatibility)
          OR
        - table_visual_validations: List[Dict] (clustered infographics, each with cluster_id)
    
    Each table_visual_validation dict contains:
        - cluster_id: Optional[str] (only for clusters)
        - blocking_error: bool
        - information_clarity: int (1-5 Likert)
        - anatomical_accuracy: float (0.0 | 0.5 | 1.0)
        - prompt_compliance: float (0.0 | 0.5 | 1.0)
        - table_visual_consistency: float (0.0 | 0.5 | 1.0)
        - extracted_text: Optional[str] (OCR-extracted text from image)
        - entities_found_in_text: Optional[List[str]] (entity names found via OCR)
        - issues: List[Dict]
        - image_path: str
    
    See docs/s5_s1_validation_specification.md for complete specification.
    """
    if not LLM_INFRASTRUCTURE_AVAILABLE:
        return {
            "blocking_error": False,
            "technical_accuracy": 1.0,
            "educational_quality": 4,
            "issues": [],
            "rag_evidence": [],
        }
    
    # Check if clustering is used
    entity_clusters = s1_table.get("entity_clusters", [])
    infographic_clusters = s1_table.get("infographic_clusters", [])
    has_clustering = bool(entity_clusters and infographic_clusters and len(entity_clusters) > 0)
    
    # Collect all infographics (clustered or single)
    cluster_infographics: List[Tuple[Optional[str], Optional[Path], Optional[Dict[str, Any]], Optional[str]]] = []
    
    if has_clustering:
        # Collect cluster infographics with cluster table data
        master_table = s1_table.get("master_table_markdown_kr", "")
        for cluster, infographic in zip(entity_clusters, infographic_clusters):
            cluster_id = cluster.get("cluster_id")
            if not cluster_id:
                continue
            
            # Extract cluster table (subset of master table for this cluster)
            cluster_entity_names = cluster.get("entity_names", [])
            cluster_table_markdown = None
            if cluster_entity_names and master_table:
                # Try to import extract_cluster_table from S3
                try:
                    import sys
                    s3_module_path = base_dir / "3_Code" / "src" / "03_s3_policy_resolver.py"
                    if s3_module_path.exists():
                        import importlib.util
                        spec = importlib.util.spec_from_file_location("s3_policy_resolver", s3_module_path)
                        if spec and spec.loader:
                            s3_module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(s3_module)
                            if hasattr(s3_module, "extract_cluster_table"):
                                cluster_table_markdown = s3_module.extract_cluster_table(
                                    master_table_markdown=master_table,
                                    entity_names=sorted(cluster_entity_names),  # Stable ordering
                                )
                except Exception:
                    pass  # Fallback to full master table
                
                # Fallback: use full master table if extraction failed
                if not cluster_table_markdown:
                    cluster_table_markdown = master_table
            
            # Resolve cluster infographic path
            cluster_infographic_path = None
            cluster_s3_spec = None
            
            if s4_manifest:
                cluster_infographic_path = resolve_image_path(
                    base_dir=base_dir,
                    run_tag=run_tag,
                    group_id=group_id,
                    entity_id=None,
                    card_role=None,
                    spec_kind="S1_TABLE_VISUAL",
                    s4_manifest=s4_manifest,
                    cluster_id=cluster_id,
                )
                
                # Load S3 cluster spec if available
                if s3_image_specs:
                    cluster_key: Tuple[str, str, Optional[str]] = (group_id, "TABLE", cluster_id)
                    cluster_s3_spec = s3_image_specs.get(cluster_key)  # type: ignore
            
            cluster_infographics.append((cluster_id, cluster_infographic_path, cluster_s3_spec, cluster_table_markdown))
    else:
        # Single infographic (non-clustered)
        infographic_path: Optional[Path] = None
        s3_infographic_spec: Optional[Dict[str, Any]] = None
        
        if s4_manifest:
            infographic_path = resolve_image_path(
                base_dir=base_dir,
                run_tag=run_tag,
                group_id=group_id,
                entity_id=None,
                card_role=None,
                spec_kind="S1_TABLE_VISUAL",
                s4_manifest=s4_manifest,
                cluster_id=None,
            )
            
            # Load S3 infographic spec if available
            if s3_image_specs:
                single_key: Tuple[str, str, Optional[str]] = (group_id, "TABLE", None)
                s3_infographic_spec = s3_image_specs.get(single_key)  # type: ignore
        
        cluster_infographics.append((None, infographic_path, s3_infographic_spec, None))
    
    # Check if any infographic exists
    has_any_infographic = any(
        infographic_path is not None and infographic_path.exists()
        for _, infographic_path, _, _ in cluster_infographics
    )
    
    # Load prompts (prefer injected prompt bundle for reproducibility)
    try:
        if not prompt_bundle:
            if load_prompt_bundle is None:
                raise RuntimeError("load_prompt_bundle function not available")
            prompt_bundle = load_prompt_bundle(str(base_dir))
        if not prompt_bundle:
            raise RuntimeError("Failed to load prompt bundle")
    except Exception as e:
        print(f"Warning: Failed to load S5 prompts: {e}", file=sys.stderr)
        return {
            "blocking_error": False,
            "technical_accuracy": 1.0,
            "educational_quality": 4,
            "issues": [],
            "rag_evidence": [],
        }
    
    # Step 1: Evaluate table without infographic (per specification)
    # This is always performed regardless of infographic existence
    # Input: master_table_markdown_kr, objective_bullets
    # Output: blocking_error, technical_accuracy, educational_quality, issues, rag_evidence
    # Prompt: S5_USER_TABLE__v2.md
    system_prompt = prompt_bundle["prompts"].get("S5_SYSTEM", "")
    user_prompt_template_table = prompt_bundle["prompts"].get("S5_USER_TABLE", "")
    
    if not user_prompt_template_table:
        print(f"Warning: S5_USER_TABLE prompt not available for group {group_id}", file=sys.stderr)
        return {
            "blocking_error": False,
            "technical_accuracy": 1.0,
            "educational_quality": 4,
            "issues": [],
            "rag_evidence": [],
        }
    
    # Format user prompt for table evaluation (no infographic)
    def safe_prompt_format(template: str, **kwargs) -> str:
        """Safely format prompt templates that may contain JSON examples with braces."""
        if template is None:
            return ""
        t = template.replace("{", "{{").replace("}", "}}")
        for k in kwargs.keys():
            t = t.replace("{{" + k + "}}", "{" + k + "}")
        try:
            return t.format(**kwargs)
        except KeyError as e:
            raise KeyError(
                f"Prompt template contains an unrecognized placeholder: {e}. "
                f"Allowed keys={sorted(kwargs.keys())}"
            ) from e
    
    prompt_kwargs_table = {
        "group_id": group_id,
        "group_path": s1_table.get("group_path", ""),
        "objective_bullets": "\n".join(s1_table.get("objective_bullets", [])),
        "master_table_markdown_kr": s1_table.get("master_table_markdown_kr", ""),
    }
    
    user_prompt_table = safe_prompt_format(user_prompt_template_table, **prompt_kwargs_table)
    
    # Call LLM for table evaluation (no infographic)
    try:
        if call_llm is None:
            raise RuntimeError("call_llm function not available")
        
        try:
            parsed_json, err, meta, raw_text = _call_llm_tracked(
                provider="gemini",
                clients=clients,
                model_name=S5_S1_TABLE_MODEL,
                system_prompt=system_prompt,
                user_prompt=user_prompt_table,
                temperature=S5_TEMPERATURE,
                timeout_s=300,
                stage=5,
                api_style="chat",
                thinking_enabled=S5_S1_TABLE_THINKING,
                thinking_level="high" if S5_S1_TABLE_THINKING else None,
                rag_enabled=S5_S1_TABLE_RAG_ENABLED,
                log_ctx=f"S5_S1_table_{group_id}",
                quota_limiter=None,  # RPD tracking disabled - rely on API errors and auto key rotation
                image_paths=None,  # No image for table-only evaluation
            )
        except Exception as llm_err:
            import traceback
            error_traceback = traceback.format_exc()
            print(f"Error: LLM call exception for group {group_id}: {llm_err}", file=sys.stderr)
            traceback.print_exc()
            
            # Log error
            log_s5_error(
                out_dir=base_dir,
                run_tag=run_tag,
                arm=arm,
                group_id=group_id,
                card_id=None,
                validation_type="s1_table",
                error_type="LLMError",
                error_class=type(llm_err).__name__,
                error_message=str(llm_err),
                traceback_str=error_traceback,
                recovered=False,
            )
            
            return {
                "blocking_error": False,
                "technical_accuracy": 1.0,
                "educational_quality": 4,
                "issues": [],
                "rag_evidence": [],
            }
        
        # Handle errors from call_llm
        if err:
            print(f"Warning: S5 S1 table validation failed for group {group_id}: {err}", file=sys.stderr)
            print(f"Error type: {type(err).__name__ if err else 'None'}", file=sys.stderr)
            if raw_text:
                print(f"Raw response length: {len(raw_text)} chars", file=sys.stderr)
                print(f"Raw response (first 2000 chars):\n{raw_text[:2000]}", file=sys.stderr)
                # Try to manually extract JSON even if call_llm reported an error
                if extract_json_object:
                    try:
                        print(f"Attempting manual JSON extraction from raw_text...", file=sys.stderr)
                        parsed_json = extract_json_object(raw_text, stage=5)
                        print(f"Info: Successfully extracted JSON manually from raw response despite error", file=sys.stderr)
                        # Continue with parsed_json if extraction succeeded
                    except Exception as parse_err:
                        import traceback
                        error_traceback = traceback.format_exc()
                        print(f"Warning: Failed to manually extract JSON: {parse_err}", file=sys.stderr)
                        traceback.print_exc(file=sys.stderr)
                        log_s5_error(
                            out_dir=base_dir,
                            run_tag=run_tag,
                            arm=arm,
                            group_id=group_id,
                            card_id=None,
                            validation_type="s1_table",
                            error_type="JSONParseError",
                            error_class="Exception",
                            error_message=str(parse_err),
                            raw_response_preview=raw_text[:1000] if raw_text else None,
                            traceback_str=error_traceback,
                            recovered=False,
                        )
                        return {
                            "blocking_error": False,
                            "technical_accuracy": 1.0,
                            "educational_quality": 4,
                            "issues": [],
                            "rag_evidence": [],
                        }
                else:
                    print(f"Warning: extract_json_object function not available", file=sys.stderr)
                    log_s5_error(
                        out_dir=base_dir,
                        run_tag=run_tag,
                        arm=arm,
                        group_id=group_id,
                        card_id=None,
                        validation_type="s1_table",
                        error_type="LLMError",
                        error_class="ValueError",
                        error_message=str(err) if err else "extract_json_object function not available",
                        recovered=False,
                    )
                    return {
                        "blocking_error": False,
                        "technical_accuracy": 1.0,
                        "educational_quality": 4,
                        "issues": [],
                        "rag_evidence": [],
                    }
            else:
                print(f"Warning: No raw_text available for manual JSON extraction", file=sys.stderr)
                log_s5_error(
                    out_dir=base_dir,
                    run_tag=run_tag,
                    arm=arm,
                    group_id=group_id,
                    card_id=None,
                    validation_type="s1_table",
                    error_type="LLMError",
                    error_class="ValueError",
                    error_message=str(err) if err else "No raw_text available",
                    recovered=False,
                )
                return {
                    "blocking_error": False,
                    "technical_accuracy": 1.0,
                    "educational_quality": 4,
                    "issues": [],
                    "rag_evidence": [],
                }
        
        if not parsed_json:
            print(f"Warning: S5 S1 table validation returned no JSON for group {group_id}", file=sys.stderr)
            if raw_text:
                print(f"Raw response (first 1000 chars): {raw_text[:1000]}", file=sys.stderr)
                # Try to manually extract JSON if available
                if extract_json_object and raw_text:
                    try:
                        parsed_json = extract_json_object(raw_text, stage=5)
                        print(f"Info: Successfully extracted JSON manually from raw response", file=sys.stderr)
                    except Exception as parse_err:
                        import traceback
                        error_traceback = traceback.format_exc()
                        print(f"Warning: Failed to manually extract JSON: {parse_err}", file=sys.stderr)
                        log_s5_error(
                            out_dir=base_dir,
                            run_tag=run_tag,
                            arm=arm,
                            group_id=group_id,
                            card_id=None,
                            validation_type="s1_table",
                            error_type="JSONParseError",
                            error_class="Exception",
                            error_message=str(parse_err),
                            raw_response_preview=raw_text[:1000],
                            traceback_str=error_traceback,
                            recovered=False,
                        )
                        return {
                            "blocking_error": False,
                            "technical_accuracy": 1.0,
                            "educational_quality": 4,
                            "issues": [],
                            "rag_evidence": [],
                        }
                else:
                    return {
                        "blocking_error": False,
                        "technical_accuracy": 1.0,
                        "educational_quality": 4,
                        "issues": [],
                        "rag_evidence": [],
                    }
            else:
                return {
                    "blocking_error": False,
                    "technical_accuracy": 1.0,
                    "educational_quality": 4,
                    "issues": [],
                    "rag_evidence": [],
                }
        
        # Validate parsed_json is a dict
        if not isinstance(parsed_json, dict):
            print(f"Warning: S5 S1 table validation returned non-dict JSON for group {group_id}: {type(parsed_json)}", file=sys.stderr)
            if raw_text:
                print(f"Raw response (first 1000 chars): {raw_text[:1000]}", file=sys.stderr)
            log_s5_error(
                out_dir=base_dir,
                run_tag=run_tag,
                arm=arm,
                group_id=group_id,
                card_id=None,
                validation_type="s1_table",
                error_type="ValidationError",
                error_class="TypeError",
                error_message=f"Expected dict, got {type(parsed_json).__name__}",
                raw_response_preview=raw_text[:1000] if raw_text else None,
                recovered=False,
            )
            return {
                "blocking_error": False,
                "technical_accuracy": 1.0,
                "educational_quality": 4,
                "issues": [],
                "rag_evidence": [],
            }
        
        # Extract validation results
        blocking_error = bool(parsed_json.get("blocking_error", False))
        technical_accuracy, ta_warn = _normalize_ta(parsed_json.get("technical_accuracy", 1.0))
        educational_quality = parsed_json.get("educational_quality", 4)
        difficulty, diff_warn = _normalize_difficulty(parsed_json.get("difficulty", None))
        issues = parsed_json.get("issues", [])
        rag_evidence = parsed_json.get("rag_evidence", [])

        # Normalize internal semantics:
        # - blocking_error is clinical-safety only and should imply technical_accuracy=0.0
        if ta_warn:
            issues = _append_inconsistency_issue(issues, note=f"S5 normalized technical_accuracy: {ta_warn}")
        if diff_warn:
            issues = _append_inconsistency_issue(issues, note=f"S5 normalized difficulty: {diff_warn}")
        if blocking_error and technical_accuracy != 0.0:
            if _has_clinical_blocking_signal(issues):
                issues = _append_inconsistency_issue(
                    issues,
                    note="Judge returned blocking_error=true but technical_accuracy!=0.0; forcing technical_accuracy=0.0 due to clinical blocking signal.",
                )
                technical_accuracy = 0.0
            else:
                issues = _append_inconsistency_issue(
                    issues,
                    note="Judge returned blocking_error=true but technical_accuracy!=0.0 with no clinical blocking signal; clearing blocking_error to preserve clinical-only semantics.",
                )
                blocking_error = False
        if (not blocking_error) and technical_accuracy == 0.0:
            # If TA is explicitly 0.0, treat as clinical blocking to keep contract consistent.
            issues = _append_inconsistency_issue(
                issues,
                note="Judge returned technical_accuracy=0.0 but blocking_error=false; forcing blocking_error=true to keep semantics consistent.",
            )
            blocking_error = True
        
        # Extract RAG evidence (from JSON or API metadata)
        if blocking_error:
            # If blocking error, ensure we have RAG evidence
            if not rag_evidence or not isinstance(rag_evidence, list) or len(rag_evidence) == 0:
                rag_evidence = extract_rag_evidence_from_response(parsed_json, meta, raw_text)
            else:
                # Validate and format existing evidence
                formatted_evidence = []
                for ev in rag_evidence:
                    if isinstance(ev, dict) and "source_id" in ev:
                        formatted_evidence.append({
                            "source_id": str(ev.get("source_id", "")),
                            "source_excerpt": str(ev.get("source_excerpt", ""))[:500],
                            "relevance": str(ev.get("relevance", "high")),
                        })
                rag_evidence = formatted_evidence
        
        # Step 2: Evaluate each infographic (per specification)
        # This is optional and only performed if infographic(s) exist
        # - Single infographic: 1 LLM call
        # - Clustered infographics: up to 4 LLM calls (one per cluster)
        # Input: table + infographic image + S3 prompt
        # Output: table_visual_validation (single) or table_visual_validations (list)
        # Prompt: S5_USER_TABLE_VISUAL__v1.md
        table_visual_validations: List[Dict[str, Any]] = []
        
        for cluster_id, infographic_path, s3_spec, cluster_table_markdown in cluster_infographics:
            if infographic_path and infographic_path.exists():
                validation, error_msg = _validate_single_infographic(
                    s1_table=s1_table,
                    clients=clients,
                    group_id=group_id,
                    base_dir=base_dir,
                    run_tag=run_tag,
                    arm=arm,
                    infographic_path=infographic_path,
                    s3_infographic_spec=s3_spec,
                    cluster_id=cluster_id,
                    prompt_bundle=prompt_bundle,
                    cluster_table_markdown=cluster_table_markdown,
                )
                
                if validation:
                    table_visual_validations.append(validation)
                elif error_msg:
                    print(f"Warning: Failed to validate infographic for group {group_id}" +
                          (f" cluster {cluster_id}" if cluster_id else "") + f": {error_msg}", file=sys.stderr)
        
        result = {
            "blocking_error": blocking_error,
            "technical_accuracy": technical_accuracy,
            "educational_quality": educational_quality,
            "issues": _deduplicate_issues(issues),
            "rag_evidence": rag_evidence,
        }
        
        # Calculate S1 table regeneration trigger score (0-100 scale, lower => more likely to regenerate)
        # This provides consistent evaluation criteria with S2 cards
        try:
            table_trigger_score = calculate_s1_table_regeneration_trigger_score({
                "blocking_error": blocking_error,
                "technical_accuracy": technical_accuracy,
                "educational_quality": educational_quality,
            })
            result["table_regeneration_trigger_score"] = table_trigger_score
        except Exception as score_err:
            print(f"Warning: Failed to calculate S1 trigger score for group {group_id}: {score_err}", file=sys.stderr)
            # Don't fail validation if score calculation fails - continue without score
            pass
        
        # Add infographic validation(s)
        if has_clustering and len(table_visual_validations) > 0:
            # Multiple clusters: use table_visual_validations (list)
            result["table_visual_validations"] = table_visual_validations
        elif len(table_visual_validations) == 1:
            # Single infographic: use table_visual_validation (dict) for backward compatibility
            result["table_visual_validation"] = table_visual_validations[0]
        
        return result
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error: S5 S1 table validation exception for group {group_id}: {e}", file=sys.stderr)
        log_s5_error(
            out_dir=base_dir,
            run_tag=run_tag,
            arm=arm,
            group_id=group_id,
            card_id=None,
            validation_type="s1_table",
            error_type="ValidationError",
            error_class=type(e).__name__,
            error_message=str(e),
            traceback_str=error_traceback,
            recovered=False,
        )
        return {
            "blocking_error": False,
            "technical_accuracy": 1.0,
            "educational_quality": 4,
            "issues": [],
            "rag_evidence": [],
        }


def validate_exam_focus_for_entity_type(
    card: Dict[str, Any],
    entity_type: str,
    entity_name: str,
    issues: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Validate that exam_focus matches entity type requirements.
    Only validates Q1 cards (Q2 always uses "concept").
    
    Args:
        card: Card dictionary with image_hint
        entity_type: Entity type ("disease", "sign", "overview", "qc", "equipment")
        entity_name: Entity name for error messages
        issues: Existing issues list
    
    Returns:
        Updated issues list (may append new issues)
    """
    # Only validate Q1 cards
    if card.get("card_role") != "Q1":
        return issues
    
    image_hint = card.get("image_hint")
    if not image_hint:
        # Missing image_hint is a separate issue (should be caught elsewhere)
        return issues
    
    exam_focus = image_hint.get("exam_focus", "")
    if not exam_focus:
        # Missing exam_focus is a separate issue
        return issues
    
    # Valid mappings (from S2_SYSTEM__v9.md)
    valid_mappings = {
        "disease": ["diagnosis"],
        "sign": ["pattern", "sign"],
        "overview": ["concept", "classification"],
        "qc": ["procedure", "measurement", "principle"],
        "equipment": ["procedure", "principle", "operation"],
        "comparison": ["diagnosis"],  # Comparison entities use "diagnosis" but frame as differential
    }
    
    valid_focuses = valid_mappings.get(entity_type, ["diagnosis"])  # Default to diagnosis
    
    if exam_focus not in valid_focuses:
        issues.append({
            "severity": "minor",
            "type": "entity_type_mismatch",
            "description": f"Entity '{entity_name}' (type: {entity_type}) should use exam_focus in {valid_focuses}, but found '{exam_focus}'",
            "issue_code": "S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH",
            "affected_stage": "S2",
            "recommended_fix_target": "S2_SYSTEM",
            "prompt_patch_hint": f"For {entity_type} entities, ensure exam_focus is one of: {', '.join(valid_focuses)}",
        })
    
    return issues


def validate_s2_card(
    card: Dict[str, Any],
    entity_context: Dict[str, Any],
    clients: Any,  # ProviderClients type
    card_id: str,
    base_dir: Path,
    run_tag: str = "unknown",
    arm: str = "unknown",
    s4_manifest: Optional[Dict[str, Dict[str, Any]]] = None,
    s3_image_specs: Optional[Dict[str, Dict[str, Any]]] = None,
    prompt_bundle: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Validate S2 card using Flash model with thinking and RAG.
    Optionally includes image evaluation if image is available.
    
    Returns validation result with blocking_error, technical_accuracy, educational_quality, issues, rag_evidence,
    and optionally card_image_validation if image exists.
    """
    # Optional field (may be present in S5 outputs). Keep defined for type-checkers.
    difficulty: Optional[float] = None

    if not LLM_INFRASTRUCTURE_AVAILABLE:
        return {
            "blocking_error": False,
            "technical_accuracy": 1.0,
            "educational_quality": 4,
            "issues": [],
            "rag_evidence": [],
        }
    
    # Check if image exists and resolve image path
    group_id = entity_context.get("group_id", "")
    entity_id = entity_context.get("entity_id", "")
    card_role = str(card.get("card_role", "") or "").strip()
    image_path: Optional[Path] = None
    s3_image_spec: Optional[Dict[str, Any]] = None
    
    # Only evaluate images for Q1 and Q2 cards
    if card_role in ("Q1", "Q2") and s4_manifest:
        image_path = resolve_image_path(
            base_dir=base_dir,
            run_tag=run_tag,
            group_id=group_id,
            entity_id=entity_id,
            card_role=card_role,
            spec_kind="S2_CARD_IMAGE",
            s4_manifest=s4_manifest,
        )
        
        # Load S3 image spec if available
        if s3_image_specs and entity_id and card_role:
            key: Tuple[str, str, str] = (group_id, entity_id, card_role)
            s3_image_spec = s3_image_specs.get(key)  # type: ignore
    
    # Determine which prompt template to use
    use_image_prompt = image_path is not None and image_path.exists()
    
    # Load prompts (prefer injected prompt bundle for reproducibility)
    try:
        if not prompt_bundle:
            if load_prompt_bundle is None:
                raise RuntimeError("load_prompt_bundle function not available")
            prompt_bundle = load_prompt_bundle(str(base_dir))
        if not prompt_bundle:
            raise RuntimeError("Failed to load prompt bundle")
        system_prompt = prompt_bundle["prompts"].get("S5_SYSTEM", "")
        if use_image_prompt:
            user_prompt_template = prompt_bundle["prompts"].get("S5_USER_CARD_IMAGE", "")
            # Fallback to regular card prompt if image prompt not available
            if not user_prompt_template:
                user_prompt_template = prompt_bundle["prompts"].get("S5_USER_CARD", "")
                use_image_prompt = False  # Disable image evaluation if prompt not available
        else:
            user_prompt_template = prompt_bundle["prompts"].get("S5_USER_CARD", "")
    except Exception as e:
        print(f"Warning: Failed to load S5 prompts: {e}", file=sys.stderr)
        return {
            "blocking_error": False,
            "technical_accuracy": 1.0,
            "educational_quality": 4,
            "issues": [],
            "rag_evidence": [],
        }
    
    # Format user prompt with card data
    card_front = card.get("front", "")
    card_back = card.get("back", "")
    card_type = str(card.get("card_type", "") or "").strip()
    card_role = str(card.get("card_role", "") or "").strip()

    # Anki MCQ convention: options/correct_index are stored in structured fields, not necessarily rendered in front/back.
    options = card.get("options", [])
    correct_index = card.get("correct_index", None)
    options_str = ""
    if isinstance(options, list) and len(options) > 0:
        # Compact, judge-friendly format
        option_labels = ["A", "B", "C", "D", "E"]
        lines = []
        for i, opt in enumerate(options[:5]):
            label = option_labels[i] if i < len(option_labels) else str(i)
            lines.append(f"{label}. {str(opt).strip()}")
        options_str = "\n".join(lines)

    correct_index_str = ""
    if isinstance(correct_index, int):
        correct_index_str = str(correct_index)

    entity_context_str = json.dumps(entity_context, ensure_ascii=False, indent=2) if entity_context else ""
    
    # Get S2 image_hint from card (original specification)
    s2_image_hint_str = ""
    key_landmarks_list = ""
    key_findings_keywords_str = ""
    image_hint = card.get("image_hint")
    if image_hint:
        s2_image_hint_str = json.dumps(image_hint, ensure_ascii=False, indent=2)
        # Extract key_findings_keywords from image_hint
        key_findings = image_hint.get("key_findings_keywords", [])
        if isinstance(key_findings, list) and key_findings:
            key_findings_keywords_str = ", ".join([str(kw) for kw in key_findings if kw])
        # Extract key_landmarks_to_include from image_hint_v2 if available
        image_hint_v2 = card.get("image_hint_v2")
        if image_hint_v2 and isinstance(image_hint_v2, dict):
            anatomy = image_hint_v2.get("anatomy", {})
            if isinstance(anatomy, dict):
                key_landmarks = anatomy.get("key_landmarks_to_include", [])
                if isinstance(key_landmarks, list) and key_landmarks:
                    key_landmarks_list = "\n".join([f"- {landmark}" for landmark in key_landmarks if landmark])
    
    # Get S3 image spec data if available
    s3_prompt_en = ""
    s3_image_hint_v2_str = ""
    exam_prompt_profile_str = ""
    if s3_image_spec:
        s3_prompt_en = s3_image_spec.get("prompt_en", "")
        image_hint_v2 = s3_image_spec.get("image_hint_v2")
        if image_hint_v2:
            s3_image_hint_v2_str = json.dumps(image_hint_v2, ensure_ascii=False, indent=2)
            # Also extract key_landmarks from S3 image_hint_v2 if not already extracted from S2
            if not key_landmarks_list and isinstance(image_hint_v2, dict):
                anatomy = image_hint_v2.get("anatomy", {})
                if isinstance(anatomy, dict):
                    key_landmarks = anatomy.get("key_landmarks_to_include", [])
                    if isinstance(key_landmarks, list) and key_landmarks:
                        key_landmarks_list = "\n".join([f"- {landmark}" for landmark in key_landmarks if landmark])
        
        # Extract exam_prompt_profile for LLM to know if this is REALISTIC or DIAGRAM
        exam_prompt_profile = s3_image_spec.get("exam_prompt_profile", "")
        if exam_prompt_profile:
            exam_prompt_profile_str = str(exam_prompt_profile).strip()
        else:
            exam_prompt_profile_str = "diagram"  # Default
    
    # Format user prompt with card data
    # Use safe formatting to avoid issues with curly braces in content (e.g., JSON examples in prompts)
    def safe_prompt_format(template: str, **kwargs) -> str:
        """Safely format prompt templates that may contain JSON examples with braces."""
        if template is None:
            return ""
        t = template.replace("{", "{{").replace("}", "}}")
        for k in kwargs.keys():
            t = t.replace("{{" + k + "}}", "{" + k + "}")
        try:
            return t.format(**kwargs)
        except KeyError as e:
            raise KeyError(
                f"Prompt template contains an unrecognized placeholder: {e}. "
                f"Allowed keys={sorted(kwargs.keys())}"
            ) from e
    
    # Prepare prompt kwargs
    prompt_kwargs = {
        "card_id": card_id,
        "card_role": card_role,
        "card_type": card_type,
        "entity_id": entity_context.get("entity_id", ""),
        "entity_name": entity_context.get("entity_name", ""),
        "card_front": card_front,
        "card_back": card_back,
        "card_options": options_str,
        "correct_index": correct_index_str,
        "entity_context": entity_context_str,
    }
    
    # Add image-specific fields if using image prompt
    if use_image_prompt:
        prompt_kwargs["s3_prompt_en"] = s3_prompt_en
        prompt_kwargs["s3_image_hint_v2"] = s3_image_hint_v2_str
        prompt_kwargs["s2_image_hint"] = s2_image_hint_str
        prompt_kwargs["key_landmarks_list"] = key_landmarks_list if key_landmarks_list else "(None specified)"
        prompt_kwargs["key_findings_keywords"] = key_findings_keywords_str if key_findings_keywords_str else "(None specified)"
        prompt_kwargs["image_path"] = str(image_path) if image_path else ""
        prompt_kwargs["exam_prompt_profile"] = exam_prompt_profile_str  # Critical: tells LLM if this is REALISTIC or DIAGRAM
    
    user_prompt = safe_prompt_format(user_prompt_template, **prompt_kwargs)
    
    # Call LLM
    try:
        if call_llm is None:
            raise RuntimeError("call_llm function not available")
        
        # Prepare image_paths for multimodal input
        image_paths: Optional[List[Path]] = None
        if use_image_prompt and image_path and image_path.exists():
            image_paths = [image_path]
        
        try:
            parsed_json, err, meta, raw_text = _call_llm_tracked(
                provider="gemini",
                clients=clients,
                model_name=S5_S2_CARD_MODEL,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=S5_TEMPERATURE,
                timeout_s=180,  # 3 minutes timeout
                stage=5,
                api_style="chat",
                thinking_enabled=S5_S2_CARD_THINKING,
                thinking_level="high" if S5_S2_CARD_THINKING else None,
                rag_enabled=S5_S2_CARD_RAG_ENABLED,
                log_ctx=f"S5_S2_card_{card_id}",
                quota_limiter=None,  # RPD tracking disabled - rely on API errors and auto key rotation
                image_paths=image_paths,  # Pass image paths for multimodal evaluation
            )
        except Exception as llm_err:
            import traceback
            error_traceback = traceback.format_exc()
            print(f"Error: LLM call exception for card {card_id}: {llm_err}", file=sys.stderr)
            traceback.print_exc()
            group_id = entity_context.get("group_id", "unknown")
            log_s5_error(
                out_dir=base_dir,
                run_tag=run_tag,
                arm=arm,
                group_id=group_id,
                card_id=card_id,
                validation_type="s2_card",
                error_type="LLMError",
                error_class=type(llm_err).__name__,
                error_message=str(llm_err),
                traceback_str=error_traceback,
                recovered=False,
            )
            return {
                "blocking_error": False,
                "technical_accuracy": 1.0,
                "educational_quality": 4,
                "issues": [],
                "rag_evidence": [],
            }
        
        # Handle errors from call_llm
        if err:
            print(f"Warning: S5 S2 card validation failed for card {card_id}: {err}", file=sys.stderr)
            print(f"Error type: {type(err).__name__ if err else 'None'}", file=sys.stderr)
            if raw_text:
                print(f"Raw response length: {len(raw_text)} chars", file=sys.stderr)
                print(f"Raw response (first 2000 chars):\n{raw_text[:2000]}", file=sys.stderr)
                # Try to manually extract JSON even if call_llm reported an error
                if extract_json_object:
                    try:
                        print(f"Attempting manual JSON extraction from raw_text...", file=sys.stderr)
                        parsed_json = extract_json_object(raw_text, stage=5)
                        print(f"Info: Successfully extracted JSON manually from raw response despite error", file=sys.stderr)
                        # Continue with parsed_json if extraction succeeded
                    except Exception as parse_err:
                        print(f"Warning: Failed to manually extract JSON: {parse_err}", file=sys.stderr)
                        import traceback
                        traceback.print_exc(file=sys.stderr)
                        return {
                            "blocking_error": False,
                            "technical_accuracy": 1.0,
                            "educational_quality": 4,
                            "issues": [],
                            "rag_evidence": [],
                        }
                else:
                    print(f"Warning: extract_json_object function not available", file=sys.stderr)
                    group_id = entity_context.get("group_id", "unknown")
                    log_s5_error(
                        out_dir=base_dir,
                        run_tag=run_tag,
                        arm=arm,
                        group_id=group_id,
                        card_id=card_id,
                        validation_type="s2_card",
                        error_type="LLMError",
                        error_class="ValueError",
                        error_message=str(err) if err else "extract_json_object function not available",
                        recovered=False,
                    )
                    return {
                        "blocking_error": False,
                        "technical_accuracy": 1.0,
                        "educational_quality": 4,
                        "issues": [],
                        "rag_evidence": [],
                    }
            else:
                print(f"Warning: No raw_text available for manual JSON extraction", file=sys.stderr)
                group_id = entity_context.get("group_id", "unknown")
                log_s5_error(
                    out_dir=base_dir,
                    run_tag=run_tag,
                    arm=arm,
                    group_id=group_id,
                    card_id=card_id,
                    validation_type="s2_card",
                    error_type="LLMError",
                    error_class="ValueError",
                    error_message=str(err) if err else "No raw_text available",
                    recovered=False,
                )
                return {
                    "blocking_error": False,
                    "technical_accuracy": 1.0,
                    "educational_quality": 4,
                    "issues": [],
                    "rag_evidence": [],
                }
        
        if not parsed_json:
            group_id = entity_context.get("group_id", "unknown")
            print(f"Warning: S5 S2 card validation returned no JSON for card {card_id}", file=sys.stderr)
            log_s5_error(
                out_dir=base_dir,
                run_tag=run_tag,
                arm=arm,
                group_id=group_id,
                card_id=card_id,
                validation_type="s2_card",
                error_type="ValidationError",
                error_class="ValueError",
                error_message="No JSON returned from LLM",
                raw_response_preview=raw_text[:1000] if raw_text else None,
                recovered=False,
            )
            if raw_text:
                print(f"Raw response (first 1000 chars): {raw_text[:1000]}", file=sys.stderr)
                # Try to manually extract JSON if available
                if extract_json_object and raw_text:
                    try:
                        parsed_json = extract_json_object(raw_text, stage=5)
                        print(f"Info: Successfully extracted JSON manually from raw response", file=sys.stderr)
                    except Exception as parse_err:
                        import traceback
                        error_traceback = traceback.format_exc()
                        print(f"Warning: Failed to manually extract JSON: {parse_err}", file=sys.stderr)
                        group_id = entity_context.get("group_id", "unknown")
                        log_s5_error(
                            out_dir=base_dir,
                            run_tag=run_tag,
                            arm=arm,
                            group_id=group_id,
                            card_id=card_id,
                            validation_type="s2_card",
                            error_type="JSONParseError",
                            error_class="Exception",
                            error_message=str(parse_err),
                            raw_response_preview=raw_text[:1000] if raw_text else None,
                            traceback_str=error_traceback,
                            recovered=False,
                        )
                        return {
                            "blocking_error": False,
                            "technical_accuracy": 1.0,
                            "educational_quality": 4,
                            "issues": [],
                            "rag_evidence": [],
                        }
                else:
                    return {
                        "blocking_error": False,
                        "technical_accuracy": 1.0,
                        "educational_quality": 4,
                        "issues": [],
                        "rag_evidence": [],
                    }
            else:
                return {
                    "blocking_error": False,
                    "technical_accuracy": 1.0,
                    "educational_quality": 4,
                    "issues": [],
                    "rag_evidence": [],
                }
        
        # Validate parsed_json is a dict
        if not isinstance(parsed_json, dict):
            print(f"Warning: S5 S2 card validation returned non-dict JSON for card {card_id}: {type(parsed_json)}", file=sys.stderr)
            if raw_text:
                print(f"Raw response (first 1000 chars): {raw_text[:1000]}", file=sys.stderr)
            group_id = entity_context.get("group_id", "unknown")
            log_s5_error(
                out_dir=base_dir,
                run_tag=run_tag,
                arm=arm,
                group_id=group_id,
                card_id=card_id,
                validation_type="s2_card",
                error_type="ValidationError",
                error_class="TypeError",
                error_message=f"Expected dict, got {type(parsed_json).__name__}",
                raw_response_preview=raw_text[:1000] if raw_text else None,
                recovered=False,
            )
            return {
                "blocking_error": False,
                "technical_accuracy": 1.0,
                "educational_quality": 4,
                "issues": [],
                "rag_evidence": [],
            }
        
        # Extract validation results
        blocking_error = bool(parsed_json.get("blocking_error", False))
        technical_accuracy, ta_warn = _normalize_ta(parsed_json.get("technical_accuracy", 1.0))
        educational_quality = parsed_json.get("educational_quality", 4)
        issues = parsed_json.get("issues", [])
        rag_evidence = parsed_json.get("rag_evidence", [])

        # Normalize internal semantics:
        # - blocking_error is clinical-safety only and should imply technical_accuracy=0.0
        if ta_warn:
            issues = _append_inconsistency_issue(issues, note=f"S5 normalized technical_accuracy: {ta_warn}")
        if blocking_error and technical_accuracy != 0.0:
            if _has_clinical_blocking_signal(issues):
                issues = _append_inconsistency_issue(
                    issues,
                    note="Judge returned blocking_error=true but technical_accuracy!=0.0; forcing technical_accuracy=0.0 due to clinical blocking signal.",
                )
                technical_accuracy = 0.0
            else:
                issues = _append_inconsistency_issue(
                    issues,
                    note="Judge returned blocking_error=true but technical_accuracy!=0.0 with no clinical blocking signal; clearing blocking_error to preserve clinical-only semantics.",
                )
                blocking_error = False
        if (not blocking_error) and technical_accuracy == 0.0:
            issues = _append_inconsistency_issue(
                issues,
                note="Judge returned technical_accuracy=0.0 but blocking_error=false; forcing blocking_error=true to keep semantics consistent.",
            )
            blocking_error = True
        
        # Extract RAG evidence (from JSON or API metadata)
        if blocking_error:
            # If blocking error, ensure we have RAG evidence
            if not rag_evidence or not isinstance(rag_evidence, list) or len(rag_evidence) == 0:
                rag_evidence = extract_rag_evidence_from_response(parsed_json, meta, raw_text)
            else:
                # Validate and format existing evidence
                formatted_evidence = []
                for ev in rag_evidence:
                    if isinstance(ev, dict) and "source_id" in ev:
                        formatted_evidence.append({
                            "source_id": str(ev.get("source_id", "")),
                            "source_excerpt": str(ev.get("source_excerpt", ""))[:500],
                            "relevance": str(ev.get("relevance", "high")),
                        })
                rag_evidence = formatted_evidence
        
        # Post-processing validation: exam_focus vs entity_type alignment
        # Only if entity_type is available and detect_entity_type_for_s2 function is available
        entity_type = entity_context.get("entity_type")
        entity_name = entity_context.get("entity_name", "")
        if entity_type and detect_entity_type_for_s2:
            issues = validate_exam_focus_for_entity_type(
                card=card,
                entity_type=entity_type,
                entity_name=entity_name,
                issues=issues
            )
        
        # Extract image validation results if present
        card_image_validation: Optional[Dict[str, Any]] = None
        if use_image_prompt and parsed_json:
            image_validation_raw = parsed_json.get("card_image_validation")
            if image_validation_raw and isinstance(image_validation_raw, dict):
                # Check if this is a REALISTIC image (from S3 spec)
                is_realistic = False
                if s3_image_spec:
                    exam_prompt_profile = str(s3_image_spec.get("exam_prompt_profile", "")).strip().lower()
                    is_realistic = exam_prompt_profile in ("v8_realistic", "realistic", "pacs", "v8_realistic_4x5_2k", "s5r2_realistic")
                
                # Normalize/augment image issues so they feed upstream prompt repair (S3) reliably.
                raw_img_issues = image_validation_raw.get("issues", [])
                img_issues: List[Dict[str, Any]] = []
                if isinstance(raw_img_issues, list):
                    img_issues = [it for it in raw_img_issues if isinstance(it, dict)]
                img_issues = _deduplicate_issues(img_issues)

                def _ensure_s3_linkage_for_image_issue(it: Dict[str, Any], *, is_realistic: bool) -> Dict[str, Any]:
                    t = str(it.get("type") or "").strip()
                    tl = t.lower()

                    # Default linkage: image-generation compliance issues should map to S3 prompt/constraints.
                    if not str(it.get("recommended_fix_target") or "").strip():
                        if tl in ("view_mismatch", "key_finding_missing", "landmark_missing", "excessive_text"):
                            it["recommended_fix_target"] = "S3_PROMPT"

                    # Deterministic issue_code defaults (only if missing).
                    if not str(it.get("issue_code") or "").strip():
                        if tl == "view_mismatch":
                            it["issue_code"] = "S3_VIEW_ALIGNMENT_VIOLATION"
                        elif tl == "key_finding_missing":
                            it["issue_code"] = "S3_PROMPT_COMPLIANCE_MISSING_FINDING"
                        elif tl == "landmark_missing":
                            it["issue_code"] = "S3_PROMPT_COMPLIANCE_MISSING_LANDMARK"
                        elif tl == "excessive_text":
                            it["issue_code"] = (
                                "S3_TEXT_POLICY_VIOLATION_REALISTIC" if is_realistic else "S3_TEXT_POLICY_VIOLATION_DIAGRAM"
                            )

                    # Best-effort patch hint (only if missing).
                    if (
                        str(it.get("recommended_fix_target") or "").strip() == "S3_PROMPT"
                        and not str(it.get("prompt_patch_hint") or "").strip()
                    ):
                        if tl == "view_mismatch":
                            it["prompt_patch_hint"] = "Strengthen S3 constraint_block view alignment checks; regenerate with correct view_plane/projection."
                        elif tl == "excessive_text":
                            it["prompt_patch_hint"] = (
                                "Enforce S3 constraint_block text policy (REALISTIC: zero text; DIAGRAM: minimal labels); regenerate."
                            )
                        elif tl in ("key_finding_missing", "landmark_missing"):
                            it["prompt_patch_hint"] = "Add explicit landmark/key-finding requirements to S3 prompt/constraint_block; regenerate."

                    return it

                img_issues = [_ensure_s3_linkage_for_image_issue(it, is_realistic=is_realistic) for it in img_issues]

                # Extract OCR fields (LLM-provided). (We cannot OCR locally; enforce via these fields.)
                extracted_text_val = image_validation_raw.get("extracted_text")
                extracted_text_str = str(extracted_text_val).strip() if extracted_text_val is not None else ""
                text_detected_val = image_validation_raw.get("text_detected")
                text_detected: Optional[bool] = None
                if isinstance(text_detected_val, bool):
                    text_detected = text_detected_val
                elif isinstance(text_detected_val, (int, float)) and text_detected_val in (0, 1):
                    text_detected = bool(text_detected_val)
                elif isinstance(text_detected_val, str) and text_detected_val.strip().lower() in ("true", "false"):
                    text_detected = text_detected_val.strip().lower() == "true"

                modality_match_val = image_validation_raw.get("modality_match")
                modality_match: Optional[bool] = None
                if isinstance(modality_match_val, bool):
                    modality_match = modality_match_val

                landmarks_present_val = image_validation_raw.get("landmarks_present")
                landmarks_present: Optional[bool] = None
                if isinstance(landmarks_present_val, bool):
                    landmarks_present = landmarks_present_val

                # REALISTIC policy: text must be 0. If the judge missed it, force an issue.
                has_any_text_signal = bool(extracted_text_str) or (text_detected is True)
                if is_realistic and has_any_text_signal:
                    already_flagged = any(
                        str(it.get("type") or "").strip().lower() == "excessive_text"
                        or str(it.get("issue_code") or "").strip() == "S3_TEXT_POLICY_VIOLATION_REALISTIC"
                        for it in img_issues
                        if isinstance(it, dict)
                    )
                    if not already_flagged:
                        img_issues.append(
                            {
                                "severity": "major",
                                "type": "excessive_text",
                                "description": "REALISTIC image contains text, but REALISTIC policy requires TEXT=0 (zero tolerance).",
                                "issue_code": "S3_TEXT_POLICY_VIOLATION_REALISTIC",
                                "recommended_fix_target": "S3_PROMPT",
                                "prompt_patch_hint": "Enforce S3 constraint_block TEXT_POLICY_ZERO_TOLERANCE for REALISTIC; regenerate with zero text.",
                                "confidence": 0.85,
                            }
                        )
                    # Also lift to card-level issues so downstream backlog tools (that only read card issues) can see it.
                    if isinstance(issues, list):
                        issues.append(
                            {
                                "severity": "major",
                                "type": "image_text_policy_violation",
                                "description": (
                                    "REALISTIC image text policy violated (TEXT=0 required). "
                                    f"text_detected={text_detected!r}, extracted_text={extracted_text_str[:120]!r}"
                                ),
                                "issue_code": "S3_TEXT_POLICY_VIOLATION_REALISTIC",
                                "recommended_fix_target": "S3_PROMPT",
                                "prompt_patch_hint": "Enforce S3 constraint_block TEXT_POLICY_ZERO_TOLERANCE for REALISTIC; regenerate with zero text.",
                                "confidence": 0.8,
                            }
                        )

                # DIAGRAM policy: text may exist (limited). We only care about OCR quality + forbidden tokens,
                # and we should NOT flag a DIAGRAM as policy-violating just because text exists.
                # Guardrail: if the judge emitted "excessive_text" for DIAGRAM but OCR text looks small/clean,
                # downgrade/remove that issue to avoid over-blocking final distribution.
                if (not is_realistic) and has_any_text_signal:
                    # Simple heuristics based on OCR string (LLM-provided).
                    # We cannot do local OCR, so rely on extracted_text_str.
                    ocr = extracted_text_str
                    ocr_l = ocr.lower()
                    # Estimate "text elements" roughly by counting short tokens.
                    tokens = [t for t in ocr.replace("\n", " ").split(" ") if t.strip()]
                    est_text_elements = len(tokens)
                    has_forbidden_laterality = any(
                        w in ocr_l.split()
                        for w in ("left", "right", "l", "r")
                    )
                    # Garble heuristic: lots of non-alnum chars relative to length.
                    if ocr:
                        non_alnum = sum(1 for ch in ocr if not ch.isalnum() and ch not in (" ", "\n", "-", "_", ":", ";", ".", ",", "(", ")", "/"))
                        garble_ratio = non_alnum / max(1, len(ocr))
                    else:
                        garble_ratio = 0.0

                    # If OCR indicates forbidden laterality tokens, ensure an issue exists.
                    if has_forbidden_laterality:
                        img_issues.append(
                            {
                                "severity": "major",
                                "type": "text_forbidden_token",
                                "description": "DIAGRAM image OCR text contains forbidden laterality token(s) (Left/Right/L/R).",
                                "issue_code": "S3_TEXT_POLICY_FORBIDDEN_LATERALITY_TOKEN",
                                "recommended_fix_target": "S3_PROMPT",
                                "prompt_patch_hint": "In DIAGRAM prompts: forbid laterality text tokens (Left/Right/L/R). Use arrows/circles instead.",
                                "confidence": 0.75,
                            }
                        )

                    # If OCR looks garbled/unreadable, flag it (non-blocking).
                    if ocr and (garble_ratio >= 0.25):
                        img_issues.append(
                            {
                                "severity": "minor",
                                "type": "unreadable_text",
                                "description": "DIAGRAM image contains text but OCR appears garbled/unreadable. Prefer fewer/cleaner labels.",
                                "issue_code": "S5_OCR_TEXT_UNREADABLE",
                                "recommended_fix_target": "S3_PROMPT",
                                "prompt_patch_hint": "Simplify labels (short ASCII words), increase contrast/size, or omit text if it distorts.",
                                "confidence": 0.6,
                            }
                        )

                    # Downgrade/remove DIAGRAM excessive_text unless it truly looks excessive.
                    # Threshold aligns with current DIAGRAM policy: excessive if ~>=8 text elements.
                    cleaned_img_issues = []
                    for it in img_issues:
                        if not isinstance(it, dict):
                            continue
                        tl = str(it.get("type") or "").strip().lower()
                        if tl == "excessive_text" and est_text_elements < 8 and not has_forbidden_laterality:
                            # Keep as minor note rather than policy violation.
                            it = dict(it)
                            it["severity"] = "minor"
                            it["description"] = (
                                "DIAGRAM image contains text, but it appears within the allowed limited-label budget; "
                                "flagging only for awareness."
                            )
                            it["issue_code"] = "S5_DIAGRAM_TEXT_PRESENT_OK"
                            it["recommended_fix_target"] = "NONE"
                            it.pop("prompt_patch_hint", None)
                        cleaned_img_issues.append(it)
                    img_issues = cleaned_img_issues

                card_image_validation = {
                    "blocking_error": bool(image_validation_raw.get("blocking_error", False)),
                    "anatomical_accuracy": float(image_validation_raw.get("anatomical_accuracy", 1.0)),
                    "prompt_compliance": float(image_validation_raw.get("prompt_compliance", 1.0)),
                    "text_image_consistency": float(image_validation_raw.get("text_image_consistency", 1.0)),
                    "image_quality": int(image_validation_raw.get("image_quality", 5)),
                    "safety_flag": bool(image_validation_raw.get("safety_flag", False)),
                    "issues": _deduplicate_issues(img_issues),
                    "image_path": str(image_path) if image_path else "",
                }

                if text_detected is not None:
                    card_image_validation["text_detected"] = text_detected
                if extracted_text_str:
                    card_image_validation["extracted_text"] = extracted_text_str
                if modality_match is not None:
                    card_image_validation["modality_match"] = modality_match
                if landmarks_present is not None:
                    card_image_validation["landmarks_present"] = landmarks_present
                
                # Add Realistic-specific metrics (only for REALISTIC images)
                if is_realistic:
                    # Extract realistic metrics from LLM response
                    realistic_appearance = image_validation_raw.get("realistic_appearance")
                    modality_texture = image_validation_raw.get("modality_appropriate_texture")
                    conspicuity = image_validation_raw.get("conspicuity_control")
                    
                    # Normalize to float (0.0/0.5/1.0) or default to 1.0 if not provided
                    if realistic_appearance is not None:
                        try:
                            card_image_validation["realistic_appearance"] = float(realistic_appearance)
                        except (ValueError, TypeError):
                            card_image_validation["realistic_appearance"] = 1.0
                    else:
                        card_image_validation["realistic_appearance"] = 1.0  # Default if not evaluated
                    
                    if modality_texture is not None:
                        try:
                            card_image_validation["modality_appropriate_texture"] = float(modality_texture)
                        except (ValueError, TypeError):
                            card_image_validation["modality_appropriate_texture"] = 1.0
                    else:
                        card_image_validation["modality_appropriate_texture"] = 1.0
                    
                    if conspicuity is not None:
                        try:
                            card_image_validation["conspicuity_control"] = float(conspicuity)
                        except (ValueError, TypeError):
                            card_image_validation["conspicuity_control"] = 1.0
                    else:
                        card_image_validation["conspicuity_control"] = 1.0
                else:
                    # For DIAGRAM images, set realistic metrics to None (not applicable)
                    card_image_validation["realistic_appearance"] = None
                    card_image_validation["modality_appropriate_texture"] = None
                    card_image_validation["conspicuity_control"] = None
        
        result = {
            "blocking_error": blocking_error,
            "technical_accuracy": technical_accuracy,
            "educational_quality": educational_quality,
            "issues": _deduplicate_issues(issues),
            "rag_evidence": rag_evidence,
        }
        if difficulty is not None:
            result["difficulty"] = difficulty
        
        # Add image validation if available
        if card_image_validation:
            result["card_image_validation"] = card_image_validation
        
        # Calculate regeneration trigger scores (for efficient downstream processing)
        # This avoids redundant LLM calls in Option C repair and assignment generation
        try:
            # Prepare score calculation input (matches score_calculator.py expected format)
            score_input = {
                "s5_blocking_error": blocking_error,
                "s5_technical_accuracy": technical_accuracy,
                "s5_educational_quality": educational_quality,
                "s5_card_image_blocking_error": card_image_validation.get("blocking_error", False) if card_image_validation else False,
                "s5_card_image_safety_flag": card_image_validation.get("safety_flag", False) if card_image_validation else False,
                "s5_card_image_quality": card_image_validation.get("image_quality") if card_image_validation else None,
                "s5_card_image_anatomical_accuracy": card_image_validation.get("anatomical_accuracy") if card_image_validation else None,
                "s5_card_image_prompt_compliance": card_image_validation.get("prompt_compliance") if card_image_validation else None,
            }
            
            # Calculate combined score (card + image)
            result["regeneration_trigger_score"] = calculate_s5_regeneration_trigger_score(score_input)
            
            # Calculate card-only score (for CARD_REGEN decision)
            result["card_regeneration_trigger_score"] = calculate_s5_card_regeneration_trigger_score(score_input)
            
            # Calculate image-only score (for IMAGE_ONLY_REGEN decision)
            image_score = calculate_s5_image_regeneration_trigger_score(score_input)
            if image_score is not None:
                result["image_regeneration_trigger_score"] = image_score
            # If None, image validation data doesn't exist (no image or not evaluated)
            
        except Exception as e:
            # Best-effort: if score calculation fails, don't block validation
            # Log but continue (scores will be missing, downstream can compute if needed)
            print(f"Warning: Failed to calculate regeneration trigger scores for card {card_id}: {e}", file=sys.stderr)
        
        return result
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error: S5 S2 card validation exception for card {card_id}: {e}", file=sys.stderr)
        group_id = entity_context.get("group_id", "unknown")
        log_s5_error(
            out_dir=base_dir,
            run_tag=run_tag,
            arm=arm,
            group_id=group_id,
            card_id=card_id,
            validation_type="s2_card",
            error_type="ValidationError",
            error_class=type(e).__name__,
            error_message=str(e),
            traceback_str=error_traceback,
            recovered=False,
        )
        return {
            "blocking_error": False,
            "technical_accuracy": 1.0,
            "educational_quality": 4,
            "issues": [],
            "rag_evidence": [],
        }


# =========================
# Main S5 Validation Function
# =========================

# Thread-local LLM call counter for per-group timing metrics.
_S5_LLM_CALL_COUNTER = threading.local()


def _call_llm_tracked(*args, **kwargs):
    """
    Wrapper around call_llm that increments a per-thread counter when available.
    This enables per-group llm_call_count measurement even when groups are processed in parallel.
    """
    try:
        # Only increment if a counter has been initialized for this thread.
        if hasattr(_S5_LLM_CALL_COUNTER, "count") and _S5_LLM_CALL_COUNTER.count is not None:
            _S5_LLM_CALL_COUNTER.count += 1
    except Exception:
        # Best-effort only; never fail validation due to metrics bookkeeping.
        pass
    if call_llm is None:
        raise RuntimeError("call_llm function not available")
    return call_llm(*args, **kwargs)


def _resolve_cli_path(path_str: Optional[str], base_dir: Path) -> Optional[Path]:
    """Resolve a CLI-provided path. Relative paths are interpreted relative to base_dir."""
    if not path_str:
        return None
    p = Path(path_str)
    if not p.is_absolute():
        p = base_dir / p
    return p.resolve()


def _relpath_or_abs(p: Path, base_dir: Path) -> str:
    """Return path relative to base_dir when possible; otherwise return absolute path."""
    try:
        return str(p.resolve().relative_to(base_dir))
    except Exception:
        return str(p.resolve())


def _infer_is_postrepair(is_postrepair_opt: Optional[bool], output_path: Optional[Path]) -> bool:
    if is_postrepair_opt is not None:
        return bool(is_postrepair_opt)
    if output_path is None:
        return False
    return "__postrepair" in output_path.name


def run_s5_validation(
    base_dir: Path,
    run_tag: str,
    arm: str,
    group_id: Optional[str] = None,
    workers_s5: int = 1,
    progress_logger: Optional[Any] = None,
    prompt_registry: Optional[str] = None,
    s1_path_override: Optional[Path] = None,
    s2_path_override: Optional[Path] = None,
    output_path_override: Optional[Path] = None,
    is_postrepair: Optional[bool] = None,
    s5_mode: str = "all",
    resume: bool = False,
) -> None:
    """
    Run S5 validation for a single group or all groups.
    
    Args:
        base_dir: Base directory of MeducAI project
        run_tag: Run tag identifier
        arm: Arm identifier (A, B, C, D, E, F)
        group_id: Optional group ID (if None, process all groups)
        workers_s5: Number of parallel workers for group processing (default: 1)
        s5_mode: Execution mode - 'all' (default, S1+S2 together), 
                 's1_only' (S1 table eval only, saves partial),
                 's2_only' (S2 card eval only, requires partial from s1_only)
        resume: If True and s5_mode is 's1_only', skip groups already present
                in the partial file instead of clearing it (default: False)
    """
    if not LLM_INFRASTRUCTURE_AVAILABLE:
        raise RuntimeError("LLM infrastructure not available. Cannot run S5 validation.")
    
    # Setup paths
    data_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    s1_path = s1_path_override.resolve() if s1_path_override else (data_dir / f"stage1_struct__arm{arm}.jsonl")
    s2_path = s2_path_override.resolve() if s2_path_override else resolve_s2_results_path(data_dir, arm)
    s3_image_spec_path = data_dir / f"s3_image_spec__arm{arm}.jsonl"
    s4_manifest_baseline_path = data_dir / f"s4_image_manifest__arm{arm}.jsonl"
    s4_manifest_repaired_path = _infer_repaired_variant_path(s4_manifest_baseline_path)
    output_path = output_path_override.resolve() if output_path_override else (data_dir / f"s5_validation__arm{arm}.jsonl")
    is_postrepair_resolved = _infer_is_postrepair(is_postrepair, output_path_override or output_path)
    if (output_path_override is None) and is_postrepair_resolved:
        output_path = data_dir / f"s5_validation__arm{arm}__postrepair.jsonl"
    # Safety guard: avoid accidentally overwriting baseline output when explicitly marked postrepair.
    if is_postrepair_resolved and output_path.name == f"s5_validation__arm{arm}.jsonl":
        raise ValueError(
            f"Refusing to write postrepair output to baseline path: {output_path}. "
            f"Use --output_path ...__postrepair.jsonl or omit --output_path and pass --is_postrepair true."
        )

    # S5 mode: partial file path for s1_only/s2_only split execution
    s5_partial_path = data_dir / f"s5_s1_partial__arm{arm}.jsonl"
    if s5_mode == "s1_only":
        # s1_only mode writes to partial file, not the final output
        output_path = s5_partial_path
        if progress_logger:
            progress_logger.info(f"[S5] Mode: s1_only - will write S1 table evaluations to {output_path}")
        else:
            print(f"[S5] Mode: s1_only - will write S1 table evaluations to {output_path}", flush=True)
    elif s5_mode == "s2_only":
        # s2_only mode requires partial file from s1_only run
        if not s5_partial_path.exists():
            raise FileNotFoundError(
                f"[S5] s2_only mode requires partial file from s1_only run: {s5_partial_path}\n"
                f"Run with --s5_mode s1_only first to generate S1 evaluations."
            )
        if progress_logger:
            progress_logger.info(f"[S5] Mode: s2_only - will load S1 partials from {s5_partial_path}")
        else:
            print(f"[S5] Mode: s2_only - will load S1 partials from {s5_partial_path}", flush=True)
    else:
        # all mode: standard behavior
        if progress_logger:
            progress_logger.info(f"[S5] Mode: all - will run S1+S2 evaluations together")
        else:
            print(f"[S5] Mode: all - will run S1+S2 evaluations together", flush=True)

    # Load S1 partials for s2_only mode
    s1_partials: Dict[str, Dict[str, Any]] = {}
    if s5_mode == "s2_only":
        try:
            with open(s5_partial_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    partial = json.loads(line)
                    gid = partial.get("group_id")
                    if gid:
                        s1_partials[gid] = partial
            if progress_logger:
                progress_logger.info(f"[S5] Loaded {len(s1_partials)} S1 partials from {s5_partial_path}")
            else:
                print(f"[S5] Loaded {len(s1_partials)} S1 partials from {s5_partial_path}", flush=True)
        except Exception as e:
            raise RuntimeError(f"[S5] Failed to load S1 partials from {s5_partial_path}: {e}")

    # Load prompt bundle once per run for judge traceability / reproducibility
    prompt_bundle: Optional[Dict[str, Any]] = None
    try:
        if load_prompt_bundle is None:
            raise RuntimeError("load_prompt_bundle function not available")
        prompt_bundle = load_prompt_bundle(str(base_dir), registry_path=prompt_registry)
        if progress_logger:
            prompt_bundle_hash = str(prompt_bundle.get("prompt_bundle_hash", "")) if prompt_bundle else ""
            reg_path = str(prompt_bundle.get("registry_path", "")) if prompt_bundle else ""
            progress_logger.info(f"[S5] Loaded prompt bundle (hash={prompt_bundle_hash[:12]}) from registry={reg_path}")
    except Exception as e:
        # If user explicitly provided a registry, fail fast to avoid accidental "judge drift".
        if prompt_registry:
            raise
        # Otherwise, keep best-effort behavior: validation can still proceed with fallback prompt loading inside validate_*.
        if progress_logger:
            progress_logger.warning(f"[S5] Failed to preload prompt bundle: {e} (will fallback to default registry per call)")
        else:
            print(f"Warning: Failed to preload prompt bundle: {e} (will fallback to default registry per call)", file=sys.stderr)
    
    # Load S4 manifest and S3 image specs for image evaluation (optional, best-effort)
    s4_manifest: Optional[Dict[str, Dict[str, Any]]] = None
    s3_image_specs: Optional[Dict[str, Dict[str, Any]]] = None
    try:
        if s4_manifest_baseline_path.exists():
            # Postrepair validation should prefer repaired images when available, but never lose baseline coverage.
            if is_postrepair_resolved and s4_manifest_repaired_path.exists():
                baseline_only = load_s4_manifest(s4_manifest_baseline_path)
                repaired_only = load_s4_manifest(s4_manifest_repaired_path)
                merged = load_s4_manifest_merged(
                    base_dir=base_dir,
                    s4_manifest_baseline_path=s4_manifest_baseline_path,
                    s4_manifest_repaired_path=s4_manifest_repaired_path,
                )
                s4_manifest = merged
                if progress_logger:
                    progress_logger.info(
                        f"[S5] Loaded S4 manifests (postrepair merge): "
                        f"baseline={len(baseline_only)} + repaired={len(repaired_only)} "
                        f"=> merged={len(merged)}"
                    )
                else:
                    print(
                        f"[S5] Loaded S4 manifests (postrepair merge): "
                        f"baseline={len(baseline_only)} + repaired={len(repaired_only)} "
                        f"=> merged={len(merged)}",
                        flush=True,
                    )
            else:
                s4_manifest = load_s4_manifest(s4_manifest_baseline_path)
                if progress_logger:
                    progress_logger.info(f"[S5] Loaded S4 baseline manifest: {len(s4_manifest)} entries")
    except Exception as e:
        print(f"Warning: Failed to load S4 manifest: {e}", file=sys.stderr)
    
    try:
        if s3_image_spec_path.exists():
            s3_image_specs = load_s3_image_specs(s3_image_spec_path)
            if progress_logger:
                progress_logger.info(f"[S5] Loaded S3 image specs: {len(s3_image_specs)} entries")
    except Exception as e:
        print(f"Warning: Failed to load S3 image specs: {e}", file=sys.stderr)
    
    # MI-CLEAR-LLM: Set up metrics path for LLM call logging
    # This ensures call_llm can log metrics to llm_metrics.jsonl
    try:
        # Access the global _LLM_METRICS_PATH from the loaded module
        generate_json_module = sys.modules.get("meducai_generate_json")
        if generate_json_module:
            metrics_path = data_dir / "logs" / "llm_metrics.jsonl"
            setattr(generate_json_module, "_LLM_METRICS_PATH", metrics_path)
            # Ensure logs directory exists
            metrics_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not set up metrics path for MI-CLEAR-LLM logging: {e}", file=sys.stderr)
    
    # Initialize LLM clients
    # Note: call_llm creates clients internally, so we just need ProviderClients class
    if ProviderClients is None:
        raise RuntimeError("LLM infrastructure not properly initialized: ProviderClients not available")
    if call_llm is None:
        raise RuntimeError("LLM infrastructure not properly initialized: call_llm not available")
    
    # Create empty ProviderClients (call_llm will handle client creation internally)
    clients = ProviderClients()
    
    # Load S1 structure (list of groups)
    s1_groups = load_s1_structure(s1_path)
    
    # Load S2 results
    s2_results = load_s2_results(s2_path)
    
    # Filter by group_id if specified
    if group_id:
        s1_groups = [g for g in s1_groups if g.get("group_id") == group_id]
        s2_results = [r for r in s2_results if r.get("group_id") == group_id]
    
    # Group S2 results by group_id
    groups_to_process = {}
    for s2_result in s2_results:
        current_group_id = s2_result.get("group_id")
        if not current_group_id:
            continue
        if current_group_id not in groups_to_process:
            groups_to_process[current_group_id] = []
        groups_to_process[current_group_id].append(s2_result)
    
    # Detect groups with S1 data but no S2 results
    s1_group_ids = {g.get("group_id") for g in s1_groups if g.get("group_id")}
    s2_group_ids = set(groups_to_process.keys())
    missing_s2_groups = {gid for gid in s1_group_ids if gid and gid not in s2_group_ids}
    
    if missing_s2_groups:
        if progress_logger:
            progress_logger.warning(f"[S5] {len(missing_s2_groups)} groups from S1 are missing S2 results")
            for gid in sorted(missing_s2_groups):
                progress_logger.warning(f"[S5] Missing S2: {gid}")
                # Log to error log
                log_s5_error(
                    out_dir=data_dir,
                    run_tag=run_tag,
                    arm=arm,
                    group_id=gid,
                    card_id=None,
                    validation_type="group",
                    error_type="MissingS2Data",
                    error_class="ValueError",
                    error_message=f"No S2 results found for group {gid}",
                    recovered=False,
                )
            progress_logger.info("[S5] These groups will be skipped during validation.")
            progress_logger.info("[S5] Use generate_missing_entities_s2_s5.py to generate S2 cards for missing groups.")
        else:
            print(f"\n[WARNING] S5 validation: {len(missing_s2_groups)} groups from S1 are missing S2 results:", file=sys.stderr, flush=True)
            for gid in sorted(missing_s2_groups):
                print(f"  - {gid}", file=sys.stderr, flush=True)
                # Log to error log
                log_s5_error(
                    out_dir=data_dir,
                    run_tag=run_tag,
                    arm=arm,
                    group_id=gid,
                    card_id=None,
                    validation_type="group",
                    error_type="MissingS2Data",
                    error_class="ValueError",
                    error_message=f"No S2 results found for group {gid}",
                    recovered=False,
                )
            print(f"\n  These groups will be skipped during validation.", file=sys.stderr, flush=True)
            print(f"  Use generate_missing_entities_s2_s5.py to generate S2 cards for missing groups.\n", file=sys.stderr, flush=True)
    
    # Helper function to process a single group
    def process_group(
        current_group_id: str,
        s2_results_for_group: List[Dict[str, Any]],
        s4_manifest: Optional[Dict[str, Dict[str, Any]]] = None,
        s3_image_specs: Optional[Dict[str, Dict[str, Any]]] = None,
        # Progress tracking parameters (for real-time progress updates during S2 validation)
        progress_logger_ref: Optional[Any] = None,
        entity_idx_offset: int = 0,
        card_idx_offset: int = 0,
        total_entities_count: int = 0,
        total_cards_count: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Process validation for a single group."""
        start_time = time.time()
        start_ts_utc = datetime.utcnow().isoformat() + "Z"
        # Initialize per-thread LLM call counter for this group.
        try:
            _S5_LLM_CALL_COUNTER.count = 0
        except Exception:
            pass
        try:
            # Log group processing start
            log_s5_processing(
                out_dir=data_dir,
                run_tag=run_tag,
                arm=arm,
                group_id=current_group_id,
                card_id=None,
                action="start",
                validation_type="group",
            )
            
            # Find matching S1 data for this group
            s1_group_data = next((g for g in s1_groups if g.get("group_id") == current_group_id), None)
            
            if not s1_group_data:
                print(f"Warning: No S1 data found for group {current_group_id}", file=sys.stderr)
                log_s5_error(
                    out_dir=data_dir,
                    run_tag=run_tag,
                    arm=arm,
                    group_id=current_group_id,
                    card_id=None,
                    validation_type="group",
                    error_type="MissingS1Data",
                    error_class="ValueError",
                    error_message=f"No S1 data found for group {current_group_id}",
                    recovered=False,
                )
                log_s5_processing(
                    out_dir=data_dir,
                    run_tag=run_tag,
                    arm=arm,
                    group_id=current_group_id,
                    card_id=None,
                    action="skipped",
                    validation_type="group",
                    duration_ms=(time.time() - start_time) * 1000,
                )
                return None
            
            # Create a new ProviderClients instance for this thread (thread-safe)
            if ProviderClients is None:
                raise RuntimeError("LLM infrastructure not properly initialized: ProviderClients not available")
            thread_clients = ProviderClients()
            
            # === S5 MODE BRANCHING ===
            
            # s2_only mode: Load S1 validation from partial file, skip S1 LLM call
            if s5_mode == "s2_only":
                partial_data = s1_partials.get(current_group_id)
                if not partial_data:
                    print(f"Warning: No S1 partial found for group {current_group_id} (skipping)", file=sys.stderr)
                    log_s5_error(
                        out_dir=data_dir,
                        run_tag=run_tag,
                        arm=arm,
                        group_id=current_group_id,
                        card_id=None,
                        validation_type="group",
                        error_type="MissingS1Partial",
                        error_class="ValueError",
                        error_message=f"No S1 partial found for group {current_group_id}",
                        recovered=False,
                    )
                    return None
                s1_validation = partial_data.get("s1_table_validation")
                if progress_logger:
                    progress_logger.debug(f"[S5] Loaded S1 partial for group {current_group_id}")
            else:
                # all or s1_only mode: Validate S1 table with LLM
                s1_validation = validate_s1_table(
                    s1_group_data, thread_clients, current_group_id, base_dir, run_tag, arm,
                    s4_manifest=s4_manifest, s3_image_specs=s3_image_specs, prompt_bundle=prompt_bundle
                )
            
            # s1_only mode: Return partial result (S1 only, no S2 evaluation)
            if s5_mode == "s1_only":
                end_ts_utc = datetime.utcnow().isoformat() + "Z"
                duration_ms = (time.time() - start_time) * 1000
                llm_call_count = 0
                try:
                    llm_call_count = int(getattr(_S5_LLM_CALL_COUNTER, "count", 0) or 0)
                except Exception:
                    llm_call_count = 0
                
                partial_result = {
                    "schema_version": "S5_S1_PARTIAL_v1.0",
                    "run_tag": run_tag,
                    "group_id": current_group_id,
                    "arm": arm,
                    "s1_completed_at": end_ts_utc,
                    "s1_table_validation": s1_validation,
                    "s1_model_info": {
                        "s1_table_model": S5_S1_TABLE_MODEL,
                        "s1_table_thinking": S5_S1_TABLE_THINKING,
                        "s1_table_rag_enabled": S5_S1_TABLE_RAG_ENABLED,
                    },
                    "s1_timing": {
                        "start_utc": start_ts_utc,
                        "end_utc": end_ts_utc,
                        "duration_ms": round(duration_ms, 2),
                        "llm_call_count": llm_call_count,
                    },
                }
                
                log_s5_processing(
                    out_dir=data_dir,
                    run_tag=run_tag,
                    arm=arm,
                    group_id=current_group_id,
                    card_id=None,
                    action="completed",
                    validation_type="group_s1_only",
                    duration_ms=duration_ms,
                    model_used=S5_S1_TABLE_MODEL,
                )
                
                return partial_result
            
            # === Continue with S2 evaluation (all or s2_only mode) ===
            
            # Validate S2 cards (aggregate across all entities in this group)
            s2_cards_validation = []
            entity_idx_in_group = 0
            card_idx_in_group = 0
            
            for s2_result in s2_results_for_group:
                entity_id = s2_result.get("entity_id", "")
                entity_name = s2_result.get("entity_name", "")
                
                # Update entity progress (using offset for global position)
                entity_idx_in_group += 1
                if progress_logger_ref and total_entities_count > 0:
                    global_entity_idx = entity_idx_offset + entity_idx_in_group
                    progress_logger_ref.update_entity(
                        global_entity_idx, total_entities_count, entity_id=entity_id
                    )
                    progress_logger_ref.reset_card()
                
                # Detect entity type for validation (reuse logic from S2)
                entity_type = "disease"  # Default fallback
                visual_type_category = s1_group_data.get("visual_type_category", "General")
                if detect_entity_type_for_s2:
                    try:
                        entity_type = detect_entity_type_for_s2(
                            entity_name=entity_name,
                            visual_type_category=visual_type_category
                        )
                    except Exception as e:
                        print(f"Warning: Failed to detect entity type for {entity_name}: {e}", file=sys.stderr)
                        entity_type = "disease"  # Fallback to default
                
                # Prepare entity context from S1
                entity_context = {
                    "entity_id": entity_id,
                    "entity_name": entity_name,
                    "group_id": current_group_id,
                    "master_table_markdown_kr": s1_group_data.get("master_table_markdown_kr", ""),
                    "visual_type_category": visual_type_category,
                    "entity_type": entity_type,
                }
                
                for card_loop_idx, card in enumerate(s2_result.get("anki_cards", [])):
                    # Generate card_id if not present (using entity_id, card_role, and index)
                    card_id = card.get("card_id")
                    card_role = card.get("card_role", "UNKNOWN")
                    if not card_id:
                        card_id = f"{entity_id}__{card_role}__{card_loop_idx}"
                    
                    card_validation = validate_s2_card(
                        card, entity_context, thread_clients, card_id, base_dir, run_tag, arm,
                        s4_manifest=s4_manifest, s3_image_specs=s3_image_specs, prompt_bundle=prompt_bundle
                    )
                    s2_cards_validation.append(
                        build_s2_card_validation_record(
                            card_id=card_id,
                            card=card,
                            entity_id=entity_id or None,
                            entity_name=entity_name or None,
                            entity_type=entity_type or None,
                            card_validation=card_validation,
                        )
                    )
                    
                    # Update card progress (after validation, for real-time feedback)
                    card_idx_in_group += 1
                    if progress_logger_ref and total_cards_count > 0:
                        global_card_idx = card_idx_offset + card_idx_in_group
                        progress_logger_ref.update_card(
                            global_card_idx, total_cards_count, card_role=card_role
                        )
            
            # Calculate summary statistics
            total_cards = len(s2_cards_validation)
            blocking_errors = sum(1 for c in s2_cards_validation if c.get("blocking_error"))
            mean_technical_accuracy = (
                sum(c.get("technical_accuracy", 0.0) for c in s2_cards_validation) / total_cards
                if total_cards > 0 else 0.0
            )
            mean_educational_quality = (
                sum(c.get("educational_quality", 0) for c in s2_cards_validation) / total_cards
                if total_cards > 0 else 0
            )
            
            # Build validation result
            prompt_bundle_section: Dict[str, Any] = {}
            if isinstance(prompt_bundle, dict):
                try:
                    reg_path_abs = str(prompt_bundle.get("registry_path", "") or "")
                    reg_path_rel = reg_path_abs
                    if reg_path_abs:
                        try:
                            reg_path_rel = str(Path(reg_path_abs).resolve().relative_to(base_dir))
                        except Exception:
                            reg_path_rel = reg_path_abs
                    prompt_file_ids = prompt_bundle.get("prompt_file_ids", {}) or {}
                    prompt_bundle_section = {
                        "prompt_registry_path": reg_path_rel,
                        "prompt_bundle_hash": prompt_bundle.get("prompt_bundle_hash", ""),
                        "prompt_file_ids": prompt_file_ids,
                        "prompt_file_ids_s5": {k: v for k, v in prompt_file_ids.items() if str(k).startswith("S5_")},
                    }
                except Exception:
                    prompt_bundle_section = {}

            # Build validation result (core payload; timing is appended later)
            # Include s5_mode and s1_partial_source for traceability
            s1_partial_source = None
            if s5_mode == "s2_only":
                partial_data = s1_partials.get(current_group_id, {})
                s1_partial_source = {
                    "s1_completed_at": partial_data.get("s1_completed_at"),
                    "s1_partial_file": _relpath_or_abs(s5_partial_path, base_dir),
                }
            
            validation_result = {
                "schema_version": "S5_VALIDATION_v1.0",
                "run_tag": run_tag,
                "group_id": current_group_id,
                "arm": arm,
                "validation_timestamp": datetime.utcnow().isoformat() + "Z",
                "s5_is_postrepair": bool(is_postrepair_resolved),
                "s5_mode": s5_mode,  # Track execution mode for audit
                "inputs": {
                    "stage1_struct_path": _relpath_or_abs(s1_path, base_dir),
                    "s2_results_path": _relpath_or_abs(s2_path, base_dir),
                    "s1_partial_source": s1_partial_source,  # Only populated in s2_only mode
                },
                "outputs": {
                    "s5_validation_path": _relpath_or_abs(output_path, base_dir),
                },
                "s5_prompt_bundle": prompt_bundle_section,
                "s5_model_info": {
                    "s1_table_model": S5_S1_TABLE_MODEL,
                    "s1_table_thinking": S5_S1_TABLE_THINKING,
                    "s1_table_rag_enabled": S5_S1_TABLE_RAG_ENABLED,
                    "s2_card_model": S5_S2_CARD_MODEL,
                    "s2_card_thinking": S5_S2_CARD_THINKING,
                    "s2_card_rag_enabled": S5_S2_CARD_RAG_ENABLED,
                },
                "s1_table_validation": s1_validation,
                "s2_cards_validation": {
                    "cards": s2_cards_validation,
                    "summary": {
                        "total_cards": total_cards,
                        "blocking_errors": blocking_errors,
                        "mean_technical_accuracy": mean_technical_accuracy,
                        "mean_educational_quality": mean_educational_quality,
                    },
                },
            }
            
            # Generate S5 snapshot ID.
            # Note: computed before attaching timing fields to reduce "run clock" noise.
            s5_model_version = f"{S5_S1_TABLE_MODEL.split('/')[-1]}_v1"
            validation_result["s5_snapshot_id"] = generate_s5_snapshot_id(
                run_tag, current_group_id, arm, s5_model_version, validation_result
            )

            # Attach timing after snapshot_id calculation
            end_ts_utc = datetime.utcnow().isoformat() + "Z"
            duration_ms = (time.time() - start_time) * 1000
            llm_call_count = 0
            try:
                llm_call_count = int(getattr(_S5_LLM_CALL_COUNTER, "count", 0) or 0)
            except Exception:
                llm_call_count = 0
            validation_result["s5_timing"] = {
                "start_utc": start_ts_utc,
                "end_utc": end_ts_utc,
                "duration_ms": duration_ms,
                "llm_call_count": llm_call_count,
            }
            
            # Log group processing complete
            log_s5_processing(
                out_dir=data_dir,
                run_tag=run_tag,
                arm=arm,
                group_id=current_group_id,
                card_id=None,
                action="complete",
                validation_type="group",
                duration_ms=duration_ms,
                model_used=S5_S1_TABLE_MODEL,
                s5_snapshot_id=validation_result["s5_snapshot_id"],
                s2_cards_count=total_cards,
                s2_cards_missing=False,
            )
            
            return validation_result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            import traceback
            error_traceback = traceback.format_exc()
            print(f"Error processing group {current_group_id}: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            
            # Log error
            log_s5_error(
                out_dir=data_dir,
                run_tag=run_tag,
                arm=arm,
                group_id=current_group_id,
                card_id=None,
                validation_type="group",
                error_type="ProcessingError",
                error_class=type(e).__name__,
                error_message=str(e),
                traceback_str=error_traceback,
                recovered=False,
            )
            
            log_s5_processing(
                out_dir=data_dir,
                run_tag=run_tag,
                arm=arm,
                group_id=current_group_id,
                card_id=None,
                action="failed",
                validation_type="group",
                duration_ms=duration_ms,
            )
            
            return None
    
    # Process groups (sequentially or in parallel based on workers_s5)
    total_groups = len(groups_to_process)
    
    # Count total entities and cards for progress tracking
    total_entities = sum(len(s2_results_list) for s2_results_list in groups_to_process.values())
    total_cards = sum(
        len(s2_result.get("anki_cards", []))
        for s2_results_list in groups_to_process.values()
        for s2_result in s2_results_list
    )
    
    # Initialize output file (overwrite for s1_only, clear for fresh runs)
    # s1_only mode: overwrite unless resume mode is enabled
    # all/s2_only mode: append behavior (existing behavior for resumability)
    completed_group_ids: Set[str] = set()
    
    if s5_mode == "s1_only":
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if resume and output_path.exists():
            # Load completed group_ids from existing partial file
            with open(output_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            partial = json.loads(line)
                            gid = partial.get("group_id")
                            if gid:
                                completed_group_ids.add(gid)
                        except json.JSONDecodeError:
                            pass
            # Filter out already-completed groups
            original_count = len(groups_to_process)
            groups_to_process = {
                gid: s2_list 
                for gid, s2_list in groups_to_process.items() 
                if gid not in completed_group_ids
            }
            # Update total_groups count after filtering
            total_groups = len(groups_to_process)
            # Recalculate total_entities and total_cards for accurate progress bars
            total_entities = sum(len(s2_results_list) for s2_results_list in groups_to_process.values())
            total_cards = sum(
                len(s2_result.get("anki_cards", []))
                for s2_results_list in groups_to_process.values()
                for s2_result in s2_results_list
            )
            if progress_logger:
                progress_logger.info(
                    f"[S5] Resume mode: {len(completed_group_ids)} groups already completed, "
                    f"{total_groups} remaining (of {original_count} total)"
                )
            else:
                print(
                    f"[S5] Resume mode: {len(completed_group_ids)} groups already completed, "
                    f"{total_groups} remaining (of {original_count} total)",
                    flush=True
                )
        else:
            # Clear the partial file before starting (original behavior)
            with open(output_path, "w", encoding="utf-8") as f:
                pass  # Create empty file
            if progress_logger:
                progress_logger.info(f"[S5] Initialized partial output file: {output_path}")
            else:
                print(f"[S5] Initialized partial output file: {output_path}", flush=True)
    
    # s2_only or all mode: Resume support
    elif s5_mode in ("s2_only", "all") and resume and output_path.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load completed group_ids from existing validation file
        with open(output_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        result = json.loads(line)
                        gid = result.get("group_id")
                        if gid:
                            completed_group_ids.add(gid)
                    except json.JSONDecodeError:
                        pass
        
        # Filter out already-completed groups
        original_count = len(groups_to_process)
        groups_to_process = {
            gid: s2_list 
            for gid, s2_list in groups_to_process.items() 
            if gid not in completed_group_ids
        }
        
        # Recalculate totals after filtering
        total_groups = len(groups_to_process)
        total_entities = sum(len(s2_results_list) for s2_results_list in groups_to_process.values())
        total_cards = sum(
            len(s2_result.get("anki_cards", []))
            for s2_results_list in groups_to_process.values()
            for s2_result in s2_results_list
        )
        
        if progress_logger:
            progress_logger.info(
                f"[S5] Resume mode ({s5_mode}): {len(completed_group_ids)} groups already completed, "
                f"{total_groups} remaining (of {original_count} total)"
            )
        else:
            print(
                f"[S5] Resume mode ({s5_mode}): {len(completed_group_ids)} groups already completed, "
                f"{total_groups} remaining (of {original_count} total)",
                flush=True
            )
    
    # Initialize progress bars
    if progress_logger:
        mode_desc = {"all": "S1+S2", "s1_only": "S1 only", "s2_only": "S2 only"}.get(s5_mode, s5_mode)
        progress_logger.init_group(total_groups, desc=f"[S5] Processing groups ({mode_desc})")
        if s5_mode != "s1_only":
            progress_logger.init_entity(total_entities, desc="  [S5] Processing entities")
            progress_logger.init_card(total_cards, desc="    [S5] Processing cards")
    if workers_s5 > 1 and total_groups > 1:
        if progress_logger:
            progress_logger.debug(f"[S5] Processing {total_groups} groups with {workers_s5} parallel workers...")
        else:
            print(f"[S5] Processing {total_groups} groups with {workers_s5} parallel workers...", flush=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use ThreadPoolExecutor for parallel processing
        # Note: Entity/card-level progress tracking is not used in parallel mode
        # because multiple groups process simultaneously, making offset calculation complex.
        # Only group-level progress is tracked via update_group after each future completes.
        with ThreadPoolExecutor(max_workers=workers_s5) as executor:
            # Submit all tasks with explicit keyword arguments
            future_to_group = {
                executor.submit(
                    process_group,
                    str(group_id),
                    s2_results_list,
                    s4_manifest=s4_manifest,
                    s3_image_specs=s3_image_specs,
                    # progress_logger_ref, entity/card offsets not passed for parallel mode
                ): str(group_id)
                for group_id, s2_results_list in groups_to_process.items()
                if group_id  # Skip None group_ids
            }
            
            completed_groups = 0
            # Collect results as they complete
            for future in as_completed(future_to_group):
                group_id = future_to_group[future]
                completed_groups += 1
                try:
                    if progress_logger:
                        progress_logger.update_group(completed_groups, total_groups, group_id=group_id)
                    
                    validation_result = future.result()
                    if validation_result:
                        # Write output (thread-safe append)
                        with open(output_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps(validation_result, ensure_ascii=False) + "\n")
                        if progress_logger:
                            progress_logger.debug(f"[S5] Validation completed for group {group_id}")
                        else:
                            print(f"✓ S5 validation completed for group {group_id}", flush=True)
                    else:
                        if progress_logger:
                            progress_logger.warning(f"[S5] Validation skipped for group {group_id} (no result)")
                        else:
                            print(f"⚠ S5 validation skipped for group {group_id} (no result)", flush=True)
                except Exception as e:
                    if progress_logger:
                        progress_logger.error(f"[S5] Validation failed for group {group_id}: {e}")
                    else:
                        print(f"✗ S5 validation failed for group {group_id}: {e}", file=sys.stderr, flush=True)
    else:
        # Sequential processing (workers_s5 == 1 or only one group)
        if workers_s5 > 1:
            if progress_logger:
                progress_logger.debug(f"[S5] Only 1 group to process, using sequential mode (workers_s5={workers_s5} ignored)")
            else:
                print(f"[S5] Only 1 group to process, using sequential mode (workers_s5={workers_s5} ignored)", flush=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        group_idx = 0
        entity_idx_offset = 0
        card_idx_offset = 0
        
        for group_id, s2_results_list in groups_to_process.items():
            if not group_id:  # Skip None group_ids
                continue
            
            group_idx += 1
            if progress_logger:
                progress_logger.update_group(group_idx, total_groups, group_id=group_id)
                if s5_mode != "s1_only":
                    progress_logger.reset_entity()
            
            # Call process_group with all required parameters including manifests
            # Progress updates for entities/cards happen inside process_group
            validation_result = process_group(
                str(group_id),
                s2_results_list,
                s4_manifest=s4_manifest,
                s3_image_specs=s3_image_specs,
                progress_logger_ref=progress_logger if s5_mode != "s1_only" else None,
                entity_idx_offset=entity_idx_offset,
                card_idx_offset=card_idx_offset,
                total_entities_count=total_entities,
                total_cards_count=total_cards,
            )
            
            # Update offsets for the next group (after processing this group)
            if s5_mode != "s1_only":
                entity_idx_offset += len(s2_results_list)
                card_idx_offset += sum(len(s2_result.get("anki_cards", [])) for s2_result in s2_results_list)
            if validation_result:
                # Write output
                with open(output_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(validation_result, ensure_ascii=False) + "\n")
                if progress_logger:
                    progress_logger.debug(f"[S5] Validation completed for group {group_id}")
                else:
                    print(f"✓ S5 validation completed for group {group_id}", flush=True)
            else:
                if progress_logger:
                    progress_logger.warning(f"[S5] Validation skipped for group {group_id} (no result)")
                else:
                    print(f"⚠ S5 validation skipped for group {group_id} (no result)", flush=True)


# =========================
# CLI Entry Point
# =========================

def main():
    parser = argparse.ArgumentParser(description="MeducAI S5 Validation & Triage")
    parser.add_argument("--base_dir", type=str, required=True, help="Base directory of MeducAI project")
    parser.add_argument("--run_tag", type=str, required=True, help="Run tag identifier")
    parser.add_argument("--arm", type=str, required=True, help="Arm identifier (A, B, C, D, E, F)")
    parser.add_argument("--group_id", type=str, default=None, help="Optional group ID (if None, process all groups)")
    parser.add_argument(
        "--s1_path",
        type=str,
        default=None,
        help="Optional override path to S1 structure JSONL. "
             "If relative, treated as relative to --base_dir. "
             "Default: 2_Data/metadata/generated/<run_tag>/stage1_struct__arm<arm>.jsonl",
    )
    parser.add_argument(
        "--s2_path",
        type=str,
        default=None,
        help="Optional override path to S2 results JSONL. "
             "If relative, treated as relative to --base_dir. "
             "Default: resolved from 2_Data/metadata/generated/<run_tag>/ based on arm naming convention.",
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default=None,
        help="Optional override path to output JSONL. "
             "If omitted, defaults to s5_validation__arm<arm>.jsonl (or __postrepair.jsonl when --is_postrepair true). "
             "If relative, treated as relative to --base_dir.",
    )
    parser.add_argument(
        "--is_postrepair",
        type=str,
        default="auto",
        choices=["auto", "true", "false"],
        help="Whether this run is validating repaired outputs (postrepair). "
             "auto: infer from --output_path name containing '__postrepair' (default). "
             "true: default output becomes s5_validation__arm<arm>__postrepair.jsonl. "
             "false: baseline output s5_validation__arm<arm>.jsonl.",
    )
    parser.add_argument(
        "--prompt_registry",
        type=str,
        default=None,
        help="Optional path to prompt registry JSON (default: 3_Code/prompt/_registry.json). "
             "Use this to pin/trace the S5 judge prompt bundle (e.g., evalS5R* registries).",
    )
    
    # Read default workers from .env if available
    # Priority: WORKERS_S5 > WORKERS
    default_workers_s5 = 1
    try:
        default_workers_s5 = int(os.getenv("WORKERS_S5", os.getenv("WORKERS", "1")))
    except (ValueError, TypeError):
        default_workers_s5 = 1
    
    parser.add_argument("--workers_s5", type=int, default=None,
                        help=f"Parallel workers for S5 validation (default: {default_workers_s5} from .env WORKERS_S5/WORKERS, or 1). "
                             f"When > 1, groups are processed in parallel.")
    parser.add_argument(
        "--image-style",
        choices=["diagram", "realistic"],
        default=None,
        help="Image style hint: 'diagram' (default, S5R3) or 'realistic' (S5R2). "
             "If not specified, auto-detects from S3 image specs (exam_prompt_profile) or run_tag (REALISTIC). "
             "This is informational only - S5 will use S3 spec data as authoritative source."
    )
    parser.add_argument(
        "--s5_mode",
        choices=["all", "s1_only", "s2_only"],
        default="all",
        help="Execution mode: 'all' (default, S1+S2 together), "
             "'s1_only' (S1 table eval only, saves partial to s5_s1_partial__arm{arm}.jsonl), "
             "'s2_only' (S2 card eval only, requires partial from s1_only run). "
             "Use s1_only with lower workers for Pro model (RPM limited), "
             "then s2_only with higher workers for Flash model."
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume s1_only mode from existing partial file. "
             "Skips groups already present in the partial file instead of clearing it."
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    run_tag = args.run_tag
    arm = args.arm
    group_id = args.group_id

    # Resolve optional IO overrides
    s1_path_override = _resolve_cli_path(args.s1_path, base_dir)
    s2_path_override = _resolve_cli_path(args.s2_path, base_dir)
    output_path_override = _resolve_cli_path(args.output_path, base_dir)
    is_postrepair_opt: Optional[bool] = None
    if args.is_postrepair == "true":
        is_postrepair_opt = True
    elif args.is_postrepair == "false":
        is_postrepair_opt = False
    else:
        is_postrepair_opt = None
    
    # Determine workers_s5 (priority: CLI arg > .env > default)
    workers_s5 = args.workers_s5 if args.workers_s5 is not None else default_workers_s5
    
    # Get s5_mode (all, s1_only, s2_only)
    s5_mode = args.s5_mode
    
    # Initialize progress logger
    progress_logger = None
    if ProgressLogger is not None:
        try:
            progress_logger = ProgressLogger(
                run_tag=run_tag,
                script_name="s5",
                arm=arm,
                base_dir=base_dir,
            )
        except Exception as e:
            print(f"[WARN] Failed to initialize ProgressLogger: {e}", file=sys.stderr)
            progress_logger = None
    
    try:
        run_s5_validation(
            base_dir,
            run_tag,
            arm,
            group_id,
            workers_s5=workers_s5,
            progress_logger=progress_logger,
            prompt_registry=args.prompt_registry,
            s1_path_override=s1_path_override,
            s2_path_override=s2_path_override,
            output_path_override=output_path_override,
            is_postrepair=is_postrepair_opt,
            s5_mode=s5_mode,
            resume=args.resume,
        )
        if progress_logger:
            progress_logger.close()
    except Exception as e:
        if progress_logger:
            progress_logger.error(f"[S5] Error: {e}")
            progress_logger.close()
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


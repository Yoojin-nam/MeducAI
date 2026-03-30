from __future__ import annotations

"""
MeducAI Step01 — 01_generate_json.py (Refactor-ready, Prompt externalized)

- Prompts are loaded from 3_Code/prompt via 3_Code/src/tools/prompt_bundle.py
- RUN_TAG-centric output:
  2_Data/metadata/generated/<run_tag>/output_<provider>_<run_tag>__arm<ARM>.jsonl

Hard-fail rules (Pipeline-critical):
- curriculum_content.entities must be a list
- Step01 output is strictly TEXT-only (image/importance fields are forbidden)

P0 Freeze Invariant (Important):
- provider/model must be resolved ONLY from ARM_CONFIGS (+ MODEL_CONFIG fallback).
- Step01 MUST NOT read global model overrides from .env such as TEXT_MODEL_STAGE1/2.

S0 Allocation v2.1:
- In S0 mode, deterministic prefix allocation (3×4) is created/validated and used to generate
  multi-entity S2 targets with exact-N per entity.
- FINAL mode: Entity당 3장으로 고정 (cards_per_entity_default 폐기).
"""

import argparse
import faulthandler
import io
import json
import multiprocessing as mp
import os
import re
import sys
import time
import random
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

# Force unbuffered output for tmux/background execution
# This ensures real-time logging and reduces I/O overhead
# Note: Python -u flag or PYTHONUNBUFFERED=1 should be set in tmux command
# This is a fallback for when those aren't set
try:
    if not sys.stdout.isatty():
        # Running in non-interactive mode (tmux, background, etc.)
        # Force line buffering for better performance (Python 3.7+)
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(line_buffering=True)  # type: ignore
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(line_buffering=True)  # type: ignore
except Exception:
    pass  # Fallback: rely on PYTHONUNBUFFERED env var or -u flag
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TextIO, Tuple
from contextlib import ExitStack

import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

try:
    # Optional: quota/rate limiting (RPM/TPM/RPD)
    from tools.quota_limiter import QuotaLimiter, quota_from_env  # type: ignore
except Exception:
    QuotaLimiter = None  # type: ignore
    quota_from_env = None  # type: ignore

try:
    from tools.progress_logger import ProgressLogger  # type: ignore
except Exception:
    ProgressLogger = None  # type: ignore

_METRICS_LOCK = threading.Lock()
_LLM_METRICS_PATH: Optional[Path] = None
_S2_EXECUTION_LOG_PATH: Optional[Path] = None
_S2_EXECUTION_LOG_LOCK = threading.Lock()

def _append_metrics_jsonl(rec: Dict[str, Any]) -> None:
    """Best-effort metrics logger (thread-safe)."""
    global _LLM_METRICS_PATH
    p = _LLM_METRICS_PATH
    if p is None:
        return
    try:
        with _METRICS_LOCK:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def log_s2_execution(
    out_dir: Path,
    run_tag: str,
    arm: str,
    group_id: str,
    action: str,  # "start" | "complete" | "skipped" | "failed"
    entities_total: Optional[int] = None,
    entities_processed: Optional[int] = None,
    reason_skipped: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """
    Log S2 execution events (start/complete/skipped/failed) to logs/s2_execution_log.jsonl.
    Thread-safe logging for parallel group processing.
    """
    global _S2_EXECUTION_LOG_PATH, _S2_EXECUTION_LOG_LOCK
    
    if _S2_EXECUTION_LOG_PATH is None:
        _S2_EXECUTION_LOG_PATH = out_dir / "logs" / "s2_execution_log.jsonl"
    
    try:
        with _S2_EXECUTION_LOG_LOCK:
            log_dir = _S2_EXECUTION_LOG_PATH.parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            log_entry = {
                "timestamp": now_ts(),
                "run_tag": run_tag,
                "arm": arm,
                "group_id": group_id,
                "action": action,
            }
            
            if entities_total is not None:
                log_entry["entities_total"] = entities_total
            if entities_processed is not None:
                log_entry["entities_processed"] = entities_processed
            if reason_skipped is not None:
                log_entry["reason_skipped"] = reason_skipped
            if error is not None:
                log_entry["error"] = error
            
            with open(_S2_EXECUTION_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        # Best-effort: don't fail the process if logging fails
        print(f"[WARN] Failed to log S2 execution: {e}", file=sys.stderr, flush=True)


def _approx_tokens(text: str) -> int:
    """
    Very rough token estimator (provider-agnostic).
    Using ~4 chars/token for mixed EN/KR is a reasonable conservative heuristic.
    """
    s = (text or "")
    if not s:
        return 0
    return max(1, int(len(s) / 4))


def _quota_defaults_for_model(model_name: str) -> Tuple[Optional[int], Optional[int], Optional[int], str]:
    """
    Returns (default_rpm, default_tpm, default_rpd, env_prefix).
    env_prefix is used for overrides: QUOTA_{env_prefix}_RPM/TPM/RPD/SAFETY.
    """
    m = (model_name or "").strip().lower()
    if "gemini-3-pro" in m:
        return 25, 1_000_000, 250, "GEMINI_3_PRO"
    if "gemini-3-flash" in m:
        return 1000, 1_000_000, 10_000, "GEMINI_3_FLASH"
    # Fallback: no quota enforcement by default
    return None, None, None, "GENERIC"


class _LockedWriter:
    def __init__(self, fh: Any, lock: threading.Lock) -> None:
        self._fh = fh
        self._lock = lock

    def write(self, s: str) -> int:
        with self._lock:
            return self._fh.write(s)

    def flush(self) -> None:
        with self._lock:
            self._fh.flush()


# --- Ensure local imports (3_Code/src) work even without PYTHONPATH ---
import sys as _sys
_THIS_DIR = Path(__file__).resolve().parent
_sys.path.insert(0, str(_THIS_DIR))

from tools.prompt_bundle import load_prompt_bundle  # noqa: E402

# S0 Allocation (v2.0)
from tools.allocation.s0_allocation import (  # noqa: E402
    S0AllocationInputs,
    build_s0_allocation_artifact,
    require_valid_s0_allocation_artifact,
    s0_artifact_to_s2_targets,
)

# -------------------------
# Objective bullets formatter (stable)
# -------------------------
# We prefer to use the canonical helper in:
#   3_Code/src/tools/format_objective_bullets.py
# but we keep a safe fallback so Step01 can still run even if tools/ is not a package yet.
try:
    from tools.format_objective_bullets import objective_list_to_bullets as _objective_list_to_bullets  # type: ignore
    from tools.api_key_rotator import ApiKeyRotator  # type: ignore
except Exception:
    _objective_list_to_bullets = None
    ApiKeyRotator = None
    try:
        _TOOLS_DIR = (_THIS_DIR / "tools").resolve()
        if _TOOLS_DIR.exists():
            _sys.path.insert(0, str(_TOOLS_DIR))
            from format_objective_bullets import objective_list_to_bullets as _objective_list_to_bullets  # type: ignore
            try:
                from api_key_rotator import ApiKeyRotator  # type: ignore
            except Exception:
                ApiKeyRotator = None
    except Exception:
        _objective_list_to_bullets = None


def build_objective_bullets(objs: Any) -> str:
    """Build markdown bullets for S1 prompt from objective_list.

    Accepts:
      - List[str] (preferred, after CSV normalization)
      - JSON array string (legacy)

    Returns:
      - non-empty markdown bullet list string

    Notes:
      - Strips trailing difficulty markers like " (A)/(B)/(C)" via the canonical helper,
        when the helper is available.
      - Deterministic output.
    """
    if objs is None:
        raise ValueError("objective_list is None")

    # Canonical path: list[str] -> JSON string -> helper
    if isinstance(objs, list):
        arr = [str(x) for x in objs]
        obj_json = json.dumps(arr, ensure_ascii=False)
    else:
        obj_json = str(objs)

    if _objective_list_to_bullets is not None:
        try:
            out = _objective_list_to_bullets(obj_json, strip_difficulty=True)
            if isinstance(out, str) and out.strip():
                return out.strip()
        except Exception:
            pass  # fall back

    # Fallback (still deterministic)
    if isinstance(objs, list):
        lines = [f"- {str(x).strip()}" for x in objs if str(x).strip()]
        out2 = "\n".join(lines).strip()
        if out2:
            return out2

    s = str(objs).strip()
    if s:
        return s if s.lstrip().startswith("- ") else f"- {s}"

    raise ValueError("objective_list is empty after normalization")

# -------------------------
# Prompt rendering safety
# -------------------------
def safe_prompt_format(template: str, **kwargs) -> str:
    """Safely format prompt templates that may contain JSON examples with braces.

    Strategy:
    1) Escape ALL braces in the template so JSON examples remain literal.
    2) Un-escape only the placeholders we intend to substitute (keys in kwargs).
    3) Apply str.format().

    This prevents KeyError caused by JSON like { "id": ... } inside prompt templates.
    """
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


# -------------------------
# Option C (PR2): Repair-plan injection + output variants
# -------------------------
def _normalize_output_variant(output_variant: str) -> str:
    v = (output_variant or "baseline").strip().lower()
    if v not in {"baseline", "repaired"}:
        raise ValueError(f"Invalid output_variant='{output_variant}'. Must be 'baseline' or 'repaired'.")
    return v


def _variant_suffix(output_variant: str) -> str:
    return "" if _normalize_output_variant(output_variant) == "baseline" else "__repaired"


def _resolve_path_maybe_relative_to_base_dir(p: Optional[str], base_dir: Path) -> Optional[Path]:
    if not p:
        return None
    pp = Path(str(p)).expanduser()
    if pp.is_absolute():
        return pp
    return (base_dir / pp).resolve()


def load_repair_plan_jsonl(path: Path) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Load repair plan JSONL.

    Returns:
      - by_group_id: map[group_id] -> record
      - by_group_key: map[group_key] -> record (best-effort)
    """
    by_gid: Dict[str, Dict[str, Any]] = {}
    by_gkey: Dict[str, Dict[str, Any]] = {}

    if not path.exists():
        raise FileNotFoundError(f"repair_plan_path not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = (line or "").strip()
            if not s:
                continue
            try:
                rec = json.loads(s)
            except Exception:
                continue
            if not isinstance(rec, dict):
                continue

            gid = rec.get("group_id") or (rec.get("metadata") or {}).get("id")
            gkey = rec.get("group_key") or (rec.get("source_info") or {}).get("group_key")
            if gid is not None and str(gid).strip():
                by_gid[str(gid).strip()] = rec
            if gkey is not None and str(gkey).strip():
                by_gkey[str(gkey).strip()] = rec

    return by_gid, by_gkey


def _truncate_text(s: str, max_chars: int) -> str:
    if s is None:
        return ""
    s = str(s)
    if len(s) <= max_chars:
        return s
    # Keep head for context (more useful than tail for plans)
    return s[:max_chars] + "\n...[TRUNCATED]..."


def format_repair_instructions_for_prompt(
    repair_plan: Dict[str, Any],
    *,
    stage: str,
    group_id: str,
    group_key: str,
    entity_name: Optional[str] = None,
    max_chars: int = 6000,
) -> str:
    """
    Convert an arbitrary repair-plan record into a compact, prompt-safe instruction block.
    """
    if not repair_plan or not isinstance(repair_plan, dict):
        return ""

    # Prefer explicit instruction fields if present
    for k in ("repair_instructions", "instructions", "user_instructions", "plan_text"):
        v = repair_plan.get(k)
        if isinstance(v, str) and v.strip():
            body = v.strip()
            break
    else:
        # Fall back to a compact JSON preview (best-effort)
        # Remove very large fields if present (e.g., raw dumps) to keep the prompt small
        scrubbed = dict(repair_plan)
        for big_k in ("raw", "raw_response", "llm_raw", "full_context", "debug"):
            if big_k in scrubbed:
                scrubbed.pop(big_k, None)
        try:
            body = json.dumps(scrubbed, ensure_ascii=False, indent=2)
        except Exception:
            body = str(scrubbed)

    hdr = [
        "[REPAIR PLAN / REGENERATION INSTRUCTIONS]",
        f"- stage: {stage}",
        f"- group_id: {group_id}",
        f"- group_key: {group_key}" if group_key else "- group_key: (empty)",
    ]
    if entity_name:
        hdr.append(f"- entity_name: {entity_name}")

    out = "\n".join(hdr) + "\n\n" + body
    return _truncate_text(out, max_chars=max_chars).strip()


def maybe_append_repair_instructions(
    user_prompt: str,
    *,
    output_variant: str,
    repair_plan: Optional[Dict[str, Any]],
    stage: str,
    group_id: str,
    group_key: str,
    entity_name: Optional[str] = None,
) -> str:
    """
    Append repair instructions to user_prompt iff output_variant == 'repaired' and repair_plan exists.
    """
    if _normalize_output_variant(output_variant) != "repaired":
        return user_prompt
    if not repair_plan:
        return user_prompt
    block = format_repair_instructions_for_prompt(
        repair_plan,
        stage=stage,
        group_id=group_id,
        group_key=group_key,
        entity_name=entity_name,
    )
    if not block:
        return user_prompt
    return (user_prompt or "").rstrip() + "\n\n---\n" + block + "\n"


def _normalize_entity_key(s: str) -> str:
    """Normalize entity names for matching (strip + remove asterisks)."""
    return re.sub(r"\*+", "", str(s or "")).strip()


# -------------------------
# Paths & ENV
# -------------------------
def resolve_base_dir(base_dir: str) -> Path:
    return Path(base_dir).resolve()


def load_env(base_dir: Path) -> None:
    env_path = base_dir / ".env"
    if env_path.exists():
        try:
            # IMPORTANT: Do not override explicit process env (CLI prefix like VAR=1 python ...).
            # We want CLI env to take precedence; .env should only fill missing values.
            load_dotenv(dotenv_path=env_path, override=False)
        except PermissionError as e:
            # If .env file cannot be read due to permissions, warn but continue
            # Environment variables may already be set in the system
            print(f"⚠️  Warning: Cannot read .env file due to permissions: {e}")
            print(f"   Continuing with system environment variables only.")
            print(f"   If API calls fail, check that required environment variables are set.")


def now_ts() -> int:
    return int(time.time())


def is_blank(x: Any) -> bool:
    return x is None or (isinstance(x, str) and x.strip() == "")


def safe_int(x: Any, default: int) -> int:
    try:
        return int(x)
    except Exception:
        return default


def env_str(name: str, default: str) -> str:
    """Read string from environment variable with default."""
    return os.getenv(name, default)


def env_int(name: str, default: int) -> int:
    return safe_int(os.getenv(name, str(default)), default)


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


# =========================
# PREFLIGHT CHECKS (Fail-Fast)
# =========================
REQUIRED_PROMPT_KEYS = {
    "S1_SYSTEM",
    "S1_USER_GROUP",
    "S2_SYSTEM",
    "S2_USER_ENTITY",
}

REQUIRED_S1_PLACEHOLDERS_MIN = {
    "group_path",
    "objective_bullets",
}

REQUIRED_S2_PLACEHOLDERS_MIN_ANY = [
    {"master_table"},
    {"master_table_md"},
]

REQUIRED_S2_PLACEHOLDERS_MIN = {
    "entity_name",
    "cards_for_entity_exact",
}

ALLOWED_S1_PLACEHOLDERS = {
    "specialty",
    "anatomy",
    "modality_or_type",
    "category",
    "group_path",
    "group_key",
    "group_id",
    "objective_bullets",
    "split_index",
    "group_size",
}

ALLOWED_S2_PLACEHOLDERS = {
    "master_table",
    "entity_name",
    "visual_type",
    "cards_per_entity",          # 호환용
    "cards_for_entity_exact",    # canonical
    "card_type_quota_lines",
    "master_table_md",
    "entity_context",
    "group_id",
}

def _pf_assert(condition: bool, msg: str) -> None:
    if not condition:
        raise RuntimeError(f"[PREFLIGHT] {msg}")

_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

def _extract_placeholders(template: str) -> set[str]:
    return set(_PLACEHOLDER_RE.findall(template or ""))

def preflight_prompt_bundle(bundle: Dict[str, Any]) -> None:
    _pf_assert(isinstance(bundle, dict), "prompt_bundle is not a dict")
    _pf_assert("prompts" in bundle, "prompt_bundle missing key 'prompts'")
    prompts = bundle["prompts"]
    _pf_assert(isinstance(prompts, dict), "prompt_bundle['prompts'] is not a dict")

    missing = REQUIRED_PROMPT_KEYS - set(prompts.keys())
    _pf_assert(not missing, f"prompt_bundle missing required prompt keys: {sorted(missing)}")

    s1_user = prompts["S1_USER_GROUP"]
    s2_user = prompts["S2_USER_ENTITY"]
    _pf_assert(bool(isinstance(s1_user, str) and s1_user.strip()), "S1_USER_GROUP is empty or not a string")
    _pf_assert(bool(isinstance(s2_user, str) and s2_user.strip()), "S2_USER_ENTITY is empty or not a string")

    # 1) 템플릿에 실제로 등장하는 placeholder 추출
    s1_ph = _extract_placeholders(s1_user)
    s2_ph = _extract_placeholders(s2_user)

    # 2) 최소 필수 placeholder만 강제
    missing_s1_min = REQUIRED_S1_PLACEHOLDERS_MIN - s1_ph
    _pf_assert(
        not missing_s1_min,
        f"S1_USER_GROUP missing required MIN placeholders: {sorted(missing_s1_min)} "
        f"(found={sorted(s1_ph)})"
    )

    # S2: 기본 MIN(항상 필수) 체크
    missing_s2_min = REQUIRED_S2_PLACEHOLDERS_MIN - s2_ph
    _pf_assert(
        not missing_s2_min,
        f"S2_USER_ENTITY missing required MIN placeholders: {sorted(missing_s2_min)} (found={sorted(s2_ph)})"
    )

    # S2: master_table 계열은 alias 중 하나면 OK
    has_any_master = any(req_set.issubset(s2_ph) for req_set in REQUIRED_S2_PLACEHOLDERS_MIN_ANY)
    _pf_assert(
        has_any_master,
        f"S2_USER_ENTITY must contain one of {REQUIRED_S2_PLACEHOLDERS_MIN_ANY} "
        f"(found={sorted(s2_ph)})"
    )

    # 3) “미해결 placeholder 위험” 체크:
    #    템플릿에 있는 placeholder가 우리가 제공 가능한 키 집합(ALLOWED) 안에 있어야 함
    bad_s1 = sorted([p for p in s1_ph if p not in ALLOWED_S1_PLACEHOLDERS])
    _pf_assert(
        not bad_s1,
        f"S1_USER_GROUP contains unknown placeholders not supported by renderer: {bad_s1}. "
        f"Allowed={sorted(ALLOWED_S1_PLACEHOLDERS)}"
    )

    bad_s2 = sorted([p for p in s2_ph if p not in ALLOWED_S2_PLACEHOLDERS])
    _pf_assert(
        not bad_s2,
        f"S2_USER_ENTITY contains unknown placeholders not supported by renderer: {bad_s2}. "
        f"Allowed={sorted(ALLOWED_S2_PLACEHOLDERS)}"
    )

def preflight_s0_allocation(mode: str, spread_mode: str) -> None:
    if str(mode).upper() != "S0":
        return

    _pf_assert(
        spread_mode in {"hard", "soft"},
        f"S0_SPREAD_MODE must be 'hard' or 'soft' (got '{spread_mode}')",
    )

    # Allocation API availability
    required_funcs = [
        build_s0_allocation_artifact,
        require_valid_s0_allocation_artifact,
        s0_artifact_to_s2_targets,
    ]
    for fn in required_funcs:
        _pf_assert(callable(fn), f"S0 allocation dependency missing or not callable: {fn}")


def preflight_input_table(df: pd.DataFrame) -> None:
    _pf_assert(isinstance(df, pd.DataFrame), "Input table is not a DataFrame")
    required_cols = {"specialty", "anatomy", "modality_or_type", "objective_list"}
    missing = required_cols - set(df.columns)
    _pf_assert(
        not missing,
        f"Input table missing required columns: {sorted(missing)}",
    )


def preflight_output_dir(out_dir: Path) -> None:
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        test = out_dir / ".write_test"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
    except Exception as e:
        raise RuntimeError(f"[PREFLIGHT] Output directory not writable: {out_dir}") from e


def preflight_api_key(provider: str, model_config: Dict[str, Any], base_dir: Optional[Path] = None, rotator: Optional[Any] = None) -> None:
    """
    Preflight check for API key availability.
    For Gemini provider, uses rotator if available, otherwise checks both single GOOGLE_API_KEY and numbered keys (GOOGLE_API_KEY_1~N) for rotator support.
    If base_dir is provided, will also try to load .env file directly if keys are not found in environment.
    
    Args:
        provider: Provider name (e.g., "gemini")
        model_config: Model configuration dict
        base_dir: Base directory for .env file lookup
        rotator: Optional ApiKeyRotator instance (if already initialized)
    """
    api_key_env = model_config[provider]["api_key_env"]
    
    if provider == "gemini" and api_key_env == "GOOGLE_API_KEY":
        # If rotator is available and initialized, use it
        if rotator is not None:
            try:
                api_key = rotator.get_current_key()
                if api_key and api_key.strip():
                    return  # Rotator has a valid key
            except Exception:
                pass  # Fall through to manual check
        
        # Manual check: Try to initialize rotator if ApiKeyRotator is available
        if ApiKeyRotator is not None and base_dir is not None:
            try:
                temp_rotator = ApiKeyRotator(base_dir=base_dir, key_prefix="GOOGLE_API_KEY")
                if temp_rotator.keys and len(temp_rotator.keys) > 0:
                    return  # Rotator found keys
            except Exception:
                pass  # Fall through to manual check
        
        # Fallback: Check for numbered keys (no upper limit, auto-detect)
        has_numbered_keys = False
        # Check numbered keys (start from 1, check up to a reasonable limit, but ApiKeyRotator auto-detects all)
        for i in range(1, 100):  # Check up to 100 keys (ApiKeyRotator auto-detects all, but we need to check manually here)
            if os.getenv(f"GOOGLE_API_KEY_{i}", "").strip():
                has_numbered_keys = True
                break
        
        # Fallback to single key
        has_single_key = bool(os.getenv(api_key_env, "").strip())
        
        # If no keys found and base_dir provided, try loading .env directly
        if not has_numbered_keys and not has_single_key and base_dir is not None:
            env_path = base_dir / ".env"
            if env_path.exists():
                try:
                    # Try loading .env file directly
                    from dotenv import dotenv_values
                    env_vars = dotenv_values(dotenv_path=env_path)
                    # Check numbered keys (no upper limit)
                    for i in range(1, 100):
                        key_val = (env_vars.get(f"GOOGLE_API_KEY_{i}") or "").strip()
                        if key_val:
                            has_numbered_keys = True
                            # Also set in environment for later use
                            os.environ[f"GOOGLE_API_KEY_{i}"] = key_val
                            break
                    # Check single key
                    key_val = (env_vars.get(api_key_env) or "").strip()
                    if key_val:
                        has_single_key = True
                        os.environ[api_key_env] = key_val
                except Exception as e:
                    print(f"⚠️  Warning: Could not read .env file directly: {e}")
        
        _pf_assert(
            has_numbered_keys or has_single_key,
            f"Missing API key: env {api_key_env} or GOOGLE_API_KEY_1~N is not set (checked environment and .env file)",
        )
    else:
        # For other providers, check single key only
        has_key = bool(os.getenv(api_key_env, "").strip())
        
        # If no key found and base_dir provided, try loading .env directly
        if not has_key and base_dir is not None:
            env_path = base_dir / ".env"
            if env_path.exists():
                try:
                    from dotenv import dotenv_values
                    env_vars = dotenv_values(dotenv_path=env_path)
                    key_val = (env_vars.get(api_key_env) or "").strip()
                    if key_val:
                        has_key = True
                        os.environ[api_key_env] = key_val
                except Exception as e:
                    print(f"⚠️  Warning: Could not read .env file directly: {e}")
        
        _pf_assert(
            has_key,
            f"Missing API key: env {api_key_env} is not set (checked environment and .env file)",
        )


# -------------------------
# Contract & Validation (Minimum + Hard-fail)
# -------------------------
def normalize_tags(tags: Any) -> str:
    if tags is None:
        return ""
    if isinstance(tags, str):
        return tags.strip()
    if isinstance(tags, list):
        return " ".join([str(t).strip() for t in tags if str(t).strip()])
    return str(tags).strip()


def validate_and_fill_entity(entity: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize an entity object for Step01 output (text-only).

    Note: Image-related fields are intentionally excluded in Step01.
    However, card_role, image_hint, image_hint_v2, options, and correct_index are preserved for S2 output.
    """
    e_in = dict(entity or {})
    e_out: Dict[str, Any] = {}

    if "group_id" in e_in and e_in["group_id"] is not None:
        e_out["group_id"] = str(e_in["group_id"]).strip()

    # Optional stable entity identifier for traceability
    if "entity_id" in e_in and e_in.get("entity_id") is not None:
        _eid = str(e_in.get("entity_id") or "").strip()
        if _eid:
            e_out["entity_id"] = _eid

    if "cards_for_entity_exact" in e_in:
        e_out["cards_for_entity_exact"] = safe_int(e_in.get("cards_for_entity_exact"), 0)

    e_out["entity_name"] = str(e_in.get("entity_name") or "").strip() or "Unnamed entity"

    cards = e_in.get("anki_cards") or []
    if not isinstance(cards, list):
        cards = []
    norm_cards: List[Dict[str, Any]] = []
    for c in cards:
        if not isinstance(c, dict):
            continue
        
        # Extract card_role (S2 v3.1)
        card_role = str(c.get("card_role") or "").strip()
        
        # Extract image_hint (S2 v3.1)
        image_hint = c.get("image_hint")
        # Extract image_hint_v2 (structured constraints; optional)
        image_hint_v2 = c.get("image_hint_v2")
        
        # Extract MCQ fields (S2 v3.1) - options and correct_index
        options = c.get("options")
        correct_index = c.get("correct_index")
        
        # Normalize tags
        tags_raw = c.get("tags")
        if isinstance(tags_raw, list):
            tags = [str(t).strip() for t in tags_raw if t]
        elif isinstance(tags_raw, str):
            tags = [t.strip() for t in tags_raw.split() if t.strip()]
        else:
            tags = []
        
        cc = {
            "card_type": str(c.get("card_type") or "Basic").strip(),
            "front": str(c.get("front") or "").strip(),
            "back": str(c.get("back") or "").strip(),
            "tags": tags,
        }
        
        # Preserve card_role if present (S2 v3.1)
        if card_role:
            cc["card_role"] = card_role
        
        # Preserve image_hint if present (S2 v3.1)
        if image_hint is not None:
            cc["image_hint"] = image_hint

        # Preserve image_hint_v2 if present (structured constraints for downstream S3/S4)
        if isinstance(image_hint_v2, dict) and image_hint_v2:
            cc["image_hint_v2"] = image_hint_v2
        
        # Preserve MCQ fields if present (S2 v3.2) - CRITICAL for Q2 MCQ cards
        if options is not None:
            # Ensure options is a list
            if isinstance(options, list):
                cc["options"] = options
            else:
                # If not a list, try to convert or skip
                pass
        
        if correct_index is not None:
            cc["correct_index"] = correct_index
        
        if not (cc["front"] and cc["back"]):
            continue
        norm_cards.append(cc)

    e_out["anki_cards"] = norm_cards
    return e_out


def hard_fail_record(record: Dict[str, Any], *, mode: str | None = None) -> None:
    """Hard-fail rules (Step01, text-only)."""
    cc = record.get("curriculum_content") or {}
    entities = cc.get("entities")
    if not isinstance(entities, list):
        raise ValueError("Hard-fail: curriculum_content.entities is not a list")

    # ---- Runtime logging hard requirements (Step01) ----
    rt = (record.get("metadata") or {}).get("runtime")
    if not isinstance(rt, dict):
        raise ValueError("Hard-fail: metadata.runtime missing or not an object")

    required_rt_keys = [
        "run_tag", "mode", "arm", "provider", "model_stage1", "model_stage2",
        "thinking_enabled", "thinking_budget",
        "rag_enabled", "rag_mode", "rag_queries_count", "rag_sources_count",
        "latency_sec_stage1", "latency_sec_stage2",
        "input_tokens_stage1", "output_tokens_stage1", "input_tokens_stage2", "output_tokens_stage2",
    ]
    missing_rt = [k for k in required_rt_keys if k not in rt]
    if missing_rt:
        raise ValueError(f"Hard-fail: metadata.runtime missing keys: {missing_rt}")


    forbidden_keys = {"row_image_prompt_en", "row_image_necessity", "importance_score"}
    for i, e in enumerate(entities):
        if not isinstance(e, dict):
            continue
        present = sorted([k for k in e.keys() if (k in forbidden_keys) or k.startswith("row_image_")])
        if present:
            raise ValueError(
                f"Hard-fail: forbidden entity keys present at entities[{i}]: {present}. "
                "Step01 output must be text-only; image/importance fields are handled in a separate pipeline."
            )


def validate_and_fill_record(
    record: Dict[str, Any],
    *,
    run_tag: str,
    mode: str,
    provider: str,
    arm: str,
) -> Dict[str, Any]:
    r = dict(record or {})

    md = dict(r.get("metadata") or {})
    src = dict(r.get("source_info") or md.get("source_info") or {})

    md.setdefault("provider", provider)
    md.setdefault("arm", arm)
    md.setdefault("run_tag", run_tag)
    md.setdefault("mode", mode)
    md.setdefault("timestamp", now_ts())

    r["metadata"] = md
    r["source_info"] = src

    cc = dict(r.get("curriculum_content") or {})
    cc.setdefault("visual_type", "General")
    cc.setdefault("master_table", "")
    ents = cc.get("entities")
    if not isinstance(ents, list):
        ents = []
    cc["entities"] = [validate_and_fill_entity(e) for e in ents if isinstance(e, dict)]
    r["curriculum_content"] = cc

    hard_fail_record(r, mode=mode)
    return r


# -------------------------
# Input loading & group row normalization
# -------------------------
def default_input_path(base_dir: Path) -> Path:
    return base_dir / "2_Data" / "metadata" / "groups_canonical.csv"


def read_input_table(path: Path) -> pd.DataFrame:
    if str(path).lower().endswith(".xlsx"):
        return pd.read_excel(path)
    return pd.read_csv(path)


def coalesce(row: Dict[str, Any], keys: List[str], default: Any = "") -> Any:
    for k in keys:
        if k in row and not is_blank(row.get(k)):
            return row.get(k)
    return default


def normalize_objective_list(v: Any) -> List[str]:
    """Normalize objective_list into List[str]."""
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]

    s = str(v).strip()
    if not s:
        return []

    if s.startswith("[") and s.endswith("]"):
        try:
            x = json.loads(s)
            if isinstance(x, list):
                return [str(y).strip() for y in x if str(y).strip()]
        except Exception:
            pass

    parts = re.split(r"[\n;\|]+", s)
    parts = [p.strip() for p in parts if p.strip()]
    return parts


CAP_CHARS_TOTAL_RISK = 2200
S2_RESULTS_SCHEMA_VERSION = "S2_RESULTS_v3.2"


def apply_cap_chars_total(
    objectives: List[str],
    cap_chars_total: int = CAP_CHARS_TOTAL_RISK,
) -> Tuple[List[str], List[int], int]:
    """Deterministic greedy truncation by total character budget."""
    if not objectives:
        return [], [], 0

    selected: List[str] = []
    indices: List[int] = []
    total = 0

    for i, obj in enumerate(objectives):
        obj_s = str(obj).strip()
        if not obj_s:
            continue
        n = len(obj_s)
        if total + n > cap_chars_total:
            break
        selected.append(obj_s)
        indices.append(i)
        total += n

    return selected, indices, total


def normalize_row(raw: Dict[str, Any]) -> Dict[str, Any]:
    r = dict(raw or {})

    specialty = coalesce(r, ["specialty", "Specialty"], "Radiology")
    anatomy = coalesce(r, ["anatomy", "Anatomy"], "General")
    modality = coalesce(r, ["modality_or_type", "Modality/Type", "Modality", "Type"], "")
    category = coalesce(r, ["category", "Category"], "")
    group_key = coalesce(r, ["group_key", "GroupKey", "group"], "")

    obj_list = coalesce(r, ["objective_list", "Objectives", "objective", "LearningObjectives"], [])
    obj_list = normalize_objective_list(obj_list)

    split_index = safe_int(coalesce(r, ["split_index", "SplitIndex"], 0), 0)
    
    # Extract group_id from CSV (canonical SSOT)
    group_id = coalesce(r, ["group_id", "GroupID", "group_id"], "")

    return {
        "specialty": str(specialty),
        "anatomy": str(anatomy),
        "modality_or_type": str(modality),
        "category": str(category),
        "group_key": str(group_key),
        "group_id": str(group_id) if group_id else "",  # Preserve group_id from CSV
        "objective_list": obj_list,
        "split_index": split_index,
        "_raw": r,
    }


def make_stable_group_id(specialty: str, anatomy: str, modality: str, category: str, split_index: int) -> str:
    import hashlib as _hashlib
    key = f"{specialty}|{anatomy}|{modality}|{category}|{split_index}"
    return _hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


# -------------------------
# Provider configs
# -------------------------
MODEL_CONFIG = {
    "gemini": {
        "model_name": "gemini-3-flash-preview",  # Updated to Gemini 3 Flash Preview (A-D arms use this)
        "api_key_env": "GOOGLE_API_KEY",
        "supports": ["chat"],
    },
    "gpt": {
        "model_name": "gpt-5.2-pro-2025-12-11",
        "api_key_env": "OPENAI_API_KEY",
        "supports": ["chat", "responses"],
    },
    "deepseek": {
        "model_name": "deepseek-reasoner",
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com",
        "supports": ["chat"],
    },
    "claude": {
        "model_name": "claude-3-5-sonnet-20241022",
        "api_key_env": "ANTHROPIC_API_KEY",
        "supports": ["chat"],
    },
}

ARM_CONFIGS = {
    "A": {"label": "Baseline",   "provider": "gemini", "api_style": "chat",      "thinking": False, "rag": False,
          "model_stage1": "gemini-3-flash-preview", "model_stage2": "gemini-3-flash-preview",
          "thinking_level": "minimal"},
    "B": {"label": "RAG_Only",   "provider": "gemini", "api_style": "chat",      "thinking": False, "rag": True,
          "model_stage1": "gemini-3-flash-preview", "model_stage2": "gemini-3-flash-preview",
          "thinking_level": "minimal"},
    "C": {"label": "Thinking",   "provider": "gemini", "api_style": "chat",      "thinking": True,  "rag": False,
          "model_stage1": "gemini-3-flash-preview", "model_stage2": "gemini-3-flash-preview",
          "thinking_level": "high"},
    "D": {"label": "Synergy",    "provider": "gemini", "api_style": "chat",      "thinking": True,  "rag": True,
          "model_stage1": "gemini-3-flash-preview", "model_stage2": "gemini-3-flash-preview",
          "thinking_level": "high"},
    "E": {"label": "High_End",   "provider": "gemini", "api_style": "chat",      "thinking": True,  "rag": True,  # TEST: RAG ON for 5-group smoke test
          "model_stage1": "gemini-3-pro-preview",   "model_stage2": "gemini-3-pro-preview",
          "thinking_budget": 2048},
    "F": {"label": "Benchmark",  "provider": "gpt",    "api_style": "responses", "thinking": True, "rag": True,
          # Arm E와 동일하게 Thinking + RAG 모두 ON: gpt-5.2(non-pro) + reasoning.effort="medium" + temperature=0
          "model_stage1": "gpt-5.2-2025-12-11", "model_stage2": "gpt-5.2-2025-12-11",
          "temp_stage1": 0.2, "temp_stage2": 0.2},
    # G: Production pipeline (USER DECISION)
    # - S1: gemini-3-pro-preview (thinking=on, RAG=off)
    # - S2: gemini-3-flash (thinking=on, RAG=off)
    # NOTE: This arm intentionally mixes S1 and S2 models to match the decided execution plan.
    "G": {"label": "S1_PRO__S2_FLASH", "provider": "gemini", "api_style": "chat", "thinking": True, "rag": False,
          "model_stage1": "gemini-3-pro-preview", "model_stage2": "gemini-3-flash-preview",
          "thinking_level": "high", "thinking_budget": 2048},
}


def validate_arm_cfg(arm_cfg: Dict[str, Any]) -> None:
    api_style = (arm_cfg.get("api_style") or "").strip().lower()
    provider = (arm_cfg.get("provider") or "").strip().lower()

    if not provider:
        raise RuntimeError("arm_cfg must define provider explicitly")
    if provider not in MODEL_CONFIG:
        raise RuntimeError(f"Unsupported provider in arm_cfg: {provider}")

    if not api_style:
        raise RuntimeError("arm_cfg must define api_style explicitly (no implicit routing)")
    if api_style not in {"chat", "responses"}:
        raise RuntimeError(f"Invalid api_style='{api_style}'. Must be one of ['chat','responses'].")

    supports = MODEL_CONFIG[provider].get("supports") or []
    if api_style not in supports:
        raise RuntimeError(
            f"Provider '{provider}' does not support api_style '{api_style}'. Supported={supports}"
        )


@dataclass
class ProviderClients:
    gemini: Any = None
    openai: Any = None
    deepseek: Any = None
    claude: Any = None


def _get_gemini_api_key_for_subprocess() -> str:
    """
    Best-effort way to obtain the *current* Gemini API key for subprocess isolation.
    - If ApiKeyRotator is active, use its current key.
    - Else fall back to GOOGLE_API_KEY in the environment.
    """
    global _global_rotator
    if _global_rotator is not None:
        try:
            k = str(_global_rotator.get_current_key() or "").strip()
            if k:
                return k
        except Exception:
            pass
    return str(os.getenv("GOOGLE_API_KEY", "") or "").strip()


def _gemini_generate_content_worker(payload: Dict[str, Any], out_q: Any, output_file: Optional[str] = None) -> None:
    """
    Subprocess worker for Gemini generate_content().
    Returns only serializable primitives via queue to avoid pickling SDK objects.
    
    Args:
        payload: Request parameters for Gemini API
        out_q: SimpleQueue for IPC (kept for backward compatibility)
        output_file: Optional file path to write result JSON (primary IPC method for macOS reliability)
    """
    result = None
    try:
        import sys
        import base64
        from google import genai  # type: ignore
        from google.genai import types as genai_types  # type: ignore

        api_key = str(payload.get("api_key") or "").strip()
        if not api_key:
            raise RuntimeError("Missing api_key for Gemini subprocess worker")

        timeout_ms = payload.get("timeout_ms")
        http_options = None
        if isinstance(timeout_ms, int) and timeout_ms > 0:
            # SDK interprets timeout as milliseconds.
            http_options = genai_types.HttpOptions(timeout=timeout_ms)

        client = genai.Client(api_key=api_key, http_options=http_options)

        model_name = str(payload.get("model_name") or "")
        user_prompt = str(payload.get("user_prompt") or "")
        system_prompt = str(payload.get("system_prompt") or "")
        temperature = float(payload.get("temperature") or 0.0)
        max_output_tokens = int(payload.get("max_output_tokens") or 0)
        rag_enabled = bool(payload.get("rag_enabled"))
        thinking_enabled = bool(payload.get("thinking_enabled"))
        thinking_level = payload.get("thinking_level")
        image_data_base64 = payload.get("image_data_base64")  # Optional: base64-encoded image
        image_mime_types = payload.get("image_mime_types")  # Optional: list of MIME types

        config_kwargs: Dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt

        # [CRITICAL] Search tool cannot be used with response_mime_type='application/json'
        if not rag_enabled:
            config_kwargs["response_mime_type"] = "application/json"

        # Thinking config
        if model_name.startswith("gemini-3"):
            if thinking_level:
                level_val = str(thinking_level).strip().lower()
                config_kwargs["thinking_config"] = genai_types.ThinkingConfig(thinking_level=level_val)  # type: ignore
            elif thinking_enabled:
                config_kwargs["thinking_config"] = genai_types.ThinkingConfig(thinking_level="high")  # type: ignore
            else:
                config_kwargs["thinking_config"] = genai_types.ThinkingConfig(thinking_level="minimal")  # type: ignore

        # RAG/search
        if rag_enabled:
            grounding_tool = genai_types.Tool(google_search=genai_types.GoogleSearch())
            config_kwargs["tools"] = [grounding_tool]

        generation_config = genai_types.GenerateContentConfig(**config_kwargs)

        # Build contents for multimodal input (text + images)
        if image_data_base64:
            # Decode base64 image and create Part
            try:
                # Handle both single image (string) and multiple images (list)
                if isinstance(image_data_base64, list):
                    # Multiple images: decode each
                    image_bytes_list = [base64.b64decode(img_b64) for img_b64 in image_data_base64]
                    mime_types = image_mime_types if isinstance(image_mime_types, list) and len(image_mime_types) == len(image_bytes_list) else ["image/jpeg"] * len(image_bytes_list)
                    # For now, use first image (can be extended to support multiple images)
                    image_bytes = image_bytes_list[0]
                    mime_type = mime_types[0] if mime_types else "image/jpeg"
                else:
                    # Single image: decode string
                    image_bytes = base64.b64decode(image_data_base64)
                    # Determine MIME type (default to JPEG, could be enhanced)
                    mime_type = image_mime_types[0] if isinstance(image_mime_types, list) and len(image_mime_types) > 0 else "image/jpeg"
                # Try keyword arguments first
                try:
                    image_part = genai_types.Part.from_bytes(  # type: ignore[call-arg]
                        data=image_bytes,
                        mime_type=mime_type
                    )
                except (TypeError, AttributeError):
                    # Fallback: create Part object directly with inline_data
                    image_part = genai_types.Part(
                        inline_data=genai_types.Blob(
                            data=image_bytes,
                            mime_type=mime_type
                        )
                    )
                # Create contents list with text and image
                contents = [user_prompt, image_part]
            except Exception as img_err:
                # Fallback to text-only if image decoding fails
                print(f"[Worker] Warning: Failed to decode image, using text-only: {img_err}", file=sys.stderr, flush=True)
                contents = user_prompt
        else:
            # Text-only: use string directly
            contents = user_prompt

        r = client.models.generate_content(model=model_name, contents=contents, config=generation_config)

        # finish_reason (best-effort)
        finish_reason = None
        try:
            cands = getattr(r, "candidates", None) or []
            if cands:
                finish_reason = getattr(cands[0], "finish_reason", None)
        except Exception:
            finish_reason = None

        # usage (best-effort)
        usage: Dict[str, Any] = {}
        try:
            um = getattr(r, "usage_metadata", None)
            if um is not None:
                usage = {
                    "prompt_token_count": getattr(um, "prompt_token_count", None),
                    "candidates_token_count": getattr(um, "candidates_token_count", None),
                    "total_token_count": getattr(um, "total_token_count", None),
                }
        except Exception:
            usage = {}

        # raw text extraction (matches parent logic)
        raw_text = (getattr(r, "text", None) or "").strip()
        if not raw_text:
            try:
                cands = getattr(r, "candidates", None) or []
                if cands:
                    content = getattr(cands[0], "content", None)
                    parts = getattr(content, "parts", None) or []
                    raw_text = "".join([(getattr(p, "text", "") or "") for p in parts]).strip()
            except Exception:
                raw_text = ""

        if not raw_text:
            raise ValueError("Empty response text from provider=gemini (google-genai)")

        # RAG metadata (best-effort)
        rag_queries_count = 0
        rag_sources_count = 0
        if rag_enabled:
            try:
                cands = getattr(r, "candidates", None) or []
                if cands and len(cands) > 0:
                    gm = getattr(cands[0], "grounding_metadata", None)
                    if gm is not None:
                        queries = getattr(gm, "web_search_queries", None) or []
                        chunks = getattr(gm, "grounding_chunks", None) or []
                        rag_queries_count = len(queries) if isinstance(queries, list) else 0
                        rag_sources_count = len(chunks) if isinstance(chunks, list) else 0
            except Exception:
                pass

        result = {
            "ok": True,
            "raw_text": raw_text,
            "finish_reason": str(finish_reason) if finish_reason is not None else None,
            "usage": usage,
            "rag_queries_count": rag_queries_count,
            "rag_sources_count": rag_sources_count,
        }
        
        # Write to file first (primary IPC method for macOS reliability)
        if output_file:
            try:
                import json
                import os
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False)
                    # Ensure file is flushed to disk (must be inside with block)
                    f.flush()
                    if hasattr(os, 'fsync'):
                        os.fsync(f.fileno())
            except Exception as file_err:
                # Log file write error but continue to queue (fallback)
                import sys
                print(f"[Worker] Failed to write result to file {output_file}: {file_err}", file=sys.stderr, flush=True)
        
        # Also put to queue (fallback for backward compatibility)
        out_q.put(result)
        # Force flush on macOS (SimpleQueue may need explicit sync)
        import sys
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception as e:
        error_result = {
            "ok": False,
            "error_class": type(e).__name__,
            "error_message": str(e),
        }
        
        # Write error to file first
        if output_file:
            try:
                import json
                import os
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(error_result, f, ensure_ascii=False)
                    # Ensure file is flushed to disk (must be inside with block)
                    f.flush()
                    if hasattr(os, 'fsync'):
                        os.fsync(f.fileno())
            except Exception as file_err:
                import sys
                print(f"[Worker] Failed to write error to file {output_file}: {file_err}", file=sys.stderr, flush=True)
        
        # Also put to queue (fallback)
        out_q.put(error_result)
        # Force flush on error too
        import sys
        sys.stdout.flush()
        sys.stderr.flush()


def _run_gemini_generate_with_hard_timeout(
    *,
    payload: Dict[str, Any],
    watchdog_s: float,
    heartbeat_s: float,
    stage: int,
    log_ctx: str,
) -> Dict[str, Any]:
    """
    Run Gemini SDK call in a subprocess so timeouts cannot hang the parent thread.
    Implements heartbeat logging in the parent while waiting.
    Uses file-based IPC for reliability on macOS spawn context (with queue fallback).
    """
    import tempfile
    
    # Determine IPC method from environment (default: file for reliability)
    ipc_method = str(os.getenv("LLM_GEMINI_IPC_METHOD", "file")).strip().lower()
    use_file_ipc = (ipc_method == "file")
    
    ctx = mp.get_context("spawn")
    # SimpleQueue kept as fallback for backward compatibility
    q = ctx.SimpleQueue()
    
    # Create temporary file for file-based IPC (primary method for macOS reliability)
    output_file = None
    if use_file_ipc:
        try:
            fd, output_file = tempfile.mkstemp(suffix=".json", prefix="gemini_ipc_", text=True)
            os.close(fd)  # Close file descriptor, worker will write to the path
        except Exception as e:
            # If temp file creation fails, fall back to queue-only
            print(f"[IPC] Failed to create temp file, falling back to queue: {e}", flush=True)
            output_file = None
    
    p = ctx.Process(target=_gemini_generate_content_worker, args=(payload, q, output_file), daemon=False)

    start_wait = time.perf_counter()
    p.start()
    try:
        while True:
            elapsed = time.perf_counter() - start_wait
            if watchdog_s and elapsed >= watchdog_s:
                try:
                    p.terminate()
                except Exception:
                    pass
                try:
                    p.join(timeout=5.0)
                except Exception:
                    pass
                if p.is_alive():
                    try:
                        p.kill()
                    except Exception:
                        pass
                    try:
                        p.join(timeout=2.0)
                    except Exception:
                        pass
                ctx_s = (" " + log_ctx.strip()) if log_ctx and log_ctx.strip() else ""
                raise TimeoutError(
                    f"[Stage{stage}] GeminiHardTimeout: elapsed={elapsed:.1f}s watchdog_s={watchdog_s}{ctx_s}"
                )

            # Poll completion at heartbeat cadence
            try:
                p.join(timeout=float(max(0.1, heartbeat_s or 0.5)))
            except Exception:
                pass

            if not p.is_alive():
                break

            # Heartbeat (suppressed for cleaner terminal output)
            # LLM waiting messages are logged to file via metrics if needed

        # Process ended: retrieve result
        # Try file-based IPC first (primary method for macOS reliability), then fallback to queue
        result = None
        
        if use_file_ipc and output_file:
            # Primary path: Read from file (more reliable on macOS spawn context)
            try:
                import json
                time.sleep(0.2)  # Brief grace period for file flush
                
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    if file_size > 0:
                        with open(output_file, "r", encoding="utf-8") as f:
                            result = json.load(f)
                        # IPC logging suppressed for cleaner terminal output
                        # Logs are still available in metrics file if needed
                    else:
                        # File exists but is empty
                        # IPC logging suppressed for cleaner terminal output
                        pass
                else:
                    # File doesn't exist
                    # IPC logging suppressed for cleaner terminal output
                    pass
            except Exception as e:
                # Log file read error, will try queue fallback
                # IPC logging suppressed for cleaner terminal output
                pass
        
        # Fallback: Try queue if file IPC failed or wasn't used
        if result is None:
            try:
                time.sleep(0.3)  # Grace period for queue flush (macOS spawn context)
                result = q.get(timeout=5.0)  # type: ignore[attr-defined]
                # IPC logging suppressed for cleaner terminal output
            except Exception as e:
                # Both file and queue failed
                file_info = ""
                if output_file:
                    try:
                        if os.path.exists(output_file):
                            file_info = f", file_exists=True, file_size={os.path.getsize(output_file)}B"
                        else:
                            file_info = ", file_exists=False"
                    except Exception:
                        file_info = ", file_stat_error=True"
                
                result = {
                    "ok": False,
                    "error_class": "EmptyIPCResult",
                    "error_message": (
                        f"Gemini subprocess returned no result via file or queue "
                        f"(exitcode={p.exitcode}, alive={p.is_alive()}, "
                        f"ipc_method={ipc_method}, queue_error={type(e).__name__}{file_info})"
                    ),
                }
        
        return result
    finally:
        # Cleanup
        try:
            if p.is_alive():
                p.terminate()
        except Exception:
            pass
        
        # Clean up temporary file
        if output_file:
            try:
                if os.path.exists(output_file):
                    os.remove(output_file)
            except Exception:
                pass  # Best effort cleanup


def build_clients(provider: str, api_key: str, *, timeout_s: Optional[int] = None) -> ProviderClients:
    c = ProviderClients()
    if provider == "gemini":
        # Google GenAI SDK (google-genai - new version)
        from google import genai  # type: ignore
        from google.genai import types as genai_types  # type: ignore
        # NOTE: google-genai HttpOptions.timeout is interpreted as a client-side deadline in MILLISECONDS.
        # If you pass seconds directly (e.g., 600), the SDK treats it as 600ms (~1s) and may fail with:
        #   "Manually set deadline 1s is too short. Minimum allowed deadline is 10s."
        # We therefore convert seconds -> milliseconds and clamp to a minimum of 10s.
        http_options = None
        if timeout_s is not None:
            try:
                timeout_sec = int(timeout_s)
            except Exception:
                timeout_sec = 0
            if timeout_sec > 0:
                timeout_sec = max(timeout_sec, 10)
                http_options = genai_types.HttpOptions(timeout=timeout_sec * 1000)
                # Client creation logging suppressed for cleaner terminal output
                pass
        else:
            # Client warning suppressed for cleaner terminal output (only log critical errors)
            pass
        client = genai.Client(api_key=api_key, http_options=http_options)
        c.gemini = client
    elif provider == "gpt":
        from openai import OpenAI  # type: ignore
        c.openai = OpenAI(api_key=api_key)
    elif provider == "deepseek":
        from openai import OpenAI  # type: ignore
        c.deepseek = OpenAI(api_key=api_key, base_url=MODEL_CONFIG["deepseek"]["base_url"])
    elif provider == "claude":
        import anthropic  # type: ignore
        c.claude = anthropic.Anthropic(api_key=api_key)
    return c


# -------------------------
# LLM call helpers
# -------------------------
def _extract_valid_object_from_array(arr: list, prefer_anki_cards: bool = True) -> Dict[str, Any]:
    """
    Extract a valid dict object from an array.
    
    Strategy:
    1. If prefer_anki_cards=True (for S2), prefer objects with 'anki_cards' field
    2. Otherwise, return first dict object
    3. If no valid dict found, raise ValueError
    
    Args:
        arr: List of potential objects
        prefer_anki_cards: If True, prefer objects with 'anki_cards' field (for S2 stage)
    
    Returns:
        First valid dict object (preferring one with 'anki_cards' if prefer_anki_cards=True)
    """
    if len(arr) == 0:
        raise ValueError("JSON array is empty - expected a single object")
    
    import sys
    
    # If prefer_anki_cards, first try to find an object with 'anki_cards' field
    if prefer_anki_cards:
        for idx, item in enumerate(arr):
            if isinstance(item, dict) and "anki_cards" in item:
                if len(arr) > 1:
                    print(
                        f"[WARN] LLM returned array with {len(arr)} elements, "
                        f"using element {idx} (has 'anki_cards' field)",
                        file=sys.stderr,
                        flush=True
                    )
                return item
    
    # Otherwise, return first dict object
    for idx, item in enumerate(arr):
        if isinstance(item, dict):
            if len(arr) > 1:
                print(
                    f"[WARN] LLM returned array with {len(arr)} elements, using element {idx}",
                    file=sys.stderr,
                    flush=True
                )
            return item
    
    # No valid dict found
    raise ValueError(
        f"JSON array contains no valid dict objects. "
        f"Array length: {len(arr)}, types: {[type(x).__name__ for x in arr[:3]]}"
    )


def extract_json_object(raw: str, stage: Optional[int] = None) -> Dict[str, Any]:
    """
    Extract JSON object from raw text response.
    Handles various formats:
    - Direct JSON
    - JSON in code blocks (```json ... ```)
    - JSON wrapped in text
    - Multiple JSON objects (returns first valid one)
    - Truncated JSON (attempts repair for end truncation)
    - Arrays (extracts first valid object, preferring one with 'anki_cards' for S2)
    
    Args:
        raw: Raw text response from LLM
        stage: Stage number (1 for S1, 2 for S2). If None, defaults to prefer_anki_cards=False
    """
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Empty response")
    
    # Determine if we should prefer objects with 'anki_cards' field (only for S2)
    prefer_anki_cards = (stage == 2)

    # Pre-processing: Fix common JSON issues from LLM responses
    # Note: This is a best-effort repair, not a perfect solution
    # The primary fix should be in the prompt (avoiding quotes in cell content)
    raw_cleaned = raw
    # Try to fix unescaped quotes in string values (heuristic: quotes inside {...} that aren't escaped)
    # This is risky, so we only do it if direct parse fails
    
    # Try 1: Direct JSON parse
    try:
        parsed = json.loads(raw)
        # Handle case where LLM returns an array instead of an object
        # This can happen despite prompt instructions - extract valid object from array
        if isinstance(parsed, list):
            parsed = _extract_valid_object_from_array(parsed, prefer_anki_cards=prefer_anki_cards)
        if not isinstance(parsed, dict):
            raise ValueError(f"JSON root is not an object (got {type(parsed).__name__})")
        return parsed
    except json.JSONDecodeError as e:
        # If parsing fails, attempt to fix common quote issues in master_table_markdown_kr
        # This is a fallback - the prompt should prevent this
        pass

    # Try 2: JSON in code blocks (```json ... ``` or ``` ... ```)
    # Handle both single-line and multi-line code blocks
    code_block_patterns = [
        r"```(?:json)?\s*\n?([\s\S]*?)\n?\s*```",  # Standard code block with optional newlines
        r"```(?:json)?\s*([\s\S]*?)\s*```",  # Standard code block without newlines
        r"```([\s\S]*?)```",  # Any code block
    ]
    for pattern in code_block_patterns:
        matches = re.finditer(pattern, raw, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        for m in matches:
            try:
                json_str = m.group(1).strip()
                # Remove leading/trailing whitespace and newlines
                json_str = json_str.strip()
                if json_str:
                    parsed = json.loads(json_str)
                    # Handle array responses (extract valid object)
                    if isinstance(parsed, list):
                        try:
                            parsed = _extract_valid_object_from_array(parsed, prefer_anki_cards=prefer_anki_cards)
                        except ValueError:
                            continue
                    if isinstance(parsed, dict):
                        return parsed
            except json.JSONDecodeError as e:
                # If JSON parsing fails, try to find the first complete JSON object within the extracted string
                # This handles cases where there might be extra text before or after the JSON
                first_brace = json_str.find('{')
                if first_brace >= 0:
                    # Try to find balanced braces
                    brace_count = 0
                    end_idx = -1
                    for i, char in enumerate(json_str[first_brace:], start=first_brace):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break
                    if end_idx > first_brace:
                        try:
                            parsed = json.loads(json_str[first_brace:end_idx])
                            if isinstance(parsed, list):
                                parsed = _extract_valid_object_from_array(parsed, prefer_anki_cards=prefer_anki_cards)
                            if isinstance(parsed, dict):
                                return parsed
                        except json.JSONDecodeError:
                            pass
                continue
    
    # Try 2.5: Handle case where response starts with ```json but code block is not properly closed
    # This can happen if the response is truncated or malformed
    if raw.strip().startswith("```"):
        # Try to extract JSON after the opening ```json
        json_start_pattern = r"```(?:json)?\s*\n?"
        if re.match(json_start_pattern, raw, re.IGNORECASE):
            # Find where the code block starts
            match = re.match(json_start_pattern, raw, re.IGNORECASE)
            if match:
                json_candidate = raw[match.end():].strip()
                # Try to find the closing ``` or just parse what we have
                closing_idx = json_candidate.find("```")
                if closing_idx > 0:
                    json_candidate = json_candidate[:closing_idx].strip()
                else:
                    # No closing ```, try to parse anyway (might be truncated)
                    json_candidate = json_candidate.strip()
                
                # Try to find first { and parse from there
                first_brace = json_candidate.find('{')
                if first_brace >= 0:
                    json_candidate = json_candidate[first_brace:]
                    try:
                        parsed = json.loads(json_candidate)
                        if isinstance(parsed, list):
                            parsed = _extract_valid_object_from_array(parsed, prefer_anki_cards=prefer_anki_cards)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        # If direct parse fails, try to find balanced braces
                        # This handles cases where there might be trailing text
                        brace_count = 0
                        end_idx = -1
                        for i, char in enumerate(json_candidate):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_idx = i + 1
                                    break
                        if end_idx > 0:
                            try:
                                parsed = json.loads(json_candidate[:end_idx])
                                if isinstance(parsed, list):
                                    parsed = _extract_valid_object_from_array(parsed, prefer_anki_cards=prefer_anki_cards)
                                if isinstance(parsed, dict):
                                    return parsed
                            except json.JSONDecodeError:
                                pass

    # Try 3: Find first JSON object in text (balanced braces)
    # This is more robust than simple regex - finds the first complete JSON object
    brace_count = 0
    start_idx = -1
    in_string = False
    escape_next = False
    string_char = None
    
    for i, char in enumerate(raw):
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
            
        if not in_string:
            if char in ('"', "'"):
                in_string = True
                string_char = char
            elif char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx >= 0:
                    # Found a complete JSON object
                    try:
                        json_str = raw[start_idx:i+1]
                        parsed = json.loads(json_str)
                        # Handle array responses (extract valid object)
                        if isinstance(parsed, list):
                            try:
                                parsed = _extract_valid_object_from_array(parsed, prefer_anki_cards=prefer_anki_cards)
                            except ValueError:
                                start_idx = -1
                                continue
                        if isinstance(parsed, dict):
                            return parsed
                        # If not dict, continue searching
                        start_idx = -1
                    except json.JSONDecodeError:
                        # Continue searching for next JSON object
                        start_idx = -1
                        continue
        else:
            if char == string_char:
                in_string = False
                string_char = None

    # Try 4: Attempt to repair truncated JSON (if it looks like it was cut off)
    # Find the first '{' and try to repair if it appears truncated
    first_brace = raw.find('{')
    if first_brace >= 0:
        # Check if the JSON appears to be truncated (ends in middle of string or unclosed)
        json_candidate = raw[first_brace:]
        
        # Count braces to see if it's unbalanced
        open_braces = json_candidate.count('{')
        close_braces = json_candidate.count('}')
        
        # If we have more open braces, try to close them
        if open_braces > close_braces:
            # Try to repair by closing strings and objects
            repaired = json_candidate
            
            # If it ends in a string (not properly closed), try to close it
            # Find the last unclosed string
            last_quote_idx = -1
            last_quote_char = None
            in_str = False
            escape = False
            for idx, c in enumerate(repaired):
                if escape:
                    escape = False
                    continue
                if c == '\\':
                    escape = True
                    continue
                if not in_str and c in ('"', "'"):
                    in_str = True
                    last_quote_char = c
                    last_quote_idx = idx
                elif in_str and c == last_quote_char:
                    in_str = False
                    last_quote_idx = -1
                    last_quote_char = None
            
            # If we're still in a string at the end, close it
            if in_str and last_quote_char:
                repaired = repaired + last_quote_char
            
            # Close any unclosed braces
            for _ in range(open_braces - close_braces):
                repaired = repaired.rstrip() + "\n}"
            
            try:
                parsed = json.loads(repaired)
                # Handle array responses (extract valid object)
                if isinstance(parsed, list):
                    parsed = _extract_valid_object_from_array(parsed, prefer_anki_cards=prefer_anki_cards)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

    # Try 5: Find any JSON-like structure with regex (fallback)
    # Try array first (more common when LLM misformats)
    m2_array = re.search(r"\[[\s\S]*\]", raw, re.MULTILINE | re.DOTALL)
    if m2_array:
        try:
            parsed = json.loads(m2_array.group(0).strip())
            if isinstance(parsed, list):
                parsed = _extract_valid_object_from_array(parsed, prefer_anki_cards=prefer_anki_cards)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
    # Try object pattern
    m2 = re.search(r"\{[\s\S]*\}", raw, re.MULTILINE | re.DOTALL)
    if m2:
        try:
            parsed = json.loads(m2.group(0).strip())
            # Handle array responses (extract valid object)
            if isinstance(parsed, list):
                parsed = _extract_valid_object_from_array(parsed, prefer_anki_cards=prefer_anki_cards)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

    # If all attempts fail, provide detailed error message
    preview = raw[:500] if len(raw) > 500 else raw
    # Check if response looks truncated
    is_likely_truncated = (
        len(raw) > 1000 and  # Large response
        (raw.rstrip().endswith('...') or 
         raw.rstrip().endswith('"') or
         raw.rstrip().endswith("'") or
         raw.count('{') > raw.count('}'))  # Unbalanced braces
    )
    
    truncation_hint = ""
    if is_likely_truncated:
        truncation_hint = " (Response appears truncated - may need higher max_output_tokens)"
    
    raise ValueError(
        f"Could not parse JSON object from response.{truncation_hint} "
        f"Response preview (first 500 chars): {preview}..."
        if len(raw) > 500 else f"Full response: {raw}"
    )


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)).strip())
    except Exception:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)).strip())
    except Exception:
        return default


# Global API key rotator (initialized in main())
_global_rotator: Optional[Any] = None

def _load_images_for_multimodal(image_paths: Optional[List[Path]]) -> List[Any]:
    """
    Load images from file paths and convert them to Gemini Part objects for multimodal input.
    
    Args:
        image_paths: Optional list of image file paths
        
    Returns:
        List of Part objects (empty list if no images or PIL unavailable)
    """
    if not image_paths:
        return []
    
    try:
        from PIL import Image
        PIL_AVAILABLE = True
    except ImportError:
        PIL_AVAILABLE = False
        print("Warning: PIL/Pillow not available. Image loading disabled.", file=sys.stderr)
        return []
    
    parts = []
    for img_path in image_paths:
        if not img_path or not isinstance(img_path, Path):
            continue
        if not img_path.exists():
            print(f"Warning: Image file not found: {img_path}", file=sys.stderr)
            continue
        
        try:
            # Load image and convert to bytes
            with open(img_path, "rb") as f:
                image_bytes = f.read()
            
            # Determine MIME type from file extension
            ext = img_path.suffix.lower()
            if ext in (".jpg", ".jpeg"):
                mime_type = "image/jpeg"
            elif ext == ".png":
                mime_type = "image/png"
            elif ext == ".gif":
                mime_type = "image/gif"
            elif ext == ".webp":
                mime_type = "image/webp"
            else:
                # Try to detect from file header
                if image_bytes.startswith(b'\xff\xd8\xff'):
                    mime_type = "image/jpeg"
                elif image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
                    mime_type = "image/png"
                else:
                    print(f"Warning: Unknown image format for {img_path}, defaulting to JPEG", file=sys.stderr)
                    mime_type = "image/jpeg"
            
            # Create Part from bytes (will be used with genai_types.Part.from_bytes)
            parts.append({
                "bytes": image_bytes,
                "mime_type": mime_type,
            })
        except Exception as e:
            print(f"Warning: Failed to load image {img_path}: {e}", file=sys.stderr)
            continue
    
    return parts

def _is_transient_error(e: Exception) -> bool:
    """
    Check if error is transient (retryable).
    Note: Quota exhaustion (RPD limit) is NOT transient - it requires key rotation.
    """
    name = type(e).__name__
    msg = str(e).lower()

    # Quota exhaustion indicators (NOT transient - requires key rotation)
    is_quota_exhausted = (
        "quota exceeded" in msg or
        "exceeded your current quota" in msg or
        ("429" in msg and "limit: 0" in msg)
    )
    if is_quota_exhausted:
        return False  # Not transient - requires key rotation

    transient_classnames = {
        "APITimeoutError", "Timeout", "TimeoutError", "ReadTimeout", "ConnectTimeout",
        "APIConnectionError", "RateLimitError", "ServiceUnavailableError",
        "InternalServerError", "BadGatewayError", "GatewayTimeoutError",
        "DeadlineExceeded", "ResourceExhausted", "Unavailable",
    }
    if name in transient_classnames:
        return True

    transient_markers = [
        "timed out", "timeout", "rate limit", "too many requests", "temporarily unavailable",
        "service unavailable", "internal server error", "bad gateway", "gateway timeout",
        "connection aborted", "connection reset", "connection error", "tls", "502", "503", "504", "429",
        # Subprocess watchdog transport-ish failures (treat as transient to allow retry loop)
        "geminisubprocesserror", "emptyipcresult", "subprocess returned no result",
    ]
    return any(m in msg for m in transient_markers)


def _raise_truncation(stage: int, provider: str, finish_reason: str | None) -> None:
    raise RuntimeError(
        f"[Stage{stage}] TruncatedOutputError: provider={provider} finish_reason={finish_reason or 'UNKNOWN'}"
    )



def call_llm(
    *,
    provider: str,
    clients: ProviderClients,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    timeout_s: int,
    stage: int,
    api_style: str,
    # Runtime logging controls
    thinking_enabled: bool,
    thinking_budget: Optional[int] = None,  # Deprecated for Gemini 3, kept for backward compatibility
    thinking_level: Optional[str] = None,  # For Gemini 3: "minimal", "low", "medium", "high"
    rag_enabled: bool = False,
    log_ctx: str = "",
    quota_limiter: Optional[Any] = None,
    image_paths: Optional[List[Path]] = None,  # Optional list of image file paths for multimodal input
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Dict[str, Any], Optional[str]]:
    """
    LLM caller with conservative transient retry and truncation hard-fail.

    Returns:
      (parsed_json | None, err | None, runtime_meta)

    runtime_meta is always returned (even on failure) and is safe to serialize.
    """
    retry_max = _env_int("LLM_RETRY_MAX", 2)
    backoff_base = _env_float("LLM_RETRY_BACKOFF_BASE_S", 2.0)
    jitter_max = _env_float("LLM_RETRY_JITTER_MAX_S", 1.0)
    
    # Global rotator for key rotation (if available)
    global _global_rotator

    # Model-specific and configuration-aware max_output_tokens
    # Base limits from environment or defaults
    base_max_out_stage1 = _env_int("MAX_OUTPUT_TOKENS_STAGE1", 64000)
    base_max_out_stage2 = _env_int("MAX_OUTPUT_TOKENS_STAGE2", 64000)
    
    # Adjust based on model and configuration
    model_lc = (model_name or "").strip().lower()
    
    # Gemini 3 (Pro and Flash) supports up to 64k output tokens per guide
    # Reference: Gemini_3_develop.md - Context Window: 1M / 64k (In / Out)
    GEMINI_3_MAX_OUTPUT_TOKENS = 64000  # 64k as per Gemini 3 guide
    
    if "gemini-3-flash" in model_lc or "gemini-3-pro" in model_lc:
        # Gemini 3 Flash and Pro both support 64k output tokens (per guide)
        # Stage1: Allow full 64k limit for Stage1 outputs (same as Stage2)
        # Some groups with many entities require extensive tokens for complete master table
        # Use environment variable if set, otherwise default to 16k (safe default)
        # Maximum allowed: 64k (full limit) - Stage1 and Stage2 are separate API calls
        stage1_max_limit = 64000  # 64k max for Stage1 (same as Stage2)
        if thinking_enabled:
            # Thinking mode may consume internal reasoning tokens, but guide states 64k max output
            max_out_stage1 = min(base_max_out_stage1, stage1_max_limit)
        else:
            # Without thinking, can use full Stage1 base limit up to 64k
            max_out_stage1 = min(base_max_out_stage1, stage1_max_limit)
        
        # Stage2: Guide states 64k output max - use higher limits aligned with guide
        # Some entities (e.g., "Dermal Sinus Tract", "US Interactions") require very long outputs
        # Use 61440 (64k - 1k margin) to leave safety margin for API overhead
        # For Gemini 3 models, we historically forced near-64k output to avoid truncation on complex entities.
        # However, this can make individual calls take several minutes and trigger S2 "stall" warnings in smoke runs.
        # Allow opting out via env for debugging / faster iteration:
        #   GEMINI3_STAGE2_FORCE_64K=0  (then MAX_OUTPUT_TOKENS_STAGE2 is respected)
        force_stage2_64k = _env_int("GEMINI3_STAGE2_FORCE_64K", 1) == 1
        stage2_target = 61440
        if thinking_enabled and rag_enabled:
            # Thinking + RAG: Full guide limit with safety margin
            max_out_stage2 = (max(base_max_out_stage2, stage2_target) if force_stage2_64k else min(base_max_out_stage2, stage2_target))
        elif thinking_enabled or rag_enabled:
            # Thinking OR RAG: Full guide limit with safety margin
            max_out_stage2 = (max(base_max_out_stage2, stage2_target) if force_stage2_64k else min(base_max_out_stage2, stage2_target))
        else:
            # Base mode: Full guide limit with safety margin
            max_out_stage2 = (max(base_max_out_stage2, stage2_target) if force_stage2_64k else min(base_max_out_stage2, stage2_target))
    elif "gpt-5.2" in model_lc:
        # GPT-5.2: Latest model with extended output token support
        # Input context: 400k tokens
        # Output tokens: Likely 128k+ (conservative estimate: 128k)
        # Use environment variable if set, otherwise apply model-specific limits
        gpt52_stage1_limit = 131072  # 128k max for GPT-5.2 (Stage1) - conservative estimate
        gpt52_stage2_limit = 131072  # 128k max for GPT-5.2 (Stage2) - conservative estimate
        max_out_stage1 = min(base_max_out_stage1, gpt52_stage1_limit)
        max_out_stage2 = min(base_max_out_stage2, gpt52_stage2_limit)
    elif "gpt" in model_lc or provider == "gpt":
        # GPT-4 and older GPT models
        # GPT-4: max 32k output tokens
        # GPT-4 Turbo: max 128k output tokens
        # Use environment variable if set, otherwise apply model-specific limits
        gpt_stage1_limit = 32000  # 32k max for GPT-4 models (Stage1)
        gpt_stage2_limit = 32000  # 32k max for GPT-4 models (Stage2)
        max_out_stage1 = min(base_max_out_stage1, gpt_stage1_limit)
        max_out_stage2 = min(base_max_out_stage2, gpt_stage2_limit)
    elif "claude" in model_lc or provider == "claude":
        # Claude models (Claude 3.5 Sonnet, etc.)
        # Claude 3.5 Sonnet: max 8k output tokens (conservative)
        # Claude 3 Opus: max 8k output tokens
        # Use environment variable if set, otherwise apply model-specific limits
        claude_stage1_limit = 8000  # 8k max for Claude models (Stage1)
        claude_stage2_limit = 8000  # 8k max for Claude models (Stage2)
        max_out_stage1 = min(base_max_out_stage1, claude_stage1_limit)
        max_out_stage2 = min(base_max_out_stage2, claude_stage2_limit)
    else:
        # Other models (Gemini 2.5, DeepSeek, etc.): use base limits from environment
        max_out_stage1 = base_max_out_stage1
        max_out_stage2 = base_max_out_stage2
    
    max_out = max_out_stage1 if stage == 1 else max_out_stage2

    # meta container (always returned)
    meta: Dict[str, Any] = {
        "stage": stage,
        "provider": provider,
        "model": model_name,
        "api_style": (api_style or "").strip().lower(),
        "thinking_enabled": bool(thinking_enabled),
        "thinking_budget": int(thinking_budget) if thinking_budget is not None else None,
        "thinking_level": thinking_level,
        "rag_enabled": bool(rag_enabled),
        "max_output_tokens": max_out,  # Record the actual limit used (model/configuration-aware)
        "attempts": 0,
        "latency_sec": None,
        "finish_reason": None,
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "raw_usage": None,
        "error_class": None,
        "error_message": None,
        "rag_queries_count": 0,
        "rag_sources_count": 0,
        "log_ctx": (log_ctx.strip() or None),
    }

    last_err: Optional[str] = None

    # Heartbeat + watchdog (helps tmux/tee runs distinguish "slow" vs "hung")
    heartbeat_s = _env_float("LLM_HEARTBEAT_S", 30.0)
    log_request_start = _env_int("LLM_LOG_REQUEST_START", 1)
    watchdog_s: Optional[float] = None
    try:
        if timeout_s and int(timeout_s) > 0:
            watchdog_s = float(_env_float("LLM_WATCHDOG_TIMEOUT_S", float(timeout_s)))
    except Exception:
        watchdog_s = float(timeout_s) if timeout_s and int(timeout_s) > 0 else None

    # Quota-exhaustion rotation budget (each rotation adds one extra attempt)
    rotations_used = 0
    rotation_budget = 0
    if provider == "gemini" and _global_rotator is not None:
        try:
            nkeys = len(getattr(_global_rotator, "keys", []) or [])
            rotation_budget = _env_int("LLM_QUOTA_ROTATION_MAX", nkeys if nkeys > 0 else 1)
        except Exception:
            rotation_budget = _env_int("LLM_QUOTA_ROTATION_MAX", 1)

    max_total_attempts = retry_max + 1
    attempt = 0
    while attempt < max_total_attempts:
        meta["attempts"] = attempt + 1
        try:
            # Stage latency should reflect the successful request attempt.
            t0 = time.perf_counter()

            if provider == "gemini":
                # Google GenAI SDK (google-genai - new version)
                from google.genai import types as genai_types  # type: ignore
                client = clients.gemini
                if log_request_start:
                    # Log to file only (via metrics or suppress terminal output)
                    # Terminal output suppressed for cleaner progress bars
                    pass
                
                # Build generation config
                config_kwargs = {
                    "temperature": temperature,
                    "max_output_tokens": max_out,
                }
                
                # Add system instruction to config
                if system_prompt:
                    config_kwargs["system_instruction"] = system_prompt
                
                # [CRITICAL] Search tool cannot be used with response_mime_type='application/json'
                if not rag_enabled:
                    config_kwargs["response_mime_type"] = "application/json"
                
                # Apply Thinking (Gemini 3 uses thinking_level, not thinking_budget)
                # For Gemini 3 Flash: minimal (lowest) or high (default/max)
                if model_name.startswith("gemini-3"):
                    # Gemini 3: use thinking_level
                    if thinking_level:
                        # Type cast: thinking_level is str but ThinkingConfig expects ThinkingLevel enum
                        level_val = str(thinking_level).strip().lower()
                        config_kwargs["thinking_config"] = genai_types.ThinkingConfig(
                            thinking_level=level_val  # type: ignore
                        )
                    elif thinking_enabled:
                        # Default to "high" if thinking is enabled but level not specified
                        config_kwargs["thinking_config"] = genai_types.ThinkingConfig(
                            thinking_level="high"  # type: ignore
                        )
                    else:
                        # Default to "minimal" if thinking is disabled
                        config_kwargs["thinking_config"] = genai_types.ThinkingConfig(
                            thinking_level="minimal"  # type: ignore
                        )
                else:
                    # Gemini 2.5: use thinking_budget (backward compatibility)
                    if thinking_enabled and thinking_budget is not None and thinking_budget > 0:
                        config_kwargs["thinking_config"] = genai_types.ThinkingConfig(
                            thinking_budget=thinking_budget
                        )
                
                # Apply Search (RAG)
                if rag_enabled:
                    grounding_tool = genai_types.Tool(
                        google_search=genai_types.GoogleSearch()
                    )
                    config_kwargs["tools"] = [grounding_tool]
                
                generation_config = genai_types.GenerateContentConfig(**config_kwargs)

                # Build contents for multimodal input (text + images)
                image_parts = _load_images_for_multimodal(image_paths)
                if image_parts:
                    # Multimodal: combine text and images
                    # Gemini Python SDK: create list with text and Part objects
                    # The SDK's generate_content accepts a list where elements can be:
                    # - strings (converted to text Parts)
                    # - Part objects (from_bytes, from_uri, etc.)
                    parts_list: List[Any] = []
                    # Add text as first element
                    parts_list.append(user_prompt)
                    # Add image Parts
                    for img_part in image_parts:
                        try:
                            # Try keyword arguments first
                            try:
                                part = genai_types.Part.from_bytes(  # type: ignore[call-arg]
                                    data=img_part["bytes"],
                                    mime_type=img_part["mime_type"]
                                )
                            except (TypeError, AttributeError):
                                # Fallback: create Part object directly with inline_data
                                part = genai_types.Part(
                                    inline_data=genai_types.Blob(
                                        data=img_part["bytes"],
                                        mime_type=img_part["mime_type"]
                                    )
                                )
                            parts_list.append(part)
                        except Exception as e:
                            print(f"Warning: Failed to create Part from image: {e}", file=sys.stderr)
                            continue
                    contents = parts_list  # SDK accepts list of strings and Parts
                else:
                    # Text-only: use string directly (SDK will convert to Content)
                    contents = user_prompt

                # ---- Global quota limiting (RPM/TPM/RPD) ----
                # Conservative estimate: prompt tokens + 40% of max output tokens.
                # For images, add extra token estimate (roughly 1 token per 256 bytes of image data)
                # Real token usage is logged via usage_metadata when available.
                if quota_limiter is not None:
                    try:
                        est_in = _approx_tokens(system_prompt or "") + _approx_tokens(user_prompt or "")
                        # Add image token estimate (rough approximation: 1 token per 256 bytes)
                        if image_parts:
                            for img_part in image_parts:
                                img_bytes = img_part.get("bytes", b"")
                                est_in += len(img_bytes) // 256
                        est_out = int(max_out * 0.40)
                        est_total = int(max(0, est_in + est_out))
                        quota_limiter.acquire_request(estimated_tokens=est_total, rpd_cost=1)
                        meta["quota_est_tokens"] = est_total
                    except RuntimeError as qe:
                        # RPD limit exceeded: Treat as quota exhaustion and rotate to next key.
                        # We don't track RPD usage per key anymore - just rotate on error.
                        error_str = str(qe)
                        if "RPD limit exceeded" in error_str:
                            # Treat RPD error as quota exhaustion to trigger key rotation
                            if provider == "gemini" and _global_rotator is not None:
                                try:
                                    if rotations_used < rotation_budget:
                                        new_key, new_index = _global_rotator.rotate_on_quota_exhausted(error_str)
                                        from google import genai  # type: ignore
                                        from google.genai import types as genai_types  # type: ignore
                                        http_options = None
                                        if timeout_s and int(timeout_s) > 0:
                                            timeout_sec = max(int(timeout_s), 10)
                                            http_options = genai_types.HttpOptions(timeout=timeout_sec * 1000)
                                        clients.gemini = genai.Client(api_key=new_key, http_options=http_options)
                                        rotations_used += 1
                                        max_total_attempts += 1
                                        meta["rotations_used"] = rotations_used
                                        meta["rotated_key_index"] = int(new_index)
                                        ctx = (" " + log_ctx.strip()) if log_ctx and log_ctx.strip() else ""
                                        print(
                                            f"[API Rotator] rotated_for_rpd stage={stage} provider=gemini "
                                            f"new_index={new_index} rotations_used={rotations_used}/{rotation_budget}{ctx}",
                                            flush=True,
                                        )
                                        attempt += 1
                                        continue  # Retry with new key
                                except Exception as rot_e:
                                    # Rotation failed; fall through to error
                                    meta["rotator_error"] = f"{type(rot_e).__name__}: {rot_e}"
                            
                            # If rotation failed or not available, return error
                            meta["error_class"] = type(qe).__name__
                            meta["error_message"] = error_str
                            _append_metrics_jsonl({**meta, "ok": False, "ts": int(time.time())})
                            return None, f"[Stage{stage}] RPD limit exceeded: {error_str}. Tried to rotate keys but failed or no more keys available.", meta, None
                        # Other RuntimeError from quota_limiter: re-raise as-is
                        meta["error_class"] = type(qe).__name__
                        meta["error_message"] = error_str
                        _append_metrics_jsonl({**meta, "ok": False, "ts": int(time.time())})
                        return None, f"[Stage{stage}] QuotaError: {qe}", meta, None
                    except Exception as qe:
                        meta["error_class"] = type(qe).__name__
                        meta["error_message"] = str(qe)
                        _append_metrics_jsonl({**meta, "ok": False, "ts": int(time.time())})
                        return None, f"[Stage{stage}] QuotaError: {qe}", meta, None
                
                # NOTE: http_options is set at client creation time (in build_clients())
                # The client.models.generate_content() method does NOT accept http_options parameter
                # HTTP-level timeout is already configured in the client, so we rely on that
                # plus the watchdog timeout mechanism below for additional safety
                
                # Generate content (hard-timeout safe): run SDK call in a subprocess when watchdog is enabled.
                use_subprocess_watchdog = _env_int("LLM_GEMINI_SUBPROCESS_WATCHDOG", 1) == 1
                # Default policy: enable subprocess watchdog for S2, but keep S1 on direct SDK calls
                # unless explicitly enabled (S1 prompt can be heavy and slow; watchdog for S1 is often unnecessary).
                if stage == 1:
                    use_subprocess_watchdog = use_subprocess_watchdog and (_env_int("LLM_GEMINI_SUBPROCESS_WATCHDOG_STAGE1", 0) == 1)
                else:
                    use_subprocess_watchdog = use_subprocess_watchdog and (_env_int("LLM_GEMINI_SUBPROCESS_WATCHDOG_STAGE2", 1) == 1)

                if watchdog_s is not None and watchdog_s > 0 and heartbeat_s and heartbeat_s > 0 and use_subprocess_watchdog:
                    # Align client http timeout with build_clients() behavior: seconds -> ms, clamp to minimum 10s.
                    timeout_sec = 0
                    try:
                        timeout_sec = int(timeout_s) if timeout_s else 0
                    except Exception:
                        timeout_sec = 0
                    if timeout_sec > 0:
                        timeout_sec = max(timeout_sec, 10)
                    timeout_ms = (timeout_sec * 1000) if timeout_sec > 0 else None

                    api_key = _get_gemini_api_key_for_subprocess()
                    # Watchdog logging suppressed for cleaner terminal output
                    # Logs are still available in metrics file if needed

                    # For subprocess watchdog, serialize image data as base64
                    image_data_base64 = None
                    image_mime_types = None
                    if image_parts:
                        import base64
                        # Serialize first image only (subprocess payload limitation)
                        # In practice, S5 will typically use one image per call
                        if len(image_parts) > 0:
                            img_bytes = image_parts[0].get("bytes", b"")
                            img_mime_type = image_parts[0].get("mime_type", "image/jpeg")
                            image_data_base64 = base64.b64encode(img_bytes).decode("utf-8")
                            image_mime_types = [img_mime_type]
                            # Note: Subprocess watchdog may need enhancement for multiple images
                            # For now, support single image per call

                    r_info = _run_gemini_generate_with_hard_timeout(
                        payload={
                            "api_key": api_key,
                            "timeout_ms": timeout_ms,
                            "model_name": model_name,
                            "system_prompt": system_prompt,
                            "user_prompt": user_prompt,
                            "temperature": temperature,
                            "max_output_tokens": max_out,
                            "thinking_enabled": thinking_enabled,
                            "thinking_level": thinking_level,
                            "rag_enabled": rag_enabled,
                            "image_data_base64": image_data_base64,  # Optional: base64-encoded image for subprocess
                            "image_mime_types": image_mime_types,  # Optional: list of MIME types
                        },
                        watchdog_s=float(watchdog_s),
                        heartbeat_s=float(heartbeat_s),
                        stage=stage,
                        log_ctx=log_ctx,
                    )

                    if not r_info.get("ok"):
                        raise RuntimeError(
                            f"GeminiSubprocessError: {r_info.get('error_class')}: {r_info.get('error_message')}"
                        )

                    # Stitch a minimal response-like dict for downstream parsing/metrics.
                    r = r_info
                else:
                    # Fallback (no watchdog): direct SDK call.
                    r = client.models.generate_content(
                        model=model_name,
                        contents=contents,  # Use multimodal contents (text + images) if available
                        config=generation_config,
                    )

                meta["latency_sec"] = round(time.perf_counter() - t0, 6)

                # Finish reason (best-effort)
                finish_reason = None
                try:
                    if isinstance(r, dict) and "finish_reason" in r:
                        finish_reason = r.get("finish_reason")
                    else:
                        cands = getattr(r, "candidates", None) or []
                        if cands:
                            finish_reason = getattr(cands[0], "finish_reason", None)
                except Exception:
                    finish_reason = None
                meta["finish_reason"] = str(finish_reason) if finish_reason is not None else None

                if finish_reason is not None:
                    fr = str(finish_reason).upper()
                    # Check for truncation: enum value "2", "MAX_TOKENS" in string, or enum name "FINISHREASON.MAX_TOKENS"
                    is_truncated = (
                        fr == "2" or
                        "MAX_TOKENS" in fr or
                        "LENGTH" in fr or
                        "FINISHREASON.MAX_TOKENS" in fr or
                        "FINISH_REASON_MAX_TOKENS" in fr
                    )
                    if is_truncated:
                        _raise_truncation(stage, provider, fr)

                # Token usage (best-effort; may be absent)
                try:
                    if isinstance(r, dict) and isinstance(r.get("usage"), dict):
                        u = r.get("usage") or {}
                        pt = u.get("prompt_token_count")
                        ct = u.get("candidates_token_count")
                        tt = u.get("total_token_count")
                    else:
                        um = getattr(r, "usage_metadata", None)
                        pt = getattr(um, "prompt_token_count", None) if um is not None else None
                        ct = getattr(um, "candidates_token_count", None) if um is not None else None
                        tt = getattr(um, "total_token_count", None) if um is not None else None
                    meta["input_tokens"] = int(pt) if pt is not None else None
                    meta["output_tokens"] = int(ct) if ct is not None else None
                    meta["total_tokens"] = int(tt) if tt is not None else None
                    meta["raw_usage"] = {
                        "prompt_token_count": meta["input_tokens"],
                        "candidates_token_count": meta["output_tokens"],
                        "total_token_count": meta["total_tokens"],
                    }
                except Exception:
                    pass

                if isinstance(r, dict) and isinstance(r.get("raw_text"), str):
                    raw_text = (r.get("raw_text") or "").strip()
                else:
                    raw_text = (getattr(r, "text", None) or "").strip()
                    if not raw_text:
                        # Fallback: assemble from parts if .text is unavailable/empty
                        try:
                            cands = getattr(r, "candidates", None) or []
                            if cands:
                                content = getattr(cands[0], "content", None)
                                parts = getattr(content, "parts", None) or []
                                raw_text = "".join([(getattr(p, "text", "") or "") for p in parts]).strip()
                        except Exception:
                            raw_text = ""

                if not raw_text:
                    raise ValueError("Empty response text from provider=gemini (google-genai)")

                # LLM phase logging suppressed for cleaner terminal output
                # Logs are still available in metrics file if needed

                # Log RAG grounding metadata (if search was used)
                if rag_enabled:
                    try:
                        if isinstance(r, dict):
                            meta["rag_queries_count"] = int(r.get("rag_queries_count") or 0)
                            meta["rag_sources_count"] = int(r.get("rag_sources_count") or 0)
                        else:
                            cands = getattr(r, "candidates", None) or []
                            if cands and len(cands) > 0:
                                gm = getattr(cands[0], "grounding_metadata", None)
                                if gm is not None:
                                    queries = getattr(gm, "web_search_queries", None) or []
                                    chunks = getattr(gm, "grounding_chunks", None) or []
                                    meta["rag_queries_count"] = len(queries) if isinstance(queries, list) else 0
                                    meta["rag_sources_count"] = len(chunks) if isinstance(chunks, list) else 0
                    except Exception:
                        pass  # Best-effort logging

                try:
                    parsed_json = extract_json_object(raw_text, stage=stage)
                    # Record successful API call
                    if _global_rotator is not None and provider == "gemini":
                        _global_rotator.record_success()
                    _append_metrics_jsonl({**meta, "ok": True, "ts": int(time.time())})
                    return parsed_json, None, meta, raw_text
                except Exception as e:
                    err = f"[Stage{stage}] JSONParseError: {e}"
                    meta["error_class"] = "JSONParseError"
                    meta["error_message"] = err
                    _append_metrics_jsonl({**meta, "ok": False, "ts": int(time.time())})
                    return None, err, meta, raw_text

            if provider == "gpt":
                cli = clients.openai
                api_style_norm = (api_style or "").strip().lower()
                if api_style_norm not in {"chat", "responses"}:
                    err = f"Invalid api_style for provider=gpt: {api_style_norm} (expected chat|responses)"
                    meta["error_class"] = "ConfigError"
                    meta["error_message"] = err
                    return None, err, meta, None

                # "thinking" controls are provider/model dependent.
                # For audit, we always log intended values; API params are best-effort and may be ignored.
                if api_style_norm == "chat":
                    # OpenAI Chat Completions (legacy)
                    r = cli.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        response_format={"type": "json_object"},
                        temperature=temperature,
                        max_tokens=max_out,
                        timeout=timeout_s,
                    )
                    meta["latency_sec"] = round(time.perf_counter() - t0, 6)

                    # Usage (best-effort)
                    try:
                        u = getattr(r, "usage", None)
                        if u is not None:
                            pt = getattr(u, "prompt_tokens", None)
                            ct = getattr(u, "completion_tokens", None)
                            tt = getattr(u, "total_tokens", None)
                            meta["input_tokens"] = int(pt) if pt is not None else None
                            meta["output_tokens"] = int(ct) if ct is not None else None
                            meta["total_tokens"] = int(tt) if tt is not None else None
                            meta["raw_usage"] = {
                                "prompt_tokens": meta["input_tokens"],
                                "completion_tokens": meta["output_tokens"],
                                "total_tokens": meta["total_tokens"],
                            }
                    except Exception:
                        pass

                    finish_reason = None
                    try:
                        finish_reason = getattr(r.choices[0], "finish_reason", None)
                    except Exception:
                        finish_reason = None
                    meta["finish_reason"] = str(finish_reason) if finish_reason is not None else None

                    if meta["finish_reason"] is not None:
                        fr = str(meta["finish_reason"]).upper()
                        if "LENGTH" in fr or "MAX_TOKENS" in fr:
                            _raise_truncation(stage, provider, fr)

                    try:
                        content = r.choices[0].message.content
                    except Exception:
                        content = None
                    if not isinstance(content, str) or not content.strip():
                        err = f"[Stage{stage}] EmptyResponseError: missing message content"
                        meta["error_class"] = "EmptyResponseError"
                        meta["error_message"] = err
                        return None, err, meta, None
                    raw_text = content
                    try:
                        parsed_json = extract_json_object(raw_text, stage=stage)
                        return parsed_json, None, meta, raw_text
                    except Exception as e:
                        err = f"[Stage{stage}] JSONParseError: {e}"
                        meta["error_class"] = "JSONParseError"
                        meta["error_message"] = err
                        return None, err, meta, raw_text

                # OpenAI Responses API
                api_kwargs: Dict[str, Any] = dict(
                    model=model_name,
                    input=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    text={"format": {"type": "json_object"}},
                    max_output_tokens=max_out,
                    timeout=timeout_s,
                )

                # GPT-5.2 parameter compatibility:
                # - temperature/top_p/logprobs are only supported when reasoning.effort == "none".
                #   Passing temperature with other reasoning efforts raises 400.
                model_lc = (model_name or "").strip().lower()
                effort_env = (os.getenv("OPENAI_REASONING_EFFORT", "") or "").strip().lower()

                reasoning_effort: Optional[str] = None
                if model_lc.startswith("gpt-5.2-pro"):
                    if not thinking_enabled:
                        err = (
                            f"[Stage{stage}] ConfigError: {model_name} does not support reasoning.effort='none'. "
                            f"Use gpt-5.2 (non-pro) or enable thinking."
                        )
                        meta["error_class"] = "ConfigError"
                        meta["error_message"] = err
                        return None, err, meta, None
                    reasoning_effort = effort_env or "medium"
                elif model_lc.startswith("gpt-5.2"):
                    # Default for GPT-5.2 is 'medium' when not set; we explicitly force 'none' when thinking is disabled.
                    reasoning_effort = (effort_env or ("medium" if thinking_enabled else "none"))
                else:
                    # Non GPT-5.2 models: apply env only when explicitly requested.
                    reasoning_effort = effort_env or None

                if reasoning_effort is not None:
                    api_kwargs["reasoning"] = {"effort": reasoning_effort}  # type: ignore

                # Only include temperature when allowed.
                if model_lc.startswith("gpt-5.2"):
                    if reasoning_effort == "none":
                        api_kwargs["temperature"] = temperature  # type: ignore
                else:
                    api_kwargs["temperature"] = temperature  # type: ignore

                r = cli.responses.create(**api_kwargs)
                meta["latency_sec"] = round(time.perf_counter() - t0, 6)

                # Usage (best-effort; schema differs)
                try:
                    u = getattr(r, "usage", None)
                    if u is not None:
                        # responses usage may be nested (input_tokens/output_tokens)
                        it = getattr(u, "input_tokens", None)
                        ot = getattr(u, "output_tokens", None)
                        tt = getattr(u, "total_tokens", None)
                        meta["input_tokens"] = int(it) if it is not None else None
                        meta["output_tokens"] = int(ot) if ot is not None else None
                        meta["total_tokens"] = int(tt) if tt is not None else None
                        meta["raw_usage"] = {  # type: ignore
                            "input_tokens": meta["input_tokens"],
                            "output_tokens": meta["output_tokens"],
                            "total_tokens": meta["total_tokens"],
                        }
                except Exception:
                    pass

                # Extract output_text
                text_parts: List[str] = []
                try:
                    ot = getattr(r, "output_text", None)
                    if isinstance(ot, str) and ot.strip():
                        text_parts.append(ot)
                except Exception:
                    pass

                if not text_parts:
                    # fallback traversal
                    try:
                        for item in (getattr(r, "output", None) or []):
                            for c in (getattr(item, "content", None) or []):
                                t = getattr(c, "text", None)
                                if isinstance(t, str) and t.strip():
                                    text_parts.append(t)
                    except Exception:
                        pass

                if not text_parts:
                    err = f"[Stage{stage}] EmptyResponseError: responses output_text missing"
                    meta["error_class"] = "EmptyResponseError"
                    meta["error_message"] = err
                    return None, err, meta, None

                # finish_reason is not always exposed in responses; leave as None if absent
                raw_text = "\n".join(text_parts)
                try:
                    parsed_json = extract_json_object(raw_text, stage=stage)
                    # Record successful API call (GPT doesn't use rotator, but keeping structure consistent)
                    return parsed_json, None, meta, raw_text
                except Exception as e:
                    err = f"[Stage{stage}] JSONParseError: {e}"
                    meta["error_class"] = "JSONParseError"
                    meta["error_message"] = err
                    return None, err, meta, raw_text

            return None, f"[Stage{stage}] UnsupportedProvider: {provider}", meta, None

        except Exception as e:
            meta["error_class"] = type(e).__name__
            meta["error_message"] = str(e)
            if quota_limiter is not None:
                try:
                    msg_lc = str(e).lower()
                    if "429" in msg_lc or "too many requests" in msg_lc or "rate limit" in msg_lc:
                        quota_limiter.note_429()
                except Exception:
                    pass
            _append_metrics_jsonl({**meta, "ok": False, "ts": int(time.time())})

            # Quota exhaustion is NOT transient; rotate key (if available) then retry immediately.
            if provider == "gemini" and _global_rotator is not None:
                try:
                    is_quota_exhausted = bool(_global_rotator.is_quota_exhausted_error(e))
                except Exception:
                    is_quota_exhausted = False

                if is_quota_exhausted and rotations_used < rotation_budget:
                    try:
                        new_key, new_index = _global_rotator.rotate_on_quota_exhausted(str(e))
                        from google import genai  # type: ignore
                        from google.genai import types as genai_types  # type: ignore
                        http_options = None
                        if timeout_s and int(timeout_s) > 0:
                            timeout_sec = max(int(timeout_s), 10)
                            http_options = genai_types.HttpOptions(timeout=timeout_sec * 1000)
                        clients.gemini = genai.Client(api_key=new_key, http_options=http_options)
                        rotations_used += 1
                        max_total_attempts += 1  # don't consume the whole retry budget just by rotating
                        meta["rotations_used"] = rotations_used
                        meta["rotated_key_index"] = int(new_index)
                        ctx = (" " + log_ctx.strip()) if log_ctx and log_ctx.strip() else ""
                        print(
                            f"[API Rotator] rotated_for_quota stage={stage} provider=gemini "
                            f"new_index={new_index} rotations_used={rotations_used}/{rotation_budget}{ctx}",
                            flush=True,
                        )
                        attempt += 1
                        continue
                    except Exception as rot_e:
                        # Rotation failed; fall through to normal error handling.
                        meta["rotator_error"] = f"{type(rot_e).__name__}: {rot_e}"

            if _is_transient_error(e) and attempt < (max_total_attempts - 1):
                last_err = f"[Stage{stage}] {type(e).__name__}: {e} (attempt={attempt+1}/{max_total_attempts})"
                sleep_s = backoff_base * (2 ** attempt) + random.random() * jitter_max
                time.sleep(min(sleep_s, 30.0))
                attempt += 1
                continue

            return None, f"[Stage{stage}] {type(e).__name__}: {e}", meta, None
        finally:
            # Increment attempt counter on successful iterations is handled by return.
            pass
        attempt += 1

    return None, last_err or f"[Stage{stage}] UnknownError: retry loop exhausted", meta, None


# -------------------------
# Schema Retry Wrapper (P0: Schema failure retry policy)
# -------------------------
MAX_SCHEMA_ATTEMPTS = 3  # Fixed: 1 initial + 2 retries = 3 total

SCHEMA_RETRY_FEEDBACK_TEMPLATE = (
    "Your previous output failed schema validation. Fix the errors and re-output ONLY the valid JSON. "
    "Do not add extra keys."
)

def _classify_schema_error(error: Exception) -> Tuple[str, str]:
    """
    Classify schema validation error into error_type and error_summary.
    
    Returns:
        (error_type, error_summary): Tuple of error classification
    """
    error_msg = str(error).lower()
    error_type = "unknown"
    error_summary = str(error)[:200]  # Truncate to 200 chars
    
    if "json" in error_msg and ("parse" in error_msg or "decode" in error_msg):
        error_type = "json_parse"
    elif "missing" in error_msg and ("key" in error_msg or "field" in error_msg):
        error_type = "schema_missing_key"
    elif "type" in error_msg and ("mismatch" in error_msg or "expected" in error_msg):
        error_type = "type_mismatch"
    elif "card" in error_msg and ("count" in error_msg or "length" in error_msg or "exactly" in error_msg):
        error_type = "card_count_mismatch"
    elif "visual_type_category" in error_msg or "master_table" in error_msg or "entity_list" in error_msg:
        error_type = "s1_required_field"
    elif "image_hint" in error_msg or "card_role" in error_msg or "anki_cards" in error_msg:
        error_type = "s2_required_field"
    elif "deictic" in error_msg or "image reference" in error_msg:
        error_type = "s2_deictic_reference"
    elif "options" in error_msg or "correct_index" in error_msg:
        error_type = "s2_mcq_format"
    
    return error_type, error_summary


def call_llm_with_schema_retry(
    *,
    provider: str,
    clients: ProviderClients,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    timeout_s: int,
    stage: int,
    api_style: str,
    thinking_enabled: bool,
    thinking_budget: Optional[int] = None,
    thinking_level: Optional[str] = None,
    rag_enabled: bool = False,
    validate_fn: Callable[[Dict[str, Any]], Dict[str, Any]],  # Validation function (validate_stage1 or validate_stage2)
    run_tag: str,
    arm: str,
    group_id: str,
    out_dir: Path,
    entity_id: Optional[str] = None,
    entity_name: Optional[str] = None,
    row_index: Optional[int] = None,
    quota_limiter: Optional[Any] = None,
    progress_logger: Optional[Any] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Dict[str, Any], Optional[str], Dict[str, Any]]:
    """
    LLM caller with schema validation retry (up to MAX_SCHEMA_ATTEMPTS total attempts).
    
    Schema retry policy:
    - On schema validation failure, retry with standardized error feedback (B mode)
    - Maximum MAX_SCHEMA_ATTEMPTS attempts (1 initial + 2 retries)
    - All attempts are logged to raw_llm/ and retry_log.jsonl
    
    Args:
        validate_fn: Validation function that raises ValueError on schema failure
        run_tag: Run tag for logging
        arm: Arm identifier
        group_id: Group identifier
        out_dir: Output directory for artifacts
        entity_id: Entity ID (for S2, optional for S1)
        entity_name: Entity name (for S2, optional for S1)
        row_index: Row index (optional, for traceability)
    
    Returns:
        (parsed_json | None, err | None, runtime_meta, raw_response, retry_meta)
        retry_meta contains: attempt_count, retry_occurred, retry_log_path, raw_paths
    """
    retry_meta: Dict[str, Any] = {
        "attempt_count": 0,
        "retry_occurred": False,
        "retry_log_path": None,
        "raw_paths": [],
        "errors": [],
    }
    
    # Prepare retry log directory
    retry_log_dir = out_dir / "logs"
    retry_log_dir.mkdir(parents=True, exist_ok=True)
    retry_log_path = retry_log_dir / "llm_schema_retry_log.jsonl"
    
    # Prepare raw_llm directory
    raw_llm_dir = out_dir / "raw_llm" / f"stage{stage}" / arm / group_id
    if entity_id:
        raw_llm_dir = raw_llm_dir / entity_id
    raw_llm_dir.mkdir(parents=True, exist_ok=True)
    
    # Base prompts (will be modified on retry)
    current_system_prompt = system_prompt
    current_user_prompt = user_prompt
    
    last_error: Optional[Exception] = None
    last_error_type: Optional[str] = None
    last_error_summary: Optional[str] = None
    
    for attempt_idx in range(1, MAX_SCHEMA_ATTEMPTS + 1):
        retry_meta["attempt_count"] = attempt_idx
        
        # Call LLM
        ctx_parts = [
            f"run_tag={run_tag}",
            f"arm={arm}",
            f"group_id={group_id}",
            f"schema_attempt={attempt_idx}/{MAX_SCHEMA_ATTEMPTS}",
        ]
        if entity_id:
            ctx_parts.append(f"entity_id={entity_id}")
        if entity_name:
            ctx_parts.append(f"entity_name={entity_name}")
        if row_index is not None:
            ctx_parts.append(f"row_index={row_index}")
        log_ctx = " ".join(ctx_parts)

        parsed_json, err, runtime_meta, raw_response = call_llm(
            provider=provider,
            clients=clients,
            model_name=model_name,
            system_prompt=current_system_prompt,
            user_prompt=current_user_prompt,
            temperature=temperature,
            timeout_s=timeout_s,
            stage=stage,
            api_style=api_style,
            thinking_enabled=thinking_enabled,
            thinking_budget=thinking_budget,
            thinking_level=thinking_level,
            rag_enabled=rag_enabled,
            log_ctx=log_ctx,
            quota_limiter=quota_limiter,
        )
        
        # Save raw response
        attempt_filename = f"attempt_{attempt_idx:02d}.txt"
        raw_path = raw_llm_dir / attempt_filename
        try:
            raw_path.write_text(raw_response or "", encoding="utf-8")
            retry_meta["raw_paths"].append(str(raw_path.relative_to(out_dir)))
        except Exception as e:
            print(f"[WARN] Failed to save raw response for attempt {attempt_idx}: {e}")
        
        # If LLM call failed (transport/rate limit), return immediately
        if not parsed_json:
            return None, err, runtime_meta, raw_response, retry_meta
        
        # Diagnostic logging: Log parsed JSON structure before validation (especially for S2)
        if stage == 2:
            import sys
            entity_name = parsed_json.get("entity_name", "Unknown")
            anki_cards = parsed_json.get("anki_cards", None)
            cards_count = len(anki_cards) if isinstance(anki_cards, list) else 0
            has_anki_cards = "anki_cards" in parsed_json
            anki_cards_type = type(anki_cards).__name__ if anki_cards is not None else "None"
            
            # Log structure info (suppressed for cleaner terminal output)
            # Diagnostic info is logged to metrics file if needed
            
            # Warn if anki_cards is missing or empty
            if not has_anki_cards:
                print(
                    f"[WARN] Missing 'anki_cards' field in parsed JSON for entity: {entity_name}",
                    file=sys.stderr,
                    flush=True
                )
            elif cards_count == 0:
                print(
                    f"[WARN] 'anki_cards' is empty array for entity: {entity_name}",
                    file=sys.stderr,
                    flush=True
                )
            elif not isinstance(anki_cards, list):
                print(
                    f"[WARN] 'anki_cards' is not a list (type={anki_cards_type}) for entity: {entity_name}",
                    file=sys.stderr,
                    flush=True
                )
        
        # Try schema validation
        try:
            validated_json = validate_fn(parsed_json)
            
            # Success: log retry info if retry occurred
            if attempt_idx > 1:
                retry_meta["retry_occurred"] = True
                retry_msg = f"[WARN] Schema retry succeeded: stage={stage}, group_id={group_id}, " \
                           f"entity={entity_name or 'N/A'}, attempt_used={attempt_idx}/{MAX_SCHEMA_ATTEMPTS}"
                if progress_logger:
                    progress_logger.debug(retry_msg)
                else:
                    print(retry_msg)
            
            # Write retry log entry (even for successful first attempt, for audit)
            retry_log_entry = {
                "run_tag": run_tag,
                "stage": f"S{stage}",
                "arm": arm,
                "group_id": group_id,
                "entity_id": entity_id,
                "entity_name": entity_name,
                "row_index": row_index,
                "attempt_idx": attempt_idx,
                "success": True,
                "error_type": None,
                "error_summary": None,
                "raw_path": str(raw_path.relative_to(out_dir)),
            }
            try:
                with open(retry_log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(retry_log_entry, ensure_ascii=False) + "\n")
                retry_meta["retry_log_path"] = str(retry_log_path.relative_to(out_dir))
            except Exception as e:
                print(f"[WARN] Failed to write retry log: {e}")
            
            return validated_json, None, runtime_meta, raw_response, retry_meta
            
        except Exception as validation_error:
            last_error = validation_error
            error_type, error_summary = _classify_schema_error(validation_error)
            last_error_type = error_type
            last_error_summary = error_summary
            if _env_int("LLM_LOG_PHASES", 0) == 1:
                ctx_s = f" entity={entity_name}" if entity_name else ""
                print(
                    f"[LLM] schema_validation_failed stage={stage} attempt={attempt_idx}/{MAX_SCHEMA_ATTEMPTS} "
                    f"error_type={error_type} summary={error_summary}{ctx_s}",
                    flush=True,
                )
            retry_meta["errors"].append({
                "attempt": attempt_idx,
                "error_type": error_type,
                "error_summary": error_summary,
            })
            
            # Write retry log entry for failed attempt
            retry_log_entry = {
                "run_tag": run_tag,
                "stage": f"S{stage}",
                "arm": arm,
                "group_id": group_id,
                "entity_id": entity_id,
                "entity_name": entity_name,
                "row_index": row_index,
                "attempt_idx": attempt_idx,
                "success": False,
                "error_type": error_type,
                "error_summary": error_summary,
                "raw_path": str(raw_path.relative_to(out_dir)),
            }
            try:
                with open(retry_log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(retry_log_entry, ensure_ascii=False) + "\n")
                retry_meta["retry_log_path"] = str(retry_log_path.relative_to(out_dir))
            except Exception as e:
                print(f"[WARN] Failed to write retry log: {e}")
            
            # If this was the last attempt, fail
            if attempt_idx >= MAX_SCHEMA_ATTEMPTS:
                print(f"[ERROR] Schema validation failed after {MAX_SCHEMA_ATTEMPTS} attempts: "
                      f"stage={stage}, group_id={group_id}, entity={entity_name or 'N/A'}, "
                      f"error_type={error_type}, error_summary={error_summary[:100]}")
                return None, (
                    f"Schema validation failed after {MAX_SCHEMA_ATTEMPTS} attempts. "
                    f"Last error: {error_type} - {error_summary}. "
                    f"Raw responses saved to: {raw_llm_dir}"
                ), runtime_meta, raw_response, retry_meta
            
            # Prepare retry with standardized error feedback (B mode)
            retry_meta["retry_occurred"] = True
            error_feedback = f"{SCHEMA_RETRY_FEEDBACK_TEMPLATE}\n\nError details: {error_summary[:500]}"
            
            # Add specific guidance for card_count_mismatch errors
            if error_type == "card_count_mismatch":
                error_feedback += (
                    "\n\nCRITICAL: Return a SINGLE JSON OBJECT (not an array). "
                    "Format: { \"entity_name\": \"...\", \"anki_cards\": [...] } "
                    "DO NOT return: [{ \"entity_name\": \"...\", \"anki_cards\": [...] }]"
                )
            
            # Append error feedback to user prompt (preserve original structure)
            current_user_prompt = f"{user_prompt}\n\n---\n{error_feedback}"
            
            # Optionally add to system prompt (less intrusive)
            # current_system_prompt = f"{system_prompt}\n\nNote: Previous attempt failed validation. Ensure output matches schema exactly."
            
            # Continue to next attempt
    
    # Should not reach here, but handle gracefully
    return None, "Schema retry loop exhausted", runtime_meta, raw_response, retry_meta


# -------------------------
# Stage validation / fallbacks
# -------------------------
# -------------------------
TABLE_INFOGRAPHIC_CONSTRAINTS = (
    "Single-page educational infographic, white background, high contrast, minimal text (labels only), "
    "no watermark, clinically accurate."
)


def _normalize_entity_list(raw: Any) -> List[Dict[str, str]]:
    """Normalize Stage1 entity_list into a list of objects.

    Canonical object shape (minimum):
      {"entity_id": <str>, "entity_name": <str>}

    Backward compatibility:
      - If raw entries are strings, we deterministically derive entity_id using the
        stabilization rule (DERIVED:sha1(normalized_name)[:12]).
      - If raw entries are dicts, we accept keys:
          entity_id / id, entity_name / name
        and derive missing entity_id when needed.

    We de-duplicate by entity_id while preserving order.
    """
    if not isinstance(raw, list):
        return []

    out: List[Dict[str, str]] = []
    seen_ids: set[str] = set()

    def _derive(name: str) -> str:
        norm = re.sub(r"\s+", " ", str(name).strip().lower())
        h = hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]
        return f"DERIVED:{h}"

    for item in raw:
        if isinstance(item, dict):
            name = str(item.get("entity_name") or item.get("name") or "").strip()
            eid = str(item.get("entity_id") or item.get("id") or "").strip()
            if not name:
                continue
            if not eid:
                eid = _derive(name)
        else:
            name = str(item).strip()
            if not name:
                continue
            eid = _derive(name)

        if not eid:
            continue
        if eid in seen_ids:
            continue

        out.append({"entity_id": eid, "entity_name": name})
        seen_ids.add(eid)

    return out

def _normalize_master_table_cells(mt_markdown: str) -> str:
    """
    Normalize cell content in master table markdown:
    - Replace <br>, <br/> with "; "
    - Replace newline characters inside cells with "; "
    - Collapse repeated delimiters/spaces
    - Trim whitespace
    
    Preserves table structure (header, separator, rows).
    """
    if not mt_markdown:
        return mt_markdown
    
    lines = mt_markdown.splitlines()
    normalized_lines = []
    
    for line in lines:
        # Skip separator row (contains only dashes, colons, pipes, spaces)
        if re.match(r"^[\s\|\-:]+$", line):
            normalized_lines.append(line)
            continue
        
        # Process table rows (contain |)
        if "|" in line:
            # Split by | to get cells
            cells = line.split("|")
            normalized_cells = []
            
            for cell in cells:
                # Normalize cell content
                cell_norm = cell.strip()
                # Replace HTML line breaks
                cell_norm = re.sub(r"<br\s*/?>", "; ", cell_norm, flags=re.IGNORECASE)
                # Replace newlines
                cell_norm = cell_norm.replace("\n", "; ").replace("\r", "; ")
                # Collapse repeated delimiters/spaces
                cell_norm = re.sub(r"[;]\s*[;]+", ";", cell_norm)  # Multiple semicolons
                cell_norm = re.sub(r"\s+", " ", cell_norm)  # Multiple spaces
                cell_norm = cell_norm.strip()
                normalized_cells.append(cell_norm)
            
            # Rejoin cells with |
            normalized_lines.append("|".join(normalized_cells))
        else:
            # Non-table line, keep as-is
            normalized_lines.append(line)
    
    return "\n".join(normalized_lines)

def extract_entity_names_from_master_table(mt_markdown: str) -> List[str]:
    """Extract entity names from the first column of a Markdown table.
    
    Args:
        mt_markdown: Markdown table string with header, separator (---), and data rows.
    
    Returns:
        List of entity names in table order (first column of each data row).
        Returns empty list if parsing fails.
    """
    if not mt_markdown or not isinstance(mt_markdown, str):
        return []
    
    lines = [line.strip() for line in mt_markdown.strip().split("\n") if line.strip()]
    if len(lines) < 3:  # Need at least header, separator, and one data row
        return []
    
    # Find header row (first line with |)
    header_idx = None
    for i, line in enumerate(lines):
        if "|" in line:
            header_idx = i
            break
    
    if header_idx is None:
        return []
    
    # Skip separator row (should be at header_idx + 1)
    data_start = header_idx + 2
    if data_start >= len(lines):
        return []
    
    entity_names = []
    for line in lines[data_start:]:
        if "|" not in line:
            continue
        
        # Split by | and trim whitespace
        cells = [cell.strip() for cell in line.split("|")]
        # Remove empty cells at start/end (markdown tables often have leading/trailing |)
        cells = [c for c in cells if c]
        
        # Take first cell as entity_name (header-driven, no hardcoded column count)
        if len(cells) >= 1:
            entity_name = cells[0].strip()
            if entity_name:
                # Remove Markdown formatting (bold, italic, etc.) - comprehensive removal
                # Remove **text** -> text (bold)
                entity_name = re.sub(r'\*\*([^*]+)\*\*', r'\1', entity_name)
                # Remove *text* -> text (italic, but be careful not to remove asterisks that are part of content)
                entity_name = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', entity_name)
                # Remove __text__ -> text (bold alternative)
                entity_name = re.sub(r'__([^_]+)__', r'\1', entity_name)
                # Remove _text_ -> text (italic alternative)
                entity_name = re.sub(r'(?<!_)_([^_]+)_(?!_)', r'\1', entity_name)
                # Remove ~~text~~ -> text (strikethrough)
                entity_name = re.sub(r'~~([^~]+)~~', r'\1', entity_name)
                # Remove `text` -> text (inline code)
                entity_name = re.sub(r'`([^`]+)`', r'\1', entity_name)
                # Remove [text](url) -> text (links)
                entity_name = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', entity_name)
                # Remove HTML tags if any
                entity_name = re.sub(r'<[^>]+>', '', entity_name)
                # Normalize whitespace - more aggressive normalization
                entity_name = re.sub(r'\s+', ' ', entity_name).strip()
                # Remove leading/trailing punctuation that might be formatting artifacts
                entity_name = entity_name.strip('.,;:!?')
                if entity_name:  # Only add non-empty names
                    entity_names.append(entity_name)
    
    return entity_names

def _extract_entity_names_from_list(entity_list: Any) -> List[str]:
    """Extract and normalize entity names from entity_list for comparison.
    
    Args:
        entity_list: Raw entity_list from S1 (list of dicts or strings).
    
    Returns:
        List of normalized entity names (with markdown formatting removed, whitespace normalized).
    """
    if not isinstance(entity_list, list):
        return []
    
    names = []
    for item in entity_list:
        if isinstance(item, dict):
            name = str(item.get("entity_name") or item.get("name") or "").strip()
        else:
            name = str(item).strip()
        
        if name:
            # Remove Markdown formatting (same as in extract_entity_names_from_master_table)
            # Remove **text** -> text (bold)
            name = re.sub(r'\*\*([^*]+)\*\*', r'\1', name)
            # Remove *text* -> text (italic, but be careful not to remove asterisks that are part of content)
            name = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', name)
            # Remove __text__ -> text (bold alternative)
            name = re.sub(r'__([^_]+)__', r'\1', name)
            # Remove _text_ -> text (italic alternative)
            name = re.sub(r'(?<!_)_([^_]+)_(?!_)', r'\1', name)
            # Remove ~~text~~ -> text (strikethrough)
            name = re.sub(r'~~([^~]+)~~', r'\1', name)
            # Remove `text` -> text (inline code)
            name = re.sub(r'`([^`]+)`', r'\1', name)
            # Remove [text](url) -> text (links)
            name = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', name)
            # Remove HTML tags if any
            name = re.sub(r'<[^>]+>', '', name)
            # Normalize whitespace - more aggressive normalization
            name = re.sub(r'\s+', ' ', name).strip()
            # Remove leading/trailing punctuation that might be formatting artifacts
            name = name.strip('.,;:!?')
            if name:
                names.append(name)
    
    return names

def validate_stage1(stage1: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage1 validation for S1 Gate stabilization.

    Canonical requirement for downstream SSOT (stage1_struct__armX.jsonl) is minimal:
      - visual_type_category (enum)
      - master_table_markdown_kr (non-empty markdown)
      - entity_list (minItems >= 1)

    NOTE:
    - We intentionally do NOT hard-require optional fields like objective_summary,
      group_objectives, or infographic prompt fields at this stage. Those belong to
      later pipeline expansions and should not block S1 Gate determinism.
    """
    if not isinstance(stage1, dict):
        raise ValueError(f"Stage1 is not an object: {type(stage1).__name__}")

    s = dict(stage1)

    # --- visual_type_category ---
    raw_v = str(s.get("visual_type_category") or "").strip()
    if not raw_v:
        raise ValueError("Stage1 visual_type_category is empty")

    # Normalize common variants to canonical enum
    canon_map = {
        "anatomy map": "Anatomy_Map",
        "anatomy_map": "Anatomy_Map",
        "anatomy": "Anatomy_Map",
        "pathology pattern": "Pathology_Pattern",
        "pathology_pattern": "Pathology_Pattern",
        "pattern collection": "Pattern_Collection",
        "pattern_collection": "Pattern_Collection",
        "physiology process": "Physiology_Process",
        "physiology_process": "Physiology_Process",
        "equipment": "Equipment",
        "qc": "QC",
        "general": "General",
    }
    key = re.sub(r"\s+", " ", raw_v.strip().lower())
    key = key.replace("-", " ").replace("/", " ").replace("__", "_").strip()
    v = canon_map.get(key) or canon_map.get(key.replace(" ", "_")) or raw_v

    # Canonical visual_type_category enum (aligned with S1_Stage1_Struct_JSON_Schema_Canonical.md v1.3)
    # Removed unused categories: Comparison, Algorithm, Classification, Sign_Collection (v11)
    VISUAL_ENUM = {
        "Anatomy_Map",
        "Pathology_Pattern",
        "Pattern_Collection",
        "Physiology_Process",
        "Equipment",
        "QC",
        "General",
    }
    if v not in VISUAL_ENUM:
        raise ValueError(f"Stage1 visual_type_category not in enum. Got={raw_v}")

    s["visual_type_category"] = v

    # --- master_table_markdown_kr ---
    mt = str(s.get("master_table_markdown_kr") or "").strip()
    if not mt:
        raise ValueError("Stage1 master_table_markdown_kr is empty")

    # Minimal shape check: looks like a markdown table
    # (Do not over-tighten during stabilization.)
    if ("|" not in mt) or ("---" not in mt):
        raise ValueError("Stage1 master_table_markdown_kr does not look like a markdown table (missing '|' or '---')")

    # Normalize cell content: replace <br>, <br/>, and newlines with "; "
    mt = _normalize_master_table_cells(mt)
    
    s["master_table_markdown_kr"] = mt

    # --- entity_list ---
    ent_raw = s.get("entity_list")
    if not isinstance(ent_raw, list):
        raise ValueError("Stage1 entity_list is not a list")

    ent_objs = _normalize_entity_list(ent_raw)
    if len(ent_objs) < 1:
        raise ValueError("Stage1 entity_list is empty")

    s["entity_list"] = ent_objs

    # --- Optional: entity_clusters and infographic_clusters validation ---
    entity_clusters = s.get("entity_clusters")
    infographic_clusters = s.get("infographic_clusters")
    
    # Both present or both absent
    if (entity_clusters is None) != (infographic_clusters is None):
        raise ValueError(
            "Stage1 entity_clusters and infographic_clusters must both be present or both absent. "
            f"Got entity_clusters={entity_clusters is not None}, infographic_clusters={infographic_clusters is not None}"
        )
    
    if entity_clusters is not None:
        # Validate clustering structure
        if not isinstance(entity_clusters, list):
            raise ValueError(f"Stage1 entity_clusters must be an array, got {type(entity_clusters).__name__}")
        
        if not isinstance(infographic_clusters, list):
            raise ValueError(f"Stage1 infographic_clusters must be an array, got {type(infographic_clusters).__name__}")
        
        # CRITICAL: entity_clusters and infographic_clusters must have same length
        # Auto-repair: if mismatch, try to fix by adding missing infographic clusters or removing extra entity clusters
        if len(entity_clusters) != len(infographic_clusters):
            if _env_int("S1_CLUSTER_LENGTH_REPAIR", 1) == 1:
                # Auto-repair: align lengths
                entity_len = len(entity_clusters)
                infographic_len = len(infographic_clusters)
                
                if entity_len > infographic_len:
                    # Missing infographic clusters: create default ones for missing cluster_ids
                    print(
                        f"[WARN] Stage1 cluster length mismatch: entity_clusters={entity_len}, infographic_clusters={infographic_len}. "
                        f"Auto-repair: creating {entity_len - infographic_len} missing infographic cluster(s).",
                        file=sys.stderr,
                        flush=True,
                    )
                    # Get cluster_ids from entity_clusters that don't have matching infographic
                    existing_infographic_ids = {inf.get("cluster_id") for inf in infographic_clusters if inf.get("cluster_id")}
                    for i, entity_cluster in enumerate(entity_clusters):
                        cluster_id = entity_cluster.get("cluster_id")
                        if cluster_id and cluster_id not in existing_infographic_ids:
                            # Create default infographic cluster
                            entity_names = entity_cluster.get("entity_names", [])
                            cluster_theme = entity_cluster.get("cluster_theme", "")
                            default_infographic = {
                                "cluster_id": cluster_id,
                                "infographic_style": str(s.get("visual_type_category", "General")).strip(),
                                "infographic_keywords_en": ", ".join([str(n).strip()[:20] for n in entity_names[:5]]),
                                "infographic_prompt_en": (
                                    f"Create a single educational infographic diagram for: {cluster_theme or 'related entities'}. "
                                    f"Entities: {', '.join([str(n).strip() for n in entity_names[:8]])}. "
                                    f"Style: clean, minimal text, lecture-slide format."
                                ),
                            }
                            infographic_clusters.append(default_infographic)
                            print(
                                f"[WARN] Created default infographic cluster for {cluster_id}",
                                file=sys.stderr,
                                flush=True,
                            )
                elif infographic_len > entity_len:
                    # Extra infographic clusters: remove ones without matching entity cluster
                    print(
                        f"[WARN] Stage1 cluster length mismatch: entity_clusters={entity_len}, infographic_clusters={infographic_len}. "
                        f"Auto-repair: removing {infographic_len - entity_len} extra infographic cluster(s).",
                        file=sys.stderr,
                        flush=True,
                    )
                    entity_cluster_ids = {ec.get("cluster_id") for ec in entity_clusters if ec.get("cluster_id")}
                    infographic_clusters[:] = [
                        inf for inf in infographic_clusters
                        if inf.get("cluster_id") in entity_cluster_ids
                    ]
                
                # Re-validate after repair
                if len(entity_clusters) != len(infographic_clusters):
                    raise ValueError(
                        f"Stage1 cluster length mismatch after auto-repair: "
                        f"entity_clusters={len(entity_clusters)}, infographic_clusters={len(infographic_clusters)}"
                    )
            else:
                # No repair: fail-fast
                raise ValueError(
                    f"Stage1 entity_clusters and infographic_clusters must have same length "
                    f"(got {len(entity_clusters)} vs {len(infographic_clusters)}). "
                    f"Enable S1_CLUSTER_LENGTH_REPAIR=1 to auto-repair."
                )
        
        if len(entity_clusters) < 1 or len(entity_clusters) > 4:
            raise ValueError(
                f"Stage1 entity_clusters must have 1-4 clusters (got {len(entity_clusters)})"
            )
        
        # Validate each cluster
        all_entity_names = set()
        duplicate_cluster_entities = set()
        entity_list_names = set()
        for entity in ent_objs:
            if isinstance(entity, dict):
                name = entity.get("entity_name") or entity.get("name", "")
            else:
                name = str(entity)
            if name:
                entity_list_names.add(name.strip())
        
        for i, cluster in enumerate(entity_clusters):
            if not isinstance(cluster, dict):
                raise ValueError(f"Stage1 entity_clusters[{i}] must be an object, got {type(cluster).__name__}")
            
            cluster_id = cluster.get("cluster_id")
            entity_names = cluster.get("entity_names", [])
            cluster_theme = cluster.get("cluster_theme", "")
            
            if not cluster_id:
                raise ValueError(f"Stage1 entity_clusters[{i}] missing cluster_id")
            
            if not isinstance(entity_names, list):
                raise ValueError(f"Stage1 entity_clusters[{i}].entity_names must be an array, got {type(entity_names).__name__}")
            
            if not entity_names:
                raise ValueError(f"Stage1 entity_clusters[{i}].entity_names is empty")
            
            if len(entity_names) < 3 or len(entity_names) > 8:
                raise ValueError(
                    f"Stage1 entity_clusters[{i}] ({cluster_id}) must have 3-8 entities (got {len(entity_names)})"
                )
            
            if not cluster_theme:
                raise ValueError(f"Stage1 entity_clusters[{i}] ({cluster_id}) missing cluster_theme")
            
            # Check for duplicates
            for name in entity_names:
                name_stripped = str(name).strip()
                if name_stripped in all_entity_names:
                    # Allow duplicates across clusters (infographic-only); warn and continue.
                    duplicate_cluster_entities.add(name_stripped)
                    continue
                all_entity_names.add(name_stripped)
            
            # Validate corresponding infographic cluster
            # Try to find by cluster_id first (more robust than index-based)
            infographic = None
            for inf in infographic_clusters:
                if isinstance(inf, dict) and inf.get("cluster_id") == cluster_id:
                    infographic = inf
                    break
            
            # If not found by cluster_id, try index-based (for backward compatibility)
            if infographic is None and i < len(infographic_clusters):
                infographic = infographic_clusters[i]
                if isinstance(infographic, dict):
                    infographic_cluster_id = infographic.get("cluster_id")
                    if infographic_cluster_id != cluster_id:
                        # Auto-repair: fix cluster_id mismatch
                        if _env_int("S1_CLUSTER_ID_REPAIR", 1) == 1:
                            print(
                                f"[WARN] Stage1 infographic_clusters[{i}].cluster_id mismatch "
                                f"(expected {cluster_id}, got {infographic_cluster_id}). Auto-repair: fixing cluster_id.",
                                file=sys.stderr,
                                flush=True,
                            )
                            infographic["cluster_id"] = cluster_id
                        else:
                            raise ValueError(
                                f"Stage1 infographic_clusters[{i}].cluster_id mismatch "
                                f"(expected {cluster_id}, got {infographic_cluster_id}). "
                                f"Enable S1_CLUSTER_ID_REPAIR=1 to auto-repair."
                            )
            
            if infographic is None:
                raise ValueError(
                    f"Stage1 infographic_clusters missing entry for cluster_id={cluster_id} "
                    f"(entity_clusters[{i}])"
                )
            
            if not isinstance(infographic, dict):
                raise ValueError(f"Stage1 infographic_clusters entry for {cluster_id} must be an object, got {type(infographic).__name__}")
            
            infographic_prompt = infographic.get("infographic_prompt_en")
            if not infographic_prompt or not str(infographic_prompt).strip():
                raise ValueError(f"Stage1 infographic_clusters[{i}] ({cluster_id}) missing infographic_prompt_en")

            # Optional: infographic_hint_v2 (structured constraints). If present, must be an object.
            infographic_hint_v2 = infographic.get("infographic_hint_v2")
            if infographic_hint_v2 is not None and not isinstance(infographic_hint_v2, dict):
                raise ValueError(
                    f"Stage1 infographic_clusters[{i}] ({cluster_id}) infographic_hint_v2 must be an object, "
                    f"got {type(infographic_hint_v2).__name__}"
                )
        
        if duplicate_cluster_entities:
            import sys as _sys
            dup_preview = ", ".join(sorted(duplicate_cluster_entities)[:20])
            more = "" if len(duplicate_cluster_entities) <= 20 else f" (+{len(duplicate_cluster_entities) - 20} more)"
            print(
                f"[WARN] Stage1 entity_clusters contains duplicated entity names across clusters: {dup_preview}{more}",
                file=_sys.stderr,
                flush=True,
            )

        # Validate all entities are covered
        if all_entity_names != entity_list_names:
            missing = entity_list_names - all_entity_names
            extra = all_entity_names - entity_list_names

            # Best-effort repair: some models forget to place “general” entities into clusters.
            # This keeps S1 from hard-failing while preserving the invariant that every entity in
            # entity_list appears in exactly one cluster.
            if _env_int("S1_CLUSTER_COVERAGE_REPAIR", 1) == 1:
                # 1) Remove extras from clusters
                if extra:
                    for cluster in entity_clusters:
                        names = cluster.get("entity_names") or []
                        if isinstance(names, list):
                            cluster["entity_names"] = [n for n in names if str(n).strip() not in extra]

                # 2) Add missing into clusters with spare capacity (validator max: 8)
                if missing:
                    clusters_by_size = sorted(
                        entity_clusters,
                        key=lambda c: len(c.get("entity_names") or []) if isinstance(c, dict) else 9999,
                    )
                    for name in sorted(missing):
                        n = str(name).strip()
                        if not n:
                            continue
                        placed = False
                        for cluster in clusters_by_size:
                            names = cluster.get("entity_names") or []
                            if not isinstance(names, list):
                                continue
                            if len(names) >= 8:
                                continue
                            if n in [str(x).strip() for x in names]:
                                placed = True
                                break
                            names.append(n)
                            cluster["entity_names"] = names
                            placed = True
                            break
                        if not placed:
                            break

                # 3) Ensure each cluster still has at least 3 entities after extra-removal
                for cluster in entity_clusters:
                    names = cluster.get("entity_names") or []
                    if not isinstance(names, list):
                        continue
                    while len(names) < 3:
                        donor = None
                        donor_names = None
                        for c2 in sorted(
                            entity_clusters,
                            key=lambda c: len(c.get("entity_names") or []) if isinstance(c, dict) else 0,
                            reverse=True,
                        ):
                            if c2 is cluster:
                                continue
                            cand = c2.get("entity_names") or []
                            if isinstance(cand, list) and len(cand) > 3:
                                donor = c2
                                donor_names = cand
                                break
                        if donor is None or donor_names is None:
                            break
                        moved = donor_names.pop()
                        names.append(moved)
                        donor["entity_names"] = donor_names
                        cluster["entity_names"] = names

                # 4) Recompute coverage and enforce invariant
                all_entity_names = set()
                duplicate_cluster_entities_after_repair = set()
                for cluster in entity_clusters:
                    names = cluster.get("entity_names") or []
                    if not isinstance(names, list):
                        continue
                    for n in names:
                        ns = str(n).strip()
                        if not ns:
                            continue
                        if ns in all_entity_names:
                            # Allow duplicates across clusters (infographic-only); warn and continue.
                            duplicate_cluster_entities_after_repair.add(ns)
                            continue
                        all_entity_names.add(ns)

                if duplicate_cluster_entities_after_repair:
                    import sys as _sys
                    dup_preview = ", ".join(sorted(duplicate_cluster_entities_after_repair)[:20])
                    more = "" if len(duplicate_cluster_entities_after_repair) <= 20 else f" (+{len(duplicate_cluster_entities_after_repair) - 20} more)"
                    print(
                        f"[WARN] Stage1 entity_clusters contains duplicated entity names across clusters (after repair): {dup_preview}{more}",
                        file=_sys.stderr,
                        flush=True,
                    )

                if all_entity_names != entity_list_names:
                    missing2 = entity_list_names - all_entity_names
                    extra2 = all_entity_names - entity_list_names
                    error_parts = []
                    if missing2:
                        error_parts.append(f"missing={sorted(missing2)}")
                    if extra2:
                        error_parts.append(f"extra={sorted(extra2)}")
                    raise ValueError(
                        f"Stage1 Entity coverage mismatch: {', '.join(error_parts)}. "
                        f"All entities in entity_list must appear in exactly one cluster."
                    )
            else:
                error_parts = []
                if missing:
                    error_parts.append(f"missing={sorted(missing)}")
                if extra:
                    error_parts.append(f"extra={sorted(extra)}")
                raise ValueError(
                    f"Stage1 Entity coverage mismatch: {', '.join(error_parts)}. "
                    f"All entities in entity_list must appear in exactly one cluster."
                )
    
    # Keep any extra keys as-is (additionalProperties allowed).
    return s

def _derive_entity_id_list(entity_list: List[str]) -> List[str]:
    """
    Deterministic derived IDs for Stage1/Stage2 linkage during stabilization.

    Rule (canonical in stabilization handoff): sha1(normalized_entity)[:12] with DERIVED: prefix.
    """
    ids: List[str] = []
    for e in (entity_list or []):
        norm = re.sub(r"\s+", " ", str(e).strip().lower())
        h = hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]
        ids.append(f"DERIVED:{h}")
    return ids


def _safe_fname(s: str) -> str:
    s = re.sub(r"[^0-9A-Za-z._-]+", "_", str(s or "").strip())
    return s[:120] if s else "NA"


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text or "", encoding="utf-8")


def _write_stage_debug(
    *,
    debug_dir: Path,
    stage: int,
    group_id: str,
    arm: str,
    system_prompt: str,
    user_prompt: str,
    raw_response: Optional[str],
    entity_name: Optional[str] = None,
    entity_id: Optional[str] = None,
) -> None:
    """
    Emit debug_raw artifacts for gating / forensic debugging.

    Filename policy:
      - Always includes group_id and arm.
      - For Stage2+ entity-specific artifacts, prefer entity_id in filename to avoid
        Unicode/slug instability (e.g., Korean-only names -> empty slug).
      - If entity_id is not provided, falls back to a safe filename from entity_name.
    """
    debug_dir.mkdir(parents=True, exist_ok=True)

    ent_part = ""
    if entity_id:
        ent_part = f"__eid_{_safe_fname(entity_id)}"
        if entity_name:
            ent_part += f"__entity_{_safe_fname(entity_name)}"
    elif entity_name:
        ent_part = f"__entity_{_safe_fname(entity_name)}"

    prefix = f"stage{stage}__group_{_safe_fname(group_id)}__arm_{_safe_fname(arm)}{ent_part}"

    _write_text(debug_dir / f"{prefix}__system_prompt.txt", system_prompt)
    _write_text(debug_dir / f"{prefix}__user_prompt.txt", user_prompt)
    if raw_response is not None:
        _write_text(debug_dir / f"{prefix}__raw_response.txt", raw_response)


def write_s2_results_jsonl(
    entities: Optional[List[Dict[str, Any]]],
    fh: Optional[TextIO],
    *,
    run_tag: str,
    arm: str,
    group_path: str,
) -> None:
    """Emit canonical S2 results JSONL records for each entity."""
    if fh is None or not entities:
        return

    for ent in entities:
        if not isinstance(ent, dict):
            continue

        group_id = str(ent.get("group_id") or "").strip()
        entity_id = str(ent.get("entity_id") or "").strip()
        entity_name = str(ent.get("entity_name") or "").strip()
        if not (group_id and entity_id and entity_name):
            continue

        cards = ent.get("anki_cards") or []
        if not isinstance(cards, list):
            cards = []

        card_count = len(cards)
        record = {
            "schema_version": S2_RESULTS_SCHEMA_VERSION,
            "run_tag": run_tag,
            "arm": arm,
            "group_id": group_id,
            "group_path": str(ent.get("group_path") or group_path or "").strip(),
            "entity_id": entity_id,
            "entity_name": entity_name,
            "cards_for_entity_exact": safe_int(ent.get("cards_for_entity_exact"), card_count) or card_count,
            "anki_cards": cards,
            "integrity": {"card_count": card_count},
        }
        
        # Include runtime metadata (tokens, latency) if present in entity
        if "metadata" in ent and isinstance(ent["metadata"], dict):
            record["metadata"] = ent["metadata"]

        fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    fh.flush()
def validate_stage2(stage2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage2 validation for S2 output schema (v3.2).
    
    Validates and normalizes:
    - Basic fields (group_id, entity_id, entity_name)
    - Card structure (card_role, card_type, front, back, tags)
    - Image hint compliance (Q1 required, Q2 required)
    - Exactly 2 cards per entity (Q1/Q2)
    - MCQ format (Q2 must have 5 options + correct_index)
    - Deictic image reference prohibition (Q2)
    """
    s_in = dict(stage2 or {})

    out: Dict[str, Any] = {}
    # Optional strictness: require image_hint_v2 to be present (useful during rollout/experiments).
    # Default OFF for backward compatibility.
    require_image_hint_v2 = str(os.getenv("S2_REQUIRE_IMAGE_HINT_V2", "")).strip().lower() in ("1", "true", "yes", "on")
    if "group_id" in s_in and s_in["group_id"] is not None:
        out["group_id"] = str(s_in["group_id"])
    if "entity_id" in s_in and s_in.get("entity_id") is not None:
        _eid = str(s_in.get("entity_id") or "").strip()
        if _eid:
            out["entity_id"] = _eid
    out["entity_name"] = str(s_in.get("entity_name") or "Unnamed entity").strip()

    cards = s_in.get("anki_cards") or []
    if not isinstance(cards, list):
        cards = []
    
    # P0: Enforce exactly 2 cards per entity (2-card policy)
    if len(cards) != 2:
        raise ValueError(
            f"S2 validation FAIL: Expected exactly 2 cards per entity, got {len(cards)}. "
            f"Entity: {out.get('entity_name', 'Unknown')}"
        )
    
    norm_cards: List[Dict[str, Any]] = []
    for idx, c in enumerate(cards):
        if not isinstance(c, dict):
            continue
        
        # P0: Extract and validate card_role - FAIL if missing
        card_role = str(c.get("card_role") or "").strip().upper()
        if not card_role or card_role not in ("Q1", "Q2"):
            # Try to infer from index if not provided (for backward compatibility)
            if len(cards) == 2:
                card_role = f"Q{idx + 1}"
            else:
                raise ValueError(
                    f"S2 validation FAIL: card_role missing or invalid for card {idx + 1}. "
                    f"Entity: {out.get('entity_name', 'Unknown')}. "
                    f"Expected Q1 or Q2, got: {c.get('card_role')}"
                )
        
        # P0: Check for deictic image references in Q2
        if card_role == "Q2":
            front_text = str(c.get("front") or "").lower()
            back_text = str(c.get("back") or "").lower()
            # More specific patterns that clearly reference an image being shown
            deictic_patterns = [
                "this image", "shown here", "above figure", "this figure", "the image shown",
                "이 영상에서", "위 ct에서", "그림에서 보이는", "이미지에서 보이는", 
                "shown in the image", "in this image", "on the image", "from the image",
                "위 그림", "이 그림", "보이는 영상", "보이는 이미지"
            ]
            # Check for patterns in context (avoid false positives)
            for pattern in deictic_patterns:
                if pattern in front_text or pattern in back_text:
                    raise ValueError(
                        f"S2 validation FAIL: Deictic image reference found in {card_role}. "
                        f"Entity: {out.get('entity_name', 'Unknown')}. "
                        f"Pattern: '{pattern}'. Q2 must not reference images. "
                        f"Text must be solvable without an image."
                    )
        
        # Extract image_hint
        image_hint_raw = c.get("image_hint")
        image_hint = None
        if image_hint_raw is not None:
            if isinstance(image_hint_raw, dict) and image_hint_raw:
                # Normalize image_hint structure
                image_hint = {
                    "modality_preferred": str(image_hint_raw.get("modality_preferred") or "Other").strip(),
                    "anatomy_region": str(image_hint_raw.get("anatomy_region") or "").strip(),
                    "key_findings_keywords": (
                        image_hint_raw.get("key_findings_keywords") or []
                        if isinstance(image_hint_raw.get("key_findings_keywords"), list)
                        else []
                    ),
                    "view_or_sequence": str(image_hint_raw.get("view_or_sequence") or "").strip(),
                    "exam_focus": str(image_hint_raw.get("exam_focus") or "").strip(),
                }
                # Remove empty optional fields
                if not image_hint["view_or_sequence"]:
                    image_hint.pop("view_or_sequence", None)
                if not image_hint["exam_focus"]:
                    image_hint.pop("exam_focus", None)

        # Extract image_hint_v2 (optional; preserve structured constraints for downstream S3/S4)
        image_hint_v2_raw = c.get("image_hint_v2")
        image_hint_v2 = None
        if image_hint_v2_raw is not None:
            if isinstance(image_hint_v2_raw, dict) and image_hint_v2_raw:
                # Preserve as-is (do not over-normalize during stabilization)
                image_hint_v2 = image_hint_v2_raw

        # Optional enforcement (experiment): require image_hint_v2 on Q1/Q2
        if require_image_hint_v2 and card_role in ("Q1", "Q2"):
            if not image_hint_v2:
                raise ValueError(
                    f"S2 validation FAIL: {card_role} requires image_hint_v2 (S2_REQUIRE_IMAGE_HINT_V2=1) but it is missing. "
                    f"Entity: {out.get('entity_name', 'Unknown')}"
                )
        
        # Validate image_hint compliance
        if card_role == "Q1":
            if not image_hint:
                raise ValueError(
                    f"S2 validation FAIL: Q1 requires image_hint but it is missing. "
                    f"Entity: {out.get('entity_name', 'Unknown')}"
                )
        elif card_role == "Q2":
            if not image_hint:
                raise ValueError(
                    f"S2 validation FAIL: Q2 requires image_hint but it is missing. "
                    f"Entity: {out.get('entity_name', 'Unknown')}"
                )
        
        # P0: Validate MCQ format for Q2
        card_type = str(c.get("card_type") or "Basic").strip()
        # Only validate MCQ format if card_type is actually MCQ
        validated_options = None
        validated_correct_index = None
        if card_role == "Q2" and card_type.upper() in ("MCQ", "MCQ_VIGNETTE"):
            # Check for options array with exactly 5 items
            options = c.get("options")
            correct_index = c.get("correct_index")
            
            # P0: Q2 MCQ must have structured options array + correct_index
            # This is now required in the prompt schema
            if options is None:
                raise ValueError(
                    f"S2 validation FAIL: {card_role} MCQ must have 'options' array. "
                    f"Entity: {out.get('entity_name', 'Unknown')}, Card type: {card_type}"
                )
            
            if not isinstance(options, list):
                raise ValueError(
                    f"S2 validation FAIL: {card_role} MCQ 'options' must be an array. "
                    f"Entity: {out.get('entity_name', 'Unknown')}, Card type: {card_type}"
                )
            
            if len(options) != 5:
                raise ValueError(
                    f"S2 validation FAIL: {card_role} MCQ must have exactly 5 options, got {len(options)}. "
                    f"Entity: {out.get('entity_name', 'Unknown')}"
                )
            
            if correct_index is None:
                raise ValueError(
                    f"S2 validation FAIL: {card_role} MCQ must have 'correct_index'. "
                    f"Entity: {out.get('entity_name', 'Unknown')}"
                )
            
            correct_idx = safe_int(correct_index, -1)
            if correct_idx < 0 or correct_idx >= 5:
                raise ValueError(
                    f"S2 validation FAIL: {card_role} MCQ correct_index must be 0-4, got {correct_idx}. "
                    f"Entity: {out.get('entity_name', 'Unknown')}"
                )
            
            # Store validated values to ensure they are preserved (validation passed, so use these)
            # CRITICAL: These values MUST be preserved in the output card
            validated_options = list(options) if isinstance(options, list) else options  # Make a copy to avoid reference issues
            validated_correct_index = correct_index
        # Note: If Q2 is not MCQ type, we don't enforce options (may be Basic or other format)
        
        # Normalize tags
        tags_raw = c.get("tags")
        if isinstance(tags_raw, list):
            tags = [str(t).strip() for t in tags_raw if t]
        elif isinstance(tags_raw, str):
            tags = [t.strip() for t in tags_raw.split() if t.strip()]
        else:
            tags = []
        
        # Build base card dict
        cc = {
            "card_role": card_role,
            "card_type": card_type,
            "front": str(c.get("front") or "").strip(),
            "back": str(c.get("back") or "").strip(),
            "tags": tags,
        }
        
        # Add MCQ-specific fields: ALWAYS preserve options and correct_index for MCQ cards
        if card_type.upper() in ("MCQ", "MCQ_VIGNETTE"):
            # CRITICAL: For MCQ cards, options and correct_index MUST be present
            # Priority 1: Use validated values (from validation step) - these are guaranteed to be valid
            if validated_options is not None:
                cc["options"] = validated_options
            # Priority 2: Use original card's options if available (fallback for edge cases)
            elif "options" in c:
                original_options = c.get("options")
                if original_options is not None:
                    cc["options"] = original_options
            
            # Same for correct_index
            if validated_correct_index is not None:
                cc["correct_index"] = validated_correct_index
            elif "correct_index" in c:
                original_correct_index = c.get("correct_index")
                if original_correct_index is not None:
                    cc["correct_index"] = original_correct_index
            
            # CRITICAL: Final safety check - if options still missing, raise error
            # This should never happen if validation passed, but we check anyway
            if "options" not in cc:
                # Last resort: try to get from original card one more time
                if "options" in c and c.get("options") is not None:
                    cc["options"] = c.get("options")
                else:
                    # This is a critical error - validation should have caught this
                    raise ValueError(
                        f"S2 validation FAIL: {card_role} MCQ card missing 'options' after validation. "
                        f"Entity: {out.get('entity_name', 'Unknown')}, Card type: {card_type}. "
                        f"validated_options={validated_options}, original_options={c.get('options')}"
                    )
            
            if "correct_index" not in cc:
                if "correct_index" in c and c.get("correct_index") is not None:
                    cc["correct_index"] = c.get("correct_index")
                else:
                    raise ValueError(
                        f"S2 validation FAIL: {card_role} MCQ card missing 'correct_index' after validation. "
                        f"Entity: {out.get('entity_name', 'Unknown')}. "
                        f"validated_correct_index={validated_correct_index}, original_correct_index={c.get('correct_index')}"
                    )
        
        # Add image_hint if present
        if image_hint:
            cc["image_hint"] = image_hint

        # Add image_hint_v2 if present
        if image_hint_v2:
            cc["image_hint_v2"] = image_hint_v2
        
        if not (cc["front"] and cc["back"]):
            continue
        norm_cards.append(cc)
    
    # Final check: must have exactly 2 cards after normalization
    if len(norm_cards) != 2:
        raise ValueError(
            f"S2 validation FAIL: After normalization, expected 2 cards, got {len(norm_cards)}. "
            f"Entity: {out.get('entity_name', 'Unknown')}"
        )
    
    # Verify Q1/Q2 are both present
    roles_found = {c["card_role"] for c in norm_cards}
    expected_roles = {"Q1", "Q2"}
    if roles_found != expected_roles:
        missing = expected_roles - roles_found
        raise ValueError(
            f"S2 validation FAIL: Missing card roles: {sorted(missing)}. "
            f"Entity: {out.get('entity_name', 'Unknown')}. "
            f"Found: {sorted(roles_found)}"
        )

    out["anki_cards"] = norm_cards
    return out


# -------------------------
# Local S2 target model (to avoid coupling)
# -------------------------
@dataclass(frozen=True)
class _S2Target:
    entity_id: str
    entity_name: str
    cards_for_entity_exact: int


# -------------------------
# Entity Type Detection for S2 Prompt Adaptation
# -------------------------
def detect_entity_type_for_s2(
    entity_name: str,
    visual_type_category: str,
    master_table_row: Optional[Dict] = None
) -> str:
    """
    Detect entity type for S2 prompt adaptation.
    
    Returns: "disease", "sign", "overview", "qc", "equipment", "comparison"
    
    This classification is used to adapt Q1/Q2 prompts for non-diagnostic entities
    (signs, overviews, QC, Equipment, comparison) that don't fit the standard diagnostic reasoning pattern.
    """
    name_lower = str(entity_name).lower()
    
    # Comparison/Differential entities: "vs", "versus", "and", "or" patterns
    # Check for comparison keywords with word boundaries to avoid false positives
    comparison_keywords = [" vs ", " versus ", " vs. ", " and ", " or "]
    if any(kw in name_lower for kw in comparison_keywords):
        return "comparison"
    
    # Sign entities: imaging patterns/signs
    sign_keywords = ["sign", "pattern", "finding", "소견", "징후"]
    if any(kw in name_lower for kw in sign_keywords):
        return "sign"
    
    # Overview entities: conceptual summaries
    overview_keywords = ["overview", "general", "총론", "개요", "원칙", "개념"]
    if any(kw in name_lower for kw in overview_keywords):
        return "overview"
    
    # QC/Equipment: from visual_type_category
    if visual_type_category == "QC":
        return "qc"
    if visual_type_category == "Equipment":
        return "equipment"
    
    # Default: disease/diagnosis entity
    return "disease"


def _classify_error_type(error: Any) -> str:
    """Classify error type from error message/exception."""
    error_str = str(error).lower()
    
    if "schema" in error_str or "validation" in error_str:
        return "schema_validation"
    if "timeout" in error_str:
        return "timeout"
    if "llm" in error_str or "api" in error_str or "quota" in error_str:
        return "llm_error"
    
    return "other"


# -------------------------
# Entity-level processing function
# -------------------------
def process_single_entity(
    *,
    entity_target: _S2Target,
    group_id: str,
    group_path: str,
    s1_json: Dict[str, Any],
    ent2id: Dict[str, str],
    provider: str,
    clients: ProviderClients,
    arm: str,
    arm_config: Dict[str, Any],
    bundle: Dict[str, Any],
    run_tag: str,
    mode: str,
    model_stage2: str,
    temp_stage2: float,
    timeout_s: int,
    thinking_enabled: bool,
    thinking_budget: Optional[int],
    thinking_level: Optional[str],
    model_is_gemini3: bool,
    rag_enabled: bool,
    out_dir: Path,
    debug_dir: Path,
    quota_s2: Optional[Any],
    P_S2_SYS: str,
    P_S2_USER_T: str,
    output_variant: str = "baseline",
    repair_plan: Optional[Dict[str, Any]] = None,
    group_key: str = "",
    progress_logger: Optional[Any] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Dict[str, Any]]:
    """
    Process a single entity for S2 stage.
    
    Returns:
        (s2_json, error_msg, runtime_meta)
        - s2_json: Validated S2 JSON output, or None if failed
        - error_msg: Error message if failed, or None if succeeded
        - runtime_meta: Runtime metadata dict (includes rt_s2 with RAG info)
    
    Note: This function is designed to be called from ThreadPoolExecutor.
    All exceptions are caught and returned as error messages to prevent
    thread pool from hanging on unhandled exceptions.
    """
    ent_name = str(entity_target.entity_name).strip()
    ent_id = str(getattr(entity_target, 'entity_id', '') or '').strip()
    log_entity = _env_int("S2_ENTITY_LOG", 1) == 1
    t0_entity = time.perf_counter()
    tid = None
    try:
        tid = threading.get_ident()
    except Exception:
        tid = None
    
    try:
        if log_entity:
            if progress_logger:
                progress_logger.debug(f"[S2][ENTITY] start entity={ent_name[:80]} entity_id={ent_id or 'NA'} tid={tid}")
            else:
                print(
                    f"  [S2][ENTITY] start entity={ent_name[:80]} entity_id={ent_id or 'NA'} tid={tid}",
                    flush=True,
                )
        if not ent_name:
            return None, "Empty entity name", {}
        
        expected_n = int(entity_target.cards_for_entity_exact)
        
        # Detect entity type for prompt adaptation
        entity_type = detect_entity_type_for_s2(
            entity_name=ent_name,
            visual_type_category=s1_json.get('visual_type_category', 'General')
        )
        
        entity_context = (
            f"Group Path: {group_path}\n"
            f"Visual Type: {s1_json.get('visual_type_category', 'General')}\n"
            f"Entity Type: {entity_type}\n"
        )
        
        s2_user = safe_prompt_format(
            P_S2_USER_T,
            # canonical + alias 둘 다 제공 (템플릿이 뭐를 쓰든 안전)
            master_table=s1_json["master_table_markdown_kr"],
            master_table_md=s1_json["master_table_markdown_kr"],
            entity_name=ent_name,
            entity_context=entity_context,
            visual_type=s1_json.get("visual_type_category", "General"),
            cards_per_entity=expected_n,               # 호환용
            cards_for_entity_exact=expected_n,         # canonical
            card_type_quota_lines="- Basic_QA: 1\n- MCQ_Vignette: 1",
        )

        # Option C (PR2): append repair-plan instructions (no prompt-template edits)
        s2_user = maybe_append_repair_instructions(
            s2_user,
            output_variant=output_variant,
            repair_plan=repair_plan,
            stage="S2",
            group_id=group_id,
            group_key=str(group_key or "").strip(),
            entity_name=ent_name,
        )
        
        ent_id_final = ent_id or ent2id.get(ent_name) or _derive_entity_id_list([ent_name])[0]
        
        s2_json, err2, rt_s2, raw_s2, retry_meta_s2 = call_llm_with_schema_retry(
            provider=provider,
            clients=clients,
            model_name=model_stage2,
            system_prompt=P_S2_SYS,
            user_prompt=s2_user,
            temperature=temp_stage2,
            timeout_s=timeout_s,
            stage=2,
            api_style=str(arm_config.get("api_style") or "chat"),
            thinking_enabled=thinking_enabled,
            thinking_budget=thinking_budget,
            thinking_level=thinking_level if model_is_gemini3 else None,
            rag_enabled=rag_enabled,
            validate_fn=validate_stage2,
            run_tag=run_tag,
            arm=arm,
            group_id=group_id,
            out_dir=out_dir,
            entity_id=ent_id_final,
            entity_name=ent_name,
            row_index=None,
            quota_limiter=quota_s2,
            progress_logger=progress_logger,
        )
        
        _write_stage_debug(
            debug_dir=debug_dir,
            stage=2,
            group_id=group_id,
            arm=arm,
            system_prompt=P_S2_SYS,
            user_prompt=s2_user,
            raw_response=raw_s2,
            entity_name=ent_name,
            entity_id=ent_id_final,
        )
        
        if not s2_json:
            error_detail = err2 or "Unknown error"
            if retry_meta_s2.get("retry_occurred"):
                error_detail += f" (schema retry occurred: {retry_meta_s2.get('attempt_count')}/{MAX_SCHEMA_ATTEMPTS} attempts)"
            # In S0, underfill/empty is unacceptable; fail fast.
            if str(mode).upper() == "S0":
                raise RuntimeError(f"S0 Stage2 failed: entity={ent_name} error={error_detail}")
            if log_entity:
                elapsed = time.perf_counter() - t0_entity
                if progress_logger:
                    progress_logger.debug(f"[S2][ENTITY] end entity={ent_name[:80]} ok=0 elapsed={elapsed:.2f}s err={error_detail[:200]}")
                else:
                    print(
                        f"  [S2][ENTITY] end entity={ent_name[:80]} ok=0 elapsed={elapsed:.2f}s err={error_detail[:200]}",
                        flush=True,
                    )
            return None, error_detail, dict(rt_s2 or {})
        
        # s2_json is already validated by call_llm_with_schema_retry
        rt_s2_dict = dict(rt_s2 or {})
        
        s2_json["group_id"] = group_id
        s2_json["group_path"] = group_path
        s2_json["cards_for_entity_exact"] = expected_n
        
        got_n = len(s2_json.get("anki_cards") or [])
        if got_n != expected_n:
            raise RuntimeError(
                f"S0 exact-N violated: expected {expected_n}, got {got_n} (entity={s2_json.get('entity_name', '?')})"
            )
        
        # attach stable entity_id for downstream traceability (already set in ent_id_final above)
        s2_json["entity_id"] = ent_id_final
        
        # Attach runtime metadata (tokens, latency) for this entity's S2 call
        if rt_s2 is not None:
            s2_json["metadata"] = {
                "runtime": {
                    "latency_sec": rt_s2.get("latency_sec"),
                    "input_tokens": rt_s2.get("input_tokens"),
                    "output_tokens": rt_s2.get("output_tokens"),
                    "total_tokens": rt_s2.get("total_tokens"),
                }
            }
        if log_entity:
            elapsed = time.perf_counter() - t0_entity
            if progress_logger:
                progress_logger.debug(f"[S2][ENTITY] end entity={ent_name[:80]} ok=1 elapsed={elapsed:.2f}s")
            else:
                print(
                    f"  [S2][ENTITY] end entity={ent_name[:80]} ok=1 elapsed={elapsed:.2f}s",
                    flush=True,
                )
        return s2_json, None, rt_s2_dict
    
    except Exception as e:
        # Catch all exceptions to prevent thread pool from hanging
        # This ensures that even if an unexpected error occurs, the future completes
        import traceback
        error_msg = f"Unexpected error processing entity {ent_name}: {type(e).__name__}: {str(e)}"
        error_detail = f"{error_msg}\n{traceback.format_exc()}"
        print(f"  [S2] [EXCEPTION] {error_msg}", flush=True)
        if log_entity:
            elapsed = time.perf_counter() - t0_entity
            if progress_logger:
                progress_logger.debug(f"[S2][ENTITY] end entity={ent_name[:80]} ok=0 elapsed={elapsed:.2f}s exception={type(e).__name__}")
            else:
                print(
                    f"  [S2][ENTITY] end entity={ent_name[:80]} ok=0 elapsed={elapsed:.2f}s exception={type(e).__name__}",
                    flush=True,
                )
        return None, error_detail, {}


# -------------------------
# MAIN PROCESS LOOP
# -------------------------
def process_single_group(
    row: Dict[str, Any],
    *,
    base_dir: Path,
    provider: str,
    clients: ProviderClients,
    arm: str,
    arm_config: Dict[str, Any],
    bundle: Dict[str, Any],
    run_tag: str,
    mode: str,
    model_stage1: str,
    model_stage2: str,
    temp_stage1: float,
    temp_stage2: float,
    timeout_s: int,
    cards_per_entity_default: int,
    s0_spread_mode: str,
    entity_list_cap: int,
    out_dir: Path,
    stage1_struct_fh: Optional[Any] = None,
    execute_s1: bool = True,
    execute_s2: bool = True,
    s1_arm: Optional[str] = None,  # Arm to use for reading S1 output (defaults to arm if None)
    quota_s1: Optional[Any] = None,
    quota_s2: Optional[Any] = None,
    workers_s2_entity: int = 1,  # Entity-level parallelization workers for S2
    progress_logger: Optional[Any] = None,  # ProgressLogger instance for progress tracking
    resume_failed: bool = False,  # Skip already successful entities when resuming failed groups
    s2_results_path: Optional[Path] = None,  # Path to S2 results file for checking existing entities
    output_variant: str = "baseline",  # baseline|repaired
    repair_plan_by_group_id: Optional[Dict[str, Dict[str, Any]]] = None,
    repair_plan_by_group_key: Optional[Dict[str, Dict[str, Any]]] = None,
    only_entity_names: Optional[set[str]] = None,
    only_entity_ids: Optional[set[str]] = None,
    regen_mode: Optional[str] = None,
    regen_specs_by_group_id: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:

    P_S1_SYS = bundle["prompts"]["S1_SYSTEM"]
    P_S1_USER_T = bundle["prompts"]["S1_USER_GROUP"]
    P_S2_SYS = bundle["prompts"]["S2_SYSTEM"]
    P_S2_USER_T = bundle["prompts"]["S2_USER_ENTITY"]

    sp = row.get("specialty", "Radiology")
    an = row.get("anatomy", "General")
    mod = row.get("modality_or_type", "")
    cat = row.get("category", "")
    key = row.get("group_key", "")
    objs = row.get("objective_list", [])

    base_path = f"{sp} > {an} > {mod}".strip()
    cat_s = str(cat).strip()
    group_path = base_path + (f" > {cat_s}" if cat_s else "")

    original_objs = normalize_objective_list(objs)
    original_n = len(original_objs)
    original_chars = sum(len(x) for x in original_objs)

    objective_selection_policy = "no_truncation"
    selected_indices: List[int] = list(range(original_n))
    selected_chars = original_chars

    if original_chars > CAP_CHARS_TOTAL_RISK:
        objs, selected_indices, selected_chars = apply_cap_chars_total(
            original_objs, cap_chars_total=CAP_CHARS_TOTAL_RISK
        )
        objective_selection_policy = f"risk_only_cap_chars_total={CAP_CHARS_TOTAL_RISK}"
    else:
        objs = original_objs

    # Use group_id from CSV (canonical SSOT) - REQUIRED, no fallback generation
    # CSV format: "grp_{sha1(group_key)[:10]}" (e.g., "grp_f073599bec")
    # This ensures consistency across S1-S4 pipeline
    gid = row.get("group_id")
    if not gid or not str(gid).strip():
        raise ValueError(
            f"group_id is required in groups_canonical.csv but missing for group. "
            f"group_key={key}, specialty={sp}, anatomy={an}, modality={mod}, category={cat}. "
            f"Please regenerate groups_canonical.csv with group_id column."
        )
    gid = str(gid).strip()

    variant_suffix = _variant_suffix(output_variant)
    debug_dir = out_dir / ("debug_raw__repaired" if variant_suffix else "debug_raw")

    # Option C (PR2): select repair-plan record for this group (best-effort)
    repair_plan: Optional[Dict[str, Any]] = None
    if _normalize_output_variant(output_variant) == "repaired":
        if repair_plan_by_group_id and gid in repair_plan_by_group_id:
            repair_plan = repair_plan_by_group_id.get(gid)
        elif repair_plan_by_group_key and key and key in repair_plan_by_group_key:
            repair_plan = repair_plan_by_group_key.get(key)

    # -------------------------
    # Runtime logging context (Step01 policy)
    # -------------------------
    thinking_enabled = bool(arm_config.get("thinking", False))
    rag_enabled = bool(arm_config.get("rag", False))

    # Determine thinking_level for Gemini 3 (or thinking_budget for Gemini 2.5)
    # For Gemini 3: use thinking_level (minimal/high)
    # For Gemini 2.5: use thinking_budget (backward compatibility)
    model_is_gemini3 = model_stage1.startswith("gemini-3") or model_stage2.startswith("gemini-3")
    
    if model_is_gemini3:
        # Gemini 3: thinking_level takes precedence
        if "thinking_level" in arm_config:
            thinking_level = str(arm_config["thinking_level"]).strip().lower()
        elif thinking_enabled:
            thinking_level = env_str(f"THINKING_LEVEL_ARM_{arm}", env_str("THINKING_LEVEL_ON", "high")).strip().lower()
        else:
            thinking_level = "minimal"

        # Optional runtime override (no code changes needed):
        # - GEMINI_THINKING_LEVEL overrides all arms
        # - GEMINI_THINKING_LEVEL_ARM_E overrides per-arm
        override_level = env_str(f"GEMINI_THINKING_LEVEL_ARM_{arm}", env_str("GEMINI_THINKING_LEVEL", "")).strip().lower()
        if override_level:
            thinking_level = override_level
        
        # Validate thinking_level
        valid_levels = {"minimal", "low", "medium", "high"}
        if thinking_level not in valid_levels:
            raise RuntimeError(f"Invalid thinking_level='{thinking_level}' for Gemini 3. Must be one of {valid_levels}")
        
        # For backward compatibility, set thinking_budget to None (not used for Gemini 3)
        thinking_budget = None
    else:
        # Gemini 2.5: use thinking_budget (backward compatibility)
        if thinking_enabled:
            if "thinking_budget" in arm_config:
                thinking_budget = int(arm_config["thinking_budget"])
            else:
                thinking_budget = env_int(f"THINKING_BUDGET_ARM_{arm}", env_int("THINKING_BUDGET_ON", 1024))
        else:
            thinking_budget = 0
        thinking_level = None

    # RAG mode/counts are logged from actual API response metadata.
    # When retrieval is not implemented yet, counts will remain 0 but still be non-null.
    rag_mode = (os.getenv("RAG_MODE", "google_search") if rag_enabled else "none").strip().lower() or "none"

    # -------- Stage 1 (S1) --------
    if not execute_s1:
        # S2-only mode: load existing S1 output from stage1_struct file
        # Use s1_arm if provided, otherwise use arm (S2 execution arm)
        s1_arm_for_reading = (s1_arm or arm).strip().upper() if s1_arm else arm
        # Option C safety contract: even when output_variant == 'repaired', S2-only MUST read baseline S1 SSOT.
        # Repaired runs are S2-only and additive; they must never require or depend on repaired S1 outputs.
        stage1_struct_path = out_dir / f"stage1_struct__arm{s1_arm_for_reading}.jsonl"
        if not stage1_struct_path.exists():
            raise RuntimeError(f"S2-only mode requires existing S1 output: {stage1_struct_path} not found. Run with --stage 1 first.")
        
        # Read S1 struct for this group_id (with fallback to group_key)
        s1_struct_data = None
        with open(stage1_struct_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    s1_struct = json.loads(line)
                    # Try group_id first (primary match)
                    if s1_struct.get("group_id") == gid:
                        s1_struct_data = s1_struct
                        break
                    # Fallback: try group_key if group_id doesn't match
                    # Check both top-level group_key and source_info.group_key
                    # (handles cases where group_id generation differs between S1 and S2)
                    if key:
                        # Check top-level group_key (S1 struct format)
                        if s1_struct.get("group_key") == key:
                            s1_struct_data = s1_struct
                            # Update gid to match the found record for consistency
                            gid = s1_struct.get("group_id", gid)
                            break
                        # Check source_info.group_key (legacy format)
                        source_info = s1_struct.get("source_info") or {}
                        if source_info.get("group_key") == key:
                            s1_struct_data = s1_struct
                            # Update gid to match the found record for consistency
                            gid = s1_struct.get("group_id", gid)
                            break
                except Exception:
                    continue
        
        if s1_struct_data is None:
            # Collect available group_ids and group_keys for debugging
            available_gids = []
            available_keys = []
            try:
                with open(stage1_struct_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            s1_struct = json.loads(line)
                            gid_found = s1_struct.get("group_id")
                            if gid_found:
                                available_gids.append(gid_found)
                            # Check both top-level and source_info.group_key
                            key_found = s1_struct.get("group_key")
                            if key_found:
                                available_keys.append(key_found)
                            source_info = s1_struct.get("source_info") or {}
                            key_found_src = source_info.get("group_key")
                            if key_found_src and key_found_src not in available_keys:
                                available_keys.append(key_found_src)
                        except Exception:
                            continue
            except Exception:
                pass
            
            error_msg = (
                f"S2-only mode: S1 output not found for group_id={gid} or group_key={key} "
                f"in {stage1_struct_path}.\n"
                f"  Looking for: group_id={gid}, group_key={key}\n"
                f"  Available in S1 file: {len(available_gids)} group_ids, {len(available_keys)} group_keys"
            )
            if available_gids:
                error_msg += f"\n  Sample group_ids: {available_gids[:5]}"
            if available_keys:
                error_msg += f"\n  Sample group_keys: {available_keys[:5]}"
            
            # Return error instead of raising - allows skipping this group and continuing
            print(f"⚠️  Skipping group (S1 output missing): {key or gid}", flush=True)
            return None, {"stage": "stage2", "group_id": gid, "error": error_msg}
        
        # Reconstruct s1_json from struct
        s1_json = {
            "visual_type_category": s1_struct_data.get("visual_type_category", "General"),
            "master_table_markdown_kr": s1_struct_data.get("master_table_markdown_kr", ""),
            "entity_list": s1_struct_data.get("entity_list", []),
        }
        
        # Use entity_list as PRIMARY source (S2-only mode fix)
        entity_list_raw = s1_struct_data.get("entity_list", [])
        entity_objs = _normalize_entity_list(entity_list_raw)
        
        # Extract entity names from master table for VALIDATION only
        mt = s1_json.get("master_table_markdown_kr", "")
        entity_names_table = extract_entity_names_from_master_table(mt)
        
        # Validate: Compare entity_list with master_table extraction
        # This validation ensures data consistency and helps identify parsing issues
        if entity_names_table:
            # Extract normalized names from entity_list for comparison
            entity_names_from_list = _extract_entity_names_from_list(entity_list_raw)
            
            # Compare normalized names (exact match required)
            if len(entity_names_from_list) != len(entity_names_table) or entity_names_from_list != entity_names_table:
                # Log detailed differences for debugging
                missing_in_table = set(entity_names_from_list) - set(entity_names_table)
                extra_in_table = set(entity_names_table) - set(entity_names_from_list)
                
                # Build comprehensive warning message
                warn_msg = (
                    f"[W] S1 entity_list and master_table first column mismatch (S2-only mode, group_id={gid}, arm={arm}, run_tag={run_tag})\n"
                    f"  entity_list count: {len(entity_names_from_list)}, master_table count: {len(entity_names_table)}\n"
                    f"  Difference: {len(entity_names_from_list) - len(entity_names_table)} entities\n"
                )
                
                if missing_in_table:
                    missing_list = list(missing_in_table)
                    warn_msg += f"  Entities in entity_list but NOT in master_table ({len(missing_in_table)} total):\n"
                    # Show first 20 entities, or all if less than 20
                    display_count = min(20, len(missing_list))
                    for i, entity in enumerate(missing_list[:display_count], 1):
                        warn_msg += f"    {i}. {entity}\n"
                    if len(missing_list) > display_count:
                        warn_msg += f"    ... and {len(missing_list) - display_count} more\n"
                
                if extra_in_table:
                    extra_list = list(extra_in_table)
                    warn_msg += f"  Entities in master_table but NOT in entity_list ({len(extra_in_table)} total):\n"
                    # Show first 20 entities, or all if less than 20
                    display_count = min(20, len(extra_list))
                    for i, entity in enumerate(extra_list[:display_count], 1):
                        warn_msg += f"    {i}. {entity}\n"
                    if len(extra_list) > display_count:
                        warn_msg += f"    ... and {len(extra_list) - display_count} more\n"
                
                warn_msg += "  ACTION: Using entity_list as primary source (master_table used for validation only). NO OVERRIDE.\n"
                warn_msg += "  This mismatch may indicate a parsing issue in master_table extraction or inconsistency in S1 output."
                
                if progress_logger:
                    progress_logger.warning(warn_msg)
                else:
                    print(warn_msg, file=_sys.stderr)
            else:
                # Log success for debugging (only if progress_logger is available)
                if progress_logger:
                    progress_logger.debug(
                        f"[OK] entity_list and master_table match ({len(entity_names_from_list)} entities, "
                        f"group_id={gid}, arm={arm}, run_tag={run_tag})"
                    )
        
        # Fallback: If entity_list is empty/missing, use master_table (should not happen in normal flow)
        if not entity_objs and entity_names_table:
            warn_msg = f"[W] entity_list is empty, falling back to master_table extraction (S2-only mode, group_id={gid}, arm={arm}, run_tag={run_tag})"
            if progress_logger:
                progress_logger.debug(warn_msg)
            else:
                print(warn_msg, file=_sys.stderr)
            entity_objs = _normalize_entity_list(entity_names_table)
        
        # In FINAL mode, entity_list_cap should not limit entities (all entities should get cards)
        # Only apply cap in S0 mode or when explicitly needed for testing
        if entity_list_cap > 0 and str(mode).upper() == "S0":
            entity_objs = entity_objs[:entity_list_cap]
            if len(entity_objs) < len(_normalize_entity_list(s1_struct_data.get("entity_list", []))):
                print(f"[INFO] entity_list_cap={entity_list_cap} applied in S0 mode, limiting to {len(entity_objs)} entities", flush=True)
        elif entity_list_cap > 0 and str(mode).upper() != "FINAL":
            # For non-FINAL modes, allow cap for testing/debugging
            entity_objs = entity_objs[:entity_list_cap]
            if len(entity_objs) < len(_normalize_entity_list(s1_struct_data.get("entity_list", []))):
                print(f"[INFO] entity_list_cap={entity_list_cap} applied, limiting to {len(entity_objs)} entities", flush=True)
        
        entity_list = [e.get("entity_name", "").strip() for e in entity_objs if str(e.get("entity_name", "")).strip()]
        entity_id_list = [e.get("entity_id", "").strip() for e in entity_objs if str(e.get("entity_id", "")).strip()]
        ent2id = {e.get("entity_name", "").strip(): e.get("entity_id", "").strip() for e in entity_objs if str(e.get("entity_name", "")).strip() and str(e.get("entity_id", "")).strip()}
        
        # For S2-only, we don't have S1 runtime metadata, so set defaults
        rt_s1 = {
            "rag_queries_count": 0,
            "rag_sources_count": 0,
            "latency_sec": None,
            "input_tokens": None,
            "output_tokens": None,
        }
        
        # Skip to S2 processing
        # objective_bullets: schema v1.3 requires array of strings, but may be string (legacy) or array
        objective_bullets_raw = s1_struct_data.get("objective_bullets", "")
        if isinstance(objective_bullets_raw, list):
            # New format: array of strings, convert to markdown bullets for prompt
            objective_bullets = "\n".join([f"- {item}" for item in objective_bullets_raw if str(item).strip()])
        elif isinstance(objective_bullets_raw, str) and objective_bullets_raw.strip():
            # Legacy format: already a markdown string
            objective_bullets = objective_bullets_raw
        else:
            # Fallback: try to reconstruct from original objs if available
            objective_bullets = build_objective_bullets(objs) if objs else ""
        
        group_path = s1_struct_data.get("group_path", "")
        if not group_path:
            # Try to reconstruct from row
            group_path = f"{sp} > {an} > {mod}".strip()
            cat_s = str(cat).strip()
            if cat_s:
                group_path += f" > {cat_s}"
    else:
        # Normal S1 execution path
        try:
            objective_bullets = build_objective_bullets(objs)
        except Exception as e:
            return None, {"stage": "input", "group_id": gid, "error": f"Objective bullets build failed: {e}"}

        s1_user = safe_prompt_format(
            P_S1_USER_T,
            specialty=sp,
            anatomy=an,
            modality_or_type=mod,
            category=cat,
            group_path=group_path,
            group_key=key,
            objective_bullets=objective_bullets,
        )

        # Option C (PR2): append repair-plan instructions (no prompt-template edits)
        s1_user = maybe_append_repair_instructions(
            s1_user,
            output_variant=output_variant,
            repair_plan=repair_plan,
            stage="S1",
            group_id=gid,
            group_key=str(key or "").strip(),
            entity_name=None,
        )

        # S1R: Check if this group has regeneration specs
        regen_spec = None
        s1_system_prompt = P_S1_SYS
        s1_user_enhanced = s1_user
        if regen_mode == "table_content_only" and regen_specs_by_group_id:
            regen_spec = regen_specs_by_group_id.get(gid)
            if regen_spec:
                positive_instruction = regen_spec.get("positive_instruction", "")
                original_entity_list = regen_spec.get("original_entity_list", [])
                original_column_names = regen_spec.get("original_column_names", [])
                
                # Build entity list constraint
                entity_constraint = "\n\n---\n\n## ⚠️ CRITICAL STRUCTURE CONSTRAINTS (MUST FOLLOW)\n\n"
                entity_constraint += "### 1. Entity List (FIXED - DO NOT MODIFY)\n\n"
                entity_constraint += "You MUST use exactly these entities in this exact order:\n\n"
                entity_constraint += "```json\n"
                entity_constraint += "\"entity_list\": [\n"
                for i, entity_name in enumerate(original_entity_list):
                    comma = "," if i < len(original_entity_list) - 1 else ""
                    entity_constraint += f'  "{entity_name}"{comma}\n'
                entity_constraint += "]\n```\n\n"
                entity_constraint += f"**Total entities: {len(original_entity_list)}** (DO NOT add or remove any)\n\n"
                
                # Build column structure constraint
                entity_constraint += "### 2. Table Column Structure (FIXED - DO NOT MODIFY)\n\n"
                entity_constraint += "You MUST use exactly these columns in this exact order:\n\n"
                for i, col_name in enumerate(original_column_names, 1):
                    entity_constraint += f"{i}. {col_name}\n"
                entity_constraint += f"\n**Total columns: {len(original_column_names)}** (DO NOT add or remove any)\n\n"
                
                # Add positive instruction
                if positive_instruction:
                    entity_constraint += "### 3. Content Improvements\n\n"
                    entity_constraint += positive_instruction
                    entity_constraint += "\n"
                
                entity_constraint += "\n**REMINDER**: Only improve the CONTENT of table cells. The entity list and column structure are FIXED and cannot be changed.\n"
                
                # Append to user prompt (more effective than system prompt)
                s1_user_enhanced = s1_user + entity_constraint
                
                print(f"  [S1R] Regenerating with structure constraints: {len(original_entity_list)} entities, {len(original_column_names)} columns (score={regen_spec.get('table_regeneration_trigger_score')})", flush=True)

        # Log S1 processing start
        if progress_logger:
            progress_logger.debug(f"[S1] Processing group: {key[:60]}... ({len(objs)} objectives)")
        else:
            print(f"  [S1] Processing group: {key[:60]}... ({len(objs)} objectives)", flush=True)

        s1_json, err1, rt_s1, raw_s1, retry_meta_s1 = call_llm_with_schema_retry(
            provider=provider,
            clients=clients,
            model_name=model_stage1,
            system_prompt=s1_system_prompt,
            user_prompt=s1_user_enhanced,
            temperature=temp_stage1,
            timeout_s=timeout_s,
            stage=1,
            api_style=str(arm_config.get("api_style") or "chat"),
            thinking_enabled=thinking_enabled,
            thinking_budget=thinking_budget,
            thinking_level=thinking_level if model_is_gemini3 else None,
            rag_enabled=rag_enabled,
            validate_fn=validate_stage1,
            run_tag=run_tag,
            arm=arm,
            group_id=gid,
            out_dir=out_dir,
            entity_id=None,
            entity_name=None,
            row_index=None,
            quota_limiter=quota_s1,
            progress_logger=progress_logger,
        )

        _write_stage_debug(
            debug_dir=debug_dir,
            stage=1,
            group_id=gid,
            arm=arm,
            system_prompt=s1_system_prompt,
            user_prompt=s1_user_enhanced,
            raw_response=raw_s1,
        )

        if not s1_json:
            error_detail = err1 or "Unknown stage1 error"
            if retry_meta_s1.get("retry_occurred"):
                error_detail += f" (schema retry occurred: {retry_meta_s1.get('attempt_count')}/{MAX_SCHEMA_ATTEMPTS} attempts)"
            return None, {"stage": "stage1", "group_id": gid, "error": error_detail}
        
        # s1_json is already validated by call_llm_with_schema_retry

        # Use entity_list as PRIMARY source (integrated mode fix)
        entity_list_raw = s1_json.get("entity_list", [])
        entity_objs = _normalize_entity_list(entity_list_raw)
        
        # S1R: Validate structure preservation (entity count and column structure only)
        if regen_mode == "table_content_only" and regen_spec:
            original_entity_list = regen_spec.get("original_entity_list", [])
            original_column_names = regen_spec.get("original_column_names", [])
            
            # Helper function to normalize entity names (remove markdown formatting)
            def normalize_entity_name(name: str) -> str:
                """Remove markdown bold/italic and extra whitespace for comparison."""
                import re
                # Remove markdown bold (**text** or __text__)
                name = re.sub(r'\*\*(.+?)\*\*', r'\1', name)
                name = re.sub(r'__(.+?)__', r'\1', name)
                # Remove markdown italic (*text* or _text_)
                name = re.sub(r'\*(.+?)\*', r'\1', name)
                name = re.sub(r'_(.+?)_', r'\1', name)
                # Normalize whitespace
                name = ' '.join(name.split())
                return name.strip()
            
            # Extract and normalize current entity names from master table
            mt_temp = s1_json.get("master_table_markdown_kr", "")
            if mt_temp:
                lines = mt_temp.strip().split('\n')
                if len(lines) >= 3:  # Header + separator + at least 1 data row
                    # Extract entity names from first column of data rows (skip header and separator)
                    current_entity_names = []
                    for line in lines[2:]:  # Skip header and separator
                        line = line.strip()
                        if line.startswith('|'):
                            cols = [col.strip() for col in line.strip('|').split('|')]
                            if cols:
                                current_entity_names.append(cols[0])
                    
                    # Normalize both lists for comparison
                    normalized_original = [normalize_entity_name(e) for e in original_entity_list]
                    normalized_current = [normalize_entity_name(e) for e in current_entity_names]
                    
                    # Validate entity count (relaxed: warn but allow ±2)
                    count_diff = abs(len(normalized_current) - len(normalized_original))
                    if count_diff > 0:
                        if count_diff > 2:
                            # Critical: block if difference > 2
                            error_msg = (
                                f"[S1R] CRITICAL entity count mismatch: original={len(normalized_original)}, "
                                f"regenerated={len(normalized_current)} (diff={count_diff}). "
                                f"Difference too large (>2), blocking."
                            )
                            print(f"❌ {error_msg}", file=_sys.stderr, flush=True)
                            return None, {"stage": "stage1_regen_validation", "group_id": gid, "error": error_msg}
                        else:
                            # Minor: warn but allow
                            warn_msg = (
                                f"⚠️  [S1R] Entity count changed: original={len(normalized_original)}, "
                                f"regenerated={len(normalized_current)} (diff={count_diff}). "
                                f"Within tolerance (≤2), proceeding."
                            )
                            print(warn_msg, file=_sys.stderr, flush=True)
                    
                    # Validate entity names (relaxed: warn only, don't block)
                    mismatches = []
                    min_len = min(len(normalized_original), len(normalized_current))
                    for i in range(min_len):
                        orig = normalized_original[i] if i < len(normalized_original) else ""
                        curr = normalized_current[i] if i < len(normalized_current) else ""
                        if orig and curr and orig != curr:
                            mismatches.append(f"  Row {i+1}: '{orig}' → '{curr}'")
                    
                    if mismatches:
                        warn_msg = (
                            f"⚠️  [S1R] Entity names changed: {len(mismatches)} mismatch(es) found. "
                            f"Proceeding with warnings."
                        )
                        print(warn_msg, file=_sys.stderr, flush=True)
                        for mm in mismatches[:3]:  # Show first 3
                            print(mm, file=_sys.stderr)
                        if len(mismatches) > 3:
                            print(f"  ... and {len(mismatches)-3} more", file=_sys.stderr)
                    
                    # Validate column structure preservation (relaxed: warn if mismatch, don't block)
                    current_col_count = 0
                    header_line = lines[0].strip()
                    if header_line.startswith('|'):
                        current_columns = [col.strip() for col in header_line.strip('|').split('|') if col.strip()]
                        current_col_count = len(current_columns)
                        if current_col_count != len(original_column_names):
                            warn_msg = (
                                f"⚠️  [S1R] Column count changed: original={len(original_column_names)}, "
                                f"regenerated={current_col_count}. Proceeding with warning."
                            )
                            print(warn_msg, file=_sys.stderr, flush=True)
                    
                    print(f"  [S1R] ✓ Validation complete: {len(normalized_current)} entities, {current_col_count} columns (relaxed mode)", flush=True)
        
        # Extract entity names from master table for VALIDATION only
        mt = s1_json.get("master_table_markdown_kr", "")
        entity_names_table = extract_entity_names_from_master_table(mt)
        
        # Warn if master table contains ellipsis
        if mt and "..." in mt:
            print(f"[W] master_table_markdown_kr contains ellipsis '...' (group_id={gid}, arm={arm}, run_tag={run_tag})", file=_sys.stderr)
        
        # Validate: Compare entity_list with master_table extraction
        # This validation ensures data consistency and helps identify parsing issues
        if entity_names_table:
            # Extract normalized names from entity_list for comparison
            entity_names_from_list = _extract_entity_names_from_list(entity_list_raw)
            
            # Compare normalized names (exact match required)
            if len(entity_names_from_list) != len(entity_names_table) or entity_names_from_list != entity_names_table:
                # Log detailed differences for debugging
                missing_in_table = set(entity_names_from_list) - set(entity_names_table)
                extra_in_table = set(entity_names_table) - set(entity_names_from_list)
                
                # Build comprehensive warning message
                warn_msg = (
                    f"[W] S1 entity_list and master_table first column mismatch (integrated mode, group_id={gid}, arm={arm}, run_tag={run_tag})\n"
                    f"  entity_list count: {len(entity_names_from_list)}, master_table count: {len(entity_names_table)}\n"
                    f"  Difference: {len(entity_names_from_list) - len(entity_names_table)} entities\n"
                )
                
                if missing_in_table:
                    missing_list = list(missing_in_table)
                    warn_msg += f"  Entities in entity_list but NOT in master_table ({len(missing_in_table)} total):\n"
                    # Show first 20 entities, or all if less than 20
                    display_count = min(20, len(missing_list))
                    for i, entity in enumerate(missing_list[:display_count], 1):
                        warn_msg += f"    {i}. {entity}\n"
                    if len(missing_list) > display_count:
                        warn_msg += f"    ... and {len(missing_list) - display_count} more\n"
                
                if extra_in_table:
                    extra_list = list(extra_in_table)
                    warn_msg += f"  Entities in master_table but NOT in entity_list ({len(extra_in_table)} total):\n"
                    # Show first 20 entities, or all if less than 20
                    display_count = min(20, len(extra_list))
                    for i, entity in enumerate(extra_list[:display_count], 1):
                        warn_msg += f"    {i}. {entity}\n"
                    if len(extra_list) > display_count:
                        warn_msg += f"    ... and {len(extra_list) - display_count} more\n"
                
                warn_msg += "  ACTION: Using entity_list as primary source (master_table used for validation only). NO OVERRIDE.\n"
                warn_msg += "  This mismatch may indicate a parsing issue in master_table extraction or inconsistency in S1 output."
                
                if progress_logger:
                    progress_logger.warning(warn_msg)
                else:
                    print(warn_msg, file=_sys.stderr)
            else:
                # Log success for debugging (only if progress_logger is available)
                if progress_logger:
                    progress_logger.debug(
                        f"[OK] entity_list and master_table match ({len(entity_names_from_list)} entities, "
                        f"group_id={gid}, arm={arm}, run_tag={run_tag})"
                    )
        
        # Fallback: If entity_list is empty/missing, use master_table (should not happen in normal flow)
        if not entity_objs and entity_names_table:
            warn_msg = f"[W] entity_list is empty, falling back to master_table extraction (integrated mode, group_id={gid}, arm={arm}, run_tag={run_tag})"
            if progress_logger:
                progress_logger.debug(warn_msg)
            else:
                print(warn_msg, file=_sys.stderr)
            entity_objs = _normalize_entity_list(entity_names_table)
        
        # In FINAL mode, entity_list_cap should not limit entities (all entities should get cards)
        # Only apply cap in S0 mode or when explicitly needed for testing
        original_entity_count = len(entity_objs)
        if entity_list_cap > 0 and str(mode).upper() == "S0":
            entity_objs = entity_objs[:entity_list_cap]
            if len(entity_objs) < original_entity_count:
                print(f"[INFO] entity_list_cap={entity_list_cap} applied in S0 mode, limiting to {len(entity_objs)} entities (from {original_entity_count})", flush=True)
        elif entity_list_cap > 0 and str(mode).upper() != "FINAL":
            # For non-FINAL modes, allow cap for testing/debugging
            entity_objs = entity_objs[:entity_list_cap]
            if len(entity_objs) < original_entity_count:
                print(f"[INFO] entity_list_cap={entity_list_cap} applied, limiting to {len(entity_objs)} entities (from {original_entity_count})", flush=True)

        entity_list = [e.get("entity_name", "").strip() for e in entity_objs if str(e.get("entity_name", "")).strip()]

        # Print S1 completion
        if progress_logger:
            progress_logger.debug(f"[S1] ✓ Completed group: {key[:60]}... ({len(entity_list)} entities)")
        else:
            print(f"  [S1] ✓ Completed group: {key[:60]}... ({len(entity_list)} entities)", flush=True)

        # Map entity_name -> stable entity_id (used for debug filenames and traceability)
        entity_id_list = [e.get("entity_id", "").strip() for e in entity_objs if str(e.get("entity_id", "")).strip()]
        ent2id = {e.get("entity_name", "").strip(): e.get("entity_id", "").strip() for e in entity_objs if str(e.get("entity_name", "")).strip() and str(e.get("entity_id", "")).strip()}

    # -------- Stage1 struct artifact (Gate input) --------
    if stage1_struct_fh is not None:
        # Count table rows for integrity object
        mt = s1_json.get("master_table_markdown_kr", "")
        table_row_count = 0
        if mt:
            lines = [line.strip() for line in mt.strip().split("\n") if line.strip()]
            # Find header row
            header_idx = None
            for i, line in enumerate(lines):
                if "|" in line:
                    header_idx = i
                    break
            if header_idx is not None:
                # Count data rows (skip header and separator)
                data_start = header_idx + 2
                if data_start < len(lines):
                    table_row_count = sum(1 for line in lines[data_start:] if "|" in line)
        
        # Build objective_bullets as array (schema requires array of strings)
        # Use original objs (List[str]) which is already normalized from objective_list
        objective_bullets_array = [str(x).strip() for x in objs if str(x).strip()]
        
        # Fallback: if objs is empty, try to parse from objective_bullets string
        if not objective_bullets_array and objective_bullets:
            # Parse markdown bullet list into array
            if isinstance(objective_bullets, str):
                for line in objective_bullets.strip().split("\n"):
                    line = line.strip()
                    if line.startswith("- "):
                        objective_bullets_array.append(line[2:].strip())
                    elif line.startswith("* "):
                        objective_bullets_array.append(line[2:].strip())
                    elif line and not line.startswith("#"):
                        objective_bullets_array.append(line)
            elif isinstance(objective_bullets, list):
                objective_bullets_array = [str(x).strip() for x in objective_bullets if str(x).strip()]  # type: ignore
        
        s1_struct = {
            "schema_version": "S1_STRUCT_v1.3",  # Required by schema
            "group_id": gid,
            "group_path": group_path,  # Required by schema
            "objective_bullets": objective_bullets_array if objective_bullets_array else [str(objective_bullets or "").strip()],  # Required: array of strings
            "visual_type_category": str(s1_json.get("visual_type_category") or "").strip(),
            "master_table_markdown_kr": str(s1_json.get("master_table_markdown_kr") or "").strip(),
            "entity_list": list(entity_objs),
            "integrity": {  # Required by schema
                "entity_count": len(entity_objs),
                "table_row_count": table_row_count,
                "objective_count": len(objective_bullets_array),
            },
        }
        # Optional redundancy for debugging (only if non-empty; schema minLength=1)
        _gk = str(key or "").strip()
        if _gk:
            s1_struct["group_key"] = _gk
        
        # Include optional infographic clustering fields if present in LLM response
        entity_clusters = s1_json.get("entity_clusters")
        infographic_clusters = s1_json.get("infographic_clusters")
        if entity_clusters is not None and infographic_clusters is not None:
            # Both must be present (validated by validate_stage1)
            s1_struct["entity_clusters"] = entity_clusters
            s1_struct["infographic_clusters"] = infographic_clusters
        
        # Include runtime metadata (tokens, latency) if available
        if rt_s1 is not None:
            s1_struct["metadata"] = {
                "runtime": {
                    "latency_sec": rt_s1.get("latency_sec"),
                    "input_tokens": rt_s1.get("input_tokens"),
                    "output_tokens": rt_s1.get("output_tokens"),
                    "total_tokens": rt_s1.get("total_tokens"),
                }
            }

        stage1_struct_fh.write(json.dumps(s1_struct, ensure_ascii=False) + "\n")
        stage1_struct_fh.flush()

    # -------- S0 Allocation → S2 targets --------
    allocation_path: Optional[str] = None
    allocation_version: Optional[str] = None

    s2_targets: List[_S2Target] = []

    # Current pipeline policy: 2-card per entity (Q1/Q2).
    # NOTE: Stage2 validator enforces 2 cards. S0 allocation artifacts may still request other counts;
    # to avoid S0 exact-N conflicts, we force S2 targets to this fixed policy.
    S2_FIXED_CARDS_PER_ENTITY = 2

    if str(mode).upper() == "S0":
        if not entity_list:
            raise RuntimeError("S0: no entities returned from S1")

        alloc_inputs = S0AllocationInputs(
            run_tag=run_tag,
            group_id=gid,
            arm=arm,
            entities_from_s1=entity_list,
        )

        alloc_path = build_s0_allocation_artifact(
            base_dir=base_dir,
            inp=alloc_inputs,
            spread_mode=s0_spread_mode,  # "hard" or "soft"
        )

        alloc_artifact = require_valid_s0_allocation_artifact(alloc_path)
        allocation_path = str(alloc_path)
        allocation_version = str(alloc_artifact.get("allocation_version") or "")

        # Convert to per-entity exact targets
        targets = s0_artifact_to_s2_targets(alloc_artifact)
        for t in targets:
            eid = ent2id.get(str(t.entity_name).strip()) or _derive_entity_id_list([str(t.entity_name).strip()])[0]
            requested_n = int(getattr(t, "cards_for_entity_exact", S2_FIXED_CARDS_PER_ENTITY) or S2_FIXED_CARDS_PER_ENTITY)
            # S0 allocation policy enforcement: silently force to pipeline policy
            # (No warning needed - this is expected behavior when S0 allocation differs from pipeline policy)
            if requested_n != S2_FIXED_CARDS_PER_ENTITY:
                # Log to file only if progress_logger is available
                if progress_logger:
                    progress_logger.debug(
                        f"S0 allocation requested cards_for_entity_exact={requested_n} "
                        f"but pipeline policy is fixed at {S2_FIXED_CARDS_PER_ENTITY}. "
                        f"Forcing to {S2_FIXED_CARDS_PER_ENTITY}. (entity={t.entity_name})"
                    )
            s2_targets.append(
                _S2Target(
                    entity_id=eid,
                    entity_name=t.entity_name,
                    cards_for_entity_exact=S2_FIXED_CARDS_PER_ENTITY,
                )
            )

    else:
        # FINAL mode: 모든 entity에 대해 Entity당 2장으로 고정 (Q1/Q2 2-card policy)
        # 모든 entity_list의 entity에 대해 카드를 생성해야 함 (제한 없음)
        FINAL_CARDS_PER_ENTITY = S2_FIXED_CARDS_PER_ENTITY
        if not entity_list:
            raise RuntimeError("FINAL: no entities returned from S1")
        for ent in entity_list:
            eid = ent2id.get(str(ent).strip()) or _derive_entity_id_list([str(ent).strip()])[0]
            s2_targets.append(_S2Target(entity_id=eid, entity_name=ent, cards_for_entity_exact=FINAL_CARDS_PER_ENTITY))

    # A안: 문제(=entity) 단위 재생성 - filter s2_targets
    if only_entity_names or only_entity_ids:
        names_norm = set()
        if only_entity_names:
            names_norm = {_normalize_entity_key(x) for x in only_entity_names if _normalize_entity_key(x)}
        ids_norm = set()
        if only_entity_ids:
            ids_norm = {str(x).strip() for x in only_entity_ids if str(x).strip()}

        before = len(s2_targets)
        s2_targets = [
            t for t in s2_targets
            if (
                (names_norm and _normalize_entity_key(t.entity_name) in names_norm)
                or (ids_norm and str(t.entity_id).strip() in ids_norm)
            )
        ]
        if not s2_targets:
            raise RuntimeError(
                f"No S2 targets matched only_entity filters for group_id={gid}. "
                f"(before={before}, names={sorted(list(names_norm))[:5]}, ids={sorted(list(ids_norm))[:5]})"
            )
        if progress_logger:
            progress_logger.debug(f"[S2] Entity filter applied: {len(s2_targets)}/{before} targets kept (group_id={gid})")
        else:
            print(f"  [S2] Entity filter applied: {len(s2_targets)}/{before} targets kept", flush=True)

    # Skip already successful entities when resuming failed groups
    # Use entity_id for comparison (more reliable than entity_name)
    if resume_failed and execute_s2 and s2_results_path and s2_results_path.exists():
        try:
            # Load existing successful entities for this group (by entity_id)
            existing_entity_ids = set()
            with open(s2_results_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        record_gid = None
                        if "metadata" in record and "id" in record["metadata"]:
                            record_gid = record["metadata"]["id"]
                        elif "group_id" in record:
                            record_gid = record["group_id"]
                        elif "source_info" in record and "group_id" in record["source_info"]:
                            record_gid = record["source_info"]["group_id"]
                        
                        if str(record_gid) == str(gid):
                            # Use entity_id for comparison (more reliable than entity_name)
                            entity_id = str(record.get("entity_id", "")).strip()
                            if entity_id:
                                existing_entity_ids.add(entity_id)
                    except json.JSONDecodeError:
                        continue
            
            # Filter out entities that already exist (by entity_id)
            if existing_entity_ids:
                original_count = len(s2_targets)
                s2_targets = [
                    tgt for tgt in s2_targets
                    if str(tgt.entity_id).strip() not in existing_entity_ids
                ]
                skipped_count = original_count - len(s2_targets)
                if skipped_count > 0:
                    if progress_logger:
                        progress_logger.debug(
                            f"[RESUME-FAILED] Group {gid}: Skipping {skipped_count} already successful entities (by entity_id). "
                            f"Processing {len(s2_targets)} missing entities."
                        )
                    else:
                        print(
                            f"[RESUME-FAILED] Group {gid}: Skipping {skipped_count} already successful entities (by entity_id). "
                            f"Processing {len(s2_targets)} missing entities.",
                            flush=True
                        )
        except Exception as e:
            if progress_logger:
                progress_logger.debug(f"[RESUME-FAILED] Warning: Could not check existing S2 entities for group {gid}: {e}")
            else:
                print(f"[RESUME-FAILED] Warning: Could not check existing S2 entities for group {gid}: {e}", file=sys.stderr, flush=True)

    # -------- Stage 2 (S2) --------
    entities_out: List[Dict[str, Any]] = []
    failed_entities: List[Dict[str, Any]] = []
    rt_s2_last: Optional[Dict[str, Any]] = None
    # Accumulate RAG metadata across all Stage2 calls
    # Use a lock for thread-safe accumulation when entity-level parallelization is enabled
    rag_lock = threading.Lock()
    rag_queries_total_s2 = 0
    rag_sources_total_s2 = 0

    if not execute_s2:
        # S1-only mode: return early with S1 results only
        record = {
            "metadata": {
                "id": gid,
                "provider": provider,
                "arm": arm,
                "arm_label": arm_config.get("label", ""),
                "run_tag": run_tag,
                "mode": mode,
                "timestamp": now_ts(),
                "model_stage1": model_stage1,
                "model_stage2": model_stage2,
                "prompt_dir": bundle.get("prompt_dir"),
                "prompt_file_ids": bundle.get("prompt_file_ids"),
                "prompt_bundle_hash": bundle.get("prompt_bundle_hash"),
                "runtime": {
                    "run_tag": run_tag,
                    "mode": mode,
                    "arm": arm,
                    "provider": provider,
                    "model_stage1": model_stage1,
                    "model_stage2": model_stage2,
                    "thinking_enabled": thinking_enabled,
                    "thinking_budget": thinking_budget,
                    "thinking_level": thinking_level if model_is_gemini3 else None,
                    "rag_enabled": rag_enabled,
                    "rag_mode": rag_mode,
                    "rag_queries_count": rt_s1.get("rag_queries_count", 0),
                    "rag_sources_count": rt_s1.get("rag_sources_count", 0),
                    "latency_sec_stage1": rt_s1.get("latency_sec"),
                    "latency_sec_stage2": None,
                    "input_tokens_stage1": rt_s1.get("input_tokens"),
                    "output_tokens_stage1": rt_s1.get("output_tokens"),
                    "input_tokens_stage2": None,
                    "output_tokens_stage2": None,
                    # MI-CLEAR-LLM: Generation config for reproducibility
                    "temperature_stage1": temp_stage1,
                    "temperature_stage2": temp_stage2,
                    "max_output_tokens_stage1": rt_s1.get("max_output_tokens"),
                    "max_output_tokens_stage2": None,
                },
            },
            "source_info": {
                "specialty": sp,
                "anatomy": an,
                "modality_or_type": mod,
                "category": cat,
                "group_path": group_path,
                "group_key": key,
                "objective_list": objs,
                "split_index": row.get("split_index", 0),
                "objective_original_count": original_n,
                "objective_original_chars": original_chars,
                "objective_selected_count": len(objs) if isinstance(objs, list) else 0,
                "objective_selected_chars": selected_chars,
                "objective_selected_indices": selected_indices,
                "objective_selection_policy": objective_selection_policy,
            },
            "curriculum_content": {
                "visual_type": s1_json.get("visual_type_category", "General"),
                "master_table": s1_json.get("master_table_markdown_kr", ""),
                "entities": [],
            },
            "meta": {
                "provider": provider,
                "arm": arm,
                "arm_label": arm_config.get("label", ""),
            },
        }
        record = validate_and_fill_record(record, run_tag=run_tag, mode=mode, provider=provider, arm=arm)
        return record, None

    # S2: Process entities with progress indication
    total_entities = len(s2_targets)
    
    # Log S2 execution start
    if execute_s2 and total_entities > 0:
        log_s2_execution(
            out_dir=out_dir,
            run_tag=run_tag,
            arm=arm,
            group_id=gid,
            action="start",
            entities_total=total_entities,
            entities_processed=0,
        )
    
    # Determine entity-level worker count (auto-adjust if not set and we have many entities)
    if workers_s2_entity == 1 and total_entities > 1:
        # Default to min(8, total_entities) if not explicitly set
        workers_s2_entity_actual = min(8, total_entities)
        if progress_logger:
            progress_logger.debug(f"[S2] Auto-adjusted entity-level workers: {workers_s2_entity_actual} (from {total_entities} entities)")
        else:
            print(f"  [S2] Auto-adjusted entity-level workers: {workers_s2_entity_actual} (from {total_entities} entities)", flush=True)
    else:
        workers_s2_entity_actual = workers_s2_entity
    
    if workers_s2_entity_actual > 1 and total_entities > 1:
        if progress_logger:
            progress_logger.debug(f"[S2] Using entity-level parallelization: {workers_s2_entity_actual} workers for {total_entities} entities")
        else:
            print(f"  [S2] Using entity-level parallelization: {workers_s2_entity_actual} workers for {total_entities} entities", flush=True)
    
    # Initialize entity progress bar
    if progress_logger and execute_s2 and total_entities > 0:
        progress_logger.init_entity(total_entities, desc="  [S2] Processing entities")
    
    if workers_s2_entity_actual > 1 and total_entities > 1:
        # Entity-level parallelization
        with ThreadPoolExecutor(max_workers=workers_s2_entity_actual) as entity_ex:
            entity_futures = {
                entity_ex.submit(
                    process_single_entity,
                    entity_target=tgt,
                    group_id=gid,
                    group_path=group_path,
                    s1_json=s1_json,
                    ent2id=ent2id,
                    provider=provider,
                    clients=clients,
                    arm=arm,
                    arm_config=arm_config,
                    bundle=bundle,
                    run_tag=run_tag,
                    mode=mode,
                    model_stage2=model_stage2,
                    temp_stage2=temp_stage2,
                    timeout_s=timeout_s,
                    thinking_enabled=thinking_enabled,
                    thinking_budget=thinking_budget,
                    thinking_level=thinking_level,
                    model_is_gemini3=model_is_gemini3,
                    rag_enabled=rag_enabled,
                    out_dir=out_dir,
                    debug_dir=debug_dir,
                    quota_s2=quota_s2,
                    P_S2_SYS=P_S2_SYS,
                    P_S2_USER_T=P_S2_USER_T,
                    output_variant=output_variant,
                    repair_plan=repair_plan,
                    group_key=str(key or "").strip(),
                    progress_logger=progress_logger,
                ): (idx, tgt)
                for idx, tgt in enumerate(s2_targets, 1)
                if str(tgt.entity_name).strip()
            }
            
            total_entities_actual = len(entity_futures)
            completed = 0
            if progress_logger:
                progress_logger.debug(f"[S2] Starting parallel processing of {total_entities_actual} entities with {workers_s2_entity_actual} workers...")
            else:
                print(
                    f"  [S2] Starting parallel processing of {total_entities_actual} entities "
                    f"with {workers_s2_entity_actual} workers...",
                    flush=True,
                )

            # Each entity should complete within timeout_s + buffer (default 120s buffer for safety)
            entity_timeout = timeout_s + 120 if timeout_s and timeout_s > 0 else 300  # Default 5 minutes if no timeout
            start_time = time.perf_counter()
            last_progress_print = start_time
            progress_check_interval = 30.0  # Check progress every 30 seconds

            # Stall diagnostics: dump all thread tracebacks when no future completes for N seconds.
            stall_dump_s = float(str(os.getenv("S2_ENTITY_STALL_DUMP_S", "180")).strip() or "180")
            last_completion_time = start_time

            pending = set(entity_futures.keys())
            while pending:
                now = time.perf_counter()
                elapsed = now - start_time

                # Overall timeout
                if elapsed >= entity_timeout:
                    print(f"  [S2] ⚠ Overall timeout after {elapsed:.1f}s (timeout={entity_timeout}s)", flush=True)
                    for fut in list(pending):
                        try:
                            fut.cancel()  # cancels only if not yet started
                        except Exception:
                            pass
                    for fut in list(pending):
                        idx, tgt = entity_futures.get(fut, (None, None))
                        ent_name = str(getattr(tgt, "entity_name", "") or "").strip()
                        completed += 1
                        # Track failed entity with entity type
                        entity_type = detect_entity_type_for_s2(
                            entity_name=ent_name,
                            visual_type_category=s1_json.get("visual_type_category", "General")
                        )
                        timeout_error = f"Entity timed out after {elapsed:.1f}s (timeout={entity_timeout}s)"
                        failed_entities.append({
                            "entity_name": ent_name,
                            "entity_id": str(getattr(tgt, "entity_id", "") or "").strip(),
                            "entity_type": entity_type,
                            "error": timeout_error,
                            "index": idx,
                        })
                        print(f"  [S2] ⚠ [{completed}/{total_entities_actual}] {ent_name[:50]} - Timeout", flush=True)
                        if str(mode).upper() == "S0":
                            raise RuntimeError(f"Entity {ent_name} timed out after {elapsed:.1f}s")
                    break

                # Periodic progress
                if now - last_progress_print >= progress_check_interval:
                    run_ct = sum(1 for f in pending if f.running())
                    if progress_logger:
                        progress_logger.debug(
                            f"[S2] Progress: {completed}/{total_entities_actual} completed, "
                            f"{len(pending)} pending ({run_ct} running) (elapsed: {elapsed:.1f}s)"
                        )
                    else:
                        print(
                            f"  [S2] Progress: {completed}/{total_entities_actual} completed, "
                            f"{len(pending)} pending ({run_ct} running) (elapsed: {elapsed:.1f}s)",
                            flush=True,
                        )
                    last_progress_print = now

                # Wait for at least one future to complete (short cadence)
                done, not_done = wait(pending, timeout=10.0, return_when=FIRST_COMPLETED)
                if not done:
                    # No completions in this tick: consider stall dump
                    if stall_dump_s and (now - last_completion_time) >= stall_dump_s:
                        run_ct = sum(1 for f in pending if f.running())
                        # Identify which entities are still running (helps distinguish slow LLM calls vs deadlocks)
                        try:
                            running_items = []
                            for f in pending:
                                if not f.running():
                                    continue
                                idx, tgt = entity_futures.get(f, (None, None))
                                ent_name = str(getattr(tgt, "entity_name", "") or "").strip()
                                ent_id = str(getattr(tgt, "entity_id", "") or "").strip()
                                group_id = str(getattr(tgt, "group_id", "") or "").strip()
                                running_items.append((idx, ent_name, ent_id, group_id))
                            running_items = sorted(running_items, key=lambda x: (x[0] is None, x[0] or 0))
                        except Exception:
                            running_items = []
                        stall_msg = f"[S2] ⚠ Stall detected: no entity completed for {now - last_completion_time:.1f}s " \
                                   f"(pending={len(pending)} running={run_ct}). Dumping thread tracebacks..."
                        if progress_logger:
                            progress_logger.debug(stall_msg)
                            if running_items:
                                # Keep it compact to avoid log spam
                                preview = running_items[:5]
                                more = max(0, len(running_items) - len(preview))
                                progress_logger.debug("  [S2] Running entities (preview):")
                                for idx, ent_name, ent_id, group_id in preview:
                                    nm = (ent_name[:80] + "…") if len(ent_name) > 80 else ent_name
                                    progress_logger.debug(
                                        f"    - idx={idx} group_id={group_id or '-'} entity_id={ent_id or '-'} name={nm or '-'}"
                                    )
                                if more:
                                    progress_logger.debug(f"    ... and {more} more running")
                            # Dump traceback to log file
                            try:
                                import io
                                traceback_buffer = io.StringIO()
                                faulthandler.dump_traceback(file=traceback_buffer, all_threads=True)
                                progress_logger.debug(f"Thread tracebacks:\n{traceback_buffer.getvalue()}")
                            except Exception:
                                pass
                        else:
                            print(stall_msg, flush=True)
                            if running_items:
                                # Keep it compact to avoid log spam
                                preview = running_items[:5]
                                more = max(0, len(running_items) - len(preview))
                                print("  [S2] Running entities (preview):", flush=True)
                                for idx, ent_name, ent_id, group_id in preview:
                                    nm = (ent_name[:80] + "…") if len(ent_name) > 80 else ent_name
                                    print(
                                        f"    - idx={idx} group_id={group_id or '-'} entity_id={ent_id or '-'} name={nm or '-'}",
                                        flush=True,
                                    )
                                if more:
                                    print(f"    ... and {more} more running", flush=True)
                            try:
                                faulthandler.dump_traceback(file=sys.stderr, all_threads=True)
                            except Exception:
                                pass
                        # Avoid dumping continuously
                        last_completion_time = now
                    continue

                pending = set(not_done)
                last_completion_time = time.perf_counter()

                for fut in done:
                    idx, tgt = entity_futures[fut]
                    ent_name = str(tgt.entity_name).strip()

                    if fut.cancelled():
                        completed += 1
                        # Track failed entity with entity type
                        entity_type = detect_entity_type_for_s2(
                            entity_name=ent_name,
                            visual_type_category=s1_json.get("visual_type_category", "General")
                        )
                        failed_entities.append({
                            "entity_name": ent_name,
                            "entity_id": str(getattr(tgt, "entity_id", "") or "").strip(),
                            "entity_type": entity_type,
                            "error": "Future was cancelled",
                            "index": idx,
                        })
                        if progress_logger:
                            progress_logger.update_entity(completed, total_entities_actual, entity_id=str(getattr(tgt, "entity_id", "") or "").strip())
                            progress_logger.warning(f"[S2] Entity cancelled: {ent_name[:50]}")
                        else:
                            print(f"  [S2] ✗ [{completed}/{total_entities_actual}] {ent_name[:50]} - Cancelled", flush=True)
                        continue

                    exc = None
                    try:
                        exc = fut.exception()
                    except Exception:
                        exc = None

                    if exc is not None:
                        completed += 1
                        error_msg = f"Future exception for entity {ent_name}: {type(exc).__name__}: {str(exc)}"
                        # Track failed entity with entity type
                        entity_type = detect_entity_type_for_s2(
                            entity_name=ent_name,
                            visual_type_category=s1_json.get("visual_type_category", "General")
                        )
                        failed_entities.append({
                            "entity_name": ent_name,
                            "entity_id": str(getattr(tgt, "entity_id", "") or "").strip(),
                            "entity_type": entity_type,
                            "error": error_msg,
                            "index": idx,
                        })
                        if progress_logger:
                            progress_logger.update_entity(completed, total_entities_actual, entity_id=str(getattr(tgt, "entity_id", "") or "").strip())
                            progress_logger.error(f"[S2] Entity failed: {ent_name[:50]} - Future exception: {str(exc)}")
                        else:
                            print(
                                f"  [S2] ✗ [{completed}/{total_entities_actual}] {ent_name[:50]} - Future exception: {str(exc)}",
                                flush=True,
                            )
                        if str(mode).upper() == "S0":
                            raise RuntimeError(error_msg) from exc
                        continue

                    try:
                        s2_json, err2, rt_s2_dict = fut.result()
                        completed += 1
                        ent_id = str(getattr(tgt, "entity_id", "") or "").strip()
                        if progress_logger:
                            progress_logger.update_entity(completed, total_entities_actual, entity_id=ent_id)
                        
                        if s2_json:
                            rt_s2_last = rt_s2_dict
                            if rt_s2_dict:
                                with rag_lock:
                                    rag_queries_total_s2 += rt_s2_dict.get("rag_queries_count", 0)
                                    rag_sources_total_s2 += rt_s2_dict.get("rag_sources_count", 0)
                            entities_out.append(s2_json)
                            expected_n = int(tgt.cards_for_entity_exact)
                            if progress_logger:
                                progress_logger.debug(f"[S2] Entity completed: {ent_name[:50]} ({expected_n} cards)")
                            else:
                                print(
                                    f"  [S2] ✓ [{completed}/{total_entities_actual}] {ent_name[:50]} ({expected_n} cards)",
                                    flush=True,
                                )
                        else:
                            # Track failed entity with entity type
                            entity_type = detect_entity_type_for_s2(
                                entity_name=ent_name,
                                visual_type_category=s1_json.get("visual_type_category", "General")
                            )
                            failed_entities.append({
                                "entity_name": ent_name,
                                "entity_id": ent_id,
                                "entity_type": entity_type,
                                "error": err2,
                                "index": idx,
                            })
                            if progress_logger:
                                progress_logger.error(f"[S2] Entity failed: {ent_name[:50]} - {err2 or 'Unknown error'}")
                            else:
                                print(
                                    f"  [S2] ✗ [{completed}/{total_entities_actual}] {ent_name[:50]} - {err2 or 'Unknown error'}",
                                    flush=True,
                                )
                    except Exception as e:
                        completed += 1
                        import traceback
                        error_msg = (
                            f"Exception getting result for entity {ent_name}: {str(e)}\n{traceback.format_exc()}"
                        )
                        # Track failed entity with entity type
                        entity_type = detect_entity_type_for_s2(
                            entity_name=ent_name,
                            visual_type_category=s1_json.get("visual_type_category", "General")
                        )
                        ent_id = str(getattr(tgt, "entity_id", "") or "").strip()
                        failed_entities.append({
                            "entity_name": ent_name,
                            "entity_id": ent_id,
                            "entity_type": entity_type,
                            "error": error_msg,
                            "index": idx,
                        })
                        if progress_logger:
                            progress_logger.update_entity(completed, total_entities_actual, entity_id=ent_id)
                            progress_logger.error(f"[S2] Entity exception: {ent_name[:50]} - {str(e)}")
                        else:
                            print(
                                f"  [S2] ✗ [{completed}/{total_entities_actual}] {ent_name[:50]} - Result exception: {str(e)}",
                                flush=True,
                            )
                        if str(mode).upper() == "S0":
                            raise RuntimeError(error_msg) from e
    else:
        # Sequential processing (original behavior)
        for idx, tgt in enumerate(s2_targets, 1):
            ent_name = str(tgt.entity_name).strip()
            if not ent_name:
                continue
            
            # Detect entity type for failure tracking
            entity_type = detect_entity_type_for_s2(
                entity_name=ent_name,
                visual_type_category=s1_json.get("visual_type_category", "General")
            )
            
            # Update entity progress
            if progress_logger:
                progress_logger.update_entity(idx, total_entities, entity_id=str(getattr(tgt, "entity_id", "") or "").strip())
                progress_logger.debug(f"[S2] Processing entity {idx}/{total_entities}: {ent_name[:50]}...")
            else:
                print(f"  [S2] Processing entity {idx}/{total_entities}: {ent_name[:50]}...", flush=True)
            
            s2_json, err2, rt_s2_dict = process_single_entity(
                entity_target=tgt,
                group_id=gid,
                group_path=group_path,
                s1_json=s1_json,
                ent2id=ent2id,
                provider=provider,
                clients=clients,
                arm=arm,
                arm_config=arm_config,
                bundle=bundle,
                run_tag=run_tag,
                mode=mode,
                model_stage2=model_stage2,
                temp_stage2=temp_stage2,
                timeout_s=timeout_s,
                thinking_enabled=thinking_enabled,
                thinking_budget=thinking_budget,
                thinking_level=thinking_level,
                model_is_gemini3=model_is_gemini3,
                rag_enabled=rag_enabled,
                out_dir=out_dir,
                debug_dir=debug_dir,
                quota_s2=quota_s2,
                P_S2_SYS=P_S2_SYS,
                P_S2_USER_T=P_S2_USER_T,
                output_variant=output_variant,
                repair_plan=repair_plan,
                group_key=str(key or "").strip(),
                progress_logger=progress_logger,
            )
            
            if not s2_json:
                # Track failed entity with entity type
                failed_entities.append({
                    "entity_name": ent_name,
                    "entity_id": str(getattr(tgt, "entity_id", "") or "").strip(),
                    "entity_type": entity_type,
                    "error": err2,
                    "index": idx,
                })
                # Error already logged in process_single_entity
                continue
            
            # s2_json is already validated and has all metadata attached
            rt_s2_last = rt_s2_dict
            
            # Accumulate RAG metadata from this Stage2 call
            if rt_s2_dict:
                rag_queries_total_s2 += rt_s2_dict.get("rag_queries_count", 0)
                rag_sources_total_s2 += rt_s2_dict.get("rag_sources_count", 0)
            
            entities_out.append(s2_json)
            
            # Log entity completion
            expected_n = int(tgt.cards_for_entity_exact)
            if progress_logger:
                progress_logger.debug(f"[S2] Entity completed: {ent_name[:50]} ({expected_n} cards)")
            else:
                print(f"  [S2] ✓ Completed entity {idx}/{total_entities}: {ent_name[:50]} ({expected_n} cards)", flush=True)

    # -------- Assemble Record --------
    record = {
        "metadata": {
            "id": gid,
            "provider": provider,
            "arm": arm,
            "arm_label": arm_config.get("label", ""),
            "run_tag": run_tag,
            "mode": mode,
            "timestamp": now_ts(),
            "model_stage1": model_stage1,
            "model_stage2": model_stage2,
            "prompt_dir": bundle.get("prompt_dir"),
            "prompt_file_ids": bundle.get("prompt_file_ids"),
            "prompt_bundle_hash": bundle.get("prompt_bundle_hash"),

            # Step01 runtime logging (canonical)
            "runtime": {
                "run_tag": run_tag,
                "mode": mode,
                "arm": arm,
                "provider": provider,
                "model_stage1": model_stage1,
                "model_stage2": model_stage2,

                "thinking_enabled": thinking_enabled,
                "thinking_budget": thinking_budget,
                "thinking_level": thinking_level if model_is_gemini3 else None,

                "rag_enabled": rag_enabled,
                "rag_mode": rag_mode,
                "rag_queries_count": rt_s1.get("rag_queries_count", 0) + rag_queries_total_s2,
                "rag_sources_count": rt_s1.get("rag_sources_count", 0) + rag_sources_total_s2,

                "latency_sec_stage1": rt_s1.get("latency_sec"),
                "latency_sec_stage2": rt_s2_last.get("latency_sec") if rt_s2_last is not None else None,

                "input_tokens_stage1": rt_s1.get("input_tokens"),
                "output_tokens_stage1": rt_s1.get("output_tokens"),
                "input_tokens_stage2": rt_s2_last.get("input_tokens") if rt_s2_last is not None else None,
                "output_tokens_stage2": rt_s2_last.get("output_tokens") if rt_s2_last is not None else None,
                # MI-CLEAR-LLM: Generation config for reproducibility
                "temperature_stage1": temp_stage1,
                "temperature_stage2": temp_stage2,
                "max_output_tokens_stage1": rt_s1.get("max_output_tokens"),
                "max_output_tokens_stage2": rt_s2_last.get("max_output_tokens") if rt_s2_last is not None else None,
            },


            # S0 allocation trace (optional, but useful for audit)
            "s0_allocation_version": allocation_version,
            "s0_allocation_path": allocation_path,
            "s0_spread_mode": s0_spread_mode if str(mode).upper() == "S0" else None,

            # S2 generation failure tracking (Phase 1: Error Visibility)
            "s2_generation": {
                "total_entities": len(s2_targets),
                "successful_entities": len(entities_out),
                "failed_entities": len(failed_entities),
            },
        },
        "source_info": {
            "specialty": sp,
            "anatomy": an,
            "modality_or_type": mod,
            "category": cat,
            "group_path": group_path,
            "group_key": key,
            "objective_list": objs,
            "split_index": row.get("split_index", 0),

            "objective_original_count": original_n,
            "objective_original_chars": original_chars,
            "objective_selected_count": len(objs) if isinstance(objs, list) else 0,
            "objective_selected_chars": selected_chars,
            "objective_selected_indices": selected_indices,
            "objective_selection_policy": objective_selection_policy,
        },
        "curriculum_content": {
            "visual_type": s1_json.get("visual_type_category", "General"),
            "master_table": s1_json.get("master_table_markdown_kr", ""),
"entities": entities_out,
        },
        "meta": {
            "provider": provider,
            "arm": arm,
            "arm_label": arm_config.get("label", ""),
        },
    }

    # Add failed entity details and entity type breakdown if there are failures
    if failed_entities:
        record["metadata"]["s2_generation"]["failed_entity_details"] = failed_entities
        # Add entity type breakdown
        entity_type_counts = {}
        for fe in failed_entities:
            et = fe.get("entity_type", "unknown")
            entity_type_counts[et] = entity_type_counts.get(et, 0) + 1
        record["metadata"]["s2_generation"]["failed_entity_types"] = entity_type_counts

    record = validate_and_fill_record(record, run_tag=run_tag, mode=mode, provider=provider, arm=arm)
    
    # Log S2 execution completion
    if execute_s2:
        if len(failed_entities) > 0:
            log_s2_execution(
                out_dir=out_dir,
                run_tag=run_tag,
                arm=arm,
                group_id=gid,
                action="failed",
                entities_total=total_entities,
                entities_processed=len(entities_out),
                error=f"{len(failed_entities)} entities failed",
            )
        elif total_entities == 0:
            log_s2_execution(
                out_dir=out_dir,
                run_tag=run_tag,
                arm=arm,
                group_id=gid,
                action="skipped",
                reason_skipped="no entities to process",
            )
        else:
            log_s2_execution(
                out_dir=out_dir,
                run_tag=run_tag,
                arm=arm,
                group_id=gid,
                action="complete",
                entities_total=total_entities,
                entities_processed=len(entities_out),
            )
    
    # Generate failure summary file if there are failures
    if failed_entities:
        failure_summary_path = out_dir / f"s2_failure_summary__arm{arm}.jsonl"
        try:
            with open(failure_summary_path, "a", encoding="utf-8") as f:
                for fe in failed_entities:
                    summary_rec = {
                        "run_tag": run_tag,
                        "arm": arm,
                        "group_id": gid,
                        "group_path": group_path,
                        "visual_type_category": s1_json.get("visual_type_category", "General"),
                        "entity_name": fe["entity_name"],
                        "entity_id": fe["entity_id"],
                        "entity_type": fe.get("entity_type", "unknown"),
                        "entity_index": fe["index"],
                        "error_type": _classify_error_type(fe["error"]),
                        "error_message": str(fe["error"])[:500],
                        "timestamp": now_ts(),
                    }
                    f.write(json.dumps(summary_rec, ensure_ascii=False) + "\n")
        except Exception as e:
            # Best-effort: log but don't fail the whole process
            print(f"  [WARN] Failed to write failure summary: {e}", flush=True)
    
    return record, None


# -------------------------
# CLI & ENTRYPOINT
# -------------------------

def _preflight_provider_model_guard(provider: str, model_stage1: str, model_stage2: str, arm: str) -> None:
    def _bad(pfx: str, name: str) -> bool:
        return bool(name) and name.startswith(pfx)

    if provider == "gpt":
        if _bad("gemini-", model_stage1) or _bad("gemini-", model_stage2):
            raise ValueError(f"[ARM {arm}] provider=gpt but model contains gemini-* (stage1={model_stage1}, stage2={model_stage2})")
        if _bad("claude-", model_stage1) or _bad("claude-", model_stage2):
            raise ValueError(f"[ARM {arm}] provider=gpt but model contains claude-* (stage1={model_stage1}, stage2={model_stage2})")
        if _bad("deepseek-", model_stage1) or _bad("deepseek-", model_stage2):
            raise ValueError(f"[ARM {arm}] provider=gpt but model contains deepseek-* (stage1={model_stage1}, stage2={model_stage2})")

    if provider == "gemini":
        if _bad("gpt-", model_stage1) or _bad("gpt-", model_stage2):
            raise ValueError(f"[ARM {arm}] provider=gemini but model contains gpt-* (stage1={model_stage1}, stage2={model_stage2})")
        if _bad("claude-", model_stage1) or _bad("claude-", model_stage2):
            raise ValueError(f"[ARM {arm}] provider=gemini but model contains claude-* (stage1={model_stage1}, stage2={model_stage2})")

    if provider == "claude":
        if _bad("gpt-", model_stage1) or _bad("gpt-", model_stage2) or _bad("gemini-", model_stage1) or _bad("gemini-", model_stage2):
            raise ValueError(f"[ARM {arm}] provider=claude but model contains gpt-/gemini-* (stage1={model_stage1}, stage2={model_stage2})")

    if provider == "deepseek":
        if _bad("gemini-", model_stage1) or _bad("gemini-", model_stage2) or _bad("claude-", model_stage1) or _bad("claude-", model_stage2):
            raise ValueError(f"[ARM {arm}] provider=deepseek but model contains gemini-/claude-* (stage1={model_stage1}, stage2={model_stage2})")


def load_processed_group_ids(output_paths: List[Path]) -> set[str]:
    """
    Load already processed group IDs from existing output files.
    
    Args:
        output_paths: List of output file paths to check (stage1_raw, stage1_struct, etc.)
    
    Returns:
        Set of group_id strings that have already been processed
    """
    processed_ids = set()
    
    for path in output_paths:
        if not path.exists():
            continue
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        # Extract group_id from various possible locations
                        group_id = None
                        if "metadata" in record and "id" in record["metadata"]:
                            group_id = record["metadata"]["id"]
                        elif "group_id" in record:
                            group_id = record["group_id"]
                        elif "source_info" in record and "group_id" in record["source_info"]:
                            group_id = record["source_info"]["group_id"]
                        
                        if group_id:
                            processed_ids.add(str(group_id))
                    except json.JSONDecodeError:
                        # Skip invalid JSON lines
                        continue
        except Exception as e:
            print(f"[RESUME] Warning: Could not read {path}: {e}", file=_sys.stderr)
            continue
    
    return processed_ids


def load_failed_group_ids(
    out_dir: Path,
    run_tag: str,
    arm: str,
    s1_arm: str,
    execute_s1: bool,
    execute_s2: bool,
    variant_suffix: str = "",
) -> set[str]:
    """
    Load failed group IDs from execution logs and output files.
    
    Args:
        out_dir: Output directory
        run_tag: Run tag
        arm: Arm for S2 (and S1 if execute_s1)
        s1_arm: Arm for reading S1 output (for S2-only mode)
        execute_s1: Whether S1 is being executed
        execute_s2: Whether S2 is being executed
    
    Returns:
        Set of group_id strings that have failed
    """
    failed_ids = set()
    
    # S2 failures: check s2_execution_log.jsonl
    if execute_s2:
        s2_log_path = out_dir / "logs" / "s2_execution_log.jsonl"
        if s2_log_path.exists():
            try:
                with open(s2_log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            log_entry = json.loads(line)
                            # Check if this log entry matches our run_tag and arm
                            if (log_entry.get("run_tag") == run_tag and 
                                log_entry.get("arm") == arm and
                                log_entry.get("action") == "failed"):
                                group_id = log_entry.get("group_id")
                                if group_id:
                                    failed_ids.add(str(group_id))
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                print(f"[RESUME-FAILED] Warning: Could not read S2 log {s2_log_path}: {e}", file=_sys.stderr)
    
    # S1 failures: check output files for errors or missing valid records
    if execute_s1:
        stage1_struct_path = out_dir / f"stage1_struct__arm{arm}{variant_suffix}.jsonl"
        stage1_raw_path = out_dir / f"stage1_raw__arm{arm}{variant_suffix}.jsonl"
        
        # Get all group IDs that have been attempted (from raw file)
        attempted_s1 = set()
        if stage1_raw_path.exists():
            try:
                with open(stage1_raw_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            group_id = None
                            if "metadata" in record and "id" in record["metadata"]:
                                group_id = record["metadata"]["id"]
                            elif "group_id" in record:
                                group_id = record["group_id"]
                            elif "source_info" in record and "group_id" in record["source_info"]:
                                group_id = record["source_info"]["group_id"]
                            
                            if group_id:
                                attempted_s1.add(str(group_id))
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                print(f"[RESUME-FAILED] Warning: Could not read S1 raw {stage1_raw_path}: {e}", file=_sys.stderr)
        
        # Get all group IDs that succeeded (from struct file)
        succeeded_s1 = set()
        if stage1_struct_path.exists():
            try:
                with open(stage1_struct_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            # Check if record is valid (has required fields)
                            # entity_list is at top level, not in curriculum_content
                            is_valid = (
                                "entity_list" in record and
                                isinstance(record["entity_list"], list) and
                                len(record["entity_list"]) > 0
                            )
                            
                            if is_valid:
                                group_id = None
                                if "metadata" in record and "id" in record["metadata"]:
                                    group_id = record["metadata"]["id"]
                                elif "group_id" in record:
                                    group_id = record["group_id"]
                                elif "source_info" in record and "group_id" in record["source_info"]:
                                    group_id = record["source_info"]["group_id"]
                                
                                if group_id:
                                    succeeded_s1.add(str(group_id))
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                print(f"[RESUME-FAILED] Warning: Could not read S1 struct {stage1_struct_path}: {e}", file=_sys.stderr)
        
        # S1 failed = attempted but not succeeded
        failed_s1 = attempted_s1 - succeeded_s1
        failed_ids.update(failed_s1)
    
    # S2 failures: also check s2_results file for groups with failed entities
    if execute_s2:
        s2_results_path = out_dir / f"s2_results__s1arm{s1_arm}__s2arm{arm}{variant_suffix}.jsonl"
        if s2_results_path.exists():
            try:
                with open(s2_results_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            # Check if this record has failed entities
                            metadata = record.get("metadata", {})
                            s2_gen = metadata.get("s2_generation", {})
                            failed_count = s2_gen.get("failed_entities", 0)
                            
                            # If all entities failed or record is invalid, mark as failed
                            total_entities = s2_gen.get("total_entities", 0)
                            if total_entities > 0 and failed_count >= total_entities:
                                group_id = None
                                if "metadata" in record and "id" in record["metadata"]:
                                    group_id = record["metadata"]["id"]
                                elif "group_id" in record:
                                    group_id = record["group_id"]
                                elif "source_info" in record and "group_id" in record["source_info"]:
                                    group_id = record["source_info"]["group_id"]
                                
                                if group_id:
                                    failed_ids.add(str(group_id))
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                print(f"[RESUME-FAILED] Warning: Could not read S2 results {s2_results_path}: {e}", file=_sys.stderr)
        
        # Check for groups with missing entities (partial failures) or completely missing groups
        # Compare S1 entity_list with S2 results to find groups with missing entities
        stage1_struct_path = out_dir / f"stage1_struct__arm{s1_arm}{variant_suffix}.jsonl"
        if stage1_struct_path.exists():
            # If S2 results file doesn't exist, all S1 groups are missing
            if not s2_results_path or not s2_results_path.exists():
                try:
                    with open(stage1_struct_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                record = json.loads(line)
                                group_id = None
                                if "metadata" in record and "id" in record["metadata"]:
                                    group_id = record["metadata"]["id"]
                                elif "group_id" in record:
                                    group_id = record["group_id"]
                                elif "source_info" in record and "group_id" in record["source_info"]:
                                    group_id = record["source_info"]["group_id"]
                                
                                if group_id:
                                    failed_ids.add(str(group_id))
                            except json.JSONDecodeError:
                                continue
                except Exception as e:
                    print(f"[RESUME-FAILED] Warning: Could not read S1 struct for missing groups: {e}", file=_sys.stderr)
            
            if s2_results_path and s2_results_path.exists():
                try:
                    # Load S1 entity lists by group
                    s1_entities_by_group: Dict[str, set[str]] = {}
                    with open(stage1_struct_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                record = json.loads(line)
                                group_id = None
                                if "metadata" in record and "id" in record["metadata"]:
                                    group_id = record["metadata"]["id"]
                                elif "group_id" in record:
                                    group_id = record["group_id"]
                                elif "source_info" in record and "group_id" in record["source_info"]:
                                    group_id = record["source_info"]["group_id"]
                                
                                if not group_id:
                                    continue
                                
                                # Extract entity names from entity_list
                                # entity_list is at top level, not in curriculum_content
                                entity_list = record.get("entity_list", [])
                                entity_names = set()
                                for e in entity_list:
                                    if isinstance(e, dict):
                                        name = str(e.get("entity_name", "") or e.get("name", "")).strip()
                                    else:
                                        name = str(e).strip()
                                    if name:
                                        # Normalize: remove asterisks for comparison
                                        normalized = re.sub(r'\*+', '', name).strip()
                                        if normalized:
                                            entity_names.add(normalized)
                                
                                if entity_names:
                                    s1_entities_by_group[str(group_id)] = entity_names
                            except json.JSONDecodeError:
                                continue
                    
                    # Load S2 entity names by group
                    s2_entities_by_group: Dict[str, set[str]] = {}
                    with open(s2_results_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                record = json.loads(line)
                                group_id = None
                                if "metadata" in record and "id" in record["metadata"]:
                                    group_id = record["metadata"]["id"]
                                elif "group_id" in record:
                                    group_id = record["group_id"]
                                elif "source_info" in record and "group_id" in record["source_info"]:
                                    group_id = record["source_info"]["group_id"]
                                
                                if not group_id:
                                    continue
                                
                                entity_name = str(record.get("entity_name", "")).strip()
                                if entity_name:
                                    # Normalize: remove asterisks for comparison
                                    normalized = re.sub(r'\*+', '', entity_name).strip()
                                    if normalized:
                                        if str(group_id) not in s2_entities_by_group:
                                            s2_entities_by_group[str(group_id)] = set()
                                        s2_entities_by_group[str(group_id)].add(normalized)
                            except json.JSONDecodeError:
                                continue
                    
                    # Find groups with missing entities or completely missing groups
                    for group_id, s1_entities in s1_entities_by_group.items():
                        s2_entities = s2_entities_by_group.get(group_id, set())
                        missing = s1_entities - s2_entities
                        if missing:
                            # Group has missing entities (partial failure) or completely missing (all entities missing)
                            failed_ids.add(group_id)
                except Exception as e:
                    print(f"[RESUME-FAILED] Warning: Could not compare S1/S2 for missing entities: {e}", file=_sys.stderr)
    
    return failed_ids


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_dir", default=".")
    # Parse base_dir first to load .env before other args
    args_base, _ = parser.parse_known_args()
    base_dir = Path(args_base.base_dir).resolve()
    
    # Load .env file from base_dir
    env_path = base_dir / ".env"
    if env_path.exists():
        # IMPORTANT: Do not override explicit process env (CLI prefix like VAR=1 python ...).
        # We want CLI env to take precedence; .env should only fill missing values.
        try:
            load_dotenv(dotenv_path=env_path, override=False)
        except PermissionError as e:
            # Some execution environments (sandbox) may block reading .env.
            # Continue with process environment only.
            print(f"⚠️  Warning: Cannot read .env file due to permissions: {e}", file=sys.stderr, flush=True)
    else:
        # Fallback: try to load from current directory
        load_dotenv()

    # Debug/trace: show effective env for rollout flags (helps catch .env override issues)
    print(
        # ENV logging suppressed for cleaner terminal output
        # Environment variables are logged to file if needed
        file=sys.stderr,
        flush=True,
    )
    
    parser.add_argument("--run_tag", required=True)
    parser.add_argument("--arm", default="A")
    parser.add_argument("--s1_arm", default=None,
                        help="Arm to use for reading S1 output (for S2 stage). Defaults to --arm if not specified. "
                             "Use this to run S2 with a different arm than S1 (e.g., --arm A --s1_arm E).")
    parser.add_argument("--mode", default="FINAL")
    parser.add_argument("--stage", default="both", choices=["1", "2", "both"],
                        help="Stage to execute: '1' (S1 only), '2' (S2 only), 'both' (S1+S2, default)")
    parser.add_argument("--sample", type=int, default=None,
                        help="Number of rows to process (default: None = all rows)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--row_index", type=int, default=None,
                        help="(1-based) Run exactly one row from groups_canonical.csv by its row index after filters.")
    parser.add_argument("--row_offset", type=int, default=0,
                        help="Skip the first N rows after filters, then apply --sample (default 1).")
    parser.add_argument("--only_group_id", action="append", default=[],
                        help="Run only the specified group_id (repeatable).")

    parser.add_argument("--only_group_key", action="append", default=[], help="Run only the specified group_key (repeatable).")
    parser.add_argument("--only_group_keys_file", default=None, help="Path to a text file with one group_key per line (comments with # allowed).")
    parser.add_argument("--resume", action="store_true", default=False,
                        help="Resume from previous run: skip already processed groups and append to existing output files.")
    parser.add_argument("--resume-failed", action="store_true", default=False,
                        help="Resume only failed groups: retry groups that failed in S1 or S2 (based on --stage). "
                             "Works with --stage to retry S1-only, S2-only, or both stages for failed groups.")

    # Option C (PR2): repaired output variant + repair-plan injection
    parser.add_argument(
        "--output_variant",
        default="baseline",
        choices=["baseline", "repaired"],
        help="Output variant. 'baseline' keeps existing filenames; 'repaired' writes to __repaired filenames (never overwrites baseline).",
    )
    parser.add_argument(
        "--repair_plan_path",
        default=None,
        help="Path to repair plan JSONL (e.g., s5_repair_plan__armX.jsonl). Used only with --output_variant repaired.",
    )

    # A안: 문제(=entity) 단위 재생성 (S2-only)
    parser.add_argument(
        "--only_entity_name",
        action="append",
        default=[],
        help="(S2-only) Run only the specified entity_name within the selected group(s) (repeatable).",
    )
    parser.add_argument(
        "--only_entity_id",
        action="append",
        default=[],
        help="(S2-only) Run only the specified entity_id within the selected group(s) (repeatable).",
    )
    parser.add_argument(
        "--only_entity_names_file",
        default=None,
        help="(S2-only) Path to a text file with one entity_name per line (comments with # allowed).",
    )
    
    # S1R: Table regeneration mode (preserves entity list and column structure)
    parser.add_argument(
        "--regen_mode",
        default=None,
        choices=["table_content_only"],
        help="Regeneration mode. 'table_content_only': Regenerate table content while preserving entity list and column structure.",
    )
    parser.add_argument(
        "--input_specs",
        default=None,
        help="Path to regeneration input specs JSONL (e.g., s1_regen_input__armG.jsonl). Required when --regen_mode is set.",
    )
    parser.add_argument(
        "--output_tag",
        default=None,
        help="Output tag suffix for regeneration (e.g., 's1r' -> stage1_struct__armG__s1r.jsonl). If not set, uses standard output names.",
    )
    
    # Read default workers from .env if available
    # Priority: WORKERS_S1 > WORKERS_S2 > WORKERS_S1_S2 > WORKERS
    default_workers_s1 = 1
    default_workers_s2 = 1
    default_workers_s2_entity = 1
    try:
        default_workers_s1 = int(os.getenv("WORKERS_S1", os.getenv("WORKERS_S1_S2", os.getenv("WORKERS", "1"))))
        default_workers_s2 = int(os.getenv("WORKERS_S2", os.getenv("WORKERS_S1_S2", os.getenv("WORKERS", "1"))))
        default_workers_s2_entity = int(os.getenv("WORKERS_S2_ENTITY", "1"))
    except (ValueError, TypeError):
        default_workers_s1 = 1
        default_workers_s2 = 1
        default_workers_s2_entity = 1
    
    # For backward compatibility, also support unified --workers
    parser.add_argument("--workers", type=int, default=None,
                        help=f"Parallel workers for group processing (applies to both S1 and S2 if --workers_s1/--workers_s2 not specified). "
                             f"Default: S1={default_workers_s1}, S2={default_workers_s2} from .env WORKERS_S1/WORKERS_S2/WORKERS_S1_S2/WORKERS, or 1.")
    parser.add_argument("--workers_s1", type=int, default=None,
                        help=f"Parallel workers for S1 stage (default: {default_workers_s1} from .env WORKERS_S1/WORKERS_S1_S2/WORKERS, or --workers, or 1).")
    parser.add_argument("--workers_s2", type=int, default=None,
                        help=f"Parallel workers for S2 stage (default: {default_workers_s2} from .env WORKERS_S2/WORKERS_S1_S2/WORKERS, or --workers, or 1).")
    parser.add_argument("--workers_s2_entity", type=int, default=None,
                        help=f"Parallel workers for entity-level processing within S2 stage (default: {default_workers_s2_entity} from .env WORKERS_S2_ENTITY, or 1). "
                             f"When > 1, entities within each group are processed in parallel.")

    args = parser.parse_args()

    # Reproducibility seed
    random.seed(args.seed)
    try:
        import numpy as np
        np.random.seed(args.seed)
    except Exception:
        pass

    base_dir = resolve_base_dir(args.base_dir)
    load_env(base_dir)

    bundle = load_prompt_bundle(str(base_dir))

    arm = (args.arm or "A").strip().upper()
    # S1 arm: for reading S1 output (defaults to S2 arm if not specified)
    s1_arm = (args.s1_arm or arm).strip().upper() if args.s1_arm else arm
    arm_cfg = ARM_CONFIGS.get(arm, {})
    validate_arm_cfg(arm_cfg)

    provider = (arm_cfg.get("provider") or os.getenv("DEFAULT_PROVIDER", "") or "gemini").strip().lower()
    if provider not in MODEL_CONFIG:
        raise ValueError(f"Unsupported provider: {provider}")

    model_stage1 = (arm_cfg.get("model_stage1") or MODEL_CONFIG[provider]["model_name"]).strip()
    model_stage2 = (arm_cfg.get("model_stage2") or MODEL_CONFIG[provider]["model_name"]).strip()
    _preflight_provider_model_guard(provider, model_stage1, model_stage2, arm)

    # Temperature (stage-wise). Allow per-arm override to keep Arm F deterministic.
    # MI-CLEAR-LLM: Fixed temperature for reproducibility (default 0.2 for all stages)
    temp_stage1 = float(arm_cfg.get("temp_stage1", env_float("TEMPERATURE_STAGE1", 0.2)))
    temp_stage2 = float(arm_cfg.get("temp_stage2", env_float("TEMPERATURE_STAGE2", 0.2)))
    timeout_s = env_int("TIMEOUT_S", 180)

    # CARDS_PER_ENTITY deprecated: pipeline policy is fixed at 2 cards per entity (Q1/Q2).
    # Keep the env read for backward compatibility, but default to 2 to match validator/prompt.
    cards_per_entity_default = env_int("CARDS_PER_ENTITY", 2)

    # S0 spread mode: hard|soft (v2.0)
    s0_spread_mode = (os.getenv("S0_SPREAD_MODE", "hard") or "hard").strip().lower()
    if s0_spread_mode not in {"hard", "soft"}:
        raise RuntimeError(f"Invalid S0_SPREAD_MODE='{s0_spread_mode}'. Must be 'hard' or 'soft'.")

    entity_list_cap = env_int("ENTITY_LIST_CAP", 50)

    # Option C (PR2): output variant + repair plan load (best-effort)
    output_variant = _normalize_output_variant(getattr(args, "output_variant", "baseline"))
    variant_suffix = _variant_suffix(output_variant)

    repair_plan_by_group_id: Dict[str, Dict[str, Any]] = {}
    repair_plan_by_group_key: Dict[str, Dict[str, Any]] = {}
    repair_plan_path = _resolve_path_maybe_relative_to_base_dir(getattr(args, "repair_plan_path", None), base_dir)
    if repair_plan_path and output_variant != "repaired":
        raise RuntimeError("--repair_plan_path is only supported with --output_variant repaired (to prevent baseline contamination).")
    if repair_plan_path:
        try:
            repair_plan_by_group_id, repair_plan_by_group_key = load_repair_plan_jsonl(repair_plan_path)
            print(f"[REPAIR PLAN] Loaded {len(repair_plan_by_group_id)} group(s) from {repair_plan_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to load repair plan JSONL: {repair_plan_path}: {e}")

    # A안: entity 단위 재생성 옵션 파싱 (S2-only)
    only_entity_names: set[str] = set()
    only_entity_ids: set[str] = set()
    if getattr(args, "only_entity_name", None):
        for n in (args.only_entity_name or []):
            nn = _normalize_entity_key(n)
            if nn:
                only_entity_names.add(nn)
    if getattr(args, "only_entity_names_file", None):
        pth = Path(args.only_entity_names_file)
        for line in pth.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            nn = _normalize_entity_key(s)
            if nn:
                only_entity_names.add(nn)
    if getattr(args, "only_entity_id", None):
        for eid in (args.only_entity_id or []):
            ee = str(eid).strip()
            if ee:
                only_entity_ids.add(ee)

    if (only_entity_names or only_entity_ids) and args.stage != "2":
        raise RuntimeError(
            "Entity-level regeneration requires S2-only mode. "
            "Please use --stage 2 (and typically also --only_group_id)."
        )

    # S1R: Load regeneration input specs (table_content_only mode)
    regen_mode = getattr(args, "regen_mode", None)
    input_specs_path = getattr(args, "input_specs", None)
    output_tag = getattr(args, "output_tag", None)
    regen_specs_by_group_id: Dict[str, Dict[str, Any]] = {}
    
    if regen_mode:
        if not input_specs_path:
            raise RuntimeError("--input_specs is required when --regen_mode is set")
        
        input_specs_path_resolved = _resolve_path_maybe_relative_to_base_dir(input_specs_path, base_dir)
        if not input_specs_path_resolved or not input_specs_path_resolved.exists():
            raise RuntimeError(f"Regeneration input specs file not found: {input_specs_path}")
        
        print(f"[S1R] Loading regeneration specs from: {input_specs_path_resolved}")
        try:
            with open(input_specs_path_resolved, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    spec = json.loads(line)
                    gid = spec.get("group_id")
                    if gid:
                        regen_specs_by_group_id[gid] = spec
            print(f"[S1R] Loaded {len(regen_specs_by_group_id)} regeneration specs")
            print(f"[S1R] Mode: {regen_mode}")
            if output_tag:
                print(f"[S1R] Output tag: {output_tag}")
        except Exception as e:
            raise RuntimeError(f"Failed to load regeneration specs: {e}")
        
        # S1R mode validation
        if regen_mode == "table_content_only":
            if args.stage not in ("1", "both"):
                print("[S1R] Warning: table_content_only mode typically runs S1 only. Consider using --stage 1")

    # Determine stage mode early (needed for path resolution)
    stage_mode = args.stage
    execute_s1 = stage_mode in ("1", "both")
    execute_s2 = stage_mode in ("2", "both")

    # Build output paths early (preflight uses it)
    out_dir = base_dir / "2_Data" / "metadata" / "generated" / args.run_tag
    # S1 output paths: use arm for writing (when executing S1), s1_arm for reading (when executing S2)
    # S2 output path: include both S1 arm and S2 arm to prevent overwrites when using different S1 arms
    # S1R: Add output_tag suffix if provided
    tag_suffix = f"__{output_tag}" if output_tag else ""
    stage1_raw_path = out_dir / f"stage1_raw__arm{arm}{tag_suffix}{variant_suffix}.jsonl"
    stage1_struct_path_for_writing = out_dir / f"stage1_struct__arm{arm}{tag_suffix}{variant_suffix}.jsonl"
    # A안(문제=entity 단위 재생성) 기본 원칙: S2는 baseline S1(master table)을 읽는다.
    # - output_variant=repaired 로 S2만 재생성할 때도, S1 read는 baseline을 유지해야 한다.
    # - (향후 필요 시) repaired S1을 읽는 옵션을 별도로 추가할 수 있다.
    stage1_struct_path_for_reading = out_dir / f"stage1_struct__arm{s1_arm}.jsonl"
    # S2 output filename includes S1 arm to prevent overwrites when same S2 arm uses different S1 arms
    s2_results_path = out_dir / f"s2_results__s1arm{s1_arm}__s2arm{arm}{variant_suffix}.jsonl"
    
    # Use appropriate path based on stage mode
    stage1_struct_path = stage1_struct_path_for_reading if stage_mode == "2" else stage1_struct_path_for_writing

    # Load input table early (preflight uses it)
    in_path = default_input_path(base_dir)
    df = read_input_table(in_path)

    # Initialize progress logger early (before rotator init, so we can log rotator init)
    progress_logger = None
    if ProgressLogger is not None:
        try:
            script_name = "s1_s2" if (execute_s1 and execute_s2) else ("s1" if execute_s1 else "s2")
            progress_logger = ProgressLogger(
                run_tag=args.run_tag,
                script_name=script_name,
                arm=arm,
                base_dir=base_dir,
            )
        except Exception as e:
            print(f"[WARN] Failed to initialize ProgressLogger: {e}", file=sys.stderr)
            progress_logger = None

    # Initialize API key rotator early (before preflight, so preflight can use it)
    # This matches S4's approach: initialize rotator early, then use it for API key checks
    global _global_rotator
    _global_rotator = None
    if provider == "gemini" and ApiKeyRotator is not None:
        try:
            # NOTE: Do NOT hard-cap max_keys here. ApiKeyRotator supports auto-detecting
            # all numbered keys present in the environment with no upper limit (e.g., GOOGLE_API_KEY_1, GOOGLE_API_KEY_2, ..., GOOGLE_API_KEY_19, ...).
            # Keys are automatically detected regardless of how many are present.
            _global_rotator = ApiKeyRotator(base_dir=base_dir, key_prefix="GOOGLE_API_KEY")
            # Log to file
            if progress_logger:
                progress_logger.debug(f"[API Rotator] Initialized with {len(_global_rotator.keys)} key(s)")
            # Also print to terminal (important initialization info)
            current_key_number = _global_rotator.key_numbers[_global_rotator._current_index]
            print(f"\n{'='*60}")
            print(f"[API Rotator] 🔑 API KEY: Starting with key index {_global_rotator._current_index} (GOOGLE_API_KEY_{current_key_number})")
            print(f"[API Rotator]    Total keys loaded: {len(_global_rotator.keys)}")
            print(f"{'='*60}\n")
        except Exception as e:
            if progress_logger:
                progress_logger.warning(f"[API Rotator] Failed to initialize rotator, using single key: {e}")
            else:
                print(f"[API Rotator] Warning: Failed to initialize rotator, using single key: {e}")
            _global_rotator = None

    # =========================
    # PREFLIGHT (Fail-Fast)
    # =========================
    preflight_prompt_bundle(bundle)
    preflight_s0_allocation(args.mode, s0_spread_mode)
    preflight_input_table(df)
    preflight_output_dir(out_dir)
    preflight_api_key(provider, MODEL_CONFIG, base_dir=base_dir, rotator=_global_rotator)
    
    # Now safe to init clients
    api_key_env = MODEL_CONFIG[provider]["api_key_env"]
    if _global_rotator is not None and provider == "gemini":
        api_key = _global_rotator.get_current_key()
        # Log to file (already printed to terminal during early initialization)
        if progress_logger:
            current_key_number = _global_rotator.key_numbers[_global_rotator._current_index]
            progress_logger.debug(f"[API Rotator] Using key index {_global_rotator._current_index} (GOOGLE_API_KEY_{current_key_number})")
    else:
        api_key = os.getenv(api_key_env, "").strip()
    clients = build_clients(provider, api_key, timeout_s=timeout_s)

    # Metrics sink (thread-safe) for quota/tokens/latency/429 visibility
    global _LLM_METRICS_PATH
    _LLM_METRICS_PATH = out_dir / "logs" / "llm_metrics.jsonl"

    # Per-stage quota limiters (RPM/TPM/RPD) - only for Gemini unless explicitly enabled.
    quota_s1 = None
    quota_s2 = None
    if provider == "gemini" and QuotaLimiter is not None and quota_from_env is not None:
        try:
            d_rpm1, d_tpm1, d_rpd1, env1 = _quota_defaults_for_model(model_stage1)
            d_rpm2, d_tpm2, d_rpd2, env2 = _quota_defaults_for_model(model_stage2)
            # Disable RPD tracking - we'll rely on API errors and auto key rotation instead
            # This avoids complexity with multiple models having different RPD limits per key
            cfg1 = quota_from_env(f"QUOTA_{env1}", default_rpm=d_rpm1, default_tpm=d_tpm1, default_rpd=None)
            cfg2 = quota_from_env(f"QUOTA_{env2}", default_rpm=d_rpm2, default_tpm=d_tpm2, default_rpd=None)
            quota_s1 = QuotaLimiter(
                name=f"S1:{model_stage1}",
                cfg=cfg1,
                rpd_persist_path=None,  # No RPD tracking - rely on API errors
            )
            quota_s2 = QuotaLimiter(
                name=f"S2:{model_stage2}",
                cfg=cfg2,
                rpd_persist_path=None,  # No RPD tracking - rely on API errors
            )
            if progress_logger:
                progress_logger.debug(f"[QUOTA] S1 quota: {quota_s1.snapshot()}")
                progress_logger.debug(f"[QUOTA] S2 quota: {quota_s2.snapshot()}")
            else:
                print(f"[QUOTA] S1 quota: {quota_s1.snapshot()}")
                print(f"[QUOTA] S2 quota: {quota_s2.snapshot()}")
        except Exception as e:
            if progress_logger:
                progress_logger.warning(f"[QUOTA] Failed to init quota limiters (continuing without): {e}")
            else:
                print(f"[QUOTA] Warning: Failed to init quota limiters (continuing without): {e}")
            quota_s1 = None
            quota_s2 = None

    rows = [normalize_row(r) for r in df.to_dict("records")]

    only_keys = set(args.only_group_key or [])
    if args.only_group_keys_file:
        pth = Path(args.only_group_keys_file)
        for line in pth.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            only_keys.add(s)

    if only_keys:
        rows = [r for r in rows if r.get("group_key") in only_keys]
        if not rows:
            raise RuntimeError(
                f"No rows matched only_keys (n={len(only_keys)}). "
                f"Check group_key spelling or file contents."
            )

    # Optional filtering by group_id (repeatable)
    only_ids = set(args.only_group_id or [])
    
    # S1R: If regen_mode is set, filter to only groups in regen_specs
    if regen_mode and regen_specs_by_group_id:
        regen_group_ids = set(regen_specs_by_group_id.keys())
        print(f"[S1R] Filtering to {len(regen_group_ids)} groups from regeneration specs")
        only_ids = only_ids.union(regen_group_ids) if only_ids else regen_group_ids
    
    if only_ids:
        rows = [r for r in rows if r.get("group_id") in only_ids]
        if not rows:
            raise RuntimeError(
                f"No rows matched only_group_id (n={len(only_ids)}). "
                f"Check group_id spelling or your filters."
            )

    # Row selection controls (applied after filters)
    if args.row_index is not None:
        if args.row_index < 1 or args.row_index > len(rows):
            raise RuntimeError(f"--row_index out of range: {args.row_index} (valid: 1..{len(rows)})")
        rows = [rows[args.row_index - 1]]
    else:
        if args.row_offset and args.row_offset > 0:
            if args.row_offset >= len(rows):
                raise RuntimeError(f"--row_offset {args.row_offset} removes all rows (n={len(rows)} after filters).")
            rows = rows[args.row_offset:]

        if args.sample is not None and args.sample > 0 and args.sample < len(rows):
            rows = rows[: args.sample]
    
    if stage_mode == "2" and not execute_s1:
        # S2 only: require existing S1 output
        if not stage1_struct_path.exists():
            s1_arm_note = f" (from arm {s1_arm})" if s1_arm != arm else ""
            raise RuntimeError(
                f"S2-only mode requires existing S1 output: {stage1_struct_path} not found{s1_arm_note}. "
                f"Run S1 with --arm {s1_arm} --stage 1 first, or use --s1_arm to specify a different S1 arm."
            )
        
        # Filter rows to only include groups that exist in S1 output
        available_s1_group_ids = set()
        available_s1_group_keys = set()
        try:
            with open(stage1_struct_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        s1_struct = json.loads(line)
                        gid_found = s1_struct.get("group_id")
                        if gid_found:
                            available_s1_group_ids.add(str(gid_found).strip())
                        key_found = s1_struct.get("group_key")
                        if key_found:
                            available_s1_group_keys.add(str(key_found).strip())
                    except Exception:
                        continue
        except Exception as e:
            raise RuntimeError(f"Failed to read S1 output file {stage1_struct_path}: {e}")
        
        if not available_s1_group_ids and not available_s1_group_keys:
            raise RuntimeError(f"S1 output file {stage1_struct_path} contains no valid groups.")
        
        # Filter rows to only include groups present in S1 output
        original_row_count = len(rows)
        rows = [
            r for r in rows 
            if (r.get("group_id") and str(r.get("group_id")).strip() in available_s1_group_ids)
            or (r.get("group_key") and str(r.get("group_key")).strip() in available_s1_group_keys)
        ]
        filtered_count = original_row_count - len(rows)
        if filtered_count > 0:
            print(f"[S2-ONLY] Filtered {filtered_count} groups without S1 output. Processing {len(rows)} groups with S1 data.")
        if not rows:
            raise RuntimeError(
                f"No groups from groups_canonical.csv match groups in S1 output. "
                f"S1 output has {len(available_s1_group_ids)} group_ids and {len(available_s1_group_keys)} group_keys."
            )
    
    # Log configuration (to file only)
    if progress_logger:
        progress_logger.debug(f"[RUN] provider={provider} arm={arm} run_tag={args.run_tag} mode={args.mode} stage={stage_mode}")
        if s1_arm != arm and stage_mode in ("2", "both"):
            progress_logger.debug(f"[RUN] S1 arm={s1_arm} (reading S1 output from arm {s1_arm}, executing S2 with arm {arm})")
        progress_logger.debug(f"[RUN] model_stage1={model_stage1} model_stage2={model_stage2}")
        progress_logger.debug(f"[RUN] S0_SPREAD_MODE={s0_spread_mode} ENTITY_LIST_CAP={entity_list_cap}")
        progress_logger.debug(f"[IN ] {in_path}")
        if execute_s1:
            progress_logger.debug(f"[OUT] stage1_raw={stage1_raw_path}")
            progress_logger.debug(f"[OUT] stage1_struct={stage1_struct_path_for_writing}")
        if execute_s2:
            progress_logger.debug(f"[OUT] s2_results={s2_results_path}")
            if not execute_s1:
                progress_logger.debug(f"[IN ] stage1_struct={stage1_struct_path_for_reading} (from arm {s1_arm})")
    else:
        print(f"[RUN] provider={provider} arm={arm} run_tag={args.run_tag} mode={args.mode} stage={stage_mode}")
        if s1_arm != arm and stage_mode in ("2", "both"):
            print(f"[RUN] S1 arm={s1_arm} (reading S1 output from arm {s1_arm}, executing S2 with arm {arm})")
        print(f"[RUN] model_stage1={model_stage1} model_stage2={model_stage2}")
        print(f"[RUN] S0_SPREAD_MODE={s0_spread_mode} ENTITY_LIST_CAP={entity_list_cap}")
        print(f"[IN ] {in_path}")
        if execute_s1:
            print(f"[OUT] stage1_raw={stage1_raw_path}")
            print(f"[OUT] stage1_struct={stage1_struct_path_for_writing}")
        if execute_s2:
            print(f"[OUT] s2_results={s2_results_path}")
            if not execute_s1:
                print(f"[IN ] stage1_struct={stage1_struct_path_for_reading} (from arm {s1_arm})")

    n_ok = 0
    n_fail = 0

    # Resume mode: load already processed group IDs
    processed_group_ids = set()
    failed_group_ids = set()
    
    if args.resume_failed:
        # Load failed group IDs
        failed_group_ids = load_failed_group_ids(
            out_dir=out_dir,
            run_tag=args.run_tag,
            arm=arm,
            s1_arm=s1_arm,
            execute_s1=execute_s1,
            execute_s2=execute_s2,
            variant_suffix=variant_suffix,
        )
        if failed_group_ids:
            print(f"[RESUME-FAILED] Found {len(failed_group_ids)} failed groups. Retrying them.")
        else:
            print(f"[RESUME-FAILED] No failed groups found. Nothing to retry.")
    
    if args.resume:
        output_paths_to_check = []
        if execute_s1:
            output_paths_to_check.extend([stage1_raw_path, stage1_struct_path_for_writing])
        if execute_s2:
            output_paths_to_check.append(s2_results_path)
        
        processed_group_ids = load_processed_group_ids(output_paths_to_check)
        if processed_group_ids:
            print(f"[RESUME] Found {len(processed_group_ids)} already processed groups. Skipping them.")
        else:
            print(f"[RESUME] No existing output files found. Starting fresh.")
    
    # Validate that --resume and --resume-failed are not both set
    if args.resume and args.resume_failed:
        raise RuntimeError("Cannot use both --resume and --resume-failed. Use --resume-failed to retry only failed groups.")

    # Open files conditionally based on stage mode and resume flag
    files_to_open = []
    file_mode = "a" if (args.resume or args.resume_failed) else "w"  # Append if resuming, write if starting fresh
    if execute_s1:
        files_to_open.append(("raw", stage1_raw_path, file_mode))
        files_to_open.append(("s1", stage1_struct_path_for_writing, file_mode))
    if execute_s2:
        files_to_open.append(("s2", s2_results_path, file_mode))
    
    # Use context manager for file handling
    from contextlib import ExitStack
    with ExitStack() as stack:
        file_handles = {}
        for name, path, mode in files_to_open:
            file_handles[name] = stack.enter_context(open(path, mode, encoding="utf-8"))
        
        f_raw = file_handles.get("raw")
        f_s1 = file_handles.get("s1")
        f_s2 = file_handles.get("s2")
        
        # Filter groups based on resume mode
        if args.resume_failed:
            # Only process failed groups
            if failed_group_ids:
                original_count = len(rows)
                rows = [r for r in rows if str(r.get("group_id", "")) in failed_group_ids]
                filtered_count = original_count - len(rows)
                if filtered_count > 0:
                    print(f"[RESUME-FAILED] Filtered {filtered_count} groups. Processing {len(rows)} failed groups.")
                if not rows:
                    print(f"[RESUME-FAILED] No failed groups to retry. Exiting.")
                    return
            else:
                print(f"[RESUME-FAILED] No failed groups found. Exiting.")
                return
        elif args.resume and processed_group_ids:
            # Skip already processed groups
            original_count = len(rows)
            rows = [r for r in rows if str(r.get("group_id", "")) not in processed_group_ids]
            skipped_count = original_count - len(rows)
            if skipped_count > 0:
                print(f"[RESUME] Skipping {skipped_count} already processed groups. Processing {len(rows)} remaining groups.")
        
        # Resolve worker counts with priority: explicit args > unified --workers > .env defaults > 1
        workers_unified = int(getattr(args, "workers", 0) or 0) if getattr(args, "workers", None) is not None else 0
        workers_s1_arg = int(getattr(args, "workers_s1", 0) or 0) if getattr(args, "workers_s1", None) is not None else 0
        workers_s2_arg = int(getattr(args, "workers_s2", 0) or 0) if getattr(args, "workers_s2", None) is not None else 0
        workers_s2_entity_arg = int(getattr(args, "workers_s2_entity", 0) or 0) if getattr(args, "workers_s2_entity", None) is not None else 0
        
        # Determine final worker counts (for logging/display purposes)
        # Note: Currently, S1 and S2 share the same worker pool (group-level parallelization)
        # Each group processes S1 then S2 sequentially, so we use the max of both for the pool size
        if workers_s1_arg > 0:
            workers_s1 = max(1, workers_s1_arg)
        elif workers_unified > 0:
            workers_s1 = max(1, workers_unified)
        else:
            workers_s1 = max(1, default_workers_s1)
        
        if workers_s2_arg > 0:
            workers_s2 = max(1, workers_s2_arg)
        elif workers_unified > 0:
            workers_s2 = max(1, workers_unified)
        else:
            workers_s2 = max(1, default_workers_s2)
        
        # Resolve entity-level workers for S2
        # If not explicitly set, default to 1 (will be auto-adjusted in process_single_group based on entity count)
        if workers_s2_entity_arg > 0:
            workers_s2_entity = max(1, workers_s2_entity_arg)
        else:
            # Use default from env, or 1 if not set
            # Note: Actual default (min(8, entity_count)) is calculated in process_single_group
            workers_s2_entity = max(1, default_workers_s2_entity)
        
        # Use maximum for actual worker pool (since each group does S1 then S2)
        # When only one stage is executed, use that stage's workers directly
        if execute_s1 and execute_s2:
            workers = max(workers_s1, workers_s2)
        elif execute_s1:
            workers = workers_s1
        elif execute_s2:
            workers = workers_s2
        else:
            workers = 1
        
        # Log worker configuration (to file and terminal - important initialization info)
        if execute_s1 and execute_s2:
            worker_info = f"S1: {workers_s1}, S2: {workers_s2}, S2-entity: {workers_s2_entity}, Group: {workers}"
            if progress_logger:
                progress_logger.debug(f"[WORKERS] {worker_info}")
            print(f"[WORKERS] {worker_info}")
        elif execute_s1:
            worker_info = f"S1: {workers_s1}, Group: {workers}"
            if progress_logger:
                progress_logger.debug(f"[WORKERS] {worker_info}")
            print(f"[WORKERS] {worker_info}")
        elif execute_s2:
            worker_info = f"S2: {workers_s2}, S2-entity: {workers_s2_entity}, Group: {workers}"
            if progress_logger:
                progress_logger.debug(f"[WORKERS] {worker_info}")
            print(f"[WORKERS] {worker_info}")

        # Writer locks (only needed for parallel mode; safe to create always)
        lock_s1 = threading.Lock()
        # stage1_struct is written inside workers; protect that handle if present.
        s1_writer = _LockedWriter(f_s1, lock_s1) if (f_s1 is not None and workers > 1) else f_s1
        
        def _run_one(r: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
            return process_single_group(
                r,
                base_dir=base_dir,
                provider=provider,
                clients=clients,
                arm=arm,
                arm_config=arm_cfg,
                bundle=bundle,
                run_tag=args.run_tag,
                mode=args.mode,
                model_stage1=model_stage1,
                model_stage2=model_stage2,
                temp_stage1=temp_stage1,
                temp_stage2=temp_stage2,
                timeout_s=timeout_s,
                cards_per_entity_default=cards_per_entity_default,
                s0_spread_mode=s0_spread_mode,
                entity_list_cap=entity_list_cap,
                out_dir=out_dir,
                stage1_struct_fh=s1_writer,
                execute_s1=execute_s1,
                execute_s2=execute_s2,
                s1_arm=s1_arm if stage_mode in ("2", "both") else None,
                quota_s1=quota_s1,
                quota_s2=quota_s2,
                workers_s2_entity=workers_s2_entity,
                progress_logger=progress_logger,
                resume_failed=args.resume_failed if execute_s2 else False,
                s2_results_path=s2_results_path if execute_s2 and args.resume_failed else None,
                output_variant=output_variant,
                repair_plan_by_group_id=repair_plan_by_group_id,
                repair_plan_by_group_key=repair_plan_by_group_key,
                only_entity_names=only_entity_names if (only_entity_names or only_entity_ids) else None,
                only_entity_ids=only_entity_ids if (only_entity_names or only_entity_ids) else None,
                regen_mode=regen_mode,
                regen_specs_by_group_id=regen_specs_by_group_id,
            )

        # Initialize group progress bar
        if progress_logger:
            progress_logger.init_group(len(rows), desc="[S1/S2] Processing groups")
        
        if workers <= 1:
            for idx, row in enumerate(rows, 1):
                try:
                    if progress_logger:
                        progress_logger.update_group(idx, len(rows), group_id=str(row.get('group_id', '') or '').strip())
                    
                    rec, err = _run_one(row)

                    if rec is not None:
                        if execute_s1 and f_raw is not None:
                            f_raw.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        if execute_s2 and f_s2 is not None:
                            write_s2_results_jsonl(
                                (rec.get("curriculum_content") or {}).get("entities"),
                                f_s2,
                                run_tag=args.run_tag,
                                arm=arm,
                                group_path=str(((rec.get("source_info") or {}).get("group_path") or "")),
                            )
                        n_ok += 1
                    else:
                        n_fail += 1
                        if progress_logger:
                            progress_logger.error(f"Group failed: {err}")
                        else:
                            print(f"❌ group failed: {err}", file=_sys.stderr)
                except Exception as e:
                    import traceback
                    error_msg = f"❌ Fatal error processing group: {str(e)}\n"
                    error_msg += f"Group: {row.get('group_id', 'unknown')} / {row.get('group_key', 'unknown')}\n"
                    error_msg += f"Traceback:\n{traceback.format_exc()}"
                    if progress_logger:
                        progress_logger.error(error_msg)
                    else:
                        print(error_msg, file=_sys.stderr)
                    n_fail += 1
                    if str(args.mode).upper() == "S0":
                        raise
        else:
            # Parallel: process groups concurrently; writes (raw + s2) are serialized in this main thread.
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futs = {ex.submit(_run_one, row): row for row in rows}
                completed_groups = 0
                for fut in as_completed(futs):
                    row = futs[fut]
                    completed_groups += 1
                    try:
                        if progress_logger:
                            progress_logger.update_group(completed_groups, len(rows), group_id=str(row.get('group_id', '') or '').strip())
                        
                        rec, err = fut.result()
                        if rec is not None:
                            if execute_s1 and f_raw is not None:
                                f_raw.write(json.dumps(rec, ensure_ascii=False) + "\n")
                            if execute_s2 and f_s2 is not None:
                                write_s2_results_jsonl(
                                    (rec.get("curriculum_content") or {}).get("entities"),
                                    f_s2,
                                    run_tag=args.run_tag,
                                    arm=arm,
                                    group_path=str(((rec.get("source_info") or {}).get("group_path") or "")),
                                )
                            n_ok += 1
                        else:
                            n_fail += 1
                            if progress_logger:
                                progress_logger.error(f"Group failed: {err}")
                            else:
                                print(f"❌ group failed: {err}", file=_sys.stderr)
                    except Exception as e:
                        import traceback
                        error_msg = f"❌ Fatal error processing group: {str(e)}\n"
                        error_msg += f"Group: {row.get('group_id', 'unknown')} / {row.get('group_key', 'unknown')}\n"
                        error_msg += f"Traceback:\n{traceback.format_exc()}"
                        if progress_logger:
                            progress_logger.error(error_msg)
                        else:
                            print(error_msg, file=_sys.stderr)
                        n_fail += 1
                        if str(args.mode).upper() == "S0":
                            raise
        
        # Close progress logger
        if progress_logger:
            progress_logger.close()

    print(f"[DONE] ok={n_ok} fail={n_fail}")
    
    # S2 completion verification: Check if all groups from S1 have S2 results
    if execute_s2 and stage1_struct_path.exists():
        try:
            # Load S1 groups
            s1_group_ids = set()
            with open(stage1_struct_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        s1_struct = json.loads(line)
                        gid = s1_struct.get("group_id")
                        if gid:
                            s1_group_ids.add(str(gid).strip())
                    except Exception:
                        continue
            
            # Load S2 groups
            s2_group_ids = set()
            if s2_results_path.exists():
                with open(s2_results_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            s2_result = json.loads(line)
                            gid = s2_result.get("group_id")
                            if gid:
                                s2_group_ids.add(str(gid).strip())
                        except Exception:
                            continue
            
            # Check for missing groups
            missing_groups = s1_group_ids - s2_group_ids
            if missing_groups:
                print(f"\n[WARNING] S2 completion check: {len(missing_groups)} groups from S1 are missing S2 results:", file=sys.stderr, flush=True)
                for gid in sorted(missing_groups):
                    print(f"  - {gid}", file=sys.stderr, flush=True)
                print(f"\n  Use generate_missing_entities_s2_s5.py to generate S2 cards for missing groups.", file=sys.stderr, flush=True)
            else:
                print(f"\n[VERIFY] S2 completion check: All {len(s1_group_ids)} S1 groups have S2 results. ✓", flush=True)
        except Exception as e:
            print(f"\n[WARNING] S2 completion check failed: {e}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        error_msg = f"Fatal error in main(): {type(e).__name__}: {str(e)}\n"
        error_msg += f"Traceback:\n{traceback.format_exc()}"
        print(error_msg, file=_sys.stderr)
        _sys.exit(1)

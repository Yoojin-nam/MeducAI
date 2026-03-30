"""
MeducAI Step04 (S4) — Image Generator

P0 Requirements:
- S4 consumes only s3_image_spec.jsonl for image generation
- Deterministic card mapping via filename: IMG__{run_tag}__{group_id}__{entity_id}__{card_role}.jpg
- Generate s4_image_manifest.jsonl with mapping
- Q1 image missing = FAIL-FAST before export

Design Principles:
- S4 is render-only (no medical interpretation)
- Deterministic filename mapping for card-to-image traceability
- Fail-fast on required image generation failures
- Uses Gemini image generation API (fixed model, arm-independent)
"""

import argparse
import base64
import hashlib
import io
import json
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from dotenv import load_dotenv

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# API Key Rotator (optional)
ApiKeyRotator = None
ROTATOR_AVAILABLE = False
try:
    import sys
    from pathlib import Path
    _THIS_DIR = Path(__file__).resolve().parent
    sys.path.insert(0, str(_THIS_DIR))
    from tools.api_key_rotator import ApiKeyRotator  # type: ignore
    ROTATOR_AVAILABLE = True
except Exception:
    # Rotator not available, continue without it
    pass

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google.genai not available. Image generation will be disabled.")

try:
    from tools.progress_logger import ProgressLogger
except ImportError:
    ProgressLogger = None

try:
    from tools.quota_limiter import QuotaLimiter, quota_from_env  # type: ignore
except Exception:
    QuotaLimiter = None  # type: ignore
    quota_from_env = None  # type: ignore

_S4_METRICS_LOCK = threading.Lock()

def _s4_append_metrics_jsonl(path: Path, rec: Dict[str, Any]) -> None:
    try:
        with _S4_METRICS_LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _as_opt_str(x: Any) -> Optional[str]:
    s = str(x or "").strip()
    return s if s else None


def _extract_exam_prompt_profile(image_spec: Dict[str, Any]) -> Optional[str]:
    return _as_opt_str(image_spec.get("exam_prompt_profile"))


def _extract_windowing_hint(image_spec: Dict[str, Any]) -> Optional[str]:
    # Primary: S3 attaches this into image_hint_v2.rendering_policy.windowing_hint (CT-only; may be absent)
    v2 = image_spec.get("image_hint_v2")
    if isinstance(v2, dict):
        rendering = v2.get("rendering_policy")
        if isinstance(rendering, dict):
            wh = _as_opt_str(rendering.get("windowing_hint"))
            return wh.lower() if wh else None

    # Fallbacks (older specs / future schema):
    wh2 = _as_opt_str(image_spec.get("windowing_hint"))
    return wh2.lower() if wh2 else None


def _constraint_block_hash(image_spec: Dict[str, Any]) -> Optional[str]:
    cb = image_spec.get("constraint_block")
    if not isinstance(cb, str):
        return None
    cb_norm = "\n".join([ln.rstrip() for ln in cb.strip().splitlines()]).strip()
    if not cb_norm:
        return None
    return hashlib.sha256(cb_norm.encode("utf-8")).hexdigest()[:16]


# =========================
# Output Variant (baseline vs repaired)
# =========================

def _normalize_output_variant(output_variant: str) -> str:
    v = (output_variant or "baseline").strip().lower()
    if v not in ("baseline", "repaired"):
        raise ValueError(f"Invalid output_variant='{output_variant}'. Must be 'baseline' or 'repaired'.")
    return v


def _variant_suffix(output_variant: str) -> str:
    return "" if _normalize_output_variant(output_variant) == "baseline" else "__repaired"


# =========================
# Filename Mapping (Deterministic)
# =========================

def make_image_filename(
    *,
    run_tag: str,
    group_id: str,
    entity_id: Optional[str] = None,
    card_role: Optional[str] = None,
    spec_kind: Optional[str] = None,
    cluster_id: Optional[str] = None,
    suffix: str = "",
) -> str:
    """
    P0: Deterministic filename mapping.
    
    For card images: IMG__{run_tag}__{group_id}__{entity_id}__{card_role}{suffix}.jpg
    For table visuals (single): IMG__{run_tag}__{group_id}__TABLE{suffix}.jpg
    For table visuals (clustered): IMG__{run_tag}__{group_id}__TABLE__{cluster_id}{suffix}.jpg
    
    Args:
        suffix: Optional suffix to add before extension (e.g., '_realistic', '_regen')
    """
    # Sanitize components (remove invalid filename chars)
    def sanitize(s: str) -> str:
        # Replace invalid chars with underscore
        invalid = '<>:"/\\|?*'
        for c in invalid:
            s = s.replace(c, '_')
        return s.strip()
    
    run_tag_safe = sanitize(str(run_tag))
    group_id_safe = sanitize(str(group_id))
    
    spec_kind = str(spec_kind or "").strip()
    if spec_kind == "S1_TABLE_VISUAL":
        # Table visual: include cluster_id if present
        if cluster_id:
            cluster_id_safe = sanitize(str(cluster_id))
            result = f"IMG__{run_tag_safe}__{group_id_safe}__TABLE__{cluster_id_safe}.jpg"
        else:
            result = f"IMG__{run_tag_safe}__{group_id_safe}__TABLE.jpg"
    else:
        # Card image: requires entity_id and card_role
        entity_id_safe = sanitize(str(entity_id or ""))
        card_role_safe = sanitize(str(card_role or "").upper())
        result = f"IMG__{run_tag_safe}__{group_id_safe}__{entity_id_safe}__{card_role_safe}.jpg"
    
    # Add suffix before extension if provided
    if suffix:
        base_name, ext = result.rsplit('.', 1)
        return f"{base_name}{suffix}.{ext}"
    return result


# =========================
# Image Generation Configuration
# =========================

# P0: Fixed image model (arm-independent, per S4_Image_Cost_and_Resolution_Policy)
# Default model: models/nano-banana-pro-preview (Gemini 3 Pro Image Preview / Nano Banana Pro Preview)
# Alternative: models/gemini-2.5-flash-image (Nano Banana, faster but lower quality)
# Can be overridden via S4_IMAGE_MODEL env var or --image_model CLI option
# Model aliases for convenience:
#   "nano-banana-pro" or "pro" -> "models/nano-banana-pro-preview"
#   "nano-banana" or "banana" -> "models/gemini-2.5-flash-image"
IMAGE_MODEL_DEFAULT = os.getenv("S4_IMAGE_MODEL", "models/nano-banana-pro-preview")

def resolve_image_model(model_arg: Optional[str] = None) -> str:
    """
    Resolve image model from CLI argument, env var, or default.
    
    Supports aliases:
    - "nano-banana-pro" or "pro" -> "models/nano-banana-pro-preview"
    - "nano-banana" or "banana" -> "models/gemini-2.5-flash-image"
    
    Args:
        model_arg: CLI argument value (None if not provided)
    
    Returns:
        Full model name (e.g., "models/nano-banana-pro-preview")
    """
    # CLI argument takes precedence
    if model_arg:
        model_arg = model_arg.strip().lower()
        # Map aliases to full model names
        alias_map = {
            "nano-banana-pro": "models/nano-banana-pro-preview",
            "pro": "models/nano-banana-pro-preview",
            "nano-banana": "models/gemini-2.5-flash-image",
            "banana": "models/gemini-2.5-flash-image",
            "gemini-3-pro-image": "models/nano-banana-pro-preview",  # Map to nano-banana-pro
            "pro-image": "models/nano-banana-pro-preview",
        }
        if model_arg in alias_map:
            return alias_map[model_arg]
        # If it's already a full model name, return as-is
        if model_arg.startswith("models/"):
            return model_arg
        # Otherwise, assume it's an alias and try to map
        return model_arg
    
    # Fall back to env var or default
    return IMAGE_MODEL_DEFAULT
IMAGE_ASPECT_RATIO = "4:5"  # S4_EXAM: 4:5 aspect ratio (for card images)
# Card image size: default 2K (2048×2560) for EXAM cards, matching S4_EXAM prompt intent
# Can be overridden via S4_CARD_IMAGE_SIZE env var (values: "1K", "2K")
# Backward compatibility: S4_IMAGE_SIZE env var takes precedence if set
S4_CARD_IMAGE_SIZE = os.getenv("S4_CARD_IMAGE_SIZE", os.getenv("S4_IMAGE_SIZE", "2K")).strip()
# Flash/entity-only images (if needed in future) can use separate size
S4_FLASH_IMAGE_SIZE = os.getenv("S4_FLASH_IMAGE_SIZE", "1K").strip()
# Legacy: IMAGE_SIZE for backward compatibility (deprecated, use S4_CARD_IMAGE_SIZE)
IMAGE_SIZE = S4_CARD_IMAGE_SIZE
# Table visual settings (can be overridden per spec)
TABLE_ASPECT_RATIO = "16:9"  # Wider for table visuals
TABLE_SIZE = "4K"  # 4K resolution for table visuals (3840×2160, sufficient for high-quality digital viewing and PDF)

# Temperature for image generation (MI-CLEAR-LLM: Fixed for reproducibility)
# Can be overridden via TEMPERATURE_STAGE4 env var
def _env_float(name: str, default: float) -> float:
    """Read float from environment variable."""
    try:
        return float(os.getenv(name, str(default)).strip())
    except Exception:
        return default

def _env_bool(name: str, default: bool) -> bool:
    """Read boolean from environment variable."""
    val = os.getenv(name, "").strip().lower()
    if val in ("1", "true", "yes", "on"):
        return True
    elif val in ("0", "false", "no", "off", ""):
        return False
    return default

IMAGE_TEMPERATURE = _env_float("TEMPERATURE_STAGE4", 0.2)

# Optional: separate temperature for REALISTIC(EXAM) prompts.
# If set, REALISTIC specs will use this temperature instead of TEMPERATURE_STAGE4.
# Keeping this opt-in avoids changing default behavior unexpectedly.
IMAGE_TEMPERATURE_REALISTIC = _env_float("S4_IMAGE_TEMPERATURE_REALISTIC", IMAGE_TEMPERATURE)

# RAG setting (default: OFF for S4 render-only principle)
# When enabled, uses Google Search to augment prompts before image generation
S4_RAG_ENABLED = _env_bool("S4_RAG_ENABLED", False)

# API key
GEMINI_API_KEY_ENV = "GOOGLE_API_KEY"

# Global rotator instance (initialized per process)
_global_rotator: Optional[Any] = None


# =========================
# Batch Tracking Check (for skipping batch-submitted entities)
# =========================

def get_batch_tracking_file_path(base_dir: Path) -> Path:
    """배치 추적 파일 경로를 반환합니다."""
    return base_dir / "2_Data" / "metadata" / ".batch_tracking.json"

def load_batch_tracking_file(tracking_path: Path) -> Dict[str, Any]:
    """
    배치 작업 추적 파일을 로드합니다.
    """
    if not tracking_path.exists():
        return {
            "schema_version": "BATCH_TRACKING_v1.0",
            "batches": {},
            "last_updated": "",
        }
    
    try:
        with open(tracking_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "schema_version" not in data:
                data["schema_version"] = "BATCH_TRACKING_v1.0"
            if "batches" not in data:
                data["batches"] = {}
            return data
    except Exception:
        return {
            "schema_version": "BATCH_TRACKING_v1.0",
            "batches": {},
            "last_updated": "",
        }


def is_prompt_in_batch(
    image_spec: Dict[str, Any],
    tracking_data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    이미지 스펙이 배치로 이미 제출되었는지 확인합니다.
    
    Returns:
        배치 정보 (제출되었으면), None (제출되지 않았으면)
    """
    prompt_en = image_spec.get("prompt_en", "").strip()
    if not prompt_en:
        return None
    
    # Calculate prompt hash
    prompt_hash = hashlib.sha256(prompt_en.encode("utf-8")).hexdigest()[:16]
    
    run_tag = str(image_spec.get("run_tag", "")).strip()
    group_id = str(image_spec.get("group_id", "")).strip()
    entity_id = image_spec.get("entity_id")
    card_role = image_spec.get("card_role")
    spec_kind = str(image_spec.get("spec_kind", "")).strip()
    
    batches = tracking_data.get("batches", {})
    
    # Check all API keys
    for api_key_str, api_batches in batches.items():
        if not isinstance(api_batches, dict):
            continue
        
        chunks = api_batches.get("chunks", [])
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
            
            # Check if chunk has prompts_metadata (new format)
            prompts_metadata = chunk.get("prompts_metadata", [])
            if prompts_metadata:
                # New format: check individual prompt metadata
                for prompt_meta in prompts_metadata:
                    if (
                        prompt_meta.get("prompt_hash") == prompt_hash
                        and prompt_meta.get("run_tag", "").strip() == run_tag
                        and prompt_meta.get("group_id", "").strip() == group_id
                        and prompt_meta.get("entity_id") == entity_id
                        and prompt_meta.get("card_role") == card_role
                        and prompt_meta.get("spec_kind", "").strip() == spec_kind
                    ):
                        # Found matching prompt in batch
                        status = chunk.get("status", "")
                        # Skip if batch is pending, running, or succeeded
                        if status in ("JOB_STATE_PENDING", "JOB_STATE_RUNNING", "JOB_STATE_SUCCEEDED"):
                            return {
                                "batch_id": chunk.get("batch_id", ""),
                                "status": status,
                                "api_key": api_key_str,
                            }
            else:
                # Old format: check prompts_hash (less precise, but still useful)
                # This is a fallback for older tracking files
                prompts_hash = api_batches.get("prompts_hash", "")
                if prompts_hash:
                    # Calculate hash of current prompt and check if it might be in the batch
                    # This is less precise but can still help avoid duplicates
                    chunk_status = chunk.get("status", "")
                    if chunk_status in ("JOB_STATE_PENDING", "JOB_STATE_RUNNING", "JOB_STATE_SUCCEEDED"):
                        # For old format, we can't be 100% sure, but we can warn
                        # Return None to allow processing (conservative approach)
                        pass
    
    return None


# =========================
# CONCEPT Preamble Loading
# =========================

def load_concept_preamble(base_dir: Path) -> str:
    """
    Load CONCEPT preamble text from file.
    
    Args:
        base_dir: Base directory (repo root)
    
    Returns:
        Preamble text string (default fallback if file not found)
    """
    default_preamble = (
        "You are generating ONE educational concept diagram (not a clinical PACS image). "
        "Short labels and axis titles are allowed. "
        "No patient info, no watermark, no brand logos, no long paragraphs. "
        "Single panel only.\n\n"
    )
    
    # Try to load from prompt directory
    try:
        prompt_dir = base_dir / "3_Code" / "prompt"
        preamble_path = prompt_dir / "S4_CONCEPT_PREAMBLE__v1.txt"
        if preamble_path.exists():
            preamble_text = preamble_path.read_text(encoding="utf-8").strip()
            if preamble_text:
                return preamble_text + "\n\n"
    except Exception as e:
        print(f"[S4] Warning: Could not load CONCEPT preamble file: {e}. Using default.")
    
    return default_preamble


# =========================
# TABLE VISUAL Safety Preambles
# =========================

def load_anatomy_safe_table_preamble(base_dir: Path) -> str:
    """
    Load a safety preamble for Anatomy_Map table visuals.

    Purpose:
    - Prevent misleading/incorrect anatomy drawings by forcing an abstract, segmented region map.
    - Encourage diagram/slide aesthetics (not photorealistic anatomy, not PACS-like scans).

    Note:
    - We intentionally keep this short and style-focused.
    - We do NOT inject medical facts; this is only a rendering constraint.
    """
    # Optional external override (so teams can tweak without code changes)
    try:
        prompt_dir = base_dir / "3_Code" / "prompt"
        preamble_path = prompt_dir / "S4_ANATOMY_SAFE_TABLE_PREAMBLE__v1.txt"
        if preamble_path.exists():
            txt = preamble_path.read_text(encoding="utf-8").strip()
            if txt:
                return txt + "\n\n"
    except Exception as e:
        print(f"[S4] Warning: Could not load anatomy-safe table preamble file: {e}. Using default.")

    return (
        "You are generating ONE educational teaching slide diagram (not a clinical scan, not a realistic anatomy drawing). "
        "SAFETY FIRST: Do NOT draw detailed organs/vessels/bones. "
        "Use ONLY abstract silhouettes and simple segmented regions (4–9 segments) with leader lines/callouts. "
        "If anatomy is uncertain, keep it abstract and do NOT guess.\n\n"
    )


# =========================
# Image Generation
# =========================

def build_gemini_client(api_key: str):
    """Build Gemini client for image generation."""
    if not GEMINI_AVAILABLE:
        raise RuntimeError("google.genai not available. Install: pip install google-genai")
    return genai.Client(api_key=api_key)


def extract_image_from_response(resp) -> Optional[bytes]:
    """Extract image bytes from Gemini response."""
    def _try_parts(parts):
        """Try to extract image from parts list."""
        if not parts:
            return None
        for part in parts:
            # Try both inline_data and inlineData (case variations)
            inline = getattr(part, "inline_data", None) or getattr(part, "inlineData", None)
            if inline and getattr(inline, "data", None):
                data = inline.data
                # Check if already bytes
                if isinstance(data, (bytes, bytearray)):
                    return bytes(data)
                # Try base64 decode
                try:
                    decoded = base64.b64decode(data)
                    return decoded
                except Exception as e:
                    print(f"[S4] Warning: Failed to decode base64 data: {e}")
                    pass
        return None
    
    try:
        # Method 1: Try response.candidates[0].content.parts (most common, per archived code)
        try:
            cand0 = resp.candidates[0]
            parts = cand0.content.parts
            result = _try_parts(parts)
            if result:
                return result
        except (AttributeError, IndexError, KeyError) as e:
            print(f"[S4] Debug: Method 1 failed: {e}")
        
        # Method 2: Try direct response.parts
        try:
            parts = getattr(resp, "parts", [])
            result = _try_parts(parts)
            if result:
                return result
        except Exception as e:
            print(f"[S4] Debug: Method 2 failed: {e}")
        
        # Method 3: Debug - print response structure for troubleshooting
        print(f"[S4] Warning: Could not extract image. Response type: {type(resp)}")
        print(f"[S4] Response has candidates: {hasattr(resp, 'candidates')}")
        if hasattr(resp, "candidates"):
            print(f"[S4] Candidates count: {len(resp.candidates) if resp.candidates else 0}")
            if resp.candidates:
                cand = resp.candidates[0]
                print(f"[S4] Candidate type: {type(cand)}")
                print(f"[S4] Candidate has content: {hasattr(cand, 'content')}")
                if hasattr(cand, "content"):
                    print(f"[S4] Content type: {type(cand.content)}")
                    print(f"[S4] Content has parts: {hasattr(cand.content, 'parts')}")
                    if hasattr(cand.content, "parts"):
                        print(f"[S4] Parts count: {len(cand.content.parts) if cand.content.parts else 0}")
        
    except Exception as e:
        print(f"[S4] Error extracting image: {e}")
        import traceback
        traceback.print_exc()
    return None


def generate_image(
    *,
    image_spec: Dict[str, Any],
    output_path: Path,
    client: Any = None,
    rag_enabled: bool = False,
    max_retries: int = 3,
    retry_delay: float = 2.0,
    base_dir: Optional[Path] = None,
    image_model: Optional[str] = None,
    quota_limiter: Optional[Any] = None,
    metrics_path: Optional[Path] = None,
    run_tag: Optional[str] = None,
) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    """
    Generate image from spec using Gemini image generation API.
    
    Args:
        image_spec: S3 image spec dict with prompt_en and spec_kind
        output_path: Output image file path
        client: Gemini client (if None, will create one)
        rag_enabled: Whether to use RAG (Google Search) to augment prompts (default: False)
        max_retries: Maximum number of retries for transient errors (default: 3)
        retry_delay: Delay between retries in seconds (default: 2.0)
    
    Returns:
        (success: bool, metadata: dict, actual_filename: None) - success status, RAG metadata, and filename (None since we keep original)
    """
    global _global_rotator  # Declare at function start for key rotation
    
    # RAG metadata (always returned for logging)
    rag_meta = {
        "rag_enabled": bool(rag_enabled),
        "rag_queries_count": 0,
        "rag_sources_count": 0,
    }
    
    if not GEMINI_AVAILABLE:
        print(f"[S4] Warning: Image generation disabled (google.genai not available)")
        return False, rag_meta, None
    
    prompt_en = image_spec.get("prompt_en", "")
    if not prompt_en:
        print(f"[S4] Error: Missing prompt_en in image_spec")
        return False, rag_meta, None
    
    try:
        # Build client if not provided
        if client is None:
            api_key = os.getenv(GEMINI_API_KEY_ENV, "").strip()
            if not api_key:
                print(f"[S4] Error: Missing API key ({GEMINI_API_KEY_ENV})")
                return False, rag_meta, None
            client = build_gemini_client(api_key)
        
        # RAG: Fail-fast if enabled (not implemented)
        if rag_enabled:
            raise RuntimeError(
                "RAG augmentation not implemented; disable S4_RAG_ENABLED flag. "
                "S4 is render-only and does not support RAG augmentation."
            )
        
        # Determine aspect ratio and size based on spec_kind
        spec_kind = str(image_spec.get("spec_kind", "S2_CARD_IMAGE")).strip()
        if spec_kind == "S1_TABLE_VISUAL":
            aspect_ratio = TABLE_ASPECT_RATIO
            image_size = TABLE_SIZE
        else:
            # Default to card image settings (S2_CARD_IMAGE and S2_CARD_CONCEPT both use 4:5/2K by default)
            aspect_ratio = IMAGE_ASPECT_RATIO
            image_size = S4_CARD_IMAGE_SIZE

        # Apply safety/style preamble for Anatomy_Map table visuals
        # This is intentionally style-only (no extra medical facts), to reduce misleading anatomy.
        if spec_kind == "S1_TABLE_VISUAL":
            vcat = str(image_spec.get("visual_type_category") or "").strip()
            if vcat == "Anatomy_Map":
                try:
                    if base_dir is None:
                        inferred_base = Path.cwd()
                        for parent in inferred_base.parents:
                            if (parent / "3_Code" / "prompt").exists():
                                inferred_base = parent
                                break
                        base_dir = inferred_base
                    prompt_en = load_anatomy_safe_table_preamble(base_dir) + prompt_en
                except Exception as e:
                    print(f"[S4] Warning: Could not apply anatomy-safe table preamble: {e}")
        
        # Apply CONCEPT preamble for S2_CARD_CONCEPT specs
        if spec_kind == "S2_CARD_CONCEPT":
            # Load preamble (use provided base_dir or try to infer from current directory)
            try:
                if base_dir is None:
                    # Try to infer base_dir from current working directory
                    inferred_base = Path.cwd()
                    # Check if we can find repo root
                    for parent in inferred_base.parents:
                        if (parent / "3_Code" / "prompt").exists():
                            inferred_base = parent
                            break
                    base_dir = inferred_base
                preamble = load_concept_preamble(base_dir)
                prompt_en = preamble + prompt_en
            except Exception as e:
                print(f"[S4] Warning: Could not load CONCEPT preamble, using prompt as-is: {e}")
                # Continue with original prompt_en
        
        # Resolve image model (use provided model or fall back to default)
        actual_model = resolve_image_model(image_model) if image_model else resolve_image_model()

        # Temperature: optionally use a separate temperature for REALISTIC(EXAM) prompts
        # to reduce over-creative outputs (exaggeration/anatomy errors).
        effective_temp = IMAGE_TEMPERATURE
        try:
            exam_profile = _as_opt_str(image_spec.get("exam_prompt_profile"))
            if exam_profile and ("realistic" in exam_profile.lower() or "pacs" in exam_profile.lower()):
                effective_temp = IMAGE_TEMPERATURE_REALISTIC
        except Exception:
            effective_temp = IMAGE_TEMPERATURE
        
        # Generate image using Gemini with retry logic for transient errors
        # MI-CLEAR-LLM: Include temperature for reproducibility
        # Note: gemini-2.5-flash-image (nano-banana) does NOT support image_size parameter
        # Only gemini-3-pro-image-preview (nano-banana-pro) supports image_size
        # gemini-2.5-flash-image resolution varies by aspect_ratio (e.g., 4:5=896x1152, 16:9=1344x768, 1:1=1024x1024)
        model_lc = actual_model.lower()
        is_nano_banana = "gemini-2.5-flash-image" in model_lc
        if is_nano_banana:
            # Nano Banana: aspect_ratio only, no image_size (resolution determined by aspect_ratio)
            config = types.GenerateContentConfig(
                temperature=effective_temp,
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                )
            )
        else:
            # Nano Banana Pro: both aspect_ratio and image_size
            config = types.GenerateContentConfig(
                temperature=effective_temp,
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                )
            )
        
        # Retry logic for transient errors (503, 429, etc.)
        response = None
        key_rotated_this_attempt = False  # Track if we rotated keys in this attempt
        consecutive_429_rate_limits = 0  # Track consecutive 429 rate limit errors (for key rotation)
        MAX_CONSECUTIVE_429_FOR_ROTATION = 2  # Rotate keys after this many consecutive 429 rate limits

        # Enrich metrics with constraint/windowing metadata for post-hoc analysis (from S3 spec).
        exam_prompt_profile = _extract_exam_prompt_profile(image_spec)
        windowing_hint = _extract_windowing_hint(image_spec)
        constraint_block_hash = _constraint_block_hash(image_spec)
        
        for attempt in range(max_retries):
            try:
                # Global quota limiting (RPM/TPM only - RPD tracking disabled)
                # Skip quota check if we just rotated keys (quota_limiter is for old key)
                if quota_limiter is not None and not key_rotated_this_attempt:
                    # Image requests are mostly prompt-sized; use a conservative small estimate.
                    est_tokens = max(100, int(len(prompt_en) / 4))
                    try:
                        quota_limiter.acquire_request(estimated_tokens=est_tokens, rpd_cost=0)  # RPD disabled
                    except RuntimeError as quota_err:
                        # Should not happen for RPM/TPM, but if it does, treat as transient
                        error_str_quota = str(quota_err)
                        print(f"[S4] Quota limit exceeded (RPM/TPM): {error_str_quota}")
                        # Wait a bit and retry (RPM/TPM are rolling windows)
                        time.sleep(2.0)
                        continue
                key_rotated_this_attempt = False  # Reset flag after quota check
                t0 = time.perf_counter()
                filename_short = str(output_path.name) if output_path else "image"
                # API call logging suppressed for cleaner terminal output
                # Logs are still available in metrics file
                response = client.models.generate_content(
                    model=actual_model,
                    contents=[prompt_en],
                    config=config,
                )
                elapsed = time.perf_counter() - t0
                # API response logging suppressed for cleaner terminal output
                if metrics_path is not None:
                    # MI-CLEAR-LLM: Include all required metadata for reproducibility
                    prompt_hash = hashlib.sha256(prompt_en.encode("utf-8")).hexdigest()[:16]
                    metrics_rec = {
                        "ts": int(time.time()),
                        "ok": True,
                        "run_tag": run_tag or str(image_spec.get("run_tag", "")),
                        "model": actual_model,
                        "spec_kind": str(image_spec.get("spec_kind", "")),
                        "group_id": str(image_spec.get("group_id", "")),
                        "entity_id": image_spec.get("entity_id"),
                        "card_role": image_spec.get("card_role"),
                        "exam_prompt_profile": exam_prompt_profile,
                        "windowing_hint": windowing_hint,
                        "constraint_block_hash": constraint_block_hash,
                        "latency_sec": round(time.perf_counter() - t0, 6),
                        "generation_config": {
                            "temperature": effective_temp,
                            "aspect_ratio": aspect_ratio,
                            "image_size": image_size if not is_nano_banana else None,
                        },
                        "prompt_hash": prompt_hash,
                        "prompt_length": len(prompt_en),
                        "estimated_input_tokens": est_tokens,
                        "rag_enabled": rag_enabled,
                        "quota": quota_limiter.snapshot() if quota_limiter is not None else None,
                    }
                    _s4_append_metrics_jsonl(metrics_path, metrics_rec)
                # Reset consecutive 429 counter on success
                consecutive_429_rate_limits = 0
                break  # Success, exit retry loop
            except Exception as e:
                error_str = str(e)
                error_str_lower = error_str.lower()
                if quota_limiter is not None:
                    try:
                        if "429" in error_str_lower or "too many requests" in error_str_lower or "rate limit" in error_str_lower:
                            quota_limiter.note_429()
                    except Exception:
                        pass
                if metrics_path is not None:
                    # MI-CLEAR-LLM: Include all required metadata even for failures
                    prompt_hash = hashlib.sha256(prompt_en.encode("utf-8")).hexdigest()[:16] if prompt_en else None
                    metrics_rec = {
                        "ts": int(time.time()),
                        "ok": False,
                        "run_tag": run_tag or str(image_spec.get("run_tag", "")),
                        "model": actual_model,
                        "spec_kind": str(image_spec.get("spec_kind", "")),
                        "group_id": str(image_spec.get("group_id", "")),
                        "entity_id": image_spec.get("entity_id"),
                        "card_role": image_spec.get("card_role"),
                        "exam_prompt_profile": exam_prompt_profile,
                        "windowing_hint": windowing_hint,
                        "constraint_block_hash": constraint_block_hash,
                        "error": error_str[:500],
                        "generation_config": {
                            "temperature": effective_temp,
                            "aspect_ratio": aspect_ratio,
                            "image_size": image_size if not is_nano_banana else None,
                        },
                        "prompt_hash": prompt_hash,
                        "prompt_length": len(prompt_en) if prompt_en else None,
                        "estimated_input_tokens": est_tokens if "est_tokens" in locals() else None,
                        "rag_enabled": rag_enabled,
                        "attempt": attempt + 1,
                        "quota": quota_limiter.snapshot() if quota_limiter is not None else None,
                    }
                    _s4_append_metrics_jsonl(metrics_path, metrics_rec)
                
                # Improved distinction between quota exhaustion (permanent) and rate limiting (temporary)
                # Quota exhaustion indicators (non-retryable, requires key rotation):
                # - "quota exceeded"
                # - "exceeded your current quota"
                # - 429 with "limit: 0" (RPD quota exhausted)
                # - "resource_exhausted" with 429 (general quota exhausted)
                # - "resource has been exhausted"
                is_quota_exhausted = (
                    "quota exceeded" in error_str_lower or
                    "exceeded your current quota" in error_str_lower or
                    ("429" in error_str and "limit: 0" in error_str_lower) or
                    ("429" in error_str and "resource_exhausted" in error_str_lower) or
                    "resource has been exhausted" in error_str_lower
                )
                
                # Check if it's an invalid API key error (400 INVALID_ARGUMENT)
                is_invalid_key = (
                    "400" in error_str or
                    "INVALID_ARGUMENT" in error_str or
                    "api key not valid" in error_str_lower or
                    "invalid api key" in error_str_lower
                )
                
                # Check if it's a 429 rate limit error (temporary, retryable with backoff or key rotation)
                # Note: 429 can occur even when RPD quota remains (RPM/TPM limits)
                is_429_rate_limit = ("429" in error_str or "too many requests" in error_str_lower or "rate limit" in error_str_lower) and not is_quota_exhausted
                
                # Check if it's other retryable errors (503, timeout, etc.)
                is_other_retryable = (
                    "503" in error_str or
                    "UNAVAILABLE" in error_str or
                    "Deadline expired" in error_str or
                    "timeout" in error_str_lower
                )
                
                is_retryable = is_429_rate_limit or is_other_retryable
                
                # Record failure and check for auto-rotation (consecutive failure tracking)
                # Note: Quota exhaustion uses rotate_on_quota_exhausted() separately (below)
                if not is_quota_exhausted and _global_rotator is not None:
                    try:
                        rotation_result = _global_rotator.record_failure(error_str, auto_rotate_threshold=3)
                        if rotation_result is not None:
                            # Auto-rotation occurred due to consecutive failures
                            new_key, new_index = rotation_result
                            new_key_number = _global_rotator.key_numbers[new_index]
                            print(f"\n{'='*60}")
                            print(f"[S4] ⚡ API KEY ROTATED: Auto-rotated to key index {new_index} (GOOGLE_API_KEY_{new_key_number})")
                            print(f"[S4]    Reason: 3 consecutive failures")
                            print(f"{'='*60}\n")
                            # Rebuild client with new key
                            client = build_gemini_client(new_key)
                            key_rotated_this_attempt = True
                            consecutive_429_rate_limits = 0  # Reset counter after key rotation
                            # Retry with new key (don't count as retry attempt)
                            continue
                    except Exception as rot_err:
                        # Log but continue with normal error handling
                        print(f"[S4] Warning: Error during failure recording: {rot_err}")
                
                if is_invalid_key:
                    # Invalid API key: try key rotation (key may be disabled or invalid)
                    if _global_rotator is not None:
                        try:
                            new_key, new_index = _global_rotator.rotate_on_quota_exhausted(error_str)
                            new_key_number = _global_rotator.key_numbers[new_index]
                            print(f"\n{'='*60}")
                            print(f"[S4] ⚡ API KEY ROTATED: Switched to key index {new_index} (GOOGLE_API_KEY_{new_key_number})")
                            print(f"[S4]    Reason: API key invalid or disabled (400 error)")
                            print(f"{'='*60}\n")
                            # Rebuild client with new key
                            client = build_gemini_client(new_key)
                            key_rotated_this_attempt = True
                            consecutive_429_rate_limits = 0  # Reset counter after key rotation
                            # Retry with new key (don't count as retry attempt)
                            continue
                        except RuntimeError as rot_err:
                            # All keys exhausted - fail immediately
                            error_msg = str(rot_err)
                            if "All" in error_msg and "keys exhausted" in error_msg:
                                print(f"[S4] {error_msg}")
                                print(f"[S4] Stopping image generation. Please check API keys or add more API keys.")
                                raise RuntimeError(f"[S4] All API keys invalid or exhausted: {error_msg}") from rot_err
                            # Other RuntimeError - re-raise as-is
                            raise
                        except Exception as rot_err:
                            print(f"[S4] Error during key rotation: {rot_err}")
                            # Fall through to raise original error
                    # No rotator or rotation failed: fail immediately
                    print(f"[S4] API key invalid (non-retryable): {error_str[:200]}")
                    raise
                elif is_quota_exhausted:
                    # Quota exhaustion: immediately try key rotation
                    if _global_rotator is not None:
                        try:
                            new_key, new_index = _global_rotator.rotate_on_quota_exhausted(error_str)
                            new_key_number = _global_rotator.key_numbers[new_index]
                            print(f"\n{'='*60}")
                            print(f"[S4] ⚡ API KEY ROTATED: Switched to key index {new_index} (GOOGLE_API_KEY_{new_key_number})")
                            print(f"[S4]    Reason: Quota exhausted (RPD limit reached)")
                            print(f"{'='*60}\n")
                            # Rebuild client with new key
                            client = build_gemini_client(new_key)
                            # Mark that we rotated keys - next attempt should skip quota_limiter check
                            # (since quota_limiter is tied to the old key's RPD counter)
                            key_rotated_this_attempt = True
                            consecutive_429_rate_limits = 0  # Reset counter after key rotation
                            # Retry with new key (don't count as retry attempt)
                            continue
                        except RuntimeError as rot_err:
                            # All keys exhausted - fail immediately
                            error_msg = str(rot_err)
                            if "All" in error_msg and "keys exhausted" in error_msg:
                                print(f"[S4] {error_msg}")
                                print(f"[S4] Stopping image generation. Please wait for quota reset or add more API keys.")
                                raise RuntimeError(f"[S4] All API keys exhausted: {error_msg}") from rot_err
                            # Other RuntimeError - re-raise as-is
                            raise
                        except Exception as rot_err:
                            print(f"[S4] Error during key rotation: {rot_err}")
                            # Fall through to raise original error
                    # No rotator or rotation failed: fail immediately
                    print(f"[S4] Quota exhausted (non-retryable): {error_str[:200]}")
                    raise
                elif is_429_rate_limit and attempt < max_retries - 1:
                    # 429 rate limit (temporary): track consecutive occurrences and rotate keys if too many
                    consecutive_429_rate_limits += 1
                    
                    # After multiple consecutive 429 rate limits, try key rotation
                    if consecutive_429_rate_limits >= MAX_CONSECUTIVE_429_FOR_ROTATION and _global_rotator is not None:
                        try:
                            new_key, new_index = _global_rotator.rotate_on_quota_exhausted(error_str)
                            new_key_number = _global_rotator.key_numbers[new_index]
                            print(f"\n{'='*60}")
                            print(f"[S4] ⚡ API KEY ROTATED: Switched to key index {new_index} (GOOGLE_API_KEY_{new_key_number})")
                            print(f"[S4]    Reason: {consecutive_429_rate_limits} consecutive 429 rate limit errors (RPM/TPM limit, RPD may remain)")
                            print(f"{'='*60}\n")
                            # Rebuild client with new key
                            client = build_gemini_client(new_key)
                            key_rotated_this_attempt = True
                            consecutive_429_rate_limits = 0  # Reset counter after key rotation
                            # Retry with new key (don't count as retry attempt)
                            continue
                        except RuntimeError as rot_err:
                            # All keys exhausted - fail immediately (same as quota exhaustion)
                            error_msg = str(rot_err)
                            if "All" in error_msg and "keys exhausted" in error_msg:
                                print(f"[S4] {error_msg}")
                                print(f"[S4] Stopping image generation. Please wait for quota reset or add more API keys.")
                                raise RuntimeError(f"[S4] All API keys exhausted: {error_msg}") from rot_err
                            else:
                                # Other RuntimeError - re-raise
                                raise
                        except Exception as rot_err:
                            print(f"[S4] Error during key rotation: {rot_err}")
                            # Fall through to raise original error
                    
                    # Short backoff for rate limits (1-2 seconds instead of exponential)
                    wait_time = min(2.0, retry_delay * (attempt + 1))
                    print(f"[S4] 429 rate limit error (attempt {attempt + 1}/{max_retries}, consecutive: {consecutive_429_rate_limits}): {error_str[:200]}")
                    print(f"[S4] Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                    continue
                elif is_retryable and attempt < max_retries - 1:
                    # Other retryable errors (not 429): reset consecutive 429 counter and use exponential backoff
                    if not is_429_rate_limit:
                        consecutive_429_rate_limits = 0  # Reset counter on non-429 errors
                    wait_time = retry_delay * (attempt + 1)
                    print(f"[S4] Transient error (attempt {attempt + 1}/{max_retries}): {error_str[:200]}")
                    print(f"[S4] Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    # Not retryable or out of retries, raise
                    raise
        
        if response is None:
            print(f"[S4] Error: Failed to generate image after {max_retries} attempts")
            return False, rag_meta, None
        
        # Record successful API call
        if _global_rotator is not None:
            _global_rotator.record_success()
        
        # Extract image bytes
        image_bytes = extract_image_from_response(response)
        if not image_bytes:
            print(f"[S4] Error: No image in response for {output_path.name}")
            return False, rag_meta, None
        
        # Detect image format for logging
        # PNG header: \x89PNG\r\n\x1a\n
        # JPEG header: \xff\xd8\xff
        if image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            format_type = "PNG"
        elif image_bytes.startswith(b'\xff\xd8\xff'):
            format_type = "JPEG"
        else:
            format_type = "Unknown"
            print(f"[S4] Warning: Unknown image format. First 16 bytes: {image_bytes[:16].hex()}")
        
        # Convert to JPEG and save (always save as JPEG regardless of API return format)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not PIL_AVAILABLE:
            # Fallback: save as-is if PIL not available (may cause issues if format mismatch)
            print(f"[S4] Warning: PIL not available, saving image as-is (format: {format_type})")
            output_path.write_bytes(image_bytes)
        else:
            # Convert to JPEG using PIL
            try:
                img = Image.open(io.BytesIO(image_bytes))
                # Convert RGBA to RGB if necessary (JPEG doesn't support transparency)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background for transparent images
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = rgb_img
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save as JPEG with optimized quality (85% to balance quality and file size for Anki)
                # Target: ≤ 100KB per image (Anki recommendation)
                img.save(output_path, 'JPEG', quality=85, optimize=True)
                print(f"[S4] Converted {format_type} to JPEG and saved")
            except Exception as e:
                print(f"[S4] Error converting image to JPEG: {e}")
                # Fallback: save as-is
                output_path.write_bytes(image_bytes)
        
        # Verify saved file
        if output_path.exists() and output_path.stat().st_size > 0:
            file_size = output_path.stat().st_size
            file_size_kb = file_size / 1024
            
            # Check if file is too small (likely corrupted)
            if file_size < 100:
                print(f"[S4] Warning: File size is suspiciously small ({file_size} bytes)")
                return False, rag_meta, None
            
            # Anki recommendation: ≤ 100KB per image (warning suppressed - file size info available in metrics if needed)
            # Note: File size warnings were removed for cleaner terminal output
            # File size information is still available in metrics/logs if needed
            # if file_size > 100 * 1024:  # 100KB
            #     print(f"[S4] Warning: Image file size ({file_size_kb:.1f} KB) exceeds Anki recommendation (100 KB): {output_path}", file=sys.stderr)
            # else:
            #     print(f"[S4] Successfully saved image: {file_size_kb:.1f} KB ({format_type} data)")
            
            # Return None for actual_filename since we keep the original filename
            return True, rag_meta, None
        else:
            print(f"[S4] Error: File was not saved correctly")
            return False, rag_meta, None
        
    except RuntimeError as e:
        # Re-raise RuntimeError (especially "All keys exhausted") to propagate to caller
        # This allows _handle_spec to catch it and stop all workers
        error_msg = str(e)
        if "All" in error_msg and "keys exhausted" in error_msg:
            # Don't print here - it will be printed by the caller
            raise
        # Other RuntimeErrors - re-raise as well
        raise
    except Exception as e:
        print(f"[S4] Image generation failed: {e}")
        return False, rag_meta, None


# =========================
# Main Processing
# =========================

def load_image_specs(image_spec_path: Path) -> Tuple[List[Dict[str, Any]], int]:
    """
    Load S3 image spec JSONL file.
    
    Returns:
        (specs, skipped_count): List of valid specs and count of skipped invalid lines
    """
    specs = []
    skipped_count = 0
    
    if not image_spec_path.exists():
        raise FileNotFoundError(f"S3 image spec not found: {image_spec_path}")
    
    with open(image_spec_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                spec = json.loads(line)
                specs.append(spec)
            except json.JSONDecodeError as e:
                print(f"[S4] Warning: Skipping invalid JSON line {line_num}: {e}")
                skipped_count += 1
                continue
    
    if skipped_count > 0:
        print(f"[S4] Warning: Skipped {skipped_count} invalid JSON lines out of {line_num} total lines")
    
    return specs, skipped_count


def load_existing_successful_images(manifest_path: Path) -> Set[str]:
    """
    Load successful images from existing manifest file.
    
    Only includes images that:
    1. Have generation_success=true in manifest, AND
    2. The actual image file exists and is valid (non-empty)
    
    This prevents duplicate API calls by skipping images that were already
    successfully generated in a previous run.
    
    Returns:
        Set of keys for successful images
        Key format: f"{group_id}::{entity_id}::{card_role}::{spec_kind}::{cluster_id or ''}"
    """
    successful_keys = set()
    
    if not manifest_path.exists():
        return successful_keys
    
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    # Only include successful images
                    if entry.get("generation_success", False):
                        # Check if the actual file exists and is valid
                        image_path_str = entry.get("image_path")
                        if image_path_str:
                            image_path = Path(image_path_str)
                            # Verify file exists and is non-empty
                            if image_path.exists():
                                try:
                                    file_size = image_path.stat().st_size
                                    if file_size > 0:
                                        # File exists and is valid - mark as successful
                                        group_id = str(entry.get("group_id") or "").strip()
                                        entity_id = str(entry.get("entity_id") or "").strip()
                                        card_role = str(entry.get("card_role") or "").strip()
                                        spec_kind = str(entry.get("spec_kind") or "").strip()
                                        cluster_id = str(entry.get("cluster_id") or "").strip()
                                        
                                        # Create unique key (matching format used in _handle_spec)
                                        key = f"{group_id}::{entity_id}::{card_role}::{spec_kind}::{cluster_id}"
                                        successful_keys.add(key)
                                except Exception:
                                    # If we can't check file, don't include it (will regenerate if needed)
                                    pass
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"[S4] Warning: Could not load manifest for skip check: {e}")
    
    return successful_keys


def load_failed_images_from_manifest(manifest_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Load failed images from existing manifest file.
    
    Only includes images that:
    1. Have generation_success=false in manifest, AND
    2. The actual image file does NOT exist (or is empty/corrupted)
    
    This prevents resume mode from retrying images that were successfully generated
    but incorrectly marked as failed in the manifest (e.g., due to previous resume runs).
    
    Returns:
        Dict mapping (group_id, entity_id, card_role, spec_kind) -> manifest entry
        Key format: f"{group_id}::{entity_id}::{card_role}::{spec_kind}::{cluster_id or ''}"
    """
    failed_map = {}
    
    if not manifest_path.exists():
        return failed_map
    
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    # Only include failed images
                    if not entry.get("generation_success", True):
                        # Check if the actual file exists and is valid
                        image_path_str = entry.get("image_path")
                        if image_path_str:
                            image_path = Path(image_path_str)
                            # If file exists and is non-empty, it was actually generated successfully
                            # Skip it (don't include in failed_map)
                            if image_path.exists():
                                try:
                                    file_size = image_path.stat().st_size
                                    if file_size > 0:
                                        # File exists and is valid - not actually failed
                                        # This can happen if manifest was incorrectly updated in a previous resume run
                                        continue
                                except Exception:
                                    # If we can't check file, assume it's failed and retry
                                    pass
                        
                        group_id = str(entry.get("group_id", "")).strip()
                        entity_id = str(entry.get("entity_id", "")).strip()
                        card_role = str(entry.get("card_role", "")).strip()
                        spec_kind = str(entry.get("spec_kind", "")).strip()
                        cluster_id = str(entry.get("cluster_id", "")).strip()
                        
                        # Create unique key
                        key = f"{group_id}::{entity_id}::{card_role}::{spec_kind}::{cluster_id}"
                        failed_map[key] = entry
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"[S4] Warning: Could not load manifest for resume: {e}")
    
    return failed_map


def filter_specs_for_resume(
    specs: List[Dict[str, Any]],
    failed_map: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Filter specs to only include failed images (for resume mode).
    
    Args:
        specs: All image specs
        failed_map: Map of failed images from manifest
    
    Returns:
        Filtered specs (only failed images)
    """
    if not failed_map:
        return []
    
    filtered = []
    for spec in specs:
        group_id = str(spec.get("group_id", "")).strip()
        entity_id = str(spec.get("entity_id", "")).strip()
        card_role = str(spec.get("card_role", "")).strip()
        spec_kind = str(spec.get("spec_kind", "")).strip()
        cluster_id = str(spec.get("cluster_id", "")).strip()
        
        key = f"{group_id}::{entity_id}::{card_role}::{spec_kind}::{cluster_id}"
        if key in failed_map:
            filtered.append(spec)
    
    return filtered


def process_s4(
    *,
    base_dir: Path,
    run_tag: str,
    arm: str,
    images_dir: Optional[Path] = None,
    dry_run: bool = False,
    only_infographic: bool = False,
    image_model: Optional[str] = None,
    workers: int = 1,
    required_only: bool = False,
    resume: bool = False,
    progress_logger: Optional[Any] = None,
    output_variant: str = "baseline",  # baseline|repaired
    only_group_ids: Optional[Sequence[str]] = None,
    only_entity_ids: Optional[Sequence[str]] = None,
    only_card_roles: Optional[Sequence[str]] = None,
    only_spec_kinds: Optional[Sequence[str]] = None,
    overwrite_existing: bool = False,
    force: bool = False,
    fail_fast_required: Optional[bool] = None,
    append_manifest: Optional[bool] = None,
    ignore_batch_tracking: bool = False,
    image_type: Optional[str] = None,
    filename_suffix: Optional[str] = None,
    spec_path: Optional[Path] = None,  # Custom S3 spec path (e.g., repaired)
) -> None:
    """Main S4 processing function."""
    # Paths
    out_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    variant_suffix = _variant_suffix(output_variant)
    
    # S3 spec path: use custom path if provided, otherwise use default baseline
    if spec_path is not None:
        image_spec_path = Path(spec_path).resolve()
    else:
        image_spec_path = out_dir / f"s3_image_spec__arm{arm}.jsonl"
    
    # Auto-set filename_suffix if not provided and image_type is set
    # Priority: CLI --filename_suffix > auto from --image_type > default (no suffix)
    if filename_suffix is None:
        if image_type == "realistic":
            filename_suffix = "_realistic"
        elif image_type == "regen":
            filename_suffix = "_regen"
        else:
            # Default: no suffix (existing behavior)
            filename_suffix = ""
    else:
        filename_suffix = str(filename_suffix)
    
    # Auto-set images_dir if not provided
    # Priority: CLI --images_dir > auto from --image_type > default (images/ or images__repaired/)
    if images_dir is None:
        if image_type == "anki":
            images_dir = out_dir / "images_anki"
        elif image_type == "realistic":
            images_dir = out_dir / "images_realistic"
        elif image_type == "regen":
            images_dir = out_dir / "images_regen"
        else:
            # Default: existing behavior (images/ folder or images__repaired/ for repaired variant)
            images_dir = out_dir / ("images__repaired" if variant_suffix else "images")
    else:
        images_dir = Path(images_dir).resolve()
    
    # Manifest path policy:
    # - Default (legacy): s4_image_manifest__armX.jsonl (baseline images/)
    # - If image_type is provided (anki/realistic/regen), write to a separate manifest to avoid
    #   clobbering baseline manifests (e.g., realistic generation should not overwrite baseline image paths).
    manifest_image_type_suffix = f"__{str(image_type).strip().lower()}" if image_type else ""
    manifest_path = out_dir / f"s4_image_manifest__arm{arm}{manifest_image_type_suffix}{variant_suffix}.jsonl"

    # Fail-fast policy:
    # - baseline: preserve legacy behavior (fail-fast on required image failures)
    # - repaired: default to non-fail-fast (S4 acts as generator for selective repairs)
    if fail_fast_required is None:
        fail_fast_required = (_normalize_output_variant(output_variant) == "baseline")

    # Manifest write policy:
    # - baseline: preserve legacy behavior (overwrite unless --resume)
    # - repaired: default to append (multiple selective repair runs should not erase prior repaired records)
    # - image_type variants (anki/realistic/regen): default to append, so incremental runs don't erase history
    if append_manifest is None:
        append_manifest = (
            _normalize_output_variant(output_variant) == "repaired"
            or bool(image_type)
        )
    
    # Resolve image model
    resolved_model = resolve_image_model(image_model)
    if progress_logger:
        progress_logger.debug(f"[S4] Image model: {resolved_model}")
        if image_model:
            progress_logger.debug(f"[S4]   (from CLI: {image_model})")
        elif os.getenv("S4_IMAGE_MODEL"):
            progress_logger.debug(f"[S4]   (from env: S4_IMAGE_MODEL)")
        else:
            progress_logger.debug(f"[S4]   (default: models/nano-banana-pro-preview)")
    else:
        print(f"[S4] Image model: {resolved_model}")
        if image_model:
            print(f"[S4]   (from CLI: {image_model})")
        elif os.getenv("S4_IMAGE_MODEL"):
            print(f"[S4]   (from env: S4_IMAGE_MODEL)")
        else:
            print(f"[S4]   (default: models/nano-banana-pro-preview)")
    
    # RAG setting (read from env, default: OFF)
    rag_enabled = S4_RAG_ENABLED
    if progress_logger:
        progress_logger.debug(f"[S4] RAG setting: {'ENABLED' if rag_enabled else 'DISABLED'} (default: OFF)")
        if rag_enabled:
            progress_logger.debug(f"[S4] Note: RAG is enabled but prompt augmentation not yet implemented")
    else:
        print(f"[S4] RAG setting: {'ENABLED' if rag_enabled else 'DISABLED'} (default: OFF)")
        if rag_enabled:
            print(f"[S4] Note: RAG is enabled but prompt augmentation not yet implemented")
    
    # Initialize API key rotator early (before loading specs, so user sees key info immediately)
    global _global_rotator
    if ApiKeyRotator is not None:
        try:
            # NOTE: Do NOT hard-cap max_keys here. ApiKeyRotator supports auto-detecting
            # all numbered keys present in the environment with no upper limit (e.g., GOOGLE_API_KEY_1, GOOGLE_API_KEY_2, ..., GOOGLE_API_KEY_19, ...).
            # Keys are automatically detected regardless of how many are present.
            _global_rotator = ApiKeyRotator(base_dir=base_dir, key_prefix="GOOGLE_API_KEY")
            # Log to file
            if progress_logger:
                progress_logger.debug(f"[S4] [API Rotator] Initialized with {len(_global_rotator.keys)} key(s)")
            # Also print to terminal (important initialization info)
            current_key_number = _global_rotator.key_numbers[_global_rotator._current_index]
            print(f"\n{'='*60}")
            print(f"[S4] 🔑 API KEY: Starting with key index {_global_rotator._current_index} (GOOGLE_API_KEY_{current_key_number})")
            print(f"[S4]    Total keys loaded: {len(_global_rotator.keys)}")
            print(f"{'='*60}\n")
        except Exception as e:
            if progress_logger:
                progress_logger.warning(f"[S4] [API Rotator] Failed to initialize rotator, using single key: {e}")
            else:
                print(f"[S4] [API Rotator] Warning: Failed to initialize rotator, using single key: {e}")
            _global_rotator = None
    
    # Load image specs (this may take a while for large files)
    print(f"[S4] Loading image specs from {image_spec_path.name}...")
    specs, skipped_count = load_image_specs(image_spec_path)
    print(f"[S4] Loaded {len(specs)} image spec(s)")
    
    # Resume mode: filter to only failed images
    if resume:
        failed_map = load_failed_images_from_manifest(manifest_path)
        if failed_map:
            original_count = len(specs)
            specs = filter_specs_for_resume(specs, failed_map)
            print(f"[S4] Resume mode: {len(specs)} failed image(s) to retry (from {original_count} total specs, {len(failed_map)} failed in manifest)")
            if not specs:
                print("[S4] No failed images found in manifest; nothing to retry.")
                return
        else:
            print("[S4] Resume mode: No manifest file found or no failed images. Running normal mode.")
            # Continue with all specs (resume mode but no previous failures)
    
    # Filter specs if only_infographic is True
    if only_infographic:
        original_count = len(specs)
        specs = [s for s in specs if str(s.get("spec_kind", "")).strip() == "S1_TABLE_VISUAL"]
        filtered_count = len(specs)
        if filtered_count < original_count:
            print(f"[S4] Filtered to {filtered_count} infographic specs (from {original_count} total specs)")
        if not specs:
            print(f"[S4] Warning: No S1_TABLE_VISUAL specs found after filtering")
            return

    # Filter specs to required-only (Q1/Q2/TABLE) if requested
    if required_only:
        original_count = len(specs)
        specs = [s for s in specs if bool(s.get("image_asset_required", False))]
        print(f"[S4] Required-only: {len(specs)} required specs (from {original_count} total specs)")
        if not specs:
            print("[S4] No required specs found; nothing to do.")
            return

    # Optional subset filters (best-effort; useful for Option C selective regeneration)
    def _as_set(xs: Optional[Sequence[str]]) -> Optional[Set[str]]:
        if not xs:
            return None
        out: Set[str] = set()
        for x in xs:
            s = str(x or "").strip()
            if s:
                out.add(s)
        return out or None

    only_group_set = _as_set(only_group_ids)
    only_entity_set = _as_set(only_entity_ids)
    only_role_set = _as_set([str(x or "").strip().upper() for x in (only_card_roles or [])]) if only_card_roles else None
    only_kind_set = _as_set([str(x or "").strip() for x in (only_spec_kinds or [])]) if only_spec_kinds else None

    if only_group_set or only_entity_set or only_role_set or only_kind_set:
        before = len(specs)
        filtered: List[Dict[str, Any]] = []
        for s in specs:
            gid = str(s.get("group_id") or "").strip()
            eid = str(s.get("entity_id") or "").strip()
            role = str(s.get("card_role") or "").strip().upper()
            kind = str(s.get("spec_kind") or "").strip()
            if only_group_set and gid not in only_group_set:
                continue
            if only_kind_set and kind not in only_kind_set:
                continue
            # Entity/card_role filters apply only to card-image specs; table visuals have empty entity_id/card_role.
            if only_entity_set and eid and eid not in only_entity_set:
                continue
            if only_role_set and role and role not in only_role_set:
                continue
            filtered.append(s)
        specs = filtered
        print(f"[S4] Subset filter: {len(specs)} spec(s) selected (from {before})")
        if not specs:
            print("[S4] Subset filter resulted in 0 specs; nothing to do.")
            return
    
    if not specs:
        if skipped_count > 0:
            raise RuntimeError(
                f"[S4] FAIL: No valid image specs found in {image_spec_path}. "
                f"All {skipped_count} lines were invalid JSON."
            )
        else:
            print(f"[S4] Warning: No image specs found in {image_spec_path}")
            return
    
    # Track required image failures for fail-fast (Q1, Q2, TABLE)
    required_failures: List[Dict[str, Any]] = []
    
    # API key rotator is already initialized above (before loading specs, so user sees key info immediately)
    
    # Build Gemini client (if not dry run)
    client = None
    if not dry_run:
        if not GEMINI_AVAILABLE:
            raise RuntimeError(
                f"[S4] FAIL: google.genai not available. "
                f"Install with: pip install google-genai"
            )
        
        # Use API key rotator if available, otherwise fall back to env var
        # Note: API key info was already printed during early initialization (before loading specs)
        if _global_rotator is not None:
            api_key = _global_rotator.get_current_key()
            # _current_index is 0-based; expose 1-based as well to match .env docs.
            # Log to file only (already printed to terminal during early initialization)
            if progress_logger:
                progress_logger.debug(f"[S4] [API Rotator] Using key index {_global_rotator._current_index} (1-based={_global_rotator._current_index + 1})")
        else:
            api_key = os.getenv(GEMINI_API_KEY_ENV, "").strip()
        
        if not api_key:
            raise RuntimeError(
                f"[S4] FAIL: Missing API key ({GEMINI_API_KEY_ENV}). "
                f"Set the API key in environment variable or .env file."
            )
        
        try:
            client = build_gemini_client(api_key)
        except Exception as e:
            raise RuntimeError(
                f"[S4] FAIL: Failed to build Gemini client: {e}. "
                f"If you want to skip image generation, use --dry-run flag."
            ) from e

    # Quota limiter for image model (RPM/TPM/RPD)
    # Defaults (from console limits): 20 RPM / 100K TPM / 250 RPD (nano-banana-pro)
    # Note: QuotaLimiter is key-agnostic; we use key index in RPD persist path to track per-key usage
    img_quota = None
    s4_metrics_path = out_dir / "logs" / ("s4_image_metrics__repaired.jsonl" if variant_suffix else "s4_image_metrics.jsonl")
    
    def _create_quota_limiter(key_index: Optional[int] = None) -> Optional[Any]:
        """Create a QuotaLimiter instance, optionally key-specific."""
        if (not dry_run) and QuotaLimiter is not None and quota_from_env is not None:
            try:
                # Use nano-banana-pro quota config (RPD tracking disabled)
                cfg = quota_from_env("QUOTA_NANO_BANANA_PRO", default_rpm=20, default_tpm=100_000, default_rpd=None)
                # Disable RPD tracking - rely on API errors and auto key rotation
                return QuotaLimiter(
                    name=f"IMG:{resolved_model}",
                    cfg=cfg,
                    rpd_persist_path=None,  # No RPD tracking - rely on API errors
                )
            except Exception as e:
                if progress_logger:
                    progress_logger.warning(f"[S4] [QUOTA] Failed to init image quota limiter: {e}")
                else:
                    print(f"[S4] [QUOTA] Warning: Failed to init image quota limiter: {e}")
        return None
    
    # Initialize quota limiter for current key
    current_key_index = None
    if _global_rotator is not None:
        current_key_index = _global_rotator._current_index
    img_quota = _create_quota_limiter(current_key_index)
    
    if img_quota is not None:
        if progress_logger:
            progress_logger.debug(f"[S4] [QUOTA] Image quota: {img_quota.snapshot()}")
        else:
            print(f"[S4] [QUOTA] Image quota: {img_quota.snapshot()}")
    
    # Process specs (optionally in parallel); manifest writes are serialized.
    workers = int(workers) if workers is not None else 1
    workers = max(1, workers)
    
    # Counters for statistics (thread-safe with lock)
    stats = {
        "total": len(specs),
        "skipped": 0,
        "generated": 0,
        "failed": 0,
    }
    stats_lock = threading.Lock()  # Lock for thread-safe stats updates
    manifest_lock = threading.Lock()  # Lock for thread-safe manifest writes
    quota_lock = threading.Lock()  # Lock for thread-safe quota limiter updates

    # Load successful images from manifest to filter out specs that don't need generation (default resume mode)
    # Behavior:
    # - If --force: Skip loading successful images (will regenerate all)
    # - If --resume: Skip loading successful images (resume mode only processes failed images)
    # - Otherwise: Load successful images if manifest exists and filter specs upfront (default resume mode - skip already generated images)
    successful_images_set: Set[str] = set()
    if manifest_path.exists() and not resume and not force:
        successful_images_set = load_existing_successful_images(manifest_path)
        if successful_images_set:
            if progress_logger:
                progress_logger.debug(f"[S4] Default resume mode: Loaded {len(successful_images_set)} successful images from manifest (will filter specs upfront)")
            else:
                print(f"[S4] Default resume mode: Loaded {len(successful_images_set)} successful images from manifest (will filter specs upfront)")
    
    # Pre-scan existing image files for faster skip checking (optimization)
    existing_files_set: Set[str] = set()
    existing_files_with_size: Dict[str, int] = {}
    if not force and images_dir.exists():
        try:
            import time
            scan_start = time.time()
            for img_file in images_dir.glob("*.jpg"):
                if img_file.is_file():
                    filename = img_file.name
                    existing_files_set.add(filename)
                    try:
                        # Also cache file size to avoid stat() calls later
                        file_size = img_file.stat().st_size
                        if file_size > 0:  # Only cache non-empty files
                            existing_files_with_size[filename] = file_size
                    except Exception:
                        pass  # Ignore errors, will check again later if needed
            scan_elapsed = time.time() - scan_start
            if existing_files_set:
                if progress_logger:
                    progress_logger.debug(f"[S4] Pre-scanned {len(existing_files_set)} existing image files ({scan_elapsed:.2f}s)")
                else:
                    print(f"[S4] Pre-scanned {len(existing_files_set)} existing image files ({scan_elapsed:.2f}s)")
        except Exception as e:
            if progress_logger:
                progress_logger.warning(f"[S4] Warning: Could not pre-scan image files: {e}")
            else:
                print(f"[S4] Warning: Could not pre-scan image files: {e}")
            # Continue without pre-scan (fallback to per-file checks)

    # Load batch tracking file to check for batch-submitted entities (skip duplicates by default)
    batch_tracking_data: Dict[str, Any] = {"schema_version": "BATCH_TRACKING_v1.0", "batches": {}, "last_updated": ""}
    if ignore_batch_tracking:
        print("[S4] ⚠️  ignore_batch_tracking=ON: Will NOT skip batch-submitted prompts. This may duplicate work/cost.")
        print("[S4]     If the images were already submitted via batch, prefer downloading batch results instead of regenerating.")
    else:
        batch_tracking_path = get_batch_tracking_file_path(base_dir)
        batch_tracking_data = load_batch_tracking_file(batch_tracking_path)
        batch_skipped_count = 0
        
        # Filter out specs that are already submitted to batch
        if batch_tracking_data.get("batches"):
            filtered_specs = []
            for spec in specs:
                batch_info = is_prompt_in_batch(spec, batch_tracking_data)
                if batch_info:
                    batch_skipped_count += 1
                    batch_id = batch_info.get("batch_id", "")
                    status = batch_info.get("status", "")
                    if progress_logger:
                        progress_logger.debug(
                            f"[S4] Skipping batch-submitted entity: {spec.get('group_id')}/{spec.get('entity_id')}/{spec.get('card_role')} "
                            f"(batch: {batch_id}, status: {status})"
                        )
                    continue
                filtered_specs.append(spec)
            specs = filtered_specs
            if batch_skipped_count > 0:
                if progress_logger:
                    progress_logger.debug(f"[S4] Filtered out {batch_skipped_count} batch-submitted image spec(s), {len(specs)} remaining")
                else:
                    print(f"[S4] Filtered out {batch_skipped_count} batch-submitted image spec(s), {len(specs)} remaining to generate")
                # Keep stats total consistent with the actually-processed spec list (avoid confusing summaries).
                stats["total"] = len(specs)
            
            if not specs:
                print("[S4] All images are already submitted to batch. Nothing to do.")
                return
    
    # Filter out specs for images that are already successfully generated (default resume mode)
    #
    # IMPORTANT:
    # - Filter based on BOTH manifest entries (generation_success=true AND file exists) AND actual file existence
    # - If a file exists (even if not in manifest), skip it upfront to avoid duplicate API calls
    # - This ensures we skip images that exist on disk, regardless of manifest state
    # - `successful_images_set` is built from manifest entries that are BOTH generation_success=true AND file exists/non-empty.
    # - `existing_files_set` contains all actual image files found on disk (pre-scanned for performance)
    if (successful_images_set or existing_files_set) and not force and not resume:
        original_spec_count = len(specs)
        filtered_specs = []
        skipped_manifest = 0
        skipped_file_only = 0
        
        for spec in specs:
            group_id = str(spec.get("group_id") or "").strip()
            entity_id = spec.get("entity_id")
            card_role = spec.get("card_role")
            spec_kind = str(spec.get("spec_kind") or "").strip()
            cluster_id = spec.get("cluster_id")

            # Check manifest key (if manifest entry exists with success=true)
            manifest_key = (
                f"{group_id}::{str(entity_id or '').strip()}::"
                f"{str(card_role or '').strip()}::{spec_kind}::{str(cluster_id or '').strip()}"
            )
            in_manifest = manifest_key in successful_images_set
            
            # Check actual file existence (generate filename and check if file exists)
            should_skip = in_manifest
            if not should_skip and existing_files_set:
                try:
                    filename = make_image_filename(
                        run_tag=run_tag,
                        group_id=group_id,
                        entity_id=entity_id,
                        card_role=card_role,
                        spec_kind=spec_kind,
                        cluster_id=cluster_id,
                        suffix=filename_suffix,
                    )
                    if filename in existing_files_set:
                        # Verify file size > 0 (non-empty)
                        file_size = existing_files_with_size.get(filename, 0)
                        if file_size > 0:
                            should_skip = True
                            skipped_file_only += 1
                except Exception:
                    # If filename generation fails, don't skip (let it process and fail properly)
                    pass
            
            if not should_skip:
                filtered_specs.append(spec)
            elif in_manifest:
                skipped_manifest += 1

        specs = filtered_specs
        # Keep stats total consistent with the actually-processed spec list (avoid confusing summaries).
        stats["total"] = len(specs)
        skipped_count = original_spec_count - len(specs)
        if skipped_count > 0:
            if progress_logger:
                progress_logger.debug(f"[S4] Filtered out {skipped_count} already-generated image spec(s) (manifest: {skipped_manifest}, file-only: {skipped_file_only}), {len(specs)} remaining")
            else:
                print(f"[S4] Filtered out {skipped_count} already-generated image spec(s) (manifest: {skipped_manifest}, file-only: {skipped_file_only}), {len(specs)} remaining to generate")
        
        if not specs:
            print("[S4] All images have already been generated. Nothing to do.")
            return

    def _handle_spec(spec: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], bool]:
        """
        Returns: (manifest_entry, failure_dict, was_skipped)
        was_skipped: True if image already existed and was skipped
        """
        run_tag_rec = str(spec.get("run_tag") or run_tag).strip()
        group_id = str(spec.get("group_id") or "").strip()
        entity_id = spec.get("entity_id")  # May be None for table visuals
        entity_name = str(spec.get("entity_name") or "").strip()
        card_role = spec.get("card_role")  # May be None for table visuals
        spec_kind = str(spec.get("spec_kind", "S2_CARD_IMAGE")).strip()
        image_required = bool(spec.get("image_asset_required", False))
        
        # Check if this spec is already submitted to batch (additional check in case filtering missed it)
        if not ignore_batch_tracking:
            batch_info = is_prompt_in_batch(spec, batch_tracking_data)
            if batch_info:
                batch_id = batch_info.get("batch_id", "")
                status = batch_info.get("status", "")
                print(f"[S4] ⏭️  Skipping batch-submitted entity: {group_id}/{entity_id}/{card_role} (batch: {batch_id}, status: {status})")
                return None, None, True

        # Validate required keys based on spec_kind
        if spec_kind == "S1_TABLE_VISUAL":
            if not group_id:
                return None, {"spec_kind": spec_kind, "entity_name": entity_name, "error": "missing group_id"}, False
        else:
            if not (group_id and entity_id and card_role):
                return None, {"spec_kind": spec_kind, "entity_name": entity_name, "error": "missing group_id/entity_id/card_role"}, False

        cluster_id = spec.get("cluster_id")
        filename = make_image_filename(
            run_tag=run_tag_rec,
            group_id=group_id,
            entity_id=entity_id,
            card_role=card_role,
            spec_kind=spec_kind,
            cluster_id=cluster_id,
            suffix=filename_suffix,
        )
        output_path = images_dir / filename

        was_skipped = False
        # Optionally overwrite existing (used for quality-driven re-generation in repaired variant)
        # Also delete if force flag is set (force regeneration)
        if (overwrite_existing or force) and output_path.exists():
            try:
                output_path.unlink()
            except Exception:
                pass

        # Note: Specs for already-generated images (in manifest) were filtered out upfront (in default resume mode)
        # So if we reach here, the image needs to be generated (unless file exists as fallback check)
        success = None
        rag_meta = None

        # Skip if image already exists and is valid (non-zero size) - fallback check for edge cases
        # Skip this check if force flag is set (force regeneration)
        # Use pre-scanned file list for fast check (optimization)
        if not force and success is None and filename in existing_files_set:
            # File exists - use cached file size if available
            file_size = existing_files_with_size.get(filename)
            if file_size is not None and file_size > 0:
                print(f"[S4] ✓ Skipping (already exists, {file_size:,} bytes): {filename}")
                success = True
                rag_meta = {"rag_enabled": False, "rag_queries_count": 0, "rag_sources_count": 0}
                was_skipped = True
            else:
                # File in pre-scan but size not cached or is 0 - verify with stat()
                try:
                    if output_path.exists():
                        file_size = output_path.stat().st_size
                        if file_size > 0:
                            print(f"[S4] ✓ Skipping (already exists, {file_size:,} bytes): {filename}")
                            # Update cache
                            existing_files_with_size[filename] = file_size
                            success = True
                            rag_meta = {"rag_enabled": False, "rag_queries_count": 0, "rag_sources_count": 0}
                            was_skipped = True
                        else:
                            # File exists but is empty (corrupted?), regenerate it
                            print(f"[S4] Warning: Existing file is empty, regenerating: {filename}")
                            output_path.unlink()  # Delete empty file
                            existing_files_set.discard(filename)  # Update cache
                            existing_files_with_size.pop(filename, None)
                            success = None  # Will generate below
                            rag_meta = None
                    else:
                        # File was in pre-scan but doesn't exist now - update cache and regenerate
                        existing_files_set.discard(filename)  # Update cache
                        existing_files_with_size.pop(filename, None)
                        success = None
                        rag_meta = None
                except Exception as e:
                    # If stat() fails, try to regenerate
                    print(f"[S4] Warning: Cannot check existing file ({e}), will regenerate: {filename}")
                    existing_files_set.discard(filename)  # Update cache
                    existing_files_with_size.pop(filename, None)
                    success = None
                    rag_meta = None
        elif not force and success is None:
            # File not in pre-scan - try exists() check as fallback (shouldn't happen often)
            if output_path.exists():
                try:
                    file_size = output_path.stat().st_size
                    if file_size > 0:
                        print(f"[S4] ✓ Skipping (already exists, {file_size:,} bytes): {filename}")
                        # Update cache
                        existing_files_set.add(filename)
                        existing_files_with_size[filename] = file_size
                        success = True
                        rag_meta = {"rag_enabled": False, "rag_queries_count": 0, "rag_sources_count": 0}
                        was_skipped = True
                    else:
                        # File exists but is empty (corrupted?), regenerate it
                        print(f"[S4] Warning: Existing file is empty, regenerating: {filename}")
                        output_path.unlink()  # Delete empty file
                        success = None  # Will generate below
                        rag_meta = None
                except Exception as e:
                    # If stat() fails, try to regenerate
                    print(f"[S4] Warning: Cannot check existing file ({e}), will regenerate: {filename}")
                    success = None
                    rag_meta = None
            else:
                success = None
                rag_meta = None
        else:
            success = None
            rag_meta = None
        
        if success is None:
            # Need to generate (file doesn't exist, is empty, or stat failed)
            if dry_run:
                print(f"[S4] [DRY-RUN] Would generate: {filename} (RAG: {'ON' if rag_enabled else 'OFF'})")
                # Dry-run should never be counted as a failure; it is a planning/preview mode.
                # IMPORTANT: This does NOT create the output file. Downstream "default resume mode"
                # still requires file existence to skip, so this won't block later real runs.
                success = True
                rag_meta = {"rag_enabled": bool(rag_enabled), "rag_queries_count": 0, "rag_sources_count": 0}
            else:
                # Generating message suppressed for cleaner terminal output (progress bar shows status)
                # Use current quota limiter (may be updated by key rotation)
                # If rotator is available, get current key index and use key-specific quota limiter
                nonlocal img_quota  # Declare nonlocal first before using img_quota
                current_quota = img_quota
                if _global_rotator is not None:
                    with quota_lock:
                        current_key_idx = _global_rotator._current_index
                        # Check if we need to recreate quota limiter for current key
                        # (This happens when key was rotated during previous image generation)
                        if current_quota is None or not hasattr(current_quota, '_key_index') or getattr(current_quota, '_key_index', None) != current_key_idx:
                            # Recreate quota limiter for current key
                            current_quota = _create_quota_limiter(current_key_idx)
                            if current_quota is not None:
                                # Store key index for future reference
                                current_quota._key_index = current_key_idx
                                img_quota = current_quota
                
                success, rag_meta, _ = generate_image(
                    image_spec=spec,
                    output_path=output_path,
                    client=client,
                    rag_enabled=rag_enabled,
                    base_dir=base_dir,
                    image_model=image_model,
                    quota_limiter=current_quota,
                    metrics_path=s4_metrics_path,
                    run_tag=run_tag,
                )
                # Success/failure messages suppressed for cleaner terminal output (progress bar shows status)
                # Detailed logs are available in metrics file

        # Ensure rag_meta is not None (should always be set above, but type checker needs this)
        if rag_meta is None:
            rag_meta = {"rag_enabled": False, "rag_queries_count": 0, "rag_sources_count": 0}
        
        manifest_entry = {
            "schema_version": "S4_IMAGE_MANIFEST_v1.0",
            "run_tag": run_tag_rec,
            "group_id": group_id,
            "entity_id": entity_id,
            "entity_name": entity_name,
            "card_role": card_role,
            "spec_kind": spec_kind,
            "media_filename": filename,
            "image_path": str(output_path),
            "generation_success": success,
            "image_required": image_required,
            "rag_enabled": bool(rag_meta.get("rag_enabled", False)),
            "rag_queries_count": int(rag_meta.get("rag_queries_count", 0)),
            "rag_sources_count": int(rag_meta.get("rag_sources_count", 0)),
        }
        if cluster_id:
            manifest_entry["cluster_id"] = cluster_id

        if not success:
            return manifest_entry, {
                "spec": spec,
                "filename": filename,
                "entity_name": entity_name or f"Group {group_id}",
                "spec_kind": spec_kind,
                "required": bool(image_required),
            }, False
        
        # In resume mode, if image was skipped (already exists), we should still write to manifest
        # to update the generation_success flag from false to true.
        # This prevents the same image from being retried in future resume runs.
        return manifest_entry, None, was_skipped

    # Group specs by group_id, entity_id, and card_role for progress tracking
    groups_dict = {}
    for spec in specs:
        group_id = str(spec.get("group_id") or "").strip()
        entity_id = str(spec.get("entity_id") or "").strip()
        card_role = str(spec.get("card_role") or "").strip()
        spec_kind = str(spec.get("spec_kind") or "").strip()
        
        if group_id:
            if group_id not in groups_dict:
                groups_dict[group_id] = {}
            if entity_id:
                if entity_id not in groups_dict[group_id]:
                    groups_dict[group_id][entity_id] = {}
                if card_role:
                    if card_role not in groups_dict[group_id][entity_id]:
                        groups_dict[group_id][entity_id][card_role] = []
                    groups_dict[group_id][entity_id][card_role].append(spec)
                elif spec_kind == "S1_TABLE_VISUAL":
                    # Table visuals don't have card_role
                    if "TABLE" not in groups_dict[group_id][entity_id]:
                        groups_dict[group_id][entity_id]["TABLE"] = []
                    groups_dict[group_id][entity_id]["TABLE"].append(spec)
    
    total_groups = len(groups_dict)
    total_entities = sum(len(entities) for entities in groups_dict.values())
    total_cards = sum(
        len(cards) if isinstance(cards, dict) else 0
        for entities in groups_dict.values()
        for cards in entities.values()
    )
    total_images = len(specs)
    
    # Initialize progress bars
    if progress_logger:
        progress_logger.init_group(total_groups, desc="[S4] Processing groups")
        progress_logger.init_entity(total_entities, desc="  [S4] Processing entities")
        progress_logger.init_card(total_cards, desc="    [S4] Processing cards")
        progress_logger.init_image(total_images, desc="      [S4] Generating images")
    
    if progress_logger:
        progress_logger.debug(f"[S4] Processing {len(specs)} image spec(s) with {workers} worker(s)...")
        progress_logger.debug(f"[S4] Images directory: {images_dir}")
    else:
        print(f"[S4] Processing {len(specs)} image spec(s) with {workers} worker(s)...", flush=True)
        print(f"[S4] Images directory: {images_dir}", flush=True)
    
    group_idx = 0
    entity_idx = 0
    card_idx = 0
    image_idx = 0
    
    # Manifest mode:
    # - resume: always append (retries write new entries)
    # - append_manifest: append without filtering (useful for selective repaired runs)
    # - otherwise: overwrite
    #
    # Note: We may produce duplicates across runs. Downstream readers should prefer the latest entry
    # (or resolve by checking actual file existence).
    manifest_mode = "a" if (resume or append_manifest) else "w"
    with open(manifest_path, manifest_mode, encoding="utf-8") as f_manifest:
        if workers <= 1:
            for idx, spec in enumerate(specs, 1):
                # Update progress
                group_id = str(spec.get("group_id") or "").strip()
                entity_id = str(spec.get("entity_id") or "").strip()
                card_role = str(spec.get("card_role") or "").strip()
                
                if progress_logger:
                    # Update image progress
                    image_idx = idx
                    progress_logger.update_image(image_idx, total_images, image_name=spec.get("filename", ""))
                    
                    # Update group/entity/card progress when moving to new items
                    if group_id and group_id in groups_dict:
                        current_group_idx = list(groups_dict.keys()).index(group_id) + 1
                        if current_group_idx != group_idx:
                            group_idx = current_group_idx
                            progress_logger.update_group(group_idx, total_groups, group_id=group_id)
                            progress_logger.reset_entity()
                        
                        if entity_id and entity_id in groups_dict[group_id]:
                            entities_list = list(groups_dict[group_id].keys())
                            current_entity_idx = entities_list.index(entity_id) + 1
                            if current_entity_idx != entity_idx:
                                entity_idx = current_entity_idx
                                progress_logger.update_entity(entity_idx, total_entities, entity_id=entity_id)
                                progress_logger.reset_card()
                            
                            if card_role and card_role in groups_dict[group_id][entity_id]:
                                cards_list = list(groups_dict[group_id][entity_id].keys())
                                current_card_idx = cards_list.index(card_role) + 1
                                if current_card_idx != card_idx:
                                    card_idx = current_card_idx
                                    progress_logger.update_card(card_idx, total_cards, card_role=card_role)
                try:
                    manifest_entry, failure, was_skipped = _handle_spec(spec)
                except RuntimeError as e:
                    error_msg = str(e)
                    # Check if this is the "all keys exhausted" error
                    if "All" in error_msg and "keys exhausted" in error_msg:
                        print(f"\n{'='*60}")
                        print(f"[S4] CRITICAL: {error_msg}")
                        print(f"[S4] Stopping image generation. Please wait for quota reset or add more API keys.")
                        print(f"{'='*60}\n")
                        # Re-raise to stop the process
                        raise RuntimeError(f"[S4] All API keys exhausted. Stopping image generation: {error_msg}") from e
                    else:
                        # Other RuntimeError - re-raise
                        raise
                if manifest_entry is None:
                    # Invalid spec
                    continue
                
                # Update statistics
                if was_skipped:
                    stats["skipped"] += 1
                elif manifest_entry.get("generation_success"):
                    stats["generated"] += 1
                else:
                    stats["failed"] += 1
                
                if failure is not None and failure.get("required"):
                    required_failures.append(failure)
                elif failure is not None:
                    print(f"[S4] Warning: Optional image generation failed: {failure.get('filename')}")
                f_manifest.write(json.dumps(manifest_entry, ensure_ascii=False) + "\n")
                
                if idx % 10 == 0 or idx == len(specs):
                    if progress_logger:
                        progress_logger.debug(f"[S4] Progress: {idx}/{len(specs)} processed (generated: {stats['generated']}, skipped: {stats['skipped']}, failed: {stats['failed']})")
                    else:
                        print(f"[S4] Progress: {idx}/{len(specs)} processed (generated: {stats['generated']}, skipped: {stats['skipped']}, failed: {stats['failed']})", flush=True)
        else:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futs = {ex.submit(_handle_spec, s): s for s in specs}
                completed = 0
                for fut in as_completed(futs):
                    completed += 1
                    try:
                        manifest_entry, failure, was_skipped = fut.result()
                    except RuntimeError as e:
                        error_msg = str(e)
                        # Check if this is the "all keys exhausted" error
                        if "All" in error_msg and "keys exhausted" in error_msg:
                            print(f"\n{'='*60}")
                            print(f"[S4] CRITICAL: {error_msg}")
                            print(f"[S4] Stopping all image generation. Please wait for quota reset or add more API keys.")
                            print(f"{'='*60}\n")
                            # Cancel all remaining futures
                            for remaining_fut in futs:
                                if remaining_fut != fut:
                                    remaining_fut.cancel()
                            # Re-raise to stop the process
                            raise RuntimeError(f"[S4] All API keys exhausted. Stopping image generation: {error_msg}") from e
                        else:
                            # Other RuntimeError - re-raise
                            raise
                    if manifest_entry is None:
                        continue
                    
                    # Update statistics (thread-safe)
                    with stats_lock:
                        if was_skipped:
                            stats["skipped"] += 1
                        elif manifest_entry.get("generation_success"):
                            stats["generated"] += 1
                        else:
                            stats["failed"] += 1
                        
                        if failure is not None and failure.get("required"):
                            required_failures.append(failure)
                    
                    if failure is not None and not failure.get("required"):
                        print(f"[S4] Warning: Optional image generation failed: {failure.get('filename')}")
                    
                    # Write manifest entry (thread-safe)
                    with manifest_lock:
                        f_manifest.write(json.dumps(manifest_entry, ensure_ascii=False) + "\n")
                    
                    # Update progress
                    if progress_logger:
                        progress_logger.update_image(completed, len(specs))
                    
                    # Progress reporting (read stats with lock)
                    if completed % 5 == 0 or completed == len(specs):
                        with stats_lock:
                            current_stats = {
                                "generated": stats["generated"],
                                "skipped": stats["skipped"],
                                "failed": stats["failed"],
                            }
                        if progress_logger:
                            progress_logger.debug(f"[S4] Progress: {completed}/{len(specs)} completed (generated: {current_stats['generated']}, skipped: {current_stats['skipped']}, failed: {current_stats['failed']})")
                        else:
                            print(f"[S4] Progress: {completed}/{len(specs)} completed (generated: {current_stats['generated']}, skipped: {current_stats['skipped']}, failed: {current_stats['failed']})", flush=True)
    
    # Print final statistics
    print(f"\n[S4] Summary: total={stats['total']}, generated={stats['generated']}, skipped={stats['skipped']}, failed={stats['failed']}", flush=True)
    
    # P0: Required images missing = FAIL-FAST (Q1, Q2, TABLE)
    # Skip FAIL-FAST in dry-run mode and resume mode
    # - dry-run: no actual generation occurs
    # - resume: already failed images are being retried, so don't fail-fast on retry failures
    #
    # Additionally, when running output_variant=repaired, we default to non-fail-fast so S4 can act
    # as a generator for selective regeneration (Option C style). You can override via CLI.
    if required_failures and not dry_run and not resume and bool(fail_fast_required):
        error_msg = "S4 FAIL-FAST: Required image generation failed:\n"
        for failure in required_failures:
            error_msg += f"  - {failure['spec_kind']}: {failure['entity_name']}, File: {failure['filename']}\n"
        raise RuntimeError(error_msg)
    elif required_failures and (dry_run or resume or (not bool(fail_fast_required))):
        if dry_run:
            mode_str = "DRY-RUN"
        elif resume:
            mode_str = "RESUME"
        else:
            mode_str = "NO-FAIL-FAST"
        print(f"[S4] [{mode_str}] Warning: {len(required_failures)} required image(s) failed:", flush=True)
        for failure in required_failures:
            print(f"  - {failure['spec_kind']}: {failure['entity_name']}, File: {failure['filename']}", flush=True)
        if resume:
            print(f"[S4] [RESUME] Note: These images failed during retry. You may need to investigate and retry again.", flush=True)
    
    print(f"[S4] Image manifest: {manifest_path}")
    print(f"[S4] Images directory: {images_dir}")


# =========================
# CLI
# =========================

def main() -> None:
    parser = argparse.ArgumentParser(description="S4 Image Generator")
    parser.add_argument("--base_dir", default=".", help="Base directory")
    parser.add_argument("--run_tag", required=True, help="Run tag")
    parser.add_argument("--arm", default="A", help="Arm identifier")
    parser.add_argument("--images_dir", default=None, help="Images output directory (default: {out_dir}/images)")
    parser.add_argument("--dry_run", action="store_true", help="Dry run mode (don't actually generate images)")
    parser.add_argument(
        "--ignore_batch_tracking",
        action="store_true",
        default=False,
        help="If set, do NOT skip prompts that appear as already submitted in .batch_tracking.json. "
             "WARNING: may duplicate batch work/cost. Prefer downloading batch results when possible.",
    )
    parser.add_argument(
        "--output_variant",
        type=str,
        default="baseline",
        choices=["baseline", "repaired"],
        help="Output variant. 'baseline' writes to images/ + s4_image_manifest__armX.jsonl; "
             "'repaired' writes to images__repaired/ + s4_image_manifest__armX__repaired.jsonl (never overwrites baseline).",
    )
    parser.add_argument("--only_group_id", action="append", default=None, help="Optional: restrict to a group_id (repeatable)")
    parser.add_argument("--only_entity_id", action="append", default=None, help="Optional: restrict to an entity_id (repeatable)")
    parser.add_argument("--only_card_role", action="append", default=None, help="Optional: restrict to card_role (Q1/Q2) (repeatable)")
    parser.add_argument("--only_spec_kind", action="append", default=None, help="Optional: restrict to spec_kind (repeatable)")
    parser.add_argument(
        "--overwrite_existing",
        action="store_true",
        default=False,
        help="If set, overwrite existing files in the selected output directory (useful for quality-driven re-generation).",
    )
    parser.add_argument(
        "--append_manifest",
        action="store_true",
        default=False,
        help="If set, append to the manifest instead of overwriting it (useful for repeated selective runs; "
             "default behavior is append for output_variant=repaired, overwrite for baseline).",
    )
    ff_grp = parser.add_mutually_exclusive_group()
    ff_grp.add_argument(
        "--fail_fast_required",
        dest="fail_fast_required",
        action="store_true",
        default=None,
        help="Fail-fast on required image generation failures (baseline default).",
    )
    ff_grp.add_argument(
        "--no_fail_fast_required",
        dest="fail_fast_required",
        action="store_false",
        default=None,
        help="Do NOT fail-fast on required image failures; only warn (repaired default).",
    )
    parser.add_argument(
        "--only-infographic",
        action="store_true",
        help="Generate only infographic images (S1_TABLE_VISUAL), skip card images (S2_CARD_IMAGE)",
    )
    parser.add_argument(
        "--image_model",
        type=str,
        default=None,
        help="Image generation model. Options: 'nano-banana-pro'/'pro' (default, high quality), "
             "'nano-banana'/'banana' (faster, lower quality). "
             "Can also use full model names like 'models/nano-banana-pro-preview' or 'models/gemini-2.5-flash-image'. "
             "Overrides S4_IMAGE_MODEL env var.",
    )
    parser.add_argument(
        "--image_type",
        type=str,
        choices=["anki", "realistic", "regen"],
        default=None,
        help="Image type for folder and filename suffix. "
             "If not provided, uses default behavior (images/ folder, no suffix). "
             "Options: 'anki' (images_anki/), 'realistic' (images_realistic/, _realistic suffix), "
             "'regen' (images_regen/, _regen suffix)",
    )
    parser.add_argument(
        "--filename_suffix",
        type=str,
        default=None,
        help="Override filename suffix (e.g., '_realistic', '_regen'). "
             "If not provided and --image_type is set, auto-derived from --image_type",
    )
    parser.add_argument(
        "--spec_path",
        type=str,
        default=None,
        help="Custom S3 image spec path (e.g., for repaired S3). "
             "If not specified, uses default: s3_image_spec__arm{arm}.jsonl",
    )
    # Parse base_dir first to load .env before other args
    args_base, _ = parser.parse_known_args()
    base_dir = Path(args_base.base_dir).resolve()
    
    # Load .env file from base_dir
    env_path = base_dir / ".env"
    if env_path.exists():
        # Override=True so per-run settings in .env (e.g., API_KEY_ROTATOR_START_INDEX)
        # reliably take effect even if the shell already has stale env values.
        load_dotenv(env_path, override=True)
    else:
        # Fallback: try to load from current directory
        load_dotenv(override=True)
    
    # Read default workers from .env if available (WORKERS_S4 or WORKERS)
    default_workers = 1
    try:
        default_workers = int(os.getenv("WORKERS_S4", os.getenv("WORKERS", "1")))
    except (ValueError, TypeError):
        default_workers = 1
    
    parser.add_argument("--workers", type=int, default=default_workers, 
                        help=f"Parallel workers for image generation (default: {default_workers} from .env WORKERS_S4/WORKERS, or 1)")
    parser.add_argument("--required_only", action="store_true", help="Generate only required images (image_asset_required=true)")
    parser.add_argument("--resume", action="store_true", 
                        help="Resume mode: retry only failed images from existing manifest. "
                             "Reads s4_image_manifest__arm{arm}.jsonl and retries images with generation_success=false.")
    parser.add_argument("--force", action="store_true",
                        help="Force regeneration: skip all existing images and manifest entries, regenerate all images. "
                             "This disables the default resume mode (automatic skipping of successful images).")
    
    args = parser.parse_args()
    
    run_tag = str(args.run_tag).strip()
    arm = str(args.arm).strip().upper()
    images_dir = Path(args.images_dir).resolve() if args.images_dir else None
    output_variant = _normalize_output_variant(getattr(args, "output_variant", "baseline"))
    
    # Initialize progress logger
    progress_logger = None
    if ProgressLogger is not None:
        try:
            progress_logger = ProgressLogger(
                run_tag=run_tag,
                script_name="s4",
                arm=arm,
                base_dir=base_dir,
            )
        except Exception as e:
            print(f"[WARN] Failed to initialize ProgressLogger: {e}", file=sys.stderr)
            progress_logger = None
    
    # Custom spec path
    spec_path = Path(args.spec_path).resolve() if args.spec_path else None
    
    if progress_logger:
        progress_logger.info(f"[S4] Processing: run_tag={run_tag}, arm={arm}")
        if spec_path:
            progress_logger.info(f"[S4] Using custom spec path: {spec_path}")
    else:
        print(f"[S4] Processing: run_tag={run_tag}, arm={arm}")
        if spec_path:
            print(f"[S4] Using custom spec path: {spec_path}")
    
    try:
        process_s4(
            base_dir=base_dir,
            run_tag=run_tag,
            arm=arm,
            images_dir=images_dir,
            dry_run=args.dry_run,
            only_infographic=args.only_infographic,
            image_model=args.image_model,
            workers=args.workers,
            required_only=args.required_only,
            resume=args.resume,
            progress_logger=progress_logger,
            output_variant=output_variant,
            only_group_ids=getattr(args, "only_group_id", None),
            only_entity_ids=getattr(args, "only_entity_id", None),
            only_card_roles=getattr(args, "only_card_role", None),
            only_spec_kinds=getattr(args, "only_spec_kind", None),
            overwrite_existing=bool(getattr(args, "overwrite_existing", False)),
            force=bool(getattr(args, "force", False)),
            fail_fast_required=getattr(args, "fail_fast_required", None),
            append_manifest=(True if bool(getattr(args, "append_manifest", False)) else None),
            ignore_batch_tracking=bool(getattr(args, "ignore_batch_tracking", False)),
            image_type=getattr(args, "image_type", None),
            filename_suffix=getattr(args, "filename_suffix", None),
            spec_path=spec_path,
        )
        if progress_logger:
            progress_logger.info("[S4] Done")
            progress_logger.close()
        else:
            print("[S4] Done")
    except Exception as e:
        if progress_logger:
            progress_logger.error(f"[S4] FAIL: {e}")
            progress_logger.close()
        else:
            print(f"[S4] FAIL: {e}")
        raise


if __name__ == "__main__":
    main()


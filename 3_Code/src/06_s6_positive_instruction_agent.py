"""
MeducAI Step06 (S6) — Positive Instruction Agent

Purpose:
- Convert S5 validation feedback (prompt_patch_hint) into positive, actionable instructions
- Enhance S3 image specs for regeneration (S4 regen pipeline)

Design Principles:
- S6 is a transformation layer (S5 feedback → positive instructions)
- Uses LLM to interpret negative feedback and reframe as affirmative guidance
- Model policy: TABLE=Pro (complex layouts), CARD=Flash (simple conversions)
- Thinking: always ON (high-quality reasoning needed)
- RAG: OFF (regeneration is generation task, avoid scope creep)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    load_dotenv = None

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL/Pillow not available. Image loading disabled.", file=sys.stderr)

try:
    from google import genai
    from google.genai import types as genai_types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google.genai not available. S6 agent will be disabled.", file=sys.stderr)

# API Key Rotator (optional)
ApiKeyRotator = None
ROTATOR_AVAILABLE = False
try:
    from tools.api_key_rotator import ApiKeyRotator  # type: ignore
    ROTATOR_AVAILABLE = True
except Exception:
    # Rotator not available, will use fallback GOOGLE_API_KEY
    pass

# =========================
# Configuration
# =========================

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

# S6 Configuration
S6_TEMPERATURE = _env_float("TEMPERATURE_S6", 0.3)  # Slightly higher than S5 for creative reframing
S6_THINKING_LEVEL = os.getenv("S6_THINKING_LEVEL", "high").strip().lower()
S6_RAG_ENABLED = _env_bool("S6_RAG_ENABLED", False)  # Default: OFF (regeneration = generation)
S6_TIMEOUT = int(_env_float("S6_TIMEOUT", 120.0))  # 120 seconds per call

# Model selection
S6_PRO_MODEL = os.getenv("S6_PRO_MODEL", "gemini-3-pro-preview").strip()
S6_FLASH_MODEL = os.getenv("S6_FLASH_MODEL", "gemini-3-flash-preview").strip()

# API Key Rotator (global instance, initialized on first use)
_global_rotator = None  # type: ignore

# =========================
# Environment Loading
# =========================

def load_env(base_dir: Path) -> None:
    """
    Load .env file from base_dir if it exists.
    Similar to 01_generate_json.py's load_env() function.
    
    Args:
        base_dir: Project base directory
    """
    if not DOTENV_AVAILABLE or load_dotenv is None:
        return
    
    env_path = base_dir / ".env"
    if env_path.exists():
        try:
            # IMPORTANT: Do not override explicit process env (CLI prefix like VAR=1 python ...).
            # We want CLI env to take precedence; .env should only fill missing values.
            load_dotenv(dotenv_path=env_path, override=False)
        except PermissionError as e:
            # If .env file cannot be read due to permissions, warn but continue
            # Environment variables may already be set in the system
            print(f"⚠️  Warning: Cannot read .env file due to permissions: {e}", file=sys.stderr)
            print(f"   Continuing with system environment variables only.", file=sys.stderr)
            print(f"   If API calls fail, check that required environment variables are set.", file=sys.stderr)
        except (OSError, FileNotFoundError):
            # Silently handle if .env doesn't exist or can't be accessed
            pass

# =========================
# Prompt Loading
# =========================

def load_prompt_template(base_dir: Path, template_name: str = "S6_POSITIVE_INSTRUCTION") -> str:
    """
    Load S6 prompt template from registry.
    
    Args:
        base_dir: Project base directory
        template_name: Template name in registry (default: S6_POSITIVE_INSTRUCTION)
        
    Returns:
        Prompt template string
    """
    prompt_dir = base_dir / "3_Code" / "prompt"
    registry_path = prompt_dir / "_registry.json"
    
    if not registry_path.exists():
        raise FileNotFoundError(f"Prompt registry not found: {registry_path}")
    
    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)
    
    template_filename = registry.get(template_name)
    if not template_filename:
        raise ValueError(f"Template '{template_name}' not found in registry")
    
    template_path = prompt_dir / template_filename
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")
    
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

# =========================
# Image Loading
# =========================

def load_image_for_multimodal(image_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load image from file path for multimodal LLM input.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Dict with 'bytes' and 'mime_type' keys, or None if loading fails
    """
    if not PIL_AVAILABLE:
        return None
    
    if not image_path.exists():
        print(f"Warning: Image file not found: {image_path}", file=sys.stderr)
        return None
    
    try:
        # Load image and convert to bytes
        img = Image.open(image_path)
        
        # Convert to RGB if needed (remove alpha channel for JPEG)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        
        # Save to bytes buffer
        import io
        buffer = io.BytesIO()
        img_format = img.format or "JPEG"
        if img_format.upper() not in ["JPEG", "PNG", "GIF", "WEBP"]:
            img_format = "JPEG"
        img.save(buffer, format=img_format)
        img_bytes = buffer.getvalue()
        
        # Determine MIME type
        mime_type_map = {
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "GIF": "image/gif",
            "WEBP": "image/webp",
        }
        mime_type = mime_type_map.get(img_format.upper(), "image/jpeg")
        
        return {
            "bytes": img_bytes,
            "mime_type": mime_type,
        }
    except Exception as e:
        print(f"Warning: Failed to load image {image_path}: {e}", file=sys.stderr)
        return None

# =========================
# LLM Caller
# =========================

def call_s6_llm(
    *,
    prompt: str,
    image_path: Path,
    model: str,
    thinking_level: str = "high",
    rag_enabled: bool = False,
    temperature: float = 0.3,
    timeout_s: int = 120,
    base_dir: Optional[Path] = None,
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Call LLM for S6 positive instruction generation.
    
    Args:
        prompt: Formatted prompt string
        image_path: Path to S4 generated image
        model: Model name (Pro or Flash)
        thinking_level: Thinking level ("minimal", "low", "medium", "high")
        rag_enabled: Whether to enable RAG (default: False)
        temperature: Temperature for generation
        timeout_s: Timeout in seconds
        base_dir: Project base directory (for loading .env file)
        
    Returns:
        (response_text, error_dict): Response text or None, error dict or None
    """
    if not GEMINI_AVAILABLE:
        return None, {"error": "google.genai not available"}
    
    # Load .env file if base_dir is provided
    if base_dir is not None:
        load_env(base_dir)
    
    # Initialize API key rotator (once per process)
    global _global_rotator
    if _global_rotator is None and ROTATOR_AVAILABLE and ApiKeyRotator is not None:
        try:
            _base_dir = base_dir if base_dir is not None else Path.cwd()
            _global_rotator = ApiKeyRotator(base_dir=_base_dir, key_prefix="GOOGLE_API_KEY")
        except Exception as e:
            print(f"[S6] Warning: Failed to initialize API key rotator: {e}", file=sys.stderr)
            _global_rotator = None
    
    # Get API key from rotator or environment
    api_key = None
    if _global_rotator is not None:
        try:
            api_key = _global_rotator.get_current_key()
        except Exception as e:
            print(f"[S6] Warning: Failed to get key from rotator: {e}", file=sys.stderr)
            api_key = None
    
    # Fallback to GOOGLE_API_KEY environment variable
    if not api_key:
        api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    
    if not api_key:
        return None, {"error": "GOOGLE_API_KEY not set and rotator unavailable"}
    
    # Load image
    image_data = load_image_for_multimodal(image_path)
    if not image_data:
        return None, {"error": f"Failed to load image: {image_path}"}
    
    try:
        # Initialize client
        client = genai.Client(api_key=api_key)
        
        # Build multimodal content (text + image)
        parts_list = []
        parts_list.append(prompt)
        
        # Add image Part
        try:
            part = genai_types.Part(
                inline_data=genai_types.Blob(
                    data=image_data["bytes"],
                    mime_type=image_data["mime_type"]
                )
            )
            parts_list.append(part)
        except Exception as e:
            return None, {"error": f"Failed to create image Part: {e}"}
        
        # Build generation config
        config_kwargs = {
            "temperature": temperature,
            "max_output_tokens": 8192,  # Sufficient for JSON output
        }
        
        # Thinking config (Gemini 3 uses thinking_level)
        if thinking_level in ("minimal", "low", "medium", "high"):
            config_kwargs["thinking_config"] = genai_types.ThinkingConfig(
                thinking_level=thinking_level  # type: ignore
            )
        
        # RAG (Google Search)
        if rag_enabled:
            grounding_tool = genai_types.Tool(
                google_search=genai_types.GoogleSearch()
            )
            config_kwargs["tools"] = [grounding_tool]
        
        generation_config = genai_types.GenerateContentConfig(**config_kwargs)
        
        # Call LLM
        response = client.models.generate_content(
            model=model,
            contents=parts_list,
            config=generation_config,
        )
        
        # Extract text
        raw_text = (getattr(response, "text", None) or "").strip()
        if not raw_text:
            # Fallback: extract from candidates
            try:
                cands = getattr(response, "candidates", None) or []
                if cands:
                    content = getattr(cands[0], "content", None)
                    parts = getattr(content, "parts", None) or []
                    raw_text = "".join([(getattr(p, "text", "") or "") for p in parts]).strip()
            except Exception:
                pass
        
        if not raw_text:
            return None, {"error": "Empty response from LLM"}
        
        # Record success in rotator
        if _global_rotator is not None:
            try:
                _global_rotator.record_success()
            except Exception:
                pass  # Don't fail the call if record fails
        
        return raw_text, None
        
    except Exception as e:
        error_str = str(e)
        
        # Check if quota exhausted and rotate if needed
        if _global_rotator is not None:
            try:
                if _global_rotator.is_quota_exhausted_error(e):
                    print(f"[S6] Quota exhausted detected, rotating API key...", file=sys.stderr)
                    _global_rotator.rotate_on_quota_exhausted(error_message=error_str)
                    print(f"[S6] Rotated to new API key", file=sys.stderr)
                else:
                    # Record non-quota failure
                    _global_rotator.record_failure(error_message=error_str)
            except Exception as rot_err:
                print(f"[S6] Warning: Rotator operation failed: {rot_err}", file=sys.stderr)
        
        return None, {"error": f"LLM call failed: {e}"}

# =========================
# JSON Parsing
# =========================

def parse_positive_instructions_json(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Parse JSON response from S6 LLM output.
    
    Expected format:
    {
      "positive_instructions": ["instruction 1", "instruction 2", ...],
      "rationale": "explanation of changes"
    }
    
    Args:
        raw_text: Raw LLM response text
        
    Returns:
        Parsed JSON dict, or None if parsing fails
    """
    import re
    
    # Try 1: Direct JSON parse (if LLM returns clean JSON)
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, dict) and "positive_instructions" in parsed:
            return parsed
    except json.JSONDecodeError as e:
        print(f"[S6 Parser] Direct JSON parse failed: {e}", file=sys.stderr)
        pass
    
    # Try 2: Extract JSON from markdown code block
    # Pattern: ```json\n{...}\n```
    json_block_pattern = r"```(?:json)?\s*\n([\s\S]*?)\n```"
    match = re.search(json_block_pattern, raw_text, re.MULTILINE | re.DOTALL)
    if match:
        json_str = match.group(1).strip()
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict) and "positive_instructions" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass
    
    # Try 3: Find any JSON object in the response
    json_object_pattern = r"\{[\s\S]*\}"
    match = re.search(json_object_pattern, raw_text, re.MULTILINE | re.DOTALL)
    if match:
        json_str = match.group(0).strip()
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict) and "positive_instructions" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass
    
    # All parsing attempts failed
    print(f"Warning: Failed to parse JSON from LLM response. Preview: {raw_text[:200]}", file=sys.stderr)
    return None

# =========================
# Core S6 Function
# =========================

def convert_patch_hint_to_positive_instruction(
    *,
    s3_spec: Dict[str, Any],
    s4_image_path: Path,
    s5_patch_hints: List[str],
    model: str,
    thinking_level: str = "high",
    rag_enabled: bool = False,
    temperature: float = 0.3,
    timeout_s: int = 120,
    base_dir: Path,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Convert S5 prompt_patch_hint to positive instructions using LLM.
    
    Args:
        s3_spec: Original S3 image spec (prompt_en, modality, anatomy, etc.)
        s4_image_path: Path to S4 generated image
        s5_patch_hints: List of prompt_patch_hint strings from S5 validation
        model: LLM model name (Pro or Flash)
        thinking_level: Thinking level for LLM
        rag_enabled: Whether to enable RAG
        temperature: Temperature for generation
        timeout_s: Timeout in seconds
        base_dir: Project base directory (for prompt loading)
        
    Returns:
        (updated_spec, error): Updated S3 spec with positive_instructions, or (None, error_dict)
    """
    try:
        # Load .env file from base_dir
        load_env(base_dir)
        
        # Load prompt template
        try:
            template = load_prompt_template(base_dir)
        except Exception as e:
            return None, {"error": f"Failed to load prompt template: {e}"}
        
        # Extract fields from S3 spec
        modality = str(s3_spec.get("modality", "Unknown")).strip()
        anatomy_region = str(s3_spec.get("anatomy_region", "Unknown")).strip()
        view_or_sequence = str(s3_spec.get("view_or_sequence", "Unknown")).strip()
        
        # Extract key_findings_keywords (may be in image_hint or image_hint_v2)
        key_findings_keywords = ""
        image_hint = s3_spec.get("image_hint", {})
        if isinstance(image_hint, dict):
            key_findings_keywords = str(image_hint.get("key_findings_keywords", "")).strip()
        if not key_findings_keywords:
            image_hint_v2 = s3_spec.get("image_hint_v2", {})
            if isinstance(image_hint_v2, dict):
                diagnostic = image_hint_v2.get("diagnostic", {})
                if isinstance(diagnostic, dict):
                    key_findings_keywords = str(diagnostic.get("key_findings_keywords", "")).strip()
        
        original_prompt_en = str(s3_spec.get("prompt_en", "")).strip()
        
        # Format patch hints as bullet list
        patch_hints_text = "\n".join([f"- {hint}" for hint in s5_patch_hints])
        
        # Fill template
        prompt = template.format(
            modality=modality,
            anatomy_region=anatomy_region,
            view_or_sequence=view_or_sequence,
            key_findings_keywords=key_findings_keywords,
            original_prompt_en=original_prompt_en,
            patch_hints=patch_hints_text,
        )
        
        # Call LLM
        response_text, error = call_s6_llm(
            prompt=prompt,
            image_path=s4_image_path,
            model=model,
            thinking_level=thinking_level,
            rag_enabled=rag_enabled,
            temperature=temperature,
            timeout_s=timeout_s,
            base_dir=base_dir,
        )
        
        if error:
            return None, error
        
        if not response_text:
            return None, {"error": "Empty response from LLM"}
        
        # Parse JSON response
        parsed = parse_positive_instructions_json(response_text)
        if not parsed:
            # Show preview of response for debugging
            preview = response_text[:500] if response_text else "(empty)"
            return None, {"error": f"Failed to parse JSON from LLM response. Preview: {preview}"}
        
        # Extract positive instructions
        positive_instructions = parsed.get("positive_instructions", [])
        if not isinstance(positive_instructions, list):
            return None, {"error": "positive_instructions is not a list"}
        
        rationale = str(parsed.get("rationale", "")).strip()
        
        # Create updated S3 spec
        updated_spec = s3_spec.copy()
        updated_spec["positive_instructions"] = positive_instructions
        updated_spec["positive_instruction_rationale"] = rationale
        
        # Enhance prompt_en with positive instructions (optional, for transparency)
        # This creates a new field that S4 can use if needed
        if positive_instructions:
            enhanced_prompt = original_prompt_en + "\n\nPositive modification instructions:\n"
            enhanced_prompt += "\n".join([f"- {inst}" for inst in positive_instructions])
            updated_spec["prompt_en_enhanced"] = enhanced_prompt
        
        return updated_spec, None
    
    except Exception as e:
        import traceback
        tb_str = traceback.format_exc()
        print(f"[S6] Unexpected exception in convert_patch_hint_to_positive_instruction: {e}\n{tb_str}", file=sys.stderr)
        return None, {"error": f"Unexpected exception: {e}"}

# =========================
# CLI Entry Point
# =========================

def main():
    """CLI entry point for S6 agent (single-card test mode)."""
    parser = argparse.ArgumentParser(
        description="S6 Positive Instruction Agent - Convert S5 feedback to positive instructions"
    )
    parser.add_argument("--base_dir", type=Path, default=Path("."),
                        help="Base directory (default: current directory)")
    parser.add_argument("--run_tag", type=str, required=True,
                        help="Run tag (e.g., FINAL_DISTRIBUTION)")
    parser.add_argument("--arm", type=str, required=True,
                        help="Arm (e.g., G)")
    parser.add_argument("--group_id", type=str, required=True,
                        help="Group ID for testing")
    parser.add_argument("--entity_id", type=str, required=True,
                        help="Entity ID for testing")
    parser.add_argument("--card_role", type=str, required=True,
                        help="Card role (Q1/Q2)")
    parser.add_argument("--dry_run", action="store_true",
                        help="Dry run mode (print prompt, don't call LLM)")
    parser.add_argument("--model", type=str, choices=["pro", "flash"],
                        help="Override model selection (default: auto from spec_kind)")
    parser.add_argument("--temperature", type=float, default=S6_TEMPERATURE,
                        help=f"Temperature (default: {S6_TEMPERATURE})")
    parser.add_argument("--thinking_level", type=str, default=S6_THINKING_LEVEL,
                        choices=["minimal", "low", "medium", "high"],
                        help=f"Thinking level (default: {S6_THINKING_LEVEL})")
    parser.add_argument("--rag_enabled", action="store_true",
                        help="Enable RAG (default: disabled)")
    
    args = parser.parse_args()
    
    # Resolve paths
    base_dir = args.base_dir.resolve()
    
    # Load .env file early
    load_env(base_dir)
    data_dir = base_dir / "2_Data" / "metadata" / "generated" / args.run_tag
    
    s3_spec_path = data_dir / f"s3_image_spec__arm{args.arm}.jsonl"
    s5_validation_path = data_dir / f"s5_validation__arm{args.arm}.jsonl"
    
    # Load S3 specs
    print(f"[S6] Loading S3 specs from {s3_spec_path.name}...")
    if not s3_spec_path.exists():
        print(f"Error: S3 spec file not found: {s3_spec_path}", file=sys.stderr)
        return 1
    
    s3_specs = []
    with open(s3_spec_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                spec = json.loads(line)
                s3_specs.append(spec)
            except json.JSONDecodeError:
                continue
    
    # Find target spec
    target_spec = None
    for spec in s3_specs:
        if (
            str(spec.get("group_id", "")).strip() == args.group_id
            and str(spec.get("entity_id", "")).strip() == args.entity_id
            and str(spec.get("card_role", "")).strip().upper() == args.card_role.upper()
        ):
            target_spec = spec
            break
    
    if not target_spec:
        print(f"Error: Could not find S3 spec for group={args.group_id}, entity={args.entity_id}, role={args.card_role}",
              file=sys.stderr)
        return 1
    
    print(f"[S6] Found S3 spec: spec_kind={target_spec.get('spec_kind')}")
    
    # Load S5 validation results
    print(f"[S6] Loading S5 validation from {s5_validation_path.name}...")
    if not s5_validation_path.exists():
        print(f"Error: S5 validation file not found: {s5_validation_path}", file=sys.stderr)
        return 1
    
    # Find target validation record
    target_validation = None
    with open(s5_validation_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if str(record.get("group_id", "")).strip() == args.group_id:
                    target_validation = record
                    break
            except json.JSONDecodeError:
                continue
    
    if not target_validation:
        print(f"Error: Could not find S5 validation for group={args.group_id}", file=sys.stderr)
        return 1
    
    # Extract patch hints from S5 validation
    patch_hints = []
    s2_cards = target_validation.get("s2_cards_validation", {}).get("cards", [])
    for card in s2_cards:
        if (
            str(card.get("entity_id", "")).strip() == args.entity_id
            and str(card.get("card_role", "")).strip().upper() == args.card_role.upper()
        ):
            # Extract image validation issues
            img_val = card.get("card_image_validation", {})
            img_issues = img_val.get("issues", [])
            for issue in img_issues:
                hint = str(issue.get("prompt_patch_hint", "")).strip()
                if hint:
                    patch_hints.append(hint)
            break
    
    if not patch_hints:
        print(f"[S6] No patch hints found for this card. Nothing to do.")
        return 0
    
    print(f"[S6] Found {len(patch_hints)} patch hint(s):")
    for i, hint in enumerate(patch_hints, 1):
        print(f"  {i}. {hint}")
    
    # Find S4 image
    images_dir = data_dir / "images"
    # Sanitize entity_id for filesystem (replace : with _)
    sanitized_entity_id = args.entity_id.replace(":", "_")
    image_filename = f"IMG__{args.run_tag}__{args.group_id}__{sanitized_entity_id}__{args.card_role}.jpg"
    s4_image_path = images_dir / image_filename
    
    if not s4_image_path.exists():
        print(f"Error: S4 image not found: {s4_image_path}", file=sys.stderr)
        return 1
    
    print(f"[S6] Found S4 image: {s4_image_path.name}")
    
    # Determine model
    if args.model:
        model = S6_PRO_MODEL if args.model == "pro" else S6_FLASH_MODEL
        print(f"[S6] Using model (CLI override): {model}")
    else:
        # Auto-select based on spec_kind
        spec_kind = str(target_spec.get("spec_kind", "")).strip()
        if spec_kind == "S1_TABLE_VISUAL":
            model = S6_PRO_MODEL
            print(f"[S6] Using Pro model for TABLE: {model}")
        else:
            model = S6_FLASH_MODEL
            print(f"[S6] Using Flash model for CARD: {model}")
    
    # Dry run mode
    if args.dry_run:
        print("\n" + "="*60)
        print("[S6] DRY RUN MODE - Skipping LLM call")
        print("="*60)
        return 0
    
    # Call S6 agent
    print("\n" + "="*60)
    print("[S6] Calling LLM to generate positive instructions...")
    print("="*60)
    
    updated_spec, error = convert_patch_hint_to_positive_instruction(
        s3_spec=target_spec,
        s4_image_path=s4_image_path,
        s5_patch_hints=patch_hints,
        model=model,
        thinking_level=args.thinking_level,
        rag_enabled=args.rag_enabled,
        temperature=args.temperature,
        timeout_s=S6_TIMEOUT,
        base_dir=base_dir,
    )
    
    if error:
        print(f"\n[S6] ❌ Error: {error.get('error', 'Unknown error')}", file=sys.stderr)
        return 1
    
    if not updated_spec:
        print("\n[S6] ❌ No updated spec returned", file=sys.stderr)
        return 1
    
    # Print results
    print("\n" + "="*60)
    print("[S6] ✅ Success! Positive Instructions:")
    print("="*60)
    
    positive_instructions = updated_spec.get("positive_instructions", [])
    for i, inst in enumerate(positive_instructions, 1):
        print(f"\n{i}. {inst}")
    
    rationale = updated_spec.get("positive_instruction_rationale", "")
    if rationale:
        print("\n" + "-"*60)
        print("Rationale:")
        print(rationale)
    
    print("\n" + "="*60)
    print("[S6] Test completed successfully")
    print("="*60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


"""
MeducAI Positive Regen Orchestrator

Purpose:
- Orchestrate the positive regeneration pipeline for images with low S5 validation scores
- Filter S5 validation results by image_regeneration_trigger_score threshold
- Call S6 agent to convert negative feedback (prompt_patch_hint) into positive instructions
- Generate enhanced S3 specs and invoke S4 for image regeneration

Design:
- Reads S5 validation results and extracts cards below threshold
- Matches with S3 specs and S4 manifest to find corresponding data
- Calls S6 agent (06_s6_positive_instruction_agent.py) for each target
- Writes enhanced specs and invokes S4 with --image_type regen
"""

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    load_dotenv = None

# Import S6 agent
S6_AVAILABLE = False
s6_agent = None  # type: ignore

# Default values (will be overridden if S6 agent is available)
S6_PRO_MODEL = "gemini-3-pro-preview"
S6_FLASH_MODEL = "gemini-3-flash-preview"
S6_TIMEOUT = 120

try:
    # Try to import S6 agent from multiple possible paths
    # Method 1: Direct import (if running from project root)
    try:
        from src import s6_positive_instruction_agent as s6_agent  # type: ignore
        S6_AVAILABLE = True
    except ImportError:
        # Method 2: Import from src directory using the actual filename
        src_dir = Path(__file__).resolve().parent.parent.parent
        if src_dir not in sys.path:
            sys.path.insert(0, str(src_dir))
        # Import using the actual module name with 06_ prefix
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "s6_agent",
            src_dir / "06_s6_positive_instruction_agent.py"
        )
        if spec and spec.loader:
            s6_agent = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(s6_agent)
            S6_AVAILABLE = True
        else:
            raise ImportError("Could not load S6 agent module")
    
    # Import constants from S6 agent if available
    if S6_AVAILABLE and s6_agent is not None:
        S6_PRO_MODEL = getattr(s6_agent, 'S6_PRO_MODEL', S6_PRO_MODEL)
        S6_FLASH_MODEL = getattr(s6_agent, 'S6_FLASH_MODEL', S6_FLASH_MODEL)
        S6_TIMEOUT = getattr(s6_agent, 'S6_TIMEOUT', S6_TIMEOUT)
        
except ImportError as e:
    S6_AVAILABLE = False
    print(f"Warning: Could not import S6 agent: {e}", file=sys.stderr)
    print("  S6 agent will not be available. Dry-run mode will still work.", file=sys.stderr)


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
# Data Loading Utilities
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
                print(f"Warning: Failed to parse JSON line in {file_path}: {e}", file=sys.stderr)
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
# S5 Validation Processing
# =========================

def extract_regen_targets(
    s5_results: List[Dict[str, Any]],
    threshold: float = 80.0,
) -> List[Dict[str, Any]]:
    """
    Extract cards that need regeneration based on image_regeneration_trigger_score.
    Also checks card_regeneration_trigger_score to determine if card text was regenerated.
    
    Args:
        s5_results: List of S5 validation records (one per group)
        threshold: Score threshold (default: 80.0, regen if < threshold)
        
    Returns:
        List of regen target dicts with:
            - group_id
            - entity_id
            - card_role
            - score (image_regeneration_trigger_score)
            - card_score (card_regeneration_trigger_score, optional)
            - card_regen_triggered (bool): True if card text regeneration was triggered
            - patch_hints (list of prompt_patch_hint strings)
    """
    regen_targets = []
    
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
            
            # Check image_regeneration_trigger_score
            img_score = card.get("image_regeneration_trigger_score")
            if img_score is None:
                # No image score available (e.g., no image validation)
                continue
            
            if img_score >= threshold:
                # Score is above threshold, no regeneration needed
                continue
            
            # Check card_regeneration_trigger_score to determine if card text was regenerated
            card_score = card.get("card_regeneration_trigger_score")
            card_regen_triggered = False
            if card_score is not None:
                try:
                    card_score_val = float(card_score)
                    card_regen_triggered = card_score_val < threshold
                except (ValueError, TypeError):
                    # If card_score is not a valid number, assume no card regen
                    card_regen_triggered = False
            
            # Extract prompt_patch_hints from card_image_validation
            patch_hints = []
            img_val = card.get("card_image_validation", {})
            
            # Try to extract from issues
            issues = img_val.get("issues", [])
            for issue in issues:
                hint = str(issue.get("prompt_patch_hint", "")).strip()
                if hint:
                    patch_hints.append(hint)
            
            # Try to extract from prompt_patch_hints (alternative field name)
            if not patch_hints:
                hints_list = img_val.get("prompt_patch_hints", [])
                if isinstance(hints_list, list):
                    patch_hints = [str(h).strip() for h in hints_list if str(h).strip()]
            
            # If no patch hints, skip this card
            if not patch_hints:
                print(f"[Regen] Warning: Card {group_id}/{entity_id}/{card_role} has low score ({img_score:.1f}) but no patch hints. Skipping.")
                continue
            
            regen_targets.append({
                "group_id": group_id,
                "entity_id": entity_id,
                "card_role": card_role,
                "score": img_score,
                "card_score": card_score,
                "card_regen_triggered": card_regen_triggered,
                "patch_hints": patch_hints,
            })
    
    return regen_targets


# =========================
# Spec and Manifest Matching
# =========================

def find_s3_spec(
    s3_specs: List[Dict[str, Any]],
    group_id: str,
    entity_id: str,
    card_role: str,
) -> Optional[Dict[str, Any]]:
    """Find matching S3 spec for a given card."""
    for spec in s3_specs:
        if (
            str(spec.get("group_id", "")).strip() == group_id
            and str(spec.get("entity_id", "")).strip() == entity_id
            and str(spec.get("card_role", "")).strip().upper() == card_role.upper()
        ):
            return spec
    return None


def find_s4_image(
    s4_manifest: List[Dict[str, Any]],
    group_id: str,
    entity_id: str,
    card_role: str,
) -> Optional[Dict[str, Any]]:
    """Find matching S4 image manifest entry for a given card."""
    for entry in s4_manifest:
        if (
            str(entry.get("group_id", "")).strip() == group_id
            and str(entry.get("entity_id", "")).strip() == entity_id
            and str(entry.get("card_role", "")).strip().upper() == card_role.upper()
        ):
            return entry
    return None


# =========================
# Positive Regen Pipeline
# =========================

def run_positive_regen(
    base_dir: Path,
    run_tag: str,
    arm: str,
    threshold: float = 80.0,
    workers: int = 4,
    dry_run: bool = False,
    only_entity_ids: Optional[List[str]] = None,
    temperature: float = 0.3,
    thinking_level: str = "high",
    rag_enabled: bool = False,
) -> int:
    """
    Positive Regen orchestrator.
    
    Steps:
    1. Load S5 validation results
    2. Filter cards with image_regeneration_trigger_score < threshold
    3. For each target:
       a. Load S3 spec
       b. Load S4 image path
       c. Extract S5 patch hints
       d. Call S6 agent to generate positive instructions
       e. Write enhanced S3 spec
    4. Call S4 with enhanced specs and --image_type regen
    
    Args:
        base_dir: Project base directory
        run_tag: Run tag (e.g., FINAL_DISTRIBUTION)
        arm: Arm identifier (e.g., G)
        threshold: Image score threshold for regeneration (default: 80.0)
        workers: Number of parallel workers for S4 (default: 4)
        dry_run: If True, don't call S6 or S4, just show plan
        only_entity_ids: If provided, only process these entity IDs (for testing)
        temperature: Temperature for S6 LLM calls
        thinking_level: Thinking level for S6 LLM calls
        rag_enabled: Whether to enable RAG for S6 calls
        
    Returns:
        Exit code (0 = success, non-zero = error)
    """
    print("="*80)
    print("Positive Regen Orchestrator")
    print("="*80)
    print(f"RUN_TAG: {run_tag}")
    print(f"ARM: {arm}")
    print(f"Threshold: {threshold}")
    print(f"Dry run: {dry_run}")
    if only_entity_ids:
        print(f"Filter: Only entity IDs: {', '.join(only_entity_ids)}")
    print()
    
    # Resolve paths
    base_dir = base_dir.resolve()
    
    # Load .env file early (defensive approach)
    load_env(base_dir)
    data_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    
    s5_path = data_dir / f"s5_validation__arm{arm}.jsonl"
    
    # Prepare S3 spec paths (both baseline and regen)
    s3_spec_path_regen = data_dir / f"s3_image_spec__arm{arm}__regen.jsonl"
    s3_spec_path_baseline = data_dir / f"s3_image_spec__arm{arm}.jsonl"
    
    images_dir = data_dir / "images"
    
    # 1. Load S5 validation results
    print("[Step 1] Loading S5 validation results...")
    if not s5_path.exists():
        print(f"Error: S5 validation file not found: {s5_path}", file=sys.stderr)
        return 1
    
    s5_results = load_jsonl(s5_path)
    print(f"  Loaded {len(s5_results)} group(s) from S5 validation")
    
    # 2. Extract regen targets
    print(f"\n[Step 2] Filtering cards with image_regeneration_trigger_score < {threshold}...")
    regen_targets = extract_regen_targets(s5_results, threshold=threshold)
    
    # Filter out card_regen cases (they should be handled by S4 direct, not S6+S4)
    # Only process image_only_regen cases (card_score >= threshold, img_score < threshold)
    regen_targets_original_count = len(regen_targets)
    regen_targets = [
        t for t in regen_targets
        if not t.get("card_regen_triggered", False)
    ]
    card_regen_filtered_count = regen_targets_original_count - len(regen_targets)
    if card_regen_filtered_count > 0:
        print(f"  Filtered out {card_regen_filtered_count} card_regen case(s) (they should use S4 direct, not S6+S4)")
    
    if only_entity_ids:
        regen_targets = [
            t for t in regen_targets
            if t["entity_id"] in only_entity_ids
        ]
        print(f"  Filtered to {len(regen_targets)} target(s) (only_entity_ids filter)")
    else:
        print(f"  Found {len(regen_targets)} card(s) needing regeneration (image_only_regen)")
    
    if not regen_targets:
        print("\n✓ No cards need regeneration. Done.")
        return 0
    
    # Show targets with regen type
    print("\n  Regeneration targets:")
    card_regen_count = 0
    image_only_regen_count = 0
    for i, target in enumerate(regen_targets, 1):
        regen_type = "카드+이미지 리젠" if target.get("card_regen_triggered", False) else "이미지만 리젠"
        if target.get("card_regen_triggered", False):
            card_regen_count += 1
        else:
            image_only_regen_count += 1
        print(f"    {i}. {target['group_id']}/{target['entity_id']}/{target['card_role']} (이미지 점수: {target['score']:.1f}, 타입: {regen_type})")
        for j, hint in enumerate(target['patch_hints'], 1):
            print(f"       Hint {j}: {hint[:80]}{'...' if len(hint) > 80 else ''}")
    
    print(f"\n  요약: 카드 리젠 {card_regen_count}개, 이미지만 리젠 {image_only_regen_count}개")
    
    # 3. Load S3 specs (both baseline and repaired if available)
    print(f"\n[Step 3] Loading S3 specs...")
    
    # Load baseline S3 specs (required)
    if not s3_spec_path_baseline.exists():
        print(f"Error: Baseline S3 spec file not found: {s3_spec_path_baseline}", file=sys.stderr)
        return 1
    
    s3_specs_baseline = load_jsonl(s3_spec_path_baseline)
    print(f"  Loaded {len(s3_specs_baseline)} baseline S3 spec(s)")
    
    # Load regen S3 specs (optional)
    s3_specs_regen = []
    if s3_spec_path_regen.exists():
        s3_specs_regen = load_jsonl(s3_spec_path_regen)
        print(f"  Loaded {len(s3_specs_regen)} regen S3 spec(s)")
    else:
        print(f"  Regen S3 spec not found (will use baseline for all cards)")
    
    print(f"  Images will be loaded from: {images_dir}")
    
    # 4. Process each target
    print(f"\n[Step 4] Processing targets with S6 agent...")
    
    if not S6_AVAILABLE and not dry_run:
        print("Error: S6 agent not available. Cannot proceed.", file=sys.stderr)
        return 1
    
    enhanced_specs = []
    success_count = 0
    error_count = 0
    
    for i, target in enumerate(regen_targets, 1):
        group_id = target["group_id"]
        entity_id = target["entity_id"]
        card_role = target["card_role"]
        
        print(f"\n  [{i}/{len(regen_targets)}] {group_id}/{entity_id}/{card_role}")
        
        # Determine regen type
        card_regen_triggered = target.get("card_regen_triggered", False)
        regen_type = "카드+이미지 리젠" if card_regen_triggered else "이미지만 리젠"
        print(f"    리젠 타입: {regen_type}")
        
        # Select S3 spec based on regen type
        # - 카드 리젠이 뜬 경우: repaired 우선, 없으면 baseline
        # - 이미지만 리젠인 경우: baseline 사용 (repaired 무시)
        s3_spec = None
        s3_spec_source = None
        
        if card_regen_triggered:
            # 카드 리젠이 뜬 경우: regen 우선
            if s3_specs_regen:
                s3_spec = find_s3_spec(s3_specs_regen, group_id, entity_id, card_role)
                if s3_spec:
                    s3_spec_source = "regen"
                else:
                    # Regen에 없으면 baseline 사용
                    s3_spec = find_s3_spec(s3_specs_baseline, group_id, entity_id, card_role)
                    if s3_spec:
                        s3_spec_source = "baseline (regen not found)"
                        print(f"    ⚠️  Warning: Card regen triggered but regen S3 spec not found, using baseline")
            else:
                # Regen 파일이 없으면 baseline 사용
                s3_spec = find_s3_spec(s3_specs_baseline, group_id, entity_id, card_role)
                if s3_spec:
                    s3_spec_source = "baseline (regen file not available)"
                    print(f"    ⚠️  Warning: Card regen triggered but regen S3 spec file not available, using baseline")
        else:
            # 이미지만 리젠인 경우: baseline 사용
            s3_spec = find_s3_spec(s3_specs_baseline, group_id, entity_id, card_role)
            if s3_spec:
                s3_spec_source = "baseline"
        
        if not s3_spec:
            print(f"    ❌ Error: S3 spec not found. Skipping.")
            error_count += 1
            continue
        
        spec_kind = s3_spec.get("spec_kind", "")
        print(f"    Found S3 spec (spec_kind: {spec_kind}, source: {s3_spec_source})")
        
        # Construct S4 image path directly (images follow predictable naming pattern)
        # Sanitize entity_id for filesystem (replace : with _)
        sanitized_entity_id = entity_id.replace(":", "_")
        image_filename = f"IMG__{run_tag}__{group_id}__{sanitized_entity_id}__{card_role}.jpg"
        s4_image_path = images_dir / image_filename
        
        if not s4_image_path.exists():
            print(f"    ❌ Error: S4 image not found: {s4_image_path.name}. Skipping.")
            error_count += 1
            continue
        
        print(f"    Found S4 image: {s4_image_path.name}")
        
        # Determine model based on spec_kind
        if spec_kind == "S1_TABLE_VISUAL":
            model = S6_PRO_MODEL
            print(f"    Using Pro model (TABLE): {model}")
        else:
            model = S6_FLASH_MODEL
            print(f"    Using Flash model (CARD): {model}")
        
        # Dry run mode
        if dry_run:
            print(f"    [DRY RUN] Would call S6 agent with {len(target['patch_hints'])} patch hint(s)")
            success_count += 1
            continue
        
        # Call S6 agent
        print(f"    Calling S6 agent to generate positive instructions...")
        try:
            if s6_agent is None:
                raise RuntimeError("S6 agent not available")
            
            updated_spec, error = s6_agent.convert_patch_hint_to_positive_instruction(
                s3_spec=s3_spec,
                s4_image_path=s4_image_path,
                s5_patch_hints=target["patch_hints"],
                model=model,
                thinking_level=thinking_level,
                rag_enabled=rag_enabled,
                temperature=temperature,
                timeout_s=S6_TIMEOUT,
                base_dir=base_dir,
            )
            
            if error:
                print(f"    ❌ Error from S6: {error.get('error', 'Unknown error')}")
                error_count += 1
                continue
            
            if not updated_spec:
                print(f"    ❌ Error: No updated spec returned from S6")
                error_count += 1
                continue
            
            # Copy prompt_en_enhanced → prompt_en (for batch_image_generator compatibility)
            if "prompt_en_enhanced" in updated_spec:
                updated_spec["prompt_en"] = updated_spec["prompt_en_enhanced"]
            
            # Add metadata for AppSheet export
            updated_spec["_regen_metadata"] = {
                "regen_type": "카드+이미지 리젠" if card_regen_triggered else "이미지만 리젠",
                "s3_spec_source": s3_spec_source,
                "card_regen_triggered": card_regen_triggered,
                "image_score": target.get("score"),
                "card_score": target.get("card_score"),
            }
            
            # Show generated instructions
            positive_instructions = updated_spec.get("positive_instructions", [])
            print(f"    ✓ Generated {len(positive_instructions)} positive instruction(s):")
            for j, inst in enumerate(positive_instructions, 1):
                print(f"      {j}. {inst[:80]}{'...' if len(inst) > 80 else ''}")
            
            enhanced_specs.append(updated_spec)
            success_count += 1
            
        except Exception as e:
            print(f"    ❌ Exception calling S6: {e}")
            error_count += 1
            continue
    
    # Summary
    print("\n" + "="*80)
    print(f"[Step 4] Processing complete:")
    print(f"  Success: {success_count}/{len(regen_targets)}")
    print(f"  Errors: {error_count}/{len(regen_targets)}")
    
    if error_count > 0:
        print(f"\n⚠️  Warning: {error_count} card(s) failed. Check errors above.")
    
    if dry_run:
        print("\n[DRY RUN] Stopping before writing specs or calling S4")
        return 0
    
    if not enhanced_specs:
        print("\n❌ Error: No enhanced specs generated. Cannot proceed to S4.")
        return 1
    
    # 5. Write enhanced specs (overwrite regen file)
    print(f"\n[Step 5] Writing enhanced S3 specs...")
    temp_spec_path = data_dir / f"s3_image_spec__arm{arm}__regen.jsonl"
    write_jsonl(temp_spec_path, enhanced_specs)
    print(f"  Written {len(enhanced_specs)} spec(s) to: {temp_spec_path.name}")
    
    # 6. Call S4 with enhanced specs
    print(f"\n[Step 6] Calling S4 Image Generator with --image_type regen...")
    s4_script_path = base_dir / "3_Code" / "src" / "04_s4_image_generator.py"
    
    if not s4_script_path.exists():
        print(f"Error: S4 script not found: {s4_script_path}", file=sys.stderr)
        return 1
    
    s4_cmd = [
        sys.executable,  # Use same Python interpreter
        str(s4_script_path),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
        "--spec_path", str(temp_spec_path),
        "--image_type", "regen",
        "--workers", str(workers),
    ]
    
    print(f"  Command: {' '.join(s4_cmd)}")
    print()
    
    try:
        result = subprocess.run(s4_cmd, check=True)
        print("\n✓ S4 completed successfully")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error: S4 failed with exit code {e.returncode}", file=sys.stderr)
        return e.returncode
    except Exception as e:
        print(f"\n❌ Error running S4: {e}", file=sys.stderr)
        return 1


# =========================
# CLI Entry Point
# =========================

def main():
    """CLI entry point for Positive Regen orchestrator."""
    parser = argparse.ArgumentParser(
        description="Positive Regen Orchestrator - Generate improved images using S6 agent + S4 regen"
    )
    parser.add_argument("--base_dir", type=Path, default=Path("."),
                        help="Base directory (default: current directory)")
    parser.add_argument("--run_tag", type=str, required=True,
                        help="Run tag (e.g., FINAL_DISTRIBUTION)")
    parser.add_argument("--arm", type=str, required=True,
                        help="Arm (e.g., G)")
    parser.add_argument("--threshold", type=float, default=80.0,
                        help="Image score threshold for regeneration (default: 80.0)")
    parser.add_argument("--workers", type=int, default=4,
                        help="Number of parallel workers for S4 (default: 4)")
    parser.add_argument("--dry_run", action="store_true",
                        help="Dry run mode (don't call S6 or S4, just show plan)")
    parser.add_argument("--only_entity_id", type=str, action="append", dest="only_entity_ids",
                        help="Only process this entity ID (can specify multiple times for testing)")
    parser.add_argument("--temperature", type=float, default=0.3,
                        help="Temperature for S6 LLM calls (default: 0.3)")
    parser.add_argument("--thinking_level", type=str, default="high",
                        choices=["minimal", "low", "medium", "high"],
                        help="Thinking level for S6 LLM calls (default: high)")
    parser.add_argument("--rag_enabled", action="store_true",
                        help="Enable RAG for S6 calls (default: disabled)")
    
    args = parser.parse_args()
    
    exit_code = run_positive_regen(
        base_dir=args.base_dir,
        run_tag=args.run_tag,
        arm=args.arm,
        threshold=args.threshold,
        workers=args.workers,
        dry_run=args.dry_run,
        only_entity_ids=args.only_entity_ids,
        temperature=args.temperature,
        thinking_level=args.thinking_level,
        rag_enabled=args.rag_enabled,
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()


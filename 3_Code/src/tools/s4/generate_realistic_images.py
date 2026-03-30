#!/usr/bin/env python3
"""
Generate Realistic images for cards assigned in FINAL QA.

This script reads Assignments.csv and generates REALISTIC images only for:
1. Specialist 330 pool cards (all specialist assignments)
2. Which ensures all calibration items (33 unique) are also included

The script:
1. Reads Assignments.csv to identify unique cards needing realistic images
2. Filters S3 image spec to only include those cards
3. Calls S4 image generator with --image_type realistic

Supports two modes:
1. Synchronous (default): Uses 04_s4_image_generator.py for real-time generation
2. Batch mode (--batch): Uses batch_image_generator.py for async batch generation

Reference:
- AppSheet_Realistic_Image_Evaluation_Design.md (Section 0.3)
- HANDOFF_2026-01-15_FINAL_DISTRIBUTION_Execution_Guide.md (Phase 5-3)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_THIS_FILE = Path(__file__).resolve()
_S4_TOOLS_DIR = _THIS_FILE.parent  # .../3_Code/src/tools/s4
_TOOLS_DIR = _S4_TOOLS_DIR.parent  # .../3_Code/src/tools
_SRC_ROOT = _TOOLS_DIR.parent  # .../3_Code/src

# Add src to path for imports
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))


def _read_csv(path: Path) -> List[Dict[str, Any]]:
    """Read CSV file and return list of dicts."""
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read JSONL file and return list of dicts."""
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    """Write list of dicts to JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_card_uid(card_uid: str) -> Tuple[str, str, str]:
    """
    Parse card_uid to extract group_id, entity_id, card_role.
    
    card_uid format: "{group_id}::{entity_id}__{card_role}__{card_idx}"
    Example: "grp_001::entity_001__Q1__0"
    
    Returns:
        (group_id, entity_id, card_role)
    """
    if not card_uid or "::" not in card_uid:
        return ("", "", "")
    
    parts = card_uid.split("::")
    if len(parts) != 2:
        return ("", "", "")
    
    group_id = parts[0].strip()
    card_id_part = parts[1].strip()
    
    # card_id format: "{entity_id}__{card_role}__{card_idx}"
    card_parts = card_id_part.split("__")
    if len(card_parts) >= 2:
        entity_id = card_parts[0].strip()
        card_role = card_parts[1].strip().upper()
        return (group_id, entity_id, card_role)
    
    return (group_id, "", "")


def get_specialist_pool_cards(assignments_path: Path) -> Set[Tuple[str, str, str]]:
    """
    Get unique cards from specialist assignments (330 pool).
    
    Returns:
        Set of (group_id, entity_id, card_role) tuples for cards needing realistic images
    """
    assignments = _read_csv(assignments_path)
    
    specialist_cards: Set[Tuple[str, str, str]] = set()
    
    for row in assignments:
        rater_role = row.get("rater_role", "").strip().lower()
        card_uid = row.get("card_uid", "").strip()
        
        # Only include specialist assignments (330 pool)
        if rater_role == "specialist" and card_uid:
            group_id, entity_id, card_role = parse_card_uid(card_uid)
            if group_id and entity_id and card_role:
                specialist_cards.add((group_id, entity_id, card_role))
    
    return specialist_cards


def filter_s3_spec(
    s3_spec_path: Path,
    target_cards: Set[Tuple[str, str, str]],
) -> List[Dict[str, Any]]:
    """
    Filter S3 image spec to only include cards that need realistic images.
    
    Args:
        s3_spec_path: Path to s3_image_spec JSONL file
        target_cards: Set of (group_id, entity_id, card_role) tuples
    
    Returns:
        List of filtered S3 spec entries
    """
    specs = _read_jsonl(s3_spec_path)
    
    filtered: List[Dict[str, Any]] = []
    
    for spec in specs:
        spec_kind = str(spec.get("spec_kind", "")).strip()
        
        # Only include S2_CARD_IMAGE specs (not TABLE or CONCEPT)
        if spec_kind != "S2_CARD_IMAGE":
            continue
        
        group_id = str(spec.get("group_id", "")).strip()
        entity_id = str(spec.get("entity_id", "")).strip()
        card_role = str(spec.get("card_role", "")).strip().upper()
        
        if (group_id, entity_id, card_role) in target_cards:
            filtered.append(spec)
    
    return filtered


def generate_realistic_images(
    *,
    base_dir: Path,
    run_tag: str,
    arm: str,
    assignments_path: Optional[Path],
    workers: int = 1,
    dry_run: bool = False,
    image_model: Optional[str] = None,
    resume: bool = False,
    overwrite: bool = False,
    use_batch: bool = False,
    check_status: bool = False,
) -> int:
    """
    Generate realistic images for specialist pool cards.
    
    Args:
        base_dir: Project base directory
        run_tag: Run tag for output directory
        arm: Arm identifier (e.g., "G")
        assignments_path: Path to Assignments.csv (required for generation, optional for check_status)
        workers: Number of parallel workers
        dry_run: If True, only show what would be generated
        image_model: Override image model
        resume: Resume from previous run
        overwrite: Overwrite existing images
        use_batch: If True, use batch API for async generation
        check_status: If True, check batch status instead of generating
    
    Returns:
        Exit code (0 = success)
    """
    out_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    
    # S3 spec 파일 경로 우선순위:
    # 1. s3_image_spec__armG__realistic.jsonl (S3에서 --image-style realistic로 생성된 파일)
    # 2. s3_image_spec__armG.jsonl (기본 diagram 파일 - 필터링 후 사용)
    s3_realistic_spec_path = out_dir / f"s3_image_spec__arm{arm}__realistic.jsonl"
    s3_diagram_spec_path = out_dir / f"s3_image_spec__arm{arm}.jsonl"
    
    # Realistic S3 spec이 있으면 우선 사용
    if s3_realistic_spec_path.exists():
        s3_spec_path = s3_realistic_spec_path
        use_native_realistic = True
        print(f"[Realistic] Using native realistic S3 spec: {s3_spec_path}")
    else:
        s3_spec_path = s3_diagram_spec_path
        use_native_realistic = False
        print(f"[Realistic] Using diagram S3 spec (will filter): {s3_spec_path}")
    
    # 필터링된 임시 spec 파일 경로
    temp_spec_path = out_dir / f"s3_image_spec__arm{arm}__realistic_filtered.jsonl"
    
    # Batch mode: check status only
    if check_status:
        batch_cmd = [
            sys.executable,
            str(_TOOLS_DIR / "batch" / "batch_image_generator.py"),
            "--base_dir", str(base_dir),
            "--check_status",
            "--image_type", "realistic",
        ]
        print(f"[Realistic] Checking batch status...")
        import subprocess
        result = subprocess.run(batch_cmd, cwd=str(base_dir))
        return result.returncode
    
    if not s3_spec_path.exists():
        print(f"[ERROR] S3 spec file not found: {s3_spec_path}")
        return 1
    
    if assignments_path is None or not assignments_path.exists():
        print(f"[ERROR] Assignments file not found: {assignments_path}")
        return 1
    
    print(f"[Realistic] Loading assignments from: {assignments_path}")
    specialist_cards = get_specialist_pool_cards(assignments_path)
    print(f"[Realistic] Found {len(specialist_cards)} unique cards in specialist 330 pool")
    
    if not specialist_cards:
        print("[WARN] No specialist assignments found. Nothing to generate.")
        return 0
    
    # Filter S3 spec to only include target cards
    print(f"[Realistic] Loading S3 spec from: {s3_spec_path}")
    filtered_specs = filter_s3_spec(s3_spec_path, specialist_cards)
    print(f"[Realistic] Filtered to {len(filtered_specs)} image specs for realistic generation")
    
    if not filtered_specs:
        print("[WARN] No matching specs found for specialist cards. Nothing to generate.")
        return 0
    
    # Create filtered S3 spec file for realistic images
    _write_jsonl(temp_spec_path, filtered_specs)
    print(f"[Realistic] Created realistic spec file: {temp_spec_path}")
    
    # Show summary of what will be generated
    groups = set()
    entities = set()
    for spec in filtered_specs:
        groups.add(spec.get("group_id", ""))
        entities.add(spec.get("entity_id", ""))
    
    mode_str = "BATCH" if use_batch else "SYNC"
    print(f"\n[Realistic] Summary ({mode_str} mode):")
    print(f"  - Groups: {len(groups)}")
    print(f"  - Entities: {len(entities)}")
    print(f"  - Image specs: {len(filtered_specs)}")
    print(f"  - Workers: {workers}")
    print(f"  - Output: images_realistic/")
    print()
    
    if dry_run:
        print(f"[DRY RUN] Would generate realistic images using {mode_str} mode")
        return 0
    
    import subprocess
    
    if use_batch:
        # Use batch API for async generation
        batch_cmd = [
            sys.executable,
            str(_TOOLS_DIR / "batch" / "batch_image_generator.py"),
            "--input", str(temp_spec_path),
            "--base_dir", str(base_dir),
            "--run_tag", run_tag,
            "--image_type", "realistic",
        ]
        
        if image_model:
            batch_cmd.extend(["--model", image_model])
        
        if resume:
            batch_cmd.append("--resume")
        
        print(f"\n[Realistic] Starting batch image generator...")
        print(f"[Realistic] Command: {' '.join(batch_cmd)}")
        print()
        
        result = subprocess.run(batch_cmd, cwd=str(base_dir))
        
        if result.returncode != 0:
            print(f"\n[ERROR] Batch image generator failed with exit code {result.returncode}")
            return result.returncode
        
        print(f"\n[Realistic] Batch submitted! Check status with: --check_status")
        return 0
    
    # Synchronous mode: use S4 generator with filters
    # Extract unique group_ids, entity_ids, card_roles for S4 filtering
    group_ids = sorted(set(g for g, _, _ in specialist_cards))
    entity_ids = sorted(set(e for _, e, _ in specialist_cards))
    card_roles = sorted(set(r for _, _, r in specialist_cards))
    
    # Build S4 command
    s4_cmd = [
        sys.executable,
        str(_SRC_ROOT / "04_s4_image_generator.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
        "--image_type", "realistic",
        "--workers", str(workers),
        "--only_spec_kind", "S2_CARD_IMAGE",  # Only card images, not tables
    ]
    
    # Add group filters
    for gid in group_ids:
        s4_cmd.extend(["--only_group_id", gid])
    
    # Add entity filters
    for eid in entity_ids:
        s4_cmd.extend(["--only_entity_id", eid])
    
    # Add card role filters
    for role in card_roles:
        s4_cmd.extend(["--only_card_role", role])
    
    if image_model:
        s4_cmd.extend(["--image_model", image_model])
    
    if resume:
        s4_cmd.append("--resume")
    
    if overwrite:
        s4_cmd.append("--overwrite_existing")
    
    # Execute S4 generator
    print(f"\n[Realistic] Starting S4 image generator...")
    print(f"[Realistic] Command: {' '.join(s4_cmd)}")
    print()
    
    result = subprocess.run(s4_cmd, cwd=str(base_dir))
    
    if result.returncode != 0:
        print(f"\n[ERROR] S4 image generator failed with exit code {result.returncode}")
        return result.returncode
    
    # Verify output
    images_dir = out_dir / "images_realistic"
    if images_dir.exists():
        image_count = len(list(images_dir.glob("*.jpg")))
        print(f"\n[Realistic] Generated {image_count} images in: {images_dir}")
    else:
        print(f"\n[WARN] Images directory not found: {images_dir}")
    
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Realistic images for FINAL QA specialist pool cards"
    )
    parser.add_argument(
        "--base_dir",
        type=Path,
        default=Path("."),
        help="Project base directory (default: current directory)",
    )
    parser.add_argument(
        "--run_tag",
        type=str,
        required=True,
        help="Run tag (e.g., FINAL_DISTRIBUTION)",
    )
    parser.add_argument(
        "--arm",
        type=str,
        default="G",
        help="Arm identifier (default: G)",
    )
    parser.add_argument(
        "--assignments",
        type=Path,
        default=None,
        help="Path to Assignments.csv file (required for generation, not for --check_status)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers (default: 1)",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Show what would be generated without actually generating",
    )
    parser.add_argument(
        "--image_model",
        type=str,
        default=None,
        help="Override image model (default: from env or nano-banana-pro)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous run (retry failed images)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing images",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Use batch API for async generation (faster for large batches)",
    )
    parser.add_argument(
        "--check_status",
        action="store_true",
        help="Check status of batch jobs instead of generating",
    )
    
    args = parser.parse_args()
    
    base_dir = args.base_dir.resolve()
    
    # Validate assignments path (required unless --check_status)
    if not args.check_status and args.assignments is None:
        print("[ERROR] --assignments is required (unless using --check_status)")
        return 1
    
    assignments_path = args.assignments.resolve() if args.assignments else None
    
    try:
        return generate_realistic_images(
            base_dir=base_dir,
            run_tag=args.run_tag,
            arm=args.arm.upper(),
            assignments_path=assignments_path,
            workers=args.workers,
            dry_run=args.dry_run,
            image_model=args.image_model,
            resume=args.resume,
            overwrite=args.overwrite,
            use_batch=args.batch,
            check_status=args.check_status,
        )
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())


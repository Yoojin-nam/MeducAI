#!/usr/bin/env python3
"""
Script to generate S2 cards and run S5 validation only for entities that are missing from existing S2 results.

Usage:
    python3 3_Code/scripts/generate_missing_entities_s2_s5.py \\
        --base_dir /path/to/workspace/workspace/MeducAI \\
        --run_tag FINAL_image_prompt_v2req5 \\
        --arm G \\
        --mode FINAL \\
        [--stage 2] \\
        [--workers 1] \\
        [--workers_s5 1] \\
        [--dry_run]

This script:
1. Reads S1 struct to get all entities per group
2. Reads existing S2 results to find which entities already have cards
3. Identifies groups with missing entities
4. Runs S2 generation for groups with missing entities (via --only_group_id)
5. Deduplicates S2 results (keeps latest per entity)
6. Runs S5 validation on the updated S2 results
7. Generates S5 report

Note: The current S2 generation code processes entire groups, so all entities in a group
will be regenerated. The script deduplicates the results afterwards to keep only the
latest entry per entity.
"""

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set


def load_s1_entities(s1_path: Path) -> Dict[str, List[str]]:
    """Load entity names by group_id from S1 struct."""
    entities_by_group = {}
    if not s1_path.exists():
        return entities_by_group
    
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                gid = rec.get("group_id", "")
                entity_list = rec.get("entity_list", [])
                entity_names = []
                for e in entity_list:
                    if isinstance(e, dict):
                        name = e.get("entity_name", "").strip()
                    else:
                        name = str(e).strip()
                    if name:
                        entity_names.append(name)
                if gid and entity_names:
                    entities_by_group[gid] = entity_names
            except json.JSONDecodeError:
                continue
    
    return entities_by_group


def load_s2_entities(s2_path: Path) -> Dict[str, Set[str]]:
    """Load entity names by group_id from S2 results."""
    entities_by_group = defaultdict(set)
    if not s2_path.exists():
        return entities_by_group
    
    with open(s2_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                gid = rec.get("group_id", "")
                entity_name = rec.get("entity_name", "").strip()
                if gid and entity_name:
                    entities_by_group[gid].add(entity_name)
            except json.JSONDecodeError:
                continue
    
    return entities_by_group


def find_missing_entities(
    s1_entities: Dict[str, List[str]],
    s2_entities: Dict[str, Set[str]]
) -> Dict[str, List[str]]:
    """Find entities that exist in S1 but not in S2."""
    missing_by_group = {}
    
    for gid, s1_list in s1_entities.items():
        s2_set = s2_entities.get(gid, set())
        missing = [e for e in s1_list if e not in s2_set]
        if missing:
            missing_by_group[gid] = missing
    
    return missing_by_group


def dedup_s2_results(s2_path: Path) -> None:
    """Deduplicate S2 results, keeping only the latest entry per (group_id, entity_name)."""
    if not s2_path.exists():
        return
    
    # Read all records
    records = []
    with open(s2_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                records.append(rec)
            except json.JSONDecodeError:
                continue
    
    if not records:
        return
    
    # Group by (group_id, entity_name) and keep latest (assume order reflects recency)
    latest_by_key = {}
    for rec in records:
        gid = rec.get("group_id", "")
        entity_name = rec.get("entity_name", "").strip()
        key = (gid, entity_name)
        # Keep the last occurrence (assumes file order reflects recency)
        latest_by_key[key] = rec
    
    # Write back deduplicated records
    backup_path = s2_path.with_suffix(s2_path.suffix + ".backup")
    print(f"  Creating backup: {backup_path}")
    s2_path.rename(backup_path)
    
    print(f"  Writing deduplicated results: {len(latest_by_key)} unique entities")
    with open(s2_path, "w", encoding="utf-8") as f:
        for rec in latest_by_key.values():
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    
    print(f"  ✓ Deduplication complete (removed {len(records) - len(latest_by_key)} duplicate entries)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate S2 cards and run S5 validation only for missing entities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base_dir", type=str, required=True, help="Project base directory")
    parser.add_argument("--run_tag", type=str, required=True, help="Run tag (e.g., FINAL_image_prompt_v2req5)")
    parser.add_argument("--arm", type=str, required=True, help="Arm identifier (A-F)")
    parser.add_argument("--mode", type=str, default="FINAL", help="Mode: FINAL or S0")
    parser.add_argument("--stage", type=str, default="2", help="Stage: 2 (S2 only) or both")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers for S2 generation")
    parser.add_argument("--workers_s5", type=int, default=1, help="Number of workers for S5 validation")
    parser.add_argument("--skip_s5", action="store_true", help="Skip S5 validation and report generation")
    parser.add_argument("--dry_run", action="store_true", help="Dry run: only show what would be generated, don't execute")
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    gen_dir = base_dir / "2_Data" / "metadata" / "generated" / args.run_tag
    
    if not gen_dir.exists():
        print(f"ERROR: Generated directory not found: {gen_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Determine S1 arm (same as S2 arm for now)
    s1_arm = args.arm.upper()
    s1_path = gen_dir / f"stage1_struct__arm{s1_arm}.jsonl"
    
    # Determine S2 path (try common patterns)
    # Pattern 1: s2_results__s1arm{arm}__s2arm{arm}.jsonl
    s2_path = gen_dir / f"s2_results__s1arm{s1_arm}__s2arm{args.arm.upper()}.jsonl"
    if not s2_path.exists():
        # Pattern 2: s2_results__arm{arm}.jsonl (legacy)
        s2_path_alt = gen_dir / f"s2_results__arm{args.arm.upper()}.jsonl"
        if s2_path_alt.exists():
            s2_path = s2_path_alt
        else:
            # Try to find any s2_results file
            s2_files = list(gen_dir.glob("s2_results*.jsonl"))
            if s2_files:
                s2_path = s2_files[0]
                print(f"  Using found S2 file: {s2_path.name}")
    
    print(f"[1/4] Loading S1 entities from: {s1_path}")
    s1_entities = load_s1_entities(s1_path)
    if not s1_entities:
        print(f"ERROR: No S1 entities found in {s1_path}", file=sys.stderr)
        sys.exit(1)
    print(f"  Found {len(s1_entities)} groups in S1")
    
    print(f"\n[2/4] Loading existing S2 entities from: {s2_path}")
    s2_entities = load_s2_entities(s2_path)
    if not s2_entities:
        print("  No existing S2 results found (will generate all entities)")
    else:
        print(f"  Found S2 results for {len(s2_entities)} groups")
    
    print(f"\n[3/4] Finding missing entities...")
    missing_by_group = find_missing_entities(s1_entities, s2_entities)
    
    if not missing_by_group:
        print("  ✓ All entities already have S2 cards. Nothing to generate.")
        sys.exit(0)
    
    total_missing = sum(len(missing) for missing in missing_by_group.values())
    print(f"  Found {total_missing} missing entities across {len(missing_by_group)} groups:")
    for gid, missing in missing_by_group.items():
        print(f"    Group {gid}: {len(missing)} missing entities")
        for ent in missing:
            print(f"      - {ent}")
    
    if args.dry_run:
        print("\n[DRY RUN] Would generate S2 cards for the above entities.")
        sys.exit(0)
    
    print(f"\n[4/6] Preparing to generate S2 cards for missing entities...")
    print(f"  Groups to process: {len(missing_by_group)}")
    print(f"  Note: Current code processes entire groups. Missing entities will be added to existing S2 results.")
    
    group_ids = list(missing_by_group.keys())
    
    # Run S2 generation for groups with missing entities
    # Note: The current implementation will regenerate all entities in the group,
    # but since S2 results are appended, this will create duplicates for existing entities.
    # We'll need to deduplicate after generation.
    cmd_parts = [
        "python3",
        str(base_dir / "3_Code" / "src" / "01_generate_json.py"),
        "--base_dir", str(base_dir),
        "--run_tag", args.run_tag,
        "--arm", args.arm.upper(),
        "--mode", args.mode,
        "--stage", args.stage,
        "--workers", str(args.workers),
        "--resume",  # Append mode to preserve existing results
    ]
    
    # Add --only_group_id for each group with missing entities
    for gid in group_ids:
        cmd_parts.extend(["--only_group_id", gid])
    
    print(f"\n[5/6] Executing S2 generation...")
    print(f"Command: {' '.join(cmd_parts)}")
    print()
    
    try:
        result = subprocess.run(cmd_parts, check=True, cwd=str(base_dir))
    except subprocess.CalledProcessError as e:
        print(f"ERROR: S2 generation failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)
    
    # Deduplicate S2 results (keep only latest entry per (group_id, entity_name))
    print(f"\n[6/6] Deduplicating S2 results (keep latest per entity)...")
    dedup_s2_results(s2_path)
    
    if not args.skip_s5:
        # Run S5 validation
        # Note: S5 validator supports --group_id for single group, or None for all groups
        # We can run once without --group_id to validate all groups (more efficient)
        print(f"\n[7/8] Running S5 validation for all groups...")
        s5_cmd = [
            "python3",
            str(base_dir / "3_Code" / "src" / "05_s5_validator.py"),
            "--base_dir", str(base_dir),
            "--run_tag", args.run_tag,
            "--arm", args.arm.upper(),
            "--workers_s5", str(args.workers_s5),
            # No --group_id: process all groups (including newly generated ones)
        ]
        
        print(f"Executing: {' '.join(s5_cmd)}")
        print()
        
        try:
            result = subprocess.run(s5_cmd, check=True, cwd=str(base_dir))
        except subprocess.CalledProcessError as e:
            print(f"ERROR: S5 validation failed with exit code {e.returncode}", file=sys.stderr)
            sys.exit(e.returncode)
        
        # Generate S5 report
        print(f"\n[8/8] Generating S5 report...")
        report_cmd = [
            "python3",
            str(base_dir / "3_Code" / "src" / "tools" / "s5" / "s5_report.py"),
            "--base_dir", str(base_dir),
            "--run_tag", args.run_tag,
            "--arm", args.arm.upper(),
        ]
        
        print(f"Executing: {' '.join(report_cmd)}")
        print()
        
        try:
            result = subprocess.run(report_cmd, check=True, cwd=str(base_dir))
        except subprocess.CalledProcessError as e:
            print(f"ERROR: S5 report generation failed with exit code {e.returncode}", file=sys.stderr)
            sys.exit(e.returncode)
        
        print("\n✓ Completed: S2 generation and S5 validation for missing entities")
    else:
        print("\n✓ Completed: S2 generation for missing entities (S5 skipped)")


if __name__ == "__main__":
    main()

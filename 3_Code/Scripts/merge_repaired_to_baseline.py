#!/usr/bin/env python3
"""
Merge repaired results into baseline files.

This script:
1. Backs up baseline files
2. Merges s2_results__repaired.jsonl into s2_results.jsonl (by entity_id)
3. Merges s5_validation__postrepair.jsonl into s5_validation.jsonl (by group_id)
4. Copies repaired images to baseline images folder
"""

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path


def backup_file(filepath: Path) -> Path:
    """Create timestamped backup of a file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = filepath.parent / "archive" / "backups" / f"{filepath.name}.backup_merge_{timestamp}"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(filepath, backup_path)
    print(f"  Backed up: {filepath.name} -> {backup_path.name}")
    return backup_path


def merge_jsonl_by_key(
    baseline_path: Path,
    repaired_path: Path,
    key_field: str,
    dry_run: bool = False
) -> dict:
    """
    Merge repaired JSONL into baseline by replacing entries with matching keys.
    
    Returns stats dict with counts.
    """
    stats = {
        "baseline_count": 0,
        "repaired_count": 0,
        "replaced_count": 0,
        "final_count": 0
    }
    
    # Load repaired entries into a dict by key
    repaired_entries = {}
    with open(repaired_path, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            key = obj.get(key_field)
            if key:
                repaired_entries[key] = obj
                stats["repaired_count"] += 1
    
    print(f"  Loaded {stats['repaired_count']} repaired entries (key: {key_field})")
    
    # Read baseline and merge
    merged_entries = []
    replaced_keys = set()
    
    with open(baseline_path, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            key = obj.get(key_field)
            stats["baseline_count"] += 1
            
            if key and key in repaired_entries:
                # Replace with repaired version
                merged_entries.append(repaired_entries[key])
                replaced_keys.add(key)
                stats["replaced_count"] += 1
            else:
                # Keep original
                merged_entries.append(obj)
    
    stats["final_count"] = len(merged_entries)
    
    # Check for any repaired entries that weren't in baseline (shouldn't happen, but log if so)
    missing_in_baseline = set(repaired_entries.keys()) - replaced_keys
    if missing_in_baseline:
        print(f"  WARNING: {len(missing_in_baseline)} repaired entries not found in baseline")
    
    if not dry_run:
        # Write merged result
        with open(baseline_path, 'w') as f:
            for entry in merged_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        print(f"  Wrote {stats['final_count']} entries to {baseline_path.name}")
    else:
        print(f"  [DRY-RUN] Would write {stats['final_count']} entries to {baseline_path.name}")
    
    return stats


def copy_repaired_images(
    baseline_images_dir: Path,
    repaired_images_dir: Path,
    dry_run: bool = False
) -> dict:
    """Copy repaired images to baseline images folder."""
    stats = {
        "copied": 0,
        "skipped": 0,
        "total_repaired": 0
    }
    
    if not repaired_images_dir.exists():
        print(f"  Repaired images directory not found: {repaired_images_dir}")
        return stats
    
    repaired_images = list(repaired_images_dir.glob("*.jpg")) + list(repaired_images_dir.glob("*.png"))
    stats["total_repaired"] = len(repaired_images)
    
    for img_path in repaired_images:
        target_path = baseline_images_dir / img_path.name
        
        if not dry_run:
            shutil.copy2(img_path, target_path)
            stats["copied"] += 1
        else:
            stats["copied"] += 1
    
    if dry_run:
        print(f"  [DRY-RUN] Would copy {stats['copied']} images")
    else:
        print(f"  Copied {stats['copied']} images to {baseline_images_dir.name}")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="Merge repaired results into baseline")
    parser.add_argument("--base_dir", type=str, default=".", help="Base directory")
    parser.add_argument("--run_tag", type=str, default="FINAL_DISTRIBUTION", help="Run tag")
    parser.add_argument("--arm", type=str, default="G", help="Arm identifier")
    parser.add_argument("--dry_run", action="store_true", help="Dry run mode")
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir)
    metadata_dir = base_dir / "2_Data" / "metadata" / "generated" / args.run_tag
    
    print("=" * 60)
    print("MERGE REPAIRED RESULTS TO BASELINE")
    print("=" * 60)
    print(f"Run tag: {args.run_tag}")
    print(f"Arm: {args.arm}")
    print(f"Dry run: {args.dry_run}")
    print()
    
    # Define file paths
    s2_baseline = metadata_dir / f"s2_results__s1arm{args.arm}__s2arm{args.arm}.jsonl"
    s2_repaired = metadata_dir / f"s2_results__s1arm{args.arm}__s2arm{args.arm}__repaired.jsonl"
    
    s5_baseline = metadata_dir / f"s5_validation__arm{args.arm}.jsonl"
    s5_postrepair = metadata_dir / f"s5_validation__arm{args.arm}__postrepair.jsonl"
    
    images_baseline = metadata_dir / "images"
    images_repaired = metadata_dir / "images__repaired"
    
    # Merge S2 results
    print("Step 1: Merge S2 results (entity-level)")
    print("-" * 40)
    if s2_repaired.exists():
        if not args.dry_run:
            backup_file(s2_baseline)
        s2_stats = merge_jsonl_by_key(s2_baseline, s2_repaired, "entity_id", args.dry_run)
        print(f"  Stats: baseline={s2_stats['baseline_count']}, replaced={s2_stats['replaced_count']}")
    else:
        print(f"  Repaired file not found: {s2_repaired}")
    print()
    
    # Merge S5 validation
    print("Step 2: Merge S5 validation (group-level)")
    print("-" * 40)
    if s5_postrepair.exists():
        if not args.dry_run:
            backup_file(s5_baseline)
        s5_stats = merge_jsonl_by_key(s5_baseline, s5_postrepair, "group_id", args.dry_run)
        print(f"  Stats: baseline={s5_stats['baseline_count']}, replaced={s5_stats['replaced_count']}")
    else:
        print(f"  Postrepair file not found: {s5_postrepair}")
    print()
    
    # Copy repaired images
    print("Step 3: Copy repaired images")
    print("-" * 40)
    if images_repaired.exists():
        img_stats = copy_repaired_images(images_baseline, images_repaired, args.dry_run)
        print(f"  Stats: copied={img_stats['copied']}")
    else:
        print(f"  Repaired images directory not found: {images_repaired}")
    print()
    
    print("=" * 60)
    print("MERGE COMPLETE" if not args.dry_run else "[DRY-RUN] MERGE PREVIEW COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()


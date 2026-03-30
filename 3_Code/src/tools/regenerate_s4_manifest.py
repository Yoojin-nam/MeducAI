#!/usr/bin/env python3
"""
Regenerate S4 image manifest from existing image files.

This script scans the images directory and creates/updates the S4 manifest
based on existing image files. Useful when images were generated previously
but the manifest is missing or incomplete.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def parse_image_filename(filename: str) -> Optional[Dict[str, str]]:
    """
    Parse image filename to extract metadata.
    
    Formats:
    - IMG__{run_tag}__{group_id}__{entity_id}__{card_role}.jpg (card image)
    - IMG__{run_tag}__{group_id}__TABLE.jpg (table visual)
    
    Returns:
        Dict with run_tag, group_id, entity_id, card_role, spec_kind, or None if invalid
    """
    # Remove extension (support both .jpg and .png for backward compatibility)
    base = filename.replace(".jpg", "").replace(".JPG", "").replace(".jpeg", "").replace(".JPEG", "")
    base = base.replace(".png", "").replace(".PNG", "")
    
    # Pattern: IMG__{run_tag}__{group_id}__{entity_id}__{card_role}
    card_pattern = r"IMG__(.+?)__(.+?)__(.+?)__(Q[123])"
    card_match = re.match(card_pattern, base)
    
    if card_match:
        run_tag, group_id, entity_id, card_role = card_match.groups()
        return {
            "run_tag": run_tag,
            "group_id": group_id,
            "entity_id": entity_id,
            "card_role": card_role.upper(),
            "spec_kind": "S2_CARD_IMAGE",
        }
    
    # Pattern: IMG__{run_tag}__{group_id}__TABLE
    table_pattern = r"IMG__(.+?)__(.+?)__TABLE"
    table_match = re.match(table_pattern, base)
    
    if table_match:
        run_tag, group_id = table_match.groups()
        return {
            "run_tag": run_tag,
            "group_id": group_id,
            "entity_id": None,
            "card_role": None,
            "spec_kind": "S1_TABLE_VISUAL",
        }
    
    return None


def load_s3_specs(s3_spec_path: Path) -> Dict[Tuple[str, str, Optional[str], Optional[str]], Dict]:
    """
    Load S3 image specs to get entity_name and other metadata.
    
    Returns:
        Dict mapping (run_tag, group_id, entity_id, card_role) -> spec dict
    """
    specs = {}
    if not s3_spec_path.exists():
        return specs
    
    with open(s3_spec_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                spec = json.loads(line)
                run_tag = str(spec.get("run_tag", "")).strip()
                group_id = str(spec.get("group_id", "")).strip()
                entity_id = spec.get("entity_id")
                card_role = spec.get("card_role")
                spec_kind = str(spec.get("spec_kind", "")).strip()
                
                key = (run_tag, group_id, entity_id, card_role)
                specs[key] = spec
            except json.JSONDecodeError:
                continue
    
    return specs


def regenerate_manifest(
    images_dir: Path,
    s3_spec_path: Path,
    manifest_path: Path,
    run_tag: str,
) -> None:
    """Regenerate S4 manifest from existing image files."""
    
    if not images_dir.exists():
        print(f"❌ Images directory not found: {images_dir}")
        sys.exit(1)
    
    # Load S3 specs for metadata
    s3_specs = load_s3_specs(s3_spec_path)
    print(f"Loaded {len(s3_specs)} S3 specs")
    
    # Scan image files (support both .jpg and .png for backward compatibility)
    image_files = list(images_dir.glob("IMG__*.jpg")) + list(images_dir.glob("IMG__*.png"))
    print(f"Found {len(image_files)} image files")
    
    manifest_entries = []
    matched_count = 0
    
    for image_file in image_files:
        filename = image_file.name
        parsed = parse_image_filename(filename)
        
        if not parsed:
            print(f"⚠️  Skipping unparseable filename: {filename}")
            continue
        
        # Try to find matching S3 spec to get original entity_id format
        # Note: parsed entity_id is from filename (DERIVED_xxx), but we need original (DERIVED:xxx)
        # Try both formats to find the spec
        parsed_entity_id = parsed["entity_id"]
        spec_key_underscore = (parsed["run_tag"], parsed["group_id"], parsed_entity_id, parsed["card_role"])
        spec_key_colon = (parsed["run_tag"], parsed["group_id"], parsed_entity_id.replace("_", ":"), parsed["card_role"])
        
        s3_spec = s3_specs.get(spec_key_colon) or s3_specs.get(spec_key_underscore, {})
        
        # Use original entity_id from S3 spec if available, otherwise use parsed one
        original_entity_id = s3_spec.get("entity_id", parsed_entity_id)
        entity_name = s3_spec.get("entity_name", "")
        image_required = bool(s3_spec.get("image_asset_required", True))
        
        # Create manifest entry with original entity_id format (DERIVED:xxx)
        manifest_entry = {
            "schema_version": "S4_IMAGE_MANIFEST_v1.0",
            "run_tag": parsed["run_tag"],
            "group_id": parsed["group_id"],
            "entity_id": original_entity_id,  # Use original format from S3 spec
            "entity_name": entity_name,
            "card_role": parsed["card_role"],
            "spec_kind": parsed["spec_kind"],
            "media_filename": filename,
            "image_path": str(image_file.resolve()),
            "generation_success": True,  # Assume success if file exists
            "image_required": image_required,
            "rag_enabled": False,
            "rag_queries_count": 0,
            "rag_sources_count": 0,
        }
        
        manifest_entries.append(manifest_entry)
        matched_count += 1
    
    # Write manifest
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        for entry in manifest_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    print(f"\n✅ Regenerated manifest: {manifest_path}")
    print(f"   Created {matched_count} manifest entries")
    
    # Count by spec_kind
    card_images = sum(1 for e in manifest_entries if e["spec_kind"] == "S2_CARD_IMAGE")
    table_visuals = sum(1 for e in manifest_entries if e["spec_kind"] == "S1_TABLE_VISUAL")
    print(f"   - S2_CARD_IMAGE: {card_images}")
    print(f"   - S1_TABLE_VISUAL: {table_visuals}")


def main():
    parser = argparse.ArgumentParser(
        description="Regenerate S4 image manifest from existing image files",
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument("--run_tag", required=True, help="Run tag")
    parser.add_argument("--arm", type=str, default="A", help="Arm identifier")
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    run_tag = args.run_tag
    arm = args.arm.upper()
    
    # Paths
    out_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    images_dir = out_dir / "images"
    s3_spec_path = out_dir / f"s3_image_spec__arm{arm}.jsonl"
    manifest_path = out_dir / f"s4_image_manifest__arm{arm}.jsonl"
    
    print("="*70)
    print("S4 Manifest Regenerator")
    print("="*70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Arm: {arm}")
    print(f"Images directory: {images_dir}")
    print(f"S3 spec path: {s3_spec_path}")
    print(f"Output manifest: {manifest_path}")
    print("="*70)
    
    regenerate_manifest(images_dir, s3_spec_path, manifest_path, run_tag)


if __name__ == "__main__":
    main()


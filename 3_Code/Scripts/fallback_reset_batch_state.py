#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fallback reset script for MeducAI batch image generation.

What it does:
- Backs up and re-initializes:
  - 2_Data/metadata/.batch_tracking.json
  - 2_Data/metadata/.batch_failed.json
- Does NOT touch any images on disk.

Why:
- When a repair attempt fails and you want to restart cleanly while still
  skipping anything that already exists locally in:
  2_Data/metadata/generated/<run_tag>/images/

Usage:
  python 3_Code/Scripts/fallback_reset_batch_state.py --base_dir . --yes

Optional convenience (prints a restart command):
  python 3_Code/Scripts/fallback_reset_batch_state.py --base_dir . --yes \
    --spec 2_Data/metadata/generated/FINAL_DISTRIBUTION/s3_image_spec__armG.jsonl \
    --run_tag FINAL_DISTRIBUTION
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def _backup_file(path: Path, timestamp: str) -> Optional[Path]:
    if not path.exists():
        return None
    backup_path = path.parent / f"{path.name}.backup_{timestamp}"
    shutil.copy2(path, backup_path)
    return backup_path


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup+reset batch tracking/failed state files (fallback).")
    parser.add_argument("--base_dir", type=str, default=".", help="Project root (default: .)")
    parser.add_argument("--yes", action="store_true", help="Confirm you want to reset state files.")
    parser.add_argument("--no_backup", action="store_true", help="Skip backups (NOT recommended).")
    parser.add_argument("--spec", type=str, default="", help="Optional spec path; used only to print restart command.")
    parser.add_argument("--run_tag", type=str, default="", help="Optional run_tag; used only to print restart command.")
    args = parser.parse_args()

    if not args.yes:
        print("❌ Refusing to reset without confirmation.")
        print("   Re-run with: --yes")
        return 2

    base_dir = Path(args.base_dir).resolve()
    tracking_path = base_dir / "2_Data" / "metadata" / ".batch_tracking.json"
    failed_path = base_dir / "2_Data" / "metadata" / ".batch_failed.json"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        if not args.no_backup:
            bt = _backup_file(tracking_path, timestamp)
            bf = _backup_file(failed_path, timestamp)
            if bt:
                print(f"📦 Tracking backup: {bt}")
            if bf:
                print(f"📦 Failed backup:   {bf}")

        _write_json(
            tracking_path,
            {
                "schema_version": "BATCH_TRACKING_v1.0",
                "batches": {},
                "last_updated": datetime.now().isoformat(),
            },
        )
        _write_json(
            failed_path,
            {
                "schema_version": "BATCH_FAILED_v1.0",
                "failed_batches": [],
                "last_updated": datetime.now().isoformat(),
            },
        )

        print(f"🧾 Tracking reset: {tracking_path}")
        print(f"🧾 Failed reset:   {failed_path}")
        print("✅ Done. Images were NOT modified; reruns should still skip locally existing images.")

        if args.spec:
            spec_path = Path(args.spec)
            run_tag_part = f" --run_tag {args.run_tag}" if args.run_tag else ""
            print("\nNext (restart example):")
            print(
                "  "
                + " ".join(
                    [
                        sys.executable,
                        str(base_dir / "3_Code" / "src" / "batch_image_generator.py"),
                        "--input",
                        str(spec_path),
                        "--base_dir",
                        str(base_dir),
                        "--resume",
                    ]
                )
                + run_tag_part
            )

        return 0
    except Exception as e:
        print(f"❌ Reset failed: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())



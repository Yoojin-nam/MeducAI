#!/usr/bin/env python3
"""
Move existing temp_*.txt files from 2_Data/metadata/ to 2_Data/metadata/temp/

This is a one-time cleanup script to organize temporary files.
After running this, all new temp files will be created in the temp/ folder
by the updated scripts.
"""

import shutil
from pathlib import Path


def main():
    base_dir = Path(__file__).parent.parent.parent
    metadata_dir = base_dir / "2_Data" / "metadata"
    temp_dir = metadata_dir / "temp"
    
    # Create temp directory if it doesn't exist
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all temp_*.txt files in metadata directory (not in subdirectories)
    temp_files = list(metadata_dir.glob("temp_*.txt"))
    
    if not temp_files:
        print("No temp_*.txt files found in 2_Data/metadata/")
        return
    
    print(f"Found {len(temp_files)} temp files to move:")
    for f in temp_files:
        print(f"  - {f.name}")
    
    # Move files
    moved_count = 0
    for src_file in temp_files:
        dst_file = temp_dir / src_file.name
        try:
            # If destination exists, skip (user can manually handle conflicts)
            if dst_file.exists():
                print(f"  ⚠️  Skipping {src_file.name} (already exists in temp/)")
                continue
            
            shutil.move(str(src_file), str(dst_file))
            moved_count += 1
            print(f"  ✅ Moved {src_file.name}")
        except Exception as e:
            print(f"  ❌ Error moving {src_file.name}: {e}")
    
    print(f"\n✅ Moved {moved_count}/{len(temp_files)} files to {temp_dir}")
    print(f"📁 New temp files will be created in: {temp_dir}")


if __name__ == "__main__":
    main()


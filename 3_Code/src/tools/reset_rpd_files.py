#!/usr/bin/env python3
"""
Reset RPD files to allow fresh quota tracking
"""
import json
from pathlib import Path
from datetime import datetime

def reset_rpd_files(base_dir=".", run_tag=None):
    """Find and reset RPD files."""
    base_path = Path(base_dir)
    
    # Search in generated directories
    generated_dir = base_path / "2_Data" / "metadata" / "generated"
    
    if not generated_dir.exists():
        print(f"❌ Generated directory not found: {generated_dir}")
        return
    
    rpd_files = []
    
    # If run_tag is specified, only check that directory
    if run_tag:
        run_dir = generated_dir / run_tag
        if run_dir.exists():
            logs_dir = run_dir / "logs"
            if logs_dir.exists():
                rpd_files.extend(logs_dir.glob("rpd_*.json"))
    else:
        # Search all run_tag directories
        for run_dir in generated_dir.iterdir():
            if run_dir.is_dir():
                logs_dir = run_dir / "logs"
                if logs_dir.exists():
                    rpd_files.extend(logs_dir.glob("rpd_*.json"))
    
    if not rpd_files:
        print("ℹ️  No RPD files found")
        return
    
    print("=" * 80)
    print("RPD Files Found")
    print("=" * 80)
    print()
    
    for rpd_file in rpd_files:
        try:
            with open(rpd_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            used = data.get("used", 0)
            updated_at = data.get("updated_at", 0)
            
            print(f"📄 {rpd_file.relative_to(base_path)}")
            print(f"   Used: {used}/250")
            print(f"   Updated: {datetime.fromtimestamp(updated_at) if updated_at else 'N/A'}")
            print()
            
            # Reset to 0
            data["used"] = 0
            data["updated_at"] = int(datetime.now().timestamp())
            
            with open(rpd_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            
            print(f"   ✅ Reset to 0/250")
            print()
            
        except Exception as e:
            print(f"   ❌ Error processing {rpd_file}: {e}")
            print()
    
    print("=" * 80)
    print("✅ RPD files reset complete")
    print("=" * 80)

if __name__ == "__main__":
    import sys
    run_tag = sys.argv[1] if len(sys.argv) > 1 else None
    reset_rpd_files(run_tag=run_tag)


#!/usr/bin/env python3
"""Export all 11 specialty-specific Anki decks with REGEN integration."""

import subprocess
import sys
from pathlib import Path

BASE_DIR = Path("/path/to/workspace/workspace/MeducAI")
OUT_DIR = BASE_DIR / "6_Distributions" / "MeducAI_Final_Share" / "anki" / "Specialty_Decks"

SPECIALTIES = {
    "abdominal_radiology": "Abdominal",
    "breast_rad": "Breast",
    "cardiovascular_rad": "Cardiovascular",
    "gu_radiology": "GU",
    "interventional_radiology": "IR",
    "musculoskeletal_radiology": "MSK",
    "neuro_hn_imaging": "NeuroHN",
    "nuclear_med": "NuclearMed",
    "pediatric_radiology": "Pediatric",
    "physics_qc_informatics": "PhysicsQC",
    "thoracic_radiology": "Thoracic",
}

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("="*60)
    print("Exporting 11 Specialty Decks with REGEN")
    print("="*60)
    
    results = []
    
    for i, (specialty_code, display_name) in enumerate(SPECIALTIES.items(), 1):
        print(f"\n[{i}/11] {display_name} ({specialty_code})...", flush=True)
        
        output_file = OUT_DIR / f"MeducAI_FINAL_{display_name}.apkg"
        
        cmd = [
            sys.executable,
            str(BASE_DIR / "3_Code/src/tools/anki/export_final_anki_integrated.py"),
            "--allocation", str(BASE_DIR / "2_Data/metadata/generated/FINAL_DISTRIBUTION/allocation/final_distribution_allocation__6000cards.json"),
            "--s5", str(BASE_DIR / "2_Data/metadata/generated/FINAL_DISTRIBUTION/s5_validation__armG.jsonl"),
            "--s2_baseline", str(BASE_DIR / "2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__medterm_en.jsonl"),
            "--s2_regen", str(BASE_DIR / "2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__regen__medterm_en.jsonl"),
            "--images_anki", str(BASE_DIR / "2_Data/metadata/generated/FINAL_DISTRIBUTION/images_anki"),
            "--images_regen", str(BASE_DIR / "2_Data/metadata/generated/FINAL_DISTRIBUTION/images_regen"),
            "--output", str(output_file),
            "--threshold", "80.0",
            "--specialty", specialty_code,
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Parse output for card count
            for line in result.stdout.splitlines():
                if "Total notes:" in line:
                    print(f"  {line.strip()}")
                    break
            
            # Check file size
            if output_file.exists():
                size_mb = output_file.stat().st_size / (1024**2)
                print(f"  ✅ Created: {size_mb:.1f} MB")
                results.append((display_name, "Success", size_mb))
            else:
                print(f"  ❌ File not created")
                results.append((display_name, "Failed - no file", 0))
                
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Export failed")
            print(f"     Error: {e.stderr[:200]}")
            results.append((display_name, "Failed", 0))
    
    # Summary
    print(f"\n{'='*60}")
    print("✅ Specialty Deck Export Complete")
    print("="*60)
    
    print(f"\nSummary:")
    success_count = sum(1 for _, status, _ in results if status == "Success")
    print(f"  Success: {success_count}/11")
    
    print(f"\nFiles:")
    for name, status, size in results:
        if status == "Success":
            print(f"  ✅ {name:20s}: {size:6.1f} MB")
        else:
            print(f"  ❌ {name:20s}: {status}")
    
    print(f"\nOutput directory: {OUT_DIR}")


if __name__ == '__main__':
    main()


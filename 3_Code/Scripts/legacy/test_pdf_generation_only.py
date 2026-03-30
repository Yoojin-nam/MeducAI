#!/usr/bin/env python3
"""
Test PDF generation only (using existing S1/S2 data)
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from Scripts.test_6arm_different_specialties import (
    load_groups_canonical,
    select_groups_by_specialty,
    generate_combined_pdf,
    ARMS,
    ARM_LABELS,
)

def main():
    base_dir = Path("/path/to/workspace/workspace/MeducAI").resolve()
    run_tag = "TEST_6ARM_SPEC_20251221_140719"
    seed = 42
    
    print("=" * 70)
    print("Testing PDF Generation (Using Existing Data)")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print("=" * 70)
    
    # Load groups
    groups_csv_path = base_dir / "2_Data" / "metadata" / "groups_canonical.csv"
    print(f"\n>>> Loading groups from: {groups_csv_path}")
    groups = load_groups_canonical(groups_csv_path)
    print(f"   Loaded {len(groups)} groups")
    
    # Select groups (same as original test)
    print(f"\n>>> Selecting groups (one per specialty, one per arm)...")
    arm_to_group = select_groups_by_specialty(groups, ARMS, seed=seed)
    print(f"\n✅ Selected {len(arm_to_group)} groups:")
    for arm in ARMS:
        if arm in arm_to_group:
            group = arm_to_group[arm]
            print(f"   Arm {arm} ({ARM_LABELS.get(arm, arm)}): {group['group_id']} - {group['specialty']}")
    
    # Generate PDF
    pdf_success = generate_combined_pdf(
        base_dir=base_dir,
        run_tag=run_tag,
        arms=ARMS,
        arm_to_group=arm_to_group,
    )
    
    if pdf_success:
        print("\n✅ PDF generation completed successfully!")
        return 0
    else:
        print("\n❌ PDF generation failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())


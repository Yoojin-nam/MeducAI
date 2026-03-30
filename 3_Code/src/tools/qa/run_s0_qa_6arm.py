#!/usr/bin/env python3
"""
S0 QA Execution Script: 6 Arms with 18 Groups (S0 Canonical Rule)

This script:
1. Selects 18 groups according to S0 canonical rule:
   - Stage 1: Each specialty minimum 1 group (highest weight)
   - Stage 2: Remaining 7 groups by weight (highest first)
2. Runs S1 for all 6 arms (A-F) with selected 18 groups
3. Runs S1 Gate validation
4. Runs S0 Allocation for all 6 arms
5. Runs S2 for all 6 arms with selected 18 groups

Reference:
- 0_Protocol/06_QA_and_Study/QA_Operations/S0_18Group_Selection_Rule_Canonical.md
- 0_Protocol/05_Pipeline_and_Execution/S0_Execution_Plan_Without_S4.md

Usage:
    python 3_Code/src/tools/qa/run_s0_qa_6arm.py [--base_dir .] [--run_tag S0_QA_YYYYMMDD] [--seed 42]
"""

import argparse
import csv
import json
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

ARM_LABELS = {
    "A": "Baseline",
    "B": "RAG Only",
    "C": "Thinking",
    "D": "Synergy",
    "E": "High-End",
    "F": "Benchmark"
}

ARMS = ["A", "B", "C", "D", "E", "F"]


def load_groups_canonical(csv_path: Path) -> List[Dict[str, str]]:
    """Load groups from groups_canonical.csv."""
    groups = []
    if not csv_path.exists():
        raise FileNotFoundError(f"groups_canonical.csv not found: {csv_path}")
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            groups.append({
                "group_id": row.get("group_id", "").strip(),
                "group_key": row.get("group_key", "").strip(),
                "specialty": row.get("specialty", "").strip(),
                "anatomy": row.get("anatomy", "").strip(),
                "modality_or_type": row.get("modality_or_type", "").strip(),
                "category": row.get("category", "").strip(),
            })
    
    return groups


def load_group_weights(base_dir: Path) -> Dict[str, float]:
    """Load group weights from EDA results."""
    weight_path = base_dir / "2_Data" / "eda" / "EDA_1780_Decision" / "tables" / "groups_weight_expected_cards.csv"
    
    if not weight_path.exists():
        print(f"⚠️  Weight file not found: {weight_path}")
        print("   Falling back to uniform selection (no weight data)")
        return {}
    
    weights = {}
    with open(weight_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            group_key = row.get("_group_key", "").strip()
            weight_sum = row.get("group_weight_sum", "0").strip()
            try:
                weights[group_key] = float(weight_sum)
            except (ValueError, TypeError):
                continue
    
    print(f"   Loaded weights for {len(weights)} groups")
    return weights


def select_18_groups_s0_rule(
    groups: List[Dict[str, str]], 
    base_dir: Path,
    seed: int = 42
) -> List[Dict[str, str]]:
    """
    Select 18 groups according to S0 canonical rule:
    
    Stage 1: Each specialty minimum 1 group (highest weight)
    Stage 2: Select 7 groups by specialty total weight (highest specialty first, one per specialty)
            - Calculate total weight for each specialty (sum of all groups)
            - Sort specialties by total weight (descending)
            - Select one group per specialty (highest weight group from remaining groups)
            - Continue until 7 groups are selected
    
    Reference: 0_Protocol/06_QA_and_Study/QA_Operations/S0_18Group_Selection_Rule_Canonical.md
    """
    random.seed(seed)
    
    # Load weights
    weights = load_group_weights(base_dir)
    has_weights = len(weights) > 0
    
    # Add weight to each group
    groups_with_weight = []
    for group in groups:
        group_key = group.get("group_key", "").strip()
        weight = weights.get(group_key, 0.0) if has_weights else 0.0
        groups_with_weight.append({
            **group,
            "weight": weight,
        })
    
    # Group by specialty
    specialty_groups: Dict[str, List[Dict[str, str]]] = {}
    for group in groups_with_weight:
        specialty = group.get("specialty", "").strip()
        if not specialty:
            continue
        if specialty not in specialty_groups:
            specialty_groups[specialty] = []
        specialty_groups[specialty].append(group)
    
    print(f"\n>>> Selecting 18 groups (S0 canonical rule)")
    print(f"   Found {len(specialty_groups)} specialties")
    
    # Stage 1: Each specialty minimum 1 group (highest weight)
    selected_stage1 = []
    selected_keys_stage1 = set()
    
    for specialty in sorted(specialty_groups.keys()):
        specialty_list = specialty_groups[specialty]
        # Sort by weight (descending), then by group_key for tie-breaking
        specialty_list.sort(key=lambda x: (x.get("weight", 0), x.get("group_key", "")), reverse=True)
        
        if specialty_list:
            best_group = specialty_list[0]
            selected_stage1.append(best_group)
            selected_keys_stage1.add(best_group["group_key"])
            print(f"  Stage 1 [{specialty:20s}]: {best_group['group_id']} - {best_group['group_key']} (weight: {best_group.get('weight', 0):.2f})")
    
    print(f"\n   Stage 1 complete: {len(selected_stage1)} groups selected")
    
    # Stage 2: Select 7 groups by specialty total weight (highest specialty first, one per specialty)
    # Calculate specialty total weights (sum of all groups in each specialty)
    specialty_total_weights = {}
    for specialty, specialty_list in specialty_groups.items():
        total_weight = sum(g.get("weight", 0) for g in specialty_list)
        specialty_total_weights[specialty] = total_weight
    
    # Sort specialties by total weight (descending)
    sorted_specialties = sorted(specialty_total_weights.items(), key=lambda x: (-x[1], x[0]))
    
    # Select one group per specialty (highest weight specialty first)
    # Skip already selected groups from Stage 1
    selected_stage2 = []
    for specialty, _ in sorted_specialties:
        specialty_list = specialty_groups[specialty]
        # Get remaining groups (not selected in Stage 1)
        remaining_in_specialty = [g for g in specialty_list if g["group_key"] not in selected_keys_stage1]
        if remaining_in_specialty:
            # Sort by weight (descending), then by group_key for tie-breaking
            remaining_in_specialty.sort(key=lambda x: (x.get("weight", 0), x.get("group_key", "")), reverse=True)
            best_remaining = remaining_in_specialty[0]
            selected_stage2.append(best_remaining)
            selected_keys_stage1.add(best_remaining["group_key"])
            print(f"  Stage 2 [{specialty:20s}]: {best_remaining['group_id']} - {best_remaining['group_key']} (weight: {best_remaining.get('weight', 0):.2f}, specialty_total: {specialty_total_weights[specialty]:.2f})")
        
        # Stop when we have 7 groups
        if len(selected_stage2) >= 7:
            break
    
    print(f"\n   Stage 2 complete: {len(selected_stage2)} groups selected")
    
    # Combine results
    all_selected = selected_stage1 + selected_stage2
    
    # Remove weight from output (not needed in return)
    for group in all_selected:
        if "weight" in group:
            del group["weight"]
    
    print(f"   Total: {len(all_selected)} groups selected")
    
    return all_selected


def run_command(cmd: List[str], cwd: Optional[Path] = None, stream_output: bool = True) -> tuple[bool, str]:
    """
    Run a command and return (success, output).
    
    Args:
        cmd: Command to run
        cwd: Working directory
        stream_output: If True, stream output in real-time. If False, capture all output.
    """
    import sys as _sys
    
    if stream_output:
        # Real-time streaming mode: show output as it happens, but also capture it
        output_lines = []
        error_lines = []
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
            )
            
            # Stream stdout and stderr in real-time
            def stream_stdout():
                for line in iter(process.stdout.readline, ''):
                    if line:
                        output_lines.append(line)
                        _sys.stdout.write(line)
                        _sys.stdout.flush()
            
            def stream_stderr():
                for line in iter(process.stderr.readline, ''):
                    if line:
                        error_lines.append(line)
                        _sys.stderr.write(line)
                        _sys.stderr.flush()
            
            # Use threads to stream both stdout and stderr simultaneously
            import threading
            stdout_thread = threading.Thread(target=stream_stdout, daemon=True)
            stderr_thread = threading.Thread(target=stream_stderr, daemon=True)
            
            stdout_thread.start()
            stderr_thread.start()
            
            # Wait for process to complete
            return_code = process.wait()
            
            # Wait for threads to finish
            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)
            
            output = ''.join(output_lines)
            error_output = ''.join(error_lines)
            
            if return_code == 0:
                return True, output
            else:
                error_parts = []
                if error_output:
                    error_parts.append(f"STDERR:\n{error_output}")
                if output:
                    error_parts.append(f"STDOUT:\n{output}")
                if not error_parts:
                    error_parts.append(f"Command failed with return code {return_code}")
                error_parts.append(f"\nCommand: {' '.join(cmd)}")
                return False, "\n".join(error_parts)
                
        except Exception as e:
            error_msg = f"Error running command: {str(e)}\nCommand: {' '.join(cmd)}"
            return False, error_msg
    else:
        # Original capture mode (for backward compatibility)
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            # Combine stderr and stdout for better error visibility
            error_parts = []
            if e.stderr:
                error_parts.append(f"STDERR:\n{e.stderr}")
            if e.stdout:
                error_parts.append(f"STDOUT:\n{e.stdout}")
            if not error_parts:
                error_parts.append(f"Command failed with return code {e.returncode}")
            error_parts.append(f"\nCommand: {' '.join(cmd)}")
            return False, "\n".join(error_parts)


def run_s1(
    base_dir: Path,
    run_tag: str,
    arm: str,
    selected_groups: List[Dict[str, str]],
) -> tuple[bool, str]:
    """Run S1 for selected groups."""
    print(f"\n[Arm {arm}] Running S1...")
    
    # Create a temporary file with selected group_keys
    temp_dir = base_dir / "2_Data" / "metadata" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_group_keys_file = temp_dir / f"temp_selected_groups_{run_tag}_{arm}.txt"
    
    with open(temp_group_keys_file, "w", encoding="utf-8") as f:
        for group in selected_groups:
            f.write(f"{group['group_key']}\n")
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "01_generate_json.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
        "--mode", "S0",
        "--stage", "1",
        "--only_group_keys_file", str(temp_group_keys_file),
        "--sample", str(len(selected_groups)),
    ]
    
    success, output = run_command(cmd, cwd=base_dir)
    
    # Clean up temp file
    if temp_group_keys_file.exists():
        temp_group_keys_file.unlink()
    
    return success, output


def run_s1_gate(base_dir: Path, run_tag: str, arms: List[str]) -> tuple[bool, str]:
    """Run S1 Gate validation for all arms. Fails fast on first failure."""
    print("\n>>> Running S1 Gate validation...")
    print(f"   Total arms to validate: {len(arms)}")
    print("=" * 70)
    
    all_output = []
    passed_arms = []
    
    for idx, arm in enumerate(arms, 1):
        progress = f"[{idx}/{len(arms)}]"
        print(f"\n{progress} Validating Arm {arm}...", end=" ", flush=True)
        
        cmd = [
            sys.executable,
            str(base_dir / "3_Code" / "src" / "tools" / "qa" / "validate_stage1_struct.py"),
            "--base_dir", str(base_dir),
            "--run_tag", run_tag,
            "--arm", arm,
        ]
        
        success, output = run_command(cmd, cwd=base_dir)
        all_output.append(f"Arm {arm}: {'PASS' if success else 'FAIL'}\n{output}")
        
        if success:
            print("✅ PASS")
            passed_arms.append(arm)
        else:
            print("❌ FAIL")
            # Fail fast: stop immediately on first failure
            print("\n" + "=" * 70)
            print(f"❌ S1 Gate validation FAILED at Arm {arm}")
            print("=" * 70)
            print(f"Failed arm: {arm}")
            print(f"Passed arms so far: {len(passed_arms)}/{idx} ({', '.join(passed_arms) if passed_arms else 'None'})")
            print(f"\nError details:")
            print(output)
            print("=" * 70)
            combined_output = "\n".join(all_output)
            return False, combined_output
    
    # All arms passed
    print("\n" + "=" * 70)
    print("✅ S1 Gate Validation Summary: ALL ARMS PASSED")
    print("-" * 70)
    print(f"  Passed: {len(passed_arms)}/{len(arms)} ({', '.join(passed_arms)})")
    print("=" * 70)
    
    combined_output = "\n".join(all_output)
    return True, combined_output


def run_allocation(base_dir: Path, run_tag: str, arm: str) -> tuple[bool, str]:
    """Run S0 Allocation for an arm."""
    print(f"\n[Arm {arm}] Running S0 Allocation...")
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "tools" / "allocation" / "s0_allocation.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
    ]
    
    return run_command(cmd, cwd=base_dir)


def run_s2(
    base_dir: Path,
    run_tag: str,
    arm: str,
    selected_groups: List[Dict[str, str]],
) -> tuple[bool, str]:
    """Run S2 for selected groups."""
    print(f"\n[Arm {arm}] Running S2...")
    
    # Create a temporary file with selected group_keys
    temp_dir = base_dir / "2_Data" / "metadata" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_group_keys_file = temp_dir / f"temp_selected_groups_{run_tag}_{arm}.txt"
    
    with open(temp_group_keys_file, "w", encoding="utf-8") as f:
        for group in selected_groups:
            f.write(f"{group['group_key']}\n")
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "01_generate_json.py"),
        "--base_dir", str(base_dir),
        "--run_tag", run_tag,
        "--arm", arm,
        "--mode", "S0",
        "--stage", "2",
        "--only_group_keys_file", str(temp_group_keys_file),
        "--sample", str(len(selected_groups)),
    ]
    
    success, output = run_command(cmd, cwd=base_dir)
    
    # Clean up temp file
    if temp_group_keys_file.exists():
        temp_group_keys_file.unlink()
    
    return success, output


def main():
    parser = argparse.ArgumentParser(
        description="S0 QA Execution: 6 Arms with 18 Groups (S0 Canonical Rule)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument(
        "--run_tag",
        type=str,
        default=None,
        help="Run tag (default: S0_QA_YYYYMMDD_HHMMSS)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument(
        "--groups_csv",
        type=str,
        default="2_Data/metadata/groups_canonical.csv",
        help="Path to groups_canonical.csv",
    )
    parser.add_argument(
        "--skip_s1",
        action="store_true",
        help="Skip S1 (assume already run)",
    )
    parser.add_argument(
        "--skip_s1_gate",
        action="store_true",
        help="Skip S1 Gate validation",
    )
    parser.add_argument(
        "--skip_allocation",
        action="store_true",
        help="Skip Allocation (assume already run)",
    )
    parser.add_argument(
        "--skip_s2",
        action="store_true",
        help="Skip S2 (assume already run)",
    )
    parser.add_argument(
        "--arms",
        type=str,
        nargs="+",
        default=ARMS,
        help=f"Arms to execute (default: {ARMS})",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        print(f"❌ Base directory does not exist: {base_dir}")
        sys.exit(1)
    
    # Generate run_tag if not provided
    if args.run_tag:
        run_tag = args.run_tag
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_tag = f"S0_QA_{timestamp}"
    
    arms = [arm.upper() for arm in args.arms]
    
    print("=" * 70)
    print("S0 QA Execution: 6 Arms with 18 Groups")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {run_tag}")
    print(f"Arms: {', '.join(arms)}")
    print(f"Seed: {args.seed}")
    print("=" * 70)
    
    # Load groups
    groups_csv_path = base_dir / args.groups_csv
    print(f"\n>>> Loading groups from: {groups_csv_path}")
    groups = load_groups_canonical(groups_csv_path)
    print(f"   Loaded {len(groups)} groups")
    
    # Select 18 groups according to S0 canonical rule
    print(f"\n>>> Selecting 18 groups (S0 canonical rule, seed={args.seed})...")
    selected_groups = select_18_groups_s0_rule(groups, base_dir=base_dir, seed=args.seed)
    print(f"\n✅ Selected {len(selected_groups)} groups from {len(set(g['specialty'] for g in selected_groups))} specialties")
    
    # Save selected groups to a file for reference
    selected_groups_file = base_dir / "2_Data" / "metadata" / "generated" / run_tag / "selected_18_groups.json"
    selected_groups_file.parent.mkdir(parents=True, exist_ok=True)
    with open(selected_groups_file, "w", encoding="utf-8") as f:
        json.dump(selected_groups, f, indent=2, ensure_ascii=False)
    print(f"   Saved selected groups to: {selected_groups_file}")
    
    # Step 1: Run S1 for all arms
    if not args.skip_s1:
        print("\n" + "=" * 70)
        print("STEP 1: Running S1 for all arms")
        print("=" * 70)
        print(f"   Total arms: {len(arms)}")
        print("-" * 70)
        
        s1_results = {}
        for idx, arm in enumerate(arms, 1):
            progress = f"[{idx}/{len(arms)}]"
            print(f"\n{progress} Running S1 for Arm {arm}...", end=" ", flush=True)
            
            success, output = run_s1(base_dir, run_tag, arm, selected_groups)
            s1_results[arm] = {"success": success, "output": output}
            
            if success:
                print("✅ DONE")
            else:
                print("❌ FAILED")
                print(f"  Error: {output[:500]}")
        
        # Summary
        print("\n" + "-" * 70)
        passed = [arm for arm, r in s1_results.items() if r["success"]]
        failed = [arm for arm, r in s1_results.items() if not r["success"]]
        print(f"  Passed: {len(passed)}/{len(arms)} ({', '.join(passed) if passed else 'None'})")
        if failed:
            print(f"  Failed: {len(failed)}/{len(arms)} ({', '.join(failed)})")
        print("=" * 70)
        
        # Check if all S1 succeeded
        all_s1_success = all(r["success"] for r in s1_results.values())
        if not all_s1_success:
            print("\n❌ Some S1 executions failed. Cannot continue.")
            sys.exit(1)
    else:
        print("\n>>> Skipping S1 (--skip_s1)")
    
    # Step 2: S1 Gate validation
    if not args.skip_s1_gate:
        print("\n" + "=" * 70)
        print("STEP 2: S1 Gate Validation")
        print("=" * 70)
        
        success, output = run_s1_gate(base_dir, run_tag, arms)
        
        if not success:
            print("\n⚠️  S1 Gate validation failed. Please review the errors above.")
            print("\nDetailed output:")
            print(output)
            sys.exit(1)
    else:
        print("\n>>> Skipping S1 Gate validation (--skip_s1_gate)")
    
    # Step 3: Run Allocation for all arms
    if not args.skip_allocation:
        print("\n" + "=" * 70)
        print("STEP 3: Running S0 Allocation for all arms")
        print("=" * 70)
        print(f"   Total arms: {len(arms)}")
        print("-" * 70)
        
        allocation_results = {}
        for idx, arm in enumerate(arms, 1):
            progress = f"[{idx}/{len(arms)}]"
            print(f"\n{progress} Running Allocation for Arm {arm}...", end=" ", flush=True)
            
            success, output = run_allocation(base_dir, run_tag, arm)
            allocation_results[arm] = {"success": success, "output": output}
            
            if success:
                print("✅ DONE")
            else:
                print("❌ FAILED")
                print(f"  Error: {output[:500]}")
        
        # Summary
        print("\n" + "-" * 70)
        passed = [arm for arm, r in allocation_results.items() if r["success"]]
        failed = [arm for arm, r in allocation_results.items() if not r["success"]]
        print(f"  Passed: {len(passed)}/{len(arms)} ({', '.join(passed) if passed else 'None'})")
        if failed:
            print(f"  Failed: {len(failed)}/{len(arms)} ({', '.join(failed)})")
        print("=" * 70)
        
        # Check if all allocations succeeded
        all_allocation_success = all(r["success"] for r in allocation_results.values())
        if not all_allocation_success:
            print("\n❌ Some allocations failed. Cannot continue.")
            sys.exit(1)
    else:
        print("\n>>> Skipping Allocation (--skip_allocation)")
    
    # Step 4: Run S2 for all arms
    if not args.skip_s2:
        print("\n" + "=" * 70)
        print("STEP 4: Running S2 for all arms")
        print("=" * 70)
        print(f"   Total arms: {len(arms)}")
        print("-" * 70)
        
        s2_results = {}
        for idx, arm in enumerate(arms, 1):
            progress = f"[{idx}/{len(arms)}]"
            print(f"\n{progress} Running S2 for Arm {arm}...", end=" ", flush=True)
            
            success, output = run_s2(base_dir, run_tag, arm, selected_groups)
            s2_results[arm] = {"success": success, "output": output}
            
            if success:
                print("✅ DONE")
            else:
                print("❌ FAILED")
                # Show first 1000 chars of error, then indicate if more exists
                error_preview = output[:1000] if len(output) <= 1000 else output[:1000] + f"\n... (truncated, {len(output)} total chars)"
                print(f"  Error preview:\n{error_preview}")
                
                # Save full error to file for debugging
                error_log_file = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"s2_error_arm_{arm}.txt"
                error_log_file.parent.mkdir(parents=True, exist_ok=True)
                with open(error_log_file, "w", encoding="utf-8") as f:
                    f.write(f"S2 Error for Arm {arm}\n")
                    f.write("=" * 70 + "\n")
                    f.write(output)
                print(f"  Full error saved to: {error_log_file}")
        
        # Summary
        print("\n" + "-" * 70)
        passed = [arm for arm, r in s2_results.items() if r["success"]]
        failed = [arm for arm, r in s2_results.items() if not r["success"]]
        print(f"  Passed: {len(passed)}/{len(arms)} ({', '.join(passed) if passed else 'None'})")
        if failed:
            print(f"  Failed: {len(failed)}/{len(arms)} ({', '.join(failed)})")
        print("=" * 70)
        
        # Check if all S2 succeeded
        all_s2_success = all(r["success"] for r in s2_results.values())
        if not all_s2_success:
            print("\n❌ Some S2 executions failed.")
            sys.exit(1)
    else:
        print("\n>>> Skipping S2 (--skip_s2)")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ S0 QA Execution Complete")
    print("=" * 70)
    print(f"  Run tag: {run_tag}")
    print(f"  Selected groups: {len(selected_groups)}")
    print(f"  Arms executed: {len(arms)} ({', '.join(arms)})")
    print(f"\n  Output files:")
    generated_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    print(f"    - S1 outputs: {generated_dir / 'stage1_struct__arm*.jsonl'}")
    print(f"    - S2 outputs: {generated_dir / 's2_results__arm*.jsonl'} (legacy) or s2_results__s1arm*__s2arm*.jsonl (new format)")
    print(f"    - Allocation: {generated_dir / 'allocation/'}")
    print(f"    - Selected groups: {selected_groups_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()


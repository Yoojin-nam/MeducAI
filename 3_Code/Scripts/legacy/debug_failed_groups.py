#!/usr/bin/env python3
"""
Debug failed S1 groups - Run individual groups and capture detailed error information.

This script:
1. Identifies missing groups from S1 output
2. Runs each missing group individually with detailed logging
3. Captures and analyzes error messages
4. Saves debug information to files

Usage:
    python 3_Code/Scripts/debug_failed_groups.py \
        --base_dir . \
        --run_tag S0_QA_fixed_v3 \
        --arm B
"""

import argparse
import json
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def load_selected_groups(base_dir: Path, run_tag: str) -> List[Dict[str, str]]:
    """Load the selected 18 groups."""
    selected_file = base_dir / "2_Data" / "metadata" / "generated" / run_tag / "selected_18_groups.json"
    if not selected_file.exists():
        raise FileNotFoundError(f"Selected groups file not found: {selected_file}")
    
    with open(selected_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_s1_group_keys(base_dir: Path, run_tag: str, arm: str) -> set:
    """Get set of group_keys that exist in S1 output."""
    s1_file = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"stage1_struct__arm{arm}.jsonl"
    if not s1_file.exists():
        return set()
    
    found_keys = set()
    with open(s1_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                gkey = data.get("group_key")
                if gkey:
                    found_keys.add(gkey)
            except Exception:
                continue
    
    return found_keys


def find_missing_groups(base_dir: Path, run_tag: str, arm: str) -> List[Dict[str, str]]:
    """Find missing groups for an arm."""
    selected = load_selected_groups(base_dir, run_tag)
    selected_keys = {g["group_key"] for g in selected}
    
    found_keys = get_s1_group_keys(base_dir, run_tag, arm)
    missing_keys = selected_keys - found_keys
    missing_groups = [g for g in selected if g["group_key"] in missing_keys]
    
    return missing_groups


def run_single_group_debug(
    base_dir: Path,
    run_tag: str,
    arm: str,
    group: Dict[str, str],
    debug_output_dir: Path,
) -> Tuple[bool, Dict[str, any]]:
    """Run S1 for a single group with detailed debugging."""
    group_key = group["group_key"]
    group_id = group.get("group_id", "unknown")
    
    print(f"\n{'='*70}")
    print(f"Debugging group: {group_key}")
    print(f"  Group ID: {group_id}")
    print(f"  Specialty: {group.get('specialty', 'unknown')}")
    print(f"{'='*70}")
    
    # Create temp file with single group
    temp_group_keys_file = debug_output_dir / f"temp_group_{group_id}.txt"
    with open(temp_group_keys_file, "w", encoding="utf-8") as f:
        f.write(f"{group_key}\n")
    
    # Create debug run tag
    debug_run_tag = f"{run_tag}_debug_{group_id}"
    
    cmd = [
        sys.executable,
        str(base_dir / "3_Code" / "src" / "01_generate_json.py"),
        "--base_dir", str(base_dir),
        "--run_tag", debug_run_tag,
        "--arm", arm,
        "--mode", "S0",
        "--stage", "1",
        "--only_group_keys_file", str(temp_group_keys_file),
        "--sample", "1",
    ]
    
    debug_info = {
        "group_key": group_key,
        "group_id": group_id,
        "arm": arm,
        "run_tag": debug_run_tag,
        "command": " ".join(cmd),
        "start_time": datetime.now().isoformat(),
        "success": False,
        "error": None,
        "stdout": None,
        "stderr": None,
        "exit_code": None,
        "output_files": {},
    }
    
    try:
        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=base_dir,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )
        
        debug_info["exit_code"] = result.returncode
        debug_info["stdout"] = result.stdout
        debug_info["stderr"] = result.stderr
        
        # Check output files
        debug_out_dir = base_dir / "2_Data" / "metadata" / "generated" / debug_run_tag
        stage1_struct_path = debug_out_dir / f"stage1_struct__arm{arm}.jsonl"
        stage1_raw_path = debug_out_dir / f"stage1_raw__arm{arm}.jsonl"
        
        if stage1_struct_path.exists():
            debug_info["output_files"]["stage1_struct"] = str(stage1_struct_path)
            # Check if group was processed
            with open(stage1_struct_path, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
                if lines:
                    try:
                        data = json.loads(lines[0])
                        if data.get("group_key") == group_key:
                            debug_info["success"] = True
                            debug_info["output_files"]["stage1_struct_content"] = data
                    except Exception as e:
                        debug_info["error"] = f"Failed to parse stage1_struct: {e}"
        
        if stage1_raw_path.exists():
            debug_info["output_files"]["stage1_raw"] = str(stage1_raw_path)
        
        # Check debug directory
        debug_raw_dir = debug_out_dir / "debug_raw"
        if debug_raw_dir.exists():
            debug_files = list(debug_raw_dir.glob("**/*"))
            debug_info["output_files"]["debug_files"] = [str(f) for f in debug_files]
        
        # Check schema retry logs
        schema_retry_log = debug_out_dir / "schema_retry_log.jsonl"
        if schema_retry_log.exists():
            debug_info["output_files"]["schema_retry_log"] = str(schema_retry_log)
            # Read retry log entries
            retry_entries = []
            with open(schema_retry_log, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            retry_entries.append(json.loads(line))
                        except:
                            pass
            debug_info["schema_retry_info"] = retry_entries
        
        if result.returncode != 0:
            debug_info["error"] = f"Process exited with code {result.returncode}"
            if result.stderr:
                debug_info["error"] += f"\nStderr: {result.stderr[:500]}"
        
        # Extract error patterns
        if result.stderr:
            error_lines = result.stderr.split("\n")
            for line in error_lines:
                if "Error" in line or "error" in line or "Exception" in line or "Traceback" in line:
                    if not debug_info.get("error_patterns"):
                        debug_info["error_patterns"] = []
                    debug_info["error_patterns"].append(line.strip())
        
        if result.stdout:
            stdout_lines = result.stdout.split("\n")
            for line in stdout_lines:
                if "❌" in line or "FAIL" in line or "Error" in line or "error" in line:
                    if not debug_info.get("error_patterns"):
                        debug_info["error_patterns"] = []
                    debug_info["error_patterns"].append(line.strip())
        
    except subprocess.TimeoutExpired:
        debug_info["error"] = "Process timed out after 10 minutes"
        debug_info["exit_code"] = -1
    except Exception as e:
        debug_info["error"] = f"Exception: {type(e).__name__}: {e}"
        debug_info["error_traceback"] = traceback.format_exc()
    
    finally:
        # Clean up temp file
        if temp_group_keys_file.exists():
            temp_group_keys_file.unlink()
    
    debug_info["end_time"] = datetime.now().isoformat()
    
    return debug_info["success"], debug_info


def analyze_debug_results(debug_results: List[Dict[str, any]]) -> Dict[str, any]:
    """Analyze debug results and categorize errors."""
    analysis = {
        "total": len(debug_results),
        "successful": sum(1 for r in debug_results if r.get("success")),
        "failed": sum(1 for r in debug_results if not r.get("success")),
        "error_categories": {},
        "common_errors": [],
    }
    
    # Categorize errors
    for result in debug_results:
        if result.get("success"):
            continue
        
        error = result.get("error", "Unknown error")
        error_type = "Unknown"
        
        if "timeout" in error.lower():
            error_type = "Timeout"
        elif "schema" in error.lower() or "validation" in error.lower():
            error_type = "Schema/Validation"
        elif "api" in error.lower() or "rate limit" in error.lower():
            error_type = "API/Rate Limit"
        elif "keyerror" in error.lower():
            error_type = "KeyError"
        elif "valueerror" in error.lower():
            error_type = "ValueError"
        elif "runtimeerror" in error.lower():
            error_type = "RuntimeError"
        elif result.get("exit_code") == -1:
            error_type = "Timeout"
        elif result.get("exit_code") and result.get("exit_code") != 0:
            error_type = f"Exit Code {result.get('exit_code')}"
        
        if error_type not in analysis["error_categories"]:
            analysis["error_categories"][error_type] = []
        analysis["error_categories"][error_type].append({
            "group_key": result.get("group_key"),
            "error": error,
        })
    
    # Find common error patterns
    error_patterns = {}
    for result in debug_results:
        if result.get("error_patterns"):
            for pattern in result["error_patterns"]:
                if pattern not in error_patterns:
                    error_patterns[pattern] = 0
                error_patterns[pattern] += 1
    
    analysis["common_errors"] = sorted(
        error_patterns.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    return analysis


def main():
    parser = argparse.ArgumentParser(
        description="Debug failed S1 groups",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument("--run_tag", type=str, required=True, help="Run tag")
    parser.add_argument("--arm", type=str, required=True, help="Arm to debug (A-F)")
    parser.add_argument(
        "--group_key",
        type=str,
        default=None,
        help="Debug specific group_key (optional)",
    )
    parser.add_argument(
        "--skip_existing",
        action="store_true",
        help="Skip groups that already exist in S1 output",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        print(f"❌ Base directory does not exist: {base_dir}")
        sys.exit(1)
    
    arm = args.arm.upper()
    
    print("=" * 70)
    print("S1 Failed Groups Debugger")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {args.run_tag}")
    print(f"Arm: {arm}")
    print("=" * 70)
    
    # Find missing groups
    if args.group_key:
        selected = load_selected_groups(base_dir, args.run_tag)
        groups_to_debug = [g for g in selected if g["group_key"] == args.group_key]
        if not groups_to_debug:
            print(f"❌ Group key not found: {args.group_key}")
            sys.exit(1)
    else:
        if args.skip_existing:
            groups_to_debug = find_missing_groups(base_dir, args.run_tag, arm)
        else:
            # Debug all selected groups
            groups_to_debug = load_selected_groups(base_dir, args.run_tag)
    
    if not groups_to_debug:
        print("\n✅ No groups to debug!")
        return 0
    
    print(f"\n>>> Found {len(groups_to_debug)} groups to debug")
    for group in groups_to_debug:
        print(f"  - {group['group_key']} ({group.get('group_id', 'unknown')})")
    
    # Create debug output directory
    debug_output_dir = base_dir / "2_Data" / "metadata" / "generated" / args.run_tag / "debug_analysis"
    debug_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run debug for each group
    print("\n" + "=" * 70)
    print("Running debug for each group...")
    print("=" * 70)
    
    debug_results = []
    for idx, group in enumerate(groups_to_debug, 1):
        print(f"\n[{idx}/{len(groups_to_debug)}] Processing {group['group_key']}...")
        success, debug_info = run_single_group_debug(
            base_dir, args.run_tag, arm, group, debug_output_dir
        )
        debug_results.append(debug_info)
        
        if success:
            print(f"✅ Success: {group['group_key']}")
        else:
            print(f"❌ Failed: {group['group_key']}")
            if debug_info.get("error"):
                print(f"   Error: {debug_info['error'][:200]}")
    
    # Save debug results
    debug_results_file = debug_output_dir / f"debug_results_arm{arm}.json"
    with open(debug_results_file, "w", encoding="utf-8") as f:
        json.dump(debug_results, f, indent=2, ensure_ascii=False)
    print(f"\n>>> Saved debug results to: {debug_results_file}")
    
    # Analyze results
    print("\n" + "=" * 70)
    print("Analysis")
    print("=" * 70)
    
    analysis = analyze_debug_results(debug_results)
    print(f"\nTotal groups: {analysis['total']}")
    print(f"Successful: {analysis['successful']}")
    print(f"Failed: {analysis['failed']}")
    
    if analysis['failed'] > 0:
        print(f"\nError Categories:")
        for error_type, groups in analysis['error_categories'].items():
            print(f"  {error_type}: {len(groups)} groups")
            for group_info in groups[:3]:  # Show first 3
                print(f"    - {group_info['group_key']}")
                print(f"      {group_info['error'][:100]}")
            if len(groups) > 3:
                print(f"    ... and {len(groups) - 3} more")
        
        if analysis['common_errors']:
            print(f"\nCommon Error Patterns:")
            for pattern, count in analysis['common_errors'][:5]:
                print(f"  [{count}x] {pattern[:100]}")
    
    # Save analysis
    analysis_file = debug_output_dir / f"analysis_arm{arm}.json"
    with open(analysis_file, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"\n>>> Saved analysis to: {analysis_file}")
    
    # Summary report
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Debug results: {debug_results_file}")
    print(f"Analysis: {analysis_file}")
    print(f"\nFailed groups: {analysis['failed']}/{analysis['total']}")
    
    if analysis['failed'] > 0:
        print("\nFailed group details:")
        for result in debug_results:
            if not result.get("success"):
                print(f"  - {result['group_key']}")
                if result.get("error"):
                    print(f"    Error: {result['error'][:150]}")
                if result.get("error_patterns"):
                    print(f"    Patterns: {', '.join(result['error_patterns'][:3])}")
    
    return 0 if analysis['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""
6-Arm S1 + S2 + S3 Full Execution and Results Report Generator

This script:
1. Executes S1 for all 6 arms (A, B, C, D, E, F)
2. Executes S2 for all 6 arms (using S1 outputs)
3. Executes S3 for all 6 arms (using S2 outputs)
4. Collects results and generates a markdown report
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

ARM_LABELS = {
    "A": "Baseline",
    "B": "RAG Only",
    "C": "Thinking",
    "D": "Synergy",
    "E": "High-End",
    "F": "Benchmark"
}

def run_command(cmd: List[str], arm: str) -> tuple[bool, str]:
    """Run a command and return (success, output)"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"


def parse_jsonl_metrics(jsonl_path: Path) -> Dict[str, Any]:
    """Parse JSONL file and extract metrics"""
    metrics = {
        "n_records": 0,
        "latency_s1_mean": None,
        "latency_s2_mean": None,
        "input_tokens_s1_mean": None,
        "output_tokens_s1_mean": None,
        "input_tokens_s2_mean": None,
        "output_tokens_s2_mean": None,
        "thinking_enabled": None,
        "rag_enabled": None,
        "thinking_budget": None,
        "rag_queries_count_mean": None,
        "rag_sources_count_mean": None,
        "provider": None,
        "model_stage1": None,
        "model_stage2": None,
    }
    
    if not jsonl_path.exists():
        return metrics
    
    lat_s1, lat_s2 = [], []
    tok_s1_in, tok_s1_out = [], []
    tok_s2_in, tok_s2_out = [], []
    rag_queries, rag_sources = [], []
    
    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                metrics["n_records"] += 1
                
                # Extract runtime metadata
                runtime = obj.get("metadata", {}).get("runtime", {})
                
                if metrics["provider"] is None:
                    metrics["provider"] = runtime.get("provider")
                    metrics["model_stage1"] = runtime.get("model_stage1")
                    metrics["model_stage2"] = runtime.get("model_stage2")
                    metrics["thinking_enabled"] = runtime.get("thinking_enabled")
                    metrics["rag_enabled"] = runtime.get("rag_enabled")
                    metrics["thinking_budget"] = runtime.get("thinking_budget")
                
                # Latency
                if runtime.get("latency_sec_stage1") is not None:
                    lat_s1.append(float(runtime["latency_sec_stage1"]))
                if runtime.get("latency_sec_stage2") is not None:
                    lat_s2.append(float(runtime["latency_sec_stage2"]))
                
                # Tokens
                if runtime.get("input_tokens_stage1") is not None:
                    tok_s1_in.append(float(runtime["input_tokens_stage1"]))
                if runtime.get("output_tokens_stage1") is not None:
                    tok_s1_out.append(float(runtime["output_tokens_stage1"]))
                if runtime.get("input_tokens_stage2") is not None:
                    tok_s2_in.append(float(runtime["input_tokens_stage2"]))
                if runtime.get("output_tokens_stage2") is not None:
                    tok_s2_out.append(float(runtime["output_tokens_stage2"]))
                
                # RAG metrics
                if runtime.get("rag_queries_count") is not None:
                    rag_queries.append(float(runtime["rag_queries_count"]))
                if runtime.get("rag_sources_count") is not None:
                    rag_sources.append(float(runtime["rag_sources_count"]))
        
        # Calculate means
        if lat_s1:
            metrics["latency_s1_mean"] = sum(lat_s1) / len(lat_s1)
        if lat_s2:
            metrics["latency_s2_mean"] = sum(lat_s2) / len(lat_s2)
        if tok_s1_in:
            metrics["input_tokens_s1_mean"] = sum(tok_s1_in) / len(tok_s1_in)
        if tok_s1_out:
            metrics["output_tokens_s1_mean"] = sum(tok_s1_out) / len(tok_s1_out)
        if tok_s2_in:
            metrics["input_tokens_s2_mean"] = sum(tok_s2_in) / len(tok_s2_in)
        if tok_s2_out:
            metrics["output_tokens_s2_mean"] = sum(tok_s2_out) / len(tok_s2_out)
        if rag_queries:
            metrics["rag_queries_count_mean"] = sum(rag_queries) / len(rag_queries)
        if rag_sources:
            metrics["rag_sources_count_mean"] = sum(rag_sources) / len(rag_sources)
            
    except Exception as e:
        print(f"Warning: Error parsing {jsonl_path}: {e}", file=sys.stderr)
    
    return metrics


def generate_markdown_report(
    run_tag: str,
    results: Dict[str, Dict[str, Any]],
    output_path: Path,
    base_dir: Path
) -> None:
    """Generate markdown report from results"""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    md_lines = [
        "# 6-Arm S1 + S2 실행 결과 리포트",
        "",
        f"**실행 일시**: {timestamp}",
        f"**RUN_TAG**: `{run_tag}`",
        "",
        "---",
        "",
        "## 📊 실행 요약",
        "",
        "| Arm | Label | Provider | Model | Thinking | RAG | S1 상태 | S2 상태 | S3 상태 | S4 상태 |",
        "|-----|-------|----------|-------|----------|-----|---------|---------|---------|---------|"
    ]
    
    for arm in ["A", "B", "C", "D", "E", "F"]:
        arm_data = results.get(arm, {})
        s1_status = "✅ 성공" if arm_data.get("s1_success") else "❌ 실패"
        s2_status = "✅ 성공" if arm_data.get("s2_success") else "❌ 실패"
        s3_status = "✅ 성공" if arm_data.get("s3_success") else "❌ 실패"
        s4_status = "✅ 성공" if arm_data.get("s4_success") else "❌ 실패"
        
        metrics = arm_data.get("metrics", {})
        provider = metrics.get("provider", "N/A")
        model = metrics.get("model_stage1", "N/A")
        thinking = "✅ ON" if metrics.get("thinking_enabled") else "❌ OFF"
        rag = "✅ ON" if metrics.get("rag_enabled") else "❌ OFF"
        
        md_lines.append(
            f"| **{arm}** | {ARM_LABELS.get(arm, arm)} | {provider} | {model} | {thinking} | {rag} | {s1_status} | {s2_status} | {s3_status} | {s4_status} |"
        )
    
    md_lines.extend([
        "",
        "---",
        "",
        "## 🔍 상세 결과",
        ""
    ])
    
    for arm in ["A", "B", "C", "D", "E", "F"]:
        arm_data = results.get(arm, {})
        metrics = arm_data.get("metrics", {})
        
        md_lines.extend([
            f"### Arm {arm}: {ARM_LABELS.get(arm, arm)}",
            "",
            "#### 설정",
            "",
            f"- **Provider**: `{metrics.get('provider', 'N/A')}`",
            f"- **Model (Stage1)**: `{metrics.get('model_stage1', 'N/A')}`",
            f"- **Model (Stage2)**: `{metrics.get('model_stage2', 'N/A')}`",
            f"- **Thinking**: {'✅ Enabled' if metrics.get('thinking_enabled') else '❌ Disabled'}",
        ])
        
        if metrics.get("thinking_enabled") and metrics.get("thinking_budget"):
            md_lines.append(f"  - Budget: `{metrics['thinking_budget']}`")
        
        md_lines.append(f"- **RAG**: {'✅ Enabled' if metrics.get('rag_enabled') else '❌ Disabled'}")
        
        if metrics.get("rag_enabled"):
            md_lines.append("  - Mode: `google_search`")
            if metrics.get("rag_queries_count_mean") is not None:
                md_lines.append(f"  - Search Queries (avg): `{metrics['rag_queries_count_mean']:.1f}`")
            if metrics.get("rag_sources_count_mean") is not None:
                md_lines.append(f"  - Sources (avg): `{metrics['rag_sources_count_mean']:.1f}`")
        
        md_lines.extend([
            "",
            "#### 성능 지표",
            ""
        ])
        
        if metrics.get("latency_s1_mean") is not None:
            md_lines.append(f"- **Stage1 Latency (avg)**: `{metrics['latency_s1_mean']:.2f}`s")
        if metrics.get("latency_s2_mean") is not None:
            md_lines.append(f"- **Stage2 Latency (avg)**: `{metrics['latency_s2_mean']:.2f}`s")
        
        if metrics.get("input_tokens_s1_mean") is not None:
            md_lines.append(f"- **Stage1 Tokens (avg)**: Input=`{int(metrics['input_tokens_s1_mean'])}`, Output=`{int(metrics['output_tokens_s1_mean']) if metrics.get('output_tokens_s1_mean') else 'N/A'}`")
        if metrics.get("input_tokens_s2_mean") is not None:
            md_lines.append(f"- **Stage2 Tokens (avg)**: Input=`{int(metrics['input_tokens_s2_mean'])}`, Output=`{int(metrics['output_tokens_s2_mean']) if metrics.get('output_tokens_s2_mean') else 'N/A'}`")
        
        md_lines.extend([
            "",
            f"- **Records**: `{metrics.get('n_records', 0)}`",
            "",
            "#### S3 결과",
            ""
        ])
        
        # Check S3 output files
        generated_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
        s3_policy_file = generated_dir / f"image_policy_manifest__arm{arm}.jsonl"
        s3_spec_file = generated_dir / f"s3_image_spec__arm{arm}.jsonl"
        
        if s3_policy_file.exists():
            s3_policy_count = sum(1 for _ in open(s3_policy_file, "r", encoding="utf-8") if _.strip())
            md_lines.append(f"- **S3 Policy Manifest**: `{s3_policy_count}` records")
        else:
            md_lines.append(f"- **S3 Policy Manifest**: ❌ Not found")
        
        if s3_spec_file.exists():
            s3_spec_count = sum(1 for _ in open(s3_spec_file, "r", encoding="utf-8") if _.strip())
            md_lines.append(f"- **S3 Image Spec**: `{s3_spec_count}` records")
        else:
            md_lines.append(f"- **S3 Image Spec**: ❌ Not found")
        
        md_lines.extend([
            "",
            "#### S4 결과",
            ""
        ])
        
        # Check S4 output files
        s4_manifest_file = generated_dir / f"s4_image_manifest__arm{arm}.jsonl"
        images_dir = generated_dir / "images"
        
        if s4_manifest_file.exists():
            s4_count = sum(1 for _ in open(s4_manifest_file, "r", encoding="utf-8") if _.strip())
            md_lines.append(f"- **S4 Image Manifest**: `{s4_count}` records")
            
            # Count actual image files
            if images_dir.exists():
                image_files = list(images_dir.glob(f"IMG__*__*__*__*.jpg")) + list(images_dir.glob(f"IMG__*__*__*__*.png"))
                md_lines.append(f"- **S4 Generated Images**: `{len(image_files)}` files")
            else:
                md_lines.append(f"- **S4 Generated Images**: ❌ Images directory not found")
        else:
            md_lines.append(f"- **S4 Image Manifest**: ❌ Not found")
        
        md_lines.extend([
            "",
            "#### 검증",
            ""
        ])
        
        if arm_data.get("s1_success") and arm_data.get("s2_success") and arm_data.get("s3_success") and arm_data.get("s4_success"):
            md_lines.append("✅ **S1, S2, S3, S4가 모두 성공적으로 실행되었습니다.**")
        elif arm_data.get("s1_success") and arm_data.get("s2_success") and arm_data.get("s3_success"):
            md_lines.append("⚠️ **S1, S2, S3는 성공했으나 S4 실행에 문제가 있습니다.**")
            if arm_data.get("s4_error"):
                md_lines.append(f"  - S4 에러: `{arm_data['s4_error'][:200]}`")
        elif arm_data.get("s1_success") and arm_data.get("s2_success"):
            md_lines.append("⚠️ **S1과 S2는 성공했으나 S3 실행에 문제가 있습니다.**")
            if arm_data.get("s3_error"):
                md_lines.append(f"  - S3 에러: `{arm_data['s3_error'][:200]}`")
        elif arm_data.get("s1_success"):
            md_lines.append("⚠️ **S1은 성공했으나 S2 실행에 문제가 있습니다.**")
            if arm_data.get("s2_error"):
                md_lines.append(f"  - S2 에러: `{arm_data['s2_error'][:200]}`")
        else:
            md_lines.append("❌ **S1 실행에 실패했습니다.**")
            if arm_data.get("s1_error"):
                md_lines.append(f"  - S1 에러: `{arm_data['s1_error'][:200]}`")
        
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
    
    md_lines.extend([
        "## 📝 결론",
        "",
        "모든 6개 arm에 대해 S1, S2, S3, S4 실행이 완료되었습니다.",
        ""
    ])
    
    # Write to file
    output_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\n✅ 리포트가 생성되었습니다: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Run 6-arm S1+S2 and generate report")
    parser.add_argument("--base_dir", type=str, default=".", help="Base directory")
    parser.add_argument("--run_tag", type=str, required=True, help="RUN_TAG")
    parser.add_argument("--mode", type=str, default="S0", choices=["S0", "FINAL"], help="Mode")
    parser.add_argument("--sample", type=int, default=1, help="Sample size")
    parser.add_argument("--arms", type=str, nargs="+", default=["A", "B", "C", "D", "E", "F"], 
                        help="Arms to execute (default: all 6 arms)")
    parser.add_argument("--output", type=str, help="Output markdown file path (default: 2_Data/metadata/generated/{run_tag}/6ARM_S1_S2_RESULTS_{run_tag}.md)")
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    run_tag = args.run_tag
    script_path = base_dir / "3_Code" / "src" / "01_generate_json.py"
    
    if not script_path.exists():
        print(f"Error: Script not found at {script_path}", file=sys.stderr)
        sys.exit(1)
    
    results = {}
    arms = [arm.upper() for arm in args.arms]  # Normalize to uppercase
    
    print("=" * 60)
    print("6-Arm S1 + S2 + S3 + S4 Full Execution")
    print("=" * 60)
    print(f"RUN_TAG: {run_tag}")
    print(f"Mode: {args.mode}")
    print(f"Sample: {args.sample}")
    print()
    
    # Check for existing output files
    generated_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    
    # Stage 1: Execute S1 for all arms (or check existing files)
    print("=" * 60)
    print("Stage 1: Checking/Executing S1 for all arms...")
    print("=" * 60)
    
    for arm in arms:
        # Check if S1 output already exists
        stage1_raw_file = generated_dir / f"stage1_raw__arm{arm}.jsonl"
        stage1_struct_file = generated_dir / f"stage1_struct__arm{arm}.jsonl"
        s1_exists = stage1_raw_file.exists() or stage1_struct_file.exists()
        
        if s1_exists:
            print(f"\n[Arm {arm}] S1 output already exists, skipping execution")
            results[arm] = {
                "s1_success": True,
                "s1_output": "Skipped (file exists)",
                "s1_error": None,
                "s2_success": False,
                "s2_output": "",
                "s2_error": None,
                "s3_success": False,
                "s3_output": "",
                "s3_error": None,
                "metrics": {}
            }
            print(f"  ✅ S1 file found for Arm {arm}")
            continue
        
        print(f"\n[Arm {arm}] Running S1...")
        cmd = [
            sys.executable,
            str(script_path),
            "--base_dir", str(base_dir),
            "--run_tag", run_tag,
            "--arm", arm,
            "--mode", args.mode,
            "--stage", "1",
            "--sample", str(args.sample)
        ]
        
        success, output = run_command(cmd, arm)
        
        # Check if output contains error indicators even if exit code is 0
        has_error = not success or "❌ group failed" in output or "fail=" in output
        if has_error and "ok=" in output:
            # Parse ok/fail counts from output
            import re
            ok_match = re.search(r'ok=(\d+)', output)
            fail_match = re.search(r'fail=(\d+)', output)
            if ok_match and fail_match:
                ok_count = int(ok_match.group(1))
                fail_count = int(fail_match.group(1))
                has_error = fail_count > 0 or ok_count == 0
        
        # Extract error message if present
        error_msg = None
        if has_error:
            error_lines = [line for line in output.split('\n') if '❌' in line or 'error' in line.lower() or 'Error' in line or 'Exception' in line or 'Traceback' in line]
            if error_lines:
                error_msg = ' | '.join(error_lines[:3])  # Take first 3 error lines
        
        results[arm] = {
            "s1_success": success and not has_error,
            "s1_output": output,
            "s1_error": error_msg,
            "s2_success": False,
            "s2_output": "",
            "s2_error": None,
            "s3_success": False,
            "s3_output": "",
            "s3_error": None,
            "metrics": {}
        }
        
        if success and not has_error:
            print(f"  ✅ S1 completed for Arm {arm}")
        else:
            print(f"  ❌ S1 failed for Arm {arm}")
            if error_msg:
                print(f"  Error: {error_msg[:300]}")
            else:
                print(f"  Error: {output[:200]}")
    
    # Stage 2: Execute S2 for all arms (or check existing files)
    print("\n" + "=" * 60)
    print("Stage 2: Checking/Executing S2 for all arms...")
    print("=" * 60)
    
    for arm in arms:
        if not results[arm]["s1_success"]:
            print(f"\n[Arm {arm}] Skipping S2 (S1 failed)")
            continue
        
        # Check if S2 output already exists
        s2_file = generated_dir / f"s2_results__arm{arm}.jsonl"
        if s2_file.exists():
            print(f"\n[Arm {arm}] S2 output already exists, skipping execution")
            results[arm]["s2_success"] = True
            results[arm]["s2_output"] = "Skipped (file exists)"
            results[arm]["s2_error"] = None
            print(f"  ✅ S2 file found for Arm {arm}")
            continue
        
        print(f"\n[Arm {arm}] Running S2...")
        cmd = [
            sys.executable,
            str(script_path),
            "--base_dir", str(base_dir),
            "--run_tag", run_tag,
            "--arm", arm,
            "--mode", args.mode,
            "--stage", "2",
            "--sample", str(args.sample)
        ]
        
        success, output = run_command(cmd, arm)
        
        # Check if output contains error indicators
        has_error = not success or "❌ group failed" in output or "fail=" in output or "RuntimeError" in output or "Traceback" in output
        if has_error and "ok=" in output:
            import re
            ok_match = re.search(r'ok=(\d+)', output)
            fail_match = re.search(r'fail=(\d+)', output)
            if ok_match and fail_match:
                ok_count = int(ok_match.group(1))
                fail_count = int(fail_match.group(1))
                has_error = fail_count > 0 or ok_count == 0
        
        # Extract error message
        error_msg = None
        if has_error:
            error_lines = [line for line in output.split('\n') if '❌' in line or 'error' in line.lower() or 'Error' in line or 'Exception' in line or 'Traceback' in line or 'RuntimeError' in line]
            if error_lines:
                error_msg = ' | '.join(error_lines[:3])
        
        results[arm]["s2_success"] = success and not has_error
        results[arm]["s2_output"] = output
        results[arm]["s2_error"] = error_msg
        
        if success and not has_error:
            print(f"  ✅ S2 completed for Arm {arm}")
        else:
            print(f"  ❌ S2 failed for Arm {arm}")
            if error_msg:
                print(f"  Error: {error_msg[:300]}")
            else:
                print(f"  Error: {output[:200]}")
    
    # Stage 3: Execute S3 for all arms (or check existing files)
    print("\n" + "=" * 60)
    print("Stage 3: Checking/Executing S3 for all arms...")
    print("=" * 60)
    
    s3_script_path = base_dir / "3_Code" / "src" / "03_s3_policy_resolver.py"
    
    s3_script_path = base_dir / "3_Code" / "src" / "03_s3_policy_resolver.py"
    
    if not s3_script_path.exists():
        print(f"⚠️  Warning: S3 script not found at {s3_script_path}")
        print("  Checking for existing S3 files only")
    
    for arm in arms:
        if not results[arm]["s2_success"]:
            print(f"\n[Arm {arm}] Skipping S3 (S2 failed)")
            continue
        
        # Check if S3 output already exists
        s3_policy_file = generated_dir / f"image_policy_manifest__arm{arm}.jsonl"
        s3_spec_file = generated_dir / f"s3_image_spec__arm{arm}.jsonl"
        s3_exists = s3_policy_file.exists() and s3_spec_file.exists()
        
        if s3_exists:
            print(f"\n[Arm {arm}] S3 output already exists, skipping execution")
            results[arm]["s3_success"] = True
            results[arm]["s3_output"] = "Skipped (files exist)"
            results[arm]["s3_error"] = None
            print(f"  ✅ S3 files found for Arm {arm}")
            continue
        
        if not s3_script_path.exists():
            print(f"\n[Arm {arm}] S3 script not found, cannot execute")
            results[arm]["s3_success"] = False
            results[arm]["s3_output"] = ""
            results[arm]["s3_error"] = "S3 script not found"
            continue
        
        print(f"\n[Arm {arm}] Running S3...")
        cmd = [
            sys.executable,
            str(s3_script_path),
            "--base_dir", str(base_dir),
            "--run_tag", run_tag,
            "--arm", arm
        ]
        
        success, output = run_command(cmd, arm)
        
        # Check if output contains error indicators
        has_error = not success or "FAIL" in output or "Error" in output or "Exception" in output or "Traceback" in output
        if has_error:
            # Check for specific S3 error patterns
            if "S3 FAIL" in output or "S3 ImageSpec FAIL" in output:
                has_error = True
        
        # Extract error message
        error_msg = None
        if has_error:
            error_lines = [line for line in output.split('\n') if 'FAIL' in line or 'Error' in line or 'Exception' in line or 'Traceback' in line]
            if error_lines:
                error_msg = ' | '.join(error_lines[:3])
        
        results[arm]["s3_success"] = success and not has_error
        results[arm]["s3_output"] = output
        results[arm]["s3_error"] = error_msg
        
        if success and not has_error:
            print(f"  ✅ S3 completed for Arm {arm}")
        else:
            print(f"  ❌ S3 failed for Arm {arm}")
            if error_msg:
                print(f"  Error: {error_msg[:300]}")
            else:
                print(f"  Error: {output[:200]}")
    
    # Stage 4: Execute S4 for all arms (or check existing files)
    print("\n" + "=" * 60)
    print("Stage 4: Checking/Executing S4 for all arms...")
    print("=" * 60)
    
    s4_script_path = base_dir / "3_Code" / "src" / "04_s4_image_generator.py"
    
    for arm in arms:
        if not results[arm]["s3_success"]:
            print(f"\n[Arm {arm}] Skipping S4 (S3 failed)")
            results[arm]["s4_success"] = False
            results[arm]["s4_output"] = "Skipped (S3 failed)"
            results[arm]["s4_error"] = "S3 failed"
            continue
        
        # Check if S4 output already exists
        s4_manifest_file = generated_dir / f"s4_image_manifest__arm{arm}.jsonl"
        s4_exists = s4_manifest_file.exists()
        
        if s4_exists:
            # Count actual image files
            images_dir = generated_dir / "images"
            if images_dir.exists():
                image_count = len(list(images_dir.glob(f"IMG__*__arm{arm}*.jpg")) + list(images_dir.glob(f"IMG__*__arm{arm}*.png")))
                if image_count > 0:
                    print(f"\n[Arm {arm}] S4 output already exists, skipping execution")
                    results[arm]["s4_success"] = True
                    results[arm]["s4_output"] = f"Skipped (files exist, {image_count} images)"
                    results[arm]["s4_error"] = None
                    print(f"  ✅ S4 files found for Arm {arm} ({image_count} images)")
                    continue
        
        if not s4_script_path.exists():
            print(f"\n[Arm {arm}] S4 script not found, cannot execute")
            results[arm]["s4_success"] = False
            results[arm]["s4_output"] = ""
            results[arm]["s4_error"] = "S4 script not found"
            continue
        
        print(f"\n[Arm {arm}] Running S4...")
        cmd = [
            sys.executable,
            str(s4_script_path),
            "--base_dir", str(base_dir),
            "--run_tag", run_tag,
            "--arm", arm
        ]
        
        success, output = run_command(cmd, arm)
        
        # Check if output contains error indicators
        has_error = not success or "FAIL" in output or "Error" in output or "Exception" in output or "Traceback" in output
        if has_error:
            if "S4 FAIL" in output or "S4 ImageSpec FAIL" in output:
                has_error = True
        
        # Extract error message
        error_msg = None
        if has_error:
            error_lines = [line for line in output.split('\n') if 'FAIL' in line or 'Error' in line or 'Exception' in line or 'Traceback' in line]
            if error_lines:
                error_msg = ' | '.join(error_lines[:3])
        
        results[arm]["s4_success"] = success and not has_error
        results[arm]["s4_output"] = output
        results[arm]["s4_error"] = error_msg
        
        if success and not has_error:
            print(f"  ✅ S4 completed for Arm {arm}")
        else:
            print(f"  ❌ S4 failed for Arm {arm}")
            if error_msg:
                print(f"  Error: {error_msg[:300]}")
            else:
                print(f"  Error: {output[:200]}")
    
    # Collect metrics from output files
    print("\n" + "=" * 60)
    print("Collecting metrics from output files...")
    print("=" * 60)
    
    generated_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    
    for arm in arms:
        # Try to find stage1_raw file (contains runtime metadata)
        stage1_raw_file = generated_dir / f"stage1_raw__arm{arm}.jsonl"
        stage1_struct_file = generated_dir / f"stage1_struct__arm{arm}.jsonl"
        s2_file = generated_dir / f"s2_results__arm{arm}.jsonl"
        s3_policy_file = generated_dir / f"image_policy_manifest__arm{arm}.jsonl"
        s3_spec_file = generated_dir / f"s3_image_spec__arm{arm}.jsonl"
        s4_manifest_file = generated_dir / f"s4_image_manifest__arm{arm}.jsonl"
        
        # Prefer stage1_raw as it contains runtime metadata
        metrics_file = stage1_raw_file if stage1_raw_file.exists() else stage1_struct_file
        
        if metrics_file.exists():
            metrics = parse_jsonl_metrics(metrics_file)
            # Also count S2 records if available
            if s2_file.exists():
                s2_count = sum(1 for _ in open(s2_file, "r", encoding="utf-8") if _.strip())
                if s2_count > 0:
                    # Update record count to reflect S2 entities
                    metrics["n_records"] = s2_count
            results[arm]["metrics"] = metrics
            print(f"  ✅ Collected metrics for Arm {arm} from {metrics_file.name}")
        else:
            print(f"  ⚠️  No metrics file found for Arm {arm}")
        
        # Check S3 output files
        if s3_policy_file.exists():
            s3_policy_count = sum(1 for _ in open(s3_policy_file, "r", encoding="utf-8") if _.strip())
            print(f"  ✅ S3 policy manifest found for Arm {arm}: {s3_policy_count} records")
        if s3_spec_file.exists():
            s3_spec_count = sum(1 for _ in open(s3_spec_file, "r", encoding="utf-8") if _.strip())
            print(f"  ✅ S3 image spec found for Arm {arm}: {s3_spec_count} records")
        
        # Check S4 output files
        if s4_manifest_file.exists():
            s4_count = sum(1 for _ in open(s4_manifest_file, "r", encoding="utf-8") if _.strip())
            images_dir = generated_dir / "images"
            image_files = (list(images_dir.glob(f"IMG__*__*__*__*.jpg")) + list(images_dir.glob(f"IMG__*__*__*__*.png"))) if images_dir.exists() else []
            print(f"  ✅ S4 image manifest found for Arm {arm}: {s4_count} records, {len(image_files)} image files")
    
    # Generate markdown report
    print("\n" + "=" * 60)
    print("Generating markdown report...")
    print("=" * 60)
    
    if args.output:
        output_path = Path(args.output).resolve()
    else:
        # Default: save report in generated directory for the run_tag
        generated_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
        generated_dir.mkdir(parents=True, exist_ok=True)
        output_path = generated_dir / f"6ARM_S1_S2_RESULTS_{run_tag}.md"
    
    generate_markdown_report(run_tag, results, output_path, base_dir)
    
    print("\n" + "=" * 60)
    print("Execution Summary")
    print("=" * 60)
    
    for arm in arms:
        arm_data = results[arm]
        s1_status = "✅" if arm_data["s1_success"] else "❌"
        s2_status = "✅" if arm_data["s2_success"] else "❌"
        s3_status = "✅" if arm_data["s3_success"] else "❌"
        s4_status = "✅" if arm_data["s4_success"] else "❌"
        print(f"Arm {arm}: S1={s1_status} S2={s2_status} S3={s3_status} S4={s4_status}")
    
    print(f"\n✅ 리포트: {output_path}")


if __name__ == "__main__":
    main()


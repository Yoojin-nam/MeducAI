"""
Test script to identify the threshold where parallel batch result file downloads hang.

This script tests different worker counts (1, 2, 5, 10) to identify where hangs occur.
It uses the actual batch_image_generator.py functions to test real scenarios.

Usage Examples:
    # Test with default worker counts (1, 2, 5, 10) on all available batches
    python test_batch_download_worker_counts.py --base_dir .
    
    # Test with specific worker counts
    python test_batch_download_worker_counts.py --base_dir . --worker-counts 1,2,5,10
    
    # Test with limited number of batches (faster testing)
    python test_batch_download_worker_counts.py --base_dir . --worker-counts 1,2 --max-batches 5
    
    # Save results to JSON file
    python test_batch_download_worker_counts.py --base_dir . --output test_results.json
    
    # Skip already completed tests (useful for resuming interrupted test runs)
    python test_batch_download_worker_counts.py --base_dir . --output test_results.json --skip-completed

Requirements:
    - Completed batches in the batch tracking file (2_Data/metadata/.batch_tracking.json)
    - GOOGLE_API_KEY environment variable or .env file
    - Access to batch result files (batches must be in SUCCEEDED state)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add parent directory to path to import batch_image_generator
_THIS_DIR = Path(__file__).resolve().parent
_PARENT_DIR = _THIS_DIR.parent
sys.path.insert(0, str(_PARENT_DIR / "src"))

try:
    from batch_image_generator import (
        download_result_files_parallel,
        get_batch_tracking_file_path,
        load_batch_tracking_file,
        initialize_api_key_rotator,
        check_batch_status,
    )
except ImportError as e:
    print(f"❌ Error importing batch_image_generator: {e}")
    print(f"   Make sure you're running from the correct directory")
    sys.exit(1)

from dotenv import load_dotenv


def collect_batches_for_testing(
    base_dir: Path,
    rotator: Optional[Any],
    max_batches: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Collect batches that need result file downloads for testing.
    
    Args:
        base_dir: Base directory
        max_batches: Maximum number of batches to test (None = all)
        
    Returns:
        List of batch info dictionaries
    """
    batch_tracking_path = get_batch_tracking_file_path(base_dir)
    
    if not batch_tracking_path.exists():
        print(f"❌ Error: Tracking file not found: {batch_tracking_path}")
        return []
    
    tracking_data = load_batch_tracking_file(batch_tracking_path)
    batches = tracking_data.get("batches", {})
    
    if not batches:
        print("❌ No tracked batches found.")
        return []
    
    batches_to_check = []
    status_counts = {}  # Track status distribution for debugging
    
    for api_key_str, api_batches in batches.items():
        chunks = api_batches.get("chunks", [])
        run_tag = api_batches.get("run_tag", "")
        
        for chunk in chunks:
            batch_id = chunk.get("batch_id", "")
            status = chunk.get("status", "")
            prompts_metadata = chunk.get("prompts_metadata", [])
            images_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag / "images"
            
            # Track status distribution
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Only test batches that are completed (have result files)
            # Status values: JOB_STATE_SUCCEEDED, JOB_STATE_FAILED, JOB_STATE_RUNNING, etc.
            if status == "JOB_STATE_SUCCEEDED":
                # Get the actual dest_file_name from batch status
                # This ensures we use the correct file name and API key
                api_key_number = chunk.get("api_key_number")
                dest_file_name = None
                
                # Try to get dest_file_name from chunk first (if it was stored)
                # Otherwise, check batch status with the correct API key
                if not dest_file_name:
                    # Get the API key that was used to create this batch
                    chunk_api_key = None
                    if api_key_number and rotator is not None:
                        try:
                            if api_key_number in rotator.key_numbers:
                                target_index = rotator.key_numbers.index(api_key_number)
                                chunk_api_key = rotator.keys[target_index]
                        except (ValueError, IndexError):
                            pass
                    
                    # Fallback to current key if not found
                    if not chunk_api_key and rotator is not None:
                        chunk_api_key = rotator.get_current_key()
                    
                    # Check batch status to get actual dest_file_name
                    # First try with the original API key
                    status_info = None
                    if chunk_api_key:
                        try:
                            status_info = check_batch_status(batch_id, api_key=chunk_api_key)
                            if status_info and "dest_file_name" in status_info:
                                dest_file_name = status_info["dest_file_name"]
                        except Exception as e:
                            # If check fails, try other keys
                            pass
                    
                    # If not found and we have rotator, try all keys
                    if not dest_file_name and rotator is not None and len(rotator.keys) > 1:
                        for key_idx, test_key in enumerate(rotator.keys):
                            if test_key == chunk_api_key:
                                continue  # Already tried
                            try:
                                status_info = check_batch_status(batch_id, api_key=test_key)
                                if status_info and "dest_file_name" in status_info:
                                    dest_file_name = status_info["dest_file_name"]
                                    # Found the correct key
                                    actual_key_number = rotator.key_numbers[key_idx]
                                    if api_key_number != actual_key_number:
                                        print(f"   ℹ️  Batch {batch_id[:20]}... found with GOOGLE_API_KEY_{actual_key_number} (was {api_key_number if api_key_number else 'unknown'})")
                                    break
                            except Exception as e:
                                error_str = str(e)
                                # 404, 400 에러는 조용히 다음 키 시도
                                if "404" in error_str or "NOT_FOUND" in error_str or "400" in error_str or "INVALID_ARGUMENT" in error_str or "API_KEY_INVALID" in error_str:
                                    continue
                                # 다른 에러도 조용히 다음 키 시도
                                continue
                
                # Fallback: use batch_id if dest_file_name not found
                if not dest_file_name:
                    dest_file_name = batch_id
                
                batch_info = {
                    "batch_id": batch_id,
                    "dest_file_name": dest_file_name,
                    "chunk": chunk,
                    "prompts_metadata": prompts_metadata,
                    "images_dir": images_dir,
                    "run_tag": run_tag,
                }
                
                batches_to_check.append(batch_info)
                
                if max_batches and len(batches_to_check) >= max_batches:
                    break
        
        if max_batches and len(batches_to_check) >= max_batches:
            break
    
    # Print status distribution for debugging
    if status_counts:
        print(f"📊 Batch status distribution in tracking file:")
        for status, count in sorted(status_counts.items()):
            marker = "✅" if status == "JOB_STATE_SUCCEEDED" else "⏳" if status in ("JOB_STATE_RUNNING", "JOB_STATE_PENDING") else "❌"
            print(f"   {marker} {status}: {count}")
        print()
    
    if not batches_to_check:
        print(f"⚠️  No batches with status 'JOB_STATE_SUCCEEDED' found.")
        print(f"   Total batches checked: {sum(status_counts.values())}")
        print(f"   Available statuses: {', '.join(sorted(status_counts.keys()))}")
        print()
    
    return batches_to_check


def test_worker_count(
    batches_to_check: List[Dict[str, Any]],
    rotator: Optional[Any],
    worker_count: int,
    test_name: str = "",
) -> Dict[str, Any]:
    """
    Test a specific worker count and return results.
    
    Args:
        batches_to_check: List of batches to download
        rotator: API key rotator
        worker_count: Number of workers to test
        test_name: Optional test name for logging
        
    Returns:
        Dictionary with test results
    """
    print("\n" + "=" * 80)
    print(f"🧪 TEST: Worker Count = {worker_count} {test_name}")
    print("=" * 80)
    print(f"   Batches to download: {len(batches_to_check)}")
    print(f"   Workers: {worker_count}")
    print(f"   Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    start_time = time.time()
    
    try:
        # Call the actual download function
        results = download_result_files_parallel(
            batches_to_check=batches_to_check,
            rotator=rotator,
            max_workers=worker_count,
        )
        
        elapsed_time = time.time() - start_time
        
        # Analyze results
        succeeded = len([r for r in results.values() if r is not None])
        failed = len([r for r in results.values() if r is None])
        total = len(results)
        
        test_result = {
            "worker_count": worker_count,
            "test_name": test_name,
            "total_batches": total,
            "succeeded": succeeded,
            "failed": failed,
            "elapsed_time": elapsed_time,
            "success_rate": (succeeded / total * 100) if total > 0 else 0,
            "status": "COMPLETED",
            "error": None,
        }
        
        print()
        print("=" * 80)
        print(f"✅ TEST COMPLETED: Worker Count = {worker_count} {test_name}")
        print("=" * 80)
        print(f"   Total batches: {total}")
        print(f"   ✅ Succeeded: {succeeded}")
        print(f"   ❌ Failed: {failed}")
        print(f"   Success rate: {test_result['success_rate']:.1f}%")
        print(f"   Elapsed time: {elapsed_time:.2f}s")
        print(f"   Average time per batch: {elapsed_time / total:.2f}s" if total > 0 else "   N/A")
        print()
        
        return test_result
        
    except KeyboardInterrupt:
        elapsed_time = time.time() - start_time
        print()
        print("=" * 80)
        print(f"⚠️  TEST INTERRUPTED: Worker Count = {worker_count} {test_name}")
        print("=" * 80)
        print(f"   Elapsed time before interruption: {elapsed_time:.2f}s")
        print()
        
        return {
            "worker_count": worker_count,
            "test_name": test_name,
            "total_batches": len(batches_to_check),
            "succeeded": 0,
            "failed": 0,
            "elapsed_time": elapsed_time,
            "success_rate": 0,
            "status": "INTERRUPTED",
            "error": "User interrupted (KeyboardInterrupt)",
        }
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print()
        print("=" * 80)
        print(f"❌ TEST ERROR: Worker Count = {worker_count} {test_name}")
        print("=" * 80)
        print(f"   Error: {type(e).__name__}: {e}")
        print(f"   Elapsed time before error: {elapsed_time:.2f}s")
        print()
        import traceback
        traceback.print_exc()
        
        return {
            "worker_count": worker_count,
            "test_name": test_name,
            "total_batches": len(batches_to_check),
            "succeeded": 0,
            "failed": 0,
            "elapsed_time": elapsed_time,
            "success_rate": 0,
            "status": "ERROR",
            "error": f"{type(e).__name__}: {e}",
        }


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(
        description="Test different worker counts for parallel batch result file downloads"
    )
    parser.add_argument(
        "--base_dir",
        type=str,
        default=".",
        help="Base directory (default: current directory)",
    )
    parser.add_argument(
        "--worker-counts",
        type=str,
        default="1,2,5,10",
        help="Comma-separated list of worker counts to test (default: 1,2,5,10)",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="Maximum number of batches to test (default: all available)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file path for test results (default: print to stdout)",
    )
    parser.add_argument(
        "--skip-completed",
        action="store_true",
        help="Skip worker counts that have already been tested (checks output file)",
    )
    
    args = parser.parse_args()
    
    # Load .env file
    base_dir = Path(args.base_dir).resolve()
    env_path = base_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    else:
        load_dotenv(override=True)
    
    # Parse worker counts
    try:
        worker_counts = [int(w.strip()) for w in args.worker_counts.split(",")]
        worker_counts = sorted(set(worker_counts))  # Remove duplicates and sort
    except ValueError as e:
        print(f"❌ Error parsing worker counts: {e}")
        print(f"   Expected format: --worker-counts 1,2,5,10")
        sys.exit(1)
    
    if not worker_counts or any(w < 1 for w in worker_counts):
        print(f"❌ Error: Worker counts must be positive integers")
        sys.exit(1)
    
    # Load previous results if skipping completed tests
    previous_results = []
    if args.skip_completed and args.output and Path(args.output).exists():
        try:
            with open(args.output, "r", encoding="utf-8") as f:
                previous_data = json.load(f)
                previous_results = previous_data.get("test_results", [])
                print(f"📋 Loaded {len(previous_results)} previous test results")
        except Exception as e:
            print(f"⚠️  Warning: Could not load previous results: {e}")
    
    # Initialize API key rotator
    rotator = initialize_api_key_rotator(base_dir)
    
    # Collect batches for testing
    print("📋 Collecting batches for testing...")
    batches_to_check = collect_batches_for_testing(
        base_dir=base_dir,
        rotator=rotator,
        max_batches=args.max_batches,
    )
    
    if not batches_to_check:
        print("❌ No batches available for testing.")
        print("   Make sure you have completed batches in the tracking file.")
        sys.exit(1)
    
    print(f"✅ Found {len(batches_to_check)} batch(es) for testing")
    print()
    
    # Run tests for each worker count
    all_test_results = []
    
    for worker_count in worker_counts:
        # Skip if already tested
        if args.skip_completed:
            already_tested = any(
                r.get("worker_count") == worker_count and r.get("status") == "COMPLETED"
                for r in previous_results
            )
            if already_tested:
                print(f"⏭️  Skipping worker count {worker_count} (already tested)")
                continue
        
        test_result = test_worker_count(
            batches_to_check=batches_to_check,
            rotator=rotator,
            worker_count=worker_count,
            test_name=f"(Test {worker_counts.index(worker_count) + 1}/{len(worker_counts)})",
        )
        
        all_test_results.append(test_result)
        
        # Wait a bit between tests to avoid API rate limiting
        if worker_count < worker_counts[-1]:  # Don't wait after last test
            wait_time = 5
            print(f"⏳ Waiting {wait_time}s before next test...")
            time.sleep(wait_time)
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print()
    
    for result in all_test_results:
        status_icon = "✅" if result["status"] == "COMPLETED" else "⚠️" if result["status"] == "INTERRUPTED" else "❌"
        print(f"{status_icon} Workers: {result['worker_count']:2d} | "
              f"Status: {result['status']:12s} | "
              f"Success: {result['succeeded']:3d}/{result['total_batches']:3d} "
              f"({result['success_rate']:5.1f}%) | "
              f"Time: {result['elapsed_time']:7.2f}s")
        if result.get("error"):
            print(f"   Error: {result['error']}")
    
    print()
    
    # Save results to file if specified
    if args.output:
        output_data = {
            "test_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "base_dir": str(base_dir),
            "batches_tested": len(batches_to_check),
            "worker_counts_tested": worker_counts,
            "test_results": all_test_results,
        }
        
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Test results saved to: {output_path}")
        print()
    
    # Worker count recommendation
    print("=" * 80)
    print("💡 WORKER COUNT RECOMMENDATION")
    print("=" * 80)
    print()
    
    completed_results = [r for r in all_test_results if r["status"] == "COMPLETED"]
    if completed_results:
        # Find the best worker count (highest success rate, reasonable time)
        best_worker = None
        best_score = -1
        
        for result in completed_results:
            if result["total_batches"] == 0:
                continue
            # Score: success_rate * (1 / normalized_time)
            # Normalize time by dividing by worker count (more workers should be faster)
            normalized_time = result["elapsed_time"] / max(result["worker_count"], 1)
            time_score = 1.0 / max(normalized_time, 1.0)  # Avoid division by zero
            score = result["success_rate"] * time_score
            
            if score > best_score:
                best_score = score
                best_worker = result
        
        if best_worker:
            print(f"✅ Recommended worker count: {best_worker['worker_count']}")
            print(f"   Success rate: {best_worker['success_rate']:.1f}%")
            print(f"   Total time: {best_worker['elapsed_time']:.1f}s")
            print(f"   Average time per batch: {best_worker['elapsed_time'] / best_worker['total_batches']:.1f}s")
            print()
        
        # Show timing comparison
        if len(completed_results) >= 2:
            print("📊 Timing comparison:")
            for result in sorted(completed_results, key=lambda x: x["worker_count"]):
                avg_time = result["elapsed_time"] / result["total_batches"] if result["total_batches"] > 0 else 0
                print(f"   Workers {result['worker_count']:2d}: {result['elapsed_time']:6.1f}s total, {avg_time:5.1f}s per batch")
            print()
    
    # Identify threshold
    print("=" * 80)
    print("🔍 THRESHOLD ANALYSIS")
    print("=" * 80)
    print()
    
    if len(completed_results) >= 2:
        # Find where success rate drops or time increases significantly
        for i in range(len(completed_results) - 1):
            curr = completed_results[i]
            next_result = completed_results[i + 1]
            
            if next_result["success_rate"] < curr["success_rate"] - 10:  # 10% drop
                print(f"⚠️  Significant success rate drop detected:")
                print(f"   Workers {curr['worker_count']}: {curr['success_rate']:.1f}% success")
                print(f"   Workers {next_result['worker_count']}: {next_result['success_rate']:.1f}% success")
                print(f"   → Possible threshold around {curr['worker_count']} workers")
                print()
            
            if next_result["elapsed_time"] > curr["elapsed_time"] * 2:  # 2x slower
                print(f"⚠️  Significant time increase detected:")
                print(f"   Workers {curr['worker_count']}: {curr['elapsed_time']:.2f}s")
                print(f"   Workers {next_result['worker_count']}: {next_result['elapsed_time']:.2f}s")
                print(f"   → Possible threshold around {curr['worker_count']} workers")
                print()
    else:
        print("⚠️  Not enough completed tests for threshold analysis")
        print()
    
    # Check for hangs (interrupted or error status)
    hung_results = [r for r in all_test_results if r["status"] in ["INTERRUPTED", "ERROR"]]
    if hung_results:
        print("⚠️  Tests that hung or errored:")
        for result in hung_results:
            print(f"   Workers {result['worker_count']}: {result['status']}")
            if result.get("error"):
                print(f"      Error: {result['error']}")
        print()
        print("💡 Recommendation: Lower worker count to avoid hangs")
    else:
        print("✅ No hangs detected in any test")
        print()


if __name__ == "__main__":
    main()


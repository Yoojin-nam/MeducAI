#!/usr/bin/env python3
"""
S5 재실행: card_image_validation 누락된 29개 그룹
생성일: 2026-01-05

Usage:
    python3 rerun_s5_missing_groups.py                    # 기본 (순차 처리)
    python3 rerun_s5_missing_groups.py --workers 4        # 4개 그룹 동시 처리
    python3 rerun_s5_missing_groups.py --workers_s5 2     # 그룹 내 2개 워커
    python3 rerun_s5_missing_groups.py --workers 4 --workers_s5 2  # 둘 다
"""

import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

BASE_DIR = Path("/path/to/workspace/workspace/MeducAI")
RUN_TAG = "FINAL_DISTRIBUTION"
ARM = "G"

# 29개 그룹 목록
GROUPS = [
    "grp_6024906e14",
    "grp_61246822e4",
    "grp_62b879c0f5",
    "grp_6415318e8a",
    "grp_641bed1b4f",
    "grp_651a04fff1",
    "grp_667f21cebc",
    "grp_670b2ec1aa",
    "grp_68db6c4b3a",
    "grp_6a3cd258ee",
    "grp_6a9258636c",
    "grp_6ae1e80a49",
    "grp_6c8f5e306d",
    "grp_6d0f5b77d8",
    "grp_6de2ba1c83",
    "grp_70bff0442c",
    "grp_7149f98c07",
    "grp_71a686597f",
    "grp_7298635e2e",
    "grp_73d656909a",
    "grp_743004ab29",
    "grp_d94a493ab2",
    "grp_db29c16fd1",
    "grp_dc7faeae74",
    "grp_dcf5b4dc09",
    "grp_dd0ad73336",
    "grp_e190b25c83",
    "grp_e344f0c686",
    "grp_e4c2459d59",
]

OUTPUT_FILE = BASE_DIR / "2_Data/metadata/generated" / RUN_TAG / "s5_validation__armG__patch_29groups.jsonl"

# Thread-safe counter
progress_lock = Lock()
completed_count = 0


def process_group(group_id: str, workers_s5: int) -> tuple[str, bool, str]:
    """Process a single group. Returns (group_id, success, message)."""
    global completed_count
    
    src_dir = BASE_DIR / "3_Code/src"
    
    cmd = [
        sys.executable,
        str(src_dir / "05_s5_validator.py"),
        "--base_dir", str(BASE_DIR),
        "--run_tag", RUN_TAG,
        "--arm", ARM,
        "--group_id", group_id,
        "--output_path", str(OUTPUT_FILE),
        "--s5_mode", "s2_only",
        "--workers_s5", str(workers_s5),
    ]
    
    try:
        result = subprocess.run(
            cmd, 
            cwd=str(src_dir),
            capture_output=True,
            text=True,
        )
        
        with progress_lock:
            completed_count += 1
            current = completed_count
        
        if result.returncode == 0:
            return (group_id, True, f"[{current}/{len(GROUPS)}] ✓ {group_id}")
        else:
            return (group_id, False, f"[{current}/{len(GROUPS)}] ✗ {group_id}: exit code {result.returncode}")
    except Exception as e:
        with progress_lock:
            completed_count += 1
            current = completed_count
        return (group_id, False, f"[{current}/{len(GROUPS)}] ✗ {group_id}: {e}")


def main():
    global completed_count
    
    parser = argparse.ArgumentParser(description="S5 재실행: card_image_validation 누락 그룹")
    parser.add_argument("--workers", type=int, default=1, 
                        help="동시에 처리할 그룹 수 (기본: 1)")
    parser.add_argument("--workers_s5", type=int, default=1,
                        help="그룹 내 S5 워커 수 (기본: 1)")
    args = parser.parse_args()
    
    print("=" * 60)
    print("S5 재실행: card_image_validation 누락 그룹")
    print("=" * 60)
    print(f"총 {len(GROUPS)}개 그룹")
    print(f"그룹 병렬 처리: {args.workers}개")
    print(f"그룹 내 워커: {args.workers_s5}개")
    print(f"출력: {OUTPUT_FILE}")
    print()

    # 기존 출력 파일 삭제
    if OUTPUT_FILE.exists():
        OUTPUT_FILE.unlink()
        print(f"기존 파일 삭제됨")

    completed_count = 0
    failed_groups = []
    
    if args.workers == 1:
        # 순차 처리
        for group_id in GROUPS:
            _, success, msg = process_group(group_id, args.workers_s5)
            print(msg)
            if not success:
                failed_groups.append(group_id)
    else:
        # 병렬 처리
        print(f"병렬 처리 시작 ({args.workers} workers)...")
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(process_group, group_id, args.workers_s5): group_id 
                for group_id in GROUPS
            }
            
            for future in as_completed(futures):
                group_id, success, msg = future.result()
                print(msg)
                if not success:
                    failed_groups.append(group_id)

    print()
    print("=" * 60)
    if failed_groups:
        print(f"완료! (실패: {len(failed_groups)}개)")
        for g in failed_groups:
            print(f"  - {g}")
    else:
        print("S5 재실행 완료!")
    print(f"패치 파일: {OUTPUT_FILE}")
    print()
    print("다음 단계: python3 3_Code/Scripts/merge_s5_patch.py")
    print("=" * 60)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Fast S2 Regeneration - 트리거된 Entity만 빠르게 재생성

S5 validation에서 threshold 미만인 entity만 추출하여
01_generate_json.py를 병렬로 실행합니다.

Usage:
    # Dry-run (확인만)
    python3 3_Code/src/tools/regen/fast_s2_regen.py \
        --base_dir . \
        --run_tag FINAL_DISTRIBUTION \
        --arm G \
        --threshold 80 \
        --dry_run

    # 실제 실행 (8 workers)
    python3 3_Code/src/tools/regen/fast_s2_regen.py \
        --base_dir . \
        --run_tag FINAL_DISTRIBUTION \
        --arm G \
        --threshold 80 \
        --workers 8
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Unbuffered output for tee compatibility
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read JSONL file."""
    rows = []
    if not path.exists():
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    rows.append(obj)
            except json.JSONDecodeError:
                continue
    return rows


def extract_triggered_entities(
    s5_path: Path,
    threshold: float,
) -> Tuple[List[Dict[str, Any]], Set[str]]:
    """
    S5 validation에서 트리거된 entity 정보 추출.
    
    Returns:
        triggered_list: 트리거된 entity 상세 정보 리스트
        already_processed: 이미 repaired에 있는 entity_id set
    """
    triggered_list = []
    
    rows = read_jsonl(s5_path)
    
    for group_rec in rows:
        group_id = str(group_rec.get("group_id") or "").strip()
        if not group_id:
            continue
        
        s2_validation = group_rec.get("s2_cards_validation") or {}
        cards = s2_validation.get("cards") or []
        
        # Entity별로 그룹화
        entity_scores: Dict[str, Dict[str, Any]] = {}
        
        for card in cards:
            if not isinstance(card, dict):
                continue
            
            entity_id = str(card.get("entity_id") or "").strip()
            entity_name = str(card.get("entity_name") or "").strip()
            card_role = str(card.get("card_role") or "").strip()
            score = card.get("regeneration_trigger_score")
            
            if not entity_id:
                continue
            
            if entity_id not in entity_scores:
                entity_scores[entity_id] = {
                    "group_id": group_id,
                    "entity_id": entity_id,
                    "entity_name": entity_name,
                    "min_score": 100.0,
                    "cards": [],
                }
            
            if score is not None:
                try:
                    score_val = float(score)
                    entity_scores[entity_id]["min_score"] = min(
                        entity_scores[entity_id]["min_score"], 
                        score_val
                    )
                except (ValueError, TypeError):
                    pass
            
            entity_scores[entity_id]["cards"].append({
                "card_role": card_role,
                "score": score,
            })
        
        # 트리거된 entity 추출
        for entity_id, info in entity_scores.items():
            if info["min_score"] < threshold:
                triggered_list.append(info)
    
    return triggered_list, set()


def get_already_processed_entities(repaired_s2_path: Path) -> Set[str]:
    """이미 repaired에 있는 entity_id 추출."""
    processed = set()
    if not repaired_s2_path.exists():
        return processed
    
    rows = read_jsonl(repaired_s2_path)
    for rec in rows:
        entity_id = str(rec.get("entity_id") or "").strip()
        if entity_id:
            processed.add(entity_id)
    
    return processed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fast S2 Regeneration - 트리거된 Entity만 빠르게 재생성"
    )
    parser.add_argument("--base_dir", type=str, required=True, help="Project base directory")
    parser.add_argument("--run_tag", type=str, required=True, help="Run tag")
    parser.add_argument("--arm", type=str, required=True, help="Arm identifier")
    parser.add_argument("--s1_arm", type=str, default=None, help="S1 arm (defaults to --arm)")
    parser.add_argument("--threshold", type=float, default=80.0, help="Trigger score threshold")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers for S2")
    parser.add_argument("--dry_run", action="store_true", help="Show what would be done without executing")
    parser.add_argument("--skip_resume_check", action="store_true", help="Don't check already processed entities")
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    run_tag = args.run_tag.strip()
    arm = args.arm.strip().upper()
    s1_arm = args.s1_arm.strip().upper() if args.s1_arm else arm
    threshold = float(args.threshold)
    workers = int(args.workers)
    dry_run = bool(args.dry_run)
    
    data_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    s5_path = data_dir / f"s5_validation__arm{arm}.jsonl"
    repaired_s2_path = data_dir / f"s2_results__s1arm{s1_arm}__s2arm{arm}__repaired.jsonl"
    
    print("=" * 60)
    print("Fast S2 Regeneration")
    print("=" * 60)
    print(f"Run tag: {run_tag}")
    print(f"Arm: {arm}")
    print(f"Threshold: {threshold}")
    print(f"Workers: {workers}")
    print(f"Dry run: {dry_run}")
    print()
    
    # 1. S5 validation에서 트리거된 entity 추출
    print("[1] S5 validation에서 트리거된 entity 추출...")
    
    if not s5_path.exists():
        print(f"  ERROR: S5 validation not found: {s5_path}")
        sys.exit(1)
    
    triggered_list, _ = extract_triggered_entities(s5_path, threshold)
    print(f"  트리거된 entity 수: {len(triggered_list)}")
    
    # 2. 이미 처리된 entity 확인
    if not args.skip_resume_check:
        print("[2] 이미 처리된 entity 확인...")
        already_processed = get_already_processed_entities(repaired_s2_path)
        print(f"  이미 처리됨: {len(already_processed)}개")
        
        # 필터링
        remaining = [e for e in triggered_list if e["entity_id"] not in already_processed]
        print(f"  남은 entity: {len(remaining)}개")
    else:
        remaining = triggered_list
        print("[2] Resume 체크 스킵")
    
    if not remaining:
        print("\n✅ 모든 트리거된 entity가 이미 처리되었습니다!")
        return
    
    # 3. 그룹별로 entity 정리
    print("\n[3] 그룹별 entity 정리...")
    group_entities: Dict[str, List[str]] = {}
    for e in remaining:
        gid = e["group_id"]
        eid = e["entity_id"]
        if gid not in group_entities:
            group_entities[gid] = []
        group_entities[gid].append(eid)
    
    print(f"  처리할 그룹 수: {len(group_entities)}")
    
    # 상위 10개 그룹 출력
    for i, (gid, eids) in enumerate(list(group_entities.items())[:10]):
        print(f"    {gid}: {len(eids)} entities")
    if len(group_entities) > 10:
        print(f"    ... 외 {len(group_entities) - 10}개 그룹")
    
    # 4. entity_id 리스트 준비
    all_entity_ids = [e["entity_id"] for e in remaining]
    print(f"\n[4] 총 {len(all_entity_ids)}개 entity 재생성 예정")
    
    if dry_run:
        print("\n🔍 DRY RUN - 실제 실행하지 않음")
        print(f"\n각 그룹별로 해당 그룹의 entity만 전달하여 실행됩니다.")
        print(f"총 {len(group_entities)}개 그룹, {len(all_entity_ids)}개 entity")
        
        # 예시 출력
        sample_gid, sample_eids = list(group_entities.items())[0]
        print(f"\n예시 명령어 (그룹 {sample_gid}):")
        print(f"  python3 3_Code/src/01_generate_json.py \\")
        print(f"    --base_dir {base_dir} \\")
        print(f"    --run_tag {run_tag} \\")
        print(f"    --arm {arm} --s1_arm {s1_arm} \\")
        print(f"    --stage 2 \\")
        print(f"    --output_variant repaired \\")
        print(f"    --resume \\")
        print(f"    --workers {workers} \\")
        print(f"    --only_group_id {sample_gid} \\")
        for eid in sample_eids[:3]:
            print(f"    --only_entity_id {eid} \\")
        if len(sample_eids) > 3:
            print(f"    ... (+{len(sample_eids) - 3}개 entity)")
        return
    
    # 5. S2 재생성 실행 (그룹별로 해당 entity만 전달, 병렬 처리)
    print("\n[5] S2 재생성 시작...")
    
    generator_script = base_dir / "3_Code" / "src" / "01_generate_json.py"
    
    total_groups = len(group_entities)
    
    print(f"  병렬 그룹 수: {workers}", flush=True)
    print(f"  총 그룹 수: {total_groups}", flush=True)
    print(f"  총 Entity 수: {len(all_entity_ids)}", flush=True)
    print(f"  실행 중... (Ctrl+C로 중단 가능)", flush=True)
    print(flush=True)
    
    import concurrent.futures
    import threading
    
    completed = 0
    failed = 0
    lock = threading.Lock()
    
    def run_group(gid_eids: Tuple[str, List[str]]) -> Tuple[str, bool, str]:
        gid, entity_ids = gid_eids
        cmd = [
            sys.executable,
            str(generator_script),
            "--base_dir", str(base_dir),
            "--run_tag", run_tag,
            "--arm", arm,
            "--s1_arm", s1_arm,
            "--stage", "2",
            "--output_variant", "repaired",
            "--resume",
            "--workers", "1",  # 내부 워커는 1로 (외부에서 병렬화)
            "--only_group_id", gid,
        ]
        for eid in entity_ids:
            cmd.extend(["--only_entity_id", eid])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        error_msg = ""
        if result.returncode != 0:
            stderr_lines = (result.stderr or result.stdout or "").strip().split("\n")
            error_msg = "\n".join(stderr_lines[-3:])
        
        return gid, result.returncode == 0, error_msg
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(run_group, item): item[0] 
                for item in group_entities.items()
            }
            
            for future in concurrent.futures.as_completed(futures):
                gid = futures[future]
                try:
                    gid, success, error_msg = future.result()
                    with lock:
                        completed += 1
                        if success:
                            print(f"[{completed}/{total_groups}] {gid} ✅", flush=True)
                        else:
                            failed += 1
                            print(f"[{completed}/{total_groups}] {gid} ❌", flush=True)
                            if error_msg:
                                for line in error_msg.split("\n"):
                                    if line.strip():
                                        print(f"    {line}", flush=True)
                except Exception as e:
                    with lock:
                        completed += 1
                        failed += 1
                        print(f"[{completed}/{total_groups}] {gid} ❌ {e}", flush=True)
        
        print()
        print("=" * 60)
        print(f"✅ S2 재생성 완료! 성공: {completed - failed}, 실패: {failed}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단됨. 다시 실행하면 이어서 처리됩니다.")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


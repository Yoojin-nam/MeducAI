#!/usr/bin/env python3
"""
Selective Merge: Baseline + Repaired Results

이 스크립트는 S5 validation score를 기반으로 baseline과 repaired 결과를 선택적으로 병합합니다.

핵심 원칙:
- 트리거된 카드 (regeneration_trigger_score < threshold): repaired 버전 사용
- 트리거 안 된 카드: baseline 버전 유지

이렇게 하면:
- QA 평가단이 점수가 높은데 재생성된 카드를 보는 어색한 상황 방지
- 배포용에도 동일한 로직 적용 가능

Usage:
    python merge_repaired_selective.py \
        --base_dir . \
        --run_tag FINAL_DISTRIBUTION \
        --arm G \
        --threshold 90 \
        --dry_run

    # 실제 병합 (백업 생성 후)
    python merge_repaired_selective.py \
        --base_dir . \
        --run_tag FINAL_DISTRIBUTION \
        --arm G \
        --threshold 90
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read JSONL file and return list of records."""
    rows: List[Dict[str, Any]] = []
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


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    """Write list of records to JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _backup_file(path: Path) -> Optional[Path]:
    """Create timestamped backup of a file."""
    if not path.exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.parent / f"{path.stem}__backup_{timestamp}{path.suffix}"
    shutil.copy2(path, backup_path)
    return backup_path


def _get_card_score(card: Dict[str, Any]) -> Optional[float]:
    """Extract regeneration_trigger_score from a card record."""
    # Try multiple field names for compatibility
    for key in ["regeneration_trigger_score", "s5_regeneration_trigger_score", 
                "s5_card_regeneration_trigger_score"]:
        val = card.get(key)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                continue
    return None


def _build_triggered_index(
    s5_path: Path,
    threshold: float,
) -> Tuple[Set[str], Dict[str, Dict[str, Any]]]:
    """
    S5 validation 결과를 읽어서 트리거된 카드 ID 집합을 반환합니다.
    
    Returns:
        triggered_card_ids: 트리거된 카드 ID 집합 (group_id::entity_id::card_role)
        card_details: 카드별 상세 정보 (score, decision 등)
    """
    triggered_card_ids: Set[str] = set()
    card_details: Dict[str, Dict[str, Any]] = {}
    
    rows = _read_jsonl(s5_path)
    
    for group_rec in rows:
        group_id = str(group_rec.get("group_id") or "").strip()
        if not group_id:
            continue
        
        s2_cards_validation = group_rec.get("s2_cards_validation") or {}
        cards = s2_cards_validation.get("cards") or []
        
        for card in cards:
            if not isinstance(card, dict):
                continue
            
            entity_id = str(card.get("entity_id") or "").strip()
            card_role = str(card.get("card_role") or "").strip().upper()
            
            if not entity_id or not card_role:
                continue
            
            score = _get_card_score(card)
            card_key = f"{group_id}::{entity_id}::{card_role}"
            
            is_triggered = False
            trigger_reason = "not_triggered"
            
            if score is not None and score < threshold:
                is_triggered = True
                trigger_reason = f"score_{score:.1f}_lt_{threshold}"
                triggered_card_ids.add(card_key)
            
            # Check for hard triggers (blocking_error, safety issues)
            if card.get("blocking_error") is True:
                is_triggered = True
                trigger_reason = "blocking_error"
                triggered_card_ids.add(card_key)
            
            card_details[card_key] = {
                "group_id": group_id,
                "entity_id": entity_id,
                "card_role": card_role,
                "score": score,
                "is_triggered": is_triggered,
                "trigger_reason": trigger_reason,
            }
    
    return triggered_card_ids, card_details


def _index_s2_by_entity(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    S2 results를 (group_id, entity_id)로 인덱싱합니다.
    같은 entity가 여러 번 나오면 마지막 것 사용.
    """
    index: Dict[str, Dict[str, Any]] = {}
    for rec in rows:
        group_id = str(rec.get("group_id") or "").strip()
        entity_id = str(rec.get("entity_id") or "").strip()
        if group_id and entity_id:
            key = f"{group_id}::{entity_id}"
            index[key] = rec
    return index


def merge_s2_results(
    *,
    baseline_path: Path,
    repaired_path: Path,
    output_path: Path,
    triggered_card_ids: Set[str],
    threshold: float,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    S2 결과를 선택적으로 병합합니다.
    
    로직:
    - Entity 내 모든 카드가 트리거되지 않음 → baseline entity 유지
    - Entity 내 하나라도 트리거됨 → repaired entity 사용 (entity 단위 재생성이므로)
    
    Returns:
        merge_stats: 병합 통계
    """
    baseline_rows = _read_jsonl(baseline_path)
    repaired_rows = _read_jsonl(repaired_path)
    
    baseline_index = _index_s2_by_entity(baseline_rows)
    repaired_index = _index_s2_by_entity(repaired_rows)
    
    merged_rows: List[Dict[str, Any]] = []
    stats = {
        "baseline_entities": len(baseline_index),
        "repaired_entities": len(repaired_index),
        "used_baseline": 0,
        "used_repaired": 0,
        "decisions": [],
    }
    
    # 모든 entity 키 수집 (baseline + repaired)
    all_entity_keys = set(baseline_index.keys()) | set(repaired_index.keys())
    
    for entity_key in sorted(all_entity_keys):
        group_id, entity_id = entity_key.split("::", 1)
        
        # 이 entity의 카드들 중 트리거된 것이 있는지 확인
        entity_triggered = False
        for card_role in ["Q1", "Q2"]:
            card_key = f"{group_id}::{entity_id}::{card_role}"
            if card_key in triggered_card_ids:
                entity_triggered = True
                break
        
        # 결정: 트리거된 entity는 repaired 사용, 아니면 baseline
        if entity_triggered and entity_key in repaired_index:
            source = "repaired"
            rec = repaired_index[entity_key].copy()
            rec["_merge_source"] = "repaired"
            rec["_merge_reason"] = "entity_had_triggered_cards"
            rec["_merge_threshold"] = threshold
            stats["used_repaired"] += 1
        elif entity_key in baseline_index:
            source = "baseline"
            rec = baseline_index[entity_key].copy()
            rec["_merge_source"] = "baseline"
            rec["_merge_reason"] = "no_triggered_cards" if not entity_triggered else "repaired_not_available"
            rec["_merge_threshold"] = threshold
            stats["used_baseline"] += 1
        else:
            # repaired에만 있고 baseline에 없는 경우 (새 entity?)
            source = "repaired_only"
            rec = repaired_index[entity_key].copy()
            rec["_merge_source"] = "repaired"
            rec["_merge_reason"] = "new_in_repaired"
            rec["_merge_threshold"] = threshold
            stats["used_repaired"] += 1
        
        merged_rows.append(rec)
        stats["decisions"].append({
            "entity_key": entity_key,
            "source": source,
            "entity_triggered": entity_triggered,
        })
    
    if not dry_run:
        _write_jsonl(output_path, merged_rows)
    
    return stats


def merge_images(
    *,
    baseline_dir: Path,
    repaired_dir: Path,
    output_dir: Path,
    triggered_card_ids: Set[str],
    run_tag: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    이미지를 선택적으로 병합합니다.
    
    로직:
    - 트리거된 카드의 이미지 → repaired 디렉토리에서 복사
    - 트리거 안 된 카드의 이미지 → baseline 디렉토리에서 복사
    
    파일명 패턴: IMG__{run_tag}__{group_id}__{entity_id}__{card_role}.jpg
    """
    stats = {
        "total_images": 0,
        "used_baseline": 0,
        "used_repaired": 0,
        "missing_baseline": 0,
        "missing_repaired": 0,
        "decisions": [],
    }
    
    if not output_dir.exists() and not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # 모든 이미지 파일 수집
    baseline_images = set(baseline_dir.glob("IMG__*.jpg")) if baseline_dir.exists() else set()
    repaired_images = set(repaired_dir.glob("IMG__*.jpg")) if repaired_dir.exists() else set()
    
    all_image_names = {p.name for p in baseline_images} | {p.name for p in repaired_images}
    
    for img_name in sorted(all_image_names):
        # 파일명에서 card_key 추출
        # IMG__{run_tag}__{group_id}__{entity_id}__{card_role}.jpg
        parts = img_name.replace(".jpg", "").split("__")
        if len(parts) < 5:
            continue
        
        # run_tag은 parts[1]이지만 run_tag 자체에 __가 포함될 수 있음
        # 마지막 4개 요소: group_id, entity_id (colon replaced), card_role
        card_role = parts[-1]
        entity_id_raw = parts[-2]
        group_id = parts[-3]
        
        # entity_id에서 DERIVED: 형식 복원
        entity_id = entity_id_raw.replace("_", ":")
        
        card_key = f"{group_id}::{entity_id}::{card_role}"
        is_triggered = card_key in triggered_card_ids
        
        baseline_path = baseline_dir / img_name
        repaired_path = repaired_dir / img_name
        output_path = output_dir / img_name
        
        source = None
        src_path = None
        
        if is_triggered:
            # 트리거된 카드 → repaired 우선
            if repaired_path.exists():
                source = "repaired"
                src_path = repaired_path
                stats["used_repaired"] += 1
            elif baseline_path.exists():
                source = "baseline_fallback"
                src_path = baseline_path
                stats["missing_repaired"] += 1
                stats["used_baseline"] += 1
        else:
            # 트리거 안 된 카드 → baseline 유지
            if baseline_path.exists():
                source = "baseline"
                src_path = baseline_path
                stats["used_baseline"] += 1
            elif repaired_path.exists():
                source = "repaired_fallback"
                src_path = repaired_path
                stats["missing_baseline"] += 1
                stats["used_repaired"] += 1
        
        if src_path and not dry_run:
            shutil.copy2(src_path, output_path)
        
        stats["total_images"] += 1
        stats["decisions"].append({
            "image": img_name,
            "card_key": card_key,
            "is_triggered": is_triggered,
            "source": source,
        })
    
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Selective merge of baseline + repaired results based on S5 trigger scores"
    )
    parser.add_argument("--base_dir", type=str, required=True, help="Project base directory")
    parser.add_argument("--run_tag", type=str, required=True, help="Run tag")
    parser.add_argument("--arm", type=str, required=True, help="Arm identifier (e.g., G)")
    parser.add_argument("--s1_arm", type=str, default=None, help="S1 arm (defaults to --arm)")
    parser.add_argument("--threshold", type=float, default=90.0, help="Trigger score threshold")
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Show what would be merged without actually doing it"
    )
    parser.add_argument(
        "--no_backup",
        action="store_true",
        help="Skip creating backups (not recommended)"
    )
    parser.add_argument(
        "--merge_s2",
        action="store_true",
        default=True,
        help="Merge S2 results (default: True)"
    )
    parser.add_argument(
        "--merge_images",
        action="store_true",
        default=True,
        help="Merge images (default: True)"
    )
    parser.add_argument(
        "--output_suffix",
        type=str,
        default="merged",
        help="Output file suffix (default: 'merged')"
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    run_tag = args.run_tag.strip()
    arm = args.arm.strip().upper()
    s1_arm = args.s1_arm.strip().upper() if args.s1_arm else arm
    threshold = float(args.threshold)
    dry_run = bool(args.dry_run)
    
    data_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    
    # 파일 경로들
    s5_baseline_path = data_dir / f"s5_validation__arm{arm}.jsonl"
    s5_postrepair_path = data_dir / f"s5_validation__arm{arm}__postrepair.jsonl"
    
    s2_baseline_path = data_dir / f"s2_results__s1arm{s1_arm}__s2arm{arm}.jsonl"
    s2_repaired_path = data_dir / f"s2_results__s1arm{s1_arm}__s2arm{arm}__repaired.jsonl"
    s2_merged_path = data_dir / f"s2_results__s1arm{s1_arm}__s2arm{arm}__{args.output_suffix}.jsonl"
    
    baseline_images_dir = data_dir / "images"
    repaired_images_dir = data_dir / "images__repaired"
    merged_images_dir = data_dir / f"images__{args.output_suffix}"
    
    print("=" * 60)
    print("Selective Merge: Baseline + Repaired")
    print("=" * 60)
    print(f"Run tag: {run_tag}")
    print(f"Arm: {arm}")
    print(f"Threshold: {threshold}")
    print(f"Dry run: {dry_run}")
    print()
    
    # S5 validation에서 트리거된 카드 식별
    print("[1] S5 validation에서 트리거된 카드 식별...")
    
    # postrepair가 있으면 그것 사용 (최신 상태), 없으면 baseline 사용
    s5_path = s5_postrepair_path if s5_postrepair_path.exists() else s5_baseline_path
    
    if not s5_path.exists():
        print(f"  ERROR: S5 validation file not found: {s5_path}")
        return
    
    triggered_card_ids, card_details = _build_triggered_index(s5_path, threshold)
    
    total_cards = len(card_details)
    triggered_count = len(triggered_card_ids)
    
    print(f"  S5 source: {s5_path.name}")
    print(f"  Total cards analyzed: {total_cards}")
    print(f"  Triggered cards (score < {threshold}): {triggered_count}")
    print(f"  Non-triggered cards: {total_cards - triggered_count}")
    print()
    
    # S2 결과 병합
    if args.merge_s2:
        print("[2] S2 결과 병합...")
        
        if not s2_baseline_path.exists():
            print(f"  SKIP: Baseline S2 not found: {s2_baseline_path}")
        elif not s2_repaired_path.exists():
            print(f"  SKIP: Repaired S2 not found: {s2_repaired_path}")
        else:
            if not dry_run and not args.no_backup:
                backup_path = _backup_file(s2_merged_path)
                if backup_path:
                    print(f"  Backup created: {backup_path.name}")
            
            s2_stats = merge_s2_results(
                baseline_path=s2_baseline_path,
                repaired_path=s2_repaired_path,
                output_path=s2_merged_path,
                triggered_card_ids=triggered_card_ids,
                threshold=threshold,
                dry_run=dry_run,
            )
            
            print(f"  Baseline entities: {s2_stats['baseline_entities']}")
            print(f"  Repaired entities: {s2_stats['repaired_entities']}")
            print(f"  → Used baseline: {s2_stats['used_baseline']}")
            print(f"  → Used repaired: {s2_stats['used_repaired']}")
            
            if not dry_run:
                print(f"  Output: {s2_merged_path.name}")
        print()
    
    # 이미지 병합
    if args.merge_images:
        print("[3] 이미지 병합...")
        
        if not baseline_images_dir.exists():
            print(f"  SKIP: Baseline images dir not found: {baseline_images_dir}")
        elif not repaired_images_dir.exists():
            print(f"  SKIP: Repaired images dir not found: {repaired_images_dir}")
        else:
            img_stats = merge_images(
                baseline_dir=baseline_images_dir,
                repaired_dir=repaired_images_dir,
                output_dir=merged_images_dir,
                triggered_card_ids=triggered_card_ids,
                run_tag=run_tag,
                dry_run=dry_run,
            )
            
            print(f"  Total images: {img_stats['total_images']}")
            print(f"  → Used baseline: {img_stats['used_baseline']}")
            print(f"  → Used repaired: {img_stats['used_repaired']}")
            
            if img_stats['missing_baseline'] > 0:
                print(f"  ⚠️  Missing baseline (used repaired fallback): {img_stats['missing_baseline']}")
            if img_stats['missing_repaired'] > 0:
                print(f"  ⚠️  Missing repaired (used baseline fallback): {img_stats['missing_repaired']}")
            
            if not dry_run:
                print(f"  Output dir: {merged_images_dir.name}/")
        print()
    
    # 요약 리포트
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Threshold: {threshold}")
    print(f"Cards triggered: {triggered_count}/{total_cards} ({100*triggered_count/max(total_cards,1):.1f}%)")
    print()
    
    if dry_run:
        print("🔍 DRY RUN - No files were modified")
        print("   Remove --dry_run to perform actual merge")
    else:
        print("✅ Merge completed!")
        print()
        print("Next steps:")
        print("  1. Verify merged outputs")
        print("  2. Use merged S2 for AppSheet export:")
        print(f"     --s2_path {s2_merged_path}")
        print("  3. Use merged images for distribution:")
        print(f"     --images_dir {merged_images_dir}")
    
    # 병합 로그 저장
    log_path = data_dir / f"merge_log__{args.output_suffix}__{_utc_now_iso().replace(':', '-')}.json"
    merge_log = {
        "timestamp": _utc_now_iso(),
        "run_tag": run_tag,
        "arm": arm,
        "threshold": threshold,
        "dry_run": dry_run,
        "total_cards": total_cards,
        "triggered_cards": triggered_count,
        "triggered_card_ids": sorted(list(triggered_card_ids)),
        "output_suffix": args.output_suffix,
    }
    
    if not dry_run:
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(merge_log, f, ensure_ascii=False, indent=2)
        print(f"\nMerge log saved: {log_path.name}")


if __name__ == "__main__":
    main()


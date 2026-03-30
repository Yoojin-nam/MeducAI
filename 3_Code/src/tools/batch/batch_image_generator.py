"""
MeducAI - Batch Image Generator (Gemini Batch API)

이 스크립트는 Google Gemini Batch API를 사용하여 대량의 이미지를 생성합니다.
기존 동기식 코드(04_s4_image_generator.py)는 수정하지 않으며,
배치 처리 전용으로 독립적으로 작동합니다.

Usage:
    python batch_image_generator.py --input 2_Data/metadata/generated/<run_tag>/s3_image_spec__armA.jsonl
    python batch_image_generator.py --input <spec_file> --resume
    python batch_image_generator.py --check_status

Requirements:
    - google-genai>=1.56.0
    - GOOGLE_API_KEY 환경 변수 또는 .env 파일
"""

import argparse
import base64
import hashlib
import io
import json
import os
import re
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, Iterator, List, Optional, Tuple

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Error: google.genai not available. Install: pip install google-genai")

from dotenv import load_dotenv

# API Key Rotator (optional)
ApiKeyRotator = None
ROTATOR_AVAILABLE = False
try:
    _THIS_DIR = Path(__file__).resolve().parent
    _SRC_DIR = _THIS_DIR.parent.parent  # 3_Code/src/
    sys.path.insert(0, str(_SRC_DIR))
    from tools.api_key_rotator import ApiKeyRotator  # type: ignore
    ROTATOR_AVAILABLE = True
except Exception:
    pass

# =========================
# Configuration
# =========================

# Tier 1 Batch Limit: 2,000,000 tokens
TIER1_BATCH_TOKEN_LIMIT = 2_000_000

# Default model
DEFAULT_MODEL = "models/nano-banana-pro-preview"  # gemini-3-pro-image-preview

# Image generation config (2K resolution for cards)
IMAGE_ASPECT_RATIO = "4:5"
IMAGE_SIZE = "2K"
IMAGE_TEMPERATURE = 0.2

# Table visual settings (infographic - 16:9 4K)
TABLE_ASPECT_RATIO = "16:9"
TABLE_SIZE = "4K"

# API Key
GEMINI_API_KEY_ENV = "GOOGLE_API_KEY"

# Batch tracking file
def get_batch_tracking_file_path(base_dir: Path) -> Path:
    """배치 추적 파일 경로를 반환합니다."""
    return base_dir / "2_Data" / "metadata" / ".batch_tracking.json"


def get_batch_log_dir(base_dir: Path) -> Path:
    """배치 로그 디렉토리 경로를 반환합니다."""
    return base_dir / "2_Data" / "metadata" / "batch_logs"


def get_api_usage_file_path(base_dir: Path) -> Path:
    """API 키별 사용량 추적 파일 경로를 반환합니다."""
    return base_dir / "2_Data" / "metadata" / ".api_usage.json"


def resolve_images_dir(
    base_dir: Path,
    run_tag: str,
    image_type: Optional[str] = None,
) -> Path:
    """
    image_type에 따라 이미지 디렉토리 경로를 반환합니다.
    
    Args:
        base_dir: 프로젝트 베이스 디렉토리
        run_tag: 실행 태그
        image_type: 이미지 타입 ('anki', 'realistic', 'regen', 'repaired', None)
    
    Returns:
        이미지 디렉토리 경로
    """
    out_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    
    if image_type == "anki":
        return out_dir / "images_anki"
    elif image_type == "realistic":
        return out_dir / "images_realistic"
    elif image_type == "regen":
        return out_dir / "images_regen"
    elif image_type == "repaired":
        return out_dir / "images__repaired"
    else:
        return out_dir / "images"


def resolve_filename_suffix(image_type: Optional[str] = None, filename_suffix: Optional[str] = None) -> str:
    """
    image_type 또는 명시적 filename_suffix에서 파일명 suffix를 반환합니다.
    
    Args:
        image_type: 이미지 타입 ('anki', 'realistic', 'regen', None)
        filename_suffix: 명시적 suffix (우선순위 높음)
    
    Returns:
        파일명 suffix (예: '_realistic', '_regen', '')
    """
    if filename_suffix is not None:
        return filename_suffix
    
    if image_type == "realistic":
        return "_realistic"
    elif image_type == "regen":
        return "_regen"
    else:
        return ""


# Global rotator instance
_global_rotator: Optional[Any] = None

# Global image_type settings (set by CLI args)
_global_image_type: Optional[str] = None
_global_filename_suffix: str = ""


# =========================
# Token Calculation (Feasibility Check)
# =========================

def estimate_tokens_per_request(prompt_text: str, image_size: str = "2K") -> int:
    """
    이미지 생성 요청 1회당 소모되는 토큰 수를 추정합니다.
    
    Args:
        prompt_text: 입력 프롬프트 텍스트
        image_size: 이미지 크기 ("1K", "2K", "4K")
    
    Returns:
        예상 토큰 수 (입력 + 출력 예약)
    """
    # 입력 토큰 추정 (보수적: 1자당 0.3 토큰으로 계산)
    input_tokens = int(len(prompt_text) * 0.3)
    
    # 출력 토큰 추정 (이미지 생성용 예약 토큰)
    output_tokens_map = {
        "1K": 1500,
        "2K": 2500,
        "4K": 4000,
    }
    output_tokens = output_tokens_map.get(image_size, 2500)  # Default: 2K
    
    return input_tokens + output_tokens


def split_prompts_by_token_limit(
    prompts_with_metadata: List[Dict[str, Any]],
    image_size: str = "2K",
    token_limit: int = TIER1_BATCH_TOKEN_LIMIT,
    safe_margin: float = 0.9,
    optimize_batch_size: bool = True,
) -> List[List[Dict[str, Any]]]:
    """
    프롬프트 리스트를 토큰 한도에 맞춰 자동으로 배치로 분할합니다.
    
    Args:
        prompts_with_metadata: 프롬프트와 메타데이터가 포함된 딕셔너리 리스트
        image_size: 이미지 크기
        token_limit: 토큰 한도
        safe_margin: 안전 마진 (기본: 0.9 = 90%)
        optimize_batch_size: 배치 크기를 동적으로 최적화할지 여부 (기본: True)
    
    Returns:
        분할된 배치 리스트 (각 배치는 프롬프트 딕셔너리 리스트)
    """
    safe_limit = int(token_limit * safe_margin)
    batches: List[List[Dict[str, Any]]] = []
    current_batch: List[Dict[str, Any]] = []
    current_tokens = 0
    
    # Calculate average tokens per request for optimization
    avg_tokens = 0
    if optimize_batch_size and prompts_with_metadata:
        total_tokens = 0
        count = 0
        for prompt_data in prompts_with_metadata:
            prompt_text = prompt_data.get("prompt_en", "")
            if not prompt_text:
                continue
            spec_kind = str(prompt_data.get("spec_kind", "")).strip()
            request_image_size = "4K" if spec_kind == "S1_TABLE_VISUAL" else image_size
            total_tokens += estimate_tokens_per_request(prompt_text, request_image_size)
            count += 1
        if count > 0:
            avg_tokens = total_tokens / count
    
    for prompt_data in prompts_with_metadata:
        prompt_text = prompt_data.get("prompt_en", "")
        if not prompt_text:
            continue
        
        # Determine image size based on spec_kind
        # S1_TABLE_VISUAL (infographic) -> 4K, others -> 2K
        spec_kind = str(prompt_data.get("spec_kind", "")).strip()
        request_image_size = "4K" if spec_kind == "S1_TABLE_VISUAL" else image_size
        
        tokens = estimate_tokens_per_request(prompt_text, request_image_size)
        
        # 현재 배치에 추가하면 한도를 초과하는지 확인
        if current_tokens + tokens > safe_limit and current_batch:
            # 현재 배치를 저장하고 새 배치 시작
            batches.append(current_batch)
            current_batch = [prompt_data]
            current_tokens = tokens
        else:
            # 현재 배치에 추가
            current_batch.append(prompt_data)
            current_tokens += tokens
    
    # 마지막 배치 추가
    if current_batch:
        batches.append(current_batch)
    
    # Optimize batch sizes if requested
    if optimize_batch_size and avg_tokens > 0 and len(batches) > 1:
        # Try to balance batch sizes for better parallel processing
        optimized_batches = []
        target_batch_size = max(1, int(safe_limit / avg_tokens))
        
        for batch in batches:
            batch_tokens = sum(
                estimate_tokens_per_request(
                    p.get("prompt_en", ""),
                    "4K" if str(p.get("spec_kind", "")).strip() == "S1_TABLE_VISUAL" else image_size
                ) for p in batch
            )
            
            # If batch is too small and can be merged with next, do so
            if batch_tokens < safe_limit * 0.5 and len(optimized_batches) > 0:
                last_batch = optimized_batches[-1]
                last_batch_tokens = sum(
                    estimate_tokens_per_request(
                        p.get("prompt_en", ""),
                        "4K" if str(p.get("spec_kind", "")).strip() == "S1_TABLE_VISUAL" else image_size
                    ) for p in last_batch
                )
                
                # Try to merge if total is within safe limit
                if last_batch_tokens + batch_tokens <= safe_limit:
                    optimized_batches[-1].extend(batch)
                    continue
            
            optimized_batches.append(batch)
        
        batches = optimized_batches
    
    return batches


def calculate_batch_feasibility(
    prompts: List[str],
    image_size: str = "2K",
    token_limit: int = TIER1_BATCH_TOKEN_LIMIT,
) -> Tuple[bool, int, int, Optional[int]]:
    """
    배치 요청이 토큰 한도 내에 들어가는지 계산합니다.
    """
    num_requests = len(prompts)
    
    if num_requests == 0:
        return True, 0, 0, None
    
    # 각 요청당 평균 토큰 추정
    avg_tokens_per_request = sum(
        estimate_tokens_per_request(prompt, image_size) for prompt in prompts
    ) / num_requests
    
    total_tokens = int(avg_tokens_per_request * num_requests)
    
    is_feasible = total_tokens <= token_limit
    
    # 안전 마진을 고려한 권장 청크 크기 (90% 한도 사용)
    safe_limit = int(token_limit * 0.9)
    recommended_chunk_size = None
    if not is_feasible or total_tokens > safe_limit:
        recommended_chunk_size = max(1, int(safe_limit / avg_tokens_per_request))
    
    return is_feasible, total_tokens, num_requests, recommended_chunk_size


def print_feasibility_report(
    prompts: List[str],
    image_size: str = "2K",
    token_limit: int = TIER1_BATCH_TOKEN_LIMIT,
) -> None:
    """Feasibility check 결과를 출력합니다."""
    is_feasible, total_tokens, num_requests, chunk_size = calculate_batch_feasibility(
        prompts, image_size, token_limit
    )
    
    print("=" * 60)
    print("Batch Token Feasibility Check")
    print("=" * 60)
    print(f"Total requests: {num_requests}")
    print(f"Image size: {image_size}")
    print(f"Token limit: {token_limit:,}")
    print(f"Estimated total tokens: {total_tokens:,}")
    print(f"Token usage: {total_tokens / token_limit * 100:.1f}% of limit")
    print(f"Feasible: {'✅ YES' if is_feasible else '❌ NO'}")
    
    if chunk_size:
        print(f"\n⚠️  Recommendation: Split into chunks of {chunk_size} requests")
        num_chunks = (num_requests + chunk_size - 1) // chunk_size
        print(f"   Total chunks needed: {num_chunks}")
    else:
        print("\n✅ All requests can be processed in a single batch")
    
    print("=" * 60)


# =========================
# Prompt Loading
# =========================

def load_prompts_from_spec(spec_path: Path) -> List[Dict[str, Any]]:
    """
    s3_image_spec.jsonl에서 프롬프트와 메타데이터를 로드합니다.
    동일한 (run_tag, group_id, entity_id, card_role, spec_kind, cluster_id) 조합은 중복 제거됩니다.
    
    NOTE:
    - S1_TABLE_VISUAL은 entity_id/card_role가 비어있는 경우가 많아 cluster_id를 포함하지 않으면
      서로 다른 클러스터가 중복으로 처리되어 로드 단계에서 유실될 수 있습니다.
    
    Returns:
        List of dicts with keys: 'prompt_en', 'run_tag', 'group_id', 
        'entity_id', 'card_role', 'spec_kind', etc.
    """
    prompts_data = []
    seen_keys = set()  # Track unique entity keys to prevent duplicates
    duplicate_count = 0
    
    if not spec_path.exists():
        print(f"❌ Error: Spec file not found: {spec_path}")
        return prompts_data
    
    try:
        with open(spec_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    spec = json.loads(line)
                    prompt_en = spec.get("prompt_en", "").strip()
                    if not prompt_en:
                        print(f"⚠️  Warning: Line {line_num} missing prompt_en, skipping")
                        continue
                    
                    spec_kind = str(spec.get("spec_kind", "")).strip()
                    cluster_id = str(spec.get("cluster_id", "")).strip() if spec_kind == "S1_TABLE_VISUAL" else ""
                    
                    # Create unique key for deduplication
                    entity_key = (
                        str(spec.get("run_tag", "")),
                        str(spec.get("group_id", "")),
                        str(spec.get("entity_id", "")),
                        str(spec.get("card_role", "")),
                        spec_kind,
                        cluster_id,
                    )
                    
                    # Skip if already seen (first occurrence is kept)
                    if entity_key in seen_keys:
                        duplicate_count += 1
                        continue
                    
                    seen_keys.add(entity_key)
                    
                    prompts_data.append({
                        "prompt_en": prompt_en,
                        "run_tag": spec.get("run_tag", ""),
                        "group_id": spec.get("group_id", ""),
                        "entity_id": spec.get("entity_id"),
                        "card_role": spec.get("card_role"),
                        "spec_kind": spec_kind,
                        "cluster_id": spec.get("cluster_id"),
                        "image_placement_final": spec.get("image_placement_final", ""),
                        "modality": spec.get("modality"),
                        "anatomy_region": spec.get("anatomy_region"),
                        "visual_type_category": spec.get("visual_type_category"),
                    })
                except json.JSONDecodeError as e:
                    print(f"⚠️  Warning: Line {line_num} JSON decode error: {e}, skipping")
                    continue
        
        if duplicate_count > 0:
            print(f"✅ Loaded {len(prompts_data)} prompts from {spec_path} (removed {duplicate_count} duplicate(s))")
        else:
            print(f"✅ Loaded {len(prompts_data)} prompts from {spec_path}")
        return prompts_data
    
    except Exception as e:
        print(f"❌ Error loading prompts from spec: {e}")
        import traceback
        traceback.print_exc()
        return []


# =========================
# Batch Tracking
# =========================

def load_batch_tracking_file(tracking_path: Path) -> Dict[str, Any]:
    """
    배치 작업 추적 파일을 로드합니다.
    """
    if not tracking_path.exists():
        return {
            "schema_version": "BATCH_TRACKING_v1.0",
            "batches": {},
            "last_updated": datetime.now().isoformat(),
        }
    
    try:
        with open(tracking_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure schema version
            if "schema_version" not in data:
                data["schema_version"] = "BATCH_TRACKING_v1.0"
            if "batches" not in data:
                data["batches"] = {}
            return data
    except Exception as e:
        print(f"⚠️  Warning: Error loading tracking file: {e}, creating new one")
        return {
            "schema_version": "BATCH_TRACKING_v1.0",
            "batches": {},
            "last_updated": datetime.now().isoformat(),
        }


def save_batch_tracking_file(tracking_path: Path, data: Dict[str, Any]) -> bool:
    """배치 추적 파일을 저장합니다."""
    try:
        tracking_path.parent.mkdir(parents=True, exist_ok=True)
        data["last_updated"] = datetime.now().isoformat()
        with open(tracking_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error saving tracking file: {e}")
        return False


def cleanup_duplicate_batches(tracking_data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    중복된 엔티티를 가진 배치 중 하나만 남기고 나머지 제거.
    
    개선 사항:
    1. 인덱스를 직접 조작하지 않고, 유지할 chunk만 수집
    2. 전체 복사 대신 필요한 부분만 재구성
    3. 더 효율적인 데이터 구조 처리
    
    Args:
        tracking_data: 배치 트래킹 데이터
        
    Returns:
        (정리된 tracking_data, 제거된 배치 수)
    """
    STATUS_PRIORITY = {
        "JOB_STATE_SUCCEEDED": 4,
        "JOB_STATE_RUNNING": 3,
        "JOB_STATE_PENDING": 2,
        "JOB_STATE_FAILED": 1,
        "JOB_STATE_CANCELLED": 0,
        "JOB_STATE_EXPIRED": 0,
    }
    
    # entity_key -> [(api_key_str, chunk_index, chunk_data, priority), ...]
    entity_to_batches = defaultdict(list)
    
    # 모든 배치 수집
    for api_key_str, api_batches in tracking_data.get("batches", {}).items():
        chunks = api_batches.get("chunks", [])
        for chunk_index, chunk in enumerate(chunks):
            batch_id = chunk.get("batch_id", "")
            status = chunk.get("status", "")
            created_at = chunk.get("created_at", "")
            
            for meta in chunk.get("prompts_metadata", []):
                entity_key = (
                    str(meta.get("run_tag", "")).strip(),
                    str(meta.get("group_id", "")).strip(),
                    str(meta.get("entity_id", "")).strip(),
                    str(meta.get("card_role", "")).strip(),
                    str(meta.get("spec_kind", "")).strip(),
                )
                priority = STATUS_PRIORITY.get(status, 0)
                entity_to_batches[entity_key].append({
                    "api_key_str": api_key_str,
                    "chunk_index": chunk_index,
                    "batch_id": batch_id,
                    "status": status,
                    "created_at": created_at,
                    "priority": priority,
                })
    
    # 유지할 배치 결정 (중복이 있는 경우만)
    chunks_to_keep = set()  # (api_key_str, chunk_index)
    chunks_to_remove = set()  # (api_key_str, chunk_index)
    
    for entity_key, batches in entity_to_batches.items():
        if len(batches) > 1:
            # 우선순위에 따라 정렬 (높은 우선순위, 최신 생성일 우선)
            batches.sort(key=lambda b: (
                b["priority"],
                b["created_at"] or "",
            ), reverse=True)
            
            # 첫 번째 배치만 유지
            keep = batches[0]
            chunks_to_keep.add((keep["api_key_str"], keep["chunk_index"]))
            
            for batch_info in batches[1:]:
                chunks_to_remove.add((batch_info["api_key_str"], batch_info["chunk_index"]))
    
    # tracking_data 재구성 (유지할 chunk만 포함)
    cleaned_data = {
        "schema_version": tracking_data.get("schema_version", "BATCH_TRACKING_v1.0"),
        "batches": {},
    }
    
    removed_count = 0
    for api_key_str, api_batches in tracking_data.get("batches", {}).items():
        chunks = api_batches.get("chunks", [])
        kept_chunks = []
        
        for chunk_index, chunk in enumerate(chunks):
            key = (api_key_str, chunk_index)
            if key in chunks_to_remove:
                removed_count += 1
            else:
                # 중복이 아닌 배치 또는 유지할 배치
                kept_chunks.append(chunk)
        
        if kept_chunks:  # chunk가 하나라도 있으면 유지
            cleaned_data["batches"][api_key_str] = {
                "chunks": kept_chunks,
                "prompts_hash": api_batches.get("prompts_hash"),
                "run_tag": api_batches.get("run_tag"),
            }
    
    return cleaned_data, removed_count


def cleanup_and_save_tracking_file(tracking_path: Path, backup: bool = True) -> Tuple[bool, int]:
    """
    배치 트래킹 파일을 로드하고 중복 정리 후 저장.
    
    Args:
        tracking_path: 배치 트래킹 파일 경로
        backup: 백업 파일 생성 여부 (기본값: True)
        
    Returns:
        (성공 여부, 제거된 배치 수)
    """
    try:
        # Load tracking file
        tracking_data = load_batch_tracking_file(tracking_path)
        
        # Create backup if requested
        if backup and tracking_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = Path(f"{tracking_path}.backup_{timestamp}")
            try:
                import shutil
                shutil.copy2(tracking_path, backup_path)
                print(f"📦 Backup created: {backup_path}")
            except Exception as e:
                print(f"⚠️  Warning: Failed to create backup: {e}")
        
        # Cleanup duplicates
        cleaned_data, removed_count = cleanup_duplicate_batches(tracking_data)
        
        # Save cleaned data
        success = save_batch_tracking_file(tracking_path, cleaned_data)
        
        if success:
            print(f"✅ Cleanup completed: {removed_count} duplicate batch(es) removed")
        else:
            print(f"❌ Failed to save cleaned tracking file")
        
        return success, removed_count
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False, 0


def get_batch_failed_file_path(base_dir: Path) -> Path:
    """실패한 배치 추적 파일 경로를 반환합니다."""
    return base_dir / "2_Data" / "metadata" / ".batch_failed.json"


def _backup_file_with_timestamp(path: Path, timestamp: str) -> Optional[Path]:
    """
    파일을 같은 디렉토리에 timestamp suffix로 백업합니다.
    예: .batch_tracking.json -> .batch_tracking.json.backup_YYYYmmdd_HHMMSS
    """
    if not path.exists():
        return None
    backup_path = path.parent / f"{path.name}.backup_{timestamp}"
    try:
        shutil.copy2(path, backup_path)
        return backup_path
    except Exception as e:
        print(f"⚠️  Warning: Failed to backup {path}: {e}")
        return None


def reset_batch_state_files(
    base_dir: Path,
    *,
    backup: bool = True,
) -> Dict[str, Any]:
    """
    수리 실패 시 사용할 fallback: tracking/failed 파일을 백업 후 초기화합니다.
    (이미지 파일은 건드리지 않으므로, 재시작 시 로컬 이미지 기반 스킵은 유지됩니다.)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tracking_path = get_batch_tracking_file_path(base_dir)
    failed_path = get_batch_failed_file_path(base_dir)

    backup_tracking = None
    backup_failed = None
    if backup:
        backup_tracking = _backup_file_with_timestamp(tracking_path, timestamp)
        backup_failed = _backup_file_with_timestamp(failed_path, timestamp)

    # Reset to empty schema
    tracking_data = {
        "schema_version": "BATCH_TRACKING_v1.0",
        "batches": {},
        "last_updated": datetime.now().isoformat(),
    }
    failed_data = {
        "schema_version": "BATCH_FAILED_v1.0",
        "failed_batches": [],
        "last_updated": datetime.now().isoformat(),
    }

    ok_tracking = save_batch_tracking_file(tracking_path, tracking_data)
    ok_failed = save_batch_failed_file(failed_path, failed_data)

    return {
        "tracking_path": str(tracking_path),
        "failed_path": str(failed_path),
        "backup_tracking_path": str(backup_tracking) if backup_tracking else "",
        "backup_failed_path": str(backup_failed) if backup_failed else "",
        "ok_tracking": ok_tracking,
        "ok_failed": ok_failed,
        "timestamp": timestamp,
    }


def load_batch_failed_file(failed_path: Path) -> Dict[str, Any]:
    """실패한 배치 추적 파일을 로드합니다."""
    if not failed_path.exists():
        return {
            "schema_version": "BATCH_FAILED_v1.0",
            "failed_batches": [],
            "last_updated": datetime.now().isoformat(),
        }
    
    try:
        with open(failed_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "schema_version" not in data:
                data["schema_version"] = "BATCH_FAILED_v1.0"
            if "failed_batches" not in data:
                data["failed_batches"] = []
            return data
    except Exception as e:
        print(f"⚠️  Warning: Error loading failed batches file: {e}, creating new one")
        return {
            "schema_version": "BATCH_FAILED_v1.0",
            "failed_batches": [],
            "last_updated": datetime.now().isoformat(),
        }


def save_batch_failed_file(failed_path: Path, data: Dict[str, Any]) -> bool:
    """실패한 배치 추적 파일을 저장합니다."""
    try:
        failed_path.parent.mkdir(parents=True, exist_ok=True)
        data["last_updated"] = datetime.now().isoformat()
        with open(failed_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error saving failed batches file: {e}")
        return False


def record_failed_batch(
    failed_path: Path,
    failed_data: Dict[str, Any],
    prompts_data: List[Dict[str, Any]],
    chunk_index: int,
    error_type: str,
    error_message: str,
    keys_tried: set,
    run_tag: str,
    spec_path: Path,
    retry_delay_hours: int = 1,
) -> None:
    """
    실패한 배치를 기록합니다.
    
    Args:
        retry_delay_hours: 재시도까지 대기할 시간 (시간 단위, 기본값: 1시간)
    """
    failed_file_data = load_batch_failed_file(failed_path)
    
    # Create metadata for each prompt
    # Normalize all fields to strings (matching create_entity_key normalization)
    prompts_metadata_list = []
    for prompt_data in prompts_data:
        prompts_metadata_list.append({
            "run_tag": str(prompt_data.get("run_tag", run_tag) or "").strip(),
            "group_id": str(prompt_data.get("group_id", "") or "").strip(),
            "entity_id": str(prompt_data.get("entity_id") or "").strip(),
            "card_role": str(prompt_data.get("card_role") or "").strip(),
            "spec_kind": str(prompt_data.get("spec_kind", "") or "").strip(),
            "cluster_id": str(prompt_data.get("cluster_id") or "").strip(),
        })
    
    # Calculate next retry time
    from datetime import timedelta
    next_retry_at = datetime.now() + timedelta(hours=retry_delay_hours)
    
    failed_batch_info = {
        "chunk_index": chunk_index,
        "run_tag": run_tag,
        "error_type": error_type,  # "429_ALL_KEYS_EXHAUSTED", "404_ALL_KEYS_FAILED", etc.
        "error_message": error_message,
        "failed_at": datetime.now().isoformat(),
        "keys_tried": sorted(list(keys_tried)) if keys_tried else [],
        "num_requests": len(prompts_data),
        "prompts_metadata": prompts_metadata_list,
        "original_spec_path": str(spec_path),
        "retry_count": 0,
        "next_retry_at": next_retry_at.isoformat(),
    }
    
    failed_file_data["failed_batches"].append(failed_batch_info)
    save_batch_failed_file(failed_path, failed_file_data)
    
    print(f"   📅 Next retry scheduled at: {next_retry_at.strftime('%Y-%m-%d %H:%M:%S')}")


def get_retryable_failed_batches(failed_path: Path) -> List[Dict[str, Any]]:
    """
    재시도 가능한 실패한 배치 목록을 반환합니다.
    
    Returns:
        재시도 가능한 배치 목록 (next_retry_at이 현재 시간 이전인 배치)
    """
    failed_file_data = load_batch_failed_file(failed_path)
    retryable = []
    
    now = datetime.now()
    for batch in failed_file_data.get("failed_batches", []):
        next_retry_at_str = batch.get("next_retry_at")
        if next_retry_at_str:
            try:
                next_retry_at = datetime.fromisoformat(next_retry_at_str)
                if next_retry_at <= now:
                    retryable.append(batch)
            except (ValueError, TypeError):
                # Invalid date format, skip
                continue
    
    return retryable


# =========================
# API Usage Tracking
# =========================

def load_api_usage_file(usage_path: Path) -> Dict[str, Any]:
    """API 키별 사용량 추적 파일을 로드합니다."""
    if not usage_path.exists():
        return {
            "schema_version": "API_USAGE_v1.0",
            "api_keys": {},
            "last_updated": datetime.now().isoformat(),
        }
    
    try:
        with open(usage_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "schema_version" not in data:
                data["schema_version"] = "API_USAGE_v1.0"
            if "api_keys" not in data:
                data["api_keys"] = {}
            return data
    except Exception as e:
        print(f"⚠️  Warning: Error loading API usage file: {e}, creating new one")
        return {
            "schema_version": "API_USAGE_v1.0",
            "api_keys": {},
            "last_updated": datetime.now().isoformat(),
        }


def save_api_usage_file(usage_path: Path, data: Dict[str, Any]) -> bool:
    """API 키별 사용량 추적 파일을 저장합니다."""
    try:
        usage_path.parent.mkdir(parents=True, exist_ok=True)
        data["last_updated"] = datetime.now().isoformat()
        with open(usage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error saving API usage file: {e}")
        return False


def track_api_usage(
    usage_path: Path,
    api_key_number: int,
    estimated_tokens: int,
    num_requests: int,
    batch_id: Optional[str] = None,
) -> None:
    """API 키 사용량을 추적합니다."""
    usage_data = load_api_usage_file(usage_path)
    
    key_str = f"GOOGLE_API_KEY_{api_key_number}"
    if key_str not in usage_data["api_keys"]:
        usage_data["api_keys"][key_str] = {
            "total_tokens": 0,
            "total_requests": 0,
            "total_batches": 0,
            "batches": [],
            "first_used": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
        }
    
    key_data = usage_data["api_keys"][key_str]
    key_data["total_tokens"] += estimated_tokens
    key_data["total_requests"] += num_requests
    key_data["total_batches"] += 1
    key_data["last_used"] = datetime.now().isoformat()
    
    if batch_id:
        key_data["batches"].append({
            "batch_id": batch_id,
            "tokens": estimated_tokens,
            "requests": num_requests,
            "timestamp": datetime.now().isoformat(),
        })
        # Keep only last 100 batches
        if len(key_data["batches"]) > 100:
            key_data["batches"] = key_data["batches"][-100:]
    
    save_api_usage_file(usage_path, usage_data)


def print_api_usage_summary(usage_path: Path) -> None:
    """API 키별 사용량 요약을 출력합니다."""
    usage_data = load_api_usage_file(usage_path)
    
    if not usage_data.get("api_keys"):
        print("📊 No API usage data found.")
        return
    
    print("\n" + "=" * 60)
    print("📊 API Key Usage Summary")
    print("=" * 60)
    
    total_tokens = 0
    total_requests = 0
    total_batches = 0
    
    for key_str, key_data in sorted(usage_data["api_keys"].items()):
        tokens = key_data.get("total_tokens", 0)
        requests = key_data.get("total_requests", 0)
        batches = key_data.get("total_batches", 0)
        
        total_tokens += tokens
        total_requests += requests
        total_batches += batches
        
        print(f"\n{key_str}:")
        print(f"  Total Tokens: {tokens:,}")
        print(f"  Total Requests: {requests:,}")
        print(f"  Total Batches: {batches}")
        print(f"  First Used: {key_data.get('first_used', 'N/A')}")
        print(f"  Last Used: {key_data.get('last_used', 'N/A')}")
    
    print("\n" + "-" * 60)
    print(f"Total Across All Keys:")
    print(f"  Total Tokens: {total_tokens:,}")
    print(f"  Total Requests: {total_requests:,}")
    print(f"  Total Batches: {total_batches}")
    print("=" * 60 + "\n")


# =========================
# Progress Monitoring
# =========================

def print_batch_progress(
    current: int,
    total: int,
    completed: int = 0,
    failed: int = 0,
    skipped: int = 0,
) -> None:
    """배치 진행률을 출력합니다."""
    pending = total - completed - failed - skipped - current
    
    print("\n" + "=" * 60)
    print("📈 Batch Progress")
    print("=" * 60)
    print(f"Total Batches: {total}")
    print(f"  ✅ Completed: {completed}")
    print(f"  ⏳ Processing: {current}")
    print(f"  ⏸️  Pending: {pending}")
    print(f"  ❌ Failed: {failed}")
    print(f"  ⏭️  Skipped: {skipped}")
    
    if total > 0:
        progress_pct = ((completed + current) / total) * 100
        print(f"\nProgress: {progress_pct:.1f}%")
        
        # Simple progress bar
        bar_length = 40
        filled = int(bar_length * (completed + current) / total)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"[{bar}]")
    
    print("=" * 60 + "\n")


def log_batch_event(
    log_dir: Path,
    event_type: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """배치 이벤트를 로그 파일에 기록합니다."""
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"batch_events_{datetime.now().strftime('%Y%m%d')}.log"
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "message": message,
    }
    
    if metadata:
        log_entry["metadata"] = metadata  # type: ignore
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"⚠️  Warning: Failed to write log entry: {e}")


def calculate_prompts_hash(prompts_data: List[Dict[str, Any]]) -> str:
    """
    프롬프트 세트의 해시를 계산합니다 (중복 확인용).
    """
    # 프롬프트만 추출하여 정렬 후 해시
    prompts_only = sorted([p.get("prompt_en", "") for p in prompts_data])
    prompts_str = "\n".join(prompts_only)
    return hashlib.sha256(prompts_str.encode("utf-8")).hexdigest()[:16]


def check_existing_batch(
    prompts_hash: str,
    api_key_index: int,
    tracking_data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    동일한 프롬프트 세트로 이미 제출된 배치가 있는지 확인.
    
    Returns:
        기존 배치 정보 (있으면), None (없으면)
    """
    api_key_str = f"api_key_{api_key_index}"
    batches = tracking_data.get("batches", {})
    
    if api_key_str not in batches:
        return None
    
    api_batches = batches[api_key_str]
    if not isinstance(api_batches, dict):
        return None
    
    # Check if prompts_hash matches
    if api_batches.get("prompts_hash") == prompts_hash:
        # Check chunks
        chunks = api_batches.get("chunks", [])
        if chunks:
            # Return first incomplete chunk if any
            for chunk in chunks:
                status = chunk.get("status", "")
                if status not in ("JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"):
                    return chunk
            # All chunks completed, return last one
            return chunks[-1] if chunks else None
    
    return None


# =========================
# JSONL File Generation
# =========================

def create_jsonl_file(
    prompts_data: List[Dict[str, Any]],
    output_path: Path,
    model: str = DEFAULT_MODEL,
    aspect_ratio: str = IMAGE_ASPECT_RATIO,
    image_size: str = IMAGE_SIZE,
    temperature: float = IMAGE_TEMPERATURE,
) -> bool:
    """
    프롬프트 리스트를 Gemini Batch API 포맷에 맞는 JSONL 파일로 저장합니다.
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            for idx, prompt_data in enumerate(prompts_data):
                prompt_en = prompt_data.get("prompt_en", "")
                if not prompt_en:
                    continue
                
                # Determine image size and aspect ratio based on spec_kind
                # S1_TABLE_VISUAL (infographic) -> 16:9 4K, others -> 4:5 2K
                spec_kind = str(prompt_data.get("spec_kind", "")).strip()
                if spec_kind == "S1_TABLE_VISUAL":
                    request_image_size = TABLE_SIZE
                    request_aspect_ratio = TABLE_ASPECT_RATIO
                else:
                    request_image_size = image_size
                    request_aspect_ratio = aspect_ratio
                
                # Batch API JSONL 포맷 (Batch.md 문서 기반)
                request_obj = {
                    "key": f"request_{idx:06d}",
                    "request": {
                        "contents": [{"parts": [{"text": prompt_en}]}],
                        "generationConfig": {
                            "temperature": temperature,
                            "responseModalities": ["TEXT", "IMAGE"],
                            "imageConfig": {
                                "aspectRatio": request_aspect_ratio,
                                "imageSize": request_image_size,
                            },
                        },
                    },
                }
                
                f.write(json.dumps(request_obj, ensure_ascii=False) + "\n")
        
        print(f"✅ JSONL file created: {output_path}")
        print(f"   Total requests: {len(prompts_data)}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating JSONL file: {e}")
        import traceback
        traceback.print_exc()
        return False


# =========================
# File Upload
# =========================

def upload_file(
    jsonl_path: Path,
    api_key: Optional[str] = None,
    max_retries: int = 3,
) -> Optional[str]:
    """
    JSONL 파일을 Google 서버에 업로드합니다 (Batch.md 문서 기반).
    
    Args:
        jsonl_path: 업로드할 JSONL 파일 경로
        api_key: API 키 (None이면 환경변수에서 로드)
        max_retries: 최대 재시도 횟수 (기본값: 3)
    
    Returns:
        업로드된 파일 URI 또는 None (실패 시)
    """
    if not GEMINI_AVAILABLE:
        print("❌ Error: google.genai not available")
        return None
    
    if not jsonl_path.exists():
        print(f"❌ Error: JSONL file not found: {jsonl_path}")
        return None
    
    # Load API key
    if api_key is None:
        api_key = os.getenv(GEMINI_API_KEY_ENV, "").strip()
        if not api_key:
            print(f"❌ Error: Missing API key ({GEMINI_API_KEY_ENV})")
            return None
    
    # Retry logic with exponential backoff
    last_error = None
    for attempt in range(max_retries):
        try:
            # Create client (recreate for each attempt)
            client = genai.Client(api_key=api_key)
            
            if attempt == 0:
                print(f"📤 Uploading file: {jsonl_path.name}...")
            else:
                wait_time = 2 ** (attempt - 1)  # 1s, 2s, 4s
                print(f"🔄 Retrying file upload (attempt {attempt + 1}/{max_retries}) after {wait_time}s...")
                time.sleep(wait_time)
            
            # Batch.md 문서 기반: client.files.upload() with config
            uploaded_file = client.files.upload(
                file=str(jsonl_path),
                config=types.UploadFileConfig(
                    display_name=jsonl_path.name,
                    mime_type='jsonl'
                )
            )
            
            file_uri = uploaded_file.name
            if attempt > 0:
                print(f"✅ File uploaded successfully after {attempt + 1} attempt(s)")
            else:
                print(f"✅ File uploaded successfully")
            print(f"   File URI: {file_uri}")
            return file_uri
            
        except Exception as e:
            last_error = e
            error_str = str(e)
            
            # Check if it's a network error (temporary) or API error (permanent)
            is_network_error = (
                "timeout" in error_str.lower() or
                "connection" in error_str.lower() or
                "network" in error_str.lower() or
                "socket" in error_str.lower() or
                "temporary" in error_str.lower()
            )
            
            is_permanent_error = (
                "401" in error_str or "UNAUTHENTICATED" in error_str or
                "403" in error_str or "PERMISSION_DENIED" in error_str or
                "400" in error_str or "INVALID_ARGUMENT" in error_str
            )
            
            if is_permanent_error:
                # Permanent errors should not be retried
                print(f"❌ Permanent error uploading file (not retrying): {e}")
                import traceback
                traceback.print_exc()
                return None
            
            if attempt < max_retries - 1:
                # Will retry
                if is_network_error:
                    print(f"⚠️  Network error (attempt {attempt + 1}/{max_retries}): {e}")
                else:
                    print(f"⚠️  Upload error (attempt {attempt + 1}/{max_retries}): {e}")
            else:
                # Last attempt failed
                print(f"❌ Error uploading file after {max_retries} attempts: {e}")
                import traceback
                traceback.print_exc()
    
    # All retries exhausted
    print(f"❌ Failed to upload file after {max_retries} attempts")
    if last_error:
        print(f"   Last error: {last_error}")
    return None


# =========================
# Batch Job Creation
# =========================

def create_batch_job(
    file_uri: str,
    model: str = DEFAULT_MODEL,
    display_name: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    업로드된 파일로 배치 작업을 생성합니다 (Batch.md 문서 기반).
    
    Returns:
        배치 작업 객체 또는 None
    """
    if not GEMINI_AVAILABLE:
        print("❌ Error: google.genai not available")
        return None
    
    try:
        # Load API key
        if api_key is None:
            api_key = os.getenv(GEMINI_API_KEY_ENV, "").strip()
            if not api_key:
                print(f"❌ Error: Missing API key ({GEMINI_API_KEY_ENV})")
                return None
        
        # Create client
        client = genai.Client(api_key=api_key)
        
        print(f"🚀 Creating batch job...")
        print(f"   Model: {model}")
        print(f"   Input file: {file_uri}")
        
        if display_name is None:
            display_name = f"batch_image_generation_{int(time.time())}"
        
        # Batch.md 문서 기반: client.batches.create() with src and config
        file_batch_job = client.batches.create(
                model=model,
            src=file_uri,
            config={
                'display_name': display_name,
            }
        )
        
        batch_id = file_batch_job.name if hasattr(file_batch_job, 'name') else None
        if not batch_id:
            print("❌ Error: Batch job created but no name returned")
            return None
        
            print(f"✅ Batch job created successfully")
            print(f"   Batch ID: {batch_id}")
        
        return {
            "name": batch_id,
            "state": file_batch_job.state if hasattr(file_batch_job, 'state') else None,
            "display_name": display_name,
        }
        
    except Exception as e:
        error_str = str(e)
        error_lower = error_str.lower()
        
        # Classify error types
        # Permanent errors (should not retry)
        is_401_error = "401" in error_str or "UNAUTHENTICATED" in error_str or "authentication" in error_lower
        is_403_error = "403" in error_str or "PERMISSION_DENIED" in error_str or "forbidden" in error_lower
        is_400_error = "400" in error_str or "INVALID_ARGUMENT" in error_str or "bad request" in error_lower
        
        # Temporary errors (can retry)
        is_429_error = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_lower
        is_404_error = "404" in error_str or "NOT_FOUND" in error_str
        is_503_error = "503" in error_str or "SERVICE_UNAVAILABLE" in error_str or "unavailable" in error_lower
        is_500_error = "500" in error_str or "INTERNAL_ERROR" in error_str or "internal server error" in error_lower
        
        # Network errors (temporary, can retry)
        is_network_error = (
            "timeout" in error_lower or
            "connection" in error_lower or
            "network" in error_lower or
            "socket" in error_lower or
            "temporary" in error_lower or
            "connection reset" in error_lower
        )
        
        # Handle permanent errors
        if is_401_error:
            print(f"❌ Error creating batch job: 401 UNAUTHENTICATED (authentication failed)")
            print(f"   This is a permanent error. Please check your API key.")
            import traceback
            traceback.print_exc()
            return None
        elif is_403_error:
            print(f"❌ Error creating batch job: 403 PERMISSION_DENIED (access forbidden)")
            print(f"   This is a permanent error. Please check your API key permissions.")
            import traceback
            traceback.print_exc()
            return None
        elif is_400_error:
            print(f"❌ Error creating batch job: 400 INVALID_ARGUMENT (bad request)")
            print(f"   This is a permanent error. Please check your request parameters.")
            import traceback
            traceback.print_exc()
            return None
        
        # Handle temporary errors (raise special exceptions for retry logic)
        elif is_429_error:
            print(f"❌ Error creating batch job: 429 RESOURCE_EXHAUSTED (quota exceeded)")
            print(f"   This is a temporary error. Will retry with different API key.")
            raise ValueError("429_QUOTA_EXHAUSTED") from e
        elif is_404_error:
            print(f"❌ Error creating batch job: 404 NOT_FOUND (file not accessible with current API key)")
            print(f"   This is a temporary error. Will retry with different API key and re-upload file.")
            raise ValueError("404_NOT_FOUND") from e
        elif is_503_error:
            print(f"❌ Error creating batch job: 503 SERVICE_UNAVAILABLE (service temporarily unavailable)")
            print(f"   This is a temporary error. Will retry.")
            raise ValueError("503_SERVICE_UNAVAILABLE") from e
        elif is_500_error:
            print(f"❌ Error creating batch job: 500 INTERNAL_ERROR (internal server error)")
            print(f"   This is a temporary error. Will retry.")
            raise ValueError("500_INTERNAL_ERROR") from e
        elif is_network_error:
            print(f"❌ Error creating batch job: Network error (temporary)")
            print(f"   This is a temporary error. Will retry.")
            raise ValueError("NETWORK_ERROR") from e
        else:
            # Unknown error - treat as potentially temporary
            print(f"❌ Error creating batch job: {e}")
            print(f"   Unknown error type. Will attempt retry.")
            import traceback
            traceback.print_exc()
            raise ValueError("UNKNOWN_ERROR") from e


# =========================
# Batch Status Check
# =========================

def check_batch_status(
    batch_id: str,
    api_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    배치 작업의 현재 상태를 조회합니다 (Batch.md 문서 기반).
    """
    if not GEMINI_AVAILABLE:
        print("❌ Error: google.genai not available")
        return None
    
    try:
        # Load API key
        if api_key is None:
            api_key = os.getenv(GEMINI_API_KEY_ENV, "").strip()
            if not api_key:
                print(f"❌ Error: Missing API key ({GEMINI_API_KEY_ENV})")
                return None
        
        # Create client
        client = genai.Client(api_key=api_key)
        
        # Batch.md 문서 기반: client.batches.get(name=batch_id)
        batch_job = client.batches.get(name=batch_id)
        
        # Extract state
        if hasattr(batch_job, 'state') and batch_job.state is not None:
            state_name = batch_job.state.name if hasattr(batch_job.state, 'name') else str(batch_job.state)
        else:
            state_name = "UNKNOWN"
        
        result = {
            "name": batch_id,
            "state": state_name,
            "display_name": getattr(batch_job, 'display_name', None),
        }
        
        # Add destination file if succeeded
        if state_name == 'JOB_STATE_SUCCEEDED' and hasattr(batch_job, 'dest') and batch_job.dest is not None:
            if hasattr(batch_job.dest, 'file_name') and batch_job.dest.file_name:
                result["dest_file_name"] = batch_job.dest.file_name
        
        # Add error if failed
        if state_name == 'JOB_STATE_FAILED' and hasattr(batch_job, 'error'):
            result["error"] = str(batch_job.error)
        
        return result
        
    except Exception as e:
        error_str = str(e)
        # 404 에러는 조용히 처리 (traceback 없이)
        if "404" in error_str or "NOT_FOUND" in error_str:
            return None
        
        # 400 에러 (API 키 무효)는 경고만 출력 (traceback 없이)
        if "400" in error_str or "INVALID_ARGUMENT" in error_str or "API_KEY_INVALID" in error_str:
            # API 키가 무효한 경우 - 조용히 처리하되 경고만 출력
            return None
        
        # 다른 에러는 출력
        print(f"❌ Error checking batch status: {e}")
        import traceback
        traceback.print_exc()
        return None


def monitor_batch_job(
    batch_id: str,
    poll_interval: int = 60,
    api_key: Optional[str] = None,
) -> Optional[str]:
    """
    배치 작업을 주기적으로 모니터링하여 완료될 때까지 대기합니다.
    """
    print(f"🔍 Monitoring batch job: {batch_id}")
    print(f"   Poll interval: {poll_interval} seconds")
    
    completed_states = set([
        'JOB_STATE_SUCCEEDED',
        'JOB_STATE_FAILED',
        'JOB_STATE_CANCELLED',
        'JOB_STATE_EXPIRED',
    ])
    
    while True:
        status_info = check_batch_status(batch_id, api_key)
        
        if status_info is None:
            print("❌ Failed to check batch status")
            return None
        
        state_name = status_info.get("state", "")
        print(f"   Status: {state_name}")
        
        if state_name in completed_states:
            print(f"\n✅ Batch job finished with state: {state_name}")
            return state_name
        
        # Wait before next check
        time.sleep(poll_interval)


# =========================
# Result Parsing and Image Saving
# =========================

def parse_batch_results(result_file_content: bytes) -> List[Dict[str, Any]]:
    """
    배치 결과 JSONL 파일을 파싱하여 이미지 데이터 추출.
    
    Returns:
        List of dicts with keys: 'key', 'image_data' (base64), 'metadata', 'error'
    """
    # NOTE:
    # - Do NOT do `decode() + splitlines()` for 1GB+ files: it can double memory usage.
    # - We stream JSONL line-by-line with incremental UTF-8 decoding.

    def _iter_batch_results(content: bytes) -> Iterator[Dict[str, Any]]:
        if not content:
            return
            yield  # pragma: no cover (keeps this as a generator for type-checkers)

        # Incremental decode + line iteration (no giant intermediate string/list).
        bio = io.BytesIO(content)
        with io.TextIOWrapper(bio, encoding="utf-8", errors="replace", newline="") as f:
            for line_no, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                try:
                    parsed_response = json.loads(line)
                except json.JSONDecodeError as e:
                    # Keep going (best-effort). Don't log the whole line.
                    print(f"⚠️  Warning: Failed to parse result line {line_no}: {e}")
                    continue

                result_item: Dict[str, Any] = {
                    "key": parsed_response.get("key", ""),
                    "image_data": None,
                    "mime_type": None,
                    "text": None,
                    "error": None,
                }

                if parsed_response.get("response"):
                    response = parsed_response["response"]
                    candidates = response.get("candidates") or []
                    if candidates:
                        candidate = candidates[0] or {}
                        content_obj = candidate.get("content") or {}
                        parts = content_obj.get("parts") or []
                        for part in parts:
                            if not isinstance(part, dict):
                                continue
                            if part.get("text"):
                                result_item["text"] = part["text"]
                            inline = part.get("inlineData")
                            if inline and isinstance(inline, dict):
                                # NOTE: For Gemini image batches, the image bytes are base64-encoded here.
                                result_item["image_data"] = inline.get("data")
                                result_item["mime_type"] = inline.get("mimeType", "image/png")
                elif parsed_response.get("error"):
                    result_item["error"] = parsed_response["error"]

                yield result_item

    try:
        return list(_iter_batch_results(result_file_content))
    except Exception as e:
        print(f"❌ Error parsing batch results: {e}")
        import traceback
        traceback.print_exc()
        return []


# =========================
# Result Key Helpers
# =========================

_REQUEST_KEY_RE = re.compile(r"^request[-_](\d+)$")


def parse_request_index(key: str) -> Optional[int]:
    """
    Parse Gemini Batch result 'key' into a chunk-local integer index.

    Supports:
      - request_123
      - request-123
      - zero-padded variants (e.g. request_000123, request-000123)

    Returns:
      int index if parsed, else None.
    """
    if not key:
        return None
    m = _REQUEST_KEY_RE.match(str(key).strip())
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def download_batch_results(
    result_file_name: str,
    api_key: Optional[str] = None,
) -> Optional[bytes]:
    """
    배치 결과 파일을 다운로드합니다.
    """
    thread_id = threading.current_thread().ident
    batch_short_id = result_file_name.split("/")[-1][:20] + "..." if "/" in result_file_name else result_file_name[:20] + "..."
    start_time = time.time()
    
    if not GEMINI_AVAILABLE:
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] ❌ Error: google.genai not available")
        return None
    
    try:
        # Load API key
        if api_key is None:
            api_key = os.getenv(GEMINI_API_KEY_ENV, "").strip()
            if not api_key:
                timestamp = datetime.now().isoformat()
                print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] ❌ Error: Missing API key ({GEMINI_API_KEY_ENV})")
                return None
        
        # Mask API key for logging
        masked_api_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] Starting download for file: {result_file_name}, API key: {masked_api_key}")
        
        # Create client with diagnostic logging
        client_start_time = time.time()
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] Creating genai.Client instance (before instantiation)...")
        try:
            client = genai.Client(api_key=api_key)
            client_elapsed = (time.time() - client_start_time) * 1000
            timestamp = datetime.now().isoformat()
            if client_elapsed > 5000:  # Warn if client creation takes longer than 5 seconds
                print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] ⚠️  Client created ({client_elapsed:.0f}ms) - SLOW (may indicate blocking)")
            else:
                print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] Client created successfully ({client_elapsed:.0f}ms)")
        except Exception as client_error:
            client_elapsed = (time.time() - client_start_time) * 1000
            timestamp = datetime.now().isoformat()
            print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] ❌ Exception during client creation after {client_elapsed:.0f}ms: {type(client_error).__name__}: {client_error}")
            raise  # Re-raise to be caught by outer exception handler
        
        # Download file with progress indication
        download_start_time = time.time()
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] Preparing to call client.files.download()...")
        print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}]   File: {result_file_name}")
        print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}]   Client type: {type(client)}")
        print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}]   Client has 'files' attribute: {hasattr(client, 'files')}")
        
        # Note: File size cannot be known before download (API limitation)
        # The result file contains base64-encoded images, so size depends on:
        # - Number of images in the batch
        # - Image resolution (2K vs 4K)
        # - Image content complexity
        # Typical sizes: 50-200MB for 2K images, 200MB-2GB+ for 4K images
        
        # Check if files attribute exists and is callable
        if not hasattr(client, 'files'):
            raise AttributeError("Client does not have 'files' attribute")
        if not hasattr(client.files, 'download'):
            raise AttributeError("Client.files does not have 'download' method")
        
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] ✅ Client verified, calling client.files.download() NOW...")
        
        # Start a progress indicator thread for long downloads
        progress_stop_event = threading.Event()
        download_started = threading.Event()
        
        def progress_indicator():
            """Print progress updates every 15 seconds during download"""
            # Wait for download to actually start (give it 1 second)
            if not download_started.wait(1.0):
                timestamp = datetime.now().isoformat()
                print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] ⚠️  WARNING: Download call may be blocking (no response after 1s)")
            
            elapsed = 0
            while not progress_stop_event.is_set():
                progress_stop_event.wait(15)  # Wait 15 seconds
                if progress_stop_event.is_set():
                    break
                elapsed += 15
                timestamp = datetime.now().isoformat()
                print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] ⏳ Download in progress... ({elapsed}s elapsed)")
        
        progress_thread = threading.Thread(target=progress_indicator, daemon=True)
        progress_thread.start()
        
        try:
            # Mark that we're about to call the download
            call_start_time = time.time()
            timestamp = datetime.now().isoformat()
            print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] 🚀 EXECUTING: client.files.download(file='{result_file_name}')")
            
            # Actually call the download
            file_content_bytes = client.files.download(file=result_file_name)
            
            # Mark that download call returned
            call_elapsed = time.time() - call_start_time
            download_started.set()  # Signal that download started/returned
            timestamp = datetime.now().isoformat()
            print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] ✅ client.files.download() RETURNED (call took {call_elapsed:.3f}s)")
        except Exception as download_error:
            download_started.set()  # Signal that we got an error (not blocking)
            timestamp = datetime.now().isoformat()
            print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] ❌ EXCEPTION in client.files.download(): {type(download_error).__name__}: {download_error}")
            raise  # Re-raise to be handled by outer exception handler
        finally:
            progress_stop_event.set()  # Stop progress indicator
        
        download_elapsed = time.time() - download_start_time
        total_elapsed = time.time() - start_time
        file_size = len(file_content_bytes) if file_content_bytes else 0
        file_size_mb = file_size / (1024 * 1024)
        download_speed_mbps = (file_size_mb / download_elapsed) if download_elapsed > 0 else 0
        
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] ✅ Download completed")
        print(f"   File size: {file_size_mb:.2f} MB")
        print(f"   Download time: {download_elapsed:.1f}s ({download_elapsed*1000:.0f}ms)")
        print(f"   Download speed: {download_speed_mbps:.2f} MB/s")
        print(f"   Total time: {total_elapsed:.1f}s ({total_elapsed*1000:.0f}ms)")
        
        return file_content_bytes
        
    except Exception as e:
        error_str = str(e)
        total_elapsed = (time.time() - start_time) * 1000
        timestamp = datetime.now().isoformat()
        
        # 404, 400 (API 키 무효) 에러는 조용히 처리 (traceback 없이)
        if "404" in error_str or "NOT_FOUND" in error_str:
            print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] File not found (404) after {total_elapsed:.0f}ms")
            return None
        if "400" in error_str or "INVALID_ARGUMENT" in error_str or "API_KEY_INVALID" in error_str:
            print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] Invalid API key or argument (400) after {total_elapsed:.0f}ms")
            return None
        
        # 다른 에러는 출력
        print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] ❌ Error downloading result file after {total_elapsed:.0f}ms: {e}")
        import traceback
        traceback.print_exc()
        return None


def download_result_file_for_batch(
    batch_info: Dict[str, Any],
    rotator: Optional[Any],
) -> Optional[List[Dict[str, Any]]]:
    """
    단일 배치의 결과 파일을 다운로드하고 파싱합니다.
    404 에러가 발생하면 모든 API 키를 시도합니다.
    
    Args:
        batch_info: 배치 정보 딕셔너리 (batch_id, chunk, dest_file_name 포함)
        rotator: API 키 rotator
        
    Returns:
        파싱된 batch_results 리스트, 실패 시 None
    """
    dest_file_name = batch_info.get("dest_file_name")
    if not dest_file_name:
        return None
    
    chunk = batch_info.get("chunk", {})
    download_api_key_number = chunk.get("api_key_number")
    batch_id = batch_info.get("batch_id", "unknown")
    batch_short_id = batch_id.split("/")[-1][:20] + "..." if batch_id and "/" in batch_id else batch_id[:20] + "..." if batch_id else "unknown"
    
    # Estimate file size based on batch info
    num_requests = chunk.get("num_requests", 0)
    prompts_metadata = batch_info.get("prompts_metadata", [])
    if not num_requests and prompts_metadata:
        num_requests = len(prompts_metadata)
    
    # Estimate size: 2K images ~2-5MB each, 4K images ~5-15MB each (base64 encoded)
    # Check if batch has 4K images (S1_TABLE_VISUAL)
    has_4k = any(
        str(meta.get("spec_kind", "")).strip() == "S1_TABLE_VISUAL"
        for meta in prompts_metadata
    )
    avg_size_per_image_mb = 8.0 if has_4k else 3.5  # 4K: ~8MB, 2K: ~3.5MB (base64 encoded)
    estimated_size_mb = num_requests * avg_size_per_image_mb if num_requests > 0 else None
    
    # 배치를 생성한 API 키로 먼저 시도
    download_key = None
    if download_api_key_number and rotator is not None:
        try:
            if download_api_key_number in rotator.key_numbers:
                target_index = rotator.key_numbers.index(download_api_key_number)
                download_key = rotator.keys[target_index]
        except (ValueError, IndexError):
            pass
    
    # Fallback: 현재 사용 중인 키 사용
    if not download_key and rotator is not None:
        download_key = rotator.get_current_key()
    
    if not download_key:
        return None
    
    # Show estimated file size before downloading
    if estimated_size_mb is not None:
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] [Thread-{threading.current_thread().ident}] [batch_{batch_short_id}] 📊 Estimated file size: ~{estimated_size_mb:.1f} MB ({num_requests} images, {'4K' if has_4k else '2K'})")
        estimated_time_sec = estimated_size_mb / 9.0  # Assume ~9 MB/s download speed
        print(f"[{timestamp}] [Thread-{threading.current_thread().ident}] [batch_{batch_short_id}]   Estimated download time: ~{estimated_time_sec:.0f}s")
    
    # 먼저 배치를 생성한 API 키로 시도
    try:
        result_file_bytes = download_batch_results(dest_file_name, api_key=download_key)
        if result_file_bytes:
            batch_results = parse_batch_results(result_file_bytes)
            return batch_results
    except Exception as e:
        error_str = str(e)
        # 404 에러가 아니면 그냥 실패 (타임아웃, 네트워크 에러 등)
        if "404" not in error_str and "NOT_FOUND" not in error_str:
            # 타임아웃이나 네트워크 에러는 출력
            if "timeout" in error_str.lower() or "timed out" in error_str.lower():
                print(f"   ⚠️  Timeout downloading result file for batch {batch_short_id}")
            elif "Connection" in error_str or "network" in error_str.lower():
                print(f"   ⚠️  Network error downloading result file for batch {batch_short_id}: {error_str[:100]}")
            # 다른 에러는 조용히 처리 (이미 download_batch_results에서 출력함)
            return None
    
    # 404 에러가 발생했거나 결과가 없으면 모든 API 키를 시도
    if rotator is not None and len(rotator.keys) > 1:
        # 이미 시도한 키는 제외하고 나머지 키들 시도
        tried_key = download_key
        for key_idx, test_key in enumerate(rotator.keys):
            if test_key == tried_key:
                continue  # 이미 시도한 키는 스킵
            
            try:
                result_file_bytes = download_batch_results(dest_file_name, api_key=test_key)
                if result_file_bytes:
                    # 올바른 키를 찾았음
                    actual_key_number = rotator.key_numbers[key_idx]
                    print(f"   ✅ Found result file with GOOGLE_API_KEY_{actual_key_number} (original key was {download_api_key_number if download_api_key_number else 'unknown'})")
                    batch_results = parse_batch_results(result_file_bytes)
                    return batch_results
            except Exception as e:
                error_str = str(e)
                # 404, 400 (API 키 무효) 에러는 조용히 다음 키 시도
                if "404" in error_str or "NOT_FOUND" in error_str or "400" in error_str or "INVALID_ARGUMENT" in error_str or "API_KEY_INVALID" in error_str:
                    continue  # Try next key silently
                else:
                    # 다른 에러는 조용히 처리 (이미 download_batch_results에서 출력함)
                    continue
    
    return None


def download_result_files_parallel(
    batches_to_check: List[Dict[str, Any]],
    rotator: Optional[Any],
    max_workers: int = 10,
) -> Dict[str, Optional[List[Dict[str, Any]]]]:
    """
    배치 결과 파일들을 병렬로 다운로드합니다.
    
    Args:
        batches_to_check: 결과 파일 다운로드가 필요한 배치 정보 리스트
        rotator: API 키 rotator
        max_workers: 최대 병렬 워커 수
        
    Returns:
        {batch_id: batch_results} 딕셔너리
    """
    if not batches_to_check:
        return {}
    
    results = {}
    task_start_times = {}  # Track when each task started
    heartbeat_interval = 30  # Heartbeat logging interval in seconds
    
    def download_single_result(batch_info: Dict[str, Any]) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
        """단일 배치의 결과 파일을 다운로드합니다."""
        thread_id = threading.current_thread().ident
        batch_id = batch_info.get("batch_id", "unknown")
        batch_short_id = batch_id.split("/")[-1][:20] + "..." if batch_id and "/" in batch_id else batch_id[:20] + "..." if batch_id else "unknown"
        task_start_time = time.time()
        task_start_times[batch_id] = task_start_time
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] Task started executing")
        
        batch_results = download_result_file_for_batch(batch_info, rotator)
        
        task_elapsed = (time.time() - task_start_time) * 1000
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] [Thread-{thread_id}] [batch_{batch_short_id}] Task completed ({task_elapsed:.0f}ms)")
        return batch_id, batch_results
    
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] 🚀 Starting parallel download of {len(batches_to_check)} result file(s) with {max_workers} worker(s)...")
    
    # Use ThreadPoolExecutor for parallel downloads
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all download tasks with logging
        future_to_batch = {}
        for idx, batch_info in enumerate(batches_to_check, 1):
            batch_id = batch_info.get("batch_id", "unknown")
            batch_short_id = batch_id.split("/")[-1][:20] + "..." if batch_id and "/" in batch_id else batch_id[:20] + "..." if batch_id else "unknown"
            future = executor.submit(download_single_result, batch_info)
            future_to_batch[future] = batch_info
            timestamp = datetime.now().isoformat()
            print(f"[{timestamp}] [Main] Task [{idx}/{len(batches_to_check)}] submitted for batch {batch_short_id}")
        
        # Start heartbeat monitoring thread
        heartbeat_stop_event = threading.Event()
        all_futures = list(future_to_batch.keys())
        
        def heartbeat_logger():
            """Periodically log thread pool state and progress."""
            while not heartbeat_stop_event.is_set():
                heartbeat_stop_event.wait(heartbeat_interval)
                if heartbeat_stop_event.is_set():
                    break
                
                # Count completed, running, and pending
                completed = sum(1 for f in all_futures if f.done())
                running = sum(1 for f in all_futures if f.running())
                pending = len(all_futures) - completed
                
                # Find long-running tasks
                now = time.time()
                long_running = []
                for future in all_futures:
                    if not future.done():
                        batch_info = future_to_batch[future]
                        batch_id = batch_info.get("batch_id", "unknown")
                        if batch_id in task_start_times:
                            elapsed = now - task_start_times[batch_id]
                            if elapsed > heartbeat_interval:
                                batch_short_id = batch_id.split("/")[-1][:20] + "..." if batch_id and "/" in batch_id else batch_id[:20] + "..." if batch_id else "unknown"
                                long_running.append((batch_short_id, elapsed))
                
                timestamp = datetime.now().isoformat()
                print(f"[{timestamp}] [Heartbeat] Progress: {completed}/{len(all_futures)} completed, {running} running, {pending} pending")
                if long_running:
                    long_running_str = ", ".join([f"{bid} ({elapsed:.0f}s)" for bid, elapsed in long_running[:5]])
                    print(f"[{timestamp}] [Heartbeat] Long-running tasks: {long_running_str}")
        
        heartbeat_thread = threading.Thread(target=heartbeat_logger, daemon=True)
        heartbeat_thread.start()
        
        # Process completed downloads (no timeout)
        completed_count = 0
        overall_start_time = time.time()
        
        try:
            for future in as_completed(future_to_batch):
                batch_info = future_to_batch[future]
                batch_id = batch_info.get("batch_id", "unknown")
                batch_short_id = batch_id.split("/")[-1][:20] + "..." if batch_id and "/" in batch_id else batch_id[:20] + "..." if batch_id else "N/A"
                
                # Calculate elapsed time for this task
                task_elapsed = 0
                if batch_id in task_start_times:
                    task_elapsed = (time.time() - task_start_times[batch_id]) * 1000
                
                try:
                    # No timeout - wait indefinitely for results
                    batch_id, batch_results = future.result()
                    results[batch_id] = batch_results
                    completed_count += 1
                    
                    # Calculate remaining tasks
                    remaining = len(batches_to_check) - completed_count
                    running = sum(1 for f in all_futures if f.running() and not f.done())
                    pending = sum(1 for f in all_futures if not f.done())
                    
                    timestamp = datetime.now().isoformat()
                    overall_elapsed = time.time() - overall_start_time
                    
                    if batch_results is None:
                        print(f"[{timestamp}] [Main] ⚠️  Failed to download result file for batch: {batch_short_id} (task: {task_elapsed:.0f}ms, overall: {overall_elapsed:.1f}s, remaining: {remaining}, running: {running}, pending: {pending})")
                    else:
                        print(f"[{timestamp}] [Main] ✅ Downloaded result file [{completed_count}/{len(batches_to_check)}] for batch {batch_short_id} (task: {task_elapsed:.0f}ms, overall: {overall_elapsed:.1f}s, remaining: {remaining}, running: {running}, pending: {pending})")
                except Exception as e:
                    results[batch_id] = None
                    completed_count += 1
                    error_str = str(e)
                    
                    remaining = len(batches_to_check) - completed_count
                    running = sum(1 for f in all_futures if f.running() and not f.done())
                    pending = sum(1 for f in all_futures if not f.done())
                    timestamp = datetime.now().isoformat()
                    overall_elapsed = time.time() - overall_start_time
                    
                    # Network errors and other exceptions
                    if "Connection" in error_str or "network" in error_str.lower():
                        print(f"[{timestamp}] [Main] ❌ Network error downloading result file for batch {batch_short_id}: {error_str[:200]} (task: {task_elapsed:.0f}ms, overall: {overall_elapsed:.1f}s, remaining: {remaining}, running: {running}, pending: {pending})")
                    else:
                        print(f"[{timestamp}] [Main] ❌ Exception while downloading result file for batch {batch_short_id}: {error_str[:200]} (task: {task_elapsed:.0f}ms, overall: {overall_elapsed:.1f}s, remaining: {remaining}, running: {running}, pending: {pending})")
        finally:
            # Stop heartbeat logging
            heartbeat_stop_event.set()
    
    timestamp = datetime.now().isoformat()
    overall_elapsed = time.time() - overall_start_time
    succeeded = len([r for r in results.values() if r is not None])
    failed = len([r for r in results.values() if r is None])
    print(f"[{timestamp}] [Main] 📊 Result file download summary: {succeeded} succeeded, {failed} failed (total time: {overall_elapsed:.1f}s)")
    return results


def make_image_filename(
    run_tag: str,
    group_id: str,
    entity_id: Optional[str] = None,
    card_role: Optional[str] = None,
    spec_kind: Optional[str] = None,
    cluster_id: Optional[str] = None,
    suffix: str = "",
) -> str:
    """
    S4와 동일한 파일명 규칙을 사용합니다.
    
    For S1_TABLE_VISUAL:
    - Without cluster_id: IMG__{run_tag}__{group_id}__TABLE{suffix}.jpg
    - With cluster_id: IMG__{run_tag}__{group_id}__TABLE__{cluster_id}{suffix}.jpg
    
    For S2_CARD_IMAGE:
    - IMG__{run_tag}__{group_id}__{entity_id}__{card_role}{suffix}.jpg
    
    Args:
        suffix: Optional suffix to add before extension (e.g., '_realistic', '_regen')
    """
    def sanitize(s: str) -> str:
        invalid = '<>:"/\\|?*'
        for c in invalid:
            s = s.replace(c, '_')
        return s.strip()
    
    run_tag_safe = sanitize(str(run_tag))
    group_id_safe = sanitize(str(group_id))
    
    spec_kind = str(spec_kind or "").strip()
    if spec_kind == "S1_TABLE_VISUAL":
        if cluster_id:
            cluster_id_safe = sanitize(str(cluster_id))
            base = f"IMG__{run_tag_safe}__{group_id_safe}__TABLE__{cluster_id_safe}"
        else:
            base = f"IMG__{run_tag_safe}__{group_id_safe}__TABLE"
    else:
        entity_id_safe = sanitize(str(entity_id or ""))
        card_role_safe = sanitize(str(card_role or "").upper())
        base = f"IMG__{run_tag_safe}__{group_id_safe}__{entity_id_safe}__{card_role_safe}"
    
    return f"{base}{suffix}.jpg"


def create_entity_key(prompt: Dict[str, Any], run_tag: str = "") -> Tuple[str, str, str, str, str, str]:
    """
    프롬프트에서 entity_key를 생성합니다 (중복 체크용).
    
    모든 필드를 str로 변환하고 공백을 제거하여 정규화합니다.
    
    Args:
        prompt: 프롬프트 데이터 (run_tag, group_id, entity_id, card_role, spec_kind 포함)
        run_tag: 기본 run_tag (prompt에 없을 경우 사용)
        
    Returns:
        (run_tag, group_id, entity_id, card_role, spec_kind, cluster_id) tuple
        
        NOTE:
        - For S1_TABLE_VISUAL, cluster_id must be included to avoid treating different clusters as duplicates.
        - For non-table specs, cluster_id is forced to "" to avoid accidental dedupe differences.
    """
    def normalize(value: Any) -> str:
        """값을 str로 변환하고 공백을 제거합니다."""
        return str(value or "").strip()
    
    spec_kind = normalize(prompt.get("spec_kind", ""))
    cluster_id = normalize(prompt.get("cluster_id", "")) if spec_kind == "S1_TABLE_VISUAL" else ""
    
    return (
        normalize(prompt.get("run_tag", run_tag)),
        normalize(prompt.get("group_id", "")),
        normalize(prompt.get("entity_id", "")),
        normalize(prompt.get("card_role", "")),
        spec_kind,
        cluster_id,
    )


def verify_prompts_metadata_format(prompts_metadata: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """
    prompts_metadata 형식이 올바른지 검증합니다.
    
    Args:
        prompts_metadata: 검증할 prompts_metadata 리스트
        
    Returns:
        (is_valid: bool, error_message: Optional[str])
    """
    if not isinstance(prompts_metadata, list):
        return False, "prompts_metadata must be a list"
    
    required_fields = {"prompt_hash", "run_tag", "group_id", "entity_id", "card_role", "spec_kind"}
    
    for idx, meta in enumerate(prompts_metadata):
        if not isinstance(meta, dict):
            return False, f"prompts_metadata[{idx}] must be a dict"
        
        # Check required fields
        missing_fields = required_fields - set(meta.keys())
        if missing_fields:
            return False, f"prompts_metadata[{idx}] missing required fields: {missing_fields}"
        
        # Verify all fields are strings (not None)
        for field in required_fields:
            value = meta.get(field)
            if value is None:
                return False, f"prompts_metadata[{idx}].{field} is None (should be normalized to empty string)"
            if not isinstance(value, str):
                return False, f"prompts_metadata[{idx}].{field} is not a string: {type(value).__name__}"
    
    return True, None


def check_if_prompt_submitted(
    prompt: Dict[str, Any],
    tracking_data: Dict[str, Any],
    base_dir: Path,
) -> bool:
    """
    프롬프트가 이미 배치로 제출되었는지 확인합니다.
    
    Args:
        prompt: 프롬프트 데이터 (run_tag, group_id, entity_id, card_role, spec_kind 포함)
        tracking_data: 배치 트래킹 데이터
        base_dir: 기본 디렉토리 (현재는 사용하지 않지만 호환성을 위해 유지)
        
    Returns:
        True if already submitted, False otherwise
    """
    prompt_run_tag = str(prompt.get("run_tag", "")).strip()
    prompt_key = create_entity_key(prompt, prompt_run_tag)
    
    # Check all batches in tracking data, but only those with matching run_tag
    for api_key_str, api_batches in tracking_data.get("batches", {}).items():
        batch_run_tag = str(api_batches.get("run_tag", "")).strip()
        # Only check batches with the same run_tag
        if batch_run_tag != prompt_run_tag:
            continue
            
        for chunk in api_batches.get("chunks", []):
            chunk_status = chunk.get("status", "")
            # Only check pending/running/succeeded batches (not failed/cancelled)
            if chunk_status in ("JOB_STATE_PENDING", "JOB_STATE_RUNNING", "JOB_STATE_SUCCEEDED"):
                chunk_metadata = chunk.get("prompts_metadata", [])
                for meta in chunk_metadata:
                    meta_key = create_entity_key(meta, meta.get("run_tag", ""))
                    if meta_key == prompt_key:
                        return True
    
    return False


def check_if_image_exists_locally(
    prompt: Dict[str, Any],
    images_dir: Path,
    run_tag: str,
) -> bool:
    """
    로컬에 이미지 파일이 존재하는지 확인합니다.
    
    Args:
        prompt: 프롬프트 데이터
        images_dir: 이미지 디렉토리 경로
        run_tag: 실행 태그
        
    Returns:
        True if image exists, False otherwise
    """
    if not images_dir.exists():
        return False
    
    filename = make_image_filename(
        run_tag=prompt.get("run_tag", run_tag),
        group_id=prompt.get("group_id", ""),
        entity_id=prompt.get("entity_id"),
        card_role=prompt.get("card_role"),
        spec_kind=prompt.get("spec_kind"),
        cluster_id=prompt.get("cluster_id"),
        suffix=_global_filename_suffix,
    )
    image_path = images_dir / filename
    return image_path.exists()


def filter_duplicate_prompts(
    prompts_data: List[Dict[str, Any]],
    tracking_data: Dict[str, Any],
    images_dir: Path,
    run_tag: str,
    base_dir: Path,
) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    프롬프트 리스트에서 중복 제거 (이미 제출된 배치 및 로컬 이미지).
    
    Args:
        prompts_data: 프롬프트 데이터 리스트
        tracking_data: 배치 트래킹 데이터
        images_dir: 이미지 디렉토리 경로
        run_tag: 실행 태그
        base_dir: 기본 디렉토리
        
    Returns:
        (filtered_prompts, already_submitted_count, already_exist_locally_count)
    """
    filtered_prompts = []
    already_submitted_count = 0
    already_exist_locally_count = 0
    
    for prompt in prompts_data:
        # Check if already submitted
        is_submitted = check_if_prompt_submitted(prompt, tracking_data, base_dir)
        
        # Check if image exists locally
        image_exists = check_if_image_exists_locally(prompt, images_dir, run_tag)
        
        if is_submitted:
            already_submitted_count += 1
        elif image_exists:
            already_exist_locally_count += 1
        else:
            filtered_prompts.append(prompt)
    
    return filtered_prompts, already_submitted_count, already_exist_locally_count


def check_batch_images_exist(
    prompts_metadata: List[Dict[str, Any]],
    images_dir: Path,
    run_tag: str,
    batch_results: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[bool, int, int]:
    """
    배치의 모든 이미지가 이미 존재하는지 확인합니다.
    
    Args:
        prompts_metadata: 배치의 프롬프트 메타데이터 목록
        images_dir: 이미지 디렉토리 경로
        run_tag: 실행 태그
        batch_results: 배치의 실제 결과 파일 내용 (선택적, 제공되면 실제 생성된 이미지만 확인)
    
    Returns:
        (all_exist: bool, total_count: int, existing_count: int)
    """
    # 디렉토리가 없으면 이미지도 없음
    if not images_dir.exists():
        return False, len(prompts_metadata), 0
    
    # 디렉토리가 존재하지만 비어있으면 이미지도 없음
    # (디렉토리만 존재하고 파일이 없는 경우를 명시적으로 확인)
    try:
        if not any(images_dir.iterdir()):
            # 디렉토리가 비어있음
            return False, len(prompts_metadata), 0
    except (OSError, PermissionError):
        # 디렉토리 접근 불가
        return False, len(prompts_metadata), 0
    
    # 배치 결과 파일이 제공된 경우, 실제로 생성된 이미지만 확인
    if batch_results is not None:
        # 결과 파일에서 실제로 생성된 이미지의 key와 메타데이터 매핑
        # batch_results의 인덱스가 prompts_metadata의 인덱스와 일치한다고 가정
        existing_count = 0
        actual_image_count = 0
        
        for idx, result in enumerate(batch_results):
            key = result.get("key", "")
            has_image = bool(result.get("image_data"))
            
            if has_image:
                actual_image_count += 1
                
                # prompts_metadata에서 해당 인덱스의 메타데이터 가져오기
                if idx < len(prompts_metadata):
                    meta = prompts_metadata[idx]
                    filename = make_image_filename(
                        run_tag=meta.get("run_tag", run_tag),
                        group_id=meta.get("group_id", ""),
                        entity_id=meta.get("entity_id"),
                        card_role=meta.get("card_role"),
                        spec_kind=meta.get("spec_kind"),
                        cluster_id=meta.get("cluster_id"),
                        suffix=_global_filename_suffix,
                    )
                    image_path = images_dir / filename
                    if image_path.exists():
                        existing_count += 1
        
        total_count = actual_image_count  # 실제로 생성된 이미지 수
        all_exist = existing_count == total_count and total_count > 0
        return all_exist, total_count, existing_count
    
    # 배치 결과 파일이 없는 경우, prompts_metadata 기반으로 확인 (기존 로직)
    existing_count = 0
    for meta in prompts_metadata:
        filename = make_image_filename(
            run_tag=meta.get("run_tag", run_tag),
            group_id=meta.get("group_id", ""),
            entity_id=meta.get("entity_id"),
            card_role=meta.get("card_role"),
            spec_kind=meta.get("spec_kind"),
            cluster_id=meta.get("cluster_id"),
            suffix=_global_filename_suffix,
        )
        image_path = images_dir / filename
        if image_path.exists():
            existing_count += 1
    
    total_count = len(prompts_metadata)
    all_exist = existing_count == total_count and total_count > 0
    
    return all_exist, total_count, existing_count


def download_batches_parallel(
    batches_to_download: List[Dict[str, Any]],
    base_dir: Path,
    rotator: Optional[Any],
    batch_tracking_path: Path,
    tracking_data: Dict[str, Any],
    max_workers: int = 5,
) -> Tuple[int, int]:
    """
    배치들을 병렬로 다운로드합니다.
    
    Args:
        batches_to_download: 다운로드할 배치 정보 리스트 (batch_info 딕셔너리)
        base_dir: 기본 디렉토리
        rotator: API 키 rotator
        batch_tracking_path: 배치 트래킹 파일 경로
        tracking_data: 배치 트래킹 데이터 (업데이트용)
        max_workers: 최대 병렬 워커 수
        
    Returns:
        (성공 개수, 실패 개수)
    """
    if not batches_to_download:
        return 0, 0
    
    success_count = 0
    fail_count = 0
    
    # Get default API key
    api_key = None
    if rotator is not None:
        api_key = rotator.get_current_key()
    else:
        api_key = os.getenv(GEMINI_API_KEY_ENV, "").strip()
    
    def download_single_batch(batch_info: Dict[str, Any]) -> Tuple[bool, str]:
        """
        단일 배치를 다운로드합니다.
        
        Returns:
            (성공 여부, 배치 ID 또는 에러 메시지)
        """
        try:
            result = download_and_save_batch_images(
                batch_info=batch_info,
                base_dir=base_dir,
                api_key=api_key,
                rotator=rotator,
                batch_tracking_path=batch_tracking_path,
                tracking_data=tracking_data,
            )
            batch_id = batch_info.get("batch_id", "unknown")
            return result, batch_id
        except Exception as e:
            batch_id = batch_info.get("batch_id", "unknown")
            error_msg = f"{batch_id}: {str(e)}"
            return False, error_msg
    
    print(f"\n🚀 Starting parallel download of {len(batches_to_download)} batch(es) with {max_workers} worker(s)...")
    
    # Use ThreadPoolExecutor for parallel downloads
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all download tasks
        future_to_batch = {
            executor.submit(download_single_batch, batch_info): batch_info
            for batch_info in batches_to_download
        }
        
        # Process completed downloads
        for future in as_completed(future_to_batch):
            batch_info = future_to_batch[future]
            try:
                success, batch_id_or_error = future.result()
                if success:
                    success_count += 1
                else:
                    fail_count += 1
                    print(f"❌ Failed to download batch: {batch_id_or_error}")
            except Exception as e:
                fail_count += 1
                batch_id = batch_info.get("batch_id", "unknown")
                print(f"❌ Exception while downloading batch {batch_id}: {e}")
    
    print(f"\n📊 Download summary: {success_count} succeeded, {fail_count} failed")
    return success_count, fail_count


def download_and_save_batch_images(
    batch_info: Dict[str, Any],
    base_dir: Path,
    api_key: str,
    rotator: Optional[Any],
    batch_tracking_path: Path,
    tracking_data: Dict[str, Any],
) -> bool:
    """
    배치 결과를 다운로드하고 이미지를 저장합니다.
    
    Returns:
        True if download was successful, False otherwise
    """
    batch_id = batch_info["batch_id"]
    run_tag = batch_info["run_tag"]
    dest_file_name = batch_info["dest_file_name"]
    prompts_metadata = batch_info.get("prompts_metadata", [])
    batch_results = batch_info.get("batch_results")
    
    # Double-check before downloading
    effective_run_tag = run_tag
    if prompts_metadata and isinstance(prompts_metadata, list):
        first_run_tag = prompts_metadata[0].get("run_tag") if isinstance(prompts_metadata[0], dict) else None
        if first_run_tag and str(first_run_tag).strip():
            effective_run_tag = str(first_run_tag).strip()

    images_dir = resolve_images_dir(base_dir, effective_run_tag, _global_image_type)
    all_exist, total_count, existing_count = check_batch_images_exist(
        prompts_metadata, images_dir, effective_run_tag, batch_results=batch_results
    )
    
    short_id = batch_id.split("/")[-1][:20] + "..." if batch_id and "/" in batch_id else batch_id[:20] + "..." if batch_id else "N/A"
    
    if all_exist:
        print(f"\n⏭️  Skipping batch: {short_id}")
        print(f"   ✅ All {total_count} images already exist (no download needed)")
        return True
    
    if existing_count > 0:
        missing_count = total_count - existing_count
        print(f"\n📥 Downloading results for batch: {short_id}")
        print(f"   📊 Status: {existing_count}/{total_count} images already exist, {missing_count} missing")
        print(f"   ⬇️  Will download result file to extract missing images")
    else:
        print(f"\n📥 Downloading results for batch: {short_id}")
        print(f"   📊 Status: 0/{total_count} images exist, all {total_count} need to be downloaded")
    
    # Use the same API key that was used to create this batch
    download_api_key_number = batch_info["chunk"].get("api_key_number")
    download_key = None
    
    if download_api_key_number and rotator is not None:
        try:
            if download_api_key_number in rotator.key_numbers:
                target_index = rotator.key_numbers.index(download_api_key_number)
                download_key = rotator.keys[target_index]
                print(f"   Using GOOGLE_API_KEY_{download_api_key_number} for download")
        except (ValueError, IndexError):
            pass
    
    if not download_key:
        download_key = api_key
    
    result_content = None
    if batch_results:
        result_content = batch_results
    else:
        try:
            result_content = download_batch_results(dest_file_name, api_key=download_key)
        except Exception as e:
            error_str = str(e)
            if (("404" in error_str or "NOT_FOUND" in error_str or "400" in error_str or "INVALID_ARGUMENT" in error_str or "API_KEY_INVALID" in error_str) and rotator is not None):
                print(f"   Trying all API keys to find the correct one for download...")
                for key_idx, test_key in enumerate(rotator.keys):
                    try:
                        test_result = download_batch_results(dest_file_name, api_key=test_key)
                        if test_result:
                            actual_key_number = rotator.key_numbers[key_idx]
                            batch_info["chunk"]["api_key_number"] = actual_key_number
                            save_batch_tracking_file(batch_tracking_path, tracking_data)
                            print(f"   ✅ Found batch with GOOGLE_API_KEY_{actual_key_number}")
                            result_content = test_result
                            break
                    except Exception as test_e:
                        test_error_str = str(test_e)
                        if "404" in test_error_str or "NOT_FOUND" in test_error_str or "400" in test_error_str or "INVALID_ARGUMENT" in test_error_str or "API_KEY_INVALID" in test_error_str:
                            continue
                        else:
                            print(f"   ⚠️  Error with GOOGLE_API_KEY_{rotator.key_numbers[key_idx]}: {test_error_str}")
                            continue
            else:
                raise
    
    if not result_content:
        print(f"   ❌ Failed to download results")
        return False
    
    # Parse results
    if isinstance(result_content, list):
        results = result_content
        print(f"   Using already parsed {len(results)} results")
    else:
        results = parse_batch_results(result_content)
        print(f"   Parsed {len(results)} results")
    
    # Debug: Show sample keys from results
    if results:
        sample_keys = [r.get("key", "NO_KEY") for r in results[:5]]
        print(f"   📋 Sample keys from results: {sample_keys}")
        has_image_data = sum(1 for r in results if r.get("image_data"))
        print(f"   📊 Results with image_data: {has_image_data}/{len(results)}")

    # =========================
    # Map results using chunk-local prompts_metadata
    # =========================
    if not prompts_metadata:
        print("   ❌ No prompts_metadata found in batch_info; cannot map results to filenames.")
        return False

    is_valid_meta, meta_err = verify_prompts_metadata_format(prompts_metadata)
    if not is_valid_meta:
        # Keep going (best-effort) because older tracking entries may miss non-critical fields.
        print(f"   ⚠️  Warning: prompts_metadata format validation failed: {meta_err}")

    if effective_run_tag != run_tag:
        print(f"   📁 Using run_tag from prompts_metadata: {effective_run_tag} (batch run_tag: {run_tag})")

    print(f"   🔍 Mapping {len(results)} results to {len(prompts_metadata)} chunk-local metadata entries...")

    mapped_in_range = 0
    skipped_no_key = 0
    skipped_wrong_prefix = 0
    skipped_parse_error = 0
    skipped_out_of_range = 0

    for r in results:
        key = r.get("key", "")
        if not key:
            skipped_no_key += 1
            continue
        if not str(key).startswith("request"):
            skipped_wrong_prefix += 1
            if skipped_wrong_prefix <= 3:
                print(f"   ⚠️  Warning: Key does not start with 'request': {key}")
            continue
        idx = parse_request_index(key)
        if idx is None:
            skipped_parse_error += 1
            if skipped_parse_error <= 3:
                print(f"   ⚠️  Warning: Could not parse key {key} as request index")
            continue

        if 0 <= idx < len(prompts_metadata):
            mapped_in_range += 1
        else:
            skipped_out_of_range += 1
            if skipped_out_of_range <= 3:
                print(f"   ⚠️  Warning: Index {idx} out of range (0..{len(prompts_metadata)-1}) for key {key}")

    print("   📊 Mapping summary (chunk-local):")
    print(f"      ✅ In-range indices: {mapped_in_range}")
    if skipped_no_key:
        print(f"      ⚠️  Skipped (no key): {skipped_no_key}")
    if skipped_wrong_prefix:
        print(f"      ⚠️  Skipped (wrong prefix): {skipped_wrong_prefix}")
    if skipped_parse_error:
        print(f"      ⚠️  Skipped (parse error): {skipped_parse_error}")
    if skipped_out_of_range:
        print(f"      ⚠️  Skipped (index out of range): {skipped_out_of_range}")

    # Diagnostics: make sure intended save location is always obvious before saving
    print("   💾 Starting image save...")
    print(f"   📁 images_dir (resolved): {images_dir}")
    print(f"   📁 Effective run_tag: {effective_run_tag} (batch run_tag: {run_tag})")
    print(f"   📊 Pre-check: {existing_count}/{total_count} images already exist (missing: {total_count - existing_count})")

    # Save images directly using prompts_metadata (submitted order == request index within this chunk)
    saved_images = save_images_from_batch(results, prompts_metadata, images_dir, effective_run_tag, _global_filename_suffix)

    newly_saved = len([img for img in saved_images if not img.get("skipped", False)])
    skipped = len([img for img in saved_images if img.get("skipped", False)])

    print(f"\n✅ Batch download completed: {short_id}")
    print(f"   📁 Images directory: {images_dir}")
    print(f"   📊 Result: {newly_saved} newly saved, {skipped} skipped (already exist)")
    print(f"   📁 Effective run_tag: {effective_run_tag}")
    if newly_saved > 0:
        sample_new = [img.get("filename") for img in saved_images if not img.get("skipped", False) and img.get("filename")][:3]
        if sample_new:
            print(f"   🧾 Sample newly saved: {sample_new}")
    if skipped > 0:
        sample_skipped = [img.get("filename") for img in saved_images if img.get("skipped", False) and img.get("filename")][:3]
        if sample_skipped:
            print(f"   🧾 Sample skipped: {sample_skipped}")

    # If we didn't save or skip anything, treat as failure to surface mapping bugs quickly.
    if newly_saved == 0 and skipped == 0:
        print("   ⚠️  WARNING: 0 images saved/skipped. This usually indicates key↔metadata mapping mismatch or missing image_data.")
        return False

    return True


def save_images_from_batch(
    results: List[Dict[str, Any]],
    prompts_metadata: List[Dict[str, Any]],
    images_dir: Path,
    run_tag: str,
    filename_suffix: str = "",
) -> List[Dict[str, Any]]:
    """
    배치 결과에서 이미지를 추출하여 저장합니다.
    
    Args:
        results: 배치 결과 리스트
        prompts_metadata: 프롬프트 메타데이터 리스트
        images_dir: 이미지 저장 디렉토리
        run_tag: 실행 태그
        filename_suffix: 파일명 suffix (예: '_realistic', '_regen')
    
    Returns:
        저장된 이미지 정보 리스트 (manifest용)
    """
    saved_images = []
    saved_count = 0
    skipped_count = 0
    error_count = 0

    # Diagnostics: always log intended save target + workload before writing anything
    print("\n💾 Saving images from batch results...")
    print(f"   📁 images_dir: {images_dir}")
    print(f"   🏷️  run_tag: {run_tag}")
    if filename_suffix:
        print(f"   📝 filename_suffix: {filename_suffix}")
    print(f"   📥 results: {len(results)}")
    print(f"   📋 prompts_metadata: {len(prompts_metadata)}")
    
    # Create mapping from key to metadata
    # Use index-based mapping, but also try to parse key to index for robustness
    key_to_metadata = {}
    for idx, meta in enumerate(prompts_metadata):
        # Try both padded and unpadded key formats
        key_padded = f"request_{idx:06d}"
        key_to_metadata[key_padded] = meta
        key_unpadded = f"request_{idx}"
        if key_unpadded not in key_to_metadata:  # Don't overwrite if already set
            key_to_metadata[key_unpadded] = meta
    
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # Also create index-based mapping for cases where results and metadata are in same order
    # This is a fallback if key lookup fails
    results_with_metadata = list(zip(results, prompts_metadata)) if len(results) == len(prompts_metadata) else None
    
    for result_idx, result in enumerate(results):
        key = result.get("key", "")
        if not key:
            continue
        
        # Try direct key lookup first
        metadata = key_to_metadata.get(key, None)
        
        # Fallback: if key lookup fails and we have same-length lists, use index-based mapping
        if not metadata and results_with_metadata and result_idx < len(results_with_metadata):
            _, metadata = results_with_metadata[result_idx]
        # Fallback: try to parse key to index
        elif not metadata:
            idx = parse_request_index(key)
            if idx is not None and 0 <= idx < len(prompts_metadata):
                metadata = prompts_metadata[idx]
        
        if not metadata:
            print(f"⚠️  Warning: No metadata found for key {key} (result index: {result_idx}, total metadata: {len(prompts_metadata)})")
            error_count += 1
            continue
        
        image_data_b64 = result.get("image_data")
        if not image_data_b64:
            error = result.get("error")
            print(f"⚠️  Warning: No image data for key {key}" + (f" (error: {error})" if error else ""))
            error_count += 1
            continue
        
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data_b64)
            
            # Generate filename (including cluster_id for clustered table visuals)
            filename = make_image_filename(
                run_tag=metadata.get("run_tag", run_tag),
                group_id=metadata.get("group_id", ""),
                entity_id=metadata.get("entity_id"),
                card_role=metadata.get("card_role"),
                spec_kind=metadata.get("spec_kind"),
                cluster_id=metadata.get("cluster_id"),
                suffix=filename_suffix,
            )
            
            # Save image (skip if file already exists to prevent overwriting)
            image_path = images_dir / filename
            if image_path.exists():
                skipped_count += 1
                # Still add to saved_images for tracking, but mark as skipped
                saved_images.append({
                    "filename": filename,
                    "run_tag": metadata.get("run_tag", run_tag),
                    "group_id": metadata.get("group_id", ""),
                    "entity_id": metadata.get("entity_id", ""),
                    "card_role": metadata.get("card_role", ""),
                    "spec_kind": metadata.get("spec_kind", ""),
                    "cluster_id": metadata.get("cluster_id", ""),
                    "image_placement_final": metadata.get("image_placement_final", ""),
                    "skipped": True,  # Mark as skipped
                })
                continue
            
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            
            saved_count += 1
            saved_images.append({
                "filename": filename,
                "run_tag": metadata.get("run_tag", run_tag),
                "group_id": metadata.get("group_id", ""),
                "entity_id": metadata.get("entity_id"),
                "card_role": metadata.get("card_role", ""),
                "spec_kind": metadata.get("spec_kind", ""),
                "cluster_id": metadata.get("cluster_id", ""),
                "image_placement_final": metadata.get("image_placement_final", ""),
            })
            
            print(f"✅ Saved image: {filename}")
            
        except Exception as e:
            print(f"❌ Error saving image for key {key}: {e}")
            error_count += 1
            continue
    
    # Print summary
    total_processed = saved_count + skipped_count + error_count
    print(f"\n📊 Image save summary:")
    print(f"   📁 images_dir: {images_dir}")
    print(f"   🏷️  run_tag: {run_tag}")
    print(f"   📥 Total results to process: {len(results)}")
    print(f"   📋 Total metadata entries: {len(prompts_metadata)}")
    if total_processed > 0:
        print(f"   ✅ Newly saved: {saved_count}")
        print(f"   ⏭️  Skipped (already exist): {skipped_count}")
        print(f"   ❌ Errors: {error_count}")
        print(f"   📦 Total processed: {total_processed}")
    else:
        print(f"   ⚠️  WARNING: No images were processed!")
        print(f"   This might indicate a problem with key mapping or image data extraction.")
        if len(results) > 0:
            print(f"   Sample result keys: {[r.get('key', 'NO_KEY') for r in results[:3]]}")
            print(f"   Results with image_data: {sum(1 for r in results if r.get('image_data'))}/{len(results)}")

    # A compact, grep-friendly summary line for automation/log scanning
    print(
        f"   🧾 Save summary line: images_dir={images_dir} run_tag={run_tag} "
        f"saved={saved_count} skipped={skipped_count} errors={error_count} total_processed={total_processed}"
    )
    
    return saved_images


# =========================
# Main Execution
# =========================

def initialize_api_key_rotator(base_dir: Path) -> Optional[Any]:
    """ApiKeyRotator를 초기화합니다. 매번 첫 번째 키부터 시작하고 .env 파일을 새로 로드합니다."""
    global _global_rotator
    
    if not ROTATOR_AVAILABLE:
        return None
    
    try:
        if ApiKeyRotator is None:
            return None
        
        # IMPORTANT: Force reload .env file to get latest API keys
        # Clear existing GOOGLE_API_KEY_* environment variables first
        env_path = base_dir / ".env"
        if env_path.exists():
            # Remove existing GOOGLE_API_KEY_* from environment to force reload
            keys_to_remove = [k for k in os.environ.keys() if k.startswith("GOOGLE_API_KEY_")]
            for key in keys_to_remove:
                os.environ.pop(key, None)
            
            # Force reload .env file with override=True
            load_dotenv(dotenv_path=env_path, override=True)
        
        # Create new rotator instance (will load fresh keys from .env)
        _global_rotator = ApiKeyRotator(base_dir=base_dir, key_prefix="GOOGLE_API_KEY")
        if _global_rotator is not None and _global_rotator.keys:
            # Always start from the first key (index 0) to use current .env keys
            _global_rotator._current_index = 0
            _global_rotator.state["current_key_index"] = 0
            _global_rotator._save_state()  # Save the reset state
            
            current_key_number = _global_rotator.key_numbers[_global_rotator._current_index]
            print(f"🔑 API KEY: Using key index {_global_rotator._current_index} (GOOGLE_API_KEY_{current_key_number})")
            print(f"   Total keys loaded: {len(_global_rotator.keys)}")
            print(f"   Loaded key numbers: {_global_rotator.key_numbers}")
        return _global_rotator
    except Exception as e:
        print(f"⚠️  Warning: Failed to initialize API key rotator: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """메인 실행 함수."""
    parser = argparse.ArgumentParser(description="Batch Image Generator using Gemini Batch API")
    parser.add_argument(
        "--input",
        type=str,
        help="Path to s3_image_spec.jsonl file",
    )
    parser.add_argument(
        "--base_dir",
        type=str,
        default=".",
        help="Base directory (default: current directory)",
    )
    parser.add_argument(
        "--run_tag",
        type=str,
        help="Run tag (if not provided, will be extracted from spec file)",
    )
    parser.add_argument(
        "--arm",
        type=str,
        help="Arm identifier (for output path)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume mode: check existing batches and skip completed ones",
    )
    parser.add_argument(
        "--check_status",
        action="store_true",
        help="Check status of all tracked batches",
    )
    parser.add_argument(
        "--batch_id",
        type=str,
        help="Check status of a specific batch ID (e.g., 'k4b7g514val6yea6jjnt' or full 'batches/...')",
    )
    parser.add_argument(
        "--api_key_index",
        type=int,
        help="Use specific API key index (1-based)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Model name (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--image_size",
        type=str,
        default=IMAGE_SIZE,
        help=f"Image size (default: {IMAGE_SIZE})",
    )
    parser.add_argument(
        "--aspect_ratio",
        type=str,
        default=IMAGE_ASPECT_RATIO,
        help=f"Aspect ratio (default: {IMAGE_ASPECT_RATIO})",
    )
    parser.add_argument(
        "--cleanup-duplicates",
        action="store_true",
        help="Clean up duplicate batch metadata entries (automatically creates backup)",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="(DANGER) Backup+reset .batch_tracking.json and .batch_failed.json. Requires --yes.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Use with --reset-state to skip creating backups (NOT recommended).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm dangerous operations (e.g., --reset-state).",
    )
    parser.add_argument(
        "--only-infographic",
        action="store_true",
        help="Generate only infographic images (S1_TABLE_VISUAL), skip card images",
    )
    parser.add_argument(
        "--image_type",
        type=str,
        choices=["anki", "realistic", "regen", "repaired"],
        default=None,
        help="Image type for folder and filename suffix. "
             "Options: 'anki' (images_anki/), 'realistic' (images_realistic/, _realistic suffix), "
             "'regen' (images_regen/, _regen suffix), 'repaired' (images__repaired/). "
             "If not provided, uses default behavior (images/ folder, no suffix).",
    )
    parser.add_argument(
        "--filename_suffix",
        type=str,
        default=None,
        help="Override filename suffix (e.g., '_realistic', '_regen'). "
             "If not provided and --image_type is set, auto-derived from --image_type.",
    )
    parser.add_argument(
        "--max-download-workers",
        type=int,
        default=5,
        help="Maximum number of parallel workers for downloading batches (default: 5)",
    )
    
    args = parser.parse_args()
    
    # Set global image_type settings (for use in helper functions)
    global _global_image_type, _global_filename_suffix
    _global_image_type = getattr(args, "image_type", None)
    _global_filename_suffix = resolve_filename_suffix(
        image_type=_global_image_type,
        filename_suffix=getattr(args, "filename_suffix", None),
    )
    
    # Load .env file
    base_dir = Path(args.base_dir).resolve()
    env_path = base_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    else:
        load_dotenv(override=True)
    
    # Initialize API key rotator
    rotator = initialize_api_key_rotator(base_dir)

    # Reset state mode (backup + initialize tracking/failed files)
    if args.reset_state:
        if not args.yes:
            print("❌ Refusing to reset state without explicit confirmation.")
            print("   Re-run with: --reset-state --yes")
            print("   (Add --no-backup only if you are absolutely sure.)")
            return

        print("🧯 Fallback reset: backing up + reinitializing batch state files...")
        result = reset_batch_state_files(base_dir, backup=(not args.no_backup))

        if result.get("backup_tracking_path"):
            print(f"📦 Tracking backup: {result['backup_tracking_path']}")
        if result.get("backup_failed_path"):
            print(f"📦 Failed backup:   {result['backup_failed_path']}")

        print(f"🧾 Tracking reset: {result['tracking_path']} (ok={result['ok_tracking']})")
        print(f"🧾 Failed reset:   {result['failed_path']} (ok={result['ok_failed']})")
        print("✅ Reset completed. Images were NOT modified; reruns will still skip locally existing images.")
        return
    
    # Cleanup duplicates mode
    if args.cleanup_duplicates:
        batch_tracking_path = get_batch_tracking_file_path(base_dir)
        if not batch_tracking_path.exists():
            print(f"❌ Error: Tracking file not found: {batch_tracking_path}")
            return
        
        print("🧹 Starting duplicate cleanup...")
        success, removed_count = cleanup_and_save_tracking_file(batch_tracking_path, backup=True)
        if success:
            print(f"✅ Cleanup completed successfully: {removed_count} duplicate batch(es) removed")
        else:
            print(f"❌ Cleanup failed")
        return
    
    # Check status mode
    if args.check_status:
        batch_tracking_path = get_batch_tracking_file_path(base_dir)
        tracking_data = load_batch_tracking_file(batch_tracking_path)
        batches = tracking_data.get("batches", {})
        
        if not batches:
            print("No tracked batches found.")
            return
    
        print("=" * 60)
        print("Batch Status Report")
        print("=" * 60)
        
        # Get API key for checking status
        api_key = None
        if rotator is not None:
            api_key = rotator.get_current_key()
        else:
            api_key = os.getenv(GEMINI_API_KEY_ENV, "").strip()
        
        completed_batches = []
        # NOTE: We intentionally do per-batch download+save in --check_status mode.
        # Pre-downloading many large result files (often 1GB+) can delay saving logs and risks OOM.
        batches_to_download = []  # Collect batches for download+save (per batch)
        
        # If --batch_id is specified, filter to only that batch
        target_batch_id = args.batch_id
        if target_batch_id:
            print(f"🔍 Checking specific batch: {target_batch_id}")
            print("=" * 60)
        
        for api_key_str, api_batches in batches.items():
            chunks = api_batches.get("chunks", [])
            run_tag = api_batches.get("run_tag", "")
            
            # Filter chunks if --batch_id is specified
            if target_batch_id:
                chunks = [
                    chunk for chunk in chunks
                    if target_batch_id in chunk.get("batch_id", "")
                ]
                if not chunks:
                    continue
            
            print(f"\n{api_key_str}:")
            print(f"  Run tag: {run_tag}")
            print(f"  Total batches: {len(chunks)}")
            
            for chunk in chunks:
                batch_id = chunk.get("batch_id", "")
                old_status = chunk.get("status", "")
                num_requests = chunk.get("num_requests", 0)
                chunk_index = chunk.get("chunk_index", "?")
                created_at = chunk.get("created_at", "")
                
                # Short batch ID for display
                short_id = batch_id.split("/")[-1][:20] + "..." if batch_id and "/" in batch_id else batch_id[:20] + "..." if batch_id else "N/A"
                
                # Get the API key that was used to create this batch
                # Priority: api_key_number (actual GOOGLE_API_KEY number) > api_key_index > try all keys
                chunk_api_key_number = chunk.get("api_key_number")
                chunk_api_key_index = chunk.get("api_key_index")
                chunk_api_key = None
                
                if chunk_api_key_number and rotator is not None:
                    # Use the actual GOOGLE_API_KEY number (e.g., 14, 15, etc.)
                    try:
                        # Find the index of the key with this number
                        if chunk_api_key_number in rotator.key_numbers:
                            target_index = rotator.key_numbers.index(chunk_api_key_number)
                            chunk_api_key = rotator.keys[target_index]
                            print(f"    Using GOOGLE_API_KEY_{chunk_api_key_number} for this batch")
                    except (ValueError, IndexError):
                        pass
                
                # Fallback: use api_key_index if api_key_number not available
                if not chunk_api_key and chunk_api_key_index and rotator is not None:
                    try:
                        # Rotate to the correct key index (0-based)
                        target_index = chunk_api_key_index - 1  # Convert 1-based to 0-based
                        if 0 <= target_index < len(rotator.keys):
                            chunk_api_key = rotator.keys[target_index]
                    except Exception:
                        pass
                
                # Last fallback: try to extract from api_key_str
                if not chunk_api_key:
                    try:
                        if api_key_str.startswith("api_key_"):
                            chunk_api_key_index = int(api_key_str.replace("api_key_", ""))
                            if chunk_api_key_index and rotator is not None:
                                target_index = chunk_api_key_index - 1
                                if 0 <= target_index < len(rotator.keys):
                                    chunk_api_key = rotator.keys[target_index]
                    except (ValueError, AttributeError, IndexError):
                        pass
                
                # Check current status with the correct API key
                status_info = None
                if chunk_api_key:
                    # Try with the identified key
                    try:
                        status_info = check_batch_status(batch_id, api_key=chunk_api_key)
                    except Exception as e:
                        error_str = str(e)
                        # 404, 400 (API 키 무효) 에러는 조용히 처리하고 모든 키 시도
                        if "404" not in error_str and "NOT_FOUND" not in error_str and "400" not in error_str and "INVALID_ARGUMENT" not in error_str and "API_KEY_INVALID" not in error_str:
                            # 다른 에러만 출력
                            print(f"    ⚠️  Error checking batch: {error_str}")
                        # 404, 400 에러는 조용히 처리하고 모든 키 시도
                        status_info = None
                
                # If still not found and we have rotator, try all keys
                # This handles cases where:
                # 1. api_key_number was stored incorrectly (e.g., based on input order instead of actual env var name)
                # 2. API keys were renumbered in .env
                # 3. The batch was created with a key that's no longer in .env
                if not status_info and rotator is not None:
                    # Only print this message if we haven't tried all keys yet
                    if not chunk_api_key:
                        print(f"    Trying all API keys to find the correct one...")
                        if chunk_api_key_number:
                            print(f"    (Note: Recorded api_key_number={chunk_api_key_number} not found in current .env)")
                    for key_idx, test_key in enumerate(rotator.keys):
                        try:
                            status_info = check_batch_status(batch_id, api_key=test_key)
                            if status_info:
                                # Found the correct key! Update the chunk with the correct key number
                                actual_key_number = rotator.key_numbers[key_idx]
                                chunk["api_key_number"] = actual_key_number
                                save_batch_tracking_file(batch_tracking_path, tracking_data)
                                print(f"    ✅ Found batch with GOOGLE_API_KEY_{actual_key_number} (was recorded as {chunk_api_key_number if chunk_api_key_number else 'unknown'})")
                                break
                        except Exception as e:
                            error_str = str(e)
                            # 404, 400 (API 키 무효) 에러는 조용히 다음 키 시도
                            if "404" in error_str or "NOT_FOUND" in error_str or "400" in error_str or "INVALID_ARGUMENT" in error_str or "API_KEY_INVALID" in error_str:
                                continue  # Try next key silently
                            else:
                                # Other error, print but continue
                                print(f"    ⚠️  Error with GOOGLE_API_KEY_{rotator.key_numbers[key_idx]}: {error_str}")
                                continue
                
                # If still not found, report error but check local images
                if not status_info:
                    print(f"  Batch {chunk_index + 1}: {short_id}")
                    print(f"    Status: {old_status} (not found with any API key)")
                    print(f"    Requests: {num_requests}")
                    if created_at:
                        print(f"    Created: {created_at[:19]}")
                    print(f"    ⚠️  Note: This batch may have been deleted, created with a key not in current .env, or the API key is invalid")
                    
                    # Even if remote status can't be checked, verify if images already exist locally
                    # This helps identify if the batch was already downloaded before
                    prompts_metadata = chunk.get("prompts_metadata", [])
                    if prompts_metadata:
                        actual_run_tag = run_tag
                        if prompts_metadata[0].get("run_tag"):
                            actual_run_tag = prompts_metadata[0].get("run_tag")
                        
                        images_dir = resolve_images_dir(base_dir, actual_run_tag, _global_image_type)
                        all_exist, total_count, existing_count = check_batch_images_exist(
                            prompts_metadata, images_dir, actual_run_tag, batch_results=None
                        )
                        
                        if all_exist:
                            print(f"    ✅ All {total_count} images already exist locally (remote status unknown)")
                        elif existing_count > 0:
                            print(f"    ⚠️  {existing_count}/{total_count} images exist locally, {total_count - existing_count} missing (remote status unknown)")
                        else:
                            print(f"    ❌ No images found locally ({total_count} expected) - batch may still be processing or needs API key to check")
                    
                    continue
                if status_info:
                    current_status = status_info.get("state", old_status)
                    # Update status in tracking file
                    if current_status != old_status:
                        chunk["status"] = current_status
                        save_batch_tracking_file(batch_tracking_path, tracking_data)
                    
                    print(f"  Batch {chunk_index + 1}: {short_id}")
                    print(f"    Status: {current_status}")
                    print(f"    Requests: {num_requests}")
                    if created_at:
                        print(f"    Created: {created_at[:19]}")
                    
                    # If completed, check if already downloaded before marking for download
                    if current_status == "JOB_STATE_SUCCEEDED" and "dest_file_name" in status_info:
                        prompts_metadata = chunk.get("prompts_metadata", [])
                        dest_file_name = status_info.get("dest_file_name", "")
                        
                        # prompts_metadata에서 실제 run_tag 가져오기 (배치의 run_tag와 다를 수 있음)
                        actual_run_tag = run_tag  # 기본값
                        if prompts_metadata and prompts_metadata[0].get("run_tag"):
                            actual_run_tag = prompts_metadata[0].get("run_tag")
                        
                        # 먼저 prompts_metadata만으로 빠르게 확인 (결과 파일 다운로드 없이)
                        images_dir = resolve_images_dir(base_dir, actual_run_tag, _global_image_type)
                        all_exist, total_count, existing_count = check_batch_images_exist(
                            prompts_metadata, images_dir, actual_run_tag, batch_results=None
                        )
                        
                        # 모든 이미지가 이미 존재하면 스킵 (결과 파일 다운로드 불필요)
                        if all_exist:
                            print(f"    ✅ All {total_count} images already exist, skipping download")
                            continue
                        
                        # 일부만 존재하거나 없으면 바로 다운로드+저장 큐에 추가
                        # (결과 파일을 미리 여러 개 다운로드해 메모리에 쌓지 않음)
                        if dest_file_name and not all_exist:
                            batch_info = {
                                "batch_id": batch_id,
                                "chunk": chunk,
                                "run_tag": actual_run_tag,
                                "dest_file_name": dest_file_name,
                                "prompts_metadata": prompts_metadata,
                                "batch_results": None,
                            }
                            batches_to_download.append(batch_info)
                            if existing_count > 0:
                                print(f"    ⚠️  {existing_count}/{total_count} images already exist, will download missing ones")
                            print(f"    📥 Queued for download+save (per batch)")
                        else:
                            # dest_file_name이 없으면 다운로드 불가 (희귀 케이스)
                            if not dest_file_name:
                                print("    ⚠️  No dest_file_name; cannot download results for this batch")
                else:
                    print(f"  Batch: {batch_id}")
                    print(f"    Status: {old_status} (could not check)")
                    print(f"    Requests: {num_requests}")
        
        # Download+save all collected batches (per batch)
        if batches_to_download:
            max_workers = args.max_download_workers
            print(f"\n{'='*60}")
            print(f"📥 Starting download of {len(batches_to_download)} batch(es)")
            print(f"{'='*60}")
            success_count, fail_count = download_batches_parallel(
                batches_to_download=batches_to_download,
                base_dir=base_dir,
                rotator=rotator,
                batch_tracking_path=batch_tracking_path,
                tracking_data=tracking_data,
                max_workers=max_workers,
            )
            print(f"\n{'='*60}")
            print(f"✅ Download completed: {success_count} succeeded, {fail_count} failed")
            if success_count > 0:
                print(f"   💡 Check individual batch logs above for details on newly saved vs skipped images")
            print(f"{'='*60}")
        else:
            print("\n✅ No batches need to be downloaded (all images already exist)")
        
        return
    
    # Load prompts from spec file
    if not args.input:
        print("❌ Error: --input is required (or use --check_status)")
        parser.print_help()
        return
    
    spec_path = Path(args.input)
    if not spec_path.is_absolute():
        spec_path = base_dir / spec_path
    
    prompts_data = load_prompts_from_spec(spec_path)
    if not prompts_data:
        print("❌ Error: No prompts loaded")
        return
    
    # Extract run_tag from first prompt if not provided
    run_tag = args.run_tag or prompts_data[0].get("run_tag", "")
    if not run_tag:
        print("❌ Error: run_tag not found in spec file and not provided via --run_tag")
        return
    
    # Filter to only S1_TABLE_VISUAL if --only-infographic
    if args.only_infographic:
        original_count = len(prompts_data)
        prompts_data = [p for p in prompts_data if str(p.get("spec_kind", "")).strip() == "S1_TABLE_VISUAL"]
        print(f"📊 Filtered to {len(prompts_data)} infographic specs (from {original_count} total)")
        if not prompts_data:
            print("❌ No S1_TABLE_VISUAL specs found")
            return
    
    print(f"📝 Total prompts: {len(prompts_data)}")
    print(f"🏷️  Run tag: {run_tag}")
    
    # Calculate prompts hash
    prompts_hash = calculate_prompts_hash(prompts_data)
    print(f"🔐 Prompts hash: {prompts_hash}")
    
    # Load tracking file
    batch_tracking_path = get_batch_tracking_file_path(base_dir)
    tracking_data = load_batch_tracking_file(batch_tracking_path)
    
    # Determine API key index
    api_key_index = args.api_key_index
    if api_key_index is None:
        if rotator:
            api_key_index = rotator._current_index + 1  # 1-based
        else:
            api_key_index = 1
    
    # Check existing batch
    if args.resume:
        existing_batch = check_existing_batch(prompts_hash, api_key_index, tracking_data)
        if existing_batch:
            batch_id = existing_batch.get("batch_id", "")
            status = existing_batch.get("status", "")
            print(f"📋 Found existing batch: {batch_id} (status: {status})")
            
            if status == "JOB_STATE_SUCCEEDED":
                print("✅ Batch already completed, skipping")
                return
            elif status in ("JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"):
                print(f"⚠️  Batch in terminal state: {status}")
                response = input("Do you want to create a new batch? (y/n): ")
                if response.lower() != 'y':
                    return
            else:
                print(f"⏳ Batch still in progress, monitoring...")
                # Monitor existing batch
                final_status = monitor_batch_job(batch_id, poll_interval=60)
                if final_status == "JOB_STATE_SUCCEEDED":
                    # Download and save results
                    status_info = check_batch_status(batch_id)
                    if status_info and "dest_file_name" in status_info:
                        result_file_name = status_info["dest_file_name"]
                        result_content = download_batch_results(result_file_name)
                        if result_content:
                            results = parse_batch_results(result_content)
                            images_dir = resolve_images_dir(base_dir, run_tag, _global_image_type)
                            saved_images = save_images_from_batch(results, prompts_data, images_dir, run_tag, _global_filename_suffix)
                            print(f"✅ Saved {len(saved_images)} images")
                return
    
    # Filter out already submitted prompts BEFORE splitting into batches
    # This prevents duplicate images across different batches
    images_dir = resolve_images_dir(base_dir, run_tag, _global_image_type)
    print(f"📁 Images directory: {images_dir}")
    if _global_filename_suffix:
        print(f"📝 Filename suffix: {_global_filename_suffix}")
    
    print(f"\n🔍 Filtering out already submitted/existing prompts...")
    
    filtered_prompts, already_submitted_count, already_exist_locally_count = filter_duplicate_prompts(
        prompts_data=prompts_data,
        tracking_data=tracking_data,
        images_dir=images_dir,
        run_tag=run_tag,
        base_dir=base_dir,
    )
    
    if already_submitted_count > 0:
        print(f"⚠️  Filtered out {already_submitted_count} already submitted prompt(s)")
    if already_exist_locally_count > 0:
        print(f"✅ Filtered out {already_exist_locally_count} prompt(s) with existing local images")
    if filtered_prompts:
        print(f"📝 {len(filtered_prompts)} new prompt(s) to process")
    else:
        print(f"✅ All prompts are already submitted or exist locally. Nothing to process.")
        return
    
    # Feasibility check (using filtered prompts)
    prompts_text = [p.get("prompt_en", "") for p in filtered_prompts]
    print_feasibility_report(prompts_text, image_size=args.image_size)
    
    # Split filtered prompts by token limit
    batches = split_prompts_by_token_limit(
        filtered_prompts,
        image_size=args.image_size,
        token_limit=TIER1_BATCH_TOKEN_LIMIT,
    )
    
    print(f"\n📦 Split into {len(batches)} batch(es)")
    for i, batch in enumerate(batches):
        total_tokens = sum(
            estimate_tokens_per_request(
                p.get("prompt_en", ""),
                "4K" if str(p.get("spec_kind", "")).strip() == "S1_TABLE_VISUAL" else args.image_size
            ) for p in batch
        )
        print(f"   Batch {i+1}: {len(batch)} requests, ~{total_tokens:,} tokens")
    
    # Get API key
    api_key = None
    if rotator is not None:
        api_key = rotator.get_current_key()
    else:
        api_key = os.getenv(GEMINI_API_KEY_ENV, "").strip()
    
    if not api_key:
        print(f"❌ Error: No API key available")
        return
    
    # Process each batch
    # Start with current API key, will rotate on 429 errors
    current_api_key_index = api_key_index
    current_api_key = api_key
    # Track actual GOOGLE_API_KEY number (not just index)
    current_actual_key_number = None
    if rotator is not None:
        current_actual_key_number = rotator.key_numbers[rotator._current_index]
    
    output_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_tmp_dir = output_dir / "batch_tmp"
    batch_tmp_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup monitoring
    log_dir = get_batch_log_dir(base_dir)
    api_usage_path = get_api_usage_file_path(base_dir)
    
    # Track progress
    total_batches = len(batches)
    completed_batches = 0
    failed_batches = 0
    skipped_batches = 0
    
    # Print initial progress
    print_batch_progress(0, total_batches, 0, 0, 0)
    log_batch_event(log_dir, "BATCH_START", f"Starting batch processing for {total_batches} batches", {
        "run_tag": run_tag,
        "total_batches": total_batches,
    })
    
    for chunk_index, batch_prompts in enumerate(batches):
        print(f"\n{'='*60}")
        print(f"Processing Batch {chunk_index + 1}/{len(batches)}")
        print(f"{'='*60}")
        
        # Check for already submitted entities in this batch
        # This prevents duplicate submissions across different batches
        # Also check if images already exist locally
        images_dir = resolve_images_dir(base_dir, run_tag, _global_image_type)
        
        # Use filter_duplicate_prompts to check for duplicates
        filtered_prompts, already_submitted_count, already_exist_locally_count = filter_duplicate_prompts(
            prompts_data=batch_prompts,
            tracking_data=tracking_data,
            images_dir=images_dir,
            run_tag=run_tag,
            base_dir=base_dir,
        )
        
        # Collect skipped prompts for detailed logging
        already_submitted = []
        already_exist_locally = []
        filtered_prompt_set = set(id(p) for p in filtered_prompts)
        
        for prompt in batch_prompts:
            if id(prompt) not in filtered_prompt_set:
                # Check which category it belongs to
                is_submitted = check_if_prompt_submitted(prompt, tracking_data, base_dir)
                if is_submitted:
                    already_submitted.append(prompt)
                else:
                    already_exist_locally.append(prompt)
        
        if already_submitted_count > 0:
            print(f"⚠️  Skipping {already_submitted_count} already submitted entity(ies) in this batch")
            for prompt in already_submitted[:5]:  # Show first 5
                entity_id = prompt.get("entity_id", "")
                card_role = prompt.get("card_role", "")
                print(f"   - {entity_id} ({card_role})")
            if len(already_submitted) > 5:
                print(f"   ... and {len(already_submitted) - 5} more")
        if already_exist_locally_count > 0:
            print(f"✅ Skipping {already_exist_locally_count} entity(ies) with existing local images")
        
        if not filtered_prompts:
            print(f"⏭️  All entities in this batch are already submitted, skipping")
            skipped_batches += 1
            print_batch_progress(0, total_batches, completed_batches, failed_batches, skipped_batches)
            continue
        
        # Use only new prompts for this batch
        batch_prompts = filtered_prompts
        print(f"📝 Processing {len(batch_prompts)} new entity(ies) in this batch")
        
        # Create JSONL file
        jsonl_path = batch_tmp_dir / f"batch_requests_{run_tag}_chunk{chunk_index}_{int(time.time())}.jsonl"
        
        if not create_jsonl_file(
            prompts_data=batch_prompts,
            output_path=jsonl_path,
            model=args.model,
            aspect_ratio=args.aspect_ratio,
            image_size=args.image_size,
            temperature=IMAGE_TEMPERATURE,
        ):
            print(f"❌ Failed to create JSONL file for chunk {chunk_index}")
            continue
        
        # Upload file (will be re-uploaded if API key rotates)
        file_uri = upload_file(jsonl_path, api_key=current_api_key)
        if not file_uri:
            print(f"❌ Failed to upload file for chunk {chunk_index}")
            continue
        
        # Create batch job with retry on 429 errors
        # Try all available API keys if 429 error occurs
        display_name = f"batch_image_{run_tag}_chunk{chunk_index}"
        batch_job = None
        
        # Calculate max retries: try all available keys + 1 initial attempt
        max_retries = len(rotator.keys) if rotator is not None else 3
        initial_key_index = rotator._current_index if rotator is not None else 0
        keys_tried = set()
        
        for retry_attempt in range(max_retries):
            try:
                batch_job = create_batch_job(
                    file_uri=file_uri,
                    model=args.model,
                    display_name=display_name,
                    api_key=current_api_key,
                )
                
                if batch_job:
                    print(f"✅ Batch job created successfully with GOOGLE_API_KEY_{current_actual_key_number}")
                    break  # Success
            except ValueError as e:
                error_str = str(e)
                # Check error types
                is_429_error = "429_QUOTA_EXHAUSTED" in error_str
                is_404_error = "404_NOT_FOUND" in error_str or "404" in error_str or "NOT_FOUND" in error_str
                is_503_error = "503_SERVICE_UNAVAILABLE" in error_str
                is_500_error = "500_INTERNAL_ERROR" in error_str
                is_network_error = "NETWORK_ERROR" in error_str
                is_unknown_error = "UNKNOWN_ERROR" in error_str
                
                # Temporary errors that need API key rotation
                needs_key_rotation = (is_429_error or is_404_error) and rotator is not None
                
                # Temporary errors that just need retry (no key rotation needed)
                needs_simple_retry = is_503_error or is_500_error or is_network_error or is_unknown_error
                
                if needs_key_rotation and rotator is not None:
                    # Track which key we tried
                    if current_actual_key_number is not None:
                        keys_tried.add(current_actual_key_number)
                    
                    # Check if we've tried all keys
                    if len(keys_tried) >= len(rotator.keys):
                        if is_429_error:
                            print(f"❌ All {len(rotator.keys)} API keys exhausted (429 errors). Skipping this batch.")
                        else:
                            print(f"❌ All {len(rotator.keys)} API keys returned 404 errors. Skipping this batch.")
                        break
                    
                    # Try to rotate to next key
                    error_type = "429" if is_429_error else "404"
                    print(f"⚠️  {error_type} error detected with GOOGLE_API_KEY_{current_actual_key_number}, rotating to next API key...")
                    try:
                        if is_429_error:
                            rotator.rotate_on_quota_exhausted()
                        else:
                            # For 404, just rotate to next key
                            if rotator._current_index < len(rotator.keys) - 1:
                                rotator._current_index += 1
                            else:
                                rotator._current_index = 0  # Wrap around
                        
                        current_api_key = rotator.get_current_key()
                        current_api_key_index = rotator._current_index + 1  # 1-based
                        current_actual_key_number = rotator.key_numbers[rotator._current_index]
                        print(f"🔄 Rotated to key index {rotator._current_index} (GOOGLE_API_KEY_{current_actual_key_number})")
                        
                        # IMPORTANT: Re-upload file with new API key (files are key-specific)
                        print(f"📤 Re-uploading file with new API key...")
                        file_uri = upload_file(jsonl_path, api_key=current_api_key)
                        if not file_uri:
                            print(f"❌ Failed to re-upload file with new key, skipping this batch")
                            break
                        print(f"✅ File re-uploaded successfully with GOOGLE_API_KEY_{current_actual_key_number}")
                        
                        # Update api_key_str for tracking
                        api_key_str = f"api_key_{current_api_key_index}"
                        if api_key_str not in tracking_data["batches"]:
                            tracking_data["batches"][api_key_str] = {
                                "prompts_hash": prompts_hash,
                                "run_tag": run_tag,
                                "chunks": [],
                            }
                        time.sleep(2)  # Brief delay before retry
                        continue
                    except Exception as rotate_error:
                        print(f"⚠️  Failed to rotate API key: {rotate_error}")
                        # If rotation fails, try to continue with next key manually
                        if rotator is not None and rotator._current_index < len(rotator.keys) - 1:
                            rotator._current_index += 1
                            current_api_key = rotator.get_current_key()
                            current_api_key_index = rotator._current_index + 1
                            current_actual_key_number = rotator.key_numbers[rotator._current_index]
                            print(f"🔄 Manually rotated to key index {rotator._current_index} (GOOGLE_API_KEY_{current_actual_key_number})")
                            # Re-upload file with new key
                            print(f"📤 Re-uploading file with new API key...")
                            file_uri = upload_file(jsonl_path, api_key=current_api_key)
                            if not file_uri:
                                print(f"❌ Failed to re-upload file with new key, skipping this batch")
                                break
                            time.sleep(2)
                            continue
                        break
                elif needs_simple_retry:
                    # Temporary errors that don't need key rotation - just retry with exponential backoff
                    wait_time = min(2 ** retry_attempt, 60)  # 1s, 2s, 4s, 8s, ... max 60s
                    error_type = "503" if is_503_error else ("500" if is_500_error else ("Network" if is_network_error else "Unknown"))
                    print(f"⚠️  {error_type} error detected (attempt {retry_attempt + 1}/{max_retries})")
                    print(f"   Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue  # Retry with same API key
                else:
                    # Not a retryable error
                    print(f"❌ Non-retryable error: {e}")
                    break
        
        if not batch_job:
            # IMPORTANT: If batch creation failed (e.g., all API keys returned 429 errors),
            # we do NOT record this in the tracking file. This allows the entities to be
            # retried in a future run. Only successfully created batches are recorded.
            # However, we DO record it in the failed batches file for retry scheduling.
            failed_batch_path = get_batch_failed_file_path(base_dir)
            error_type = "UNKNOWN"
            error_message = ""
            
            if rotator is not None and len(keys_tried) >= len(rotator.keys):
                error_type = "429_ALL_KEYS_EXHAUSTED"
                error_message = f"All {len(rotator.keys)} API keys returned 429 errors (quota exhausted)"
                print(f"❌ Failed to create batch job for chunk {chunk_index}: {error_message}")
            else:
                error_type = "BATCH_CREATION_FAILED"
                error_message = f"Failed after {retry_attempt + 1} attempt(s)"
                print(f"❌ Failed to create batch job for chunk {chunk_index}: {error_message}")
            
            # Record failed batch for retry scheduling
            try:
                record_failed_batch(
                    failed_path=failed_batch_path,
                    failed_data={},
                    prompts_data=batch_prompts,
                    chunk_index=chunk_index,
                    error_type=error_type,
                    error_message=error_message,
                    keys_tried=keys_tried,
                    run_tag=run_tag,
                    spec_path=spec_path,
                )
                print(f"📝 Failed batch recorded in {failed_batch_path.name} for retry scheduling")
            except Exception as record_error:
                print(f"⚠️  Warning: Failed to record failed batch: {record_error}")
            
            print(f"⏭️  Skipping this batch and continuing with next batch...")
            print(f"   ⚠️  Note: This batch is NOT recorded in tracking file, so entities can be retried later")
            
            # Update progress
            failed_batches += 1
            print_batch_progress(0, total_batches, completed_batches, failed_batches, skipped_batches)
            log_batch_event(log_dir, "BATCH_FAILED", f"Batch {chunk_index + 1} failed", {
                "chunk_index": chunk_index,
                "error_type": error_type,
                "error_message": error_message,
            })
            continue
        
        # IMPORTANT: Only record successfully created batches in tracking file.
        # Failed batches are NOT recorded, allowing entities to be retried in future runs.
        
        # Ensure api_key_str is set correctly
        api_key_str = f"api_key_{current_api_key_index}"
        if api_key_str not in tracking_data["batches"]:
            tracking_data["batches"][api_key_str] = {
                "prompts_hash": prompts_hash,
                "run_tag": run_tag,
                "chunks": [],
            }
        
        batch_id = batch_job["name"]
        state_name = batch_job["state"]
        
        # Update tracking file - ONLY for successfully created batches
        # Store individual prompt metadata for S4 to check
        # All fields are normalized to strings (None -> "") for consistency with create_entity_key
        prompts_metadata_list = []
        for prompt_data in batch_prompts:
            prompt_hash = hashlib.sha256(prompt_data.get("prompt_en", "").encode("utf-8")).hexdigest()[:16]
            # Normalize all fields to strings (matching create_entity_key normalization)
            # This ensures consistent comparison when checking for duplicates
            prompts_metadata_list.append({
                "prompt_hash": prompt_hash,
                "run_tag": str(prompt_data.get("run_tag", run_tag) or "").strip(),
                "group_id": str(prompt_data.get("group_id", "") or "").strip(),
                "entity_id": str(prompt_data.get("entity_id") or "").strip(),
                "card_role": str(prompt_data.get("card_role") or "").strip(),
                "spec_kind": str(prompt_data.get("spec_kind", "") or "").strip(),
                "cluster_id": str(prompt_data.get("cluster_id") or "").strip(),
            })
        
        # Verify prompts_metadata format before saving
        is_valid, error_msg = verify_prompts_metadata_format(prompts_metadata_list)
        if not is_valid:
            print(f"❌ Error: prompts_metadata validation failed: {error_msg}")
            print(f"   This should not happen - please report this issue")
            # Continue anyway (don't fail the batch), but log the error
            log_batch_event(log_dir, "METADATA_VALIDATION_ERROR", f"prompts_metadata validation failed: {error_msg}", {
                "chunk_index": chunk_index,
                "batch_id": batch_id,
            })
        
        chunk_info = {
            "chunk_index": chunk_index,
            "batch_id": batch_id,
            "status": state_name,
            "created_at": datetime.now().isoformat(),
            "file_uri": file_uri,
            "num_requests": len(batch_prompts),
            "estimated_tokens": sum(
                estimate_tokens_per_request(
                    p.get("prompt_en", ""),
                    "4K" if str(p.get("spec_kind", "")).strip() == "S1_TABLE_VISUAL" else args.image_size
                ) for p in batch_prompts
            ),
            "prompts_metadata": prompts_metadata_list,  # Store individual prompt info for S4 checking
            "original_spec_path": str(spec_path),  # Store original spec file path for result mapping
            "api_key_index": current_api_key_index,  # Store which API key index was used (1-based)
            "api_key_number": current_actual_key_number,  # Store actual GOOGLE_API_KEY number (e.g., 14, 15, etc.)
        }
        
        # Record this batch in tracking file - only successful batches reach here
        tracking_data["batches"][api_key_str]["chunks"].append(chunk_info)
        save_batch_tracking_file(batch_tracking_path, tracking_data)
        print(f"✅ Batch recorded in tracking file (entities will be skipped in future runs)")
        
        # Track API usage
        if current_actual_key_number is not None:
            estimated_tokens = chunk_info.get("estimated_tokens", 0)
            num_requests = chunk_info.get("num_requests", 0)
            track_api_usage(
                usage_path=api_usage_path,
                api_key_number=current_actual_key_number,
                estimated_tokens=estimated_tokens,
                num_requests=num_requests,
                batch_id=batch_id,
            )
        
        # Log batch creation
        log_batch_event(log_dir, "BATCH_CREATED", f"Batch {chunk_index + 1} created successfully", {
            "chunk_index": chunk_index,
            "batch_id": batch_id,
            "status": state_name,
            "api_key_number": current_actual_key_number,
            "num_requests": len(batch_prompts),
            "estimated_tokens": chunk_info.get("estimated_tokens", 0),
        })
        
        print(f"✅ Batch job created: {batch_id}")
        print(f"   Status: {state_name}")
        print(f"   Monitor: python batch_image_generator.py --check_status")
        
        # Update progress
        completed_batches += 1
        print_batch_progress(0, total_batches, completed_batches, failed_batches, skipped_batches)
    
    # Final progress update
    print_batch_progress(0, total_batches, completed_batches, failed_batches, skipped_batches)
    
    # Log completion
    log_batch_event(log_dir, "BATCH_COMPLETE", f"All batches processed", {
        "total_batches": total_batches,
        "completed": completed_batches,
        "failed": failed_batches,
        "skipped": skipped_batches,
    })
    
    print(f"\n✅ All batches submitted!")
    print(f"   Total batches: {total_batches}")
    print(f"   ✅ Completed: {completed_batches}")
    print(f"   ❌ Failed: {failed_batches}")
    print(f"   ⏭️  Skipped: {skipped_batches}")
    print(f"   Tracking file: {batch_tracking_path}")
    print(f"   Check status: python batch_image_generator.py --check_status")
    
    # Print API usage summary
    print_api_usage_summary(api_usage_path)


if __name__ == "__main__":
    main()

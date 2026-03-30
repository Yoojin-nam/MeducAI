"""
MeducAI - Batch S5 Validator (Gemini Batch API)

이 스크립트는 Google Gemini Batch API를 사용하여 대량의 S5 검증(S1 table + S2 card)을 수행합니다.
기존 동기식 코드(05_s5_validator.py)는 수정하지 않으며,
배치 처리 전용으로 독립적으로 작동합니다.

Usage:
    # S1 table 배치 검증 제출
    python batch_s5_validator.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm G --mode s1_only
    
    # 상태 확인 및 결과 다운로드
    python batch_s5_validator.py --check_status
    
    # 재시도 (실패한 배치)
    python batch_s5_validator.py --resume

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
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Error: google.genai not available. Install: pip install google-genai")

from dotenv import load_dotenv

# API Key Rotator
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

# Prompt bundle loader
try:
    from tools.prompt_bundle import load_prompt_bundle
except ImportError:
    load_prompt_bundle = None

# =========================
# Configuration
# =========================

# Tier 1 Batch Limit: 2,000,000 tokens
TIER1_BATCH_TOKEN_LIMIT = 2_000_000

# S5 Models (fixed, arm-independent)
S5_S1_TABLE_MODEL = "gemini-3-pro-preview"  # Pro model for S1 table validation
S5_S2_CARD_MODEL = "gemini-3-flash-preview"  # Flash model for S2 card validation

# S5 Temperature (low for reproducibility)
S5_TEMPERATURE = 0.2

# Max output tokens (model-specific)
# Gemini Pro: 8192 default, max 32768
# Gemini Flash: 8192 default
S5_MAX_OUTPUT_TOKENS_PRO = 32768  # For S1 table validation (very large responses with many issues)
S5_MAX_OUTPUT_TOKENS_FLASH = 8192  # For S2 card validation (smaller responses)

# API Key
GEMINI_API_KEY_ENV = "GOOGLE_API_KEY"

# Global rotator instance
_global_rotator: Optional[Any] = None


def get_batch_tracking_file_path(base_dir: Path) -> Path:
    """S5 배치 추적 파일 경로를 반환합니다."""
    return base_dir / "2_Data" / "metadata" / ".batch_s5_tracking.json"


def get_batch_failed_file_path(base_dir: Path) -> Path:
    """S5 배치 실패 기록 파일 경로를 반환합니다."""
    return base_dir / "2_Data" / "metadata" / ".batch_s5_failed.json"


def get_batch_log_dir(base_dir: Path) -> Path:
    """S5 배치 로그 디렉토리 경로를 반환합니다."""
    return base_dir / "2_Data" / "metadata" / "batch_logs_s5"


# =========================
# Token Estimation
# =========================

def estimate_tokens_per_s1_request(
    table_markdown: str,
    objective_bullets: str,
    has_infographic: bool = False,
    num_clusters: int = 0,
) -> int:
    """
    S1 table validation 요청 1회당 소모되는 토큰 수를 추정합니다.
    
    Args:
        table_markdown: S1 master table markdown
        objective_bullets: Objective bullets
        has_infographic: 인포그래픽 포함 여부
        num_clusters: 클러스터 수 (clustered infographic)
    
    Returns:
        예상 토큰 수
    """
    # 입력 토큰: system + user prompt + table + objective
    text_tokens = int((len(table_markdown) + len(objective_bullets)) * 0.3)
    system_tokens = 500  # S5_SYSTEM prompt
    user_tokens = 1000  # S5_USER_TABLE prompt template
    
    # 인포그래픽 이미지 토큰 (4K image ≈ 5000 tokens)
    image_tokens = 0
    if has_infographic:
        if num_clusters > 0:
            # 클러스터링된 인포그래픽: 각 클러스터당 별도 LLM 호출
            image_tokens = 5000 * min(num_clusters, 4)  # Max 4 clusters
        else:
            # 단일 인포그래픽
            image_tokens = 5000
    
    # 출력 토큰: JSON response + RAG evidence
    output_tokens = 2000
    
    return system_tokens + user_tokens + text_tokens + image_tokens + output_tokens


def estimate_tokens_per_s2_request(card_text: str) -> int:
    """
    S2 card validation 요청 1회당 소모되는 토큰 수를 추정합니다.
    
    Args:
        card_text: S2 card 텍스트
    
    Returns:
        예상 토큰 수
    """
    # 입력 토큰: system + user prompt + card
    text_tokens = int(len(card_text) * 0.3)
    system_tokens = 500
    user_tokens = 800
    
    # 출력 토큰: JSON response
    output_tokens = 1500
    
    return system_tokens + user_tokens + text_tokens + output_tokens


# =========================
# Batch Tracking
# =========================

def load_batch_tracking_file(tracking_path: Path) -> Dict[str, Any]:
    """S5 배치 작업 추적 파일을 로드합니다."""
    if not tracking_path.exists():
        return {
            "schema_version": "S5_BATCH_TRACKING_v1.0",
            "batches": {},
            "last_updated": datetime.now().isoformat(),
        }
    
    try:
        with open(tracking_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "schema_version" not in data:
                data["schema_version"] = "S5_BATCH_TRACKING_v1.0"
            if "batches" not in data:
                data["batches"] = {}
            return data
    except Exception as e:
        print(f"⚠️  Warning: Error loading tracking file: {e}, creating new one")
        return {
            "schema_version": "S5_BATCH_TRACKING_v1.0",
            "batches": {},
            "last_updated": datetime.now().isoformat(),
        }


def save_batch_tracking_file(tracking_path: Path, data: Dict[str, Any]) -> bool:
    """S5 배치 추적 파일을 저장합니다."""
    try:
        tracking_path.parent.mkdir(parents=True, exist_ok=True)
        data["last_updated"] = datetime.now().isoformat()
        with open(tracking_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error saving tracking file: {e}")
        return False


# =========================
# Data Loading
# =========================

def load_s1_tables(base_dir: Path, run_tag: str, arm: str) -> Dict[str, Any]:
    """
    s1_s2__armX.jsonl에서 S1 테이블 데이터를 로드합니다.
    
    Returns:
        Dict[group_id, s1_table_data]
    """
    s1_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"s1_s2__arm{arm}.jsonl"
    
    if not s1_path.exists():
        print(f"❌ Error: S1 tables file not found: {s1_path}")
        return {}
    
    s1_tables = {}
    try:
        with open(s1_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    record = json.loads(line)
                    group_id = record.get("group_id")
                    if not group_id:
                        print(f"⚠️  Warning: Line {line_num} missing group_id, skipping")
                        continue
                    
                    s1_tables[group_id] = record
                except json.JSONDecodeError as e:
                    print(f"⚠️  Warning: Line {line_num} JSON decode error: {e}, skipping")
                    continue
        
        print(f"✅ Loaded {len(s1_tables)} S1 tables from {s1_path}")
        return s1_tables
    
    except Exception as e:
        print(f"❌ Error loading S1 tables: {e}")
        import traceback
        traceback.print_exc()
        return {}


def load_s2_cards(base_dir: Path, run_tag: str, arm: str, s1_arm: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    s2_entity__armX.jsonl에서 S2 카드 데이터를 로드합니다.
    
    Returns:
        Dict[group_id, List[card_data]]
    """
    # Try s2_entity__s1armX__s2armY.jsonl first (S1/S2 split arms)
    if s1_arm:
        s2_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"s2_entity__s1arm{s1_arm}__s2arm{arm}.jsonl"
    else:
        s2_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"s2_entity__arm{arm}.jsonl"
    
    if not s2_path.exists():
        print(f"⚠️  Warning: S2 cards file not found: {s2_path}")
        return {}
    
    s2_cards_by_group: Dict[str, List[Dict[str, Any]]] = {}
    try:
        with open(s2_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    record = json.loads(line)
                    group_id = record.get("group_id")
                    if not group_id:
                        continue
                    
                    if group_id not in s2_cards_by_group:
                        s2_cards_by_group[group_id] = []
                    
                    s2_cards_by_group[group_id].append(record)
                except json.JSONDecodeError:
                    continue
        
        total_cards = sum(len(cards) for cards in s2_cards_by_group.values())
        print(f"✅ Loaded {total_cards} S2 cards from {s2_path} ({len(s2_cards_by_group)} groups)")
        return s2_cards_by_group
    
    except Exception as e:
        print(f"❌ Error loading S2 cards: {e}")
        return {}


def load_s4_manifest(base_dir: Path, run_tag: str, arm: str) -> Dict[Tuple[str, Optional[str], Optional[str]], Path]:
    """
    s4_image_manifest.jsonl에서 이미지 경로를 로드합니다.
    
    Returns:
        Dict[(group_id, entity_id/role, cluster_id), image_path]
    """
    manifest_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"s4_image_manifest__arm{arm}.jsonl"
    
    if not manifest_path.exists():
        print(f"⚠️  Warning: S4 manifest not found: {manifest_path}")
        return {}
    
    manifest = {}
    try:
        images_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag / "images"
        
        with open(manifest_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    record = json.loads(line)
                    group_id = record.get("group_id")
                    spec_kind = record.get("spec_kind", "")
                    filename = record.get("filename")
                    
                    if not filename:
                        continue
                    
                    image_path = images_dir / filename
                    if not image_path.exists():
                        continue
                    
                    # Key format: (group_id, entity_id/card_role or "TABLE", cluster_id)
                    if spec_kind == "S1_TABLE_VISUAL":
                        cluster_id = record.get("cluster_id")
                        key = (group_id, "TABLE", cluster_id)
                    else:
                        entity_id = record.get("entity_id")
                        card_role = record.get("card_role")
                        key = (group_id, f"{entity_id}_{card_role}", None)
                    
                    manifest[key] = image_path
                except json.JSONDecodeError:
                    continue
        
        print(f"✅ Loaded {len(manifest)} images from S4 manifest")
        return manifest
    
    except Exception as e:
        print(f"❌ Error loading S4 manifest: {e}")
        return {}


# =========================
# Request Builder
# =========================

def build_s1_table_validation_request(
    key: str,
    group_id: str,
    s1_table: Dict[str, Any],
    infographic_path: Optional[Path],
    prompt_bundle: Dict[str, Any],
) -> Dict[str, Any]:
    """
    S1 table validation 요청을 빌드합니다.
    
    Returns:
        {
            "key": "s1_G001",
            "request": {
                "contents": [...],
                "config": {
                    "system_instruction": {...},
                    "temperature": 0.2,
                    "tools": [{"google_search": {}}],
                    "response_mime_type": "application/json",
                    "response_schema": {...}
                }
            }
        }
    """
    # Extract S1 table data
    master_table = s1_table.get("master_table_markdown_kr", "")
    objective_bullets_raw = s1_table.get("objective_bullets", "")
    
    # Convert objective_bullets to string if it's a list
    if isinstance(objective_bullets_raw, list):
        objective_bullets = "\n".join(f"- {obj}" for obj in objective_bullets_raw)
    else:
        objective_bullets = str(objective_bullets_raw) if objective_bullets_raw else ""
    
    # Load prompts
    system_prompt = prompt_bundle["prompts"].get("S5_SYSTEM", "")
    user_prompt_template = prompt_bundle["prompts"].get("S5_USER_TABLE", "")
    
    # Fill user prompt
    user_prompt = user_prompt_template.replace("{objective_bullets}", objective_bullets or "N/A")
    user_prompt = user_prompt.replace("{master_table_markdown_kr}", master_table or "N/A")
    
    # Build request contents
    contents = []
    parts = [{"text": user_prompt}]
    
    # Add infographic image if available
    if infographic_path and infographic_path.exists():
        try:
            with open(infographic_path, "rb") as f:
                image_bytes = f.read()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": image_b64
                }
            })
        except Exception as e:
            print(f"⚠️  Warning: Failed to load infographic {infographic_path}: {e}")
    
    contents.append({
        "parts": parts,
        "role": "user"
    })
    
    # Build response schema (S1 table validation)
    # Detailed schema to prevent model from putting all data in severity field
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "blocking_error": {
                "type": "BOOLEAN",
                "description": "True if safety-critical medical error exists"
            },
            "technical_accuracy": {
                "type": "NUMBER",
                "description": "0.0, 0.5, or 1.0"
            },
            "educational_quality": {
                "type": "INTEGER",
                "description": "1 to 5"
            },
            "issues": {
                "type": "ARRAY",
                "description": "Maximum 10 issues, most important first",
                "maxItems": 10,
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "severity": {
                            "type": "STRING",
                            "description": "blocking, warning, or minor"
                        },
                        "type": {
                            "type": "STRING",
                            "description": "Issue type code"
                        },
                        "description": {
                            "type": "STRING",
                            "description": "Concise issue description (max 200 chars)",
                            "maxLength": 500
                        },
                        "row_index": {
                            "type": "INTEGER",
                            "description": "0-based row index"
                        },
                        "entity_name": {
                            "type": "STRING",
                            "description": "Entity name from table"
                        },
                        "suggested_fix": {
                            "type": "STRING",
                            "description": "Brief fix suggestion"
                        }
                    },
                    "required": ["severity", "description"]
                }
            },
            "rag_evidence": {
                "type": "ARRAY",
                "description": "Only for blocking errors (max 3 entries)",
                "maxItems": 3,
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "source_id": {"type": "STRING"},
                        "source_excerpt": {"type": "STRING", "description": "Max 200 chars", "maxLength": 500},
                        "relevance": {"type": "STRING", "description": "high, medium, or low"}
                    }
                }
            }
        },
        "required": ["blocking_error", "technical_accuracy", "educational_quality", "issues"]
    }
    
    # Build request with proper Batch API JSONL format
    # Ref: Batch.md lines 122-123, 932
    return {
        "key": key,
        "request": {
            "contents": contents,
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "generation_config": {
                "temperature": S5_TEMPERATURE,
                "response_mime_type": "application/json",
                "response_schema": response_schema,
                "max_output_tokens": S5_MAX_OUTPUT_TOKENS_PRO,  # Pro model: 32768 tokens for large S1 responses
                "stop_sequences": ["</end>"],  # Add stop sequence to prevent runaway generation
                "top_p": 0.95,  # Nucleus sampling to reduce repetition
                "top_k": 40  # Top-k sampling to prevent repetition loops
            },
            "tools": [{"google_search": {}}]  # RAG enabled
        }
    }


def build_s2_card_validation_request(
    key: str,
    group_id: str,
    entity_id: str,
    card: Dict[str, Any],
    prompt_bundle: Dict[str, Any],
) -> Dict[str, Any]:
    """
    S2 card validation 요청을 빌드합니다.
    
    Returns:
        Same format as build_s1_table_validation_request
    """
    # Extract card data
    card_type = card.get("card_type", "")
    card_role = card.get("card_role", "")
    card_text = card.get("card_text_kr", "") or card.get("text_kr", "")
    
    # Load prompts
    system_prompt = prompt_bundle["prompts"].get("S5_SYSTEM", "")
    user_prompt_template = prompt_bundle["prompts"].get("S5_USER_CARD", "")
    
    # Fill user prompt
    user_prompt = user_prompt_template.replace("{card_type}", card_type)
    user_prompt = user_prompt.replace("{card_role}", card_role)
    user_prompt = user_prompt.replace("{card_text_kr}", card_text or "N/A")
    
    # Build request contents
    contents = [{
        "parts": [{"text": user_prompt}],
        "role": "user"
    }]
    
    # Build response schema (S2 card validation)
    # Detailed schema to prevent model from putting all data in severity field
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "blocking_error": {
                "type": "BOOLEAN",
                "description": "True if safety-critical medical error exists"
            },
            "content_accuracy": {
                "type": "NUMBER",
                "description": "0.0, 0.5, or 1.0"
            },
            "clarity": {
                "type": "INTEGER",
                "description": "1 to 5"
            },
            "issues": {
                "type": "ARRAY",
                "description": "Maximum 5 issues, most important first",
                "maxItems": 5,
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "severity": {
                            "type": "STRING",
                            "description": "blocking, warning, or minor"
                        },
                        "type": {
                            "type": "STRING",
                            "description": "Issue type code"
                        },
                        "description": {
                            "type": "STRING",
                            "description": "Concise issue description (max 150 chars)"
                        }
                    },
                    "required": ["severity", "description"]
                }
            }
        },
        "required": ["blocking_error", "content_accuracy", "clarity", "issues"]
    }
    
    # Build request with proper Batch API JSONL format
    # Ref: Batch.md lines 122-123, 932
    return {
        "key": key,
        "request": {
            "contents": contents,
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "generation_config": {
                "temperature": S5_TEMPERATURE,
                "response_mime_type": "application/json",
                "response_schema": response_schema,
                "max_output_tokens": S5_MAX_OUTPUT_TOKENS_FLASH,  # Flash model: 8192 tokens for S2 responses
                "top_p": 0.95,
                "top_k": 40
            },
            "tools": [{"google_search": {}}]  # RAG enabled
        }
    }


def build_batch_requests(
    base_dir: Path,
    run_tag: str,
    arm: str,
    mode: str = "full",
    s1_arm: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    S5 배치 요청 리스트를 빌드합니다.
    
    Args:
        base_dir: 프로젝트 베이스 디렉토리
        run_tag: 실행 태그
        arm: Arm 식별자
        mode: "s1_only" | "s2_only" | "full"
        s1_arm: S1 arm (S1/S2 split arms인 경우)
    
    Returns:
        List of request dicts with metadata
    """
    # Load data
    s1_tables = {}
    s2_cards_by_group = {}
    s4_manifest = {}
    
    if mode in ("s1_only", "full"):
        s1_tables = load_s1_tables(base_dir, run_tag, arm)
        s4_manifest = load_s4_manifest(base_dir, run_tag, arm)
    
    if mode in ("s2_only", "full"):
        s2_cards_by_group = load_s2_cards(base_dir, run_tag, arm, s1_arm)
    
    # Load prompt bundle
    if load_prompt_bundle is None:
        print("❌ Error: load_prompt_bundle not available")
        return []
    
    prompt_bundle = load_prompt_bundle(str(base_dir))
    if not prompt_bundle:
        print("❌ Error: Failed to load prompt bundle")
        return []
    
    # Build requests
    requests = []
    
    # S1 table requests
    if mode in ("s1_only", "full"):
        for group_id, s1_table in s1_tables.items():
            # Check for infographic (non-clustered)
            infographic_path = s4_manifest.get((group_id, "TABLE", None))
            
            key = f"s1_{group_id}"
            request = build_s1_table_validation_request(
                key=key,
                group_id=group_id,
                s1_table=s1_table,
                infographic_path=infographic_path,
                prompt_bundle=prompt_bundle,
            )
            
            # Add metadata for tracking
            request["metadata"] = {
                "group_id": group_id,
                "entity_id": None,
                "validation_type": "s1_table",
                "has_infographic": infographic_path is not None,
            }
            
            requests.append(request)
    
    # S2 card requests
    if mode in ("s2_only", "full"):
        for group_id, cards in s2_cards_by_group.items():
            for card in cards:
                entity_id = card.get("entity_id", "")
                card_id = card.get("card_id", "")
                
                key = f"s2_{group_id}_{card_id}"
                request = build_s2_card_validation_request(
                    key=key,
                    group_id=group_id,
                    entity_id=entity_id,
                    card=card,
                    prompt_bundle=prompt_bundle,
                )
                
                # Add metadata for tracking
                request["metadata"] = {
                    "group_id": group_id,
                    "entity_id": entity_id,
                    "card_id": card_id,
                    "validation_type": "s2_card",
                }
                
                requests.append(request)
    
    print(f"✅ Built {len(requests)} validation requests (mode: {mode})")
    return requests


# =========================
# Token-based Batch Splitting
# =========================

def split_requests_by_token_limit(
    requests: List[Dict[str, Any]],
    token_limit: int = TIER1_BATCH_TOKEN_LIMIT,
    safe_margin: float = 0.9,
) -> List[List[Dict[str, Any]]]:
    """
    요청 리스트를 토큰 한도에 맞춰 자동으로 배치로 분할합니다.
    
    Args:
        requests: 요청 리스트
        token_limit: 토큰 한도
        safe_margin: 안전 마진 (기본: 0.9 = 90%)
    
    Returns:
        분할된 배치 리스트
    """
    safe_limit = int(token_limit * safe_margin)
    batches: List[List[Dict[str, Any]]] = []
    current_batch: List[Dict[str, Any]] = []
    current_tokens = 0
    
    for request in requests:
        # Estimate tokens for this request
        metadata = request.get("metadata", {})
        validation_type = metadata.get("validation_type", "")
        
        if validation_type == "s1_table":
            # Estimate S1 tokens (rough estimate)
            tokens = 8000  # Conservative estimate for S1 + infographic
        elif validation_type == "s2_card":
            # Estimate S2 tokens
            tokens = 2000  # Conservative estimate for S2 card
        else:
            tokens = 3000  # Default
        
        # Check if adding this request would exceed limit
        if current_tokens + tokens > safe_limit and current_batch:
            # Save current batch and start new one
            batches.append(current_batch)
            current_batch = [request]
            current_tokens = tokens
        else:
            # Add to current batch
            current_batch.append(request)
            current_tokens += tokens
    
    # Add final batch
    if current_batch:
        batches.append(current_batch)
    
    return batches


# =========================
# File Upload and Batch Creation
# =========================

def upload_batch_file(
    requests: List[Dict[str, Any]],
    api_key: str,
    display_name: Optional[str] = None,
) -> Optional[str]:
    """
    요청 리스트를 JSONL 파일로 업로드합니다.
    
    Returns:
        File URI (e.g., "https://generativelanguage.googleapis.com/v1beta/files/xxx")
    """
    if not GEMINI_AVAILABLE:
        print("❌ Error: google.genai not available")
        return None
    
    try:
        # Create client
        client = genai.Client(api_key=api_key)
        
        # Build JSONL content
        jsonl_lines = []
        for request in requests:
            jsonl_lines.append(json.dumps(request, ensure_ascii=False))
        jsonl_content = "\n".join(jsonl_lines).encode("utf-8")
        
        # Debug: Save JSONL locally for inspection
        debug_path = Path("/tmp/batch_s5_debug.jsonl")
        with open(debug_path, "wb") as f:
            f.write(jsonl_content)
        print(f"🔍 Debug: Saved JSONL to {debug_path}")
        
        # Upload file
        print(f"📤 Uploading batch file ({len(requests)} requests, {len(jsonl_content)} bytes)...")
        
        if display_name is None:
            display_name = f"s5_validation_batch_{int(time.time())}"
        
        # Use files.upload() API
        uploaded_file = client.files.upload(
            file=io.BytesIO(jsonl_content),
            config={
                "display_name": f"{display_name}.jsonl",
                "mime_type": "application/jsonl"
            }
        )
        
        file_uri = uploaded_file.name if hasattr(uploaded_file, 'name') else None
        if not file_uri:
            print("❌ Error: File uploaded but no URI returned")
            return None
        
        print(f"✅ File uploaded successfully: {file_uri}")
        return file_uri
    
    except Exception as e:
        print(f"❌ Error uploading file: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_batch_job(
    file_uri: str,
    model: str,
    display_name: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    업로드된 파일로 배치 작업을 생성합니다.
    
    Returns:
        배치 작업 정보 또는 None
    """
    if not GEMINI_AVAILABLE:
        print("❌ Error: google.genai not available")
        return None
    
    try:
        # Create client
        if api_key is None:
            api_key = os.getenv(GEMINI_API_KEY_ENV, "").strip()
            if not api_key:
                print(f"❌ Error: Missing API key ({GEMINI_API_KEY_ENV})")
                return None
        
        client = genai.Client(api_key=api_key)
        
        print(f"🚀 Creating batch job...")
        print(f"   Model: {model}")
        print(f"   Input file: {file_uri}")
        
        if display_name is None:
            display_name = f"s5_validation_{int(time.time())}"
        
        # Create batch job
        batch_job = client.batches.create(
            model=model,
            src=file_uri,
            config={
                'display_name': display_name,
            }
        )
        
        batch_id = batch_job.name if hasattr(batch_job, 'name') else None
        if not batch_id:
            print("❌ Error: Batch job created but no ID returned")
            return None
        
        print(f"✅ Batch job created successfully")
        print(f"   Batch ID: {batch_id}")
        
        return {
            "name": batch_id,
            "state": batch_job.state if hasattr(batch_job, 'state') else None,
            "display_name": display_name,
        }
    
    except Exception as e:
        error_str = str(e)
        
        # Classify errors (similar to S4 pattern)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            print(f"❌ Error: 429 RESOURCE_EXHAUSTED (quota exceeded)")
            raise ValueError("429_QUOTA_EXHAUSTED") from e
        elif "404" in error_str or "NOT_FOUND" in error_str:
            print(f"❌ Error: 404 NOT_FOUND (file not accessible)")
            raise ValueError("404_NOT_FOUND") from e
        elif "503" in error_str or "SERVICE_UNAVAILABLE" in error_str:
            print(f"❌ Error: 503 SERVICE_UNAVAILABLE")
            raise ValueError("503_SERVICE_UNAVAILABLE") from e
        else:
            print(f"❌ Error creating batch job: {e}")
            import traceback
            traceback.print_exc()
            raise ValueError("UNKNOWN_ERROR") from e


def check_batch_status(
    batch_id: str,
    api_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """배치 작업의 현재 상태를 조회합니다."""
    if not GEMINI_AVAILABLE:
        return None
    
    try:
        if api_key is None:
            api_key = os.getenv(GEMINI_API_KEY_ENV, "").strip()
            if not api_key:
                return None
        
        client = genai.Client(api_key=api_key)
        batch_job = client.batches.get(name=batch_id)
        
        state_name = batch_job.state.name if hasattr(batch_job.state, 'name') else str(batch_job.state)
        
        result = {
            "name": batch_id,
            "state": state_name,
            "display_name": getattr(batch_job, 'display_name', None),
        }
        
        # Add destination file if succeeded
        if state_name == 'JOB_STATE_SUCCEEDED' and hasattr(batch_job, 'dest') and batch_job.dest is not None:
            if hasattr(batch_job.dest, 'file_name') and batch_job.dest.file_name:
                result["dest_file_name"] = batch_job.dest.file_name
        
        return result
    
    except Exception as e:
        error_str = str(e)
        if "404" in error_str or "NOT_FOUND" in error_str:
            return None
        if "400" in error_str or "INVALID_ARGUMENT" in error_str:
            return None
        print(f"❌ Error checking batch status: {e}")
        return None


def download_batch_results(file_name: str, api_key: Optional[str] = None) -> Optional[bytes]:
    """배치 결과 파일을 다운로드합니다."""
    if not GEMINI_AVAILABLE:
        return None
    
    try:
        if api_key is None:
            api_key = os.getenv(GEMINI_API_KEY_ENV, "").strip()
            if not api_key:
                return None
        
        client = genai.Client(api_key=api_key)
        
        # Download file - correct parameter is 'file' not 'name'
        result_bytes = client.files.download(file=file_name)
        return result_bytes
    
    except Exception as e:
        print(f"❌ Error downloading results: {e}")
        return None


# =========================
# Result Parsing
# =========================

def parse_batch_results(result_content: bytes) -> List[Dict[str, Any]]:
    """
    배치 결과 JSONL을 파싱하여 validation 데이터 추출.
    
    Returns:
        List of dicts with keys: 'key', 'validation', 'error'
    """
    results = []
    
    try:
        # Incremental decode + line iteration
        bio = io.BytesIO(result_content)
        with io.TextIOWrapper(bio, encoding="utf-8", errors="replace", newline="") as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                
                try:
                    parsed_response = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"⚠️  Warning: Failed to parse result line {line_num}: {e}")
                    continue
                
                key = parsed_response.get("key", "")
                validation = None
                error = None
                
                # Extract validation JSON from response
                if parsed_response.get("response"):
                    response = parsed_response["response"]
                    candidates = response.get("candidates") or []
                    if candidates:
                        candidate = candidates[0] or {}
                        content = candidate.get("content") or {}
                        parts = content.get("parts") or []
                        for part in parts:
                            if not isinstance(part, dict):
                                continue
                            text = part.get("text")
                            if text:
                                try:
                                    validation = json.loads(text)
                                    break
                                except json.JSONDecodeError:
                                    pass
                
                # Check for errors
                if parsed_response.get("error"):
                    error = parsed_response["error"]
                
                results.append({
                    "key": key,
                    "validation": validation,
                    "error": error,
                })
        
        return results
    
    except Exception as e:
        print(f"❌ Error parsing batch results: {e}")
        import traceback
        traceback.print_exc()
        return []


def merge_to_s5_validation(
    base_dir: Path,
    run_tag: str,
    arm: str,
    results: List[Dict[str, Any]],
) -> bool:
    """
    배치 결과를 s5_validation__armX.jsonl에 병합합니다.
    
    Args:
        base_dir: 프로젝트 베이스 디렉토리
        run_tag: 실행 태그
        arm: Arm 식별자
        results: 파싱된 배치 결과
    
    Returns:
        True if successful
    """
    output_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"s5_validation__arm{arm}.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing s5_validation records
    existing_records: Dict[str, Dict[str, Any]] = {}
    if output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        group_id = record.get("group_id")
                        if group_id:
                            existing_records[group_id] = record
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"⚠️  Warning: Error loading existing s5_validation: {e}")
    
    # Merge results
    merged_count = 0
    error_count = 0
    
    for result in results:
        key = result.get("key", "")
        validation = result.get("validation")
        error = result.get("error")
        
        if not key:
            continue
        
        # Parse key to extract group_id, entity_id, card_id
        if key.startswith("s1_"):
            # S1 table validation
            group_id = key.replace("s1_", "")
            
            if group_id not in existing_records:
                existing_records[group_id] = {
                    "group_id": group_id,
                    "run_tag": run_tag,
                    "arm": arm,
                }
            
            if validation:
                existing_records[group_id]["s1_table_validation"] = validation
                merged_count += 1
            elif error:
                existing_records[group_id]["s1_table_error"] = error
                error_count += 1
        
        elif key.startswith("s2_"):
            # S2 card validation
            parts = key.replace("s2_", "").split("_", 1)
            if len(parts) < 2:
                continue
            group_id = parts[0]
            card_id = parts[1]
            
            if group_id not in existing_records:
                existing_records[group_id] = {
                    "group_id": group_id,
                    "run_tag": run_tag,
                    "arm": arm,
                }
            
            # Initialize s2_cards_validation if needed
            if "s2_cards_validation" not in existing_records[group_id]:
                existing_records[group_id]["s2_cards_validation"] = {"cards": []}
            
            # Add card validation
            card_validation = {
                "card_id": card_id,
            }
            if validation:
                card_validation.update(validation)
                merged_count += 1
            elif error:
                card_validation["error"] = error
                error_count += 1
            
            existing_records[group_id]["s2_cards_validation"]["cards"].append(card_validation)
    
    # Write merged records
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            for group_id in sorted(existing_records.keys()):
                record = existing_records[group_id]
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        
        print(f"✅ Merged {merged_count} validation results to {output_path}")
        if error_count > 0:
            print(f"⚠️  {error_count} results had errors")
        return True
    
    except Exception as e:
        print(f"❌ Error writing s5_validation: {e}")
        import traceback
        traceback.print_exc()
        return False


# =========================
# CLI and Main Execution
# =========================

def initialize_api_key_rotator(base_dir: Path) -> Optional[Any]:
    """ApiKeyRotator를 초기화합니다."""
    global _global_rotator
    
    if not ROTATOR_AVAILABLE:
        return None
    
    try:
        if ApiKeyRotator is None:
            return None
        
        # Force reload .env file
        env_path = base_dir / ".env"
        if env_path.exists():
            keys_to_remove = [k for k in os.environ.keys() if k.startswith("GOOGLE_API_KEY_")]
            for key in keys_to_remove:
                os.environ.pop(key, None)
            load_dotenv(dotenv_path=env_path, override=True)
        
        # Create rotator
        _global_rotator = ApiKeyRotator(base_dir=base_dir, key_prefix="GOOGLE_API_KEY")
        if _global_rotator is not None and _global_rotator.keys:
            current_key_number = _global_rotator.key_numbers[_global_rotator._current_index]
            print(f"🔑 API KEY: Using key index {_global_rotator._current_index} (GOOGLE_API_KEY_{current_key_number})")
            print(f"   Total keys loaded: {len(_global_rotator.keys)}")
        return _global_rotator
    except Exception as e:
        print(f"⚠️  Warning: Failed to initialize API key rotator: {e}")
        return None


def main():
    """메인 실행 함수."""
    parser = argparse.ArgumentParser(description="Batch S5 Validator using Gemini Batch API")
    parser.add_argument(
        "--base_dir",
        type=str,
        default=".",
        help="Base directory (default: current directory)",
    )
    parser.add_argument(
        "--run_tag",
        type=str,
        help="Run tag",
    )
    parser.add_argument(
        "--arm",
        type=str,
        help="Arm identifier (A, B, C, D, E, F, G)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["s1_only", "s2_only", "full"],
        default="s1_only",
        help="Validation mode (default: s1_only)",
    )
    parser.add_argument(
        "--s1_arm",
        type=str,
        help="S1 arm (for S1/S2 split arms)",
    )
    parser.add_argument(
        "--check_status",
        action="store_true",
        help="Check status of all tracked batches",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume mode: retry failed batches",
    )
    parser.add_argument(
        "--batch_id",
        type=str,
        help="Check status of a specific batch ID",
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    base_dir = Path(args.base_dir).resolve()
    
    # Initialize API key rotator
    rotator = initialize_api_key_rotator(base_dir)
    
    # Load tracking file
    tracking_path = get_batch_tracking_file_path(base_dir)
    tracking_data = load_batch_tracking_file(tracking_path)
    
    # --check_status mode
    if args.check_status:
        print("=" * 60)
        print("S5 Batch Status Check")
        print("=" * 60)
        
        batches = tracking_data.get("batches", {})
        if not batches:
            print("No batches found in tracking file")
            return
        
        # Check each batch
        for api_key_str, api_batches in batches.items():
            chunks = api_batches.get("chunks", [])
            run_tag = api_batches.get("run_tag", "")
            
            # Filter by batch_id if specified
            if args.batch_id:
                chunks = [c for c in chunks if args.batch_id in c.get("batch_id", "")]
                if not chunks:
                    continue
            
            print(f"\n{api_key_str}:")
            print(f"  Run tag: {run_tag}")
            print(f"  Total batches: {len(chunks)}")
            
            for chunk in chunks:
                batch_id = chunk.get("batch_id", "")
                status = chunk.get("status", "")
                mode = chunk.get("mode", "")
                num_requests = chunk.get("num_requests", 0)
                
                short_id = batch_id.split("/")[-1][:20] if "/" in batch_id else batch_id[:20]
                
                # Check current status - try with all available API keys
                status_info = None
                working_api_key = None
                if rotator:
                    for key_idx, api_key in enumerate(rotator.keys):
                        try:
                            status_info = check_batch_status(batch_id, api_key=api_key)
                            if status_info:
                                working_api_key = api_key
                                break
                        except Exception:
                            continue
                
                if status_info:
                    current_status = status_info.get("state", status)
                    # Update tracking file
                    if current_status != status:
                        chunk["status"] = current_status
                        save_batch_tracking_file(tracking_path, tracking_data)
                    
                    print(f"  Batch: {short_id}")
                    print(f"    Status: {current_status}")
                    print(f"    Mode: {mode}")
                    print(f"    Requests: {num_requests}")
                    
                    # Download and merge if succeeded
                    if current_status == "JOB_STATE_SUCCEEDED" and "dest_file_name" in status_info:
                        dest_file_name = status_info["dest_file_name"]
                        arm = chunk.get("arm", "")
                        
                        # Download results - use the same API key that successfully checked status
                        print(f"    📥 Downloading results...")
                        result_content = download_batch_results(dest_file_name, api_key=working_api_key)
                        
                        if result_content:
                            # Debug: Save RAW batch response first
                            raw_debug_path = base_dir / "2_Data" / "metadata" / f".batch_s5_raw_{batch_id.split('/')[-1][:10]}.jsonl"
                            try:
                                with open(raw_debug_path, "wb") as f:
                                    f.write(result_content)
                                print(f"    🔍 Debug: Saved RAW batch response to {raw_debug_path.name}")
                            except Exception as e:
                                print(f"    ⚠️  Raw debug save failed: {e}")
                            
                            # Parse results
                            results = parse_batch_results(result_content)
                            print(f"    ✅ Parsed {len(results)} results")
                            
                            # Debug: Save parsed results
                            debug_path = base_dir / "2_Data" / "metadata" / f".batch_s5_results_debug_{batch_id.split('/')[-1][:10]}.jsonl"
                            try:
                                with open(debug_path, "w", encoding="utf-8") as f:
                                    for result in results:
                                        f.write(json.dumps(result, ensure_ascii=False) + "\n")
                                print(f"    🔍 Debug: Saved parsed results to {debug_path.name}")
                            except Exception as e:
                                print(f"    ⚠️  Debug save failed: {e}")
                            
                            # Merge to s5_validation
                            merge_success = merge_to_s5_validation(base_dir, run_tag, arm, results)
                            if merge_success:
                                print(f"    ✅ Merged to s5_validation__arm{arm}.jsonl")
                        else:
                            print(f"    ❌ Failed to download results")
                else:
                    print(f"  Batch: {short_id}")
                    print(f"    Status: {status} (not found with any API key)")
        
        return
    
    # Normal mode: create new batch
    if not args.run_tag or not args.arm:
        print("❌ Error: --run_tag and --arm are required (or use --check_status)")
        parser.print_help()
        return
    
    run_tag = args.run_tag
    arm = args.arm
    mode = args.mode
    s1_arm = args.s1_arm
    
    print(f"🏷️  Run tag: {run_tag}")
    print(f"🔤 Arm: {arm}")
    print(f"📋 Mode: {mode}")
    
    # Build requests
    requests = build_batch_requests(base_dir, run_tag, arm, mode, s1_arm)
    
    if not requests:
        print("❌ Error: No requests to process")
        return
    
    # Split into batches by token limit
    batches = split_requests_by_token_limit(requests)
    
    print(f"\n📦 Split into {len(batches)} batch(es)")
    for i, batch in enumerate(batches):
        print(f"   Batch {i+1}: {len(batch)} requests")
    
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
    for chunk_index, batch_requests in enumerate(batches):
        print(f"\n{'='*60}")
        print(f"Processing Batch {chunk_index + 1}/{len(batches)}")
        print(f"{'='*60}")
        
        # Determine model based on mode
        if mode == "s1_only":
            model = S5_S1_TABLE_MODEL
        elif mode == "s2_only":
            model = S5_S2_CARD_MODEL
        else:
            # Mixed mode: use Pro model (more capable)
            model = S5_S1_TABLE_MODEL
        
        # Upload file
        file_uri = upload_batch_file(
            batch_requests,
            api_key=api_key,
            display_name=f"s5_{run_tag}_{arm}_{mode}_chunk{chunk_index}",
        )
        
        if not file_uri:
            print(f"❌ Failed to upload batch file for chunk {chunk_index}")
            continue
        
        # Create batch job
        try:
            batch_info = create_batch_job(
                file_uri=file_uri,
                model=model,
                display_name=f"s5_{run_tag}_{arm}_{mode}_chunk{chunk_index}",
                api_key=api_key,
            )
            
            if not batch_info:
                print(f"❌ Failed to create batch job for chunk {chunk_index}")
                continue
            
            batch_id = batch_info["name"]
            
            # Save to tracking file
            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            
            if api_key_hash not in tracking_data["batches"]:
                tracking_data["batches"][api_key_hash] = {
                    "run_tag": run_tag,
                    "chunks": [],
                }
            
            # Extract metadata from requests
            prompts_metadata = []
            for req in batch_requests:
                meta = req.get("metadata", {})
                prompts_metadata.append({
                    "key": req.get("key", ""),
                    "group_id": meta.get("group_id", ""),
                    "entity_id": meta.get("entity_id", ""),
                    "validation_type": meta.get("validation_type", ""),
                })
            
            tracking_data["batches"][api_key_hash]["chunks"].append({
                "batch_id": batch_id,
                "status": batch_info["state"],
                "mode": mode,
                "arm": arm,
                "num_requests": len(batch_requests),
                "prompts_metadata": prompts_metadata,
                "created_at": datetime.now().isoformat(),
                "chunk_index": chunk_index,
            })
            
            save_batch_tracking_file(tracking_path, tracking_data)
            
            print(f"✅ Batch {chunk_index + 1} created successfully")
            print(f"   Batch ID: {batch_id}")
        
        except ValueError as e:
            error_msg = str(e)
            if "429_QUOTA_EXHAUSTED" in error_msg:
                print(f"⚠️  Quota exhausted, rotating API key...")
                if rotator:
                    new_key, new_index = rotator.rotate_on_quota_exhausted()
                    api_key = new_key
                    print(f"   Switched to key index {new_index}")
                    # Retry this batch with new key
                    # (In production, you'd want more sophisticated retry logic)
                else:
                    print(f"❌ No rotator available, cannot retry")
                    break
            elif "404_NOT_FOUND" in error_msg:
                print(f"⚠️  File not accessible, re-uploading with new key...")
                if rotator:
                    new_key, new_index = rotator.rotate_on_quota_exhausted()
                    api_key = new_key
                    # Retry upload and batch creation
                else:
                    print(f"❌ No rotator available, cannot retry")
                    break
            else:
                print(f"❌ Error creating batch: {error_msg}")
                break
    
    print(f"\n{'='*60}")
    print(f"✅ Batch submission completed")
    print(f"   Total batches: {len(batches)}")
    print(f"   Use --check_status to monitor progress")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()


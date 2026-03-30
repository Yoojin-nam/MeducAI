#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MeducAI - Batch Medical Term Translation (via Gemini Batch API)

이 스크립트는 한글 의료용어를 영어로 번역합니다.
Google Gemini Batch API를 사용하여 비용 절감(50%) 및 RPM/RPD 제한 우회를 달성합니다.

Usage:
    # Submit batch for translation
    python batch_medterm_translation.py \
        --input /path/to/s2_results.jsonl \
        --output /path/to/s2_results_translated.jsonl \
        --submit
    
    # Check status
    python batch_medterm_translation.py --check_status
    
    # Download results and apply
    python batch_medterm_translation.py \
        --input /path/to/s2_results.jsonl \
        --output /path/to/s2_results_translated.jsonl \
        --download_and_apply

Requirements:
    - google-genai>=1.56.0
    - GOOGLE_API_KEY environment variable
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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
except Exception as e:
    print(f"Warning: Could not import ApiKeyRotator: {e}")

# Global rotator instance
_global_rotator: Optional[Any] = None

# =========================
# Configuration
# =========================

# Model for translation
TRANSLATE_MODEL = "gemini-2.5-flash"  # Batch API 지원, 빠름, 저렴

# Temperature (low for consistency)
TRANSLATE_TEMPERATURE = 0.2

# Max output tokens
TRANSLATE_MAX_OUTPUT_TOKENS = 16384

# Tier 1 Batch Token Limit (conservative: use 1.5M to leave buffer)
TIER1_BATCH_TOKEN_LIMIT = 1_500_000

# Approximate chars per token (for estimation)
CHARS_PER_TOKEN = 4

# Simplified prompt (from translate_medical_terms_module.py)
SYSTEM_PROMPT = """
You are a medical translator for Korean radiology board exams.

CRITICAL: Do NOT summarize, delete, or shorten content.
Preserve meaning, line breaks, bullets, numbering, and section headers exactly.

GOAL: Translate ONLY specific medical terminology to English. Keep general words, sentence structure, and formatting in Korean.
This applies to ALL fields: front, back (including 근거/오답 포인트), and options.

═══════════════════════════════════════════════════════════════════

RULE 1: WHAT TO TRANSLATE ✅

Translate these medical terms to English:
• Diseases: 폐렴→pneumonia, 뇌경색→cerebral infarction, 간경화→liver cirrhosis
• Organs: 간→liver, 폐→lung, 심장→heart, 신장→kidney, 췌장→pancreas, 위→stomach
• Anatomy: 문합부→anastomosis, 장간막→mesentery, 기저핵→basal ganglia, 송과체→pineal gland, 맥락총→choroid plexus, 담창구→globus pallidus, 시상→thalamus
• Findings: 저음영→low attenuation, 고음영→high attenuation, 조영증강→enhancement, 석회화→calcification
• Procedures: 위절제술→gastrectomy, 혈관조영술→angiography
• Very common terms (do NOT leave in Korean):
  - 초음파→ultrasound
  - 유방 촬영술→mammography
  - 핵의학→nuclear medicine
  - 하대정맥→inferior vena cava
  - 뇌척수액→cerebrospinal fluid
  - 총담관→common bile duct
  - 상장간막동맥→superior mesenteric artery
  - 하장간막동맥→inferior mesenteric artery
  - 관전압→tube voltage
  - 골단→epiphysis
  - 혈관종→hemangioma
  - 점액낭→bursa
  - 대전자→greater trochanter
  - 중장→midgut
  - 후장→hindgut
• Also translate: artery/vein/nerve names, syndrome names, medical English terms (mechanism, complication, infarction, thrombosis, etc.)

═══════════════════════════════════════════════════════════════════

RULE 2: WHAT NOT TO TRANSLATE ❌

Keep in Korean:
• General words: 환자, 검사, 진단, 소견, 관찰, 시사, 발생, 특징, 증상
• Actions: 시행, 확인, 발견, 내원
• Structure: 정답, 근거, 오답, 함정/감별, ~의, ~로, ~에서

═══════════════════════════════════════════════════════════════════

RULE 3: MIXED FORMATS (MUST FIX) ✅

This is the #1 quality rule. Many failures happen here.

3A) Korean with English gloss:  "한글(English)" or "한글 (English)"
→ Do NOT output the mixed format. You must normalize it.

Decide which case it is:

CASE A (medical TERM in Korean): the Korean chunk is a medical term (organ/anatomy/disease/procedure/finding).
→ Prefer English term. Remove Korean completely.
  - If the parentheses content is an abbreviation (US/IVC/CSF/CBD/SMA/IMA/SUV/SNR/T1/etc), keep it as "(ABBREV)" after the English for clarity.

CASE B (general Korean phrase + English label/abbrev): the Korean chunk is NOT a medical term (e.g., "...인 경우", "...으로 인한", "...의 시간적 순서", "...의 폭", "…저하").
→ KEEP the Korean phrase (meaning/grammar) and REMOVE the parentheses by placing the English token after the Korean phrase:
  "KoreanPhrase(English)" → "KoreanPhrase English"
  (Do not delete the Korean phrase in this case.)

CASE B-2 (Korean head-noun + English term): if the Korean chunk is a short generic head noun like:
  수술 / 소실 / 저하 / 진단 / 징후 / 소견 / 증후군 / 결손 / 병변 / 파급 / 경로 / 통로
and the parentheses contain the specific English term,
→ Put English first (more natural Korean):
  "HeadNoun(English)" → "English HeadNoun"

Examples (correct):
• "대전자 점액낭(Trochanteric bursa)" → "Trochanteric bursa"
• "중장(Midgut)과 후장(Hindgut)" → "Midgut과 Hindgut"
• "초음파(US)" → "ultrasound (US)"
• "유방 촬영술(Mammography)" → "mammography"
• "하대정맥(IVC)" → "inferior vena cava (IVC)"
• "뇌척수액(CSF)" → "cerebrospinal fluid (CSF)"
• "총담관(CBD)" → "common bile duct (CBD)"
• "상장간막동맥(SMA)" → "superior mesenteric artery (SMA)"
• "급성 장간막 허혈(AMI)" → "acute mesenteric ischemia (AMI)"
• "하장간막동맥(IMA)" → "inferior mesenteric artery (IMA)"
• "영상의 통계적 품질(SNR)" → "영상의 통계적 품질 SNR"
• "영상에서 정량적 분석(SUV)" → "영상에서 정량적 분석 SUV"
• "에 국한된 경우(T1)" → "에 국한된 경우 T1"
• "이 없는 경우(Non-AC)" → "이 없는 경우 Non-AC"
• "수술(Esophagectomy)" → "Esophagectomy 수술"
• "수술(Arterial switch)" → "Arterial switch 수술"
• "소실(Silhouette sign)" → "Silhouette sign 소실"
• "저하(Drug interference)" → "Drug interference 저하"

3B) English with Korean gloss:  "English(한글)" or "English (한글)"
→ REMOVE the Korean in parentheses (do NOT keep Korean in parentheses).
  - If the Korean gloss is important, translate it into English and keep it as English gloss.

Examples (correct):
• "BI-RADS 2(양성)" → "BI-RADS 2 (benign)"
• "HPV(인유두종 바이러스)" → "HPV (human papillomavirus)"
• WRONG: "Kidney(소변)"  (meaning error) ❌
• CORRECT: "Kidney(신장)" → "Kidney (kidney)" or just "Kidney" ✅

3C) Self-check (MANDATORY)
Before outputting, scan your own text and fix ALL occurrences of:
• Korean immediately followed by "(English...)"  → must become CASE A or CASE B normalized form (no parentheses-mix)
• English immediately followed by "(Korean...)"  → must remove Korean parentheses (optionally English gloss)

Keep spacing and particles (은/는/이/가/을/를/의/에서/과/와) intact after the English term.

═══════════════════════════════════════════════════════════════════

RULE 4: CAPITALIZATION (첫글자 대문자)

ALWAYS capitalize the first letter of translated English terms when:
• Start of sentence or field
• After colon (:) → "근거: Pneumonia...", "Answer: Liver cirrhosis"
• After period (.) → "...소견임. Cerebral infarction은..."
• After bullet/number → "* Mesentery의...", "1. Gastrectomy 후..."

Lowercase in mid-sentence: "환자에서 pneumonia 소견이 관찰됨"
Always uppercase: CT, MRI, Billroth II, Roux-en-Y (abbreviations/proper nouns)

═══════════════════════════════════════════════════════════════════

RULE 5: PRESERVE FORMATTING

Keep exactly: line breaks, bullets (*, •), numbering, headers (Answer:, 정답:, 근거:), HTML tags
""".strip()

# Response schema for structured output
TRANSLATION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "translated_front": {"type": "STRING"},
        "translated_back": {"type": "STRING"},
        "translated_options": {
            "type": "ARRAY",
            "items": {"type": "STRING"}
        }
    },
    "required": ["translated_front", "translated_back"]
}

# Tracking file path
def get_tracking_file_path(output_path: Path) -> Path:
    """배치 추적 파일 경로를 반환합니다."""
    return output_path.parent / f".batch_medterm_tracking_{output_path.stem}.json"


# =========================
# Helper Functions
# =========================

def load_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """Load a JSONL file and return list of records."""
    records = []
    if not file_path.exists():
        return records
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                records.append(record)
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse JSON line: {e}", file=sys.stderr)
                continue
    
    return records


def write_jsonl(file_path: Path, records: List[Dict[str, Any]]) -> None:
    """Write records to a JSONL file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        for record in records:
            json_line = json.dumps(record, ensure_ascii=False)
            f.write(json_line + "\n")


def get_record_key(record: Dict[str, Any]) -> str:
    """레코드의 고유 키를 생성합니다."""
    group_id = record.get("group_id", "")
    entity_id = record.get("entity_id", "")
    return f"{group_id}_{entity_id}"


def extract_already_translated(output_path: Path) -> Set[str]:
    """이미 번역된 레코드의 키를 추출합니다."""
    translated = set()
    
    # Check main output file
    if output_path.exists():
        records = load_jsonl(output_path)
        for rec in records:
            translated.add(get_record_key(rec))
    
    # Check .tmp file if exists
    tmp_path = Path(str(output_path) + ".tmp")
    if tmp_path.exists():
        records = load_jsonl(tmp_path)
        for rec in records:
            translated.add(get_record_key(rec))
    
    return translated


# =========================
# Batch Request Builder
# =========================

def build_translation_batch_request(
    record: Dict[str, Any],
    request_idx: int,
) -> Tuple[str, Dict[str, Any]]:
    """
    Build a Gemini Batch API request for medical term translation.
    
    Args:
        record: S2 결과 레코드
        request_idx: 요청 인덱스
        
    Returns:
        (request_key, request_dict)
    """
    group_id = record.get("group_id", "")
    entity_id = record.get("entity_id", "")
    anki_cards = record.get("anki_cards", [])
    
    # 카드 정보 추출
    card_texts = []
    for card in anki_cards:
        card_role = card.get("card_role", "")
        front = card.get("front", "")
        back = card.get("back", "")
        options = card.get("options", [])
        
        card_text = f"[Card: {card_role}]\nFront: {front}\nBack: {back}"
        if options:
            card_text += f"\nOptions: {json.dumps(options, ensure_ascii=False)}"
        card_texts.append(card_text)
    
    combined_text = "\n\n".join(card_texts)
    
    # User prompt
    user_prompt = f"""Translate the medical terms in the following Anki cards from Korean to English.
Each card has front, back, and optionally options.
Return the translated text in JSON format.

INPUT:
{combined_text}

OUTPUT FORMAT:
{{
  "translated_front": "...",
  "translated_back": "...",
  "translated_options": ["...", "..."]  // only if options exist
}}

Apply the translation rules to all fields. Preserve formatting exactly."""

    # Request key (for tracking)
    request_key = f"medterm_{request_idx}_{group_id}_{entity_id}"
    
    # Build request following Batch API format
    request_dict = {
        "key": request_key,
        "request": {
            "contents": [{
                "parts": [{"text": user_prompt}],
                "role": "user"
            }],
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "generation_config": {
                "temperature": TRANSLATE_TEMPERATURE,
                "max_output_tokens": TRANSLATE_MAX_OUTPUT_TOKENS,
                "response_mime_type": "application/json",
                "response_schema": TRANSLATION_SCHEMA
            }
        }
    }
    
    return request_key, request_dict


def estimate_tokens(request_dict: Dict[str, Any]) -> int:
    """Estimate token count for a request."""
    # Serialize to JSON and estimate tokens
    json_str = json.dumps(request_dict, ensure_ascii=False)
    return len(json_str) // CHARS_PER_TOKEN


def split_into_batches(
    batch_requests: List[Dict[str, Any]],
    token_limit: int = TIER1_BATCH_TOKEN_LIMIT,
) -> List[List[Dict[str, Any]]]:
    """
    Split batch requests into multiple batches to stay under token limit.
    
    Args:
        batch_requests: All requests to split
        token_limit: Maximum tokens per batch
        
    Returns:
        List of batches, each batch is a list of requests
    """
    batches = []
    current_batch = []
    current_tokens = 0
    
    for request in batch_requests:
        request_tokens = estimate_tokens(request)
        
        # If adding this request would exceed limit, start new batch
        if current_tokens + request_tokens > token_limit and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0
        
        current_batch.append(request)
        current_tokens += request_tokens
    
    # Don't forget the last batch
    if current_batch:
        batches.append(current_batch)
    
    return batches


def prepare_batch_requests(
    input_path: Path,
    output_path: Path,
    max_records: Optional[int] = None,
    resume: bool = True,
) -> Tuple[List[List[Dict[str, Any]]], Dict[str, Dict[str, Any]]]:
    """
    Prepare batch requests for translation, split by token limit.
    
    Args:
        input_path: 입력 JSONL 파일 경로
        output_path: 출력 JSONL 파일 경로
        max_records: 최대 레코드 수 (테스트용)
        resume: 이미 번역된 레코드 건너뛰기
        
    Returns:
        (batches, record_map)  # batches: list of request lists, record_map: key -> original record
    """
    print(f"[Step 1] Loading input file: {input_path}")
    records = load_jsonl(input_path)
    print(f"  Loaded {len(records)} records")
    
    # Skip already translated
    if resume:
        already_translated = extract_already_translated(output_path)
        if already_translated:
            print(f"  Already translated: {len(already_translated)} records")
            records = [r for r in records if get_record_key(r) not in already_translated]
            print(f"  Remaining to translate: {len(records)} records")
    
    # Limit records if specified
    if max_records and len(records) > max_records:
        print(f"  Limiting to {max_records} records (--max_records)")
        records = records[:max_records]
    
    if not records:
        print("✓ All records already translated. Nothing to do.")
        return [], {}
    
    # Build batch requests
    print(f"\n[Step 2] Building batch requests for {len(records)} records...")
    batch_requests = []
    record_map = {}  # key -> original record
    
    for idx, record in enumerate(records):
        request_key, request_dict = build_translation_batch_request(record, idx)
        batch_requests.append(request_dict)
        record_map[request_key] = record
    
    # Split into batches by token limit
    print(f"\n[Step 2b] Splitting into batches (token limit: {TIER1_BATCH_TOKEN_LIMIT:,})...")
    batches = split_into_batches(batch_requests, TIER1_BATCH_TOKEN_LIMIT)
    
    total_tokens = sum(estimate_tokens(r) for r in batch_requests)
    print(f"  Total requests: {len(batch_requests)}")
    print(f"  Estimated tokens: {total_tokens:,}")
    print(f"  Split into {len(batches)} batch(es)")
    for i, batch in enumerate(batches):
        batch_tokens = sum(estimate_tokens(r) for r in batch)
        print(f"    Batch {i+1}: {len(batch)} requests, ~{batch_tokens:,} tokens")
    
    return batches, record_map


# =========================
# Batch Tracking
# =========================

def load_tracking_file(tracking_path: Path) -> Dict[str, Any]:
    """Load batch tracking file."""
    if not tracking_path.exists():
        return {
            "schema_version": "MEDTERM_BATCH_v1.0",
            "batches": {},
            "failed_requests": [],
            "last_updated": datetime.now().isoformat(),
        }
    
    try:
        with open(tracking_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Warning: Error loading tracking file: {e}")
        return {
            "schema_version": "MEDTERM_BATCH_v1.0",
            "batches": {},
            "failed_requests": [],
            "last_updated": datetime.now().isoformat(),
        }


def save_tracking_file(tracking_path: Path, data: Dict[str, Any]) -> None:
    """Save batch tracking file."""
    tracking_path.parent.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = datetime.now().isoformat()
    with open(tracking_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# =========================
# Batch Operations
# =========================

def get_api_key_with_rotator(base_dir: Optional[Path] = None) -> Optional[str]:
    """
    Get API key using rotator if available, otherwise from environment.
    """
    global _global_rotator
    
    # Determine base_dir
    if base_dir is None:
        base_dir = Path(__file__).resolve().parents[4]  # MeducAI root
    
    # Load .env
    env_path = base_dir / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        load_dotenv()
    
    # Try rotator first
    if ROTATOR_AVAILABLE and ApiKeyRotator:
        try:
            _global_rotator = ApiKeyRotator(base_dir=base_dir)
            api_key = _global_rotator.get_current_key()
            if api_key:
                num_keys = len(_global_rotator.keys)
                current_idx = _global_rotator._current_index
                print(f"[Rotator] Using API key index {current_idx + 1}/{num_keys}")
                return api_key
        except RuntimeError as e:
            # All keys exhausted
            print(f"[Rotator] Error: {e}")
            return None
        except Exception as e:
            print(f"[Rotator] Warning: Rotator failed: {e}")
    
    # Fallback to environment
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        return api_key
    
    # Try numbered keys
    for i in range(1, 20):
        key = os.getenv(f"GOOGLE_API_KEY_{i}")
        if key:
            return key
    
    return None


def submit_batch(
    input_path: Path,
    output_path: Path,
    max_records: Optional[int] = None,
    resume: bool = True,
    base_dir: Optional[Path] = None,
) -> bool:
    """
    Submit batch job(s) for translation.
    May submit multiple batches if requests exceed token limit.
    """
    if not GEMINI_AVAILABLE:
        print("Error: google.genai not available")
        return False
    
    # Determine base_dir
    if base_dir is None:
        base_dir = Path(__file__).resolve().parents[4]  # MeducAI root
    
    # Get API key
    api_key = get_api_key_with_rotator(base_dir)
    if not api_key:
        print("Error: No GOOGLE_API_KEY found in environment")
        return False
    
    # Prepare requests (now returns list of batches)
    batches, record_map = prepare_batch_requests(
        input_path, output_path, max_records, resume
    )
    
    if not batches:
        return True  # Nothing to do
    
    # Process each batch
    tracking_path = get_tracking_file_path(output_path)
    tracking_data = load_tracking_file(tracking_path)
    
    total_batches = len(batches)
    successful_batches = 0
    
    for batch_idx, batch_requests in enumerate(batches):
        print(f"\n{'='*60}")
        print(f"[Batch {batch_idx + 1}/{total_batches}] Processing {len(batch_requests)} requests...")
        print(f"{'='*60}")
        
        # Create JSONL file for this batch
        print(f"\n[Step 3] Creating batch request file...")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        batch_input_file = output_path.parent / f".batch_medterm_input_{timestamp}_part{batch_idx + 1}.jsonl"
        
        with open(batch_input_file, "w", encoding="utf-8") as f:
            for req in batch_requests:
                f.write(json.dumps(req, ensure_ascii=False) + "\n")
        
        print(f"  Created: {batch_input_file}")
        print(f"  Requests: {len(batch_requests)}")
        
        # Upload and submit with key rotation on 429
        # IMPORTANT: File uploads are tied to the API key that uploaded them.
        # If we rotate keys, we must re-upload the file.
        max_retries = len(_global_rotator.keys) if _global_rotator else 3
        batch_job = None
        
        for attempt in range(max_retries):
            # Get current API key
            if _global_rotator:
                api_key = _global_rotator.get_current_key()
                current_idx = getattr(_global_rotator, '_current_index', 0)
                print(f"\n[Attempt {attempt + 1}/{max_retries}] Using API key index {current_idx + 1}")
            
            client = genai.Client(api_key=api_key)
            
            # Step 4: Upload file (must upload with each key since files are key-specific)
            print(f"\n[Step 4] Uploading to Gemini File API...")
            try:
                uploaded_file = client.files.upload(
                    file=str(batch_input_file),
                    config=types.UploadFileConfig(
                        display_name=f"medterm_batch_{timestamp}_part{batch_idx + 1}",
                        mime_type="jsonl"
                    )
                )
                print(f"  Uploaded: {uploaded_file.name}")
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "quota" in error_str.lower():
                    print(f"  ❌ Error 429: Quota exhausted. Rotating API key...")
                    if _global_rotator:
                        try:
                            new_key, new_index = _global_rotator.rotate_on_quota_exhausted(error_str)
                            print(f"  → Rotated to key index {new_index + 1}")
                            api_key = new_key
                            continue
                        except Exception as re:
                            print(f"  ⚠️  Rotation failed: {re}")
                print(f"Error uploading file: {e}")
                if attempt == max_retries - 1:
                    print(f"  ⚠️  Batch {batch_idx + 1} failed, continuing with next batch...")
                    break
                continue
            
            # Step 5: Create batch job
            print(f"\n[Step 5] Creating batch job...")
            try:
                batch_job = client.batches.create(
                    model=f"models/{TRANSLATE_MODEL}",
                    src=uploaded_file.name,
                    config={
                        "display_name": f"medterm_translation_{timestamp}_part{batch_idx + 1}",
                    },
                )
                print(f"  ✅ Batch job created: {batch_job.name}")
                successful_batches += 1
                break  # Success for this batch!
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "quota" in error_str.lower():
                    print(f"  ❌ Error 429: Quota exhausted. Rotating API key...")
                    if _global_rotator:
                        try:
                            new_key, new_index = _global_rotator.rotate_on_quota_exhausted(error_str)
                            print(f"  → Rotated to key index {new_index + 1}")
                            api_key = new_key
                            continue
                        except Exception as re:
                            print(f"  ⚠️  Rotation failed: {re}")
                print(f"Error creating batch job: {e}")
                if attempt == max_retries - 1:
                    print(f"  ⚠️  Batch {batch_idx + 1} failed, continuing with next batch...")
                    break
        
        # Save tracking info for this batch
        if batch_job is not None:
            # Get request keys for this batch
            batch_request_keys = [req["key"] for req in batch_requests]
            
            # Save which API key was used (for download later)
            api_key_index = _global_rotator._current_index if _global_rotator else 0
            api_key_id = f"GOOGLE_API_KEY_{_global_rotator.key_numbers[api_key_index]}" if _global_rotator else "GOOGLE_API_KEY"
            
            tracking_data["batches"][batch_job.name] = {
                "created_at": datetime.now().isoformat(),
                "state": "PENDING",
                "input_file": str(batch_input_file),
                "uploaded_file": uploaded_file.name,
                "num_requests": len(batch_requests),
                "batch_index": batch_idx + 1,
                "total_batches": total_batches,
                "record_keys": batch_request_keys,
                "api_key_id": api_key_id,  # Track which key created this batch
                "api_key_index": api_key_index,
            }
            
            # Save tracking after each successful batch
            save_tracking_file(tracking_path, tracking_data)
    
    # Save record map for later use (once, for all batches)
    record_map_file = output_path.parent / f".batch_medterm_record_map_{timestamp}.json"
    with open(record_map_file, "w", encoding="utf-8") as f:
        # Save original records for later merge
        json.dump({k: v for k, v in record_map.items()}, f, ensure_ascii=False, indent=2)
    
    # Update all batches with record_map_file reference
    for batch_name in tracking_data["batches"]:
        if "record_map_file" not in tracking_data["batches"][batch_name]:
            tracking_data["batches"][batch_name]["record_map_file"] = str(record_map_file)
    
    save_tracking_file(tracking_path, tracking_data)
    
    print(f"\n{'='*60}")
    print(f"✅ Batch submission complete!")
    print(f"   Total batches: {total_batches}")
    print(f"   Successful: {successful_batches}")
    print(f"   Failed: {total_batches - successful_batches}")
    print(f"   Tracking file: {tracking_path}")
    print(f"\n   To check status: python {__file__} --check_status --output {output_path}")
    print(f"   To download results: python {__file__} --download_and_apply --input {input_path} --output {output_path}")
    
    return successful_batches > 0


def check_status(output_path: Optional[Path] = None, base_dir: Optional[Path] = None) -> None:
    """
    Check status of all pending batch jobs.
    """
    if not GEMINI_AVAILABLE:
        print("Error: google.genai not available")
        return
    
    if base_dir is None:
        base_dir = Path(__file__).resolve().parents[4]
    
    # Initialize rotator (for multi-key lookup) and also keep a single client
    # for listing all batches (when output_path is not provided).
    api_key = get_api_key_with_rotator(base_dir)
    if not api_key:
        print("Error: No GOOGLE_API_KEY found")
        return
    client = genai.Client(api_key=api_key)
    
    # If output_path specified, check specific tracking file
    if output_path:
        tracking_path = get_tracking_file_path(output_path)
        tracking_data = load_tracking_file(tracking_path)
        
        if not tracking_data.get("batches"):
            print("No batch jobs found in tracking file.")
            return
        
        print(f"Checking {len(tracking_data['batches'])} batch job(s)...\n")
        
        for job_name, job_info in tracking_data["batches"].items():
            # Try to find the API key that created this batch
            batch_job = None
            used_key = None
            
            if _global_rotator:
                for key_idx, key_value in enumerate(_global_rotator.keys):
                    try:
                        temp_client = genai.Client(api_key=key_value)
                        batch_job = temp_client.batches.get(name=job_name)
                        used_key = f"key index {key_idx + 1}"
                        break
                    except Exception:
                        continue
            
            if batch_job is None:
                print(f"Job: {job_name}")
                print(f"  Error: Could not find batch with any API key\n")
                continue
            
            try:
                state = batch_job.state.name if hasattr(batch_job.state, 'name') else str(batch_job.state)
                
                print(f"Job: {job_name}")
                print(f"  State: {state}")
                print(f"  API Key: {used_key}")
                print(f"  Created: {job_info.get('created_at', 'N/A')}")
                print(f"  Requests: {job_info.get('num_requests', 'N/A')}")
                
                # Update tracking
                tracking_data["batches"][job_name]["state"] = state
                print()
                
            except Exception as e:
                print(f"Error checking job {job_name}: {e}\n")
        
        save_tracking_file(tracking_path, tracking_data)
    
    else:
        # List all batches from API
        print("Listing all batch jobs...\n")
        try:
            batches = list(client.batches.list())
            if not batches:
                print("No batch jobs found.")
                return
            
            for batch in batches:
                state = batch.state.name if hasattr(batch.state, 'name') else str(batch.state)
                print(f"Job: {batch.name}")
                print(f"  Display Name: {getattr(batch, 'display_name', 'N/A')}")
                print(f"  State: {state}")
                print(f"  Model: {getattr(batch, 'model', 'N/A')}")
                print()
                
        except Exception as e:
            print(f"Error listing batches: {e}")


def download_and_apply(
    input_path: Path,
    output_path: Path,
    base_dir: Optional[Path] = None,
) -> bool:
    """
    Download completed batch results and apply to output file.
    """
    if not GEMINI_AVAILABLE:
        print("Error: google.genai not available")
        return False
    
    if base_dir is None:
        base_dir = Path(__file__).resolve().parents[4]
    
    api_key = get_api_key_with_rotator(base_dir)
    if not api_key:
        print("Error: No GOOGLE_API_KEY found")
        return False
    
    tracking_path = get_tracking_file_path(output_path)
    tracking_data = load_tracking_file(tracking_path)
    
    if not tracking_data.get("batches"):
        print("No batch jobs found in tracking file.")
        return False
    
    # Build API key lookup from rotator
    api_key_lookup = {}
    if _global_rotator:
        for i, key in enumerate(_global_rotator.keys):
            key_id = f"GOOGLE_API_KEY_{_global_rotator.key_numbers[i]}"
            api_key_lookup[key_id] = key
            api_key_lookup[i] = key  # Also index-based lookup
    
    # Load original records
    print(f"[Step 1] Loading original records from {input_path}...")
    original_records = load_jsonl(input_path)
    original_map = {get_record_key(r): r for r in original_records}
    print(f"  Loaded {len(original_records)} original records")
    
    # Load already translated (if resuming)
    already_translated = {}
    if output_path.exists():
        existing = load_jsonl(output_path)
        already_translated = {get_record_key(r): r for r in existing}
        print(f"  Already translated: {len(already_translated)} records")
    
    # Process each completed batch
    total_applied = 0
    total_failed = 0
    
    for job_name, job_info in list(tracking_data["batches"].items()):
        print(f"\n[Processing] {job_name}")
        
        # Get the API key that was used to create this batch
        batch_api_key_id = job_info.get("api_key_id")
        batch_api_key_index = job_info.get("api_key_index")
        
        # Try to get the correct API key
        batch_api_key = None
        if batch_api_key_id and batch_api_key_id in api_key_lookup:
            batch_api_key = api_key_lookup[batch_api_key_id]
            print(f"  Using saved API key: {batch_api_key_id}")
        elif batch_api_key_index is not None and batch_api_key_index in api_key_lookup:
            batch_api_key = api_key_lookup[batch_api_key_index]
            print(f"  Using saved API key index: {batch_api_key_index}")
        else:
            # Fallback: try all keys to find this batch
            print(f"  API key not saved, searching across all keys...")
            for key_id, key in api_key_lookup.items():
                if not isinstance(key_id, str):
                    continue
                try:
                    test_client = genai.Client(api_key=key)
                    test_batch = test_client.batches.get(name=job_name)
                    batch_api_key = key
                    print(f"  Found batch with: {key_id}")
                    # Save for future use
                    tracking_data["batches"][job_name]["api_key_id"] = key_id
                    break
                except Exception:
                    continue
        
        if not batch_api_key:
            print(f"  ⚠️  Could not find API key for this batch, skipping...")
            continue
        
        client = genai.Client(api_key=batch_api_key)
        
        try:
            batch_job = client.batches.get(name=job_name)
            state = batch_job.state.name if hasattr(batch_job.state, 'name') else str(batch_job.state)
            
            if state != "JOB_STATE_SUCCEEDED":
                print(f"  Skipping: state is {state}")
                tracking_data["batches"][job_name]["state"] = state
                continue
            
            # Download results
            print(f"  Downloading results...")
            
            if batch_job.dest and batch_job.dest.file_name:
                result_file_name = batch_job.dest.file_name
                print(f"  Result file: {result_file_name}")
                
                file_content_bytes = client.files.download(file=result_file_name)
                file_content = file_content_bytes.decode("utf-8")
                
                # Parse results
                for line in file_content.splitlines():
                    if not line.strip():
                        continue
                    
                    try:
                        result = json.loads(line)
                        request_key = result.get("key", "")
                        
                        # Extract original record info from key
                        # Format: medterm_{idx}_{group_id}_{entity_id}
                        parts = request_key.split("_", 3)
                        if len(parts) >= 4:
                            group_id = parts[2]
                            entity_id = parts[3]
                            record_key = f"{group_id}_{entity_id}"
                        else:
                            print(f"  Warning: Could not parse key: {request_key}")
                            continue
                        
                        # Get original record
                        original = original_map.get(record_key)
                        if not original:
                            print(f"  Warning: Original record not found for {record_key}")
                            continue
                        
                        # Parse response
                        if "response" in result and result["response"]:
                            response = result["response"]
                            # Extract text from candidates
                            if "candidates" in response and response["candidates"]:
                                candidate = response["candidates"][0]
                                if "content" in candidate and "parts" in candidate["content"]:
                                    parts_list = candidate["content"]["parts"]
                                    if parts_list and "text" in parts_list[0]:
                                        text = parts_list[0]["text"]
                                        try:
                                            translated = json.loads(text)
                                            
                                            # Apply translation to original record
                                            translated_record = apply_translation(original, translated)
                                            already_translated[record_key] = translated_record
                                            total_applied += 1
                                        except json.JSONDecodeError as e:
                                            print(f"  Warning: JSON parse error for {record_key}: {e}")
                                            total_failed += 1
                        elif "error" in result:
                            print(f"  Error for {record_key}: {result['error']}")
                            total_failed += 1
                            tracking_data["failed_requests"].append({
                                "key": request_key,
                                "error": str(result.get("error")),
                            })
                    
                    except json.JSONDecodeError as e:
                        print(f"  Warning: Could not parse result line: {e}")
                        total_failed += 1
                
                # Mark batch as processed
                tracking_data["batches"][job_name]["state"] = "PROCESSED"
                tracking_data["batches"][job_name]["applied_count"] = total_applied
                
            elif batch_job.dest and batch_job.dest.inlined_responses:
                # Inline responses (for small batches)
                for i, inline_response in enumerate(batch_job.dest.inlined_responses):
                    if inline_response.response:
                        try:
                            text = inline_response.response.text
                            translated = json.loads(text)
                            # Would need to map back to original record
                            # This path is less common for large batches
                            total_applied += 1
                        except Exception as e:
                            print(f"  Warning: Error processing inline response {i}: {e}")
                            total_failed += 1
                    elif inline_response.error:
                        print(f"  Error in inline response {i}: {inline_response.error}")
                        total_failed += 1
            
        except Exception as e:
            print(f"  Error processing batch {job_name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Write output
    if already_translated:
        print(f"\n[Step 2] Writing output to {output_path}...")
        
        # Preserve order from original
        final_records = []
        for record in original_records:
            key = get_record_key(record)
            if key in already_translated:
                final_records.append(already_translated[key])
        
        write_jsonl(output_path, final_records)
        print(f"  Written {len(final_records)} records")
    
    # Save tracking
    save_tracking_file(tracking_path, tracking_data)
    
    print(f"\n✅ Download and apply complete!")
    print(f"   Applied: {total_applied}")
    print(f"   Failed: {total_failed}")
    print(f"   Total in output: {len(already_translated)}")
    
    return True


def apply_translation(
    original: Dict[str, Any],
    translated: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Apply translation results to original record.
    """
    import copy
    result = copy.deepcopy(original)
    
    anki_cards = result.get("anki_cards", [])
    if not anki_cards:
        return result
    
    # Apply to first card (most common case)
    card = anki_cards[0]
    
    if "translated_front" in translated:
        card["front"] = translated["translated_front"]
    
    if "translated_back" in translated:
        card["back"] = translated["translated_back"]
    
    if "translated_options" in translated and translated["translated_options"]:
        card["options"] = translated["translated_options"]
    
    return result


# =========================
# Main
# =========================

def main():
    parser = argparse.ArgumentParser(
        description="Batch Medical Term Translation via Gemini Batch API"
    )
    
    parser.add_argument("--input", type=str, help="Input JSONL file path")
    parser.add_argument("--output", type=str, help="Output JSONL file path")
    parser.add_argument("--max_records", type=int, help="Maximum records to process (for testing)")
    parser.add_argument("--no_resume", action="store_true", help="Start fresh, don't skip already translated")
    
    # Actions
    parser.add_argument("--submit", action="store_true", help="Submit batch job")
    parser.add_argument("--check_status", action="store_true", help="Check batch job status")
    parser.add_argument("--download_and_apply", action="store_true", help="Download results and apply")
    
    args = parser.parse_args()
    
    # Validate args
    if args.submit or args.download_and_apply:
        if not args.input or not args.output:
            print("Error: --input and --output are required for --submit and --download_and_apply")
            sys.exit(1)
    
    input_path = Path(args.input) if args.input else None
    output_path = Path(args.output) if args.output else None
    
    if args.submit:
        success = submit_batch(
            input_path=input_path,
            output_path=output_path,
            max_records=args.max_records,
            resume=not args.no_resume,
        )
        sys.exit(0 if success else 1)
    
    elif args.check_status:
        check_status(output_path)
    
    elif args.download_and_apply:
        success = download_and_apply(
            input_path=input_path,
            output_path=output_path,
        )
        sys.exit(0 if success else 1)
    
    else:
        parser.print_help()
        print("\n예시:")
        print("  # 배치 제출")
        print("  python batch_medterm_translation.py --input s2_results.jsonl --output s2_translated.jsonl --submit")
        print("")
        print("  # 상태 확인")
        print("  python batch_medterm_translation.py --check_status --output s2_translated.jsonl")
        print("")
        print("  # 결과 다운로드 및 적용")
        print("  python batch_medterm_translation.py --input s2_results.jsonl --output s2_translated.jsonl --download_and_apply")


if __name__ == "__main__":
    main()


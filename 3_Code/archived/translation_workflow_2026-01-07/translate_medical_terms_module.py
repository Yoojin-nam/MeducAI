#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reusable module for translating Korean medical terms to English in Anki cards.

This module provides:
- Safe translation function with improved prompts
- Batch processing support
- Error handling and fallback
"""

from __future__ import annotations

import copy
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

_THIS_DIR = Path(__file__).resolve().parent
_parent = _THIS_DIR.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from preprocess.gemini_utils import GeminiClient, GeminiConfig  # noqa: E402

# Try to import ApiKeyRotator (optional)
try:
    from tools.api_key_rotator import ApiKeyRotator
    ROTATOR_AVAILABLE = True
except ImportError:
    ROTATOR_AVAILABLE = False
    ApiKeyRotator = None  # type: ignore

# Simplified prompt v3: core rules only, reduced redundancy
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

# JSON Schema for structured output
TRANSLATION_SCHEMA = {
    "type": "object",
    "properties": {
        "translated_text": {
            "type": "string",
            "description": "The text with medical terms translated to English"
        }
    },
    "required": ["translated_text"]
}

#
# Post-translation cleanup (baseline-alignment)
# -------------------------------------------
# We keep this narrowly scoped to MCQ `back` fields because that's where
# explanatory gloss patterns like `한글(English)` commonly remain and create
# inconsistent output.
#
_RE_KO_EN_PAREN = re.compile(r"(?P<ko>[가-힣][가-힣0-9·\-\s']{0,80})\s*\(\s*(?P<en>[A-Za-z][^)]{0,120})\s*\)")
_RE_EN_KO_PAREN = re.compile(r"(?P<en>[A-Za-z][A-Za-z0-9 .:/_\\-]{0,120})\s*\(\s*(?P<ko>[가-힣][^)]{0,120})\s*\)")

# Explicit pair overrides (Korean, English) -> desired replacement
_MCQ_BACK_PAREN_OVERRIDES: Dict[tuple, str] = {
    ("하베뉼라", "Habenula"): "Habenula",
    ("앞쪽", "Anterior"): "앞쪽",
    ("누출", "Leakage"): "누출",
    ("조영술", "UGI"): "UGI",
    ("긴장", "Tension"): "tension",
    ("반응성 저혈당", "Reactive hypoglycemia"): "Reactive hypoglycemia",
}

# Non-parenthetical phrase overrides (applied after translation)
_MCQ_BACK_PHRASE_OVERRIDES: Dict[str, str] = {
    "후기 덤핑": "late dumping",
    "고삼투압 음식물": "Hyperosmolar food",
}


def _postprocess_mcq_back(text: str) -> str:
    """
    Postprocess MCQ back to align with baseline style:
    - Remove bilingual gloss parentheses and keep the preferred side.
    - Apply a small set of stable phrase overrides.

    This is intentionally conservative and only runs on MCQ `back`.
    """
    if not text:
        return text

    # 1) Phrase overrides first (so parentheses handling sees final tokens if they appear)
    for src, dst in _MCQ_BACK_PHRASE_OVERRIDES.items():
        if src in text:
            text = text.replace(src, dst)

    # 2) Handle Korean(English) glosses
    def repl_ko_en(m: re.Match) -> str:
        ko = (m.group("ko") or "").strip()
        en = (m.group("en") or "").strip()
        key = (ko, en)
        if key in _MCQ_BACK_PAREN_OVERRIDES:
            return _MCQ_BACK_PAREN_OVERRIDES[key]

        # Heuristic defaults: keep common abbreviations, otherwise keep Korean for non-medical
        # directional/administrative words; else prefer English (baseline-ish).
        en_compact = re.sub(r"\s+", "", en)
        if en_compact.isupper() and 2 <= len(en_compact) <= 6:
            return en_compact
        if ko in {"앞쪽", "뒤쪽", "위쪽", "아래쪽", "누출"}:
            return ko
        return en

    text = _RE_KO_EN_PAREN.sub(repl_ko_en, text)

    # 3) Handle English(Korean) glosses -> keep English side (strip parentheses)
    text = _RE_EN_KO_PAREN.sub(lambda m: (m.group("en") or "").strip(), text)

    return text


def _detect_project_root(start: Path) -> Path:
    """
    Best-effort repo root detection (so ApiKeyRotator can reliably find `.env` in tests).

    Heuristic: repo root contains both `2_Data/` and `3_Code/`.
    """
    start = start.resolve()
    for p in [start] + list(start.parents):
        if (p / "2_Data").is_dir() and (p / "3_Code").is_dir():
            return p
    return start.parent


def _schema_for_model(base_schema: dict, model: str) -> dict:
    """
    Gemini 2.0 models can be picky about property order in JSON Schema.
    Add `propertyOrdering` only for gemini-2.0* models.
    """
    schema = copy.deepcopy(base_schema)
    if "gemini-2.0" in (model or ""):
        props = schema.get("properties")
        if isinstance(props, dict) and "propertyOrdering" not in schema:
            schema["propertyOrdering"] = list(props.keys())
    return schema


def _make_structured_generate_config(
    *,
    types: Any,
    model: str,
    system_instruction: str,
    temperature: float,
    schema: dict,
) -> Any:
    """
    Build `GenerateContentConfig` using the SDK-supported schema field name.

    Newer SDKs: `response_json_schema`
    Older SDKs: `response_schema`
    """
    schema_for_model = _schema_for_model(schema, model)
    # Disable/minimize thinking for simple translation tasks (much faster)
    thinking_config = None
    if "gemini-3" in (model or ""):
        # Gemini 3: use thinking_level="minimal" (officially supported, faster than budget=0)
        try:
            thinking_config = types.ThinkingConfig(thinking_level="minimal")
        except (AttributeError, TypeError):
            pass  # SDK doesn't support ThinkingConfig
    elif "gemini-2.5" in (model or ""):
        # Gemini 2.5: use thinking_budget=0 to disable thinking
        try:
            thinking_config = types.ThinkingConfig(thinking_budget=0)
        except (AttributeError, TypeError):
            pass
    
    base_kwargs = dict(
        system_instruction=system_instruction,
        temperature=temperature,
        top_p=1.0,
        top_k=1,
        candidate_count=1,
        max_output_tokens=16384,
        response_mime_type="application/json",
    )
    if thinking_config is not None:
        base_kwargs["thinking_config"] = thinking_config
    try:
        return types.GenerateContentConfig(**base_kwargs, response_json_schema=schema_for_model)
    except TypeError:
        return types.GenerateContentConfig(**base_kwargs, response_schema=schema_for_model)


class MedicalTermTranslator:
    """Translator for Korean medical terms in Anki cards."""
    
    def __init__(
        self,
        model: str = "gemini-3-flash-preview",
        temperature: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        use_rotator: bool = True,
        base_dir: Optional[Path] = None,
    ):
        """
        Initialize translator with Gemini client and optional API key rotation.
        
        Args:
            model: Gemini model name
            temperature: Temperature for generation
            max_retries: Max retries for transient errors
            retry_delay: Delay between retries
            use_rotator: Enable API key rotation (default: True)
            base_dir: Project base directory for rotator (auto-detected if None)
        """
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client: Optional[GeminiClient] = None
        self._translation_cache: Dict[str, str] = {}
        
        # Initialize API key rotator if available
        self.rotator: Optional[Any] = None  # Use Any to avoid type issues when rotator not available
        if use_rotator and ROTATOR_AVAILABLE and ApiKeyRotator is not None:
            if base_dir is None:
                # Auto-detect repo root (so `.env` is found reliably even in ad-hoc tests)
                base_dir = _detect_project_root(Path(__file__).resolve())
            try:
                self.rotator = ApiKeyRotator(base_dir=base_dir)
                num_keys = len(self.rotator.keys) if hasattr(self.rotator, 'keys') else 0
                print(f"[Translator] API Key Rotator enabled with {num_keys} keys")
            except Exception as e:
                print(f"[Translator] Warning: Failed to initialize API Key Rotator: {e}")
                print(f"[Translator] Continuing with single API key from environment")
                self.rotator = None
        elif use_rotator and not ROTATOR_AVAILABLE:
            print(f"[Translator] Warning: API Key Rotator not available (module not found)")
            print(f"[Translator] Continuing with single API key from environment")
    
    def _get_client(self, api_key: Optional[str] = None) -> GeminiClient:
        """
        Lazy initialization of Gemini client.
        
        Args:
            api_key: Optional API key override (for rotation)
        """
        # If rotator is enabled and we have multiple keys, always create new client with current key
        if self.rotator and api_key is None:
            api_key = self.rotator.get_current_key()
            # Always recreate client when using rotator to ensure we use the current key
            self._client = GeminiClient(
                GeminiConfig(
                    model=self.model,
                    temperature=self.temperature,
                    top_p=1.0,
                    top_k=1,
                    max_output_tokens=16384,
                    response_mime_type=None,
                ),
                api_key=api_key,
            )
            return self._client
        
        # Single key mode or explicit api_key provided
        if self._client is None or api_key is not None:
            self._client = GeminiClient(
                GeminiConfig(
                    model=self.model,
                    temperature=self.temperature,
                    top_p=1.0,
                    top_k=1,
                    max_output_tokens=16384,
                    response_mime_type=None,
                ),
                api_key=api_key,
            )
        return self._client
    
    def translate_text(
        self,
        text: str,
        use_cache: bool = True,
        verbose: bool = False,
    ) -> str:
        """
        Translate Korean medical terms in text to English.
        
        Args:
            text: Input text containing Korean medical terms
            use_cache: Whether to use translation cache
            verbose: Whether to print warnings
            
        Returns:
            Translated text with medical terms in English
        """
        if not text or not text.strip():
            return text
        
        # Check if text contains Korean characters
        has_korean = any('\uAC00' <= char <= '\uD7A3' for char in text)
        if not has_korean:
            return text  # No Korean, skip translation
        
        # Check cache
        if use_cache and text in self._translation_cache:
            return self._translation_cache[text]
        
        # Translate with API key rotation support
        result = text  # Default to original on error
        
        for attempt in range(self.max_retries):
            try:
                # Get fresh client (with current API key if using rotator)
                client = self._get_client()
                
                cfg = _make_structured_generate_config(
                    types=client._types,
                    model=client.cfg.model,
                    system_instruction=SYSTEM_PROMPT,
                    temperature=self.temperature,
                    schema=TRANSLATION_SCHEMA,
                )
                
                resp = client._client.models.generate_content(
                    model=client.cfg.model,
                    contents=text,
                    config=cfg,
                )
                
                # Parse JSON response
                raw_result = getattr(resp, "text", "").strip()
                try:
                    import json as json_module
                    parsed = json_module.loads(raw_result)
                    result = parsed.get("translated_text", "").strip()
                    
                    if not result:
                        # translated_text field is empty
                        if verbose:
                            print(f"  [WARN] Empty translated_text field in JSON response")
                        result = text  # Return original
                        
                except json_module.JSONDecodeError as e:
                    # JSON parsing failed - this is a problem!
                    print(f"  [ERROR] JSON parsing failed: {e}", file=sys.stderr)
                    print(f"  [ERROR] Raw response: {raw_result[:200]}", file=sys.stderr)
                    # Return original text as fallback
                    result = text
                except Exception as e:
                    print(f"  [ERROR] Unexpected error parsing JSON: {e}", file=sys.stderr)
                    result = text
                
                # Remove Gemini 3 "thinking" process text from output
                # These patterns indicate internal reasoning that should not be in final output
                if result:
                    import re
                    thinking_patterns = [
                        r'Let\'s re-evaluate[^\n]*\n',
                        r'Rule \d+:[^\n]*\n',
                        r'So "[^"]*"[^\n]*\n',
                        r'\*Let\'s[^\n]*\n',
                        r'One detail:[^\n]*\n',
                        r'This is already[^\n]*\n',
                        r'The input has[^\n]*\n',
                        r'Final check on[^\n]*\n',
                        r'^\s*"\s*is just the plain[^\n]*\n',
                        r'^\s*"[^"]*"\s*is just the plain[^\n]*\n',
                        r'Wait,[^\n]*\n',  # Wait, "something"...
                        r'If I follow Rule[^\n]*\n',  # If I follow Rule X:
                        r'\*\s*Wait,[^\*]*\*',  # *Wait, ...*
                        r'\*\s*Rule \d+:[^\*]*\*',  # *Rule X: ...*
                        r'\*\s*Final check[^\*]*\*',  # *Final check on...*
                        r'\*\s*One detail:[^\*]*\*',  # *One detail:...*
                    ]
                    for pattern in thinking_patterns:
                        result = re.sub(pattern, '', result, flags=re.IGNORECASE | re.MULTILINE)
                    # Clean up multiple consecutive newlines and asterisks
                    result = re.sub(r'\n{3,}', '\n\n', result)
                    result = re.sub(r'\*\s*\*', '', result)  # Remove empty ** markers
                    result = result.strip()
                
                if result:
                    # Success! Record it if using rotator
                    if self.rotator:
                        self.rotator.record_success(batch_save=True)
                    break
                else:
                    if verbose:
                        print(f"  [WARN] Empty translation response, attempt {attempt + 1}/{self.max_retries}")
                    
            except Exception as e:
                error_str = str(e).lower()
                
                # Check if this is a quota exhaustion error (non-retryable)
                is_quota_exhausted = (
                    "quota exceeded" in error_str or
                    "exceeded your current quota" in error_str or
                    ("429" in error_str and "limit: 0" in error_str) or
                    ("429" in error_str and "resource_exhausted" in error_str) or
                    "resource has been exhausted" in error_str
                )
                
                if is_quota_exhausted and self.rotator:
                    # Quota exhausted - rotate to next key
                    if verbose:
                        print(f"  [INFO] Quota exhausted, rotating to next API key...")
                    try:
                        new_key, new_index = self.rotator.rotate_on_quota_exhausted(str(e))
                        if verbose:
                            print(f"  [INFO] Switched to API key #{new_index + 1}")
                        # Retry immediately with new key (don't count as retry)
                        continue
                    except RuntimeError as re:
                        # All keys exhausted
                        if verbose:
                            print(f"  [ERROR] All API keys exhausted: {re}")
                        raise
                else:
                    # Transient error - retry with backoff
                    if verbose:
                        print(f"  [WARN] Translation failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (attempt + 1))
                    continue
        
        # Warn if translation didn't change anything (when Korean was present)
        if verbose and result == text and has_korean:
            snippet = text[:80].replace('\n', ' ')
            print(f"  [WARN] Translation unchanged for text with Korean: {snippet}...", file=sys.stderr)
        
        # Cache result
        if use_cache:
            self._translation_cache[text] = result
        
        return result
    
    def translate_card(self, card: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
        """
        Translate medical terms in a single Anki card.
        
        Args:
            card: Anki card dictionary with 'front', 'back', 'options' fields
            verbose: Whether to print warnings
            
        Returns:
            Translated card dictionary
        """
        translated = card.copy()
        
        # Translate front field
        if 'front' in translated:
            translated['front'] = self.translate_text(translated['front'], verbose=verbose)
        
        # Translate back field
        if 'back' in translated:
            translated['back'] = self.translate_text(translated['back'], verbose=verbose)
            # Baseline-alignment cleanup for MCQ back explanations
            # NOTE: Temporarily disabled to test prompt-only effectiveness
            # if str(translated.get("card_type", "")).upper() == "MCQ":
            #     translated["back"] = _postprocess_mcq_back(str(translated.get("back") or ""))
        
        # Translate options (for MCQ cards)
        if 'options' in translated and isinstance(translated['options'], list):
            translated['options'] = [
                self.translate_text(opt, verbose=verbose) for opt in translated['options']
            ]
        
        return translated
    
    def translate_s2_record(
        self,
        record: Dict[str, Any],
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """
        Translate medical terms in an S2 JSONL record.
        
        Args:
            record: S2 record dictionary with 'anki_cards' field
            verbose: Whether to print warnings
            
        Returns:
            Translated S2 record
        """
        translated = record.copy()
        
        # Translate anki_cards
        if 'anki_cards' in translated and isinstance(translated['anki_cards'], list):
            translated['anki_cards'] = [
                self.translate_card(card, verbose=verbose)
                for card in translated['anki_cards']
            ]
        
        return translated


def translate_s2_jsonl_file(
    input_path: Path,
    output_path: Path,
    translator: Optional[MedicalTermTranslator] = None,
    batch_size: int = 10,
    max_records: Optional[int] = None,
    verbose: bool = True,
    max_workers: int = 10,
    resume: bool = True,
) -> int:
    """
    Translate medical terms in an S2 JSONL file with parallel processing.
    
    Supports resume: if output file exists, skips already translated records.
    
    Args:
        input_path: Input S2 JSONL file path
        output_path: Output JSONL file path
        translator: Translator instance (creates new one if None)
        batch_size: Print progress every N records
        max_records: Maximum number of records to process (for testing)
        verbose: Whether to print progress
        max_workers: Number of parallel workers (default: 10)
        resume: Whether to resume from existing output file (default: True)
        
    Returns:
        Number of records translated
    """
    import json
    
    if translator is None:
        translator = MedicalTermTranslator()
    
    # Clear translation cache when not resuming (force fresh translation)
    if not resume:
        translator._translation_cache = {}
        if verbose:
            print("[INFO] Translation cache cleared (resume=False)")
    
    if verbose:
        print(f"Reading: {input_path}")
        print(f"Output: {output_path}")
        print(f"Parallel workers: {max_workers}")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check for existing output (resume)
    already_translated = set()
    if resume and output_path.exists():
        try:
            with output_path.open('r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        rec = json.loads(line)
                        # Use group_id + entity_id as unique key
                        key = (rec.get('group_id', ''), rec.get('entity_id', ''))
                        already_translated.add(key)
            if verbose and already_translated:
                print(f"Resume mode: {len(already_translated)} records already translated")
        except Exception as e:
            if verbose:
                print(f"  [WARN] Could not read existing output for resume: {e}")
    
    # Read all records first
    records = []
    with input_path.open('r', encoding='utf-8') as infile:
        for line_num, line in enumerate(infile, 1):
            if not line.strip():
                continue
            if max_records and line_num > max_records:
                break
            try:
                record = json.loads(line)
                # Skip if already translated
                key = (record.get('group_id', ''), record.get('entity_id', ''))
                if key not in already_translated:
                    records.append((line_num, record))
            except json.JSONDecodeError as e:
                if verbose:
                    print(f"  [ERROR] Line {line_num}: JSON decode error: {e}", file=sys.stderr)
    
    total_records = len(records)
    if verbose:
        print(f"Records to translate: {total_records}")
    
    # Translate in parallel with IMMEDIATE writing
    translated_count = 0
    write_lock = Lock()
    
    def translate_record(line_num: int, record: Dict[str, Any]) -> tuple:
        """Translate a single record"""
        try:
            translated = translator.translate_s2_record(record, verbose=verbose)
            return (line_num, translated, None)
        except Exception as e:
            return (line_num, None, str(e))
    
    # Execute parallel translation
    start_time = time.time()
    
    try:
        from tqdm import tqdm
        use_tqdm = True
    except ImportError:
        use_tqdm = False
    
    # Open output file for writing (append if resuming).
    #
    # Important safety: when starting fresh (mode='w'), write to a temp file first and
    # replace the final output only if we managed to write at least one record.
    # This avoids leaving an empty/truncated output file when all translations fail.
    mode = 'a' if (resume and already_translated) else 'w'
    temp_output_path = output_path
    if mode == 'w':
        temp_output_path = output_path.with_suffix(output_path.suffix + '.tmp')

    errors: List[tuple] = []

    with temp_output_path.open(mode, encoding='utf-8', buffering=1) as outfile:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(translate_record, line_num, record): line_num
                for line_num, record in records
            }
            
            if use_tqdm and verbose:
                # Use tqdm for nice progress bar
                with tqdm(total=total_records, desc="Translating", unit="record") as pbar:
                    for future in as_completed(futures):
                        line_num, translated, error = future.result()
                        if error:
                            print(f"\n  [ERROR] Line {line_num}: {error}", file=sys.stderr)
                            errors.append((line_num, error))
                        else:
                            # Write immediately with lock
                            with write_lock:
                                outfile.write(json.dumps(translated, ensure_ascii=False) + '\n')
                                outfile.flush()
                                translated_count += 1
                        pbar.update(1)
            else:
                # Fallback to basic progress reporting
                completed = 0
                for future in as_completed(futures):
                    line_num, translated, error = future.result()
                    if error:
                        if verbose:
                            print(f"  [ERROR] Line {line_num}: {error}", file=sys.stderr)
                        errors.append((line_num, error))
                    else:
                        # Write immediately with lock
                        with write_lock:
                            outfile.write(json.dumps(translated, ensure_ascii=False) + '\n')
                            outfile.flush()
                            translated_count += 1
                    
                    completed += 1
                    if verbose and completed % batch_size == 0:
                        print(f"  Progress: {completed}/{total_records} records ({100*completed//total_records}%)", flush=True)
    
    elapsed = time.time() - start_time

    # If we wrote to a temp file, only promote it when we actually produced output.
    if mode == 'w':
        if translated_count > 0 or total_records == 0:
            # Backup existing output before overwrite (if any).
            if output_path.exists():
                import shutil
                import datetime as _dt

                ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = output_path.with_suffix(output_path.suffix + f".bak_{ts}")
                # Avoid unlikely collision if called multiple times within same second.
                if backup_path.exists():
                    i = 2
                    while True:
                        candidate = output_path.with_suffix(output_path.suffix + f".bak_{ts}_{i}")
                        if not candidate.exists():
                            backup_path = candidate
                            break
                        i += 1
                try:
                    shutil.copy2(output_path, backup_path)
                    if verbose:
                        print(f"✅ Backup created: {backup_path}")
                except Exception as e:
                    if verbose:
                        print(f"  [WARN] Failed to create backup of existing output: {e}", file=sys.stderr)

            try:
                temp_output_path.replace(output_path)
            except Exception:
                # Fall back: if replace fails, at least keep the temp file for inspection.
                if verbose:
                    print(f"  [WARN] Could not replace output with temp file: {temp_output_path}", file=sys.stderr)
        else:
            # All translations failed; leave temp file for debugging and raise.
            first_err = errors[0] if errors else None
            if verbose:
                print(f"\n❌ No records were written (all {total_records} failed).", file=sys.stderr)
                if first_err:
                    print(f"   First error at line {first_err[0]}: {first_err[1]}", file=sys.stderr)
                print(f"   Temp output kept for inspection: {temp_output_path}", file=sys.stderr)
            raise RuntimeError(
                "Translation produced 0 records. "
                "Check API key / SDK / quota errors above; output was not written."
            )
    
    if verbose:
        print(f"\n✅ Complete: {translated_count} records translated in {elapsed:.1f}s")
        if translated_count > 0:
            print(f"   Average: {elapsed/translated_count:.2f}s per record")
        if already_translated:
            print(f"   Total in output file: {len(already_translated) + translated_count} records")
        if errors:
            print(f"   Errors: {len(errors)}", file=sys.stderr)
    
    return translated_count


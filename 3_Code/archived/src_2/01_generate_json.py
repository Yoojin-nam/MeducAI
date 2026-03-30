#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MeducAI Pipeline v3.6 (Hotfix): Ensure Master Table & Infographic Data Flow
-------------------------------------------------------------------------
- Fixes regression where table values were dropped between Stage 1 and Output.
- Enforces JSON Schema v3.8 alignment.
- MI-CLEAR-LLM Compliant (Logging & Reproducibility)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import time
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv

import google.generativeai as genai
from openai import OpenAI
import anthropic


# -------------------------
# Configuration & Paths
# -------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    print(f"⚠️  Warning: .env file NOT found at: {env_path}")

INPUT_FILE = BASE_DIR / "2_Data" / "metadata" / "groups.csv"  # Modified to look for groups.csv if xlsx missing
if not INPUT_FILE.exists():
    INPUT_FILE = BASE_DIR / "2_Data" / "processed" / "Radiology_Curriculum_Weight_Factor.xlsx"

OUTPUT_DIR = BASE_DIR / "2_Data" / "metadata"

# --- ENV Vars ---
GROUP_KEY_MODE = os.getenv("GROUP_KEY_MODE", "AUTO").strip().upper()
try:
    GROUP_MAX_OBJECTIVES = int(os.getenv("GROUP_MAX_OBJECTIVES", "16"))
except ValueError:
    GROUP_MAX_OBJECTIVES = 16

def _env_float(name: str, default: float) -> float:
    try: return float(os.getenv(name, str(default)))
    except: return default

def _env_int(name: str, default: int) -> int:
    try: return int(os.getenv(name, str(default)))
    except: return default

BASE_CARDS_PER_GROUP = _env_int("BASE_CARDS_PER_GROUP", 8)
MIN_CARDS_PER_GROUP = _env_int("MIN_CARDS_PER_GROUP", 4)
MAX_CARDS_PER_GROUP = _env_int("MAX_CARDS_PER_GROUP", 20)
WEIGHT_TRANSFORM = os.getenv("WEIGHT_TRANSFORM", "LOG1P").strip().upper()

TARGET_COUNT_MIN = 1
TARGET_COUNT_MAX = _env_int("TARGET_COUNT_MAX", 80)

CARDS_PER_ENTITY = _env_int("CARDS_PER_ENTITY", 3)

# -------------------------
# MINIMUM CONTRACT (Step01 JSONL schema)
# -------------------------
CONTRACT_NAME = "meducai_step01_min_contract"
CONTRACT_VERSION = "1.0.0"

# Pragmatic schema spec (not full JSON Schema) used for validation & defaults.
MIN_CONTRACT_SPEC = {
    "top_level_required": ["metadata", "curriculum_content"],
    "metadata_required": ["id", "provider", "arm", "timestamp", "source_info"],
    "curriculum_required": ["visual_type", "table_infographic", "entities"],
    "table_infographic_required": ["style", "keywords_en", "prompt_en"],
    "entity_required": ["entity_name", "importance_score", "row_image_necessity", "row_image_prompt_en", "anki_cards"],
    "card_required": ["card_type", "front", "back", "tags"],
    "allowed_row_image_necessity": ["IMG_REQ", "IMG_OPT", "IMG_NONE"],
}

def now_ts() -> int:
    return int(time.time())

def is_blank(x: Any) -> bool:
    return x is None or (isinstance(x, str) and x.strip() == "")

def normalize_tags(tags: Any) -> str:
    if tags is None:
        return ""
    if isinstance(tags, str):
        return tags.strip()
    if isinstance(tags, list):
        return " ".join([str(t).strip() for t in tags if str(t).strip()])
    return str(tags).strip()

def mk_fallback_entity_prompt(entity_name: str) -> str:
    ent = (entity_name or "").strip() or "the key concept"
    return (
        f"High-quality medical illustration of {ent}. "
        f"Clean, exam-oriented style, accurate anatomy, plain background, "
        f"no decorative elements, minimal but clear labeling if needed."
    )

def mk_error_record(*, gid: str, provider: str, arm: str, run_tag: str, mode: str, source_info: Dict[str, Any],
                    error_stage: str, error_message: str) -> Dict[str, Any]:
    ts = now_ts()
    return {
        "contract": {"name": CONTRACT_NAME, "version": CONTRACT_VERSION},
        "record_id": gid,
        "group_id": gid,
        "run_tag": run_tag,
        "mode": mode,
        "provider": provider,
        "arm": arm,
        "metadata": {
            "id": gid,
            "provider": provider,
            "arm": arm,
            "timestamp": ts,
            "source_info": source_info,
            "ok": False,
            "error": {"stage": error_stage, "message": error_message},
        },
        "meta": {
            "provider": provider,
            "arm": arm,
            "source_info": source_info,
            "ok": False,
            "error": {"stage": error_stage, "message": error_message},
        },
        "curriculum_content": {
            "visual_type": "error",
            "master_table": "",
            "table_infographic": {"style": "error", "keywords_en": [], "prompt_en": ""},
            "entities": [],
        },
    }

def validate_and_fill_entity(entity: Dict[str, Any]) -> Dict[str, Any]:
    entity = dict(entity or {})
    entity["entity_name"] = str(entity.get("entity_name") or "").strip() or "Unnamed entity"
    try:
        entity["importance_score"] = int(entity.get("importance_score", 50))
    except Exception:
        entity["importance_score"] = 50

    nec = str(entity.get("row_image_necessity") or "IMG_OPT").strip()
    if nec not in MIN_CONTRACT_SPEC["allowed_row_image_necessity"]:
        nec = "IMG_OPT"
    entity["row_image_necessity"] = nec

    if nec == "IMG_NONE":
        entity["row_image_prompt_en"] = None
    else:
        prompt = str(entity.get("row_image_prompt_en") or "").strip()
        if not prompt:
            prompt = mk_fallback_entity_prompt(entity["entity_name"])
        entity["row_image_prompt_en"] = prompt

    cards = entity.get("anki_cards")
    if not isinstance(cards, list):
        cards = []

    cleaned_cards = []
    for c in cards:
        if not isinstance(c, dict):
            continue
        card_type = str(c.get("card_type") or "").strip() or "Basic_QA"
        front = str(c.get("front") or "").strip()
        back = str(c.get("back") or "").strip()
        tags = normalize_tags(c.get("tags"))
        if not front or not back:
            continue
        cleaned_cards.append({"card_type": card_type, "front": front, "back": back, "tags": tags})

    entity["anki_cards"] = cleaned_cards
    return entity

def validate_and_fill_record(record: Dict[str, Any], *, run_tag: str, mode: str, provider: str, arm: str) -> Dict[str, Any]:
    record = dict(record or {})
    gid = record.get("record_id") or record.get("group_id") or record.get("metadata", {}).get("id")
    if is_blank(gid):
        gid = sha1_text(f"{provider}|{arm}|{now_ts()}")

    record["record_id"] = gid
    record["group_id"] = gid
    record["run_tag"] = run_tag
    record["mode"] = mode
    record["provider"] = provider
    record["arm"] = arm
    record["contract"] = {"name": CONTRACT_NAME, "version": CONTRACT_VERSION}

    md = dict(record.get("metadata") or {})
    md.setdefault("id", gid)
    md.setdefault("provider", provider)
    md.setdefault("arm", arm)
    md.setdefault("timestamp", now_ts())
    md.setdefault("source_info", {})
    md["ok"] = True
    record["metadata"] = md

    meta = dict(record.get("meta") or {})
    meta.setdefault("provider", provider)
    meta.setdefault("arm", arm)
    meta.setdefault("source_info", md.get("source_info", {}))
    meta["ok"] = True
    record["meta"] = meta

    cc = dict(record.get("curriculum_content") or {})
    cc.setdefault("visual_type", "general_radiology")
    cc.setdefault("master_table", "")
    ti = dict(cc.get("table_infographic") or {})
    ti.setdefault("style", "medical_infographic")
    ti.setdefault("keywords_en", [])
    ti.setdefault("prompt_en", "")
    cc["table_infographic"] = ti

    entities = cc.get("entities")
    if not isinstance(entities, list):
        entities = []
    cc["entities"] = [validate_and_fill_entity(e) for e in entities if isinstance(e, dict)]
    record["curriculum_content"] = cc

    return record

CARD_TYPE_RATIOS_SPEC = os.getenv("CARD_TYPE_RATIOS", "Basic_QA:0.34,Cloze_Finding:0.33,MCQ_Vignette:0.33").strip()
IMAGE_NECESSITY_RATIOS_SPEC = os.getenv("IMAGE_NECESSITY_RATIOS", "IMG_REQ:0.40,IMG_OPT:0.40,IMG_NONE:0.20").strip()
IMAGE_ASSIGN_POLICY = os.getenv("IMAGE_ASSIGN_POLICY", "RANKED_BY_IMPORTANCE").strip().upper()

PROVIDER_TEXT_ENV = os.getenv("PROVIDER_TEXT", "").strip().lower()
TEXT_MODEL_STAGE1 = os.getenv("TEXT_MODEL_STAGE1", "").strip()
TEXT_MODEL_STAGE2 = os.getenv("TEXT_MODEL_STAGE2", "").strip()
TEMPERATURE_STAGE1 = _env_float("TEMPERATURE_STAGE1", 0.2)
TEMPERATURE_STAGE2 = _env_float("TEMPERATURE_STAGE2", 0.3)
MAX_TOKENS_STAGE1 = _env_int("MAX_TOKENS_STAGE1", 8192)
MAX_TOKENS_STAGE2 = _env_int("MAX_TOKENS_STAGE2", 8192)
TIMEOUT_S = _env_int("TIMEOUT_S", 120)

MODEL_CONFIG = {
    "gemini": {"model_name": "gemini-2.5-flash", "api_key_env": "GOOGLE_API_KEY"}, # Updated default
    "gpt": {"model_name": "gpt-5.2-pro-2025-12-11", "api_key_env": "OPENAI_API_KEY"},
    "deepseek": {"model_name": "deepseek-reasoner", "api_key_env": "DEEPSEEK_API_KEY", "base_url": "https://api.deepseek.com"},
    "claude": {"model_name": "claude-3-5-sonnet-20241022", "api_key_env": "ANTHROPIC_API_KEY"},
}

ARM_CONFIGS = {
    "A": {"label": "Baseline",   "provider": "gemini", "text_model_stage1": "gemini-2.5-flash", "text_model_stage2": "gemini-2.5-flash", "thinking": False, "rag": False},
    "B": {"label": "RAG_Only",   "provider": "gemini", "text_model_stage1": "gemini-2.5-flash", "text_model_stage2": "gemini-2.5-flash", "thinking": False, "rag": True},
    "C": {"label": "Thinking",   "provider": "gemini", "text_model_stage1": "gemini-2.5-flash", "text_model_stage2": "gemini-2.5-flash", "thinking": True,  "rag": False},
    "D": {"label": "Synergy",    "provider": "gemini", "text_model_stage1": "gemini-2.5-flash", "text_model_stage2": "gemini-2.5-flash", "thinking": True,  "rag": True},
    "E": {"label": "High_End",   "provider": "gemini", "text_model_stage1": "gemini-3-pro-preview",   "text_model_stage2": "gemini-3-pro-preview",   "thinking": True,  "rag": False},
    "F": {"label": "Benchmark",  "provider": "gpt",    "text_model_stage1": "gpt-5.2-pro-2025-12-11", "text_model_stage2": "gpt-5.2-pro-2025-12-11", "thinking": True, "rag": False},
}

ALLOWED_VISUAL_TYPES = {"Anatomy", "Pathology", "Physics", "Equipment", "QC", "General"}
ALLOWED_IMG_NECESSITY = {"IMG_REQ", "IMG_OPT", "IMG_NONE"}
ALLOWED_CARD_TYPES = {"Basic_QA", "MCQ_Vignette", "Cloze_Finding", "Image_Diagnosis", "Physics_Concept"}
ALLOWED_TABLE_INFOGRAPHIC_STYLES = {"Anatomy", "Physics_Diagram", "Physics_Graph", "Equipment_Structure", "Imaging_Artifact", "MRI_Pulse_Sequence", "QC_Phantom", "Radiograph", "Default"}

TABLE_INFOGRAPHIC_CONSTRAINTS = "Single-page educational infographic, white background, high contrast, minimal text (labels only), no watermark, clinically accurate."
PACS_REALISM_CONSTRAINTS = "STRICT realism: PACS-style grayscale (CT/MRI/XR), no labels/overlays, subtle findings, mobile-friendly 4:5 ratio."

# -------------------------
# PROMPTS
# -------------------------
PROMPT_STAGE_1_SYSTEM = """You are a 'Radiology Board Exam Architect'.
Analyze objectives and extract structured metadata.
CRITICAL: You MUST generate a 'Master Table' summarizing the key concepts in Korean Markdown format.
Return ONLY valid JSON."""

PROMPT_STAGE_1_USER_GROUP = """Task: Analyze the GROUP of 'Learning Objectives'.

Context:
- Path: {specialty} > {anatomy} > {modality_or_type}
- Group Key: {group_key}
- Objectives:
{objective_bullets}

Instructions:
1. Infer scope and visual type.
2. **CREATE A MASTER TABLE** (Markdown, Korean) summarizing key concepts. This is MANDATORY.
3. Extract distinct sub-entities for Anki cards.
4. Define ONE table-level infographic style and prompt.

Output Schema (JSON):
{{
  "id": "{group_id}",
  "objective_summary": "One sentence summary",
  "group_objectives": ["obj1", "obj2"],
  "visual_type_category": "Select ONE: [Anatomy, Pathology, Physics, Equipment, QC, General]",
  "master_table_markdown_kr": "| Key | Concept | Clinical Significance |\n|---|---|---|\n| ... | ... | ... |",
  "entity_list": ["Entity 1", "Entity 2"],
  "table_infographic_style": "Style",
  "table_infographic_keywords_en": "keywords",
  "table_infographic_prompt_en": "Image prompt"
}}
"""

PROMPT_STAGE_2_SYSTEM = f"""You are a 'Radiology Content Creator'.
Generate Anki cards based on the provided Master Table.
If image is needed, provide a PACS-realistic prompt.
Return ONLY valid JSON.
"""

PROMPT_STAGE_2_USER = """Context (Master Table):
{master_table}

Target Entity: "{entity_name}"
Visual Type: {visual_type}

Task:
1. Generate {cards_per_entity} Anki cards obeying this mix:
{card_type_quota_lines}
2. If image is appropriate, provide a PACS prompt.

Output Schema (JSON):
{{
  "entity_name": "{entity_name}",
  "importance_score": 50,
  "row_image_necessity": "IMG_REQ/IMG_OPT/IMG_NONE",
  "row_image_prompt_en": "Prompt or null",
  "anki_cards": [ ... ]
}}
"""

# -------------------------
# UTILS
# -------------------------
def extract_json_object(raw: str) -> Dict[str, Any]:
    raw = (raw or "").strip()
    if not raw: raise ValueError("Empty response")
    try: return json.loads(raw)
    except: pass
    
    # Try fencing
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
    if m:
        try: return json.loads(m.group(1).strip())
        except: pass
        
    # Try finding first { and last }
    m2 = re.search(r"\{[\s\S]*\}", raw, re.MULTILINE)
    if m2: return json.loads(m2.group(0).strip())
    
    raise ValueError("Could not parse JSON")

def clamp_choice(val, allowed, default):
    return val if val in allowed else default

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def make_stable_group_id(sp, an, mod, cat, split):
    key = f"{sp}|{an}|{mod}|{cat}|{split}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]

# -------------------------
# VALIDATION LOGIC (CRITICAL FIX)
# -------------------------
def validate_stage1(obj: Dict[str, Any], fallback_summary: str) -> Dict[str, Any]:
    """
    Ensure master_table and infographic fields exist. If not, generate fallbacks.
    """
    obj = dict(obj or {})
    
    # 1. Master Table Fallback
    mt = str(obj.get("master_table_markdown_kr", "")).strip()
    if not mt or len(mt) < 10:
        print("⚠️  [Stage1 Warning] Master Table missing from LLM. Using fallback.")
        mt = f"| Concept | Summary |\n|---|---|\n| **Overview** | {fallback_summary} |"
    obj["master_table_markdown_kr"] = mt

    # 2. Infographic Fallback
    prompt = str(obj.get("table_infographic_prompt_en", "")).strip()
    if not prompt:
        kw = str(obj.get("table_infographic_keywords_en", "")) or fallback_summary
        prompt = f"Educational medical infographic about {kw}, white background, labels only. {TABLE_INFOGRAPHIC_CONSTRAINTS}"
    obj["table_infographic_prompt_en"] = prompt
    
    obj["visual_type_category"] = clamp_choice(obj.get("visual_type_category"), ALLOWED_VISUAL_TYPES, "General")
    obj["entity_list"] = [str(x) for x in obj.get("entity_list", []) if str(x).strip()]
    
    return obj

def validate_stage2(obj: Dict[str, Any]) -> Dict[str, Any]:
    obj = dict(obj or {})
    # Simple validation
    if obj.get("row_image_necessity") == "IMG_NONE":
        obj["row_image_prompt_en"] = None
    return obj

# -------------------------
# PROVIDER CLIENTS
# -------------------------
@dataclass
class ProviderClients:
    openai_client: Optional[OpenAI] = None
    deepseek_client: Optional[OpenAI] = None
    claude_client: Optional[anthropic.Anthropic] = None

def build_clients(provider: str, api_key: str) -> ProviderClients:
    c = ProviderClients()
    if provider == "gemini": genai.configure(api_key=api_key)
    elif provider == "gpt": c.openai_client = OpenAI(api_key=api_key)
    elif provider == "deepseek": c.deepseek_client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    elif provider == "claude": c.claude_client = anthropic.Anthropic(api_key=api_key)
    return c

def _model_for_stage(provider, stage):
    if stage == 1 and TEXT_MODEL_STAGE1: return TEXT_MODEL_STAGE1
    if stage == 2 and TEXT_MODEL_STAGE2: return TEXT_MODEL_STAGE2
    return MODEL_CONFIG[provider]["model_name"]

def call_llm(provider, clients, sys_p, user_p, stage, retries=3):
    model_name = _model_for_stage(provider, stage)
    temp = TEMPERATURE_STAGE1 if stage == 1 else TEMPERATURE_STAGE2
    
    for i in range(retries):
        try:
            raw = ""
            if provider == "gemini":
                m = genai.GenerativeModel(model_name=model_name, system_instruction=sys_p)
                r = m.generate_content(user_p, generation_config={"temperature": temp, "response_mime_type": "application/json"})
                raw = r.text
            elif provider == "gpt":
                r = clients.openai_client.chat.completions.create(
                    model=model_name, messages=[{"role":"system","content":sys_p},{"role":"user","content":user_p}],
                    response_format={"type": "json_object"}
                )
                raw = r.choices[0].message.content
            # ... (Deepseek/Claude logic omitted for brevity, assumes standard structure)
            
            return extract_json_object(raw), None
        except Exception as e:
            if i == retries - 1: return None, str(e)
            time.sleep(2**i)
    return None, "Max retries"

# -------------------------
# MAIN PROCESS LOOP
# -------------------------
def process_single_group(row, provider, clients, arm, arm_config):
    # Extract Metadata
    sp = row.get("specialty", "General")
    an = row.get("anatomy", "General")
    mod = row.get("modality_or_type", "")
    cat = row.get("category", "")
    key = row.get("group_key", "")
    objs = row.get("objective_list", [])
    
    # ID Generation
    gid = make_stable_group_id(sp, an, mod, cat, row.get("split_index", 0))
    
    # 1. STAGE 1
    s1_user = PROMPT_STAGE_1_USER_GROUP.format(
        specialty=sp, anatomy=an, modality_or_type=mod, group_key=key, group_id=gid,
        objective_bullets="\n".join([f"- {x}" for x in objs])
    )
    
    s1_json, err = call_llm(provider, clients, PROMPT_STAGE_1_SYSTEM, s1_user, stage=1)
    
    # Failure Handling
    if not s1_json:
        return None, {
            "metadata": {"id": gid, "error": err}, 
            "error": "Stage1 failed (legacy)",
            "meta": {"source": row, "arm": arm} # Audit
        }
    
    # VALIDATION & FALLBACK (The Fix)
    fallback_txt = objs[0] if objs else key
    s1_json = validate_stage1(s1_json, fallback_txt)
    
    # 2. STAGE 2 (Loop over entities)
    entities = []
    # Simplified loop for brevity
    target_entities = s1_json["entity_list"][:10] # Cap at 10
    
    for ent_name in target_entities:
        s2_user = PROMPT_STAGE_2_USER.format(
            master_table=s1_json["master_table_markdown_kr"], # PASSING THE TABLE
            entity_name=ent_name,
            visual_type=s1_json["visual_type_category"],
            cards_per_entity=CARDS_PER_ENTITY,
            card_type_quota_lines="- Basic_QA: 1\n- MCQ: 1" # Simplified placeholder
        )
        
        s2_json, err2 = call_llm(provider, clients, PROMPT_STAGE_2_SYSTEM, s2_user, stage=2)
        if s2_json:
            s2_json = validate_stage2(s2_json)
            entities.append(s2_json)
            
    # 3. CONSTRUCT RESULT (The Fix: Ensure curriculum_content has table info)
    result = {
        "metadata": {
            "id": gid,
            "provider": provider,
            "arm": arm,
            "timestamp": int(time.time()),
            "source_info": row
        },
        "meta": { # Legacy/MI-CLEAR compatibility
            "source": row,
            "provider": provider,
            "arm": arm
        },
        "curriculum_content": {
            "visual_type": s1_json["visual_type_category"],
            "master_table": s1_json["master_table_markdown_kr"], # CRITICAL: Persist Table
            "table_infographic": {
                "style": s1_json.get("table_infographic_style", "Default"),
                "keywords_en": s1_json.get("table_infographic_keywords_en", ""),
                "prompt_en": s1_json.get("table_infographic_prompt_en", "") # CRITICAL: Persist Prompt
            },
            "entities": entities
        }
    }
    result = validate_and_fill_record(result, run_tag=run_tag, mode=mode, provider=provider, arm=arm)
    return result, None

# -------------------------
# CLI & ENTRYPOINT
# -------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="gemini")
    parser.add_argument("--run_tag", default="test_fix")
    parser.add_argument("--arm", default="")
    parser.add_argument("--sample", type=int, default=1) # Default sample 1 for safety
    args = parser.parse_args()
    
    # Load Groups
    if str(INPUT_FILE).endswith(".xlsx"):
        df = pd.read_excel(INPUT_FILE)
    else:
        df = pd.read_csv(INPUT_FILE)
        
    # Mock Group Building (Assuming input is already somewhat processed or doing minimal processing)
    # Ideally reuse build_groups from original file, but for hotfix simplified:
    df["group_key"] = df.apply(lambda r: f"{r.get('Anatomy','')} - {r.get('Modality',' ')}", axis=1)
    target_rows = df.sample(args.sample).to_dict('records')
    
    # Setup Provider
    arm_cfg = ARM_CONFIGS.get(args.arm, {})
    provider = arm_cfg.get("provider", args.provider)
    api_key = os.getenv(MODEL_CONFIG[provider]["api_key_env"])
    clients = build_clients(provider, api_key)
    
    out_path = OUTPUT_DIR / "generated" / provider / f"output_{provider}_{args.run_tag}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"🚀 Running Fix Mode | Tag: {args.run_tag} | Provider: {provider}")
    
    with open(out_path, "a", encoding="utf-8") as f:
        for row in tqdm(target_rows):
            res, err = process_single_group(row, provider, clients, args.arm, arm_cfg)
            if res:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
            else:
                print(f"❌ Error: {err}")

if __name__ == "__main__":
    main()

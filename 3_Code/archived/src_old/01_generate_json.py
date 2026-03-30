"""
[LEGACY/OLD VERSION] MeducAI Generation Script - Iteration 2
Target: 3_code/src_old/01_generate_json.py
Policy: Arm A High-Yield + Medical Korean (Enhanced)
"""
from __future__ import annotations
import argparse, json, math, os, re, time, hashlib, sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List
from dotenv import load_dotenv
import pandas as pd
from tqdm import tqdm

# Provider imports
try:
    from google import genai
    from google.genai import types
except ImportError:
    pass
from openai import OpenAI
import anthropic

# -------------------------
# Configuration
# -------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

INPUT_FILE = BASE_DIR / "2_Data" / "processed" / "Radiology_Curriculum_Weight_Factor.xlsx"
OUTPUT_DIR = BASE_DIR / "2_Data" / "metadata"

CARDS_PER_ENTITY = 5 
CARD_TYPE_RATIOS_SPEC = "Basic_QA:0.40,Cloze_Finding:0.30,MCQ_Vignette:0.30"

MODEL_CONFIG = {
    "gemini": {"model_name": "gemini-2.5-flash", "api_key_env": "GOOGLE_API_KEY"},
    "gpt": {"model_name": "gpt-5.2-pro", "api_key_env": "OPENAI_API_KEY"},
}

ARM_CONFIGS = {
    "A": {"label": "Baseline", "provider": "gemini", "thinking": False, "rag": False},
}

# -------------------------
# Prompts (Refined for Yield & Medical Korean)
# -------------------------
PROMPT_STAGE_1_SYSTEM = """You are a 'Radiology Board Exam Architect'.
Extract metadata to generate maximum high-quality Anki cards.
CRITICAL: You MUST extract at least 3 distinct clinical entities (diseases, signs, anatomy) per group.
Medical Safety: Stick to standard guidelines.
Return ONLY valid JSON."""

PROMPT_STAGE_1_USER_GROUP = """Task: Analyze Learning Objectives.
Input: {group_key}
Tags: {anki_tags}

Instructions:
1) Infer scope.
2) Classify visual type.
3) Draft Master Table (Korean Markdown).
4) **Entity Extraction (CRITICAL)**: Extract 3-5 distinct sub-entities. If general, split by subtypes or key concepts.
5) Style/Keywords/ImagePrompt.

Output Schema (JSON):
{{
  "id": "{group_id}",
  "objective_summary": "Summary",
  "group_objectives": ["..."],
  "visual_type_category": "General",
  "master_table_markdown_kr": "Markdown",
  "entity_list": ["Entity1", "Entity2", "Entity3"],
  "table_infographic_style": "Default",
  "table_infographic_keywords_en": "Keywords",
  "table_infographic_prompt_en": "Prompt"
}}"""

# [KEY CHANGE] Medical Korean Policy + Formatting
PROMPT_STAGE_2_SYSTEM = """You are a 'Radiology Content Creator'.

LANGUAGE POLICY (MEDICAL KOREAN):
- **Sentence Structure**: Korean (e.g., ~은/는, ~관찰됨, ~를 시사함).
- **Medical Terms**: English (Diagnosis, Anatomy, Signs, Pathophysiology).
- **DO NOT TRANSLATE** standard terms (e.g., Use 'Pneumonia' not '폐렴', 'HCC' not '간세포암' if HCC is standard).
- **Example**: "Liver Cirrhosis 환자에서 Portal Hypertension 소견이..." (Good).

FORMATTING (STRICT):
1. **Basic_QA**: Front=Question, Back=Concise Answer.
2. **MCQ**: Front=Vignette+Options (A,B,C,D), Back=Answer(A)+Explanation.
3. **Cloze**: Use {{c1::text}}. **DO NOT** repeat the answer in the Back field.

Return ONLY valid JSON."""

PROMPT_STAGE_2_USER = """Context: {master_table}
Entity: "{entity_name}"
Task: Generate {cards_per_entity} cards.
Mix: {card_type_quota_lines}
Image Policy: PACS-realistic, grayscale, no labels.

Output Schema (JSON):
{{
  "entity_name": "{entity_name}",
  "importance_score": 50,
  "row_image_necessity": "IMG_REQ",
  "row_image_prompt_en": "...",
  "anki_cards": [
    {{ "card_type": "...", "front": "...", "back": "...", "tags": ["..."] }}
  ]
}}"""

# -------------------------
# Helpers
# -------------------------
def apportion_counts(total, ratios):
    raw = {k: ratios[k]*total for k in ratios}
    base = {k: int(math.floor(v)) for k, v in raw.items()}
    rem = total - sum(base.values())
    for k in sorted(ratios, key=lambda x: raw[x]-base[x], reverse=True):
        if rem <= 0: break
        base[k]+=1
        rem-=1
    return base

def parse_ratio_spec(spec):
    out = {}
    for p in spec.split(","):
        if ":" in p:
            k, v = p.split(":", 1)
            try: out[k.strip()] = float(v)
            except: pass
    return {k: v/sum(out.values()) for k, v in out.items()} if sum(out.values()) > 0 else {}

def call_llm(provider, clients, sys_p, user_p, stage, arm_cfg):
    try:
        model = MODEL_CONFIG[provider]["model_name"]
        if provider == "gemini":
            cfg = types.GenerateContentConfig(temperature=0.3, response_mime_type="application/json")
            resp = clients.gemini_client.models.generate_content(
                model=model, contents=f"System: {sys_p}\nUser: {user_p}", config=cfg
            )
            return json.loads(resp.text), None
        elif provider == "gpt":
            resp = clients.openai_client.chat.completions.create(
                model=model, messages=[{"role":"system","content":sys_p},{"role":"user","content":user_p}],
                response_format={"type": "json_object"}
            )
            return json.loads(resp.choices[0].message.content), None
    except Exception as e:
        return None, str(e)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="gemini")
    parser.add_argument("--arm", default="A")
    parser.add_argument("--sample", type=int, default=0)
    parser.add_argument("--run_tag", default="")
    args = parser.parse_args()

    pkey = MODEL_CONFIG[args.provider]["api_key_env"]
    if not os.getenv(pkey): return print(f"Missing {pkey}")
    
    class Clients: pass
    c = Clients()
    if args.provider=="gemini": c.gemini_client = genai.Client(api_key=os.getenv(pkey))
    if args.provider=="gpt": c.openai_client = OpenAI(api_key=os.getenv(pkey))

    df = pd.read_excel(INPUT_FILE)
    if args.sample > 0:
        df = df.head(args.sample)
    
    run_tag = args.run_tag or time.strftime("%Y%m%d_%H%M")
    out_dir = OUTPUT_DIR / "generated" / run_tag
    out_dir.mkdir(parents=True, exist_ok=True)
    fpath = out_dir / f"output_{args.provider}_{run_tag}__arm{args.arm}.jsonl"

    print(f"🚀 Running Arm {args.arm} | Sample: {len(df)} | Output: {fpath}")

    ratios = parse_ratio_spec(CARD_TYPE_RATIOS_SPEC)

    for i, row in tqdm(df.iterrows(), total=len(df)):
        # Stage 1
        s1_user = PROMPT_STAGE_1_USER_GROUP.format(
            group_id=i, group_key=row.get("objective", "Unknown"), anki_tags="Radiology",
            objective_bullets=f"- {row.get('objective', '')}"
        )
        s1, err = call_llm(args.provider, c, PROMPT_STAGE_1_SYSTEM, s1_user, 1, {})
        
        # [DEBUG] Entity Extraction Check
        entities = s1.get("entity_list", []) if s1 else []
        if not entities:
            # Fallback: Use objective as entity if extraction fails
            entities = [str(row.get("objective", "General Topic"))[:50]]
            if s1: s1["entity_list"] = entities # Update s1 for consistency
        
        # Stage 2
        gen_entities = []
        quotas = apportion_counts(CARDS_PER_ENTITY, ratios)
        quota_lines = "\n".join([f"- {k}: {v}" for k,v in quotas.items()])
        
        for ent in entities[:5]: # Cap at 5 entities per group
            s2_user = PROMPT_STAGE_2_USER.format(
                master_table=s1.get("master_table_markdown_kr",""), 
                entity_name=ent, 
                visual_type=s1.get("visual_type_category",""),
                cards_per_entity=CARDS_PER_ENTITY,
                card_type_quota_lines=quota_lines
            )
            s2, err2 = call_llm(args.provider, c, PROMPT_STAGE_2_SYSTEM, s2_user, 2, {})
            if s2: gen_entities.append(s2)
        
        final = {
            "metadata": {
                "id": str(i), 
                "arm": args.arm, 
                "source_info": {
                    "group_key": str(row.get("objective"))[:20],
                    "specialty": "Gen", "anatomy": "Gen", "modality_or_type": "Gen", "category": "Gen",
                    "group_weight_sum": 1.0, "tags_agg": "Gen"
                }
            },
            "curriculum_content": {"entities": gen_entities, "objective": row.get("objective"), "table_infographic": {}}
        }
        with open(fpath, "a", encoding="utf-8") as f:
            f.write(json.dumps(final, ensure_ascii=False)+"\n")

if __name__ == "__main__":
    main()

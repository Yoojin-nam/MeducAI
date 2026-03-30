#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MeducAI Pipeline v3.5: Group-first + Ratio-controlled Card/Image Mix (ENV-driven)
--------------------------------------------------------------------------------
- output_{provider}_{run_tag}.jsonl (JSONL: 1 group per line)
- record_id == group_id (stable)

[KEY FEATURES]
1) group-first (record_id = group_id)
2) Category NaN leakage fix (NaN/None/"nan"/"null" -> "")
3) Card type mix enforced by ENV (per-entity)
   - CARDS_PER_ENTITY
   - CARD_TYPE_RATIOS (e.g., Basic_QA:0.34,Cloze_Finding:0.33,MCQ_Vignette:0.33)
4) Image necessity mix enforced by ENV (per-group, ranked by importance_score)
   - IMAGE_NECESSITY_RATIOS (e.g., IMG_REQ:0.40,IMG_OPT:0.40,IMG_NONE:0.20)
   - IMAGE_ASSIGN_POLICY=RANKED_BY_IMPORTANCE

Notes:
- We strongly encourage enforcing mix at prompt-level (Stage2), and we also apply a
  conservative post-adjustment to prevent extreme skew if the model deviates.
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
    print(f"✅ Loaded .env from: {env_path}")
else:
    print(f"⚠️  Warning: .env file NOT found at: {env_path}")

INPUT_FILE = BASE_DIR / "2_Data" / "processed" / "Radiology_Curriculum_Weight_Factor.xlsx"
OUTPUT_DIR = BASE_DIR / "2_Data" / "metadata"

# --- Grouping ENV ---
GROUP_KEY_MODE = os.getenv("GROUP_KEY_MODE", "AUTO").strip().upper()  # AUTO
try:
    GROUP_MAX_OBJECTIVES = int(os.getenv("GROUP_MAX_OBJECTIVES", "16"))
except ValueError:
    GROUP_MAX_OBJECTIVES = 16

# --- Card budgeting ENV ---
def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default

try:
    BASE_CARDS_PER_GROUP = int(os.getenv("BASE_CARDS_PER_GROUP", "8"))
except ValueError:
    BASE_CARDS_PER_GROUP = 8

try:
    MIN_CARDS_PER_GROUP = int(os.getenv("MIN_CARDS_PER_GROUP", "4"))
except ValueError:
    MIN_CARDS_PER_GROUP = 4

try:
    MAX_CARDS_PER_GROUP = int(os.getenv("MAX_CARDS_PER_GROUP", "20"))
except ValueError:
    MAX_CARDS_PER_GROUP = 20

WEIGHT_TRANSFORM = os.getenv("WEIGHT_TRANSFORM", "LOG1P").strip().upper()

# legacy compatibility (still used as hard cap of extracted entities)
TARGET_COUNT_MIN = 1
TARGET_COUNT_MAX = int(os.getenv("TARGET_COUNT_MAX", "80"))

# --- Mix control (NEW) ---
CARDS_PER_ENTITY = _env_int("CARDS_PER_ENTITY", 3)
CARD_TYPE_RATIOS_SPEC = os.getenv(
    "CARD_TYPE_RATIOS",
    "Basic_QA:0.34,Cloze_Finding:0.33,MCQ_Vignette:0.33"
).strip()

IMAGE_NECESSITY_RATIOS_SPEC = os.getenv(
    "IMAGE_NECESSITY_RATIOS",
    "IMG_REQ:0.40,IMG_OPT:0.40,IMG_NONE:0.20"
).strip()

IMAGE_ASSIGN_POLICY = os.getenv("IMAGE_ASSIGN_POLICY", "RANKED_BY_IMPORTANCE").strip().upper()

# --- Provider/model ENV ---
# Provider selection:
# - For backward compatibility we keep CLI --provider (gemini/gpt/deepseek/claude)
# - If PROVIDER_TEXT exists, it overrides CLI provider
PROVIDER_TEXT_ENV = os.getenv("PROVIDER_TEXT", "").strip().lower()

# Stage-specific model names (optional overrides)
TEXT_MODEL_STAGE1 = os.getenv("TEXT_MODEL_STAGE1", "").strip()
TEXT_MODEL_STAGE2 = os.getenv("TEXT_MODEL_STAGE2", "").strip()

TEMPERATURE_STAGE1 = _env_float("TEMPERATURE_STAGE1", 0.2)
TEMPERATURE_STAGE2 = _env_float("TEMPERATURE_STAGE2", 0.3)
MAX_TOKENS_STAGE1 = _env_int("MAX_TOKENS_STAGE1", 8192)
MAX_TOKENS_STAGE2 = _env_int("MAX_TOKENS_STAGE2", 8192)
TIMEOUT_S = _env_int("TIMEOUT_S", 120)


MODEL_CONFIG = {
    "gemini": {
        "model_name": "gemini-2.5-pro",
        "api_key_env": "GOOGLE_API_KEY",
    },
    "gpt": {
        "model_name": "gpt-5.2-pro-2025-12-11",
        "api_key_env": "OPENAI_API_KEY",
    },
    "deepseek": {
        "model_name": "deepseek-reasoner",
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com",
    },
    "claude": {
        "model_name": "claude-opus-4-5-20251101",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
}



# -------------------------
# 6-Arm QA Design (S0) - Optional CLI override
# -------------------------
# If --arm is provided, we override provider/model settings for reproducible S0 generation.
# Arms are aligned to the QA Framework v1.6+ intent: E/F are "closed-book" (RAG OFF).
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

# Card types (UPDATED: add Basic_QA)
ALLOWED_CARD_TYPES = {
    "Basic_QA",        # 단답형 Q/A
    "MCQ_Vignette",
    "Cloze_Finding",
    "Image_Diagnosis",
    "Physics_Concept",
}

# Table-level infographic styles (one infographic per Master Table)
ALLOWED_TABLE_INFOGRAPHIC_STYLES = {
    "Anatomy",
    "Physics_Diagram",
    "Physics_Graph",
    "Equipment_Structure",
    "Imaging_Artifact",
    "MRI_Pulse_Sequence",
    "QC_Phantom",
    "Radiograph",
    "Default",
}

TABLE_INFOGRAPHIC_CONSTRAINTS = (
    "Additional constraints: single-page educational infographic figure, "
    "white background, high contrast, minimal text (labels only), "
    "no watermark, no logo, print-ready, clinically accurate."
)

PACS_REALISM_CONSTRAINTS = (
    "STRICT realism constraints: realistic PACS-style appearance, authentic radiologic contrast and mild noise; "
    "grayscale only for CT/MRI/X-ray; no labels/arrows/circles/text overlays; "
    "do not exaggerate findings; keep subtle and clinically plausible; "
    "single image only; mobile-friendly vertical ratio 4:5 preferred (or 3:4)."
)

PHYSICS_TEXT_MATH_POLICY = (
    "NO-LaTeX POLICY (STRICT, MUST FOLLOW):\n"
    "- Do NOT use LaTeX in any form: no $...$, no \\commands (e.g., \\frac, \\times, \\rightarrow, \\leq, \\geq).\n"
    "- Write all formulas in plain text only.\n"
    "- Allowed math symbols: ×, /, →, ∝, ≥, ≤, ±, °.\n"
    "- Fractions must be written as a / b (e.g., d = c × t / 2).\n"
    "- Use standard radiology/physics notation for subscripts: B0, T1, T2, T2* (no LaTeX sub/superscripts).\n"
    "- Units must be plain text: cm, mm, Hz, kHz, MHz, ms, s, dB, Gy, mGy, mAs, kVp.\n"
    "- Ultrasound: distance formula should be written as d = c × t / 2; explain why /2 when relevant.\n"
    "- CT: relations should be plain text like Noise ∝ 1 / √mAs, Dose ∝ mAs.\n"
    "- MRI: relations should be plain text like SNR ∝ voxel volume; Higher B0 → higher SNR.\n"
    "- Do NOT use *, ->, <=, >=. Use ×, →, ≤, ≥.\n"
)


# -------------------------
# Prompts
# -------------------------
PROMPT_STAGE_1_SYSTEM = """\
You are a 'Radiology Board Exam Architect' designed to structure medical knowledge.
Your goal is to analyze learning objectives and extract structured metadata for Anki card creation.

CRITICAL MEDICAL SAFETY:
- Do not invent statistics or prevalence data.
- If a concept is controversial, stick to standard textbook guidelines (e.g., AJCC 8th Ed, WHO Classification).

Return ONLY valid JSON that matches the provided schema. No extra text.
"""

PROMPT_STAGE_1_USER_GROUP = """\
Task: Analyze the provided GROUP of 'Learning Objectives' for Radiology Board Exam preparation.

Input Context:
- Group Path: {specialty} > {anatomy} > {modality_or_type}{category_suffix}
- Group Key: {group_key}
- Split Index (if any): {split_index}
- Group Size: {group_size} objectives
- Group Weight Sum: {group_weight_sum}
- Tags (aggregated): {anki_tags}
- Target Card Count: {target_count} (distinct sub-entities to extract, group-level)

Group Objectives (list):
{objective_bullets}

Instructions:
1) Infer the coherent scope of the group from the Group Path + objectives list.
2) Classify the visual type (Anatomy / Pathology / Physics / Equipment / QC / General).
3) Draft ONE Master Table (Korean Markdown) summarizing key concepts for the entire group.
4) Extract a list of distinct sub-entities to generate Anki cards for (group-level).

Table-level Infographic (Master Table -> ONE image):
5) Decide ONE table-level infographic style for generating a SINGLE infographic image for the entire Master Table.
   - Choose from: [Anatomy, Physics_Diagram, Physics_Graph, Equipment_Structure, Imaging_Artifact, MRI_Pulse_Sequence, QC_Phantom, Radiograph, Default]
6) Extract concise English keywords (10–25 words) that summarize the whole Master Table.
7) Compose a final English image prompt for an image generator using the selected style + keywords.
   - Must be a single-page educational infographic with minimal text (labels only).
   - White background, high contrast, clinically accurate, no watermark/logo.

Output Schema (JSON):
{{
  "id": "{group_id}",
  "objective_summary": "ONE representative summary sentence for the group (Korean or English)",
  "group_objectives": ["objective 1", "objective 2", "..."],
  "visual_type_category": "Select ONE: [Anatomy, Pathology, Physics, Equipment, QC, General]",
  "master_table_markdown_kr": "| Header1 | Header2 | ... | (Markdown Table String)",
  "entity_list": ["Entity Name 1", "Entity Name 2", "..."],
  "table_infographic_style": "Select ONE: [Anatomy, Physics_Diagram, Physics_Graph, Equipment_Structure, Imaging_Artifact, MRI_Pulse_Sequence, QC_Phantom, Radiograph, Default]",
  "table_infographic_keywords_en": "10–25 English words, comma-separated or short phrase",
  "table_infographic_prompt_en": "Final image prompt string for generating ONE table-level infographic"
}}
"""

PROMPT_STAGE_2_SYSTEM = f"""\
You are a 'Radiology Content Creator' for Anki Flashcards.
Your goal is to generate board-relevant Anki cards AND (optionally) ONE realistic PACS-style radiology image prompt per entity.

PACS-REALISTIC IMAGE PROMPT RULES (STRICT):
- If 'IMG_REQ' or 'IMG_OPT', produce an English prompt to generate ONE realistic radiology image (PACS-like).
- Grayscale only for CT/MRI/X-ray; authentic radiologic contrast and mild noise.
- No labels, arrows, circles, text overlays, or watermark/logo.
- Do NOT exaggerate findings; keep subtle and clinically plausible.
- Prefer a mobile-friendly vertical ratio 4:5 (or 3:4).
- If image is not appropriate, set IMG_NONE and row_image_prompt_en = null.

{PHYSICS_TEXT_MATH_POLICY}

Return ONLY valid JSON that matches the schema. No extra text.
"""

PROMPT_STAGE_2_USER = """\
Context (Master Table):
{master_table}

Target Entity: "{entity_name}"
Domain (broad): {visual_type}

CARD MIX POLICY (MANDATORY):
- Generate exactly {cards_per_entity} Anki cards in total for this entity.
- Enforce this card-type distribution exactly:
{card_type_quota_lines}

IMAGE POLICY:
- Decide whether an Anki image would meaningfully support learning for this entity.
- If yes: set row_image_necessity to IMG_REQ or IMG_OPT and provide a PACS-realistic image prompt.
- If no: set IMG_NONE and row_image_prompt_en = null.

IMPORTANT:
- The image prompt must be "PACS-realistic radiology image" (not an illustration).
- No annotations on the image.
- If modality/plane/FOV are ambiguous, choose the most standard diagnostic scenario for board exams.

PHYSICS OUTPUT STYLE (STRICT):
- Do NOT use LaTeX ($...$ or \\commands). Use plain text math only.
- Use ×, /, →, ∝, ≥, ≤, ±, ° when needed.
- Fractions must be written like: d = c × t / 2
- Do not use *, ->, <=, >=.

Output Schema (JSON):
{{
  "entity_name": "{entity_name}",
  "importance_score": "Integer 0-100 (100=Must Know)",
  "row_image_necessity": "Select ONE: [IMG_REQ, IMG_OPT, IMG_NONE]",
  "row_image_prompt_en": "English prompt for ONE realistic PACS-style radiology image. Null if IMG_NONE.",

  "image_modality": "Optional. e.g., MRI brain, CT chest, X-ray, ultrasound, etc.",
  "image_plane": "Optional. e.g., axial/coronal/sagittal/AP/PA/lateral.",
  "image_fov": "Optional. Short FOV description.",
  "image_core_concept": "Optional. One sentence describing the key imaging concept.",
  "image_finding_1": "Optional. Key visual feature #1 to show.",
  "image_finding_2": "Optional. Key visual feature #2 to show.",
  "image_exclude_1": "Optional. One key feature to exclude (e.g., hemorrhage, invasion, labels).",

  "anki_cards": [
    {{
      "card_type": "Select: [Basic_QA, MCQ_Vignette, Cloze_Finding, Image_Diagnosis, Physics_Concept]",
      "front": "Question Text (Korean/English mixed allowed)",
      "back": "Answer with concise explanation",
      "tags": ["#Tag1", "#Tag2"]
    }}
  ]
}}
"""


# -------------------------
# Utilities
# -------------------------
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
_JSON_OBJ_RE = re.compile(r"\{[\s\S]*\}", re.MULTILINE)

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def extract_json_object(raw: str) -> Dict[str, Any]:
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Empty response text")

    try:
        return json.loads(raw)
    except Exception:
        pass

    m = _JSON_FENCE_RE.search(raw)
    if m:
        inner = m.group(1).strip()
        try:
            return json.loads(inner)
        except Exception:
            raw = inner

    m2 = _JSON_OBJ_RE.search(raw)
    if m2:
        return json.loads(m2.group(0).strip())

    raise ValueError("Could not extract JSON object")

def clamp_choice(val: Any, allowed: set, default: str) -> str:
    if isinstance(val, str) and val in allowed:
        return val
    return default

def to_int_0_100(x: Any, default: int = 50) -> int:
    try:
        v = int(x)
        return max(0, min(100, v))
    except Exception:
        return default

def safe_float(x: Any, default: float = 1.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default

def _normalize_key_text(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s

def make_stable_group_id(
    specialty: str,
    anatomy: str,
    modality_or_type: str,
    category: str = "",
    split_index: int = 0,
) -> str:
    key = f"{specialty}|{anatomy}|{modality_or_type}|{category}|{split_index}".strip()
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]

def weight_transform(x: float) -> float:
    x = max(0.0, float(x or 0.0))
    if WEIGHT_TRANSFORM == "LOG1P":
        return math.log1p(x)
    if WEIGHT_TRANSFORM == "SQRT":
        return math.sqrt(x)
    if WEIGHT_TRANSFORM == "LINEAR":
        return x
    return math.log1p(x)

def compute_group_target_cards(group_weight_sum: float) -> int:
    w = weight_transform(group_weight_sum)
    calculated = round(BASE_CARDS_PER_GROUP * w) if w > 0 else MIN_CARDS_PER_GROUP
    calculated = max(MIN_CARDS_PER_GROUP, calculated)
    calculated = min(MAX_CARDS_PER_GROUP, calculated)
    return int(calculated)

def _ensure_table_constraints(prompt: str) -> str:
    p = (prompt or "").strip()
    if not p:
        return p
    low = p.lower()
    must_have = ["single-page", "labels", "no watermark", "white background"]
    if any(k not in low for k in must_have):
        return p.rstrip() + " " + TABLE_INFOGRAPHIC_CONSTRAINTS
    return p

def _ensure_pacs_constraints(prompt: str) -> str:
    p = (prompt or "").strip()
    if not p:
        return p
    low = p.lower()
    must_have = ["pacs", "grayscale", "no labels", "no arrows", "no text", "subtle", "single image"]
    if any(k not in low for k in must_have):
        return p.rstrip() + "\n\n" + PACS_REALISM_CONSTRAINTS
    return p


# -------------------------
# Ratio parsing & rounding
# -------------------------
def parse_ratio_spec(spec: str, allowed_keys: set, default: Dict[str, float]) -> Dict[str, float]:
    if not spec:
        return dict(default)

    out: Dict[str, float] = {}
    parts = [p.strip() for p in spec.split(",") if p.strip()]
    for p in parts:
        if ":" not in p:
            continue
        k, v = p.split(":", 1)
        k = k.strip()
        if k not in allowed_keys:
            continue
        try:
            fv = float(v.strip())
        except Exception:
            continue
        if fv < 0:
            continue
        out[k] = fv

    s = sum(out.values())
    if s <= 0:
        return dict(default)

    return {k: (v / s) for k, v in out.items()}

def apportion_counts(total: int, ratios: Dict[str, float]) -> Dict[str, int]:
    total = max(0, int(total))
    if total == 0:
        return {k: 0 for k in ratios.keys()}

    raw = {k: ratios[k] * total for k in ratios.keys()}
    base = {k: int(math.floor(raw[k])) for k in ratios.keys()}
    remainder = total - sum(base.values())
    if remainder <= 0:
        while sum(base.values()) > total:
            kmax = max(base.keys(), key=lambda k: base[k])
            if base[kmax] > 0:
                base[kmax] -= 1
            else:
                break
        return base

    frac = sorted(ratios.keys(), key=lambda k: (raw[k] - base[k]), reverse=True)
    i = 0
    while remainder > 0 and frac:
        k = frac[i % len(frac)]
        base[k] += 1
        remainder -= 1
        i += 1
    return base


# -------------------------
# NO-LaTeX normalizer (conservative)
# -------------------------
_LATEX_INLINE_DOLLAR_RE = re.compile(r"\$([^$]+)\$")

def normalize_no_latex_math(text: str) -> str:
    s = (text or "")
    s = _LATEX_INLINE_DOLLAR_RE.sub(lambda m: m.group(1), s)
    s = s.replace("\\times", "×").replace("\\cdot", "×")
    s = s.replace("\\rightarrow", "→").replace("\\leftarrow", "←")
    s = s.replace("\\geq", "≥").replace("\\leq", "≤")
    s = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"\1 / \2", s)
    s = re.sub(r"\\[A-Za-z]+", "", s)
    s = s.replace("->", "→").replace("<=", "≤").replace(">=", "≥")
    s = re.sub(r'(?<!T\d)\s*\*\s*(?!\s*$)', ' × ', s)
    s = re.sub(r'\s+×\s+', ' × ', s)
    return s.strip()


# -------------------------
# Validation / Normalization
# -------------------------
def validate_stage1(obj: Dict[str, Any], fallback_objective_summary: str, fallback_objectives: List[str]) -> Dict[str, Any]:
    obj = dict(obj or {})
    obj["id"] = str(obj.get("id", "")).strip() or "Unknown"

    if "objective_summary" not in obj or not str(obj.get("objective_summary", "")).strip():
        obj["objective_summary"] = fallback_objective_summary.strip()
    else:
        obj["objective_summary"] = str(obj.get("objective_summary", "")).strip()

    go = obj.get("group_objectives", None)
    if not isinstance(go, list) or len([x for x in go if str(x).strip()]) == 0:
        obj["group_objectives"] = fallback_objectives
    else:
        obj["group_objectives"] = [str(x).strip() for x in go if str(x).strip()]

    obj["objective"] = str(obj.get("objective", "")).strip()
    if not obj["objective"]:
        obj["objective"] = obj["objective_summary"]

    obj["visual_type_category"] = clamp_choice(obj.get("visual_type_category"), ALLOWED_VISUAL_TYPES, "General")
    obj["master_table_markdown_kr"] = str(obj.get("master_table_markdown_kr", "")).strip()

    ent = obj.get("entity_list", [])
    obj["entity_list"] = [str(x).strip() for x in ent if str(x).strip()] if isinstance(ent, list) else []

    obj["table_infographic_style"] = clamp_choice(
        obj.get("table_infographic_style"),
        ALLOWED_TABLE_INFOGRAPHIC_STYLES,
        "Default",
    )
    obj["table_infographic_keywords_en"] = str(obj.get("table_infographic_keywords_en", "")).strip()
    obj["table_infographic_prompt_en"] = str(obj.get("table_infographic_prompt_en", "")).strip()

    if not obj["table_infographic_prompt_en"]:
        kw = obj["table_infographic_keywords_en"] or obj["objective_summary"] or "radiology board exam concept"
        obj["table_infographic_prompt_en"] = (
            f"A high-quality medical infographic of {kw}, educational schematic style, "
            f"white background, labels only. {TABLE_INFOGRAPHIC_CONSTRAINTS}"
        )
    else:
        obj["table_infographic_prompt_en"] = _ensure_table_constraints(obj["table_infographic_prompt_en"])

    return obj


def _build_pacs_template_from_entity(obj: Dict[str, Any]) -> str:
    entity_name = str(obj.get("entity_name", "")).strip() or "target condition"
    modality = str(obj.get("image_modality", "")).strip() or "MRI/CT/X-ray as appropriate"
    plane = str(obj.get("image_plane", "")).strip() or "Standard diagnostic plane"
    fov = str(obj.get("image_fov", "")).strip() or "Region-of-interest centered"
    core_concept = str(obj.get("image_core_concept", "")).strip() or "Show the key diagnostic finding realistically"
    finding_1 = str(obj.get("image_finding_1", "")).strip() or f"Key imaging finding consistent with {entity_name}"
    finding_2 = str(obj.get("image_finding_2", "")).strip() or "Realistic surrounding anatomy and context"
    exclude_1 = str(obj.get("image_exclude_1", "")).strip() or "Any labels/arrows/circles/text overlays or watermark"

    return textwrap.dedent(f"""\
    You are a board-certified radiologist creating a SINGLE realistic PACS-style radiology image
    to accompany a short-answer / single-best-answer board exam question in Anki.

    TARGET CONDITION
    {entity_name}

    IMAGING SCENARIO (MANDATORY)
    • Modality: {modality}
    • Plane: {plane}
    • Field of view: {fov}
    • Key imaging concept to reflect: {core_concept}

    KEY VISUAL FEATURES TO SHOW (STRICT)
    • {finding_1}
    • {finding_2}

    KEY FEATURES TO EXCLUDE (STRICT)
    • {exclude_1}

    STYLE & ANNOTATION RULES (STRICT)
    • Realistic PACS-style appearance (textbook/board-review look)
    • Grayscale only (for CT/MRI/X-ray); authentic contrast and mild noise
    • No labels, no arrows, no circles, no text overlays
    • Do NOT exaggerate findings; keep subtle and clinically plausible

    ANKI FORMAT (MANDATORY)
    • Single image only
    • Mobile-friendly vertical ratio: 4:5 (preferred) or 3:4

    OUTPUT
    Generate ONE realistic radiology image only. IMAGE ONLY. No explanation.
    """)

def validate_stage2(obj: Dict[str, Any]) -> Dict[str, Any]:
    obj = dict(obj or {})
    obj["entity_name"] = str(obj.get("entity_name", "")).strip()
    obj["importance_score"] = to_int_0_100(obj.get("importance_score", 50), default=50)
    obj["row_image_necessity"] = clamp_choice(obj.get("row_image_necessity"), ALLOWED_IMG_NECESSITY, "IMG_OPT")

    if obj["row_image_necessity"] == "IMG_NONE":
        obj["row_image_prompt_en"] = None
    else:
        prompt = obj.get("row_image_prompt_en")
        prompt = None if prompt is None else str(prompt).strip()
        template = _build_pacs_template_from_entity(obj)

        if not prompt:
            obj["row_image_prompt_en"] = template
        else:
            combined = (prompt.rstrip() + "\n\n" + template).strip()
            obj["row_image_prompt_en"] = _ensure_pacs_constraints(combined)

    cards = obj.get("anki_cards", [])
    norm_cards: List[Dict[str, Any]] = []
    if isinstance(cards, list):
        for c in cards:
            if not isinstance(c, dict):
                continue
            front = str(c.get("front", "")).strip()
            back = str(c.get("back", "")).strip()
            if not front or not back:
                continue
            front = normalize_no_latex_math(front)
            back = normalize_no_latex_math(back)
            card_type = clamp_choice(c.get("card_type"), ALLOWED_CARD_TYPES, "Cloze_Finding")
            tags = c.get("tags", [])
            if isinstance(tags, list):
                tags = [str(t).strip() for t in tags if str(t).strip()]
            else:
                tags = []
            norm_cards.append({"card_type": card_type, "front": front, "back": back, "tags": tags})
    obj["anki_cards"] = norm_cards
    return obj


# -------------------------
# Mix enforcement helpers
# -------------------------
DEFAULT_CARD_RATIOS = {"Basic_QA": 0.34, "Cloze_Finding": 0.33, "MCQ_Vignette": 0.33}
DEFAULT_IMG_RATIOS = {"IMG_REQ": 0.40, "IMG_OPT": 0.40, "IMG_NONE": 0.20}

CARD_TYPE_RATIOS = parse_ratio_spec(CARD_TYPE_RATIOS_SPEC, ALLOWED_CARD_TYPES, DEFAULT_CARD_RATIOS)
IMAGE_NECESSITY_RATIOS = parse_ratio_spec(IMAGE_NECESSITY_RATIOS_SPEC, ALLOWED_IMG_NECESSITY, DEFAULT_IMG_RATIOS)

def card_type_quota_lines(cards_per_entity: int, ratios: Dict[str, float]) -> Tuple[str, Dict[str, int]]:
    quotas = apportion_counts(cards_per_entity, ratios)
    keys = [k for k in ["Basic_QA", "Cloze_Finding", "MCQ_Vignette", "Image_Diagnosis", "Physics_Concept"] if k in quotas]
    lines = "\n".join([f"- {k}: {quotas[k]} card(s)" for k in keys])
    return lines, quotas

def enforce_card_quota(cards: List[Dict[str, Any]], quotas: Dict[str, int]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    diagnostics = {"quota": dict(quotas), "deficit": {}, "picked": {}}

    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for c in cards:
        by_type.setdefault(c["card_type"], []).append(c)

    picked: List[Dict[str, Any]] = []
    for t, q in quotas.items():
        pool = by_type.get(t, [])
        take = min(q, len(pool))
        picked.extend(pool[:take])
        diagnostics["picked"][t] = take
        if take < q:
            diagnostics["deficit"][t] = q - take

    total_needed = sum(quotas.values())
    if len(picked) < total_needed:
        remaining = total_needed - len(picked)
        used_ids = set(id(x) for x in picked)
        other = [c for c in cards if id(c) not in used_ids]
        picked.extend(other[:remaining])

    picked = picked[:total_needed]
    return picked, diagnostics

def assign_image_necessity_by_ratio(entities: List[Dict[str, Any]], ratios: Dict[str, float]) -> Dict[str, int]:
    n = len(entities)
    quotas = apportion_counts(n, ratios)
    ranked_idx = sorted(range(n), key=lambda i: int(entities[i].get("importance_score", 0)), reverse=True)

    labels = []
    labels.extend(["IMG_REQ"] * quotas.get("IMG_REQ", 0))
    labels.extend(["IMG_OPT"] * quotas.get("IMG_OPT", 0))
    labels.extend(["IMG_NONE"] * quotas.get("IMG_NONE", 0))
    labels = (labels + ["IMG_OPT"] * n)[:n]

    assigned_counts = {"IMG_REQ": 0, "IMG_OPT": 0, "IMG_NONE": 0}
    for rank_pos, i in enumerate(ranked_idx):
        lab = labels[rank_pos]
        entities[i]["row_image_necessity"] = lab
        if lab == "IMG_NONE":
            entities[i]["row_image_prompt_en"] = None
        else:
            prompt = entities[i].get("row_image_prompt_en")
            if prompt is None or not str(prompt).strip():
                entities[i]["row_image_prompt_en"] = _build_pacs_template_from_entity(entities[i])
            else:
                entities[i]["row_image_prompt_en"] = _ensure_pacs_constraints(str(prompt).strip())
        assigned_counts[lab] += 1

    return assigned_counts


# -------------------------
# Provider Abstraction
# -------------------------
@dataclass
class ProviderClients:
    openai_client: Optional[OpenAI] = None
    deepseek_client: Optional[OpenAI] = None
    claude_client: Optional[anthropic.Anthropic] = None

def build_clients(provider: str, api_key: str) -> ProviderClients:
    clients = ProviderClients()
    if provider == "gemini":
        genai.configure(api_key=api_key)
    elif provider == "gpt":
        clients.openai_client = OpenAI(api_key=api_key)
    elif provider == "deepseek":
        clients.deepseek_client = OpenAI(api_key=api_key, base_url=MODEL_CONFIG["deepseek"]["base_url"])
    elif provider == "claude":
        clients.claude_client = anthropic.Anthropic(api_key=api_key)
    return clients

def _model_for_stage(provider: str, stage: int) -> str:
    default = MODEL_CONFIG[provider]["model_name"]
    if stage == 1 and TEXT_MODEL_STAGE1:
        return TEXT_MODEL_STAGE1
    if stage == 2 and TEXT_MODEL_STAGE2:
        return TEXT_MODEL_STAGE2
    return default

def call_llm(
    provider: str,
    clients: ProviderClients,
    system_prompt: str,
    user_prompt: str,
    stage: int,
    retries: int = 3,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    model_name = _model_for_stage(provider, stage)
    temperature = TEMPERATURE_STAGE1 if stage == 1 else TEMPERATURE_STAGE2
    max_tokens = MAX_TOKENS_STAGE1 if stage == 1 else MAX_TOKENS_STAGE2

    for attempt in range(retries):
        try:
            raw_text = ""

            if provider == "gemini":
                model = genai.GenerativeModel(model_name=model_name, system_instruction=system_prompt)
                resp = model.generate_content(
                    user_prompt,
                    generation_config={
                        "temperature": temperature,
                        "top_p": 0.95,
                        "max_output_tokens": max_tokens,
                        "response_mime_type": "application/json",
                    },
                )
                raw_text = getattr(resp, "text", "") or ""

            elif provider == "gpt":
                if clients.openai_client is None:
                    return None, "OpenAI client not initialized"
n
                resp = clients.openai_client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    
                    
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )
                raw_text = raw_text or ""

            elif provider == "deepseek":
                if clients.deepseek_client is None:
                    return None, "DeepSeek client not initialized"
                try:
n
                    resp = clients.deepseek_client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                        
                        
                        max_tokens=max_tokens,
                        response_format={"type": "json_object"},
                    )
                except Exception:
n
                    resp = clients.deepseek_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt + "\nReturn ONLY valid JSON. No extra text."},
                            {"role": "user", "content": user_prompt},
                        ],
                        
                        
                        max_tokens=max_tokens,
                    )
                raw_text = raw_text or ""

            elif provider == "claude":
                if clients.claude_client is None:
                    return None, "Claude client not initialized"
                resp = clients.claude_client.messages.create(
                    model=model_name,
                    max_tokens=max_tokens,
                    
                    
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                parts = []
                for block in resp.content:
                    if getattr(block, "type", "") == "text":
                        parts.append(block.text)
                raw_text = "\n".join(parts).strip()

            obj = extract_json_object(raw_text)
            return obj, None

        except Exception as e:
            msg = f"{provider} Error (Attempt {attempt + 1}/{retries}): {e}"
            print(f"⚠️ {msg}")
            time.sleep(2 ** attempt)

    return None, "Max retries exceeded"


# -------------------------
# Column helpers / Grouping
# -------------------------
def norm_cell(v: Any) -> str:
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    s = str(v).strip()
    if s.lower() in {"nan", "null", "none", ""}:
        return ""
    return s

# -------------------------
# Tag parsing / Canonicalization (P0-3)
# -------------------------
_TAG_SPLIT_RE = re.compile(r"[|,;/\s]+")

def parse_anki_tag_string(cell: Any) -> List[str]:
    """
    Parse Anki_Tag_String cell into normalized tag tokens.
    - split on: space, comma, semicolon, pipe
    - remove leading '#'
    - drop empties
    """
    s = norm_cell(cell)
    if not s:
        return []
    toks = [t.strip() for t in _TAG_SPLIT_RE.split(s) if t.strip()]
    out: List[str] = []
    for t in toks:
        t = t.lstrip("#").strip()
        if t:
            out.append(t)
    return out

def canonicalize_tag_tokens(tokens: List[str]) -> str:
    """Return stable canonical tag string: sorted unique tokens joined by single space."""
    uniq = sorted(set([t for t in tokens if t]))
    return " ".join(uniq)

def _pick_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    cols = {c.strip(): c for c in df.columns}
    for cand in candidates:
        if cand in cols:
            return cols[cand]
    lower_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        c2 = lower_map.get(cand.lower())
        if c2:
            return c2
    return None

def _get_row_value(row: pd.Series, col: Optional[str], default: str = "") -> str:
    if not col:
        return default
    if row is None:
        return default
    v = row.get(col, default)
    s = norm_cell(v)
    return s if s != "" else norm_cell(default)

def build_groups(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()

    col_specialty = _pick_col(df, ["Specialty"])
    col_anatomy = _pick_col(df, ["Anatomy"])
    col_topic = _pick_col(df, ["Topic"])
    col_objective = _pick_col(df, ["Objective"])
    col_archetype = _pick_col(df, ["Archetype"])
    col_topic_clean = _pick_col(df, ["Topic_Clean", "TopicClean", "topic_clean"])
    col_tags = _pick_col(df, ["Anki_Tag_String", "Tags", "tags"])
    col_weight = _pick_col(df, ["weight_factor", "Weight_Factor", "WeightFactor", "wf"])

    col_modality = _pick_col(df, ["Modality/Type", "Modality_Type", "ModalityType", "Modality", "Type"])
    col_category = _pick_col(df, ["Category", "Subcategory", "Sub-Category", "Sub_Category"])

    def row_group_key(r: pd.Series) -> Tuple[str, str, str, str]:
        specialty = _normalize_key_text(_get_row_value(r, col_specialty, "General")) or "General"
        anatomy = _normalize_key_text(_get_row_value(r, col_anatomy, "General")) or "General"
        modality = _normalize_key_text(_get_row_value(r, col_modality, ""))
        category = _normalize_key_text(_get_row_value(r, col_category, ""))

        if GROUP_KEY_MODE == "AUTO":
            return specialty, anatomy, modality, category
        return specialty, anatomy, modality, category

    tmp = []
    for _, r in df.iterrows():
        specialty, anatomy, modality, category = row_group_key(r)
        obj = _get_row_value(r, col_objective, "")
        topic = _get_row_value(r, col_topic, "")
        archetype = _get_row_value(r, col_archetype, "General")
        topic_clean = _get_row_value(r, col_topic_clean, "").replace(" ", "_")
        tags = _get_row_value(r, col_tags, "")
        wf = safe_float(r.get(col_weight, 1.0) if col_weight else 1.0, default=1.0)

        category_effective = category if category else ""
        group_key = f"{anatomy} – {modality}" + (f" – {category_effective}" if category_effective else "")

        tmp.append({
            "specialty": specialty,
            "anatomy": anatomy,
            "modality_or_type": modality,
            "category": category_effective,
            "group_key": group_key,
            "objective": obj,
            "topic": topic,
            "archetype": archetype,
            "topic_clean": topic_clean,
            "tags": tags,
            "weight_factor": wf,
        })

    dfx = pd.DataFrame(tmp)
    keys = ["specialty", "anatomy", "modality_or_type", "category", "group_key"]
    grp = dfx.groupby(keys, dropna=False, sort=False)

    groups = []
    for k, g in grp:
        specialty, anatomy, modality, category, group_key = k
        objectives = [str(x).strip() for x in g["objective"].tolist() if str(x).strip()]
        topics = sorted({str(x).strip() for x in g["topic"].tolist() if str(x).strip()})
        archetypes = sorted({str(x).strip() for x in g["archetype"].tolist() if str(x).strip()})

        # P0-3: canonical tags derived ONLY from Anki_Tag_String (single source)
        tag_tokens: List[str] = []
        for cell in g["tags"].tolist():
            tag_tokens.extend(parse_anki_tag_string(cell))
        tags_joined = canonicalize_tag_tokens(tag_tokens)

        group_weight_sum = float(g["weight_factor"].sum()) if "weight_factor" in g else float(len(g))
        group_size = int(len(objectives))

        groups.append({
            "specialty": specialty,
            "anatomy": anatomy,
            "modality_or_type": modality,
            "category": category,
            "group_key": group_key,
            "group_size": group_size,
            "group_weight_sum": group_weight_sum,
            "objective_list": objectives,
            "topics": topics,
            "archetypes": archetypes,
            "tags_agg": tags_joined,
        })

    return pd.DataFrame(groups)


def split_group_objectives(group_row: Dict[str, Any]) -> List[Dict[str, Any]]:
    objectives: List[str] = list(group_row.get("objective_list", []) or [])
    if not objectives:
        return []

    chunks = []
    if GROUP_MAX_OBJECTIVES <= 0 or len(objectives) <= GROUP_MAX_OBJECTIVES:
        chunks.append((0, objectives))
    else:
        split_index = 0
        for i in range(0, len(objectives), GROUP_MAX_OBJECTIVES):
            chunks.append((split_index, objectives[i:i + GROUP_MAX_OBJECTIVES]))
            split_index += 1

    out = []
    for split_index, obj_chunk in chunks:
        total = len(objectives)
        chunk_w = float(group_row.get("group_weight_sum", 0.0))
        chunk_weight_sum = chunk_w * (len(obj_chunk) / total) if total > 0 else chunk_w

        out.append({
            **group_row,
            "split_index": split_index,
            "objective_list": obj_chunk,
            "group_size": len(obj_chunk),
            "group_weight_sum": chunk_weight_sum,
        })
    return out


# -------------------------
# Resume helpers
# -------------------------
def load_done_ids(jsonl_path: Path) -> set:
    done = set()
    if not jsonl_path.exists():
        return done
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                rid = obj.get("metadata", {}).get("id")
                if rid:
                    done.add(str(rid))
            except Exception:
                continue
    return done


# -------------------------
# Group Processing
# -------------------------
def process_single_group(
    group_row: Dict[str, Any],
    provider: str,
    clients: ProviderClients,
    arm: str = "",
    arm_config: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:

    specialty = str(group_row.get("specialty", "General")).strip() or "General"
    anatomy = str(group_row.get("anatomy", "General")).strip() or "General"
    modality_or_type = str(group_row.get("modality_or_type", "")).strip()
    category = str(group_row.get("category", "")).strip()
    group_key = str(group_row.get("group_key", "")).strip() or f"{anatomy} – {modality_or_type}".strip(" –")
    split_index = int(group_row.get("split_index", 0))
    group_size = int(group_row.get("group_size", 0))
    group_weight_sum = float(group_row.get("group_weight_sum", 0.0))
    objective_list: List[str] = list(group_row.get("objective_list", []) or [])
    anki_tags = str(group_row.get("tags_agg", "")).strip()  # canonical, space-joined

    group_id = make_stable_group_id(specialty, anatomy, modality_or_type, category, split_index)

    group_target_cards = compute_group_target_cards(group_weight_sum)
    target_count = min(max(TARGET_COUNT_MIN, group_target_cards), TARGET_COUNT_MAX)

    # NOTE(P0-2): group_target_cards is legacy naming.
    # Semantic meaning: number of target entities (not actual card count).
    group_target_entities = int(target_count)

    t_start = time.time()
    prompt_hash = sha256_text(
        PROMPT_STAGE_1_SYSTEM + PROMPT_STAGE_2_SYSTEM + PROMPT_STAGE_1_USER_GROUP + PROMPT_STAGE_2_USER
    )

    # ✅ canonical source info (this will be stored in BOTH metadata.source_info and meta.source)
    source_info = {
        "specialty": specialty,
        "anatomy": anatomy,
        "modality_or_type": modality_or_type,
        "category": category,
        "group_key": group_key,
        "group_size": group_size,
        "group_weight_sum": group_weight_sum,
        "split_index": split_index,
        "tags": anki_tags,
    }

    # Stage1 prompt
    objective_bullets = "\n".join([f"- {x}" for x in objective_list]) if objective_list else "- (none)"
    category_suffix = f" > {category}" if category else ""
    s1_user = PROMPT_STAGE_1_USER_GROUP.format(
        group_id=group_id,
        specialty=specialty,
        anatomy=anatomy,
        modality_or_type=modality_or_type or "General",
        category_suffix=category_suffix,
        group_key=group_key,
        split_index=split_index,
        group_size=group_size,
        group_weight_sum=round(group_weight_sum, 4),
        anki_tags=anki_tags,
        target_count=target_count,
        objective_bullets=objective_bullets,
    )

    s1_json, s1_err = call_llm(provider, clients, PROMPT_STAGE_1_SYSTEM, s1_user, stage=1)
    if not s1_json:
        err_obj = {
            # ✅ keep existing contract
            "metadata": {
            "latency_sec": round(time.time() - t_start, 2),
                "id": group_id,
                "provider": provider,
                "arm": arm,
                "arm_config": arm_config or {},
                "model_version_stage1": _model_for_stage(provider, 1),
                "timestamp": int(time.time()),
                "prompt_hash": prompt_hash,
                "source_info": source_info,
                "target_count": target_count,
                "group_target_entities": group_target_entities,
                "group_target_cards": group_target_cards,
                "weight_factor": group_weight_sum,
                "generation_config": {
                    "temperature_stage1": TEMPERATURE_STAGE1,
                    "max_tokens_stage1": MAX_TOKENS_STAGE1,
                    "temperature_stage2": TEMPERATURE_STAGE2,
                    "max_tokens_stage2": MAX_TOKENS_STAGE2,
                    "timeout_s": TIMEOUT_S,
                },
            },
            # ✅ NEW: mirror for your meta.source debug & future tooling
            "meta": {
                "source": dict(source_info),
                "provider": provider,
                "arm": arm,
                "arm_config": arm_config or {},
                "run_tag": None,
            },
            "error": {"stage": 1, "message": s1_err or "stage1_failed"},
        }
        return None, err_obj

    fallback_summary = objective_list[0] if objective_list else f"{group_key}"
    s1_json = validate_stage1(s1_json, fallback_objective_summary=fallback_summary, fallback_objectives=objective_list)

    quota_lines, quotas = card_type_quota_lines(CARDS_PER_ENTITY, CARD_TYPE_RATIOS)

    detailed_entities: List[Dict[str, Any]] = []
    stage2_warnings: List[Dict[str, Any]] = []

    for entity in s1_json.get("entity_list", [])[:target_count]:
        s2_user = PROMPT_STAGE_2_USER.format(
            master_table=s1_json.get("master_table_markdown_kr", ""),
            entity_name=entity,
            visual_type=s1_json.get("visual_type_category", "General"),
            cards_per_entity=CARDS_PER_ENTITY,
            card_type_quota_lines=quota_lines,
        )
        s2_json, s2_err = call_llm(provider, clients, PROMPT_STAGE_2_SYSTEM, s2_user, stage=2)
        if not s2_json:
            stage2_warnings.append({"entity": str(entity), "message": s2_err or "stage2_failed"})
            continue

        ent_obj = validate_stage2(s2_json)

        cards = ent_obj.get("anki_cards", [])
        fixed_cards, diag = enforce_card_quota(cards, quotas)
        ent_obj["anki_cards"] = fixed_cards

        # P0-3: overwrite card tags (NEVER trust LLM tags)
        canonical_group_tags_list = [t for t in anki_tags.split() if t]
        for c in ent_obj["anki_cards"]:
            ct = (c.get("card_type") or "").strip().lower()
            ct_tag = f"ct_{ct}" if ct else ""
            merged = canonical_group_tags_list + ([ct_tag] if ct_tag else [])
            # de-dup while preserving order
            seen = set()
            merged2: List[str] = []
            for x in merged:
                if x and x not in seen:
                    seen.add(x)
                    merged2.append(x)
            c["tags"] = merged2

        if diag.get("deficit"):
            stage2_warnings.append({
                "entity": ent_obj.get("entity_name", str(entity)),
                "message": "card_type_quota_deficit",
                "detail": diag,
            })

        detailed_entities.append(ent_obj)

    if detailed_entities and IMAGE_ASSIGN_POLICY == "RANKED_BY_IMPORTANCE":
        assigned = assign_image_necessity_by_ratio(detailed_entities, IMAGE_NECESSITY_RATIOS)
        stage2_warnings.append({
            "entity": "__GROUP__",
            "message": "image_necessity_ratio_applied",
            "detail": {"policy": IMAGE_ASSIGN_POLICY, "assigned_counts": assigned, "ratios": IMAGE_NECESSITY_RATIOS},
        })

    result_obj = {
        "metadata": {
            "latency_sec": round(time.time() - t_start, 2),
            "id": group_id,
            "provider": provider,
            "arm": arm,
            "arm_config": arm_config or {},
            "model_version_stage1": _model_for_stage(provider, 1),
            "model_version_stage2": _model_for_stage(provider, 2),
            "timestamp": int(time.time()),
            "prompt_hash": prompt_hash,
            "source_info": source_info,
            "target_count": target_count,
            "group_target_entities": group_target_entities,
            "group_target_cards": group_target_cards,
            "weight_factor": group_weight_sum,
            "generation_config": {
                "temperature_stage1": TEMPERATURE_STAGE1,
                "max_tokens_stage1": MAX_TOKENS_STAGE1,
                "temperature_stage2": TEMPERATURE_STAGE2,
                "max_tokens_stage2": MAX_TOKENS_STAGE2,
                "timeout_s": TIMEOUT_S,
            },
            "stage2_warnings": stage2_warnings,
        },
        # ✅ NEW: mirror for meta.source (so your debug code works)
        "meta": {
            "source": dict(source_info),
            "provider": provider,
            "arm": arm,
            "arm_config": arm_config or {},
            "run_tag": None,
        },
        "curriculum_content": {
            "objective": s1_json.get("objective", s1_json.get("objective_summary", "")),
            "objective_summary": s1_json.get("objective_summary", ""),
            "group_objectives": s1_json.get("group_objectives", objective_list),

            "visual_type": s1_json.get("visual_type_category", "General"),
            "master_table": s1_json.get("master_table_markdown_kr", ""),
            "table_infographic": {
                "style": s1_json.get("table_infographic_style", "Default"),
                "keywords_en": s1_json.get("table_infographic_keywords_en", ""),
                "prompt_en": s1_json.get("table_infographic_prompt_en", ""),
            },
            "entities": detailed_entities,
        },
    }

    return result_obj, None


# -------------------------
# Sampling (group-level)
# -------------------------
def get_stratified_sample(df: pd.DataFrame, n: int) -> pd.DataFrame:
    if n <= 0 or n >= len(df):
        return df

    df = df.copy()
    tag_col = "tags_agg" if "tags_agg" in df.columns else None

    if tag_col is None:
        print("⚠️ No tag column found; random sampling.")
        return df.sample(n=n, random_state=42).reset_index(drop=True)

    mask = df[tag_col].fillna("").astype(str).str.contains(r"Physics|QC|Quality|Safety|물리|품질", case=False, regex=True)
    physics_df = df[mask]
    rest_df = df[~mask]

    n_phys = min(int(n * 0.2), len(physics_df))
    n_rest = n - n_phys

    sample_phys = physics_df.sample(n=n_phys, random_state=42) if n_phys > 0 else df.iloc[0:0]
    sample_rest = rest_df.sample(n=n_rest, random_state=42) if n_rest > 0 else df.iloc[0:0]

    return pd.concat([sample_phys, sample_rest]).sample(frac=1, random_state=42).reset_index(drop=True)


# -------------------------
# Main
# -------------------------
def main():
    parser = argparse.ArgumentParser(description="MeducAI Gen Pipeline v3.5 (group-first + ratio-controlled mix)")
    parser.add_argument("--provider", default="gemini", choices=["gemini", "gpt", "deepseek", "claude"])
    parser.add_argument("--arm", default="", choices=["", "A", "B", "C", "D", "E", "F"],
                        help="Optional: 6-arm S0 QA override. If set, overrides --provider and stage model names.")
    parser.add_argument("--sample", type=int, default=0, help="0 = Process All groups")
    parser.add_argument("--resume", action="store_true", help="Resume within the same run_tag output file")
    parser.add_argument("--sleep_s", type=float, default=0.0, help="Sleep between groups (rate-limit safety)")
    parser.add_argument("--run_tag", type=str, default="", help="Experiment tag for file separation (e.g., exp01, pilotA)")
    args = parser.parse_args()
    # -------------------------
    # Arm override (S0 QA)
    # -------------------------
    arm = (args.arm or "").strip().upper()
    arm_config = ARM_CONFIGS.get(arm, {}) if arm else {}
    if arm_config:
        # Override provider/model globals for this run (single-arm execution)
        args.provider = arm_config["provider"]
        global TEXT_MODEL_STAGE1, TEXT_MODEL_STAGE2
        TEXT_MODEL_STAGE1 = arm_config.get("text_model_stage1", TEXT_MODEL_STAGE1)
        TEXT_MODEL_STAGE2 = arm_config.get("text_model_stage2", TEXT_MODEL_STAGE2)
    else:
        arm = ""
        arm_config = {}


    if PROVIDER_TEXT_ENV and not arm:
        args.provider = PROVIDER_TEXT_ENV

    if not args.run_tag.strip():
        args.run_tag = time.strftime("%Y%m%d_%H%M%S")

    if args.provider not in MODEL_CONFIG:
        raise ValueError(f"Unknown provider: {args.provider}")

    key_env = MODEL_CONFIG[args.provider]["api_key_env"]
    api_key = os.getenv(key_env)
    if not api_key:
        raise ValueError(f"Missing API Key for {args.provider}. Check env var: {key_env}")

    if not INPUT_FILE.exists():
        print(f"❌ Input file missing: {INPUT_FILE}")
        return

    print(f"📂 Loading: {INPUT_FILE.name}")
    df = pd.read_excel(INPUT_FILE)

    print("🧩 Building groups (group-first)...")
    gdf = build_groups(df)
    if gdf.empty:
        print("❌ No groups built. Check column names for Modality/Type and Category.")
        return

    target_gdf = get_stratified_sample(gdf, args.sample)

    provider_dir = OUTPUT_DIR / "generated" / args.provider
    provider_dir.mkdir(parents=True, exist_ok=True)

    jsonl_suffix = f"__arm{arm}" if arm else ""
    jsonl_path = provider_dir / f"output_{args.provider}_{args.run_tag}{jsonl_suffix}.jsonl"

    done_ids = set()
    if args.resume:
        done_ids = load_done_ids(jsonl_path)
        print(f"🔄 Resume enabled: {len(done_ids)} IDs already processed in {jsonl_path.name}")

    clients = build_clients(args.provider, api_key)

    n_total = len(target_gdf)
    n_success = 0
    n_error = 0
    n_skipped = 0

    print(f"🚀 Processing {n_total} groups | provider={args.provider} | run_tag={args.run_tag}")
    print(f"📄 Output JSONL: {jsonl_path}")

    print("🧪 Mix config (ENV):")
    print(f"  - CARDS_PER_ENTITY={CARDS_PER_ENTITY}")
    print(f"  - CARD_TYPE_RATIOS={CARD_TYPE_RATIOS}")
    print(f"  - IMAGE_NECESSITY_RATIOS={IMAGE_NECESSITY_RATIOS}")
    print(f"  - IMAGE_ASSIGN_POLICY={IMAGE_ASSIGN_POLICY}")

    with open(jsonl_path, "a", encoding="utf-8") as f_out:
        for _, row in tqdm(target_gdf.iterrows(), total=n_total):
            group_row = dict(row.to_dict())

            split_rows = split_group_objectives(group_row)
            if not split_rows:
                split_rows = [dict(group_row, split_index=0)]

            for gr in split_rows:
                specialty = str(gr.get("specialty", "General")).strip() or "General"
                anatomy = str(gr.get("anatomy", "General")).strip() or "General"
                modality = str(gr.get("modality_or_type", "")).strip()
                category = str(gr.get("category", "")).strip()
                split_index = int(gr.get("split_index", 0))
                group_id = make_stable_group_id(specialty, anatomy, modality, category, split_index)

                if args.resume and group_id in done_ids:
                    n_skipped += 1
                    continue

                res, err = process_single_group(gr, args.provider, clients=clients, arm=arm, arm_config=arm_config)
                if res is not None:
                    # fill run_tag in meta
                    res["meta"]["run_tag"] = args.run_tag
                    f_out.write(json.dumps(res, ensure_ascii=False) + "\n")
                    n_success += 1
                else:
                    err["meta"]["run_tag"] = args.run_tag
                    f_out.write(json.dumps(err, ensure_ascii=False) + "\n")
                    n_error += 1

                f_out.flush()
                if args.sleep_s > 0:
                    time.sleep(args.sleep_s)

    print("✅ Done.")
    print(f"   success: {n_success}")
    print(f"   skipped: {n_skipped}")
    print(f"   errors:  {n_error}")
    print(f"📄 Saved to: {jsonl_path}")


if __name__ == "__main__":
    main()

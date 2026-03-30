#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MeducAI Step03 – Generate Images (JSONL-only)

Single Source of Truth:
  Step01 JSONL
  2_Data/metadata/generated/<run_tag>/output_<provider>_<run_tag>__armX.jsonl

CSV is NOT used.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv

from google import genai
from google.genai import types

# -------------------------------------------------
# Paths / Env
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
IMAGE_ROOT = BASE_DIR / "2_Data" / "images" / "generated"

env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)
    print(f"✅ Loaded .env from: {env_path}")

# -------------------------------------------------
# Model config
# -------------------------------------------------
IMAGE_MODEL_TABLE = os.getenv("IMAGE_MODEL_TABLE", "").strip()
IMAGE_MODEL_ENTITY = os.getenv("IMAGE_MODEL_ENTITY", "").strip()

MODEL_CONFIG = {
    "gemini": {
        "model_name": "nano-banana-pro-preview",
        "api_key_env": "GOOGLE_API_KEY",
    }
}

# -------------------------------------------------
# Utilities
# -------------------------------------------------
def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def slugify(text: str, max_len: int = 80) -> str:
    t = (text or "").lower().strip()
    t = re.sub(r"[^a-z0-9]+", "_", t)
    t = re.sub(r"_+", "_", t).strip("_")
    return t[:max_len] if len(t) > max_len else t

def sha1_short(text: str, n: int = 10) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]

def write_jsonl(path: Path, obj: Dict[str, Any]):
    ensure_dir(path.parent)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

# -------------------------------------------------
# JSONL Loaders
# -------------------------------------------------
def resolve_step01_jsonl(base_dir: Path, provider: str, run_tag: str, arm: str) -> Path:
    return (
        base_dir
        / "2_Data"
        / "metadata"
        / "generated"
        / run_tag
        / f"output_{provider}_{run_tag}__arm{arm}.jsonl"
    )

def load_table_df(jsonl: Path) -> pd.DataFrame:
    rows = []
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        obj = json.loads(line)
        rid = obj.get("record_id") or obj.get("group_id")
        prompt = obj["curriculum_content"]["table_infographic"]["prompt_en"]
        rows.append({
            "record_id": rid,
            "prompt": prompt,
        })
    return pd.DataFrame(rows)

def load_entity_df(jsonl: Path, include_opt: bool) -> pd.DataFrame:
    rows = []
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        obj = json.loads(line)
        rid = obj.get("record_id") or obj.get("group_id")
        ent = obj["curriculum_content"]["entities"][0]
        need = ent.get("row_image_necessity", "IMG_OPT")
        if need == "IMG_NONE":
            continue
        if need == "IMG_OPT" and not include_opt:
            continue
        rows.append({
            "record_id": rid,
            "entity_name": ent.get("entity_name", "entity"),
            "necessity": need,
            "prompt": ent["row_image_prompt_en"],
        })
    return pd.DataFrame(rows)

# -------------------------------------------------
# Image Generation
# -------------------------------------------------
def build_gemini_client(api_key: str):
    return genai.Client(api_key=api_key)

def extract_image(resp) -> Optional[bytes]:
    for cand in getattr(resp, "candidates", []):
        for part in cand.content.parts:
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                return base64.b64decode(inline.data)
    return None

def generate_image(client, model, prompt, aspect_ratio, image_size):
    try:
        cfg = types.GenerateContentConfig(
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=image_size,
            )
        )
        resp = client.models.generate_content(model=model, contents=[prompt], config=cfg)
        img = extract_image(resp)
        return True, img, "ok" if img else "no_image"
    except Exception as e:
        return False, None, str(e)

# -------------------------------------------------
# Main
# -------------------------------------------------
def main():
    ap = argparse.ArgumentParser("Step03 – JSONL-only image generation")
    ap.add_argument("--provider", default="gemini")
    ap.add_argument("--run_tag", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--input_kind", choices=["table", "entity"], required=True)
    ap.add_argument("--include_opt", action="store_true")
    ap.add_argument("--aspect_ratio", default="4:5")
    ap.add_argument("--image_size", default="2K")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry_run", action="store_true")
    ap.add_argument("--sleep_s", type=float, default=0.2)
    args = ap.parse_args()

    base_dir = BASE_DIR
    jsonl = resolve_step01_jsonl(base_dir, args.provider, args.run_tag, args.arm)
    if not jsonl.exists():
        raise FileNotFoundError(jsonl)

    api_key = os.getenv(MODEL_CONFIG["gemini"]["api_key_env"], "")
    model = (
        IMAGE_MODEL_TABLE if args.input_kind == "table"
        else IMAGE_MODEL_ENTITY
        or MODEL_CONFIG["gemini"]["model_name"]
    )

    df = (
        load_table_df(jsonl)
        if args.input_kind == "table"
        else load_entity_df(jsonl, args.include_opt)
    )

    if args.limit:
        df = df.head(args.limit)

    out_dir = IMAGE_ROOT / args.run_tag / args.input_kind
    ensure_dir(out_dir)
    manifest = out_dir / f"manifest_{args.provider}_{args.run_tag}_{args.input_kind}.jsonl"

    client = build_gemini_client(api_key) if not args.dry_run else None

    for _, r in tqdm(df.iterrows(), total=len(df)):
        rid = slugify(r["record_id"], 40)
        ph = sha1_short(r["prompt"])
        fname = f"{rid}__{ph}__{args.aspect_ratio}__{args.image_size}.png"
        out = out_dir / fname

        if args.dry_run:
            print(f"[DRY] {out.name}")
            continue

        ok, img, msg = generate_image(
            client, model, r["prompt"], args.aspect_ratio, args.image_size
        )
        if ok and img:
            out.write_bytes(img)

        write_jsonl(manifest, {
            "record_id": r["record_id"],
            "status": "ok" if ok else "fail",
            "path": str(out),
            "message": msg,
        })

        time.sleep(max(0.0, args.sleep_s))

    print("✅ Done.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
03_generate_images.py (Unified Image Generation)
------------------------------------------------
Inputs (from Step 02):
- Entity prompts CSV:
  image_prompts_<provider>_<run_tag>.csv
  columns: record_id, entity_name, row_image_necessity, row_image_prompt_en, ...

- Table infographic prompts CSV:
  table_infographic_prompts_<provider>_<run_tag>.csv
  columns: record_id, table_infographic_style, table_infographic_prompt_en, (optional objective/topic...)

Outputs:
- 2_Data/images/generated/<provider>/<run_tag>/<entity|table>/*.png
- 2_Data/images/generated/<provider>/<run_tag>/<entity|table>/manifest_<provider>_<run_tag>_<entity|table>.jsonl

Modes:
- Default: filenames include prompt hash (entity/table) to avoid collisions.
- --table_one_per_record (recommended for input_kind=table):
    - Exactly ONE png per record_id (overwrites on rerun)
    - Stable filename independent of prompt hash
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

from dotenv import load_dotenv
import pandas as pd
from tqdm import tqdm

from google import genai
from google.genai import types


# -------------------------
# Paths / Env
# -------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
    print(f"✅ Loaded .env from: {env_path}")
else:
    print(f"⚠️  Warning: .env file NOT found at: {env_path}")


# -------------------------
# Model Config
# -------------------------
MODEL_CONFIG = {
    "gemini": {
        "model_name": "nano-banana-pro-preview",
        "api_key_env": "GOOGLE_API_KEY",
    },
}


# -------------------------
# Utilities
# -------------------------
def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def write_jsonl_line(path: Path, obj: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def slugify(text: str, max_len: int = 80) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:max_len] if len(text) > max_len else text


def sha1_short(text: str, n: int = 10) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:n]


def detect_input_kind(df: pd.DataFrame) -> str:
    cols = set([c.strip() for c in df.columns])
    if {"entity_name", "row_image_prompt_en", "row_image_necessity"}.issubset(cols):
        return "entity"
    if "table_infographic_prompt_en" in cols:
        return "table"
    return "unknown"


def extract_first_image_bytes(response: Any) -> Optional[bytes]:
    """
    Extract first image bytes from google.genai response.
    Handles typical inline_data payloads.
    """
    try:
        cand = response.candidates[0]
        parts = cand.content.parts
        for part in parts:
            inline = getattr(part, "inline_data", None) or getattr(part, "inlineData", None)
            if inline and getattr(inline, "data", None):
                b64 = inline.data
                if isinstance(b64, (bytes, bytearray)):
                    return bytes(b64)
                return base64.b64decode(b64)
    except Exception:
        return None
    return None


def build_gemini_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def gemini_generate_image(
    client: genai.Client,
    model: str,
    prompt: str,
    aspect_ratio: str,
    image_size: str,
) -> Tuple[bool, Optional[bytes], str]:
    try:
        config = types.GenerateContentConfig(
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=image_size,
            )
        )
        resp = client.models.generate_content(
            model=model,
            contents=[prompt],
            config=config,
        )
        img_bytes = extract_first_image_bytes(resp)
        if not img_bytes:
            return False, None, "no_image_bytes"
        return True, img_bytes, "ok"
    except Exception as e:
        return False, None, f"exception: {e}"


def build_filename_entity(
    record_id: str,
    entity_name: str,
    necessity: str,
    aspect_ratio: str,
    image_size: str,
    prompt: str,
) -> str:
    rid = slugify(record_id, max_len=40) or "unknown"
    ent = slugify(entity_name, max_len=60) or "entity"
    nec = slugify(necessity, max_len=20) or "img"
    ph = sha1_short(prompt, n=10)
    return f"{rid}__{ent}__{nec}__{aspect_ratio}__{image_size}__{ph}.png"


def build_filename_table_hashed(
    record_id: str,
    style: str,
    title_hint: str,
    aspect_ratio: str,
    image_size: str,
    prompt: str,
) -> str:
    rid = slugify(record_id, max_len=40) or "unknown"
    st = slugify(style, max_len=30) or "default"
    hint = slugify(title_hint, max_len=40) or "table"
    ph = sha1_short(prompt, n=10)
    return f"{rid}__{hint}__{st}__{aspect_ratio}__{image_size}__{ph}.png"


def build_filename_table_one_per_record(
    record_id: str,
    style: str,
    aspect_ratio: str,
    image_size: str,
) -> str:
    rid = slugify(record_id, max_len=40) or "unknown"
    st = slugify(style, max_len=30) or "default"
    return f"{rid}__table_infographic__{st}__{aspect_ratio}__{image_size}.png"


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    return df


# -------------------------
# Main
# -------------------------
def main():
    parser = argparse.ArgumentParser(description="MeducAI Step 03 - Generate images (Unified CSV input)")
    parser.add_argument("--provider", default="gemini", help="Provider name (default=gemini)")
    parser.add_argument("--run_tag", required=True, help="Same run_tag used in Step 01/02 (e.g., pilot2)")
    parser.add_argument("--base_dir", default=".", help="MeducAI project root (default=.)")

    parser.add_argument(
        "--input_csv",
        default="",
        help="Explicit input CSV path. If empty, defaults to entity CSV under metadata/generated/<provider>/",
    )
    parser.add_argument(
        "--input_kind",
        default="auto",
        choices=["auto", "entity", "table"],
        help="auto=detect by columns; entity=image_prompts CSV; table=table_infographic_prompts CSV",
    )

    # NEW: table output stabilization
    parser.add_argument(
        "--table_one_per_record",
        action="store_true",
        help="For table input: force exactly one output image per record_id (stable filename; overwrite on rerun).",
    )

    parser.add_argument("--model", default="", help="Override model id (default uses MODEL_CONFIG[provider])")

    parser.add_argument(
        "--aspect_ratio",
        default="4:5",
        choices=["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
        help="Aspect ratio for generated images",
    )
    parser.add_argument("--image_size", default="2K", choices=["1K", "2K", "4K"], help="Image size")

    parser.add_argument("--include_opt", action="store_true", help="For entity CSV: include IMG_OPT (default: IMG_REQ only)")
    parser.add_argument("--limit", type=int, default=0, help="0=all; else cap number of prompts")
    parser.add_argument("--resume", action="store_true", help="Skip if output image file already exists")
    parser.add_argument("--dry_run", action="store_true", help="Do not call API; print planned outputs")
    parser.add_argument("--sleep_s", type=float, default=0.2, help="Sleep seconds between calls")
    args = parser.parse_args()

    if args.provider not in MODEL_CONFIG:
        raise ValueError(f"Unsupported provider: {args.provider}. Supported: {list(MODEL_CONFIG.keys())}")
    if args.provider != "gemini":
        raise NotImplementedError("This script currently implements Gemini image generation only.")

    base_dir = Path(args.base_dir).resolve()

    if args.input_csv.strip():
        in_csv = Path(args.input_csv).expanduser().resolve()
    else:
        in_csv = (
            base_dir
            / "2_Data"
            / "metadata"
            / "generated"
            / args.provider
            / f"image_prompts_{args.provider}_{args.run_tag}.csv"
        )

    df = load_csv(in_csv)

    detected = detect_input_kind(df)
    input_kind = detected if args.input_kind == "auto" else args.input_kind
    if input_kind not in {"entity", "table"}:
        raise ValueError(
            f"Could not determine input_kind from CSV. detected={detected}. "
            f"Provide --input_kind entity|table explicitly, and ensure required columns exist."
        )

    # Output structure separated by kind
    out_dir = base_dir / "2_Data" / "images" / "generated" / args.provider / args.run_tag / input_kind
    ensure_dir(out_dir)
    manifest_path = out_dir / f"manifest_{args.provider}_{args.run_tag}_{input_kind}.jsonl"

    print(f"📥 Input CSV: {in_csv}")
    print(f"🧾 Input kind: {input_kind}")
    print(f"🖼️ Output dir: {out_dir}")
    print(f"🧾 Manifest:  {manifest_path}")
    if input_kind == "table":
        print(f"🧷 table_one_per_record: {args.table_one_per_record}")

    model_id = args.model.strip() or MODEL_CONFIG[args.provider]["model_name"]
    api_key_env = MODEL_CONFIG[args.provider]["api_key_env"]
    api_key = os.getenv(api_key_env, "")

    print(f"🧠 Model:   {model_id}")
    print(f"🔐 API env: {api_key_env}")

    if not api_key and not args.dry_run:
        raise ValueError(f"Missing API key: set {api_key_env} in environment/.env")

    client = build_gemini_client(api_key) if not args.dry_run else None

    # Filter rows
    if input_kind == "entity":
        for col in ["record_id", "entity_name", "row_image_necessity", "row_image_prompt_en"]:
            if col not in df.columns:
                df[col] = ""

        df["row_image_necessity"] = df["row_image_necessity"].fillna("").astype(str).str.upper()
        df["row_image_prompt_en"] = df["row_image_prompt_en"].fillna("").astype(str)

        if args.include_opt:
            df = df[df["row_image_necessity"].isin(["IMG_REQ", "IMG_OPT"])]
        else:
            df = df[df["row_image_necessity"].eq("IMG_REQ")]

        df = df[df["row_image_prompt_en"].str.strip() != ""]

    else:  # table
        for col in ["record_id", "table_infographic_style", "table_infographic_prompt_en"]:
            if col not in df.columns:
                df[col] = ""

        df["table_infographic_style"] = df["table_infographic_style"].fillna("").astype(str)
        df["table_infographic_prompt_en"] = df["table_infographic_prompt_en"].fillna("").astype(str)
        df = df[df["table_infographic_prompt_en"].str.strip() != ""]

    if args.limit and args.limit > 0:
        df = df.head(args.limit)

    print(f"🔎 Rows to generate: {len(df)}")

    n_ok = 0
    n_skip = 0
    n_fail = 0
    n_overwrite = 0

    for _, row in tqdm(df.iterrows(), total=len(df)):
        record_id = str(row.get("record_id", "")).strip() or "unknown"

        if input_kind == "entity":
            entity = str(row.get("entity_name", "")).strip() or "entity"
            necessity = str(row.get("row_image_necessity", "")).strip() or "IMG_OPT"
            prompt = str(row.get("row_image_prompt_en", "")).strip()

            filename = build_filename_entity(
                record_id=record_id,
                entity_name=entity,
                necessity=necessity,
                aspect_ratio=args.aspect_ratio,
                image_size=args.image_size,
                prompt=prompt,
            )
            out_path = out_dir / filename

            if args.resume and out_path.exists():
                n_skip += 1
                continue

            meta_extra = {
                "entity_name": entity,
                "row_image_necessity": necessity,
            }

        else:
            style = str(row.get("table_infographic_style", "")).strip() or "Default"
            prompt = str(row.get("table_infographic_prompt_en", "")).strip()

            title_hint = (
                str(row.get("topic", "")).strip()
                or str(row.get("objective", "")).strip()
                or "master_table"
            )

            if args.table_one_per_record:
                filename = build_filename_table_one_per_record(
                    record_id=record_id,
                    style=style,
                    aspect_ratio=args.aspect_ratio,
                    image_size=args.image_size,
                )
            else:
                filename = build_filename_table_hashed(
                    record_id=record_id,
                    style=style,
                    title_hint=title_hint,
                    aspect_ratio=args.aspect_ratio,
                    image_size=args.image_size,
                    prompt=prompt,
                )

            out_path = out_dir / filename

            if args.table_one_per_record:
                # Overwrite mode: do not skip even if exists
                if out_path.exists():
                    n_overwrite += 1
            else:
                if args.resume and out_path.exists():
                    n_skip += 1
                    continue

            meta_extra = {
                "table_infographic_style": style,
                "title_hint": title_hint[:120],
                "table_one_per_record": bool(args.table_one_per_record),
            }

        if args.dry_run:
            print(f"[DRY] {out_path.name}")
            print(f"  prompt: {prompt[:180]}{'...' if len(prompt) > 180 else ''}")
            n_ok += 1
            continue

        ok, img_bytes, msg = gemini_generate_image(
            client=client,
            model=model_id,
            prompt=prompt,
            aspect_ratio=args.aspect_ratio,
            image_size=args.image_size,
        )

        event: Dict[str, Any] = {
            "ts": int(time.time()),
            "provider": args.provider,
            "run_tag": args.run_tag,
            "input_kind": input_kind,
            "model": model_id,
            "record_id": record_id,
            "aspect_ratio": args.aspect_ratio,
            "image_size": args.image_size,
            "prompt_hash": sha1_short(prompt, 12),
            "output_path": str(out_path),
            "status": "ok" if ok else "fail",
            "message": msg,
            **meta_extra,
        }

        if ok and img_bytes:
            out_path.write_bytes(img_bytes)
            n_ok += 1
        else:
            n_fail += 1

        write_jsonl_line(manifest_path, event)
        time.sleep(max(0.0, args.sleep_s))

    print("✅ Image generation finished.")
    print(f"  ok:        {n_ok}")
    print(f"  skip:      {n_skip}")
    print(f"  overwrite: {n_overwrite}")
    print(f"  fail:      {n_fail}")
    print(f"📁 Images:   {out_dir}")
    print(f"🧾 Manifest: {manifest_path}")


if __name__ == "__main__":
    main()

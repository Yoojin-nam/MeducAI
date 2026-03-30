#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
V2 enrichment: add Topic + Archetype columns using Gemini.

Notebook reference:
- 3_Code/notebooks/RaB-LLM_02_Enrichment.ipynb
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from gemini_utils import GeminiClient, GeminiConfig  # noqa: E402
from run_logging import JsonlLogger, append_system_prompt, make_run_id, make_default_artifacts  # noqa: E402


SYSTEM_INSTRUCTION = (
    "You are an expert medical curriculum data analyst specializing in Radiology.\n"
    "Your task is to structure unstructured learning objectives into specific topics and archetypes.\n"
    "Do not hallucinate. If the topic is unclear, infer the most likely medical entity based on the context.\n"
    "Output must be a SINGLE valid JSON object mapping each input index to a string in the format: \"Topic | Archetype\".\n"
    "Archetype must be one of [Disease, Anatomy, Tumor, Staging, Intervention, Pattern].\n"
)


def _batch(items: List[Tuple[int, str, str]], batch_size: int) -> List[List[Tuple[int, str, str]]]:
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def _parse_topic_archetype(s: str) -> Tuple[str, str]:
    t = (s or "").strip()
    if "|" not in t:
        return t, "Check_Format"
    a, b = t.split("|", 1)
    return a.strip(), b.strip()


def main() -> None:
    ap = argparse.ArgumentParser(description="Enrich curriculum rows with Topic/Archetype (v2).")
    ap.add_argument("--in_xlsx", required=True)
    ap.add_argument("--out_xlsx", required=True)
    ap.add_argument("--model", default="gemini-3-flash-preview")
    ap.add_argument("--batch_size", type=int, default=10)
    ap.add_argument("--run_id", default=None, help="Optional run id for MI-CLEAR logging")
    ap.add_argument("--log_jsonl", default=None, help="Optional JSONL log path")
    ap.add_argument("--prompts_txt", default=None, help="Optional system prompts snapshot path")
    ap.add_argument("--repo_root", default=".", help="Repo root (for default log locations)")
    args = ap.parse_args()

    in_path = Path(args.in_xlsx).resolve()
    out_path = Path(args.out_xlsx).resolve()

    df = pd.read_excel(in_path)
    df = df.reset_index(drop=True)

    if "Category" not in df.columns or "Objective" not in df.columns:
        raise ValueError("Input must contain columns: Category, Objective")

    items: List[Tuple[int, str, str]] = []
    for i in range(len(df)):
        cat_val = df.at[i, "Category"]
        obj_val = df.at[i, "Objective"]
        cat = "" if pd.isna(cat_val) else str(cat_val)
        obj = "" if pd.isna(obj_val) else str(obj_val)
        items.append((i, cat, obj))

    client = GeminiClient(GeminiConfig(model=args.model))
    process_date = dt.datetime.now().strftime("%Y-%m-%d")

    run_id = str(args.run_id or "").strip() or make_run_id("enrichv2")
    repo_root = Path(args.repo_root).resolve()
    artifacts = make_default_artifacts(repo_root, run_id)
    log_path = Path(args.log_jsonl).resolve() if args.log_jsonl else artifacts.log_jsonl
    prompts_path = Path(args.prompts_txt).resolve() if args.prompts_txt else artifacts.prompts_txt
    logger = JsonlLogger(log_path, run_id=run_id)
    append_system_prompt(prompts_path, "enrich_v2.SYSTEM_INSTRUCTION", SYSTEM_INSTRUCTION)
    logger.write(
        {
            "event": "step_start",
            "step": "enrich_v2",
            "in_xlsx": str(in_path),
            "out_xlsx": str(out_path),
            "rows": int(len(df)),
            "batch_size": int(args.batch_size),
            "model": args.model,
            "temperature": 0.0,
            "top_p": 1.0,
            "top_k": 1,
        }
    )

    topic_col = [""] * len(df)
    archetype_col = [""] * len(df)

    batches = _batch(items, args.batch_size)
    total_batches = len(batches)
    for bi, b in enumerate(batches, start=1):
        print(f"[enrich_v2] batch {bi}/{total_batches} (rows {len(b)})", flush=True)
        payload: Dict[str, Dict[str, str]] = {str(i): {"Category": c, "Objective": o} for i, c, o in b}
        prompt = json.dumps(payload, ensure_ascii=False)
        result, meta = client.generate_json_with_meta(prompt, SYSTEM_INSTRUCTION)
        if not isinstance(result, dict):
            raise RuntimeError(f"Unexpected response type: {type(result)}")
        for k, v in result.items():
            idx = int(k)
            t, a = _parse_topic_archetype(str(v))
            topic_col[idx] = t
            archetype_col[idx] = a
        logger.write(
            {
                "event": "batch_ok",
                "step": "enrich_v2",
                "batch": bi,
                "batches_total": total_batches,
                "rows_in_batch": int(len(b)),
                "row_index_min": int(min(i for i, _, _ in b)) if b else None,
                "row_index_max": int(max(i for i, _, _ in b)) if b else None,
                "gemini": meta,
            }
        )

    df["Topic"] = topic_col
    df["Archetype"] = archetype_col
    df["Model_Used"] = args.model
    df["Process_Date"] = process_date

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(out_path, index=False, engine="openpyxl")
    logger.write({"event": "step_done", "step": "enrich_v2", "rows": int(len(df))})
    print(f"OK: wrote {out_path} rows={len(df)}")


if __name__ == "__main__":
    main()



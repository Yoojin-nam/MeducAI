#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
V2 translation: translate structural labels + Objective text.

Notebook reference:
- 3_Code/notebooks/RaB-LLM_04_Curriculum_translate.ipynb
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import base64
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from gemini_utils import GeminiClient, GeminiConfig  # noqa: E402
from run_logging import JsonlLogger, append_system_prompt, make_run_id, make_default_artifacts  # noqa: E402


SYSTEM_PROMPT_TRANSLATION = """
You are an expert medical translator specializing in Radiology.

Your task:
You will receive a JSON array of Korean medical curriculum terms (strings).

Return a SINGLE valid JSON ARRAY where each element is an object with EXACTLY:
- \"kr\": original Korean term (string)
- \"label\": a human-readable English phrase (string)
- \"tag\": a short, machine-friendly identifier (string)

Requirements for \"label\":
- Professional radiology English.
- Use normal spaces, not underscores.
- Use sentence or title case.
- Keep the phrase concise but clinically accurate.

Requirements for \"tag\":
- Use only: lowercase letters, numbers, and underscores.
- Prefer short tags.
- Use common abbreviations where obvious.
- Remove articles and conjunctions.

Ambiguity handling:
- If a term is ambiguous or you are not confident, set:
  - \"label\": \"REVIEW_NEEDED\"
  - \"tag\": \"review_needed\"

Output format:
- Return a SINGLE valid JSON array.
- Do NOT wrap the JSON in markdown code blocks.
""".strip()


SYSTEM_PROMPT_OBJECTIVE = """
You are an expert medical educator.

Your Task:
Translate the provided Korean radiology learning objectives into professional English medical curriculum statements.

Input format:
- You will receive a JSON object where keys are indices (strings) and values are Korean objective sentences.

Output format:
- Return a SINGLE valid JSON array of objects.
- Each element MUST be:
  - "i": the same index as an integer
  - "en_b64": BASE64 of the UTF-8 encoded translated English objective (string, MUST be single-line, no whitespace/newlines)

Hard rules:
1) Output MUST be valid JSON (no trailing commentary).
2) Output MUST be a JSON array (even if only one item).
3) Do NOT include any keys other than "i" and "en_b64".
4) If you are unsure, return an empty array [].

Constraints:
1. Maintain clinical and educational accuracy.
2. Use clear, natural professional English.
3. No conversational filler, no explanations, only the JSON object.
4. Do NOT wrap the JSON in markdown code blocks.
""".strip()


def _batch(items: List[Tuple[int, str]], batch_size: int) -> List[List[Tuple[int, str]]]:
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def _get_label(v: Any, fallback: str) -> str:
    if isinstance(v, dict):
        return str(v.get("label") or fallback)
    return str(v or fallback)


def _get_tag(v: Any, fallback: str) -> str:
    if isinstance(v, dict):
        return str(v.get("tag") or fallback)
    return str(v or fallback)


def _batch_terms(items: List[str], batch_size: int) -> List[List[str]]:
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def _sanitize_for_excel(s: str) -> str:
    """
    Remove control characters and other characters that openpyxl rejects.
    openpyxl rejects: \x00-\x08, \x0B, \x0C, \x0E-\x1F (control chars except \t, \n, \r)
    Also remove corrupted UTF-8 sequences that might appear as replacement chars.
    """
    if not isinstance(s, str):
        s = str(s)
    # Remove control characters except tab, newline, carriage return
    # \x00-\x08, \x0B, \x0C, \x0E-\x1F are illegal in Excel XML
    s = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", s)
    # Remove any remaining non-printable Unicode characters (but keep normal spaces, tabs, newlines)
    # This catches corrupted UTF-8 sequences that decode to replacement chars
    s = "".join(c for c in s if c.isprintable() or c in "\t\n\r")
    return s


def main() -> None:
    ap = argparse.ArgumentParser(description="Translate curriculum structure + objectives (v2).")
    ap.add_argument("--in_xlsx", required=True)
    ap.add_argument("--out_xlsx", required=True)
    ap.add_argument("--out_map_json", required=True)
    ap.add_argument("--model", default="gemini-3-flash-preview")
    ap.add_argument("--obj_batch_size", type=int, default=15)
    ap.add_argument("--checkpoint_every", type=int, default=10, help="Write partial out_xlsx every N objective batches")
    ap.add_argument("--resume", default="1", help="Resume if out_xlsx exists and has Objective_EN (default: 1)")
    ap.add_argument("--run_id", default=None, help="Optional run id for MI-CLEAR logging")
    ap.add_argument("--log_jsonl", default=None, help="Optional JSONL log path")
    ap.add_argument("--prompts_txt", default=None, help="Optional system prompts snapshot path")
    ap.add_argument("--repo_root", default=".", help="Repo root (for default log locations)")
    args = ap.parse_args()

    in_path = Path(args.in_xlsx).resolve()
    out_path = Path(args.out_xlsx).resolve()
    map_path = Path(args.out_map_json).resolve()

    df = pd.read_excel(in_path).reset_index(drop=True)
    # Resume support: if out exists and has Objective_EN, reuse it (assumes same row ordering).
    out_exists = out_path.exists()
    if str(args.resume).strip() != "0" and out_exists:
        try:
            prev = pd.read_excel(out_path).reset_index(drop=True)
            if "Objective_EN" in prev.columns and len(prev) == len(df):
                df["Objective_EN"] = prev["Objective_EN"]
                print("[translate_v2] resume: loaded existing Objective_EN from output", flush=True)
        except Exception:
            pass

    client = GeminiClient(GeminiConfig(model=args.model))

    run_id = str(args.run_id or "").strip() or make_run_id("translatev2")
    repo_root = Path(args.repo_root).resolve()
    artifacts = make_default_artifacts(repo_root, run_id)
    log_path = Path(args.log_jsonl).resolve() if args.log_jsonl else artifacts.log_jsonl
    prompts_path = Path(args.prompts_txt).resolve() if args.prompts_txt else artifacts.prompts_txt
    logger = JsonlLogger(log_path, run_id=run_id)
    append_system_prompt(prompts_path, "translate_v2.SYSTEM_PROMPT_TRANSLATION", SYSTEM_PROMPT_TRANSLATION)
    append_system_prompt(prompts_path, "translate_v2.SYSTEM_PROMPT_OBJECTIVE", SYSTEM_PROMPT_OBJECTIVE)
    logger.write(
        {
            "event": "step_start",
            "step": "translate_v2",
            "in_xlsx": str(in_path),
            "out_xlsx": str(out_path),
            "rows": int(len(df)),
            "model": args.model,
            "temperature": 0.0,
            "top_p": 1.0,
            "top_k": 1,
            "obj_batch_size": int(args.obj_batch_size),
        }
    )

    # 1) Structural translation map
    structure_cols = ["Specialty", "Anatomy", "Modality/Type", "Category"]
    existing_cols = [c for c in structure_cols if c in df.columns]
    unique_terms: List[str] = []
    if existing_cols:
        terms = set()
        for c in existing_cols:
            terms.update(df[c].dropna().astype(str).unique().tolist())
        unique_terms = sorted(terms)

    # Load existing translation_map if it exists
    translation_map: Dict[str, Any] = {}
    if map_path.exists():
        try:
            with open(map_path, "r", encoding="utf-8") as f:
                translation_map = json.load(f)
            print(f"[translate_v2] loaded existing translation_map: {len(translation_map)} entries", flush=True)
        except Exception as e:
            print(f"[translate_v2] WARNING: failed to load existing translation_map: {e}", flush=True)
            translation_map = {}
    
    if unique_terms:
        # Filter out terms that are already in translation_map
        missing_terms = [t for t in unique_terms if t not in translation_map]
        print(f"[translate_v2] structural terms: {len(unique_terms)} total, {len(missing_terms)} missing from map", flush=True)
        
        if missing_terms:
            # IMPORTANT: Use JSON array of fixed-shape objects (kr/label/tag),
            # then rebuild a dict. This avoids Gemini emitting invalid JSON objects
            # with dynamic keys (a frequent failure mode).
            term_batches = _batch_terms(missing_terms, batch_size=40)
            total_tb = len(term_batches)
            for bi, terms in enumerate(term_batches, start=1):
                print(f"[translate_v2] structural batch {bi}/{total_tb} (terms {len(terms)})", flush=True)
                arr, meta_struct = client.generate_json_with_meta(
                    json.dumps(terms, ensure_ascii=False), SYSTEM_PROMPT_TRANSLATION
                )
                # Gemini sometimes returns a dict despite the prompt. Accept both and normalize.
                if isinstance(arr, list):
                    for it in arr:
                        if not isinstance(it, dict):
                            continue
                        kr = str(it.get("kr") or "").strip()
                        if not kr:
                            continue
                        translation_map[kr] = {"label": it.get("label"), "tag": it.get("tag")}
                elif isinstance(arr, dict):
                    # Expected shapes:
                    # - { "<KR>": {"label": "...", "tag": "..."}, ... }
                    # - { "<KR>": {"kr": "<KR>", "label": "...", "tag": "..."}, ... }
                    for kr_key, v in arr.items():
                        kr = str(kr_key).strip()
                        if not kr:
                            continue
                        if isinstance(v, dict):
                            translation_map[kr] = {"label": v.get("label"), "tag": v.get("tag")}
                        else:
                            # Worst-case fallback: store value as label and tag as review_needed
                            translation_map[kr] = {"label": str(v), "tag": "review_needed"}
                else:
                    raise RuntimeError(f"Structural translation returned unexpected JSON type: {type(arr)}")
                logger.write(
                    {
                        "event": "struct_batch_ok",
                        "step": "translate_v2",
                        "batch": bi,
                        "batches_total": total_tb,
                        "terms_in_batch": int(len(terms)),
                        "gemini": meta_struct,
                    }
                )

        map_path.parent.mkdir(parents=True, exist_ok=True)
        map_path.write_text(json.dumps(translation_map, ensure_ascii=False, indent=2), encoding="utf-8")

        for col in existing_cols:
            label_col = col.replace("/", "_") + "_EN_LABEL"
            tag_col = col.replace("/", "_") + "_EN_TAG"

            src = df[col].astype(str)
            df[label_col] = src.map(lambda t: _get_label(translation_map.get(str(t)), str(t)))
            df[tag_col] = src.map(lambda t: _get_tag(translation_map.get(str(t)), str(t)))
            df[tag_col] = df[tag_col].astype(str).str.replace(" ", "_")

        if "Topic" in df.columns:
            df["Topic_Clean"] = (
                df["Topic"].astype(str).str.replace("/", "_").str.replace(" ", "_")
            )

    # 2) Objective translation
    if "Objective" not in df.columns:
        raise ValueError("Input missing Objective column")

    obj_series = df["Objective"].fillna("").astype(str)
    existing_en = df["Objective_EN"].fillna("").astype(str) if "Objective_EN" in df.columns else pd.Series([""] * len(df))
    objectives: List[Tuple[int, str]] = [
        (i, obj_series.iat[i])
        for i in range(len(obj_series))
        if obj_series.iat[i].strip() and (str(existing_en.iat[i]).strip() == "")
    ]
    translated: Dict[int, str] = {}

    batches = _batch(objectives, args.obj_batch_size)
    total_batches = len(batches)
    for bi, b in enumerate(batches, start=1):
        print(f"[translate_v2] objective batch {bi}/{total_batches} (rows {len(b)})", flush=True)
        payload = {str(i): text for i, text in b}
        result, meta = client.generate_json_with_meta(json.dumps(payload, ensure_ascii=False), SYSTEM_PROMPT_OBJECTIVE)
        # Accept list or dict. Prefer list of {i,en_b64}.
        if isinstance(result, list):
            for it in result:
                if not isinstance(it, dict):
                    continue
                idx = it.get("i")
                b64 = it.get("en_b64")
                if idx is None or b64 is None:
                    continue
                try:
                    b64s = str(b64).strip().replace("\n", "").replace("\r", "").replace(" ", "")
                    en = base64.b64decode(b64s, validate=False).decode("utf-8", errors="replace")
                    en = _sanitize_for_excel(en)  # Remove control chars immediately after decode
                except Exception:
                    en = ""
                translated[int(idx)] = en
        elif isinstance(result, dict):
            # Fallbacks:
            # 1) Single object: {"i": 123, "en_b64": "..."}
            # 2) Map: { "123": "base64..." } or { "123": {"en_b64": "..."} }
            if "i" in result and "en_b64" in result:
                try:
                    idx = int(result.get("i"))  # type: ignore[arg-type]
                except Exception:
                    idx = None
                b64 = result.get("en_b64")
                if idx is not None and b64 is not None:
                    try:
                        b64s = str(b64).strip().replace("\n", "").replace("\r", "").replace(" ", "")
                        en = base64.b64decode(b64s, validate=False).decode("utf-8", errors="replace")
                        en = _sanitize_for_excel(en)  # Remove control chars immediately after decode
                    except Exception:
                        en = ""
                    translated[int(idx)] = en
            else:
                for k, v in result.items():
                    if isinstance(v, dict) and "en_b64" in v:
                        b64 = v.get("en_b64")
                    else:
                        b64 = v
                try:
                    b64s = str(b64).strip().replace("\n", "").replace("\r", "").replace(" ", "")
                    en = base64.b64decode(b64s, validate=False).decode("utf-8", errors="replace")
                    en = _sanitize_for_excel(en)  # Remove control chars immediately after decode
                except Exception:
                    en = ""
                # Guard: sometimes model returns keys like "i" unexpectedly
                try:
                    translated[int(k)] = en
                except Exception:
                    continue
        else:
            raise RuntimeError(f"Objective translation returned unexpected JSON type: {type(result)}")
        logger.write(
            {
                "event": "batch_ok",
                "step": "translate_v2",
                "batch": bi,
                "batches_total": total_batches,
                "rows_in_batch": int(len(b)),
                "row_index_min": int(min(i for i, _ in b)) if b else None,
                "row_index_max": int(max(i for i, _ in b)) if b else None,
                "gemini": meta,
            }
        )
        # Checkpoint write (partial) so we can resume without re-running earlier batches
        if args.checkpoint_every and (bi % int(args.checkpoint_every) == 0):
            if "Objective_EN" not in df.columns:
                df["Objective_EN"] = ""
            for k, v in translated.items():
                df.at[int(k), "Objective_EN"] = v
            # Sanitize string columns before Excel write
            if "Objective_EN" in df.columns:
                df["Objective_EN"] = df["Objective_EN"].astype(str).apply(_sanitize_for_excel)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_excel(out_path, index=False, engine="openpyxl")
            logger.write({"event": "checkpoint_write", "step": "translate_v2", "batch": bi, "out_xlsx": str(out_path)})

    if "Objective_EN" not in df.columns:
        df["Objective_EN"] = ""
    # Apply batch translations, preserving any resumed values already present.
    for k, v in translated.items():
        df.at[int(k), "Objective_EN"] = v
    df["Objective_EN"] = df["Objective_EN"].fillna("").astype(str)
    # Fallback for blanks
    df.loc[df["Objective_EN"].str.strip() == "", "Objective_EN"] = df["Objective"].astype(str)
    # Sanitize string columns before Excel write (remove control chars that openpyxl rejects)
    if "Objective_EN" in df.columns:
        df["Objective_EN"] = df["Objective_EN"].apply(_sanitize_for_excel)

    # Provenance
    df["Meta_Model_Version"] = args.model
    df["Meta_Temperature"] = 0.0
    df["Meta_Execution_Date"] = dt.datetime.now().strftime("%Y-%m-%d")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(out_path, index=False, engine="openpyxl")
    logger.write({"event": "step_done", "step": "translate_v2", "rows": int(len(df)), "map_terms": int(len(unique_terms))})
    print(f"OK: wrote {out_path} rows={len(df)} map_terms={len(unique_terms)}")


if __name__ == "__main__":
    main()



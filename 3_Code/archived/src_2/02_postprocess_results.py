#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
02_postprocess_results.py (MeducAI v3.7 - integrated path)
------------------------------------------------------
Step 02: Normalize Step 01 JSONL output into stable CSV interfaces.

Input:
- 2_Data/metadata/generated/<run_tag>/output_<provider>_<run_tag>__armX.jsonl

Outputs (same folder):
- table_infographic_prompts_<provider>_<run_tag>__armX.csv
- image_prompts_<provider>_<run_tag>__armX.csv
- anki_cards_<provider>_<run_tag>__armX.csv
- postprocess_summary_<provider>_<run_tag>__armX.json

Key updates (v3.7):
- Input path is now integrated: <run_tag>/output_<provider>...jsonl
- Provider auto-detection logic based on ARM_CONFIGS removed (no longer needed).
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
# [MODIFIED] Import path helper
from generated_paths import generated_run_dir
from typing import Any, Dict, List
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))


# -------------------------
# Utilities
# -------------------------
def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def safe_str(x: Any, default: str = "") -> str:
    if x is None:
        return default
    try:
        s = str(x)
    except Exception:
        return default
    return s.strip()


def safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def norm_cell(x: Any, default: str = "") -> str:
    """
    Normalize cell-like values for CSV consistency.
    - None -> ""
    - string "nan"/"null"/"none" -> ""
    - empty/whitespace -> ""
    - else stripped string
    """
    s = safe_str(x, default=default)
    if not s:
        return ""
    if s.lower() in {"nan", "null", "none"}:
        return ""
    return s


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        raise FileNotFoundError(f"JSONL not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                # corrupt line - skip
                continue
    return rows


def write_csv(path: Path, header: List[str], rows: List[Dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            # [FIXED v3.8] Changed 'for h in h' to 'for h in header'
            w.writerow({h: r.get(h, "") for h in header})


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def extract_source_info(meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Group-first source_info extractor.

    Expected (Step01 v3.4):
      meta.source_info = {
        specialty, anatomy, modality_or_type, category, group_key,
        group_size, group_weight_sum, split_index, tags, ...
      }

    Backward compatibility (legacy):
      specialty, anatomy, topic, archetype, tags
    """
    src = meta.get("source_info", {}) if isinstance(meta, dict) else {}
    if not isinstance(src, dict):
        src = {}

    specialty = norm_cell(src.get("specialty"))
    anatomy = norm_cell(src.get("anatomy"))

    # group-first fields (normalize to prevent "nan" leakage)
    modality_or_type = norm_cell(src.get("modality_or_type"))
    category = norm_cell(src.get("category"))
    group_key = norm_cell(src.get("group_key"))

    # legacy fallback
    topic = norm_cell(src.get("topic"))
    archetype = norm_cell(src.get("archetype"))

    tags_source = norm_cell(src.get("tags"))

    group_size = safe_int(src.get("group_size"), default=0)
    split_index = safe_int(src.get("split_index"), default=0)

    # group_weight_sum preferred; fallback to meta.weight_factor if present
    group_weight_sum = safe_float(src.get("group_weight_sum"), default=0.0)

    # Some older JSONLs might not have group_weight_sum in source_info, but have meta.weight_factor
    if group_weight_sum == 0.0:
        group_weight_sum = safe_float(meta.get("weight_factor"), default=0.0)

    # Decide weight_factor output: for group-first, weight_factor == group_weight_sum
    weight_factor = safe_float(meta.get("weight_factor"), default=group_weight_sum)
    if weight_factor == 0.0 and group_weight_sum != 0.0:
        weight_factor = group_weight_sum

    return {
        "specialty": specialty,
        "anatomy": anatomy,
        "modality_or_type": modality_or_type,
        "category": category,
        "group_key": group_key,

        # legacy (kept for compatibility with existing scripts; may be empty in group-first)
        "topic": topic,
        "archetype": archetype,

        "tags_source": tags_source,
        "group_size": group_size,
        "split_index": split_index,
        "group_weight_sum": group_weight_sum,
        "weight_factor": weight_factor,
    }


def get_arm(meta: Dict[str, Any]) -> str:
    """Return arm label (A-F) if present in metadata; else empty string."""
    if not isinstance(meta, dict):
        return ""
    return norm_cell(meta.get("arm"))

def get_model_version(meta: Dict[str, Any]) -> str:
    """
    Step01 v3.4 uses model_version_stage1 / model_version_stage2.
    Legacy uses model_version.
    For CSVs we emit a single model_version (prefer stage2 if present).
    """
    if not isinstance(meta, dict):
        return ""
    mv2 = norm_cell(meta.get("model_version_stage2"))
    if mv2:
        return mv2
    mv1 = norm_cell(meta.get("model_version_stage1"))
    if mv1:
        return mv1
    return norm_cell(meta.get("model_version"))


# -------------------------
# Headers (v3.4 group-first)
# -------------------------
COMMON_GROUP_FIELDS = [
    "provider",
    "run_tag",
    "arm",
    "record_id",

    # group identity / slicing
    "specialty",
    "anatomy",
    "modality_or_type",
    "category",
    "group_key",
    "group_size",
    "split_index",

    # weights
    "weight_factor",
    "group_weight_sum",
]

# Table interface
TABLE_INFO_HEADER = COMMON_GROUP_FIELDS + [
    # legacy fields (topic/archetype) remain for compatibility but may be empty
    "topic",
    "archetype",

    "objective",
    "visual_type",
    "table_infographic_style",
    "table_infographic_keywords_en",
    "table_infographic_prompt_en",
    "model_version",
    "timestamp",
    "prompt_hash",
]

# Entity image prompt interface
ENTITY_IMAGE_HEADER = COMMON_GROUP_FIELDS + [
    "topic",
    "archetype",

    "objective",
    "visual_type",
    "entity_name",
    "importance_score",
    "row_image_necessity",
    "row_image_prompt_en",
    "model_version",
    "timestamp",
    "prompt_hash",
]

# Anki card interface
ANKI_CARDS_HEADER = COMMON_GROUP_FIELDS + [
    "topic",
    "archetype",

    "entity_name",
    "importance_score",
    "card_type",
    "front",
    "back",
    "tags",
    "row_image_necessity",
    "row_image_prompt_en",
    "model_version",
    "timestamp",
    "prompt_hash",
]


# -------------------------
# Main Processing
# -------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="MeducAI Step 02 - Postprocess JSONL into CSV interfaces (v3.7 integrated path)"
    )
    # --provider 인자는 입력 파일 경로 구성에 사용되지 않지만, 출력 파일명 및 CSV 필드에 필요하므로 유지합니다.
    parser.add_argument("--provider", required=True, help="Provider name (gemini/gpt/deepseek/claude)")
    parser.add_argument("--run_tag", required=True, help="Same run_tag used in Step 01 output filename")
    parser.add_argument("--arm", default="", choices=["", "A", "B", "C", "D", "E", "F"], help="Optional: arm suffix for 6-arm outputs (matches Step01 __armX filename suffix).")
    parser.add_argument("--base_dir", default=".", help="MeducAI project root (default=.)")
    parser.add_argument("--keep_failed", action="store_true", help="Include error lines too (default: skip)")
    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    provider = norm_cell(args.provider)
    run_tag = norm_cell(args.run_tag)

    arm_val = norm_cell(args.arm).upper()
    arm_suffix = f"__arm{arm_val}" if arm_val else ""
    provider_file_prefix = f"{provider}_" if provider and provider != "default" else ""
    
    # [MODIFIED v3.7] Input directory is now just OUTPUT_DIR / "generated" / run_tag
    out_dir_base = base_dir / "2_Data" / "metadata" / "generated" / run_tag

    in_jsonl = (
        out_dir_base
        / f"output_{provider_file_prefix}{run_tag}{arm_suffix}.jsonl"
    )
    
    out_dir = generated_run_dir(base_dir, run_tag)
    # Output file names remain the same (keeping provider for audit trail in filename)
    out_table_csv = out_dir / f"table_infographic_prompts_{provider}_{run_tag}{arm_suffix}.csv"
    out_entity_img_csv = out_dir / f"image_prompts_{provider}_{run_tag}{arm_suffix}.csv"
    out_anki_csv = out_dir / f"anki_cards_{provider}_{run_tag}{arm_suffix}.csv"
    out_summary_json = out_dir / f"postprocess_summary_{provider}_{run_tag}{arm_suffix}.json"

    rows = read_jsonl(in_jsonl)

    table_rows: List[Dict[str, Any]] = []
    entity_img_rows: List[Dict[str, Any]] = []
    anki_rows: List[Dict[str, Any]] = []

    # Stats
    n_total = 0
    n_content = 0
    n_error = 0
    n_skipped = 0

    n_tables = 0
    n_entities = 0
    n_entity_img_req = 0
    n_entity_img_opt = 0
    n_entity_img_none = 0
    n_cards = 0

    card_type_counts: Dict[str, int] = {}

    for obj in rows:
        n_total += 1

        if not isinstance(obj, dict):
            n_skipped += 1
            continue

        # Error line structure: {"metadata":..., "error":...}
        if "error" in obj and "curriculum_content" not in obj:
            n_error += 1
            if args.keep_failed:
                # keep_failed currently only affects summary; we do not emit CSV rows for failed lines
                pass
            continue

        meta = obj.get("metadata", {})
        content = obj.get("curriculum_content", {})

        if not isinstance(meta, dict) or not isinstance(content, dict):
            n_skipped += 1
            continue

        n_content += 1

        record_id = norm_cell(meta.get("id"))
        arm_log_val = get_arm(meta) # 로그에 기록된 arm 값을 사용
        model_version = get_model_version(meta)
        timestamp = safe_int(meta.get("timestamp"))
        prompt_hash = norm_cell(meta.get("prompt_hash"))

        src = extract_source_info(meta)

        specialty = src["specialty"]
        anatomy = src["anatomy"]
        modality_or_type = src["modality_or_type"]
        category = src["category"]
        group_key = src["group_key"]
        group_size = src["group_size"]
        split_index = src["split_index"]
        weight_factor = src["weight_factor"]
        group_weight_sum = src["group_weight_sum"]

        # legacy (may be empty in group-first)
        topic = src["topic"]
        archetype = src["archetype"]

        objective = norm_cell(content.get("objective"))  # kept for downstream compatibility
        visual_type = norm_cell(content.get("visual_type"))

        # 1) Table infographic row (one per record_id)
        table_inf = content.get("table_infographic", {}) if isinstance(content.get("table_infographic"), dict) else {}
        table_style = norm_cell(table_inf.get("style"))
        table_kw = norm_cell(table_inf.get("keywords_en"))
        table_prompt = norm_cell(table_inf.get("prompt_en"))

        table_rows.append({
            # common group fields
            "provider": provider, # 인자로 받은 provider를 사용
            "run_tag": run_tag,
            "arm": arm_log_val,
            "record_id": record_id,
            "specialty": specialty,
            "anatomy": anatomy,
            "modality_or_type": modality_or_type,
            "category": category,
            "group_key": group_key,
            "group_size": group_size,
            "split_index": split_index,
            "weight_factor": weight_factor,
            "group_weight_sum": group_weight_sum,

            # legacy
            "topic": topic,
            "archetype": archetype,

            # table fields
            "objective": objective,
            "visual_type": visual_type,
            "table_infographic_style": table_style,
            "table_infographic_keywords_en": table_kw,
            "table_infographic_prompt_en": table_prompt,

            # meta
            "model_version": model_version,
            "timestamp": timestamp,
            "prompt_hash": prompt_hash,
        })
        n_tables += 1

        # 2) Entities + image prompts + anki cards
        entities = content.get("entities", [])
        if not isinstance(entities, list):
            entities = []

        for ent in entities:
            if not isinstance(ent, dict):
                continue

            entity_name = norm_cell(ent.get("entity_name"))
            importance_score = safe_int(ent.get("importance_score"), default=50)
            row_img_nec = norm_cell(ent.get("row_image_necessity"))
            row_img_prompt = ent.get("row_image_prompt_en")
            row_img_prompt = "" if row_img_prompt is None else norm_cell(row_img_prompt)

            # entity image prompt rows: IMG_REQ/IMG_OPT only
            if row_img_nec in ("IMG_REQ", "IMG_OPT"):
                entity_img_rows.append({
                    # common group fields
                    "provider": provider,
            "run_tag": run_tag,
            "arm": arm_log_val,
                    "record_id": record_id,
                    "specialty": specialty,
                    "anatomy": anatomy,
                    "modality_or_type": modality_or_type,
                    "category": category,
                    "group_key": group_key,
                    "group_size": group_size,
                    "split_index": split_index,
                    "weight_factor": weight_factor,
                    "group_weight_sum": group_weight_sum,

                    # legacy
                    "topic": topic,
                    "archetype": archetype,

                    # entity fields
                    "objective": objective,
                    "visual_type": visual_type,
                    "entity_name": entity_name,
                    "importance_score": importance_score,
                    "row_image_necessity": row_img_nec,
                    "row_image_prompt_en": row_img_prompt,

                    # meta
                    "model_version": model_version,
                    "timestamp": timestamp,
                    "prompt_hash": prompt_hash,
                })
                if row_img_nec == "IMG_REQ":
                    n_entity_img_req += 1
                else:
                    n_entity_img_opt += 1
            else:
                n_entity_img_none += 1

            n_entities += 1

            # anki cards flatten
            cards = ent.get("anki_cards", [])
            if not isinstance(cards, list):
                cards = []

            for c in cards:
                if not isinstance(c, dict):
                    continue
                card_type = norm_cell(c.get("card_type"))
                front = norm_cell(c.get("front"))
                back = norm_cell(c.get("back"))

                tags_val = c.get("tags", [])
                if isinstance(tags_val, list):
                    tags_str = " ".join([norm_cell(t) for t in tags_val if norm_cell(t)])
                else:
                    tags_str = norm_cell(tags_val)

                if not front or not back:
                    continue

                anki_rows.append({
                    # common group fields
                    "provider": provider,
            "run_tag": run_tag,
            "arm": arm_log_val,
                    "record_id": record_id,
                    "specialty": specialty,
                    "anatomy": anatomy,
                    "modality_or_type": modality_or_type,
                    "category": category,
                    "group_key": group_key,
                    "group_size": group_size,
                    "split_index": split_index,
                    "weight_factor": weight_factor,
                    "group_weight_sum": group_weight_sum,

                    # legacy
                    "topic": topic,
                    "archetype": archetype,

                    # card fields
                    "entity_name": entity_name,
                    "importance_score": importance_score,
                    "card_type": card_type,
                    "front": front,
                    "back": back,
                    "tags": tags_str,
                    "row_image_necessity": row_img_nec,
                    "row_image_prompt_en": row_img_prompt,

                    # meta
                    "model_version": model_version,
                    "timestamp": timestamp,
                    "prompt_hash": prompt_hash,
                })

                n_cards += 1
                card_type_counts[card_type] = card_type_counts.get(card_type, 0) + 1

    # Write outputs
    write_csv(out_table_csv, TABLE_INFO_HEADER, table_rows)
    write_csv(out_entity_img_csv, ENTITY_IMAGE_HEADER, entity_img_rows)
    write_csv(out_anki_csv, ANKI_CARDS_HEADER, anki_rows)

    summary = {
        "provider": provider,
            "run_tag": run_tag,
            "arm": arm_val,
        "input_jsonl": str(in_jsonl),
        "output_dir": str(out_dir),
        "created_at_ts": int(time.time()),
        "counts": {
            "jsonl_lines_total": n_total,
            "content_lines": n_content,
            "error_lines_skipped": n_error,
            "skipped_nonconforming": n_skipped,
            "table_rows": n_tables,
            "entity_rows_total": n_entities,
            "entity_image_rows_written": len(entity_img_rows),
            "entity_image_req": n_entity_img_req,
            "entity_image_opt": n_entity_img_opt,
            "entity_image_none": n_entity_img_none,
            "anki_cards_rows": n_cards,
        },
        "card_type_counts": dict(sorted(card_type_counts.items(), key=lambda x: (-x[1], x[0]))),
        "outputs": {
            "table_infographic_prompts_csv": str(out_table_csv),
            "image_prompts_csv": str(out_entity_img_csv),
            "anki_cards_csv": str(out_anki_csv),
            "summary_json": str(out_summary_json),
        },
        "headers": {
            "table_infographic_prompts": TABLE_INFO_HEADER,
            "image_prompts": ENTITY_IMAGE_HEADER,
            "anki_cards": ANKI_CARDS_HEADER,
        },
    }
    write_json(out_summary_json, summary)

    print("✅ Step 02 postprocess completed (v3.8 fix).")
    print(f"  Input JSONL: {in_jsonl}")
    print(f"  Table CSV:   {out_table_csv}   (rows={n_tables})")
    print(f"  Entity CSV:  {out_entity_img_csv} (rows={len(entity_img_rows)})")
    print(f"  Anki CSV:    {out_anki_csv}    (rows={n_cards})")
    print(f"  Summary:     {out_summary_json}")
    print("  Card types:")
    for k, v in summary["card_type_counts"].items():
        print(f"    - {k}: {v}")


if __name__ == "__main__":
    main()

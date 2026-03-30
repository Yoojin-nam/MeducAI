#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
02_postprocess_results.py (MeducAI v3.0)
----------------------------------------
Step 02: Normalize Step 01 JSONL output into stable CSV interfaces.

Input:
- 2_Data/metadata/generated/<provider>/output_<provider>_<run_tag>.jsonl

Outputs (same folder):
- table_infographic_prompts_<provider>_<run_tag>.csv
- image_prompts_<provider>_<run_tag>.csv
- anki_cards_<provider>_<run_tag>.csv
- postprocess_summary_<provider>_<run_tag>.json

Notes:
- append-safe Step 01 JSONL을 "정규화된 인터페이스 CSV"로 변환하는 단계
- Step 04 (Anki export)에서 subdeck 분리를 위해 specialty/topic 등 source_info를 카드 CSV로 내립니다.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


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
            w.writerow({h: r.get(h, "") for h in header})


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def extract_source_info(meta: Dict[str, Any]) -> Dict[str, str]:
    src = meta.get("source_info", {}) if isinstance(meta, dict) else {}
    if not isinstance(src, dict):
        src = {}

    # Step 01이 source_info에 넣는 키 기준
    return {
        "specialty": safe_str(src.get("specialty")),
        "anatomy": safe_str(src.get("anatomy")),
        "topic": safe_str(src.get("topic")),
        "tags_source": safe_str(src.get("tags")),  # 참고용(anki tags와 다를 수 있음)
    }


# -------------------------
# Headers (v3.0)
# -------------------------
TABLE_INFO_HEADER = [
    "provider",
    "run_tag",
    "record_id",
    "specialty",
    "anatomy",
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

ENTITY_IMAGE_HEADER = [
    "provider",
    "run_tag",
    "record_id",
    "specialty",
    "anatomy",
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

ANKI_CARDS_HEADER = [
    "provider",
    "run_tag",
    "record_id",
    "specialty",
    "anatomy",
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
    parser = argparse.ArgumentParser(description="MeducAI Step 02 - Postprocess JSONL into CSV interfaces (v3.0)")
    parser.add_argument("--provider", required=True, help="Provider name (gemini/gpt/deepseek/claude)")
    parser.add_argument("--run_tag", required=True, help="Same run_tag used in Step 01 output filename")
    parser.add_argument("--base_dir", default=".", help="MeducAI project root (default=.)")
    parser.add_argument("--keep_failed", action="store_true", help="Include error lines too (default: skip)")
    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    provider = safe_str(args.provider)
    run_tag = safe_str(args.run_tag)

    in_jsonl = (
        base_dir
        / "2_Data"
        / "metadata"
        / "generated"
        / provider
        / f"output_{provider}_{run_tag}.jsonl"
    )

    out_dir = in_jsonl.parent
    out_table_csv = out_dir / f"table_infographic_prompts_{provider}_{run_tag}.csv"
    out_entity_img_csv = out_dir / f"image_prompts_{provider}_{run_tag}.csv"
    out_anki_csv = out_dir / f"anki_cards_{provider}_{run_tag}.csv"
    out_summary_json = out_dir / f"postprocess_summary_{provider}_{run_tag}.json"

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

    # By card_type
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
                # we still might want metadata for debugging, but we won't output CSV rows
                pass
            continue

        meta = obj.get("metadata", {})
        content = obj.get("curriculum_content", {})

        if not isinstance(meta, dict) or not isinstance(content, dict):
            n_skipped += 1
            continue

        n_content += 1

        record_id = safe_str(meta.get("id"))
        model_version = safe_str(meta.get("model_version"))
        timestamp = safe_int(meta.get("timestamp"))
        prompt_hash = safe_str(meta.get("prompt_hash"))

        src = extract_source_info(meta)
        specialty = src["specialty"]
        anatomy = src["anatomy"]
        topic = src["topic"]
        # archetype은 Step 01이 source_info에 넣지 않을 수 있음 → 빈값 허용
        archetype = safe_str(meta.get("source_info", {}).get("archetype", ""))

        objective = safe_str(content.get("objective"))
        visual_type = safe_str(content.get("visual_type"))

        # 1) Table infographic row (one per record_id)
        table_inf = content.get("table_infographic", {}) if isinstance(content.get("table_infographic"), dict) else {}
        table_style = safe_str(table_inf.get("style"))
        table_kw = safe_str(table_inf.get("keywords_en"))
        table_prompt = safe_str(table_inf.get("prompt_en"))

        # table row는 prompt가 있을 때만 넣는게 합리적(없어도 넣어도 되지만 여기서는 생성됐다는 가정)
        table_rows.append({
            "provider": provider,
            "run_tag": run_tag,
            "record_id": record_id,
            "specialty": specialty,
            "anatomy": anatomy,
            "topic": topic,
            "archetype": archetype,
            "objective": objective,
            "visual_type": visual_type,
            "table_infographic_style": table_style,
            "table_infographic_keywords_en": table_kw,
            "table_infographic_prompt_en": table_prompt,
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

            entity_name = safe_str(ent.get("entity_name"))
            importance_score = safe_int(ent.get("importance_score"), default=50)
            row_img_nec = safe_str(ent.get("row_image_necessity"))
            row_img_prompt = ent.get("row_image_prompt_en")
            row_img_prompt = "" if row_img_prompt is None else safe_str(row_img_prompt)

            # entity image prompt rows: IMG_REQ/IMG_OPT만 저장 (IMG_NONE은 prompt가 비어야 정상)
            if row_img_nec in ("IMG_REQ", "IMG_OPT"):
                entity_img_rows.append({
                    "provider": provider,
                    "run_tag": run_tag,
                    "record_id": record_id,
                    "specialty": specialty,
                    "anatomy": anatomy,
                    "topic": topic,
                    "archetype": archetype,
                    "objective": objective,
                    "visual_type": visual_type,
                    "entity_name": entity_name,
                    "importance_score": importance_score,
                    "row_image_necessity": row_img_nec,
                    "row_image_prompt_en": row_img_prompt,
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
                card_type = safe_str(c.get("card_type"))
                front = safe_str(c.get("front"))
                back = safe_str(c.get("back"))

                # tags: list or string
                tags_val = c.get("tags", [])
                if isinstance(tags_val, list):
                    tags_str = " ".join([safe_str(t) for t in tags_val if safe_str(t)])
                else:
                    tags_str = safe_str(tags_val)

                if not front or not back:
                    continue

                anki_rows.append({
                    "provider": provider,
                    "run_tag": run_tag,
                    "record_id": record_id,
                    "specialty": specialty,
                    "anatomy": anatomy,
                    "topic": topic,
                    "archetype": archetype,
                    "entity_name": entity_name,
                    "importance_score": importance_score,
                    "card_type": card_type,
                    "front": front,
                    "back": back,
                    "tags": tags_str,
                    "row_image_necessity": row_img_nec,
                    "row_image_prompt_en": row_img_prompt,
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

    print("✅ Step 02 postprocess completed.")
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

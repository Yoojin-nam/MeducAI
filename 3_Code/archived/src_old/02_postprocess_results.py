# 1. 02_postprocess_results.py 파일 전체 수정 (Overwrite)
#    - ARM_CONFIGS 추가 및 Provider 확인 로직 추가

cat << 'EOF' > 3_Code/src/02_postprocess_results.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
02_postprocess_results.py (MeducAI v3.5 - auto-provider check)
------------------------------------------------------
Step 02: Normalize Step 01 JSONL output into stable CSV interfaces.

... (중략) ...

"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from generated_paths import generated_run_dir
from typing import Any, Dict, List
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))


# -------------------------
# Arm Configuration (Re-copy from 01_generate_json.py for self-sufficiency)
# -------------------------
ARM_CONFIGS = {
    "A": {"label": "Baseline",   "provider": "gemini", "text_model_stage1": "gemini-2.5-flash", "text_model_stage2": "gemini-2.5-flash", "thinking": False, "rag": False},
    "B": {"label": "RAG_Only",   "provider": "gemini", "text_model_stage1": "gemini-2.5-flash", "text_model_stage2": "gemini-2.5-flash", "thinking": False, "rag": True},
    "C": {"label": "Thinking",   "provider": "gemini", "text_model_stage1": "gemini-2.5-flash", "text_model_stage2": "gemini-2.5-flash", "thinking": True, "thinking_budget": 1024, "rag": False},
    "D": {"label": "Synergy",    "provider": "gemini", "text_model_stage1": "gemini-2.5-flash", "text_model_stage2": "gemini-2.5-flash", "thinking": True, "thinking_budget": 1024, "rag": True},
    "E": {"label": "High_End",   "provider": "gemini", "text_model_stage1": "gemini-3-pro-preview",   "text_model_stage2": "gemini-3-pro-preview",   "thinking": True, "thinking_budget": 2048, "rag": False},
    "F": {"label": "Benchmark",  "provider": "gpt",    "text_model_stage1": "gpt-5.2-pro-2025-12-11", "text_model_stage2": "gpt-5.2-pro-2025-12-11", "thinking": True, "rag": False},
}


# -------------------------
# Utilities
# -------------------------
def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


# ... (중략: safe_str, safe_int, safe_float, norm_cell, read_jsonl, write_csv, write_json 함수는 동일) ...

def write_json(path: Path, obj: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def extract_source_info(meta: Dict[str, Any]) -> Dict[str, Any]:
    # ... (중략: extract_source_info 함수는 동일) ...
    # Decided to omit the identical long function body here for brevity.
    # It must be copied fully from the original file.
    
    # Keeping the function body identical to the original file to avoid disruption.
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

# ... (중략: get_arm, get_model_version, COMMON_GROUP_FIELDS, TABLE_INFO_HEADER, ENTITY_IMAGE_HEADER, ANKI_CARDS_HEADER는 동일) ...

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
        description="MeducAI Step 02 - Postprocess JSONL into CSV interfaces (v3.5 auto-provider check)"
    )
    # provider 인자를 제거하지 않고, arm 인자가 있을 경우 arm 설정의 provider를 따르도록 유연하게 처리
    parser.add_argument("--provider", required=True, help="Provider name (gemini/gpt/deepseek/claude)")
    parser.add_argument("--run_tag", required=True, help="Same run_tag used in Step 01 output filename")
    parser.add_argument("--arm", default="", choices=["", "A", "B", "C", "D", "E", "F"], help="Optional: arm suffix for 6-arm outputs (matches Step01 __armX filename suffix).")
    parser.add_argument("--base_dir", default=".", help="MeducAI project root (default=.)")
    parser.add_argument("--keep_failed", action="store_true", help="Include error lines too (default: skip)")
    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    
    # 🌟 [NEW] ARM Provider Override Logic (MI-CLEAR Compliance: Reproducibility)
    arm_val = norm_cell(args.arm).upper()
    provider = norm_cell(args.provider)
    
    if arm_val in ARM_CONFIGS:
        arm_provider = ARM_CONFIGS[arm_val]["provider"]
        if arm_provider != provider:
            print(f"⚠️  Warning: Provider '{provider}' given, but Arm '{arm_val}' uses '{arm_provider}'. Overriding provider to '{arm_provider}'.")
            provider = arm_provider # Arm 설정에 따라 Provider를 강제 오버라이드
    
    # End of NEW Logic 🌟
    
    run_tag = norm_cell(args.run_tag)

    arm_suffix = f"__arm{arm_val}" if arm_val else ""

    in_jsonl = (
        base_dir
        / "2_Data"
        / "metadata"
        / "generated"
        / provider
        / f"output_{provider}_{run_tag}{arm_suffix}.jsonl"
    )
    out_dir = generated_run_dir(base_dir, run_tag)
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
            "provider": provider, # 오버라이드된 최종 provider를 사용
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

    print("✅ Step 02 postprocess completed (v3.5 auto-provider check).")
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
EOF

# 2. 수정 확인
echo "Checking ARM_CONFIGS in file..."
grep -A 8 'ARM_CONFIGS' 3_Code/src/02_postprocess_results.py

echo "Checking new provider override logic..."
grep "Arm '{arm_val}' uses" 3_Code/src/02_postprocess_results.py

# 3. 실행 (Run)
# 이제 --provider를 gemini로 두더라도 Arm F의 Provider인 gpt 폴더를 찾아 시도합니다.

echo "--- 🛠️ Re-Running Step 02 for Arm F (Testing Auto-Provider Check) ---"
# 💡 실제 사용된 RUN_TAG를 여기에 고정 (로그에 기반)
RUN_TAG="S0_SMOKE_20251215_144054" 
BASE_DIR="/path/to/workspace/Library/CloudStorage/GoogleDrive-[email-redacted]/내 드라이브/Research/MeducAI"

/path/to/workspace/meducai_venv/bin/python3 3_Code/src/02_postprocess_results.py \
  --provider gemini \
  --run_tag "$RUN_TAG" \
  --arm F \
  --base_dir "$BASE_DIR"

# 4. Debug Hint
echo "# Debug: 'JSONL not found' 에러가 다시 발생하면, 입력된 RUN_TAG 값이 정확한지, 해당 경로에 JSONL 파일이 실제로 존재하는지 확인하십시오. (ls -l $BASE_DIR/2_Data/metadata/generated/gpt/ | grep $RUN_TAG)"
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
V2 tag autogenerator (Part/Region/Category/Topic tags).

Notebook reference:
- 3_Code/notebooks/RaB-LLM_06_tag_autogenerator.ipynb
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd


def _normalize_key(text: str) -> str:
    return "_".join(str(text).strip().lower().split())


def _make_topic_tag(topic_clean: str) -> str:
    t = str(topic_clean or "").strip()
    if not t:
        return "topic_unknown"
    base = t.lower().replace(" ", "_")
    return f"topic_{base}"


def _load_latest_tagging_rules(repo_root: Path) -> Path:
    cfg_dir = repo_root / "3_Code" / "configs"
    candidates = sorted(cfg_dir.glob("tagging_rules_v*.json"))
    if not candidates:
        raise FileNotFoundError(f"No tagging rules found in {cfg_dir}")
    return candidates[-1]


def _build_maps(tag_rules: Dict) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    part_label_to_tag: Dict[str, str] = {}
    category_label_to_tag: Dict[str, str] = {}
    region_key_to_tag: Dict[str, str] = tag_rules.get("region_examples", {}) or {}

    for _, info in (tag_rules.get("part", {}) or {}).items():
        label = info.get("label", "")
        tag = info.get("tag", "")
        if label and tag:
            part_label_to_tag[_normalize_key(label)] = tag

    for _, info in (tag_rules.get("category", {}) or {}).items():
        label = info.get("label", "")
        tag = info.get("tag", "")
        if label and tag:
            category_label_to_tag[_normalize_key(label)] = tag

    return part_label_to_tag, category_label_to_tag, region_key_to_tag


def _infer_part_tag(specialty_en_label: str, part_label_to_tag: Dict[str, str]) -> str:
    key = _normalize_key(specialty_en_label)
    if not key:
        return "part_unknown"
    if key in part_label_to_tag:
        return part_label_to_tag[key]
    # Heuristics (kept aligned with notebook)
    if "musculoskeletal" in key:
        return "part_msk"
    if "thoracic" in key or "chest" in key:
        return "part_thx"
    if "abdominal" in key:
        return "part_abd"
    if "genitourinary" in key or "gu_" in key or key.startswith("gu"):
        return "part_gu"
    if "neuro" in key:
        return "part_neuro"
    if "pediatric" in key:
        return "part_ped"
    if "breast" in key:
        return "part_breast"
    if "cardio" in key or "cardiovascular" in key:
        return "part_cv"
    if "interventional" in key:
        return "part_ir"
    if "nuclear" in key:
        return "part_nm"
    return "part_unknown"


def _infer_category_tag(category_en_label: str, category_label_to_tag: Dict[str, str]) -> str:
    key = _normalize_key(category_en_label)
    if not key:
        return "cat_other"
    if key in category_label_to_tag:
        return category_label_to_tag[key]
    # Heuristics (kept aligned with notebook)
    if "anatomy" in key:
        return "cat_anatomy"
    if "finding" in key or "pattern" in key:
        return "cat_findings"
    if "differential" in key or "ddx" in key:
        return "cat_ddx"
    if "technique" in key or "modality" in key:
        return "cat_technique"
    if "procedure" in key or "intervention" in key:
        return "cat_procedure"
    return "cat_other"


def _infer_region_tag(anatomy_en_label: str, region_key_to_tag: Dict[str, str]) -> str:
    key = _normalize_key(anatomy_en_label)
    if not key:
        return "reg_unknown"
    for base_key, tag in region_key_to_tag.items():
        if base_key in key:
            return tag
    return f"reg_{key.replace('__', '_')}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Auto-generate tag columns (v2).")
    ap.add_argument("--in_xlsx", required=True)
    ap.add_argument("--out_xlsx", required=True)
    ap.add_argument("--tag_rules_json", default=None, help="Optional path to tagging_rules_v*.json (defaults to latest).")
    ap.add_argument("--repo_root", default=".", help="Repo root for auto-discovery of configs.")
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    in_path = Path(args.in_xlsx).resolve()
    out_path = Path(args.out_xlsx).resolve()

    rules_path = Path(args.tag_rules_json).resolve() if args.tag_rules_json else _load_latest_tagging_rules(repo_root)
    tag_rules = json.loads(rules_path.read_text(encoding="utf-8"))

    df = pd.read_excel(in_path).reset_index(drop=True)

    # Columns expected from translation/enrichment
    specialty_col = "Specialty_EN_LABEL"
    anatomy_col = "Anatomy_EN_LABEL"
    category_col = "Category_EN_LABEL"
    topic_col = "Topic_Clean"

    for c in [specialty_col, anatomy_col, category_col, topic_col]:
        if c not in df.columns:
            raise ValueError(f"Missing expected column: {c} (input={in_path})")

    part_label_to_tag, category_label_to_tag, region_key_to_tag = _build_maps(tag_rules)

    df["Part_Tag"] = df[specialty_col].astype(str).map(lambda s: _infer_part_tag(s, part_label_to_tag))
    df["Region_Tag"] = df[anatomy_col].astype(str).map(lambda s: _infer_region_tag(s, region_key_to_tag))
    df["Category_Tag"] = df[category_col].astype(str).map(lambda s: _infer_category_tag(s, category_label_to_tag))
    df["Topic_Tag"] = df[topic_col].astype(str).map(_make_topic_tag)

    def make_anki(row) -> str:
        parts = [row.get("Part_Tag"), row.get("Region_Tag"), row.get("Topic_Tag"), row.get("Category_Tag")]
        return "; ".join([p for p in parts if isinstance(p, str) and p.strip()])

    df["Anki_Tag_String"] = df.apply(make_anki, axis=1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(out_path, index=False, engine="openpyxl")
    print(f"OK: wrote {out_path} rows={len(df)} rules={rules_path.name}")


if __name__ == "__main__":
    main()



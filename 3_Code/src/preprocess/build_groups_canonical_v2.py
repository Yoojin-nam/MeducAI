#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build versioned canonical groups file from a curriculum SSOT.

This is a v2-friendly wrapper of `3_Code/src/0_build_groups_canonical.py` that:
- allows explicit output filenames (so we don't overwrite v1)
- keeps the grouping rules identical
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


def safe_str(x) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and math.isnan(x):
        return ""
    s = str(x).strip()
    if s.lower() in {"nan", "none", "null"}:
        return ""
    return s


_DIFFICULTY_SUFFIX_RE = re.compile(r"\s*[\(\[]\s*([ABCabcSs])\s*[\)\]]\s*[\.\:;,\-]?\s*$")


def strip_trailing_difficulty(s: str) -> tuple[str, str]:
    t = safe_str(s)
    if not t:
        return "", ""
    m = _DIFFICULTY_SUFFIX_RE.search(t)
    if not m:
        return t, ""
    diff = m.group(1).upper()
    cleaned = _DIFFICULTY_SUFFIX_RE.sub("", t).strip()
    return cleaned, diff


def read_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    if path.suffix.lower() in [".xlsx", ".xls"]:
        return pd.read_excel(path, engine="openpyxl")
    return pd.read_csv(path)


def stable_group_id_from_key(group_key: str) -> str:
    h = hashlib.sha1(group_key.encode("utf-8")).hexdigest()
    return f"grp_{h[:10]}"


def ordered_unique(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for it in items:
        s = safe_str(it)
        if not s:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def pick_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    cols: Dict[str, Optional[str]] = {}
    cols["spec"] = "Specialty_EN_TAG" if "Specialty_EN_TAG" in df.columns else ("Specialty" if "Specialty" in df.columns else None)
    cols["anat"] = "Anatomy_EN_TAG" if "Anatomy_EN_TAG" in df.columns else ("Anatomy" if "Anatomy" in df.columns else None)
    cols["mod"] = "Modality_Type_EN_TAG" if "Modality_Type_EN_TAG" in df.columns else (
        "Modality/Type" if "Modality/Type" in df.columns else ("Modality_Type" if "Modality_Type" in df.columns else None)
    )
    cols["cat"] = "Category_EN_TAG" if "Category_EN_TAG" in df.columns else ("Category" if "Category" in df.columns else None)
    cols["w"] = "weight_factor" if "weight_factor" in df.columns else None

    objective_en_candidates = [
        "Objective_EN",
        "Objective List",
        "Objective_List",
        "Learning Objective",
        "Learning_Objective",
        "ObjectiveText",
        "Objective_Text",
    ]
    cols["obj"] = next((c for c in objective_en_candidates if c in df.columns), None)
    if cols["obj"] is None and "Objective" in df.columns:
        cols["obj"] = "Objective"

    if "Objective_EN" in df.columns and "Objective" in df.columns:
        cols["obj_kr"] = "Objective"
    else:
        korean_objective_candidates = [
            "Objective_KR",
            "Objective_KO",
            "Objective_ko",
            "Objective_kr",
            "Objective_한글",
            "Learning Objective_KR",
            "Learning_Objective_KR",
        ]
        cols["obj_kr"] = next((c for c in korean_objective_candidates if c in df.columns), None)

    missing_required = [k for k in ["spec", "anat", "mod", "cat", "w"] if cols.get(k) is None]
    if missing_required:
        raise ValueError(f"Missing required columns (or fallbacks not found): {missing_required}")
    if cols["obj"] is None:
        raise ValueError("Missing objective text column (Objective_EN or Objective).")
    return cols


def make_group_key(anat: str, mod: str, cat: str) -> str:
    if cat:
        return f"{anat}__{mod}__{cat}"
    return f"{anat}__{mod}"


def dominant_specialty_per_group(df: pd.DataFrame) -> pd.DataFrame:
    spec_w = (
        df.groupby(["group_key", "specialty"], as_index=False)["w"]
        .sum()
    )
    spec_w = spec_w.rename(columns={"w": "spec_weight_sum"})  # type: ignore[call-arg]
    idx = spec_w.groupby("group_key")["spec_weight_sum"].idxmax()
    dom = spec_w.loc[idx, ["group_key", "specialty"]].copy()
    dom["specialty"] = dom["specialty"].fillna("")
    return dom


def objective_list_per_group(df: pd.DataFrame, objective_col: str) -> pd.DataFrame:
    agg = (
        df.groupby("group_key")[objective_col]
        .apply(lambda s: ordered_unique(list(s)))
        .reset_index()
    )
    agg.columns = ["group_key", "objective_list"]
    agg["objective_list"] = agg["objective_list"].apply(lambda lst: json.dumps(lst, ensure_ascii=False))
    return agg


def main() -> None:
    ap = argparse.ArgumentParser(description="Build versioned groups_canonical_v2.csv (SSOT).")
    ap.add_argument("--input", required=True, help="Curriculum source file (xlsx/csv) with weight_factor")
    ap.add_argument("--out_csv", required=True, help="Output groups CSV path (versioned)")
    ap.add_argument("--out_meta", required=True, help="Output meta JSON path (versioned)")
    args = ap.parse_args()

    in_path = Path(args.input).resolve()
    out_csv = Path(args.out_csv).resolve()
    out_meta = Path(args.out_meta).resolve()
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_meta.parent.mkdir(parents=True, exist_ok=True)

    df_raw = read_table(in_path)
    df_raw.columns = [c.strip() for c in df_raw.columns]
    cols = pick_columns(df_raw)

    df = pd.DataFrame()
    df["specialty"] = df_raw[cols["spec"]].map(safe_str)
    df["anatomy"] = df_raw[cols["anat"]].map(safe_str)
    df["modality_or_type"] = df_raw[cols["mod"]].map(safe_str)
    df["category"] = df_raw[cols["cat"]].map(safe_str)
    df["objective_text"] = df_raw[cols["obj"]].map(safe_str)

    cleaned = df["objective_text"].apply(strip_trailing_difficulty)
    df["objective_text"] = cleaned.apply(lambda x: x[0])
    df["objective_difficulty"] = cleaned.apply(lambda x: x[1])

    if cols["obj_kr"]:
        df["objective_text_kr"] = df_raw[cols["obj_kr"]].map(safe_str)
        cleaned_kr = df["objective_text_kr"].apply(strip_trailing_difficulty)
        df["objective_text_kr"] = cleaned_kr.apply(lambda x: x[0])
    else:
        df["objective_text_kr"] = ""

    df["w"] = pd.to_numeric(df_raw[cols["w"]], errors="coerce")
    df["w"] = df["w"].fillna(0.0).astype(float)
    df["group_key"] = [make_group_key(a, m, c) for a, m, c in zip(df["anatomy"], df["modality_or_type"], df["category"])]

    grp = df.groupby("group_key", as_index=False).agg(
        objectives=("group_key", "count"),
        group_weight_sum=("w", "sum"),
    )
    grp = grp.sort_values("group_weight_sum", ascending=False).reset_index(drop=True)  # type: ignore[call-arg]

    obj_agg = objective_list_per_group(df, objective_col="objective_text")
    grp = grp.merge(obj_agg, on="group_key", how="left")
    grp["objective_list"] = grp["objective_list"].fillna("[]")

    obj_kr_agg = objective_list_per_group(df, objective_col="objective_text_kr")
    obj_kr_agg = obj_kr_agg.rename(columns={"objective_list": "objective_list_kr"})
    grp = grp.merge(obj_kr_agg, on="group_key", how="left")
    grp["objective_list_kr"] = grp["objective_list_kr"].fillna("[]")

    parts = grp["group_key"].str.split("__", expand=True)
    grp["anatomy"] = parts[0].fillna("")
    grp["modality_or_type"] = parts[1].fillna("")
    grp["category"] = parts[2].fillna("") if parts.shape[1] > 2 else ""
    grp["group_id"] = grp["group_key"].map(stable_group_id_from_key)

    dom = dominant_specialty_per_group(df)
    grp = grp.merge(dom, on="group_key", how="left")
    grp["specialty"] = grp["specialty"].fillna("")

    cols_out = [
        "group_id",
        "group_key",
        "specialty",
        "anatomy",
        "modality_or_type",
        "category",
        "objectives",
        "objective_list",
        "objective_list_kr",
        "group_weight_sum",
    ]
    grp[cols_out].to_csv(out_csv, index=False, encoding="utf-8")

    total_rows = int(len(df))
    removed_rows = int((df["objective_difficulty"] != "").sum())
    by_level = {k: int((df["objective_difficulty"] == k).sum()) for k in ["A", "B", "C", "S"]}

    meta = {
        "status": "canonical_v2_versioned",
        "generated_by": "build_groups_canonical_v2.py",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_file": str(in_path),
        "grouping_rule": "Anatomy–Modality/Type–Category (fallback if category empty)",
        "weight_definition": "group_weight_sum = sum(weight_factor)",
        "normalization": "none",
        "objective_list": {
            "source_column": cols["obj"],
            "aggregation": "ordered_unique(list of row-level objective texts) per group_key",
            "serialization": "JSON string in CSV cell",
        },
        "objective_text_cleanup": {
            "applied": True,
            "pattern": _DIFFICULTY_SUFFIX_RE.pattern,
            "removed_rows": removed_rows,
            "total_rows": total_rows,
            "by_level": by_level,
        },
    }
    out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print("OK")
    print(f"- out_csv: {out_csv}")
    print(f"- out_meta: {out_meta}")
    print(f"- groups: {len(grp)}")


if __name__ == "__main__":
    main()



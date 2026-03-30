#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
V2 merge weights: compute and append `weight_factor` using the blueprint-style
question plan, matching the notebook logic.

Notebook reference:
- 3_Code/notebooks/0_merge_weights.ipynb
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


QUESTION_PLAN = {
    "흉부 영상의학": 24,
    "심장 혈관계 영상의학": 11,
    "인터벤션 영상의학": 14,
    "복부 영상의학": 31,
    "비뇨생식기계 영상의학": 17,
    "뇌신경계 및 두경부 영상의학": 25,
    "근골격계 영상의학": 21,
    "소아 영상의학": 17,
    "유방 영상의학": 14,
    "핵의학": 4,
    "물리, 품질관리 및 의료정보": 22,
}


def main() -> None:
    ap = argparse.ArgumentParser(description="Append weight_factor to tagged curriculum (v2).")
    ap.add_argument("--in_xlsx", required=True)
    ap.add_argument("--out_xlsx", required=True)
    args = ap.parse_args()

    in_path = Path(args.in_xlsx).resolve()
    out_path = Path(args.out_xlsx).resolve()

    df = pd.read_excel(in_path)
    df.columns = df.columns.str.strip()
    if "Specialty" not in df.columns:
        raise ValueError("Input missing Specialty column")

    obj_per_spec = df.groupby("Specialty", as_index=False).agg(n_objectives=("Specialty", "size"))
    q_df = pd.DataFrame(list(QUESTION_PLAN.items()), columns=["Specialty", "n_questions"])  # type: ignore[arg-type]

    summary = obj_per_spec.merge(q_df, on="Specialty", how="left")
    summary["n_questions"] = summary["n_questions"].fillna(0)
    summary["q_per_obj"] = summary["n_questions"] / summary["n_objectives"]

    mean_q_per_obj = summary["q_per_obj"].replace([np.inf, -np.inf], 0).mean()
    summary["weight_factor"] = summary["q_per_obj"] / mean_q_per_obj

    weight_map: dict[str, float] = summary.set_index("Specialty")["weight_factor"].to_dict()  # type: ignore[assignment]
    df["weight_factor"] = df["Specialty"].map(weight_map)  # type: ignore[arg-type]
    df["weight_factor"] = df["weight_factor"].fillna(1.0).astype(float)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(out_path, index=False, engine="openpyxl")
    print(f"OK: wrote {out_path} rows={len(df)}")


if __name__ == "__main__":
    main()



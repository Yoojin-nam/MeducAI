#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import argparse
from pathlib import Path
import math
import pandas as pd
import matplotlib.pyplot as plt


def safe_str(x) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and math.isnan(x):
        return ""
    s = str(x).strip()
    if s.lower() in {"nan", "none", "null"}:
        return ""
    return s


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def read_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    if path.suffix.lower() in [".xlsx", ".xls"]:
        return pd.read_excel(path, engine="openpyxl")
    return pd.read_csv(path)


def save_bar(series: pd.Series, title: str, out_png: Path, topn: int = 15):
    vc = series.value_counts().head(topn)
    plt.figure()
    vc.plot(kind="bar")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()


def save_hist(values: pd.Series, title: str, out_png: Path, bins: int = 30):
    plt.figure()
    plt.hist(values.astype(float), bins=bins)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()


def gini(arr) -> float:
    a = [float(x) for x in arr if x is not None]
    a = [x for x in a if x >= 0]
    if not a:
        return 0.0
    a.sort()
    n = len(a)
    cum = 0.0
    for i, x in enumerate(a, start=1):
        cum += i * x
    total = sum(a)
    if total == 0:
        return 0.0
    return (2 * cum) / (n * total) - (n + 1) / n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base_dir", default=".")
    ap.add_argument("--input", required=True, help="xlsx/csv path containing curriculum metadata + weight_factor")
    ap.add_argument("--run_tag", default="EDA_STRUCT")
    ap.add_argument("--total_cards", type=int, default=6000, help="target total cards for expected allocation")
    args = ap.parse_args()

    base_dir = Path(args.base_dir).resolve()
    in_path = Path(args.input).expanduser()
    if not in_path.is_absolute():
        in_path = (base_dir / in_path).resolve()

    df = read_table(in_path)
    df.columns = [c.strip() for c in df.columns]

    # Required-ish columns (from your sample)
    col_spec = "Specialty_EN_TAG" if "Specialty_EN_TAG" in df.columns else "Specialty"
    col_anat = "Anatomy_EN_TAG" if "Anatomy_EN_TAG" in df.columns else "Anatomy"
    col_mod  = "Modality_Type_EN_TAG" if "Modality_Type_EN_TAG" in df.columns else ("Modality/Type" if "Modality/Type" in df.columns else "Modality_Type")
    col_cat  = "Category_EN_TAG" if "Category_EN_TAG" in df.columns else "Category"
    col_w    = "weight_factor"

    for c in [col_spec, col_anat, col_mod, col_cat, col_w]:
        if c not in df.columns:
            raise ValueError(f"Missing required column: {c}")

    # Normalize strings
    df["_spec"] = df[col_spec].map(safe_str)
    df["_anat"] = df[col_anat].map(safe_str)
    df["_mod"]  = df[col_mod].map(safe_str)
    df["_cat"]  = df[col_cat].map(safe_str)

    # Group rule: with/without category
    def make_group_key(r):
        if r["_cat"]:
            return f"{r['_anat']}__{r['_mod']}__{r['_cat']}"
        return f"{r['_anat']}__{r['_mod']}"
    df["_group_key"] = df.apply(make_group_key, axis=1)

    # Weight
    df["_w"] = pd.to_numeric(df[col_w], errors="coerce").fillna(0.0)

    # Group aggregates
    grp = df.groupby("_group_key", as_index=False).agg(
        objectives=(" _group_key".strip(), "count")  # trick: count rows
    )
    grp["group_weight_sum"] = df.groupby("_group_key")["_w"].sum().values
    grp["expected_cards"] = (args.total_cards * grp["group_weight_sum"] / (grp["group_weight_sum"].sum() or 1.0)).round().astype(int)

    # For convenience: split group key back to anatomy/modality/category
    parts = grp["_group_key"].str.split("__", expand=True)
    grp["anatomy_tag"] = parts[0]
    grp["modality_tag"] = parts[1]
    grp["category_tag"] = parts[2] if parts.shape[1] > 2 else ""

    # Subspecialty aggregates
    subs = df.groupby("_spec", as_index=False).agg(
        objectives=(" _spec".strip(), "count")
    )
    subs["weight_sum"] = df.groupby("_spec")["_w"].sum().values
    subs["expected_cards"] = (args.total_cards * subs["weight_sum"] / (subs["weight_sum"].sum() or 1.0)).round().astype(int)
    subs["share_expected_cards"] = subs["expected_cards"] / (subs["expected_cards"].sum() or 1.0)
    subs["cards_per_objective"] = subs["expected_cards"] / subs["objectives"]

    # Key stats
    n_obj = len(df)
    n_groups = grp["_group_key"].nunique()
    total_weight = float(df["_w"].sum())
    grp_sorted = grp.sort_values("group_weight_sum", ascending=False)
    top20_n = max(1, int(0.2 * len(grp_sorted)))
    top20_share = float(grp_sorted.head(top20_n)["group_weight_sum"].sum() / (total_weight or 1.0))
    gini_w = gini(grp["group_weight_sum"].values)

    # Output dirs
    out_dir = base_dir / "2_Data" / "eda" / args.run_tag
    figs = out_dir / "figs"
    tables = out_dir / "tables"
    ensure_dir(figs); ensure_dir(tables)

    # Save tables
    grp_sorted.to_csv(tables / "groups_weight_expected_cards.csv", index=False)
    subs.sort_values("expected_cards", ascending=False).to_csv(tables / "subspecialty_expected_cards.csv", index=False)

    # Figures
    save_hist(grp["objectives"], "Distribution: Objectives per Group", figs / "group_objectives_hist.png")
    save_hist(grp["group_weight_sum"], "Distribution: Group Weight Sum", figs / "group_weight_hist.png")
    save_bar(df["_spec"], "Subspecialty Distribution by Objectives (Top 15)", figs / "subspecialty_objectives_top15.png", topn=15)

    # Decision-ready conclusion sentence
    decision_sentence = (
        f"Based on EDA of the 1,780-objective curriculum metadata, objectives were consolidated into {n_groups:,} groups "
        f"(category-aware grouping), and the top 20% of groups accounted for {top20_share*100:.1f}% of the total weight "
        f"(Gini={gini_w:.2f}), supporting a group-first deployment strategy and weight-informed allocation "
        f"for an estimated {args.total_cards:,} cards."
    )

    # 1-page MD summary
    md = []
    md.append(f"# MeducAI EDA – 1-page Summary ({args.run_tag})")
    md.append("")
    md.append("## Executive Takeaways (Decision-ready)")
    md.append("")
    md.append("**Conclusion sentence (fixed):**")
    md.append("")
    md.append(f"> {decision_sentence}")
    md.append("")
    md.append("## Key Numbers")
    md.append("")
    md.append(f"- Total objectives: **{n_obj:,}**")
    md.append(f"- Total groups: **{n_groups:,}**")
    md.append(f"- Total weight sum: **{total_weight:.3f}**")
    md.append(f"- Top 20% group weight share: **{top20_share*100:.1f}%**")
    md.append(f"- Weight inequality (Gini): **{gini_w:.2f}**")
    md.append(f"- Total expected cards (assumed): **{args.total_cards:,}**")
    md.append("")
    md.append("## Figures")
    md.append("")
    md.append(f"![Objectives per group](figs/group_objectives_hist.png)")
    md.append(f"![Group weight](figs/group_weight_hist.png)")
    md.append(f"![Subspecialty objectives](figs/subspecialty_objectives_top15.png)")
    md.append("")
    md.append("## Tables (evidence)")
    md.append("")
    md.append("- `tables/groups_weight_expected_cards.csv`")
    md.append("- `tables/subspecialty_expected_cards.csv`")

    (out_dir / "eda_summary_1page.md").write_text("\n".join(md), encoding="utf-8")

    print(f"[OK] Outputs: {out_dir}")
    print("[OK] Decision sentence:")
    print(decision_sentence)


if __name__ == "__main__":
    main()

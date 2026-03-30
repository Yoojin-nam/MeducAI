#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
04_5_check_deck_stats.py (MeducAI v3.2)
---------------------------------------
Purpose:
- Validate deck candidate/selected CSV stats:
  1) Coverage: per (specialty/anatomy/topic) counts, min/max, uncovered topics
  2) Mix: card_type distribution vs expected mix (optional)
  3) Image: necessity distribution (if columns exist)
  4) Group: group_key distribution (if exists), group_weight_sum distribution (if exists)
  5) Sanity: missing required columns, empty fields, NaN/"nan" leakage

Input:
- anki_cards_<provider>_<run_tag>.csv (candidate) OR
- anki_cards_selected_<provider>_<run_tag>.csv (selected)

Outputs:
- prints a concise report to stdout
- optionally writes JSON report to 2_Data/metadata/generated/<provider>/deck_stats_<provider>_<run_tag>.json
"""

from __future__ import annotations


from generated_paths import generated_run_dir, resolve_in_run_or_legacy
import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# -------------------------
# CSV loader (critical)
# -------------------------
def load_csv_stable(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    df = pd.read_csv(path, keep_default_na=False, na_filter=False)
    df.columns = df.columns.str.strip()
    return df


def safe_str(x: Any) -> str:
    if x is None:
        return ""
    # keep_default_na=False로 읽어도, 보험용 처리
    try:
        if isinstance(x, float) and math.isnan(x):
            return ""
    except Exception:
        pass
    s = str(x).strip()
    if s.lower() in {"nan", "null", "none"}:
        return ""
    return s


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def parse_mix(s: str) -> Dict[str, float]:
    """
    Example: "Basic_QA:0.34,Cloze_Finding:0.33,MCQ_Vignette:0.33"
    Returns normalized ratios.
    """
    s = safe_str(s)
    if not s:
        return {}
    out: Dict[str, float] = {}
    for part in s.split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        k, v = part.split(":", 1)
        k = k.strip()
        try:
            out[k] = float(v.strip())
        except Exception:
            continue
    tot = sum(out.values())
    if tot > 0:
        out = {k: v / tot for k, v in out.items()}
    return out


def freq_table(series: pd.Series) -> Dict[str, int]:
    vc = series.value_counts(dropna=False)
    return {safe_str(k): int(v) for k, v in vc.items()}


def compute_topic_key(df: pd.DataFrame) -> pd.Series:
    sp = df.get("specialty", "")
    an = df.get("anatomy", "")
    tp = df.get("topic", "")
    return sp.astype(str) + " | " + an.astype(str) + " | " + tp.astype(str)


def report_mix(actual: Dict[str, int], expected: Dict[str, float], total: int) -> Dict[str, Any]:
    """
    Compare actual counts vs expected ratios.
    """
    if not expected:
        return {"enabled": False}
    rows: List[Dict[str, Any]] = []
    for ct, ratio in expected.items():
        exp = ratio * total
        act = actual.get(ct, 0)
        rows.append({
            "card_type": ct,
            "expected_ratio": ratio,
            "expected_count": exp,
            "actual_count": act,
            "delta": act - exp,
        })
    # add actual-only types
    for ct in actual.keys():
        if ct not in expected:
            rows.append({
                "card_type": ct,
                "expected_ratio": 0.0,
                "expected_count": 0.0,
                "actual_count": actual.get(ct, 0),
                "delta": actual.get(ct, 0),
            })
    rows.sort(key=lambda r: (-r["actual_count"], r["card_type"]))
    return {"enabled": True, "rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser(description="MeducAI Step 04.5 - Check deck stats (coverage/mix/sanity)")

    ap.add_argument("--provider", required=True)
    ap.add_argument("--run_tag", required=True)
    ap.add_argument("--arm", default="", help="Arm label (A-F). If set, uses __armX suffix")
    ap.add_argument("--base_dir", default=".")
    ap.add_argument("--selected", action="store_true", help="Use anki_cards_selected_* instead of anki_cards_*")
    ap.add_argument("--save_json", action="store_true", help="Save deck stats JSON alongside CSV")
    ap.add_argument("--input_csv", default="", help="Optional override CSV path")

    ap.add_argument("--min_per_topic", type=int, default=0, help="Coverage check threshold (0 disables)")
    ap.add_argument("--max_per_topic", type=int, default=0, help="Coverage cap check (0 disables)")

    ap.add_argument("--expected_card_mix", default="", help='e.g. "Basic_QA:0.34,Cloze_Finding:0.33,MCQ_Vignette:0.33"')
    # NOTE: write_json deprecated; use --save_json


    args = ap.parse_args()


    arm = (getattr(args, "arm", "") or "").strip()
    suffix = f"__arm{arm}" if arm else ""
    base_dir = Path(args.base_dir).resolve()
    if args.input_csv.strip():
        csv_path = Path(args.input_csv).expanduser()
        if not csv_path.is_absolute():
            csv_path = (base_dir / csv_path).resolve()
    else:
        fname = f"anki_cards_selected_{args.provider}_{args.run_tag}{suffix}.csv" if args.selected else f"anki_cards_{args.provider}_{args.run_tag}{suffix}.csv"
        csv_path = resolve_in_run_or_legacy(base_dir, args.run_tag, args.provider, fname)

    df = load_csv_stable(csv_path)

    # Required columns for basic sanity (create if missing)
    for col in ["record_id", "entity_name", "card_type", "front", "back", "specialty", "anatomy", "topic"]:
        if col not in df.columns:
            df[col] = ""

    # -------- Sanity checks --------
    n = len(df)
    empty_front = int((df["front"].astype(str).str.strip() == "").sum())
    empty_back = int((df["back"].astype(str).str.strip() == "").sum())

    # "nan" leakage check (string-level)
    nan_like = {}
    for col in ["category", "group_key", "record_id", "entity_name", "specialty", "anatomy", "topic"]:
        if col in df.columns:
            s = df[col].astype(str).str.strip().str.lower()
            nan_like[col] = int((s.isin(["nan", "none", "null"])).sum())

    # -------- Coverage --------
    df["_topic_key"] = compute_topic_key(df)
    topic_counts = df["_topic_key"].value_counts(dropna=False)
    n_topics = int(topic_counts.shape[0])
    min_count = int(topic_counts.min()) if n_topics else 0
    max_count = int(topic_counts.max()) if n_topics else 0

    undercovered: List[Tuple[str, int]] = []
    overcovered: List[Tuple[str, int]] = []
    if args.min_per_topic and args.min_per_topic > 0:
        under = topic_counts[topic_counts < args.min_per_topic]
        undercovered = [(idx, int(val)) for idx, val in under.items()]
    if args.max_per_topic and args.max_per_topic > 0:
        over = topic_counts[topic_counts > args.max_per_topic]
        overcovered = [(idx, int(val)) for idx, val in over.items()]

    # -------- Mix --------
    actual_mix = freq_table(df["card_type"].astype(str))
    expected_mix = parse_mix(args.expected_card_mix)
    mix_report = report_mix(actual_mix, expected_mix, n)

    # -------- Optional distributions --------
    group_counts = {}
    if "group_key" in df.columns:
        group_counts = freq_table(df["group_key"].astype(str))

    img_necessity_counts = {}
    if "image_necessity" in df.columns:
        img_necessity_counts = freq_table(df["image_necessity"].astype(str))

    # -------- Print report --------
    print("=== MeducAI Step 04.5 Deck Stats ===")
    print(f"CSV: {csv_path}")
    print(f"Rows: {n}")
    print("")
    print("[Sanity]")
    print(f"- empty front: {empty_front}")
    print(f"- empty back : {empty_back}")
    for k, v in nan_like.items():
        if v:
            print(f"- nan-like strings in {k}: {v}")

    print("")
    print("[Coverage]")
    print(f"- topics: {n_topics}")
    print(f"- per-topic min/max: {min_count} / {max_count}")
    if args.min_per_topic:
        print(f"- undercovered (<{args.min_per_topic}): {len(undercovered)}")
        for tk, c in undercovered[:10]:
            print(f"  * {tk} = {c}")
        if len(undercovered) > 10:
            print("  ...")
    if args.max_per_topic:
        print(f"- overcovered (>{args.max_per_topic}): {len(overcovered)}")
        for tk, c in overcovered[:10]:
            print(f"  * {tk} = {c}")
        if len(overcovered) > 10:
            print("  ...")

    print("")
    print("[Card Type Mix]")
    for ct, cnt in sorted(actual_mix.items(), key=lambda x: (-x[1], x[0])):
        print(f"- {ct}: {cnt}")

    if mix_report.get("enabled"):
        print("")
        print("[Mix vs Expected]")
        for r in mix_report["rows"][:15]:
            print(
                f"- {r['card_type']}: actual={r['actual_count']}, "
                f"expected≈{r['expected_count']:.1f} (ratio={r['expected_ratio']:.3f}), "
                f"delta={r['delta']:.1f}"
            )
        if len(mix_report["rows"]) > 15:
            print("  ...")

    if group_counts:
        print("")
        print("[Group Key]")
        print(f"- unique groups: {len(group_counts)}")

    if img_necessity_counts:
        print("")
        print("[Image Necessity]")
        for k, v in sorted(img_necessity_counts.items(), key=lambda x: (-x[1], x[0])):
            print(f"- {k}: {v}")

    # -------- JSON report (optional) --------
    report = {
        "csv": str(csv_path),
        "rows": n,
        "sanity": {
            "empty_front": empty_front,
            "empty_back": empty_back,
            "nan_like_strings": nan_like,
        },
        "coverage": {
            "topics": n_topics,
            "min_per_topic": min_count,
            "max_per_topic": max_count,
            "undercovered": undercovered[:200],
            "overcovered": overcovered[:200],
        },
        "mix": {
            "actual": actual_mix,
            "expected": expected_mix,
            "comparison": mix_report,
        },
        "group_key": {
            "unique_groups": len(group_counts) if group_counts else 0,
        },
        "image_necessity": img_necessity_counts,
    }

    if args.save_json:
        out_dir = generated_run_dir(base_dir, args.run_tag)
        ensure_dir(out_dir)
        suffix = f"__arm{arm}" if arm else ""
        out_path = out_dir / f"deck_stats_{args.provider}_{args.run_tag}{suffix}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print("")
        print(f"JSON report written: {out_path}")


if __name__ == "__main__":
    main()

# # NOTE(P0-2): --target_total is a CARD COUNT target for deck selection.
# Fields like target_count / group_target_entities are ENTITY targets recorded for auditability only.

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
03_5_select_deck.py
-------------------
MeducAI Step 03.5: Candidate pool selection (coverage + high-yield + dedup)

Input:
- 2_Data/metadata/generated/<provider>/anki_cards_<provider>_<run_tag>.csv

Output:
- 2_Data/metadata/generated/<provider>/anki_cards_selected_<provider>_<run_tag>.csv

Selection objectives:
1) Coverage: ensure at least min_per_topic cards per (specialty, anatomy, topic)
2) Cap: at most max_per_topic cards per topic
3) High-yield: prioritize by priority_score (importance_score + weight_factor)
4) Dedup: remove near-duplicates using dedup_key
5) Card-type mix: enforce approximate mix (optional)

Note:
- This is deterministic by default.
"""

from __future__ import annotations


from generated_paths import generated_run_dir, resolve_in_run_or_legacy
import argparse
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd


# -------------------------
# Utilities
# -------------------------
def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def safe_str(x: Any) -> str:
    """
    Stable string conversion:
    - None -> ""
    - float('nan') -> ""
    - "nan"/"null"/"none" (case-insensitive) -> ""
    - else -> stripped string
    """
    if x is None:
        return ""
    try:
        if isinstance(x, float) and math.isnan(x):
            return ""
    except Exception:
        pass

    s = str(x).strip()
    if not s:
        return ""
    if s.lower() in {"nan", "null", "none"}:
        return ""
    return s


def safe_float(x: Any, default: float = 1.0) -> float:
    try:
        if x is None:
            return default
        # handle NaN explicitly
        if isinstance(x, float) and math.isnan(x):
            return default
        v = float(x)
        if math.isnan(v):
            return default
        return v
    except Exception:
        return default


def safe_int(x: Any, default: int = 0) -> int:
    try:
        if x is None:
            return default
        if isinstance(x, float) and math.isnan(x):
            return default
        return int(float(x))
    except Exception:
        return default


def norm_text(s: str) -> str:
    s = safe_str(s).lower()
    s = re.sub(r"<[^>]+>", " ", s)          # strip HTML tags
    s = re.sub(r"\{\{c\d+::", " ", s)       # cloze marker start
    s = s.replace("}}", " ")
    s = re.sub(r"[^a-z0-9가-힣]+", " ", s)  # keep alnum + Korean
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_mix(s: str) -> Dict[str, float]:
    """
    Example: "MCQ_Vignette:0.5,Cloze_Finding:0.3,Image_Diagnosis:0.2"
    """
    out: Dict[str, float] = {}
    s = safe_str(s)
    if not s:
        return out
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            continue
        k, v = part.split(":", 1)
        k = k.strip()
        try:
            out[k] = float(v.strip())
        except Exception:
            continue

    # normalize to sum=1 if non-empty
    tot = sum(out.values())
    if tot > 0:
        for k in list(out.keys()):
            out[k] = out[k] / tot
    return out


# -------------------------
# Scoring / Dedup
# -------------------------
def compute_priority_score(row: pd.Series) -> float:
    """
    priority_score = 0.6 * weight_factor_norm + 0.4 * importance_norm
    - If weight_factor not present -> default 1.0
    - importance_score expected 0-100; if missing -> 50
    """
    wf = safe_float(row.get("weight_factor", 1.0), default=1.0)
    imp = safe_int(row.get("importance_score", 50), default=50)

    # weight_factor can be >1; compress using log to avoid dominance
    wf_norm = math.log1p(max(0.0, wf))  # 0..(slow growth)
    imp_norm = max(0.0, min(100.0, float(imp))) / 100.0  # 0..1

    return 0.6 * wf_norm + 0.4 * imp_norm


def make_topic_key(row: pd.Series) -> Tuple[str, str, str]:
    sp = safe_str(row.get("specialty", "")) or "UnknownSpecialty"
    an = safe_str(row.get("anatomy", "")) or "UnknownAnatomy"
    tp = safe_str(row.get("topic", "")) or "UnknownTopic"
    return (sp, an, tp)


def make_dedup_key(row: pd.Series) -> str:
    """
    Conservative dedup key:
    - entity_name
    - card_type
    - normalized "answer core" derived from back
    - normalized "stem core" derived from front (first ~120 chars)
    This will remove near-identical cards but keep conceptually distinct ones.
    """
    entity = norm_text(safe_str(row.get("entity_name", "")))
    ct = safe_str(row.get("card_type", ""))
    front = norm_text(safe_str(row.get("front", "")))[:120]
    back = norm_text(safe_str(row.get("back", "")))[:120]
    return f"{entity}|{ct}|{front}|{back}"


# -------------------------
# Selection Logic
# -------------------------
def select_cards(
    df: pd.DataFrame,
    target_total: int,
    min_per_topic: int,
    max_per_topic: int,
    dedup: bool,
    mix: Dict[str, float],
) -> pd.DataFrame:
    df = df.copy()

    # required columns (fill if missing)
    for c in ["specialty", "anatomy", "topic", "entity_name", "card_type", "front", "back"]:
        if c not in df.columns:
            df[c] = ""

    if "importance_score" not in df.columns:
        df["importance_score"] = 50
    if "weight_factor" not in df.columns:
        df["weight_factor"] = 1.0

    df["topic_key"] = df.apply(make_topic_key, axis=1)
    df["priority_score"] = df.apply(compute_priority_score, axis=1)
    df["dedup_key"] = df.apply(make_dedup_key, axis=1)

    # drop invalid
    df["front"] = df["front"].fillna("").astype(str)
    df["back"] = df["back"].fillna("").astype(str)
    df = df[(df["front"].str.strip() != "") & (df["back"].str.strip() != "")].reset_index(drop=True)

    # sort by score desc
    df = df.sort_values(["priority_score"], ascending=False).reset_index(drop=True)

    # target_total sanity
    if target_total <= 0:
        target_total = len(df)

    # card type quotas (soft)
    quotas: Dict[str, int] = {}
    if mix:
        for ct, frac in mix.items():
            quotas[ct] = max(0, int(round(target_total * frac)))

    # counts trackers
    selected_rows: List[int] = []
    used_dedup = set()
    topic_counts: Dict[Tuple[str, str, str], int] = {}
    ct_counts: Dict[str, int] = {}

    def can_take(i: int) -> bool:
        r = df.iloc[i]
        tk = r["topic_key"]
        ct = safe_str(r.get("card_type", ""))
        dk = r["dedup_key"]

        if dedup and dk in used_dedup:
            return False

        if topic_counts.get(tk, 0) >= max_per_topic:
            return False

        # if quotas exist, prefer not exceeding too much (soft constraint)
        if quotas:
            # allow exceeding by small slack; hard stop only if wildly beyond
            q = quotas.get(ct, 0)
            if q > 0 and ct_counts.get(ct, 0) >= q + max(2, int(0.05 * target_total)):
                return False

        return True

    def take(i: int) -> None:
        r = df.iloc[i]
        tk = r["topic_key"]
        ct = safe_str(r.get("card_type", ""))
        dk = r["dedup_key"]

        selected_rows.append(i)
        topic_counts[tk] = topic_counts.get(tk, 0) + 1
        ct_counts[ct] = ct_counts.get(ct, 0) + 1
        if dedup:
            used_dedup.add(dk)

    # --- Phase 1: coverage (min_per_topic) ---
    # group order: high-yield topics first (by best card score)
    best_by_topic = df.groupby("topic_key")["priority_score"].max().sort_values(ascending=False)
    for tk in best_by_topic.index:
        if len(selected_rows) >= target_total:
            break
        need = max(0, min_per_topic - topic_counts.get(tk, 0))
        if need <= 0:
            continue

        candidates = df.index[df["topic_key"] == tk].tolist()
        for i in candidates:
            if len(selected_rows) >= target_total or need <= 0:
                break
            if can_take(i):
                take(i)
                need -= 1

    # --- Phase 2: fill remaining by global priority ---
    if len(selected_rows) < target_total:
        for i in range(len(df)):
            if len(selected_rows) >= target_total:
                break
            if i in selected_rows:
                continue
            if can_take(i):
                take(i)

    out = df.iloc[selected_rows].copy().reset_index(drop=True)
    out["selected_rank"] = range(1, len(out) + 1)

    return out


# -------------------------
# Main
# -------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="MeducAI Step 03.5 - Select Anki deck candidates")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--run_tag", required=True)
    parser.add_argument("--arm", default="", help="Arm label (A-F). If set, uses __armX suffix for IO.")
    parser.add_argument("--base_dir", default=".")

    parser.add_argument("--target_total", type=int, default=0, help="0=keep all candidates after dedup/caps")
    parser.add_argument("--min_per_topic", type=int, default=1)
    parser.add_argument("--max_per_topic", type=int, default=3)

    parser.add_argument("--dedup", action="store_true", help="Enable dedup_key based near-duplicate removal")
    parser.add_argument(
        "--card_type_mix",
        default="",
        help='Optional, e.g. "MCQ_Vignette:0.5,Cloze_Finding:0.3,Image_Diagnosis:0.2"',
    )

    args = parser.parse_args()


    arm = (getattr(args, "arm", "") or "").strip()
    suffix = f"__arm{arm}" if arm else ""
    base_dir = Path(args.base_dir).resolve()

    # --------
    # Paths: generated/<run_tag>/ (canonical) with legacy fallback
    # --------
    fname_in = f"anki_cards_{args.provider}_{args.run_tag}{suffix}.csv"
    in_csv = resolve_in_run_or_legacy(base_dir, args.run_tag, args.provider, fname_in)
    if not in_csv.exists():
        raise FileNotFoundError(f"Input CSV not found (run_tag or legacy): {in_csv}")

    run_dir = generated_run_dir(base_dir, args.run_tag)
    out_csv = run_dir / f"anki_cards_selected_{args.provider}_{args.run_tag}{suffix}.csv"
    # ✅ 핵심 패치: 빈 칸을 NaN으로 올리지 않도록 안정적으로 로드
    df = pd.read_csv(in_csv, keep_default_na=False, na_filter=False)
    df.columns = df.columns.str.strip()

    mix = parse_mix(args.card_type_mix)

    selected = select_cards(
        df=df,
        target_total=args.target_total,
        min_per_topic=args.min_per_topic,
        max_per_topic=args.max_per_topic,
        dedup=args.dedup,
        mix=mix,
    )

    ensure_dir(out_csv.parent)
    selected.to_csv(out_csv, index=False, encoding="utf-8-sig")

    # Summary
    selected["topic_key"] = selected.apply(
        lambda r: (safe_str(r.get("specialty")), safe_str(r.get("anatomy")), safe_str(r.get("topic"))),
        axis=1,
    )
    n_topics = selected["topic_key"].nunique()
    print("✅ Step 03.5 selection completed.")
    print(f"  Input:   {in_csv}")
    print(f"  Output:  {out_csv}")
    print(f"  Selected cards: {len(selected)}")
    print(f"  Topics covered: {n_topics}")
    print(f"  min_per_topic={args.min_per_topic}, max_per_topic={args.max_per_topic}, dedup={args.dedup}")
    if mix:
        print(f"  card_type_mix={mix}")
        print("  card_type counts:")
        print(selected["card_type"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()

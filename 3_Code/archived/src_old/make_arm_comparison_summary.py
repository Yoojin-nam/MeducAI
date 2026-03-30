#!/usr/bin/env python3
import argparse
import json
import statistics
from pathlib import Path
import pandas as pd
from tabulate import tabulate

ARMS = list("ABCDEF")

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True)
    ap.add_argument("--run_tag_base", required=True)
    ap.add_argument("--base_dir", default=".")
    return ap.parse_args()

def load_latency_stats(path: Path):
    latencies = []
    if not path.exists(): return "N/A"
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                obj = json.loads(line)
                lat = obj.get("metadata", {}).get("latency_sec")
                if lat: latencies.append(float(lat))
        return round(statistics.mean(latencies), 2) if latencies else "N/A"
    except: return "Error"

def count_generated_images(csv_path: Path) -> str:
    """CSV를 읽어 이미지 생성 성공(경로 존재) 개수를 셉니다."""
    if not csv_path.exists():
        return "0/0"
    try:
        df = pd.read_csv(csv_path)
        # Nanobanana가 성공 시 'Local_File_Path'에 경로를 적는다고 가정
        col_check = "Local_File_Path" if "Local_File_Path" in df.columns else "image_path"
        
        if col_check not in df.columns:
            return f"?/{len(df)}"
        
        # 성공 = 해당 컬럼이 비어있지 않고 "FAILED"가 아님
        success = df[df[col_check].notna() & (df[col_check].astype(str).str.upper() != "FAILED") & (df[col_check].astype(str).strip() != "")].shape[0]
        total = len(df)
        return f"{success}/{total}"
    except:
        return "Err"

def main():
    args = parse_args()
    base_dir = Path(args.base_dir)
    meta_dir = base_dir / "2_Data" / "metadata" / "generated" / args.provider
    out_dir = base_dir / "7_QC_Validation" / "S0_QA" / args.run_tag_base
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for arm in ARMS:
        deck_path = meta_dir / f"deck_stats_{args.provider}_{args.run_tag_base}__arm{arm}.json"
        jsonl_path = meta_dir / f"output_{args.provider}_{args.run_tag_base}__arm{arm}.jsonl"
        
        # 이미지 CSV 찾기 (Step 02 산출물)
        anki_csv = next(meta_dir.glob(f"image_prompts_{args.provider}_{args.run_tag_base}__arm{arm}.csv"), Path("XXXX"))
        info_csv = next(meta_dir.glob(f"table_infographic_prompts_{args.provider}_{args.run_tag_base}__arm{arm}.csv"), Path("XXXX"))

        if not deck_path.exists(): continue

        with open(deck_path, "r") as f: d = json.load(f)
        latency = load_latency_stats(jsonl_path)
        
        # 이미지 카운트
        anki_img_stat = count_generated_images(anki_csv)
        info_img_stat = count_generated_images(info_csv)

        rows.append({
            "Arm": arm,
            "Latency(s)": latency,
            "Cards": d.get("n_rows", 0),
            "Grps": d.get("unique_groups", 0),
            "Images(Anki)": anki_img_stat,
            "Images(Info)": info_img_stat,
            "Err(F/B)": f"{d.get('empty_front',0)}/{d.get('empty_back',0)}",
            "Basic": d.get("card_type_counts", {}).get("Basic_QA", 0),
            "Cloze": d.get("card_type_counts", {}).get("Cloze_Finding", 0),
            "Vignette": d.get("card_type_counts", {}).get("MCQ_Vignette", 0)
        })

    if not rows:
        print("No data found.")
        return

    df = pd.DataFrame(rows)
    csv_path = out_dir / f"arm_comparison_summary_{args.provider}_{args.run_tag_base}.csv"
    md_path = out_dir / f"arm_comparison_summary_{args.provider}_{args.run_tag_base}.md"

    df.to_csv(csv_path, index=False)
    
    md = [f"# S0 QA Summary: {args.run_tag_base}", ""]
    md.append(tabulate(df, headers="keys", tablefmt="github", showindex=False))
    md.append("\n*Images(X): (Success / Total). Using 'Nanobanana' script.*")
    
    with open(md_path, "w") as f: f.write("\n".join(md))
    print(f"✅ Summary Updated: {md_path}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
make_arm_comparison_summary.py

Purpose (v2.0 aligned):
- Produce S0 arm-level summary tables for reporting (Paper-1).
- Merge (optional) S0 score sheet (resident/attending ratings) to compute:
  blocking error rate, editing time, clarity, relevance, etc.
- Summarize system metrics from jsonl (latency/tokens/cost/rag) when present.
- Summarize deck_stats and image generation success counts.

Inputs (expected in):
  <base_dir>/2_Data/metadata/generated/<provider>/
    - deck_stats_<provider>_<run_tag_base>__armA.json  ... armF.json
    - output_<provider>_<run_tag_base>__armA.jsonl     ... armF.jsonl
    - image_prompts_<provider>_<run_tag_base>__armA.csv (optional)
    - table_infographic_prompts_<provider>_<run_tag_base>__armA.csv (optional)

Outputs (v2.0):
  <base_dir>/2_Data/04_QA_Analysis/S0/<run_tag_base>/
    - arm_comparison_summary_<provider>_<run_tag_base>.csv
    - arm_comparison_summary_<provider>_<run_tag_base>.md

Optional:
  Provide --score_sheet_csv to merge S0 rubric metrics (blocking/editing/likert).
"""

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from tabulate import tabulate

ARMS = list("ABCDEF")


# -----------------------------
# Helpers
# -----------------------------
def _safe_mean(x):
    x = [v for v in x if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return None if not x else float(statistics.mean(x))


def _safe_stdev(x):
    x = [v for v in x if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if len(x) < 2:
        return None
    return float(statistics.stdev(x))


def _fmt_mean_sd(mean_v: Optional[float], sd_v: Optional[float], digits: int = 2) -> str:
    if mean_v is None:
        return "N/A"
    if sd_v is None:
        return f"{mean_v:.{digits}f}"
    return f"{mean_v:.{digits}f}±{sd_v:.{digits}f}"


def _fmt_num(v: Optional[float], digits: int = 2) -> str:
    if v is None:
        return "N/A"
    return f"{v:.{digits}f}"


def count_generated_images(csv_path: Path) -> str:
    """
    Reads an image prompt CSV and counts success/total.
    Assumes success when a path column is non-empty and not FAILED.
    """
    if not csv_path.exists():
        return "0/0"
    try:
        df = pd.read_csv(csv_path)
        # Most common columns seen in prior pipelines
        candidates = ["Local_File_Path", "local_file_path", "image_path", "output_path"]
        col = next((c for c in candidates if c in df.columns), None)
        if col is None:
            return f"?/{len(df)}"
        s = df[col].astype(str)
        ok = df[df[col].notna() & (s.str.strip() != "") & (s.str.upper() != "FAILED")].shape[0]
        return f"{ok}/{len(df)}"
    except Exception:
        return "Err"


def load_deck_stats(deck_path: Path) -> Optional[Dict[str, Any]]:
    if not deck_path.exists():
        return None
    try:
        return json.loads(deck_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def summarize_jsonl_metrics(jsonl_path: Path) -> Dict[str, Any]:
    """
    Parses output_*.jsonl and aggregates (if present):
      - latency_sec
      - input_tokens, output_tokens
      - cost_estimated_usd
      - rag_queries_count, rag_sources_count
    Also returns n_records.
    """
    out = {
        "n_records": 0,
        "latency_mean": None,
        "input_tokens_mean": None,
        "output_tokens_mean": None,
        "cost_mean": None,
        "rag_queries_mean": None,
        "rag_sources_mean": None,
    }
    if not jsonl_path.exists():
        return out

    lat, itok, otok, cost, rq, rs = [], [], [], [], [], []
    n = 0
    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                n += 1
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                md = obj.get("metadata", {}) if isinstance(obj, dict) else {}
                # latency
                v = md.get("latency_sec")
                if v is not None:
                    try:
                        lat.append(float(v))
                    except Exception:
                        pass
                # tokens
                for key, arr in [("input_tokens", itok), ("output_tokens", otok)]:
                    v = md.get(key)
                    if v is not None:
                        try:
                            arr.append(float(v))
                        except Exception:
                            pass
                # cost
                v = md.get("cost_estimated_usd")
                if v is not None:
                    try:
                        cost.append(float(v))
                    except Exception:
                        pass
                # rag counts
                for key, arr in [("rag_queries_count", rq), ("rag_sources_count", rs)]:
                    v = md.get(key)
                    if v is not None:
                        try:
                            arr.append(float(v))
                        except Exception:
                            pass

        out["n_records"] = n
        out["latency_mean"] = _safe_mean(lat)
        out["input_tokens_mean"] = _safe_mean(itok)
        out["output_tokens_mean"] = _safe_mean(otok)
        out["cost_mean"] = _safe_mean(cost)
        out["rag_queries_mean"] = _safe_mean(rq)
        out["rag_sources_mean"] = _safe_mean(rs)
        return out
    except Exception:
        return out


def summarize_score_sheet(score_csv: Path) -> pd.DataFrame:
    """
    Reads S0 score sheet (long format: set × rater rows) and aggregates by arm.
    Required columns (any of these pairs are acceptable):
      - arm_id OR Arm
      - accuracy_score OR blocking_flag
      - editing_time_min (optional but recommended)
      - clarity_likert_1_5 (optional)
      - relevance_likert_1_5 (optional)

    Returns a df with one row per arm and columns:
      - Arm
      - QA_N_rows
      - QA_N_sets
      - BlockingRate
      - EditingTime(mean±sd)
      - Clarity(mean±sd)
      - Relevance(mean±sd)
    """
    df = pd.read_csv(score_csv)
    # normalize arm column
    arm_col = "arm_id" if "arm_id" in df.columns else ("Arm" if "Arm" in df.columns else None)
    if arm_col is None:
        raise ValueError("Score sheet missing 'arm_id' or 'Arm' column.")

    df["Arm"] = df[arm_col].astype(str).str.replace("arm", "", case=False).str.strip().str.upper()

    # blocking flag
    if "blocking_flag" in df.columns:
        df["_blocking"] = pd.to_numeric(df["blocking_flag"], errors="coerce")
    elif "accuracy_score" in df.columns:
        acc = pd.to_numeric(df["accuracy_score"], errors="coerce")
        df["_blocking"] = (acc == 0).astype(float)
    else:
        raise ValueError("Score sheet missing 'blocking_flag' or 'accuracy_score'.")

    # set id for n_sets
    if "set_id" in df.columns:
        df["_set_id"] = df["set_id"].astype(str)
    else:
        # fallback: if no set_id, treat each row as a unique unit (less ideal)
        df["_set_id"] = df.index.astype(str)

    # numeric fields
    for col in ["editing_time_min", "clarity_likert_1_5", "relevance_likert_1_5"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    rows = []
    for arm in ARMS:
        sub = df[df["Arm"] == arm].copy()
        if sub.empty:
            continue

        blocking_rate = _safe_mean(sub["_blocking"].tolist())

        # editing time
        et = sub["editing_time_min"].tolist() if "editing_time_min" in sub.columns else []
        et_mean, et_sd = _safe_mean(et), _safe_stdev(et)

        # clarity
        cl = sub["clarity_likert_1_5"].tolist() if "clarity_likert_1_5" in sub.columns else []
        cl_mean, cl_sd = _safe_mean(cl), _safe_stdev(cl)

        # relevance
        rv = sub["relevance_likert_1_5"].tolist() if "relevance_likert_1_5" in sub.columns else []
        rv_mean, rv_sd = _safe_mean(rv), _safe_stdev(rv)

        rows.append({
            "Arm": arm,
            "QA_N_rows": int(len(sub)),
            "QA_N_sets": int(sub["_set_id"].nunique()),
            "BlockingRate": blocking_rate,
            "EditingTime_mean_sd": _fmt_mean_sd(et_mean, et_sd, digits=2),
            "Clarity_mean_sd": _fmt_mean_sd(cl_mean, cl_sd, digits=2),
            "Relevance_mean_sd": _fmt_mean_sd(rv_mean, rv_sd, digits=2),
        })

    out = pd.DataFrame(rows)
    return out


# -----------------------------
# CLI
# -----------------------------
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True, help="e.g., gemini / openai")
    ap.add_argument("--run_tag_base", required=True, help="e.g., S0_QA_Nano_20251214_0943_SAMPLE5")
    ap.add_argument("--base_dir", default=".", help="Project root (MeducAI)")
    ap.add_argument(
        "--score_sheet_csv",
        default=None,
        help="Optional: path to S0 score sheet CSV (raw or post-unblinding). If provided, merges QA rubric metrics.",
    )
    ap.add_argument(
        "--out_subdir",
        default=None,
        help="Optional: override output subdir under 2_Data/04_QA_Analysis/S0/. Default=<run_tag_base>.",
    )
    return ap.parse_args()


def main():
    args = parse_args()
    base_dir = Path(args.base_dir)

    # Inputs (generation metadata)
    meta_dir = base_dir / "2_Data" / "metadata" / "generated" / args.provider

    # Outputs (v2.0 aligned)
    out_subdir = args.out_subdir or args.run_tag_base
    out_dir = base_dir / "2_Data" / "04_QA_Analysis" / "S0" / out_subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for arm in ARMS:
        deck_path = meta_dir / f"deck_stats_{args.provider}_{args.run_tag_base}__arm{arm}.json"
        jsonl_path = meta_dir / f"output_{args.provider}_{args.run_tag_base}__arm{arm}.jsonl"

        # image CSVs (optional)
        anki_csv = meta_dir / f"image_prompts_{args.provider}_{args.run_tag_base}__arm{arm}.csv"
        info_csv = meta_dir / f"table_infographic_prompts_{args.provider}_{args.run_tag_base}__arm{arm}.csv"

        deck = load_deck_stats(deck_path)
        if deck is None:
            continue

        sysm = summarize_jsonl_metrics(jsonl_path)

        anki_img_stat = count_generated_images(anki_csv)
        info_img_stat = count_generated_images(info_csv)

        rows.append({
            "Arm": arm,

            # System metrics (secondary)
            "Latency_mean_s": _fmt_num(sysm.get("latency_mean"), 2),
            "InputTokens_mean": _fmt_num(sysm.get("input_tokens_mean"), 0) if sysm.get("input_tokens_mean") is not None else "N/A",
            "OutputTokens_mean": _fmt_num(sysm.get("output_tokens_mean"), 0) if sysm.get("output_tokens_mean") is not None else "N/A",
            "Cost_mean_usd": _fmt_num(sysm.get("cost_mean"), 4),
            "RAG_queries_mean": _fmt_num(sysm.get("rag_queries_mean"), 2),
            "RAG_sources_mean": _fmt_num(sysm.get("rag_sources_mean"), 2),
            "JSONL_records": int(sysm.get("n_records", 0)),

            # Deck stats (sanity)
            "Cards": int(deck.get("n_rows", 0)),
            "Groups": int(deck.get("unique_groups", 0)),
            "Err_empty_F_B": f"{int(deck.get('empty_front', 0))}/{int(deck.get('empty_back', 0))}",

            # Card type mix (names depend on your deck_stats schema; keep legacy keys)
            "Basic": int(deck.get("card_type_counts", {}).get("Basic_QA", 0)),
            "Cloze": int(deck.get("card_type_counts", {}).get("Cloze_Finding", 0)),
            "Vignette": int(deck.get("card_type_counts", {}).get("MCQ_Vignette", 0)),

            # Image success ratio
            "Images_Anki": anki_img_stat,
            "Images_Info": info_img_stat,
        })

    if not rows:
        print("No data found. Check provider/run_tag_base/meta_dir:")
        print(f"  meta_dir = {meta_dir}")
        return

    df = pd.DataFrame(rows).sort_values("Arm")

    # Optional merge: S0 score sheet QA metrics (v2.0 reporting)
    merged_note = ""
    if args.score_sheet_csv:
        score_path = Path(args.score_sheet_csv)
        if not score_path.exists():
            raise FileNotFoundError(f"--score_sheet_csv not found: {score_path}")
        qa_df = summarize_score_sheet(score_path).sort_values("Arm")

        # Merge on Arm
        df = df.merge(qa_df, on="Arm", how="left")

        # Friendly formatting for BlockingRate
        if "BlockingRate" in df.columns:
            df["BlockingRate"] = df["BlockingRate"].apply(lambda x: "N/A" if pd.isna(x) else f"{float(x)*100:.2f}%")

        merged_note = f"\n- Merged score sheet: {score_path.as_posix()}"

    # Write outputs
    csv_path = out_dir / f"arm_comparison_summary_{args.provider}_{args.run_tag_base}.csv"
    md_path = out_dir / f"arm_comparison_summary_{args.provider}_{args.run_tag_base}.md"

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    md = [
        f"# S0 Arm Comparison Summary (v2.0 aligned)",
        f"- provider: `{args.provider}`",
        f"- run_tag_base: `{args.run_tag_base}`",
        f"- output_dir: `{out_dir.as_posix()}`",
    ]
    if merged_note:
        md.append(merged_note.strip())

    md.append("")
    md.append(tabulate(df, headers="keys", tablefmt="github", showindex=False))
    md.append("")
    md.append("*Images_* columns are shown as (Success/Total) based on presence of saved file paths in the prompt CSVs.")
    md.append("*BlockingRate is derived from score_sheet (Accuracy==0 or blocking_flag==1).")
    md.append("")

    md_path.write_text("\n".join(md), encoding="utf-8")
    print(f"✅ Summary CSV: {csv_path}")
    print(f"✅ Summary MD : {md_path}")


if __name__ == "__main__":
    main()

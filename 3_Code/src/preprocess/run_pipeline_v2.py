#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
One-command v2 pipeline runner.

Produces versioned outputs (suffix-based), matching the notebook pipeline:
PDF -> Raw -> Enrich -> Translate -> Tag -> WeightFactor -> groups_canonical
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd


def _run(cmd: List[str]) -> None:
    print("RUN:", " ".join(cmd))
    subprocess.check_call(cmd)


def _audit_diff_v1_v2(v1_xlsx: Path, v2_xlsx: Path, out_md: Path) -> None:
    df1 = pd.read_excel(v1_xlsx)
    df2 = pd.read_excel(v2_xlsx)
    obj1 = set(df1["Objective"].astype(str).str.strip().tolist())
    obj2 = set(df2["Objective"].astype(str).str.strip().tolist())

    added = sorted([x for x in obj2 - obj1 if x])
    removed = sorted([x for x in obj1 - obj2 if x])

    lines: List[str] = []
    lines.append("# Curriculum v2 rebuild audit")
    lines.append("")
    lines.append(f"- v1 rows: **{len(df1)}**")
    lines.append(f"- v2 rows: **{len(df2)}**")
    lines.append(f"- added objectives (v2 - v1): **{len(added)}**")
    lines.append(f"- removed objectives (v1 - v2): **{len(removed)}**")
    lines.append("")

    lines.append("## Added objectives (sample)")
    lines.append("")
    for x in added[:100]:
        lines.append(f"- {x}")
    if len(added) > 100:
        lines.append(f"- ... and {len(added) - 100} more")
    lines.append("")

    lines.append("## Removed objectives (sample)")
    lines.append("")
    for x in removed[:100]:
        lines.append(f"- {x}")
    if len(removed) > 100:
        lines.append(f"- ... and {len(removed) - 100} more")
    lines.append("")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v2 preprocessing pipeline end-to-end.")
    ap.add_argument("--pdf", required=True, help="Input PDF path")
    ap.add_argument("--out_suffix", default="_v2", help="Suffix for outputs (default: _v2)")
    ap.add_argument("--model", default="gemini-3-flash-preview", help="Gemini model id")
    ap.add_argument("--repo_root", default=".", help="Repo root")
    ap.add_argument(
        "--normalize",
        default="1",
        help="Normalize Objective text before enrich/translate (default: 1). Set 0 to disable.",
    )
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    pdf = Path(args.pdf).resolve()
    suffix = args.out_suffix
    run_id = f"pipelinev2_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    logs_dir = repo_root / "2_Data" / "processed" / "logs"
    log_jsonl = logs_dir / f"{run_id}.jsonl"
    prompts_txt = logs_dir / f"{run_id}.system_prompts.txt"

    raw_v1 = repo_root / "2_Data/raw/Radiology_Curriculum.xlsx"
    raw_v2 = repo_root / f"2_Data/raw/Radiology_Curriculum{suffix}.xlsx"
    raw_v2_norm = repo_root / f"2_Data/raw/Radiology_Curriculum{suffix}_norm.xlsx"

    enriched_v2 = repo_root / f"2_Data/processed/Radiology_Curriculum_Enriched{suffix}.xlsx"
    enriched_v2_norm = repo_root / f"2_Data/processed/Radiology_Curriculum_Enriched{suffix}_norm.xlsx"
    translated_v2 = repo_root / f"2_Data/processed/Radiology_Curriculum_Translated_DB{suffix}.xlsx"
    tagged_v2 = repo_root / f"2_Data/processed/Radiology_Curriculum_Tagged{suffix}.xlsx"
    weight_v2 = repo_root / f"2_Data/processed/Radiology_Curriculum_Weight_Factor{suffix}.xlsx"

    suspicious_json = repo_root / f"2_Data/processed/audit_curriculum_parse{suffix}.suspicious.json"
    parse_audit_md = repo_root / f"2_Data/processed/audit_curriculum_parse{suffix}.md"
    diff_audit_md = repo_root / f"2_Data/processed/audit_curriculum_diff_v1_vs{suffix}.md"

    map_json = repo_root / f"2_Data/metadata/translation_map{suffix}.json"

    # 1) Parse PDF -> raw_v2 + audit artifacts
    _run(
        [
            "python3",
            str(repo_root / "3_Code/src/preprocess/parse_curriculum_pdf_v2.py"),
            "--pdf",
            str(pdf),
            "--out_xlsx",
            str(raw_v2),
            "--out_audit_md",
            str(parse_audit_md),
            "--out_suspicious_json",
            str(suspicious_json),
        ]
    )

    # 1.5) Normalize Objective text (no LLM)
    if str(args.normalize).strip() != "0":
        _run(
            [
                "python3",
                str(repo_root / "3_Code/src/preprocess/normalize_curriculum_text_v2.py"),
                "--in_xlsx",
                str(raw_v2),
                "--out_xlsx",
                str(raw_v2_norm),
                "--cols",
                "Objective",
            ]
        )
        enrich_input = raw_v2_norm
    else:
        enrich_input = raw_v2

    # 2) Enrich
    _run(
        [
            "python3",
            str(repo_root / "3_Code/src/preprocess/enrich_v2.py"),
            "--in_xlsx",
            str(enrich_input),
            "--out_xlsx",
            str(enriched_v2),
            "--model",
            args.model,
            "--run_id",
            run_id,
            "--log_jsonl",
            str(log_jsonl),
            "--prompts_txt",
            str(prompts_txt),
            "--repo_root",
            str(repo_root),
        ]
    )

    # 2.5) Normalize Objective text again at Enriched stage (safety; Objective should be identical)
    if str(args.normalize).strip() != "0":
        _run(
            [
                "python3",
                str(repo_root / "3_Code/src/preprocess/normalize_curriculum_text_v2.py"),
                "--in_xlsx",
                str(enriched_v2),
                "--out_xlsx",
                str(enriched_v2_norm),
                "--cols",
                "Objective",
            ]
        )
        translate_input = enriched_v2_norm
    else:
        translate_input = enriched_v2

    # 3) Translate
    _run(
        [
            "python3",
            str(repo_root / "3_Code/src/preprocess/translate_v2.py"),
            "--in_xlsx",
            str(translate_input),
            "--out_xlsx",
            str(translated_v2),
            "--out_map_json",
            str(map_json),
            "--model",
            args.model,
            "--run_id",
            run_id,
            "--log_jsonl",
            str(log_jsonl),
            "--prompts_txt",
            str(prompts_txt),
            "--repo_root",
            str(repo_root),
        ]
    )

    # 4) Tag
    _run(
        [
            "python3",
            str(repo_root / "3_Code/src/preprocess/tag_v2.py"),
            "--in_xlsx",
            str(translated_v2),
            "--out_xlsx",
            str(tagged_v2),
            "--repo_root",
            str(repo_root),
        ]
    )

    # 5) Weight factor
    _run(
        [
            "python3",
            str(repo_root / "3_Code/src/preprocess/merge_weights_v2.py"),
            "--in_xlsx",
            str(tagged_v2),
            "--out_xlsx",
            str(weight_v2),
        ]
    )

    # 6) Diff audit (v1 raw vs v2 raw)
    if raw_v1.exists():
        _audit_diff_v1_v2(raw_v1, raw_v2, diff_audit_md)

    print("OK: pipeline v2 complete")
    print(f"- raw_v2: {raw_v2}")
    print(f"- weight_v2: {weight_v2}")
    print(f"- parse_audit: {parse_audit_md}")
    print(f"- diff_audit: {diff_audit_md}")
    print(f"- mi_clear_log_jsonl: {log_jsonl}")
    print(f"- mi_clear_prompts_txt: {prompts_txt}")


if __name__ == "__main__":
    main()



#!/usr/bin/env python3
"""
MeducAI QA Distribution Builder

Goal:
- Build a distribution-ready set per arm:
  (1) entity images (+ manifest)
  (2) table infographic images (1 per record)
  (3) Anki .apkg with embedded images

Key design:
- A single RUN_TAG_BASE is expanded into per-arm run_tag = f"{RUN_TAG_BASE}__armX"
- Idempotent: supports --resume and will skip steps if outputs exist (unless --force)
- Reproducible: writes a run report JSONL + summary MD under 6_Distributions

Typical usage:
  python3 3_Code/src/05_build_qa_distribution.py \
    --base_dir . \
    --run_tag_base S0_QA_DIST_20251215_073000 \
    --arms A B C D E F \
    --image_provider gemini \
    --export_provider_mode per_arm \
    --resume

Notes on Arm F:
- If Arm F provider is "gpt" but you want to generate images with "gemini",
  this runner will copy ONLY the entity manifest into the gpt folder so that
  04_export_anki.py can find it while still referencing the actual image paths.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# -------------------------
# Configuration
# -------------------------

@dataclass(frozen=True)
class ArmConfig:
    arm: str
    provider: str  # provider used for Step01/02 outputs (and usually export)


DEFAULT_ARM_PROVIDERS: Dict[str, str] = {
    "A": "gemini",
    "B": "gemini",
    "C": "gemini",
    "D": "gemini",
    "E": "gemini",
    "F": "gpt",   # typical setup from your S0 design
}


# -------------------------
# Helpers
# -------------------------

def now_ts() -> int:
    return int(time.time())

def run_cmd(cmd: List[str], cwd: Optional[Path] = None) -> None:
    """Run a command with streaming stdout/stderr. Raises on non-zero exit."""
    print("\n[RUN]", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def write_jsonl(path: Path, obj: dict) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def file_exists(p: Path) -> bool:
    return p.exists() and p.is_file() and p.stat().st_size > 0

def guess_csv_paths(base_dir: Path, provider: str, run_tag_base: str, arm: str) -> Tuple[Path, Path, Path]:
    """
    Step02 outputs are arm-suffixed, e.g.
      2_Data/metadata/generated/<run_tag_base>/
        image_prompts_<provider>_<run_tag_base>__armA.csv
        table_infographic_prompts_<provider>_<run_tag_base>__armA.csv
        anki_cards_selected_<provider>_<run_tag_base>__armA.csv
    """
    out_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag_base
    arm_suffix = f"__arm{arm}"
    image_prompts = out_dir / f"image_prompts_{provider}_{run_tag_base}{arm_suffix}.csv"
    table_prompts = out_dir / f"table_infographic_prompts_{provider}_{run_tag_base}{arm_suffix}.csv"
    selected_cards = out_dir / f"anki_cards_selected_{provider}_{run_tag_base}{arm_suffix}.csv"
    return image_prompts, table_prompts, selected_cards

def manifest_path(base_dir: Path, provider: str, run_tag: str, kind: str) -> Path:
    """
    03_generate_images.py convention:
      2_Data/images/generated/<provider>/<run_tag>/<kind>/manifest_<provider>_<run_tag>_<kind>.jsonl
    kind: "entity" or "table"
    """
    root = base_dir / "2_Data" / "images" / "generated" / provider / run_tag / kind
    return root / f"manifest_{provider}_{run_tag}_{kind}.jsonl"

def distribution_root(base_dir: Path, run_tag_base: str) -> Path:
    return base_dir / "6_Distributions" / "S0_QA" / run_tag_base

def anki_out_dir(base_dir: Path, run_tag_base: str) -> Path:
    return distribution_root(base_dir, run_tag_base) / "anki"

def run_report_jsonl(base_dir: Path, run_tag_base: str) -> Path:
    return distribution_root(base_dir, run_tag_base) / "run_report.jsonl"

def summary_md_path(base_dir: Path, run_tag_base: str) -> Path:
    return distribution_root(base_dir, run_tag_base) / "SUMMARY.md"


# -------------------------
# Pipeline steps
# -------------------------

def step03_generate_entity_images(
    base_dir: Path,
    image_provider: str,
    run_tag: str,
    image_prompts_csv: Path,
    aspect_ratio: str,
    image_size: str,
    include_opt: bool,
    resume: bool,
) -> None:
    cmd = [
        sys.executable, "3_Code/src/03_generate_images.py",
        "--base_dir", str(base_dir),
        "--provider", image_provider,
        "--run_tag", run_tag,
        "--input_csv", str(image_prompts_csv),
        "--aspect_ratio", aspect_ratio,
        "--image_size", image_size,
    ]
    if include_opt:
        cmd.append("--include_opt")
    if resume:
        cmd.append("--resume")
    run_cmd(cmd, cwd=base_dir)

def step03_generate_table_images(
    base_dir: Path,
    image_provider: str,
    run_tag: str,
    table_prompts_csv: Path,
    aspect_ratio: str,
    image_size: str,
    table_one_per_record: bool,
    resume: bool,
) -> None:
    cmd = [
        sys.executable, "3_Code/src/03_generate_images.py",
        "--base_dir", str(base_dir),
        "--provider", image_provider,
        "--run_tag", run_tag,
        "--input_csv", str(table_prompts_csv),
        "--aspect_ratio", aspect_ratio,
        "--image_size", image_size,
    ]
    if table_one_per_record:
        cmd.append("--table_one_per_record")
    if resume:
        cmd.append("--resume")
    run_cmd(cmd, cwd=base_dir)

def step04_export_anki(
    base_dir: Path,
    export_provider: str,
    run_tag: str,
    selected_cards_csv: Path,
    out_dir: Path,
    attach_images: bool,
    attach_default_to: str,
) -> None:
    cmd = [
        sys.executable, "3_Code/src/04_export_anki.py",
        "--base_dir", str(base_dir),
        "--provider", export_provider,
        "--run_tag", run_tag,
        "--input_csv", str(selected_cards_csv),
        "--out_dir", str(out_dir),
    ]
    if attach_images:
        cmd.append("--attach_images")
        cmd += ["--attach_default_to", attach_default_to]
    run_cmd(cmd, cwd=base_dir)

def mirror_entity_manifest_for_export_provider(
    base_dir: Path,
    image_provider: str,
    export_provider: str,
    run_tag: str,
) -> Path:
    """
    If export_provider != image_provider, 04_export_anki.py will look for manifest under export_provider/run_tag/entity.
    We copy the entity manifest there WITHOUT rewriting output_path, so it still points to the real image files.
    """
    src = manifest_path(base_dir, image_provider, run_tag, "entity")
    if not file_exists(src):
        raise FileNotFoundError(f"Entity manifest not found at: {src}")
    dst = manifest_path(base_dir, export_provider, run_tag, "entity")
    ensure_dir(dst.parent)
    shutil.copy2(src, dst)
    return dst


# -------------------------
# Main
# -------------------------

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base_dir", default=".", type=str)
    p.add_argument("--run_tag_base", required=True, type=str)

    p.add_argument("--arms", nargs="+", default=list(DEFAULT_ARM_PROVIDERS.keys()))
    p.add_argument("--image_provider", default="gemini", type=str)

    # Export provider policy:
    # - per_arm: use DEFAULT_ARM_PROVIDERS[arm] (i.e., your Step01/02 provider)
    # - image_provider: export with image_provider for all arms (simplifies attachment, deck naming becomes image_provider)
    p.add_argument("--export_provider_mode", choices=["per_arm", "image_provider"], default="per_arm")

    # Entity image profile (Anki attachment)
    p.add_argument("--entity_aspect_ratio", default="4:5")
    p.add_argument("--entity_image_size", default="1K")
    p.add_argument("--include_opt", action="store_true", help="Also generate IMG_OPT entities")

    # Table image profile (infographic)
    p.add_argument("--table_aspect_ratio", default="16:9")
    p.add_argument("--table_image_size", default="4K")
    p.add_argument("--table_one_per_record", action="store_true", default=True)

    p.add_argument("--resume", action="store_true")
    p.add_argument("--force", action="store_true")

    # Anki attachment policy
    p.add_argument("--attach_images", action="store_true", default=True)
    p.add_argument("--attach_default_to", choices=["front", "back"], default="back")

    args = p.parse_args()

    base_dir = Path(args.base_dir).resolve()
    run_tag_base = args.run_tag_base

    dist_root = distribution_root(base_dir, run_tag_base)
    ensure_dir(dist_root)
    ensure_dir(anki_out_dir(base_dir, run_tag_base))

    # Resolve arms
    arms: List[str] = [a.upper() for a in args.arms]
    for a in arms:
        if a not in DEFAULT_ARM_PROVIDERS:
            raise ValueError(f"Unknown arm: {a}. Known: {sorted(DEFAULT_ARM_PROVIDERS.keys())}")

    write_jsonl(run_report_jsonl(base_dir, run_tag_base), {
        "ts": now_ts(),
        "event": "START",
        "run_tag_base": run_tag_base,
        "arms": arms,
        "image_provider": args.image_provider,
        "export_provider_mode": args.export_provider_mode,
    })

    results: List[dict] = []

    for arm in arms:
        arm_provider = DEFAULT_ARM_PROVIDERS[arm]
        run_tag = f"{run_tag_base}__arm{arm}"
        export_provider = arm_provider if args.export_provider_mode == "per_arm" else args.image_provider
        image_provider = args.image_provider

        rec = {
            "ts": now_ts(),
            "arm": arm,
            "run_tag": run_tag,
            "arm_provider": arm_provider,
            "image_provider": image_provider,
            "export_provider": export_provider,
            "status": "init",
        }

        try:
            image_prompts_csv, table_prompts_csv, selected_cards_csv = guess_csv_paths(
                base_dir=base_dir,
                provider=arm_provider,
                run_tag_base=run_tag_base,
                arm=arm,
            )

            # Validate inputs exist
            missing_inputs = [str(p) for p in [image_prompts_csv, table_prompts_csv, selected_cards_csv] if not p.exists()]
            if missing_inputs:
                raise FileNotFoundError(f"Missing input CSV(s): {missing_inputs}")

            # Step 03-A: entity images
            entity_manifest = manifest_path(base_dir, image_provider, run_tag, "entity")
            if args.force or not file_exists(entity_manifest):
                step03_generate_entity_images(
                    base_dir=base_dir,
                    image_provider=image_provider,
                    run_tag=run_tag,
                    image_prompts_csv=image_prompts_csv,
                    aspect_ratio=args.entity_aspect_ratio,
                    image_size=args.entity_image_size,
                    include_opt=args.include_opt,
                    resume=args.resume,
                )

            # Step 03-B: table infographic images
            table_manifest = manifest_path(base_dir, image_provider, run_tag, "table")
            if args.force or not file_exists(table_manifest):
                step03_generate_table_images(
                    base_dir=base_dir,
                    image_provider=image_provider,
                    run_tag=run_tag,
                    table_prompts_csv=table_prompts_csv,
                    aspect_ratio=args.table_aspect_ratio,
                    image_size=args.table_image_size,
                    table_one_per_record=args.table_one_per_record,
                    resume=args.resume,
                )

            # If export_provider differs, mirror entity manifest so export can find it
            mirrored_manifest = None
            if args.attach_images and export_provider != image_provider:
                mirrored_manifest = mirror_entity_manifest_for_export_provider(
                    base_dir=base_dir,
                    image_provider=image_provider,
                    export_provider=export_provider,
                    run_tag=run_tag,
                )

            # Step 04: export Anki
            # We cannot easily know exact output filename without parsing 04_export_anki logic,
            # so we validate that *some* apkg is created/updated under the out_dir after export.
            out_dir = anki_out_dir(base_dir, run_tag_base)
            before = {p.name for p in out_dir.glob("*.apkg")}

            step04_export_anki(
                base_dir=base_dir,
                export_provider=export_provider,
                run_tag=run_tag,
                selected_cards_csv=selected_cards_csv,
                out_dir=out_dir,
                attach_images=args.attach_images,
                attach_default_to=args.attach_default_to,
            )

            after = {p.name for p in out_dir.glob("*.apkg")}
            created = sorted(list(after - before))

            rec.update({
                "status": "ok",
                "inputs": {
                    "image_prompts_csv": str(image_prompts_csv),
                    "table_prompts_csv": str(table_prompts_csv),
                    "selected_cards_csv": str(selected_cards_csv),
                },
                "manifests": {
                    "entity_manifest": str(entity_manifest),
                    "table_manifest": str(table_manifest),
                    "mirrored_entity_manifest": str(mirrored_manifest) if mirrored_manifest else None,
                },
                "anki_out_dir": str(out_dir),
                "anki_created": created,
            })

        except Exception as e:
            rec.update({"status": "error", "error": repr(e)})

        results.append(rec)
        write_jsonl(run_report_jsonl(base_dir, run_tag_base), rec)

        # fail-fast on error
        if rec["status"] != "ok":
            print("\n[ERROR]", rec["error"])
            print("Arm failed:", arm)
            sys.exit(1)

    # Write SUMMARY.md
    lines = []
    lines.append(f"# QA Distribution Summary\n")
    lines.append(f"- run_tag_base: `{run_tag_base}`\n")
    lines.append(f"- image_provider: `{args.image_provider}`\n")
    lines.append(f"- export_provider_mode: `{args.export_provider_mode}`\n")
    lines.append(f"- arms: {', '.join(arms)}\n")
    lines.append("\n## Outputs\n")
    lines.append(f"- Anki out dir: `{anki_out_dir(base_dir, run_tag_base)}`\n")
    lines.append(f"- Run report: `{run_report_jsonl(base_dir, run_tag_base)}`\n")

    lines.append("\n## Per-arm status\n")
    for r in results:
        lines.append(f"- Arm {r['arm']}: {r['status']} | run_tag={r['run_tag']} | export_provider={r['export_provider']} | image_provider={r['image_provider']}\n")
        if r["status"] == "ok":
            created = r.get("anki_created") or []
            if created:
                lines.append(f"  - apkg created: {', '.join(created)}\n")

    summary_path = summary_md_path(base_dir, run_tag_base)
    ensure_dir(summary_path.parent)
    summary_path.write_text("".join(lines), encoding="utf-8")

    write_jsonl(run_report_jsonl(base_dir, run_tag_base), {
        "ts": now_ts(),
        "event": "DONE",
        "run_tag_base": run_tag_base,
        "status": "ok",
        "summary_md": str(summary_path),
    })

    print("\n[DONE] Distribution build completed.")
    print("Summary:", summary_path)


if __name__ == "__main__":
    main()

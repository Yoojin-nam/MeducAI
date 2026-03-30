#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PPTX Embedded Image Audit (offline)
----------------------------------

Goal:
- Extract original embedded images from .pptx (zip: ppt/media/*)
- Compute lightweight image statistics (luminance / chroma)
- Produce a small offline report (JSONL/CSV + Markdown + contact sheets)

This is intended to support REALISTIC guardrail tuning by grounding
"typical windowing / contrast / texture" in real exam slide assets.

No network access; no extra dependencies beyond repo runtime:
- numpy, Pillow, tqdm
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image
from tqdm import tqdm


# PIL safety: keep default behavior, but be explicit about intent.
# (If any image triggers DecompressionBombError, we record an error row and continue.)

ALLOWED_IMAGE_EXTS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
    ".webp",
}


def _now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _resolve_under(base_dir: Path, p: Path) -> Path:
    return p if p.is_absolute() else (base_dir / p)


def _sanitize_stem_for_dir(name: str) -> str:
    # Allow ASCII + Hangul, keep file-system safe and stable.
    cleaned = re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", name).strip("_")
    return cleaned or "pptx"


def _sha1_bytes(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def _iter_pptx_media_members(zf: zipfile.ZipFile) -> Iterable[zipfile.ZipInfo]:
    for info in zf.infolist():
        if info.is_dir():
            continue
        # Embedded media are typically stored here.
        if not info.filename.startswith("ppt/media/"):
            continue
        yield info


def _guess_ext_from_name(name: str) -> str:
    return Path(name).suffix.lower()


def _classify_color_from_rgb(rgb: Image.Image, threshold: float = 0.15) -> Tuple[str, float]:
    """
    Lightweight chroma score classifier (same idea as tools/optimize_images.py):
    score = mean(abs(R-G) + abs(G-B) + abs(B-R)) / 255
    """
    img = rgb
    if img.mode != "RGB":
        img = img.convert("RGB")

    w, h = img.size
    max_dim = max(w, h)
    if max_dim > 256:
        scale = 256.0 / max_dim
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)

    arr = np.array(img, dtype=np.float32)
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    chroma_diff = np.abs(r - g) + np.abs(g - b) + np.abs(b - r)
    score = float(np.mean(chroma_diff) / 255.0)
    cls = "COLOR" if score > threshold else "GRAY"
    return cls, score


def _compute_luminance_stats(img: Image.Image, max_dim_for_stats: int = 1024) -> Dict[str, float]:
    """
    Compute robust luminance stats from an image.
    - Convert to 8-bit grayscale
    - Optionally downsample for speed
    """
    g = img.convert("L")
    w, h = g.size
    max_dim = max(w, h)
    if max_dim > max_dim_for_stats:
        scale = max_dim_for_stats / float(max_dim)
        g = g.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.BILINEAR)

    arr = np.array(g, dtype=np.uint8).reshape(-1)
    if arr.size == 0:
        return {
            "lum_mean": 0.0,
            "lum_std": 0.0,
            "lum_min": 0.0,
            "lum_max": 0.0,
            "lum_p01": 0.0,
            "lum_p05": 0.0,
            "lum_p50": 0.0,
            "lum_p95": 0.0,
            "lum_p99": 0.0,
            "lum_p95_minus_p05": 0.0,
            "lum_frac_lt10": 0.0,
            "lum_frac_gt245": 0.0,
        }

    p01, p05, p50, p95, p99 = np.percentile(arr, [1, 5, 50, 95, 99]).tolist()
    mean = float(arr.mean())
    std = float(arr.std())
    mn = float(arr.min())
    mx = float(arr.max())
    frac_lt10 = float(np.mean(arr < 10))
    frac_gt245 = float(np.mean(arr > 245))
    return {
        "lum_mean": mean,
        "lum_std": std,
        "lum_min": mn,
        "lum_max": mx,
        "lum_p01": float(p01),
        "lum_p05": float(p05),
        "lum_p50": float(p50),
        "lum_p95": float(p95),
        "lum_p99": float(p99),
        "lum_p95_minus_p05": float(p95 - p05),
        "lum_frac_lt10": frac_lt10,
        "lum_frac_gt245": frac_gt245,
    }


def _make_contact_sheet(
    image_paths: Sequence[Path],
    out_path: Path,
    thumb_size: int = 256,
    cols: int = 8,
    max_items: int = 80,
) -> Optional[Path]:
    if not image_paths:
        return None

    selected = list(image_paths[:max_items])
    n = len(selected)
    cols = max(1, cols)
    rows = (n + cols - 1) // cols

    # White background; simple and readable.
    sheet_w = cols * thumb_size
    sheet_h = rows * thumb_size
    sheet = Image.new("RGB", (sheet_w, sheet_h), color=(255, 255, 255))

    for idx, p in enumerate(selected):
        r = idx // cols
        c = idx % cols
        x0 = c * thumb_size
        y0 = r * thumb_size
        try:
            with Image.open(p) as im:
                im = im.convert("RGB")
                im.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)
                # Center thumbnail in cell
                ox = x0 + (thumb_size - im.size[0]) // 2
                oy = y0 + (thumb_size - im.size[1]) // 2
                sheet.paste(im, (ox, oy))
        except Exception:
            # Skip unreadable images; leave blank cell.
            continue

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    return out_path


@dataclass
class ImageAuditRow:
    pptx_path: str
    pptx_stem: str
    pptx_sha1: str
    media_member: str
    extracted_path: str
    extracted_sha1: str
    extracted_bytes: int
    ext: str
    width: int
    height: int
    pil_mode: str
    color_class: str
    chroma_score: float
    error: str
    # Luminance stats (float)
    lum_mean: float
    lum_std: float
    lum_min: float
    lum_max: float
    lum_p01: float
    lum_p05: float
    lum_p50: float
    lum_p95: float
    lum_p99: float
    lum_p95_minus_p05: float
    lum_frac_lt10: float
    lum_frac_gt245: float


def _pptx_file_sha1(pptx_path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha1()
    with open(pptx_path, "rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _write_jsonl(rows: Sequence[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _write_csv(rows: Sequence[dict], path: Path) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _safe_rel(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except Exception:
        return path.as_posix()


def run_audit(
    base_dir: Path,
    input_dir: Path,
    output_dir: Path,
    max_images_per_pptx: int,
    max_total_images: int,
    chroma_threshold: float,
    thumb_size: int,
    contact_cols: int,
    contact_max_items: int,
) -> None:
    in_dir = _resolve_under(base_dir, input_dir)
    out_dir = _resolve_under(base_dir, output_dir)
    if not in_dir.exists():
        raise FileNotFoundError(f"Input dir not found: {in_dir}")

    pptx_files = sorted(in_dir.rglob("*.pptx"))
    if not pptx_files:
        print(f"[WARN] No .pptx files found under: {in_dir}")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    images_root = out_dir / "images"
    report_root = out_dir / "report"
    report_root.mkdir(parents=True, exist_ok=True)

    rows: List[ImageAuditRow] = []
    extracted_image_paths: List[Path] = []

    total_extracted = 0
    for pptx_path in tqdm(pptx_files, desc="PPTX", unit="file"):
        pptx_stem = pptx_path.stem
        pptx_stem_safe = _sanitize_stem_for_dir(pptx_stem)
        pptx_sha1 = _pptx_file_sha1(pptx_path)

        out_subdir = images_root / pptx_stem_safe
        out_subdir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(pptx_path, "r") as zf:
                members = list(_iter_pptx_media_members(zf))
                if max_images_per_pptx > 0:
                    members = members[:max_images_per_pptx]

                for info in members:
                    if 0 < max_total_images <= total_extracted:
                        break

                    ext = _guess_ext_from_name(info.filename)
                    # Extract bytes regardless of ext; we may still open with PIL.
                    data = zf.read(info.filename)
                    extracted_sha1 = _sha1_bytes(data)
                    extracted_bytes = len(data)

                    # Pick output filename: keep original media name but make it stable.
                    media_name = Path(info.filename).name
                    out_path = out_subdir / media_name
                    if not out_path.suffix:
                        # If no suffix, try using ext from member path; else default.
                        out_path = out_subdir / (media_name + (ext or ".bin"))

                    # If ext is missing/unexpected, keep bytes anyway; analysis may fail but row is recorded.
                    with open(out_path, "wb") as f:
                        f.write(data)

                    width = 0
                    height = 0
                    pil_mode = ""
                    color_class = ""
                    chroma_score = 0.0
                    err = ""
                    lum_stats: Dict[str, float] = {
                        "lum_mean": 0.0,
                        "lum_std": 0.0,
                        "lum_min": 0.0,
                        "lum_max": 0.0,
                        "lum_p01": 0.0,
                        "lum_p05": 0.0,
                        "lum_p50": 0.0,
                        "lum_p95": 0.0,
                        "lum_p99": 0.0,
                        "lum_p95_minus_p05": 0.0,
                        "lum_frac_lt10": 0.0,
                        "lum_frac_gt245": 0.0,
                    }

                    # Analyze only if PIL can open it (best-effort).
                    try:
                        with Image.open(BytesIO(data)) as im:
                            width, height = im.size
                            pil_mode = im.mode
                            # Color class
                            rgb = im.convert("RGB")
                            color_class, chroma_score = _classify_color_from_rgb(rgb, threshold=chroma_threshold)
                            # Luminance stats
                            lum_stats = _compute_luminance_stats(im)
                            extracted_image_paths.append(out_path)
                    except Exception as e:
                        err = f"{type(e).__name__}: {e}"

                    rows.append(
                        ImageAuditRow(
                            pptx_path=_safe_rel(pptx_path, base_dir),
                            pptx_stem=pptx_stem,
                            pptx_sha1=pptx_sha1,
                            media_member=info.filename,
                            extracted_path=_safe_rel(out_path, base_dir),
                            extracted_sha1=extracted_sha1,
                            extracted_bytes=extracted_bytes,
                            ext=ext,
                            width=width,
                            height=height,
                            pil_mode=pil_mode,
                            color_class=color_class,
                            chroma_score=float(chroma_score),
                            error=err,
                            **lum_stats,
                        )
                    )
                    total_extracted += 1

                if 0 < max_total_images <= total_extracted:
                    break
        except zipfile.BadZipFile as e:
            # One row per PPTX failure (no extracted image)
            rows.append(
                ImageAuditRow(
                    pptx_path=_safe_rel(pptx_path, base_dir),
                    pptx_stem=pptx_stem,
                    pptx_sha1=pptx_sha1,
                    media_member="",
                    extracted_path="",
                    extracted_sha1="",
                    extracted_bytes=0,
                    ext="",
                    width=0,
                    height=0,
                    pil_mode="",
                    color_class="",
                    chroma_score=0.0,
                    error=f"BadZipFile: {e}",
                    lum_mean=0.0,
                    lum_std=0.0,
                    lum_min=0.0,
                    lum_max=0.0,
                    lum_p01=0.0,
                    lum_p05=0.0,
                    lum_p50=0.0,
                    lum_p95=0.0,
                    lum_p99=0.0,
                    lum_p95_minus_p05=0.0,
                    lum_frac_lt10=0.0,
                    lum_frac_gt245=0.0,
                )
            )

    dict_rows = [asdict(r) for r in rows]
    jsonl_path = report_root / "manifest.jsonl"
    csv_path = report_root / "manifest.csv"
    _write_jsonl(dict_rows, jsonl_path)
    _write_csv(dict_rows, csv_path)

    # Summary aggregations (best-effort; ignore error rows for stats)
    ok_rows = [r for r in rows if not r.error and r.width > 0 and r.height > 0]
    by_ext: Dict[str, int] = {}
    by_class: Dict[str, int] = {}
    for r in ok_rows:
        by_ext[r.ext] = by_ext.get(r.ext, 0) + 1
        by_class[r.color_class] = by_class.get(r.color_class, 0) + 1

    def _median(values: List[float]) -> float:
        if not values:
            return 0.0
        return float(np.median(np.array(values, dtype=np.float32)))

    summary = {
        "input_dir": _safe_rel(in_dir, base_dir),
        "output_dir": _safe_rel(out_dir, base_dir),
        "pptx_files": len(pptx_files),
        "rows_total": len(rows),
        "images_ok": len(ok_rows),
        "images_error": len(rows) - len(ok_rows),
        "count_by_ext": dict(sorted(by_ext.items(), key=lambda kv: (-kv[1], kv[0]))),
        "count_by_color_class": dict(sorted(by_class.items(), key=lambda kv: (-kv[1], kv[0]))),
        "lum_mean_median": _median([r.lum_mean for r in ok_rows]),
        "lum_p95_minus_p05_median": _median([r.lum_p95_minus_p05 for r in ok_rows]),
        "lum_frac_lt10_median": _median([r.lum_frac_lt10 for r in ok_rows]),
        "lum_frac_gt245_median": _median([r.lum_frac_gt245 for r in ok_rows]),
    }
    with open(report_root / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Contact sheets (overall + gray/color split)
    contact_dir = report_root / "contact_sheets"
    # Keep deterministic ordering: extracted_image_paths are appended in pptx order.
    contact_all = _make_contact_sheet(
        extracted_image_paths,
        contact_dir / "all.png",
        thumb_size=thumb_size,
        cols=contact_cols,
        max_items=contact_max_items,
    )

    gray_paths = []
    color_paths = []
    # Map extracted_path -> class from ok_rows (best-effort)
    class_map = {(_resolve_under(base_dir, Path(r.extracted_path)).as_posix()): r.color_class for r in ok_rows}
    for p in extracted_image_paths:
        cls = class_map.get(p.as_posix(), "")
        if cls == "GRAY":
            gray_paths.append(p)
        elif cls == "COLOR":
            color_paths.append(p)

    contact_gray = _make_contact_sheet(
        gray_paths,
        contact_dir / "gray.png",
        thumb_size=thumb_size,
        cols=contact_cols,
        max_items=contact_max_items,
    )
    contact_color = _make_contact_sheet(
        color_paths,
        contact_dir / "color.png",
        thumb_size=thumb_size,
        cols=contact_cols,
        max_items=contact_max_items,
    )

    # Markdown report
    md_lines = []
    md_lines.append("# PPTX Embedded Image Audit\n")
    md_lines.append(f"- Generated: `{_now_tag()}`\n")
    md_lines.append(f"- Input: `{summary['input_dir']}`\n")
    md_lines.append(f"- Output: `{summary['output_dir']}`\n")
    md_lines.append("\n## Counts\n")
    md_lines.append(f"- PPTX files: **{summary['pptx_files']}**\n")
    md_lines.append(f"- Extracted images (OK): **{summary['images_ok']}**\n")
    md_lines.append(f"- Error rows: **{summary['images_error']}**\n")

    md_lines.append("\n### By extension\n")
    for k, v in summary["count_by_ext"].items():
        md_lines.append(f"- **{k or '(none)'}**: {v}\n")

    md_lines.append("\n### By color class\n")
    for k, v in summary["count_by_color_class"].items():
        md_lines.append(f"- **{k or '(unknown)'}**: {v}\n")

    md_lines.append("\n## Luminance quick stats (median over images)\n")
    md_lines.append(f"- **lum_mean**: {summary['lum_mean_median']:.1f} / 255\n")
    md_lines.append(f"- **lum_p95 - lum_p05** (robust contrast): {summary['lum_p95_minus_p05_median']:.1f}\n")
    md_lines.append(f"- **frac(lum < 10)** (near-black): {summary['lum_frac_lt10_median']:.3f}\n")
    md_lines.append(f"- **frac(lum > 245)** (near-white): {summary['lum_frac_gt245_median']:.3f}\n")

    def _md_img(p: Optional[Path], label: str) -> None:
        if not p:
            return
        rel = _safe_rel(p, report_root)
        md_lines.append(f"\n## {label}\n\n![]({rel})\n")

    _md_img(contact_all, "Contact sheet (all)")
    _md_img(contact_gray, "Contact sheet (GRAY)")
    _md_img(contact_color, "Contact sheet (COLOR)")

    md_lines.append("\n## Files\n")
    md_lines.append(f"- Manifest JSONL: `{_safe_rel(jsonl_path, base_dir)}`\n")
    md_lines.append(f"- Manifest CSV: `{_safe_rel(csv_path, base_dir)}`\n")
    md_lines.append(f"- Summary JSON: `{_safe_rel(report_root / 'summary.json', base_dir)}`\n")

    with open(report_root / "report.md", "w", encoding="utf-8") as f:
        f.write("".join(md_lines))

    print(f"[OK] Wrote: {report_root / 'report.md'}")
    print(f"[OK] Wrote: {jsonl_path}")
    print(f"[OK] Wrote: {csv_path}")


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Extract embedded images from PPTX and produce a quick offline stats report."
    )
    p.add_argument(
        "--base_dir",
        type=Path,
        default=Path("."),
        help="Project base dir (paths are resolved under this unless absolute). Default: .",
    )
    p.add_argument(
        "--input_dir",
        type=Path,
        default=Path("2_Data/raw/2024"),
        help="Directory to search recursively for .pptx files. Default: 2_Data/raw/2024",
    )
    p.add_argument(
        "--output_dir",
        type=Path,
        default=Path(f"2_Data/eda/PPTX_IMAGE_AUDIT_{_now_tag()}"),
        help="Output directory. Default: 2_Data/eda/PPTX_IMAGE_AUDIT_<timestamp>",
    )
    p.add_argument(
        "--max_images_per_pptx",
        type=int,
        default=0,
        help="Limit extracted images per PPTX (0 = no limit).",
    )
    p.add_argument(
        "--max_total_images",
        type=int,
        default=0,
        help="Global limit on extracted images (0 = no limit).",
    )
    p.add_argument(
        "--chroma_threshold",
        type=float,
        default=0.15,
        help="Threshold for GRAY vs COLOR classification.",
    )
    p.add_argument(
        "--thumb_size",
        type=int,
        default=192,
        help="Thumbnail size (px) for contact sheets.",
    )
    p.add_argument(
        "--contact_cols",
        type=int,
        default=10,
        help="Number of columns in contact sheets.",
    )
    p.add_argument(
        "--contact_max_items",
        type=int,
        default=120,
        help="Max images included per contact sheet.",
    )
    return p


def main() -> None:
    args = build_argparser().parse_args()
    try:
        run_audit(
            base_dir=args.base_dir,
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            max_images_per_pptx=int(args.max_images_per_pptx),
            max_total_images=int(args.max_total_images),
            chroma_threshold=float(args.chroma_threshold),
            thumb_size=int(args.thumb_size),
            contact_cols=int(args.contact_cols),
            contact_max_items=int(args.contact_max_items),
        )
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()



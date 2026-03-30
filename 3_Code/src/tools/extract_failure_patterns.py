#!/usr/bin/env python3
"""
Extract cluster-level infographic_prompt_en / infographic_hint_v2 from S1 debug_raw artifacts
and summarize common trigger patterns (3D/scan wording, minimal_labels_only, style mismatch).

Typical usage:
  python3 3_Code/src/tools/extract_failure_patterns.py \
    --base_dir . --run_tag FINAL_DISTRIBUTION --arm G \
    --group_id grp_a8b30bdbb7 --group_id grp_47059b1c5d --group_id grp_ebdc9f5c1e \
    --write_md 5_Meeting/CLUSTER_FAILURE_PATTERNS__FINAL_DISTRIBUTION.md
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


TRIGGER_PATTERNS_3D = [
    r"\b3d\b",
    r"\b3-d\b",
    r"\bthree[- ]dimensional\b",
    r"\btransparent 3d\b",
    r"\bvolume render(?:ing)?\b",
    r"\b3d_volume_rendering\b",
    r"\bcomplex_3d_render\b",
    r"\breconstruction\b",
]

TRIGGER_PATTERNS_SCAN = [
    r"\bct scan\b",
    r"\bct density\b",
    r"\boverlaid on\b",
    r"\bmri\b",  # not always bad; included for visibility
]


@dataclass
class ClusterExtract:
    group_id: str
    visual_type_category: str
    cluster_id: str
    infographic_style: str
    infographic_prompt_en: str
    infographic_hint_v2: Dict[str, Any]
    triggers: List[str]


def _detect_triggers(
    *,
    prompt_en: str,
    hint_v2: Optional[Dict[str, Any]],
    visual_type_category: str,
    infographic_style: str,
) -> List[str]:
    triggers: List[str] = []
    p = (prompt_en or "").strip()
    p_lc = p.lower()

    if any(re.search(pat, p_lc) for pat in TRIGGER_PATTERNS_3D):
        triggers.append("prompt_mentions_3d")
    if any(re.search(pat, p_lc) for pat in TRIGGER_PATTERNS_SCAN):
        # "mri" is not always a bug, but often correlates with scan-like phrasing.
        triggers.append("prompt_mentions_scan_like_wording(ct/mri/overlay)")

    text_budget = None
    if isinstance(hint_v2, dict):
        rp = hint_v2.get("rendering_policy")
        if isinstance(rp, dict):
            text_budget = rp.get("text_budget")
    if str(text_budget or "").strip() == "minimal_labels_only":
        triggers.append("hint_text_budget=minimal_labels_only")

    if (
        str(infographic_style or "").strip()
        and str(visual_type_category or "").strip()
        and str(infographic_style).strip() != str(visual_type_category).strip()
    ):
        triggers.append("style_mismatch(infographic_style!=visual_type_category)")

    return triggers


def _load_stage1_debug_raw_response(
    *, base_dir: Path, run_tag: str, arm: str, group_id: str
) -> Tuple[Path, Dict[str, Any]]:
    arm = str(arm or "").strip().upper()
    p = (
        base_dir
        / "2_Data"
        / "metadata"
        / "generated"
        / run_tag
        / "debug_raw"
        / f"stage1__group_{group_id}__arm_{arm}__raw_response.txt"
    )
    if not p.exists():
        raise FileNotFoundError(f"Missing debug_raw stage1 raw response: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected JSON root in {p}: expected object, got {type(data).__name__}")
    return p, data


def extract_clusters_from_debug_raw(
    *,
    base_dir: Path,
    run_tag: str,
    arm: str,
    group_id: str,
) -> List[ClusterExtract]:
    _, data = _load_stage1_debug_raw_response(base_dir=base_dir, run_tag=run_tag, arm=arm, group_id=group_id)
    visual_type_category = str(data.get("visual_type_category", "")).strip()
    clusters = data.get("infographic_clusters") or []
    if not isinstance(clusters, list):
        raise ValueError(f"Unexpected infographic_clusters type in {group_id}: {type(clusters).__name__}")

    out: List[ClusterExtract] = []
    for c in clusters:
        if not isinstance(c, dict):
            continue
        cluster_id = str(c.get("cluster_id", "")).strip()
        infographic_style = str(c.get("infographic_style", "")).strip()
        prompt_en = str(c.get("infographic_prompt_en", "")).strip()
        hint_v2 = c.get("infographic_hint_v2")
        hint_v2_obj: Dict[str, Any] = hint_v2 if isinstance(hint_v2, dict) else {}
        triggers = _detect_triggers(
            prompt_en=prompt_en,
            hint_v2=hint_v2_obj,
            visual_type_category=visual_type_category,
            infographic_style=infographic_style,
        )
        out.append(
            ClusterExtract(
                group_id=group_id,
                visual_type_category=visual_type_category,
                cluster_id=cluster_id or "(missing)",
                infographic_style=infographic_style or "(missing)",
                infographic_prompt_en=prompt_en,
                infographic_hint_v2=hint_v2_obj,
                triggers=triggers,
            )
        )
    return out


def _json_compact(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)


def build_markdown_report(*, extracts: List[ClusterExtract], run_tag: str, arm: str) -> str:
    lines: List[str] = []
    lines.append(f"# Cluster failure patterns — extracted from S1 debug_raw ({run_tag}, arm {arm})")
    lines.append("")
    lines.append("## Trigger summary (auto-detected)")
    lines.append("")
    trigger_counts: Dict[str, int] = {}
    for e in extracts:
        for t in e.triggers:
            trigger_counts[t] = trigger_counts.get(t, 0) + 1
    for k in sorted(trigger_counts.keys()):
        lines.append(f"- **{k}**: {trigger_counts[k]}")
    lines.append("")
    lines.append("## Extracted cluster payloads (exact)")
    lines.append("")

    for e in extracts:
        lines.append(f"### {e.group_id} / {e.cluster_id}")
        lines.append("")
        lines.append(f"- **visual_type_category**: `{e.visual_type_category}`")
        lines.append(f"- **infographic_style**: `{e.infographic_style}`")
        lines.append(f"- **triggers**: `{', '.join(e.triggers) if e.triggers else '(none detected)'}`")
        lines.append("")
        lines.append("**infographic_prompt_en (exact)**")
        lines.append("")
        lines.append("```")
        lines.append(e.infographic_prompt_en or "")
        lines.append("```")
        lines.append("")
        lines.append("**infographic_hint_v2 (exact)**")
        lines.append("")
        lines.append("```json")
        lines.append(_json_compact(e.infographic_hint_v2 or {}))
        lines.append("```")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base_dir", default=".", help="Repo base dir (default: .)")
    ap.add_argument("--run_tag", required=True)
    ap.add_argument("--arm", required=True, help="Arm letter, e.g., G")
    ap.add_argument("--group_id", action="append", required=True, help="Repeatable: group id like grp_a8b30bdbb7")
    ap.add_argument("--write_md", default="", help="Optional markdown output path")
    args = ap.parse_args()

    base_dir = Path(args.base_dir).resolve()
    run_tag = str(args.run_tag).strip()
    arm = str(args.arm).strip().upper()
    group_ids = [str(g).strip() for g in (args.group_id or []) if str(g).strip()]

    all_extracts: List[ClusterExtract] = []
    for gid in group_ids:
        all_extracts.extend(extract_clusters_from_debug_raw(base_dir=base_dir, run_tag=run_tag, arm=arm, group_id=gid))

    # Print a compact console view
    for e in all_extracts:
        text_budget = None
        rp = (e.infographic_hint_v2 or {}).get("rendering_policy")
        if isinstance(rp, dict):
            text_budget = rp.get("text_budget")
        print(
            f"[{e.group_id} {e.cluster_id}] "
            f"visual_type={e.visual_type_category} style={e.infographic_style} "
            f"text_budget={text_budget} triggers={e.triggers}"
        )

    if args.write_md:
        md_path = (base_dir / args.write_md).resolve()
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md = build_markdown_report(extracts=all_extracts, run_tag=run_tag, arm=arm)
        md_path.write_text(md, encoding="utf-8")
        print(f"[OUT] wrote markdown report: {md_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())



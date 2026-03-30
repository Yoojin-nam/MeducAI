#!/usr/bin/env python3
"""
S5R Phase-1 (Baseline) Analysis Helper

What this does:
- Loads S5 validation JSONL for 2 replicates (rep1/rep2) for the same Arm + groups
- Dedupes multiple lines per group (keeps latest validation_timestamp)
- Computes group-level endpoints from per-card `issues[]`:
  - S2_any_issue_rate_per_group
  - S2_issues_per_card_per_group
  - TA_bad_rate_per_group (cards with technical_accuracy < 1.0)
  - (S1 issue counts for context)
- Aggregates replicates using mean + SD (canonical replicate aggregation rule)
- Writes a Markdown analysis artifact (Phase 1: S5R0 analysis & improvement points input)

Usage:
  python3 3_Code/src/tools/s5/s5r_phase1_analysis.py \
    --base_dir . \
    --arm G \
    --rep1_run_tag DEV_armG_mm_S5R0_before_rerun_preFix_...__rep1 \
    --rep2_run_tag DEV_armG_mm_S5R0_before_rerun_preFix_...__rep2 \
    --output 0_Protocol/05_Pipeline_and_Execution/S5R0_Phase1_Analysis__DEV_armG_mm.md
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _parse_iso(ts: str) -> Optional[datetime]:
    ts = (ts or "").strip()
    if not ts:
        return None
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _dedupe_latest_by_group(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    best: Dict[str, Tuple[Optional[datetime], Dict[str, Any]]] = {}
    for r in rows:
        gid = str(r.get("group_id") or "").strip()
        if not gid:
            continue
        ts_str = str(r.get("validation_timestamp") or "")
        ts = _parse_iso(ts_str)
        cur = best.get(gid)
        if cur is None or (ts is not None and (cur[0] is None or ts > cur[0])):
            best[gid] = (ts, r)
    # Stable ordering for human tables
    return [v[1] for v in sorted(best.values(), key=lambda x: (x[0] is None, x[0]))]


def _safe_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def _safe_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _issue_code(it: Any) -> str:
    if not isinstance(it, dict):
        return "UNKNOWN"
    return str(it.get("issue_code") or "").strip() or "UNKNOWN"


def _fix_target(it: Any) -> str:
    if not isinstance(it, dict):
        return "UNKNOWN"
    return str(it.get("recommended_fix_target") or "").strip() or "UNKNOWN"


def _extract_judge_info(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract judge version information from S5 validation records.
    
    Returns:
        {
            "prompt_bundle_hash": str or None,
            "prompt_file_ids_s5": dict or None,
            "prompt_registry_path": str or None,
            "eval_s5r": str or None,  # Parsed from run_tag __evalS5Rk
            "generation_s5r": str or None,  # Parsed from run_tag S5Rk
            "judge_consistent": bool,  # True if all records use same judge
        }
    """
    if not rows:
        return {}
    
    # Extract from first record (should be consistent across groups)
    first = rows[0]
    s5_prompt_bundle = first.get("s5_prompt_bundle", {}) or {}
    
    # Parse run_tag for S5R info
    run_tag = str(first.get("run_tag", ""))
    eval_s5r = None
    generation_s5r = None
    
    # Parse __evalS5Rk suffix
    if "__evalS5R" in run_tag:
        match = re.search(r"__evalS5R(\d+)", run_tag)
        if match:
            eval_s5r = f"S5R{match.group(1)}"
    
    # Parse generation S5R from run_tag pattern: ..._S5Rk_...
    if "_S5R" in run_tag:
        match = re.search(r"_S5R(\d+)_", run_tag)
        if match:
            generation_s5r = f"S5R{match.group(1)}"
    
    # Check judge consistency across all records
    judge_consistent = True
    if len(rows) > 1:
        first_hash = s5_prompt_bundle.get("prompt_bundle_hash", "")
        for r in rows[1:]:
            other_bundle = r.get("s5_prompt_bundle", {}) or {}
            other_hash = other_bundle.get("prompt_bundle_hash", "")
            if other_hash and first_hash and other_hash != first_hash:
                judge_consistent = False
                break
    
    return {
        "prompt_bundle_hash": s5_prompt_bundle.get("prompt_bundle_hash"),
        "prompt_file_ids_s5": s5_prompt_bundle.get("prompt_file_ids_s5", {}),
        "prompt_registry_path": s5_prompt_bundle.get("prompt_registry_path"),
        "eval_s5r": eval_s5r,
        "generation_s5r": generation_s5r,
        "judge_consistent": judge_consistent,
    }


@dataclass(frozen=True)
class GroupEndpoints:
    group_id: str
    s1_issue_count: int
    s2_total_cards: int
    s2_cards_with_issue: int
    s2_total_issues: int
    s2_any_issue_rate: float
    s2_issues_per_card: float
    s2_ta_bad_rate: float


@dataclass(frozen=True)
class RunSummary:
    run_tag: str
    arm: str
    groups: int
    total_cards: int
    cards_with_issue: int
    total_issues: int
    overall_any_issue_rate_by_cards: float
    mean_any_issue_rate_by_groups: float
    mean_issues_per_card_by_groups: float
    mean_ta_bad_rate_by_groups: float


def _compute_endpoints_per_group(
    rows_latest: List[Dict[str, Any]],
) -> Tuple[List[GroupEndpoints], Dict[str, Dict[str, Dict[str, int]]], Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]]:
    """
    Returns:
      - per-group endpoints (one row per group_id)
      - issue taxonomy counts:
          {
            "S1": {"issue_code": {CODE: n}, "fix_target": {TARGET: n}},
            "S2": {"issue_code": {CODE: n}, "fix_target": {TARGET: n}},
          }
      - patch backlog (actionable rollup):
          {
            "S1": {TARGET: {ISSUE_CODE: {"count": n, "hints": set([...])}}},
            "S2": {TARGET: {ISSUE_CODE: {"count": n, "hints": set([...])}}},
          }
    """
    out: List[GroupEndpoints] = []
    taxonomy = {"S1": {"issue_code": {}, "fix_target": {}}, "S2": {"issue_code": {}, "fix_target": {}}}
    backlog: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {"S1": {}, "S2": {}}

    def bump(stage: str, kind: str, key: str) -> None:
        d = taxonomy[stage][kind]
        d[key] = int(d.get(key, 0)) + 1

    def bump_backlog(stage: str, target: str, code: str, hint: str) -> None:
        stage_map = backlog.setdefault(stage, {})
        tgt_map = stage_map.setdefault(target, {})
        rec = tgt_map.setdefault(code, {"count": 0, "hints": set()})
        rec["count"] = int(rec.get("count", 0)) + 1
        hint = (hint or "").strip()
        if hint:
            hints = rec.get("hints")
            if isinstance(hints, set):
                hints.add(hint)

    for r in rows_latest:
        gid = str(r.get("group_id") or "").strip()
        if not gid:
            continue

        s1 = _safe_dict(r.get("s1_table_validation"))
        s1_issues = _safe_list(s1.get("issues"))
        for it in s1_issues:
            code = _issue_code(it)
            tgt = _fix_target(it)
            hint = str(it.get("prompt_patch_hint") or "")
            bump("S1", "issue_code", code)
            bump("S1", "fix_target", tgt)
            bump_backlog("S1", tgt, code, hint)

        s2 = _safe_dict(r.get("s2_cards_validation"))
        cards = _safe_list(s2.get("cards"))

        total_cards = 0
        cards_with_issue = 0
        total_issues = 0
        ta_bad = 0

        for c in cards:
            if not isinstance(c, dict):
                continue
            total_cards += 1
            issues = _safe_list(c.get("issues"))
            if issues:
                cards_with_issue += 1
                total_issues += len(issues)
                for it in issues:
                    code = _issue_code(it)
                    tgt = _fix_target(it)
                    hint = str(it.get("prompt_patch_hint") or "")
                    bump("S2", "issue_code", code)
                    bump("S2", "fix_target", tgt)
                    bump_backlog("S2", tgt, code, hint)
            try:
                ta = float(c.get("technical_accuracy", 0.0) or 0.0)
            except Exception:
                ta = 0.0
            if ta < 1.0:
                ta_bad += 1

        any_issue_rate = (cards_with_issue / total_cards) if total_cards > 0 else 0.0
        issues_per_card = (total_issues / total_cards) if total_cards > 0 else 0.0
        ta_bad_rate = (ta_bad / total_cards) if total_cards > 0 else 0.0

        out.append(
            GroupEndpoints(
                group_id=gid,
                s1_issue_count=len(s1_issues),
                s2_total_cards=total_cards,
                s2_cards_with_issue=cards_with_issue,
                s2_total_issues=total_issues,
                s2_any_issue_rate=any_issue_rate,
                s2_issues_per_card=issues_per_card,
                s2_ta_bad_rate=ta_bad_rate,
            )
        )

    out.sort(key=lambda x: x.group_id)
    return out, taxonomy, backlog


def _run_summary(run_tag: str, arm: str, groups: List[GroupEndpoints]) -> RunSummary:
    n = len(groups)
    total_cards = sum(g.s2_total_cards for g in groups)
    cards_with_issue = sum(g.s2_cards_with_issue for g in groups)
    total_issues = sum(g.s2_total_issues for g in groups)
    overall_rate = (cards_with_issue / total_cards) if total_cards > 0 else 0.0
    mean_any_issue_rate = (sum(g.s2_any_issue_rate for g in groups) / n) if n > 0 else 0.0
    mean_issues_per_card = (sum(g.s2_issues_per_card for g in groups) / n) if n > 0 else 0.0
    mean_ta_bad_rate = (sum(g.s2_ta_bad_rate for g in groups) / n) if n > 0 else 0.0
    return RunSummary(
        run_tag=run_tag,
        arm=arm,
        groups=n,
        total_cards=total_cards,
        cards_with_issue=cards_with_issue,
        total_issues=total_issues,
        overall_any_issue_rate_by_cards=overall_rate,
        mean_any_issue_rate_by_groups=mean_any_issue_rate,
        mean_issues_per_card_by_groups=mean_issues_per_card,
        mean_ta_bad_rate_by_groups=mean_ta_bad_rate,
    )


def _mean_sd(a: float, b: float) -> Tuple[float, float]:
    m = (a + b) / 2.0
    # For n=2 replicates, SD = |a-b| / sqrt(2)
    sd = abs(a - b) / (2**0.5)
    return m, sd


def _top_k(d: Dict[str, int], k: int = 12) -> List[Tuple[str, int]]:
    return sorted(d.items(), key=lambda x: (-x[1], x[0]))[:k]


def _pct(x: float) -> str:
    return f"{x*100:.1f}%"


def _md_table(rows: List[List[str]]) -> str:
    if not rows:
        return ""
    header = rows[0]
    out = []
    out.append("| " + " | ".join(header) + " |")
    out.append("|" + "|".join(["---"] * len(header)) + "|")
    for r in rows[1:]:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def build_markdown(
    *,
    arm: str,
    rep1_run_tag: str,
    rep2_run_tag: str,
    rep1: List[GroupEndpoints],
    rep2: List[GroupEndpoints],
    rep1_tax: Dict[str, Dict[str, Dict[str, int]]],
    rep2_tax: Dict[str, Dict[str, Dict[str, int]]],
    rep1_backlog: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]],
    rep2_backlog: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]],
    rep1_judge_info: Dict[str, Any],
    rep2_judge_info: Dict[str, Any],
) -> str:
    rep1_by_gid = {g.group_id: g for g in rep1}
    rep2_by_gid = {g.group_id: g for g in rep2}
    all_gids = sorted(set(rep1_by_gid) | set(rep2_by_gid))
    missing_1 = [g for g in all_gids if g not in rep1_by_gid]
    missing_2 = [g for g in all_gids if g not in rep2_by_gid]

    rs1 = _run_summary(rep1_run_tag, arm, rep1)
    rs2 = _run_summary(rep2_run_tag, arm, rep2)

    # Aggregate per group
    table_rows: List[List[str]] = [
        [
            "group_id",
            "S2_any_issue_rate (rep1)",
            "S2_any_issue_rate (rep2)",
            "mean",
            "SD",
            "S2_total_cards (rep1/rep2)",
            "S2_cards_with_issue (rep1/rep2)",
            "S2_issues_per_card mean (rep1/rep2)",
        ]
    ]
    for gid in all_gids:
        g1 = rep1_by_gid.get(gid)
        g2 = rep2_by_gid.get(gid)
        if not g1 or not g2:
            continue
        mean_rate, sd_rate = _mean_sd(g1.s2_any_issue_rate, g2.s2_any_issue_rate)
        table_rows.append(
            [
                f"`{gid}`",
                _pct(g1.s2_any_issue_rate),
                _pct(g2.s2_any_issue_rate),
                _pct(mean_rate),
                _pct(sd_rate),
                f"{g1.s2_total_cards}/{g2.s2_total_cards}",
                f"{g1.s2_cards_with_issue}/{g2.s2_cards_with_issue}",
                f"{g1.s2_issues_per_card:.3f}/{g2.s2_issues_per_card:.3f}",
            ]
        )

    # Combine taxonomies
    def merge_counts(a: Dict[str, int], b: Dict[str, int]) -> Dict[str, int]:
        out = dict(a)
        for k, v in b.items():
            out[k] = int(out.get(k, 0)) + int(v)
        return out

    def merge_backlog(
        a: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]],
        b: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]],
    ) -> Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]:
        out: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {"S1": {}, "S2": {}}
        for stage in ("S1", "S2"):
            for src in (a.get(stage, {}), b.get(stage, {})):
                for tgt, codes in src.items():
                    for code, rec in codes.items():
                        orec = out[stage].setdefault(tgt, {}).setdefault(code, {"count": 0, "hints": set()})
                        orec["count"] = int(orec.get("count", 0)) + int(rec.get("count", 0))
                        hints = orec.get("hints")
                        if not isinstance(hints, set):
                            continue
                        for h in rec.get("hints", set()):
                            if isinstance(h, str) and h.strip():
                                hints.add(h.strip())
        return out

    s1_issue_codes = merge_counts(rep1_tax["S1"]["issue_code"], rep2_tax["S1"]["issue_code"])
    s2_issue_codes = merge_counts(rep1_tax["S2"]["issue_code"], rep2_tax["S2"]["issue_code"])
    s1_fix_targets = merge_counts(rep1_tax["S1"]["fix_target"], rep2_tax["S1"]["fix_target"])
    s2_fix_targets = merge_counts(rep1_tax["S2"]["fix_target"], rep2_tax["S2"]["fix_target"])
    combined_backlog = merge_backlog(rep1_backlog, rep2_backlog)

    lines: List[str] = []
    lines.append("# S5R0 Phase 1 — S5 Report Analysis & Improvement Points (Arm G)")
    lines.append("")
    lines.append(f"- **rep1 run_tag**: `{rep1_run_tag}`")
    lines.append(f"- **rep2 run_tag**: `{rep2_run_tag}`")
    lines.append(f"- **Arm**: `{arm}`")
    lines.append("")
    
    lines.append("## 0. Judge version information (for cross-evaluation)")
    lines.append("")
    lines.append("### rep1 judge info")
    lines.append(f"- **Generation S5R**: {rep1_judge_info.get('generation_s5r', 'Unknown')}")
    lines.append(f"- **Evaluation judge S5R**: {rep1_judge_info.get('eval_s5r', 'Not specified (using default registry)')}")
    prompt_hash = rep1_judge_info.get('prompt_bundle_hash')
    if prompt_hash:
        lines.append(f"- **Prompt bundle hash**: {prompt_hash[:16] if len(prompt_hash) > 16 else prompt_hash}")
    else:
        lines.append("- **Prompt bundle hash**: Not available")
    prompt_file_ids = rep1_judge_info.get('prompt_file_ids_s5', {})
    if prompt_file_ids:
        lines.append(f"- **S5 prompt files**: {', '.join(prompt_file_ids.keys())}")
    else:
        lines.append("- **S5 prompt files**: Not available")
    lines.append(f"- **Judge consistency**: {'✓ Consistent' if rep1_judge_info.get('judge_consistent', True) else '⚠ Inconsistent across groups'}")
    lines.append("")
    lines.append("### rep2 judge info")
    lines.append(f"- **Generation S5R**: {rep2_judge_info.get('generation_s5r', 'Unknown')}")
    lines.append(f"- **Evaluation judge S5R**: {rep2_judge_info.get('eval_s5r', 'Not specified (using default registry)')}")
    prompt_hash2 = rep2_judge_info.get('prompt_bundle_hash')
    if prompt_hash2:
        lines.append(f"- **Prompt bundle hash**: {prompt_hash2[:16] if len(prompt_hash2) > 16 else prompt_hash2}")
    else:
        lines.append("- **Prompt bundle hash**: Not available")
    prompt_file_ids2 = rep2_judge_info.get('prompt_file_ids_s5', {})
    if prompt_file_ids2:
        lines.append(f"- **S5 prompt files**: {', '.join(prompt_file_ids2.keys())}")
    else:
        lines.append("- **S5 prompt files**: Not available")
    lines.append(f"- **Judge consistency**: {'✓ Consistent' if rep2_judge_info.get('judge_consistent', True) else '⚠ Inconsistent across groups'}")
    lines.append("")
    
    # Cross-evaluation warning
    if rep1_judge_info.get('eval_s5r') or rep2_judge_info.get('eval_s5r'):
        lines.append("⚠️ **Cross-evaluation detected**: This analysis compares results evaluated with different judge versions.")
        lines.append("   - For Target 1 (Generation effect), ensure both before/after use the same judge.")
        lines.append("   - For Target 2 (Judge effect), this is expected behavior.")
        lines.append("")
    elif rep1_judge_info.get('generation_s5r') != rep2_judge_info.get('generation_s5r'):
        lines.append("⚠️ **Generation version mismatch**: rep1 and rep2 use different generation S5R versions.")
        lines.append("   - This may affect comparison validity.")
        lines.append("")

    lines.append("## 1. Run-level summary (per replicate)")
    lines.append("")
    lines.append(_md_table([
        ["replicate", "groups", "S2 total cards", "cards with ≥1 issue", "total issues", "any-issue rate (by cards)", "mean(any-issue rate) (by groups)"],
        ["rep1", str(rs1.groups), str(rs1.total_cards), str(rs1.cards_with_issue), str(rs1.total_issues), _pct(rs1.overall_any_issue_rate_by_cards), _pct(rs1.mean_any_issue_rate_by_groups)],
        ["rep2", str(rs2.groups), str(rs2.total_cards), str(rs2.cards_with_issue), str(rs2.total_issues), _pct(rs2.overall_any_issue_rate_by_cards), _pct(rs2.mean_any_issue_rate_by_groups)],
    ]))
    lines.append("")
    lines.append("- Notes:")
    lines.append("  - **Primary endpoint unit is group-level** (n=11 groups); replicate count does not increase n.")
    lines.append("  - **IMG numeric endpoints not computed here** because these S5 JSONL records do not include image-evaluation rubric fields (no `card_image_*` / `table_visual_*`).")
    lines.append("    - However, many **image-related issues** are still present as `issue_code`s on S2 cards (e.g., view mismatch, excessive text).")
    lines.append("")

    lines.append("## 2. Primary endpoint per group (S2_any_issue_rate_per_group)")
    lines.append("")
    if missing_1 or missing_2:
        lines.append(f"- ⚠️ Group mismatch detected: missing in rep1={len(missing_1)}, missing in rep2={len(missing_2)}")
        if missing_1:
            lines.append(f"  - missing in rep1: {', '.join(missing_1)}")
        if missing_2:
            lines.append(f"  - missing in rep2: {', '.join(missing_2)}")
        lines.append("")
    lines.append(_md_table(table_rows))
    lines.append("")
    lines.append("## 3. Issue taxonomy (rep1+rep2 combined; descriptive)")
    lines.append("")
    lines.append("### 3.1 S1 (table) — top issue codes")
    lines.append("")
    for k, v in _top_k(s1_issue_codes, k=15):
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    lines.append("### 3.2 S2 (cards) — top issue codes")
    lines.append("")
    for k, v in _top_k(s2_issue_codes, k=20):
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    lines.append("### 3.3 recommended_fix_target distribution (combined)")
    lines.append("")
    lines.append("**S1**:")
    for k, v in _top_k(s1_fix_targets, k=12):
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    lines.append("**S2**:")
    for k, v in _top_k(s2_fix_targets, k=12):
        lines.append(f"- `{k}`: {v}")
    lines.append("")

    lines.append("## 4. Patch backlog (rep1+rep2 combined; top targets)")
    lines.append("")
    lines.append("This is a compact, actionable view: **recommended_fix_target → issue_code → count (+ up to 2 patch hints)**.")
    lines.append("")

    def render_target_backlog(stage: str, target: str, top_codes: int = 8) -> None:
        codes = combined_backlog.get(stage, {}).get(target, {})
        if not codes:
            lines.append(f"- `{stage}` target `{target}`: (no backlog items)")
            return
        lines.append(f"### {stage} target: `{target}`")
        for code, rec in sorted(codes.items(), key=lambda x: (-int(x[1].get('count', 0)), x[0]))[:top_codes]:
            cnt = int(rec.get("count", 0))
            hints = rec.get("hints", set())
            hint_list = [h for h in hints if isinstance(h, str) and h.strip()]
            hint_list = sorted(hint_list)[:2]
            if hint_list:
                lines.append(f"- `{code}`: {cnt}")
                for h in hint_list:
                    lines.append(f"  - patch_hint: {h}")
            else:
                lines.append(f"- `{code}`: {cnt}")
        lines.append("")

    # Pick the highest frequency targets
    top_s2_targets = [k for k, _ in _top_k(s2_fix_targets, k=3)]
    top_s1_targets = [k for k, _ in _top_k(s1_fix_targets, k=2)]

    for t in top_s2_targets:
        render_target_backlog("S2", t)
    for t in top_s1_targets:
        render_target_backlog("S1", t)

    lines.append("## 5. Phase-2 (S5R1) improvement points (from S5R0 issues)")
    lines.append("")
    lines.append("### 5.1 Image-spec / image-generation prompt improvements (highest frequency in S5R0)")
    lines.append("")
    lines.append("- **Reduce image text load**: enforce a strict text budget and label-count limit in S3/S4 prompts to address `IMAGE_TEXT_*` failures.")
    lines.append("- **View compliance**: enforce explicit view tokens (AP/PA/Lateral/etc.) and validate they match the requested view (`*_VIEW_MISMATCH`).")
    lines.append("- **Laterality & anatomy sanity checks**: add a minimal self-check step for laterality inversion and label placement.")
    lines.append("")

    lines.append("### 5.2 S2 prompt/system improvements (next highest leverage)")
    lines.append("")
    lines.append("- **Diagnosis vs descriptor / vague answers**: tighten instruction to ensure `Answer` matches the question intent (diagnosis vs imaging finding/descriptor).")
    lines.append("- **Entity type ↔ exam_focus alignment**: enforce `exam_focus` allowed values by entity type (e.g., disease → diagnosis) to prevent `S2_EXAM_FOCUS_ENTITY_TYPE_MISMATCH`.")
    lines.append("- **Korean terminology + typos**: add explicit “medical Korean spell-check + avoid near-homophone slips” step (e.g., 분만/분산, 하하지/하지).")
    lines.append("- **Circular answers**: forbid answers that restate the question; require a direct 'why' / purpose when asked.")
    lines.append("")
    lines.append("### 5.3 S1 table improvements (quality + exam fidelity)")
    lines.append("")
    lines.append("- **Definition precision**: codify numeric thresholds precisely when they are canonical exam points (e.g., BI-RADS calcification size cutoffs).")
    lines.append("- **Modern terminology**: update outdated eponyms/terms (optionally keep '(formerly …)' for recall).")
    lines.append("- **Physics/wording clarity**: clarify terms that are easily misread (e.g., washout vs photopenia; DWI shine-through vs ADC).")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base_dir", required=True, help="Repo base dir (e.g., .)")
    ap.add_argument("--arm", required=True, help="Arm letter (e.g., G)")
    ap.add_argument("--rep1_run_tag", required=True)
    ap.add_argument("--rep2_run_tag", required=True)
    ap.add_argument("--output", required=True, help="Markdown output path")
    args = ap.parse_args()

    base_dir = Path(args.base_dir).resolve()
    arm = str(args.arm).strip()
    rep1_run_tag = str(args.rep1_run_tag).strip()
    rep2_run_tag = str(args.rep2_run_tag).strip()

    p1 = base_dir / "2_Data" / "metadata" / "generated" / rep1_run_tag / f"s5_validation__arm{arm}.jsonl"
    p2 = base_dir / "2_Data" / "metadata" / "generated" / rep2_run_tag / f"s5_validation__arm{arm}.jsonl"
    if not p1.exists():
        raise SystemExit(f"Missing S5 validation file: {p1}")
    if not p2.exists():
        raise SystemExit(f"Missing S5 validation file: {p2}")

    rows1 = _dedupe_latest_by_group(_read_jsonl(p1))
    rows2 = _dedupe_latest_by_group(_read_jsonl(p2))

    rep1_groups, rep1_tax, rep1_backlog = _compute_endpoints_per_group(rows1)
    rep2_groups, rep2_tax, rep2_backlog = _compute_endpoints_per_group(rows2)

    # Extract judge information
    rep1_judge_info = _extract_judge_info(rows1)
    rep2_judge_info = _extract_judge_info(rows2)

    md = build_markdown(
        arm=arm,
        rep1_run_tag=rep1_run_tag,
        rep2_run_tag=rep2_run_tag,
        rep1=rep1_groups,
        rep2=rep2_groups,
        rep1_tax=rep1_tax,
        rep2_tax=rep2_tax,
        rep1_backlog=rep1_backlog,
        rep2_backlog=rep2_backlog,
        rep1_judge_info=rep1_judge_info,
        rep2_judge_info=rep2_judge_info,
    )

    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = base_dir / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()



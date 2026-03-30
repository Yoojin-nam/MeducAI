"""
MeducAI Step05 (S5) — Validation Report Generator

Purpose:
- Summarize S5 validation outputs into a human-readable Markdown report.
- Designed for MI-CLEAR-LLM style auditability: clear counts, blocking items, and issue taxonomy.

Inputs:
- 2_Data/metadata/generated/{run_tag}/s5_validation__arm{arm}.jsonl

Outputs (default):
- 2_Data/metadata/generated/{run_tag}/reports/s5_report__arm{arm}.md

Notes:
- S5 output may contain multiple lines per group due to repeated runs.
  This script deduplicates by group_id keeping the latest validation_timestamp by default.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set


def _parse_iso(ts: str) -> Optional[datetime]:
    ts = (ts or "").strip()
    if not ts:
        return None
    # Accept "Z"
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


def _safe_get(d: Dict[str, Any], path: List[str], default: Any = None) -> Any:
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


@dataclass(frozen=True)
class GroupSummary:
    group_id: str
    ts: str
    s1_blocking: bool
    s1_ta: float
    s1_eq: int
    s1_issue_count: int
    s2_total: int
    s2_blocking: int
    s2_mean_ta: float
    s2_mean_eq: float


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
    return [v[1] for v in sorted(best.values(), key=lambda x: (x[0] is None, x[0]))]


def _collect_issue_types(issues: List[Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for it in issues:
        if not isinstance(it, dict):
            continue
        t = str(it.get("type") or "").strip() or "UNKNOWN"
        counts[t] = counts.get(t, 0) + 1
    return counts


def _collect_issue_field_counts(issues: List[Any], field: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for it in issues:
        if not isinstance(it, dict):
            continue
        v = str(it.get(field) or "").strip() or "UNKNOWN"
        counts[v] = counts.get(v, 0) + 1
    return counts


def _merge_counts(a: Dict[str, int], b: Dict[str, int]) -> Dict[str, int]:
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0) + int(v)
    return out


def _top_k(counts: Dict[str, int], k: int = 10) -> List[Tuple[str, int]]:
    return sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:k]


def build_report_md(
    *,
    run_tag: str,
    arm: str,
    src_path: Path,
    rows_latest: List[Dict[str, Any]],
) -> str:
    summaries: List[GroupSummary] = []
    s1_issue_types: Dict[str, int] = {}
    s2_issue_types: Dict[str, int] = {}
    s1_issue_codes: Dict[str, int] = {}
    s2_issue_codes: Dict[str, int] = {}
    s1_fix_targets: Dict[str, int] = {}
    s2_fix_targets: Dict[str, int] = {}
    total_s2_cards = 0
    total_s2_blocking = 0
    total_s1_blocking = 0

    # Difficulty (optional; per-card)
    s2_difficulty_vals: List[float] = []
    s2_difficulty_counts: Dict[str, int] = {}

    blocking_cards: List[Dict[str, Any]] = []
    blocking_tables: List[Dict[str, Any]] = []

    # Image evaluation statistics
    total_card_images = 0
    total_card_images_blocking = 0
    card_image_anatomical_accuracy_vals: List[float] = []
    card_image_prompt_compliance_vals: List[float] = []
    card_image_text_consistency_vals: List[float] = []
    card_image_quality_vals: List[int] = []
    card_image_issue_types: Dict[str, int] = {}
    card_image_issue_codes: Dict[str, int] = {}
    
    total_table_visuals = 0
    total_table_visuals_blocking = 0
    table_visual_info_clarity_vals: List[int] = []
    table_visual_anatomical_accuracy_vals: List[float] = []
    table_visual_prompt_compliance_vals: List[float] = []
    table_visual_consistency_vals: List[float] = []
    table_visual_issue_types: Dict[str, int] = {}
    table_visual_issue_codes: Dict[str, int] = {}

    # Actionable backlog: fix_target -> issue_code -> {count, hints}
    backlog: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for r in rows_latest:
        gid = str(r.get("group_id") or "").strip()
        ts = str(r.get("validation_timestamp") or "").strip()

        s1 = _safe_get(r, ["s1_table_validation"], {}) or {}
        s2 = _safe_get(r, ["s2_cards_validation"], {}) or {}
        s2_summary = _safe_get(s2, ["summary"], {}) or {}

        s1_blocking = bool(s1.get("blocking_error", False))
        s1_ta = float(s1.get("technical_accuracy", 0.0) or 0.0)
        s1_eq = int(s1.get("educational_quality", 0) or 0)
        s1_issues_raw = s1.get("issues")
        s1_issues: List[Any] = s1_issues_raw if isinstance(s1_issues_raw, list) else []

        s2_total = int(s2_summary.get("total_cards", 0) or 0)
        s2_blocking = int(s2_summary.get("blocking_errors", 0) or 0)
        s2_mean_ta = float(s2_summary.get("mean_technical_accuracy", 0.0) or 0.0)
        s2_mean_eq = float(s2_summary.get("mean_educational_quality", 0.0) or 0.0)

        summaries.append(
            GroupSummary(
                group_id=gid,
                ts=ts,
                s1_blocking=s1_blocking,
                s1_ta=s1_ta,
                s1_eq=s1_eq,
                s1_issue_count=len(s1_issues),
                s2_total=s2_total,
                s2_blocking=s2_blocking,
                s2_mean_ta=s2_mean_ta,
                s2_mean_eq=s2_mean_eq,
            )
        )

        if s1_blocking:
            blocking_tables.append(r)
            total_s1_blocking += 1

        s1_issue_types = _merge_counts(s1_issue_types, _collect_issue_types(s1_issues))
        s1_issue_codes = _merge_counts(s1_issue_codes, _collect_issue_field_counts(s1_issues, "issue_code"))
        s1_fix_targets = _merge_counts(s1_fix_targets, _collect_issue_field_counts(s1_issues, "recommended_fix_target"))

        # Backlog collection (S1)
        for it in s1_issues:
            if not isinstance(it, dict):
                continue
            tgt = str(it.get("recommended_fix_target") or "").strip() or "UNKNOWN"
            code = str(it.get("issue_code") or "").strip() or "UNKNOWN"
            hint = str(it.get("prompt_patch_hint") or "").strip()
            backlog.setdefault(tgt, {}).setdefault(code, {"count": 0, "hints": set()})
            backlog[tgt][code]["count"] += 1
            if hint:
                # store unique hints
                hints_set = backlog[tgt][code].get("hints")
                if isinstance(hints_set, set):
                    hints_set.add(hint)

        s2_cards = _safe_get(s2, ["cards"], []) or []
        if isinstance(s2_cards, list):
            for c in s2_cards:
                if isinstance(c, dict) and bool(c.get("blocking_error", False)):
                    blocking_cards.append({"group_id": gid, **c})

                # Difficulty (optional)
                if isinstance(c, dict) and ("difficulty" in c):
                    try:
                        dv = float(c.get("difficulty"))  # type: ignore[arg-type]
                        if dv in (0.0, 0.5, 1.0):
                            s2_difficulty_vals.append(dv)
                            k = f"{dv:.1f}"
                            s2_difficulty_counts[k] = s2_difficulty_counts.get(k, 0) + 1
                    except Exception:
                        # Ignore invalid values (validator should normalize/drop)
                        pass
                
                # Collect card image validation data
                card_image_val = c.get("card_image_validation")
                if card_image_val and isinstance(card_image_val, dict):
                    total_card_images += 1
                    if bool(card_image_val.get("blocking_error", False)):
                        total_card_images_blocking += 1
                    card_image_anatomical_accuracy_vals.append(float(card_image_val.get("anatomical_accuracy", 1.0)))
                    card_image_prompt_compliance_vals.append(float(card_image_val.get("prompt_compliance", 1.0)))
                    card_image_text_consistency_vals.append(float(card_image_val.get("text_image_consistency", 1.0)))
                    card_image_quality_vals.append(int(card_image_val.get("image_quality", 5)))
                    img_issues = card_image_val.get("issues", [])
                    if isinstance(img_issues, list):
                        card_image_issue_types = _merge_counts(card_image_issue_types, _collect_issue_types(img_issues))
                        card_image_issue_codes = _merge_counts(card_image_issue_codes, _collect_issue_field_counts(img_issues, "issue_code"))
                        # Add image issues to backlog
                        for it in img_issues:
                            if not isinstance(it, dict):
                                continue
                            tgt = str(it.get("recommended_fix_target") or "").strip() or "UNKNOWN"
                            code = str(it.get("issue_code") or "").strip() or "UNKNOWN"
                            hint = str(it.get("prompt_patch_hint") or "").strip()
                            backlog.setdefault(tgt, {}).setdefault(code, {"count": 0, "hints": set()})
                            backlog[tgt][code]["count"] += 1
                            if hint:
                                hints_set = backlog[tgt][code].get("hints")
                                if isinstance(hints_set, set):
                                    hints_set.add(hint)
        
        s2_issues_all: List[Any] = []
        if isinstance(s2_cards, list):
            for c in s2_cards:
                if isinstance(c, dict) and isinstance(c.get("issues"), list):
                    s2_issues_all.extend(c.get("issues") or [])
        s2_issue_types = _merge_counts(s2_issue_types, _collect_issue_types(s2_issues_all))
        s2_issue_codes = _merge_counts(s2_issue_codes, _collect_issue_field_counts(s2_issues_all, "issue_code"))
        s2_fix_targets = _merge_counts(s2_fix_targets, _collect_issue_field_counts(s2_issues_all, "recommended_fix_target"))

        # Backlog collection (S2)
        for it in s2_issues_all:
            if not isinstance(it, dict):
                continue
            tgt = str(it.get("recommended_fix_target") or "").strip() or "UNKNOWN"
            code = str(it.get("issue_code") or "").strip() or "UNKNOWN"
            hint = str(it.get("prompt_patch_hint") or "").strip()
            backlog.setdefault(tgt, {}).setdefault(code, {"count": 0, "hints": set()})
            backlog[tgt][code]["count"] += 1
            if hint:
                hints_set = backlog[tgt][code].get("hints")
                if isinstance(hints_set, set):
                    hints_set.add(hint)
        
        # Collect table visual validation data
        table_visual_val = s1.get("table_visual_validation")
        if table_visual_val and isinstance(table_visual_val, dict):
            total_table_visuals += 1
            if bool(table_visual_val.get("blocking_error", False)):
                total_table_visuals_blocking += 1
            table_visual_info_clarity_vals.append(int(table_visual_val.get("information_clarity", 5)))
            table_visual_anatomical_accuracy_vals.append(float(table_visual_val.get("anatomical_accuracy", 1.0)))
            table_visual_prompt_compliance_vals.append(float(table_visual_val.get("prompt_compliance", 1.0)))
            table_visual_consistency_vals.append(float(table_visual_val.get("table_visual_consistency", 1.0)))
            visual_issues = table_visual_val.get("issues", [])
            if isinstance(visual_issues, list):
                table_visual_issue_types = _merge_counts(table_visual_issue_types, _collect_issue_types(visual_issues))
                table_visual_issue_codes = _merge_counts(table_visual_issue_codes, _collect_issue_field_counts(visual_issues, "issue_code"))
                # Add visual issues to backlog
                for it in visual_issues:
                    if not isinstance(it, dict):
                        continue
                    tgt = str(it.get("recommended_fix_target") or "").strip() or "UNKNOWN"
                    code = str(it.get("issue_code") or "").strip() or "UNKNOWN"
                    hint = str(it.get("prompt_patch_hint") or "").strip()
                    backlog.setdefault(tgt, {}).setdefault(code, {"count": 0, "hints": set()})
                    backlog[tgt][code]["count"] += 1
                    if hint:
                        hints_set = backlog[tgt][code].get("hints")
                        if isinstance(hints_set, set):
                            hints_set.add(hint)

        total_s2_cards += s2_total
        total_s2_blocking += s2_blocking

    # means
    s1_eq_vals = [s.s1_eq for s in summaries if s.s1_eq > 0]
    s1_ta_vals = [s.s1_ta for s in summaries if s.s1_ta > 0]
    s2_eq_vals = [s.s2_mean_eq for s in summaries if s.s2_mean_eq > 0]
    s2_ta_vals = [s.s2_mean_ta for s in summaries if s.s2_mean_ta > 0]

    def mean(xs: List[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    md: List[str] = []
    md.append(f"# S5 Validation Report (Run: `{run_tag}`, Arm: `{arm}`)\n")
    md.append(f"- **Source**: `{src_path}`\n")
    md.append(f"- **Records (latest per group)**: {len(rows_latest)}\n")

    md.append("\n## Summary\n")
    md.append(f"- **S1 blocking tables**: {total_s1_blocking}/{len(rows_latest)}\n")
    md.append(f"- **S1 mean technical accuracy**: {mean(s1_ta_vals):.2f}\n")
    md.append(f"- **S1 mean educational quality**: {mean([float(x) for x in s1_eq_vals]):.2f}\n")
    md.append(f"- **S2 total cards validated**: {total_s2_cards}\n")
    md.append(f"- **S2 blocking cards**: {total_s2_blocking}/{total_s2_cards} ({(100.0*total_s2_blocking/total_s2_cards):.1f}% if total>0 else 0)\n" if total_s2_cards else "- **S2 blocking cards**: 0/0\n")
    md.append(f"- **S2 mean technical accuracy (group means)**: {mean(s2_ta_vals):.2f}\n")
    md.append(f"- **S2 mean educational quality (group means)**: {mean(s2_eq_vals):.2f}\n")

    # Difficulty summary (optional)
    if len(s2_difficulty_vals) > 0:
        md.append(f"- **S2 mean difficulty (card-level)**: {mean(s2_difficulty_vals):.3f} (n={len(s2_difficulty_vals)})\n")
        parts: List[str] = []
        for k in ["0.0", "0.5", "1.0"]:
            if k in s2_difficulty_counts:
                parts.append(f"{k}: {s2_difficulty_counts[k]}")
        if parts:
            md.append(f"- **S2 difficulty distribution**: {', '.join(parts)}\n")
    else:
        md.append("- **S2 difficulty**: (not available in S5 outputs)\n")
    
    # Image evaluation summary
    if total_card_images > 0:
        md.append(f"- **Card images evaluated**: {total_card_images}\n")
        md.append(f"- **Card images with blocking errors**: {total_card_images_blocking}/{total_card_images} ({(100.0*total_card_images_blocking/total_card_images):.1f}%)\n")
        md.append(f"- **Card images mean anatomical accuracy**: {mean(card_image_anatomical_accuracy_vals):.2f}\n")
        md.append(f"- **Card images mean prompt compliance**: {mean(card_image_prompt_compliance_vals):.2f}\n")
        md.append(f"- **Card images mean text-image consistency**: {mean(card_image_text_consistency_vals):.2f}\n")
        md.append(f"- **Card images mean quality**: {mean([float(x) for x in card_image_quality_vals]):.2f}\n")
    
    if total_table_visuals > 0:
        md.append(f"- **Table visuals evaluated**: {total_table_visuals}\n")
        md.append(f"- **Table visuals with blocking errors**: {total_table_visuals_blocking}/{total_table_visuals} ({(100.0*total_table_visuals_blocking/total_table_visuals):.1f}%)\n")
        md.append(f"- **Table visuals mean information clarity**: {mean([float(x) for x in table_visual_info_clarity_vals]):.2f}\n")
        md.append(f"- **Table visuals mean anatomical accuracy**: {mean(table_visual_anatomical_accuracy_vals):.2f}\n")
        md.append(f"- **Table visuals mean prompt compliance**: {mean(table_visual_prompt_compliance_vals):.2f}\n")
        md.append(f"- **Table visuals mean table-visual consistency**: {mean(table_visual_consistency_vals):.2f}\n")

    md.append("\n## Per-group summary (latest)\n")
    md.append("| group_id | validation_timestamp | S1_blocking | S1_TA | S1_EQ | S1_issues | S2_total | S2_blocking |\n")
    md.append("|---|---|---:|---:|---:|---:|---:|---:|\n")
    for s in summaries:
        md.append(
            f"| `{s.group_id}` | {s.ts or ''} | {str(s.s1_blocking)} | {s.s1_ta:.1f} | {s.s1_eq} | {s.s1_issue_count} | {s.s2_total} | {s.s2_blocking} |\n"
        )

    md.append("\n## Issue taxonomy (top)\n")
    md.append("\n### S1 issue types\n")
    for k, v in _top_k(s1_issue_types, 15):
        md.append(f"- **{k}**: {v}\n")

    md.append("\n### S2 issue types\n")
    for k, v in _top_k(s2_issue_types, 15):
        md.append(f"- **{k}**: {v}\n")

    md.append("\n### S1 issue codes (optional; top)\n")
    for k, v in _top_k(s1_issue_codes, 15):
        md.append(f"- **{k}**: {v}\n")

    md.append("\n### S2 issue codes (optional; top)\n")
    for k, v in _top_k(s2_issue_codes, 15):
        md.append(f"- **{k}**: {v}\n")

    md.append("\n### S1 recommended_fix_target (optional; top)\n")
    for k, v in _top_k(s1_fix_targets, 15):
        md.append(f"- **{k}**: {v}\n")

    md.append("\n### S2 recommended_fix_target (optional; top)\n")
    for k, v in _top_k(s2_fix_targets, 15):
        md.append(f"- **{k}**: {v}\n")
    
    # Image issue taxonomy
    if total_card_images > 0:
        md.append("\n### Card image issue types (optional; top)\n")
        for k, v in _top_k(card_image_issue_types, 15):
            md.append(f"- **{k}**: {v}\n")
        
        md.append("\n### Card image issue codes (optional; top)\n")
        for k, v in _top_k(card_image_issue_codes, 15):
            md.append(f"- **{k}**: {v}\n")
    
    if total_table_visuals > 0:
        md.append("\n### Table visual issue types (optional; top)\n")
        for k, v in _top_k(table_visual_issue_types, 15):
            md.append(f"- **{k}**: {v}\n")
        
        md.append("\n### Table visual issue codes (optional; top)\n")
        for k, v in _top_k(table_visual_issue_codes, 15):
            md.append(f"- **{k}**: {v}\n")

    md.append("\n## Blocking items (latest)\n")
    md.append("\n### Blocking S1 tables\n")
    if not blocking_tables:
        md.append("- (none)\n")
    else:
        for r in blocking_tables:
            gid = str(r.get("group_id") or "")
            s1 = _safe_get(r, ["s1_table_validation"], {}) or {}
            md.append(f"- **group_id** `{gid}`: {s1.get('description', '')}\n")

    md.append("\n### Blocking S2 cards\n")
    if not blocking_cards:
        md.append("- (none)\n")
    else:
        for c in blocking_cards:
            gid = str(c.get("group_id") or "")
            cid = str(c.get("card_id") or "")
            role = str(c.get("card_role") or "")
            issues_raw = c.get("issues")
            issues: List[Any] = issues_raw if isinstance(issues_raw, list) else []
            md.append(f"- **group_id** `{gid}` / **card_id** `{cid}` / **role** `{role}`\n")
            for it in issues[:3]:
                if not isinstance(it, dict):
                    continue
                md.append(f"  - **[{it.get('severity','')}] {it.get('type','')}**: {str(it.get('description','')).strip()}\n")
                if it.get("suggested_fix"):
                    md.append(f"    - **suggested_fix**: {str(it.get('suggested_fix')).strip()}\n")
            ev_raw = c.get("rag_evidence")
            ev: List[Any] = ev_raw if isinstance(ev_raw, list) else []
            if len(ev) > 0:
                md.append("  - **evidence (first)**:\n")
                e0: Dict[str, Any] = ev[0] if isinstance(ev[0], dict) else {}
                md.append(f"    - source_id: `{str(e0.get('source_id',''))}`\n")
                md.append(f"    - excerpt: {str(e0.get('source_excerpt',''))}\n")

    md.append("\n## Recommended improvements (for schema & prompts)\n")
    md.append(
        "- **Schema (S5 output)**: consider adding explicit `run_tag` (top-level) and `inputs` (paths/hashes) for traceability. "
        "This makes MI-CLEAR-LLM audit easier than relying only on `s5_snapshot_id`.\n"
    )
    md.append(
        "- **Prompts (S5 validator)**: add explicit format checks for MCQ cards (options presence, correct_index validity, consistent rationale). "
        "Many blocking errors are structural/format rather than medical content.\n"
    )
    md.append(
        "- **Upstream prompts (S2 generation)**: reinforce MCQ schema constraints: if `card_type=MCQ`, output MUST include `options[]` (exactly 5) + `correct_index` (0–4). "
        "Options do not need to be duplicated in `front` (Anki convention).\n"
    )
    md.append(
        "- **Operational**: always dedupe by latest `validation_timestamp` for analysis; repeated runs append multiple lines.\n"
    )

    # Actionable patch backlog (optional)
    md.append("\n## Patch backlog (actionable; optional)\n")
    md.append(
        "This section is generated only if S5 outputs include `issue_code` / `recommended_fix_target` / `prompt_patch_hint`.\n"
    )
    # Sort targets by total count (descending), keep top 10
    target_counts: List[Tuple[str, int]] = []
    for tgt, by_code in backlog.items():
        total = sum(int(v.get("count", 0) or 0) for v in by_code.values() if isinstance(v, dict))
        target_counts.append((tgt, total))
    for tgt, total in sorted(target_counts, key=lambda x: (-x[1], x[0]))[:10]:
        md.append(f"\n### Target: `{tgt}` (n={total})\n")
        by_code = backlog.get(tgt, {})
        # sort codes by count
        code_counts: List[Tuple[str, int]] = []
        for code, payload in by_code.items():
            if not isinstance(payload, dict):
                continue
            code_counts.append((code, int(payload.get("count", 0) or 0)))
        for code, cnt in sorted(code_counts, key=lambda x: (-x[1], x[0]))[:8]:
            md.append(f"- **{code}**: {cnt}\n")
            payload = by_code.get(code, {})
            hints_list: List[str] = []
            if isinstance(payload, dict):
                raw_hints = payload.get("hints")
                if isinstance(raw_hints, set):
                    hints_list = sorted([str(x) for x in raw_hints])
            for h in hints_list[:3]:
                md.append(f"  - patch_hint: {h}\n")

    return "".join(md).strip() + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description="MeducAI S5 validation report generator")
    p.add_argument("--base_dir", required=True, type=str)
    p.add_argument("--run_tag", required=True, type=str)
    p.add_argument("--arm", required=True, type=str)
    p.add_argument("--input", default=None, type=str, help="Override input s5_validation jsonl path")
    p.add_argument("--output_md", default=None, type=str, help="Override output report path")
    p.add_argument("--keep_all", action="store_true", help="Do not dedupe; report on all lines (debug)")
    args = p.parse_args()

    base_dir = Path(args.base_dir).resolve()
    run_tag = str(args.run_tag).strip()
    arm = str(args.arm).strip().upper()

    data_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    src_path = Path(args.input).resolve() if args.input else (data_dir / f"s5_validation__arm{arm}.jsonl")
    if not src_path.exists():
        raise SystemExit(f"Input not found: {src_path}")

    rows = _read_jsonl(src_path)
    rows_latest = rows if args.keep_all else _dedupe_latest_by_group(rows)

    report_md = build_report_md(run_tag=run_tag, arm=arm, src_path=src_path, rows_latest=rows_latest)

    out_path = Path(args.output_md).resolve() if args.output_md else (data_dir / "reports" / f"s5_report__arm{arm}.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_md, encoding="utf-8")
    print(f"✓ Wrote report: {out_path}")


if __name__ == "__main__":
    main()



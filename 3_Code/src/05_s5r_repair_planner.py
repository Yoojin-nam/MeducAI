#!/usr/bin/env python3
"""
MeducAI Step05R (S5R) — Repair Planner (Option C)
-------------------------------------------------
Reads baseline S5 validation outputs and produces a deterministic, one-shot repair plan
to be consumed by S1R/S2R regeneration.

Key constraints (per protocol):
- Baseline artifacts are immutable (read-only). This script only *plans* repairs.
- Output is additive: `s5_repair_plan__arm{arm}.jsonl`
- One record per `group_id`
- Evidence discipline: if the plan asserts blocking/factual fixes, attach evidence
  (prefer S5 RAG evidence; fallback to issue excerpts).

This is intentionally non-LLM and deterministic: it converts S5 structured issues into
clear repair instructions and guardrails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from tools.path_resolver import resolve_s2_results_path
except Exception:
    resolve_s2_results_path = None  # type: ignore


SCHEMA_VERSION = "S5R_REPAIR_PLAN_v1.0"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _stable_hash(obj: Any) -> str:
    """
    Deterministic SHA256 over JSON (sort_keys=True), used for lineage fields.
    """
    s = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _safe_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def _safe_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _as_bool(v: Any) -> Optional[bool]:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        if v == 0:
            return False
        if v == 1:
            return True
        return None
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("1", "true", "yes", "y"):
            return True
        if s in ("0", "false", "no", "n"):
            return False
    return None


def _as_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return float(s)
        except Exception:
            return None
    return None


def _is_blocking_or_factual_issue(issue: Any) -> bool:
    if not isinstance(issue, dict):
        return False
    sev = str(issue.get("severity") or "").strip().lower()
    t = str(issue.get("type") or "").strip().lower()
    code = str(issue.get("issue_code") or "").strip()
    if code.startswith("FATAL_"):
        return True
    if sev == "blocking":
        return True
    # Conservative mapping: anything explicitly about accuracy/factual/clinical risk
    if any(k in t for k in ("factual", "accuracy", "medical", "clinical", "guideline", "dosage", "contra")):
        return True
    return False


def _action_type_from_issue(issue: Dict[str, Any], *, default: str) -> str:
    code = str(issue.get("issue_code") or "").upper()
    t = str(issue.get("type") or "").lower()
    desc = str(issue.get("description") or "").lower()
    if code.startswith("FATAL_") or "clinical" in t or "guideline" in t:
        return "fix_clinical_safety"
    if "factual" in t or "accuracy" in t or "medical_false" in t:
        return "fix_factual"
    if "correct_index" in code or "correct index" in desc:
        return "fix_correct_index"
    if "missing" in code and "option" in code:
        return "add_missing_options"
    if "format" in t or "schema" in t or "json" in desc:
        return "fix_format"
    if "ambigu" in t or "clarity" in t or "clar" in desc:
        return "improve_clarity"
    return default


def _build_instruction(issue: Dict[str, Any]) -> str:
    """
    Keep this short and generator-friendly (1-3 lines).
    """
    desc = str(issue.get("description") or "").strip()
    hint = str(issue.get("prompt_patch_hint") or "").strip()
    lines: List[str] = []
    if desc:
        lines.append(desc)
    if hint:
        lines.append(f"Hint: {hint}")
    if not lines:
        lines.append("Fix the reported issue conservatively without introducing new content.")
    return "\n".join(lines[:3])


def _ensure_evidence(
    *,
    evidence: List[Any],
    issues: List[Dict[str, Any]],
    fallback_context: Optional[str] = None,
) -> List[Any]:
    """
    Evidence discipline: if we claim blocking/factual fixes, attach evidence.
    Prefer existing evidence objects; otherwise fall back to issue excerpt(s).
    """
    if evidence:
        return evidence
    excerpts: List[Dict[str, Any]] = []
    for it in issues:
        if not isinstance(it, dict):
            continue
        if _is_blocking_or_factual_issue(it):
            desc = str(it.get("description") or "").strip()
            code = str(it.get("issue_code") or "").strip()
            if desc:
                excerpts.append(
                    {
                        "source_id": f"S5_ISSUE::{code or 'UNKNOWN'}",
                        "source_excerpt": desc[:800],
                        "relevance": "blocking_or_factual_issue_excerpt",
                    }
                )
        if len(excerpts) >= 3:
            break
    if not excerpts and fallback_context:
        excerpts.append(
            {
                "source_id": "S5R_FALLBACK_CONTEXT",
                "source_excerpt": str(fallback_context)[:800],
                "relevance": "fallback_context",
            }
        )
    return excerpts


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
    # Stable ordering
    return [v[1] for v in sorted(best.values(), key=lambda x: (x[0] is None, x[0], str(x[1].get("group_id") or "")))]


def _index_s1_by_group(path: Path) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for r in _read_jsonl(path):
        gid = str(r.get("group_id") or "").strip()
        if gid:
            out[gid] = r
    return out


def _index_s2_by_group(path: Path) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for r in _read_jsonl(path):
        gid = str(r.get("group_id") or "").strip()
        if not gid:
            continue
        out.setdefault(gid, []).append(r)
    return out


@dataclass(frozen=True)
class PlanBuildCtx:
    run_tag: str
    arm: str
    base_dir: Path
    s1_path: Path
    s2_path: Path
    s5_path: Path


def build_repair_plan_for_group(
    *,
    s5_record: Dict[str, Any],
    ctx: PlanBuildCtx,
    s1_struct_by_group: Dict[str, Dict[str, Any]],
    s2_entities_by_group: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    gid = str(s5_record.get("group_id") or "").strip()
    t0 = time.time()
    started_at = _utc_now_iso()

    errors: List[str] = []

    # --- Baseline lineage hashes (per group) ---
    s1_struct = s1_struct_by_group.get(gid)
    if not s1_struct:
        errors.append("Missing baseline S1 struct for group_id")
    baseline_s1_hash = _stable_hash(s1_struct) if s1_struct else None

    s2_entities = s2_entities_by_group.get(gid, [])
    if not s2_entities:
        errors.append("Missing baseline S2 entities for group_id")
    # Stable hash over sorted entity list (by entity_id/name fallback)
    s2_entities_sorted = sorted(
        [e for e in s2_entities if isinstance(e, dict)],
        key=lambda x: (str(x.get("entity_id") or ""), str(x.get("entity_name") or "")),
    )
    baseline_s2_hash = _stable_hash(s2_entities_sorted) if s2_entities_sorted else None

    s5_snapshot_id = str(s5_record.get("s5_snapshot_id") or "").strip()
    if not s5_snapshot_id:
        # Fallback: hash the full record
        s5_snapshot_id = f"s5_missing_{_stable_hash(s5_record)[:12]}"
        errors.append("Missing s5_snapshot_id in S5 record; used fallback hash id")

    # --- S1 actions ---
    s1 = _safe_dict(s5_record.get("s1_table_validation"))
    s1_issues_raw = _safe_list(s1.get("issues"))
    s1_issues: List[Dict[str, Any]] = [it for it in s1_issues_raw if isinstance(it, dict)]
    s1_rag_evidence = _safe_list(s1.get("rag_evidence"))

    s1_actions: List[Dict[str, Any]] = []
    for idx, it in enumerate(s1_issues):
        action_type = _action_type_from_issue(it, default="fix_table_issue")
        instruction = _build_instruction(it)
        needs_evidence = _is_blocking_or_factual_issue(it) or (_as_bool(s1.get("blocking_error")) is True)
        evidence_out = s1_rag_evidence if needs_evidence else []
        if needs_evidence:
            evidence_out = _ensure_evidence(
                evidence=evidence_out,
                issues=[it],
                fallback_context=f"S1 issue for group {gid}",
            )
        s1_actions.append(
            {
                "action_id": f"s1_{idx+1}",
                "action_type": action_type,
                "target": {
                    "recommended_fix_target": it.get("recommended_fix_target"),
                    "issue_code": it.get("issue_code"),
                },
                "instruction": instruction,
                "evidence": evidence_out,
            }
        )

    # --- S2 actions (per card) ---
    s2 = _safe_dict(s5_record.get("s2_cards_validation"))
    cards_raw = _safe_list(s2.get("cards"))
    cards: List[Dict[str, Any]] = [c for c in cards_raw if isinstance(c, dict)]

    s2_actions: List[Dict[str, Any]] = []
    s2_action_idx = 0
    for c in cards:
        issues_raw = _safe_list(c.get("issues"))
        issues: List[Dict[str, Any]] = [it for it in issues_raw if isinstance(it, dict)]
        blocking = _as_bool(c.get("blocking_error")) is True
        ta = _as_float(c.get("technical_accuracy"))
        ta_zero = ta is not None and ta == 0.0

        # Also consider image blocking signals (best-effort).
        card_img_val = _safe_dict(c.get("card_image_validation"))
        img_blocking = _as_bool(card_img_val.get("blocking_error")) is True
        img_safety = _as_bool(card_img_val.get("safety_flag")) is True

        needs_action = bool(issues) or blocking or ta_zero or img_blocking or img_safety
        if not needs_action:
            continue

        # Determine action type (worst-first)
        action_type = "fix_card_issue"
        if blocking or ta_zero or any(_is_blocking_or_factual_issue(it) for it in issues):
            action_type = "fix_blocking_or_factual"
        elif any("missing" in str(it.get("issue_code") or "").lower() for it in issues):
            action_type = "add_missing_components"
        elif any("clar" in str(it.get("type") or "").lower() for it in issues):
            action_type = "improve_clarity"
        if img_blocking or img_safety:
            action_type = "fix_image_related_issue"

        card_id = str(c.get("card_id") or "").strip()
        card_role = str(c.get("card_role") or "").strip()
        entity_id = str(c.get("entity_id") or "").strip()
        entity_name = str(c.get("entity_name") or "").strip()

        # Build instruction: compact rollup per card
        issue_summaries = []
        for it in issues[:5]:
            code = str(it.get("issue_code") or "UNKNOWN").strip()
            desc = str(it.get("description") or "").strip()
            if desc:
                issue_summaries.append(f"- ({code}) {desc}")
            else:
                issue_summaries.append(f"- ({code})")
        if img_blocking or img_safety:
            issue_summaries.append("- (IMAGE) Fix image-related blocking/safety/answerability issues per spec; do not add new claims.")
        if not issue_summaries and (blocking or ta_zero):
            issue_summaries.append("- Fix blocking/accuracy issues conservatively.")

        instruction_lines = [
            "Fix the following S5-reported issues for this card (keep scope minimal; no new content):",
            *issue_summaries[:6],
        ]
        instruction = "\n".join(instruction_lines[:8])

        # Evidence discipline: required for blocking/factual plans
        needs_evidence = blocking or ta_zero or any(_is_blocking_or_factual_issue(it) for it in issues)
        evidence_in = _safe_list(c.get("rag_evidence")) if needs_evidence else []
        if needs_evidence:
            evidence_in = _ensure_evidence(
                evidence=evidence_in,
                issues=issues,
                fallback_context=f"S2 card issue card_id={card_id} group={gid}",
            )

        s2_action_idx += 1
        s2_actions.append(
            {
                "action_id": f"s2_{s2_action_idx}",
                "target_card_id": card_id or None,
                "card_role": card_role or None,
                "entity_id": entity_id or None,
                "entity_name": entity_name or None,
                "action_type": action_type,
                "instruction": instruction,
                "issue_codes": sorted({str(it.get("issue_code") or "UNKNOWN").strip() for it in issues}) if issues else [],
                "evidence": evidence_in,
            }
        )

    # --- Guardrails / summary ---
    created_at = _utc_now_iso()
    baseline_snapshot_id = None
    if baseline_s1_hash or baseline_s2_hash:
        baseline_snapshot_id = f"base_{ctx.run_tag}_{gid}_{ctx.arm}_{_stable_hash({'s1': baseline_s1_hash, 's2': baseline_s2_hash})[:12]}"

    plan_core = {
        "schema_version": SCHEMA_VERSION,
        "created_at": created_at,
        "run_tag": ctx.run_tag,
        "arm": ctx.arm,
        "group_id": gid,
        # Required lineage fields (top-level for easy downstream consumption)
        "s5_snapshot_id": s5_snapshot_id,
        "baseline_snapshot_id": baseline_snapshot_id,
        "baseline_s1_hash": baseline_s1_hash,
        "baseline_s2_hash": baseline_s2_hash,
        "inputs_used": {
            "s5_validation_path": str(ctx.s5_path.resolve().relative_to(ctx.base_dir)),
            "stage1_struct_path": str(ctx.s1_path.resolve().relative_to(ctx.base_dir)),
            "s2_results_path": str(ctx.s2_path.resolve().relative_to(ctx.base_dir)),
            "s5_snapshot_id": s5_snapshot_id,
            "baseline_snapshot_id": baseline_snapshot_id,
            "baseline_s1_hash": baseline_s1_hash,
            "baseline_s2_hash": baseline_s2_hash,
        },
        "repair_iteration": 1,
        "no_new_content_scope": True,
        "max_iteration": 1,
        "s1_actions": s1_actions,
        "s2_actions": s2_actions,
        "summary": {
            "s1_action_count": len(s1_actions),
            "s2_action_count": len(s2_actions),
            "needs_repair": bool(s1_actions or s2_actions),
        },
    }

    # Plan snapshot id (deterministic over plan content excluding timing fields)
    plan_snapshot_id = f"s5r_{ctx.run_tag}_{gid}_{ctx.arm}_{_stable_hash(plan_core)[:12]}"

    ended_at = _utc_now_iso()
    duration_ms = int((time.time() - t0) * 1000)

    plan = {
        **plan_core,
        "s5r_plan_id": plan_snapshot_id,
        "s5r_timing": {
            "start": started_at,
            "end": ended_at,
            "duration_ms": duration_ms,
        },
    }

    if errors:
        plan["errors"] = errors

    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description="S5R repair planner (Option C): produce s5_repair_plan JSONL")
    parser.add_argument("--base_dir", type=str, required=True, help="Project base dir (repo root)")
    parser.add_argument("--run_tag", type=str, required=True, help="RUN_TAG under 2_Data/metadata/generated/")
    parser.add_argument("--arm", type=str, required=True, help="Arm identifier (e.g., A/B/.../G)")
    parser.add_argument("--s1_arm", type=str, default=None, help="Optional S1 arm used to resolve S2 path (defaults to arm)")
    parser.add_argument("--s5_path", type=str, default=None, help="Override S5 validation jsonl path")
    parser.add_argument("--s1_path", type=str, default=None, help="Override baseline stage1_struct jsonl path")
    parser.add_argument("--s2_path", type=str, default=None, help="Override baseline s2_results jsonl path")
    parser.add_argument("--output_path", type=str, default=None, help="Output path (default: s5_repair_plan__arm{arm}.jsonl)")
    parser.add_argument("--only_group_id", type=str, default=None, help="Optional: generate plan for a single group_id")
    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    run_tag = str(args.run_tag).strip()
    arm = str(args.arm).strip().upper()
    s1_arm = str(args.s1_arm).strip().upper() if args.s1_arm else None

    data_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag

    s5_path = Path(args.s5_path).resolve() if args.s5_path else (data_dir / f"s5_validation__arm{arm}.jsonl")
    s1_path = Path(args.s1_path).resolve() if args.s1_path else (data_dir / f"stage1_struct__arm{arm}.jsonl")

    if args.s2_path:
        s2_path = Path(args.s2_path).resolve()
    else:
        if resolve_s2_results_path is None:
            s2_path = data_dir / f"s2_results__arm{arm}.jsonl"
        else:
            s2_path = resolve_s2_results_path(data_dir, arm, s1_arm=s1_arm)  # type: ignore[arg-type]

    output_path = Path(args.output_path).resolve() if args.output_path else (data_dir / f"s5_repair_plan__arm{arm}.jsonl")

    # Validate required inputs
    missing = []
    if not s5_path.exists():
        missing.append(f"S5 validation not found: {s5_path}")
    if not s1_path.exists():
        missing.append(f"Baseline S1 not found: {s1_path}")
    if not s2_path.exists():
        missing.append(f"Baseline S2 not found: {s2_path}")
    if missing:
        for m in missing:
            print(f"[S5R] ERROR: {m}", file=sys.stderr)
        sys.exit(2)

    # Load inputs
    s5_rows = _read_jsonl(s5_path)
    s5_latest = _dedupe_latest_by_group(s5_rows)
    if args.only_group_id:
        og = str(args.only_group_id).strip()
        s5_latest = [r for r in s5_latest if str(r.get("group_id") or "").strip() == og]

    s1_by_group = _index_s1_by_group(s1_path)
    s2_by_group = _index_s2_by_group(s2_path)

    ctx = PlanBuildCtx(
        run_tag=run_tag,
        arm=arm,
        base_dir=base_dir,
        s1_path=s1_path,
        s2_path=s2_path,
        s5_path=s5_path,
    )

    out_rows: List[Dict[str, Any]] = []
    for r in s5_latest:
        gid = str(r.get("group_id") or "").strip()
        if not gid:
            continue
        out_rows.append(
            build_repair_plan_for_group(
                s5_record=r,
                ctx=ctx,
                s1_struct_by_group=s1_by_group,
                s2_entities_by_group=s2_by_group,
            )
        )

    # Stable output ordering by group_id
    out_rows_sorted = sorted(out_rows, key=lambda x: str(x.get("group_id") or ""))
    _write_jsonl(output_path, out_rows_sorted)

    print(f"[S5R] Wrote {len(out_rows_sorted)} plan records to: {output_path}")
    # Quick summary for operator
    needs = sum(1 for r in out_rows_sorted if _safe_dict(r.get("summary")).get("needs_repair"))
    print(f"[S5R] Groups needing repair (any actions): {needs}/{len(out_rows_sorted)}")


if __name__ == "__main__":
    main()



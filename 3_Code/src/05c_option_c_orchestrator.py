#!/usr/bin/env python3
"""
MeducAI Option C Orchestrator (one-shot)
=======================================

Implements the Option C flow described in the attached rollout plan:
  baseline S5 -> trigger selection (hardTrigger OR score<threshold)
    -> S5R repair plan
    -> S2-only regeneration (entity-scoped when possible)
    -> S4 repaired image regeneration (subset; quality/missing/hard-trigger driven)
    -> S5 postrepair validation

Design goals
------------
- Safety-first: conservative triggering and no baseline overwrite.
- One-shot operator UX: a single command to run the pipeline for selected group(s).
- Non fail-fast: one group failure must not stop other groups; baseline fallback remains possible.

Artifacts (additive)
--------------------
- s5_repair_plan__arm{arm}__group{group_id}.jsonl     (per-group plan, created by orchestrator)
- s2_results__s1arm{s1_arm}__s2arm{arm}__repaired.jsonl  (written by 01_generate_json.py)
- s5_validation__arm{arm}__postrepair.jsonl          (appended by 05_s5_validator.py)
- optionc_orchestrator__arm{arm}__runlog.json         (run summary)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from tools.multi_agent.score_calculator import calculate_s5_regeneration_trigger_score


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


def _safe_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _safe_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


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


def _as_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return int(v)
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return int(float(s))
        except Exception:
            return None
    return None


def _path_exists_best_effort(p: Path, *, base_dir: Path) -> bool:
    """
    Treat absolute/relative string paths in manifests robustly.
    """
    try:
        if p.is_absolute():
            return p.exists() and p.stat().st_size > 0
    except Exception:
        pass
    try:
        rel = (base_dir / p).resolve()
        return rel.exists() and rel.stat().st_size > 0
    except Exception:
        return False


def _baseline_image_exists_on_disk(
    *,
    base_dir: Path,
    run_tag: str,
    group_id: str,
    entity_id: str,
    card_role: str,
) -> bool:
    """
    Fallback missing-image check when S4 manifest is absent.
    """
    fname = f"IMG__{run_tag}__{group_id}__{entity_id}__{card_role}.jpg"
    img_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag / "images"
    for ext in (".jpg", ".jpeg", ".png"):
        p = img_dir / fname.replace(".jpg", ext)
        try:
            if p.exists() and p.stat().st_size > 0:
                return True
        except Exception:
            continue
    return False


def _load_s4_card_manifest_index(*, manifest_path: Path) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    """
    Load S4 manifest and index card-image entries by (group_id, entity_id, card_role).
    """
    out: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    if not manifest_path.exists():
        return out
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            if not isinstance(entry, dict):
                continue
            gid = str(entry.get("group_id") or "").strip()
            eid = str(entry.get("entity_id") or "").strip()
            role = str(entry.get("card_role") or "").strip().upper()
            spec_kind = str(entry.get("spec_kind") or "").strip()
            if not (gid and eid and role):
                continue
            if spec_kind not in ("S2_CARD_IMAGE", "S2_CARD_CONCEPT"):
                continue
            out[(gid, eid, role)] = entry
    return out


def _extract_s4_image_targets_from_s5_group_record(
    *,
    group_record: Dict[str, Any],
    base_dir: Path,
    run_tag: str,
    s4_quality_threshold: int,
    s4_manifest_index: Optional[Dict[Tuple[str, str, str], Dict[str, Any]]] = None,
) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
    """
    Extract (entity_ids, card_roles) for S4 selective repaired regeneration from baseline S5 record.

    Target rules:
    - hard trigger: card_image_validation.blocking_error==true OR safety_flag==true
    - low quality: image_quality <= threshold
    - missing: baseline S4 manifest says generation_success=false OR file missing OR no manifest entry and file missing on disk
    """
    gid = str(group_record.get("group_id") or "").strip()
    s2 = _safe_dict(group_record.get("s2_cards_validation"))
    cards = _safe_list(s2.get("cards"))

    entity_ids_set: set[str] = set()
    card_roles_set: set[str] = set()
    reasons: List[Dict[str, Any]] = []

    for c in cards:
        if not isinstance(c, dict):
            continue
        # Some S5 JSONL variants may omit entity_id at the card level.
        # Fallback: parse entity_id from card_id format like "{entity_id}__{card_role}__{idx}".
        eid = str(c.get("entity_id") or "").strip()
        if not eid:
            cid = str(c.get("card_id") or "").strip()
            if "__" in cid:
                eid = cid.split("__", 1)[0].strip()
        role = str(c.get("card_role") or "").strip().upper()
        if not (gid and eid and role in ("Q1", "Q2")):
            continue

        civ = _safe_dict(c.get("card_image_validation"))
        has_civ = bool(civ)
        hard = (_as_bool(civ.get("blocking_error")) is True) or (_as_bool(civ.get("safety_flag")) is True) if has_civ else False
        q = _as_int(civ.get("image_quality")) if has_civ else None
        lowq = (q is not None) and (int(q) <= int(s4_quality_threshold))

        missing = False
        entry: Optional[Dict[str, Any]] = None
        if s4_manifest_index is not None:
            entry = s4_manifest_index.get((gid, eid, role))
            if entry is None:
                # No manifest entry: check disk (baseline images/) before calling it missing.
                missing = not _baseline_image_exists_on_disk(
                    base_dir=base_dir, run_tag=run_tag, group_id=gid, entity_id=eid, card_role=role
                )
            else:
                if _as_bool(entry.get("generation_success")) is False:
                    missing = True
                p_str = str(entry.get("image_path") or "").strip()
                if p_str:
                    missing = missing or (not _path_exists_best_effort(Path(p_str), base_dir=base_dir))
                else:
                    missing = True
        else:
            # No manifest available: disk-only check
            missing = not _baseline_image_exists_on_disk(
                base_dir=base_dir, run_tag=run_tag, group_id=gid, entity_id=eid, card_role=role
            )

        if hard or lowq or missing:
            entity_ids_set.add(eid)
            card_roles_set.add(role)
            reasons.append(
                {
                    "group_id": gid,
                    "entity_id": eid,
                    "card_role": role,
                    "hard_trigger": bool(hard),
                    "low_quality": bool(lowq),
                    "image_quality": int(q) if q is not None else None,
                    "missing": bool(missing),
                }
            )

    entity_ids = sorted(entity_ids_set)
    card_roles = sorted(card_roles_set)
    return (entity_ids, card_roles, reasons)


def _dedupe_latest_by_group(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    The baseline S5 validator appends to JSONL. For selection we want the latest record per group_id.
    """
    best: Dict[str, Tuple[Optional[datetime], Dict[str, Any]]] = {}
    for r in rows:
        gid = str(r.get("group_id") or "").strip()
        if not gid:
            continue
        ts = _parse_iso(str(r.get("validation_timestamp") or ""))
        cur = best.get(gid)
        if cur is None or (ts is not None and (cur[0] is None or ts > cur[0])):
            best[gid] = (ts, r)
    return [v[1] for v in sorted(best.values(), key=lambda x: (x[0] is None, x[0], str(x[1].get("group_id") or "")))]


@dataclass(frozen=True)
class TriggerDecision:
    group_id: str
    trigger_mode: str
    hard_trigger: bool
    s1_hard_trigger: bool
    min_score: float
    threshold: float
    trigger_reason: str
    triggered_entities: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def should_trigger(self) -> bool:
        return self.hard_trigger or self.min_score < self.threshold


def _score_inputs_from_s5_validation_record(group_record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert S5 validation JSONL (group record) to "flattened" dicts that the score calculator expects.
    We compute per-card (and optionally per-S1-table) scores, then aggregate at the group level.
    """
    out: List[Dict[str, Any]] = []

    # S1 table validation as a "pseudo card"
    s1 = _safe_dict(group_record.get("s1_table_validation"))
    if s1:
        out.append(
            {
                "s5_blocking_error": s1.get("blocking_error"),
                "s5_technical_accuracy": s1.get("technical_accuracy"),
                "s5_educational_quality": s1.get("educational_quality"),
                # no image for S1 table
                "s5_card_image_blocking_error": False,
                "s5_card_image_safety_flag": False,
                "s5_card_image_quality": None,
            }
        )

    s2 = _safe_dict(group_record.get("s2_cards_validation"))
    for c in _safe_list(s2.get("cards")):
        if not isinstance(c, dict):
            continue
        civ = _safe_dict(c.get("card_image_validation"))
        out.append(
            {
                "s5_blocking_error": c.get("blocking_error"),
                "s5_technical_accuracy": c.get("technical_accuracy"),
                "s5_educational_quality": c.get("educational_quality"),
                "s5_card_image_blocking_error": civ.get("blocking_error"),
                "s5_card_image_safety_flag": civ.get("safety_flag"),
                "s5_card_image_quality": civ.get("image_quality"),
            }
        )
    return out


def _is_hard_trigger_from_score_input(x: Dict[str, Any]) -> bool:
    if _as_bool(x.get("s5_blocking_error")) is True:
        return True
    ta = _as_float(x.get("s5_technical_accuracy"))
    if ta is not None and ta == 0.0:
        return True
    if _as_bool(x.get("s5_card_image_blocking_error")) is True:
        return True
    if _as_bool(x.get("s5_card_image_safety_flag")) is True:
        return True
    return False


def _score_input_from_s2_card(card: Dict[str, Any]) -> Dict[str, Any]:
    civ = _safe_dict(card.get("card_image_validation"))
    return {
        "s5_blocking_error": card.get("blocking_error"),
        "s5_technical_accuracy": card.get("technical_accuracy"),
        "s5_educational_quality": card.get("educational_quality"),
        "s5_card_image_blocking_error": civ.get("blocking_error"),
        "s5_card_image_safety_flag": civ.get("safety_flag"),
        "s5_card_image_quality": civ.get("image_quality"),
    }


def decide_trigger_for_group(
    *,
    group_record: Dict[str, Any],
    threshold: float,
) -> TriggerDecision:
    """
    Group mode trigger decision.
    
    Rules:
    - Only S1 table and Infographic are evaluated (S2 cards excluded).
    - S1 table validation and table-level infographic image are the focus.
    """
    gid = str(group_record.get("group_id") or "").strip()

    # Group mode: Only S1 table and Infographic (S2 cards excluded)
    s1 = _safe_dict(group_record.get("s1_table_validation"))
    
    if not s1:
        # If no S1 data, be conservative: do not auto-trigger.
        return TriggerDecision(
            group_id=gid,
            trigger_mode="group",
            hard_trigger=False,
            s1_hard_trigger=False,
            min_score=100.0,
            threshold=threshold,
            trigger_reason="no_score_inputs",
            triggered_entities=[],
        )
    
    # S1 score (table + infographic)
    s1_input = {
        "s5_blocking_error": s1.get("blocking_error"),
        "s5_technical_accuracy": s1.get("technical_accuracy"),
        "s5_educational_quality": s1.get("educational_quality"),
        "s5_card_image_blocking_error": False,  # Infographic image issues would be here if tracked separately
        "s5_card_image_safety_flag": False,
        "s5_card_image_quality": None,  # Infographic quality would be here if tracked separately
    }
    s1_score = float(calculate_s5_regeneration_trigger_score(s1_input))
    s1_hard = _is_hard_trigger_from_score_input(s1_input)

    if s1_hard:
        reason = "hard_trigger"
    elif s1_score < float(threshold):
        reason = "score_lt_threshold"
    else:
        reason = "no_trigger"

    return TriggerDecision(
        group_id=gid,
        trigger_mode="group",
        hard_trigger=bool(s1_hard),
        s1_hard_trigger=bool(s1_hard),
        min_score=float(s1_score),  # S1 table and Infographic only
        threshold=float(threshold),
        trigger_reason=reason,
        triggered_entities=[],
    )


def decide_trigger_for_group_entitywise(
    *,
    group_record: Dict[str, Any],
    threshold: float,
) -> TriggerDecision:
    """
    Entity-wise trigger decision.

    Rules:
    - Compute per-entity min_score across S2 cards grouped by (entity_id if present else entity_name).
    - An entity triggers if any card is hard-trigger OR entity_min_score < threshold.
    - S1 is NOT evaluated in entity mode (focus on cards and card images only).
    """
    gid = str(group_record.get("group_id") or "").strip()

    # --- S2 cards grouped by entity (S1 excluded in entity mode) ---
    s2 = _safe_dict(group_record.get("s2_cards_validation"))
    entity_bucket: Dict[str, Dict[str, Any]] = {}

    for c in _safe_list(s2.get("cards")):
        if not isinstance(c, dict):
            continue

        eid = str(c.get("entity_id") or "").strip()
        enm = str(c.get("entity_name") or "").strip()

        # Grouping key: prefer entity_id, else entity_name, else fallback bucket.
        if eid:
            k = f"id:{eid}"
        elif enm:
            k = f"name:{enm}"
        else:
            k = "missing_entity"

        b = entity_bucket.get(k)
        if b is None:
            b = {
                "entity_id": eid or None,
                "entity_name": enm or None,
                "min_score": 100.0,
                "hard_trigger": False,
                "card_ids": [],
            }
            entity_bucket[k] = b

        # Use pre-recorded score if available, otherwise calculate
        recorded_score = c.get("regeneration_trigger_score")
        score_input = _score_input_from_s2_card(c)
        
        if recorded_score is not None:
            score = float(recorded_score)
        else:
            # Fallback: calculate if no recorded score
            score = float(calculate_s5_regeneration_trigger_score(score_input))
        
        hard = _is_hard_trigger_from_score_input(score_input)

        b["min_score"] = float(min(float(b["min_score"]), score))
        b["hard_trigger"] = bool(b["hard_trigger"] or hard)

        cid = str(c.get("card_id") or "").strip()
        if cid:
            b["card_ids"].append(cid)

        # If we are in a fallback bucket, keep the best-effort metadata we have.
        if (not b.get("entity_id")) and eid:
            b["entity_id"] = eid
        if (not b.get("entity_name")) and enm:
            b["entity_name"] = enm

    triggered_entities: List[Dict[str, Any]] = []
    any_score_lt = False
    any_hard_s2 = False
    min_entity_score = 100.0

    for b in entity_bucket.values():
        min_entity_score = min(min_entity_score, float(b.get("min_score", 100.0)))
        any_hard_s2 = bool(any_hard_s2 or bool(b.get("hard_trigger")))
        if bool(b.get("hard_trigger")):
            b_reason = "hard_trigger"
        elif float(b.get("min_score", 100.0)) < float(threshold):
            b_reason = "score_lt_threshold"
            any_score_lt = True
        else:
            b_reason = "no_trigger"
        b["trigger_reason"] = b_reason

        if b_reason in ("hard_trigger", "score_lt_threshold"):
            triggered_entities.append(
                {
                    "entity_id": b.get("entity_id"),
                    "entity_name": b.get("entity_name"),
                    "min_score": float(b.get("min_score", 100.0)),
                    "hard_trigger": bool(b.get("hard_trigger")),
                    "trigger_reason": b_reason,
                    "card_ids": list(b.get("card_ids") or []),
                }
            )

    # Sort: hard first, then lower score, then stable by entity identifiers.
    triggered_entities.sort(
        key=lambda x: (
            0 if x.get("hard_trigger") else 1,
            float(x.get("min_score") or 100.0),
            str(x.get("entity_id") or ""),
            str(x.get("entity_name") or ""),
        )
    )

    # Group-level aggregation (for selection list + compatibility with previous runlog shape)
    # Entity mode: Only S2 cards and card images are evaluated (S1 excluded)
    group_min_score = float(min_entity_score) if entity_bucket else 100.0
    group_hard = bool(any_hard_s2)

    if group_hard:
        reason = "hard_trigger"
    elif any_score_lt:
        reason = "score_lt_threshold"
    else:
        reason = "no_trigger"

    # If we cannot compute entity scores (empty S2), be conservative: do not auto-trigger.
    if not entity_bucket:
        return TriggerDecision(
            group_id=gid,
            trigger_mode="entity",
            hard_trigger=False,
            s1_hard_trigger=False,
            min_score=100.0,
            threshold=float(threshold),
            trigger_reason="no_score_inputs",
            triggered_entities=[],
        )

    return TriggerDecision(
        group_id=gid,
        trigger_mode="entity",
        hard_trigger=group_hard,
        s1_hard_trigger=False,  # S1 is not evaluated in entity mode
        min_score=float(group_min_score),  # S2 cards and card images only
        threshold=float(threshold),
        trigger_reason=reason,
        triggered_entities=triggered_entities,
    )


def _collect_entities_from_plan(plan_path: Path) -> Tuple[List[str], List[str]]:
    """
    Returns (entity_ids, entity_names) to be passed to 01_generate_json.py.
    Prefer entity_id when available.
    """
    rows = _read_jsonl(plan_path)
    if not rows:
        return ([], [])
    plan = rows[0]
    s2_actions = _safe_list(plan.get("s2_actions"))

    entity_ids: List[str] = []
    entity_names: List[str] = []
    ids_seen: set[str] = set()
    names_seen: set[str] = set()

    for a in s2_actions:
        if not isinstance(a, dict):
            continue
        eid = str(a.get("entity_id") or "").strip()
        enm = str(a.get("entity_name") or "").strip()
        if eid and eid not in ids_seen:
            ids_seen.add(eid)
            entity_ids.append(eid)
        elif (not eid) and enm and enm not in names_seen:
            names_seen.add(enm)
            entity_names.append(enm)

    return (entity_ids, entity_names)


def _read_stage1_struct_for_group(*, stage1_struct_path: Path, group_id: str) -> Optional[Dict[str, Any]]:
    gid = str(group_id or "").strip()
    if not gid:
        return None
    if not stage1_struct_path.exists():
        return None
    with open(stage1_struct_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            if str(obj.get("group_id") or "").strip() == gid:
                return obj
    return None


def _inject_s1_preserve_entity_list_guardrail(
    *,
    plan_path: Path,
    baseline_entity_names: List[str],
) -> bool:
    """
    Add a conservative S1 guardrail to the S5R plan:
    - Do NOT add/remove/rename entities.
    - Keep master_table first column identical to baseline entity list (order preserved).
    """
    rows = _read_jsonl(plan_path)
    if not rows:
        return False
    plan = rows[0]
    s1_actions = _safe_list(plan.get("s1_actions"))
    if not isinstance(s1_actions, list):
        s1_actions = []

    names = [str(x).strip() for x in (baseline_entity_names or []) if str(x).strip()]
    if not names:
        return False

    preview_n = 40
    preview = ", ".join(names[:preview_n])
    more = "" if len(names) <= preview_n else f" ... (+{len(names) - preview_n} more)"
    instruction = (
        "Entity list SSOT guardrail (must preserve S1→S2 stability):\n"
        "- Do NOT add/remove/rename entities.\n"
        "- Keep master_table_markdown_kr first column (entity names) EXACTLY identical to baseline (order preserved).\n"
        f"- Baseline entity_names (count={len(names)}): {preview}{more}"
    )

    guardrail_action = {
        "action_id": "s1_preserve_entity_list",
        "action_type": "preserve_entity_list",
        "instruction": instruction,
    }

    # Prepend once (idempotent by action_id)
    existing_ids = {str(a.get("action_id") or "") for a in s1_actions if isinstance(a, dict)}
    if guardrail_action["action_id"] not in existing_ids:
        s1_actions = [guardrail_action] + [a for a in s1_actions if isinstance(a, dict)]
        plan["s1_actions"] = s1_actions
        _write_jsonl(plan_path, [plan])
        return True
    return False


def _run_cmd(cmd: List[str], *, dry_run: bool) -> Tuple[int, float, str]:
    """
    Returns (returncode, duration_s, short_status).
    """
    t0 = time.time()
    if dry_run:
        print("[DRY-RUN]", " ".join(cmd), flush=True)
        return (0, 0.0, "dry_run")
    try:
        proc = subprocess.run(cmd, check=False)
        dt = time.time() - t0
        return (int(proc.returncode), dt, "ok" if proc.returncode == 0 else "error")
    except Exception as e:
        dt = time.time() - t0
        return (2, dt, f"exception:{type(e).__name__}:{e}")


def main() -> None:
    p = argparse.ArgumentParser(description="Option C orchestrator (S5 -> S5R -> S2 repaired -> S5 postrepair)")
    p.add_argument("--base_dir", type=str, required=True, help="Project base dir (repo root)")
    p.add_argument("--run_tag", type=str, required=True, help="RUN_TAG under 2_Data/metadata/generated/")
    p.add_argument("--arm", type=str, required=True, help="S2 arm identifier (e.g., A/B/...)")
    p.add_argument("--s1_arm", type=str, default=None, help="Optional: S1 arm (defaults to --arm)")
    p.add_argument("--only_group_id", type=str, default=None, help="Optional: run only one group_id")
    p.add_argument("--threshold", type=float, default=80.0, help="Trigger score threshold (default 80.0)")
    p.add_argument(
        "--trigger_mode",
        type=str,
        default="entity",
        choices=["entity", "group"],
        help="Trigger selection mode. entity: per-entity min score (S2) + S1 hard-trigger forces group. group: legacy group-level min score.",
    )
    p.add_argument(
        "--entity_filter_mode",
        type=str,
        default="from_plan",
        choices=["from_plan", "none"],
        help="Entity scoping strategy for S2 regeneration. from_plan: use entity_id/name from S5R plan. none: regenerate full group S2.",
    )
    p.add_argument(
        "--dry_run",
        action="store_true",
        default=False,
        help="Print planned actions/commands without executing subprocesses.",
    )
    s4_inc = p.add_mutually_exclusive_group()
    s4_inc.add_argument(
        "--include_s4",
        dest="include_s4",
        action="store_true",
        default=True,
        help="Include S4 repaired image regeneration (subset) before postrepair S5 validation (default: true).",
    )
    s4_inc.add_argument(
        "--no_include_s4",
        dest="include_s4",
        action="store_false",
        help="Disable S4 repaired image regeneration step.",
    )
    p.add_argument(
        "--s4_image_quality_threshold",
        type=int,
        default=3,
        help="If image_quality <= threshold, regenerate that card image in S4 repaired (default: 3).",
    )
    s4_ow = p.add_mutually_exclusive_group()
    s4_ow.add_argument(
        "--s4_overwrite_existing",
        dest="s4_overwrite_existing",
        action="store_true",
        default=True,
        help="Overwrite existing repaired images for selected targets (default: true).",
    )
    s4_ow.add_argument(
        "--no_s4_overwrite_existing",
        dest="s4_overwrite_existing",
        action="store_false",
        help="Do not overwrite existing repaired images (missing-only fill).",
    )
    p.add_argument(
        "--s4_workers",
        type=int,
        default=1,
        help="Parallel workers for S4 image generation (default: 1).",
    )
    args = p.parse_args()

    base_dir = Path(args.base_dir).resolve()
    run_tag = str(args.run_tag).strip()
    arm = str(args.arm).strip().upper()
    s1_arm = str(args.s1_arm).strip().upper() if args.s1_arm else arm
    threshold = float(args.threshold)
    only_group_id = str(args.only_group_id).strip() if args.only_group_id else None
    dry_run = bool(args.dry_run)

    data_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    s5_path = data_dir / f"s5_validation__arm{arm}.jsonl"
    if not s5_path.exists():
        print(f"[OptionC] ERROR: baseline S5 validation not found: {s5_path}", file=sys.stderr)
        sys.exit(2)

    rows = _dedupe_latest_by_group(_read_jsonl(s5_path))
    if only_group_id:
        rows = [r for r in rows if str(r.get("group_id") or "").strip() == only_group_id]
        if not rows:
            print(f"[OptionC] ERROR: only_group_id={only_group_id} not found in {s5_path}", file=sys.stderr)
            sys.exit(2)

    decisions: List[TriggerDecision] = []
    for r in rows:
        if args.trigger_mode == "entity":
            decisions.append(decide_trigger_for_group_entitywise(group_record=r, threshold=threshold))
        else:
            decisions.append(decide_trigger_for_group(group_record=r, threshold=threshold))

    selected = [d for d in decisions if d.should_trigger]
    selected_ids = [d.group_id for d in selected]
    group_record_by_id: Dict[str, Dict[str, Any]] = {str(r.get("group_id") or "").strip(): r for r in rows if isinstance(r, dict)}

    print(f"[OptionC] Groups in baseline S5 (deduped): {len(decisions)}")
    print(f"[OptionC] Trigger mode: {args.trigger_mode}")
    print(f"[OptionC] Selected for repair/regeneration: {len(selected)} (threshold={threshold})")
    if selected_ids:
        print(f"[OptionC] Selected group_ids: {', '.join(selected_ids[:50])}{'...' if len(selected_ids) > 50 else ''}")
    else:
        print("[OptionC] Nothing selected. Exiting.")
        # Still write a run log for traceability.
        runlog_path = data_dir / f"optionc_orchestrator__arm{arm}__runlog.json"
        runlog_path.parent.mkdir(parents=True, exist_ok=True)
        runlog_path.write_text(
            json.dumps(
                {
                    "run_tag": run_tag,
                    "arm": arm,
                    "s1_arm": s1_arm,
                    "started_at": _utc_now_iso(),
                    "ended_at": _utc_now_iso(),
                    "threshold": threshold,
                    "trigger_mode": args.trigger_mode,
                    "entity_filter_mode": args.entity_filter_mode,
                    "selected_groups": [],
                    "decisions": [d.__dict__ for d in decisions],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return

    src_dir = base_dir / "3_Code" / "src"
    planner_script = src_dir / "05_s5r_repair_planner.py"
    generator_script = src_dir / "01_generate_json.py"
    s4_script = src_dir / "04_s4_image_generator.py"
    validator_script = src_dir / "05_s5_validator.py"

    for s in (planner_script, generator_script, s4_script, validator_script):
        if not s.exists():
            print(f"[OptionC] ERROR: missing script: {s}", file=sys.stderr)
            sys.exit(2)

    # Baseline S4 manifest (for missing-image detection). Best-effort: if not present, disk checks still work.
    s4_manifest_index: Optional[Dict[Tuple[str, str, str], Dict[str, Any]]] = None
    s4_manifest_baseline_path = data_dir / f"s4_image_manifest__arm{arm}.jsonl"
    if bool(args.include_s4) and s4_manifest_baseline_path.exists():
        try:
            s4_manifest_index = _load_s4_card_manifest_index(manifest_path=s4_manifest_baseline_path)
        except Exception as e:
            print(f"[OptionC] WARN: failed to load S4 manifest for missing checks: {e}", file=sys.stderr)
            s4_manifest_index = None

    # Outputs used by downstream tools (standard paths)
    repaired_s2_path = data_dir / f"s2_results__s1arm{s1_arm}__s2arm{arm}__repaired.jsonl"
    baseline_s2_path = data_dir / f"s2_results__s1arm{s1_arm}__s2arm{arm}.jsonl"
    postrepair_s5_path = data_dir / f"s5_validation__arm{arm}__postrepair.jsonl"
    baseline_s1_struct_path = data_dir / f"stage1_struct__arm{s1_arm}.jsonl"
    repaired_s1_struct_path = data_dir / f"stage1_struct__arm{s1_arm}__repaired.jsonl"

    started_at = _utc_now_iso()
    per_group_results: List[Dict[str, Any]] = []

    for d in selected:
        gid = d.group_id
        print(f"\n[OptionC] === Group {gid} ===")
        if d.trigger_mode == "entity":
            print(
                f"[OptionC] decision(entity): hard={d.hard_trigger} s1_hard={d.s1_hard_trigger} "
                f"min_score={d.min_score} reason={d.trigger_reason} triggered_entities={len(d.triggered_entities)}"
            )
        else:
            print(f"[OptionC] decision(group): hard={d.hard_trigger} min_score={d.min_score} reason={d.trigger_reason}")

        plan_path = data_dir / f"s5_repair_plan__arm{arm}__group{gid}.jsonl"

        # --- Precompute S4 targets from baseline S5 record (best-effort) ---
        s4_entity_ids: List[str] = []
        s4_card_roles: List[str] = []
        s4_reasons: List[Dict[str, Any]] = []
        if bool(args.include_s4):
            gr = group_record_by_id.get(gid) or {}
            try:
                s4_entity_ids, s4_card_roles, s4_reasons = _extract_s4_image_targets_from_s5_group_record(
                    group_record=gr,
                    base_dir=base_dir,
                    run_tag=run_tag,
                    s4_quality_threshold=int(args.s4_image_quality_threshold),
                    s4_manifest_index=s4_manifest_index,
                )
            except Exception as e:
                print(f"[OptionC] WARN: failed to extract S4 targets for group {gid}: {e}", file=sys.stderr)
                s4_entity_ids, s4_card_roles, s4_reasons = ([], [], [])

        # 1) S5R repair plan
        cmd_plan = [
            sys.executable,
            str(planner_script),
            "--base_dir",
            str(base_dir),
            "--run_tag",
            run_tag,
            "--arm",
            arm,
            "--s1_arm",
            s1_arm,
            "--only_group_id",
            gid,
            "--output_path",
            str(plan_path),
        ]
        rc_plan, dt_plan, st_plan = _run_cmd(cmd_plan, dry_run=dry_run)
        if (not dry_run) and rc_plan != 0:
            per_group_results.append(
                {
                    "group_id": gid,
                    "decision": d.__dict__,
                    "plan": {"returncode": rc_plan, "duration_s": dt_plan, "status": st_plan},
                    "regenerate": {"status": "skipped_due_to_plan_failure"},
                    "postrepair_validate": {"status": "skipped_due_to_plan_failure"},
                }
            )
            print(f"[OptionC] WARN: plan failed for group {gid} (rc={rc_plan}); continuing.", file=sys.stderr)
            continue

        # If S1 is hard-triggered but S2 passed (entity-mode: no triggered S2 entities),
        # do NOT touch S2. This preserves S2 stability while allowing S1-only repair workflows.
        skip_s2_regen_due_to_s1_hard_trigger = bool(
            d.s1_hard_trigger
            and (d.trigger_mode == "entity")
            and (len(d.triggered_entities or []) == 0)
        )

        # Add S1 guardrail to preserve entity list (best-effort, only when S1 hard-triggered).
        injected_entity_guardrail = False
        if d.s1_hard_trigger and (not dry_run):
            s1_struct = _read_stage1_struct_for_group(stage1_struct_path=baseline_s1_struct_path, group_id=gid)
            ent_names: List[str] = []
            if s1_struct:
                raw_list = _safe_list(s1_struct.get("entity_list"))
                for it in raw_list:
                    if isinstance(it, dict):
                        nm = str(it.get("entity_name") or it.get("name") or "").strip()
                    else:
                        nm = str(it).strip()
                    if nm:
                        ent_names.append(nm)
            if ent_names:
                injected_entity_guardrail = _inject_s1_preserve_entity_list_guardrail(
                    plan_path=plan_path,
                    baseline_entity_names=ent_names,
                )

        if skip_s2_regen_due_to_s1_hard_trigger:
            print("[OptionC] S1 hard trigger but no failing S2 entities -> skipping S2 regeneration (keep S2 untouched).")

            # 2a) S1 repaired generation (additive; writes __repaired artifacts)
            cmd_s1r = [
                sys.executable,
                str(generator_script),
                "--base_dir",
                str(base_dir),
                "--run_tag",
                run_tag,
                "--arm",
                s1_arm,  # write S1 repaired outputs under the S1 arm
                "--stage",
                "1",
                "--only_group_id",
                gid,
                "--output_variant",
                "repaired",
                "--repair_plan_path",
                str(plan_path),
                "--resume",
            ]
            rc_s1r, dt_s1r, st_s1r = _run_cmd(cmd_s1r, dry_run=dry_run)
            if (not dry_run) and rc_s1r != 0:
                per_group_results.append(
                    {
                        "group_id": gid,
                        "decision": d.__dict__,
                        "plan_path": str(plan_path),
                        "s1_entity_list_guardrail_injected": bool(injected_entity_guardrail),
                        "plan": {"returncode": rc_plan, "duration_s": dt_plan, "status": st_plan},
                        "s1_repaired": {"returncode": rc_s1r, "duration_s": dt_s1r, "status": st_s1r},
                        "regenerate": {"status": "skipped_s2_due_to_s1_hard_trigger"},
                        "postrepair_validate": {"status": "skipped_due_to_s1_repair_failure"},
                    }
                )
                print(f"[OptionC] WARN: S1 repaired generation failed for group {gid} (rc={rc_s1r}); continuing.", file=sys.stderr)
                continue

            # 2b-optional) S4 repaired (subset) for image issues
            rc_s4 = 0
            dt_s4 = 0.0
            st_s4 = "skipped"
            if bool(args.include_s4) and (s4_entity_ids or s4_card_roles):
                print(
                    f"[OptionC] S4 targets: entities={len(s4_entity_ids)} roles={s4_card_roles} "
                    f"(quality_threshold={int(args.s4_image_quality_threshold)})"
                )
                cmd_s4 = [
                    sys.executable,
                    str(s4_script),
                    "--base_dir",
                    str(base_dir),
                    "--run_tag",
                    run_tag,
                    "--arm",
                    arm,
                    "--output_variant",
                    "repaired",
                    "--no_fail_fast_required",
                    "--workers",
                    str(int(args.s4_workers)),
                    "--only_group_id",
                    gid,
                    "--only_spec_kind",
                    "S2_CARD_IMAGE",
                    "--only_spec_kind",
                    "S2_CARD_CONCEPT",
                ]
                for eid in s4_entity_ids:
                    cmd_s4.extend(["--only_entity_id", eid])
                for role in s4_card_roles:
                    cmd_s4.extend(["--only_card_role", role])
                if bool(args.s4_overwrite_existing):
                    cmd_s4.append("--overwrite_existing")
                rc_s4, dt_s4, st_s4 = _run_cmd(cmd_s4, dry_run=dry_run)
                if (not dry_run) and rc_s4 != 0:
                    print(f"[OptionC] WARN: S4 repaired failed for group {gid} (rc={rc_s4}); continuing.", file=sys.stderr)

            # 2b) Postrepair S5 validation using repaired S1 + baseline S2 (untouched)
            cmd_s5p_s1 = [
                sys.executable,
                str(validator_script),
                "--base_dir",
                str(base_dir),
                "--run_tag",
                run_tag,
                "--arm",
                arm,
                "--group_id",
                gid,
                "--s1_path",
                str(repaired_s1_struct_path),
                "--s2_path",
                str(baseline_s2_path),
                "--output_path",
                str(postrepair_s5_path),
                "--is_postrepair",
                "true",
            ]
            rc_s5p, dt_s5p, st_s5p = _run_cmd(cmd_s5p_s1, dry_run=dry_run)
            if (not dry_run) and rc_s5p != 0:
                print(f"[OptionC] WARN: postrepair validation failed for group {gid} (rc={rc_s5p}); continuing.", file=sys.stderr)

            per_group_results.append(
                {
                    "group_id": gid,
                    "decision": d.__dict__,
                    "plan_path": str(plan_path),
                    "s1_entity_list_guardrail_injected": bool(injected_entity_guardrail),
                    "plan": {"returncode": rc_plan, "duration_s": dt_plan, "status": st_plan},
                    "s1_repaired": {"returncode": rc_s1r, "duration_s": dt_s1r, "status": st_s1r},
                    "s4_repaired": {
                        "status": st_s4,
                        "returncode": rc_s4,
                        "duration_s": dt_s4,
                        "targets": {"entity_ids": s4_entity_ids, "card_roles": s4_card_roles, "reasons_n": len(s4_reasons)},
                    },
                    "regenerate": {"status": "skipped_s2_due_to_s1_hard_trigger"},
                    "postrepair_validate": {"returncode": rc_s5p, "duration_s": dt_s5p, "status": st_s5p},
                }
            )
            continue

        # 2) Determine entity scope (optional)
        effective_entity_filter_mode = args.entity_filter_mode
        entity_ids: List[str] = []
        entity_names: List[str] = []
        if (not dry_run) and effective_entity_filter_mode == "from_plan":
            entity_ids, entity_names = _collect_entities_from_plan(plan_path)

        if effective_entity_filter_mode == "none":
            entity_ids, entity_names = ([], [])

        if effective_entity_filter_mode == "from_plan" and (not entity_ids and not entity_names):
            print("[OptionC] entity_filter_mode=from_plan but no entity targets found; regenerating full group S2.")

        # 3) S2-only regeneration (repaired output variant + plan injection)
        cmd_gen: List[str] = [
            sys.executable,
            str(generator_script),
            "--base_dir",
            str(base_dir),
            "--run_tag",
            run_tag,
            "--arm",
            arm,
            "--s1_arm",
            s1_arm,
            "--stage",
            "2",
            "--only_group_id",
            gid,
            "--output_variant",
            "repaired",
            "--repair_plan_path",
            str(plan_path),
            "--resume",  # append to __repaired artifacts; never overwrite baseline
        ]
        for eid in entity_ids:
            cmd_gen.extend(["--only_entity_id", eid])
        for enm in entity_names:
            cmd_gen.extend(["--only_entity_name", enm])

        rc_gen, dt_gen, st_gen = _run_cmd(cmd_gen, dry_run=dry_run)
        if (not dry_run) and rc_gen != 0:
            per_group_results.append(
                {
                    "group_id": gid,
                    "decision": d.__dict__,
                    "plan_path": str(plan_path),
                    "plan": {"returncode": rc_plan, "duration_s": dt_plan, "status": st_plan},
                    "entity_scope": {
                        "effective_entity_filter_mode": effective_entity_filter_mode,
                        "skip_s2_regen_due_to_s1_hard_trigger": False,
                        "entity_ids": entity_ids,
                        "entity_names": entity_names,
                    },
                    "regenerate": {"returncode": rc_gen, "duration_s": dt_gen, "status": st_gen},
                    "postrepair_validate": {"status": "skipped_due_to_regen_failure"},
                }
            )
            print(f"[OptionC] WARN: regeneration failed for group {gid} (rc={rc_gen}); continuing.", file=sys.stderr)
            continue

        # 4a) S4 repaired (subset) for image issues, before postrepair S5 validation
        rc_s4 = 0
        dt_s4 = 0.0
        st_s4 = "skipped"
        if bool(args.include_s4) and (s4_entity_ids or s4_card_roles):
            print(
                f"[OptionC] S4 targets: entities={len(s4_entity_ids)} roles={s4_card_roles} "
                f"(quality_threshold={int(args.s4_image_quality_threshold)})"
            )
            cmd_s4 = [
                sys.executable,
                str(s4_script),
                "--base_dir",
                str(base_dir),
                "--run_tag",
                run_tag,
                "--arm",
                arm,
                "--output_variant",
                "repaired",
                "--no_fail_fast_required",
                "--workers",
                str(int(args.s4_workers)),
                "--only_group_id",
                gid,
                "--only_spec_kind",
                "S2_CARD_IMAGE",
                "--only_spec_kind",
                "S2_CARD_CONCEPT",
            ]
            for eid in s4_entity_ids:
                cmd_s4.extend(["--only_entity_id", eid])
            for role in s4_card_roles:
                cmd_s4.extend(["--only_card_role", role])
            if bool(args.s4_overwrite_existing):
                cmd_s4.append("--overwrite_existing")
            rc_s4, dt_s4, st_s4 = _run_cmd(cmd_s4, dry_run=dry_run)
            if (not dry_run) and rc_s4 != 0:
                print(f"[OptionC] WARN: S4 repaired failed for group {gid} (rc={rc_s4}); continuing.", file=sys.stderr)

        # 4) Postrepair S5 validation (validate baseline S1 + repaired S2)
        cmd_s5p = [
            sys.executable,
            str(validator_script),
            "--base_dir",
            str(base_dir),
            "--run_tag",
            run_tag,
            "--arm",
            arm,
            "--group_id",
            gid,
            "--s1_path",
            str(data_dir / f"stage1_struct__arm{s1_arm}.jsonl"),
            "--s2_path",
            str(repaired_s2_path),
            "--output_path",
            str(postrepair_s5_path),
            "--is_postrepair",
            "true",
        ]
        rc_s5p, dt_s5p, st_s5p = _run_cmd(cmd_s5p, dry_run=dry_run)
        if (not dry_run) and rc_s5p != 0:
            print(f"[OptionC] WARN: postrepair validation failed for group {gid} (rc={rc_s5p}); continuing.", file=sys.stderr)

        per_group_results.append(
            {
                "group_id": gid,
                "decision": d.__dict__,
                "plan_path": str(plan_path),
                "entity_scope": {
                    "effective_entity_filter_mode": effective_entity_filter_mode,
                    "skip_s2_regen_due_to_s1_hard_trigger": False,
                    "entity_ids": entity_ids,
                    "entity_names": entity_names,
                },
                "plan": {"returncode": rc_plan, "duration_s": dt_plan, "status": st_plan},
                "regenerate": {"returncode": rc_gen, "duration_s": dt_gen, "status": st_gen},
                "s4_repaired": {
                    "status": st_s4,
                    "returncode": rc_s4,
                    "duration_s": dt_s4,
                    "targets": {"entity_ids": s4_entity_ids, "card_roles": s4_card_roles, "reasons_n": len(s4_reasons)},
                },
                "postrepair_validate": {"returncode": rc_s5p, "duration_s": dt_s5p, "status": st_s5p},
            }
        )

    ended_at = _utc_now_iso()
    runlog = {
        "run_tag": run_tag,
        "arm": arm,
        "s1_arm": s1_arm,
        "started_at": started_at,
        "ended_at": ended_at,
        "threshold": threshold,
        "trigger_mode": args.trigger_mode,
        "entity_filter_mode": args.entity_filter_mode,
        "inputs": {"baseline_s5_path": str(s5_path)},
        "outputs": {
            "repaired_s2_path": str(repaired_s2_path),
            "postrepair_s5_path": str(postrepair_s5_path),
            "repaired_s1_struct_path": str(repaired_s1_struct_path),
        },
        "selected_groups": selected_ids,
        "decisions": [d.__dict__ for d in decisions],
        "per_group_results": per_group_results,
    }

    runlog_path = data_dir / f"optionc_orchestrator__arm{arm}__runlog.json"
    runlog_path.parent.mkdir(parents=True, exist_ok=True)
    runlog_path.write_text(json.dumps(runlog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[OptionC] Wrote run log: {runlog_path}")
    print(f"[OptionC] Repaired S2 (append mode) path: {repaired_s2_path}")
    print(f"[OptionC] Postrepair S5 (append mode) path: {postrepair_s5_path}")


if __name__ == "__main__":
    main()



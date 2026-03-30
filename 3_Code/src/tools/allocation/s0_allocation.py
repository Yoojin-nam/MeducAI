"""
S0 Allocation Module
-------------------
Canonical implementation for S0 allocation artifacts.

v2.1 policy (current canonical):
- Fixed 12 cards per set (group × arm)
- Deterministic prefix allocation (3×4):
    - If E >= 4: use first 4 entities × 3 cards each = 12
    - If E < 4 : use all entities, deterministic even split to sum 12
- Allocation artifact is mandatory and persisted to disk

Backward compatibility:
- Can validate/read v1.0 artifacts (representative entity only)
- Can validate/read v2.0 artifacts (legacy spread allocation)

Applies to: S0 QA / Model Comparison phase only
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


# =========================
# Constants (S0 Canonical)
# =========================

S0_SET_TARGET_CARDS = 12

# Current canonical (write)
S0_ALLOCATION_VERSION_V2_1 = "S0-Allocation-v2.1"

# Legacy (read-only)
S0_ALLOCATION_VERSION_V2_0 = "S0-Allocation-v2.0"
S0_ALLOCATION_VERSION_V1_0 = "S0-Allocation-v1.0"

# Legacy spread modes (kept for API compatibility only)
SPREAD_MODE_HARD = "hard"
SPREAD_MODE_SOFT = "soft"
ALLOWED_SPREAD_MODES = {SPREAD_MODE_HARD, SPREAD_MODE_SOFT}


# =========================
# Errors
# =========================

class AllocationError(RuntimeError):
    """Raised when allocation invariants are violated."""
    pass


# =========================
# Data Models
# =========================

@dataclass(frozen=True)
class S0AllocationInputs:
    run_tag: str
    group_id: str
    arm: str
    entities_from_s1: List[str]  # ordered list from S1 output


@dataclass(frozen=True)
class S2ExecutionTarget:
    entity_name: str
    cards_for_entity_exact: int


# =========================
# Utilities
# =========================

def _atomic_write_json(path: Path, obj: Dict[str, Any]) -> None:
    """
    Atomically write JSON to disk (POSIX-safe).
    Prevents partial files on crash.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)


def get_s0_allocation_path(base_dir: Path, run_tag: str, group_id: str, arm: str) -> Path:
    """
    Canonical allocation artifact path for S0.
    """
    return (
        base_dir
        / "2_Data/metadata/generated"
        / run_tag
        / "allocation"
        / f"allocation_s0__group_{group_id}__arm_{arm}.json"
    )


def _sanitize_entities_from_s1(raw: List[str]) -> List[str]:
    """Sanitize entity list while preserving order and removing empties."""
    if not isinstance(raw, list):
        return []
    out: List[str] = []
    for e in raw:
        if isinstance(e, str):
            s = e.strip()
            if s:
                out.append(s)
    return out


# =========================
# Allocation builders (v2.1)
# =========================

def _pick_entities_deterministic_prefix(entities: List[str], k: int) -> List[str]:
    """Deterministic selection: first k entities (preserve S1 order)."""
    return entities[:k]


def _alloc_even_split_over_entities(entities: List[str], total_cards: int) -> List[Dict[str, Any]]:
    """
    Even split across ALL provided entities.
    Deterministic: allocates base, then remainder to earliest entities.
    """
    E = len(entities)
    if E <= 0:
        raise AllocationError("cannot allocate with empty entity list")

    base = total_cards // E
    rem = total_cards % E
    allocs: List[Dict[str, Any]] = []
    for i, e in enumerate(entities):
        n = base + (1 if i < rem else 0)
        if n <= 0:
            raise AllocationError("invalid even split produced non-positive allocation")
        allocs.append({"entity_name": e, "cards_for_entity_exact": int(n)})
    return allocs


def _alloc_prefix_3x4_or_fallback(entities: List[str]) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    v2.1 canonical allocation:
      - If E >= 4: use first 4 entities × 3 cards each = 12
      - If E < 4 : use all entities and distribute evenly to sum 12
    Returns (selected_entities, entity_allocations).
    """
    E = len(entities)
    if E <= 0:
        raise AllocationError("S1 entity_list is empty or invalid")

    if E >= 4:
        picked = _pick_entities_deterministic_prefix(entities, 4)
        allocs = [{"entity_name": e, "cards_for_entity_exact": 3} for e in picked]
        return picked, allocs

    # E < 4 fallback: use all entities
    picked = list(entities)
    allocs = _alloc_even_split_over_entities(picked, S0_SET_TARGET_CARDS)
    return picked, allocs


def _alloc_metrics_from_allocs(allocs: List[Dict[str, Any]]) -> Dict[str, Any]:
    max_cards = max(int(r["cards_for_entity_exact"]) for r in allocs) if allocs else None
    distinct = len(allocs)
    return {
        "distinct_entities_used": distinct,
        "max_cards_per_entity": max_cards,
        "spread_flag_low": bool(distinct < 4),
    }


# =========================
# Validation (Fail-Fast)
# =========================

def _validate_s0_allocation_artifact_v1(artifact: Dict[str, Any]) -> None:
    """
    Validate S0 allocation artifact against v1.0 invariants.
    v1.0: representative entity only (exactly 1 allocation, exactly 12 cards).
    """
    if artifact.get("allocation_version") != S0_ALLOCATION_VERSION_V1_0:
        raise AllocationError("allocation_version mismatch (expected v1.0)")

    if artifact.get("mode") != "S0":
        raise AllocationError("mode must be 'S0'")

    if artifact.get("set_target_cards") != S0_SET_TARGET_CARDS:
        raise AllocationError(f"set_target_cards must be {S0_SET_TARGET_CARDS}")

    entities_from_s1 = artifact.get("entities_from_s1")
    if not isinstance(entities_from_s1, list) or not entities_from_s1:
        raise AllocationError("entities_from_s1 must be a non-empty list")

    selected_entity = artifact.get("selected_entity")
    if not isinstance(selected_entity, str) or not selected_entity.strip():
        raise AllocationError("selected_entity must be a non-empty string")

    if selected_entity not in entities_from_s1:
        raise AllocationError("selected_entity must be contained in entities_from_s1")

    allocs = artifact.get("entity_allocations")
    if not isinstance(allocs, list) or len(allocs) != 1:
        raise AllocationError("entity_allocations must contain exactly 1 entry in S0 (v1.0)")

    row = allocs[0]
    if row.get("entity_name") != selected_entity:
        raise AllocationError("entity_allocations[0].entity_name must equal selected_entity")

    n = row.get("cards_for_entity_exact")
    if not isinstance(n, int) or n <= 0:
        raise AllocationError("cards_for_entity_exact must be int > 0")

    if n != S0_SET_TARGET_CARDS:
        raise AllocationError(f"cards_for_entity_exact must equal {S0_SET_TARGET_CARDS} in S0 (v1.0)")

    checksum = artifact.get("allocation_checksum") or {}
    if checksum.get("sum_cards") != S0_SET_TARGET_CARDS:
        raise AllocationError("allocation_checksum.sum_cards mismatch")
    if checksum.get("entity_count_used") != 1:
        raise AllocationError("allocation_checksum.entity_count_used must be 1")


def _validate_s0_allocation_artifact_v2_0_legacy(artifact: Dict[str, Any]) -> None:
    """
    Validate S0 allocation artifact against v2.0 invariants (legacy spread).
    Read/validate only. Not written by current code.
    """
    if artifact.get("allocation_version") != S0_ALLOCATION_VERSION_V2_0:
        raise AllocationError("allocation_version mismatch (expected v2.0)")

    if artifact.get("mode") != "S0":
        raise AllocationError("mode must be 'S0'")

    if artifact.get("set_target_cards") != S0_SET_TARGET_CARDS:
        raise AllocationError(f"set_target_cards must be {S0_SET_TARGET_CARDS}")

    entities_from_s1 = artifact.get("entities_from_s1")
    if not isinstance(entities_from_s1, list) or not entities_from_s1:
        raise AllocationError("entities_from_s1 must be a non-empty list")

    policy = artifact.get("entity_selection_policy") or {}
    if not isinstance(policy, dict):
        raise AllocationError("entity_selection_policy must be an object")

    # legacy: spread_mode required
    spread_mode = policy.get("spread_mode")
    if spread_mode not in ALLOWED_SPREAD_MODES:
        raise AllocationError(f"entity_selection_policy.spread_mode must be one of {sorted(ALLOWED_SPREAD_MODES)}")

    allocs = artifact.get("entity_allocations")
    if not isinstance(allocs, list) or len(allocs) < 1:
        raise AllocationError("entity_allocations must contain at least 1 entry in S0 (v2.0)")

    seen = set()
    total = 0
    for row in allocs:
        if not isinstance(row, dict):
            raise AllocationError("each entity_allocations row must be an object")
        name = row.get("entity_name")
        n = row.get("cards_for_entity_exact")

        if not isinstance(name, str) or not name.strip():
            raise AllocationError("entity_name must be a non-empty string")
        if name not in entities_from_s1:
            raise AllocationError("entity_name must be contained in entities_from_s1")
        if name in seen:
            raise AllocationError("duplicate entity_name in entity_allocations")
        seen.add(name)

        if not isinstance(n, int) or n <= 0:
            raise AllocationError("cards_for_entity_exact must be int > 0")
        total += int(n)

    if total != S0_SET_TARGET_CARDS:
        raise AllocationError(f"sum(cards_for_entity_exact) must equal {S0_SET_TARGET_CARDS} in S0 (v2.0)")

    checksum = artifact.get("allocation_checksum") or {}
    if checksum.get("sum_cards") != S0_SET_TARGET_CARDS:
        raise AllocationError("allocation_checksum.sum_cards mismatch")
    if checksum.get("entity_count_used") != len(allocs):
        raise AllocationError("allocation_checksum.entity_count_used mismatch")


def _validate_s0_allocation_artifact_v2_1(artifact: Dict[str, Any]) -> None:
    """
    Validate S0 allocation artifact against v2.1 invariants.
    v2.1: deterministic prefix 3×4 (E>=4) else deterministic even split (E<4).
    """
    if artifact.get("allocation_version") != S0_ALLOCATION_VERSION_V2_1:
        raise AllocationError("allocation_version mismatch (expected v2.1)")

    if artifact.get("mode") != "S0":
        raise AllocationError("mode must be 'S0'")

    if artifact.get("set_target_cards") != S0_SET_TARGET_CARDS:
        raise AllocationError(f"set_target_cards must be {S0_SET_TARGET_CARDS}")

    entities_from_s1 = artifact.get("entities_from_s1")
    if not isinstance(entities_from_s1, list) or not entities_from_s1:
        raise AllocationError("entities_from_s1 must be a non-empty list")

    selected_entities = artifact.get("selected_entities")
    if not isinstance(selected_entities, list) or not selected_entities:
        raise AllocationError("selected_entities must be a non-empty list")

    # policy (v2.1)
    policy = artifact.get("entity_selection_policy") or {}
    if not isinstance(policy, dict):
        raise AllocationError("entity_selection_policy must be an object")
    if policy.get("type") != "deterministic_prefix":
        raise AllocationError("entity_selection_policy.type must be 'deterministic_prefix' (v2.1)")

    # legacy param recording (optional)
    if "spread_mode_legacy" in policy and policy["spread_mode_legacy"] not in ALLOWED_SPREAD_MODES:
        raise AllocationError("entity_selection_policy.spread_mode_legacy invalid")

    # selected_entities must be prefix-min(4,E) or all when E<4
    E = len(entities_from_s1)
    expected = entities_from_s1[:4] if E >= 4 else entities_from_s1[:]
    if selected_entities != expected:
        raise AllocationError("selected_entities must equal deterministic prefix selection from entities_from_s1")

    allocs = artifact.get("entity_allocations")
    if not isinstance(allocs, list) or len(allocs) < 1:
        raise AllocationError("entity_allocations must contain at least 1 entry in S0 (v2.1)")
    if len(allocs) != len(selected_entities):
        raise AllocationError("entity_allocations length must equal selected_entities length (v2.1)")

    seen = set()
    total = 0
    for row in allocs:
        if not isinstance(row, dict):
            raise AllocationError("each entity_allocations row must be an object")
        name = row.get("entity_name")
        n = row.get("cards_for_entity_exact")

        if not isinstance(name, str) or not name.strip():
            raise AllocationError("entity_name must be a non-empty string")
        if name not in entities_from_s1:
            raise AllocationError("entity_name must be contained in entities_from_s1")
        if name in seen:
            raise AllocationError("duplicate entity_name in entity_allocations")
        seen.add(name)

        if not isinstance(n, int) or n <= 0:
            raise AllocationError("cards_for_entity_exact must be int > 0")
        total += int(n)

    if total != S0_SET_TARGET_CARDS:
        raise AllocationError(f"sum(cards_for_entity_exact) must equal {S0_SET_TARGET_CARDS} in S0 (v2.1)")

    # 3×4 enforcement when E>=4
    if E >= 4:
        if len(allocs) != 4:
            raise AllocationError("v2.1 requires exactly 4 allocations when E>=4")
        for row in allocs:
            if int(row["cards_for_entity_exact"]) != 3:
                raise AllocationError("v2.1 requires cards_for_entity_exact == 3 for all selected entities when E>=4")

    checksum = artifact.get("allocation_checksum") or {}
    if checksum.get("sum_cards") != S0_SET_TARGET_CARDS:
        raise AllocationError("allocation_checksum.sum_cards mismatch")
    if checksum.get("entity_count_used") != len(allocs):
        raise AllocationError("allocation_checksum.entity_count_used mismatch")

    if "allocation_checksum" in artifact and not isinstance(artifact["allocation_checksum"], dict):
        raise AllocationError("allocation_checksum must be an object")

    if "allocation_metrics" in artifact and not isinstance(artifact["allocation_metrics"], dict):
        raise AllocationError("allocation_metrics must be an object if present")


def validate_s0_allocation_artifact(artifact: Dict[str, Any]) -> None:
    """
    Version-dispatch validator. Fails fast on unknown versions.
    """
    v = artifact.get("allocation_version")
    if v == S0_ALLOCATION_VERSION_V2_1:
        _validate_s0_allocation_artifact_v2_1(artifact)
        return
    if v == S0_ALLOCATION_VERSION_V2_0:
        _validate_s0_allocation_artifact_v2_0_legacy(artifact)
        return
    if v == S0_ALLOCATION_VERSION_V1_0:
        _validate_s0_allocation_artifact_v1(artifact)
        return
    raise AllocationError(f"unknown allocation_version: {v}")


# =========================
# Builders / Loaders
# =========================

def build_s0_allocation_artifact(
    base_dir: Path,
    inp: S0AllocationInputs,
    spread_mode: str = SPREAD_MODE_HARD,
) -> Path:
    """
    Build and persist S0 allocation artifact (v2.1, canonical).

    Note:
    - spread_mode is accepted only for backward API compatibility.
      It does NOT affect allocation under v2.1, and is recorded as spread_mode_legacy.
    """
    if spread_mode not in ALLOWED_SPREAD_MODES:
        raise AllocationError(f"invalid spread_mode: {spread_mode}")

    entities = _sanitize_entities_from_s1(inp.entities_from_s1)
    if not entities:
        raise AllocationError("S1 entity_list is empty or invalid")

    selected_entities, allocs = _alloc_prefix_3x4_or_fallback(entities)

    # compute checksum + metrics
    sum_cards = sum(int(r["cards_for_entity_exact"]) for r in allocs)
    if sum_cards != S0_SET_TARGET_CARDS:
        raise AllocationError("internal error: allocation does not sum to set target")

    metrics = _alloc_metrics_from_allocs(allocs)

    rule = "3x4: if E>=4 use first_4_entities_each_3_cards else deterministic_even_split_over_all_entities"

    artifact: Dict[str, Any] = {
        "allocation_version": S0_ALLOCATION_VERSION_V2_1,
        "run_tag": inp.run_tag,
        "mode": "S0",
        "group_id": inp.group_id,
        "arm": inp.arm,

        "set_target_cards": S0_SET_TARGET_CARDS,

        "entity_selection_policy": {
            "type": "deterministic_prefix",
            "rule": rule,
            "selection": "deterministic_prefix_from_S1_order",
            # legacy trace only (non-binding)
            "spread_mode_legacy": spread_mode,
        },

        "entities_from_s1": entities,
        "selected_entities": selected_entities,

        "entity_allocations": allocs,

        "allocation_checksum": {
            "sum_cards": S0_SET_TARGET_CARDS,
            "entity_count_used": len(allocs),
        },

        # analysis helpers (non-binding)
        "allocation_metrics": metrics,

        # audit helpers
        "created_ts_unix": int(time.time()),
        "created_by": os.getenv("USER") or None,
    }

    # pre-write validation
    validate_s0_allocation_artifact(artifact)

    out_path = get_s0_allocation_path(
        base_dir=base_dir,
        run_tag=inp.run_tag,
        group_id=inp.group_id,
        arm=inp.arm,
    )

    _atomic_write_json(out_path, artifact)

    # post-write validation (defensive)
    with out_path.open("r", encoding="utf-8") as f:
        reloaded = json.load(f)
    validate_s0_allocation_artifact(reloaded)

    return out_path


def require_valid_s0_allocation_artifact(path: Path) -> Dict[str, Any]:
    """
    Guard for S2 execution.
    Ensures allocation artifact exists, is readable, and valid.
    """
    if not path.exists():
        raise AllocationError(f"S0 allocation artifact missing: {path}")
    if path.stat().st_size <= 0:
        raise AllocationError(f"S0 allocation artifact is empty (0B): {path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            obj = json.load(f)
    except Exception as e:
        raise AllocationError(f"S0 allocation artifact invalid JSON: {path}") from e

    validate_s0_allocation_artifact(obj)
    return obj


def s0_artifact_to_s2_targets(artifact: Dict[str, Any]) -> Tuple[S2ExecutionTarget, ...]:
    """
    Convert S0 allocation artifact into S2 execution targets.

    v2.1: returns 1..4 targets (typically 4 when E>=4)
    v2.0: returns 1..N targets (legacy spread)
    v1.0: returns exactly 1 target (representative entity only)
    """
    validate_s0_allocation_artifact(artifact)

    allocs = artifact["entity_allocations"]
    targets: List[S2ExecutionTarget] = []
    for row in allocs:
        targets.append(
            S2ExecutionTarget(
                entity_name=row["entity_name"],
                cards_for_entity_exact=int(row["cards_for_entity_exact"]),
            )
        )
    return tuple(targets)
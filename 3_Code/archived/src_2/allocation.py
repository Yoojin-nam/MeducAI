"""
MeducAI FINAL card allocation
- Weight transform (NONE / LOG1P / SQRT)
- Min/Max caps per group
- Constrained Hamilton-style apportionment (largest remainder) with rebalancing

Design goals:
- Deterministic
- Sum of allocations == total_cards (if feasible under caps)
- Respects min/max for every group
- Works even when some weights are zero (falls back to uniform among eligible)

Author: MeducAI
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Dict, Literal, Tuple, List


WeightTransform = Literal["NONE", "LOG1P", "SQRT"]
RoundingMethod = Literal["HAMILTON"]


@dataclass(frozen=True)
class AllocationParams:
    total_cards: int
    min_cards_per_group: int
    max_cards_per_group: int
    weight_transform: WeightTransform = "LOG1P"
    rounding: RoundingMethod = "HAMILTON"


def transform_weight(w: float, method: WeightTransform) -> float:
    """Transforms raw weights to reduce skew."""
    if w is None or not math.isfinite(w):
        return 0.0
    if w <= 0:
        return 0.0

    if method == "NONE":
        return float(w)
    if method == "LOG1P":
        return math.log1p(float(w))
    if method == "SQRT":
        return math.sqrt(float(w))

    raise ValueError(f"Unknown weight_transform: {method}")


def _validate_params(n_groups: int, params: AllocationParams) -> None:
    if n_groups <= 0:
        raise ValueError("group_weights must contain at least 1 group")

    if params.total_cards <= 0:
        raise ValueError("total_cards must be > 0")

    if params.min_cards_per_group < 0:
        raise ValueError("min_cards_per_group must be >= 0")

    if params.max_cards_per_group < 0:
        raise ValueError("max_cards_per_group must be >= 0")

    if params.min_cards_per_group > params.max_cards_per_group:
        raise ValueError("min_cards_per_group cannot exceed max_cards_per_group")

    min_possible = n_groups * params.min_cards_per_group
    max_possible = n_groups * params.max_cards_per_group

    if params.total_cards < min_possible:
        raise ValueError(
            f"Infeasible allocation: total_cards={params.total_cards} < "
            f"n_groups*min={min_possible}"
        )
    if params.total_cards > max_possible:
        raise ValueError(
            f"Infeasible allocation: total_cards={params.total_cards} > "
            f"n_groups*max={max_possible}"
        )


def allocate_cards_by_weight(
    group_weights: Dict[str, float],
    params: AllocationParams,
) -> Dict[str, int]:
    """
    Constrained proportional allocation with caps.

    Algorithm (FINAL only):
    1) transformed weights w_i (>=0)
    2) allocate base min to all groups
    3) distribute remaining cards proportionally with largest remainder (Hamilton)
       while respecting remaining capacity (max - current)
    4) iterate if some groups saturate early

    Returns:
        target_cards_per_group dict (group_id -> int), sum == total_cards
    """
    group_ids = list(group_weights.keys())
    _validate_params(len(group_ids), params)

    # Transform weights
    tw: Dict[str, float] = {
        gid: transform_weight(group_weights.get(gid, 0.0), params.weight_transform)
        for gid in group_ids
    }

    # Start with minimum allocation
    alloc: Dict[str, int] = {gid: int(params.min_cards_per_group) for gid in group_ids}
    remaining = params.total_cards - sum(alloc.values())

    # Quick exit if remaining == 0
    if remaining == 0:
        return alloc

    # Helper: eligible groups that still have capacity
    def eligible_groups() -> List[str]:
        return [gid for gid in group_ids if alloc[gid] < params.max_cards_per_group]

    # Helper: remaining capacity
    def cap_left(gid: str) -> int:
        return params.max_cards_per_group - alloc[gid]

    # If all weights are zero, distribute uniformly among eligible
    # (but still deterministic by sorted group_id order)
    def sum_weights(gids: List[str]) -> float:
        return float(sum(tw[g] for g in gids))

    # Iteratively distribute remaining, re-normalizing among non-saturated groups
    # until remaining == 0.
    while remaining > 0:
        elig = eligible_groups()
        if not elig:
            # Should never happen due to feasibility check.
            raise RuntimeError("No eligible groups left but remaining > 0 (unexpected).")

        sw = sum_weights(elig)

        # Compute ideal additional quotas for this iteration
        ideal_add: Dict[str, float] = {}
        if sw > 0:
            for gid in elig:
                ideal_add[gid] = remaining * (tw[gid] / sw)
        else:
            # All weights zero among eligible: uniform
            u = remaining / len(elig)
            for gid in elig:
                ideal_add[gid] = u

        # Floor allocation (respect capacity)
        add_floor: Dict[str, int] = {}
        used = 0
        for gid in elig:
            flo = int(math.floor(ideal_add[gid]))
            flo = max(0, flo)
            flo = min(flo, cap_left(gid))
            add_floor[gid] = flo
            used += flo

        # Apply floors
        if used > 0:
            for gid, a in add_floor.items():
                alloc[gid] += a
            remaining -= used
            if remaining == 0:
                break

        # Largest remainder distribution for the leftover (still respect capacity)
        # Use fractional parts from this iteration's ideals.
        # Deterministic tie-break: (fraction desc, weight desc, group_id asc)
        remainders: List[Tuple[float, float, str]] = []
        for gid in elig:
            if cap_left(gid) <= 0:
                continue
            frac = ideal_add[gid] - math.floor(ideal_add[gid])
            # if ideal_add < 0 (shouldn't), protect
            if frac < 0:
                frac = 0.0
            remainders.append((frac, tw[gid], gid))

        remainders.sort(key=lambda x: (-x[0], -x[1], x[2]))

        # If no remainders available (e.g., everyone saturated after floors),
        # loop will re-evaluate elig and continue.
        if not remainders:
            continue

        # Assign one by one
        i = 0
        while remaining > 0 and i < len(remainders):
            _, _, gid = remainders[i]
            if cap_left(gid) > 0:
                alloc[gid] += 1
                remaining -= 1
            i += 1

        # If remaining > 0 after one pass, we loop again:
        # - some groups may still have capacity
        # - re-normalize ideals among currently eligible groups

    # Final sanity checks
    total = sum(alloc.values())
    if total != params.total_cards:
        raise RuntimeError(
            f"Allocation sum mismatch: got {total}, expected {params.total_cards}"
        )
    for gid, v in alloc.items():
        if v < params.min_cards_per_group or v > params.max_cards_per_group:
            raise RuntimeError(
                f"Cap violation for {gid}: {v} not in "
                f"[{params.min_cards_per_group},{params.max_cards_per_group}]"
            )

    return alloc


def save_target_cards_json(
    target: Dict[str, int],
    out_path: str,
    meta: Dict[str, object] | None = None,
) -> None:
    """Optional helper to persist freeze log."""
    payload = {
        "meta": meta or {},
        "target_cards_per_group": target,
        "sum": int(sum(target.values())),
        "n_groups": int(len(target)),
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

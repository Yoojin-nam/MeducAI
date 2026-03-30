# -*- coding: utf-8 -*-
"""
MeducAI - generation_policy.py
FINAL candidate generation policy (over-generate + retry) to prevent shortfall.

This module is intentionally independent so Step01 can import it without
creating circular dependencies.

Author: MeducAI
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class CandidateGenPolicy:
    overgen_factor: float
    overgen_add: int
    max_candidates_per_group: int
    retry_rounds: int
    retry_extra: int


def load_policy_from_env() -> CandidateGenPolicy:
    def _f(key: str, default: float) -> float:
        v = os.getenv(key, "")
        return default if v == "" else float(v)

    def _i(key: str, default: int) -> int:
        v = os.getenv(key, "")
        return default if v == "" else int(v)

    return CandidateGenPolicy(
        overgen_factor=_f("FINAL_OVERGEN_FACTOR", 1.6),
        overgen_add=_i("FINAL_OVERGEN_ADD", 2),
        max_candidates_per_group=_i("MAX_CANDIDATES_PER_GROUP", 30),
        retry_rounds=_i("FINAL_RETRY_ROUNDS", 2),
        retry_extra=_i("FINAL_RETRY_EXTRA", 3),
    )


def compute_candidate_count(q: int, pol: CandidateGenPolicy) -> int:
    """
    Compute candidate generation target n_candidates for a group with quota q.

    Rule:
      n = ceil(q * factor) + add
      n = min(n, max_candidates_per_group)

    Hard constraints:
      - q must be >= 0
      - If q > max_candidates_per_group, it is a configuration error for FINAL.
        (Because you'd never be able to generate enough candidates under cap.)
    """
    if q < 0:
        raise ValueError(f"quota must be >= 0, got {q}")

    if q == 0:
        return 0

    if pol.max_candidates_per_group <= 0:
        raise ValueError("max_candidates_per_group must be > 0")

    if q > pol.max_candidates_per_group:
        raise ValueError(
            "Impossible FINAL candidate policy: quota exceeds MAX_CANDIDATES_PER_GROUP.\n"
            f"quota={q}, MAX_CANDIDATES_PER_GROUP={pol.max_candidates_per_group}\n"
            "Fix: increase MAX_CANDIDATES_PER_GROUP or reduce MAX_CARDS_PER_GROUP/total_cards."
        )

    n = int(math.ceil(q * float(pol.overgen_factor)) + int(pol.overgen_add))
    n = max(n, q)  # never below quota
    n = min(n, int(pol.max_candidates_per_group))
    return n


def load_target_quota_json(path: str) -> Dict[str, int]:
    """
    Load target_cards_per_group from:
      target_cards_per_group_<RUN_TAG>__armX.json

    Returns:
      { group_id: quota_int }
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"target quota json not found: {p}")

    obj = json.loads(p.read_text(encoding="utf-8"))
    if "target_cards_per_group" not in obj:
        raise KeyError(f"Missing key 'target_cards_per_group' in {p}")

    raw = obj["target_cards_per_group"]
    if not isinstance(raw, dict):
        raise TypeError(f"target_cards_per_group must be dict, got {type(raw)}")

    out: Dict[str, int] = {}
    for k, v in raw.items():
        try:
            out[str(k)] = int(v)
        except Exception as e:
            raise ValueError(f"Bad quota value for {k}: {v!r} ({e})")
    return out


def compute_candidate_plan(
    quota: Dict[str, int],
    pol: CandidateGenPolicy,
) -> Dict[str, int]:
    """
    Convert quota per group -> candidates per group.
    """
    plan: Dict[str, int] = {}
    for gid, q in quota.items():
        plan[gid] = compute_candidate_count(q, pol)
    return plan


def missing_quota_after_counts(
    quota: Dict[str, int],
    counts: Dict[str, int],
) -> Dict[str, int]:
    """
    Return missing {gid: missing_count} where counts < quota.
    """
    missing: Dict[str, int] = {}
    for gid, q in quota.items():
        got = int(counts.get(gid, 0))
        if got < q:
            missing[gid] = q - got
    return missing


def compute_retry_target(missing_q: int, pol: CandidateGenPolicy) -> int:
    """
    For a group that is missing missing_q cards, generate:
      missing_q + retry_extra
    (capped by max_candidates_per_group is intentionally NOT applied here,
     because this is an incremental add; Step01 should enforce a total cap policy if desired.)
    """
    if missing_q <= 0:
        return 0
    return int(missing_q + int(pol.retry_extra))

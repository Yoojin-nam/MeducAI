"""
Focused test group sets (small, human-curated lists).

These are used to avoid repeatedly copy/pasting long --only_group_id lists during
targeted investigations/regenerations.
"""

from __future__ import annotations

from typing import Dict, List


# From plan: "Anatomy_Map 8개 그룹 집중 테스트 플랜" (includes the known failure case grp_a8b30bdbb7).
ANATOMY_MAP_FOCUS_8_GROUP_IDS: List[str] = [
    "grp_a8b30bdbb7",  # known problematic case (temporal/facial bone clusters)
    "grp_0a283963db",  # pulmonary artery anatomy
    "grp_47059b1c5d",  # liver segments
    "grp_5778ad2ed4",  # biliary/GB anatomy & variants
    "grp_180c68cb1a",  # neck/skull base spaces & vessels
    "grp_ebdc9f5c1e",  # female reproductive anatomy
    "grp_ed69308598",  # breast anatomy/mammo
    "grp_cb76c6fb1e",  # colon/appendix/rectum anatomy
]


FOCUS_GROUP_SETS: Dict[str, List[str]] = {
    "anatomy_map_8": ANATOMY_MAP_FOCUS_8_GROUP_IDS,
}


def get_focus_group_ids(set_name: str) -> List[str]:
    """
    Resolve a focus group set name into a list of group_ids.
    """
    key = (set_name or "").strip()
    if not key:
        raise ValueError("set_name is empty")
    if key not in FOCUS_GROUP_SETS:
        raise KeyError(f"Unknown focus group set: {key}. Available: {sorted(FOCUS_GROUP_SETS.keys())}")
    return list(FOCUS_GROUP_SETS[key])



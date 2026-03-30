"""
S6 Export Manifest utilities.

The S6 export manifest decides, per `group_id`, whether downstream exporters
(PDF packet builder / Anki exporter) should use baseline artifacts or repaired artifacts.

This module is intentionally small and dependency-free so it can be imported from
CLI scripts without pulling in the rest of the pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def load_export_manifest(manifest_path: Optional[Path]) -> Dict[str, bool]:
    """
    Load an export manifest and return a mapping: group_id -> use_repaired (bool).

    Supported shapes:
      1) {"entries": [{"group_id": "...", "use_repaired": true}, ...]}
      2) {"groups": {"<group_id>": {"use_repaired": true, ...}, ...}}
      3) {"groups": {"<group_id>": true, ...}}  (bool shorthand)

    If `manifest_path` is None, returns {}.
    """
    if manifest_path is None:
        return {}

    p = Path(manifest_path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Export manifest not found: {p}")

    with p.open("r", encoding="utf-8") as f:
        payload: Any = json.load(f)

    out: Dict[str, bool] = {}

    if isinstance(payload, dict) and isinstance(payload.get("entries"), list):
        for e in payload.get("entries") or []:
            if not isinstance(e, dict):
                continue
            gid = str(e.get("group_id") or "").strip()
            if not gid:
                continue
            out[gid] = bool(e.get("use_repaired"))
        return out

    if isinstance(payload, dict) and isinstance(payload.get("groups"), dict):
        groups = payload.get("groups") or {}
        for gid, v in groups.items():
            gid_s = str(gid or "").strip()
            if not gid_s:
                continue
            if isinstance(v, dict):
                out[gid_s] = bool(v.get("use_repaired"))
            else:
                out[gid_s] = bool(v)
        return out

    raise ValueError(
        "Unsupported export manifest JSON shape. Expected keys: 'entries' or 'groups'."
    )


def should_use_repaired(
    manifest: Dict[str, bool],
    *,
    group_id: str,
    default: bool = False,
) -> bool:
    """Return True if the manifest selects repaired artifacts for this group."""
    gid = str(group_id or "").strip()
    if not gid:
        return default
    return bool(manifest.get(gid, default))



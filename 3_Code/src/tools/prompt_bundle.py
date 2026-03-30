from __future__ import annotations

from pathlib import Path
import hashlib
import json as _json
from typing import Any, Dict, Optional, Union

def _resolve_repo_root(start: Path) -> Path:
    """
    Walk upwards to find MeducAI repo root.
    Heuristic: presence of '3_Code' and '2_Data' directories.
    """
    cur = start.resolve()
    for _ in range(5):
        if (cur / "3_Code").exists() and (cur / "2_Data").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise RuntimeError("Could not resolve MeducAI repo root")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def load_prompt_bundle(base_dir: str, registry_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Load prompts from 3_Code/prompt.

    Returns dict:
      - prompts: {key: text}
      - prompt_file_ids: {key: filename}
      - prompt_bundle_hash: sha256 hex
      - prompt_dir: absolute path
      - registry_path: absolute path to the registry json used
    """
    base_dir_p = Path(base_dir).resolve()
    repo_root = _resolve_repo_root(base_dir_p)
    prompt_dir = (repo_root / "3_Code" / "prompt").resolve()
    resolved_registry_path: Path
    if registry_path is None:
        resolved_registry_path = prompt_dir / "_registry.json"
    else:
        rp = Path(registry_path).expanduser()
        resolved_registry_path = (rp if rp.is_absolute() else (repo_root / rp)).resolve()

    if resolved_registry_path.exists():
        reg = _json.loads(_read_text(resolved_registry_path))
    else:
        # 하드코딩 대신 에러 발생 (또는 빈 dict 리턴)
        raise FileNotFoundError(f"Registry not found at {resolved_registry_path}")

    prompts = {}
    prompt_file_ids = {}
    bundle_parts = []

    for k, fn in reg.items():
        p = prompt_dir / fn
        txt = (_read_text(p).strip() + "\n") if p.exists() else ""
        prompts[k] = txt
        prompt_file_ids[k] = fn
        bundle_parts.append(f"## {k}::{fn}\n{txt}")

    prompt_bundle_hash = hashlib.sha256("".join(bundle_parts).encode("utf-8")).hexdigest()

    return {
        "prompts": prompts,
        "prompt_file_ids": prompt_file_ids,
        "prompt_bundle_hash": prompt_bundle_hash,
        "prompt_dir": str(prompt_dir),
        "registry_path": str(resolved_registry_path),
    }

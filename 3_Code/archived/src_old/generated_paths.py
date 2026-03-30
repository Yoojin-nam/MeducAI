from __future__ import annotations
from pathlib import Path

def generated_root(base_dir: Path) -> Path:
    return base_dir / "2_Data" / "metadata" / "generated"

def generated_run_dir(base_dir: Path, run_tag_base: str) -> Path:
    d = generated_root(base_dir) / run_tag_base
    d.mkdir(parents=True, exist_ok=True)
    return d

def legacy_provider_dir(base_dir: Path, provider: str) -> Path:
    return generated_root(base_dir) / provider

def resolve_in_run_or_legacy(base_dir: Path, run_tag_base: str, provider: str, filename: str) -> Path:
    """
    Read path resolver:
    1) generated/<run_tag_base>/<filename>
    2) generated/<provider>/<filename> (legacy)
    3) generated/<filename> (older flat)
    """
    root = generated_root(base_dir)
    p1 = root / run_tag_base / filename
    if p1.exists():
        return p1
    p2 = legacy_provider_dir(base_dir, provider) / filename
    if p2.exists():
        return p2
    return root / filename

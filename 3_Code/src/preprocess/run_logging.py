#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def make_run_id(prefix: str = "v2") -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}_{ts}"


def default_logs_dir(repo_root: Path) -> Path:
    return repo_root / "2_Data" / "processed" / "logs"


@dataclass(frozen=True)
class RunArtifacts:
    run_id: str
    log_jsonl: Path
    prompts_txt: Path


def make_default_artifacts(repo_root: Path, run_id: str) -> RunArtifacts:
    logs_dir = default_logs_dir(repo_root)
    return RunArtifacts(
        run_id=run_id,
        log_jsonl=logs_dir / f"{run_id}.jsonl",
        prompts_txt=logs_dir / f"{run_id}.system_prompts.txt",
    )


class JsonlLogger:
    def __init__(self, path: Path, run_id: str) -> None:
        self.path = path
        self.run_id = run_id
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: Dict[str, Any]) -> None:
        base = {"run_id": self.run_id, "ts": utc_now_iso()}
        out = {**base, **event}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(out, ensure_ascii=False) + "\n")


class Timer:
    def __init__(self) -> None:
        self.t0 = time.time()

    def elapsed_s(self) -> float:
        return float(time.time() - self.t0)


def append_system_prompt(prompts_path: Path, section: str, prompt: str) -> None:
    prompts_path.parent.mkdir(parents=True, exist_ok=True)
    with open(prompts_path, "a", encoding="utf-8") as f:
        f.write(f"## {section}\n")
        f.write(f"- recorded_at: {utc_now_iso()}\n")
        f.write(prompt.strip() + "\n\n")


def safe_env_hint() -> Dict[str, Any]:
    """
    High-level environment info only (never includes secrets).
    """
    return {
        "cwd": str(Path.cwd()),
        "python": os.environ.get("PYTHON_VERSION") or "",
    }



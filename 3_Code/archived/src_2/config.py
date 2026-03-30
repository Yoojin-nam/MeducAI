# 3_Code/src/config.py
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from dotenv import load_dotenv

Mode = Literal["S0", "FINAL"]


@dataclass(frozen=True)
class RunConfig:
    base_dir: str
    run_tag: str
    mode: Mode
    arm: str
    seed: int
    provider_text: str
    total_cards: Optional[int] = None
    daily_study_cards: Optional[int] = None


def load_env_defaults(base_dir: str) -> Dict[str, Any]:
    """
    Loads .env (if present) and returns a dict of defaults used by runtime guards.
    Keep this function intentionally small: only variables that influence safety gates.
    """
    # Ensure .env in project root is loaded if present
    env_path = os.path.join(base_dir, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path, override=False)

    def _get(key: str, default: Optional[str] = None) -> Optional[str]:
        v = os.getenv(key)
        return v if v is not None and v != "" else default

    def _get_int(key: str, default: Optional[int] = None) -> Optional[int]:
        v = _get(key, None)
        if v is None:
            return default
        try:
            return int(v)
        except ValueError:
            raise ValueError(f"Invalid int for env {key}={v!r}")

    env: Dict[str, Any] = {
        # Guard-rail: mode/budget alignment
        "CARD_BUDGET_MODE": _get("CARD_BUDGET_MODE", None),  # expected: S0_FIXED_PAYLOAD or TOTAL_WEIGHTED_DISTRIBUTION
        "S0_FIXED_PAYLOAD_CARDS": _get_int("S0_FIXED_PAYLOAD_CARDS", 12),
        "DAILY_STUDY_CARDS_DEFAULT": _get_int("DAILY_STUDY_CARDS_DEFAULT", None),
    }
    return env


def validate_mode_budget(cfg: RunConfig, env: Dict[str, Any]) -> RunConfig:
    """
    Enforces:
      - S0 ignores total_cards (policy: warn+ignore handled upstream) but cannot be FINAL budget mode.
      - FINAL requires total_cards.
      - env CARD_BUDGET_MODE must align with cfg.mode (hard error if mismatch).
    Returns possibly-updated cfg (e.g., daily_study_cards default injected).
    """
    mode = cfg.mode
    cbm = env.get("CARD_BUDGET_MODE")

    # Hard alignment check (prevents silent “wrong branch” runs)
    if mode == "S0":
        if cbm and cbm != "S0_FIXED_PAYLOAD":
            raise RuntimeError(
                f"Mode/env mismatch: --mode S0 requires CARD_BUDGET_MODE=S0_FIXED_PAYLOAD, got {cbm!r}"
            )
    elif mode == "FINAL":
        if cbm and cbm != "TOTAL_WEIGHTED_DISTRIBUTION":
            raise RuntimeError(
                f"Mode/env mismatch: --mode FINAL requires CARD_BUDGET_MODE=TOTAL_WEIGHTED_DISTRIBUTION, got {cbm!r}"
            )
    else:
        raise RuntimeError(f"Unknown mode: {mode}")

    # FINAL requires total_cards
    if mode == "FINAL" and (cfg.total_cards is None or cfg.total_cards <= 0):
        raise RuntimeError("--mode FINAL requires --total_cards > 0")

    # Inject daily default if missing (FINAL only; S0 may ignore)
    daily = cfg.daily_study_cards
    if daily is None and mode == "FINAL":
        default_daily = env.get("DAILY_STUDY_CARDS_DEFAULT")
        if isinstance(default_daily, int) and default_daily > 0:
            # frozen dataclass: create new
            cfg = RunConfig(
                base_dir=cfg.base_dir,
                run_tag=cfg.run_tag,
                mode=cfg.mode,
                arm=cfg.arm,
                seed=cfg.seed,
                provider_text=cfg.provider_text,
                total_cards=cfg.total_cards,
                daily_study_cards=default_daily,
            )

    return cfg


def write_run_manifest(cfg: RunConfig, env: Dict[str, Any], out_path: str) -> None:
    """
    Writes a minimal MI-CLEAR-friendly run manifest for auditing.
    Keep it stable; add fields only deliberately.
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    payload: Dict[str, Any] = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "run_config": asdict(cfg),
        "env_guard": {
            "CARD_BUDGET_MODE": env.get("CARD_BUDGET_MODE"),
            "S0_FIXED_PAYLOAD_CARDS": env.get("S0_FIXED_PAYLOAD_CARDS"),
            "DAILY_STUDY_CARDS_DEFAULT": env.get("DAILY_STUDY_CARDS_DEFAULT"),
        },
        # Useful for forensic reproducibility
        "python": {
            "executable": os.sys.executable,
            "cwd": os.getcwd(),
        },
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

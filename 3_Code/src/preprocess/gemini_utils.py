#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Optional


def _strip_code_fences(s: str) -> str:
    t = (s or "").strip()
    if t.startswith("```json"):
        t = t[len("```json") :].strip()
        if t.endswith("```"):
            t = t[: -len("```")].strip()
    elif t.startswith("```"):
        t = t[len("```") :].strip()
        if t.endswith("```"):
            t = t[: -len("```")].strip()
    return t


def _extract_outer_json(s: str) -> str:
    """
    Best-effort extraction of the outermost JSON object/array from model output.
    """
    t = (s or "").strip()
    if not t:
        return t
    # Prefer object
    if "{" in t and "}" in t:
        a = t.find("{")
        b = t.rfind("}")
        if 0 <= a < b:
            return t[a : b + 1].strip()
    # Fallback to array
    if "[" in t and "]" in t:
        a = t.find("[")
        b = t.rfind("]")
        if 0 <= a < b:
            return t[a : b + 1].strip()
    return t


def _parse_first_json_value(s: str) -> Any:
    """
    Parse the first JSON value (object/array) from a string and ignore trailing text.
    This handles Gemini outputs like: `<json>\\n\\nSome explanation...` or multiple JSON blocks.
    """
    t = (s or "").strip()
    if not t:
        raise json.JSONDecodeError("Empty input", t, 0)

    # Find the first plausible JSON start.
    i_obj = t.find("{")
    i_arr = t.find("[")
    candidates = [i for i in [i_obj, i_arr] if i >= 0]
    if not candidates:
        raise json.JSONDecodeError("No JSON start token found", t, 0)
    start = min(candidates)

    dec = json.JSONDecoder()
    val, _end = dec.raw_decode(t, start)
    return val


def _loads_json_robust(s: str) -> Any:
    """
    Robust JSON loader for Gemini outputs.
    Known failure mode: raw newlines inside JSON string values (unterminated string).
    Strategy:
    - strip code fences
    - parse first JSON value (ignore trailing text)
    - if fails, replace CR/LF with spaces and retry
    """
    try:
        return _parse_first_json_value(_strip_code_fences(s))
    except Exception:
        # Second try: normalize newlines (common broken JSON case)
        t2 = _strip_code_fences(s).replace("\r", " ").replace("\n", " ")
        try:
            return _parse_first_json_value(t2)
        except Exception:
            # Last resort: attempt outermost extraction then parse first JSON again
            t3 = _extract_outer_json(t2)
            return _parse_first_json_value(t3)


def _get_api_key() -> str:
    # Load `.env` if present (repo already depends on python-dotenv).
    try:
        from dotenv import load_dotenv  # type: ignore
        from pathlib import Path

        env_path = Path.cwd() / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
        else:
            # Fallback: best-effort (may rely on find_dotenv)
            load_dotenv()
    except Exception:
        pass

    # Prefer repo-friendly env var name; allow legacy name used in Colab secrets.
    return (
        os.environ.get("RAB_LLM_API_KEY")
        or os.environ.get("GOOGLE_API_KEY_10")
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("RaB-LLM")
        or os.environ.get("GEMINI_API_KEY")
        or ""
    ).strip()


@dataclass(frozen=True)
class GeminiConfig:
    model: str
    temperature: float = 0.0
    top_p: float = 1.0
    top_k: int = 1
    max_output_tokens: int = 8192
    response_mime_type: Optional[str] = "application/json"
    retries: int = 3
    backoff_s: float = 0.5


class GeminiClient:
    def __init__(self, cfg: GeminiConfig, api_key: Optional[str] = None) -> None:
        self.cfg = cfg
        self.api_key = (api_key or _get_api_key()).strip()
        if not self.api_key:
            raise RuntimeError(
                "Missing Gemini API key. Set env var RAB_LLM_API_KEY (preferred) "
                "or GEMINI_API_KEY."
            )

        # NOTE: Import inside init to avoid sandbox syscall issues unless the caller
        # runs with broader permissions (required for this repo environment).
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore

        self._types = types
        self._client = genai.Client(api_key=self.api_key)

    def generate_json(self, prompt_data: Any, system_instruction: str) -> Any:
        """
        Calls Gemini with deterministic settings and returns parsed JSON response.
        `prompt_data` should be a string (already JSON-encoded) for best reliability.
        """
        last_err: Optional[Exception] = None
        for attempt in range(self.cfg.retries):
            try:
                cfg = self._types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=self.cfg.temperature,
                    top_p=self.cfg.top_p,
                    top_k=self.cfg.top_k,
                    candidate_count=1,
                    max_output_tokens=self.cfg.max_output_tokens,
                    response_mime_type=self.cfg.response_mime_type,
                )
                resp = self._client.models.generate_content(
                    model=self.cfg.model,
                    contents=prompt_data,
                    config=cfg,
                )
                txt = getattr(resp, "text", "") or ""
                return _loads_json_robust(txt)
            except Exception as e:  # noqa: BLE001
                last_err = e
                time.sleep(self.cfg.backoff_s * (attempt + 1))
                continue
        raise RuntimeError(f"Gemini call failed after {self.cfg.retries} attempts: {last_err}") from last_err

    def generate_json_with_meta(self, prompt_data: Any, system_instruction: str) -> tuple[Any, dict[str, Any]]:
        """
        Same as generate_json(), but also returns lightweight runtime metadata
        suitable for MI-CLEAR-style logging (no secrets).
        """
        import time as _time

        t0 = _time.time()
        last_err: Optional[Exception] = None
        attempts = 0
        for attempt in range(self.cfg.retries):
            attempts = attempt + 1
            try:
                cfg = self._types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=self.cfg.temperature,
                    top_p=self.cfg.top_p,
                    top_k=self.cfg.top_k,
                    candidate_count=1,
                    max_output_tokens=self.cfg.max_output_tokens,
                    response_mime_type=self.cfg.response_mime_type,
                )
                resp = self._client.models.generate_content(
                    model=self.cfg.model,
                    contents=prompt_data,
                    config=cfg,
                )
                txt = getattr(resp, "text", "") or ""
                data = _loads_json_robust(txt)
                meta = {
                    "ok": True,
                    "attempts_used": attempts,
                    "elapsed_s": float(_time.time() - t0),
                    "model": self.cfg.model,
                    "temperature": self.cfg.temperature,
                    "top_p": self.cfg.top_p,
                    "top_k": self.cfg.top_k,
                    "max_output_tokens": self.cfg.max_output_tokens,
                    "response_mime_type": self.cfg.response_mime_type,
                }
                return data, meta
            except Exception as e:  # noqa: BLE001
                last_err = e
                _time.sleep(self.cfg.backoff_s * (attempt + 1))
                continue
        meta = {
            "ok": False,
            "attempts_used": attempts,
            "elapsed_s": float(_time.time() - t0),
            "model": self.cfg.model,
            "temperature": self.cfg.temperature,
            "top_p": self.cfg.top_p,
            "top_k": self.cfg.top_k,
            "max_output_tokens": self.cfg.max_output_tokens,
            "response_mime_type": self.cfg.response_mime_type,
            "error_class": type(last_err).__name__ if last_err else "Unknown",
            "error_message": str(last_err) if last_err else "",
        }
        raise RuntimeError(f"Gemini call failed after {self.cfg.retries} attempts: {last_err}") from last_err



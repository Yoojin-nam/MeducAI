from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List


def _load_gate_module() -> Any:
    # 06_s6_export_gate.py isn't importable as a normal module name, so load by filepath.
    src_root = Path(__file__).resolve().parents[1] / "src"
    gate_path = src_root / "06_s6_export_gate.py"
    spec = importlib.util.spec_from_file_location("s6_export_gate", gate_path)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["s6_export_gate"] = m
    spec.loader.exec_module(m)
    return m


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


class TestS6ExportGateManifest(unittest.TestCase):
    def test_promotes_when_accept_and_postrepair_ok(self) -> None:
        gate = _load_gate_module()

        ratings_rows = [{"card_uid": "grp_1::c1", "accept_ai_correction": "ACCEPT"}]
        accept_by_group = gate._compute_accept_stats_by_group(ratings_rows)
        self.assertEqual(accept_by_group["grp_1"].n_accept, 1)
        self.assertEqual(accept_by_group["grp_1"].n_reject, 0)

        s5p = {
            "group_id": "grp_1",
            "validation_timestamp": "2026-01-01T00:00:00Z",
            "s5_snapshot_id": "snap_post_1",
            "s1_table_validation": {"blocking_error": False},
            "s2_cards_validation": {
                "summary": {"blocking_errors": 0},
                "cards": [
                    {
                        "blocking_error": False,
                        "card_image_validation": {"blocking_error": False, "safety_flag": False},
                    }
                ],
            },
        }

        with tempfile.TemporaryDirectory() as td:
            s5p_path = Path(td) / "s5_validation__armA__postrepair.jsonl"
            _write_jsonl(s5p_path, [s5p])

            latest = gate._load_latest_s5_by_group(s5p_path)
            ok, _audit = gate._postrepair_is_non_blocking(latest["grp_1"])
            self.assertTrue(ok)

            use_repaired, reason = gate._decide_use_repaired(
                accept_stats=accept_by_group["grp_1"],
                accept_policy="any_accept_no_reject",
                min_accept_count=1,
                postrepair_ok=ok,
            )
            self.assertTrue(use_repaired)
            self.assertEqual(reason, "accepted_and_postrepair_ok")

    def test_reject_blocks_promotion_even_if_postrepair_ok(self) -> None:
        gate = _load_gate_module()

        ratings_rows = [{"card_uid": "grp_2::c1", "accept_ai_correction": "REJECT"}]
        accept_by_group = gate._compute_accept_stats_by_group(ratings_rows)
        self.assertEqual(accept_by_group["grp_2"].n_accept, 0)
        self.assertEqual(accept_by_group["grp_2"].n_reject, 1)

        s5p = {
            "group_id": "grp_2",
            "validation_timestamp": "2026-01-01T00:00:00Z",
            "s5_snapshot_id": "snap_post_2",
            "s1_table_validation": {"blocking_error": False},
            "s2_cards_validation": {"summary": {"blocking_errors": 0}, "cards": []},
        }

        with tempfile.TemporaryDirectory() as td:
            s5p_path = Path(td) / "s5_validation__armA__postrepair.jsonl"
            _write_jsonl(s5p_path, [s5p])

            ok, _audit = gate._postrepair_is_non_blocking(gate._load_latest_s5_by_group(s5p_path)["grp_2"])
            self.assertTrue(ok)

            use_repaired, reason = gate._decide_use_repaired(
                accept_stats=accept_by_group["grp_2"],
                accept_policy="any_accept_no_reject",
                min_accept_count=1,
                postrepair_ok=ok,
            )
            self.assertFalse(use_repaired)
            self.assertEqual(reason, "explicit_reject_present")


if __name__ == "__main__":
    unittest.main()



from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from typing import Any, Dict


def _load_optionc_module() -> Any:
    # 05c_option_c_orchestrator.py isn't importable as a normal module name, so load by filepath.
    src_root = Path(__file__).resolve().parents[1] / "src"
    path = src_root / "05c_option_c_orchestrator.py"
    spec = importlib.util.spec_from_file_location("optionc_orchestrator", path)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["optionc_orchestrator"] = m
    spec.loader.exec_module(m)
    return m


class TestOptionCEntityTrigger(unittest.TestCase):
    def test_entitywise_trigger_selects_only_bad_entity(self) -> None:
        optionc = _load_optionc_module()

        # Patch the score calculator so no external dependencies / LLM logic are involved.
        # We key off `s5_technical_accuracy` (which is passed through the score input).
        def fake_score(x: Dict[str, Any]) -> float:
            ta = x.get("s5_technical_accuracy")
            if ta == 0.4:
                return 40.0
            if ta == 0.9:
                return 90.0
            return 100.0

        group_record = {
            "group_id": "grp_1",
            "s1_table_validation": {"blocking_error": False, "technical_accuracy": 1.0, "educational_quality": 5},
            "s2_cards_validation": {
                "cards": [
                    # Entity E1 should trigger (min_score 40 < threshold)
                    {"card_id": "E1__Q1__0", "entity_id": "E1", "entity_name": "Ent1", "technical_accuracy": 0.4},
                    # Entity E2 should not trigger (score 90 >= threshold)
                    {"card_id": "E2__Q1__0", "entity_id": "E2", "entity_name": "Ent2", "technical_accuracy": 0.9},
                ]
            },
        }

        with patch.object(optionc, "calculate_s5_regeneration_trigger_score", side_effect=fake_score):
            d = optionc.decide_trigger_for_group_entitywise(group_record=group_record, threshold=50.0)

        self.assertEqual(d.trigger_mode, "entity")
        self.assertEqual(d.group_id, "grp_1")
        self.assertTrue(d.should_trigger)
        self.assertEqual(d.trigger_reason, "score_lt_threshold")

        # Only E1 should be included.
        self.assertEqual(len(d.triggered_entities), 1)
        self.assertEqual(d.triggered_entities[0]["entity_id"], "E1")
        self.assertEqual(d.triggered_entities[0]["trigger_reason"], "score_lt_threshold")

    def test_s1_hard_trigger_forces_group_selection(self) -> None:
        optionc = _load_optionc_module()

        def fake_score(_: Dict[str, Any]) -> float:
            return 100.0

        group_record = {
            "group_id": "grp_2",
            "s1_table_validation": {"blocking_error": True, "technical_accuracy": 1.0, "educational_quality": 5},
            "s2_cards_validation": {"cards": []},
        }

        with patch.object(optionc, "calculate_s5_regeneration_trigger_score", side_effect=fake_score):
            d = optionc.decide_trigger_for_group_entitywise(group_record=group_record, threshold=50.0)

        self.assertEqual(d.trigger_reason, "s1_hard_trigger")
        self.assertTrue(d.hard_trigger)
        self.assertTrue(d.s1_hard_trigger)


if __name__ == "__main__":
    unittest.main()



from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Ensure `3_Code/src` is importable
SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))

from tools.multi_agent.score_calculator import calculate_s5_regeneration_trigger_score  # type: ignore


class TestTriggerScoreCalculator(unittest.TestCase):
    def test_hard_triggers_return_30(self) -> None:
        self.assertEqual(calculate_s5_regeneration_trigger_score({"s5_blocking_error": True}), 30.0)
        self.assertEqual(calculate_s5_regeneration_trigger_score({"s5_technical_accuracy": 0.0}), 30.0)
        self.assertEqual(calculate_s5_regeneration_trigger_score({"s5_card_image_blocking_error": True}), 30.0)
        self.assertEqual(calculate_s5_regeneration_trigger_score({"s5_card_image_safety_flag": True}), 30.0)

    def test_weighted_sum_defaults_to_100(self) -> None:
        # Missing TA/EQ/Image => TA=1.0 (50) + EQ=5 (30) + no-image => 20 = 100
        self.assertEqual(calculate_s5_regeneration_trigger_score({}), 100.0)

    def test_weighted_sum_example_values(self) -> None:
        score = calculate_s5_regeneration_trigger_score(
            {
                "s5_technical_accuracy": 0.5,  # 25
                "s5_educational_quality": 3,  # 18
                "s5_card_image_quality": 5,  # 20
            }
        )
        self.assertEqual(score, 63.0)


if __name__ == "__main__":
    unittest.main()



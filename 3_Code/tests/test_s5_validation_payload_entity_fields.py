from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Ensure `3_Code/src` is importable
SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))

from tools.s5.s5_validation_payload import build_s2_card_validation_record  # type: ignore


class TestS5ValidationPayloadEntityFields(unittest.TestCase):
    def test_build_s2_card_validation_record_includes_entity_fields(self) -> None:
        rec = build_s2_card_validation_record(
            card_id="E1__Q1__0",
            card={"card_type": "Basic", "card_role": "Q1"},
            entity_id="E1",
            entity_name="Pneumothorax",
            entity_type="disease",
            card_validation={"blocking_error": False, "technical_accuracy": 1.0},
        )

        # Required SSOT metadata for downstream repair planning
        self.assertEqual(rec["entity_id"], "E1")
        self.assertEqual(rec["entity_name"], "Pneumothorax")
        self.assertEqual(rec["entity_type"], "disease")
        self.assertEqual(rec["card_type"], "Basic")
        self.assertEqual(rec["card_role"], "Q1")

        # Ensure validation keys are preserved/merged
        self.assertIn("blocking_error", rec)
        self.assertIn("technical_accuracy", rec)

    def test_build_s2_card_validation_record_normalizes_blank_entity_to_none(self) -> None:
        rec = build_s2_card_validation_record(
            card_id="__Q1__0",
            card={"card_type": "Basic", "card_role": "Q1"},
            entity_id="",
            entity_name="   ",
            entity_type=None,
            card_validation={},
        )
        self.assertIsNone(rec["entity_id"])
        self.assertIsNone(rec["entity_name"])
        self.assertIsNone(rec["entity_type"])


if __name__ == "__main__":
    unittest.main()



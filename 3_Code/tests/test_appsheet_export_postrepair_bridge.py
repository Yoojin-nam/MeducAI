"""
Smoke-ish test for AppSheet export bridge:
- regenerated content comes from s2_results__*__repaired.jsonl into S5.csv
- regenerated image metadata comes from S4 regen manifest (s4_image_manifest__*__regen.jsonl)

This is intentionally lightweight and filesystem-based, matching how we run exports.
"""

from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "3_Code" / "src"
sys.path.insert(0, str(SRC_ROOT))

from tools.final_qa.export_appsheet_tables import export_appsheet_tables  # type: ignore


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _read_csv_index(path: Path, key: str) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        rdr = csv.DictReader(f)
        out: dict[str, dict[str, str]] = {}
        for row in rdr:
            k = (row.get(key) or "").strip()
            if k:
                out[k] = row
        return out


def run_smoke() -> int:
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        run_dir = base / "run"
        out_dir = base / "out"

        gid = "G001"
        eid = "G001__E01"
        # idx=0, role=Q1 -> derived card id used by exporter
        card_id = f"{eid}__Q1__0"
        card_uid = f"{gid}::{card_id}"

        _write_jsonl(
            run_dir / "stage1_struct__armA.jsonl",
            [
                {
                    "group_id": gid,
                    "group_path": "Neuro > Stroke",
                    "group_key": "neuro/stroke",
                    "visual_type_category": "Pathology_Pattern",
                    "objective_bullets": ["Obj1"],
                    "master_table_markdown_kr": "",
                    "integrity": {"entity_count": 1, "table_row_count": 1},
                }
            ],
        )

        # Baseline S2
        _write_jsonl(
            run_dir / "s2_results__s1armA__s2armA.jsonl",
            [
                {
                    "run_tag": "T",
                    "arm": "A",
                    "group_id": gid,
                    "group_path": "Neuro > Stroke",
                    "entity_id": eid,
                    "entity_name": "Acute ischemic stroke",
                    "anki_cards": [
                        {
                            "card_role": "Q1",
                            "card_type": "MCQ",
                            "front": "Baseline front",
                            "back": "Baseline back",
                            "options": ["opt1", "opt2"],
                            "correct_index": 0,
                            "tags": ["t1"],
                            "image_hint": {},
                            "image_hint_v2": {},
                        }
                    ],
                }
            ],
        )

        # Repaired S2 (regenerated content should be bridged into S5.csv)
        _write_jsonl(
            run_dir / "s2_results__s1armA__s2armA__repaired.jsonl",
            [
                {
                    "run_tag": "T",
                    "arm": "A",
                    "group_id": gid,
                    "group_path": "Neuro > Stroke",
                    "entity_id": eid,
                    "entity_name": "Acute ischemic stroke",
                    "anki_cards": [
                        {
                            "card_role": "Q1",
                            "card_type": "MCQ",
                            "front": "Repaired front",
                            "back": "Repaired back",
                            "options": ["opt1", "opt2"],
                            "correct_index": 0,
                            "tags": ["t1"],
                            "image_hint": {},
                            "image_hint_v2": {},
                        }
                    ],
                }
            ],
        )

        # Baseline S5 validation
        _write_jsonl(
            run_dir / "s5_validation__armA.jsonl",
            [
                {
                    "run_tag": "T",
                    "arm": "A",
                    "group_id": gid,
                    "s2_cards_validation": {
                        "cards": [
                            {
                                "card_id": card_id,
                                # Force CARD_REGEN decision so regenerated front/back are expected to be populated.
                                "blocking_error": True,
                                "technical_accuracy": 0.0,
                                "educational_quality": 0.0,
                                "issues": [],
                                "rag_evidence": [],
                                "card_image_validation": {
                                    "blocking_error": False,
                                    "anatomical_accuracy": 1.0,
                                    "prompt_compliance": 1.0,
                                    "text_image_consistency": 1.0,
                                    "image_quality": 1.0,
                                    "safety_flag": False,
                                    "issues": [],
                                    "image_path": "",
                                },
                            }
                        ]
                    },
                }
            ],
        )

        # Regen manifest + dummy regen image file (used to populate S5.csv regen image fields)
        regen_img_dir = run_dir / "images_regen"
        regen_img_dir.mkdir(parents=True, exist_ok=True)
        regen_img_name = f"IMG__T__{gid}__{eid}__Q1_regen.jpg"
        regen_img_path = regen_img_dir / regen_img_name
        regen_img_path.write_bytes(b"fakejpg")

        _write_jsonl(
            run_dir / "s4_image_manifest__armA__regen.jsonl",
            [
                {
                    "schema_version": "S4_IMAGE_MANIFEST_v1.0",
                    "run_tag": "T",
                    "group_id": gid,
                    "entity_id": eid,
                    "entity_name": "Acute ischemic stroke",
                    "card_role": "Q1",
                    "spec_kind": "S2_CARD_IMAGE",
                    "media_filename": regen_img_name,
                    "image_path": str(regen_img_path),
                    "generation_success": True,
                    "image_required": True,
                    "rag_enabled": False,
                    "rag_queries_count": 0,
                    "rag_sources_count": 0,
                }
            ],
        )

        export_appsheet_tables(
            run_dir=run_dir,
            out_dir=out_dir,
            copy_images=False,
            make_group_table_pdfs=False,
            verbose=False,
        )

        s5_idx = _read_csv_index(out_dir / "S5.csv", key="card_uid")
        if card_uid not in s5_idx:
            print("FAIL: card missing from S5.csv")
            return 1

        # Regenerated content should come from repaired S2.
        if (s5_idx[card_uid].get("s5_was_regenerated") or "").strip() != "1":
            print("FAIL: s5_was_regenerated not set")
            return 1
        if "Repaired front" not in (s5_idx[card_uid].get("s5_regenerated_front") or ""):
            print("FAIL: regenerated front not bridged from repaired S2")
            return 1
        if "Repaired back" not in (s5_idx[card_uid].get("s5_regenerated_back") or ""):
            print("FAIL: regenerated back not bridged from repaired S2")
            return 1

        # Regen image fields should be populated from regen manifest (even if copy_images=False).
        v = (s5_idx[card_uid].get("s5_regenerated_image_filename") or "").strip()
        if v == "":
            print("FAIL: s5_regenerated_image_filename not populated from regen manifest")
            return 1
        if not v.endswith(regen_img_name):
            print(f"FAIL: s5_regenerated_image_filename should end with {regen_img_name}, got: {v}")
            return 1
        if (s5_idx[card_uid].get("s5_regeneration_timestamp") or "").strip() == "":
            print("FAIL: s5_regeneration_timestamp not populated from regen image mtime")
            return 1

        # Ratings.csv should be template-only by default (header + 0 rows).
        ratings_path = out_dir / "Ratings.csv"
        if not ratings_path.exists():
            print("FAIL: Ratings.csv not emitted")
            return 1
        with ratings_path.open("r", encoding="utf-8", newline="") as f:
            lines = f.read().splitlines()
        if len(lines) != 1:
            print(f"FAIL: Ratings.csv should be header-only, got {len(lines)-1} data row(s)")
            return 1

        print("PASS")
        return 0


def test_appsheet_export_postrepair_bridge() -> None:
    assert run_smoke() == 0


if __name__ == "__main__":
    raise SystemExit(run_smoke())



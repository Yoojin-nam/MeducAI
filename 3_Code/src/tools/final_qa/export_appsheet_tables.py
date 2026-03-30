#!/usr/bin/env python3
"""
Export MeducAI pipeline outputs (JSONL) into AppSheet-friendly CSV tables.

Primary goal:
- Use *sample* runs now, but keep the schema stable so full-scale runs can be
  swapped in by replacing CSVs.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.units import cm

_THIS_FILE = Path(__file__).resolve()
_SRC_ROOT = _THIS_FILE.parents[2]  # .../3_Code/src
if str(_SRC_ROOT) not in sys.path:
    # Allow running as a script: `python 3_Code/src/tools/qa_appsheet/export_appsheet_tables.py ...`
    sys.path.insert(0, str(_SRC_ROOT))

from tools.multi_agent.score_calculator import (
    calculate_s5_regeneration_trigger_score,
    calculate_s5_card_regeneration_trigger_score,
    calculate_s5_image_regeneration_trigger_score,
)
from tools.qa.s5_decision import determine_s5_decision, determine_s5_decision_detailed, determine_s5_decision_v2


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSONL at {path} line {line_no}: {e}") from e
    return rows


def _safe_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _strip_md_bold(s: str) -> str:
    """
    Remove Markdown bold syntax from string.
    Handles both full-string bold and inline bold.
    
    Examples:
        "**May-Thurner Syndrome**" → "May-Thurner Syndrome"
        "K-space의 **중심부(Center)**는" → "K-space의 중심부(Center)는"
    """
    import re
    # Remove all **text** patterns
    return re.sub(r'\*\*([^*]+)\*\*', r'\1', s)


def _bool01(v: Any) -> Optional[int]:
    if v is None:
        return None
    if isinstance(v, bool):
        return 1 if v else 0
    return None


def _json_dumps(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def _extract_issues_description(issues_json_str: str) -> str:
    """Extract description values from s5_issues_json.
    
    Args:
        issues_json_str: JSON string containing list of issue dictionaries
    
    Returns:
        Comma-separated string of description values, or empty string if empty/error
    """
    if not issues_json_str or issues_json_str.strip() == "":
        return ""
    
    try:
        issues = json.loads(issues_json_str)
        if not isinstance(issues, list):
            return ""
        
        descriptions = []
        for issue in issues:
            if isinstance(issue, dict):
                desc = issue.get("description", "")
                if desc and str(desc).strip():
                    descriptions.append(str(desc).strip())
        
        return ", ".join(descriptions) if descriptions else ""
    except (json.JSONDecodeError, TypeError, ValueError):
        return ""


def _extract_issues_evidence_ref(issues_json_str: str) -> str:
    """Extract evidence_ref values from s5_issues_json.
    
    Args:
        issues_json_str: JSON string containing list of issue dictionaries
    
    Returns:
        Comma-separated string of evidence_ref values, or empty string if empty/error
    """
    if not issues_json_str or issues_json_str.strip() == "":
        return ""
    
    try:
        issues = json.loads(issues_json_str)
        if not isinstance(issues, list):
            return ""
        
        evidence_refs = []
        for issue in issues:
            if isinstance(issue, dict):
                # Check both "evidence_ref" and "rag_evidence" fields
                evidence_ref = issue.get("evidence_ref") or issue.get("rag_evidence")
                if evidence_ref:
                    if isinstance(evidence_ref, list):
                        # If it's a list, extract source_id or description from each item
                        for ev in evidence_ref:
                            if isinstance(ev, dict):
                                source_id = ev.get("source_id") or ev.get("source_excerpt", "")
                                if source_id and str(source_id).strip():
                                    evidence_refs.append(str(source_id).strip())
                    elif isinstance(evidence_ref, str) and evidence_ref.strip():
                        evidence_refs.append(evidence_ref.strip())
                    else:
                        # Try to convert to string
                        ev_str = str(evidence_ref).strip()
                        if ev_str:
                            evidence_refs.append(ev_str)
        
        return ", ".join(evidence_refs) if evidence_refs else ""
    except (json.JSONDecodeError, TypeError, ValueError):
        return ""


def _derive_card_id(entity_id: str, card_role: str, card_idx_in_entity: int) -> str:
    # Observed in S5: e.g. "DERIVED:95d8c0fd6c07__Q2__1"
    return f"{entity_id}__{card_role}__{card_idx_in_entity}"


def _format_front_with_mcq_options(*, card_type: str, front: str, options: List[Any]) -> str:
    """
    Keep a single source of truth for how MCQ options are appended to the front text.
    This must match what we export into Cards.csv so any regenerated content lines up.
    """
    if card_type != "MCQ" or not options:
        return front
    option_labels = ["A", "B", "C", "D", "E", "F", "G", "H"]
    options_text = "\n\n[선택지]\n"
    for i, opt in enumerate(options):
        if i < len(option_labels):
            options_text += f"{option_labels[i]}. {opt}\n"
        else:
            options_text += f"{i+1}. {opt}\n"
    return (front or "") + options_text.rstrip("\n")


def _build_s2_regenerated_index(s2_results_repaired_path: Path) -> Dict[str, Dict[str, str]]:
    """
    Build a per-card content index from repaired S2 results.

    Returns:
      card_uid -> {"front": str, "back": str}
    """
    out: Dict[str, Dict[str, str]] = {}
    for row in _read_jsonl(s2_results_repaired_path):
        group_id = row.get("group_id", "") or ""
        entity_id = row.get("entity_id", "") or ""
        if not group_id or not entity_id:
            continue
        anki_cards = row.get("anki_cards") or []
        for idx, c in enumerate(anki_cards):
            card_role = c.get("card_role", "") or ""
            if not card_role:
                continue
            card_type = c.get("card_type", "") or ""
            front = c.get("front", "") or ""
            back = c.get("back", "") or ""
            mcq_options = c.get("options") or []
            front = _format_front_with_mcq_options(card_type=card_type, front=front, options=mcq_options)

            card_id = _derive_card_id(entity_id, card_role, idx)
            card_uid = f"{group_id}::{card_id}"
            out[card_uid] = {"front": front, "back": back}
    return out


def _rename_s5_fields_for_postrepair(s5_flat: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert baseline-style flattened S5 fields into postrepair-prefixed columns.
    Keeps IDs (card_uid/card_id/run_tag/arm/group_id) unprefixed for stable joins.
    """
    keep = {"card_uid", "card_id", "run_tag", "arm", "group_id"}
    out: Dict[str, Any] = {k: s5_flat.get(k, "") for k in keep}
    for k, v in s5_flat.items():
        if k in keep:
            continue
        if k.startswith("s5_"):
            out[f"s5_postrepair_{k[3:]}"] = v
        else:
            out[f"s5_postrepair_{k}"] = v
    return out


def _load_groups(stage1_struct_path: Path) -> Dict[str, Dict[str, Any]]:
    groups = {}
    for row in _read_jsonl(stage1_struct_path):
        gid = row.get("group_id")
        if not gid:
            continue
        groups[gid] = row
    return groups


def _build_s5_card_index(s5_validation_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Returns a dict: card_uid -> flattened S5 fields.
    card_uid is stable and unique: "{group_id}::{card_id}"
    """
    out: Dict[str, Dict[str, Any]] = {}
    for row in _read_jsonl(s5_validation_path):
        run_tag = row.get("run_tag", "")
        arm = row.get("arm", "")
        group_id = row.get("group_id", "")

        s2 = (row.get("s2_cards_validation") or {})
        cards = s2.get("cards") or []
        for c in cards:
            card_id = c.get("card_id")
            if not card_id:
                continue
            card_uid = f"{group_id}::{card_id}"

            civ = c.get("card_image_validation") or {}
            flattened: Dict[str, Any] = {
                "card_uid": card_uid,
                "card_id": card_id,
                "run_tag": run_tag,
                "arm": arm,
                "group_id": group_id,
                "s5_blocking_error": _bool01(c.get("blocking_error")),
                "s5_technical_accuracy": c.get("technical_accuracy"),
                "s5_educational_quality": c.get("educational_quality"),
                "s5_issues_json": _json_dumps(c.get("issues") or []),
                "s5_rag_evidence_json": _json_dumps(c.get("rag_evidence") or []),
                "s5_card_image_blocking_error": _bool01(civ.get("blocking_error")),
                "s5_card_image_anatomical_accuracy": civ.get("anatomical_accuracy"),
                "s5_card_image_prompt_compliance": civ.get("prompt_compliance"),
                "s5_card_image_text_image_consistency": civ.get("text_image_consistency"),
                "s5_card_image_quality": civ.get("image_quality"),
                "s5_card_image_safety_flag": _bool01(civ.get("safety_flag")),
                "s5_card_image_issues_json": _json_dumps(civ.get("issues") or []),
                "image_path_local": civ.get("image_path") or "",
            }

            # Fill scores if missing (Safety-first preset).
            # Legacy combined score (for backward compatibility)
            existing_ts = c.get("s5_regeneration_trigger_score")
            if existing_ts is None:
                existing_ts = c.get("regeneration_trigger_score")
            if existing_ts is None:
                existing_ts = row.get("s5_regeneration_trigger_score")
            is_missing_ts = existing_ts is None or (isinstance(existing_ts, str) and not existing_ts.strip())
            flattened["s5_regeneration_trigger_score"] = (
                calculate_s5_regeneration_trigger_score(flattened) if is_missing_ts else existing_ts
            )
            
            # New: Card-only score (for CARD_REGEN decision)
            existing_card_score = c.get("s5_card_regeneration_trigger_score")
            if existing_card_score is None:
                existing_card_score = calculate_s5_card_regeneration_trigger_score(flattened)
            flattened["s5_card_regeneration_trigger_score"] = existing_card_score
            
            # New: Image-only score (for IMAGE_ONLY_REGEN decision)
            existing_image_score = c.get("s5_image_regeneration_trigger_score")
            if existing_image_score is None:
                existing_image_score = calculate_s5_image_regeneration_trigger_score(flattened)
            flattened["s5_image_regeneration_trigger_score"] = existing_image_score
            
            # New: Detailed decision (PASS / CARD_REGEN / IMAGE_ONLY_REGEN)
            flattened["s5_decision"] = determine_s5_decision(flattened)
            flattened["s5_decision_detailed"] = determine_s5_decision_detailed(flattened)

            out[card_uid] = flattened
    return out


def _parse_markdown_table(md: str) -> Tuple[List[str], List[List[str]]]:
    """
    Parse a simple GitHub-flavored markdown table into header + rows.
    Assumptions: pipe-separated table, first row header, second row alignment.
    """
    if not md:
        return [], []
    lines = [ln.strip() for ln in md.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return [], []

    def split_row(line: str) -> List[str]:
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]
        parts = [p.strip() for p in line.split("|")]
        return [_strip_md_bold(p) for p in parts]

    header = split_row(lines[0])
    # Skip alignment line (---)
    body_lines = lines[2:] if len(lines) >= 3 else []
    rows = [split_row(ln) for ln in body_lines if "|" in ln]
    # Normalize row widths
    w = len(header)
    norm_rows: List[List[str]] = []
    for r in rows:
        if len(r) < w:
            r = r + [""] * (w - len(r))
        elif len(r) > w:
            r = r[:w]
        norm_rows.append(r)
    return header, norm_rows


def _render_group_master_table_pdf(
    *,
    out_pdf: Path,
    title: str,
    objective_bullets: List[str],
    master_table_markdown: str,
) -> None:
    """
    Render a group master table into a PDF using reportlab.
    """
    header, rows = _parse_markdown_table(master_table_markdown)
    styles = getSampleStyleSheet()
    story: List[Any] = []

    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 0.3 * cm))

    if objective_bullets:
        story.append(Paragraph("Objectives", styles["Heading2"]))
        for b in objective_bullets:
            story.append(Paragraph(f"• {_strip_md_bold(str(b))}", styles["BodyText"]))
        story.append(Spacer(1, 0.3 * cm))

    if header and rows:
        story.append(Paragraph("Master Table", styles["Heading2"]))
        table_data = [header] + rows
        tbl = Table(table_data, repeatRows=1)
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ]
            )
        )
        story.append(tbl)
    else:
        story.append(Paragraph("Master Table (raw)", styles["Heading2"]))
        story.append(Paragraph(master_table_markdown.replace("\n", "<br/>"), styles["Code"]))

    doc = SimpleDocTemplate(str(out_pdf), pagesize=A4, rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=24)
    doc.build(story)


def _build_manifest_image_index(run_dir: Path) -> Dict[Tuple[str, str, str], str]:
    """
    Fallback image mapping from S4 image manifest.

    Returns:
      (group_id, entity_id, card_role) -> image_path_local
    """
    candidates = sorted(run_dir.glob("s4_image_manifest__*.jsonl"))
    if not candidates:
        return {}

    manifest_path = candidates[0]
    out: Dict[Tuple[str, str, str], str] = {}
    for row in _read_jsonl(manifest_path):
        gid = row.get("group_id") or ""
        eid = row.get("entity_id") or ""
        role = row.get("card_role") or ""
        img_path = row.get("image_path") or ""
        if gid and eid and role and img_path:
            out[(gid, eid, role)] = img_path
    return out


def _build_manifest_entry_index(
    run_dir: Path,
    *,
    require_stem_substring: Optional[str] = None,
    exclude_stem_substring: Optional[str] = None,
) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    """
    Load S4 image manifest entries keyed by (group_id, entity_id, card_role).

    This is used to locate regenerated images (e.g., __regen manifests) and to extract
    metadata such as media_filename / image_path.
    """
    candidates = sorted(run_dir.glob("s4_image_manifest__*.jsonl"))
    if require_stem_substring:
        candidates = [p for p in candidates if require_stem_substring in p.stem]
    if exclude_stem_substring:
        candidates = [p for p in candidates if exclude_stem_substring not in p.stem]
    if not candidates:
        return {}

    manifest_path = candidates[0]
    out: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for row in _read_jsonl(manifest_path):
        gid = row.get("group_id") or ""
        eid = row.get("entity_id") or ""
        role = row.get("card_role") or ""
        if gid and eid and role:
            out[(gid, eid, role)] = row
    return out


def _iso_ts_from_file_mtime(p: Path) -> str:
    try:
        import datetime as _dt

        ts = p.stat().st_mtime
        return _dt.datetime.fromtimestamp(ts).isoformat(sep=" ", timespec="seconds")
    except Exception:
        return ""


def _norm_text(s: Any) -> str:
    """Normalize text for change detection (whitespace-insensitive)."""
    if s is None:
        return ""
    try:
        out = str(s)
    except Exception:
        return ""
    return " ".join(out.split()).strip()


def _load_s2_cards(s2_results_path: Path) -> List[Dict[str, Any]]:
    return _read_jsonl(s2_results_path)


def _write_csv(path: Path, fieldnames: List[str], rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _read_csv_rows(path: Path) -> Iterable[Dict[str, Any]]:
    """Read CSV rows as dictionaries."""
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def _generate_ratings_from_assignments(
    assignments_path: Path,
    cards_path: Path,
    out_path: Path,
    fieldnames: List[str],
) -> None:
    """
    Generate Ratings.csv with pre-created rows for all assignments.
    
    Creates one row per (rater_email, card_uid) from Assignments.
    This implements the "Ratings-first queue model" for production use.
    """
    # Load assignments
    assignments = list(_read_csv_rows(assignments_path))
    
    # Load cards to get card_uid mapping (if needed for validation)
    cards_by_id = {}
    if cards_path.exists():
        for row in _read_csv_rows(cards_path):
            card_id = row.get("card_id", "")
            if card_id:
                cards_by_id[card_id] = row
    
    # Group assignments by rater_email and create Ratings rows
    ratings_rows = []
    rater_card_pairs = set()
    
    for assign in assignments:
        rater_email = assign.get("rater_email", "").strip()
        card_uid = assign.get("card_uid", "").strip()
        card_id = assign.get("card_id", "").strip()
        assignment_id = assign.get("assignment_id", "").strip()
        assignment_order_str = assign.get("assignment_order", "0").strip()
        batch_id = assign.get("batch_id", "").strip()
        
        if not rater_email or not card_uid:
            continue
        
        # Avoid duplicates
        pair_key = (rater_email, card_uid)
        if pair_key in rater_card_pairs:
            continue
        rater_card_pairs.add(pair_key)
        
        rating_id = f"{card_uid}::{rater_email}"
        
        # Parse assignment_order as integer
        try:
            assignment_order = int(assignment_order_str) if assignment_order_str else 0
        except (ValueError, TypeError):
            assignment_order = 0
        
        ratings_rows.append({
            "rating_id": rating_id,
            "card_uid": card_uid,
            "card_id": card_id,
            "rater_email": rater_email,
            "assignment_id": assignment_id,
            "assignment_order": assignment_order,
            "batch_id": batch_id,
            # Pre fields (blank initially)
            "blocking_error_pre": "",
            "technical_accuracy_pre": "",
            "educational_quality_pre": "",
            "evidence_comment_pre": "",
            "pre_started_ts": "",
            "pre_submitted_ts": "",
            "pre_duration_sec": "",
            # Image evaluation - Pre (blank initially, evaluated in Post stage)
            "image_blocking_error_pre": "",
            "image_anatomical_accuracy_pre": "",
            "image_quality_pre": "",
            "image_text_consistency_pre": "",
            # Post fields (blank initially)
            "blocking_error_post": "",
            "technical_accuracy_post": "",
            "educational_quality_post": "",
            "evidence_comment_post": "",
            "post_started_ts": "",
            "post_submitted_ts": "",
            "post_duration_sec": "",
            # Image evaluation - Post (evaluated after S5 reveal)
            "image_blocking_error_post": "",
            "image_anatomical_accuracy_post": "",
            "image_quality_post": "",
            "image_text_consistency_post": "",
            # Realistic Image evaluation (SPECIALIST-only; time-independent from Pre/Post)
            "realistic_image_blocking_error": "",
            "realistic_image_anatomical_accuracy": "",
            "realistic_image_quality": "",
            "realistic_image_text_consistency": "",
            "realistic_image_started_ts": "",
            "realistic_image_submitted_ts": "",
            "realistic_image_duration_sec": "",
            # Change log
            "change_reason_code": "",
            "change_note": "",
            "changed_fields": "",
            # Flags
            "flag_followup": "0",
            "flag_note": "",
            # Admin undo (optional)
            "admin_undo_pre_submitted_ts": "",
            "admin_undo_post_submitted_ts": "",
            "undo_reason": "",
            # S5 Final Assessment (멀티에이전트 시스템의 Self-Improvement 검증)
            "s5_started_ts": "",
            "s5_submitted_ts": "",
            "s5_duration_sec": "",
            "ai_self_reliability": "",
            "ai_self_reliability_comment": "",
            "accept_ai_correction": "",
            "ai_correction_quality": "",
            "ai_correction_comment": "",
        })
    
    # Sort by rater_email, then assignment_order
    ratings_rows.sort(key=lambda x: (x["rater_email"], x.get("assignment_order", 0)))
    
    # Write CSV
    _write_csv(out_path, fieldnames, ratings_rows)


def _copy_image(src_path: Path, dst_base_dir: Path, preserve_folder: bool = True) -> str:
    """
    Copy an image into dst_base_dir, preserving folder structure if preserve_folder is True.
    Returns relative path from dst_base_dir (e.g., "images_anki/filename.jpg").
    If src_path does not exist, returns empty string.
    
    Args:
        src_path: Source image file path
        dst_base_dir: Base output directory
        preserve_folder: If True, preserve folder structure (e.g., images_anki/, images_realistic/)
    """
    if not src_path or not src_path.exists():
        return ""
    
    filename = src_path.name
    
    # Determine relative path from source to preserve folder structure
    if preserve_folder:
        # Try to detect folder name from source path
        # Common folders: images/, images_anki/, images_realistic/, images_regen/
        src_parent = src_path.parent.name
        if src_parent in ("images", "images_anki", "images_realistic", "images_regen", "images__repaired"):
            folder_name = src_parent
            relative_path = f"{folder_name}/{filename}"
            dst_path = dst_base_dir / folder_name / filename
        else:
            # Fallback: no folder structure
            relative_path = filename
            dst_path = dst_base_dir / filename
    else:
        # No folder structure
        relative_path = filename
        dst_path = dst_base_dir / filename
    
    # Create parent directory if needed
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Copy if not exists
    if not dst_path.exists():
        shutil.copy2(src_path, dst_path)
    
    return relative_path


def export_appsheet_tables(
    run_dir: Path,
    out_dir: Path,
    copy_images: bool,
    make_group_table_pdfs: bool,
    verbose: bool,
    realistic_run_dir: Optional[Path] = None,
    prefill_ratings: bool = False,
) -> None:
    run_dir = run_dir.resolve()
    out_dir = out_dir.resolve()
    _safe_mkdir(out_dir)

    # Be permissive: allow future full runs / different arms by discovering files.
    stage1_candidates = sorted(run_dir.glob("stage1_struct__*.jsonl"))
    
    # S2 baseline: prefer translated files (__medterm_en.jsonl), exclude regen/repaired variants
    s2_baseline_translated = sorted(run_dir.glob("s2_results__*__medterm_en.jsonl"))
    s2_baseline_translated = [p for p in s2_baseline_translated if "__regen" not in p.stem and "__repaired" not in p.stem]
    s2_candidates_all = sorted(run_dir.glob("s2_results__*.jsonl"))
    s2_candidates = [p for p in s2_candidates_all if "__regen" not in p.stem and "__repaired" not in p.stem and "__medterm_en" not in p.stem]
    # Prefer translated baseline, fall back to original
    s2_baseline_candidates = s2_baseline_translated if s2_baseline_translated else s2_candidates
    
    # S2 regen/repaired: prefer translated regen, then original regen, then repaired
    s2_regen_translated = sorted(run_dir.glob("s2_results__*__regen__medterm_en.jsonl"))
    s2_regen_original = sorted(run_dir.glob("s2_results__*__regen.jsonl"))
    s2_repaired_candidates = sorted(run_dir.glob("s2_results__*__repaired.jsonl"))
    # Prefer translated regen, then original regen, then repaired
    s2_regen_candidates = s2_regen_translated if s2_regen_translated else (s2_regen_original if s2_regen_original else s2_repaired_candidates)
    
    s5_candidates_all = sorted(run_dir.glob("s5_validation__*.jsonl"))
    # Prefer baseline S5 (exclude post-repair variants by default).
    s5_candidates = [p for p in s5_candidates_all if "__postrepair" not in p.stem]
    if not s5_candidates:
        s5_candidates = s5_candidates_all
    s5_postrepair_candidates = sorted(run_dir.glob("s5_validation__*__postrepair.jsonl"))

    stage1_struct_path = stage1_candidates[0] if stage1_candidates else (run_dir / "stage1_struct__armG.jsonl")
    s2_results_path = s2_baseline_candidates[0] if s2_baseline_candidates else (run_dir / "s2_results__s1armG__s2armG.jsonl")
    s5_validation_path = s5_candidates[0] if s5_candidates else (run_dir / "s5_validation__armG.jsonl")
    s2_results_repaired_path = s2_regen_candidates[0] if s2_regen_candidates else None
    s5_postrepair_path = s5_postrepair_candidates[0] if s5_postrepair_candidates else None

    if not stage1_struct_path.exists():
        raise FileNotFoundError(f"Missing: {stage1_struct_path}")
    if not s2_results_path.exists():
        raise FileNotFoundError(f"Missing: {s2_results_path}")
    if not s5_validation_path.exists():
        raise FileNotFoundError(f"Missing: {s5_validation_path}")

    groups = _load_groups(stage1_struct_path)
    s5_by_card = _build_s5_card_index(s5_validation_path)
    manifest_image_by_key = _build_manifest_image_index(run_dir)
    # Regenerated images are emitted by S4 with --image_type regen into:
    # - images_regen/
    # - s4_image_manifest__armX__regen.jsonl
    regen_manifest_by_key = _build_manifest_entry_index(run_dir, require_stem_substring="__regen")
    # Build realistic image index if realistic_run_dir is provided
    realistic_image_by_key: Dict[Tuple[str, str, str], str] = {}
    if realistic_run_dir is not None:
        realistic_run_dir = realistic_run_dir.resolve()
        if realistic_run_dir.exists():
            realistic_image_by_key = _build_manifest_image_index(realistic_run_dir)
    regenerated_by_card_uid: Dict[str, Dict[str, str]] = {}
    if s2_results_repaired_path is not None and s2_results_repaired_path.exists():
        regenerated_by_card_uid = _build_s2_regenerated_index(s2_results_repaired_path)

    s5_postrepair_by_card: Dict[str, Dict[str, Any]] = {}
    if s5_postrepair_path is not None and s5_postrepair_path.exists():
        s5p_raw = _build_s5_card_index(s5_postrepair_path)
        # Rename the fields to avoid clobbering baseline S5 columns.
        for cu, flat in s5p_raw.items():
            s5_postrepair_by_card[cu] = _rename_s5_fields_for_postrepair(flat)

    # Images output directory (base directory for preserving folder structure)
    images_out_dir = out_dir
    if copy_images:
        _safe_mkdir(images_out_dir)

    group_table_out_dir = out_dir / "group_table_pdfs"
    if make_group_table_pdfs:
        _safe_mkdir(group_table_out_dir)

    # ---- Groups.csv ----
    group_rows: List[Dict[str, Any]] = []
    for gid, g in groups.items():
        master_table_pdf_relpath = ""
        if make_group_table_pdfs:
            mt = g.get("master_table_markdown_kr", "") or ""
            if mt.strip():
                pdf_name = f"MT__{(g.get('group_key') or gid).replace('/', '_')}__{gid}.pdf"
                out_pdf = group_table_out_dir / pdf_name
                title = f"{gid} — {g.get('group_path','')}"
                objective_bullets = g.get("objective_bullets") or []
                _render_group_master_table_pdf(
                    out_pdf=out_pdf,
                    title=title,
                    objective_bullets=[str(x) for x in objective_bullets],
                    master_table_markdown=mt,
                )
                master_table_pdf_relpath = f"group_table_pdfs/{pdf_name}"

        group_rows.append(
            {
                "group_id": gid,
                "group_path": g.get("group_path", ""),
                "group_key": g.get("group_key", ""),
                "visual_type_category": g.get("visual_type_category", ""),
                "objective_bullets_json": _json_dumps(g.get("objective_bullets") or []),
                "master_table_markdown_kr": g.get("master_table_markdown_kr", ""),
                "master_table_pdf_file": master_table_pdf_relpath,
                "entity_count": (g.get("integrity") or {}).get("entity_count"),
                "table_row_count": (g.get("integrity") or {}).get("table_row_count"),
            }
        )
    _write_csv(
        out_dir / "Groups.csv",
        [
            "group_id",
            "group_path",
            "group_key",
            "visual_type_category",
            "objective_bullets_json",
            "master_table_markdown_kr",
            "master_table_pdf_file",
            "entity_count",
            "table_row_count",
        ],
        group_rows,
    )

    # ---- Cards.csv ----
    card_rows: List[Dict[str, Any]] = []
    all_card_uids: List[str] = []
    card_meta_by_uid: Dict[str, Dict[str, str]] = {}
    s2_rows = _load_s2_cards(s2_results_path)
    for row in s2_rows:
        run_tag = row.get("run_tag", "")
        arm = row.get("arm", "")
        group_id = row.get("group_id", "")
        group_path = row.get("group_path", "")
        entity_id = row.get("entity_id", "")
        entity_name = _strip_md_bold(row.get("entity_name", "") or "")

        anki_cards = row.get("anki_cards") or []
        for idx, c in enumerate(anki_cards):
            card_role = c.get("card_role", "")
            card_type = c.get("card_type", "")
            front = c.get("front", "")
            back = c.get("back", "")
            tags = c.get("tags") or []
            tags_csv = ",".join(str(t) for t in tags)
            mcq_options = c.get("options") or []
            mcq_correct_index = c.get("correct_index")
            image_hint = c.get("image_hint") or {}
            image_hint_v2 = c.get("image_hint_v2") or {}

            # MCQ 타입일 때 front에 선택지 포함 (shared formatting helper)
            front = _format_front_with_mcq_options(card_type=card_type, front=front, options=mcq_options)
            
            # Remove Markdown bold from front and back for AppSheet display
            front = _strip_md_bold(front)
            back = _strip_md_bold(back)

            card_id = _derive_card_id(entity_id, card_role, idx)
            card_uid = f"{group_id}::{card_id}"
            s5 = s5_by_card.get(card_uid) or {}

            # Baseline image path (raw local path) for later change detection in S5.csv.
            baseline_image_path_local = s5.get("image_path_local") or ""
            if not baseline_image_path_local:
                baseline_image_path_local = manifest_image_by_key.get((group_id, entity_id, card_role), "")

            image_filename = ""
            if copy_images:
                image_path_local = s5.get("image_path_local") or ""
                if not image_path_local:
                    image_path_local = manifest_image_by_key.get((group_id, entity_id, card_role), "")
                if image_path_local:
                    # Preserve folder structure (images/, images_anki/, etc.)
                    image_filename = _copy_image(Path(image_path_local), images_out_dir, preserve_folder=True)

            # Realistic image filename (populated from realistic_run_dir if provided)
            realistic_image_filename = ""
            if copy_images and realistic_image_by_key:
                realistic_image_path = realistic_image_by_key.get((group_id, entity_id, card_role), "")
                if realistic_image_path:
                    # Preserve folder structure (images_realistic/)
                    realistic_image_filename = _copy_image(Path(realistic_image_path), images_out_dir, preserve_folder=True)

            # Calculate S5 decision (PASS/CARD_REGEN/IMAGE_REGEN)
            # Use detailed decision to distinguish card regen vs image-only regen
            # Use 80.0 threshold to match positive_regen_runner.py criteria
            s5_decision_detailed, card_score, image_score = determine_s5_decision_v2(
                s5, card_threshold=80.0, image_threshold=80.0
            )
            # Map IMAGE_ONLY_REGEN to IMAGE_REGEN for AppSheet display
            if s5_decision_detailed == "IMAGE_ONLY_REGEN":
                s5_decision = "IMAGE_REGEN"
            elif s5_decision_detailed == "CARD_REGEN":
                s5_decision = "CARD_REGEN"
            else:
                s5_decision = "PASS"

            all_card_uids.append(card_uid)
            card_meta_by_uid[card_uid] = {
                "group_id": str(group_id),
                "entity_id": str(entity_id),
                "card_role": str(card_role),
                # Baseline (S2) text used for diff-based s5_was_regenerated.
                "baseline_front": str(front or ""),
                "baseline_back": str(back or ""),
                "baseline_image_path_local": str(baseline_image_path_local or ""),
            }
            card_rows.append(
                {
                    "card_uid": card_uid,
                    "card_id": card_id,
                    "run_tag": run_tag,
                    "arm": arm,
                    "group_id": group_id,
                    "group_path": group_path,
                    "entity_id": entity_id,
                    "entity_name": entity_name,
                    "card_idx_in_entity": idx,
                    "card_role": card_role,
                    "card_type": card_type,
                    "front": front,
                    "back": back,
                    "tags_csv": tags_csv,
                    "tags_json": _json_dumps(tags),
                    "mcq_options_json": _json_dumps(mcq_options),
                    "mcq_correct_index": mcq_correct_index,
                    "image_hint_json": _json_dumps(image_hint),
                    "image_hint_v2_json": _json_dumps(image_hint_v2),
                    "image_filename": image_filename,
                    "realistic_image_filename": realistic_image_filename,
                    "s5_decision": s5_decision,
                }
            )

    _write_csv(
        out_dir / "Cards.csv",
        [
            "card_uid",
            "card_id",
            "run_tag",
            "arm",
            "group_id",
            "group_path",
            "entity_id",
            "entity_name",
            "card_idx_in_entity",
            "card_role",
            "card_type",
            "front",
            "back",
            "tags_csv",
            "tags_json",
            "mcq_options_json",
            "mcq_correct_index",
            "image_hint_json",
            "image_hint_v2_json",
            "image_filename",
            "realistic_image_filename",
            "s5_decision",
        ],
        card_rows,
    )

    # ---- S5.csv (baseline + postrepair merged) ----
    s5_rows: List[Dict[str, Any]] = []
    # Left-join to all cards so AppSheet Ref rows always exist.
    for card_uid in all_card_uids:
        s5 = s5_by_card.get(card_uid) or {}
        regen = regenerated_by_card_uid.get(card_uid) or {}
        s5p = s5_postrepair_by_card.get(card_uid) or {}
        meta = card_meta_by_uid.get(card_uid) or {}

        # Image regen metadata (from S4 regen manifest), best-effort.
        # Note: These fields are NOT present in baseline S5 validation JSONL by default.
        regen_image_filename = ""
        regen_ts = ""
        if meta:
            k = (meta.get("group_id", ""), meta.get("entity_id", ""), meta.get("card_role", ""))
            entry = regen_manifest_by_key.get(k) or {}
            media_filename = entry.get("media_filename") or ""
            image_path = entry.get("image_path") or ""
            if media_filename:
                # Prefer including the folder prefix (e.g., images_regen/...) so AppSheet can resolve it.
                if image_path:
                    try:
                        p = Path(str(image_path))
                        folder = p.parent.name
                        if folder:
                            regen_image_filename = f"{folder}/{p.name}"
                        else:
                            regen_image_filename = p.name
                    except Exception:
                        regen_image_filename = str(media_filename)
                else:
                    # Regen manifest implies images_regen/ by convention.
                    regen_image_filename = f"images_regen/{str(media_filename)}"
            # Timestamp: derive from the regenerated image file mtime (if the file exists).
            if image_path:
                p = Path(str(image_path))
                if p.exists():
                    regen_ts = _iso_ts_from_file_mtime(p)

            # If we are copying images for AppSheet upload, prefer returning the copied relative path
            # (preserving folder structure such as images_regen/).
            if copy_images and image_path:
                copied = _copy_image(Path(str(image_path)), images_out_dir, preserve_folder=True)
                if copied:
                    regen_image_filename = copied
        
        # Calculate S5 decision (PASS/CARD_REGEN/IMAGE_REGEN)
        # Use detailed decision to distinguish card regen vs image-only regen
        # Use 80.0 threshold to match positive_regen_runner.py criteria
        s5_decision_detailed, card_score, image_score = determine_s5_decision_v2(
            s5, card_threshold=80.0, image_threshold=80.0
        )
        # Map IMAGE_ONLY_REGEN to IMAGE_REGEN for AppSheet display
        if s5_decision_detailed == "IMAGE_ONLY_REGEN":
            s5_decision = "IMAGE_REGEN"
        elif s5_decision_detailed == "CARD_REGEN":
            s5_decision = "CARD_REGEN"
        else:
            s5_decision = "PASS"
        
        # Gate "regenerated_*" fields by decision.
        # Rationale: The repaired S2 JSONL may include all cards (not only ones needing regen),
        # so populating these fields unconditionally can confuse AppSheet UX.
        #
        # - CARD_REGEN: show regenerated front/back (+ image fields if available)
        # - IMAGE_REGEN: show only regenerated image fields (front/back should remain blank)
        # - PASS: leave regenerated_* fields blank
        base_regen_front = (
            regen.get("front", "") or s5.get("s5_regenerated_front") or s5.get("s5_front_modified", "")
        )
        base_regen_back = (
            regen.get("back", "") or s5.get("s5_regenerated_back") or s5.get("s5_back_modified", "")
        )
        if s5_decision == "CARD_REGEN":
            out_regen_front = base_regen_front
            out_regen_back = base_regen_back
            out_regen_image_filename = regen_image_filename or s5.get("s5_regenerated_image_filename", "")
            out_regen_ts = regen_ts or s5.get("s5_regeneration_timestamp") or s5.get("s5_modified_timestamp", "")
        elif s5_decision == "IMAGE_REGEN":
            out_regen_front = ""
            out_regen_back = ""
            out_regen_image_filename = regen_image_filename or s5.get("s5_regenerated_image_filename", "")
            out_regen_ts = regen_ts or s5.get("s5_regeneration_timestamp") or s5.get("s5_modified_timestamp", "")
        else:
            out_regen_front = ""
            out_regen_back = ""
            out_regen_image_filename = ""
            out_regen_ts = ""

        # Regenerated flag: diff-based (only true if content actually changed vs baseline).
        baseline_front = meta.get("baseline_front", "")
        baseline_back = meta.get("baseline_back", "")
        baseline_img_name = ""
        baseline_img_path = meta.get("baseline_image_path_local", "")
        if baseline_img_path:
            try:
                baseline_img_name = Path(str(baseline_img_path)).name
            except Exception:
                baseline_img_name = ""

        regen_img_name = ""
        if meta:
            entry = regen_manifest_by_key.get((meta.get("group_id", ""), meta.get("entity_id", ""), meta.get("card_role", ""))) or {}
            img_path = entry.get("image_path") or ""
            if img_path:
                try:
                    regen_img_name = Path(str(img_path)).name
                except Exception:
                    regen_img_name = ""
        if not regen_img_name and out_regen_image_filename:
            try:
                regen_img_name = Path(str(out_regen_image_filename)).name
            except Exception:
                regen_img_name = ""

        text_changed = (
            (_norm_text(out_regen_front) != "" and _norm_text(out_regen_front) != _norm_text(baseline_front))
            or (_norm_text(out_regen_back) != "" and _norm_text(out_regen_back) != _norm_text(baseline_back))
        )
        image_changed = (regen_img_name != "" and regen_img_name != baseline_img_name)

        if s5_decision == "PASS":
            out_was_regenerated = 0
        elif s5_decision == "IMAGE_REGEN":
            out_was_regenerated = 1 if image_changed else 0
        else:  # CARD_REGEN
            out_was_regenerated = 1 if (text_changed or image_changed) else 0

        s5_rows.append(
            {
                "card_uid": card_uid,
                "card_id": s5.get("card_id", ""),
                "run_tag": s5.get("run_tag", ""),
                "arm": s5.get("arm", ""),
                "group_id": s5.get("group_id", card_uid.split("::", 1)[0] if "::" in card_uid else ""),
                # Baseline S5 validation results
                "s5_blocking_error": s5.get("s5_blocking_error"),
                "s5_technical_accuracy": s5.get("s5_technical_accuracy"),
                "s5_educational_quality": s5.get("s5_educational_quality"),
                "s5_issues_json": s5.get("s5_issues_json", "[]"),
                "s5_description": _extract_issues_description(s5.get("s5_issues_json", "[]")),
                "s5_evidence_ref": _extract_issues_evidence_ref(s5.get("s5_issues_json", "[]")),
                "s5_rag_evidence_json": s5.get("s5_rag_evidence_json", "[]"),
                "s5_card_image_blocking_error": s5.get("s5_card_image_blocking_error"),
                "s5_card_image_anatomical_accuracy": s5.get("s5_card_image_anatomical_accuracy"),
                "s5_card_image_prompt_compliance": s5.get("s5_card_image_prompt_compliance"),
                "s5_card_image_text_image_consistency": s5.get("s5_card_image_text_image_consistency"),
                "s5_card_image_quality": s5.get("s5_card_image_quality"),
                "s5_card_image_safety_flag": s5.get("s5_card_image_safety_flag"),
                "s5_card_image_issues_json": s5.get("s5_card_image_issues_json", "[]"),
                # S5 재생성 콘텐츠 (멀티에이전트 시스템의 Self-Improvement 결과)
                # 기존 s5_front_modified, s5_back_modified, s5_modified_timestamp와 통합
                "s5_regenerated_front": out_regen_front,
                "s5_regenerated_back": out_regen_back,
                "s5_regenerated_image_filename": out_regen_image_filename,
                "s5_regeneration_timestamp": out_regen_ts,
                "s5_regeneration_trigger_score": s5.get("s5_regeneration_trigger_score"),
                "s5_was_regenerated": out_was_regenerated,
                "s5_decision": s5_decision,
                # Note: Postrepair S5 validation results (s5_postrepair_*) are NOT exported to AppSheet
                # because S4 regeneration workflow only shows regenerated card content (s5_regenerated_*)
                # and user decision (accept_ai_correction). Postrepair validation is for internal use only.
            }
        )
    _write_csv(
        out_dir / "S5.csv",
        [
            "card_uid",
            "card_id",
            "run_tag",
            "arm",
            "group_id",
            # Baseline S5 validation results
            "s5_blocking_error",
            "s5_technical_accuracy",
            "s5_educational_quality",
            "s5_issues_json",
            "s5_description",
            "s5_evidence_ref",
            "s5_rag_evidence_json",
            "s5_card_image_blocking_error",
            "s5_card_image_anatomical_accuracy",
            "s5_card_image_prompt_compliance",
            "s5_card_image_text_image_consistency",
            "s5_card_image_quality",
            "s5_card_image_safety_flag",
            "s5_card_image_issues_json",
            # S5 재생성 콘텐츠 (멀티에이전트 시스템의 Self-Improvement 결과)
            "s5_regenerated_front",
            "s5_regenerated_back",
            "s5_regenerated_image_filename",
            "s5_regeneration_timestamp",
            "s5_regeneration_trigger_score",
            "s5_was_regenerated",
            "s5_decision",
            # Note: Postrepair S5 validation results are NOT exported to AppSheet
            # (for internal analysis only, not shown to users)
        ],
        s5_rows,
    )

    # ---- Ratings.csv (template or pre-populated) ----
    assignments_path = out_dir / "Assignments.csv"
    cards_path = out_dir / "Cards.csv"
    
    ratings_fieldnames = [
        "rating_id",
        "card_uid",
        "card_id",
        "rater_email",
        "assignment_id",
        "assignment_order",
        "batch_id",
        "blocking_error_pre",
        "technical_accuracy_pre",
        "educational_quality_pre",
        "evidence_comment_pre",
        "pre_started_ts",
        "pre_submitted_ts",
        "pre_duration_sec",
        # Image evaluation - Pre (evaluated in Post stage)
        "image_blocking_error_pre",
        "image_anatomical_accuracy_pre",
        "image_quality_pre",
        "image_text_consistency_pre",
        "blocking_error_post",
        "technical_accuracy_post",
        "educational_quality_post",
        "evidence_comment_post",
        "post_started_ts",
        "post_submitted_ts",
        "post_duration_sec",
        # Image evaluation - Post (evaluated after S5 reveal)
        "image_blocking_error_post",
        "image_anatomical_accuracy_post",
        "image_quality_post",
        "image_text_consistency_post",
        # Realistic Image evaluation (SPECIALIST-only; time-independent from Pre/Post)
        "realistic_image_blocking_error",
        "realistic_image_anatomical_accuracy",
        "realistic_image_quality",
        "realistic_image_text_consistency",
        "realistic_image_started_ts",
        "realistic_image_submitted_ts",
        "realistic_image_duration_sec",
        "change_reason_code",
        "change_note",
        "changed_fields",
        "flag_followup",
        "flag_note",
        "admin_undo_pre_submitted_ts",
        "admin_undo_post_submitted_ts",
        "undo_reason",
        # S5 Final Assessment (멀티에이전트 시스템의 Self-Improvement 검증)
        "s5_started_ts",
        "s5_submitted_ts",
        "s5_duration_sec",
        "ai_self_reliability",
        "ai_self_reliability_comment",
        "accept_ai_correction",
        "ai_correction_quality",
        "ai_correction_comment",
    ]
    
    # Ratings.csv policy:
    # - Default (recommended): template-only (header + 0 rows). AppSheet creates rows via Add(+) at runtime.
    # - Optional legacy mode: prefill rows from Assignments (ratings-first queue model).
    if prefill_ratings:
        if assignments_path.exists() and cards_path.exists():
            try:
                _generate_ratings_from_assignments(
                    assignments_path=assignments_path,
                    cards_path=cards_path,
                    out_path=out_dir / "Ratings.csv",
                    fieldnames=ratings_fieldnames,
                )
                if verbose:
                    ratings_count = sum(1 for _ in _read_csv_rows(out_dir / "Ratings.csv"))
                    print(f"[OK] Wrote: {out_dir / 'Ratings.csv'} ({ratings_count} pre-created rows from Assignments)")
            except Exception as e:
                if verbose:
                    print(f"[WARN] Failed to generate Ratings from Assignments: {e}")
                    print(f"[INFO] Falling back to template-only Ratings.csv")
                _write_csv(out_dir / "Ratings.csv", ratings_fieldnames, [])
        else:
            _write_csv(out_dir / "Ratings.csv", ratings_fieldnames, [])
            if verbose:
                print(f"[OK] Wrote: {out_dir / 'Ratings.csv'} (template - missing Assignments.csv)")
    else:
        _write_csv(out_dir / "Ratings.csv", ratings_fieldnames, [])
        if verbose:
            print(f"[OK] Wrote: {out_dir / 'Ratings.csv'} (template-only; AppSheet will create rows at runtime)")

    # ---- Assignments.csv (template) ----
    # IMPORTANT: If Assignments.csv already exists (e.g., generated by an assignment generator),
    # do NOT overwrite it. Overwriting would destroy the assignment plan and break AppSheet upload.
    if not assignments_path.exists():
        _write_csv(
            assignments_path,
            [
                "assignment_id",
                "rater_email",
                "card_uid",
                "card_id",
                "assignment_order",
                "batch_id",
                "status",
            ],
            [],
        )
        if verbose:
            print(f"[OK] Wrote: {out_dir / 'Assignments.csv'} (template)")
    else:
        if verbose:
            print(f"[OK] Kept existing: {out_dir / 'Assignments.csv'} (not overwritten)")

    if verbose:
        print(f"[OK] Wrote: {out_dir / 'Groups.csv'} ({len(group_rows)} rows)")
        print(f"[OK] Wrote: {out_dir / 'Cards.csv'} ({len(card_rows)} rows)")
        regenerated_count = sum(1 for card_uid in all_card_uids if card_uid in regenerated_by_card_uid)
        if regenerated_count > 0:
            print(f"[OK] Wrote: {out_dir / 'S5.csv'} ({len(s5_rows)} rows, {regenerated_count} with regenerated content)")
        else:
            print(f"[OK] Wrote: {out_dir / 'S5.csv'} ({len(s5_rows)} rows)")
        # Note: Postrepair S5 validation data exists but is not exported to AppSheet
        # (for internal analysis only, not shown to users)
        # Ratings.csv message is handled in the generation section above
        if copy_images:
            # Count images in all subdirectories (images/, images_anki/, images_realistic/, etc.)
            n_images = 0
            for img_dir in images_out_dir.iterdir():
                if img_dir.is_dir() and img_dir.name.startswith("images"):
                    n_images += len(list(img_dir.glob("*")))
            print(f"[OK] Copied images: {n_images} files -> {images_out_dir} (preserving folder structure)")
        missing_s5 = sorted(set(all_card_uids) - set(s5_by_card.keys()))
        if missing_s5:
            preview = ", ".join(missing_s5[:5])
            print(f"[WARN] Missing S5 rows for {len(missing_s5)} cards (left-joined as blank). e.g. {preview}")
        if s2_results_repaired_path is not None and regenerated_by_card_uid:
            print(f"[OK] Found repaired S2: {s2_results_repaired_path.name} ({len(regenerated_by_card_uid)} regenerated cards)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_dir", type=str, required=True)
    parser.add_argument("--out_dir", type=str, required=True)
    parser.add_argument("--copy_images", type=str, default="true")
    parser.add_argument("--make_group_table_pdfs", type=str, default="true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--prefill_ratings",
        type=str,
        default="false",
        help="If true, pre-create Ratings.csv rows from Assignments.csv (legacy mode). "
             "Default false (recommended): Ratings.csv is header-only and AppSheet creates rows at runtime.",
    )
    parser.add_argument("--realistic_run_dir", type=str, default=None,
                        help="Path to realistic image run directory (for populating realistic_image_filename)")
    args = parser.parse_args()

    copy_images = str(args.copy_images).lower() in ("1", "true", "yes", "y")
    make_group_table_pdfs = str(args.make_group_table_pdfs).lower() in ("1", "true", "yes", "y")
    prefill_ratings = str(args.prefill_ratings).lower() in ("1", "true", "yes", "y")
    realistic_run_dir = Path(args.realistic_run_dir) if args.realistic_run_dir else None
    export_appsheet_tables(
        run_dir=Path(args.run_dir),
        out_dir=Path(args.out_dir),
        copy_images=copy_images,
        make_group_table_pdfs=make_group_table_pdfs,
        verbose=bool(args.verbose),
        realistic_run_dir=realistic_run_dir,
        prefill_ratings=prefill_ratings,
    )


if __name__ == "__main__":
    main()



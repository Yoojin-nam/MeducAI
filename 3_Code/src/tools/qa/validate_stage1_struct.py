#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
validate_stage1_struct.py

Purpose
- Minimal, deterministic "S1 Gate" validator for Stage1 JSONL artifacts.
- Designed to fail-fast on structural errors that cascade into S2.

Assumptions (lightweight)
- Artifact lives under: <base_dir>/2_Data/metadata/generated/<run_tag>/
 - Canonical filename is per-arm: stage1_struct__armX.jsonl (inside RUN_TAG folder)
  - Legacy compatibility: stage1_struct.jsonl (single file) or output_*__armX.jsonl fallback

Exit codes
- 0: PASS
- 1: FAIL

Usage
  python 3_Code/src/tools/qa/validate_stage1_struct.py --base_dir . --run_tag "$RUN_TAG" --arm A
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Canonical visual_type_category enum (aligned with S1_Stage1_Struct_JSON_Schema_Canonical.md v1.3)
# Removed unused categories: Comparison, Algorithm, Classification, Sign_Collection (v11)
ALLOWED_VISUAL_CATEGORIES = {
    "Anatomy_Map",
    "Pathology_Pattern",
    "Pattern_Collection",
    "Physiology_Process",
    "Equipment",
    "QC",
    "General",
}

# Expected 6-column headers by visual_type_category (S1_SYSTEM__v12)
EXPECTED_HEADERS = {
    "Anatomy_Map": ["Entity name", "해부학적 구조", "위치/인접 구조", "정상변이/함정", "임상 적용", "시험포인트"],
    "Pathology_Pattern": ["Entity name", "질환 정의 및 분류", "모달리티별 핵심 영상 소견", "병리·기전/특징", "감별 질환", "시험포인트"],
    "Pattern_Collection": ["Entity name", "패턴 정의 및 특징", "핵심 영상 단서(키워드+모달리티)", "유사/대조 및 함정", "임상 의미/대표 질환", "시험포인트"],
    "Physiology_Process": ["Entity name", "생리 과정/단계 설명", "조건/원인/대상", "영상 표현", "시간축/순서", "시험포인트"],
    "Equipment": ["Entity name", "장비/기기명 및 용도", "원리/기술", "프로토콜/적용", "아티팩트/제한", "시험포인트"],
    "QC": ["Entity name", "품질 지표 정의", "허용 범위/기준", "측정 방법", "트러블슈팅(원인→조치)", "시험포인트"],
    "General": ["Entity name", "핵심 개념 설명", "핵심 영상 단서(키워드+모달리티)", "병리·기전/특징", "감별 질환", "시험포인트"],
}


@dataclass
class GateResult:
    ok: bool
    errors: List[str]
    warnings: List[str]


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                raise ValueError(f"Invalid JSON at line {i}: {e}") from e
            if not isinstance(obj, dict):
                raise ValueError(f"Line {i} is not a JSON object.")
            rows.append(obj)
    return rows


def _pick_artifact(run_dir: Path, arm: Optional[str]) -> Path:
    arm_norm = arm.strip().upper() if isinstance(arm, str) and arm.strip() else None

    if arm_norm:
        per_arm = run_dir / f"stage1_struct__arm{arm_norm}.jsonl"
        if per_arm.exists():
            return per_arm

    per_arm_candidates = sorted(run_dir.glob("stage1_struct__arm*.jsonl"))
    if per_arm_candidates:
        if arm_norm is None:
            if len(per_arm_candidates) == 1:
                return per_arm_candidates[0]
            raise FileNotFoundError(
                "Multiple stage1_struct__arm*.jsonl found; supply --arm to select one.\n"
                + "\n".join(str(p) for p in per_arm_candidates)
            )
        else:
            matches = [p for p in per_arm_candidates if p.name.endswith(f"__arm{arm_norm}.jsonl")]
            if matches:
                return matches[0]

    canonical = run_dir / "stage1_struct.jsonl"
    if canonical.exists():
        return canonical

    # Fallback to new stage1_raw__arm*.jsonl or legacy output_*__arm*.jsonl
    fallback_patterns = ["stage1_raw__arm*.jsonl", "output_*__arm*.jsonl"]
    for pattern in fallback_patterns:
        candidates = sorted(run_dir.glob(pattern))
        if not candidates:
            continue

        if arm_norm is None:
            if len(candidates) == 1:
                return candidates[0]
            raise FileNotFoundError(
                f"Multiple {pattern.replace('*', '<ARM>')} candidates found; provide --arm.\n"
                + "\n".join(str(p) for p in candidates)
            )

        arm_candidates = [p for p in candidates if f"__arm{arm_norm}.jsonl" in p.name]
        if arm_candidates:
            arm_candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return arm_candidates[0]

    missing_hint = (
        f"Missing stage1_struct__arm*.jsonl and stage1_struct.jsonl in {run_dir}. "
        "No fallback raw/output artifacts found either."
    )
    if arm_norm:
        missing_hint += f" (arm={arm_norm})"
    raise FileNotFoundError(missing_hint)


def _count_markdown_table_columns(md: str) -> Tuple[int, Optional[str]]:
    """
    Returns (column_count, error_message_if_unparseable)
    Heuristic: expects pipe-delimited markdown table with a header and separator row.
    """
    lines = [ln.rstrip() for ln in md.splitlines() if ln.strip()]
    if len(lines) < 2:
        return 0, "Markdown table too short (need header + separator)."

    # Find first plausible header/separator pair
    header_idx = None
    for i in range(len(lines) - 1):
        h, sep = lines[i], lines[i + 1]
        # separator row pattern: contains '-' and '|' and mostly dashes/colons/spaces
        if ("|" in h) and ("|" in sep) and re.fullmatch(r"[\s\|\-:]+", sep) and ("-" in sep):
            header_idx = i
            break

    if header_idx is None:
        return 0, "Could not find a valid markdown table header/separator pair."

    header_line = lines[header_idx]
    # Count columns by splitting on '|' and filtering empty strings
    columns = [col.strip() for col in header_line.split("|") if col.strip()]
    return len(columns), None


def _count_markdown_table_rows(md: str) -> Tuple[int, Optional[str]]:
    """
    Returns (body_rows_count, error_message_if_unparseable)
    Heuristic: expects pipe-delimited markdown table with a header and separator row.
    """
    lines = [ln.rstrip() for ln in md.splitlines() if ln.strip()]
    if len(lines) < 3:
        return 0, "Markdown table too short (need header + separator + >=1 row)."

    # Find first plausible header/separator pair
    header_idx = None
    for i in range(len(lines) - 1):
        h, sep = lines[i], lines[i + 1]
        if "|" in h and re.search(r"^\s*\|?\s*:?-{2,}", sep.replace("|", "").strip()) is None:
            # separator row usually contains --- segments; we check it differently below
            pass
        # separator row pattern: contains '-' and '|' and mostly dashes/colons/spaces
        if ("|" in h) and ("|" in sep) and re.fullmatch(r"[\s\|\-:]+", sep) and ("-" in sep):
            header_idx = i
            break

    if header_idx is None:
        return 0, "Could not find a valid markdown table header/separator pair."

    body = lines[header_idx + 2 :]
    # Count rows that look like table rows
    body_rows = [ln for ln in body if "|" in ln]
    return len(body_rows), None


def _parse_markdown_table_headers(md: str) -> Tuple[List[str], Optional[str]]:
    """
    Returns (headers_list, error_message_if_unparseable)
    Extracts column headers from markdown table.
    """
    lines = [ln.rstrip() for ln in md.splitlines() if ln.strip()]
    if len(lines) < 2:
        return [], "Markdown table too short (need header + separator)."

    # Find first plausible header/separator pair
    header_idx = None
    for i in range(len(lines) - 1):
        h, sep = lines[i], lines[i + 1]
        if ("|" in h) and ("|" in sep) and re.fullmatch(r"[\s\|\-:]+", sep) and ("-" in sep):
            header_idx = i
            break

    if header_idx is None:
        return [], "Could not find a valid markdown table header/separator pair."

    header_line = lines[header_idx]
    # Extract headers by splitting on '|' and trimming
    headers = [col.strip() for col in header_line.split("|") if col.strip()]
    return headers, None


def _check_cell_normalization(md: str) -> List[str]:
    """
    Check for HTML tags, newlines in cells, and other formatting issues.
    Returns list of warning/error messages.
    """
    issues = []
    lines = [ln.rstrip() for ln in md.splitlines() if ln.strip()]
    
    # Find data rows (skip header and separator)
    header_idx = None
    for i in range(len(lines) - 1):
        h, sep = lines[i], lines[i + 1]
        if ("|" in h) and ("|" in sep) and re.fullmatch(r"[\s\|\-:]+", sep) and ("-" in sep):
            header_idx = i
            break
    
    if header_idx is None:
        return ["Could not parse table structure for normalization check"]
    
    data_rows = lines[header_idx + 2:]
    
    for row_idx, line in enumerate(data_rows, start=header_idx + 3):
        if "|" not in line:
            continue
        
        # Extract cells
        cells = [cell.strip() for cell in line.split("|") if cell.strip()]
        
        for col_idx, cell in enumerate(cells, start=1):
            # Check for HTML tags
            if "<br" in cell.lower() or "<br/>" in cell.lower():
                issues.append(f"Row {row_idx}, column {col_idx}: Contains HTML tag (<br>)")
            
            # Check for newlines (should not exist in single-line cells)
            if "\n" in cell or "\r" in cell:
                issues.append(f"Row {row_idx}, column {col_idx}: Contains newline character")
    
    return issues


def _extract_strong_tokens(text: str) -> set:
    """
    Extract strong tokens from text for coverage/scope checking.
    Returns set of normalized tokens (medical terms, acronyms, numbers with units, key nouns).
    """
    if not text:
        return set()
    
    tokens = set()
    
    # Extract English medical terms (A-Z sequences, mixed-case)
    english_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    tokens.update(term.lower() for term in english_terms)
    
    # Extract acronyms (all caps, 2+ chars)
    acronyms = re.findall(r'\b[A-Z]{2,}\b', text)
    tokens.update(ac.upper() for ac in acronyms)
    
    # Extract numbers with units (e.g., "5 mm", "2 Gy")
    numbers_units = re.findall(r'\d+\s*(?:mm|cm|m|Gy|mSv|%|세)', text, re.IGNORECASE)
    tokens.update(nu.lower() for nu in numbers_units)
    
    # Extract terms in parentheses (often medical terms)
    paren_terms = re.findall(r'\(([^)]+)\)', text)
    for term in paren_terms:
        # Split on common delimiters
        parts = re.split(r'[,\s/]+', term.strip())
        tokens.update(p.lower().strip() for p in parts if len(p.strip()) >= 2)
    
    # Filter out very short tokens (noise)
    tokens = {t for t in tokens if len(t) >= 2}
    
    return tokens


def _objective_coverage_check(
    objective_bullets: str | List[str],
    entity_list: List[Dict[str, Any]],
    master_table_markdown: str,
    coverage_threshold: float = 0.70,
) -> Tuple[float, List[str], List[str]]:
    """
    Heuristic check for objective coverage.
    
    Returns: (coverage_ratio, missing_tokens, warnings)
    - coverage_ratio: fraction of objective tokens covered
    - missing_tokens: list of tokens from objectives not found in entities/table
    - warnings: list of warning messages
    """
    warnings = []
    
    # Normalize objective_bullets to string
    if isinstance(objective_bullets, list):
        obj_text = " ".join(str(b) for b in objective_bullets)
    else:
        obj_text = str(objective_bullets)
    
    # Extract tokens from objectives
    obj_tokens = _extract_strong_tokens(obj_text)
    if not obj_tokens:
        return 1.0, [], ["No extractable tokens from objective_bullets (heuristic may be too strict)"]
    
    # Extract entity names
    entity_names = []
    for ent in entity_list:
        if isinstance(ent, dict):
            name = ent.get("entity_name") or ent.get("name", "")
            if name:
                entity_names.append(str(name))
    
    entity_text = " ".join(entity_names)
    table_text = master_table_markdown
    
    # Extract tokens from entities + table
    covered_tokens = _extract_strong_tokens(entity_text + " " + table_text)
    
    # Compute coverage
    missing = obj_tokens - covered_tokens
    coverage_ratio = (len(obj_tokens) - len(missing)) / len(obj_tokens) if obj_tokens else 1.0
    
    missing_list = sorted(list(missing))
    
    if coverage_ratio < coverage_threshold:
        warnings.append(
            f"Objective coverage ratio {coverage_ratio:.2f} < threshold {coverage_threshold:.2f}. "
            f"Missing tokens: {missing_list[:10]}{'...' if len(missing_list) > 10 else ''}"
        )
    
    return coverage_ratio, missing_list, warnings


def _out_of_scope_check(
    objective_bullets: str | List[str],
    master_table_markdown: str,
    scope_threshold: int = 5,
) -> Tuple[int, List[str]]:
    """
    Heuristic check for out-of-scope content in table.
    
    Returns: (out_of_scope_count, suspected_tokens)
    """
    # Normalize objective_bullets to string
    if isinstance(objective_bullets, list):
        obj_text = " ".join(str(b) for b in objective_bullets)
    else:
        obj_text = str(objective_bullets)
    
    obj_tokens = _extract_strong_tokens(obj_text)
    table_tokens = _extract_strong_tokens(master_table_markdown)
    
    # Tokens in table but not in objectives
    out_of_scope = table_tokens - obj_tokens
    suspected = sorted(list(out_of_scope))
    
    return len(suspected), suspected


def _validate_one(
    obj: Dict[str, Any],
    entity_cap: int,
    enable_coverage_check: bool = False,
    coverage_threshold: float = 0.70,
    enable_scope_check: bool = False,
    scope_threshold: int = 5,
) -> GateResult:
    errors: List[str] = []
    warnings: List[str] = []

    # ---- Core required fields (minimal but strict types) ----
    if not obj.get("group_id") or not isinstance(obj.get("group_id"), str):
        errors.append("Missing/invalid required field: group_id (non-empty string).")
    
    # Schema version (required in v1.3)
    schema_ver = obj.get("schema_version")
    if schema_ver:
        if schema_ver != "S1_STRUCT_v1.3":
            warnings.append(f"schema_version is '{schema_ver}', expected 'S1_STRUCT_v1.3' (schema v1.3)")
    else:
        warnings.append("schema_version missing (recommended for schema v1.3)")

    vtc = obj.get("visual_type_category")
    if not vtc or not isinstance(vtc, str):
        errors.append("Missing/invalid required field: visual_type_category (non-empty string).")
    else:
        if vtc not in ALLOWED_VISUAL_CATEGORIES:
            warnings.append(
                f"visual_type_category='{vtc}' not in allowed set; "
                f"keeping permissive, but consider normalizing."
            )

    ent = obj.get("entity_list")
    if ent is None or not isinstance(ent, list):
        errors.append("Missing/invalid required field: entity_list (list).")
        ent = []

    # ---- Entity list checks ----
    if isinstance(ent, list):
        if len(ent) == 0:
            warnings.append("entity_list is empty. (May be acceptable for some groups, but risky for S2.)")
        if len(ent) > entity_cap:
            errors.append(f"entity_list length {len(ent)} exceeds cap {entity_cap}.")
        seen_ids = set()
        for idx, e in enumerate(ent, start=1):
            if not isinstance(e, dict):
                errors.append(f"entity_list[{idx}] is not an object.")
                continue
            eid = e.get("entity_id")
            ename = e.get("entity_name")
            if not eid or not isinstance(eid, str):
                errors.append(f"entity_list[{idx}].entity_id missing/invalid.")
            else:
                if eid in seen_ids:
                    errors.append(f"Duplicate entity_id found: {eid}")
                seen_ids.add(eid)
            if not ename or not isinstance(ename, str):
                warnings.append(f"entity_list[{idx}].entity_name missing/invalid (recommended).")

    # ---- Objective bullets (recommended) ----
    # Schema v1.3: objective_bullets should be array of strings
    # Legacy: may also be a markdown string (for backward compatibility)
    if "objective_bullets" in obj:
        ob = obj.get("objective_bullets")
        if isinstance(ob, list):
            # New format: array of strings (schema v1.3)
            if len(ob) == 0:
                warnings.append("objective_bullets is empty array.")
            elif not all(isinstance(x, str) and x.strip() for x in ob):
                warnings.append("objective_bullets array contains non-string or empty items.")
        elif isinstance(ob, str):
            # Legacy format: markdown string
            if not ob.strip():
                warnings.append("objective_bullets (string) is empty.")
            else:
                # Expect markdown bullets "- " or "* "
                if not re.search(r"(?m)^\s*[-\*]\s+\S", ob):
                    warnings.append("objective_bullets (string) does not look like markdown bullet list (heuristic).")
        else:
            warnings.append("objective_bullets present but invalid type (expected array of strings or string).")
    else:
        warnings.append("objective_bullets key missing (recommended for S1->S2).")
    
    # ---- Integrity object (required in schema v1.3) ----
    integrity = obj.get("integrity")
    if integrity:
        if not isinstance(integrity, dict):
            warnings.append("integrity is present but not an object.")
        else:
            # Check required integrity fields
            entity_count = integrity.get("entity_count")
            table_row_count = integrity.get("table_row_count")
            objective_count = integrity.get("objective_count")
            if entity_count is None or not isinstance(entity_count, int):
                warnings.append("integrity.entity_count missing or invalid.")
            if table_row_count is None or not isinstance(table_row_count, int):
                warnings.append("integrity.table_row_count missing or invalid.")
            if objective_count is None or not isinstance(objective_count, int):
                warnings.append("integrity.objective_count missing or invalid.")
    else:
        warnings.append("integrity object missing (recommended for schema v1.3)")
    
    # ---- Master table markdown (recommended) ----
    # Accept either "master_table_markdown" (canonical) or "master_table_markdown_kr" (legacy/localized).
    mt_key = "master_table_markdown" if "master_table_markdown" in obj else ("master_table_markdown_kr" if "master_table_markdown_kr" in obj else None)
    if mt_key is not None:
        mt = obj.get(mt_key)
        if not isinstance(mt, str) or not mt.strip():
            warnings.append(f"{mt_key} present but empty/invalid.")
        else:
            # Check column count (must be 6 per S1_SYSTEM__v12)
            col_count, col_err = _count_markdown_table_columns(mt)
            if col_err:
                warnings.append(f"{mt_key} column count parse warning: {col_err}")
            else:
                if col_count != 6:
                    errors.append(f"{mt_key} must have exactly 6 columns, got {col_count}.")
            
            # Check header match if visual_type_category is known
            if vtc and vtc in EXPECTED_HEADERS:
                headers, header_err = _parse_markdown_table_headers(mt)
                if header_err:
                    warnings.append(f"{mt_key} header parse warning: {header_err}")
                elif len(headers) == 6:
                    expected = EXPECTED_HEADERS[vtc]
                    if headers != expected:
                        warnings.append(
                            f"{mt_key} headers do not match expected for {vtc}. "
                            f"Got: {headers}, Expected: {expected}"
                        )
            
            # Check cell normalization (no HTML tags, no newlines in cells)
            norm_issues = _check_cell_normalization(mt)
            for issue in norm_issues:
                errors.append(f"{mt_key}: {issue}")
            
            body_rows, err = _count_markdown_table_rows(mt)
            if err:
                warnings.append(f"{mt_key} parse warning: {err}")
            else:
                if body_rows > 20:
                    errors.append(f"{mt_key} body rows {body_rows} > 20 (hard fail).")
                elif 15 <= body_rows <= 20:
                    warnings.append(f"{mt_key} body rows {body_rows} in 15–20 range (PASS with warning).")
    else:
        warnings.append("master_table_markdown key missing (recommended for downstream table rendering).")
    
    # ---- Objective coverage check (optional, heuristic) ----
    if enable_coverage_check:
        objective_bullets = obj.get("objective_bullets")
        if objective_bullets and mt_key:
            mt_val = obj.get(mt_key, "")
            if isinstance(mt_val, str) and mt_val.strip():
                cov_ratio, missing_tokens, cov_warnings = _objective_coverage_check(
                    objective_bullets,
                    ent if isinstance(ent, list) else [],
                    mt_val,
                    coverage_threshold=coverage_threshold,
                )
                for w in cov_warnings:
                    warnings.append(f"Coverage check: {w}")
                if cov_ratio < 0.60:  # Hard fail threshold lower than warning threshold
                    errors.append(
                        f"Objective coverage too low ({cov_ratio:.2f} < 0.60). "
                        f"Consider adding entities or adjusting table content."
                    )
    
    # ---- Out-of-scope check (optional, heuristic) ----
    if enable_scope_check:
        objective_bullets = obj.get("objective_bullets")
        if objective_bullets and mt_key:
            mt_val = obj.get(mt_key, "")
            if isinstance(mt_val, str) and mt_val.strip():
                oos_count, suspected = _out_of_scope_check(
                    objective_bullets,
                    mt_val,
                    scope_threshold=scope_threshold,
                )
                if oos_count > scope_threshold:
                    warnings.append(
                        f"Out-of-scope check: {oos_count} tokens in table not found in objectives "
                        f"(threshold: {scope_threshold}). Suspected: {suspected[:10]}{'...' if len(suspected) > 10 else ''}"
                    )
    
    return GateResult(ok=(len(errors) == 0), errors=errors, warnings=warnings)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base_dir", default=".", help="Project base directory (default: .)")
    ap.add_argument("--run_tag", required=True, help="RUN_TAG name (folder under 2_Data/metadata/generated/)")
    ap.add_argument("--arm", default=None, help="Arm letter to disambiguate output jsonl fallback (e.g., A)")
    ap.add_argument("--entity_cap", type=int, default=None, help="Max entities allowed (default: env ENTITY_LIST_CAP or 50)")
    ap.add_argument("--enable_coverage_check", action="store_true", help="Enable objective coverage heuristic check")
    ap.add_argument("--coverage_threshold", type=float, default=0.70, help="Coverage threshold (default: 0.70)")
    ap.add_argument("--enable_scope_check", action="store_true", help="Enable out-of-scope content heuristic check")
    ap.add_argument("--scope_threshold", type=int, default=5, help="Out-of-scope token count threshold (default: 5)")
    args = ap.parse_args()

    base = Path(args.base_dir).resolve()
    run_dir = base / "2_Data" / "metadata" / "generated" / args.run_tag

    if not run_dir.exists():
        print(f"[S1-GATE] FAIL :: run_dir not found: {run_dir}")
        return 1

    entity_cap = args.entity_cap
    if entity_cap is None:
        try:
            entity_cap = int(os.environ.get("ENTITY_LIST_CAP", "50"))
        except Exception:
            entity_cap = 50

    try:
        artifact = _pick_artifact(run_dir, args.arm)
    except Exception as e:
        print(f"[S1-GATE] FAIL :: {e}")
        return 1

    try:
        objs = _read_jsonl(artifact)
    except Exception as e:
        print(f"[S1-GATE] FAIL :: cannot read JSONL: {artifact}\n  -> {e}")
        return 1

    if not objs:
        print(f"[S1-GATE] FAIL :: empty JSONL: {artifact}")
        return 1

    any_fail = False
    total_warn = 0

    for i, obj in enumerate(objs, start=1):
        res = _validate_one(
            obj,
            entity_cap=entity_cap,
            enable_coverage_check=args.enable_coverage_check,
            coverage_threshold=args.coverage_threshold,
            enable_scope_check=args.enable_scope_check,
            scope_threshold=args.scope_threshold,
        )
        total_warn += len(res.warnings)

        if not res.ok:
            any_fail = True
            print(f"[S1-GATE] FAIL :: record #{i}")
            for msg in res.errors:
                print(f"  [E] {msg}")
            for msg in res.warnings:
                print(f"  [W] {msg}")
        else:
            # Keep output concise but informative
            if res.warnings:
                print(f"[S1-GATE] PASS+WARN :: record #{i} ({len(res.warnings)} warnings)")
                for msg in res.warnings:
                    print(f"  [W] {msg}")
            else:
                print(f"[S1-GATE] PASS :: record #{i}")

    print(f"[S1-GATE] artifact={artifact.name} records={len(objs)} warnings={total_warn}")
    return 1 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())


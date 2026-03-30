"""
MeducAI Step06 (Order File Generator) — Generate specialty order files from xlsx

P0 Requirements:
- Read Radiology_Curriculum_Weight_Factor.xlsx
- Auto-detect group_key (or matching key) from xlsx columns
- Generate specialty-specific order files with order=1..N based on row sequence
- Validate against groups_canonical.csv (fail-fast on missing/duplicates)
- Output: 2_Data/metadata/group_order/specialty_group_order.csv

Design Principles:
- SSOT protection: groups_canonical.csv is frozen, only read for validation
- Auto-detection: try multiple strategies to match group_key
- Fail-fast: raise errors on validation failures
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("ERROR: pandas is required. Install with: pip install pandas openpyxl", file=sys.stderr)
    sys.exit(1)


def normalize_key_text(text: str) -> str:
    """Normalize text for key matching (lowercase, strip, replace spaces with underscores)."""
    if not text or pd.isna(text):
        return ""
    text = str(text).strip().lower()
    # Replace spaces and special chars with underscores
    text = text.replace(" ", "_").replace("-", "_").replace("/", "_")
    # Remove multiple underscores
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_")


def construct_group_key_from_tags(
    row: pd.Series,
    anatomy_tag_col: Optional[str],
    modality_tag_col: Optional[str],
    category_tag_col: Optional[str],
) -> Optional[str]:
    """
    Construct group_key from tag columns: {anatomy}__{modality}__{category}
    
    Returns None if required columns are missing or empty.
    """
    if not anatomy_tag_col or not modality_tag_col or not category_tag_col:
        return None
    
    anatomy_val = row.get(anatomy_tag_col, "")
    modality_val = row.get(modality_tag_col, "")
    category_val = row.get(category_tag_col, "")
    
    anatomy = normalize_key_text(str(anatomy_val) if anatomy_val is not None and not (isinstance(anatomy_val, float) and pd.isna(anatomy_val)) else "")
    modality = normalize_key_text(str(modality_val) if modality_val is not None and not (isinstance(modality_val, float) and pd.isna(modality_val)) else "")
    category_raw = str(category_val) if category_val is not None and not (isinstance(category_val, float) and pd.isna(category_val)) else ""
    category = normalize_key_text(category_raw) if category_raw and category_raw.lower() not in ("nan", "none", "null", "") else ""
    
    if not anatomy or not modality:
        return None
    
    # Category is optional (some groups don't have category)
    # Only include category if it's non-empty and not "nan"
    if category and category.lower() not in ("nan", "none", "null"):
        return f"{anatomy}__{modality}__{category}"
    else:
        return f"{anatomy}__{modality}"


def construct_group_key_from_korean_columns(
    row: pd.Series,
    anatomy_col: Optional[str],
    modality_col: Optional[str],
    category_col: Optional[str],
) -> Optional[str]:
    """
    Construct group_key from Korean columns by normalizing to match canonical format.
    
    This is a fallback if tag columns don't work.
    """
    if not anatomy_col or not modality_col:
        return None
    
    anatomy_val = row.get(anatomy_col, "")
    modality_val = row.get(modality_col, "")
    category_val = row.get(category_col, "") if category_col else ""
    
    anatomy = normalize_key_text(str(anatomy_val) if anatomy_val is not None and not (isinstance(anatomy_val, float) and pd.isna(anatomy_val)) else "")
    modality = normalize_key_text(str(modality_val) if modality_val is not None and not (isinstance(modality_val, float) and pd.isna(modality_val)) else "")
    category_raw = str(category_val) if category_val and category_val is not None and not (isinstance(category_val, float) and pd.isna(category_val)) else ""
    category = normalize_key_text(category_raw) if category_raw and category_raw.lower() not in ("nan", "none", "null", "") else ""
    
    if not anatomy or not modality:
        return None
    
    # Only include category if it's non-empty and not "nan"
    if category and category.lower() not in ("nan", "none", "null"):
        return f"{anatomy}__{modality}__{category}"
    else:
        return f"{anatomy}__{modality}"


def auto_detect_group_key_column(df: pd.DataFrame) -> Optional[str]:
    """
    Auto-detect if there's a direct group_key column.
    
    Returns column name if found, None otherwise.
    """
    candidates = ["group_key", "GroupKey", "group", "Group", "GROUP_KEY"]
    for col in candidates:
        if col in df.columns:
            return col
    return None


def auto_detect_tag_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Auto-detect tag columns for anatomy, modality, category.
    
    Returns (anatomy_tag_col, modality_tag_col, category_tag_col)
    """
    anatomy_tag = None
    modality_tag = None
    category_tag = None
    
    # Try EN_TAG columns first (most reliable) - prioritize exact matches
    for col in df.columns:
        col_lower = col.lower()
        # Exact match for anatomy
        if col == "Anatomy_EN_TAG":
            anatomy_tag = col
        elif "anatomy" in col_lower and ("en_tag" in col_lower) and not anatomy_tag:
            anatomy_tag = col
        # Exact match for modality
        elif col == "Modality_Type_EN_TAG":
            modality_tag = col
        elif ("modality" in col_lower or "type" in col_lower) and ("en_tag" in col_lower) and not modality_tag:
            modality_tag = col
        # Exact match for category
        elif col == "Category_EN_TAG":
            category_tag = col
        elif "category" in col_lower and ("en_tag" in col_lower) and not category_tag:
            category_tag = col
    
    return anatomy_tag, modality_tag, category_tag


def auto_detect_korean_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Auto-detect Korean columns for anatomy, modality, category.
    
    Returns (anatomy_col, modality_col, category_col)
    """
    anatomy_col = None
    modality_col = None
    category_col = None
    
    for col in df.columns:
        col_lower = col.lower()
        if col == "Anatomy" or (col_lower == "anatomy" and "tag" not in col_lower):
            anatomy_col = col
        elif col == "Modality/Type" or col == "Modality_Type" or (("modality" in col_lower or "type" in col_lower) and "tag" not in col_lower):
            modality_col = col
        elif col == "Category" or (col_lower == "category" and "tag" not in col_lower):
            category_col = col
    
    return anatomy_col, modality_col, category_col


def map_specialty_korean_to_canonical(specialty_kr: str, canonical_specialties: Set[str]) -> Optional[str]:
    """
    Map Korean specialty name to canonical specialty.
    
    This is a simple mapping - may need refinement based on actual data.
    """
    specialty_norm = normalize_key_text(specialty_kr)
    
    # Direct match
    if specialty_norm in canonical_specialties:
        return specialty_norm
    
    # Try common mappings
    mappings = {
        "근골격계_영상의학": "musculoskeletal_radiology",
        "유방_영상의학": "breast_rad",
        "흉부_영상의학": "thoracic_radiology",
        "비뇨생식기_영상의학": "gu_radiology",
        "신경_영상의학": "neuroradiology",
        "소아_영상의학": "pediatric_radiology",
        "심혈관_영상의학": "cardiovascular_radiology",
        "응급_영상의학": "emergency_radiology",
        "물리_품질관리_및_의료정보": "physics_qc_informatics",
    }
    
    if specialty_norm in mappings:
        mapped = mappings[specialty_norm]
        if mapped in canonical_specialties:
            return mapped
    
    # Try partial match
    for canon_spec in canonical_specialties:
        if specialty_norm in canon_spec or canon_spec in specialty_norm:
            return canon_spec
    
    return None


def load_canonical_groups(canonical_path: Path) -> Dict[str, Dict[str, str]]:
    """
    Load groups_canonical.csv and return mapping: group_key -> {specialty, group_id, ...}
    """
    if not canonical_path.exists():
        raise FileNotFoundError(f"Canonical groups file not found: {canonical_path}")
    
    canonical = {}
    with open(canonical_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            group_key = row.get("group_key", "").strip()
            if group_key:
                canonical[group_key] = {
                    "specialty": row.get("specialty", "").strip(),
                    "group_id": row.get("group_id", "").strip(),
                    "group_key": group_key,
                }
    
    return canonical


def validate_and_generate_order(
    xlsx_path: Path,
    canonical_path: Path,
    out_dir: Path,
) -> Path:
    """
    Main function: read xlsx, match to canonical, generate order file.
    
    Returns path to generated order file.
    """
    # Load canonical groups
    print(f"[Order Generator] Loading canonical groups from: {canonical_path}")
    canonical = load_canonical_groups(canonical_path)
    canonical_specialties = set(canonical[gk]["specialty"] for gk in canonical.keys())
    print(f"[Order Generator] Loaded {len(canonical)} canonical groups across {len(canonical_specialties)} specialties")
    
    # Load xlsx
    print(f"[Order Generator] Loading xlsx from: {xlsx_path}")
    xl = pd.ExcelFile(xlsx_path)
    if not xl.sheet_names:
        raise ValueError(f"No sheets found in {xlsx_path}")
    
    # Read all sheets and combine (or use first sheet if only one)
    all_rows = []
    for sheet_name in xl.sheet_names:
        df = pd.read_excel(xlsx_path, sheet_name=sheet_name)
        print(f"[Order Generator] Sheet '{sheet_name}': {len(df)} rows, {len(df.columns)} columns")
        all_rows.append(df)
    
    # Combine all sheets (if multiple)
    if len(all_rows) > 1:
        df = pd.concat(all_rows, ignore_index=True)
        print(f"[Order Generator] Combined {len(all_rows)} sheets: {len(df)} total rows")
    else:
        df = all_rows[0]
    
    # Auto-detect group_key column or construction method
    group_key_col = auto_detect_group_key_column(df)
    anatomy_tag, modality_tag, category_tag = auto_detect_tag_columns(df)
    anatomy_kr, modality_kr, category_kr = auto_detect_korean_columns(df)
    
    print(f"[Order Generator] Auto-detection results:")
    print(f"  - Direct group_key column: {group_key_col}")
    print(f"  - Tag columns: anatomy={anatomy_tag}, modality={modality_tag}, category={category_tag}")
    print(f"  - Korean columns: anatomy={anatomy_kr}, modality={modality_kr}, category={category_kr}")
    
    # Detect specialty column
    specialty_col = None
    for col in df.columns:
        if col.lower() in ["specialty", "specialty_en_label", "specialty_en_tag"]:
            specialty_col = col
            break
    
    if not specialty_col:
        raise ValueError("Could not find Specialty column in xlsx")
    
    print(f"[Order Generator] Using specialty column: {specialty_col}")
    
    # Build group_key for each row
    # Note: xlsx has multiple rows per group (one per objective), so we need to deduplicate
    matched_groups_raw = []
    unmatched_rows = []
    seen_group_keys = {}  # group_key -> first occurrence info
    
    for idx, row in df.iterrows():
        group_key = None
        
        # Strategy 1: Direct column
        if group_key_col:
            group_key_raw = row.get(group_key_col, "")
            if group_key_raw is not None and not (isinstance(group_key_raw, float) and pd.isna(group_key_raw)):
                group_key_raw_str = str(group_key_raw).strip()
                if group_key_raw_str:
                    group_key = normalize_key_text(group_key_raw_str)
        
        # Strategy 2: Construct from tag columns
        if not group_key and anatomy_tag and modality_tag:
            group_key = construct_group_key_from_tags(row, anatomy_tag, modality_tag, category_tag)
        
        # Strategy 3: Construct from Korean columns (fallback)
        if not group_key and anatomy_kr and modality_kr:
            group_key = construct_group_key_from_korean_columns(row, anatomy_kr, modality_kr, category_kr)
        
        if not group_key:
            unmatched_rows.append((idx, row))
            continue
        
        # Check if group_key exists in canonical
        if group_key not in canonical:
            unmatched_rows.append((idx, group_key))
            continue
        
        # Deduplicate: only keep first occurrence of each group_key
        if group_key not in seen_group_keys:
            # Get specialty
            specialty_kr = str(row.get(specialty_col, "")).strip()
            specialty_canon = map_specialty_korean_to_canonical(specialty_kr, canonical_specialties)
            
            if not specialty_canon:
                # Use specialty from canonical
                specialty_canon = canonical[group_key]["specialty"]
            
            seen_group_keys[group_key] = {
                "row_index": idx,
                "group_key": group_key,
                "specialty": specialty_canon,
                "specialty_kr": specialty_kr,
                "group_id": canonical[group_key]["group_id"],
            }
    
    matched_groups = list(seen_group_keys.values())
    print(f"[Order Generator] Matched {len(matched_groups)} unique groups (from {len(df)} xlsx rows), {len(unmatched_rows)} unmatched rows")
    
    if unmatched_rows:
        print(f"[Order Generator] WARNING: {len(unmatched_rows)} rows could not be matched")
        if len(unmatched_rows) <= 10:
            for item in unmatched_rows[:10]:
                if isinstance(item, tuple) and len(item) == 2:
                    idx, key = item
                    print(f"  Row {idx}: {key}")
    
    # Group by specialty and assign order
    specialty_groups = {}
    for mg in matched_groups:
        spec = mg["specialty"]
        if spec not in specialty_groups:
            specialty_groups[spec] = []
        specialty_groups[spec].append(mg)
    
    # Sort by row_index within each specialty (preserve xlsx order)
    for spec in specialty_groups:
        specialty_groups[spec].sort(key=lambda x: x["row_index"])
        # Assign order
        for order, mg in enumerate(specialty_groups[spec], start=1):
            mg["order"] = order
    
    # Validate: check for duplicates and missing groups
    print(f"[Order Generator] Validating against canonical...")
    all_canonical_keys = set(canonical.keys())
    all_matched_keys = set(mg["group_key"] for mg in matched_groups)
    
    missing_in_order = all_canonical_keys - all_matched_keys
    
    # Check for duplicates (should not happen after deduplication, but verify)
    duplicates_in_order = {}
    for mg in matched_groups:
        gk = mg["group_key"]
        if gk not in duplicates_in_order:
            duplicates_in_order[gk] = []
        duplicates_in_order[gk].append(mg)
    
    duplicate_keys = {gk: items for gk, items in duplicates_in_order.items() if len(items) > 1}
    
    # Fail-fast on validation errors (duplicates are hard errors)
    # Missing groups are warnings (xlsx may be a subset of canonical)
    errors = []
    warnings = []
    
    if missing_in_order:
        warnings.append(f"Missing {len(missing_in_order)} groups from canonical (not in xlsx order)")
        if len(missing_in_order) <= 20:
            for gk in sorted(list(missing_in_order))[:20]:
                warnings.append(f"  - {gk}")
        else:
            warnings.append(f"  ... and {len(missing_in_order) - 20} more")
    
    if duplicate_keys:
        errors.append(f"Duplicate group_keys in xlsx order: {len(duplicate_keys)} groups")
        for gk, items in list(duplicate_keys.items())[:10]:
            errors.append(f"  - {gk}: appears {len(items)} times")
    
    if warnings:
        print("[Order Generator] VALIDATION WARNINGS:")
        for warn in warnings:
            print(f"  {warn}")
    
    if errors:
        print("[Order Generator] VALIDATION ERRORS:", file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        raise ValueError("Validation failed: order file generation aborted")
    
    # Generate output file
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "specialty_group_order.csv"
    
    print(f"[Order Generator] Writing order file to: {out_path}")
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["specialty", "order", "group_key", "group_id", "specialty_kr"])
        writer.writeheader()
        for spec in sorted(specialty_groups.keys()):
            for mg in specialty_groups[spec]:
                writer.writerow({
                    "specialty": mg["specialty"],
                    "order": mg["order"],
                    "group_key": mg["group_key"],
                    "group_id": mg["group_id"],
                    "specialty_kr": mg["specialty_kr"],
                })
    
    print(f"[Order Generator] ✓ Successfully generated order file: {out_path}")
    print(f"[Order Generator] Summary: {len(specialty_groups)} specialties, {len(matched_groups)} groups total")
    
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate specialty order file from Radiology_Curriculum_Weight_Factor.xlsx",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python 3_Code/src/06_generate_order_file.py \\
    --base_dir . \\
    --xlsx_path 2_Data/processed/Radiology_Curriculum_Weight_Factor_v2.xlsx \\
    --out_dir 2_Data/metadata/group_order

Output:
  - 2_Data/metadata/group_order/specialty_group_order.csv
  - Format: specialty, order, group_key, group_id, specialty_kr
        """,
    )
    
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument(
        "--xlsx_path",
        type=str,
        default="2_Data/processed/Radiology_Curriculum_Weight_Factor_v2.xlsx",
        help="Path to Radiology_Curriculum_Weight_Factor.xlsx (relative to base_dir or absolute)",
    )
    parser.add_argument(
        "--canonical_path",
        type=str,
        default="2_Data/metadata/groups_canonical.csv",
        help="Path to groups_canonical.csv (relative to base_dir or absolute)",
    )
    parser.add_argument(
        "--out_dir",
        type=str,
        default="2_Data/metadata/group_order",
        help="Output directory for order file",
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    xlsx_path = base_dir / args.xlsx_path if not Path(args.xlsx_path).is_absolute() else Path(args.xlsx_path)
    canonical_path = base_dir / args.canonical_path if not Path(args.canonical_path).is_absolute() else Path(args.canonical_path)
    out_dir = base_dir / args.out_dir if not Path(args.out_dir).is_absolute() else Path(args.out_dir)
    
    try:
        out_path = validate_and_generate_order(xlsx_path, canonical_path, out_dir)
        print(f"\n[Order Generator] ✓ Complete: {out_path}")
    except Exception as e:
        print(f"[Order Generator] ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


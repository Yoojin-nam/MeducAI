from pathlib import Path

def generated_run_dir(base_dir: Path, run_tag: str) -> Path:
    """
    Returns: 2_Data/metadata/generated/<run_tag>
    This is the new canonical path for all metadata outputs (CSV/JSON/Summary).
    """
    return base_dir / "2_Data" / "metadata" / "generated" / run_tag

def generated_image_dir(base_dir: Path, run_tag: str, kind: str) -> Path:
    """
    Returns: 2_Data/images/generated/<run_tag>/<kind>
    This is the new canonical path for all image outputs and manifests.
    (Provider folder is intentionally removed for path simplification)
    """
    return base_dir / "2_Data" / "images" / "generated" / run_tag / kind

def resolve_in_run_dir(base_dir: Path, run_tag: str, provider: str, filename: str) -> Path:
    """
    Finds a file created by Step 01/02/03.5 inside the unified <run_tag> metadata folder.
    Used for CSV inputs (e.g., anki_cards_<provider>_<run_tag>__armX.csv).
    
    Legacy support is deprecated; only the unified path is supported in v3.7+.
    """
    run_dir = generated_run_dir(base_dir, run_tag)
    # The provider is still part of the filename for auditability (e.g., anki_cards_gemini_S0_...)
    # The generated_run_dir logic handles the file path consolidation.
    return run_dir / filename

# Legacy function kept but updated to ONLY use the new path structure
# to force all scripts to conform to the new standard.
def resolve_in_run_or_legacy(base_dir: Path, run_tag: str, provider: str, filename: str) -> Path:
    return resolve_in_run_dir(base_dir, run_tag, provider, filename)


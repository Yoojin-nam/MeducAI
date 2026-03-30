"""
Path resolver utility for S2 results files with backward compatibility.

This module provides functions to resolve S2 results file paths,
supporting both the new format (with S1 arm) and legacy format (arm only).
"""

from pathlib import Path
from typing import Optional


def resolve_s2_results_path(
    out_dir: Path,
    arm: str,
    s1_arm: Optional[str] = None,
) -> Path:
    """
    Resolve S2 results file path with backward compatibility.
    
    Tries the following in order:
    1. New format: s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl (if s1_arm is provided and different from arm)
    2. New format (same arm): s2_results__s1arm{ARM}__s2arm{ARM}.jsonl (if s1_arm is provided)
    3. Legacy format: s2_results__arm{ARM}.jsonl (for backward compatibility with S0 results)
    
    Args:
        out_dir: Output directory (e.g., 2_Data/metadata/generated/{RUN_TAG})
        arm: S2 execution arm
        s1_arm: S1 arm used for reading (optional, defaults to arm)
    
    Returns:
        Path to S2 results file (first existing file found, or new format path if none exist)
    """
    s1_arm_actual = (s1_arm or arm).strip().upper()
    arm_upper = arm.strip().upper()
    
    # Try new format first (if s1_arm is different from arm, or if explicitly provided)
    if s1_arm is not None or s1_arm_actual != arm_upper:
        new_format_path = out_dir / f"s2_results__s1arm{s1_arm_actual}__s2arm{arm_upper}.jsonl"
        if new_format_path.exists():
            return new_format_path
    
    # Try legacy format for backward compatibility (S0 results)
    legacy_path = out_dir / f"s2_results__arm{arm_upper}.jsonl"
    if legacy_path.exists():
        return legacy_path
    
    # If neither exists, return new format path (for writing)
    if s1_arm is not None or s1_arm_actual != arm_upper:
        return out_dir / f"s2_results__s1arm{s1_arm_actual}__s2arm{arm_upper}.jsonl"
    else:
        # If same arm, prefer new format but fallback to legacy for writing
        return out_dir / f"s2_results__s1arm{arm_upper}__s2arm{arm_upper}.jsonl"


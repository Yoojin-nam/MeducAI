#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Anki Image Optimization Pipeline

Optimizes images for Anki with two modes:
- Sample mode: Generate multiple variants for a subset of images
- Final mode: Apply chosen settings to full dataset
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import shutil
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageOps
from tqdm import tqdm


# =========================
# Data Structures
# =========================

# Guardrails / heuristics
SMALL_JPEG_SKIP_REENCODE_KB = 400  # If no resize and original JPEG is already small, prefer copying over re-encoding.

@dataclass
class ImageInfo:
    """Metadata for a single image file."""
    path: Path
    size_bytes: int
    width: int
    height: int
    extension: str


@dataclass
class ClassifiedImageInfo:
    """Image info with color classification."""
    image_info: ImageInfo
    color_class: str  # "GRAY" or "COLOR"
    chroma_score: float


@dataclass
class OptimizationResult:
    """Result of optimizing a single image."""
    original_path: Path
    output_path: Path
    original_size_kb: float
    output_size_kb: float
    attempted_output_size_kb: float
    attempted_output_ge_original: bool
    original_w: int
    original_h: int
    output_w: int
    output_h: int
    color_class: str
    width_target: int
    quality: int
    grayscale_encoded: bool
    action_taken: str  # "reencode", "resize_only", "converted_from_png", "no_change"
    fallback_used: str  # "none", "original", "lossless_opt"
    chroma_score: float = 0.0  # For verification/debugging
    qc_equip_hint: bool = False  # True if filename contains QC/EQUIPMENT hint

@dataclass
class FinalManifestRow:
    """Row for final-mode manifest output."""
    status: str  # "OK", "SKIPPED", "ERROR"
    error: str
    original_path: Path
    output_path: Path
    original_rel_path: str
    output_rel_path: str
    original_ext: str
    output_ext: str
    original_size_kb: float
    output_size_kb: float
    attempted_output_size_kb: float
    attempted_output_ge_original: bool
    original_w: int
    original_h: int
    output_w: int
    output_h: int
    color_class: str
    chroma_score: float
    width_target: int
    quality: int
    grayscale_encoded: bool
    action_taken: str
    fallback_used: str


# =========================
# RUN_TAG & Directory Management (Image Asset Naming Convention)
# =========================

def extract_run_tag(input_dir: Path) -> Optional[str]:
    """Extract RUN_TAG from input directory path.
    
    Expected path structure: 2_Data/metadata/generated/{RUN_TAG}/images/
    
    Args:
        input_dir: Input directory path (should be images/ subdirectory)
        
    Returns:
        RUN_TAG string if path structure matches, None otherwise
    """
    try:
        # Resolve absolute path
        abs_path = input_dir.resolve()
        parts = abs_path.parts
        
        # Look for the pattern: .../2_Data/metadata/generated/{RUN_TAG}/images/
        try:
            # Find 'generated' in path parts
            gen_idx = None
            for i, part in enumerate(parts):
                if part == 'generated':
                    gen_idx = i
                    break
            
            if gen_idx is None or gen_idx + 1 >= len(parts):
                return None
            
            # Next part after 'generated' should be RUN_TAG
            # Input dir should be 'images' (last part)
            if parts[-1] == 'images' and gen_idx + 1 < len(parts) - 1:
                run_tag = parts[gen_idx + 1]
                return run_tag
        except (IndexError, AttributeError):
            pass
        
        # Fallback: try parent directory name if input_dir ends with 'images'
        if abs_path.name == 'images':
            parent = abs_path.parent
            # Check if parent/grandparent structure suggests RUN_TAG
            if parent.name and parent.parent.name == 'generated':
                return parent.name
        
        return None
    except Exception:
        return None


def get_output_dir(input_dir: Path, mode: str, custom_out: Optional[str] = None) -> Path:
    """Get output directory path following Image Asset Naming Convention.
    
    Creates output directory at same RUN_TAG level:
    - sample mode: {RUN_TAG}/images_sample/
    - final mode: {RUN_TAG}/images_anki/
    
    Args:
        input_dir: Input directory (should be {RUN_TAG}/images/)
        mode: 'sample' or 'final'
        custom_out: Optional custom output directory name (relative to RUN_TAG dir)
        
    Returns:
        Output directory Path
    """
    run_tag = extract_run_tag(input_dir)
    
    if custom_out:
        # User specified custom output directory
        if run_tag:
            # If RUN_TAG extracted, create at same level
            run_tag_dir = input_dir.parent
            return run_tag_dir / custom_out
        else:
            # Fallback: relative to input_dir
            return input_dir.parent / custom_out
    else:
        # Default output directories
        if run_tag:
            run_tag_dir = input_dir.parent
            if mode == 'sample':
                return run_tag_dir / 'images_sample'
            elif mode == 'final':
                return run_tag_dir / 'images_anki'
            else:
                raise ValueError(f"Unknown mode: {mode}")
        else:
            # Fallback: create in input_dir parent
            parent = input_dir.parent
            if mode == 'sample':
                return parent / 'images_sample'
            elif mode == 'final':
                return parent / 'images_anki'
            else:
                raise ValueError(f"Unknown mode: {mode}")


# =========================
# Step 0: Inventory & Format Check
# =========================

def inventory_images(input_dir: Path, read_dimensions: bool = True) -> List[ImageInfo]:
    """Scan input_dir recursively for image files and collect metadata.
    
    Args:
        input_dir: Directory to scan for images
        read_dimensions: If True, open images to read width/height (slower).
                        If False, width/height are set to 0 (faster; suitable for sampling).
        
    Returns:
        List of ImageInfo objects with path, size, dimensions, and extension
    """
    image_extensions = {'.jpg', '.jpeg', '.png'}
    image_info_list: List[ImageInfo] = []
    
    # Recursively scan for image files
    for image_path in input_dir.rglob('*'):
        if not image_path.is_file():
            continue
            
        # Check extension (case-insensitive)
        ext = image_path.suffix.lower()
        if ext not in image_extensions:
            continue
        
        # Get file size
        size_bytes = image_path.stat().st_size

        width = height = 0
        if read_dimensions:
            try:
                # Get image dimensions (best-effort; corrupt images still get inventoried)
                with Image.open(image_path) as img:
                    width, height = img.size
            except Exception as e:
                width, height = 0, 0
                print(f"[WARNING] Unreadable image (will be processed as ERROR later): {image_path}: {e}", file=sys.stderr)

        image_info_list.append(
            ImageInfo(
                path=image_path,
                size_bytes=size_bytes,
                width=width,
                height=height,
                extension=ext,
            )
        )
    
    return image_info_list


def _safe_relpath(path: Path, base: Path) -> str:
    """Return a stable, POSIX-ish relative path for manifest/printing."""
    try:
        rel = path.relative_to(base)
        return rel.as_posix()
    except Exception:
        return path.name


def _has_subdirs(image_info_list: List[ImageInfo], input_dir: Path) -> bool:
    """Return True if any inventoried image is under a subdirectory of input_dir."""
    for info in image_info_list:
        try:
            if len(info.path.relative_to(input_dir).parts) > 1:
                return True
        except Exception:
            continue
    return False


def compute_size_statistics(sizes: List[int]) -> Tuple[int, int, int]:
    """Compute min, median, and p95 for a list of sizes.
    
    Args:
        sizes: List of file sizes in bytes
        
    Returns:
        Tuple of (min, median, p95) in bytes
    """
    if not sizes:
        return (0, 0, 0)
    
    sorted_sizes = sorted(sizes)
    min_size = sorted_sizes[0]
    median_size = int(statistics.median(sorted_sizes))
    
    # Calculate p95 (95th percentile)
    p95_index = int(len(sorted_sizes) * 0.95)
    p95_size = sorted_sizes[p95_index] if p95_index < len(sorted_sizes) else sorted_sizes[-1]
    
    return (min_size, median_size, p95_size)


def print_inventory_summary(image_info_list: List[ImageInfo]) -> None:
    """Print summary of image inventory: counts, extensions, size distribution.
    
    Args:
        image_info_list: List of ImageInfo objects
    """
    if not image_info_list:
        print("No image files found.")
        return
    
    # Count by extension
    ext_counts = {}
    ext_sizes = {}
    for info in image_info_list:
        ext = info.extension
        ext_counts[ext] = ext_counts.get(ext, 0) + 1
        if ext not in ext_sizes:
            ext_sizes[ext] = []
        ext_sizes[ext].append(info.size_bytes)
    
    # Overall size distribution
    all_sizes = [info.size_bytes for info in image_info_list]
    min_size, median_size, p95_size = compute_size_statistics(all_sizes)
    
    # Print summary
    print("=" * 60)
    print("Image Inventory Summary")
    print("=" * 60)
    print(f"Total files: {len(image_info_list)}")
    print()
    print("Extension counts:")
    for ext in sorted(ext_counts.keys()):
        count = ext_counts[ext]
        print(f"  {ext}: {count}")
    print()
    print("Size distribution (all files):")
    print(f"  Min:    {min_size:,} bytes ({min_size / 1024:.1f} KB)")
    print(f"  Median: {median_size:,} bytes ({median_size / 1024:.1f} KB)")
    print(f"  P95:    {p95_size:,} bytes ({p95_size / 1024:.1f} KB)")
    print()
    
    # Per-extension size distribution
    if len(ext_counts) > 1:
        print("Size distribution by extension:")
        for ext in sorted(ext_counts.keys()):
            sizes = ext_sizes[ext]
            min_e, median_e, p95_e = compute_size_statistics(sizes)
            print(f"  {ext}:")
            print(f"    Min:    {min_e:,} bytes ({min_e / 1024:.1f} KB)")
            print(f"    Median: {median_e:,} bytes ({median_e / 1024:.1f} KB)")
            print(f"    P95:    {p95_e:,} bytes ({p95_e / 1024:.1f} KB)")
        print()
    
    print("=" * 60)


# =========================
# Step 1: Lightweight Color Profile Separation
# =========================

def classify_color(image_path: Path, threshold: float = 0.15) -> Tuple[str, float]:
    """Classify an image as GRAY or COLOR using chroma score.
    
    Algorithm:
    1. Load image and downsample to max 256px on longest side (for performance)
    2. Compute chroma score: mean(abs(R-G) + abs(G-B) + abs(B-R)) normalized
    3. Threshold: score > threshold → COLOR, else → GRAY
    
    Args:
        image_path: Path to the image file
        threshold: Chroma score threshold (default 0.15)
        
    Returns:
        Tuple of (class, chroma_score) where class is "GRAY" or "COLOR"
    """
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary (handles grayscale, RGBA, etc.)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Downsample to max 256px on longest side for performance
            width, height = img.size
            max_dim = max(width, height)
            if max_dim > 256:
                scale_factor = 256.0 / max_dim
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert PIL image to numpy array
            img_array = np.array(img, dtype=np.float32)
            
            # Compute chroma score: mean(abs(R-G) + abs(G-B) + abs(B-R))
            # Normalize by dividing by 255.0 to get score in range [0, 1]
            r = img_array[:, :, 0]
            g = img_array[:, :, 1]
            b = img_array[:, :, 2]
            
            chroma_diff = np.abs(r - g) + np.abs(g - b) + np.abs(b - r)
            chroma_score = np.mean(chroma_diff) / 255.0
            
            # Classify based on threshold
            color_class = "COLOR" if chroma_score > threshold else "GRAY"
            
            return (color_class, float(chroma_score))
            
    except Exception as e:
        # If classification fails, default to COLOR (safer default)
        # This should be rare, but we want to handle corrupt images gracefully
        print(f"[WARNING] Failed to classify {image_path}: {e}", file=sys.stderr)
        return ("COLOR", 0.0)


def classify_images(image_info_list: List[ImageInfo], threshold: float = 0.15) -> List[ClassifiedImageInfo]:
    """Classify a list of images as GRAY or COLOR.
    
    Args:
        image_info_list: List of ImageInfo objects to classify
        threshold: Chroma score threshold (default 0.15)
        
    Returns:
        List of ClassifiedImageInfo objects
    """
    classified_list: List[ClassifiedImageInfo] = []
    
    for image_info in image_info_list:
        color_class, chroma_score = classify_color(image_info.path, threshold)
        classified_list.append(ClassifiedImageInfo(
            image_info=image_info,
            color_class=color_class,
            chroma_score=chroma_score
        ))
    
    return classified_list


def pick_final_class(
    image_path: Path,
    base_class: str,
    chroma_score: float,
    threshold: float,
) -> str:
    """Apply filename hints (QC/EQUIP) to adjust class selection for final mode.

    Policy (per plan):
    - If filename has QC/EQUIP hint -> prefer COLOR
    - Unless classifier *strongly* indicates GRAY
    """
    name = image_path.name.lower()
    hinted = ("qc" in name) or ("equip" in name)
    if not hinted:
        return base_class

    # Strong GRAY: well below threshold.
    strong_gray = (base_class == "GRAY") and (chroma_score <= (threshold * 0.5))
    return "GRAY" if strong_gray else "COLOR"


def refine_color_class_with_color_fraction(
    *,
    image_path: Path,
    base_class: str,
    chroma_score: float,
    threshold: float,
    near_factor: float = 0.90,
    spread_threshold: int = 15,
    frac_threshold: float = 0.01,
) -> Tuple[str, float]:
    """Refine GRAY/COLOR decision using a second cheap signal (color pixel fraction).

    We only pay extra cost when base_class is GRAY and chroma_score is near the threshold.
    This prevents COLOR images (e.g., subtle tinted backgrounds) from being treated as GRAY,
    which would otherwise trigger grayscale encoding and destroy color information.
    """
    try:
        if base_class != "GRAY":
            return base_class, 0.0
        if float(chroma_score) < float(threshold) * float(near_factor):
            return base_class, 0.0
        frac = compute_color_pixel_fraction(image_path, spread_threshold=spread_threshold)
        if frac >= float(frac_threshold):
            return "COLOR", float(frac)
        return base_class, float(frac)
    except Exception:
        return base_class, 0.0


def refine_classified_list_inplace(
    classified_list: List[ClassifiedImageInfo],
    *,
    threshold: float,
    near_factor: float = 0.90,
    spread_threshold: int = 15,
    frac_threshold: float = 0.01,
) -> None:
    """Mutate ClassifiedImageInfo entries to reduce COLOR→GRAY misclassification risk."""
    for c in classified_list:
        if _is_table_image_name(c.image_info.path.name):
            continue
        refined, _frac = refine_color_class_with_color_fraction(
            image_path=c.image_info.path,
            base_class=c.color_class,
            chroma_score=c.chroma_score,
            threshold=threshold,
            near_factor=near_factor,
            spread_threshold=spread_threshold,
            frac_threshold=frac_threshold,
        )
        c.color_class = refined


def print_color_classification_summary(classified_list: List[ClassifiedImageInfo]) -> None:
    """Print summary of color classification: counts, examples, size distribution.
    
    Args:
        classified_list: List of ClassifiedImageInfo objects
    """
    if not classified_list:
        print("No images to classify.")
        return
    
    # Separate by class
    gray_images = [c for c in classified_list if c.color_class == "GRAY"]
    color_images = [c for c in classified_list if c.color_class == "COLOR"]
    
    # Print summary
    print("=" * 60)
    print("Color Classification Summary")
    print("=" * 60)
    print(f"Total images: {len(classified_list)}")
    print(f"  GRAY:  {len(gray_images)} ({len(gray_images)/len(classified_list)*100:.1f}%)")
    print(f"  COLOR: {len(color_images)} ({len(color_images)/len(classified_list)*100:.1f}%)")
    print()
    
    # Example filenames per class
    print("Example filenames:")
    if gray_images:
        print("  GRAY examples:")
        for classified in gray_images[:5]:  # Show up to 5 examples
            print(f"    {classified.image_info.path.name}")
        if len(gray_images) > 5:
            print(f"    ... and {len(gray_images) - 5} more")
    if color_images:
        print("  COLOR examples:")
        for classified in color_images[:5]:  # Show up to 5 examples
            print(f"    {classified.image_info.path.name}")
        if len(color_images) > 5:
            print(f"    ... and {len(color_images) - 5} more")
    print()
    
    # Size distribution per class
    print("Size distribution by class:")
    
    if gray_images:
        gray_sizes = [c.image_info.size_bytes for c in gray_images]
        min_g, median_g, p95_g = compute_size_statistics(gray_sizes)
        print(f"  GRAY:")
        print(f"    Count:  {len(gray_images)}")
        print(f"    Min:    {min_g:,} bytes ({min_g / 1024:.1f} KB)")
        print(f"    Median: {median_g:,} bytes ({median_g / 1024:.1f} KB)")
        print(f"    P95:    {p95_g:,} bytes ({p95_g / 1024:.1f} KB)")
    
    if color_images:
        color_sizes = [c.image_info.size_bytes for c in color_images]
        min_c, median_c, p95_c = compute_size_statistics(color_sizes)
        print(f"  COLOR:")
        print(f"    Count:  {len(color_images)}")
        print(f"    Min:    {min_c:,} bytes ({min_c / 1024:.1f} KB)")
        print(f"    Median: {median_c:,} bytes ({median_c / 1024:.1f} KB)")
        print(f"    P95:    {p95_c:,} bytes ({p95_c / 1024:.1f} KB)")
    
    print()
    print("=" * 60)


# =========================
# Step 2: Sampling Selection Strategy
# =========================

def _parse_csv_int_list(s: Optional[str]) -> Optional[List[int]]:
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    out: List[int] = []
    for part in s.split(","):
        p = part.strip()
        if not p:
            continue
        out.append(int(p))
    return out or None


def _is_table_image_name(filename: str) -> bool:
    # Table images have pattern: IMG__...__TABLE.jpg or IMG__...__TABLE__cluster_X.jpg
    return "__TABLE" in filename


def select_samples(
    classified_list: List[ClassifiedImageInfo],
    n: int = 60,
    compressed_threshold_kb: int = 400,
    unoptimized_threshold_kb: int = 1500
) -> List[ClassifiedImageInfo]:
    """Select balanced sample of images for optimization testing.
    
    Balanced selection strategy:
    - 20 from "already compressed" group (smallest files, <400KB)
    - 30 from "unoptimized large" group (largest files, >1.5MB)
    - 10 from QC/EQUIPMENT hints (filename contains "QC" or "EQUIP"), 
      or COLOR class if hints unavailable
    
    Ensures diversity: Mix of GRAY/COLOR based on classification.
    
    Args:
        classified_list: List of ClassifiedImageInfo objects to select from
        n: Total number of samples to select (default 60)
        compressed_threshold_kb: Size threshold in KB for "compressed" group (default 400)
        unoptimized_threshold_kb: Size threshold in KB for "unoptimized" group (default 1500)
        
    Returns:
        List of selected ClassifiedImageInfo objects
    """
    if not classified_list:
        return []
    
    if n <= 0:
        return []
    
    # Filter out TABLE images (processed separately)
    filtered_list: List[ClassifiedImageInfo] = []
    table_images_count = 0
    for classified in classified_list:
        filename = classified.image_info.path.name
        if _is_table_image_name(filename):
            table_images_count += 1
        else:
            filtered_list.append(classified)
    
    if table_images_count > 0:
        print(f"[INFO] Excluded {table_images_count} TABLE images from sampling (will be processed separately)")
    
    classified_list = filtered_list
    
    if not classified_list:
        print("[WARNING] No non-TABLE images found after filtering")
        return []
    
    # Convert thresholds to bytes
    compressed_threshold_bytes = compressed_threshold_kb * 1024
    unoptimized_threshold_bytes = unoptimized_threshold_kb * 1024
    
    # Separate images by size category
    compressed_images: List[ClassifiedImageInfo] = []
    unoptimized_images: List[ClassifiedImageInfo] = []
    medium_images: List[ClassifiedImageInfo] = []
    
    for classified in classified_list:
        size_bytes = classified.image_info.size_bytes
        if size_bytes < compressed_threshold_bytes:
            compressed_images.append(classified)
        elif size_bytes > unoptimized_threshold_bytes:
            unoptimized_images.append(classified)
        else:
            medium_images.append(classified)
    
    # Find QC/EQUIPMENT hints
    qc_hint_images: List[ClassifiedImageInfo] = []
    for classified in classified_list:
        filename_lower = classified.image_info.path.name.lower()
        if 'qc' in filename_lower or 'equip' in filename_lower:
            qc_hint_images.append(classified)
    
    # Calculate target counts (proportional to n=60)
    target_compressed = int(20 * n / 60)
    target_unoptimized = int(30 * n / 60)
    target_qc_hints = int(10 * n / 60)
    
    selected: List[ClassifiedImageInfo] = []
    used_paths = set()  # Track selected paths to avoid duplicates
    
    def add_if_not_used(classified: ClassifiedImageInfo) -> bool:
        """Add classified image if not already selected."""
        if classified.image_info.path not in used_paths:
            selected.append(classified)
            used_paths.add(classified.image_info.path)
            return True
        return False
    
    # Helper to select with GRAY/COLOR diversity
    def select_with_diversity(
        candidates: List[ClassifiedImageInfo],
        count: int,
        prefer_class: Optional[str] = None
    ) -> None:
        """Select images ensuring GRAY/COLOR diversity.
        
        Args:
            candidates: List of candidates to select from
            count: Number to select
            prefer_class: If specified, prefer this class but still ensure diversity
        """
        if not candidates or count <= 0:
            return
        
        # Separate by class
        gray_candidates = [c for c in candidates if c.color_class == "GRAY" and c.image_info.path not in used_paths]
        color_candidates = [c for c in candidates if c.color_class == "COLOR" and c.image_info.path not in used_paths]
        
        # Calculate target distribution (roughly balanced)
        target_gray = max(1, count // 2) if gray_candidates else 0
        target_color = max(1, count // 2) if color_candidates else 0
        
        # Adjust if one class is preferred
        if prefer_class == "GRAY" and gray_candidates:
            target_gray = min(count, len(gray_candidates))
            target_color = count - target_gray
        elif prefer_class == "COLOR" and color_candidates:
            target_color = min(count, len(color_candidates))
            target_gray = count - target_color
        
        # Select from each class
        selected_gray = min(target_gray, len(gray_candidates))
        selected_color = min(target_color, len(color_candidates))
        
        # If we need more, fill from the other class
        remaining = count - selected_gray - selected_color
        if remaining > 0:
            if len(gray_candidates) > selected_gray:
                selected_gray = min(selected_gray + remaining, len(gray_candidates))
            elif len(color_candidates) > selected_color:
                selected_color = min(selected_color + remaining, len(color_candidates))
        
        # Actually select the images
        for classified in gray_candidates[:selected_gray]:
            add_if_not_used(classified)
        
        for classified in color_candidates[:selected_color]:
            add_if_not_used(classified)
    
    # 1. Select from compressed group (20, smallest files)
    # Sort by size (ascending) to get smallest files
    compressed_sorted = sorted(compressed_images, key=lambda c: c.image_info.size_bytes)
    select_with_diversity(compressed_sorted, target_compressed)
    
    # 2. Select from unoptimized group (30, largest files)
    # Sort by size (descending) to get largest files
    unoptimized_sorted = sorted(unoptimized_images, key=lambda c: c.image_info.size_bytes, reverse=True)
    select_with_diversity(unoptimized_sorted, target_unoptimized)
    
    # 3. Select from QC/EQUIPMENT hints (10), or COLOR class if hints unavailable
    if qc_hint_images:
        # Use QC hints, ensuring diversity
        qc_sorted = sorted(qc_hint_images, key=lambda c: c.image_info.size_bytes)
        select_with_diversity(qc_sorted, target_qc_hints)
    else:
        # Fallback: select from COLOR class
        color_candidates = [c for c in classified_list if c.color_class == "COLOR" and c.image_info.path not in used_paths]
        color_sorted = sorted(color_candidates, key=lambda c: c.image_info.size_bytes)
        # Still ensure some diversity (prefer COLOR but allow GRAY if needed)
        select_with_diversity(color_sorted, target_qc_hints, prefer_class="COLOR")
    
    # If we still need more samples to reach n, fill from remaining images
    remaining_needed = n - len(selected)
    if remaining_needed > 0:
        all_remaining = [
            c for c in classified_list 
            if c.image_info.path not in used_paths
        ]
        # Sort by size to get a mix
        all_remaining_sorted = sorted(all_remaining, key=lambda c: c.image_info.size_bytes)
        select_with_diversity(all_remaining_sorted, remaining_needed)
    
    return selected[:n]  # Ensure we don't exceed n


# =========================
# Step 3: Variant Matrix for Sampling
# =========================

def generate_variant_filename(
    original_path: Path,
    width: int,
    quality: int,
    color_class: str,
    variant_id: int
) -> str:
    """Generate variant filename according to naming convention.
    
    Format: <stem>__W{width}__Q{quality}__{GRAY|COLOR}__v{variant_id}.jpg
    
    Args:
        original_path: Path to original image
        width: Target width
        quality: JPEG quality
        color_class: "GRAY" or "COLOR"
        variant_id: Variant identifier (0-based)
        
    Returns:
        Filename string (without directory)
    """
    stem = original_path.stem
    return f"{stem}__W{width}__Q{quality}__{color_class}__v{variant_id}.jpg"


def compute_color_pixel_fraction(
    image_path: Path,
    max_side: int = 256,
    spread_threshold: int = 15,
) -> float:
    """Cheap 'is there real color?' metric.

    Returns fraction of pixels where (max(R,G,B) - min(R,G,B)) >= spread_threshold,
    computed on a downsampled RGB image.
    """
    try:
        with Image.open(image_path) as img:
            img_t = ImageOps.exif_transpose(img)
            img = img_t if img_t is not None else img
            img = img.convert("RGB")
            w, h = img.size
            if w <= 0 or h <= 0:
                return 0.0
            scale = max(w, h) / float(max_side)
            if scale > 1.0:
                new_w = max(1, int(round(w / scale)))
                new_h = max(1, int(round(h / scale)))
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            arr = np.asarray(img, dtype=np.int16)
            mx = arr.max(axis=2)
            mn = arr.min(axis=2)
            spread = mx - mn
            return float(np.mean(spread >= int(spread_threshold)))
    except Exception:
        return 0.0


def audit_possible_color_misclassifications(
    classified_list: List[ClassifiedImageInfo],
    threshold: float,
    max_candidates: int = 50,
    spread_threshold: int = 15,
    frac_threshold: float = 0.01,
) -> List[Dict[str, object]]:
    """Find images classified as GRAY but likely containing color.

    Heuristics (lightweight):
    - Near-threshold GRAY: chroma_score in [0.9*threshold, threshold)
    - Color-pixel fraction: fraction of pixels with channel spread >= spread_threshold exceeds frac_threshold
    """
    candidates: List[Dict[str, object]] = []
    for c in classified_list:
        name = c.image_info.path.name
        if _is_table_image_name(name):
            continue
        if c.color_class != "GRAY":
            continue
        near = float(c.chroma_score) >= float(threshold) * 0.90
        frac = compute_color_pixel_fraction(c.image_info.path, spread_threshold=spread_threshold)
        frac_flag = frac >= float(frac_threshold)
        if near or frac_flag:
            candidates.append(
                {
                    "path": str(c.image_info.path),
                    "filename": name,
                    "size_kb": float(c.image_info.size_bytes) / 1024.0,
                    "w": int(c.image_info.width),
                    "h": int(c.image_info.height),
                    "base_class": c.color_class,
                    "chroma_score": float(c.chroma_score),
                    "near_threshold": int(bool(near)),
                    "color_pixel_frac": float(frac),
                    "color_frac_flag": int(bool(frac_flag)),
                    "qc_equip_hint": int(bool(("qc" in name.lower()) or ("equip" in name.lower()))),
                }
            )
    # Sort: most suspicious first.
    candidates.sort(key=lambda r: (r["near_threshold"], r["color_pixel_frac"], r["chroma_score"]), reverse=True)
    return candidates[: int(max_candidates)]


def has_png_transparency(img: Image.Image) -> bool:
    """Detect whether a PNG-like image actually uses transparency."""
    try:
        if img.mode in ("RGBA", "LA"):
            alpha = img.getchannel("A")
            extrema = alpha.getextrema()
            if isinstance(extrema, tuple) and len(extrema) == 2 and isinstance(extrema[0], (int, float)):
                return float(extrema[0]) < 255.0
            return False
        if img.mode == "P" and ("transparency" in img.info):
            # Convert palette transparency to alpha and check.
            rgba = img.convert("RGBA")
            alpha = rgba.getchannel("A")
            extrema = alpha.getextrema()
            if isinstance(extrema, tuple) and len(extrema) == 2 and isinstance(extrema[0], (int, float)):
                return float(extrema[0]) < 255.0
            return False
        return False
    except Exception:
        # Conservative default: assume no transparency.
        return False


def apply_lossless_jpeg_optimization(input_path: Path, output_path: Path) -> bool:
    """Run lossless jpegtran optimization and write to output_path if it reduces size.

    Returns True iff output_path was written and is strictly smaller than input_path.
    """
    jpegtran = shutil.which("jpegtran")
    if not jpegtran:
        return False

    if input_path.suffix.lower() not in {".jpg", ".jpeg"}:
        return False

    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            jpegtran,
            "-copy",
            "none",
            "-optimize",
            "-outfile",
            str(tmp_path),
            str(input_path),
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if proc.returncode != 0 or (not tmp_path.exists()):
            try:
                tmp_path.unlink(missing_ok=True)  # py>=3.8
            except Exception:
                pass
            return False

        in_size = input_path.stat().st_size
        out_size = tmp_path.stat().st_size
        if out_size >= in_size:
            tmp_path.unlink(missing_ok=True)
            return False

        # Atomic-ish replace.
        if output_path.exists():
            output_path.unlink()
        tmp_path.replace(output_path)
        return True
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        return False


def _format_reduction(original_kb: float, output_kb: float) -> str:
    if original_kb <= 0:
        return "n/a"
    delta = original_kb - output_kb
    pct = (delta / original_kb) * 100.0
    return f"{delta:.1f}KB ({pct:.1f}%)"


def _deterministic_output_path(
    input_path: Path,
    input_dir: Path,
    out_dir: Path,
    output_ext: str,
    preserve_subdirs: bool,
    preserve_basename: bool = False,
) -> Path:
    """Map input_path to deterministic output path under out_dir.
    
    Args:
        input_path: Input file path
        input_dir: Input directory root
        out_dir: Output directory root
        output_ext: Output file extension (e.g., '.jpg')
        preserve_subdirs: Whether to preserve subdirectory structure
        preserve_basename: If True, preserve exact basename (including extension);
                          used in final mode per Image Asset Naming Convention
    
    Returns:
        Output file path
    """
    if preserve_basename:
        # Final mode: preserve exact basename (per Image Asset Naming Convention)
        if preserve_subdirs:
            rel = input_path.relative_to(input_dir)
            # Replace extension if needed, but keep same basename structure
            rel = rel.with_suffix(output_ext)
            return out_dir / rel
        else:
            # Flat: just change extension if different
            if output_ext.lower() != input_path.suffix.lower():
                return out_dir / f"{input_path.stem}{output_ext}"
            else:
                return out_dir / input_path.name
    
    # Original logic for sampling mode (variants with modified basenames)
    if preserve_subdirs:
        rel = input_path.relative_to(input_dir)
        rel = rel.with_suffix(output_ext)
        return out_dir / rel
    # Flat output: just filename stem with new extension.
    return out_dir / f"{input_path.stem}{output_ext}"


def optimize_image_final(
    image_info: ImageInfo,
    input_dir: Path,
    out_dir: Path,
    threshold: float,
    gray_width: int,
    gray_quality: int,
    gray_grayscale_encode: bool,
    color_width: int,
    color_quality: int,
    lossless_opt: bool,
    overwrite: bool,
    preserve_subdirs: bool,
) -> FinalManifestRow:
    """Optimize a single image for final mode, returning a manifest row (never raises)."""
    original_path = image_info.path
    original_rel = _safe_relpath(original_path, input_dir)
    original_ext = original_path.suffix.lower()

    # Default error-shaped row; filled in later.
    base_row = FinalManifestRow(
        status="ERROR",
        error="",
        original_path=original_path,
        output_path=Path(""),
        original_rel_path=original_rel,
        output_rel_path="",
        original_ext=original_ext,
        output_ext="",
        original_size_kb=image_info.size_bytes / 1024.0,
        output_size_kb=0.0,
        attempted_output_size_kb=0.0,
        attempted_output_ge_original=False,
        original_w=image_info.width,
        original_h=image_info.height,
        output_w=0,
        output_h=0,
        color_class="COLOR",
        chroma_score=0.0,
        width_target=0,
        quality=0,
        grayscale_encoded=False,
        action_taken="",
        fallback_used="none",
    )

    try:
        base_class, chroma_score = classify_color(original_path, threshold=threshold)
        color_class = pick_final_class(original_path, base_class, chroma_score, threshold)
        # Guardrail: promote likely-color images that were classified as GRAY near threshold.
        color_class, _color_frac = refine_color_class_with_color_fraction(
            image_path=original_path,
            base_class=color_class,
            chroma_score=chroma_score,
            threshold=threshold,
            near_factor=0.90,
            spread_threshold=15,
            frac_threshold=0.01,
        )
        base_row.color_class = color_class
        base_row.chroma_score = chroma_score

        if color_class == "GRAY":
            width_target = int(gray_width)
            quality = int(gray_quality)
            grayscale_encode = bool(gray_grayscale_encode)
            quality_floor = 85
        else:
            width_target = int(color_width)
            quality = int(color_quality)
            grayscale_encode = False
            quality_floor = 90

        base_row.width_target = width_target
        base_row.quality = quality

        # Decide output extension / container.
        output_ext: str
        wants_keep_png = False
        if original_ext == ".png":
            # Need to peek for transparency to decide keep PNG vs convert to JPEG.
            with Image.open(original_path) as _img0:
                _img0_t = ImageOps.exif_transpose(_img0)
                _img0_fixed = _img0_t if _img0_t is not None else _img0
                wants_keep_png = has_png_transparency(_img0_fixed)
            output_ext = ".png" if wants_keep_png else ".jpg"
        else:
            output_ext = ".jpg"

        # Final mode: preserve exact basename per Image Asset Naming Convention
        out_path = _deterministic_output_path(
            input_path=original_path,
            input_dir=input_dir,
            out_dir=out_dir,
            output_ext=output_ext,
            preserve_subdirs=preserve_subdirs,
            preserve_basename=True,  # CRITICAL: preserve basename in final mode
        )
        base_row.output_path = out_path
        base_row.output_rel_path = _safe_relpath(out_path, out_dir)
        base_row.output_ext = output_ext

        if out_path.exists() and (not overwrite):
            base_row.status = "SKIPPED"
            base_row.error = ""
            base_row.output_size_kb = out_path.stat().st_size / 1024.0
            base_row.attempted_output_size_kb = base_row.output_size_kb
            base_row.action_taken = "skipped_exists"
            return base_row

        out_path.parent.mkdir(parents=True, exist_ok=True)

        with Image.open(original_path) as img:
            img_t = ImageOps.exif_transpose(img)
            img = img_t if img_t is not None else img
            original_w, original_h = img.size
            base_row.original_w = original_w
            base_row.original_h = original_h

            original_size_bytes = image_info.size_bytes
            original_size_kb = original_size_bytes / 1024.0

            # Normalize image mode and handle PNG conversion.
            if output_ext == ".jpg":
                # JPEG path: flatten alpha if needed, ensure RGB/L.
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and ("transparency" in img.info)):
                    img = img.convert("RGBA")
                    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
                    img = Image.alpha_composite(bg, img).convert("RGB")
                elif img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
            else:
                # PNG path: keep alpha if present; convert paletted to RGBA for safety.
                if img.mode == "P":
                    img = img.convert("RGBA")

            # Resize decision: only if original larger than target; never upscale.
            resize_occurred = False
            output_w, output_h = original_w, original_h
            if original_w > width_target:
                aspect = original_h / float(original_w)
                new_h = int(width_target * aspect)
                img = img.resize((width_target, new_h), Image.Resampling.LANCZOS)
                resize_occurred = True
                output_w, output_h = width_target, new_h

            # Conditional re-encode policy for small JPEGs w/ no resize.
            original_is_small_jpeg = (
                (original_ext in {".jpg", ".jpeg"}) and (original_size_kb <= SMALL_JPEG_SKIP_REENCODE_KB)
            )
            needs_grayscale_conversion = (output_ext == ".jpg") and grayscale_encode and (color_class == "GRAY") and (img.mode != "L")
            if (not resize_occurred) and original_is_small_jpeg and (not needs_grayscale_conversion):
                # If requested quality is below a conservative floor, do not re-encode.
                if quality < quality_floor:
                    shutil.copy2(original_path, out_path)
                    base_row.status = "OK"
                    base_row.error = ""
                    base_row.output_w = output_w
                    base_row.output_h = output_h
                    base_row.grayscale_encoded = False
                    base_row.action_taken = "no_change"
                    base_row.output_size_kb = out_path.stat().st_size / 1024.0
                    base_row.attempted_output_size_kb = base_row.output_size_kb
                    base_row.attempted_output_ge_original = False
                    base_row.fallback_used = "none"
                    return base_row

            # Encode / save.
            attempted_output_kb = 0.0
            attempted_ge_original = False
            action_taken = "reencode" if resize_occurred else "reencode"

            if output_ext == ".png":
                # PNG save ignores quality; keep alpha.
                img.save(out_path, "PNG", optimize=True, compress_level=9)
                attempted_output_kb = out_path.stat().st_size / 1024.0
                attempted_ge_original = out_path.stat().st_size >= original_size_bytes
                action_taken = "resize_only" if resize_occurred else "no_change"
                fallback_used = "none"
                # If PNG got bigger, fallback to original PNG (copy).
                if attempted_ge_original:
                    out_path.unlink(missing_ok=True)
                    shutil.copy2(original_path, out_path)
                    fallback_used = "original"
                base_row.status = "OK"
                base_row.error = ""
                base_row.output_w = output_w
                base_row.output_h = output_h
                base_row.grayscale_encoded = False
                base_row.action_taken = action_taken
                base_row.fallback_used = fallback_used
                base_row.attempted_output_size_kb = attempted_output_kb
                base_row.attempted_output_ge_original = attempted_ge_original
                base_row.output_size_kb = out_path.stat().st_size / 1024.0
                return base_row

            # JPEG path: optional grayscale encode.
            grayscale_encoded = False
            if grayscale_encode and color_class == "GRAY":
                if img.mode != "L":
                    img = img.convert("L")
                grayscale_encoded = True
            else:
                if img.mode == "L":
                    img = img.convert("RGB")
                grayscale_encoded = False

            save_kwargs = {"quality": int(quality), "optimize": True}
            if grayscale_encoded:
                save_kwargs["subsampling"] = 0
            img.save(out_path, "JPEG", **save_kwargs)

            attempted_size_bytes = out_path.stat().st_size
            attempted_output_kb = attempted_size_bytes / 1024.0
            attempted_ge_original = attempted_size_bytes >= original_size_bytes

            fallback_used = "none"
            if attempted_ge_original:
                # Output is not smaller. Prefer lossless jpegtran (if enabled), otherwise copy original.
                out_path.unlink(missing_ok=True)
                if lossless_opt and apply_lossless_jpeg_optimization(original_path, out_path):
                    fallback_used = "lossless_opt"
                else:
                    shutil.copy2(original_path, out_path)
                    fallback_used = "original"

            # Determine action.
            if original_ext == ".png":
                action_taken = "converted_from_png"
            elif resize_occurred:
                action_taken = "reencode"
            else:
                action_taken = "reencode" if (not original_is_small_jpeg or needs_grayscale_conversion) else "no_change"

            base_row.status = "OK"
            base_row.error = ""
            base_row.output_w = output_w
            base_row.output_h = output_h
            base_row.grayscale_encoded = grayscale_encoded
            base_row.action_taken = action_taken
            base_row.fallback_used = fallback_used
            base_row.attempted_output_size_kb = attempted_output_kb
            base_row.attempted_output_ge_original = attempted_ge_original
            base_row.output_size_kb = out_path.stat().st_size / 1024.0
            return base_row

    except Exception as e:
        base_row.status = "ERROR"
        base_row.error = str(e)
        return base_row

def optimize_image_variant(
    classified_image: ClassifiedImageInfo,
    output_dir: Path,
    width_target: int,
    quality: int,
    grayscale_encode: bool,
    variant_id: int,
    overwrite: bool = False
) -> Optional[OptimizationResult]:
    """Generate a single optimization variant for an image.
    
    Applies resizing, quality adjustment, and optional grayscale encoding.
    Implements guardrails: no upscaling, conditional re-encoding.
    
    Args:
        classified_image: ClassifiedImageInfo with image metadata and color class
        output_dir: Directory to write output file
        width_target: Target width (will not upscale if original is smaller)
        quality: JPEG quality (1-100)
        grayscale_encode: If True, convert to grayscale JPEG (1-channel)
        variant_id: Variant identifier for filename
        overwrite: If False, skip if output already exists
        
    Returns:
        OptimizationResult if successful, None if skipped or failed
    """
    image_info = classified_image.image_info
    original_path = image_info.path
    color_class = classified_image.color_class
    
    # Generate output filename
    output_filename = generate_variant_filename(
        original_path, width_target, quality, color_class, variant_id
    )
    output_path = output_dir / output_filename
    
    # Check if output exists and overwrite flag
    if output_path.exists() and not overwrite:
        return None  # Skip existing files
    
    try:
        # Load original image
        with Image.open(original_path) as img:
            original_w, original_h = img.size
            original_size_bytes = image_info.size_bytes
            original_size_kb = original_size_bytes / 1024.0
            original_is_jpeg = original_path.suffix.lower() in {'.jpg', '.jpeg'}
            small_jpeg = original_is_jpeg and (original_size_kb <= SMALL_JPEG_SKIP_REENCODE_KB)
            
            # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
            if img.mode != 'RGB' and img.mode != 'L':
                # Handle PNG with transparency: convert to RGB with white background
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
                    img = background
                else:
                    img = img.convert('RGB')
            
            # Resize decision: only resize if original is larger than target
            # Never upscale
            if original_w > width_target:
                # Calculate new height maintaining aspect ratio
                aspect_ratio = original_h / original_w
                new_height = int(width_target * aspect_ratio)
                img = img.resize((width_target, new_height), Image.Resampling.LANCZOS)
                output_w, output_h = width_target, new_height
                resize_occurred = True
            else:
                # Keep original dimensions (no upscale)
                output_w, output_h = original_w, original_h
                resize_occurred = False

            # Guardrail: conditional re-encoding
            # If no resize happened and the original is already a small JPEG, skip re-encoding
            # unless we need an actual pixel-transform (e.g. grayscale conversion).
            needs_grayscale_conversion = (
                grayscale_encode and color_class == "GRAY" and img.mode != 'L'
            )
            needs_rgb_conversion = (not grayscale_encode) and (img.mode == 'L') and (color_class == "COLOR")
            if (not resize_occurred) and small_jpeg and (not needs_grayscale_conversion) and (not needs_rgb_conversion):
                output_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original_path, output_path)
                output_size_bytes = output_path.stat().st_size
                output_size_kb = output_size_bytes / 1024.0
                # Check for QC/EQUIPMENT hint in filename
                filename_lower = original_path.name.lower()
                qc_equip_hint = ('qc' in filename_lower) or ('equip' in filename_lower)
                
                return OptimizationResult(
                    original_path=original_path,
                    output_path=output_path,
                    original_size_kb=original_size_kb,
                    output_size_kb=output_size_kb,
                    attempted_output_size_kb=output_size_kb,
                    attempted_output_ge_original=False,
                    original_w=original_w,
                    original_h=original_h,
                    output_w=output_w,
                    output_h=output_h,
                    color_class=color_class,
                    width_target=width_target,
                    quality=quality,
                    grayscale_encoded=(img.mode == 'L'),
                    action_taken="no_change",
                    fallback_used="none",
                    chroma_score=classified_image.chroma_score,
                    qc_equip_hint=qc_equip_hint,
                )
            
            # Apply grayscale encoding if requested and image is classified as GRAY
            if grayscale_encode and color_class == "GRAY":
                # Convert to grayscale (L mode = 1-channel)
                if img.mode != 'L':
                    img = img.convert('L')
                grayscale_encoded = True
            else:
                # Ensure RGB mode for color images
                if img.mode == 'L':
                    img = img.convert('RGB')
                grayscale_encoded = False
            
            # Save with specified quality
            # For grayscale, use subsampling=0 (4:4:4 equivalent) for better text quality
            # For color, use default subsampling
            save_kwargs = {
                'quality': quality,
                'optimize': True
            }
            
            if grayscale_encoded:
                # Use subsampling=0 for grayscale (better for text)
                # Note: Pillow's subsampling parameter: 0 = 4:4:4, 1 = 4:2:2, 2 = 4:2:0
                save_kwargs['subsampling'] = 0
            
            # Save to output path
            img.save(output_path, 'JPEG', **save_kwargs)
            
            # Get output file size
            output_size_bytes = output_path.stat().st_size
            output_size_kb = output_size_bytes / 1024.0
            attempted_output_size_kb = output_size_kb
            attempted_output_ge_original = output_size_bytes >= original_size_bytes
            
            # Determine action taken
            if original_path.suffix.lower() == '.png':
                action_taken = "converted_from_png"
            elif resize_occurred:
                action_taken = "reencode"  # Resize implies re-encoding
            else:
                # No resize occurred - check if we re-encoded
                if output_size_bytes != original_size_bytes:
                    action_taken = "reencode"
                else:
                    action_taken = "no_change"
            
            # Check if output is larger than original (fallback logic)
            fallback_used = "none"
            if attempted_output_ge_original:
                # Output is not smaller - use original file instead
                output_path.unlink()  # Delete the larger output
                shutil.copy2(original_path, output_path)
                output_size_bytes = original_size_bytes
                output_size_kb = original_size_kb
                fallback_used = "original"
            
            # Check for QC/EQUIPMENT hint in filename
            filename_lower = original_path.name.lower()
            qc_equip_hint = ('qc' in filename_lower) or ('equip' in filename_lower)
            
            return OptimizationResult(
                original_path=original_path,
                output_path=output_path,
                original_size_kb=original_size_kb,
                output_size_kb=output_size_kb,
                attempted_output_size_kb=attempted_output_size_kb,
                attempted_output_ge_original=attempted_output_ge_original,
                original_w=original_w,
                original_h=original_h,
                output_w=output_w,
                output_h=output_h,
                color_class=color_class,
                width_target=width_target,
                quality=quality,
                grayscale_encoded=grayscale_encoded,
                action_taken=action_taken,
                fallback_used=fallback_used,
                chroma_score=classified_image.chroma_score,
                qc_equip_hint=qc_equip_hint,
            )
            
    except Exception as e:
        print(f"[ERROR] Failed to optimize {original_path}: {e}", file=sys.stderr)
        return None


def _p95(values: List[float]) -> float:
    """Compute a simple p95 (95th percentile) for a list of floats."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    p95_index = int(len(sorted_vals) * 0.95)
    if p95_index >= len(sorted_vals):
        p95_index = len(sorted_vals) - 1
    return float(sorted_vals[p95_index])


def write_sampling_summary_csv(results: List[OptimizationResult], csv_path: Path) -> None:
    """Write sampling summary CSV with required columns + flags.
    
    Required columns (plan):
    - original_path, original_size_kb, original_w, original_h
    - output_path, output_size_kb, output_w, output_h
    - class, width_target, quality, grayscale_encoded
    - action_taken, fallback_used
    
    Extra helpful columns:
    - attempted_output_size_kb, attempted_output_ge_original
    """
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "original_path",
        "original_size_kb",
        "original_w",
        "original_h",
        "output_path",
        "output_size_kb",
        "output_w",
        "output_h",
        "class",
        "width_target",
        "quality",
        "grayscale_encoded",
        "action_taken",
        "fallback_used",
        "attempted_output_size_kb",
        "attempted_output_ge_original",
        "chroma_score",
        "qc_equip_hint",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(
                {
                    "original_path": str(r.original_path),
                    "original_size_kb": f"{r.original_size_kb:.1f}",
                    "original_w": r.original_w,
                    "original_h": r.original_h,
                    "output_path": str(r.output_path),
                    "output_size_kb": f"{r.output_size_kb:.1f}",
                    "output_w": r.output_w,
                    "output_h": r.output_h,
                    "class": r.color_class,
                    "width_target": r.width_target,
                    "quality": r.quality,
                    "grayscale_encoded": int(bool(r.grayscale_encoded)),
                    "action_taken": r.action_taken,
                    "fallback_used": r.fallback_used,
                    "attempted_output_size_kb": f"{r.attempted_output_size_kb:.1f}",
                    "attempted_output_ge_original": int(bool(r.attempted_output_ge_original)),
                    "chroma_score": f"{r.chroma_score:.4f}",
                    "qc_equip_hint": int(bool(r.qc_equip_hint)),
                }
            )


def compute_per_variant_statistics(results: List[OptimizationResult]) -> Dict[str, Dict[str, float]]:
    """Compute per-variant statistics for sample outputs.
    
    Groups by (class, width_target, quality, grayscale_encoded).
    For each variant config, computes:
    - count
    - median_output_size_kb, p95_output_size_kb
    - median_output_over_original, p95_output_over_original
    - median_reduction_pct, p95_reduction_pct  (reduction = 1 - output/original)
    - attempted_ge_original_count  (flags where attempted output was >= original)
    """
    grouped_sizes: Dict[str, List[float]] = defaultdict(list)
    grouped_ratios: Dict[str, List[float]] = defaultdict(list)
    grouped_attempted_ge_original: Dict[str, int] = defaultdict(int)
    grouped_count: Dict[str, int] = defaultdict(int)

    for r in results:
        key = f"{r.color_class}|W{r.width_target}|Q{r.quality}|G{int(bool(r.grayscale_encoded))}"
        grouped_sizes[key].append(float(r.output_size_kb))
        ratio = float(r.output_size_kb) / float(r.original_size_kb) if r.original_size_kb > 0 else 0.0
        grouped_ratios[key].append(ratio)
        grouped_count[key] += 1
        if r.attempted_output_ge_original:
            grouped_attempted_ge_original[key] += 1

    stats: Dict[str, Dict[str, float]] = {}
    for key in sorted(grouped_count.keys()):
        sizes = grouped_sizes[key]
        ratios = grouped_ratios[key]
        median_size = float(statistics.median(sizes)) if sizes else 0.0
        p95_size = _p95(sizes)
        median_ratio = float(statistics.median(ratios)) if ratios else 0.0
        p95_ratio = _p95(ratios)
        stats[key] = {
            "count": float(grouped_count[key]),
            "median_output_size_kb": median_size,
            "p95_output_size_kb": p95_size,
            "median_output_over_original": median_ratio,
            "p95_output_over_original": p95_ratio,
            "median_reduction_pct": (1.0 - median_ratio) * 100.0,
            "p95_reduction_pct": (1.0 - p95_ratio) * 100.0,
            "attempted_ge_original_count": float(grouped_attempted_ge_original.get(key, 0)),
        }
    return stats


def print_per_variant_statistics(stats: Dict[str, Dict[str, float]]) -> None:
    """Pretty-print per-variant statistics."""
    if not stats:
        print("No variant statistics to report.")
        return
    print()
    print("=" * 60)
    print("Per-Variant Statistics (sample outputs)")
    print("=" * 60)
    for key, s in stats.items():
        print(f"- {key}")
        print(f"  Count: {int(s['count'])}")
        print(f"  Output size KB: median={s['median_output_size_kb']:.1f}, p95={s['p95_output_size_kb']:.1f}")
        print(
            f"  Output/Original: median={s['median_output_over_original']:.3f}, "
            f"p95={s['p95_output_over_original']:.3f}"
        )
        print(
            f"  Reduction %: median={s['median_reduction_pct']:.1f}%, "
            f"p95={s['p95_reduction_pct']:.1f}%"
        )
        attempted_ct = int(s.get("attempted_ge_original_count", 0))
        if attempted_ct > 0:
            print(f"  Flag: attempted_output_ge_original count={attempted_ct}")
    print("=" * 60)


def generate_variants_for_image(
    classified_image: ClassifiedImageInfo,
    output_dir: Path,
    overwrite: bool = False,
    gray_widths: Optional[List[int]] = None,
    gray_qualities: Optional[List[int]] = None,
    color_widths: Optional[List[int]] = None,
    color_qualities: Optional[List[int]] = None,
) -> List[OptimizationResult]:
    """Generate all variants for a single image based on its color class.
    
    GRAY images: widths [1200, 1400], qualities [75, 85], grayscale encoding
    COLOR images: widths [1600, 1800], qualities [80, 90], RGB encoding
    
    Args:
        classified_image: ClassifiedImageInfo with image metadata and color class
        output_dir: Directory to write output files
        overwrite: If False, skip existing files
        
    Returns:
        List of OptimizationResult objects (one per variant)
    """
    color_class = classified_image.color_class
    results: List[OptimizationResult] = []
    variant_id = 0
    
    if color_class == "GRAY":
        # GRAY candidates default
        widths = gray_widths or [1200, 1400]
        qualities = gray_qualities or [75, 85]
        grayscale_encode = True
    else:  # COLOR (including infographics)
        # COLOR candidates: default same widths as GRAY for Anki compatibility
        widths = color_widths or [1200, 1400]
        qualities = color_qualities or [80, 90]
        grayscale_encode = False
    
    # Generate all combinations
    for width in widths:
        for quality in qualities:
            result = optimize_image_variant(
                classified_image=classified_image,
                output_dir=output_dir,
                width_target=width,
                quality=quality,
                grayscale_encode=grayscale_encode,
                variant_id=variant_id,
                overwrite=overwrite
            )
            if result is not None:
                results.append(result)
            variant_id += 1
    
    return results


# =========================
# CLI Interface
# =========================

def cmd_sample(args: argparse.Namespace) -> None:
    """Run sample command: generate variants for selected images and write summary CSV."""
    input_dir = Path(args.input)
    n = int(args.n)
    overwrite = bool(args.overwrite)
    
    # Get output directory (auto-detect RUN_TAG if available)
    custom_out = args.out if hasattr(args, 'out') and args.out else None
    output_dir = get_output_dir(input_dir, mode='sample', custom_out=custom_out)

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: Input directory does not exist or is not a directory: {input_dir}")
        return

    # Print RUN_TAG info if detected
    run_tag = extract_run_tag(input_dir)
    if run_tag:
        print(f"[INFO] Detected RUN_TAG: {run_tag}")
        print(f"[INFO] Output directory: {output_dir} (same RUN_TAG level)")
    else:
        print(f"[INFO] RUN_TAG not detected from path structure")
        print(f"[INFO] Output directory: {output_dir}")
    
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Scanning images in: {input_dir}")
    image_info_list = inventory_images(input_dir)
    print_inventory_summary(image_info_list)

    print()
    print("Classifying images (GRAY vs COLOR)...")
    classified_list = classify_images(image_info_list, threshold=float(args.threshold))
    # Guardrail: if an image is near the chroma threshold but has non-trivial color pixel fraction,
    # treat it as COLOR to avoid accidental grayscale encoding in sampling variants.
    refine_classified_list_inplace(
        classified_list,
        threshold=float(args.threshold),
        near_factor=0.90,
        spread_threshold=int(getattr(args, "audit_spread", 15)),
        frac_threshold=float(getattr(args, "audit_frac", 0.01)),
    )
    print_color_classification_summary(classified_list)

    # Optional audit: find likely COLOR misclassified as GRAY (one-time check)
    if int(getattr(args, "audit_misclass", 1)) == 1:
        print()
        print("Auditing possible COLOR→GRAY misclassifications (lightweight)...")
        suspects = audit_possible_color_misclassifications(
            classified_list,
            threshold=float(args.threshold),
            max_candidates=int(getattr(args, "audit_top", 50)),
            spread_threshold=int(getattr(args, "audit_spread", 15)),
            frac_threshold=float(getattr(args, "audit_frac", 0.01)),
        )
        if not suspects:
            print("[INFO] No suspicious COLOR→GRAY candidates found by heuristic.")
        else:
            audit_csv = output_dir / "audit_color_misclass_candidates.csv"
            audit_csv.parent.mkdir(parents=True, exist_ok=True)
            with audit_csv.open("w", newline="", encoding="utf-8") as f:
                fieldnames = list(suspects[0].keys())
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader()
                for r in suspects:
                    w.writerow(r)
            print(f"[INFO] Wrote audit candidates CSV: {audit_csv}")
            print("[INFO] Top suspicious candidates (first 10):")
            for r in suspects[:10]:
                print(
                    f"  - {r['filename']} | chroma={r['chroma_score']:.4f} | "
                    f"color_frac={r['color_pixel_frac']:.4f} | size={r['size_kb']:.1f}KB"
                )

    print()
    print(f"Selecting {n} samples...")
    selected = select_samples(classified_list, n=n)
    print(f"Selected {len(selected)} images for sampling.")

    # Print selected images with classification info
    print("\nSelected images for sampling:")
    print("=" * 80)
    for idx, classified in enumerate(selected, start=1):
        filename_lower = classified.image_info.path.name.lower()
        qc_equip_hint = ('qc' in filename_lower) or ('equip' in filename_lower)
        hint_marker = " [QC/EQUIP]" if qc_equip_hint else ""
        print(f"  [{idx:2d}] {classified.image_info.path.name}")
        print(f"       Class: {classified.color_class}, Chroma: {classified.chroma_score:.4f}{hint_marker}")
    print("=" * 80)
    print()
    
    # Parse optional sampling variant overrides (e.g., try width=900)
    gray_widths = _parse_csv_int_list(getattr(args, "gray_widths", None))
    gray_qualities = _parse_csv_int_list(getattr(args, "gray_qualities", None))
    color_widths = _parse_csv_int_list(getattr(args, "color_widths", None))
    color_qualities = _parse_csv_int_list(getattr(args, "color_qualities", None))

    results: List[OptimizationResult] = []
    for idx, classified in enumerate(selected, start=1):
        print(f"[{idx}/{len(selected)}] Generating variants for {classified.image_info.path.name} ({classified.color_class})")
        results.extend(
            generate_variants_for_image(
                classified,
                output_dir=output_dir,
                overwrite=overwrite,
                gray_widths=gray_widths,
                gray_qualities=gray_qualities,
                color_widths=color_widths,
                color_qualities=color_qualities,
            )
        )

    if not results:
        print("No variants generated (all outputs existed and --overwrite not set?).")
        return

    summary_csv_path = output_dir / "summary.csv"
    write_sampling_summary_csv(results, summary_csv_path)
    print()
    print(f"Wrote sampling summary CSV: {summary_csv_path}")

    stats = compute_per_variant_statistics(results)
    print_per_variant_statistics(stats)


def cmd_audit(args: argparse.Namespace) -> None:
    """Run audit command: report likely COLOR→GRAY misclassifications."""
    input_dir = Path(args.input)
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: Input directory does not exist or is not a directory: {input_dir}")
        return

    custom_out = args.out if hasattr(args, "out") and args.out else None
    output_dir = get_output_dir(input_dir, mode="sample", custom_out=custom_out)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Scanning images in: {input_dir}")
    image_info_list = inventory_images(input_dir)
    print_inventory_summary(image_info_list)

    print()
    print("Classifying images (GRAY vs COLOR)...")
    classified_list = classify_images(image_info_list, threshold=float(args.threshold))
    print_color_classification_summary(classified_list)

    print()
    print("Auditing possible COLOR→GRAY misclassifications (lightweight)...")
    suspects = audit_possible_color_misclassifications(
        classified_list,
        threshold=float(args.threshold),
        max_candidates=int(args.audit_top),
        spread_threshold=int(args.audit_spread),
        frac_threshold=float(args.audit_frac),
    )
    if not suspects:
        print("[INFO] No suspicious COLOR→GRAY candidates found by heuristic.")
        return

    audit_csv = output_dir / "audit_color_misclass_candidates.csv"
    with audit_csv.open("w", newline="", encoding="utf-8") as f:
        fieldnames = list(suspects[0].keys())
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in suspects:
            w.writerow(r)
    print(f"[INFO] Wrote audit candidates CSV: {audit_csv}")
    print("[INFO] Top suspicious candidates (first 20):")
    for r in suspects[:20]:
        print(
            f"  - {r['filename']} | chroma={r['chroma_score']:.4f} | "
            f"color_frac={r['color_pixel_frac']:.4f} | size={r['size_kb']:.1f}KB"
        )

    # Optional: copy originals into a convenient folder for manual inspection.
    if int(getattr(args, "copy_originals", 0)) == 1:
        subdir = str(getattr(args, "copy_dir", "audit_candidates_originals")).strip() or "audit_candidates_originals"
        copy_dir = output_dir / subdir
        copy_dir.mkdir(parents=True, exist_ok=True)
        overwrite = bool(int(getattr(args, "copy_overwrite", 0)))
        copied = skipped = failed = 0
        print(f"[INFO] Copying candidate originals into: {copy_dir} (overwrite={int(overwrite)})")
        for r in suspects:
            try:
                src = Path(str(r["path"]))
                dst = copy_dir / src.name
                if dst.exists() and not overwrite:
                    skipped += 1
                    continue
                shutil.copy2(src, dst)
                copied += 1
            except Exception as e:
                failed += 1
                print(f"[WARNING] Failed to copy {r.get('filename')}: {e}", file=sys.stderr)
        print(f"[INFO] Copy done. copied={copied}, skipped={skipped}, failed={failed}")


def cmd_inventory(args: argparse.Namespace) -> None:
    """Run inventory command."""
    input_dir = Path(args.input)
    
    if not input_dir.exists():
        print(f"Error: Input directory does not exist: {input_dir}")
        return
    
    if not input_dir.is_dir():
        print(f"Error: Input path is not a directory: {input_dir}")
        return
    
    print(f"Scanning images in: {input_dir}")
    print()
    
    image_info_list = inventory_images(input_dir)
    print_inventory_summary(image_info_list)


def write_final_manifest_csv(rows: List[FinalManifestRow], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "status",
        "error",
        "original_rel_path",
        "output_rel_path",
        "original_path",
        "output_path",
        "original_ext",
        "output_ext",
        "original_size_kb",
        "output_size_kb",
        "attempted_output_size_kb",
        "attempted_output_ge_original",
        "original_w",
        "original_h",
        "output_w",
        "output_h",
        "class",
        "chroma_score",
        "width_target",
        "quality",
        "grayscale_encoded",
        "action_taken",
        "fallback_used",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(
                {
                    "status": r.status,
                    "error": r.error,
                    "original_rel_path": r.original_rel_path,
                    "output_rel_path": r.output_rel_path,
                    "original_path": str(r.original_path),
                    "output_path": str(r.output_path),
                    "original_ext": r.original_ext,
                    "output_ext": r.output_ext,
                    "original_size_kb": f"{r.original_size_kb:.1f}",
                    "output_size_kb": f"{r.output_size_kb:.1f}",
                    "attempted_output_size_kb": f"{r.attempted_output_size_kb:.1f}",
                    "attempted_output_ge_original": int(bool(r.attempted_output_ge_original)),
                    "original_w": r.original_w,
                    "original_h": r.original_h,
                    "output_w": r.output_w,
                    "output_h": r.output_h,
                    "class": r.color_class,
                    "chroma_score": f"{r.chroma_score:.4f}",
                    "width_target": r.width_target,
                    "quality": r.quality,
                    "grayscale_encoded": int(bool(r.grayscale_encoded)),
                    "action_taken": r.action_taken,
                    "fallback_used": r.fallback_used,
                }
            )


def cmd_final(args: argparse.Namespace) -> None:
    input_dir = Path(args.input)
    overwrite = bool(args.overwrite)
    threshold = float(args.threshold)

    gray_width = int(args.gray_width)
    gray_quality = int(args.gray_quality)
    gray_grayscale_encode = bool(int(args.gray_grayscale_encode))

    # COLOR width defaults to GRAY width if not specified (for Anki compatibility)
    color_width = int(args.color_width) if args.color_width is not None else gray_width
    color_quality = int(args.color_quality)

    lossless_opt = bool(int(args.lossless_opt))
    
    # Get output directory (auto-detect RUN_TAG if available)
    custom_out = args.out if hasattr(args, 'out') and args.out else None
    out_dir = get_output_dir(input_dir, mode='final', custom_out=custom_out)

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: Input directory does not exist or is not a directory: {input_dir}")
        return

    # Print RUN_TAG info if detected
    run_tag = extract_run_tag(input_dir)
    if run_tag:
        print(f"[INFO] Detected RUN_TAG: {run_tag}")
        print(f"[INFO] Output directory: {out_dir} (same RUN_TAG level)")
        print(f"[INFO] Basename preservation: ENABLED (per Image Asset Naming Convention)")
    else:
        print(f"[INFO] RUN_TAG not detected from path structure")
        print(f"[INFO] Output directory: {out_dir}")
        print(f"[INFO] Basename preservation: ENABLED (per Image Asset Naming Convention)")
    
    # Print optimization settings
    print(f"[INFO] GRAY settings: width={gray_width}, quality={gray_quality}, grayscale_encode={gray_grayscale_encode}")
    print(f"[INFO] COLOR settings: width={color_width}, quality={color_quality}")
    if color_width == gray_width:
        print(f"[INFO] COLOR width matches GRAY width (Anki-compatible for infographics)")
    
    out_dir.mkdir(parents=True, exist_ok=True)

    image_info_list = inventory_images(input_dir)
    if not image_info_list:
        print("No images found.")
        return
    
    # Filter out TABLE images if needed (will be processed separately later)
    original_count = len(image_info_list)
    image_info_list = [img for img in image_info_list if '__TABLE' not in img.path.name]
    table_count = original_count - len(image_info_list)
    if table_count > 0:
        print(f"[INFO] Excluded {table_count} TABLE images from processing (will be processed separately)")
    
    if not image_info_list:
        print("No non-TABLE images found.")
        return

    preserve_subdirs = _has_subdirs(image_info_list, input_dir)

    rows: List[FinalManifestRow] = []
    ok = skipped = err = 0

    for info in tqdm(image_info_list, desc="Optimizing (final)", unit="img"):
        row = optimize_image_final(
            image_info=info,
            input_dir=input_dir,
            out_dir=out_dir,
            threshold=threshold,
            gray_width=gray_width,
            gray_quality=gray_quality,
            gray_grayscale_encode=gray_grayscale_encode,
            color_width=color_width,
            color_quality=color_quality,
            lossless_opt=lossless_opt,
            overwrite=overwrite,
            preserve_subdirs=preserve_subdirs,
        )
        rows.append(row)

        # Structured one-line logging.
        if row.status == "OK":
            ok += 1
            print(
                f"[INFO] {row.action_taken} {row.original_rel_path} → {row.output_rel_path} "
                f"({_format_reduction(row.original_size_kb, row.output_size_kb)}), "
                f"class={row.color_class}, W={row.width_target}, Q={row.quality}, fallback={row.fallback_used}"
            )
        elif row.status == "SKIPPED":
            skipped += 1
            print(f"[INFO] skipped {row.original_rel_path} → {row.output_rel_path} (exists)")
        else:
            err += 1
            print(f"[ERROR] failed {row.original_rel_path}: {row.error}", file=sys.stderr)

    manifest_path = out_dir / "manifest.csv"
    write_final_manifest_csv(rows, manifest_path)
    print()
    print(f"Wrote final manifest: {manifest_path}")
    print(f"Done. OK={ok}, SKIPPED={skipped}, ERROR={err}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Optimize images for Anki",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Inventory command
    inv_parser = subparsers.add_parser('inventory', help='Scan and inventory images')
    inv_parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Input directory containing images'
    )
    
    # Sample command
    sample_parser = subparsers.add_parser('sample', help='Generate sample variants + summary.csv')
    sample_parser.add_argument('--input', type=str, required=True, help='Input directory containing images (should be {RUN_TAG}/images/)')
    sample_parser.add_argument(
        '--out', 
        type=str, 
        default=None,
        help='Output directory name (relative to RUN_TAG dir, default: images_sample). If RUN_TAG not detected, relative to input parent.'
    )
    sample_parser.add_argument('--n', type=int, default=60, help='Number of images to sample (default: 60)')
    sample_parser.add_argument('--threshold', type=float, default=0.15, help='Chroma threshold for COLOR vs GRAY')
    sample_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing outputs')
    sample_parser.add_argument('--gray_widths', type=str, default=None, help='Override GRAY sample widths, comma-separated (e.g., 900,1200)')
    sample_parser.add_argument('--gray_qualities', type=str, default=None, help='Override GRAY sample qualities, comma-separated (e.g., 75)')
    sample_parser.add_argument('--color_widths', type=str, default=None, help='Override COLOR sample widths, comma-separated (e.g., 900,1200)')
    sample_parser.add_argument('--color_qualities', type=str, default=None, help='Override COLOR sample qualities, comma-separated (e.g., 80)')
    sample_parser.add_argument('--audit_misclass', type=int, default=1, help='1 to run COLOR→GRAY misclass audit in sample mode, 0 to skip (default: 1)')
    sample_parser.add_argument('--audit_top', type=int, default=50, help='Max audit candidates to write/print (default: 50)')
    sample_parser.add_argument('--audit_spread', type=int, default=15, help='Audit spread threshold for color pixel detection (default: 15)')
    sample_parser.add_argument('--audit_frac', type=float, default=0.01, help='Audit fraction threshold for color pixel detection (default: 0.01)')

    # Audit command
    audit_parser = subparsers.add_parser('audit', help='Audit likely COLOR→GRAY misclassifications (writes CSV)')
    audit_parser.add_argument('--input', type=str, required=True, help='Input directory containing images (should be {RUN_TAG}/images/)')
    audit_parser.add_argument(
        '--out',
        type=str,
        default=None,
        help='Output directory name (relative to RUN_TAG dir, default: images_sample). If RUN_TAG not detected, relative to input parent.'
    )
    audit_parser.add_argument('--threshold', type=float, default=0.15, help='Chroma threshold for COLOR vs GRAY')
    audit_parser.add_argument('--audit_top', type=int, default=200, help='Max audit candidates to write/print (default: 200)')
    audit_parser.add_argument('--audit_spread', type=int, default=15, help='Audit spread threshold for color pixel detection (default: 15)')
    audit_parser.add_argument('--audit_frac', type=float, default=0.01, help='Audit fraction threshold for color pixel detection (default: 0.01)')
    audit_parser.add_argument('--copy_originals', type=int, default=0, help='1 to copy candidate originals into images_sample subfolder (default: 0)')
    audit_parser.add_argument('--copy_dir', type=str, default="audit_candidates_originals", help='Subfolder name under images_sample for copied originals')
    audit_parser.add_argument('--copy_overwrite', type=int, default=0, help='1 to overwrite already-copied originals (default: 0)')

    # Final command
    final_parser = subparsers.add_parser('final', help='Apply optimization to full dataset (writes manifest.csv). Preserves basename per Image Asset Naming Convention.')
    final_parser.add_argument('--input', type=str, required=True, help='Input directory containing images (should be {RUN_TAG}/images/)')
    final_parser.add_argument(
        '--out', 
        type=str, 
        default=None,
        help='Output directory name (relative to RUN_TAG dir, default: images_anki). If RUN_TAG not detected, relative to input parent. Basename will be preserved.'
    )
    final_parser.add_argument('--threshold', type=float, default=0.15, help='Chroma threshold for COLOR vs GRAY')
    final_parser.add_argument('--gray_width', type=int, required=True, help='Target width for GRAY images')
    final_parser.add_argument('--gray_quality', type=int, required=True, help='JPEG quality for GRAY images')
    final_parser.add_argument(
        '--gray_grayscale_encode',
        type=int,
        default=1,
        help='1 to encode GRAY images as grayscale JPEG, 0 to keep RGB (default: 1)',
    )
    final_parser.add_argument(
        '--color_width', 
        type=int, 
        default=None,
        help='Target width for COLOR images (including infographics). Defaults to --gray_width if not specified.'
    )
    final_parser.add_argument('--color_quality', type=int, required=True, help='JPEG quality for COLOR images')
    final_parser.add_argument(
        '--lossless_opt',
        type=int,
        default=0,
        help='1 to enable jpegtran lossless optimization fallback, 0 to disable (default: 0)',
    )
    final_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing outputs')
    
    args = parser.parse_args()
    
    if args.command == 'inventory':
        cmd_inventory(args)
    elif args.command == 'sample':
        cmd_sample(args)
    elif args.command == 'audit':
        cmd_audit(args)
    elif args.command == 'final':
        cmd_final(args)
    elif args.command is None:
        parser.print_help()
    else:
        print(f"Command '{args.command}' not yet implemented.")


if __name__ == '__main__':
    main()


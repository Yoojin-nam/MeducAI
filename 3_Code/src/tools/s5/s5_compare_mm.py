#!/usr/bin/env python3
"""
MeducAI S5 multimodal comparison (Text + Image): S5R0 (Before) vs S5R2 (After)

Professor-aligned rules implemented:
1) Replicates are NOT independent:
   - Aggregate within condition by group_id, using the MEAN across replicate run_tags.
   - Perform paired comparisons on aggregated group-level means.

2) Endpoints:
   - Prereg primary: S2_any_issue_rate_per_group
     - Definition: within-group % of S2 cards with issue_count >= 1
   - Key secondary: TA_bad_rate_per_group
     - Definition: within-group % of S2 cards with technical_accuracy < 1.0
   - Key secondary (image): IMG_any_issue_rate_per_group
     - Definition: within-group % of evaluated images (card images + table visual, if present) with issue_count >= 1
   - Additional endpoints are still computed for operational tracking (S1 issues, S2 issues_per_card, TA mean, clean/blocking rates, etc.)

3) Default inference (prereg-aligned):
   - diff = after - before per group (paired)
   - Summary: median(diff)
   - Test: Wilcoxon signed-rank (two-sided)
   - CI: bootstrap percentile CI for median(diff)

4) Reporting:
   - Median/mean summaries, Wilcoxon p-value, bootstrap CI, and a simple directionality flag ("higher is better" vs "lower is better")
   - Targeted issue reduction: per-code counts (text + image)

Outputs:
- Markdown report: summary__mm.md
- Paired long-form CSV: paired_long__mm.csv
- Group-level wide CSV: group_level__mm.csv

Dependency note:
- SciPy is OPTIONAL but strongly recommended for Shapiro-Wilk + exact p-values.
  If SciPy is unavailable, the script will:
    - default to Wilcoxon (normal approximation) and still compute bootstrap CI + effect sizes,
    - and explicitly annotate the limitation in the Markdown output.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import numpy as np  # type: ignore
    _NUMPY_AVAILABLE = True
except Exception:
    np = None  # type: ignore
    _NUMPY_AVAILABLE = False

try:
    from scipy import stats  # type: ignore
    _SCIPY_AVAILABLE = True
except Exception:
    stats = None  # type: ignore
    _SCIPY_AVAILABLE = False


TEXT_TARGETED_DEFAULT = [
    "KEYWORD_MISSING",
    "MISSING_CLINICAL_PEARL",
    "MISSING_EXAM_POINT",
    "DISTRACTOR_MISMATCH",
    "DISTRACTOR_EXPLANATION_MISMATCH",
    "VAGUE_QUESTION",
    "NOMENCLATURE_PRECISION",
    "CLINICAL_NUANCE_PEDIATRIC",
    "NUMERICAL_INCONSISTENCY",
    "GUIDELINE_UPDATE",
]

IMAGE_TARGETED_DEFAULT = [
    "modality_mismatch_text_hint",
    "modality_mismatch_image_actual",
    "modality_mismatch_text_image",
    "landmark_missing",
    "laterality_error",
    "unexpected_text",
    "diagnosis_mismatch",
    "key_finding_missing",
]


def _parse_iso(ts: str) -> Optional[datetime]:
    ts = (ts or "").strip()
    if not ts:
        return None
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _safe_get(d: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


def _dedupe_latest_by_group(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    best: Dict[str, Tuple[Optional[datetime], Dict[str, Any]]] = {}
    for r in rows:
        gid = str(r.get("group_id") or "").strip()
        if not gid:
            continue
        ts_str = str(r.get("validation_timestamp") or "")
        ts = _parse_iso(ts_str)
        cur = best.get(gid)
        if cur is None or (ts is not None and (cur[0] is None or ts > cur[0])):
            best[gid] = (ts, r)
    return [v[1] for v in best.values()]


def _count_issue_codes(issues: Any, code_set: Iterable[str]) -> Dict[str, int]:
    wanted = set(code_set)
    out = {c: 0 for c in wanted}
    if not isinstance(issues, list):
        return out
    for it in issues:
        if not isinstance(it, dict):
            continue
        code = str(it.get("issue_code") or "").strip()
        if code in wanted:
            out[code] += 1
    return out


def _merge_counts(a: Dict[str, int], b: Dict[str, int]) -> Dict[str, int]:
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0) + int(v)
    return out


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _sd(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def _rate(numer: int, denom: int) -> float:
    return float(numer) / float(denom) if denom else 0.0


def _median(xs: List[float]) -> float:
    if not xs:
        return 0.0
    ys = sorted(xs)
    n = len(ys)
    mid = n // 2
    if n % 2 == 1:
        return float(ys[mid])
    return 0.5 * (float(ys[mid - 1]) + float(ys[mid]))


@dataclass
class GroupMetrics:
    group_id: str

    # Core S1 endpoints
    s1_issues_per_group: float
    s1_blocking_rate: float  # 0/1 (group-level)

    # Core S2 endpoints (group-level)
    s2_issues_per_card: float
    s2_ta_mean: float
    # prereg endpoints
    s2_any_issue_rate_per_group: float  # cards with >=1 issue / total cards
    ta_bad_rate_per_group: float  # cards with technical_accuracy < 1.0 / total cards
    s2_blocking_rate: float  # blocking cards / total cards
    s2_clean_rate: float  # cards with 0 issues AND not blocking / total cards

    # Optional difficulty (group-level)
    s2_difficulty_mean: Optional[float]

    # Image endpoints (group-level)
    img_issues_per_image: float
    img_clean_rate: float  # images with 0 issues AND not blocking / total images
    img_blocking_rate: float
    img_any_issue_rate_per_group: float  # images with >=1 issue / total evaluated images


@dataclass
class GroupCodeCounts:
    """Per-group code counts (text issues and image issues)."""
    group_id: str
    text_counts: Dict[str, float]  # per-code (may be replicate-mean -> float)
    image_counts: Dict[str, float]


def compute_group_metrics(
    row: Dict[str, Any],
    *,
    text_targeted: List[str],
    image_targeted: List[str],
) -> GroupMetrics:
    gid = str(row.get("group_id") or "").strip()

    # ---------- S1 ----------
    s1 = _safe_get(row, ["s1_table_validation"], {}) or {}
    s1_issues = s1.get("issues", [])
    s1_issue_count = len(s1_issues) if isinstance(s1_issues, list) else 0
    s1_blocking = 1.0 if bool(s1.get("blocking_error", False)) else 0.0

    # ---------- S2 ----------
    s2 = _safe_get(row, ["s2_cards_validation"], {}) or {}
    s2_summary = _safe_get(s2, ["summary"], {}) or {}
    cards = _safe_get(s2, ["cards"], []) or []
    if not isinstance(cards, list):
        cards = []
    total_cards = int(s2_summary.get("total_cards", len(cards)) or len(cards))
    total_cards = max(0, total_cards)
    blocking_cards = int(s2_summary.get("blocking_errors", 0) or 0)

    # primary continuous
    s2_issue_count_total = 0
    s2_any_issue_cards = 0
    s2_ta_bad_cards = 0
    try:
        s2_ta_mean = float(s2_summary.get("mean_technical_accuracy", 0.0) or 0.0)
    except Exception:
        s2_ta_mean = 0.0

    clean_cards = 0
    diff_vals: List[float] = []
    text_target_counts = {c: 0 for c in text_targeted}

    # ---------- Images (card images + optional table visual) ----------
    img_total = 0
    img_issues_total = 0
    img_blocking_total = 0
    img_clean_total = 0
    img_any_issue_total = 0
    img_target_counts = {c: 0 for c in image_targeted}

    # table visual counts as 1 image if present
    table_visual = s1.get("table_visual_validation")
    if isinstance(table_visual, dict):
        img_total += 1
        v_issues = table_visual.get("issues", [])
        v_issue_count = len(v_issues) if isinstance(v_issues, list) else 0
        img_issues_total += v_issue_count
        if v_issue_count >= 1:
            img_any_issue_total += 1
        if bool(table_visual.get("blocking_error", False)):
            img_blocking_total += 1
        if v_issue_count == 0 and (not bool(table_visual.get("blocking_error", False))):
            img_clean_total += 1
        img_target_counts = _merge_counts(img_target_counts, _count_issue_codes(v_issues, image_targeted))

    for c in cards:
        if not isinstance(c, dict):
            continue
        issues = c.get("issues", [])
        issue_count = len(issues) if isinstance(issues, list) else 0
        s2_issue_count_total += issue_count
        if issue_count >= 1:
            s2_any_issue_cards += 1
        text_target_counts = _merge_counts(text_target_counts, _count_issue_codes(issues, text_targeted))

        # TA bad (prereg key secondary)
        try:
            ta = float(c.get("technical_accuracy", 1.0) or 1.0)
        except Exception:
            ta = 1.0
        if ta < 1.0:
            s2_ta_bad_cards += 1

        # clean = no issues and not blocking
        if (issue_count == 0) and (not bool(c.get("blocking_error", False))):
            clean_cards += 1

        # difficulty (optional)
        if "difficulty" in c:
            try:
                dv_raw = c.get("difficulty")
                if dv_raw is not None:
                    dv = float(dv_raw)
                    if dv in (0.0, 0.5, 1.0):
                        diff_vals.append(dv)
            except Exception:
                pass

        civ = c.get("card_image_validation")
        if isinstance(civ, dict):
            img_total += 1
            i_issues = civ.get("issues", [])
            i_issue_count = len(i_issues) if isinstance(i_issues, list) else 0
            img_issues_total += i_issue_count
            if i_issue_count >= 1:
                img_any_issue_total += 1
            if bool(civ.get("blocking_error", False)):
                img_blocking_total += 1
            if i_issue_count == 0 and (not bool(civ.get("blocking_error", False))):
                img_clean_total += 1
            img_target_counts = _merge_counts(img_target_counts, _count_issue_codes(i_issues, image_targeted))

    s2_issues_per_card = float(s2_issue_count_total) / float(total_cards) if total_cards else 0.0
    s2_any_issue_rate_per_group = float(s2_any_issue_cards) / float(total_cards) if total_cards else 0.0
    ta_bad_rate_per_group = float(s2_ta_bad_cards) / float(total_cards) if total_cards else 0.0
    s2_blocking_rate = float(blocking_cards) / float(total_cards) if total_cards else 0.0
    s2_clean_rate = float(clean_cards) / float(total_cards) if total_cards else 0.0
    s2_difficulty_mean = _mean(diff_vals) if diff_vals else None

    img_issues_per_image = float(img_issues_total) / float(img_total) if img_total else 0.0
    img_blocking_rate = float(img_blocking_total) / float(img_total) if img_total else 0.0
    img_clean_rate = float(img_clean_total) / float(img_total) if img_total else 0.0
    img_any_issue_rate_per_group = float(img_any_issue_total) / float(img_total) if img_total else 0.0

    return GroupMetrics(
        group_id=gid,
        s1_issues_per_group=float(s1_issue_count),
        s1_blocking_rate=s1_blocking,
        s2_issues_per_card=s2_issues_per_card,
        s2_ta_mean=s2_ta_mean,
        s2_any_issue_rate_per_group=s2_any_issue_rate_per_group,
        ta_bad_rate_per_group=ta_bad_rate_per_group,
        s2_blocking_rate=s2_blocking_rate,
        s2_clean_rate=s2_clean_rate,
        s2_difficulty_mean=s2_difficulty_mean,
        img_issues_per_image=img_issues_per_image,
        img_clean_rate=img_clean_rate,
        img_blocking_rate=img_blocking_rate,
        img_any_issue_rate_per_group=img_any_issue_rate_per_group,
    )


def compute_group_code_counts(
    row: Dict[str, Any],
    *,
    text_targeted: List[str],
    image_targeted: List[str],
) -> GroupCodeCounts:
    gid = str(row.get("group_id") or "").strip()
    text_counts = {c: 0.0 for c in text_targeted}
    image_counts = {c: 0.0 for c in image_targeted}

    # S1 issues (text)
    s1 = _safe_get(row, ["s1_table_validation"], {}) or {}
    s1_issues = s1.get("issues", [])
    text_counts = _merge_counts(text_counts, _count_issue_codes(s1_issues, text_targeted))  # type: ignore[arg-type]

    # S2 issues (text) + card images (image)
    s2 = _safe_get(row, ["s2_cards_validation"], {}) or {}
    cards = _safe_get(s2, ["cards"], []) or []
    if isinstance(cards, list):
        for c in cards:
            if not isinstance(c, dict):
                continue
            text_counts = _merge_counts(text_counts, _count_issue_codes(c.get("issues", []), text_targeted))  # type: ignore[arg-type]
            civ = c.get("card_image_validation")
            if isinstance(civ, dict):
                image_counts = _merge_counts(image_counts, _count_issue_codes(civ.get("issues", []), image_targeted))  # type: ignore[arg-type]

    # table visuals (image)
    tv = s1.get("table_visual_validation")
    if isinstance(tv, dict):
        image_counts = _merge_counts(image_counts, _count_issue_codes(tv.get("issues", []), image_targeted))  # type: ignore[arg-type]

    # Convert to float (replicate-mean friendly)
    text_counts_f = {k: float(v) for k, v in text_counts.items()}
    image_counts_f = {k: float(v) for k, v in image_counts.items()}
    return GroupCodeCounts(group_id=gid, text_counts=text_counts_f, image_counts=image_counts_f)


def _sanitize_name(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^A-Za-z0-9_\\-\\.]+", "_", s)
    return s[:120] if len(s) > 120 else s


def load_run_tag_group_metrics(
    *,
    base_dir: Path,
    run_tag: str,
    arm: str,
    text_targeted: List[str],
    image_targeted: List[str],
    keep_all: bool,
) -> Dict[str, GroupMetrics]:
    data_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    path = data_dir / f"s5_validation__arm{arm}.jsonl"
    if not path.exists():
        raise SystemExit(f"Input not found: {path}")
    rows = _read_jsonl(path)
    rows_use = rows if keep_all else _dedupe_latest_by_group(rows)
    out: Dict[str, GroupMetrics] = {}
    for r in rows_use:
        gid = str(r.get("group_id") or "").strip()
        if not gid:
            continue
        out[gid] = compute_group_metrics(r, text_targeted=text_targeted, image_targeted=image_targeted)
    return out


def load_run_tag_code_counts(
    *,
    base_dir: Path,
    run_tag: str,
    arm: str,
    text_targeted: List[str],
    image_targeted: List[str],
    keep_all: bool,
) -> Dict[str, GroupCodeCounts]:
    data_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    path = data_dir / f"s5_validation__arm{arm}.jsonl"
    if not path.exists():
        raise SystemExit(f"Input not found: {path}")
    rows = _read_jsonl(path)
    rows_use = rows if keep_all else _dedupe_latest_by_group(rows)
    out: Dict[str, GroupCodeCounts] = {}
    for r in rows_use:
        gid = str(r.get("group_id") or "").strip()
        if not gid:
            continue
        out[gid] = compute_group_code_counts(r, text_targeted=text_targeted, image_targeted=image_targeted)
    return out


def _write_csv(path: Path, header: List[str], rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


def _bootstrap_ci_mean_diff(diffs: List[float], *, n_boot: int = 10000, seed: int = 123) -> Tuple[float, float]:
    if len(diffs) == 0:
        return (0.0, 0.0)
    rng = random.Random(seed)
    boots: List[float] = []
    for _ in range(n_boot):
        sample = [diffs[rng.randrange(0, len(diffs))] for _ in range(len(diffs))]
        boots.append(_mean(sample))
    boots.sort()
    lo = boots[int(0.025 * (len(boots) - 1))]
    hi = boots[int(0.975 * (len(boots) - 1))]
    return (lo, hi)


def _bootstrap_ci_median_diff(diffs: List[float], *, n_boot: int = 10000, seed: int = 123) -> Tuple[float, float]:
    if len(diffs) == 0:
        return (0.0, 0.0)
    rng = random.Random(seed)
    boots: List[float] = []
    for _ in range(n_boot):
        sample = [diffs[rng.randrange(0, len(diffs))] for _ in range(len(diffs))]
        boots.append(_median(sample))
    boots.sort()
    lo = boots[int(0.025 * (len(boots) - 1))]
    hi = boots[int(0.975 * (len(boots) - 1))]
    return (lo, hi)


def _paired_ttest(diffs: List[float]) -> Tuple[float, float, float]:
    """
    Returns (t_stat, p_value_two_sided, cohen_dz).
    Requires SciPy for exact p-value; otherwise uses normal approximation when n>=30.
    """
    n = len(diffs)
    if n < 2:
        return (0.0, 1.0, 0.0)
    m = _mean(diffs)
    sd = _sd(diffs)
    dz = (m / sd) if sd > 0 else 0.0
    t_stat = (m / (sd / math.sqrt(n))) if sd > 0 else 0.0
    if _SCIPY_AVAILABLE and stats is not None:
        # two-sided p-value from t distribution
        p = 2.0 * float(stats.t.sf(abs(t_stat), df=n - 1))
        return (t_stat, p, dz)
    # fallback: normal approximation only when n is large
    if n >= 30:
        z = abs(t_stat)
        p = math.erfc(z / math.sqrt(2.0))
        return (t_stat, p, dz)
    # small n: refuse to pretend exact p-values without SciPy
    raise RuntimeError("Paired t-test p-value requires SciPy for n<30. Install scipy or use --force_wilcoxon.")


def _wilcoxon_signed_rank(diffs: List[float]) -> Tuple[float, float, float]:
    """
    Returns (W_stat, p_value_two_sided, rank_biserial_correlation).
    - If SciPy available: uses stats.wilcoxon for p-value.
    - Else: uses normal approximation for p-value (two-sided).
    Effect size: matched-pairs rank biserial correlation.
    """
    # remove zeros
    nonzero = [(i, d) for i, d in enumerate(diffs) if d != 0.0]
    if len(nonzero) == 0:
        return (0.0, 1.0, 0.0)
    vals = [d for _, d in nonzero]
    abs_vals = [abs(d) for d in vals]
    # rank abs diffs (average ranks for ties)
    order = sorted(range(len(abs_vals)), key=lambda i: abs_vals[i])
    ranks = [0.0] * len(abs_vals)
    i = 0
    r = 1
    while i < len(order):
        j = i
        while j < len(order) and abs_vals[order[j]] == abs_vals[order[i]]:
            j += 1
        avg_rank = (r + (r + (j - i) - 1)) / 2.0
        for k in range(i, j):
            ranks[order[k]] = avg_rank
        r += (j - i)
        i = j

    w_pos = sum(rank for rank, d in zip(ranks, vals) if d > 0)
    w_neg = sum(rank for rank, d in zip(ranks, vals) if d < 0)
    w_stat = min(w_pos, w_neg)  # conventional
    # rank biserial correlation
    denom = w_pos + w_neg
    rbc = (w_pos - w_neg) / denom if denom > 0 else 0.0

    if _SCIPY_AVAILABLE and stats is not None:
        res = stats.wilcoxon(vals, zero_method="wilcox", correction=False, alternative="two-sided", mode="auto")
        p = float(res.pvalue)
        return (float(res.statistic), p, float(rbc))

    # normal approximation for W (two-sided); adequate for n>=10-ish
    n = len(vals)
    mu = n * (n + 1) / 4.0
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24.0)
    z = (w_pos - mu) / sigma if sigma > 0 else 0.0
    p = math.erfc(abs(z) / math.sqrt(2.0))
    return (w_stat, p, float(rbc))


def main() -> None:
    ap = argparse.ArgumentParser(description="MeducAI S5 compare (multimodal)")
    ap.add_argument("--base_dir", required=True, type=str)
    ap.add_argument("--arm", required=True, type=str)
    # Support both --before_run_tag (repeatable) and --before_run_tags (multiple values at once)
    ap.add_argument("--before_run_tag", action="append", default=[], help="Repeatable: specify each run tag separately (e.g., --before_run_tag TAG1 --before_run_tag TAG2)")
    ap.add_argument("--before_run_tags", nargs="+", default=[], help="Specify multiple run tags at once (e.g., --before_run_tags TAG1 TAG2)")
    ap.add_argument("--after_run_tag", action="append", default=[], help="Repeatable: specify each run tag separately (e.g., --after_run_tag TAG1 --after_run_tag TAG2)")
    ap.add_argument("--after_run_tags", nargs="+", default=[], help="Specify multiple run tags at once (e.g., --after_run_tags TAG1 TAG2)")
    ap.add_argument("--out_dir", default=None, type=str, help="Override output directory")
    ap.add_argument("--keep_all", action="store_true", help="Do not dedupe by latest timestamp per group")
    ap.add_argument("--text_targeted", default=",".join(TEXT_TARGETED_DEFAULT), type=str)
    ap.add_argument("--image_targeted", default=",".join(IMAGE_TARGETED_DEFAULT), type=str)
    ap.add_argument("--force_wilcoxon", action="store_true", help="Skip Shapiro/t-test branching and always use Wilcoxon")
    ap.add_argument("--n_boot", type=int, default=10000, help="Bootstrap resamples for CI (default: 10000)")
    ap.add_argument("--seed", type=int, default=123, help="Seed for bootstrap (default: 123)")
    args = ap.parse_args()

    base_dir = Path(args.base_dir).resolve()
    arm = str(args.arm).strip().upper()
    
    # Combine --before_run_tag (append) and --before_run_tags (nargs="+")
    before_tags = []
    if args.before_run_tag:
        before_tags.extend([str(x).strip() for x in args.before_run_tag if str(x).strip()])
    if args.before_run_tags:
        before_tags.extend([str(x).strip() for x in args.before_run_tags if str(x).strip()])
    before_tags = [t for t in before_tags if t]  # Remove empty strings
    
    after_tags = []
    if args.after_run_tag:
        after_tags.extend([str(x).strip() for x in args.after_run_tag if str(x).strip()])
    if args.after_run_tags:
        after_tags.extend([str(x).strip() for x in args.after_run_tags if str(x).strip()])
    after_tags = [t for t in after_tags if t]  # Remove empty strings
    
    if not before_tags or not after_tags:
        raise SystemExit("Provide at least one --before_run_tag/--before_run_tags and one --after_run_tag/--after_run_tags")

    text_targeted = [x.strip() for x in str(args.text_targeted).split(",") if x.strip()]
    image_targeted = [x.strip() for x in str(args.image_targeted).split(",") if x.strip()]

    # Load per-run_tag group metrics + code counts
    before_by_tag: Dict[str, Dict[str, GroupMetrics]] = {}
    after_by_tag: Dict[str, Dict[str, GroupMetrics]] = {}
    before_codes_by_tag: Dict[str, Dict[str, GroupCodeCounts]] = {}
    after_codes_by_tag: Dict[str, Dict[str, GroupCodeCounts]] = {}
    for t in before_tags:
        before_by_tag[t] = load_run_tag_group_metrics(
            base_dir=base_dir,
            run_tag=t,
            arm=arm,
            text_targeted=text_targeted,
            image_targeted=image_targeted,
            keep_all=bool(args.keep_all),
        )
        before_codes_by_tag[t] = load_run_tag_code_counts(
            base_dir=base_dir,
            run_tag=t,
            arm=arm,
            text_targeted=text_targeted,
            image_targeted=image_targeted,
            keep_all=bool(args.keep_all),
        )
    for t in after_tags:
        after_by_tag[t] = load_run_tag_group_metrics(
            base_dir=base_dir,
            run_tag=t,
            arm=arm,
            text_targeted=text_targeted,
            image_targeted=image_targeted,
            keep_all=bool(args.keep_all),
        )
        after_codes_by_tag[t] = load_run_tag_code_counts(
            base_dir=base_dir,
            run_tag=t,
            arm=arm,
            text_targeted=text_targeted,
            image_targeted=image_targeted,
            keep_all=bool(args.keep_all),
        )

    # Determine common groups across all tags
    common = None
    for d in list(before_by_tag.values()) + list(after_by_tag.values()):
        gids = set(d.keys())
        common = gids if common is None else (common & gids)
    common_groups = sorted(common or [])
    if not common_groups:
        raise SystemExit("No common group_ids across provided run_tags")

    def agg_group(gid: str, pool: Dict[str, Dict[str, GroupMetrics]]) -> GroupMetrics:
        ms = [pool[tag][gid] for tag in pool.keys()]
        # difficulty mean: average of available means (skip None)
        diffs = [m.s2_difficulty_mean for m in ms if m.s2_difficulty_mean is not None]
        diff_mean = (sum(diffs) / len(diffs)) if diffs else None
        return GroupMetrics(
            group_id=gid,
            s1_issues_per_group=_mean([m.s1_issues_per_group for m in ms]),
            s1_blocking_rate=_mean([m.s1_blocking_rate for m in ms]),
            s2_issues_per_card=_mean([m.s2_issues_per_card for m in ms]),
            s2_ta_mean=_mean([m.s2_ta_mean for m in ms]),
            s2_any_issue_rate_per_group=_mean([m.s2_any_issue_rate_per_group for m in ms]),
            ta_bad_rate_per_group=_mean([m.ta_bad_rate_per_group for m in ms]),
            s2_blocking_rate=_mean([m.s2_blocking_rate for m in ms]),
            s2_clean_rate=_mean([m.s2_clean_rate for m in ms]),
            s2_difficulty_mean=diff_mean,
            img_issues_per_image=_mean([m.img_issues_per_image for m in ms]),
            img_clean_rate=_mean([m.img_clean_rate for m in ms]),
            img_blocking_rate=_mean([m.img_blocking_rate for m in ms]),
            img_any_issue_rate_per_group=_mean([m.img_any_issue_rate_per_group for m in ms]),
        )

    def agg_codes(gid: str, pool: Dict[str, Dict[str, GroupCodeCounts]]) -> GroupCodeCounts:
        reps = [pool[tag][gid] for tag in pool.keys()]
        txt = {c: 0.0 for c in text_targeted}
        img = {c: 0.0 for c in image_targeted}
        for rcc in reps:
            for c, v in rcc.text_counts.items():
                txt[c] = txt.get(c, 0.0) + float(v)
            for c, v in rcc.image_counts.items():
                img[c] = img.get(c, 0.0) + float(v)
        k = float(len(reps)) if reps else 1.0
        txt = {c: (txt.get(c, 0.0) / k) for c in txt.keys()}
        img = {c: (img.get(c, 0.0) / k) for c in img.keys()}
        return GroupCodeCounts(group_id=gid, text_counts=txt, image_counts=img)

    before_agg = {gid: agg_group(gid, before_by_tag) for gid in common_groups}
    after_agg = {gid: agg_group(gid, after_by_tag) for gid in common_groups}
    before_codes_agg = {gid: agg_codes(gid, before_codes_by_tag) for gid in common_groups}
    after_codes_agg = {gid: agg_codes(gid, after_codes_by_tag) for gid in common_groups}

    def _rep_vals(
        *,
        gid: str,
        attr: str,
        tags: List[str],
        pool_by_tag: Dict[str, Dict[str, GroupMetrics]],
    ) -> List[float]:
        vals: List[float] = []
        for t in tags:
            v = float(getattr(pool_by_tag[t][gid], attr))
            vals.append(v)
        return vals

    # Build group-level wide CSV
    group_rows: List[Dict[str, Any]] = []
    for gid in common_groups:
        b = before_agg[gid]
        a = after_agg[gid]
        row: Dict[str, Any] = {
            "group_id": gid,
            # Prereg endpoints (rates; reported as % in this wide CSV)
            "s2_any_issue_rate_per_group_before": round(100.0 * b.s2_any_issue_rate_per_group, 3),
            "s2_any_issue_rate_per_group_after": round(100.0 * a.s2_any_issue_rate_per_group, 3),
            "ta_bad_rate_per_group_before": round(100.0 * b.ta_bad_rate_per_group, 3),
            "ta_bad_rate_per_group_after": round(100.0 * a.ta_bad_rate_per_group, 3),
            "img_any_issue_rate_per_group_before": round(100.0 * b.img_any_issue_rate_per_group, 3),
            "img_any_issue_rate_per_group_after": round(100.0 * a.img_any_issue_rate_per_group, 3),
        }

        # Replicate stability (per-tag values + SD/min/max) for prereg endpoints
        for metric_name, attr in [
            ("s2_any_issue_rate_per_group", "s2_any_issue_rate_per_group"),
            ("ta_bad_rate_per_group", "ta_bad_rate_per_group"),
            ("img_any_issue_rate_per_group", "img_any_issue_rate_per_group"),
        ]:
            b_reps = _rep_vals(gid=gid, attr=attr, tags=before_tags, pool_by_tag=before_by_tag)
            a_reps = _rep_vals(gid=gid, attr=attr, tags=after_tags, pool_by_tag=after_by_tag)

            for t, v in zip(before_tags, b_reps):
                row[f"{metric_name}_before_rep__{_sanitize_name(t)}"] = round(100.0 * v, 3)
            for t, v in zip(after_tags, a_reps):
                row[f"{metric_name}_after_rep__{_sanitize_name(t)}"] = round(100.0 * v, 3)

            row[f"{metric_name}_before_rep_sd"] = round(100.0 * _sd(b_reps), 3) if len(b_reps) >= 2 else 0.0
            row[f"{metric_name}_after_rep_sd"] = round(100.0 * _sd(a_reps), 3) if len(a_reps) >= 2 else 0.0
            row[f"{metric_name}_before_rep_min"] = round(100.0 * min(b_reps), 3) if b_reps else 0.0
            row[f"{metric_name}_before_rep_max"] = round(100.0 * max(b_reps), 3) if b_reps else 0.0
            row[f"{metric_name}_after_rep_min"] = round(100.0 * min(a_reps), 3) if a_reps else 0.0
            row[f"{metric_name}_after_rep_max"] = round(100.0 * max(a_reps), 3) if a_reps else 0.0

        # Additional (non-prereg) endpoints
        row.update(
            {
                # Primary (continuous/rate)
                "s1_issues_per_group_before": round(b.s1_issues_per_group, 6),
                "s1_issues_per_group_after": round(a.s1_issues_per_group, 6),
                "s2_issues_per_card_before": round(b.s2_issues_per_card, 6),
                "s2_issues_per_card_after": round(a.s2_issues_per_card, 6),
                "s2_ta_mean_before": round(b.s2_ta_mean, 6),
                "s2_ta_mean_after": round(a.s2_ta_mean, 6),
                "img_issues_per_image_before": round(b.img_issues_per_image, 6),
                "img_issues_per_image_after": round(a.img_issues_per_image, 6),
                # Secondary (binary rates)
                "s1_blocking_rate_before": round(100.0 * b.s1_blocking_rate, 3),
                "s1_blocking_rate_after": round(100.0 * a.s1_blocking_rate, 3),
                "s2_clean_rate_before": round(100.0 * b.s2_clean_rate, 3),
                "s2_clean_rate_after": round(100.0 * a.s2_clean_rate, 3),
                "s2_blocking_rate_before": round(100.0 * b.s2_blocking_rate, 3),
                "s2_blocking_rate_after": round(100.0 * a.s2_blocking_rate, 3),
                "img_clean_rate_before": round(100.0 * b.img_clean_rate, 3),
                "img_clean_rate_after": round(100.0 * a.img_clean_rate, 3),
                "img_blocking_rate_before": round(100.0 * b.img_blocking_rate, 3),
                "img_blocking_rate_after": round(100.0 * a.img_blocking_rate, 3),
                "s2_difficulty_mean_before": "" if b.s2_difficulty_mean is None else round(b.s2_difficulty_mean, 6),
                "s2_difficulty_mean_after": "" if a.s2_difficulty_mean is None else round(a.s2_difficulty_mean, 6),
            }
        )
        group_rows.append(row)

    # Long-form paired CSV for external checking
    endpoints = [
        ("S2_any_issue_rate_per_group", "s2_any_issue_rate_per_group"),
        ("IMG_any_issue_rate_per_group", "img_any_issue_rate_per_group"),
        ("S2_issues_per_card_per_group", "s2_issues_per_card"),
        ("TA_bad_rate_per_group", "ta_bad_rate_per_group"),
        ("S1_issues_per_group", "s1_issues_per_group"),
        ("S2_TA_mean", "s2_ta_mean"),
        ("IMG_issues_per_image", "img_issues_per_image"),
        ("S2_clean_rate", "s2_clean_rate"),
        ("S2_blocking_rate", "s2_blocking_rate"),
        ("IMG_clean_rate", "img_clean_rate"),
        ("IMG_blocking_rate", "img_blocking_rate"),
        ("S1_blocking_rate", "s1_blocking_rate"),
    ]
    paired_long: List[Dict[str, Any]] = []
    for gid in common_groups:
        b = before_agg[gid]
        a = after_agg[gid]
        for name, attr in endpoints:
            bv = float(getattr(b, attr))
            av = float(getattr(a, attr))
            paired_long.append(
                {"group_id": gid, "endpoint": name, "before": bv, "after": av, "diff": av - bv}
            )

    # Difficulty (optional; only if present in at least one group in both conditions)
    diff_before = {gid: before_agg[gid].s2_difficulty_mean for gid in common_groups}
    diff_after = {gid: after_agg[gid].s2_difficulty_mean for gid in common_groups}
    diff_pairs: List[Tuple[str, float, float]] = []
    for gid in common_groups:
        bv0 = diff_before.get(gid)
        av0 = diff_after.get(gid)
        if bv0 is None or av0 is None:
            continue
        diff_pairs.append((gid, float(bv0), float(av0)))
    if len(diff_pairs) > 0:
        for gid, bv, av in diff_pairs:
            paired_long.append(
                {"group_id": gid, "endpoint": "S2_difficulty_mean", "before": bv, "after": av, "diff": av - bv}
            )

    # Output directory
    if args.out_dir:
        out_dir = Path(args.out_dir).resolve()
    else:
        name = f"COMPARE__{_sanitize_name(before_tags[0])}__VS__{_sanitize_name(after_tags[0])}"
        out_dir = base_dir / "2_Data" / "metadata" / "generated" / name
    out_dir.mkdir(parents=True, exist_ok=True)

    _write_csv(out_dir / "group_level__mm.csv", list(group_rows[0].keys()), group_rows)
    _write_csv(out_dir / "paired_long__mm.csv", ["group_id", "endpoint", "before", "after", "diff"], paired_long)

    # Targeted code tables (mean counts per group, then across groups)
    targeted_text_rows: List[Dict[str, Any]] = []
    targeted_img_rows: List[Dict[str, Any]] = []
    for code in text_targeted:
        before_vals = [before_codes_agg[gid].text_counts.get(code, 0.0) for gid in common_groups]
        after_vals = [after_codes_agg[gid].text_counts.get(code, 0.0) for gid in common_groups]
        targeted_text_rows.append(
            {"issue_code": code, "before_mean_per_group": _mean(before_vals), "after_mean_per_group": _mean(after_vals)}
        )
    for code in image_targeted:
        before_vals = [before_codes_agg[gid].image_counts.get(code, 0.0) for gid in common_groups]
        after_vals = [after_codes_agg[gid].image_counts.get(code, 0.0) for gid in common_groups]
        targeted_img_rows.append(
            {"issue_code": code, "before_mean_per_group": _mean(before_vals), "after_mean_per_group": _mean(after_vals)}
        )
    _write_csv(out_dir / "targeted_codes__text.csv", ["issue_code", "before_mean_per_group", "after_mean_per_group"], targeted_text_rows)
    _write_csv(out_dir / "targeted_codes__image.csv", ["issue_code", "before_mean_per_group", "after_mean_per_group"], targeted_img_rows)

    # ---------- Statistical reporting ----------
    @dataclass(frozen=True)
    class EndpointSpec:
        name: str
        attr: str
        better: str  # "lower" or "higher"
        tier: str  # "primary" | "key_secondary" | "secondary" | "exploratory"

    def _directionality_flag(diff_median: float, *, better: str) -> str:
        if better not in ("lower", "higher"):
            return ""
        if diff_median == 0.0:
            return "no_change"
        if better == "lower":
            return "improved" if diff_median < 0 else "worse"
        return "improved" if diff_median > 0 else "worse"

    def analyze_endpoint(spec: EndpointSpec, values_before: List[float], values_after: List[float]) -> Dict[str, Any]:
        diffs = [a - b for a, b in zip(values_after, values_before)]
        n = len(diffs)
        out: Dict[str, Any] = {
            "endpoint": spec.name,
            "tier": spec.tier,
            "n_groups": n,
            "better": spec.better,
            "before_mean": _mean(values_before),
            "before_sd": _sd(values_before),
            "after_mean": _mean(values_after),
            "after_sd": _sd(values_after),
            "diff_mean": _mean(diffs),
            "diff_sd": _sd(diffs),
            "before_median": _median(values_before),
            "after_median": _median(values_after),
            "diff_median": _median(diffs),
        }
        ci_m_lo, ci_m_hi = _bootstrap_ci_median_diff(diffs, n_boot=int(args.n_boot), seed=int(args.seed))
        out["diff_median_ci95_boot_lo"] = ci_m_lo
        out["diff_median_ci95_boot_hi"] = ci_m_hi
        ci_lo, ci_hi = _bootstrap_ci_mean_diff(diffs, n_boot=int(args.n_boot), seed=int(args.seed))
        out["diff_mean_ci95_boot_lo"] = ci_lo
        out["diff_mean_ci95_boot_hi"] = ci_hi

        # Prereg default test: Wilcoxon signed-rank (two-sided)
        w_stat, p, rbc = _wilcoxon_signed_rank(diffs)
        out.update({"test": "wilcoxon_signed_rank", "stat": w_stat, "p_value": p, "effect_size": rbc, "effect_size_name": "rank_biserial"})

        # Simple directionality flag based on median(diff)
        out["directionality"] = _directionality_flag(float(out["diff_median"]), better=spec.better)
        
        # Prereg directionality: 개선 그룹 수 / 전체 그룹 수
        # For "lower is better": improvement means After < Before (diff < 0)
        # For "higher is better": improvement means After > Before (diff > 0)
        if spec.better == "lower":
            improved_count = sum(1 for d in diffs if d < 0)
        elif spec.better == "higher":
            improved_count = sum(1 for d in diffs if d > 0)
        else:
            improved_count = 0
        out["improved_groups"] = improved_count
        out["total_groups"] = n
        out["improved_groups_ratio"] = float(improved_count) / float(n) if n > 0 else 0.0
        
        return out

    analyses: List[Dict[str, Any]] = []
    def collect(attr: str) -> Tuple[List[float], List[float]]:
        return ([float(getattr(before_agg[g], attr)) for g in common_groups], [float(getattr(after_agg[g], attr)) for g in common_groups])

    # Endpoint set (ordered; prereg primary/secondary first)
    endpoint_specs: List[EndpointSpec] = [
        EndpointSpec("S2_any_issue_rate_per_group", "s2_any_issue_rate_per_group", "lower", "primary"),
        EndpointSpec("IMG_any_issue_rate_per_group", "img_any_issue_rate_per_group", "lower", "key_secondary"),
        EndpointSpec("S2_issues_per_card_per_group", "s2_issues_per_card", "lower", "key_secondary"),
        EndpointSpec("TA_bad_rate_per_group", "ta_bad_rate_per_group", "lower", "key_secondary"),
        # Operational / legacy tracking
        EndpointSpec("S1_issues_per_group", "s1_issues_per_group", "lower", "secondary"),
        EndpointSpec("S2_technical_accuracy_mean", "s2_ta_mean", "higher", "secondary"),
        EndpointSpec("S2_is_clean_rate", "s2_clean_rate", "higher", "secondary"),
        EndpointSpec("S2_blocking_error_rate", "s2_blocking_rate", "lower", "secondary"),
        EndpointSpec("S1_blocking_error_rate", "s1_blocking_rate", "lower", "secondary"),
        EndpointSpec("IMG_issues_per_image", "img_issues_per_image", "lower", "exploratory"),
        EndpointSpec("IMG_is_clean_rate", "img_clean_rate", "higher", "exploratory"),
        EndpointSpec("IMG_blocking_error_rate", "img_blocking_rate", "lower", "exploratory"),
    ]
    for spec in endpoint_specs:
        bvals, avals = collect(spec.attr)
        analyses.append(analyze_endpoint(spec, bvals, avals))

    # Optional: difficulty mean if available
    if len(diff_pairs) >= 3:
        bvals = [b for _, b, _ in diff_pairs]
        avals = [a for _, _, a in diff_pairs]
        analyses.append(analyze_endpoint(EndpointSpec("S2_difficulty_mean", "_", "higher", "exploratory"), bvals, avals))

    _write_csv(
        out_dir / "stats_summary__mm.csv",
        [
            "endpoint",
            "tier",
            "n_groups",
            "better",
            "directionality",
            "improved_groups",
            "total_groups",
            "improved_groups_ratio",
            "before_median",
            "after_median",
            "diff_median",
            "diff_median_ci95_boot_lo",
            "diff_median_ci95_boot_hi",
            "test",
            "stat",
            "p_value",
            "effect_size_name",
            "effect_size",
            # additional (non-prereg) summaries for convenience
            "before_mean",
            "before_sd",
            "after_mean",
            "after_sd",
            "diff_mean",
            "diff_sd",
            "diff_mean_ci95_boot_lo",
            "diff_mean_ci95_boot_hi",
        ],
        analyses,
    )

    # Markdown report
    md: List[str] = []
    md.append("# S5R Prompt Improvement Experiment — Statistical Summary\n\n")
    md.append(f"- **Arm**: `{arm}`\n")
    md.append(f"- **Groups (paired)**: {len(common_groups)}\n")
    md.append(f"- **Before run_tags (replicates)**: {', '.join(f'`{t}`' for t in before_tags)}\n")
    md.append(f"- **After run_tags (replicates)**: {', '.join(f'`{t}`' for t in after_tags)}\n")
    md.append(f"- **Replicate handling**: per-group mean across replicates, then paired comparison\n")
    md.append(f"- **SciPy available**: {str(_SCIPY_AVAILABLE)}\n")
    if not _SCIPY_AVAILABLE:
        md.append("  - Note: Shapiro-Wilk and exact t-test/Wilcoxon p-values require SciPy. Using Wilcoxon normal approximation where needed.\n")
    md.append("\n## Outputs\n")
    md.append(f"- `{(out_dir / 'stats_summary__mm.csv').name}`\n")
    md.append(f"- `{(out_dir / 'group_level__mm.csv').name}`\n")
    md.append(f"- `{(out_dir / 'paired_long__mm.csv').name}`\n")
    md.append(f"- `{(out_dir / 'targeted_codes__text.csv').name}`\n")
    md.append(f"- `{(out_dir / 'targeted_codes__image.csv').name}`\n")

    # Replicate stability table (primary endpoint)
    md.append("\n## Replicate stability (per-group; prereg primary)\n")
    md.append("Primary endpoint: **S2_any_issue_rate_per_group** (values shown as %)\n\n")
    hdr_before = " / ".join(f"`{t}`" for t in before_tags)
    hdr_after = " / ".join(f"`{t}`" for t in after_tags)
    md.append(f"- **Before replicates**: {hdr_before}\n")
    md.append(f"- **After replicates**: {hdr_after}\n\n")
    md.append("| group_id | before_mean% | before_rep% (in order) | before_sd% | after_mean% | after_rep% (in order) | after_sd% |\n")
    md.append("|---|---:|---|---:|---:|---|---:|\n")
    for gid in common_groups:
        b_mean = 100.0 * float(before_agg[gid].s2_any_issue_rate_per_group)
        a_mean = 100.0 * float(after_agg[gid].s2_any_issue_rate_per_group)
        b_reps = [100.0 * v for v in _rep_vals(gid=gid, attr="s2_any_issue_rate_per_group", tags=before_tags, pool_by_tag=before_by_tag)]
        a_reps = [100.0 * v for v in _rep_vals(gid=gid, attr="s2_any_issue_rate_per_group", tags=after_tags, pool_by_tag=after_by_tag)]
        b_sd = 100.0 * _sd([v / 100.0 for v in b_reps]) if len(b_reps) >= 2 else 0.0
        a_sd = 100.0 * _sd([v / 100.0 for v in a_reps]) if len(a_reps) >= 2 else 0.0
        b_rep_str = ", ".join(f"{v:.3f}" for v in b_reps)
        a_rep_str = ", ".join(f"{v:.3f}" for v in a_reps)
        md.append(f"| `{gid}` | {b_mean:.3f} | {b_rep_str} | {b_sd:.3f} | {a_mean:.3f} | {a_rep_str} | {a_sd:.3f} |\n")

    md.append("\n## Endpoint results\n")
    md.append("| Endpoint | Tier | Better | n_groups | Before median | After median | Median diff | 95% CI (boot, median diff) | Test | p | Effect size | Direction | Improved groups |\n")
    md.append("|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|--:|\n")
    for a in analyses:
        improved_str = f"{a.get('improved_groups', 0)}/{a.get('total_groups', a['n_groups'])}"
        md.append(
            f"| {a['endpoint']} | {a.get('tier','')} | {a.get('better','')} | {a['n_groups']} | {float(a['before_median']):.4f} | {float(a['after_median']):.4f} | {float(a['diff_median']):.4f} | [{float(a['diff_median_ci95_boot_lo']):.4f}, {float(a['diff_median_ci95_boot_hi']):.4f}] | {a['test']} | {float(a['p_value']):.4g} | {a['effect_size_name']}={float(a['effect_size']):.4f} | {a.get('directionality','')} | {improved_str} |\n"
        )

    md.append("\n## Targeted issue codes (mean count per group)\n")
    md.append("\n### Text targeted\n")
    md.append("| issue_code | before_mean_per_group | after_mean_per_group |\n")
    md.append("|---|---:|---:|\n")
    for r in targeted_text_rows:
        md.append(f"| {r['issue_code']} | {float(r['before_mean_per_group']):.4f} | {float(r['after_mean_per_group']):.4f} |\n")
    md.append("\n### Image targeted\n")
    md.append("| issue_code | before_mean_per_group | after_mean_per_group |\n")
    md.append("|---|---:|---:|\n")
    for r in targeted_img_rows:
        md.append(f"| {r['issue_code']} | {float(r['before_mean_per_group']):.4f} | {float(r['after_mean_per_group']):.4f} |\n")

    md.append("\n## Notes / Caveats\n")
    md.append("- Default inference is prereg-aligned: median(diff) + Wilcoxon + bootstrap CI (median diff).\n")
    md.append("- Replicates are averaged within condition (per group) before paired inference.\n")
    md.append("- Without SciPy, Wilcoxon p-values use a normal approximation (still reports bootstrap CI).\n")

    (out_dir / "summary__mm.md").write_text("".join(md), encoding="utf-8")

    print(f"✓ Wrote compare outputs: {out_dir}")


if __name__ == "__main__":
    main()



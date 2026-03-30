# Entity Quota Distribution Policy (v1.0, Canonical)

**Status:** Canonical (Frozen once FINAL generation begins)  
**Applies to:** FINAL (group_target_cards q_i → cards_for_entity_exact)  
**Does NOT apply to:** S0 fixed payload (12 cards/set, representative entity only) :contentReference[oaicite:2]{index=2}  
**Single Authority:** Code determines N; S2 executes exactly N cards and nothing more. :contentReference[oaicite:3]{index=3}

## 🚫 Explicit Exclusion: Step S0 (Hard Rule)

This policy is **never invoked in Step S0**.

In Step S0:
- There is **no entity quota distribution**.
- Only a single representative entity is selected.
- The card count is fixed at the set level (`q = 12`) with **no per-entity expansion**.
- S0 allocation behavior is defined exclusively in
  `S0_Allocation_Artifact_Spec.md`.

Any interpretation that applies entity-level quota distribution to S0
is a **policy violation**.

---

## 0. Non-negotiable principle

> S2 never decides card counts.  
> For each entity, code provides `cards_for_entity_exact = N` and S2 must output exactly N cards.

Violation → hard fail.

---

## 1. Inputs

### 1.1 Group quota (binding)
- Source: Allocation output `group_quotas.csv`
- Field: `group_target_cards = q_i` (integer)

### 1.2 Group structure (authoritative)
- Source: S1 output for the group
- Field: `entity_list` (ordered list; immutable after S1) :contentReference[oaicite:4]{index=4}

---

## 2. Output (S2 execution plan)

For each group, produce an **entity execution plan**:

- one row per entity:
  - `group_id`
  - `entity_name`
  - `cards_for_entity_exact`
  - `entity_index` (0-based)
  - `run_tag`
  - `distribution_method` (string)

Hard invariant:
```

Σ_entity cards_for_entity_exact = group_target_cards (q_i)

```

---

## 3. Canonical distribution algorithm (deterministic)

### 3.1 Entity-level fixed allocation (v2.1, Canonical)

**Policy:** 각 엔티티당 **정확히 3장**으로 고정 (S0의 3×4 규칙과 일관성 유지)

Let:
- E = number of entities in `entity_list`
- q = group_target_cards

**Computation:**
- `cards_for_entity_exact = 3` (모든 엔티티에 동일)
- `q = E × 3` (group_target_cards는 엔티티 수에 따라 결정됨)

**Ordering:**
- use S1-provided `entity_list` order (do NOT sort or re-rank)

**Rationale:**
- S0의 3×4 규칙과 일관성 유지
- Entity당 3장은 QA 단위(문항 3종: Q1/Q2/Q3)를 보장
- 단순하고 결정론적이며 재현 가능

### 3.2 Legacy distribution methods (deprecated)

**Note:** 이전 버전의 "Even + Remainder" 알고리즘은 더 이상 사용되지 않습니다.
현재 정책은 Entity당 3장 고정입니다.

**Legacy reference (for historical context only):**
- Even + Remainder: base = q // E, remainder = q % E
- Minimum per entity: optional switch (deprecated)

---

## 4. Guardrails (hard fail conditions)

- E == 0 → FAIL (S1 invalid output)
- q != E × 3 → FAIL (group_target_cards must equal entity_count × 3)
- Any computed N != 3 → FAIL (all entities must get exactly 3 cards)
- Final sum mismatch → FAIL

---

## 5. Separation from selection & QA (S3 boundary)

This distribution plan determines only S2 generation targets.
S3 later selects exactly `group_target_cards` and fails on shortfall. :contentReference[oaicite:5]{index=5}

---

## 6. Canonical statement (handoff)

> FINAL card counts are controlled at the group level (q_i = E × 3) and deterministically assigned as exactly 3 cards per entity, using the S1 entity order. S2 executes exactly 3 text-only cards per entity. This policy maintains consistency with S0's 3×4 rule.
```

---

# 2) 코드 스켈레톤: S1 entity_list + group_quotas → entity_plan.csv

권장 파일 경로:
`3_Code/src/allocation/build_s2_entity_plan.py`

> 전제: 각 group에 대해 **S1 output JSON**(group_id, entity_list 포함)을 읽을 수 있어야 합니다.
> (파일 위치는 현재 프로젝트에 맞게 `--s1_dir` 패턴으로 잡았습니다.)

```python
#!/usr/bin/env python3
"""
build_s2_entity_plan.py

Canonical: FINAL only
- Input: S1 outputs (entity_list per group) + Allocation quotas (group_target_cards per group)
- Output: S2 entity execution plan (one row per entity) with cards_for_entity_exact

S2 will be called per (group_id, entity_name, cards_for_entity_exact).
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class GroupQuota:
    group_id: str
    group_target_cards: int


def read_group_quotas_csv(path: Path) -> Dict[str, GroupQuota]:
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        required = {"group_id", "group_target_cards"}
        if not r.fieldnames or not required.issubset(set(r.fieldnames)):
            raise ValueError(f"quota csv missing columns: {required} in {path}")
        out: Dict[str, GroupQuota] = {}
        for row in r:
            gid = (row["group_id"] or "").strip()
            q = int(row["group_target_cards"])
            if not gid:
                raise ValueError("Empty group_id in quota csv")
            if q <= 0:
                raise ValueError(f"Invalid group_target_cards (<=0) for {gid}: {q}")
            out[gid] = GroupQuota(group_id=gid, group_target_cards=q)
        if not out:
            raise ValueError("quota csv has 0 rows")
        return out


def load_s1_group_json(s1_path: Path) -> dict:
    with s1_path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if "group_id" not in obj or "entity_list" not in obj:
        raise ValueError(f"S1 json missing group_id/entity_list: {s1_path}")
    return obj


def distribute_even_remainder(entity_list: List[str], q: int, min_per_entity: int = 0) -> List[int]:
    E = len(entity_list)
    if E <= 0:
        raise ValueError("entity_list is empty")
    if q <= 0:
        raise ValueError("q must be > 0")

    if min_per_entity == 1 and q < E:
        raise ValueError(f"min_per_entity=1 requires q>=E, got q={q}, E={E}")

    base = q // E
    rem = q % E

    ns = []
    for i in range(E):
        n = base + (1 if i < rem else 0)
        if min_per_entity == 1 and n < 1:
            # should not happen due to q>=E guard, but keep fail-fast
            raise RuntimeError("Unexpected n<1 under min_per_entity=1")
        if n < 0:
            raise RuntimeError("Unexpected negative allocation")
        ns.append(n)

    if sum(ns) != q:
        raise RuntimeError(f"Sum mismatch: sum(ns)={sum(ns)} != q={q}")
    return ns


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--quota_csv", required=True, help="Allocation output group_quotas.csv")
    p.add_argument("--s1_dir", required=True, help="Directory containing per-group S1 JSON outputs")
    p.add_argument("--s1_glob", default="*.json", help="Glob pattern for S1 json files in s1_dir")
    p.add_argument("--run_tag", required=True, help="RUN_TAG for outputs")
    p.add_argument("--out_csv", default="2_Data/metadata/quotas/s2_entity_plan__{run_tag}.csv",
                   help="Output csv path template")
    p.add_argument("--min_per_entity", type=int, default=0, choices=[0, 1],
                   help="0: allow zero; 1: require >=1 per entity (fails if q<E)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    quota_csv = Path(args.quota_csv)
    s1_dir = Path(args.s1_dir)

    quotas = read_group_quotas_csv(quota_csv)

    s1_paths = sorted(s1_dir.glob(args.s1_glob))
    if not s1_paths:
        raise FileNotFoundError(f"No S1 json files found: {s1_dir} / {args.s1_glob}")

    out_csv_path = Path(args.out_csv.format(run_tag=args.run_tag))
    out_csv_path.parent.mkdir(parents=True, exist_ok=True)

    rows_written = 0
    missing_quota = 0

    with out_csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "run_tag",
            "group_id",
            "entity_index",
            "entity_name",
            "cards_for_entity_exact",
            "group_target_cards",
            "distribution_method",
            "min_per_entity"
        ])

        for s1_path in s1_paths:
            s1 = load_s1_group_json(s1_path)
            gid = str(s1["group_id"]).strip()
            entity_list = s1["entity_list"]

            if gid not in quotas:
                missing_quota += 1
                continue

            q = quotas[gid].group_target_cards
            if not isinstance(entity_list, list) or not all(isinstance(x, str) and x.strip() for x in entity_list):
                raise ValueError(f"Invalid entity_list for group_id={gid} in {s1_path}")

            ns = distribute_even_remainder(entity_list, q, min_per_entity=args.min_per_entity)

            for idx, (name, n) in enumerate(zip(entity_list, ns)):
                w.writerow([args.run_tag, gid, idx, name, n, q, "even_remainder_v1", args.min_per_entity])
                rows_written += 1

    if missing_quota > 0:
        # strict by default: quota universe must match S1 universe in FINAL runs
        raise RuntimeError(f"{missing_quota} groups had S1 outputs but no quota found in quota_csv")

    print("[OK] S2 entity plan generated")
    print(f"- out_csv: {out_csv_path}")
    print(f"- rows: {rows_written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

---

# 3) 실행 예시 (FINAL 전용)

```bash
python3 3_Code/src/allocation/build_s2_entity_plan.py \
  --quota_csv 2_Data/metadata/quotas/group_quotas__FINAL_ALLOC_20251216.csv \
  --s1_dir 2_Data/metadata/generated/FINAL_S1_<RUN_TAG>/s1_outputs \
  --s1_glob "*.json" \
  --run_tag FINAL_PLAN_20251216 \
  --min_per_entity 0
```

생성물:

* `2_Data/metadata/quotas/s2_entity_plan__FINAL_PLAN_20251216.csv`

---

# 4) 운영적으로 매우 중요한 선택지 2개

## 옵션 A (권장, 안전/현실적): `min_per_entity = 0`

* q가 작고 entity가 많으면 일부 entity는 N=0
* 장점: **항상 실행 가능**, quota 합 정확히 유지
* 단점: “정의는 됐는데 카드가 안 생긴 entity”가 생길 수 있음
  → 그러나 이는 FINAL에서 **정상적인 트레이드오프**입니다(coverage vs quota).

## 옵션 B (엄격 커버리지): `min_per_entity = 1`

* 모든 entity에 최소 1장 보장
* 조건: 반드시 q ≥ E
* 실패 시 hard fail → 운영 난이도 상승
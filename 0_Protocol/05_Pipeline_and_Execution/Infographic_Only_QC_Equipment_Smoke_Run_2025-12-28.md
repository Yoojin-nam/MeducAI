# Infographic-only QC/Equipment smoke run (S1 → S4, no OCR)

- Last Updated: 2025-12-28
- Purpose: Validate the updated infographic text policy:
  - `ALLOWED_TEXT` injected into `S1_TABLE_VISUAL` prompts
  - 시험포인트 up to **2 tokens** per entity
  - QC/Equipment profile routing (`infographic_profile=qc_equipment`)
- Scope: S1-only → S3 S1-only → S4 only-infographic

## 0) Preconditions
- Working dir: repo root
- `.env` contains required provider keys (S1/S4 need API key access)

## 1) Generate RUN_TAG and choose 4 QC/physics-like groups
```bash
export RUN_TAG="QC_EQUIP_INFOG_$(date +%Y%m%d_%H%M%S)"
export KEYS_FILE="2_Data/metadata/generated/$RUN_TAG/only_group_keys.txt"
mkdir -p "2_Data/metadata/generated/$RUN_TAG"

python3 - <<'PY'
import csv, random, os
from pathlib import Path

run_tag = os.environ["RUN_TAG"]
csv_path = Path("2_Data/metadata/groups_canonical.csv")

cands = []
with csv_path.open("r", encoding="utf-8") as f:
    r = csv.DictReader(f)
    for row in r:
        key = (row.get("group_key") or "").strip()
        spec = (row.get("specialty") or "").strip().lower()
        if spec in {"physics_qc_informatics"} or key.startswith(("qc__", "quality_control__", "physics__")):
            if key:
                cands.append(key)

cands = sorted(set(cands))
random.seed(42)
sel = random.sample(cands, 4)

out = Path("2_Data/metadata/generated") / run_tag / "only_group_keys.txt"
out.write_text("\n".join(sel) + "\n", encoding="utf-8")
print("Selected 4 group_keys:")
print("\n".join(sel))
print(f"\nWrote: {out}")
PY
```

## 2) Run S1 only (stage 1)
```bash
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --run_tag "$RUN_TAG" \
  --arm A \
  --mode S0 \
  --stage 1 \
  --only_group_keys_file "$KEYS_FILE"
```

## 3) Run S3 in S1-only mode (infographics only)
Use full table for QC/Equipment only:
```bash
S3_S1_ONLY=1 S4_TABLE_INPUT_MODE=full_qc_equipment \
python3 3_Code/src/03_s3_policy_resolver.py \
  --base_dir . --run_tag "$RUN_TAG" --arm A
```

## 4) Run S4 infographic-only
```bash
S4_TABLE_INPUT_MODE=full_qc_equipment \
python3 3_Code/src/04_s4_image_generator.py \
  --base_dir . --run_tag "$RUN_TAG" --arm A --only-infographic --workers 2
```

## 5) Verify (prompt contract)
```bash
python3 - <<'PY'
import json, os
from pathlib import Path

run_tag = os.environ["RUN_TAG"]
p = Path(f"2_Data/metadata/generated/{run_tag}/s3_image_spec__armA.jsonl")
n = 0
for line in p.read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    if r.get("spec_kind") != "S1_TABLE_VISUAL":
        continue
    n += 1
    assert "ALLOWED_TEXT (AUTHORITATIVE):" in (r.get("prompt_en") or "")
    assert isinstance(r.get("exam_point_tokens_by_entity"), dict)
    assert isinstance(r.get("allowed_text_en"), list) and len(r["allowed_text_en"]) > 0
    assert isinstance(r.get("allowed_text_kr"), list)
print("OK. S1_TABLE_VISUAL specs:", n)
PY
```



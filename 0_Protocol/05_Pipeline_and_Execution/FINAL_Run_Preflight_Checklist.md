````markdown
# FINAL Run – Preflight Checklist (Freeze-aligned)

> 목적: Step03_4(Quota allocation) → Step01 FINAL(candidate generation)이
> **groups_canonical.csv (aka legacy “groups.csv”) Freeze 룰을 위반하지 않고**, **터지지 않고 안정적으로** 끝나도록 사전 점검한다.

---

## 0. Canonical Rule (MUST READ)

### 0.1 groups.csv는 SSOT이며 “입력 아티팩트”다 (Hard Rule)
- **Canonical file:** `2_Data/metadata/groups_canonical.csv`
  - (Legacy naming note) 일부 문서/스크립트에서 `groups.csv`로 표기되었으나, **코드 입력 SSOT는 `groups_canonical.csv`**이다.
- `groups_canonical.csv`는 **EDA로 1회 생성 후 Freeze**하며, **S0/S1/FINAL 모든 RUN_TAG에서 동일 파일을 재사용**한다.
- 어떤 downstream 단계도 `groups_canonical.csv`를 **재생성/수정/정규화 변경**하면 안 된다.
- `groups_canonical.csv`의 canonical weight 컬럼은 **`group_weight_sum`**이며, 이것이 “유일한 정본”이다. (다른 weight 파일은 파생/Deprecated)

### 0.2 Freeze 이후 변경 가능한 것 vs 불가능한 것
- **가능(운영 파라미터):** `TOTAL_CARDS`, 일별 학습량, quota/selection 전략, QA sampling 파라미터 등 (EDA 재실행 불필요) :contentReference[oaicite:3]{index=3}
- **불가(구조 파라미터):** curriculum/그룹핑 규칙/weight 정의(정규화 포함)/태그 시스템으로 grouping key가 바뀌는 변경  
  → **EDA 재실행 + groups_canonical.csv 재Freeze 필수**

---

## 1. FINAL Quota Allocation (Step03_4) – REQUIRED

### 1.1 전체 목표 카드 수 (CLI)
- [ ] `TOTAL_CARDS` (CLI)
  - 의미: 이번 FINAL RUN_TAG에서 **최종 확보할 전체 카드 수**
  - 예:
    - Smoke / Dev: `20 ~ 100`
    - Production(예): `1780`

### 1.2 그룹별 카드 수 캡 (ENV)
```env
MIN_CARDS_PER_GROUP_FINAL=1
MAX_CARDS_PER_GROUP_FINAL=20
`````

* [ ] `MIN_CARDS_PER_GROUP_FINAL`

  * 의미: 어떤 그룹도 **0장**이 되지 않도록 하는 최소 보장
  * 권장: `1 ~ 2`
* [ ] `MAX_CARDS_PER_GROUP_FINAL`

  * 의미: 특정 그룹으로 quota “몰빵” 방지
  * ⚠️ 반드시 Step01 candidate 정책과 정렬 필요 (아래 2번)

---

## 2. Step01 FINAL – Candidate Generation Policy (READ-ONLY)

> generation_policy.py 내부 정책 (env로 직접 조정하지 않음)

```text
max_candidates_per_group = 30
overgen_factor = 1.6
overgen_add = 2
retry_rounds = 2
```

### 2.1 핵심 정렬 규칙 (HARD RULE)

* [ ] `MAX_CARDS_PER_GROUP_FINAL <= max_candidates_per_group`

❌ 위 규칙 위반 시:

```
ValueError: Impossible FINAL candidate policy:
quota exceeds MAX_CANDIDATES_PER_GROUP
```

✅ 안전한 조합 예:

* `MAX_CARDS_PER_GROUP_FINAL = 20`
* `max_candidates_per_group = 30`

---

## 3. Group Universe Consistency (DATA INVARIANT) — Freeze-aligned

### 3.1 Canonical file location & immutability

* [ ] `groups_canonical.csv`가 **정해진 위치**에 존재: `2_Data/metadata/groups_canonical.csv`
* [ ] FINAL 실행 전/후에 `groups_canonical.csv`가 **바뀌지 않았음**(hash/mtime로 확인)

> `groups_canonical.csv`는 “생성물이 아니라 입력 SSOT”이며, FINAL RUN에서 수정되면 **재현성 위반**이다. 

### 3.2 group_weights.csv 관련 규칙 (정렬 수정)

* [ ] `group_weights.csv`를 “정본”으로 가정하지 않는다.
* [ ] 존재하더라도 **파생/캐시**로만 취급하며, 필요 시 **groups_canonical.csv의 group_weight_sum으로 재생성**되는 것이 원칙이다. 

### 3.3 Preflight validation (빠른 점검 커맨드)

```bash
python3 - << 'PY'
import pandas as pd, hashlib, os
from pathlib import Path

p = Path("2_Data/metadata/groups_canonical.csv")
assert p.exists(), f"Missing: {p}"

b = p.read_bytes()
print("groups_canonical.csv bytes:", len(b))
print("groups_canonical.csv sha256:", hashlib.sha256(b).hexdigest())

df = pd.read_csv(p, keep_default_na=False)
req = ["group_id","group_key","anatomy","modality_or_type","category","group_weight_sum"]
miss = [c for c in req if c not in df.columns]
assert not miss, f"Missing required columns: {miss}"


wbad = (pd.to_numeric(df["group_weight_sum"], errors="coerce") <= 0).sum()
assert wbad == 0, f"group_weight_sum <= 0 rows: {wbad}"

print("OK: groups_canonical.csv SSOT contract satisfied. rows=", len(df))
PY
```

---

## 4. Recommended Presets

### 4.1 Smoke / Development

```env
MIN_CARDS_PER_GROUP_FINAL=1
MAX_CARDS_PER_GROUP_FINAL=20
```

```bash
TOTAL_CARDS=20~100
```

### 4.2 Production (1780)

```env
MIN_CARDS_PER_GROUP_FINAL=1
MAX_CARDS_PER_GROUP_FINAL=20~25
```

```bash
TOTAL_CARDS=1780
```

> 25 초과는 Step01 정책 조정 없이 비권장

---

## 5. Execution Order (DO NOT SKIP)

1. [ ] `.env` 수정
2. [ ] Step03_4 재실행 (quota json **재생성**)

```bash
python3 3_Code/src/03_4_plan_allocation.py \
  --base_dir . \
  --run_tag <RUN_TAG> \
  --arm A \
  --mode FINAL \
  --total_cards <TOTAL_CARDS>
```

3. [ ] Step01 FINAL

```bash
python3 3_Code/src/01_generate_json.py \
  --mode FINAL --provider gemini --arm A --run_tag <RUN_TAG>
```

---

## 6. One-line Sanity Check (Post-allocation)

```bash
python3 - << 'PY'
import json
p="2_Data/metadata/generated/<RUN_TAG>/target_cards_per_group_<RUN_TAG>__armA.json"
q=json.load(open(p))["target_cards_per_group"]
print("groups:", len(q), "max_quota:", max(q.values()), "sum_quota:", sum(q.values()))
PY
```

* [ ] `max_quota <= MAX_CARDS_PER_GROUP_FINAL`
* [ ] `sum(quota) == TOTAL_CARDS`

---

## 7. Post-run Freeze Evidence (FINAL run record-keeping)

* [ ] `groups.csv sha256`를 run log(또는 run manifest)에 기록한다.
* [ ] “이번 FINAL은 groups.csv를 변경하지 않았다”는 문장 1줄을 남긴다.

  * 이유: 같은 `groups.csv`를 S0/S1/FINAL에 재사용해야 재현성이 성립한다. 
# FINAL Export - Quick Reference Card

**Last Updated**: 2026-01-07

---

## 🚀 Complete Export Pipeline (4 Phases)

### Phase 1: Allocation (6,000 cards)
```bash
python3 3_Code/src/tools/allocation/final_distribution_allocation.py \
    --base_dir . \
    --must_include 2_Data/metadata/generated/FINAL_DISTRIBUTION/assignments_specialist.csv
```
**Output**: `allocation/final_distribution_allocation__6000cards.json`

---

### Phase 2: Assignments (1,680 rows)
```bash
python3 3_Code/src/tools/qa/generate_resident_assignments_from_specialist.py \
    --allocation 2_Data/metadata/generated/FINAL_DISTRIBUTION/allocation/final_distribution_allocation__6000cards.json \
    --s5 2_Data/metadata/generated/FINAL_DISTRIBUTION/s5_validation__armG.jsonl \
    --reviewers 1_Secure_Participant_Info/reviewer_master.csv \
    --specialist_assignments 2_Data/metadata/generated/FINAL_DISTRIBUTION/assignments_specialist.csv \
    --out_dir 2_Data/metadata/generated/FINAL_DISTRIBUTION/assignments \
    --seed 20260101
```
**Output**: `assignments/Assignments.csv` (1,680 rows)

---

### Phase 3: AppSheet Export
```bash
# Step 1: Generate CSVs
python3 3_Code/src/tools/final_qa/export_appsheet_tables.py \
    --run_dir 2_Data/metadata/generated/FINAL_DISTRIBUTION \
    --out_dir 6_Distributions/Final_QA/AppSheet_Export \
    --realistic_run_dir 2_Data/metadata/generated/FINAL_DISTRIBUTION \
    --copy_images true \
    --verbose

# Step 2: Copy REGEN images (QA subset)
python3 << 'PYTHON'
import csv, os, shutil
from pathlib import Path

with open('6_Distributions/Final_QA/AppSheet_Export/Assignments.csv') as f:
    assignment_uids = set(row['card_uid'] for row in csv.DictReader(f))

src = Path('2_Data/metadata/generated/FINAL_DISTRIBUTION/images_regen')
dst = Path('6_Distributions/Final_QA/AppSheet_Export/images_regen')
dst.mkdir(exist_ok=True)

for fname in os.listdir(src):
    if fname.endswith('.jpg'):
        parts = fname.replace('IMG__FINAL_DISTRIBUTION__','').replace('_regen.jpg','').split('__')
        if len(parts) >= 3:
            gid, eid, role = parts[0], parts[1].replace('_',':',1), parts[2]
            uid = f'{gid}::{eid}__{role}__{0 if role=="Q1" else 1}'
            if uid in assignment_uids:
                shutil.copy2(src/fname, dst/fname)
PYTHON

# Step 3: Fix S5.csv image references
python3 << 'PYTHON'
import csv

with open('6_Distributions/Final_QA/AppSheet_Export/S5.csv', 'r', newline='') as f:
    rows = list(csv.DictReader(f))

for row in rows:
    img = row.get('s5_regenerated_image_filename', '')
    if img:
        row['s5_regenerated_image_filename'] = img.replace('__0_regen.jpg','_regen.jpg').replace('__1_regen.jpg','_regen.jpg')

with open('6_Distributions/Final_QA/AppSheet_Export/S5.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
PYTHON
```

**Output**: `6_Distributions/Final_QA/AppSheet_Export/` (5 CSVs + 3 image dirs)

---

### Phase 4: Anki Export (Main + 11 Specialty)
```bash
# Main integrated deck
python3 3_Code/src/tools/anki/export_final_anki_integrated.py \
    --allocation 2_Data/metadata/generated/FINAL_DISTRIBUTION/allocation/final_distribution_allocation__6000cards.json \
    --s5 2_Data/metadata/generated/FINAL_DISTRIBUTION/s5_validation__armG.jsonl \
    --s2_baseline 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG.jsonl \
    --s2_regen 2_Data/metadata/generated/FINAL_DISTRIBUTION/s2_results__s1armG__s2armG__regen.jsonl \
    --images_anki 2_Data/metadata/generated/FINAL_DISTRIBUTION/images_anki \
    --images_regen 2_Data/metadata/generated/FINAL_DISTRIBUTION/images_regen \
    --output 6_Distributions/anki/MeducAI_FINAL_6000cards_Integrated.apkg \
    --threshold 80.0

# 11 Specialty decks
python3 3_Code/Scripts/export_all_specialty_decks.py
```

**Output**: 
- `6_Distributions/anki/MeducAI_FINAL_6000cards_Integrated.apkg` (496 MB)
- `6_Distributions/anki/Specialty_Decks/*.apkg` (11 files, ~497 MB)

---

## 📊 Expected Results

| Metric | Value |
|--------|-------|
| Allocation | 6,000 cards |
| Assignments | 1,680 rows |
| QA unique cards | 1,284 |
| Anki cards | ~5,950 |
| REGEN cards | ~5,660 |
| File size (Anki) | ~1 GB |
| File size (AppSheet) | ~615 MB |

---

## ⚠️ Critical Checkpoints

1. **After Allocation**: Verify specialist 330 cards 100% included
2. **After Assignments**: Verify specialist_uids match exactly
3. **After AppSheet**: Verify images_regen/ exists with ~350 files
4. **After Anki**: Verify REGEN integration (check stats output)

---

**Quick Reference Version**: 1.0  
**For Full Details**: See `FINAL_EXPORT_Allocation_and_Integration_Guide.md`

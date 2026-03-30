# S4 Prompt Template Smoke Test Plan

**Date:** 2025-12-20  
**Purpose:** Verify S3 prompt_en generation using prompt templates  
**Scope:** CONCEPT lane (S1_TABLE_VISUAL) and EXAM lane (S2_CARD_IMAGE)

---

## Prerequisites

1. S0/S1/S2 pipeline has been run successfully for at least one group
2. Test data available:
   - `stage1_struct__arm{arm}.jsonl` with at least one group
   - `s2_results__s1arm{S1_ARM}__s2arm{S2_ARM}.jsonl` (new format, 2025-12-23) 또는 `s2_results__arm{arm}.jsonl` (legacy) with at least one entity having Q1 card
3. Prompt templates are in place:
   - `3_Code/prompt/S4_CONCEPT_SYSTEM__v1.md`
   - `3_Code/prompt/S4_CONCEPT_USER__{visual_type}__v1.md` (for test group's visual_type)
   - `3_Code/prompt/S4_EXAM_SYSTEM__v1.md`
   - `3_Code/prompt/S4_EXAM_USER__v1.md`
4. `_registry.json` includes all S4 prompt keys

---

## Test Commands

### Step 1: Verify Prompt Templates Exist

```bash
# Check CONCEPT templates
ls -1 3_Code/prompt/S4_CONCEPT_*.md | wc -l
# Expected: 13 files (1 system + 12 user templates)

# Check EXAM templates
ls -1 3_Code/prompt/S4_EXAM_*.md | wc -l
# Expected: 2 files (1 system + 1 user)

# Verify registry entries
grep -E "S4_(CONCEPT|EXAM)" 3_Code/prompt/_registry.json
# Expected: All S4 prompt keys present
```

### Step 2: Run S3 with Test Data

```bash
# Set base directory (adjust as needed)
BASE_DIR="/path/to/workspace/workspace/MeducAI"
RUN_TAG="TEST_20251220"  # Use your test run_tag
ARM="A"  # Use your test arm

# Run S3
cd "$BASE_DIR"
python 3_Code/src/03_s3_policy_resolver.py \
  --base_dir "$BASE_DIR" \
  --run_tag "$RUN_TAG" \
  --arm "$ARM"
```

**Expected:** S3 completes without errors

### Step 3: Verify S3 Output Artifacts

```bash
OUT_DIR="$BASE_DIR/2_Data/metadata/generated/$RUN_TAG"
IMAGE_SPEC="$OUT_DIR/s3_image_spec__arm${ARM}.jsonl"

# Check that image spec file exists and is non-empty
test -f "$IMAGE_SPEC" && echo "✓ Image spec file exists" || echo "✗ Image spec file missing"
test -s "$IMAGE_SPEC" && echo "✓ Image spec file is non-empty" || echo "✗ Image spec file is empty"

# Count specs by kind
echo "=== Spec counts by kind ==="
grep -o '"spec_kind":"[^"]*"' "$IMAGE_SPEC" | sort | uniq -c
# Expected: At least 1 S1_TABLE_VISUAL and 1 S2_CARD_IMAGE

# Verify prompt_en field exists and is non-empty for all specs
echo "=== Prompt validation ==="
python3 << 'EOF'
import json
import sys

spec_file = sys.argv[1]
with open(spec_file, 'r') as f:
    specs = [json.loads(line) for line in f if line.strip()]

print(f"Total specs: {len(specs)}")
for i, spec in enumerate(specs, 1):
    spec_kind = spec.get('spec_kind', 'UNKNOWN')
    prompt_en = spec.get('prompt_en', '')
    group_id = spec.get('group_id', 'UNKNOWN')
    
    if not prompt_en:
        print(f"✗ Spec {i} ({spec_kind}, group={group_id}): prompt_en is empty")
        sys.exit(1)
    
    if len(prompt_en) < 50:
        print(f"⚠ Spec {i} ({spec_kind}, group={group_id}): prompt_en is suspiciously short ({len(prompt_en)} chars)")
    
    # Check that prompt contains expected template content
    if spec_kind == "S1_TABLE_VISUAL":
        if "medical illustrator" not in prompt_en.lower() and "radiologist" not in prompt_en.lower():
            print(f"⚠ Spec {i} (TABLE_VISUAL): prompt_en may not contain system prompt")
        if "master table" not in prompt_en.lower() and "MASTER TABLE" not in prompt_en:
            print(f"⚠ Spec {i} (TABLE_VISUAL): prompt_en may not contain master table reference")
    
    if spec_kind == "S2_CARD_IMAGE":
        if "radiologist" not in prompt_en.lower():
            print(f"⚠ Spec {i} (CARD_IMAGE): prompt_en may not contain system prompt")
        modality = spec.get('modality', '')
        anatomy = spec.get('anatomy_region', '')
        if modality and modality not in prompt_en:
            print(f"⚠ Spec {i} (CARD_IMAGE): modality '{modality}' not found in prompt_en")
        if anatomy and anatomy not in prompt_en:
            print(f"⚠ Spec {i} (CARD_IMAGE): anatomy_region '{anatomy}' not found in prompt_en")

print("✓ All specs have non-empty prompt_en")
EOF
"$IMAGE_SPEC"
```

**Expected:** All specs have non-empty prompt_en with expected content

### Step 4: Verify Template Content (Not Raw Template Keys)

```bash
# Ensure prompt_en contains actual formatted content, not template placeholders
echo "=== Checking for unformatted placeholders ==="
grep -n "{group_id}\|{group_path}\|{visual_type_category}\|{master_table_markdown_kr}\|{entity_name}\|{card_role}\|{modality_preferred}\|{anatomy_region}\|{view_or_sequence}\|{key_findings_keywords}\|{exam_focus}" "$IMAGE_SPEC" && echo "✗ Found unformatted placeholders!" || echo "✓ No unformatted placeholders found"

# Ensure prompt_en does NOT contain raw template file references
grep -n "S4_CONCEPT_SYSTEM\|S4_CONCEPT_USER\|S4_EXAM_SYSTEM\|S4_EXAM_USER" "$IMAGE_SPEC" && echo "✗ Found template file references in prompt_en!" || echo "✓ No template file references found"
```

**Expected:** 
- No unformatted placeholders (all should be replaced)
- No template file references (prompts are concatenated, not referenced)

### Step 5: Verify Visual Type Category Mapping

```bash
# For CONCEPT lane, verify correct user template is used based on visual_type_category
echo "=== Verifying visual_type_category mapping ==="
python3 << 'EOF'
import json
import sys

spec_file = sys.argv[1]
with open(spec_file, 'r') as f:
    specs = [json.loads(line) for line in f if line.strip()]

table_specs = [s for s in specs if s.get('spec_kind') == 'S1_TABLE_VISUAL']
print(f"Found {len(table_specs)} TABLE_VISUAL specs")

for spec in table_specs:
    visual_type = spec.get('visual_type_category', 'UNKNOWN')
    prompt_en = spec.get('prompt_en', '')
    group_id = spec.get('group_id', 'UNKNOWN')
    
    # Check for visual-type-specific content hints
    visual_type_lower = visual_type.lower()
    # Note (v11): Comparison, Algorithm, Classification, and Sign_Collection categories removed
    # Add checks for other visual types as needed
    
    print(f"✓ Group {group_id}: visual_type={visual_type}, prompt length={len(prompt_en)}")

print("✓ Visual type category mapping verified")
EOF
"$IMAGE_SPEC"
```

**Expected:** Each TABLE_VISUAL spec uses appropriate template for its visual_type_category

### Step 6: Verify EXAM Lane Prompt Structure

```bash
# For EXAM lane, verify prompt uses ONLY image_hint (no card text)
echo "=== Verifying EXAM lane prompt structure ==="
python3 << 'EOF'
import json
import sys

spec_file = sys.argv[1]
with open(spec_file, 'r') as f:
    specs = [json.loads(line) for line in f if line.strip()]

card_specs = [s for s in specs if s.get('spec_kind') == 'S2_CARD_IMAGE']
print(f"Found {len(card_specs)} CARD_IMAGE specs")

for spec in card_specs:
    prompt_en = spec.get('prompt_en', '')
    entity_name = spec.get('entity_name', 'UNKNOWN')
    card_role = spec.get('card_role', 'UNKNOWN')
    
    # Check that prompt contains image_hint fields
    modality = spec.get('modality', '')
    anatomy = spec.get('anatomy_region', '')
    key_findings = spec.get('key_findings_keywords', [])
    
    if modality and modality not in prompt_en:
        print(f"✗ Entity {entity_name} ({card_role}): modality '{modality}' missing from prompt")
    if anatomy and anatomy not in prompt_en:
        print(f"✗ Entity {entity_name} ({card_role}): anatomy_region '{anatomy}' missing from prompt")
    
    # Verify key_findings are included
    if key_findings:
        key_findings_str = ', '.join(str(k) for k in key_findings[:3])  # Check first 3
        if key_findings_str.lower() not in prompt_en.lower():
            print(f"⚠ Entity {entity_name} ({card_role}): key_findings may not be properly included")
    
    # Check that prompt does NOT contain card text references (EXAM lane should use image_hint only)
    # Note: This is a soft check - the prompt template itself may mention "flashcard" generically
    if "Question (front):" in prompt_en or "Explanation (back):" in prompt_en:
        print(f"⚠ Entity {entity_name} ({card_role}): prompt may contain card text (EXAM lane should use image_hint only)")
    
    print(f"✓ Entity {entity_name} ({card_role}): prompt length={len(prompt_en)}")

print("✓ EXAM lane prompt structure verified")
EOF
"$IMAGE_SPEC"
```

**Expected:** EXAM lane prompts contain image_hint fields, no card text references

### Step 7: Determinism Check (Optional)

```bash
# Run S3 twice and verify prompt_en is identical (byte-for-byte)
echo "=== Determinism check ==="
python3 << 'EOF'
import json
import sys

spec_file = sys.argv[1]

# Read specs and extract prompt_en values
with open(spec_file, 'r') as f:
    specs = [json.loads(line) for line in f if line.strip()]

prompt_en_values = []
for spec in specs:
    spec_id = f"{spec.get('group_id', '?')}__{spec.get('entity_id', '?')}__{spec.get('card_role', '?')}__{spec.get('spec_kind', '?')}"
    prompt_en = spec.get('prompt_en', '')
    prompt_en_values.append((spec_id, prompt_en))

# Check for duplicates (same spec should have same prompt)
from collections import defaultdict
prompt_by_id = defaultdict(list)
for spec_id, prompt in prompt_en_values:
    prompt_by_id[spec_id].append(prompt)

for spec_id, prompts in prompt_by_id.items():
    if len(set(prompts)) > 1:
        print(f"✗ {spec_id}: Non-deterministic prompts detected")
        for i, p in enumerate(prompts):
            print(f"  Prompt {i+1}: {p[:100]}...")
    else:
        print(f"✓ {spec_id}: Deterministic")

print("✓ Determinism check complete")
EOF
"$IMAGE_SPEC"
```

**Expected:** Same inputs produce identical prompt_en (deterministic)

---

## Success Criteria

✅ All prompt template files exist  
✅ `_registry.json` includes all S4 prompt keys  
✅ S3 runs without errors  
✅ `s3_image_spec__arm{arm}.jsonl` contains specs with non-empty `prompt_en`  
✅ `prompt_en` contains formatted content (no unformatted placeholders)  
✅ `prompt_en` does NOT contain template file references  
✅ CONCEPT lane uses correct template based on `visual_type_category`  
✅ EXAM lane prompts contain image_hint fields (modality, anatomy, key_findings)  
✅ EXAM lane prompts do NOT contain card text (front/back)  
✅ Prompts are deterministic (same inputs → same outputs)

---

## Troubleshooting

### Issue: "Missing prompt template" error

**Check:**
- Prompt files exist in `3_Code/prompt/`
- `_registry.json` includes the key
- File naming matches registry exactly

**Fix:**
```bash
# Verify file exists
ls -la "3_Code/prompt/S4_CONCEPT_SYSTEM__v1.md"

# Check registry entry
grep "S4_CONCEPT_SYSTEM" "3_Code/prompt/_registry.json"
```

### Issue: Unformatted placeholders in prompt_en

**Check:**
- `safe_prompt_format()` is being called correctly
- All required kwargs are provided

**Fix:**
- Review `compile_table_visual_spec()` and `compile_image_spec()` functions
- Ensure all placeholders in template have corresponding kwargs

### Issue: Wrong template used for visual_type_category

**Check:**
- `visual_type_category` value matches expected enum
- Fallback to General is working

**Fix:**
- Verify `visual_type_category` normalization in S1
- Check template file naming matches `S4_CONCEPT_USER__{visual_type}__v1.md`

---

## Next Steps (After Smoke Test Passes)

1. Run S4 image generation with the new prompts
2. Verify image quality matches expectations
3. Compare generated images with previous template-based prompts
4. Update documentation if needed


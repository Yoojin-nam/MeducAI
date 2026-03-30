# S4 Concept Prompt v2 Summary

**Date:** 2025-12-20  
**Purpose:** Improve S4 Concept infographic quality with deterministic expansion, larger panels, and schematic-first visuals

---

## Files Created

### System Prompt
- `S4_CONCEPT_SYSTEM__v2.md` - Enhanced system prompt with global rules

### User Templates (11 files)
1. `S4_CONCEPT_USER__General__v2.md`
2. `S4_CONCEPT_USER__Pathology_Pattern__v2.md`
3. `S4_CONCEPT_USER__Pattern_Collection__v2.md`
4. `S4_CONCEPT_USER__Physiology_Process__v2.md`
5. `S4_CONCEPT_USER__QC__v2.md`
6. `S4_CONCEPT_USER__Sign_Collection__v2.md`
7. `S4_CONCEPT_USER__Anatomy_Map__v2.md`
8. `S4_CONCEPT_USER__Comparison__v2.md`
9. `S4_CONCEPT_USER__Classification__v2.md`
10. `S4_CONCEPT_USER__Algorithm__v2.md`
11. `S4_CONCEPT_USER__Equipment__v2.md`

---

## Key Changes from v1 to v2

### Global Rules (System Prompt)

1. **Deterministic Panel Limit**
   - MAX 6 expanded panels (prefer 4)
   - If table rows > 6: expand only first 6 rows in table order
   - Remaining entities → compact "Others" section (keywords only)
   - NO subjective selection of "important" entities

2. **Word Budget per Panel**
   - Entity name (English, bold)
   - ≤ 3 keywords (short phrases, no sentences)
   - 1 boxed "시험포인트" (Korean, EXACTLY one short line)
   - Ban paragraphs globally

3. **No Markdown Table Rendering**
   - Explicit instruction: "Do NOT render the markdown table as a table"
   - Must transform into diagram/grid/flow

4. **Schematic-First Requirement**
   - QC/Physiology_Process/Equipment/Algorithm MUST include:
     - flowchart, block diagram, loop diagram, or axes chart
   - "Text-only slide" is a FAIL condition

5. **Strict Boundary**
   - Use ONLY master table content
   - No hallucinated parameters/values/ranges
   - No extra findings, taxonomy, or steps

### Visual-Type Specific Enhancements

#### General
- 4–6 entity panels + Others list
- Optional small schematic icons per panel

#### Pathology_Pattern
- Pattern-first illustrations emphasizing distribution/appearance
- Grid layout (2×2 or 3×2)

#### Pattern_Collection
- 3–5 buckets allowed
- Total expanded items capped by top-N rule (max 6)
- Bucket headers short; mini-items: name + 1 keyword

#### Physiology_Process
- **MANDATORY** 4–7 stage arrow flow diagram
- Each stage: ≤ 2 tokens for imaging manifestation
- One compact "exam pitfalls" box (≤ 3 lines)

#### QC
- **MANDATORY** QC loop diagram: Acquire → Measure → Compare → Action
- Compact metrics panel (keywords only; ranges only if provided)
- "failure → fix" mini-map
- No bullet-only dashboards

#### Sign_Collection
- Uniform grid (max 6)
- Each cell: sign name + tiny pseudo-image + ≤ 2 keywords + one-line 시험포인트

#### Anatomy_Map
- Central schematic map + max 6 callouts
- Others list for additional regions

#### Comparison
- Choose ONE coherent layout; cap expanded items (max 4–6)
- Emphasize differentiator axes

#### Classification
- **MANDATORY** decision tree/taxonomy diagram
- Max 6 leaf nodes shown; rest in Others

#### Algorithm
- **MANDATORY** pipeline: Input → Steps(3–6) → Output
- Each step ≤ 2 tokens
- One "common pitfall" exam box (Korean one-liner)

#### Equipment
- **MANDATORY** labeled block diagram of components
- "artifact/limitation → mitigation" mini-map
- Do not hallucinate numeric settings

---

## Compatibility

### Preserved Elements
- ✅ All placeholders unchanged: `{group_id}`, `{group_path}`, `{visual_type_category}`, `{master_table_markdown_kr}`
- ✅ Output contract unchanged: "Return IMAGE ONLY."
- ✅ No schema field changes
- ✅ No S1/S2 contract modifications

### Integration
- ✅ `_registry.json` updated to default to v2 for all S4_CONCEPT prompts
- ✅ Code in `03_s3_policy_resolver.py` automatically uses v2 (loads from registry)
- ✅ v1 files remain untouched (available as fallback if needed)

---

## Testing Recommendations

1. **QC/Physics-heavy group**: Verify at least one diagram present, not text-only
2. **Pathology/Neuro group**: Confirm 4–6 panels, large readable text, "Others" behavior when rows > 6
3. **Verify output**: Still returns "IMAGE ONLY" and placeholders render correctly

---

## Fallback to v1

To revert to v1, update `_registry.json` entries back to `*__v1.md` filenames. No code changes needed.

---

## v3 Stabilization Patch (2025-12-23)

### Key Changes

- **ALLOWED TEXT ZONES**: Defined explicit 3-zone structure (Title bar, Structural labels, Entity text tokens) to resolve System ↔ Category rule conflicts
- **시험포인트 Determinism**: Made 시험포인트 MANDATORY when table cell is non-empty and clear (not optional anymore)
- **Imaging Cue Token**: Added optional 1-2 word imaging cue token (extracted from table, no labels)
- **Numeric Relaxation**: QC and Equipment categories can include numeric tokens if present anywhere in table row (not only in 시험포인트)
- **"Others" Token Selection**: Deterministic priority list (시험포인트 → imaging cue → modality → omit)
- **Modality Harmonization**: Category-specific rules (REQUIRED for General/Pathology_Pattern/Anatomy_Map if present; OPTIONAL for QC/Equipment/Physiology_Process)
- **Structural Labels**: Explicitly allowed Zone 2 labels for QC loop, stage labels, bucket headers, component blocks
- **Text Prohibitions**: Removed all literal "..." truncations; clarified field label prohibitions


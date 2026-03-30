# HANDOFF — Table Visual(Infographic) Richer Text + Auto-fit + Expanded Allowlist (2026-01-03)

## Context / Goal

- **Goal**: Increase explanatory richness in S4-generated teaching slides while enforcing **no clipping/overlap**, **no taxonomy/group-path leakage**, and **no Korean**.
- **Constraint**: Maintain **“ALLOWED_TEXT only”** contract; therefore S3 must provide a sufficiently rich allowlist.
- **Observed issue**: Some table visuals (esp. Anatomy/relationship diagrams) produced incorrect arrows/relationships when S4 input was overly compact.

---

## Summary of Changes

### A) S4 prompt updates — richer explanatory text + key takeaways + strict auto-fit

Updated the following prompt templates:

- `3_Code/prompt/S4_CONCEPT_SYSTEM__S5R2__v5.md`
- `3_Code/prompt/S4_CONCEPT_USER__General__S5R2__v5.md`
- `3_Code/prompt/S4_CONCEPT_USER__Anatomy_Map__S5R2__v5.md`
- `3_Code/prompt/S4_CONCEPT_USER__Equipment__S5R2__v5.md`
- `3_Code/prompt/S4_CONCEPT_USER__Pathology_Pattern__S5R2__v5.md`

Key behaviors now explicitly required:

- **Per panel/callout**:
  - Target **2–4 short lines** (excluding entity name line).
  - Add **1–2 `Explanation:` lines** derived ONLY from the same row content.
  - If space is tight: **drop the 2nd explanation line first** (before shrinking fonts).
- **Slide-level summary**:
  - Add **`Key takeaways:` 5–8 bullet lines**, derived ONLY from the master table.
  - If space is tight: reduce to **minimum 5** before font-size reduction.
- **Auto-fit/no-clipping**:
  - Reinforced deterministic overflow order; added “2nd Explanation line” as an explicit optional-removal target.
- **Leak prevention**:
  - Continued hard bans: no taxonomy (`>`), no group_path/path-like tokens, no Korean.
  - Structural labels explicitly allowed include `Explanation:` and `Key takeaways:` (still must use ALLOWED_TEXT after labels).

#### Anatomy_Map-specific safety: prevent “wrong anatomy arrows”

In `S4_CONCEPT_USER__Anatomy_Map__S5R2__v5.md`, added a strict rule to avoid incorrect leader lines:

- Do NOT draw detailed vessel/bronchus branching or true 3D courses.
- Leader lines/arrows may point ONLY to abstract segments / numbered tags on the region map.
- If placement would require guessing: do NOT place on the map; render as a “Structure card” and express relationships in text only.

---

### B) S3 allowlist expansion — extract sanitized EN phrases from original master table (bounded)

Modified:

- `3_Code/src/03_s3_policy_resolver.py`

Changes:

- Expanded `allowed_text_en` generation:
  - Previously: derived mostly from the compact 4-column table.
  - Now: additionally extracts **EN phrase candidates (1–6 words)** from **original master table cells**:
    - Sanitizes markdown triggers (`|`, backticks, fences), removes `>` and Hangul.
    - Splits on punctuation and delimiters, chunks long fragments into max-6-word groups.
    - Filters out numeric-only tokens and metadata-ish phrases.
    - De-duplicates and caps to a bounded size.
- Increased the number of allowlist items **printed into the prompt** (previously hard-capped at 200):
  - Now controlled by env var: `S3_ALLOWED_TEXT_EN_MAX_ITEMS` (default `600`, clamp `50..2000`).
- Phrase extraction cap:
  - `S3_ALLOWED_TEXT_PHRASE_MAX` (default `600`, clamp `0..2000`).

---

### C) S3 guard strengthening — taxonomy `>` detection in prompt hygiene

In `3_Code/src/03_s3_policy_resolver.py` prompt-hygiene checks:

- Added a hard finding if the rendered prompt contains **any raw `>` character**, regardless of spacing:
  - `contains_gt_char('>')`
- Kept the existing heuristic `_detect_taxonomy_path_separator()` for token>token patterns as an additional signal.

---

### D) Fix for Anatomy_Map arrow errors — default FULL table input for Anatomy_Map

Root cause observed from a real sample (`grp_0a283963db`):

- `visual_type_category=Anatomy_Map`
- but `master_table_input_kind=compact` → adjacency/relationship fields were lost → model “guessed” and drew incorrect arrows.

Change:

- In `compile_table_visual_spec()` table input policy:
  - When `S4_TABLE_INPUT_MODE` is not explicitly set:
    - **If `visual_type_category == Anatomy_Map` → default `full_all`** (uses the full master table for S4).
    - Otherwise keep the existing legacy env-based behavior.

Users can still override with `S4_TABLE_INPUT_MODE=compact` if needed.

---

## Recommended Re-run Commands (Operator Notes)

Recompile S3 specs (arm P):

```bash
python3 3_Code/src/03_s3_policy_resolver.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm P
```

Selective S4 regeneration for a specific group (recommended `repaired`):

```bash
python3 3_Code/src/04_s4_image_generator.py --base_dir . --run_tag FINAL_DISTRIBUTION --arm P \
  --output_variant repaired --only-infographic --only_group_id grp_0a283963db \
  --overwrite_existing --ignore_batch_tracking
```

Allowlist size tuning (defaults shown):

- `S3_ALLOWED_TEXT_PHRASE_MAX=600` (candidate phrases extracted from original table)
- `S3_ALLOWED_TEXT_EN_MAX_ITEMS=600` (items printed into the prompt)

---

## Trade-offs / Risks

- **Prompt length increases**: allowlist printed to prompt grows from 200 → (default) 600; may increase token usage.
  - Mitigation: reduce `S3_ALLOWED_TEXT_EN_MAX_ITEMS` to 300–500 if needed.
- **Anatomy_Map uses full table by default**: better grounding but longer prompts.
- **Arrow correctness limits**: Even with more context, precise 3D anatomical course drawings can remain error-prone.
  - Mitigation: “anti-wrong-arrow” rules constrain arrows to abstract segments/number tags and move uncertain placement into text-only cards.



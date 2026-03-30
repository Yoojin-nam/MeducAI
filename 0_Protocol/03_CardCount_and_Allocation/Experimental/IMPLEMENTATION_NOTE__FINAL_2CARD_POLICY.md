# Implementation Note — FINAL 2-card (Q1/Q2) operational policy

**Status:** EXPERIMENTAL / Implementation note (Non‑Canonical)  
**Applies to:** Current runtime behavior of `3_Code/src/01_generate_json.py` + `3_Code/prompt/S2_SYSTEM__v8.md`  
**Last Updated:** 2025-12-28

---

## Why this note exists

The **canonical protocol** documents in this folder define:

- **S0 (QA / arm comparison):** fixed 12 cards per set, typically **4 entities × 3 cards** (Q1/Q2/Q3)
- **FINAL (deployment):** (in canonical docs) typically **3 cards per entity**

However, the **current implementation** of the pipeline has moved to an **exam-aligned 2-card policy** for S2:

- S2 prompt (`S2_SYSTEM__v8.md`) describes **Q1/Q2 only**
- `validate_stage2()` in `3_Code/src/01_generate_json.py` enforces **exactly 2 cards per entity**

This note records that operational reality **without changing the canonical protocol docs retroactively**.

---

## Practical implications (today)

- **FINAL runs**: effectively **2 cards per entity (Q1/Q2)** at S2.
- **S0 runs**: historical QA was performed with **4×3** (Q1/Q2/Q3).  
  If S0 is not rerun, no code change is required; we just keep this as a traceability note.

---

## If we ever need to rerun S0 (future contingency)

If S0 must be rerun with **4×3**, the pipeline needs an explicit “S0-3card” prompt+validator path (e.g., use archived `S2_SYSTEM__v7.md` and a 3-card validator), instead of relying on the FINAL 2-card validator.



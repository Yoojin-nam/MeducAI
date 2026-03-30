# Canonical Merge Log — 2025-12-17

**Status:** Historical Reference  
**Last Updated:** 2025-12-20  
**Purpose:** Canonical merge 기록 (Historical)

## Scope
This merge finalizes the responsibility boundaries and card-count governance
across Step S0–S4 and FINAL deployment in MeducAI.

## Verified by CP Framework
- CP-1: Card-count decision authority isolated to FINAL Allocation
- CP-2: S0 Allocation fixed as recording-only artifact
- CP-3: S2 fixed as execution-only engine
- CP-4: S3 fixed as state-only QA gate
- CP-5: RAG / Thinking hard-gated for valid arm comparison

## Key Invariants (Frozen)
- S0 uses fixed set-level payload (q = 12)
- FINAL uses group-level quotas (Σ q_i = TOTAL_CARDS)
- LLM stages never decide counts or policy
- RAG / Thinking experiments require observable execution and metadata

## Status
All CP checks PASSED.
This Canonical set is **approved and frozen**.

Further changes require:
- Explicit protocol proposal
- CP re-validation
- New Canonical merge record

2025-12-17 — Governance declaration: S0/S1 Canonical Set Complete. All future changes must follow archived + new canonical policy with CP re-validation.

2021-12-18 - “Objective Source Traceability Canonical v1.0 merged”
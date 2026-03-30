# Protocol Addendum: S0 6-Arm — RAG/Thinking Option B

**Status:** **SUPERSEDED** (Historical Reference)  
**Superseded-by:** `ARM_CONFIGS_Provider_Model_Resolution.md`  
**Applies-to:** Step S0 (Implementation)  
**Last Updated:** 2025-12-20

**⚠️ IMPORTANT:** This document is **superseded**. The canonical protocol is `ARM_CONFIGS_Provider_Model_Resolution.md`. This document is retained as a **historical reference** for implementation details and verification procedures.

---

## 1. Purpose
This document provides implementation details and verification procedures
for RAG and Thinking in S0.

Normative acceptance rules are defined in
ARM_CONFIGS_Provider_Model_Resolution.md.

---

## 2. Problem Statement (Recorded)
In the current S0 6-arm setup, **RAG/Thinking are labeled in ARM_CONFIGS but not propagated** to LLM calls, nor logged in output metadata. Consequently, B/D (RAG) and C/D (Thinking) behave identically to baseline, invalidating arm comparisons.

---

## 3. Decision
Adopt **Option B**: implement real retrieval and real thinking control, with deterministic logging sufficient for audit and IRB-grade verification.

---

## 4. Acceptance Criteria (Binding)
The following **must** be true for every JSONL record before S0 full runs:

### 4.1 Metadata (Minimum Required)
- **Arm Trace:** `arm`, `provider`, `model_stage1`, `model_stage2`, `run_tag`, `mode`
- **Thinking:** `thinking_enabled` (bool), `thinking_budget` (int/str)
- **RAG:** `rag_enabled` (bool), `rag_mode` (enum), `rag_queries_count` (int), `rag_sources_count` (int)
- **Performance:** `latency_sec_stage1`, `latency_sec_stage2` (or total); tokens best-effort

**Minimum pass:** For **B/D**, `rag_enabled=true` **and** `rag_sources_count > 0`.

### 4.2 Observable Arm Differences
- **A vs B:** retrieval presence/counts differ
- **A vs C:** thinking budget/mode differ
- **D:** both RAG and Thinking enabled and logged

---

## 5. Implementation Requirements (Normative)

### 5.1 Ordering (P0)
- **P0-1:** Always record RAG/Thinking flags and placeholders in metadata
- **P0-2:** Record latency (stage-wise); tokens where available
- **P0-3:** Apply Thinking via provider-supported parameters (budgeted)
- **P0-4:** Execute RAG with counts; store audit separately for blinding

### 5.2 RAG Architecture (Required)
- Retrieval **must** execute when `rag_enabled=true`
- Evidence is inserted into an **AUTHORITATIVE CONTEXT** section (not card text)
- **Audit separation:** store `rag_audit` outside distributable payloads; record only path/summary in metadata

### 5.3 Thinking Control (Required)
- When enabled, **explicit budget** is applied
- When disabled, **budget=0 or minimal** is enforced
- Applied values **must match metadata** (no silent ignore)

---

## 6. Verification Procedure (Binding)
- Run smoke: sample=1 across 6 arms
- Confirm metadata presence and non-null counts
- Console proof (temporary): `[RAG] queries=.. sources=..` and `[THINK] budget=..`
- Failure modes are judged **by metadata**, not wall-time alone

---

## 7. Prohibition
**Do not start** S0 full runs (e.g., 18 groups × 6 arms × 12 cards) until all Acceptance Criteria pass.

---

## 8. Change Control
This addendum is **Frozen**. Changes require protocol update with versioned addendum.


# Objective Source Traceability Specification

**Document Type:** Canonical Governance Specification  
**Applies to:** MeducAI (Upstream → Group Canonical → S1/S2/S3/S4)  
**Status:** Active  
**Version:** v1.0  
**Last Updated:** 2025-12-18  
**Location:** 0_Protocol/00_Governance/Objective_Source_Traceability_Spec.md

---

## 1. Purpose

This document defines the canonical rules for tracing every learning **Objective** used in MeducAI
back to its authoritative **source documents**.  
Its purpose is to ensure explainability, reproducibility, and governance compliance
(MI-CLEAR-LLM, IRB, expert QA).

Every Objective must be answerable to the question:

> “Why does this Objective exist in MeducAI?”

within one minute, using documented evidence.

---

## 2. Scope

This specification applies to:

- All `objective_bullets`
- All Objectives included in `group_canonical`
- All Objectives passed into S1 / S2 / S3 prompts
- All Objectives referenced in QA or analysis stages

---

## 3. Source Taxonomy

### 3.1 Primary Sources (Authoritative)

Official documents defining scope or content.

| source_id | Description |
|----------|------------|
| SRC_KSR_CUR_2018 | Korean Society of Radiology Residency Curriculum (2018) |
| SRC_KSR_EXAM_2026 | 2026 Board Exam Plan & Weight Table |

Primary sources define **what may exist** as an Objective.

---

### 3.2 Derived Sources

Artifacts derived from primary sources.

Examples:
- Parsed PDF tables
- Keyword extraction tables
- Translated objective lists
- Scope-mapping spreadsheets

Derived sources must always reference a primary source.

---

### 3.3 Interpretive Layers

Human or LLM-based transformations applied to objectives.

Examples:
- Korean → English translation
- Sentence compression or restructuring
- Removal of difficulty labels (B/A/S)
- Group-level abstraction

Interpretive layers are not sources; they are recorded transformations.

---

## 4. Mandatory Traceability Fields

Each Objective MUST carry the following metadata:

```json
{
  "objective_id": "OBJ_000123",
  "objective_text_ko": "...",
  "objective_text_en": "...",
  "source": {
    "primary_source_id": "SRC_KSR_CUR_2018",
    "location": {
      "section": "IV. Specific Educational Objectives",
      "subsection": "Chest Radiology",
      "page": 105
    }
  },
  "derivation": {
    "translated": true,
    "translation_method": "LLM-assisted",
    "difficulty_label_removed": true,
    "sentence_restructured": false
  }
}
```

---

## 5. Difficulty Labels (B / A / S)

### 5.1 Principle

- B / A / S indicate **training stage**, not exam weight or difficulty.
- They do not alter the semantic meaning of an Objective.

### 5.2 Enforcement Rules

| Stage | Rule |
|-----|-----|
| Upstream parsing | Preserve as metadata only |
| objective_bullets | Remove |
| group_canonical | Prohibited |
| QA / analysis | Optional reference |

Removal must be explicitly recorded.

---

## 6. Relationship to Board Exam Plan

| Document | Role |
|--------|------|
| Curriculum | Defines *what* should be learned |
| Board Exam Plan | Defines *how much* is tested |

Rules:
- Objectives must NOT include exam weight.
- Weighting is applied only at **group level**, never at Objective level.

---

## 7. Group-Level Traceability

Groups aggregate Objectives but do not replace Objective traceability.

```json
{
  "group_id": "GRP_CHEST_PULMONARY",
  "source_summary": {
    "primary_sources": ["SRC_KSR_CUR_2018"],
    "exam_weight_source": "SRC_KSR_EXAM_2026"
  },
  "objectives": ["OBJ_000121", "OBJ_000122"]
}
```

---

## 8. MI-CLEAR-LLM Alignment

This specification ensures:

- Explicit source attribution
- Transparent LLM involvement
- Reproducible upstream decisions
- Human-auditable Objective provenance

---

## 9. Anti-Patterns (Violations)

The following are strictly prohibited:

- Objectives without primary sources
- Altering objectives based on perceived exam importance
- Treating B/A/S as difficulty or weight
- Injecting exam ratios into objective text

---

## 10. Canonical Rule

> An Objective exists in MeducAI **only if** its origin, transformation,
> and justification are explicitly documented.

---

**Canonical Location:**  
`0_Protocol/00_Governance/Objective_Source_Traceability_Spec.md`

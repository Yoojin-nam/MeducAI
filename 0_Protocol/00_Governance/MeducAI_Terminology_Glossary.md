# MeducAI Terminology Glossary (Canonical)

**Path**
`00_Governance/MeducAI_Terminology_Glossary.md`

**Status:** Canonical · Frozen
**Applies to:** All MeducAI documents, code, protocols, IRB submissions, and publications
**Last Updated:** 2025-12-17

---

## 1. Purpose (Normative)

This document defines the **single authoritative glossary of terms** used across the MeducAI project.

Its purpose is to:

* eliminate ambiguity in internal development
* ensure consistency across Canonical documents
* support IRB review, external collaboration, and peer review
* prevent silent semantic drift between code, protocol, and manuscript text

> **Any interpretation of MeducAI documents MUST follow the definitions in this glossary.**
> Conflicting informal usage is considered non-authoritative.

---

## 2. Scope

This glossary governs terminology used in:

* Pipeline documentation (S0–S4, FINAL)
* Canonical policies and contracts
* Code (variable names, comments, logs)
* IRB protocols and consent materials
* Manuscripts, supplements, and reviewer responses

---

## 3. Core Structural Units

### 3.1 Group

**Definition (Authoritative)**
A **Group** is the highest-level curricular unit in MeducAI, representing a coherent medical topic or concept cluster.

**Properties**

* Defined in `groups_canonical.csv` (Single Source of Truth)
* Stable and frozen once Canonical
* Owns learning objectives, not card counts

**Notes**

* Groups exist independently of experimental arms
* Groups are the unit of quota ownership in FINAL allocation

---

### 3.2 Set

**Definition (S0-only)**
A **Set** is a single execution instance defined as:

```
Set = Group × Arm
```

**Scope**

* Exists **only in Step S0**
* Used exclusively for QA and model comparison

**Notes**

* Sets do NOT exist in FINAL
* Card count in S0 is fixed per set (q = 12)

---

### 3.3 Entity

**Definition (Authoritative)**
An **Entity** is an abstract execution unit derived from a Group, representing a sub-concept that S2 can operate on.

**Properties**

* Defined by S1 (structure-only)
* Immutable once passed to S2
* Has no inherent importance, quota, or weight

**Explicit Non-Properties**

* ❌ Does NOT own card counts
* ❌ Does NOT imply educational priority
* ❌ Does NOT correspond to learner-facing structure

---

## 4. Content Units

### 4.1 Card

**Definition (Authoritative)**
A **Card** is a single Anki-compatible learning item with a `front`, `back`, and `card_type`.

**Properties**

* Generated in S2
* Selected or rejected in S3
* Rendered (optionally) in S4

**Notes**

* Cards are the smallest learner-facing unit
* Cards never decide their own importance or count

---

### 4.2 Payload

**Definition (Context-dependent)**

The term **Payload** refers to a **fixed bundle of cards** executed as a unit.

| Context   | Meaning                                  |
| --------- | ---------------------------------------- |
| **S0**    | Fixed set-level card bundle (q = 12)     |
| **FINAL** | Not used (replaced by quota terminology) |

**Important**

* “Payload” must NOT be used to describe FINAL allocation results
* Payload does not imply optimization or weighting

---

## 5. Count & Allocation Terminology

### 5.1 Allocation

**Definition (Strict)**
**Allocation** is the **only process allowed to decide card counts**, and it exists in two **completely disjoint forms**.

#### S0 Allocation

* Records a fixed payload
* Selects a representative entity
* Makes **no decisions**

#### FINAL Allocation

* Computes group-level card quotas
* Enforces global totals (e.g., TOTAL_CARDS = 6,000)
* Is the **only decision-making authority**

> Allocation is a **code responsibility**, never an LLM responsibility.

---

### 5.2 Quota

**Definition (FINAL-only)**
A **Quota** is a decision variable that specifies how many cards a Group must contain in FINAL generation.

**Properties**

* Computed only in FINAL Allocation
* Enforced downstream by S3
* Sum of all quotas equals TOTAL_CARDS

**Prohibition**

* The term “quota” must NEVER be used in S0 context

---

### 5.3 Exact Count (`cards_for_entity_exact`)

**Definition (Execution-level)**
An **Exact Count** is a binding execution instruction passed to S2:

```
Generate exactly N cards.
```

**Properties**

* Not a target
* Not a range
* Not an estimate

**Violation**

```
len(cards) ≠ N → HARD FAIL
```

---

## 6. Experimental Structure

### 6.1 Arm

**Definition (Authoritative)**
An **Arm** is a fixed experimental configuration defining:

* provider
* model resolution
* experimental factors (e.g., RAG, Thinking)

**Notes**

* Arms are immutable during a run
* Arms define experimental conditions, not execution logic

---

### 6.2 Run

**Definition**
A **Run** is a single execution instance identified by a unique `RUN_TAG`.

**Properties**

* Spans one or more arms
* Produces auditable artifacts
* Is either PASS or FAIL under Fail-Fast rules

---

## 7. Visual Terminology

### 7.1 Image Lane

**Definition**
An **Image Lane** defines the rendering intent in S4.

| Lane       | Purpose                               |
| ---------- | ------------------------------------- |
| S4_CONCEPT | Conceptual / infographic illustration |
| S4_EXAM    | Exam-style realistic imagery          |

**Notes**

* Lanes must never mix
* Lane selection is upstream-defined

---

### 7.2 Image Necessity

**Definition (Card-level)**
`row_image_necessity ∈ {IMG_REQ, IMG_OPT, IMG_NONE}`

**Authority**

* Assigned upstream
* Enforced in S3
* Rendered in S4

**Prohibition**

* S4 must not reclassify image necessity

---

## 8. Governance Terms

### 8.1 Canonical

**Definition**
A **Canonical document** is the single authoritative definition of a concept.

**Rules**

* Only one Canonical version exists at a time
* Older versions are archived, not deleted
* Canonical documents override all informal descriptions

---

### 8.2 Frozen

**Definition**
A **Frozen** document cannot be modified without:

1. Explicit versioning
2. CP re-validation
3. Canonical merge record

---

## 9. Conflict Resolution Rule (Binding)

If a term appears to have multiple meanings:

1. This glossary overrides all other documents
2. Higher-level Canonical documents override lower-level ones
3. Informal usage (code comments, discussions) is non-authoritative

---

## 10. One-Line Canonical Summary

> **This glossary defines the only valid meanings of MeducAI terms.
> Any interpretation, implementation, or explanation that deviates from these definitions is invalid.**
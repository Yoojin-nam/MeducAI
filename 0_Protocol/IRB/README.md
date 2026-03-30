# MeducAI – IRB Documentation Index

This directory contains **all official Institutional Review Board (IRB)–related documents**
for the MeducAI project.

Documents in this folder constitute the **regulatory and ethical record**
of the study and must be handled with strict version control.

---

## 1. Purpose of This Directory

The purpose of `02_IRB/` is to:

- archive all IRB-submitted materials,
- maintain a clear record of approved study design and procedures,
- document version history and amendments,
- and provide a single source of truth for regulatory review.

This directory defines **what is officially approved** versus
what exists as internal design or operational documentation elsewhere.

---

## 2. Official IRB Documents (Authoritative)

The following documents are considered **official IRB materials**.
Any modification to these documents may require IRB review or amendment.

### 2.1 Primary Research Protocol

- **IRB_Research_Protocol_MeducAI_v3.0.md**
  - Markdown archive of the IRB-approved research protocol
  - Content-equivalent to the submitted Word/PDF version
  - Used for internal reference and auditability

(Submitted Word/PDF versions are stored in secure institutional systems.)

---

### 2.2 Informed Consent Materials

- Informed consent form(s)
- Participant information sheets (if applicable)

These documents define:
- participant rights,
- data usage and protection,
- withdrawal procedures.

---

### 2.3 Survey Instruments

- Questionnaires measuring:
  - cognitive load,
  - academic self-efficacy,
  - learning satisfaction,
  - technology acceptance,
  - and related covariates.

Survey wording and scale structure are IRB-approved
and must not be altered without amendment.

---

## 3. Versioning and Amendment Policy

### 3.1 Version Naming

All IRB documents must include explicit version identifiers:
- version number (e.g., v3.0),
- date of finalization (recommended within document body).

---

### 3.2 What Constitutes an IRB-Relevant Change

The following changes **require IRB notification or amendment**:

- modification of study objectives,
- changes in inclusion/exclusion criteria,
- alterations to participant-facing procedures,
- changes to consent language,
- addition or removal of survey instruments,
- changes to data privacy or handling procedures.

---

### 3.3 What Does Not Require IRB Amendment

The following are **non-IRB operational changes**:

- internal model selection decisions,
- QA rubric refinements (expert-only),
- generation pipeline optimization,
- code refactoring,
- internal documentation updates outside participant interaction.

Such changes are documented in other directories
(e.g., `01_Study_Design/`, `04_QA_Framework/`, `05_Model_Selection/`)
but do not affect IRB approval status.

---

## 4. Relationship to Other Protocol Documents

- Conceptual study design rationale:
  - `01_Study_Design/`
- Human baseline reference protocols:
  - `03_Human_Baseline/`
- Expert QA rules and rubrics:
  - `04_QA_Framework/`
- Model selection and sample experiment planning:
  - `05_Model_Selection/`

These documents **support** the IRB protocol
but are not themselves regulatory submissions.

---

## 5. IRB Communication and Audit Trail (Recommended)

It is strongly recommended to maintain:

- an **IRB Response Log** documenting:
  - IRB questions,
  - requested clarifications,
  - investigator responses,
  - dates of approval.

This log may be stored as:
- `IRB_Response_Log.md` within this directory.

---

## 6. Access Control and Handling

- Access to this directory should be limited
  to the principal investigator and designated study staff.
- Documents should not be edited casually;
  changes must follow versioning and amendment rules.
- Public or collaborator-facing exports
  should omit internal notes and correspondence.

---

## Summary

This directory represents the **ethical and regulatory backbone**
of the MeducAI project.

It ensures that:
- participant rights are protected,
- approved procedures are clearly defined,
- and the study remains compliant, auditable, and defensible.

When in doubt, treat documents in this directory as **immutable**
unless formal IRB processes are followed.

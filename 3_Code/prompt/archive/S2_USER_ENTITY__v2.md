You will be given **entity-level inputs** derived from a validated Master Table.

Your task is to generate **exam-oriented Anki cards** for the specified entity, strictly following the instructions below.

### CONTEXT INPUTS

* **Master Table (Korean Markdown)**
  This table defines the validated scope and framing of the learning objective group.
  Do NOT introduce concepts that are not aligned with this table.

* **Target Entity**
  The entity name represents a single, focused exam concept.
  Do NOT broaden the scope beyond this entity.

* **Visual Type**
  Describes the imaging modality or visual context associated with this entity.
  Use this only to guide image necessity and prompt realism.

---

### TASK REQUIREMENTS

1. Generate **exactly `{cards_per_entity}` Anki cards** for the target entity.
2. The card-type composition MUST strictly follow the quota below:

```
{card_type_quota_lines}
```

Do NOT exceed or fall short of the requested total number of cards.
Do NOT invent additional card types.

---

### CONTENT CONSTRAINTS (VERY IMPORTANT)

* All cards must be:

  * Directly relevant to **board examinations**
  * Anchored to **commonly tested knowledge**
  * Appropriate for **active recall**

* Do NOT include:

  * Lecture-style explanations
  * Research-level nuance
  * Rare exceptions unless they are clearly high-yield

If content is marginally relevant, exclude it.

---

### ENTITY SCOPE CONTROL

* Treat the target entity as a **closed scope**.
* Do NOT:

  * Merge with related but distinct entities
  * Introduce umbrella categories
  * Expand into differential diagnoses unless explicitly high-yield

Granularity must remain consistent across all cards.

---

### IMAGE DECISION RULE

You must explicitly set `row_image_necessity` to **one of the following**:

* `IMG_REQ`
  Choose this ONLY if an image is essential for recognizing or recalling the entity in an exam context.

* `IMG_OPT`
  Choose this if an image may be helpful but is not essential.

* `IMG_NONE`
  Choose this if an image does not add meaningful exam value.

This decision must be **conservative and exam-driven**, not aesthetic.

---

### IMAGE PROMPT RULES (WHEN APPLICABLE)

If `row_image_necessity` is `IMG_REQ` or `IMG_OPT`:

* Provide a **PACS-realistic image prompt in English**.
* The image must be:

  * Clinically realistic
  * Exam-appropriate
  * Free of decorative or illustrative elements
* Do NOT include:

  * Cartoon or artistic styles
  * Overlays revealing the answer
  * Text labels that give away key facts

If `row_image_necessity` is `IMG_NONE`, set `row_image_prompt_en` to `null`.

---

### OUTPUT FORMAT (HARD)

You must return **ONLY valid JSON** with the following structure, exactly as specified:

```
{
  "entity_name": "{entity_name}",
  "importance_score": 50,
  "row_image_necessity": "IMG_REQ | IMG_OPT | IMG_NONE",
  "row_image_prompt_en": "string or null",
  "anki_cards": [ ... ]
}
```

* Do NOT add or remove keys.
* Do NOT change key names or nesting.
* Do NOT include commentary or explanation outside JSON.

Any deviation from this format is a **blocking error**.

---

### FINAL REMINDER

If you face a trade-off between:

* completeness and exam relevance
* creativity and reproducibility
* aggressiveness and medical safety

you must always choose **exam relevance, reproducibility, and safety**.
# Prompt Authoring Guideline (Canonical)

**Status:** Active
**Scope:** MeducAI Step01 (S1 / S2 prompts)
**Audience:** Prompt authors, reviewers, pipeline maintainers

---

## 1. Purpose

This document defines **mandatory authoring rules** for all prompt files used in **MeducAI Step01**.

The goal is to guarantee:
- Deterministic execution of the pipeline
- Strict JSON contract compliance
- Zero runtime failures caused by prompt formatting
- Reproducibility suitable for IRB-reviewed research

This guideline is **not optional**. Violations will cause immediate runtime failure or downstream data corruption.

---

## 2. Scope of Prompts Covered

The following prompt files are governed by this document:

- `S1_SYSTEM.md`
- `S1_USER_GROUP.md`
- `S2_SYSTEM.md`
- `S2_USER_ENTITY.md`

Any future prompt added to Step01 must comply with the same rules.

---

## 3. Execution Context (Critical)

All user-facing prompts are rendered via **Python `str.format()`** inside `01_generate_json.py`.

This has two critical implications:

1. `{}` is interpreted as a **format placeholder**
2. Unescaped JSON braces will cause **runtime `KeyError`**

Therefore, prompt content must be written with **Python string formatting semantics in mind**.

---

## 4. Brace Escaping Rule (Mandatory)

### 4.1 Core Rule

If a prompt file contains **JSON examples or JSON schema**, all braces **must be escaped**.

| Original | Required |
|--------|----------|
| `{` | `{{` |
| `}` | `}}` |

Failure to do so will result in errors such as:
```
KeyError: '\n"id"'
```

---

### 4.2 Correct Example

❌ **Incorrect (will crash):**
```json
{
  "id": "string",
  "entities": []
}
```

✅ **Correct (escaped):**
```text
{{
  "id": "string",
  "entities": []
}}
```

---

## 5. Allowed Template Variables

Only the following placeholders are allowed to remain **unescaped**:

- `{specialty}`
- `{anatomy}`
- `{modality_or_type}`
- `{category}`
- `{group_key}`
- `{group_id}`
- `{objective_bullets}`

All other braces must be escaped.

---

## 6. JSON Output Contract (High-Level)

All Step01 outputs must conform to the following **top-level structure**:

```text
{{
  "metadata": {{...}},
  "source_info": {{...}},
  "curriculum_content": {{...}}
}}
```

- No additional top-level keys are permitted
- Key renaming is forbidden
- Nesting level must not change

---

## 7. S1 (Group-Level) JSON Contract

### 7.1 Required Fields

```text
{{
  "objective_summary": "string",
  "group_objectives": ["string"],
  "visual_type_category": "string",
  "master_table_markdown_kr": "string",
  "entity_list": ["string"],
  "table_infographic_style": "string",
  "table_infographic_keywords_en": "string",
  "table_infographic_prompt_en": "string"
}}
```

### 7.2 Hard-Fail Rule

- `table_infographic_prompt_en` **must be non-empty**

Empty strings or null values will terminate Step01 execution.

---

## 8. S2 (Entity-Level) JSON Contract

### 8.1 Required Fields

```text
{{
  "entity_name": "string",
  "importance_score": 0,
  "row_image_necessity": "IMG_REQ | IMG_OPT | IMG_NONE",
  "row_image_prompt_en": "string | null",
  "anki_cards": [
    {{
      "card_type": "string",
      "front": "string",
      "back": "string",
      "tags": "string"
    }}
  ]
}}
```

### 8.2 Hard-Fail Rule

If:
```
row_image_necessity == "IMG_REQ"
```
Then:
```
row_image_prompt_en must be non-empty
```

---

## 9. Prompt Authoring Checklist (Required Before Commit)

Before committing any prompt change, verify:

- [ ] All JSON braces are escaped (`{{` `}}`)
- [ ] Only approved template variables are unescaped
- [ ] JSON keys exactly match contract
- [ ] No optional language ("may include", "if desired", etc.)
- [ ] Hard-fail fields are clearly emphasized

---

## 10. Validation Command (Mandatory)

After modifying prompts, the following command **must pass**:

```bash
RUN_TAG="S0_PROMPT_VALIDATION"
python3 3_Code/src/01_generate_json.py \
  --base_dir . \
  --mode S0 \
  --run_tag "$RUN_TAG" \
  --arm A \
  --sample 1
```

Any failure here blocks further development.

---

## 11. Final Reminder

**Prompts in MeducAI are executable contracts, not documentation.**

Incorrect formatting does not degrade output quality — it **halts the pipeline**.

When in doubt:
> Escape braces first.

---

**End of Document**


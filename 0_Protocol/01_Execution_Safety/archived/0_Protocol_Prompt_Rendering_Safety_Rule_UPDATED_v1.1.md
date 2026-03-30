# Prompt Rendering Safety Rule

**Status:** Archived · Frozen  
**Superseded by:** `0_Protocol/01_Execution_Safety/Prompt_Rendering_Safety_Rule.md`
**Do not use this file for new decisions or execution.**
**Version:** 1.1  
**Supersedes:** v1.0 (2025-12-18 initial)  
**Applies to:** Step01 (S1/S2 prompt rendering)  
**Scope:** Code + Prompt Bundle  
**Last Updated:** 2025-12-18  

---

## 0. Purpose (Normative)

Prevent Python `str.format()` failures and silent corruption when prompt templates contain JSON examples with `{}` braces.

This rule is binding for all Step01 code paths that render prompt templates.

---

## 1. Root Cause

Prompt templates often include JSON schema/examples. Python `str.format()` interprets `{}` as placeholders and raises `KeyError` (or corrupts text) when braces are not escaped.

---

## 2. Non‑Negotiable Rule (Binding)

### 2.1 Absolute Prohibition

- **Forbidden:** calling `template.format(...)` directly anywhere in Step01.
- **Forbidden:** f-string interpolation against templates that contain untrusted `{}` blocks.
- **Forbidden:** “quick fixes” (try/except swallowing, ad‑hoc brace replacement) outside the canonical renderer.

### 2.2 Required Single Rendering Function

All prompt rendering must go through a single safe function (e.g., `safe_prompt_format()` / `render_prompt()`), which:

1) escapes all braces,  
2) un-escapes only intended placeholders,  
3) formats using provided variables only,  
4) hard-fails on unknown placeholders (no silent dropping).

---

## 3. Enforcement (Recommended)

### 3.1 Code Centralization

- Centralize all prompt rendering via `safe_prompt_format()`.
- Replace any direct `.format()` calls with the canonical renderer.

### 3.2 Static Check (Fail-fast)

```bash
grep -nR '\.format\(' /path/to/workspace/workspace/MeducAI/3_Code/src/01_generate_json.py \
  && echo 'FAIL: direct .format detected (Prompt Rendering Safety Rule violation)' \
  && exit 1
```

---

## 4. TL;DR (Operational)

- Step01에서는 `str.format()`을 직접 쓰지 않는다. 프롬프트는 반드시 안전 렌더러로만 생성한다.  
- Patch delivery workflow는 `File_Replacement_Patch_Delivery_Rule_v1.1.md`를 참조한다.

---

**Frozen. Any changes require explicit version bump and governance review.**

# S2R User Prompt v1.0 — S2 Card Repair Request

**Task:** Repair the following Anki card based on S5 validation feedback.

---

## Original Card Content

### Front (Question)
```
{front_text}
```

### Back (Answer/Explanation)
```
{back_text}
```

### Options (for MCQ cards)
```
{options_list}
```

---

## S5 Validation Issues

{s5_issues_formatted}

---

## Instructions

1. **Analyze each issue** carefully:
   - Identify which field is affected (front/back/options)
   - Understand the nature of the problem (factual error, clarity issue, fairness problem, etc.)
   - Review the suggested fix (if provided)

2. **Verify corrections** using Google Search when needed:
   - For factual issues (severity: blocking/major), search for authoritative sources
   - Examples: ACR guidelines, RadioGraphics articles, anatomy atlases, pathology textbooks
   - Ensure terminology aligns with Korean radiology standards

3. **Apply minimal surgical edits**:
   - Fix ONLY the specific text mentioned in the issues
   - Preserve the card type (BASIC/MCQ) and overall structure
   - For MCQ: maintain exactly 5 options (A-E) with a single best answer
   - Keep the original writing style and tone where not flagged

4. **Generate the improved card**:
   - Return corrected front, back, and options (if MCQ)
   - Ensure the explanation (back) aligns with the correct answer
   - For MCQ: verify that distractors are plausible but clearly wrong
   - Double-check medical terminology accuracy

5. **Provide a changes summary**:
   - Briefly describe what was changed (2-3 sentences)
   - Example: "Corrected pathophysiology in back text: changed 'sweat gland' to 'sebaceous gland'. Fixed ambiguous distractor in option C."

6. **Assess your confidence**:
   - Rate your confidence in the corrections (0.0-1.0 scale)
   - Use 0.9+ for well-established facts, 0.7-0.9 for evidence-based but nuanced corrections, <0.7 for uncertain cases

---

## Output Format

Return a JSON object:

```json
{{
  "improved_front": "<corrected front text>",
  "improved_back": "<corrected back text>",
  "improved_options": ["<option A>", "<option B>", "<option C>", "<option D>", "<option E>"],
  "changes_summary": "<brief description of changes>",
  "confidence": 0.85
}}
```

**Note:** For BASIC cards, you may omit the `improved_options` field or set it to an empty list.

---

## Quality Requirements

- **Accuracy**: All corrections must be factually correct and evidence-based
- **Minimalism**: Change only what is flagged; preserve everything else
- **Clarity**: Improved text should be clearer and more exam-appropriate
- **Structure**: Card type (BASIC/MCQ) and format must be preserved
- **Language**: Maintain Korean medical terminology consistency
- **Board-Relevance**: Ensure the card remains aligned with radiology board exam style

---

## Special Notes

### For MCQ Cards
- **Exactly 5 options required** (A, B, C, D, E)
- **Single best answer** (no ambiguity)
- **Plausible distractors** (not obviously wrong, but clearly incorrect upon analysis)
- **Explanation must match** the correct answer in the back text

### For BASIC Cards
- **Clear question-answer relationship** (front asks, back answers)
- **Sufficient detail** in the back without overwhelming the learner
- **Key learning points** highlighted (e.g., pathognomonic features, DDx, exam tips)

---

## Issue Severity Guidance

- **Blocking**: Must fix (medical safety-critical error)
- **Major**: Should fix (factually incorrect or significantly misleading)
- **Minor**: May fix if straightforward (stylistic or clarity improvement)

---

**Version:** 1.0  
**Last Updated:** 2026-01-06


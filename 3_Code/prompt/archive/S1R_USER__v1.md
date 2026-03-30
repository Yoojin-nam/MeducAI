# S1R User Prompt v1.0 — S1 Table Repair Request

**Task:** Repair the following Master Table based on S5 validation feedback.

---

## Original Master Table

```markdown
{master_table_markdown_kr}
```

---

## S5 Validation Issues

{s5_issues_formatted}

---

## Instructions

1. **Analyze each issue** carefully:
   - Identify the specific row(s) and column(s) affected
   - Understand the nature of the problem (factual error, clarity issue, tone problem, etc.)
   - Review the suggested fix (if provided)

2. **Verify corrections** using Google Search when needed:
   - For factual issues (severity: blocking/major), search for authoritative sources
   - Examples: ACR BI-RADS guidelines, Fleischner Society recommendations, RadioGraphics articles
   - Ensure terminology aligns with Korean radiology standards

3. **Apply minimal surgical edits**:
   - Fix ONLY the specific cells/text mentioned in the issues
   - Preserve all entity names and their order
   - Maintain the 6-column structure and markdown formatting
   - Keep the original writing style and tone where not flagged

4. **Generate the improved table**:
   - Return the complete corrected table in markdown format
   - Ensure all rows are present in the same order
   - Double-check markdown syntax (proper pipes, alignment)

5. **Provide a changes summary**:
   - Briefly describe what was changed (2-3 sentences)
   - Example: "Fixed ambiguous DDx in row 1 (Skin Calcification), replaced absolute language '100% 양성' with 'Pathognomonic for benignity' in row 6 (Rim Calcification)"

6. **Assess your confidence**:
   - Rate your confidence in the corrections (0.0-1.0 scale)
   - Use 0.9+ for well-established facts, 0.7-0.9 for evidence-based but nuanced corrections, <0.7 for uncertain cases

---

## Output Format

Return a JSON object:

```json
{{
  "improved_table_markdown": "<full corrected table>",
  "changes_summary": "<brief description of changes>",
  "confidence": 0.85
}}
```

---

## Quality Requirements

- **Accuracy**: All corrections must be factually correct and evidence-based
- **Minimalism**: Change only what is flagged; preserve everything else
- **Clarity**: Improved text should be clearer and more exam-appropriate
- **Structure**: Table structure (rows, columns, order) must be preserved
- **Language**: Maintain Korean medical terminology consistency

---

**Note:** If an issue has `severity="minor"`, you may choose to fix it only if the correction is straightforward and does not introduce ambiguity. For `severity="blocking"` or `severity="major"`, you MUST fix the issue.

---

**Version:** 1.0  
**Last Updated:** 2026-01-06


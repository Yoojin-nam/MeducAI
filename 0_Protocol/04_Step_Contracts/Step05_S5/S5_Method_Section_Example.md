# 논문 Method 섹션 예시: LLM 기반 콘텐츠 검증 및 반복적 개선

이 문서는 논문의 Methods 섹션에 포함될 수 있는 S5 검증 및 프롬프트 개선 방법론의 예시입니다.

---

## 2.4 LLM-based Content Validation and Iterative Prompt Refinement

### Overview

To ensure the quality and accuracy of generated educational content, we implemented an LLM-as-a-judge validation system (Step 5, S5) that evaluates S1 tables and S2 cards, followed by an iterative refinement loop that updates generation prompts based on validation feedback.

### Validation System (S5)

**Validation Scope and Model**: We used Gemini 1.5 Pro as an independent judge to evaluate each generated S1 table and S2 card. The validation covers three primary dimensions:

1. **Technical Accuracy** (0.0–1.0): Factual correctness, medical accuracy, and alignment with current clinical guidelines.
2. **Educational Quality** (1–5 Likert scale): Clarity, exam-relevance, and pedagogical effectiveness.
3. **Blocking Errors** (binary): Critical issues that pose clinical safety risks or render content unsolvable.

**Validation Criteria**: The LLM judge was instructed to:
- Identify factual errors, terminology misuse, and outdated clinical information.
- Assess clarity, completeness, and exam-appropriateness of questions and explanations.
- Flag critical safety issues (e.g., incorrect diagnostic criteria, misleading imaging descriptions).
- Detect structural inconsistencies (e.g., MCQ options not matching explanations, missing distractor rationale).

**Output Schema**: Each validation result includes:
- Scores for technical accuracy and educational quality.
- A binary blocking error flag (if true, technical accuracy is automatically set to 0.0).
- A list of issues with severity, type, and actionable metadata (issue_code, recommended_fix_target, prompt_patch_hint).

**RAG-enabled Validation**: For fact-checking, we enabled Google Search grounding (RAG) during validation, allowing the judge to verify current clinical guidelines, terminology, and evidence-based recommendations.

### Iterative Refinement Loop

**Report Generation**: After validation, we aggregate results into a human-readable report that includes:
- Overall statistics (mean technical accuracy, educational quality, blocking error rate).
- Issue distribution by category (terminology, clarity, structure/consistency).
- A prioritized "patch backlog" that groups issues by recommended_fix_target and issue_code, listing specific prompt_patch_hint suggestions.

**Prompt Patching Process**: Based on the patch backlog, we systematically update generation prompts:

1. **Issue Analysis**: We identify recurring patterns (e.g., terminology misuse, structural inconsistencies) and map them to specific prompt sections.
2. **Rule Addition**: We add explicit rules to the relevant prompt files (S1_SYSTEM, S2_SYSTEM, S2_USER_ENTITY) that prevent the identified issues.
3. **Versioning**: Each prompt update increments the version number (e.g., v12 → v13), and changes are tracked in a prompt registry.

**Example Refinement Cycle**: In one iteration, we identified 4 high-priority issues:
- **QC/Administrative Terminology Confusion**: QC questions incorrectly used "진단" (diagnosis) instead of "판정" (judgment) or "평가 결과" (evaluation result). We added a rule distinguishing clinical vs. administrative terminology.
- **MCQ Option Format**: Options included redundant prefixes (e.g., "A. CTDIw" instead of "CTDIw"). We enforced clean option text without letter prefixes.
- **Incomplete Distractor Explanations**: MCQ explanations omitted rationale for some distractors. We required all 5 options (A–E) to be addressed in the explanation.
- **Terminology Specificity**: Terms like "Pruning" were misused outside their correct clinical context (Pulmonary Hypertension). We added explicit mappings for radiological sign terminology.

**Validation of Improvements**: After prompt updates, we re-ran content generation and validation to measure improvement rates. In our test run, the four high-priority issues were reduced from 9 total occurrences to 0.

### Traceability and Reproducibility

All validation outputs include:
- Run tag and revision ID for artifact traceability.
- Judge model identification (Gemini 1.5 Pro).
- Prompt version hash for reproducibility.
- Timestamp and validation criteria version.

This ensures that validation results can be traced back to specific generation runs and prompt versions, supporting reproducibility and auditability for regulatory compliance (MI-CLEAR-LLM requirements).

---

## Alternative Shorter Version (for space-constrained papers)

### 2.4 LLM-based Content Validation and Iterative Refinement

We implemented an LLM-as-a-judge validation system (S5) using Gemini 1.5 Pro to evaluate generated S1 tables and S2 cards across three dimensions: technical accuracy (0.0–1.0), educational quality (1–5 Likert), and blocking errors (binary). Validation results include issue codes, recommended fix targets, and prompt patch hints. We aggregate results into a prioritized patch backlog and systematically update generation prompts (S1_SYSTEM, S2_SYSTEM, S2_USER_ENTITY) by adding explicit rules that prevent identified issues. Each prompt update is versioned and tracked. In a test iteration, we addressed 4 high-priority issues (terminology confusion, MCQ format inconsistencies, incomplete explanations) and reduced their occurrence from 9 to 0 after prompt updates. All validation outputs include run tags, model identification, and prompt version hashes for traceability (MI-CLEAR-LLM compliance).

---

## Key Points for Authors

1. **Emphasize the systematic nature**: This is not ad-hoc editing, but a structured, traceable refinement process.
2. **Highlight the closed-loop**: Validation → Analysis → Prompt Update → Re-validation.
3. **Show concrete examples**: Include 1–2 specific examples of issues and how they were fixed.
4. **Mention reproducibility**: Traceability (run tags, version hashes) is important for regulatory compliance.
5. **Quantify improvements**: If possible, include before/after metrics (e.g., "reduced from 9 to 0 occurrences").

---

## Integration into Full Methods Section

This subsection would typically appear after:
- Section 2.1: Dataset and Learning Objectives
- Section 2.2: Content Generation Pipeline (S1, S2)
- Section 2.3: Image Generation (S3, S4)

And before:
- Section 2.5: Human Evaluation Protocol
- Section 2.6: Statistical Analysis

---

## References to Include

- LLM-as-a-judge methodology: Liu et al. (2023) G-Eval, Zheng et al. (2023) MT-Bench
- Iterative refinement: Madaan et al. (2023) Self-Refine, Shinn et al. (2023) Reflexion
- RAG for validation: Gao et al. (2023) RARR
- MI-CLEAR-LLM: Model identification and traceability requirements


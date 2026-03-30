# npj Digital Medicine (Nature Portfolio) Flowchart & Diagram Design Guide

**Target Scope:** Paper 1, 2, 3 Architecture figures, S0-S6 Pipeline Diagrams, CONSORT Patient flowcharts.
**Goal:** Align all diagrammatic assets perfectly with **npj Digital Medicine** artwork and formatting guidelines.

## 1. Nature Portfolio Tooling & Formatting Requirements
*   **Format:** Export final diagrams as **PDF or EPS** (Vector formats are required for flowcharts). JPEG/PNG are only for photographs/scans, not node diagrams.
*   **Color Profile:** sRGB is preferred for npj Digital Medicine (being an online-only journal), but CMYK conversion-safe palettes are best.
*   **Width:** 
    *   Single-column figure: **89 mm** (max).
    *   Two-column figure: **183 mm** (max).
    *   (Rule of thumb: Design at exactly 89mm or 183mm width in Illustrator, don't just "scale down").
*   **Maximum Depth (Height):** 247 mm.

## 2. npj / Nature Aesthetic & Color Palette
*   **Line Weights:** Minimum 0.5 pt, ideally **0.5 pt to 1.0 pt**. Do not use heavy borders (>1.5pt).
*   **Color Rules:** Use clean colorblind-safe tones. Nature prefers minimal background fills and stark black/charcoal lines. 
    *   Primary Outline/Text: `Black` or `Dark Charcoal (#333333)`.
    *   Emphasis Fill: `Blue (#0072B2)` or `Teal (#009E73)`.
    *   Error/Reject Fill: `Vermillion (#D55E00)`.
    *   *Avoid*: Drop shadows, 3D effects, gradients, and purely decorative textures.

## 3. Typography Rules (Strict)
*   **Font Family:** **Arial** or **Helvetica** only.
*   **Font Sizes:** 
    *   Must be between **5 pt and 8 pt** at actual size (89mm/183mm).
    *   Do NOT use 10pt or 12pt fonts—they look gigantic in final print format.
*   **Capitalization:** Use sentence case ("Image generation phase" not "Image Generation Phase"). Only capitalize proper nouns and the first letter.
*   **Alignment:** Meticulous mathematical alignment (Center or Left).

## 4. Pipeline Specifics (S0 to S6)
When drawing the S0-S6 MeducAI pipeline:
1.  **Modularity**: Visually separate the "Canonical Rule Engine" (Governance docs) from the "Execution Engine" (LLM/Python). Use a dashed box (`#6B7280`) to represent the protocol boundary.
2.  **LLM Representation**: Use a consistent, simple AI/Robot line-art icon for Gemini/Nano-Banana steps. Do not use random generic server icons.
3.  **Fail-Fast Loop**: Always depict the S5 Validation cycle as a loop returning to S4 with a distinct red line (`#991B1B`) or caution marker that indicates strict protocol abort conditions.

## 5. Review Checklist for Co-Authors
- [ ] Are all lines perfectly orthogonal (90 degrees) or using clean 45-degree bezier curves?
- [ ] Is there identical padding inside all text boxes?
- [ ] Are all pure red/green/blue colors eliminated?
- [ ] Can the diagram be understood in grayscale? (Crucial for printed journals, rely on contrast and stroke patterns).

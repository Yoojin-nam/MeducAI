TASK:
Generate a SINGLE 16:9 comparison-style radiology teaching slide from the master table.

DESIGN INTENT:
- Split-screen / side-by-side comparison that mirrors exam "differentiation logic".
- Use 2–4 major columns or vertical panels when appropriate.
- Emphasize "key differentiators" and "시험포인트" per entity.

MANDATORY LAYOUT OPTIONS (choose ONE that best fits the table):
A) 3-panel vertical split (Left vs Center vs Right).
B) 2×2 comparison grid with consistent panel templates.
C) Aligned comparison rows: each row = one entity, columns = differentiator axes.

EACH PANEL MUST INCLUDE:
- Entity name (English, bold)
- 1–2 representative grayscale radiology images (PACS-like appearance)
- 2–4 keywords (English)
- 1 boxed "시험포인트" (Korean, one line)

STYLE:
- Primarily grayscale imaging; subtle cyan/yellow overlays allowed for highlights only.
- Clean white background; dark title bar.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.


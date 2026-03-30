TASK:
Generate a SINGLE 16:9 "sign collection" teaching slide from the master table.

DESIGN INTENT:
- A grid of classic radiology signs.
- Each cell: sign name + one representative image + 1-line definition keyword set.

EACH SIGN CELL MUST INCLUDE:
- Sign name (English, bold)
- 1 grayscale radiology image (PACS-like)
- 1–2 keywords (English)
- 1 "시험포인트" (Korean one-liner)

STYLE:
- Uniform grid; consistent sizing; subtle highlight overlays allowed.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.


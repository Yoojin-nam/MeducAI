TASK:
Generate a SINGLE 16:9 pathology-pattern teaching slide from the master table.

DESIGN INTENT:
- Pattern recognition first.
- Use 2×2 or 3×2 grid of entities/patterns.
- Each panel includes 1 representative images and key distribution/sequence keywords.

PANEL TEMPLATE:
- Entity name (English)
- Key imaging pattern keywords (English)
- 1 boxed "시험포인트" (Korean one-liner)
- Optional subtle highlight overlay.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.


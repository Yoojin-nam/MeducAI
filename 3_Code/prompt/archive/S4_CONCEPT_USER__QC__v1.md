TASK:
Generate a SINGLE 16:9 QC/quality-control teaching slide from the master table.

DESIGN INTENT:
- Checklist/metrics layout (clean dashboard feel).
- Include acceptability ranges ONLY if present in the table.
- Show failure causes and corrective actions as short bullets.

MANDATORY:
- "QC metric" list (English keywords)
- "시험포인트" box (Korean one-liner)

RULES:
- No invented thresholds.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.


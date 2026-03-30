TASK:
Generate a SINGLE 16:9 equipment-focused radiology teaching slide from the master table.

DESIGN INTENT:
- Schematic of the device/workflow components + a compact parameter table.
- Emphasize artifacts/limitations and indications if present.

MANDATORY:
- A labeled schematic block (English component names).
- A small "시험포인트" box (Korean one-liner) with a common pitfall.

RULES:
- Do NOT invent parameter values not in the table.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.


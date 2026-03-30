TASK:
Generate a SINGLE 16:9 "pattern collection" slide: group multiple entities into a small number of named patterns.

DETERMINISTIC EXPANSION RULES:
- 3–5 pattern buckets allowed, but total expanded items still capped by top-N rule (max 6).
- Expand ONLY the first 4–6 rows from the master table (in table order).
- If table has > 6 rows, render remaining entities in a compact "Others" section.

DESIGN INTENT:
- 3–5 pattern buckets (Pattern 1, 2, 3…).
- Each bucket contains mini-items (name + 1 keyword + tiny icon if helpful).
- Bucket headers must be short.

RULES:
- Bucketing must be defensible using the table wording; do NOT invent a new taxonomy.
- Keep bucket labels short.
- Mini-items: entity name + 1 keyword (+ tiny icon if helpful).
- Do NOT render the markdown table as a table.

VISUAL REQUIREMENTS:
- Large fonts, readable when downscaled.
- Clean white background, ample whitespace.

INPUT (AUTHORITATIVE; READ-ONLY):
Group ID: {group_id}
Group Path: {group_path}
Visual Type Category: {visual_type_category}

MASTER TABLE (use ONLY this content):
{master_table_markdown_kr}

OUTPUT:
Return IMAGE ONLY.


#!/usr/bin/env python3
"""
post-compact-restore.py — MeducAI Session Restore Hook

Triggered after context window compression. Reads the saved state from
pre-compact and injects a resume summary into the conversation.

Hook type: PostCompact
Event: Reads .claude/manuscript_state.json and .claude/session_resume.md
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

def main():
    # Read hook event from stdin
    try:
        event = json.load(sys.stdin)
    except Exception:
        event = {}

    project_root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    state_file = project_root / ".claude" / "manuscript_state.json"
    resume_file = project_root / ".claude" / "session_resume.md"

    if not state_file.exists():
        # No saved state — nothing to restore
        output = {
            "type": "text",
            "text": ""
        }
        print(json.dumps(output))
        return

    with open(state_file) as f:
        state = json.load(f)

    saved_at = state.get("timestamp", "unknown time")
    current_phase = state.get("current_phase")
    current_section = state.get("current_section", "unknown")
    pending_issues = state.get("pending_issues", [])
    last_files = state.get("last_modified_files", [])
    word_counts = state.get("word_counts", {})

    # Build restore message
    lines = [
        "## ⚡ Session Restored After Context Compression",
        "",
        f"**Saved at:** {saved_at}",
        "",
    ]

    if current_phase is not None:
        phase_names = {
            0: "Phase 0: Project Init",
            1: "Phase 1: Outline",
            2: "Phase 2: Tables & Figures",
            3: "Phase 3: Methods",
            4: "Phase 4: Results",
            5: "Phase 5: Discussion",
            6: "Phase 6: Introduction & Abstract",
            7: "Phase 7: Polish"
        }
        phase_label = phase_names.get(current_phase, f"Phase {current_phase}")
        lines.append(f"**Last active phase:** {phase_label} — {current_section}")
        lines.append("")

    if word_counts:
        lines.append("**Word counts at save:**")
        for section, count in word_counts.items():
            lines.append(f"  - {section}: {count} words")
        lines.append("")

    if last_files:
        lines.append("**Recently modified files:**")
        for f in last_files[-5:]:  # Show last 5
            lines.append(f"  - `{f}`")
        lines.append("")

    if pending_issues:
        lines.append("**Pending critic issues (must resolve):**")
        for issue in pending_issues:
            lines.append(f"  - {issue}")
        lines.append("")

    if resume_file.exists():
        with open(resume_file) as f:
            resume_content = f.read().strip()
        if resume_content:
            lines.append("**Resume notes:**")
            lines.append(resume_content)
            lines.append("")

    lines.append("---")
    lines.append("*Context was compressed. Review saved state above before continuing.*")

    output = {
        "type": "text",
        "text": "\n".join(lines)
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()

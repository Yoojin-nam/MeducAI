#!/usr/bin/env python3
"""
context-monitor.py — MeducAI Context Window Monitor Hook

Monitors context window usage and warns at 60% and 75% utilization.
Suggests saving manuscript state before compression occurs.

Hook type: PostToolUse
Fires after every tool use to check context window usage.
"""

import json
import sys
import os
from pathlib import Path


WARN_60_THRESHOLD = 0.60
WARN_75_THRESHOLD = 0.75
CRITICAL_THRESHOLD = 0.85

# Track whether we've already warned in this session
# (use a temp file to avoid repeated warnings)
def get_warned_levels(project_root: Path) -> set:
    warn_file = project_root / ".claude" / ".context_warnings.json"
    if warn_file.exists():
        try:
            with open(warn_file) as f:
                return set(json.load(f).get("warned", []))
        except Exception:
            pass
    return set()


def set_warned_level(project_root: Path, level: str):
    warn_file = project_root / ".claude" / ".context_warnings.json"
    warn_file.parent.mkdir(parents=True, exist_ok=True)
    warned = get_warned_levels(project_root)
    warned.add(level)
    with open(warn_file, "w") as f:
        json.dump({"warned": list(warned)}, f)


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"type": "text", "text": ""}))
        return

    # Extract context window usage from event
    # Claude Code passes context_window stats in some hook events
    usage = event.get("context_window", {})
    tokens_used = usage.get("tokens_used", 0)
    tokens_max = usage.get("tokens_max", 0)

    if tokens_max == 0:
        print(json.dumps({"type": "text", "text": ""}))
        return

    ratio = tokens_used / tokens_max
    project_root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    warned = get_warned_levels(project_root)

    message = ""

    if ratio >= CRITICAL_THRESHOLD and "critical" not in warned:
        message = (
            f"⚠️ **Context window {ratio*100:.0f}% full** — compression imminent!\n\n"
            "**Save your work now:**\n"
            "1. Note which phase/section you are in\n"
            "2. List any unresolved critic issues\n"
            "3. Type `/compact` when ready\n\n"
            "State will be saved automatically by pre-compact hook."
        )
        set_warned_level(project_root, "critical")
        set_warned_level(project_root, "75")
        set_warned_level(project_root, "60")

    elif ratio >= WARN_75_THRESHOLD and "75" not in warned:
        message = (
            f"📊 **Context window {ratio*100:.0f}% full** — approaching compression.\n\n"
            "Consider saving manuscript state soon. "
            "Complete the current section before context is compressed."
        )
        set_warned_level(project_root, "75")
        set_warned_level(project_root, "60")

    elif ratio >= WARN_60_THRESHOLD and "60" not in warned:
        message = (
            f"📈 Context window {ratio*100:.0f}% full. "
            "If writing a long section, consider wrapping up before compression."
        )
        set_warned_level(project_root, "60")

    output = {"type": "text", "text": message}
    print(json.dumps(output))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
pre-compact.py — MeducAI Pre-Compact Session Save Hook

Triggered before context window compression. Saves current manuscript
writing state to .claude/manuscript_state.json and creates a compact
summary in .claude/session_resume.md.

Hook type: PreCompact
"""

import json
import sys
import os
import glob
from datetime import datetime
from pathlib import Path


def count_words_in_file(filepath: str) -> int:
    """Count approximate words in a .qmd or .tex file (ignores LaTeX commands)."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        # Remove YAML frontmatter
        if content.startswith('---'):
            end = content.find('---', 3)
            if end > 0:
                content = content[end+3:]
        # Simple word count (rough approximation)
        words = len(content.split())
        return words
    except Exception:
        return 0


def get_recently_modified_files(project_root: Path, hours: int = 4) -> list:
    """Find files modified in the last N hours."""
    import time
    cutoff = time.time() - (hours * 3600)
    recent = []

    # Check manuscript files
    patterns = [
        "7_Manuscript/**/*.qmd",
        "7_Manuscript/**/*.tex",
        "7_Manuscript/**/*.md",
        "analysis/scripts/*.py",
        "analysis/scripts/*.R",
    ]

    for pattern in patterns:
        for filepath in glob.glob(str(project_root / pattern), recursive=True):
            if os.path.getmtime(filepath) > cutoff:
                # Make relative to project root
                rel_path = os.path.relpath(filepath, project_root)
                recent.append(rel_path)

    return sorted(recent)[:10]  # Return at most 10


def detect_current_phase(project_root: Path) -> tuple:
    """Try to detect current write-paper phase from existing files."""
    manuscript_dir = project_root / "7_Manuscript" / "drafts"

    # Check which sections exist and have content
    section_files = {
        "methods": ["methods.qmd", "methods.tex"],
        "results": ["results.qmd", "results.tex"],
        "discussion": ["discussion.qmd", "discussion.tex"],
        "introduction": ["introduction.qmd", "introduction.tex"],
        "abstract": ["abstract.qmd", "abstract.tex"],
    }

    sections_present = []
    for section, filenames in section_files.items():
        for fname in filenames:
            for root, dirs, files in os.walk(manuscript_dir):
                if fname in files:
                    filepath = os.path.join(root, fname)
                    if os.path.getsize(filepath) > 100:  # Non-empty
                        sections_present.append(section)
                        break

    # Infer phase from which sections exist
    if "abstract" in sections_present and "introduction" in sections_present:
        phase = 7  # Polish phase
        section = "abstract/introduction"
    elif "introduction" in sections_present:
        phase = 6
        section = "introduction"
    elif "discussion" in sections_present:
        phase = 5
        section = "discussion"
    elif "results" in sections_present:
        phase = 4
        section = "results"
    elif "methods" in sections_present:
        phase = 3
        section = "methods"
    else:
        phase = 2
        section = "tables/figures"

    return phase, section


def get_word_counts(project_root: Path) -> dict:
    """Get word counts for each manuscript section."""
    manuscript_dir = project_root / "7_Manuscript"
    counts = {}

    section_patterns = {
        "methods": ["**/methods.qmd", "**/methods.tex"],
        "results": ["**/results.qmd", "**/results.tex"],
        "discussion": ["**/discussion.qmd", "**/discussion.tex"],
        "introduction": ["**/introduction.qmd", "**/introduction.tex"],
        "abstract": ["**/abstract.qmd", "**/abstract.tex"],
    }

    for section, patterns in section_patterns.items():
        for pattern in patterns:
            matches = glob.glob(str(manuscript_dir / pattern), recursive=True)
            if matches:
                counts[section] = count_words_in_file(matches[0])
                break

    return counts


def main():
    # Read hook event from stdin
    try:
        event = json.load(sys.stdin)
    except Exception:
        event = {}

    project_root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    state_dir = project_root / ".claude"
    state_dir.mkdir(parents=True, exist_ok=True)

    state_file = state_dir / "manuscript_state.json"
    resume_file = state_dir / "session_resume.md"

    # Detect current state
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_phase, current_section = detect_current_phase(project_root)
    word_counts = get_word_counts(project_root)
    last_modified = get_recently_modified_files(project_root)

    # Load existing state to preserve pending_issues
    pending_issues = []
    if state_file.exists():
        try:
            with open(state_file) as f:
                old_state = json.load(f)
            pending_issues = old_state.get("pending_issues", [])
        except Exception:
            pass

    # Build new state
    state = {
        "timestamp": timestamp,
        "current_phase": current_phase,
        "current_section": current_section,
        "word_counts": word_counts,
        "last_modified_files": last_modified,
        "pending_issues": pending_issues,
        "project_root": str(project_root),
    }

    # Save state
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

    # Build resume summary
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

    total_words = sum(word_counts.values())
    phase_label = phase_names.get(current_phase, f"Phase {current_phase}")

    resume_lines = [
        f"# Session State — Saved {timestamp}",
        "",
        f"**Active phase:** {phase_label} — working on {current_section}",
        f"**Total words:** ~{total_words:,}",
        "",
    ]

    if word_counts:
        resume_lines.append("**Section word counts:**")
        for section, count in word_counts.items():
            if count > 0:
                resume_lines.append(f"  - {section}: ~{count:,} words")
        resume_lines.append("")

    if last_modified:
        resume_lines.append("**Recently modified:**")
        for f in last_modified[:5]:
            resume_lines.append(f"  - {f}")
        resume_lines.append("")

    if pending_issues:
        resume_lines.append("**Pending critic issues:**")
        for issue in pending_issues:
            resume_lines.append(f"  - {issue}")
        resume_lines.append("")

    resume_lines.append("---")
    resume_lines.append("*To resume: continue from the active phase above.*")

    with open(resume_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(resume_lines))

    # Print summary to console
    print(f"\n📦 Pre-compact save complete — {timestamp}")
    print(f"   Phase: {phase_label} ({current_section})")
    print(f"   Words: ~{total_words:,} total")
    if last_modified:
        print(f"   Last modified: {last_modified[0]}")
    print(f"   State saved to: .claude/manuscript_state.json\n")

    # Return empty response (hook doesn't inject text)
    output = {"type": "text", "text": ""}
    print(json.dumps(output))


if __name__ == "__main__":
    main()

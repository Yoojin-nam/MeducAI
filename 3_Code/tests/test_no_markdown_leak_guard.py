#!/usr/bin/env python3
"""
Regression tests for "no-markdown-leak" guardrails in S3 TABLE_VISUAL prompt construction.

Focus:
- markdown tables must be converted into pipe-free plain rows
- prompt-level markdown-table signatures should be detectable
"""

import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

import importlib.util

# Load 03_s3_policy_resolver
s3_spec = importlib.util.spec_from_file_location("s3_policy_resolver", src_dir / "03_s3_policy_resolver.py")
s3_spec = s3_spec  # keep name stable for linters
assert s3_spec is not None and s3_spec.loader is not None
s3_policy_resolver = importlib.util.module_from_spec(s3_spec)
s3_spec.loader.exec_module(s3_policy_resolver)


def test_markdown_table_to_plain_rows_has_no_pipes():
    md = "| A | B |\n| --- | --- |\n| x | y |\n"
    plain = s3_policy_resolver.markdown_table_to_plain_rows(md, strip_korean=False)
    assert "|" not in plain, f"plain rows should be pipe-free, got: {plain!r}"


def test_detect_markdown_table_leak_finds_separator_and_row():
    prompt = "Header\n| A | B |\n| --- | --- |\n| x | y |\nFooter\n"
    findings = s3_policy_resolver._detect_markdown_table_leak(prompt)
    assert "contains_markdown_table_separator('|---')" in findings
    assert "contains_markdown_table_row_line" in findings


def test_allowed_text_block_does_not_inject_pipe_separator():
    blk = s3_policy_resolver._format_allowed_text_block(
        allowed_text_en=["CT", "MRI"],
        allowed_text_kr=[],
        exam_point_tokens_by_entity={"Entity1": ["tokenA", "tokenB"]},
    )
    assert " | " not in blk, f"ALLOWED_TEXT block should not include ' | ' separators, got: {blk!r}"



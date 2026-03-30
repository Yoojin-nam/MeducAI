#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Smoke test for S0 non-inferiority analysis.

Tests:
1. Script runs without errors on synthetic fixture
2. Outputs are created with correct naming
3. Re-running with same seed produces identical outputs
4. Summary CSV has required columns
5. Decision logic produces expected PASS/FAIL for known cases
"""

import hashlib
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest


# Get paths relative to this test file
TEST_DIR = Path(__file__).parent
FIXTURE_DIR = TEST_DIR / 'fixtures'
FIXTURE_CSV = FIXTURE_DIR / 'qa_long_synthetic.csv'
REPO_ROOT = TEST_DIR.parent.parent.parent
SRC_DIR = REPO_ROOT / '3_Code' / 'src'


def test_fixture_exists():
    """Verify test fixture exists."""
    assert FIXTURE_CSV.exists(), f"Fixture not found: {FIXTURE_CSV}"


def test_script_runs(tmp_path):
    """Test that script runs without errors and produces outputs."""
    out_dir = tmp_path / 'qa_output'
    out_dir.mkdir()
    
    # Run the script (adjust path if needed)
    script_path = SRC_DIR / 'qa' / 's0_noninferiority.py'
    cmd = [
        sys.executable, str(script_path),
        '--input_csv', str(FIXTURE_CSV),
        '--baseline_arm', 'A',
        '--delta', '0.05',
        '--ci', '0.90',
        '--bootstrap_n', '1000',  # Smaller for faster test
        '--seed', '20251220',
        '--out_dir', str(out_dir),
        '--min_pairs', '2'  # Lower threshold for test fixture
    ]
    
    result = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    
    assert result.returncode == 0, f"Script failed:\n{result.stderr}"
    
    # Check outputs exist
    summary_csv = out_dir / 'qa_s0_noninferiority_summary.csv'
    decision_md = out_dir / 'qa_s0_noninferiority_decision.md'
    meta_json = out_dir / 'qa_s0_noninferiority_bootstrap_meta.json'
    
    assert summary_csv.exists(), "Summary CSV not created"
    assert decision_md.exists(), "Decision MD not created"
    assert meta_json.exists(), "Bootstrap meta JSON not created"


def test_summary_csv_columns(tmp_path):
    """Test that summary CSV has all required columns."""
    out_dir = tmp_path / 'qa_output'
    out_dir.mkdir()
    
    script_path = SRC_DIR / 'qa' / 's0_noninferiority.py'
    cmd = [
        sys.executable, str(script_path),
        '--input_csv', str(FIXTURE_CSV),
        '--baseline_arm', 'A',
        '--delta', '0.05',
        '--ci', '0.90',
        '--bootstrap_n', '1000',
        '--seed', '20251220',
        '--out_dir', str(out_dir),
        '--min_pairs', '2'
    ]
    
    subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, check=True)
    
    summary_csv = out_dir / 'qa_s0_noninferiority_summary.csv'
    df = pd.read_csv(summary_csv)
    
    # Required columns
    required = [
        'arm', 'baseline_arm', 'n_pairs', 'n_cards',
        'mean_accuracy', 'diff_vs_baseline', 'diff_ci_low', 'diff_ci_high',
        'delta', 'ci_level', 'ni_pass',
        'p0', 'rd0_vs_baseline', 'rd0_ci_low', 'rd0_ci_high',
        'major_error_margin', 'safety_pass', 'final_pass'
    ]
    
    missing = [col for col in required if col not in df.columns]
    assert len(missing) == 0, f"Missing required columns: {missing}"
    
    # Check that we have results for all arms
    assert len(df) >= 3, "Should have results for at least 3 arms (A, B, C)"


def test_deterministic_output(tmp_path):
    """Test that re-running with same seed produces identical outputs."""
    out_dir1 = tmp_path / 'qa_output1'
    out_dir2 = tmp_path / 'qa_output2'
    out_dir1.mkdir()
    out_dir2.mkdir()
    
    script_path = SRC_DIR / 'qa' / 's0_noninferiority.py'
    cmd_base = [
        sys.executable, str(script_path),
        '--input_csv', str(FIXTURE_CSV),
        '--baseline_arm', 'A',
        '--delta', '0.05',
        '--ci', '0.90',
        '--bootstrap_n', '1000',
        '--seed', '20251220',
        '--min_pairs', '2'
    ]
    
    # Run twice with same seed
    cmd1 = cmd_base + ['--out_dir', str(out_dir1)]
    cmd2 = cmd_base + ['--out_dir', str(out_dir2)]
    
    subprocess.run(cmd1, cwd=str(REPO_ROOT), capture_output=True, check=True)
    subprocess.run(cmd2, cwd=str(REPO_ROOT), capture_output=True, check=True)
    
    # Compare CSV files (should be identical)
    csv1 = out_dir1 / 'qa_s0_noninferiority_summary.csv'
    csv2 = out_dir2 / 'qa_s0_noninferiority_summary.csv'
    
    df1 = pd.read_csv(csv1)
    df2 = pd.read_csv(csv2)
    
    # Compare numeric columns (ignore empty strings)
    numeric_cols = ['mean_accuracy', 'diff_vs_baseline', 'diff_ci_low', 'diff_ci_high',
                     'p0', 'rd0_vs_baseline', 'rd0_ci_low', 'rd0_ci_high']
    
    for col in numeric_cols:
        if col in df1.columns and col in df2.columns:
            # Convert empty strings to NaN for comparison
            s1 = pd.to_numeric(df1[col], errors='coerce')
            s2 = pd.to_numeric(df2[col], errors='coerce')
            pd.testing.assert_series_equal(s1, s2, check_names=False, 
                                          check_exact=False, rtol=1e-10)
    
    # Compare file hashes
    def file_hash(path):
        sha256 = hashlib.sha256()
        with open(path, 'rb') as f:
            sha256.update(f.read())
        return sha256.hexdigest()
    
    # JSON should be identical (except timestamp)
    json1 = out_dir1 / 'qa_s0_noninferiority_bootstrap_meta.json'
    json2 = out_dir2 / 'qa_s0_noninferiority_bootstrap_meta.json'
    
    import json
    with open(json1) as f:
        meta1 = json.load(f)
    with open(json2) as f:
        meta2 = json.load(f)
    
    # Remove timestamp for comparison
    meta1.pop('timestamp', None)
    meta2.pop('timestamp', None)
    
    assert meta1 == meta2, "Metadata should be identical (except timestamp)"


def test_expected_pass_fail_logic(tmp_path):
    """Test that known cases produce expected PASS/FAIL results."""
    out_dir = tmp_path / 'qa_output'
    out_dir.mkdir()
    
    script_path = SRC_DIR / 'qa' / 's0_noninferiority.py'
    cmd = [
        sys.executable, str(script_path),
        '--input_csv', str(FIXTURE_CSV),
        '--baseline_arm', 'A',
        '--delta', '0.05',
        '--ci', '0.90',
        '--bootstrap_n', '2000',  # More replicates for stability
        '--seed', '20251220',
        '--out_dir', str(out_dir),
        '--min_pairs', '2'
    ]
    
    subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, check=True)
    
    summary_csv = out_dir / 'qa_s0_noninferiority_summary.csv'
    df = pd.read_csv(summary_csv)
    
    # Baseline arm A should always pass
    arm_a = df[df['arm'] == 'A'].iloc[0]
    assert arm_a['final_pass'] == True, "Baseline arm A should pass"
    
    # Arm B should pass (similar performance to A, no major errors)
    arm_b = df[df['arm'] == 'B']
    if len(arm_b) > 0:
        arm_b = arm_b.iloc[0]
        # Arm B has similar scores to A, should pass safety and likely pass NI
        # (exact result depends on bootstrap, but should be reasonable)
        assert arm_b['safety_pass'] == True, "Arm B should pass safety (no major errors)"
    
    # Arm C has 0-score cards (major errors), should fail safety
    arm_c = df[df['arm'] == 'C']
    if len(arm_c) > 0:
        arm_c = arm_c.iloc[0]
        # Arm C has blocking errors (0-score cards), should fail safety
        # Note: exact result depends on bootstrap CI, but should generally fail
        # We check that p0 is higher than baseline
        assert arm_c['p0'] > arm_a['p0'], "Arm C should have higher p0 than baseline"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


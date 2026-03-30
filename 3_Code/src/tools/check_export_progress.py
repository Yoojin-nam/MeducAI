#!/usr/bin/env python3
"""
Check export progress for Anki deck generation
"""
import json
from pathlib import Path
from collections import defaultdict

def count_lines(filepath):
    """Count non-empty lines in a file."""
    if not filepath.exists():
        return 0
    count = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                count += 1
    return count

def analyze_s2_results(s2_path):
    """Analyze S2 results to count cards."""
    if not s2_path.exists():
        return None
    
    total_entities = 0
    total_cards = 0
    q1_count = 0
    q2_count = 0
    
    with open(s2_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if isinstance(record, dict):
                    total_entities += 1
                    cards = record.get("anki_cards", [])
                    for card in cards:
                        if isinstance(card, dict):
                            total_cards += 1
                            card_role = str(card.get("card_role", "")).strip().upper()
                            if card_role == "Q1":
                                q1_count += 1
                            elif card_role == "Q2":
                                q2_count += 1
            except json.JSONDecodeError:
                continue
    
    return {
        "total_entities": total_entities,
        "total_cards": total_cards,
        "q1_count": q1_count,
        "q2_count": q2_count,
    }

def check_export_progress(base_dir="."):
    """Check export progress for all run_tags."""
    base_path = Path(base_dir)
    generated_dir = base_path / "2_Data" / "metadata" / "generated"
    anki_dir = base_path / "6_Distributions" / "anki"
    
    if not generated_dir.exists():
        print(f"Generated directory not found: {generated_dir}")
        return
    
    print("=" * 80)
    print("Export Progress Check")
    print("=" * 80)
    print()
    
    # Find all run_tags
    run_tags = []
    for item in generated_dir.iterdir():
        if item.is_dir():
            run_tags.append(item.name)
    
    run_tags.sort(reverse=True)  # Most recent first
    
    print(f"Found {len(run_tags)} run_tags")
    print()
    
    # Check each run_tag
    for run_tag in run_tags[:10]:  # Check top 10 most recent
        print(f"Run Tag: {run_tag}")
        print("-" * 80)
        
        run_dir = generated_dir / run_tag
        
        # Check S2 results
        s2_paths = [
            run_dir / "s2_results__armG.jsonl",
            run_dir / "s2_results__s1armG__s2armG.jsonl",
            run_dir / "s2_results__s1armA__s2armA.jsonl",
        ]
        
        s2_path = None
        for path in s2_paths:
            if path.exists():
                s2_path = path
                break
        
        if s2_path:
            s2_stats = analyze_s2_results(s2_path)
            if s2_stats:
                print(f"  S2 Results: {s2_path.name}")
                print(f"    Entities: {s2_stats['total_entities']}")
                print(f"    Total Cards: {s2_stats['total_cards']} (Q1: {s2_stats['q1_count']}, Q2: {s2_stats['q2_count']})")
            else:
                print(f"  S2 Results: {s2_path.name} (empty or invalid)")
        else:
            print("  S2 Results: Not found")
        
        # Check S4 manifest
        s4_manifest = run_dir / "s4_image_manifest__armG.jsonl"
        if s4_manifest.exists():
            s4_count = count_lines(s4_manifest)
            print(f"  S4 Manifest: {s4_count} entries")
        else:
            print("  S4 Manifest: Not found")
        
        # Check if .apkg exists
        apkg_path = anki_dir / f"MeducAI_{run_tag}_armG.apkg"
        if apkg_path.exists():
            size_mb = apkg_path.stat().st_size / (1024 * 1024)
            print(f"  Anki Deck: ✓ EXISTS ({size_mb:.2f} MB)")
        else:
            print(f"  Anki Deck: ✗ NOT FOUND")
        
        print()

if __name__ == "__main__":
    check_export_progress()


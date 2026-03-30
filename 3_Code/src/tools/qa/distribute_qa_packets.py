#!/usr/bin/env python3
"""
QA Packet Distribution Script

This script:
1. Generates PDFs for all sets (108 sets = 18 groups × 6 arms)
2. Organizes PDFs by reviewer (Q01~Q12 per reviewer)
3. Creates zip archives for each reviewer
4. Sends emails with zip attachments

Usage:
    python 3_Code/src/tools/qa/distribute_qa_packets.py \
        --base_dir . \
        --run_tag S0_QA_20251220 \
        [--skip_pdf] \
        [--skip_organize] \
        [--skip_zip] \
        [--skip_email] \
        [--dry_run]
"""

import argparse
import csv
import json
import shutil
import smtplib
import sys
import zipfile
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def load_s1_group_mapping(s1_path: Path) -> Dict[str, str]:
    """Load group_key -> group_id mapping from S1 results."""
    mapping = {}
    if not s1_path.exists():
        return mapping
    
    with open(s1_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                group_id = record.get("group_id", "").strip()
                group_key = record.get("group_key", "").strip()
                if group_id and group_key:
                    mapping[group_key] = group_id
            except json.JSONDecodeError:
                continue
    
    return mapping


def load_assignment_map(csv_path: Path) -> List[Dict[str, str]]:
    """Load assignment_map.csv."""
    assignments = []
    if not csv_path.exists():
        raise FileNotFoundError(f"assignment_map.csv not found: {csv_path}")
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            assignments.append({
                "reviewer_id": row.get("reviewer_id", "").strip(),
                "local_qid": row.get("local_qid", "").strip(),
                "set_id": row.get("set_id", "").strip(),
                "group_id": row.get("group_id", "").strip(),
                "arm_id": row.get("arm_id", "").strip(),
                "role": row.get("role", "").strip(),
            })
    
    return assignments


def load_surrogate_map(csv_path: Path) -> Dict[Tuple[str, str], str]:
    """Load surrogate_map.csv and return (group_id, arm) -> surrogate_set_id mapping."""
    mapping = {}
    if not csv_path.exists():
        return mapping
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            group_id = row.get("group_id", "").strip()
            arm = row.get("arm", "").strip()
            surrogate = row.get("surrogate_set_id", "").strip()
            if group_id and arm and surrogate:
                mapping[(group_id, arm)] = surrogate
    
    return mapping


def load_reviewer_master(csv_path: Path) -> Dict[str, Dict[str, str]]:
    """Load reviewer_master.csv and return reviewer_id -> info mapping."""
    reviewers = {}
    if not csv_path.exists():
        print(f"⚠️  reviewer_master.csv not found: {csv_path}")
        return reviewers
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            reviewer_id = row.get("reviewer_id", "").strip()
            if reviewer_id:
                reviewers[reviewer_id] = {
                    "name": row.get("name", "").strip(),
                    "email": row.get("email", "").strip(),
                    "role": row.get("role", "").strip(),
                    "institution": row.get("institution", "").strip(),
                    "subspecialty": row.get("subspecialty", "").strip(),
                }
    
    return reviewers


def update_assignment_map_with_real_group_ids(
    base_dir: Path,
    run_tag: str,
    assignment_map_path: Path,
    arms: List[str],
) -> Dict[str, str]:
    """
    Update assignment_map.csv placeholder group_ids with real group_ids from S1 output.
    
    Returns: mapping from placeholder (group_01) to real group_id (G0123)
    """
    print("\n>>> Updating assignment_map with real group_ids...")
    
    # Load all S1 outputs to get group_key -> group_id mappings
    all_group_mappings = {}
    for arm in arms:
        s1_path = base_dir / "2_Data" / "metadata" / "generated" / run_tag / f"stage1_struct__arm{arm}.jsonl"
        if s1_path.exists():
            mapping = load_s1_group_mapping(s1_path)
            all_group_mappings.update(mapping)
    
    if not all_group_mappings:
        print("⚠️  No S1 outputs found. Cannot update group_ids.")
        return {}
    
    # Load assignment_map
    assignments = load_assignment_map(assignment_map_path)
    
    # Load selected groups to map placeholder to group_key
    selected_groups_file = base_dir / "2_Data" / "metadata" / "generated" / run_tag / "selected_18_groups.json"
    if not selected_groups_file.exists():
        print(f"⚠️  selected_18_groups.json not found: {selected_groups_file}")
        return {}
    
    with open(selected_groups_file, "r", encoding="utf-8") as f:
        selected_groups = json.load(f)
    
    # Create placeholder -> group_key mapping
    placeholder_to_key = {}
    for i, group in enumerate(selected_groups, 1):
        placeholder = f"group_{i:02d}"
        placeholder_to_key[placeholder] = group.get("group_key", "")
    
    # Create placeholder -> real group_id mapping
    placeholder_to_real = {}
    for placeholder, group_key in placeholder_to_key.items():
        real_id = all_group_mappings.get(group_key)
        if real_id:
            placeholder_to_real[placeholder] = real_id
            print(f"  {placeholder} -> {real_id} ({group_key})")
    
    # Update assignment_map.csv
    updated_assignments = []
    for assignment in assignments:
        placeholder = assignment["group_id"]
        real_id = placeholder_to_real.get(placeholder, placeholder)
        assignment["group_id"] = real_id
        updated_assignments.append(assignment)
    
    # Save updated assignment_map
    updated_path = assignment_map_path.parent / f"{assignment_map_path.stem}_updated.csv"
    with open(updated_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["reviewer_id", "local_qid", "set_id", "group_id", "arm_id", "role"])
        writer.writeheader()
        writer.writerows(updated_assignments)
    
    print(f"✅ Updated assignment_map saved to: {updated_path}")
    return placeholder_to_real


def generate_all_pdfs(
    base_dir: Path,
    run_tag: str,
    arms: List[str],
    assignment_map_path: Path,
    surrogate_map_path: Path,
    dry_run: bool = False,
) -> Dict[Tuple[str, str], Path]:
    """
    Generate PDFs for all sets.
    
    Returns: mapping from (group_id, arm) to PDF path
    """
    print("\n" + "=" * 70)
    print("STEP 1: Generating PDFs for all sets")
    print("=" * 70)
    
    # Load assignment map to get all (group_id, arm) combinations
    assignments = load_assignment_map(assignment_map_path)
    surrogate_map = load_surrogate_map(surrogate_map_path)
    
    # Get unique (group_id, arm) pairs
    set_keys = set()
    for assignment in assignments:
        group_id = assignment["group_id"]
        arm_id = assignment["arm_id"]
        if group_id and arm_id:
            set_keys.add((group_id, arm_id))
    
    print(f"   Found {len(set_keys)} unique sets to generate")
    
    out_dir = base_dir / "6_Distributions" / "QA_Packets"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_mapping = {}
    success_count = 0
    
    for group_id, arm in sorted(set_keys):
        surrogate = surrogate_map.get((group_id, arm), f"SET_{group_id}_arm{arm}")
        pdf_filename = f"{surrogate}.pdf"
        pdf_path = out_dir / pdf_filename
        
        if pdf_path.exists():
            print(f"  ✅ PDF already exists: {pdf_filename}")
            pdf_mapping[(group_id, arm)] = pdf_path
            success_count += 1
            continue
        
        if dry_run:
            print(f"  [DRY RUN] Would generate: {pdf_filename}")
            pdf_mapping[(group_id, arm)] = pdf_path
            continue
        
        print(f"  Generating PDF for {group_id} (arm {arm})...")
        
        cmd = [
            sys.executable,
            str(base_dir / "3_Code" / "src" / "07_build_set_pdf.py"),
            "--base_dir", str(base_dir),
            "--run_tag", run_tag,
            "--arm", arm,
            "--group_id", group_id,
            "--out_dir", str(out_dir),
            "--blinded",
            "--set_surrogate_csv", str(surrogate_map_path),
            "--allow_missing_images",  # Allow missing images for now
        ]
        
        import subprocess
        try:
            result = subprocess.run(cmd, cwd=base_dir, capture_output=True, text=True, check=True)
            if pdf_path.exists():
                print(f"    ✅ Created: {pdf_filename}")
                pdf_mapping[(group_id, arm)] = pdf_path
                success_count += 1
            else:
                print(f"    ⚠️  Command succeeded but PDF not found: {pdf_filename}")
        except subprocess.CalledProcessError as e:
            print(f"    ❌ Failed to generate PDF: {e.stderr[:200]}")
    
    print(f"\n✅ Generated {success_count}/{len(set_keys)} PDFs")
    return pdf_mapping


def organize_pdfs_by_reviewer(
    base_dir: Path,
    assignment_map_path: Path,
    pdf_mapping: Dict[Tuple[str, str], Path],
    dry_run: bool = False,
) -> Dict[str, List[Tuple[str, Path]]]:
    """
    Organize PDFs by reviewer (Q01~Q12 per reviewer).
    
    Returns: mapping from reviewer_id to list of (local_qid, pdf_path) tuples
    """
    print("\n" + "=" * 70)
    print("STEP 2: Organizing PDFs by reviewer")
    print("=" * 70)
    
    assignments = load_assignment_map(assignment_map_path)
    
    reviewer_pdfs = {}
    
    for assignment in assignments:
        reviewer_id = assignment["reviewer_id"]
        local_qid = assignment["local_qid"]
        group_id = assignment["group_id"]
        arm_id = assignment["arm_id"]
        
        pdf_path = pdf_mapping.get((group_id, arm_id))
        if not pdf_path or not pdf_path.exists():
            print(f"  ⚠️  PDF not found for {reviewer_id} {local_qid}: {group_id} arm{arm_id}")
            continue
        
        if reviewer_id not in reviewer_pdfs:
            reviewer_pdfs[reviewer_id] = []
        
        reviewer_pdfs[reviewer_id].append((local_qid, pdf_path))
    
    # Sort by local_qid (Q01, Q02, ..., Q12)
    for reviewer_id in reviewer_pdfs:
        reviewer_pdfs[reviewer_id].sort(key=lambda x: x[0])
    
    # Create reviewer directories and copy PDFs
    reviewer_dir = base_dir / "6_Distributions" / "QA_Packets" / "by_reviewer"
    reviewer_dir.mkdir(parents=True, exist_ok=True)
    
    for reviewer_id, pdfs in reviewer_pdfs.items():
        reviewer_folder = reviewer_dir / reviewer_id
        if not dry_run:
            reviewer_folder.mkdir(parents=True, exist_ok=True)
        
        print(f"\n  Reviewer {reviewer_id}: {len(pdfs)} PDFs")
        for local_qid, pdf_path in pdfs:
            dest_path = reviewer_folder / f"{local_qid}.pdf"
            if not dry_run:
                shutil.copy2(pdf_path, dest_path)
            print(f"    {local_qid}: {pdf_path.name} -> {dest_path.name}")
    
    print(f"\n✅ Organized PDFs for {len(reviewer_pdfs)} reviewers")
    return reviewer_pdfs


def create_zip_archives(
    base_dir: Path,
    reviewer_pdfs: Dict[str, List[Tuple[str, Path]]],
    dry_run: bool = False,
) -> Dict[str, Path]:
    """
    Create zip archives for each reviewer.
    
    Returns: mapping from reviewer_id to zip path
    """
    print("\n" + "=" * 70)
    print("STEP 3: Creating zip archives")
    print("=" * 70)
    
    reviewer_dir = base_dir / "6_Distributions" / "QA_Packets" / "by_reviewer"
    zip_dir = base_dir / "6_Distributions" / "QA_Packets" / "zip"
    zip_dir.mkdir(parents=True, exist_ok=True)
    
    zip_mapping = {}
    
    for reviewer_id, pdfs in reviewer_pdfs.items():
        zip_filename = f"{reviewer_id}_QA_Packets.zip"
        zip_path = zip_dir / zip_filename
        
        if dry_run:
            print(f"  [DRY RUN] Would create: {zip_filename} ({len(pdfs)} files)")
            zip_mapping[reviewer_id] = zip_path
            continue
        
        print(f"  Creating zip for {reviewer_id}...")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for local_qid, pdf_path in pdfs:
                # Add PDF to zip with QID as filename
                zipf.write(pdf_path, arcname=f"{local_qid}.pdf")
        
        print(f"    ✅ Created: {zip_filename} ({zip_path.stat().st_size / 1024 / 1024:.2f} MB)")
        zip_mapping[reviewer_id] = zip_path
    
    print(f"\n✅ Created {len(zip_mapping)} zip archives")
    return zip_mapping


def send_emails(
    base_dir: Path,
    reviewer_master_path: Path,
    zip_mapping: Dict[str, Path],
    dry_run: bool = False,
    smtp_server: Optional[str] = None,
    smtp_port: int = 587,
    smtp_user: Optional[str] = None,
    smtp_password: Optional[str] = None,
    from_email: Optional[str] = None,
) -> None:
    """
    Send emails with zip attachments to reviewers.
    """
    print("\n" + "=" * 70)
    print("STEP 4: Sending emails")
    print("=" * 70)
    
    reviewers = load_reviewer_master(reviewer_master_path)
    
    if not reviewers:
        print("⚠️  No reviewer information found. Skipping email sending.")
        return
    
    if dry_run:
        print("  [DRY RUN] Would send emails to:")
        for reviewer_id, zip_path in zip_mapping.items():
            reviewer_info = reviewers.get(reviewer_id, {})
            email = reviewer_info.get("email", "N/A")
            name = reviewer_info.get("name", reviewer_id)
            print(f"    {name} ({email}): {zip_path.name}")
        return
    
    # Check SMTP configuration
    if not smtp_server or not smtp_user or not smtp_password or not from_email:
        print("⚠️  SMTP configuration not provided. Skipping email sending.")
        print("   To send emails, provide: --smtp_server, --smtp_user, --smtp_password, --from_email")
        return
    
    print(f"  Connecting to SMTP server: {smtp_server}:{smtp_port}")
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        
        sent_count = 0
        for reviewer_id, zip_path in zip_mapping.items():
            reviewer_info = reviewers.get(reviewer_id, {})
            email = reviewer_info.get("email", "")
            name = reviewer_info.get("name", reviewer_id)
            
            if not email:
                print(f"  ⚠️  No email for {reviewer_id}, skipping")
                continue
            
            # Create email
            msg = MIMEMultipart()
            msg["From"] = from_email
            msg["To"] = email
            msg["Subject"] = "MeducAI S0 QA Evaluation Packet"
            
            body = f"""
Dear {name},

Please find attached your QA evaluation packet for the MeducAI S0 study.

The packet contains 12 PDF files (Q01.pdf through Q12.pdf) for your evaluation.

Thank you for your participation.

Best regards,
MeducAI Team
"""
            msg.attach(MIMEText(body, "plain"))
            
            # Attach zip file
            with open(zip_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=zip_path.name)
                part["Content-Disposition"] = f'attachment; filename="{zip_path.name}"'
                msg.attach(part)
            
            # Send email
            server.send_message(msg)
            print(f"  ✅ Sent email to {name} ({email})")
            sent_count += 1
        
        server.quit()
        print(f"\n✅ Sent {sent_count} emails")
        
    except Exception as e:
        print(f"❌ Error sending emails: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description="Distribute QA packets to reviewers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base_dir", type=str, default=".", help="Project base directory")
    parser.add_argument("--run_tag", type=str, required=True, help="Run tag")
    parser.add_argument(
        "--assignment_map",
        type=str,
        default="0_Protocol/06_QA_and_Study/QA_Operations/assignment_map.csv",
        help="Path to assignment_map.csv",
    )
    parser.add_argument(
        "--surrogate_map",
        type=str,
        default="0_Protocol/06_QA_and_Study/QA_Operations/surrogate_map.csv",
        help="Path to surrogate_map.csv",
    )
    parser.add_argument(
        "--reviewer_master",
        type=str,
        default="1_Secure_Participant_Info/reviewer_master.csv",
        help="Path to reviewer_master.csv",
    )
    parser.add_argument("--arms", type=str, nargs="+", default=["A", "B", "C", "D", "E", "F"], help="Arms")
    parser.add_argument("--skip_pdf", action="store_true", help="Skip PDF generation")
    parser.add_argument("--skip_organize", action="store_true", help="Skip PDF organization")
    parser.add_argument("--skip_zip", action="store_true", help="Skip zip creation")
    parser.add_argument("--skip_email", action="store_true", help="Skip email sending")
    parser.add_argument("--dry_run", action="store_true", help="Dry run (no actual operations)")
    
    # Email configuration
    parser.add_argument("--smtp_server", type=str, help="SMTP server address")
    parser.add_argument("--smtp_port", type=int, default=587, help="SMTP server port")
    parser.add_argument("--smtp_user", type=str, help="SMTP username")
    parser.add_argument("--smtp_password", type=str, help="SMTP password")
    parser.add_argument("--from_email", type=str, help="From email address")
    
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir).resolve()
    arms = [arm.upper() for arm in args.arms]
    
    print("=" * 70)
    print("QA Packet Distribution")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
    print(f"Run tag: {args.run_tag}")
    print(f"Arms: {', '.join(arms)}")
    if args.dry_run:
        print("⚠️  DRY RUN MODE")
    print("=" * 70)
    
    assignment_map_path = base_dir / args.assignment_map
    surrogate_map_path = base_dir / args.surrogate_map
    reviewer_master_path = base_dir / args.reviewer_master
    
    # Step 0: Update assignment_map with real group_ids
    print("\n>>> Updating assignment_map with real group_ids...")
    placeholder_to_real = update_assignment_map_with_real_group_ids(
        base_dir, args.run_tag, assignment_map_path, arms
    )
    
    # Use updated assignment_map if available
    if (assignment_map_path.parent / f"{assignment_map_path.stem}_updated.csv").exists():
        assignment_map_path = assignment_map_path.parent / f"{assignment_map_path.stem}_updated.csv"
        print(f"   Using updated assignment_map: {assignment_map_path}")
    
    # Step 1: Generate PDFs
    pdf_mapping = {}
    if not args.skip_pdf:
        pdf_mapping = generate_all_pdfs(
            base_dir, args.run_tag, arms, assignment_map_path, surrogate_map_path, args.dry_run
        )
    else:
        print("\n>>> Skipping PDF generation (--skip_pdf)")
        # Load existing PDFs
        pdf_dir = base_dir / "6_Distributions" / "QA_Packets"
        for pdf_file in pdf_dir.glob("SET_*.pdf"):
            # Try to extract group_id and arm from filename
            # Format: SET_<surrogate>.pdf or SET_<group_id>_arm<arm>_<run_tag>.pdf
            pdf_mapping[("unknown", "unknown")] = pdf_file
    
    # Step 2: Organize PDFs by reviewer
    reviewer_pdfs = {}
    if not args.skip_organize:
        reviewer_pdfs = organize_pdfs_by_reviewer(
            base_dir, assignment_map_path, pdf_mapping, args.dry_run
        )
    else:
        print("\n>>> Skipping PDF organization (--skip_organize)")
    
    # Step 3: Create zip archives
    zip_mapping = {}
    if not args.skip_zip:
        zip_mapping = create_zip_archives(base_dir, reviewer_pdfs, args.dry_run)
    else:
        print("\n>>> Skipping zip creation (--skip_zip)")
    
    # Step 4: Send emails
    if not args.skip_email:
        send_emails(
            base_dir,
            reviewer_master_path,
            zip_mapping,
            args.dry_run,
            args.smtp_server,
            args.smtp_port,
            args.smtp_user,
            args.smtp_password,
            args.from_email,
        )
    else:
        print("\n>>> Skipping email sending (--skip_email)")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ Distribution Complete")
    print("=" * 70)
    print(f"PDFs generated: {len(pdf_mapping)}")
    print(f"Reviewers organized: {len(reviewer_pdfs)}")
    print(f"Zip archives created: {len(zip_mapping)}")
    print("=" * 70)


if __name__ == "__main__":
    main()


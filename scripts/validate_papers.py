#!/usr/bin/env python3
"""
validate_papers.py — Check that every downloaded PDF is a valid, readable file.

Checks performed on each PDF:
  1. File exists and size > 5 KB  (catches empty / failed downloads)
  2. Starts with the PDF magic bytes (%PDF-)
  3. pdfminer can extract at least one page of text
  4. Extracted text is not suspiciously short (< 50 chars total)
     which would indicate a scanned-only / image PDF

Usage:
  python3 validate_papers.py                  # scans ./papers/ by default
  python3 validate_papers.py --dir /my/path   # custom folder

Output:
  - Prints a per-file PASS / FAIL / WARN result
  - Prints a summary table at the end
  - Exits with code 1 if any file FAILs (useful for scripting)
"""

import os
import sys
import argparse
from pathlib import Path

# ── Dependency check ──────────────────────────────────────────────────────────
try:
    from pdfminer.high_level import extract_text
    from pdfminer.pdfparser import PDFSyntaxError
except ImportError:
    print("ERROR: pdfminer.six is not installed.")
    print("       Run:  pip install pdfminer.six")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
MIN_FILE_SIZE_BYTES = 5 * 1024          # 5 KB — anything smaller is almost certainly broken
MIN_TEXT_CHARS      = 50                # minimum extractable characters to be considered readable
PDF_MAGIC           = b"%PDF-"         # first 5 bytes of every valid PDF

# Status labels
PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"   # file is valid PDF but very little text (likely scanned image PDF)


# ── Core validator ────────────────────────────────────────────────────────────
def validate_pdf(path: Path) -> tuple[str, str]:
    """
    Validate a single PDF file.
    Returns (status, reason) where status is PASS / FAIL / WARN.
    """
    # Check 1 — file must exist
    if not path.exists():
        return FAIL, "File does not exist"

    # Check 2 — file size
    size = path.stat().st_size
    if size < MIN_FILE_SIZE_BYTES:
        return FAIL, f"File too small ({size} bytes) — download likely failed or truncated"

    # Check 3 — PDF magic bytes
    try:
        with open(path, "rb") as f:
            header = f.read(5)
        if header != PDF_MAGIC:
            return FAIL, f"Not a valid PDF (header: {header!r}) — may be an HTML error page"
    except OSError as e:
        return FAIL, f"Cannot read file: {e}"

    # Check 4 — pdfminer text extraction
    try:
        text = extract_text(str(path))
    except PDFSyntaxError as e:
        return FAIL, f"PDF syntax error — file is corrupt: {e}"
    except Exception as e:
        return FAIL, f"Extraction error: {e}"

    text = (text or "").strip()
    char_count = len(text)

    if char_count < MIN_TEXT_CHARS:
        return WARN, (
            f"Extracted only {char_count} characters — "
            "PDF may be scanned/image-only (no OCR text). "
            "RAG pipeline will produce empty chunks for this file."
        )

    return PASS, f"{char_count:,} characters extracted, {size / 1024:.1f} KB"


# ── Scanner ───────────────────────────────────────────────────────────────────
def scan_directory(root: Path) -> list[dict]:
    """Walk root recursively and validate every .pdf file found."""
    pdf_files = sorted(root.rglob("*.pdf"))

    if not pdf_files:
        print(f"\nNo PDF files found under: {root}")
        print("Make sure you ran download_papers.sh first.\n")
        sys.exit(0)

    results = []
    total   = len(pdf_files)

    print(f"\nScanning {total} PDFs under: {root}\n")
    print(f"  {'STATUS':<6}  {'FILE':<55}  DETAIL")
    print(f"  {'------':<6}  {'----':<55}  ------")

    for pdf in pdf_files:
        status, reason = validate_pdf(pdf)
        relative       = pdf.relative_to(root)

        # Colour codes (work in Cloud Shell / most terminals)
        if status == PASS:
            colour, reset = "\033[92m", "\033[0m"   # green
        elif status == WARN:
            colour, reset = "\033[93m", "\033[0m"   # yellow
        else:
            colour, reset = "\033[91m", "\033[0m"   # red

        label = f"{colour}{status}{reset}"
        print(f"  {label:<6}  {str(relative):<55}  {reason}")

        results.append({
            "path":   pdf,
            "status": status,
            "reason": reason,
        })

    return results


# ── Summary ───────────────────────────────────────────────────────────────────
def print_summary(results: list[dict]) -> int:
    """Print summary table grouped by subfolder. Returns exit code."""
    passed  = [r for r in results if r["status"] == PASS]
    warned  = [r for r in results if r["status"] == WARN]
    failed  = [r for r in results if r["status"] == FAIL]
    total   = len(results)

    print("\n" + "=" * 70)
    print(" VALIDATION SUMMARY")
    print("=" * 70)
    print(f"  Total PDFs scanned : {total}")
    print(f"  \033[92mPASS\033[0m               : {len(passed)}")
    print(f"  \033[93mWARN\033[0m (image PDFs)  : {len(warned)}")
    print(f"  \033[91mFAIL\033[0m               : {len(failed)}")
    print("=" * 70)

    if failed:
        print("\n\033[91mFAILED FILES — re-download or replace these:\033[0m")
        for r in failed:
            print(f"  {r['path'].name}")
            print(f"    Reason: {r['reason']}")

    if warned:
        print("\n\033[93mWARNED FILES — valid PDFs but little extractable text:\033[0m")
        for r in warned:
            print(f"  {r['path'].name}")
            print(f"    Reason: {r['reason']}")

    if not failed and not warned:
        print("\n\033[92mAll PDFs passed validation — safe to upload to the RAG app.\033[0m")
    elif not failed:
        print("\n\033[93mNo failures, but some warned files may produce sparse results in RAG.\033[0m")
    else:
        print("\n\033[91mFix the failed files before uploading to the RAG app.\033[0m")

    print()
    return 1 if failed else 0


# ── Subfolder breakdown ───────────────────────────────────────────────────────
def print_group_breakdown(results: list[dict], root: Path):
    """Show pass/fail counts per subfolder."""
    groups: dict[str, dict] = {}

    for r in results:
        try:
            group = r["path"].relative_to(root).parts[0]
        except (IndexError, ValueError):
            group = "root"

        if group not in groups:
            groups[group] = {PASS: 0, WARN: 0, FAIL: 0}
        groups[group][r["status"]] += 1

    print("\n  GROUP BREAKDOWN")
    print(f"  {'FOLDER':<20}  {'PASS':>6}  {'WARN':>6}  {'FAIL':>6}  {'TOTAL':>6}")
    print(f"  {'------':<20}  {'----':>6}  {'----':>6}  {'----':>6}  {'-----':>6}")
    for group, counts in sorted(groups.items()):
        total = sum(counts.values())
        print(
            f"  {group:<20}  {counts[PASS]:>6}  {counts[WARN]:>6}  {counts[FAIL]:>6}  {total:>6}"
        )


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Validate downloaded nutrition research PDFs."
    )
    parser.add_argument(
        "--dir",
        type=str,
        default="./papers",
        help="Root folder to scan (default: ./papers)",
    )
    args = parser.parse_args()

    root = Path(args.dir).resolve()

    if not root.exists():
        print(f"ERROR: Directory not found: {root}")
        print("       Run download_papers.sh first to populate it.")
        sys.exit(1)

    results  = scan_directory(root)
    print_group_breakdown(results, root)
    exit_code = print_summary(results)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

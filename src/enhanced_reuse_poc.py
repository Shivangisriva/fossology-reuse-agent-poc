from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


LICENSE_PATTERNS = [
    (re.compile(r"SPDX-License-Identifier:\s*([A-Za-z0-9.+-]+)", re.IGNORECASE), "spdx"),
    (re.compile(r"\bMIT License\b", re.IGNORECASE), "MIT"),
    (re.compile(r"\bMIT\b", re.IGNORECASE), "MIT"),
    (re.compile(r"\bApache License\b", re.IGNORECASE), "Apache-2.0"),
    (re.compile(r"\bApache[- ]?2(?:\.0)?\b", re.IGNORECASE), "Apache-2.0"),
    (re.compile(r"\bGPLv?3(?:\.0)?\b", re.IGNORECASE), "GPL-3.0"),
    (re.compile(r"\bGPLv?2(?:\.0)?\b", re.IGNORECASE), "GPL-2.0"),
    (re.compile(r"\bGNU General Public License\b", re.IGNORECASE), "GPL"),
    (re.compile(r"\bBSD[- ]?3[- ]?Clause\b", re.IGNORECASE), "BSD-3-Clause"),
    (re.compile(r"\bBSD[- ]?2[- ]?Clause\b", re.IGNORECASE), "BSD-2-Clause"),
    (re.compile(r"\bMPL[- ]?2(?:\.0)?\b", re.IGNORECASE), "MPL-2.0"),
]


@dataclass
class FileAnalysis:
    file: str
    status: str
    similarity: float
    similarity_percent: float
    suggested_reuse: str
    diff_added_lines: int
    diff_removed_lines: int
    old_license: Optional[str]
    new_license: Optional[str]
    license_change: str
    risk: int
    decision: str


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1", errors="replace")


def detect_license(text: str) -> Optional[str]:
    for pattern, value in LICENSE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        if value == "spdx":
            return match.group(1).strip()
        return value
    return None


def collect_files(root: Path) -> Dict[str, str]:
    files: Dict[str, str] = {}
    for current_root, _, file_names in os.walk(root):
        for name in file_names:
            full_path = Path(current_root) / name
            if full_path.is_file():
                rel_path = full_path.relative_to(root).as_posix()
                files[rel_path] = read_text_safe(full_path)
    return files


def line_diff_stats(old_text: str, new_text: str) -> Tuple[int, int]:
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    diff = difflib.unified_diff(old_lines, new_lines, lineterm="")
    added = 0
    removed = 0
    for line in diff:
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return added, removed


def decide_license_change(old_license: Optional[str], new_license: Optional[str], status: str) -> str:
    if status == "new":
        return f"new file ({new_license or 'unknown'})"
    if status == "deleted":
        return "deleted file"
    if old_license == new_license:
        return "none"
    if old_license is None and new_license is not None:
        return f"added ({new_license})"
    if old_license is not None and new_license is None:
        return f"removed ({old_license})"
    return f"changed ({old_license} -> {new_license})"


def score_risk(status: str, license_change: str) -> int:
    if status == "deleted":
        return 0
    if status == "unchanged" and license_change == "none":
        return 0
    if license_change.startswith("added") or license_change.startswith("removed") or license_change.startswith("changed"):
        return 2
    if status == "new":
        return 1
    if status == "modified":
        return 1
    return 1


def risk_decision(risk: int) -> str:
    if risk == 0:
        return "safe reuse"
    if risk == 1:
        return "manual check"
    return "license review required"


def reuse_suggestion(status: str, similarity: float, license_change: str) -> str:
    if status == "unchanged" and license_change == "none":
        return "direct reuse"
    if status == "deleted":
        return "not applicable"
    if status == "new":
        return "new implementation"
    if status == "modified":
        if license_change != "none":
            return "reuse blocked pending license review"
        if similarity >= 0.95:
            return "high-confidence reuse"
        if similarity >= 0.80:
            return "partial reuse likely"
        return "low reuse confidence"
    return "manual assessment"


def analyze(v1_root: Path, v2_root: Path) -> List[FileAnalysis]:
    v1_files = collect_files(v1_root)
    v2_files = collect_files(v2_root)

    all_paths = sorted(set(v1_files.keys()) | set(v2_files.keys()))
    results: List[FileAnalysis] = []

    for file_path in all_paths:
        in_v1 = file_path in v1_files
        in_v2 = file_path in v2_files

        old_text = v1_files.get(file_path, "")
        new_text = v2_files.get(file_path, "")

        if in_v1 and in_v2:
            old_hash = sha256_text(old_text)
            new_hash = sha256_text(new_text)
            status = "unchanged" if old_hash == new_hash else "modified"
            similarity = difflib.SequenceMatcher(None, old_text, new_text).ratio()
            added, removed = line_diff_stats(old_text, new_text)
        elif in_v1 and not in_v2:
            status = "deleted"
            similarity = 0.0
            added, removed = 0, len(old_text.splitlines())
        else:
            status = "new"
            similarity = 0.0
            added, removed = len(new_text.splitlines()), 0

        old_license = detect_license(old_text) if in_v1 else None
        new_license = detect_license(new_text) if in_v2 else None
        license_change = decide_license_change(old_license, new_license, status)
        risk = score_risk(status, license_change)

        results.append(
            FileAnalysis(
                file=file_path,
                status=status,
                similarity=round(similarity, 3),
                similarity_percent=round(similarity * 100, 1),
                suggested_reuse=reuse_suggestion(status, similarity, license_change),
                diff_added_lines=added,
                diff_removed_lines=removed,
                old_license=old_license,
                new_license=new_license,
                license_change=license_change,
                risk=risk,
                decision=risk_decision(risk),
            )
        )

    return results


def print_table(results: List[FileAnalysis]) -> None:
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="Enhanced Reuse Agent - POC Summary")
        table.add_column("File", overflow="fold")
        table.add_column("Status")
        table.add_column("Similarity %")
        table.add_column("License Change")
        table.add_column("Suggested Reuse", overflow="fold")
        table.add_column("Risk")
        table.add_column("Decision")

        for row in results:
            risk_style = "green" if row.risk == 0 else "yellow" if row.risk == 1 else "red"
            table.add_row(
                row.file,
                row.status,
                f"{row.similarity_percent:.1f}%",
                row.license_change,
                row.suggested_reuse,
                f"[{risk_style}]{row.risk}[/{risk_style}]",
                row.decision,
            )

        console.print(table)
    except Exception:
        header = f"{'File':40} {'Status':10} {'Sim%':8} {'License Change':28} {'Suggested Reuse':34} {'Risk':4} Decision"
        print(header)
        print("-" * len(header))
        for row in results:
            print(
                f"{row.file:40} {row.status:10} {row.similarity_percent:>6.1f}% {row.license_change:28} "
                f"{row.suggested_reuse:34} {row.risk:<4} {row.decision}"
            )


def print_histogram(results: List[FileAnalysis]) -> None:
    buckets = {0: 0, 1: 0, 2: 0}
    for row in results:
        buckets[row.risk] = buckets.get(row.risk, 0) + 1

    print("\nRisk histogram")
    for risk in sorted(buckets):
        count = buckets[risk]
        bar = "#" * count
        print(f"Risk {risk}: {bar} ({count})")


def print_tree_view(results: List[FileAnalysis]) -> None:
    print("\nASCII tree view (v2-centric)")
    grouped: Dict[str, List[FileAnalysis]] = {}
    for row in results:
        folder = str(Path(row.file).parent).replace("\\", "/")
        if folder == ".":
            folder = "/"
        grouped.setdefault(folder, []).append(row)

    risk_marker = {0: "[OK]", 1: "[WARN]", 2: "[RISK]"}

    for folder in sorted(grouped):
        print(f"{folder}")
        for row in sorted(grouped[folder], key=lambda r: r.file):
            name = Path(row.file).name
            marker = risk_marker.get(row.risk, "[?]")
            print(f"  +-- {name} {marker} [{row.status}, sim={row.similarity_percent:.1f}%]")


def print_folder_summary(results: List[FileAnalysis]) -> None:
    print("\nFolder-level risk summary")
    grouped: Dict[str, Dict[str, int]] = {}
    for row in results:
        folder = str(Path(row.file).parent).replace("\\", "/")
        if folder == ".":
            folder = "/"

        if folder not in grouped:
            grouped[folder] = {"safe": 0, "manual": 0, "review": 0, "total": 0}

        grouped[folder]["total"] += 1
        if row.risk == 0:
            grouped[folder]["safe"] += 1
        elif row.risk == 1:
            grouped[folder]["manual"] += 1
        else:
            grouped[folder]["review"] += 1

    for folder in sorted(grouped):
        data = grouped[folder]
        print(
            f"{folder}: safe={data['safe']}, manual_check={data['manual']}, "
            f"license_review={data['review']}, total={data['total']}"
        )


def write_outputs(results: List[FileAnalysis], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "reuse_report.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, indent=2)

    md_path = out_dir / "reuse_report.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Enhanced Reuse Agent POC Report\n\n")
        f.write("| File | Status | Similarity % | License Change | Suggested Reuse | Risk | Decision |\n")
        f.write("|---|---|---:|---|---|---:|---|\n")
        for row in results:
            f.write(
                f"| {row.file} | {row.status} | {row.similarity_percent:.1f}% | {row.license_change} | "
                f"{row.suggested_reuse} | {row.risk} | {row.decision} |\\n"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enhanced Reuse Agent POC")
    parser.add_argument("--v1", required=True, type=Path, help="Path to baseline folder")
    parser.add_argument("--v2", required=True, type=Path, help="Path to updated folder")
    parser.add_argument("--out", required=True, type=Path, help="Path to output folder")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = analyze(args.v1, args.v2)

    print_table(results)
    print_histogram(results)
    print_folder_summary(results)
    print_tree_view(results)
    write_outputs(results, args.out)

    print(f"\nWrote reports to: {args.out}")


if __name__ == "__main__":
    main()

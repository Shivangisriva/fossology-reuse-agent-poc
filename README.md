# Enhanced Reuse Agent POC (FOSSology Proposal)

This repository contains a runnable proof of concept for **intelligent license reuse analysis**.

## What this POC demonstrates

- File-level reuse detection between two versions (`v1` and `v2`)
- File status detection: unchanged, modified, new, deleted
- Lightweight license detection from comments/headers
- License change analysis and risk scoring
- CLI summary report + JSON + Markdown outputs

## Folder layout

- `data/v1`: baseline source version
- `data/v2`: updated source version
- `src/enhanced_reuse_poc.py`: POC engine
- `output/`: generated reports after running the script

## Quick start

1. Open terminal in the project root.
2. Run:

   `python src/enhanced_reuse_poc.py --v1 data/v1 --v2 data/v2 --out output`

3. Check generated reports:

- `output/reuse_report.json`
- `output/reuse_report.md`

## Optional dependency for colorful table output

If you want a richer terminal table, install:

`pip install rich`

The script works without `rich` as well.

## How this maps to the proposal

This POC validates the core idea for FOSSology contribution:

- Detect safe-to-reuse files
- Highlight changed files and the degree of change
- Flag license changes for review
- Produce an auditable output suitable for maintainers

  <img width="1386" height="703" alt="image" src="https://github.com/user-attachments/assets/90633ef6-d635-4b72-81ac-39f449b8bb7a" />

## Note

This proof of concept was developed with assistance from AI tools for ideation and implementation support.

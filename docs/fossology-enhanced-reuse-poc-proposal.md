# FOSSology Contribution POC Proposal

## Title
Enhanced Reuse Agent for Intelligent License Reuse

## Problem
Current reuse workflows can be time-consuming when reviewing new uploads against previously scanned versions. Maintainers and compliance teams need a fast way to identify:

- which files are safely reusable,
- which files have meaningful changes,
- and which license changes require legal/compliance review.

## POC Objective
Demonstrate an automated, auditable workflow that compares two versions of a source tree and outputs file-level reuse risk.

## Core Capabilities Demonstrated

1. File status detection
- unchanged
- modified
- new
- deleted

2. Lightweight license extraction
- SPDX-License-Identifier and common license keywords (MIT, GPL, Apache, BSD, MPL)

3. License delta analysis
- none
- added
- removed
- changed

4. Risk scoring for reuse
- 0: safe reuse
- 1: manual check
- 2: license review required

5. Explainable output
- CLI summary table
- JSON report for integration
- Markdown report for reviewer readability

## Scope of POC

In scope:
- Local filesystem comparison of two directories
- Heuristic license detection in source text comments/headers
- Deterministic risk scoring logic

Out of scope:
- Full parser parity with existing FOSSology license scanners
- Database integration
- Production API/UI
- ML similarity scoring

## Why this matters for FOSSology

- Improves triage speed for incremental uploads.
- Reduces manual effort by surfacing high-risk changes quickly.
- Provides transparent reasoning for each decision, aligned with compliance workflows.

## Proposed Next Steps After POC

1. Integrate with FOSSology upload and scan metadata.
2. Replace heuristic detector with FOSSology scanner outputs for authoritative license evidence.
3. Add persistence and API endpoint for reuse comparison results.
4. Add UI panel for risk overview and drill-down per file.

## Evaluation Criteria

- Correctly identifies unchanged, modified, new, and deleted files.
- Flags license additions/changes/removals.
- Produces stable, reproducible risk scores.
- Output is usable by maintainers for review decisions.

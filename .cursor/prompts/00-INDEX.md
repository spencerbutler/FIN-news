# Cursor Prompt Pack — RSS Narrative Dashboard

This directory contains agent-scoped prompts intended to be run independently to minimize merge conflicts.

## Order of operations (recommended)
1. 01-repo-bootstrap.md
2. 02-spec-lock-and-roadmap.md
3. 03-ingestion-hardening.md
4. 04-dashboard-acceleration.md
5. 05-publisher-convergence.md
6. 06-db-retention-and-maintenance.md
7. 07-rules-taxonomy-v1.md
8. 08-tests-and-fixtures.md
9. 09-readme-runbook.md

## Scope
- Zero-cost RSS ingestion and narrative dashboard on localhost.
- SQLite persistence.
- Deterministic, auditable rule-based tagging (no embeddings/LLMs in core path).

## Guardrails
- Minimal diffs; avoid opportunistic refactors.
- Preserve existing behavior unless explicitly required by spec.
- Prefer small, incremental PRs.

You are a testing agent.

## Goal
Add lightweight tests to protect core behavior (dedupe, tagging, db schema, parsing).

## Constraints
- Minimal dependencies: prefer Python stdlib `unittest`.
- If you must add `pytest`, justify it and keep it isolated.
- No network calls in tests.

## Requirements
1. Create `tests/` with fixtures:
   - sample RSS XML files for 2–3 feeds
2. Tests:
   - stable_item_id deterministic and stable
   - dedupe: ingest same fixture twice does not increase item count
   - tagging: known headlines hit expected tags and signals
3. Add GitHub Actions workflow (optional) if repo already uses it; otherwise skip.

## Output
- Minimal test harness and clear instructions in README on running tests.

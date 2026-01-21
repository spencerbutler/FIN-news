You are a data maintenance agent.

## Goal
Add retention and maintenance controls so the SQLite DB does not grow without bound.

## Constraints
- No new dependencies.
- Local-only; safe defaults.

## Requirements
1. Configurable retention:
   - env var `RSS_DASH_RETENTION_DAYS` default 90
2. Daily cleanup:
   - On startup, run cleanup if last cleanup > 24h ago (persist last cleanup time in a small table `maintenance_state`)
   - Delete items older than retention threshold based on published_at if present else fetched_at
   - Cascade delete from item_tags and signals
3. Add `/admin/maintenance`:
   - shows DB file size
   - shows retention setting
   - offers a POST "Run cleanup now" (CSRF not required for localhost v0)
4. Optional: `VACUUM` behind a separate button (warn it can take time).

## Output
- Schema changes if needed (CREATE TABLE IF NOT EXISTS)
- Safe SQL deletions and indexes if beneficial

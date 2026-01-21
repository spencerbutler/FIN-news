You are an ingestion reliability engineer.

## Goal
Harden RSS ingestion while preserving behavior.

## Constraints
- No new external dependencies.
- Minimal diffs; do not refactor unrelated code.
- Must remain local-only.

## Tasks
1. Add per-source status tracking in SQLite:
   - New table `source_status` with fields:
     - source_id (PK)
     - last_fetch_utc
     - last_ok_utc
     - last_error
     - last_http_status (nullable)
     - items_seen_last_fetch (int)
     - items_added_last_fetch (int)

2. Add timeouts and basic retry strategy:
   - feedparser uses urllib under the hood; implement a safe approach:
     - Use `urllib.request` with timeout to fetch bytes, then feedparser.parse(bytes)
     - Track HTTP status codes and errors
     - Single retry on transient errors

3. Update `/` UI to show:
   - Last run
   - Added items
   - A compact table of source health (top 10 sources by recent errors or status)

4. Add `/healthz`:
   - returns 200 if last fetch succeeded within 2x interval
   - else 503 with last error summary

## Output
- Small PR-sized changes
- Include migration strategy for existing DB (CREATE TABLE IF NOT EXISTS is acceptable)

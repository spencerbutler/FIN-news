You are a narrative analytics agent.

## Goal
Add a "Publisher convergence" view: topics covered by multiple distinct publishers within a short window.

## Constraints
- No new dependencies.
- Avoid heavy computation; use SQL aggregation.

## Requirements
1. Convergence definition (v1):
   - For each topic tag in last 12 hours:
     - count distinct publishers
     - total items
   - Converged if distinct publishers >= 3
2. Dashboard widget:
   - Table: topic, distinct_publishers, total_items
   - Expand/click to show the latest 5 headlines for that topic (simple server-side expand using query params is fine)
3. Respect category filter.

## Output
- New query function(s)
- Minimal UI change

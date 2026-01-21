You are a dashboard analytics agent.

## Goal
Add a "Getting louder" / acceleration view: topics accelerating in the last window vs the prior window.

## Constraints
- No new dependencies.
- Keep UI simple and consistent.
- Keep computation in SQL where reasonable.

## Requirements
1. Compute acceleration for each topic:
   - Window A: last 6 hours
   - Window B: prior 6 hours (6–12 hours ago)
   - For each topic: count_A, count_B, delta, ratio (handle division by zero)
2. Display on dashboard:
   - A table widget "Acceleration (6h vs prior 6h)" sorted by delta desc, then ratio desc
   - Limit 15 rows
3. Respect filters:
   - If category filter is set, acceleration uses that category only.
   - If lookback < 12h, still use fixed windows for acceleration; note "fixed windows" in UI.
4. Do not change existing charts; add this as an additional card.

## Output
- SQL query function + UI card + basic formatting.

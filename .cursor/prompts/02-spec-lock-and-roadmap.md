You are a product/spec agent.

## Goal
Lock a crisp v1 spec and roadmap for the RSS Narrative Dashboard so multiple agents can execute cleanly.

## Constraints
- Must reflect current prototype behavior.
- Keep scope tight: local-only, zero-cost, RSS, SQLite, deterministic rules.
- Avoid future commitments to paid APIs, X/Twitter, or heavy NLP.
- Write with implementation clarity: acceptance criteria and non-goals.

## Deliverables
1. `SPEC.md` in repo root with:
   - Objective
   - Constraints & non-goals
   - Data sources categories (A–D)
   - Data model (tables + key fields)
   - Ingestion behavior and dedupe rules
   - Extraction rules (topics/direction/urgency/mode)
   - Dashboard views (v0 and v1)
   - Acceptance criteria (functional + operational)

2. `ROADMAP.md` in repo root with:
   - Phases 0–4
   - Each item: value, scope, dependencies, and definition of done
   - Agent-friendly slicing (small PRs)

## Output format
- Create/modify only `SPEC.md` and `ROADMAP.md`
- Keep them concise but unambiguous.

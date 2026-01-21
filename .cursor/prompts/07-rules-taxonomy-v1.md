You are a taxonomy/rules agent.

## Goal
Improve tagging accuracy while staying deterministic and auditable.

## Constraints
- No ML/LLMs in the core path.
- Minimal churn: extend existing TOPIC_RULES and cue lists; do not replace them wholesale.

## Requirements
1. Add tag types beyond topic:
   - asset_class: equities, rates, credit, fx, commodities
   - geo: US, Europe, China, Global, EM
2. Implement tagging:
   - Add new rule dictionaries: ASSET_CLASS_RULES, GEO_RULES
   - Store them in `tags` with tag_type
   - Write to `item_tags` with confidence 1.0 and tagger rules_v1
3. Add UI:
   - Show asset_class and geo tags as small chips on each item (if present)
4. Provide a small audit utility:
   - `/debug/rules` endpoint returning JSON of rule hit counts over last 24h (for tuning)

## Output
- Changes limited to rules + tagging + small UI enhancement + debug endpoint

# RSS Narrative Dashboard — Roadmap

## Phase 0: Bootstrap (✅ Complete)
**Value**: Establish clean repository structure for maintainability.

**Scope**:
- Split single-file prototype into modular structure (`src/db.py`, `src/rules.py`, `src/ingest.py`, `src/web.py`, `src/utils.py`)
- Keep `rss_dash.py` as thin entrypoint
- Add `.gitignore` and `README.md`
- Fix database locking issues

**Dependencies**: None

**Definition of Done**:
- [x] All modules import correctly
- [x] `python rss_dash.py` starts without errors
- [x] Dashboard loads at `http://127.0.0.1:5000`
- [x] Background fetch loop works
- [x] Manual fetch works
- [x] No database locking errors

---

## Phase 1: Spec Lock and Roadmap (✅ Complete)
**Value**: Establish authoritative specification and execution plan.

**Scope**:
- Document current behavior in `SPEC.md`
- Create `ROADMAP.md` with phases 0–4
- Ensure specs are agent-friendly (clear acceptance criteria)

**Dependencies**: Phase 0

**Definition of Done**:
- [x] `SPEC.md` documents all current behavior
- [x] `ROADMAP.md` defines phases 1–4 with dependencies
- [x] Acceptance criteria defined for each phase

---

## Phase 2: Ingestion Hardening
**Value**: Improve reliability and observability of RSS ingestion.

**Scope**:
1. **Per-source status tracking**:
   - New table `source_status` with: `source_id`, `last_fetch_utc`, `last_ok_utc`, `last_error`, `last_http_status`, `items_seen_last_fetch`, `items_added_last_fetch`
   - Update status after each source fetch

2. **Timeouts and retries**:
   - Use `urllib.request` with timeout to fetch bytes before parsing
   - Track HTTP status codes
   - Single retry on transient errors (5xx, network timeout)

3. **Dashboard enhancements**:
   - Show per-source health table (top 10 by recent errors)
   - Display last run, items added per source

4. **Health endpoint**:
   - `/healthz` returns 200 if last fetch succeeded within 2x interval
   - Returns 503 with error summary if unhealthy

**Dependencies**: Phase 1

**Definition of Done**:
- [x] `source_status` table created and populated
- [x] Network timeouts implemented (30s default)
- [x] Retry logic handles transient errors
- [x] Dashboard shows source health table
- [x] `/healthz` endpoint works correctly
- [x] No regressions in existing functionality

**PR Strategy**: Single PR for all changes (tightly coupled).

---

## Phase 3: Dashboard Acceleration
**Value**: Identify trending topics by showing acceleration in recent window vs prior window.

**Scope**:
1. **Acceleration calculation**:
   - Window A: last 6 hours
   - Window B: prior 6 hours (6–12 hours ago)
   - For each topic: count_A, count_B, delta (count_A - count_B), ratio (count_A / count_B if count_B > 0, else count_A)

2. **Dashboard widget**:
   - New card: "Acceleration (6h vs prior 6h)"
   - Table sorted by delta DESC, then ratio DESC
   - Limit 15 rows
   - Show topic, count_A, count_B, delta, ratio

3. **Filter integration**:
   - If category filter set, acceleration uses that category only
   - If lookback < 12h, still use fixed windows; note "fixed windows" in UI

4. **No changes to existing charts**

**Dependencies**: Phase 2

**Definition of Done**:
- [x] SQL query function computes acceleration correctly
- [x] Acceleration widget appears on dashboard
- [x] Respects category filter
- [x] Handles edge cases (no items in prior window)
- [x] UI indicates fixed 6h windows when lookback < 12h
- [x] No regressions in existing widgets

**PR Strategy**: Single PR (isolated feature).

---

## Phase 4: Publisher Convergence
**Value**: Normalize items that represent the same story across multiple publishers.

**Scope**:
1. **Similarity detection** (v1: simple approach):
   - Title similarity using normalized edit distance
   - Same topic tags + published within 2 hours = candidate cluster
   - Threshold TBD (start with 0.7 similarity)

2. **Clustering**:
   - New table `clusters` with: `cluster_id`, `canonical_item_id`, `created_at`
   - New table `item_clusters` with: `item_id`, `cluster_id`
   - Canonical item: earliest published item in cluster

3. **Dashboard display**:
   - Group items by cluster in latest items list
   - Show canonical title with "N sources" indicator
   - Expandable to show all items in cluster

**Dependencies**: Phase 3

**Definition of Done**:
- [x] Clustering algorithm groups similar items
- [x] Clusters persist in database
- [x] Dashboard groups items by cluster
- [x] Expandable cluster view works
- [x] Performance acceptable (< 5s for clustering 1000 items)

**PR Strategy**: 2 PRs (clustering logic, then UI integration).

---

## Phase 5: Database Retention and Maintenance (✅ Complete)
**Value**: Prevent unbounded database growth and maintain query performance.

**Scope**:
- Automated retention policies (e.g., keep 90 days)
- Periodic vacuum/optimize
- Optional archiving to compressed files

**Dependencies**: Phase 4

**Definition of Done**:
- [x] Automated cleanup runs based on retention settings
- [x] VACUUM available via admin interface
- [x] Archive functionality exports old data to compressed JSON
- [x] Admin interface provides access to all maintenance features

---

## Phase 6: Rules Taxonomy v1 (✅ Complete)
**Value**: Improve tagging accuracy and add new topic categories.

**Scope**:
- Refine existing topic rules based on usage data
- Add new topics (e.g., crypto, commodities)
- Improve direction/urgency classification
- Allow rule configuration without code changes

**Dependencies**: Phase 5

**Definition of Done**:
- [x] Added crypto, startups, investors, markets topics
- [x] Expanded regulation rules (taxes, auditors)
- [x] Created configurable rules system (JSON files)
- [x] Rules load from config/ directory without code changes
- [x] Created example configuration files

---

## Phase 7: Tests and Fixtures (Future)

---

## Phase 7: Tests and Fixtures (✅ Complete)
**Value**: Ensure reliability through automated testing.

**Scope**:
- Unit tests for rule functions
- Integration tests for ingestion
- Test fixtures with sample RSS feeds
- CI/CD pipeline

**Dependencies**: Phase 6

**Definition of Done**:
- [x] Unit tests for rules (direction, urgency, mode, tagging)
- [x] Database operation tests (cleanup, archiving, upsert)
- [x] Configurable rules system tests
- [x] Integration tests for full ingestion pipeline
- [x] Additional test fixtures (crypto news feed)
- [x] CI/CD workflow with GitHub Actions
- [x] Test coverage expanded from basic to comprehensive

---

## Phase 8: README Runbook (Future)

---

## Phase 8: README Runbook (Future)
**Value**: Document operational procedures for users.

**Scope**:
- Complete user documentation
- Troubleshooting guide
- Performance tuning recommendations
- Source addition instructions

**Dependencies**: Phase 7

---

## Agent-Friendly Slicing

### Principles
1. **One feature per PR**: Keep PRs focused and reviewable
2. **No opportunistic refactors**: Only change what's necessary
3. **Minimal diffs**: Preserve existing behavior unless specified
4. **Test before declare done**: Verify acceptance criteria manually

### PR Template
- **Goal**: What user-visible change does this make?
- **Changes**: List of files modified
- **Testing**: How to verify the change works
- **Rollback**: How to revert if needed

### Dependencies
- Phases must complete in order
- Each phase builds on previous phase
- No skipping phases (risk of technical debt)

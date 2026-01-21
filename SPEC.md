# RSS Narrative Dashboard — Specification v1

## Objective

A zero-cost, local-only RSS narrative dashboard that aggregates financial news from multiple sources, applies rule-based topic tagging and headline framing analysis, and presents insights through a simple web interface. Designed for personal use without external API dependencies or cloud services.

## Constraints & Non-Goals

### Constraints
- **Local-only**: No cloud services, no external APIs beyond free RSS feeds
- **Zero-cost**: No paid subscriptions or API keys required
- **Deterministic**: Rule-based tagging using regex patterns (no embeddings/LLMs in core path)
- **SQLite**: Single-file database for simplicity
- **Python + Flask**: Standard library and minimal dependencies

### Non-Goals (v1)
- **No embeddings/LLMs**: Tagging and classification use deterministic regex rules
- **No paid APIs**: Twitter/X, news APIs, or other subscription services
- **No real-time alerts**: Polling-based ingestion only
- **No multi-user**: Single-user dashboard on localhost
- **No authentication**: Local access only
- **No mobile app**: Web dashboard only

## Data Sources

### Category A — Market News
- Reuters Markets (`reuters_markets`)
- Bloomberg Markets (`bloomberg_markets`)
- Financial Times Markets (`ft_markets`)
- WSJ Markets (`wsj_markets`)

### Category B — Interpretive / Opinion
- Bloomberg Opinion (`bloomberg_opinion`)
- Financial Times Alphaville (`ft_alphaville`)
- Financial Times Opinion (`ft_opinion`)
- The Economist Finance & Economics (`economist_finance`)

### Category C — Macro / Policy Anchors
- NY Fed Liberty Street Economics (`nyfed_liberty`)
- St. Louis Fed Research/Publications (`stlouisfed_research`)
- BIS RSS (`bis_all`)
- IMF Blogs (`imf_blogs`)

### Category D — Practitioner / Allocator Commentary
- AQR Insights (`aqr_insights`)
- Bridgewater Research & Insights (`bridgewater_insights`)
- BlackRock Investment Insights (`blackrock_insights`)

## Data Model

### Tables

#### `sources`
- `source_id` (TEXT, PK): Unique identifier (e.g., `reuters_markets`)
- `publisher` (TEXT): Publisher name (e.g., "Reuters")
- `feed_name` (TEXT): Feed name (e.g., "Markets")
- `category` (TEXT): Category (A, B, C, D)
- `rss_url` (TEXT): RSS feed URL
- `cadence_hint` (TEXT, nullable): Hint about update frequency
- `enabled` (INTEGER): 1 if enabled, 0 if disabled

#### `items`
- `item_id` (TEXT, PK): SHA256 hash of normalized identifier
- `source_id` (TEXT, FK → sources): Source of the item
- `published_at` (TEXT, nullable): ISO8601 UTC timestamp from feed
- `fetched_at` (TEXT): ISO8601 UTC timestamp when fetched
- `title` (TEXT): Normalized headline
- `url` (TEXT): Article URL
- `guid` (TEXT, nullable): Feed GUID if available
- `summary` (TEXT, nullable): Article summary (max 1000 chars)
- `raw_json` (TEXT, nullable): Reserved for future use

**Indexes**: `published_at`, `source_id`

#### `tags`
- `tag` (TEXT, PK): Tag identifier (e.g., `rates`, `inflation`)
- `tag_type` (TEXT): Type (currently `topic`)
- `description` (TEXT): Human-readable description

#### `item_tags`
- `item_id` (TEXT, FK → items)
- `tag` (TEXT, FK → tags)
- `confidence` (REAL): Confidence score (default 1.0 for rules_v0)
- `tagger` (TEXT): Tagger identifier (default `rules_v0`)
- **Primary Key**: `(item_id, tag)`

#### `signals`
- `item_id` (TEXT, PK, FK → items): One signal per item
- `direction` (TEXT): `pos`, `neg`, `neutral`, or `mixed`
- `urgency` (TEXT): `high`, `med`, or `low`
- `mode` (TEXT): `explain`, `warn`, `opportunity`, `posthoc`, `policy`, or `unknown`
- `notes` (TEXT, nullable): Reserved for future use
- `scorer` (TEXT): Scorer identifier (default `rules_v0`)

### Database Configuration
- **Journal Mode**: WAL (Write-Ahead Logging) for concurrent access
- **Synchronous**: NORMAL
- **Connection Timeout**: 30 seconds

## Ingestion Behavior

### Fetch Process
1. **Frequency**: Default 15 minutes (configurable via `RSS_DASH_FETCH_INTERVAL`)
2. **Initial Fetch**: Runs immediately on startup
3. **Background Thread**: Daemon thread runs continuous fetch loop
4. **Per Source**: Fetches all enabled sources sequentially

### Deduplication
- **Item ID Generation**: SHA256 hash of:
  - Feed GUID (if available), OR
  - `{source_id}|{normalized_title}|{url}`
- **Title Normalization**:
  - Convert to lowercase
  - Normalize whitespace
  - Strip publisher suffixes (e.g., "- Reuters", "- Bloomberg")
- **Insertion**: `INSERT OR IGNORE` prevents duplicates
- **New Item Detection**: Check existence before upsert to count newly added items

### Error Handling
- **RSS Parse Errors**: Continue processing (RSS feeds often have minor issues)
- **Network Errors**: Logged in `_last_fetch_status`, fetch loop continues
- **Database Errors**: Transaction rollback, error logged, loop continues
- **Individual Source Failures**: Do not block other sources

### Normalization
- **Title**: Strip leading/trailing whitespace, normalize internal whitespace
- **Summary**: Truncate to 1000 characters, normalize whitespace
- **Dates**: Parse with `dateutil.parser`, convert to UTC ISO8601

## Extraction Rules

### Topic Tagging (`tag_topics`)
Deterministic keyword matching against title (case-insensitive regex):
- **rates**: rates, yields, treasuries, 10-year, 2-year
- **inflation**: inflation, CPI, PCE, prices
- **fed**: Fed, FOMC, Powell, central bank
- **jobs**: jobs, employment, unemployment, payrolls
- **growth**: GDP, growth, recession, soft landing, hard landing
- **credit**: credit, spreads, defaults, downgrades
- **banks**: banks, financials, lenders
- **housing**: housing, mortgages, homes, real estate
- **energy**: energy, oil, OPEC, WTI, Brent, gas
- **ai**: AI, artificial intelligence, LLMs
- **semis**: semis, chips, NVIDIA, TSMC
- **big_tech**: Apple, Microsoft, Google, Alphabet, Amazon, Meta
- **china**: China, Beijing, yuan
- **europe**: Europe, EU, ECB, UK, Britain
- **geopolitics**: war, sanctions, geopolitical, Middle East, Ukraine
- **earnings**: earnings, revenue, guidance, beats, misses
- **mna**: mergers, acquisitions, buyouts, deals, IPOs
- **regulation**: regulation, antitrust, law, SEC

**Logic**: Multiple topics can match per item.

### Direction Classification (`classify_direction`)
Matching against title (case-insensitive regex):
- **Negative Cues**: slump, fall, plunge, sell-off, warning, risk, crisis, default, downgrade, tumble, crash, panic
- **Positive Cues**: rally, surge, rise, beats, upgrade, strong, record, optimism, gains, soar

**Result**: `pos`, `neg`, `neutral`, or `mixed` (if both cues present)

### Urgency Classification (`classify_urgency`)
Matching against title (case-insensitive regex):
- **High**: crisis, panic, plunge, soar, shock, emergency, scramble, collapse
- **Medium**: volatility, pressure, concern, risk, slide, jump

**Result**: `high`, `med`, or `low` (default)

### Mode Classification (`classify_mode`)
Matching against title (case-insensitive regex):
- **explain**: why, explainer, what is, how
- **warn**: warning, risk, threat, could, may
- **opportunity**: buy, bull case, undervalued, opportunity
- **posthoc**: "as X falls", "after X drops", "following sell-off"
- **policy**: Fed, FOMC, Treasury, ECB, BOJ, IMF, BIS

**Result**: First matching mode, or `unknown` if none match

## Dashboard Views

### v0 (Current)
- **Layout**: Single page with multiple widgets
- **Ingestion Status**: Last run UTC, items added, last error
- **Top Topics Chart**: Bar chart of top 20 topics by count (last 24h default)
- **Framing Skew Chart**: Bar chart of direction distribution (pos/neg/neutral/mixed)
- **Latest Items List**: Up to 500 items with:
  - Publisher, feed name, category
  - Published/fetched timestamp
  - Title (linked)
  - Direction, urgency, mode badges
  - Summary (if available)

**Filters**:
- **Lookback**: 6h, 12h, 24h, 48h, 72h, 168h (default: 24h)
- **Category**: All, A, B, C, D, E
- **Topic**: Text input for topic tag

**Actions**:
- **Fetch Now**: Manual trigger for immediate fetch
- **Reset**: Clear all filters

### v1 (Planned)
- All v0 features plus:
- **Source Health Table**: Top 10 sources by recent errors/status
- **Acceleration View**: Topics accelerating in last 6h vs prior 6h
- **Health Endpoint**: `/healthz` for monitoring

## Acceptance Criteria

### Functional
1. **Ingestion**: All enabled RSS sources fetch successfully with default 15-minute interval
2. **Deduplication**: Duplicate items from same source are not re-inserted
3. **Tagging**: Items receive appropriate topic tags based on title matching
4. **Signals**: Items receive direction, urgency, and mode classifications
5. **Dashboard**: Web UI loads at `http://127.0.0.1:5000` with all widgets visible
6. **Filters**: Category, topic, and lookback filters work correctly
7. **Manual Fetch**: `/fetch-now` route triggers immediate fetch and redirects

### Operational
1. **Startup**: `python rss_dash.py` starts server and background worker
2. **Background Loop**: Fetches run automatically every 15 minutes
3. **Concurrency**: Web UI remains responsive during background fetches (WAL mode)
4. **Error Recovery**: Individual source failures do not crash the application
5. **Database Locking**: No "database is locked" errors with concurrent access
6. **Data Persistence**: Items persist across application restarts

### Performance
1. **Initial Fetch**: Completes within 30 seconds for all sources
2. **Dashboard Load**: Renders within 2 seconds for 500 items
3. **Memory**: Runs on systems with < 1GB RAM available
4. **Disk**: Database grows at reasonable rate (< 100MB/month typical)

## Configuration

### Environment Variables
- `RSS_DASH_DB`: Database file path (default: `rss_dash.sqlite3`)
- `RSS_DASH_FETCH_INTERVAL`: Fetch interval in seconds (default: `900` = 15 minutes)
- `RSS_DASH_LOOKBACK_HOURS`: Default lookback for dashboard (default: `24`)

### Source Configuration
Sources are defined in `rss_dash.py` as `SOURCES` list. Each source includes:
- `source_id`: Unique identifier
- `publisher`: Display name
- `feed_name`: Feed display name
- `category`: A, B, C, or D
- `rss_url`: Feed URL
- `enabled`: Boolean flag

## Technology Stack
- **Python**: 3.10+ (uses `__future__` annotations)
- **Flask**: 3.0.3 (web framework)
- **feedparser**: 6.0.11 (RSS parsing)
- **python-dateutil**: 2.9.0 (date parsing)
- **SQLite**: 3.x (database)
- **Frontend**: Tailwind CSS + Chart.js (via CDN)

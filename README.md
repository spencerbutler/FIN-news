# RSS Narrative Dashboard

A zero-cost, local-only RSS narrative dashboard that aggregates financial news from multiple sources, applies rule-based topic tagging and headline framing analysis, and presents insights through a simple web interface.

## What This Is

- **Personal RSS aggregator** focused on financial markets and economic news
- **Rule-based tagging** using deterministic regex patterns (no ML/AI)
- **Local-first architecture** - no cloud services, no external APIs
- **SQLite persistence** with automatic cleanup and maintenance
- **Web dashboard** with filtering, analytics, and health monitoring

## What This Is Not

- A replacement for Bloomberg/Reuters - just aggregates their free RSS feeds
- An AI-powered news analyzer - uses simple regex rules only
- A real-time alerting system - polling-based with 15-minute intervals
- A multi-user platform - designed for personal use on localhost

## Quick Start

### Prerequisites
- Python 3.10+
- pip (Python package manager)

### Installation

1. **Clone or download** the repository
2. **Create virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the application**:
   ```bash
   python rss_dash.py
   ```
5. **Open your browser** to `http://127.0.0.1:5000`

The application will automatically start fetching RSS feeds and populate the dashboard.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RSS_DASH_DB` | `rss_dash.sqlite3` | SQLite database file path |
| `RSS_DASH_FETCH_INTERVAL` | `900` (15 min) | Fetch interval in seconds |
| `RSS_DASH_LOOKBACK_HOURS` | `24` | Default dashboard lookback period |
| `RSS_DASH_RETENTION_DAYS` | `90` | Days to retain items before cleanup |

### RSS Sources

Sources are configured in `rss_dash.py` in the `SOURCES` list. Each source includes:
- `source_id`: Unique identifier
- `publisher`: Display name
- `feed_name`: Feed description
- `category`: A, B, C, or D (market segments)
- `rss_url`: RSS feed URL
- `enabled`: Boolean flag

## Data Model

### Categories
- **A: Market News** - Direct market coverage (Reuters, Bloomberg, FT, WSJ)
- **B: Interpretive/Opinion** - Analysis and commentary (FT Alphaville, Economist)
- **C: Macro/Policy Anchors** - Central banks and policy (Fed, ECB, BIS, IMF)
- **D: Practitioner Commentary** - Asset managers and allocators (AQR, Bridgewater)

### Tagging System
Articles receive multiple types of tags:
- **Topics**: Economic concepts (rates, inflation, growth, etc.)
- **Asset Classes**: Equities, rates, credit, FX, commodities
- **Geography**: US, Europe, China, Global, EM
- **Signals**: Direction (pos/neg/neutral), urgency (high/med/low), mode (policy/warn/etc.)

## Features

### Dashboard Views
- **Latest Items**: Chronological feed with filtering
- **Topic Analytics**: Bar charts of top topics by frequency
- **Framing Analysis**: Sentiment distribution across headlines
- **Acceleration Tracking**: Topics gaining/losing momentum (6h vs 6h prior)
- **Source Health**: RSS feed status and error monitoring

### Maintenance
- **Automatic Cleanup**: Removes items older than retention period
- **Database Optimization**: VACUUM operations available
- **Health Monitoring**: `/healthz` endpoint for monitoring
- **Admin Interface**: `/admin/maintenance` for manual operations

### Filtering
- **Time Range**: 6h to 7 days
- **Category**: Market segments A-D
- **Topic Tags**: Filter by economic concepts
- **Combined Filters**: All filters work together

## Operating Notes

### Database Growth
- Typical retention: 90 days
- Estimated growth: <100MB/month with default settings
- Automatic cleanup runs on startup if >24h since last cleanup

### Performance
- Initial fetch: ~30 seconds for all sources
- Dashboard load: <2 seconds for 500 items
- Memory usage: <1GB RAM on typical systems

### Reliability
- **Feed Errors**: Individual source failures don't stop processing
- **Network Issues**: Automatic retry with exponential backoff
- **Deduplication**: Same article never appears twice
- **Concurrent Access**: WAL mode prevents locking issues

## Troubleshooting

### Feeds Returning Empty
- **Cause**: RSS feeds may be temporarily unavailable or rate-limited
- **Check**: Source health table shows fetch status and errors
- **Solution**: Wait and retry; feeds usually recover within hours

### Parse Errors / "Bozo" Feeds
- **Cause**: Some RSS feeds have minor formatting issues
- **Behavior**: Application logs warnings but continues processing
- **Solution**: Usually harmless; contact feed provider if persistent

### SQLite "Database Locked" Errors
- **Cause**: Concurrent read/write operations
- **Solution**: WAL mode is enabled by default. Restart application if issues persist
- **Prevention**: Avoid manual database access while application is running

### High Memory Usage
- **Cause**: Large result sets with long lookback periods
- **Solution**: Reduce lookback hours or add more specific filters
- **Prevention**: Use shorter default lookback (12-24h recommended)

### Missing Items
- **Cause**: Feeds may remove old items, or cleanup may have run
- **Check**: Look at retention settings and last cleanup time
- **Recovery**: Reduce `RSS_DASH_RETENTION_DAYS` if needed

## Development

### Running Tests
```bash
# Run all tests
python -m unittest discover tests/

# Run specific test file
python -m unittest tests.test_rules

# Run with verbose output
python -m unittest -v tests.test_ingest
```

### Test Coverage
- **Rule Functions**: Tagging accuracy and classification logic
- **Deduplication**: Ensures no duplicate items from same source
- **Database Operations**: Cleanup, retention, and maintenance
- **Integration**: Full ingestion pipeline with fixtures

### Adding New Sources
1. Add entry to `SOURCES` list in `rss_dash.py`
2. Test RSS URL accessibility
3. Verify feed format (standard RSS 2.0 preferred)
4. Run application and check source health table

## License

MIT License - see LICENSE file for details.

## Contributing

This is a personal project, but feel free to:
- Report issues or suggest improvements
- Submit pull requests for bug fixes
- Share your own RSS source configurations

Please maintain the core principles:
- Local-only architecture
- Zero external dependencies for core functionality
- Deterministic rule-based processing

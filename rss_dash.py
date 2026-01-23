#!/usr/bin/env python3
"""
rss_dash.py — zero-cost RSS narrative dashboard (single-file)
- Flask web UI (Tailwind + Chart.js via CDN)
- feedparser ingestion
- SQLite persistence
- simple rule-based topic tagging + headline framing signals
"""

from __future__ import annotations

import os
import sqlite3

from src import db, web

# -----------------------------
# Configuration (edit here)
# -----------------------------

APP_TITLE = "Market Thesis News"

# Fetch interval in seconds (v0: every 15 minutes)
FETCH_INTERVAL_SECONDS = int(os.environ.get("RSS_DASH_FETCH_INTERVAL", str(15 * 60)))

# How far back to show items on dashboard
DEFAULT_LOOKBACK_HOURS = int(os.environ.get("RSS_DASH_LOOKBACK_HOURS", "24"))

# v0 Sources (from Step 1)
SOURCES = [
    # Category A — Market News
    dict(source_id="reuters_markets", publisher="Reuters", feed_name="Markets", category="A",
         rss_url="https://www.reuters.com/markets/rss", enabled=True),
    dict(source_id="bloomberg_markets", publisher="Bloomberg", feed_name="Markets", category="A",
         rss_url="https://www.bloomberg.com/feeds/markets.xml", enabled=True),
    dict(source_id="ft_markets", publisher="Financial Times", feed_name="Markets", category="A",
         rss_url="https://www.ft.com/markets?format=rss", enabled=True),
    dict(source_id="wsj_markets", publisher="WSJ", feed_name="Markets", category="A",
         rss_url="https://feeds.a.dj.com/rss/RSSMarketsMain.xml", enabled=True),

    # Category B — Interpretive / Opinion
    dict(source_id="bloomberg_opinion", publisher="Bloomberg", feed_name="Opinion", category="B",
         rss_url="https://www.bloomberg.com/feeds/opinion.xml", enabled=True),
    dict(source_id="ft_alphaville", publisher="Financial Times", feed_name="Alphaville", category="B",
         rss_url="https://www.ft.com/alphaville?format=rss", enabled=True),
    dict(source_id="ft_opinion", publisher="Financial Times", feed_name="Opinion", category="B",
         rss_url="https://www.ft.com/opinion?format=rss", enabled=True),
    dict(source_id="economist_finance", publisher="The Economist", feed_name="Finance & Economics", category="B",
         rss_url="https://www.economist.com/finance-and-economics/rss.xml", enabled=True),

    # Category C — Macro / Policy Anchors
    dict(source_id="nyfed_liberty", publisher="NY Fed", feed_name="Liberty Street Economics", category="C",
         rss_url="https://libertystreeteconomics.newyorkfed.org/feed/", enabled=True),
    dict(source_id="stlouisfed_research", publisher="St. Louis Fed", feed_name="Research/Publications", category="C",
         rss_url="https://research.stlouisfed.org/publications/rss.xml", enabled=True),
    dict(source_id="bis_all", publisher="BIS", feed_name="BIS RSS", category="C",
         rss_url="https://www.bis.org/rss/bis.xml", enabled=True),
    dict(source_id="imf_blogs", publisher="IMF", feed_name="Blogs", category="C",
         rss_url="https://www.imf.org/en/Blogs/rss", enabled=True),

    # Category D — Practitioner / Allocator Commentary
    dict(source_id="aqr_insights", publisher="AQR", feed_name="Insights", category="D",
         rss_url="https://www.aqr.com/Insights/RSS", enabled=True),
    dict(source_id="bridgewater_insights", publisher="Bridgewater", feed_name="Research & Insights", category="D",
         rss_url="https://www.bridgewater.com/research-and-insights/rss.xml", enabled=True),
    dict(source_id="blackrock_insights", publisher="BlackRock", feed_name="Investment Insights", category="D",
         rss_url="https://www.blackrock.com/us/individual/insights/rss", enabled=True),
]

if __name__ == "__main__":
    db.init_db(SOURCES)
    # Run daily cleanup on startup if needed (using direct connection to avoid Flask context issues)
    conn = sqlite3.connect(db.DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        cleanup_stats = db.maybe_run_daily_cleanup(conn)
        if cleanup_stats["items_deleted"] > 0:
            print(f"Database cleanup: deleted {cleanup_stats['items_deleted']} items, "
                  f"{cleanup_stats['tags_deleted']} tags, {cleanup_stats['signals_deleted']} signals")
    finally:
        conn.close()
    app = web.create_app(APP_TITLE, DEFAULT_LOOKBACK_HOURS, FETCH_INTERVAL_SECONDS)
    app.run(host="127.0.0.1", port=5000, debug=False)

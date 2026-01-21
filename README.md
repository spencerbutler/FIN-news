# RSS Narrative Dashboard

Zero-cost RSS narrative dashboard for financial news aggregation and topic analysis.

## Overview

Single-file Flask web application that:
- Ingests RSS feeds from financial news sources
- Applies rule-based topic tagging and headline framing signals
- Provides a web dashboard with charts and filtering

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python rss_dash.py
```

The dashboard will be available at `http://127.0.0.1:5000`

## Configuration

Configuration is in `rss_dash.py`:
- RSS feed sources
- Fetch interval (default: 15 minutes)
- Lookback window (default: 24 hours)

## Status

This is a v0 prototype. A detailed runbook will be added in a future update.

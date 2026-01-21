"""RSS feed ingestion functions."""

from __future__ import annotations

import sqlite3
import threading
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

import feedparser

from . import db, rules, utils

_last_fetch_status: Dict[str, Any] = {"last_run_utc": None, "last_error": None, "items_added": 0}

# Timeout for RSS fetch (seconds)
FETCH_TIMEOUT = 30.0


def fetch_feed_with_timeout(url: str) -> Tuple[Any, Optional[int], Optional[str]]:
    """
    Fetch RSS feed with timeout and retry logic.
    Returns: (parsed_feed, http_status, error_message)
    
    Only retries on transient errors (5xx, network timeouts).
    Does not retry on client errors (401, 403, 404, 429) to avoid being a nuisance.
    """
    import time
    
    # Try once, then retry once only on transient errors
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                url, 
                headers={
                    "User-Agent": "RSS-Dash/1.0 (Personal RSS Aggregator)",
                    "Accept": "application/rss+xml, application/xml, text/xml, */*"
                }
            )
            with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as response:
                http_status = response.getcode()
                feed_bytes = response.read()
                # Parse the feed from bytes
                parsed = feedparser.parse(feed_bytes)
                return parsed, http_status, None
        except urllib.error.HTTPError as e:
            http_status = e.code
            # Don't retry on client errors (4xx) - they're permanent or require auth
            if 400 <= http_status < 500:
                # Special handling for common cases
                if http_status == 401:
                    return None, http_status, "HTTP 401: Unauthorized (requires authentication)"
                elif http_status == 403:
                    return None, http_status, "HTTP 403: Forbidden"
                elif http_status == 404:
                    return None, http_status, "HTTP 404: Not Found (feed may have moved)"
                elif http_status == 429:
                    return None, http_status, "HTTP 429: Rate Limited (too many requests)"
                else:
                    return None, http_status, f"HTTP {http_status}: {e.reason}"
            # Only retry on 5xx server errors (transient)
            if attempt == 0 and 500 <= http_status < 600:
                # Small delay before retry
                time.sleep(1)
                continue
            return None, http_status, f"HTTP {http_status}: {e.reason}"
        except urllib.error.URLError as e:
            # Retry on network errors (timeout, connection refused, etc.)
            if attempt == 0:
                time.sleep(1)
                continue
            return None, None, f"Network error: {e.reason}"
        except Exception as e:
            return None, None, f"{type(e).__name__}: {str(e)}"
    
    return None, None, "Failed after retry"


def update_source_status(conn: sqlite3.Connection, source_id: str, fetch_utc: str, 
                         ok_utc: Optional[str], error: Optional[str], 
                         http_status: Optional[int], items_seen: int, items_added: int) -> None:
    """Update source_status table for a source."""
    conn.execute(
        """INSERT OR REPLACE INTO source_status
           (source_id, last_fetch_utc, last_ok_utc, last_error, last_http_status,
            items_seen_last_fetch, items_added_last_fetch)
           VALUES(?,?,?,?,?,?,?)""",
        (source_id, fetch_utc, ok_utc, error, http_status, items_seen, items_added),
    )


def fetch_once() -> None:
    global _last_fetch_status
    added = 0
    err = None
    started = utils.utcnow()
    fetch_utc = started.isoformat()
    conn = sqlite3.connect(db.DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Ensure WAL mode is enabled for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        sources = conn.execute("SELECT * FROM sources WHERE enabled=1").fetchall()
        for s in sources:
            source_id = s["source_id"]
            source_added = 0
            source_seen = 0
            source_error = None
            source_http_status = None
            source_ok_utc = None

            # Fetch with timeout and retry
            d, http_status, fetch_error = fetch_feed_with_timeout(s["rss_url"])
            
            if fetch_error:
                source_error = fetch_error
                source_http_status = http_status
                update_source_status(
                    conn, source_id, fetch_utc, source_ok_utc, 
                    source_error, source_http_status, source_seen, source_added
                )
                conn.commit()  # Commit error status immediately
                continue
            
            source_http_status = http_status
            source_ok_utc = fetch_utc
            
            if getattr(d, "bozo", 0):
                # RSS parse issues - log but continue
                source_error = "RSS parse warning (bozo flag set)"
            
            for e in d.entries:
                source_seen += 1
                title = utils.normalize_ws(getattr(e, "title", "") or "")
                url = getattr(e, "link", "") or ""
                if not title or not url:
                    continue
                guid = getattr(e, "id", None) or getattr(e, "guid", None)
                published = utils.parse_published(e)
                item_id = utils.stable_item_id(source_id, title, url, guid)
                fetched_at = utils.utcnow().isoformat()

                topics = rules.tag_topics(title)
                asset_classes = rules.tag_asset_class(title)
                geo_tags = rules.tag_geo(title)
                direction = rules.classify_direction(title)
                urgency = rules.classify_urgency(title)
                mode = rules.classify_mode(title)

                item = dict(
                    item_id=item_id,
                    source_id=source_id,
                    published_at=(published.isoformat() if published else None),
                    fetched_at=fetched_at,
                    title=title,
                    url=url,
                    guid=guid,
                    summary=utils.normalize_ws(getattr(e, "summary", "") or "")[:1000] or None,
                    raw_json=None,  # keep None v0; can store later if desired
                    topics=topics,
                    asset_classes=asset_classes,
                    geo_tags=geo_tags,
                    direction=direction,
                    urgency=urgency,
                    mode=mode,
                    notes=None,
                )

                # detect whether it is new
                cur = conn.execute("SELECT 1 FROM items WHERE item_id=?", (item_id,))
                exists = cur.fetchone() is not None
                db.upsert_item_and_annotations(conn, item)
                if not exists:
                    source_added += 1
                    added += 1
            
            # Update source status after processing
            update_source_status(
                conn, source_id, fetch_utc, source_ok_utc, 
                source_error, source_http_status, source_seen, source_added
            )
            
            # Commit after each source to release locks sooner
            conn.commit()
    except Exception as ex:
        conn.rollback()
        err = f"{type(ex).__name__}: {ex}"
    finally:
        conn.close()

    _last_fetch_status = {
        "last_run_utc": started.isoformat(),
        "last_error": err,
        "items_added": added,
    }


def fetch_loop(stop_event: threading.Event, fetch_interval_seconds: int) -> None:
    # Do an initial fetch quickly so dashboard has data.
    fetch_once()
    while not stop_event.is_set():
        stop_event.wait(fetch_interval_seconds)
        if stop_event.is_set():
            break
        fetch_once()


def get_fetch_status() -> Dict[str, Any]:
    """Get the last fetch status."""
    return _last_fetch_status.copy()

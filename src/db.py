"""Database schema and functions."""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict

from flask import g

from . import rules

DB_PATH = os.environ.get("RSS_DASH_DB", "rss_dash.sqlite3")

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY,
  publisher TEXT NOT NULL,
  feed_name TEXT NOT NULL,
  category TEXT NOT NULL,
  rss_url TEXT NOT NULL,
  cadence_hint TEXT,
  enabled INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS items (
  item_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  published_at TEXT,
  fetched_at TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  guid TEXT,
  summary TEXT,
  raw_json TEXT,
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

CREATE INDEX IF NOT EXISTS idx_items_published ON items(published_at);
CREATE INDEX IF NOT EXISTS idx_items_source ON items(source_id);

CREATE TABLE IF NOT EXISTS tags (
  tag TEXT PRIMARY KEY,
  tag_type TEXT NOT NULL,
  description TEXT
);

CREATE TABLE IF NOT EXISTS item_tags (
  item_id TEXT NOT NULL,
  tag TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 1.0,
  tagger TEXT NOT NULL DEFAULT 'rules_v0',
  PRIMARY KEY (item_id, tag),
  FOREIGN KEY (item_id) REFERENCES items(item_id),
  FOREIGN KEY (tag) REFERENCES tags(tag)
);

CREATE TABLE IF NOT EXISTS signals (
  item_id TEXT PRIMARY KEY,
  direction TEXT NOT NULL,
  urgency TEXT NOT NULL,
  mode TEXT NOT NULL,
  notes TEXT,
  scorer TEXT NOT NULL DEFAULT 'rules_v0',
  FOREIGN KEY (item_id) REFERENCES items(item_id)
);

CREATE TABLE IF NOT EXISTS source_status (
  source_id TEXT PRIMARY KEY,
  last_fetch_utc TEXT,
  last_ok_utc TEXT,
  last_error TEXT,
  last_http_status INTEGER,
  items_seen_last_fetch INTEGER NOT NULL DEFAULT 0,
  items_added_last_fetch INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

CREATE TABLE IF NOT EXISTS maintenance_state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        # Ensure WAL mode is enabled for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        g.db = conn
    return g.db


def init_db(sources: list[Dict[str, Any]]) -> None:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    # seed sources
    for s in sources:
        conn.execute(
            """INSERT OR REPLACE INTO sources(source_id,publisher,feed_name,category,rss_url,cadence_hint,enabled)
               VALUES(?,?,?,?,?,?,?)""",
            (s["source_id"], s["publisher"], s["feed_name"], s["category"], s["rss_url"], s.get("cadence_hint"),
             1 if s.get("enabled", True) else 0),
        )
    # seed tags table (topics, asset classes, and geo tags)
    for tag in rules.TOPIC_RULES.keys():
        conn.execute(
            "INSERT OR IGNORE INTO tags(tag, tag_type, description) VALUES(?,?,?)",
            (tag, "topic", f"Auto topic tag: {tag}"),
        )
    for tag in rules.ASSET_CLASS_RULES.keys():
        conn.execute(
            "INSERT OR IGNORE INTO tags(tag, tag_type, description) VALUES(?,?,?)",
            (tag, "asset_class", f"Auto asset class tag: {tag}"),
        )
    for tag in rules.GEO_RULES.keys():
        conn.execute(
            "INSERT OR IGNORE INTO tags(tag, tag_type, description) VALUES(?,?,?)",
            (tag, "geo", f"Auto geo tag: {tag}"),
        )
    conn.commit()
    conn.close()


def upsert_item_and_annotations(conn: sqlite3.Connection, item: Dict[str, Any]) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO items(item_id,source_id,published_at,fetched_at,title,url,guid,summary,raw_json)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        (
            item["item_id"],
            item["source_id"],
            item["published_at"],
            item["fetched_at"],
            item["title"],
            item["url"],
            item.get("guid"),
            item.get("summary"),
            item.get("raw_json"),
        ),
    )
    # signals
    conn.execute(
        """INSERT OR REPLACE INTO signals(item_id,direction,urgency,mode,notes,scorer)
           VALUES(?,?,?,?,?,?)""",
        (
            item["item_id"],
            item["direction"],
            item["urgency"],
            item["mode"],
            item.get("notes"),
            "rules_v0",
        ),
    )
    # tags (topics, asset classes, geo tags)
    # First ensure tags exist in tags table
    for tag in item["topics"]:
        conn.execute(
            "INSERT OR IGNORE INTO tags(tag, tag_type, description) VALUES(?,?,?)",
            (tag, "topic", f"Manual topic tag: {tag}"),
        )
        conn.execute(
            """INSERT OR IGNORE INTO item_tags(item_id,tag,confidence,tagger)
               VALUES(?,?,?,?)""",
            (item["item_id"], tag, 1.0, "rules_v1"),
        )
    for tag in item.get("asset_classes", []):
        conn.execute(
            "INSERT OR IGNORE INTO tags(tag, tag_type, description) VALUES(?,?,?)",
            (tag, "asset_class", f"Manual asset class tag: {tag}"),
        )
        conn.execute(
            """INSERT OR IGNORE INTO item_tags(item_id,tag,confidence,tagger)
               VALUES(?,?,?,?)""",
            (item["item_id"], tag, 1.0, "rules_v1"),
        )
    for tag in item.get("geo_tags", []):
        conn.execute(
            "INSERT OR IGNORE INTO tags(tag, tag_type, description) VALUES(?,?,?)",
            (tag, "geo", f"Manual geo tag: {tag}"),
        )
        conn.execute(
            """INSERT OR IGNORE INTO item_tags(item_id,tag,confidence,tagger)
               VALUES(?,?,?,?)""",
            (item["item_id"], tag, 1.0, "rules_v1"),
        )


def get_retention_days() -> int:
    """Get retention period in days from environment variable, default 90."""
    return int(os.environ.get("RSS_DASH_RETENTION_DAYS", "90"))


def get_maintenance_state(conn: sqlite3.Connection, key: str) -> str | None:
    """Get maintenance state value by key."""
    row = conn.execute(
        "SELECT value FROM maintenance_state WHERE key = ?",
        (key,)
    ).fetchone()
    return row["value"] if row else None


def set_maintenance_state(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Set maintenance state value by key."""
    from datetime import datetime, timezone
    conn.execute(
        "INSERT OR REPLACE INTO maintenance_state(key, value, updated_at) VALUES(?, ?, ?)",
        (key, value, datetime.now(timezone.utc).isoformat())
    )


def run_cleanup(conn: sqlite3.Connection) -> Dict[str, int]:
    """Run database cleanup based on retention policy. Returns stats about what was deleted."""
    from datetime import datetime, timedelta
    retention_days = get_retention_days()
    cutoff = datetime.now() - timedelta(days=retention_days)

    # Delete old items based on published_at if present, else fetched_at
    # SQLite doesn't support CASCADE DELETE directly, so we need to delete from child tables first
    cursor = conn.execute("""
        SELECT item_id FROM items
        WHERE (published_at IS NOT NULL AND published_at < ?) OR
              (published_at IS NULL AND fetched_at < ?)
    """, (cutoff.isoformat(), cutoff.isoformat()))

    old_item_ids = [row["item_id"] for row in cursor.fetchall()]

    if not old_item_ids:
        return {"items_deleted": 0, "tags_deleted": 0, "signals_deleted": 0}

    # Delete from child tables first
    placeholders = ",".join("?" * len(old_item_ids))

    tags_deleted = conn.execute(
        f"DELETE FROM item_tags WHERE item_id IN ({placeholders})",
        old_item_ids
    ).rowcount

    signals_deleted = conn.execute(
        f"DELETE FROM signals WHERE item_id IN ({placeholders})",
        old_item_ids
    ).rowcount

    items_deleted = conn.execute(
        f"DELETE FROM items WHERE item_id IN ({placeholders})",
        old_item_ids
    ).rowcount

    # Update maintenance state
    from datetime import datetime, timezone
    set_maintenance_state(conn, "last_cleanup", datetime.now(timezone.utc).isoformat())

    return {
        "items_deleted": items_deleted,
        "tags_deleted": tags_deleted,
        "signals_deleted": signals_deleted,
    }


def get_db_file_size() -> int:
    """Get database file size in bytes."""
    try:
        return os.path.getsize(DB_PATH)
    except OSError:
        return 0


def maybe_run_daily_cleanup(conn: sqlite3.Connection | None = None) -> Dict[str, int]:
    """Run cleanup if last cleanup was more than 24 hours ago. Returns cleanup stats."""
    from datetime import datetime, timedelta
    if conn is None:
        conn = get_db()

    last_cleanup_str = get_maintenance_state(conn, "last_cleanup")
    if last_cleanup_str:
        try:
            last_cleanup = datetime.fromisoformat(last_cleanup_str)
            if datetime.now() - last_cleanup < timedelta(hours=24):
                # Not time to run cleanup yet
                return {"items_deleted": 0, "tags_deleted": 0, "signals_deleted": 0}
        except ValueError:
            pass  # Invalid timestamp, proceed with cleanup

    # Time to run cleanup
    return run_cleanup(conn)


def archive_old_items(conn: sqlite3.Connection, archive_days: int) -> str:
    """
    Archive items older than archive_days to a compressed JSON file.
    Returns the path to the created archive file.
    """
    import json
    import gzip
    from datetime import datetime, timedelta
    from pathlib import Path

    cutoff = datetime.now() - timedelta(days=archive_days)

    # Get old items with all their data
    cursor = conn.execute("""
        SELECT
            i.*,
            s.publisher,
            s.feed_name,
            s.category,
            sig.direction,
            sig.urgency,
            sig.mode,
            GROUP_CONCAT(DISTINCT it_topic.tag) as topics,
            GROUP_CONCAT(DISTINCT it_asset.tag) as asset_classes,
            GROUP_CONCAT(DISTINCT it_geo.tag) as geo_tags
        FROM items i
        JOIN sources s ON s.source_id = i.source_id
        LEFT JOIN signals sig ON sig.item_id = i.item_id
        LEFT JOIN item_tags it_topic ON it_topic.item_id = i.item_id
            AND it_topic.tag IN (SELECT tag FROM tags WHERE tag_type = 'topic')
        LEFT JOIN item_tags it_asset ON it_asset.item_id = i.item_id
            AND it_asset.tag IN (SELECT tag FROM tags WHERE tag_type = 'asset_class')
        LEFT JOIN item_tags it_geo ON it_geo.item_id = i.item_id
            AND it_geo.tag IN (SELECT tag FROM tags WHERE tag_type = 'geo')
        WHERE (i.published_at IS NOT NULL AND i.published_at < ?) OR
              (i.published_at IS NULL AND i.fetched_at < ?)
        GROUP BY i.item_id
        ORDER BY COALESCE(i.published_at, i.fetched_at) DESC
    """, (cutoff.isoformat(), cutoff.isoformat()))

    old_items = []
    for row in cursor.fetchall():
        item_dict = dict(row)
        # Parse comma-separated tag strings back to lists
        item_dict['topics'] = item_dict['topics'].split(',') if item_dict['topics'] else []
        item_dict['asset_classes'] = item_dict['asset_classes'].split(',') if item_dict['asset_classes'] else []
        item_dict['geo_tags'] = item_dict['geo_tags'].split(',') if item_dict['geo_tags'] else []
        old_items.append(item_dict)

    if not old_items:
        raise ValueError(f"No items found older than {archive_days} days to archive")

    # Create archive filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = Path(DB_PATH).parent / "archives"
    archive_dir.mkdir(exist_ok=True)
    archive_path = archive_dir / f"rss_archive_{timestamp}_{archive_days}days.json.gz"

    # Write compressed JSON
    with gzip.open(archive_path, 'wt', encoding='utf-8') as f:
        json.dump({
            "archived_at": datetime.now().isoformat(),
            "archive_days": archive_days,
            "total_items": len(old_items),
            "items": old_items
        }, f, indent=2, default=str)

    return str(archive_path)

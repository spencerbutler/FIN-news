"""Tests for database operations."""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import db


class TestDatabase(unittest.TestCase):
    """Test database operations and utilities."""

    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()

        # Override DB_PATH for testing
        self.original_db_path = db.DB_PATH
        db.DB_PATH = self.temp_db.name

        # Initialize database
        db.init_db([
            {
                "source_id": "test_source",
                "publisher": "Test Publisher",
                "feed_name": "Test Feed",
                "category": "A",
                "rss_url": "https://example.com/feed",
                "enabled": True
            }
        ])

    def tearDown(self):
        """Clean up test database."""
        # Restore original DB_PATH
        db.DB_PATH = self.original_db_path

        # Remove temp file
        import os
        try:
            os.unlink(self.temp_db.name)
        except OSError:
            pass

    def test_get_db_file_size(self):
        """Test database file size reporting."""
        size = db.get_db_file_size()
        self.assertIsInstance(size, int)
        self.assertGreater(size, 0)  # Should have some content

    def test_maintenance_state_operations(self):
        """Test maintenance state get/set operations."""
        conn = sqlite3.connect(db.DB_PATH, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row

        try:
            # Test setting and getting state
            db.set_maintenance_state(conn, "test_key", "test_value")
            retrieved = db.get_maintenance_state(conn, "test_key")

            self.assertEqual(retrieved, "test_value")

            # Test non-existent key
            missing = db.get_maintenance_state(conn, "missing_key")
            self.assertIsNone(missing)
        finally:
            conn.close()

    def test_maybe_run_daily_cleanup(self):
        """Test daily cleanup logic."""
        conn = sqlite3.connect(db.DB_PATH, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row

        try:
            # First call should run cleanup (no last_cleanup set)
            stats1 = db.maybe_run_daily_cleanup(conn)
            self.assertIn("items_deleted", stats1)

            # Second call should not run cleanup (too soon)
            stats2 = db.maybe_run_daily_cleanup(conn)
            self.assertEqual(stats2["items_deleted"], 0)
        finally:
            conn.close()

    @patch('src.db.get_retention_days')
    def test_run_cleanup_with_retention(self, mock_retention):
        """Test cleanup with custom retention period."""
        mock_retention.return_value = 0  # Delete everything immediately

        conn = sqlite3.connect(db.DB_PATH, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row

        try:
            # Add a test item
            test_item = {
                "item_id": "test_cleanup_item",
                "source_id": "test_source",
                "published_at": None,
                "fetched_at": "2020-01-01T00:00:00.000000+00:00",  # Old date
                "title": "Test Item for Cleanup",
                "url": "https://example.com/test",
                "guid": None,
                "summary": None,
                "raw_json": None,
                "topics": [],
                "asset_classes": [],
                "geo_tags": [],
                "direction": "neutral",
                "urgency": "low",
                "mode": "unknown",
                "notes": None,
            }

            db.upsert_item_and_annotations(conn, test_item)

            # Verify item exists
            cursor = conn.execute("SELECT COUNT(*) FROM items WHERE item_id = ?", ("test_cleanup_item",))
            self.assertEqual(cursor.fetchone()[0], 1)

            # Run cleanup
            stats = db.run_cleanup(conn)

            # Should have deleted the item
            self.assertEqual(stats["items_deleted"], 1)

            # Verify item is gone
            cursor = conn.execute("SELECT COUNT(*) FROM items WHERE item_id = ?", ("test_cleanup_item",))
            self.assertEqual(cursor.fetchone()[0], 0)
        finally:
            conn.close()

    def test_archive_old_items_validation(self):
        """Test archive validation with no old items."""
        from src import web
        app = web.create_app("Test", 24, 900)

        with app.app_context():
            conn = db.get_db()

            # Try to archive with 365 days - should fail since no old items
            with self.assertRaises(ValueError) as cm:
                db.archive_old_items(conn, 365)

            self.assertIn("No items found older than 365 days", str(cm.exception))

    def test_upsert_item_and_annotations(self):
        """Test inserting and updating items with annotations."""
        conn = sqlite3.connect(db.DB_PATH, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row

        try:
            test_item = {
                "item_id": "test_upsert_item",
                "source_id": "test_source",
                "published_at": "2026-01-20T12:00:00.000000+00:00",
                "fetched_at": "2026-01-20T12:00:00.000000+00:00",
                "title": "Test Item for Upsert",
                "url": "https://example.com/test",
                "guid": "https://example.com/test-guid",
                "summary": "Test summary",
                "raw_json": None,
                "topics": ["test_topic", "fed"],
                "asset_classes": ["equities"],
                "geo_tags": ["US"],
                "direction": "pos",
                "urgency": "high",
                "mode": "policy",
                "notes": None,
            }

            # Insert item
            db.upsert_item_and_annotations(conn, test_item)

            # Verify item exists
            cursor = conn.execute("SELECT * FROM items WHERE item_id = ?", ("test_upsert_item",))
            item_row = cursor.fetchone()
            self.assertIsNotNone(item_row)
            self.assertEqual(item_row["title"], "Test Item for Upsert")

            # Verify signals
            cursor = conn.execute("SELECT * FROM signals WHERE item_id = ?", ("test_upsert_item",))
            signal_row = cursor.fetchone()
            self.assertIsNotNone(signal_row)
            self.assertEqual(signal_row["direction"], "pos")
            self.assertEqual(signal_row["urgency"], "high")
            self.assertEqual(signal_row["mode"], "policy")

            # Verify tags exist
            cursor = conn.execute("""
                SELECT t.tag_type, COUNT(*) as count
                FROM item_tags it
                JOIN tags t ON it.tag = t.tag
                WHERE it.item_id = ?
                GROUP BY t.tag_type
            """, ("test_upsert_item",))

            tag_counts = {row[0]: row[1] for row in cursor.fetchall()}
            self.assertEqual(tag_counts.get("topic", 0), 2)  # test_topic + fed
            self.assertEqual(tag_counts.get("asset_class", 0), 1)  # equities
            self.assertEqual(tag_counts.get("geo", 0), 1)  # US

            # Update item (should not create duplicates)
            test_item["title"] = "Updated Test Item"
            db.upsert_item_and_annotations(conn, test_item)

            # Verify still only one item
            cursor = conn.execute("SELECT COUNT(*) FROM items WHERE item_id = ?", ("test_upsert_item",))
            self.assertEqual(cursor.fetchone()[0], 1)

            # Verify title was updated
            cursor = conn.execute("SELECT title FROM items WHERE item_id = ?", ("test_upsert_item",))
            self.assertEqual(cursor.fetchone()[0], "Updated Test Item")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()

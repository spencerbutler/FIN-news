"""Integration tests for RSS ingestion pipeline."""

import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from src import db, ingest


class TestIntegration(unittest.TestCase):
    """Test full RSS ingestion pipeline integration."""

    def setUp(self):
        """Set up test database and environment."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()

        # Override DB_PATH for testing
        self.original_db_path = db.DB_PATH
        db.DB_PATH = self.temp_db.name

        # Initialize database with test sources
        db.init_db([
            {
                "source_id": "crypto_feed",
                "publisher": "Crypto News",
                "feed_name": "Crypto Feed",
                "category": "A",
                "rss_url": "file://" + os.path.join(os.path.dirname(__file__), "fixtures", "sample_feed_crypto.xml"),
                "enabled": True
            },
            {
                "source_id": "finance_feed",
                "publisher": "Financial News",
                "feed_name": "Finance Feed",
                "category": "A",
                "rss_url": "file://" + os.path.join(os.path.dirname(__file__), "fixtures", "sample_feed_1.xml"),
                "enabled": True
            }
        ])

    def tearDown(self):
        """Clean up test environment."""
        # Restore original DB_PATH
        db.DB_PATH = self.original_db_path

        # Remove temp file
        import os
        try:
            os.unlink(self.temp_db.name)
        except OSError:
            pass

    def test_full_ingestion_pipeline(self):
        """Test complete ingestion pipeline with mocked RSS feeds."""
        # Mock the RSS fetch to return our test feeds
        def mock_fetch_feed(url):
            if "sample_feed_crypto.xml" in url:
                fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "sample_feed_crypto.xml")
                with open(fixture_path, 'rb') as f:
                    feed_bytes = f.read()
                import feedparser
                parsed = feedparser.parse(feed_bytes)
                return parsed, 200, None
            elif "sample_feed_1.xml" in url:
                fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "sample_feed_1.xml")
                with open(fixture_path, 'rb') as f:
                    feed_bytes = f.read()
                import feedparser
                parsed = feedparser.parse(feed_bytes)
                return parsed, 200, None
            else:
                return None, None, "Feed not found"

        with patch('src.ingest.fetch_feed_with_timeout', side_effect=mock_fetch_feed):
            # Run ingestion
            ingest.fetch_once()

            # Verify results
            conn = sqlite3.connect(db.DB_PATH, check_same_thread=False, timeout=30.0)
            conn.row_factory = sqlite3.Row

            try:
                # Check total items ingested
                cursor = conn.execute("SELECT COUNT(*) FROM items")
                total_items = cursor.fetchone()[0]
                self.assertGreater(total_items, 0, "Should have ingested some items")

                # Check crypto feed items
                cursor = conn.execute("SELECT COUNT(*) FROM items WHERE source_id = 'crypto_feed'")
                crypto_items = cursor.fetchone()[0]
                self.assertEqual(crypto_items, 4, "Should have 4 crypto feed items")

                # Check finance feed items
                cursor = conn.execute("SELECT COUNT(*) FROM items WHERE source_id = 'finance_feed'")
                finance_items = cursor.fetchone()[0]
                self.assertEqual(finance_items, 5, "Should have 5 finance feed items")

                # Verify crypto topics were tagged
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM item_tags it
                    JOIN tags t ON it.tag = t.tag
                    WHERE t.tag_type = 'topic' AND it.tag = 'crypto'
                """)
                crypto_tags = cursor.fetchone()[0]
                self.assertGreater(crypto_tags, 0, "Should have crypto topic tags")

                # Verify signals were created
                cursor = conn.execute("SELECT COUNT(*) FROM signals")
                signal_count = cursor.fetchone()[0]
                self.assertEqual(signal_count, total_items, "Should have signals for all items")

                # Check deduplication works (run again)
                initial_count = total_items
                ingest.fetch_once()

                cursor = conn.execute("SELECT COUNT(*) FROM items")
                final_count = cursor.fetchone()[0]
                self.assertEqual(final_count, initial_count, "Should not create duplicates on re-ingestion")

            finally:
                conn.close()

    def test_source_health_tracking(self):
        """Test that source health is properly tracked after ingestion."""
        def mock_fetch_feed(url):
            if "sample_feed_crypto.xml" in url:
                fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "sample_feed_crypto.xml")
                with open(fixture_path, 'rb') as f:
                    feed_bytes = f.read()
                import feedparser
                parsed = feedparser.parse(feed_bytes)
                return parsed, 200, None
            else:
                return None, None, "Feed not found"

        with patch('src.ingest.fetch_feed_with_timeout', side_effect=mock_fetch_feed):
            ingest.fetch_once()

            conn = sqlite3.connect(db.DB_PATH, check_same_thread=False, timeout=30.0)
            conn.row_factory = sqlite3.Row

            try:
                # Check source status was updated
                cursor = conn.execute("SELECT * FROM source_status WHERE source_id = 'crypto_feed'")
                status_row = cursor.fetchone()

                self.assertIsNotNone(status_row, "Should have source status record")
                self.assertIsNotNone(status_row['last_ok_utc'], "Should have last OK timestamp")
                self.assertEqual(status_row['last_http_status'], 200, "Should record HTTP 200")
                self.assertEqual(status_row['items_added_last_fetch'], 4, "Should record items added")

            finally:
                conn.close()

    def test_topic_usage_statistics(self):
        """Test that topic usage statistics are accurate after ingestion."""
        def mock_fetch_feed(url):
            if "sample_feed_crypto.xml" in url:
                fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "sample_feed_crypto.xml")
                with open(fixture_path, 'rb') as f:
                    feed_bytes = f.read()
                import feedparser
                parsed = feedparser.parse(feed_bytes)
                return parsed, 200, None
            else:
                return None, None, "Feed not found"

        with patch('src.ingest.fetch_feed_with_timeout', side_effect=mock_fetch_feed):
            ingest.fetch_once()

            conn = sqlite3.connect(db.DB_PATH, check_same_thread=False, timeout=30.0)
            conn.row_factory = sqlite3.Row

            try:
                # Check topic usage
                cursor = conn.execute("""
                    SELECT tag, COUNT(*) as count
                    FROM item_tags
                    WHERE tag IN (SELECT tag FROM tags WHERE tag_type = 'topic')
                    GROUP BY tag
                    ORDER BY count DESC
                """)

                topics = {row['tag']: row['count'] for row in cursor.fetchall()}

                # Should have crypto topics
                self.assertIn('crypto', topics, "Should have crypto topic")
                self.assertGreaterEqual(topics['crypto'], 2, "Should have at least 2 crypto-tagged items")

                # Should have other topics too
                self.assertGreater(len(topics), 1, "Should have multiple topic types")

            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()

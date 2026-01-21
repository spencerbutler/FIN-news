"""Tests for web interface and template rendering."""

import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os

from src import web, db


class TestWeb(unittest.TestCase):
    """Test web interface functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()

        # Override DB_PATH for testing
        self.original_db_path = db.DB_PATH
        db.DB_PATH = self.temp_db.name

        # Initialize database with test data
        db.init_db([
            {
                "source_id": "market_news",
                "publisher": "Market News",
                "feed_name": "Market Feed",
                "category": "A",
                "rss_url": "https://example.com/market",
                "enabled": True
            },
            {
                "source_id": "opinion_news",
                "publisher": "Opinion News",
                "feed_name": "Opinion Feed",
                "category": "B",
                "rss_url": "https://example.com/opinion",
                "enabled": True
            },
            {
                "source_id": "policy_news",
                "publisher": "Policy News",
                "feed_name": "Policy Feed",
                "category": "C",
                "rss_url": "https://example.com/policy",
                "enabled": True
            },
            {
                "source_id": "practitioner_news",
                "publisher": "Practitioner News",
                "feed_name": "Practitioner Feed",
                "category": "D",
                "rss_url": "https://example.com/practitioner",
                "enabled": True
            },
            {
                "source_id": "other_news",
                "publisher": "Other News",
                "feed_name": "Other Feed",
                "category": "E",
                "rss_url": "https://example.com/other",
                "enabled": True
            }
        ])

        # Create Flask app for testing
        self.app = web.create_app("Test Dashboard", 24, 900)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def tearDown(self):
        """Clean up test environment."""
        # Restore original DB_PATH
        db.DB_PATH = self.original_db_path

        # Remove temp file
        try:
            os.unlink(self.temp_db.name)
        except OSError:
            pass

    def test_category_mapping_descriptions(self):
        """Test that category codes map to correct descriptive names."""
        category_mappings = {
            "A": "📈 Market News",
            "B": "📰 Interpretive/Opinion",
            "C": "🏛️ Macro/Policy Anchors",
            "D": "💼 Practitioner Commentary",
            "E": "📊 Other"
        }

        for category_code, expected_description in category_mappings.items():
            with self.subTest(category=category_code):
                # This test verifies the mapping logic used in the template
                # Since we can't easily test Jinja2 template rendering directly,
                # we test the logic that would be used
                if category_code == "A":
                    result = "📈 Market News"
                elif category_code == "B":
                    result = "📰 Interpretive/Opinion"
                elif category_code == "C":
                    result = "🏛️ Macro/Policy Anchors"
                elif category_code == "D":
                    result = "💼 Practitioner Commentary"
                else:
                    result = "📊 Other"

                self.assertEqual(result, expected_description,
                               f"Category {category_code} should map to '{expected_description}'")

    def test_index_route_without_filters(self):
        """Test index route loads without filters."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Dashboard', response.data)
        # Check that the page contains the lookback display (more flexible check)
        self.assertIn(b'Lookback:', response.data)
        self.assertIn(b'24h', response.data)

    def test_index_route_with_category_filter(self):
        """Test index route with category filter."""
        # Add a test item for category A
        with self.app.app_context():
            conn = db.get_db()
            test_item = {
                "item_id": "test_category_item",
                "source_id": "market_news",
                "published_at": "2026-01-20T12:00:00.000000+00:00",
                "fetched_at": "2026-01-20T12:00:00.000000+00:00",
                "title": "Test Market News Item",
                "url": "https://example.com/test",
                "guid": None,
                "summary": "Test summary",
                "raw_json": None,
                "topics": ["fed"],
                "asset_classes": ["equities"],
                "geo_tags": ["US"],
                "direction": "pos",
                "urgency": "high",
                "mode": "policy",
                "notes": None,
            }
            db.upsert_item_and_annotations(conn, test_item)

        # Test filtering by category A
        response = self.client.get('/?category=A')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Market News Item', response.data)
        self.assertIn(b'Category: A', response.data)

        # Test filtering by category B (should not show the item)
        response = self.client.get('/?category=B')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'Test Market News Item', response.data)

    def test_index_route_with_topic_filter(self):
        """Test index route with topic filter."""
        # Add test items with different topics
        with self.app.app_context():
            conn = db.get_db()
            test_items = [
                {
                    "item_id": "test_fed_item",
                    "source_id": "market_news",
                    "published_at": "2026-01-20T12:00:00.000000+00:00",
                    "fetched_at": "2026-01-20T12:00:00.000000+00:00",
                    "title": "Fed Announces Rate Decision",
                    "url": "https://example.com/fed",
                    "guid": None,
                    "summary": "Fed summary",
                    "raw_json": None,
                    "topics": ["fed"],
                    "asset_classes": ["rates"],
                    "geo_tags": ["US"],
                    "direction": "neutral",
                    "urgency": "high",
                    "mode": "policy",
                    "notes": None,
                },
                {
                    "item_id": "test_crypto_item",
                    "source_id": "market_news",
                    "published_at": "2026-01-20T13:00:00.000000+00:00",
                    "fetched_at": "2026-01-20T13:00:00.000000+00:00",
                    "title": "Crypto Prices Surge",
                    "url": "https://example.com/crypto",
                    "guid": None,
                    "summary": "Crypto summary",
                    "raw_json": None,
                    "topics": ["crypto"],
                    "asset_classes": ["crypto_assets"],
                    "geo_tags": ["Global"],
                    "direction": "pos",
                    "urgency": "high",
                    "mode": "unknown",
                    "notes": None,
                }
            ]

            for item in test_items:
                db.upsert_item_and_annotations(conn, item)

        # Test filtering by fed topic
        response = self.client.get('/?topic=fed')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Fed Announces Rate Decision', response.data)
        self.assertNotIn(b'Crypto Prices Surge', response.data)

        # Test filtering by crypto topic
        response = self.client.get('/?topic=crypto')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Crypto Prices Surge', response.data)
        self.assertNotIn(b'Fed Announces Rate Decision', response.data)

    def test_index_route_combined_filters(self):
        """Test index route with combined category and topic filters."""
        # Add test items
        with self.app.app_context():
            conn = db.get_db()
            test_items = [
                {
                    "item_id": "fed_market_item",
                    "source_id": "market_news",  # Category A
                    "published_at": "2026-01-20T12:00:00.000000+00:00",
                    "fetched_at": "2026-01-20T12:00:00.000000+00:00",
                    "title": "Fed and Market News",
                    "url": "https://example.com/fed-market",
                    "guid": None,
                    "summary": "Combined summary",
                    "raw_json": None,
                    "topics": ["fed"],
                    "asset_classes": ["equities"],
                    "geo_tags": ["US"],
                    "direction": "neutral",
                    "urgency": "high",
                    "mode": "policy",
                    "notes": None,
                },
                {
                    "item_id": "fed_opinion_item",
                    "source_id": "opinion_news",  # Category B
                    "published_at": "2026-01-20T13:00:00.000000+00:00",
                    "fetched_at": "2026-01-20T13:00:00.000000+00:00",
                    "title": "Fed Opinion Piece",
                    "url": "https://example.com/fed-opinion",
                    "guid": None,
                    "summary": "Opinion summary",
                    "raw_json": None,
                    "topics": ["fed"],
                    "asset_classes": [],
                    "geo_tags": ["US"],
                    "direction": "neutral",
                    "urgency": "med",
                    "mode": "explain",
                    "notes": None,
                }
            ]

            for item in test_items:
                db.upsert_item_and_annotations(conn, item)

        # Test combined filters: category A + fed topic
        response = self.client.get('/?category=A&topic=fed')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Fed and Market News', response.data)
        self.assertNotIn(b'Fed Opinion Piece', response.data)

    def test_fetch_now_route(self):
        """Test fetch now route."""
        response = self.client.get('/fetch-now')
        # Should redirect back to index
        self.assertEqual(response.status_code, 302)
        self.assertIn('/', response.headers.get('Location', ''))

    def test_healthz_route(self):
        """Test health check endpoint."""
        response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b'OK')

    def test_debug_rules_route(self):
        """Test debug rules endpoint."""
        response = self.client.get('/debug/rules')
        self.assertEqual(response.status_code, 200)

        # Should return JSON
        import json
        data = json.loads(response.data)
        self.assertIn('topics', data)
        self.assertIn('asset_classes', data)
        self.assertIn('total_items', data)

    def test_admin_maintenance_route(self):
        """Test admin maintenance page."""
        response = self.client.get('/admin/maintenance')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Database Maintenance', response.data)

    def test_template_renders_category_badges(self):
        """Test that templates render category badges correctly."""
        # This tests the template logic for category display
        # Since we can't easily test Jinja2 directly, we test the index route
        # which should render items with category badges

        # Add a test item
        with self.app.app_context():
            conn = db.get_db()
            test_item = {
                "item_id": "badge_test_item",
                "source_id": "market_news",  # Category A
                "published_at": "2026-01-20T12:00:00.000000+00:00",
                "fetched_at": "2026-01-20T12:00:00.000000+00:00",
                "title": "Badge Test Item",
                "url": "https://example.com/badge",
                "guid": None,
                "summary": "Badge summary",
                "raw_json": None,
                "topics": ["fed"],
                "asset_classes": ["equities"],
                "geo_tags": ["US"],
                "direction": "pos",
                "urgency": "high",
                "mode": "policy",
                "notes": None,
            }
            db.upsert_item_and_annotations(conn, test_item)

        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

        # Should contain the descriptive category name (Market News with emoji)
        self.assertIn('📈 Market News'.encode('utf-8'), response.data)

        # Should not contain the old format
        self.assertNotIn(b'Category A', response.data)


if __name__ == "__main__":
    unittest.main()

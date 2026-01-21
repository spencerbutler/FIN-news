"""Tests for configurable rules system."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import rules_config


class TestRulesConfig(unittest.TestCase):
    """Test configurable rules loading and validation."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_config_dir = rules_config.get_config_dir()
        # Mock the config directory
        with patch('src.rules_config.get_config_dir', return_value=Path(self.temp_dir)):
            self.config_dir = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_load_rules_from_file_valid(self):
        """Test loading valid JSON rules file."""
        test_file = self.config_dir / "test.json"
        test_data = {"topic1": [r"\btest\b"], "topic2": [r"\bexample\b"]}

        with open(test_file, 'w') as f:
            json.dump(test_data, f)

        result = rules_config.load_rules_from_file(str(test_file))
        self.assertEqual(result, test_data)

    def test_load_rules_from_file_invalid_json(self):
        """Test loading invalid JSON file returns None."""
        test_file = self.config_dir / "invalid.json"

        with open(test_file, 'w') as f:
            f.write("invalid json content {")

        result = rules_config.load_rules_from_file(str(test_file))
        self.assertIsNone(result)

    def test_load_rules_from_file_missing(self):
        """Test loading missing file returns None."""
        test_file = self.config_dir / "missing.json"
        result = rules_config.load_rules_from_file(str(test_file))
        self.assertIsNone(result)

    @patch('src.rules_config.get_config_dir')
    def test_load_topic_rules_from_config(self, mock_get_dir):
        """Test loading topic rules from config file."""
        mock_get_dir.return_value = self.config_dir

        # Create config file
        config_file = self.config_dir / "topics.json"
        config_data = {
            "custom_topic": [r"\bcustom\b"],
            "test_topic": [r"\btest\b"]
        }

        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        result = rules_config.load_topic_rules()
        self.assertEqual(result, config_data)

    @patch('src.rules_config.get_config_dir')
    def test_load_topic_rules_fallback_to_defaults(self, mock_get_dir):
        """Test that missing config file falls back to defaults."""
        mock_get_dir.return_value = self.config_dir

        # No config file exists
        result = rules_config.load_topic_rules()

        # Should return the default rules
        self.assertIn("crypto", result)
        self.assertIn("fed", result)
        self.assertIn("rates", result)
        self.assertEqual(len(result), len(rules_config.DEFAULT_TOPIC_RULES))

    @patch('src.rules_config.get_config_dir')
    def test_load_topic_rules_invalid_config(self, mock_get_dir):
        """Test that invalid config falls back to defaults."""
        mock_get_dir.return_value = self.config_dir

        # Create invalid config file
        config_file = self.config_dir / "topics.json"
        with open(config_file, 'w') as f:
            f.write("invalid json")

        result = rules_config.load_topic_rules()

        # Should return defaults
        self.assertIn("crypto", result)
        self.assertEqual(len(result), len(rules_config.DEFAULT_TOPIC_RULES))

    @patch('src.rules_config.get_config_dir')
    def test_load_topic_rules_partial_invalid(self, mock_get_dir):
        """Test that partially invalid config keeps valid entries."""
        mock_get_dir.return_value = self.config_dir

        # Create config with some valid, some invalid entries
        config_file = self.config_dir / "topics.json"
        config_data = {
            "valid_topic": [r"\bvalid\b"],  # Valid
            "invalid_topic": "not_a_list",  # Invalid - should be list
            "another_valid": [r"\banother\b"]  # Valid
        }

        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        result = rules_config.load_topic_rules()

        # Should only include valid entries
        self.assertIn("valid_topic", result)
        self.assertIn("another_valid", result)
        self.assertNotIn("invalid_topic", result)

    def test_create_example_configs(self):
        """Test creating example configuration files."""
        rules_config.create_example_configs()

        # Check that example files were created
        topics_example = self.config_dir / "topics_example.json"
        assets_example = self.config_dir / "asset_classes_example.json"

        self.assertTrue(topics_example.exists())
        self.assertTrue(assets_example.exists())

        # Check content
        with open(topics_example) as f:
            topics_data = json.load(f)
            self.assertIn("crypto", topics_data)

        with open(assets_example) as f:
            assets_data = json.load(f)
            self.assertIn("crypto_assets", assets_data)


if __name__ == "__main__":
    unittest.main()

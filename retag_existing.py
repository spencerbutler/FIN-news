#!/usr/bin/env python3
"""
Re-tag existing items with updated tagging rules.
"""

import sqlite3
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from rules import tag_topics, tag_asset_class, tag_geo

def retag_existing_items():
    """Re-tag all existing items with current tagging rules."""
    conn = sqlite3.connect('rss_dash.sqlite3')
    conn.row_factory = sqlite3.Row

    try:
        # Get all existing items
        cursor = conn.execute('SELECT item_id, title FROM items')
        items = cursor.fetchall()

        print(f'Re-tagging {len(items)} existing items with new rules...')

        tagged_count = 0
        for item in items:
            item_id = item['item_id']
            title = item['title'] or ''

            # Apply new tagging rules
            topics = tag_topics(title)
            asset_classes = tag_asset_class(title)
            geo_tags = tag_geo(title)

            # Add new tags to item_tags table
            for topic in topics:
                conn.execute('''
                    INSERT OR IGNORE INTO item_tags (item_id, tag, confidence, tagger)
                    VALUES (?, ?, 1.0, 'retag_script')
                ''', (item_id, topic))

            for asset_class in asset_classes:
                conn.execute('''
                    INSERT OR IGNORE INTO item_tags (item_id, tag, confidence, tagger)
                    VALUES (?, ?, 1.0, 'retag_script')
                ''', (item_id, asset_class))

            for geo_tag in geo_tags:
                conn.execute('''
                    INSERT OR IGNORE INTO item_tags (item_id, tag, confidence, tagger)
                    VALUES (?, ?, 1.0, 'retag_script')
                ''', (item_id, geo_tag))

            if topics or asset_classes or geo_tags:
                tagged_count += 1

        conn.commit()

        # Check final count
        cursor = conn.execute('SELECT COUNT(*) FROM item_tags WHERE tag = "trump"')
        trump_tagged = cursor.fetchone()[0]

        print('✅ Re-tagging complete!')
        print(f'   Updated {tagged_count} items')
        print(f'   {trump_tagged} items now tagged with "trump" topic')

    finally:
        conn.close()

if __name__ == '__main__':
    retag_existing_items()

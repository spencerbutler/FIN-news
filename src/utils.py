"""Utility functions."""

from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

from dateutil import parser as dtparser


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def normalize_title_for_hash(title: str, source_id: str) -> str:
    t = title.lower()
    t = normalize_ws(t)
    # light, safe stripping of common suffix patterns
    # per-source exceptions can be added later
    t = re.sub(r"\s+-\s+reuters$", "", t)
    t = re.sub(r"\s+-\s+bloomberg$", "", t)
    t = re.sub(r"\s+-\s+financial times$", "", t)
    t = re.sub(r"\s+-\s+the economist$", "", t)
    t = re.sub(r"\s+-\s+wsj$", "", t)
    return t


def stable_item_id(source_id: str, title: str, url: str, guid: Optional[str]) -> str:
    base = guid or f"{source_id}|{normalize_title_for_hash(title, source_id)}|{url}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def parse_published(entry: Any) -> Optional[datetime]:
    # feedparser sometimes provides published_parsed; we also accept published/updated strings
    for key in ("published", "updated", "created"):
        if getattr(entry, key, None):
            try:
                dt = dtparser.parse(getattr(entry, key))
                return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass
    # published_parsed as struct_time
    if getattr(entry, "published_parsed", None):
        try:
            return datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
        except Exception:
            pass
    return None

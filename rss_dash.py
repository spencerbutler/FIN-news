#!/usr/bin/env python3
"""
rss_dash.py — zero-cost RSS narrative dashboard (single-file)
- Flask web UI (Tailwind + Chart.js via CDN)
- feedparser ingestion
- SQLite persistence
- simple rule-based topic tagging + headline framing signals
"""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import feedparser
from dateutil import parser as dtparser
from flask import Flask, Response, g, redirect, render_template_string, request, url_for

# -----------------------------
# Configuration (edit here)
# -----------------------------

APP_TITLE = "RSS Narrative Dashboard (v0)"
DB_PATH = os.environ.get("RSS_DASH_DB", "rss_dash.sqlite3")

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

# Topic tagging (v0: deterministic keywords)
TOPIC_RULES: Dict[str, List[str]] = {
    "rates": [r"\brate(s)?\b", r"\byield(s)?\b", r"\btreasur(y|ies)\b", r"\b10-?year\b", r"\b2-?year\b"],
    "inflation": [r"\binflation\b", r"\bCPI\b", r"\bPCE\b", r"\bprice(s)?\b"],
    "fed": [r"\bFed\b", r"\bFOMC\b", r"\bPowell\b", r"\bcentral bank\b"],
    "jobs": [r"\bjobs\b", r"\bemployment\b", r"\bunemployment\b", r"\bpayrolls\b"],
    "growth": [r"\bGDP\b", r"\bgrowth\b", r"\brecession\b", r"\bsoft landing\b", r"\bhard landing\b"],
    "credit": [r"\bcredit\b", r"\bspreads?\b", r"\bdefault(s)?\b", r"\bdowngrade(s|d)?\b"],
    "banks": [r"\bbank(s)?\b", r"\bfinancial(s)?\b", r"\blender(s)?\b"],
    "housing": [r"\bhousing\b", r"\bmortgage(s)?\b", r"\bhome(s)?\b", r"\breal estate\b"],
    "energy": [r"\benergy\b", r"\boil\b", r"\bOPEC\b", r"\bWTI\b", r"\bBrent\b", r"\bgas\b"],
    "ai": [r"\bAI\b", r"\bartificial intelligence\b", r"\bLLM(s)?\b"],
    "semis": [r"\bsemi(s)?\b", r"\bchip(s)?\b", r"\bNVIDIA\b", r"\bTSMC\b"],
    "big_tech": [r"\bApple\b", r"\bMicrosoft\b", r"\bGoogle\b", r"\bAlphabet\b", r"\bAmazon\b", r"\bMeta\b"],
    "china": [r"\bChina\b", r"\bBeijing\b", r"\byuan\b"],
    "europe": [r"\bEurope\b", r"\bEU\b", r"\bECB\b", r"\bUK\b", r"\bBritain\b"],
    "geopolitics": [r"\bwar\b", r"\bsanction(s)?\b", r"\bgeopolitic(s|al)\b", r"\bMiddle East\b", r"\bUkraine\b"],
    "earnings": [r"\bearnings\b", r"\brevenue\b", r"\bguidance\b", r"\bbeats?\b", r"\bmiss(es|ed)?\b"],
    "mna": [r"\bmerger(s)?\b", r"\bacquisition(s)?\b", r"\bbuyout\b", r"\bdeal\b", r"\bIPO\b"],
    "regulation": [r"\bregulat(ion|or|ory)\b", r"\bantitrust\b", r"\blaw\b", r"\bSEC\b"],
}

NEG_CUES = [r"\bslump(s|ed)?\b", r"\bfall(s|ing)?\b", r"\bplunge(s|d)?\b", r"\bsell-?off\b",
            r"\bwarning\b", r"\brisk(s)?\b", r"\bcrisis\b", r"\bdefault(s|ed)?\b", r"\bdowngrade(s|d)?\b",
            r"\btumble(s|d)?\b", r"\bcrash\b", r"\bpanic\b"]
POS_CUES = [r"\brally\b", r"\bsurge(s|d)?\b", r"\brise(s|rising)?\b", r"\bbeats?\b", r"\bupgrade(s|d)?\b",
            r"\bstrong\b", r"\brecord\b", r"\boptimis(m|tic)\b", r"\bgain(s|ed)?\b", r"\bsoar(s|ed)?\b"]
URG_HIGH = [r"\bcrisis\b", r"\bpanic\b", r"\bplunge(s|d)?\b", r"\bsoar(s|ed)?\b", r"\bshock\b",
            r"\bemergency\b", r"\bscramble(s|d)?\b", r"\bcollapse\b"]
URG_MED = [r"\bvolatil(e|ity)\b", r"\bpressure\b", r"\bconcern(s)?\b", r"\brisk(s)?\b", r"\bslide(s|d)?\b",
           r"\bjump(s|ed)?\b"]
MODE_RULES = [
    ("explain", [r"\bwhy\b", r"\bexplainer\b", r"\bwhat is\b", r"\bhow\b"]),
    ("warn", [r"\bwarning\b", r"\brisk(s)?\b", r"\bthreat\b", r"\bcould\b", r"\bmay\b"]),
    ("opportunity", [r"\bbuy\b", r"\bbull case\b", r"\bundervalued\b", r"\bopportunity\b"]),
    ("posthoc", [r"\bas\b.*\bfall(s|ing)?\b", r"\bafter\b.*\bdrop(s|ped)?\b", r"\bfollowing\b.*\bsell-?off\b"]),
    ("policy", [r"\bFed\b", r"\bFOMC\b", r"\bTreasury\b", r"\bECB\b", r"\bBOJ\b", r"\bIMF\b", r"\bBIS\b"]),
]

# -----------------------------
# Utilities
# -----------------------------

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

def regex_any(patterns: List[str], text: str) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)

def classify_direction(title: str) -> str:
    t = title
    has_neg = regex_any(NEG_CUES, t)
    has_pos = regex_any(POS_CUES, t)
    if has_neg and has_pos:
        return "mixed"
    if has_neg:
        return "neg"
    if has_pos:
        return "pos"
    return "neutral"

def classify_urgency(title: str) -> str:
    t = title
    if regex_any(URG_HIGH, t):
        return "high"
    if regex_any(URG_MED, t):
        return "med"
    return "low"

def classify_mode(title: str) -> str:
    t = title
    for mode, pats in MODE_RULES:
        if regex_any(pats, t):
            return mode
    return "unknown"

def tag_topics(title: str) -> List[str]:
    hits: List[str] = []
    for tag, pats in TOPIC_RULES.items():
        if regex_any(pats, title):
            hits.append(tag)
    return hits

# -----------------------------
# Database
# -----------------------------

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
"""

def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db

def init_db() -> None:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    # seed sources
    for s in SOURCES:
        conn.execute(
            """INSERT OR REPLACE INTO sources(source_id,publisher,feed_name,category,rss_url,cadence_hint,enabled)
               VALUES(?,?,?,?,?,?,?)""",
            (s["source_id"], s["publisher"], s["feed_name"], s["category"], s["rss_url"], s.get("cadence_hint"),
             1 if s.get("enabled", True) else 0),
        )
    # seed tags table (topic tags only for now)
    for tag in TOPIC_RULES.keys():
        conn.execute(
            "INSERT OR IGNORE INTO tags(tag, tag_type, description) VALUES(?,?,?)",
            (tag, "topic", f"Auto topic tag: {tag}"),
        )
    conn.commit()
    conn.close()

def upsert_item_and_annotations(conn: sqlite3.Connection, item: Dict[str, Any]) -> None:
    conn.execute(
        """INSERT OR IGNORE INTO items(item_id,source_id,published_at,fetched_at,title,url,guid,summary,raw_json)
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
    # tags
    for tag in item["topics"]:
        conn.execute(
            """INSERT OR IGNORE INTO item_tags(item_id,tag,confidence,tagger)
               VALUES(?,?,?,?)""",
            (item["item_id"], tag, 1.0, "rules_v0"),
        )

# -----------------------------
# Ingestion worker
# -----------------------------

_last_fetch_status: Dict[str, Any] = {"last_run_utc": None, "last_error": None, "items_added": 0}

def fetch_once() -> None:
    global _last_fetch_status
    added = 0
    err = None
    started = utcnow()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        sources = conn.execute("SELECT * FROM sources WHERE enabled=1").fetchall()
        for s in sources:
            d = feedparser.parse(s["rss_url"])
            if getattr(d, "bozo", 0):
                # Keep going; RSS often has minor issues
                pass
            for e in d.entries:
                title = normalize_ws(getattr(e, "title", "") or "")
                url = getattr(e, "link", "") or ""
                if not title or not url:
                    continue
                guid = getattr(e, "id", None) or getattr(e, "guid", None)
                published = parse_published(e)
                item_id = stable_item_id(s["source_id"], title, url, guid)
                fetched_at = utcnow().isoformat()

                topics = tag_topics(title)
                direction = classify_direction(title)
                urgency = classify_urgency(title)
                mode = classify_mode(title)

                item = dict(
                    item_id=item_id,
                    source_id=s["source_id"],
                    published_at=(published.isoformat() if published else None),
                    fetched_at=fetched_at,
                    title=title,
                    url=url,
                    guid=guid,
                    summary=normalize_ws(getattr(e, "summary", "") or "")[:1000] or None,
                    raw_json=None,  # keep None v0; can store later if desired
                    topics=topics,
                    direction=direction,
                    urgency=urgency,
                    mode=mode,
                    notes=None,
                )

                # detect whether it is new
                cur = conn.execute("SELECT 1 FROM items WHERE item_id=?", (item_id,))
                exists = cur.fetchone() is not None
                upsert_item_and_annotations(conn, item)
                if not exists:
                    added += 1

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

def fetch_loop(stop_event: threading.Event) -> None:
    # Do an initial fetch quickly so dashboard has data.
    fetch_once()
    while not stop_event.is_set():
        stop_event.wait(FETCH_INTERVAL_SECONDS)
        if stop_event.is_set():
            break
        fetch_once()

# -----------------------------
# Web app
# -----------------------------

app = Flask(__name__)
_stop_event = threading.Event()
_worker_thread: Optional[threading.Thread] = None

@app.before_request
def _before_request() -> None:
    _ = get_db()

@app.teardown_appcontext
def _teardown(exc: Optional[BaseException]) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()

def query_items(lookback_hours: int, category: Optional[str], topic: Optional[str]) -> List[sqlite3.Row]:
    db = get_db()
    since = utcnow() - timedelta(hours=lookback_hours)
    params: List[Any] = [since.isoformat()]
    where = ["(published_at IS NULL AND fetched_at >= ?) OR (published_at >= ?)"]
    params = [since.isoformat(), since.isoformat()]

    if category:
        where.append("s.category = ?")
        params.append(category)
    if topic:
        where.append("it.tag = ?")
        params.append(topic)

    sql = f"""
    SELECT i.*, s.publisher, s.feed_name, s.category,
           sig.direction, sig.urgency, sig.mode
    FROM items i
    JOIN sources s ON s.source_id = i.source_id
    LEFT JOIN signals sig ON sig.item_id = i.item_id
    LEFT JOIN item_tags it ON it.item_id = i.item_id
    WHERE {" AND ".join(where)}
    GROUP BY i.item_id
    ORDER BY COALESCE(i.published_at, i.fetched_at) DESC
    LIMIT 500
    """
    return db.execute(sql, params).fetchall()

def query_topic_counts(lookback_hours: int, category: Optional[str]) -> List[Tuple[str, int]]:
    db = get_db()
    since = utcnow() - timedelta(hours=lookback_hours)
    params: List[Any] = [since.isoformat(), since.isoformat()]
    where = ["(i.published_at IS NULL AND i.fetched_at >= ?) OR (i.published_at >= ?)"]
    if category:
        where.append("s.category = ?")
        params.append(category)

    sql = f"""
    SELECT it.tag as tag, COUNT(DISTINCT i.item_id) as n
    FROM items i
    JOIN sources s ON s.source_id = i.source_id
    JOIN item_tags it ON it.item_id = i.item_id
    WHERE {" AND ".join(where)}
    GROUP BY it.tag
    ORDER BY n DESC
    LIMIT 20
    """
    rows = db.execute(sql, params).fetchall()
    return [(r["tag"], int(r["n"])) for r in rows]

def query_framing_skew(lookback_hours: int, topic: Optional[str]) -> Dict[str, int]:
    db = get_db()
    since = utcnow() - timedelta(hours=lookback_hours)
    params: List[Any] = [since.isoformat(), since.isoformat()]
    where = ["(i.published_at IS NULL AND i.fetched_at >= ?) OR (i.published_at >= ?)"]
    if topic:
        where.append("it.tag = ?")
        params.append(topic)

    sql = f"""
    SELECT sig.direction as direction, COUNT(DISTINCT i.item_id) as n
    FROM items i
    LEFT JOIN signals sig ON sig.item_id = i.item_id
    LEFT JOIN item_tags it ON it.item_id = i.item_id
    WHERE {" AND ".join(where)}
    GROUP BY sig.direction
    """
    rows = db.execute(sql, params).fetchall()
    out = {"pos": 0, "neg": 0, "neutral": 0, "mixed": 0}
    for r in rows:
        k = r["direction"] or "neutral"
        if k not in out:
            continue
        out[k] = int(r["n"])
    return out

TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{{ title }}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-slate-950 text-slate-100">
  <div class="max-w-7xl mx-auto p-4 md:p-8">
    <div class="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
      <div>
        <h1 class="text-2xl md:text-3xl font-semibold">{{ title }}</h1>
        <div class="text-slate-300 mt-1 text-sm">
          Lookback: <span class="font-medium">{{ lookback_hours }}h</span>
          {% if category %} • Category: <span class="font-medium">{{ category }}</span>{% endif %}
          {% if topic %} • Topic: <span class="font-medium">{{ topic }}</span>{% endif %}
        </div>
      </div>
      <div class="flex flex-wrap gap-2 items-center">
        <a class="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-sm" href="{{ url_for('fetch_now') }}">Fetch now</a>
        <form method="get" class="flex flex-wrap gap-2 items-center">
          <select name="lookback" class="bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm">
            {% for h in [6,12,24,48,72,168] %}
              <option value="{{h}}" {% if h==lookback_hours %}selected{% endif %}>{{h}}h</option>
            {% endfor %}
          </select>
          <select name="category" class="bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm">
            <option value="">All categories</option>
            {% for c in ["A","B","C","D","E"] %}
              <option value="{{c}}" {% if c==category %}selected{% endif %}>Category {{c}}</option>
            {% endfor %}
          </select>
          <input name="topic" value="{{ topic or '' }}" placeholder="topic tag (e.g., rates)" class="bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm w-56" />
          <button class="px-3 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-sm font-medium" type="submit">Apply</button>
          <a class="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-sm" href="{{ url_for('index') }}">Reset</a>
        </form>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-6">
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4">
        <div class="text-sm text-slate-300">Ingestion status</div>
        <div class="mt-2 text-sm">
          <div>Last run (UTC): <span class="font-medium">{{ status.last_run_utc or "—" }}</span></div>
          <div>Items added: <span class="font-medium">{{ status.items_added }}</span></div>
          <div>Last error: <span class="font-medium {% if status.last_error %}text-rose-300{% else %}text-slate-200{% endif %}">{{ status.last_error or "none" }}</span></div>
        </div>
      </div>

      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 lg:col-span-2">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-sm text-slate-300">Top topics (count)</div>
            <div class="text-xs text-slate-400">Deterministic keyword tags (v0)</div>
          </div>
        </div>
        <div class="mt-3">
          <canvas id="topicsChart" height="110"></canvas>
        </div>
      </div>

      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 lg:col-span-3">
        <div class="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <div class="text-sm text-slate-300">Framing skew</div>
            <div class="text-xs text-slate-400">pos / neg / neutral / mixed (headline cues only)</div>
          </div>
          <div class="text-xs text-slate-400">
            Tip: filter by a topic for a cleaner view.
          </div>
        </div>
        <div class="mt-3">
          <canvas id="skewChart" height="80"></canvas>
        </div>
      </div>

      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 lg:col-span-3">
        <div class="text-sm text-slate-300">Latest items</div>
        <div class="text-xs text-slate-400">Showing up to 500 items.</div>
        <div class="mt-4 divide-y divide-slate-800">
          {% for it in items %}
            <div class="py-3 flex flex-col md:flex-row md:items-start gap-2 md:gap-4">
              <div class="md:w-56 shrink-0">
                <div class="text-xs text-slate-400">
                  {{ it.publisher }} • {{ it.feed_name }} • Cat {{ it.category }}
                </div>
                <div class="text-xs text-slate-500 mt-1">
                  {{ it.published_at or it.fetched_at }}
                </div>
              </div>
              <div class="flex-1">
                <a class="text-slate-100 hover:text-indigo-300 font-medium" href="{{ it.url }}" target="_blank" rel="noreferrer">
                  {{ it.title }}
                </a>
                <div class="mt-1 text-xs text-slate-400 flex flex-wrap gap-2">
                  <span class="px-2 py-1 rounded-lg bg-slate-800">dir: {{ it.direction }}</span>
                  <span class="px-2 py-1 rounded-lg bg-slate-800">urg: {{ it.urgency }}</span>
                  <span class="px-2 py-1 rounded-lg bg-slate-800">mode: {{ it.mode }}</span>
                </div>
                {% if it.summary %}
                  <div class="mt-2 text-sm text-slate-300 line-clamp-2">{{ it.summary }}</div>
                {% endif %}
              </div>
            </div>
          {% endfor %}
        </div>
      </div>
    </div>
  </div>

<script>
  const topicLabels = {{ topic_labels | safe }};
  const topicCounts = {{ topic_counts | safe }};

  const topicsCtx = document.getElementById("topicsChart").getContext("2d");
  new Chart(topicsCtx, {
    type: "bar",
    data: {
      labels: topicLabels,
      datasets: [{ label: "Count", data: topicCounts }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#cbd5e1" }, grid: { color: "rgba(148,163,184,0.12)" } },
        y: { ticks: { color: "#cbd5e1" }, grid: { color: "rgba(148,163,184,0.12)" } }
      }
    }
  });

  const skew = {{ skew | safe }};
  const skewCtx = document.getElementById("skewChart").getContext("2d");
  new Chart(skewCtx, {
    type: "bar",
    data: {
      labels: ["pos","neg","neutral","mixed"],
      datasets: [{ label: "Items", data: [skew.pos, skew.neg, skew.neutral, skew.mixed] }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#cbd5e1" }, grid: { color: "rgba(148,163,184,0.12)" } },
        y: { ticks: { color: "#cbd5e1" }, grid: { color: "rgba(148,163,184,0.12)" } }
      }
    }
  });
</script>
</body>
</html>
"""

@app.route("/")
def index() -> Response:
    lookback = int(request.args.get("lookback", DEFAULT_LOOKBACK_HOURS))
    category = request.args.get("category") or None
    topic = (request.args.get("topic") or "").strip() or None

    items = query_items(lookback, category, topic)
    topic_counts = query_topic_counts(lookback, category)
    skew = query_framing_skew(lookback, topic)

    labels = [t for (t, n) in topic_counts]
    counts = [n for (t, n) in topic_counts]

    return render_template_string(
        TEMPLATE,
        title=APP_TITLE,
        lookback_hours=lookback,
        category=category,
        topic=topic,
        items=items,
        topic_labels=labels,
        topic_counts=counts,
        skew=skew,
        status=type("S", (), _last_fetch_status),
    )

@app.route("/fetch-now")
def fetch_now() -> Response:
    fetch_once()
    return redirect(url_for("index"))

def start_worker_if_needed() -> None:
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return
    _worker_thread = threading.Thread(target=fetch_loop, args=(_stop_event,), daemon=True)
    _worker_thread.start()

if __name__ == "__main__":
    init_db()
    start_worker_if_needed()
    app.run(host="127.0.0.1", port=5000, debug=False)

"""Topic tagging rules and classifiers."""

from __future__ import annotations

import re
from typing import Dict, List

# Import configurable rules system
from .rules_config import load_topic_rules, load_asset_class_rules, load_geo_rules

# Load rules from config files or use defaults
TOPIC_RULES: Dict[str, List[str]] = load_topic_rules()
ASSET_CLASS_RULES: Dict[str, List[str]] = load_asset_class_rules()
GEO_RULES: Dict[str, List[str]] = load_geo_rules()

NEG_CUES = [r"\bslump(s|ed)?\b", r"\bfall(s|ing)?\b", r"\bplunge(s|d)?\b", r"\bsell-?off\b",
            r"\bwarning\b", r"\brisk(s)?\b", r"\bcrisis\b", r"\bdefault(s|ed)?\b", r"\bdowngrade(s|d)?\b",
            r"\btumble(s|d)?\b", r"\bcrash\b", r"\bpanic\b"]
POS_CUES = [r"\brally\b", r"\bsurge(s|d)?\b", r"\brise(s|rising)?\b", r"\bbeats?\b", r"\bupgrade(s|d)?\b",
            r"\bstrong\b", r"\brecord\b", r"\boptimis(m|tic)\b", r"\bgain(s|ed)?\b", r"\bsoar(s|ed)?\b"]
URG_HIGH = [r"\bcrisis\b", r"\bpanic\b", r"\bplunge(s|d)?\b", r"\bsoar(s|ed)?\b", r"\bsurge(s|d)?\b", r"\bshock\b",
            r"\bemergency\b", r"\bscramble(s|d)?\b", r"\bcollapse\b"]
URG_MED = [r"\bvolatil(e|ity)\b", r"\bpressure\b", r"\bconcern(s)?\b", r"\brisk(s)?\b", r"\bslide(s|d)?\b",
           r"\bjump(s|ed)?\b"]
MODE_RULES = [
    ("explain", [r"\bwhy\b", r"\bexplainer\b", r"\bwhat is\b", r"\bhow\b"]),
    ("warn", [r"\bwarning\b", r"\brisk(s)?\b", r"\bthreat\b", r"\bcould\b", r"\bmay\b"]),
    ("opportunity", [r"\bbuy\b", r"\bbull case\b", r"\bundervalued\b", r"\bopportunity\b"]),
    ("posthoc", [r"\bas\b.*\bfall(s|ing)?\b", r"\bafter\b.*\bdrop(s|ped)?\b", r"\bfollowing\b.*\bsell-?off\b"]),
    ("policy", [r"\bFed\b", r"\bFOMC\b", r"\bTreasury\b", r"\bECB\b", r"\bBOJ\b", r"\bIMF\b", r"\bBIS\b", r"\bcentral bank\b"]),
]


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


def tag_asset_class(title: str) -> List[str]:
    """Tag asset classes based on title content."""
    hits: List[str] = []
    for tag, pats in ASSET_CLASS_RULES.items():
        if regex_any(pats, title):
            hits.append(tag)
    return hits


def tag_geo(title: str) -> List[str]:
    """Tag geographic regions based on title content."""
    hits: List[str] = []
    for tag, pats in GEO_RULES.items():
        if regex_any(pats, title):
            hits.append(tag)
    return hits


def apply_all_tagging(title: str) -> Dict[str, List[str]]:
    """Apply all tagging rules and return results."""
    return {
        "topics": tag_topics(title),
        "asset_classes": tag_asset_class(title),
        "geo_tags": tag_geo(title),
        "direction": classify_direction(title),
        "urgency": classify_urgency(title),
        "mode": classify_mode(title),
    }

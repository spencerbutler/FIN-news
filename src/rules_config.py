"""
Configurable rules system for topic tagging.
Allows rules to be loaded from JSON files without code changes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Default fallback rules (same as hardcoded rules in rules.py)
DEFAULT_TOPIC_RULES = {
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
    "europe": [r"\bEurope(an)?\b", r"\bEU\b", r"\bECB\b", r"\bUK\b", r"\bBritain\b"],
    "geopolitics": [r"\bwar\b", r"\bsanction(s)?\b", r"\bgeopolitic(s|al)\b", r"\bMiddle East\b", r"\bUkraine\b"],
    "earnings": [r"\bearnings\b", r"\brevenue\b", r"\bguidance\b", r"\bbeats?\b", r"\bmiss(es|ed)?\b"],
    "mna": [r"\bmerger(s)?\b", r"\bacquisition(s)?\b", r"\bbuyout\b", r"\bdeal\b", r"\bIPO\b"],
    "regulation": [r"\bregulat(ion|or|ory)\b", r"\bantitrust\b", r"\blaw\b", r"\bSEC\b", r"\btax(es)?\b", r"\bauditor(s)?\b"],
    "politics": [r"\belection(s)?\b", r"\bpolitical\b", r"\bpolitician(s)?\b", r"\bgovernment\b", r"\bcongress\b", r"\bsenate\b", r"\bhouse\b", r"\bparliament\b", r"\bpolicy\b", r"\bregime\b"],
    "trump": [r"\bTrump\b", r"\btrump\b"],
    "biden": [r"\bBiden\b", r"\bbiden\b"],
    "crypto": [r"\bcrypto\b", r"\bbitcoin\b", r"\bBTC\b", r"\bethereum\b", r"\bETH\b", r"\bblockchain\b", r"\bNFT(s)?\b"],
    "startups": [r"\bstartup(s)?\b", r"\bVC\b", r"\bventure capital\b", r"\bfounder(s)?\b", r"\bunicorn(s)?\b"],
    "investors": [r"\binvestor(s)?\b", r"\bhedge fund(s)?\b", r"\bprivate equity\b", r"\bPE\b"],
    "markets": [r"\bmarket(s)?\b", r"\btrading\b", r"\bNYSE\b", r"\bNASDAQ\b"],
}

DEFAULT_ASSET_CLASS_RULES = {
    "equities": [r"\bstocks?\b", r"\bequities?\b", r"\bshares?\b", r"\bSPY\b", r"\bQQQ\b", r"\bDIA\b", r"\bS&P\b", r"\bNasdaq\b", r"\bDow\b"],
    "rates": [r"\bbonds?\b", r"\bfixed income\b", r"\btreasur(y|ies)\b", r"\byield(s)?\b", r"\bTLT\b", r"\bIEF\b", r"\bAGG\b"],
    "credit": [r"\bcredit\b", r"\bcorporate bonds?\b", r"\bhigh yield\b", r"\bjunk bonds?\b", r"\bLQD\b", r"\bHYG\b"],
    "fx": [r"\bcurrency\b", r"\bforex\b", r"\bFX\b", r"\bdollar\b", r"\beuro\b", r"\byen\b", r"\bpound\b", r"\bEURUSD\b", r"\bGBPUSD\b"],
    "commodities": [r"\bcommodit(y|ies)\b", r"\bgold\b", r"\bsilver\b", r"\bcopper\b", r"\boil\b", r"\bWTI\b", r"\bBrent\b", r"\bGLD\b", r"\bSLV\b"],
}

DEFAULT_GEO_RULES = {
    "US": [r"\bUS\b", r"\bUnited States\b", r"\bAmerica\b", r"\bUS economy\b", r"\bFederal Reserve\b", r"\bFOMC\b"],
    "Europe": [r"\bEurope\b", r"\bEU\b", r"\bEurozone\b", r"\bECB\b", r"\bEuropean Central Bank\b", r"\bGermany\b", r"\bFrance\b"],
    "China": [r"\bChina\b", r"\bBeijing\b", r"\bShanghai\b", r"\bHong Kong\b", r"\byuan\b", r"\bPBOC\b"],
    "Global": [r"\bglobal\b", r"\bworldwide\b", r"\binternational\b", r"\bG7\b", r"\bG20\b", r"\bIMF\b", r"\bWorld Bank\b"],
    "EM": [r"\bemerging markets?\b", r"\bdeveloping countries\b", r"\bBRICS\b", r"\bBrazil\b", r"\bRussia\b", r"\bIndia\b", r"\bSouth Africa\b"],
}

def load_rules_from_file(file_path: str) -> Optional[Dict[str, Any]]:
    """Load rules from a JSON file. Returns None if file doesn't exist or is invalid."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        return None

def get_config_dir() -> Path:
    """Get the configuration directory path."""
    # Look for config directory relative to the src directory
    src_dir = Path(__file__).parent
    config_dir = src_dir.parent / "config"

    # Create config directory if it doesn't exist
    config_dir.mkdir(exist_ok=True)
    return config_dir

def load_topic_rules() -> Dict[str, List[str]]:
    """Load topic rules from config file or use defaults."""
    config_dir = get_config_dir()
    config_file = config_dir / "topics.json"

    config = load_rules_from_file(str(config_file))
    if config:
        # Validate that it's a dict of lists
        if isinstance(config, dict):
            validated = {}
            for key, value in config.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    validated[key] = value
                else:
                    print(f"Warning: Invalid topic rule for '{key}', using default")
            if validated:
                return validated

    return DEFAULT_TOPIC_RULES

def load_asset_class_rules() -> Dict[str, List[str]]:
    """Load asset class rules from config file or use defaults."""
    config_dir = get_config_dir()
    config_file = config_dir / "asset_classes.json"

    config = load_rules_from_file(str(config_file))
    if config:
        # Validate format
        if isinstance(config, dict):
            validated = {}
            for key, value in config.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    validated[key] = value
                else:
                    print(f"Warning: Invalid asset class rule for '{key}', using default")
            if validated:
                return validated

    return DEFAULT_ASSET_CLASS_RULES

def load_geo_rules() -> Dict[str, List[str]]:
    """Load geographic rules from config file or use defaults."""
    config_dir = get_config_dir()
    config_file = config_dir / "geo.json"

    config = load_rules_from_file(str(config_file))
    if config:
        # Validate format
        if isinstance(config, dict):
            validated = {}
            for key, value in config.items():
                if isinstance(value, list) and all(isinstance(item, str) for item in value):
                    validated[key] = value
                else:
                    print(f"Warning: Invalid geo rule for '{key}', using default")
            if validated:
                return validated

    return DEFAULT_GEO_RULES

def create_example_configs():
    """Create example configuration files for reference."""
    config_dir = get_config_dir()

    # Create example topic rules
    example_topics = {
        "crypto": [r"\bcrypto\b", r"\bbitcoin\b", r"\bethereum\b"],
        "startups": [r"\bstartup(s)?\b", r"\bVC\b"],
        "custom_topic": [r"\bcustom keyword\b"]
    }

    with open(config_dir / "topics_example.json", 'w') as f:
        json.dump(example_topics, f, indent=2)

    # Create example asset class rules
    example_assets = {
        "crypto_assets": [r"\bcrypto\b", r"\bbitcoin\b"],
        "custom_asset": [r"\bcustom asset\b"]
    }

    with open(config_dir / "asset_classes_example.json", 'w') as f:
        json.dump(example_assets, f, indent=2)

    print(f"Created example config files in {config_dir}")
    print("Rename _example.json files to .json to use them")

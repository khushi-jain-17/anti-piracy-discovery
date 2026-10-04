"""Allowlist configuration for Official and Authorized domains."""

ALLOWLIST_DOMAINS = {
    # Core DAZN Group & Rights Holders
    "dazn.com",
    "www.dazn.com",
    "foxtel.com.au",
    "www.foxtel.com.au",
    "kayosports.com.au",
    "www.kayosports.com.au",
    "binge.com.au",
    "www.binge.com.au",
    "indazn.com",

    # Official Sports Leagues & Content Partners
    "motogp.com",
    "formula1.com",
    "f1.com",
    "uefa.com",
    "fifa.com",
    "nfl.com",
    "nba.com",

    # Search Engines (to prevent indexing engines from being flagged as pirate hosts)
    "baidu.com",
    "yandex.com",
    "yandex.ru",
    "bing.com",

    # Official Social Media & App Distribution
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "twitter.com",
    "x.com",
    "facebook.com",
    "www.facebook.com",
    "instagram.com",
    "www.instagram.com",
    "apps.apple.com",
    "play.google.com",

    # Major Legitimate News & Sports Outlets
    "wikipedia.org",
    "en.wikipedia.org",
    "bbc.com",
    "bbc.co.uk",
    "espn.com",
    "espn.co.uk",
    "skysports.com",
    "www.skysports.com",
    "foxsports.com.au",
    "marca.com",
    "theguardian.com",
    "reuters.com",
    "bloomberg.com",
}

ALLOWLIST_PATTERNS = [
    r"^([a-z0-9-]+\.)*dazn\.com$",
    r"^([a-z0-9-]+\.)*foxtel\.com\.au$",
    r"^([a-z0-9-]+\.)*kayosports\.com\.au$",
    r"^([a-z0-9-]+\.)*binge\.com\.au$",
    r"^([a-z0-9-]+\.)*google\.com$",
    r"^([a-z0-9-]+\.)*apple\.com$",
]

def is_domain_allowlisted(domain: str) -> bool:
    """Check if domain or any parent domain matches the allowlist."""
    domain = domain.lower().strip()
    if domain in ALLOWLIST_DOMAINS:
        return True
    
    # Check parent domain matches (e.g. news.bbc.co.uk -> bbc.co.uk, sports.espn.com -> espn.com)
    for base in ALLOWLIST_DOMAINS:
        if domain.endswith("." + base):
            return True

    return False


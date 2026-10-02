"""Configuration package for Anti-Piracy Discovery & Verification System."""
from .settings import settings
from .allowlist import ALLOWLIST_DOMAINS, ALLOWLIST_PATTERNS, is_domain_allowlisted
from .heuristics import PIRACY_KEYWORDS, BRAND_TERMS, IMPERSONATION_DOMAINS, HIGH_RISK_TLDS, AD_NETWORK_DOMAINS, WEIGHTS

__all__ = [
    "settings",
    "ALLOWLIST_DOMAINS",
    "ALLOWLIST_PATTERNS",
    "is_domain_allowlisted",
    "PIRACY_KEYWORDS",
    "BRAND_TERMS",
    "IMPERSONATION_DOMAINS",
    "HIGH_RISK_TLDS",
    "AD_NETWORK_DOMAINS",
    "WEIGHTS",
]


import re
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from config import (
    ALLOWLIST_DOMAINS,
    ALLOWLIST_PATTERNS,
    is_domain_allowlisted,
    PIRACY_KEYWORDS,
    BRAND_TERMS,
    IMPERSONATION_DOMAINS,
    HIGH_RISK_TLDS,
    AD_NETWORK_DOMAINS,
    WEIGHTS,
)
from discovery.base import SearchResult
from .network_lookup import NetworkLookupHelper

logger = logging.getLogger(__name__)

class ClassificationResult(BaseModel):
    search_result: SearchResult
    classification: str  # Official / Pirate / Uncertain
    confidence_score: int  # 0 - 100
    matched_heuristics: List[str]
    hosting_ip: str = "Unknown"
    asn: str = "Unknown"

class DomainClassifier:
    def __init__(self):
        self.allowlist_domains = ALLOWLIST_DOMAINS
        self.allowlist_patterns = [re.compile(p, re.IGNORECASE) for p in ALLOWLIST_PATTERNS]
        self.lookup_helper = NetworkLookupHelper()

    def classify(self, search_result: SearchResult, body_text: Optional[str] = None) -> ClassificationResult:
        domain = search_result.domain.lower()
        url = search_result.url.lower()
        title = search_result.page_title.lower()
        snippet = search_result.snippet.lower()
        body = (body_text or "").lower()

        matched_signals = []
        score = 0

        # 1. Check Allowlist (Official check)
        is_allowlisted = is_domain_allowlisted(domain)
        if not is_allowlisted:
            for pat in self.allowlist_patterns:
                if pat.search(domain):
                    is_allowlisted = True
                    break

        if is_allowlisted:
            hosting_info = self.lookup_helper.get_hosting_info(domain)
            return ClassificationResult(
                search_result=search_result,
                classification="Official",
                confidence_score=95,
                matched_heuristics=["ALLOWLIST_MATCH"],
                hosting_ip=hosting_info.get("hosting_ip", "Unknown"),
                asn=hosting_info.get("asn", "Unknown"),
            )

        # 2. Check Network & WHOIS/RDAP Privacy (Bonus signal)
        hosting_info = self.lookup_helper.get_hosting_info(domain)
        if hosting_info.get("is_privacy_whois"):
            score += WEIGHTS.get("ANONYMOUS_WHOIS", 15)
            matched_signals.append("ANONYMOUS_WHOIS_PRIVACY")

        # 3. Check Known Impersonation Domains or Brand Impersonation in domain
        if domain in IMPERSONATION_DOMAINS or any(domain.endswith("." + imp) for imp in IMPERSONATION_DOMAINS):
            score += WEIGHTS["BRAND_IMPERSONATION"]
            matched_signals.append("KNOWN_IMPERSONATION_DOMAIN")
        elif any(brand in domain for brand in BRAND_TERMS):
            score += WEIGHTS["BRAND_IMPERSONATION"]
            matched_signals.append("BRAND_IMPERSONATION")

        # 4. Check High-Risk TLDs
        if any(domain.endswith(tld) for tld in HIGH_RISK_TLDS):
            score += WEIGHTS["HIGH_RISK_TLD"]
            matched_signals.append("HIGH_RISK_TLD")

        # 5. Check Piracy Keywords in Domain
        domain_piracy = [kw for kw in ["stream", "live", "crack", "free", "iptv", "zhibo", "kanqiu", "hd"] if kw in domain]
        if domain_piracy:
            score += WEIGHTS["PIRACY_KEYWORD_IN_DOMAIN"]
            matched_signals.append(f"PIRACY_KEYWORD_IN_DOMAIN({','.join(domain_piracy)})")

        # 6. Check Piracy Keywords in URL Path
        url_kw_matches = [kw for kw in PIRACY_KEYWORDS if kw in url]
        if url_kw_matches:
            score += WEIGHTS["PIRACY_KEYWORD_IN_URL"]
            matched_signals.append(f"PIRACY_KEYWORD_IN_URL({len(url_kw_matches)})")

        # 7. Check Piracy Keywords in Title
        title_kw_matches = [kw for kw in PIRACY_KEYWORDS if kw in title]
        if title_kw_matches:
            score += WEIGHTS["PIRACY_KEYWORD_IN_TITLE"]
            matched_signals.append(f"PIRACY_KEYWORD_IN_TITLE({len(title_kw_matches)})")

        # 8. Check Piracy Keywords in Snippet
        snippet_kw_matches = [kw for kw in PIRACY_KEYWORDS if kw in snippet]
        if snippet_kw_matches:
            score += WEIGHTS["PIRACY_KEYWORD_IN_SNIPPET"]
            matched_signals.append(f"PIRACY_KEYWORD_IN_SNIPPET({len(snippet_kw_matches)})")

        # 9. Check Piracy Keywords in Body (if present)
        if body:
            body_kw_matches = [kw for kw in PIRACY_KEYWORDS if kw in body]
            if body_kw_matches:
                score += WEIGHTS.get("PIRACY_KEYWORD_IN_BODY", 20)
                matched_signals.append(f"PIRACY_KEYWORD_IN_BODY({len(body_kw_matches)})")

        # 10. Check Aggressive Ad Networks / Pop-up Scripts
        full_text = f"{url} {title} {snippet} {body}"
        matched_ads = [ad for ad in AD_NETWORK_DOMAINS if ad in full_text]
        if matched_ads:
            score += WEIGHTS.get("AGGRESSIVE_ADS_OR_POPUPS", 25)
            matched_signals.append(f"AGGRESSIVE_ADS_OR_POPUPS({','.join(matched_ads)})")

        # Clamp confidence score 0 to 100
        confidence = min(100, max(0, score))

        # Assign label
        if confidence >= 40:
            classification = "Pirate"
        elif confidence >= 20:
            classification = "Uncertain"
        else:
            classification = "Official"

        return ClassificationResult(
            search_result=search_result,
            classification=classification,
            confidence_score=confidence,
            matched_heuristics=matched_signals,
            hosting_ip=hosting_info.get("hosting_ip", "Unknown"),
            asn=hosting_info.get("asn", "Unknown"),
        )


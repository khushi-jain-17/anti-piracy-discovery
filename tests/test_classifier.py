import pytest
from discovery.base import SearchResult
from classification.classifier import DomainClassifier
import pytest
from discovery.base import SearchResult
from classification.classifier import DomainClassifier
from reporting.exporter import ReportExporter

def test_allowlist_seed_list_and_subdomains():
    classifier = DomainClassifier()
    seed_domains = [
        ("https://www.dazn.com/en-GLOBAL/welcome", "dazn.com"),
        ("https://foxtel.com.au/sports", "foxtel.com.au"),
        ("https://kayosports.com.au/live", "kayosports.com.au"),
        ("https://binge.com.au/watch", "binge.com.au"),
        ("https://www.youtube.com/user/dazn", "www.youtube.com"),
        ("https://apps.apple.com/us/app/dazn/id1129523589", "apps.apple.com"),
        ("https://play.google.com/store/apps/details?id=com.dazn", "play.google.com"),
        ("https://news.bbc.co.uk/sport/dazn", "news.bbc.co.uk"),
        ("https://sports.espn.com/article/dazn-deal", "sports.espn.com"),
    ]
    for url, domain in seed_domains:
        res = SearchResult(
            query="DAZN sports",
            search_engine="Yandex",
            rank=1,
            url=url,
            domain=domain,
            page_title="Official / News Media Page",
            snippet="Official coverage"
        )
        classified = classifier.classify(res)
        assert classified.classification == "Official", f"Failed for {domain}"
        assert "ALLOWLIST_MATCH" in classified.matched_heuristics

def test_impersonation_and_heuristics():
    classifier = DomainClassifier()
    # Test brand impersonation example from spec: dazn.love, dazn-live.xyz
    for imp_domain in ["dazn.love", "dazn-live.xyz"]:
        res = SearchResult(
            query="watch DAZN live free",
            search_engine="Yandex",
            rank=1,
            url=f"https://{imp_domain}/watch-hd-stream",
            domain=imp_domain,
            page_title="Watch DAZN Live Stream Free HD online IPTV",
            snippet="Free live stream popads.net"
        )
        classified = classifier.classify(res)
        assert classified.classification == "Pirate"
        assert classified.confidence_score >= 40
        assert any("IMPERSONATION" in h for h in classified.matched_heuristics)

def test_hd_keyword_and_ad_network_heuristics():
    classifier = DomainClassifier()
    res = SearchResult(
        query="free sports hd stream",
        search_engine="Baidu",
        rank=2,
        url="http://sports-free.top/hd-stream",
        domain="sports-free.top",
        page_title="Watch HD Sports Stream Free",
        snippet="Free HD live stream popads.net"
    )
    classified = classifier.classify(res)
    assert classified.classification == "Pirate"
    assert any("PIRACY_KEYWORD" in h for h in classified.matched_heuristics)
    assert any("AGGRESSIVE_ADS_OR_POPUPS" in h for h in classified.matched_heuristics)

def test_pirate_only_export_exclusion(tmp_path):
    exporter = ReportExporter(output_dir=tmp_path)
    records = [
        {"domain": "dazn.com", "classification": "Official", "confidence_score": 95},
        {"domain": "dazn.love", "classification": "Pirate", "confidence_score": 85},
        {"domain": "uncertain-stream.site", "classification": "Uncertain", "confidence_score": 30},
    ]
    out = exporter.export_pirates_only(records, "pirates.csv", "pirates.json")
    import pandas as pd
    df = pd.read_csv(out["csv"])
    domains = df["domain"].tolist()
    assert "dazn.com" not in domains
    assert "dazn.love" in domains
    assert "uncertain-stream.site" in domains


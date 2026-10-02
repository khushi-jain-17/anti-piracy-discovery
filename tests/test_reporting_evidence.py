import pytest
from pathlib import Path
from reporting.exporter import ReportExporter, MANDATORY_FIELDS
from reporting.summary import SummaryReporter
from evidence.screenshot import ScreenshotCapturer

def test_mandatory_fields_presence():
    required_keys = [
        "search_engine", "query", "rank", "url", "domain", "classification",
        "confidence_score", "player_detected", "player_type", "player_status",
        "stream_source", "screenshot_path", "checked_at_utc", "hosting_ip"
    ]
    for key in required_keys:
        assert key in MANDATORY_FIELDS, f"Missing required field {key} in MANDATORY_FIELDS"

def test_summary_reporter_output(tmp_path):
    records = [
        {"domain": "dazn.com", "classification": "Official", "player_detected": False, "player_status": "Not Applicable"},
        {"domain": "dazn.love", "classification": "Pirate", "player_detected": True, "player_status": "Player Present - Playing"},
        {"domain": "dazn-live.xyz", "classification": "Pirate", "player_detected": True, "player_status": "Player Present - Playing"},
    ]
    summary = SummaryReporter.generate_summary(records)
    assert summary["total_discovered"] == 3
    assert summary["total_official"] == 1
    assert summary["total_pirate"] == 2
    assert summary["players_detected"] == 2
    assert summary["actively_playing"] == 2

def test_fallback_card_generation(tmp_path):
    capturer = ScreenshotCapturer(output_dir=tmp_path)
    card_path = capturer.generate_fallback_card(
        filename="fallback_test.png",
        url="https://offline-pirate.xyz",
        domain="offline-pirate.xyz",
        timestamp_utc="2026-10-02 12:00:00",
        error_msg="DNS Resolution Failed"
    )
    assert Path(tmp_path / "fallback_test.png").exists()

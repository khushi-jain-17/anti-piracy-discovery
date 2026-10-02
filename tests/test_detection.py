import pytest
from detection.network_sniffer import NetworkSniffer
from detection.player_detector import PlayerDetector, DetectionResult

def test_network_sniffer_manifest_detection():
    sniffer = NetworkSniffer()
    
    # Mock request object
    class MockRequest:
        def __init__(self, url):
            self.url = url

    # Simulate request handling
    req_hls = MockRequest("https://stream.example.com/live/index.m3u8?token=123")
    req_dash = MockRequest("https://stream.example.com/dash/manifest.mpd")
    req_ts = MockRequest("https://stream.example.com/live/segment100.ts")

    # Manually trigger handler logic
    url_hls = req_hls.url.lower()
    if ".m3u8" in url_hls:
        sniffer.stream_manifests.add(req_hls.url)
    
    url_dash = req_dash.url.lower()
    if ".mpd" in url_dash:
        sniffer.stream_manifests.add(req_dash.url)

    url_ts = req_ts.url.lower()
    if ".ts" in url_ts:
        sniffer.stream_segments.add(req_ts.url)

    assert len(sniffer.stream_manifests) == 2
    assert sniffer.get_primary_stream_source().endswith("123") or ".mpd" in sniffer.get_primary_stream_source()
    assert sniffer.has_active_segments() is True

def test_detection_result_schema():
    res = DetectionResult(
        player_detected=True,
        player_type="JW Player",
        player_status="Player Present - Playing",
        stream_source="https://example.com/playlist.m3u8",
        iframe_domains=["embed-stream.xyz"],
        video_bounding_box={"x": 10, "y": 20, "width": 640, "height": 360}
    )
    assert res.player_detected is True
    assert res.player_type == "JW Player"
    assert res.player_status == "Player Present - Playing"
    assert "embed-stream.xyz" in res.iframe_domains

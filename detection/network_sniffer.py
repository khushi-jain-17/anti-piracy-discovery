import logging
from typing import List, Set
from playwright.async_api import Page, Response, Request

logger = logging.getLogger(__name__)

class NetworkSniffer:
    def __init__(self):
        self.stream_manifests: Set[str] = set()
        self.stream_segments: Set[str] = set()

    def attach_to_page(self, page: Page):
        """Attach network request listeners to sniff stream manifests and media segments."""
        self.stream_manifests.clear()
        self.stream_segments.clear()

        def handle_request(request: Request):
            url = request.url.lower()
            if any(ign in url for ign in ["analytics", "tracker", "beacon", "telemetry"]):
                return

            # Check HLS / DASH manifest patterns
            if any(m in url for m in [".m3u8", ".mpd", "playlist.m3u", "manifest.mpd", "hls/"]):
                self.stream_manifests.add(request.url)
                logger.info(f"[NetworkSniffer] Stream manifest detected: {request.url[:80]}...")
            
            # Check HLS / DASH segment chunks
            elif any(seg in url for seg in [".ts", ".m4s", "fragment", "segment", ".init.mp4", ".fmp4"]):
                self.stream_segments.add(request.url)

        page.on("request", handle_request)

    def get_primary_stream_source(self) -> str:
        if self.stream_manifests:
            return list(self.stream_manifests)[0]
        elif self.stream_segments:
            return list(self.stream_segments)[0]
        return ""

    def has_active_segments(self) -> bool:
        return len(self.stream_segments) > 0


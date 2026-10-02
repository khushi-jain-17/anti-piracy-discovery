import asyncio
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from playwright.async_api import Page, Frame
from config import settings
from .network_sniffer import NetworkSniffer

logger = logging.getLogger(__name__)

class DetectionResult(BaseModel):
    player_detected: bool
    player_type: str  # HTML5, JW Player, Video.js, Clappr, hls.js, Flowplayer, Plyr, iframe, etc.
    player_status: str  # No Player / Player Present - Not Playing / Player Present - Playing
    stream_source: str = ""
    iframe_domains: List[str] = []
    video_bounding_box: Optional[Dict[str, float]] = None

KNOWN_PLAYER_SCRIPTS = [
    ("JW Player", ["jwplayer", "jw-video", "jw-player"]),
    ("Video.js", ["video-js", "vjs-tech", "videojs"]),
    ("Clappr", ["clappr", "clappr-player"]),
    ("hls.js", ["hls.js", "Hls"]),
    ("Flowplayer", ["flowplayer"]),
    ("Plyr", ["plyr"]),
    ("DPlayer", ["dplayer"]),
    ("dash.js", ["dashjs", "dash.js"]),
]

class PlayerDetector:
    def __init__(self, wait_seconds: int = None):
        self.wait_seconds = wait_seconds or settings.PLAYER_DETECTION_WAIT_SEC

    async def detect(self, page: Page, sniffer: NetworkSniffer) -> DetectionResult:
        """Inspect page and child frames for HTML5 video, JS player instances, iframes, and active playback status."""
        # 1. Check HTML5 <video> elements across main page and frames
        html5_info = await self._check_html5_video(page)
        
        # 2. Check JS player libraries in global window scope
        js_player_type = await self._check_js_players(page)

        # 3. Check <iframe> embedded players and extract source domains
        iframe_info = await self._check_iframe_players(page)

        # 4. Check stream manifest network sniffing result (.m3u8, .mpd)
        manifest_url = sniffer.get_primary_stream_source()
        has_active_stream = sniffer.has_active_segments() or bool(manifest_url)

        # Determine overall player type
        player_type = "None"
        if html5_info.get("detected"):
            player_type = js_player_type if js_player_type != "None" else "HTML5 Video"
        elif iframe_info.get("detected"):
            player_type = f"iframe ({iframe_info.get('embed_domain', 'embed')})"
        elif js_player_type != "None":
            player_type = js_player_type
        elif manifest_url:
            player_type = "HLS/DASH Stream"

        player_detected = (player_type != "None")

        # Determine playback status
        player_status = "No Player"
        if player_detected:
            # Check if video currentTime advanced, paused is False, or active streaming manifests/segments are detected
            is_playing = html5_info.get("playing", False) or has_active_stream

            if not is_playing and html5_info.get("detected"):
                # Wait briefly to measure if currentTime advances over time
                initial_time = html5_info.get("currentTime", 0)
                await asyncio.sleep(2)
                html5_recheck = await self._check_html5_video(page)
                current_time = html5_recheck.get("currentTime", 0)
                if current_time > initial_time or (html5_recheck.get("detected") and not html5_recheck.get("paused")):
                    is_playing = True

            player_status = "Player Present - Playing" if is_playing else "Player Present - Not Playing"

        # Determine stream source
        stream_source = manifest_url or html5_info.get("src") or iframe_info.get("src", "")
        iframe_domains = iframe_info.get("iframe_domains", [])

        return DetectionResult(
            player_detected=player_detected,
            player_type=player_type,
            player_status=player_status,
            stream_source=stream_source,
            iframe_domains=iframe_domains,
            video_bounding_box=html5_info.get("bounding_box") or iframe_info.get("bounding_box")
        )

    async def _check_html5_video(self, page: Page) -> Dict[str, Any]:
        js_code = """
        () => {
            const videos = Array.from(document.querySelectorAll('video'));
            if (videos.length === 0) return { detected: false };
            
            // Find active or main video
            let v = videos[0];
            for (let vid of videos) {
                if (!vid.paused || vid.currentTime > 0) {
                    v = vid;
                    break;
                }
            }
            const rect = v.getBoundingClientRect();
            return {
                detected: true,
                paused: v.paused,
                currentTime: v.currentTime || 0,
                duration: v.duration || 0,
                readyState: v.readyState || 0,
                playing: !v.paused && (v.currentTime > 0 || v.readyState >= 2),
                src: v.src || (v.querySelector('source') ? v.querySelector('source').src : ''),
                bounding_box: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
            };
        }
        """
        try:
            res = await page.evaluate(js_code)
            if isinstance(res, dict) and res.get("detected"):
                return res
            
            # Check Playwright child frames if main frame yielded no video tag
            for frame in page.frames[1:]:
                try:
                    f_res = await frame.evaluate(js_code)
                    if isinstance(f_res, dict) and f_res.get("detected"):
                        return f_res
                except Exception:
                    continue

            return {"detected": False}
        except Exception as e:
            logger.debug(f"HTML5 video check error: {e}")
            return {"detected": False}

    async def _check_js_players(self, page: Page) -> str:
        js_code = """
        () => {
            let found = [];
            if (window.jwplayer || document.querySelector('.jwplayer')) found.push("JW Player");
            if (window.videojs || document.querySelector('.video-js, .vjs-tech')) found.push("Video.js");
            if (window.Clappr || document.querySelector('.clappr-player')) found.push("Clappr");
            if (window.Hls || document.querySelector('[data-hls]')) found.push("hls.js");
            if (window.flowplayer || document.querySelector('.flowplayer')) found.push("Flowplayer");
            if (window.Plyr || document.querySelector('.plyr')) found.push("Plyr");
            if (window.DPlayer || document.querySelector('.dplayer')) found.push("DPlayer");
            if (window.dashjs) found.push("dash.js");
            return found;
        }
        """
        try:
            players = await page.evaluate(js_code)
            if players and isinstance(players, list) and len(players) > 0:
                return players[0]
            
            # Also check child frames
            for frame in page.frames[1:]:
                try:
                    f_players = await frame.evaluate(js_code)
                    if f_players and isinstance(f_players, list) and len(f_players) > 0:
                        return f_players[0]
                except Exception:
                    continue
        except Exception:
            pass
        return "None"

    async def _check_iframe_players(self, page: Page) -> Dict[str, Any]:
        js_code = """
        () => {
            const iframes = Array.from(document.querySelectorAll('iframe'));
            let detected = false;
            let primarySrc = '';
            let primaryDomain = '';
            let boundingBox = null;
            let domains = [];

            for (let f of iframes) {
                const src = f.src || f.getAttribute('data-src') || '';
                if (!src) continue;

                let domain = '';
                try {
                    domain = new URL(src).hostname;
                } catch(e) {
                    if (src.includes('//')) {
                        domain = src.split('//')[1].split('/')[0];
                    }
                }
                if (domain) domains.push(domain);

                const rect = f.getBoundingClientRect();
                const isPlayerIframe = (rect.width > 200 && rect.height > 150) || 
                                       /player|embed|stream|m3u8|hls|live|video|vidsrc|ok\\.ru|vk\\.com/i.test(src);

                if (isPlayerIframe && !detected) {
                    detected = true;
                    primarySrc = src;
                    primaryDomain = domain || 'iframe';
                    boundingBox = { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
                }
            }
            return {
                detected: detected,
                src: primarySrc,
                embed_domain: primaryDomain,
                iframe_domains: Array.from(new Set(domains)),
                bounding_box: boundingBox
            };
        }
        """
        try:
            res = await page.evaluate(js_code)
            if isinstance(res, dict) and res.get("detected"):
                return res
        except Exception:
            pass
        return {"detected": False, "iframe_domains": []}


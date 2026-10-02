import datetime
import logging
from pathlib import Path
from typing import Dict, Any
from config import settings

logger = logging.getLogger(__name__)

class TakedownNoticeGenerator:
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or settings.TAKEDOWN_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_notice(self, record: Dict[str, Any]) -> str:
        """Generate a DMCA Takedown Notice Markdown document for a confirmed pirate domain."""
        domain = record.get("domain", "unknown")
        url = record.get("url", "")
        stream_source = record.get("stream_source", "N/A")
        hosting_ip = record.get("hosting_ip", "Unknown")
        asn = record.get("asn", "Unknown")
        timestamp = record.get("checked_at_utc", datetime.datetime.now(datetime.timezone.utc).isoformat())

        safe_domain = domain.replace(".", "_")
        filename = f"DMCA_Takedown_{safe_domain}.md"
        filepath = self.output_dir / filename

        content = f"""# DIGITAL MILLENNIUM COPYRIGHT ACT (DMCA) TAKEDOWN NOTICE

**To:** Abuse Department / Designated Copyright Agent  
**Host / Network Operator:** {asn} ({hosting_ip})  
**Date:** {timestamp}  

---

### 1. Rights Holder Identification
- **Copyright Owner:** DAZN Group Limited (and affiliated entities Foxtel, Kayo Sports, Binge)
- **Authorized Representative:** DAZN Content Protection Automation Team
- **Contact Email:** anti-piracy@dazn.com

---

### 2. Infringing Work Identified
- **Protected Content:** Exclusive Live Sports Broadcast Rights (UEFA Champions League, Formula 1, Moto GP, Premier League)
- **Authorized Platform:** https://www.dazn.com / https://www.kayosports.com.au / https://www.foxtel.com.au

---

### 3. Infringing Material & Evidence Details
- **Infringing Target URL:** [{url}]({url})
- **Infringing Domain:** `{domain}`
- **Hosting IP / ASN:** `{hosting_ip}` ({asn})
- **Discovered Stream Source / Manifest:** `{stream_source}`
- **Evidence Timestamp (UTC):** `{timestamp}`
- **Evidence Screenshot:** `{record.get("screenshot_path", "N/A")}`

---

### 4. Statement of Good Faith & Accuracy
I have a good faith belief that the use of the copyrighted material described above is not authorized by the copyright owner, its agent, or the law. The information in this notification is accurate, and under penalty of perjury, I declare that I am authorized to act on behalf of DAZN Group.

**Signed:**  
*DAZN Group Anti-Piracy Specialist*
"""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"[Takedown] Generated DMCA notice: {filename}")
            return str(filepath.relative_to(settings.BASE_DIR))
        except Exception as e:
            logger.error(f"[Takedown] Failed to generate notice for {domain}: {e}")
            return ""
        

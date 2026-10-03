import socket
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class NetworkLookupHelper:
    @staticmethod
    def get_hosting_info(domain: str) -> Dict[str, Any]:
        """Resolve IP address and lookup ASN / Hosting info using free RDAP/ip-api endpoint."""
        info = {
            "hosting_ip": "Unknown",
            "asn": "Unknown",
            "org": "Unknown",
            "country": "Unknown",
            "is_privacy_whois": False  # unknown unless a real WHOIS/RDAP lookup proves privacy
        }
        try:
            # 1. Resolve IP via socket
            ip = socket.gethostbyname(domain)
            info["hosting_ip"] = ip

            # 2. Query ip-api for ASN/Hosting info (free rate-limited endpoint)
            resp = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,org,as,query", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    info["asn"] = data.get("as", "Unknown")
                    info["org"] = data.get("org", "Unknown")
                    info["country"] = data.get("country", "Unknown")
        except Exception as e:
            logger.debug(f"Network lookup for domain {domain} failed: {e}")

        return info

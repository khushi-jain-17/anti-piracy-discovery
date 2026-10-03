import requests
import os

headers = {"User-Agent": "AntiPiracyResearchBot/1.0 (anti-piracy@example.com)"}

api_url = "https://commons.wikimedia.org/w/api.php"
params = {
    "action": "query",
    "generator": "search",
    "gsrsearch": "DAZN logo",
    "gsrnamespace": "6",
    "prop": "imageinfo",
    "iiprop": "url",
    "iiurlwidth": "400",
    "format": "json"
}

target_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "reference_logos")
os.makedirs(target_dir, exist_ok=True)

try:
    r = requests.get(api_url, params=params, headers=headers, timeout=10)
    data = r.json()
    pages = data.get("query", {}).get("pages", {})
    for page_id, page_info in pages.items():
        title = page_info.get("title", "")
        img_info = page_info.get("imageinfo", [{}])[0]
        thumb_url = img_info.get("thumburl") or img_info.get("url")
        if thumb_url and ("logo" in title.lower() or "dazn" in title.lower()):
            clean_name = title.replace("File:", "").replace(" ", "_").replace(".svg", ".png")
            resp = requests.get(thumb_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                with open(os.path.join(target_dir, clean_name), "wb") as f:
                    f.write(resp.content)
                print(f"Downloaded authentic asset: {clean_name} ({len(resp.content)} bytes)")
except Exception as e:
    print(f"API query failed: {e}")

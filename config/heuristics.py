"""Heuristics definition for piracy signal classification."""

PIRACY_KEYWORDS = [
    # English
    "free", "stream", "live stream", "watch online", "watch free", "live online",
    "iptv", "m3u", "sports stream", "crackstreams", "buffstreams", "viprow",
    "vipleague", "hesgoal", "freestreams-live1", "stream2watch", "livesoccertv",
    "hd", "hd stream", "full hd", "1080p stream", "direct stream", "free sports",
    
    # Russian
    "смотреть онлайн", "бесплатно", "прямой эфир", "трансляция",
    "смотреть бесплатно", "прямая трансляция", "сопки", "sopcast", "acestream",
    "онлайн трансляция", "спорт трансляция",

    # Chinese
    "直播", "在线观看", "免费", "高清直播", "免费直播", "无插件",
    "体育直播", "足球直播", "赛事实时直播", "免费在线",
]

BRAND_TERMS = [
    "dazn", "kayo", "foxtel", "binge", "motogp", "formula1", "f1"
]

IMPERSONATION_DOMAINS = [
    "dazn.love", "dazn-live.xyz", "watchdazn.com", "daznstream.net",
    "kayosportsfree.com", "foxtelstream.xyz", "bingetvfree.com"
]

HIGH_RISK_TLDS = [
    ".xyz", ".top", ".cc", ".to", ".live", ".stream", ".site", ".ru", ".cn", ".pw", ".info", ".online", ".me", ".app", ".buzz", ".cx", ".tv"
]

AD_NETWORK_DOMAINS = [
    "popads.net", "popcash.net", "exoclick.com", "juicyads.com", "adsterra.com",
    "1xbet.com", "bet365.com", "propellerads.com", "clickadu.com", "hilltopads.com"
]

# Scoring Weights
WEIGHTS = {
    "ALLOWLIST_MATCH": -100,         # Instantly Official
    "BRAND_IMPERSONATION": 50,      # Domain contains brand name but isn't DAZN
    "HIGH_RISK_TLD": 20,            # .xyz, .stream, .top, .to
    "PIRACY_KEYWORD_IN_DOMAIN": 35, # 'stream', 'crack', 'iptv' in domain
    "PIRACY_KEYWORD_IN_URL": 20,    # Keywords in path/query
    "PIRACY_KEYWORD_IN_TITLE": 25,  # Keywords in HTML title
    "PIRACY_KEYWORD_IN_SNIPPET": 15, # Keywords in search snippet
    "PIRACY_KEYWORD_IN_BODY": 20,   # Keywords in HTML body
    "ANONYMOUS_WHOIS": 15,          # WHOIS privacy / missing owner
    "AGGRESSIVE_ADS_OR_POPUPS": 25, # Detection of ad networks / pop-ups
}


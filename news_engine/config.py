"""
Feed configuration — RSS/Atom sources organized by category.
"""

CATEGORIES = {
    "general": {
        "label": "General",
        "icon": "📰",
        "color": "#3b82f6",
        "feeds": [
            {"name": "BBC News", "url": "http://feeds.bbci.co.uk/news/rss.xml"},
            {"name": "NPR", "url": "https://feeds.npr.org/1001/rss.xml"},
            {"name": "PBS NewsHour", "url": "https://www.pbs.org/newshour/feeds/rss/headlines"},
            {"name": "ABC News", "url": "https://abcnews.go.com/abcnews/topstories"},
            {"name": "CBS News", "url": "https://www.cbsnews.com/latest/rss/main"},
            {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
        ],
    },
    "texas": {
        "label": "Texas / Houston",
        "icon": "⛐",
        "color": "#f59e0b",
        "feeds": [
            {"name": "Texas Tribune", "url": "https://www.texastribune.org/feeds/main/"},
            {"name": "Houston Public Media", "url": "https://www.houstonpublicmedia.org/feed/"},
            {"name": "KHOU Houston", "url": "https://www.khou.com/feeds/syndication/rss/news"},
            {"name": "San Antonio Express", "url": "https://www.expressnews.com/rss/feed/Express-News-Top-Stories-702.php"},
        ],
    },
    "tech": {
        "label": "Tech",
        "icon": "💻",
        "color": "#8b5cf6",
        "feeds": [
            {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
            {"name": "Hacker News", "url": "https://hnrss.org/frontpage"},
            {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
            {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
            {"name": "Wired", "url": "https://www.wired.com/feed/rss"},
        ],
    },
    "finance": {
        "label": "Finance",
        "icon": "💰",
        "color": "#10b981",
        "feeds": [
            {"name": "CNBC", "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html"},
            {"name": "CNBC Markets", "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html"},
            {"name": "MarketWatch", "url": "https://www.marketwatch.com/rss/topstories"},
            {"name": "Yahoo Finance", "url": "https://finance.yahoo.com/news/rssindex"},
        ],
    },
    "sports": {
        "label": "Sports",
        "icon": "🏈",
        "color": "#ef4444",
        "feeds": [
            {"name": "ESPN", "url": "https://www.espn.com/espn/rss/news"},
            {"name": "ESPN NFL", "url": "https://www.espn.com/espn/rss/nfl/news"},
            {"name": "ESPN NBA", "url": "https://www.espn.com/espn/rss/nba/news"},
            {"name": "ESPN MLB", "url": "https://www.espn.com/espn/rss/mlb/news"},
            {"name": "CBS Sports", "url": "https://www.cbssports.com/rss/headlines/"},
        ],
    },
}

# User-Agent for feed requests
USER_AGENT = "FakeNews/1.0 (Home Assistant Add-on; +https://github.com/gmarblestone/NewsApp)"

# Fetch timeout per feed (seconds)
FETCH_TIMEOUT = 10

# Max concurrent feed fetches
MAX_WORKERS = 8

# Default max articles per feed
DEFAULT_MAX_PER_FEED = 15

"""
Data models for the news engine.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Article:
    title: str
    link: str
    source: str
    category: str
    published: datetime
    summary: str = ""
    image_url: str = ""

    @property
    def time_ago(self) -> str:
        now = datetime.now(timezone.utc)
        diff = now - self.published
        seconds = diff.total_seconds()
        if seconds < 0:
            return "just now"
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            m = int(seconds / 60)
            return f"{m}m ago"
        if seconds < 86400:
            h = int(seconds / 3600)
            return f"{h}h ago"
        if seconds < 172800:
            return "Yesterday"
        d = int(seconds / 86400)
        if d < 30:
            return f"{d}d ago"
        return self.published.strftime("%m/%d")


@dataclass
class NewsFeed:
    articles: list = field(default_factory=list)
    categories_used: list = field(default_factory=list)
    generated_at: str = ""
    total_feeds: int = 0
    failed_feeds: int = 0
    error_details: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "article_count": len(self.articles),
            "categories": self.categories_used,
            "generated_at": self.generated_at,
            "total_feeds": self.total_feeds,
            "failed_feeds": self.failed_feeds,
        }

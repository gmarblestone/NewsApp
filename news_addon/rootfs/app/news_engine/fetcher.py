"""
RSS/Atom feed fetcher — parallel fetch, parse, clean, deduplicate.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup

from news_engine.config import (
    CATEGORIES,
    DEFAULT_MAX_PER_FEED,
    FETCH_TIMEOUT,
    MAX_WORKERS,
    USER_AGENT,
)
from news_engine.models import Article, NewsFeed

logger = logging.getLogger(__name__)


def _strip_html(html_str: str) -> str:
    """Remove HTML tags and clean whitespace."""
    if not html_str:
        return ""
    soup = BeautifulSoup(html_str, "html.parser")
    # Remove script/style
    for tag in soup(["script", "style", "iframe"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_image(entry) -> str:
    """Try to find an image URL from feed entry metadata."""
    # media:thumbnail
    thumbs = getattr(entry, "media_thumbnail", None)
    if thumbs and isinstance(thumbs, list) and thumbs[0].get("url"):
        return thumbs[0]["url"]
    # media:content
    media = getattr(entry, "media_content", None)
    if media and isinstance(media, list):
        for m in media:
            if m.get("type", "").startswith("image/") or m.get("medium") == "image":
                return m.get("url", "")
    # enclosures
    enclosures = getattr(entry, "enclosures", None)
    if enclosures:
        for enc in enclosures:
            if enc.get("type", "").startswith("image/"):
                return enc.get("href", enc.get("url", ""))
    # First <img> in summary
    summary = getattr(entry, "summary", "")
    if "<img" in summary:
        soup = BeautifulSoup(summary, "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]
    return ""


def _parse_date(entry) -> datetime:
    """Extract publication date from a feed entry."""
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
    return datetime.now(timezone.utc)


def _fetch_single_feed(feed_info: dict, category: str, max_articles: int) -> tuple:
    """Fetch and parse a single feed. Returns (articles, error_or_none)."""
    name = feed_info["name"]
    url = feed_info["url"]
    articles = []

    try:
        resp = requests.get(
            url,
            timeout=FETCH_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()

        feed = feedparser.parse(resp.content)

        if not feed.entries:
            logger.warning("No entries in feed: %s (%s)", name, url)
            return articles, f"{name}: no entries"

        for entry in feed.entries[:max_articles]:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            if not title or not link:
                continue

            # Get best summary
            summary_html = ""
            content = getattr(entry, "content", None)
            if content and isinstance(content, list) and content[0].get("value"):
                summary_html = content[0]["value"]
            if not summary_html:
                summary_html = getattr(entry, "summary", "")

            summary = _strip_html(summary_html)
            # Truncate
            if len(summary) > 400:
                summary = summary[:397] + "..."

            articles.append(
                Article(
                    title=title,
                    link=link,
                    source=name,
                    category=category,
                    published=_parse_date(entry),
                    summary=summary,
                    image_url=_extract_image(entry),
                )
            )

        logger.info("Fetched %d articles from %s", len(articles), name)
        return articles, None

    except Exception as e:
        logger.error("Failed to fetch %s: %s", name, e)
        return [], f"{name}: {e}"


def fetch_all_news(
    categories: list = None,
    max_per_feed: int = DEFAULT_MAX_PER_FEED,
) -> NewsFeed:
    """Fetch articles from all configured feeds in parallel."""

    if categories is None:
        categories = list(CATEGORIES.keys())

    # Build list of (feed_info, category) tuples
    tasks = []
    for cat_key in categories:
        cat = CATEGORIES.get(cat_key)
        if not cat:
            logger.warning("Unknown category: %s", cat_key)
            continue
        for feed_info in cat["feeds"]:
            tasks.append((feed_info, cat_key))

    total_feeds = len(tasks)
    all_articles = []
    errors = []

    logger.info("Fetching %d feeds across %d categories...", total_feeds, len(categories))

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(_fetch_single_feed, fi, cat, max_per_feed): (fi, cat)
            for fi, cat in tasks
        }
        for future in as_completed(futures):
            articles, error = future.result()
            all_articles.extend(articles)
            if error:
                errors.append(error)

    # Deduplicate by URL
    seen = set()
    unique = []
    for a in all_articles:
        if a.link not in seen:
            seen.add(a.link)
            unique.append(a)

    # Sort newest first
    unique.sort(key=lambda a: a.published, reverse=True)

    now = datetime.now(timezone.utc)

    try:
        from zoneinfo import ZoneInfo
        central = ZoneInfo("America/Chicago")
        now_local = now.astimezone(central)
    except Exception:
        now_local = now

    generated_at = now_local.strftime("%m/%d/%Y %I:%M %p").lstrip("0").replace("/0", "/").replace(" 0", " ")

    logger.info(
        "Fetched %d unique articles (%d feeds, %d failed)",
        len(unique), total_feeds, len(errors),
    )

    return NewsFeed(
        articles=unique,
        categories_used=categories,
        generated_at=generated_at,
        total_feeds=total_feeds,
        failed_feeds=len(errors),
        error_details=errors,
    )

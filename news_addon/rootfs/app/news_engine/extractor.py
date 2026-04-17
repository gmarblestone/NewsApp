"""
Article content extractor — downloads full articles and strips ads/junk.
Uses trafilatura for main content extraction.
Stores clean articles as HTML files organized by date.
"""

import hashlib
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    import trafilatura
except ImportError:
    trafilatura = None

from news_engine.config import FETCH_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)

# Where articles get stored (overridden in addon via parameter)
DEFAULT_ARTICLES_DIR = "articles"


def _slug(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:80].strip('-')


def _article_id(url: str) -> str:
    """Short hash of URL for unique filenames."""
    return hashlib.md5(url.encode()).hexdigest()[:10]


def extract_article(url: str) -> dict:
    """Download a URL and extract the main article content.
    
    Returns dict with keys: title, author, content_html, content_text, image_url
    """
    if trafilatura is None:
        logger.warning("trafilatura not installed — skipping article extraction")
        return {}

    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return {}

        # Extract with full options
        result = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            include_images=True,
            include_links=True,
            output_format="html",
            favor_precision=True,
        )

        # Also get plain text version for fallback
        text_result = trafilatura.extract(
            downloaded,
            include_comments=False,
            output_format="txt",
            favor_precision=True,
        )

        # Extract metadata
        metadata = trafilatura.extract_metadata(downloaded)

        return {
            "content_html": result or "",
            "content_text": text_result or "",
            "author": getattr(metadata, "author", "") or "" if metadata else "",
            "sitename": getattr(metadata, "sitename", "") or "" if metadata else "",
            "extracted_title": getattr(metadata, "title", "") or "" if metadata else "",
            "image_url": getattr(metadata, "image", "") or "" if metadata else "",
        }

    except Exception as e:
        logger.error("Failed to extract %s: %s", url, e)
        return {}


def _build_article_html(article, extracted: dict) -> str:
    """Build a clean, self-contained HTML page for a single article."""
    import html as html_mod

    title = html_mod.escape(article.title)
    source = html_mod.escape(article.source)
    author = html_mod.escape(extracted.get("author", ""))
    original_link = html_mod.escape(article.link, quote=True)
    content = extracted.get("content_html", "")
    pub_date = article.published.strftime("%B %d, %Y at %I:%M %p").replace(" 0", " ")

    author_line = f'<div class="author">By {author}</div>' if author else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
<title>{title} — Fake News Reader</title>
<style>
  :root {{
    --bg: #fafafa;
    --card-bg: #ffffff;
    --text: #1a1a1a;
    --text-secondary: #555;
    --text-muted: #888;
    --border: #e5e5e5;
    --accent: #dc2626;
    --link: #2563eb;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --text: #e2e8f0;
      --text-secondary: #94a3b8;
      --text-muted: #64748b;
      --border: #334155;
      --link: #60a5fa;
    }}
  }}
  .dark {{
    --bg: #0f172a;
    --card-bg: #1e293b;
    --text: #e2e8f0;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --border: #334155;
    --link: #60a5fa;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: Georgia, "Times New Roman", serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.8;
    -webkit-font-smoothing: antialiased;
  }}

  .top-bar {{
    position: sticky;
    top: 0;
    z-index: 100;
    background: var(--card-bg);
    border-bottom: 1px solid var(--border);
    padding: 10px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }}
  .top-bar a {{
    color: var(--accent);
    text-decoration: none;
    font-weight: 700;
    font-size: 14px;
  }}
  .top-bar-actions {{
    display: flex;
    gap: 8px;
  }}
  .top-bar-btn {{
    background: var(--bg);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    padding: 4px 12px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
  }}

  .article-container {{
    max-width: 720px;
    margin: 0 auto;
    padding: 40px 24px 80px;
  }}

  .article-header {{
    margin-bottom: 32px;
    padding-bottom: 24px;
    border-bottom: 1px solid var(--border);
  }}
  .source-tag {{
    display: inline-block;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--accent);
    margin-bottom: 12px;
  }}
  h1 {{
    font-size: 32px;
    line-height: 1.25;
    font-weight: 700;
    margin-bottom: 16px;
  }}
  .meta {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 14px;
    color: var(--text-muted);
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }}
  .author {{ color: var(--text-secondary); }}

  .article-body {{
    font-size: 19px;
    line-height: 1.8;
  }}
  .article-body p {{
    margin-bottom: 1.2em;
  }}
  .article-body h2, .article-body h3 {{
    font-size: 24px;
    margin-top: 1.5em;
    margin-bottom: 0.6em;
    line-height: 1.3;
  }}
  .article-body img {{
    max-width: 100%;
    height: auto;
    border-radius: 8px;
    margin: 1.2em 0;
  }}
  .article-body a {{
    color: var(--link);
    text-decoration: underline;
  }}
  .article-body blockquote {{
    border-left: 4px solid var(--accent);
    padding: 8px 20px;
    margin: 1.2em 0;
    color: var(--text-secondary);
    font-style: italic;
  }}
  .article-body ul, .article-body ol {{
    margin: 1em 0;
    padding-left: 1.5em;
  }}
  .article-body li {{
    margin-bottom: 0.4em;
  }}
  .article-body table {{
    width: 100%;
    border-collapse: collapse;
    margin: 1.2em 0;
    font-size: 16px;
  }}
  .article-body th, .article-body td {{
    padding: 8px 12px;
    border: 1px solid var(--border);
    text-align: left;
  }}

  .original-link {{
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid var(--border);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13px;
    color: var(--text-muted);
  }}
  .original-link a {{ color: var(--link); }}

  @media (max-width: 768px) {{
    .article-container {{ padding: 24px 16px 60px; }}
    h1 {{ font-size: 24px; }}
    .article-body {{ font-size: 17px; }}
  }}

  @media print {{
    .top-bar {{ display: none; }}
    .article-container {{ padding: 0; }}
    body {{ font-size: 12pt; }}
  }}
</style>
</head>
<body>

<div class="top-bar">
  <a href="#" id="backBtn">← FAKE NEWS</a>
  <div class="top-bar-actions">
    <button class="top-bar-btn" id="darkBtn">🌙</button>
    <button class="top-bar-btn" id="printBtn">🖨️</button>
  </div>
</div>

<div class="article-container">
  <div class="article-header">
    <div class="source-tag">{source}</div>
    <h1>{title}</h1>
    <div class="meta">
      {author_line}
      <div>{pub_date}</div>
    </div>
  </div>

  <div class="article-body">
    {content}
  </div>

  <div class="original-link">
    <a href="{original_link}" target="_blank" rel="noopener noreferrer">View original article →</a>
  </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {{
  // Back button — go back in history to restore scroll/filter state
  document.getElementById('backBtn').addEventListener('click', function(e) {{
    e.preventDefault();
    if (history.length > 1 && document.referrer) {{
      history.back();
    }} else {{
      // Articles are in articles/YYYY-MM-DD/ — go up 2 levels
      location.href = '../../';
    }}
  }});

  // Dark mode
  var darkBtn = document.getElementById('darkBtn');
  if (localStorage.getItem('fn_dark') === '1') {{
    document.body.classList.add('dark');
  }}
  darkBtn.addEventListener('click', function() {{
    document.body.classList.toggle('dark');
    var isDark = document.body.classList.contains('dark');
    localStorage.setItem('fn_dark', isDark ? '1' : '0');
  }});
  document.getElementById('printBtn').addEventListener('click', function() {{
    if (navigator.share) {{ navigator.share({{ url: location.href }}); }}
    else {{ window.print(); }}
  }});
}});
</script>

</body>
</html>"""


def save_articles(articles, articles_dir: str = DEFAULT_ARTICLES_DIR, max_workers: int = 6) -> dict:
    """Download, extract, and save articles organized by date.
    
    Returns dict mapping article.link -> relative path of saved HTML file.
    """
    if trafilatura is None:
        logger.warning("trafilatura not installed — article extraction disabled")
        return {}

    base = Path(articles_dir)
    saved = {}
    to_extract = []

    for article in articles:
        date_str = article.published.strftime("%Y-%m-%d")
        slug = _slug(article.title)
        aid = _article_id(article.link)
        filename = f"{slug}-{aid}.html"
        day_dir = base / date_str
        filepath = day_dir / filename
        rel_path = f"articles/{date_str}/{filename}"

        # Skip if already extracted today
        if filepath.exists():
            saved[article.link] = rel_path
            continue

        to_extract.append((article, day_dir, filepath, rel_path))

    if not to_extract:
        logger.info("All %d articles already cached", len(saved))
        return saved

    logger.info("Extracting %d new articles (%d cached)...", len(to_extract), len(saved))

    def _process(item):
        article, day_dir, filepath, rel_path = item
        extracted = extract_article(article.link)
        if not extracted or not extracted.get("content_html"):
            return article.link, None
        
        day_dir.mkdir(parents=True, exist_ok=True)
        html = _build_article_html(article, extracted)
        filepath.write_text(html, encoding="utf-8")
        return article.link, rel_path

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process, item): item for item in to_extract}
        for future in as_completed(futures):
            link, rel_path = future.result()
            if rel_path:
                saved[link] = rel_path

    logger.info("Extracted %d articles total", len(saved))
    return saved

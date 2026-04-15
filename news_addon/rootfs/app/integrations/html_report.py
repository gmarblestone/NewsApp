"""
Generate a self-contained HTML news page.
Clean, fast, no ads, no tracking, no cookie banners — just news.
"""

import html as html_mod
import logging
from datetime import datetime, timezone
from pathlib import Path

from news_engine.config import CATEGORIES
from news_engine.models import NewsFeed

logger = logging.getLogger(__name__)

VERSION = "1.0.1"


def _category_color(cat_key: str) -> str:
    cat = CATEGORIES.get(cat_key, {})
    return cat.get("color", "#64748b")


def _category_label(cat_key: str) -> str:
    cat = CATEGORIES.get(cat_key, {})
    return cat.get("label", cat_key.title())


def _category_icon(cat_key: str) -> str:
    cat = CATEGORIES.get(cat_key, {})
    return cat.get("icon", "📄")


def generate_html_string(feed: NewsFeed) -> str:
    """Build the complete HTML string from a NewsFeed."""

    if not feed.articles:
        return "<html><body><h1>No articles loaded</h1></body></html>"

    # Count per category
    cat_counts = {}
    for a in feed.articles:
        cat_counts[a.category] = cat_counts.get(a.category, 0) + 1

    # Build category tabs
    tabs_html = f'<button class="cat-tab active" data-category="all">All ({len(feed.articles)})</button>\n'
    for cat_key in feed.categories_used:
        count = cat_counts.get(cat_key, 0)
        if count == 0:
            continue
        label = _category_label(cat_key)
        icon = _category_icon(cat_key)
        color = _category_color(cat_key)
        tabs_html += f'    <button class="cat-tab" data-category="{cat_key}" style="--cat-color:{color}">{icon} {label} ({count})</button>\n'

    # Build article cards
    cards_html = ""
    for a in feed.articles:
        color = _category_color(a.category)
        title_escaped = html_mod.escape(a.title)
        summary_escaped = html_mod.escape(a.summary)
        source_escaped = html_mod.escape(a.source)
        link_escaped = html_mod.escape(a.link, quote=True)

        cards_html += f"""    <a href="{link_escaped}" target="_blank" rel="noopener noreferrer" class="article-card" data-category="{a.category}">
      <div class="article-meta">
        <span class="source-badge" style="background:{color}">{source_escaped}</span>
        <span class="article-time">{a.time_ago}</span>
      </div>
      <h3 class="article-title">{title_escaped}</h3>
      <p class="article-summary">{summary_escaped}</p>
    </a>
"""

    # Feed status
    status_parts = [f"{len(feed.articles)} articles"]
    if feed.failed_feeds:
        status_parts.append(f"{feed.failed_feeds}/{feed.total_feeds} feeds failed")
    else:
        status_parts.append(f"{feed.total_feeds} feeds")
    status_text = " &middot; ".join(status_parts)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
<title>Fake News</title>
<style>
  :root {{
    --bg: #f1f5f9;
    --card-bg: #ffffff;
    --text: #0f172a;
    --text-secondary: #475569;
    --text-muted: #94a3b8;
    --border: #e2e8f0;
    --header-bg: #0f172a;
    --header-text: #f8fafc;
    --accent: #dc2626;
    --tab-bg: #e2e8f0;
    --tab-active-bg: #0f172a;
    --tab-active-text: #f8fafc;
    --hover-bg: #f8fafc;
    --shadow: 0 1px 3px rgba(0,0,0,0.08);
    --shadow-hover: 0 4px 12px rgba(0,0,0,0.12);
  }}
  .dark {{
    --bg: #0f172a;
    --card-bg: #1e293b;
    --text: #e2e8f0;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --border: #334155;
    --header-bg: #020617;
    --tab-bg: #1e293b;
    --tab-active-bg: #f8fafc;
    --tab-active-text: #0f172a;
    --hover-bg: #273549;
    --shadow: 0 1px 3px rgba(0,0,0,0.3);
    --shadow-hover: 0 4px 12px rgba(0,0,0,0.4);
  }}

  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }}

  /* Header */
  .header {{
    background: var(--header-bg);
    color: var(--header-text);
    padding: 20px 24px;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  }}
  .header-inner {{
    max-width: 1400px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }}
  .brand {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .brand-icon {{ font-size: 28px; }}
  .brand h1 {{
    font-size: 26px;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: var(--accent);
    text-transform: uppercase;
  }}
  .brand-sub {{
    font-size: 11px;
    color: var(--text-muted);
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }}
  .header-actions {{
    display: flex;
    gap: 8px;
    align-items: center;
    flex-shrink: 0;
  }}
  .header-btn {{
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.15);
    color: var(--header-text);
    padding: 6px 14px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
    transition: background 0.15s;
  }}
  .header-btn:hover {{ background: rgba(255,255,255,0.2); }}

  /* Category tabs */
  .tabs-bar {{
    max-width: 1400px;
    margin: 0 auto;
    padding: 16px 24px 8px;
    display: flex;
    gap: 8px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }}
  .tabs-bar::-webkit-scrollbar {{ display: none; }}
  .cat-tab {{
    background: var(--tab-bg);
    border: none;
    color: var(--text-secondary);
    padding: 8px 16px;
    border-radius: 20px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
    white-space: nowrap;
    transition: all 0.15s;
  }}
  .cat-tab:hover {{ opacity: 0.8; }}
  .cat-tab.active {{
    background: var(--tab-active-bg);
    color: var(--tab-active-text);
  }}

  /* Article grid */
  .article-grid {{
    max-width: 1400px;
    margin: 0 auto;
    padding: 16px 24px 40px;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 16px;
  }}

  /* Article card */
  .article-card {{
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 20px;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    text-decoration: none;
    color: var(--text);
    transition: box-shadow 0.15s, transform 0.1s;
    box-shadow: var(--shadow);
  }}
  .article-card:hover {{
    box-shadow: var(--shadow-hover);
    transform: translateY(-1px);
  }}
  .article-meta {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }}
  .source-badge {{
    font-size: 11px;
    font-weight: 700;
    color: white;
    padding: 3px 10px;
    border-radius: 12px;
    letter-spacing: 0.3px;
    text-transform: uppercase;
  }}
  .article-time {{
    font-size: 12px;
    color: var(--text-muted);
    white-space: nowrap;
  }}
  .article-title {{
    font-size: 17px;
    font-weight: 700;
    line-height: 1.35;
    color: var(--text);
  }}
  .article-summary {{
    font-size: 14px;
    color: var(--text-secondary);
    line-height: 1.55;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }}

  /* Footer */
  .footer {{
    text-align: center;
    padding: 24px;
    font-size: 12px;
    color: var(--text-muted);
    border-top: 1px solid var(--border);
    max-width: 1400px;
    margin: 0 auto;
  }}

  /* Responsive */
  @media (max-width: 768px) {{
    .header {{ padding: 14px 16px; }}
    .brand h1 {{ font-size: 20px; }}
    .brand-sub {{ display: none; }}
    .header-btn {{ padding: 5px 10px; font-size: 12px; }}
    .tabs-bar {{ padding: 12px 16px 4px; }}
    .article-grid {{
      padding: 12px 16px 32px;
      grid-template-columns: 1fr;
      gap: 12px;
    }}
    .article-card {{ padding: 16px; }}
    .article-title {{ font-size: 15px; }}
    .article-summary {{ font-size: 13px; -webkit-line-clamp: 2; }}
  }}

  /* Print */
  @media print {{
    .header {{ position: static; }}
    .header-actions, .tabs-bar {{ display: none; }}
    .article-grid {{ display: block; }}
    .article-card {{
      break-inside: avoid;
      margin-bottom: 12px;
      box-shadow: none;
      border: 1px solid #ccc;
    }}
  }}
</style>
</head>
<body>

<div class="header">
  <div class="header-inner">
    <div class="brand">
      <span class="brand-icon">📰</span>
      <div>
        <h1>Fake News</h1>
        <div class="brand-sub">De-enshittified &middot; Updated {feed.generated_at}</div>
      </div>
    </div>
    <div class="header-actions">
      <button class="header-btn" id="refreshBtn">🔄 Refresh</button>
      <button class="header-btn" id="darkBtn">🌙 Dark</button>
      <button class="header-btn" id="printBtn">🖨️ Print</button>
    </div>
  </div>
</div>

<div class="tabs-bar">
  {tabs_html}
</div>

<div class="article-grid">
{cards_html}
</div>

<div class="footer">
  Fake News v{VERSION} &middot; {status_text} &middot; {feed.generated_at} &middot; No ads, no tracking, no cookies
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {{
  // Category tabs
  var tabs = document.querySelectorAll('.cat-tab');
  var cards = document.querySelectorAll('.article-card');
  tabs.forEach(function(tab) {{
    tab.addEventListener('click', function() {{
      var cat = this.dataset.category;
      tabs.forEach(function(t) {{ t.classList.remove('active'); }});
      this.classList.add('active');
      cards.forEach(function(card) {{
        card.style.display = (cat === 'all' || card.dataset.category === cat) ? '' : 'none';
      }});
    }});
  }});

  // Dark mode
  var darkBtn = document.getElementById('darkBtn');
  if (localStorage.getItem('fn_dark') === '1') {{
    document.body.classList.add('dark');
    darkBtn.textContent = '☀️ Light';
  }}
  darkBtn.addEventListener('click', function() {{
    document.body.classList.toggle('dark');
    var isDark = document.body.classList.contains('dark');
    localStorage.setItem('fn_dark', isDark ? '1' : '0');
    this.textContent = isDark ? '☀️ Light' : '🌙 Dark';
  }});

  // Print / Share
  var printBtn = document.getElementById('printBtn');
  printBtn.addEventListener('click', function() {{
    if (navigator.share) {{
      navigator.share({{ url: location.href }});
    }} else {{
      window.print();
    }}
  }});

  // Refresh
  var refreshBtn = document.getElementById('refreshBtn');
  refreshBtn.addEventListener('click', function() {{
    location.reload();
  }});
}});
</script>

</body>
</html>"""

    return html


def generate_html(
    categories: list = None,
    output_path: str = "fake_news.html",
) -> str:
    """Fetch news and write HTML report to disk."""
    from news_engine.fetcher import fetch_all_news

    feed = fetch_all_news(categories=categories)
    html = generate_html_string(feed)
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    logger.info("HTML report written to %s", p.resolve())
    return str(p.resolve())


def open_report(
    categories: list = None,
    output_path: str = "fake_news.html",
) -> str:
    """Generate and open in browser."""
    import webbrowser

    path = generate_html(categories=categories, output_path=output_path)
    webbrowser.open(f"file://{path}")
    return path

# 📰 Fake News

**De-enshittified news reader for Home Assistant.**

No ads. No tracking. No cookie banners. No paywalls. No autoplaying videos. Just news.

Fake News pulls clean articles from 23 RSS feeds across 5 categories and serves a fast, self-contained HTML page via Home Assistant ingress.

![Home Assistant Add-on](https://img.shields.io/badge/Home%20Assistant-Add--on-blue?logo=homeassistant)

---

## Features

- **23 RSS feeds** across 5 categories — parsed in parallel (~3 seconds)
- **Category tabs** — filter by General, Texas/Houston, Tech, Finance, Sports
- **Dark mode** with persistent toggle
- **Mobile responsive** — works great on phones via HA Companion app
- **Auto-refresh** — configurable interval (default: 30 minutes)
- **Print / Share** — iOS share sheet on mobile, print on desktop
- **Zero JavaScript tracking** — fully self-contained HTML, no external requests
- **Home Assistant ingress** — no port forwarding needed

## News Sources

| Category | Sources |
|----------|---------|
| 📰 **General** | BBC News, NPR, PBS NewsHour, ABC News, CBS News, Al Jazeera |
| ⛐ **Texas / Houston** | Texas Tribune, Houston Public Media, KHOU, San Antonio Express |
| 💻 **Tech** | Ars Technica, Hacker News, The Verge, TechCrunch, Wired |
| 💰 **Finance** | CNBC, CNBC Markets, MarketWatch, Yahoo Finance |
| 🏈 **Sports** | ESPN, ESPN NFL, ESPN NBA, ESPN MLB, CBS Sports |

## Installation

### 1. Add the repository

In Home Assistant, go to **Settings → Add-ons → Add-on Store → ⋮ → Repositories** and add:

```
https://github.com/gmarblestone/NewsApp
```

### 2. Install

Find **Fake News** in the add-on store and click **Install**.

### 3. Configure (optional)

Default settings work out of the box. You can customize:

| Option | Default | Description |
|--------|---------|-------------|
| `categories` | `general,texas,tech,finance,sports` | Comma-separated category keys |
| `refresh_minutes` | `30` | How often to re-fetch feeds (10–1440) |
| `max_articles_per_feed` | `15` | Max articles pulled per feed (5–50) |
| `report_path` | `/config/www/fake_news.html` | Where to write the HTML file |

### 4. Start

Start the add-on and open it from the sidebar (newspaper icon).

## Architecture

Same proven pattern as [FishingApp](https://github.com/gmarblestone/FishingApp):

```
news_addon/
├── Dockerfile           # Alpine + Python + nginx
├── config.yaml          # HA add-on manifest
└── rootfs/
    ├── run.sh           # Entrypoint: nginx + fetch loop
    ├── nginx.conf       # Static file server on ingress port
    └── app/
        ├── news_engine/ # Feed fetcher + config + models
        └── integrations/
            └── html_report.py  # Self-contained HTML generator
```

- **nginx** serves the static HTML via HA ingress (port 5056)
- **run.sh** fetches feeds on startup, then refreshes on the configured interval
- **feedparser** handles RSS/Atom parsing; **BeautifulSoup** strips HTML from summaries
- All feeds fetched in parallel via `ThreadPoolExecutor`

## Local Development

```bash
# Clone
git clone https://github.com/gmarblestone/NewsApp.git
cd NewsApp

# Install dependencies
pip install -r requirements.txt

# Generate report and open in browser
python run_news.py report

# Generate without opening
python run_news.py report --no-open

# Fetch specific categories
python run_news.py report --categories tech,finance

# Print summary to console
python run_news.py fetch
```

## License

MIT

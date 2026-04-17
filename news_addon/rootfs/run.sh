#!/bin/bash
set -o pipefail

log() { echo "[INFO]  $(date '+%H:%M:%S') $*"; }
warn() { echo "[WARN]  $(date '+%H:%M:%S') $*"; }
err() { echo "[ERROR] $(date '+%H:%M:%S') $*"; }

log "============================================"
log "Fake News Add-on starting"
log "PID $$, user $(whoami)"
log "============================================"

# ── Read add-on options ──────────────────────────────────────────────────────

OPTIONS="/data/options.json"
if [ ! -f "$OPTIONS" ]; then
  err "Missing $OPTIONS"
  CATEGORIES="general,texas,tech,finance,sports"
  REFRESH_MINUTES=30
  MAX_PER_FEED=15
  REPORT_PATH="/config/www/fake_news.html"
else
  CATEGORIES=$(jq -r '.categories // "general,texas,tech,finance,sports"' "$OPTIONS")
  REFRESH_MINUTES=$(jq -r '.refresh_minutes // 30' "$OPTIONS")
  MAX_PER_FEED=$(jq -r '.max_articles_per_feed // 15' "$OPTIONS")
  REPORT_PATH=$(jq -r '.report_path // "/config/www/fake_news.html"' "$OPTIONS")
  log "Options: categories=${CATEGORIES} refresh=${REFRESH_MINUTES}min max_per_feed=${MAX_PER_FEED}"
fi

PORT="${INGRESS_PORT:-5056}"
log "Ingress port: ${PORT}"

mkdir -p "$(dirname "${REPORT_PATH}")" 2>/dev/null || true
mkdir -p /app/www /run/nginx

# Ensure articles dir lives alongside the report (for iframe /local/ access)
# and is symlinked into nginx's docroot (for ingress access)
REPORT_DIR="$(dirname "${REPORT_PATH}")"
ARTICLES_DIR="${REPORT_DIR}/articles"
mkdir -p "${ARTICLES_DIR}" 2>/dev/null || true
ln -sfn "${ARTICLES_DIR}" /app/www/articles
log "Articles dir: ${ARTICLES_DIR} (symlinked to /app/www/articles)"

# ── Write loading page ───────────────────────────────────────────────────────

cat > /app/www/index.html << 'LOADING'
<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Fake News</title>
<style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#f1f5f9;}
.box{text-align:center;padding:40px;background:white;border-radius:16px;box-shadow:0 2px 8px rgba(0,0,0,0.1);}
h1{color:#dc2626;margin-bottom:8px;} p{color:#64748b;}</style></head>
<body><div class="box"><h1>📰 FAKE NEWS</h1><p>Loading news feeds...</p><p>This page will refresh automatically.</p>
<script>setTimeout(()=>location.reload(),15000)</script></div></body></html>
LOADING
log "Loading page written"

# ── Kill stale nginx ─────────────────────────────────────────────────────────

if command -v pkill >/dev/null 2>&1; then
  pkill -f "nginx" 2>/dev/null || true
  sleep 1
fi

# ── Configure and start nginx ────────────────────────────────────────────────

if ! command -v nginx >/dev/null 2>&1; then
  err "nginx not installed!"
  exit 1
fi

sed -i "s/__PORT__/${PORT}/" /etc/nginx/nginx.conf
log "nginx config: port set to ${PORT}"

nginx -t 2>&1 | while IFS= read -r line; do log "  $line"; done

log "Starting nginx..."
nginx &
NGINX_PID=$!
sleep 2

if kill -0 "${NGINX_PID}" 2>/dev/null; then
  log "nginx running (PID ${NGINX_PID})"
else
  err "nginx FAILED to start!"
  cat /var/log/nginx/error.log 2>/dev/null || true
  cd /app/www && python3 -m http.server "${PORT}" --bind 0.0.0.0 &
  NGINX_PID=$!
fi

# ── Start refresh API server ────────────────────────────────────────────────

log "Starting refresh API server..."
python3 /app/refresh_server.py &
REFRESH_PID=$!
sleep 1
if kill -0 "${REFRESH_PID}" 2>/dev/null; then
  log "Refresh server running (PID ${REFRESH_PID})"
else
  warn "Refresh server failed to start"
fi

# ── Graceful shutdown ────────────────────────────────────────────────────────

shutdown() {
  log "Shutdown requested..."
  kill -TERM "${NGINX_PID}" 2>/dev/null || true
  kill -TERM "${REFRESH_PID}" 2>/dev/null || true
  wait "${NGINX_PID}" 2>/dev/null || true
  wait "${REFRESH_PID}" 2>/dev/null || true
  exit 0
}
trap shutdown INT TERM

# ── News fetch helper ────────────────────────────────────────────────────────

run_news() {
    log "Fetching news (categories: ${CATEGORIES})..."
    touch /tmp/refresh_running
    cd /app && python3 -c "
import sys, traceback
sys.path.insert(0, '.')
try:
    from news_engine.fetcher import fetch_all_news
    from news_engine.extractor import save_articles
    from integrations.html_report import generate_html_string
    cats = '${CATEGORIES}'.split(',')
    cats = [c.strip() for c in cats if c.strip()]
    feed = fetch_all_news(categories=cats, max_per_feed=${MAX_PER_FEED})
    print('Fetched ' + str(len(feed.articles)) + ' articles from ' + str(feed.total_feeds) + ' feeds')
    if feed.failed_feeds:
        print('WARNING: ' + str(feed.failed_feeds) + ' feeds failed')
        for e in feed.error_details[:5]:
            print('  ' + str(e))
    # Extract full articles
    saved = {}
    try:
        saved = save_articles(feed.articles, articles_dir='${ARTICLES_DIR}')
        print('Extracted ' + str(len(saved)) + '/' + str(len(feed.articles)) + ' articles')
    except Exception as e:
        print('Article extraction warning: ' + str(e))
    html = generate_html_string(feed, saved_articles=saved)
    with open('${REPORT_PATH}', 'w') as f:
        f.write(html)
    with open('/app/www/index.html', 'w') as f:
        f.write(html)
    print('HTML report written')
except Exception as e:
    print('ERROR: ' + str(e))
    traceback.print_exc()
    sys.exit(1)
" 2>&1 | while read -r line; do log "  ${line}"; done

    if [ $? -ne 0 ]; then
        err "News fetch failed"
        rm -f /tmp/refresh_running
        return 1
    fi
    rm -f /tmp/refresh_running
    log "News fetch complete"
}

# ── Initial run ──────────────────────────────────────────────────────────────

log "Running initial fetch..."
run_news || warn "Initial fetch failed — will retry"

# ── Main loop ────────────────────────────────────────────────────────────────

log "Entering main loop (refresh every ${REFRESH_MINUTES} min, trigger check every 5s)"
SLEEP_SECONDS=$((REFRESH_MINUTES * 60))
ELAPSED=0

while true; do
    sleep 5
    ELAPSED=$((ELAPSED + 5))

    # Check for manual refresh trigger
    if [ -f /tmp/refresh_trigger ]; then
        log "Manual refresh triggered!"
        rm -f /tmp/refresh_trigger
        run_news || warn "Triggered fetch failed"
        ELAPSED=0
    fi

    # Scheduled refresh
    if [ "${ELAPSED}" -ge "${SLEEP_SECONDS}" ]; then
        run_news || warn "Scheduled fetch failed"
        ELAPSED=0
    fi

    # Keep nginx alive
    if ! kill -0 "${NGINX_PID}" 2>/dev/null; then
        warn "nginx died — restarting..."
        nginx &
        NGINX_PID=$!
    fi

    # Keep refresh server alive
    if ! kill -0 "${REFRESH_PID}" 2>/dev/null; then
        warn "Refresh server died — restarting..."
        python3 /app/refresh_server.py &
        REFRESH_PID=$!
    fi
done

"""
Fake News — CLI entry point.

Usage:
    python run_news.py report              # Generate HTML and open in browser
    python run_news.py report --no-open    # Generate HTML only
    python run_news.py fetch               # Print article count to console
"""

import argparse
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_fetch(args):
    from news_engine.fetcher import fetch_all_news

    cats = args.categories.split(",") if args.categories else None
    feed = fetch_all_news(categories=cats, max_per_feed=args.max_per_feed)
    print(json.dumps(feed.to_dict(), indent=2))
    for a in feed.articles[:5]:
        print(f"  [{a.source}] {a.title} ({a.time_ago})")
    if len(feed.articles) > 5:
        print(f"  ... and {len(feed.articles) - 5} more")


def cmd_report(args):
    from integrations.html_report import open_report, generate_html

    cats = args.categories.split(",") if args.categories else None
    if args.no_open:
        path = generate_html(categories=cats, output_path=args.output)
    else:
        path = open_report(categories=cats, output_path=args.output)
    print(f"Report: {path}")


def main():
    parser = argparse.ArgumentParser(description="Fake News — De-enshittified News Reader")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # fetch
    p_fetch = subparsers.add_parser("fetch", help="Fetch and print summary")
    p_fetch.add_argument("--categories", default=None, help="Comma-separated category keys")
    p_fetch.add_argument("--max-per-feed", type=int, default=15)

    # report
    p_report = subparsers.add_parser("report", help="Generate HTML report")
    p_report.add_argument("--output", default="fake_news.html")
    p_report.add_argument("--no-open", action="store_true", help="Don't open browser")
    p_report.add_argument("--categories", default=None, help="Comma-separated category keys")

    args = parser.parse_args()
    {"fetch": cmd_fetch, "report": cmd_report}[args.command](args)


if __name__ == "__main__":
    main()

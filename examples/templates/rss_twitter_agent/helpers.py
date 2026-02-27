"""Helper functions for RSS-to-Twitter data operations."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from examples.template.rss_twitter_agent.twitter import post_threads_impl
from .credentials import resolve_twitter_session_dir


def fetch_rss_data(inputs: dict[str, Any]) -> dict[str, Any]:
    """Fetch and parse RSS feed into normalized article objects."""
    feed_url = str(inputs.get("feed_url") or "https://news.ycombinator.com/rss")
    max_articles = int(inputs.get("max_articles") or 3)

    try:
        with httpx.Client() as client:
            resp = client.get(feed_url, timeout=10.0, follow_redirects=True)
            resp.raise_for_status()
            xml_content = resp.text
    except Exception as exc:
        return {"articles": [], "error": f"fetch_failed: {exc}"}

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return {"articles": [], "error": "invalid_xml"}

    articles: list[dict[str, str]] = []
    for item in root.findall(".//item")[:max_articles]:
        title_elem = item.find("title")
        link_elem = item.find("link")
        desc_elem = item.find("description")
        articles.append(
            {
                "title": title_elem.text if title_elem is not None else "",
                "link": link_elem.text if link_elem is not None else "",
                "summary": (
                    desc_elem.text[:220] if desc_elem is not None and desc_elem.text else ""
                ),
                "source": "RSS",
            }
        )

    return {"articles": articles, "feed_url": feed_url, "count": len(articles)}


def summarize_articles_data(inputs: dict[str, Any]) -> dict[str, Any]:
    """Summarize articles into structured tweet-ready summaries."""
    articles = inputs.get("articles") or []
    summaries: list[dict[str, str]] = []
    for article in articles:
        title = str(article.get("title") or "")
        source = str(article.get("source") or "RSS")
        summary = str(article.get("summary") or "")
        summaries.append(
            {
                "title": title,
                "source": source,
                "summary": summary[:280],
            }
        )
    return {"summaries": summaries}


def generate_threads_data(inputs: dict[str, Any]) -> dict[str, Any]:
    """Generate thread drafts from summaries."""
    summaries = inputs.get("summaries") or []
    threads: list[dict[str, Any]] = []
    for summary in summaries:
        title = str(summary.get("title") or "Untitled")
        body = str(summary.get("summary") or "")
        source = str(summary.get("source") or "RSS")
        tweets = [f"{title}\n\n{body}".strip()[:280], f"Source: {source}"]
        threads.append({"title": title, "tweets": tweets})
    return {"threads": threads}


def post_to_twitter_data(inputs: dict[str, Any]) -> dict[str, Any]:
    """Post approved threads through Playwright-based twitter helper."""
    threads = inputs.get("approved_threads") or inputs.get("threads") or []
    if not isinstance(threads, list):
        return {"success": False, "error": "threads must be a list"}
    credential_ref = inputs.get("twitter_credential_ref")
    session_dir = resolve_twitter_session_dir(
        credential_ref=str(credential_ref) if credential_ref else None
    )

    import asyncio

    result = asyncio.run(post_threads_impl(json.dumps(threads), None))
    if isinstance(result, dict):
        if session_dir:
            result["session_dir"] = session_dir
        return result
    return {"success": False, "error": str(result)}

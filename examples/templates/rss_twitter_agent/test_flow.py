#!/usr/bin/env python
"""Focused tests for the RSS-to-Twitter interactive runner."""

from __future__ import annotations

import asyncio
import json

from .fetch import approve_threads
from . import run as run_module


def test_run_interactive_posts_approved_thread(monkeypatch) -> None:
    articles = [{"title": "A", "link": "https://example.com/a", "summary": "Sum"}]
    summaries = [
        {
            "title": "A",
            "url": "https://example.com/a",
            "hook": "Hook",
            "points": ["Point 1", "Point 2"],
            "why_it_matters": "Why",
            "hashtags": ["#Tech"],
        }
    ]
    post_calls: list[list[dict]] = []

    monkeypatch.setattr(run_module, "fetch_rss", lambda **_: json.dumps(articles))
    monkeypatch.setattr(
        run_module, "summarize_articles", lambda _: json.dumps(summaries)
    )
    monkeypatch.setattr(
        run_module,
        "_generate_thread_for_article",
        lambda summary: {
            "title": summary["title"],
            "tweets": ["tweet 1", "tweet 2", "tweet 3", "tweet 4"],
        },
    )

    async def fake_post(approved_json: str) -> str:
        payload = json.loads(approved_json)
        post_calls.append(payload)
        return json.dumps({"success": True, "posted": len(payload[0]["tweets"])})

    monkeypatch.setattr(run_module, "post_to_twitter", fake_post)
    responses = iter(["y"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(responses))

    result = asyncio.run(run_module.run_interactive(max_articles=1))

    assert result["success"] is True
    assert result["articles_fetched"] == 1
    assert result["threads_reviewed"] == 1
    assert result["threads_posted"] == 1
    assert len(post_calls) == 1


def test_run_interactive_quit_stops_remaining_threads(monkeypatch) -> None:
    articles = [
        {"title": "A", "link": "https://example.com/a", "summary": "Sum"},
        {"title": "B", "link": "https://example.com/b", "summary": "Sum"},
    ]
    summaries = [
        {
            "title": article["title"],
            "url": article["link"],
            "hook": article["title"],
            "points": ["Point 1"],
            "why_it_matters": "Why",
            "hashtags": ["#Tech"],
        }
        for article in articles
    ]
    post_calls: list[list[dict]] = []

    monkeypatch.setattr(run_module, "fetch_rss", lambda **_: json.dumps(articles))
    monkeypatch.setattr(
        run_module, "summarize_articles", lambda _: json.dumps(summaries)
    )
    monkeypatch.setattr(
        run_module,
        "_generate_thread_for_article",
        lambda summary: {
            "title": summary["title"],
            "tweets": ["tweet 1", "tweet 2", "tweet 3", "tweet 4"],
        },
    )

    async def fake_post(approved_json: str) -> str:
        payload = json.loads(approved_json)
        post_calls.append(payload)
        return json.dumps({"success": True, "posted": len(payload[0]["tweets"])})

    monkeypatch.setattr(run_module, "post_to_twitter", fake_post)
    responses = iter(["q"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(responses))

    result = asyncio.run(run_module.run_interactive(max_articles=2))

    assert result["threads_reviewed"] == 1
    assert result["threads_posted"] == 0
    assert post_calls == []


def test_approve_threads_keeps_prior_approvals_before_quit(monkeypatch) -> None:
    threads = [
        {"title": "A", "tweets": ["tweet 1"]},
        {"title": "B", "tweets": ["tweet 2"]},
    ]
    responses = iter(["y", "q"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(responses))

    approved = json.loads(approve_threads(json.dumps(threads)))

    assert approved == [threads[0]]


if __name__ == "__main__":
    result = asyncio.run(run_module.run_interactive(max_articles=1))
    print(json.dumps(result, indent=2, default=str))

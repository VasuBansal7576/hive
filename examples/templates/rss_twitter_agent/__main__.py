"""CLI entry point for modern RSS-to-Twitter Agent."""

from __future__ import annotations

import asyncio
import json
import sys

import click

from .agent import default_agent


@click.group()
@click.version_option(version="2.0.0")
def cli() -> None:
    """RSS-to-Twitter Agent."""


@cli.command()
@click.option("--feed-url", default="https://news.ycombinator.com/rss", show_default=True)
@click.option("--max-articles", default=3, show_default=True, type=int)
@click.option(
    "--twitter-credential-ref",
    default=None,
    help="Hive credential reference in {name}/{alias} format (example: twitter/default).",
)
@click.option("--mock", is_flag=True, help="Run with deterministic mock LLM")
@click.option("--auto-approve/--no-auto-approve", default=True, help="Mock-only approval decision")
def run(
    feed_url: str,
    max_articles: int,
    twitter_credential_ref: str | None,
    mock: bool,
    auto_approve: bool,
) -> None:
    """Run the RSS-to-Twitter workflow."""
    context = {
        "feed_url": feed_url,
        "max_articles": max_articles,
        "auto_approve": auto_approve,
    }
    if twitter_credential_ref:
        context["twitter_credential_ref"] = twitter_credential_ref
    result = asyncio.run(default_agent.run(context=context, mock_mode=mock))
    payload = {
        "success": result.success,
        "steps_executed": result.steps_executed,
        "output": result.output,
    }
    if result.error:
        payload["error"] = result.error
    click.echo(json.dumps(payload, indent=2, default=str))
    sys.exit(0 if result.success else 1)


@cli.command()
@click.option("--json", "output_json", is_flag=True)
def info(output_json: bool) -> None:
    """Show agent metadata and graph summary."""
    data = default_agent.info()
    if output_json:
        click.echo(json.dumps(data, indent=2))
        return
    click.echo(f"Agent: {data['name']}")
    click.echo(f"Version: {data['version']}")
    click.echo(f"Description: {data['description']}")
    click.echo(f"Nodes: {', '.join(data['nodes'])}")
    click.echo(f"Client-facing: {', '.join(data['client_facing_nodes'])}")
    click.echo(f"Entry: {data['entry_node']}")
    click.echo(f"Terminal: {', '.join(data['terminal_nodes'])}")


@cli.command()
def validate() -> None:
    """Validate graph shape."""
    result = default_agent.validate()
    if result["valid"]:
        click.echo("Agent is valid")
        sys.exit(0)
    click.echo("Agent has errors:")
    for err in result["errors"]:
        click.echo(f"  ERROR: {err}")
    sys.exit(1)


if __name__ == "__main__":
    cli()

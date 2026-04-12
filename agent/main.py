"""
NESL Social Media Agent — CLI
Usage (from project root):
  python run.py <command> [options]
  python -m agent.main <command> [options]

Commands:
  check      Verify configuration and API connectivity
  scores     Post final score updates
  news       Post breaking news
  hype       Post a pre-game hype post
  daily      Full daily update (scores + news for both teams)
  post       Create a custom post with a given headline
  schedule   Run the agent on a recurring schedule (daemon mode)
"""
from __future__ import annotations

import sys
import time

import click
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import config
from .nesl_agent import NESLAgent

console = Console()


def _banner() -> None:
    console.print(
        Panel.fit(
            "[bold gold1]NESL[/bold gold1]  [bold white]New England Sports Lab[/bold white]\n"
            "[dim cyan]Social Media Agent  •  @nesportslab[/dim cyan]",
            border_style="gold1",
            padding=(0, 2),
        )
    )


# ─── CLI Root ─────────────────────────────────────────────────────────────────

@click.group()
def cli() -> None:
    """NESL Social Media Agent — Boston Sports Coverage 🏆"""


# ─── check ────────────────────────────────────────────────────────────────────

@cli.command()
def check() -> None:
    """Verify configuration and test the ESPN API connection."""
    _banner()

    table = Table(title="Configuration", show_header=False, box=None, padding=(0, 2))
    table.add_column("Key",   style="bold")
    table.add_column("Value")

    def ok(v: str) -> str:
        return f"[green]✓[/green]  {v}"

    def err(v: str) -> str:
        return f"[red]✗[/red]  {v}"

    def warn(v: str) -> str:
        return f"[yellow]⚠[/yellow]  {v}"

    table.add_row("Claude API Key",     ok("set") if config.ANTHROPIC_API_KEY else err("missing (ANTHROPIC_API_KEY)"))
    table.add_row("Instagram Username", ok(config.INSTAGRAM_USERNAME) if config.INSTAGRAM_USERNAME else warn("not set"))
    table.add_row("Instagram Password", ok("set") if config.INSTAGRAM_PASSWORD else warn("not set"))
    table.add_row("NESL Logo",          ok("found") if config.NESL_LOGO_PATH.exists() else warn("missing — add nesl_logo.png to assets/"))
    table.add_row("Posts directory",    ok(str(config.POSTS_DIR)))
    console.print(table)

    console.print("\n[bold]ESPN API connectivity:[/bold]")
    try:
        from .sports_data import SportsDataFetcher
        f = SportsDataFetcher()
        celtics  = f.get_celtics_games()
        patriots = f.get_patriots_games()
        console.print(f"  [green]✓[/green]  Celtics  — {len(celtics)} game(s) on today's board")
        console.print(f"  [green]✓[/green]  Patriots — {len(patriots)} game(s) on today's board")
    except Exception as exc:
        console.print(f"  [red]✗[/red]  ESPN API error: {exc}")


# ─── scores ───────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--team", type=click.Choice(["patriots", "celtics", "both"]), default="both", show_default=True)
@click.option("--days", default=2, show_default=True, help="Days back to search for completed games.")
@click.option("--post", "live_post", is_flag=True, default=False, help="Post live to Instagram (default: save draft).")
def scores(team: str, days: int, live_post: bool) -> None:
    """Check for final scores and create score-update posts."""
    _banner()
    action = "post to Instagram" if live_post else "save as draft"
    task = (
        f"Check for completed {team} game(s) from the last {days} day(s). "
        f"For each completed game create an engaging score-update post with a flyer and {action}. "
        "If no completed games are found, let me know."
    )
    NESLAgent().run(task)


# ─── news ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--team", type=click.Choice(["patriots", "celtics", "both"]), default="both", show_default=True)
@click.option("--limit", default=5, show_default=True, help="Number of news items to review.")
@click.option("--post", "live_post", is_flag=True, default=False, help="Post live to Instagram.")
def news(team: str, limit: int, live_post: bool) -> None:
    """Fetch the latest news and create a breaking-news post."""
    _banner()
    action = "post to Instagram" if live_post else "save as draft"
    task = (
        f"Get the latest {limit} news articles for the {team}. "
        f"Pick the single most newsworthy/exciting story and create a BREAKING NEWS post with a flyer and {action}."
    )
    NESLAgent().run(task)


# ─── hype ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--team", type=click.Choice(["patriots", "celtics"]), required=True)
@click.option("--post", "live_post", is_flag=True, default=False, help="Post live to Instagram.")
def hype(team: str, live_post: bool) -> None:
    """Create a high-energy hype post for an upcoming game."""
    _banner()
    action = "post to Instagram" if live_post else "save as draft"
    task = (
        f"Check the latest news for the {team} and create an exciting game-day hype post. "
        f"Make it energetic and get the fans fired up! Create a flyer and {action}."
    )
    NESLAgent().run(task)


# ─── daily ────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--post", "live_post", is_flag=True, default=False, help="Post live to Instagram.")
def daily(live_post: bool) -> None:
    """Run the full daily NESL update — scores + top news for both teams."""
    _banner()
    action = "post all to Instagram" if live_post else "save all as drafts"
    task = f"""\
Run the full daily NESL social media update:
1. Check for completed Patriots AND Celtics games from the last 2 days.
   • For every completed game create a score-update post with a flyer.
2. Fetch the latest news for both teams.
   • Pick the single most important story and create a breaking-news post with a flyer.
3. {action}.
4. Summarize everything you posted."""
    NESLAgent().run(task)


# ─── post ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("headline")
@click.option("--team", type=click.Choice(["patriots", "celtics", "nesl"]), default="nesl", show_default=True)
@click.option("--subtitle", default="", help="Optional supporting text.")
@click.option("--type", "post_type",
              type=click.Choice(["score_update", "breaking_news", "hype", "general"]),
              default="general", show_default=True)
@click.option("--post", "live_post", is_flag=True, default=False, help="Post live to Instagram.")
def post(headline: str, team: str, subtitle: str, post_type: str, live_post: bool) -> None:
    """Create a custom post with HEADLINE as the main text."""
    _banner()
    action = "post to Instagram" if live_post else "save as draft"
    sub_part = f" with subtitle '{subtitle}'" if subtitle else ""
    task = (
        f"Create a {post_type} post with headline: '{headline}'{sub_part} for the {team}. "
        f"Create a matching flyer and {action}."
    )
    NESLAgent().run(task)


# ─── schedule ─────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--interval", default=60, show_default=True, help="Minutes between runs.")
@click.option("--post", "live_post", is_flag=True, default=False, help="Post live to Instagram.")
def schedule(interval: int, live_post: bool) -> None:
    """Run the daily update agent on a recurring schedule (daemon mode)."""
    _banner()
    console.print(f"[bold]Scheduler started[/bold] — running every [cyan]{interval}[/cyan] minute(s). Press Ctrl+C to stop.\n")

    action = "post to Instagram" if live_post else "save as draft"
    task = (
        "Check for any new completed Patriots or Celtics games from the last 3 hours "
        "and check for fresh breaking news. Create posts with flyers for anything new "
        f"and {action}. If nothing new, do nothing."
    )

    while True:
        console.print(f"[dim]{__import__('datetime').datetime.now():%Y-%m-%d %H:%M}[/dim]  Running update...")
        try:
            NESLAgent().run(task, verbose=False)
        except Exception as exc:
            console.print(f"[red]Error during scheduled run: {exc}[/red]")
        time.sleep(interval * 60)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()

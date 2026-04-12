"""
NESL Agent — Sports Data Fetcher
Pulls live scores from ESPN and news from ESPN + local Boston outlets
(NBC Sports Boston, Boston Herald, Boston Globe) via RSS.
"""
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import requests

from . import config

# Bypass any system-level proxy so ESPN and RSS feeds are reachable directly
_NO_PROXY = {"http": None, "https": None}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; NESLBot/1.0; +https://instagram.com/nesportslab)"
    )
}


def _strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text or "")).strip()


class SportsDataFetcher:
    """Fetches game scores and news from ESPN + local Boston RSS feeds."""

    TIMEOUT = 12

    def _get(self, url: str, params: dict | None = None) -> dict:
        try:
            resp = requests.get(
                url,
                params=params or {},
                headers=_HEADERS,
                timeout=self.TIMEOUT,
                proxies=_NO_PROXY,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"error": str(e), "events": [], "articles": []}

    def _get_rss(self, url: str, source_label: str) -> list[dict]:
        """Fetch and parse an RSS 2.0 feed; return normalised article dicts."""
        try:
            resp = requests.get(
                url,
                headers=_HEADERS,
                timeout=self.TIMEOUT,
                proxies=_NO_PROXY,
            )
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception:
            return []

        articles = []
        for item in root.findall(".//item"):
            headline = _strip_html(item.findtext("title", ""))
            desc     = _strip_html(item.findtext("description", ""))
            pub      = item.findtext("pubDate", "")
            link     = item.findtext("link", "") or item.findtext("guid", "")
            if headline:
                articles.append({
                    "headline":    headline,
                    "description": desc,
                    "published":   pub,
                    "url":         link,
                    "source":      source_label,
                })
        return articles

    # ─── Scoreboards ─────────────────────────────────────────────────────────────────────────────

    def get_nfl_scoreboard(self, date: str | None = None) -> dict:
        """date: YYYYMMDD format; omit for today."""
        params = {"dates": date} if date else {}
        return self._get(config.ESPN_NFL_SCOREBOARD, params)

    def get_nba_scoreboard(self, date: str | None = None) -> dict:
        params = {"dates": date} if date else {}
        return self._get(config.ESPN_NBA_SCOREBOARD, params)

    # ─── ESPN News ───────────────────────────────────────────────────────────────────────────────

    def _espn_news(self, url: str, team_id: str, limit: int) -> list[dict]:
        data = self._get(url, {"limit": limit, "team": team_id})
        articles = []
        for article in data.get("articles", []):
            articles.append({
                "headline":    article.get("headline", ""),
                "description": article.get("description", ""),
                "published":   article.get("published", ""),
                "url":         article.get("links", {}).get("web", {}).get("href", ""),
                "source":      "ESPN",
            })
        return articles

    # ─── Local Boston RSS Sources ─────────────────────────────────────────────────────────────────────

    def get_nbc_boston_news(self, team: str, limit: int = 5) -> list[dict]:
        url = (
            config.NBC_BOSTON_CELTICS
            if team == "celtics"
            else config.NBC_BOSTON_PATRIOTS
        )
        return self._get_rss(url, "NBC Sports Boston")[:limit]

    def get_herald_news(self, team: str, limit: int = 5) -> list[dict]:
        url = (
            config.HERALD_CELTICS
            if team == "celtics"
            else config.HERALD_PATRIOTS
        )
        return self._get_rss(url, "Boston Herald")[:limit]

    def get_globe_news(self, team: str, limit: int = 5) -> list[dict]:
        url = (
            config.GLOBE_CELTICS
            if team == "celtics"
            else config.GLOBE_PATRIOTS
        )
        return self._get_rss(url, "Boston Globe")[:limit]

    # ─── Aggregated News ──────────────────────────────────────────────────────────────────────────────

    def get_nfl_news(self, limit: int = 5) -> list[dict]:
        """Patriots news from ESPN + NBC Sports Boston + Herald + Globe."""
        articles: list[dict] = []
        articles.extend(self._espn_news(config.ESPN_NFL_NEWS, config.PATRIOTS_TEAM_ID, limit))
        articles.extend(self.get_nbc_boston_news("patriots", limit))
        articles.extend(self.get_herald_news("patriots", limit))
        articles.extend(self.get_globe_news("patriots", limit))
        return articles[:limit * 2]

    def get_nba_news(self, limit: int = 5) -> list[dict]:
        """Celtics news from ESPN + NBC Sports Boston + Herald + Globe."""
        articles: list[dict] = []
        articles.extend(self._espn_news(config.ESPN_NBA_NEWS, config.CELTICS_TEAM_ID, limit))
        articles.extend(self.get_nbc_boston_news("celtics", limit))
        articles.extend(self.get_herald_news("celtics", limit))
        articles.extend(self.get_globe_news("celtics", limit))
        return articles[:limit * 2]

    # ─── Game Parsing ──────────────────────────────────────────────────────────────────────────────

    def _parse_game(self, event: dict, competition: dict) -> dict:
        status      = event.get("status", {}).get("type", {})
        competitors = competition.get("competitors", [])

        home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0] if competitors else {})
        away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[-1] if competitors else {})

        def safe_score(c: dict) -> int:
            try:
                return int(c.get("score", 0) or 0)
            except (ValueError, TypeError):
                return 0

        return {
            "id":             event.get("id", ""),
            "name":           event.get("name", ""),
            "date":           event.get("date", "")[:10],
            "status":         status.get("description", ""),
            "completed":      status.get("completed", False),
            "home_team":      home.get("team", {}).get("displayName", ""),
            "home_team_abbr": home.get("team", {}).get("abbreviation", ""),
            "home_score":     safe_score(home),
            "home_winner":    home.get("winner", False),
            "away_team":      away.get("team", {}).get("displayName", ""),
            "away_team_abbr": away.get("team", {}).get("abbreviation", ""),
            "away_score":     safe_score(away),
            "away_winner":    away.get("winner", False),
            "venue":          competition.get("venue", {}).get("fullName", ""),
        }

    def _filter_by_team(self, data: dict, team_id: str) -> list[dict]:
        games = []
        for event in data.get("events", []):
            for competition in event.get("competitions", []):
                for competitor in competition.get("competitors", []):
                    if competitor.get("team", {}).get("id") == team_id:
                        games.append(self._parse_game(event, competition))
                        break
        return games

    # ─── Public Accessors ─────────────────────────────────────────────────────────────────────────────

    def get_patriots_games(self, date: str | None = None) -> list[dict]:
        return self._filter_by_team(self.get_nfl_scoreboard(date), config.PATRIOTS_TEAM_ID)

    def get_celtics_games(self, date: str | None = None) -> list[dict]:
        return self._filter_by_team(self.get_nba_scoreboard(date), config.CELTICS_TEAM_ID)

    def get_recent_results(self, team: str, days_back: int = 3) -> list[dict]:
        """Return completed games from the last N days."""
        results = []
        for i in range(days_back):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
            if team in ("patriots", "both"):
                games = self.get_patriots_games(date)
                results.extend(g for g in games if g["completed"])
            if team in ("celtics", "both"):
                games = self.get_celtics_games(date)
                results.extend(g for g in games if g["completed"])
        return results

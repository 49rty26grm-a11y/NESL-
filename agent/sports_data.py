"""
NESL Agent — Sports Data Fetcher
Pulls live scores and news from ESPN's unofficial public API.
"""
import requests
from datetime import datetime, timedelta
from typing import Optional
from . import config


class SportsDataFetcher:
    """Fetches game scores and news from ESPN's public API."""

    TIMEOUT = 10

    def _get(self, url: str, params: dict | None = None) -> dict:
        try:
            resp = requests.get(url, params=params or {}, timeout=self.TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"error": str(e), "events": [], "articles": []}

    # ─── Scoreboards ──────────────────────────────────────────────────────────

    def get_nfl_scoreboard(self, date: str | None = None) -> dict:
        """date: YYYYMMDD format; omit for today."""
        params = {"dates": date} if date else {}
        return self._get(config.ESPN_NFL_SCOREBOARD, params)

    def get_nba_scoreboard(self, date: str | None = None) -> dict:
        params = {"dates": date} if date else {}
        return self._get(config.ESPN_NBA_SCOREBOARD, params)

    # ─── News ─────────────────────────────────────────────────────────────────

    def get_nfl_news(self, limit: int = 5) -> list[dict]:
        data = self._get(config.ESPN_NFL_NEWS, {
            "limit": limit, "team": config.PATRIOTS_TEAM_ID
        })
        return self._parse_news(data)

    def get_nba_news(self, limit: int = 5) -> list[dict]:
        data = self._get(config.ESPN_NBA_NEWS, {
            "limit": limit, "team": config.CELTICS_TEAM_ID
        })
        return self._parse_news(data)

    def _parse_news(self, data: dict) -> list[dict]:
        articles = []
        for article in data.get("articles", []):
            articles.append({
                "headline":    article.get("headline", ""),
                "description": article.get("description", ""),
                "published":   article.get("published", ""),
                "url": article.get("links", {}).get("web", {}).get("href", ""),
            })
        return articles

    # ─── Game Parsing ──────────────────────────────────────────────────────────

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
            "id":            event.get("id", ""),
            "name":          event.get("name", ""),
            "date":          event.get("date", "")[:10],
            "status":        status.get("description", ""),
            "completed":     status.get("completed", False),
            "home_team":     home.get("team", {}).get("displayName", ""),
            "home_team_abbr":home.get("team", {}).get("abbreviation", ""),
            "home_score":    safe_score(home),
            "home_winner":   home.get("winner", False),
            "away_team":     away.get("team", {}).get("displayName", ""),
            "away_team_abbr":away.get("team", {}).get("abbreviation", ""),
            "away_score":    safe_score(away),
            "away_winner":   away.get("winner", False),
            "venue":         competition.get("venue", {}).get("fullName", ""),
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

    # ─── Public Accessors ─────────────────────────────────────────────────────

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

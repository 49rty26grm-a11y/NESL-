"""
NESL Agent — Configuration
All settings, team colors, and API endpoints.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project paths
BASE_DIR = Path(__file__).parent.parent
ASSETS_DIR = BASE_DIR / "assets"
POSTS_DIR = BASE_DIR / "posts"

POSTS_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "")

# NESL Branding
NESL_HANDLE = "@nesportslab"
NESL_LOGO_PATH = ASSETS_DIR / "nesl_logo.png"
AUTO_POST = os.getenv("AUTO_POST", "false").lower() == "true"

# ─── Team Colors ──────────────────────────────────────────────────────────────

PATRIOTS_COLORS = {
    "primary":   (12, 35, 64),      # Navy     #0C2340
    "secondary": (198, 12, 48),     # Red      #C60C30
    "accent":    (176, 183, 188),   # Silver   #B0B7BC
    "text":      (255, 255, 255),   # White
    "name":      "New England Patriots",
    "sport":     "NFL",
    "hashtags":  "#GoPats #PatriotsNation #NewEnglandPatriots #NFL",
}

CELTICS_COLORS = {
    "primary":   (0, 122, 51),      # Green    #007A33
    "secondary": (186, 150, 83),    # Gold     #BA9653
    "accent":    (255, 255, 255),   # White
    "text":      (255, 255, 255),   # White
    "name":      "Boston Celtics",
    "sport":     "NBA",
    "hashtags":  "#Celtics #CelticsNation #BostonCeltics #BleedGreen #NBA",
}

BREAKING_COLORS = {
    "primary":   (10, 10, 10),      # Near black
    "secondary": (220, 38, 38),     # Red
    "accent":    (255, 215, 0),     # Gold
    "text":      (255, 255, 255),   # White
}

# ─── ESPN Unofficial API ───────────────────────────────────────────────────────

ESPN_NFL_SCOREBOARD  = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
ESPN_NBA_SCOREBOARD  = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
ESPN_NFL_NEWS        = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/news"
ESPN_NBA_NEWS        = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/news"

PATRIOTS_TEAM_ID = "17"
CELTICS_TEAM_ID  = "2"

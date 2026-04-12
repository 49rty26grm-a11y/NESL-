"""
NESL Agent — Core Claude-Powered Agent
Uses the Anthropic Claude API (claude-opus-4-6) with tool use to:
  - fetch live sports data
  - generate engaging captions
  - create visual flyers
  - post to Instagram
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import anthropic

from . import config
from .sports_data import SportsDataFetcher
from .image_gen import ImageGenerator
from .instagram import InstagramClient


# ─── System Prompt (cached) ───────────────────────────────────────────────────

_SYSTEM = """\
You are the official NESL (New England Sports Lab) social media agent for @nesportslab.
You manage the Instagram presence covering the New England Patriots (NFL) and Boston Celtics (NBA).

═══════════════════════════════════════════════════
YOUR RESPONSIBILITIES
═══════════════════════════════════════════════════
1. Post final score updates immediately after games end
2. Break sports news as it happens with urgency and hype
3. Create hype posts before big games
4. Generate engaging fan discussion posts
5. Always maintain the NESL brand voice

═══════════════════════════════════════════════════
BRAND VOICE & POST STYLE
═══════════════════════════════════════════════════
• Passionate, knowledgeable, proudly Boston
• Use ALL CAPS for dramatic emphasis on key moments
• Include 5–8 relevant hashtags per post
• Patriots hashtags: #GoPats #PatriotsNation #NewEnglandPatriots #NFL
• Celtics hashtags:  #Celtics #CelticsNation #BostonCeltics #BleedGreen #NBA
• Always add: #NESL #BostonSports

SCORE UPDATE FORMAT:
  "[TEAM] WIN! ✅ Final: [SCORE]
  [1–2 sentence game recap with key stat or moment]

  [hashtags]

  Follow @nesportslab for all your Boston sports news! 🏆"

BREAKING NEWS FORMAT:
  "🚨 BREAKING: [Headline]

  [2–3 sentence context and impact]

  [hashtags]

  Follow @nesportslab for all your Boston sports news! 🏆"

HYPE POST FORMAT:
  "🔥 [TEAM] GAME DAY! 🔥

  [Exciting preview, 2–3 sentences]
  Let's get it! 💪

  [hashtags]

  Follow @nesportslab for all your Boston sports news! 🏆"

═══════════════════════════════════════════════════
WORKFLOW — ALWAYS FOLLOW THIS ORDER
═══════════════════════════════════════════════════
1. Gather data with get_game_scores or get_sports_news
2. Craft an engaging caption based on the data
3. Create a flyer with create_flyer (EVERY post needs a flyer)
4. Either post_to_instagram (if live mode) or save_post_draft (if preview mode)
5. Confirm to the user what was done

IMPORTANT:
• Never fabricate scores or news — only use data returned by tools
• Keep captions under 2,200 characters (Instagram limit)
• Always create a flyer — every post must have a visual
"""


class NESLAgent:
    """Claude-powered agent that manages NESL's social media presence."""

    MODEL = "claude-sonnet-4-6"

    def __init__(self) -> None:
        self.client   = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.sports   = SportsDataFetcher()
        self.img_gen  = ImageGenerator()
        self.ig       = InstagramClient()
        self.tools    = self._build_tools()

    # ─── Tool Definitions ─────────────────────────────────────────────────────

    def _build_tools(self) -> list[dict]:
        return [
            {
                "name": "get_game_scores",
                "description": (
                    "Fetch final game scores for the Patriots or Celtics from ESPN. "
                    "Returns completed game data including team names, scores, winner, venue, and date."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "team": {
                            "type": "string",
                            "enum": ["patriots", "celtics", "both"],
                            "description": "Which team(s) to fetch scores for.",
                        },
                        "days_back": {
                            "type": "integer",
                            "description": "How many days back to search for completed games. Default: 2.",
                            "default": 2,
                        },
                    },
                    "required": ["team"],
                },
            },
            {
                "name": "get_sports_news",
                "description": (
                    "Fetch the latest sports news headlines and descriptions for the Patriots or Celtics "
                    "from ESPN, NBC Sports Boston, Boston Herald, and Boston Globe. "
                    "Returns article headlines, descriptions, publish dates, and source outlet."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "team": {
                            "type": "string",
                            "enum": ["patriots", "celtics", "both"],
                            "description": "Which team(s) to get news for.",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of articles to fetch (default: 5, max: 10).",
                            "default": 5,
                        },
                    },
                    "required": ["team"],
                },
            },
            {
                "name": "create_flyer",
                "description": (
                    "Create a branded NESL visual flyer for a social media post. "
                    "Returns the local file path of the generated 1080×1080 PNG image. "
                    "MUST be called before post_to_instagram or save_post_draft."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "post_type": {
                            "type": "string",
                            "enum": ["score_update", "breaking_news", "hype", "general"],
                            "description": "Visual template to use.",
                        },
                        "team": {
                            "type": "string",
                            "enum": ["patriots", "celtics", "nesl"],
                            "description": "Team color theme for the flyer.",
                        },
                        "headline": {
                            "type": "string",
                            "description": "Short punchy headline (≤50 chars) shown prominently on the flyer.",
                        },
                        "subtitle": {
                            "type": "string",
                            "description": "Supporting text shown below the headline (optional).",
                        },
                        "game_data": {
                            "type": "object",
                            "description": "Required for score_update flyers — pass the game object from get_game_scores.",
                            "properties": {
                                "home_team":     {"type": "string"},
                                "home_team_abbr":{"type": "string"},
                                "home_score":    {"type": "integer"},
                                "home_winner":   {"type": "boolean"},
                                "away_team":     {"type": "string"},
                                "away_team_abbr":{"type": "string"},
                                "away_score":    {"type": "integer"},
                                "away_winner":   {"type": "boolean"},
                                "venue":         {"type": "string"},
                                "date":          {"type": "string"},
                            },
                        },
                    },
                    "required": ["post_type", "team", "headline"],
                },
            },
            {
                "name": "post_to_instagram",
                "description": (
                    "Upload the flyer image and caption to Instagram. "
                    "Requires a valid image_path returned by create_flyer. "
                    "Also saves a local copy of the caption for records."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "File path returned by create_flyer.",
                        },
                        "caption": {
                            "type": "string",
                            "description": "Full Instagram caption including hashtags (≤2200 chars).",
                        },
                        "post_as_story": {
                            "type": "boolean",
                            "description": "Also post this image to Instagram Stories. Default: false.",
                            "default": False,
                        },
                    },
                    "required": ["image_path", "caption"],
                },
            },
            {
                "name": "save_post_draft",
                "description": (
                    "Save the flyer image path and caption locally as a draft — does NOT post to Instagram. "
                    "Use this for preview/review mode."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "File path returned by create_flyer.",
                        },
                        "caption": {
                            "type": "string",
                            "description": "Full post caption with hashtags.",
                        },
                        "post_type": {
                            "type": "string",
                            "description": "Label for organizing drafts (e.g. score_update, breaking_news).",
                        },
                    },
                    "required": ["image_path", "caption"],
                },
            },
        ]

    # ─── Tool Execution ───────────────────────────────────────────────────────

    def _run_tool(self, name: str, inp: dict) -> Any:
        # ── get_game_scores ──────────────────────────────────────────────────
        if name == "get_game_scores":
            team      = inp["team"]
            days_back = inp.get("days_back", 2)
            results: list[dict] = []

            if team in ("patriots", "both"):
                games = self.sports.get_recent_results("patriots", days_back)
                results.extend({**g, "_team_ctx": "patriots"} for g in games)
            if team in ("celtics", "both"):
                games = self.sports.get_recent_results("celtics", days_back)
                results.extend({**g, "_team_ctx": "celtics"} for g in games)

            return {"games": results, "count": len(results)}

        # ── get_sports_news ──────────────────────────────────────────────────
        if name == "get_sports_news":
            team  = inp["team"]
            limit = min(inp.get("limit", 5), 10)
            arts: list[dict] = []

            if team in ("patriots", "both"):
                arts.extend({**a, "_team": "patriots"} for a in self.sports.get_nfl_news(limit))
            if team in ("celtics", "both"):
                arts.extend({**a, "_team": "celtics"} for a in self.sports.get_nba_news(limit))

            return {"articles": arts[:limit], "count": len(arts)}

        # ── create_flyer ─────────────────────────────────────────────────────
        if name == "create_flyer":
            post_type = inp["post_type"]
            team      = inp["team"]
            headline  = inp["headline"]
            subtitle  = inp.get("subtitle", "")
            game_data = inp.get("game_data")

            if post_type == "score_update" and game_data:
                path = self.img_gen.create_score_update(game_data, team)
            elif post_type == "breaking_news":
                path = self.img_gen.create_breaking_news(headline, subtitle, team)
            elif post_type == "hype":
                path = self.img_gen.create_hype_post(headline, subtitle, team)
            else:
                path = self.img_gen.create_general_post(headline, subtitle, team)

            return {"image_path": path, "success": True}

        # ── post_to_instagram ────────────────────────────────────────────────
        if name == "post_to_instagram":
            image_path    = inp["image_path"]
            caption       = inp["caption"]
            post_as_story = inp.get("post_as_story", False)

            result = self.ig.post_photo(image_path, caption)

            if post_as_story:
                result["story"] = self.ig.post_story(image_path)

            # Always record a local draft copy
            self._write_draft(image_path, caption, "ig_post")
            return result

        # ── save_post_draft ──────────────────────────────────────────────────
        if name == "save_post_draft":
            image_path = inp["image_path"]
            caption    = inp["caption"]
            post_type  = inp.get("post_type", "general")
            self._write_draft(image_path, caption, post_type)
            return {
                "success": True,
                "message": f"Draft saved to {config.POSTS_DIR}",
                "image_path": image_path,
            }

        return {"error": f"Unknown tool: {name}"}

    def _write_draft(self, image_path: str, caption: str, label: str) -> None:
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = config.POSTS_DIR / f"{label}_{ts}_caption.txt"
        path.write_text(caption, encoding="utf-8")

    # ─── Agentic Loop ─────────────────────────────────────────────────────────

    def run(self, task: str, verbose: bool = True) -> str:
        """
        Run the agentic loop for a given task.
        Uses tool use until Claude returns end_turn.
        """
        if verbose:
            print(f"\n[NESL] Task: {task}")

        messages: list[dict] = [{"role": "user", "content": task}]
        max_iters = 12

        for iteration in range(max_iters):
            response = self.client.messages.create(
                model=self.MODEL,
                max_tokens=4096,
                system=[
                    {
                        "type": "text",
                        "text": _SYSTEM,
                        "cache_control": {"type": "ephemeral"},   # cache the system prompt
                    }
                ],
                tools=self.tools,
                messages=messages,
            )

            # Append the full assistant response (preserves thinking blocks too)
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                final = next(
                    (b.text for b in response.content if hasattr(b, "text")),
                    "Task completed.",
                )
                if verbose:
                    print(f"\n[NESL] Done: {final}")
                return final

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    if verbose:
                        print(f"[NESL] → {block.name}({json.dumps(block.input, default=str)[:120]}...)")
                    result = self._run_tool(block.name, block.input)
                    if verbose:
                        print(f"[NESL] ← {json.dumps(result, default=str)[:180]}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str),
                    })
                messages.append({"role": "user", "content": tool_results})
                continue

            # Unexpected stop reason — exit loop
            break

        return "Agent loop completed."

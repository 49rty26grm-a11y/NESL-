# NESL — New England Sports Lab Social Media Agent

AI-powered social media agent for [@nesportslab](https://instagram.com/nesportslab), covering the **New England Patriots** and **Boston Celtics**.

Built with the [Claude claude-opus-4-6](https://anthropic.com) API, ESPN's public data feed, and Pillow for flyer generation.

---

## Features

| Feature | Details |
|---|---|
| **Score updates** | Detects completed games, generates recap + branded flyer |
| **Breaking news** | Pulls latest ESPN headlines, creates high-impact news flyer |
| **Hype posts** | Pre-game energy posts with team-color flyers |
| **Custom posts** | One-off posts from any headline you provide |
| **Daily digest** | One command covers scores + top news for both teams |
| **Scheduler** | Daemon mode — runs on a configurable interval |
| **Instagram** | Auto-posts or saves as a local draft for review |
| **NESL logo** | Logo overlaid on every generated flyer |

---

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Add ANTHROPIC_API_KEY (and Instagram creds when ready)

# 3. Add logo
# Drop nesl_logo.png into assets/

# 4. Check setup
python run.py check
```

---

## Commands

```bash
# Score updates — last 2 days, both teams (saves drafts)
python run.py scores

# Score update for Celtics only, auto-post to Instagram
python run.py scores --team celtics --post

# Breaking news post
python run.py news --team patriots

# Game-day hype post
python run.py hype --team celtics --post

# Full daily update (scores + top news, both teams)
python run.py daily

# Custom post
python run.py post "JAYLEN BROWN IS UNSTOPPABLE" --team celtics --type hype

# Scheduled daemon (every 30 minutes)
python run.py schedule --interval 30
```

All commands default to **draft mode**. Add `--post` to go live on Instagram.

---

## Project Structure

```
NESL-/
├── run.py                  ← entry point
├── requirements.txt
├── .env.example
├── agent/
│   ├── config.py           ← settings, team colors, ESPN endpoints
│   ├── sports_data.py      ← ESPN API fetcher (scores + news)
│   ├── image_gen.py        ← Pillow flyer generator (4 templates)
│   ├── instagram.py        ← instagrapi client (feed + stories)
│   ├── nesl_agent.py       ← Claude claude-opus-4-6 agentic loop + tools
│   └── main.py             ← Click CLI
├── assets/
│   └── nesl_logo.png       ← ADD YOUR LOGO HERE
└── posts/                  ← generated flyers + draft captions saved here
```

---

## Instagram Setup

1. Add `INSTAGRAM_USERNAME` + `INSTAGRAM_PASSWORD` to `.env`
2. Run any command with `--post`
3. A session file (`.ig_session.json`) is cached to avoid repeated logins

---

## How It Works

```
python run.py scores
       │
       ▼
 NESLAgent.run(task)
       │
       ├── Claude claude-opus-4-6 reasons + calls tools
       │
       ├── get_game_scores  → ESPN scoreboard API
       ├── get_sports_news  → ESPN news API
       ├── create_flyer     → Pillow 1080×1080 PNG
       ├── post_to_instagram → instagrapi
       └── save_post_draft  → local draft copy
```

Adaptive thinking + prompt caching keep it fast and cost-efficient.

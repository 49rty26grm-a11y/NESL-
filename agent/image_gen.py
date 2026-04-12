"""
NESL Agent — Image / Flyer Generator
Creates branded social media flyers using Pillow.
Supports: score updates, breaking news, hype posts, general posts.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import config


class ImageGenerator:
    """Generates 1080×1080 social media flyers with NESL branding."""

    WIDTH  = 1080
    HEIGHT = 1080

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        candidates = []
        if bold:
            candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
                "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
                "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
            ]
        else:
            candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
                "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size)
            except (IOError, OSError):
                continue
        # Fallback: PIL default (no size control but always works)
        return ImageFont.load_default()

    def _draw_gradient(self, img: Image.Image, top: tuple, bottom: tuple) -> None:
        """Vertical gradient background from top color to bottom color."""
        w, h = img.size
        strip = Image.new("RGB", (1, h))
        for y in range(h):
            ratio = y / h
            px = tuple(int(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(3))
            strip.putpixel((0, y), px)
        img.paste(strip.resize((w, h), Image.NEAREST))

    @staticmethod
    def _darken(color: tuple, factor: float = 0.5) -> tuple:
        return tuple(int(c * factor) for c in color[:3])

    def _wrap_text(
        self, draw: ImageDraw.ImageDraw, text: str,
        font: ImageFont.FreeTypeFont, max_width: int
    ) -> list[str]:
        words, lines, current = text.split(), [], []
        for word in words:
            test = " ".join(current + [word])
            w = draw.textlength(test, font=font)
            if w <= max_width:
                current.append(word)
            else:
                if current:
                    lines.append(" ".join(current))
                current = [word]
        if current:
            lines.append(" ".join(current))
        return lines

    def _stamp_logo(self, img: Image.Image, corner: str = "br", size: int = 140) -> None:
        """Overlay the NESL logo (or a text badge fallback) onto img."""
        w, h = img.size
        pad = 18

        if config.NESL_LOGO_PATH.exists():
            logo = Image.open(config.NESL_LOGO_PATH).convert("RGBA")
            logo.thumbnail((size, size), Image.LANCZOS)
            lw, lh = logo.size
            positions = {
                "br": (w - lw - pad, h - lh - pad),
                "bl": (pad, h - lh - pad),
                "tr": (w - lw - pad, pad),
                "tl": (pad, pad),
            }
            pos = positions.get(corner, positions["br"])
            img.paste(logo, pos, logo)
        else:
            # Text badge fallback when logo file is absent
            draw = ImageDraw.Draw(img)
            font = self._get_font(26, bold=True)
            bw, bh = 190, 56
            positions = {
                "br": (w - bw - pad, h - bh - pad),
                "bl": (pad, h - bh - pad),
                "tr": (w - bw - pad, pad),
                "tl": (pad, pad),
            }
            bx, by = positions.get(corner, positions["br"])
            draw.rectangle([bx, by, bx + bw, by + bh], fill=(0, 0, 0), outline=(255, 215, 0), width=3)
            draw.text((bx + bw // 2, by + bh // 2), "NESL", fill=(255, 215, 0), font=font, anchor="mm")

    def _bottom_bar(self, draw: ImageDraw.ImageDraw, fill: tuple) -> None:
        draw.rectangle([0, 930, self.WIDTH, self.HEIGHT], fill=fill)
        font = self._get_font(20)
        draw.text(
            (self.WIDTH // 2, 965),
            "FOLLOW @NESPORTSLAB FOR ALL YOUR BOSTON SPORTS NEWS  🏆",
            fill=(255, 215, 0), font=font, anchor="mm",
        )

    def _save(self, img: Image.Image, prefix: str) -> str:
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = config.POSTS_DIR / f"{prefix}_{ts}.png"
        img.save(str(path), optimize=True)
        return str(path)

    # ─── Templates ────────────────────────────────────────────────────────────

    def create_score_update(self, game_data: dict, team: str = "patriots") -> str:
        """Final score flyer showing both teams, scores and winner highlight."""
        colors = config.PATRIOTS_COLORS if team == "patriots" else config.CELTICS_COLORS
        img    = Image.new("RGB", (self.WIDTH, self.HEIGHT))

        self._draw_gradient(img, colors["primary"], self._darken(colors["primary"], 0.45))
        draw = ImageDraw.Draw(img)

        # Red/green accent stripe at the top
        draw.rectangle([0, 0, self.WIDTH, 140], fill=colors["secondary"])

        # Diagonal decorative stripe
        draw.polygon(
            [(0, 140), (self.WIDTH, 140), (self.WIDTH, 220), (0, 320)],
            fill=(*self._darken(colors["secondary"], 0.7), 160),
        )

        font_xl  = self._get_font(96, bold=True)
        font_lg  = self._get_font(60, bold=True)
        font_md  = self._get_font(44, bold=True)
        font_sm  = self._get_font(30)
        font_xs  = self._get_font(22)

        # "FINAL" header
        draw.text((self.WIDTH // 2, 70), "F I N A L", fill=colors["text"], font=font_md, anchor="mm")

        # Vertical center divider
        draw.rectangle([self.WIDTH // 2 - 2, 150, self.WIDTH // 2 + 2, 890], fill=(*colors["accent"], 120))

        away_team  = game_data.get("away_team", "")
        away_abbr  = game_data.get("away_team_abbr", away_team[:3].upper())
        away_score = game_data.get("away_score", 0)
        away_win   = game_data.get("away_winner", False)
        home_team  = game_data.get("home_team", "")
        home_abbr  = game_data.get("home_team_abbr", home_team[:3].upper())
        home_score = game_data.get("home_score", 0)
        home_win   = game_data.get("home_winner", False)

        gold = (255, 215, 0)

        # ── Away side (left) ──
        draw.text((self.WIDTH // 4, 300), away_abbr, fill=colors["accent"], font=font_lg, anchor="mm")
        for j, line in enumerate(self._wrap_text(draw, away_team.upper(), font_sm, 460)[:2]):
            draw.text((self.WIDTH // 4, 380 + j * 42), line, fill=colors["text"], font=font_sm, anchor="mm")
        draw.text((self.WIDTH // 4, 570), str(away_score),
                  fill=gold if away_win else colors["text"], font=font_xl, anchor="mm")

        # ── Home side (right) ──
        draw.text((3 * self.WIDTH // 4, 300), home_abbr, fill=colors["accent"], font=font_lg, anchor="mm")
        for j, line in enumerate(self._wrap_text(draw, home_team.upper(), font_sm, 460)[:2]):
            draw.text((3 * self.WIDTH // 4, 380 + j * 42), line, fill=colors["text"], font=font_sm, anchor="mm")
        draw.text((3 * self.WIDTH // 4, 570), str(home_score),
                  fill=gold if home_win else colors["text"], font=font_xl, anchor="mm")

        # Winner crown
        winner = away_team if away_win else home_team
        draw.text((self.WIDTH // 2, 700), f"🏆  {winner.upper()}  WIN!", fill=gold, font=font_sm, anchor="mm")

        venue = game_data.get("venue", "")
        date  = game_data.get("date", "")
        if venue:
            draw.text((self.WIDTH // 2, 780), venue, fill=colors["accent"], font=font_xs, anchor="mm")
        if date:
            draw.text((self.WIDTH // 2, 810), date, fill=(200, 200, 200), font=font_xs, anchor="mm")

        self._bottom_bar(draw, self._darken(colors["primary"], 0.35))
        self._stamp_logo(img, "br", 130)
        return self._save(img, f"score_{team}")

    def create_breaking_news(self, headline: str, subtitle: str = "", team: str = "nesl") -> str:
        """High-impact breaking news flyer with red BREAKING banner."""
        img  = Image.new("RGB", (self.WIDTH, self.HEIGHT))
        self._draw_gradient(img, (8, 8, 8), (28, 28, 28))
        draw = ImageDraw.Draw(img)

        red = (220, 38, 38)
        gold = (255, 215, 0)

        # Red accent bars
        draw.rectangle([0, 0, self.WIDTH, 6], fill=red)
        draw.rectangle([0, self.HEIGHT - 6, self.WIDTH, self.HEIGHT], fill=red)

        # BREAKING banner
        draw.rectangle([0, 0, self.WIDTH, 175], fill=red)
        font_breaking = self._get_font(78, bold=True)
        draw.text((self.WIDTH // 2, 88), "⚡  BREAKING NEWS  ⚡", fill=(255, 255, 255), font=font_breaking, anchor="mm")

        # Team color tag
        if team == "patriots":
            tag_color = config.PATRIOTS_COLORS["secondary"]
            tag_text  = "NEW ENGLAND PATRIOTS"
        elif team == "celtics":
            tag_color = config.CELTICS_COLORS["primary"]
            tag_text  = "BOSTON CELTICS"
        else:
            tag_color = (40, 40, 40)
            tag_text  = "BOSTON SPORTS"

        draw.rectangle([0, 175, self.WIDTH, 230], fill=tag_color)
        draw.text((self.WIDTH // 2, 202), tag_text, fill=(255, 255, 255),
                  font=self._get_font(32, bold=True), anchor="mm")

        # Headline
        font_hl = self._get_font(58, bold=True)
        y = 300
        for line in self._wrap_text(draw, headline.upper(), font_hl, self.WIDTH - 80)[:4]:
            draw.text((self.WIDTH // 2, y), line, fill=gold, font=font_hl, anchor="mm")
            y += 82

        # Subtitle
        if subtitle:
            y += 20
            font_sub = self._get_font(36)
            for line in self._wrap_text(draw, subtitle, font_sub, self.WIDTH - 100)[:3]:
                draw.text((self.WIDTH // 2, y), line, fill=(210, 210, 210), font=font_sub, anchor="mm")
                y += 55

        self._bottom_bar(draw, (18, 18, 18))
        self._stamp_logo(img, "bl", 130)
        return self._save(img, f"news_{team}")

    def create_hype_post(self, headline: str, subtitle: str = "", team: str = "patriots") -> str:
        """Pre-game hype / engagement post with team colors."""
        colors = config.PATRIOTS_COLORS if team == "patriots" else config.CELTICS_COLORS
        img    = Image.new("RGB", (self.WIDTH, self.HEIGHT))

        self._draw_gradient(img, self._darken(colors["primary"], 0.4), colors["primary"])
        draw = ImageDraw.Draw(img)

        # Bottom accent triangle
        draw.polygon(
            [(0, self.HEIGHT), (self.WIDTH, self.HEIGHT), (self.WIDTH, self.HEIGHT - 300), (0, self.HEIGHT - 180)],
            fill=(*colors["secondary"], 90),
        )

        font_team = self._get_font(36, bold=True)
        font_xl   = self._get_font(88, bold=True)
        font_md   = self._get_font(40)
        font_xs   = self._get_font(22)

        # Team name header
        team_name = colors["name"].upper()
        draw.text((self.WIDTH // 2, 80), team_name, fill=colors["accent"], font=font_team, anchor="mm")

        # Gold divider
        draw.rectangle([80, 118, self.WIDTH - 80, 124], fill=colors["secondary"])

        # Main headline
        y = 220
        for line in self._wrap_text(draw, headline.upper(), font_xl, self.WIDTH - 60)[:3]:
            draw.text((self.WIDTH // 2, y), line, fill=colors["text"], font=font_xl, anchor="mm")
            y += 108

        # Subtitle
        if subtitle:
            y += 24
            for line in self._wrap_text(draw, subtitle, font_md, self.WIDTH - 100)[:2]:
                draw.text((self.WIDTH // 2, y), line, fill=colors["accent"], font=font_md, anchor="mm")
                y += 60

        self._bottom_bar(draw, self._darken(colors["primary"], 0.35))
        self._stamp_logo(img, "br", 130)
        return self._save(img, f"hype_{team}")

    def create_general_post(self, headline: str, body: str = "", team: str = "nesl") -> str:
        """General engagement / discussion post."""
        if team == "patriots":
            return self.create_hype_post(headline, body, "patriots")
        elif team == "celtics":
            return self.create_hype_post(headline, body, "celtics")
        else:
            return self.create_breaking_news(headline, body, "nesl")

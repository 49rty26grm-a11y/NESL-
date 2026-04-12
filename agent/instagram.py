"""
NESL Agent — Instagram Client
Handles login (with session caching) and photo/story posting via instagrapi.
Falls back to local-save-only mode when credentials are missing.
"""
from __future__ import annotations

from pathlib import Path
from . import config

try:
    from instagrapi import Client as _IGClient
    _INSTAGRAPI_OK = True
except ImportError:
    _INSTAGRAPI_OK = False


class InstagramClient:
    """Thin wrapper around instagrapi for NESL posting needs."""

    def __init__(self) -> None:
        self._client: "_IGClient | None" = None
        self._logged_in = False
        self._session_path = config.BASE_DIR / ".ig_session.json"

    # ─── Auth ─────────────────────────────────────────────────────────────────

    def _ensure_login(self) -> bool:
        if not _INSTAGRAPI_OK:
            print("[Instagram] instagrapi not installed — posts saved locally only.")
            return False
        if not (config.INSTAGRAM_USERNAME and config.INSTAGRAM_PASSWORD):
            print("[Instagram] Credentials not set — posts saved locally only.")
            return False
        if self._logged_in and self._client:
            return True

        self._client = _IGClient()

        # Try reusing an existing session first (avoids challenge prompts)
        if self._session_path.exists():
            try:
                self._client.load_settings(str(self._session_path))
                self._client.get_timeline_feed()   # lightweight auth test
                self._logged_in = True
                return True
            except Exception:
                pass

        # Fresh login
        try:
            self._client.login(config.INSTAGRAM_USERNAME, config.INSTAGRAM_PASSWORD)
            self._client.dump_settings(str(self._session_path))
            self._logged_in = True
            return True
        except Exception as exc:
            print(f"[Instagram] Login failed: {exc}")
            return False

    # ─── Posting ──────────────────────────────────────────────────────────────

    def post_photo(self, image_path: str, caption: str) -> dict:
        """Upload a photo to the Instagram feed."""
        if not self._ensure_login():
            return {"success": False, "reason": "not_logged_in", "local_path": image_path}
        try:
            media = self._client.photo_upload(image_path, caption)  # type: ignore[union-attr]
            return {
                "success": True,
                "media_id": str(media.pk),
                "url": f"https://www.instagram.com/p/{media.code}/",
            }
        except Exception as exc:
            return {"success": False, "error": str(exc), "local_path": image_path}

    def post_story(self, image_path: str) -> dict:
        """Upload a photo to Instagram Stories."""
        if not self._ensure_login():
            return {"success": False, "reason": "not_logged_in"}
        try:
            media = self._client.photo_upload_to_story(image_path)  # type: ignore[union-attr]
            return {"success": True, "media_id": str(media.pk)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

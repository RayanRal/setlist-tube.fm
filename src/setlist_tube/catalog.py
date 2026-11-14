"""Music catalogs we can search. YouTube Music today; others (Spotify) later."""

from __future__ import annotations

import logging
import re
import threading
from typing import Any, Literal, Protocol

from ytmusicapi import YTMusic

from setlist_tube.models import Track

log = logging.getLogger(__name__)

SearchKind = Literal["songs", "videos"]

DEAD_STATUSES = frozenset({"UNPLAYABLE", "ERROR"})
"""Playability statuses that mean the video is gone. Anything else (sign-in or
age walls, odd new statuses) might still play for the viewer, so we keep it."""
_BOT_WALL_RE = re.compile(r"\b(bot|sign in|log in|login)\b", re.IGNORECASE)
"""YouTube's answer to requests it suspects are automated, e.g. from cloud
servers: it says nothing about whether the video plays for a real viewer."""
DISTRUST_AFTER = 5
"""After this many rejections in a row, assume YouTube is blocking our checks
(not that every track is dead) and keep tracks until a check succeeds again."""


class Catalog(Protocol):
    def search(self, query: str, limit: int = 5, *, videos: bool = False) -> list[Track]:
        """Search catalog songs, or plain videos when ``videos`` is set.

        Catalogs without videos (e.g. Spotify) return ``[]`` for ``videos=True``.
        """
        ...

    def is_playable(self, track_id: str) -> bool:
        """Whether the track can actually be played (not removed or blocked)."""
        ...


def _track_from_result(result: dict[str, Any], *, is_song: bool) -> Track | None:
    video_id = result.get("videoId")
    title = result.get("title")
    if not video_id or not title or result.get("isAvailable") is False:
        return None
    return Track(
        id=video_id,
        title=title,
        artists=[a["name"] for a in result.get("artists") or [] if a.get("name")],
        album=(result.get("album") or {}).get("name"),
        duration=result.get("duration"),
        is_song=is_song,
    )


class YouTubeMusicCatalog:
    """Anonymous (no login) YouTube Music search via ytmusicapi.

    Songs give clean studio tracks; videos cover rarities and live-only songs.
    """

    def __init__(self, client: Any | None = None) -> None:
        self._yt = client if client is not None else YTMusic()
        self._lock = threading.Lock()
        self._dead_streak = 0

    def _search(self, query: str, kind: SearchKind, limit: int) -> list[Track]:
        try:
            results = self._yt.search(query, filter=kind, limit=limit)
        except Exception:  # ytmusicapi raises assorted errors on API changes
            log.exception("YouTube Music search failed for %r", query)
            return []
        tracks = (_track_from_result(r, is_song=kind == "songs") for r in results)
        return [t for t in tracks if t is not None][:limit]

    def search(self, query: str, limit: int = 5, *, videos: bool = False) -> list[Track]:
        return self._search(query, "videos" if videos else "songs", limit)

    def is_playable(self, track_id: str) -> bool:
        """Ask YouTube whether the video plays, as seen from this server.

        Search still returns some tracks that only show "Video unavailable",
        so those are dropped. Whenever the answer is unclear (the check fails,
        YouTube asks us to prove we're not a bot, or every check is coming
        back negative) we keep the track: a rare dead track is far better
        than an empty playlist.
        """
        try:
            status = self._yt.get_song(track_id).get("playabilityStatus") or {}
        except Exception:
            log.exception("YouTube playability check failed for %r", track_id)
            return True
        code, reason = status.get("status"), str(status.get("reason") or "")
        if code == "OK":
            self._record(dead=False)
            return True
        if code not in DEAD_STATUSES or _BOT_WALL_RE.search(reason):
            log.warning("Unclear playability for %s (%s: %s); keeping it", track_id, code, reason)
            return True
        if self._record(dead=True) >= DISTRUST_AFTER:
            log.warning(
                "Ignoring 'unplayable' for %s: %d in a row looks like blocking",
                track_id,
                self._dead_streak,
            )
            return True
        log.info("Skipping unplayable %s: %s", track_id, reason)
        return False

    def _record(self, *, dead: bool) -> int:
        """Track consecutive 'dead' answers; return the current streak."""
        with self._lock:
            self._dead_streak = self._dead_streak + 1 if dead else 0
            return self._dead_streak

"""Music catalogs we can search. YouTube Music today; others (Spotify) later."""

from __future__ import annotations

import logging
from typing import Any, Literal, Protocol

from ytmusicapi import YTMusic

from setlist_tube.models import Track

log = logging.getLogger(__name__)

SearchKind = Literal["songs", "videos"]


class Catalog(Protocol):
    def search(self, query: str, limit: int = 5, *, videos: bool = False) -> list[Track]:
        """Search catalog songs, or plain videos when ``videos`` is set.

        Catalogs without videos (e.g. Spotify) return ``[]`` for ``videos=True``.
        """
        ...


def _track_from_result(result: dict[str, Any], *, is_song: bool) -> Track | None:
    video_id = result.get("videoId")
    title = result.get("title")
    if not video_id or not title:
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

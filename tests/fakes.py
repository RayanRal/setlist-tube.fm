"""Test doubles shared across tests."""

from __future__ import annotations

from setlist_tube.models import Track


class FakeCatalog:
    """Returns canned results keyed by exact query string."""

    def __init__(
        self,
        songs: dict[str, list[Track]],
        videos: dict[str, list[Track]] | None = None,
        unplayable: set[str] | None = None,
    ) -> None:
        self.songs = songs
        self.videos = videos or {}
        self.unplayable = unplayable or set()
        self.queries: list[tuple[str, bool]] = []
        self.playability_checks: list[str] = []

    def search(self, query: str, limit: int = 5, *, videos: bool = False) -> list[Track]:
        self.queries.append((query, videos))
        return (self.videos if videos else self.songs).get(query, [])[:limit]

    def is_playable(self, track_id: str) -> bool:
        self.playability_checks.append(track_id)
        return track_id not in self.unplayable


def track(id_: str, title: str, *artists: str, is_song: bool = True) -> Track:
    return Track(id=id_, title=title, artists=list(artists), is_song=is_song)

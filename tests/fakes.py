"""Test doubles shared across tests."""

from __future__ import annotations

from setlist_tube.models import Track


class FakeCatalog:
    """Returns canned results keyed by exact query string."""

    def __init__(
        self, songs: dict[str, list[Track]], videos: dict[str, list[Track]] | None = None
    ) -> None:
        self.songs = songs
        self.videos = videos or {}
        self.queries: list[tuple[str, bool]] = []

    def search(self, query: str, limit: int = 5, *, videos: bool = False) -> list[Track]:
        self.queries.append((query, videos))
        return (self.videos if videos else self.songs).get(query, [])[:limit]


def track(id_: str, title: str, *artists: str, is_song: bool = True) -> Track:
    return Track(id=id_, title=title, artists=list(artists), is_song=is_song)

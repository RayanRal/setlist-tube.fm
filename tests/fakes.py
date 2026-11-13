"""Test doubles shared across tests."""

from __future__ import annotations

from setlist_tube.models import Track


class FakeCatalog:
    """Returns canned results keyed by exact query string."""

    def __init__(self, results: dict[str, list[Track]]) -> None:
        self.results = results
        self.queries: list[str] = []

    def search(self, query: str, limit: int = 5) -> list[Track]:
        self.queries.append(query)
        return self.results.get(query, [])[:limit]


def track(id_: str, title: str, *artists: str, is_song: bool = True) -> Track:
    return Track(id=id_, title=title, artists=list(artists), is_song=is_song)

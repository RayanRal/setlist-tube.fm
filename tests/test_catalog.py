from typing import Any

from setlist_tube.catalog import YouTubeMusicCatalog


class FakeYTMusic:
    def __init__(self, results: dict[str, list[dict[str, Any]]], fail: bool = False) -> None:
        self.results = results
        self.fail = fail
        self.calls: list[tuple[str, str | None]] = []

    def search(
        self, query: str, filter: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        self.calls.append((query, filter))
        if self.fail:
            raise RuntimeError("API changed")
        return self.results.get(filter or "", [])


SONG_RESULT = {
    "videoId": "abc123",
    "title": "Daydreaming",
    "artists": [{"name": "Radiohead", "id": "x"}],
    "album": {"name": "A Moon Shaped Pool"},
    "duration": "6:24",
}


def test_search_songs() -> None:
    catalog = YouTubeMusicCatalog(FakeYTMusic({"songs": [SONG_RESULT, {"title": "no id"}]}))
    [result] = catalog.search("radiohead daydreaming")
    assert result.id == "abc123"
    assert result.artists == ["Radiohead"]
    assert result.album == "A Moon Shaped Pool"
    assert result.is_song


def test_search_videos() -> None:
    fake = FakeYTMusic({"videos": [{**SONG_RESULT, "album": None}]})
    [result] = YouTubeMusicCatalog(fake).search("q", videos=True)
    assert not result.is_song
    assert result.album is None
    assert fake.calls == [("q", "videos")]


def test_search_errors_are_swallowed() -> None:
    assert YouTubeMusicCatalog(FakeYTMusic({}, fail=True)).search("q") == []

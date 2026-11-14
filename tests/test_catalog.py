from typing import Any

from setlist_tube.catalog import YouTubeMusicCatalog


class FakeYTMusic:
    def __init__(
        self,
        results: dict[str, list[dict[str, Any]]],
        fail: bool = False,
        songs: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.results = results
        self.fail = fail
        self.songs = songs or {}
        self.calls: list[tuple[str, str | None]] = []

    def search(
        self, query: str, filter: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        self.calls.append((query, filter))
        if self.fail:
            raise RuntimeError("API changed")
        return self.results.get(filter or "", [])

    def get_song(self, video_id: str) -> dict[str, Any]:
        if self.fail:
            raise RuntimeError("API changed")
        return self.songs[video_id]


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


def test_search_skips_results_marked_unavailable() -> None:
    gone = {**SONG_RESULT, "videoId": "gone", "isAvailable": False}
    catalog = YouTubeMusicCatalog(FakeYTMusic({"songs": [gone, SONG_RESULT]}))
    assert [t.id for t in catalog.search("q")] == ["abc123"]


def test_is_playable() -> None:
    fake = FakeYTMusic(
        {},
        songs={
            "ok": {"playabilityStatus": {"status": "OK"}},
            "dead": {"playabilityStatus": {"status": "UNPLAYABLE", "reason": "Video unavailable"}},
            "odd": {},
        },
    )
    catalog = YouTubeMusicCatalog(fake)
    assert catalog.is_playable("ok")
    assert not catalog.is_playable("dead")
    assert not catalog.is_playable("odd")


def test_is_playable_assumes_yes_when_check_fails() -> None:
    assert YouTubeMusicCatalog(FakeYTMusic({}, fail=True)).is_playable("x")

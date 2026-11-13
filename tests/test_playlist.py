from urllib.parse import parse_qs, urlparse

from setlist_tube.playlist import temporary_playlist_urls
from tests.fakes import track


def test_single_link_dedupes_and_keeps_order() -> None:
    [url] = temporary_playlist_urls([track("b", "x"), track("a", "y"), track("b", "x")])
    parsed = urlparse(url)
    assert parsed.netloc == "www.youtube.com"
    assert parsed.path == "/watch_videos"
    assert parse_qs(parsed.query)["video_ids"] == ["b,a"]


def test_splits_into_chunks_of_50() -> None:
    urls = temporary_playlist_urls([track(f"id{i}", "t") for i in range(120)])
    assert len(urls) == 3
    assert parse_qs(urlparse(urls[2]).query)["video_ids"][0].count(",") == 19


def test_no_tracks_no_links() -> None:
    assert temporary_playlist_urls([]) == []

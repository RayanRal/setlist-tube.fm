from typing import Any

import httpx
import pytest

from setlist_tube.setlistfm import (
    InvalidSetlistUrl,
    SetlistFmClient,
    SetlistNotFound,
    SetlistServiceError,
    parse_setlist,
    parse_setlist_id,
)

SAMPLE: dict[str, Any] = {
    "id": "63de4613",
    "url": "https://www.setlist.fm/setlist/radiohead/2017/x-63de4613.html",
    "eventDate": "26-07-2017",
    "artist": {"name": "Radiohead"},
    "venue": {
        "name": "Madison Square Garden",
        "city": {"name": "New York", "country": {"name": "United States"}},
    },
    "sets": {
        "set": [
            {
                "song": [
                    {"name": "Intro Music", "tape": True},
                    {"name": "Daydreaming"},
                    {"name": ""},
                    {"name": "Ful Stop"},
                ]
            },
            {
                "encore": 1,
                "song": [{"name": "Nobody Does It Better", "cover": {"name": "Carly Simon"}}],
            },
        ]
    },
}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "https://www.setlist.fm/setlist/radiohead/2017/madison-square-garden-new-york-ny-63de4613.html",
            "63de4613",
        ),
        ("setlist.fm/setlist/radiohead/2017/msg-63DE4613.html", "63de4613"),
        ("https://de.setlist.fm/setlist/radiohead/2017/msg-63de4613.html", "63de4613"),
        ("  63de4613 ", "63de4613"),
    ],
)
def test_parse_setlist_id(value: str, expected: str) -> None:
    assert parse_setlist_id(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "https://example.com/setlist/radiohead/2017/msg-63de4613.html",
        "https://notsetlist.fm/setlist/a/2017/msg-63de4613.html",
        "https://www.setlist.fm/stats/radiohead-bd6bd12.html",
        "https://www.setlist.fm/setlist/radiohead/2017/no-id.html",
        "https://[www.setlist.fm/setlist/radiohead/2017/msg-63de4613.html",
        "",
    ],
)
def test_parse_setlist_id_rejects(value: str) -> None:
    with pytest.raises(InvalidSetlistUrl):
        parse_setlist_id(value)


def test_parse_setlist() -> None:
    setlist = parse_setlist(SAMPLE)
    assert setlist.artist == "Radiohead"
    assert setlist.city == "New York, United States"
    assert (
        setlist.title == "Radiohead - Madison Square Garden, New York, United States (26-07-2017)"
    )
    assert [s.title for s in setlist.songs] == [
        "Intro Music",
        "Daydreaming",
        "Ful Stop",
        "Nobody Does It Better",
    ]
    assert setlist.songs[0].is_tape
    assert setlist.songs[3].original_artist == "Carly Simon"


def _client(handler: Any) -> SetlistFmClient:
    return SetlistFmClient("test-key", http=httpx.Client(transport=httpx.MockTransport(handler)))


def test_client_fetches_setlist() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/1.0/setlist/63de4613"
        assert request.headers["x-api-key"] == "test-key"
        return httpx.Response(200, json=SAMPLE)

    assert _client(handler).get_setlist("63de4613").artist == "Radiohead"


@pytest.mark.parametrize(
    ("status", "error"),
    [(404, SetlistNotFound), (429, SetlistServiceError), (500, SetlistServiceError)],
)
def test_client_errors(status: int, error: type[Exception]) -> None:
    with pytest.raises(error):
        _client(lambda _: httpx.Response(status)).get_setlist("63de4613")


def test_client_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(SetlistServiceError):
        _client(handler).get_setlist("63de4613")

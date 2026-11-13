from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from setlist_tube.models import Setlist, Song
from setlist_tube.service import SetlistService
from setlist_tube.setlistfm import SetlistNotFound
from setlist_tube.web import app, get_service
from tests.fakes import FakeCatalog, track

SETLIST = Setlist(
    id="63de4613",
    url="https://www.setlist.fm/setlist/radiohead/2017/msg-63de4613.html",
    artist="Radiohead",
    event_date="26-07-2017",
    venue="Madison Square Garden",
    city="New York",
    songs=[
        Song(title="Daydreaming", artist="Radiohead"),
        Song(title="Daydreamin", artist="Radiohead"),
        Song(title="Lost Song", artist="Radiohead"),
        Song(title="Outro", artist="Radiohead", is_tape=True),
    ],
)
SHOW_URL = SETLIST.url


class FakeSetlists:
    def get_setlist(self, setlist_id: str) -> Setlist:
        if setlist_id != "63de4613":
            raise SetlistNotFound("setlist.fm has no setlist with that ID.")
        return SETLIST


@pytest.fixture
def client() -> Iterator[TestClient]:
    catalog = FakeCatalog(
        {
            "Radiohead Daydreaming": [track("d1", "Daydreaming", "Radiohead")],
            "Radiohead Daydreamin": [track("d2", "Daydreaming", "Radiohead Tribute")],
        }
    )
    service = SetlistService(FakeSetlists(), catalog)  # type: ignore[arg-type]
    app.dependency_overrides[get_service] = lambda: service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_healthz(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


def test_index(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Make playlist" in response.text


def test_show(client: TestClient) -> None:
    response = client.get("/show", params={"url": SHOW_URL})
    assert response.status_code == 200
    html = response.text
    assert "Madison Square Garden" in html
    assert "watch_videos?video_ids=d1%2Cd2" in html
    assert "2 of 3 songs found" in html
    assert "unsure" in html
    assert "not found" in html
    assert "Skipped tape: Outro" in html


@pytest.mark.parametrize(
    ("url", "status", "message"),
    [
        ("https://example.com/foo", 400, "doesn&#39;t look like a setlist.fm link"),
        ("https://www.setlist.fm/setlist/a/2017/b-aaaaaaaa.html", 404, "no setlist with that ID"),
    ],
)
def test_show_errors(client: TestClient, url: str, status: int, message: str) -> None:
    response = client.get("/show", params={"url": url})
    assert response.status_code == status
    assert message in response.text


def test_api(client: TestClient) -> None:
    data = client.get("/api/setlist", params={"url": SHOW_URL}).json()
    assert data["setlist"]["artist"] == "Radiohead"
    assert data["setlist"]["title"].startswith("Radiohead - ")
    assert [m["track"]["id"] if m["track"] else None for m in data["matches"]] == [
        "d1",
        "d2",
        None,
    ]
    assert data["skipped"][0]["title"] == "Outro"


def test_api_error(client: TestClient) -> None:
    response = client.get("/api/setlist", params={"url": "nope"})
    assert response.status_code == 400


def test_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SETLISTFM_API_KEY", raising=False)
    get_service.cache_clear()
    response = TestClient(app).get("/show", params={"url": SHOW_URL})
    assert response.status_code == 503

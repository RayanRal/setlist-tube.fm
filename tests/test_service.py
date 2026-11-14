from setlist_tube.models import Setlist, Song
from setlist_tube.service import SetlistService, match_song
from tests.fakes import FakeCatalog, track


class FakeSetlists:
    def __init__(self, setlist: Setlist) -> None:
        self.setlist = setlist
        self.requested: list[str] = []

    def get_setlist(self, setlist_id: str) -> Setlist:
        self.requested.append(setlist_id)
        return self.setlist


COVER = Song(title="Nobody Does It Better", artist="Radiohead", original_artist="Carly Simon")


def test_cover_falls_back_to_original_artist() -> None:
    catalog = FakeCatalog(
        {"Carly Simon Nobody Does It Better": [track("c", "Nobody Does It Better", "Carly Simon")]}
    )
    match = match_song(catalog, COVER)
    assert match.track is not None and match.track.id == "c"
    assert catalog.queries == [
        ("Radiohead Nobody Does It Better", False),
        ("Radiohead Nobody Does It Better", True),
        ("Carly Simon Nobody Does It Better", False),
    ]


def test_cover_by_band_found_skips_fallback() -> None:
    catalog = FakeCatalog(
        {"Radiohead Nobody Does It Better": [track("r", "Nobody Does It Better", "Radiohead")]}
    )
    match = match_song(catalog, COVER)
    assert match.track is not None and match.track.id == "r"
    assert len(catalog.queries) == 1


def test_videos_tried_when_songs_dont_match() -> None:
    rarity = Song(title="Lift", artist="Radiohead")
    catalog = FakeCatalog(
        songs={"Radiohead Lift": [track("s", "Lift Me Up", "Someone Else")]},
        videos={"Radiohead Lift": [track("v", "Lift", "Radiohead", is_song=False)]},
    )
    match = match_song(catalog, rarity)
    assert match.track is not None and match.track.id == "v"


def test_unsure_song_kept_over_worse_video() -> None:
    song = Song(title="Daydreaming", artist="Radiohead")
    catalog = FakeCatalog(
        songs={"Radiohead Daydreaming": [track("s", "Daydreaming", "Radiohead Live Band")]},
        videos={"Radiohead Daydreaming": [track("v", "Daydream", "Radiohead Fans", is_song=False)]},
    )
    match = match_song(catalog, song)
    assert match.track is not None and match.track.id == "s"
    assert not match.confident


def test_build_end_to_end() -> None:
    setlist = Setlist(
        id="63de4613",
        url="https://www.setlist.fm/setlist/x-63de4613.html",
        artist="Radiohead",
        event_date="26-07-2017",
        venue="MSG",
        city="New York",
        songs=[
            Song(title="Intro", artist="Radiohead", is_tape=True),
            Song(title="Daydreaming", artist="Radiohead"),
            Song(title="Unknown B-side", artist="Radiohead"),
            Song(title="Ful Stop", artist="Radiohead"),
        ],
    )
    catalog = FakeCatalog(
        {
            "Radiohead Daydreaming": [track("d", "Daydreaming", "Radiohead")],
            "Radiohead Ful Stop": [track("f", "Ful Stop", "Radiohead")],
        }
    )
    setlists = FakeSetlists(setlist)
    result = SetlistService(setlists, catalog).build(  # type: ignore[arg-type]
        "https://www.setlist.fm/setlist/radiohead/2017/msg-63de4613.html"
    )

    assert setlists.requested == ["63de4613"]
    assert [s.title for s in result.skipped] == ["Intro"]
    assert [m.song.title for m in result.matches] == ["Daydreaming", "Unknown B-side", "Ful Stop"]
    assert [m.track.id for m in result.found if m.track] == ["d", "f"]
    assert len(result.playlist_urls) == 1
    assert "d%2Cf" in result.playlist_urls[0]


def test_build_can_include_tape() -> None:
    setlist = Setlist(
        id="1",
        url="",
        artist="A",
        event_date="",
        venue="",
        city="",
        songs=[Song(title="Intro", artist="A", is_tape=True)],
    )
    result = SetlistService(FakeSetlists(setlist), FakeCatalog({})).build(  # type: ignore[arg-type]
        "abcdef12", include_tape=True
    )
    assert result.skipped == []
    assert len(result.matches) == 1


RUE_MORGUE = Song(title="Murders in the Rue Morgue", artist="Iron Maiden")


def test_unplayable_match_falls_back_to_next_candidate() -> None:
    catalog = FakeCatalog(
        {
            "Iron Maiden Murders in the Rue Morgue": [
                track("dead", "Murders in the Rue Morgue", "Iron Maiden"),
                track("alive", "Murders in the Rue Morgue", "Iron Maiden"),
            ]
        },
        unplayable={"dead"},
    )
    match = match_song(catalog, RUE_MORGUE)
    assert match.track is not None and match.track.id == "alive"
    assert match.confident
    assert catalog.playability_checks == ["dead", "alive"]


def test_unplayable_song_falls_back_to_video() -> None:
    query = "Iron Maiden Murders in the Rue Morgue"
    catalog = FakeCatalog(
        {query: [track("dead", "Murders in the Rue Morgue", "Iron Maiden")]},
        videos={query: [track("v", "Murders in the Rue Morgue", "Iron Maiden", is_song=False)]},
        unplayable={"dead"},
    )
    match = match_song(catalog, RUE_MORGUE)
    assert match.track is not None and match.track.id == "v"


def test_all_unplayable_is_not_found() -> None:
    query = "Iron Maiden Murders in the Rue Morgue"
    catalog = FakeCatalog(
        {query: [track("dead", "Murders in the Rue Morgue", "Iron Maiden")]},
        unplayable={"dead"},
    )
    assert match_song(catalog, RUE_MORGUE).track is None


def test_playability_not_checked_for_candidates_that_cannot_win() -> None:
    query = "Iron Maiden Murders in the Rue Morgue"
    catalog = FakeCatalog(
        {query: [track("s", "Murders in the Rue Morgue", "Iron Maiden")]},
    )
    match_song(catalog, RUE_MORGUE)
    assert catalog.playability_checks == ["s"]  # confident on first search: one check

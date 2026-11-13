import pytest

from setlist_tube.matching import best_match, is_impostor, normalize, pick, title_similarity
from setlist_tube.models import Song
from tests.fakes import track


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Paranoid Android (Live at Glastonbury)", "paranoid android"),
        ("Karma Police - Remastered 2009", "karma police"),
        ("Beyoncé", "beyonce"),
        ("Crazy in Love (feat. Jay-Z)", "crazy in love"),
        ("Hey Ya!", "hey ya"),
        ("Rock & Roll", "rock and roll"),
        ("(Nice Dream)", "nice dream"),
    ],
)
def test_normalize(raw: str, expected: str) -> None:
    assert normalize(raw) == expected


def test_title_similarity_tolerates_typos() -> None:
    assert title_similarity("Paranoid Androd", "Paranoid Android") > 90
    assert title_similarity("Creep", "Karma Police") < 50
    assert title_similarity("", "Anything") == 0


SONG = Song(title="Daydreaming", artist="Radiohead")


def test_best_match_prefers_right_artist_and_title() -> None:
    match = best_match(
        SONG,
        "Radiohead",
        [
            track("a", "Daydreaming", "Some Cover Band"),
            track("b", "Daydreaming", "Radiohead"),
            track("c", "Burn the Witch", "Radiohead"),
        ],
    )
    assert match.track is not None and match.track.id == "b"
    assert match.confident


def test_best_match_prefers_songs_over_videos() -> None:
    match = best_match(
        SONG,
        "Radiohead",
        [
            track("v", "Daydreaming", "Radiohead", is_song=False),
            track("s", "Daydreaming", "Radiohead"),
        ],
    )
    assert match.track is not None and match.track.id == "s"


def test_best_match_low_confidence_still_returned() -> None:
    match = best_match(SONG, "Radiohead", [track("x", "Daydreamin", "Radiohead Live Band")])
    assert match.track is not None
    assert not match.confident


def test_best_match_rejects_garbage() -> None:
    match = best_match(SONG, "Radiohead", [track("x", "Baby Shark", "Pinkfong")])
    assert match.track is None
    assert best_match(SONG, "Radiohead", []).track is None


def test_pick_prefers_confident_then_score() -> None:
    weak = best_match(SONG, "Radiohead", [track("w", "Daydreamin", "Radiohead Live Band")])
    strong = best_match(SONG, "Radiohead", [track("s", "Daydreaming", "Radiohead")])
    none = best_match(SONG, "Radiohead", [])
    assert pick(weak, strong, none) is strong
    assert pick(none, weak) is weak


def test_best_match_rejects_same_title_by_other_artist() -> None:
    creep = Song(title="Creep", artist="Radiohead")
    assert best_match(creep, "Radiohead", [track("t", "Creep", "TLC")]).track is None
    assert best_match(creep, "Radiohead", [track("n", "Creep")]).track is None


def test_best_match_rejects_tributes_and_karaoke() -> None:
    song = Song(title="Californication", artist="Red Hot Chili Peppers")
    candidates = [
        track("t", "Californication", "Red Hot Chili Peppers Tribute"),
        track("k", "Californication (Karaoke Version)", "Red Hot Chili Peppers"),
        track("p", "Californication (Piano Version)", "Red Hot Chili Peppers"),
    ]
    assert best_match(song, "Red Hot Chili Peppers", candidates).track is None


@pytest.mark.parametrize(
    ("title", "artist", "found_title", "expected"),
    [
        ("Daydreaming", "Radiohead", "Daydreaming", False),
        ("Daydreaming", "Radiohead", "Daydreaming (Instrumental)", True),
        # The setlist itself asked for it, so it's not an impostor.
        ("Instrumental Jam", "Radiohead", "Instrumental Jam", False),
        ("Tribute", "Tenacious D", "Tribute", False),
    ],
)
def test_is_impostor(title: str, artist: str, found_title: str, expected: bool) -> None:
    assert is_impostor(title, artist, track("x", found_title, artist)) is expected

import pytest

from setlist_tube.matching import best_match, normalize, pick, title_similarity
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
    match = best_match(SONG, "Radiohead", [track("x", "Daydreamin", "Radiohead Tribute")])
    assert match.track is not None
    assert not match.confident


def test_best_match_rejects_garbage() -> None:
    match = best_match(SONG, "Radiohead", [track("x", "Baby Shark", "Pinkfong")])
    assert match.track is None
    assert best_match(SONG, "Radiohead", []).track is None


def test_pick_prefers_confident_then_score() -> None:
    weak = best_match(SONG, "Radiohead", [track("w", "Daydreamin", "Radiohead Tribute")])
    strong = best_match(SONG, "Radiohead", [track("s", "Daydreaming", "Radiohead")])
    none = best_match(SONG, "Radiohead", [])
    assert pick(weak, strong, none) is strong
    assert pick(none, weak) is weak

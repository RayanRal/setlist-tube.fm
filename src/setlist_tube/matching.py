"""Pick the catalog track that best matches a setlist song.

Pure functions only (no network) so the rules are easy to test and tune.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from rapidfuzz import fuzz

from setlist_tube.models import Match, Song, Track

# Suffixes/annotations that don't change which song it is.
_NOISE_RE = re.compile(
    r"""
    \s*[\(\[][^)\]]*\b(live|remaster(ed)?|version|edit|mix|mono|stereo|demo|acoustic
        |feat\.?|ft\.?|with|from|official|audio|video|lyrics?|explicit|bonus|deluxe)\b[^)\]]*[\)\]]
    | \s+-\s+.*\b(live|remaster(ed)?|version|edit|mix|mono|stereo|demo|acoustic)\b.*$
    | \s+(feat\.?|ft\.?)\s+.*$
    """,
    re.IGNORECASE | re.VERBOSE,
)
_NON_WORD_RE = re.compile(r"[^\w\s]")
# Re-recordings by someone else that otherwise look like a perfect match.
_IMPOSTOR_RE = re.compile(
    r"\b(tribute|karaoke|covers?|covered by|in the style of|made famous|originally performed"
    r"|instrumental|8[ -]?bit|lullaby|piano version|backing track)\b",
    re.IGNORECASE,
)
_SPACES_RE = re.compile(r"\s+")

TITLE_WEIGHT = 0.65
ARTIST_WEIGHT = 0.35
CONFIDENT_TITLE = 85.0
CONFIDENT_ARTIST = 80.0
MIN_SCORE = 55.0
"""Below this we'd rather report "not found" than play the wrong song."""
MIN_TITLE = 60.0
MIN_ARTIST = 50.0
"""Both must be plausible on their own: a same-titled song by another artist
(or with no artist at all) is a different song, however exact the title."""
VIDEO_PENALTY = 5.0
"""Prefer real catalog songs over plain videos when scores are close."""


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("&", " and ")
    text = _NOISE_RE.sub("", text)
    text = _NON_WORD_RE.sub(" ", text.lower())
    return _SPACES_RE.sub(" ", text).strip()


def title_similarity(a: str, b: str) -> float:
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    return max(fuzz.ratio(na, nb), fuzz.token_sort_ratio(na, nb))


def artist_similarity(artist: str, track_artists: Iterable[str]) -> float:
    target = normalize(artist)
    names = [normalize(a) for a in track_artists]
    if not target or not names:
        return 0.0
    # ytmusicapi already splits multi-artist credits into a list, so compare
    # each name whole: a partial match would let "X Tribute Band" pass for "X".
    return max(fuzz.ratio(target, n) for n in names)


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch)).lower()


def is_impostor(song_title: str, artist: str, track: Track) -> bool:
    """True for tribute/karaoke/cover-style tracks the setlist didn't ask for.

    Checked on the raw text, since :func:`normalize` strips some of these
    words (e.g. "(Piano Version)").
    """
    wanted = _fold(f"{song_title} {artist}")
    found = _fold(" ".join([track.title, *track.artists]))
    return any(m.group(0) not in wanted for m in _IMPOSTOR_RE.finditer(found))


def score(song_title: str, artist: str, track: Track) -> tuple[float, float, float]:
    """Return ``(total, title_score, artist_score)``."""
    t = title_similarity(song_title, track.title)
    a = artist_similarity(artist, track.artists)
    total = TITLE_WEIGHT * t + ARTIST_WEIGHT * a
    if not track.is_song:
        total -= VIDEO_PENALTY
    return total, t, a


def best_match(song: Song, artist: str, candidates: Iterable[Track]) -> Match:
    """Choose the best of ``candidates`` for ``song`` as performed by ``artist``."""
    best: Match = Match(song=song, track=None, score=0.0, confident=False)
    for track in candidates:
        if is_impostor(song.title, artist, track):
            continue
        total, t, a = score(song.title, artist, track)
        if t < MIN_TITLE or a < MIN_ARTIST:
            continue
        if total > best.score:
            confident = t >= CONFIDENT_TITLE and a >= CONFIDENT_ARTIST
            best = Match(song=song, track=track, score=total, confident=confident)
    if best.score < MIN_SCORE:
        return Match(song=song, track=None, score=best.score, confident=False)
    return best


def pick(*matches: Match) -> Match:
    """Prefer a confident match, then the highest score."""
    return max(matches, key=lambda m: (m.track is not None, m.confident, m.score))

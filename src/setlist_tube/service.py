"""Orchestrates: setlist.fm show -> matched tracks -> playlist links."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from setlist_tube.catalog import Catalog
from setlist_tube.matching import best_match, pick
from setlist_tube.models import Match, Setlist, Song
from setlist_tube.playlist import temporary_playlist_urls
from setlist_tube.setlistfm import SetlistFmClient, parse_setlist_id

SEARCH_CONCURRENCY = 6


@dataclass(frozen=True)
class SetlistResult:
    setlist: Setlist
    matches: list[Match]
    skipped: list[Song]
    """Songs we intentionally left out (tape intros/outros)."""
    playlist_urls: list[str]

    @property
    def found(self) -> list[Match]:
        return [m for m in self.matches if m.track is not None]


def match_song(catalog: Catalog, song: Song) -> Match:
    """Search until a confident match turns up, cheapest/likeliest first.

    1. The band's songs; 2. the band's videos (rarities, live-only songs);
    3-4. for covers, the original artist's songs, then videos.
    """
    artists = [song.artist]
    if song.original_artist:
        artists.append(song.original_artist)

    best = Match(song=song, track=None, score=0.0, confident=False)
    for artist in artists:
        for videos in (False, True):
            candidates = catalog.search(f"{artist} {song.title}", videos=videos)
            best = pick(best, best_match(song, artist, candidates))
            if best.confident:
                return best
    return best


class SetlistService:
    def __init__(self, setlists: SetlistFmClient, catalog: Catalog) -> None:
        self._setlists = setlists
        self._catalog = catalog

    def build(self, url_or_id: str, *, include_tape: bool = False) -> SetlistResult:
        setlist = self._setlists.get_setlist(parse_setlist_id(url_or_id))
        songs = [s for s in setlist.songs if include_tape or not s.is_tape]
        skipped = [s for s in setlist.songs if s.is_tape and not include_tape]

        with ThreadPoolExecutor(max_workers=SEARCH_CONCURRENCY) as pool:
            matches = list(pool.map(lambda s: match_song(self._catalog, s), songs))

        tracks = [m.track for m in matches if m.track is not None]
        return SetlistResult(
            setlist=setlist,
            matches=matches,
            skipped=skipped,
            playlist_urls=temporary_playlist_urls(tracks),
        )

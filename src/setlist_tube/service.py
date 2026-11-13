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
    primary = best_match(song, song.artist, catalog.search(f"{song.artist} {song.title}"))
    if primary.confident or not song.original_artist:
        return primary
    # Cover: the band's own recording may not exist; try the original artist.
    original = best_match(
        song,
        song.original_artist,
        catalog.search(f"{song.original_artist} {song.title}"),
    )
    return pick(primary, original)


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

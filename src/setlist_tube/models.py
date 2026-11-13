"""Plain data types shared across the app.

These are deliberately free of any service-specific details so that other
sources (beyond setlist.fm) and other catalogs (e.g. Spotify) can plug in later.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Song:
    """A song as listed in a setlist."""

    title: str
    artist: str
    """The performing artist."""
    original_artist: str | None = None
    """Set when the song is a cover."""
    is_tape: bool = False
    """Played from tape (intro/outro music), not performed live."""


@dataclass(frozen=True)
class Setlist:
    id: str
    url: str
    artist: str
    event_date: str
    venue: str
    city: str
    songs: list[Song] = field(default_factory=list)

    @property
    def title(self) -> str:
        place = ", ".join(part for part in (self.venue, self.city) if part)
        return f"{self.artist} - {place} ({self.event_date})"


@dataclass(frozen=True)
class Track:
    """A playable track in a music catalog."""

    id: str
    title: str
    artists: list[str]
    album: str | None = None
    duration: str | None = None
    is_song: bool = True
    """True for a catalog song; False for a plain video."""


@dataclass(frozen=True)
class Match:
    song: Song
    track: Track | None
    score: float
    """0-100; how confident we are that ``track`` is ``song``."""
    confident: bool

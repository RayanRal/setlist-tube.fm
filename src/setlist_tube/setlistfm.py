"""setlist.fm API client: https://api.setlist.fm/docs/1.0/index.html"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import httpx

from setlist_tube.models import Setlist, Song

API_BASE = "https://api.setlist.fm/rest/1.0"

# e.g. https://www.setlist.fm/setlist/radiohead/2017/madison-square-garden-new-york-ny-63de4613.html
_URL_ID_RE = re.compile(r"-([0-9a-f]{6,10})\.html?$", re.IGNORECASE)
_BARE_ID_RE = re.compile(r"^[0-9a-f]{6,10}$", re.IGNORECASE)


class SetlistError(Exception):
    """Base error; ``str(err)`` is safe to show to users."""


class InvalidSetlistUrl(SetlistError):  # noqa: N818 - reads better at call sites
    pass


class SetlistNotFound(SetlistError):  # noqa: N818
    pass


class SetlistServiceError(SetlistError):
    pass


def parse_setlist_id(url_or_id: str) -> str:
    """Extract the setlist ID from a setlist.fm show URL (or accept a bare ID)."""
    value = url_or_id.strip()
    if _BARE_ID_RE.match(value):
        return value.lower()

    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = (parsed.hostname or "").lower()
    if host != "setlist.fm" and not host.endswith(".setlist.fm"):
        raise InvalidSetlistUrl("That doesn't look like a setlist.fm link.")
    if not parsed.path.startswith("/setlist/"):
        raise InvalidSetlistUrl("Please link to a specific show (a setlist.fm/setlist/... page).")
    match = _URL_ID_RE.search(parsed.path)
    if not match:
        raise InvalidSetlistUrl("Couldn't find a setlist ID in that link.")
    return match.group(1).lower()


def parse_setlist(data: dict[str, Any]) -> Setlist:
    """Convert a setlist.fm API ``setlist`` payload into a :class:`Setlist`."""
    artist = (data.get("artist") or {}).get("name", "")
    venue = data.get("venue") or {}
    city = venue.get("city") or {}
    city_name = ", ".join(
        part for part in (city.get("name"), (city.get("country") or {}).get("name")) if part
    )

    songs: list[Song] = []
    for set_ in (data.get("sets") or {}).get("set") or []:
        for raw in set_.get("song") or []:
            title = (raw.get("name") or "").strip()
            if not title:
                continue  # setlist.fm uses empty names for unknown songs
            cover = (raw.get("cover") or {}).get("name")
            songs.append(
                Song(
                    title=title,
                    artist=artist,
                    original_artist=cover or None,
                    is_tape=bool(raw.get("tape")),
                )
            )

    return Setlist(
        id=data.get("id", ""),
        url=data.get("url", ""),
        artist=artist,
        event_date=data.get("eventDate", ""),
        venue=venue.get("name", ""),
        city=city_name,
        songs=songs,
    )


class SetlistFmClient:
    def __init__(self, api_key: str, http: httpx.Client | None = None) -> None:
        self._http = http or httpx.Client(timeout=10.0)
        self._headers = {"x-api-key": api_key, "Accept": "application/json"}

    def get_setlist(self, setlist_id: str) -> Setlist:
        try:
            response = self._http.get(f"{API_BASE}/setlist/{setlist_id}", headers=self._headers)
        except httpx.HTTPError as exc:
            raise SetlistServiceError("Couldn't reach setlist.fm. Try again shortly.") from exc

        if response.status_code == httpx.codes.NOT_FOUND:
            raise SetlistNotFound("setlist.fm has no setlist with that ID.")
        if response.status_code == httpx.codes.TOO_MANY_REQUESTS:
            raise SetlistServiceError("setlist.fm is rate-limiting us. Try again in a minute.")
        if response.is_error:
            raise SetlistServiceError(f"setlist.fm returned an error ({response.status_code}).")
        return parse_setlist(response.json())

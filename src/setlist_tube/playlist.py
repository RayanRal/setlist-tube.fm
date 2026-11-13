"""Turn matched tracks into something playable.

Today: anonymous temporary YouTube playlists (no account needed). A future
"save to my YouTube Music / Spotify" exporter can sit alongside this.
"""

from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import urlencode

from setlist_tube.models import Track

MAX_VIDEOS_PER_LINK = 50
"""YouTube ignores IDs beyond this in a single watch_videos link."""


def temporary_playlist_urls(tracks: Sequence[Track]) -> list[str]:
    """Build ``watch_videos`` links (split into chunks of 50) for ``tracks``."""
    ids = list(dict.fromkeys(t.id for t in tracks))  # de-dupe, keep order
    return [
        "https://www.youtube.com/watch_videos?"
        + urlencode({"video_ids": ",".join(ids[i : i + MAX_VIDEOS_PER_LINK])})
        for i in range(0, len(ids), MAX_VIDEOS_PER_LINK)
    ]

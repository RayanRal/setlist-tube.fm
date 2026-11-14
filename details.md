# How it works

1. The setlist is fetched from the setlist.fm API.
2. Each song is searched on YouTube Music (no login) and fuzzy-matched on
   title and artist. Live/remaster/feat. noise is ignored, covers fall back to
   the original artist, and tape intros/outros are skipped. Tracks YouTube
   reports as unplayable are skipped in favour of the next-best match.
3. The matches become a temporary YouTube playlist link
   (`youtube.com/watch_videos?video_ids=…`). No account needed.

Low-confidence matches are flagged as **unsure**; songs that can't be found are
listed but left out.

## Layout

```
src/setlist_tube/
  setlistfm.py   setlist.fm API client + URL parsing
  catalog.py     Catalog protocol; YouTube Music search via ytmusicapi
  matching.py    title/artist scoring (pure, no network)
  playlist.py    temporary YouTube playlist links
  service.py     ties it together: link -> setlist -> matches -> playlist
  web.py         FastAPI app (HTML page, JSON API, /healthz)
  templates/, static/
```

## Extension points

Not built yet, but the code is shaped for them:

- **Other catalogs (Spotify):** implement `Catalog.search` and
  `Catalog.is_playable` in `catalog.py`.
- **Save to the user's account (YouTube Music / Spotify):** add an exporter
  next to `playlist.py`; it takes the matched `Track`s.
- **Sharing / history:** `SetlistResult` is a plain dataclass, easy to
  persist once there's a database.

## Caveats

- YouTube Music search uses the unofficial
  [ytmusicapi](https://github.com/sigma67/ytmusicapi), which can break when
  YouTube changes things. YouTube may also throttle searches from cloud IPs.
- Playability is checked from the server's region, so a track blocked only in
  the viewer's country can still end up in the playlist.
- `watch_videos` links are undocumented and cap at 50 videos per link (longer
  shows get several links). They open in YouTube, not the YouTube Music app.
